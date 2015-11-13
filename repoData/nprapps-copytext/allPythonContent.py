__FILENAME__ = copytext
#!/usr/bin/env python

from markupsafe import Markup
from openpyxl.reader.excel import load_workbook

class CopyException(Exception):
    pass

class Error(object):
    """
    An error object that can mimic the structure of the COPY data, whether the error happens at the Copy, Sheet or Row level. Will print the error whenever it gets repr'ed. 
    """
    _error = ''

    def __init__(self, error):
        self._error = error

    def __getitem__(self, i):
        return self
    
    def __iter__(self):
        return iter([self])

    def __len__(self):
        return 1

    def __repr__(self):
        return self._error

    def __nonzero__(self):
        return False 

class Row(object):
    """
    Wraps a row of copy for error handling.
    """
    _sheet = None
    _row = []
    _columns = []
    _index = 0

    def __init__(self, sheet, row, columns, index):
        self._sheet = sheet
        self._row = row
        self._columns = columns
        self._index = index

    def __getitem__(self, i):
        """
        Allow dict-style item access by index (column id), or by column name.
        """
        if isinstance(i, int):
            if i >= len(self._row):
                return Error('COPY.%s.%i.%i [column index outside range]' % (self._sheet.name, self._index, i))

            value = self._row[i]

            return Markup(value or '')

        if i not in self._columns:
            return Error('COPY.%s.%i.%s [column does not exist in sheet]' % (self._sheet.name, self._index, i))

        value = self._row[self._columns.index(i)]

        return Markup(value or '')

    def __iter__(self):
        return iter(self._row)

    def __len__(self):
        return len(self._row)

    def __unicode__(self):
        if 'value' in self._columns:
            value = self._row[self._columns.index('value')]

            return Markup(value or '')

        return Error('COPY.%s.%s [no value column in sheet]' % (self._sheet.name, self._row[self._columns.index('key')])) 

    def __html__(self):
        return self.__unicode__()

    def __nonzero__(self):
        if 'value' in self._columns:
            val = self._row[self._columns.index('value')]

            if not val:
                return False 

            return len(val)
    
        return True

class Sheet(object):
    """
    Wrap copy text, for a single worksheet, for error handling.
    """
    name = None
    _sheet = []
    _columns = []

    def __init__(self, name, data, columns):
        self.name = name
        self._sheet = [Row(self, [row[c] for c in columns], columns, i) for i, row in enumerate(data)]
        self._columns = columns

    def __getitem__(self, i):
        """
        Allow dict-style item access by index (row id), or by row name ("key" column).
        """
        if isinstance(i, int):
            if i >= len(self._sheet):
                return Error('COPY.%s.%i [row index outside range]' % (self.name, i))

            return self._sheet[i]

        if 'key' not in self._columns:
            return Error('COPY.%s.%s [no key column in sheet]' % (self.name, i))

        for row in self._sheet:
            if row['key'] == i:
                return row 

        return Error('COPY.%s.%s [key does not exist in sheet]' % (self.name, i))

    def __iter__(self):
        return iter(self._sheet)

    def __len__(self):
        return len(self._sheet)

class Copy(object):
    """
    Wraps copy text, for multiple worksheets, for error handling.
    """
    _filename = ''
    _copy = {}

    def __init__(self, filename):
        self._filename = filename
        self.load()

    def __getitem__(self, name):
        """
        Allow dict-style item access by sheet name.
        """
        if name not in self._copy:
            return Error('COPY.%s [sheet does not exist]' % name)

        return self._copy[name]

    def load(self):
        """
        Parses the downloaded Excel file and writes it as JSON.
        """
        try:
            book = load_workbook(self._filename, data_only=True)
        except IOError:
            raise CopyException('"%s" does not exist. Have you run "fab update_copy"?' % self._filename)

        for sheet in book:
            columns = []
            rows = []

            for i, row in enumerate(sheet.rows):
                row_data = [c.internal_value for c in row]

                if i == 0:
                    columns = row_data 

                # If nothing in a row then it doesn't matter
                if all([c is None for c in row_data]):
                    continue

                rows.append(dict(zip(columns, row_data)))

            self._copy[sheet.title] = Sheet(sheet.title, rows, columns)

    def json(self):
        """
        Serialize the copy as JSON.
        """
        import json

        obj = {}    
    
        for name, sheet in self._copy.items():
            if 'key' in sheet._columns:
                obj[name] = {}

                for row in sheet:
                    obj[name][row['key']] = row['value']
            else:
                obj[name] = []
                
                for row in sheet:
                    obj[name].append(row._row)
            
        return json.dumps(obj)

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import os
import sys

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
sys.path.insert(0, os.path.abspath('..'))

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.intersphinx']
autodoc_member_order = 'bysource'

