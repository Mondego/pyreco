__FILENAME__ = commands
"""
distutils commands for riak-python-client
"""

__all__ = ['create_bucket_types']

from distutils import log
from distutils.core import Command
from distutils.errors import DistutilsOptionError
from subprocess import CalledProcessError, Popen, PIPE

try:
    from subprocess import check_output
except ImportError:
    def check_output(*popenargs, **kwargs):
        """Run command with arguments and return its output as a byte string.

        If the exit code was non-zero it raises a CalledProcessError.  The
        CalledProcessError object will have the return code in the returncode
        attribute and output in the output attribute.

        The arguments are the same as for the Popen constructor.  Example:

        >>> check_output(["ls", "-l", "/dev/null"])
        'crw-rw-rw- 1 root root 1, 3 Oct 18  2007 /dev/null\n'

        The stdout argument is not allowed as it is used internally.
        To capture standard error in the result, use stderr=STDOUT.

        >>> import sys
        >>> check_output(["/bin/sh", "-c",
        ...               "ls -l non_existent_file ; exit 0"],
        ...              stderr=sys.stdout)
        'ls: non_existent_file: No such file or directory\n'
        """
        if 'stdout' in kwargs:
            raise ValueError('stdout argument not allowed, it will be '
                             'overridden.')
        process = Popen(stdout=PIPE, *popenargs, **kwargs)
        output, unused_err = process.communicate()
        retcode = process.poll()
        if retcode:
            cmd = kwargs.get("args")
            if cmd is None:
                cmd = popenargs[0]
            raise CalledProcessError(retcode, cmd, output=output)
        return output

try:
    import simplejson as json
except ImportError:
    import json


class create_bucket_types(Command):
    """
    Creates bucket-types appropriate for testing. By default this will create:

    * `pytest-maps` with ``{"datatype":"map"}``
    * `pytest-sets` with ``{"datatype":"set"}``
    * `pytest-counters` with ``{"datatype":"counter"}``
    * `pytest-consistent` with ``{"consistent":true}``
    * `pytest` with ``{"allow_mult":false}``
    """

    description = "create bucket-types used in integration tests"

    user_options = [
        ('riak-admin=', None, 'path to the riak-admin script')
    ]

    _props = {
        'pytest-maps': {'datatype': 'map'},
        'pytest-sets': {'datatype': 'set'},
        'pytest-counters': {'datatype': 'counter'},
        'pytest-consistent': {'consistent': True},
        'pytest': {'allow_mult': False}
    }

    def initialize_options(self):
        self.riak_admin = None

    def finalize_options(self):
        if self.riak_admin is None:
            raise DistutilsOptionError("riak-admin option not set")

    def run(self):
        if self._check_available():
            for name in self._props:
                self._create_and_activate_type(name, self._props[name])

    def check_output(self, *args, **kwargs):
        if self.dry_run:
            log.info(' '.join(args))
            return bytearray()
        else:
            return check_output(*args, **kwargs)

    def _check_available(self):
        try:
            self.check_btype_command("list")
            return True
        except CalledProcessError:
            log.error("Bucket types are not supported on this Riak node!")
            return False

    def _create_and_activate_type(self, name, props):
        # Check status of bucket-type
        exists = False
        active = False
        try:
            status = self.check_btype_command('status', name)
        except CalledProcessError as e:
            status = e.output

        exists = ('not an existing bucket type' not in status)
        active = ('is active' in status)

        if exists or active:
            log.info("Updating {!r} bucket-type with props {!r}".format(name,
                                                                        props))
            self.check_btype_command("update", name,
                                     json.dumps({'props': props},
                                                separators=(',', ':')))
        else:
            log.info("Creating {!r} bucket-type with props {!r}".format(name,
                                                                        props))
            self.check_btype_command("create", name,
                                     json.dumps({'props': props},
                                                separators=(',', ':')))

        if not active:
            log.info('Activating {!r} bucket-type'.format(name))
            self.check_btype_command("activate", name)

    def check_btype_command(self, *args):
        cmd = self._btype_command(*args)
        return self.check_output(cmd)

    def run_btype_command(self, *args):
        self.spawn(self._btype_command(*args))

    def _btype_command(self, *args):
        cmd = [self.riak_admin, "bucket-type"]
        cmd.extend(args)
        return cmd

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# Riak (Python binding) documentation build configuration file, created by
# sphinx-quickstart on Sun Nov 21 11:23:53 2010.
#
# This file is execfile()d with the current directory set to its
# containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys
import os

on_rtd = os.environ.get('READTHEDOCS', None) == 'True'
if not on_rtd:
    import sphinx_rtd_theme
    html_theme = 'sphinx_rtd_theme'
    html_theme_path = [sphinx_rtd_theme.get_html_theme_path()]

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
sys.path.insert(0, os.path.abspath('..'))

from version import get_version
# -- General configuration ----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = ['sphinx.ext.autodoc']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'Riak Python Client'
copyright = u'2010-2013, Basho Technologies'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The full version, including alpha/beta/rc tags.
release = get_version()

# The short X.Y version.
version = '.'.join(release.split('.')[0:3])

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

# The reST default role (used for this markup: `text`) to use for all
# documents.
# default_role = None

# If true, '()' will be appended to :func: etc. cross-reference text.
#add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
#add_module_names = True

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
#show_authors = False

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'tango'

# A list of ignored prefixes for module index sorting.
#modindex_common_prefix = []


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
# html_theme = 'default'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.

# Add any paths that contain custom themes here, relative to this
# directory.

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
htmlhelp_basename = 'RiakPythonbindingdoc'


# -- Options for LaTeX output ------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author,
#  documentclass [howto/manual]).
# latex_documents = [
#   ('index', 'RiakPythonbinding.tex', u'Riak (Python binding) Documentation',
#    u'Daniel Lindsley', 'manual'),
# ]

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


# -- Options for manual page output ------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
# man_pages = [
#     ('index', 'riakpythonbinding', u'Riak (Python binding) Documentation',
#      [u'Daniel Lindsley'], 1)
# ]


# -- Options for Epub output -------------------------------------------------

# Bibliographic Dublin Core info.
# epub_title = u'Riak (Python binding)'
# epub_author = u'Daniel Lindsley'
# epub_publisher = u'Daniel Lindsley'
# epub_copyright = u'2010, Daniel Lindsley'

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

# Autodoc settings
autodoc_default_flags = ['no-undoc-members']
autodoc_member_order = 'groupwise'
autoclass_content = 'both'

########NEW FILE########
__FILENAME__ = benchmark
"""
Copyright 2013 Basho Technologies, Inc.

This file is provided to you under the Apache License,
Version 2.0 (the "License"); you may not use this file
except in compliance with the License.  You may obtain
a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on an
"AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
KIND, either express or implied.  See the License for the
specific language governing permissions and limitations
under the License.
"""

import os
import gc

__all__ = ['measure', 'measure_with_rehearsal']


def measure_with_rehearsal():
    """
    Runs a benchmark when used as an iterator, injecting a garbage
    collection between iterations. Example::

        for b in riak.benchmark.measure_with_rehearsal():
            with b.report("pow"):
                for _ in range(10000):
                    math.pow(2,10000)
            with b.report("factorial"):
                for i in range(100):
                    math.factorial(i)
    """
    return Benchmark(True)


def measure():
    """
    Runs a benchmark once when used as a context manager. Example::

        with riak.benchmark.measure() as b:
            with b.report("pow"):
                for _ in range(10000):
                    math.pow(2,10000)
            with b.report("factorial"):
                for i in range(100):
                    math.factorial(i)
    """
    return Benchmark()


class Benchmark(object):
    """
    A benchmarking run, which may consist of multiple steps. See
    measure_with_rehearsal() and measure() for examples.
    """
    def __init__(self, rehearse=False):
        """
        Creates a new benchmark reporter.

        :param rehearse: whether to run twice to take counter the effects
           of garbage collection
        :type rehearse: boolean
        """
        self.rehearse = rehearse
        if rehearse:
            self.count = 2
        else:
            self.count = 1
        self._report = None

    def __enter__(self):
        if self.rehearse:
            raise ValueError("measure_with_rehearsal() cannot be used in with "
                             "statements, use measure() or the for..in "
                             "statement")
        print_header()
        self._report = BenchmarkReport()
        self._report.__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._report:
            return self._report.__exit__(exc_type, exc_val, exc_tb)
        else:
            print
            return True

    def __iter__(self):
        return self

    def next(self):
        """
        Runs the next iteration of the benchmark.
        """
        if self.count == 0:
            raise StopIteration
        elif self.count > 1:
            print_rehearsal_header()
        else:
            if self.rehearse:
                gc.collect()
                print ("-" * 59)
                print
            print_header()

        self.count -= 1
        return self

    def report(self, name):
        """
        Returns a report for the current step of the benchmark.
        """
        self._report = None
        return BenchmarkReport(name)


def print_rehearsal_header():
    """
    Prints the header for the rehearsal phase of a benchmark.
    """
    print
    print "Rehearsal -------------------------------------------------"


def print_report(label, user, system, real):
    """
    Prints the report of one step of a benchmark.
    """
    print "{:<12s} {:12f} {:12f} ( {:12f} )".format(label, user, system, real)


def print_header():
    """
    Prints the header for the normal phase of a benchmark.
    """
    print "{:<12s} {:<12s} {:<12s} ( {:<12s} )"\
        .format('', 'user', 'system', 'real')


class BenchmarkReport(object):
    """
    A labeled step in a benchmark. Acts as a context-manager, printing
    its timing results when the context exits.
    """
    def __init__(self, name='benchmark'):
        self.name = name
        self.start = None

    def __enter__(self):
        self.start = os.times()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if not exc_type:
            user1, system1, _, _, real1 = self.start
            user2, system2, _, _, real2 = os.times()
            print_report(self.name, user2 - user1, system2 - system1,
                         real2 - real1)
        elif exc_type is KeyboardInterrupt:
            return False
        else:
            print "EXCEPTION! %r" % ((exc_type, exc_val, exc_tb),)
        return True

########NEW FILE########
__FILENAME__ = bucket
"""
Copyright 2010 Rusty Klophaus <rusty@basho.com>
Copyright 2010 Justin Sheehy <justin@basho.com>
Copyright 2009 Jay Baird <jay@mochimedia.com>

This file is provided to you under the Apache License,
Version 2.0 (the "License"); you may not use this file
except in compliance with the License.  You may obtain
a copy of the License at

  http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on an
"AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
KIND, either express or implied.  See the License for the
specific language governing permissions and limitations
under the License.
"""
import mimetypes
from riak.util import deprecateQuorumAccessors, deprecated


def deprecateBucketQuorumAccessors(klass):
    return deprecateQuorumAccessors(klass, parent='_client')


def bucket_property(name, doc=None):
    def _prop_getter(self):
        return self.get_property(name)

    def _prop_setter(self, value):
        return self.set_property(name, value)

    return property(_prop_getter, _prop_setter, doc=doc)


@deprecateBucketQuorumAccessors
class RiakBucket(object):
    """
    The ``RiakBucket`` object allows you to access and change information
    about a Riak bucket, and provides methods to create or retrieve
    objects within the bucket.
    """

    def __init__(self, client, name, bucket_type):
        """
        Returns a new ``RiakBucket`` instance.

        :param client: A :class:`RiakClient <riak.client.RiakClient>` instance
        :type client: :class:`RiakClient <riak.client.RiakClient>`
        :param name: The bucket name
        :type name: string
        :param bucket_type: The parent bucket type of this bucket
        :type bucket_type: :class:`BucketType`
        """
        try:
            if isinstance(name, basestring):
                name = name.encode('ascii')
            else:
                raise TypeError('Bucket name must be a string')
        except UnicodeError:
            raise TypeError('Unicode bucket names are not supported.')

        if not isinstance(bucket_type, BucketType):
            raise TypeError('Parent bucket type must be a BucketType instance')

        self._client = client
        self.name = name
        self.bucket_type = bucket_type
        self._encoders = {}
        self._decoders = {}
        self._resolver = None

    def __hash__(self):
        return hash((self.bucket_type.name, self.name, self._client))

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return hash(self) == hash(other)
        else:
            return False

    def __ne__(self, other):
        if isinstance(other, self.__class__):
            return hash(self) != hash(other)
        else:
            return True

    def get_encoder(self, content_type):
        """
        Get the encoding function for the provided content type for
        this bucket.

        :param content_type: the requested media type
        :type content_type: str
        :param content_type: Content type requested
        """
        if content_type in self._encoders:
            return self._encoders[content_type]
        else:
            return self._client.get_encoder(content_type)

    def set_encoder(self, content_type, encoder):
        """
        Set the encoding function for the provided content type for
        this bucket.

        :param content_type: the requested media type
        :type content_type: str
        :param encoder: an encoding function, takes a single object
            argument and returns a string data as single argument.
        :type encoder: function
        """
        self._encoders[content_type] = encoder
        return self

    def get_decoder(self, content_type):
        """
        Get the decoding function for the provided content type for
        this bucket.

        :param content_type: the requested media type
        :type content_type: str
        :rtype: function
        """
        if content_type in self._decoders:
            return self._decoders[content_type]
        else:
            return self._client.get_decoder(content_type)

    def set_decoder(self, content_type, decoder):
        """
        Set the decoding function for the provided content type for
        this bucket.

        :param content_type: the requested media type
        :type content_type: str
        :param decoder: a decoding function, takes a string and
            returns a Python type
        :type decoder: function
        """
        self._decoders[content_type] = decoder
        return self

    def new(self, key=None, data=None, content_type='application/json',
            encoded_data=None):
        """
        Create a new :class:`RiakObject <riak.riak_object.RiakObject>`
        that will be stored as JSON. A shortcut for manually
        instantiating a :class:`RiakObject
        <riak.riak_object.RiakObject>`.

        :param key: Name of the key. Leaving this to be None (default)
                    will make Riak generate the key on store.
        :type key: string
        :param data: The data to store.
        :type data: object
        :rtype: :class:`RiakObject <riak.riak_object.RiakObject>`
        """
        try:
            if isinstance(data, basestring):
                data = data.encode('ascii')
        except UnicodeError:
            raise TypeError('Unicode data values are not supported.')

        obj = RiakObject(self._client, self, key)
        obj.content_type = content_type
        if data is not None:
            obj.data = data
        if encoded_data is not None:
            obj.encoded_data = encoded_data
        return obj

    def new_binary(self, key=None, data=None,
                   content_type='application/octet-stream'):
        """
        Create a new :class:`RiakObject <riak.riak_object.RiakObject>`
        that will be stored as plain text/binary. A shortcut for
        manually instantiating a :class:`RiakObject
        <riak.riak_object.RiakObject>`.

        .. deprecated:: 2.0.0
           Use :meth:`new` instead.

        :param key: Name of the key.
        :type key: string
        :param data: The data to store.
        :type data: object
        :param content_type: The content type of the object.
        :type content_type: string
        :rtype: :class:`RiakObject <riak.riak_object.RiakObject>`
        """
        deprecated('RiakBucket.new_binary is deprecated, '
                   'use RiakBucket.new with the encoded_data '
                   'param instead of data')
        return self.new(key, encoded_data=data, content_type=content_type)

    def get(self, key, r=None, pr=None, timeout=None):
        """
        Retrieve an object from Riak.

        :param key: Name of the key.
        :type key: string
        :param r: R-Value of the request (defaults to bucket's R)
        :type r: integer
        :param pr: PR-Value of the request (defaults to bucket's PR)
        :type pr: integer
        :param timeout: a timeout value in milliseconds
        :type timeout: int
        :rtype: :class:`RiakObject <riak.riak_object.RiakObject>`
        """
        obj = RiakObject(self._client, self, key)
        return obj.reload(r=r, pr=pr, timeout=timeout)

    def get_binary(self, key, r=None, pr=None, timeout=None):
        """
        Retrieve a binary/string object from Riak.

        .. deprecated:: 2.0.0
           Use :meth:`get` instead.

        :param key: Name of the key.
        :type key: string
        :param r: R-Value of the request (defaults to bucket's R)
        :type r: integer
        :param pr: PR-Value of the request (defaults to bucket's PR)
        :type pr: integer
        :param timeout: a timeout value in milliseconds
        :type timeout: int
        :rtype: :class:`RiakObject <riak.riak_object.RiakObject>`
        """
        deprecated('RiakBucket.get_binary is deprecated, '
                   'use RiakBucket.get')
        return self.get(key, r=r, pr=pr, timeout=timeout)

    def multiget(self, keys, r=None, pr=None):
        """
        Retrieves a list of keys belonging to this bucket in parallel.

        :param keys: the keys to fetch
        :type keys: list
        :param r: R-Value for the requests (defaults to bucket's R)
        :type r: integer
        :param pr: PR-Value for the requests (defaults to bucket's PR)
        :type pr: integer
        :rtype: list of :class:`RiakObject <riak.riak_object.RiakObject>`
        """
        bkeys = [(self.name, key) for key in keys]
        return self._client.multiget(bkeys, r=r, pr=pr)

    def _get_resolver(self):
        if callable(self._resolver):
            return self._resolver
        elif self._resolver is None:
            return self._client.resolver
        else:
            raise TypeError("resolver is not a function")

    def _set_resolver(self, value):
        if value is None or callable(value):
            self._resolver = value
        else:
            raise TypeError("resolver is not a function")

    resolver = property(_get_resolver, _set_resolver,
                        doc="""The sibling-resolution function for this
                           bucket. If the resolver is not set, the
                           client's resolver will be used.""")

    n_val = bucket_property('n_val', doc="""
    N-value for this bucket, which is the number of replicas
    that will be written of each object in the bucket.

    .. warning:: Set this once before you write any data to the
        bucket, and never change it again, otherwise unpredictable
        things could happen. This should only be used if you know what
        you are doing.
    """)

    allow_mult = bucket_property('allow_mult', doc="""
    If set to True, then writes with conflicting data will be stored
    and returned to the client.

    :type bool: boolean
    """)

    r = bucket_property('r', doc="""
    The default 'read' quorum for this bucket (how many replicas must
    reply for a successful read). This should be an integer less than
    the 'n_val' property, or a string of 'one', 'quorum', 'all', or
    'default'""")

    pr = bucket_property('pr', doc="""
    The default 'primary read' quorum for this bucket (how many
    primary replicas are required for a successful read). This should
    be an integer less than the 'n_val' property, or a string of
    'one', 'quorum', 'all', or 'default'""")

    rw = bucket_property('rw', doc="""
    The default 'read' and 'write' quorum for this bucket (equivalent
    to 'r' and 'w' but for deletes). This should be an integer less
    than the 'n_val' property, or a string of 'one', 'quorum', 'all',
    or 'default'""")

    w = bucket_property('w', doc="""
    The default 'write' quorum for this bucket (how many replicas must
    acknowledge receipt of a write). This should be an integer less
    than the 'n_val' property, or a string of 'one', 'quorum', 'all',
    or 'default'""")

    dw = bucket_property('dw', doc="""
    The default 'durable write' quorum for this bucket (how many
    replicas must commit the write). This should be an integer less
    than the 'n_val' property, or a string of 'one', 'quorum', 'all',
    or 'default'""")

    pw = bucket_property('pw', doc="""
    The default 'primary write' quorum for this bucket (how many
    primary replicas are required for a successful write). This should
    be an integer less than the 'n_val' property, or a string of
    'one', 'quorum', 'all', or 'default'""")

    def set_property(self, key, value):
        """
        Set a bucket property.

        :param key: Property to set.
        :type key: string
        :param value: Property value.
        :type value: mixed
        """
        return self.set_properties({key: value})

    def get_property(self, key):
        """
        Retrieve a bucket property.

        :param key: The property to retrieve.
        :type key: string
        :rtype: mixed
        """
        return self.get_properties()[key]

    def set_properties(self, props):
        """
        Set multiple bucket properties in one call.

        :param props: A dictionary of properties
        :type props: dict
        """
        self._client.set_bucket_props(self, props)

    def get_properties(self):
        """
        Retrieve a dict of all bucket properties.

        :rtype: dict
        """
        return self._client.get_bucket_props(self)

    def clear_properties(self):
        """
        Reset all bucket properties to their defaults.
        """
        return self._client.clear_bucket_props(self)

    def get_keys(self):
        """
        Return all keys within the bucket.

        :rtype: list of keys
        """
        return self._client.get_keys(self)

    def stream_keys(self):
        """
        Streams all keys within the bucket through an iterator.

        :rtype: iterator
        """
        return self._client.stream_keys(self)

    def new_from_file(self, key, filename):
        """
        Create a new Riak object in the bucket, using the contents of
        the specified file. This is a shortcut for :meth:`new`, where the
        ``encoded_data`` and ``content_type`` are set for you.

        :param key: the key of the new object
        :type key: string
        :param filename: the file to read the contents from
        :type filename: string
        :rtype: :class:`RiakObject <riak.riak_object.RiakObject>`
        """
        binary_data = open(filename, "rb").read()
        mimetype, encoding = mimetypes.guess_type(filename)
        if encoding:
            binary_data = bytearray(binary_data, encoding)
        else:
            binary_data = bytearray(binary_data)
        if not mimetype:
            mimetype = 'application/octet-stream'
        return self.new(key, encoded_data=binary_data, content_type=mimetype)

    def new_binary_from_file(self, key, filename):
        """
        Create a new Riak object in the bucket, using the contents of
        the specified file. This is a shortcut for :meth:`new`, where the
        ``encoded_data`` and ``content_type`` are set for you.

        .. deprecated:: 2.0.0
           Use :meth:`new_from_file` instead.

        :param key: the key of the new object
        :type key: string
        :param filename: the file to read the contents from
        :type filename: string
        :rtype: :class:`RiakObject <riak.riak_object.RiakObject>`
        """
        deprecated('RiakBucket.new_binary_from_file is deprecated, use '
                   'RiakBucket.new_from_file')
        return self.new_from_file(key, filename)

    def search_enabled(self):
        """
        Returns True if search indexing is enabled for this
        bucket.
        """
        return self.get_properties().get('search', False)

    def enable_search(self):
        """
        Enable search indexing for this bucket.
        """
        if not self.search_enabled():
            self.set_property('search', True)
        return True

    def disable_search(self):
        """
        Disable search indexing for this bucket.
        """
        if self.search_enabled():
            self.set_property('search', False)
        return True

    def search(self, query, **params):
        """
        Queries a search index over objects in this bucket/index. See
        :meth:`RiakClient.fulltext_search()
        <riak.client.RiakClient.fulltext_search>` for more details.
        """
        return self._client.fulltext_search(self.name, query, **params)

    def get_index(self, index, startkey, endkey=None, return_terms=None,
                  max_results=None, continuation=None, timeout=None,
                  term_regex=None):
        """
        Queries a secondary index over objects in this bucket,
        returning keys or index/key pairs. See
        :meth:`RiakClient.get_index()
        <riak.client.RiakClient.get_index>` for more details.
        """
        return self._client.get_index(self, index, startkey, endkey,
                                      return_terms=return_terms,
                                      max_results=max_results,
                                      continuation=continuation,
                                      timeout=timeout, term_regex=term_regex)

    def stream_index(self, index, startkey, endkey=None, return_terms=None,
                     max_results=None, continuation=None, timeout=None,
                     term_regex=None):
        """
        Queries a secondary index over objects in this bucket,
        streaming keys or index/key pairs via an iterator. See
        :meth:`RiakClient.stream_index()
        <riak.client.RiakClient.stream_index>` for more details.
        """
        return self._client.stream_index(self, index, startkey, endkey,
                                         return_terms=return_terms,
                                         max_results=max_results,
                                         continuation=continuation,
                                         timeout=timeout,
                                         term_regex=term_regex)

    def delete(self, key, **kwargs):
        """Deletes an object from riak. Short hand for
        bucket.new(key).delete(). See :meth:`RiakClient.delete()
        <riak.client.RiakClient.delete>` for options.

        :param key: The key for the object
        :type key: string
        :rtype: RiakObject
        """
        return self.new(key).delete(**kwargs)

    def get_counter(self, key, **kwargs):
        """
        Gets the value of a counter stored in this bucket. See
        :meth:`RiakClient.get_counter()
        <riak.client.RiakClient.get_counter>` for options.

        :param key: the key of the counter
        :type key: string
        :rtype: int
        """
        return self._client.get_counter(self, key, **kwargs)

    def update_counter(self, key, value, **kwargs):
        """
        Updates the value of a counter stored in this bucket. Positive
        values increment the counter, negative values decrement. See
        :meth:`RiakClient.update_counter()
        <riak.client.RiakClient.update_counter>` for options.


        :param key: the key of the counter
        :type key: string
        :param value: the amount to increment or decrement
        :type value: integer
        """
        return self._client.update_counter(self, key, value, **kwargs)

    increment_counter = update_counter

    def __str__(self):
        if self.bucket_type.is_default():
            return '<RiakBucket {0!r}>'.format(self.name)
        else:
            return '<RiakBucket {0!r}/{1!r}>'.format(self.bucket_type.name,
                                                     self.name)

    __repr__ = __str__


class BucketType(object):
    """
    The ``BucketType`` object allows you to access and change
    properties on a Riak bucket type and access buckets within its
    namespace.
    """
    def __init__(self, client, name):
        """
        Returns a new ``BucketType`` instance.

        :param client: A :class:`RiakClient <riak.client.RiakClient>` instance
        :type client: :class:`RiakClient <riak.client.RiakClient>`
        :param name: The bucket-type's name
        :type name: string
        """
        self._client = client
        self.name = name

    def is_default(self):
        """
        Whether this bucket type is the default type, or a
        user-defined type.

        :rtype: bool
        """
        return self.name == 'default'

    def get_property(self, key, value):
        """
        Retrieve a bucket-type property.

        :param key: The property to retrieve.
        :type key: string
        :rtype: mixed
        """
        return self.get_properties()[key]

    def set_property(self, key, value):
        """
        Set a bucket-type property.

        :param key: Property to set.
        :type key: string
        :param value: Property value.
        :type value: mixed
        """
        return self.set_properties({key: value})

    def get_properties(self):
        """
        Retrieve a dict of all bucket-type properties.

        :rtype: dict
        """
        return self._client.get_bucket_type_props(self)

    def set_properties(self, props):
        """
        Set multiple bucket-type properties in one call.

        :param props: A dictionary of properties
        :type props: dict
        """
        self._client.set_bucket_type_props(self, props)

    def bucket(self, name):
        """
        Gets a bucket that belongs to this bucket-type.

        :param name: the bucket name
        :type name: str
        :rtype: :class:`RiakBucket`
        """
        return self._client.bucket(name, self)

    def get_buckets(self, timeout=None):
        """
        Get the list of buckets under this bucket-type as
        :class:`RiakBucket <riak.bucket.RiakBucket>` instances.

        .. warning:: Do not use this in production, as it requires
           traversing through all keys stored in a cluster.

        .. note:: This request is automatically retried :attr:`retries`
           times if it fails due to network error.

        :param timeout: a timeout value in milliseconds
        :type timeout: int
        :rtype: list of :class:`RiakBucket <riak.bucket.RiakBucket>` instances
        """
        return self._client.get_buckets(bucket_type=self, timeout=timeout)

    def stream_buckets(self, timeout=None):
        """
        Streams the list of buckets under this bucket-type. This is a
        generator method that should be iterated over.

        .. warning:: Do not use this in production, as it requires
           traversing through all keys stored in a cluster.

        :param timeout: a timeout value in milliseconds
        :type timeout: int
        :rtype: iterator that yields lists of :class:`RiakBucket
             <riak.bucket.RiakBucket>` instances
        """
        return self._client.stream_buckets(bucket_type=self, timeout=timeout)

    def __str__(self):
        return "<BucketType {0!r}>".format(self.name)

    __repr__ = __str__

    def __hash__(self):
        return hash((self.name, self._client))

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return hash(self) == hash(other)
        else:
            return False

    def __ne__(self, other):
        if isinstance(other, self.__class__):
            return hash(self) != hash(other)
        else:
            return True


from riak_object import RiakObject

########NEW FILE########
__FILENAME__ = index_page
"""
Copyright 2013 Basho Technologies, Inc.

This file is provided to you under the Apache License,
Version 2.0 (the "License"); you may not use this file
except in compliance with the License.  You may obtain
a copy of the License at

  http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on an
"AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
KIND, either express or implied.  See the License for the
specific language governing permissions and limitations
under the License.
"""

from collections import namedtuple, Sequence


CONTINUATION = namedtuple('Continuation', ['c'])


class IndexPage(Sequence, object):
    """
    Encapsulates a single page of results from a secondary index
    query, with the ability to iterate over results (if not streamed),
    capture the page marker (continuation), and automatically fetch
    the next page.

    While users will interact with this object, it will be created
    automatically by the client and does not need to be instantiated
    elsewhere.
    """
    def __init__(self, client, bucket, index, startkey, endkey, return_terms,
                 max_results, term_regex):
        self.client = client
        self.bucket = bucket
        self.index = index
        self.startkey = startkey
        self.endkey = endkey
        self.return_terms = return_terms
        self.max_results = max_results
        self.results = None
        self.stream = False
        self.term_regex = term_regex

    continuation = None
    """
    The opaque page marker that is used when fetching the next chunk
    of results. The user can simply call :meth:`next_page` to do so,
    or pass this to the :meth:`~riak.client.RiakClient.get_index`
    method using the ``continuation`` option.
    """

    def __iter__(self):
        """
        Emulates the iterator interface. When streaming, this means
        delegating to the stream, otherwise iterating over the
        existing result set.
        """
        if self.results is None:
            raise ValueError("No index results to iterate")

        try:
            for result in self.results:
                if self.stream and isinstance(result, CONTINUATION):
                    self.continuation = result.c
                else:
                    yield self._inject_term(result)
        finally:
            if self.stream:
                self.results.close()

    def __len__(self):
        """
        Returns the length of the captured results.
        """
        if self._has_results():
            return len(self.results)
        else:
            raise ValueError("Streamed index page has no length")

    def __getitem__(self, index):
        """
        Fetches an item by index from the captured results.
        """
        if self._has_results():
            return self.results[index]
        else:
            raise ValueError("Streamed index page has no entries")

    def __eq__(self, other):
        """
        An IndexPage can pretend to be equal to a list when it has
        captured results by simply comparing the internal results to
        the passed list. Otherwise the other object needs to be an
        equivalent IndexPage.
        """
        if isinstance(other, list) and self._has_results():
            return self._inject_term(self.results) == other
        elif isinstance(other, IndexPage):
            return other.__dict__ == self.__dict__
        else:
            return False

    def __ne__(self, other):
        """
        Converse of __eq__.
        """
        return not self.__eq__(other)

    def has_next_page(self):
        """
        Whether there is another page available, i.e. the response
        included a continuation.
        """
        return self.continuation is not None

    def next_page(self, timeout=None, stream=None):
        """
        Fetches the next page using the same parameters as the
        original query.

        Note that if streaming was used before, it will be used again
        unless overridden.

        :param stream: whether to enable streaming. `True` enables,
            `False` disables, `None` uses previous value.
        :type stream: boolean
        :param timeout: a timeout value in milliseconds, or 'infinity'
        :type timeout: int
        """
        if not self.continuation:
            raise ValueError("Cannot get next index page, no continuation")

        if stream is not None:
            self.stream = stream

        args = {'bucket': self.bucket,
                'index': self.index,
                'startkey': self.startkey,
                'endkey': self.endkey,
                'return_terms': self.return_terms,
                'max_results': self.max_results,
                'continuation': self.continuation,
                'timeout': timeout,
                'term_regex': self.term_regex}

        if self.stream:
            return self.client.stream_index(**args)
        else:
            return self.client.get_index(**args)

    def _has_results(self):
        """
        When not streaming, have results been assigned?
        """
        return not (self.stream or self.results is None)

    def _should_inject_term(self, term):
        """
        The index term should be injected when using an equality query
        and the return terms option. If the term is already a tuple,
        it can be skipped.
        """
        return self.return_terms and not self.endkey

    def _inject_term(self, result):
        """
        Upgrades a result (streamed or not) to include the index term
        when an equality query is used with return_terms.
        """
        if self._should_inject_term(result):
            if type(result) is list:
                return [(self.startkey, r) for r in result]
            else:
                return (self.startkey, result)
        else:
            return result

    def __repr__(self):
        return "<{!s} {!r}>".format(self.__class__.__name__, self.__dict__)

########NEW FILE########
__FILENAME__ = multiget
"""
Copyright 2013 Basho Technologies, Inc.

This file is provided to you under the Apache License,
Version 2.0 (the "License"); you may not use this file
except in compliance with the License.  You may obtain
a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on an
"AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
KIND, either express or implied.  See the License for the
specific language governing permissions and limitations
under the License.
"""

from collections import namedtuple
from Queue import Queue
from threading import Thread, Lock, Event
from multiprocessing import cpu_count

__all__ = ['multiget']


try:
    #: The default size of the worker pool, either based on the number
    #: of CPUS or defaulting to 6
    POOL_SIZE = cpu_count()
except NotImplementedError:
    # Make an educated guess
    POOL_SIZE = 6

#: A :class:`namedtuple` for tasks that are fed to workers in the
#: multiget pool.
Task = namedtuple('Task', ['client', 'outq', 'bucket', 'key', 'options'])


class MultiGetPool(object):
    """
    Encapsulates a pool of fetcher threads. These threads can be used
    across many multi-get requests.
    """

    def __init__(self, size=POOL_SIZE):
        """
        :param size: the desired size of the worker pool
        :type size: int
        """

        self._inq = Queue()
        self._size = size
        self._started = Event()
        self._stop = Event()
        self._lock = Lock()
        self._workers = []

    def enq(self, task):
        """
        Enqueues a fetch task to the pool of workers. This will raise
        a RuntimeError if the pool is stopped or in the process of
        stopping.

        :param task: the Task object
        :type task: Task
        """
        if not self._stop.is_set():
            self._inq.put(task)
        else:
            raise RuntimeError("Attempted to enqueue a fetch operation while "
                               "multi-get pool was shutdown!")

    def start(self):
        """
        Starts the worker threads if they are not already started.
        This method is thread-safe and will be called automatically
        when executing a MultiGet operation.
        """
        # Check whether we are already started, skip if we are.
        if not self._started.is_set():
            # If we are not started, try to capture the lock.
            if self._lock.acquire(False):
                # If we got the lock, go ahead and start the worker
                # threads, set the started flag, and release the lock.
                for i in range(self._size):
                    name = "riak.client.multiget-worker-{0}".format(i)
                    worker = Thread(target=self._fetcher, name=name)
                    worker.daemon = True
                    worker.start()
                    self._workers.append(worker)
                self._started.set()
                self._lock.release()
            else:
                # We didn't get the lock, so someone else is already
                # starting the worker threads. Wait until they have
                # signaled that the threads are started.
                self._started.wait()

    def stop(self):
        """
        Signals the worker threads to exit and waits on them.
        """
        self._stop.set()
        for worker in self._workers:
            worker.join()

    def stopped(self):
        """
        Detects whether this pool has been stopped.
        """
        return self._stop.is_set()

    def __del__(self):
        # Ensure that all work in the queue is processed before
        # shutting down.
        self.stop()

    def _fetcher(self):
        """
        The body of the multi-get worker. Loops until
        :meth:`_should_quit` returns ``True``, taking tasks off the
        input queue, fetching the object, and putting them on the
        output queue.
        """
        while not self._should_quit():
            task = self._inq.get()
            try:
                obj = task.client.bucket(task.bucket).get(task.key,
                                                          **task.options)
                task.outq.put(obj)
            except KeyboardInterrupt:
                raise
            except Exception as err:
                task.outq.put((task.bucket, task.key, err), )
            finally:
                self._inq.task_done()

    def _should_quit(self):
        """
        Worker threads should exit when the stop flag is set and the
        input queue is empty. Once the stop flag is set, new enqueues
        are disallowed, meaning that the workers can safely drain the
        queue before exiting.

        :rtype: bool
        """
        return self.stopped() and self._inq.empty()


#: The default pool is automatically created and stored in this constant.
RIAK_MULTIGET_POOL = MultiGetPool()


def multiget(client, keys, **options):
    """
    Executes a parallel-fetch across multiple threads. Returns a list
    containing :class:`~riak.riak_object.RiakObject` instances, or
    3-tuples of bucket, key, and the exception raised.

    :param client: the client to use
    :type client: :class:`~riak.client.RiakClient`
    :param keys: the bucket/key pairs to fetch in parallel
    :type keys: list of two-tuples -- bucket/key pairs
    :rtype: list
    """
    outq = Queue()

    RIAK_MULTIGET_POOL.start()
    for bucket, key in keys:
        task = Task(client, outq, bucket, key, options)
        RIAK_MULTIGET_POOL.enq(task)

    results = []
    for _ in range(len(keys)):
        if RIAK_MULTIGET_POOL.stopped():
            raise RuntimeError("Multi-get operation interrupted by pool "
                               "stopping!")
        results.append(outq.get())
        outq.task_done()

    return results

if __name__ == '__main__':
    # Run a benchmark!
    from riak import RiakClient
    import riak.benchmark as benchmark
    client = RiakClient(protocol='pbc')
    bkeys = [('multiget', str(key)) for key in xrange(10000)]

    data = open(__file__).read()

    print "Benchmarking multiget:"
    print "      CPUs: {0}".format(cpu_count())
    print "   Threads: {0}".format(POOL_SIZE)
    print "      Keys: {0}".format(len(bkeys))
    print

    with benchmark.measure() as b:
        with b.report('populate'):
            for bucket, key in bkeys:
                client.bucket(bucket).new(key, encoded_data=data,
                                          content_type='text/plain'
                                          ).store()
    for b in benchmark.measure_with_rehearsal():
        client.protocol = 'http'
        with b.report('http seq'):
            for bucket, key in bkeys:
                client.bucket(bucket).get(key)

        with b.report('http multi'):
            multiget(client, bkeys)

        client.protocol = 'pbc'
        with b.report('pbc seq'):
            for bucket, key in bkeys:
                client.bucket(bucket).get(key)

        with b.report('pbc multi'):
            multiget(client, bkeys)

########NEW FILE########
__FILENAME__ = operations
"""
Copyright 2012 Basho Technologies, Inc.

This file is provided to you under the Apache License,
Version 2.0 (the "License"); you may not use this file
except in compliance with the License.  You may obtain
a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on an
"AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
KIND, either express or implied.  See the License for the
specific language governing permissions and limitations
under the License.
"""

from transport import RiakClientTransport, retryable, retryableHttpOnly
from multiget import multiget
from index_page import IndexPage


class RiakClientOperations(RiakClientTransport):
    """
    Methods for RiakClient that result in requests sent to the Riak
    cluster.

    Note that many of these methods have an implicit 'transport'
    argument that will be prepended automatically as part of the retry
    logic, and does not need to be supplied by the user.
    """

    @retryable
    def get_buckets(self, transport, bucket_type=None, timeout=None):
        """
        get_buckets(bucket_type=None, timeout=None)

        Get the list of buckets as :class:`RiakBucket
        <riak.bucket.RiakBucket>` instances.

        .. warning:: Do not use this in production, as it requires
           traversing through all keys stored in a cluster.

        .. note:: This request is automatically retried :attr:`retries`
           times if it fails due to network error.

        :param bucket_type: the optional containing bucket type
        :type bucket_type: :class:`~riak.bucket.BucketType`
        :param timeout: a timeout value in milliseconds
        :type timeout: int
        :rtype: list of :class:`RiakBucket <riak.bucket.RiakBucket>` instances
        """
        _validate_timeout(timeout)
        if bucket_type:
            bucketfn = lambda name: bucket_type.bucket(name)
        else:
            bucketfn = lambda name: self.bucket(name)

        return [bucketfn(name) for name in
                transport.get_buckets(bucket_type=bucket_type,
                                      timeout=timeout)]

    def stream_buckets(self, bucket_type=None, timeout=None):
        """
        Streams the list of buckets. This is a generator method that
        should be iterated over.

        .. warning:: Do not use this in production, as it requires
           traversing through all keys stored in a cluster.

        :param bucket_type: the optional containing bucket type
        :type bucket_type: :class:`~riak.bucket.BucketType`
        :param timeout: a timeout value in milliseconds
        :type timeout: int
        :rtype: iterator that yields lists of :class:`RiakBucket
             <riak.bucket.RiakBucket>` instances
        """
        _validate_timeout(timeout)
        if bucket_type:
            bucketfn = lambda name: bucket_type.bucket(name)
        else:
            bucketfn = lambda name: self.bucket(name)

        with self._transport() as transport:
            stream = transport.stream_buckets(bucket_type=bucket_type,
                                              timeout=timeout)
            try:
                for bucket_list in stream:
                    bucket_list = [bucketfn(name) for name in bucket_list]
                    if len(bucket_list) > 0:
                        yield bucket_list
            finally:
                stream.close()

    @retryable
    def ping(self, transport):
        """
        ping()

        Check if the Riak server for this ``RiakClient`` instance is alive.

        .. note:: This request is automatically retried :attr:`retries`
           times if it fails due to network error.

        :rtype: boolean
        """
        return transport.ping()

    is_alive = ping

    @retryable
    def get_index(self, transport, bucket, index, startkey, endkey=None,
                  return_terms=None, max_results=None, continuation=None,
                  timeout=None, term_regex=None):
        """
        get_index(bucket, index, startkey, endkey=None, return_terms=None,\
                  max_results=None, continuation=None)

        Queries a secondary index, returning matching keys.

        .. note:: This request is automatically retried :attr:`retries`
           times if it fails due to network error.

        :param bucket: the bucket whose index will be queried
        :type bucket: RiakBucket
        :param index: the index to query
        :type index: string
        :param startkey: the sole key to query, or beginning of the query range
        :type startkey: string, integer
        :param endkey: the end of the query range (optional if equality)
        :type endkey: string, integer
        :param return_terms: whether to include the secondary index value
        :type return_terms: boolean
        :param max_results: the maximum number of results to return (page size)
        :type max_results: integer
        :param continuation: the opaque continuation returned from a
            previous paginated request
        :type continuation: string
        :param timeout: a timeout value in milliseconds, or 'infinity'
        :type timeout: int
        :param term_regex: a regular expression used to filter index terms
        :type term_regex: string
        :rtype: :class:`riak.client.index_page.IndexPage`
        """
        if timeout != 'infinity':
            _validate_timeout(timeout)

        page = IndexPage(self, bucket, index, startkey, endkey,
                         return_terms, max_results, term_regex)

        results, continuation = transport.get_index(
            bucket, index, startkey, endkey, return_terms=return_terms,
            max_results=max_results, continuation=continuation,
            timeout=timeout, term_regex=term_regex)

        page.results = results
        page.continuation = continuation
        return page

    def stream_index(self, bucket, index, startkey, endkey=None,
                     return_terms=None, max_results=None, continuation=None,
                     timeout=None, term_regex=None):
        """
        Queries a secondary index, streaming matching keys through an
        iterator.

        :param bucket: the bucket whose index will be queried
        :type bucket: RiakBucket
        :param index: the index to query
        :type index: string
        :param startkey: the sole key to query, or beginning of the query range
        :type startkey: string, integer
        :param endkey: the end of the query range (optional if equality)
        :type endkey: string, integer
        :param return_terms: whether to include the secondary index value
        :type return_terms: boolean
        :param max_results: the maximum number of results to return (page size)
        :type max_results: integer
        :param continuation: the opaque continuation returned from a
            previous paginated request
        :type continuation: string
        :param timeout: a timeout value in milliseconds, or 'infinity'
        :type timeout: int
        :param term_regex: a regular expression used to filter index terms
        :type term_regex: string
        :rtype: :class:`riak.client.index_page.IndexPage`
        """
        if timeout != 'infinity':
            _validate_timeout(timeout)

        with self._transport() as transport:
            page = IndexPage(self, bucket, index, startkey, endkey,
                             return_terms, max_results, term_regex)
            page.stream = True
            page.results = transport.stream_index(
                bucket, index, startkey, endkey, return_terms=return_terms,
                max_results=max_results, continuation=continuation,
                timeout=timeout, term_regex=term_regex)
            return page

    @retryable
    def get_bucket_props(self, transport, bucket):
        """
        get_bucket_props(bucket)

        Fetches bucket properties for the given bucket.

        .. note:: This request is automatically retried :attr:`retries`
           times if it fails due to network error.

        :param bucket: the bucket whose properties will be fetched
        :type bucket: RiakBucket
        :rtype: dict
        """
        return transport.get_bucket_props(bucket)

    @retryable
    def set_bucket_props(self, transport, bucket, props):
        """
        set_bucket_props(bucket, props)

        Sets bucket properties for the given bucket.

        .. note:: This request is automatically retried :attr:`retries`
           times if it fails due to network error.

        :param bucket: the bucket whose properties will be set
        :type bucket: RiakBucket
        :param props: the properties to set
        :type props: dict
        """
        return transport.set_bucket_props(bucket, props)

    @retryable
    def clear_bucket_props(self, transport, bucket):
        """
        clear_bucket_props(bucket)

        Resets bucket properties for the given bucket.

        .. note:: This request is automatically retried :attr:`retries`
           times if it fails due to network error.

        :param bucket: the bucket whose properties will be set
        :type bucket: RiakBucket
        """
        return transport.clear_bucket_props(bucket)

    @retryable
    def get_bucket_type_props(self, transport, bucket_type):
        """
        get_bucket_type_props(bucket_type)

        Fetches properties for the given bucket-type.

        .. note:: This request is automatically retried :attr:`retries`
           times if it fails due to network error.

        :param bucket_type: the bucket-type whose properties will be fetched
        :type bucket_type: BucketType
        :rtype: dict
        """
        return transport.get_bucket_type_props(bucket_type)

    @retryable
    def set_bucket_type_props(self, transport, bucket_type, props):
        """
        set_bucket_type_props(bucket_type, props)

        Sets properties for the given bucket-type.

        .. note:: This request is automatically retried :attr:`retries`
           times if it fails due to network error.

        :param bucket_type: the bucket-type whose properties will be set
        :type bucket_type: BucketType
        :param props: the properties to set
        :type props: dict
        """
        return transport.set_bucket_type_props(bucket_type, props)

    @retryable
    def get_keys(self, transport, bucket, timeout=None):
        """
        get_keys(bucket, timeout=None)

        Lists all keys in a bucket.

        .. note:: This request is automatically retried :attr:`retries`
           times if it fails due to network error.

        :param bucket: the bucket whose keys are fetched
        :type bucket: RiakBucket
        :param timeout: a timeout value in milliseconds
        :type timeout: int
        :rtype: list
        """
        _validate_timeout(timeout)
        return transport.get_keys(bucket, timeout=timeout)

    def stream_keys(self, bucket, timeout=None):
        """
        Lists all keys in a bucket via a stream. This is a generator
        method which should be iterated over.

        :param bucket: the bucket whose properties will be set
        :type bucket: RiakBucket
        :param timeout: a timeout value in milliseconds
        :type timeout: int
        :rtype: iterator
        """
        _validate_timeout(timeout)
        with self._transport() as transport:
            stream = transport.stream_keys(bucket, timeout=timeout)
            try:
                for keylist in stream:
                    if len(keylist) > 0:
                        yield keylist
            finally:
                stream.close()

    @retryable
    def put(self, transport, robj, w=None, dw=None, pw=None, return_body=None,
            if_none_match=None, timeout=None):
        """
        put(robj, w=None, dw=None, pw=None, return_body=None,\
            if_none_match=None, timeout=None)

        Stores an object in the Riak cluster.

        .. note:: This request is automatically retried :attr:`retries`
           times if it fails due to network error.

        :param robj: the object to store
        :type robj: RiakObject
        :param w: the write quorum
        :type w: integer, string, None
        :param dw: the durable write quorum
        :type dw: integer, string, None
        :param pw: the primary write quorum
        :type pw: integer, string, None
        :param return_body: whether to return the resulting object
           after the write
        :type return_body: boolean
        :param if_none_match: whether to fail the write if the object
          exists
        :type if_none_match: boolean
        :param timeout: a timeout value in milliseconds
        :type timeout: int
        """
        _validate_timeout(timeout)
        return transport.put(robj, w=w, dw=dw, pw=pw,
                             return_body=return_body,
                             if_none_match=if_none_match,
                             timeout=timeout)

    @retryable
    def get(self, transport, robj, r=None, pr=None, timeout=None):
        """
        get(robj, r=None, pr=None, timeout=None)

        Fetches the contents of a Riak object.

        .. note:: This request is automatically retried :attr:`retries`
           times if it fails due to network error.

        :param robj: the object to fetch
        :type robj: RiakObject
        :param r: the read quorum
        :type r: integer, string, None
        :param pr: the primary read quorum
        :type pr: integer, string, None
        :param timeout: a timeout value in milliseconds
        :type timeout: int
        """
        _validate_timeout(timeout)
        if not isinstance(robj.key, basestring):
            raise TypeError(
                'key must be a string, instead got {0}'.format(repr(robj.key)))

        return transport.get(robj, r=r, pr=pr, timeout=timeout)

    @retryable
    def delete(self, transport, robj, rw=None, r=None, w=None, dw=None,
               pr=None, pw=None, timeout=None):
        """
        delete(robj, rw=None, r=None, w=None, dw=None, pr=None, pw=None,\
               timeout=None)

        Deletes an object from Riak.

        .. note:: This request is automatically retried :attr:`retries`
           times if it fails due to network error.

        :param robj: the object to delete
        :type robj: RiakObject
        :param rw: the read/write (delete) quorum
        :type rw: integer, string, None
        :param r: the read quorum
        :type r: integer, string, None
        :param pr: the primary read quorum
        :type pr: integer, string, None
        :param w: the write quorum
        :type w: integer, string, None
        :param dw: the durable write quorum
        :type dw: integer, string, None
        :param pw: the primary write quorum
        :type pw: integer, string, None
        :param timeout: a timeout value in milliseconds
        :type timeout: int
        """
        _validate_timeout(timeout)
        return transport.delete(robj, rw=rw, r=r, w=w, dw=dw, pr=pr,
                                pw=pw, timeout=timeout)

    @retryable
    def mapred(self, transport, inputs, query, timeout):
        """
        mapred(inputs, query, timeout)

        Executes a MapReduce query.

        .. note:: This request is automatically retried :attr:`retries`
           times if it fails due to network error.

        :param inputs: the input list/structure
        :type inputs: list, dict
        :param query: the list of query phases
        :type query: list
        :param timeout: the query timeout
        :type timeout: integer, None
        :rtype: mixed
        """
        _validate_timeout(timeout)
        return transport.mapred(inputs, query, timeout)

    def stream_mapred(self, inputs, query, timeout):
        """
        Streams a MapReduce query as (phase, data) pairs. This is a
        generator method which should be iterated over.

        :param inputs: the input list/structure
        :type inputs: list, dict
        :param query: the list of query phases
        :type query: list
        :param timeout: the query timeout
        :type timeout: integer, None
        :rtype: iterator
        """
        _validate_timeout(timeout)
        with self._transport() as transport:
            stream = transport.stream_mapred(inputs, query, timeout)
            try:
                for phase, data in stream:
                    yield phase, data
            finally:
                stream.close()

    @retryable
    def create_search_index(self, transport, index, schema=None, n_val=None):
        """
        create_search_index(index, schema, n_val)

        Create a search index of the given name, and optionally set
        a schema. If no schema is set, the default will be used.

        :param index: the name of the index to create
        :type index: string
        :param schema: the schema that this index will follow
        :type schema: string, None
        :param n_val: this indexes N value
        :type n_val: integer, None
        """
        return transport.create_search_index(index, schema, n_val)

    @retryable
    def get_search_index(self, transport, index):
        """
        get_search_index(index)

        Gets a search index of the given name if it exists,
        which will also return the schema. Raises a RiakError
        if no such schema exists.

        :param index: the name of the index to create
        :type index: string
        """
        return transport.get_search_index(index)

    @retryable
    def list_search_indexes(self, transport):
        """
        list_search_indexes(bucket)

        Gets all search indexes and their schemas. Returns
        a blank list if none exist
        """
        return transport.list_search_indexes()

    @retryable
    def delete_search_index(self, transport, index):
        """
        delete_search_index(index)

        Delete the search index that matches the given name.

        :param index: the name of the index to delete
        :type index: string
        """
        return transport.delete_search_index(index)

    @retryable
    def create_search_schema(self, transport, schema, content):
        """
        create_search_schema(schema, content)

        Creates a solr schema of the given name and content.
        Content must be valid solr schema xml.

        :param schema: the name of the schema to create
        :type schema: string
        :param schema: the solr schema xml content
        :type schema: string
        """
        return transport.create_search_schema(schema, content)

    @retryable
    def get_search_schema(self, transport, schema):
        """
        get_search_schema(schema)

        Gets a search schema of the given name if it exists.
        Raises a RiakError if no such schema exists.

        :param schema: the name of the schema to get
        :type schema: string
        """
        return transport.get_search_schema(schema)

    @retryable
    def fulltext_search(self, transport, index, query, **params):
        """
        fulltext_search(index, query, **params)

        Performs a full-text search query.

        .. note:: This request is automatically retried :attr:`retries`
           times if it fails due to network error.

        :param index: the bucket/index to search over
        :type index: string
        :param query: the search query
        :type query: string
        :param params: additional query flags
        :type params: dict
        """
        return transport.search(index, query, **params)

    @retryableHttpOnly
    def fulltext_add(self, transport, index, docs):
        """
        fulltext_add(index, docs)

        Adds documents to the full-text index.

        .. note:: This request is automatically retried
           :attr:`retries` times if it fails due to network error.
           Only HTTP will be used for this request.

        :param index: the bucket/index in which to index these docs
        :type index: string
        :param docs: the list of documents
        :type docs: list
        """
        transport.fulltext_add(index, docs)

    @retryableHttpOnly
    def fulltext_delete(self, transport, index, docs=None, queries=None):
        """
        fulltext_delete(index, docs=None, queries=None)

        Removes documents from the full-text index.

        .. note:: This request is automatically retried
           :attr:`retries` times if it fails due to network error.
           Only HTTP will be used for this request.

        :param index: the bucket/index from which to delete
        :type index: string
        :param docs: a list of documents (with ids)
        :type docs: list
        :param queries: a list of queries to match and delete
        :type queries: list
        """
        transport.fulltext_delete(index, docs, queries)

    def multiget(self, pairs, **params):
        """
        Fetches many keys in parallel via threads.

        :param pairs: list of bucket/key tuple pairs
        :type pairs: list
        :param params: additional request flags, e.g. r, pr
        :type params: dict
        :rtype: list of :class:`RiakObject <riak.riak_object.RiakObject>`
            instances
        """
        return multiget(self, pairs, **params)

    @retryable
    def get_counter(self, transport, bucket, key, r=None, pr=None,
                    basic_quorum=None, notfound_ok=None):
        """
        get_counter(bucket, key, r=None, pr=None, basic_quorum=None,\
                    notfound_ok=None)

        Gets the value of a counter.

        .. note:: This request is automatically retried :attr:`retries`
           times if it fails due to network error.

        :param bucket: the bucket of the counter
        :type bucket: RiakBucket
        :param key: the key of the counter
        :type key: string
        :param r: the read quorum
        :type r: integer, string, None
        :param pr: the primary read quorum
        :type pr: integer, string, None
        :param basic_quorum: whether to use the "basic quorum" policy
           for not-founds
        :type basic_quorum: bool
        :param notfound_ok: whether to treat not-found responses as successful
        :type notfound_ok: bool
        :rtype: integer
        """
        return transport.get_counter(bucket, key, r=r, pr=pr)

    def update_counter(self, bucket, key, value, w=None, dw=None, pw=None,
                       returnvalue=False):
        """
        update_counter(bucket, key, value, w=None, dw=None, pw=None,\
                       returnvalue=False)

        Updates a counter by the given value. This operation is not
        idempotent and so should not be retried automatically.

        :param bucket: the bucket of the counter
        :type bucket: RiakBucket
        :param key: the key of the counter
        :type key: string
        :param value: the amount to increment or decrement
        :type value: integer
        :param w: the write quorum
        :type w: integer, string, None
        :param dw: the durable write quorum
        :type dw: integer, string, None
        :param pw: the primary write quorum
        :type pw: integer, string, None
        :param returnvalue: whether to return the updated value of the counter
        :type returnvalue: bool
        """
        if type(value) not in (int, long):
            raise TypeError("Counter update amount must be an integer")
        if value == 0:
            raise ValueError("Cannot increment counter by 0")

        with self._transport() as transport:
            return transport.update_counter(bucket, key, value,
                                            w=w, dw=dw, pw=pw,
                                            returnvalue=returnvalue)

    increment_counter = update_counter


def _validate_timeout(timeout):
    """
    Raises an exception if the given timeout is an invalid value.
    """
    if not (timeout is None or
            (type(timeout) in (int, long) and
             timeout > 0)):
        raise ValueError("timeout must be a positive integer")

########NEW FILE########
__FILENAME__ = transport
"""
Copyright 2012 Basho Technologies, Inc.

This file is provided to you under the Apache License,
Version 2.0 (the "License"); you may not use this file
except in compliance with the License.  You may obtain
a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on an
"AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
KIND, either express or implied.  See the License for the
specific language governing permissions and limitations
under the License.
"""
from contextlib import contextmanager
from riak.transports.pool import BadResource
from riak.transports.pbc import is_retryable as is_pbc_retryable
from riak.transports.http import is_retryable as is_http_retryable
import threading
import httplib

#: The default (global) number of times to retry requests that are
#: retryable. This can be modified locally, per-thread, via the
#: :attr:`RiakClient.retries` property, or using the
#: :attr:`RiakClient.retry_count` method in a ``with`` statement.
DEFAULT_RETRY_COUNT = 3


class _client_locals(threading.local):
    """
    A thread-locals object used by the client.
    """
    def __init__(self):
        self.riak_retries_count = DEFAULT_RETRY_COUNT


class RiakClientTransport(object):
    """
    Methods for RiakClient related to transport selection and retries.
    """

    # These will be set or redefined by the RiakClient initializer
    protocol = 'http'
    _http_pool = None
    _pb_pool = None
    _locals = _client_locals()

    def _get_retry_count(self):
        return self._locals.riak_retries_count or DEFAULT_RETRY_COUNT

    def _set_retry_count(self, value):
        if not isinstance(value, int):
            raise TypeError("retries must be an integer")
        self._locals.riak_retries_count = value

    __retries_doc = """
          The number of times retryable operations will be attempted
          before raising an exception to the caller. Defaults to
          ``3``.

          :note: This is a thread-local for safety and
                 operation-specific modification. To change the
                 default globally, modify
                 :data:`riak.client.transport.DEFAULT_RETRY_COUNT`.
          """

    retries = property(_get_retry_count, _set_retry_count, doc=__retries_doc)

    @contextmanager
    def retry_count(self, retries):
        """
        retry_count(retries)

        Modifies the number of retries for the scope of the ``with``
        statement (in the current thread).

        Example::

            with client.retry_count(10):
                client.ping()
        """
        if not isinstance(retries, int):
            raise TypeError("retries must be an integer")

        old_retries, self.retries = self.retries, retries
        try:
            yield
        finally:
            self.retries = old_retries

    @contextmanager
    def _transport(self):
        """
        _transport()

        Yields a single transport to the caller from the default pool,
        without retries.
        """
        pool = self._choose_pool()
        with pool.take() as transport:
            yield transport

    def _with_retries(self, pool, fn):
        """
        Performs the passed function with retries against the given pool.

        :param pool: the connection pool to use
        :type pool: Pool
        :param fn: the function to pass a transport
        :type fn: function
        """
        skip_nodes = []

        def _skip_bad_nodes(transport):
            return transport._node not in skip_nodes

        retry_count = self.retries

        for retry in range(retry_count):
            try:
                with pool.take(_filter=_skip_bad_nodes) as transport:
                    try:
                        return fn(transport)
                    except (IOError, httplib.HTTPException) as e:
                        if _is_retryable(e):
                            transport._node.error_rate.incr(1)
                            skip_nodes.append(transport._node)
                            raise BadResource(e)
                        else:
                            raise
            except BadResource as e:
                if retry < (retry_count - 1):
                    continue
                else:
                    # Re-raise the inner exception
                    raise e.args[0]

    def _choose_pool(self, protocol=None):
        """
        Selects a connection pool according to the default protocol
        and the passed one.

        :param protocol: the protocol to use
        :type protocol: string
        :rtype: Pool
        """
        if not protocol:
            protocol = self.protocol
        if protocol in ['http', 'https']:
            pool = self._http_pool
        elif protocol == 'pbc':
            pool = self._pb_pool
        else:
            raise ValueError("invalid protocol %s" % protocol)
        return pool


def _is_retryable(error):
    """
    Determines whether a given error is retryable according to the
    exceptions allowed to be retried by each transport.

    :param error: the error to check
    :type error: Exception
    :rtype: boolean
    """
    return is_pbc_retryable(error) or is_http_retryable(error)


def retryable(fn, protocol=None):
    """
    Wraps a client operation that can be retried according to the set
    :attr:`RiakClient.retries`. Used internally.
    """
    def wrapper(self, *args, **kwargs):
        pool = self._choose_pool(protocol)

        def thunk(transport):
            return fn(self, transport, *args, **kwargs)

        return self._with_retries(pool, thunk)

    wrapper.__doc__ = fn.__doc__
    wrapper.__repr__ = fn.__repr__

    return wrapper


def retryableHttpOnly(fn):
    """
    Wraps a retryable client operation that is only valid over HTTP.
    Used internally.
    """
    return retryable(fn, protocol='http')

########NEW FILE########
__FILENAME__ = content
"""
Copyright 2013 Basho Technologies, Inc.

This file is provided to you under the Apache License,
Version 2.0 (the "License"); you may not use this file
except in compliance with the License.  You may obtain
a copy of the License at

  http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on an
"AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
KIND, either express or implied.  See the License for the
specific language governing permissions and limitations
under the License.
"""
from riak import RiakError
from riak.util import deprecated


class RiakContent(object):
    """
    The RiakContent holds the metadata and value of a single sibling
    within a RiakObject. RiakObjects that have more than one sibling
    are considered to be in conflict.
    """
    def __init__(self, robject, data=None, encoded_data=None, charset=None,
                 content_type='application/json', content_encoding=None,
                 last_modified=None, etag=None, usermeta=None, links=None,
                 indexes=None, exists=False):
        self._robject = robject
        self._data = data
        self._encoded_data = encoded_data
        self.charset = charset
        self.content_type = content_type
        self.content_encoding = content_encoding
        self.last_modified = last_modified
        self.etag = etag
        self.usermeta = usermeta or {}
        self.links = links or []
        self.indexes = indexes or set()
        self.exists = exists

    def _get_data(self):
        if self._encoded_data is not None and self._data is None:
            self._data = self._deserialize(self._encoded_data)
            self._encoded_data = None
        return self._data

    def _set_data(self, value):
        self._encoded_data = None
        self._data = value

    data = property(_get_data, _set_data, doc="""
        The data stored in this object, as Python objects. For the raw
        data, use the `encoded_data` property. If unset, accessing
        this property will result in decoding the `encoded_data`
        property into Python values. The decoding is dependent on the
        `content_type` property and the bucket's registered decoders.
        :type mixed """)

    def get_encoded_data(self):
        deprecated("`get_encoded_data` is deprecated, use the `encoded_data`"
                   " property")
        return self.encoded_data

    def set_encoded_data(self, value):
        deprecated("`set_encoded_data` is deprecated, use the `encoded_data`"
                   " property")
        self.encoded_data = value

    def _get_encoded_data(self):
        if self._data is not None and self._encoded_data is None:
            self._encoded_data = self._serialize(self._data)
            self._data = None
        return self._encoded_data

    def _set_encoded_data(self, value):
        self._data = None
        self._encoded_data = value

    encoded_data = property(_get_encoded_data, _set_encoded_data, doc="""
        The raw data stored in this object, essentially the encoded
        form of the `data` property. If unset, accessing this property
        will result in encoding the `data` property into a string. The
        encoding is dependent on the `content_type` property and the
        bucket's registered encoders.
        :type basestring""")

    def _serialize(self, value):
        encoder = self._robject.bucket.get_encoder(self.content_type)
        if encoder:
            return encoder(value)
        elif isinstance(value, basestring):
            return value.encode()
        else:
            raise TypeError('No encoder for non-string data '
                            'with content type "{0}"'.
                            format(self.content_type))

    def _deserialize(self, value):
        decoder = self._robject.bucket.get_decoder(self.content_type)
        if decoder:
            return decoder(value)
        else:
            raise TypeError('No decoder for content type "{0}"'.
                            format(self.content_type))

    def add_index(self, field, value):
        """
        add_index(field, value)

        Tag this object with the specified field/value pair for
        indexing.

        :param field: The index field.
        :type field: string
        :param value: The index value.
        :type value: string or integer
        :rtype: :class:`RiakObject <riak.riak_object.RiakObject>`
        """
        if field[-4:] not in ("_bin", "_int"):
            raise RiakError("Riak 2i fields must end with either '_bin'"
                            " or '_int'.")

        self.indexes.add((field, value))

        return self._robject

    def remove_index(self, field=None, value=None):
        """
        remove_index(field=None, value=None)

        Remove the specified field/value pair as an index on this
        object.

        :param field: The index field.
        :type field: string
        :param value: The index value.
        :type value: string or integer
        :rtype: :class:`RiakObject <riak.riak_object.RiakObject>`
        """
        if not field and not value:
            self.indexes.clear()
        elif field and not value:
            for index in [x for x in self.indexes if x[0] == field]:
                self.indexes.remove(index)
        elif field and value:
            self.indexes.remove((field, value))
        else:
            raise RiakError("Cannot pass value without a field"
                            " name while removing index")

        return self._robject

    remove_indexes = remove_index

    def set_index(self, field, value):
        """
        set_index(field, value)

        Works like :meth:`add_index`, but ensures that there is only
        one index on given field. If other found, then removes it
        first.

        :param field: The index field.
        :type field: string
        :param value: The index value.
        :type value: string or integer
        :rtype: :class:`RiakObject <riak.riak_object.RiakObject>`
        """
        to_rem = set((x for x in self.indexes if x[0] == field))
        self.indexes.difference_update(to_rem)
        return self.add_index(field, value)

    def add_link(self, obj, tag=None):
        """
        add_link(obj, tag=None)

        Add a link to a RiakObject.

        :param obj: Either a RiakObject or 3 item link tuple consisting
            of (bucket, key, tag).
        :type obj: mixed
        :param tag: Optional link tag. Defaults to bucket name. It is ignored
            if ``obj`` is a 3 item link tuple.
        :type tag: string
        :rtype: :class:`RiakObject <riak.riak_object.RiakObject>`
        """
        if isinstance(obj, tuple):
            newlink = obj
        else:
            newlink = (obj.bucket.name, obj.key, tag)

        self.links.append(newlink)
        return self._robject

########NEW FILE########
__FILENAME__ = mapreduce
"""
Copyright 2010 Rusty Klophaus <rusty@basho.com>
Copyright 2010 Justin Sheehy <justin@basho.com>
Copyright 2009 Jay Baird <jay@mochimedia.com>

This file is provided to you under the Apache License,
Version 2.0 (the "License"); you may not use this file
except in compliance with the License.  You may obtain
a copy of the License at

  http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on an
"AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
KIND, either express or implied.  See the License for the
specific language governing permissions and limitations
under the License.
"""

from collections import Iterable, namedtuple
from riak import RiakError

#: Links are just bucket/key/tag tuples, this class provides a
#: backwards-compatible format: ``RiakLink(bucket, key, tag)``
RiakLink = namedtuple("RiakLink", ("bucket", "key", "tag"))


class RiakMapReduce(object):
    """
    The RiakMapReduce object allows you to build up and run a
    map/reduce operation on Riak. Most methods return the object on
    which it was called, modified with new information, so you can
    chain calls together to build the job.
    """
    def __init__(self, client):
        """
        Construct a Map/Reduce object.

        :param client: the client that will perform the query
        :type client: :class:`~riak.client.RiakClient`
        """
        self._client = client
        self._phases = []
        self._inputs = []
        self._key_filters = []
        self._input_mode = None

    def add(self, arg1, arg2=None, arg3=None):
        """
        Add inputs to a map/reduce operation. This method takes three
        different forms, depending on the provided inputs. You can
        specify either a RiakObject, a string bucket name, or a bucket,
        key, and additional arg.

        :param arg1: the object or bucket to add
        :type arg1: RiakObject, string
        :param arg2: a key or list of keys to add (if a bucket is
          given in arg1)
        :type arg2: string, list, None
        :param arg3: key data for this input (must be convertible to JSON)
        :type arg3: string, list, dict, None
        :rtype: :class:`RiakMapReduce`
        """
        if (arg2 is None) and (arg3 is None):
            if isinstance(arg1, RiakObject):
                return self.add_object(arg1)
            else:
                return self.add_bucket(arg1)
        else:
            return self.add_bucket_key_data(arg1, arg2, arg3)

    def add_object(self, obj):
        """
        Adds a RiakObject to the inputs.

        :param obj: the object to add
        :type obj: RiakObject
        :rtype: :class:`RiakMapReduce`
        """
        return self.add_bucket_key_data(obj._bucket._name, obj._key, None)

    def add_bucket_key_data(self, bucket, key, data):
        """
        Adds a bucket/key/keydata triple to the inputs.

        :param bucket: the bucket
        :type bucket: string
        :param key: the key or list of keys
        :type key: string
        :param data: the key-specific data
        :type data: string, list, dict, None
        :rtype: :class:`RiakMapReduce`
        """
        if self._input_mode == 'bucket':
            raise ValueError('Already added a bucket, can\'t add an object.')
        elif self._input_mode == 'query':
            raise ValueError('Already added a query, can\'t add an object.')
        else:
            if isinstance(key, Iterable) and \
                    not isinstance(key, basestring):
                for k in key:
                    self._inputs.append([bucket, k, data])
            else:
                self._inputs.append([bucket, key, data])
            return self

    def add_bucket(self, bucket):
        """
        Adds all keys in a bucket to the inputs.

        :param bucket: the bucket
        :type bucket: string
        :rtype: :class:`RiakMapReduce`
        """
        self._input_mode = 'bucket'
        self._inputs = bucket
        return self

    def add_key_filters(self, key_filters):
        """
        Adds key filters to the inputs.

        :param key_filters: a list of filters
        :type key_filters: list
        :rtype: :class:`RiakMapReduce`
        """
        if self._input_mode == 'query':
            raise ValueError('Key filters are not supported in a query.')

        self._key_filters.extend(key_filters)
        return self

    def add_key_filter(self, *args):
        """
        Add a single key filter to the inputs.

        :param args: a filter
        :type args: list
        :rtype: :class:`RiakMapReduce`
        """
        if self._input_mode == 'query':
            raise ValueError('Key filters are not supported in a query.')

        self._key_filters.append(args)
        return self

    def search(self, bucket, query):
        """
        Begin a map/reduce operation using a Search. This command will
        return an error unless executed against a Riak Search cluster.

        :param bucket: The bucket over which to perform the search
        :type bucket: string
        :param query: The search query
        :type query: string
        :rtype: :class:`RiakMapReduce`
        """
        self._input_mode = 'query'
        self._inputs = {'module': 'riak_search',
                        'function': 'mapred_search',
                        'arg': [bucket, query]}
        return self

    def index(self, bucket, index, startkey, endkey=None):
        """
        Begin a map/reduce operation using a Secondary Index
        query.

        :param bucket: The bucket over which to perform the query
        :type bucket: string
        :param index: The index to use for query
        :type index: string
        :param startkey: The start key of index range, or the
           value which all entries must equal
        :type startkey: string, integer
        :param endkey: The end key of index range (if doing a range query)
        :type endkey: string, integer, None
        :rtype: :class:`RiakMapReduce`
        """
        self._input_mode = 'query'

        if endkey is None:
            self._inputs = {'bucket': bucket,
                            'index': index,
                            'key': startkey}
        else:
            self._inputs = {'bucket': bucket,
                            'index': index,
                            'start': startkey,
                            'end': endkey}
        return self

    def link(self, bucket='_', tag='_', keep=False):
        """
        Add a link phase to the map/reduce operation.

        :param bucket: Bucket name (default '_', which means all
            buckets)
        :type bucket: string
        :param tag:  Tag (default '_', which means any tag)
        :type tag: string
        :param keep: Flag whether to keep results from this stage in
          the map/reduce. (default False, unless this is the last step
          in the phase)
        :type keep: boolean
        :rtype: :class:`RiakMapReduce`
        """
        self._phases.append(RiakLinkPhase(bucket, tag, keep))
        return self

    def map(self, function, options=None):
        """
        Add a map phase to the map/reduce operation.

        :param function: Either a named Javascript function (ie:
          'Riak.mapValues'), or an anonymous javascript function (ie:
          'function(...) ... ' or an array ['erlang_module',
          'function'].
        :type function: string, list
        :param options: phase options, containing 'language', 'keep'
          flag, and/or 'arg'.
        :type options: dict
        :rtype: :class:`RiakMapReduce`
        """
        if options is None:
            options = dict()
        if isinstance(function, list):
            language = 'erlang'
        else:
            language = 'javascript'

        mr = RiakMapReducePhase('map',
                                function,
                                options.get('language', language),
                                options.get('keep', False),
                                options.get('arg', None))
        self._phases.append(mr)
        return self

    def reduce(self, function, options=None):
        """
        Add a reduce phase to the map/reduce operation.

        :param function: Either a named Javascript function (ie.
          'Riak.reduceSum'), or an anonymous javascript function(ie:
          'function(...) { ... }' or an array ['erlang_module',
          'function'].
        :type function: string, list
        :param options: phase options, containing 'language', 'keep'
          flag, and/or 'arg'.
        :rtype: :class:`RiakMapReduce`
        """
        if options is None:
            options = dict()
        if isinstance(function, list):
            language = 'erlang'
        else:
            language = 'javascript'

        mr = RiakMapReducePhase('reduce',
                                function,
                                options.get('language', language),
                                options.get('keep', False),
                                options.get('arg', None))
        self._phases.append(mr)
        return self

    def run(self, timeout=None):
        """
        Run the map/reduce operation synchronously. Returns a list of
        results, or a list of links if the last phase is a link phase.
        Shortcut for :meth:`riak.client.RiakClient.mapred`.

        :param timeout: Timeout in milliseconds
        :type timeout: integer, None
        :rtype: list
        """
        query, link_results_flag = self._normalize_query()

        try:
            result = self._client.mapred(self._inputs, query, timeout)
        except RiakError as e:
            if 'worker_startup_failed' in e.value:
                for phase in self._phases:
                    if phase._language == 'erlang':
                        if type(phase._function) is str:
                            raise RiakError('May have tried erlang strfun '
                                            'when not allowed\n'
                                            'original error: ' + e.value)
            raise e

        # If the last phase is NOT a link phase, then return the result.
        if not (link_results_flag
                or isinstance(self._phases[-1], RiakLinkPhase)):
            return result

        # If there are no results, then return an empty list.
        if result is None:
            return []

        # Otherwise, if the last phase IS a link phase, then convert the
        # results to link tuples.
        a = []
        for r in result:
            if (len(r) == 2):
                link = (r[0], r[1], None)
            elif (len(r) == 3):
                link = (r[0], r[1], r[2])
            a.append(link)

        return a

    def stream(self, timeout=None):
        """
        Streams the MapReduce query (returns an iterator). Shortcut
        for :meth:`riak.client.RiakClient.stream_mapred`.

        :param timeout: Timeout in milliseconds
        :type timeout: integer
        :rtype: iterator that yields (phase_num, data) tuples
        """
        query, lrf = self._normalize_query()
        return self._client.stream_mapred(self._inputs, query, timeout)

    def _normalize_query(self):
        num_phases = len(self._phases)

        # If there are no phases, return the keys as links
        if num_phases is 0:
            link_results_flag = True
        else:
            link_results_flag = False

        # Convert all phases to associative arrays. Also,
        # if none of the phases are accumulating, then set the last one to
        # accumulate.
        keep_flag = False
        query = []
        for i in range(num_phases):
            phase = self._phases[i]
            if (i == (num_phases - 1)) and (not keep_flag):
                phase._keep = True
            if phase._keep:
                keep_flag = True
            query.append(phase.to_array())

        if (len(self._key_filters) > 0):
            bucket_name = None
            if (type(self._inputs) == str):
                bucket_name = self._inputs
            elif (type(self._inputs) == RiakBucket):
                bucket_name = self._inputs.name

            if (bucket_name is not None):
                self._inputs = {'bucket':       bucket_name,
                                'key_filters':  self._key_filters}

        return query, link_results_flag

    ##
    # Start Shortcuts to built-ins
    ##
    def map_values(self, options=None):
        """
        Adds the Javascript built-in ``Riak.mapValues`` to the query
        as a map phase.

        :param options: phase options, containing 'language', 'keep'
          flag, and/or 'arg'.
        :type options: dict
        """
        return self.map("Riak.mapValues", options=options)

    def map_values_json(self, options=None):
        """
        Adds the Javascript built-in ``Riak.mapValuesJson`` to the
        query as a map phase.

        :param options: phase options, containing 'language', 'keep'
          flag, and/or 'arg'.
        :type options: dict
        """
        return self.map("Riak.mapValuesJson", options=options)

    def reduce_sum(self, options=None):
        """
        Adds the Javascript built-in ``Riak.reduceSum`` to the query
        as a reduce phase.

        :param options: phase options, containing 'language', 'keep'
          flag, and/or 'arg'.
        :type options: dict
        """
        return self.reduce("Riak.reduceSum", options=options)

    def reduce_min(self, options=None):
        """
        Adds the Javascript built-in ``Riak.reduceMin`` to the query
        as a reduce phase.

        :param options: phase options, containing 'language', 'keep'
          flag, and/or 'arg'.
        :type options: dict
        """
        return self.reduce("Riak.reduceMin", options=options)

    def reduce_max(self, options=None):
        """
        Adds the Javascript built-in ``Riak.reduceMax`` to the query
        as a reduce phase.

        :param options: phase options, containing 'language', 'keep'
          flag, and/or 'arg'.
        :type options: dict
        """
        return self.reduce("Riak.reduceMax", options=options)

    def reduce_sort(self, js_cmp=None, options=None):
        """
        Adds the Javascript built-in ``Riak.reduceSort`` to the query
        as a reduce phase.

        :param js_cmp: A Javascript comparator function as specified by
          Array.sort()
        :type js_cmp: string
        :param options: phase options, containing 'language', 'keep'
          flag, and/or 'arg'.
        :type options: dict
        """
        if options is None:
            options = dict()

        if js_cmp:
            options['arg'] = js_cmp

        return self.reduce("Riak.reduceSort", options=options)

    def reduce_numeric_sort(self, options=None):
        """
        Adds the Javascript built-in ``Riak.reduceNumericSort`` to the
        query as a reduce phase.

        :param options: phase options, containing 'language', 'keep'
          flag, and/or 'arg'.
        :type options: dict
        """
        return self.reduce("Riak.reduceNumericSort", options=options)

    def reduce_limit(self, limit, options=None):
        """
        Adds the Javascript built-in ``Riak.reduceLimit`` to the query
        as a reduce phase.

        :param limit: the maximum number of results to return
        :type limit: integer
        :param options: phase options, containing 'language', 'keep'
          flag, and/or 'arg'.
        :type options: dict
        """
        if options is None:
            options = dict()

        options['arg'] = limit
        # reduceLimit is broken in riak_kv
        code = """function(value, arg) {
            return value.slice(0, arg);
        }"""
        return self.reduce(code, options=options)

    def reduce_slice(self, start, end, options=None):
        """
        Adds the Javascript built-in ``Riak.reduceSlice`` to the
        query as a reduce phase.

        :param start: the beginning of the slice
        :type start: integer
        :param end: the end of the slice
        :type end: integer
        :param options: phase options, containing 'language', 'keep'
          flag, and/or 'arg'.
        :type options: dict
        """
        if options is None:
            options = dict()

        options['arg'] = [start, end]
        return self.reduce("Riak.reduceSlice", options=options)

    def filter_not_found(self, options=None):
        """
        Adds the Javascript built-in ``Riak.filterNotFound`` to the query
        as a reduce phase.

        :param options: phase options, containing 'language', 'keep'
          flag, and/or 'arg'.
        :type options: dict
        """
        return self.reduce("Riak.filterNotFound", options=options)


class RiakMapReducePhase(object):
    """
    The RiakMapReducePhase holds information about a Map or Reduce
    phase in a RiakMapReduce operation.

    Normally you won't need to use this object directly, but instead
    call methods on RiakMapReduce objects to add instances to the
    query.
    """

    def __init__(self, type, function, language, keep, arg):
        """
        Construct a RiakMapReducePhase object.

        :param type: the phase type - 'map', 'reduce', 'link'
        :type type: string
        :param function: the function to execute
        :type function: string, list
        :param language: 'javascript' or 'erlang'
        :type language: string
        :param keep: whether to return the output of this phase in the results.
        :type keep: boolean
        :param arg: Additional static value to pass into the map or
          reduce function.
        :type arg: string, dict, list
        """
        try:
            if isinstance(function, basestring):
                function = function.encode('ascii')
        except UnicodeError:
            raise TypeError('Unicode encoded functions are not supported.')

        self._type = type
        self._language = language
        self._function = function
        self._keep = keep
        self._arg = arg

    def to_array(self):
        """
        Convert the RiakMapReducePhase to a format that can be output
        into JSON. Used internally.

        :rtype: dict
        """
        stepdef = {'keep': self._keep,
                   'language': self._language,
                   'arg': self._arg}

        if self._language == 'javascript':
            if isinstance(self._function, list):
                stepdef['bucket'] = self._function[0]
                stepdef['key'] = self._function[1]
            elif isinstance(self._function, str):
                if ("{" in self._function):
                    stepdef['source'] = self._function
                else:
                    stepdef['name'] = self._function

        elif (self._language == 'erlang' and isinstance(self._function, list)):
            stepdef['module'] = self._function[0]
            stepdef['function'] = self._function[1]

        elif (self._language == 'erlang' and isinstance(self._function, str)):
            stepdef['source'] = self._function

        return {self._type: stepdef}


class RiakLinkPhase(object):
    """
    The RiakLinkPhase object holds information about a Link phase in a
    map/reduce operation.

    Normally you won't need to use this object directly, but instead
    call :meth:`RiakMapReduce.link` on RiakMapReduce objects to add
    instances to the query.
    """

    def __init__(self, bucket, tag, keep):
        """
        Construct a RiakLinkPhase object.

        :param bucket: - The bucket name
        :type bucket: string
        :param tag: The tag
        :type tag: string
        :param keep: whether to return results of this phase.
        :type keep: boolean
        """
        self._bucket = bucket
        self._tag = tag
        self._keep = keep

    def to_array(self):
        """
        Convert the RiakLinkPhase to a format that can be output into
        JSON. Used internally.
        """
        stepdef = {'bucket': self._bucket,
                   'tag': self._tag,
                   'keep': self._keep}
        return {'link': stepdef}


class RiakKeyFilter(object):
    """
    A helper class for building up lists of key filters. Unknown
    methods are treated as filters to be added; ``&`` and ``|`` create
    conjunctions and disjunctions, respectively. ``+`` concatenates filters.

    Example::

        f1 = RiakKeyFilter().starts_with('2005')
        f2 = RiakKeyFilter().ends_with('-01')
        f3 = f1 & f2
        print f3
        # => [['and', [['starts_with', '2005']], [['ends_with', '-01']]]]
    """

    def __init__(self, *args):
        """
        :param args: a list of arguments to be treated as a filter.
        :type args: list
        """
        if args:
            self._filters = [list(args)]
        else:
            self._filters = []

    def __add__(self, other):
        f = RiakKeyFilter()
        f._filters = self._filters + other._filters
        return f

    def _bool_op(self, op, other):
        # If the current filter is an and, append the other's
        # filters onto the filter
        if(self._filters and self._filters[0][0] == op):
            f = RiakKeyFilter()
            f._filters.extend(self._filters)
            f._filters[0].append(other._filters)
            return f
        # Otherwise just create a new RiakKeyFilter() object with an and
        return RiakKeyFilter(op, self._filters, other._filters)

    def __and__(self, other):
        return self._bool_op("and", other)

    def __or__(self, other):
        return self._bool_op("or", other)

    def __repr__(self):
        return str(self._filters)

    def __getattr__(self, name):
        def function(*args):
            args1 = [name] + list(args)
            other = RiakKeyFilter(*args1)
            return self + other
        return function

    def __iter__(self):
        return iter(self._filters)


class RiakMapReduceChain(object):
    """
    Mixin to add chaining from the client object directly into a
    MapReduce operation.
    """
    def add(self, *args):
        """
        Start assembling a Map/Reduce operation. A shortcut for
        :func:`RiakMapReduce.add`.

        :rtype: :class:`RiakMapReduce`
        """
        mr = RiakMapReduce(self)
        return mr.add(*args)

    def search(self, *args):
        """
        Start assembling a Map/Reduce operation based on search
        results. This command will return an error unless executed
        against a Riak Search cluster. A shortcut for
        :func:`RiakMapReduce.search`.

        :rtype: :class:`RiakMapReduce`
        """
        mr = RiakMapReduce(self)
        return mr.search(*args)

    def index(self, *args):
        """
        Start assembling a Map/Reduce operation based on secondary
        index query results.

        :rtype: :class:`RiakMapReduce`
        """
        mr = RiakMapReduce(self)
        return mr.index(*args)

    def link(self, *args):
        """
        Start assembling a Map/Reduce operation. A shortcut for
        :func:`RiakMapReduce.link`.

        :rtype: :class:`RiakMapReduce`
        """
        mr = RiakMapReduce(self)
        return mr.link(*args)

    def map(self, *args):
        """
        Start assembling a Map/Reduce operation. A shortcut for
        :func:`RiakMapReduce.map`.

        :rtype: :class:`RiakMapReduce`
        """
        mr = RiakMapReduce(self)
        return mr.map(*args)

    def reduce(self, *args):
        """
        Start assembling a Map/Reduce operation. A shortcut for
        :func:`RiakMapReduce.reduce`.

        :rtype: :class:`RiakMapReduce`
        """
        mr = RiakMapReduce(self)
        return mr.reduce(*args)

from riak.riak_object import RiakObject
from riak.bucket import RiakBucket

########NEW FILE########
__FILENAME__ = multidict
# (c) 2005 Ian Bicking and contributors; written for Paste
# (http://pythonpaste.org) Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license.php
from UserDict import DictMixin


class MultiDict(DictMixin):

    """
    An ordered dictionary that can have multiple values for each key.
    Adds the methods getall, getone, mixed, and add to the normal
    dictionary interface.
    """

    def __init__(self, *args, **kw):
        if len(args) > 1:
            raise TypeError(
                "MultiDict can only be called with one positional argument")
        if args:
            if hasattr(args[0], 'iteritems'):
                items = list(args[0].iteritems())
            elif hasattr(args[0], 'items'):
                items = args[0].items()
            else:
                items = list(args[0])
            self._items = items
        else:
            self._items = []
        self._items.extend(kw.iteritems())

    def __getitem__(self, key):
        for k, v in self._items:
            if k == key:
                return v
        raise KeyError(repr(key))

    def __setitem__(self, key, value):
        try:
            del self[key]
        except KeyError:
            pass
        self._items.append((key, value))

    def add(self, key, value):
        """
        Add the key and value, not overwriting any previous value.
        """
        self._items.append((key, value))

    def getall(self, key):
        """
        Return a list of all values matching the key (may be an empty list)
        """
        result = []
        for k, v in self._items:
            if key == k:
                result.append(v)
        return result

    def getone(self, key):
        """
        Get one value matching the key, raising a KeyError if multiple
        values were found.
        """
        v = self.getall(key)
        if not v:
            raise KeyError('Key not found: %r' % key)
        if len(v) > 1:
            raise KeyError('Multiple values match %r: %r' % (key, v))
        return v[0]

    def mixed(self):
        """
        Returns a dictionary where the values are either single
        values, or a list of values when a key/value appears more than
        once in this dictionary.  This is similar to the kind of
        dictionary often used to represent the variables in a web
        request.
        """
        result = {}
        multi = {}
        for key, value in self._items:
            if key in result:
                # We do this to not clobber any lists that are
                # *actual* values in this dictionary:
                if key in multi:
                    result[key].append(value)
                else:
                    result[key] = [result[key], value]
                    multi[key] = None
            else:
                result[key] = value
        return result

    def dict_of_lists(self):
        """
        Returns a dictionary where each key is associated with a
        list of values.
        """
        result = {}
        for key, value in self._items:
            if key in result:
                result[key].append(value)
            else:
                result[key] = [value]
        return result

    def __delitem__(self, key):
        items = self._items
        found = False
        for i in range(len(items) - 1, -1, -1):
            if items[i][0] == key:
                del items[i]
                found = True
        if not found:
            raise KeyError(repr(key))

    def __contains__(self, key):
        for k, v in self._items:
            if k == key:
                return True
        return False

    has_key = __contains__

    def clear(self):
        self._items = []

    def copy(self):
        return MultiDict(self)

    def setdefault(self, key, default=None):
        for k, v in self._items:
            if key == k:
                return v
        self._items.append((key, default))
        return default

    def pop(self, key, *args):
        if len(args) > 1:
            raise TypeError("pop expected at most 2 arguments, got %s" %
                            (1 + len(args)))
        for i in range(len(self._items)):
            if self._items[i][0] == key:
                v = self._items[i][1]
                del self._items[i]
                return v
        if args:
            return args[0]
        else:
            raise KeyError(repr(key))

    def popitem(self):
        return self._items.pop()

    def update(self, other=None, **kwargs):
        if other is None:
            pass
        elif hasattr(other, 'items'):
            self._items.extend(other.items())
        elif hasattr(other, 'keys'):
            for k in other.keys():
                self._items.append((k, other[k]))
        else:
            for k, v in other:
                self._items.append((k, v))
        if kwargs:
            self.update(kwargs)

    def __repr__(self):
        items = ', '.join(['(%r, %r)' % v for v in self._items])
        return '%s([%s])' % (self.__class__.__name__, items)

    def __len__(self):
        return len(self._items)

    # All the iteration:

    def keys(self):
        return [k for k, v in self._items]

    def iterkeys(self):
        for k, v in self._items:
            yield k

    __iter__ = iterkeys

    def items(self):
        return self._items[:]

    def iteritems(self):
        return iter(self._items)

    def values(self):
        return [v for k, v in self._items]

    def itervalues(self):
        for k, v in self._items:
            yield v

########NEW FILE########
__FILENAME__ = node
"""
Copyright 2012 Basho Technologies, Inc.

This file is provided to you under the Apache License,
Version 2.0 (the "License"); you may not use this file
except in compliance with the License.  You may obtain
a copy of the License at

  http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on an
"AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
KIND, either express or implied.  See the License for the
specific language governing permissions and limitations
under the License.
"""
import math
import time
from threading import RLock
from riak.util import deprecated


class Decaying(object):
    """
    A float value which decays exponentially toward 0 over time. This
    is used internally to select nodes for new connections that have
    had the least errors within the recent period.
    """

    def __init__(self, p=0.0, e=math.e, r=None):
        """
        Creates a new decaying error counter.

        :param p: the initial value (defaults to 0.0)
        :type p: float
        :param e: the exponent base (defaults to math.e)
        :type e: float
        :param r: timescale factor (defaults to decaying 50% over 10
            seconds, i.e. log(0.5) / 10)
        :type r: float
        """
        self.p = p
        self.e = e
        self.r = r or (math.log(0.5) / 10)
        self.lock = RLock()
        self.t0 = time.time()

    def incr(self, d):
        """
        Increases the value by the argument.

        :param d: the value to increase by
        :type d: float
        """
        with self.lock:
            self.p = self.value() + d

    def value(self):
        """
        Returns the current value (adjusted for the time decay)

        :rtype: float
        """
        with self.lock:
            now = time.time()
            dt = now - self.t0
            self.t0 = now
            self.p = self.p * (math.pow(self.e, self.r * dt))
            return self.p


class RiakNode(object):
    """
    The internal representation of a Riak node to which the client can
    connect. Encapsulates both the configuration for the node and
    error tracking used for node-selection.
    """

    def __init__(self, host='127.0.0.1', http_port=8098, pb_port=8087,
                 **unused_args):
        """
        Creates a node.

        :param host: an IP address or hostname
        :type host: string
        :param http_port: the HTTP port of the node
        :type http_port: integer
        :param pb_port: the Protcol Buffers port of the node
        :type pb_port: integer
        """

        if 'port' in unused_args and 'already_warned_port' not in unused_args:
            deprecated("port option is deprecated, use http_port or pb_port")

        self.host = host
        self.http_port = http_port
        self.pb_port = pb_port
        self.error_rate = Decaying()

########NEW FILE########
__FILENAME__ = resolver
"""
Copyright 2013 Basho Technologies, Inc.

This file is provided to you under the Apache License,
Version 2.0 (the "License"); you may not use this file
except in compliance with the License.  You may obtain
a copy of the License at

  http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on an
"AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
KIND, either express or implied.  See the License for the
specific language governing permissions and limitations
under the License.
"""


def default_resolver(riak_object):
    """
    The default conflict-resolution function, which does nothing. To
    implement a resolver, define a function that sets the
    :attr:`siblings <riak.riak_object.RiakObject.siblings>` property
    on the passed :class:`RiakObject <riak.riak_object.RiakObject>`
    instance to a list containing a single :class:`RiakContent
    <riak.content.RiakContent>` object.

    :param riak_object: an object-in-conflict that will be resolved
    :type riak_object: :class:`RiakObject <riak.riak_object.RiakObject>`
    """
    pass


def last_written_resolver(riak_object):
    """
    A conflict-resolution function that resolves by selecting the most
    recently-modified sibling by timestamp.

    :param riak_object: an object-in-conflict that will be resolved
    :type riak_object: :class:`RiakObject <riak.riak_object.RiakObject>`
    """
    lm = lambda x: x.last_modified
    riak_object.siblings = [max(riak_object.siblings, key=lm), ]

########NEW FILE########
__FILENAME__ = riak_object
"""
Copyright 2012-2013 Basho Technologies <dev@basho.com>
Copyright 2010 Rusty Klophaus <rusty@basho.com>
Copyright 2010 Justin Sheehy <justin@basho.com>
Copyright 2009 Jay Baird <jay@mochimedia.com>

This file is provided to you under the Apache License,
Version 2.0 (the "License"); you may not use this file
except in compliance with the License.  You may obtain
a copy of the License at

  http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on an
"AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
KIND, either express or implied.  See the License for the
specific language governing permissions and limitations
under the License.
"""
from riak import ConflictError
from riak.content import RiakContent
from riak.util import deprecated
import base64


def content_property(name, doc=None):
    """
    Delegates a property to the first sibling in a RiakObject, raising
    an error when the object is in conflict.
    """
    def _setter(self, value):
        if len(self.siblings) == 0:
            # In this case, assume that what the user wants is to
            # create a new sibling inside an empty object.
            self.siblings = [RiakContent(self)]
        if len(self.siblings) != 1:
            raise ConflictError()
        setattr(self.siblings[0], name, value)

    def _getter(self):
        if len(self.siblings) == 0:
            return
        if len(self.siblings) != 1:
            raise ConflictError()
        return getattr(self.siblings[0], name)

    return property(_getter, _setter, doc=doc)


def content_method(name):
    """
    Delegates a method to the first sibling in a RiakObject, raising
    an error when the object is in conflict.
    """
    def _delegate(self, *args, **kwargs):
        if len(self.siblings) != 1:
            raise ConflictError()
        return getattr(self.siblings[0], name).__call__(*args, **kwargs)

    _delegate.__doc__ = getattr(RiakContent, name).__doc__

    return _delegate


class VClock(object):
    """
    A representation of a vector clock received from Riak.
    """

    _decoders = {
        'base64': base64.b64decode,
        'binary': str
    }

    _encoders = {
        'base64': base64.b64encode,
        'binary': str
    }

    def __init__(self, value, encoding):
        self._vclock = self._decoders[encoding].__call__(value)

    def encode(self, encoding):
        if encoding in self._encoders:
            return self._encoders[encoding].__call__(self._vclock)
        else:
            raise ValueError('{} is not a valid vector clock encoding'.
                             format(encoding))

    def __repr__(self):
        return '<{} {}>'.format(self.__class__.__name__,
                                self.encode('base64'))


class RiakObject(object):
    """
    The RiakObject holds meta information about a Riak object, plus the
    object's data.
    """
    def __init__(self, client, bucket, key=None):
        """
        Construct a new RiakObject.

        :param client: A RiakClient object.
        :type client: :class:`RiakClient <riak.client.RiakClient>`
        :param bucket: A RiakBucket object.
        :type bucket: :class:`RiakBucket <riak.bucket.RiakBucket>`
        :param key: An optional key. If not specified, then the key
         is generated by the server when :func:`store` is called.
        :type key: string
        """
        try:
            if isinstance(key, basestring):
                key = key.encode('ascii')
        except UnicodeError:
            raise TypeError('Unicode keys are not supported.')

        if key is not None and len(key) == 0:
            raise ValueError('Key name must either be "None"'
                             ' or a non-empty string.')

        self._resolver = None
        self.client = client
        self.bucket = bucket
        self.key = key
        self.vclock = None
        self.siblings = [RiakContent(self)]

    #: The list of sibling values contained in this object
    siblings = []

    def __hash__(self):
        return hash((self.key, self.bucket, self.vclock))

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return hash(self) == hash(other)
        else:
            return False

    def __ne__(self, other):
        if isinstance(other, self.__class__):
            return hash(self) != hash(other)
        else:
            return True

    data = content_property('data', doc="""
        The data stored in this object, as Python objects. For the raw
        data, use the `encoded_data` property. If unset, accessing
        this property will result in decoding the `encoded_data`
        property into Python values. The decoding is dependent on the
        `content_type` property and the bucket's registered decoders.
        """)

    encoded_data = content_property('encoded_data', doc="""
        The raw data stored in this object, essentially the encoded
        form of the `data` property. If unset, accessing this property
        will result in encoding the `data` property into a string. The
        encoding is dependent on the `content_type` property and the
        bucket's registered encoders.
        """)

    charset = content_property('charset', doc="""
        The character set of the encoded data as a string
        """)

    content_type = content_property('content_type', doc="""
        The MIME media type of the encoded data as a string
        """)

    content_encoding = content_property('content_encoding', doc="""
        The encoding (compression) of the encoded data. Valid values
        are identity, deflate, gzip
        """)

    last_modified = content_property('last_modified', """
        The UNIX timestamp of the modification time of this value.
        """)

    etag = content_property('etag', """
        A unique entity-tag for the value.
        """)

    usermeta = content_property('usermeta', doc="""
        Arbitrary user-defined metadata dict, mapping strings to strings.
        """)

    links = content_property('links', doc="""
        A set of bucket/key/tag 3-tuples representing links to other
        keys.
        """)

    indexes = content_property('indexes', doc="""
        The set of secondary index entries, consisting of
        index-name/value tuples
        """)

    get_encoded_data = content_method('get_encoded_data')
    set_encoded_data = content_method('set_encoded_data')
    add_index = content_method('add_index')
    remove_index = content_method('remove_index')
    remove_indexes = remove_index
    set_index = content_method('set_index')
    add_link = content_method('add_link')

    def _exists(self):
        if len(self.siblings) == 0:
            return False
        elif len(self.siblings) > 1:
            # Even if all of the siblings are tombstones, the object
            # essentially exists.
            return True
        else:
            return self.siblings[0].exists

    exists = property(_exists, None, doc="""
       Whether the object exists. This is only ``False`` when there
       are no siblings (the object was not found), or the solitary
       sibling is a tombstone.
       """)

    def _get_resolver(self):
        if callable(self._resolver):
            return self._resolver
        elif self._resolver is None:
            return self.bucket.resolver
        else:
            raise TypeError("resolver is not a function")

    def _set_resolver(self, value):
        if value is None or callable(value):
            self._resolver = value
        else:
            raise TypeError("resolver is not a function")

    resolver = property(_get_resolver, _set_resolver,
                        doc="""The sibling-resolution function for this
                           object. If the resolver is not set, the
                           bucket's resolver will be used.""")

    def get_sibling(self, index):
        deprecated("RiakObject.get_sibling is deprecated, use the "
                   "siblings property instead")
        return self.siblings[index]

    def store(self, w=None, dw=None, pw=None, return_body=True,
              if_none_match=False, timeout=None):
        """
        Store the object in Riak. When this operation completes, the
        object could contain new metadata and possibly new data if Riak
        contains a newer version of the object according to the object's
        vector clock.

        :param w: W-value, wait for this many partitions to respond
         before returning to client.
        :type w: integer
        :param dw: DW-value, wait for this many partitions to
         confirm the write before returning to client.
        :type dw: integer

        :param pw: PW-value, require this many primary partitions to
                   be available before performing the put
        :type pw: integer
        :param return_body: if the newly stored object should be
                            retrieved
        :type return_body: bool
        :param if_none_match: Should the object be stored only if
                              there is no key previously defined
        :type if_none_match: bool
        :param timeout: a timeout value in milliseconds
        :type timeout: int
        :rtype: :class:`RiakObject` """
        if len(self.siblings) != 1:
            raise ConflictError("Attempting to store an invalid object, "
                                "resolve the siblings first")

        self.client.put(self, w=w, dw=dw, pw=pw,
                        return_body=return_body,
                        if_none_match=if_none_match,
                        timeout=timeout)

        return self

    def reload(self, r=None, pr=None, timeout=None):
        """
        Reload the object from Riak. When this operation completes, the
        object could contain new metadata and a new value, if the object
        was updated in Riak since it was last retrieved.

        .. note:: Even if the key is not found in Riak, this will
           return a :class:`RiakObject`. Check the :attr:`exists`
           property to see if the key was found.

        :param r: R-Value, wait for this many partitions to respond
         before returning to client.
        :type r: integer
        :param pr: PR-value, require this many primary partitions to
                   be available before performing the read that
                   precedes the put
        :type pr: integer
        :param timeout: a timeout value in milliseconds
        :type timeout: int
        :rtype: :class:`RiakObject`
        """

        self.client.get(self, r=r, pr=pr, timeout=timeout)
        return self

    def delete(self, rw=None, r=None, w=None, dw=None, pr=None, pw=None,
               timeout=None):
        """
        Delete this object from Riak.

        :param rw: RW-value. Wait until this many partitions have
            deleted the object before responding. (deprecated in Riak
            1.0+, use R/W/DW)
        :type rw: integer
        :param r: R-value, wait for this many partitions to read object
         before performing the put
        :type r: integer
        :param w: W-value, wait for this many partitions to respond
         before returning to client.
        :type w: integer
        :param dw: DW-value, wait for this many partitions to
         confirm the write before returning to client.
        :type dw: integer
        :param pr: PR-value, require this many primary partitions to
                   be available before performing the read that
                   precedes the put
        :type pr: integer
        :param pw: PW-value, require this many primary partitions to
                   be available before performing the put
        :type pw: integer
        :param timeout: a timeout value in milliseconds
        :type timeout: int
        :rtype: :class:`RiakObject`
        """

        self.client.delete(self, rw=rw, r=r, w=w, dw=dw, pr=pr, pw=pw,
                           timeout=timeout)
        self.clear()
        return self

    def clear(self):
        """
        Reset this object.

        :rtype: RiakObject
        """
        self.siblings = []
        return self

    def add(self, *args):
        """
        Start assembling a Map/Reduce operation.
        A shortcut for :meth:`~riak.mapreduce.RiakMapReduce.add`.

        :rtype: :class:`~riak.mapreduce.RiakMapReduce`
        """
        mr = RiakMapReduce(self.client)
        mr.add(self.bucket.name, self.key)
        return mr.add(*args)

    def link(self, *args):
        """
        Start assembling a Map/Reduce operation.
        A shortcut for :meth:`~riak.mapreduce.RiakMapReduce.link`.

        :rtype: :class:`~riak.mapreduce.RiakMapReduce`
        """
        mr = RiakMapReduce(self.client)
        mr.add(self.bucket.name, self.key)
        return mr.link(*args)

    def map(self, *args):
        """
        Start assembling a Map/Reduce operation.
        A shortcut for :meth:`~riak.mapreduce.RiakMapReduce.map`.

        :rtype: :class:`~riak.mapreduce.RiakMapReduce`
        """
        mr = RiakMapReduce(self.client)
        mr.add(self.bucket.name, self.key)
        return mr.map(*args)

    def reduce(self, *args):
        """
        Start assembling a Map/Reduce operation.
        A shortcut for :meth:`~riak.mapreduce.RiakMapReduce.reduce`.

        :rtype: :class:`~riak.mapreduce.RiakMapReduce`
        """
        mr = RiakMapReduce(self.client)
        mr.add(self.bucket.name, self.key)
        return mr.reduce(*args)

from riak.mapreduce import RiakMapReduce

########NEW FILE########
__FILENAME__ = search
"""
Copyright 2010 Basho Technologies, Inc.

This file is provided to you under the Apache License,
Version 2.0 (the "License"); you may not use this file
except in compliance with the License.  You may obtain
a copy of the License at

  http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on an
"AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
KIND, either express or implied.  See the License for the
specific language governing permissions and limitations
under the License.
"""


class RiakSearch(object):
    """
    A wrapper around Riak Search-related client operations. See
    :func:`RiakClient.solr`.
    """

    def __init__(self, client, **unused_args):
        self._client = client

    def add(self, index, *docs):
        """
        Adds documents to a fulltext index. Shortcut and backwards
        compatibility for :func:`RiakClientOperations.fulltext_add`.
        """
        self._client.fulltext_add(index, docs=docs)

    index = add

    def delete(self, index, docs=None, queries=None):
        """
        Removes documents from a fulltext index. Shortcut and backwards
        compatibility for :func:`RiakClientOperations.fulltext_delete`.
        """
        self._client.fulltext_delete(index, docs=docs, queries=queries)

    remove = delete

    def search(self, index, query, **params):
        """
        Searches a fulltext index. Shortcut and backwards
        compatibility for :func:`RiakClientOperations.fulltext_search`.
        """
        return self._client.fulltext_search(index, query, **params)

    select = search

########NEW FILE########
__FILENAME__ = pool-grinder
#!/usr/bin/env python

from Queue import Queue
from threading import Thread
import sys
sys.path.append("../transports/")
from pool import Pool
from random import SystemRandom
from time import sleep


class SimplePool(Pool):
    def __init__(self):
        self.count = 0
        Pool.__init__(self)

    def create_resource(self):
        self.count += 1
        return [self.count]

    def destroy_resource(self, resource):
        del resource[:]


class EmptyListPool(Pool):
    def create_resource(self):
        return []


def test():
    started = Queue()
    n = 1000
    threads = []
    touched = []
    pool = EmptyListPool()
    rand = SystemRandom()

    def _run():
        psleep = rand.uniform(0.05, 0.1)
        with pool.take() as a:
            started.put(1)
            started.join()
            a.append(rand.uniform(0, 1))
            if psleep > 1:
                print psleep
            sleep(psleep)

    for i in range(n):
        th = Thread(target=_run)
        threads.append(th)
        th.start()

    for i in range(n):
        started.get()
        started.task_done()

    for element in pool:
        touched.append(element)

    for thr in threads:
        thr.join()

    if set(pool.elements) != set(touched):
        print set(pool.elements) - set(touched)
        return False
    else:
        return True

ret = True
count = 0
while ret:
    ret = test()
    count += 1
    print count


# INSTRUMENTED FUNCTION

#     def __claim_elements(self):
#         #print 'waiting for self lock'
#         with self.lock:
#             if self.__all_claimed(): # and self.unlocked:
#                 #print 'waiting on releaser lock'
#                 with self.releaser:
#                     print 'waiting for release'
#                     print 'targets', self.targets
#                     print 'tomb', self.targets[0].tomb
#                     print 'claimed', self.targets[0].claimed
#                     print self.releaser
#                     print self.lock
#                     print self.unlocked
#                     self.releaser.wait(1)
#             for element in self.targets:
#                 if element.tomb:
#                     self.targets.remove(element)
#                     #self.unlocked.remove(element)
#                     continue
#                 if not element.claimed:
#                     self.targets.remove(element)
#                     self.unlocked.append(element)
#                     element.claimed = True

########NEW FILE########
__FILENAME__ = suite
import os.path
import platform

if platform.python_version() < '2.7':
    unittest = __import__('unittest2')
else:
    import unittest


def additional_tests():
    top_level = os.path.join(os.path.dirname(__file__), "../../")
    start_dir = os.path.dirname(__file__)
    suite = unittest.TestSuite()
    suite.addTest(unittest.TestLoader().discover(start_dir,
                                                 top_level_dir=top_level))
    return suite

########NEW FILE########
__FILENAME__ = test_2i
# -*- coding: utf-8 -*-
import platform
if platform.python_version() < '2.7':
    unittest = __import__('unittest2')
else:
    import unittest

from riak import RiakError
from . import SKIP_INDEXES


class TwoITests(object):
    def is_2i_supported(self):
        # Immediate test to see if 2i is even supported w/ the backend
        try:
            self.client.get_index('foo', 'bar_bin', 'baz')
            return True
        except Exception as e:
            if "indexes_not_supported" in str(e):
                return False
            return True  # it failed, but is supported!

    @unittest.skipIf(SKIP_INDEXES, 'SKIP_INDEXES is defined')
    def test_secondary_index_store(self):
        if not self.is_2i_supported():
            raise unittest.SkipTest("2I not supported")

        # Create a new object with indexes...
        bucket = self.client.bucket(self.bucket_name)
        rand = self.randint()
        obj = bucket.new('mykey1', rand)
        obj.add_index('field1_bin', 'val1a')
        obj.add_index('field1_int', 1011)
        obj.store()

        # Retrieve the object, check that the correct indexes exist...
        obj = bucket.get('mykey1')
        self.assertEqual(['val1a'], [y for (x, y) in obj.indexes
                                     if x == 'field1_bin'])
        self.assertEqual([1011], [y for (x, y) in obj.indexes
                                  if x == 'field1_int'])

        # Add more indexes and save...
        obj.add_index('field1_bin', 'val1b')
        obj.add_index('field1_int', 1012)
        obj.store()

        # Retrieve the object, check that the correct indexes exist...
        obj = bucket.get('mykey1')
        self.assertEqual(['val1a', 'val1b'],
                         sorted([y for (x, y) in obj.indexes
                                 if x == 'field1_bin']))
        self.assertEqual([1011, 1012],
                         sorted([y for (x, y) in obj.indexes
                                 if x == 'field1_int']))

        self.assertEqual(
            [('field1_bin', 'val1a'),
             ('field1_bin', 'val1b'),
             ('field1_int', 1011),
             ('field1_int', 1012)
             ], sorted(obj.indexes))

        # Delete an index...
        obj.remove_index('field1_bin', 'val1a')
        obj.remove_index('field1_int', 1011)
        obj.store()

        # Retrieve the object, check that the correct indexes exist...
        obj = bucket.get('mykey1')
        self.assertEqual(['val1b'], sorted([y for (x, y) in obj.indexes
                                            if x == 'field1_bin']))
        self.assertEqual([1012], sorted([y for (x, y) in obj.indexes
                                         if x == 'field1_int']))

        # Check duplicate entries...
        obj.add_index('field1_bin', 'val1a')
        obj.add_index('field1_bin', 'val1a')
        obj.add_index('field1_bin', 'val1a')
        obj.add_index('field1_int', 1011)
        obj.add_index('field1_int', 1011)
        obj.add_index('field1_int', 1011)

        self.assertEqual(
            [('field1_bin', 'val1a'),
             ('field1_bin', 'val1b'),
             ('field1_int', 1011),
             ('field1_int', 1012)
             ], sorted(obj.indexes))

        obj.store()
        obj = bucket.get('mykey1')

        self.assertEqual(
            [('field1_bin', 'val1a'),
             ('field1_bin', 'val1b'),
             ('field1_int', 1011),
             ('field1_int', 1012)
             ], sorted(obj.indexes))

        # Clean up...
        bucket.get('mykey1').delete()

    @unittest.skipIf(SKIP_INDEXES, 'SKIP_INDEXES is defined')
    def test_set_indexes(self):
        if not self.is_2i_supported():
            raise unittest.SkipTest("2I not supported")

        bucket = self.client.bucket(self.bucket_name)
        foo = bucket.new('foo', 1)
        foo.indexes = set([('field1_bin', 'test'), ('field2_int', 1337)])
        foo.store()
        result = self.client.index(self.bucket_name, 'field2_int', 1337).run()

        self.assertEqual(1, len(result))
        self.assertEqual('foo', result[0][1])

        result = bucket.get_index('field1_bin', 'test')
        self.assertEqual(1, len(result))
        self.assertEqual('foo', str(result[0]))

    @unittest.skipIf(SKIP_INDEXES, 'SKIP_INDEXES is defined')
    def test_remove_indexes(self):
        if not self.is_2i_supported():
            raise unittest.SkipTest("2I not supported")

        bucket = self.client.bucket(self.bucket_name)
        bar = bucket.new('bar', 1).add_index('bar_int', 1)\
            .add_index('bar_int', 2).add_index('baz_bin', 'baz').store()
        result = bucket.get_index('bar_int', 1)
        self.assertEqual(1, len(result))
        self.assertEqual(3, len(bar.indexes))
        self.assertEqual(2, len([x for x in bar.indexes
                                 if x[0] == 'bar_int']))

        # remove all indexes
        bar = bar.remove_indexes().store()
        result = bucket.get_index('bar_int', 1)
        self.assertEqual(0, len(result))
        result = bucket.get_index('baz_bin', 'baz')
        self.assertEqual(0, len(result))
        self.assertEqual(0, len(bar.indexes))
        self.assertEqual(0, len([x for x in bar.indexes
                                 if x[0] == 'bar_int']))
        self.assertEqual(0, len([x for x in bar.indexes
                                 if x[0] == 'baz_bin']))

        # add index again
        bar = bar.add_index('bar_int', 1).add_index('bar_int', 2)\
            .add_index('baz_bin', 'baz').store()
        # remove all index with field='bar_int'
        bar = bar.remove_index(field='bar_int').store()
        result = bucket.get_index('bar_int', 1)
        self.assertEqual(0, len(result))
        result = bucket.get_index('bar_int', 2)
        self.assertEqual(0, len(result))
        result = bucket.get_index('baz_bin', 'baz')
        self.assertEqual(1, len(result))
        self.assertEqual(1, len(bar.indexes))
        self.assertEqual(0, len([x for x in bar.indexes
                                 if x[0] == 'bar_int']))
        self.assertEqual(1, len([x for x in bar.indexes
                                 if x[0] == 'baz_bin']))

        # add index again
        bar = bar.add_index('bar_int', 1).add_index('bar_int', 2)\
            .add_index('baz_bin', 'baz').store()
        # remove an index field value pair
        bar = bar.remove_index(field='bar_int', value=2).store()
        result = bucket.get_index('bar_int', 1)
        self.assertEqual(1, len(result))
        result = bucket.get_index('bar_int', 2)
        self.assertEqual(0, len(result))
        result = bucket.get_index('baz_bin', 'baz')
        self.assertEqual(1, len(result))
        self.assertEqual(2, len(bar.indexes))
        self.assertEqual(1, len([x for x in bar.indexes
                                 if x[0] == 'bar_int']))
        self.assertEqual(1, len([x for x in bar.indexes
                                 if x[0] == 'baz_bin']))

    @unittest.skipIf(SKIP_INDEXES, 'SKIP_INDEXES is defined')
    def test_secondary_index_query(self):
        if not self.is_2i_supported():
            raise unittest.SkipTest("2I not supported")

        bucket, o1, o2, o3, o4 = self._create_index_objects()

        # Test an equality query...
        results = bucket.get_index('field1_bin', 'val2')
        self.assertEquals(1, len(results))
        self.assertEquals(o2.key, str(results[0]))

        # Test a range query...
        results = bucket.get_index('field1_bin', 'val2', 'val4')
        vals = set([str(key) for key in results])
        self.assertEquals(3, len(results))
        self.assertEquals(set([o2.key, o3.key, o4.key]), vals)

        # Test an equality query...
        results = bucket.get_index('field2_int', 1002)
        self.assertEquals(1, len(results))
        self.assertEquals(o2.key, str(results[0]))

        # Test a range query...
        results = bucket.get_index('field2_int', 1002, 1004)
        vals = set([str(key) for key in results])
        self.assertEquals(3, len(results))
        self.assertEquals(set([o2.key, o3.key, o4.key]), vals)

    @unittest.skipIf(SKIP_INDEXES, 'SKIP_INDEXES is defined')
    def test_secondary_index_invalid_name(self):
        if not self.is_2i_supported():
            raise unittest.SkipTest("2I not supported")

        bucket = self.client.bucket(self.bucket_name)

        with self.assertRaises(RiakError):
            bucket.new('k', 'a').add_index('field1', 'value1')

    @unittest.skipIf(SKIP_INDEXES, 'SKIP_INDEX is defined')
    def test_set_index(self):
        if not self.is_2i_supported():
            raise unittest.SkipTest("2I not supported")

        bucket = self.client.bucket(self.bucket_name)
        obj = bucket.new('bar', 1)
        obj.set_index('bar_int', 1)
        obj.set_index('bar2_int', 1)
        self.assertEqual(2, len(obj.indexes))
        self.assertEqual(set((('bar_int', 1), ('bar2_int', 1))), obj.indexes)

        obj.set_index('bar_int', 3)
        self.assertEqual(2, len(obj.indexes))
        self.assertEqual(set((('bar_int', 3), ('bar2_int', 1))), obj.indexes)
        obj.set_index('bar2_int', 10)
        self.assertEqual(set((('bar_int', 3), ('bar2_int', 10))), obj.indexes)

    @unittest.skipIf(SKIP_INDEXES, 'SKIP_INDEX is defined')
    def test_stream_index(self):
        if not self.is_2i_supported():
            raise unittest.SkipTest("2I not supported")

        bucket, o1, o2, o3, o4 = self._create_index_objects()

        keys = []
        for entries in bucket.stream_index('field1_bin', 'val1', 'val3'):
            keys.extend(entries)

        self.assertEqual(sorted([o1.key, o2.key, o3.key]), sorted(keys))

    @unittest.skipIf(SKIP_INDEXES, 'SKIP_INDEX is defined')
    def test_index_return_terms(self):
        if not self.is_2i_supported():
            raise unittest.SkipTest("2I is not supported")

        bucket, o1, o2, o3, o4 = self._create_index_objects()

        # Test synchronous index query
        pairs = bucket.get_index('field1_bin', 'val2', 'val4',
                                 return_terms=True)

        self.assertEqual([('val2', o2.key),
                          ('val3', o3.key),
                          ('val4', o4.key)], sorted(pairs))

        # Test streaming index query
        spairs = []
        for chunk in bucket.stream_index('field2_int', 1002, 1004,
                                         return_terms=True):
            spairs.extend(chunk)

        self.assertEqual([(1002, o2.key), (1003, o3.key), (1004, o4.key)],
                         sorted(spairs))

    @unittest.skipIf(SKIP_INDEXES, 'SKIP_INDEX is defined')
    def test_index_pagination(self):
        if not self.is_2i_supported():
            raise unittest.SkipTest("2I is not supported")

        bucket, o1, o2, o3, o4 = self._create_index_objects()

        results = bucket.get_index('field1_bin', 'val0', 'val5',
                                   max_results=2)
        # Number of results =< page size
        self.assertLessEqual(2, len(results))
        # Results are in-order
        self.assertEqual([o1.key, o2.key], results)

        # Continuation/next page present when page size smaller than
        # total results size
        self.assertIsNotNone(results.continuation)
        self.assertTrue(results.has_next_page())

        # Retrieving next page gets more results
        page2 = results.next_page()
        self.assertLessEqual(2, len(page2))
        self.assertEqual([o3.key, o4.key], page2)

    @unittest.skipIf(SKIP_INDEXES, 'SKIP_INDEX is defined')
    def test_index_pagination_return_terms(self):
        if not self.is_2i_supported():
            raise unittest.SkipTest("2I is not supported")

        bucket, o1, o2, o3, o4 = self._create_index_objects()

        # ========= Above steps work for return-terms ==========
        results = bucket.get_index('field1_bin', 'val0', 'val5',
                                   max_results=2, return_terms=True)
        # Number of results =< page size
        self.assertLessEqual(2, len(results))
        # Results are in-order
        self.assertEqual([('val1', o1.key), ('val2', o2.key)], results)

        # Continuation/next page present when page size smaller than
        # total results size
        self.assertIsNotNone(results.continuation)
        self.assertTrue(results.has_next_page())

        # Retrieving next page gets more results
        page2 = results.next_page()
        self.assertLessEqual(2, len(results))
        self.assertEqual([('val3', o3.key), ('val4', o4.key)], page2)

    @unittest.skipIf(SKIP_INDEXES, 'SKIP_INDEX is defined')
    def test_index_pagination_stream(self):
        if not self.is_2i_supported():
            raise unittest.SkipTest("2I is not supported")

        bucket, o1, o2, o3, o4 = self._create_index_objects()

        # ========= Above steps work for streaming ==========
        stream = bucket.stream_index('field1_bin', 'val0', 'val5',
                                     max_results=2)
        results = []
        for result in stream:
            results.extend(result)

        # Number of results =< page size
        self.assertLessEqual(2, len(results))
        # Results are in-order
        self.assertEqual([o1.key, o2.key], results)

        # Continuation/next page present when page size smaller than
        # total results size
        self.assertIsNotNone(stream.continuation)
        self.assertTrue(stream.has_next_page())

        # Retrieving next page gets more results
        results = []
        for result in stream.next_page():
            results.extend(result)
        self.assertLessEqual(2, len(results))
        self.assertEqual([o3.key, o4.key], results)

    @unittest.skipIf(SKIP_INDEXES, 'SKIP_INDEX is defined')
    def test_index_pagination_stream_return_terms(self):
        if not self.is_2i_supported():
            raise unittest.SkipTest("2I is not supported")

        bucket, o1, o2, o3, o4 = self._create_index_objects()

        # ========= Above steps work for streaming with return-terms ==========

        stream = bucket.stream_index('field1_bin', 'val0', 'val5',
                                     max_results=2, return_terms=True)
        results = []
        for result in stream:
            results.extend(result)

        # Number of results =< page size
        self.assertLessEqual(2, len(results))
        # Results are in-order
        self.assertEqual([('val1', o1.key), ('val2', o2.key)], results)

        # Continuation/next page present when page size smaller than
        # total results size
        self.assertIsNotNone(stream.continuation)
        self.assertTrue(stream.has_next_page())

        # Retrieving next page gets more results
        results = []
        for result in stream.next_page():
            results.extend(result)
        self.assertLessEqual(2, len(results))
        self.assertEqual([('val3', o3.key), ('val4', o4.key)], results)

    @unittest.skipIf(SKIP_INDEXES, 'SKIP_INDEX is defined')
    def test_index_eq_query_return_terms(self):
        if not self.is_2i_supported():
            raise unittest.SkipTest("2I is not supported")

        bucket, o1, o2, o3, o4 = self._create_index_objects()

        results = bucket.get_index('field2_int', 1001, return_terms=True)
        self.assertEqual([(1001, o1.key)], results)

    @unittest.skipIf(SKIP_INDEXES, 'SKIP_INDEX is defined')
    def test_index_eq_query_stream_return_terms(self):
        if not self.is_2i_supported():
            raise unittest.SkipTest("2I is not supported")

        bucket, o1, o2, o3, o4 = self._create_index_objects()

        results = []
        for item in bucket.stream_index('field2_int', 1001, return_terms=True):
            results.extend(item)

        self.assertEqual([(1001, o1.key)], results)

    @unittest.skipIf(SKIP_INDEXES, 'SKIP_INDEX is defined')
    def test_index_timeout(self):
        if not self.is_2i_supported():
            raise unittest.SkipTest("2I is not supported")

        bucket, o1, o2, o3, o4 = self._create_index_objects()

        with self.assertRaises(RiakError):
            bucket.get_index('field1_bin', 'val1', timeout=1)

        with self.assertRaises(RiakError):
            for i in bucket.stream_index('field1_bin', 'val1', timeout=1):
                pass

        # This should not raise
        self.assertEqual([o1.key], bucket.get_index('field1_bin', 'val1',
                                                    timeout='infinity'))

    @unittest.skipIf(SKIP_INDEXES, 'SKIP_INDEX is defined')
    def test_index_regex(self):
        if not self.is_2i_supported():
            raise unittest.SkipTest("2I is not supported")

        bucket, o1, o2, o3, o4 = self._create_index_objects()

        results = []
        for item in bucket.stream_index('field1_bin', 'val0',
                                        'val5', term_regex='.*l2',
                                        return_terms=True):
            results.extend(item)

        self.assertEqual([('val2', o2.key)], results)

    def _create_index_objects(self):
        """
        Creates a number of index objects to be used in 2i test
        """
        bucket = self.client.bucket(self.bucket_name)

        o1 = bucket.\
            new(self.randname(), 'data1').\
            add_index('field1_bin', 'val1').\
            add_index('field2_int', 1001).\
            store()
        o2 = bucket.\
            new(self.randname(), 'data1').\
            add_index('field1_bin', 'val2').\
            add_index('field2_int', 1002).\
            store()
        o3 = bucket.\
            new(self.randname(), 'data1').\
            add_index('field1_bin', 'val3').\
            add_index('field2_int', 1003).\
            store()
        o4 = bucket.\
            new(self.randname(), 'data1').\
            add_index('field1_bin', 'val4').\
            add_index('field2_int', 1004).\
            store()

        return bucket, o1, o2, o3, o4

########NEW FILE########
__FILENAME__ = test_all
# -*- coding: utf-8 -*-
import random
import platform
from threading import Thread
from Queue import Queue

if platform.python_version() < '2.7':
    unittest = __import__('unittest2')
else:
    import unittest

from riak import RiakError
from riak.client import RiakClient
from riak.riak_object import RiakObject

from riak.tests.test_yokozuna import YZSearchTests
from riak.tests.test_search import SearchTests, \
    EnableSearchTests, SolrSearchTests
from riak.tests.test_mapreduce import MapReduceAliasTests, \
    ErlangMapReduceTests, JSMapReduceTests, LinkTests, MapReduceStreamTests
from riak.tests.test_kv import BasicKVTests, KVFileTests, \
    BucketPropsTest, CounterTests
from riak.tests.test_2i import TwoITests
from riak.tests.test_btypes import BucketTypeTests

from riak.tests import HOST, PB_HOST, PB_PORT, HTTP_HOST, HTTP_PORT, \
    HAVE_PROTO, DUMMY_HTTP_PORT, DUMMY_PB_PORT, \
    SKIP_SEARCH, RUN_YZ

testrun_search_bucket = None
testrun_props_bucket = None
testrun_sibs_bucket = None
testrun_yz_bucket = None


def setUpModule():
    global testrun_search_bucket, testrun_props_bucket, \
        testrun_sibs_bucket, testrun_yz_bucket

    c = RiakClient(protocol='http', host=HTTP_HOST, http_port=HTTP_PORT,
                   pb_port=PB_PORT)

    testrun_props_bucket = 'propsbucket'
    testrun_sibs_bucket = 'sibsbucket'
    c.bucket(testrun_sibs_bucket).allow_mult = True

    if (not SKIP_SEARCH and not RUN_YZ):
        testrun_search_bucket = 'searchbucket'
        b = c.bucket(testrun_search_bucket)
        b.enable_search()

    if RUN_YZ:
        c.protocol = 'pbc'
        testrun_yz_bucket = 'yzbucket'
        c.create_search_index(testrun_yz_bucket)
        b = c.bucket(testrun_yz_bucket)
        index_set = False
        while not index_set:
            try:
                b.set_property('search_index', testrun_yz_bucket)
                index_set = True
            except RiakError:
                pass


def tearDownModule():
    global testrun_search_bucket, testrun_props_bucket, \
        testrun_sibs_bucket, testrun_yz_bucket

    c = RiakClient(protocol='http', host=HTTP_HOST, http_port=HTTP_PORT,
                   pb_port=PB_PORT)

    c.bucket(testrun_sibs_bucket).clear_properties()
    c.bucket(testrun_props_bucket).clear_properties()

    if not SKIP_SEARCH and not RUN_YZ:
        b = c.bucket(testrun_search_bucket)
        b.clear_properties()

    if RUN_YZ:
        c.protocol = 'pbc'
        yzbucket = c.bucket(testrun_yz_bucket)
        yzbucket.set_property('search_index', '_dont_index_')
        c.delete_search_index(testrun_yz_bucket)
        for keys in yzbucket.stream_keys():
            for key in keys:
                yzbucket.delete(key)


class BaseTestCase(object):

    host = None
    pb_port = None
    http_port = None

    @staticmethod
    def randint():
        return random.randint(1, 999999)

    @staticmethod
    def randname(length=12):
        out = ''
        for i in range(length):
            out += chr(random.randint(ord('a'), ord('z')))
        return out

    def create_client(self, host=None, http_port=None, pb_port=None,
                      protocol=None, **client_args):
        host = host or self.host or HOST
        http_port = http_port or self.http_port or HTTP_PORT
        pb_port = pb_port or self.pb_port or PB_PORT
        protocol = protocol or self.protocol
        return RiakClient(protocol=protocol,
                          host=host,
                          http_port=http_port,
                          pb_port=pb_port, **client_args)

    def setUp(self):
        self.bucket_name = self.randname()
        self.key_name = self.randname()
        self.search_bucket = testrun_search_bucket
        self.sibs_bucket = testrun_sibs_bucket
        self.props_bucket = testrun_props_bucket
        self.yz_bucket = testrun_yz_bucket

        self.client = self.create_client()


class ClientTests(object):
    def test_request_retries(self):
        # We guess at some ports that will be unused by Riak or
        # anything else.
        client = self.create_client(http_port=DUMMY_HTTP_PORT,
                                    pb_port=DUMMY_PB_PORT)

        # If retries are exhausted, the final result should also be an
        # error.
        self.assertRaises(IOError, client.ping)

    def test_request_retries_configurable(self):
        # We guess at some ports that will be unused by Riak or
        # anything else.
        client = self.create_client(http_port=DUMMY_HTTP_PORT,
                                    pb_port=DUMMY_PB_PORT)

        # Change the retry count
        client.retries = 10
        self.assertEqual(10, client.retries)

        # The retry count should be a thread local
        retries = Queue()

        def _target():
            retries.put(client.retries)
            retries.join()

        th = Thread(target=_target)
        th.start()
        self.assertEqual(3, retries.get(block=True))
        retries.task_done()
        th.join()

        # Modify the retries in a with statement
        with client.retry_count(5):
            self.assertEqual(5, client.retries)
            self.assertRaises(IOError, client.ping)

    def test_timeout_validation(self):
        bucket = self.client.bucket(self.bucket_name)
        key = self.key_name
        obj = bucket.new(key)
        for bad in [0, -1, False, "foo"]:
            with self.assertRaises(ValueError):
                self.client.get_buckets(timeout=bad)

            with self.assertRaises(ValueError):
                for i in self.client.stream_buckets(timeout=bad):
                    pass

            with self.assertRaises(ValueError):
                self.client.get_keys(bucket, timeout=bad)

            with self.assertRaises(ValueError):
                for i in self.client.stream_keys(bucket, timeout=bad):
                    pass

            with self.assertRaises(ValueError):
                self.client.put(obj, timeout=bad)

            with self.assertRaises(ValueError):
                self.client.get(obj, timeout=bad)

            with self.assertRaises(ValueError):
                self.client.delete(obj, timeout=bad)

            with self.assertRaises(ValueError):
                self.client.mapred([], [], bad)

            with self.assertRaises(ValueError):
                for i in self.client.stream_mapred([], [], bad):
                    pass

            with self.assertRaises(ValueError):
                self.client.get_index(bucket, 'field1_bin', 'val1', 'val4',
                                      timeout=bad)

            with self.assertRaises(ValueError):
                for i in self.client.stream_index(bucket, 'field1_bin', 'val1',
                                                  'val4', timeout=bad):
                    pass

    def test_multiget_bucket(self):
        """
        Multiget operations can be invoked on buckets.
        """
        keys = [self.key_name, self.randname(), self.randname()]
        for key in keys:
            self.client.bucket(self.bucket_name)\
                .new(key, encoded_data=key, content_type="text/plain")\
                .store()
        results = self.client.bucket(self.bucket_name).multiget(keys)
        for obj in results:
            self.assertIsInstance(obj, RiakObject)
            self.assertTrue(obj.exists)
            self.assertEqual(obj.key, obj.encoded_data)

    def test_multiget_errors(self):
        """
        Unrecoverable errors are captured along with the bucket/key
        and not propagated.
        """
        keys = [self.key_name, self.randname(), self.randname()]
        client = self.create_client(http_port=DUMMY_HTTP_PORT,
                                    pb_port=DUMMY_PB_PORT)
        results = client.bucket(self.bucket_name).multiget(keys)
        for failure in results:
            self.assertIsInstance(failure, tuple)
            self.assertEqual(failure[0], self.bucket_name)
            self.assertIn(failure[1], keys)
            self.assertIsInstance(failure[2], StandardError)

    def test_multiget_notfounds(self):
        """
        Not founds work in multiget just the same as get.
        """
        keys = [(self.bucket_name, self.key_name),
                (self.bucket_name, self.randname())]
        results = self.client.multiget(keys)
        for obj in results:
            self.assertIsInstance(obj, RiakObject)
            self.assertFalse(obj.exists)

    def test_pool_close(self):
        """
        Iterate over the connection pool and close all connections.
        """
        # Do something to add to the connection pool
        self.test_multiget_bucket()
        if self.client.protocol == 'pbc':
            self.assertGreater(len(self.client._pb_pool.elements), 1)
        else:
            self.assertGreater(len(self.client._http_pool.elements), 1)
        # Now close them all up
        self.client.close()
        self.assertEqual(len(self.client._http_pool.elements), 0)
        self.assertEqual(len(self.client._pb_pool.elements), 0)

class RiakPbcTransportTestCase(BasicKVTests,
                               KVFileTests,
                               BucketPropsTest,
                               TwoITests,
                               LinkTests,
                               ErlangMapReduceTests,
                               JSMapReduceTests,
                               MapReduceAliasTests,
                               MapReduceStreamTests,
                               EnableSearchTests,
                               SearchTests,
                               YZSearchTests,
                               ClientTests,
                               CounterTests,
                               BucketTypeTests,
                               BaseTestCase,
                               unittest.TestCase):

    def setUp(self):
        if not HAVE_PROTO:
            self.skipTest('protobuf is unavailable')
        self.host = PB_HOST
        self.pb_port = PB_PORT
        self.protocol = 'pbc'
        super(RiakPbcTransportTestCase, self).setUp()

    def test_uses_client_id_if_given(self):
        zero_client_id = "\0\0\0\0"
        c = self.create_client(client_id=zero_client_id)
        self.assertEqual(zero_client_id, c.client_id)


class RiakHttpTransportTestCase(BasicKVTests,
                                KVFileTests,
                                BucketPropsTest,
                                TwoITests,
                                LinkTests,
                                ErlangMapReduceTests,
                                JSMapReduceTests,
                                MapReduceAliasTests,
                                MapReduceStreamTests,
                                EnableSearchTests,
                                SolrSearchTests,
                                SearchTests,
                                YZSearchTests,
                                ClientTests,
                                CounterTests,
                                BucketTypeTests,
                                BaseTestCase,
                                unittest.TestCase):

    def setUp(self):
        self.host = HTTP_HOST
        self.http_port = HTTP_PORT
        self.protocol = 'http'
        super(RiakHttpTransportTestCase, self).setUp()

    def test_no_returnbody(self):
        bucket = self.client.bucket(self.bucket_name)
        o = bucket.new(self.key_name, "bar").store(return_body=False)
        self.assertEqual(o.vclock, None)

    def test_too_many_link_headers_shouldnt_break_http(self):
        bucket = self.client.bucket(self.bucket_name)
        o = bucket.new("lots_of_links", "My god, it's full of links!")
        for i in range(0, 400):
            link = ("other", "key%d" % i, "next")
            o.add_link(link)

        o.store()
        stored_object = bucket.get("lots_of_links")
        self.assertEqual(len(stored_object.links), 400)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_btypes
import platform

if platform.python_version() < '2.7':
    unittest = __import__('unittest2')
else:
    import unittest

from . import SKIP_BTYPES
from riak.bucket import RiakBucket, BucketType
from riak import RiakError


class BucketTypeTests(object):
    def test_btype_init(self):
        btype = self.client.bucket_type('foo')
        self.assertIsInstance(btype, BucketType)
        self.assertEqual('foo', btype.name)
        self.assertIs(btype, self.client.bucket_type('foo'))

    def test_btype_get_bucket(self):
        btype = self.client.bucket_type('foo')
        bucket = btype.bucket(self.bucket_name)
        self.assertIsInstance(bucket, RiakBucket)
        self.assertIs(btype, bucket.bucket_type)
        self.assertIs(bucket,
                      self.client.bucket_type('foo').bucket(self.bucket_name))
        self.assertIsNot(bucket, self.client.bucket(self.bucket_name))

    def test_btype_default(self):
        defbtype = self.client.bucket_type('default')
        othertype = self.client.bucket_type('foo')
        self.assertTrue(defbtype.is_default())
        self.assertFalse(othertype.is_default())

    def test_btype_repr(self):
        defbtype = self.client.bucket_type("default")
        othertype = self.client.bucket_type("foo")
        self.assertEqual("<BucketType 'default'>", str(defbtype))
        self.assertEqual("<BucketType 'foo'>", str(othertype))
        self.assertEqual("<BucketType 'default'>", repr(defbtype))
        self.assertEqual("<BucketType 'foo'>", repr(othertype))

    @unittest.skipIf(SKIP_BTYPES == '1', "SKIP_BTYPES is set")
    def test_btype_get_props(self):
        defbtype = self.client.bucket_type("default")
        btype = self.client.bucket_type("pytest")
        with self.assertRaises(ValueError):
            defbtype.get_properties()

        props = btype.get_properties()
        self.assertIsInstance(props, dict)
        self.assertIn('n_val', props)
        self.assertEqual(3, props['n_val'])

    @unittest.skipIf(SKIP_BTYPES == '1', "SKIP_BTYPES is set")
    def test_btype_set_props(self):
        defbtype = self.client.bucket_type("default")
        btype = self.client.bucket_type("pytest")
        with self.assertRaises(ValueError):
            defbtype.set_properties({'allow_mult': True})

        oldprops = btype.get_properties()
        try:
            btype.set_properties({'allow_mult': True})
            newprops = btype.get_properties()
            self.assertIsInstance(newprops, dict)
            self.assertIn('allow_mult', newprops)
            self.assertTrue(newprops['allow_mult'])
            if 'claimant' in oldprops:  # HTTP hack
                del oldprops['claimant']
        finally:
            btype.set_properties(oldprops)

    @unittest.skipIf(SKIP_BTYPES == '1', "SKIP_BTYPES is set")
    def test_btype_set_props_immutable(self):
        btype = self.client.bucket_type("pytest-maps")
        with self.assertRaises(RiakError):
            btype.set_property('datatype', 'counter')

    @unittest.skipIf(SKIP_BTYPES == '1', "SKIP_BTYPES is set")
    def test_btype_list_buckets(self):
        btype = self.client.bucket_type("pytest")
        bucket = btype.bucket(self.bucket_name)
        obj = bucket.new(self.key_name)
        obj.data = [1, 2, 3]
        obj.store()

        self.assertIn(bucket, btype.get_buckets())
        buckets = []
        for nested_buckets in btype.stream_buckets():
            buckets.extend(nested_buckets)

        self.assertIn(bucket, buckets)

    @unittest.skipIf(SKIP_BTYPES == '1', "SKIP_BTYPES is set")
    def test_btype_list_keys(self):
        btype = self.client.bucket_type("pytest")
        bucket = btype.bucket(self.bucket_name)

        obj = bucket.new(self.key_name)
        obj.data = [1, 2, 3]
        obj.store()

        self.assertIn(self.key_name, bucket.get_keys())
        keys = []
        for keylist in bucket.stream_keys():
            keys.extend(keylist)

        self.assertIn(self.key_name, keys)

    @unittest.skipIf(SKIP_BTYPES == '1', "SKIP_BTYPES is set")
    def test_default_btype_list_buckets(self):
        default_btype = self.client.bucket_type("default")
        bucket = default_btype.bucket(self.bucket_name)
        obj = bucket.new(self.key_name)
        obj.data = [1, 2, 3]
        obj.store()

        self.assertIn(bucket, default_btype.get_buckets())
        buckets = []
        for nested_buckets in default_btype.stream_buckets():
            buckets.extend(nested_buckets)

        self.assertIn(bucket, buckets)

        self.assertItemsEqual(buckets, self.client.get_buckets())

    @unittest.skipIf(SKIP_BTYPES == '1', "SKIP_BTYPES is set")
    def test_default_btype_list_keys(self):
        btype = self.client.bucket_type("default")
        bucket = btype.bucket(self.bucket_name)

        obj = bucket.new(self.key_name)
        obj.data = [1, 2, 3]
        obj.store()

        self.assertIn(self.key_name, bucket.get_keys())
        keys = []
        for keylist in bucket.stream_keys():
            keys.extend(keylist)

        self.assertIn(self.key_name, keys)

        oldapikeys = self.client.get_keys(self.client.bucket(self.bucket_name))
        self.assertItemsEqual(keys, oldapikeys)

########NEW FILE########
__FILENAME__ = test_comparison
import platform

if platform.python_version() < '2.7':
    unittest = __import__('unittest2')
else:
    import unittest

from riak.riak_object import RiakObject
from riak.bucket import RiakBucket, BucketType
from riak.tests.test_all import BaseTestCase


class BucketTypeRichComparisonTest(unittest.TestCase):
    def test_btype_eq(self):
        a = BucketType('client', 'a')
        b = BucketType('client', 'a')
        c = BucketType(None, 'a')
        d = BucketType(None, 'a')
        self.assertEqual(a, b)
        self.assertEqual(c, d)

    def test_btype_nq(self):
        a = BucketType('client', 'a')
        b = BucketType('client', 'b')
        c = BucketType(None, 'a')
        d = BucketType(None, 'a')
        self.assertNotEqual(a, b, "matched with different name, same client")
        self.assertNotEqual(a, c, "matched with different client, same name")
        self.assertNotEqual(b, d, "matched with nothing in common")

    def test_btype_hash(self):
        a = BucketType('client', 'a')
        b = BucketType('client', 'a')
        c = BucketType('client', 'c')
        d = BucketType('client2', 'a')
        self.assertEqual(hash(a), hash(b),
                         'same bucket type has different hashes')
        self.assertNotEqual(hash(a), hash(c),
                            'different bucket has same hash')
        self.assertNotEqual(hash(a), hash(d),
                            'same bucket type, different client has same hash')


class RiakBucketRichComparisonTest(unittest.TestCase):
    def test_bucket_eq(self):
        default_bt = BucketType(None, "default")
        foo_bt = BucketType(None, "foo")
        a = RiakBucket('client', 'a', default_bt)
        b = RiakBucket('client', 'a', default_bt)
        c = RiakBucket('client', 'a', foo_bt)
        d = RiakBucket('client', 'a', foo_bt)
        self.assertEqual(a, b)
        self.assertEqual(c, d)

    def test_bucket_nq(self):
        default_bt = BucketType(None, "default")
        foo_bt = BucketType(None, "foo")
        a = RiakBucket('client', 'a', default_bt)
        b = RiakBucket('client', 'b', default_bt)
        c = RiakBucket('client', 'a', foo_bt)
        self.assertNotEqual(a, b, 'matched with a different bucket')
        self.assertNotEqual(a, c, 'matched with a different bucket type')

    def test_bucket_hash(self):
        default_bt = BucketType(None, "default")
        foo_bt = BucketType(None, "foo")
        a = RiakBucket('client', 'a', default_bt)
        b = RiakBucket('client', 'a', default_bt)
        c = RiakBucket('client', 'c', default_bt)
        d = RiakBucket('client', 'a', foo_bt)
        self.assertEqual(hash(a), hash(b),
                         'same bucket has different hashes')
        self.assertNotEqual(hash(a), hash(c),
                            'different bucket has same hash')
        self.assertNotEqual(hash(a), hash(d),
                            'same bucket, different bucket type has same hash')


class RiakObjectComparisonTest(unittest.TestCase):
    def test_object_eq(self):
        a = RiakObject(None, 'bucket', 'key')
        b = RiakObject(None, 'bucket', 'key')
        self.assertEqual(a, b)
        default_bt = BucketType(None, "default")
        bucket_a = RiakBucket('client', 'a', default_bt)
        bucket_b = RiakBucket('client', 'a', default_bt)
        c = RiakObject(None, bucket_a, 'key')
        d = RiakObject(None, bucket_b, 'key')
        self.assertEqual(c, d)

    def test_object_nq(self):
        a = RiakObject(None, 'bucket', 'key')
        b = RiakObject(None, 'bucket', 'not key')
        c = RiakObject(None, 'not bucket', 'key')
        self.assertNotEqual(a, b, 'matched with different keys')
        self.assertNotEqual(a, c, 'matched with different buckets')
        default_bt = BucketType(None, "default")
        foo_bt = BucketType(None, "foo")
        bucket_a = RiakBucket('client', 'a', default_bt)
        bucket_b = RiakBucket('client', 'a', foo_bt)
        c = RiakObject(None, bucket_a, 'key')
        d = RiakObject(None, bucket_b, 'key')
        self.assertNotEqual(c, d)

    def test_object_hash(self):
        a = RiakObject(None, 'bucket', 'key')
        b = RiakObject(None, 'bucket', 'key')
        c = RiakObject(None, 'bucket', 'not key')
        self.assertEqual(hash(a), hash(b), 'same object has different hashes')
        self.assertNotEqual(hash(a), hash(c), 'different object has same hash')

        default_bt = BucketType(None, "default")
        foo_bt = BucketType(None, "foo")
        bucket_a = RiakBucket('client', 'a', default_bt)
        bucket_b = RiakBucket('client', 'a', foo_bt)
        d = RiakObject(None, bucket_a, 'key')
        e = RiakObject(None, bucket_a, 'key')
        f = RiakObject(None, bucket_b, 'key')
        g = RiakObject(None, bucket_b, 'not key')
        self.assertEqual(hash(d), hash(e),
                         'same object, same bucket_type has different hashes')
        self.assertNotEqual(hash(e), hash(f),
                            'same object, different bucket type has the '
                            'same hash')
        self.assertNotEqual(hash(d), hash(g),
                            'different object, different bucket '
                            'type has same hash')

    def test_object_valid_key(self):
        a = RiakObject(None, 'bucket', 'key')
        self.assertIsInstance(a, RiakObject, 'valid key name is rejected')
        try:
            b = RiakObject(None, 'bucket', '')
        except ValueError:
            b = None
        self.assertIsNone(b, 'empty object key not allowed')


class RiakClientComparisonTest(unittest.TestCase, BaseTestCase):
    def test_client_eq(self):
        self.protocol = 'http'
        a = self.create_client(host='host1', http_port=11)
        b = self.create_client(host='host1', http_port=11)
        self.assertEqual(a, b)

    def test_client_nq(self):
        self.protocol = 'http'
        a = self.create_client(host='host1', http_port=11)
        b = self.create_client(host='host2', http_port=11)
        c = self.create_client(host='host1', http_port=12)
        self.assertNotEqual(a, b, 'matched with different hosts')
        self.assertNotEqual(a, c, 'matched with different ports')

    def test_client_hash(self):
        self.protocol = 'http'
        a = self.create_client(host='host1', http_port=11)
        b = self.create_client(host='host1', http_port=11)
        c = self.create_client(host='host2', http_port=11)
        self.assertEqual(hash(a), hash(b), 'same object has different hashes')
        self.assertNotEqual(hash(a), hash(c), 'different object has same hash')

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_feature_detection
"""
Copyright 2012-2014 Basho Technologies, Inc.

This file is provided to you under the Apache License,
Version 2.0 (the "License"); you may not use this file
except in compliance with the License.  You may obtain
a copy of the License at

  http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on an
"AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
KIND, either express or implied.  See the License for the
specific language governing permissions and limitations
under the License.
"""

import platform

if platform.python_version() < '2.7':
    unittest = __import__('unittest2')
else:
    import unittest

from riak.transports.feature_detect import FeatureDetection


class IncompleteTransport(FeatureDetection):
    pass


class DummyTransport(FeatureDetection):
    def __init__(self, version):
        self._version = version

    def _server_version(self):
        return self._version


class FeatureDetectionTest(unittest.TestCase):
    def test_implements_server_version(self):
        t = IncompleteTransport()

        with self.assertRaises(NotImplementedError):
            t.server_version

    def test_pre_10(self):
        t = DummyTransport("0.14.2")
        self.assertFalse(t.phaseless_mapred())
        self.assertFalse(t.pb_indexes())
        self.assertFalse(t.pb_search())
        self.assertFalse(t.pb_conditionals())
        self.assertFalse(t.quorum_controls())
        self.assertFalse(t.tombstone_vclocks())
        self.assertFalse(t.pb_head())
        self.assertFalse(t.pb_clear_bucket_props())
        self.assertFalse(t.pb_all_bucket_props())
        self.assertFalse(t.counters())
        self.assertFalse(t.stream_indexes())
        self.assertFalse(t.index_term_regex())
        self.assertFalse(t.bucket_types())

    def test_10(self):
        t = DummyTransport("1.0.3")
        self.assertFalse(t.phaseless_mapred())
        self.assertFalse(t.pb_indexes())
        self.assertFalse(t.pb_search())
        self.assertTrue(t.pb_conditionals())
        self.assertTrue(t.quorum_controls())
        self.assertTrue(t.tombstone_vclocks())
        self.assertTrue(t.pb_head())
        self.assertFalse(t.pb_clear_bucket_props())
        self.assertFalse(t.pb_all_bucket_props())
        self.assertFalse(t.counters())
        self.assertFalse(t.stream_indexes())
        self.assertFalse(t.index_term_regex())
        self.assertFalse(t.bucket_types())

    def test_11(self):
        t = DummyTransport("1.1.4")
        self.assertTrue(t.phaseless_mapred())
        self.assertFalse(t.pb_indexes())
        self.assertFalse(t.pb_search())
        self.assertTrue(t.pb_conditionals())
        self.assertTrue(t.quorum_controls())
        self.assertTrue(t.tombstone_vclocks())
        self.assertTrue(t.pb_head())
        self.assertFalse(t.pb_clear_bucket_props())
        self.assertFalse(t.pb_all_bucket_props())
        self.assertFalse(t.counters())
        self.assertFalse(t.stream_indexes())
        self.assertFalse(t.index_term_regex())
        self.assertFalse(t.bucket_types())

    def test_12(self):
        t = DummyTransport("1.2.0")
        self.assertTrue(t.phaseless_mapred())
        self.assertTrue(t.pb_indexes())
        self.assertTrue(t.pb_search())
        self.assertTrue(t.pb_conditionals())
        self.assertTrue(t.quorum_controls())
        self.assertTrue(t.tombstone_vclocks())
        self.assertTrue(t.pb_head())
        self.assertFalse(t.pb_clear_bucket_props())
        self.assertFalse(t.pb_all_bucket_props())
        self.assertFalse(t.counters())
        self.assertFalse(t.stream_indexes())
        self.assertFalse(t.index_term_regex())
        self.assertFalse(t.bucket_types())

    def test_12_loose(self):
        t = DummyTransport("1.2.1p3")
        self.assertTrue(t.phaseless_mapred())
        self.assertTrue(t.pb_indexes())
        self.assertTrue(t.pb_search())
        self.assertTrue(t.pb_conditionals())
        self.assertTrue(t.quorum_controls())
        self.assertTrue(t.tombstone_vclocks())
        self.assertTrue(t.pb_head())
        self.assertFalse(t.pb_clear_bucket_props())
        self.assertFalse(t.pb_all_bucket_props())
        self.assertFalse(t.counters())
        self.assertFalse(t.stream_indexes())
        self.assertFalse(t.index_term_regex())
        self.assertFalse(t.bucket_types())

    def test_14(self):
        t = DummyTransport("1.4.0rc1")
        self.assertTrue(t.phaseless_mapred())
        self.assertTrue(t.pb_indexes())
        self.assertTrue(t.pb_search())
        self.assertTrue(t.pb_conditionals())
        self.assertTrue(t.quorum_controls())
        self.assertTrue(t.tombstone_vclocks())
        self.assertTrue(t.pb_head())
        self.assertTrue(t.pb_clear_bucket_props())
        self.assertTrue(t.pb_all_bucket_props())
        self.assertTrue(t.counters())
        self.assertTrue(t.stream_indexes())
        self.assertFalse(t.index_term_regex())
        self.assertFalse(t.bucket_types())

    def test_144(self):
        t = DummyTransport("1.4.6")
        self.assertTrue(t.phaseless_mapred())
        self.assertTrue(t.pb_indexes())
        self.assertTrue(t.pb_search())
        self.assertTrue(t.pb_conditionals())
        self.assertTrue(t.quorum_controls())
        self.assertTrue(t.tombstone_vclocks())
        self.assertTrue(t.pb_head())
        self.assertTrue(t.pb_clear_bucket_props())
        self.assertTrue(t.pb_all_bucket_props())
        self.assertTrue(t.counters())
        self.assertTrue(t.stream_indexes())
        self.assertTrue(t.index_term_regex())
        self.assertFalse(t.bucket_types())

    def test_20(self):
        t = DummyTransport("2.0.1")
        self.assertTrue(t.phaseless_mapred())
        self.assertTrue(t.pb_indexes())
        self.assertTrue(t.pb_search())
        self.assertTrue(t.pb_conditionals())
        self.assertTrue(t.quorum_controls())
        self.assertTrue(t.tombstone_vclocks())
        self.assertTrue(t.pb_head())
        self.assertTrue(t.pb_clear_bucket_props())
        self.assertTrue(t.pb_all_bucket_props())
        self.assertTrue(t.counters())
        self.assertTrue(t.stream_indexes())
        self.assertTrue(t.index_term_regex())
        self.assertTrue(t.bucket_types())

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_filters
import platform
from riak.mapreduce import RiakKeyFilter
from riak import key_filter

if platform.python_version() < '2.7':
    unittest = __import__('unittest2')
else:
    import unittest


class FilterTests(unittest.TestCase):
    def test_simple(self):
        f1 = RiakKeyFilter("tokenize", "-", 1)
        self.assertEqual(f1._filters, [["tokenize", "-", 1]])

    def test_add(self):
        f1 = RiakKeyFilter("tokenize", "-", 1)
        f2 = RiakKeyFilter("eq", "2005")
        f3 = f1 + f2
        self.assertEqual(list(f3), [["tokenize", "-", 1], ["eq", "2005"]])

    def test_and(self):
        f1 = RiakKeyFilter("starts_with", "2005-")
        f2 = RiakKeyFilter("ends_with", "-01")
        f3 = f1 & f2
        self.assertEqual(list(f3),
                         [["and",
                           [["starts_with", "2005-"]],
                           [["ends_with", "-01"]]]])

    def test_multi_and(self):
        f1 = RiakKeyFilter("starts_with", "2005-")
        f2 = RiakKeyFilter("ends_with", "-01")
        f3 = RiakKeyFilter("matches", "-11-")
        f4 = f1 & f2 & f3
        self.assertEqual(list(f4), [["and",
                                     [["starts_with", "2005-"]],
                                     [["ends_with", "-01"]],
                                     [["matches", "-11-"]],
                                     ]])

    def test_or(self):
        f1 = RiakKeyFilter("starts_with", "2005-")
        f2 = RiakKeyFilter("ends_with", "-01")
        f3 = f1 | f2
        self.assertEqual(list(f3), [["or", [["starts_with", "2005-"]],
                                     [["ends_with", "-01"]]]])

    def test_multi_or(self):
        f1 = RiakKeyFilter("starts_with", "2005-")
        f2 = RiakKeyFilter("ends_with", "-01")
        f3 = RiakKeyFilter("matches", "-11-")
        f4 = f1 | f2 | f3
        self.assertEqual(list(f4), [["or",
                                     [["starts_with", "2005-"]],
                                     [["ends_with", "-01"]],
                                     [["matches", "-11-"]],
                                     ]])

    def test_chaining(self):
        f1 = key_filter.tokenize("-", 1).eq("2005")
        f2 = key_filter.tokenize("-", 2).eq("05")
        f3 = f1 & f2
        self.assertEqual(list(f3), [["and",
                                     [["tokenize", "-", 1], ["eq", "2005"]],
                                     [["tokenize", "-", 2], ["eq", "05"]]
                                     ]])

########NEW FILE########
__FILENAME__ = test_kv
# -*- coding: utf-8 -*-
import os
import cPickle
import copy
import platform
from time import sleep
from riak import ConflictError, RiakBucket, RiakError
from riak.resolver import default_resolver, last_written_resolver
try:
    import simplejson as json
except ImportError:
    import json

if platform.python_version() < '2.7':
    unittest = __import__('unittest2')
else:
    import unittest

from . import SKIP_RESOLVE


class NotJsonSerializable(object):

    def __init__(self, *args, **kwargs):
        self.args = list(args)
        self.kwargs = kwargs

    def __eq__(self, other):
        if len(self.args) != len(other.args):
            return False
        if len(self.kwargs) != len(other.kwargs):
            return False
        for name, value in self.kwargs.items():
            if other.kwargs[name] != value:
                return False
        value1_args = copy.copy(self.args)
        value2_args = copy.copy(other.args)
        value1_args.sort()
        value2_args.sort()
        for i in xrange(len(value1_args)):
            if value1_args[i] != value2_args[i]:
                return False
        return True


class BasicKVTests(object):
    def test_is_alive(self):
        self.assertTrue(self.client.is_alive())

    def test_store_and_get(self):
        bucket = self.client.bucket(self.bucket_name)
        rand = self.randint()
        obj = bucket.new('foo', rand)
        obj.store()
        obj = bucket.get('foo')
        self.assertTrue(obj.exists)
        self.assertEqual(obj.bucket.name, self.bucket_name)
        self.assertEqual(obj.key, 'foo')
        self.assertEqual(obj.data, rand)

        # unicode objects are fine, as long as they don't
        # contain any non-ASCII chars
        self.client.bucket(unicode(self.bucket_name))
        self.assertRaises(TypeError, self.client.bucket, u'búcket')
        self.assertRaises(TypeError, self.client.bucket, 'búcket')

        bucket.get(u'foo')
        self.assertRaises(TypeError, bucket.get, u'føø')
        self.assertRaises(TypeError, bucket.get, 'føø')

        self.assertRaises(TypeError, bucket.new, u'foo', 'éå')
        self.assertRaises(TypeError, bucket.new, u'foo', 'éå')
        self.assertRaises(TypeError, bucket.new, 'foo', u'éå')
        self.assertRaises(TypeError, bucket.new, 'foo', u'éå')

        obj2 = bucket.new('baz', rand, 'application/json')
        obj2.charset = 'UTF-8'
        obj2.store()
        obj2 = bucket.get('baz')
        self.assertEqual(obj2.data, rand)

    def test_store_obj_with_unicode(self):
        bucket = self.client.bucket(self.bucket_name)
        data = {u'føø': u'éå'}
        obj = bucket.new('foo', data)
        obj.store()
        obj = bucket.get('foo')
        self.assertEqual(obj.data, data)

    def test_store_unicode_string(self):
        bucket = self.client.bucket(self.bucket_name)
        data = u"some unicode data: \u00c6"
        obj = bucket.new(self.key_name, encoded_data=data.encode('utf-8'),
                         content_type='text/plain')
        obj.charset = 'utf-8'
        obj.store()
        obj2 = bucket.get(self.key_name)
        self.assertEqual(data, obj2.encoded_data.decode('utf-8'))

    def test_string_bucket_name(self):
        # Things that are not strings cannot be bucket names
        for bad in (12345, True, None, {}, []):
            with self.assertRaisesRegexp(TypeError, 'must be a string'):
                self.client.bucket(bad)

            with self.assertRaisesRegexp(TypeError, 'must be a string'):
                RiakBucket(self.client, bad, None)

        # Unicode bucket names are not supported, if they can't be
        # encoded to ASCII. This should be changed in a future
        # release.
        with self.assertRaisesRegexp(TypeError,
                                     'Unicode bucket names are not supported'):
            self.client.bucket(u'føø')

        # This is fine, since it's already ASCII
        self.client.bucket('ASCII')

    def test_generate_key(self):
        # Ensure that Riak generates a random key when
        # the key passed to bucket.new() is None.
        bucket = self.client.bucket('random_key_bucket')
        existing_keys = bucket.get_keys()
        o = bucket.new(None, data={})
        self.assertIsNone(o.key)
        o.store()
        self.assertIsNotNone(o.key)
        self.assertNotIn('/', o.key)
        self.assertNotIn(o.key, existing_keys)
        self.assertEqual(len(bucket.get_keys()), len(existing_keys) + 1)

    def test_stream_keys(self):
        bucket = self.client.bucket('random_key_bucket')
        regular_keys = bucket.get_keys()
        self.assertNotEqual(len(regular_keys), 0)
        streamed_keys = []
        for keylist in bucket.stream_keys():
            self.assertNotEqual([], keylist)
            for key in keylist:
                self.assertIsInstance(key, basestring)
            streamed_keys += keylist
        self.assertEqual(sorted(regular_keys), sorted(streamed_keys))

    def test_stream_keys_timeout(self):
        bucket = self.client.bucket('random_key_bucket')
        streamed_keys = []
        with self.assertRaises(RiakError):
            for keylist in self.client.stream_keys(bucket, timeout=1):
                self.assertNotEqual([], keylist)
                for key in keylist:
                    self.assertIsInstance(key, basestring)
                streamed_keys += keylist

    def test_stream_keys_abort(self):
        bucket = self.client.bucket('random_key_bucket')
        regular_keys = bucket.get_keys()
        self.assertNotEqual(len(regular_keys), 0)
        try:
            for keylist in bucket.stream_keys():
                raise RuntimeError("abort")
        except RuntimeError:
            pass

        # If the stream was closed correctly, this will not error
        robj = bucket.get(regular_keys[0])
        self.assertEqual(len(robj.siblings), 1)
        self.assertEqual(True, robj.exists)

    def test_bad_key(self):
        bucket = self.client.bucket(self.bucket_name)
        obj = bucket.new()
        with self.assertRaises(TypeError):
            bucket.get(None)

        with self.assertRaises(TypeError):
            self.client.get(obj)

        with self.assertRaises(TypeError):
            bucket.get(1)

    def test_binary_store_and_get(self):
        bucket = self.client.bucket(self.bucket_name)
        # Store as binary, retrieve as binary, then compare...
        rand = str(self.randint())
        obj = bucket.new(self.key_name, encoded_data=rand,
                         content_type='text/plain')
        obj.store()
        obj = bucket.get(self.key_name)
        self.assertTrue(obj.exists)
        self.assertEqual(obj.encoded_data, rand)
        # Store as JSON, retrieve as binary, JSON-decode, then compare...
        data = [self.randint(), self.randint(), self.randint()]
        key2 = self.randname()
        obj = bucket.new(key2, data)
        obj.store()
        obj = bucket.get(key2)
        self.assertEqual(data, json.loads(obj.encoded_data))

    def test_blank_binary_204(self):
        bucket = self.client.bucket(self.bucket_name)

        # this should *not* raise an error
        obj = bucket.new('foo2', encoded_data='', content_type='text/plain')
        obj.store()
        obj = bucket.get('foo2')
        self.assertTrue(obj.exists)
        self.assertEqual(obj.encoded_data, '')

    def test_custom_bucket_encoder_decoder(self):
        bucket = self.client.bucket(self.bucket_name)
        # Teach the bucket how to pickle
        bucket.set_encoder('application/x-pickle', cPickle.dumps)
        bucket.set_decoder('application/x-pickle', cPickle.loads)
        data = {'array': [1, 2, 3], 'badforjson': NotJsonSerializable(1, 3)}
        obj = bucket.new(self.key_name, data, 'application/x-pickle')
        obj.store()
        obj2 = bucket.get(self.key_name)
        self.assertEqual(data, obj2.data)

    def test_custom_client_encoder_decoder(self):
        bucket = self.client.bucket(self.bucket_name)
        # Teach the client how to pickle
        self.client.set_encoder('application/x-pickle', cPickle.dumps)
        self.client.set_decoder('application/x-pickle', cPickle.loads)
        data = {'array': [1, 2, 3], 'badforjson': NotJsonSerializable(1, 3)}
        obj = bucket.new(self.key_name, data, 'application/x-pickle')
        obj.store()
        obj2 = bucket.get(self.key_name)
        self.assertEqual(data, obj2.data)

    def test_unknown_content_type_encoder_decoder(self):
        # Teach the bucket how to pickle
        bucket = self.client.bucket(self.bucket_name)
        data = "some funny data"
        obj = bucket.new(self.key_name,
                         encoded_data=data,
                         content_type='application/x-frobnicator')
        obj.store()
        obj2 = bucket.get(self.key_name)
        self.assertEqual(data, obj2.encoded_data)

    def test_text_plain_encoder_decoder(self):
        bucket = self.client.bucket(self.bucket_name)
        data = "some funny data"
        obj = bucket.new(self.key_name, data, content_type='text/plain')
        obj.store()
        obj2 = bucket.get(self.key_name)
        self.assertEqual(data, obj2.data)

    def test_missing_object(self):
        bucket = self.client.bucket(self.bucket_name)
        obj = bucket.get(self.key_name)
        self.assertFalse(obj.exists)
        # Object with no siblings should not raise the ConflictError
        self.assertIsNone(obj.data)

    def test_delete(self):
        bucket = self.client.bucket(self.bucket_name)
        rand = self.randint()
        obj = bucket.new(self.key_name, rand)
        obj.store()
        obj = bucket.get(self.key_name)
        self.assertTrue(obj.exists)

        obj.delete()
        obj.reload()
        self.assertFalse(obj.exists)

    def test_bucket_delete(self):
        bucket = self.client.bucket(self.bucket_name)
        rand = self.randint()
        obj = bucket.new(self.key_name, rand)
        obj.store()

        bucket.delete(self.key_name)
        obj.reload()
        self.assertFalse(obj.exists)

    def test_set_bucket_properties(self):
        bucket = self.client.bucket(self.props_bucket)
        # Test setting allow mult...
        bucket.allow_mult = True
        # Test setting nval...
        bucket.n_val = 1

        bucket2 = self.create_client().bucket(self.props_bucket)
        self.assertTrue(bucket2.allow_mult)
        self.assertEqual(bucket2.n_val, 1)
        # Test setting multiple properties...
        bucket.set_properties({"allow_mult": False, "n_val": 2})

        bucket3 = self.create_client().bucket(self.props_bucket)
        self.assertFalse(bucket3.allow_mult)
        self.assertEqual(bucket3.n_val, 2)

    def test_if_none_match(self):
        bucket = self.client.bucket(self.bucket_name)
        obj = bucket.get(self.key_name)
        obj.delete()

        obj.reload()
        self.assertFalse(obj.exists)
        obj.data = ["first store"]
        obj.content_type = 'application/json'
        obj.store()

        obj.data = ["second store"]
        with self.assertRaises(Exception):
            obj.store(if_none_match=True)

    def test_siblings(self):
        # Set up the bucket, clear any existing object...
        bucket = self.client.bucket(self.sibs_bucket)
        obj = bucket.get(self.key_name)
        bucket.allow_mult = True

        # Even if it previously existed, let's store a base resolved version
        # from which we can diverge by sending a stale vclock.
        obj.encoded_data = 'start'
        obj.content_type = 'application/octet-stream'
        obj.store()

        vals = set(self.generate_siblings(obj, count=5))

        # Make sure the object has five siblings...
        obj = bucket.get(self.key_name)
        obj.reload()
        self.assertEqual(len(obj.siblings), 5)

        # When the object is in conflict, using the shortcut methods
        # should raise the ConflictError
        with self.assertRaises(ConflictError):
            obj.data

        # Get each of the values - make sure they match what was
        # assigned
        vals2 = set([sibling.encoded_data for sibling in obj.siblings])
        self.assertEqual(vals, vals2)

        # Resolve the conflict, and then do a get...
        resolved_sibling = obj.siblings[3]
        obj.siblings = [resolved_sibling]
        obj.store()

        obj.reload()
        self.assertEqual(len(obj.siblings), 1)
        self.assertEqual(obj.encoded_data, resolved_sibling.encoded_data)

    @unittest.skipIf(SKIP_RESOLVE == '1',
                     "skip requested for resolvers test")
    def test_resolution(self):
        bucket = self.client.bucket(self.sibs_bucket)
        obj = bucket.get(self.key_name)
        bucket.allow_mult = True

        # Even if it previously existed, let's store a base resolved version
        # from which we can diverge by sending a stale vclock.
        obj.encoded_data = 'start'
        obj.content_type = 'text/plain'
        obj.store()

        vals = self.generate_siblings(obj, count=5, delay=1.01)

        # Make sure the object has five siblings when using the
        # default resolver
        obj = bucket.get(self.key_name)
        obj.reload()
        self.assertEqual(len(obj.siblings), 5)

        # Setting the resolver on the client object to use the
        # "last-write-wins" behavior
        self.client.resolver = last_written_resolver
        obj.reload()
        self.assertEqual(obj.resolver, last_written_resolver)
        self.assertEqual(1, len(obj.siblings))
        self.assertEqual(obj.data, vals[-1])

        # Set the resolver on the bucket to the default resolver,
        # overriding the resolver on the client
        bucket.resolver = default_resolver
        obj.reload()
        self.assertEqual(obj.resolver, default_resolver)
        self.assertEqual(len(obj.siblings), 5)

        # Define our own custom resolver on the object that returns
        # the maximum value, overriding the bucket and client resolvers
        def max_value_resolver(obj):
            datafun = lambda s: s.data
            obj.siblings = [max(obj.siblings, key=datafun), ]

        obj.resolver = max_value_resolver
        obj.reload()
        self.assertEqual(obj.resolver, max_value_resolver)
        self.assertEqual(obj.data, max(vals))

    def test_tombstone_siblings(self):
        # Set up the bucket, clear any existing object...
        bucket = self.client.bucket(self.sibs_bucket)
        obj = bucket.get(self.key_name)
        bucket.allow_mult = True

        obj.encoded_data = 'start'
        obj.content_type = 'application/octet-stream'
        obj.store(return_body=True)

        obj.delete()

        vals = set(self.generate_siblings(obj, count=4))

        obj = bucket.get(self.key_name)
        self.assertEqual(len(obj.siblings), 5)
        non_tombstones = 0
        for sib in obj.siblings:
            if sib.exists:
                non_tombstones += 1
            self.assertTrue(sib.encoded_data in vals or not sib.exists)
        self.assertEqual(non_tombstones, 4)

    def test_store_of_missing_object(self):
        bucket = self.client.bucket(self.bucket_name)
        # for json objects
        o = bucket.get(self.key_name)
        self.assertEqual(o.exists, False)
        o.data = {"foo": "bar"}
        o.content_type = 'application/json'

        o = o.store()
        self.assertEqual(o.data, {"foo": "bar"})
        self.assertEqual(o.content_type, "application/json")
        o.delete()
        # for binary objects
        o = bucket.get(self.randname())
        self.assertEqual(o.exists, False)
        o.encoded_data = "1234567890"
        o.content_type = 'application/octet-stream'

        o = o.store()
        self.assertEqual(o.encoded_data, "1234567890")
        self.assertEqual(o.content_type, "application/octet-stream")
        o.delete()

    def test_store_metadata(self):
        bucket = self.client.bucket(self.bucket_name)
        rand = self.randint()
        obj = bucket.new(self.key_name, rand)
        obj.usermeta = {'custom': 'some metadata'}
        obj.store()
        obj = bucket.get(self.key_name)
        self.assertEqual('some metadata', obj.usermeta['custom'])

    def test_list_buckets(self):
        bucket = self.client.bucket(self.bucket_name)
        bucket.new("one", {"foo": "one", "bar": "red"}).store()
        buckets = self.client.get_buckets()
        self.assertTrue(self.bucket_name in [x.name for x in buckets])

    def test_stream_buckets(self):
        bucket = self.client.bucket(self.bucket_name)
        bucket.new(self.key_name, data={"foo": "one",
                                        "bar": "baz"}).store()
        buckets = []
        for bucket_list in self.client.stream_buckets():
            buckets.extend(bucket_list)

        self.assertTrue(self.bucket_name in [x.name for x in buckets])

    def test_stream_buckets_abort(self):
        bucket = self.client.bucket(self.bucket_name)
        bucket.new(self.key_name, data={"foo": "one",
                                        "bar": "baz"}).store()
        try:
            for bucket_list in self.client.stream_buckets():
                raise RuntimeError("abort")
        except RuntimeError:
            pass

        robj = bucket.get(self.key_name)
        self.assertTrue(robj.exists)
        self.assertEqual(len(robj.siblings), 1)

    def generate_siblings(self, original, count=5, delay=None):
        vals = []
        for i in range(count):
            while True:
                randval = self.randint()
                if str(randval) not in vals:
                    break

            other_obj = original.bucket.new(key=original.key,
                                            encoded_data=str(randval),
                                            content_type='text/plain')
            other_obj.vclock = original.vclock
            other_obj.store()
            vals.append(str(randval))
            if delay:
                sleep(delay)
        return vals


class BucketPropsTest(object):
    def test_rw_settings(self):
        bucket = self.client.bucket(self.props_bucket)
        self.assertEqual(bucket.r, "quorum")
        self.assertEqual(bucket.w, "quorum")
        self.assertEqual(bucket.dw, "quorum")
        self.assertEqual(bucket.rw, "quorum")

        bucket.w = 1
        self.assertEqual(bucket.w, 1)

        bucket.r = "quorum"
        self.assertEqual(bucket.r, "quorum")

        bucket.dw = "all"
        self.assertEqual(bucket.dw, "all")

        bucket.rw = "one"
        self.assertEqual(bucket.rw, "one")

        bucket.set_properties({'w': 'quorum',
                               'r': 'quorum',
                               'dw': 'quorum',
                               'rw': 'quorum'})
        bucket.clear_properties()

    def test_primary_quora(self):
        bucket = self.client.bucket(self.props_bucket)
        self.assertEqual(bucket.pr, 0)
        self.assertEqual(bucket.pw, 0)

        bucket.pr = 1
        self.assertEqual(bucket.pr, 1)

        bucket.pw = "quorum"
        self.assertEqual(bucket.pw, "quorum")

        bucket.set_properties({'pr': 0, 'pw': 0})
        bucket.clear_properties()

    def test_clear_bucket_properties(self):
        bucket = self.client.bucket(self.props_bucket)
        bucket.allow_mult = True
        self.assertTrue(bucket.allow_mult)
        bucket.n_val = 1
        self.assertEqual(bucket.n_val, 1)
        # Test setting clearing properties...

        self.assertTrue(bucket.clear_properties())
        self.assertFalse(bucket.allow_mult)
        self.assertEqual(bucket.n_val, 3)


class KVFileTests(object):
    def test_store_binary_object_from_file(self):
        bucket = self.client.bucket(self.bucket_name)
        filepath = os.path.join(os.path.dirname(__file__), 'test_all.py')
        obj = bucket.new_from_file(self.key_name, filepath)
        obj.store()
        obj = bucket.get(self.key_name)
        self.assertNotEqual(obj.encoded_data, None)
        self.assertEqual(obj.content_type, "text/x-python")

    def test_store_binary_object_from_file_should_use_default_mimetype(self):
        bucket = self.client.bucket(self.bucket_name)
        filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                os.pardir, os.pardir, 'THANKS')
        obj = bucket.new_from_file(self.key_name, filepath)
        obj.store()
        obj = bucket.get(self.key_name)
        self.assertEqual(obj.content_type, 'application/octet-stream')

    def test_store_binary_object_from_file_should_fail_if_file_not_found(self):
        bucket = self.client.bucket(self.bucket_name)
        with self.assertRaises(IOError):
            bucket.new_from_file(self.key_name, 'FILE_NOT_FOUND')
        obj = bucket.get(self.key_name)
        # self.assertEqual(obj.encoded_data, None)
        self.assertFalse(obj.exists)


class CounterTests(object):
    def test_counter_requires_allow_mult(self):
        bucket = self.client.bucket(self.bucket_name)
        if bucket.allow_mult:
            bucket.allow_mult = False
        self.assertFalse(bucket.allow_mult)

        with self.assertRaises(Exception):
            bucket.update_counter(self.key_name, 10)

    def test_counter_ops(self):
        bucket = self.client.bucket(self.sibs_bucket)
        self.assertTrue(bucket.allow_mult)

        # Non-existent counter has no value
        self.assertEqual(None, bucket.get_counter(self.key_name))

        # Update the counter
        bucket.update_counter(self.key_name, 10)
        self.assertEqual(10, bucket.get_counter(self.key_name))

        # Update with returning the value
        self.assertEqual(15, bucket.update_counter(self.key_name, 5,
                                                   returnvalue=True))

        # Now try decrementing
        self.assertEqual(10, bucket.update_counter(self.key_name, -5,
                                                   returnvalue=True))

########NEW FILE########
__FILENAME__ = test_mapreduce
# -*- coding: utf-8 -*-

from riak.mapreduce import RiakMapReduce
from riak import key_filter, RiakError


class LinkTests(object):
    def test_store_and_get_links(self):
        # Create the object...
        bucket = self.client.bucket(self.bucket_name)
        bucket.new(key=self.key_name, encoded_data='2',
                   content_type='application/octet-stream') \
            .add_link(bucket.new("foo1")) \
            .add_link(bucket.new("foo2"), "tag") \
            .add_link(bucket.new("foo3"), "tag2!@#%^&*)") \
            .store()
        obj = bucket.get(self.key_name)
        links = obj.links
        self.assertEqual(len(links), 3)
        for bucket, key, tag in links:
            if (key == "foo1"):
                self.assertEqual(bucket, self.bucket_name)
            elif (key == "foo2"):
                self.assertEqual(tag, "tag")
            elif (key == "foo3"):
                self.assertEqual(tag, "tag2!@#%^&*)")
            else:
                self.assertEqual(key, "unknown key")

    def test_set_links(self):
        # Create the object
        bucket = self.client.bucket(self.bucket_name)
        o = bucket.new(self.key_name, 2)
        o.links = [(self.bucket_name, "foo1", None),
                   (self.bucket_name, "foo2", "tag"),
                   ("bucket", "foo2", "tag2")]
        o.store()
        obj = bucket.get(self.key_name)
        links = sorted(obj.links, key=lambda x: x[1])
        self.assertEqual(len(links), 3)
        self.assertEqual(links[0][1], "foo1")
        self.assertEqual(links[1][1], "foo2")
        self.assertEqual(links[1][2], "tag")
        self.assertEqual(links[2][1], "foo2")
        self.assertEqual(links[2][2], "tag2")

    def test_link_walking(self):
        # Create the object...
        bucket = self.client.bucket(self.bucket_name)
        bucket.new("foo", 2) \
            .add_link(bucket.new("foo1", "test1").store()) \
            .add_link(bucket.new("foo2", "test2").store(), "tag") \
            .add_link(bucket.new("foo3", "test3").store(), "tag2!@#%^&*)") \
            .store()
        obj = bucket.get("foo")
        results = obj.link(self.bucket_name).run()
        self.assertEqual(len(results), 3)
        results = obj.link(self.bucket_name, "tag").run()
        self.assertEqual(len(results), 1)


class ErlangMapReduceTests(object):
    def test_erlang_map_reduce(self):
        # Create the object...
        bucket = self.client.bucket(self.bucket_name)
        bucket.new("foo", 2).store()
        bucket.new("bar", 2).store()
        bucket.new("baz", 4).store()
        # Run the map...
        result = self.client \
            .add(self.bucket_name, "foo") \
            .add(self.bucket_name, "bar") \
            .add(self.bucket_name, "baz") \
            .map(["riak_kv_mapreduce", "map_object_value"]) \
            .reduce(["riak_kv_mapreduce", "reduce_set_union"]) \
            .run()
        self.assertEqual(len(result), 2)

    def test_erlang_source_map_reduce(self):
        # Create the object...
        bucket = self.client.bucket(self.bucket_name)
        bucket.new("foo", 2).store()
        bucket.new("bar", 3).store()
        bucket.new("baz", 4).store()
        strfun_allowed = True
        # Run the map...
        try:
            result = self.client \
                .add(self.bucket_name, "foo") \
                .add(self.bucket_name, "bar") \
                .add(self.bucket_name, "baz") \
                .map("""fun(Object, _KD, _A) ->
            Value = riak_object:get_value(Object),
            [Value]
        end.""", {'language': 'erlang'}).run()
        except RiakError as e:
            if e.value.startswith('May have tried'):
                strfun_allowed = False
        if strfun_allowed:
            self.assertEqual(result, ['2', '3', '4'])

    def test_client_exceptional_paths(self):
        bucket = self.client.bucket(self.bucket_name)
        bucket.new("foo", 2).store()
        bucket.new("bar", 2).store()
        bucket.new("baz", 4).store()

        # adding a b-key pair to a bucket input
        with self.assertRaises(ValueError):
            mr = self.client.add(self.bucket_name)
            mr.add(self.bucket_name, 'bar')

        # adding a b-key pair to a query input
        with self.assertRaises(ValueError):
            mr = self.client.search(self.bucket_name, 'fleh')
            mr.add(self.bucket_name, 'bar')

        # adding a key filter to a query input
        with self.assertRaises(ValueError):
            mr = self.client.search(self.bucket_name, 'fleh')
            mr.add_key_filter("tokenize", "-", 1)


class JSMapReduceTests(object):
    def test_javascript_source_map(self):
        # Create the object...
        bucket = self.client.bucket(self.bucket_name)
        bucket.new("foo", 2).store()
        # Run the map...
        mr = self.client.add(self.bucket_name, "foo")
        result = mr.map(
            "function (v) { return [JSON.parse(v.values[0].data)]; }").run()
        self.assertEqual(result, [2])

        # test ASCII-encodable unicode is accepted
        mr.map(u"function (v) { return [JSON.parse(v.values[0].data)]; }")

        # test non-ASCII-encodable unicode is rejected
        self.assertRaises(TypeError, mr.map,
                          u"""
                          function (v) {
                          /* æ */
                            return [JSON.parse(v.values[0].data)];
                          }""")

        # test non-ASCII-encodable string is rejected
        self.assertRaises(TypeError, mr.map,
                          """function (v) {
                               /* æ */
                               return [JSON.parse(v.values[0].data)];
                             }""")

    def test_javascript_named_map(self):
        # Create the object...
        bucket = self.client.bucket(self.bucket_name)
        bucket.new("foo", 2).store()
        # Run the map...
        result = self.client \
            .add(self.bucket_name, "foo") \
            .map("Riak.mapValuesJson") \
            .run()
        self.assertEqual(result, [2])

    def test_javascript_source_map_reduce(self):
        # Create the object...
        bucket = self.client.bucket(self.bucket_name)
        bucket.new("foo", 2).store()
        bucket.new("bar", 3).store()
        bucket.new("baz", 4).store()
        # Run the map...
        result = self.client \
            .add(self.bucket_name, "foo") \
            .add(self.bucket_name, "bar") \
            .add(self.bucket_name, "baz") \
            .map("function (v) { return [1]; }") \
            .reduce("Riak.reduceSum") \
            .run()
        self.assertEqual(result, [3])

    def test_javascript_named_map_reduce(self):
        # Create the object...
        bucket = self.client.bucket(self.bucket_name)
        bucket.new("foo", 2).store()
        bucket.new("bar", 3).store()
        bucket.new("baz", 4).store()
        # Run the map...
        result = self.client \
            .add(self.bucket_name, "foo") \
            .add(self.bucket_name, "bar") \
            .add(self.bucket_name, "baz") \
            .map("Riak.mapValuesJson") \
            .reduce("Riak.reduceSum") \
            .run()
        self.assertEqual(result, [9])

    def test_javascript_bucket_map_reduce(self):
        # Create the object...
        bucket = self.client.bucket("bucket_%s" % self.randint())
        bucket.new("foo", 2).store()
        bucket.new("bar", 3).store()
        bucket.new("baz", 4).store()
        # Run the map...
        result = self.client \
            .add(bucket.name) \
            .map("Riak.mapValuesJson") \
            .reduce("Riak.reduceSum") \
            .run()
        self.assertEqual(result, [9])

    def test_javascript_arg_map_reduce(self):
        # Create the object...
        bucket = self.client.bucket(self.bucket_name)
        bucket.new("foo", 2).store()
        # Run the map...
        result = self.client \
            .add(self.bucket_name, "foo", 5) \
            .add(self.bucket_name, "foo", 10) \
            .add(self.bucket_name, "foo", 15) \
            .add(self.bucket_name, "foo", -15) \
            .add(self.bucket_name, "foo", -5) \
            .map("function(v, arg) { return [arg]; }") \
            .reduce("Riak.reduceSum") \
            .run()
        self.assertEqual(result, [10])

    def test_key_filters(self):
        bucket = self.client.bucket("kftest")
        bucket.new("basho-20101215", 1).store()
        bucket.new("google-20110103", 2).store()
        bucket.new("yahoo-20090613", 3).store()

        result = self.client \
            .add("kftest") \
            .add_key_filters([["tokenize", "-", 2]]) \
            .add_key_filter("ends_with", "0613") \
            .map("function (v, keydata) { return [v.key]; }") \
            .run()

        self.assertEqual(result, ["yahoo-20090613"])

    def test_key_filters_f_chain(self):
        bucket = self.client.bucket("kftest")
        bucket.new("basho-20101215", 1).store()
        bucket.new("google-20110103", 2).store()
        bucket.new("yahoo-20090613", 3).store()

        # compose a chain of key filters using f as the root of
        # two filters ANDed together to ensure that f can be the root
        # of multiple chains
        filters = key_filter.tokenize("-", 1).eq("yahoo") \
            & key_filter.tokenize("-", 2).ends_with("0613")

        result = self.client \
            .add("kftest") \
            .add_key_filters(filters) \
            .map("function (v, keydata) { return [v.key]; }") \
            .run()

        self.assertEqual(result, ["yahoo-20090613"])

    def test_key_filters_with_search_query(self):
        mapreduce = self.client.search("kftest", "query")
        self.assertRaises(Exception, mapreduce.add_key_filters,
                          [["tokenize", "-", 2]])
        self.assertRaises(Exception, mapreduce.add_key_filter,
                          "ends_with", "0613")

    def test_map_reduce_from_object(self):
        # Create the object...
        bucket = self.client.bucket(self.bucket_name)
        bucket.new("foo", 2).store()
        obj = bucket.get("foo")
        result = obj.map("Riak.mapValuesJson").run()
        self.assertEqual(result, [2])

    def test_mr_list_add(self):
        bucket = self.client.bucket(self.bucket_name)
        for x in range(20):
            bucket.new('baz' + str(x),
                       'bazval' + str(x)).store()
        mr = self.client.add(self.bucket_name, ['baz' + str(x)
                                                for x in range(2, 5)])
        results = mr.map_values().run()
        results.sort()
        self.assertEqual(results,
                         [u'"bazval2"',
                          u'"bazval3"',
                          u'"bazval4"'])

    def test_mr_list_add_two_buckets(self):
        bucket = self.client.bucket(self.bucket_name)
        name2 = self.randname()
        for x in range(10):
            bucket.new('foo' + str(x),
                       'fooval' + str(x)).store()
        bucket = self.client.bucket(name2)
        for x in range(10):
            bucket.new('bar' + str(x),
                       'barval' + str(x)).store()

        mr = self.client.add(self.bucket_name, ['foo' + str(x)
                                                for x in range(2, 4)])
        mr.add(name2, ['bar' + str(x)
                       for x in range(5, 7)])
        results = mr.map_values().run()
        results.sort()

        self.assertEqual(results,
                         [u'"barval5"',
                          u'"barval6"',
                          u'"fooval2"',
                          u'"fooval3"'])

    def test_mr_list_add_mix(self):
        bucket = self.client.bucket("bucket_a")
        for x in range(10):
            bucket.new('foo' + str(x),
                       'fooval' + str(x)).store()
        bucket = self.client.bucket("bucket_b")
        for x in range(10):
            bucket.new('bar' + str(x),
                       'barval' + str(x)).store()

        mr = self.client.add('bucket_a', ['foo' + str(x)
                                          for x in range(2, 4)])
        mr.add('bucket_b', 'bar9')
        mr.add('bucket_b', 'bar2')
        results = mr.map_values().run()
        results.sort()

        self.assertEqual(results,
                         [u'"barval2"',
                          u'"barval9"',
                          u'"fooval2"',
                          u'"fooval3"'])


class MapReduceAliasTests(object):
    """This tests the map reduce aliases"""

    def test_map_values(self):
        # Add a value to the bucket
        bucket = self.client.bucket(self.bucket_name)
        bucket.new('one', encoded_data='value_1',
                   content_type='text/plain').store()
        bucket.new('two', encoded_data='value_2',
                   content_type='text/plain').store()

        # Create a map reduce object and use one and two as inputs
        mr = self.client.add(self.bucket_name, 'one')\
                        .add(self.bucket_name, 'two')

        # Use the map_values alias
        result = mr.map_values().run()

        # Sort the result so that we can have a consistent
        # expected value
        result.sort()

        self.assertEqual(result, ["value_1", "value_2"])

    def test_map_values_json(self):
        # Add a value to the bucket
        bucket = self.client.bucket(self.bucket_name)
        bucket.new('one', data={'val': 'value_1'}).store()
        bucket.new('two', data={'val': 'value_2'}).store()

        # Create a map reduce object and use one and two as inputs
        mr = self.client.add(self.bucket_name, 'one')\
                        .add(self.bucket_name, 'two')

        # Use the map_values alias
        result = mr.map_values_json().run()

        # Sort the result so that we can have a consistent
        # expected value
        result.sort(key=lambda x: x['val'])

        self.assertEqual(result, [{'val': "value_1"}, {'val': "value_2"}])

    def test_reduce_sum(self):
        # Add a value to the bucket
        bucket = self.client.bucket(self.bucket_name)
        bucket.new('one', data=1).store()
        bucket.new('two', data=2).store()

        # Create a map reduce object and use one and two as inputs
        mr = self.client.add(self.bucket_name, 'one')\
                        .add(self.bucket_name, 'two')

        # Use the map_values alias
        result = mr.map_values_json().reduce_sum().run()

        self.assertEqual(result, [3])

    def test_reduce_min(self):
        # Add a value to the bucket
        bucket = self.client.bucket(self.bucket_name)
        bucket.new('one', data=1).store()
        bucket.new('two', data=2).store()

        # Create a map reduce object and use one and two as inputs
        mr = self.client.add(self.bucket_name, 'one')\
                        .add(self.bucket_name, 'two')

        # Use the map_values alias
        result = mr.map_values_json().reduce_min().run()

        self.assertEqual(result, [1])

    def test_reduce_max(self):
        # Add a value to the bucket
        bucket = self.client.bucket(self.bucket_name)
        bucket.new('one', data=1).store()
        bucket.new('two', data=2).store()

        # Create a map reduce object and use one and two as inputs
        mr = self.client.add(self.bucket_name, 'one')\
                        .add(self.bucket_name, 'two')

        # Use the map_values alias
        result = mr.map_values_json().reduce_max().run()

        self.assertEqual(result, [2])

    def test_reduce_sort(self):
        # Add a value to the bucket
        bucket = self.client.bucket(self.bucket_name)
        bucket.new('one', data="value1").store()
        bucket.new('two', data="value2").store()

        # Create a map reduce object and use one and two as inputs
        mr = self.client.add(self.bucket_name, 'one')\
                        .add(self.bucket_name, 'two')

        # Use the map_values alias
        result = mr.map_values_json().reduce_sort().run()

        self.assertEqual(result, ["value1", "value2"])

    def test_reduce_sort_custom(self):
        # Add a value to the bucket
        bucket = self.client.bucket(self.bucket_name)
        bucket.new('one', data="value1").store()
        bucket.new('two', data="value2").store()

        # Create a map reduce object and use one and two as inputs
        mr = self.client.add(self.bucket_name, 'one')\
                        .add(self.bucket_name, 'two')

        # Use the map_values alias
        result = mr.map_values_json().reduce_sort("""function(x,y) {
           if(x == y) return 0;
           return x > y ? -1 : 1;
        }""").run()

        self.assertEqual(result, ["value2", "value1"])

    def test_reduce_numeric_sort(self):
        # Add a value to the bucket
        bucket = self.client.bucket(self.bucket_name)
        bucket.new('one', data=1).store()
        bucket.new('two', data=2).store()

        # Create a map reduce object and use one and two as inputs
        mr = self.client.add(self.bucket_name, 'one')\
                        .add(self.bucket_name, 'two')

        # Use the map_values alias
        result = mr.map_values_json().reduce_numeric_sort().run()

        self.assertEqual(result, [1, 2])

    def test_reduce_limit(self):
        # Add a value to the bucket
        bucket = self.client.bucket(self.bucket_name)
        bucket.new('one', data=1).store()
        bucket.new('two', data=2).store()

        # Create a map reduce object and use one and two as inputs
        mr = self.client.add(self.bucket_name, 'one')\
                        .add(self.bucket_name, 'two')

        # Use the map_values alias
        result = mr.map_values_json()\
                   .reduce_numeric_sort()\
                   .reduce_limit(1).run()

        self.assertEqual(result, [1])

    def test_reduce_slice(self):
        # Add a value to the bucket
        bucket = self.client.bucket(self.bucket_name)
        bucket.new('one', data=1).store()
        bucket.new('two', data=2).store()

        # Create a map reduce object and use one and two as inputs
        mr = self.client.add(self.bucket_name, 'one')\
                        .add(self.bucket_name, 'two')

        # Use the map_values alias
        result = mr.map_values_json()\
                   .reduce_numeric_sort()\
                   .reduce_slice(1, 2).run()

        self.assertEqual(result, [2])

    def test_filter_not_found(self):
        # Add a value to the bucket
        bucket = self.client.bucket(self.bucket_name)
        bucket.new('one', data=1).store()
        bucket.new('two', data=2).store()

        # Create a map reduce object and use one and two as inputs
        mr = self.client.add(self.bucket_name, 'one')\
                        .add(self.bucket_name, 'two')\
                        .add(self.bucket_name, self.key_name)

        # Use the map_values alias
        result = mr.map_values_json()\
                   .filter_not_found()\
                   .run()

        self.assertEqual(sorted(result), [1, 2])


class MapReduceStreamTests(object):
    def test_stream_results(self):
        bucket = self.client.bucket(self.bucket_name)
        bucket.new('one', data=1).store()
        bucket.new('two', data=2).store()

        mr = RiakMapReduce(self.client).add(self.bucket_name, 'one')\
                                       .add(self.bucket_name, 'two')
        mr.map_values_json()
        results = []
        for phase, data in mr.stream():
            results.extend(data)

        self.assertEqual(sorted(results), [1, 2])

    def test_stream_cleanoperationsup(self):
        bucket = self.client.bucket(self.bucket_name)
        bucket.new('one', data=1).store()
        bucket.new('two', data=2).store()

        mr = RiakMapReduce(self.client).add(self.bucket_name, 'one')\
                                       .add(self.bucket_name, 'two')
        mr.map_values_json()
        try:
            for phase, data in mr.stream():
                raise RuntimeError("woops")
        except RuntimeError:
            pass

        # This should not raise an exception
        obj = bucket.get('one')
        self.assertEqual('1', obj.encoded_data)

########NEW FILE########
__FILENAME__ = test_pool
"""
Copyright 2012 Basho Technologies, Inc.

This file is provided to you under the Apache License,
Version 2.0 (the "License"); you may not use this file
except in compliance with the License.  You may obtain
a copy of the License at

  http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on an
"AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
KIND, either express or implied.  See the License for the
specific language governing permissions and limitations
under the License.
"""

import platform
from Queue import Queue
from threading import Thread, currentThread
from riak.transports.pool import Pool, BadResource
from random import SystemRandom
from time import sleep

if platform.python_version() < '2.7':
    unittest = __import__('unittest2')
else:
    import unittest
from . import SKIP_POOL


class SimplePool(Pool):
    def __init__(self):
        self.count = 0
        Pool.__init__(self)

    def create_resource(self):
        self.count += 1
        return [self.count]

    def destroy_resource(self, resource):
        del resource[:]


class EmptyListPool(Pool):
    def create_resource(self):
        return []


@unittest.skipIf(SKIP_POOL,
                 'Skipping connection pool tests')
class PoolTest(unittest.TestCase):
    def test_yields_new_object_when_empty(self):
        """
        The pool should create new resources as needed.
        """
        pool = SimplePool()
        with pool.take() as element:
            self.assertEqual([1], element)

    def test_yields_same_object_in_serial_access(self):
        """
        The pool should reuse resources that already exist, when used
        serially.
        """
        pool = SimplePool()

        with pool.take() as element:
            self.assertEqual([1], element)
            element.append(2)

        with pool.take() as element2:
            self.assertEqual(1, len(pool.elements))
            self.assertEqual([1, 2], element2)

        self.assertEqual(1, len(pool.elements))

    def test_reentrance(self):
        """
        The pool should be re-entrant, that is, yield new resources
        while one is already claimed in the same code path.
        """
        pool = SimplePool()
        with pool.take() as first:
            self.assertEqual([1], first)
            with pool.take() as second:
                self.assertEqual([2], second)
                with pool.take() as third:
                    self.assertEqual([3], third)

    def test_unlocks_when_exception_raised(self):
        """
        The pool should unlock all resources that were previously
        claimed when an exception occurs.
        """
        pool = SimplePool()
        try:
            with pool.take():
                with pool.take():
                    raise RuntimeError
        except:
            self.assertEqual(2, len(pool.elements))
            for e in pool.elements:
                self.assertFalse(e.claimed)

    def test_removes_bad_resource(self):
        """
        The pool should remove resources that are considered bad by
        user code throwing a BadResource exception.
        """
        pool = SimplePool()
        with pool.take() as element:
            self.assertEqual([1], element)
            element.append(2)
        try:
            with pool.take():
                raise BadResource
        except BadResource:
            self.assertEqual(0, len(pool.elements))
            with pool.take() as goodie:
                self.assertEqual([2], goodie)

    def test_filter_skips_unmatching_elements(self):
        """
        The _filter parameter should cause the pool to yield the first
        unclaimed resource that passes the filter.
        """
        def filtereven(numlist):
            return numlist[0] % 2 == 0

        pool = SimplePool()
        with pool.take():
            with pool.take():
                pass

        with pool.take(_filter=filtereven) as f:
            self.assertEqual([2], f)

    def test_requires_filter_to_be_callable(self):
        """
        The _filter parameter should be required to be a callable, or
        None.
        """
        badfilter = 'foo'
        pool = SimplePool()

        with self.assertRaises(TypeError):
            with pool.take(_filter=badfilter):
                pass

    def test_yields_default_when_empty(self):
        """
        The pool should yield the given default when no existing
        resources are free.
        """
        pool = SimplePool()
        with pool.take(default='default') as x:
            self.assertEqual('default', x)

    def test_thread_safety(self):
        """
        The pool should allocate n objects for n concurrent operations.
        """
        n = 10
        pool = EmptyListPool()
        readyq = Queue()
        finishq = Queue()
        threads = []

        def _run():
            with pool.take() as resource:
                readyq.put(1)
                resource.append(currentThread())
                finishq.get(True)
                finishq.task_done()

        for i in range(n):
            th = Thread(target=_run)
            threads.append(th)
            th.start()

        for i in range(n):
            readyq.get()
            readyq.task_done()

        for i in range(n):
            finishq.put(1)

        for thr in threads:
            thr.join()

        self.assertEqual(n, len(pool.elements))
        for element in pool.elements:
            self.assertFalse(element.claimed)
            self.assertEqual(1, len(element.object))
            self.assertIn(element.object[0], threads)

    def test_iteration(self):
        """
        Iteration over the pool resources, even when some are claimed,
        should eventually touch all resources (excluding ones created
        during iteration).
        """

        for i in range(25):
            started = Queue()
            n = 1000
            threads = []
            touched = []
            pool = EmptyListPool()
            rand = SystemRandom()

            def _run():
                psleep = rand.uniform(0.05, 0.1)
                with pool.take() as a:
                    started.put(1)
                    started.join()
                    a.append(rand.uniform(0, 1))
                    sleep(psleep)

            for i in range(n):
                th = Thread(target=_run)
                threads.append(th)
                th.start()

            for i in range(n):
                started.get()
                started.task_done()

            for element in pool:
                touched.append(element)

            for thr in threads:
                thr.join()

            self.assertItemsEqual(pool.elements, touched)

    def test_clear(self):
        """
        Clearing the pool should remove all resources known at the
        time of the call.
        """
        n = 10
        startq = Queue()
        finishq = Queue()
        rand = SystemRandom()
        threads = []
        pusher = None
        pool = SimplePool()

        def worker_run():
            with pool.take():
                startq.put(1)
                startq.join()
                sleep(rand.uniform(0, 0.5))
                finishq.get()
                finishq.task_done()

        def pusher_run():
            for i in range(n):
                finishq.put(1)
                sleep(rand.uniform(0, 0.1))
            finishq.join()

        # Allocate 10 resources in the pool by spinning up 10 threads
        for i in range(n):
            th = Thread(target=worker_run)
            threads.append(th)
            th.start()

        # Pull everything off the queue, allowing the workers to run
        for i in range(n):
            startq.get()
            startq.task_done()

        # Start the pusher that will allow them to proceed and exit
        pusher = Thread(target=pusher_run)
        threads.append(pusher)
        pusher.start()

        # Clear the pool
        pool.clear()

        # Wait for all threads to complete
        for t in threads:
            t.join()

        # Make sure that the pool resources are gone
        self.assertEqual(0, len(pool.elements))

    def test_stress(self):
        """
        Runs a large number of threads doing operations with elements
        checked out, ensuring properties of the pool.
        """
        rand = SystemRandom()
        n = rand.randint(1, 400)
        passes = rand.randint(1, 20)
        rounds = rand.randint(1, 200)
        breaker = rand.uniform(0, 1)
        pool = EmptyListPool()

        def _run():
            for i in range(rounds):
                with pool.take() as a:
                    self.assertEqual([], a)
                    a.append(currentThread())
                    self.assertEqual([currentThread()], a)

                    for p in range(passes):
                        self.assertEqual([currentThread()], a)
                        if rand.uniform(0, 1) > breaker:
                            break

                    a.remove(currentThread())

        threads = []

        for i in range(n):
            th = Thread(target=_run)
            threads.append(th)
            th.start()

        for th in threads:
            th.join()

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_search
# -*- coding: utf-8 -*-
import platform
if platform.python_version() < '2.7':
    unittest = __import__('unittest2')
else:
    import unittest

from . import SKIP_SEARCH


class EnableSearchTests(object):
    @unittest.skipIf(SKIP_SEARCH, 'SKIP_SEARCH is defined')
    def test_bucket_search_enabled(self):
        bucket = self.client.bucket(self.bucket_name)
        self.assertFalse(bucket.search_enabled())

    @unittest.skipIf(SKIP_SEARCH, 'SKIP_SEARCH is defined')
    def test_enable_search_commit_hook(self):
        bucket = self.client.bucket(self.search_bucket)
        bucket.clear_properties()
        self.assertFalse(self.create_client().
                         bucket(self.search_bucket).
                         search_enabled())
        bucket.enable_search()
        self.assertTrue(self.create_client().
                        bucket(self.search_bucket).
                        search_enabled())

    @unittest.skipIf(SKIP_SEARCH, 'SKIP_SEARCH is defined')
    def test_disable_search_commit_hook(self):
        bucket = self.client.bucket(self.search_bucket)
        bucket.clear_properties()
        bucket.enable_search()
        self.assertTrue(self.create_client().bucket(self.search_bucket)
                            .search_enabled())
        bucket.disable_search()
        self.assertFalse(self.create_client().bucket(self.search_bucket)
                             .search_enabled())
        bucket.enable_search()


class SolrSearchTests(object):
    @unittest.skipIf(SKIP_SEARCH, 'SKIP_SEARCH is defined')
    def test_add_document_to_index(self):
        self.client.fulltext_add(self.search_bucket,
                                 [{"id": "doc", "username": "tony"}])
        results = self.client.fulltext_search(self.search_bucket,
                                              "username:tony")
        self.assertEquals("tony", results['docs'][0]['username'])

    @unittest.skipIf(SKIP_SEARCH, 'SKIP_SEARCH is defined')
    def test_add_multiple_documents_to_index(self):
        self.client.fulltext_add(
            self.search_bucket,
            [{"id": "dizzy", "username": "dizzy"},
             {"id": "russell", "username": "russell"}])
        results = self.client.fulltext_search(
            self.search_bucket, "username:russell OR username:dizzy")
        self.assertEquals(2, len(results['docs']))

    @unittest.skipIf(SKIP_SEARCH, 'SKIP_SEARCH is defined')
    def test_delete_documents_from_search_by_id(self):
        self.client.fulltext_add(
            self.search_bucket,
            [{"id": "dizzy", "username": "dizzy"},
             {"id": "russell", "username": "russell"}])
        self.client.fulltext_delete(self.search_bucket, docs=["dizzy"])
        results = self.client.fulltext_search(
            self.search_bucket, "username:russell OR username:dizzy")
        self.assertEquals(1, len(results['docs']))

    @unittest.skipIf(SKIP_SEARCH, 'SKIP_SEARCH is defined')
    def test_delete_documents_from_search_by_query(self):
        self.client.fulltext_add(
            self.search_bucket,
            [{"id": "dizzy", "username": "dizzy"},
             {"id": "russell", "username": "russell"}])
        self.client.fulltext_delete(
            self.search_bucket,
            queries=["username:dizzy", "username:russell"])
        results = self.client.fulltext_search(
            self.search_bucket, "username:russell OR username:dizzy")
        self.assertEquals(0, len(results['docs']))

    @unittest.skipIf(SKIP_SEARCH, 'SKIP_SEARCH is defined')
    def test_delete_documents_from_search_by_query_and_id(self):
        self.client.fulltext_add(
            self.search_bucket,
            [{"id": "dizzy", "username": "dizzy"},
             {"id": "russell", "username": "russell"}])
        self.client.fulltext_delete(
            self.search_bucket,
            docs=["dizzy"],
            queries=["username:russell"])
        results = self.client.fulltext_search(
            self.search_bucket,
            "username:russell OR username:dizzy")
        self.assertEquals(0, len(results['docs']))


class SearchTests(object):
    @unittest.skipIf(SKIP_SEARCH, 'SKIP_SEARCH is defined')
    def test_solr_search_from_bucket(self):
        bucket = self.client.bucket(self.search_bucket)
        bucket.new("user", {"username": "roidrage"}).store()
        results = bucket.search("username:roidrage")
        self.assertEquals(1, len(results['docs']))

    @unittest.skipIf(SKIP_SEARCH, 'SKIP_SEARCH is defined')
    def test_solr_search_with_params_from_bucket(self):
        bucket = self.client.bucket(self.search_bucket)
        bucket.new("user", {"username": "roidrage"}).store()
        results = bucket.search("username:roidrage", wt="xml")
        self.assertEquals(1, len(results['docs']))

    @unittest.skipIf(SKIP_SEARCH, 'SKIP_SEARCH is defined')
    def test_solr_search_with_params(self):
        bucket = self.client.bucket(self.search_bucket)
        bucket.new("user", {"username": "roidrage"}).store()
        results = self.client.fulltext_search(
            self.search_bucket,
            "username:roidrage", wt="xml")
        self.assertEquals(1, len(results['docs']))

    @unittest.skipIf(SKIP_SEARCH, 'SKIP_SEARCH is defined')
    def test_solr_search(self):
        bucket = self.client.bucket(self.search_bucket)
        bucket.new("user", {"username": "roidrage"}).store()
        results = self.client.fulltext_search(self.search_bucket,
                                              "username:roidrage")
        self.assertEquals(1, len(results["docs"]))

    @unittest.skipIf(SKIP_SEARCH, 'SKIP_SEARCH is defined')
    def test_search_integration(self):
        # Create some objects to search across...
        bucket = self.client.bucket(self.search_bucket)
        bucket.new("one", {"foo": "one", "bar": "red"}).store()
        bucket.new("two", {"foo": "two", "bar": "green"}).store()
        bucket.new("three", {"foo": "three", "bar": "blue"}).store()
        bucket.new("four", {"foo": "four", "bar": "orange"}).store()
        bucket.new("five", {"foo": "five", "bar": "yellow"}).store()

        # Run some operations...
        results = self.client.fulltext_search(self.search_bucket,
                                              "foo:one OR foo:two")
        if (len(results) == 0):
            print "\n\nNot running test \"testSearchIntegration()\".\n"
            print """Please ensure that you have installed the Riak
            Search hook on bucket \"searchbucket\" by running
            \"bin/search-cmd install searchbucket\".\n\n"""
            return
        self.assertEqual(len(results['docs']), 2)
        query = "(foo:one OR foo:two OR foo:three OR foo:four) AND\
                 (NOT bar:green)"
        results = self.client.fulltext_search(self.search_bucket, query)

        self.assertEqual(len(results['docs']), 3)

########NEW FILE########
__FILENAME__ = test_server_test
from riak.test_server import TestServer
import unittest


class TestServerTestCase(unittest.TestCase):
    def setUp(self):
        self.test_server = TestServer()

    def tearDown(self):
        pass

    def test_options_defaults(self):
        self.assertEquals(
            self.test_server.app_config["riak_core"]["handoff_port"], 9001)
        self.assertEquals(
            self.test_server.app_config["riak_kv"]["pb_ip"], "127.0.0.1")

    def test_merge_riak_core_options(self):
        self.test_server = TestServer(riak_core={"handoff_port": 10000})
        self.assertEquals(
            self.test_server.app_config["riak_core"]["handoff_port"], 10000)

    def test_merge_riak_search_options(self):
        self.test_server = TestServer(
            riak_search={"search_backend": "riak_search_backend"})
        self.assertEquals(
            self.test_server.app_config["riak_search"]["search_backend"],
            "riak_search_backend")

    def test_merge_riak_kv_options(self):
        self.test_server = TestServer(riak_kv={"pb_ip": "192.168.2.1"})
        self.assertEquals(self.test_server.app_config["riak_kv"]["pb_ip"],
                          "192.168.2.1")

    def test_merge_vmargs(self):
        self.test_server = TestServer(vm_args={"-P": 65000})
        self.assertEquals(self.test_server.vm_args["-P"], 65000)

    def test_set_ring_state_dir(self):
        self.assertEquals(
            self.test_server.app_config["riak_core"]["ring_state_dir"],
            "/tmp/riak/test_server/data/ring")

    def test_set_default_tmp_dir(self):
        self.assertEquals(self.test_server.temp_dir, "/tmp/riak/test_server")

    def test_set_non_default_tmp_dir(self):
        tmp_dir = '/not/the/default/dir'
        server = TestServer(tmp_dir=tmp_dir)
        self.assertEquals(server.temp_dir, tmp_dir)


def suite():
    suite = unittest.TestSuite()
    suite.addTest(TestServerTestCase())
    return suite

########NEW FILE########
__FILENAME__ = test_yokozuna
# -*- coding: utf-8 -*-
import platform
import time
if platform.python_version() < '2.7':
    unittest = __import__('unittest2')
else:
    import unittest

from . import RUN_YZ


class YZSearchTests(object):
    @unittest.skipUnless(RUN_YZ, 'RUN_YZ is undefined')
    def test_yz_search_from_bucket(self):
        bucket = self.client.bucket(self.yz_bucket)
        bucket.new("user", {"user_s": "Z"}).store()
        time.sleep(1)
        results = bucket.search("user_s:Z")
        self.assertEquals(1, len(results['docs']))
        # TODO: check that docs return useful info
        result = results['docs'][0]
        self.assertIn('_yz_rk', result)
        self.assertEquals(u'user', result['_yz_rk'])
        self.assertIn('_yz_rb', result)
        self.assertEquals(self.yz_bucket, result['_yz_rb'])
        self.assertIn('score', result)
        self.assertIn('user_s', result)
        self.assertEquals(u'Z', result['user_s'])

    @unittest.skipUnless(RUN_YZ, 'RUN_YZ is undefined')
    def test_yz_get_search_index(self):
        index = self.client.get_search_index(self.yz_bucket)
        self.assertEquals(self.yz_bucket, index['name'])
        self.assertEquals('_yz_default', index['schema'])
        self.assertEquals(3, index['n_val'])
        with self.assertRaises(Exception):
            self.client.get_search_index('NOT' + self.yz_bucket)

    @unittest.skipUnless(RUN_YZ, 'RUN_YZ is undefined')
    def test_yz_delete_search_index(self):
        # expected to fail, since there's an attached bucket
        with self.assertRaises(Exception):
            self.client.delete_search_index(self.yz_bucket)
        # detatch bucket from index then delete
        b = self.client.bucket(self.yz_bucket)
        b.set_property('search_index', '_dont_index_')
        self.assertTrue(self.client.delete_search_index(self.yz_bucket))
        # create it again
        self.client.create_search_index(self.yz_bucket, '_yz_default', 3)
        b = self.client.bucket(self.yz_bucket)
        b.set_property('search_index', self.yz_bucket)
        time.sleep(1)  # wait for index to apply

    @unittest.skipUnless(RUN_YZ, 'RUN_YZ is undefined')
    def test_yz_list_search_indexes(self):
        indexes = self.client.list_search_indexes()
        self.assertIn(self.yz_bucket, [item['name'] for item in indexes])
        self.assertLessEqual(1, len(indexes))

    @unittest.skipUnless(RUN_YZ, 'RUN_YZ is undefined')
    def test_yz_create_schema(self):
        content = """<?xml version="1.0" encoding="UTF-8" ?>
        <schema name="test" version="1.5">
        <fields>
           <field name="_yz_id" type="_yz_str" indexed="true" stored="true"
            required="true" />
           <field name="_yz_ed" type="_yz_str" indexed="true" stored="true"/>
           <field name="_yz_pn" type="_yz_str" indexed="true" stored="true"/>
           <field name="_yz_fpn" type="_yz_str" indexed="true" stored="true"/>
           <field name="_yz_vtag" type="_yz_str" indexed="true" stored="true"/>
           <field name="_yz_node" type="_yz_str" indexed="true" stored="true"/>
           <field name="_yz_rk" type="_yz_str" indexed="true" stored="true"/>
           <field name="_yz_rb" type="_yz_str" indexed="true" stored="true"/>
           <field name="_yz_rt" type="_yz_str" indexed="true" stored="true"/>
           <field name="_yz_err" type="_yz_str" indexed="true"/>
        </fields>
        <uniqueKey>_yz_id</uniqueKey>
        <types>
            <fieldType name="_yz_str" class="solr.StrField"
             sortMissingLast="true" />
        </types>
        </schema>"""
        schema_name = self.randname()
        self.assertTrue(self.client.create_search_schema(schema_name, content))
        schema = self.client.get_search_schema(schema_name)
        self.assertEquals(schema_name, schema['name'])
        self.assertEquals(content, schema['content'])

    @unittest.skipUnless(RUN_YZ, 'RUN_YZ is undefined')
    def test_yz_create_bad_schema(self):
        bad_content = """
        <derp nope nope, how do i computer?
        """
        with self.assertRaises(Exception):
            self.client.create_search_schema(self.randname(), bad_content)

    @unittest.skipUnless(RUN_YZ, 'RUN_YZ is undefined')
    def test_yz_search_queries(self):
        bucket = self.client.bucket(self.yz_bucket)
        bucket.new("Z", {"username_s": "Z", "name_s": "ryan",
                         "age_i": 30}).store()
        bucket.new("R", {"username_s": "R", "name_s": "eric",
                         "age_i": 34}).store()
        bucket.new("F", {"username_s": "F", "name_s": "bryan fink",
                         "age_i": 32}).store()
        bucket.new("H", {"username_s": "H", "name_s": "brett",
                         "age_i": 14}).store()
        time.sleep(1)
        # multiterm
        results = bucket.search("username_s:(F OR H)")
        self.assertEquals(2, len(results['docs']))
        # boolean
        results = bucket.search("username_s:Z AND name_s:ryan")
        self.assertEquals(1, len(results['docs']))
        # range
        results = bucket.search("age_i:[30 TO 33]")
        self.assertEquals(2, len(results['docs']))
        # phrase
        results = bucket.search('name_s:"bryan fink"')
        self.assertEquals(1, len(results['docs']))
        # wildcard
        results = bucket.search('name_s:*ryan*')
        self.assertEquals(2, len(results['docs']))
        # regexp
        results = bucket.search('name_s:/br.*/')
        self.assertEquals(2, len(results['docs']))
        # Parameters:
        # limit
        results = bucket.search('username_s:*', rows=2)
        self.assertEquals(2, len(results['docs']))
        # sort
        results = bucket.search('username_s:*', sort="age_i asc")
        self.assertEquals(14, int(results['docs'][0]['age_i']))

    @unittest.skipUnless(RUN_YZ, 'RUN_YZ is undefined')
    def test_yz_search_utf8(self):
        bucket = self.client.bucket(self.yz_bucket)
        body = {"text_ja": u"私はハイビスカスを食べるのが 大好き"}
        bucket.new("shift_jis", body).store()
        # TODO: fails due to lack of direct PB unicode support
        # results = bucket.search(u"text_ja:大好き")
        # self.assertEquals(1, len(results['docs']))

########NEW FILE########
__FILENAME__ = test_server
import os.path
import threading
import string
import re
import random
import shutil
import socket
import time
from subprocess import Popen, PIPE
from riak.util import deep_merge

try:
    bytes
except NameError:
    bytes = str


class Atom(object):
    def __init__(self, s):
        self.str = s

    def __str__(self):
        return str(self.str)

    def __repr__(self):
        return repr(self.str)

    def __eq__(self, other):
        return self.str == other

    def __cmp__(self, other):
        return cmp(self.str, other)


def erlang_config(hash, depth=1):
    def printable(item):
        k, v = item
        if isinstance(v, str):
            p = '"%s"' % v
        elif isinstance(v, dict):
            p = erlang_config(v, depth + 1)
        elif isinstance(v, bool):
            p = ("%s" % v).lower()
        else:
            p = "%s" % v

        return "{%s, %s}" % (k, p)

    padding = '    ' * depth
    parent_padding = '    ' * (depth - 1)
    values = (",\n%s" % padding).join(map(printable, hash.items()))
    return "[\n%s%s\n%s]" % (padding, values, parent_padding)


class TestServer(object):
    VM_ARGS_DEFAULTS = {
        "-name": "riaktest%d@127.0.0.1" % random.randint(0, 100000),
        "-setcookie": "%d_%d" % (random.randint(0, 100000),
                                 random.randint(0, 100000)),
        "+K": "true",
        "+A": 64,
        "-smp": "enable",
        "-env ERL_MAX_PORTS": 4096,
        "-env ERL_FULLSWEEP_AFTER": 10,
        "-pa": os.path.abspath(os.path.join(os.path.dirname(__file__),
                                            "erl_src"))
    }

    APP_CONFIG_DEFAULTS = {
        "riak_core": {
            "web_ip": "127.0.0.1",
            "web_port": 9000,
            "handoff_port": 9001,
            "ring_creation_size": 64
        },
        "riak_kv": {
            "storage_backend": Atom("riak_kv_test_backend"),
            "pb_ip": "127.0.0.1",
            "pb_port": 9002,
            "js_vm_count": 8,
            "js_max_vm_mem": 8,
            "js_thread_stack": 16,
            "riak_kv_stat": True,
            "map_cache_size": 0,
            "vnode_cache_entries": 0,
            "test": True,
            "memory_backend": {
                "test": True,
            },
        },
        "riak_search": {
            "enabled": True,
            "search_backend": Atom("riak_search_test_backend")
        },
    }

    DEFAULT_BASE_DIR = "RUNNER_BASE_DIR=${RUNNER_SCRIPT_DIR%/*}"

    _temp_bin = None
    _temp_etc = None
    _temp_log = None
    _temp_pipe = None

    def __init__(self, tmp_dir="/tmp/riak/test_server",
                 bin_dir=os.path.expanduser("~/.riak/install/riak-0.14.2/bin"),
                 vm_args=None, **options):
        self._lock = threading.Lock()
        self.temp_dir = tmp_dir
        self.bin_dir = bin_dir
        self._prepared = False
        self._started = False
        self.vm_args = self.VM_ARGS_DEFAULTS.copy()
        if vm_args is not None:
            self.vm_args = deep_merge(self.vm_args, vm_args)

        self.app_config = self.APP_CONFIG_DEFAULTS.copy()
        for key, value in options.items():
            if key in self.app_config:
                self.app_config[key] = deep_merge(self.app_config[key], value)
        ring_dir = os.path.join(self.temp_dir, "data", "ring")
        crash_log = os.path.join(self.temp_dir, "log", "crash.log")
        self.app_config["riak_core"]["ring_state_dir"] = ring_dir
        self.app_config["riak_core"]["platform_data_dir"] = self.temp_dir
        self.app_config["lager"] = {"crash_log": crash_log}

    def prepare(self):
        if not self._prepared:
            self.touch_ssl_distribution_args()
            self.create_temp_directories()
            self._riak_script = os.path.join(self._temp_bin, "riak")
            self.write_riak_script()
            self.write_vm_args()
            self.write_app_config()
            self._prepared = True

    def create_temp_directories(self):
        directories = ["bin", "etc", "log", "data", "pipe"]
        for directory in directories:
            dir = os.path.normpath(os.path.join(self.temp_dir, directory))
            if not os.path.exists(dir):
                os.makedirs(dir)
            setattr(self, "_temp_%s" % directory, dir)

    def start(self):
        if self._prepared and not self._started:
            with self._lock:
                self._server = Popen([self._riak_script, "console"],
                                     stdin=PIPE, stdout=PIPE, stderr=PIPE)
                self._server.stdin.write("\n")
                self._server.stdin.flush()
                self.wait_for_erlang_prompt()
                self._started = True

    def stop(self):
        if self._started:
            with self._lock:
                self._server.stdin.write("init:stop().\n")
                self._server.stdin.flush()
                self._server.wait()
                self._started = False

    def cleanup(self):
        if self._started:
            self.stop()

        shutil.rmtree(self.temp_dir, True)
        self._prepared = False

    def recycle(self):
        if self._started:
            with self._lock:
                stdin = self._server.stdin
                if self._kv_backend() == "riak_kv_test_backend":
                    stdin.write("riak_kv_test_backend:reset().\n")
                    stdin.flush()
                    self.wait_for_erlang_prompt()

                    if self.app_config["riak_search"]["enabled"]:
                        stdin.write("riak_search_test_backend:reset().\n")
                        stdin.flush()
                        self.wait_for_erlang_prompt()
                else:
                    stdin.write("init:restart().\n")
                    stdin.flush()
                    self.wait_for_erlang_prompt()
                    self.wait_for_startup()

    def wait_for_startup(self):
        listening = False
        while not listening:
            try:
                socket.create_connection((self._http_ip(), self._http_port()),
                                         1.0)
            except socket.error, (value, message):
                pass
            else:
                listening = True

    def wait_for_erlang_prompt(self):
        prompted = False
        buffer = ""
        while not prompted:
            line = self._server.stdout.readline()
            if len(line) > 0:
                buffer += line
            if re.search(r"\(%s\)\d+>" % self.vm_args["-name"], buffer):
                prompted = True
            if re.search(r'"Kernel pid terminated".*\n', buffer):
                raise Exception("Riak test server failed to start.")

    def write_riak_script(self):
        with open(self._riak_script, "wb") as temp_bin_file:
            with open(os.path.join(self.bin_dir, "riak"), "r") as riak_file:
                for line in riak_file.readlines():
                    line = re.sub("(RUNNER_SCRIPT_DIR=)(.*)", r'\1%s' %
                                  self._temp_bin,
                                  line)
                    line = re.sub("(RUNNER_ETC_DIR=)(.*)", r'\1%s' %
                                  self._temp_etc, line)
                    line = re.sub("(RUNNER_USER=)(.*)", r'\1', line)
                    line = re.sub("(RUNNER_LOG_DIR=)(.*)", r'\1%s' %
                                  self._temp_log, line)
                    line = re.sub("(PIPE_DIR=)(.*)", r'\1%s' %
                                  self._temp_pipe, line)
                    line = re.sub("(PLATFORM_DATA_DIR=)(.*)", r'\1%s' %
                                  self.temp_dir, line)

                    if (string.strip(line) == self.DEFAULT_BASE_DIR):
                        line = ("RUNNER_BASE_DIR=%s\n" %
                                os.path.normpath(os.path.join(self.bin_dir,
                                                              "..")))

                    temp_bin_file.write(line)

                os.fchmod(temp_bin_file.fileno(), 0755)

    def write_vm_args(self):
        with open(self._vm_args_path(), 'wb') as vm_args:
            for arg, value in self.vm_args.items():
                vm_args.write("%s %s\n" % (arg, value))

    def write_app_config(self):
        with open(self._app_config_path(), "wb") as app_config:
            app_config.write(erlang_config(self.app_config))
            app_config.write(".")

    def touch_ssl_distribution_args(self):
        # To make sure that the ssl_distribution.args file is present,
        # the control script in the source node has to have been run at
        # least once. Running the `chkconfig` command is innocuous
        # enough to accomplish this without other side-effects.
        script = os.path.join(self.bin_dir, "riak")
        Popen([script, "chkconfig"],
              stdin=PIPE, stdout=PIPE, stderr=PIPE).communicate()

    def _kv_backend(self):
        return self.app_config["riak_kv"]["storage_backend"]

    def _http_ip(self):
        return self.app_config["riak_core"]["web_ip"]

    def _http_port(self):
        return self.app_config["riak_core"]["web_port"]

    def _app_config_path(self):
        return os.path.join(self._temp_etc, "app.config")

    def _vm_args_path(self):
        return os.path.join(self._temp_etc, "vm.args")


if __name__ == "__main__":
    server = TestServer()
    server.prepare()
    server.start()
    print("Started...")
    time.sleep(20)
    print("Recycling...")
    server.recycle()
    time.sleep(20)
    server.stop()
    server.cleanup()

########NEW FILE########
__FILENAME__ = feature_detect
"""
Copyright 2012 Basho Technologies, Inc.

This file is provided to you under the Apache License,
Version 2.0 (the "License"); you may not use this file
except in compliance with the License.  You may obtain
a copy of the License at

  http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on an
"AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
KIND, either express or implied.  See the License for the
specific language governing permissions and limitations
under the License.
"""

from distutils.version import LooseVersion
from riak.util import lazy_property


versions = {
    1: LooseVersion("1.0.0"),
    1.1: LooseVersion("1.1.0"),
    1.2: LooseVersion("1.2.0"),
    1.4: LooseVersion("1.4.0"),
    1.44: LooseVersion("1.4.4"),
    2.0: LooseVersion("2.0.0")
}


class FeatureDetection(object):
    """
    Implements boolean methods that can be checked for the presence of
    specific server-side features. Subclasses must implement the
    :meth:`_server_version` method to use this functionality, which
    should return the server's version as a string.

    :class:`FeatureDetection` is a parent class of
    :class:`RiakTransport <riak.transports.transport.RiakTransport>`.
    """

    def _server_version(self):
        """
        Gets the server version from the server. To be implemented by
        the individual transport class.

        :rtype: string
        """
        raise NotImplementedError

    def phaseless_mapred(self):
        """
        Whether MapReduce requests can be submitted without phases.

        :rtype: bool
        """
        return self.server_version >= versions[1.1]

    def pb_indexes(self):
        """
        Whether secondary index queries are supported over Protocol
        Buffers

        :rtype: bool
        """
        return self.server_version >= versions[1.2]

    def pb_search_admin(self):
        """
        Whether search administration is supported over Protocol Buffers

        :rtype: bool
        """
        return self.server_version >= versions[2.0]

    def pb_search(self):
        """
        Whether search queries are supported over Protocol Buffers

        :rtype: bool
        """
        return self.server_version >= versions[1.2]

    def pb_conditionals(self):
        """
        Whether conditional fetch/store semantics are supported over
        Protocol Buffers

        :rtype: bool
        """
        return self.server_version >= versions[1]

    def quorum_controls(self):
        """
        Whether additional quorums and FSM controls are available,
        e.g. primary quorums, basic_quorum, notfound_ok

        :rtype: bool
        """
        return self.server_version >= versions[1]

    def tombstone_vclocks(self):
        """
        Whether 'not found' responses might include vclocks

        :rtype: bool
        """
        return self.server_version >= versions[1]

    def pb_head(self):
        """
        Whether partial-fetches (vclock and metadata only) are
        supported over Protocol Buffers

        :rtype: bool
        """
        return self.server_version >= versions[1]

    def pb_clear_bucket_props(self):
        """
        Whether bucket properties can be cleared over Protocol
        Buffers.

        :rtype: bool
        """
        return self.server_version >= versions[1.4]

    def pb_all_bucket_props(self):
        """
        Whether all normal bucket properties are supported over
        Protocol Buffers.

        :rtype: bool
        """
        return self.server_version >= versions[1.4]

    def counters(self):
        """
        Whether CRDT counters are supported.

        :rtype: bool
        """
        return self.server_version >= versions[1.4]

    def bucket_stream(self):
        """
        Whether streaming bucket lists are supported.

        :rtype: bool
        """
        return self.server_version >= versions[1.4]

    def client_timeouts(self):
        """
        Whether client-supplied timeouts are supported.

        :rtype: bool
        """
        return self.server_version >= versions[1.4]

    def stream_indexes(self):
        """
        Whether secondary indexes support streaming responses.

        :rtype: bool
        """
        return self.server_version >= versions[1.4]

    def index_term_regex(self):
        """
        Whether secondary indexes supports a regexp term filter.

        :rtype: bool
        """
        return self.server_version >= versions[1.44]

    def bucket_types(self):
        """
        Whether bucket-types are supported.

        :rtype: bool
        """
        return self.server_version >= versions[2.0]

    @lazy_property
    def server_version(self):
        return LooseVersion(self._server_version())

########NEW FILE########
__FILENAME__ = codec
"""
Copyright 2012 Basho Technologies, Inc.
Copyright 2010 Rusty Klophaus <rusty@basho.com>
Copyright 2010 Justin Sheehy <justin@basho.com>
Copyright 2009 Jay Baird <jay@mochimedia.com>

This file is provided to you under the Apache License,
Version 2.0 (the "License"); you may not use this file
except in compliance with the License.  You may obtain
a copy of the License at

  http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on an
"AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
KIND, either express or implied.  See the License for the
specific language governing permissions and limitations
under the License.
"""

# subtract length of "Link: " header string and newline
MAX_LINK_HEADER_SIZE = 8192 - 8


import re
import csv
import urllib
from cgi import parse_header
from email import message_from_string
from rfc822 import parsedate_tz, mktime_tz
from xml.etree import ElementTree
from riak import RiakError
from riak.content import RiakContent
from riak.riak_object import VClock
from riak.multidict import MultiDict
from riak.transports.http.search import XMLSearchResult
from riak.util import decode_index_value


class RiakHttpCodec(object):
    """
    Methods for HTTP transport that marshals and unmarshals HTTP
    messages.
    """

    def _parse_body(self, robj, response, expected_statuses):
        """
        Parse the body of an object response and populate the object.
        """
        # If no response given, then return.
        if response is None:
            return None

        status, headers, data = response

        # Check if the server is down(status==0)
        if not status:
            m = 'Could not contact Riak Server: http://{0}:{1}!'.format(
                self._node.host, self._node.http_port)
            raise RiakError(m)

        # Make sure expected code came back
        self.check_http_code(status, expected_statuses)

        if 'x-riak-vclock' in headers:
            robj.vclock = VClock(headers['x-riak-vclock'], 'base64')

        # If 404(Not Found), then clear the object.
        if status == 404:
            robj.siblings = []
            return None
        # If 201 Created, we need to extract the location and set the
        # key on the object.
        elif status == 201:
            robj.key = headers['location'].strip().split('/')[-1]
        # If 300(Siblings), apply the siblings to the object
        elif status == 300:
            ctype, params = parse_header(headers['content-type'])
            if ctype == 'multipart/mixed':
                boundary = re.compile('\r?\n--%s(?:--)?\r?\n' %
                                      re.escape(params['boundary']))
                parts = [message_from_string(p)
                         for p in re.split(boundary, data)[1:-1]]
                robj.siblings = [self._parse_sibling(RiakContent(robj),
                                                     part.items(),
                                                     part.get_payload())
                                 for part in parts]

                # Invoke sibling-resolution logic
                if robj.resolver is not None:
                    robj.resolver(robj)

                return robj
            else:
                raise Exception('unexpected sibling response format: {0}'.
                                format(ctype))

        robj.siblings = [self._parse_sibling(RiakContent(robj),
                                             headers.items(), data)]

        return robj

    def _parse_sibling(self, sibling, headers, data):
        """
        Parses a single sibling out of a response.
        """

        sibling.exists = True

        # Parse the headers...
        for header, value in headers:
            header = header.lower()
            if header == 'content-type':
                sibling.content_type, sibling.charset = \
                    self._parse_content_type(value)
            elif header == 'etag':
                sibling.etag = value
            elif header == 'link':
                sibling.links = self._parse_links(value)
            elif header == 'last-modified':
                sibling.last_modified = mktime_tz(parsedate_tz(value))
            elif header.startswith('x-riak-meta-'):
                metakey = header.replace('x-riak-meta-', '')
                sibling.usermeta[metakey] = value
            elif header.startswith('x-riak-index-'):
                field = header.replace('x-riak-index-', '')
                reader = csv.reader([value], skipinitialspace=True)
                for line in reader:
                    for token in line:
                        token = decode_index_value(field, token)
                        sibling.add_index(field, token)
            elif header == 'x-riak-deleted':
                sibling.exists = False

        sibling.encoded_data = data

        return sibling

    def _to_link_header(self, link):
        """
        Convert the link tuple to a link header string. Used internally.
        """
        try:
            bucket, key, tag = link
        except ValueError:
            raise RiakError("Invalid link tuple %s" % link)
        tag = tag if tag is not None else bucket
        url = self.object_path(bucket, key)
        header = '<%s>; riaktag="%s"' % (url, tag)
        return header

    def _parse_links(self, linkHeaders):
        links = []
        oldform = "</([^/]+)/([^/]+)/([^/]+)>; ?riaktag=\"([^\"]+)\""
        newform = "</(buckets)/([^/]+)/keys/([^/]+)>; ?riaktag=\"([^\"]+)\""
        for linkHeader in linkHeaders.strip().split(','):
            linkHeader = linkHeader.strip()
            matches = (re.match(oldform, linkHeader) or
                       re.match(newform, linkHeader))
            if matches is not None:
                link = (urllib.unquote_plus(matches.group(2)),
                        urllib.unquote_plus(matches.group(3)),
                        urllib.unquote_plus(matches.group(4)))
                links.append(link)
        return links

    def _add_links_for_riak_object(self, robject, headers):
        links = robject.links
        if links:
            current_header = ''
            for link in links:
                header = self._to_link_header(link)
                if len(current_header + header) > MAX_LINK_HEADER_SIZE:
                    headers.add('Link', current_header)
                    current_header = ''

                if current_header != '':
                    header = ', ' + header
                current_header += header

            headers.add('Link', current_header)

        return headers

    def _build_put_headers(self, robj, if_none_match=False):
        """Build the headers for a POST/PUT request."""

        # Construct the headers...
        if robj.charset is not None:
            content_type = ('%s; charset="%s"' %
                            (robj.content_type, robj.charset))
        else:
            content_type = robj.content_type

        headers = MultiDict({'Content-Type': content_type,
                             'X-Riak-ClientId': self._client_id})

        # Add the vclock if it exists...
        if robj.vclock is not None:
            headers['X-Riak-Vclock'] = robj.vclock.encode('base64')

        # Create the header from metadata
        self._add_links_for_riak_object(robj, headers)

        for key, value in robj.usermeta.iteritems():
            headers['X-Riak-Meta-%s' % key] = value

        for field, value in robj.indexes:
            key = 'X-Riak-Index-%s' % field
            if key in headers:
                headers[key] += ", " + str(value)
            else:
                headers[key] = str(value)

        if if_none_match:
            headers['If-None-Match'] = '*'

        return headers

    def _normalize_json_search_response(self, json):
        """
        Normalizes a JSON search response so that PB and HTTP have the
        same return value
        """
        result = {}
        if u'response' in json:
            result['num_found'] = json[u'response'][u'numFound']
            result['max_score'] = float(json[u'response'][u'maxScore'])
            docs = []
            for doc in json[u'response'][u'docs']:
                resdoc = {}
                if u'_yz_rk' in doc:
                    # Is this a Riak 2.0 result?
                    resdoc = doc
                else:
                    # Riak Search 1.0 Legacy assumptions about format
                    resdoc[u'id'] = doc[u'id']
                    if u'fields' in doc:
                        for k, v in doc[u'fields'].iteritems():
                            resdoc[k] = v
                docs.append(resdoc)
            result['docs'] = docs
        return result

    def _normalize_xml_search_response(self, xml):
        """
        Normalizes an XML search response so that PB and HTTP have the
        same return value
        """
        target = XMLSearchResult()
        parser = ElementTree.XMLParser(target=target)
        parser.feed(xml)
        return parser.close()

    def _parse_content_type(self, value):
        """
        Split the content-type header into two parts:
        1) Actual main/sub encoding type
        2) charset

        :param value: Complete MIME content-type string
        """
        content_type, params = parse_header(value)
        if 'charset' in params:
            charset = params['charset']
        else:
            charset = None
        return content_type, charset

########NEW FILE########
__FILENAME__ = connection
"""
Copyright 2012 Basho Technologies, Inc.

This file is provided to you under the Apache License,
Version 2.0 (the "License"); you may not use this file
except in compliance with the License.  You may obtain
a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on an
"AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
KIND, either express or implied.  See the License for the
specific language governing permissions and limitations
under the License.
"""

import httplib


class RiakHttpConnection(object):
    """
    Connection and low-level request methods for RiakHttpTransport.
    """

    def _request(self, method, uri, headers={}, body='', stream=False):
        """
        Given a Method, URL, Headers, and Body, perform and HTTP
        request, and return a 3-tuple containing the response status,
        response headers (as httplib.HTTPMessage), and response body.
        """
        response = None
        headers.setdefault('Accept',
                           'multipart/mixed, application/json, */*;q=0.5')
        try:
            self._connection.request(method, uri, body, headers)
            response = self._connection.getresponse()

            if stream:
                # The caller is responsible for fully reading the
                # response and closing it when streaming.
                response_body = response
            else:
                response_body = response.read()
        finally:
            if response and not stream:
                response.close()

        return response.status, response.msg, response_body

    def _connect(self):
        self._connection = self._connection_class(self._node.host,
                                                  self._node.http_port)
        # Forces the population of stats and resources before any
        # other requests are made.
        self.server_version

    def close(self):
        """
        Closes the underlying HTTP connection.
        """
        try:
            self._connection.close()
        except httplib.NotConnected:
            pass

    # These are set by the RiakHttpTransport initializer
    _connection_class = httplib.HTTPConnection
    _node = None

########NEW FILE########
__FILENAME__ = resources
"""
Copyright 2012 Basho Technologies, Inc.

This file is provided to you under the Apache License,
Version 2.0 (the "License"); you may not use this file
except in compliance with the License.  You may obtain
a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on an
"AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
KIND, either express or implied.  See the License for the
specific language governing permissions and limitations
under the License.
"""

import re
from urllib import quote_plus, urlencode
from riak import RiakError
from riak.util import lazy_property


class RiakHttpResources(object):
    """
    Methods for RiakHttpTransport related to URL generation, i.e.
    creating the proper paths.
    """

    def ping_path(self):
        return mkpath(self.riak_kv_wm_ping)

    def stats_path(self):
        return mkpath(self.riak_kv_wm_stats)

    def mapred_path(self, **options):
        return mkpath(self.riak_kv_wm_mapred, **options)

    def bucket_list_path(self, bucket_type=None, **options):
        query = {'buckets': True}
        query.update(options)
        if self.riak_kv_wm_bucket_type and bucket_type:
            return mkpath("/types", quote_plus(bucket_type),
                          "buckets", **query)
        elif self.riak_kv_wm_buckets:
            return mkpath("/buckets", **query)
        else:
            return mkpath(self.riak_kv_wm_raw, **query)

    def bucket_properties_path(self, bucket, bucket_type=None, **options):
        if self.riak_kv_wm_bucket_type and bucket_type:
            return mkpath("/types", quote_plus(bucket_type), "buckets",
                          quote_plus(bucket), "props", **options)
        elif self.riak_kv_wm_buckets:
            return mkpath("/buckets", quote_plus(bucket),
                          "props", **options)
        else:
            query = options.copy()
            query.update(props=True, keys=False)
            return mkpath(self.riak_kv_wm_raw, quote_plus(bucket), **query)

    def bucket_type_properties_path(self, bucket_type, **options):
        return mkpath("/types", quote_plus(bucket_type), "props",
                      **options)

    def key_list_path(self, bucket, bucket_type=None, **options):
        query = {'keys': True, 'props': False}
        query.update(options)
        if self.riak_kv_wm_bucket_type and bucket_type:
            return mkpath("/types", quote_plus(bucket_type), "buckets",
                          quote_plus(bucket), "keys", **query)
        if self.riak_kv_wm_buckets:
            return mkpath("/buckets", quote_plus(bucket), "keys",
                          **query)
        else:
            return mkpath(self.riak_kv_wm_raw, quote_plus(bucket), **query)

    def object_path(self, bucket, key=None, bucket_type=None, **options):
        if key:
            key = quote_plus(key)
        if self.riak_kv_wm_bucket_type and bucket_type:
            return mkpath("/types", quote_plus(bucket_type), "buckets",
                          quote_plus(bucket), "keys", key, **options)
        elif self.riak_kv_wm_buckets:
            return mkpath("/buckets", quote_plus(bucket), "keys",
                          key, **options)
        else:
            return mkpath(self.riak_kv_wm_raw, quote_plus(bucket), key,
                          **options)

    def index_path(self, bucket, index, start, finish=None, bucket_type=None,
                   **options):
        if not self.riak_kv_wm_buckets:
            raise RiakError("Indexes are unsupported by this Riak node")
        if finish:
            finish = quote_plus(str(finish))
        if self.riak_kv_wm_bucket_type and bucket_type:
            return mkpath("/types", quote_plus(bucket_type),
                          "buckets", quote_plus(bucket),
                          "index", quote_plus(index), quote_plus(str(start)),
                          finish, **options)
        else:
            return mkpath("/buckets", quote_plus(bucket),
                          "index", quote_plus(index), quote_plus(str(start)),
                          finish, **options)

    def search_index_path(self, index=None, **options):
        """
        Builds a Yokozuna search index URL.

        :param index: optional name of a yz index
        :type index: string
        :param options: optional list of additional arguments
        :type index: dict
        :rtype URL string
        """
        if not self.yz_wm_index:
            raise RiakError("Yokozuna search is unsupported by this Riak node")
        if index:
            quote_plus(index)
        return mkpath(self.yz_wm_index, "index", index, **options)

    def search_schema_path(self, index, **options):
        """
        Builds a Yokozuna search Solr schema URL.

        :param index: a name of a yz solr schema
        :type index: string
        :param options: optional list of additional arguments
        :type index: dict
        :rtype URL string
        """
        if not self.yz_wm_schema:
            raise RiakError("Yokozuna search is unsupported by this Riak node")
        return mkpath(self.yz_wm_schema, "schema", quote_plus(index),
                      **options)

    def solr_select_path(self, index, query, **options):
        if not self.riak_solr_searcher_wm and not self.yz_wm_search:
            raise RiakError("Search is unsupported by this Riak node")
        qs = {'q': query, 'wt': 'json', 'fl': '*,score'}
        qs.update(options)
        if index:
            index = quote_plus(index)
        return mkpath("/solr", index, "select", **qs)

    def solr_update_path(self, index):
        if not self.riak_solr_searcher_wm:
            raise RiakError("Riak Search 1 is unsupported by this Riak node")
        if index:
            index = quote_plus(index)
        return mkpath(self.riak_solr_indexer_wm, index, "update")

    def counters_path(self, bucket, key, **options):
        if not self.riak_kv_wm_counter:
            raise RiakError("Counters are unsupported by this Riak node")

        return mkpath(self.riak_kv_wm_buckets, quote_plus(bucket), "counters",
                      quote_plus(key), **options)

    # Feature detection overrides
    def bucket_types(self):
        return self.riak_kv_wm_bucket_type is not None

    def index_term_regex(self):
        if self.riak_kv_wm_bucket_type is not None:
            return True
        else:
            return super(RiakHttpResources, self).index_term_regex()

    # Resource root paths
    @lazy_property
    def riak_kv_wm_bucket_type(self):
        if 'riak_kv_wm_bucket_type' in self.resources:
            return "/types"

    @lazy_property
    def riak_kv_wm_buckets(self):
        if 'riak_kv_wm_buckets' in self.resources:
            return "/buckets"

    @lazy_property
    def riak_kv_wm_raw(self):
        return self.resources.get('riak_kv_wm_raw') or "/riak"

    @lazy_property
    def riak_kv_wm_link_walker(self):
        return self.resources.get('riak_kv_wm_linkwalker') or "/riak"

    @lazy_property
    def riak_kv_wm_mapred(self):
        return self.resources.get('riak_kv_wm_mapred') or "/mapred"

    @lazy_property
    def riak_kv_wm_ping(self):
        return self.resources.get('riak_kv_wm_ping') or "/ping"

    @lazy_property
    def riak_kv_wm_stats(self):
        return self.resources.get('riak_kv_wm_stats') or "/stats"

    @lazy_property
    def riak_solr_searcher_wm(self):
        return self.resources.get('riak_solr_searcher_wm')

    @lazy_property
    def riak_solr_indexer_wm(self):
        return self.resources.get('riak_solr_indexer_wm')

    @lazy_property
    def riak_kv_wm_counter(self):
        return self.resources.get('riak_kv_wm_counter')

    @lazy_property
    def yz_wm_search(self):
        return self.resources.get('yz_wm_search')

    @lazy_property
    def yz_wm_extract(self):
        return self.resources.get('yz_wm_extract')

    @lazy_property
    def yz_wm_schema(self):
        return self.resources.get('yz_wm_schema')

    @lazy_property
    def yz_wm_index(self):
        return self.resources.get('yz_wm_index')

    @lazy_property
    def resources(self):
        return self.get_resources()


def mkpath(*segments, **query):
    """
    Constructs the path & query portion of a URI from path segments
    and a dict.
    """
    # Remove empty segments (e.g. no key specified)
    segments = [s for s in segments if s is not None]
    # Join the segments into a path
    pathstring = '/'.join(segments)
    # Remove extra slashes
    pathstring = re.sub('/+', '/', pathstring)

    # Add the query string if it exists
    _query = {}
    for key in query:
        if query[key] in [False, True]:
            _query[key] = str(query[key]).lower()
        elif query[key] is not None:
            if isinstance(query[key], unicode):
                _query[key] = query[key].encode('utf-8')
            else:
                _query[key] = query[key]

    if len(_query) > 0:
        pathstring += "?" + urlencode(_query)

    if not pathstring.startswith('/'):
        pathstring = '/' + pathstring

    return pathstring

########NEW FILE########
__FILENAME__ = search
class XMLSearchResult(object):
    # Match tags that are document fields
    fieldtags = ['str', 'int', 'date']

    def __init__(self):
        # Results
        self.num_found = 0
        self.max_score = 0.0
        self.docs = []

        # Parser state
        self.currdoc = None
        self.currfield = None
        self.currvalue = None

    def start(self, tag, attrib):
        if tag == 'result':
            self.num_found = int(attrib['numFound'])
            self.max_score = float(attrib['maxScore'])
        elif tag == 'doc':
            self.currdoc = {}
        elif tag in self.fieldtags and self.currdoc is not None:
            self.currfield = attrib['name']

    def end(self, tag):
        if tag == 'doc' and self.currdoc is not None:
            self.docs.append(self.currdoc)
            self.currdoc = None
        elif tag in self.fieldtags and self.currdoc is not None:
            if tag == 'int':
                self.currvalue = int(self.currvalue)
            self.currdoc[self.currfield] = self.currvalue
            self.currfield = None
            self.currvalue = None

    def data(self, data):
        if self.currfield:
            # riak_solr_output adds NL + 6 spaces
            data = data.rstrip()
            if self.currvalue:
                self.currvalue += data
            else:
                self.currvalue = data

    def close(self):
        return {'num_found': self.num_found,
                'max_score': self.max_score,
                'docs': self.docs}

########NEW FILE########
__FILENAME__ = stream
"""
Copyright 2012 Basho Technologies, Inc.

This file is provided to you under the Apache License,
Version 2.0 (the "License"); you may not use this file
except in compliance with the License.  You may obtain
a copy of the License at

  http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on an
"AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
KIND, either express or implied.  See the License for the
specific language governing permissions and limitations
under the License.
"""

import json
import string
import re
from cgi import parse_header
from email import message_from_string
from riak.util import decode_index_value
from riak.client.index_page import CONTINUATION
from riak import RiakError


class RiakHttpStream(object):
    """
    Base class for HTTP streaming iterators.
    """

    BLOCK_SIZE = 2048

    def __init__(self, response):
        self.response = response
        self.buffer = ''
        self.response_done = False

    def __iter__(self):
        return self

    def _read(self):
        chunk = self.response.read(self.BLOCK_SIZE)
        if chunk == '':
            self.response_done = True
        self.buffer += chunk

    def next(self):
        raise NotImplementedError

    def close(self):
        pass


class RiakHttpJsonStream(RiakHttpStream):
    _json_field = None

    def next(self):
        while '}' not in self.buffer and not self.response_done:
            self._read()

        if '}' in self.buffer:
            idx = string.index(self.buffer, '}') + 1
            chunk = self.buffer[:idx]
            self.buffer = self.buffer[idx:]
            jsdict = json.loads(chunk)
            if 'error' in jsdict:
                self.close()
                raise RiakError(jsdict['error'])
            field = jsdict[self._json_field]
            return field
        else:
            raise StopIteration


class RiakHttpKeyStream(RiakHttpJsonStream):
    """
    Streaming iterator for list-keys over HTTP
    """
    _json_field = u'keys'


class RiakHttpBucketStream(RiakHttpJsonStream):
    """
    Streaming iterator for list-buckets over HTTP
    """
    _json_field = u'buckets'


class RiakHttpMultipartStream(RiakHttpStream):
    """
    Streaming iterator for multipart messages over HTTP
    """
    def __init__(self, response):
        super(RiakHttpMultipartStream, self).__init__(response)
        ctypehdr = response.getheader('content-type')
        _, params = parse_header(ctypehdr)
        self.boundary_re = re.compile('\r?\n--%s(?:--)?\r?\n' %
                                      re.escape(params['boundary']))
        self.next_boundary = None
        self.seen_first = False

    def next(self):
        # multipart/mixed starts with a boundary, then the first part.
        if not self.seen_first:
            self.read_until_boundary()
            self.advance_buffer()
            self.seen_first = True

        self.read_until_boundary()

        if self.next_boundary:
            part = self.advance_buffer()
            message = message_from_string(part)
            return message
        else:
            raise StopIteration

    def try_match(self):
        self.next_boundary = self.boundary_re.search(self.buffer)
        return self.next_boundary

    def advance_buffer(self):
        part = self.buffer[:self.next_boundary.start()]
        self.buffer = self.buffer[self.next_boundary.end():]
        self.next_boundary = None
        return part

    def read_until_boundary(self):
        while not self.try_match() and not self.response_done:
            self._read()


class RiakHttpMapReduceStream(RiakHttpMultipartStream):
    """
    Streaming iterator for MapReduce over HTTP
    """

    def next(self):
        message = super(RiakHttpMapReduceStream, self).next()
        payload = json.loads(message.get_payload())
        return payload['phase'], payload['data']


class RiakHttpIndexStream(RiakHttpMultipartStream):
    """
    Streaming iterator for secondary indexes over HTTP
    """

    def __init__(self, response, index, return_terms):
        super(RiakHttpIndexStream, self).__init__(response)
        self.index = index
        self.return_terms = return_terms

    def next(self):
        message = super(RiakHttpIndexStream, self).next()
        payload = json.loads(message.get_payload())
        if u'error' in payload:
            raise RiakError(payload[u'error'])
        elif u'keys' in payload:
            return payload[u'keys']
        elif u'results' in payload:
            structs = payload[u'results']
            # Format is {"results":[{"2ikey":"primarykey"}, ...]}
            return [self._decode_pair(d.items()[0]) for d in structs]
        elif u'continuation' in payload:
            return CONTINUATION(payload[u'continuation'])

    def _decode_pair(self, pair):
        return (decode_index_value(self.index, pair[0]), pair[1])

########NEW FILE########
__FILENAME__ = transport
"""
Copyright 2012 Basho Technologies, Inc.
Copyright 2010 Rusty Klophaus <rusty@basho.com>
Copyright 2010 Justin Sheehy <justin@basho.com>
Copyright 2009 Jay Baird <jay@mochimedia.com>

This file is provided to you under the Apache License,
Version 2.0 (the "License"); you may not use this file
except in compliance with the License.  You may obtain
a copy of the License at

  http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on an
"AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
KIND, either express or implied.  See the License for the
specific language governing permissions and limitations
under the License.
"""

try:
    import simplejson as json
except ImportError:
    import json


import httplib
from xml.dom.minidom import Document
from riak.transports.transport import RiakTransport
from riak.transports.http.resources import RiakHttpResources
from riak.transports.http.connection import RiakHttpConnection
from riak.transports.http.codec import RiakHttpCodec
from riak.transports.http.stream import (
    RiakHttpKeyStream,
    RiakHttpMapReduceStream,
    RiakHttpBucketStream,
    RiakHttpIndexStream)
from riak import RiakError
from riak.util import decode_index_value


class RiakHttpTransport(RiakHttpConnection, RiakHttpResources, RiakHttpCodec,
                        RiakTransport):
    """
    The RiakHttpTransport object holds information necessary to
    connect to Riak via HTTP.
    """

    def __init__(self, node=None,
                 client=None,
                 connection_class=httplib.HTTPConnection,
                 client_id=None,
                 **unused_options):
        """
        Construct a new HTTP connection to Riak.
        """
        super(RiakHttpTransport, self).__init__()

        self._client = client
        self._node = node
        self._connection_class = connection_class
        self._client_id = client_id
        if not self._client_id:
            self._client_id = self.make_random_client_id()
        self._connect()

    def ping(self):
        """
        Check server is alive over HTTP
        """
        status, _, body = self._request('GET', self.ping_path())
        return(status is not None) and (body == 'OK')

    def stats(self):
        """
        Gets performance statistics and server information
        """
        status, _, body = self._request('GET', self.stats_path(),
                                        {'Accept': 'application/json'})
        if status == 200:
            return json.loads(body)
        else:
            return None

    # FeatureDetection API - private
    def _server_version(self):
        stats = self.stats()
        if stats is not None:
            return stats['riak_kv_version']
        # If stats is disabled, we can't assume the Riak version
        # is >= 1.1. However, we can assume the new URL scheme is
        # at least version 1.0
        elif self.riak_kv_wm_buckets:
            return "1.0.0"
        else:
            return "0.14.0"

    def get_resources(self):
        """
        Gets a JSON mapping of server-side resource names to paths
        :rtype dict
        """
        status, _, body = self._request('GET', '/',
                                        {'Accept': 'application/json'})
        if status == 200:
            return json.loads(body)
        else:
            return {}

    def get(self, robj, r=None, pr=None, timeout=None):
        """
        Get a bucket/key from the server
        """
        # We could detect quorum_controls here but HTTP ignores
        # unknown flags/params.
        params = {'r': r, 'pr': pr, 'timeout': timeout}

        bucket_type = self._get_bucket_type(robj.bucket.bucket_type)

        url = self.object_path(robj.bucket.name, robj.key,
                               bucket_type=bucket_type, **params)
        response = self._request('GET', url)
        return self._parse_body(robj, response, [200, 300, 404])

    def put(self, robj, w=None, dw=None, pw=None, return_body=True,
            if_none_match=False, timeout=None):
        """
        Puts a (possibly new) object.
        """
        # We could detect quorum_controls here but HTTP ignores
        # unknown flags/params.
        params = {'returnbody': return_body, 'w': w, 'dw': dw, 'pw': pw,
                  'timeout': timeout}

        bucket_type = self._get_bucket_type(robj.bucket.bucket_type)

        url = self.object_path(robj.bucket.name, robj.key,
                               bucket_type=bucket_type,
                               **params)
        headers = self._build_put_headers(robj, if_none_match=if_none_match)
        content = bytearray(robj.encoded_data)

        if robj.key is None:
            expect = [201]
            method = 'POST'
        else:
            expect = [204]
            method = 'PUT'

        response = self._request(method, url, headers, content)
        if return_body:
            return self._parse_body(robj, response, [200, 201, 204, 300])
        else:
            self.check_http_code(response[0], expect)
            return None

    def delete(self, robj, rw=None, r=None, w=None, dw=None, pr=None, pw=None,
               timeout=None):
        """
        Delete an object.
        """
        # We could detect quorum_controls here but HTTP ignores
        # unknown flags/params.
        params = {'rw': rw, 'r': r, 'w': w, 'dw': dw, 'pr': pr, 'pw': pw,
                  'timeout': timeout}
        headers = {}

        bucket_type = self._get_bucket_type(robj.bucket.bucket_type)

        url = self.object_path(robj.bucket.name, robj.key,
                               bucket_type=bucket_type, **params)
        if self.tombstone_vclocks() and robj.vclock is not None:
            headers['X-Riak-Vclock'] = robj.vclock.encode('base64')
        response = self._request('DELETE', url, headers)
        self.check_http_code(response[0], [204, 404])
        return self

    def get_keys(self, bucket, timeout=None):
        """
        Fetch a list of keys for the bucket
        """
        bucket_type = self._get_bucket_type(bucket.bucket_type)
        url = self.key_list_path(bucket.name, bucket_type=bucket_type,
                                 timeout=timeout)
        status, _, body = self._request('GET', url)

        if status == 200:
            props = json.loads(body)
            return props['keys']
        else:
            raise RiakError('Error listing keys.')

    def stream_keys(self, bucket, timeout=None):
        bucket_type = self._get_bucket_type(bucket.bucket_type)
        url = self.key_list_path(bucket.name, bucket_type=bucket_type,
                                 keys='stream', timeout=timeout)
        status, headers, response = self._request('GET', url, stream=True)

        if status == 200:
            return RiakHttpKeyStream(response)
        else:
            raise RiakError('Error listing keys.')

    def get_buckets(self, bucket_type=None, timeout=None):
        """
        Fetch a list of all buckets
        """
        bucket_type = self._get_bucket_type(bucket_type)
        url = self.bucket_list_path(bucket_type=bucket_type,
                                    timeout=timeout)
        status, headers, body = self._request('GET', url)

        if status == 200:
            props = json.loads(body)
            return props['buckets']
        else:
            raise RiakError('Error getting buckets.')

    def stream_buckets(self, bucket_type=None, timeout=None):
        """
        Stream list of buckets through an iterator
        """
        if not self.bucket_stream():
            raise NotImplementedError('Streaming list-buckets is not '
                                      "supported on %s" %
                                      self.server_version.vstring)
        bucket_type = self._get_bucket_type(bucket_type)
        url = self.bucket_list_path(bucket_type=bucket_type,
                                    buckets="stream", timeout=timeout)
        status, headers, response = self._request('GET', url, stream=True)

        if status == 200:
            return RiakHttpBucketStream(response)
        else:
            raise RiakError('Error listing buckets.')

    def get_bucket_props(self, bucket):
        """
        Get properties for a bucket
        """
        bucket_type = self._get_bucket_type(bucket.bucket_type)
        url = self.bucket_properties_path(bucket.name,
                                          bucket_type=bucket_type)
        status, headers, body = self._request('GET', url)

        if status == 200:
            props = json.loads(body)
            return props['props']
        else:
            raise RiakError('Error getting bucket properties.')

    def set_bucket_props(self, bucket, props):
        """
        Set the properties on the bucket object given
        """
        bucket_type = self._get_bucket_type(bucket.bucket_type)
        url = self.bucket_properties_path(bucket.name,
                                          bucket_type=bucket_type)
        headers = {'Content-Type': 'application/json'}
        content = json.dumps({'props': props})

        # Run the request...
        status, _, _ = self._request('PUT', url, headers, content)

        if status != 204:
            raise RiakError('Error setting bucket properties.')
        return True

    def clear_bucket_props(self, bucket):
        """
        reset the properties on the bucket object given
        """
        bucket_type = self._get_bucket_type(bucket.bucket_type)
        url = self.bucket_properties_path(bucket.name,
                                          bucket_type=bucket_type)
        url = self.bucket_properties_path(bucket.name)
        headers = {'Content-Type': 'application/json'}

        # Run the request...
        status, _, _ = self._request('DELETE', url, headers, None)

        if status == 204:
            return True
        elif status == 405:
            return False
        else:
            raise RiakError('Error %s clearing bucket properties.'
                            % status)

    def get_bucket_type_props(self, bucket_type):
        """
        Get properties for a bucket-type
        """
        self._check_bucket_types(bucket_type)
        url = self.bucket_type_properties_path(bucket_type.name)
        status, headers, body = self._request('GET', url)

        if status == 200:
            props = json.loads(body)
            return props['props']
        else:
            raise RiakError('Error getting bucket-type properties.')

    def set_bucket_type_props(self, bucket_type, props):
        """
        Set the properties on the bucket-type
        """
        self._check_bucket_types(bucket_type)
        url = self.bucket_type_properties_path(bucket_type.name)
        headers = {'Content-Type': 'application/json'}
        content = json.dumps({'props': props})

        # Run the request...
        status, _, _ = self._request('PUT', url, headers, content)

        if status != 204:
            raise RiakError('Error setting bucket-type properties.')
        return True

    def mapred(self, inputs, query, timeout=None):
        """
        Run a MapReduce query.
        """
        # Construct the job, optionally set the timeout...
        content = self._construct_mapred_json(inputs, query, timeout)

        # Do the request...
        url = self.mapred_path()
        headers = {'Content-Type': 'application/json'}
        status, headers, body = self._request('POST', url, headers, content)

        # Make sure the expected status code came back...
        if status != 200:
            raise RiakError(
                'Error running MapReduce operation. Headers: %s Body: %s' %
                (repr(headers), repr(body)))

        result = json.loads(body)
        return result

    def stream_mapred(self, inputs, query, timeout=None):
        content = self._construct_mapred_json(inputs, query, timeout)

        url = self.mapred_path(chunked=True)
        reqheaders = {'Content-Type': 'application/json'}
        status, headers, response = self._request('POST', url, reqheaders,
                                                  content, stream=True)

        if status == 200:
            return RiakHttpMapReduceStream(response)
        else:
            raise RiakError(
                'Error running MapReduce operation. Headers: %s Body: %s' %
                (repr(headers), repr(response.read())))

    def get_index(self, bucket, index, startkey, endkey=None,
                  return_terms=None, max_results=None, continuation=None,
                  timeout=None, term_regex=None):
        """
        Performs a secondary index query.
        """
        if term_regex and not self.index_term_regex():
            raise NotImplementedError("Secondary index term_regex is not "
                                      "supported on %s" %
                                      self.server_version.vstring)

        if timeout == 'infinity':
            timeout = 0

        params = {'return_terms': return_terms, 'max_results': max_results,
                  'continuation': continuation, 'timeout': timeout,
                  'term_regex': term_regex}
        bucket_type = self._get_bucket_type(bucket.bucket_type)
        url = self.index_path(bucket.name, index, startkey, endkey,
                              bucket_type=bucket_type, **params)
        status, headers, body = self._request('GET', url)
        self.check_http_code(status, [200])
        json_data = json.loads(body)
        if return_terms and u'results' in json_data:
            results = []
            for result in json_data[u'results'][:]:
                term, key = result.items()[0]
                results.append((decode_index_value(index, term), key),)
        else:
            results = json_data[u'keys'][:]

        if max_results and u'continuation' in json_data:
            return (results, json_data[u'continuation'])
        else:
            return (results, None)

    def stream_index(self, bucket, index, startkey, endkey=None,
                     return_terms=None, max_results=None, continuation=None,
                     timeout=None, term_regex=None):
        """
        Streams a secondary index query.
        """
        if not self.stream_indexes():
            raise NotImplementedError("Secondary index streaming is not "
                                      "supported on %s" %
                                      self.server_version.vstring)

        if term_regex and not self.index_term_regex():
            raise NotImplementedError("Secondary index term_regex is not "
                                      "supported on %s" %
                                      self.server_version.vstring)

        if timeout == 'infinity':
            timeout = 0

        params = {'return_terms': return_terms, 'stream': True,
                  'max_results': max_results, 'continuation': continuation,
                  'timeout': timeout, 'term_regex': term_regex}
        bucket_type = self._get_bucket_type(bucket.bucket_type)
        url = self.index_path(bucket.name, index, startkey, endkey,
                              bucket_type=bucket_type, **params)
        status, headers, response = self._request('GET', url, stream=True)

        if status == 200:
            return RiakHttpIndexStream(response, index, return_terms)
        else:
            raise RiakError('Error streaming secondary index.')

    def create_search_index(self, index, schema=None, n_val=None):
        """
        Create a Solr search index for Yokozuna.

        :param index: a name of a yz index
        :type index: string
        :param schema: XML of Solr schema
        :type schema: string
        :param n_val: N value of the write
        :type n_val: int
        :rtype boolean
        """
        if not self.yz_wm_index:
            raise NotImplementedError("Search 2.0 administration is not "
                                      "supported for this version")

        url = self.search_index_path(index)
        headers = {'Content-Type': 'application/json'}
        content_dict = dict()
        if schema:
            content_dict['schema'] = schema
        if n_val:
            content_dict['n_val'] = n_val
        content = json.dumps(content_dict)

        # Run the request...
        status, _, _ = self._request('PUT', url, headers, content)

        if status != 204:
            raise RiakError('Error setting Search 2.0 index.')
        return True

    def get_search_index(self, index):
        """
        Fetch the specified Solr search index for Yokozuna.

        :param index: a name of a yz index
        :type index: string
        :rtype string
        """
        if not self.yz_wm_index:
            raise NotImplementedError("Search 2.0 administration is not "
                                      "supported for this version")

        url = self.search_index_path(index)

        # Run the request...
        status, headers, body = self._request('GET', url)

        if status == 200:
            return json.loads(body)
        else:
            raise RiakError('Error getting Search 2.0 index.')

    def list_search_indexes(self):
        """
        Return a list of Solr search indexes from Yokozuna.

        :rtype list of dicts
        """
        if not self.yz_wm_index:
            raise NotImplementedError("Search 2.0 administration is not "
                                      "supported for this version")

        url = self.search_index_path()

        # Run the request...
        status, headers, body = self._request('GET', url)

        if status == 200:
            json_data = json.loads(body)
            # Return a list of dictionaries
            return json_data
        else:
            raise RiakError('Error getting Search 2.0 index.')

    def delete_search_index(self, index):
        """
        Fetch the specified Solr search index for Yokozuna.

        :param index: a name of a yz index
        :type index: string
        :rtype boolean
        """
        if not self.yz_wm_index:
            raise NotImplementedError("Search 2.0 administration is not "
                                      "supported for this version")

        url = self.search_index_path(index)

        # Run the request...
        status, _, _ = self._request('DELETE', url)

        if status != 204:
            raise RiakError('Error setting Search 2.0 index.')
        return True

    def create_search_schema(self, schema, content):
        """
        Create a new Solr schema for Yokozuna.

        :param schema: name of Solr schema
        :type schema: string
        :param content: actual defintion of schema (XML)
        :type content: string
        :rtype boolean
        """
        if not self.yz_wm_schema:
            raise NotImplementedError("Search 2.0 administration is not "
                                      "supported for this version")

        url = self.search_schema_path(schema)
        headers = {'Content-Type': 'application/xml'}

        # Run the request...
        status, header, body = self._request('PUT', url, headers, content)

        if status != 204:
            raise RiakError('Error creating Search 2.0 schema.')
        return True

    def get_search_schema(self, schema):
        """
        Fetch a Solr schema from Yokozuna.

        :param schema: name of Solr schema
        :type schema: string
        :rtype dict
        """
        if not self.yz_wm_schema:
            raise NotImplementedError("Search 2.0 administration is not "
                                      "supported for this version")
        url = self.search_schema_path(schema)

        # Run the request...
        status, _, body = self._request('GET', url)

        if status == 200:
            result = {}
            result['name'] = schema
            result['content'] = body
            return result
        else:
            raise RiakError('Error getting Search 2.0 schema.')

    def search(self, index, query, **params):
        """
        Performs a search query.
        """
        if index is None:
            index = 'search'

        options = {}
        if 'op' in params:
            op = params.pop('op')
            options['q.op'] = op

        options.update(params)
        url = self.solr_select_path(index, query, **options)
        status, headers, data = self._request('GET', url)
        self.check_http_code(status, [200])
        if 'json' in headers['content-type']:
            results = json.loads(data)
            return self._normalize_json_search_response(results)
        elif 'xml' in headers['content-type']:
            return self._normalize_xml_search_response(data)
        else:
            raise ValueError("Could not decode search response")

    def fulltext_add(self, index, docs):
        """
        Adds documents to the search index.
        """
        xml = Document()
        root = xml.createElement('add')
        for doc in docs:
            doc_element = xml.createElement('doc')
            for key in doc:
                value = doc[key]
                field = xml.createElement('field')
                field.setAttribute("name", key)
                text = xml.createTextNode(value)
                field.appendChild(text)
                doc_element.appendChild(field)
            root.appendChild(doc_element)
        xml.appendChild(root)

        self._request('POST', self.solr_update_path(index),
                      {'Content-Type': 'text/xml'},
                      xml.toxml().encode('utf-8'))

    def fulltext_delete(self, index, docs=None, queries=None):
        """
        Removes documents from the full-text index.
        """
        xml = Document()
        root = xml.createElement('delete')
        if docs:
            for doc in docs:
                doc_element = xml.createElement('id')
                text = xml.createTextNode(doc)
                doc_element.appendChild(text)
                root.appendChild(doc_element)
        if queries:
            for query in queries:
                query_element = xml.createElement('query')
                text = xml.createTextNode(query)
                query_element.appendChild(text)
                root.appendChild(query_element)

        xml.appendChild(root)

        self._request('POST', self.solr_update_path(index),
                      {'Content-Type': 'text/xml'},
                      xml.toxml().encode('utf-8'))

    def get_counter(self, bucket, key, **options):
        if not bucket.bucket_type.is_default():
            raise NotImplementedError("Counters are not "
                                      "supported with bucket-types, "
                                      "use datatypes instead.")

        if not self.counters():
            raise NotImplementedError("Counters are not "
                                      "supported on %s" %
                                      self.server_version.vstring)

        url = self.counters_path(bucket.name, key, **options)
        status, headers, body = self._request('GET', url)

        self.check_http_code(status, [200, 404])
        if status == 200:
            return long(body.strip())
        elif status == 404:
            return None

    def update_counter(self, bucket, key, amount, **options):
        if not bucket.bucket_type.is_default():
            raise NotImplementedError("Counters are not "
                                      "supported with bucket-types, "
                                      "use datatypes instead.")

        if not self.counters():
            raise NotImplementedError("Counters are not "
                                      "supported on %s" %
                                      self.server_version.vstring)

        return_value = 'returnvalue' in options and options['returnvalue']
        headers = {'Content-Type': 'text/plain'}
        url = self.counters_path(bucket.name, key, **options)
        status, headers, body = self._request('POST', url, headers,
                                              str(amount))
        if return_value and status == 200:
            return long(body.strip())
        elif status == 204:
            return True
        else:
            self.check_http_code(status, [200, 204])

    def check_http_code(self, status, expected_statuses):
        if status not in expected_statuses:
            raise RiakError('Expected status %s, received %s' %
                            (expected_statuses, status))

    def _get_bucket_type(self, bucket_type):
        if bucket_type is None:
            return None
        if bucket_type.is_default():
            return None
        elif not self.bucket_types():
            raise NotImplementedError('Server does not support bucket-types')
        else:
            return bucket_type.name

########NEW FILE########
__FILENAME__ = codec
"""
Copyright 2012 Basho Technologies, Inc.

This file is provided to you under the Apache License,
Version 2.0 (the "License"); you may not use this file
except in compliance with the License.  You may obtain
a copy of the License at

  http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on an
"AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
KIND, either express or implied.  See the License for the
specific language governing permissions and limitations
under the License.
"""
import riak_pb
from riak import RiakError
from riak.content import RiakContent
from riak.util import decode_index_value


def _invert(d):
    out = {}
    for key in d:
        value = d[key]
        out[value] = key
    return out

REPL_TO_PY = {riak_pb.RpbBucketProps.FALSE: False,
              riak_pb.RpbBucketProps.TRUE: True,
              riak_pb.RpbBucketProps.REALTIME: 'realtime',
              riak_pb.RpbBucketProps.FULLSYNC: 'fullsync'}

REPL_TO_PB = _invert(REPL_TO_PY)

RIAKC_RW_ONE = 4294967294
RIAKC_RW_QUORUM = 4294967293
RIAKC_RW_ALL = 4294967292
RIAKC_RW_DEFAULT = 4294967291

QUORUM_TO_PB = {'default': RIAKC_RW_DEFAULT,
                'all': RIAKC_RW_ALL,
                'quorum': RIAKC_RW_QUORUM,
                'one': RIAKC_RW_ONE}

QUORUM_TO_PY = _invert(QUORUM_TO_PB)

NORMAL_PROPS = ['n_val', 'allow_mult', 'last_write_wins', 'old_vclock',
                'young_vclock', 'big_vclock', 'small_vclock', 'basic_quorum',
                'notfound_ok', 'search', 'backend', 'search_index', 'datatype']
COMMIT_HOOK_PROPS = ['precommit', 'postcommit']
MODFUN_PROPS = ['chash_keyfun', 'linkfun']
QUORUM_PROPS = ['r', 'pr', 'w', 'pw', 'dw', 'rw']


class RiakPbcCodec(object):
    """
    Protobuffs Encoding and decoding methods for RiakPbcTransport.
    """

    def __init__(self, **unused_args):
        if riak_pb is None:
            raise NotImplementedError("this transport is not available")
        super(RiakPbcCodec, self).__init__(**unused_args)

    def _encode_quorum(self, rw):
        """
        Converts a symbolic quorum value into its on-the-wire
        equivalent.

        :param rw: the quorum
        :type rw: string, integer
        :rtype: integer
        """
        if rw in QUORUM_TO_PB:
            return QUORUM_TO_PB[rw]
        elif type(rw) is int and rw >= 0:
            return rw
        else:
            return None

    def _decode_quorum(self, rw):
        """
        Converts a protobuf quorum value to a symbolic value if
        necessary.

        :param rw: the quorum
        :type rw: int
        :rtype int or string
        """
        if rw in QUORUM_TO_PY:
            return QUORUM_TO_PY[rw]
        else:
            return rw

    def _decode_contents(self, contents, obj):
        """
        Decodes the list of siblings from the protobuf representation
        into the object.

        :param contents: a list of RpbContent messages
        :type contents: list
        :param obj: a RiakObject
        :type obj: RiakObject
        :rtype RiakObject
        """
        obj.siblings = [self._decode_content(c, RiakContent(obj))
                        for c in contents]
        # Invoke sibling-resolution logic
        if len(obj.siblings) > 1 and obj.resolver is not None:
            obj.resolver(obj)
        return obj

    def _decode_content(self, rpb_content, sibling):
        """
        Decodes a single sibling from the protobuf representation into
        a RiakObject.

        :param rpb_content: a single RpbContent message
        :type rpb_content: riak_pb.RpbContent
        :param sibling: a RiakContent sibling container
        :type sibling: RiakContent
        :rtype: RiakContent
        """

        if rpb_content.HasField("deleted") and rpb_content.deleted:
            sibling.exists = False
        else:
            sibling.exists = True
        if rpb_content.HasField("content_type"):
            sibling.content_type = rpb_content.content_type
        if rpb_content.HasField("charset"):
            sibling.charset = rpb_content.charset
        if rpb_content.HasField("content_encoding"):
            sibling.content_encoding = rpb_content.content_encoding
        if rpb_content.HasField("vtag"):
            sibling.etag = rpb_content.vtag

        sibling.links = [self._decode_link(link)
                         for link in rpb_content.links]
        if rpb_content.HasField("last_mod"):
            sibling.last_modified = float(rpb_content.last_mod)
            if rpb_content.HasField("last_mod_usecs"):
                sibling.last_modified += rpb_content.last_mod_usecs / 1000000.0

        sibling.usermeta = dict([(usermd.key, usermd.value)
                                 for usermd in rpb_content.usermeta])
        sibling.indexes = set([(index.key,
                                decode_index_value(index.key, index.value))
                               for index in rpb_content.indexes])

        sibling.encoded_data = rpb_content.value

        return sibling

    def _encode_content(self, robj, rpb_content):
        """
        Fills an RpbContent message with the appropriate data and
        metadata from a RiakObject.

        :param robj: a RiakObject
        :type robj: RiakObject
        :param rpb_content: the protobuf message to fill
        :type rpb_content: riak_pb.RpbContent
        """
        if robj.content_type:
            rpb_content.content_type = robj.content_type
        if robj.charset:
            rpb_content.charset = robj.charset
        if robj.content_encoding:
            rpb_content.content_encoding = robj.content_encoding
        for uk in robj.usermeta:
            pair = rpb_content.usermeta.add()
            pair.key = uk
            pair.value = robj.usermeta[uk]
        for link in robj.links:
            pb_link = rpb_content.links.add()
            try:
                bucket, key, tag = link
            except ValueError:
                raise RiakError("Invalid link tuple %s" % link)

            pb_link.bucket = bucket
            pb_link.key = key
            if tag:
                pb_link.tag = tag
            else:
                pb_link.tag = ''

        for field, value in robj.indexes:
            pair = rpb_content.indexes.add()
            pair.key = field
            pair.value = str(value)

        rpb_content.value = str(robj.encoded_data)

    def _decode_link(self, link):
        """
        Decodes an RpbLink message into a tuple

        :param link: an RpbLink message
        :type link: riak_pb.RpbLink
        :rtype tuple
        """

        if link.HasField("bucket"):
            bucket = link.bucket
        else:
            bucket = None
        if link.HasField("key"):
            key = link.key
        else:
            key = None
        if link.HasField("tag"):
            tag = link.tag
        else:
            tag = None

        return (bucket, key, tag)

    def _decode_index_value(self, index, value):
        """
        Decodes a secondary index value into the correct Python type.
        :param index: the name of the index
        :type index: str
        :param value: the value of the index entry
        :type  value: str
        :rtype str or int
        """
        if index.endswith("_int"):
            return int(value)
        else:
            return value

    def _encode_bucket_props(self, props, msg):
        """
        Encodes a dict of bucket properties into the protobuf message.

        :param props: bucket properties
        :type props: dict
        :param msg: the protobuf message to fill
        :type msg: riak_pb.RpbSetBucketReq
        """
        for prop in NORMAL_PROPS:
            if prop in props and props[prop] is not None:
                setattr(msg.props, prop, props[prop])
        for prop in COMMIT_HOOK_PROPS:
            if prop in props:
                setattr(msg.props, 'has_' + prop, True)
                self._encode_hooklist(props[prop], getattr(msg.props, prop))
        for prop in MODFUN_PROPS:
            if prop in props and props[prop] is not None:
                self._encode_modfun(props[prop], getattr(msg.props, prop))
        for prop in QUORUM_PROPS:
            if prop in props and props[prop] not in (None, 'default'):
                value = self._encode_quorum(props[prop])
                if value is not None:
                    setattr(msg.props, prop, value)
        if 'repl' in props:
            msg.props.repl = REPL_TO_PY[props['repl']]

        return msg

    def _decode_bucket_props(self, msg):
        """
        Decodes the protobuf bucket properties message into a dict.

        :param msg: the protobuf message to decode
        :type msg: riak_pb.RpbBucketProps
        :rtype dict
        """
        props = {}

        for prop in NORMAL_PROPS:
            if msg.HasField(prop):
                props[prop] = getattr(msg, prop)
        for prop in COMMIT_HOOK_PROPS:
            if getattr(msg, 'has_' + prop):
                props[prop] = self._decode_hooklist(getattr(msg, prop))
        for prop in MODFUN_PROPS:
            if msg.HasField(prop):
                props[prop] = self._decode_modfun(getattr(msg, prop))
        for prop in QUORUM_PROPS:
            if msg.HasField(prop):
                props[prop] = self._decode_quorum(getattr(msg, prop))
        if msg.HasField('repl'):
            props['repl'] = REPL_TO_PY[msg.repl]

        return props

    def _decode_modfun(self, modfun):
        """
        Decodes a protobuf modfun pair into a dict with 'mod' and
        'fun' keys. Used in bucket properties.

        :param modfun: the protobuf message to decode
        :type modfun: riak_pb.RpbModFun
        :rtype dict
        """
        return {'mod': modfun.module,
                'fun': modfun.function}

    def _encode_modfun(self, props, msg=None):
        """
        Encodes a dict with 'mod' and 'fun' keys into a protobuf
        modfun pair. Used in bucket properties.

        :param props: the module/function pair
        :type props: dict
        :param msg: the protobuf message to fill
        :type msg: riak_pb.RpbModFun
        :rtype riak_pb.RpbModFun
        """
        if msg is None:
            msg = riak_pb.RpbModFun()
        msg.module = props['mod']
        msg.function = props['fun']
        return msg

    def _decode_hooklist(self, hooklist):
        """
        Decodes a list of protobuf commit hooks into their python
        equivalents. Used in bucket properties.

        :param hooklist: a list of protobuf commit hooks
        :type hooklist: list
        :rtype list
        """
        return [self._decode_hook(hook) for hook in hooklist]

    def _encode_hooklist(self, hooklist, msg):
        """
        Encodes a list of commit hooks into their protobuf equivalent.
        Used in bucket properties.

        :param hooklist: a list of commit hooks
        :type hooklist: list
        :param msg: a protobuf field that is a list of commit hooks
        """
        for hook in hooklist:
            pbhook = msg.add()
            self._encode_hook(hook, pbhook)

    def _decode_hook(self, hook):
        """
        Decodes a protobuf commit hook message into a dict. Used in
        bucket properties.

        :param hook: the hook to decode
        :type hook: riak_pb.RpbCommitHook
        :rtype dict
        """
        if hook.HasField('modfun'):
            return self._decode_modfun(hook.modfun)
        else:
            return {'name': hook.name}

    def _encode_hook(self, hook, msg):
        """
        Encodes a commit hook dict into the protobuf message. Used in
        bucket properties.

        :param hook: the hook to encode
        :type hook: dict
        :param msg: the protobuf message to fill
        :type msg: riak_pb.RpbCommitHook
        :rtype riak_pb.RpbCommitHook
        """
        if 'name' in hook:
            msg.name = hook['name']
        else:
            self._encode_modfun(hook, msg.modfun)
        return msg

    def _encode_index_req(self, bucket, index, startkey, endkey=None,
                          return_terms=None, max_results=None,
                          continuation=None, timeout=None, term_regex=None):
        """
        Encodes a secondary index request into the protobuf message.

        :param bucket: the bucket whose index to query
        :type bucket: string
        :param index: the index to query
        :type index: string
        :param startkey: the value or beginning of the range
        :type startkey: integer, string
        :param endkey: the end of the range
        :type endkey: integer, string
        :param return_terms: whether to return the index term with the key
        :type return_terms: bool
        :param max_results: the maximum number of results to return (page size)
        :type max_results: integer
        :param continuation: the opaque continuation returned from a
            previous paginated request
        :type continuation: string
        :param timeout: a timeout value in milliseconds, or 'infinity'
        :type timeout: int
        :rtype riak_pb.RpbIndexReq
        """
        req = riak_pb.RpbIndexReq(bucket=bucket.name, index=index)
        self._add_bucket_type(req, bucket.bucket_type)
        if endkey:
            req.qtype = riak_pb.RpbIndexReq.range
            req.range_min = str(startkey)
            req.range_max = str(endkey)
        else:
            req.qtype = riak_pb.RpbIndexReq.eq
            req.key = str(startkey)
        if return_terms is not None:
            req.return_terms = return_terms
        if max_results:
            req.max_results = max_results
        if continuation:
            req.continuation = continuation
        if timeout:
            if timeout == 'infinity':
                req.timeout = 0
            else:
                req.timeout = timeout
        if term_regex:
            req.term_regex = term_regex
        return req

    def _decode_search_index(self, index):
        """
        Fills an RpbYokozunaIndex message with the appropriate data.

        :param index: a yz index message
        :type index: riak_pb.RpbYokozunaIndex
        :rtype dict
        """
        result = {}
        result['name'] = index.name
        if index.HasField('schema'):
            result['schema'] = index.schema
        if index.HasField('n_val'):
            result['n_val'] = index.n_val
        return result

    def _add_bucket_type(self, req, bucket_type):
        if bucket_type and not bucket_type.is_default():
            if not self.bucket_types():
                raise NotImplementedError(
                    'Server does not support bucket-types')
            req.type = bucket_type.name

########NEW FILE########
__FILENAME__ = connection
"""
Copyright 2012 Basho Technologies, Inc.

This file is provided to you under the Apache License,
Version 2.0 (the "License"); you may not use this file
except in compliance with the License.  You may obtain
a copy of the License at

  http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on an
"AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
KIND, either express or implied.  See the License for the
specific language governing permissions and limitations
under the License.
"""

import socket
import struct
from riak import RiakError
from riak_pb.messages import (
    MESSAGE_CLASSES,
    MSG_CODE_ERROR_RESP
)


class RiakPbcConnection(object):
    """
    Connection-related methods for RiakPbcTransport.
    """

    def _encode_msg(self, msg_code, msg=None):
        if msg is None:
            return struct.pack("!iB", 1, msg_code)
        msgstr = msg.SerializeToString()
        slen = len(msgstr)
        hdr = struct.pack("!iB", 1 + slen, msg_code)
        return hdr + msgstr

    def _request(self, msg_code, msg=None, expect=None):
        self._send_msg(msg_code, msg)
        return self._recv_msg(expect)

    def _send_msg(self, msg_code, msg):
        self._connect()
        self._socket.send(self._encode_msg(msg_code, msg))

    def _recv_msg(self, expect=None):
        self._recv_pkt()
        msg_code, = struct.unpack("B", self._inbuf[:1])

        if msg_code is MSG_CODE_ERROR_RESP:
            err = self._parse_msg(msg_code, self._inbuf[1:])
            raise RiakError(err.errmsg)
        elif msg_code in MESSAGE_CLASSES:
            msg = self._parse_msg(msg_code, self._inbuf[1:])
        else:
            raise Exception("unknown msg code %s" % msg_code)

        if expect and msg_code != expect:
            raise RiakError("unexpected protocol buffer message code: %d, %r"
                            % (msg_code, msg))
        return msg_code, msg

    def _recv_pkt(self):
        nmsglen = self._socket.recv(4)
        if len(nmsglen) != 4:
            raise RiakError(
                "Socket returned short packet length %d - expected 4"
                % len(nmsglen))
        msglen, = struct.unpack('!i', nmsglen)
        self._inbuf_len = msglen
        self._inbuf = ''
        while len(self._inbuf) < msglen:
            want_len = min(8192, msglen - len(self._inbuf))
            recv_buf = self._socket.recv(want_len)
            if not recv_buf:
                break
            self._inbuf += recv_buf
        if len(self._inbuf) != self._inbuf_len:
            raise RiakError("Socket returned short packet %d - expected %d"
                            % (len(self._inbuf), self._inbuf_len))

    def _connect(self):
        if not self._socket:
            if self._timeout:
                self._socket = socket.create_connection(self._address,
                                                        self._timeout)
            else:
                self._socket = socket.create_connection(self._address)

    def close(self):
        """
        Closes the underlying socket of the PB connection.
        """
        if self._socket:
            self._socket.shutdown(socket.SHUT_RDWR)

    def _parse_msg(self, code, packet):
        try:
            pbclass = MESSAGE_CLASSES[code]
        except KeyError:
            pbclass = None

        if pbclass is None:
            return None

        pbo = pbclass()
        pbo.ParseFromString(packet)
        return pbo

    # These are set in the RiakPbcTransport initializer
    _address = None
    _timeout = None

########NEW FILE########
__FILENAME__ = stream
"""
Copyright 2012 Basho Technologies, Inc.

This file is provided to you under the Apache License,
Version 2.0 (the "License"); you may not use this file
except in compliance with the License.  You may obtain
a copy of the License at

  http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on an
"AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
KIND, either express or implied.  See the License for the
specific language governing permissions and limitations
under the License.
"""


import json
from riak_pb.messages import (
    MSG_CODE_LIST_KEYS_RESP,
    MSG_CODE_MAP_RED_RESP,
    MSG_CODE_LIST_BUCKETS_RESP,
    MSG_CODE_INDEX_RESP
)
from riak.util import decode_index_value
from riak.client.index_page import CONTINUATION


class RiakPbcStream(object):
    """
    Used internally by RiakPbcTransport to implement streaming
    operations. Implements the iterator interface.
    """

    _expect = None

    def __init__(self, transport):
        self.finished = False
        self.transport = transport

    def __iter__(self):
        return self

    def next(self):
        if self.finished:
            raise StopIteration

        try:
            msg_code, resp = self.transport._recv_msg(expect=self._expect)
        except:
            self.finished = True
            raise

        if(self._is_done(resp)):
            self.finished = True

        return resp

    def _is_done(self, response):
        # This could break if new messages don't name the field the
        # same thing.
        return response.done

    def close(self):
        # We have to drain the socket to make sure that we don't get
        # weird responses when some other request comes after a
        # failed/prematurely-terminated one.
        try:
            while self.next():
                pass
        except StopIteration:
            pass


class RiakPbcKeyStream(RiakPbcStream):
    """
    Used internally by RiakPbcTransport to implement key-list streams.
    """

    _expect = MSG_CODE_LIST_KEYS_RESP

    def next(self):
        response = super(RiakPbcKeyStream, self).next()

        if response.done and len(response.keys) is 0:
            raise StopIteration

        return response.keys


class RiakPbcMapredStream(RiakPbcStream):
    """
    Used internally by RiakPbcTransport to implement MapReduce
    streams.
    """

    _expect = MSG_CODE_MAP_RED_RESP

    def next(self):
        response = super(RiakPbcMapredStream, self).next()

        if response.done and not response.HasField('response'):
            raise StopIteration

        return response.phase, json.loads(response.response)


class RiakPbcBucketStream(RiakPbcStream):
    """
    Used internally by RiakPbcTransport to implement key-list streams.
    """

    _expect = MSG_CODE_LIST_BUCKETS_RESP

    def next(self):
        response = super(RiakPbcBucketStream, self).next()

        if response.done and len(response.buckets) is 0:
            raise StopIteration

        return response.buckets


class RiakPbcIndexStream(RiakPbcStream):
    """
    Used internally by RiakPbcTransport to implement Secondary Index
    streams.
    """

    _expect = MSG_CODE_INDEX_RESP

    def __init__(self, transport, index, return_terms=False):
        super(RiakPbcIndexStream, self).__init__(transport)
        self.index = index
        self.return_terms = return_terms

    def next(self):
        response = super(RiakPbcIndexStream, self).next()

        if response.done and not (response.keys or
                                  response.results or
                                  response.continuation):
            raise StopIteration

        if self.return_terms and response.results:
            return [(decode_index_value(self.index, r.key), r.value)
                    for r in response.results]
        elif response.keys:
            return response.keys[:]
        elif response.continuation:
            return CONTINUATION(response.continuation)

########NEW FILE########
__FILENAME__ = transport
"""
Copyright 2012 Basho Technologies, Inc.
Copyright 2010 Rusty Klophaus <rusty@basho.com>
Copyright 2010 Justin Sheehy <justin@basho.com>
Copyright 2009 Jay Baird <jay@mochimedia.com>

This file is provided to you under the Apache License,
Version 2.0 (the "License"); you may not use this file
except in compliance with the License.  You may obtain
a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on an
"AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
KIND, either express or implied.  See the License for the
specific language governing permissions and limitations
under the License.
"""

import riak_pb
from riak import RiakError
from riak.transports.transport import RiakTransport
from riak.riak_object import VClock
from riak.util import decode_index_value
from connection import RiakPbcConnection
from stream import (RiakPbcKeyStream, RiakPbcMapredStream, RiakPbcBucketStream,
                    RiakPbcIndexStream)
from codec import RiakPbcCodec

from riak_pb.messages import (
    MSG_CODE_PING_REQ,
    MSG_CODE_PING_RESP,
    MSG_CODE_GET_CLIENT_ID_REQ,
    MSG_CODE_GET_CLIENT_ID_RESP,
    MSG_CODE_SET_CLIENT_ID_REQ,
    MSG_CODE_SET_CLIENT_ID_RESP,
    MSG_CODE_GET_SERVER_INFO_REQ,
    MSG_CODE_GET_SERVER_INFO_RESP,
    MSG_CODE_GET_REQ,
    MSG_CODE_GET_RESP,
    MSG_CODE_PUT_REQ,
    MSG_CODE_PUT_RESP,
    MSG_CODE_DEL_REQ,
    MSG_CODE_DEL_RESP,
    MSG_CODE_LIST_BUCKETS_REQ,
    MSG_CODE_LIST_BUCKETS_RESP,
    MSG_CODE_LIST_KEYS_REQ,
    MSG_CODE_GET_BUCKET_REQ,
    MSG_CODE_GET_BUCKET_RESP,
    MSG_CODE_SET_BUCKET_REQ,
    MSG_CODE_SET_BUCKET_RESP,
    MSG_CODE_GET_BUCKET_TYPE_REQ,
    MSG_CODE_SET_BUCKET_TYPE_REQ,
    MSG_CODE_MAP_RED_REQ,
    MSG_CODE_INDEX_REQ,
    MSG_CODE_INDEX_RESP,
    MSG_CODE_SEARCH_QUERY_REQ,
    MSG_CODE_SEARCH_QUERY_RESP,
    MSG_CODE_RESET_BUCKET_REQ,
    MSG_CODE_RESET_BUCKET_RESP,
    MSG_CODE_COUNTER_UPDATE_REQ,
    MSG_CODE_COUNTER_UPDATE_RESP,
    MSG_CODE_COUNTER_GET_REQ,
    MSG_CODE_COUNTER_GET_RESP,
    MSG_CODE_YOKOZUNA_INDEX_GET_REQ,
    MSG_CODE_YOKOZUNA_INDEX_GET_RESP,
    MSG_CODE_YOKOZUNA_INDEX_PUT_REQ,
    MSG_CODE_YOKOZUNA_INDEX_DELETE_REQ,
    MSG_CODE_YOKOZUNA_SCHEMA_GET_REQ,
    MSG_CODE_YOKOZUNA_SCHEMA_GET_RESP,
    MSG_CODE_YOKOZUNA_SCHEMA_PUT_REQ

)


class RiakPbcTransport(RiakTransport, RiakPbcConnection, RiakPbcCodec):
    """
    The RiakPbcTransport object holds a connection to the protocol
    buffers interface on the riak server.
    """

    def __init__(self, node=None, client=None, timeout=None, *unused_options):
        """
        Construct a new RiakPbcTransport object.
        """
        super(RiakPbcTransport, self).__init__()

        self._client = client
        self._node = node
        self._address = (node.host, node.pb_port)
        self._timeout = timeout
        self._socket = None

    # FeatureDetection API
    def _server_version(self):
        return self.get_server_info()['server_version']

    def ping(self):
        """
        Ping the remote server
        """

        msg_code, msg = self._request(MSG_CODE_PING_REQ)
        if msg_code == MSG_CODE_PING_RESP:
            return True
        else:
            return False

    def get_server_info(self):
        """
        Get information about the server
        """
        msg_code, resp = self._request(MSG_CODE_GET_SERVER_INFO_REQ,
                                       expect=MSG_CODE_GET_SERVER_INFO_RESP)
        return {'node': resp.node, 'server_version': resp.server_version}

    def _get_client_id(self):
        msg_code, resp = self._request(MSG_CODE_GET_CLIENT_ID_REQ,
                                       expect=MSG_CODE_GET_CLIENT_ID_RESP)
        return resp.client_id

    def _set_client_id(self, client_id):
        req = riak_pb.RpbSetClientIdReq()
        req.client_id = client_id

        msg_code, resp = self._request(MSG_CODE_SET_CLIENT_ID_REQ, req,
                                       MSG_CODE_SET_CLIENT_ID_RESP)

        self._client_id = client_id

    client_id = property(_get_client_id, _set_client_id,
                         doc="""the client ID for this connection""")

    def get(self, robj, r=None, pr=None, timeout=None):
        """
        Serialize get request and deserialize response
        """
        bucket = robj.bucket

        req = riak_pb.RpbGetReq()
        if r:
            req.r = self._encode_quorum(r)
        if self.quorum_controls() and pr:
            req.pr = self._encode_quorum(pr)
        if self.client_timeouts() and timeout:
            req.timeout = timeout
        if self.tombstone_vclocks():
            req.deletedvclock = 1

        req.bucket = bucket.name
        self._add_bucket_type(req, bucket.bucket_type)

        req.key = robj.key

        msg_code, resp = self._request(MSG_CODE_GET_REQ, req,
                                       MSG_CODE_GET_RESP)

        # TODO: support if_modified flag

        if resp is not None:
            if resp.HasField('vclock'):
                robj.vclock = VClock(resp.vclock, 'binary')
            # We should do this even if there are no contents, i.e.
            # the object is tombstoned
            self._decode_contents(resp.content, robj)
        else:
            # "not found" returns an empty message,
            # so let's make sure to clear the siblings
            robj.siblings = []

        return robj

    def put(self, robj, w=None, dw=None, pw=None, return_body=True,
            if_none_match=False, timeout=None):
        bucket = robj.bucket

        req = riak_pb.RpbPutReq()
        if w:
            req.w = self._encode_quorum(w)
        if dw:
            req.dw = self._encode_quorum(dw)
        if self.quorum_controls() and pw:
            req.pw = self._encode_quorum(pw)

        if return_body:
            req.return_body = 1
        if if_none_match:
            req.if_none_match = 1
        if self.client_timeouts() and timeout:
            req.timeout = timeout

        req.bucket = bucket.name
        self._add_bucket_type(req, bucket.bucket_type)

        if robj.key:
            req.key = robj.key
        if robj.vclock:
            req.vclock = robj.vclock.encode('binary')

        self._encode_content(robj, req.content)

        msg_code, resp = self._request(MSG_CODE_PUT_REQ, req,
                                       MSG_CODE_PUT_RESP)

        if resp is not None:
            if resp.HasField('key'):
                robj.key = resp.key
            if resp.HasField("vclock"):
                robj.vclock = VClock(resp.vclock, 'binary')
            if resp.content:
                self._decode_contents(resp.content, robj)
        elif not robj.key:
            raise RiakError("missing response object")

        return robj

    def delete(self, robj, rw=None, r=None, w=None, dw=None, pr=None, pw=None,
               timeout=None):
        req = riak_pb.RpbDelReq()
        if rw:
            req.rw = self._encode_quorum(rw)
        if r:
            req.r = self._encode_quorum(r)
        if w:
            req.w = self._encode_quorum(w)
        if dw:
            req.dw = self._encode_quorum(dw)

        if self.quorum_controls():
            if pr:
                req.pr = self._encode_quorum(pr)
            if pw:
                req.pw = self._encode_quorum(pw)

        if self.client_timeouts() and timeout:
            req.timeout = timeout

        if self.tombstone_vclocks() and robj.vclock:
            req.vclock = robj.vclock.encode('binary')

        bucket = robj.bucket
        req.bucket = bucket.name
        self._add_bucket_type(req, bucket.bucket_type)
        req.key = robj.key

        msg_code, resp = self._request(MSG_CODE_DEL_REQ, req,
                                       MSG_CODE_DEL_RESP)
        return self

    def get_keys(self, bucket, timeout=None):
        """
        Lists all keys within a bucket.
        """
        keys = []
        for keylist in self.stream_keys(bucket, timeout=timeout):
            for key in keylist:
                keys.append(key)

        return keys

    def stream_keys(self, bucket, timeout=None):
        """
        Streams keys from a bucket, returning an iterator that yields
        lists of keys.
        """
        req = riak_pb.RpbListKeysReq()
        req.bucket = bucket.name
        self._add_bucket_type(req, bucket.bucket_type)
        if self.client_timeouts() and timeout:
            req.timeout = timeout

        self._send_msg(MSG_CODE_LIST_KEYS_REQ, req)

        return RiakPbcKeyStream(self)

    def get_buckets(self, bucket_type=None, timeout=None):
        """
        Serialize bucket listing request and deserialize response
        """
        req = riak_pb.RpbListBucketsReq()
        self._add_bucket_type(req, bucket_type)

        if self.client_timeouts() and timeout:
            req.timeout = timeout

        msg_code, resp = self._request(MSG_CODE_LIST_BUCKETS_REQ, req,
                                       MSG_CODE_LIST_BUCKETS_RESP)
        return resp.buckets

    def stream_buckets(self, bucket_type=None, timeout=None):
        """
        Stream list of buckets through an iterator
        """

        if not self.bucket_stream():
            raise NotImplementedError('Streaming list-buckets is not '
                                      'supported')

        req = riak_pb.RpbListBucketsReq()
        req.stream = True
        self._add_bucket_type(req, bucket_type)
        # Bucket streaming landed in the same release as timeouts, so
        # we don't need to check the capability.
        if timeout:
            req.timeout = timeout

        self._send_msg(MSG_CODE_LIST_BUCKETS_REQ, req)

        return RiakPbcBucketStream(self)

    def get_bucket_props(self, bucket):
        """
        Serialize bucket property request and deserialize response
        """
        req = riak_pb.RpbGetBucketReq()
        req.bucket = bucket.name
        self._add_bucket_type(req, bucket.bucket_type)

        msg_code, resp = self._request(MSG_CODE_GET_BUCKET_REQ, req,
                                       MSG_CODE_GET_BUCKET_RESP)

        return self._decode_bucket_props(resp.props)

    def set_bucket_props(self, bucket, props):
        """
        Serialize set bucket property request and deserialize response
        """
        req = riak_pb.RpbSetBucketReq()
        req.bucket = bucket.name
        self._add_bucket_type(req, bucket.bucket_type)

        if not self.pb_all_bucket_props():
            for key in props:
                if key not in ('n_val', 'allow_mult'):
                    raise NotImplementedError('Server only supports n_val and '
                                              'allow_mult properties over PBC')

        self._encode_bucket_props(props, req)

        msg_code, resp = self._request(MSG_CODE_SET_BUCKET_REQ, req,
                                       MSG_CODE_SET_BUCKET_RESP)
        return True

    def clear_bucket_props(self, bucket):
        """
        Clear bucket properties, resetting them to their defaults
        """
        if not self.pb_clear_bucket_props():
            return False

        req = riak_pb.RpbResetBucketReq()
        req.bucket = bucket.name
        self._add_bucket_type(req, bucket.bucket_type)
        self._request(MSG_CODE_RESET_BUCKET_REQ, req,
                      MSG_CODE_RESET_BUCKET_RESP)
        return True

    def get_bucket_type_props(self, bucket_type):
        """
        Fetch bucket-type properties
        """
        self._check_bucket_types(bucket_type)

        req = riak_pb.RpbGetBucketTypeReq()
        req.type = bucket_type.name

        msg_code, resp = self._request(MSG_CODE_GET_BUCKET_TYPE_REQ, req,
                                       MSG_CODE_GET_BUCKET_RESP)

        return self._decode_bucket_props(resp.props)

    def set_bucket_type_props(self, bucket_type, props):
        """
        Set bucket-type properties
        """
        self._check_bucket_types(bucket_type)

        req = riak_pb.RpbSetBucketTypeReq()
        req.type = bucket_type.name

        self._encode_bucket_props(props, req)

        msg_code, resp = self._request(MSG_CODE_SET_BUCKET_TYPE_REQ, req,
                                       MSG_CODE_SET_BUCKET_RESP)
        return True

    def mapred(self, inputs, query, timeout=None):
        # dictionary of phase results - each content should be an encoded array
        # which is appended to the result for that phase.
        result = {}
        for phase, content in self.stream_mapred(inputs, query, timeout):
            if phase in result:
                result[phase] += content
            else:
                result[phase] = content

        # If a single result - return the same as the HTTP interface does
        # otherwise return all the phase information
        if not len(result):
            return None
        elif len(result) == 1:
            return result[max(result.keys())]
        else:
            return result

    def stream_mapred(self, inputs, query, timeout=None):
        # Construct the job, optionally set the timeout...
        content = self._construct_mapred_json(inputs, query, timeout)

        req = riak_pb.RpbMapRedReq()
        req.request = content
        req.content_type = "application/json"

        self._send_msg(MSG_CODE_MAP_RED_REQ, req)

        return RiakPbcMapredStream(self)

    def get_index(self, bucket, index, startkey, endkey=None,
                  return_terms=None, max_results=None, continuation=None,
                  timeout=None, term_regex=None):
        if not self.pb_indexes():
            return self._get_index_mapred_emu(bucket, index, startkey, endkey)

        if term_regex and not self.index_term_regex():
            raise NotImplementedError("Secondary index term_regex is not "
                                      "supported")

        req = self._encode_index_req(bucket, index, startkey, endkey,
                                     return_terms, max_results, continuation,
                                     timeout, term_regex)

        msg_code, resp = self._request(MSG_CODE_INDEX_REQ, req,
                                       MSG_CODE_INDEX_RESP)

        if return_terms and resp.results:
            results = [(decode_index_value(index, pair.key), pair.value)
                       for pair in resp.results]
        else:
            results = resp.keys[:]

        if max_results:
            return (results, resp.continuation)
        else:
            return (results, None)

    def stream_index(self, bucket, index, startkey, endkey=None,
                     return_terms=None, max_results=None, continuation=None,
                     timeout=None, term_regex=None):
        if not self.stream_indexes():
            raise NotImplementedError("Secondary index streaming is not "
                                      "supported")

        if term_regex and not self.index_term_regex():
            raise NotImplementedError("Secondary index term_regex is not "
                                      "supported")

        req = self._encode_index_req(bucket, index, startkey, endkey,
                                     return_terms, max_results, continuation,
                                     timeout, term_regex)
        req.stream = True

        self._send_msg(MSG_CODE_INDEX_REQ, req)

        return RiakPbcIndexStream(self, index, return_terms)

    def create_search_index(self, index, schema=None, n_val=None):
        if not self.pb_search_admin():
            raise NotImplementedError("Search 2.0 administration is not "
                                      "supported for this version")
        idx = riak_pb.RpbYokozunaIndex(name=index)
        if schema:
            idx.schema = schema
        if n_val:
            idx.n_val = n_val
        req = riak_pb.RpbYokozunaIndexPutReq(index=idx)

        self._request(MSG_CODE_YOKOZUNA_INDEX_PUT_REQ, req,
                      MSG_CODE_PUT_RESP)
        return True

    def get_search_index(self, index):
        if not self.pb_search_admin():
            raise NotImplementedError("Search 2.0 administration is not "
                                      "supported for this version")
        req = riak_pb.RpbYokozunaIndexGetReq(name=index)

        msg_code, resp = self._request(MSG_CODE_YOKOZUNA_INDEX_GET_REQ, req,
                                       MSG_CODE_YOKOZUNA_INDEX_GET_RESP)
        if len(resp.index) > 0:
            return self._decode_search_index(resp.index[0])
        else:
            raise RiakError('notfound')

    def list_search_indexes(self):
        if not self.pb_search_admin():
            raise NotImplementedError("Search 2.0 administration is not "
                                      "supported for this version")
        req = riak_pb.RpbYokozunaIndexGetReq()

        msg_code, resp = self._request(MSG_CODE_YOKOZUNA_INDEX_GET_REQ, req,
                                       MSG_CODE_YOKOZUNA_INDEX_GET_RESP)

        return [self._decode_search_index(index) for index in resp.index]

    def delete_search_index(self, index):
        if not self.pb_search_admin():
            raise NotImplementedError("Search 2.0 administration is not "
                                      "supported for this version")
        req = riak_pb.RpbYokozunaIndexDeleteReq(name=index)

        self._request(MSG_CODE_YOKOZUNA_INDEX_DELETE_REQ, req,
                      MSG_CODE_DEL_RESP)

        return True

    def create_search_schema(self, schema, content):
        if not self.pb_search_admin():
            raise NotImplementedError("Search 2.0 administration is not "
                                      "supported for this version")
        scma = riak_pb.RpbYokozunaSchema(name=schema, content=content)
        req = riak_pb.RpbYokozunaSchemaPutReq(schema=scma)

        self._request(MSG_CODE_YOKOZUNA_SCHEMA_PUT_REQ, req,
                      MSG_CODE_PUT_RESP)
        return True

    def get_search_schema(self, schema):
        if not self.pb_search_admin():
            raise NotImplementedError("Search 2.0 administration is not "
                                      "supported for this version")
        req = riak_pb.RpbYokozunaSchemaGetReq(name=schema)

        msg_code, resp = self._request(MSG_CODE_YOKOZUNA_SCHEMA_GET_REQ, req,
                                       MSG_CODE_YOKOZUNA_SCHEMA_GET_RESP)
        result = {}
        result['name'] = resp.schema.name
        result['content'] = resp.schema.content
        return result

    def search(self, index, query, **params):
        if not self.pb_search():
            return self._search_mapred_emu(index, query)

        req = riak_pb.RpbSearchQueryReq(index=index, q=query)
        if 'rows' in params:
            req.rows = params['rows']
        if 'start' in params:
            req.start = params['start']
        if 'sort' in params:
            req.sort = params['sort']
        if 'filter' in params:
            req.filter = params['filter']
        if 'df' in params:
            req.df = params['df']
        if 'op' in params:
            req.op = params['op']
        if 'q.op' in params:
            req.op = params['q.op']
        if 'fl' in params:
            if isinstance(params['fl'], list):
                req.fl.extend(params['fl'])
            else:
                req.fl.append(params['fl'])
        if 'presort' in params:
            req.presort = params['presort']

        msg_code, resp = self._request(MSG_CODE_SEARCH_QUERY_REQ, req,
                                       MSG_CODE_SEARCH_QUERY_RESP)

        result = {}
        if resp.HasField('max_score'):
            result['max_score'] = resp.max_score
        if resp.HasField('num_found'):
            result['num_found'] = resp.num_found
        docs = []
        for doc in resp.docs:
            resultdoc = {}
            for pair in doc.fields:
                ukey = unicode(pair.key, 'utf-8')
                uval = unicode(pair.value, 'utf-8')
                resultdoc[ukey] = uval
            docs.append(resultdoc)
        result['docs'] = docs
        return result

    def get_counter(self, bucket, key, **params):
        if not bucket.bucket_type.is_default():
            raise NotImplementedError("Counters are not "
                                      "supported with bucket-types, "
                                      "use datatypes instead.")

        if not self.counters():
            raise NotImplementedError("Counters are not supported")

        req = riak_pb.RpbCounterGetReq()
        req.bucket = bucket.name
        req.key = key
        if params.get('r') is not None:
            req.r = self._encode_quorum(params['r'])
        if params.get('pr') is not None:
            req.pr = self._encode_quorum(params['pr'])
        if params.get('basic_quorum') is not None:
            req.basic_quorum = params['basic_quorum']
        if params.get('notfound_ok') is not None:
            req.notfound_ok = params['notfound_ok']

        msg_code, resp = self._request(MSG_CODE_COUNTER_GET_REQ, req,
                                       MSG_CODE_COUNTER_GET_RESP)
        if resp.HasField('value'):
            return resp.value
        else:
            return None

    def update_counter(self, bucket, key, value, **params):
        if not bucket.bucket_type.is_default():
            raise NotImplementedError("Counters are not "
                                      "supported with bucket-types, "
                                      "use datatypes instead.")

        if not self.counters():
            raise NotImplementedError("Counters are not supported")

        req = riak_pb.RpbCounterUpdateReq()
        req.bucket = bucket.name
        req.key = key
        req.amount = value
        if params.get('w') is not None:
            req.w = self._encode_quorum(params['w'])
        if params.get('dw') is not None:
            req.dw = self._encode_quorum(params['dw'])
        if params.get('pw') is not None:
            req.pw = self._encode_quorum(params['pw'])
        if params.get('returnvalue') is not None:
            req.returnvalue = params['returnvalue']

        msg_code, resp = self._request(MSG_CODE_COUNTER_UPDATE_REQ, req,
                                       MSG_CODE_COUNTER_UPDATE_RESP)
        if resp.HasField('value'):
            return resp.value
        else:
            return True

########NEW FILE########
__FILENAME__ = pool
"""
Copyright 2012 Basho Technologies, Inc.

This file is provided to you under the Apache License,
Version 2.0 (the "License"); you may not use this file
except in compliance with the License.  You may obtain
a copy of the License at

  http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on an
"AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
KIND, either express or implied.  See the License for the
specific language governing permissions and limitations
under the License.
"""

from contextlib import contextmanager
import threading


# This file is a rough port of the Innertube Ruby library
class BadResource(StandardError):
    """
    Users of a :class:`Pool` should raise this error when the pool
    element currently in-use is bad and should be removed from the
    pool.
    """
    pass


class Element(object):
    """
    A member of the :class:`Pool`, a container for the actual resource
    being pooled and a marker for whether the resource is currently
    claimed.
    """
    def __init__(self, obj):
        """
        Creates a new Element, wrapping the passed object as the
        pooled resource.

        :param obj: the resource to wrap
        :type obj: object
        """

        self.object = obj
        """The wrapped pool resource."""

        self.claimed = False
        """Whether the resource is currently in use."""


class Pool(object):
    """
    A thread-safe, reentrant resource pool, ported from the
    "Innertube" Ruby library. Pool should be subclassed to implement
    the create_resource and destroy_resource functions that are
    responsible for creating and cleaning up the resources in the
    pool, respectively. Claiming a resource of the pool for a block of
    code is done using a with statement on the take method. The take
    method also allows filtering of the pool and supplying a default
    value to be used as the resource if no elements are free.

    Example::

        from riak.Pool import Pool, BadResource
        class ListPool(Pool):
            def create_resource(self):
                return []

            def destroy_resource(self):
                # Lists don't need to be cleaned up
                pass

        pool = ListPool()
        with pool.take() as resource:
            resource.append(1)
        with pool.take() as resource2:
            print repr(resource2) # should be [1]
    """

    def __init__(self):
        """
        Creates a new Pool. This should be called manually if you
        override the :meth:`__init__` method in a subclass.
        """
        self.lock = threading.RLock()
        self.releaser = threading.Condition(self.lock)
        self.elements = list()

    @contextmanager
    def take(self, _filter=None, default=None):
        """
        take(_filter=None, default=None)

        Claims a resource from the pool for use in a thread-safe,
        reentrant manner (as part of a with statement). Resources are
        created as needed when all members of the pool are claimed or
        the pool is empty.

        :param _filter: a filter that can be used to select a member
            of the pool
        :type _filter: callable
        :param default: a value that will be used instead of calling
            :meth:`create_resource` if a new resource needs to be created
        """
        if not _filter:
            def _filter(obj):
                return True
        elif not callable(_filter):
            raise TypeError("_filter is not a callable")

        element = None
        with self.lock:
            for e in self.elements:
                if not e.claimed and _filter(e.object):
                    element = e
                    break
            if element is None:
                if default is not None:
                    element = Element(default)
                else:
                    element = Element(self.create_resource())
                self.elements.append(element)
            element.claimed = True
        try:
            yield element.object
        except BadResource:
            self.delete_element(element)
            raise
        finally:
            with self.releaser:
                element.claimed = False
                self.releaser.notify_all()

    def delete_element(self, element):
        """
        Deletes the element from the pool and destroys the associated
        resource. Not usually needed by users of the pool, but called
        internally when BadResource is raised.

        :param element: the element to remove
        :type element: Element
        """
        with self.lock:
            self.elements.remove(element)
        self.destroy_resource(element.object)
        del element

    def __iter__(self):
        """
        Iterator callback to iterate over the elements of the pool.
        """
        return PoolIterator(self)

    def clear(self):
        """
        Removes all resources from the pool, calling :meth:`delete_element`
        with each one so that the resources are cleaned up.
        """
        for element in self:
            self.delete_element(element)

    def create_resource(self):
        """
        Implemented by subclasses to allocate a new resource for use
        in the pool.
        """
        raise NotImplementedError

    def destroy_resource(self, obj):
        """
        Called when removing a resource from the pool so that it can
        be cleanly deallocated. Subclasses should implement this
        method if additional cleanup is needed beyond normal GC. The
        default implementation is a no-op.

        :param obj: the resource being removed
        """
        pass


class PoolIterator(object):
    """
    Iterates over a snapshot of the pool in a thread-safe manner,
    eventually touching all resources that were known when the
    iteration started.

    Note that if claimed resources are not released for long periods,
    the iterator may hang, waiting for those last resources to be
    released. The iteration and pool functionality is only meant to be
    used internally within the client, and resources will be claimed
    per client operation, making this an unlikely event (although
    still possible).
    """

    def __init__(self, pool):
        with pool.lock:
            self.targets = pool.elements[:]
        self.unlocked = []
        self.lock = pool.lock
        self.releaser = pool.releaser

    def __iter__(self):
        return self

    def next(self):
        if len(self.targets) == 0:
            raise StopIteration
        if len(self.unlocked) == 0:
            self.__claim_elements()
        return self.unlocked.pop(0)

    def __claim_elements(self):
        with self.lock:
            with self.releaser:
                if self.__all_claimed():
                    self.releaser.wait()
            for element in self.targets:
                if not element.claimed:
                    self.targets.remove(element)
                    self.unlocked.append(element)
                    element.claimed = True

    def __all_claimed(self):
        for element in self.targets:
            if not element.claimed:
                return False
        return True

########NEW FILE########
__FILENAME__ = transport
"""
Copyright 2010 Rusty Klophaus <rusty@basho.com>
Copyright 2010 Justin Sheehy <justin@basho.com>
Copyright 2009 Jay Baird <jay@mochimedia.com>

This file is provided to you under the Apache License,
Version 2.0 (the "License"); you may not use this file
except in compliance with the License.  You may obtain
a copy of the License at

  http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on an
"AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
KIND, either express or implied.  See the License for the
specific language governing permissions and limitations
under the License.
"""
import base64
import random
import threading
import platform
import os
import json
from feature_detect import FeatureDetection


class RiakTransport(FeatureDetection):
    """
    Class to encapsulate transport details and methods. All protocol
    transports are subclasses of this class.
    """

    def _get_client_id(self):
        return self._client_id

    def _set_client_id(self, value):
        self._client_id = value

    client_id = property(_get_client_id, _set_client_id,
                         doc="""the client ID for this connection""")

    @classmethod
    def make_random_client_id(self):
        """
        Returns a random client identifier
        """
        return ('py_%s' %
                base64.b64encode(str(random.randint(1, 0x40000000))))

    @classmethod
    def make_fixed_client_id(self):
        """
        Returns a unique identifier for the current machine/process/thread.
        """
        machine = platform.node()
        process = os.getpid()
        thread = threading.currentThread().getName()
        return base64.b64encode('%s|%s|%s' % (machine, process, thread))

    def ping(self):
        """
        Ping the remote server
        """
        raise NotImplementedError

    def get(self, robj, r=None, pr=None, timeout=None):
        """
        Fetches an object.
        """
        raise NotImplementedError

    def put(self, robj, w=None, dw=None, pw=None, return_body=None,
            if_none_match=None, timeout=None):
        """
        Stores an object.
        """
        raise NotImplementedError

    def delete(self, robj, rw=None, r=None, w=None, dw=None, pr=None,
               pw=None, timeout=None):
        """
        Deletes an object.
        """
        raise NotImplementedError

    def get_buckets(self, bucket_type=None, timeout=None):
        """
        Gets the list of buckets as strings.
        """
        raise NotImplementedError

    def stream_buckets(self, bucket_type=None, timeout=None):
        """
        Streams the list of buckets through an iterator
        """
        raise NotImplementedError

    def get_bucket_props(self, bucket):
        """
        Fetches properties for the given bucket.
        """
        raise NotImplementedError

    def set_bucket_props(self, bucket, props):
        """
        Sets properties on the given bucket.
        """
        raise NotImplementedError

    def get_bucket_type_props(self, bucket_type):
        """
        Fetches properties for the given bucket-type.
        """
        raise NotImplementedError

    def set_bucket_type_props(self, bucket_type, props):
        """
        Sets properties on the given bucket-type.
        """
        raise NotImplementedError

    def clear_bucket_props(self, bucket):
        """
        Reset bucket properties to their defaults
        """
        raise NotImplementedError

    def get_keys(self, bucket, timeout=None):
        """
        Lists all keys within the given bucket.
        """
        raise NotImplementedError

    def stream_keys(self, bucket, timeout=None):
        """
        Streams the list of keys for the bucket through an iterator.
        """
        raise NotImplementedError

    def mapred(self, inputs, query, timeout=None):
        """
        Sends a MapReduce request synchronously.
        """
        raise NotImplementedError

    def stream_mapred(self, inputs, query, timeout=None):
        """
        Streams the results of a MapReduce request through an iterator.
        """
        raise NotImplementedError

    def set_client_id(self, client_id):
        """
        Set the client id. This overrides the default, random client
        id, which is automatically generated when none is specified in
        when creating the transport object.
        """
        raise NotImplementedError

    def get_client_id(self):
        """
        Fetch the client id for the transport.
        """
        raise NotImplementedError

    def create_search_index(self, index, schema=None, n_val=None):
        """
        Creates a yokozuna search index.
        """
        raise NotImplementedError

    def get_search_index(self, index):
        """
        Returns a yokozuna search index or None.
        """
        raise NotImplementedError

    def list_search_indexes(self):
        """
        Lists all yokozuna search indexes.
        """
        raise NotImplementedError

    def delete_search_index(self, index):
        """
        Deletes a yokozuna search index.
        """
        raise NotImplementedError

    def create_search_schema(self, schema, content):
        """
        Creates a yokozuna search schema.
        """
        raise NotImplementedError

    def get_search_schema(self, schema):
        """
        Returns a yokozuna search schema.
        """
        raise NotImplementedError

    def search(self, index, query, **params):
        """
        Performs a search query.
        """
        raise NotImplementedError

    def get_index(self, bucket, index, startkey, endkey=None,
                  return_terms=None, max_results=None, continuation=None,
                  timeout=None, term_regex=None):
        """
        Performs a secondary index query.
        """
        raise NotImplementedError

    def stream_index(self, bucket, index, startkey, endkey=None,
                     return_terms=None, max_results=None, continuation=None,
                     timeout=None):
        """
        Streams a secondary index query.
        """
        raise NotImplementedError

    def fulltext_add(self, index, *docs):
        """
        Adds documents to the full-text index.
        """
        raise NotImplementedError

    def fulltext_delete(self, index, docs=None, queries=None):
        """
        Removes documents from the full-text index.
        """
        raise NotImplementedError

    def get_counter(self, bucket, key, r=None, pr=None, basic_quorum=None,
                    notfound_ok=None):
        """
        Gets the value of a counter.
        """
        raise NotImplementedError

    def update_counter(self, bucket, key, value, w=None, dw=None, pw=None,
                       returnvalue=False):
        """
        Updates a counter by the given value.
        """
        raise NotImplementedError

    def _search_mapred_emu(self, index, query):
        """
        Emulates a search request via MapReduce. Used in the case
        where the transport supports MapReduce but has no native
        search capability.
        """
        phases = []
        if not self.phaseless_mapred():
            phases.append({'language': 'erlang',
                           'module': 'riak_kv_mapreduce',
                           'function': 'reduce_identity',
                           'keep': True})
        mr_result = self.mapred({'module': 'riak_search',
                                 'function': 'mapred_search',
                                 'arg': [index, query]},
                                phases)
        result = {'num_found': len(mr_result),
                  'max_score': 0.0,
                  'docs': []}
        for bucket, key, data in mr_result:
            if u'score' in data and data[u'score'][0] > result['max_score']:
                result['max_score'] = data[u'score'][0]
            result['docs'].append({u'id': key})
        return result

    def _get_index_mapred_emu(self, bucket, index, startkey, endkey=None):
        """
        Emulates a secondary index request via MapReduce. Used in the
        case where the transport supports MapReduce but has no native
        secondary index query capability.
        """
        phases = []
        if not self.phaseless_mapred():
            phases.append({'language': 'erlang',
                           'module': 'riak_kv_mapreduce',
                           'function': 'reduce_identity',
                           'keep': True})
        if endkey:
            result = self.mapred({'bucket': bucket,
                                  'index': index,
                                  'start': startkey,
                                  'end': endkey},
                                 phases)
        else:
            result = self.mapred({'bucket': bucket,
                                  'index': index,
                                  'key': startkey},
                                 phases)
        return [key for resultbucket, key in result]

    def _construct_mapred_json(self, inputs, query, timeout=None):
        if not self.phaseless_mapred() and (query is None or len(query) is 0):
            raise Exception(
                'Phase-less MapReduce is not supported by Riak node')

        job = {'inputs': inputs, 'query': query}
        if timeout is not None:
            job['timeout'] = timeout

        content = json.dumps(job)
        return content

    def _check_bucket_types(self, bucket_type):
        if not self.bucket_types():
            raise NotImplementedError('Server does not support bucket-types')

        if bucket_type.is_default():
            raise ValueError('Cannot manipulate the default bucket-type')

########NEW FILE########
__FILENAME__ = util
"""
Copyright 2010 Basho Technologies, Inc.

This file is provided to you under the Apache License,
Version 2.0 (the "License"); you may not use this file
except in compliance with the License.  You may obtain
a copy of the License at

  http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on an
"AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
KIND, either express or implied.  See the License for the
specific language governing permissions and limitations
under the License.
"""

import warnings
from collections import Mapping


def quacks_like_dict(object):
    """Check if object is dict-like"""
    return isinstance(object, Mapping)


def deep_merge(a, b):
    """Merge two deep dicts non-destructively

    Uses a stack to avoid maximum recursion depth exceptions

    >>> a = {'a': 1, 'b': {1: 1, 2: 2}, 'd': 6}
    >>> b = {'c': 3, 'b': {2: 7}, 'd': {'z': [1, 2, 3]}}
    >>> c = deep_merge(a, b)
    >>> from pprint import pprint; pprint(c)
    {'a': 1, 'b': {1: 1, 2: 7}, 'c': 3, 'd': {'z': [1, 2, 3]}}
    """
    assert quacks_like_dict(a), quacks_like_dict(b)
    dst = a.copy()

    stack = [(dst, b)]
    while stack:
        current_dst, current_src = stack.pop()
        for key in current_src:
            if key not in current_dst:
                current_dst[key] = current_src[key]
            else:
                if (quacks_like_dict(current_src[key])
                        and quacks_like_dict(current_dst[key])):
                    stack.append((current_dst[key], current_src[key]))
                else:
                    current_dst[key] = current_src[key]
    return dst


def deprecated(message, stacklevel=3):
    """
    Prints a deprecation warning to the console.
    """
    warnings.warn(message, UserWarning, stacklevel=stacklevel)

QUORUMS = ['r', 'pr', 'w', 'dw', 'pw', 'rw']
QDEPMESSAGE = """
Quorum accessors on type %s are deprecated. Use request-specific
parameters or bucket properties instead.
"""


def deprecateQuorumAccessors(klass, parent=None):
    """
    Adds deprecation warnings for the quorum get_* and set_*
    accessors, informing the user to switch to the appropriate bucket
    properties or requests parameters.
    """
    for q in QUORUMS:
        __deprecateQuorumAccessor(klass, parent, q)
    return klass


def __deprecateQuorumAccessor(klass, parent, quorum):
    propname = "_%s" % quorum
    getter_name = "get_%s" % quorum
    setter_name = "set_%s" % quorum
    if not parent:
        def direct_getter(self, value=None):
            deprecated(QDEPMESSAGE % klass.__name__)
            if value:
                return value
            return getattr(self, propname, "default")

        getter = direct_getter
    else:
        def parent_getter(self, value=None):
            deprecated(QDEPMESSAGE % klass.__name__)
            if value:
                return value
            parentInstance = getattr(self, parent)
            return getattr(self, propname,
                           getattr(parentInstance, propname, "default"))

        getter = parent_getter

    def setter(self, value):
        deprecated(QDEPMESSAGE % klass.__name__)
        setattr(self, propname, value)
        return self

    getter.__doc__ = """
       Gets the value used in requests for the {0!r} quorum.
       If not set, returns the passed value.

       .. deprecated:: 2.0.0
          Use the {0!r} bucket property or request option instead.

       :param value: the value to use if not set
       :type value: mixed
       :rtype: mixed""".format(quorum)

    setter.__doc__ = """
       Sets the value used in requests for the {0!r} quorum.

       .. deprecated:: 2.0.0
          Use the {0!r} bucket property or request option instead.

       :param value: the value to use if not set
       :type value: mixed
       """.format(quorum)

    setattr(klass, getter_name, getter)
    setattr(klass, setter_name, setter)


class lazy_property(object):
    '''
    A method decorator meant to be used for lazy evaluation and
    memoization of an object attribute. The property should represent
    immutable data, as it replaces itself on first access.
    '''

    def __init__(self, fget):
        self.fget = fget
        self.func_name = fget.__name__

    def __get__(self, obj, cls):
        if obj is None:
            return None
        value = self.fget(obj)
        setattr(obj, self.func_name, value)
        return value


def decode_index_value(index, value):
    if "_int" in index:
        return long(value)
    else:
        return str(value)

########NEW FILE########
__FILENAME__ = version
# This program is placed into the public domain.

"""
Gets the current version number.
If in a git repository, it is the current git tag.
Otherwise it is the one contained in the PKG-INFO file.

To use this script, simply import it in your setup.py file
and use the results of get_version() as your package version:

    from version import *

    setup(
        ...
        version=get_version(),
        ...
    )
"""

__all__ = ('get_version')

from os.path import dirname, isdir, join
import re
from subprocess import CalledProcessError, Popen, PIPE

try:
    from subprocess import check_output
except ImportError:
    def check_output(*popenargs, **kwargs):
        """Run command with arguments and return its output as a byte string.

        If the exit code was non-zero it raises a CalledProcessError.  The
        CalledProcessError object will have the return code in the returncode
        attribute and output in the output attribute.

        The arguments are the same as for the Popen constructor.  Example:

        >>> check_output(["ls", "-l", "/dev/null"])
        'crw-rw-rw- 1 root root 1, 3 Oct 18  2007 /dev/null\n'

        The stdout argument is not allowed as it is used internally.
        To capture standard error in the result, use stderr=STDOUT.

        >>> import sys
        >>> check_output(["/bin/sh", "-c",
        ...               "ls -l non_existent_file ; exit 0"],
        ...              stderr=sys.stdout)
        'ls: non_existent_file: No such file or directory\n'
        """
        if 'stdout' in kwargs:
            raise ValueError('stdout argument not allowed, it will be '
                             'overridden.')
        process = Popen(stdout=PIPE, *popenargs, **kwargs)
        output, unused_err = process.communicate()
        retcode = process.poll()
        if retcode:
            cmd = kwargs.get("args")
            if cmd is None:
                cmd = popenargs[0]
            raise CalledProcessError(retcode, cmd, output=output)
        return output

version_re = re.compile('^Version: (.+)$', re.M)


def get_version():
    d = dirname(__file__)

    if isdir(join(d, '.git')):
        # Get the version using "git describe".
        cmd = 'git describe --tags --match [0-9]*'.split()
        try:
            version = check_output(cmd).decode().strip()
        except CalledProcessError:
            print('Unable to get version number from git tags')
            exit(1)

        # PEP 386 compatibility
        if '-' in version:
            version = '.post'.join(version.split('-')[:2])

    else:
        # Extract the version from the PKG-INFO file.
        with open(join(d, 'PKG-INFO')) as f:
            version = version_re.search(f.read()).group(1)

    return version


if __name__ == '__main__':
    print(get_version())

########NEW FILE########
