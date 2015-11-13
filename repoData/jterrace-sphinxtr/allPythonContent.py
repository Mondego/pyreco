__FILENAME__ = conf
import sys, os

# directory relative to this conf file
CURDIR = os.path.abspath(os.path.dirname(__file__))
# add custom extensions directory to python path
sys.path.append(os.path.join(os.path.abspath(os.path.dirname(__file__)), 'extensions'))

# import the custom html and latex builders/translators/writers
import html_mods
import latex_mods

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# import order is important here
extensions = [
              'fix_equation_ref',
              'sphinx.ext.mathjax',
              'sphinx.ext.ifconfig',
              'subfig',
              'numfig',
              'numsec',
              'natbib',
              'figtable',
              'singlehtml_toc',
              'singletext',
              ]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
source_encoding = 'utf-8-sig'

# General information about the project.
project = u'The Sphinx Thesis Resource (sphinxtr)'
author = u'Jeff Terrace'
copyright = u'by %s, 2012.' % author
version = '0.1'
release = '0.1'

# Turns on numbered figures for HTML output
number_figures = True

# configures bibliography
# see http://wnielson.bitbucket.org/projects/sphinx-natbib/
natbib = {
    'file': 'refs.bib',
    'brackets': '[]',
    'separator': ',',
    'style': 'numbers',
    'sort': True,
}

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = [
                    '_build',
                    'tex',
                    'epilog.rst',
                    'README.rst',
                    ]

# The master toctree document.
# Ideally, we wouldn't have to do this, but sphinx seems to have trouble with
# directives inside only directives
if tags.has('latex'):
    master_doc = 'index_tex'
    exclude_patterns.append('index.rst')
else:
    master_doc = 'index'
    exclude_patterns.append('index_tex.rst')

# A string of reStructuredText that will be included at the end of
# every source file that is read.
rst_epilog = open(os.path.join(CURDIR, 'epilog.rst'),'r').read().decode('utf8')

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'


# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = 'sphinxdoc'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
#html_theme_path = []

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
html_title = "%s" % project

# A shorter title for the navigation bar.  Default is the same as html_title.
html_short_title = "Someone's PhD Thesis"

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
html_static_path = ['static']

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
#html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
#html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
template_files = ['localtoc.html', 'relations.html', 'sourcelink.html']
if not tags.has('singlehtml'):
    # only include search box for regular html, not single page html
    template_files.append('searchbox.html')
html_sidebars = {
   '**': template_files,
}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If false, no module index is generated.
html_domain_indices = False

# If false, no index is generated.
html_use_index = False

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

# supresses the last dot in section numbers
# changes "1. Introduction" -> "1 Introduction"
# default string is ". "
html_secnumber_suffix = " "

# Output file base name for HTML help builder.
htmlhelp_basename = 'htmlhelpoutput'

# location of mathjax script if you don't want to use CDN
# mathjax_path = 'MathJax/MathJax.js?config=TeX-AMS-MML_HTMLorMML'




# -- Options for LaTeX output --------------------------------------------------

ADDITIONAL_PREAMBLE = """
\input{preamble._tex}
\usepackage{sphinx}
"""

ADDITIONAL_FOOTER = """
\input{footer._tex}
"""

latex_elements = {
    # The paper size ('letterpaper' or 'a4paper').
    'papersize': 'letterpaper',
    
    # * gets passed to \documentclass
    # * default options are single sided, double spaced
    #   you can change them with these options:
    #   * twoside
    #   * singlespace
    # * you might want to omit the list of tables (lot)
    #   if you use figtable without the :nofig: option
    'classoptions': ',english,lof,lot',
    
    # The font size ('10pt', '11pt' or '12pt').
    'pointsize': '12pt',
    
    # Additional stuff for the LaTeX preamble.
    'preamble': ADDITIONAL_PREAMBLE,
    
    # Additional footer
    'footer': ADDITIONAL_FOOTER,
    
    # disable font inclusion
    'fontpkg': '',
    'fontenc': '',
    
    # disable fancychp
    'fncychap': '',
    
    # get rid of the sphinx wrapper class file
    'wrapperclass': 'puthesis',
    
    # override maketitle
    'maketitle': '\makefrontmatter',
    'tableofcontents': '',
    
    # disable index printing
    'printindex': '',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
    ('index_tex',
     'thesis.tex',
     project,
     author,
     'manual',
     True),
]

latex_docclass = {
    'manual': 'puthesis',
}

