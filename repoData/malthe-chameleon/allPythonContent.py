__FILENAME__ = bm_chameleon
#!/usr/bin/python2

"""
Benchmark for test the performance of Chameleon page template engine.
"""

__author__ = "mborch@gmail.com (Malthe Borch)"

# Python imports
import os
import sys
import optparse
import time

# Local imports
import util


def relative(*args):
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), *args)

sys.path.insert(0, relative('..', 'src'))

# Chameleon imports
from chameleon import PageTemplate


LOREM_IPSUM = """Quisque lobortis hendrerit posuere. Curabitur
aliquet consequat sapien molestie pretium. Nunc adipiscing luc
tus mi, viverra porttitor lorem vulputate et. Ut at purus sem,
sed tincidunt ante. Vestibulum ante ipsum primis in faucibus
orci luctus et ultrices posuere cubilia Curae; Praesent pulvinar
sodales justo at congue. Praesent aliquet facilisis nisl a
molestie. Sed tempus nisl ut augue eleifend tincidunt. Sed a
lacinia nulla. Cras tortor est, mollis et consequat at,
vulputate et orci. Nulla sollicitudin"""

BASE_TEMPLATE = '''
<tal:macros condition="False">
    <table metal:define-macro="table">
       <tr tal:repeat="row table">
          <td tal:repeat="col row">${col}</td>
       </tr>
    </table>
    <img metal:define-macro="img" src="${src}" alt="${alt}" />
</tal:macros>
<html metal:define-macro="master">
    <head><title>${title.strip()}</title></head>
    <body metal:define-slot="body" />
</html>
'''

PAGE_TEMPLATE = '''
<html metal:define-macro="master" metal:extend-macro="base.macros['master']">
<body metal:fill-slot="body">
<table metal:use-macro="base.macros['table']" />
images:
<tal:images repeat="nr xrange(img_count)">
    <img tal:define="src '/foo/bar/baz.png';
                     alt 'no image :o'"
         metal:use-macro="base.macros['img']" />
</tal:images>
<metal:body define-slot="body" />
<p tal:repeat="nr paragraphs">${lorem}</p>
<table metal:use-macro="base.macros['table']" />
</body>
</html>
'''

CONTENT_TEMPLATE = '''
<html metal:use-macro="page.macros['master']">
<span metal:define-macro="fun1">fun1</span>
<span metal:define-macro="fun2">fun2</span>
<span metal:define-macro="fun3">fun3</span>
<span metal:define-macro="fun4">fun4</span>
<span metal:define-macro="fun5">fun5</span>
<span metal:define-macro="fun6">fun6</span>
<body metal:fill-slot="body">
<p>Lorem ipsum dolor sit amet, consectetur adipiscing elit.
Nam laoreet justo in velit faucibus lobortis. Sed dictum sagittis
volutpat. Sed adipiscing vestibulum consequat. Nullam laoreet, ante
nec pretium varius, libero arcu porttitor orci, id cursus odio nibh
nec leo. Vestibulum dapibus pellentesque purus, sed bibendum tortor
laoreet id. Praesent quis sodales ipsum. Fusce ut ligula sed diam
pretium sagittis vel at ipsum. Nulla sagittis sem quam, et volutpat
velit. Fusce dapibus ligula quis lectus ultricies tempor. Pellente</p>
<span metal:use-macro="template.macros['fun1']" />
<span metal:use-macro="template.macros['fun2']" />
<span metal:use-macro="template.macros['fun3']" />
<span metal:use-macro="template.macros['fun4']" />
<span metal:use-macro="template.macros['fun5']" />
<span metal:use-macro="template.macros['fun6']" />
</body>
</html>
'''


def test_mako(count):
    template = PageTemplate(CONTENT_TEMPLATE)
    base = PageTemplate(BASE_TEMPLATE)
    page = PageTemplate(PAGE_TEMPLATE)

    table = [xrange(150) for i in xrange(150)]
    paragraphs = xrange(50)
    title = 'Hello world!'

    times = []
    for i in range(count):
        t0 = time.time()
        data = template.render(
            table=table, paragraphs=paragraphs,
            lorem=LOREM_IPSUM, title=title,
            img_count=50,
            base=base,
            page=page,
            )
        t1 = time.time()
        times.append(t1-t0)
    return times

if __name__ == "__main__":
    parser = optparse.OptionParser(
        usage="%prog [options]",
        description=("Test the performance of Chameleon templates."))
    util.add_standard_options_to(parser)
    (options, args) = parser.parse_args()

    util.run_benchmark(options, options.num_runs, test_mako)

########NEW FILE########
__FILENAME__ = bm_mako
#!/usr/bin/python

"""
Benchmark for test the performance of Mako templates engine.
Includes:
    -two template inherences
    -HTML escaping, XML escaping, URL escaping, whitespace trimming
    -function defitions and calls
    -forloops
"""

__author__ = "virhilo@gmail.com (Lukasz Fidosz)"

# Python imports
import os
import sys
import optparse
import time

# Local imports
import util

def relative(*args):
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), *args)

sys.path.insert(0, relative('..', 'lib'))

# Mako imports
from mako.template import Template
from mako.lookup import TemplateLookup


LOREM_IPSUM = """Quisque lobortis hendrerit posuere. Curabitur
aliquet consequat sapien molestie pretium. Nunc adipiscing luc
tus mi, viverra porttitor lorem vulputate et. Ut at purus sem,
sed tincidunt ante. Vestibulum ante ipsum primis in faucibus 
orci luctus et ultrices posuere cubilia Curae; Praesent pulvinar
sodales justo at congue. Praesent aliquet facilisis nisl a
molestie. Sed tempus nisl ut augue eleifend tincidunt. Sed a
lacinia nulla. Cras tortor est, mollis et consequat at,
vulputate et orci. Nulla sollicitudin"""

BASE_TEMPLATE = """
<%def name="render_table(table)">
    <table>
    % for row in table:
        <tr>
        % for col in row:
            <td>${col|h}</td>
        % endfor
        </tr>
    % endfor
    </table>
</%def>
<%def name="img(src, alt)">
    <img src="${src|u}" alt="${alt}" />
</%def>
<html>
    <head><title>${title|h,trim}</title></head>
    <body>
        ${next.body()}
    </body>
<html>
"""

PAGE_TEMPLATE = """
<%inherit file="base.mako"/>
<table>
    % for row in table:
        <tr>
            % for col in row:
                <td>${col}</td>
            % endfor
        </tr>
    % endfor
</table>
% for nr in xrange(img_count):
    ${parent.img('/foo/bar/baz.png', 'no image :o')}
% endfor
${next.body()}
% for nr in paragraphs:
    <p>${lorem|x}</p>
% endfor
${parent.render_table(table)}
"""

CONTENT_TEMPLATE = """
<%inherit file="page.mako"/>
<%def name="fun1()">
    <span>fun1</span>
</%def>
<%def name="fun2()">
    <span>fun2</span>
</%def>
<%def name="fun3()">
    <span>foo3</span>
</%def>
<%def name="fun4()">
    <span>foo4</span>
</%def>
<%def name="fun5()">
    <span>foo5</span>
</%def>
<%def name="fun6()">
    <span>foo6</span>
</%def>
<p>Lorem ipsum dolor sit amet, consectetur adipiscing elit.
Nam laoreet justo in velit faucibus lobortis. Sed dictum sagittis
volutpat. Sed adipiscing vestibulum consequat. Nullam laoreet, ante
nec pretium varius, libero arcu porttitor orci, id cursus odio nibh
nec leo. Vestibulum dapibus pellentesque purus, sed bibendum tortor
laoreet id. Praesent quis sodales ipsum. Fusce ut ligula sed diam
pretium sagittis vel at ipsum. Nulla sagittis sem quam, et volutpat
velit. Fusce dapibus ligula quis lectus ultricies tempor. Pellente</p>
${fun1()}
${fun2()}
${fun3()}
${fun4()}
${fun5()}
${fun6()}
"""


def test_mako(count):

    lookup = TemplateLookup()
    lookup.put_string('base.mako', BASE_TEMPLATE)
    lookup.put_string('page.mako', PAGE_TEMPLATE)

    template = Template(CONTENT_TEMPLATE, lookup=lookup)
    
    table = [xrange(150) for i in xrange(150)]
    paragraphs = xrange(50)
    title = 'Hello world!'

    times = []
    for i in range(count):
        t0 = time.time()
        data = template.render(table=table, paragraphs=paragraphs,
                               lorem=LOREM_IPSUM, title=title,
                               img_count=50)
        t1 = time.time()
        times.append(t1-t0)
    return times

if __name__ == "__main__":
    parser = optparse.OptionParser(
        usage="%prog [options]",
        description=("Test the performance of Mako templates."))
    util.add_standard_options_to(parser)
    (options, args) = parser.parse_args()

    util.run_benchmark(options, options.num_runs, test_mako)

########NEW FILE########
__FILENAME__ = util
#!/usr/bin/env python

"""Utility code for benchmark scripts."""

__author__ = "collinwinter@google.com (Collin Winter)"

import math
import operator


def run_benchmark(options, num_runs, bench_func, *args):
    """Run the given benchmark, print results to stdout.

    Args:
        options: optparse.Values instance.
        num_runs: number of times to run the benchmark
        bench_func: benchmark function. `num_runs, *args` will be passed to this
            function. This should return a list of floats (benchmark execution
            times).
    """
    if options.profile:
        import cProfile
        prof = cProfile.Profile()
        prof.runcall(bench_func, num_runs, *args)
        prof.print_stats(sort=options.profile_sort)
    else:
        data = bench_func(num_runs, *args)
        if options.take_geo_mean:
            product = reduce(operator.mul, data, 1)
            print math.pow(product, 1.0 / len(data))
        else:
            for x in data:
                print x


def add_standard_options_to(parser):
    """Add a bunch of common command-line flags to an existing OptionParser.

    This function operates on `parser` in-place.

    Args:
        parser: optparse.OptionParser instance.
    """
    parser.add_option("-n", action="store", type="int", default=100,
                      dest="num_runs", help="Number of times to run the test.")
    parser.add_option("--profile", action="store_true",
                      help="Run the benchmark through cProfile.")
    parser.add_option("--profile_sort", action="store", type="str",
                      default="time", help="Column to sort cProfile output by.")
    parser.add_option("--take_geo_mean", action="store_true",
                      help="Return the geo mean, rather than individual data.")

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# Chameleon documentation build configuration file, created by
# sphinx-quickstart on Sun Nov  1 16:08:00 2009.
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
#sys.path.append(os.path.abspath('.'))

# -- General configuration -----------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'Chameleon'
copyright = u'2008-2011 by Malthe Borch and the Repoze Community'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '2.10'
# The full version, including alpha/beta/rc tags.
release = '2.10'

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of documents that shouldn't be included in the build.
#unused_docs = []

# List of directories, relative to source directory, that shouldn't be searched
# for source files.
exclude_trees = ['_build']

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

# The theme to use for HTML and HTML Help pages.  Major themes that come with
# Sphinx are currently 'default' and 'sphinxdoc'.
html_theme = 'default'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
#html_theme_path = []

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
html_title = "Chameleon %s documentation" % version

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

# If not '', a 'Last updated on:' timestamp is inserted at every page bchameleonm,
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
#html_use_modindex = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# If nonempty, this is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = ''

# Output file base name for HTML help builder.
htmlhelp_basename = 'chameleondoc'


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'chameleon.tex', u'Chameleon Documentation',
   u'Malthe Borch et. al', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# Additional stuff for the LaTeX preamble.
#latex_preamble = ''

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_use_modindex = True

########NEW FILE########
__FILENAME__ = ast25
# -*- coding: utf-8 -*-
#
# Copyright 2008 by Armin Ronacher.
# License: Python License.
#

import _ast

from _ast import *


def fix_missing_locations(node):
    """
    When you compile a node tree with compile(), the compiler expects lineno and
    col_offset attributes for every node that supports them.  This is rather
    tedious to fill in for generated nodes, so this helper adds these attributes
    recursively where not already set, by setting them to the values of the
    parent node.  It works recursively starting at *node*.
    """
    def _fix(node, lineno, col_offset):
        if 'lineno' in node._attributes:
            if not hasattr(node, 'lineno'):
                node.lineno = lineno
            else:
                lineno = node.lineno
        if 'col_offset' in node._attributes:
            if not hasattr(node, 'col_offset'):
                node.col_offset = col_offset
            else:
                col_offset = node.col_offset
        for child in iter_child_nodes(node):
            _fix(child, lineno, col_offset)
    _fix(node, 1, 0)
    return node


def iter_child_nodes(node):
    """
    Yield all direct child nodes of *node*, that is, all fields that are nodes
    and all items of fields that are lists of nodes.
    """
    for name, field in iter_fields(node):
        if isinstance(field, (AST, _ast.AST)):
            yield field
        elif isinstance(field, list):
            for item in field:
                if isinstance(item, (AST, _ast.AST)):
                    yield item


def iter_fields(node):
    """
    Yield a tuple of ``(fieldname, value)`` for each field in ``node._fields``
    that is present on *node*.
    """

    for field in node._fields or ():
        try:
            yield field, getattr(node, field)
        except AttributeError:
            pass


def walk(node):
    """
    Recursively yield all child nodes of *node*, in no specified order.  This is
    useful if you only want to modify nodes in place and don't care about the
    context.
    """
    from collections import deque
    todo = deque([node])
    while todo:
        node = todo.popleft()
        todo.extend(iter_child_nodes(node))
        yield node


class NodeVisitor(object):
    """
    A node visitor base class that walks the abstract syntax tree and calls a
    visitor function for every node found.  This function may return a value
    which is forwarded by the `visit` method.

    This class is meant to be subclassed, with the subclass adding visitor
    methods.

    Per default the visitor functions for the nodes are ``'visit_'`` +
    class name of the node.  So a `TryFinally` node visit function would
    be `visit_TryFinally`.  This behavior can be changed by overriding
    the `visit` method.  If no visitor function exists for a node
    (return value `None`) the `generic_visit` visitor is used instead.

    Don't use the `NodeVisitor` if you want to apply changes to nodes during
    traversing.  For this a special visitor exists (`NodeTransformer`) that
    allows modifications.
    """

    def visit(self, node):
        """Visit a node."""
        method = 'visit_' + node.__class__.__name__
        visitor = getattr(self, method, self.generic_visit)
        return visitor(node)

    def generic_visit(self, node):
        """Called if no explicit visitor function exists for a node."""
        for field, value in iter_fields(node):
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, (AST, _ast.AST)):
                        self.visit(item)
            elif isinstance(value, (AST, _ast.AST)):
                self.visit(value)


class AST(object):
    _fields = ()
    _attributes = 'lineno', 'col_offset'

    def __init__(self, *args, **kwargs):
        self.__dict__.update(kwargs)
        self._fields = self._fields or ()
        for name, value in zip(self._fields, args):
            setattr(self, name, value)


for name, cls in _ast.__dict__.items():
    if isinstance(cls, type) and issubclass(cls, _ast.AST):
        try:
            cls.__bases__ = (AST, ) + cls.__bases__
        except TypeError:
            pass


class ExceptHandler(AST):
    _fields = "type", "name", "body"

########NEW FILE########
__FILENAME__ = astutil
# -*- coding: utf-8 -*-
#
# Copyright (C) 2008-2009 Edgewall Software
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution. The terms
# are also available at http://genshi.edgewall.org/wiki/License.
#
# This software consists of voluntary contributions made by many
# individuals. For the exact contribution history, see the revision
# history and logs, available at http://genshi.edgewall.org/log/.

"""Support classes for generating code from abstract syntax trees."""

try:
    import ast
except ImportError:
    from chameleon import ast25 as ast

import sys
import logging
import weakref
import collections

node_annotations = weakref.WeakKeyDictionary()

try:
    node_annotations[ast.Name()] = None
except TypeError:
    logging.debug(
        "Unable to create weak references to AST nodes. " \
        "A lock will be used around compilation loop."
        )

    node_annotations = {}

__docformat__ = 'restructuredtext en'


def annotated(value):
    node = load("annotation")
    node_annotations[node] = value
    return node


def parse(source, mode='eval'):
    return compile(source, '', mode, ast.PyCF_ONLY_AST)


def load(name):
    return ast.Name(id=name, ctx=ast.Load())


def store(name):
    return ast.Name(id=name, ctx=ast.Store())


def param(name):
    return ast.Name(id=name, ctx=ast.Param())


def delete(name):
    return ast.Name(id=name, ctx=ast.Del())


def subscript(name, value, ctx):
    return ast.Subscript(
        value=value,
        slice=ast.Index(value=ast.Str(s=name)),
        ctx=ctx,
        )


def walk_names(target, mode):
    for node in ast.walk(target):
        if isinstance(node, ast.Name) and \
               isinstance(node.ctx, mode):
            yield node.id


def iter_fields(node):
    """
    Yield a tuple of ``(fieldname, value)`` for each field in ``node._fields``
    that is present on *node*.
    """
    for field in node._fields:
        try:
            yield field, getattr(node, field)
        except AttributeError:
            pass


def iter_child_nodes(node):
    """
    Yield all direct child nodes of *node*, that is, all fields that are nodes
    and all items of fields that are lists of nodes.
    """
    for name, field in iter_fields(node):
        if isinstance(field, Node):
            yield field
        elif isinstance(field, list):
            for item in field:
                if isinstance(item, Node):
                    yield item


def walk(node):
    """
    Recursively yield all descendant nodes in the tree starting at *node*
    (including *node* itself), in no specified order.  This is useful if you
    only want to modify nodes in place and don't care about the context.
    """
    todo = collections.deque([node])
    while todo:
        node = todo.popleft()
        todo.extend(iter_child_nodes(node))
        yield node


def copy(source, target):
    target.__class__ = source.__class__
    target.__dict__ = source.__dict__


def swap(root, replacement, name):
    for node in ast.walk(root):
        if (isinstance(node, ast.Name) and
            isinstance(node.ctx, ast.Load) and
            node.id == name):
            assert hasattr(replacement, '_fields')
            node_annotations.setdefault(node, replacement)


def marker(name):
    return ast.Str(s="__%s" % name)


class Node(object):
    """AST baseclass that gives us a convenient initialization
    method. We explicitly declare and use the ``_fields`` attribute."""

    _fields = ()

    def __init__(self, *args, **kwargs):
        assert isinstance(self._fields, tuple)
        self.__dict__.update(kwargs)
        for name, value in zip(self._fields, args):
            setattr(self, name, value)

    def __repr__(self):
        """Poor man's single-line pretty printer."""

        name = type(self).__name__
        return '<%s%s at %x>' % (
            name,
            "".join(" %s=%r" % (name, getattr(self, name, "\"?\""))
                        for name in self._fields),
            id(self)
            )

    def extract(self, condition):
        result = []
        for node in walk(self):
            if condition(node):
                result.append(node)

        return result


class Builtin(Node):
    """Represents a Python builtin.

    Used when a builtin is used internally by the compiler, to avoid
    clashing with a user assignment (e.g. ``help`` is a builtin, but
    also commonly assigned in templates).
    """

    _fields = "id", "ctx"

    ctx = ast.Load()


class Symbol(Node):
    """Represents an importable symbol."""

    _fields = "value",


class Static(Node):
    """Represents a static value."""

    _fields = "value", "name"

    name = None


class Comment(Node):
    _fields = "text", "space", "stmt"

    stmt = None
    space = ""


class ASTCodeGenerator(object):
    """General purpose base class for AST transformations.

    Every visitor method can be overridden to return an AST node that has been
    altered or replaced in some way.
    """

    def __init__(self, tree):
        self.lines_info = []
        self.line_info = []
        self.lines = []
        self.line = ""
        self.last = None
        self.indent = 0
        self.blame_stack = []
        self.visit(tree)

        if self.line.strip():
            self._new_line()

        self.line = None
        self.line_info = None

        # strip trivial lines
        self.code = "\n".join(
            line.strip() and line or ""
            for line in self.lines
            )

    def _change_indent(self, delta):
        self.indent += delta

    def _new_line(self):
        if self.line is not None:
            self.lines.append(self.line)
            self.lines_info.append(self.line_info)
        self.line = ' ' * 4 * self.indent
        if len(self.blame_stack) == 0:
            self.line_info = []
            self.last = None
        else:
            self.line_info = [(0, self.blame_stack[-1],)]
            self.last = self.blame_stack[-1]

    def _write(self, s):
        if len(s) == 0:
            return
        if len(self.blame_stack) == 0:
            if self.last is not None:
                self.last = None
                self.line_info.append((len(self.line), self.last))
        else:
            if self.last != self.blame_stack[-1]:
                self.last = self.blame_stack[-1]
                self.line_info.append((len(self.line), self.last))
        self.line += s

    def flush(self):
        if self.line:
            self._new_line()

    def visit(self, node):
        if node is None:
            return None
        if type(node) is tuple:
            return tuple([self.visit(n) for n in node])
        try:
            self.blame_stack.append((node.lineno, node.col_offset,))
            info = True
        except AttributeError:
            info = False
        visitor = getattr(self, 'visit_%s' % node.__class__.__name__, None)
        if visitor is None:
            raise Exception('No handler for ``%s`` (%s).' % (
                node.__class__.__name__, repr(node)))
        ret = visitor(node)
        if info:
            self.blame_stack.pop()
        return ret

    def visit_Module(self, node):
        for n in node.body:
            self.visit(n)
    visit_Interactive = visit_Module
    visit_Suite = visit_Module

    def visit_Expression(self, node):
        return self.visit(node.body)

    # arguments = (expr* args, identifier? vararg,
    #              identifier? kwarg, expr* defaults)
    def visit_arguments(self, node):
        first = True
        no_default_count = len(node.args) - len(node.defaults)
        for i, arg in enumerate(node.args):
            if not first:
                self._write(', ')
            else:
                first = False
            self.visit(arg)
            if i >= no_default_count:
                self._write('=')
                self.visit(node.defaults[i - no_default_count])
        if getattr(node, 'vararg', None):
            if not first:
                self._write(', ')
            else:
                first = False
            self._write('*' + node.vararg)
        if getattr(node, 'kwarg', None):
            if not first:
                self._write(', ')
            else:
                first = False
            self._write('**' + node.kwarg)

    def visit_arg(self, node):
        self._write(node.arg)

    # FunctionDef(identifier name, arguments args,
    #                           stmt* body, expr* decorators)
    def visit_FunctionDef(self, node):
        self._new_line()
        for decorator in getattr(node, 'decorator_list', ()):
            self._new_line()
            self._write('@')
            self.visit(decorator)
        self._new_line()
        self._write('def ' + node.name + '(')
        self.visit(node.args)
        self._write('):')
        self._change_indent(1)
        for statement in node.body:
            self.visit(statement)
        self._change_indent(-1)

    # ClassDef(identifier name, expr* bases, stmt* body)
    def visit_ClassDef(self, node):
        self._new_line()
        self._write('class ' + node.name)
        if node.bases:
            self._write('(')
            self.visit(node.bases[0])
            for base in node.bases[1:]:
                self._write(', ')
                self.visit(base)
            self._write(')')
        self._write(':')
        self._change_indent(1)
        for statement in node.body:
            self.visit(statement)
        self._change_indent(-1)

    # Return(expr? value)
    def visit_Return(self, node):
        self._new_line()
        self._write('return')
        if getattr(node, 'value', None):
            self._write(' ')
            self.visit(node.value)

    # Delete(expr* targets)
    def visit_Delete(self, node):
        self._new_line()
        self._write('del ')
        self.visit(node.targets[0])
        for target in node.targets[1:]:
            self._write(', ')
            self.visit(target)

    # Assign(expr* targets, expr value)
    def visit_Assign(self, node):
        self._new_line()
        for target in node.targets:
            self.visit(target)
            self._write(' = ')
        self.visit(node.value)

    # AugAssign(expr target, operator op, expr value)
    def visit_AugAssign(self, node):
        self._new_line()
        self.visit(node.target)
        self._write(' ' + self.binary_operators[node.op.__class__] + '= ')
        self.visit(node.value)

    # Print(expr? dest, expr* values, bool nl)
    def visit_Print(self, node):
        self._new_line()
        self._write('print')
        if getattr(node, 'dest', None):
            self._write(' >> ')
            self.visit(node.dest)
            if getattr(node, 'values', None):
                self._write(', ')
        else:
            self._write(' ')
        if getattr(node, 'values', None):
            self.visit(node.values[0])
            for value in node.values[1:]:
                self._write(', ')
                self.visit(value)
        if not node.nl:
            self._write(',')

    # For(expr target, expr iter, stmt* body, stmt* orelse)
    def visit_For(self, node):
        self._new_line()
        self._write('for ')
        self.visit(node.target)
        self._write(' in ')
        self.visit(node.iter)
        self._write(':')
        self._change_indent(1)
        for statement in node.body:
            self.visit(statement)
        self._change_indent(-1)
        if getattr(node, 'orelse', None):
            self._new_line()
            self._write('else:')
            self._change_indent(1)
            for statement in node.orelse:
                self.visit(statement)
            self._change_indent(-1)

    # While(expr test, stmt* body, stmt* orelse)
    def visit_While(self, node):
        self._new_line()
        self._write('while ')
        self.visit(node.test)
        self._write(':')
        self._change_indent(1)
        for statement in node.body:
            self.visit(statement)
        self._change_indent(-1)
        if getattr(node, 'orelse', None):
            self._new_line()
            self._write('else:')
            self._change_indent(1)
            for statement in node.orelse:
                self.visit(statement)
            self._change_indent(-1)

    # If(expr test, stmt* body, stmt* orelse)
    def visit_If(self, node):
        self._new_line()
        self._write('if ')
        self.visit(node.test)
        self._write(':')
        self._change_indent(1)
        for statement in node.body:
            self.visit(statement)
        self._change_indent(-1)
        if getattr(node, 'orelse', None):
            self._new_line()
            self._write('else:')
            self._change_indent(1)
            for statement in node.orelse:
                self.visit(statement)
            self._change_indent(-1)

    # With(expr context_expr, expr? optional_vars, stmt* body)
    def visit_With(self, node):
        self._new_line()
        self._write('with ')
        self.visit(node.context_expr)
        if getattr(node, 'optional_vars', None):
            self._write(' as ')
            self.visit(node.optional_vars)
        self._write(':')
        self._change_indent(1)
        for statement in node.body:
            self.visit(statement)
        self._change_indent(-1)

    # Raise(expr? type, expr? inst, expr? tback)
    def visit_Raise(self, node):
        self._new_line()
        self._write('raise')
        if not getattr(node, "type", None):
            exc = getattr(node, "exc", None)
            if exc is None:
                return
            self._write(' ')
            return self.visit(exc)
        self._write(' ')
        self.visit(node.type)
        if not node.inst:
            return
        self._write(', ')
        self.visit(node.inst)
        if not node.tback:
            return
        self._write(', ')
        self.visit(node.tback)

    # Try(stmt* body, excepthandler* handlers, stmt* orelse, stmt* finalbody)
    def visit_Try(self, node):
        self._new_line()
        self._write('try:')
        self._change_indent(1)
        for statement in node.body:
            self.visit(statement)
        self._change_indent(-1)
        if getattr(node, 'handlers', None):
            for handler in node.handlers:
                self.visit(handler)
        self._new_line()

        if getattr(node, 'orelse', None):
            self._write('else:')
            self._change_indent(1)
            for statement in node.orelse:
                self.visit(statement)
            self._change_indent(-1)

        if getattr(node, 'finalbody', None):
            self._new_line()
            self._write('finally:')
            self._change_indent(1)
            for statement in node.finalbody:
                self.visit(statement)
            self._change_indent(-1)

    # TryExcept(stmt* body, excepthandler* handlers, stmt* orelse)
    def visit_TryExcept(self, node):
        self._new_line()
        self._write('try:')
        self._change_indent(1)
        for statement in node.body:
            self.visit(statement)
        self._change_indent(-1)
        if getattr(node, 'handlers', None):
            for handler in node.handlers:
                self.visit(handler)
        self._new_line()
        if getattr(node, 'orelse', None):
            self._write('else:')
            self._change_indent(1)
            for statement in node.orelse:
                self.visit(statement)
            self._change_indent(-1)

    # excepthandler = (expr? type, expr? name, stmt* body)
    def visit_ExceptHandler(self, node):
        self._new_line()
        self._write('except')
        if getattr(node, 'type', None):
            self._write(' ')
            self.visit(node.type)
        if getattr(node, 'name', None):
            if sys.version_info[0] == 2:
                assert getattr(node, 'type', None)
                self._write(', ')
            else:
                self._write(' as ')
            self.visit(node.name)
        self._write(':')
        self._change_indent(1)
        for statement in node.body:
            self.visit(statement)
        self._change_indent(-1)
    visit_excepthandler = visit_ExceptHandler

    # TryFinally(stmt* body, stmt* finalbody)
    def visit_TryFinally(self, node):
        self._new_line()
        self._write('try:')
        self._change_indent(1)
        for statement in node.body:
            self.visit(statement)
        self._change_indent(-1)

        if getattr(node, 'finalbody', None):
            self._new_line()
            self._write('finally:')
            self._change_indent(1)
            for statement in node.finalbody:
                self.visit(statement)
            self._change_indent(-1)

    # Assert(expr test, expr? msg)
    def visit_Assert(self, node):
        self._new_line()
        self._write('assert ')
        self.visit(node.test)
        if getattr(node, 'msg', None):
            self._write(', ')
            self.visit(node.msg)

    def visit_alias(self, node):
        self._write(node.name)
        if getattr(node, 'asname', None):
            self._write(' as ')
            self._write(node.asname)

    # Import(alias* names)
    def visit_Import(self, node):
        self._new_line()
        self._write('import ')
        self.visit(node.names[0])
        for name in node.names[1:]:
            self._write(', ')
            self.visit(name)

    # ImportFrom(identifier module, alias* names, int? level)
    def visit_ImportFrom(self, node):
        self._new_line()
        self._write('from ')
        if node.level:
            self._write('.' * node.level)
        self._write(node.module)
        self._write(' import ')
        self.visit(node.names[0])
        for name in node.names[1:]:
            self._write(', ')
            self.visit(name)

    # Exec(expr body, expr? globals, expr? locals)
    def visit_Exec(self, node):
        self._new_line()
        self._write('exec ')
        self.visit(node.body)
        if not node.globals:
            return
        self._write(', ')
        self.visit(node.globals)
        if not node.locals:
            return
        self._write(', ')
        self.visit(node.locals)

    # Global(identifier* names)
    def visit_Global(self, node):
        self._new_line()
        self._write('global ')
        self.visit(node.names[0])
        for name in node.names[1:]:
            self._write(', ')
            self.visit(name)

    # Expr(expr value)
    def visit_Expr(self, node):
        self._new_line()
        self.visit(node.value)

    # Pass
    def visit_Pass(self, node):
        self._new_line()
        self._write('pass')

    # Break
    def visit_Break(self, node):
        self._new_line()
        self._write('break')

    # Continue
    def visit_Continue(self, node):
        self._new_line()
        self._write('continue')

    ### EXPRESSIONS
    def with_parens(f):
        def _f(self, node):
            self._write('(')
            f(self, node)
            self._write(')')
        return _f

    bool_operators = {ast.And: 'and', ast.Or: 'or'}

    # BoolOp(boolop op, expr* values)
    @with_parens
    def visit_BoolOp(self, node):
        joiner = ' ' + self.bool_operators[node.op.__class__] + ' '
        self.visit(node.values[0])
        for value in node.values[1:]:
            self._write(joiner)
            self.visit(value)

    binary_operators = {
        ast.Add: '+',
        ast.Sub: '-',
        ast.Mult: '*',
        ast.Div: '/',
        ast.Mod: '%',
        ast.Pow: '**',
        ast.LShift: '<<',
        ast.RShift: '>>',
        ast.BitOr: '|',
        ast.BitXor: '^',
        ast.BitAnd: '&',
        ast.FloorDiv: '//'
    }

    # BinOp(expr left, operator op, expr right)
    @with_parens
    def visit_BinOp(self, node):
        self.visit(node.left)
        self._write(' ' + self.binary_operators[node.op.__class__] + ' ')
        self.visit(node.right)

    unary_operators = {
        ast.Invert: '~',
        ast.Not: 'not',
        ast.UAdd: '+',
        ast.USub: '-',
    }

    # UnaryOp(unaryop op, expr operand)
    def visit_UnaryOp(self, node):
        self._write(self.unary_operators[node.op.__class__] + ' ')
        self.visit(node.operand)

    # Lambda(arguments args, expr body)
    @with_parens
    def visit_Lambda(self, node):
        self._write('lambda ')
        self.visit(node.args)
        self._write(': ')
        self.visit(node.body)

    # IfExp(expr test, expr body, expr orelse)
    @with_parens
    def visit_IfExp(self, node):
        self.visit(node.body)
        self._write(' if ')
        self.visit(node.test)
        self._write(' else ')
        self.visit(node.orelse)

    # Dict(expr* keys, expr* values)
    def visit_Dict(self, node):
        self._write('{')
        for key, value in zip(node.keys, node.values):
            self.visit(key)
            self._write(': ')
            self.visit(value)
            self._write(', ')
        self._write('}')

    def visit_Set(self, node):
        self._write('{')
        elts = list(node.elts)
        last = elts.pop()
        for elt in elts:
            self.visit(elt)
            self._write(', ')
        self.visit(last)
        self._write('}')

    # ListComp(expr elt, comprehension* generators)
    def visit_ListComp(self, node):
        self._write('[')
        self.visit(node.elt)
        for generator in node.generators:
            # comprehension = (expr target, expr iter, expr* ifs)
            self._write(' for ')
            self.visit(generator.target)
            self._write(' in ')
            self.visit(generator.iter)
            for ifexpr in generator.ifs:
                self._write(' if ')
                self.visit(ifexpr)
        self._write(']')

    # GeneratorExp(expr elt, comprehension* generators)
    def visit_GeneratorExp(self, node):
        self._write('(')
        self.visit(node.elt)
        for generator in node.generators:
            # comprehension = (expr target, expr iter, expr* ifs)
            self._write(' for ')
            self.visit(generator.target)
            self._write(' in ')
            self.visit(generator.iter)
            for ifexpr in generator.ifs:
                self._write(' if ')
                self.visit(ifexpr)
        self._write(')')

    # Yield(expr? value)
    def visit_Yield(self, node):
        self._write('yield')
        if getattr(node, 'value', None):
            self._write(' ')
            self.visit(node.value)

    comparison_operators = {
        ast.Eq: '==',
        ast.NotEq: '!=',
        ast.Lt: '<',
        ast.LtE: '<=',
        ast.Gt: '>',
        ast.GtE: '>=',
        ast.Is: 'is',
        ast.IsNot: 'is not',
        ast.In: 'in',
        ast.NotIn: 'not in',
    }

    # Compare(expr left, cmpop* ops, expr* comparators)
    @with_parens
    def visit_Compare(self, node):
        self.visit(node.left)
        for op, comparator in zip(node.ops, node.comparators):
            self._write(' ' + self.comparison_operators[op.__class__] + ' ')
            self.visit(comparator)

    # Call(expr func, expr* args, keyword* keywords,
    #                         expr? starargs, expr? kwargs)
    def visit_Call(self, node):
        self.visit(node.func)
        self._write('(')
        first = True
        for arg in node.args:
            if not first:
                self._write(', ')
            first = False
            self.visit(arg)

        for keyword in node.keywords:
            if not first:
                self._write(', ')
            first = False
            # keyword = (identifier arg, expr value)
            self._write(keyword.arg)
            self._write('=')
            self.visit(keyword.value)
        if getattr(node, 'starargs', None):
            if not first:
                self._write(', ')
            first = False
            self._write('*')
            self.visit(node.starargs)

        if getattr(node, 'kwargs', None):
            if not first:
                self._write(', ')
            first = False
            self._write('**')
            self.visit(node.kwargs)
        self._write(')')

    # Repr(expr value)
    def visit_Repr(self, node):
        self._write('`')
        self.visit(node.value)
        self._write('`')

    # Num(object n)
    def visit_Num(self, node):
        self._write(repr(node.n))

    # Str(string s)
    def visit_Str(self, node):
        self._write(repr(node.s))

    # Attribute(expr value, identifier attr, expr_context ctx)
    def visit_Attribute(self, node):
        self.visit(node.value)
        self._write('.')
        self._write(node.attr)

    # Subscript(expr value, slice slice, expr_context ctx)
    def visit_Subscript(self, node):
        self.visit(node.value)
        self._write('[')

        def _process_slice(node):
            if isinstance(node, ast.Ellipsis):
                self._write('...')
            elif isinstance(node, ast.Slice):
                if getattr(node, 'lower', 'None'):
                    self.visit(node.lower)
                self._write(':')
                if getattr(node, 'upper', None):
                    self.visit(node.upper)
                if getattr(node, 'step', None):
                    self._write(':')
                    self.visit(node.step)
            elif isinstance(node, ast.Index):
                self.visit(node.value)
            elif isinstance(node, ast.ExtSlice):
                self.visit(node.dims[0])
                for dim in node.dims[1:]:
                    self._write(', ')
                    self.visit(dim)
            else:
                raise NotImplemented('Slice type not implemented')
        _process_slice(node.slice)
        self._write(']')

    # Name(identifier id, expr_context ctx)
    def visit_Name(self, node):
        self._write(node.id)

    # List(expr* elts, expr_context ctx)
    def visit_List(self, node):
        self._write('[')
        for elt in node.elts:
            self.visit(elt)
            self._write(', ')
        self._write(']')

    # Tuple(expr *elts, expr_context ctx)
    def visit_Tuple(self, node):
        self._write('(')
        for elt in node.elts:
            self.visit(elt)
            self._write(', ')
        self._write(')')

    # NameConstant(singleton value)
    def visit_NameConstant(self, node):
        self._write(str(node.value))

