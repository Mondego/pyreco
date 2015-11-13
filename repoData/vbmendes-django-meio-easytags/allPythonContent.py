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
import urllib
import urllib2
import subprocess
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
site = __import__('site')
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
parser.add_option(
    "-v", "--version",
    dest="version",
    help="use a specific zc.buildout version"
)
parser.add_option(
    "-d", "--distribute",
    action="store_true",
    dest="use_distribute",
    default=False,
    help="Use Distribute rather than Setuptools."
)
parser.add_option(
    "--setup-source",
    action="callback",
    dest="setup_source",
    callback=normalize_to_url,
    nargs=1,
    type="string",
    help=(
        "Specify a URL or file location for the setup file. "
        "If you use Setuptools, this will default to " +
        setuptools_source + "; if you use Distribute, this "
        "will default to " + distribute_source + "."
    )
)
parser.add_option(
    "--download-base",
    action="callback",
    dest="download_base",
    callback=normalize_to_url,
    nargs=1,
    type="string",
    help=(
        "Specify a URL or directory for downloading "
        "zc.buildout and either Setuptools or Distribute. "
        "Defaults to PyPI."
    )
)
parser.add_option(
    "--eggs",
    help=(
        "Specify a directory for storing eggs.  Defaults to "
        "a temporary directory that is deleted when the "
        "bootstrap script completes."
    )
)
parser.add_option(
    "-t", "--accept-buildout-test-releases",
    dest='accept_buildout_test_releases',
    action="store_true",
    default=False,
    help=(
        "Normally, if you do not specify a --version, the "
        "bootstrap script and buildout gets the newest "
        "*final* versions of zc.buildout and its recipes and "
        "extensions for you.  If you use this flag, "
        "bootstrap and buildout will get the newest releases "
        "even if they are alphas or betas."
    )
)
parser.add_option(
    "-c", None,
    action="store",
    dest="config_file",
    help=(
        "Specify the path to the buildout configuration "
        "file to be used."
    )
)

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
zc.buildout.buildout.main(args)
if not options.eggs:  # clean up temporary egg directory
    shutil.rmtree(eggs_dir)

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# django-meio-easytags documentation build configuration file, created by
# sphinx-quickstart on Tue Feb 22 22:55:42 2011.
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
project = u'django-meio-easytags'
copyright = u'2011, Vinicius Mendes'

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
htmlhelp_basename = 'django-meio-easytagsdoc'


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'django-meio-easytags.tex', u'django-meio-easytags Documentation',
   u'Vinicius Mendes', 'manual'),
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
    ('index', 'django-meio-easytags', u'django-meio-easytags Documentation',
     [u'Vinicius Mendes'], 1)
]


# -- Options for Epub output ---------------------------------------------------

# Bibliographic Dublin Core info.
epub_title = u'django-meio-easytags'
epub_author = u'Vinicius Mendes'
epub_publisher = u'Vinicius Mendes'
epub_copyright = u'2011, Vinicius Mendes'

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
__FILENAME__ = library
# -*- coding: utf-8 -*-

'''
Created on 01/03/2011

@author: vbmendes
'''

from django.template import Library

from node import EasyNode, EasyAsNode


class EasyLibrary(Library):

    @classmethod
    def _get_name_and_renderer(cls, name, renderer):
        if not renderer:
            renderer = name
            name = renderer.__name__
        return name, renderer

    def easytag(self, name=None, renderer=None):
        return self._handle_decorator(EasyNode, name, renderer)

    def easyastag(self, name=None, renderer=None):
        return self._handle_decorator(EasyAsNode, name, renderer)

    def _handle_decorator(self, node_class, name, renderer):
        if not name and not renderer:
            return self.easytag
        if not renderer:
            if callable(name):
                renderer = name
                return self._register_easytag(node_class, renderer.__name__, renderer)
            else:
                def dec(renderer):
                    return self._register_easytag(node_class, name, renderer)
                return dec
        return self._register_easytag(node_class, name, renderer)

    def _register_easytag(self, node_class, name, renderer):
        if not renderer:
            renderer = name
            name = renderer.__name__

        def render_context(self, context, *args, **kwargs):
            return renderer(context, *args, **kwargs)

        get_argspec = classmethod(lambda cls: node_class.get_argspec(renderer))

        tag_node = type('%sEasyNode' % name, (node_class,), {
            'render_context': render_context,
            'get_argspec': get_argspec,
        })
        self.tag(name, tag_node.parse)
        return renderer

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = node
# -*- coding: utf-8 -*-

