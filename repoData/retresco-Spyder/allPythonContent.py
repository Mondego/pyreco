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
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# Spyder documentation build configuration file, created by
# sphinx-quickstart on Fri Jan  7 15:59:33 2011.
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
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.doctest', 'sphinx.ext.todo', 'sphinx.ext.coverage', 'sphinx.ext.pngmath', 'sphinx.ext.ifconfig', 'sphinx.ext.viewcode']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'Spyder'
copyright = u'2011, Daniel Truemper'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '0'
# The full version, including alpha/beta/rc tags.
release = '0.1'

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
exclude_patterns = []

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
htmlhelp_basename = 'Spyderdoc'


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
latex_paper_size = 'a4'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'Spyder.tex', u'Spyder Documentation',
   u'Daniel Truemper', 'manual'),
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
    ('index', 'spyder', u'Spyder Documentation',
     [u'Daniel Truemper'], 1)
]


# -- Options for Epub output ---------------------------------------------------

# Bibliographic Dublin Core info.
epub_title = u'Spyder'
epub_author = u'Daniel Truemper'
epub_publisher = u'Daniel Truemper'
epub_copyright = u'2011, Daniel Truemper'

# The language of the text. It defaults to the language option
# or en if the language is not set.
#epub_language = ''

# The scheme of the identifier. Typical schemes are ISBN or URL.
#epub_scheme = ''

# The unique identifier of the text. This can be a ISBN number
# or the project homepage.
#epub_identifier = ''

# A unique identification for the text.
#epub_uid = ''

# HTML files that should be inserted before the pages created by sphinx.
# The format is a list of tuples containing the path and title.
#epub_pre_files = []

# HTML files shat should be inserted after the pages created by sphinx.
# The format is a list of tuples containing the path and title.
#epub_post_files = []

# A list of files that should not be packed into the epub file.
#epub_exclude_files = []

# The depth of the table of contents in toc.ncx.
#epub_tocdepth = 3

# Allow duplicate toc entries.
#epub_tocdup = True

########NEW FILE########
__FILENAME__ = constants
#
# Copyright (c) 2011 Daniel Truemper truemped@googlemail.com
#
# constants.py 10-Jan-2011
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
"""
Serveral constants mainly for ZeroMQ topics and messages.
"""

# general topic for spyder related management tasks
ZMQ_SPYDER_MGMT = 'spyder.'

ZMQ_SPYDER_MGMT_WORKER = ZMQ_SPYDER_MGMT + 'worker.'
ZMQ_SPYDER_MGMT_WORKER_AVAIL = 'be here now'.encode()
ZMQ_SPYDER_MGMT_WORKER_QUIT = 'quit'.encode()
ZMQ_SPYDER_MGMT_WORKER_QUIT_ACK = 'quit.ack'.encode()

# constants used in the optional_vars map of CrawlUris
CURI_OPTIONAL_TRUE = "1".encode()
CURI_OPTIONAL_FALSE = "0".encode()

# username and password fields
CURI_SITE_USERNAME = "username".encode()
CURI_SITE_PASSWORD = "password".encode()

# extraction finished field
CURI_EXTRACTION_FINISHED = "extraction_finished".encode()

# extracted urls field
CURI_EXTRACTED_URLS = "extracted_urls".encode()

# Some internal error states
CURI_EUNCAUGHT_EXCEPTION = 710

########NEW FILE########
__FILENAME__ = dnscache
#
# Copyright (c) 2011 Daniel Truemper truemped@googlemail.com
#
# dnscache.py 24-Jan-2011
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
"""
A very simple dns cache.

Currently dns resolution is blocking style but this should get a nonblocking
version.
"""

import socket

from brownie.caching import LRUCache as LRUDict


class DnsCache(object):
    """
    This is a least recently used cache for hostname to ip addresses. If the
    cache has reached it's maximum size, the least used key is being removed
    and a new DNS lookup is made.

    In addition you may add static mappings via the
    ``settings.STATIC_DNS_MAPPINGS`` dict.
    """

    def __init__(self, settings):
        """
        Initialize the lru cache and the static mappings.
        """
        self._cache = LRUDict(maxsize=settings.SIZE_DNS_CACHE)
        self._static_cache = dict()
        self._static_cache.update(settings.STATIC_DNS_MAPPINGS)

    def __getitem__(self, host_port_string):
        """
        Retrieve the item from the cache or resolve the hostname and store the
        result in the cache.

        Returns a tuple of `(ip, port)`. At the moment we only support IPv4 but
        this will probably change in the future.
        """
        if host_port_string in self._static_cache.keys():
            return self._static_cache[host_port_string]

        if host_port_string not in self._cache:
            (hostname, port) = host_port_string.split(":")
            infos = socket.getaddrinfo(hostname, port, 0, 0, socket.SOL_TCP)
            for (_family, _socktype, _proto, _canoname, sockaddr) in infos:
                if len(sockaddr) == 2:
                    # IPv4 (which we prefer)
                    self._cache[host_port_string] = sockaddr

        return self._cache[host_port_string]

########NEW FILE########
__FILENAME__ = frontier
#
# Copyright (c) 2011 Daniel Truemper truemped@googlemail.com
#
# frontier.py 26-Jan-2011
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
"""
Generic Frontier implementation.

The :class:`SingleHostFrontier` will only select URIs from the queues by
iterating over all available queues and added into a priority queue.

The priority is calculated based on the timestamp it should be crawled next.

In contrast to the :mod:`spyder.core.sqlitequeues` module, URIs in this module
are represented as :class:`spyder.thrift.gen.ttypes.CrawlUri`.
"""

import time
from datetime import datetime
from datetime import timedelta

from Queue import PriorityQueue, Empty, Full
from urlparse import urlparse

from spyder.core.constants import CURI_SITE_USERNAME, CURI_SITE_PASSWORD
from spyder.core.constants import CURI_EXTRACTED_URLS
from spyder.core.dnscache import DnsCache
from spyder.time import serialize_date_time, deserialize_date_time
from spyder.core.log import LoggingMixin
from spyder.core.sqlitequeues import SQLiteSingleHostUriQueue
from spyder.core.sqlitequeues import SQLiteMultipleHostUriQueue
from spyder.core.uri_uniq import UniqueUriFilter
from spyder.thrift.gen.ttypes import CrawlUri
from spyder.import_util import import_class


# some default port numbers as of /etc/services
PROTOCOLS_DEFAULT_PORT = {
    "http": 80,
    "https": 443,
    "ftp": 21,
    "ftps": 990,
    "sftp": 115,
}


class AbstractBaseFrontier(object, LoggingMixin):
    """
    A base class for implementing frontiers.

    Basically this class provides the different general methods and
    configuration parameters used for frontiers.
    """

    def __init__(self, settings, log_handler, front_end_queues, prioritizer,
        unique_hash='sha1'):
        """
        Initialize the frontier and instantiate the
        :class:`SQLiteSingleHostUriQueue`.

        The default frontier we will use the `sha1` hash function for the
        unique uri filter. For very large crawls you might want to use a
        larger hash function (`sha512`, e.g.)
        """
        LoggingMixin.__init__(self, log_handler, settings.LOG_LEVEL_MASTER)
        # front end queue
        self._prioritizer = prioritizer
        self._front_end_queues = front_end_queues
        # checkpointing
        self._checkpoint_interval = settings.FRONTIER_CHECKPOINTING
        self._uris_added = 0

        # the heap
        self._heap = PriorityQueue(maxsize=settings.FRONTIER_HEAP_SIZE)
        self._heap_min_size = settings.FRONTIER_HEAP_MIN

        # a list of uris currently being crawled.
        self._current_uris = dict()
        # dns cache
        self._dns_cache = DnsCache(settings)
        # unique uri filter
        self._unique_uri = UniqueUriFilter(unique_hash)
        for url in self._front_end_queues.all_uris():
            assert not self._unique_uri.is_known(url, add_if_unknown=True)

        # the sinks
        self._sinks = []

        # timezone
        self._timezone = settings.LOCAL_TIMEZONE
        self._logger.info("frontier::initialized")

    def add_sink(self, sink):
        """
        Add a sink to the frontier. A sink will be responsible for the long
        term storage of the crawled contents.
        """
        self._sinks.append(sink)

    def add_uri(self, curi):
        """
        Add the specified :class:`CrawlUri` to the frontier.

        `next_date` is a datetime object for the next time the uri should be
        crawled.

        Note: time based crawling is never strict, it is generally used as some
        kind of prioritization.
        """
        if self._unique_uri.is_known(curi.url, add_if_unknown=True):
            # we already know this uri
            self._logger.debug("frontier::Trying to update a known uri... " + \
                    "(%s)" % (curi.url,))
            return

        self._logger.info("frontier::Adding '%s' to the frontier" % curi.url)
        self._front_end_queues.add_uri(self._uri_from_curi(curi))
        self._maybe_checkpoint()

    def update_uri(self, curi):
        """
        Update a given uri.
        """
        self._front_end_queues.update_uri(self._uri_from_curi(curi))
        self._maybe_checkpoint()

    def get_next(self):
        """
        Return the next uri scheduled for crawling.
        """
        if self._heap.qsize() < self._heap_min_size:
            self._update_heap()

        try:
            (_next_date, next_uri) = self._heap.get_nowait()
        except Empty:
            # heap is empty, there is nothing to crawl right now!
            # maybe log this in the future
            raise

        return self._crawluri_from_uri(next_uri)

    def close(self):
        """
        Close the underlying frontend queues.
        """
        self._front_end_queues.checkpoint()
        self._front_end_queues.close()

    def _crawl_now(self, uri):
        """
        Convinience method for crawling an uri right away.
        """
        self._add_to_heap(uri, 3000)

    def _add_to_heap(self, uri, next_date):
        """
        Add an URI to the heap that is ready to be crawled.
        """
        self._heap.put_nowait((next_date, uri))
        (url, _etag, _mod_date, _next_date, _prio) = uri
        self._current_uris[url] = uri
        self._logger.debug("frontier::Adding '%s' to the heap" % url)

    def _reschedule_uri(self, curi):
        """
        Return the `next_crawl_date` for :class:`CrawlUri`s.
        """
        (prio, delta) = self._prioritizer.calculate_priority(curi)
        now = datetime.now(self._timezone)
        return (prio, time.mktime((now + delta).timetuple()))

    def _ignore_uri(self, curi):
        """
        Ignore a :class:`CrawlUri` from now on.
        """
        self._front_end_queues.ignore_uri(curi.url, curi.status_code)

    def _uri_from_curi(self, curi):
        """
        Create the uri tuple from the :class:`CrawlUri` and calculate the
        priority.

        Overwrite this method in more specific frontiers.
        """
        etag = mod_date = None
        if curi.rep_header:
            if "Etag" in curi.rep_header:
                etag = curi.rep_header["Etag"]
            if "Last-Modified" in curi.rep_header:
                mod_date = time.mktime(deserialize_date_time(
                    curi.rep_header["Last-Modified"]).timetuple())
            if not mod_date and 'Date' in curi.rep_header:
                mod_date = time.mktime(deserialize_date_time(
                    curi.rep_header["Date"]).timetuple())

        if mod_date:
            # only reschedule if it has been crawled before
            (prio, next_crawl_date) = self._reschedule_uri(curi)
        else:
            (prio, next_crawl_date) = (1,
                    time.mktime(datetime.now(self._timezone).timetuple()))

        return (curi.url, etag, mod_date, next_crawl_date, prio)

    def _crawluri_from_uri(self, uri):
        """
        Convert an URI tuple to a :class:`CrawlUri`.

        Replace the hostname with the real IP in order to cache DNS queries.
        """
        (url, etag, mod_date, _next_date, prio) = uri

        parsed_url = urlparse(url)

        # dns resolution and caching
        port = parsed_url.port
        if not port:
            port = PROTOCOLS_DEFAULT_PORT[parsed_url.scheme]

        effective_netloc = self._dns_cache["%s:%s" % (parsed_url.hostname,
            port)]

        curi = CrawlUri(url)
        curi.effective_url = url.replace(parsed_url.netloc, "%s:%s" %
                effective_netloc)
        curi.current_priority = prio
        curi.req_header = dict()
        if etag:
            curi.req_header["Etag"] = etag
        if mod_date:
            mod_date_time = datetime.fromtimestamp(mod_date)
            curi.req_header["Last-Modified"] = serialize_date_time(
                    mod_date_time)

        curi.optional_vars = dict()
        if parsed_url.username and parsed_url.password:
            curi.optional_vars[CURI_SITE_USERNAME] = \
                parsed_url.username.encode()
            curi.optional_vars[CURI_SITE_PASSWORD] = \
                parsed_url.password.encode()

        return curi

    def _update_heap(self):
        """
        Abstract method. Implement this in the actual Frontier.

        The implementation should really only add uris to the heap if they can
        be downloaded right away.
        """
        pass

    def _maybe_checkpoint(self, force_checkpoint=False):
        """
        Periodically checkpoint the state db.
        """
        self._uris_added += 1
        if self._uris_added > self._checkpoint_interval or force_checkpoint:
            self._front_end_queues.checkpoint()
            self._uris_added = 0

    def process_successful_crawl(self, curi):
        """
        Called when an URI has been crawled successfully.

        `curi` is a :class:`CrawlUri`
        """
        self.update_uri(curi)

        if curi.optional_vars and CURI_EXTRACTED_URLS in curi.optional_vars:
            for url in curi.optional_vars[CURI_EXTRACTED_URLS].split("\n"):
                if len(url) > 5 and not self._unique_uri.is_known(url):
                    self.add_uri(CrawlUri(url))

        del self._current_uris[curi.url]

        for sink in self._sinks:
            sink.process_successful_crawl(curi)

    def process_not_found(self, curi):
        """
        Called when an URL was not found.

        This could mean, that the URL has been removed from the server. If so,
        do something about it!

        Override this method in the actual frontier implementation.
        """
        del self._current_uris[curi.url]
        self._ignore_uri(curi)

        for sink in self._sinks:
            sink.process_not_found(curi)

    def process_redirect(self, curi):
        """
        Called when there were too many redirects for an URL, or the site has
        note been updated since the last visit.

        In the latter case, update the internal uri and increase the priority
        level.
        """
        del self._current_uris[curi.url]

        if curi.status_code in [301, 302]:
            # simply ignore the URL. The URL that is being redirected to is
            # extracted and added in the processing
            self._ignore_uri(curi)

        if curi.status_code == 304:
            # the page has not been modified since the last visit! Update it
            # NOTE: prio increasing happens in the prioritizer
            self.update_uri(curi)

        for sink in self._sinks:
            sink.process_redirect(curi)

    def process_server_error(self, curi):
        """
        Called when there was some kind of server error.

        Override this method in the actual frontier implementation.
        """
        del self._current_uris[curi.url]
        self._ignore_uri(curi)

        for sink in self._sinks:
            sink.process_server_error(curi)


class SingleHostFrontier(AbstractBaseFrontier):
    """
    A frontier for crawling a single host.
    """

    def __init__(self, settings, log_handler):
        """
        Initialize the base frontier.
        """
        prio_clazz = import_class(settings.PRIORITIZER_CLASS)
        AbstractBaseFrontier.__init__(self, settings, log_handler,
                SQLiteSingleHostUriQueue(settings.FRONTIER_STATE_FILE),
                prio_clazz(settings))

        self._crawl_delay = settings.FRONTIER_CRAWL_DELAY_FACTOR
        self._min_delay = settings.FRONTIER_MIN_DELAY
        self._next_possible_crawl = time.time()

    def get_next(self):
        """
        Get the next URI.

        Only return the next URI if  we have waited enough.
        """
        if self._heap.qsize() < self._heap_min_size:
            self._update_heap()

        if time.time() >= self._next_possible_crawl:
            (next_date, next_uri) = self._heap.get_nowait()

            now = datetime.now(self._timezone)
            localized_next_date = self._timezone.fromutc(
                    datetime.utcfromtimestamp(next_date))

            if now < localized_next_date:
                # reschedule the uri for crawling
                self._heap.put_nowait((next_date, next_uri))
                raise Empty()

            self._next_possible_crawl = time.time() + self._min_delay
            return self._crawluri_from_uri(next_uri)

        raise Empty()

    def _update_heap(self):
        """
        Update the heap with URIs we should crawl.

        Note: it is possible that the heap is not full after it was updated!
        """
        self._logger.debug("frontier::Updating heap")
        for uri in self._front_end_queues.queue_head(n=50):

            (url, _etag, _mod_date, next_date, _prio) = uri

            if url not in self._current_uris:
                try:
                    self._add_to_heap(uri, next_date)
                except Full:
                    # heap is full, return to the caller
                    self._logger.error("singlehostfrontier::Heap is full " + \
                            "during update")
                    return

    def process_successful_crawl(self, curi):
        """
        Add the timebased politeness to this frontier.
        """
        AbstractBaseFrontier.process_successful_crawl(self, curi)
        now = time.time()
        self._next_possible_crawl = now + max(self._crawl_delay *
                curi.req_time, self._min_delay)
        self._logger.debug("singlehostfrontier::Next possible crawl: %s" %
                (self._next_possible_crawl,))


class MultipleHostFrontier(AbstractBaseFrontier):
    """
    A Frontier for crawling many hosts simultaneously.
    """

    def __init__(self, settings, log_handler):
        """
        Initialize the abstract base frontier and this implementation with the
        different configuration parameters.
        """
        prio_clazz = import_class(settings.PRIORITIZER_CLASS)
        AbstractBaseFrontier.__init__(self, settings, log_handler,
                SQLiteMultipleHostUriQueue(settings.FRONTIER_STATE_FILE),
                prio_clazz(settings))

        self._delay_factor = settings.FRONTIER_CRAWL_DELAY_FACTOR
        self._min_delay = settings.FRONTIER_MIN_DELAY
        self._num_active_queues = settings.FRONTIER_ACTIVE_QUEUES
        self._max_queue_budget = settings.FRONTIER_QUEUE_BUDGET
        self._budget_punishment = settings.FRONTIER_QUEUE_BUDGET_PUNISH

        self._queue_ids = []
        for (queue, _) in self._front_end_queues.get_all_queues():
            self._queue_ids.append(queue)

        qs_clazz = import_class(settings.QUEUE_SELECTOR_CLASS)
        self._backend_selector = qs_clazz(len(self._queue_ids))

        qa_clazz = import_class(settings.QUEUE_ASSIGNMENT_CLASS)
        self._backend_assignment = qa_clazz(self._dns_cache)

        self._current_queues = dict()
        self._current_queues_in_heap = []
        self._time_politeness = dict()
        self._budget_politeness = dict()

    def _uri_from_curi(self, curi):
        """
        Override the uri creation in order to assign the queue to it. Otherwise
        the uri would not end up in the correct queue.
        """
        uri = AbstractBaseFrontier._uri_from_curi(self, curi)
        (url, etag, mod_date, next_crawl_date, prio) = uri
        ident =  self._backend_assignment.get_identifier(url)

        queue = self._front_end_queues.add_or_create_queue(ident)
        if queue not in self._queue_ids:
            self._queue_ids.append(queue)
            self._backend_selector.reset_queues(len(self._queue_ids))
        return (url, queue, etag, mod_date, next_crawl_date, prio)

    def _add_to_heap(self, uri, next_date):
        """
        Override the base method since it only accepts the smaller tuples.
        """
        (url, queue, etag, mod_date, next_crawl_date, prio) = uri
        queue_free_uri = (url, etag, mod_date, next_crawl_date, prio)
        return AbstractBaseFrontier._add_to_heap(self, queue_free_uri,
                next_date)

    def get_next(self):
        """
        Get the next URI that is ready to be crawled.
        """
        if self._heap.qsize() < self._heap_min_size:
            self._update_heap()

        (_date, uri) = self._heap.get_nowait()
        return self._crawluri_from_uri(uri)

    def _update_heap(self):
        """
        Update the heap from the currently used queues. Respect the time based
        politeness and the queue's budget.

        The algorithm is as follows:

          1. Remove queues that are out of budget and add new ones

          2. Add all URIs to the heap that are crawlable with respect to the
              time based politeness
        """
        self._maybe_add_queues()
        self._cleanup_budget_politeness()

        now = time.mktime(datetime.now(self._timezone).timetuple())
        for q in self._time_politeness.keys():
            if now >= self._time_politeness[q] and \
                q not in self._current_queues_in_heap:

                # we may crawl from this queue!
                queue = self._current_queues[q]
                try:
                    (localized_next_date, next_uri) = queue.get_nowait()
                except Empty:
                    # this queue is empty! Remove it and check the next queue
                    self._remove_queue_from_memory(q)
                    continue

                if now < localized_next_date:
                    # reschedule the uri for crawling
                    queue.put_nowait((localized_next_date, next_uri))
                else:
                    # add this uri to the heap, i.e. it can be crawled
                    self._add_to_heap(next_uri, localized_next_date)
                    self._current_queues_in_heap.append(q)

    def _maybe_add_queues(self):
        """
        If there are free queue slots available, add inactive queues from the
        backend.
        """
        qcount = self._front_end_queues.get_queue_count()
        acount = len(self._current_queues)

        while self._num_active_queues > acount and acount < qcount:
            next_queue = self._get_next_queue()
            if next_queue:
                self._add_queue_from_storage(next_queue)
                self._logger.debug("multifrontier::Adding queue with id=%s" %
                        (next_queue,))
                acount = len(self._current_queues)
            else:
                break

    def _cleanup_budget_politeness(self):
        """
        Check if any queue has reached the `self._max_queue_budget` and replace
        those with queues from the storage.
        """
        removeable = []
        for q in self._budget_politeness.keys():
            if self._budget_politeness[q] <= 0:
                removeable.append(q)

        for rm_queue in removeable:
            next_queue = self._get_next_queue()
            if next_queue:
                self._add_queue_from_storage(next_queue)

            self._remove_queue_from_memory(rm_queue)
            self._logger.debug("multifrontier::Removing queue with id=%s" %
                    rm_queue)

    def _get_next_queue(self):
        """
        Get the next queue candidate.
        """
        for i in range(0, 10):
            next_id = self._backend_selector.get_queue()
            q = self._queue_ids[next_id]
            if q not in self._budget_politeness.keys():
                return q

        return None

    def _get_queue_for_url(self, url):
        """
        Determine the queue for a given `url`.
        """
        ident =  self._backend_assignment.get_identifier(url)
        return self._front_end_queues.get_queue_for_ident(ident)

    def _remove_queue_from_memory(self, queue):
        """
        Remove a queue from the internal memory buffers.
        """
        del self._time_politeness[queue]
        del self._budget_politeness[queue]
        del self._current_queues[queue]

    def _add_queue_from_storage(self, next_queue):
        """
        Called when a queue should be crawled from now on.
        """
        self._budget_politeness[next_queue] = self._max_queue_budget
        self._time_politeness[next_queue] = time.mktime(datetime.now(self._timezone).timetuple())
        self._current_queues[next_queue] = \
            PriorityQueue(maxsize=self._max_queue_budget)

        queue = self._current_queues[next_queue]

        for uri in self._front_end_queues.queue_head(next_queue,
                n=self._max_queue_budget):

            (_url, _queue, _etag, _mod_date, next_date, _prio) = uri
            localized_next_date = self._timezone.fromutc(
                    datetime.utcfromtimestamp(next_date))
            queue.put_nowait((time.mktime(localized_next_date.timetuple()), uri))

    def _update_politeness(self, curi):
        """
        Update all politeness rules.
        """
        uri = self._uri_from_curi(curi)
        (url, queue, etag, mod_date, next_crawl_date, prio) = uri

        if 200 <= curi.status_code < 500:
            self._budget_politeness[queue] -= 1
        if 500 <= curi.status_code < 600:
            self._budget_politeness[queue] -= self._budget_punishment

        now = datetime.now(self._timezone)
        delta_seconds = max(self._delay_factor * curi.req_time,
                self._min_delay)
        self._time_politeness[queue] = time.mktime((now + timedelta(seconds=delta_seconds)).timetuple())

        self._current_queues_in_heap.remove(queue)

    def process_successful_crawl(self, curi):
        """
        Crawling was successful, now update the politeness rules.
        """
        self._update_politeness(curi)
        AbstractBaseFrontier.process_successful_crawl(self, curi)

    def process_not_found(self, curi):
        """
        The page does not exist anymore!
        """
        self._update_politeness(curi)
        AbstractBaseFrontier.process_not_found(self, curi)

    def process_redirect(self, curi):
        """
        There was a redirect.
        """
        self._update_politeness(curi)
        AbstractBaseFrontier.process_server_error(self, curi)

    def process_server_error(self, curi):
        """
        Punish any server errors in the budget for this queue.
        """
        self._update_politeness(curi)
        AbstractBaseFrontier.process_server_error(self, curi)

########NEW FILE########
__FILENAME__ = log
#
# Copyright (c) 2011 Daniel Truemper truemped@googlemail.com
#
# logging.py 04-Feb-2011
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
"""
A simple pyzmq logging mixin.
"""

import logging


class LoggingMixin:
    """
    Simple mixin for adding logging methods to a class.
    """

    def __init__(self, pub_handler, log_level):
        """
        Initialize the logger.
        """
        self._logger = logging.getLogger()
        self._logger.addHandler(pub_handler)
        self._logger.setLevel(log_level)

########NEW FILE########
__FILENAME__ = master
#
# Copyright (c) 2011 Daniel Truemper truemped@googlemail.com
#
# master.py 31-Jan-2011
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
"""
A ZeroMQ master, i.e. the producer of URIs.
"""
import traceback
from Queue import Empty

from zmq.eventloop.ioloop import IOLoop, PeriodicCallback
from zmq.eventloop.zmqstream import ZMQStream

from spyder.core.constants import ZMQ_SPYDER_MGMT_WORKER
from spyder.core.constants import ZMQ_SPYDER_MGMT_WORKER_AVAIL
from spyder.core.constants import ZMQ_SPYDER_MGMT_WORKER_QUIT
from spyder.core.constants import ZMQ_SPYDER_MGMT_WORKER_QUIT_ACK
from spyder.core.constants import CURI_EUNCAUGHT_EXCEPTION
from spyder.core.messages import DataMessage
from spyder.core.log import LoggingMixin


