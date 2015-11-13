__FILENAME__ = cli
#!/usr/bin/env python
#
# Command line interface to dayone_export
#
# For help, run `dayone_export --help`

from . import dayone_export, VERSION, compat
import dateutil.parser
import jinja2
import argparse
import codecs
import locale
import os
import sys


def template_not_found_message(template):
    message = ["Template not found: {0}".format(template),
            "Use the `--template` option to specify a template."]
    try:
        from pkg_resources import resource_listdir
        message.extend(["The following templates are built-in:"] +
                resource_listdir('dayone_export', 'templates'))
    except ImportError:
        pass
    return '\n'.join(message)


def parse_args(args=None):
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
      description="Export Day One entries using a Jinja template",
      usage="%(prog)s [--output FILE] [opts] journal",
      epilog="""If the Day One package has photos, you may need to copy
        the "photos" folder from the package into the same directory
        as the output file.""")
    parser.add_argument('journal', help="path to Day One journal package")
    parser.add_argument('--output', metavar="FILE", default="",
      help="file to write (default print to stdout). "
            "Using strftime syntax will produce multiple "
            "output files with entries grouped by date.")
    parser.add_argument('--format', metavar="FMT",
      help="output format (default guess from output file extension)")
    parser.add_argument('--template', metavar="NAME",
      help="name or file of template to use")
    parser.add_argument('--template-dir', metavar="DIR",
      help='location of templates (default ~/.dayone_export)')
    parser.add_argument('--tags',
      help='export entries with these comma-separated tags. Tag \'any\' has a special meaning.')
    parser.add_argument('--exclude',
      help='exclude entries with these comma-separated tags')
    parser.add_argument('--after', metavar='DATE',
      help='export entries published after this date')
    parser.add_argument('--reverse', action="store_true",
      help="display in reverse chronological order")
    parser.add_argument('--autobold', action="store_true",
      help="autobold first lines (titles) of posts")
    parser.add_argument('--nl2br', action="store_true",
      help="convert each new line to a <br>")

    parser.add_argument('--version', action='version', version=VERSION)
    return parser.parse_args(args)

# command line interface
def run(args=None):
    locale.setlocale(locale.LC_ALL, '')
    args = parse_args(args)

    # determine output format
    if args.format is None:
        args.format = os.path.splitext(args.output)[1][1:] if args.output \
                      else 'html'
    if args.format.lower() in ['md', 'markdown', 'mdown', 'mkdn']:
        args.format = 'md'

    # Check journal files exist
    args.journal = os.path.expanduser(args.journal)
    if not os.path.exists(args.journal):
        return "File not found: " + args.journal
    if not os.path.exists(os.path.join(args.journal, 'entries')):
        return "Not a valid Day One package: " + args.journal

    # tags
    tags = args.tags
    if tags is not None:
        if tags != 'any':
            tags = [tag.strip() for tag in tags.split(',')]

    # excluded tags
    excluded_tags = args.exclude
    if excluded_tags is not None:
        excluded_tags = [tag.strip() for tag in excluded_tags.split(',')]

    # parse after date
    if args.after:
        try:
            args.after = dateutil.parser.parse(args.after)
        except (ValueError, OverflowError):
            return "Unable to parse date '{0}'".format(args.after)

    generator = dayone_export(args.journal, template=args.template,
        reverse=args.reverse, tags=tags, exclude=excluded_tags,
        after=args.after, format=args.format, template_dir=args.template_dir,
        autobold=args.autobold, nl2br=args.nl2br, filename_template=args.output)

    try:

        # Output is a generator returning each file's name and contents one at a time
        for filename, output in generator:
            if args.output:
                with codecs.open(filename, 'w', encoding='utf-8') as f:
                    f.write(output)
            else:
                compat.print_bytes(output.encode('utf-8'))
                compat.print_bytes("\n".encode('utf-8'))

    except jinja2.TemplateNotFound as err:
        return template_not_found_message(err)
    except IOError as err:
        return str(err)


if __name__ == "__main__":
    sys.exit(run())

########NEW FILE########
__FILENAME__ = compat
"""Python 2 vs 3 compatibility."""
import sys