class AnnotationAwareVisitor(ast.NodeVisitor):
    def visit(self, node):
        annotation = node_annotations.get(node)
        if annotation is not None:
            assert hasattr(annotation, '_fields')
            node = annotation

        super(AnnotationAwareVisitor, self).visit(node)

    def apply_transform(self, node):
        if node not in node_annotations:
            result = self.transform(node)
            if result is not None and result is not node:
                node_annotations[node] = result


class NameLookupRewriteVisitor(AnnotationAwareVisitor):
    def __init__(self, transform):
        self.transform = transform
        self.transformed = set()
        self.scopes = [set()]

    def __call__(self, node):
        self.visit(node)
        return self.transformed

    def visit_Name(self, node):
        scope = self.scopes[-1]
        if isinstance(node.ctx, ast.Param):
            scope.add(node.id)
        elif node.id not in scope:
            self.transformed.add(node.id)
            self.apply_transform(node)

    def visit_FunctionDef(self, node):
        self.scopes[-1].add(node.name)

    def visit_alias(self, node):
        name = node.asname if node.asname is not None else node.name
        self.scopes[-1].add(name)

    def visit_Lambda(self, node):
        self.scopes.append(set())
        try:
            self.visit(node.args)
            self.visit(node.body)
        finally:
            self.scopes.pop()


class ItemLookupOnAttributeErrorVisitor(AnnotationAwareVisitor):
    def __init__(self, transform):
        self.transform = transform

    def visit_Attribute(self, node):
        self.generic_visit(node)
        self.apply_transform(node)

########NEW FILE########
__FILENAME__ = benchmark
import unittest
import time
import os
import re
from .utils import text_

re_amp = re.compile(r'&(?!([A-Za-z]+|#[0-9]+);)')

BIGTABLE_ZPT = """\
<table xmlns="http://www.w3.org/1999/xhtml"
xmlns:tal="http://xml.zope.org/namespaces/tal">
<tr tal:repeat="row python: options['table']">
<td tal:repeat="c python: row.values()">
<span tal:define="d python: c + 1"
tal:attributes="class python: 'column-' + str(d)"
tal:content="python: d" />
</td>
</tr>
</table>"""

MANY_STRINGS_ZPT = """\
<table xmlns="http://www.w3.org/1999/xhtml"
xmlns:tal="http://xml.zope.org/namespaces/tal">
<tr tal:repeat="i python: xrange(1000)">
<td tal:content="string: number ${i}" />
</tr>
</table>
"""

HELLO_WORLD_ZPT = """\
<html xmlns="http://www.w3.org/1999/xhtml"
xmlns:tal="http://xml.zope.org/namespaces/tal">
<body>
<h1>Hello, world!</h1>
</body>
</html>
"""

I18N_ZPT = """\
<html xmlns="http://www.w3.org/1999/xhtml"
xmlns:tal="http://xml.zope.org/namespaces/tal"
xmlns:i18n="http://xml.zope.org/namespaces/i18n">
  <body>
    <div tal:repeat="i python: xrange(10)">
      <div i18n:translate="">
        Hello world!
      </div>
      <div i18n:translate="hello_world">
        Hello world!
      </div>
      <div i18n:translate="">
        <sup>Hello world!</sup>
      </div>
    </div>
  </body>
</html>
"""


def benchmark(title):
    def decorator(f):
        def wrapper(*args):
            print(
                "==========================\n " \
                "%s\n==========================" % \
                title)
            return f(*args)
        return wrapper
    return decorator


def timing(func, *args, **kwargs):
    t1 = t2 = time.time()
    i = 0
    while t2 - t1 < 3:
        func(**kwargs)
        func(**kwargs)
        func(**kwargs)
        func(**kwargs)
        i += 4
        t2 = time.time()
    return float(10 * (t2 - t1)) / i


START = 0
END = 1
TAG = 2


def yield_tokens(table=None):
    index = []
    tag = index.append
    _re_amp = re_amp
    tag(START)
    yield "<", "html", "", ">\n"
    for r in table:
        tag(START)
        yield "<", "tr", "", ">\n"

        for c in r.values():
            d = c + 1
            tag(START)
            yield "<", "td", "", ">\n"

            _tmp5 = d
            if not isinstance(_tmp5, unicode):
                _tmp5 = str(_tmp5)
            if ('&' in _tmp5):
                if (';' in _tmp5):
                    _tmp5 = _re_amp.sub('&amp;', _tmp5)
                else:
                    _tmp5 = _tmp5.replace('&', '&amp;')
            if ('<' in _tmp5):
                _tmp5 = _tmp5.replace('<', '&lt;')
            if ('>' in _tmp5):
                _tmp5 = _tmp5.replace('>', '&gt;')
            if ('"' in _tmp5):
                _tmp5 = _tmp5.replace('"', '&quot;')
            _tmp5 = "column-%s" % _tmp5

            _tmp = d
            if (_tmp.__class__ not in (str, unicode, int, float, )):
                raise
            if (_tmp is not None):
                if not isinstance(_tmp, unicode):
                    _tmp = str(_tmp)
                if ('&' in _tmp):
                    if (';' in _tmp):
                        _tmp = _re_amp.sub('&amp;', _tmp)
                    else:
                        _tmp = _tmp.replace('&', '&amp;')
                if ('<' in _tmp):
                    _tmp = _tmp.replace('<', '&lt;')
                if ('>' in _tmp):
                    _tmp = _tmp.replace('>', '&gt;')
            tag(START)

            t = ["classicism"]

            yield "<", "span", " ", t[0], '="', _tmp5, '"', ">\n"
            tag(END)
            yield "</", "span", ">\n"
            tag(END)
            yield "</", "td", ">\n"
        tag(END)
        yield "</", "tr", ">\n"
    tag(END)
    yield "</", "html", ">\n"


def yield_tokens_dict_version(**kwargs):
    index = []
    tag = index.append
    _re_amp = re_amp
    tag(START)
    yield "<", "html", "", ">\n"

    for r in kwargs['table']:
        kwargs['r'] = r
        tag(START)
        yield "<", "tr", "", ">\n"

        for c in kwargs['r'].values():
            kwargs['d'] = c + 1
            tag(START)
            yield "<", "td", "", ">\n"

            _tmp5 = kwargs['d']
            if not isinstance(_tmp5, unicode):
                _tmp5 = str(_tmp5)
            if ('&' in _tmp5):
                if (';' in _tmp5):
                    _tmp5 = _re_amp.sub('&amp;', _tmp5)
                else:
                    _tmp5 = _tmp5.replace('&', '&amp;')
            if ('<' in _tmp5):
                _tmp5 = _tmp5.replace('<', '&lt;')
            if ('>' in _tmp5):
                _tmp5 = _tmp5.replace('>', '&gt;')
            if ('"' in _tmp5):
                _tmp5 = _tmp5.replace('"', '&quot;')
            _tmp5 = "column-%s" % _tmp5

            _tmp = kwargs['d']
            if (_tmp.__class__ not in (str, unicode, int, float, )):
                raise
            if (_tmp is not None):
                if not isinstance(_tmp, unicode):
                    _tmp = str(_tmp)
                if ('&' in _tmp):
                    if (';' in _tmp):
                        _tmp = _re_amp.sub('&amp;', _tmp)
                    else:
                        _tmp = _tmp.replace('&', '&amp;')
                if ('<' in _tmp):
                    _tmp = _tmp.replace('<', '&lt;')
                if ('>' in _tmp):
                    _tmp = _tmp.replace('>', '&gt;')
            tag(START)

            t = ["classicism"]

            yield "<", "span", " ", t[0], '="', _tmp5, '"', ">\n"
            tag(END)
            yield "</", "span", ">\n"
            tag(END)
            yield "</", "td", ">\n"
        tag(END)
        yield "</", "tr", ">\n"
    tag(END)
    yield "</", "html", ">\n"


def yield_stream(table=None):
    _re_amp = re_amp
    yield START, ("html", "", "\n"), None
    for r in table:
        yield START, ("tr", "", "\n"), None

        for c in r.values():
            d = c + 1
            yield START, ("td", "", "\n"), None

            _tmp5 = d
            if not isinstance(_tmp5, unicode):
                _tmp5 = str(_tmp5)
            if ('&' in _tmp5):
                if (';' in _tmp5):
                    _tmp5 = _re_amp.sub('&amp;', _tmp5)
                else:
                    _tmp5 = _tmp5.replace('&', '&amp;')
            if ('<' in _tmp5):
                _tmp5 = _tmp5.replace('<', '&lt;')
            if ('>' in _tmp5):
                _tmp5 = _tmp5.replace('>', '&gt;')
            if ('"' in _tmp5):
                _tmp5 = _tmp5.replace('"', '&quot;')
            _tmp5 = "column-%s" % _tmp5

            _tmp = d
            if (_tmp.__class__ not in (str, unicode, int, float, )):
                raise
            if (_tmp is not None):
                if not isinstance(_tmp, unicode):
                    _tmp = str(_tmp)
                if ('&' in _tmp):
                    if (';' in _tmp):
                        _tmp = _re_amp.sub('&amp;', _tmp)
                    else:
                        _tmp = _tmp.replace('&', '&amp;')
                if ('<' in _tmp):
                    _tmp = _tmp.replace('<', '&lt;')
                if ('>' in _tmp):
                    _tmp = _tmp.replace('>', '&gt;')
            yield START, ("span", "", _tmp, " ", "class", _tmp5), None

            yield END, ("span", "", "\n"), None
            yield END, ("td", "", "\n"), None
        yield END, ("tr", "", "\n"), None
    yield END, ("html", "", "\n"), None

from itertools import chain


def bigtable_python_tokens(table=None, renderer=None):
    iterable = renderer(table=table)
    stream = chain(*iterable)
    return "".join(stream)


def bigtable_python_stream(table=None, renderer=None):
    stream = renderer(table=table)
    return "".join(stream_output(stream))


def bigtable_python_stream_with_filter(table=None, renderer=None):
    stream = renderer(table=table)
    return "".join(stream_output(uppercase_filter(stream)))


def uppercase_filter(stream):
    for kind, data, pos in stream:
        if kind is START:
            data = (data[0], data[1], data[2].upper(),) + data[3:]
        elif kind is END:
            data = (data[0], data[1], data[2].upper())
        elif kind is TAG:
            raise NotImplemented
        yield kind, data, pos


def stream_output(stream):
    for kind, data, pos in stream:
        if kind is START:
            tag = data[0]
            yield "<%s" % tag
            l = len(data)

            # optimize for common cases
            if l == 3:
                pass
            elif l == 6:
                yield '%s%s="%s"' % (data[3], data[4], data[5])
            else:
                i = 3
                while i < l:
                    yield '%s%s="%s"' % (data[i], data[i + 1], data[i + 2])
                    i += 3
            yield "%s>%s" % (data[1], data[2])
        elif kind is END:
            yield "</%s%s>%s" % data
        elif kind is TAG:
            raise NotImplemented


class Benchmarks(unittest.TestCase):
    table = [dict(a=1, b=2, c=3, d=4, e=5, f=6, g=7, h=8, i=9, j=10) \
             for x in range(1000)]

    def setUp(self):
        # set up i18n component
        from zope.i18n import translate
        from zope.i18n.interfaces import INegotiator
        from zope.i18n.interfaces import ITranslationDomain
        from zope.i18n.negotiator import Negotiator
        from zope.i18n.simpletranslationdomain import SimpleTranslationDomain
        from zope.i18n.tests.test_negotiator import Env
        from zope.tales.tales import Context

        self.env = Env(('klingon', 'da', 'en', 'fr', 'no'))

        class ZopeI18NContext(Context):

            def translate(self, msgid, domain=None, context=None,
                          mapping=None, default=None):
                context = self.vars['options']['env']
                return translate(msgid, domain, mapping,
                                 context=context, default=default)

        def _getContext(self, contexts=None, **kwcontexts):
            if contexts is not None:
                if kwcontexts:
                    kwcontexts.update(contexts)
                else:
                    kwcontexts = contexts
            return ZopeI18NContext(self, kwcontexts)

        def _pt_getEngineContext(namespace):
            self = namespace['template']
            engine = self.pt_getEngine()
            return _getContext(engine, namespace)

        import zope.component
        zope.component.provideUtility(Negotiator(), INegotiator)
        catalog = SimpleTranslationDomain('domain')
        zope.component.provideUtility(catalog, ITranslationDomain, 'domain')
        self.files = os.path.abspath(os.path.join(__file__, '..', 'input'))

    @staticmethod
    def _chameleon(body, **kwargs):
        from .zpt.template import PageTemplate
        return PageTemplate(body, **kwargs)

    @staticmethod
    def _zope(body):
        from zope.pagetemplate.pagetemplatefile import PageTemplate
        template = PageTemplate()
        template.pt_edit(body, 'text/xhtml')
        return template

    @benchmark(text_("BIGTABLE [python]"))
    def test_bigtable(self):
        options = {'table': self.table}

        t_chameleon = timing(self._chameleon(BIGTABLE_ZPT), options=options)
        print("chameleon:         %7.2f" % t_chameleon)

        t_chameleon_utf8 = timing(
            self._chameleon(BIGTABLE_ZPT, encoding='utf-8'), options=options)
        print("chameleon (utf-8): %7.2f" % t_chameleon_utf8)

        t_tokens = timing(
            bigtable_python_tokens, table=self.table, renderer=yield_tokens)
        print("token:             %7.2f" % t_tokens)

        t_tokens_dict_version = timing(
            bigtable_python_tokens, table=self.table,
            renderer=yield_tokens_dict_version)
        print("token (dict):      %7.2f" % t_tokens_dict_version)

        t_stream = timing(
            bigtable_python_stream, table=self.table, renderer=yield_stream)
        print("stream:            %7.2f" % t_stream)

        t_zope = timing(self._zope(BIGTABLE_ZPT), table=self.table)
        print("zope.pagetemplate: %7.2f" % t_zope)
        print("                  %7.1fX" % (t_zope / t_chameleon))

        print("--------------------------")
        print("check: %d vs %d" % (
            len(self._chameleon(BIGTABLE_ZPT)(options=options)),
            len(self._zope(BIGTABLE_ZPT)(table=self.table))))
        print("--------------------------")

    @benchmark(text_("MANY STRINGS [python]"))
    def test_many_strings(self):
        t_chameleon = timing(self._chameleon(MANY_STRINGS_ZPT))
        print("chameleon:         %7.2f" % t_chameleon)
        t_zope = timing(self._zope(MANY_STRINGS_ZPT))
        print("zope.pagetemplate: %7.2f" % t_zope)
        print("                  %7.1fX" % (t_zope / t_chameleon))

        print("--------------------------")
        print("check: %d vs %d" % (
            len(self._chameleon(MANY_STRINGS_ZPT)()),
            len(self._zope(MANY_STRINGS_ZPT)())))
        print("--------------------------")

    @benchmark(text_("HELLO WORLD"))
    def test_hello_world(self):
        t_chameleon = timing(self._chameleon(HELLO_WORLD_ZPT)) * 1000
        print("chameleon:         %7.2f" % t_chameleon)
        t_zope = timing(self._zope(HELLO_WORLD_ZPT)) * 1000
        print("zope.pagetemplate: %7.2f" % t_zope)
        print("                  %7.1fX" % (t_zope / t_chameleon))

        print("--------------------------")
        print("check: %d vs %d" % (
            len(self._chameleon(HELLO_WORLD_ZPT)()),
            len(self._zope(HELLO_WORLD_ZPT)())))
        print("--------------------------")

    @benchmark(text_("I18N"))
    def test_i18n(self):
        from zope.i18n import translate
        t_chameleon = timing(
            self._chameleon(I18N_ZPT),
            translate=translate,
            language="klingon") * 1000
        print("chameleon:         %7.2f" % t_chameleon)
        t_zope = timing(self._zope(I18N_ZPT), env=self.env) * 1000
        print("zope.pagetemplate: %7.2f" % t_zope)
        print("                  %7.1fX" % (t_zope / t_chameleon))

    @benchmark(text_("COMPILATION"))
    def test_compilation(self):
        template = self._chameleon(HELLO_WORLD_ZPT)

        def chameleon_cook_and_render(template=template):
            template.cook(HELLO_WORLD_ZPT)
            template()

        t_chameleon = timing(chameleon_cook_and_render) * 1000
        print("chameleon:         %7.2f" % t_chameleon)

        template = self._zope(HELLO_WORLD_ZPT)

        def zope_cook_and_render(templte=template):
            template._cook()
            template()

        t_zope = timing(zope_cook_and_render) * 1000
        print("zope.pagetemplate: %7.2f" % t_zope)
        print("                    %0.3fX" % (t_zope / t_chameleon))


def start():
    result = unittest.TestResult()
    test = unittest.makeSuite(Benchmarks)
    test.run(result)

    for error in result.errors:
        print("Error in %s...\n" % error[0])
        print(error[1])

    for failure in result.failures:
        print("Failure in %s...\n" % failure[0])
        print(failure[1])

########NEW FILE########
__FILENAME__ = codegen
try:
    import ast
except ImportError:
    from chameleon import ast25 as ast

import inspect
import textwrap
import types
import copy

try:
    import __builtin__ as builtins
except ImportError:
    import builtins

reverse_builtin_map = {}
for name, value in builtins.__dict__.items():
    try:
        hash(value)
    except TypeError:
        continue

    reverse_builtin_map[value] = name

try:
    basestring
except NameError:
    basestring = str

from .astutil import ASTCodeGenerator
from .astutil import load
from .astutil import store
from .astutil import parse
from .astutil import Builtin
from .astutil import Symbol
from .astutil import node_annotations

from .exc import CompilationError


try:
    NATIVE_NUMBERS = int, float, long, bool
except NameError:
    NATIVE_NUMBERS = int, float, bool


def template(function, mode='exec', **kw):
    def wrapper(*vargs, **kwargs):
        symbols = dict(zip(args, vargs + defaults))
        symbols.update(kwargs)

        class Visitor(ast.NodeVisitor):
            def visit_FunctionDef(self, node):
                self.generic_visit(node)

                name = symbols.get(node.name, self)
                if name is not self:
                    node_annotations[node] = ast.FunctionDef(
                        name=name,
                        args=node.args,
                        body=node.body,
                        decorator_list=getattr(node, "decorator_list", []),
                        )

            def visit_Name(self, node):
                value = symbols.get(node.id, self)
                if value is not self:
                    if isinstance(value, basestring):
                        value = load(value)
                    if isinstance(value, type) or value in reverse_builtin_map:
                        name = reverse_builtin_map.get(value)
                        if name is not None:
                            value = Builtin(name)
                        else:
                            value = Symbol(value)

                    assert node not in node_annotations
                    assert hasattr(value, '_fields')
                    node_annotations[node] = value

        expr = parse(source, mode=mode)
        if not isinstance(function, basestring):
            expr = expr.body[0]

        Visitor().visit(expr)
        return expr.body

    if isinstance(function, basestring):
        source = function
        defaults = args = ()
        return wrapper(**kw)

    source = textwrap.dedent(inspect.getsource(function))
    argspec = inspect.getargspec(function)
    args = argspec[0]
    defaults = argspec[3] or ()
    return wrapper


class TemplateCodeGenerator(ASTCodeGenerator):
    """Extends the standard Python code generator class with handlers
    for the helper node classes:

    - Symbol (an importable value)
    - Static (value that can be made global)
    - Builtin (from the builtins module)
    - Marker (short-hand for a unique static object)

    """

    names = ()

    def __init__(self, tree):
        self.imports = {}
        self.defines = {}
        self.markers = {}

        # Generate code
        super(TemplateCodeGenerator, self).__init__(tree)

    def visit_Module(self, node):
        super(TemplateCodeGenerator, self).visit_Module(node)

        # Make sure we terminate the line printer
        self.flush()

        # Clear lines array for import visits
        body = self.lines
        self.lines = []

        while self.defines:
            name, node = self.defines.popitem()
            assignment = ast.Assign(targets=[store(name)], value=node)
            self.visit(assignment)

        # Make sure we terminate the line printer
        self.flush()

        # Clear lines array for import visits
        defines = self.lines
        self.lines = []

        while self.imports:
            value, node = self.imports.popitem()

            if isinstance(value, types.ModuleType):
                stmt = ast.Import(
                    names=[ast.alias(name=value.__name__, asname=node.id)])
            elif hasattr(value, '__name__'):
                path = reverse_builtin_map.get(value)
                if path is None:
                    path = value.__module__
                    name = value.__name__
                stmt = ast.ImportFrom(
                    module=path,
                    names=[ast.alias(name=name, asname=node.id)],
                    level=0,
                )
            else:
                raise TypeError(value)

            self.visit(stmt)

        # Clear last import
        self.flush()

        # Stich together lines
        self.lines += defines + body

    def define(self, name, node):
        assert node is not None
        value = self.defines.get(name)

        if value is node:
            pass
        elif value is None:
            self.defines[name] = node
        else:
            raise CompilationError(
                "Duplicate symbol name for define.", name)

        return load(name)

    def require(self, value):
        if value is None:
            return load("None")

        if isinstance(value, NATIVE_NUMBERS):
            return ast.Num(value)

        node = self.imports.get(value)
        if node is None:
            # we come up with a unique symbol based on the class name
            name = "_%s" % getattr(value, '__name__', str(value)).\
                   rsplit('.', 1)[-1]
            node = load(name)
            self.imports[value] = store(node.id)

        return node

    def visit(self, node):
        annotation = node_annotations.get(node)
        if annotation is None:
            super(TemplateCodeGenerator, self).visit(node)
        else:
            self.visit(annotation)

    def visit_Comment(self, node):
        if node.stmt is None:
            self._new_line()
        else:
            self.visit(node.stmt)

        for line in node.text.replace('\r', '\n').split('\n'):
            self._new_line()
            self._write("%s#%s" % (node.space, line))

    def visit_Builtin(self, node):
        name = load(node.id)
        self.visit(name)

    def visit_Symbol(self, node):
        node = self.require(node.value)
        self.visit(node)

    def visit_Static(self, node):
        if node.name is None:
            name = "_static_%s" % str(id(node.value)).replace('-', '_')
        else:
            name = node.name

        node = self.define(name, node.value)
        self.visit(node)