class ZmqMaster(object, LoggingMixin):
    """
    This is the ZMQ Master implementation.

    The master will send :class:`DataMessage` object to the workers and receive
    the processed messages. Unknown links will then be added to the frontier.
    """

    def __init__(self, settings, identity, insocket, outsocket, mgmt, frontier,
            log_handler, log_level, io_loop):
        """
        Initialize the master.
        """
        LoggingMixin.__init__(self, log_handler, log_level)
        self._identity = identity
        self._io_loop = io_loop or IOLoop.instance()

        self._in_stream = ZMQStream(insocket, io_loop)
        self._out_stream = ZMQStream(outsocket, io_loop)

        self._mgmt = mgmt
        self._frontier = frontier

        self._running = False
        self._available_workers = []

        # periodically check if there are pending URIs to crawl
        self._periodic_update = PeriodicCallback(self._send_next_uri,
                settings.MASTER_PERIODIC_UPDATE_INTERVAL, io_loop=io_loop)
        # start this periodic callback when you are waiting for the workers to
        # finish
        self._periodic_shutdown = PeriodicCallback(self._shutdown_wait, 500,
                io_loop=io_loop)
        self._shutdown_counter = 0
        self._logger.debug("zmqmaster::initialized")

    def start(self):
        """
        Start the master.
        """
        self._mgmt.add_callback(ZMQ_SPYDER_MGMT_WORKER, self._worker_msg)
        self._in_stream.on_recv(self._receive_processed_uri)
        self._periodic_update.start()
        self._running = True
        self._logger.debug("zmqmaster::starting...")

    def stop(self):
        """
        Stop the master gracefully, i.e. stop sending more URIs that should get
        processed.
        """
        self._logger.debug("zmqmaster::stopping...")
        self._running = False
        self._periodic_update.stop()

    def shutdown(self):
        """
        Shutdown the master and notify the workers.
        """
        self._logger.debug("zmqmaster::shutdown...")
        self.stop()
        self._mgmt.publish(topic=ZMQ_SPYDER_MGMT_WORKER,
                identity=self._identity, data=ZMQ_SPYDER_MGMT_WORKER_QUIT)
        self._frontier.close()
        self._periodic_shutdown.start()

    def _shutdown_wait(self):
        """
        Callback called from `self._periodic_shutdown` in order to wait for the
        workers to finish.
        """
        self._shutdown_counter += 1
        if 0 == len(self._available_workers) or self._shutdown_counter > 5:
            self._periodic_shutdown.stop()
            self._logger.debug("zmqmaster::bye bye...")
            self._io_loop.stop()

    def close(self):
        """
        Close all open sockets.
        """
        self._in_stream.close()
        self._out_stream.close()

    def finished(self):
        """
        Return true if all uris have been processed and the master is ready to
        be shut down.
        """
        return not self._running

    def _worker_msg(self, msg):
        """
        Called when a worker has sent a :class:`MgmtMessage`.
        """
        if ZMQ_SPYDER_MGMT_WORKER_AVAIL == msg.data:
            self._available_workers.append(msg.identity)
            self._logger.info("zmqmaster::A new worker is available (%s)" %
                    msg.identity)
            self._send_next_uri()

        if ZMQ_SPYDER_MGMT_WORKER_QUIT_ACK == msg.data:
            if msg.identity in self._available_workers:
                self._available_workers.remove(msg.identity)
                self._logger.info("zmqmaster::Removing worker (%s)" %
                        msg.identity)

    def _send_next_uri(self):
        """
        See if there are more uris to process and send them to the workers if
        there are any.

        At this point there is a very small heuristic in order to maximize the
        throughput: try to keep the `self._out_stream._send_queue` full.
        """
        if not self._running:
            self._logger.error("Master is not running, not sending more uris")
            return

        num_workers = len(self._available_workers)

        if self._running and num_workers > 0:
            while self._out_stream._send_queue.qsize() < num_workers * 4:

                try:
                    next_curi = self._frontier.get_next()
                except Empty:
                    # well, frontier has nothing to process right now
                    self._logger.debug("zmqmaster::Nothing to crawl right now")
                    break

                self._logger.info("zmqmaster::Begin crawling next URL (%s)" %
                        next_curi.url)
                msg = DataMessage(identity=self._identity, curi=next_curi)
                self._out_stream.send_multipart(msg.serialize())

    def _receive_processed_uri(self, raw_msg):
        """
        Receive and reschedule an URI that has been processed. Additionally add
        all extracted URLs to the frontier.
        """
        msg = DataMessage(raw_msg)
        self._logger.info("zmqmaster::Crawling URL (%s) finished" %
                msg.curi.url)

        try:
            if 200 <= msg.curi.status_code < 300:
                # we have some kind of success code! yay
                self._frontier.process_successful_crawl(msg.curi)
            elif 300 <= msg.curi.status_code < 400:
                # Some kind of redirect code. This will only happen if the number
                # of redirects exceeds settings.MAX_REDIRECTS
                self._frontier.process_redirect(msg.curi)
            elif 400 <= msg.curi.status_code < 500:
                # some kind of error where the resource could not be found.
                self._frontier.process_not_found(msg.curi)
            elif 500 <= msg.curi.status_code < 600:
                # some kind of server error
                self._frontier.process_server_error(msg.curi)
        except:
            self._logger.critical("zmqmaster::Uncaught exception in the sink")
            self._logger.critical("zmqmaster::%s" % (traceback.format_exc(),))
            msg.curi.status_code = CURI_EUNCAUGHT_EXCEPTION
            self._frontier.process_server_error(msg.curi)

        self._send_next_uri()

########NEW FILE########
__FILENAME__ = messages
#
# Copyright (c) 2011 Daniel Truemper truemped@googlemail.com
#
# messages.py 14-Jan-2011
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
"""
Definitions of messages that are being sent via ZeroMQ Sockets.

Plus some (de-)serialization helpers.
"""
from  thrift import TSerialization

from spyder.thrift.gen.ttypes import CrawlUri


class DataMessage(object):
    """
    Envelope class describing `data` messages.
    """

    def __init__(self, message=None, identity=None, curi=None):
        """
        Construct a new message.
        """
        if message is not None:
            self.identity = message[0]
            self.serialized_curi = message[1]
            self.curi = deserialize_crawl_uri(message[1])
        elif identity is not None or curi is not None:
            self.identity = identity
            self.curi = curi
        else:
            self.identity = self.curi = None

    def serialize(self):
        """
        Return a new message envelope from the class members.
        """
        return [self.identity, serialize_crawl_uri(self.curi)]

    def __eq__(self, other):
        return (self.identity == other.identity
            and self.curi == other.curi)


class MgmtMessage(object):
    """
    Envelope class describing `management` messages.
    """

    def __init__(self, message=None, topic=None, identity=None, data=None):
        """
        Construct a new message and if given parse the serialized message.
        """
        if message is not None:
            self.topic = message[0]
            self.identity = message[1]
            self.data = message[2]
        elif topic is not None or identity is not None or data is not None:
            self.topic = topic
            self.identity = identity
            self.data = data
        else:
            self.topic = self.identity = self.data = None

    def serialize(self):
        """
        Return a new message envelope from the class members.
        """
        return [self.topic, self.identity, self.data]

    def __eq__(self, other):
        return (self.topic == other.topic
            and self.identity == other.identity
            and self.data == other.data)


def deserialize_crawl_uri(serialized):
    """
    Deserialize a `CrawlUri` that has been serialized using Thrift.
    """
    return TSerialization.deserialize(CrawlUri(), serialized)


def serialize_crawl_uri(crawl_uri):
    """
    Serialize a `CrawlUri` using Thrift.
    """
    return TSerialization.serialize(crawl_uri)

########NEW FILE########
__FILENAME__ = mgmt
#
# Copyright (c) 2011 Daniel Truemper truemped@googlemail.com
#
# mgmt.py 10-Jan-2011
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
"""
A management module for managing components via ZeroMQ.
"""

from zmq.eventloop.ioloop import IOLoop
from zmq.eventloop.zmqstream import ZMQStream

from spyder.core.constants import ZMQ_SPYDER_MGMT_WORKER
from spyder.core.constants import ZMQ_SPYDER_MGMT_WORKER_QUIT
from spyder.core.constants import ZMQ_SPYDER_MGMT_WORKER_QUIT_ACK
from spyder.core.messages import MgmtMessage


class ZmqMgmt(object):
    """
    A :class:`ZMQStream` object handling the management sockets.
    """

    def __init__(self, subscriber, publisher, **kwargs):
        """
        Initialize the management interface.

        The `subscriber` socket is the socket used by the Master to send
        commands to the workers. The publisher socket is used to send commands
        to the Master.

        You have to set the `zmq.SUBSCRIBE` socket option yourself!
        """
        self._io_loop = kwargs.get('io_loop', IOLoop.instance())

        self._subscriber = subscriber
        self._in_stream = ZMQStream(self._subscriber, self._io_loop)

        self._publisher = publisher
        self._out_stream = ZMQStream(self._publisher, self._io_loop)

        self._callbacks = dict()

    def _receive(self, raw_msg):
        """
        Main method for receiving management messages.

        `message` is a multipart message where `message[0]` contains the topic,
        `message[1]` is 0 and `message[1]` contains the actual message.
        """
        msg = MgmtMessage(raw_msg)

        if msg.topic in self._callbacks:
            for callback in self._callbacks[msg.topic]:
                if callable(callback):
                    callback(msg)

        if ZMQ_SPYDER_MGMT_WORKER_QUIT == msg.data:
            self.stop()

    def start(self):
        """
        Start the MGMT interface.
        """
        self._in_stream.on_recv(self._receive)

    def stop(self):
        """
        Stop the MGMT interface.
        """
        self._in_stream.stop_on_recv()
        self.publish(topic=ZMQ_SPYDER_MGMT_WORKER, identity=None,
                data=ZMQ_SPYDER_MGMT_WORKER_QUIT_ACK)

    def close(self):
        """
        Close all open sockets.
        """
        self._in_stream.close()
        self._subscriber.close()
        self._out_stream.close()
        self._publisher.close()

    def add_callback(self, topic, callback):
        """
        Add a callback to the specified topic.
        """
        if not callable(callback):
            raise ValueError('callback must be callable')

        if topic not in self._callbacks:
            self._callbacks[topic] = []

        self._callbacks[topic].append(callback)

    def remove_callback(self, topic, callback):
        """
        Remove a callback from the specified topic.
        """
        if topic in self._callbacks and callback in self._callbacks[topic]:
            self._callbacks[topic].remove(callback)

    def publish(self, topic=None, identity=None, data=None):
        """
        Publish a message to the intended audience.
        """
        assert topic is not None
        assert data is not None
        msg = MgmtMessage(topic=topic, identity=identity, data=data)
        self._out_stream.send_multipart(msg.serialize())

########NEW FILE########
__FILENAME__ = prioritizer
#
# Copyright (c) 2011 Daniel Truemper truemped@googlemail.com
#
# prioritizer.py 01-Feb-2011
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
"""
URL prioritizers will calculate priorities of new URLs and the recrawling
priority.
"""


class SimpleTimestampPrioritizer(object):
    """
    A simple prioritizer where the priority is based on the timestamp of the
    next scheduled crawl of the URL.
    """

    def __init__(self, settings):
        """
        Initialize the number of available priorities and the priority delta
        between the priorities.
        """
        self._priorities = settings.PRIORITIZER_NUM_PRIORITIES
        self._default_priority = settings.PRIORITIZER_DEFAULT_PRIORITY
        self._delta = settings.PRIORITIZER_CRAWL_DELTA

    def calculate_priority(self, curi):
        """
        Calculate the new priority based on the :class:`CrawlUri`s current.

        This should return a tuple of
            (prio_level, prio)
        """
        if curi.current_priority and curi.status_code == 304:
            prio_level = min(curi.current_priority + 1, self._priorities)
        else:
            prio_level = 1
        prio = self._delta * prio_level
        return (prio_level, prio)

########NEW FILE########
__FILENAME__ = queueassignment
#
# Copyright (c) 2011 Daniel Truemper truemped@googlemail.com
#
# queueassignment.py 14-Mar-2011
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
"""
A collection of queue assignment classes.
"""
from urlparse import urlparse

from spyder.core.frontier import PROTOCOLS_DEFAULT_PORT


class HostBasedQueueAssignment(object):
    """
    This class will assign URLs to queues based on the hostnames.
    """

    def __init__(self, dnscache):
        """
        Initialize the assignment class.
        """
        self._dns_cache = dnscache

    def get_identifier(self, url):
        """
        Get the identifier for this url.
        """
        parsed_url = urlparse(url)
        return parsed_url.hostname


class IpBasedQueueAssignment(HostBasedQueueAssignment):
    """
    This class will assign urls to queues based on the server's IP address.
    """

    def __init__(self, dnscache):
        """
        Call the parent only.
        """
        HostBasedQueueAssignment.__init__(self, dnscache)

    def get_identifier(self, url):
        """
        Get the identifier for this url.
        """
        parsed_url = urlparse(url)

        # dns resolution and caching
        port = parsed_url.port
        if not port:
            port = PROTOCOLS_DEFAULT_PORT[parsed_url.scheme]

        (ip, port) = self._dns_cache["%s:%s" % (parsed_url.hostname, port)]

        return "%s" % (ip,)

########NEW FILE########
__FILENAME__ = queueselector
#
# Copyright (c) 2011 Daniel Truemper truemped@googlemail.com
#
# queueselector.py 25-Jan-2011
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
"""
A random queue selector.

Based on the number of queues (i.e. `FrontEnd queues`) return a number of the
queue with a bias towards lower numbered queues.
"""

import random


class BiasedQueueSelector(object):
    """
    The default queue selector based on radom selection with bias towards lower
    numbered queues.
    """

    def __init__(self, number_of_queues):
        """
        Initialize the queue selector with the number of available queues.
        """
        self._weights = []
        self._sum_weights = 0
        self._enumerate_weights = []
        self.reset_queues(number_of_queues)

    def reset_queues(self, number_of_queues):
        self._weights = [1 / (float(i) * number_of_queues)
            for i in range(1, number_of_queues + 1)]
        self._sum_weights = sum(self._weights)
        self._enumerate_weights = [(i, w) for i, w in enumerate(self._weights)]

    def get_queue(self):
        """
        Return the next queue to use.
        """
        random_weight = random.random() * self._sum_weights
        for (i, weight) in self._enumerate_weights:
            random_weight -= weight
            if random_weight < 0:
                return i

########NEW FILE########
__FILENAME__ = settings
#
# Copyright (c) 2011 Daniel Truemper truemped@googlemail.com
#
# settings.py 10-Jan-2011
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
"""
Simple class for working with settings.

Adopted from the Django based settings system.
"""

from spyder import defaultsettings


class Settings(object):
    """
    Class for handling spyder settings.
    """

    def __init__(self, settings=None):
        """
        Initialize the settings.
        """

        # load the default settings
        for setting in dir(defaultsettings):
            if setting == setting.upper():
                setattr(self, setting, getattr(defaultsettings, setting))

        # now override with user settings
        if settings is not None:
            for setting in dir(settings):
                if setting == setting.upper():
                    setattr(self, setting, getattr(settings, setting))

########NEW FILE########
__FILENAME__ = sink
#
# Copyright (c) 2011 Daniel Truemper truemped@googlemail.com
#
# sink.py 02-Feb-2011
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
"""
A sink of :class:`CrawlUri`.
"""


class AbstractCrawlUriSink(object):
    """
    Abstract sink. Only overwrite the methods you are interested in.
    """

    def process_successful_crawl(self, curi):
        """
        We have crawled a uri successfully. If there are newly extracted links,
        add them alongside the original uri to the frontier.
        """
        pass

    def process_not_found(self, curi):
        """
        The uri we should have crawled was not found, i.e. HTTP Error 404. Do
        something with that.
        """
        pass

    def process_redirect(self, curi):
        """
        There have been too many redirects, i.e. in the default config there
        have been more than 3 redirects.
        """
        pass

    def process_server_error(self, curi):
        """
        There has been a server error, i.e. HTTP Error 50x. Maybe we should try
        to crawl this uri again a little bit later.
        """
        pass

########NEW FILE########
__FILENAME__ = sqlitequeues
#
# Copyright (c) 2011 Daniel Truemper truemped@googlemail.com
#
# sqlitequques.py 24-Jan-2011
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
"""
This module contains the default queue storages backed by SQlite.
"""
import sqlite3 as sqlite


class QueueException(Exception):
    """
    Base exception for errors in the queues.
    """
    pass

class UriNotFound(QueueException):
    """
    Exception raised when an URI could not be found in the storage.
    """

    def __init__(self, url):
        self._url = url

    def __repr__(self):
        return "UriNotFound(%s)" % (self._url,)


class QueueNotFound(QueueException):
    """
    Exception raised when a ``queue`` could not be found.
    """

    def __init__(self, identifier):
        self._identifier = identifier

    def __repr__(self):
        return "QueueNotFound(%s)" % (self._identifier,)


class SQLiteStore(object):
    """
    Simple base class for sqlite based queue storages. This class basically
    creates the default pragmas and initializes all the unicode stuff.
    """

    def __init__(self, db_name):
        """
        Initialize the sqlite store.

        `db_name` can be a filanem or `:memory:` for in-memory databases.
        """
        self._connection = sqlite.connect(db_name)
        self._connection.row_factory = sqlite.Row
        self._connection.text_factory = sqlite.OptimizedUnicode
        self._cursor = self._connection.cursor()
        self._cursor.execute("PRAGMA encoding=\"UTF-8\";")
        self._cursor.execute("PRAGMA locking_mode=EXCLUSIVE;")

    def close(self):
        """
        Close the SQLite connection.
        """
        self.checkpoint()
        self._connection.close()

    def checkpoint(self):
        """
        Checkpoint the database, i.e. commit everything.
        """
        self._connection.commit()


class SQLiteSingleHostUriQueue(SQLiteStore):
    """
    This is a queue that can be used for crawling a single host.

    Internally there is only one queue for all URLs. Each URL is represented as
    a tuple of the form: ``uri = (url, etag, mod_date, next_date, priority)``.

    The queue is ordered using the ``next_date`` in ascending fashion.
    """

    def __init__(self, db_name):
        """
        Initialize the simple uri queue.

        This is a single queue working only with one host!
        """
        SQLiteStore.__init__(self, db_name)

        # create the tables if they do not exist
        self._cursor.executescript("""
                CREATE TABLE IF NOT EXISTS queue(
                    url TEXT PRIMARY KEY ASC,
                    etag TEXT,
                    mod_date INTEGER,
                    next_date INTEGER,
                    priority INTEGER
                );

                CREATE INDEX IF NOT EXISTS queue_fifo ON queue(
                    next_date ASC,
                    priority ASC
                );
                """)

    def add_uri(self, uri):
        """
        Add a uri to the specified queue.
        """
        (url, etag, mod_date, next_date, prio) = uri
        self._cursor.execute("""INSERT INTO queue
                (url, etag, mod_date, next_date, priority) VALUES
                (?, ?, ?, ?, ?)""", (url, etag, mod_date, next_date, prio))

    def add_uris(self, urls):
        """
        Add a list of uris.
        """
        self._cursor.executemany("""INSERT INTO queue
                (url, etag, mod_date, next_date, priority) VALUES
                (?, ?, ?, ?, ?)""", urls)

    def update_uri(self, uri):
        """
        Update the uri.
        """
        (url, etag, mod_date, next_date, prio) = uri
        self._cursor.execute("""UPDATE queue SET
                etag=?, mod_date=?, next_date=?, priority=?
                WHERE url=?""", (etag, mod_date, next_date, prio, url))

    def update_uris(self, uris):
        """
        Update the list of uris in the database.
        """
        update_uris = [(etag, mod_date, next_date, priority, url)
            for (url, etag, mod_date, next_date, priority) in uris]
        self._cursor.executemany("""UPDATE queue SET
                etag=?, mod_date=?, next_date=?, priority=?
                WHERE url=?""", update_uris)

    def ignore_uri(self, url, status):
        """
        Called when an URI should be ignored. This is usually the case when
        there is a HTTP 404 or recurring HTTP 500's.
        """
        self.update_uri((url, None, None, status, 1))

    def queue_head(self, n=1, offset=0):
        """
        Return the top `n` elements from the queue. By default, return the top
        element from the queue.

        If you specify `offset` the first `offset` entries are ignored.

        Any entries with a `next_date` below `1000` are being ignored. This
        enables the crawler to ignore URIs _and_ storing the status code.
        """
        self._cursor.execute("""SELECT * FROM queue
                WHERE next_date > 1000
                ORDER BY next_date ASC
                LIMIT ?
                OFFSET ?""", (n, offset))
        for row in self._cursor:
            yield (row['url'], row['etag'], row['mod_date'],
                row['next_date'], row['priority'])

    def remove_uris(self, uris):
        """
        Remove all uris.
        """
        del_uris = [(url,) for (url, _etag, _mod_date, _next_date, _priority)
            in uris]
        self._cursor.executemany("DELETE FROM queue WHERE url=?",
                del_uris)

    def __len__(self):
        """
        Calculate the number of known uris.
        """
        cursor = self._cursor.execute("""SELECT count(url) FROM queue""")
        return cursor.fetchone()[0]

    def all_uris(self):
        """
        A generator for iterating over all available urls.

        Note: does not return the full uri object, only the url. This will be
        used to refill the unique uri filter upon restart.
        """
        self._cursor.execute("""SELECT url FROM queue""")
        for row in self._cursor:
            yield row['url']

    def get_uri(self, url):
        """
        Mostly for debugging purposes.
        """
        self._cursor.execute("SELECT * FROM queue WHERE url=?",
                (url,))
        row = self._cursor.fetchone()
        if row:
            return (row['url'], row['etag'], row['mod_date'], row['next_date'],
                    row['priority'])
        raise UriNotFound(url)


class SQLiteMultipleHostUriQueue(SQLiteStore):
    """
    A queue storage for multiple queues that can be used for crawling multiple
    hosts simultaneously.

    Internally all URLs are being stored in one table. Each queue has its own
    INTEGER identifier.

    Each URL is represented as a tuple of the form
    ``uri = (url, queue, etag, mod_date, next_date, priority)``.

    The queue is ordered using the ``next_date`` in ascending fashion.
    """

    def __init__(self, db_name):
        """
        Initialize the simple uri queue.

        This is a single queue working only with one host!
        """
        SQLiteStore.__init__(self, db_name)

        # create the tables if they do not exist
        self._cursor.executescript("""
                CREATE TABLE IF NOT EXISTS queues(
                    url TEXT PRIMARY KEY ASC,
                    queue INTEGER,
                    etag TEXT,
                    mod_date INTEGER,
                    next_date INTEGER,
                    priority INTEGER
                );

                CREATE TABLE IF NOT EXISTS queue_identifiers(
                    queue INTEGER,
                    identifier TEXT,
                    PRIMARY KEY (queue, identifier)
                );

                CREATE INDEX IF NOT EXISTS queue_fifo ON queues(
                    queue,
                    next_date ASC
                );
                """)

    def add_uri(self, uri):
        """
        Add the uri to the given queue.
        """
        self._cursor.execute("""INSERT INTO queues
                (url, queue, etag, mod_date, next_date, priority) VALUES
                (?, ?, ?, ?, ?, ?)""", uri)

    def add_uris(self, uris):
        """
        Add the list of uris to the given queue.
        """
        self._cursor.executemany("""INSERT INTO queues
                (url, queue, etag, mod_date, next_date, priority) VALUES
                (?, ?,  ?, ?, ?, ?)""", uris)

    def update_uri(self, uri):
        """
        Update the uri.
        """
        (url, queue, etag, mod_date, next_date, prio) = uri
        self._cursor.execute("""UPDATE queues SET queue=?,
                etag=?, mod_date=?, next_date=?, priority=?
                WHERE url=?""", (queue, etag, mod_date, next_date, prio, url))

    def update_uris(self, uris):
        """
        Update the list of uris in the database.
        """
        update_uris = [(queue, etag, mod_date, next_date, priority, url)
            for (url, queue, etag, mod_date, next_date, priority) in uris]
        self._cursor.executemany("""UPDATE queues SET queue=?,
                etag=?, mod_date=?, next_date=?, priority=?
                WHERE url=?""", update_uris)

    def ignore_uri(self, url, status):
        """
        Called when an URI should be ignored. This is usually the case when
        there is a HTTP 404 or recurring HTTP 500's.
        """
        self.update_uri((url, None, None, None, status, 1))

    def queue_head(self, queue, n=1, offset=0):
        """
        Return the top `n` elements from the `queue`. By default, return the top
        element from the queue.

        If you specify `offset` the first `offset` entries are ignored.

        Any entries with a `next_date` below `1000` are being ignored. This
        enables the crawler to ignore URIs _and_ storing the status code.
        """
        self._cursor.execute("""SELECT * FROM queues
                WHERE queue = ?
                AND next_date > 1000
                ORDER BY next_date ASC
                LIMIT ?
                OFFSET ?""", (queue, n, offset))
        for row in self._cursor:
            yield (row['url'], row['queue'], row['etag'], row['mod_date'],
                row['next_date'], row['priority'])

    def remove_uris(self, uris):
        """
        Remove all uris.
        """
        del_uris = [(url,) for (url, _queue, _etag, _mod_date, _queue,
                _next_date) in uris]
        self._cursor.executemany("DELETE FROM queues WHERE url=?",
                del_uris)

    def qsize(self, queue=None):
        """
        Calculate the number of known uris. If `queue` is given, only return
        the size of this queue, otherwise the size of all queues is returned.
        """
        if queue:
            cursor = self._cursor.execute("""SELECT count(url) FROM queues
                    WHERE queue=?""", (queue,))
        else:
            cursor = self._cursor.execute("""SELECT count(url) FROM queues""")
        return cursor.fetchone()[0]

    def all_uris(self, queue=None):
        """
        A generator for iterating over all available urls.

        Note: does not return the full uri object, only the url. This will be
        used to refill the unique uri filter upon restart.
        """
        if queue:
            self._cursor.execute("""SELECT url FROM queues WHERE queue=?""",
                    queue)
        else:
            self._cursor.execute("""SELECT url FROM queues""")
        for row in self._cursor:
            yield row['url']

    def get_uri(self, url):
        """
        Return the *URI* tuple for the given ``URL``.
        """
        self._cursor.execute("SELECT * FROM queues WHERE url=?",
                (url,))
        row = self._cursor.fetchone()
        if row:
            return (row['url'], row['queue'], row['etag'], row['mod_date'],
                    row['next_date'], row['priority'])
        raise UriNotFound(url)

    def get_all_queues(self):
        """
        A generator for iterating over all available queues.

        This will return `(queue, identifier)` as `(int, str)`
        """
        self._cursor.execute("SELECT * FROM queue_identifiers")
        for row in self._cursor:
            yield (row['queue'], row['identifier'])

    def get_queue_count(self):
        """
        Return the number of available queues.
        """
        self._cursor.execute("SELECT count(queue) as queues FROM queue_identifiers")
        row = self._cursor.fetchone()

        if row['queues']:
            return row['queues']
        return 0

    def get_queue_for_ident(self, identifier):
        """
        Get the ``queue`` for the given `identifier` if there is one.
        Raises a `QueueNotFound` error if there is no queue with the
        identifier.
        """
        self._cursor.execute("""SELECT queue FROM queue_identifiers WHERE
                identifier=?""", (identifier,))

        row = self._cursor.fetchone()
        if row:
            return row['queue']
        raise QueueNotFound(identifier)

    def add_or_create_queue(self, identifier):
        """
        Add a new queue with the ``identifier``. If the queue already exists,
        it's `id` is returned, otherwise the `id` of the newly created queue.
        """
        try:
            return self.get_queue_for_ident(identifier)
        except QueueNotFound:
            pass

        self._cursor.execute("SELECT MAX(queue) AS id FROM queue_identifiers")
        row = self._cursor.fetchone()

        if row['id']:
            next_id = row['id'] + 1
        else:
            next_id = 1

        self._cursor.execute("INSERT INTO queue_identifiers VALUES(?,?)",
            (next_id, identifier))
        return next_id