intersphinx_mapping = {
    'python': ('http://docs.python.org/2.7', None)
}

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'copytext'
copyright = u'2014, NPR'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '0.1.4'
# The full version, including alpha/beta/rc tags.
release = '0.1.4 (beta)'

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
htmlhelp_basename = 'copytextdoc'


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'copytext.tex', u'copytext Documentation',
   u'NPR', 'manual'),
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
#    ('scripts/csvcut', 'csvcut', u'csvcut Documentation',
#     [u'Christopher Groskopf'], 1),
]


########NEW FILE########
__FILENAME__ = test_copytext
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import unittest2 as unittest

from markupsafe import Markup

import copytext

class CopyTestCase(unittest.TestCase):
    """
    Test the Copy object.
    """
    def setUp(self):
        self.copy = copytext.Copy('examples/test_copy.xlsx')

    def test_sheet_by_item_name(self):
        sheet = self.copy['content']
        self.assertTrue(isinstance(sheet, copytext.Sheet))

    def test_sheet_by_prop_name(self):
        with self.assertRaises(AttributeError):
            self.copy.content

    def test_sheet_does_not_exist(self):
        error = self.copy['foo']
        self.assertTrue(isinstance(error, copytext.Error))
        self.assertEquals(error._error, 'COPY.foo [sheet does not exist]')

    def test_json(self):
        s = self.copy.json()
        data = json.loads(s)
    
        self.assertTrue('attribution' in data)
        self.assertTrue('content' in data)
        self.assertTrue('example_list' in data)

        attribution = data['attribution']

        self.assertIsInstance(attribution, dict)
        self.assertTrue('byline' in attribution)
        self.assertEqual(attribution['byline'], u'Uñicodë')

        example_list = data['example_list']

        self.assertIsInstance(example_list, list)
        self.assertIsInstance(example_list[0], list)
        self.assertEqual(example_list[0], ['term', 'definition'])

class SheetTestCase(unittest.TestCase):
    """
    Test the Sheet object.
    """
    def setUp(self):
        copy = copytext.Copy('examples/test_copy.xlsx')
        self.sheet = copy['content']

    def test_row_by_key_item_index(self):
        row = self.sheet[1]
        self.assertTrue(isinstance(row, copytext.Row))

    def test_row_by_key_item_name(self):
        row = self.sheet['header_title']
        self.assertTrue(isinstance(row, copytext.Row))

    def test_row_by_key_prop_name(self):
        with self.assertRaises(AttributeError):
            self.sheet.header_title

    def test_key_does_not_exist(self):
        error = self.sheet['foo']
        self.assertTrue(isinstance(error, copytext.Error))
        self.assertEquals(error._error, 'COPY.content.foo [key does not exist in sheet]')

    def test_column_index_outside_range(self):
        error = self.sheet[65]
        self.assertTrue(isinstance(error, copytext.Error))
        self.assertEquals(error._error, 'COPY.content.65 [row index outside range]')

