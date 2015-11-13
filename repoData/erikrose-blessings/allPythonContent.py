__FILENAME__ = tests
# -*- coding: utf-8 -*-
"""Automated tests (as opposed to human-verified test patterns)

It was tempting to mock out curses to get predictable output from ``tigetstr``,
but there are concrete integration-testing benefits in not doing so. For
instance, ``tigetstr`` changed its return type in Python 3.2.3. So instead, we
simply create all our test ``Terminal`` instances with a known terminal type.
All we require from the host machine is that a standard terminfo definition of
xterm-256color exists.

"""
from __future__ import with_statement  # Make 2.5-compatible
from curses import tigetstr, tparm
from functools import partial
from StringIO import StringIO
import sys

from nose import SkipTest
from nose.tools import eq_

# This tests that __all__ is correct, since we use below everything that should
# be imported:
from blessings import *


TestTerminal = partial(Terminal, kind='xterm-256color')


def unicode_cap(cap):
    """Return the result of ``tigetstr`` except as Unicode."""
    return tigetstr(cap).decode('latin1')


def unicode_parm(cap, *parms):
    """Return the result of ``tparm(tigetstr())`` except as Unicode."""
    return tparm(tigetstr(cap), *parms).decode('latin1')


def test_capability():
    """Check that a capability lookup works.

    Also test that Terminal grabs a reasonable default stream. This test
    assumes it will be run from a tty.

    """
    t = TestTerminal()
    sc = unicode_cap('sc')
    eq_(t.save, sc)
    eq_(t.save, sc)  # Make sure caching doesn't screw it up.


def test_capability_without_tty():
    """Assert capability templates are '' when stream is not a tty."""
    t = TestTerminal(stream=StringIO())
    eq_(t.save, u'')
    eq_(t.red, u'')


def test_capability_with_forced_tty():
    """If we force styling, capabilities had better not (generally) be
    empty."""
    t = TestTerminal(stream=StringIO(), force_styling=True)
    eq_(t.save, unicode_cap('sc'))


def test_parametrization():
    """Test parametrizing a capability."""
    eq_(TestTerminal().cup(3, 4), unicode_parm('cup', 3, 4))


def test_height_and_width():
    """Assert that ``height_and_width()`` returns ints."""
    t = TestTerminal()  # kind shouldn't matter.
    assert isinstance(t.height, int)
    assert isinstance(t.width, int)


def test_stream_attr():
    """Make sure Terminal exposes a ``stream`` attribute that defaults to
    something sane."""
    eq_(Terminal().stream, sys.__stdout__)


def test_location():
    """Make sure ``location()`` does what it claims."""
    t = TestTerminal(stream=StringIO(), force_styling=True)

    with t.location(3, 4):
        t.stream.write(u'hi')

    eq_(t.stream.getvalue(), unicode_cap('sc') +
                             unicode_parm('cup', 4, 3) +
                             u'hi' +
                             unicode_cap('rc'))


def test_horizontal_location():
    """Make sure we can move the cursor horizontally without changing rows."""
    t = TestTerminal(stream=StringIO(), force_styling=True)
    with t.location(x=5):
        pass
    eq_(t.stream.getvalue(), unicode_cap('sc') +
                             unicode_parm('hpa', 5) +
                             unicode_cap('rc'))


def test_null_location():
    """Make sure ``location()`` with no args just does position restoration."""
    t = TestTerminal(stream=StringIO(), force_styling=True)
    with t.location():
        pass
    eq_(t.stream.getvalue(), unicode_cap('sc') +
                             unicode_cap('rc'))


def test_zero_location():
    """Make sure ``location()`` pays attention to 0-valued args."""
    t = TestTerminal(stream=StringIO(), force_styling=True)
    with t.location(0, 0):
        pass
    eq_(t.stream.getvalue(), unicode_cap('sc') +
                             unicode_parm('cup', 0, 0) +
                             unicode_cap('rc'))


def test_null_fileno():
    """Make sure ``Terminal`` works when ``fileno`` is ``None``.

    This simulates piping output to another program.

    """
    out = StringIO()
    out.fileno = None
    t = TestTerminal(stream=out)
    eq_(t.save, u'')


def test_mnemonic_colors():
    """Make sure color shortcuts work."""
    def color(num):
        return unicode_parm('setaf', num)

    def on_color(num):
        return unicode_parm('setab', num)

    # Avoid testing red, blue, yellow, and cyan, since they might someday
    # change depending on terminal type.
    t = TestTerminal()
    eq_(t.white, color(7))
    eq_(t.green, color(2))  # Make sure it's different than white.
    eq_(t.on_black, on_color(0))
    eq_(t.on_green, on_color(2))
    eq_(t.bright_black, color(8))
    eq_(t.bright_green, color(10))
    eq_(t.on_bright_black, on_color(8))
    eq_(t.on_bright_green, on_color(10))


def test_callable_numeric_colors():
    """``color(n)`` should return a formatting wrapper."""
    t = TestTerminal()
    eq_(t.color(5)('smoo'), t.magenta + 'smoo' + t.normal)
    eq_(t.color(5)('smoo'), t.color(5) + 'smoo' + t.normal)
    eq_(t.on_color(2)('smoo'), t.on_green + 'smoo' + t.normal)
    eq_(t.on_color(2)('smoo'), t.on_color(2) + 'smoo' + t.normal)