########NEW FILE########
__FILENAME__ = uri_uniq
#
# Copyright (c) 2011 Daniel Truemper truemped@googlemail.com
#
# uri_uniq.py 31-Jan-2011
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
"""
A simple filter for unique uris.
"""

import hashlib


class UniqueUriFilter(object):
    """
    A simple filter for unique uris. This is used to keep the frontier clean.
    """

    def __init__(self, hash_method, depth=3):
        """
        Create a new unique uri filter using the specified `hash_method`.

        `depth` is used to determine the number of nested dictionaries to use.
        Example: using `depth=2` the dictionary storing all hash values use the
        first 2 bytes as keys, i.e. if the hash value is `abc` then

          hashes[a][b] = [c,]

        This should reduce the number of lookups within a dictionary.
        """
        self._hash = hash_method
        self._depth = depth
        self._hashes = dict()

    def is_known(self, url, add_if_unknown=False):
        """
        Test whether the given `url` is known. If not, store it from now on.
        """
        hash_method = hashlib.new(self._hash)
        hash_method.update(url)
        hash_value = hash_method.hexdigest()

        dictionary = self._hashes
        for i in range(0, self._depth):
            if hash_value[i] in dictionary:
                dictionary = dictionary[hash_value[i]]
            else:
                # unknown dict, add it now
                if i == self._depth - 1:
                    dictionary[hash_value[i]] = []
                else:
                    dictionary[hash_value[i]] = dict()
                dictionary = dictionary[hash_value[i]]

        # now dictionary is the list at the deepest level
        if hash_value[self._depth:] in dictionary:
            return True
        else:
            # since we still are here, only the nested list does not
            # contain the given rest. Now we know it
            if add_if_unknown:
                dictionary.append(hash_value[self._depth:])
            return False

########NEW FILE########
__FILENAME__ = worker
#
# Copyright (c) 2011 Daniel Truemper truemped@googlemail.com
#
# worker.py 10-Jan-2011
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
"""
This module contains a ZeroMQ based Worker abstraction.

The `ZmqWorker` class expects an incoming and one outgoing `zmq.socket` as well
as an instance of the `spyder.core.mgmt.ZmqMgmt` class.
"""
import traceback

from zmq.eventloop.ioloop import IOLoop
from zmq.eventloop.zmqstream import ZMQStream

from spyder.core.constants import ZMQ_SPYDER_MGMT_WORKER
from spyder.core.constants import ZMQ_SPYDER_MGMT_WORKER_QUIT
from spyder.core.log import LoggingMixin
from spyder.core.messages import DataMessage


class ZmqWorker(object, LoggingMixin):
    """
    This is the ZMQ worker implementation.

    The worker will register a :class:`ZMQStream` with the configured
    :class:`zmq.Socket` and :class:`zmq.eventloop.ioloop.IOLoop` instance.

    Upon `ZMQStream.on_recv` the configured `processors` will be executed
    with the deserialized context and the result will be published through the
    configured `zmq.socket`.
    """

    def __init__(self, insocket, outsocket, mgmt, processing, log_handler,
            log_level, io_loop=None):
        """
        Initialize the `ZMQStream` with the `insocket` and `io_loop` and store
        the `outsocket`.

        `insocket` should be of the type `zmq.socket.PULL` `outsocket` should
        be of the type `zmq.socket.PUB`

        `mgmt` is an instance of `spyder.core.mgmt.ZmqMgmt` that handles
        communication between master and worker processes.
        """
        LoggingMixin.__init__(self, log_handler, log_level)

        self._insocket = insocket
        self._io_loop = io_loop or IOLoop.instance()
        self._outsocket = outsocket

        self._processing = processing
        self._mgmt = mgmt
        self._in_stream = ZMQStream(self._insocket, self._io_loop)
        self._out_stream = ZMQStream(self._outsocket, self._io_loop)

    def _quit(self, msg):
        """
        The worker is quitting, stop receiving messages.
        """
        if ZMQ_SPYDER_MGMT_WORKER_QUIT == msg.data:
            self.stop()

    def _receive(self, msg):
        """
        We have a message!

        `msg` is a serialized version of a `DataMessage`.
        """
        message = DataMessage(msg)

        try:
            # this is the real work we want to do
            curi = self._processing(message.curi)
            message.curi = curi
        except:
            # catch any uncaught exception and only log it as CRITICAL
            self._logger.critical(
                    "worker::Uncaught exception executing the worker for URL %s!" %
                    (message.curi.url,))
            self._logger.critical("worker::%s" % (traceback.format_exc(),))

        # finished, now send the result back to the master
        self._out_stream.send_multipart(message.serialize())

    def start(self):
        """
        Start the worker.
        """
        self._mgmt.add_callback(ZMQ_SPYDER_MGMT_WORKER, self._quit)
        self._in_stream.on_recv(self._receive)

    def stop(self):
        """
        Stop the worker.
        """
        # stop receiving
        self._in_stream.stop_on_recv()
        self._mgmt.remove_callback(ZMQ_SPYDER_MGMT_WORKER, self._quit)
        # but work on anything we might already have
        self._in_stream.flush()
        self._out_stream.flush()

    def close(self):
        """
        Close all open sockets.
        """
        self._in_stream.close()
        self._insocket.close()
        self._out_stream.close()
        self._outsocket.close()


class AsyncZmqWorker(ZmqWorker):
    """
    Asynchronous version of the `ZmqWorker`.

    This worker differs in that the `self._processing` method should have two
    arguments: the message and the socket where the result should be sent to!
    """

    def _receive(self, msg):
        """
        We have a message!

        Instead of the synchronous version we do not handle serializing and
        sending the result to the `self._outsocket`. This has to be handled by
        the `self._processing` method.
        """
        message = DataMessage(msg)

        try:
            self._processing(message, self._out_stream)
        except:
            # catch any uncaught exception and only log it as CRITICAL
            self._logger.critical("Uncaught exception executing the worker!")
            self._logger.critical(traceback.format_exc())

########NEW FILE########
__FILENAME__ = defaultsettings
#
# Copyright (c) 2011 Daniel Truemper truemped@googlemail.com
#
# settings.py 10-Jan-2011
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
"""
Module for the default spyder settings.
"""
import logging

import pytz
from datetime import timedelta


# simple settings
LOG_LEVEL_MASTER = logging.DEBUG
LOG_LEVEL_WORKER = logging.DEBUG


# my local timezone
LOCAL_TIMEZONE = pytz.timezone('Europe/Berlin')


# Fetch Processor
USER_AGENT = "Mozilla/5.0 (compatible; spyder/0.1; " + \
    "+http://github.com/retresco/spyder)"
MAX_CLIENTS = 10
MAX_SIMULTANEOUS_CONNECTIONS = 1
FOLLOW_REDIRECTS = False
MAX_REDIRECTS = 3
USE_GZIP = True

# Proxy configuration. Both PROXY_HOST and PROXY_PORT must be set!
# PROXY_USERNAME and PROXY_PASSWORD are optional
PROXY_HOST = None
PROXY_PORT = None
PROXY_USERNAME = ''
PROXY_PASSWORD = ''

# Timeout settings for requests. See tornado HTTPRequest class for explanation
# defaults to 20.0 (float)
REQUEST_TIMEOUT = 20.0
CONNECT_TIMEOUT = REQUEST_TIMEOUT

VALIDATE_CERTIFICATES = True

#
# static dns mappings. Mapping has to be like this:
#    "hostname:port" => ("xxx.xxx.xxx.xxx", port)
#
STATIC_DNS_MAPPINGS = dict()
# Size of the DNS Cache.
SIZE_DNS_CACHE = 1000


# Callback for Master processes.
MASTER_CALLBACK = None
# Interval for the periodic updater (surviving times where nothing is to be
# crawled)
MASTER_PERIODIC_UPDATE_INTERVAL = 60 * 1000


# Frontier implementation to use
FRONTIER_CLASS = 'spyder.core.frontier.SingleHostFrontier'
# Filename storing the frontier state
FRONTIER_STATE_FILE = "./state.db"
# checkpointing interval (uris added/changed)
FRONTIER_CHECKPOINTING = 1000
# The number of URIs to keep inside the HEAP
FRONTIER_HEAP_SIZE = 500
# Minimum number of URIs in the HEAP
FRONTIER_HEAP_MIN = 100
# Download duration times this factor throttles the spyder
FRONTIER_CRAWL_DELAY_FACTOR = 4
# Minimum delay to wait before connecting the host again (s)
FRONTIER_MIN_DELAY = 5

# Number of simultaneously active queues
FRONTIER_ACTIVE_QUEUES = 100
# Number of URLs to be processed in one queue before it is put on hold
FRONTIER_QUEUE_BUDGET = 50
# Punishment of server errors with the queue
FRONTIER_QUEUE_BUDGET_PUNISH = 5


# Name of the prioritizer class to use
PRIORITIZER_CLASS = 'spyder.core.prioritizer.SimpleTimestampPrioritizer'
# The number of priority levels where URIs are being assigned to (lowest means
# highest priority)
PRIORITIZER_NUM_PRIORITIES = 10
# default priority for new urls
PRIORITIZER_DEFAULT_PRIORITY = 1
# Default crawl delta for known urls
PRIORITIZER_CRAWL_DELTA = timedelta(days=1)


# Name of the queue selector to use
QUEUE_SELECTOR_CLASS = 'spyder.core.queueselector.BiasedQueueSelector'


# Name of the queue assignment class to use
QUEUE_ASSIGNMENT_CLASS = 'spyder.core.queueassignment.HostBasedQueueAssignment'


# The pipeline of link extractors
SPYDER_EXTRACTOR_PIPELINE = [
    'spyder.processor.limiter.DefaultLimiter',
    'spyder.processor.htmllinkextractor.DefaultHtmlLinkExtractor',
    'spyder.processor.httpextractor.HttpExtractor',
]


# Default HTML Extractor settings
# maximum number of chars an element name may have
REGEX_LINK_XTRACTOR_MAX_ELEMENT_LENGTH = 64


# The pipeline of scope processors
SPYDER_SCOPER_PIPELINE = [
    'spyder.processor.scoper.RegexScoper',
    'spyder.processor.stripsessions.StripSessionIds',
    'spyder.processor.cleanupquery.CleanupQueryString',
]

# List of positive regular expressions for the crawl scope
REGEX_SCOPE_POSITIVE = [
]

# List of negative regular expressions for the crawl scope
REGEX_SCOPE_NEGATIVE = [
]


# List of 404 redirects
HTTP_EXTRACTOR_404_REDIRECT = [
]


# Whether to remove anchors from extracted urls.
REMOVE_ANCHORS_FROM_LINKS = True


# define a parent directory for unix sockets that will be created
PARENT_SOCKET_DIRECTORY = "/tmp"

#
# improved settings
# only edit if you are usually working behind a nuclear power plant's control
# panel

# ZeroMQ Master Push
ZEROMQ_MASTER_PUSH = "ipc://%s/spyder-zmq-master-push.sock" % \
    PARENT_SOCKET_DIRECTORY
ZEROMQ_MASTER_PUSH_HWM = 10

# ZeroMQ Fetcher
ZEROMQ_WORKER_PROC_FETCHER_PULL = ZEROMQ_MASTER_PUSH
ZEROMQ_WORKER_PROC_FETCHER_PUSH = "inproc://processing/fetcher/push"
ZEROMQ_WORKER_PROC_FETCHER_PUSH_HWM = 10

# ZeroMQ Extractor
ZEROMQ_WORKER_PROC_EXTRACTOR_PULL = ZEROMQ_WORKER_PROC_FETCHER_PUSH
ZEROMQ_WORKER_PROC_EXTRACTOR_PUB = "ipc://%s/spyder-zmq-master-sub.sock" % \
    PARENT_SOCKET_DIRECTORY
ZEROMQ_WORKER_PROC_EXTRACTOR_PUB_HWM = 10

# ZeroMQ Master Sub
ZEROMQ_MASTER_SUB = ZEROMQ_WORKER_PROC_EXTRACTOR_PUB

# ZeroMQ Management Sockets
ZEROMQ_MGMT_MASTER = "ipc://%s/spyder-zmq-mgmt-master.sock" % \
    (PARENT_SOCKET_DIRECTORY,)
ZEROMQ_MGMT_WORKER = "ipc://%s/spyder-zmq-mgmt-worker.sock" % \
    (PARENT_SOCKET_DIRECTORY,)

# ZeroMQ logging socket
ZEROMQ_LOGGING = "ipc://%s/spyder-logging.sock" % (PARENT_SOCKET_DIRECTORY,)

########NEW FILE########
__FILENAME__ = encoding
#
# Copyright (c) 2011 Daniel Truemper truemped@googlemail.com
#
# encoding.py 09-Feb-2011
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#


def get_content_type_encoding(curi):
    """
    Determine the content encoding based on the `Content-Type` Header.

    `curi` is the :class:`CrawlUri`.
    """
    content_type = "text/plain"
    charset = ""

    if curi.rep_header and "Content-Type" in curi.rep_header:
        (content_type, charset) = extract_content_type_encoding(
                curi.rep_header["Content-Type"])

    if charset == "" and curi.content_body and len(curi.content_body) >= 512:
        # no charset information in the http header
        first_bytes = curi.content_body[:512].lower()
        ctypestart = first_bytes.find("content-type")
        if ctypestart != -1:
            # there is a html header
            ctypestart = first_bytes.find("content=\"", ctypestart)
            ctypeend = first_bytes.find("\"", ctypestart + 9)
            return extract_content_type_encoding(
                    first_bytes[ctypestart + 9:ctypeend])

    return (content_type, charset)


def extract_content_type_encoding(content_type_string):
    """
    Extract the content type and encoding information.
    """
    charset = ""
    content_type = ""
    for part in content_type_string.split(";"):
        part = part.strip().lower()
        if part.startswith("charset"):
            charset = part.split("=")[1]
            charset = charset.replace("-", "_")
        else:
            content_type = part

    return (content_type, charset)

########NEW FILE########
__FILENAME__ = import_util
#
# Copyright (c) 2011 Daniel Truemper truemped@googlemail.com
#
# import_util.py 07-Feb-2011
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# under the License.
# All programs in this directory and
# subdirectories are published under the GNU General Public License as
# described below.
#
#
"""
A custom import method for importing modules or classes from a string.
"""


def custom_import(module):
    """
    A custom import method to import a module.
    see: stackoverflow.com: 547829/how-to-dynamically-load-a-python-class
    """
    mod = __import__(module)
    components = module.split('.')
    for comp in components[1:]:
        mod = getattr(mod, comp)
    return mod


def import_class(classstring):
    """
    Import a class using a `classstring`. This string is split by `.` and the
    last part is interpreted as class name.
    """
    (module_name, _sep, class_name) = classstring.rpartition('.')
    module = custom_import(module_name)
    return getattr(module, class_name)

########NEW FILE########
__FILENAME__ = logsink
#
# Copyright (c) 2011 Daniel Truemper truemped@googlemail.com
#
# logsink.py 03-Feb-2011
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
"""
Module for aggregating spyder logs.
"""
import logging
import logging.config
import signal
import os.path
import traceback

import zmq
from zmq.core.error import ZMQError
from zmq.eventloop.ioloop import IOLoop
from zmq.eventloop.zmqstream import ZMQStream


LOGGERS = {"default": logging.getLogger()}

LOGGERS['master'] = logging.getLogger('masterlog')
LOGGERS['worker'] = logging.getLogger('workerlog')


def log_zmq_message(msg):
    """
    Log a specific message.

    The message has the format::

        message = [topic, msg]

    `topic` is a string of the form::

        topic = "process.LEVEL.subtopics"
    """
    topic = msg[0].split(".")
    if len(topic) == 3:
        topic.append("SUBTOPIC")
    if topic[1] in LOGGERS:
        log = getattr(LOGGERS[topic[1]], topic[2].lower())
        log("%s - %s" % (topic[3], msg[1].strip()))
    else:
        log = getattr(LOGGERS['default'], topic[2].lower())
        log("%s: %s)" % (topic[3], msg[2].strip()))


def main(settings):
    """
    Initialize the logger sink.
    """

    if os.path.isfile('logging.conf'):
        logging.config.fileConfig('logging.conf')

    ctx = zmq.Context()
    io_loop = IOLoop.instance()

    log_sub = ctx.socket(zmq.SUB)
    log_sub.setsockopt(zmq.SUBSCRIBE, "")
    log_sub.bind(settings.ZEROMQ_LOGGING)

    log_stream = ZMQStream(log_sub, io_loop)

    log_stream.on_recv(log_zmq_message)

    def handle_shutdown_signal(_sig, _frame):
        """
        Called from the os when a shutdown signal is fired.
        """
        log_stream.stop_on_recv()
        log_stream.flush()
        io_loop.stop()

    # handle kill signals
    signal.signal(signal.SIGINT, handle_shutdown_signal)
    signal.signal(signal.SIGTERM, handle_shutdown_signal)

    try:
        io_loop.start()
    except ZMQError:
        LOGGERS['master'].debug("Caught a ZMQError. Hopefully during shutdown")
        LOGGERS['master'].debug(traceback.format_exc())

    log_stream.close()
    ctx.term()

########NEW FILE########
__FILENAME__ = masterprocess
#
# Copyright (c) 2011 Daniel Truemper truemped@googlemail.com
#
# masterprocess.py 31-Jan-2011
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
"""
This module contains the default architecture for master process.

The main task for masterprocesses is to create and run the **Frontier**.
Starting a master involves the following steps:

1. Bind to the configured |zmq| sockets
2. Start the management interface
3. Create the frontier
4. Start the master

Once the master is up and you have configured a ``settings.MASTER_CALLBACK``,
this method will be called before the master is really started, i.e. before the
``IOLoop.start()`` is called. This will allow you to insert *Seed* |urls|, e.g.
"""

import logging
import os
import signal
import socket
import traceback

import zmq
from zmq.core.error import ZMQError
from zmq.eventloop.ioloop import IOLoop
from zmq.log.handlers import PUBHandler

from spyder.import_util import import_class
from spyder.core.master import ZmqMaster
from spyder.core.mgmt import ZmqMgmt


def create_master_management(settings, zmq_context, io_loop):
    """
    Create the management interface for master processes.
    """
    listening_socket = zmq_context.socket(zmq.SUB)
    listening_socket.setsockopt(zmq.SUBSCRIBE, "")
    listening_socket.bind(settings.ZEROMQ_MGMT_WORKER)

    publishing_socket = zmq_context.socket(zmq.PUB)
    publishing_socket.bind(settings.ZEROMQ_MGMT_MASTER)

    return ZmqMgmt(listening_socket, publishing_socket, io_loop=io_loop)


def create_frontier(settings, log_handler):
    """
    Create the frontier to use.
    """
    frontier = import_class(settings.FRONTIER_CLASS)
    return frontier(settings, log_handler)


def main(settings):
    """
    Main method for master processes.
    """
    # create my own identity
    identity = "master:%s:%s" % (socket.gethostname(), os.getpid())

    ctx = zmq.Context()
    io_loop = IOLoop.instance()

    # initialize the logging subsystem
    log_pub = ctx.socket(zmq.PUB)
    log_pub.connect(settings.ZEROMQ_LOGGING)
    zmq_logging_handler = PUBHandler(log_pub)
    zmq_logging_handler.root_topic = "spyder.master"
    logger = logging.getLogger()
    logger.addHandler(zmq_logging_handler)
    logger.setLevel(settings.LOG_LEVEL_MASTER)

    logger.info("process::Starting up the master")

    mgmt = create_master_management(settings, ctx, io_loop)
    frontier = create_frontier(settings, zmq_logging_handler)

    publishing_socket = ctx.socket(zmq.PUSH)
    publishing_socket.setsockopt(zmq.HWM, settings.ZEROMQ_MASTER_PUSH_HWM)
    publishing_socket.bind(settings.ZEROMQ_MASTER_PUSH)

    receiving_socket = ctx.socket(zmq.SUB)
    receiving_socket.setsockopt(zmq.SUBSCRIBE, "")
    receiving_socket.bind(settings.ZEROMQ_MASTER_SUB)

    master = ZmqMaster(settings, identity, receiving_socket,
            publishing_socket, mgmt, frontier, zmq_logging_handler,
            settings.LOG_LEVEL_MASTER, io_loop)

    def handle_shutdown_signal(_sig, _frame):
        """
        Called from the os when a shutdown signal is fired.
        """
        master.shutdown()
        # zmq 2.1 stops blocking calls, restart the ioloop
        io_loop.start()

    # handle kill signals
    signal.signal(signal.SIGINT, handle_shutdown_signal)
    signal.signal(signal.SIGTERM, handle_shutdown_signal)

    if settings.MASTER_CALLBACK:
        callback = import_class(settings.MASTER_CALLBACK)
        callback(settings, ctx, io_loop, frontier)

    mgmt.start()
    master.start()

    # this will block until the master stops
    try:
        io_loop.start()
    except ZMQError:
        logger.debug("Caught a ZMQError. Hopefully during shutdown")
        logger.debug(traceback.format_exc())

    master.close()
    mgmt.close()

    logger.info("process::Master is down.")
    log_pub.close()

    ctx.term()

########NEW FILE########
__FILENAME__ = cleanupquery
#
# Copyright (c) 2011 Daniel Truemper truemped@googlemail.com
#
# cleanupquery.py 14-Apr-2011
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
#
"""
Processor to clean up the query string. At this point we want to strip any
trailing '?' or '&' and optionally remove any anchors from it.
"""
from spyder.core.constants import CURI_EXTRACTED_URLS


class CleanupQueryString(object):
    """
    The processor for cleaning up the query string.
    """

    def __init__(self, settings):
        """
        Initialize me.
        """
        self._remove_anchors = settings.REMOVE_ANCHORS_FROM_LINKS

    def __call__(self, curi):
        """
        Remove any obsolete stuff from the query string.
        """
        if CURI_EXTRACTED_URLS not in curi.optional_vars:
            return curi

        urls = []
        for raw_url in curi.optional_vars[CURI_EXTRACTED_URLS].split('\n'):
            urls.append(self._cleanup_query_string(raw_url))

        curi.optional_vars[CURI_EXTRACTED_URLS] = "\n".join(urls)
        return curi

    def _cleanup_query_string(self, raw_url):
        """
        """
        url = raw_url
        if self._remove_anchors:
            begin = raw_url.find("#")
            if begin > -1:
                url = raw_url[:begin]

        if len(url) == 0:
            return raw_url

        while url[-1] == '?' or url[-1] == '&':
            return url[:-1]

        return url

########NEW FILE########
__FILENAME__ = fetcher
#
# Copyright (c) 2011 Daniel Truemper truemped@googlemail.com
#
# fetcher.py 14-Jan-2011
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
"""
Module for downloading content from the web.

TODO: document pycurls features, i.e. what it can download.
"""

import logging

from urlparse import urlsplit

from tornado.httpclient import AsyncHTTPClient, HTTPRequest
from tornado.httputil import HTTPHeaders

from zmq.eventloop.ioloop import IOLoop

from spyder.core.constants import CURI_SITE_USERNAME
from spyder.core.constants import CURI_SITE_PASSWORD
from spyder.time import deserialize_date_time

LOG = logging.getLogger('fetcher')