class KeyValueRowTestCase(unittest.TestCase):
    """
    Test the Row object.
    """
    def setUp(self):
        copy = copytext.Copy('examples/test_copy.xlsx')
        self.sheet = copy['content']
        self.row = self.sheet['header_title']

    def test_cell_by_value_unicode(self):
        cell = unicode(self.row)
        self.assertTrue(isinstance(cell, Markup))
        self.assertEqual(cell, 'Across-The-Top Header')

    def test_null_cell_value(self):
        row = self.sheet['nothing']
        self.assertIs(True if row else False, False)
        self.assertIs(True if row[1] else False, False)

    def test_cell_by_index(self):
        cell = self.row[1]
        self.assertTrue(isinstance(cell, Markup))
        self.assertEqual(cell, 'Across-The-Top Header')

    def test_cell_by_item_name(self):
        cell = self.row['value']
        self.assertTrue(isinstance(cell, Markup))
        self.assertEqual(cell, 'Across-The-Top Header')

    def test_cell_by_prop_name(self):
        with self.assertRaises(AttributeError):
            self.row.value

    def test_column_does_not_exist(self):
        error = self.row['foo']
        self.assertTrue(isinstance(error, copytext.Error))
        self.assertEquals(error._error, 'COPY.content.1.foo [column does not exist in sheet]')

    def test_column_index_outside_range(self):
        error = self.row[2]
        self.assertTrue(isinstance(error, copytext.Error))
        self.assertEquals(error._error, 'COPY.content.1.2 [column index outside range]')

    def test_row_truthiness(self):
        self.assertIs(True if self.sheet['foo'] else False, False)
        self.assertIs(True if self.sheet['header_title'] else False, True)

class ListRowTestCase(unittest.TestCase):
    def setUp(self):
        copy = copytext.Copy('examples/test_copy.xlsx')
        self.sheet = copy['example_list']

    def test_iteration(self):
        i = iter(self.sheet)
        row = i.next()

        self.assertEqual(row[0], 'term')
        self.assertEqual(row[1], 'definition')

        row = i.next()

        self.assertEqual(row[0], 'jabberwocky')
        self.assertEqual(row[1], 'Invented or meaningless language; nonsense.')

    def test_row_truthiness(self):
        row = self.sheet[0]

        self.assertIs(True if row else False, True)
        
        row = self.sheet[100]
        
        self.assertIs(True if row else False, False)

class MarkupTestCase(unittest.TestCase):
    """
    Test strings get Markup'd.
    """
    def setUp(self):
        copy = copytext.Copy('examples/test_copy.xlsx')
        self.sheet = copy['content']

    def test_markup_row(self):
        row = self.sheet['footer_title']
        
        self.assertTrue(isinstance(row.__html__(), Markup))
        self.assertEqual(row.__html__(), '<strong>This content goes to 12</strong>')

    def test_markup_cell(self):
        cell = unicode(self.sheet['footer_title'])

        self.assertTrue(isinstance(cell, Markup))
        self.assertEqual(cell, '<strong>This content goes to 12</strong>')

class CellTypeTestCase(unittest.TestCase):
    """
    Test various cell "types".

    NB: These tests are fake. They only work if the input data is formatted as text.

    Things which are actually non-string don't work and can't be supported.
    """
    def setUp(self):
        copy = copytext.Copy('examples/test_copy.xlsx')
        self.sheet = copy['attribution']

    def test_date(self):
        row = self.sheet['pubdate']
        val = unicode(row)

        self.assertEquals(val, '1/22/2013')

    def test_time(self):
        row = self.sheet['pubtime']
        val = unicode(row)

        self.assertEqual(val, '3:37 AM')

class ErrorTestCase(unittest.TestCase):
    """
    Test for Error object.
    """
    def setUp(self):
        self.error = copytext.Error('foobar')

    def test_getitem(self):
        child_error = self.error['bing']
        self.assertIs(child_error, self.error)
        self.assertEqual(str(child_error), 'foobar')

    def test_getitem_index(self):
        child_error = self.error[1]
        self.assertIs(child_error, self.error)
        self.assertEqual(str(child_error), 'foobar')

    def test_iter(self):
        i = iter(self.error)
        child_error = i.next()
        self.assertIs(child_error, self.error)
        self.assertEqual(str(child_error), 'foobar')

        with self.assertRaises(StopIteration):
            i.next()

    def test_len(self):
        self.assertEqual(len(self.error), 1)

    def test_unicode(self):
        self.assertEqual(str(self.error), 'foobar')

    def test_falsey(self):
        self.assertIs(True if self.error else False, False)

########NEW FILE########