########NEW FILE########
__FILENAME__ = compiler
import re
import cgi
import sys
import itertools
import logging
import threading
import functools
import collections
import pickle
import textwrap

from .astutil import load
from .astutil import store
from .astutil import param
from .astutil import swap
from .astutil import subscript
from .astutil import node_annotations
from .astutil import annotated
from .astutil import NameLookupRewriteVisitor
from .astutil import Comment
from .astutil import Symbol
from .astutil import Builtin
from .astutil import Static

from .codegen import TemplateCodeGenerator
from .codegen import template

from .tal import ErrorInfo
from .tal import NAME
from .i18n import simple_translate

from .nodes import Text
from .nodes import Value
from .nodes import Substitution
from .nodes import Assignment
from .nodes import Module
from .nodes import Context

from .tokenize import Token
from .config import DEBUG_MODE
from .exc import TranslationError
from .exc import ExpressionError
from .parser import groupdict

from .utils import DebuggingOutputStream
from .utils import char2entity
from .utils import ListDictProxy
from .utils import native_string
from .utils import byte_string
from .utils import string_type
from .utils import unicode_string
from .utils import version
from .utils import ast
from .utils import safe_native
from .utils import builtins
from .utils import decode_htmlentities


if version >= (3, 0, 0):
    long = int

log = logging.getLogger('chameleon.compiler')

COMPILER_INTERNALS_OR_DISALLOWED = set([
    "econtext",
    "rcontext",
    "str",
    "int",
    "float",
    "long",
    "len",
    "None",
    "True",
    "False",
    "RuntimeError",
    ])


RE_MANGLE = re.compile('[^\w_]')
RE_NAME = re.compile('^%s$' % NAME)

if DEBUG_MODE:
    LIST = template("cls()", cls=DebuggingOutputStream, mode="eval")
else:
    LIST = template("[]", mode="eval")


def identifier(prefix, suffix=None):
    return "__%s_%s" % (prefix, mangle(suffix or id(prefix)))


def mangle(string):
    return RE_MANGLE.sub('_', str(string)).replace('\n', '').replace('-', '_')


def load_econtext(name):
    return template("getitem(KEY)", KEY=ast.Str(s=name), mode="eval")


def store_econtext(name):
    name = native_string(name)
    return subscript(name, load("econtext"), ast.Store())


def store_rcontext(name):
    name = native_string(name)
    return subscript(name, load("rcontext"), ast.Store())


def set_error(token, exception):
    try:
        line, column = token.location
        filename = token.filename
    except AttributeError:
        line, column = 0, 0
        filename = "<string>"

    string = safe_native(token)

    return template(
        "rcontext.setdefault('__error__', [])."
        "append((string, line, col, src, exc))",
        string=ast.Str(s=string),
        line=ast.Num(n=line),
        col=ast.Num(n=column),
        src=ast.Str(s=filename),
        sys=Symbol(sys),
        exc=exception,
        )


def try_except_wrap(stmts, token):
    exception = template(
        "exc_info()[1]", exc_info=Symbol(sys.exc_info), mode="eval"
        )

    body = set_error(token, exception) + template("raise")

    return ast.TryExcept(
        body=stmts,
        handlers=[ast.ExceptHandler(body=body)],
        )


@template
def emit_node(node):  # pragma: no cover
    __append(node)


@template
def emit_node_if_non_trivial(node):  # pragma: no cover
    if node is not None:
        __append(node)


@template
def emit_bool(target, s, default_marker=None,
                 default=None):  # pragma: no cover
    if target is default_marker:
        target = default
    elif target:
        target = s
    else:
        target = None


@template
def emit_convert(
    target, encoded=byte_string, str=unicode_string,
    long=long, type=type,
    default_marker=None, default=None):  # pragma: no cover
    if target is None:
        pass
    elif target is default_marker:
        target = default
    else:
        __tt = type(target)

        if __tt is int or __tt is float or __tt is long:
            target = str(target)
        elif __tt is encoded:
            target = decode(target)
        elif __tt is not str:
            try:
                target = target.__html__
            except AttributeError:
                __converted = convert(target)
                target = str(target) if target is __converted else __converted
            else:
                target = target()


@template
def emit_func_convert(
    func, encoded=byte_string, str=unicode_string,
    long=long, type=type):  # pragma: no cover
    def func(target):
        if target is None:
            return

        __tt = type(target)

        if __tt is int or __tt is float or __tt is long:
            target = str(target)

        elif __tt is encoded:
            target = decode(target)

        elif __tt is not str:
            try:
                target = target.__html__
            except AttributeError:
                __converted = convert(target)
                target = str(target) if target is __converted else __converted
            else:
                target = target()

        return target


@template
def emit_translate(target, msgid, default=None):  # pragma: no cover
    target = translate(msgid, default=default, domain=__i18n_domain)


@template
def emit_func_convert_and_escape(
    func, str=unicode_string, long=long,
    type=type, encoded=byte_string):  # pragma: no cover

    def func(target, quote, quote_entity, default, default_marker):
        if target is None:
            return

        if target is default_marker:
            return default

        __tt = type(target)

        if __tt is int or __tt is float or __tt is long:
            target = str(target)
        else:
            if __tt is encoded:
                target = decode(target)
            elif __tt is not str:
                try:
                    target = target.__html__
                except:
                    __converted = convert(target)
                    target = str(target) if target is __converted \
                             else __converted
                else:
                    return target()

            if target is not None:
                try:
                    escape = __re_needs_escape(target) is not None
                except TypeError:
                    pass
                else:
                    if escape:
                        # Character escape
                        if '&' in target:
                            target = target.replace('&', '&amp;')
                        if '<' in target:
                            target = target.replace('<', '&lt;')
                        if '>' in target:
                            target = target.replace('>', '&gt;')
                        if quote is not None and quote in target:
                            target = target.replace(quote, quote_entity)

        return target


class Interpolator(object):
    braces_required_regex = re.compile(
        r'(?<!\\)\$({(?P<expression>.*)})',
        re.DOTALL)

    braces_optional_regex = re.compile(
        r'(?<!\\)\$({(?P<expression>.*)}|(?P<variable>[A-Za-z][A-Za-z0-9_]*))',
        re.DOTALL)

    def __init__(self, expression, braces_required, translate=False):
        self.expression = expression
        self.regex = self.braces_required_regex if braces_required else \
                     self.braces_optional_regex
        self.translate = translate

    def __call__(self, name, engine):
        """The strategy is to find possible expression strings and
        call the ``validate`` function of the parser to validate.

        For every possible starting point, the longest possible
        expression is tried first, then the second longest and so
        forth.

        Example 1:

          ${'expressions use the ${<expression>} format'}

        The entire expression is attempted first and it is also the
        only one that validates.

        Example 2:

          ${'Hello'} ${'world!'}

        Validation of the longest possible expression (the entire
        string) will fail, while the second round of attempts,
        ``${'Hello'}`` and ``${'world!'}`` respectively, validate.

        """

        body = []
        nodes = []
        text = self.expression

        expr_map = {}
        translate = self.translate

        while text:
            matched = text
            m = self.regex.search(matched)
            if m is None:
                nodes.append(ast.Str(s=text))
                break

            part = text[:m.start()]
            text = text[m.start():]

            if part:
                node = ast.Str(s=part)
                nodes.append(node)

            if not body:
                target = name
            else:
                target = store("%s_%d" % (name.id, text.pos))

            while True:
                d = groupdict(m, matched)
                string = d["expression"] or d.get("variable") or ""
                string = decode_htmlentities(string)

                if string:
                    try:
                        compiler = engine.parse(string)
                        body += compiler.assign_text(target)
                    except ExpressionError:
                        matched = matched[m.start():m.end() - 1]
                        m = self.regex.search(matched)
                        if m is None:
                            raise

                        continue
                else:
                    s = m.group()
                    assign = ast.Assign(targets=[target], value=ast.Str(s=s))
                    body += [assign]

                break

            # If one or more expressions are not simple names, we
            # disable translation.
            if RE_NAME.match(string) is None:
                translate = False

            # if this is the first expression, use the provided
            # assignment name; otherwise, generate one (here based
            # on the string position)
            node = load(target.id)
            nodes.append(node)

            expr_map[node] = safe_native(string)

            text = text[len(m.group()):]

        if len(nodes) == 1:
            target = nodes[0]

            if translate and isinstance(target, ast.Str):
                target = template(
                    "translate(msgid, domain=__i18n_domain, context=econtext)",
                    msgid=target, mode="eval",
                    )
        else:
            if translate:
                formatting_string = ""
                keys = []
                values = []

                for node in nodes:
                    if isinstance(node, ast.Str):
                        formatting_string += node.s
                    else:
                        string = expr_map[node]
                        formatting_string += "${%s}" % string
                        keys.append(ast.Str(s=string))
                        values.append(node)

                target = template(
                    "translate(msgid, mapping=mapping, domain=__i18n_domain, context=econtext)",
                    msgid=ast.Str(s=formatting_string),
                    mapping=ast.Dict(keys=keys, values=values),
                    mode="eval"
                    )
            else:
                nodes = [
                    template(
                        "NODE if NODE is not None else ''",
                        NODE=node, mode="eval"
                        )
                    for node in nodes
                    ]

                target = ast.BinOp(
                    left=ast.Str(s="%s" * len(nodes)),
                    op=ast.Mod(),
                    right=ast.Tuple(elts=nodes, ctx=ast.Load()))

        body += [ast.Assign(targets=[name], value=target)]
        return body


class ExpressionEngine(object):
    """Expression engine.

    This test demonstrates how to configure and invoke the engine.

    >>> from chameleon import tales
    >>> parser = tales.ExpressionParser({
    ...     'python': tales.PythonExpr,
    ...     'not': tales.NotExpr,
    ...     'exists': tales.ExistsExpr,
    ...     'string': tales.StringExpr,
    ...     }, 'python')

    >>> engine = ExpressionEngine(parser)

    An expression evaluation function:

    >>> eval = lambda expression: tales.test(
    ...     tales.IdentityExpr(expression), engine)

    We have provided 'python' as the default expression type. This
    means that when no prefix is given, the expression is evaluated as
    a Python expression:

    >>> eval('not False')
    True

    Note that the ``type`` prefixes bind left. If ``not`` and
    ``exits`` are two expression type prefixes, consider the
    following::

    >>> eval('not: exists: int(None)')
    True

    The pipe operator binds right. In the following example, but
    arguments are evaluated against ``not: exists: ``.

    >>> eval('not: exists: help')
    False

    >>> eval('string:test ${1}${2}')
    'test 12'

    """

    supported_char_escape_set = set(('&', '<', '>'))

    def __init__(self, parser, char_escape=(),
                 default=None, default_marker=None):
        self._parser = parser
        self._char_escape = char_escape
        self._default = default
        self._default_marker = default_marker

    def __call__(self, string, target):
        # BBB: This method is deprecated. Instead, a call should first
        # be made to ``parse`` and then one of the assignment methods
        # ("value" or "text").

        compiler = self.parse(string)
        return compiler(string, target)

    def parse(self, string):
        expression = self._parser(string)
        compiler = self.get_compiler(expression, string)
        return ExpressionCompiler(compiler, self)

    def get_compiler(self, expression, string):
        def compiler(target, engine, result_type=None, *args):
            stmts = expression(target, engine)

            if result_type is not None:
                method = getattr(self, '_convert_%s' % result_type)
                steps = method(target, *args)
                stmts.extend(steps)

            return [try_except_wrap(stmts, string)]

        return compiler

    def _convert_bool(self, target, s):
        """Converts value given by ``target`` to a string ``s`` if the
        target is a true value, otherwise ``None``.
        """

        return emit_bool(
            target, ast.Str(s=s),
            default=self._default,
            default_marker=self._default_marker
            )

    def _convert_text(self, target):
        """Converts value given by ``target`` to text."""

        if self._char_escape:
            # This is a cop-out - we really only support a very select
            # set of escape characters
            other = set(self._char_escape) - self.supported_char_escape_set

            if other:
                for supported in '"', '\'', '':
                    if supported in self._char_escape:
                        quote = supported
                        break
                else:
                    raise RuntimeError(
                        "Unsupported escape set: %s." % repr(self._char_escape)
                        )
            else:
                quote = '\0'

            entity = char2entity(quote or '\0')

            return template(
                "TARGET = __quote(TARGET, QUOTE, Q_ENTITY, DEFAULT, MARKER)",
                TARGET=target,
                QUOTE=ast.Str(s=quote),
                Q_ENTITY=ast.Str(s=entity),
                DEFAULT=self._default,
                MARKER=self._default_marker,
                )

        return emit_convert(
            target,
            default=self._default,
            default_marker=self._default_marker,
            )


class ExpressionCompiler(object):
    def __init__(self, compiler, engine):
        self.compiler = compiler
        self.engine = engine

    def assign_bool(self, target, s):
        return self.compiler(target, self.engine, "bool", s)

    def assign_text(self, target):
        return self.compiler(target, self.engine, "text")

    def assign_value(self, target):
        return self.compiler(target, self.engine)


class ExpressionEvaluator(object):
    """Evaluates dynamic expression.

    This is not particularly efficient, but supported for legacy
    applications.

    >>> from chameleon import tales
    >>> parser = tales.ExpressionParser({'python': tales.PythonExpr}, 'python')
    >>> engine = functools.partial(ExpressionEngine, parser)

    >>> evaluate = ExpressionEvaluator(engine, {
    ...     'foo': 'bar',
    ...     })

    The evaluation function is passed the local and remote context,
    the expression type and finally the expression.

    >>> evaluate({'boo': 'baz'}, {}, 'python', 'foo + boo')
    'barbaz'

    The cache is now primed:

    >>> evaluate({'boo': 'baz'}, {}, 'python', 'foo + boo')
    'barbaz'

    Note that the call method supports currying of the expression
    argument:

    >>> python = evaluate({'boo': 'baz'}, {}, 'python')
    >>> python('foo + boo')
    'barbaz'

    """

    __slots__ = "_engine", "_cache", "_names", "_builtins"

    def __init__(self, engine, builtins):
        self._engine = engine
        self._names, self._builtins = zip(*builtins.items())
        self._cache = {}

    def __call__(self, econtext, rcontext, expression_type, string=None):
        if string is None:
            return functools.partial(
                self.__call__, econtext, rcontext, expression_type
                )

        expression = "%s:%s" % (expression_type, string)

        try:
            evaluate = self._cache[expression]
        except KeyError:
            assignment = Assignment(["_result"], expression, True)
            module = Module("evaluate", Context(assignment))

            compiler = Compiler(
                self._engine, module, ('econtext', 'rcontext') + self._names
                )

            env = {}
            exec(compiler.code, env)
            evaluate = self._cache[expression] = env["evaluate"]

        evaluate(econtext, rcontext, *self._builtins)
        return econtext['_result']


class NameTransform(object):
    """
    >>> nt = NameTransform(
    ...     set(('foo', 'bar', )), {'boo': 'boz'},
    ...     ('econtext', ),
    ... )

    >>> def test(node):
    ...     rewritten = nt(node)
    ...     module = ast.Module([ast.fix_missing_locations(rewritten)])
    ...     codegen = TemplateCodeGenerator(module)
    ...     return codegen.code

    Any odd name:

    >>> test(load('frobnitz'))
    "getitem('frobnitz')"

    A 'builtin' name will first be looked up via ``get`` allowing fall
    back to the global builtin value:

    >>> test(load('foo'))
    "get('foo', foo)"

    Internal names (with two leading underscores) are left alone:

    >>> test(load('__internal'))
    '__internal'

    Compiler internals or disallowed names:

    >>> test(load('econtext'))
    'econtext'

    Aliased names:

    >>> test(load('boo'))
    'boz'

    """

    def __init__(self, builtins, aliases, internals):
        self.builtins = builtins
        self.aliases = aliases
        self.internals = internals

    def __call__(self, node):
        name = node.id

        # Don't rewrite names that begin with an underscore; they are
        # internal and can be assumed to be locally defined. This
        # policy really should be part of the template program, not
        # defined here in the compiler.
        if name.startswith('__') or name in self.internals:
            return node

        if isinstance(node.ctx, ast.Store):
            return store_econtext(name)

        aliased = self.aliases.get(name)
        if aliased is not None:
            return load(aliased)

        # If the name is a Python global, first try acquiring it from
        # the dynamic context, then fall back to the global.
        if name in self.builtins:
            return template(
                "get(key, name)",
                mode="eval",
                key=ast.Str(s=name),
                name=load(name),
                )

        # Otherwise, simply acquire it from the dynamic context.
        return load_econtext(name)


class ExpressionTransform(object):
    """Internal wrapper to transform expression nodes into assignment
    statements.

    The node input may use the provided expression engine, but other
    expression node types are supported such as ``Builtin`` which
    simply resolves a built-in name.

    Used internally be the compiler.
    """

    loads_symbol = Symbol(pickle.loads)

    def __init__(self, engine_factory, cache, visitor, strict=True):
        self.engine_factory = engine_factory
        self.cache = cache
        self.strict = strict
        self.visitor = visitor

    def __call__(self, expression, target):
        if isinstance(target, string_type):
            target = store(target)

        try:
            stmts = self.translate(expression, target)
        except ExpressionError:
            if self.strict:
                raise

            exc = sys.exc_info()[1]
            p = pickle.dumps(exc)

            stmts = template(
                "__exc = loads(p)", loads=self.loads_symbol, p=ast.Str(s=p)
                )

            token = Token(exc.token, exc.offset, filename=exc.filename)

            stmts += set_error(token, load("__exc"))
            stmts += [ast.Raise(exc=load("__exc"))]

        # Apply visitor to each statement
        for stmt in stmts:
            self.visitor(stmt)

        return stmts

    def translate(self, expression, target):
        if isinstance(target, string_type):
            target = store(target)

        cached = self.cache.get(expression)

        if cached is not None:
            stmts = [ast.Assign(targets=[target], value=cached)]
        elif isinstance(expression, ast.expr):
            stmts = [ast.Assign(targets=[target], value=expression)]
        else:
            # The engine interface supports simple strings, which
            # default to expression nodes
            if isinstance(expression, string_type):
                expression = Value(expression, True)

            kind = type(expression).__name__
            visitor = getattr(self, "visit_%s" % kind)
            stmts = visitor(expression, target)

            # Add comment
            target_id = getattr(target, "id", target)
            comment = Comment(" %r -> %s" % (expression, target_id))
            stmts.insert(0, comment)

        return stmts

    def visit_Value(self, node, target):
        engine = self.engine_factory()
        compiler = engine.parse(node.value)
        return compiler.assign_value(target)

    def visit_Copy(self, node, target):
        return self.translate(node.expression, target)

    def visit_Default(self, node, target):
        value = annotated(node.marker)
        return [ast.Assign(targets=[target], value=value)]

    def visit_Substitution(self, node, target):
        engine = self.engine_factory(
            char_escape=node.char_escape,
            default=node.default,
            )
        compiler = engine.parse(node.value)
        return compiler.assign_text(target)

    def visit_Negate(self, node, target):
        return self.translate(node.value, target) + \
               template("TARGET = not TARGET", TARGET=target)

    def visit_Identity(self, node, target):
        expression = self.translate(node.expression, "__expression")
        value = self.translate(node.value, "__value")

        return expression + value + \
               template("TARGET = __expression is __value", TARGET=target)

    def visit_Equality(self, node, target):
        expression = self.translate(node.expression, "__expression")
        value = self.translate(node.value, "__value")

        return expression + value + \
               template("TARGET = __expression == __value", TARGET=target)

    def visit_Boolean(self, node, target):
        engine = self.engine_factory()
        compiler = engine.parse(node.value)
        return compiler.assign_bool(target, node.s)

    def visit_Interpolation(self, node, target):
        expr = node.value
        if isinstance(expr, Substitution):
            engine = self.engine_factory(
                char_escape=expr.char_escape,
                default=expr.default,
                )
        elif isinstance(expr, Value):
            engine = self.engine_factory()
        else:
            raise RuntimeError("Bad value: %r." % node.value)

        interpolator = Interpolator(
            expr.value, node.braces_required, node.translation
            )

        compiler = engine.get_compiler(interpolator, expr.value)
        return compiler(target, engine)

    def visit_Translate(self, node, target):
        if node.msgid is not None:
            msgid = ast.Str(s=node.msgid)
        else:
            msgid = target
        return self.translate(node.node, target) + \
               emit_translate(target, msgid, default=target)

    def visit_Static(self, node, target):
        value = annotated(node)
        return [ast.Assign(targets=[target], value=value)]

    def visit_Builtin(self, node, target):
        value = annotated(node)
        return [ast.Assign(targets=[target], value=value)]