class FetchProcessor(object):
    """
    A processing class for downloading all kinds of stuff from the web.
    """

    def __init__(self, settings, io_loop=None):
        """
        Initialize the members.
        """
        self._user_agent = settings.USER_AGENT
        assert self._user_agent

        self._io_loop = io_loop or IOLoop.instance()

        self._follow_redirects = settings.FOLLOW_REDIRECTS
        self._max_redirects = settings.MAX_REDIRECTS
        self._gzip = settings.USE_GZIP

        if settings.PROXY_HOST:
            proxy_port = settings.PROXY_PORT
            assert proxy_port
            assert isinstance(proxy_port, int)

            self._proxy_configuration = dict(
                    host = settings.PROXY_HOST,
                    port = settings.PROXY_PORT,
                    user = settings.PROXY_USERNAME,
                    password = settings.PROXY_PASSWORD
                    )

        self._validate_cert = settings.VALIDATE_CERTIFICATES
        self._request_timeout = settings.REQUEST_TIMEOUT
        self._connect_timeout = settings.CONNECT_TIMEOUT

        max_clients = settings.MAX_CLIENTS
        max_simultaneous_connections = settings.MAX_SIMULTANEOUS_CONNECTIONS

        self._client = AsyncHTTPClient(self._io_loop,
            max_clients=max_clients,
            max_simultaneous_connections=max_simultaneous_connections)

    def __call__(self, msg, out_stream):
        """
        Work on the current `DataMessage` and send the result to `out_stream`.
        """
        # prepare the HTTPHeaders
        headers = prepare_headers(msg)

        last_modified = None
        if msg.curi.req_header:
            # check if we have a date when the page was last crawled
            if "Last-Modified" in msg.curi.req_header:
                last_modified = deserialize_date_time(
                        msg.curi.req_header["Last-Modified"])

        # check if we have username and password present
        auth_username = None
        auth_password = None
        if msg.curi.optional_vars and \
            CURI_SITE_USERNAME in msg.curi.optional_vars and \
            CURI_SITE_PASSWORD in msg.curi.optional_vars:

            auth_username = msg.curi.optional_vars[CURI_SITE_USERNAME]
            auth_password = msg.curi.optional_vars[CURI_SITE_PASSWORD]

        # create the request
        request = HTTPRequest(msg.curi.effective_url,
                method="GET",
                headers=headers,
                auth_username=auth_username,
                auth_password=auth_password,
                if_modified_since=last_modified,
                follow_redirects=self._follow_redirects,
                max_redirects=self._max_redirects,
                user_agent=self._user_agent,
                request_timeout = self._request_timeout,
                connect_timeout = self._connect_timeout,
                validate_cert = self._validate_cert)

        if hasattr(self, '_proxy_configuration'):
            request.proxy_host = self._proxy_configuration['host']
            request.proxy_port = self._proxy_configuration['port']
            request.proxy_username = \
                    self._proxy_configuration.get('user', None)
            request.proxy_password = \
                    self._proxy_configuration.get('password', None)

        LOG.info("proc.fetch::request for %s" % msg.curi.url)
        self._client.fetch(request, handle_response(msg, out_stream))


def prepare_headers(msg):
    """
    Construct the :class:`HTTPHeaders` with all the necessary information for
    the request.
    """
    # construct the headers
    headers = HTTPHeaders()

    if msg.curi.req_header:
        # check if we have a previous Etag
        if "Etag" in msg.curi.req_header:
            headers["If-None-Match"] = \
                msg.curi.req_header["Etag"]

    # manually set the Host header since we are requesting using an IP
    host = urlsplit(msg.curi.url).hostname
    if host is None:
        LOG.error("proc.fetch::cannot extract hostname from url '%s'" %
                msg.curi.url)
    else:
        headers["Host"] = host

    return headers


def handle_response(msg, out_stream):
    """
    Decorator for the actual callback function that will extract interesting
    info and forward the response.
    """
    def handle_server_response(response):
        """
        The actual callback function.

        Extract interesting info from the response using
        :meth:`extract_info_from_response` and forward the result to the
        `out_stream`.
        """
        extract_info_from_response(response, msg)
        LOG.info("proc.fetch::response for %s (took '%s'ms)" %
                (msg.curi.url, response.request_time))
        if response.code >= 400:
            LOG.error("proc.fetch::response error: %s", response)
        out_stream.send_multipart(msg.serialize())

    return handle_server_response


def extract_info_from_response(response, msg):
    """
    Extract the interesting information from a HTTPResponse.
    """
    msg.curi.status_code = response.code
    msg.curi.req_header = response.request.headers
    msg.curi.rep_header = response.headers
    msg.curi.req_time = response.request_time
    msg.curi.queue_time = response.time_info["queue"]
    msg.curi.content_body = response.body

    return msg

########NEW FILE########
__FILENAME__ = htmllinkextractor
#
# Copyright (c) 2011 Daniel Truemper truemped@googlemail.com
#
# htmlextractor.py 21-Jan-2011
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
"""
The :class:`DefaultHtmlLinkExtractor` will try to extract new links from the
``curi.content_body``. In order to find them two regular expressions are used.

1. The ``RELEVANT_TAG_EXTRACTOR`` extracts the following tags:
    - ``<script>..</script>``
    - ``<style>..</style>``
    - ``<meta>``
    - or any other open tag with at least one attribute (e.g. not ``<br>``).

2. The ``LINK_EXTRACTOR`` extracts links from tags using `href` or `src`
attributes.

If the link is relative, the appropriate prefix is automatically added here.

The regular expressions have been adopted from Heritrix. See the Heritrix 3
source code:

``modules/src/main/java/org/archive/modules/extractor/ExtractorHTML.java``

.. note:: Heritrix has a newer way of extracting links, i.e. with different
    regular expressions. Since these are working for me at the moment, I am
    fine with it.
"""
import re
import htmlentitydefs

import urlparse

from spyder.core.constants import CURI_EXTRACTED_URLS
from spyder.core.constants import CURI_OPTIONAL_TRUE, CURI_EXTRACTION_FINISHED
from spyder.encoding import get_content_type_encoding

# Maximum number of chars an element name may have
MAX_ELEMENT_REPLACE = "MAX_ELEMENT_REPLACE"

# Pattern for extracting relevant tags from HTML
#
# This pattern extracts:
#  1: <script>...</script>
#  2: <style>...</style>
#  3: <meta...>
#  4: any other open tag with at least one attribute
#     (eg matches "<a href='boo'>" but not "</a>" or "<br>")
#
# Groups in this pattern:
#
#  1: script src=foo>boo</script
#  2: just the script open tag
#  3: style type=moo>zoo</style
#  4: just the style open tag
#  5: entire other tag, without '<' '>'
#  6: element
#  7: meta
#  8: !-- comment --
RELEVANT_TAG_EXTRACTOR = "<(?:((script[^>]*)>[^(</script)]*</script)" + "|" + \
    "((style[^/]*)>[^(</style)]*</style)" + "|" + \
    "(((meta)|(?:\\w{1,MAX_ELEMENT_REPLACE}))\\s+[^>]*)" + "|" + \
    "(!--.*?--))>"


# The simpler pattern to extract links from tags
#
# Groups in this expression:
#
#  1: the attribute name
#  2: href | src
#  3: the url in quotes
LINK_EXTRACTOR = "(\w+)[^>]*?(?:(href|src))\s*=\s*" + \
    "(?:(\"[^\"]+\"|'[^']+'))"


class DefaultHtmlLinkExtractor(object):
    """
    The default extractor for Links from HTML pages.

    The internal regular expressions currently are not modifiable. Only the
    maximum length of an opening tag can be configured using the
    ``settings.REGEX_LINK_XTRACTOR_MAX_ELEMENT_LENGTH``.
    """

    def __init__(self, settings):
        """
        Initialize the regular expressions.
        """
        max_size = settings.REGEX_LINK_XTRACTOR_MAX_ELEMENT_LENGTH
        self._tag_extractor = re.compile(
                RELEVANT_TAG_EXTRACTOR.replace(MAX_ELEMENT_REPLACE,
                    str(max_size)), re.I | re.S)

        self._link_extractor = re.compile(LINK_EXTRACTOR, re.I | re.S)
        self._base_url = ""

    def __call__(self, curi):
        """
        Actually extract links from the html content if the content type
        matches.
        """
        if not self._restrict_content_type(curi):
            return curi

        if CURI_EXTRACTION_FINISHED in curi.optional_vars and \
            curi.optional_vars[CURI_EXTRACTION_FINISHED] == CURI_OPTIONAL_TRUE:
            return curi

        (_type, encoding) = get_content_type_encoding(curi)

        try:
            content = curi.content_body.decode(encoding)
        except Exception:
            content = curi.content_body

        parsed_url = urlparse.urlparse(curi.url)
        self._base_url = curi.url

        # iterate over all tags
        for tag in self._tag_extractor.finditer(content):

            if tag.start(8) > 0:
                # a html comment, ignore
                continue

            elif tag.start(7) > 0:
                # a meta tag
                curi = self._process_meta(curi, parsed_url, content,
                        (tag.start(5), tag.end(5)))

            elif tag.start(5) > 0:
                # generic <whatever tag
                curi = self._process_generic_tag(curi, parsed_url, content,
                        (tag.start(6), tag.end(6)),
                        (tag.start(5), tag.end(5)))

            elif tag.start(1) > 0:
                # <script> tag
                # TODO no script handling so far
                pass

            elif tag.start(3) > 0:
                # <style> tag
                # TODO no tag handling so far
                pass

        return curi

    def _process_generic_tag(self, curi, parsed_url, content,
            element_name_tuple, element_tuple):
        """
        Process a generic tag.

        This can be anything but `meta`, `script` or `style` tags.

        `content` is the decoded content body.
        `element_name_tuple` is a tuple containing (start,end) integers of
            the current tag name.
        `element_tuple` is a tuple containing (start,end) integers of the
            current element
        """
        (start, end) = element_name_tuple
        el_name = content[start:end]
        if "a" == el_name.lower():
            curi = self._extract_links(curi, parsed_url, content,
                    element_tuple)
        elif "base" == el_name.lower():
            self._base_url = self._get_links(content, element_tuple)[0]

        return curi

    def _get_links(self, content, element_tuple):
        """
        Do the actual link extraction and return the list of links.

        `content` is the decoded content body.
        `element_tuple` is a tuple containing (start,end) integers of the
            current element
        """
        links = []
        (start, end) = element_tuple
        element = self._unescape_html(content[start:end])

        for link_candidate in self._link_extractor.finditer(element):
            link = link_candidate.group(3)[1:-1]
            if link.find("mailto:") > -1 or link.find("javascript:") > -1:
                continue
            if link.find("://") == -1:
                link = urlparse.urljoin(self._base_url, link)
            links.append(link)

        return links

    def _extract_links(self, curi, parsed_url, content, element_tuple):
        """
        Extract links from an element, e.g. href="" attributes.
        """
        links = self._get_links(content, element_tuple)

        linkstring = "\n".join(links).encode('ascii', 'replace')
        if not CURI_EXTRACTED_URLS in curi.optional_vars:
            curi.optional_vars[CURI_EXTRACTED_URLS] = linkstring
        else:
            curi.optional_vars[CURI_EXTRACTED_URLS] += "\n" + linkstring

        return curi

    def _process_meta(self, curi, _parsed_url, _content, _element_tuple):
        """
        Process a meta tag.
        """
        return curi

    def _restrict_content_type(self, curi):
        """
        Decide based on the `CrawlUri`s Content-Type whether we want to process
        it.
        """
        allowed = ["text/html", "application/xhtml", "text/vnd.wap.wml",
            "application/vnd.wap.wml", "application/vnd.wap.xhtm"]
        (ctype, _enc) = get_content_type_encoding(curi)
        return ctype in allowed

    def _unescape_html(self, link):
        """
        Unescape the link.

        keep &amp;, &gt;, &lt; in the source code.

        http://effbot.org/zone/re-sub.htm#unescape-html
        """
        def fixup(m):
            text = m.group(0)
            if text[:2] == "&#":
                # character reference
                try:
                    if text[:3] == "&#x":
                        return unichr(int(text[3:-1], 16))
                    else:
                        return unichr(int(text[2:-1]))
                except ValueError:
                    pass
            else:
                # named entity
                try:
                    text = unichr(htmlentitydefs.name2codepoint[text[1:-1]])
                except KeyError:
                    pass
            return text
        return re.sub("&#?\w+;", fixup, link)

########NEW FILE########
__FILENAME__ = httpextractor
#
# Copyright (c) 2010 Daniel Truemper truemped@googlemail.com
#
# httpextractor.py 17-Mar-2011
#
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
#
#
"""
Link extractor for detecting links in HTTP codes.

The main use case for this are HTTP redirects, e.g. In the case of a redirect
the HTTP status code ``30X`` is present and the ``Location`` header indicates
the new location.
"""
import urlparse

from spyder.core.constants import CURI_EXTRACTED_URLS


class HttpExtractor(object):
    """
    The processor for extracting links from ``HTTP`` headers.
    """

    def __init__(self, settings):
        """
        Initialize the extractor.
        """
        self._not_found_redirects = settings.HTTP_EXTRACTOR_404_REDIRECT

    def __call__(self, curi):
        """
        Perform the URL extraction in case of a redirect code.

        I.e. if ``300 <= curi.status_code < 400``, then search for any
        HTTP ``Location`` header and append the given URL to the list of
        extracted URLs.
        """

        if 300 <= curi.status_code < 400 and curi.rep_header and \
            "Location" in curi.rep_header:

            link = curi.rep_header["Location"]

            if link.find("://") == -1:
                # a relative link. this is bad behaviour, but yeah, you know...
                link = urlparse.urljoin(curi.url, link)

            if link not in self._not_found_redirects:
                if not hasattr(curi, "optional_vars"):
                    curi.optional_vars = dict()

                if not CURI_EXTRACTED_URLS in curi.optional_vars:
                    curi.optional_vars[CURI_EXTRACTED_URLS] = link
                else:
                    curi.optional_vars[CURI_EXTRACTED_URLS] += "\n" + link

        return curi

########NEW FILE########
__FILENAME__ = limiter
#
# Copyright (c) 2011 Daniel Truemper truemped@googlemail.com
#
# limiter.py 18-Jan-2011
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
"""
A processor used for limiting the extraction and scoping processings.

Basically this will be used for ignoring any `robots.txt` for being processed.
"""

from spyder.core.constants import CURI_OPTIONAL_TRUE, CURI_EXTRACTION_FINISHED


class DefaultLimiter(object):
    """
    The default crawl limiter.
    """

    def __init__(self, settings):
        """
        Initialize the limiter with the given settings.
        """
        pass

    def __call__(self, curi):
        """
        Do the actual limiting.
        """
        return self._do_not_process_robots(curi)

    def _do_not_process_robots(self, curi):
        """
        Do not process `CrawlUris` if they are **robots.txt** files.
        """
        if CURI_EXTRACTION_FINISHED not in curi.optional_vars and \
            curi.effective_url.endswith("robots.txt"):
            curi.optional_vars[CURI_EXTRACTION_FINISHED] = CURI_OPTIONAL_TRUE

        return curi

########NEW FILE########
__FILENAME__ = scoper
#
# Copyright (c) 2011 Daniel Truemper truemped@googlemail.com
#
# scoper.py 24-Jan-2011
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
"""
The *Crawl Scope* defines which *URLs* the *Spyder* should process. The main
usecases for them are:

- only spider content from the *Seed* Hosts
- do not spider images, css, videos

and there are probably a lot of other reasons you want to have at least one the
scoper configured, otherwise you might end up downloading the internet.

So each scoper should iterate over the
``curi.optional_vars[CURI_EXTRACTED_URLS]`` and determine if it should be
downloaded or not.

The :class:`RegexScoper` maintains a list of regular expressions that define
the crawl scope. Two classes of expressions exist: positive and negative.
The initial decision of the scoper is to not download its content. If a regex
from the positive list matches, and no regex from the negative list matches,
the *URL* is marked for downloading. In any other case, the *URL* will be
abandoned.

.. note:: We should really split up the regex scoper and allow the user to
    configure more than just one scoper.
"""

import re

from spyder.core.constants import CURI_EXTRACTED_URLS


class RegexScoper(object):
    """
    The scoper based on regular expressions.

    There are two settings that influence this scoper:

    1. ``settings.REGEX_SCOPE_POSITIVE``
    2. ``settings.REGEX_SCOPE_NEGATIVE``

    Both have to be a ``list``. The scoper is executed in the
    :meth:`__call__` method.
    """

    def __init__(self, settings):
        """
        Compile the regular expressions.
        """
        self._positive_regex = []
        for regex in settings.REGEX_SCOPE_POSITIVE:
            self._positive_regex.append(re.compile(regex))

        self._negative_regex = []
        for regex in settings.REGEX_SCOPE_NEGATIVE:
            self._negative_regex.append(re.compile(regex))

    def __call__(self, curi):
        """
        Filter all newly extracted URLs for those we want in this crawl.
        """
        if CURI_EXTRACTED_URLS not in curi.optional_vars:
            return curi

        urls = []
        for url in curi.optional_vars[CURI_EXTRACTED_URLS].split("\n"):
            add_url = False
            for regex in self._positive_regex:
                if regex.match(url):
                    add_url = True

            for regex in self._negative_regex:
                if regex.match(url):
                    add_url = False

            if add_url:
                urls.append(url)

        curi.optional_vars[CURI_EXTRACTED_URLS] = "\n".join(urls)
        return curi

########NEW FILE########
__FILENAME__ = stripsessions
#
# Copyright (c) 2011 Daniel Truemper truemped@googlemail.com
#
# stripsessions.py 14-Apr-2011
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
#
"""
Processor to strip all session ids from the extracted URLs. It should be placed
at the very end of the scoper chain in order to process only those URLs that
are relevant for the crawl.

It basically searches for

   sid=
   jsessionid=
   phpsessionid=
   aspsessionid=
"""
from spyder.core.constants import CURI_EXTRACTED_URLS


class StripSessionIds(object):
    """
    The processor for removing session information from the query string.
    """

    def __init__(self, settings):
        """
        Initialize me.
        """
        self._session_params = ['jsessionid=', 'phpsessid=',
            'aspsessionid=', 'sid=']

    def __call__(self, curi):
        """
        Main method stripping the session stuff from the query string.
        """
        if CURI_EXTRACTED_URLS not in curi.optional_vars:
            return curi

        urls = []
        for raw_url in curi.optional_vars[CURI_EXTRACTED_URLS].split('\n'):
            urls.append(self._remove_session_ids(raw_url))

        curi.optional_vars[CURI_EXTRACTED_URLS] = "\n".join(urls)
        return curi

    def _remove_session_ids(self, raw_url):
        """
        Remove the session information.
        """
        for session in self._session_params:
            url = raw_url.lower()
            begin = url.find(session)
            while begin > -1:
                end = url.find('&', begin)
                if end == -1:
                    raw_url = raw_url[:begin]
                else:
                    raw_url = "%s%s" % (raw_url[:begin], raw_url[end:])
                url = raw_url.lower()
                begin = url.find(session)

        return raw_url

########NEW FILE########
__FILENAME__ = master
#
# Copyright (c) 2011 Daniel Truemper truemped@googlemail.com
#
# master.py 21-Apr-2011
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
#
"""
Master module starting a crawl.
"""
from spyder import CrawlUri

from sink import MySink


def initialize(settings, zmq_ctx, io_loop, frontier):
    """
    Initialize the **Master**.

    You may access and manipulate the `settings`, the process global `zmq_ctx`,
    *pyzmq's* `io_loop` and the `frontier`.
    """
    frontier.add_uri(CrawlUri("http://www.dmoz.org/Recreation/Boating/Sailing/")))
    frontier.add_sink(MySink(settings))

########NEW FILE########
__FILENAME__ = settings
#
# settings.py
#
"""
Your crawler specific settings.
"""
import logging

LOG_LEVEL_MASTER = logging.INFO
LOG_LEVEL_WORKER = logging.INFO

USER_AGENT = "Mozilla/5.0 (compatible; spyder/0.1; " + \
    "+http://github.com/retresco/spyder)"

# callback for initializing the periodic crawling of the sitemap
MASTER_CALLBACK = 'master.initialize'

# List of positive regular expressions for the crawl scope
REGEX_SCOPE_POSITIVE = [
    "^http://www\.dmoz\.org/Recreation/Boating/Sailing/.*",
]

# List of negative regular expressions for the crawl scope
REGEX_SCOPE_NEGATIVE = [
    "^http://www\.dmoz\.org/Recreation/Boating/Sailing/Racing/.*",
]

########NEW FILE########
__FILENAME__ = sink
#
# sink.py 21-Apr-2011
#
"""
Put your storage code here.
"""
from spyder.core.sink import AbstractCrawlUriSink


class MySink(AbstractCrawlUriSink):
    """
    This is my sink.
    """

    def __init__(self, settings):
        """
        Initialize me with some settings.
        """
        pass

    def process_successful_crawl(self, curi):
        """
        We have crawled a uri successfully. If there are newly extracted links,
        add them alongside the original uri to the frontier.
        """
        pass

    def process_not_found(self, curi):
        """
        The uri we should have crawled was not found, i.e. HTTP Error 404. Do
        something with that.
        """
        pass

    def process_redirect(self, curi):
        """
        There have been too many redirects, i.e. in the default config there
        have been more than 3 redirects.
        """
        pass

    def process_server_error(self, curi):
        """
        There has been a server error, i.e. HTTP Error 50x. Maybe we should try
        to crawl this uri again a little bit later.
        """
        pass

########NEW FILE########
__FILENAME__ = spyder-ctrl
#
# Copyright (c) 2011 Daniel Truemper truemped@googlemail.com
#
# spyder.py 02-Feb-2011
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import sys

import spyder

try:
    import settings
except ImportError:
    print >> sys.stderr, \
        """Cannot find settings.py in the directory containing %s""" % __file__
    sys.exit(1)


if __name__ == "__main__":
    spyder.spyder_management(settings)

########NEW FILE########
__FILENAME__ = constants
#
# Autogenerated by Thrift
#
# DO NOT EDIT UNLESS YOU ARE SURE THAT YOU KNOW WHAT YOU ARE DOING
#

from thrift.Thrift import *
from ttypes import *


########NEW FILE########
__FILENAME__ = ttypes
#
# Autogenerated by Thrift
#
# DO NOT EDIT UNLESS YOU ARE SURE THAT YOU KNOW WHAT YOU ARE DOING
#

from thrift.Thrift import *

from thrift.transport import TTransport
from thrift.protocol import TBinaryProtocol, TProtocol
try:
  from thrift.protocol import fastbinary
except:
  fastbinary = None



class CrawlUri(object):
  """
  The main strcut for CrawlUris.

  This contains some metadata and if possible the saved web page.

  Attributes:
   - url
   - effective_url
   - current_priority
   - begin_processing
   - end_processing
   - req_header
   - rep_header
   - content_body
   - status_code
   - req_time
   - queue_time
   - optional_vars
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRING, 'url', None, None, ), # 1
    (2, TType.STRING, 'effective_url', None, None, ), # 2
    (3, TType.I16, 'current_priority', None, None, ), # 3
    (4, TType.I64, 'begin_processing', None, None, ), # 4
    (5, TType.I64, 'end_processing', None, None, ), # 5
    (6, TType.MAP, 'req_header', (TType.STRING,None,TType.STRING,None), None, ), # 6
    (7, TType.MAP, 'rep_header', (TType.STRING,None,TType.STRING,None), None, ), # 7
    (8, TType.STRING, 'content_body', None, None, ), # 8
    (9, TType.I16, 'status_code', None, None, ), # 9
    (10, TType.DOUBLE, 'req_time', None, None, ), # 10
    (11, TType.DOUBLE, 'queue_time', None, None, ), # 11
    (12, TType.MAP, 'optional_vars', (TType.STRING,None,TType.STRING,None), None, ), # 12
  )

  def __init__(self, url=None, effective_url=None, current_priority=None, begin_processing=None, end_processing=None, req_header=None, rep_header=None, content_body=None, status_code=None, req_time=None, queue_time=None, optional_vars=None,):
    self.url = url
    self.effective_url = effective_url
    self.current_priority = current_priority
    self.begin_processing = begin_processing
    self.end_processing = end_processing
    self.req_header = req_header
    self.rep_header = rep_header
    self.content_body = content_body
    self.status_code = status_code
    self.req_time = req_time
    self.queue_time = queue_time
    self.optional_vars = optional_vars

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRING:
          self.url = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.STRING:
          self.effective_url = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 3:
        if ftype == TType.I16:
          self.current_priority = iprot.readI16();
        else:
          iprot.skip(ftype)
      elif fid == 4:
        if ftype == TType.I64:
          self.begin_processing = iprot.readI64();
        else:
          iprot.skip(ftype)
      elif fid == 5:
        if ftype == TType.I64:
          self.end_processing = iprot.readI64();
        else:
          iprot.skip(ftype)
      elif fid == 6:
        if ftype == TType.MAP:
          self.req_header = {}
          (_ktype1, _vtype2, _size0 ) = iprot.readMapBegin() 
          for _i4 in xrange(_size0):
            _key5 = iprot.readString();
            _val6 = iprot.readString();
            self.req_header[_key5] = _val6
          iprot.readMapEnd()
        else:
          iprot.skip(ftype)
      elif fid == 7:
        if ftype == TType.MAP:
          self.rep_header = {}
          (_ktype8, _vtype9, _size7 ) = iprot.readMapBegin() 
          for _i11 in xrange(_size7):
            _key12 = iprot.readString();
            _val13 = iprot.readString();
            self.rep_header[_key12] = _val13
          iprot.readMapEnd()
        else:
          iprot.skip(ftype)
      elif fid == 8:
        if ftype == TType.STRING:
          self.content_body = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 9:
        if ftype == TType.I16:
          self.status_code = iprot.readI16();
        else:
          iprot.skip(ftype)
      elif fid == 10:
        if ftype == TType.DOUBLE:
          self.req_time = iprot.readDouble();
        else:
          iprot.skip(ftype)
      elif fid == 11:
        if ftype == TType.DOUBLE:
          self.queue_time = iprot.readDouble();
        else:
          iprot.skip(ftype)
      elif fid == 12:
        if ftype == TType.MAP:
          self.optional_vars = {}
          (_ktype15, _vtype16, _size14 ) = iprot.readMapBegin() 
          for _i18 in xrange(_size14):
            _key19 = iprot.readString();
            _val20 = iprot.readString();
            self.optional_vars[_key19] = _val20
          iprot.readMapEnd()
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('CrawlUri')
    if self.url != None:
      oprot.writeFieldBegin('url', TType.STRING, 1)
      oprot.writeString(self.url)
      oprot.writeFieldEnd()
    if self.effective_url != None:
      oprot.writeFieldBegin('effective_url', TType.STRING, 2)
      oprot.writeString(self.effective_url)
      oprot.writeFieldEnd()
    if self.current_priority != None:
      oprot.writeFieldBegin('current_priority', TType.I16, 3)
      oprot.writeI16(self.current_priority)
      oprot.writeFieldEnd()
    if self.begin_processing != None:
      oprot.writeFieldBegin('begin_processing', TType.I64, 4)
      oprot.writeI64(self.begin_processing)
      oprot.writeFieldEnd()
    if self.end_processing != None:
      oprot.writeFieldBegin('end_processing', TType.I64, 5)
      oprot.writeI64(self.end_processing)
      oprot.writeFieldEnd()
    if self.req_header != None:
      oprot.writeFieldBegin('req_header', TType.MAP, 6)
      oprot.writeMapBegin(TType.STRING, TType.STRING, len(self.req_header))
      for kiter21,viter22 in self.req_header.items():
        oprot.writeString(kiter21)
        oprot.writeString(viter22)
      oprot.writeMapEnd()
      oprot.writeFieldEnd()
    if self.rep_header != None:
      oprot.writeFieldBegin('rep_header', TType.MAP, 7)
      oprot.writeMapBegin(TType.STRING, TType.STRING, len(self.rep_header))
      for kiter23,viter24 in self.rep_header.items():
        oprot.writeString(kiter23)
        oprot.writeString(viter24)
      oprot.writeMapEnd()
      oprot.writeFieldEnd()
    if self.content_body != None:
      oprot.writeFieldBegin('content_body', TType.STRING, 8)
      oprot.writeString(self.content_body)
      oprot.writeFieldEnd()
    if self.status_code != None:
      oprot.writeFieldBegin('status_code', TType.I16, 9)
      oprot.writeI16(self.status_code)
      oprot.writeFieldEnd()
    if self.req_time != None:
      oprot.writeFieldBegin('req_time', TType.DOUBLE, 10)
      oprot.writeDouble(self.req_time)
      oprot.writeFieldEnd()
    if self.queue_time != None:
      oprot.writeFieldBegin('queue_time', TType.DOUBLE, 11)
      oprot.writeDouble(self.queue_time)
      oprot.writeFieldEnd()
    if self.optional_vars != None:
      oprot.writeFieldBegin('optional_vars', TType.MAP, 12)
      oprot.writeMapBegin(TType.STRING, TType.STRING, len(self.optional_vars))
      for kiter25,viter26 in self.optional_vars.items():
        oprot.writeString(kiter25)
        oprot.writeString(viter26)
      oprot.writeMapEnd()
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()
    def validate(self):
      return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

########NEW FILE########
__FILENAME__ = time
#
# Copyright (c) 2011 Daniel Truemper truemped@googlemail.com
#
# time.py 15-Feb-2011
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# under the License.
# All programs in this directory and
# subdirectories are published under the GNU General Public License as
# described below.
#
#
"""
Time related utilities.
"""
from datetime import datetime

import pytz

SERVER_TIME_FORMAT = "%a, %d %b %Y %H:%M:%S %Z"
GMT = pytz.timezone('GMT')


def serialize_date_time(date_time):
    """
    Create a string of the datetime.
    """
    return GMT.localize(date_time).strftime(SERVER_TIME_FORMAT)


def deserialize_date_time(date_string):
    """
    Read a string as a datetime.
    """
    return datetime.strptime(date_string, SERVER_TIME_FORMAT)

########NEW FILE########
__FILENAME__ = workerprocess
#
# Copyright (c) 2011 Daniel Truemper truemped@googlemail.com
#
# workerprocess.py 18-Jan-2011
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
"""
This module contains the default architecture for worker processes. In order to
start a new worker process you should simply call this modules `main` method.