PY2 = sys.version_info[0] == 2

if PY2:
    string_types = (str, unicode)
    print_bytes = lambda s: sys.stdout.write(s)
else:
    string_types = (str,)
    print_bytes = lambda s: sys.stdout.buffer.write(s)

########NEW FILE########
__FILENAME__ = filters
# Copyright (c) 2012, Nathan Grigg
# All rights reserved.
# BSD License

import os
import re
import sys
import base64
import pytz
import markdown
from io import BytesIO

MARKER = 'zpoqjd_marker_zpoqjd'
RE_PERCENT_MINUS = re.compile(r'(?<!%)%-')
RE_REMOVE_MARKER = re.compile(MARKER + '0*')

class WarnOnce(object):
    """Issue a warning only one time.

    >>> warn_once = WarnOnce({'foo': 'bar'})
    >>> warn_once('foo')
    (print to stderr) bar

    >>> warn_once('foo')
    (nothing happens)
    """
    def __init__(self, warnings):
        self.warnings = warnings
        self.issued = dict((k, False) for k in warnings)

    def __call__(self, warning):
        if not self.issued[warning]:
            self.issued[warning] = True
            sys.stderr.write(self.warnings[warning] + '\n')

warn_once = WarnOnce({
'imgbase64': 'Warning: Cannot load Python Imaging Library. Encoding full-size images.'
})

#############################
# Markdown
#############################

def markdown_filter(autobold=False, nl2br=False):
    """Returns a markdown filter"""
    extensions = ['footnotes',
                  'tables',
                  'smart_strong',
                  'fenced_code',
                  'attr_list',
                  'def_list',
                  'abbr',
                  'dayone_export.mdx_hashtag',
                  'dayone_export.mdx_urlize',
                 ]

    if autobold:
        extensions.append('dayone_export.mdx_autobold')

    if nl2br:
        extensions.append('nl2br')

    md = markdown.Markdown(extensions=extensions,
      extension_configs={'footnotes': [('UNIQUE_IDS', True)]},
      output_format='html5')

    def markup(text, *args, **kwargs):
        md.reset()
        return md.convert(text)

    return markup


#############################
# Date formatting
#############################
def format(value, fmt='%A, %b %-d, %Y', tz=None):
    """Format a date or time."""

    if tz:
        value = value.astimezone(pytz.timezone(tz))
    try:
        return value.strftime(fmt)
    except ValueError:
        return _strftime_portable(value, fmt)

def _strftime_portable(value, fmt='%A, %b %-d, %Y'):
    marked = value.strftime(RE_PERCENT_MINUS.sub(MARKER + "%", fmt))
    return RE_REMOVE_MARKER.sub("", marked)


#############################
# Escape Latex (http://flask.pocoo.org/snippets/55/)
#############################
LATEX_SUBS = (
    (re.compile(r'\\'), r'\\textbackslashzzz'),
    (re.compile(r'([{}_#%&$])'), r'\\\1'),
    (re.compile(r'~'), r'\\textasciitilde{}'),
    (re.compile(r'\^'), r'\\textasciicircum{}'),
    (re.compile(r'"'), r"''"),
    (re.compile(r'\.\.\.+'), r'\\ldots'),
    (re.compile(r'\\textbackslashzzz'), r'\\textbackslash{}'),
)

def escape_tex(value):
    newval = value
    for pattern, replacement in LATEX_SUBS:
        newval = pattern.sub(replacement, newval)
    return newval


#############################
# Base64 encode images
#############################
try:
    from PIL import Image
except ImportError:
    # if we don't have PIL available, include the image in its
    # original size
    def imgbase64(infile, max_size=None, dayone_folder=None):
        warn_once('imgbase64')
        filename, ext = os.path.splitext(infile)
        with open(dayone_folder + "/" + infile, "rb") as image_file:
            base64data = base64.b64encode(image_file.read())
            return "data:image/%s;base64,%s" % (ext[1:], base64data)