'''
Created on 20/02/2011

@author: vbmendes
'''

from inspect import getargspec

from django.template import Node, Variable, TemplateSyntaxError


is_kwarg = lambda bit: not bit[0] in (u'"', u"'") and u'=' in bit


def get_args_kwargs_from_bits(parser, bits):
    args = []
    kwargs = {}
    for bit in bits:
        if is_kwarg(bit):
            key, value = bit.split(u'=', 1)
            kwargs[key] = parser.compile_filter(value)
        else:
            if not kwargs:
                args.append(parser.compile_filter(bit))
            else:
                raise TemplateSyntaxError(u"Args must be before kwargs.")

    return {'args': tuple(args), 'kwargs': kwargs}


def SmartVariable(var):
    if hasattr(var, 'resolve'):
        return var
    return Variable(var)


class EasyNode(Node):

    @classmethod
    def parse_to_args_kwargs(cls, parser, token):
        bits = token.split_contents()
        return get_args_kwargs_from_bits(parser, bits[1:])

    @classmethod
    def parse(cls, parser, token):
        args_kwargs = cls.parse_to_args_kwargs(parser, token)
        cls.is_args_kwargs_valid(args_kwargs)
        return cls(args_kwargs)

    @classmethod
    def get_argspec(cls, func=None):
        func = func or cls.render_context
        return getargspec(func)

    @classmethod
    def is_args_kwargs_valid(cls, args_kwargs):
        render_context_spec = cls.get_argspec()

        args = args_kwargs['args']
        kwargs = args_kwargs['kwargs']

        valid_args_names = render_context_spec.args
        if 'self' in valid_args_names:
            valid_args_names.remove('self')
        if 'context' in valid_args_names:
            valid_args_names.remove('context')

        n_args_kwargs = len(args) + len(kwargs)

        max_n_args_kwargs = len(valid_args_names)
        if not render_context_spec.varargs and not render_context_spec.keywords and n_args_kwargs > max_n_args_kwargs:
            raise TemplateSyntaxError(u'Invalid number of args %s (max. %s)' % (n_args_kwargs, max_n_args_kwargs))

        min_n_args_kwargs = max_n_args_kwargs - len(render_context_spec.defaults or ())
        if n_args_kwargs < min_n_args_kwargs:
            raise TemplateSyntaxError(u'Invalid number of args %s (min. %s)' % (n_args_kwargs, max_n_args_kwargs))

        required_args_names = valid_args_names[len(args):min_n_args_kwargs]
        for required_arg_name in required_args_names:
            if not required_arg_name in kwargs:
                raise TemplateSyntaxError(u'Required arg missing: %s' % required_arg_name)

        first_kwarg_index = len(args)
        if not render_context_spec.keywords:
            valid_kwargs = valid_args_names[first_kwarg_index:]
            for kwarg in kwargs:
                if not kwarg in valid_kwargs:
                    raise TemplateSyntaxError(u'Invalid kwarg %s.' % kwarg)
        else:
            defined_args = valid_args_names[:first_kwarg_index]
            for kwarg in kwargs:
                if kwarg in defined_args:
                    raise TemplateSyntaxError(u'%s was defined twice.' % kwarg)

    def __init__(self, args_kwargs):
        self.args = [SmartVariable(arg) for arg in args_kwargs['args']]
        self.kwargs = dict((key, SmartVariable(value)) for key, value in args_kwargs['kwargs'].iteritems())

    def render(self, context):
        args = [arg.resolve(context) for arg in self.args]
        kwargs = dict((str(key), value.resolve(context)) for key, value in self.kwargs.iteritems())
        return self.render_context(context, *args, **kwargs)

    def render_context(self, context, *args, **kwargs):
        raise NotImplementedError