Communication between master -> worker and inside the worker is as follows:

Master              -> PUSH ->              Worker Fetcher

Worker Fetcher      -> PUSH ->              Worker Extractor

Worker Extractor    -> PUB  ->              Master

Each Worker is a ZmqWorker (or ZmqAsyncWorker). The Master pushes new CrawlUris
to the `Worker Fetcher`. This will download the content from the web and `PUSH`
the resulting `CrawlUri` to the `Worker Extractor`. At this stage several
Modules for extracting new URLs are running. The `Worker Scoper` will decide if
the newly extracted URLs are within the scope of the crawl.
"""
import logging
import os
import signal
import socket
import traceback

import zmq
from zmq.core.error import ZMQError
from zmq.eventloop.ioloop import IOLoop, DelayedCallback
from zmq.log.handlers import PUBHandler

from spyder.import_util import import_class
from spyder.core.constants import ZMQ_SPYDER_MGMT_WORKER
from spyder.core.constants import ZMQ_SPYDER_MGMT_WORKER_AVAIL
from spyder.core.constants import ZMQ_SPYDER_MGMT_WORKER_QUIT
from spyder.core.constants import ZMQ_SPYDER_MGMT_WORKER_QUIT_ACK
from spyder.core.messages import MgmtMessage
from spyder.core.mgmt import ZmqMgmt
from spyder.core.worker import ZmqWorker, AsyncZmqWorker
from spyder.processor.fetcher import FetchProcessor


def create_worker_management(settings, zmq_context, io_loop):
    """
    Create and return a new instance of the `ZmqMgmt`.
    """
    listening_socket = zmq_context.socket(zmq.SUB)
    listening_socket.setsockopt(zmq.SUBSCRIBE, "")
    listening_socket.connect(settings.ZEROMQ_MGMT_MASTER)

    publishing_socket = zmq_context.socket(zmq.PUB)
    publishing_socket.connect(settings.ZEROMQ_MGMT_WORKER)

    return ZmqMgmt(listening_socket, publishing_socket, io_loop=io_loop)


def create_worker_fetcher(settings, mgmt, zmq_context, log_handler, io_loop):
    """
    Create and return a new `Worker Fetcher`.
    """
    pulling_socket = zmq_context.socket(zmq.PULL)
    pulling_socket.connect(settings.ZEROMQ_WORKER_PROC_FETCHER_PULL)

    pushing_socket = zmq_context.socket(zmq.PUSH)
    pushing_socket.setsockopt(zmq.HWM,
            settings.ZEROMQ_WORKER_PROC_FETCHER_PUSH_HWM)
    pushing_socket.bind(settings.ZEROMQ_WORKER_PROC_FETCHER_PUSH)

    fetcher = FetchProcessor(settings, io_loop)

    return AsyncZmqWorker(pulling_socket, pushing_socket, mgmt, fetcher,
            log_handler, settings.LOG_LEVEL_WORKER, io_loop)


def create_processing_function(settings, pipeline):
    """
    Create a processing method that iterates all processors over the incoming
    message.
    """
    processors = []
    for processor in pipeline:
        processor_class = import_class(processor)
        processors.append(processor_class(settings))

    def processing(data_message):
        """
        The actual processing function calling each configured processor in the
        order they have been configured.
        """
        next_message = data_message
        for processor in processors:
            next_message = processor(next_message)
        return next_message

    return processing


def create_worker_extractor(settings, mgmt, zmq_context, log_handler, io_loop):
    """
    Create and return a new `Worker Extractor` that will combine all configured
    extractors to a single :class:`ZmqWorker`.
    """
    # the processing function used to process the incoming `DataMessage` by
    # iterating over all available processors
    pipeline = settings.SPYDER_EXTRACTOR_PIPELINE
    pipeline.extend(settings.SPYDER_SCOPER_PIPELINE)

    processing = create_processing_function(settings, pipeline)

    pulling_socket = zmq_context.socket(zmq.PULL)
    pulling_socket.connect(settings.ZEROMQ_WORKER_PROC_EXTRACTOR_PULL)

    pushing_socket = zmq_context.socket(zmq.PUB)
    pushing_socket.setsockopt(zmq.HWM,
            settings.ZEROMQ_WORKER_PROC_EXTRACTOR_PUB_HWM)
    pushing_socket.connect(settings.ZEROMQ_WORKER_PROC_EXTRACTOR_PUB)

    return ZmqWorker(pulling_socket, pushing_socket, mgmt, processing,
        log_handler, settings.LOG_LEVEL_WORKER, io_loop=io_loop)


def main(settings):
    """
    The :meth:`main` method for worker processes.

    Here we will:

     - create a :class:`ZmqMgmt` instance

     - create a :class:`Fetcher` instance

     - initialize and instantiate the extractor chain

    The `settings` have to be loaded already.
    """
    # create my own identity
    identity = "worker:%s:%s" % (socket.gethostname(), os.getpid())

    ctx = zmq.Context()
    io_loop = IOLoop.instance()

    # initialize the logging subsystem
    log_pub = ctx.socket(zmq.PUB)
    log_pub.connect(settings.ZEROMQ_LOGGING)
    zmq_logging_handler = PUBHandler(log_pub)
    zmq_logging_handler.root_topic = "spyder.worker"
    logger = logging.getLogger()
    logger.addHandler(zmq_logging_handler)
    logger.setLevel(settings.LOG_LEVEL_WORKER)

    logger.info("process::Starting up another worker")

    mgmt = create_worker_management(settings, ctx, io_loop)

    logger.debug("process::Initializing fetcher, extractor and scoper")

    fetcher = create_worker_fetcher(settings, mgmt, ctx, zmq_logging_handler,
        io_loop)
    fetcher.start()
    extractor = create_worker_extractor(settings, mgmt, ctx,
        zmq_logging_handler, io_loop)
    extractor.start()

    def quit_worker(raw_msg):
        """
        When the worker should quit, stop the io_loop after 2 seconds.
        """
        msg = MgmtMessage(raw_msg)
        if ZMQ_SPYDER_MGMT_WORKER_QUIT == msg.data:
            logger.info("process::We have been asked to shutdown, do so")
            DelayedCallback(io_loop.stop, 2000, io_loop).start()
            ack = MgmtMessage(topic=ZMQ_SPYDER_MGMT_WORKER, identity=identity,
                    data=ZMQ_SPYDER_MGMT_WORKER_QUIT_ACK)
            mgmt._out_stream.send_multipart(ack.serialize())

    mgmt.add_callback(ZMQ_SPYDER_MGMT_WORKER, quit_worker)
    mgmt.start()

    # notify the master that we are online
    msg = MgmtMessage(topic=ZMQ_SPYDER_MGMT_WORKER, identity=identity,
            data=ZMQ_SPYDER_MGMT_WORKER_AVAIL)
    mgmt._out_stream.send_multipart(msg.serialize())

    def handle_shutdown_signal(_sig, _frame):
        """
        Called from the os when a shutdown signal is fired.
        """
        msg = MgmtMessage(data=ZMQ_SPYDER_MGMT_WORKER_QUIT)
        quit_worker(msg.serialize())
        # zmq 2.1 stops blocking calls, restart the ioloop
        io_loop.start()

    # handle kill signals
    signal.signal(signal.SIGINT, handle_shutdown_signal)
    signal.signal(signal.SIGTERM, handle_shutdown_signal)

    logger.info("process::waiting for action")
    # this will block until the worker quits
    try:
        io_loop.start()
    except ZMQError:
        logger.debug("Caught a ZMQError. Hopefully during shutdown")
        logger.debug(traceback.format_exc())

    for mod in [fetcher, extractor, mgmt]:
        mod.close()

    logger.info("process::Houston: Worker down")
    ctx.term()

########NEW FILE########
__FILENAME__ = test_async_worker
#
# Copyright (c) 2011 Daniel Truemper truemped@googlemail.com
#
# test_async_worker.py 14-Jan-2011
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import logging
from logging import StreamHandler
import sys
import unittest

import zmq
from zmq.eventloop.ioloop import IOLoop
from zmq.eventloop.zmqstream import ZMQStream

from spyder.core.constants import ZMQ_SPYDER_MGMT_WORKER
from spyder.core.constants import ZMQ_SPYDER_MGMT_WORKER_QUIT
from spyder.core.constants import ZMQ_SPYDER_MGMT_WORKER_QUIT_ACK
from spyder.core.mgmt import ZmqMgmt
from spyder.core.worker import AsyncZmqWorker
from spyder.core.messages import DataMessage, MgmtMessage
from spyder.thrift.gen.ttypes import CrawlUri


class ZmqTornadoIntegrationTest(unittest.TestCase):

    def setUp(self):

        # create the io_loop
        self._io_loop = IOLoop.instance()

        # and the context
        self._ctx = zmq.Context(1)

        # setup the mgmt sockets
        self._setup_mgmt_sockets()

        # setup the data sockets
        self._setup_data_sockets()

        # setup the management interface
        self._mgmt = ZmqMgmt( self._mgmt_sockets['worker_sub'],
            self._mgmt_sockets['worker_pub'], io_loop=self._io_loop)
        self._mgmt.start()
        self._mgmt.add_callback(ZMQ_SPYDER_MGMT_WORKER, self.on_mgmt_end)

    def tearDown(self):
        # stop the mgmt
        self._mgmt.stop()

        # close all sockets
        for socket in self._mgmt_sockets.itervalues():
            socket.close()
        for socket in self._worker_sockets.itervalues():
            socket.close()

        # terminate the context
        self._ctx.term()

    def _setup_mgmt_sockets(self):

        self._mgmt_sockets = dict()

        # adress for the communication from master to worker(s)
        mgmt_master_worker = 'inproc://master/worker/coordination/'

        # connect the master with the worker
        # the master is a ZMQStream because we are sending msgs from the test
        sock = self._ctx.socket(zmq.PUB)
        sock.bind(mgmt_master_worker)
        self._mgmt_sockets['tmp1'] = sock
        self._mgmt_sockets['master_pub'] = ZMQStream(sock, self._io_loop)
        # the worker stream is created inside the ZmqMgmt class
        self._mgmt_sockets['worker_sub'] = self._ctx.socket(zmq.SUB)
        self._mgmt_sockets['worker_sub'].setsockopt(zmq.SUBSCRIBE, "")
        self._mgmt_sockets['worker_sub'].connect(mgmt_master_worker)

        # adress for the communication from worker(s) to master
        mgmt_worker_master = 'inproc://worker/master/coordination/'

        # connect the worker with the master
        self._mgmt_sockets['worker_pub'] = self._ctx.socket(zmq.PUB)
        self._mgmt_sockets['worker_pub'].bind(mgmt_worker_master)
        sock = self._ctx.socket(zmq.SUB)
        sock.setsockopt(zmq.SUBSCRIBE, "")
        sock.connect(mgmt_worker_master)
        self._mgmt_sockets['tmp2'] = sock
        self._mgmt_sockets['master_sub'] = ZMQStream(sock, self._io_loop)

    def _setup_data_sockets(self):

        self._worker_sockets = dict()

        # address for master -> worker communication
        data_master_worker = 'inproc://master/worker/pipeline/'

        sock = self._ctx.socket(zmq.PUSH)
        sock.bind(data_master_worker)
        self._worker_sockets['tmp3'] = sock
        self._worker_sockets['master_push'] = ZMQStream(sock, self._io_loop)
        self._worker_sockets['worker_pull'] = self._ctx.socket(zmq.PULL)
        self._worker_sockets['worker_pull'].connect(data_master_worker)

        # address for worker -> master communication
        data_worker_master = 'inproc://worker/master/pipeline/'

        self._worker_sockets['worker_pub'] = self._ctx.socket(zmq.PUB)
        self._worker_sockets['worker_pub'].bind(data_worker_master)
        sock = self._ctx.socket(zmq.SUB)
        sock.setsockopt(zmq.SUBSCRIBE, "")
        sock.connect(data_worker_master)
        self._worker_sockets['tmp4'] = sock
        self._worker_sockets['master_sub'] = ZMQStream(sock, self._io_loop)

    def on_mgmt_end(self, _msg):
        self._io_loop.stop()


class AsyncZmqWorkerIntegrationTest(ZmqTornadoIntegrationTest):

    def echo_processing(self, data_message, out_socket):
        msg = MgmtMessage(topic=ZMQ_SPYDER_MGMT_WORKER,
                data=ZMQ_SPYDER_MGMT_WORKER_QUIT)
        self._mgmt_sockets['master_pub'].send_multipart(msg.serialize())
        out_socket.send_multipart(data_message.serialize())

    def test_that_async_worker_works(self):
        worker = AsyncZmqWorker( self._worker_sockets['worker_pull'],
            self._worker_sockets['worker_pub'],
            self._mgmt,
            self.echo_processing,
            StreamHandler(sys.stdout),
            logging.DEBUG,
            self._io_loop)

        worker.start()

        curi = CrawlUri(url="http://localhost")
        msg = DataMessage()
        msg.identity = "me"
        msg.curi = curi

        def assert_correct_data(msg2):
            msg3 = DataMessage(msg2)
            self.assertEqual(msg, msg3)

        self._worker_sockets['master_sub'].on_recv(assert_correct_data)

        def assert_correct_mgmt(msg4):
            self.assertEqual(ZMQ_SPYDER_MGMT_WORKER_QUIT_ACK, msg4.data)

        self._mgmt_sockets['master_sub'].on_recv(assert_correct_mgmt)

        self._worker_sockets['master_push'].send_multipart(msg.serialize())

        self._io_loop.start()
        worker._in_stream.flush()


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_cleanup_qs
#
# Copyright (c) 2011 Daniel Truemper truemped@googlemail.com
#
# test_cleanup_qs.py 14-Apr-2011
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
#
import unittest

from spyder.core.settings import Settings
from spyder.processor.cleanupquery import CleanupQueryString


class CleanupQueryStringTest(unittest.TestCase):

    def test_that_cleaning_qs_works(self):
        s = Settings()
        c = CleanupQueryString(s)

        self.assertEqual("http://tesT.com/t.html?p=a",
                c._cleanup_query_string("http://tesT.com/t.html?p=a#top"))

        self.assertEqual("http://test.com/t.html",
                c._cleanup_query_string("http://test.com/t.html?#top"))

        self.assertEqual("http://test.com/t.html?test=a",
                c._cleanup_query_string("http://test.com/t.html?test=a&"))

########NEW FILE########
__FILENAME__ = test_default_html_link_extractor
#
# Copyright (c) 2011 Daniel Truemper truemped@googlemail.com
#
# test_default_html_link_extractor.py 21-Jan-2011
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import unittest

from spyder.core.constants import CURI_EXTRACTED_URLS
from spyder.core.settings import Settings
from spyder.processor.htmllinkextractor import DefaultHtmlLinkExtractor
from spyder.thrift.gen.ttypes import CrawlUri


class HtmlLinkExtractorTest(unittest.TestCase):

    def test_that_content_type_restriction_works(self):
        xtor = DefaultHtmlLinkExtractor(Settings())

        curi = CrawlUri()
        curi.rep_header = dict()
        curi.rep_header["Content-Type"] = "text/html"
        self.assertTrue(xtor._restrict_content_type(curi))
        curi.rep_header["Content-Type"] = "pille/palle"
        self.assertFalse(xtor._restrict_content_type(curi))

    def test_link_extraction_works(self):

        src = "<a href='http://www.google.de' title='ups'> viel text</a>" + \
            "<a title='ups i did it again' href ='/relative.html'>und " + \
            "noch mehr!</a><a href='evenmorerelative.html'/>" + \
            "<a href='&#109;&#97;&#105;&#108;&#116;&#111;&#58;&#109;&#117;&#115;&#116;&#101;&#114;&#64;&#98;&#102;&#97;&#114;&#109;&#46;&#100;&#101;'/>"

        curi = CrawlUri()
        curi.rep_header = dict()
        curi.rep_header["Content-Type"] = "text/html; charset=utf-8"
        curi.url = "http://www.bmg.bund.de/test/"
        curi.content_body = src
        curi.optional_vars = dict()

        xtor = DefaultHtmlLinkExtractor(Settings())
        curi = xtor(curi)

        links = curi.optional_vars[CURI_EXTRACTED_URLS].split("\n")
        self.assertEqual("http://www.google.de", links[0])
        self.assertEqual("http://www.bmg.bund.de/relative.html", links[1])
        self.assertEqual("http://www.bmg.bund.de/test/evenmorerelative.html",
                links[2])

    def test_link_extraction_with_base_works(self):

        src = "<base href='http://www.bing.com' />" + \
            "<a href='http://www.google.de' title='ups'> viel text</a>" + \
            "<a title='ups i did it again' href ='/relative.html'>und " + \
            "noch mehr!</a><a href='evenmorerelative.html'>"

        curi = CrawlUri()
        curi.rep_header = dict()
        curi.rep_header["Content-Type"] = "text/html; charset=utf-8"
        curi.url = "http://www.bmg.bund.de/test/"
        curi.content_body = src
        curi.optional_vars = dict()

        xtor = DefaultHtmlLinkExtractor(Settings())
        curi = xtor(curi)

        links = curi.optional_vars[CURI_EXTRACTED_URLS].split("\n")
        self.assertEqual("http://www.google.de", links[0])
        self.assertEqual("http://www.bing.com/relative.html", links[1])
        self.assertEqual("http://www.bing.com/evenmorerelative.html",
                links[2])

    def test_missing_encoding_works(self):
        src = "<a href='http://www.google.de' title='ups'> viel text</a>" + \
            "<a title='ups i did it again' href ='/relative.html'>und " + \
            "noch mehr!</a><a href='evenmorerelative.html'>"

        curi = CrawlUri()
        curi.rep_header = dict()
        curi.rep_header["Content-Type"] = "text/html"
        curi.url = "http://www.bmg.bund.de/test/"
        curi.content_body = src
        curi.optional_vars = dict()

        xtor = DefaultHtmlLinkExtractor(Settings())
        curi = xtor(curi)

        links = curi.optional_vars[CURI_EXTRACTED_URLS].split("\n")
        self.assertEqual("http://www.google.de", links[0])
        self.assertEqual("http://www.bmg.bund.de/relative.html", links[1])
        self.assertEqual("http://www.bmg.bund.de/test/evenmorerelative.html",
                links[2])


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_dns_cache
#
# Copyright (c) 2011 Daniel Truemper truemped@googlemail.com
#
# test_dns_cache.py 25-Jan-2011
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import unittest

from spyder.core.dnscache import DnsCache
from spyder.core.settings import Settings


class DnsCacheTest(unittest.TestCase):

    def test_dns_cache(self):
        s = Settings()
        s.SIZE_DNS_CACHE = 1
        dns = DnsCache(s)
        self.assertEqual(('127.0.0.1', 80), dns["localhost:80"])
        self.assertEqual(('127.0.0.1', 81), dns["localhost:81"])
        self.assertTrue(1, len(dns._cache))

    def test_static_dns_mapping(self):
        s = Settings()
        s.STATIC_DNS_MAPPINGS = {"localhost:123": ("-1.-1.-1.-1", 123)}
        dns = DnsCache(s)
        self.assertEqual(("-1.-1.-1.-1", 123), dns["localhost:123"])
        self.assertEqual(('127.0.0.1', 80), dns["localhost:80"])
        self.assertTrue(1, len(dns._cache))


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_fetch_processor
#
# Copyright (c) 2011 Daniel Truemper truemped@googlemail.com
#
# test_fetch_processor.py 17-Jan-2011
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import logging
from logging import StreamHandler
import sys

import os.path
import time
import random

import unittest

import tornado
import tornado.httpserver
import tornado.web

import zmq
from zmq.eventloop.ioloop import IOLoop
from zmq.eventloop.zmqstream import ZMQStream

from spyder.core.constants import ZMQ_SPYDER_MGMT_WORKER
from spyder.core.constants import ZMQ_SPYDER_MGMT_WORKER_QUIT
from spyder.core.constants import ZMQ_SPYDER_MGMT_WORKER_QUIT_ACK
from spyder.core.messages import DataMessage, MgmtMessage
from spyder.core.mgmt import ZmqMgmt
from spyder.core.worker import AsyncZmqWorker
from spyder.core.settings import Settings
from spyder.processor.fetcher import FetchProcessor
from spyder.encoding import extract_content_type_encoding
from spyder.thrift.gen.ttypes import CrawlUri


class ZmqTornadoIntegrationTest(unittest.TestCase):

    def setUp(self):

        # create the io_loop
        self._io_loop = IOLoop.instance()

        # and the context
        self._ctx = zmq.Context(1)

        # setup the mgmt sockets
        self._setup_mgmt_sockets()

        # setup the data sockets
        self._setup_data_sockets()

        # setup the management interface
        self._mgmt = ZmqMgmt( self._mgmt_sockets['worker_sub'],
            self._mgmt_sockets['worker_pub'], io_loop=self._io_loop)
        self._mgmt.start()
        self._mgmt.add_callback(ZMQ_SPYDER_MGMT_WORKER, self.on_mgmt_end)

    def tearDown(self):
        # stop the mgmt
        self._mgmt.stop()

        # close all sockets
        for socket in self._mgmt_sockets.itervalues():
            socket.close()
        for socket in self._worker_sockets.itervalues():
            socket.close()

        # terminate the context
        self._ctx.term()

    def _setup_mgmt_sockets(self):

        self._mgmt_sockets = dict()

        # adress for the communication from master to worker(s)
        mgmt_master_worker = 'inproc://master/worker/coordination/'

        # connect the master with the worker
        # the master is a ZMQStream because we are sending msgs from the test
        sock = self._ctx.socket(zmq.PUB)
        sock.bind(mgmt_master_worker)
        self._mgmt_sockets['tmp1'] = sock
        self._mgmt_sockets['master_pub'] = ZMQStream(sock, self._io_loop)
        # the worker stream is created inside the ZmqMgmt class
        self._mgmt_sockets['worker_sub'] = self._ctx.socket(zmq.SUB)
        self._mgmt_sockets['worker_sub'].setsockopt(zmq.SUBSCRIBE, "")
        self._mgmt_sockets['worker_sub'].connect(mgmt_master_worker)

        # adress for the communication from worker(s) to master
        mgmt_worker_master = 'inproc://worker/master/coordination/'

        # connect the worker with the master
        self._mgmt_sockets['worker_pub'] = self._ctx.socket(zmq.PUB)
        self._mgmt_sockets['worker_pub'].bind(mgmt_worker_master)
        sock = self._ctx.socket(zmq.SUB)
        sock.setsockopt(zmq.SUBSCRIBE, "")
        sock.connect(mgmt_worker_master)
        self._mgmt_sockets['tmp2'] = sock
        self._mgmt_sockets['master_sub'] = ZMQStream(sock, self._io_loop)

    def _setup_data_sockets(self):

        self._worker_sockets = dict()

        # address for master -> worker communication
        data_master_worker = 'inproc://master/worker/pipeline/'

        sock = self._ctx.socket(zmq.PUSH)
        sock.bind(data_master_worker)
        self._worker_sockets['tmp3'] = sock
        self._worker_sockets['master_push'] = ZMQStream(sock, self._io_loop)
        self._worker_sockets['worker_pull'] = self._ctx.socket(zmq.PULL)
        self._worker_sockets['worker_pull'].connect(data_master_worker)

        # address for worker -> master communication
        data_worker_master = 'inproc://worker/master/pipeline/'

        self._worker_sockets['worker_pub'] = self._ctx.socket(zmq.PUB)
        self._worker_sockets['worker_pub'].bind(data_worker_master)
        sock = self._ctx.socket(zmq.SUB)
        sock.setsockopt(zmq.SUBSCRIBE, "")
        sock.connect(data_worker_master)
        self._worker_sockets['tmp4'] = sock
        self._worker_sockets['master_sub'] = ZMQStream(sock, self._io_loop)

    def on_mgmt_end(self, _msg):
        self._io_loop.stop()


class SimpleFetcherTestCase(ZmqTornadoIntegrationTest):

    port = 8085

    def setUp(self):
        ZmqTornadoIntegrationTest.setUp(self)

        path = os.path.join(os.path.dirname(__file__), "static")
        application = tornado.web.Application([
            (r"/(.*)", tornado.web.StaticFileHandler, {"path": path}),
        ])
        self._server = tornado.httpserver.HTTPServer(application, io_loop =
                self._io_loop)
        self._server.listen(self.port)

    def tearDown(self):
        ZmqTornadoIntegrationTest.tearDown(self)
        self._server.stop()

    def test_content_type_encoding(self):
        rep_header = dict()
        rep_header["Content-Type"] = "text/html; charset=ISO-8859-1"
        (ct, encoding) = extract_content_type_encoding(rep_header["Content-Type"])
        self.assertEqual("text/html", ct)
        self.assertEqual("iso_8859_1", encoding)

    def test_fetching_works(self):

        settings = Settings()
        fetcher = FetchProcessor(settings, io_loop=self._io_loop)

        worker = AsyncZmqWorker( self._worker_sockets['worker_pull'],
            self._worker_sockets['worker_pub'],
            self._mgmt,
            fetcher,
            StreamHandler(sys.stdout),
            logging.DEBUG,
            self._io_loop)
        worker.start()

        curi = CrawlUri(url="http://localhost:%s/robots.txt" % self.port,
                effective_url="http://127.0.0.1:%s/robots.txt" % self.port,
                )
        msg = DataMessage()
        msg.identity = "me"
        msg.curi = curi

        self._worker_sockets['master_push'].send_multipart(msg.serialize())

        def assert_expected_result_and_stop(raw_msg):
            msg = DataMessage(raw_msg)
            robots = open(os.path.join(os.path.dirname(__file__),
                        "static/robots.txt")).read()
            self.assertEqual(robots, msg.curi.content_body)
            death = MgmtMessage(topic=ZMQ_SPYDER_MGMT_WORKER,
                    data=ZMQ_SPYDER_MGMT_WORKER_QUIT)
            self._mgmt_sockets['master_pub'].send_multipart(death.serialize())

        self._worker_sockets['master_sub'].on_recv(assert_expected_result_and_stop)

        self._io_loop.start()


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_fetch_processor_last_modified_works
#
# Copyright (c) 2011 Daniel Truemper truemped@googlemail.com
#
# test_fetch_processor_last_modified_works.py 17-Jan-2011
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import logging
from logging import StreamHandler
import sys

import os
import os.path
import time
from datetime import datetime
import random

import unittest

import tornado
import tornado.httpserver
import tornado.web

import zmq
from zmq.eventloop.ioloop import IOLoop
from zmq.eventloop.zmqstream import ZMQStream

from spyder.core.constants import ZMQ_SPYDER_MGMT_WORKER
from spyder.core.constants import ZMQ_SPYDER_MGMT_WORKER_QUIT
from spyder.core.constants import ZMQ_SPYDER_MGMT_WORKER_QUIT_ACK
from spyder.core.messages import DataMessage, MgmtMessage
from spyder.time import serialize_date_time
from spyder.core.mgmt import ZmqMgmt
from spyder.core.worker import AsyncZmqWorker
from spyder.core.settings import Settings
from spyder.processor.fetcher import FetchProcessor
from spyder.thrift.gen.ttypes import CrawlUri


class ZmqTornadoIntegrationTest(unittest.TestCase):

    def setUp(self):

        # create the io_loop
        self._io_loop = IOLoop.instance()

        # and the context
        self._ctx = zmq.Context(1)

        # setup the mgmt sockets
        self._setup_mgmt_sockets()

        # setup the data sockets
        self._setup_data_sockets()

        # setup the management interface
        self._mgmt = ZmqMgmt( self._mgmt_sockets['worker_sub'],
            self._mgmt_sockets['worker_pub'], io_loop=self._io_loop)
        self._mgmt.start()
        self._mgmt.add_callback(ZMQ_SPYDER_MGMT_WORKER, self.on_mgmt_end)

    def tearDown(self):
        # stop the mgmt
        self._mgmt.stop()

        # close all sockets
        for socket in self._mgmt_sockets.itervalues():
            socket.close()
        for socket in self._worker_sockets.itervalues():
            socket.close()

        # terminate the context
        self._ctx.term()

    def _setup_mgmt_sockets(self):

        self._mgmt_sockets = dict()

        # adress for the communication from master to worker(s)
        mgmt_master_worker = 'inproc://master/worker/coordination/'

        # connect the master with the worker
        # the master is a ZMQStream because we are sending msgs from the test
        sock = self._ctx.socket(zmq.PUB)
        sock.bind(mgmt_master_worker)
        self._mgmt_sockets['tmp1'] = sock
        self._mgmt_sockets['master_pub'] = ZMQStream(sock, self._io_loop)
        # the worker stream is created inside the ZmqMgmt class
        self._mgmt_sockets['worker_sub'] = self._ctx.socket(zmq.SUB)
        self._mgmt_sockets['worker_sub'].setsockopt(zmq.SUBSCRIBE, "")
        self._mgmt_sockets['worker_sub'].connect(mgmt_master_worker)

        # adress for the communication from worker(s) to master
        mgmt_worker_master = 'inproc://worker/master/coordination/'

        # connect the worker with the master
        self._mgmt_sockets['worker_pub'] = self._ctx.socket(zmq.PUB)
        self._mgmt_sockets['worker_pub'].bind(mgmt_worker_master)
        sock = self._ctx.socket(zmq.SUB)
        sock.setsockopt(zmq.SUBSCRIBE, "")
        sock.connect(mgmt_worker_master)
        self._mgmt_sockets['tmp2'] = sock
        self._mgmt_sockets['master_sub'] = ZMQStream(sock, self._io_loop)

    def _setup_data_sockets(self):

        self._worker_sockets = dict()

        # address for master -> worker communication
        data_master_worker = 'inproc://master/worker/pipeline/'

        sock = self._ctx.socket(zmq.PUSH)
        sock.bind(data_master_worker)
        self._worker_sockets['tmp3'] = sock
        self._worker_sockets['master_push'] = ZMQStream(sock, self._io_loop)
        self._worker_sockets['worker_pull'] = self._ctx.socket(zmq.PULL)
        self._worker_sockets['worker_pull'].connect(data_master_worker)

        # address for worker -> master communication
        data_worker_master = 'inproc://worker/master/pipeline/'

        self._worker_sockets['worker_pub'] = self._ctx.socket(zmq.PUB)
        self._worker_sockets['worker_pub'].bind(data_worker_master)
        sock = self._ctx.socket(zmq.SUB)
        sock.setsockopt(zmq.SUBSCRIBE, "")
        sock.connect(data_worker_master)
        self._worker_sockets['tmp4'] = sock
        self._worker_sockets['master_sub'] = ZMQStream(sock, self._io_loop)

    def on_mgmt_end(self, _msg):
        self._io_loop.stop()


class SimpleFetcherTestCase(ZmqTornadoIntegrationTest):

    port = 8085

    def setUp(self):
        ZmqTornadoIntegrationTest.setUp(self)

        self._path = os.path.join(os.path.dirname(__file__), "static")
        application = tornado.web.Application([
            (r"/(.*)", tornado.web.StaticFileHandler, {"path": self._path}),
        ])
        self._server = tornado.httpserver.HTTPServer(application, io_loop =
                self._io_loop)
        self._server.listen(self.port)

    def tearDown(self):
        ZmqTornadoIntegrationTest.tearDown(self)
        self._server.stop()

    def test_fetching_last_modified_works(self):

        settings = Settings()
        fetcher = FetchProcessor(settings, io_loop=self._io_loop)

        worker = AsyncZmqWorker( self._worker_sockets['worker_pull'],
            self._worker_sockets['worker_pub'],
            self._mgmt,
            fetcher,
            StreamHandler(sys.stdout),
            logging.DEBUG,
            self._io_loop)
        worker.start()

        mtimestamp = datetime.fromtimestamp(os.stat(os.path.join(self._path,
                        "robots.txt")).st_mtime)
        mtime = serialize_date_time(mtimestamp)
        curi = CrawlUri(url="http://localhost:%s/robots.txt" % self.port,
                effective_url="http://127.0.0.1:%s/robots.txt" % self.port,
                req_header = { "Last-Modified" :
                    mtime }
                )

        msg = DataMessage()
        msg.identity = "me"
        msg.curi = curi

        def assert_expected_result_and_stop(raw_msg):
            msg = DataMessage(raw_msg)
            self.assertEqual(304, msg.curi.status_code)
            self.assertEqual("", msg.curi.content_body)
            death = MgmtMessage(topic=ZMQ_SPYDER_MGMT_WORKER,
                    data=ZMQ_SPYDER_MGMT_WORKER_QUIT)
            self._mgmt_sockets['master_pub'].send_multipart(death.serialize())

        self._worker_sockets['master_sub'].on_recv(assert_expected_result_and_stop)

        self._worker_sockets['master_push'].send_multipart(msg.serialize())

        self._io_loop.start()


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_fetch_processor_with_etag
#
# Copyright (c) 2011 Daniel Truemper truemped@googlemail.com
#
# test_fetch_processor_with_etag.py 17-Jan-2011
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import logging
from logging import StreamHandler
import sys

import os.path
import time
import random

import unittest

import tornado
import tornado.httpserver
import tornado.web

import zmq
from zmq.eventloop.ioloop import IOLoop
from zmq.eventloop.zmqstream import ZMQStream

from spyder.core.constants import ZMQ_SPYDER_MGMT_WORKER
from spyder.core.constants import ZMQ_SPYDER_MGMT_WORKER_QUIT
from spyder.core.constants import ZMQ_SPYDER_MGMT_WORKER_QUIT_ACK
from spyder.core.messages import DataMessage, MgmtMessage
from spyder.core.mgmt import ZmqMgmt
from spyder.core.worker import AsyncZmqWorker
from spyder.core.settings import Settings
from spyder.processor.fetcher import FetchProcessor
from spyder.thrift.gen.ttypes import CrawlUri


class ZmqTornadoIntegrationTest(unittest.TestCase):

    def setUp(self):

        # create the io_loop
        self._io_loop = IOLoop.instance()

        # and the context
        self._ctx = zmq.Context(1)

        # setup the mgmt sockets
        self._setup_mgmt_sockets()

        # setup the data sockets
        self._setup_data_sockets()

        # setup the management interface
        self._mgmt = ZmqMgmt( self._mgmt_sockets['worker_sub'],
            self._mgmt_sockets['worker_pub'], io_loop=self._io_loop)
        self._mgmt.start()
        self._mgmt.add_callback(ZMQ_SPYDER_MGMT_WORKER, self.on_mgmt_end)

    def tearDown(self):
        # stop the mgmt
        self._mgmt.stop()

        # close all sockets
        for socket in self._mgmt_sockets.itervalues():
            socket.close()
        for socket in self._worker_sockets.itervalues():
            socket.close()

        # terminate the context
        self._ctx.term()

    def _setup_mgmt_sockets(self):

        self._mgmt_sockets = dict()

        # adress for the communication from master to worker(s)
        mgmt_master_worker = 'inproc://master/worker/coordination/'

        # connect the master with the worker
        # the master is a ZMQStream because we are sending msgs from the test
        sock = self._ctx.socket(zmq.PUB)
        sock.bind(mgmt_master_worker)
        self._mgmt_sockets['tmp1'] = sock
        self._mgmt_sockets['master_pub'] = ZMQStream(sock, self._io_loop)
        # the worker stream is created inside the ZmqMgmt class
        self._mgmt_sockets['worker_sub'] = self._ctx.socket(zmq.SUB)
        self._mgmt_sockets['worker_sub'].setsockopt(zmq.SUBSCRIBE, "")
        self._mgmt_sockets['worker_sub'].connect(mgmt_master_worker)

        # adress for the communication from worker(s) to master
        mgmt_worker_master = 'inproc://worker/master/coordination/'

        # connect the worker with the master
        self._mgmt_sockets['worker_pub'] = self._ctx.socket(zmq.PUB)
        self._mgmt_sockets['worker_pub'].bind(mgmt_worker_master)
        sock = self._ctx.socket(zmq.SUB)
        sock.setsockopt(zmq.SUBSCRIBE, "")
        sock.connect(mgmt_worker_master)
        self._mgmt_sockets['tmp2'] = sock
        self._mgmt_sockets['master_sub'] = ZMQStream(sock, self._io_loop)

    def _setup_data_sockets(self):

        self._worker_sockets = dict()

        # address for master -> worker communication
        data_master_worker = 'inproc://master/worker/pipeline/'

        sock = self._ctx.socket(zmq.PUSH)
        sock.bind(data_master_worker)
        self._worker_sockets['tmp3'] = sock
        self._worker_sockets['master_push'] = ZMQStream(sock, self._io_loop)
        self._worker_sockets['worker_pull'] = self._ctx.socket(zmq.PULL)
        self._worker_sockets['worker_pull'].connect(data_master_worker)

        # address for worker -> master communication
        data_worker_master = 'inproc://worker/master/pipeline/'

        self._worker_sockets['worker_pub'] = self._ctx.socket(zmq.PUB)
        self._worker_sockets['worker_pub'].bind(data_worker_master)
        sock = self._ctx.socket(zmq.SUB)
        sock.setsockopt(zmq.SUBSCRIBE, "")
        sock.connect(data_worker_master)
        self._worker_sockets['tmp4'] = sock
        self._worker_sockets['master_sub'] = ZMQStream(sock, self._io_loop)

    def on_mgmt_end(self, _msg):
        self._io_loop.stop()


class SimpleFetcherTestCase(ZmqTornadoIntegrationTest):

    port = 8085

    def setUp(self):
        ZmqTornadoIntegrationTest.setUp(self)

        path = os.path.join(os.path.dirname(__file__), "static")
        application = tornado.web.Application([
            (r"/(.*)", tornado.web.StaticFileHandler, {"path": path}),
        ])
        self._server = tornado.httpserver.HTTPServer(application, io_loop =
                self._io_loop)
        self._server.listen(self.port)

    def tearDown(self):
        ZmqTornadoIntegrationTest.tearDown(self)
        self._server.stop()

    def test_fetching_etag_works(self):

        settings = Settings()
        fetcher = FetchProcessor(settings, io_loop=self._io_loop)

        worker = AsyncZmqWorker( self._worker_sockets['worker_pull'],
            self._worker_sockets['worker_pub'],
            self._mgmt,
            fetcher,
            StreamHandler(sys.stdout),
            logging.DEBUG,
            self._io_loop)
        worker.start()

        curi = CrawlUri(url="http://localhost:%s/robots.txt" % self.port,
                effective_url="http://127.0.0.1:%s/robots.txt" % self.port,
                req_header = { "Etag" :
                    "\"3926227169c58185234888b60000c6eb1169577d\"" }
                )

        msg = DataMessage()
        msg.identity = "me"
        msg.curi = curi

        def assert_expected_result_and_stop(raw_msg):
            msg = DataMessage(raw_msg)
            self.assertEqual(304, msg.curi.status_code)
            self.assertEqual("", msg.curi.content_body)
            death = MgmtMessage(topic=ZMQ_SPYDER_MGMT_WORKER,
                    data=ZMQ_SPYDER_MGMT_WORKER_QUIT)
            self._mgmt_sockets['master_pub'].send_multipart(death.serialize())

        self._worker_sockets['master_sub'].on_recv(assert_expected_result_and_stop)

        self._worker_sockets['master_push'].send_multipart(msg.serialize())

        self._io_loop.start()


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_frontier
#
# Copyright (c) 2011 Daniel Truemper truemped@googlemail.com
#
# test_frontier.py 27-Jan-2011
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import logging
from logging import StreamHandler

import time
from datetime import datetime, timedelta
import unittest

import sys

from spyder.core.constants import *
from spyder.core.frontier import *
from spyder.time import serialize_date_time, deserialize_date_time
from spyder.core.prioritizer import SimpleTimestampPrioritizer
from spyder.core.settings import Settings
from spyder.core.sink import AbstractCrawlUriSink
from spyder.core.sqlitequeues import SQLiteSingleHostUriQueue
from spyder.thrift.gen.ttypes import CrawlUri


class BaseFrontierTest(unittest.TestCase):

    def test_adding_uri_works(self):

        now = datetime(*datetime.fromtimestamp(time.time()).timetuple()[0:6])
        next_crawl_date = now + timedelta(days=1)

        s = Settings()
        s.FRONTIER_STATE_FILE = ":memory:"

        curi = CrawlUri("http://localhost")
        curi.rep_header = { "Etag" : "123", "Date" : serialize_date_time(now) }
        curi.current_priority = 2

        frontier = AbstractBaseFrontier(s, StreamHandler(sys.stdout),
                SQLiteSingleHostUriQueue(s.FRONTIER_STATE_FILE),
                SimpleTimestampPrioritizer(s))
        frontier.add_uri(curi)

        for uri in frontier._front_end_queues.queue_head():
            (url, etag, mod_date, queue, next_date) = uri
            self.assertEqual("http://localhost", url)
            self.assertEqual("123", etag)
            self.assertEqual(now, datetime.fromtimestamp(mod_date))
            frontier._current_uris[url] = uri

    def test_crawluri_from_uri(self):

        now = datetime(*datetime.fromtimestamp(time.time()).timetuple()[0:6])
        now_timestamp = time.mktime(now.timetuple())
        next_crawl_date = now + timedelta(days=1)
        next_crawl_date_timestamp = time.mktime(next_crawl_date.timetuple())

        s = Settings()
        s.FRONTIER_STATE_FILE = ":memory:"

        frontier = AbstractBaseFrontier(s, StreamHandler(sys.stdout),
                SQLiteSingleHostUriQueue(s.FRONTIER_STATE_FILE),
                SimpleTimestampPrioritizer(s))

        uri = ("http://localhost", "123", now_timestamp, 1,
                next_crawl_date_timestamp)

        curi = frontier._crawluri_from_uri(uri)

        self.assertEqual("http://localhost", curi.url)
        self.assertEqual("123", curi.req_header["Etag"])
        self.assertEqual(serialize_date_time(now), curi.req_header["Last-Modified"])

    def test_crawluri_from_uri_with_credentials(self):

        now = datetime(*datetime.fromtimestamp(time.time()).timetuple()[0:6])
        now_timestamp = time.mktime(now.timetuple())
        next_crawl_date = now + timedelta(days=1)
        next_crawl_date_timestamp = time.mktime(next_crawl_date.timetuple())

        s = Settings()
        s.FRONTIER_STATE_FILE = ":memory:"

        frontier = AbstractBaseFrontier(s, StreamHandler(sys.stdout),
                SQLiteSingleHostUriQueue(s.FRONTIER_STATE_FILE),
                SimpleTimestampPrioritizer(s))

        uri = ("http://user:passwd@localhost", "123", now_timestamp, 1,
            next_crawl_date_timestamp)

        curi = frontier._crawluri_from_uri(uri)

        self.assertEqual("http://user:passwd@localhost", curi.url)
        self.assertEqual("123", curi.req_header["Etag"])
        self.assertEqual(serialize_date_time(now),
            curi.req_header["Last-Modified"])
        self.assertEqual("user", curi.optional_vars[CURI_SITE_USERNAME])
        self.assertEqual("passwd", curi.optional_vars[CURI_SITE_PASSWORD])

    def test_sinks(self):
        now = datetime(*datetime.fromtimestamp(time.time()).timetuple()[0:6])
        s = Settings()
        s.FRONTIER_STATE_FILE = ":memory:"

        frontier = AbstractBaseFrontier(s, StreamHandler(sys.stdout),
                SQLiteSingleHostUriQueue(s.FRONTIER_STATE_FILE),
                SimpleTimestampPrioritizer(s))
        frontier.add_sink(AbstractCrawlUriSink())

        curi = CrawlUri("http://localhost")
        curi.rep_header = { "Etag" : "123", "Date" : serialize_date_time(now) }
        curi.current_priority = 2

        frontier._add_to_heap(frontier._uri_from_curi(curi), 0)
        frontier.process_successful_crawl(curi)

        frontier._add_to_heap(frontier._uri_from_curi(curi), 0)
        frontier.process_not_found(curi)

        frontier._add_to_heap(frontier._uri_from_curi(curi), 0)
        frontier.process_redirect(curi)

        frontier._add_to_heap(frontier._uri_from_curi(curi), 0)
        frontier.process_server_error(curi)


class SingleHostFrontierTest(unittest.TestCase):

    def test_that_updating_heap_works(self):

        s = Settings()
        s.FRONTIER_STATE_FILE = ":memory:"

        frontier = SingleHostFrontier(s, StreamHandler(sys.stdout))

        q1 = []
        q2 = []

        now = datetime(*datetime.fromtimestamp(
            time.time()).timetuple()[0:6]) - timedelta(days=2)

        for i in range(1, 20):
            curi = CrawlUri("http://localhost/test/%s" % i)
            curi.current_priority = (i % 2 + 1)
            curi.rep_header = { "Etag" : "123%s" % i, "Date" : serialize_date_time(now) }

            frontier.add_uri(curi)

            if i % 2 == 0:
                (url, etag, mod_date, next_date, prio) = frontier._uri_from_curi(curi)
                next_date = next_date - 1000 * 60 * 5
                frontier._front_end_queues.update_uri((url, etag, mod_date,
                            next_date, prio))
                q2.append(curi.url)
            else:
                q1.append(curi.url)

        self.assertRaises(Empty, frontier._heap.get_nowait)

        for i in range(1, 10):
            frontier._next_possible_crawl = time.time()
            candidate_uri = frontier.get_next()

            if candidate_uri.url in q1:
                self.assertTrue(candidate_uri.url in q1)
                q1.remove(candidate_uri.url)
            elif candidate_uri.url in q2:
                self.assertTrue(candidate_uri.url in q2)
                q2.remove(candidate_uri.url)

        self.assertEqual(10, len(q1))
        self.assertEqual(0, len(q2))

        self.assertRaises(Empty, frontier.get_next)

    def test_that_time_based_politeness_works(self):

        s = Settings()
        s.FRONTIER_STATE_FILE = ":memory:"

        frontier = SingleHostFrontier(s, StreamHandler(sys.stdout))

        now = datetime(*datetime.fromtimestamp(
            time.time()).timetuple()[0:6]) - timedelta(days=2)
        curi = CrawlUri("http://localhost/test")
        curi.current_priority = 3
        curi.rep_header = { "Etag" : "123", "Date" : serialize_date_time(now) }
        curi.req_time = 0.5

        frontier._add_to_heap(frontier._uri_from_curi(curi), 0)

        a = frontier._next_possible_crawl
        frontier.process_successful_crawl(curi)
        self.assertTrue(frontier._next_possible_crawl > a)
        self.assertTrue(frontier._next_possible_crawl > time.time())
        self.assertRaises(Empty, frontier.get_next)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_http_extractor
#
# Copyright (c) 2010 Daniel Truemper truemped@googlemail.com
#
# test_http_extractor.py 17-Mar-2011
#
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
#
#
import unittest

from spyder.core.constants import CURI_EXTRACTED_URLS
from spyder.core.settings import Settings
from spyder.processor.httpextractor import HttpExtractor
from spyder.thrift.gen.ttypes import CrawlUri


class HttpExtractorTest(unittest.TestCase):

    def test_correct_extraction(self):

        s = Settings()

        curi = CrawlUri("http://localhost")
        curi.status_code = 302
        curi.rep_header = {"Location": "http://localhost/index.html"}
        curi.optional_vars = dict()

        xtor = HttpExtractor(s)
        curi = xtor(curi)

        self.assertTrue(CURI_EXTRACTED_URLS in curi.optional_vars)
        self.assertEquals("http://localhost/index.html",
                curi.optional_vars[CURI_EXTRACTED_URLS])

    def test_only_on_redirect(self):

        s = Settings()

        curi = CrawlUri("http://localhost")
        curi.status_code = 200
        curi.rep_header = {"Location": "http://localhost/index.html"}
        curi.optional_vars = dict()

        xtor = HttpExtractor(s)
        curi = xtor(curi)

        self.assertFalse(CURI_EXTRACTED_URLS in curi.optional_vars)

    def test_relative_links(self):

        s = Settings()

        curi = CrawlUri("http://localhost")
        curi.status_code = 303
        curi.rep_header = {"Location": "/index.html"}
        curi.optional_vars = dict()

        xtor = HttpExtractor(s)
        curi = xtor(curi)

        self.assertTrue(CURI_EXTRACTED_URLS in curi.optional_vars)
        self.assertEquals("http://localhost/index.html",
                curi.optional_vars[CURI_EXTRACTED_URLS])

########NEW FILE########
__FILENAME__ = test_limiter
#
# Copyright (c) 2011 Daniel Truemper truemped@googlemail.com
#
# test_limiter.py 18-Jan-2011
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import unittest

from spyder.core.constants import CURI_EXTRACTION_FINISHED, CURI_OPTIONAL_TRUE
from spyder.processor import limiter
from spyder.thrift.gen.ttypes import CrawlUri


class LimiterTestCase(unittest.TestCase):

    def test_do_not_process_robots_works(self):

        curi = CrawlUri()
        curi.effective_url = "http://127.0.0.1/robots.txt"
        curi.optional_vars = dict()

        l = limiter.DefaultLimiter(None)

        for i in range(2):
            l._do_not_process_robots(curi)
            self.assertEqual(CURI_OPTIONAL_TRUE,
                    curi.optional_vars[CURI_EXTRACTION_FINISHED])


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_masterprocess
#
# Copyright (c) 2011 Daniel Truemper truemped@googlemail.com
#
# test_masterprocess.py 07-Feb-2011
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import logging
import unittest

import sys

from spyder.core.settings import Settings
from spyder import masterprocess


class MasterProcessTest(unittest.TestCase):

    def test_create_frontier_works(self):

        handler = logging.StreamHandler(sys.stdout)
        s = Settings()
        s.FRONTIER_STATE_FILE = ":memory:"

        frontier = masterprocess.create_frontier(s, handler)

        self.assertTrue(frontier is not None)

########NEW FILE########
__FILENAME__ = test_messages
#
# Copyright (c) 2011 Daniel Truemper truemped@googlemail.com
#
# test_messages.py 14-Jan-2011
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import unittest

from spyder.core.messages import DataMessage, MgmtMessage
from spyder.core.messages import serialize_crawl_uri, deserialize_crawl_uri
from spyder.thrift.gen.ttypes import CrawlUri

class TestMessages(unittest.TestCase):

    def test_that_serialization_works(self):
    
        curi = CrawlUri(url="http://localhost")

        serialized = serialize_crawl_uri(curi)
        deserialized = deserialize_crawl_uri(serialized)

        self.assertEqual(curi, deserialized)

    def test_that_data_messages_work(self):
        identity = "me myself and i"
        curi = CrawlUri(url="http://localhost")
        serialized = serialize_crawl_uri(curi)

        msg = DataMessage([identity, serialized])

        self.assertEqual(identity, msg.identity)
        self.assertEqual(curi, msg.curi)
        self.assertEqual([identity, serialized], msg.serialize())
        self.assertEqual(msg, DataMessage(msg.serialize()))

    def test_that_mgmt_messages_work(self):
        topic = "me"
        identity = "myself"
        data = "and i"

        msg = MgmtMessage([topic, identity, data])

        self.assertEqual(topic, msg.topic)
        self.assertEqual(identity, msg.identity)
        self.assertEqual(data, msg.data)
        self.assertEqual([topic, identity, data], msg.serialize())
        self.assertEqual(msg, MgmtMessage(msg.serialize()))

    def test_that_construction_works(self):
        msg = DataMessage(identity="me")
        self.assertEqual("me", msg.identity)
        self.assertEqual(None, msg.curi)

        msg = DataMessage(curi="bla")
        self.assertEqual("bla", msg.curi)
        self.assertEqual(None, msg.identity)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_mgmt
#
# Copyright (c) 2011 Daniel Truemper truemped@googlemail.com
#
# test_mgmt.py 10-Jan-2011
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import unittest

import time

import zmq
from zmq.eventloop.ioloop import IOLoop
from zmq.eventloop.zmqstream import ZMQStream

from spyder.core.messages import MgmtMessage
from spyder.core.mgmt import ZmqMgmt
from spyder.core.constants import *


class ManagementIntegrationTest(unittest.TestCase):


    def setUp(self):
        self._io_loop = IOLoop.instance()
        self._ctx = zmq.Context(1)

        sock = self._ctx.socket(zmq.PUB)
        sock.bind('inproc://master/worker/coordination')
        self._master_pub_sock = sock
        self._master_pub = ZMQStream(sock, self._io_loop)

        self._worker_sub = self._ctx.socket(zmq.SUB)
        self._worker_sub.setsockopt(zmq.SUBSCRIBE, "")
        self._worker_sub.connect('inproc://master/worker/coordination')

        self._worker_pub = self._ctx.socket(zmq.PUB)
        self._worker_pub.bind( 'inproc://worker/master/coordination' )

        sock = self._ctx.socket(zmq.SUB)
        sock.setsockopt(zmq.SUBSCRIBE, "")
        sock.connect( 'inproc://worker/master/coordination' )
        self._master_sub_sock = sock
        self._master_sub = ZMQStream(sock, self._io_loop)

        self._topic = ZMQ_SPYDER_MGMT_WORKER + 'testtopic'

    def tearDown(self):
        self._master_pub.close()
        self._master_pub_sock.close()
        self._worker_sub.close()
        self._worker_pub.close()
        self._master_sub.close()
        self._master_sub_sock.close()
        self._ctx.term()

    def call_me(self, msg):
        self.assertEqual(self._topic, msg.topic)
        self.assertEqual('test'.encode(), msg.data)
        death = MgmtMessage(topic=ZMQ_SPYDER_MGMT_WORKER,
                data=ZMQ_SPYDER_MGMT_WORKER_QUIT)
        self._master_pub.send_multipart(death.serialize())

    def on_end(self, msg):
        self.assertEqual(ZMQ_SPYDER_MGMT_WORKER_QUIT, msg.data)
        self._io_loop.stop()


    def test_simple_mgmt_session(self):
        
        mgmt = ZmqMgmt(self._worker_sub, self._worker_pub, io_loop=self._io_loop)
        mgmt.start()

        self.assertRaises(ValueError, mgmt.add_callback, "test", "test")

        mgmt.add_callback(self._topic, self.call_me)
        mgmt.add_callback(ZMQ_SPYDER_MGMT_WORKER, self.on_end)

        test_msg = MgmtMessage(topic=self._topic, data='test'.encode())
        self._master_pub.send_multipart(test_msg.serialize())

        def assert_correct_mgmt_answer(raw_msg):
            msg = MgmtMessage(raw_msg)
            self.assertEqual(ZMQ_SPYDER_MGMT_WORKER_QUIT_ACK, msg.data)
            mgmt.remove_callback(self._topic, self.call_me)
            mgmt.remove_callback(ZMQ_SPYDER_MGMT_WORKER, self.on_end)
            self.assertEqual({}, mgmt._callbacks)

        self._master_sub.on_recv(assert_correct_mgmt_answer)

        self._io_loop.start()


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_multiple_frontier
#
# Copyright (c) 2011 Daniel Truemper truemped@googlemail.com
#
# test_multiple_frontier.py 31-Mar-2011
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import logging
from logging import StreamHandler

from datetime import datetime
from datetime import timedelta
import time
import unittest
import sys

from spyder.core.frontier import MultipleHostFrontier
from spyder.core.settings import Settings
from spyder.time import serialize_date_time, deserialize_date_time
from spyder.thrift.gen.ttypes import CrawlUri


class MultipleHostFrontierTest(unittest.TestCase):

    def test_that_adding_uris_works(self):

        s = Settings()
        s.FRONTIER_STATE_FILE = ":memory:"

        frontier = MultipleHostFrontier(s, StreamHandler(sys.stdout))

        now = datetime(*datetime.fromtimestamp(time.time()).timetuple()[0:6])
        next_crawl_date = now + timedelta(days=1)
        curi = CrawlUri("http://localhost")
        curi.rep_header = { "Etag" : "123", "Date" : serialize_date_time(now) }
        curi.current_priority = 2

        frontier.add_uri(curi)

        cur = frontier._front_end_queues._cursor

        curi = CrawlUri("http://foreignhost")
        curi.rep_header = { "Etag" : "123", "Date" : serialize_date_time(now) }
        curi.current_priority = 1

        frontier.add_uri(curi)

        idents = {"localhost": -1, "foreignhost": -1}
        cur.execute("SELECT * FROM queue_identifiers")
        for row in cur:
            self.assertTrue(row['identifier'] in idents.keys())
            idents["http://%s" % row['identifier']] = row['queue']

        cur.execute("SELECT * FROM queues")
        for row in cur:
            self.assertEqual(idents[row['url']], row['queue'])

        self.assertEqual(2, frontier._front_end_queues.get_queue_count())

    def test_queues_work(self):

        s = Settings()
        s.FRONTIER_STATE_FILE = ":memory:"
        s.FRONTIER_ACTIVE_QUEUES = 1
        s.FRONTIER_QUEUE_BUDGET = 4
        s.FRONTIER_QUEUE_BUDGET_PUNISH = 5

        frontier = MultipleHostFrontier(s, StreamHandler(sys.stdout))

        now = datetime(*datetime.fromtimestamp(time.time()).timetuple()[0:6])
        curi1 = CrawlUri("http://localhost")
        curi1.current_priority = 2
        curi1.req_time = 0.4

        frontier.add_uri(curi1)

        cur = frontier._front_end_queues._cursor

        curi2 = CrawlUri("http://foreignhost")
        curi2.current_priority = 1
        curi2.req_time = 1.4

        frontier.add_uri(curi2)

        self.assertEqual(0, len(frontier._current_queues))
        frontier._maybe_add_queues()

        self.assertEqual(1, len(frontier._current_queues))
        for q1 in frontier._current_queues.keys():
            pass

        self.assertEquals(4, frontier._budget_politeness[q1])
        frontier._cleanup_budget_politeness()
        self.assertEquals(4, frontier._budget_politeness[q1])

        frontier._update_heap()
        self.assertEqual(1, len(frontier._current_queues))

        if q1 == 1:
            curi1.status_code = 500
            frontier.process_server_error(curi1)
        else:
            curi1.status_code = 500
            frontier.process_server_error(curi2)

        self.assertEquals(-1, frontier._budget_politeness[q1])

        frontier._cleanup_budget_politeness()

        self.assertEqual(1, len(frontier._current_queues))
        for q2 in frontier._current_queues.keys():
            pass

        self.assertEquals(4, frontier._budget_politeness[q2])
        frontier._cleanup_budget_politeness()
        self.assertEquals(4, frontier._budget_politeness[q2])
 
        frontier._update_heap()
        self.assertEqual(1, len(frontier._current_queues))

        if q2 == 1:
            curi1.status_code = 200
            frontier.process_successful_crawl(curi1)
        else:
            curi2.status_code = 200
            frontier.process_successful_crawl(curi2)

        self.assertEquals(3, frontier._budget_politeness[q2])

        frontier._cleanup_budget_politeness()

    def test_with_multiple_active_queues(self):

        s = Settings()
        s.FRONTIER_STATE_FILE = ":memory:"
        s.FRONTIER_ACTIVE_QUEUES = 2
        s.FRONTIER_QUEUE_BUDGET = 4
        s.FRONTIER_QUEUE_BUDGET_PUNISH = 5

        frontier = MultipleHostFrontier(s, StreamHandler(sys.stdout))

        now = datetime(*datetime.fromtimestamp(time.time()).timetuple()[0:6])
        curi1 = CrawlUri("http://localhost")
        curi1.current_priority = 2
        curi1.req_time = 0.4

        frontier.add_uri(curi1)

        cur = frontier._front_end_queues._cursor

        curi2 = CrawlUri("http://www.google.de")
        curi2.current_priority = 1
        curi2.req_time = 1.4

        frontier.add_uri(curi2)

        self.assertEqual(0, len(frontier._current_queues))
        frontier._maybe_add_queues()

        self.assertEqual(2, len(frontier._current_queues))

        next_url = frontier.get_next()


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_queue_assignment
#
# Copyright (c) 2011 Daniel Truemper truemped@googlemail.com
#
# test_queue_assignment.py 31-Mar-2011
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import unittest

from spyder.core.settings import Settings
from spyder.core.dnscache import DnsCache
from spyder.core.queueassignment import HostBasedQueueAssignment
from spyder.core.queueassignment import IpBasedQueueAssignment

class HostBasedQueueAssignmentTest(unittest.TestCase):

    def test_host_based_assignment(self):

        s = Settings()
        dns = DnsCache(s)
        assign = HostBasedQueueAssignment(dns)

        url = "http://www.google.com/pille/palle"
        self.assertEqual("www.google.com", assign.get_identifier(url))



class IpBasedQueueAssignmentTest(unittest.TestCase):

    def test_ip_based_assignment(self):

        s = Settings()
        dns = DnsCache(s)
        assign = IpBasedQueueAssignment(dns)

        url = "http://localhost:12345/this"
        self.assertEqual("127.0.0.1", assign.get_identifier(url))

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_queue_selector
#
# Copyright (c) 2011 Daniel Truemper truemped@googlemail.com
#
# test_queue_selector.py 25-Jan-2011
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import unittest

from collections import defaultdict

from spyder.core.queueselector import BiasedQueueSelector


class BiasedQueueSelectorTest(unittest.TestCase):

    def test_histogram(self):

        # create a selector with 10 queues
        selector = BiasedQueueSelector(10)

        histogram = defaultdict(int)

        for i in xrange(100000):
            histogram[selector.get_queue()] += 1

        for i in range(1,9):
            self.assertTrue(histogram[i] > histogram[i+1])


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_regex_scoper
#
# Copyright (c) 2011 Daniel Truemper truemped@googlemail.com
#
# test_regex_scoper.py 24-Jan-2011
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import unittest

from spyder.core.constants import CURI_EXTRACTED_URLS
from spyder.core.settings import Settings
from spyder.thrift.gen.ttypes import CrawlUri

from spyder.processor.scoper import *

class RegexScoperTest(unittest.TestCase):

    def test_regex_scoper(self):

        curi = CrawlUri()
        curi.optional_vars = dict()
        curi.optional_vars[CURI_EXTRACTED_URLS] = "\n".join([
            "http://www.google.de/index.html",
            "ftp://www.google.de/pillepalle.avi",
        ])

        settings = Settings()
        settings.REGEX_SCOPE_POSITIVE = ['^.*\.html']
        settings.REGEX_SCOPE_NEGATIVE = ['^.*\.avi']
        scoper = RegexScoper(settings)

        curi = scoper(curi)

        print curi.optional_vars[CURI_EXTRACTED_URLS]
        self.assertTrue("http://www.google.de/index.html" in
                curi.optional_vars[CURI_EXTRACTED_URLS])
        self.assertFalse("ftp://www.google.de/pillepalle.avi" in
                curi.optional_vars[CURI_EXTRACTED_URLS])


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_settings
#
# Copyright (c) 2011 Daniel Truemper truemped@googlemail.com
#
# test_settings.py 10-Jan-2011
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import unittest


class SettingsTest(unittest.TestCase):

    def test_loading_default_settings_works(self):

        from spyder import defaultsettings
        from spyder.core.settings import Settings

        settings = Settings()
        self.assertEqual(defaultsettings.ZEROMQ_MGMT_MASTER,
                settings.ZEROMQ_MGMT_MASTER)


    def test_loading_custom_settings_works(self):

        from spyder import defaultsettings
        from spyder.core.settings import Settings

        import test_settings_settings
        settings = Settings(test_settings_settings)

        self.assertEqual(test_settings_settings.ZEROMQ_MGMT_WORKER,
                settings.ZEROMQ_MGMT_WORKER)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_settings_settings
#
# Copyright (c) 2011 Daniel Truemper truemped@googlemail.com
#
# test_settings_settings.py 10-Jan-2011
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

ZEROMQ_MGMT_WORKER = "test"

########NEW FILE########
__FILENAME__ = test_sqlite_multiple_queues
#
# Copyright (c) 2011 Daniel Truemper truemped@googlemail.com
#
# test_sqlite_multiple_queues.py 15-Mar-2011
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import unittest

import time

from spyder.core.sqlitequeues import SQLiteMultipleHostUriQueue, UriNotFound


class SqliteQueuesTest(unittest.TestCase):


    def test_adding_works(self):

        uri = ("http://localhost", 1, "etag", int(time.time()*1000),
                int(time.time() * 1000), 1)

        q = SQLiteMultipleHostUriQueue(":memory:")
        q.add_uri(uri)

        self.assertEqual(1, q.qsize())

        cursor = q._connection.execute("SELECT * FROM queues WHERE queue=1")
        uri_res = cursor.fetchone()
        (url, queue, etag, mod_date, next_date, prio) = uri
        (url_res, queue_res, etag_res, mod_date_res, next_date_res, prio_res) = uri_res
        self.assertEqual(url, url_res)
        self.assertEqual(queue, queue_res)
        self.assertEqual(etag, etag_res)
        self.assertEqual(mod_date, mod_date_res)
        self.assertEqual(prio, prio_res)
        self.assertEqual(next_date, next_date_res)

        q.close()

    def test_updating_works(self):

        uri = ("http://localhost", 1, "etag", int(time.time()*1000),
                int(time.time() * 1000), 1)

        q = SQLiteMultipleHostUriQueue(":memory:")
        q.add_uri(uri)

        uri = ("http://localhost", 1, "etag", int(time.time()*1000),
                int(time.time() * 1000), 2)

        q.update_uri(uri)

        cursor = q._connection.execute("SELECT * FROM queues WHERE queue=1")
        uri_res = cursor.fetchone()
        (url, queue, etag, mod_date, next_date, prio) = uri
        (url_res, queue_res, etag_res, mod_date_res, next_date_res, prio_res) = uri_res
        self.assertEqual(url, url_res)
        self.assertEqual(etag, etag_res)
        self.assertEqual(mod_date, mod_date_res)
        self.assertEqual(prio, prio_res)
        self.assertEqual(next_date, next_date_res)

        q.close()

    def test_adding_lists_works(self):

        uris = [("http://localhost", 1, "etag", int(time.time()*1000),
                int(time.time() * 1010), 1),
        ]

        q = SQLiteMultipleHostUriQueue(":memory:")
        q.add_uris(uris)

        cursor = q._connection.execute("SELECT * FROM queues WHERE queue=1")
        uri_res = cursor.fetchone()
        (url, queue, etag, mod_date, next_date, prio) = uris[0]
        (url_res, queue_res, etag_res, mod_date_res, next_date_res, prio_res) = uri_res
        self.assertEqual(url, url_res)
        self.assertEqual(etag, etag_res)
        self.assertEqual(mod_date, mod_date_res)
        self.assertEqual(prio, prio_res)
        self.assertEqual(next_date, next_date_res)

    def test_updating_lists_works(self):

        uris = [("http://localhost", 1, "etag", int(time.time()*1000),
                int(time.time() * 1000), 1),
        ]

        q = SQLiteMultipleHostUriQueue(":memory:")
        q.add_uris(uris)

        uris = [("http://localhost", 1, "etag", int(time.time()*1000),
                int(time.time() * 1000), 2),
        ]

        q.update_uris(uris)

        cursor = q._connection.execute("SELECT * FROM queues WHERE queue=1")
        uri_res = cursor.fetchone()
        (url, queue, etag, mod_date, next_date, prio) = uris[0]
        (url_res, queue_res, etag_res, mod_date_res, next_date_res, prio_res) = uri_res
        self.assertEqual(url, url_res)
        self.assertEqual(etag, etag_res)
        self.assertEqual(mod_date, mod_date_res)
        self.assertEqual(prio, prio_res)
        self.assertEqual(next_date, next_date_res)

    def test_removing_lists_works(self):

        uris = [("http://localhost", 1, "etag", int(time.time()*1000),
                int(time.time() * 1000), 1),
            ("http://fogeignhost", 1, "ETAG", int(time.time()*1000),
             int(time.time() * 1000), 2),
        ]

        q = SQLiteMultipleHostUriQueue(":memory:")
        q.add_uris(uris)

        q.remove_uris(uris)

        cursor = q._connection.execute("SELECT * FROM queues WHERE queue=1")
        self.assertTrue(None is cursor.fetchone())

    def test_iterating_over_all_uris_works(self):

        uris = [("http://localhost", 1, "etag", int(time.time()*1000),
                int(time.time() * 1000), 1),
            ("http://foreignhost", 1, "ETAG", int(time.time()*1000),
             int(time.time() * 1000), 2),
        ]
        urls = ["http://localhost", "http://foreignhost"]

        q = SQLiteMultipleHostUriQueue(":memory:")
        q.add_uris(uris)

        uri = q.get_uri("http://foreignhost")
        self.assertEqual(uris[1], uri)

        self.assertRaises(UriNotFound, q.get_uri, "http://gibtsnuesch")

        for url in q.all_uris():
            self.assertTrue(url in urls)

    def test_queue_head_works(self):

        uris = [("http://localhost", 1, "etag", int(time.time()*1000),
                int(time.time() * 1000), 1),
            ("http://fogeignhost", 1, "ETAG", int(time.time()*1000),
             int(time.time() * 1001), 2),
        ]

        q = SQLiteMultipleHostUriQueue(":memory:")
        q.add_uris(uris)

        self.assertEqual(2, q.qsize())
        self.assertEqual(2, q.qsize(queue=1))

        (url1, queue1,  etag1, mod_date1, next_date1, prio1) = uris[0]
        (url2, queue2, etag2, mod_date2, next_date2, prio2) = uris[1]

        for uri_res in q.queue_head(1, n=1, offset=0):
            (url_res, queue_res,  etag_res, mod_date_res, next_date_res,
                prio_res) = uri_res
            self.assertEqual(url1, url_res)
            self.assertEqual(queue1, queue_res)
            self.assertEqual(etag1, etag_res)
            self.assertEqual(mod_date1, mod_date_res)
            self.assertEqual(prio1, prio_res)
            self.assertEqual(next_date1, next_date_res)

        for uri_res in q.queue_head(1, n=1, offset=1):
            (url_res, queue_res,  etag_res, mod_date_res, next_date_res,
                prio_res) = uri_res
            self.assertEqual(url2, url_res)
            self.assertEqual(queue2, queue_res)
            self.assertEqual(etag2, etag_res)
            self.assertEqual(mod_date2, mod_date_res)
            self.assertEqual(prio2, prio_res)
            self.assertEqual(next_date2, next_date_res)

        uris.append(("http://localhost/1", 1, "eTag", int(time.time()*1000),
                    int(time.time()*1002), 1))
        (url3, queue3, etag3, mod_date3, next_date3, prio3) = uris[2]
        q.add_uri(uris[2])

        self.assertEqual(3, q.qsize())
        self.assertEqual(3, q.qsize(queue=1))

        q.ignore_uri("http://localhost", 404)

        for uri_res in q.queue_head(1, n=1, offset=1):
            (url_res, queue_res,  etag_res, mod_date_res, next_date_res,
                prio_res) = uri_res
            self.assertEqual(url3, url_res)
            self.assertEqual(queue3, queue_res)
            self.assertEqual(etag3, etag_res)
            self.assertEqual(mod_date3, mod_date_res)
            self.assertEqual(prio3, prio_res)
            self.assertEqual(next_date3, next_date_res)

        uris.append(("http://localhost2/1", 2, "eTag", int(time.time()*1000),
                    int(time.time()*1002), 1))
        (url4, queue4, etag4, mod_date4, next_date4, prio4) = uris[3]
        q.add_uri(uris[3])

        self.assertEqual(4, q.qsize())
        self.assertEqual(2, q.qsize(queue=1))
        self.assertEqual(1, q.qsize(queue=2))

        for uri_res in q.queue_head(2, n=1, offset=0):
            (url_res, queue_res,  etag_res, mod_date_res, next_date_res,
                prio_res) = uri_res
            self.assertEqual(url4, url_res)
            self.assertEqual(queue4, queue_res)
            self.assertEqual(etag4, etag_res)
            self.assertEqual(mod_date4, mod_date_res)
            self.assertEqual(prio4, prio_res)
            self.assertEqual(next_date4, next_date_res)

    def test_that_queues_work(self):

        q = SQLiteMultipleHostUriQueue(':memory:')

        for queue in q.get_all_queues():
            self.assertFalse(True)

        qid1 = q.add_or_create_queue('test')
        
        for (queue, ident) in q.get_all_queues():
            self.assertEqual(qid1, queue)
            self.assertEqual('test', ident)

        qid2 = q.add_or_create_queue('test2')

        i = 0
        for (queue, ident) in q.get_all_queues():
            if i==0:
                self.assertEqual(qid1, queue)
                self.assertEqual('test', ident)
                i += 1
            else:
                self.assertEqual(qid2, queue)
                self.assertEqual('test2', ident)

        self.assertEqual(qid1, q.add_or_create_queue('test'))


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_sqlite_queues
#
# Copyright (c) 2011 Daniel Truemper truemped@googlemail.com
#
# test_sqlite_queues.py 25-Jan-2011
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import unittest

import time

from spyder.core.sqlitequeues import SQLiteSingleHostUriQueue, UriNotFound


class SqliteQueuesTest(unittest.TestCase):

    def test_adding_works(self):

        uri = ("http://localhost", "etag", int(time.time()*1000),
                int(time.time() * 1000), 1)

        q = SQLiteSingleHostUriQueue(":memory:")
        q.add_uri(uri)

        self.assertEqual(1, len(q))

        cursor = q._connection.execute("SELECT * FROM queue")
        uri_res = cursor.fetchone()
        (url, etag, mod_date, next_date, prio) = uri
        (url_res, etag_res, mod_date_res, next_date_res, prio_res) = uri_res
        self.assertEqual(url, url_res)
        self.assertEqual(etag, etag_res)
        self.assertEqual(mod_date, mod_date_res)
        self.assertEqual(prio, prio_res)
        self.assertEqual(next_date, next_date_res)

        q.close()

    def test_updating_works(self):

        uri = ("http://localhost", "etag", int(time.time()*1000),
                int(time.time() * 1000), 1)

        q = SQLiteSingleHostUriQueue(":memory:")
        q.add_uri(uri)

        uri = ("http://localhost", "etag", int(time.time()*1000),
                int(time.time() * 1000), 2)

        q.update_uri(uri)

        cursor = q._connection.execute("SELECT * FROM queue")
        uri_res = cursor.fetchone()
        (url, etag, mod_date, next_date, prio) = uri
        (url_res, etag_res, mod_date_res, next_date_res, prio_res) = uri_res
        self.assertEqual(url, url_res)
        self.assertEqual(etag, etag_res)
        self.assertEqual(mod_date, mod_date_res)
        self.assertEqual(prio, prio_res)
        self.assertEqual(next_date, next_date_res)

    def test_adding_lists_works(self):

        uris = [("http://localhost", "etag", int(time.time()*1000),
                int(time.time() * 1010), 1),
        ]

        q = SQLiteSingleHostUriQueue(":memory:")
        q.add_uris(uris)

        cursor = q._connection.execute("SELECT * FROM queue")
        uri_res = cursor.fetchone()
        (url, etag, mod_date, next_date, prio) = uris[0]
        (url_res, etag_res, mod_date_res, next_date_res, prio_res) = uri_res
        self.assertEqual(url, url_res)
        self.assertEqual(etag, etag_res)
        self.assertEqual(mod_date, mod_date_res)
        self.assertEqual(prio, prio_res)
        self.assertEqual(next_date, next_date_res)

    def test_updating_lists_works(self):

        uris = [("http://localhost", "etag", int(time.time()*1000),
                int(time.time() * 1000), 1),
        ]

        q = SQLiteSingleHostUriQueue(":memory:")
        q.add_uris(uris)

        uris = [("http://localhost", "etag", int(time.time()*1000),
                int(time.time() * 1000), 2),
        ]

        q.update_uris(uris)

        cursor = q._connection.execute("SELECT * FROM queue")
        uri_res = cursor.fetchone()
        (url, etag, mod_date, next_date, prio) = uris[0]
        (url_res, etag_res, mod_date_res, next_date_res, prio_res) = uri_res
        self.assertEqual(url, url_res)
        self.assertEqual(etag, etag_res)
        self.assertEqual(mod_date, mod_date_res)
        self.assertEqual(prio, prio_res)
        self.assertEqual(next_date, next_date_res)

    def test_removing_lists_works(self):

        uris = [("http://localhost", "etag", int(time.time()*1000),
                int(time.time() * 1000), 1),
            ("http://fogeignhost", "ETAG", int(time.time()*1000),
             int(time.time() * 1000), 2),
        ]

        q = SQLiteSingleHostUriQueue(":memory:")
        q.add_uris(uris)

        q.remove_uris(uris)

        cursor = q._connection.execute("SELECT * FROM queue")
        self.assertTrue(None is cursor.fetchone())

    def test_iterating_over_all_uris_works(self):

        uris = [("http://localhost", "etag", int(time.time()*1000),
                int(time.time() * 1000), 1),
            ("http://foreignhost", "ETAG", int(time.time()*1000),
             int(time.time() * 1000), 2),
        ]
        urls = ["http://localhost", "http://foreignhost"]

        q = SQLiteSingleHostUriQueue(":memory:")
        q.add_uris(uris)

        uri = q.get_uri("http://foreignhost")
        self.assertEqual(uris[1], uri)

        self.assertRaises(UriNotFound, q.get_uri, "http://gibtsnuesch")

        for url in q.all_uris():
            self.assertTrue(url in urls)

    def test_queue_head_works(self):

        uris = [("http://localhost", "etag", int(time.time()*1000),
                int(time.time() * 1000), 1),
            ("http://fogeignhost", "ETAG", int(time.time()*1000),
             int(time.time() * 1001), 2),
        ]

        q = SQLiteSingleHostUriQueue(":memory:")
        q.add_uris(uris)

        (url1, etag1, mod_date1, next_date1, prio1) = uris[0]
        (url2, etag2, mod_date2, next_date2, prio2) = uris[1]

        for uri_res in q.queue_head(n=1, offset=0):
            (url_res, etag_res, mod_date_res, next_date_res, prio_res) = uri_res
            self.assertEqual(url1, url_res)
            self.assertEqual(etag1, etag_res)
            self.assertEqual(mod_date1, mod_date_res)
            self.assertEqual(prio1, prio_res)
            self.assertEqual(next_date1, next_date_res)

        for uri_res in q.queue_head(n=1, offset=1):
            (url_res, etag_res, mod_date_res, next_date_res, prio_res) = uri_res
            self.assertEqual(url2, url_res)
            self.assertEqual(etag2, etag_res)
            self.assertEqual(mod_date2, mod_date_res)
            self.assertEqual(prio2, prio_res)
            self.assertEqual(next_date2, next_date_res)

        uris.append(("http://localhost/1", "eTag", int(time.time()*1000),
                    int(time.time()*1002), 1))
        (url3, etag3, mod_date3, next_date3, prio3) = uris[2]
        q.add_uri(uris[2])

        q.ignore_uri("http://localhost", 404)

        for uri_res in q.queue_head(n=1, offset=1):
            (url_res, etag_res, mod_date_res, next_date_res, prio_res) = uri_res
            self.assertEqual(url3, url_res)
            self.assertEqual(etag3, etag_res)
            self.assertEqual(mod_date3, mod_date_res)
            self.assertEqual(prio3, prio_res)
            self.assertEqual(next_date3, next_date_res)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_strip_session_ids
#
# Copyright (c) 2011 Daniel Truemper truemped@googlemail.com
#
# test_strip_session_ids.py 14-Apr-2011
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
#
import unittest

from spyder.core.constants import CURI_EXTRACTED_URLS
from spyder.core.settings import Settings
from spyder.processor.stripsessions import StripSessionIds
from spyder.thrift.gen.ttypes import CrawlUri


class StripSessionIdsTest(unittest.TestCase):

    def test_that_stripping_session_stuff_works(self):

        s = StripSessionIds(Settings())

        url = "http://pREis.de/traeger/index.php?sid=8429fb3ae210a2a0e28800b7f48d90f2"

        self.assertEqual("http://pREis.de/traeger/index.php?",
                s._remove_session_ids(url))

        url = "http://preis.de/traeger/index.php?jsessionid=8429fb3ae210a2a0e28800b7f48d90f2"

        self.assertEqual("http://preis.de/traeger/index.php?",
                s._remove_session_ids(url))

        url = "http://preis.de/traeger/index.php?phpsessid=8429fb3ae210a2a0e28800b7f48d90f2"

        self.assertEqual("http://preis.de/traeger/index.php?",
                s._remove_session_ids(url))

        url = "http://preis.de/traeger/index.php?aspsessionid=8429fb3ae210a2a0e28800b7f48d90f2"

        self.assertEqual("http://preis.de/traeger/index.php?",
                s._remove_session_ids(url))

    def test_that_with_uri_works(self):

        s = StripSessionIds(Settings())

        urls = ["http://preis.de/traeger/index.php?sid=8429fb3ae210a2a0e28800b7f48d90f2",
            "http://preis.de/traeger/index.php?jsessionid=8429fb3ae210a2a0e28800b7f48d90f2",
            "http://preis.de/traeger/index.php?phpsessid=8429fb3ae210a2a0e28800b7f48d90f2",
            "http://preis.de/traeger/index.php?aspsessionid=8429fb3ae210a2a0e28800b7f48d90f2",
        ]

        curi = CrawlUri()
        curi.optional_vars = { CURI_EXTRACTED_URLS: "\n".join(urls) }

        curi = s(curi)
        clean_urls = curi.optional_vars[CURI_EXTRACTED_URLS].split('\n')

        for u in clean_urls:
            self.assertEqual("http://preis.de/traeger/index.php?", u)

########NEW FILE########
__FILENAME__ = test_uri_unique_filter
#
# Copyright (c) 2011 Daniel Truemper truemped@googlemail.com
#
# test_uri_unique_filter.py 31-Jan-2011
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import unittest

from spyder.core.uri_uniq import UniqueUriFilter

class UniqueUriFilterTest(unittest.TestCase):

    def test_unknown_uris(self):

        unique_filter = UniqueUriFilter('sha1')

        self.assertFalse(unique_filter.is_known("http://www.google.de",
                    add_if_unknown=True))
        self.assertFalse(unique_filter.is_known("http://www.yahoo.com",
                    add_if_unknown=True))
        self.assertTrue(unique_filter.is_known("http://www.google.de"))
        self.assertTrue(unique_filter.is_known("http://www.yahoo.com"))


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_worker
#
# Copyright (c) 2011 Daniel Truemper truemped@googlemail.com
#
# test_worker.py 11-Jan-2011
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import logging
from logging import StreamHandler
import sys

import unittest

import time

import zmq
from zmq import Socket
from zmq.eventloop.ioloop import IOLoop
from zmq.eventloop.zmqstream import ZMQStream

from spyder.core.constants import ZMQ_SPYDER_MGMT_WORKER
from spyder.core.constants import ZMQ_SPYDER_MGMT_WORKER_QUIT
from spyder.core.constants import ZMQ_SPYDER_MGMT_WORKER_QUIT_ACK
from spyder.core.mgmt import ZmqMgmt
from spyder.core.worker import ZmqWorker, AsyncZmqWorker
from spyder.core.messages import DataMessage, MgmtMessage
from spyder.thrift.gen.ttypes import CrawlUri


class ZmqTornadoIntegrationTest(unittest.TestCase):

    def setUp(self):

        # create the io_loop
        self._io_loop = IOLoop.instance()

        # and the context
        self._ctx = zmq.Context(1)

        # setup the mgmt sockets
        self._setup_mgmt_sockets()

        # setup the data sockets
        self._setup_data_sockets()

        # setup the management interface
        self._mgmt = ZmqMgmt( self._mgmt_sockets['worker_sub'],
            self._mgmt_sockets['worker_pub'], io_loop=self._io_loop)
        self._mgmt.start()
        self._mgmt.add_callback(ZMQ_SPYDER_MGMT_WORKER, self.on_mgmt_end)

    def tearDown(self):
        # stop the mgmt
        self._mgmt.stop()

        # close all sockets
        for socket in self._mgmt_sockets.itervalues():
            socket.close()
        for socket in self._worker_sockets.itervalues():
            socket.close()

        # terminate the context
        self._ctx.term()

    def _setup_mgmt_sockets(self):

        self._mgmt_sockets = dict()

        # adress for the communication from master to worker(s)
        mgmt_master_worker = 'inproc://master/worker/coordination/'

        # connect the master with the worker
        # the master is a ZMQStream because we are sending msgs from the test
        sock = self._ctx.socket(zmq.PUB)
        sock.bind(mgmt_master_worker)
        self._mgmt_sockets['tmp1'] = sock
        self._mgmt_sockets['master_pub'] = ZMQStream(sock, self._io_loop)
        # the worker stream is created inside the ZmqMgmt class
        self._mgmt_sockets['worker_sub'] = self._ctx.socket(zmq.SUB)
        self._mgmt_sockets['worker_sub'].setsockopt(zmq.SUBSCRIBE, "")
        self._mgmt_sockets['worker_sub'].connect(mgmt_master_worker)

        # adress for the communication from worker(s) to master
        mgmt_worker_master = 'inproc://worker/master/coordination/'

        # connect the worker with the master
        self._mgmt_sockets['worker_pub'] = self._ctx.socket(zmq.PUB)
        self._mgmt_sockets['worker_pub'].bind(mgmt_worker_master)
        sock = self._ctx.socket(zmq.SUB)
        sock.setsockopt(zmq.SUBSCRIBE, "")
        sock.connect(mgmt_worker_master)
        self._mgmt_sockets['tmp2'] = sock
        self._mgmt_sockets['master_sub'] = ZMQStream(sock, self._io_loop)

    def _setup_data_sockets(self):

        self._worker_sockets = dict()

        # address for master -> worker communication
        data_master_worker = 'inproc://master/worker/pipeline/'

        sock = self._ctx.socket(zmq.PUSH)
        sock.bind(data_master_worker)
        self._worker_sockets['tmp3'] = sock
        self._worker_sockets['master_push'] = ZMQStream(sock, self._io_loop)
        self._worker_sockets['worker_pull'] = self._ctx.socket(zmq.PULL)
        self._worker_sockets['worker_pull'].connect(data_master_worker)

        # address for worker -> master communication
        data_worker_master = 'inproc://worker/master/pipeline/'

        self._worker_sockets['worker_pub'] = self._ctx.socket(zmq.PUB)
        self._worker_sockets['worker_pub'].bind(data_worker_master)
        sock = self._ctx.socket(zmq.SUB)
        sock.setsockopt(zmq.SUBSCRIBE, "")
        sock.connect(data_worker_master)
        self._worker_sockets['tmp4'] = sock
        self._worker_sockets['master_sub'] = ZMQStream(sock, self._io_loop)

    def on_mgmt_end(self, _msg):
        self._io_loop.stop()


class ZmqWorkerIntegrationTest(ZmqTornadoIntegrationTest):
    
    def echo_processing(self, crawl_uri):
        death = MgmtMessage(topic=ZMQ_SPYDER_MGMT_WORKER,
                data=ZMQ_SPYDER_MGMT_WORKER_QUIT)
        self._mgmt_sockets['master_pub'].send_multipart(death.serialize())
        return crawl_uri

    def test_that_stopping_worker_via_mgmt_works(self):

        worker = ZmqWorker( self._worker_sockets['worker_pull'],
            self._worker_sockets['worker_pub'],
            self._mgmt,
            self.echo_processing,
            StreamHandler(sys.stdout),
            logging.DEBUG,
            self._io_loop)

        worker.start()

        curi = CrawlUri(url="http://localhost")
        msg = DataMessage()
        msg.identity = "me"
        msg.curi = curi

        def assert_correct_data_answer(msg2):
            self.assertEqual(msg, DataMessage(msg2))

        self._worker_sockets['master_sub'].on_recv(assert_correct_data_answer)

        def assert_correct_mgmt_answer(msg3):
            self.assertEqual(ZMQ_SPYDER_MGMT_WORKER_QUIT_ACK, msg3.data)

        self._mgmt_sockets['master_sub'].on_recv(assert_correct_data_answer)

        self._worker_sockets['master_push'].send_multipart(msg.serialize())

        self._io_loop.start()


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_workerprocess_extractor
#
# Copyright (c) 2011 Daniel Truemper truemped@googlemail.com
#
# test_workerprocess_extractor.py 19-Jan-2011
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import sys
import logging
from logging import StreamHandler

import unittest

import zmq
from zmq.eventloop.ioloop import IOLoop
from zmq.eventloop.zmqstream import ZMQStream

from spyder.core.constants import CURI_OPTIONAL_TRUE
from spyder.core.constants import CURI_EXTRACTION_FINISHED
from spyder.core.constants import ZMQ_SPYDER_MGMT_WORKER
from spyder.core.constants import ZMQ_SPYDER_MGMT_WORKER_QUIT
from spyder.core.constants import ZMQ_SPYDER_MGMT_WORKER_QUIT_ACK
from spyder.core.messages import DataMessage, MgmtMessage
from spyder.core.mgmt import ZmqMgmt
from spyder.core.settings import Settings
from spyder.processor import limiter
from spyder.thrift.gen.ttypes import CrawlUri
from spyder import workerprocess


class ZmqTornadoIntegrationTest(unittest.TestCase):

    def setUp(self):

        # create the io_loop
        self._io_loop = IOLoop.instance()

        # and the context
        self._ctx = zmq.Context(1)

        self._settings = Settings()
        self._settings.ZEROMQ_MASTER_PUSH = 'inproc://spyder-zmq-master-push'
        self._settings.ZEROMQ_WORKER_PROC_FETCHER_PULL = \
            self._settings.ZEROMQ_MASTER_PUSH
        self._settings.ZEROMQ_MASTER_SUB = 'inproc://spyder-zmq-master-sub'
        self._settings.ZEROMQ_WORKER_PROC_EXTRACTOR_PUB = \
            self._settings.ZEROMQ_MASTER_SUB

        self._settings.ZEROMQ_MGMT_MASTER = 'inproc://spyder-zmq-mgmt-master'
        self._settings.ZEROMQ_MGMT_WORKER = 'inproc://spyder-zmq-mgmt-worker'

        # setup the mgmt sockets
        self._setup_mgmt_sockets()

        # setup the data sockets
        self._setup_data_servers()

        # setup the management interface
        self._mgmt = ZmqMgmt( self._mgmt_sockets['worker_sub'],
            self._mgmt_sockets['worker_pub'], io_loop=self._io_loop)
        self._mgmt.start()
        self._mgmt.add_callback(ZMQ_SPYDER_MGMT_WORKER, self.on_mgmt_end)

    def tearDown(self):
        # stop the mgmt
        self._mgmt.stop()

        # close all sockets
        for socket in self._mgmt_sockets.itervalues():
            socket.close()
        for socket in self._worker_sockets.itervalues():
            socket.close()

        # terminate the context
        self._ctx.term()

    def _setup_mgmt_sockets(self):

        self._mgmt_sockets = dict()

        # adress for the communication from master to worker(s)
        mgmt_master_worker = self._settings.ZEROMQ_MGMT_MASTER

        # connect the master with the worker
        # the master is a ZMQStream because we are sending msgs from the test
        sock = self._ctx.socket(zmq.PUB)
        sock.bind(mgmt_master_worker)
        self._mgmt_sockets['tmp1'] = sock
        self._mgmt_sockets['master_pub'] = ZMQStream(sock, self._io_loop)
        # the worker stream is created inside the ZmqMgmt class
        self._mgmt_sockets['worker_sub'] = self._ctx.socket(zmq.SUB)
        self._mgmt_sockets['worker_sub'].setsockopt(zmq.SUBSCRIBE, "")
        self._mgmt_sockets['worker_sub'].connect(mgmt_master_worker)

        # adress for the communication from worker(s) to master
        mgmt_worker_master = self._settings.ZEROMQ_MGMT_WORKER

        # connect the worker with the master
        self._mgmt_sockets['worker_pub'] = self._ctx.socket(zmq.PUB)
        self._mgmt_sockets['worker_pub'].bind(mgmt_worker_master)
        sock = self._ctx.socket(zmq.SUB)
        sock.setsockopt(zmq.SUBSCRIBE, "")
        sock.connect(mgmt_worker_master)
        self._mgmt_sockets['tmp2'] = sock
        self._mgmt_sockets['master_sub'] = ZMQStream(sock, self._io_loop)

    def _setup_data_servers(self):

        self._worker_sockets = dict()

        # address for master -> worker communication
        data_master_worker = self._settings.ZEROMQ_WORKER_PROC_EXTRACTOR_PULL

        sock = self._ctx.socket(zmq.PUSH)
        sock.bind(data_master_worker)
        self._worker_sockets['tmp3'] = sock
        self._worker_sockets['master_push'] = ZMQStream(sock, self._io_loop)

        # address for worker -> master communication
        data_worker_master = self._settings.ZEROMQ_WORKER_PROC_EXTRACTOR_PUB

        sock = self._ctx.socket(zmq.SUB)
        sock.setsockopt(zmq.SUBSCRIBE, "")
        sock.bind(data_worker_master)
        self._worker_sockets['tmp4'] = sock
        self._worker_sockets['master_sub'] = ZMQStream(sock, self._io_loop)

    def on_mgmt_end(self, _msg):
        self._io_loop.stop()


class WorkerExtractorTestCase(ZmqTornadoIntegrationTest):

    def test_that_creating_extractor_works(self):

        self._settings.SPYDER_EXTRACTOR_PIPELINE = ['spyder.processor.limiter.DefaultLimiter',]

        extractor = workerprocess.create_worker_extractor(self._settings,
                self._mgmt, self._ctx, StreamHandler(sys.stdout), self._io_loop)
        extractor.start()

        curi = CrawlUri(url="http://localhost:80/robots.txt",
                effective_url="http://127.0.0.1:%s/robots.txt",
                optional_vars=dict(),
                )
        msg = DataMessage()
        msg.identity = "me"
        msg.curi = curi

        def assert_expected_result_and_stop(raw_msg):
            msg2 = DataMessage(raw_msg)
            self.assertEqual(CURI_OPTIONAL_TRUE,
                    msg2.curi.optional_vars[CURI_EXTRACTION_FINISHED])
            death = MgmtMessage(topic=ZMQ_SPYDER_MGMT_WORKER,
                    data=ZMQ_SPYDER_MGMT_WORKER_QUIT)
            self._mgmt_sockets['master_pub'].send_multipart(death.serialize())

        self._worker_sockets['master_sub'].on_recv(assert_expected_result_and_stop)

        def assert_correct_mgmt_message(raw_msg):
            self.assertEqual(ZMQ_SPYDER_MGMT_WORKER_QUIT_ACK, raw_msg)

        self._mgmt_sockets['master_sub'].on_recv(assert_correct_mgmt_message)

        self._worker_sockets['master_push'].send_multipart(msg.serialize())

        self._io_loop.start()

        extractor._out_stream.close()
        extractor._outsocket.close()
        extractor._in_stream.close()
        extractor._insocket.close()


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_workerprocess_fetcher
#
# Copyright (c) 2011 Daniel Truemper truemped@googlemail.com
#
# test_workerprocess_fetcher.py 19-Jan-2011
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import logging
from logging import StreamHandler
import sys

import unittest
import time

import zmq
from zmq.eventloop.ioloop import IOLoop
from zmq.eventloop.zmqstream import ZMQStream

from spyder.core.constants import CURI_OPTIONAL_TRUE
from spyder.core.constants import CURI_EXTRACTION_FINISHED
from spyder.core.constants import ZMQ_SPYDER_MGMT_WORKER
from spyder.core.settings import Settings
from spyder.core.worker import AsyncZmqWorker
from spyder import workerprocess

from spyder.processor.fetcher import FetchProcessor

class WorkerExtractorTestCase(unittest.TestCase):

    def test_that_creating_fetcher_works(self):
        ctx = zmq.Context()
        io_loop = IOLoop.instance()

        def stop_looping(_msg):
            io_loop.stop()

        settings = Settings()

        master_push = ctx.socket(zmq.PUSH)
        master_push.bind(settings.ZEROMQ_MASTER_PUSH)

        fetcher = workerprocess.create_worker_fetcher(settings, {}, ctx,
                StreamHandler(sys.stdout), io_loop)

        self.assertTrue(isinstance(fetcher._processing, FetchProcessor))
        self.assertTrue(isinstance(fetcher, AsyncZmqWorker))

        fetcher._insocket.close()
        fetcher._outsocket.close()
        master_push.close()
        ctx.term()


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_workerprocess_mgmtintegration
#
# Copyright (c) 2011 Daniel Truemper truemped@googlemail.com
#
# test_workerprocess.py 18-Jan-2011
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import unittest
import time

import zmq
from zmq.eventloop.ioloop import IOLoop
from zmq.eventloop.zmqstream import ZMQStream

from spyder.core.constants import ZMQ_SPYDER_MGMT_WORKER
from spyder.core.constants import ZMQ_SPYDER_MGMT_WORKER_QUIT
from spyder.core.constants import ZMQ_SPYDER_MGMT_WORKER_QUIT_ACK
from spyder.core.messages import MgmtMessage
from spyder.core.settings import Settings
from spyder.processor import limiter
from spyder import workerprocess


class WorkerProcessTestCase(unittest.TestCase):

    def test_that_creating_mgmt_works(self):

        ctx = zmq.Context()
        io_loop = IOLoop.instance()

        def stop_looping(_msg):
            io_loop.stop()

        settings = Settings()
        settings.ZEROMQ_MASTER_PUSH = 'inproc://spyder-zmq-master-push'
        settings.ZEROMQ_WORKER_PROC_FETCHER_PULL = \
            settings.ZEROMQ_MASTER_PUSH
        settings.ZEROMQ_MASTER_SUB = 'inproc://spyder-zmq-master-sub'
        settings.ZEROMQ_WORKER_PROC_EXTRACTOR_PUB = \
            settings.ZEROMQ_MASTER_SUB

        settings.ZEROMQ_MGMT_MASTER = 'inproc://spyder-zmq-mgmt-master'
        settings.ZEROMQ_MGMT_WORKER = 'inproc://spyder-zmq-mgmt-worker'

        pubsocket = ctx.socket(zmq.PUB)
        pubsocket.bind(settings.ZEROMQ_MGMT_MASTER)
        pub_stream = ZMQStream(pubsocket, io_loop)

        subsocket = ctx.socket(zmq.SUB)
        subsocket.setsockopt(zmq.SUBSCRIBE, "")
        subsocket.bind(settings.ZEROMQ_MGMT_WORKER)
        sub_stream = ZMQStream(subsocket, io_loop)

        mgmt = workerprocess.create_worker_management(settings, ctx, io_loop)
        mgmt.add_callback(ZMQ_SPYDER_MGMT_WORKER, stop_looping)
        mgmt.start()

        def assert_quit_message(msg):
            self.assertEqual(ZMQ_SPYDER_MGMT_WORKER_QUIT_ACK, msg.data)

        sub_stream.on_recv(assert_quit_message)

        death = MgmtMessage(topic=ZMQ_SPYDER_MGMT_WORKER,
                data=ZMQ_SPYDER_MGMT_WORKER_QUIT)
        pub_stream.send_multipart(death.serialize())

        io_loop.start()

        mgmt._out_stream.close()
        mgmt._in_stream.close()
        mgmt._publisher.close()
        mgmt._subscriber.close()
        pub_stream.close()
        pubsocket.close()
        sub_stream.close()
        subsocket.close()
        ctx.term()


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_workerprocess_processing
#
# Copyright (c) 2011 Daniel Truemper truemped@googlemail.com
#
# test_workerprocess_processing.py 18-Jan-2011
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import unittest

from spyder.core.constants import CURI_OPTIONAL_TRUE
from spyder.core.constants import CURI_EXTRACTION_FINISHED
from spyder.core.settings import Settings
from spyder.processor import limiter
from spyder.thrift.gen.ttypes import CrawlUri
from spyder import workerprocess


class WorkerProcessingUnittest(unittest.TestCase):

    def test_that_creating_processing_function_works(self):
        settings = Settings()
        processors = settings.SPYDER_EXTRACTOR_PIPELINE
        processors.extend(settings.SPYDER_SCOPER_PIPELINE)
        processors.append('test_workerprocess')
        self.assertRaises(ValueError, workerprocess.create_processing_function,
                settings, processors)

        processors.pop()
        processors.append('test_workerprocess_unspec')
        self.assertRaises(ValueError, workerprocess.create_processing_function,
                settings, processors)

        processors.pop()
        processing = workerprocess.create_processing_function(settings,
                processors)

        curi = CrawlUri(optional_vars=dict())
        curi.effective_url = "http://127.0.0.1/robots.txt"
        curi2 = processing(curi)

        self.assertEqual(CURI_OPTIONAL_TRUE,
                curi2.optional_vars[CURI_EXTRACTION_FINISHED])

########NEW FILE########
__FILENAME__ = test_workerprocess_unspec
#
# Copyright (c) 2011 Daniel Truemper truemped@googlemail.com
#
# test_workerprocess_unspec.py 26-Jan-2011
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

def a_plugin_with_no_create_processor_method():
    pass

########NEW FILE########