else:
    # if we have PIL, resize the image
    def imgbase64(infile, max_size=400, dayone_folder=None):
        size = max_size, max_size
        filename, ext = os.path.splitext(infile)
        im = Image.open(dayone_folder + "/" + infile)
        im.thumbnail(size, Image.ANTIALIAS)
        output = BytesIO()
        im.save(output, "jpeg")  # we assume that we get best compressions with jpeg
        base64data = output.getvalue().encode("base64")
        return "data:image/jpeg;base64,%s" % (base64data)

########NEW FILE########
__FILENAME__ = mdx_autobold
"""Autobold preprocessor for Markdown.

Makes the first line of text into a heading.
"""

import markdown

MAX_LEN = 99

class AutoboldPreprocessor(markdown.preprocessors.Preprocessor):
    def run(self, lines):
        """Makes the first line a heading"""
        line = lines[0]
        if line.startswith('# ') or len(line) > MAX_LEN:
            return lines
        else:
            return ["# " + line] + lines[1:]

class AutoboldExtension(markdown.Extension):
    """The extension to be installed"""
    def extendMarkdown(self, md, md_globals):
        md.preprocessors['autobold'] = AutoboldPreprocessor(md)

def makeExtension(configs=None) :
    return AutoboldExtension(configs=configs)

########NEW FILE########
__FILENAME__ = mdx_hashtag
"""Hashtag preprocessor for Markdown.

Changes lines beginning with #tag to \#tag to prevent #tag from
becoming <h1>tag</h1>.
"""

import markdown
import re

# Global Vars
HASHTAG_RE = re.compile('#\w')

class HashtagPreprocessor(markdown.preprocessors.Preprocessor):
    def run(self, lines):
        """Add a backslash before #\w at the beginning of each line"""
        transformed = []
        for line in lines:
            if HASHTAG_RE.match(line): # matches beginning of lines only
                line = '\\' + line
            transformed.append(line)

        return transformed

class HashtagExtension(markdown.Extension):
    """The extension to be installed"""
    def extendMarkdown(self, md, md_globals):
        md.preprocessors.add('hashtag', HashtagPreprocessor(md), '>reference')

def makeExtension(configs=None) :
    return HashtagExtension(configs=configs)

########NEW FILE########
__FILENAME__ = mdx_urlize
# encoding: utf-8
# Adapted from https://github.com/bruth/marky, by Byron Ruth

import re
import markdown
import logging
import time


PROTOCOL_MATCH = re.compile(r'^(news|telnet|nttp|file|http|ftp|https)')
# from John Gruber
URLIZE_RE = '(?!%s)' % markdown.util.INLINE_PLACEHOLDER_PREFIX[1:] + \
    r'''(?i)\b((?:[a-z][\w-]+:(?:/{1,3}|[a-z0-9%])|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\((?:[^\s()<>]+|(?:\([^\s()<>]+\)))*\))+(?:\((?:[^\s()<>]+|(?:\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'".,<>?''' + u"«»“”‘’]))"

class UrlizePattern(markdown.inlinepatterns.Pattern):
    def handleMatch(self, m):
        url = text = m.group(2)

        if not PROTOCOL_MATCH.match(url):
            url = 'http://' + url

        el = markdown.util.etree.Element("a")
        el.set('href', url)
        el.text = markdown.util.AtomicString(text)
        return el

class UrlizeExtension(markdown.Extension):
    "Urlize Extension for Python-Markdown."

    def extendMarkdown(self, md, md_globals):
        md.inlinePatterns['urlize'] = UrlizePattern(URLIZE_RE, md)

def makeExtension(configs=None):
    return UrlizeExtension(configs=configs)

########NEW FILE########
__FILENAME__ = version
VERSION = "0.8.0"

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# Day One Export documentation build configuration file, created by
# sphinx-quickstart on Wed Sep 26 19:30:45 2012.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os
on_rtd = os.environ.get('READTHEDOCS', None) == 'True'
if on_rtd:
    html_theme = 'default'
else:
    html_theme = 'nature'

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
sys.path.insert(0, os.path.abspath('..'))
# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
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
project = u'Day One Export'
copyright = u'2012, Nathan Grigg'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The default replacements for |version| and |release|, also used in various
# other places throughout the built documents.
#
import pkg_resources
try:
    release = pkg_resources.get_distribution('dayone_export').version