latex_additional_files = [
    'tex/puthesis.cls',
    'tex/preamble._tex',
    'tex/footer._tex',
    'tex/sphinx.sty',
    'tex/Makefile',
    'tex/refstyle.bst',
    'refs.bib',
    'tex/ccicons.sty',
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
latex_use_parts = False

# If true, show page references after internal links.
#latex_show_pagerefs = False

# If true, show URL addresses after external links.
#latex_show_urls = False

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
latex_domain_indices = False

########NEW FILE########
__FILENAME__ = backports
import collections

Set = set

try:
    from collections import OrderedDict
except ImportError:
    class OrderedDict(dict):
        'Dictionary that remembers insertion order'
        # An inherited dict maps keys to values.
        # The inherited dict provides __getitem__, __len__, __contains__, and get.
        # The remaining methods are order-aware.
        # Big-O running times for all methods are the same as for regular dictionaries.
    
        # The internal self.__map dictionary maps keys to links in a doubly linked list.
        # The circular doubly linked list starts and ends with a sentinel element.
        # The sentinel element never gets deleted (this simplifies the algorithm).
        # Each link is stored as a list of length three:  [PREV, NEXT, KEY].
    
        def __init__(self, *args, **kwds):
            '''Initialize an ordered dictionary.  Signature is the same as for
            regular dictionaries, but keyword arguments are not recommended
            because their insertion order is arbitrary.
    
            '''
            if len(args) > 1:
                raise TypeError('expected at most 1 arguments, got %d' % len(args))
            try:
                self.__root
            except AttributeError:
                self.__root = root = []                     # sentinel node
                root[:] = [root, root, None]
                self.__map = {}
            self.__update(*args, **kwds)
    
        def __setitem__(self, key, value, dict_setitem=dict.__setitem__):
            'od.__setitem__(i, y) <==> od[i]=y'
            # Setting a new item creates a new link which goes at the end of the linked
            # list, and the inherited dictionary is updated with the new key/value pair.
            if key not in self:
                root = self.__root
                last = root[0]
                last[1] = root[0] = self.__map[key] = [last, root, key]
            dict_setitem(self, key, value)
    
        def __delitem__(self, key, dict_delitem=dict.__delitem__):
            'od.__delitem__(y) <==> del od[y]'
            # Deleting an existing item uses self.__map to find the link which is
            # then removed by updating the links in the predecessor and successor nodes.
            dict_delitem(self, key)
            link_prev, link_next, key = self.__map.pop(key)
            link_prev[1] = link_next
            link_next[0] = link_prev
    
        def __iter__(self):
            'od.__iter__() <==> iter(od)'
            root = self.__root
            curr = root[1]
            while curr is not root:
                yield curr[2]
                curr = curr[1]
    
        def __reversed__(self):
            'od.__reversed__() <==> reversed(od)'
            root = self.__root
            curr = root[0]
            while curr is not root:
                yield curr[2]
                curr = curr[0]
    
        def clear(self):
            'od.clear() -> None.  Remove all items from od.'
            try:
                for node in self.__map.itervalues():
                    del node[:]
                root = self.__root
                root[:] = [root, root, None]
                self.__map.clear()
            except AttributeError:
                pass
            dict.clear(self)
    
        def popitem(self, last=True):
            '''od.popitem() -> (k, v), return and remove a (key, value) pair.
            Pairs are returned in LIFO order if last is true or FIFO order if false.
    
            '''
            if not self:
                raise KeyError('dictionary is empty')
            root = self.__root
            if last:
                link = root[0]
                link_prev = link[0]
                link_prev[1] = root
                root[0] = link_prev
            else:
                link = root[1]
                link_next = link[1]
                root[1] = link_next
                link_next[0] = root
            key = link[2]
            del self.__map[key]
            value = dict.pop(self, key)
            return key, value
    
        # -- the following methods do not depend on the internal structure --
    
        def keys(self):
            'od.keys() -> list of keys in od'
            return list(self)
    
        def values(self):
            'od.values() -> list of values in od'
            return [self[key] for key in self]
    
        def items(self):
            'od.items() -> list of (key, value) pairs in od'
            return [(key, self[key]) for key in self]
    
        def iterkeys(self):
            'od.iterkeys() -> an iterator over the keys in od'
            return iter(self)
    
        def itervalues(self):
            'od.itervalues -> an iterator over the values in od'
            for k in self:
                yield self[k]
    
        def iteritems(self):
            'od.iteritems -> an iterator over the (key, value) items in od'
            for k in self:
                yield (k, self[k])
    
        def update(*args, **kwds):
            '''od.update(E, **F) -> None.  Update od from dict/iterable E and F.
    
            If E is a dict instance, does:           for k in E: od[k] = E[k]
            If E has a .keys() method, does:         for k in E.keys(): od[k] = E[k]
            Or if E is an iterable of items, does:   for k, v in E: od[k] = v
            In either case, this is followed by:     for k, v in F.items(): od[k] = v
    
            '''
            if len(args) > 2:
                raise TypeError('update() takes at most 2 positional '
                                'arguments (%d given)' % (len(args),))
            elif not args:
                raise TypeError('update() takes at least 1 argument (0 given)')
            self = args[0]
            # Make progressively weaker assumptions about "other"
            other = ()
            if len(args) == 2:
                other = args[1]
            if isinstance(other, dict):
                for key in other:
                    self[key] = other[key]
            elif hasattr(other, 'keys'):
                for key in other.keys():
                    self[key] = other[key]
            else:
                for key, value in other:
                    self[key] = value
            for key, value in kwds.items():
                self[key] = value
    
        __update = update  # let subclasses override update without breaking __init__
    
        __marker = object()
    
        def pop(self, key, default=__marker):
            '''od.pop(k[,d]) -> v, remove specified key and return the corresponding value.
            If key is not found, d is returned if given, otherwise KeyError is raised.
    
            '''
            if key in self:
                result = self[key]
                del self[key]
                return result
            if default is self.__marker:
                raise KeyError(key)
            return default
    
        def setdefault(self, key, default=None):
            'od.setdefault(k[,d]) -> od.get(k,d), also set od[k]=d if k not in od'
            if key in self:
                return self[key]
            self[key] = default
            return default
    
        def __repr__(self, _repr_running={}):
            'od.__repr__() <==> repr(od)'
            call_key = id(self), _get_ident()
            if call_key in _repr_running:
                return '...'
            _repr_running[call_key] = 1
            try:
                if not self:
                    return '%s()' % (self.__class__.__name__,)
                return '%s(%r)' % (self.__class__.__name__, self.items())
            finally:
                del _repr_running[call_key]
    
        def __reduce__(self):
            'Return state information for pickling'
            items = [[k, self[k]] for k in self]
            inst_dict = vars(self).copy()
            for k in vars(OrderedDict()):
                inst_dict.pop(k, None)
            if inst_dict:
                return (self.__class__, (items,), inst_dict)
            return self.__class__, (items,)
    
        def copy(self):
            'od.copy() -> a shallow copy of od'
            return self.__class__(self)
    
        @classmethod
        def fromkeys(cls, iterable, value=None):
            '''OD.fromkeys(S[, v]) -> New ordered dictionary with keys from S
            and values equal to v (which defaults to None).
    
            '''
            d = cls()
            for key in iterable:
                d[key] = value
            return d
    
        def __eq__(self, other):
            '''od.__eq__(y) <==> od==y.  Comparison to another OD is order-sensitive
            while comparison to a regular mapping is order-insensitive.
    
            '''
            if isinstance(other, OrderedDict):
                return len(self)==len(other) and self.items() == other.items()
            return dict.__eq__(self, other)
    
        def __ne__(self, other):
            return not self == other
    
        # -- the following methods are only used in Python 2.7 --
    
        def viewkeys(self):
            "od.viewkeys() -> a set-like object providing a view on od's keys"
            return KeysView(self)
    
        def viewvalues(self):
            "od.viewvalues() -> an object providing a view on od's values"
            return ValuesView(self)
    
        def viewitems(self):
            "od.viewitems() -> a set-like object providing a view on od's items"
            return ItemsView(self)

KEY, PREV, NEXT = range(3)

class OrderedSet(collections.MutableSet):
  """
  From: http://code.activestate.com/recipes/576694/
  """
  def __init__(self, iterable=None):
    self.end = end = [] 
    end += [None, end, end]         # sentinel node for doubly linked list
    self.map = {}                   # key --> [key, prev, next]
    if iterable is not None:
      self |= iterable

  def __len__(self):
    return len(self.map)

  def __contains__(self, key):
    return key in self.map

  def add(self, key):
    if key not in self.map:
      end = self.end
      curr = end[PREV]
      curr[NEXT] = end[PREV] = self.map[key] = [key, curr, end]

  def discard(self, key):
    if key in self.map:        
      key, prev, next = self.map.pop(key)
      prev[NEXT] = next
      next[PREV] = prev

  def __iter__(self):
    end = self.end
    curr = end[NEXT]
    while curr is not end:
      yield curr[KEY]
      curr = curr[NEXT]
  
  def __reversed__(self):
    end = self.end
    curr = end[PREV]
    while curr is not end:
      yield curr[KEY]
      curr = curr[PREV]
  
  def pop(self, last=True):
    if not self:
      raise KeyError('set is empty')
    key = next(reversed(self)) if last else next(iter(self))
    self.discard(key)
    return key

  def __repr__(self):
    if not self:
      return '%s()' % (self.__class__.__name__,)
    return '%s(%r)' % (self.__class__.__name__, list(self))

  def __eq__(self, other):
    if isinstance(other, OrderedSet):
      return len(self) == len(other) and list(self) == list(other)
    return set(self) == set(other)

  def __del__(self):
    self.clear()                    # remove circular references

########NEW FILE########
__FILENAME__ = figtable
"""
Adds a new directive called 'figtable' that creates a figure
around a table.
"""

from docutils import nodes
import docutils.parsers.rst.directives as directives
from sphinx.util.compat import Directive
from sphinx import addnodes

class figtable(nodes.General, nodes.Element):
    pass

def visit_figtable_node(self, node):
    pass

def depart_figtable_node(self, node):
    pass

def visit_figtable_tex(self, node):
    if node['nofig']:
        self.body.append('\n\n\\begin{table}\n\\capstart\n\\begin{center}\n')
    else:
        self.body.append('\n\n\\begin{figure}[tbp]\n\\capstart\n\\begin{center}\n')

def depart_figtable_tex(self, node):
    if node['nofig']:
        self.body.append('\n\\end{center}\n\\end{table}\n')
    else:
        self.body.append('\n\\end{center}\n\\end{figure}\n')

def visit_figtable_html(self, node):
    atts = {'class': 'figure align-center'}
    self.body.append(self.starttag(node, 'div', **atts) + '<center>')

def depart_figtable_html(self, node):
    self.body.append('</center></div>')

class FigTableDirective(Directive):
    
    has_content = True
    optional_arguments = 5
    final_argument_whitespace = True

    option_spec = {'label': directives.uri,
                   'spec': directives.unchanged,
                   'caption': directives.unchanged,
                   'alt': directives.unchanged,
                   'nofig': directives.flag}

    def run(self):
        label = self.options.get('label', None)
        spec = self.options.get('spec', None)
        caption = self.options.get('caption', None)
        alt = self.options.get('alt', None)
        nofig = 'nofig' in self.options
        
        figtable_node = figtable('', ids=[label] if label is not None else [])
        figtable_node['nofig'] = nofig
        
        if spec is not None:
            table_spec_node = addnodes.tabular_col_spec()
            table_spec_node['spec'] = spec
            figtable_node.append(table_spec_node)
        
        node = nodes.Element()
        self.state.nested_parse(self.content, self.content_offset, node)
        tablenode = node[0]
        if alt is not None:
            tablenode['alt'] = alt
        figtable_node.append(tablenode)
        
        if caption is not None:
            caption_node = nodes.caption('', '', nodes.Text(caption))
            figtable_node.append(caption_node)
        
        if label is not None:
            targetnode = nodes.target('', '', ids=[label])
            figtable_node.append(targetnode)
        
        return [figtable_node]

def setup(app):
    app.add_node(figtable,
                 html=(visit_figtable_html, depart_figtable_html),
                 singlehtml=(visit_figtable_html, depart_figtable_html),
                 latex=(visit_figtable_tex, depart_figtable_tex),
                 text=(visit_figtable_node, depart_figtable_node))

    app.add_directive('figtable', FigTableDirective)

########NEW FILE########
__FILENAME__ = fix_equation_ref
"""
Fixes equation references from Sphinx math domain
from Equation (1) to Equation 1, which is what they
should be. Must be before sphinx.ext.math* in
extensions list.
"""

from docutils import nodes
import sphinx.ext.mathbase
from sphinx.ext.mathbase import displaymath, eqref

def number_equations(app, doctree, docname):
    num = 0
    numbers = {}
    for node in doctree.traverse(displaymath):
        if node['label'] is not None:
            num += 1
            node['number'] = num
            numbers[node['label']] = num
        else:
            node['number'] = None
    for node in doctree.traverse(eqref):
        if node['target'] not in numbers:
            continue
        num = '%d' % numbers[node['target']]
        node[0] = nodes.Text(num, num)

sphinx.ext.mathbase.number_equations = number_equations

def setup(app):
    pass

########NEW FILE########
__FILENAME__ = html_mods
import re
from docutils import nodes
import sphinx.writers.html

BaseTranslator = sphinx.writers.html.SmartyPantsHTMLTranslator
class CustomHTMLTranslator(BaseTranslator):
    def visit_tabular_col_spec(self, node):
        self.table_spec = re.split(r'[\s\|]+', node['spec'])
        raise nodes.SkipNode
    
    def bulk_text_processor(self, text):
        if '~' in text:
            text = text.replace('~', '&nbsp;')
        return text
    
    def visit_entry(self, node):
        atts = {'class': []}
        if isinstance(node.parent.parent, nodes.thead):
            atts['class'].append('head')
        if node.parent.parent.parent.stubs[node.parent.column]:
            # "stubs" list is an attribute of the tgroup element
            atts['class'].append('stub')
        if atts['class']:
            tagname = 'th'
            atts['class'] = ' '.join(atts['class'])
        else:
            tagname = 'td'
            del atts['class']
        table_spec = getattr(self, 'table_spec', None)
        if (tagname == 'td' or tagname == 'th') and table_spec is not None:
            if len(table_spec) > node.parent.column:
                colspec = table_spec[node.parent.column]
                
                horiz_align = ''
                vert_align = ''
                
                if 'raggedright' in colspec or colspec == 'l':
                    horiz_align = ' align-left'
                elif 'raggedleft' in colspec or colspec == 'r':
                    horiz_align = ' align-right'
                elif 'center' in colspec or colspec == 'c':
                    horiz_align = ' align-center'
                
                if 'p{' in colspec:
                    vert_align = ' align-top'
                elif 'm{' in colspec:
                    vert_align = ' align-middle'
                elif 'b{' in colspec:
                    vert_align = ' align-bottom'
                
                align_type = {'l': 'left',
                              'r': 'right',
                              'c': 'center'}
                atts['class'] = (atts.get('class', '') + horiz_align + vert_align)
        node.parent.column += 1
        if 'morerows' in node:
            atts['rowspan'] = node['morerows'] + 1
        if 'morecols' in node:
            atts['colspan'] = node['morecols'] + 1
            node.parent.column += node['morecols']
        self.body.append(self.starttag(node, tagname, '', **atts))
        self.context.append('</%s>\n' % tagname.lower())
        if len(node) == 0:              # empty cell
            self.body.append('&nbsp;')
        self.set_first_last(node)

sphinx.writers.html.SmartyPantsHTMLTranslator = CustomHTMLTranslator

########NEW FILE########
__FILENAME__ = latex_mods
# -*- coding: utf-8 -*-
import os

from docutils.io import FileOutput
from docutils.frontend import OptionParser
from docutils import nodes

import sphinx.builders.latex
from sphinx.util.smartypants import educate_quotes_latex
from sphinx.writers.latex import LaTeXWriter
from sphinx.util.console import bold
from sphinx.util.osutil import copyfile
from sphinx.util.texescape import tex_escape_map
import sphinx.writers.latex

# remove usepackage for sphinx here, we add it later in the preamble in conf.py
sphinx.writers.latex.HEADER = sphinx.writers.latex.HEADER.replace('\usepackage{sphinx}', '')

BaseTranslator = sphinx.writers.latex.LaTeXTranslator

class DocTranslator(BaseTranslator):

    def visit_caption(self, node):
        caption_idx = node.parent.index(node)
        if caption_idx > 0:
            look_node = node.parent.children[caption_idx - 1]
        else:
            look_node = node.parent

        short_caption = unicode(look_node.get('alt', '')).translate(tex_escape_map)
        if short_caption != "":
            short_caption = '[%s]' % short_caption

        self.in_caption += 1
        self.body.append('\\caption%s{' % short_caption)
    def depart_caption(self, node):
        self.body.append('}')
        self.in_caption -= 1

    def visit_Text(self, node):
        if self.verbatim is not None:
            self.verbatim += node.astext()
        else:
            text = self.encode(node.astext())
            if '\\textasciitilde{}' in text:
                text = text.replace('\\textasciitilde{}', '~')
            if not self.no_contractions:
                text = educate_quotes_latex(text)
            self.body.append(text)

    def visit_table(self, node):
        if self.table:
            raise UnsupportedError(
                '%s:%s: nested tables are not yet implemented.' %
                (self.curfilestack[-1], node.line or ''))

        self.table = sphinx.writers.latex.Table()
        self.table.longtable = False
        self.tablebody = []
        self.tableheaders = []

        # Redirect body output until table is finished.
        self._body = self.body
        self.body = self.tablebody

    def depart_table(self, node):
        self.body = self._body
        colspec = self.table.colspec or ''

        if 'p{' in colspec or 'm{' in colspec or 'b{' in colspec:
            self.body.append('\n\\bodyspacing\n')

        self.body.append('\n\\begin{tabular}')

        if colspec:
            self.body.append(colspec)
        else:
            self.body.append('{|' + ('l|' * self.table.colcount) + '}')

        self.body.append('\n')

        if self.table.caption is not None:
            for id in self.next_table_ids:
                self.body.append(self.hypertarget(id, anchor=False))
            self.next_table_ids.clear()

        self.body.append('\\toprule\n')

        self.body.extend(self.tableheaders)

        self.body.append('\\midrule\n')

        self.body.extend(self.tablebody)

        self.body.append('\\bottomrule\n')

        self.body.append('\n\\end{tabular}\n')

        self.table = None
        self.tablebody = None

    def depart_row(self, node):
        if self.previous_spanning_row == 1:
            self.previous_spanning_row = 0
            self.body.append('\\\\\n')
        else:
            self.body.append('\\\\\n')
        self.table.rowcount += 1

    def depart_literal_block(self, node):
        code = self.verbatim.rstrip('\n')
        lang = self.hlsettingstack[-1][0]
        linenos = code.count('\n') >= self.hlsettingstack[-1][1] - 1
        highlight_args = node.get('highlight_args', {})
        if 'language' in node:
            # code-block directives
            lang = node['language']
            highlight_args['force'] = True
        if 'linenos' in node:
            linenos = node['linenos']
        def warner(msg):
            self.builder.warn(msg, (self.curfilestack[-1], node.line))
        hlcode = self.highlighter.highlight_block(code, lang, warn=warner,
                linenos=linenos, **highlight_args)
        hlcode = hlcode.replace('\$', '$')
        hlcode = hlcode.replace('\%', '%')
        # workaround for Unicode issue
        hlcode = hlcode.replace(u'€', u'@texteuro[]')
        # must use original Verbatim environment and "tabular" environment
        if self.table:
            hlcode = hlcode.replace('\\begin{Verbatim}',
                                    '\\begin{OriginalVerbatim}')
            self.table.has_problematic = True
            self.table.has_verbatim = True
        # get consistent trailer
        hlcode = hlcode.rstrip()[:-14] # strip \end{Verbatim}
        hlcode = hlcode.rstrip() + '\n'
        hlcode = '\n' + hlcode + '\\end{%sVerbatim}\n' % (self.table and 'Original' or '')
        hlcode = hlcode.replace('Verbatim', 'lstlisting')
        begin_bracket = hlcode.find('[')
        end_bracket = hlcode.find(']')
        hlcode = hlcode[:begin_bracket] + '[]' + hlcode[end_bracket+1:]
        self.body.append(hlcode)
        self.verbatim = None

    def visit_figure(self, node):
        ids = ''
        for id in self.next_figure_ids:
            ids += self.hypertarget(id, anchor=False)
        self.next_figure_ids.clear()
        if 'width' in node and node.get('align', '') in ('left', 'right'):
            self.body.append('\\begin{wrapfigure}{%s}{%s}\n\\centering' %
                             (node['align'] == 'right' and 'r' or 'l',
                              node['width']))
            self.context.append(ids + '\\end{wrapfigure}\n')
        else:
            if (not 'align' in node.attributes or
                node.attributes['align'] == 'center'):
                # centering does not add vertical space like center.
                align = '\n\\centering'
                align_end = ''
            else:
                # TODO non vertical space for other alignments.
                align = '\\begin{flush%s}' % node.attributes['align']
                align_end = '\\end{flush%s}' % node.attributes['align']
            self.body.append('\\begin{figure}[tbp]%s\n' % align)
            if any(isinstance(child, nodes.caption) for child in node):
                self.body.append('\\capstart\n')
            self.context.append(ids + align_end + '\\end{figure}\n')

sphinx.writers.latex.LaTeXTranslator = DocTranslator

class CustomLaTeXTranslator(DocTranslator):
    def astext(self):
            return (#HEADER % self.elements +
                    #self.highlighter.get_stylesheet() +
                    u''.join(self.body)
                    #'\n' + self.elements['footer'] + '\n' +
                    #self.generate_indices() +
                    #FOOTER % self.elements
                    )

    def unknown_departure(self, node):
        if node.tagname == 'only':
            return
        return super(CustomLaTeXTranslator, self).unknown_departure(node)

    def unknown_visit(self, node):
        if node.tagname == 'only':
            return
        return super(CustomLaTeXTranslator, self).unknown_visit(node)

class CustomLaTeXBuilder(sphinx.builders.latex.LaTeXBuilder):

    def write(self, *ignored):
        super(CustomLaTeXBuilder, self).write(*ignored)

        backup_translator = sphinx.writers.latex.LaTeXTranslator
        sphinx.writers.latex.LaTeXTranslator = CustomLaTeXTranslator
        backup_doc = sphinx.writers.latex.BEGIN_DOC
        sphinx.writers.latex.BEGIN_DOC = ''

        # output these as include files
        for docname in ['abstract', 'dedication', 'acknowledgements']:
            destination = FileOutput(
                    destination_path=os.path.join(self.outdir, '%s.inc' % docname),
                    encoding='utf-8')

            docwriter = LaTeXWriter(self)
            doctree = self.env.get_doctree(docname)

            docsettings = OptionParser(
                defaults=self.env.settings,
                components=(docwriter,)).get_default_values()
            doctree.settings = docsettings
            docwriter.write(doctree, destination)

        sphinx.writers.latex.LaTeXTranslator = backup_translator
        sphinx.writers.latex.BEGIN_DOC = backup_doc

    def finish(self, *args, **kwargs):
        super(CustomLaTeXBuilder, self).finish(*args, **kwargs)
        # copy additional files again *after* tex support files so we can override them!
        if self.config.latex_additional_files:
            self.info(bold('copying additional files again...'), nonl=1)
            for filename in self.config.latex_additional_files:
                self.info(' '+filename, nonl=1)
                copyfile(os.path.join(self.confdir, filename),
                         os.path.join(self.outdir, os.path.basename(filename)))
            self.info()

# monkey patch the shit out of it
sphinx.builders.latex.LaTeXBuilder = CustomLaTeXBuilder

########NEW FILE########
__FILENAME__ = latex_codec
"""latex.py

Character translation utilities for LaTeX-formatted text.

Usage:
 - unicode(string,'latex')
 - ustring.decode('latex')
are both available just by letting "import latex" find this file.
 - unicode(string,'latex+latin1')
 - ustring.decode('latex+latin1')
where latin1 can be replaced by any other known encoding, also
become available by calling latex.register().

We also make public a dictionary latex_equivalents,
mapping ord(unicode char) to LaTeX code.

D. Eppstein, October 2003.
"""

from __future__ import generators
import codecs
import re
from backports import Set

def register():
    """Enable encodings of the form 'latex+x' where x describes another encoding.
    Unicode characters are translated to or from x when possible, otherwise
    expanded to latex.
    """
    codecs.register(_registry)

def getregentry():
    """Encodings module API."""
    return _registry('latex')

def _registry(encoding):
    if encoding == 'latex':
        encoding = None
    elif encoding.startswith('latex+'):
        encoding = encoding[6:]
    else:
        return None
        
    class Codec(codecs.Codec):
        def encode(self,input,errors='strict'):
            """Convert unicode string to latex."""
            output = []
            for c in input:
                if encoding:
                    try:
                        output.append(c.encode(encoding))
                        continue
                    except:
                        pass
                if ord(c) in latex_equivalents:
                    output.append(latex_equivalents[ord(c)])
                else:
                    output += ['{\\char', str(ord(c)), '}']
            return ''.join(output), len(input)
            
        def decode(self,input,errors='strict'):
            """Convert latex source string to unicode."""
            if encoding:
                input = unicode(input,encoding,errors)

            # Note: we may get buffer objects here.
            # It is not permussable to call join on buffer objects
            # but we can make them joinable by calling unicode.
            # This should always be safe since we are supposed
            # to be producing unicode output anyway.
            x = map(unicode,_unlatex(input))
            return u''.join(x), len(input)
    
    class StreamWriter(Codec,codecs.StreamWriter):
        pass
            
    class StreamReader(Codec,codecs.StreamReader):
        pass

    return (Codec().encode,Codec().decode,StreamReader,StreamWriter)

def _tokenize(tex):
    """Convert latex source into sequence of single-token substrings."""
    start = 0
    try:
        # skip quickly across boring stuff
        pos = _stoppers.finditer(tex).next().span()[0]
    except StopIteration:
        yield tex
        return

    while 1:
        if pos > start:
            yield tex[start:pos]
            if tex[start] == '\\' and not (tex[pos-1].isdigit() and tex[start+1].isalpha()):
                while pos < len(tex) and tex[pos].isspace(): # skip blanks after csname
                    pos += 1

        while pos < len(tex) and tex[pos] in _ignore:
            pos += 1    # flush control characters
        if pos >= len(tex):
            return
        start = pos
        if tex[pos:pos+2] in {'$$':None, '/~':None}:    # protect ~ in urls
            pos += 2
        elif tex[pos].isdigit():
            while pos < len(tex) and tex[pos].isdigit():
                pos += 1
        elif tex[pos] == '-':
            while pos < len(tex) and tex[pos] == '-':
                pos += 1
        elif tex[pos] != '\\' or pos == len(tex) - 1:
            pos += 1
        elif not tex[pos+1].isalpha():
            pos += 2
        else:
            pos += 1
            while pos < len(tex) and tex[pos].isalpha():
                pos += 1
            if tex[start:pos] == '\\char' or tex[start:pos] == '\\accent':
                while pos < len(tex) and tex[pos].isdigit():
                    pos += 1

class _unlatex:
    """Convert tokenized tex into sequence of unicode strings.  Helper for decode()."""

    def __iter__(self):
        """Turn self into an iterator.  It already is one, nothing to do."""
        return self

    def __init__(self,tex):
        """Create a new token converter from a string."""
        self.tex = tuple(_tokenize(tex))  # turn tokens into indexable list
        self.pos = 0                    # index of first unprocessed token 
        self.lastoutput = 'x'           # lastoutput must always be nonempty string
    
    def __getitem__(self,n):
        """Return token at offset n from current pos."""
        p = self.pos + n
        t = self.tex
        return p < len(t) and t[p] or None

    def next(self):
        """Find and return another piece of converted output."""
        if self.pos >= len(self.tex):
            raise StopIteration
        nextoutput = self.chunk()
        if self.lastoutput[0] == '\\' and self.lastoutput[-1].isalpha() and nextoutput[0].isalpha():
            nextoutput = ' ' + nextoutput   # add extra space to terminate csname
        self.lastoutput = nextoutput
        return nextoutput
    
    def chunk(self):
        """Grab another set of input tokens and convert them to an output string."""
        for delta,c in self.candidates(0):
            if c in _l2u:
                self.pos += delta
                return unichr(_l2u[c])
            elif len(c) == 2 and c[1] == 'i' and (c[0],'\\i') in _l2u:
                self.pos += delta       # correct failure to undot i
                return unichr(_l2u[(c[0],'\\i')])
            elif len(c) == 1 and c[0].startswith('\\char') and c[0][5:].isdigit():
                self.pos += delta
                return unichr(int(c[0][5:]))
    
        # nothing matches, just pass through token as-is
        self.pos += 1
        return self[-1]
    
    def candidates(self,offset):
        """Generate pairs delta,c where c is a token or tuple of tokens from tex
        (after deleting extraneous brackets starting at pos) and delta
        is the length of the tokens prior to bracket deletion.
        """
        t = self[offset]
        if t in _blacklist:
            return
        elif t == '{':
            for delta,c in self.candidates(offset+1):
                if self[offset+delta+1] == '}':
                    yield delta+2,c
        elif t == '\\mbox':
            for delta,c in self.candidates(offset+1):
                yield delta+1,c
        elif t == '$' and self[offset+2] == '$':
            yield 3, (t,self[offset+1],t)
        else:
            q = self[offset+1]
            if q == '{' and self[offset+3] == '}':
                yield 4, (t,self[offset+2])
            elif q:
                yield 2, (t,q)
            yield 1, t

latex_equivalents = {
    0x0009: ' ',
    0x000a: '\n',
    0x0023: '{\#}',
    0x0026: '{\&}',
    0x00a0: '{~}',
    0x00a1: '{!`}',
    0x00a2: '{\\not{c}}',
    0x00a3: '{\\pounds}',
    0x00a7: '{\\S}',
    0x00a8: '{\\"{}}',
    0x00a9: '{\\copyright}',
    0x00af: '{\\={}}',
    0x00ac: '{\\neg}',
    0x00ad: '{\\-}',
    0x00b0: '{\\mbox{$^\\circ$}}',
    0x00b1: '{\\mbox{$\\pm$}}',
    0x00b2: '{\\mbox{$^2$}}',
    0x00b3: '{\\mbox{$^3$}}',
    0x00b4: "{\\'{}}",
    0x00b5: '{\\mbox{$\\mu$}}',
    0x00b6: '{\\P}',
    0x00b7: '{\\mbox{$\\cdot$}}',
    0x00b8: '{\\c{}}',
    0x00b9: '{\\mbox{$^1$}}',
    0x00bf: '{?`}',
    0x00c0: '{\\`A}',
    0x00c1: "{\\'A}",
    0x00c2: '{\\^A}',
    0x00c3: '{\\~A}',
    0x00c4: '{\\"A}',
    0x00c5: '{\\AA}',
    0x00c6: '{\\AE}',
    0x00c7: '{\\c{C}}',
    0x00c8: '{\\`E}',
    0x00c9: "{\\'E}",
    0x00ca: '{\\^E}',
    0x00cb: '{\\"E}',
    0x00cc: '{\\`I}',
    0x00cd: "{\\'I}",
    0x00ce: '{\\^I}',
    0x00cf: '{\\"I}',
    0x00d1: '{\\~N}',
    0x00d2: '{\\`O}',
    0x00d3: "{\\'O}",
    0x00d4: '{\\^O}',
    0x00d5: '{\\~O}',
    0x00d6: '{\\"O}',
    0x00d7: '{\\mbox{$\\times$}}',
    0x00d8: '{\\O}',
    0x00d9: '{\\`U}',
    0x00da: "{\\'U}",
    0x00db: '{\\^U}',
    0x00dc: '{\\"U}',
    0x00dd: "{\\'Y}",
    0x00df: '{\\ss}',
    0x00e0: '{\\`a}',
    0x00e1: "{\\'a}",
    0x00e2: '{\\^a}',
    0x00e3: '{\\~a}',
    0x00e4: '{\\"a}',
    0x00e5: '{\\aa}',
    0x00e6: '{\\ae}',
    0x00e7: '{\\c{c}}',
    0x00e8: '{\\`e}',
    0x00e9: "{\\'e}",
    0x00ea: '{\\^e}',
    0x00eb: '{\\"e}',
    0x00ec: '{\\`\\i}',
    0x00ed: "{\\'\\i}",
    0x00ee: '{\\^\\i}',
    0x00ef: '{\\"\\i}',
    0x00f1: '{\\~n}',
    0x00f2: '{\\`o}',
    0x00f3: "{\\'o}",
    0x00f4: '{\\^o}',
    0x00f5: '{\\~o}',
    0x00f6: '{\\"o}',
    0x00f7: '{\\mbox{$\\div$}}',
    0x00f8: '{\\o}',
    0x00f9: '{\\`u}',
    0x00fa: "{\\'u}",
    0x00fb: '{\\^u}',
    0x00fc: '{\\"u}',
    0x00fd: "{\\'y}",
    0x00ff: '{\\"y}',
    
    0x0100: '{\\=A}',
    0x0101: '{\\=a}',
    0x0102: '{\\u{A}}',
    0x0103: '{\\u{a}}',
    0x0104: '{\\c{A}}',
    0x0105: '{\\c{a}}',
    0x0106: "{\\'C}",
    0x0107: "{\\'c}",
    0x0108: "{\\^C}",
    0x0109: "{\\^c}",
    0x010a: "{\\.C}",
    0x010b: "{\\.c}",
    0x010c: "{\\v{C}}",
    0x010d: "{\\v{c}}",
    0x010e: "{\\v{D}}",
    0x010f: "{\\v{d}}",
    0x0112: '{\\=E}',
    0x0113: '{\\=e}',
    0x0114: '{\\u{E}}',
    0x0115: '{\\u{e}}',
    0x0116: '{\\.E}',
    0x0117: '{\\.e}',
    0x0118: '{\\c{E}}',
    0x0119: '{\\c{e}}',
    0x011a: "{\\v{E}}",
    0x011b: "{\\v{e}}",
    0x011c: '{\\^G}',
    0x011d: '{\\^g}',
    0x011e: '{\\u{G}}',
    0x011f: '{\\u{g}}',
    0x0120: '{\\.G}',
    0x0121: '{\\.g}',
    0x0122: '{\\c{G}}',
    0x0123: '{\\c{g}}',
    0x0124: '{\\^H}',
    0x0125: '{\\^h}',
    0x0128: '{\\~I}',
    0x0129: '{\\~\\i}',
    0x012a: '{\\=I}',
    0x012b: '{\\=\\i}',
    0x012c: '{\\u{I}}',
    0x012d: '{\\u\\i}',
    0x012e: '{\\c{I}}',
    0x012f: '{\\c{i}}',
    0x0130: '{\\.I}',
    0x0131: '{\\i}',
    0x0132: '{IJ}',
    0x0133: '{ij}',
    0x0134: '{\\^J}',
    0x0135: '{\\^\\j}',
    0x0136: '{\\c{K}}',
    0x0137: '{\\c{k}}',
    0x0139: "{\\'L}",
    0x013a: "{\\'l}",
    0x013b: "{\\c{L}}",
    0x013c: "{\\c{l}}",
    0x013d: "{\\v{L}}",
    0x013e: "{\\v{l}}",
    0x0141: '{\\L}',
    0x0142: '{\\l}',
    0x0143: "{\\'N}",
    0x0144: "{\\'n}",
    0x0145: "{\\c{N}}",
    0x0146: "{\\c{n}}",
    0x0147: "{\\v{N}}",
    0x0148: "{\\v{n}}",
    0x014c: '{\\=O}',
    0x014d: '{\\=o}',
    0x014e: '{\\u{O}}',
    0x014f: '{\\u{o}}',
    0x0150: '{\\H{O}}',
    0x0151: '{\\H{o}}',
    0x0152: '{\\OE}',
    0x0153: '{\\oe}',
    0x0154: "{\\'R}",
    0x0155: "{\\'r}",
    0x0156: "{\\c{R}}",
    0x0157: "{\\c{r}}",
    0x0158: "{\\v{R}}",
    0x0159: "{\\v{r}}",
    0x015a: "{\\'S}",
    0x015b: "{\\'s}",
    0x015c: "{\\^S}",
    0x015d: "{\\^s}",
    0x015e: "{\\c{S}}",
    0x015f: "{\\c{s}}",
    0x0160: "{\\v{S}}",
    0x0161: "{\\v{s}}",
    0x0162: "{\\c{T}}",
    0x0163: "{\\c{t}}",
    0x0164: "{\\v{T}}",
    0x0165: "{\\v{t}}",
    0x0168: "{\\~U}",
    0x0169: "{\\~u}",
    0x016a: "{\\=U}",
    0x016b: "{\\=u}",
    0x016c: "{\\u{U}}",
    0x016d: "{\\u{u}}",
    0x016e: "{\\r{U}}",
    0x016f: "{\\r{u}}",
    0x0170: "{\\H{U}}",
    0x0171: "{\\H{u}}",
    0x0172: "{\\c{U}}",
    0x0173: "{\\c{u}}",
    0x0174: "{\\^W}",
    0x0175: "{\\^w}",
    0x0176: "{\\^Y}",
    0x0177: "{\\^y}",
    0x0178: '{\\"Y}',
    0x0179: "{\\'Z}",
    0x017a: "{\\'Z}",
    0x017b: "{\\.Z}",
    0x017c: "{\\.Z}",
    0x017d: "{\\v{Z}}",
    0x017e: "{\\v{z}}",

    0x01c4: "{D\\v{Z}}",
    0x01c5: "{D\\v{z}}",
    0x01c6: "{d\\v{z}}",
    0x01c7: "{LJ}",
    0x01c8: "{Lj}",
    0x01c9: "{lj}",
    0x01ca: "{NJ}",
    0x01cb: "{Nj}",
    0x01cc: "{nj}",
    0x01cd: "{\\v{A}}",
    0x01ce: "{\\v{a}}",
    0x01cf: "{\\v{I}}",
    0x01d0: "{\\v\\i}",
    0x01d1: "{\\v{O}}",
    0x01d2: "{\\v{o}}",
    0x01d3: "{\\v{U}}",
    0x01d4: "{\\v{u}}",
    0x01e6: "{\\v{G}}",
    0x01e7: "{\\v{g}}",
    0x01e8: "{\\v{K}}",
    0x01e9: "{\\v{k}}",
    0x01ea: "{\\c{O}}",
    0x01eb: "{\\c{o}}",
    0x01f0: "{\\v\\j}",
    0x01f1: "{DZ}",
    0x01f2: "{Dz}",
    0x01f3: "{dz}",
    0x01f4: "{\\'G}",
    0x01f5: "{\\'g}",
    0x01fc: "{\\'\\AE}",
    0x01fd: "{\\'\\ae}",
    0x01fe: "{\\'\\O}",
    0x01ff: "{\\'\\o}",

    0x02c6: '{\\^{}}',
    0x02dc: '{\\~{}}',
    0x02d8: '{\\u{}}',
    0x02d9: '{\\.{}}',
    0x02da: "{\\r{}}",
    0x02dd: '{\\H{}}',
    0x02db: '{\\c{}}',
    0x02c7: '{\\v{}}',
    
    0x03c0: '{\\mbox{$\\pi$}}',
    # consider adding more Greek here
    
    0xfb01: '{fi}',
    0xfb02: '{fl}',
    
    0x2013: '{--}',
    0x2014: '{---}',
    0x2018: "{`}",
    0x2019: "{'}",
    0x201c: "{``}",
    0x201d: "{''}",
    0x2020: "{\\dag}",
    0x2021: "{\\ddag}",
    0x2122: "{\\mbox{$^\\mbox{TM}$}}",
    0x2022: "{\\mbox{$\\bullet$}}",
    0x2026: "{\\ldots}",
    0x2202: "{\\mbox{$\\partial$}}",
    0x220f: "{\\mbox{$\\prod$}}",
    0x2211: "{\\mbox{$\\sum$}}",
    0x221a: "{\\mbox{$\\surd$}}",
    0x221e: "{\\mbox{$\\infty$}}",
    0x222b: "{\\mbox{$\\int$}}",
    0x2248: "{\\mbox{$\\approx$}}",
    0x2260: "{\\mbox{$\\neq$}}",
    0x2264: "{\\mbox{$\\leq$}}",
    0x2265: "{\\mbox{$\\geq$}}",
}
for _i in range(0x0020):
    if _i not in latex_equivalents:
        latex_equivalents[_i] = ''
for _i in range(0x0020,0x007f):
    if _i not in latex_equivalents:
        latex_equivalents[_i] = chr(_i)

# Characters that should be ignored and not output in tokenization
_ignore = Set([chr(i) for i in range(32)+[127]]) - Set('\t\n\r')

# Regexp of chars not in blacklist, for quick start of tokenize
_stoppers = re.compile('[\x00-\x1f!$\\-?\\{~\\\\`\']')

_blacklist = Set(' \n\r')
_blacklist.add(None)    # shortcut candidate generation at end of data

# Construction of inverse translation table
_l2u = {
    '\ ':ord(' ')   # unexpanding space makes no sense in non-TeX contexts
}

for _tex in latex_equivalents:
    if _tex <= 0x0020 or (_tex <= 0x007f and len(latex_equivalents[_tex]) <= 1):
        continue    # boring entry
    _toks = tuple(_tokenize(latex_equivalents[_tex]))
    if _toks[0] == '{' and _toks[-1] == '}':
        _toks = _toks[1:-1]
    if _toks[0].isalpha():
        continue    # don't turn ligatures into single chars
    if len(_toks) == 1 and (_toks[0] == "'" or _toks[0] == "`"):
        continue    # don't turn ascii quotes into curly quotes
    if _toks[0] == '\\mbox' and _toks[1] == '{' and _toks[-1] == '}':
        _toks = _toks[2:-1]
    if len(_toks) == 4 and _toks[1] == '{' and _toks[3] == '}':
        _toks = (_toks[0],_toks[2])
    if len(_toks) == 1:
        _toks = _toks[0]
    _l2u[_toks] = _tex

# Shortcut candidate generation for certain useless candidates:
# a character is in _blacklist if it can not be at the start
# of any translation in _l2u.  We use this to quickly skip through
# such characters before getting to more difficult-translate parts.
# _blacklist is defined several lines up from here because it must
# be defined in order to call _tokenize, however it is safe to
# delay filling it out until now.

for i in range(0x0020,0x007f):
    _blacklist.add(chr(i))
_blacklist.remove('{')
_blacklist.remove('$')
for candidate in _l2u:
    if isinstance(candidate,tuple):
        if not candidate or not candidate[0]:
            continue
        firstchar = candidate[0][0]
    else:
        firstchar = candidate[0]
    _blacklist.discard(firstchar)

########NEW FILE########
__FILENAME__ = numfig
from docutils import nodes
from sphinx.roles import XRefRole
import figtable
import subfig
from backports import OrderedDict, OrderedSet

# Element classes

class page_ref(nodes.reference):
    pass

class num_ref(nodes.reference):
    pass


# Visit/depart functions

def skip_page_ref(self, node):
    raise nodes.SkipNode

def latex_visit_page_ref(self, node):
    self.body.append("\\pageref{%s:%s}" % (node['refdoc'], node['reftarget']))
    raise nodes.SkipNode

def latex_visit_num_ref(self, node):
    fields = node['reftarget'].split('#')
    
    if len(fields) > 1:
        label, target = fields
    else:
        label = None
        target = fields[0]
    
    if target not in self.builder.env.docnames_by_figname:
        raise nodes.SkipNode
    targetdoc = self.builder.env.docnames_by_figname[target]
    
    ref_link = '%s:%s' % (targetdoc, target)
    
    if label is None:
        latex = '\\ref{%s}' % ref_link
    else:
        latex = "\\hyperref[%s]{%s \\ref*{%s}}" % (ref_link, label, ref_link)
    
    self.body.append(latex)
    raise nodes.SkipNode


def doctree_read(app, doctree):
    # first generate figure numbers for each figure
    env = app.builder.env
    
    docname_figs = getattr(env, 'docname_figs', {})
    docnames_by_figname = getattr(env, 'docnames_by_figname', {})
    
    for figure_info in doctree.traverse(lambda n: isinstance(n, nodes.figure) or \
                                                  isinstance(n, subfig.subfigend) or \
                                                  isinstance(n, figtable.figtable)):
        
        for id in figure_info['ids']:
            docnames_by_figname[id] = env.docname
            
            fig_docname = docnames_by_figname[id]
            if fig_docname not in docname_figs:
                docname_figs[fig_docname] = OrderedDict()
            
            if isinstance(figure_info.parent, subfig.subfig):
                mainid = figure_info.parent['mainfigid']
            else:
                mainid = id
            
            if mainid not in docname_figs[fig_docname]:
                docname_figs[fig_docname][mainid] = OrderedSet()
            
            if isinstance(figure_info.parent, subfig.subfig):
                docname_figs[fig_docname][mainid].add(id)
    
    env.docnames_by_figname = docnames_by_figname
    env.docname_figs = docname_figs

def doctree_resolved(app, doctree, docname):
    # replace numfig nodes with links
    if app.builder.name in ('html', 'singlehtml', 'epub'):
        env = app.builder.env
        
        docname_figs = getattr(env, 'docname_figs', {})
        docnames_by_figname = env.docnames_by_figname
        
        figids = getattr(env, 'figids', {})
        
        secnums = []
        fignames_by_secnum = {}
        for figdocname, figurelist in env.docname_figs.iteritems():
            if figdocname not in env.toc_secnumbers:
                continue
            secnum = env.toc_secnumbers[figdocname]['']
            secnums.append(secnum)
            fignames_by_secnum[secnum] = figurelist
        
        last_secnum = 0
        secnums = sorted(secnums)
        figid = 1
        for secnum in secnums:
            if secnum[0] != last_secnum:
                figid = 1
            for figname, subfigs in fignames_by_secnum[secnum].iteritems():
                figids[figname] = str(secnum[0]) + '.' + str(figid)
                for i, subfigname in enumerate(subfigs):
                    subfigid = figids[figname] + chr(ord('a') + i)
                    figids[subfigname] = subfigid
                figid += 1
            last_secnum = secnum[0]
            
            env.figids = figids
        
        for figure_info in doctree.traverse(lambda n: isinstance(n, nodes.figure) or \
                                                      isinstance(n, subfig.subfigend) or \
                                                      isinstance(n, figtable.figtable)):
            id = figure_info['ids'][0]
            fignum = figids[id]
            for cap in figure_info.traverse(nodes.caption):
                cap.insert(1, nodes.Text(" %s" % cap[0]))
                if fignum[-1] in map(str, range(10)):
                    boldcaption = "%s %s:" % (app.config.figure_caption_prefix, fignum)
                else:
                    boldcaption = "(%s)" % fignum[-1]
                cap[0] = nodes.strong('', boldcaption)
        
        for ref_info in doctree.traverse(num_ref):
            if '#' in ref_info['reftarget']:
                label, target = ref_info['reftarget'].split('#')
                labelfmt = label + " %s"
            else:
                labelfmt = '%s'
                target = ref_info['reftarget']
            
            if target not in docnames_by_figname:
                app.warn('Target figure not found: %s' % target)
                link = "#%s" % target
                linktext = target
            else:
                target_doc = docnames_by_figname[target]
                
                if app.builder.name == 'singlehtml':
                    link = "#%s" % target
                else:
                    link = "%s#%s" % (app.builder.get_relative_uri(docname, target_doc),
                                      target)
                
                linktext = labelfmt % figids[target]
            
            html = '<a href="%s">%s</a>' % (link, linktext)
            ref_info.replace_self(nodes.raw(html, html, format='html'))

def setup(app):
    app.add_config_value('number_figures', True, True)
    app.add_config_value('figure_caption_prefix', "Figure", True)

    app.add_node(page_ref,
                 text=(skip_page_ref, None),
                 html=(skip_page_ref, None),
                 singlehtml=(skip_page_ref, None),
                 latex=(latex_visit_page_ref, None))

    app.add_role('page', XRefRole(nodeclass=page_ref))

    app.add_node(num_ref,
                 latex=(latex_visit_num_ref, None),
                 text=(skip_page_ref, None))

    app.add_role('num', XRefRole(nodeclass=num_ref))

    app.connect('doctree-read', doctree_read)
    app.connect('doctree-resolved', doctree_resolved)

########NEW FILE########
__FILENAME__ = numsec
"""
Changes section references to be the section number
instead of the title of the section.
"""

from docutils import nodes
import sphinx.domains.std

class CustomStandardDomain(sphinx.domains.std.StandardDomain):

    def __init__(self, env):
        env.settings['footnote_references'] = 'superscript'
        sphinx.domains.std.StandardDomain.__init__(self, env)

    def resolve_xref(self, env, fromdocname, builder,
                     typ, target, node, contnode):
        res = super(CustomStandardDomain, self).resolve_xref(env, fromdocname, builder,
                                                            typ, target, node, contnode)
        
        if res is None:
            return res
        
        if typ == 'ref' and not node['refexplicit']:
            docname, labelid, sectname = self.data['labels'].get(target, ('','',''))
            res['refdocname'] = docname
        
        return res

def doctree_resolved(app, doctree, docname):
    secnums = app.builder.env.toc_secnumbers
    for node in doctree.traverse(nodes.reference):
        if 'refdocname' in node:
            refdocname = node['refdocname']
            if refdocname in secnums:
                secnum = secnums[refdocname]
                emphnode = node.children[0]
                textnode = emphnode.children[0]
                
                toclist = app.builder.env.tocs[refdocname]
                anchorname = None
                for refnode in toclist.traverse(nodes.reference):
                    if refnode.astext() == textnode.astext():
                        anchorname = refnode['anchorname']
                if anchorname is None:
                    continue
                linktext = '.'.join(map(str, secnum[anchorname]))
                node.replace(emphnode, nodes.Text(linktext))

def setup(app):
    app.override_domain(CustomStandardDomain)
    app.connect('doctree-resolved', doctree_resolved)

########NEW FILE########
__FILENAME__ = singlehtml_toc
"""
Fixes the table of contents in singlehtml mode so that section titles have the
correct section number in front.
"""

from docutils import nodes
from sphinx import addnodes

def stringize_secnum(secnum):
    return '.'.join(map(str, secnum))

def doctree_resolved(app, doctree, fromdocname):
    if app.builder.name == 'singlehtml':
        secnums = app.builder.env.toc_secnumbers
        for filenode in doctree.traverse(addnodes.start_of_file):
            docname = filenode['docname']
            if docname not in secnums:
                continue
            
            doc_secnums = secnums[docname]
            first_title_node = filenode.next_node(nodes.title)
            if first_title_node is not None and '' in doc_secnums:
                file_secnum = stringize_secnum(doc_secnums[''])
                title_text_node = first_title_node.children[0]
                newtext = file_secnum + ' ' + title_text_node.astext()
                first_title_node.replace(title_text_node, nodes.Text(newtext))
            
            for section_node in filenode.traverse(nodes.section):
                for id in section_node['ids']:
                    if '#' + id in doc_secnums:
                        subsection_num = stringize_secnum(doc_secnums['#' + id])
                        first_title_node = section_node.next_node(nodes.title)
                        if first_title_node is not None:
                            title_text_node = first_title_node.children[0]
                            newtext = subsection_num + ' ' + title_text_node.astext()
                            first_title_node.replace(title_text_node, nodes.Text(newtext))

def setup(app):
    app.connect('doctree-resolved', doctree_resolved)

########NEW FILE########
__FILENAME__ = singletext
import codecs
from os import path

from docutils.io import StringOutput

from sphinx.util.console import bold, darkgreen, brown
from sphinx.util.nodes import inline_all_toctrees
from sphinx.util.osutil import ensuredir, os_path
from sphinx.builders.text import TextBuilder
from sphinx.writers.text import TextWriter, TextTranslator

class SingleFileTextTranslator(TextTranslator):
    def visit_start_of_file(self, node):
        pass
    def depart_start_of_file(self, node):
        pass

class SingleFileTextWriter(TextWriter):
    def translate(self):
        visitor = SingleFileTextTranslator(self.document, self.builder)
        self.document.walkabout(visitor)
        self.output = visitor.body

class SingleFileTextBuilder(TextBuilder):
    """
    A TextBuilder subclass that puts the whole document tree in one text file.
    """
    name = 'singletext'
    copysource = False

    def get_outdated_docs(self):
        return 'all documents'

    def assemble_doctree(self):
        master = self.config.master_doc
        tree = self.env.get_doctree(master)
        tree = inline_all_toctrees(self, set(), master, tree, darkgreen)
        tree['docname'] = master
        self.env.resolve_references(tree, master, self)
        return tree

    def prepare_writing(self, docnames):
        self.writer = SingleFileTextWriter(self)

    def write(self, *ignored):
        docnames = self.env.all_docs

        self.info(bold('preparing documents... '), nonl=True)
        self.prepare_writing(docnames)
        self.info('done')

        self.info(bold('assembling single document... '), nonl=True)
        doctree = self.assemble_doctree()
        self.info()
        self.info(bold('writing... '), nonl=True)
        self.write_doc(self.config.master_doc, doctree)
        self.info('done')

def setup(app):
    app.add_builder(SingleFileTextBuilder)

########NEW FILE########
__FILENAME__ = subfig
"""
Adds subfigure functionality
"""

from docutils import nodes
import docutils.parsers.rst.directives as directives
from sphinx.util.compat import Directive
from sphinx import addnodes

class subfig(nodes.General, nodes.Element):
    pass

def skip_visit(self, node):
    raise nodes.SkipNode

def visit_subfig_tex(self, node):
    self.__body = self.body
    self.body = []

def depart_subfig_tex(self, node):
    figoutput = ''.join(self.body)
    figoutput = figoutput.replace('[tbp]', '[t]{%s\\linewidth}' % node['width'])
    figoutput = figoutput.replace('figure', 'subfigure')
    self.body = self.__body
    self.body.append(figoutput)

def visit_subfig_html(self, node):
    self.__body = self.body
    self.body = []

def depart_subfig_html(self, node):
    figoutput = ''.join(self.body)
    figoutput = figoutput.replace('class="figure', 'style="width: %g%%" class="subfigure' % (float(node['width']) * 100))
    self.body = self.__body
    self.body.append(figoutput)

class subfigstart(nodes.General, nodes.Element):
    pass

def visit_subfigstart_tex(self, node):
    self.body.append('\n\\begin{figure}\n\\centering\n\\capstart\n')

def depart_subfigstart_tex(self, node):
    pass

def visit_subfigstart_html(self, node):
    atts = {'class': 'figure compound align-center'}
    self.body.append(self.starttag(node['subfigend'], 'div', **atts))

def depart_subfigstart_html(self, node):
    pass

class subfigend(nodes.General, nodes.Element):
    pass

def visit_subfigend_tex(self, node):
    pass

def depart_subfigend_tex(self, node):
    self.body.append('\n\n\\end{figure}\n\n')

def visit_subfigend_html(self, node):
    pass

def depart_subfigend_html(self, node):
    self.body.append('</div>')

class SubFigEndDirective(Directive):
    has_content = True
    optional_arguments = 3
    final_argument_whitespace = True

    option_spec = {'label': directives.uri,
                   'alt': directives.unchanged,
                   'width': directives.unchanged_required}
    
    def run(self):
        label = self.options.get('label', None)
        width = self.options.get('width', None)
        alt = self.options.get('alt', None)
        
        node = subfigend('', ids=[label] if label is not None else [])
        
        if width is not None:
            node['width'] = width
        if alt is not None:
            node['alt'] = alt
        
        if self.content:
            anon = nodes.Element()
            self.state.nested_parse(self.content, self.content_offset, anon)
            first_node = anon[0]
            if isinstance(first_node, nodes.paragraph):
                caption = nodes.caption(first_node.rawsource, '',
                                        *first_node.children)
                node += caption
        
        if label is not None:
            targetnode = nodes.target('', '', ids=[label])
            node.append(targetnode)
        
        return [node]

class SubFigStartDirective(Directive):
    has_content = False
    optional_arguments = 0
    
    def run(self):
        node = subfigstart()
        return [node]

def doctree_read(app, doctree):
    secnums = app.builder.env.toc_secnumbers
    for node in doctree.traverse(subfigstart):
        parentloc = node.parent.children.index(node)
        
        subfigendloc = parentloc
        while subfigendloc < len(node.parent.children):
            n = node.parent.children[subfigendloc]
            if isinstance(n, subfigend):
                break
            subfigendloc += 1
        
        if subfigendloc == len(node.parent.children):
            return
        
        between_nodes = node.parent.children[parentloc:subfigendloc]
        subfigend_node = node.parent.children[subfigendloc]
        node['subfigend'] = subfigend_node
        for i, n in enumerate(between_nodes):
            if isinstance(n, nodes.figure):
                children = [n]
                prevnode = between_nodes[i-1]
                if isinstance(prevnode, nodes.target):
                    node.parent.children.remove(prevnode)
                    children.insert(0, prevnode)
                nodeloc = node.parent.children.index(n)
                node.parent.children[nodeloc] = subfig('', *children)
                node.parent.children[nodeloc]['width'] = subfigend_node['width']
                node.parent.children[nodeloc]['mainfigid'] = subfigend_node['ids'][0]

def setup(app):
    app.add_node(subfigstart,
                 html=(visit_subfigstart_html, depart_subfigstart_html),
                 singlehtml=(visit_subfigstart_html, depart_subfigstart_html),
                 text=(skip_visit, None),
                 latex=(visit_subfigstart_tex, depart_subfigstart_tex))

    app.add_node(subfig,
                 html=(visit_subfig_html, depart_subfig_html),
                 singlehtml=(visit_subfig_html, depart_subfig_html),
                 text=(skip_visit, None),
                 latex=(visit_subfig_tex, depart_subfig_tex))

    app.add_node(subfigend,
                 html=(visit_subfigend_html, depart_subfigend_html),
                 singlehtml=(visit_subfigend_html, depart_subfigend_html),
                 text=(skip_visit, None),
                 latex=(visit_subfigend_tex, depart_subfigend_tex))

    app.add_directive('subfigstart', SubFigStartDirective)
    app.add_directive('subfigend', SubFigEndDirective)
    
    app.connect('doctree-read', doctree_read)

########NEW FILE########