class Compiler(object):
    """Generic compiler class.

    Iterates through nodes and yields Python statements which form a
    template program.
    """

    exceptions = NameError, \
                 ValueError, \
                 AttributeError, \
                 LookupError, \
                 TypeError

    defaults = {
        'translate': Symbol(simple_translate),
        'decode': Builtin("str"),
        'convert': Builtin("str"),
        }

    lock = threading.Lock()

    global_builtins = set(builtins.__dict__)

    def __init__(self, engine_factory, node, builtins={}, strict=True):
        self._scopes = [set()]
        self._expression_cache = {}
        self._translations = []
        self._builtins = builtins
        self._aliases = [{}]
        self._macros = []
        self._current_slot = []

        internals = COMPILER_INTERNALS_OR_DISALLOWED | \
                    set(self.defaults)

        transform = NameTransform(
            self.global_builtins | set(builtins),
            ListDictProxy(self._aliases),
            internals,
            )

        self._visitor = visitor = NameLookupRewriteVisitor(transform)

        self._engine = ExpressionTransform(
            engine_factory,
            self._expression_cache,
            visitor,
            strict=strict,
            )

        if isinstance(node_annotations, dict):
            self.lock.acquire()
            backup = node_annotations.copy()
        else:
            backup = None

        try:
            module = ast.Module([])
            module.body += self.visit(node)
            ast.fix_missing_locations(module)
            generator = TemplateCodeGenerator(module)
        finally:
            if backup is not None:
                node_annotations.clear()
                node_annotations.update(backup)
                self.lock.release()

        self.code = generator.code

    def visit(self, node):
        if node is None:
            return ()
        kind = type(node).__name__
        visitor = getattr(self, "visit_%s" % kind)
        iterator = visitor(node)
        return list(iterator)

    def visit_Sequence(self, node):
        for item in node.items:
            for stmt in self.visit(item):
                yield stmt

    def visit_Element(self, node):
        for stmt in self.visit(node.start):
            yield stmt

        for stmt in self.visit(node.content):
            yield stmt

        if node.end is not None:
            for stmt in self.visit(node.end):
                yield stmt

    def visit_Module(self, node):
        body = []

        body += template("import re")
        body += template("import functools")
        body += template("from itertools import chain as __chain")
        body += template("__marker = object()")
        body += template(
            r"g_re_amp = re.compile(r'&(?!([A-Za-z]+|#[0-9]+);)')"
        )
        body += template(
            r"g_re_needs_escape = re.compile(r'[&<>\"\']').search")

        body += template(
            r"__re_whitespace = "
            r"functools.partial(re.compile('\s+').sub, ' ')",
        )

        # Visit module content
        program = self.visit(node.program)

        body += [ast.FunctionDef(
            name=node.name, args=ast.arguments(
                args=[param(b) for b in self._builtins],
                defaults=(),
                ),
            body=program
            )]

        return body

    def visit_MacroProgram(self, node):
        functions = []

        # Visit defined macros
        macros = getattr(node, "macros", ())
        names = []
        for macro in macros:
            stmts = self.visit(macro)
            function = stmts[-1]
            names.append(function.name)
            functions += stmts

        # Return function dictionary
        functions += [ast.Return(value=ast.Dict(
            keys=[ast.Str(s=name) for name in names],
            values=[load(name) for name in names],
            ))]

        return functions

    def visit_Context(self, node):
        return template("getitem = econtext.__getitem__") + \
               template("get = econtext.get") + \
               self.visit(node.node)

    def visit_Macro(self, node):
        body = []

        # Initialization
        body += template("__append = __stream.append")
        body += template("__re_amp = g_re_amp")
        body += template("__re_needs_escape = g_re_needs_escape")

        body += emit_func_convert("__convert")
        body += emit_func_convert_and_escape("__quote")

        # Resolve defaults
        for name in self.defaults:
            body += template(
                "NAME = econtext[KEY]",
                NAME=name, KEY=ast.Str(s="__" + name)
            )

        # Internal set of defined slots
        self._slots = set()

        # Visit macro body
        nodes = itertools.chain(*tuple(map(self.visit, node.body)))

        # Slot resolution
        for name in self._slots:
            body += template(
                "try: NAME = econtext[KEY].pop()\n"
                "except: NAME = None",
                KEY=ast.Str(s=name), NAME=store(name))

        # Append visited nodes
        body += nodes

        function_name = "render" if node.name is None else \
                        "render_%s" % mangle(node.name)

        function = ast.FunctionDef(
            name=function_name, args=ast.arguments(
                args=[
                    param("__stream"),
                    param("econtext"),
                    param("rcontext"),
                    param("__i18n_domain"),
                    ],
                defaults=[load("None")],
            ),
            body=body
            )

        yield function

    def visit_Text(self, node):
        return emit_node(ast.Str(s=node.value))

    def visit_Domain(self, node):
        backup = "__previous_i18n_domain_%s" % mangle(id(node))
        return template("BACKUP = __i18n_domain", BACKUP=backup) + \
               template("__i18n_domain = NAME", NAME=ast.Str(s=node.name)) + \
               self.visit(node.node) + \
               template("__i18n_domain = BACKUP", BACKUP=backup)

    def visit_OnError(self, node):
        body = []

        fallback = identifier("__fallback")
        body += template("fallback = len(__stream)", fallback=fallback)

        self._enter_assignment((node.name, ))
        fallback_body = self.visit(node.fallback)
        self._leave_assignment((node.name, ))

        error_assignment = template(
            "econtext[key] = cls(__exc, rcontext['__error__'][-1][1:3])",
            cls=ErrorInfo,
            key=ast.Str(s=node.name),
            )

        body += [ast.TryExcept(
            body=self.visit(node.node),
            handlers=[ast.ExceptHandler(
                type=ast.Tuple(elts=[Builtin("Exception")], ctx=ast.Load()),
                name=store("__exc"),
                body=(error_assignment + \
                      template("del __stream[fallback:]", fallback=fallback) + \
                      fallback_body
                      ),
                )]
            )]

        return body

    def visit_Content(self, node):
        name = "__content"
        body = self._engine(node.expression, store(name))

        if node.translate:
            body += emit_translate(name, name)

        if node.char_escape:
            body += template(
                "NAME=__quote(NAME, None, '\255', None, None)",
                NAME=name,
                )
        else:
            body += template("NAME = __convert(NAME)", NAME=name)

        body += template("if NAME is not None: __append(NAME)", NAME=name)

        return body

    def visit_Interpolation(self, node):
        name = identifier("content")
        return self._engine(node, name) + \
               emit_node_if_non_trivial(name)

    def visit_Alias(self, node):
        assert len(node.names) == 1
        name = node.names[0]
        target = self._aliases[-1][name] = identifier(name, id(node))
        return self._engine(node.expression, target)

    def visit_Assignment(self, node):
        for name in node.names:
            if name in COMPILER_INTERNALS_OR_DISALLOWED:
                raise TranslationError(
                    "Name disallowed by compiler.", name
                    )

            if name.startswith('__'):
                raise TranslationError(
                    "Name disallowed by compiler (double underscore).",
                    name
                    )

        assignment = self._engine(node.expression, store("__value"))

        if len(node.names) != 1:
            target = ast.Tuple(
                elts=[store_econtext(name) for name in node.names],
                ctx=ast.Store(),
            )
        else:
            target = store_econtext(node.names[0])

        assignment.append(ast.Assign(targets=[target], value=load("__value")))

        for name in node.names:
            if not node.local:
                assignment += template(
                    "rcontext[KEY] = __value", KEY=ast.Str(s=native_string(name))
                    )

        return assignment

    def visit_Define(self, node):
        scope = set(self._scopes[-1])
        self._scopes.append(scope)
        self._aliases.append(self._aliases[-1].copy())

        for assignment in node.assignments:
            if assignment.local:
                for stmt in self._enter_assignment(assignment.names):
                    yield stmt

            for stmt in self.visit(assignment):
                yield stmt

        for stmt in self.visit(node.node):
            yield stmt

        for assignment in node.assignments:
            if assignment.local:
                for stmt in self._leave_assignment(assignment.names):
                    yield stmt

        self._scopes.pop()
        self._aliases.pop()

    def visit_Omit(self, node):
        return self.visit_Condition(node)

    def visit_Condition(self, node):
        target = "__condition"
        assignment = self._engine(node.expression, target)

        assert assignment

        for stmt in assignment:
            yield stmt

        body = self.visit(node.node) or [ast.Pass()]

        orelse = getattr(node, "orelse", None)
        if orelse is not None:
            orelse = self.visit(orelse)

        test = load(target)

        yield ast.If(test=test, body=body, orelse=orelse)

    def visit_Translate(self, node):
        """Translation.

        Visit items and assign output to a default value.

        Finally, compile a translation expression and use either
        result or default.
        """

        body = []

        # Track the blocks of this translation
        self._translations.append(set())

        # Prepare new stream
        append = identifier("append", id(node))
        stream = identifier("stream", id(node))
        body += template("s = new_list", s=stream, new_list=LIST) + \
                template("a = s.append", a=append, s=stream)

        # Visit body to generate the message body
        code = self.visit(node.node)
        swap(ast.Suite(body=code), load(append), "__append")
        body += code

        # Reduce white space and assign as message id
        msgid = identifier("msgid", id(node))
        body += template(
            "msgid = __re_whitespace(''.join(stream)).strip()",
            msgid=msgid, stream=stream
        )

        default = msgid

        # Compute translation block mapping if applicable
        names = self._translations[-1]
        if names:
            keys = []
            values = []

            for name in names:
                stream, append = self._get_translation_identifiers(name)
                keys.append(ast.Str(s=name))
                values.append(load(stream))

                # Initialize value
                body.insert(
                    0, ast.Assign(
                        targets=[store(stream)],
                        value=ast.Str(s=native_string(""))))

            mapping = ast.Dict(keys=keys, values=values)
        else:
            mapping = None

        # if this translation node has a name, use it as the message id
        if node.msgid:
            msgid = ast.Str(s=node.msgid)

        # emit the translation expression
        body += template(
            "if msgid: __append(translate("
            "msgid, mapping=mapping, default=default, domain=__i18n_domain, context=econtext))",
            msgid=msgid, default=default, mapping=mapping
            )

        # pop away translation block reference
        self._translations.pop()

        return body

    def visit_Start(self, node):
        try:
            line, column = node.prefix.location
        except AttributeError:
            line, column = 0, 0

        yield Comment(
            " %s%s ... (%d:%d)\n"
            " --------------------------------------------------------" % (
                node.prefix, node.name, line, column))

        if node.attributes:
            for stmt in emit_node(ast.Str(s=node.prefix + node.name)):
                yield stmt

            for stmt in self.visit(node.attributes):
                yield stmt

            for stmt in emit_node(ast.Str(s=node.suffix)):
                yield stmt
        else:
            for stmt in emit_node(
                ast.Str(s=node.prefix + node.name + node.suffix)):
                yield stmt

    def visit_End(self, node):
        for stmt in emit_node(ast.Str(
            s=node.prefix + node.name + node.space + node.suffix)):
            yield stmt

    def visit_Attribute(self, node):
        attr_format = (node.space + node.name + node.eq +
                       node.quote + "%s" + node.quote)

        filter_args = list(map(self._engine.cache.get, node.filters))

        filter_condition = template(
            "NAME not in CHAIN",
            NAME=ast.Str(s=node.name),
            CHAIN=ast.Call(
                func=load("__chain"),
                args=filter_args,
                keywords=[],
                starargs=None,
                kwargs=None,
            ),
            mode="eval"
        )

        # Static attributes are just outputted directly
        if isinstance(node.expression, ast.Str):
            s = attr_format % node.expression.s
            if node.filters:
                return template(
                    "if C: __append(S)", C=filter_condition, S=ast.Str(s=s)
                )
            else:
                return template("__append(S)", S=ast.Str(s=s))

        target = identifier("attr", node.name)
        body = self._engine(node.expression, store(target))

        condition = template("TARGET is not None", TARGET=target, mode="eval")

        if node.filters:
            condition = ast.BoolOp(
                values=[condition, filter_condition],
                op=ast.And(),
            )

        return body + template(
            "if CONDITION: __append(FORMAT % TARGET)",
            FORMAT=ast.Str(s=attr_format),
            TARGET=target,
            CONDITION=condition,
        )

    def visit_DictAttributes(self, node):
        target = identifier("attr", id(node))
        body = self._engine(node.expression, store(target))

        exclude = Static(template(
            "set(LIST)", LIST=ast.List(
                elts=[ast.Str(s=name) for name in node.exclude],
                ctx=ast.Load(),
            ), mode="eval"
        ))

        body += template(
            "for name, value in TARGET.items():\n  "
            "if name not in EXCLUDE and value is not None: __append("
            "' ' + name + '=' + QUOTE + "
            "QUOTE_FUNC(value, QUOTE, QUOTE_ENTITY, None, None) + QUOTE"
            ")",
            TARGET=target,
            EXCLUDE=exclude,
            QUOTE_FUNC="__quote",
            QUOTE=ast.Str(s=node.quote),
            QUOTE_ENTITY=ast.Str(s=char2entity(node.quote or '\0')),
            )

        return body

    def visit_Cache(self, node):
        body = []

        for expression in node.expressions:
            name = identifier("cache", id(expression))
            target = store(name)

            # Skip re-evaluation
            if self._expression_cache.get(expression):
                continue

            body += self._engine(expression, target)
            self._expression_cache[expression] = target

        body += self.visit(node.node)

        return body

    def visit_Cancel(self, node):
        body = []

        for expression in node.expressions:
            name = identifier("cache", id(expression))
            target = store(name)

            if not self._expression_cache.get(expression):
               continue

            body.append(ast.Assign([target], load("None")))

        body += self.visit(node.node)

        return body

    def visit_UseInternalMacro(self, node):
        if node.name is None:
            render = "render"
        else:
            render = "render_%s" % mangle(node.name)

        return template(
            "f(__stream, econtext.copy(), rcontext, __i18n_domain)",
            f=render) + \
            template("econtext.update(rcontext)")

    def visit_DefineSlot(self, node):
        name = "__slot_%s" % mangle(node.name)
        body = self.visit(node.node)

        self._slots.add(name)

        orelse = template(
            "SLOT(__stream, econtext.copy(), rcontext)",
            SLOT=name)
        test = ast.Compare(
            left=load(name),
            ops=[ast.Is()],
            comparators=[load("None")]
            )

        return [
            ast.If(test=test, body=body or [ast.Pass()], orelse=orelse)
            ]

    def visit_Name(self, node):
        """Translation name."""

        if not self._translations:
            raise TranslationError(
                "Not allowed outside of translation.", node.name)

        if node.name in self._translations[-1]:
            raise TranslationError(
                "Duplicate translation name: %s.", node.name)

        self._translations[-1].add(node.name)
        body = []

        # prepare new stream
        stream, append = self._get_translation_identifiers(node.name)
        body += template("s = new_list", s=stream, new_list=LIST) + \
                template("a = s.append", a=append, s=stream)

        # generate code
        code = self.visit(node.node)
        swap(ast.Suite(body=code), load(append), "__append")
        body += code

        # output msgid
        text = Text('${%s}' % node.name)
        body += self.visit(text)

        # Concatenate stream
        body += template("stream = ''.join(stream)", stream=stream)

        return body

    def visit_CodeBlock(self, node):
        stmts = template(textwrap.dedent(node.source.strip('\n')))

        for stmt in stmts:
            self._visitor(stmt)

        return [try_except_wrap(stmts, node.source)]

    def visit_UseExternalMacro(self, node):
        self._macros.append(node.extend)

        callbacks = []
        for slot in node.slots:
            key = "__slot_%s" % mangle(slot.name)
            fun = "__fill_%s" % mangle(slot.name)

            self._current_slot.append(slot.name)

            body = template("getitem = econtext.__getitem__") + \
                   template("get = econtext.get") + \
                   self.visit(slot.node)

            assert self._current_slot.pop() == slot.name

            callbacks.append(
                ast.FunctionDef(
                    name=fun,
                    args=ast.arguments(
                        args=[
                            param("__stream"),
                            param("econtext"),
                            param("rcontext"),
                            param("__i18n_domain"),
                            ],
                        defaults=[load("__i18n_domain")],
                        ),
                    body=body or [ast.Pass()],
                ))

            key = ast.Str(s=key)

            assignment = template(
                "_slots = econtext[KEY] = DEQUE((NAME,))",
                KEY=key, NAME=fun, DEQUE=Symbol(collections.deque),
                )

            if node.extend:
                append = template("_slots.appendleft(NAME)", NAME=fun)

                assignment = [ast.TryExcept(
                    body=template("_slots = getitem(KEY)", KEY=key),
                    handlers=[ast.ExceptHandler(body=assignment)],
                    orelse=append,
                    )]

            callbacks.extend(assignment)

        assert self._macros.pop() == node.extend

        assignment = self._engine(node.expression, store("__macro"))

        return (
            callbacks + \
            assignment + \
            template(
                "__macro.include(__stream, econtext.copy(), " \
                "rcontext, __i18n_domain)") + \
            template("econtext.update(rcontext)")
            )

    def visit_Repeat(self, node):
        # Used for loop variable definition and restore
        self._scopes.append(set())

        # Variable assignment and repeat key for single- and
        # multi-variable repeat clause
        if node.local:
            contexts = "econtext",
        else:
            contexts = "econtext", "rcontext"

        for name in node.names:
            if name in COMPILER_INTERNALS_OR_DISALLOWED:
                raise TranslationError(
                    "Name disallowed by compiler.", name
                    )

        if len(node.names) > 1:
            targets = [
                ast.Tuple(elts=[
                    subscript(native_string(name), load(context), ast.Store())
                    for name in node.names], ctx=ast.Store())
                for context in contexts
                ]

            key = ast.Tuple(
                elts=[ast.Str(s=name) for name in node.names],
                ctx=ast.Load())
        else:
            name = node.names[0]
            targets = [
                subscript(native_string(name), load(context), ast.Store())
                for context in contexts
                ]

            key = ast.Str(s=node.names[0])

        index = identifier("__index", id(node))
        assignment = [ast.Assign(targets=targets, value=load("__item"))]

        # Make repeat assignment in outer loop
        names = node.names
        local = node.local

        outer = self._engine(node.expression, store("__iterator"))

        if local:
            outer[:] = list(self._enter_assignment(names)) + outer

        outer += template(
            "__iterator, INDEX = getitem('repeat')(key, __iterator)",
            key=key, INDEX=index
            )

        # Set a trivial default value for each name assigned to make
        # sure we assign a value even if the iteration is empty
        outer += [ast.Assign(
            targets=[store_econtext(name)
                     for name in node.names],
            value=load("None"))
              ]

        # Compute inner body
        inner = self.visit(node.node)

        # After each iteration, decrease the index
        inner += template("index -= 1", index=index)

        # For items up to N - 1, emit repeat whitespace
        inner += template(
            "if INDEX > 0: __append(WHITESPACE)",
            INDEX=index, WHITESPACE=ast.Str(s=node.whitespace)
            )

        # Main repeat loop
        outer += [ast.For(
            target=store("__item"),
            iter=load("__iterator"),
            body=assignment + inner,
            )]

        # Finally, clean up assignment if it's local
        if outer:
            outer += self._leave_assignment(names)

        self._scopes.pop()

        return outer

    def _get_translation_identifiers(self, name):
        assert self._translations
        prefix = str(id(self._translations[-1])).replace('-', '_')
        stream = identifier("stream_%s" % prefix, name)
        append = identifier("append_%s" % prefix, name)
        return stream, append

    def _enter_assignment(self, names):
        for name in names:
            for stmt in template(
                "BACKUP = get(KEY, __marker)",
                BACKUP=identifier("backup_%s" % name, id(names)),
                KEY=ast.Str(s=native_string(name)),
                ):
                yield stmt

    def _leave_assignment(self, names):
        for name in names:
            for stmt in template(
                "if BACKUP is __marker: del econtext[KEY]\n"
                "else:                 econtext[KEY] = BACKUP",
                BACKUP=identifier("backup_%s" % name, id(names)),
                KEY=ast.Str(s=native_string(name)),
                ):
                yield stmt

########NEW FILE########
__FILENAME__ = config
import os
import logging

log = logging.getLogger('chameleon.config')

# Define which values are read as true
TRUE = ('y', 'yes', 't', 'true', 'on', '1')

# If eager parsing is enabled, templates are parsed upon
# instantiation, rather than when first called upon; this mode is
# useful for verifying validity of templates across a project
EAGER_PARSING = os.environ.pop('CHAMELEON_EAGER', 'false')
EAGER_PARSING = EAGER_PARSING.lower() in TRUE

# Debug mode is mostly useful for debugging the template engine
# itself. When enabled, generated source code is written to disk to
# ease step-debugging and some log levels are lowered to increase
# output. Also, the generated source code is available in the
# ``source`` attribute of the template instance if compilation
# succeeded.
DEBUG_MODE = os.environ.pop('CHAMELEON_DEBUG', 'false')
DEBUG_MODE = DEBUG_MODE.lower() in TRUE

# If a cache directory is specified, template source code will be
# persisted on disk and reloaded between sessions
path = os.environ.pop('CHAMELEON_CACHE', None)
if path is not None:
    CACHE_DIRECTORY = os.path.abspath(path)
    if not os.path.exists(CACHE_DIRECTORY):
        raise ValueError(
            "Cache directory does not exist: %s." % CACHE_DIRECTORY
            )
    log.info("directory cache: %s." % CACHE_DIRECTORY)
else:
    CACHE_DIRECTORY = None

# When auto-reload is enabled, templates are reloaded on file change.
AUTO_RELOAD = os.environ.pop('CHAMELEON_RELOAD', 'false')
AUTO_RELOAD = AUTO_RELOAD.lower() in TRUE

for key in os.environ:
    if key.lower().startswith('chameleon'):
        log.warn("unknown environment variable set: \"%s\"." % key)

# This is the slice length of the expression displayed in the
# formatted exception string
SOURCE_EXPRESSION_MARKER_LENGTH = 60

########NEW FILE########
__FILENAME__ = exc
# -*- coding: utf-8 -*-

import traceback

from .utils import format_kwargs
from .utils import safe_native
from .tokenize import Token
from .config import SOURCE_EXPRESSION_MARKER_LENGTH as LENGTH


def compute_source_marker(line, column, expression, size):
    """Computes source marker location string.

    >>> def test(l, c, e, s):
    ...     s, marker = compute_source_marker(l, c, e, s)
    ...     out = s + '\\n' + marker
    ...
    ...     # Replace dot with middle-dot to work around doctest ellipsis
    ...     print(out.replace('...', '···'))

    >>> test('foo bar', 4, 'bar', 7)
    foo bar
        ^^^

    >>> test('foo ${bar}', 4, 'bar', 10)
    foo ${bar}
          ^^^

    >>> test('  foo bar', 6, 'bar', 6)
    ··· oo bar
           ^^^

    >>> test('  foo bar baz  ', 6, 'bar', 6)
    ··· o bar ···
          ^^^

    The entire expression is always shown, even if ``size`` does not
    accomodate for it.

    >>> test('  foo bar baz  ', 6, 'bar baz', 10)
    ··· oo bar baz
           ^^^^^^^

    >>> test('      foo bar', 10, 'bar', 5)
    ··· o bar
          ^^^

    >>> test('      foo bar', 10, 'boo', 5)
    ··· o bar
          ^

    """

    s = line.lstrip()
    column -= len(line) - len(s)
    s = s.rstrip()

    try:
        i  = s[column:].index(expression)
    except ValueError:
        # If we can't find the expression
        # (this shouldn't happen), simply
        # use a standard size marker
        marker = "^"
    else:
        column += i
        marker = "^" * len(expression)

    if len(expression) > size:
        offset = column
        size = len(expression)
    else:
        window = (size - len(expression)) / 2.0
        offset = column - window
        offset -= min(3, max(0, column + window + len(expression) - len(s)))
        offset = int(offset)

    if offset > 0:
        s = s[offset:]
        r = s.lstrip()
        d = len(s) - len(r)
        s = "... " + r
        column += 4 - d
        column -= offset

        # This also adds to the displayed length
        size += 4

    if len(s) > size:
        s = s[:size].rstrip() + " ..."

    return s, column * " " + marker


def ellipsify(string, limit):
    if len(string) > limit:
        return "... " + string[-(limit - 4):]

    return string


def reconstruct_exc(cls, state):
    exc = Exception.__new__(cls)
    exc.__dict__ = state
    return exc


class TemplateError(Exception):
    """An error raised by Chameleon.

    >>> from chameleon.tokenize import Token
    >>> token = Token('token')
    >>> message = 'message'

    Make sure the exceptions can be copied:

    >>> from copy import copy
    >>> copy(TemplateError(message, token))
    TemplateError('message', 'token')

    And pickle/unpickled:

    >>> from pickle import dumps, loads
    >>> loads(dumps(TemplateError(message, token)))
    TemplateError('message', 'token')

    """

    def __init__(self, msg, token):
        if not isinstance(token, Token):
            token = Token(token, 0)

        self.msg = msg
        self.token = safe_native(token)
        self.offset = getattr(token, "pos", 0)
        self.filename = token.filename
        self.location = token.location

    def __copy__(self):
        inst = Exception.__new__(type(self))
        inst.__dict__ = self.__dict__.copy()
        return inst

    def __reduce__(self):
        return reconstruct_exc, (type(self), self.__dict__)

    def __str__(self):
        text = "%s\n\n" % self.msg
        text += " - String:     \"%s\"" % self.token

        if self.filename:
            text += "\n"
            text += " - Filename:   %s" % self.filename

        line, column = self.location
        text += "\n"
        text += " - Location:   (line %d: col %d)" % (line, column)

        return text

    def __repr__(self):
        try:
            return "%s('%s', '%s')" % (
                self.__class__.__name__, self.msg, self.token
                )
        except AttributeError:
            return object.__repr__(self)


class ParseError(TemplateError):
    """An error occurred during parsing.

    Indicates an error on the structural level.
    """


class CompilationError(TemplateError):
    """An error occurred during compilation.

    Indicates a general compilation error.
    """


class TranslationError(TemplateError):
    """An error occurred during translation.

    Indicates a general translation error.
    """


class LanguageError(CompilationError):
    """Language syntax error.

    Indicates a syntactical error due to incorrect usage of the
    template language.
    """


class ExpressionError(LanguageError):
    """An error occurred compiling an expression.

    Indicates a syntactical error in an expression.
    """


class ExceptionFormatter(object):
    def __init__(self, errors, econtext, rcontext):
        kwargs = rcontext.copy()
        kwargs.update(econtext)

        for name in tuple(kwargs):
            if name.startswith('__'):
                del kwargs[name]

        self._errors = errors
        self._kwargs = kwargs

    def __call__(self):
        # Format keyword arguments; consecutive arguments are indented
        # for readability
        try:
            formatted = format_kwargs(self._kwargs)
        except:
            # the ``pprint.pformat`` method calls the representation
            # method of the arguments; this may fail and since we're
            # already in an exception handler, there's no point in
            # pursuing this further
            formatted = ()

        for index, string in enumerate(formatted[1:]):
            formatted[index + 1] = " " * 15 + string

        out = []
        seen = set()

        for error in reversed(self._errors):
            expression, line, column, filename, exc = error

            if exc in seen:
                continue

            seen.add(exc)

            if isinstance(exc, UnicodeDecodeError):
                string = safe_native(exc.object)

                s, marker = compute_source_marker(
                    string, exc.start, string[exc.start:exc.end], LENGTH
                    )

                out.append(" - Stream:     %s" % s)
                out.append("               %s" % marker)

            _filename = ellipsify(filename, 60) if filename else "<string>"

            out.append(" - Expression: \"%s\"" % expression)
            out.append(" - Filename:   %s" % _filename)
            out.append(" - Location:   (line %d: col %d)" % (line, column))

            if filename and line and column:
                try:
                    f = open(filename, 'r')
                except IOError:
                    pass
                else:
                    try:
                        # Pick out source line and format marker
                        for i, l in enumerate(f):
                            if i + 1 == line:
                                s, marker = compute_source_marker(
                                    l, column, expression, LENGTH
                                    )

                                out.append(" - Source:     %s" % s)
                                out.append("               %s" % marker)
                                break
                    finally:
                        f.close()

        out.append(" - Arguments:  %s" % "\n".join(formatted))

        formatted = traceback.format_exception_only(type(exc), exc)[-1]
        formatted_class = "%s:" % type(exc).__name__

        if formatted.startswith(formatted_class):
            formatted = formatted[len(formatted_class):].lstrip()

        return "\n".join(map(safe_native, [formatted] + out))

########NEW FILE########
__FILENAME__ = i18n
##############################################################################
#
# Copyright (c) 2001, 2002 Zope Foundation and Contributors.
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

import re

from .exc import CompilationError
from .utils import unicode_string

NAME_RE = r"[a-zA-Z][-a-zA-Z0-9_]*"

WHITELIST = frozenset([
    "translate",
    "domain",
    "target",
    "source",
    "attributes",
    "data",
    "name",
    "mode",
    "xmlns",
    "xml"
    ])

_interp_regex = re.compile(r'(?<!\$)(\$(?:(%(n)s)|{(%(n)s)}))'
    % ({'n': NAME_RE}))


try:  # pragma: no cover
    str = unicode
except NameError:
    pass

# BBB: The ``fast_translate`` function here is kept for backwards
# compatibility reasons. Do not use!

try:  # pragma: no cover
    from zope.i18n import interpolate
    from zope.i18n import translate
    from zope.i18nmessageid import Message
except ImportError:   # pragma: no cover
    pass
else:   # pragma: no cover
    def fast_translate(msgid, domain=None, mapping=None, context=None,
                       target_language=None, default=None):
        if msgid is None:
            return

        if target_language is not None or context is not None:
            result = translate(
                msgid, domain=domain, mapping=mapping, context=context,
                target_language=target_language, default=default)
            if result != msgid:
                return result

        if isinstance(msgid, Message):
            default = msgid.default
            mapping = msgid.mapping

        if default is None:
            default = str(msgid)

        if not isinstance(default, basestring):
            return default

        return interpolate(default, mapping)


def simple_translate(msgid, domain=None, mapping=None, context=None,
                   target_language=None, default=None):
    if default is None:
        default = getattr(msgid, "default", msgid)

    if mapping is None:
        mapping = getattr(msgid, "mapping", None)

    if mapping:
        def replace(match):
            whole, param1, param2 = match.groups()
            return unicode_string(mapping.get(param1 or param2, whole))
        return _interp_regex.sub(replace, default)

    return default


def parse_attributes(attrs, xml=True):
    d = {}

    # filter out empty items, eg:
    # i18n:attributes="value msgid; name msgid2;"
    # would result in 3 items where the last one is empty
    attrs = [spec for spec in attrs.split(";") if spec]

    for spec in attrs:
        if ',' in spec:
            raise CompilationError(
                "Attribute must not contain comma. Use semicolon to "
                "list multiple attributes", spec
                )
        parts = spec.split()
        if len(parts) == 2:
            attr, msgid = parts
        elif len(parts) == 1:
            attr = parts[0]
            msgid = None
        else:
            raise CompilationError(
                "Illegal i18n:attributes specification.", spec)
        if not xml:
            attr = attr.lower()
        attr = attr.strip()
        if attr in d:
            raise CompilationError(
                "Attribute may only be specified once in i18n:attributes", attr)
        d[attr] = msgid

    return d

########NEW FILE########
__FILENAME__ = interfaces
from zope.interface import Interface
from zope.interface import Attribute


class ITALExpressionErrorInfo(Interface):

    type = Attribute("type",
                     "The exception class.")

    value = Attribute("value",
                      "The exception instance.")

    lineno = Attribute("lineno",
                       "The line number the error occurred on in the source.")

    offset = Attribute("offset",
                       "The character offset at which the error occurred.")


class ITALIterator(Interface):  # pragma: no cover
    """A TAL iterator

    Not to be confused with a Python iterator.
    """

    def next():
        """Advance to the next value in the iteration, if possible

        Return a true value if it was possible to advance and return
        a false value otherwise.
        """


class ITALESIterator(ITALIterator):  # pragma: no cover
    """TAL Iterator provided by TALES

    Values of this iterator are assigned to items in the repeat namespace.

    For example, with a TAL statement like: tal:repeat="item items",
    an iterator will be assigned to "repeat/item".  The iterator
    provides a number of handy methods useful in writing TAL loops.

    The results are undefined of calling any of the methods except
    'length' before the first iteration.
    """

    def index():
        """Return the position (starting with "0") within the iteration
        """

    def number():
        """Return the position (starting with "1") within the iteration
        """

    def even():
        """Return whether the current position is even
        """

    def odd():
        """Return whether the current position is odd
        """

    def parity():
        """Return 'odd' or 'even' depending on the position's parity

        Useful for assigning CSS class names to table rows.
        """

    def start():
        """Return whether the current position is the first position
        """

    def end():
        """Return whether the current position is the last position
        """

    def letter():
        """Return the position (starting with "a") within the iteration
        """

    def Letter():
        """Return the position (starting with "A") within the iteration
        """

    def roman():
        """Return the position (starting with "i") within the iteration
        """

    def Roman():
        """Return the position (starting with "I") within the iteration
        """

    def item():
        """Return the item at the current position
        """

    def length():
        """Return the length of the sequence

        Note that this may fail if the TAL iterator was created on a Python
        iterator.
        """

########NEW FILE########
__FILENAME__ = loader
import functools
import imp
import logging
import os
import py_compile
import shutil
import sys
import tempfile
import warnings
import pkg_resources

log = logging.getLogger('chameleon.loader')

from .utils import string_type
from .utils import encode_string


def cache(func):
    def load(self, *args, **kwargs):
        template = self.registry.get(args)
        if template is None:
            self.registry[args] = template = func(self, *args, **kwargs)
        return template
    return load


def abspath_from_asset_spec(spec):
    pname, filename = spec.split(':', 1)
    return pkg_resources.resource_filename(pname, filename)

if os.name == "nt":
    def abspath_from_asset_spec(spec, f=abspath_from_asset_spec):
        if spec[1] == ":":
            return spec
        return f(spec)


class TemplateLoader(object):
    """Template loader class.

    To load templates using relative filenames, pass a sequence of
    paths (or a single path) as ``search_path``.

    To apply a default filename extension to inputs which do not have
    an extension already (i.e. no dot), provide this as
    ``default_extension`` (e.g. ``'.pt'``).

    Additional keyword-arguments will be passed on to the template
    constructor.
    """

    default_extension = None

    def __init__(self, search_path=None, default_extension=None, **kwargs):
        if search_path is None:
            search_path = []
        if isinstance(search_path, string_type):
            search_path = [search_path]
        if default_extension is not None:
            self.default_extension = ".%s" % default_extension.lstrip('.')
        self.search_path = search_path
        self.registry = {}
        self.kwargs = kwargs

    @cache
    def load(self, spec, cls=None):
        if cls is None:
            raise ValueError("Unbound template loader.")

        spec = spec.strip()

        if self.default_extension is not None and '.' not in spec:
            spec += self.default_extension

        if ':' in spec:
            spec = abspath_from_asset_spec(spec)

        if os.path.isabs(spec):
            return cls(spec, **self.kwargs)

        for path in self.search_path:
            path = os.path.join(path, spec)
            if os.path.exists(path):
                return cls(path, **self.kwargs)

        raise ValueError("Template not found: %s." % spec)

    def bind(self, cls):
        return functools.partial(self.load, cls=cls)


class MemoryLoader(object):
    def build(self, source, filename):
        code = compile(source, filename, 'exec')
        env = {}
        exec(code, env)
        return env

    def get(self, name):
        return None


class ModuleLoader(object):
    def __init__(self, path, remove=False):
        self.path = path
        self.remove = remove

    def __del__(self, shutil=shutil):
        if not self.remove:
            return
        try:
            shutil.rmtree(self.path)
        except:
            warnings.warn("Could not clean up temporary file path: %s" % (self.path,))

    def get(self, filename):
        path = os.path.join(self.path, filename)
        if os.path.exists(path):
            log.debug("loading module from cache: %s." % filename)
            base, ext = os.path.splitext(filename)
            return self._load(base, path)
        else:
            log.debug('cache miss: %s' % filename)

    def build(self, source, filename):
        imp.acquire_lock()
        try:
            d = self.get(filename)
            if d is not None:
                return d

            base, ext = os.path.splitext(filename)
            name = os.path.join(self.path, base + ".py")

            log.debug("writing source to disk (%d bytes)." % len(source))
            fd, fn = tempfile.mkstemp(prefix=base, suffix='.tmp', dir=self.path)
            temp = os.fdopen(fd, 'wb')
            encoded = source.encode('utf-8')
            header = encode_string("# -*- coding: utf-8 -*-" + "\n")

            try:
                try:
                    temp.write(header)
                    temp.write(encoded)
                finally:
                    temp.close()
            except:
                os.remove(fn)
                raise

            os.rename(fn, name)
            log.debug("compiling %s into byte-code..." % filename)
            py_compile.compile(name)

            return self._load(base, name)
        finally:
            imp.release_lock()

    def _load(self, base, filename):
        imp.acquire_lock()
        try:
            module = sys.modules.get(base)
            if module is None:
                f = open(filename, 'rb')
                try:
                    assert base not in sys.modules
                    module = imp.load_source(base, filename, f)
                finally:
                    f.close()
        finally:
            imp.release_lock()

        return module.__dict__

########NEW FILE########
__FILENAME__ = metal
##############################################################################
#
# Copyright (c) 2001, 2002 Zope Foundation and Contributors.
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

WHITELIST = frozenset([
    "define-macro",
    "extend-macro",
    "use-macro",
    "define-slot",
    "fill-slot",
    "xmlns",
    "xml"
    ])

########NEW FILE########
__FILENAME__ = namespaces
XML_NS = "http://www.w3.org/XML/1998/namespace"
XMLNS_NS = "http://www.w3.org/2000/xmlns/"
XHTML_NS = "http://www.w3.org/1999/xhtml"
TAL_NS = "http://xml.zope.org/namespaces/tal"
META_NS = "http://xml.zope.org/namespaces/meta"
METAL_NS = "http://xml.zope.org/namespaces/metal"
XI_NS = "http://www.w3.org/2001/XInclude"
I18N_NS = "http://xml.zope.org/namespaces/i18n"
PY_NS = "http://genshi.edgewall.org/"

########NEW FILE########
__FILENAME__ = nodes
from .astutil import Node


class UseExternalMacro(Node):
    """Extend external macro."""

    _fields = "expression", "slots", "extend"


class Sequence(Node):
    """Element sequence."""

    _fields = "items",

    def __nonzero__(self):
        return bool(self.items)


class Content(Node):
    """Content substitution."""

    _fields = "expression", "char_escape", "translate"


class Default(Node):
    """Represents a default value."""

    _fields = "marker",


class CodeBlock(Node):
    _fields = "source",


class Value(Node):
    """Expression object value."""

    _fields = "value",

    def __repr__(self):
        try:
            line, column = self.value.location
        except AttributeError:
            line, column = 0, 0

        return "<%s %r (%d:%d)>" % (
            type(self).__name__, self.value, line, column
            )


class Substitution(Value):
    """Expression value for text substitution."""

    _fields = "value", "char_escape", "default"

    default = None


class Boolean(Value):
    _fields = "value", "s"


class Negate(Node):
    """Wraps an expression with a negation."""

    _fields = "value",