def test_null_callable_numeric_colors():
    """``color(n)`` should be a no-op on null terminals."""
    t = TestTerminal(stream=StringIO())
    eq_(t.color(5)('smoo'), 'smoo')
    eq_(t.on_color(6)('smoo'), 'smoo')


def test_naked_color_cap():
    """``term.color`` should return a stringlike capability."""
    t = TestTerminal()
    eq_(t.color + '', t.setaf + '')


def test_number_of_colors_without_tty():
    """``number_of_colors`` should return 0 when there's no tty."""
    # Hypothesis: once setupterm() has run and decided the tty supports 256
    # colors, it never changes its mind.
    raise SkipTest

    t = TestTerminal(stream=StringIO())
    eq_(t.number_of_colors, 0)
    t = TestTerminal(stream=StringIO(), force_styling=True)
    eq_(t.number_of_colors, 0)


def test_number_of_colors_with_tty():
    """``number_of_colors`` should work."""
    t = TestTerminal()
    eq_(t.number_of_colors, 256)


def test_formatting_functions():
    """Test crazy-ass formatting wrappers, both simple and compound."""
    t = TestTerminal()
    # By now, it should be safe to use sugared attributes. Other tests test
    # those.
    eq_(t.bold(u'hi'), t.bold + u'hi' + t.normal)
    eq_(t.green('hi'), t.green + u'hi' + t.normal)  # Plain strs for Python 2.x
    # Test some non-ASCII chars, probably not necessary:
    eq_(t.bold_green(u'boö'), t.bold + t.green + u'boö' + t.normal)
    eq_(t.bold_underline_green_on_red('boo'),
        t.bold + t.underline + t.green + t.on_red + u'boo' + t.normal)
    # Don't spell things like this:
    eq_(t.on_bright_red_bold_bright_green_underline('meh'),
        t.on_bright_red + t.bold + t.bright_green + t.underline + u'meh' +
                          t.normal)


def test_formatting_functions_without_tty():
    """Test crazy-ass formatting wrappers when there's no tty."""
    t = TestTerminal(stream=StringIO())
    eq_(t.bold(u'hi'), u'hi')
    eq_(t.green('hi'), u'hi')
    # Test non-ASCII chars, no longer really necessary:
    eq_(t.bold_green(u'boö'), u'boö')
    eq_(t.bold_underline_green_on_red('loo'), u'loo')
    eq_(t.on_bright_red_bold_bright_green_underline('meh'), u'meh')


def test_nice_formatting_errors():
    """Make sure you get nice hints if you misspell a formatting wrapper."""
    t = TestTerminal()
    try:
        t.bold_misspelled('hey')
    except TypeError, e:
        assert 'probably misspelled' in e.args[0]

    try:
        t.bold_misspelled(u'hey')  # unicode
    except TypeError, e:
        assert 'probably misspelled' in e.args[0]

    try:
        t.bold_misspelled(None)  # an arbitrary non-string
    except TypeError, e:
        assert 'probably misspelled' not in e.args[0]

    try:
        t.bold_misspelled('a', 'b')  # >1 string arg
    except TypeError, e:
        assert 'probably misspelled' not in e.args[0]


def test_init_descriptor_always_initted():
    """We should be able to get a height and width even on no-tty Terminals."""
    t = Terminal(stream=StringIO())
    eq_(type(t.height), int)


def test_force_styling_none():
    """If ``force_styling=None`` is passed to the constructor, don't ever do
    styling."""
    t = TestTerminal(force_styling=None)
    eq_(t.save, '')


def test_null_callable_string():
    """Make sure NullCallableString tolerates all numbers and kinds of args it
    might receive."""
    t = TestTerminal(stream=StringIO())
    eq_(t.clear, '')
    eq_(t.move(1, 2), '')
    eq_(t.move_x(1), '')

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# blessings documentation build configuration file, created by
# sphinx-quickstart on Thu Mar 31 13:40:27 2011.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os

import blessings

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
project = u'Blessings'
copyright = u'2011, Erik Rose'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '1.6'
# The full version, including alpha/beta/rc tags.
release = version

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
html_static_path = []

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
htmlhelp_basename = 'blessingsdoc'


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'blessings.tex', u'Blessings Documentation',
   u'Erik Rose', 'manual'),
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
    ('index', 'Blessings', u'Blessings Documentation',
     [u'Erik Rose'], 1)
]

########NEW FILE########
__FILENAME__ = fabfile
"""Run this using ``fabric``.

I can't remember any of this syntax on my own.

"""
from functools import partial
from os import environ
from os.path import abspath, dirname

from fabric.api import local, cd


local = partial(local, capture=False)

ROOT = abspath(dirname(__file__))

environ['PYTHONPATH'] = (((environ['PYTHONPATH'] + ':') if
    environ.get('PYTHONPATH') else '') + ROOT)


def doc(kind='html'):
    """Build Sphinx docs.

    Requires Sphinx to be installed.

    """
    with cd('docs'):
        local('make clean %s' % kind)


def updoc():
    """Build Sphinx docs and upload them to packages.python.org.

    Requires Sphinx-PyPI-upload to be installed.

    """
    doc('html')
    local('python setup.py upload_sphinx --upload-dir=docs/_build/html')

########NEW FILE########
