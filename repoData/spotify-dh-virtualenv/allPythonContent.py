__FILENAME__ = cmdline
# -*- coding: utf-8 -*-
# Copyright (c) 2014 Spotify AB

# This file is part of dh-virtualenv.

# dh-virtualenv is free software: you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation, either version 2 of the
# License, or (at your option) any later version.

# dh-virtualenv is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with dh-virtualenv. If not, see
# <http://www.gnu.org/licenses/>.

"""Helpers to handle debhelper command line options."""

import os

from optparse import OptionParser, SUPPRESS_HELP


class DebhelperOptionParser(OptionParser):
    """Special OptionParser for handling Debhelper options.

    Basically this means converting -O--option to --option before
    parsing.

    """
    def parse_args(self, args=None, values=None):
        args = [o[2:] if o.startswith('-O-') else o
                for o in self._get_args(args)]
        args.extend(os.environ.get('DH_OPTIONS', '').split())
        # Unfortunately OptionParser is an old style class :(
        return OptionParser.parse_args(self, args, values)


def get_default_parser():
    usage = '%prog [options]'
    parser = DebhelperOptionParser(usage, version='%prog 0.7')
    parser.add_option('-p', '--package', action='append',
                      help='act on the package named PACKAGE')
    parser.add_option('-N', '--no-package', action='append',
                      help='do not act on the specified package')
    parser.add_option('-v', '--verbose', action='store_true',
                      default=False, help='Turn on verbose mode')
    parser.add_option('-s', '--setuptools', action='store_true',
                      default=False, help='Use Setuptools instead of Distribute')
    parser.add_option('--extra-index-url', action='append',
                      help='extra index URL to pass to pip.',
                      default=[])
    parser.add_option('--preinstall', action='append',
                      help=('package to install before processing '
                            'requirements.txt.'),
                      default=[])
    parser.add_option('--pypi-url', help='Base URL of the PyPI server')
    parser.add_option('--python', help='The Python to use')
    parser.add_option('-D', '--sourcedirectory', dest='sourcedirectory',
                      help='The source directory')
    parser.add_option('--no-test', action='store_false', dest='test',
                      help="Don't run tests for the package. Useful "
                      "for example when you have packaged with distutils.",
                      default=True)

    # Ignore user-specified option bundles
    parser.add_option('-O', help=SUPPRESS_HELP)
    parser.add_option('-a', '--arch', dest="arch",
                      help=("Act on architecture dependent packages that "
                            "should be built for the build architecture. "
                            "This option is ignored"),
                      action="store", type="string")

    parser.add_option('-i', '--indep', dest="indep",
                      help=("Act on all architecture independent packages. "
                            "This option is ignored"),
                      action="store_true")
    return parser

########NEW FILE########
__FILENAME__ = deployment
# -*- coding: utf-8 -*-
# Copyright (c) 2013 - 2014 Spotify AB

# This file is part of dh-virtualenv.

# dh-virtualenv is free software: you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation, either version 2 of the
# License, or (at your option) any later version.

# dh-virtualenv is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with dh-virtualenv. If not, see
# <http://www.gnu.org/licenses/>.

import os
import re
import shutil
import subprocess
import tempfile

ROOT_ENV_KEY = 'DH_VIRTUALENV_INSTALL_ROOT'
DEFAULT_INSTALL_DIR = '/usr/share/python/'


