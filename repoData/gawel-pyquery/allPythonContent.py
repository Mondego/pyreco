__FILENAME__ = bootstrap-py3k
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

import os, shutil, sys, tempfile, textwrap
try:
    import urllib.request as urllib2
except ImportError:
    import urllib2
import subprocess
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
    [sys.executable, '-S', '-c',
     'try:\n'
     '    import pickle\n'
     'except ImportError:\n'
     '    print(1)\n'
     'else:\n'
     '    print(0)\n'],
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
    args = list(map(quote, args))
    os.execv(sys.executable, args)

# Now we are running with -S.  We'll get the clean sys.path, import site
# because distutils will do it later, and then reset the path and clean
# out any namespace packages from site-packages that might have been
# loaded by .pth files.
clean_path = sys.path[:]
import site
sys.path[:] = clean_path
for k, v in list(sys.modules.items()):
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
                urllib2.pathname2url(
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
parser.add_option("--setup-version", dest="setup_version",
                  help="The version of setuptools or distribute to use.")
parser.add_option("-d", "--distribute",
                   action="store_true", dest="use_distribute",
                   default= sys.version_info[0] >= 3,
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
                  action="store_true",
                  default=sys.version_info[0] > 2,
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
        options.setup_source).read().replace('\r\n'.encode(), '\n'.encode())
    ez = {}
    exec(ez_code, ez)
    setup_args = dict(to_dir=eggs_dir, download_delay=0)
    if options.download_base:
        setup_args['download_base'] = options.download_base
    if options.setup_version:
        setup_args['version'] = options.setup_version
    if options.use_distribute:
        setup_args['no_fake'] = True
    ez['use_setuptools'](**setup_args)
    if 'pkg_resources' in sys.modules:
        if sys.version_info[0] >= 3:
            import imp
            reload_ = imp.reload
        else:
            reload_ = reload

        reload_(sys.modules['pkg_resources'])
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
    print("An error occurred when trying to install zc.buildout. "
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
                   action="store_true", dest="use_distribute", default=False,
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
__FILENAME__ = ajax_fixt
# -*- coding: utf-8 -*-
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from webtest import http
from doctest import SKIP
from tests.apps import input_app

PY3 = sys.version_info >= (3,)


def setup_test(test):
    for example in test.examples:
        # urlopen as moved in py3
        if PY3:
            example.options.setdefault(SKIP, 1)
    if not PY3:
        server = http.StopableWSGIServer.create(input_app)
        server.wait()
        path_to_html_file = os.path.join('tests', 'test.html')
        test.globs.update(
            input_app=input_app,
            server=server,
            your_url=server.application_url.rstrip('/') + '/html',
            path_to_html_file=path_to_html_file,
        )
setup_test.__test__ = False


def teardown_test(test):
    if 'server' in test.globs:
        test.globs['server'].shutdown()
teardown_test.__test__ = False

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# pyquery documentation build configuration file, created by
# sphinx-quickstart on Thu Nov  1 21:48:09 2012.
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
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.viewcode']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'pyquery'
copyright = u'2012, Olivier Lauzanne'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '0.3'
# The full version, including alpha/beta/rc tags.
release = '0.3'

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
html_theme = 'nature'

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
htmlhelp_basename = 'pyquerydoc'


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
  ('index', 'pyquery.tex', u'pyquery Documentation',
   u'Olivier Lauzanne', 'manual'),
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
    ('index', 'pyquery', u'pyquery Documentation',
     [u'Olivier Lauzanne'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'pyquery', u'pyquery Documentation',
   u'Olivier Lauzanne', 'pyquery', 'One line description of project.',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'

from os import path
pkg_dir = path.abspath(__file__).split('/docs')[0]
setup = path.join(pkg_dir, 'setup.py')
if path.isfile(setup):
    for line_ in open(setup):
        if line_.startswith("version"):
            version = line_.split('=')[-1]
            version = version.strip()
            version = version.strip("'\"")
            release = version
            break
del pkg_dir, setup, path

from pyquery.cssselectpatch import JQueryTranslator

with open('pseudo_classes.rst', 'w') as fd:
    fd.write('=========================\n')
    fd.write('Using pseudo classes\n')
    fd.write('=========================\n')
    for k in sorted(dir(JQueryTranslator)):
        if k.startswith('xpath_'):
            attr = getattr(JQueryTranslator, k)
            doc = getattr(attr, '__doc__', '') or ''
            doc = doc.strip()
            if doc.startswith('Common implementation'):
                continue
            k = k[6:]
            if '_' not in k or not doc:
                continue
            k, t = k.split('_', 1)
            if '_' in t:
                continue
            if t == 'function':
                k += '()'
            fd.write('\n\n:%s\n' % k)
            fd.write('==================\n\n')
            fd.write(doc.strip('..').replace('        ', '    '))

########NEW FILE########
__FILENAME__ = scrap_fixt
# -*- coding: utf-8 -*-
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from webtest import http
from tests.apps import input_app


def setup_test(test):
    server = http.StopableWSGIServer.create(input_app)
    server.wait()
    test.globs.update(
        server=server,
        your_url=server.application_url.rstrip('/') + '/html',
    )
setup_test.__test__ = False


def teardown_test(test):
    test.globs['server'].shutdown()
teardown_test.__test__ = False

########NEW FILE########
__FILENAME__ = tips_fixt
# -*- coding: utf-8 -*-
import os
from webtest import http
from webtest.debugapp import debug_app


def setup_test(test):
    server = http.StopableWSGIServer.create(debug_app)
    server.wait()
    path_to_html_file = os.path.join('tests', 'test.html')
    test.globs.update(
        server=server,
        your_url=server.application_url.rstrip('/') + '/form.html',
        path_to_html_file=path_to_html_file,
    )
setup_test.__test__ = False


def teardown_test(test):
    test.globs['server'].shutdown()
teardown_test.__test__ = False

########NEW FILE########
__FILENAME__ = ajax
# -*- coding: utf-8 -*-
from .pyquery import PyQuery as Base
from .pyquery import no_default

from webob import Request
from webob import Response

try:
    from restkit.contrib.wsgi_proxy import HostProxy
except ImportError:
    HostProxy = no_default  # NOQA


class PyQuery(Base):

    def __init__(self, *args, **kwargs):
        if 'response' in kwargs:
            self.response = kwargs.pop('response')
        else:
            self.response = Response()
        if 'app' in kwargs:
            self.app = kwargs.pop('app')
            if len(args) == 0:
                args = [[]]
        else:
            self.app = no_default
        Base.__init__(self, *args, **kwargs)
        if self._parent is not no_default:
            self.app = self._parent.app

    def _wsgi_get(self, path_info, **kwargs):
        if path_info.startswith('/'):
            if 'app' in kwargs:
                app = kwargs.pop('app')
            elif self.app is not no_default:
                app = self.app
            else:
                raise ValueError('There is no app available')
        else:
            if HostProxy is not no_default:
                app = HostProxy(path_info)
                path_info = '/'
            else:
                raise ImportError('restkit is not installed')

        environ = kwargs.pop('environ').copy()
        environ.update(kwargs)

        # unsuported (came from Deliverance)
        for key in ['HTTP_ACCEPT_ENCODING', 'HTTP_IF_MATCH',
                    'HTTP_IF_UNMODIFIED_SINCE', 'HTTP_RANGE', 'HTTP_IF_RANGE']:
            if key in environ:
                del environ[key]

        req = Request.blank(path_info)
        req.environ.update(environ)
        resp = req.get_response(app)
        status = resp.status.split()
        ctype = resp.content_type.split(';')[0]
        if status[0] not in '45' and ctype == 'text/html':
            body = resp.body
        else:
            body = []
        result = self.__class__(body,
                                parent=self._parent,
                                app=self.app,  # always return self.app
                                response=resp)
        return result

    def get(self, path_info, **kwargs):
        """GET a path from wsgi app or url
        """
        environ = kwargs.setdefault('environ', {})
        environ['REQUEST_METHOD'] = 'GET'
        environ['CONTENT_LENGTH'] = '0'
        return self._wsgi_get(path_info, **kwargs)

    def post(self, path_info, **kwargs):
        """POST a path from wsgi app or url
        """
        environ = kwargs.setdefault('environ', {})
        environ['REQUEST_METHOD'] = 'POST'
        return self._wsgi_get(path_info, **kwargs)

########NEW FILE########
__FILENAME__ = cssselectpatch
#-*- coding:utf-8 -*-
#
# Copyright (C) 2008 - Olivier Lauzanne <olauzanne@gmail.com>
#
# Distributed under the BSD license, see LICENSE.txt
from __future__ import unicode_literals
from cssselect import xpath as cssselect_xpath
from cssselect.xpath import ExpressionError

XPathExprOrig = cssselect_xpath.XPathExpr


class XPathExpr(XPathExprOrig):

    def __init__(self, path='', element='*', condition='', star_prefix=False):
        self.path = path
        self.element = element
        self.condition = condition
        self.post_condition = None

    def add_post_condition(self, post_condition):
        if self.post_condition:
            self.post_condition = '%s and (%s)' % (self.post_condition,
                                                   post_condition)
        else:
            self.post_condition = post_condition

    def __str__(self):
        path = XPathExprOrig.__str__(self)
        if self.post_condition:
            path = '%s[%s]' % (path, self.post_condition)
        return path

    def join(self, combiner, other):
        res = XPathExprOrig.join(self, combiner, other)
        self.post_condition = other.post_condition
        return res


# keep cssselect < 0.8 compat for now


class JQueryTranslator(cssselect_xpath.HTMLTranslator):
    """This class is used to implement the css pseudo classes
    (:first, :last, ...) that are not defined in the css standard,
    but are defined in the jquery API.
    """

    xpathexpr_cls = XPathExpr

    def xpath_first_pseudo(self, xpath):
        """Matches the first selected element::

            >>> from pyquery import PyQuery
            >>> d = PyQuery('<div><p class="first"></p><p></p></div>')
            >>> d('p:first')
            [<p.first>]

        ..
        """
        xpath.add_post_condition('position() = 1')
        return xpath

    def xpath_last_pseudo(self, xpath):
        """Matches the last selected element::

            >>> from pyquery import PyQuery
            >>> d = PyQuery('<div><p></p><p class="last"></p></div>')
            >>> d('p:last')
            [<p.last>]

        ..
        """
        xpath.add_post_condition('position() = last()')
        return xpath

    def xpath_even_pseudo(self, xpath):
        """Matches even elements, zero-indexed::

            >>> from pyquery import PyQuery
            >>> d = PyQuery('<div><p></p><p class="last"></p></div>')
            >>> d('p:even')
            [<p>]

        ..
        """
        # the first element is 1 in xpath and 0 in python and js
        xpath.add_post_condition('position() mod 2 = 1')
        return xpath

    def xpath_odd_pseudo(self, xpath):
        """Matches odd elements, zero-indexed::

            >>> from pyquery import PyQuery
            >>> d = PyQuery('<div><p></p><p class="last"></p></div>')
            >>> d('p:odd')
            [<p.last>]

        ..
        """
        xpath.add_post_condition('position() mod 2 = 0')
        return xpath

    def xpath_checked_pseudo(self, xpath):
        """Matches odd elements, zero-indexed::

            >>> from pyquery import PyQuery
            >>> d = PyQuery('<div><input checked="checked"/></div>')
            >>> d('input:checked')
            [<input>]

        ..
        """
        xpath.add_condition("@checked and name(.) = 'input'")
        return xpath

    def xpath_selected_pseudo(self, xpath):
        """Matches all elements that are selected::

            >>> from pyquery import PyQuery
            >>> d = PyQuery('<select><option selected="selected"/></select>')
            >>> d('option:selected')
            [<option>]

        ..
        """
        xpath.add_condition("@selected and name(.) = 'option'")
        return xpath

    def xpath_disabled_pseudo(self, xpath):
        """Matches all elements that are disabled::

            >>> from pyquery import PyQuery
            >>> d = PyQuery('<div><input disabled="disabled"/></div>')
            >>> d('input:disabled')
            [<input>]

        ..
        """
        xpath.add_condition("@disabled")
        return xpath

    def xpath_enabled_pseudo(self, xpath):
        """Matches all elements that are enabled::

            >>> from pyquery import PyQuery
            >>> d = PyQuery('<div><input value="foo" /></div>')
            >>> d('input:enabled')
            [<input>]

        ..
        """
        xpath.add_condition("not(@disabled) and name(.) = 'input'")
        return xpath

    def xpath_file_pseudo(self, xpath):
        """Matches all input elements of type file::

            >>> from pyquery import PyQuery
            >>> d = PyQuery('<div><input type="file"/></div>')
            >>> d('input:file')
            [<input>]

        ..
        """
        xpath.add_condition("@type = 'file' and name(.) = 'input'")
        return xpath

    def xpath_input_pseudo(self, xpath):
        """Matches all input elements::

            >>> from pyquery import PyQuery
            >>> d = PyQuery(('<div><input type="file"/>'
            ...              '<textarea></textarea></div>'))
            >>> d(':input')
            [<input>, <textarea>]

        ..
        """
        xpath.add_condition((
            "(name(.) = 'input' or name(.) = 'select') "
            "or (name(.) = 'textarea' or name(.) = 'button')"))
        return xpath

    def xpath_button_pseudo(self, xpath):
        """Matches all button input elements and the button element::

            >>> from pyquery import PyQuery
            >>> d = PyQuery(('<div><input type="button"/>'
            ...              '<button></button></div>'))
            >>> d(':button')
            [<input>, <button>]

        ..
        """
        xpath.add_condition((
            "(@type = 'button' and name(.) = 'input') "
            "or name(.) = 'button'"))
        return xpath

    def xpath_radio_pseudo(self, xpath):
        """Matches all radio input elements::

            >>> from pyquery import PyQuery
            >>> d = PyQuery('<div><input type="radio"/></div>')
            >>> d('input:radio')
            [<input>]

        ..
        """
        xpath.add_condition("@type = 'radio' and name(.) = 'input'")
        return xpath

    def xpath_text_pseudo(self, xpath):
        """Matches all text input elements::

            >>> from pyquery import PyQuery
            >>> d = PyQuery('<div><input type="text"/></div>')
            >>> d('input:text')
            [<input>]

        ..
        """
        xpath.add_condition("@type = 'text' and name(.) = 'input'")
        return xpath

    def xpath_checkbox_pseudo(self, xpath):
        """Matches all checkbox input elements::

            >>> from pyquery import PyQuery
            >>> d = PyQuery('<div><input type="checkbox"/></div>')
            >>> d('input:checkbox')
            [<input>]

        ..
        """
        xpath.add_condition("@type = 'checkbox' and name(.) = 'input'")
        return xpath

    def xpath_password_pseudo(self, xpath):
        """Matches all password input elements::

            >>> from pyquery import PyQuery
            >>> d = PyQuery('<div><input type="password"/></div>')
            >>> d('input:password')
            [<input>]

        ..
        """
        xpath.add_condition("@type = 'password' and name(.) = 'input'")
        return xpath

    def xpath_submit_pseudo(self, xpath):
        """Matches all submit input elements::

            >>> from pyquery import PyQuery
            >>> d = PyQuery('<div><input type="submit"/></div>')
            >>> d('input:submit')
            [<input>]

        ..
        """
        xpath.add_condition("@type = 'submit' and name(.) = 'input'")
        return xpath

    def xpath_hidden_pseudo(self, xpath):
        """Matches all hidden input elements::

            >>> from pyquery import PyQuery
            >>> d = PyQuery('<div><input type="hidden"/></div>')
            >>> d('input:hidden')
            [<input>]

        ..
        """
        xpath.add_condition("@type = 'hidden' and name(.) = 'input'")
        return xpath

    def xpath_image_pseudo(self, xpath):
        """Matches all image input elements::

            >>> from pyquery import PyQuery
            >>> d = PyQuery('<div><input type="image"/></div>')
            >>> d('input:image')
            [<input>]

        ..
        """
        xpath.add_condition("@type = 'image' and name(.) = 'input'")
        return xpath

    def xpath_reset_pseudo(self, xpath):
        """Matches all reset input elements::

            >>> from pyquery import PyQuery
            >>> d = PyQuery('<div><input type="reset"/></div>')
            >>> d('input:reset')
            [<input>]

        ..
        """
        xpath.add_condition("@type = 'reset' and name(.) = 'input'")
        return xpath

    def xpath_header_pseudo(self, xpath):
        """Matches all header elelements (h1, ..., h6)::

            >>> from pyquery import PyQuery
            >>> d = PyQuery('<div><h1>title</h1></div>')
            >>> d(':header')
            [<h1>]

        ..
        """
        # this seems kind of brute-force, is there a better way?
        xpath.add_condition((
            "(name(.) = 'h1' or name(.) = 'h2' or name (.) = 'h3') "
            "or (name(.) = 'h4' or name (.) = 'h5' or name(.) = 'h6')"))
        return xpath

    def xpath_parent_pseudo(self, xpath):
        """Match all elements that contain other elements::

            >>> from pyquery import PyQuery
            >>> d = PyQuery('<div><h1><span>title</span></h1><h1/></div>')
            >>> d('h1:parent')
            [<h1>]

        ..
        """
        xpath.add_condition("count(child::*) > 0")
        return xpath

    def xpath_empty_pseudo(self, xpath):
        """Match all elements that do not contain other elements::

            >>> from pyquery import PyQuery
            >>> d = PyQuery('<div><h1><span>title</span></h1><h2/></div>')
            >>> d(':empty')
            [<span>, <h2>]

        ..
        """
        xpath.add_condition("count(child::*) = 0")
        return xpath

    def xpath_eq_function(self, xpath, function):
        """Matches a single element by its index::

            >>> from pyquery import PyQuery
            >>> d = PyQuery('<div><h1 class="first"/><h1 class="last"/></div>')
            >>> d('h1:eq(0)')
            [<h1.first>]
            >>> d('h1:eq(1)')
            [<h1.last>]

        ..
        """
        if function.argument_types() != ['NUMBER']:
            raise ExpressionError(
                "Expected a single integer for :eq(), got %r" % (
                    function.arguments,))
        value = int(function.arguments[0].value)
        xpath.add_post_condition('position() = %s' % (value + 1))
        return xpath

    def xpath_gt_function(self, xpath, function):
        """Matches all elements with an index over the given one::

            >>> from pyquery import PyQuery
            >>> d = PyQuery('<div><h1 class="first"/><h1 class="last"/></div>')
            >>> d('h1:gt(0)')
            [<h1.last>]

        ..
        """
        if function.argument_types() != ['NUMBER']:
            raise ExpressionError(
                "Expected a single integer for :gt(), got %r" % (
                    function.arguments,))
        value = int(function.arguments[0].value)
        xpath.add_post_condition('position() > %s' % (value + 1))
        return xpath

    def xpath_lt_function(self, xpath, function):
        """Matches all elements with an index below the given one::

            >>> from pyquery import PyQuery
            >>> d = PyQuery('<div><h1 class="first"/><h1 class="last"/></div>')
            >>> d('h1:lt(1)')
            [<h1.first>]

        ..
        """
        if function.argument_types() != ['NUMBER']:
            raise ExpressionError(
                "Expected a single integer for :gt(), got %r" % (
                    function.arguments,))

        value = int(function.arguments[0].value)
        xpath.add_post_condition('position() < %s' % (value + 1))
        return xpath

    def xpath_contains_function(self, xpath, function):
        """Matches all elements that contain the given text

            >>> from pyquery import PyQuery
            >>> d = PyQuery('<div><h1/><h1 class="title">title</h1></div>')
            >>> d(':contains("title")')
            [<h1.title>]

        ..
        """
        if function.argument_types() != ['STRING']:
            raise ExpressionError(
                "Expected a single string for :contains(), got %r" % (
                    function.arguments,))

        value = self.xpath_literal(function.arguments[0].value)
        xpath.add_post_condition("contains(text(), %s)" % value)
        return xpath

########NEW FILE########
__FILENAME__ = openers
# -*- coding: utf-8 -*-
import sys

PY3k = sys.version_info >= (3,)

if PY3k:
    from urllib.request import urlopen
    from urllib.parse import urlencode
    basestring = (str, bytes)
else:
    from urllib2 import urlopen  # NOQA
    from urllib import urlencode  # NOQA

try:
    import requests
    HAS_REQUEST = True
except ImportError:
    HAS_REQUEST = False


allowed_args = (
    'auth', 'data', 'headers', 'verify', 'cert', 'config', 'hooks', 'proxies')


def _query(url, method, kwargs):
    data = None
    if 'data' in kwargs:
        data = kwargs.pop('data')
    if type(data) in (dict, list, tuple):
        data = urlencode(data)

    if isinstance(method, basestring) and \
       method.lower() == 'get' and data:
        if '?' not in url:
            url += '?'
        elif url[-1] not in ('?', '&'):
            url += '&'
        url += data
        data = None

    if data and PY3k:
        data = data.encode('utf-8')
    return url, data


def _requests(url, kwargs):
    encoding = kwargs.get('encoding')
    method = kwargs.get('method', 'get').lower()
    meth = getattr(requests, str(method))
    if method == 'get':
        url, data = _query(url, method, kwargs)
    kw = {}
    for k in allowed_args:
        if k in kwargs:
            kw[k] = kwargs[k]
    resp = meth(url=url, **kw)
    if encoding:
        resp.encoding = encoding
    html = resp.text
    return html


def _urllib(url, kwargs):
    method = kwargs.get('method')
    url, data = _query(url, method, kwargs)
    return urlopen(url, data)


def url_opener(url, kwargs):
    if HAS_REQUEST:
        return _requests(url, kwargs)
    return _urllib(url, kwargs)

########NEW FILE########
__FILENAME__ = pyquery
#-*- coding:utf-8 -*-
#
# Copyright (C) 2008 - Olivier Lauzanne <olauzanne@gmail.com>
#
# Distributed under the BSD license, see LICENSE.txt
from .cssselectpatch import JQueryTranslator
from .openers import url_opener
from copy import deepcopy
from lxml import etree
import lxml.html
import inspect
import types
import sys


PY3k = sys.version_info >= (3,)

if PY3k:
    from urllib.parse import urlencode
    from urllib.parse import urljoin
    basestring = (str, bytes)
    unicode = str
else:
    from urllib import urlencode  # NOQA
    from urlparse import urljoin  # NOQA


def func_globals(f):
    return f.__globals__ if PY3k else f.func_globals


def func_code(f):
    return f.__code__ if PY3k else f.func_code


def with_camel_case_alias(func):
    """decorator for methods who required a camelcase alias"""
    _camel_case_aliases.add(func.__name__)
    return func
_camel_case_aliases = set()


def build_camel_case_aliases(PyQuery):
    """add camelcase aliases to PyQuery"""
    for alias in _camel_case_aliases:
        parts = list(alias.split('_'))
        name = parts[0] + ''.join([p.title() for p in parts[1:]])
        func = getattr(PyQuery, alias)
        f = types.FunctionType(func_code(func), func_globals(func),
                               name, inspect.getargspec(func).defaults)
        f.__doc__ = (
            'Alias for :func:`~pyquery.pyquery.PyQuery.%s`') % func.__name__
        setattr(PyQuery, name, f.__get__(None, PyQuery))


def fromstring(context, parser=None, custom_parser=None):
    """use html parser if we don't have clean xml
    """
    if hasattr(context, 'read') and hasattr(context.read, '__call__'):
        meth = 'parse'
    else:
        meth = 'fromstring'
    if custom_parser is None:
        if parser is None:
            try:
                result = getattr(etree, meth)(context)
            except etree.XMLSyntaxError:
                if hasattr(context, 'seek'):
                    context.seek(0)
                result = getattr(lxml.html, meth)(context)
            if isinstance(result, etree._ElementTree):
                return [result.getroot()]
            else:
                return [result]
        elif parser == 'xml':
            custom_parser = getattr(etree, meth)
        elif parser == 'html':
            custom_parser = getattr(lxml.html, meth)
        elif parser == 'html5':
            from lxml.html import html5parser
            custom_parser = getattr(html5parser, meth)
        elif parser == 'soup':
            from lxml.html import soupparser
            custom_parser = getattr(soupparser, meth)
        elif parser == 'html_fragments':
            custom_parser = lxml.html.fragments_fromstring
        else:
            raise ValueError('No such parser: "%s"' % parser)

    result = custom_parser(context)
    if type(result) is list:
        return result
    elif isinstance(result, etree._ElementTree):
        return [result.getroot()]
    elif result is not None:
        return [result]
    else:
        return []


def callback(func, *args):
    return func(*args[:func_code(func).co_argcount])


class NoDefault(object):
    def __repr__(self):
        """clean representation in Sphinx"""
        return '<NoDefault>'

no_default = NoDefault()
del NoDefault


class FlexibleElement(object):
    """property to allow a flexible api"""
    def __init__(self, pget, pset=no_default, pdel=no_default):
        self.pget = pget
        self.pset = pset
        self.pdel = pdel

    def __get__(self, instance, klass):
        class _element(object):
            """real element to support set/get/del attr and item and js call
            style"""
            def __call__(prop, *args, **kwargs):
                return self.pget(instance, *args, **kwargs)
            __getattr__ = __getitem__ = __setattr__ = __setitem__ = __call__

            def __delitem__(prop, name):
                if self.pdel is not no_default:
                    return self.pdel(instance, name)
                else:
                    raise NotImplementedError()
            __delattr__ = __delitem__

            def __repr__(prop):
                return '<flexible_element %s>' % self.pget.__name__
        return _element()

    def __set__(self, instance, value):
        if self.pset is not no_default:
            self.pset(instance, value)
        else:
            raise NotImplementedError()


class PyQuery(list):
    """The main class
    """

    _translator_class = JQueryTranslator

    def __init__(self, *args, **kwargs):
        html = None
        elements = []
        self._base_url = None
        self.parser = kwargs.pop('parser', None)

        if (len(args) >= 1 and
                (not PY3k and isinstance(args[0], basestring) or
                (PY3k and isinstance(args[0], str))) and
                args[0].split('://', 1)[0] in ('http', 'https')):
            kwargs['url'] = args[0]
            if len(args) >= 2:
                kwargs['data'] = args[1]
            args = []

        if 'parent' in kwargs:
            self._parent = kwargs.pop('parent')
        else:
            self._parent = no_default

        if 'css_translator' in kwargs:
            self._translator = kwargs.pop('css_translator')
        elif self.parser in ('xml',):
            self._translator = self._translator_class(xhtml=True)
        elif self._parent is not no_default:
            self._translator = self._parent._translator
        else:
            self._translator = self._translator_class(xhtml=False)

        namespaces = kwargs.pop('namespaces', {})

        if kwargs:
            # specific case to get the dom
            if 'filename' in kwargs:
                html = open(kwargs['filename'])
            elif 'url' in kwargs:
                url = kwargs.pop('url')
                if 'opener' in kwargs:
                    opener = kwargs.pop('opener')
                    html = opener(url, **kwargs)
                else:
                    html = url_opener(url, kwargs)
                if not self.parser:
                    self.parser = 'html'
                self._base_url = url
            else:
                raise ValueError('Invalid keyword arguments %s' % kwargs)

            elements = fromstring(html, self.parser)
            # close open descriptor if possible
            if hasattr(html, 'close'):
                try:
                    html.close()
                except:
                    pass

        else:
            # get nodes

            # determine context and selector if any
            selector = context = no_default
            length = len(args)
            if length == 1:
                context = args[0]
            elif length == 2:
                selector, context = args
            else:
                raise ValueError(
                    "You can't do that. Please, provide arguments")

            # get context
            if isinstance(context, basestring):
                try:
                    elements = fromstring(context, self.parser)
                except Exception:
                    raise
            elif isinstance(context, self.__class__):
                # copy
                elements = context[:]
            elif isinstance(context, list):
                elements = context
            elif isinstance(context, etree._Element):
                elements = [context]

            # select nodes
            if elements and selector is not no_default:
                xpath = self._css_to_xpath(selector)
                results = []
                for tag in elements:
                    results.extend(tag.xpath(xpath, namespaces=namespaces))
                elements = results

        list.__init__(self, elements)

    def _css_to_xpath(self, selector, prefix='descendant-or-self::'):
        selector = selector.replace('[@', '[')
        return self._translator.css_to_xpath(selector, prefix)

    def __call__(self, *args, **kwargs):
        """return a new PyQuery instance
        """
        length = len(args)
        if length == 0:
            raise ValueError('You must provide at least a selector')
        if args[0] == '':
            return self.__class__([])
        if (len(args) == 1 and
                (not PY3k and isinstance(args[0], basestring) or
                (PY3k and isinstance(args[0], str))) and
                not args[0].startswith('<')):
            args += (self,)
        result = self.__class__(*args, parent=self, **kwargs)
        return result

    # keep original list api prefixed with _
    _append = list.append
    _extend = list.extend

    # improve pythonic api
    def __add__(self, other):
        assert isinstance(other, self.__class__)
        return self.__class__(self[:] + other[:])

    def extend(self, other):
        """Extend with anoter PyQuery object"""
        assert isinstance(other, self.__class__)
        self._extend(other[:])

    def items(self, selector=None):
        """Iter over elements. Return PyQuery objects:

            >>> d = PyQuery('<div><span>foo</span><span>bar</span></div>')
            >>> [i.text() for i in d.items('span')]
            ['foo', 'bar']
            >>> [i.text() for i in d('span').items()]
            ['foo', 'bar']
            >>> list(d.items('a')) == list(d('a').items())
            True
        """
        if selector:
            elems = self(selector) or []
        else:
            elems = self
        for elem in elems:
            yield self.__class__(elem)

    def xhtml_to_html(self):
        """Remove xhtml namespace:

            >>> doc = PyQuery(
            ...         '<html xmlns="http://www.w3.org/1999/xhtml"></html>')
            >>> doc
            [<{http://www.w3.org/1999/xhtml}html>]
            >>> doc.xhtml_to_html()
            [<html>]
        """
        try:
            root = self[0].getroottree()
        except IndexError:
            pass
        else:
            lxml.html.xhtml_to_html(root)
        return self

    def remove_namespaces(self):
        """Remove all namespaces:

            >>> doc = PyQuery('<foo xmlns="http://example.com/foo"></foo>')
            >>> doc
            [<{http://example.com/foo}foo>]
            >>> doc.remove_namespaces()
            [<foo>]
        """
        try:
            root = self[0].getroottree()
        except IndexError:
            pass
        else:
            for el in root.iter('{*}*'):
                if el.tag.startswith('{'):
                    el.tag = el.tag.split('}', 1)[1]
        return self

    def __str__(self):
        """xml representation of current nodes::

            >>> xml = PyQuery(
            ...   '<script><![[CDATA[ ]></script>', parser='html_fragments')
            >>> print(str(xml))
            <script>&lt;![[CDATA[ ]&gt;</script>

        """
        if PY3k:
            return ''.join([etree.tostring(e, encoding=str) for e in self])
        else:
            return ''.join([etree.tostring(e) for e in self])

    def __unicode__(self):
        """xml representation of current nodes"""
        return unicode('').join([etree.tostring(e, encoding=unicode)
                                 for e in self])

    def __html__(self):
        """html representation of current nodes::

            >>> html = PyQuery(
            ...   '<script><![[CDATA[ ]></script>', parser='html_fragments')
            >>> print(html.__html__())
            <script><![[CDATA[ ]></script>

        """
        return unicode('').join([lxml.html.tostring(e, encoding=unicode)
                                 for e in self])

    def __repr__(self):
        r = []
        try:
            for el in self:
                c = el.get('class')
                c = c and '.' + '.'.join(c.split(' ')) or ''
                id = el.get('id')
                id = id and '#' + id or ''
                r.append('<%s%s%s>' % (el.tag, id, c))
            return '[' + (', '.join(r)) + ']'
        except AttributeError:
            if PY3k:
                return list.__repr__(self)
            else:
                for el in self:
                    if isinstance(el, unicode):
                        r.append(el.encode('utf-8'))
                    else:
                        r.append(el)
                return repr(r)

    @property
    def root(self):
        """return the xml root element
        """
        if self._parent is not no_default:
            return self._parent.getroottree()
        return self[0].getroottree()

    @property
    def encoding(self):
        """return the xml encoding of the root element
        """
        root = self.root
        if root is not None:
            return self.root.docinfo.encoding

    ##############
    # Traversing #
    ##############

    def _filter_only(self, selector, elements, reverse=False, unique=False):
        """Filters the selection set only, as opposed to also including
           descendants.
        """
        if selector is None:
            results = elements
        else:
            xpath = self._css_to_xpath(selector, 'self::')
            results = []
            for tag in elements:
                results.extend(tag.xpath(xpath))
        if reverse:
            results.reverse()
        if unique:
            result_list = results
            results = []
            for item in result_list:
                if not item in results:
                    results.append(item)
        return self.__class__(results, **dict(parent=self))

    def parent(self, selector=None):
        return self._filter_only(
            selector,
            [e.getparent() for e in self if e.getparent() is not None],
            unique=True)

    def prev(self, selector=None):
        return self._filter_only(
            selector,
            [e.getprevious() for e in self if e.getprevious() is not None])

    def next(self, selector=None):
        return self._filter_only(
            selector,
            [e.getnext() for e in self if e.getnext() is not None])

    def _traverse(self, method):
        for e in self:
            current = getattr(e, method)()
            while current is not None:
                yield current
                current = getattr(current, method)()

    def _traverse_parent_topdown(self):
        for e in self:
            this_list = []
            current = e.getparent()
            while current is not None:
                this_list.append(current)
                current = current.getparent()
            this_list.reverse()
            for j in this_list:
                yield j

    def _next_all(self):
        return [e for e in self._traverse('getnext')]

    @with_camel_case_alias
    def next_all(self, selector=None):
        """
        >>> h = '<span><p class="hello">Hi</p><p>Bye</p><img scr=""/></span>'
        >>> d = PyQuery(h)
        >>> d('p:last').next_all()
        [<img>]
        >>> d('p:last').nextAll()
        [<img>]
        """
        return self._filter_only(selector, self._next_all())

    def _prev_all(self):
        return [e for e in self._traverse('getprevious')]

    @with_camel_case_alias
    def prev_all(self, selector=None):
        """
        >>> h = '<span><p class="hello">Hi</p><p>Bye</p><img scr=""/></span>'
        >>> d = PyQuery(h)
        >>> d('p:last').prev_all()
        [<p.hello>]
        >>> d('p:last').prevAll()
        [<p.hello>]
        """
        return self._filter_only(selector, self._prev_all(), reverse=True)

    def siblings(self, selector=None):
        """
         >>> h = '<span><p class="hello">Hi</p><p>Bye</p><img scr=""/></span>'
         >>> d = PyQuery(h)
         >>> d('.hello').siblings()
         [<p>, <img>]
         >>> d('.hello').siblings('img')
         [<img>]

        """
        return self._filter_only(selector, self._prev_all() + self._next_all())

    def parents(self, selector=None):
        """
        >>> d = PyQuery('<span><p class="hello">Hi</p><p>Bye</p></span>')
        >>> d('p').parents()
        [<span>]
        >>> d('.hello').parents('span')
        [<span>]
        >>> d('.hello').parents('p')
        []
        """
        return self._filter_only(
            selector,
            [e for e in self._traverse_parent_topdown()],
            unique=True
        )

    def children(self, selector=None):
        """Filter elements that are direct children of self using optional
        selector:

            >>> d = PyQuery('<span><p class="hello">Hi</p><p>Bye</p></span>')
            >>> d
            [<span>]
            >>> d.children()
            [<p.hello>, <p>]
            >>> d.children('.hello')
            [<p.hello>]
        """
        elements = [child for tag in self for child in tag.getchildren()]
        return self._filter_only(selector, elements)

    def closest(self, selector=None):
        """
        >>> d = PyQuery(
        ...  '<div class="hello"><p>This is a '
        ...  '<strong class="hello">test</strong></p></div>')
        >>> d('strong').closest('div')
        [<div.hello>]
        >>> d('strong').closest('.hello')
        [<strong.hello>]
        >>> d('strong').closest('form')
        []
        """
        result = []
        for current in self:
            while (current is not None and
                    not self.__class__(current).is_(selector)):
                current = current.getparent()
            if current is not None:
                result.append(current)
        return self.__class__(result, **dict(parent=self))

    def contents(self):
        """
        Return contents (with text nodes):

            >>> d = PyQuery('hello <b>bold</b>')
            >>> d.contents()  # doctest: +ELLIPSIS
            ['hello ', <Element b at ...>]
        """
        results = []
        for elem in self:
            results.extend(elem.xpath('child::text()|child::*'))
        return self.__class__(results, **dict(parent=self))

    def filter(self, selector):
        """Filter elements in self using selector (string or function):

            >>> d = PyQuery('<p class="hello">Hi</p><p>Bye</p>')
            >>> d('p')
            [<p.hello>, <p>]
            >>> d('p').filter('.hello')
            [<p.hello>]
            >>> d('p').filter(lambda i: i == 1)
            [<p>]
            >>> d('p').filter(lambda i: PyQuery(this).text() == 'Hi')
            [<p.hello>]
            >>> d('p').filter(lambda i, this: PyQuery(this).text() == 'Hi')
            [<p.hello>]
        """
        if not hasattr(selector, '__call__'):
            return self._filter_only(selector, self)
        else:
            elements = []
            args = inspect.getargspec(callback).args
            try:
                for i, this in enumerate(self):
                    if len(args) == 1:
                        func_globals(selector)['this'] = this
                    if callback(selector, i, this):
                        elements.append(this)
            finally:
                f_globals = func_globals(selector)
                if 'this' in f_globals:
                    del f_globals['this']
            return self.__class__(elements, **dict(parent=self))

    def not_(self, selector):
        """Return elements that don't match the given selector:

            >>> d = PyQuery('<p class="hello">Hi</p><p>Bye</p><div></div>')
            >>> d('p').not_('.hello')
            [<p>]
        """
        exclude = set(self.__class__(selector, self))
        return self.__class__([e for e in self if e not in exclude],
                              **dict(parent=self))

    def is_(self, selector):
        """Returns True if selector matches at least one current element, else
        False:

            >>> d = PyQuery('<p class="hello"><span>Hi</span></p><p>Bye</p>')
            >>> d('p').eq(0).is_('.hello')
            True

            >>> d('p').eq(0).is_('span')
            False

            >>> d('p').eq(1).is_('.hello')
            False

        ..
        """
        return bool(self._filter_only(selector, self))

    def find(self, selector):
        """Find elements using selector traversing down from self:

            >>> m = '<p><span><em>Whoah!</em></span></p><p><em> there</em></p>'
            >>> d = PyQuery(m)
            >>> d('p').find('em')
            [<em>, <em>]
            >>> d('p').eq(1).find('em')
            [<em>]
        """
        xpath = self._css_to_xpath(selector)
        results = [child.xpath(xpath) for tag in self
                   for child in tag.getchildren()]
        # Flatten the results
        elements = []
        for r in results:
            elements.extend(r)
        return self.__class__(elements, **dict(parent=self))

    def eq(self, index):
        """Return PyQuery of only the element with the provided index::

            >>> d = PyQuery('<p class="hello">Hi</p><p>Bye</p><div></div>')
            >>> d('p').eq(0)
            [<p.hello>]
            >>> d('p').eq(1)
            [<p>]
            >>> d('p').eq(2)
            []

        ..
        """
        # Use slicing to silently handle out of bounds indexes
        items = self[index:index + 1]
        return self.__class__(items, **dict(parent=self))

    def each(self, func):
        """apply func on each nodes
        """
        try:
            for i, element in enumerate(self):
                func_globals(func)['this'] = element
                if callback(func, i, element) is False:
                    break
        finally:
            f_globals = func_globals(func)
            if 'this' in f_globals:
                del f_globals['this']
        return self

    def map(self, func):
        """Returns a new PyQuery after transforming current items with func.

        func should take two arguments - 'index' and 'element'.  Elements can
        also be referred to as 'this' inside of func::

            >>> d = PyQuery('<p class="hello">Hi there</p><p>Bye</p><br />')
            >>> d('p').map(lambda i, e: PyQuery(e).text())
            ['Hi there', 'Bye']

            >>> d('p').map(lambda i, e: len(PyQuery(this).text()))
            [8, 3]

            >>> d('p').map(lambda i, e: PyQuery(this).text().split())
            ['Hi', 'there', 'Bye']

        """
        items = []
        try:
            for i, element in enumerate(self):
                func_globals(func)['this'] = element
                result = callback(func, i, element)
                if result is not None:
                    if not isinstance(result, list):
                        items.append(result)
                    else:
                        items.extend(result)
        finally:
            f_globals = func_globals(func)
            if 'this' in f_globals:
                del f_globals['this']
        return self.__class__(items, **dict(parent=self))

    @property
    def length(self):
        return len(self)

    def size(self):
        return len(self)

    def end(self):
        """Break out of a level of traversal and return to the parent level.

            >>> m = '<p><span><em>Whoah!</em></span></p><p><em> there</em></p>'
            >>> d = PyQuery(m)
            >>> d('p').eq(1).find('em').end().end()
            [<p>, <p>]
        """
        return self._parent

    ##############
    # Attributes #
    ##############
    def attr(self, *args, **kwargs):
        """Attributes manipulation
        """

        mapping = {'class_': 'class', 'for_': 'for'}

        attr = value = no_default
        length = len(args)
        if length == 1:
            attr = args[0]
            attr = mapping.get(attr, attr)
        elif length == 2:
            attr, value = args
            attr = mapping.get(attr, attr)
        elif kwargs:
            attr = {}
            for k, v in kwargs.items():
                attr[mapping.get(k, k)] = v
        else:
            raise ValueError('Invalid arguments %s %s' % (args, kwargs))

        if not self:
            return None
        elif isinstance(attr, dict):
            for tag in self:
                for key, value in attr.items():
                    tag.set(key, value)
        elif value is no_default:
            return self[0].get(attr)
        elif value is None or value == '':
            return self.remove_attr(attr)
        else:
            for tag in self:
                tag.set(attr, value)
        return self

    @with_camel_case_alias
    def remove_attr(self, name):
        """Remove an attribute::

            >>> d = PyQuery('<div id="myid"></div>')
            >>> d.remove_attr('id')
            [<div>]
            >>> d.removeAttr('id')
            [<div>]

        ..
        """
        for tag in self:
            try:
                del tag.attrib[name]
            except KeyError:
                pass
        return self

    attr = FlexibleElement(pget=attr, pdel=remove_attr)

    #######
    # CSS #
    #######
    def height(self, value=no_default):
        """set/get height of element
        """
        return self.attr('height', value)

    def width(self, value=no_default):
        """set/get width of element
        """
        return self.attr('width', value)

    @with_camel_case_alias
    def has_class(self, name):
        """Return True if element has class::

            >>> d = PyQuery('<div class="myclass"></div>')
            >>> d.has_class('myclass')
            True
            >>> d.hasClass('myclass')
            True

        ..
        """
        return self.is_('.%s' % name)

    @with_camel_case_alias
    def add_class(self, value):
        """Add a css class to elements::

            >>> d = PyQuery('<div></div>')
            >>> d.add_class('myclass')
            [<div.myclass>]
            >>> d.addClass('myclass')
            [<div.myclass>]

        ..
        """
        for tag in self:
            values = value.split(' ')
            classes = (tag.get('class') or '').split()
            classes += [v for v in values if v not in classes]
            tag.set('class', ' '.join(classes))
        return self

    @with_camel_case_alias
    def remove_class(self, value):
        """Remove a css class to elements::

            >>> d = PyQuery('<div class="myclass"></div>')
            >>> d.remove_class('myclass')
            [<div>]
            >>> d.removeClass('myclass')
            [<div>]

        ..
        """
        for tag in self:
            values = value.split(' ')
            classes = set((tag.get('class') or '').split())
            classes.difference_update(values)
            classes.difference_update([''])
            classes = ' '.join(classes)
            if classes.strip():
                tag.set('class', classes)
            elif tag.get('class'):
                tag.set('class', classes)
        return self

    @with_camel_case_alias
    def toggle_class(self, value):
        """Toggle a css class to elements

            >>> d = PyQuery('<div></div>')
            >>> d.toggle_class('myclass')
            [<div.myclass>]
            >>> d.toggleClass('myclass')
            [<div>]

        """
        for tag in self:
            values = value.split(' ')
            classes = (tag.get('class') or '').split()
            values_to_add = [v for v in values if v not in classes]
            values_to_del = [v for v in values if v in classes]
            classes = [v for v in classes if v not in values_to_del]
            classes += values_to_add
            tag.set('class', ' '.join(classes))
        return self

    def css(self, *args, **kwargs):
        """css attributes manipulation
        """

        attr = value = no_default
        length = len(args)
        if length == 1:
            attr = args[0]
        elif length == 2:
            attr, value = args
        elif kwargs:
            attr = kwargs
        else:
            raise ValueError('Invalid arguments %s %s' % (args, kwargs))

        if isinstance(attr, dict):
            for tag in self:
                stripped_keys = [key.strip().replace('_', '-')
                                 for key in attr.keys()]
                current = [el.strip()
                           for el in (tag.get('style') or '').split(';')
                           if el.strip()
                           and not el.split(':')[0].strip() in stripped_keys]
                for key, value in attr.items():
                    key = key.replace('_', '-')
                    current.append('%s: %s' % (key, value))
                tag.set('style', '; '.join(current))
        elif isinstance(value, basestring):
            attr = attr.replace('_', '-')
            for tag in self:
                current = [
                    el.strip()
                    for el in (tag.get('style') or '').split(';')
                    if (el.strip() and
                        not el.split(':')[0].strip() == attr.strip())]
                current.append('%s: %s' % (attr, value))
                tag.set('style', '; '.join(current))
        return self

    css = FlexibleElement(pget=css, pset=css)

    ###################
    # CORE UI EFFECTS #
    ###################
    def hide(self):
        """remove display:none to elements style

            >>> print(PyQuery('<div style="display:none;"/>').hide())
            <div style="display: none"/>

        """
        return self.css('display', 'none')

    def show(self):
        """add display:block to elements style

            >>> print(PyQuery('<div />').show())
            <div style="display: block"/>

        """
        return self.css('display', 'block')

    ########
    # HTML #
    ########
    def val(self, value=no_default):
        """Set the attribute value::

            >>> d = PyQuery('<input />')
            >>> d.val('Youhou')
            [<input>]

        Get the attribute value::

            >>> d.val()
            'Youhou'

        """
        return self.attr('value', value) or None

    def html(self, value=no_default, **kwargs):
        """Get or set the html representation of sub nodes.

        Get the text value::

            >>> d = PyQuery('<div><span>toto</span></div>')
            >>> print(d.html())
            <span>toto</span>

        Extra args are passed to ``lxml.etree.tostring``::

            >>> d = PyQuery('<div><span></span></div>')
            >>> print(d.html())
            <span/>
            >>> print(d.html(method='html'))
            <span></span>

        Set the text value::

            >>> d.html('<span>Youhou !</span>')
            [<div>]
            >>> print(d)
            <div><span>Youhou !</span></div>
        """
        if value is no_default:
            if not self:
                return None
            tag = self[0]
            children = tag.getchildren()
            if not children:
                return tag.text
            html = tag.text or ''
            if 'encoding' not in kwargs:
                kwargs['encoding'] = unicode
            html += unicode('').join([etree.tostring(e, **kwargs)
                                      for e in children])
            return html
        else:
            if isinstance(value, self.__class__):
                new_html = unicode(value)
            elif isinstance(value, basestring):
                new_html = value
            elif not value:
                new_html = ''
            else:
                raise ValueError(type(value))

            for tag in self:
                for child in tag.getchildren():
                    tag.remove(child)
                root = fromstring(
                    unicode('<root>') + new_html + unicode('</root>'),
                    self.parser)[0]
                children = root.getchildren()
                if children:
                    tag.extend(children)
                tag.text = root.text
                tag.tail = root.tail
        return self

    @with_camel_case_alias
    def outer_html(self):
        """Get the html representation of the first selected element::

            >>> d = PyQuery('<div><span class="red">toto</span> rocks</div>')
            >>> print(d('span'))
            <span class="red">toto</span> rocks
            >>> print(d('span').outer_html())
            <span class="red">toto</span>
            >>> print(d('span').outerHtml())
            <span class="red">toto</span>

            >>> S = PyQuery('<p>Only <b>me</b> & myself</p>')
            >>> print(S('b').outer_html())
            <b>me</b>

        ..
        """

        if not self:
            return None
        e0 = self[0]
        if e0.tail:
            e0 = deepcopy(e0)
            e0.tail = ''
        return lxml.html.tostring(e0, encoding=unicode)

    def text(self, value=no_default):
        """Get or set the text representation of sub nodes.

        Get the text value::

            >>> doc = PyQuery('<div><span>toto</span><span>tata</span></div>')
            >>> print(doc.text())
            toto tata

        Set the text value::

            >>> doc.text('Youhou !')
            [<div>]
            >>> print(doc)
            <div>Youhou !</div>

        """

        if value is no_default:
            if not self:
                return ''

            text = []

            def add_text(tag, no_tail=False):
                if tag.text and not isinstance(tag, lxml.etree._Comment):
                    text.append(tag.text)
                for child in tag.getchildren():
                    add_text(child)
                if not no_tail and tag.tail:
                    text.append(tag.tail)

            for tag in self:
                add_text(tag, no_tail=True)
            return ' '.join([t.strip() for t in text if t.strip()])

        for tag in self:
            for child in tag.getchildren():
                tag.remove(child)
            tag.text = value
        return self

    ################
    # Manipulating #
    ################

    def _get_root(self, value):
        if isinstance(value, basestring):
            root = fromstring(unicode('<root>') + value + unicode('</root>'),
                              self.parser)[0]
        elif isinstance(value, etree._Element):
            root = self.__class__(value)
        elif isinstance(value, PyQuery):
            root = value
        else:
            raise TypeError(
                'Value must be string, PyQuery or Element. Got %r' % value)
        if hasattr(root, 'text') and isinstance(root.text, basestring):
            root_text = root.text
        else:
            root_text = ''
        return root, root_text

    def append(self, value):
        """append value to each nodes
        """
        root, root_text = self._get_root(value)
        for i, tag in enumerate(self):
            if len(tag) > 0:  # if the tag has children
                last_child = tag[-1]
                if not last_child.tail:
                    last_child.tail = ''
                last_child.tail += root_text
            else:
                if not tag.text:
                    tag.text = ''
                tag.text += root_text
            if i > 0:
                root = deepcopy(list(root))
            tag.extend(root)
            root = tag[-len(root):]
        return self

    @with_camel_case_alias
    def append_to(self, value):
        """append nodes to value
        """
        value.append(self)
        return self

    def prepend(self, value):
        """prepend value to nodes
        """
        root, root_text = self._get_root(value)
        for i, tag in enumerate(self):
            if not tag.text:
                tag.text = ''
            if len(root) > 0:
                root[-1].tail = tag.text
                tag.text = root_text
            else:
                tag.text = root_text + tag.text
            if i > 0:
                root = deepcopy(list(root))
            tag[:0] = root
            root = tag[:len(root)]
        return self

    @with_camel_case_alias
    def prepend_to(self, value):
        """prepend nodes to value
        """
        value.prepend(self)
        return self

    def after(self, value):
        """add value after nodes
        """
        root, root_text = self._get_root(value)
        for i, tag in enumerate(self):
            if not tag.tail:
                tag.tail = ''
            tag.tail += root_text
            if i > 0:
                root = deepcopy(list(root))
            parent = tag.getparent()
            index = parent.index(tag) + 1
            parent[index:index] = root
            root = parent[index:len(root)]
        return self

    @with_camel_case_alias
    def insert_after(self, value):
        """insert nodes after value
        """
        value.after(self)
        return self

    def before(self, value):
        """insert value before nodes
        """
        root, root_text = self._get_root(value)
        for i, tag in enumerate(self):
            previous = tag.getprevious()
            if previous is not None:
                if not previous.tail:
                    previous.tail = ''
                previous.tail += root_text
            else:
                parent = tag.getparent()
                if not parent.text:
                    parent.text = ''
                parent.text += root_text
            if i > 0:
                root = deepcopy(list(root))
            parent = tag.getparent()
            index = parent.index(tag)
            parent[index:index] = root
            root = parent[index:len(root)]
        return self

    @with_camel_case_alias
    def insert_before(self, value):
        """insert nodes before value
        """
        value.before(self)
        return self

    def wrap(self, value):
        """A string of HTML that will be created on the fly and wrapped around
        each target:

            >>> d = PyQuery('<span>youhou</span>')
            >>> d.wrap('<div></div>')
            [<div>]
            >>> print(d)
            <div><span>youhou</span></div>

        """
        assert isinstance(value, basestring)
        value = fromstring(value)[0]
        nodes = []
        for tag in self:
            wrapper = deepcopy(value)
            # FIXME: using iterchildren is probably not optimal
            if not wrapper.getchildren():
                wrapper.append(deepcopy(tag))
            else:
                childs = [c for c in wrapper.iterchildren()]
                child = childs[-1]
                child.append(deepcopy(tag))
            nodes.append(wrapper)

            parent = tag.getparent()
            if parent is not None:
                for t in parent.iterchildren():
                    if t is tag:
                        t.addnext(wrapper)
                        parent.remove(t)
                        break
        self[:] = nodes
        return self

    @with_camel_case_alias
    def wrap_all(self, value):
        """Wrap all the elements in the matched set into a single wrapper
        element::

            >>> d = PyQuery('<div><span>Hey</span><span>you !</span></div>')
            >>> print(d('span').wrap_all('<div id="wrapper"></div>'))
            <div id="wrapper"><span>Hey</span><span>you !</span></div>

            >>> d = PyQuery('<div><span>Hey</span><span>you !</span></div>')
            >>> print(d('span').wrapAll('<div id="wrapper"></div>'))
            <div id="wrapper"><span>Hey</span><span>you !</span></div>

        ..
        """
        if not self:
            return self

        assert isinstance(value, basestring)
        value = fromstring(value)[0]
        wrapper = deepcopy(value)
        if not wrapper.getchildren():
            child = wrapper
        else:
            childs = [c for c in wrapper.iterchildren()]
            child = childs[-1]

        replace_childs = True
        parent = self[0].getparent()
        if parent is None:
            parent = no_default

        # add nodes to wrapper and check parent
        for tag in self:
            child.append(deepcopy(tag))
            if tag.getparent() is not parent:
                replace_childs = False

        # replace nodes i parent if possible
        if parent is not no_default and replace_childs:
            childs = [c for c in parent.iterchildren()]
            if len(childs) == len(self):
                for tag in self:
                    parent.remove(tag)
                parent.append(wrapper)

        self[:] = [wrapper]
        return self

    @with_camel_case_alias
    def replace_with(self, value):
        """replace nodes by value::

            >>> doc = PyQuery("<html><div /></html>")
            >>> node = PyQuery("<span />")
            >>> child = doc.find('div')
            >>> child.replace_with(node)
            [<div>]
            >>> print(doc)
            <html><span/></html>

        """
        if isinstance(value, PyQuery):
            value = str(value)
        if hasattr(value, '__call__'):
            for i, element in enumerate(self):
                self.__class__(element).before(
                    value(i, element) + (element.tail or ''))
                parent = element.getparent()
                parent.remove(element)
        else:
            for tag in self:
                self.__class__(tag).before(value + (tag.tail or ''))
                parent = tag.getparent()
                parent.remove(tag)
        return self

    @with_camel_case_alias
    def replace_all(self, expr):
        """replace nodes by expr
        """
        if self._parent is no_default:
            raise ValueError(
                'replaceAll can only be used with an object with parent')
        self._parent(expr).replace_with(self)
        return self

    def clone(self):
        """return a copy of nodes
        """
        return PyQuery([deepcopy(tag) for tag in self])

    def empty(self):
        """remove nodes content
        """
        for tag in self:
            tag.text = None
            tag[:] = []
        return self

    def remove(self, expr=no_default):
        """Remove nodes:

         >>> h = '<div>Maybe <em>she</em> does <strong>NOT</strong> know</div>'
         >>> d = PyQuery(h)
         >>> d('strong').remove()
         [<strong>]
         >>> print(d)
         <div>Maybe <em>she</em> does   know</div>
        """
        if expr is no_default:
            for tag in self:
                parent = tag.getparent()
                if parent is not None:
                    if tag.tail:
                        prev = tag.getprevious()
                        if prev is None:
                            if not parent.text:
                                parent.text = ''
                            parent.text += ' ' + tag.tail
                        else:
                            if not prev.tail:
                                prev.tail = ''
                            prev.tail += ' ' + tag.tail
                    parent.remove(tag)
        else:
            results = self.__class__(expr, self)
            results.remove()
        return self

    class Fn(object):
        """Hook for defining custom function (like the jQuery.fn):

        .. sourcecode:: python

         >>> fn = lambda: this.map(lambda i, el: PyQuery(this).outerHtml())
         >>> PyQuery.fn.listOuterHtml = fn
         >>> S = PyQuery(
         ...   '<ol>   <li>Coffee</li>   <li>Tea</li>   <li>Milk</li>   </ol>')
         >>> S('li').listOuterHtml()
         ['<li>Coffee</li>', '<li>Tea</li>', '<li>Milk</li>']

        """
        def __setattr__(self, name, func):
            def fn(self, *args):
                func_globals(func)['this'] = self
                return func(*args)
            fn.__name__ = name
            setattr(PyQuery, name, fn)
    fn = Fn()

    #####################################################
    # Additional methods that are not in the jQuery API #
    #####################################################

    @property
    def base_url(self):
        """Return the url of current html document or None if not available.
        """
        if self._base_url is not None:
            return self._base_url
        if self._parent is not no_default:
            return self._parent.base_url

    def make_links_absolute(self, base_url=None):
        """Make all links absolute.
        """
        if base_url is None:
            base_url = self.base_url
            if base_url is None:
                raise ValueError((
                    'You need a base URL to make your links'
                    'absolute. It can be provided by the base_url parameter.'))

        def repl(i, e):
            return self(e).attr(
                'href',
                urljoin(base_url, self(e).attr('href')))

        self('a').each(repl)
        return self

build_camel_case_aliases(PyQuery)

########NEW FILE########
__FILENAME__ = rules
# -*- coding: utf-8 -*-
try:
    from deliverance.pyref import PyReference
    from deliverance import rules
    from ajax import PyQuery as pq
except ImportError:
    pass
else:
    class PyQuery(rules.AbstractAction):
        """Python function"""
        name = 'py'
        def __init__(self, source_location, pyref):
            self.source_location = source_location
            self.pyref = pyref

        def apply(self, content_doc, theme_doc, resource_fetcher, log):
            self.pyref(pq([content_doc]), pq([theme_doc]), resource_fetcher, log)

        @classmethod
        def from_xml(cls, el, source_location):
            """Parses and instantiates the class from an element"""
            pyref = PyReference.parse_xml(
                el, source_location=source_location,
                default_function='transform')
            return cls(source_location, pyref)

    rules._actions['pyquery'] = PyQuery

    def deliverance_proxy():
        import deliverance.proxycommand
        deliverance.proxycommand.main()

########NEW FILE########
__FILENAME__ = README_fixt
# -*- coding: utf-8 -*-
import os
from webtest import http
from webtest.debugapp import debug_app

try:
    from urllib import urlopen
except ImportError:
    from urllib.request import urlopen


def setup_test(test):
    server = http.StopableWSGIServer.create(debug_app)
    server.wait()
    path_to_html_file = os.path.join('tests', 'test.html')
    test.globs.update(
        urlopen=urlopen,
        server=server,
        your_url=server.application_url,
        path_to_html_file=path_to_html_file,
    )
setup_test.__test__ = False


def teardown_test(test):
    test.globs['server'].shutdown()
teardown_test.__test__ = False

########NEW FILE########
__FILENAME__ = apps
# -*- coding: utf-8 -*-
from webob import Request
from webob import Response
from webob import exc
from .compat import b


def input_app(environ, start_response):
    resp = Response()
    req = Request(environ)
    if req.path_info == '/':
        resp.body = b('<input name="youyou" type="text" value="" />')
    elif req.path_info == '/submit':
        resp.body = b('<input type="submit" value="OK" />')
    elif req.path_info.startswith('/html'):
        resp.body = b('<html><p>Success</p></html>')
    else:
        resp.body = ''
    return resp(environ, start_response)


def application(environ, start_response):
    req = Request(environ)
    response = Response()
    if req.method == 'GET':
        response.body = b('<pre>Yeah !</pre>')
    else:
        response.body = b('<a href="/plop">Yeah !</a>')
    return response(environ, start_response)


def secure_application(environ, start_response):
    if 'REMOTE_USER' not in environ:
        return exc.HTTPUnauthorized('vomis')(environ, start_response)
    return application(environ, start_response)

########NEW FILE########
__FILENAME__ = compat
# -*- coding: utf-8 -*-
import sys

PY3k = sys.version_info >= (3,)

if PY3k:
    text_type = str

    def u(value, encoding):
        return str(value)

    def b(value):
        return value.encode('utf-8')
else:
    text_type = unicode

    def u(value, encoding):  # NOQA
        return unicode(value, encoding)

    def b(value):  # NOQA
        return str(value)

try:
    from unittest2 import TestCase
except ImportError:
    from unittest import TestCase  # NOQA

########NEW FILE########
__FILENAME__ = test_pyquery
#-*- coding:utf-8 -*-
#
# Copyright (C) 2008 - Olivier Lauzanne <olauzanne@gmail.com>
#
# Distributed under the BSD license, see LICENSE.txt
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from lxml import etree
from pyquery.pyquery import PyQuery as pq
from pyquery.ajax import PyQuery as pqa
from webtest import http
from webtest.debugapp import debug_app
from .apps import application
from .apps import secure_application
from .compat import PY3k
from .compat import u
from .compat import b
from .compat import text_type
from .compat import TestCase


def not_py3k(func):
    if not PY3k:
        return func

try:
    import requests  # NOQA
    HAS_REQUEST = True
except ImportError:
    HAS_REQUEST = False


dirname = os.path.dirname(os.path.abspath(__file__))
docs = os.path.join(os.path.dirname(dirname), 'docs')
path_to_html_file = os.path.join(dirname, 'test.html')
path_to_invalid_file = os.path.join(dirname, 'invalid.xml')


class TestUnicode(TestCase):

    def test_unicode(self):
        xml = pq(u("<html><p>é</p></html>", 'utf-8'))
        self.assertEqual(type(xml.html()), text_type)
        if PY3k:
            self.assertEqual(str(xml), '<html><p>é</p></html>')
            self.assertEqual(str(xml('p:contains("é")')), '<p>é</p>')
        else:
            self.assertEqual(unicode(xml), u("<html><p>é</p></html>", 'utf-8'))
            self.assertEqual(str(xml), '<html><p>&#233;</p></html>')
            self.assertEqual(str(xml(u('p:contains("é")', 'utf8'))),
                             '<p>&#233;</p>')
            self.assertEqual(unicode(xml(u('p:contains("é")', 'utf8'))),
                             u('<p>é</p>', 'utf8'))


class TestAttributeCase(TestCase):

    def test_xml_upper_element_name(self):
        xml = pq('<X>foo</X>', parser='xml')
        self.assertEqual(len(xml('X')), 1)
        self.assertEqual(len(xml('x')), 0)

    def test_html_upper_element_name(self):
        xml = pq('<X>foo</X>', parser='html')
        self.assertEqual(len(xml('X')), 1)
        self.assertEqual(len(xml('x')), 1)


class TestSelector(TestCase):
    klass = pq
    html = """
           <html>
            <body>
              <div>node1</div>
              <div id="node2">node2</div>
              <div class="node3">node3</div>
            </body>
           </html>
           """

    html2 = """
           <html>
            <body>
              <div>node1</div>
            </body>
           </html>
           """

    html3 = """
           <html>
            <body>
              <div>node1</div>
              <div id="node2">node2</div>
              <div class="node3">node3</div>
            </body>
           </html>
           """

    html4 = """
           <html>
            <body>
              <form action="/">
                <input name="enabled" type="text" value="test"/>
                <input name="disabled" type="text"
                       value="disabled" disabled="disabled"/>
                <input name="file" type="file" />
                <select name="select">
                  <option value="">Choose something</option>
                  <option value="one">One</option>
                  <option value="two" selected="selected">Two</option>
                  <option value="three">Three</option>
                </select>
                <input name="radio" type="radio" value="one"/>
                <input name="radio" type="radio"
                       value="two" checked="checked"/>
                <input name="radio" type="radio" value="three"/>
                <input name="checkbox" type="checkbox" value="a"/>
                <input name="checkbox" type="checkbox"
                       value="b" checked="checked"/>
                <input name="checkbox" type="checkbox" value="c"/>
                <input name="button" type="button" value="button" />
                <button>button</button>
              </form>
            </body>
           </html>
           """

    html5 = """
           <html>
            <body>
              <h1>Heading 1</h1>
              <h2>Heading 2</h2>
              <h3>Heading 3</h3>
              <h4>Heading 4</h4>
              <h5>Heading 5</h5>
              <h6>Heading 6</h6>
            </body>
           </html>
           """

    def test_get_root(self):
        doc = pq(b('<?xml version="1.0" encoding="UTF-8"?><root><p/></root>'))
        self.assertEqual(isinstance(doc.root, etree._ElementTree), True)
        self.assertEqual(doc.encoding, 'UTF-8')

    def test_selector_from_doc(self):
        doc = etree.fromstring(self.html)
        assert len(self.klass(doc)) == 1
        assert len(self.klass('div', doc)) == 3
        assert len(self.klass('div#node2', doc)) == 1

    def test_selector_from_html(self):
        assert len(self.klass(self.html)) == 1
        assert len(self.klass('div', self.html)) == 3
        assert len(self.klass('div#node2', self.html)) == 1

    def test_selector_from_obj(self):
        e = self.klass(self.html)
        assert len(e('div')) == 3
        assert len(e('div#node2')) == 1

    def test_selector_from_html_from_obj(self):
        e = self.klass(self.html)
        assert len(e('div', self.html2)) == 1
        assert len(e('div#node2', self.html2)) == 0

    def test_class(self):
        e = self.klass(self.html)
        assert isinstance(e, self.klass)
        n = e('div', self.html2)
        assert isinstance(n, self.klass)
        assert n._parent is e

    def test_pseudo_classes(self):
        e = self.klass(self.html)
        self.assertEqual(e('div:first').text(), 'node1')
        self.assertEqual(e('div:last').text(), 'node3')
        self.assertEqual(e('div:even').text(), 'node1 node3')
        self.assertEqual(e('div div:even').text(), '')
        self.assertEqual(e('body div:even').text(), 'node1 node3')
        self.assertEqual(e('div:gt(0)').text(), 'node2 node3')
        self.assertEqual(e('div:lt(1)').text(), 'node1')
        self.assertEqual(e('div:eq(2)').text(), 'node3')

        #test on the form
        e = self.klass(self.html4)
        assert len(e(':disabled')) == 1
        assert len(e('input:enabled')) == 9
        assert len(e(':selected')) == 1
        assert len(e(':checked')) == 2
        assert len(e(':file')) == 1
        assert len(e(':input')) == 12
        assert len(e(':button')) == 2
        assert len(e(':radio')) == 3
        assert len(e(':checkbox')) == 3

        #test on other elements
        e = self.klass(self.html5)
        assert len(e(":header")) == 6
        assert len(e(":parent")) == 2
        assert len(e(":empty")) == 6
        assert len(e(":contains('Heading')")) == 6

    def test_on_the_fly_dom_creation(self):
        e = self.klass(self.html)
        assert e('<p>Hello world</p>').text() == 'Hello world'
        assert e('').text() == ''


class TestTraversal(TestCase):
    klass = pq
    html = """
           <html>
            <body>
              <div id="node1"><span>node1</span></div>
              <div id="node2" class="node3">
                        <span>node2</span><span> booyah</span></div>
            </body>
           </html>
           """

    def test_filter(self):
        assert len(self.klass('div', self.html).filter('.node3')) == 1
        assert len(self.klass('div', self.html).filter('#node2')) == 1
        assert len(self.klass('div', self.html).filter(lambda i: i == 0)) == 1

        d = pq('<p>Hello <b>warming</b> world</p>')
        self.assertEqual(d('strong').filter(lambda el: True), [])

    def test_not(self):
        assert len(self.klass('div', self.html).not_('.node3')) == 1

    def test_is(self):
        assert self.klass('div', self.html).is_('.node3')
        assert not self.klass('div', self.html).is_('.foobazbar')

    def test_find(self):
        assert len(self.klass('#node1', self.html).find('span')) == 1
        assert len(self.klass('#node2', self.html).find('span')) == 2
        assert len(self.klass('div', self.html).find('span')) == 3

    def test_each(self):
        doc = self.klass(self.html)
        doc('span').each(lambda: doc(this).wrap("<em></em>"))  # NOQA
        assert len(doc('em')) == 3

    def test_map(self):
        def ids_minus_one(i, elem):
            return int(self.klass(elem).attr('id')[-1]) - 1
        assert self.klass('div', self.html).map(ids_minus_one) == [0, 1]

        d = pq('<p>Hello <b>warming</b> world</p>')
        self.assertEqual(d('strong').map(lambda i, el: pq(this).text()), [])  # NOQA

    def test_end(self):
        assert len(self.klass('div', self.html).find('span').end()) == 2
        assert len(self.klass('#node2', self.html).find('span').end()) == 1

    def test_closest(self):
        assert len(self.klass('#node1 span', self.html).closest('body')) == 1
        assert self.klass('#node2',
                          self.html).closest('.node3').attr('id') == 'node2'
        assert self.klass('.node3', self.html).closest('form') == []


class TestOpener(TestCase):

    def test_open_filename(self):
        doc = pq(filename=path_to_html_file)
        self.assertEqual(len(doc('p#test').text()), 14)

    def test_invalid_filename(self):
        doc = pq(filename=path_to_invalid_file)
        self.assertEqual(len(doc('p#test').text()), 14)

    def test_custom_opener(self):
        def opener(url):
            return '<html><body><div class="node"></div>'

        doc = pq(url='http://example.com', opener=opener)
        assert len(doc('.node')) == 1, doc


class TestComment(TestCase):

    def test_comment(self):
        doc = pq('<div><!-- foo --> bar</div>')
        self.assertEqual(doc.text(), 'bar')


class TestCallback(TestCase):
    html = """
        <ol>
            <li>Coffee</li>
            <li>Tea</li>
            <li>Milk</li>
        </ol>
    """

    def test_S_this_inside_callback(self):
        S = pq(self.html)
        self.assertEqual(S('li').map(lambda i, el: S(this).html()),  # NOQA
                                     ['Coffee', 'Tea', 'Milk'])

    def test_parameterless_callback(self):
        S = pq(self.html)
        self.assertEqual(S('li').map(lambda: S(this).html()),  # NOQA
                                     ['Coffee', 'Tea', 'Milk'])


class TestAjaxSelector(TestSelector):
    klass = pqa

    def setUp(self):
        self.s = http.StopableWSGIServer.create(application)

    @not_py3k
    def test_proxy(self):
        self.s.wait()
        application_url = self.s.application_url
        e = self.klass([])
        val = e.get(application_url)
        assert len(val('pre')) == 1, (str(val.response), val)

    def test_get(self):
        e = self.klass(app=application)
        val = e.get('/')
        assert len(val('pre')) == 1, val

    def test_secure_get(self):
        e = self.klass(app=secure_application)
        val = e.get('/', environ=dict(REMOTE_USER='gawii'))
        assert len(val('pre')) == 1, val
        val = e.get('/', REMOTE_USER='gawii')
        assert len(val('pre')) == 1, val

    def test_secure_get_not_authorized(self):
        e = self.klass(app=secure_application)
        val = e.get('/')
        assert len(val('pre')) == 0, val

    def test_post(self):
        e = self.klass(app=application)
        val = e.post('/')
        assert len(val('a')) == 1, val

    def test_subquery(self):
        e = self.klass(app=application)
        n = e('div')
        val = n.post('/')
        assert len(val('a')) == 1, val

    def tearDown(self):
        self.s.shutdown()


class TestManipulating(TestCase):
    html = '''
    <div class="portlet">
      <a href="/toto">Test<img src ="myimage" />My link text</a>
      <a href="/toto2"><img src ="myimage2" />My link text 2</a>
    </div>
    '''

    def test_remove(self):
        d = pq(self.html)
        d('img').remove()
        val = d('a:first').html()
        assert val == 'Test My link text', repr(val)
        val = d('a:last').html()
        assert val == ' My link text 2', repr(val)

    def test_class(self):
        d = pq('<div></div>')
        d.removeClass('xx')
        assert 'class' not in str(d), str(d)


class TestMakeLinks(TestCase):

    html = '''
    <html>
    <div>
    <a href="/path_info">with href</a>
    <a>without href</a>
    </div>
    </html>
    '''

    def test_make_link(self):
        d = pq(self.html, parser='xml')
        d.make_links_absolute(base_url='http://example.com')
        self.assertTrue(len(d('a[href]')), 1)
        self.assertEqual(d('a[href]').attr('href'),
                         'http://example.com/path_info')


class TestHTMLParser(TestCase):
    xml = "<div>I'm valid XML</div>"
    html = '''<div class="portlet">
      <a href="/toto">TestimageMy link text</a>
      <a href="/toto2">imageMy link text 2</a>
      Behind you, a three-headed HTML&dash;Entity!
    </div>'''

    def test_parser_persistance(self):
        d = pq(self.xml, parser='xml')
        self.assertRaises(etree.XMLSyntaxError, lambda: d.after(self.html))
        d = pq(self.xml, parser='html')
        d.after(self.html)  # this should not fail

    @not_py3k
    def test_soup_parser(self):
        d = pq('<meta><head><title>Hello</head><body onload=crash()>Hi all<p>',
               parser='soup')
        self.assertEqual(str(d), (
            '<html><meta/><head><title>Hello</title></head>'
            '<body onload="crash()">Hi all<p/></body></html>'))

    def test_replaceWith(self):
        expected = '''<div class="portlet">
      <a href="/toto">TestimageMy link text</a>
      <a href="/toto2">imageMy link text 2</a>
      Behind you, a three-headed HTML&amp;dash;Entity!
    </div>'''
        d = pq(self.html)
        d('img').replace_with('image')
        val = d.__html__()
        assert val == expected, (repr(val), repr(expected))

    def test_replaceWith_with_function(self):
        expected = '''<div class="portlet">
      TestimageMy link text
      imageMy link text 2
      Behind you, a three-headed HTML&amp;dash;Entity!
    </div>'''
        d = pq(self.html)
        d('a').replace_with(lambda i, e: pq(e).html())
        val = d.__html__()
        assert val == expected, (repr(val), repr(expected))


class TestXMLNamespace(TestCase):
    xml = '''<?xml version="1.0" encoding="UTF-8" ?>
    <foo xmlns:bar="http://example.com/bar">
    <bar:blah>What</bar:blah>
    <idiot>123</idiot>
    </foo>'''

    xhtml = '''
    <html xmlns="http://www.w3.org/1999/xhtml">
    <body>
    <div>What</div>
    </body>
    </html>'''

    def test_selector(self):
        expected = 'What'
        d = pq(b(self.xml), parser='xml')
        val = d('bar|blah',
                namespaces={'bar': 'http://example.com/bar'}).text()
        self.assertEqual(repr(val), repr(expected))

    def test_selector_with_xml(self):
        expected = 'What'
        d = pq('bar|blah', b(self.xml), parser='xml',
               namespaces={'bar': 'http://example.com/bar'})
        val = d.text()
        self.assertEqual(repr(val), repr(expected))

    def test_selector_html(self):
        expected = 'What'
        d = pq('blah', self.xml.split('?>', 1)[1], parser='html')
        val = d.text()
        self.assertEqual(repr(val), repr(expected))

    def test_xhtml_namespace(self):
        expected = 'What'
        d = pq(b(self.xhtml), parser='xml')
        d.xhtml_to_html()
        val = d('div').text()
        self.assertEqual(repr(val), repr(expected))

    def test_xhtml_namespace_html_parser(self):
        expected = 'What'
        d = pq(self.xhtml, parser='html')
        d.xhtml_to_html()
        val = d('div').text()
        self.assertEqual(repr(val), repr(expected))

    def test_remove_namespaces(self):
        expected = 'What'
        d = pq(b(self.xml), parser='xml').remove_namespaces()
        val = d('blah').text()
        self.assertEqual(repr(val), repr(expected))


class TestWebScrapping(TestCase):

    def setUp(self):
        self.s = http.StopableWSGIServer.create(debug_app)
        self.s.wait()
        self.application_url = self.s.application_url.rstrip('/')

    def test_get(self):
        d = pq(self.application_url, {'q': 'foo'},
               method='get')
        print(d)
        self.assertIn('REQUEST_METHOD: GET', d('p').text())
        self.assertIn('q=foo', d('p').text())

    def test_post(self):
        d = pq(self.application_url, {'q': 'foo'},
               method='post')
        self.assertIn('REQUEST_METHOD: POST', d('p').text())
        self.assertIn('q=foo', d('p').text())

    def tearDown(self):
        self.s.shutdown()


class TestWebScrappingEncoding(TestCase):

    def test_get(self):
        if not HAS_REQUEST:
            return
        d = pq(u('http://ru.wikipedia.org/wiki/Заглавная_страница', 'utf8'),
               method='get')
        print(d)
        self.assertEqual(d('#n-mainpage a').text(),
                         u('Заглавная страница', 'utf8'))

########NEW FILE########