class EasyAsNode(EasyNode):

    @classmethod
    def parse_to_args_kwargs(cls, parser, token):
        bits = token.split_contents()[1:]
        if len(bits) >= 2 and bits[-2] == 'as':
            varname = bits[-1]
            bits = bits[:-2]
        else:
            varname = None
        args_kwargs = get_args_kwargs_from_bits(parser, bits)
        args_kwargs['varname'] = varname
        return args_kwargs

    def __init__(self, args_kwargs):
        super(EasyAsNode, self).__init__(args_kwargs)
        self.varname = args_kwargs['varname']

    def render(self, context):
        rendered = super(EasyAsNode, self).render(context)
        if self.varname:
            context[self.varname] = rendered
            return u''
        return rendered

########NEW FILE########
__FILENAME__ = test_library
# -*- coding: utf-8 -*-

'''
Created on 01/03/2011

@author: vbmendes
'''

import unittest

from django import template

from easytags import EasyLibrary
from easytags import EasyNode, EasyAsNode


class LibraryTests(unittest.TestCase):

    def test_easy_library_register_easy_node(self):
        def test_tag(context):
            return u'my return'

        register = EasyLibrary()
        register.easytag(test_tag)

        parser = template.Parser([])
        token = template.Token(template.TOKEN_BLOCK, 'test_tag')

        self.assertTrue('test_tag' in register.tags)

        test_node = register.tags['test_tag'](parser, token)

        self.assertTrue(isinstance(test_node, EasyNode))

        context = template.Context({})

        self.assertEquals(u'my return', test_node.render(context))

    def test_easy_library_register_easy_node_with_parameters(self):
        def test_tag(context, arg1):
            return arg1

        register = EasyLibrary()
        register.easytag(test_tag)

        parser = template.Parser([])
        token = template.Token(template.TOKEN_BLOCK, 'test_tag "my arg"')
        test_node = register.tags['test_tag'](parser, token)

        context = template.Context({})
        self.assertEquals(u'my arg', test_node.render(context))

    def test_easy_library_register_tags_with_custom_names(self):
        def test_tag(context):
            return u''

        register = EasyLibrary()
        register.easytag('tag_name', test_tag)

        self.assertTrue('tag_name' in register.tags)

    def test_easy_library_register_tags_as_decorating_method(self):
        def test_tag(context):
            return u''

        register = EasyLibrary()
        register.easytag()(test_tag)

        self.assertTrue('test_tag' in register.tags)

    def test_easy_library_register_tags_as_decorating_method_with_name(self):
        def test_tag(context):
            return u''

        register = EasyLibrary()
        register.easytag('tag_name')(test_tag)

        self.assertTrue('tag_name' in register.tags)

    def test_easy_library_register_tags_as_decorating_method_with_name_kwarg(self):
        def test_tag(context):
            return u''

        register = EasyLibrary()
        register.easytag(name='tag_name')(test_tag)

        self.assertTrue('tag_name' in register.tags)

    def test_easy_library_register_tags_keeps_decorated_function_data(self):
        def test_tag(context):
            return u''

        register = EasyLibrary()
        test_tag = register.easytag(name='tag_name')(test_tag)

        self.assertEquals('test_tag', test_tag.__name__)

    def test_easy_library_register_as_tags(self):
        def test_tag(context):
            return u'my return'

        register = EasyLibrary()
        register.easyastag(test_tag)

        parser = template.Parser([])
        token = template.Token(template.TOKEN_BLOCK, 'test_tag as varname')

        self.assertTrue('test_tag' in register.tags)

        test_node = register.tags['test_tag'](parser, token)

        self.assertTrue(isinstance(test_node, EasyAsNode))

        context = template.Context({})

        self.assertEquals(u'', test_node.render(context))
        self.assertEquals(u'my return', context['varname'])