except ImportError:
    print 'To build the documentation, The distribution information of'
    print 'dayone_export has to be available.  Either install the package'
    print 'into your development environment or run "setup.py develop" to'
    print 'setup the metadata.  A virtualenv is recommended!'
    sys.exit(1)
version = '.'.join(release.split('.')[:2])

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
# html_theme = 'nature'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
#html_theme_path = []

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
html_title = 'Day One Export documentation'

# A shorter title for the navigation bar.  Default is the same as html_title.
html_short_title = '{0} {1} documentation'.format(project, version)

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
html_last_updated_fmt = '%b %d, %Y'

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
html_use_index = False

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
#html_show_sphinx = True

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is True.
html_show_copyright = False

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# This is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = None

# Output file base name for HTML help builder.
htmlhelp_basename = 'DayOneExportdoc'


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
  ('index', 'DayOneExport.tex', u'Day One Export Documentation',
   u'Nathan Grigg', 'manual'),
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
    ('index', 'dayoneexport', u'Day One Export Documentation',
     [u'Nathan Grigg'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'DayOneExport', u'Day One Export Documentation',
   u'Nathan Grigg', 'DayOneExport', 'One line description of project.',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'

########NEW FILE########
__FILENAME__ = test_dayone_export
import unittest
import dayone_export as doe
import dayone_export.cli
from mock import patch
import os
import jinja2
from datetime import datetime
import pytz
import locale

this_path = os.path.split(os.path.abspath(__file__))[0]
fake_journal = os.path.join(this_path, 'fake_journal')

class TestEntryObject(unittest.TestCase):
    def setUp(self):
        self.entry = doe.Entry(fake_journal + '/entries/full.doentry')
        self.entry.set_photo('foo')
        self.no_location = doe.Entry(fake_journal + '/entries/00-first.doentry')
        self.entry.set_time_zone('America/Los_Angeles')
        self.entry.set_localized_date('America/Los_Angeles')
        self.last_entry = doe.Entry(fake_journal + '/entries/zz-last.doentry')

    def test_tags(self):
        self.assertEqual(self.entry.data['Tags'], ['tag'])

    def test_set_photo(self):
        self.assertEqual(self.entry.data['Photo'], 'foo')

    def test_place_no_arguments(self):
        expected = 'Zoo, Seattle, Washington, United States'
        actual = self.entry.place()
        self.assertEqual(expected, actual)

    def test_place_int_argument(self):
        expected = 'Zoo, Seattle, Washington'
        actual = self.entry.place(3)
        self.assertEqual(expected, actual)

    def test_old_invalid_place_range_argument(self):
        self.assertRaises(TypeError, self.entry.place, 1, 3)

    def test_place_list_argument(self):
        expected = 'Seattle, United States'
        actual = self.entry.place([1, 3])
        self.assertEqual(expected, actual)

    def test_place_no_location(self):
        self.assertEqual(self.no_location.place(), "")

    def test_place_ignore_argument(self):
        expected = 'Washington'
        actual = self.entry.place([2, 3], ignore='United States')
        self.assertEqual(expected, actual)

    def test_getitem_data_key(self):
        self.assertEqual(self.entry['Photo'], 'foo')

    def test_getitem_text(self):
        expected = '2: Full entry with time zone, location, weather and a tag'
        self.assertEqual(self.entry['Text'], expected)

    def test_getitem_date(self):
        date = self.entry['Date']
        naive_date = date.replace(tzinfo = None)
        expected_date = datetime(2012, 1, 1, 16, 0)
        expected_zone = 'America/Los_Angeles'
        self.assertEqual(naive_date, expected_date)
        self.assertEqual(date.tzinfo.zone, expected_zone)

    def test_getitem_raises_keyerror(self):
        self.assertRaises(KeyError, lambda:self.entry['foo'])

    def test_getitem_flattened_dict(self):
        self.assertEqual(
                self.entry['Country'], self.entry['Location']['Country'])
        self.assertEqual(
                self.last_entry['Album'], self.last_entry['Music']['Album'])
        self.assertEqual(
                self.last_entry['Host Name'],
                self.last_entry['Creator']['Host Name'])
        self.assertEqual(
                self.last_entry['Relative Humidity'],
                self.last_entry['Weather']['Relative Humidity'])

    def test_get_keys_are_actually_keys(self):
        for key in self.entry.keys():
            self.assertTrue(key in self.entry, key)

class TestJournalParser(unittest.TestCase):
    def setUp(self):
        self.j = doe.parse_journal(fake_journal)

    def test_automatically_set_photos(self):
        expected = 'photos/00F9FA96F29043D09638DF0866EC73B2.jpg'
        actual = self.j[0]['Photo']
        self.assertEqual(expected, actual)

    def test_sort_order(self):
        j = self.j
        k = 'Creation Date'
        result = j[0][k] <= j[1][k] <= j[2][k]
        self.assertTrue(result)

    @patch('jinja2.Template.render')
    def test_dayone_export_run(self, mock_render):
        doe.dayone_export(fake_journal)
        mock_render.assert_called()

    @patch('jinja2.Template.render')
    def test_dayone_export_run_with_naive_after(self, mock_render):
        doe.dayone_export(fake_journal, after=datetime(2012, 9, 1))
        mock_render.assert_called()

    @patch('jinja2.Template.render')
    def test_dayone_export_run_with_localized_after(self, mock_render):
        after = pytz.timezone('America/New_York').localize(datetime(2012, 9, 1))
        doe.dayone_export(fake_journal, after=after)
        mock_render.assert_called()

    def test_after_filter(self):
        filtered = doe._filter_by_after_date(self.j, datetime(2012, 9, 1))
        self.assertEqual(len(filtered), 2)

    def test_tags_any_tag(self):
        filtered = doe._filter_by_tag(self.j, 'any')
        self.assertEqual(len(list(filtered)), 2)

    def test_tags_one_tag(self):
        filtered = doe._filter_by_tag(self.j, ['tag'])
        self.assertEqual(len(list(filtered)), 1)

    def test_tags_no_matches(self):
        filtered = doe._filter_by_tag(self.j, ['porcupine'])
        self.assertEqual(len(list(filtered)), 0)

    def test_exclude_nonexistent_tag(self):
        actual_size = len(self.j)
        after_exlusion = doe._exclude_tags(self.j, ['porcupine'])
        self.assertEqual(actual_size, len(list(after_exlusion)))

    def test_exclude_multiple_nonexistent_tags(self):
        actual_size = len(self.j)
        after_exlusion = doe._exclude_tags(self.j, ['porcupine', 'nosuchtag'])
        self.assertEqual(actual_size, len(list(after_exlusion)))

    def test_exclude_tag(self):
        actual_size = len(self.j)
        after_exlusion = doe._exclude_tags(self.j, ['absolutelyuniqtag22'])
        self.assertEqual(len(list(after_exlusion)), actual_size-1)

    def test_tags_and_exclude_combined(self):
        actual_size = len(self.j)
        filtered = doe._filter_by_tag(self.j, 'any')
        after_exlusion = doe._exclude_tags(filtered, ['absolutelyuniqtag22'])
        self.assertEqual(len(list(after_exlusion)), 1)

    @patch('jinja2.Template.render')
    def test_file_splitter(self, mock_render):
        gen = doe.dayone_export(fake_journal)
        self.assertEqual(len(list(gen)), 1)
        # If doing careful date comparisons, beware of timezones
        gen = doe.dayone_export(fake_journal, filename_template="%Y")
        fnames = sorted(fn for fn, _ in gen)
        self.assertEqual(fnames, ["2011", "2012", "2013"])
        gen = doe.dayone_export(fake_journal, filename_template="%Y%m%d")
        fnames = sorted(fn for fn, _ in gen)
        self.assertEqual(fnames, ["20111231", "20120101", "20131113", "20131207"])



class TestTemplateInheritance(unittest.TestCase):
    def setUp(self):
        self.patcher1 = patch('jinja2.ChoiceLoader', side_effect=lambda x:x)
        self.patcher2 = patch('jinja2.FileSystemLoader', side_effect=lambda x:x)
        self.patcher3 = patch('jinja2.PackageLoader', side_effect=lambda x:x)
        self.patcher1.start()
        self.patcher2.start()
        self.patcher3.start()
        self.dir = os.path.expanduser('~/.dayone_export')

    def tearDown(self):
        self.patcher1.stop()
        self.patcher2.stop()
        self.patcher3.stop()

    def test_explicit_template(self):
        actual = doe._determine_inheritance('a/b', 'ccc', 'ddd')
        expected = 'a', 'b'
        self.assertEqual(actual, expected)

    def test_no_template_no_dir_no_format(self):
        actual = doe._determine_inheritance(None, None, None)
        expected = [[self.dir], 'dayone_export'], 'default.html'
        self.assertEqual(actual, expected)

    def test_yes_template_no_dir_no_format(self):
        actual = doe._determine_inheritance('foo', None, None)
        expected = [['.', self.dir], 'dayone_export'], 'foo'
        self.assertEqual(actual, expected)

    def test_no_template_yes_dir_no_format(self):
        actual = doe._determine_inheritance(None, 'bar', None)
        expected = 'bar', 'default.html'
        self.assertEqual(actual, expected)

    def test_yes_template_yes_dir_no_format(self):
        actual = doe._determine_inheritance('foo', 'bar', None)
        expected = 'bar', 'foo'
        self.assertEqual(actual, expected)

    def test_no_template_no_dir_yes_format(self):
        actual = doe._determine_inheritance(None, None, 'text')
        expected = [[self.dir], 'dayone_export'], 'default.text'
        self.assertEqual(actual, expected)

    def test_yes_template_no_dir_yes_format(self):
        actual = doe._determine_inheritance('foo', None , 'text')
        expected = [['.', self.dir], 'dayone_export'], 'foo'
        self.assertEqual(actual, expected)

    def test_no_template_yes_dir_yes_format(self):
        actual = doe._determine_inheritance(None, 'bar', 'text')
        expected = 'bar', 'default.text'
        self.assertEqual(actual, expected)

    def test_yes_template_yes_dir_yes_format(self):
        actual = doe._determine_inheritance('foo', 'bar', 'text')
        expected = 'bar', 'foo'
        self.assertEqual(actual, expected)

class TestCLI(unittest.TestCase):
    def setUp(self):
        self.silencer = patch('sys.stdout')
        self.silencer.start()

    def tearDown(self):
        self.silencer.stop()

    @patch('dayone_export.cli.dayone_export', return_value="")
    def test_tag_splitter_protects_any(self, mock_doe):
        dayone_export.cli.run(['--tags', 'any', fake_journal])
        expected = 'any'
        actual = mock_doe.call_args[1]['tags']
        self.assertEqual(expected, actual)

    @patch('dayone_export.cli.dayone_export', return_value="")
    def test_tag_splitter(self, mock_doe):
        dayone_export.cli.run(['--tags', 'a, b', fake_journal])
        expected = ['a', 'b']
        actual = mock_doe.call_args[1]['tags']
        self.assertEqual(expected, actual)

    def test_invalid_package(self):
        actual = dayone_export.cli.run(['.'])
        expected = 'Not a valid Day One package'
        self.assertTrue(actual.startswith(expected), actual)

    @patch('dayone_export.jinja2.Template.render', side_effect=jinja2.TemplateNotFound('msg'))
    def test_template_not_found(self, mock_doe):
        actual = dayone_export.cli.run([fake_journal])
        expected = "Template not found"
        self.assertTrue(actual.startswith(expected), actual)


class TestMarkdown(unittest.TestCase):
    """Test the markdown formatter"""
    def setUp(self):
        self.md = doe.filters.markdown_filter()
        self.autobold = doe.filters.markdown_filter(autobold=True)
        self.nl2br = doe.filters.markdown_filter(nl2br=True)

    def test_basic_markdown(self):
        expected = '<p>This <em>is</em> a <strong>test</strong>.</p>'
        actual = self.md('This *is* a **test**.')
        self.assertEqual(expected, actual)

    def test_urlize_http(self):
        expected = '<p>xx (<a href="http://url.com">http://url.com</a>) xx</p>'
        actual = self.md('xx (http://url.com) xx')
        self.assertEqual(expected, actual)

    def test_urlize_www(self):
        expected = '<p>xx <a href="http://www.google.com">www.google.com</a> xx</p>'
        actual = self.md('xx www.google.com xx')
        self.assertEqual(expected, actual)

    def test_urlize_no_www(self):
        expected = '<p>xx <a href="http://bit.ly/blah">bit.ly/blah</a> xx</p>'
        actual = self.md('xx bit.ly/blah xx')
        self.assertEqual(expected, actual)

    def test_urlize_quotes(self):
        expected = '<p>"<a href="http://www.url.com">www.url.com</a>"</p>'
        actual = self.md('"www.url.com"')
        self.assertEqual(expected, actual)

    def test_urlize_period(self):
        expected = '<p>See <a href="http://url.com">http://url.com</a>.</p>'
        actual = self.md('See http://url.com.')
        self.assertEqual(expected, actual)

    def test_two_footnotes(self):
        """Make sure the footnote counter is working"""
        text = "Footnote[^1]\n\n[^1]: Footnote text"
        self.assertNotEqual(self.md(text), self.md(text))

    def test_hashtag_does_not_become_h1(self):
        expected = '<p>#tag and #tag</p>'
        actual = self.md('#tag and #tag')
        self.assertEqual(expected, actual)

    def test_h1_becomes_h1(self):
        expected = '<h1>tag and #tag</h1>'
        actual = self.md('# tag and #tag')
        self.assertEqual(expected, actual)

    def test_autobold(self):
        expected = '<h1>This is a title</h1>\n<p>This is the next line</p>'
        actual = self.autobold('This is a title\nThis is the next line')
        self.assertEqual(expected, actual)

    def test_autobold_doesnt_happen_on_long_line(self):
        expected = '<p>AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA</p>'
        actual = self.autobold('AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA')
        self.assertEqual(expected, actual)

    def test_nl2br(self):
        expected = '<p>a<br>\nb</p>'
        actual = self.nl2br('a\nb')
        self.assertEqual(expected, actual)

class TestLatex(unittest.TestCase):
    def test_latex_escape_backslash(self):
        actual = doe.filters.escape_tex(r'bl\ah')
        expected = r'bl\textbackslash{}ah'
        self.assertEqual(expected, actual)

    def test_latex_escape_dollar(self):
        actual = doe.filters.escape_tex(r'bl$ah')
        expected = r'bl\$ah'
        self.assertEqual(expected, actual)

    def test_latex_escape_symbols(self):
        actual = doe.filters.escape_tex(r'${}#^&~')
        expected = r'\$\{\}\#\textasciicircum{}\&\textasciitilde{}'
        self.assertEqual(expected, actual)

    def test_latex_sanity(self):
        _, actual = next(doe.dayone_export(fake_journal, format='tex'))
        expected = r'\documentclass'
        self.assertEqual(actual[:14], expected)


class TestDateFormat(unittest.TestCase):
    def setUp(self):
        locale.setlocale(locale.LC_ALL, "C")
        self.date = datetime(2014, 2, 3)

    def test_default_format(self):
        expected = 'Monday, Feb 3, 2014'
        self.assertEqual(expected, doe.filters.format(self.date))
        self.assertEqual(expected, doe.filters._strftime_portable(self.date))

    def test_format_leave_zero(self):
        expected = '2014-02-03'
        self.assertEqual(expected, doe.filters.format(self.date, '%Y-%m-%d'))
        self.assertEqual(
            expected, doe.filters._strftime_portable(self.date, '%Y-%m-%d'))

    def test_format_remove_zero(self):
        expected = '2/3/2014'
        self.assertEqual(
            expected, doe.filters.format(self.date, '%-m/%-d/%Y'))
        self.assertEqual(
            expected, doe.filters._strftime_portable(self.date, '%-m/%-d/%Y'))

########NEW FILE########