class Element(Node):
    """XML element."""

    _fields = "start", "end", "content"


class DictAttributes(Node):
    """Element attributes from one or more Python dicts."""

    _fields = "expression", "char_escape", "quote", "exclude"


class Attribute(Node):
    """Element attribute."""

    _fields = "name", "expression", "quote", "eq", "space", "filters"


class Start(Node):
    """Start-tag."""

    _fields = "name", "prefix", "suffix", "attributes"


class End(Node):
    """End-tag."""

    _fields = "name", "space", "prefix", "suffix"


class Condition(Node):
    """Node visited only if some condition holds."""

    _fields = "expression", "node", "orelse"


class Identity(Node):
    """Condition expression that is true on identity."""

    _fields = "expression", "value"


class Equality(Node):
    """Condition expression that is true on equality."""

    _fields = "expression", "value"


class Cache(Node):
    """Cache (evaluate only once) the value of ``expression`` inside
    ``node``.
    """

    _fields = "expressions", "node"


class Cancel(Cache):
    pass


class Copy(Node):
    _fields = "expression",


class Assignment(Node):
    """Variable assignment."""

    _fields = "names", "expression", "local"


class Alias(Assignment):
    """Alias assignment.

    Note that ``expression`` should be a cached or global value.
    """

    local = False


class Define(Node):
    """Variable definition in scope."""

    _fields = "assignments", "node"


class Repeat(Assignment):
    """Iterate over provided assignment and repeat body."""

    _fields = "names", "expression", "local", "whitespace", "node"


class Macro(Node):
    """Macro definition."""

    _fields = "name", "body"


class Program(Node):
    _fields = "name", "body"


class Module(Node):
    _fields = "name", "program",


class Context(Node):
    _fields = "node",


class Text(Node):
    """Static text output."""

    _fields = "value",


class Interpolation(Text):
    """String interpolation output."""

    _fields = "value", "braces_required", "translation"


class Translate(Node):
    """Translate node."""

    _fields = "msgid", "node"


class Name(Node):
    """Translation name."""

    _fields = "name", "node"


class Domain(Node):
    """Update translation domain."""

    _fields = "name", "node"


class OnError(Node):
    _fields = "fallback", "name", "node"


class UseInternalMacro(Node):
    """Use internal macro (defined inside same program)."""

    _fields = "name",


class FillSlot(Node):
    """Fill a macro slot."""

    _fields = "name", "node"


class DefineSlot(Node):
    """Define a macro slot."""

    _fields = "name", "node"

########NEW FILE########
__FILENAME__ = parser
import re
import logging

try:
    from collections import OrderedDict
except ImportError:
    from ordereddict import OrderedDict

from .exc import ParseError
from .namespaces import XML_NS
from .tokenize import Token

match_tag_prefix_and_name = re.compile(
    r'^(?P<prefix></?)(?P<name>([^:\n ]+:)?[^ \n\t>/]+)'
    '(?P<suffix>(?P<space>\s*)/?>)?',
    re.UNICODE | re.DOTALL)
match_single_attribute = re.compile(
    r'(?P<space>\s+)(?!\d)'
    r'(?P<name>[^ =/>\n\t]+)'
    r'((?P<eq>\s*=\s*)'
    r'((?P<quote>[\'"])(?P<value>.*?)(?P=quote)|'
    r'(?P<alt_value>[^\s\'">/]+))|'
    r'(?P<simple_value>(?![ \\n\\t\\r]*=)))',
    re.UNICODE | re.DOTALL)
match_comment = re.compile(
    r'^<!--(?P<text>.*)-->$', re.DOTALL)
match_cdata = re.compile(
    r'^<!\[CDATA\[(?P<text>.*)\]>$', re.DOTALL)
match_declaration = re.compile(
    r'^<!(?P<text>[^>]+)>$', re.DOTALL)
match_processing_instruction = re.compile(
    r'^<\?(?P<name>\w+)(?P<text>.*?)\?>', re.DOTALL)
match_xml_declaration = re.compile(r'^<\?xml(?=[ /])', re.DOTALL)

log = logging.getLogger('chameleon.parser')


def substitute(regex, repl, token):
    if not isinstance(token, Token):
        token = Token(token)

    return Token(
        regex.sub(repl, token),
        token.pos,
        token.source,
        token.filename
        )


def groups(m, token):
    result = []
    for i, group in enumerate(m.groups()):
        if group is not None:
            j, k = m.span(i + 1)
            group = token[j:k]

        result.append(group)

    return tuple(result)


def groupdict(m, token):
    d = m.groupdict()
    for name, value in d.items():
        if value is not None:
            i, j = m.span(name)
            d[name] = token[i:j]

    return d


def match_tag(token, regex=match_tag_prefix_and_name):
    m = regex.match(token)
    d = groupdict(m, token)

    end = m.end()
    token = token[end:]

    attrs = d['attrs'] = []
    for m in match_single_attribute.finditer(token):
        attr = groupdict(m, token)
        alt_value = attr.pop('alt_value', None)
        if alt_value is not None:
            attr['value'] = alt_value
            attr['quote'] = ''
        simple_value = attr.pop('simple_value', None)
        if simple_value is not None:
            attr['quote'] = ''
            attr['value'] = ''
            attr['eq'] = ''
        attrs.append(attr)
        d['suffix'] = token[m.end():]

    return d


def parse_tag(token, namespace):
    node = match_tag(token)

    update_namespace(node['attrs'], namespace)

    if ':' in node['name']:
        prefix = node['name'].split(':')[0]
    else:
        prefix = None

    default = node['namespace'] = namespace.get(prefix, XML_NS)

    node['ns_attrs'] = unpack_attributes(
        node['attrs'], namespace, default)

    return node


def update_namespace(attributes, namespace):
    # possibly update namespaces; we do this in a separate step
    # because this assignment is irrespective of order
    for attribute in attributes:
        name = attribute['name']
        value = attribute['value']
        if name == 'xmlns':
            namespace[None] = value
        elif name.startswith('xmlns:'):
            namespace[name[6:]] = value


def unpack_attributes(attributes, namespace, default):
    namespaced = OrderedDict()

    for index, attribute in enumerate(attributes):
        name = attribute['name']
        value = attribute['value']

        if ':' in name:
            prefix = name.split(':')[0]
            name = name[len(prefix) + 1:]
            try:
                ns = namespace[prefix]
            except KeyError:
                raise KeyError(
                    "Undefined namespace prefix: %s." % prefix)
        else:
            ns = default
        namespaced[ns, name] = value

    return namespaced


def identify(string):
    if string.startswith("<"):
        if string.startswith("<!--"):
            return "comment"
        if string.startswith("<![CDATA["):
            return "cdata"
        if string.startswith("<!"):
            return "declaration"
        if string.startswith("<?xml"):
            return "xml_declaration"
        if string.startswith("<?"):
            return "processing_instruction"
        if string.startswith("</"):
            return "end_tag"
        if string.endswith("/>"):
            return "empty_tag"
        if string.endswith(">"):
            return "start_tag"
        return "error"
    return "text"


class ElementParser(object):
    """Parses tokens into elements."""

    def __init__(self, stream, default_namespaces):
        self.stream = stream
        self.queue = []
        self.index = []
        self.namespaces = [default_namespaces.copy()]

    def __iter__(self):
        for token in self.stream:
            item = self.parse(token)
            self.queue.append(item)

        return iter(self.queue)

    def parse(self, token):
        kind = identify(token)
        visitor = getattr(self, "visit_%s" % kind, self.visit_default)
        return visitor(kind, token)

    def visit_comment(self, kind, token):
        return "comment", (token, )

    def visit_cdata(self, kind, token):
        return "cdata", (token, )

    def visit_default(self, kind, token):
        return "default", (token, )

    def visit_processing_instruction(self, kind, token):
        m = match_processing_instruction.match(token)
        if m is None:
            return self.visit_default(kind, token)

        return "processing_instruction", (groupdict(m, token), )

    def visit_text(self, kind, token):
        return kind, (token, )

    def visit_start_tag(self, kind, token):
        namespace = self.namespaces[-1].copy()
        self.namespaces.append(namespace)
        node = parse_tag(token, namespace)
        self.index.append((node['name'], len(self.queue)))
        return kind, (node, )

    def visit_end_tag(self, kind, token):
        try:
            namespace = self.namespaces.pop()
        except IndexError:
            raise ParseError("Unexpected end tag.", token)

        node = parse_tag(token, namespace)

        while self.index:
            name, pos = self.index.pop()
            if name == node['name']:
                start, = self.queue.pop(pos)[1]
                children = self.queue[pos:]
                del self.queue[pos:]
                break
        else:
            raise ParseError("Unexpected end tag.", token)

        return "element", (start, node, children)

    def visit_empty_tag(self, kind, token):
        namespace = self.namespaces[-1].copy()
        node = parse_tag(token, namespace)
        return "element", (node, None, [])

########NEW FILE########
__FILENAME__ = program
try:
    str = unicode
except NameError:
    long = int

from .tokenize import iter_xml
from .tokenize import iter_text
from .parser import ElementParser
from .namespaces import XML_NS
from .namespaces import XMLNS_NS


class ElementProgram(object):
    DEFAULT_NAMESPACES = {
        'xmlns': XMLNS_NS,
        'xml': XML_NS,
        }

    tokenizers = {
        'xml': iter_xml,
        'text': iter_text,
        }

    def __init__(self, source, mode="xml", filename=None):
        tokenizer = self.tokenizers[mode]
        tokens = tokenizer(source, filename)
        parser = ElementParser(tokens, self.DEFAULT_NAMESPACES)

        self.body = []

        for kind, args in parser:
            node = self.visit(kind, args)
            if node is not None:
                self.body.append(node)

    def visit(self, kind, args):
        visitor = getattr(self, "visit_%s" % kind)
        return visitor(*args)

########NEW FILE########
__FILENAME__ = py25
import sys

def lookup_attr(obj, key):
    try:
        return getattr(obj, key)
    except AttributeError:
        exc = sys.exc_info()[1]
        try:
            get = obj.__getitem__
        except AttributeError:
            raise exc
        try:
            return get(key)
        except KeyError:
            raise exc

def exec_(code, globs=None, locs=None):
    """Execute code in a namespace."""
    if globs is None:
        frame = sys._getframe(1)
        globs = frame.f_globals
        if locs is None:
            locs = frame.f_locals
        del frame
    elif locs is None:
        locs = globs
    exec("""exec code in globs, locs""")


exec_("""def raise_with_traceback(exc, tb):
    raise type(exc), exc, tb
""")


def next(iter):
    return iter.next()

########NEW FILE########
__FILENAME__ = py26
import sys

def lookup_attr(obj, key):
    try:
        return getattr(obj, key)
    except AttributeError:
        exc = sys.exc_info()[1]
        try:
            get = obj.__getitem__
        except AttributeError:
            raise exc
        try:
            return get(key)
        except KeyError:
            raise exc

########NEW FILE########
__FILENAME__ = tal
##############################################################################
#
# Copyright (c) 2001, 2002 Zope Foundation and Contributors.
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

import re
import copy

from .exc import LanguageError
from .utils import descriptorint
from .utils import descriptorstr
from .namespaces import XMLNS_NS
from .parser import groups


try:
    next
except NameError:
    from chameleon.py25 import next

try:
    # optional library: `zope.interface`
    from chameleon import interfaces
    import zope.interface
except ImportError:
    interfaces = None


NAME = r"[a-zA-Z_][-a-zA-Z0-9_]*"
DEFINE_RE = re.compile(r"(?s)\s*(?:(global|local)\s+)?" +
                       r"(%s|\(%s(?:,\s*%s)*\))\s+(.*)\Z" % (NAME, NAME, NAME),
                       re.UNICODE)
SUBST_RE = re.compile(r"\s*(?:(text|structure)\s+)?(.*)\Z", re.S | re.UNICODE)
ATTR_RE = re.compile(r"\s*([^\s{}'\"]+)\s+([^\s].*)\Z", re.S | re.UNICODE)

ENTITY_RE = re.compile(r'(&(#?)(x?)(\d{1,5}|\w{1,8});)')

WHITELIST = frozenset([
    "define",
    "comment",
    "condition",
    "content",
    "replace",
    "repeat",
    "attributes",
    "on-error",
    "omit-tag",
    "script",
    "switch",
    "case",
    "xmlns",
    "xml"
    ])


def split_parts(arg):
    # Break in pieces at undoubled semicolons and
    # change double semicolons to singles:
    i = 0
    while i < len(arg):
        m = ENTITY_RE.search(arg[i:])
        if m is None:
            break
        arg = arg[:i + m.end()] + ';' + arg[i + m.end():]
        i += m.end()

    arg = arg.replace(";;", "\0")
    parts = arg.split(';')
    parts = [p.replace("\0", ";") for p in parts]
    if len(parts) > 1 and not parts[-1].strip():
        del parts[-1]  # It ended in a semicolon

    return parts


def parse_attributes(clause):
    attrs = []
    seen = set()
    for part in split_parts(clause):
        m = ATTR_RE.match(part)
        if not m:
            name, expr = None, part.strip()
        else:
            name, expr = groups(m, part)

        if name in seen:
            raise LanguageError(
                "Duplicate attribute name in attributes.", part)

        seen.add(name)
        attrs.append((name, expr))

    return attrs


def parse_substitution(clause):
    m = SUBST_RE.match(clause)
    if m is None:
        raise LanguageError(
            "Invalid content substitution syntax.", clause)

    key, expression = groups(m, clause)
    if not key:
        key = "text"

    return key, expression


def parse_defines(clause):
    """
    Parses a tal:define value.

    # Basic syntax, implicit local
    >>> parse_defines('hello lovely')
    [('local', ('hello',), 'lovely')]

    # Explicit local
    >>> parse_defines('local hello lovely')
    [('local', ('hello',), 'lovely')]

    # With global
    >>> parse_defines('global hello lovely')
    [('global', ('hello',), 'lovely')]

    # Multiple expressions
    >>> parse_defines('hello lovely; tea time')
    [('local', ('hello',), 'lovely'), ('local', ('tea',), 'time')]

    # With multiple names
    >>> parse_defines('(hello, howdy) lovely')
    [('local', ['hello', 'howdy'], 'lovely')]

    # With unicode whitespace
    >>> try:
    ...     s = '\xc2\xa0hello lovely'.decode('utf-8')
    ... except AttributeError:
    ...     s = '\xa0hello lovely'
    >>> from chameleon.utils import unicode_string
    >>> parse_defines(s) == [
    ...     ('local', ('hello',), 'lovely')
    ... ]
    True

    """
    defines = []
    for part in split_parts(clause):
        m = DEFINE_RE.match(part)
        if m is None:
            raise LanguageError("Invalid define syntax", part)
        context, name, expr = groups(m, part)
        context = context or "local"

        if name.startswith('('):
            names = [n.strip() for n in name.strip('()').split(',')]
        else:
            names = (name,)

        defines.append((context, names, expr))

    return defines


def prepare_attributes(attrs, dyn_attributes, i18n_attributes,
                       ns_attributes, drop_ns):
    drop = set([attribute['name'] for attribute, (ns, value)
                in zip(attrs, ns_attributes)
                if ns in drop_ns or (
                    ns == XMLNS_NS and
                    attribute['value'] in drop_ns
                    )
                ])

    attributes = []
    normalized = {}
    computed = []

    for attribute in attrs:
        name = attribute['name']

        if name in drop:
            continue

        attributes.append((
            name,
            attribute['value'],
            attribute['quote'],
            attribute['space'],
            attribute['eq'],
            None,
            ))

        normalized[name.lower()] = len(attributes) - 1

    for name, expr in dyn_attributes:
        index = normalized.get(name.lower()) if name else None

        if index is not None:
            _, text, quote, space, eq, _ = attributes[index]
            add = attributes.__setitem__
        else:
            text = None
            quote = '"'
            space = " "
            eq = "="
            index = len(attributes)
            add = attributes.insert
            if name is not None:
                normalized[name.lower()] = len(attributes) - 1

        attribute = name, text, quote, space, eq, expr
        add(index, attribute)

    for name in i18n_attributes:
        attr = name.lower()
        if attr not in normalized:
            attributes.append((name, name, '"', " ", "=", None))
            normalized[attr] = len(attributes) - 1

    return attributes


class RepeatItem(object):
    __slots__ = "length", "_iterator"

    __allow_access_to_unprotected_subobjects__ = True

    def __init__(self, iterator, length):
        self.length = length
        self._iterator = iterator

    def __iter__(self):
        return self._iterator

    try:
        iter(()).__len__
    except AttributeError:
        @descriptorint
        def index(self):
            try:
                remaining = self._iterator.__length_hint__()
            except AttributeError:
                remaining = len(tuple(copy.copy(self._iterator)))
            return self.length - remaining - 1
    else:
        @descriptorint
        def index(self):
            remaining = self._iterator.__len__()
            return self.length - remaining - 1

    @descriptorint
    def start(self):
        return self.index == 0

    @descriptorint
    def end(self):
        return self.index == self.length - 1

    @descriptorint
    def number(self):
        return self.index + 1

    @descriptorstr
    def odd(self):
        """Returns a true value if the item index is odd.

        >>> it = RepeatItem(iter(("apple", "pear")), 2)

        >>> next(it._iterator)
        'apple'
        >>> it.odd()
        ''

        >>> next(it._iterator)
        'pear'
        >>> it.odd()
        'odd'
        """

        return self.index % 2 == 1 and 'odd' or ''

    @descriptorstr
    def even(self):
        """Returns a true value if the item index is even.

        >>> it = RepeatItem(iter(("apple", "pear")), 2)

        >>> next(it._iterator)
        'apple'
        >>> it.even()
        'even'

        >>> next(it._iterator)
        'pear'
        >>> it.even()
        ''
        """

        return self.index % 2 == 0 and 'even' or ''

    def next(self):
        raise NotImplementedError(
            "Method not implemented (can't update local variable).")

    def _letter(self, base=ord('a'), radix=26):
        """Get the iterator position as a lower-case letter

        >>> it = RepeatItem(iter(("apple", "pear", "orange")), 3)
        >>> next(it._iterator)
        'apple'
        >>> it.letter()
        'a'
        >>> next(it._iterator)
        'pear'
        >>> it.letter()
        'b'
        >>> next(it._iterator)
        'orange'
        >>> it.letter()
        'c'
        """

        index = self.index
        if index < 0:
            raise TypeError("No iteration position")
        s = ""
        while 1:
            index, off = divmod(index, radix)
            s = chr(base + off) + s
            if not index:
                return s

    letter = descriptorstr(_letter)

    @descriptorstr
    def Letter(self):
        """Get the iterator position as an upper-case letter

        >>> it = RepeatItem(iter(("apple", "pear", "orange")), 3)
        >>> next(it._iterator)
        'apple'
        >>> it.Letter()
        'A'
        >>> next(it._iterator)
        'pear'
        >>> it.Letter()
        'B'
        >>> next(it._iterator)
        'orange'
        >>> it.Letter()
        'C'
        """

        return self._letter(base=ord('A'))

    @descriptorstr
    def Roman(self, rnvalues=(
                    (1000, 'M'), (900, 'CM'), (500, 'D'), (400, 'CD'),
                    (100, 'C'), (90, 'XC'), (50, 'L'), (40, 'XL'),
                    (10, 'X'), (9, 'IX'), (5, 'V'), (4, 'IV'), (1, 'I'))):
        """Get the iterator position as an upper-case roman numeral

        >>> it = RepeatItem(iter(("apple", "pear", "orange")), 3)
        >>> next(it._iterator)
        'apple'
        >>> it.Roman()
        'I'
        >>> next(it._iterator)
        'pear'
        >>> it.Roman()
        'II'
        >>> next(it._iterator)
        'orange'
        >>> it.Roman()
        'III'
        """

        n = self.index + 1
        s = ""
        for v, r in rnvalues:
            rct, n = divmod(n, v)
            s = s + r * rct
        return s

    @descriptorstr
    def roman(self):
        """Get the iterator position as a lower-case roman numeral

        >>> it = RepeatItem(iter(("apple", "pear", "orange")), 3)
        >>> next(it._iterator)
        'apple'
        >>> it.roman()
        'i'
        >>> next(it._iterator)
        'pear'
        >>> it.roman()
        'ii'
        >>> next(it._iterator)
        'orange'
        >>> it.roman()
        'iii'
        """

        return self.Roman().lower()


if interfaces is not None:
    zope.interface.classImplements(RepeatItem, interfaces.ITALESIterator)