########NEW FILE########
__FILENAME__ = test_node
# -*- coding: utf-8 -*-

'''
Created on 20/02/2011

@author: vbmendes
'''

from django import template
from django.template import Context, Variable, TemplateSyntaxError
from django.test import TestCase

from easytags.node import EasyNode, EasyAsNode


class MyEasyNode(EasyNode):

    def render_context(self, context, arg1, kwarg1=None):
        return arg1


class MyEasyNodeWithoutDefaults(EasyNode):

    def render_context(self, context, arg1):
        return arg1


class NodeTests(TestCase):

    def test_resolves_absolute_string(self):
        context = Context({})
        args_kwargs = {'args': ('"absolute string"',), 'kwargs': {}}

        node = MyEasyNode(args_kwargs)

        self.assertEquals(
            u'absolute string',
            node.render(context),
        )

    def test_resolve_simple_variable(self):
        context = Context({'simple_variable': u'simple variable value'})
        args_kwargs = {'args': ('simple_variable',), 'kwargs': {}}

        node = MyEasyNode(args_kwargs)

        self.assertEquals(
            u'simple variable value',
            node.render(context),
        )

    def test_resolve_dict_variable(self):
        context = Context({'mydict': {'key': u'value'}})
        args_kwargs = {'args': ('mydict.key',), 'kwargs': {}}

        node = MyEasyNode(args_kwargs)

        self.assertEquals(
            u'value',
            node.render(context),
        )

    def test_resolve_absolute_string_in_kwargs(self):
        context = Context({})
        args_kwargs = {'args': (), 'kwargs': {'arg1': u'"absolute string"'}}

        node = MyEasyNode(args_kwargs)

        self.assertEquals(
            u'absolute string',
            node.render(context),
        )

    def test_resolve_simple_variable_in_kwargs(self):
        context = Context({'simple_variable': u'simple variable value'})
        args_kwargs = {'args': (), 'kwargs': {'arg1': u'simple_variable'}}

        node = MyEasyNode(args_kwargs)

        self.assertEquals(
            u'simple variable value',
            node.render(context),
        )

    def test_resolve_dict_variable_in_kwargs(self):
        context = Context({'mydict': {'key': u'value'}})
        args_kwargs = {'args': (), 'kwargs': {'arg1': 'mydict.key'}}

        node = MyEasyNode(args_kwargs)

        self.assertEquals(
            u'value',
            node.render(context),
        )

    def test_node_parse_returns_node_instance(self):
        parser = template.Parser([])
        token = template.Token(template.TOKEN_BLOCK, 'tag_name arg1 kwarg1="a=1"')
        node = MyEasyNode.parse(parser, token)

        self.assertTrue(isinstance(node, MyEasyNode))
        self.assertEquals(u'arg1', node.args[0].token)
        self.assertEquals(u'"a=1"', node.kwargs['kwarg1'].token)

    def test_node_parse_verifies_invalid_kwarg(self):
        parser = template.Parser([])
        token = template.Token(template.TOKEN_BLOCK, 'tag_name arg1 invalid_kwarg="a=1"')

        self.assertRaises(TemplateSyntaxError, MyEasyNode.parse, parser, token)

    def test_node_parse_verifies_kwarg_already_satisfied_by_arg(self):
        parser = template.Parser([])
        token = template.Token(template.TOKEN_BLOCK, 'tag_name arg1 arg1="a=1"')

        self.assertRaises(TemplateSyntaxError, MyEasyNode.parse, parser, token)

    def test_node_parse_verifies_if_there_are_more_args_kwargs_then_method_requires(self):
        parser = template.Parser([])
        token = template.Token(template.TOKEN_BLOCK, 'tag_name arg1 arg2 arg3')

        self.assertRaises(TemplateSyntaxError, MyEasyNode.parse, parser, token)

    def test_node_parse_verifies_if_there_are_less_args_kwargs_then_method_requires(self):
        parser = template.Parser([])
        token = template.Token(template.TOKEN_BLOCK, 'tag_name')

        self.assertRaises(TemplateSyntaxError, MyEasyNode.parse, parser, token)

    def test_node_parse_verifies_if_required_arg_is_specified(self):
        parser = template.Parser([])
        token = template.Token(template.TOKEN_BLOCK, 'tag_name kwarg1="a"')

        self.assertRaises(TemplateSyntaxError, MyEasyNode.parse, parser, token)

    def test_node_can_have_no_args_with_default_value(self):
        parser = template.Parser([])
        token = template.Token(template.TOKEN_BLOCK, 'tag_name "a"')

        node = MyEasyNodeWithoutDefaults.parse(parser, token)

        self.assertEquals(u'a' ,node.args[0].var)

    def test_node_can_receive_infinite_args(self):
        parser = template.Parser([])
        token = template.Token(template.TOKEN_BLOCK, 'tag_name "a" "b" "c" "d"')

        MyEasyNode = type('MyEasyNodeWithArgs', (EasyNode,), {
            'render_context': lambda self, context, *args: reduce(lambda x, y: x + y, args)
        })

        node = MyEasyNode.parse(parser, token)

        self.assertEquals(u'abcd' ,node.render(Context({})))

    def test_node_can_receive_required_arg_and_infinite_args(self):
        parser = template.Parser([])
        token = template.Token(template.TOKEN_BLOCK, 'tag_name "a" "b" "c" "d"')

        MyEasyNode = type('MyEasyNode', (EasyNode,), {
            'render_context': lambda self, context, arg1, *args: arg1 + reduce(lambda x, y: x + y, args)
        })

        node = MyEasyNode.parse(parser, token)

        self.assertEquals(u'abcd' ,node.render(Context({})))

    def test_node_verifies_if_required_arg_is_specified_when_node_can_receive_infinite_args(self):
        parser = template.Parser([])
        token = template.Token(template.TOKEN_BLOCK, 'tag_name')

        MyEasyNode = type('MyEasyNode', (EasyNode,), {
            'render_context': lambda self, context, arg1, *args: True
        })

        self.assertRaises(TemplateSyntaxError, MyEasyNode.parse, parser, token)

    def test_node_can_receive_kwargs(self):
        parser = template.Parser([])
        token = template.Token(template.TOKEN_BLOCK, 'tag_name arg1="bla" arg2="ble"')

        MyEasyNode = type('MyEasyNode', (EasyNode,), {
            'render_context': lambda self, context, **kwargs:\
                reduce(lambda x,y: u'%s%s' % (x, y),
                    ['%s=%s' % (key, value) for key, value in kwargs.items()])
        })

        node = MyEasyNode.parse(parser, token)

        self.assertEquals(u'arg1=blaarg2=ble', node.render(Context({})))

    def test_node_verifies_if_required_arg_is_specified_when_code_can_receive_kwargs(self):
        parser = template.Parser([])
        token = template.Token(template.TOKEN_BLOCK, 'tag_name')

        MyEasyNode = type('MyEasyNode', (EasyNode,), {
            'render_context': lambda self, context, arg1, **kwargs: True
        })

        self.assertRaises(TemplateSyntaxError, MyEasyNode.parse, parser, token)

    def test_node_verifies_if_required_kwarg_is_specified_when_code_can_receive_kwargs(self):
        parser = template.Parser([])
        token = template.Token(template.TOKEN_BLOCK, 'tag_name arg2="2"')

        MyEasyNode = type('MyEasyNode', (EasyNode,), {
            'render_context': lambda self, context, arg1, **kwargs: True
        })

        self.assertRaises(TemplateSyntaxError, MyEasyNode.parse, parser, token)

    def test_if_node_can_receive_args_and_kwargs(self):
        parser = template.Parser([])
        token = template.Token(template.TOKEN_BLOCK, 'tag_name "1" arg2="2"')

        MyEasyNode = type('MyEasyNode', (EasyNode,), {
            'render_context': lambda self, context, *args, **kwargs:
                args[0]+kwargs.items()[0][0]+u'='+kwargs.items()[0][1]
        })

        node = MyEasyNode.parse(parser, token)

        self.assertEquals(u'1arg2=2', node.render(Context({})))

    def test_if_node_can_receive_required_arg_and_kwargs(self):
        parser = template.Parser([])
        token = template.Token(template.TOKEN_BLOCK, 'tag_name "required" "2" arg3="3"')

        MyEasyNode = type('MyEasyNode', (EasyNode,), {
            'render_context': lambda self, context, arg1, *args, **kwargs:
                arg1+args[0]+kwargs.items()[0][0]+u'='+kwargs.items()[0][1]
        })

        node = MyEasyNode.parse(parser, token)

        self.assertEquals(u'required2arg3=3', node.render(Context({})))

    def test_node_verifies_if_required_arg_is_specified_two_times(self):
        parser = template.Parser([])
        token = template.Token(template.TOKEN_BLOCK, 'tag_name "required" arg1="3"')

        MyEasyNode = type('MyEasyNode', (EasyNode,), {
            'render_context': lambda self, context, arg1, *args, **kwargs: True
        })

        self.assertRaises(TemplateSyntaxError, MyEasyNode.parse, parser, token)

    def test_node_applies_filters_to_args(self):
        parser = template.Parser([])
        context = Context({})
        token = template.Token(template.TOKEN_BLOCK, 'tag_name "string1 string2"|slugify|upper')
        args_kwargs = EasyNode.parse_to_args_kwargs(parser, token)

        node = MyEasyNode(args_kwargs)

        self.assertEquals(
            u'STRING1-STRING2',
            node.render(context),
        )

    def test_node_applies_filters_to_kwargs(self):
        parser = template.Parser([])
        context = Context({})
        token = template.Token(template.TOKEN_BLOCK, 'tag_name arg1="string1 string2"|slugify|upper')
        args_kwargs = EasyNode.parse_to_args_kwargs(parser, token)

        node = MyEasyNode(args_kwargs)

        self.assertEquals(
            u'STRING1-STRING2',
            node.render(context),
        )

    def test_node_applies_filters_to_variable_in_args(self):
        parser = template.Parser([])
        context = Context({'variable': "string1 string2"})
        token = template.Token(template.TOKEN_BLOCK, 'tag_name variable|slugify|upper')
        args_kwargs = EasyNode.parse_to_args_kwargs(parser, token)

        node = MyEasyNode(args_kwargs)

        self.assertEquals(
            u'STRING1-STRING2',
            node.render(context),
        )

    def test_node_applies_filters_to_variable_in_kwargs(self):
        parser = template.Parser([])
        context = Context({'variable': "string1 string2"})
        token = template.Token(template.TOKEN_BLOCK, 'tag_name arg1=variable|slugify|upper')
        args_kwargs = EasyNode.parse_to_args_kwargs(parser, token)

        node = MyEasyNode(args_kwargs)

        self.assertEquals(
            u'STRING1-STRING2',
            node.render(context),
        )

    def test_as_node_receives_as_parameter(self):
        parser = template.Parser([])
        token = template.Token(template.TOKEN_BLOCK, u'tag_name as varname')

        MyEasyAsNode = type('MyEasyAsNode', (EasyAsNode,), {
            'render_context': lambda self, context, **kwargs: 'value'
        })

        node = MyEasyAsNode.parse(parser, token)
        context = Context()

        self.assertEqual('', node.render(context))
        self.assertEqual('value', context['varname'])

    def test_as_node_can_be_used_without_as_parameter(self):
        parser = template.Parser([])
        token = template.Token(template.TOKEN_BLOCK, u'tag_name "value"')

        MyEasyAsNode = type('MyEasyAsNode', (EasyAsNode,), {
            'render_context': lambda self, context, arg1, **kwargs: arg1
        })

        node = MyEasyAsNode.parse(parser, token)
        context = Context()

        self.assertEqual('value', node.render(context))