class Deployment(object):
    def __init__(self, package, extra_urls=None, preinstall=None, pypi_url=None,
                 setuptools=False, python=None, sourcedirectory=None, verbose=False):
        self.package = package
        install_root = os.environ.get(ROOT_ENV_KEY, DEFAULT_INSTALL_DIR)
        self.virtualenv_install_dir = os.path.join(install_root, self.package)
        self.debian_root = os.path.join(
            'debian', package, install_root.lstrip('/'))
        self.package_dir = os.path.join(self.debian_root, package)
        self.bin_dir = os.path.join(self.package_dir, 'bin')

        self.extra_urls = extra_urls if extra_urls is not None else []
        self.preinstall = preinstall if preinstall is not None else []
        self.pypi_url = pypi_url
        self.log_file = tempfile.NamedTemporaryFile()
        self.verbose = verbose
        self.setuptools = setuptools
        self.python = python
        self.sourcedirectory = '.' if sourcedirectory is None else sourcedirectory

    @classmethod
    def from_options(cls, package, options):
        verbose = options.verbose or os.environ.get('DH_VERBOSE') == '1'
        return cls(package,
                   extra_urls=options.extra_index_url,
                   preinstall=options.preinstall,
                   pypi_url=options.pypi_url,
                   setuptools=options.setuptools,
                   python=options.python,
                   sourcedirectory=options.sourcedirectory,
                   verbose=verbose)

    def clean(self):
        shutil.rmtree(self.debian_root)

    def create_virtualenv(self):
        virtualenv = ['virtualenv', '--no-site-packages']

        if self.setuptools:
            virtualenv.append('--setuptools')

        if self.verbose:
            virtualenv.append('--verbose')

        if self.python:
            virtualenv.extend(('--python', self.python))

        virtualenv.append(self.package_dir)
        subprocess.check_call(virtualenv)

        # We need to prefix the pip run with the location of python
        # executable. Otherwise it would just blow up due to too long
        # shebang-line.
        self.pip_prefix = [
            os.path.join(self.bin_dir, 'python'),
            os.path.join(self.bin_dir, 'pip'),
        ]
        if self.verbose:
            self.pip_prefix.append('-v')

        self.pip_prefix.append('install')

        if self.pypi_url:
            self.pip_prefix.append('--pypi-url={0}'.format(self.pypi_url))
        self.pip_prefix.extend([
            '--extra-index-url={0}'.format(url) for url in self.extra_urls
        ])
        self.pip_prefix.append('--log={0}'.format(self.log_file.name))

    def pip(self, *args):
        return self.pip_prefix + list(args)

    def install_dependencies(self):
        # Install preinstall stage packages. This is handy if you need
        # a custom package to install dependencies (think something
        # along lines of setuptools), but that does not get installed
        # by default virtualenv.
        if self.preinstall:
            subprocess.check_call(self.pip(*self.preinstall))

        requirements_path = os.path.join(self.sourcedirectory, 'requirements.txt')
        if os.path.exists(requirements_path):
            subprocess.check_call(self.pip('-r', requirements_path))

    def run_tests(self):
        python = os.path.join(self.bin_dir, 'python')
        setup_py = os.path.join(self.sourcedirectory, 'setup.py')
        if os.path.exists(setup_py):
            subprocess.check_call([python, 'setup.py', 'test'])

    def fix_shebangs(self):
        """Translate /usr/bin/python and /usr/bin/env python sheband
        lines to point to our virtualenv python.
        """
        grep_proc = subprocess.Popen(
            ['grep', '-l', '-r', '-e', r'^#!.*bin/\(env \)\?python',
             self.bin_dir],
            stdout=subprocess.PIPE
        )
        files, stderr = grep_proc.communicate()
        files = files.strip()
        if not files:
            return

        pythonpath = os.path.join(self.virtualenv_install_dir, 'bin/python')
        for f in files.split('\n'):
            subprocess.check_call(
                ['sed', '-i', r's|^#!.*bin/\(env \)\?python|#!{0}|'.format(
                    pythonpath),
                 f])

    def fix_activate_path(self):
        """Replace the `VIRTUAL_ENV` path in bin/activate to reflect the
        post-install path of the virtualenv.
        """
        virtualenv_path = 'VIRTUAL_ENV="{0}"'.format(
            self.virtualenv_install_dir)
        pattern = re.compile(r'^VIRTUAL_ENV=.*$', flags=re.M)

        with open(os.path.join(self.bin_dir, 'activate'), 'r+') as fh:
            content = pattern.sub(virtualenv_path, fh.read())
            fh.seek(0)
            fh.truncate()
            fh.write(content)

    def install_package(self):
        setup_path = os.path.join(self.sourcedirectory)
        subprocess.check_call(self.pip(setup_path))

    def fix_local_symlinks(self):
        # The virtualenv might end up with a local folder that points outside the package
        # Specifically it might point at the build environment that created it!
        # Make those links relative
        # See https://github.com/pypa/virtualenv/commit/5cb7cd652953441a6696c15bdac3c4f9746dfaa1
        local_dir = os.path.join(self.package_dir, "local")
        if not os.path.isdir(local_dir):
            return
        for d in os.listdir(local_dir):
            path = os.path.join(local_dir, d)
            if not os.path.islink(path):
                continue

            existing_target = os.readlink(path)
            if not os.path.isabs(existing_target):
                # If the symlink is already relative, we don't
                # want to touch it.
                continue

            new_target = os.path.relpath(existing_target, local_dir)
            os.unlink(path)
            os.symlink(new_target, path)

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# dh-virtualenv documentation build configuration file, created by
# sphinx-quickstart on Wed Feb 20 17:29:43 2013.
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
project = u'dh-virtualenv'
copyright = u'2013-2014 Spotify AB'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '0.7'
# The full version, including alpha/beta/rc tags.
release = '0.7'

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
htmlhelp_basename = 'dh-virtualenvdoc'


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
  ('index', 'dh-virtualenv.tex', u'dh-virtualenv Documentation',
   u'Spotify AB', 'manual'),
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
    ('index', 'dh-virtualenv', u'dh-virtualenv Documentation',
     [u'Spotify AB'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
    ('index', 'dh-virtualenv', u'dh-virtualenv Documentation',
     u'Spotify AB', 'dh-virtualenv',
     'Debian packaging sequence for Python virtualenvs.',
     'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'

########NEW FILE########
__FILENAME__ = test_cmdline
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2014 Spotify AB

# This file is part of dh-virtualenv.

# dh-virtualenv is free software: you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation, either version 2 of the
# License, or (at your option) any later version.

# dh-virtualenv is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with dh-virtualenv. If not, see
# <http://www.gnu.org/licenses/>.
import os

from dh_virtualenv import cmdline
from mock import patch
from nose.tools import eq_


@patch.object(cmdline.DebhelperOptionParser, 'error')
def test_unknown_argument_is_error(error_mock):
    parser = cmdline.DebhelperOptionParser(usage='foo')
    parser.parse_args(['-f'])
    eq_(1, error_mock.call_count)


def test_test_debhelper_option_parsing():
    parser = cmdline.DebhelperOptionParser()
    parser.add_option('--sourcedirectory')
    opts, args = parser.parse_args(['-O--sourcedirectory', '/tmp'])
    eq_('/tmp', opts.sourcedirectory)
    eq_([], args)


def test_parser_picks_up_DH_OPTIONS_from_environ():
    os.environ['DH_OPTIONS'] = '--sourcedirectory=/tmp/'
    parser = cmdline.get_default_parser()
    opts, args = parser.parse_args()
    eq_('/tmp/', opts.sourcedirectory)
    del os.environ['DH_OPTIONS']


def test_get_default_parser():
    parser = cmdline.get_default_parser()
    opts, args = parser.parse_args([
        '-O--sourcedirectory', '/tmp/foo',
        '--extra-index-url', 'http://example.com'
    ])
    eq_('/tmp/foo', opts.sourcedirectory)
    eq_(['http://example.com'], opts.extra_index_url)


def test_that_default_test_option_should_be_true():
    parser = cmdline.get_default_parser()
    opts, args = parser.parse_args()
    eq_(True, opts.test)


def test_that_test_option_can_be_false():
    parser = cmdline.get_default_parser()
    opts, args = parser.parse_args(['--no-test'])
    eq_(False, opts.test)

########NEW FILE########
__FILENAME__ = test_deployment
# -*- coding: utf-8 -*-
# Copyright (c) 2013-2014 Spotify AB

# This file is part of dh-virtualenv.

# dh-virtualenv is free software: you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation, either version 2 of the
# License, or (at your option) any later version.

# dh-virtualenv is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with dh-virtualenv. If not, see
# <http://www.gnu.org/licenses/>.

import functools
import os
import shutil
import tempfile
import textwrap

from mock import patch, call

from nose.tools import eq_
from dh_virtualenv import Deployment
from dh_virtualenv.cmdline import get_default_parser


class FakeTemporaryFile(object):
    name = 'foo'


def temporary_dir(fn):
    """Pass a temporary directory to the fn.

    This method makes sure it is destroyed at the end
    """
    @functools.wraps(fn)
    def _inner(*args, **kwargs):
        try:
            tempdir = tempfile.mkdtemp()
            return fn(tempdir, *args, **kwargs)
        finally:
            shutil.rmtree(tempdir)
    return _inner


def test_shebangs_fix():
    deployment = Deployment('test')
    temp = tempfile.NamedTemporaryFile()
    # We cheat here a little. The fix_shebangs walks through the
    # project directory, however we can just point to a single
    # file, as the underlying mechanism is just grep -r.
    deployment.bin_dir = temp.name

    with open(temp.name, 'w') as f:
        f.write('#!/usr/bin/python\n')

    deployment.fix_shebangs()

    with open(temp.name) as f:
        eq_('#!/usr/share/python/test/bin/python\n', f.read())

    with open(temp.name, 'w') as f:
        f.write('#!/usr/bin/env python\n')

    deployment.fix_shebangs()
    with open(temp.name) as f:
        eq_('#!/usr/share/python/test/bin/python\n', f.readline())


def test_shebangs_fix_overridden_root():
    os.environ['DH_VIRTUALENV_INSTALL_ROOT'] = 'foo'
    deployment = Deployment('test')
    temp = tempfile.NamedTemporaryFile()
    # We cheat here a little. The fix_shebangs walks through the
    # project directory, however we can just point to a single
    # file, as the underlying mechanism is just grep -r.
    deployment.bin_dir = temp.name

    with open(temp.name, 'w') as f:
        f.write('#!/usr/bin/python\n')

    deployment.fix_shebangs()

    with open(temp.name) as f:
        eq_('#!foo/test/bin/python\n', f.read())

    with open(temp.name, 'w') as f:
        f.write('#!/usr/bin/env python\n')

    deployment.fix_shebangs()
    with open(temp.name) as f:
        eq_('#!foo/test/bin/python\n', f.readline())
    del os.environ['DH_VIRTUALENV_INSTALL_ROOT']


@patch('os.path.exists', lambda x: False)
@patch('subprocess.check_call')
def test_install_dependencies_with_no_requirements(callmock):
    d = Deployment('test')
    d.pip_prefix = ['pip', 'install']
    d.install_dependencies()
    callmock.assert_has_calls([])


@patch('os.path.exists', lambda x: True)
@patch('subprocess.check_call')
def test_install_dependencies_with_requirements(callmock):
    d = Deployment('test')
    d.pip_prefix = ['pip', 'install']
    d.install_dependencies()
    callmock.assert_called_with(
        ['pip', 'install', '-r', './requirements.txt'])


@patch('subprocess.check_call')
def test_install_dependencies_with_preinstall(callmock):
    d = Deployment('test', preinstall=['foobar'])
    d.pip_prefix = ['pip', 'install']
    d.install_dependencies()
    callmock.assert_called_with(
        ['pip', 'install', 'foobar'])


@patch('os.path.exists', lambda x: True)
@patch('subprocess.check_call')
def test_install_dependencies_with_preinstall_with_requirements(callmock):
    d = Deployment('test', preinstall=['foobar'])
    d.pip_prefix = ['pip', 'install']
    d.install_dependencies()
    callmock.assert_has_calls([
        call(['pip', 'install', 'foobar']),
        call(['pip', 'install', '-r', './requirements.txt'])
    ])


@patch('tempfile.NamedTemporaryFile', FakeTemporaryFile)
@patch('subprocess.check_call')
def test_create_venv(callmock):
    d = Deployment('test')
    d.create_virtualenv()
    eq_('debian/test/usr/share/python/test', d.package_dir)
    callmock.assert_called_with(['virtualenv', '--no-site-packages',
                                 'debian/test/usr/share/python/test'])
    eq_(['debian/test/usr/share/python/test/bin/python',
         'debian/test/usr/share/python/test/bin/pip',
         'install',
         '--log=foo'], d.pip_prefix)


@patch('tempfile.NamedTemporaryFile', FakeTemporaryFile)
@patch('subprocess.check_call')
def test_create_venv_with_verbose(callmock):
    d = Deployment('test', verbose=True)
    d.create_virtualenv()
    eq_('debian/test/usr/share/python/test', d.package_dir)
    callmock.assert_called_with(['virtualenv', '--no-site-packages',
                                 '--verbose',
                                 'debian/test/usr/share/python/test'])
    eq_(['debian/test/usr/share/python/test/bin/python',
         'debian/test/usr/share/python/test/bin/pip',
         '-v',
         'install',
         '--log=foo'], d.pip_prefix)


@patch('tempfile.NamedTemporaryFile', FakeTemporaryFile)
@patch('subprocess.check_call')
def test_create_venv_with_extra_urls(callmock):
    d = Deployment('test', extra_urls=['foo', 'bar'])
    d.create_virtualenv()
    eq_('debian/test/usr/share/python/test', d.package_dir)
    callmock.assert_called_with(['virtualenv', '--no-site-packages',
                                 'debian/test/usr/share/python/test'])
    eq_(['debian/test/usr/share/python/test/bin/python',
         'debian/test/usr/share/python/test/bin/pip',
         'install', '--extra-index-url=foo',
         '--extra-index-url=bar',
         '--log=foo'], d.pip_prefix)


@patch('tempfile.NamedTemporaryFile', FakeTemporaryFile)
@patch('subprocess.check_call')
def test_create_venv_with_custom_index_url(callmock):
    d = Deployment('test', extra_urls=['foo', 'bar'],
                   pypi_url='http://example.com/simple')
    d.create_virtualenv()
    eq_('debian/test/usr/share/python/test', d.package_dir)
    callmock.assert_called_with(['virtualenv', '--no-site-packages',
                                 'debian/test/usr/share/python/test'])
    eq_(['debian/test/usr/share/python/test/bin/python',
         'debian/test/usr/share/python/test/bin/pip',
         'install',
         '--pypi-url=http://example.com/simple',
         '--extra-index-url=foo',
         '--extra-index-url=bar',
         '--log=foo'], d.pip_prefix)


@patch('tempfile.NamedTemporaryFile', FakeTemporaryFile)
@patch('subprocess.check_call')
def test_create_venv_with_setuptools(callmock):
    d = Deployment('test', setuptools=True)
    d.create_virtualenv()
    eq_('debian/test/usr/share/python/test', d.package_dir)
    callmock.assert_called_with(['virtualenv', '--no-site-packages',
                                 '--setuptools',
                                 'debian/test/usr/share/python/test'])
    eq_(['debian/test/usr/share/python/test/bin/python',
         'debian/test/usr/share/python/test/bin/pip',
         'install',
         '--log=foo'], d.pip_prefix)


@patch('tempfile.NamedTemporaryFile', FakeTemporaryFile)
@patch('subprocess.check_call')
def test_venv_with_custom_python(callmock):
    d = Deployment('test', python='/tmp/python')
    d.create_virtualenv()
    eq_('debian/test/usr/share/python/test', d.package_dir)
    callmock.assert_called_with(['virtualenv', '--no-site-packages',
                                 '--python', '/tmp/python',
                                 'debian/test/usr/share/python/test'])
    eq_(['debian/test/usr/share/python/test/bin/python',
         'debian/test/usr/share/python/test/bin/pip',
         'install',
         '--log=foo'], d.pip_prefix)


@patch('tempfile.NamedTemporaryFile', FakeTemporaryFile)
@patch('subprocess.check_call')
def test_install_package(callmock):
    d = Deployment('test')
    d.bin_dir = 'derp'
    d.pip_prefix = ['derp/python', 'derp/pip']
    d.install_package()
    callmock.assert_called_with([
        'derp/python', 'derp/pip', '.',
    ])


def test_fix_activate_path():
    deployment = Deployment('test')
    temp = tempfile.NamedTemporaryFile()

    with open(temp.name, 'w') as fh:
        fh.write(textwrap.dedent("""
            other things

            VIRTUAL_ENV="/this/path/is/wrong/and/longer/than/new/path"

            more other things
        """))

    expected = textwrap.dedent("""
        other things

        VIRTUAL_ENV="/usr/share/python/test"

        more other things
    """)

    with patch('dh_virtualenv.deployment.os.path.join',
               return_value=temp.name):
        deployment.fix_activate_path()

    with open(temp.name) as fh:
        eq_(expected, temp.read())


@patch('os.path.exists', lambda x: True)
@patch('tempfile.NamedTemporaryFile', FakeTemporaryFile)
@patch('subprocess.check_call')
def test_custom_src_dir(callmock):
    d = Deployment('test')
    d.pip_prefix = ['pip', 'install']
    d.sourcedirectory = 'root/srv/application'
    d.create_virtualenv()
    d.install_dependencies()
    callmock.assert_called_with([
        'debian/test/usr/share/python/test/bin/python',
        'debian/test/usr/share/python/test/bin/pip',
        'install',
        '--log=foo',
        '-r',
        'root/srv/application/requirements.txt'],
    )
    d.install_package()
    callmock.assert_called_with([
        'debian/test/usr/share/python/test/bin/python',
        'debian/test/usr/share/python/test/bin/pip',
        'install',
        '--log=foo',
        'root/srv/application',
    ])


@patch('os.path.exists', lambda *a: True)
@patch('subprocess.check_call')
def test_testrunner(callmock):
    d = Deployment('test')
    d.run_tests()
    callmock.assert_called_once_with([
        'debian/test/usr/share/python/test/bin/python',
        'setup.py',
        'test',
    ])


@patch('os.path.exists', lambda *a: False)
@patch('subprocess.check_call')
def test_testrunner_setuppy_not_found(callmock):
    d = Deployment('test')
    d.run_tests()
    eq_(callmock.call_count, 0)


def test_deployment_from_options():
        options, _ = get_default_parser().parse_args([
            '--extra-index-url', 'http://example.com',
            '-O--pypi-url', 'http://example.org'
        ])
        d = Deployment.from_options('foo', options)
        eq_(d.package, 'foo')
        eq_(d.pypi_url, 'http://example.org')
        eq_(d.extra_urls, ['http://example.com'])


def test_deployment_from_options_with_verbose():
        options, _ = get_default_parser().parse_args([
            '--verbose'
        ])
        d = Deployment.from_options('foo', options)
        eq_(d.package, 'foo')
        eq_(d.verbose, True)


@patch('os.environ.get')
def test_deployment_from_options_with_verbose_from_env(env_mock):
        env_mock.return_value = '1'
        options, _ = get_default_parser().parse_args([])
        d = Deployment.from_options('foo', options)
        eq_(d.package, 'foo')
        eq_(d.verbose, True)


@temporary_dir
def test_fix_local_symlinks(deployment_dir):
        d = Deployment('testing')
        d.package_dir = deployment_dir

        local = os.path.join(deployment_dir, 'local')
        os.makedirs(local)
        target = os.path.join(deployment_dir, 'sometarget')
        symlink = os.path.join(local, 'symlink')
        os.symlink(target, symlink)

        d.fix_local_symlinks()
        eq_(os.readlink(symlink), '../sometarget')


@temporary_dir
def test_fix_local_symlinks_with_relative_links(deployment_dir):
        # Runs shouldn't ruin the already relative symlinks.
        d = Deployment('testing')
        d.package_dir = deployment_dir

        local = os.path.join(deployment_dir, 'local')
        os.makedirs(local)
        symlink = os.path.join(local, 'symlink')
        os.symlink('../target', symlink)

        d.fix_local_symlinks()
        eq_(os.readlink(symlink), '../target')


@temporary_dir
def test_fix_local_symlinks_does_not_blow_up_on_missing_local(deployment_dir):
        d = Deployment('testing')
        d.package_dir = deployment_dir
        d.fix_local_symlinks()

########NEW FILE########