class RepeatDict(dict):
    """Repeat dictionary implementation.

    >>> repeat = RepeatDict({})
    >>> iterator, length = repeat('numbers', range(5))
    >>> length
    5

    >>> repeat['numbers']
    <chameleon.tal.RepeatItem object at ...>

    >>> repeat.numbers
    <chameleon.tal.RepeatItem object at ...>

    >>> getattr(repeat, 'missing_key', None) is None
    True

	>>> try:
	...     from chameleon import interfaces
	...     interfaces.ITALESIterator(repeat,None) is None
	... except ImportError:
	...     True
	...
	True
	"""

    __slots__ = "__setitem__", "__getitem__"

    def __init__(self, d):
        self.__setitem__ = d.__setitem__
        self.__getitem__ = d.__getitem__

    def __getattr__(self,key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(key)


    def __call__(self, key, iterable):
        """We coerce the iterable to a tuple and return an iterator
        after registering it in the repeat dictionary."""

        iterable = list(iterable) if iterable is not None else ()

        length = len(iterable)
        iterator = iter(iterable)

        # Insert as repeat item
        self[key] = RepeatItem(iterator, length)

        return iterator, length


class ErrorInfo(object):
    """Information about an exception passed to an on-error handler."""

    def __init__(self, err, position=(None, None)):
        if isinstance(err, Exception):
            self.type = err.__class__
            self.value = err
        else:
            self.type = err
            self.value = None
        self.lineno = position[0]
        self.offset = position[1]


if interfaces is not None:
    zope.interface.classImplements(ErrorInfo, interfaces.ITALExpressionErrorInfo)

########NEW FILE########
__FILENAME__ = tales
import re
import sys

from .astutil import parse
from .astutil import store
from .astutil import load
from .astutil import ItemLookupOnAttributeErrorVisitor
from .codegen import TemplateCodeGenerator
from .codegen import template
from .codegen import reverse_builtin_map
from .astutil import Builtin
from .astutil import Symbol
from .exc import ExpressionError
from .utils import resolve_dotted
from .utils import Markup
from .utils import ast
from .tokenize import Token
from .parser import substitute
from .compiler import Interpolator

try:
    from .py26 import lookup_attr
except SyntaxError:
    from .py25 import lookup_attr


split_parts = re.compile(r'(?<!\\)\|')
match_prefix = re.compile(r'^\s*([a-z\-_]+):').match
re_continuation = re.compile(r'\\\s*$', re.MULTILINE)

try:
    from __builtin__ import basestring
except ImportError:
    basestring = str


def resolve_global(value):
    name = reverse_builtin_map.get(value)
    if name is not None:
        return Builtin(name)

    return Symbol(value)


def test(expression, engine=None, **env):
    if engine is None:
        engine = SimpleEngine()

    body = expression(store("result"), engine)
    module = ast.Module(body)
    module = ast.fix_missing_locations(module)
    env['rcontext'] = {}
    source = TemplateCodeGenerator(module).code
    code = compile(source, '<string>', 'exec')
    exec(code, env)
    result = env["result"]

    if isinstance(result, basestring):
        result = str(result)

    return result


def transform_attribute(node):
    return template(
        "lookup(object, name)",
        lookup=Symbol(lookup_attr),
        object=node.value,
        name=ast.Str(s=node.attr),
        mode="eval"
        )


class TalesExpr(object):
    """Base class.

    This class helps implementations for the Template Attribute
    Language Expression Syntax (TALES).

    The syntax evaluates one or more expressions, separated by '|'
    (pipe). The first expression that succeeds, is returned.

    Expression:

      expression    := (type ':')? line ('|' expression)?
      line          := .*

    Expression lines may not contain the pipe character unless
    escaped. It has a special meaning:

    If the expression to the left of the pipe fails (raises one of the
    exceptions listed in ``catch_exceptions``), evaluation proceeds to
    the expression(s) on the right.

    Subclasses must implement ``translate`` which assigns a value for
    a given expression.

    >>> class PythonPipeExpr(TalesExpr):
    ...     def translate(self, expression, target):
    ...         compiler = PythonExpr(expression)
    ...         return compiler(target, None)

    >>> test(PythonPipeExpr('foo | bar | 42'))
    42

    >>> test(PythonPipeExpr('foo|42'))
    42
    """

    exceptions = NameError, \
                 ValueError, \
                 AttributeError, \
                 LookupError, \
                 TypeError

    ignore_prefix = True

    def __init__(self, expression):
        self.expression = expression

    def __call__(self, target, engine):
        remaining = self.expression
        assignments = []

        while remaining:
            if self.ignore_prefix and match_prefix(remaining) is not None:
                compiler = engine.parse(remaining)
                assignment = compiler.assign_value(target)
                remaining = ""
            else:
                for m in split_parts.finditer(remaining):
                    expression = remaining[:m.start()]
                    remaining = remaining[m.end():]
                    break
                else:
                    expression = remaining
                    remaining = ""

                expression = expression.replace('\\|', '|')
                assignment = self.translate_proxy(engine, expression, target)
            assignments.append(assignment)

        if not assignments:
            if not remaining:
                raise ExpressionError("No input:", remaining)

            assignments.append(
                self.translate_proxy(engine, remaining, target)
                )

        for i, assignment in enumerate(reversed(assignments)):
            if i == 0:
                body = assignment
            else:
                body = [ast.TryExcept(
                    body=assignment,
                    handlers=[ast.ExceptHandler(
                        type=ast.Tuple(
                            elts=map(resolve_global, self.exceptions),
                            ctx=ast.Load()),
                        name=None,
                        body=body,
                        )],
                    )]

        return body

    def translate_proxy(self, engine, *args):
        """Default implementation delegates to ``translate`` method."""

        return self.translate(*args)

    def translate(self, expression, target):
        """Return statements that assign a value to ``target``."""

        raise NotImplementedError(
            "Must be implemented by a subclass.")


class PathExpr(TalesExpr):
    """Path expression compiler.

    Syntax::

        PathExpr ::= Path [ '|' Path ]*
        Path ::= variable [ '/' URL_Segment ]*
        variable ::= Name

    For example::

        request/cookies/oatmeal
        nothing
        here/some-file 2001_02.html.tar.gz/foo
        root/to/branch | default

    When a path expression is evaluated, it attempts to traverse
    each path, from left to right, until it succeeds or runs out of
    paths. To traverse a path, it first fetches the object stored in
    the variable. For each path segment, it traverses from the current
    object to the subobject named by the path segment.

    Once a path has been successfully traversed, the resulting object
    is the value of the expression. If it is a callable object, such
    as a method or class, it is called.

    The semantics of traversal (and what it means to be callable) are
    implementation-dependent (see the ``translate`` method).
    """

    def translate(self, expression, target):
        raise NotImplementedError(
            "Path expressions are not yet implemented. "
            "It's unclear whether a general implementation "
            "can be devised.")


class PythonExpr(TalesExpr):
    """Python expression compiler.

    >>> test(PythonExpr('2 + 2'))
    4

    The Python expression is a TALES expression. That means we can use
    the pipe operator:

    >>> test(PythonExpr('foo | 2 + 2 | 5'))
    4

    To include a pipe character, use a backslash escape sequence:

    >>> test(PythonExpr('\"\|\"'))
    '|'
    """

    transform = ItemLookupOnAttributeErrorVisitor(transform_attribute)

    def parse(self, string):
        return parse(string, 'eval').body

    def translate(self, expression, target):
        # Strip spaces
        string = expression.strip()

        # Conver line continuations to newlines
        string = substitute(re_continuation, '\n', string)

        # Convert newlines to spaces
        string = string.replace('\n', ' ')

        try:
            value = self.parse(string)
        except SyntaxError:
            exc = sys.exc_info()[1]
            raise ExpressionError(exc.msg, string)

        # Transform attribute lookups to allow fallback to item lookup
        self.transform.visit(value)

        return [ast.Assign(targets=[target], value=value)]


class ImportExpr(object):
    re_dotted = re.compile(r'^[A-Za-z.]+$')

    def __init__(self, expression):
        self.expression = expression

    def __call__(self, target, engine):
        string = self.expression.strip().replace('\n', ' ')
        value = template(
            "RESOLVE(NAME)",
            RESOLVE=Symbol(resolve_dotted),
            NAME=ast.Str(s=string),
            mode="eval",
            )
        return [ast.Assign(targets=[target], value=value)]


class NotExpr(object):
    """Negates the expression.

    >>> engine = SimpleEngine(PythonExpr)

    >>> test(NotExpr('False'), engine)
    True
    >>> test(NotExpr('True'), engine)
    False
    """

    def __init__(self, expression):
        self.expression = expression

    def __call__(self, target, engine):
        compiler = engine.parse(self.expression)
        body = compiler.assign_value(target)
        return body + template("target = not target", target=target)


class StructureExpr(object):
    """Wraps the expression result as 'structure'.

    >>> engine = SimpleEngine(PythonExpr)

    >>> test(StructureExpr('\"<tt>foo</tt>\"'), engine)
    '<tt>foo</tt>'
    """

    wrapper_class = Symbol(Markup)

    def __init__(self, expression):
        self.expression = expression

    def __call__(self, target, engine):
        compiler = engine.parse(self.expression)
        body = compiler.assign_value(target)
        return body + template(
            "target = wrapper(target)",
            target=target,
            wrapper=self.wrapper_class
            )


class IdentityExpr(object):
    """Identity expression.

    Exists to demonstrate the interface.

    >>> test(IdentityExpr('42'))
    42
    """

    def __init__(self, expression):
        self.expression = expression

    def __call__(self, target, engine):
        compiler = engine.parse(self.expression)
        return compiler.assign_value(target)


class StringExpr(object):
    """Similar to the built-in ``string.Template``, but uses an
    expression engine to support pluggable string substitution
    expressions.

    Expr string:

      string       := (text | substitution) (string)?
      substitution := ('$' variable | '${' expression '}')
      text         := .*

    In other words, an expression string can contain multiple
    substitutions. The text- and substitution parts will be
    concatenated back into a string.

    >>> test(StringExpr('Hello ${name}!'), name='world')
    'Hello world!'

    In the default configuration, braces may be omitted if the
    expression is an identifier.

    >>> test(StringExpr('Hello $name!'), name='world')
    'Hello world!'

    The ``braces_required`` flag changes this setting:

    >>> test(StringExpr('Hello $name!', True))
    'Hello $name!'

    We can escape interpolation using the standard escaping
    syntax:

    >>> test(StringExpr('\\${name}'))
    '\\\${name}'

    Multiple interpolations in one:

    >>> test(StringExpr(\"Hello ${'a'}${'b'}${'c'}!\"))
    'Hello abc!'

    Here's a more involved example taken from a javascript source:

    >>> result = test(StringExpr(\"\"\"
    ... function(oid) {
    ...     $('#' + oid).autocomplete({source: ${'source'}});
    ... }
    ... \"\"\"))

    >>> 'source: source' in result
    True

    In the above examples, the expression is evaluated using the
    dummy engine which just returns the input as a string.

    As an example, we'll implement an expression engine which
    instead counts the number of characters in the expresion and
    returns an integer result.

    >>> class engine:
    ...     @staticmethod
    ...     def parse(expression):
    ...         class compiler:
    ...             @staticmethod
    ...             def assign_text(target):
    ...                 return [
    ...                     ast.Assign(
    ...                         targets=[target],
    ...                         value=ast.Num(n=len(expression))
    ...                     )]
    ...
    ...         return compiler

    This will demonstrate how the string expression coerces the
    input to a string.

    >>> expr = StringExpr(
    ...    'There are ${hello world} characters in \"hello world\"')

    We evaluate the expression using the new engine:

    >>> test(expr, engine)
    'There are 11 characters in \"hello world\"'
    """

    def __init__(self, expression, braces_required=False):
        # The code relies on the expression being a token string
        if not isinstance(expression, Token):
            expression = Token(expression, 0)

        self.translator = Interpolator(expression, braces_required)

    def __call__(self, name, engine):
        return self.translator(name, engine)


class ProxyExpr(TalesExpr):
    braces_required = False

    def __init__(self, name, expression, ignore_prefix=True):
        super(ProxyExpr, self).__init__(expression)
        self.ignore_prefix = ignore_prefix
        self.name = name

    def translate_proxy(self, engine, expression, target):
        translator = Interpolator(expression, self.braces_required)
        assignment = translator(target, engine)

        return assignment + [
            ast.Assign(targets=[target], value=ast.Call(
                func=load(self.name),
                args=[target],
                keywords=[],
                starargs=None,
                kwargs=None
            ))
        ]


class ExistsExpr(object):
    """Boolean wrapper.

    Return 0 if the expression results in an exception, otherwise 1.

    As a means to generate exceptions, we set up an expression engine
    which evaluates the provided expression using Python:

    >>> engine = SimpleEngine(PythonExpr)

    >>> test(ExistsExpr('int(0)'), engine)
    1
    >>> test(ExistsExpr('int(None)'), engine)
    0

    """

    exceptions = AttributeError, LookupError, TypeError, NameError, KeyError

    def __init__(self, expression):
        self.expression = expression

    def __call__(self, target, engine):
        ignore = store("_ignore")
        compiler = engine.parse(self.expression)
        body = compiler.assign_value(ignore)

        classes = map(resolve_global, self.exceptions)

        return [
            ast.TryExcept(
                body=body,
                handlers=[ast.ExceptHandler(
                    type=ast.Tuple(elts=classes, ctx=ast.Load()),
                    name=None,
                    body=template("target = 0", target=target),
                    )],
                orelse=template("target = 1", target=target)
                )
            ]


class ExpressionParser(object):
    def __init__(self, factories, default):
        self.factories = factories
        self.default = default

    def __call__(self, expression):
        m = match_prefix(expression)
        if m is not None:
            prefix = m.group(1)
            expression = expression[m.end():]
        else:
            prefix = self.default

        try:
            factory = self.factories[prefix]
        except KeyError:
            exc = sys.exc_info()[1]
            raise LookupError(
                "Unknown expression type: %s." % str(exc)
                )

        return factory(expression)


class SimpleEngine(object):
    expression = PythonExpr

    def __init__(self, expression=None):
        if expression is not None:
            self.expression = expression

    def parse(self, string):
        compiler = self.expression(string)
        return SimpleCompiler(compiler, self)


class SimpleCompiler(object):
    def __init__(self, compiler, engine):
        self.compiler = compiler
        self.engine = engine

    def assign_text(self, target):
        """Assign expression string as a text value."""

        return self._assign_value_and_coerce(target, "str")

    def assign_value(self, target):
        """Assign expression string as object value."""

        return self.compiler(target, self.engine)

    def _assign_value_and_coerce(self, target, builtin):
        return self.assign_value(target) + template(
            "target = builtin(target)",
            target=target,
            builtin=builtin
            )

########NEW FILE########
__FILENAME__ = template
from __future__ import with_statement

import os
import sys
import hashlib
import logging
import tempfile
import inspect

pkg_digest = hashlib.sha1(__name__.encode('utf-8'))

try:
    import pkg_resources
except ImportError:
    logging.info("Setuptools not installed. Unable to determine version.")
else:
    for path in sys.path:
        for distribution in pkg_resources.find_distributions(path):
            if distribution.has_version():
                version = distribution.version.encode('utf-8')
                pkg_digest.update(version)


from .exc import TemplateError
from .exc import ExceptionFormatter
from .compiler import Compiler
from .config import DEBUG_MODE
from .config import AUTO_RELOAD
from .config import EAGER_PARSING
from .config import CACHE_DIRECTORY
from .loader import ModuleLoader
from .loader import MemoryLoader
from .nodes import Module
from .utils import DebuggingOutputStream
from .utils import Scope
from .utils import join
from .utils import mangle
from .utils import create_formatted_exception
from .utils import read_bytes
from .utils import raise_with_traceback
from .utils import byte_string


log = logging.getLogger('chameleon.template')


def _make_module_loader():
    remove = False
    if CACHE_DIRECTORY:
        path = CACHE_DIRECTORY
    else:
        path = tempfile.mkdtemp()
        remove = True

    return ModuleLoader(path, remove)


class BaseTemplate(object):
    """Template base class.

    Takes a string input which must be one of the following:

    - a unicode string (or string on Python 3);
    - a utf-8 encoded byte string;
    - a byte string for an XML document that defines an encoding
      in the document premamble;
    - an HTML document that specifies the encoding via the META tag.

    Note that the template input is decoded, parsed and compiled on
    initialization.
    """

    default_encoding = "utf-8"

    # This attribute is strictly informational in this template class
    # and is used in exception formatting. It may be set on
    # initialization using the optional ``filename`` keyword argument.
    filename = '<string>'

    _cooked = False

    if DEBUG_MODE or CACHE_DIRECTORY:
        loader = _make_module_loader()
    else:
        loader = MemoryLoader()

    if DEBUG_MODE:
        output_stream_factory = DebuggingOutputStream
    else:
        output_stream_factory = list

    debug = DEBUG_MODE

    # The ``builtins`` dictionary can be used by a template class to
    # add symbols which may not be redefined and which are (cheaply)
    # available in the template variable scope
    builtins = {}

    # The ``builtins`` dictionary is updated with this dictionary at
    # cook time. Note that it can be provided at class initialization
    # using the ``extra_builtins`` keyword argument.
    extra_builtins = {}

    # Expression engine must be provided by subclass
    engine = None

    # When ``strict`` is set, expressions must be valid at compile
    # time. When not set, this is only required at evaluation time.
    strict = True

    def __init__(self, body=None, **config):
        self.__dict__.update(config)

        if body is not None:
            self.write(body)

        # This is only necessary if the ``debug`` flag was passed as a
        # keyword argument
        if self.__dict__.get('debug') is True:
            self.loader = _make_module_loader()

    def __call__(self, **kwargs):
        return self.render(**kwargs)

    def __repr__(self):
        return "<%s %s>" % (self.__class__.__name__, self.filename)

    @property
    def keep_body(self):
        # By default, we only save the template body if we're
        # in debugging mode (to save memory).
        return self.__dict__.get('keep_body', DEBUG_MODE)

    @property
    def keep_source(self):
        # By default, we only save the generated source code if we're
        # in debugging mode (to save memory).
        return self.__dict__.get('keep_source', DEBUG_MODE)

    def cook(self, body):
        builtins_dict = self.builtins.copy()
        builtins_dict.update(self.extra_builtins)
        names, builtins = zip(*sorted(builtins_dict.items()))
        digest = self.digest(body, names)
        program = self._cook(body, digest, names)

        initialize = program['initialize']
        functions = initialize(*builtins)

        for name, function in functions.items():
            setattr(self, "_" + name, function)

        self._cooked = True

        if self.keep_body:
            self.body = body

    def cook_check(self):
        assert self._cooked

    def parse(self, body):
        raise NotImplementedError("Must be implemented by subclass.")

    def render(self, **__kw):
        econtext = Scope(__kw)
        rcontext = {}
        self.cook_check()
        stream = self.output_stream_factory()
        try:
            self._render(stream, econtext, rcontext)
        except:
            cls, exc, tb = sys.exc_info()
            errors = rcontext.get('__error__')
            if errors:
                formatter = exc.__str__
                if isinstance(formatter, ExceptionFormatter):
                    if errors is not formatter._errors:
                        formatter._errors.extend(errors)
                    raise

                formatter = ExceptionFormatter(errors, econtext, rcontext)

                try:
                    exc = create_formatted_exception(exc, cls, formatter)
                except TypeError:
                    pass

                raise_with_traceback(exc, tb)

            raise

        return join(stream)

    def write(self, body):
        if isinstance(body, byte_string):
            body, encoding, content_type = read_bytes(
                body, self.default_encoding
                )
        else:
            content_type = body.startswith('<?xml')
            encoding = None

        self.content_type = content_type
        self.content_encoding = encoding

        self.cook(body)

    def _get_module_name(self, name):
        return "%s.py" % name

    def _cook(self, body, name, builtins):
        filename = self._get_module_name(name)
        cooked = self.loader.get(filename)
        if cooked is None:
            try:
                source = self._make(body, builtins)
                if self.debug:
                    source = "# template: %s\n#\n%s" % (
                        self.filename, source)
                if self.keep_source:
                    self.source = source
                cooked = self.loader.build(source, filename)
            except TemplateError:
                exc = sys.exc_info()[1]
                exc.filename = self.filename
                raise
        elif self.keep_source:
            module = sys.modules.get(cooked.get('__name__'))
            if module is not None:
                self.source = inspect.getsource(module)
            else:
                self.source = None
        return cooked

    def digest(self, body, names):
        class_name = type(self).__name__.encode('utf-8')
        sha = pkg_digest.copy()
        sha.update(body.encode('utf-8', 'ignore'))
        sha.update(class_name)
        return sha.hexdigest()

    def _compile(self, program, builtins):
        compiler = Compiler(self.engine, program, builtins, strict=self.strict)
        return compiler.code

    def _make(self, body, builtins):
        program = self.parse(body)
        module = Module("initialize", program)
        return self._compile(module, builtins)


class BaseTemplateFile(BaseTemplate):
    """File-based template base class.

    Relative path names are supported only when a template loader is
    provided as the ``loader`` parameter.
    """

    # Auto reload is not enabled by default because it's a significant
    # performance hit
    auto_reload = AUTO_RELOAD

    def __init__(self, filename, auto_reload=None, **config):
        # Normalize filename
        filename = os.path.abspath(
            os.path.normpath(os.path.expanduser(filename))
            )

        self.filename = filename

        # Override reload setting only if value is provided explicitly
        if auto_reload is not None:
            self.auto_reload = auto_reload

        super(BaseTemplateFile, self).__init__(**config)

        if EAGER_PARSING:
            self.cook_check()

    def cook_check(self):
        if self.auto_reload:
            mtime = self.mtime()

            if mtime != self._v_last_read:
                self._v_last_read = mtime
                self._cooked = False

        if self._cooked is False:
            body = self.read()
            log.debug("cooking %r (%d bytes)..." % (self.filename, len(body)))
            self.cook(body)

    def mtime(self):
        try:
            return os.path.getmtime(self.filename)
        except (IOError, OSError):
            return 0

    def read(self):
        with open(self.filename, "rb") as f:
            data = f.read()

        body, encoding, content_type = read_bytes(
            data, self.default_encoding
            )

        # In non-XML mode, we support various platform-specific line
        # endings and convert them to the UNIX newline character
        if content_type != "text/xml" and '\r' in body:
            body = body.replace('\r\n', '\n').replace('\r', '\n')

        self.content_type = content_type
        self.content_encoding = encoding

        return body

    def _get_module_name(self, name):
        filename = os.path.basename(self.filename)
        mangled = mangle(filename)
        return "%s_%s.py" % (mangled, name)

    def _get_filename(self):
        return self.__dict__.get('filename')

    def _set_filename(self, filename):
        self.__dict__['filename'] = filename
        self._v_last_read = None
        self._cooked = False

    filename = property(_get_filename, _set_filename)

########NEW FILE########
__FILENAME__ = test_doctests
import unittest
import doctest

OPTIONFLAGS = (doctest.ELLIPSIS |
               doctest.REPORT_ONLY_FIRST_FAILURE)


class DoctestCase(unittest.TestCase):
    def __new__(self, test):
        return getattr(self, test)()

    @classmethod
    def test_tal(cls):
        from chameleon import tal
        return doctest.DocTestSuite(
            tal, optionflags=OPTIONFLAGS)

    @classmethod
    def test_tales(cls):
        from chameleon import tales
        return doctest.DocTestSuite(
            tales, optionflags=OPTIONFLAGS)

    @classmethod
    def test_utils(cls):
        from chameleon import utils
        return doctest.DocTestSuite(
            utils, optionflags=OPTIONFLAGS)

    @classmethod
    def test_exc(cls):
        from chameleon import exc
        return doctest.DocTestSuite(
            exc, optionflags=OPTIONFLAGS)

    @classmethod
    def test_compiler(cls):
        from chameleon import compiler
        return doctest.DocTestSuite(
            compiler, optionflags=OPTIONFLAGS)

########NEW FILE########
__FILENAME__ = test_exc
from unittest import TestCase

class TestTemplateError(TestCase):

    def test_keep_token_location_info(self):
        # tokens should not lose information when passed to a TemplateError
        from chameleon import exc, tokenize, utils
        token = tokenize.Token('stuff', 5, 'more\nstuff', 'mystuff.txt')
        error = exc.TemplateError('message', token)
        s = str(error)
        self.assertTrue(
                '- Location:   (line 2: col 0)' in s,
                'No location data found\n%s' % s)

########NEW FILE########
__FILENAME__ = test_loader
import unittest


class LoadTests:
    def _makeOne(self, search_path=None, **kwargs):
        klass = self._getTargetClass()
        return klass(search_path, **kwargs)

    def _getTargetClass(self):
        from chameleon.loader import TemplateLoader
        return TemplateLoader

    def test_load_relative(self):
        import os
        here = os.path.join(os.path.dirname(__file__), "inputs")
        loader = self._makeOne(search_path=[here])
        result = self._load(loader, 'hello_world.pt')
        self.assertEqual(result.filename, os.path.join(here, 'hello_world.pt'))

    def test_consecutive_loads(self):
        import os
        here = os.path.join(os.path.dirname(__file__), "inputs")
        loader = self._makeOne(search_path=[here])

        self.assertTrue(
            self._load(loader, 'hello_world.pt') is \
            self._load(loader, 'hello_world.pt'))

    def test_load_relative_badpath_in_searchpath(self):
        import os
        here = os.path.join(os.path.dirname(__file__), "inputs")
        loader = self._makeOne(search_path=[os.path.join(here, 'none'), here])
        result = self._load(loader, 'hello_world.pt')
        self.assertEqual(result.filename, os.path.join(here, 'hello_world.pt'))

    def test_load_abs(self):
        import os
        here = os.path.join(os.path.dirname(__file__), "inputs")
        loader = self._makeOne()
        abs = os.path.join(here, 'hello_world.pt')
        result = self._load(loader, abs)
        self.assertEqual(result.filename, abs)


class LoadPageTests(unittest.TestCase, LoadTests):
    def _load(self, loader, filename):
        from chameleon.zpt import template
        return loader.load(filename, template.PageTemplateFile)


class ModuleLoadTests(unittest.TestCase):
    def _makeOne(self, *args, **kwargs):
        from chameleon.loader import ModuleLoader
        return ModuleLoader(*args, **kwargs)

    def test_build(self):
        import tempfile
        path = tempfile.mkdtemp()
        loader = self._makeOne(path)
        source = "def function(): return %r" % "\xc3\xa6\xc3\xb8\xc3\xa5"
        try:
            source = source.decode('utf-8')
        except AttributeError:
            import sys
            self.assertTrue(sys.version_info[0] > 2)

        module = loader.build(source, "test.xml")
        result1 = module['function']()
        d = {}
        code = compile(source, 'test.py', 'exec')
        exec(code, d)
        result2 = d['function']()
        self.assertEqual(result1, result2)

        import os
        self.assertTrue("test.py" in os.listdir(path))

        import shutil
        shutil.rmtree(path)


class ZPTLoadTests(unittest.TestCase):
    def _makeOne(self, *args, **kwargs):
        import os
        here = os.path.join(os.path.dirname(__file__), "inputs")
        from chameleon.zpt import loader
        return loader.TemplateLoader(here, **kwargs)

    def test_load_xml(self):
        loader = self._makeOne()
        template = loader.load("hello_world.pt", "xml")
        from chameleon.zpt.template import PageTemplateFile
        self.assertTrue(isinstance(template, PageTemplateFile))

    def test_load_text(self):
        loader = self._makeOne()
        template = loader.load("hello_world.txt", "text")
        from chameleon.zpt.template import PageTextTemplateFile
        self.assertTrue(isinstance(template, PageTextTemplateFile))

    def test_load_getitem_gets_xml_file(self):
        loader = self._makeOne()
        template = loader["hello_world.pt"]
        from chameleon.zpt.template import PageTemplateFile
        self.assertTrue(isinstance(template, PageTemplateFile))


def test_suite():
    import sys
    return unittest.findTestCases(sys.modules[__name__])

########NEW FILE########
__FILENAME__ = test_parser
from __future__ import with_statement

import sys

from unittest import TestCase

from ..namespaces import XML_NS
from ..namespaces import XMLNS_NS
from ..namespaces import PY_NS


class ParserTest(TestCase):
    def test_sample_files(self):
        import os
        import traceback
        path = os.path.join(os.path.dirname(__file__), "inputs")
        for filename in os.listdir(path):
            if not filename.endswith('.html'):
                continue

            with open(os.path.join(path, filename), 'rb') as f:
                source = f.read()

            from ..utils import read_encoded
            try:
                want = read_encoded(source)
            except UnicodeDecodeError:
                exc = sys.exc_info()[1]
                self.fail("%s - %s" % (exc, filename))

            from ..tokenize import iter_xml
            from ..parser import ElementParser
            try:
                tokens = iter_xml(want)
                parser = ElementParser(tokens, {
                    'xmlns': XMLNS_NS,
                    'xml': XML_NS,
                    'py': PY_NS,
                    })
                elements = tuple(parser)
            except:
                self.fail(traceback.format_exc())

            output = []

            def render(kind, args):
                if kind == 'element':
                    # start tag
                    tag, end, children = args
                    output.append("%(prefix)s%(name)s" % tag)

                    for attr in tag['attrs']:
                        output.append(
                            "%(space)s%(name)s%(eq)s%(quote)s%(value)s%(quote)s" % \
                            attr
                            )

                    output.append("%(suffix)s" % tag)

                    # children
                    for item in children:
                        render(*item)

                    # end tag
                    output.append(
                        "%(prefix)s%(name)s%(space)s%(suffix)s" % end
                        )
                elif kind == 'text':
                    text = args[0]
                    output.append(text)
                elif kind == 'start_tag':
                    node = args[0]
                    output.append(
                        "%(prefix)s%(name)s%(space)s%(suffix)s" % node
                        )
                else:
                    raise RuntimeError("Not implemented: %s." % kind)

            for kind, args in elements:
                render(kind, args)

            got = "".join(output)

            from doctest import OutputChecker
            checker = OutputChecker()

            if checker.check_output(want, got, 0) is False:
                from doctest import Example
                example = Example(f.name, want)
                diff = checker.output_difference(
                    example, got, 0)
                self.fail("(%s) - \n%s" % (f.name, diff))

########NEW FILE########
__FILENAME__ = test_sniffing
from __future__ import with_statement

import os
import unittest
import tempfile
import shutil

from chameleon.utils import unicode_string
from chameleon.utils import encode_string


class TypeSniffingTestCase(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.mkdtemp(prefix='chameleon-tests')

    def tearDown(self):
        shutil.rmtree(self.tempdir)

    def _get_temporary_file(self):
        filename = os.path.join(self.tempdir, 'template.py')
        assert not os.path.exists(filename)
        f = open(filename, 'w')
        f.flush()
        f.close()
        return filename

    def get_template(self, text):
        fn = self._get_temporary_file()

        with open(fn, 'wb') as tmpfile:
            tmpfile.write(text)

        from chameleon.template import BaseTemplateFile

        class DummyTemplateFile(BaseTemplateFile):
            def cook(self, body):
                self.body = body

        template = DummyTemplateFile(fn)
        template.cook_check()
        return template

    def check_content_type(self, text, expected_type):
        from chameleon.utils import read_bytes
        content_type = read_bytes(text, 'ascii')[2]
        self.assertEqual(content_type, expected_type)

    def test_xml_encoding(self):
        from chameleon.utils import xml_prefixes

        document1 = unicode_string(
            "<?xml version='1.0' encoding='ascii'?><doc/>"
            )
        document2 = unicode_string(
            "<?xml\tversion='1.0' encoding='ascii'?><doc/>"
            )

        for bom, encoding in xml_prefixes:
            try:
                "".encode(encoding)
            except LookupError:
                # System does not support this encoding
                continue

            self.check_content_type(document1.encode(encoding), "text/xml")
            self.check_content_type(document2.encode(encoding), "text/xml")

    HTML_PUBLIC_ID = "-//W3C//DTD HTML 4.01 Transitional//EN"
    HTML_SYSTEM_ID = "http://www.w3.org/TR/html4/loose.dtd"

    # Couldn't find the code that handles this... yet.
    # def test_sniffer_html_ascii(self):
    #     self.check_content_type(
    #         "<!DOCTYPE html [ SYSTEM '%s' ]><html></html>"
    #         % self.HTML_SYSTEM_ID,
    #         "text/html")
    #     self.check_content_type(
    #         "<html><head><title>sample document</title></head></html>",
    #         "text/html")

    # TODO: This reflects a case that simply isn't handled by the
    # sniffer; there are many, but it gets it right more often than
    # before.
    def donttest_sniffer_xml_simple(self):
        self.check_content_type("<doc><element/></doc>", "text/xml")

    def test_html_default_encoding(self):
        body = encode_string(
            '<html><head><title>' \
            '\xc3\x90\xc2\xa2\xc3\x90\xc2\xb5' \
            '\xc3\x91\xc2\x81\xc3\x91\xc2\x82' \
            '</title></head></html>')

        template = self.get_template(body)
        self.assertEqual(template.body, body.decode('utf-8'))

    def test_html_encoding_by_meta(self):
        body = encode_string(
            '<html><head><title>' \
            '\xc3\x92\xc3\xa5\xc3\xb1\xc3\xb2' \
            '</title><meta http-equiv="Content-Type"' \
            ' content="text/html; charset=windows-1251"/>' \
            "</head></html>")

        template = self.get_template(body)
        self.assertEqual(template.body, body.decode('windows-1251'))

    def test_xhtml(self):
        body = encode_string(
            '<html><head><title>' \
            '\xc3\x92\xc3\xa5\xc3\xb1\xc3\xb2' \
            '</title><meta http-equiv="Content-Type"' \
            ' content="text/html; charset=windows-1251"/>' \
            "</head></html>")

        template = self.get_template(body)
        self.assertEqual(template.body, body.decode('windows-1251'))


def test_suite():
    return unittest.makeSuite(TypeSniffingTestCase)

if __name__ == "__main__":
    unittest.main(defaultTest="test_suite")

########NEW FILE########
__FILENAME__ = test_templates
# -*- coding: utf-8 -*-

from __future__ import with_statement

import re
import os
import sys
import shutil
import tempfile

from functools import wraps
from functools import partial

try:
    from unittest2 import TestCase
except ImportError:
    from unittest import TestCase


from chameleon.utils import byte_string


class Message(object):
    def __str__(self):
        return "message"


class ImportTestCase(TestCase):
    def test_pagetemplates(self):
        from chameleon import PageTemplate
        from chameleon import PageTemplateFile
        from chameleon import PageTemplateLoader

    def test_pagetexttemplates(self):
        from chameleon import PageTextTemplate
        from chameleon import PageTextTemplateFile


class TemplateFileTestCase(TestCase):
    @property
    def _class(self):
        from chameleon.template import BaseTemplateFile

        class TestTemplateFile(BaseTemplateFile):
            cook_count = 0

            def cook(self, body):
                self.cook_count += 1
                self._cooked = True

        return TestTemplateFile

    def setUp(self):
        self.tempdir = tempfile.mkdtemp(prefix='chameleon-tests')

    def tearDown(self):
        shutil.rmtree(self.tempdir)

    def _get_temporary_file(self):
        filename = os.path.join(self.tempdir, 'template.py')
        assert not os.path.exists(filename)
        f = open(filename, 'w')
        f.flush()
        f.close()
        return filename

    def test_cook_check(self):
        fn = self._get_temporary_file()
        template = self._class(fn)
        template.cook_check()
        self.assertEqual(template.cook_count, 1)

    def test_auto_reload(self):
        fn = self._get_temporary_file()

        # set time in past
        os.utime(fn, (0, 0))

        template = self._class(fn, auto_reload=True)
        template.cook_check()

        # a second cook check makes no difference
        template.cook_check()
        self.assertEqual(template.cook_count, 1)

        # set current time on file
        os.utime(fn, None)

        # file is reloaded
        template.cook_check()
        self.assertEqual(template.cook_count, 2)

    def test_relative_is_expanded_to_cwd(self):
        template = self._class("___does_not_exist___")
        try:
            template.cook_check()
        except IOError:
            exc = sys.exc_info()[1]
            self.assertEqual(
                os.getcwd(),
                os.path.dirname(exc.filename)
                )
        else:
            self.fail("Expected OSError.")


class RenderTestCase(TestCase):
    root = os.path.dirname(__file__)

    def find_files(self, ext):
        inputs = os.path.join(self.root, "inputs")
        outputs = os.path.join(self.root, "outputs")
        for filename in sorted(os.listdir(inputs)):
            name, extension = os.path.splitext(filename)
            if extension != ext:
                continue
            path = os.path.join(inputs, filename)

            # if there's no output file, treat document as static and
            # expect intput equal to output
            import glob
            globbed = tuple(glob.iglob(os.path.join(
                outputs, "%s*%s" % (name.split('-', 1)[0], ext))))

            if not globbed:
                self.fail("Missing output for: %s." % name)

            for output in globbed:
                name, ext = os.path.splitext(output)
                basename = os.path.basename(name)
                if '-' in basename:
                    language = basename.split('-')[1]
                else:
                    language = None

                yield path, output, language


class ZopePageTemplatesTest(RenderTestCase):
    @property
    def from_string(body):
        from ..zpt.template import PageTemplate
        return partial(PageTemplate, keep_source=True)

    @property
    def from_file(body):
        from ..zpt.template import PageTemplateFile
        return partial(PageTemplateFile, keep_source=True)

    def template(body):
        def decorator(func):
            @wraps(func)
            def wrapper(self):
                template = self.from_string(body)
                return func(self, template)

            return wrapper
        return decorator

    def error(body):
        def decorator(func):
            @wraps(func)
            def wrapper(self):
                from chameleon.exc import TemplateError
                try:
                    template = self.from_string(body)
                except TemplateError:
                    exc = sys.exc_info()[1]
                    return func(self, body, exc)
                else:
                    self.fail("Expected exception.")

            return wrapper
        return decorator

    def test_syntax_error_in_strict_mode(self):
        from chameleon.exc import ExpressionError

        self.assertRaises(
            ExpressionError,
            self.from_string,
            """<tal:block replace='bad /// ' />""",
            strict=True
            )

    def test_syntax_error_in_non_strict_mode(self):
        from chameleon.exc import ExpressionError

        body = """<tal:block replace='bad /// ' />"""
        template = self.from_string(body, strict=False)

        try:
            template()
        except ExpressionError:
            exc = sys.exc_info()[1]
            self.assertTrue(body[exc.offset:].startswith('bad ///'))
        else:
            self.fail("Expected exception")

    @error("""<tal:dummy attributes=\"dummy 'dummy'\" />""")
    def test_attributes_on_tal_tag_fails(self, body, exc):
        self.assertTrue(body[exc.offset:].startswith('dummy'))

    @error("""<tal:dummy i18n:attributes=\"foo, bar\" />""")
    def test_i18n_attributes_with_non_identifiers(self, body, exc):
        self.assertTrue(body[exc.offset:].startswith('foo,'))

    @error("""<tal:dummy repeat=\"key,value mydict.items()\">""")
    def test_repeat_syntax_error_message(self, body, exc):
        self.assertTrue(body[exc.offset:].startswith('key,value'))

    @error('''<tal:dummy><p i18n:translate="mymsgid">
            <span i18n:name="repeat"/><span i18n:name="repeat"/>
            </p></tal:dummy>''')
    def test_repeat_i18n_name_error(self, body, exc):
        self.assertTrue(body[exc.offset:].startswith('repeat'), body[exc.offset:])

    @error('''<tal:dummy>
            <span i18n:name="not_in_translation"/>
            </tal:dummy>''')
    def test_i18n_name_not_in_translation_error(self, body, exc):
        self.assertTrue(body[exc.offset:].startswith('not_in_translation'))

    def test_encoded(self):
        filename = '074-encoded-template.pt'
        with open(os.path.join(self.root, 'inputs', filename), 'rb') as f:
            body = f.read()

        self.from_string(body)

    def test_utf8_encoded(self):
        filename = '073-utf8-encoded.pt'
        with open(os.path.join(self.root, 'inputs', filename), 'rb') as f:
            body = f.read()

        self.from_string(body)

    def test_unicode_decode_error(self):
        template = self.from_file(
            os.path.join(self.root, 'inputs', 'greeting.pt')
            )

        string = native = "the artist formerly known as ƤŗíƞĆě"
        try:
            string = string.decode('utf-8')
        except AttributeError:
            pass

        class name:
            @staticmethod
            def __html__():
                # This raises a decoding exception
                string.encode('utf-8').decode('ascii')

                self.fail("Expected exception raised.")

        try:
            template(name=name)
        except UnicodeDecodeError:
            exc = sys.exc_info()[1]
            formatted = str(exc)

            # There's a marker under the expression that has the
            # unicode decode error
            self.assertTrue('^^^^^' in formatted)
            self.assertTrue(native in formatted)
        else:
            self.fail("expected error")

    def test_custom_encoding_for_str_or_bytes_in_content(self):
        string = '<div>Тест${text}</div>'
        try:
            string = string.decode('utf-8')
        except AttributeError:
            pass

        template = self.from_string(string, encoding="windows-1251")

        text = 'Тест'

        try:
            text = text.decode('utf-8')
        except AttributeError:
            pass

        rendered = template(text=text.encode('windows-1251'))

        self.assertEqual(
            rendered,
            string.replace('${text}', text)
            )

    def test_custom_encoding_for_str_or_bytes_in_attributes(self):
        string = '<img tal="Тест${text}" />'
        try:
            string = string.decode('utf-8')
        except AttributeError:
            pass

        template = self.from_string(string, encoding="windows-1251")

        text = 'Тест'

        try:
            text = text.decode('utf-8')
        except AttributeError:
            pass

        rendered = template(text=text.encode('windows-1251'))

        self.assertEqual(
            rendered,
            string.replace('${text}', text)
            )

    def test_null_translate_function(self):
        template = self.from_string('${test}', translate=None)
        rendered = template(test=object())
        self.assertTrue('object' in rendered)

    def test_object_substitution_coerce_to_str(self):
        template = self.from_string('${test}', translate=None)

        class dummy(object):
            def __repr__(inst):
                self.fail("call not expected")

            def __str__(inst):
                return '<dummy>'

        rendered = template(test=dummy())
        self.assertEqual(rendered, '&lt;dummy&gt;')

    def test_repr(self):
        template = self.from_file(
            os.path.join(self.root, 'inputs', 'hello_world.pt')
            )
        self.assertTrue(template.filename in repr(template))

    def test_underscore_variable(self):
        template = self.from_string(
            "<div tal:define=\"_dummy 'foo'\">${_dummy}</div>"
            )
        self.assertTrue(template(), "<div>foo</div>")

    def test_trim_attribute_space(self):
        document = '''<div
                  class="document"
                  id="test"
                  tal:attributes="class string:${default} test"
            />'''

        result1 = self.from_string(
            document)()

        result2 = self.from_string(
            document, trim_attribute_space=True)()

        self.assertEqual(result1.count(" "), 49)
        self.assertEqual(result2.count(" "), 4)
        self.assertTrue(" />" in result1)
        self.assertTrue(" />" in result2)

    def test_exception(self):
        from traceback import format_exception_only

        template = self.from_string(
            "<div tal:define=\"dummy foo\">${dummy}</div>"
            )
        try:
            template()
        except:
            exc = sys.exc_info()[1]
            formatted = str(exc)
            self.assertFalse('NameError:' in formatted)
            self.assertTrue('foo' in formatted)
            self.assertTrue('(line 1: col 23)' in formatted)

            formatted_exc = "\n".join(format_exception_only(type(exc), exc))
            self.assertTrue('NameError: foo' in formatted_exc)
        else:
            self.fail("expected error")

    def test_create_formatted_exception(self):
        from chameleon.utils import create_formatted_exception

        exc = create_formatted_exception(NameError('foo'), NameError, str)
        self.assertEqual(exc.args, ('foo', ))

        class MyNameError(NameError):
            def __init__(self, boo):
                NameError.__init__(self, boo)
                self.bar = boo

        exc = create_formatted_exception(MyNameError('foo'), MyNameError, str)
        self.assertEqual(exc.args, ('foo', ))
        self.assertEqual(exc.bar, 'foo')

    def test_create_formatted_exception_no_subclass(self):
        from chameleon.utils import create_formatted_exception

        class DifficultMetaClass(type):
            def __init__(self, class_name, bases, namespace):
                if not bases == (BaseException, ):
                    raise TypeError(bases)

        Difficult = DifficultMetaClass('Difficult', (BaseException, ), {'args': ()})

        exc = create_formatted_exception(Difficult(), Difficult, str)
        self.assertEqual(exc.args, ())

    def test_error_handler_makes_safe_copy(self):
        calls = []

        class TestException(Exception):
            def __init__(self, *args, **kwargs):
                calls.append((args, kwargs))

        def _render(stream, econtext, rcontext):
            exc = TestException('foo', bar='baz')
            rcontext['__error__'] = ('expression', 1, 42, 'test.pt', exc),
            raise exc

        template = self.from_string("")
        template._render = _render
        try:
            template()
        except TestException:
            self.assertEqual(calls, [(('foo', ), {'bar': 'baz'})])
            exc = sys.exc_info()[1]
            formatted = str(exc)
            self.assertTrue('TestException' in formatted)
            self.assertTrue('"expression"' in formatted)
            self.assertTrue('(line 1: col 42)' in formatted)
        else:
            self.fail("unexpected error")

    def test_double_underscore_variable(self):
        from chameleon.exc import TranslationError
        self.assertRaises(
            TranslationError, self.from_string,
            "<div tal:define=\"__dummy 'foo'\">${__dummy}</div>",
            )

    def test_compiler_internals_are_disallowed(self):
        from chameleon.compiler import COMPILER_INTERNALS_OR_DISALLOWED
        from chameleon.exc import TranslationError

        for name in COMPILER_INTERNALS_OR_DISALLOWED:
            body = "<d tal:define=\"%s 'foo'\">${%s}</d>" % (name, name)
            self.assertRaises(TranslationError, self.from_string, body)

    def test_simple_translate_mapping(self):
        template = self.from_string(
            '<div i18n:translate="">'
            '<span i18n:name="name">foo</span>'
            '</div>')

        self.assertEqual(template(), '<div><span>foo</span></div>')

    def test_translate_is_not_an_internal(self):
        macro = self.from_string('<span i18n:translate="">bar</span>')
        template = self.from_string(
            '''
            <tal:defs define="translate string:">
              <span i18n:translate="">foo</span>
              <metal:macro use-macro="macro" />
            </tal:defs>
            ''')

        result = template(macro=macro)
        self.assertTrue('foo' in result)
        self.assertTrue('foo' in result)

    def test_literal_false(self):
        template = self.from_string(
            '<input type="input" tal:attributes="checked False" />'
            '<input type="input" tal:attributes="checked True" />'
            '<input type="input" tal:attributes="checked None" />'
            '<input type="input" tal:attributes="checked default" />',
            literal_false=True,
            )

        self.assertEqual(
            template(),
            '<input type="input" checked="False" />'
            '<input type="input" checked="True" />'
            '<input type="input" />'
            '<input type="input" />',
            template.source
            )

    def test_boolean_attributes(self):
        template = self.from_string(
            '<input type="input" tal:attributes="checked False" />'
            '<input type="input" tal:attributes="checked True" />'
            '<input type="input" tal:attributes="checked None" />'
            '<input type="input" tal:attributes="checked \'\'" />'
            '<input type="input" tal:attributes="checked default" />'
            '<input type="input" checked="checked" tal:attributes="checked default" />',
            boolean_attributes=set(['checked'])
            )

        self.assertEqual(
            template(),
            '<input type="input" />'
            '<input type="input" checked="checked" />'
            '<input type="input" />'
            '<input type="input" />'
            '<input type="input" />'
            '<input type="input" checked="checked" />',
            template.source
            )

    def test_default_debug_flag(self):
        from chameleon.config import DEBUG_MODE
        template = self.from_file(
            os.path.join(self.root, 'inputs', 'hello_world.pt'),
            )
        self.assertEqual(template.debug, DEBUG_MODE)
        self.assertTrue('debug' not in template.__dict__)

    def test_debug_flag_on_string(self):
        from chameleon.loader import ModuleLoader

        with open(os.path.join(self.root, 'inputs', 'hello_world.pt')) as f:
            source = f.read()

        template = self.from_string(source, debug=True)

        self.assertTrue(template.debug)
        self.assertTrue(isinstance(template.loader, ModuleLoader))

    def test_debug_flag_on_file(self):
        from chameleon.loader import ModuleLoader
        template = self.from_file(
            os.path.join(self.root, 'inputs', 'hello_world.pt'),
            debug=True,
            )
        self.assertTrue(template.debug)
        self.assertTrue(isinstance(template.loader, ModuleLoader))

    def test_tag_mismatch(self):
        from chameleon.exc import ParseError

        try:
            self.from_string("""
            <div metal:use-macro="layout">
            <div metal:fill-slot="name"></dav>
            </div>
            """)
        except ParseError:
            exc = sys.exc_info()[1]
            self.assertTrue("</dav>" in str(exc))
        else:
            self.fail("Expected error.")


class ZopeTemplatesTestSuite(RenderTestCase):
    def setUp(self):
        self.temp_path = temp_path = tempfile.mkdtemp()

        @self.addCleanup
        def cleanup(path=temp_path):
            shutil.rmtree(path)

    def test_pt_files(self):
        from ..zpt.template import PageTemplateFile

        class Literal(object):
            def __init__(self, s):
                self.s = s

            def __html__(self):
                return self.s

            def __str__(self):
                raise RuntimeError(
                    "%r is a literal." % self.s)

        from chameleon.loader import TemplateLoader
        loader = TemplateLoader(os.path.join(self.root, "inputs"))

        self.execute(
            ".pt", PageTemplateFile,
            literal=Literal("<div>Hello world!</div>"),
            content="<div>Hello world!</div>",
            message=Message(),
            load=loader.bind(PageTemplateFile),
            )

    def test_txt_files(self):
        from ..zpt.template import PageTextTemplateFile
        self.execute(".txt", PageTextTemplateFile)

    def execute(self, ext, factory, **kwargs):
        def translate(msgid, domain=None, mapping=None, context=None,
                      target_language=None, default=None):
            if default is None:
                default = str(msgid)

            if isinstance(msgid, Message):
                default = "Message"

            if mapping:
                default = re.sub(r'\${([a-z_]+)}', r'%(\1)s', default) % \
                          mapping

            if target_language is None:
                return default

            if domain is None:
                with_domain = ""
            else:
                with_domain = " with domain '%s'" % domain

            stripped = default.rstrip('\n ')
            return "%s ('%s' translation into '%s'%s)%s" % (
                stripped, msgid, target_language, with_domain,
                default[len(stripped):]
                )

        for input_path, output_path, language in self.find_files(ext):
            # Make friendly title so we can locate the generated
            # source when debugging
            self.shortDescription = lambda: input_path

            # When input path contaiins the string 'implicit-i18n', we
            # enable "implicit translation".
            implicit_i18n = 'implicit-i18n' in input_path
            implicit_i18n_attrs = ("alt", "title") if implicit_i18n else ()

            template = factory(
                input_path,
                keep_source=True,
                strict=False,
                implicit_i18n_translate=implicit_i18n,
                implicit_i18n_attributes=implicit_i18n_attrs,
                )

            params = kwargs.copy()
            params.update({
                'translate': translate,
                'target_language': language,
                })

            template.cook_check()

            try:
                got = template.render(**params)
            except:
                import traceback
                e = traceback.format_exc()
                self.fail("%s\n\n    Example source:\n\n%s" % (e, "\n".join(
                    ["%#03.d%s" % (lineno + 1, line and " " + line or "")
                     for (lineno, line) in
                     enumerate(template.source.split(
                         '\n'))])))

            if isinstance(got, byte_string):
                got = got.decode('utf-8')

            from doctest import OutputChecker
            checker = OutputChecker()

            if not os.path.exists(output_path):
                output = template.body
            else:
                with open(output_path, 'rb') as f:
                    output = f.read()

            from chameleon.utils import read_xml_encoding
            from chameleon.utils import detect_encoding

            if template.content_type == 'text/xml':
                encoding = read_xml_encoding(output) or \
                           template.default_encoding
            else:
                content_type, encoding = detect_encoding(
                    output, template.default_encoding)

            want = output.decode(encoding)

            if checker.check_output(want, got, 0) is False:
                from doctest import Example
                example = Example(input_path, want)
                diff = checker.output_difference(
                    example, got, 0)
                self.fail("(%s) - \n%s\n\nCode:\n%s" % (
                    input_path, diff.rstrip('\n'),
                    template.source.encode('utf-8')))

########NEW FILE########
__FILENAME__ = test_tokenizer
import sys

from unittest import TestCase


class TokenizerTest(TestCase):
    def test_sample_files(self):
        import os
        import traceback
        path = os.path.join(os.path.dirname(__file__), "inputs")
        for filename in os.listdir(path):
            if not filename.endswith('.xml'):
                continue
            f = open(os.path.join(path, filename), 'rb')
            source = f.read()
            f.close()

            from ..utils import read_encoded
            try:
                want = read_encoded(source)
            except UnicodeDecodeError:
                exc = sys.exc_info()[1]
                self.fail("%s - %s" % (exc, filename))

            from ..tokenize import iter_xml
            try:
                tokens = iter_xml(want)
                got = "".join(tokens)
            except:
                self.fail(traceback.format_exc())

            from doctest import OutputChecker
            checker = OutputChecker()

            if checker.check_output(want, got, 0) is False:
                from doctest import Example
                example = Example(f.name, want)
                diff = checker.output_difference(
                    example, got, 0)
                self.fail("(%s) - \n%s" % (f.name, diff))

    def test_token(self):
        from chameleon.tokenize import Token
        token = Token("abc", 1)

        self.assertTrue(isinstance(token[1:], Token))
        self.assertEqual(token[1:].pos, 2)

########NEW FILE########
__FILENAME__ = tokenize
# http://code.activestate.com/recipes/65125-xml-lexing-shallow-parsing/
# by Paul Prescod
# licensed under the PSF License
#
# modified to capture all non-overlapping parts of tokens

import re

try:
    str = unicode
except NameError:
    pass

class recollector:
    def __init__(self):
        self.res = {}

    def add(self, name, reg ):
        re.compile(reg)  # check that it is valid
        self.res[name] = reg % self.res

collector = recollector()
a = collector.add

a("TextSE", "[^<]+")
a("UntilHyphen", "[^-]*-")
a("Until2Hyphens", "%(UntilHyphen)s(?:[^-]%(UntilHyphen)s)*-")
a("CommentCE", "%(Until2Hyphens)s>?")
a("UntilRSBs", "[^\\]]*](?:[^\\]]+])*]+")
a("CDATA_CE", "%(UntilRSBs)s(?:[^\\]>]%(UntilRSBs)s)*>" )
a("S", "[ \\n\\t\\r]+")
a("Simple", "[^\"'>/]+")
a("NameStrt", "[A-Za-z_:]|[^\\x00-\\x7F]")
a("NameChar", "[A-Za-z0-9_:.-]|[^\\x00-\\x7F]")
a("Name", "(?:%(NameStrt)s)(?:%(NameChar)s)*")
a("QuoteSE", "\"[^\"]*\"|'[^']*'")
a("DT_IdentSE" , "%(S)s%(Name)s(?:%(S)s(?:%(Name)s|%(QuoteSE)s))*" )
a("MarkupDeclCE" , "(?:[^\\]\"'><]+|%(QuoteSE)s)*>" )
a("S1", "[\\n\\r\\t ]")
a("UntilQMs", "[^?]*\\?+")
a("PI_Tail" , "\\?>|%(S1)s%(UntilQMs)s(?:[^>?]%(UntilQMs)s)*>" )
a("DT_ItemSE",
  "<(?:!(?:--%(Until2Hyphens)s>|[^-]%(MarkupDeclCE)s)|"
  "\\?%(Name)s(?:%(PI_Tail)s))|%%%(Name)s;|%(S)s"
)
a("DocTypeCE" ,
"%(DT_IdentSE)s(?:%(S)s)?(?:\\[(?:%(DT_ItemSE)s)*](?:%(S)s)?)?>?" )
a("DeclCE",
  "--(?:%(CommentCE)s)?|\\[CDATA\\[(?:%(CDATA_CE)s)?|"
  "DOCTYPE(?:%(DocTypeCE)s)?")
a("PI_CE", "%(Name)s(?:%(PI_Tail)s)?")
a("EndTagCE", "%(Name)s(?:%(S)s)?>?")
a("AttValSE", "\"[^\"]*\"|'[^']*'")
a("ElemTagCE",
  "(%(Name)s)(?:(%(S)s)(%(Name)s)(((?:%(S)s)?=(?:%(S)s)?)"
  "(?:%(AttValSE)s|%(Simple)s)|(?!(?:%(S)s)?=)))*(?:%(S)s)?(/?>)?")
a("MarkupSPE",
  "<(?:!(?:%(DeclCE)s)?|"
  "\\?(?:%(PI_CE)s)?|/(?:%(EndTagCE)s)?|(?:%(ElemTagCE)s)?)")
a("XML_SPE", "%(TextSE)s|%(MarkupSPE)s")
a("XML_MARKUP_ONLY_SPE", "%(MarkupSPE)s")
a("ElemTagSPE", "<|%(Name)s")

re_xml_spe = re.compile(collector.res['XML_SPE'])
re_markup_only_spe = re.compile(collector.res['XML_MARKUP_ONLY_SPE'])


def iter_xml(body, filename=None):
    for match in re_xml_spe.finditer(body):
        string = match.group()
        pos = match.start()
        yield Token(string, pos, body, filename)


def iter_text(body, filename=None):
    yield Token(body, 0, body, filename)


class Token(str):
    __slots__ = "pos", "source", "filename"

    def __new__(cls, string, pos=0, source=None, filename=None):
        inst = str.__new__(cls, string)
        inst.pos = pos
        inst.source = source
        inst.filename = filename or ""
        return inst

    def __getslice__(self, i, j):
        slice = str.__getslice__(self, i, j)
        return Token(slice, self.pos + i, self.source, self.filename)

    def __getitem__(self, index):
        s = str.__getitem__(self, index)
        if isinstance(index, slice):
            return Token(
                s, self.pos + (index.start or 0), self.source, self.filename)
        return s

    def __add__(self, other):
        if other is None:
            return self

        return Token(
            str.__add__(self, other), self.pos, self.source, self.filename)

    def __eq__(self, other):
        return str.__eq__(self, other)

    def __hash__(self):
        return str.__hash__(self)

    def replace(self, *args):
        s = str.replace(self, *args)
        return Token(s, self.pos, self.source, self.filename)

    def split(self, *args):
        l = str.split(self, *args)
        pos = self.pos
        for i, s in enumerate(l):
            l[i] = Token(s, pos, self.source, self.filename)
            pos += len(s)
        return l

    def strip(self, *args):
        return self.lstrip(*args).rstrip(*args)

    def lstrip(self, *args):
        s = str.lstrip(self, *args)
        return Token(
            s, self.pos + len(self) - len(s), self.source, self.filename)

    def rstrip(self, *args):
        s = str.rstrip(self, *args)
        return Token(s, self.pos, self.source, self.filename)

    @property
    def location(self):
        if self.source is None:
            return 0, self.pos

        body = self.source[:self.pos]
        line = body.count('\n')
        return line + 1, self.pos - body.rfind('\n', 0) - 1

########NEW FILE########
__FILENAME__ = utils
import os
import re
import sys
import codecs
import logging

from copy import copy

version = sys.version_info[:3]

try:
    import ast as _ast
except ImportError:
    from chameleon import ast25 as _ast


class ASTProxy(object):
    aliases = {
        # Python 3.3
        'TryExcept': 'Try',
        'TryFinally': 'Try',
        }

    def __getattr__(self, name):
        return _ast.__dict__.get(name) or getattr(_ast, self.aliases[name])


ast = ASTProxy()

log = logging.getLogger('chameleon.utils')

# Python 2
if version < (3, 0, 0):
    import htmlentitydefs
    import __builtin__ as builtins

    from .py25 import raise_with_traceback

    chr = unichr
    native_string = str
    decode_string = unicode
    encode_string = str
    unicode_string = unicode
    string_type = basestring
    byte_string = str

    def safe_native(s, encoding='utf-8'):
        if not isinstance(s, unicode):
            s = decode_string(s, encoding, 'replace')

        return s.encode(encoding)

# Python 3
else:
    from html import entities as htmlentitydefs
    import builtins

    byte_string = bytes
    string_type = str
    native_string = str
    decode_string = bytes.decode
    encode_string = lambda s: bytes(s, 'utf-8')
    unicode_string = str

    def safe_native(s, encoding='utf-8'):
        if not isinstance(s, str):
            s = decode_string(s, encoding, 'replace')

        return s

    def raise_with_traceback(exc, tb):
        exc.__traceback__ = tb
        raise exc

def text_(s, encoding='latin-1', errors='strict'):
    """ If ``s`` is an instance of ``byte_string``, return
    ``s.decode(encoding, errors)``, otherwise return ``s``"""
    if isinstance(s, byte_string):
        return s.decode(encoding, errors)
    return s

entity_re = re.compile(r'&(#?)(x?)(\d{1,5}|\w{1,8});')

module_cache = {}

xml_prefixes = (
    (codecs.BOM_UTF8, 'utf-8-sig'),
    (codecs.BOM_UTF16_BE, 'utf-16-be'),
    (codecs.BOM_UTF16_LE, 'utf-16-le'),
    (codecs.BOM_UTF16, 'utf-16'),
    (codecs.BOM_UTF32_BE, 'utf-32-be'),
    (codecs.BOM_UTF32_LE, 'utf-32-le'),
    (codecs.BOM_UTF32, 'utf-32'),
    )


def _has_encoding(encoding):
    try:
        "".encode(encoding)
    except LookupError:
        return False
    else:
        return True


# Precomputed prefix table
_xml_prefixes = tuple(
    (bom, str('<?xml').encode(encoding), encoding)
    for bom, encoding in reversed(xml_prefixes)
    if _has_encoding(encoding)
    )

_xml_decl = encode_string("<?xml")

RE_META = re.compile(
    r'\s*<meta\s+http-equiv=["\']?Content-Type["\']?'
    r'\s+content=["\']?([^;]+);\s*charset=([^"\']+)["\']?\s*/?\s*>\s*',
    re.IGNORECASE
    )

RE_ENCODING = re.compile(
    r'encoding\s*=\s*(?:"|\')(?P<encoding>[\w\-]+)(?:"|\')'.encode('ascii'),
    re.IGNORECASE
    )


def read_encoded(data):
    return read_bytes(data, "utf-8")[0]


def read_bytes(body, default_encoding):
    for bom, prefix, encoding in _xml_prefixes:
        if body.startswith(bom):
            document = body.decode(encoding)
            return document, encoding, \
                   "text/xml" if document.startswith("<?xml") else None

        if prefix != encode_string('<?xml') and body.startswith(prefix):
            return body.decode(encoding), encoding, "text/xml"

    if body.startswith(_xml_decl):
        content_type = "text/xml"

        encoding = read_xml_encoding(body) or default_encoding
    else:
        content_type, encoding = detect_encoding(body, default_encoding)

    return body.decode(encoding), encoding, content_type


def detect_encoding(body, default_encoding):
    if not isinstance(body, str):
        body = body.decode('ascii', 'ignore')

    match = RE_META.search(body)
    if match is not None:
        return match.groups()

    return None, default_encoding


def read_xml_encoding(body):
    if body.startswith('<?xml'.encode('ascii')):
        match = RE_ENCODING.search(body)
        if match is not None:
            return match.group('encoding').decode('ascii')


def mangle(filename):
    """Mangles template filename into top-level Python module name.

    >>> mangle('hello_world.pt')
    'hello_world'

    >>> mangle('foo.bar.baz.pt')
    'foo_bar_baz'

    >>> mangle('foo-bar-baz.pt')
    'foo_bar_baz'

    """

    base, ext = os.path.splitext(filename)
    return base.replace('.', '_').replace('-', '_')


def char2entity(c):
    cp = ord(c)
    name = htmlentitydefs.codepoint2name.get(cp)
    return '&%s;' % name if name is not None else '&#%d;' % cp


def substitute_entity(match, n2cp=htmlentitydefs.name2codepoint):
    ent = match.group(3)

    if match.group(1) == "#":
        if match.group(2) == '':
            return chr(int(ent))
        elif match.group(2) == 'x':
            return chr(int('0x' + ent, 16))
    else:
        cp = n2cp.get(ent)

        if cp:
            return chr(cp)
        else:
            return match.group()


def create_formatted_exception(exc, cls, formatter):
    try:
        try:
            new = type(cls.__name__, (cls, Exception), {
                '__str__': formatter,
                '__new__': BaseException.__new__,
                '__module__': cls.__module__,
                })
        except TypeError:
            new = cls

        try:
            inst = BaseException.__new__(new)
        except TypeError:
            inst = cls.__new__(new)

        BaseException.__init__(inst, *exc.args)
        inst.__dict__ = exc.__dict__

        return inst
    except ValueError:
        name = type(exc).__name__
        log.warn("Unable to copy exception of type '%s'." % name)
        raise TypeError(exc)


def unescape(string):
    for name in ('lt', 'gt', 'quot'):
        cp = htmlentitydefs.name2codepoint[name]
        string = string.replace('&%s;' % name, chr(cp))

    return string


_concat = unicode_string("").join


def join(stream):
    """Concatenate stream.

    >>> print(join(('Hello', ' ', 'world')))
    Hello world

    >>> join(('Hello', 0))
    Traceback (most recent call last):
     ...
    TypeError: ... expected ...

    """

    try:
        return _concat(stream)
    except:
        # Loop through stream and coerce each element into unicode;
        # this should raise an exception
        for element in stream:
            unicode_string(element)

        # In case it didn't, re-raise the original exception
        raise


def decode_htmlentities(string):
    """
    >>> native_string(decode_htmlentities('&amp;amp;'))
    '&amp;'

    """

    decoded = entity_re.subn(substitute_entity, string)[0]

    # preserve input token data
    return string.replace(string, decoded)


# Taken from zope.dottedname
def _resolve_dotted(name, module=None):
    name = name.split('.')
    if not name[0]:
        if module is None:
            raise ValueError("relative name without base module")
        module = module.split('.')
        name.pop(0)
        while not name[0]:
            module.pop()
            name.pop(0)
        name = module + name

    used = name.pop(0)
    found = __import__(used)
    for n in name:
        used += '.' + n
        try:
            found = getattr(found, n)
        except AttributeError:
            __import__(used)
            found = getattr(found, n)

    return found


def resolve_dotted(dotted):
    if not dotted in module_cache:
        resolved = _resolve_dotted(dotted)
        module_cache[dotted] = resolved
    return module_cache[dotted]


def limit_string(s, max_length=53):
    if len(s) > max_length:
        return s[:max_length - 3] + '...'

    return s


def format_kwargs(kwargs):
    items = []
    for name, value in kwargs.items():
        if isinstance(value, string_type):
            short = limit_string(value)
            items.append((name, short.replace('\n', '\\n')))
        elif isinstance(value, (int, float)):
            items.append((name, value))
        elif isinstance(value, dict):
            items.append((name, '{...} (%d)' % len(value)))
        else:
            items.append((name,
                "<%s %s at %s>" % (
                    type(value).__name__,
                    getattr(value, '__name__', "-"),
                    hex(abs(id(value))))))

    return ["%s: %s" % item for item in items]


class callablestr(str):
    __slots__ = ()

    def __call__(self):
        return self


class callableint(int):
    __slots__ = ()

    def __call__(self):
        return self


class descriptorstr(object):
    __slots__ = "function", "__name__"

    def __init__(self, function):
        self.function = function
        self.__name__ = function.__name__

    def __get__(self, context, cls):
        return callablestr(self.function(context))


class descriptorint(object):
    __slots__ = "function", "__name__"

    def __init__(self, function):
        self.function = function
        self.__name__ = function.__name__

    def __get__(self, context, cls):
        return callableint(self.function(context))


class DebuggingOutputStream(list):
    def append(self, value):
        if not isinstance(value, string_type):
            raise TypeError(value)

        unicode_string(value)
        list.append(self, value)


class Scope(dict):
    set_local = setLocal = dict.__setitem__

    __slots__ = "set_global",

    def __new__(cls, *args):
        inst = dict.__new__(cls, *args)
        inst.set_global = inst.__setitem__
        return inst

    def __getitem__(self, key):
        try:
            return dict.__getitem__(self, key)
        except KeyError:
            raise NameError(key)

    @property
    def vars(self):
        return self

    def copy(self):
        inst = Scope(self)
        inst.set_global = self.set_global
        return inst


class ListDictProxy(object):
    def __init__(self, l):
        self._l = l

    def get(self, key):
        return self._l[-1].get(key)


class Markup(unicode_string):
    """Wraps a string to always render as structure.

    >>> Markup('<br />')
    s'<br />'
    """

    def __html__(self):
        return unicode_string(self)

    def __repr__(self):
        return "s'%s'" % self

########NEW FILE########
__FILENAME__ = loader
from chameleon.loader import TemplateLoader as BaseLoader
from chameleon.zpt import template


class TemplateLoader(BaseLoader):
    formats = {
        "xml": template.PageTemplateFile,
        "text": template.PageTextTemplateFile,
        }

    default_format = "xml"

    def __init__(self, *args, **kwargs):
        formats = kwargs.pop('formats', None)
        if formats is not None:
            self.formats = formats

        super(TemplateLoader, self).__init__(*args, **kwargs)

    def load(self, filename, format=None):
        """Load and return a template file.

        The format parameter determines will parse the file. Valid
        options are `xml` and `text`.
        """

        cls = self.formats[format or self.default_format]
        return super(TemplateLoader, self).load(filename, cls)

    __getitem__ = load

########NEW FILE########
__FILENAME__ = program
import re

try:
    import ast
except ImportError:
    from chameleon import ast25 as ast

try:
    str = unicode
except NameError:
    long = int

from functools import partial
from copy import copy

from ..program import ElementProgram

from ..namespaces import XML_NS
from ..namespaces import XMLNS_NS
from ..namespaces import I18N_NS as I18N
from ..namespaces import TAL_NS as TAL
from ..namespaces import METAL_NS as METAL
from ..namespaces import META_NS as META

from ..astutil import Static
from ..astutil import parse
from ..astutil import marker

from .. import tal
from .. import metal
from .. import i18n
from .. import nodes

from ..exc import LanguageError
from ..exc import ParseError
from ..exc import CompilationError

from ..utils import decode_htmlentities

try:
    str = unicode
except NameError:
    long = int


missing = object()

re_trim = re.compile(r'($\s+|\s+^)', re.MULTILINE)

EMPTY_DICT = Static(ast.Dict(keys=[], values=[]))


def skip(node):
    return node


def wrap(node, *wrappers):
    for wrapper in reversed(wrappers):
        node = wrapper(node)
    return node


def validate_attributes(attributes, namespace, whitelist):
    for ns, name in attributes:
        if ns == namespace and name not in whitelist:
            raise CompilationError(
                "Bad attribute for namespace '%s'" % ns, name
                )


class MacroProgram(ElementProgram):
    """Visitor class that generates a program for the ZPT language."""

    DEFAULT_NAMESPACES = {
        'xmlns': XMLNS_NS,
        'xml': XML_NS,
        'tal': TAL,
        'metal': METAL,
        'i18n': I18N,
        'meta': META,
        }

    DROP_NS = TAL, METAL, I18N, META

    VARIABLE_BLACKLIST = "default", "repeat", "nothing", \
                         "convert", "decode", "translate"

    _interpolation_enabled = True
    _whitespace = "\n"
    _last = ""

    # Macro name (always trivial for a macro program)
    name = None

    # This default marker value has the semantics that if an
    # expression evaluates to that value, the expression default value
    # is returned. For an attribute, if there is no default, this
    # means that the attribute is dropped.
    default_marker = None

    # Escape mode (true value means XML-escape)
    escape = True

    # Attributes which should have boolean behavior (on true, the
    # value takes the attribute name, on false, the attribute is
    # dropped)
    boolean_attributes = set()

    # If provided, this should be a set of attributes for implicit
    # translation. Any attribute whose name is included in the set
    # will be translated even without explicit markup. Note that all
    # values should be lowercase strings.
    implicit_i18n_attributes = set()

    # If set, text will be translated even without explicit markup.
    implicit_i18n_translate = False

    # If set, additional attribute whitespace will be stripped.
    trim_attribute_space = False

    def __init__(self, *args, **kwargs):
        # Internal array for switch statements
        self._switches = []

        # Internal array for current use macro level
        self._use_macro = []

        # Internal array for current interpolation status
        self._interpolation = [True]

        # Internal dictionary of macro definitions
        self._macros = {}

        # Apply default values from **kwargs to self
        self._pop_defaults(
            kwargs,
            'boolean_attributes',
            'default_marker',
            'escape',
            'implicit_i18n_translate',
            'implicit_i18n_attributes',
            'trim_attribute_space',
            )

        super(MacroProgram, self).__init__(*args, **kwargs)

    @property
    def macros(self):
        macros = list(self._macros.items())
        macros.append((None, nodes.Sequence(self.body)))

        return tuple(
            nodes.Macro(name, [nodes.Context(node)])
            for name, node in macros
            )

    def visit_default(self, node):
        return nodes.Text(node)

    def visit_element(self, start, end, children):
        ns = start['ns_attrs']

        for (prefix, attr), encoded in tuple(ns.items()):
            if prefix == TAL:
                ns[prefix, attr] = decode_htmlentities(encoded)

        # Validate namespace attributes
        validate_attributes(ns, TAL, tal.WHITELIST)
        validate_attributes(ns, METAL, metal.WHITELIST)
        validate_attributes(ns, I18N, i18n.WHITELIST)

        # Check attributes for language errors
        self._check_attributes(start['namespace'], ns)

        # Remember whitespace for item repetition
        if self._last is not None:
            self._whitespace = "\n" + " " * len(self._last.rsplit('\n', 1)[-1])

        # Set element-local whitespace
        whitespace = self._whitespace

        # Set up switch
        try:
            clause = ns[TAL, 'switch']
        except KeyError:
            switch = None
        else:
            value = nodes.Value(clause)
            switch = value, nodes.Copy(value)

        self._switches.append(switch)

        body = []

        # Include macro
        use_macro = ns.get((METAL, 'use-macro'))
        extend_macro = ns.get((METAL, 'extend-macro'))
        if use_macro or extend_macro:
            omit = True
            slots = []
            self._use_macro.append(slots)

            if use_macro:
                inner = nodes.UseExternalMacro(
                    nodes.Value(use_macro), slots, False
                    )
            else:
                inner = nodes.UseExternalMacro(
                    nodes.Value(extend_macro), slots, True
                    )
        # -or- include tag
        else:
            content = nodes.Sequence(body)

            # tal:content
            try:
                clause = ns[TAL, 'content']
            except KeyError:
                pass
            else:
                key, value = tal.parse_substitution(clause)
                xlate = True if ns.get((I18N, 'translate')) == '' else False
                content = self._make_content_node(value, content, key, xlate)

                if end is None:
                    # Make sure start-tag has opening suffix.
                    start['suffix']  = ">"

                    # Explicitly set end-tag.
                    end = {
                        'prefix': '</',
                        'name': start['name'],
                        'space': '',
                        'suffix': '>'
                        }

            # i18n:translate
            try:
                clause = ns[I18N, 'translate']
            except KeyError:
                pass
            else:
                dynamic = ns.get((TAL, 'content')) or ns.get((TAL, 'replace'))

                if not dynamic:
                    content = nodes.Translate(clause, content)

            # tal:attributes
            try:
                clause = ns[TAL, 'attributes']
            except KeyError:
                TAL_ATTRIBUTES = []
            else:
                TAL_ATTRIBUTES = tal.parse_attributes(clause)

            # i18n:attributes
            try:
                clause = ns[I18N, 'attributes']
            except KeyError:
                I18N_ATTRIBUTES = {}
            else:
                I18N_ATTRIBUTES = i18n.parse_attributes(clause)

            # Prepare attributes from TAL language
            prepared = tal.prepare_attributes(
                start['attrs'], TAL_ATTRIBUTES,
                I18N_ATTRIBUTES, ns, self.DROP_NS
                )

            # Create attribute nodes
            STATIC_ATTRIBUTES = self._create_static_attributes(prepared)
            ATTRIBUTES = self._create_attributes_nodes(
                prepared, I18N_ATTRIBUTES, STATIC_ATTRIBUTES
                )

            # Start- and end nodes
            start_tag = nodes.Start(
                start['name'],
                self._maybe_trim(start['prefix']),
                self._maybe_trim(start['suffix']),
                ATTRIBUTES
                )

            end_tag = nodes.End(
                end['name'],
                end['space'],
                self._maybe_trim(end['prefix']),
                self._maybe_trim(end['suffix']),
                ) if end is not None else None

            # tal:omit-tag
            try:
                clause = ns[TAL, 'omit-tag']
            except KeyError:
                omit = False
            else:
                clause = clause.strip()

                if clause == "":
                    omit = True
                else:
                    expression = nodes.Negate(nodes.Value(clause))
                    omit = expression

                    # Wrap start- and end-tags in condition
                    start_tag = nodes.Condition(expression, start_tag)

                    if end_tag is not None:
                        end_tag = nodes.Condition(expression, end_tag)

            if omit is True or start['namespace'] in self.DROP_NS:
                inner = content
            else:
                inner = nodes.Element(
                    start_tag,
                    end_tag,
                    content,
                    )

                # Assign static attributes dictionary to "attrs" value
                inner = nodes.Define(
                    [nodes.Alias(["attrs"], STATIC_ATTRIBUTES or EMPTY_DICT)],
                    inner,
                    )

                if omit is not False:
                    inner = nodes.Cache([omit], inner)

            # tal:replace
            try:
                clause = ns[TAL, 'replace']
            except KeyError:
                pass
            else:
                key, value = tal.parse_substitution(clause)
                xlate = True if ns.get((I18N, 'translate')) == '' else False
                inner = self._make_content_node(value, inner, key, xlate)

        # metal:define-slot
        try:
            clause = ns[METAL, 'define-slot']
        except KeyError:
            DEFINE_SLOT = skip
        else:
            DEFINE_SLOT = partial(nodes.DefineSlot, clause)

        # tal:define
        try:
            clause = ns[TAL, 'define']
        except KeyError:
            DEFINE = skip
        else:
            defines = tal.parse_defines(clause)
            if defines is None:
                raise ParseError("Invalid define syntax.", clause)

            DEFINE = partial(
                nodes.Define,
                [nodes.Assignment(
                    names, nodes.Value(expr), context == "local")
                 for (context, names, expr) in defines],
                )

        # tal:case
        try:
            clause = ns[TAL, 'case']
        except KeyError:
            CASE = skip
        else:
            value = nodes.Value(clause)
            for switch in reversed(self._switches):
                if switch is not None:
                    break
            else:
                raise LanguageError(
                    "Must define switch on a parent element.", clause
                    )

            CASE = lambda node: nodes.Define(
                [nodes.Alias(["default"], switch[1], False)],
                nodes.Condition(
                    nodes.Equality(switch[0], value),
                    nodes.Cancel([switch[0]], node),
                ))

        # tal:repeat
        try:
            clause = ns[TAL, 'repeat']
        except KeyError:
            REPEAT = skip
        else:
            defines = tal.parse_defines(clause)
            assert len(defines) == 1
            context, names, expr = defines[0]

            expression = nodes.Value(expr)

            if start['namespace'] == TAL:
                self._last = None
                self._whitespace = whitespace.lstrip('\n')
                whitespace = ""

            REPEAT = partial(
                nodes.Repeat,
                names,
                expression,
                context == "local",
                whitespace
                )

        # tal:condition
        try:
            clause = ns[TAL, 'condition']
        except KeyError:
            CONDITION = skip
        else:
            expression = nodes.Value(clause)
            CONDITION = partial(nodes.Condition, expression)

        # tal:switch
        if switch is None:
            SWITCH = skip
        else:
            SWITCH = partial(nodes.Cache, list(switch))

        # i18n:domain
        try:
            clause = ns[I18N, 'domain']
        except KeyError:
            DOMAIN = skip
        else:
            DOMAIN = partial(nodes.Domain, clause)

        # i18n:name
        try:
            clause = ns[I18N, 'name']
        except KeyError:
            NAME = skip
        else:
            if not clause.strip():
                NAME = skip
            else:
                NAME = partial(nodes.Name, clause)

        # The "slot" node next is the first node level that can serve
        # as a macro slot
        slot = wrap(
            inner,
            DEFINE_SLOT,
            DEFINE,
            CASE,
            CONDITION,
            REPEAT,
            SWITCH,
            DOMAIN,
            )

        # metal:fill-slot
        try:
            clause = ns[METAL, 'fill-slot']
        except KeyError:
            pass
        else:
            if not clause.strip():
                raise LanguageError(
                    "Must provide a non-trivial string for metal:fill-slot.",
                    clause
                )

            index = -(1 + int(bool(use_macro or extend_macro)))

            try:
                slots = self._use_macro[index]
            except IndexError:
                raise LanguageError(
                    "Cannot use metal:fill-slot without metal:use-macro.",
                    clause
                    )

            slots = self._use_macro[index]
            slots.append(nodes.FillSlot(clause, slot))

        # metal:define-macro
        try:
            clause = ns[METAL, 'define-macro']
        except KeyError:
            pass
        else:
            self._macros[clause] = slot
            slot = nodes.UseInternalMacro(clause)

        slot = wrap(
            slot,
            NAME
            )

        # tal:on-error
        try:
            clause = ns[TAL, 'on-error']
        except KeyError:
            ON_ERROR = skip
        else:
            key, value = tal.parse_substitution(clause)
            translate = True if ns.get((I18N, 'translate')) == '' else False

            fallback = self._make_content_node(value, None, key, translate)

            if omit is False and start['namespace'] not in self.DROP_NS:
                start_tag = copy(start_tag)

                start_tag.attributes = nodes.Sequence(
                    start_tag.attributes.extract(
                        lambda attribute:
                        isinstance(attribute, nodes.Attribute) and
                        isinstance(attribute.expression, ast.Str)
                    )
                )

                if end_tag is None:
                    # Make sure start-tag has opening suffix. We don't
                    # allow self-closing element here.
                    start_tag.suffix  = ">"

                    # Explicitly set end-tag.
                    end_tag = nodes.End(start_tag.name, '', '</', '>',)

                fallback = nodes.Element(
                    start_tag,
                    end_tag,
                    fallback,
                )

            ON_ERROR = partial(nodes.OnError, fallback, 'error')

        clause = ns.get((META, 'interpolation'))
        if clause in ('false', 'off'):
            INTERPOLATION = False
        elif clause in ('true', 'on'):
            INTERPOLATION = True
        elif clause is None:
            INTERPOLATION = self._interpolation[-1]
        else:
            raise LanguageError("Bad interpolation setting.", clause)

        self._interpolation.append(INTERPOLATION)

        # Visit content body
        for child in children:
            body.append(self.visit(*child))

        self._switches.pop()
        self._interpolation.pop()

        if use_macro:
            self._use_macro.pop()

        return wrap(
            slot,
            ON_ERROR
            )

    def visit_start_tag(self, start):
        return self.visit_element(start, None, [])

    def visit_cdata(self, node):
        if not self._interpolation[-1] or not '${' in node:
            return nodes.Text(node)

        expr = nodes.Substitution(node, ())
        return nodes.Interpolation(expr, True, False)

    def visit_comment(self, node):
        if node.startswith('<!--!'):
            return

        if node.startswith('<!--?'):
            return nodes.Text('<!--' + node.lstrip('<!-?'))

        if not self._interpolation[-1] or not '${' in node:
            return nodes.Text(node)

        char_escape = ('&', '<', '>') if self.escape else ()
        expression = nodes.Substitution(node[4:-3], char_escape)

        return nodes.Sequence(
            [nodes.Text(node[:4]),
             nodes.Interpolation(expression, True, False),
             nodes.Text(node[-3:])
             ])

    def visit_processing_instruction(self, node):
        if node['name'] != 'python':
            text = '<?' + node['name'] + node['text'] + '?>'
            return self.visit_text(text)

        return nodes.CodeBlock(node['text'])

    def visit_text(self, node):
        self._last = node

        translation = self.implicit_i18n_translate

        if self._interpolation[-1] and '${' in node:
            char_escape = ('&', '<', '>') if self.escape else ()
            expression = nodes.Substitution(node, char_escape)
            return nodes.Interpolation(expression, True, translation)

        if not translation:
            return nodes.Text(node)

        match = re.search(r'(\s*)(.*\S)(\s*)', node, flags=re.DOTALL)
        if match is not None:
            prefix, text, suffix = match.groups()
            normalized = re.sub('\s+', ' ', text)
            return nodes.Sequence([
                nodes.Text(prefix),
                nodes.Translate(normalized, nodes.Text(normalized)),
                nodes.Text(suffix),
            ])
        else:
            return nodes.Text(node)

    def _pop_defaults(self, kwargs, *attributes):
        for attribute in attributes:
            default = getattr(self, attribute)
            value = kwargs.pop(attribute, default)
            setattr(self, attribute, value)

    def _check_attributes(self, namespace, ns):
        if namespace in self.DROP_NS and ns.get((TAL, 'attributes')):
            raise LanguageError(
                "Dynamic attributes not allowed on elements of "
                "the namespace: %s." % namespace,
                ns[TAL, 'attributes'],
                )

        script = ns.get((TAL, 'script'))
        if script is not None:
            raise LanguageError(
                "The script attribute is unsupported.", script)

        tal_content = ns.get((TAL, 'content'))
        if tal_content and ns.get((TAL, 'replace')):
            raise LanguageError(
                "You cannot use tal:content and tal:replace at the same time.",
                tal_content
                )

        if tal_content and ns.get((I18N, 'translate')):
            raise LanguageError(
                "You cannot use tal:content with non-trivial i18n:translate.",
                tal_content
                )

    def _make_content_node(self, expression, default, key, translate):
        value = nodes.Value(expression)
        char_escape = ('&', '<', '>') if key == 'text' else ()
        content = nodes.Content(value, char_escape, translate)

        if default is not None:
            content = nodes.Condition(
                nodes.Identity(value, marker("default")),
                default,
                content,
                )

            # Cache expression to avoid duplicate evaluation
            content = nodes.Cache([value], content)

            # Define local marker "default"
            content = nodes.Define(
                [nodes.Alias(["default"], marker("default"))],
                content
                )

        return content

    def _create_attributes_nodes(self, prepared, I18N_ATTRIBUTES, STATIC):
        attributes = []

        names = [attr[0] for attr in prepared]
        filtering = [[]]

        for i, (name, text, quote, space, eq, expr) in enumerate(prepared):
            implicit_i18n = (
                name is not None and
                name.lower() in self.implicit_i18n_attributes
            )

            char_escape = ('&', '<', '>', quote)

            # Use a provided default text as the default marker
            # (aliased to the name ``default``), otherwise use the
            # program's default marker value.
            if text is not None:
                default_marker = ast.Str(s=text)
            else:
                default_marker = self.default_marker

            msgid = I18N_ATTRIBUTES.get(name, missing)

            # If (by heuristic) ``text`` contains one or more
            # interpolation expressions, apply interpolation
            # substitution to the text
            if expr is None and text is not None and '${' in text:
                expr = nodes.Substitution(text, char_escape, None)
                translation = implicit_i18n and msgid is missing
                value = nodes.Interpolation(expr, True, translation)
                default_marker = self.default_marker

            # If the expression is non-trivial, the attribute is
            # dynamic (computed).
            elif expr is not None:
                if name is None:
                    expression = nodes.Value(expr)
                    value = nodes.DictAttributes(
                        expression, ('&', '<', '>', '"'), '"',
                        set(filter(None, names[i:]))
                    )
                    for fs in filtering:
                        fs.append(expression)
                    filtering.append([])
                elif name in self.boolean_attributes:
                    value = nodes.Boolean(expr, name)
                else:
                    if text is not None:
                        default = default_marker
                    else:
                        default = None

                    value = nodes.Substitution(expr, char_escape, default)

            # Otherwise, it's a static attribute. We don't include it
            # here if there's one or more "computed" attributes
            # (dynamic, from one or more dict values).
            else:
                value = ast.Str(s=text)
                if msgid is missing and implicit_i18n:
                    msgid = text

            if name is not None:
                # If translation is required, wrap in a translation
                # clause
                if msgid is not missing:
                    value = nodes.Translate(msgid, value)

                space = self._maybe_trim(space)
                fs = filtering[-1]
                attribute = nodes.Attribute(name, value, quote, eq, space, fs)

                if not isinstance(value, ast.Str):
                    # Always define a ``default`` alias for non-static
                    # expressions.
                    attribute = nodes.Define(
                        [nodes.Alias(["default"], default_marker)],
                        attribute,
                        )

                value = attribute

            attributes.append(value)

        result = nodes.Sequence(attributes)

        fs = filtering[0]
        if fs:
            return nodes.Cache(fs, result)

        return result

    def _create_static_attributes(self, prepared):
        static_attrs = {}

        for name, text, quote, space, eq, expr in prepared:
            if name is None:
                continue

            static_attrs[name] = text if text is not None else expr

        if not static_attrs:
            return

        return Static(parse(repr(static_attrs)).body)

    def _maybe_trim(self, string):
        if self.trim_attribute_space:
            return re_trim.sub(" ", string)

        return string

########NEW FILE########
__FILENAME__ = template
try:
    import ast
except ImportError:
    from chameleon import ast25 as ast

from functools import partial
from os.path import dirname
from hashlib import md5

from ..i18n import simple_translate
from ..tales import PythonExpr
from ..tales import StringExpr
from ..tales import NotExpr
from ..tales import ExistsExpr
from ..tales import ImportExpr
from ..tales import ProxyExpr
from ..tales import StructureExpr
from ..tales import ExpressionParser

from ..tal import RepeatDict

from ..template import BaseTemplate
from ..template import BaseTemplateFile
from ..compiler import ExpressionEngine
from ..loader import TemplateLoader
from ..astutil import Builtin
from ..utils import decode_string
from ..utils import string_type

from .program import MacroProgram

try:
    bytes
except NameError:
    bytes = str


class PageTemplate(BaseTemplate):
    """Constructor for the page template language.

    Takes a string input as the only positional argument::

      template = PageTemplate("<div>Hello, ${name}.</div>")

    Configuration (keyword arguments):

      ``default_expression``

        Set the default expression type. The default setting is
        ``python``.

      ``encoding``

        The default text substitution value is a unicode string on
        Python 2 or simply string on Python 3.

        Pass an encoding to allow encoded byte string input
        (e.g. UTF-8).

      ``literal_false``

        Attributes are not dropped for a value of ``False``. Instead,
        the value is coerced to a string.

        This setting exists to provide compatibility with the
        reference implementation.

      ``boolean_attributes``

        Attributes included in this set are treated as booleans: if a
        true value is provided, the attribute value is the attribute
        name, e.g.::

            boolean_attributes = {"selected"}

        If we insert an attribute with the name "selected" and
        provide a true value, the attribute will be rendered::

            selected="selected"

        If a false attribute is provided (including the empty string),
        the attribute is dropped.

        The special return value ``default`` drops or inserts the
        attribute based on the value element attribute value.

      ``translate``

        Use this option to set a translation function.

        Example::

          def translate(msgid, domain=None, mapping=None, default=None, context=None):
              ...
              return translation

        Note that if ``target_language`` is provided at render time,
        the translation function must support this argument.

      ``implicit_i18n_translate``

        Enables implicit translation for text appearing inside
        elements. Default setting is ``False``.

        While implicit translation does work for text that includes
        expression interpolation, each expression must be simply a
        variable name (e.g. ``${foo}``); otherwise, the text will not
        be marked for translation.

      ``implicit_i18n_attributes``

        Any attribute contained in this set will be marked for
        implicit translation. Each entry must be a lowercase string.

        Example::

          implicit_i18n_attributes = set(['alt', 'title'])

      ``strict``

        Enabled by default. If disabled, expressions are only required
        to be valid at evaluation time.

        This setting exists to provide compatibility with the
        reference implementation which compiles expressions at
        evaluation time.

      ``trim_attribute_space``

        If set, additional attribute whitespace will be stripped.

    Output is unicode on Python 2 and string on Python 3.
    """

    expression_types = {
        'python': PythonExpr,
        'string': StringExpr,
        'not': NotExpr,
        'exists': ExistsExpr,
        'import': ImportExpr,
        'structure': StructureExpr,
        }

    default_expression = 'python'

    translate = staticmethod(simple_translate)

    encoding = None

    boolean_attributes = set()

    literal_false = False

    mode = "xml"

    implicit_i18n_translate = False

    implicit_i18n_attributes = set()

    trim_attribute_space = False

    def __init__(self, body, **config):
        self.macros = Macros(self)
        super(PageTemplate, self).__init__(body, **config)

    def __getitem__(self, name):
        return self.macros[name]

    @property
    def builtins(self):
        return self._builtins()

    @property
    def engine(self):
        if self.literal_false:
            default_marker = ast.Str(s="__default__")
        else:
            default_marker = Builtin("False")

        return partial(
            ExpressionEngine,
            self.expression_parser,
            default_marker=default_marker,
            )

    @property
    def expression_parser(self):
        return ExpressionParser(self.expression_types, self.default_expression)

    def parse(self, body):
        if self.literal_false:
            default_marker = ast.Str(s="__default__")
        else:
            default_marker = Builtin("False")

        return MacroProgram(
            body, self.mode, self.filename,
            escape=True if self.mode == "xml" else False,
            default_marker=default_marker,
            boolean_attributes=self.boolean_attributes,
            implicit_i18n_translate=self.implicit_i18n_translate,
            implicit_i18n_attributes=self.implicit_i18n_attributes,
            trim_attribute_space=self.trim_attribute_space,
            )

    def render(self, encoding=None, translate=None, **vars):
        """Render template to string.

        The ``encoding`` and ``translate`` arguments are documented in
        the template class constructor. If passed to this method, they
        are used instead of the class defaults.

        Additional arguments:

          ``target_language``

            This argument will be partially applied to the translation
            function.

            An alternative is thus to simply provide a custom
            translation function which includes this information or
            relies on a different mechanism.

        """

        non_trivial_translate = translate is not None
        translate = translate if non_trivial_translate else self.translate or \
                    type(self).translate

        # Curry language parameter if non-trivial
        target_language = vars.get('target_language')
        if target_language is not None:
            translate = partial(translate, target_language=target_language)

        encoding = encoding if encoding is not None else self.encoding
        if encoding is not None:
            def translate(msgid, txl=translate, encoding=encoding, **kwargs):
                if isinstance(msgid, bytes):
                    msgid = decode_string(msgid, encoding)
                return txl(msgid, **kwargs)

            def decode(inst, encoding=encoding):
                return decode_string(inst, encoding, 'ignore')
        else:
            decode = decode_string

        setdefault = vars.setdefault
        setdefault("__translate", translate)
        setdefault("__convert", translate)
        setdefault("__decode", decode)

        if non_trivial_translate:
            vars['translate'] = translate

        # Make sure we have a repeat dictionary
        if 'repeat' not in vars: vars['repeat'] = RepeatDict({})

        return super(PageTemplate, self).render(**vars)

    def include(self, *args, **kwargs):
        self.cook_check()
        self._render(*args, **kwargs)

    def digest(self, body, names):
        hex = super(PageTemplate, self).digest(body, names)
        digest = md5(hex.encode('ascii'))
        digest.update(';'.join(names).encode('utf-8'))

        for attr in (
            'trim_attribute_space',
            'implicit_i18n_translate',
            'literal_false',
            'strict'
        ):
            v = getattr(self, attr)
            digest.update(
                (";%s=%s" % (attr, str(v))).encode('ascii')
            )

        return digest.hexdigest()

    def _builtins(self):
        return {
            'template': self,
            'macros': self.macros,
            'nothing': None,
            }


class PageTemplateFile(PageTemplate, BaseTemplateFile):
    """File-based constructor.

    Takes a string input as the only positional argument::

      template = PageTemplateFile(absolute_path)

    Note that the file-based template class comes with the expression
    type ``load`` which loads templates relative to the provided
    filename.

    Below are listed the configuration arguments specific to
    file-based templates; see the string-based template class for
    general options and documentation:

    Configuration (keyword arguments):

      ``loader_class``

        The provided class will be used to create the template loader
        object. The default implementation supports relative and
        absolute path specs.

        The class must accept keyword arguments ``search_path``
        (sequence of paths to search for relative a path spec) and
        ``default_extension`` (if provided, this should be added to
        any path spec).

      ``prepend_relative_search_path``

        Inserts the path relative to the provided template file path
        into the template search path.

        The default setting is ``True``.

      ``search_path``

        If provided, this is used as the search path for the ``load:``
        expression. It must be a string or an iterable yielding a
        sequence of strings.

    """

    expression_types = PageTemplate.expression_types.copy()
    expression_types['load'] = partial(
        ProxyExpr, '__loader',
        ignore_prefix=False
    )

    prepend_relative_search_path = True

    def __init__(self, filename, search_path=None, loader_class=TemplateLoader,
                 **config):
        super(PageTemplateFile, self).__init__(filename, **config)

        if search_path is None:
            search_path = []
        else:
            if isinstance(search_path, string_type):
                search_path = [search_path]
            else:
                search_path = list(search_path)

        # If the flag is set (this is the default), prepend the path
        # relative to the template file to the search path
        if self.prepend_relative_search_path:
            path = dirname(self.filename)
            search_path.insert(0, path)

        loader = loader_class(search_path=search_path, **config)
        template_class = type(self)

        # Bind relative template loader instance to the same template
        # class, providing the same keyword arguments.
        self._loader = loader.bind(template_class)

    def _builtins(self):
        d = super(PageTemplateFile, self)._builtins()
        d['__loader'] = self._loader
        return d


class PageTextTemplate(PageTemplate):
    """Text-based template class.

    Takes a non-XML input::

      template = PageTextTemplate("Hello, ${name}.")

    This is similar to the standard library class ``string.Template``,
    but uses the expression engine to substitute variables.
    """

    mode = "text"


class PageTextTemplateFile(PageTemplateFile):
    """File-based constructor."""

    mode = "text"

    def render(self, **vars):
        result = super(PageTextTemplateFile, self).render(**vars)
        return result.encode(self.encoding or 'utf-8')


class Macro(object):
    __slots__ = "include",

    def __init__(self, render):
        self.include = render


class Macros(object):
    __slots__ = "template",

    def __init__(self, template):
        self.template = template

    def __getitem__(self, name):
        name = name.replace('-', '_')
        self.template.cook_check()

        try:
            function = getattr(self.template, "_render_%s" % name)
        except AttributeError:
            raise KeyError(
                "Macro does not exist: '%s'." % name)

        return Macro(function)

    @property
    def names(self):
        self.template.cook_check()

        result = []
        for name in self.template.__dict__:
            if name.startswith('_render_'):
                result.append(name[8:])
        return result

########NEW FILE########