########NEW FILE########
__FILENAME__ = test_parser
# -*- coding: utf-8 -*-

'''
Created on 20/02/2011

@author: vbmendes
'''

from django import template
from django.test import TestCase

from easytags.node import EasyNode, EasyAsNode


class ParserTests(TestCase):

    def test_environment(self):
        """
            Just make sure everything is set up correctly.
        """
        self.assertTrue(True)

    def test_parse_tag_with_args(self):
        """
            Tests if the parser recognizes one tag and parses its args
        """
        parser = template.Parser([])
        token = template.Token(template.TOKEN_BLOCK, 'tag_name "arg1" "arg2"')
        args_kwargs = EasyNode.parse_to_args_kwargs(parser, token)
        args_kwargs_str = {'args': tuple([x.token for x in args_kwargs['args']]),
                           'kwargs': dict((key, value.token) for key, value in args_kwargs['kwargs'].iteritems())}
        self.assertEquals(
            {'args': ('"arg1"', '"arg2"'), 'kwargs': {}},
            args_kwargs_str
        )

    def test_parse_tag_with_kwargs(self):
        """
            Tests if the parser recognizes one tag and parses its kwargs
        """
        parser = template.Parser([])
        token = template.Token(template.TOKEN_BLOCK, 'tag_name kwarg1="1" kwarg2="2"')
        args_kwargs = EasyNode.parse_to_args_kwargs(parser, token)
        args_kwargs_str = {'args': tuple([x.token for x in args_kwargs['args']]),
                           'kwargs': dict((key, value.token) for key, value in args_kwargs['kwargs'].iteritems())}
        self.assertEquals(
            {'args': (), 'kwargs': {'kwarg1': '"1"', 'kwarg2': '"2"'}},
            args_kwargs_str
        )

    def test_parse_tag_with_args_and_kwargs(self):
        """
            Tests if the parser recognizes one tag and parses its args and kwargs
        """
        parser = template.Parser([])
        token = template.Token(template.TOKEN_BLOCK, 'tag_name "arg1" kwarg1="1"')
        args_kwargs = EasyNode.parse_to_args_kwargs(parser, token)
        args_kwargs_str = {'args': tuple([x.token for x in args_kwargs['args']]),
                           'kwargs': dict((key, value.token) for key, value in args_kwargs['kwargs'].iteritems())}
        self.assertEquals(
            {'args': ('"arg1"',), 'kwargs': {'kwarg1': '"1"'}},
            args_kwargs_str
        )

    def test_parse_tag_with_variable_arg(self):
        parser = template.Parser([])
        token = template.Token(template.TOKEN_BLOCK, 'tag_name argvariable')
        args_kwargs = EasyNode.parse_to_args_kwargs(parser, token)
        args_kwargs_str = {'args': tuple([x.token for x in args_kwargs['args']]),
                           'kwargs': dict((key, value.token) for key, value in args_kwargs['kwargs'].iteritems())}
        self.assertEquals(
            {'args': ('argvariable',), 'kwargs': {}},
            args_kwargs_str
        )

    def test_parse_tag_with_equals_in_arg_value(self):
        parser = template.Parser([])
        token = template.Token(template.TOKEN_BLOCK, 'tag_name "a=1"')
        args_kwargs = EasyNode.parse_to_args_kwargs(parser, token)
        args_kwargs_str = {'args': tuple([x.token for x in args_kwargs['args']]),
                           'kwargs': dict((key, value.token) for key, value in args_kwargs['kwargs'].iteritems())}
        self.assertEquals(
            {'args': ('"a=1"',), 'kwargs': {}},
            args_kwargs_str
        )

    def test_parse_tag_with_equals_in_kwarg_value(self):
        parser = template.Parser([])
        token = template.Token(template.TOKEN_BLOCK, 'tag_name kwarg1="a=1"')
        args_kwargs = EasyNode.parse_to_args_kwargs(parser, token)
        args_kwargs_str = {'args': tuple([x.token for x in args_kwargs['args']]),
                           'kwargs': dict((key, value.token) for key, value in args_kwargs['kwargs'].iteritems())}
        self.assertEquals(
            {'args': (), 'kwargs': {'kwarg1': '"a=1"'}},
            args_kwargs_str
        )

    def test_parse_tag_special_symbol_in_arg_value(self):
        parser = template.Parser([])
        token = template.Token(template.TOKEN_BLOCK, u'tag_name "será?"')
        args_kwargs = EasyNode.parse_to_args_kwargs(parser, token)
        args_kwargs_str = {'args': tuple([x.token for x in args_kwargs['args']]),
                           'kwargs': dict((key, value.token) for key, value in args_kwargs['kwargs'].iteritems())}
        self.assertEquals(
            {'args': (u'"será?"',), 'kwargs': {}},
            args_kwargs_str
        )

    def test_parse_tag_special_symbol_in_kwarg_value(self):
        parser = template.Parser([])
        token = template.Token(template.TOKEN_BLOCK, u'tag_name kwarg1="será?"')
        args_kwargs = EasyNode.parse_to_args_kwargs(parser, token)
        args_kwargs_str = {'args': tuple([x.token for x in args_kwargs['args']]),
                           'kwargs': dict((key, value.token) for key, value in args_kwargs['kwargs'].iteritems())}
        self.assertEquals(
            {'args': (), 'kwargs': {'kwarg1': u'"será?"'}},
            args_kwargs_str
        )

    def test_parse_tag_with_args_after_kwargs_raises_exception(self):
        parser = template.Parser([])
        token = template.Token(template.TOKEN_BLOCK, u'tag_name kwarg1="será?" my_arg')
        self.assertRaises(template.TemplateSyntaxError,
            EasyNode.parse_to_args_kwargs, parser, token
        )

    def test_parse_as_tag_with_args(self):
        """
            Tests if the parser recognizes one tag and parses its args even when using EasyAsNode
        """
        parser = template.Parser([])
        token = template.Token(template.TOKEN_BLOCK, 'tag_name "arg1" "arg2"')
        args_kwargs = EasyAsNode.parse_to_args_kwargs(parser, token)
        args_kwargs_str = {'args': tuple([x.token for x in args_kwargs['args']]),
                           'kwargs': dict((key, value.token) for key, value in args_kwargs['kwargs'].iteritems()),
                           'varname': args_kwargs['varname']}
        self.assertEquals(
            {'args': ('"arg1"', '"arg2"'), 'kwargs': {}, 'varname': None},
            args_kwargs_str
        )

    def test_parse_as_tag_with_args_and_as_parameter(self):
        """
            Tests if the parser recognizes one tag and parses its args and as parameter
        """
        parser = template.Parser([])
        token = template.Token(template.TOKEN_BLOCK, 'tag_name "arg1" "arg2" as varname')
        args_kwargs = EasyAsNode.parse_to_args_kwargs(parser, token)
        args_kwargs_str = {'args': tuple([x.token for x in args_kwargs['args']]),
                           'kwargs': dict((key, value.token) for key, value in args_kwargs['kwargs'].iteritems()),
                           'varname': args_kwargs['varname']}
        self.assertEquals(
            {'args': ('"arg1"', '"arg2"'), 'kwargs': {}, 'varname': 'varname'},
            args_kwargs_str
        )

########NEW FILE########
__FILENAME__ = testsettings
DATABASE_ENGINE = 'sqlite3'
DATABASE_NAME = '/tmp/easytags.db'
INSTALLED_APPS = ('easytags',)
ROOT_URLCONF = ('easytags.urls',)

########NEW FILE########
