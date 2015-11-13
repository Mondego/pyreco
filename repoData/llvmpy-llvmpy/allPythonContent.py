__FILENAME__ = run_test
import sys
import platform
import llvm

from llvm.core import Module
from llvm.ee import EngineBuilder
from llvm.utils import check_intrinsics

m = Module.new('fjoidajfa')
eb = EngineBuilder.new(m)
target = eb.select_target()

print('target.triple=%r' % target.triple)
if sys.platform == 'darwin':
    s = {'64bit': 'x86_64', '32bit': 'x86'}[platform.architecture()[0]]
    assert target.triple.startswith(s + '-apple-darwin')

assert llvm.test(verbosity=2, run_isolated=False) == 0
#check_intrinsics.main()

print('llvm.__version__: %s' % llvm.__version__)
#assert llvm.__version__ == '0.12.0'

########NEW FILE########
__FILENAME__ = gh-pages
#!/usr/bin/env python
"""Script to commit the doc build outputs into the github-pages repo.

Use:

  gh-pages.py [tag]

If no tag is given, the current output of 'git describe' is used.  If given,
that is how the resulting directory will be named.

In practice, you should use either actual clean tags from a current build or
something like 'current' as a stable URL for the most current version of the """

#-----------------------------------------------------------------------------
# Imports
#-----------------------------------------------------------------------------
import os
import re
import shutil
import sys
from os import chdir as cd
from os.path import join as pjoin

from subprocess import Popen, PIPE, CalledProcessError, check_call

#-----------------------------------------------------------------------------
# Globals
#-----------------------------------------------------------------------------

pages_dir = 'gh-pages'
html_dir = '_build/html'
pdf_dir = '_build/latex'
pages_repo = 'https://github.com/llvmpy/llvmpy-doc.git'

#-----------------------------------------------------------------------------
# Functions
#-----------------------------------------------------------------------------
def sh(cmd):
    """Execute command in a subshell, return status code."""
    return check_call(cmd, shell=True)


def sh2(cmd):
    """Execute command in a subshell, return stdout.

    Stderr is unbuffered from the subshell.x"""
    p = Popen(cmd, stdout=PIPE, shell=True)
    out = p.communicate()[0]
    retcode = p.returncode
    if retcode:
        raise CalledProcessError(retcode, cmd)
    else:
        return out.rstrip()


def sh3(cmd):
    """Execute command in a subshell, return stdout, stderr

    If anything appears in stderr, print it out to sys.stderr"""
    p = Popen(cmd, stdout=PIPE, stderr=PIPE, shell=True)
    out, err = p.communicate()
    retcode = p.returncode
    if retcode:
        raise CalledProcessError(retcode, cmd)
    else:
        return out.rstrip(), err.rstrip()


def init_repo(path):
    """clone the gh-pages repo if we haven't already."""
    sh("git clone %s %s"%(pages_repo, path))
    here = os.getcwdu()
    cd(path)
    sh('git checkout gh-pages')
    cd(here)

#-----------------------------------------------------------------------------
# Script starts
#-----------------------------------------------------------------------------
if __name__ == '__main__':
    # The tag can be given as a positional argument
    try:
        tag = sys.argv[1]
    except IndexError:
        try:
            tag = sh2('git describe --exact-match')
        except CalledProcessError:
            tag = "dev"   # Fallback

    startdir = os.getcwdu()
    if not os.path.exists(pages_dir):
        # init the repo
        init_repo(pages_dir)
    else:
        # ensure up-to-date before operating
        cd(pages_dir)
        sh('git checkout gh-pages')
        sh('git pull')
        cd(startdir)

    dest = pjoin(pages_dir, tag)

    # don't `make html` here, because gh-pages already depends on html in Makefile
    # sh('make html')
    if tag != 'dev':
        # only build pdf for non-dev targets
        #sh2('make pdf')
        pass

    # This is pretty unforgiving: we unconditionally nuke the destination
    # directory, and then copy the html tree in there
    shutil.rmtree(dest, ignore_errors=True)
    shutil.copytree(html_dir, dest)
    if tag != 'dev':
        #shutil.copy(pjoin(pdf_dir, 'ipython.pdf'), pjoin(dest, 'ipython.pdf'))
        pass

    try:
        cd(pages_dir)
        status = sh2('git status | head -1')
        branch = re.match('\# On branch (.*)$', status).group(1)
        if branch != 'gh-pages':
            e = 'On %r, git branch is %r, MUST be "gh-pages"' % (pages_dir,
                                                                 branch)
            raise RuntimeError(e)

        sh('git add -A %s' % tag)
        sh('git commit -m"Updated doc release: %s"' % tag)
        print
        print 'Most recent 3 commits:'
        sys.stdout.flush()
        sh('git --no-pager log --oneline HEAD~3..')
    finally:
        cd(startdir)

    print
    print 'Now verify the build in: %r' % dest
    print "If everything looks good, 'git push'"

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# llvmpy documentation build configuration file, created by
# sphinx-quickstart on Wed Aug  8 17:33:58 2012.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os, glob

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#sys.path.insert(0, os.path.abspath('../..'))

# Support sphinx.ext.autodoc to extract docstrings from modules without installing
# complete package.
# The python modules depend on _core, so we must build entire package first though.
built_lib = glob.glob('../../build/lib.*-%d.%d/' % sys.version_info[:2])
if not built_lib:
    sys.stderr.write("WARNING: To build complete documentation you must build "
                     "package first\n")
else:
    # lib dir has platform suffix
    sys.path.insert(0, os.path.abspath(built_lib[0]))

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.mathjax', 'sphinx.ext.autodoc']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'llvmpy'
copyright = u'2013, Mahadevan R (2008-2010), Continuum Analytics (2012-2013)'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
try:
    import llvm
    version_strs = llvm.__version__.split('.')
    # The short X.Y version.
    version = '.'.join(version_strs[:2])
    # The full version, including alpha/beta/rc tags.
    release = '%s.%s' % (version, '-'.join(version_strs[2].split('-')[:2]))
except ImportError:
    version = 'unknown-version'
    release = 'unknown-release'

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
htmlhelp_basename = 'llvmpydoc'


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
  ('index', 'llvmpy.tex', u'llvmpy Documentation',
   u'Mahadevan R (2008-2010), Continuum Analytics (2012)', 'manual'),
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
    ('index', 'llvmpy', u'llvmpy Documentation',
     [u'Mahadevan R (2008-2010), Continuum Analytics (2012)'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'llvmpy', u'llvmpy Documentation',
   u'Mahadevan R (2008-2010), Continuum Analytics (2012)', 'llvmpy', 'One line description of project.',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'

########NEW FILE########
__FILENAME__ = vector_instr
'''
This example shows:
1) how to use vector instructions
2) how to take advantage of LLVM loop vectorization to transform scalar     
   operations to vector operations
'''

from __future__ import print_function
import llvm.core as lc
import llvm.ee as le
import llvm.passes as lp
from ctypes import CFUNCTYPE, POINTER, c_int, c_float

def build_manual_vector():
    mod = lc.Module.new('manual.vector')
    intty = lc.Type.int(32)
    vecty = lc.Type.vector(lc.Type.float(), 4)
    aryty = lc.Type.pointer(lc.Type.float())
    fnty = lc.Type.function(lc.Type.void(), [aryty, aryty, aryty, intty])
    fn = mod.add_function(fnty, name='vector_add')
    bbentry = fn.append_basic_block('entry')
    bbloopcond = fn.append_basic_block('loop.cond')
    bbloopbody = fn.append_basic_block('loop.body')
    bbexit = fn.append_basic_block('exit')
    builder = lc.Builder.new(bbentry)

    # populate function body
    in1, in2, out, size = fn.args
    ZERO = lc.Constant.null(intty)
    loopi_ptr = builder.alloca(intty)
    builder.store(ZERO, loopi_ptr)

    builder.branch(bbloopcond)
    builder.position_at_end(bbloopcond)

    loopi = builder.load(loopi_ptr)
    loopcond = builder.icmp(lc.ICMP_ULT, loopi, size)

    builder.cbranch(loopcond, bbloopbody, bbexit)
    builder.position_at_end(bbloopbody)

    vecaryty = lc.Type.pointer(vecty)
    in1asvec = builder.bitcast(builder.gep(in1, [loopi]), vecaryty)
    in2asvec = builder.bitcast(builder.gep(in2, [loopi]), vecaryty)
    outasvec = builder.bitcast(builder.gep(out, [loopi]), vecaryty)

    vec1 = builder.load(in1asvec)
    vec2 = builder.load(in2asvec)

    vecout = builder.fadd(vec1, vec2)

    builder.store(vecout, outasvec)

    next = builder.add(loopi, lc.Constant.int(intty, 4))
    builder.store(next, loopi_ptr)

    builder.branch(bbloopcond)
    builder.position_at_end(bbexit)

    builder.ret_void()

    return mod, fn


def build_auto_vector():
    mod = lc.Module.new('auto.vector')
    # Loop vectorize is sensitive to the size of the index size(!?)
    intty = lc.Type.int(tuple.__itemsize__ * 8)
    aryty = lc.Type.pointer(lc.Type.float())
    fnty = lc.Type.function(lc.Type.void(), [aryty, aryty, aryty, intty])
    fn = mod.add_function(fnty, name='vector_add')
    bbentry = fn.append_basic_block('entry')
    bbloopcond = fn.append_basic_block('loop.cond')
    bbloopbody = fn.append_basic_block('loop.body')
    bbexit = fn.append_basic_block('exit')
    builder = lc.Builder.new(bbentry)

    # populate function body
    in1, in2, out, size = fn.args
    in1.add_attribute(lc.ATTR_NO_ALIAS)
    in2.add_attribute(lc.ATTR_NO_ALIAS)
    out.add_attribute(lc.ATTR_NO_ALIAS)
    ZERO = lc.Constant.null(intty)
    loopi_ptr = builder.alloca(intty)
    builder.store(ZERO, loopi_ptr)

    builder.branch(bbloopcond)
    builder.position_at_end(bbloopcond)

    loopi = builder.load(loopi_ptr)
    loopcond = builder.icmp(lc.ICMP_ULT, loopi, size)

    builder.cbranch(loopcond, bbloopbody, bbexit)
    builder.position_at_end(bbloopbody)

    in1elem = builder.load(builder.gep(in1, [loopi]))
    in2elem = builder.load(builder.gep(in2, [loopi]))

    outelem = builder.fadd(in1elem, in2elem)

    builder.store(outelem, builder.gep(out, [loopi]))

    next = builder.add(loopi, lc.Constant.int(intty, 1))
    builder.store(next, loopi_ptr)

    builder.branch(bbloopcond)
    builder.position_at_end(bbexit)

    builder.ret_void()

    return mod, fn

def example(title, module_builder, opt):
    print(title.center(80, '='))
    mod, fn = module_builder()

    eb = le.EngineBuilder.new(mod).opt(3)
    if opt:
        print('opt')
        tm = eb.select_target()
        pms = lp.build_pass_managers(mod=mod, tm=tm, opt=3, loop_vectorize=True,
                                     fpm=False)
        pms.pm.run(mod)

    print(mod)
    print(mod.to_native_assembly())

    engine = eb.create()
    ptr = engine.get_pointer_to_function(fn)

    callable = CFUNCTYPE(None, POINTER(c_float), POINTER(c_float),
                         POINTER(c_float), c_int)(ptr)

    N = 20
    in1 = (c_float * N)(*range(N))
    in2 = (c_float * N)(*range(N))
    out = (c_float * N)()

    print('in1: ', list(in1))
    print('in1: ', list(in2))

    callable(in1, in2, out, N)

    print('out', list(out))


def main():
    example('manual vector function', build_manual_vector, False)
    example('auto vector function', build_auto_vector, True)

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = bytecode_visitor
# ______________________________________________________________________
from __future__ import absolute_import
import itertools

import opcode
from .opcode_util import itercode

# ______________________________________________________________________

class BytecodeVisitor (object):
    opnames = [name.split('+')[0] for name in opcode.opname]

    def visit_op (self, i, op, arg, *args, **kws):
        if op < 0:
            ret_val = self.visit_synthetic_op(i, op, arg, *args, **kws)
        else:
            method = getattr(self, 'op_' + self.opnames[op])
            ret_val = method(i, op, arg, *args, **kws)
        return ret_val

    def visit_synthetic_op (self, i, op, arg, *args, **kws):
        raise NotImplementedError(
            'BytecodeVisitor.visit_synthetic_op() must be overloaded if using '
            'synthetic opcodes.')

    def _not_implemented (self, i, op, arg, *args, **kws):
        raise NotImplementedError("BytecodeVisitor.op_%s (@ bytecode index %d)"
                                  % (self.opnames[op], i))

    op_BINARY_ADD = _not_implemented
    op_BINARY_AND = _not_implemented
    op_BINARY_DIVIDE = _not_implemented
    op_BINARY_FLOOR_DIVIDE = _not_implemented
    op_BINARY_LSHIFT = _not_implemented
    op_BINARY_MODULO = _not_implemented
    op_BINARY_MULTIPLY = _not_implemented
    op_BINARY_OR = _not_implemented
    op_BINARY_POWER = _not_implemented
    op_BINARY_RSHIFT = _not_implemented
    op_BINARY_SUBSCR = _not_implemented
    op_BINARY_SUBTRACT = _not_implemented
    op_BINARY_TRUE_DIVIDE = _not_implemented
    op_BINARY_XOR = _not_implemented
    op_BREAK_LOOP = _not_implemented
    op_BUILD_CLASS = _not_implemented
    op_BUILD_LIST = _not_implemented
    op_BUILD_MAP = _not_implemented
    op_BUILD_SET = _not_implemented
    op_BUILD_SLICE = _not_implemented
    op_BUILD_TUPLE = _not_implemented
    op_CALL_FUNCTION = _not_implemented
    op_CALL_FUNCTION_KW = _not_implemented
    op_CALL_FUNCTION_VAR = _not_implemented
    op_CALL_FUNCTION_VAR_KW = _not_implemented
    op_COMPARE_OP = _not_implemented
    op_CONTINUE_LOOP = _not_implemented
    op_DELETE_ATTR = _not_implemented
    op_DELETE_DEREF = _not_implemented
    op_DELETE_FAST = _not_implemented
    op_DELETE_GLOBAL = _not_implemented
    op_DELETE_NAME = _not_implemented
    op_DELETE_SLICE = _not_implemented
    op_DELETE_SUBSCR = _not_implemented
    op_DUP_TOP = _not_implemented
    op_DUP_TOPX = _not_implemented
    op_DUP_TOP_TWO = _not_implemented
    op_END_FINALLY = _not_implemented
    op_EXEC_STMT = _not_implemented
    op_EXTENDED_ARG = _not_implemented
    op_FOR_ITER = _not_implemented
    op_GET_ITER = _not_implemented
    op_IMPORT_FROM = _not_implemented
    op_IMPORT_NAME = _not_implemented
    op_IMPORT_STAR = _not_implemented
    op_INPLACE_ADD = _not_implemented
    op_INPLACE_AND = _not_implemented
    op_INPLACE_DIVIDE = _not_implemented
    op_INPLACE_FLOOR_DIVIDE = _not_implemented
    op_INPLACE_LSHIFT = _not_implemented
    op_INPLACE_MODULO = _not_implemented
    op_INPLACE_MULTIPLY = _not_implemented
    op_INPLACE_OR = _not_implemented
    op_INPLACE_POWER = _not_implemented
    op_INPLACE_RSHIFT = _not_implemented
    op_INPLACE_SUBTRACT = _not_implemented
    op_INPLACE_TRUE_DIVIDE = _not_implemented
    op_INPLACE_XOR = _not_implemented
    op_JUMP_ABSOLUTE = _not_implemented
    op_JUMP_FORWARD = _not_implemented
    op_JUMP_IF_FALSE = _not_implemented
    op_JUMP_IF_FALSE_OR_POP = _not_implemented
    op_JUMP_IF_TRUE = _not_implemented
    op_JUMP_IF_TRUE_OR_POP = _not_implemented
    op_LIST_APPEND = _not_implemented
    op_LOAD_ATTR = _not_implemented
    op_LOAD_BUILD_CLASS = _not_implemented
    op_LOAD_CLOSURE = _not_implemented
    op_LOAD_CONST = _not_implemented
    op_LOAD_DEREF = _not_implemented
    op_LOAD_FAST = _not_implemented
    op_LOAD_GLOBAL = _not_implemented
    op_LOAD_LOCALS = _not_implemented
    op_LOAD_NAME = _not_implemented
    op_MAKE_CLOSURE = _not_implemented
    op_MAKE_FUNCTION = _not_implemented
    op_MAP_ADD = _not_implemented
    op_NOP = _not_implemented
    op_POP_BLOCK = _not_implemented
    op_POP_EXCEPT = _not_implemented
    op_POP_JUMP_IF_FALSE = _not_implemented
    op_POP_JUMP_IF_TRUE = _not_implemented
    op_POP_TOP = _not_implemented
    op_PRINT_EXPR = _not_implemented
    op_PRINT_ITEM = _not_implemented
    op_PRINT_ITEM_TO = _not_implemented
    op_PRINT_NEWLINE = _not_implemented
    op_PRINT_NEWLINE_TO = _not_implemented
    op_RAISE_VARARGS = _not_implemented
    op_RETURN_VALUE = _not_implemented
    op_ROT_FOUR = _not_implemented
    op_ROT_THREE = _not_implemented
    op_ROT_TWO = _not_implemented
    op_SETUP_EXCEPT = _not_implemented
    op_SETUP_FINALLY = _not_implemented
    op_SETUP_LOOP = _not_implemented
    op_SETUP_WITH = _not_implemented
    op_SET_ADD = _not_implemented
    op_SLICE = _not_implemented
    op_STOP_CODE = _not_implemented
    op_STORE_ATTR = _not_implemented
    op_STORE_DEREF = _not_implemented
    op_STORE_FAST = _not_implemented
    op_STORE_GLOBAL = _not_implemented
    op_STORE_LOCALS = _not_implemented
    op_STORE_MAP = _not_implemented
    op_STORE_NAME = _not_implemented
    op_STORE_SLICE = _not_implemented
    op_STORE_SUBSCR = _not_implemented
    op_UNARY_CONVERT = _not_implemented
    op_UNARY_INVERT = _not_implemented
    op_UNARY_NEGATIVE = _not_implemented
    op_UNARY_NOT = _not_implemented
    op_UNARY_POSITIVE = _not_implemented
    op_UNPACK_EX = _not_implemented
    op_UNPACK_SEQUENCE = _not_implemented
    op_WITH_CLEANUP = _not_implemented
    op_YIELD_VALUE = _not_implemented

# ______________________________________________________________________

class BytecodeIterVisitor (BytecodeVisitor):
    def visit (self, co_obj):
        self.enter_code_object(co_obj)
        for i, op, arg in itercode(co_obj.co_code):
            self.visit_op(i, op, arg)
        return self.exit_code_object(co_obj)

    def enter_code_object (self, co_obj):
        pass

    def exit_code_object (self, co_obj):
        pass

# ______________________________________________________________________

class BasicBlockVisitor (BytecodeVisitor):
    def visit (self, blocks):
        self.enter_blocks(blocks)
        block_indices = list(blocks.keys())
        block_indices.sort()
        for block_index in block_indices:
            self.enter_block(block_index)
            for i, op, arg in blocks[block_index]:
                self.visit_op(i, op, arg)
            self.exit_block(block_index)
        return self.exit_blocks(blocks)

    def enter_blocks (self, blocks):
        pass

    def exit_blocks (self, blocks):
        pass

    def enter_block (self, block_index):
        pass

    def exit_block (self, block_index):
        pass

# ______________________________________________________________________

class BytecodeFlowVisitor (BytecodeVisitor):
    def visit (self, flow):
        self.block_list = list(flow.keys())
        self.block_list.sort()
        self.enter_flow_object(flow)
        for block in self.block_list:
            prelude = self.enter_block(block)
            prelude_isa_list = isinstance(prelude, list)
            if prelude or prelude_isa_list:
                if not prelude_isa_list:
                    prelude = []
                new_stmts = list(self.visit_op(i, op, arg, *args)
                                 for i, op, _, arg, args in flow[block])
                self.new_flow[block] = list(itertools.chain(
                    prelude, *new_stmts))
            self.exit_block(block)
        del self.block_list
        return self.exit_flow_object(flow)

    def visit_op (self, i, op, arg, *args, **kws):
        new_args = []
        for child_i, child_op, _, child_arg, child_args in args:
            new_args.extend(self.visit_op(child_i, child_op, child_arg,
                                          *child_args))
        ret_val = super(BytecodeFlowVisitor, self).visit_op(i, op, arg,
                                                            *new_args)
        return ret_val

    def enter_flow_object (self, flow):
        self.new_flow = {}

    def exit_flow_object (self, flow):
        ret_val = self.new_flow
        del self.new_flow
        return ret_val

    def enter_block (self, block):
        pass

    def exit_block (self, block):
        pass

# ______________________________________________________________________

class BenignBytecodeVisitorMixin (object):
    def _do_nothing (self, i, op, arg, *args, **kws):
        return [(i, op, self.opnames[op], arg, args)]

    op_BINARY_ADD = _do_nothing
    op_BINARY_AND = _do_nothing
    op_BINARY_DIVIDE = _do_nothing
    op_BINARY_FLOOR_DIVIDE = _do_nothing
    op_BINARY_LSHIFT = _do_nothing
    op_BINARY_MODULO = _do_nothing
    op_BINARY_MULTIPLY = _do_nothing
    op_BINARY_OR = _do_nothing
    op_BINARY_POWER = _do_nothing
    op_BINARY_RSHIFT = _do_nothing
    op_BINARY_SUBSCR = _do_nothing
    op_BINARY_SUBTRACT = _do_nothing
    op_BINARY_TRUE_DIVIDE = _do_nothing
    op_BINARY_XOR = _do_nothing
    op_BREAK_LOOP = _do_nothing
    op_BUILD_CLASS = _do_nothing
    op_BUILD_LIST = _do_nothing
    op_BUILD_MAP = _do_nothing
    op_BUILD_SET = _do_nothing
    op_BUILD_SLICE = _do_nothing
    op_BUILD_TUPLE = _do_nothing
    op_CALL_FUNCTION = _do_nothing
    op_CALL_FUNCTION_KW = _do_nothing
    op_CALL_FUNCTION_VAR = _do_nothing
    op_CALL_FUNCTION_VAR_KW = _do_nothing
    op_COMPARE_OP = _do_nothing
    op_CONTINUE_LOOP = _do_nothing
    op_DELETE_ATTR = _do_nothing
    op_DELETE_DEREF = _do_nothing
    op_DELETE_FAST = _do_nothing
    op_DELETE_GLOBAL = _do_nothing
    op_DELETE_NAME = _do_nothing
    op_DELETE_SLICE = _do_nothing
    op_DELETE_SUBSCR = _do_nothing
    op_DUP_TOP = _do_nothing
    op_DUP_TOPX = _do_nothing
    op_DUP_TOP_TWO = _do_nothing
    op_END_FINALLY = _do_nothing
    op_EXEC_STMT = _do_nothing
    op_EXTENDED_ARG = _do_nothing
    op_FOR_ITER = _do_nothing
    op_GET_ITER = _do_nothing
    op_IMPORT_FROM = _do_nothing
    op_IMPORT_NAME = _do_nothing
    op_IMPORT_STAR = _do_nothing
    op_INPLACE_ADD = _do_nothing
    op_INPLACE_AND = _do_nothing
    op_INPLACE_DIVIDE = _do_nothing
    op_INPLACE_FLOOR_DIVIDE = _do_nothing
    op_INPLACE_LSHIFT = _do_nothing
    op_INPLACE_MODULO = _do_nothing
    op_INPLACE_MULTIPLY = _do_nothing
    op_INPLACE_OR = _do_nothing
    op_INPLACE_POWER = _do_nothing
    op_INPLACE_RSHIFT = _do_nothing
    op_INPLACE_SUBTRACT = _do_nothing
    op_INPLACE_TRUE_DIVIDE = _do_nothing
    op_INPLACE_XOR = _do_nothing
    op_JUMP_ABSOLUTE = _do_nothing
    op_JUMP_FORWARD = _do_nothing
    op_JUMP_IF_FALSE = _do_nothing
    op_JUMP_IF_FALSE_OR_POP = _do_nothing
    op_JUMP_IF_TRUE = _do_nothing
    op_JUMP_IF_TRUE_OR_POP = _do_nothing
    op_LIST_APPEND = _do_nothing
    op_LOAD_ATTR = _do_nothing
    op_LOAD_BUILD_CLASS = _do_nothing
    op_LOAD_CLOSURE = _do_nothing
    op_LOAD_CONST = _do_nothing
    op_LOAD_DEREF = _do_nothing
    op_LOAD_FAST = _do_nothing
    op_LOAD_GLOBAL = _do_nothing
    op_LOAD_LOCALS = _do_nothing
    op_LOAD_NAME = _do_nothing
    op_MAKE_CLOSURE = _do_nothing
    op_MAKE_FUNCTION = _do_nothing
    op_MAP_ADD = _do_nothing
    op_NOP = _do_nothing
    op_POP_BLOCK = _do_nothing
    op_POP_EXCEPT = _do_nothing
    op_POP_JUMP_IF_FALSE = _do_nothing
    op_POP_JUMP_IF_TRUE = _do_nothing
    op_POP_TOP = _do_nothing
    op_PRINT_EXPR = _do_nothing
    op_PRINT_ITEM = _do_nothing
    op_PRINT_ITEM_TO = _do_nothing
    op_PRINT_NEWLINE = _do_nothing
    op_PRINT_NEWLINE_TO = _do_nothing
    op_RAISE_VARARGS = _do_nothing
    op_RETURN_VALUE = _do_nothing
    op_ROT_FOUR = _do_nothing
    op_ROT_THREE = _do_nothing
    op_ROT_TWO = _do_nothing
    op_SETUP_EXCEPT = _do_nothing
    op_SETUP_FINALLY = _do_nothing
    op_SETUP_LOOP = _do_nothing
    op_SETUP_WITH = _do_nothing
    op_SET_ADD = _do_nothing
    op_SLICE = _do_nothing
    op_STOP_CODE = _do_nothing
    op_STORE_ATTR = _do_nothing
    op_STORE_DEREF = _do_nothing
    op_STORE_FAST = _do_nothing
    op_STORE_GLOBAL = _do_nothing
    op_STORE_LOCALS = _do_nothing
    op_STORE_MAP = _do_nothing
    op_STORE_NAME = _do_nothing
    op_STORE_SLICE = _do_nothing
    op_STORE_SUBSCR = _do_nothing
    op_UNARY_CONVERT = _do_nothing
    op_UNARY_INVERT = _do_nothing
    op_UNARY_NEGATIVE = _do_nothing
    op_UNARY_NOT = _do_nothing
    op_UNARY_POSITIVE = _do_nothing
    op_UNPACK_EX = _do_nothing
    op_UNPACK_SEQUENCE = _do_nothing
    op_WITH_CLEANUP = _do_nothing
    op_YIELD_VALUE = _do_nothing

# ______________________________________________________________________
# End of bytecode_visitor.py

########NEW FILE########
__FILENAME__ = bytetype
# ______________________________________________________________________

import ctypes

import llvm.core as lc

# ______________________________________________________________________

lvoid = lc.Type.void()
li1 = lc.Type.int(1)
li8 = lc.Type.int(8)
li16 = lc.Type.int(16)
li32 = lc.Type.int(32)
li64 = lc.Type.int(64)
liptr = lc.Type.int(ctypes.sizeof(ctypes.c_void_p) * 8)
lc_size_t = lc.Type.int(ctypes.sizeof(
        getattr(ctypes, 'c_ssize_t', getattr(ctypes, 'c_size_t'))) * 8)
lfloat = lc.Type.float()
ldouble = lc.Type.double()
li8_ptr = lc.Type.pointer(li8)

lc_int = lc.Type.int(ctypes.sizeof(ctypes.c_int) * 8)
lc_long = lc.Type.int(ctypes.sizeof(ctypes.c_long) * 8)

l_pyobject_head = [lc_size_t, lc.Type.pointer(li32)]
l_pyobject_head_struct = lc.Type.struct(l_pyobject_head)
l_pyobj_p = l_pyobject_head_struct_p = lc.Type.pointer(l_pyobject_head_struct)
l_pyfunc = lc.Type.function(l_pyobj_p, (l_pyobj_p, l_pyobj_p))

strlen = lc.Type.function(lc_size_t, (li8_ptr,))
strncpy = lc.Type.function(li8_ptr, (li8_ptr, li8_ptr, lc_size_t))
strndup = lc.Type.function(li8_ptr, (li8_ptr, lc_size_t))
malloc = lc.Type.function(li8_ptr, (lc_size_t,))
free = lc.Type.function(lvoid, (li8_ptr,))

Py_BuildValue = lc.Type.function(l_pyobj_p, [li8_ptr], True)
PyArg_ParseTuple = lc.Type.function(lc_int, [l_pyobj_p, li8_ptr], True)
PyEval_SaveThread = lc.Type.function(li8_ptr, [])
PyEval_RestoreThread = lc.Type.function(lc.Type.void(), [li8_ptr])

# ______________________________________________________________________
# End of bytetype.py

########NEW FILE########
__FILENAME__ = byte_control
# ______________________________________________________________________
from __future__ import absolute_import
import opcode
from . import opcode_util
import pprint

from .bytecode_visitor import BasicBlockVisitor, BenignBytecodeVisitorMixin
from .control_flow import ControlFlowGraph

# ______________________________________________________________________

class ControlFlowBuilder (BenignBytecodeVisitorMixin, BasicBlockVisitor):
    '''Visitor responsible for traversing a bytecode basic block map and
    building a control flow graph (CFG).

    The primary purpose of this transformation is to create a CFG,
    which is used by later transformers for dataflow analysis.
    '''
    def visit (self, flow, nargs = 0, *args, **kws):
        '''Given a bytecode flow, and an optional number of arguments,
        return a :py:class:`llpython.control_flow.ControlFlowGraph`
        instance describing the full control flow of the bytecode
        flow.'''
        self.nargs = nargs
        ret_val = super(ControlFlowBuilder, self).visit(flow, *args, **kws)
        del self.nargs
        return ret_val

    def enter_blocks (self, blocks):
        super(ControlFlowBuilder, self).enter_blocks(blocks)
        self.blocks = blocks
        self.block_list = list(blocks.keys())
        self.block_list.sort()
        self.cfg = ControlFlowGraph()
        self.loop_stack = []
        for block in self.block_list:
            self.cfg.add_block(block, blocks[block])

    def exit_blocks (self, blocks):
        super(ControlFlowBuilder, self).exit_blocks(blocks)
        assert self.blocks == blocks
        self.cfg.compute_dataflow()
        self.cfg.update_for_ssa()
        ret_val = self.cfg
        del self.loop_stack
        del self.cfg
        del self.block_list
        del self.blocks
        return ret_val

    def enter_block (self, block):
        self.block = block
        assert block in self.cfg.blocks
        if block == 0:
            for local_index in range(self.nargs):
                self.op_STORE_FAST(0, opcode.opmap['STORE_FAST'], local_index)
        return True

    def _get_next_block (self, block):
        return self.block_list[self.block_list.index(block) + 1]

    def exit_block (self, block):
        assert block == self.block
        del self.block
        i, op, arg = self.blocks[block][-1]
        opname = opcode.opname[op]
        if op in opcode.hasjabs:
            self.cfg.add_edge(block, arg)
        elif op in opcode.hasjrel:
            self.cfg.add_edge(block, i + arg + 3)
        elif opname == 'BREAK_LOOP':
            loop_i, _, loop_arg = self.loop_stack[-1]
            self.cfg.add_edge(block, loop_i + loop_arg + 3)
        elif opname != 'RETURN_VALUE':
            self.cfg.add_edge(block, self._get_next_block(block))
        if op in opcode_util.hascbranch:
            self.cfg.add_edge(block, self._get_next_block(block))

    def op_LOAD_FAST (self, i, op, arg, *args, **kws):
        self.cfg.blocks_reads[self.block].add(arg)
        return super(ControlFlowBuilder, self).op_LOAD_FAST(i, op, arg, *args,
                                                            **kws)

    def op_STORE_FAST (self, i, op, arg, *args, **kws):
        self.cfg.writes_local(self.block, i, arg)
        return super(ControlFlowBuilder, self).op_STORE_FAST(i, op, arg, *args,
                                                             **kws)

    def op_SETUP_LOOP (self, i, op, arg, *args, **kws):
        self.loop_stack.append((i, op, arg))
        return super(ControlFlowBuilder, self).op_SETUP_LOOP(i, op, arg, *args,
                                                             **kws)

    def op_POP_BLOCK (self, i, op, arg, *args, **kws):
        self.loop_stack.pop()
        return super(ControlFlowBuilder, self).op_POP_BLOCK(i, op, arg, *args,
                                                            **kws)

# ______________________________________________________________________

def build_cfg (func):
    '''Given a Python function, create a bytecode flow, visit the flow
    object, and return a control flow graph.'''
    co_obj = opcode_util.get_code_object(func)
    return ControlFlowBuilder().visit(opcode_util.build_basic_blocks(co_obj),
                                      co_obj.co_argcount)

# ______________________________________________________________________
# Main (self-test) routine

def main (*args, **kws):
    from tests import llfuncs
    if not args:
        args = ('doslice',)
    for arg in args:
        build_cfg(getattr(llfuncs, arg)).pprint()

# ______________________________________________________________________

if __name__ == "__main__":
    import sys
    main(*sys.argv[1:])

# ______________________________________________________________________
# End of byte_control.py

########NEW FILE########
__FILENAME__ = byte_flow
# ______________________________________________________________________
from __future__ import absolute_import
import dis
import opcode

from .bytecode_visitor import BasicBlockVisitor
from . import opcode_util

# ______________________________________________________________________

class BytecodeFlowBuilder (BasicBlockVisitor):
    '''Transforms a CFG into a bytecode "flow tree".

    The flow tree is a Python dictionary, described loosely by the
    following set of productions:

      * `flow_tree` ``:=`` ``{`` `blocks` ``*`` ``}``
      * `blocks` ``:=`` `block_index` ``:`` ``[`` `bytecode_tree` ``*`` ``]``
      * `bytecode_tree` ``:=`` ``(`` `opcode_index` ``,`` `opcode` ``,``
          `opname` ``,`` `arg` ``,`` ``[`` `bytecode_tree` ``*`` ``]`` ``)``

    The primary purpose of this transformation is to simulate the
    value stack, removing it and any stack-specific opcodes.'''

    def __init__ (self, *args, **kws):
        super(BytecodeFlowBuilder, self).__init__(*args, **kws)
        om_items = opcode_util.OPCODE_MAP.items()
        self.opmap = dict((opcode.opmap[opname], (opname, pops, pushes, stmt))
                          for opname, (pops, pushes, stmt) in om_items
                          if opname in opcode.opmap)

    def _visit_op (self, i, op, arg, opname, pops, pushes, appends):
        assert pops is not None, ('%s not well defined in opcode_util.'
                                  'OPCODE_MAP' % opname)
        if pops:
            if pops < 0:
                pops = arg - pops - 1
            assert pops <= len(self.stack), ("Stack underflow at instruction "
                                             "%d (%s)!" % (i, opname))
            stk_args = self.stack[-pops:]
            del self.stack[-pops:]
        else:
            stk_args = []
        ret_val = (i, op, opname, arg, stk_args)
        if pushes:
            self.stack.append(ret_val)
        if appends:
            self.block.append(ret_val)
        return ret_val

    def _op (self, i, op, arg):
        opname, pops, pushes, appends = self.opmap[op]
        return self._visit_op(i, op, arg, opname, pops, pushes, appends)

    def visit_cfg (self, cfg):
        self.cfg = cfg
        ret_val = self.visit(cfg.blocks)
        del self.cfg
        return ret_val

    def enter_blocks (self, blocks):
        labels = list(blocks.keys())
        labels.sort()
        self.blocks = dict((index, [])
                           for index in labels)
        self.loop_stack = []
        self.stacks = {}

    def exit_blocks (self, blocks):
        ret_val = self.blocks
        del self.stacks
        del self.loop_stack
        del self.blocks
        return ret_val

    def enter_block (self, block):
        self.block_no = block
        self.block = self.blocks[block]
        in_blocks = self.cfg.blocks_in[block]
        if len(in_blocks) == 0:
            self.stack = []
        else:
            pred_stack = None
            for pred in in_blocks:
                if pred in self.stacks:
                    pred_stack = self.stacks[pred]
                    break
            if pred_stack is not None:
                self.stack = pred_stack[:]
            else:
                raise NotImplementedError()

    def exit_block (self, block):
        assert self.block_no == block
        self.stacks[block] = self.stack
        del self.stack
        del self.block
        del self.block_no

    op_BINARY_ADD = _op
    op_BINARY_AND = _op
    op_BINARY_DIVIDE = _op
    op_BINARY_FLOOR_DIVIDE = _op
    op_BINARY_LSHIFT = _op
    op_BINARY_MODULO = _op
    op_BINARY_MULTIPLY = _op
    op_BINARY_OR = _op
    op_BINARY_POWER = _op
    op_BINARY_RSHIFT = _op
    op_BINARY_SUBSCR = _op
    op_BINARY_SUBTRACT = _op
    op_BINARY_TRUE_DIVIDE = _op
    op_BINARY_XOR = _op

    def op_BREAK_LOOP (self, i, op, arg):
        loop_i, _, loop_arg = self.loop_stack[-1]
        assert arg is None
        return self._op(i, op, loop_i + loop_arg + 3)

    #op_BUILD_CLASS = _op
    op_BUILD_LIST = _op
    op_BUILD_MAP = _op
    op_BUILD_SLICE = _op
    op_BUILD_TUPLE = _op
    op_CALL_FUNCTION = _op
    op_CALL_FUNCTION_KW = _op
    op_CALL_FUNCTION_VAR = _op
    op_CALL_FUNCTION_VAR_KW = _op
    op_COMPARE_OP = _op
    #op_CONTINUE_LOOP = _op
    op_DELETE_ATTR = _op
    op_DELETE_FAST = _op
    op_DELETE_GLOBAL = _op
    op_DELETE_NAME = _op
    op_DELETE_SLICE = _op
    op_DELETE_SUBSCR = _op

    def op_DUP_TOP (self, i, op, arg):
        self.stack.append(self.stack[-1])

    def op_DUP_TOPX (self, i, op, arg):
        self.stack += self.stack[-arg:]

    #op_END_FINALLY = _op
    op_EXEC_STMT = _op
    #op_EXTENDED_ARG = _op
    op_FOR_ITER = _op
    op_GET_ITER = _op
    op_IMPORT_FROM = _op
    op_IMPORT_NAME = _op
    op_IMPORT_STAR = _op
    op_INPLACE_ADD = _op
    op_INPLACE_AND = _op
    op_INPLACE_DIVIDE = _op
    op_INPLACE_FLOOR_DIVIDE = _op
    op_INPLACE_LSHIFT = _op
    op_INPLACE_MODULO = _op
    op_INPLACE_MULTIPLY = _op
    op_INPLACE_OR = _op
    op_INPLACE_POWER = _op
    op_INPLACE_RSHIFT = _op
    op_INPLACE_SUBTRACT = _op
    op_INPLACE_TRUE_DIVIDE = _op
    op_INPLACE_XOR = _op
    op_JUMP_ABSOLUTE = _op
    op_JUMP_FORWARD = _op

    def op_JUMP_IF_FALSE (self, i, op, arg):
        opname, _, _, _ = self.opmap[op]
        ret_val = (i, op, opname, arg, [self.stack[-1]])
        self.block.append(ret_val)
        return ret_val

    op_JUMP_IF_TRUE = op_JUMP_IF_FALSE
    op_LIST_APPEND = _op
    op_LOAD_ATTR = _op
    op_LOAD_CLOSURE = _op
    op_LOAD_CONST = _op
    op_LOAD_DEREF = _op
    op_LOAD_FAST = _op
    op_LOAD_GLOBAL = _op
    op_LOAD_LOCALS = _op
    op_LOAD_NAME = _op
    op_MAKE_CLOSURE = _op
    op_MAKE_FUNCTION = _op
    op_NOP = _op

    def op_POP_BLOCK (self, i, op, arg):
        self.loop_stack.pop()
        return self._op(i, op, arg)

    op_POP_JUMP_IF_FALSE = _op
    op_POP_JUMP_IF_TRUE = _op
    op_POP_TOP = _op
    op_PRINT_EXPR = _op
    op_PRINT_ITEM = _op
    op_PRINT_ITEM_TO = _op
    op_PRINT_NEWLINE = _op
    op_PRINT_NEWLINE_TO = _op
    op_RAISE_VARARGS = _op
    op_RETURN_VALUE = _op

    def op_ROT_FOUR (self, i, op, arg):
        self.stack[-4:] = (self.stack[-1], self.stack[-4], self.stack[-3],
                           self.stack[-2])

    def op_ROT_THREE (self, i, op, arg):
        self.stack[-3:] = (self.stack[-1], self.stack[-3], self.stack[-2])

    def op_ROT_TWO (self, i, op, arg):
        self.stack[-2:] = (self.stack[-1], self.stack[-2])

    #op_SETUP_EXCEPT = _op
    #op_SETUP_FINALLY = _op

    def op_SETUP_LOOP (self, i, op, arg):
        self.loop_stack.append((i, op, arg))
        self.block.append((i, op, self.opnames[op], arg, []))

    op_SLICE = _op
    #op_STOP_CODE = _op
    op_STORE_ATTR = _op
    op_STORE_DEREF = _op
    op_STORE_FAST = _op
    op_STORE_GLOBAL = _op
    op_STORE_MAP = _op
    op_STORE_NAME = _op
    op_STORE_SLICE = _op
    op_STORE_SUBSCR = _op
    op_UNARY_CONVERT = _op
    op_UNARY_INVERT = _op
    op_UNARY_NEGATIVE = _op
    op_UNARY_NOT = _op
    op_UNARY_POSITIVE = _op
    op_UNPACK_SEQUENCE = _op
    #op_WITH_CLEANUP = _op
    op_YIELD_VALUE = _op

# ______________________________________________________________________

def build_flow (func):
    '''Given a Python function, return a bytecode flow tree for that
    function.'''
    import byte_control
    cfg = byte_control.build_cfg(func)
    return BytecodeFlowBuilder().visit_cfg(cfg)

# ______________________________________________________________________
# Main (self-test) routine

def main (*args):
    import pprint
    from tests import llfuncs
    if not args:
        args = ('doslice',)
    for arg in args:
        pprint.pprint(build_flow(getattr(llfuncs, arg)))

# ______________________________________________________________________

if __name__ == '__main__':
    import sys
    main(*sys.argv[1:])

# ______________________________________________________________________
# End of byte_flow.py

########NEW FILE########
__FILENAME__ = byte_translator
# ______________________________________________________________________
'''Defines a bytecode based LLVM translator for llpython code.
'''
# ______________________________________________________________________
# Module imports
from __future__ import absolute_import
import opcode
import types
import logging

import llvm.core as lc

from . import opcode_util
from . import bytetype
from .bytecode_visitor import BytecodeFlowVisitor
from .byte_flow import BytecodeFlowBuilder
from .byte_control import ControlFlowBuilder
from .phi_injector import PhiInjector, synthetic_opname

# ______________________________________________________________________
# Module data

logger = logging.getLogger(__name__)

# XXX Stolen from numba.translate:

_compare_mapping_float = {'>':lc.FCMP_OGT,
                           '<':lc.FCMP_OLT,
                           '==':lc.FCMP_OEQ,
                           '>=':lc.FCMP_OGE,
                           '<=':lc.FCMP_OLE,
                           '!=':lc.FCMP_ONE}

_compare_mapping_sint = {'>':lc.ICMP_SGT,
                          '<':lc.ICMP_SLT,
                          '==':lc.ICMP_EQ,
                          '>=':lc.ICMP_SGE,
                          '<=':lc.ICMP_SLE,
                          '!=':lc.ICMP_NE}

# XXX Stolen from numba.llvm_types:

class LLVMCaster (object):
    def build_pointer_cast(_, builder, lval1, lty2):
        return builder.bitcast(lval1, lty2)

    def build_int_cast(_, builder, lval1, lty2, unsigned = False):
        width1 = lval1.type.width
        width2 = lty2.width
        ret_val = lval1
        if width2 > width1:
            if unsigned:
                ret_val = builder.zext(lval1, lty2)
            else:
                ret_val = builder.sext(lval1, lty2)
        elif width2 < width1:
            ret_val = builder.trunc(lval1, lty2)
        return ret_val

    def build_float_ext(_, builder, lval1, lty2):
        return builder.fpext(lval1, lty2)

    def build_float_trunc(_, builder, lval1, lty2):
        return builder.fptrunc(lval1, lty2)

    def build_int_to_float_cast(_, builder, lval1, lty2, unsigned = False):
        ret_val = None
        if unsigned:
            ret_val = builder.uitofp(lval1, lty2)
        else:
            ret_val = builder.sitofp(lval1, lty2)
        return ret_val

    def build_int_to_ptr_cast(_, builder, lval1, lty2):
        return builder.inttoptr(lval1, lty2)

    def build_float_to_int_cast(_, builder, lval1, lty2, unsigned = False):
        ret_val = None
        if unsigned:
            ret_val = builder.fptoui(lval1, lty2)
        else:
            ret_val = builder.fptosi(lval1, lty2)
        return ret_val

    CAST_MAP = {
        lc.TYPE_POINTER : build_pointer_cast,
        lc.TYPE_INTEGER: build_int_cast,
        (lc.TYPE_FLOAT, lc.TYPE_DOUBLE) : build_float_ext,
        (lc.TYPE_DOUBLE, lc.TYPE_FLOAT) : build_float_trunc,
        (lc.TYPE_INTEGER, lc.TYPE_FLOAT) : build_int_to_float_cast,
        (lc.TYPE_INTEGER, lc.TYPE_DOUBLE) : build_int_to_float_cast,
        (lc.TYPE_INTEGER, lc.TYPE_POINTER) : build_int_to_ptr_cast,
        (lc.TYPE_FLOAT, lc.TYPE_INTEGER) : build_float_to_int_cast,
        (lc.TYPE_DOUBLE, lc.TYPE_INTEGER) : build_float_to_int_cast,

    }

    @classmethod
    def build_cast(cls, builder, lval1, lty2, *args, **kws):
        ret_val = lval1
        lty1 = lval1.type
        lkind1 = lty1.kind
        lkind2 = lty2.kind

        if lkind1 == lkind2:

            if lkind1 in cls.CAST_MAP:
                ret_val = cls.CAST_MAP[lkind1](cls, builder, lval1, lty2,
                                               *args, **kws)
            else:
                raise NotImplementedError(lkind1)
        else:
            map_index = (lkind1, lkind2)
            if map_index in cls.CAST_MAP:
                ret_val = cls.CAST_MAP[map_index](cls, builder, lval1, lty2,
                                                  *args, **kws)
            else:
                raise NotImplementedError(lkind1, lkind2)
        return ret_val

# ______________________________________________________________________
# Class definitions

class LLVMTranslator (BytecodeFlowVisitor):
    '''Transformer responsible for visiting a set of bytecode flow
    trees, emitting LLVM code.

    Unlike other translators in :py:mod:`llpython`, this
    incorporates the full transformation chain, starting with
    :py:class:`llpython.byte_flow.BytecodeFlowBuilder`, then
    :py:class:`llpython.byte_control.ControlFlowBuilder`, and
    then :py:class:`llpython.phi_injector.PhiInjector`.'''

    def __init__ (self, llvm_module = None, *args, **kws):
        '''Constructor for LLVMTranslator.'''
        super(LLVMTranslator, self).__init__(*args, **kws)
        if llvm_module is None:
            llvm_module = lc.Module.new('Translated_Module_%d' % (id(self),))
        self.llvm_module = llvm_module
        self.bytecode_flow_builder = BytecodeFlowBuilder()
        self.control_flow_builder = ControlFlowBuilder()
        self.phi_injector = PhiInjector()

    def translate (self, function, llvm_type = None, llvm_function = None,
                   env = None):
        '''Translate a function to the given LLVM function type.

        If no type is given, then assume the function is of LLVM type
        "void ()".

        The optional env parameter allows extension of the global
        environment.'''
        if llvm_type is None:
            if llvm_function is None:
                llvm_type = lc.Type.function(bytetype.lvoid, ())
            else:
                llvm_type = llvm_function.type.pointee
        if env is None:
            env = {}
        else:
            env = env.copy()
        env.update((name, method)
                   for name, method in lc.Builder.__dict__.items()
                   if not name.startswith('_'))
        env.update((name, value)
                   for name, value in bytetype.__dict__.items()
                   if not name.startswith('_'))
        self.loop_stack = []
        self.llvm_type = llvm_type
        self.target_function_name = env.get('target_function_name',
                                            function.__name__)
        self.function = function
        self.code_obj = opcode_util.get_code_object(function)
        func_globals = getattr(function, 'func_globals',
                               getattr(function, '__globals__', {})).copy()
        func_globals.update(env)
        self.globals = func_globals
        nargs = self.code_obj.co_argcount
        self.cfg = self.control_flow_builder.visit(
            opcode_util.build_basic_blocks(self.code_obj), nargs)
        self.cfg.blocks = self.bytecode_flow_builder.visit_cfg(self.cfg)
        self.llvm_function = llvm_function
        flow = self.phi_injector.visit_cfg(self.cfg, nargs)
        ret_val = self.visit(flow)
        del self.cfg
        del self.globals
        del self.code_obj
        del self.target_function_name
        del self.function
        del self.llvm_type
        del self.loop_stack
        return ret_val

    def enter_flow_object (self, flow):
        super(LLVMTranslator, self).enter_flow_object(flow)
        if self.llvm_function is None:
            self.llvm_function = self.llvm_module.add_function(
                self.llvm_type, self.target_function_name)
        self.llvm_blocks = {}
        self.llvm_definitions = {}
        self.pending_phis = {}
        for block in self.block_list:
            if 0 in self.cfg.blocks_reaching[block]:
                bb = self.llvm_function.append_basic_block(
                    'BLOCK_%d' % (block,))
                self.llvm_blocks[block] = bb

    def exit_flow_object (self, flow):
        super(LLVMTranslator, self).exit_flow_object(flow)
        ret_val = self.llvm_function
        del self.pending_phis
        del self.llvm_definitions
        del self.llvm_blocks
        if __debug__ and logger.getEffectiveLevel() < logging.DEBUG:
            logger.debug(str(ret_val))
        return ret_val

    def enter_block (self, block):
        ret_val = False
        if block in self.llvm_blocks:
            self.llvm_block = self.llvm_blocks[block]
            self.builder = lc.Builder.new(self.llvm_block)
            ret_val = True
        return ret_val

    def exit_block (self, block):
        bb_instrs = self.llvm_block.instructions
        if ((len(bb_instrs) == 0) or
                (not bb_instrs[-1].is_terminator)):
            out_blocks = list(self.cfg.blocks_out[block])
            assert len(out_blocks) == 1
            self.builder.branch(self.llvm_blocks[out_blocks[0]])
        del self.llvm_block
        del self.builder

    def visit_synthetic_op (self, i, op, arg, *args, **kws):
        method = getattr(self, 'op_%s' % (synthetic_opname[op],))
        return method(i, op, arg, *args, **kws)

    def op_REF_ARG (self, i, op, arg, *args, **kws):
        return [self.llvm_function.args[arg]]

    def op_BUILD_PHI (self, i, op, arg, *args, **kws):
        phi_type = None
        incoming = []
        pending = []
        for child_arg in arg:
            child_block, _, child_opname, child_arg, _ = child_arg
            assert child_opname == 'REF_DEF'
            if child_arg in self.llvm_definitions:
                child_def = self.llvm_definitions[child_arg]
                if phi_type is None:
                    phi_type = child_def.type
                incoming.append((child_block, child_def))
            else:
                pending.append((child_arg, child_block))
        phi = self.builder.phi(phi_type)
        for block_index, defn in incoming:
            phi.add_incoming(defn, self.llvm_blocks[block_index])
        for defn_index, block_index in pending:
            if defn_index not in self.pending_phis:
                self.pending_phis[defn_index] = []
            self.pending_phis[defn_index].append((phi, block_index))
        return [phi]

    def op_DEFINITION (self, i, op, def_index, *args, **kws):
        assert len(args) == 1
        arg = args[0]
        if def_index in self.pending_phis:
            for phi, block_index in self.pending_phis[def_index]:
                phi.add_incoming(arg, self.llvm_blocks[block_index])
        self.llvm_definitions[def_index] = arg
        return args

    def op_REF_DEF (self, i, op, arg, *args, **kws):
        return [self.llvm_definitions[arg]]

    def op_BINARY_ADD (self, i, op, arg, *args, **kws):
        arg1, arg2 = args
        if arg1.type.kind == lc.TYPE_INTEGER:
            ret_val = [self.builder.add(arg1, arg2)]
        elif arg1.type.kind in (lc.TYPE_FLOAT, lc.TYPE_DOUBLE):
            ret_val = [self.builder.fadd(arg1, arg2)]
        elif arg1.type.kind == lc.TYPE_POINTER:
            ret_val = [self.builder.gep(arg1, [arg2])]
        else:
            raise NotImplementedError("LLVMTranslator.op_BINARY_ADD for %r" %
                                      (args,))
        return ret_val

    def op_BINARY_AND (self, i, op, arg, *args, **kws):
        return [self.builder.and_(args[0], args[1])]

    def op_BINARY_DIVIDE (self, i, op, arg, *args, **kws):
        arg1, arg2 = args
        if arg1.type.kind == lc.TYPE_INTEGER:
            ret_val = [self.builder.sdiv(arg1, arg2)]
        elif arg1.type.kind in (lc.TYPE_FLOAT, lc.TYPE_DOUBLE):
            ret_val = [self.builder.fdiv(arg1, arg2)]
        else:
            raise NotImplementedError("LLVMTranslator.op_BINARY_DIVIDE for %r"
                                      % (args,))
        return ret_val

    def op_BINARY_FLOOR_DIVIDE (self, i, op, arg, *args, **kws):
        raise NotImplementedError("LLVMTranslator.op_BINARY_FLOOR_DIVIDE")

    def op_BINARY_LSHIFT (self, i, op, arg, *args, **kws):
        return [self.builder.shl(args[0], args[1])]

    def op_BINARY_MODULO (self, i, op, arg, *args, **kws):
        arg1, arg2 = args
        if arg1.type.kind == lc.TYPE_INTEGER:
            ret_val = [self.builder.srem(arg1, arg2)]
        elif arg1.type.kind in (lc.TYPE_FLOAT, lc.TYPE_DOUBLE):
            ret_val = [self.builder.frem(arg1, arg2)]
        else:
            raise NotImplementedError("LLVMTranslator.op_BINARY_MODULO for %r"
                                      % (args,))
        return ret_val

    def op_BINARY_MULTIPLY (self, i, op, arg, *args, **kws):
        arg1, arg2 = args
        if arg1.type.kind == lc.TYPE_INTEGER:
            ret_val = [self.builder.mul(arg1, arg2)]
        elif arg1.type.kind in (lc.TYPE_FLOAT, lc.TYPE_DOUBLE):
            ret_val = [self.builder.fmul(arg1, arg2)]
        else:
            raise NotImplementedError("LLVMTranslator.op_BINARY_MULTIPLY for "
                                      "%r" % (args,))
        return ret_val

    def op_BINARY_OR (self, i, op, arg, *args, **kws):
        return [self.builder.or_(args[0], args[1])]

    def op_BINARY_POWER (self, i, op, arg, *args, **kws):
        raise NotImplementedError("LLVMTranslator.op_BINARY_POWER")

    def op_BINARY_RSHIFT (self, i, op, arg, *args, **kws):
        return [self.builder.lshr(args[0], args[1])]

    def op_BINARY_SUBSCR (self, i, op, arg, *args, **kws):
        arr_val = args[0]
        index_vals = args[1:]
        ret_val = gep_result = self.builder.gep(arr_val, index_vals)
        if (gep_result.type.kind == lc.TYPE_POINTER and
            gep_result.type.pointee.kind != lc.TYPE_POINTER):
            ret_val = self.builder.load(gep_result)
        return [ret_val]

    def op_BINARY_SUBTRACT (self, i, op, arg, *args, **kws):
        arg1, arg2 = args
        if arg1.type.kind == lc.TYPE_INTEGER:
            ret_val = [self.builder.sub(arg1, arg2)]
        elif arg1.type.kind in (lc.TYPE_FLOAT, lc.TYPE_DOUBLE):
            ret_val = [self.builder.fsub(arg1, arg2)]
        else:
            raise NotImplementedError("LLVMTranslator.op_BINARY_SUBTRACT for "
                                      "%r" % (args,))
        return ret_val

    op_BINARY_TRUE_DIVIDE = op_BINARY_DIVIDE

    def op_BINARY_XOR (self, i, op, arg, *args, **kws):
        return [self.builder.xor(args[0], args[1])]

    def op_BREAK_LOOP (self, i, op, arg, *args, **kws):
        return [self.builder.branch(self.llvm_blocks[arg])]

    def op_BUILD_SLICE (self, i, op, arg, *args, **kws):
        raise NotImplementedError("LLVMTranslator.op_BUILD_SLICE")

    def op_BUILD_TUPLE (self, i, op, arg, *args, **kws):
        return args

    def op_CALL_FUNCTION (self, i, op, arg, *args, **kws):
        fn = args[0]
        args = args[1:]
        fn_name = getattr(fn, '__name__', None)
        if isinstance(fn, (types.FunctionType, types.MethodType)):
            ret_val = [fn(self.builder, *args)]
        elif isinstance(fn, lc.Value):
            ret_val = [self.builder.call(fn, args)]
        elif isinstance(fn, lc.Type):
            if isinstance(fn, lc.FunctionType):
                ret_val = [self.builder.call(
                        self.llvm_module.get_or_insert_function(fn, fn_name),
                        args)]
            else:
                assert len(args) == 1
                ret_val = [LLVMCaster.build_cast(self.builder, args[0], fn)]
        else:
            raise NotImplementedError("Don't know how to call %s() (%r @ %d)!"
                                      % (fn_name, fn, i))
        return ret_val

    def op_CALL_FUNCTION_KW (self, i, op, arg, *args, **kws):
        raise NotImplementedError("LLVMTranslator.op_CALL_FUNCTION_KW")

    def op_CALL_FUNCTION_VAR (self, i, op, arg, *args, **kws):
        args = list(args)
        var_args = list(args.pop())
        args.extend(var_args)
        return self.op_CALL_FUNCTION(i, op, arg, *args, **kws)

    def op_CALL_FUNCTION_VAR_KW (self, i, op, arg, *args, **kws):
        raise NotImplementedError("LLVMTranslator.op_CALL_FUNCTION_VAR_KW")

    def op_COMPARE_OP (self, i, op, arg, *args, **kws):
        arg1, arg2 = args
        cmp_kind = opcode.cmp_op[arg]
        if isinstance(arg1.type, lc.IntegerType):
            ret_val = [self.builder.icmp(_compare_mapping_sint[cmp_kind],
                                         arg1, arg2)]
        elif arg1.type.kind in (lc.TYPE_FLOAT, lc.TYPE_DOUBLE):
            ret_val = [self.builder.fcmp(_compare_mapping_float[cmp_kind],
                                         arg1, arg2)]
        else:
            raise NotImplementedError('Comparison of type %r' % (arg1.type,))
        return ret_val

    def op_CONTINUE_LOOP (self, i, op, arg, *args, **kws):
        raise NotImplementedError("LLVMTranslator.op_CONTINUE_LOOP")

    def op_DELETE_ATTR (self, i, op, arg, *args, **kws):
        raise NotImplementedError("LLVMTranslator.op_DELETE_ATTR")

    def op_DELETE_SLICE (self, i, op, arg, *args, **kws):
        raise NotImplementedError("LLVMTranslator.op_DELETE_SLICE")

    def op_FOR_ITER (self, i, op, arg, *args, **kws):
        raise NotImplementedError("LLVMTranslator.op_FOR_ITER")

    def op_GET_ITER (self, i, op, arg, *args, **kws):
        raise NotImplementedError("LLVMTranslator.op_GET_ITER")

    op_INPLACE_ADD = op_BINARY_ADD
    op_INPLACE_AND = op_BINARY_AND
    op_INPLACE_DIVIDE = op_BINARY_DIVIDE
    op_INPLACE_FLOOR_DIVIDE = op_BINARY_FLOOR_DIVIDE
    op_INPLACE_LSHIFT = op_BINARY_LSHIFT
    op_INPLACE_MODULO = op_BINARY_MODULO
    op_INPLACE_MULTIPLY = op_BINARY_MULTIPLY
    op_INPLACE_OR = op_BINARY_OR
    op_INPLACE_POWER = op_BINARY_POWER
    op_INPLACE_RSHIFT = op_BINARY_RSHIFT
    op_INPLACE_SUBTRACT = op_BINARY_SUBTRACT
    op_INPLACE_TRUE_DIVIDE = op_BINARY_TRUE_DIVIDE
    op_INPLACE_XOR = op_BINARY_XOR

    def op_JUMP_ABSOLUTE (self, i, op, arg, *args, **kws):
        return [self.builder.branch(self.llvm_blocks[arg])]

    def op_JUMP_FORWARD (self, i, op, arg, *args, **kws):
        return [self.builder.branch(self.llvm_blocks[i + arg + 3])]

    def op_JUMP_IF_FALSE (self, i, op, arg, *args, **kws):
        cond = args[0]
        block_false = self.llvm_blocks[i + 3 + arg]
        block_true = self.llvm_blocks[i + 3]
        return [self.builder.cbranch(cond, block_true, block_false)]
        # raise NotImplementedError("LLVMTranslator.op_JUMP_IF_FALSE")

    def op_JUMP_IF_FALSE_OR_POP (self, i, op, arg, *args, **kws):
        raise NotImplementedError("LLVMTranslator.op_JUMP_IF_FALSE_OR_POP")

    def op_JUMP_IF_TRUE (self, i, op, arg, *args, **kws):
        raise NotImplementedError("LLVMTranslator.op_JUMP_IF_TRUE")

    def op_JUMP_IF_TRUE_OR_POP (self, i, op, arg, *args, **kws):
        raise NotImplementedError("LLVMTranslator.op_JUMP_IF_TRUE_OR_POP")

    def op_LOAD_ATTR (self, i, op, arg, *args, **kws):
        raise NotImplementedError("LLVMTranslator.op_LOAD_ATTR")

    def op_LOAD_CONST (self, i, op, arg, *args, **kws):
        py_val = self.code_obj.co_consts[arg]
        if isinstance(py_val, int):
            ret_val = [lc.Constant.int(bytetype.lc_int, py_val)]
        elif isinstance(py_val, float):
            ret_val = [lc.Constant.double(py_val)]
        elif py_val == None:
            ret_val = [None]
        else:
            raise NotImplementedError('Constant converstion for %r' %
                                      (py_val,))
        return ret_val

    def op_LOAD_DEREF (self, i, op, arg, *args, **kws):
        name = self.code_obj.co_freevars[arg]
        ret_val = self.globals[name]
        if isinstance(ret_val, lc.Type) and not hasattr(ret_val, '__name__'):
            ret_val.__name__ = name
        return [ret_val]

    def op_LOAD_GLOBAL (self, i, op, arg, *args, **kws):
        name = self.code_obj.co_names[arg]
        ret_val = self.globals[name]
        if isinstance(ret_val, lc.Type) and not hasattr(ret_val, '__name__'):
            ret_val.__name__ = name
        return [ret_val]

    def op_POP_BLOCK (self, i, op, arg, *args, **kws):
        self.loop_stack.pop()
        return [self.builder.branch(self.llvm_blocks[i + 1])]

    def op_POP_JUMP_IF_FALSE (self, i, op, arg, *args, **kws):
        return [self.builder.cbranch(args[0], self.llvm_blocks[i + 3],
                                     self.llvm_blocks[arg])]

    def op_POP_JUMP_IF_TRUE (self, i, op, arg, *args, **kws):
        raise NotImplementedError("LLVMTranslator.op_POP_JUMP_IF_TRUE")

    def op_POP_TOP (self, i, op, arg, *args, **kws):
        return args

    def op_RETURN_VALUE (self, i, op, arg, *args, **kws):
        if args[0] is None:
            ret_val = [self.builder.ret_void()]
        else:
            ret_val = [self.builder.ret(args[0])]
        return ret_val

    def op_SETUP_LOOP (self, i, op, arg, *args, **kws):
        self.loop_stack.append((i, arg))
        return [self.builder.branch(self.llvm_blocks[i + 3])]

    def op_SLICE (self, i, op, arg, *args, **kws):
        raise NotImplementedError("LLVMTranslator.op_SLICE")

    def op_STORE_ATTR (self, i, op, arg, *args, **kws):
        raise NotImplementedError("LLVMTranslator.op_STORE_ATTR")

    def op_STORE_SLICE (self, i, op, arg, *args, **kws):
        raise NotImplementedError("LLVMTranslator.op_STORE_SLICE")

    def op_STORE_SUBSCR (self, i, op, arg, *args, **kws):
        store_val, arr_val, index_val = args
        dest_addr = self.builder.gep(arr_val, [index_val])
        return [self.builder.store(store_val, dest_addr)]

    def op_UNARY_CONVERT (self, i, op, arg, *args, **kws):
        raise NotImplementedError("LLVMTranslator.op_UNARY_CONVERT")

    def op_UNARY_INVERT (self, i, op, arg, *args, **kws):
        raise NotImplementedError("LLVMTranslator.op_UNARY_INVERT")

    def op_UNARY_NEGATIVE (self, i, op, arg, *args, **kws):
        raise NotImplementedError("LLVMTranslator.op_UNARY_NEGATIVE")

    def op_UNARY_NOT (self, i, op, arg, *args, **kws):
        raise NotImplementedError("LLVMTranslator.op_UNARY_NOT")

    def op_UNARY_POSITIVE (self, i, op, arg, *args, **kws):
        raise NotImplementedError("LLVMTranslator.op_UNARY_POSITIVE")

# ______________________________________________________________________

def translate_function (func, lltype, llvm_module = None, **kws):
    '''Given a function and an LLVM function type, emit LLVM code for
    that function using a new LLVMTranslator instance.'''
    translator = LLVMTranslator(llvm_module)
    ret_val = translator.translate(func, lltype, env = kws)
    return ret_val

# ______________________________________________________________________

def translate_into_function (py_function, llvm_function, **kws):
    translator = LLVMTranslator(llvm_function.module)
    ret_val = translator.translate(py_function, llvm_function = llvm_function,
                                   env = kws)
    return ret_val

# ______________________________________________________________________

def llpython (lltype, llvm_module = None, **kws):
    '''Decorator version of translate_function().'''
    def _llpython (func):
        return translate_function(func, lltype, llvm_module, **kws)
    return _llpython

# ______________________________________________________________________

def llpython_into (llvm_function, **kws):
    def _llpython_into (func):
        return translate_into_function(llvm_function, func, **kws)
    return _llpython_into

# ______________________________________________________________________
# Main (self-test) routine

def main (*args):
    from tests import llfuncs, llfunctys
    if not args:
        args = ('doslice',)
    elif 'all' in args:
        args = [llfunc
                for llfunc in dir(llfuncs) if not llfunc.startswith('_')]
    llvm_module = lc.Module.new('test_module')
    for arg in args:
        translate_function(getattr(llfuncs, arg), getattr(llfunctys, arg),
                           llvm_module)
    print(llvm_module)

# ______________________________________________________________________

if __name__ == '__main__':
    import sys
    main(*sys.argv[1:])

# ______________________________________________________________________
# End of byte_translator.py

########NEW FILE########
__FILENAME__ = control_flow
# ______________________________________________________________________

import pprint

# ______________________________________________________________________

class ControlFlowGraph (object):
    def __init__ (self):
        self.blocks = {}
        self.blocks_in = {}
        self.blocks_out = {}
        self.blocks_reads = {}
        self.blocks_writes = {}
        self.blocks_writer = {}
        self.blocks_dom = {}
        self.blocks_reaching = {}

    def add_block (self, key, value = None):
        self.blocks[key] = value
        if key not in self.blocks_in:
            self.blocks_in[key] = set()
            self.blocks_out[key] = set()
            self.blocks_reads[key] = set()
            self.blocks_writes[key] = set()
            self.blocks_writer[key] = {}

    def add_edge (self, from_block, to_block):
        self.blocks_out[from_block].add(to_block)
        self.blocks_in[to_block].add(from_block)

    def unlink_unreachables (self):
        changed = True
        next_blocks = self.blocks.keys()
        next_blocks.remove(0)
        while changed:
            changed = False
            blocks = next_blocks
            next_blocks = blocks[:]
            for block in blocks:
                if len(self.blocks_in[block]) == 0:
                    blocks_out = self.blocks_out[block]
                    for out_edge in blocks_out:
                        self.blocks_in[out_edge].discard(block)
                    blocks_out.clear()
                    next_blocks.remove(block)
                    changed = True

    def compute_dataflow (self):
        '''Compute the dominator and reaching dataflow relationships
        in the CFG.'''
        blocks = set(self.blocks.keys())
        nonentry_blocks = blocks.copy()
        for block in blocks:
            self.blocks_dom[block] = blocks
            self.blocks_reaching[block] = set((block,))
            if len(self.blocks_in[block]) == 0:
                self.blocks_dom[block] = set((block,))
                nonentry_blocks.remove(block)
        changed = True
        while changed:
            changed = False
            for block in nonentry_blocks:
                olddom = self.blocks_dom[block]
                newdom = set.intersection(*[self.blocks_dom[pred]
                                            for pred in self.blocks_in[block]])
                newdom.add(block)
                if newdom != olddom:
                    changed = True
                    self.blocks_dom[block] = newdom
                oldreaching = self.blocks_reaching[block]
                newreaching = set.union(
                    *[self.blocks_reaching[pred]
                      for pred in self.blocks_in[block]])
                newreaching.add(block)
                if newreaching != oldreaching:
                    changed = True
                    self.blocks_reaching[block] = newreaching
        return self.blocks_dom, self.blocks_reaching

    def update_for_ssa (self):
        '''Modify the blocks_writes map to reflect phi nodes inserted
        for static single assignment representations.'''
        joins = [block for block in self.blocks.keys()
                 if len(self.blocks_in[block]) > 1]
        changed = True
        while changed:
            changed = False
            for block in joins:
                phis_needed = self.phi_needed(block)
                for affected_local in phis_needed:
                    if affected_local not in self.blocks_writes[block]:
                        changed = True
                        # NOTE: For this to work, we assume that basic
                        # blocks are indexed by their instruction
                        # index in the VM bytecode.
                        self.writes_local(block, block, affected_local)
            if changed:
                # Any modifications have invalidated the reaching
                # definitions, so delete any memoized results.
                if hasattr(self, 'reaching_definitions'):
                    del self.reaching_definitions

    def idom (self, block):
        '''Compute the immediate dominator (idom) of the given block
        key.  Returns None if the block has no in edges.

        Note that in the case where there are multiple immediate
        dominators (a join after a non-loop branch), this returns one
        of the predecessors, but is not guaranteed to reliably select
        one over the others (depends on the ordering of the set type
        iterator).'''
        preds = self.blocks_in[block]
        npreds = len(preds)
        if npreds == 0:
            ret_val = None
        elif npreds == 1:
            ret_val = tuple(preds)[0]
        else:
            ret_val = [pred for pred in preds
                       if block not in self.blocks_dom[pred]][0]
        return ret_val

    def block_writes_to_writer_map (self, block):
        ret_val = {}
        for local in self.blocks_writes[block]:
            ret_val[local] = block
        return ret_val

    def get_reaching_definitions (self, block):
        '''Return a nested map for the given block
        s.t. ret_val[pred][local] equals the block key for the
        definition of local that reaches the argument block via that
        predecessor.

        Useful for actually populating phi nodes, once you know you
        need them.'''
        has_memoized = hasattr(self, 'reaching_definitions')
        if has_memoized and block in self.reaching_definitions:
            ret_val = self.reaching_definitions[block]
        else:
            preds = self.blocks_in[block]
            ret_val = {}
            for pred in preds:
                ret_val[pred] = self.block_writes_to_writer_map(pred)
                crnt = self.idom(pred)
                while crnt != None:
                    crnt_writer_map = self.block_writes_to_writer_map(crnt)
                    # This order of update favors the first definitions
                    # encountered in the traversal since the traversal
                    # visits blocks in reverse execution order.
                    crnt_writer_map.update(ret_val[pred])
                    ret_val[pred] = crnt_writer_map
                    crnt = self.idom(crnt)
            if not has_memoized:
                self.reaching_definitions = {}
            self.reaching_definitions[block] = ret_val
        return ret_val

    def nreaches (self, block):
        '''For each local, find the number of unique reaching
        definitions the current block has.'''
        reaching_definitions = self.get_reaching_definitions(block)
        definition_map = {}
        for pred in self.blocks_in[block]:
            reaching_from_pred = reaching_definitions[pred]
            for local in reaching_from_pred.keys():
                if local not in definition_map:
                    definition_map[local] = set()
                definition_map[local].add(reaching_from_pred[local])
        ret_val = {}
        for local in definition_map.keys():
            ret_val[local] = len(definition_map[local])
        return ret_val

    def writes_local (self, block, write_instr_index, local_index):
        self.blocks_writes[block].add(local_index)
        block_writers = self.blocks_writer[block]
        old_index = block_writers.get(local_index, -1)
        # This checks for a corner case that would impact
        # numba.translate.Translate.build_phi_nodes().
        assert old_index != write_instr_index, (
            "Found corner case for STORE_FAST at a CFG join!")
        block_writers[local_index] = max(write_instr_index, old_index)

    def phi_needed (self, join):
        '''Return the set of locals that will require a phi node to be
        generated at the given join.'''
        nreaches = self.nreaches(join)
        return set([local for local in nreaches.keys()
                    if nreaches[local] > 1])

    def pprint (self, *args, **kws):
        pprint.pprint(self.__dict__, *args, **kws)

    def pformat (self, *args, **kws):
        return pprint.pformat(self.__dict__, *args, **kws)

    def to_dot (self, graph_name = None):
        '''Return a dot (digraph visualizer in Graphviz) graph
        description as a string.'''
        if graph_name is None:
            graph_name = 'CFG_%d' % id(self)
        lines_out = []
        for block_index in self.blocks:
            lines_out.append(
                'BLOCK_%r [shape=box, label="BLOCK_%r\\nr: %r, w: %r"];' %
                (block_index, block_index,
                 tuple(self.blocks_reads[block_index]),
                 tuple(self.blocks_writes[block_index])))
        for block_index in self.blocks:
            for out_edge in self.blocks_out[block_index]:
                lines_out.append('BLOCK_%r -> BLOCK_%r;' %
                                 (block_index, out_edge))
        return 'digraph %s {\n%s\n}\n' % (graph_name, '\n'.join(lines_out))

# ______________________________________________________________________
# End of control_flow.py

########NEW FILE########
__FILENAME__ = gen_bytecode_visitor
# ______________________________________________________________________
from __future__ import absolute_import
from . import opcode_util

# ______________________________________________________________________

def generate_bytecode_visitor (classname = 'BytecodeVisitor',
                               baseclass = 'object'):
    opnames = list(set((opname.split('+')[0]
                        for opname in opcode_util.OPCODE_MAP.keys())))
    opnames.sort()
    return 'class %s (%s):\n%s\n' % (
        classname, baseclass,
        '\n\n'.join(('    def op_%s (self, i, op, arg):\n'
                     '        raise NotImplementedError("%s.op_%s")' %
                     (opname, classname, opname)
                     for opname in opnames)))

# ______________________________________________________________________

if __name__ == "__main__":
    import sys
    print(generate_bytecode_visitor(*sys.argv[1:]))

# ______________________________________________________________________
# End of gen_bytecode_visitor.py

########NEW FILE########
__FILENAME__ = nobitey
# ______________________________________________________________________
from __future__ import absolute_import
import sys
import os.path
import imp
import io
import types

import llvm.core as lc
import llvm.ee as le

from . import bytetype, byte_translator
from .pyaddfunc import pyaddfunc

LLVM_TO_INT_PARSE_STR_MAP = {
    8 : 'b',
    16 : 'h',
    32 : 'i', # Note that on 32-bit systems sizeof(int) == sizeof(long)
    64 : 'L', # Seeing sizeof(long long) == 8 on both 32 and 64-bit platforms
}

LLVM_TO_PARSE_STR_MAP = {
    lc.TYPE_FLOAT : 'f',
    lc.TYPE_DOUBLE : 'd',
}

# ______________________________________________________________________

# XXX Stolen from numba.translate

def get_string_constant (module, const_str):
    const_name = "__STR_%x" % (hash(const_str),)
    try:
        ret_val = module.get_global_variable_named(const_name)
    except:
        lconst_str = lc.Constant.stringz(const_str)
        ret_val = module.add_global_variable(lconst_str.type, const_name)
        ret_val.initializer = lconst_str
        ret_val.linkage = lc.LINKAGE_INTERNAL
    return ret_val

# ______________________________________________________________________

class NoBitey (object):
    def __init__ (self, target_module = None, type_annotations = None):
        if target_module is None:
            target_module = lc.Module.new('NoBitey_%d' % id(self))
        if type_annotations is None:
            type_annotations = {}
        self.target_module = target_module
        self.type_aliases = type_annotations # Reserved for future use.

    def _build_parse_string (self, llvm_type):
        kind = llvm_type.kind
        if kind == lc.TYPE_INTEGER:
            ret_val = LLVM_TO_INT_PARSE_STR_MAP[llvm_type.width]
        elif kind in LLVM_TO_PARSE_STR_MAP:
            ret_val = LLVM_TO_PARSE_STR_MAP[kind]
        else:
            raise TypeError('Unsupported LLVM type: %s' % str(llvm_type))
        return ret_val

    def build_parse_string (self, llvm_tys):
        """Given a set of LLVM types, return a string for parsing
        them via PyArg_ParseTuple."""
        return ''.join((self._build_parse_string(ty)
                        for ty in llvm_tys))

    def handle_abi_casts (self, builder, result):
        if result.type.kind == lc.TYPE_FLOAT:
            # NOTE: The C ABI apparently casts floats to doubles when
            # an argument must be pushed on the stack, as is the case
            # when calling a variable argument function.
            # XXX Is there documentation on this where I can find all
            # coercion rules?  Do we still need some libffi
            # integration?
            result = builder.fpext(result, bytetype.ldouble)
        return result

    def build_wrapper_function (self, llvm_function, engine = None):
        arg_types = llvm_function.type.pointee.args
        return_type = llvm_function.type.pointee.return_type
        li32_0 = lc.Constant.int(bytetype.li32, 0)
        def get_llvm_function (builder):
            if self.target_module != llvm_function.module:
                llvm_function_ptr = self.target_module.add_global_variable(
                    llvm_function.type, llvm_function.name)
                llvm_function_ptr.initializer = lc.Constant.inttoptr(
                    lc.Constant.int(
                        bytetype.liptr,
                        engine.get_pointer_to_function(llvm_function)),
                    llvm_function.type)
                llvm_function_ptr.linkage = lc.LINKAGE_INTERNAL
                ret_val = builder.load(llvm_function_ptr)
            else:
                ret_val = llvm_function
            return ret_val
        def build_parse_args (builder):
            return [builder.alloca(arg_type) for arg_type in arg_types]
        def build_parse_string (builder):
            parse_str = get_string_constant(
                self.target_module, self.build_parse_string(arg_types))
            return builder.gep(parse_str, (li32_0, li32_0))
        def load_target_args (builder, args):
            return [builder.load(arg) for arg in args]
        def build_build_string (builder):
            build_str = get_string_constant(
                self.target_module, self._build_parse_string(return_type))
            return builder.gep(build_str, (li32_0, li32_0))
        handle_abi_casts = self.handle_abi_casts
        target_function_name = llvm_function.name + "_wrapper"
        # __________________________________________________
        @byte_translator.llpython(bytetype.l_pyfunc, self.target_module,
                                   **locals())
        def _wrapper (self, args):
            ret_val = l_pyobj_p(0)
            parse_args = build_parse_args()
            parse_result = PyArg_ParseTuple(args, build_parse_string(),
                                            *parse_args)
            if parse_result != li32(0):
                thread_state = PyEval_SaveThread()
                target_args = load_target_args(parse_args)
                llresult = handle_abi_casts(get_llvm_function()(*target_args))
                PyEval_RestoreThread(thread_state)
                ret_val = Py_BuildValue(build_build_string(), llresult)
            return ret_val
        # __________________________________________________
        return _wrapper

    def wrap_llvm_module (self, llvm_module, engine = None, py_module = None):
        '''
        Shamefully adapted from bitey.bind.wrap_llvm_module().
        '''
        functions = [func for func in llvm_module.functions
                     if not func.name.startswith("_")
                     and not func.is_declaration
                     and func.linkage == lc.LINKAGE_EXTERNAL]
        if engine is None:
            engine = le.ExecutionEngine.new(llvm_module)
        wrappers = [self.build_wrapper_function(func, engine)
                    for func in functions]
        if __debug__: print(self.target_module)
        if self.target_module != llvm_module:
            engine.add_module(self.target_module)
        py_wrappers = [pyaddfunc(wrapper.name,
                                 engine.get_pointer_to_function(wrapper))
                       for wrapper in wrappers]
        if py_module:
            for py_wrapper in py_wrappers:
                setattr(py_module, py_wrapper.__name__[:-8], py_wrapper)
            setattr(py_module, '_llvm_module', llvm_module)
            setattr(py_module, '_llvm_engine', engine)
            if self.target_module != llvm_module:
                setattr(py_module, '_llvm_wrappers', self.target_module)
        return engine, py_wrappers

    def wrap_llvm_module_in_python (self, llvm_module, py_module = None):
        '''
        Mildly reworked and abstracted bitey.bind.wrap_llvm_bitcode().
        Abstracted to accept any existing LLVM Module object, and
        return a Python wrapper module (even if one wasn't originally
        specified).
        '''
        if py_module is None:
            py_module = types.ModuleType(str(llvm_module.id))
        engine = le.ExecutionEngine.new(llvm_module)
        self.wrap_llvm_module(llvm_module, engine, py_module)
        return py_module

    def wrap_llvm_bitcode (self, bitcode, py_module = None):
        '''
        Intended to be drop-in replacement of
        bitey.bind.wrap_llvm_bitcode().
        '''
        return self.wrap_llvm_module_in_python(
            lc.Module.from_bitcode(io.BytesIO(bitcode)), py_module)

    def wrap_llvm_assembly (self, llvm_asm, py_module = None):
        return self.wrap_llvm_module_in_python(
            lc.Module.from_assembly(io.BytesIO(llvm_asm)), py_module)

# ______________________________________________________________________

class NoBiteyLoader(object):
    """
    Load LLVM compiled bitcode and autogenerate a ctypes binding.

    Initially copied and adapted from bitey.loader module.
    """
    def __init__(self, pkg, name, source, preload, postload):
        self.package = pkg
        self.name = name
        self.fullname = '.'.join((pkg,name))
        self.source = source
        self.preload = preload
        self.postload = postload

    @classmethod
    def _check_magic(cls, filename):
        if os.path.exists(filename):
            magic = open(filename,"rb").read(4)
            if magic == b'\xde\xc0\x17\x0b':
                return True
            elif magic[:2] == b'\x42\x43':
                return True
            else:
                return False
        else:
            return False

    @classmethod
    def build_module(cls, fullname, source_path, source_data, preload=None,
                     postload=None):
        name = fullname.split(".")[-1]
        mod = imp.new_module(name)
        if preload:
            exec(preload, mod.__dict__, mod.__dict__)
        type_annotations = getattr(mod, '_type_annotations', None)
        nb = NoBitey(type_annotations = type_annotations)
        if source_path.endswith(('.o', '.bc')):
            nb.wrap_llvm_bitcode(source_data, mod)
        elif source_path.endswith('.s'):
            nb.wrap_llvm_assembly(source_data, mod)
        if postload:
            exec(postload, mod.__dict__, mod.__dict__)
        return mod

    @classmethod
    def find_module(cls, fullname, paths = None):
        if paths is None:
            paths = sys.path
        names = fullname.split('.')
        modname = names[-1]
        source_paths = None
        for f in paths:
            path = os.path.join(os.path.realpath(f), modname)
            source = path + '.o'
            if cls._check_magic(source):
                source_paths = path, source
                break
            source = path + '.bc'
            if os.path.exists(source):
                source_paths = path, source
                break
            source = path + '.s'
            if os.path.exists(source):
                source_paths = path, source
                break
        if source_paths:
            path, source = source_paths
            return cls('.'.join(names[:-1]), modname, source,
                       path + ".pre.py", path + ".post.py")

    def get_code(self, module):
        pass

    def get_data(self, module):
        pass

    def get_filename(self, name):
        return self.source

    def get_source(self, name):
        with open(self.source, 'rb') as f:
             return f.read()

    def is_package(self, *args, **kw):
        return False

    def load_module(self, fullname):
        if fullname in sys.modules:
            return sys.modules[fullname]

        preload = None
        postload = None

        # Get the preload file (if any)
        if os.path.exists(self.preload):
            with open(self.preload) as f:
                preload = f.read()

        # Get the source
        with open(self.source, 'rb') as f:
            source_data = f.read()

        # Get the postload file (if any)
        if os.path.exists(self.postload):
            with open(self.postload) as f:
                postload = f.read()

        mod = self.build_module(fullname, self.get_filename(None), source_data,
                                preload, postload)
        sys.modules[fullname] = mod
        mod.__loader__ = self
        mod.__file__ = self.source
        return mod

    @classmethod
    def install(cls):
        if cls not in sys.meta_path:
            sys.meta_path.append(cls)

    @classmethod
    def remove(cls):
        sys.meta_path.remove(cls)

# ______________________________________________________________________

def _mk_add_42 (llvm_module, at_type = bytetype.lc_long):
    f = llvm_module.add_function(
        lc.Type.function(at_type, [at_type]), 'add_42_%s' % str(at_type))
    block = f.append_basic_block('entry')
    builder = lc.Builder.new(block)
    if at_type.kind == lc.TYPE_INTEGER:
        const_42 = lc.Constant.int(at_type, 42)
        add = builder.add
    elif at_type.kind in (lc.TYPE_FLOAT, lc.TYPE_DOUBLE):
        const_42 = lc.Constant.real(at_type, 42.)
        add = builder.fadd
    else:
        raise TypeError('Unsupported type: %s' % str(at_type))
    builder.ret(add(f.args[0], const_42))
    return f

# ______________________________________________________________________

def build_test_module ():
    llvm_module = lc.Module.new('nobitey_test')
    for ty in (bytetype.li32, bytetype.li64, bytetype.lfloat,
               bytetype.ldouble):
        fn = _mk_add_42(llvm_module, ty)
    return llvm_module

# ______________________________________________________________________

def test_wrap_module (arg = None):
    # Build up a module.
    m = build_test_module()
    if arg and arg.lower() == 'separated':
        wrap_module = NoBitey().wrap_llvm_module_in_python(m)
    else:
        wrap_module = NoBitey(m).wrap_llvm_module_in_python(m)
    # Now try running the generated wrappers.
    for py_wf_name in ('add_42_i32', 'add_42_i64', 'add_42_float',
                       'add_42_double'):
        py_wf = getattr(wrap_module, py_wf_name)
        for i in range(42):
            result = py_wf(i)
            expected = i + 42
            assert result == expected, "%r != %r in %r" % (
                result, expected, py_wf)
    return wrap_module

# ______________________________________________________________________

def main (*args):
    if args:
        for arg in args:
            test_wrap_module(arg)
    else:
        test_wrap_module()

if __name__ == "__main__":
    main(*sys.argv[1:])

# ______________________________________________________________________
# End of nobitey.py

########NEW FILE########
__FILENAME__ = opcode_util
# ______________________________________________________________________

import dis
import opcode

# ______________________________________________________________________
# Module data

hasjump = opcode.hasjrel + opcode.hasjabs
hascbranch = [op for op in hasjump
              if 'IF' in opcode.opname[op]
              or opcode.opname[op] in ('FOR_ITER', 'SETUP_LOOP')]

# Since the actual opcode value may change, manage opcode abstraction
# data by opcode name.

OPCODE_MAP = {
    'BINARY_ADD': (2, 1, None),
    'BINARY_AND': (2, 1, None),
    'BINARY_DIVIDE': (2, 1, None),
    'BINARY_FLOOR_DIVIDE': (2, 1, None),
    'BINARY_LSHIFT': (2, 1, None),
    'BINARY_MODULO': (2, 1, None),
    'BINARY_MULTIPLY': (2, 1, None),
    'BINARY_OR': (2, 1, None),
    'BINARY_POWER': (2, 1, None),
    'BINARY_RSHIFT': (2, 1, None),
    'BINARY_SUBSCR': (2, 1, None),
    'BINARY_SUBTRACT': (2, 1, None),
    'BINARY_TRUE_DIVIDE': (2, 1, None),
    'BINARY_XOR': (2, 1, None),
    'BREAK_LOOP': (0, None, 1),
    'BUILD_CLASS': (None, None, None),
    'BUILD_LIST': (-1, 1, None),
    'BUILD_MAP': (None, None, None),
    'BUILD_SET': (None, None, None),
    'BUILD_SLICE': (None, None, None),
    'BUILD_TUPLE': (-1, 1, None),
    'CALL_FUNCTION': (-2, 1, None),
    'CALL_FUNCTION_KW': (-3, 1, None),
    'CALL_FUNCTION_VAR': (-3, 1, None),
    'CALL_FUNCTION_VAR_KW': (-4, 1, None),
    'COMPARE_OP': (2, 1, None),
    'CONTINUE_LOOP': (None, None, None),
    'DELETE_ATTR': (1, None, 1),
    'DELETE_DEREF': (None, None, None),
    'DELETE_FAST': (0, None, 1),
    'DELETE_GLOBAL': (0, None, 1),
    'DELETE_NAME': (0, None, 1),
    'DELETE_SLICE+0': (1, None, 1),
    'DELETE_SLICE+1': (2, None, 1),
    'DELETE_SLICE+2': (2, None, 1),
    'DELETE_SLICE+3': (3, None, 1),
    'DELETE_SUBSCR': (2, None, 1),
    'DUP_TOP': (None, None, None),
    'DUP_TOPX': (None, None, None),
    'DUP_TOP_TWO': (None, None, None),
    'END_FINALLY': (None, None, None),
    'EXEC_STMT': (None, None, None),
    'EXTENDED_ARG': (None, None, None),
    'FOR_ITER': (1, 1, 1),
    'GET_ITER': (1, 1, None),
    'IMPORT_FROM': (None, None, None),
    'IMPORT_NAME': (None, None, None),
    'IMPORT_STAR': (1, None, 1),
    'INPLACE_ADD': (2, 1, None),
    'INPLACE_AND': (2, 1, None),
    'INPLACE_DIVIDE': (2, 1, None),
    'INPLACE_FLOOR_DIVIDE': (2, 1, None),
    'INPLACE_LSHIFT': (2, 1, None),
    'INPLACE_MODULO': (2, 1, None),
    'INPLACE_MULTIPLY': (2, 1, None),
    'INPLACE_OR': (2, 1, None),
    'INPLACE_POWER': (2, 1, None),
    'INPLACE_RSHIFT': (2, 1, None),
    'INPLACE_SUBTRACT': (2, 1, None),
    'INPLACE_TRUE_DIVIDE': (2, 1, None),
    'INPLACE_XOR': (2, 1, None),
    'JUMP_ABSOLUTE': (0, None, 1),
    'JUMP_FORWARD': (0, None, 1),
    'JUMP_IF_FALSE': (1, 1, 1),
    'JUMP_IF_FALSE_OR_POP': (None, None, None),
    'JUMP_IF_TRUE': (1, 1, 1),
    'JUMP_IF_TRUE_OR_POP': (None, None, None),
    'LIST_APPEND': (2, 0, 1),
    'LOAD_ATTR': (1, 1, None),
    'LOAD_BUILD_CLASS': (None, None, None),
    'LOAD_CLOSURE': (None, None, None),
    'LOAD_CONST': (0, 1, None),
    'LOAD_DEREF': (0, 1, None),
    'LOAD_FAST': (0, 1, None),
    'LOAD_GLOBAL': (0, 1, None),
    'LOAD_LOCALS': (None, None, None),
    'LOAD_NAME': (0, 1, None),
    'MAKE_CLOSURE': (None, None, None),
    'MAKE_FUNCTION': (-2, 1, None),
    'MAP_ADD': (None, None, None),
    'NOP': (0, None, None),
    'POP_BLOCK': (0, None, 1),
    'POP_EXCEPT': (None, None, None),
    'POP_JUMP_IF_FALSE': (1, None, 1),
    'POP_JUMP_IF_TRUE': (1, None, 1),
    'POP_TOP': (1, None, 1),
    'PRINT_EXPR': (1, None, 1),
    'PRINT_ITEM': (1, None, 1),
    'PRINT_ITEM_TO': (2, None, 1),
    'PRINT_NEWLINE': (0, None, 1),
    'PRINT_NEWLINE_TO': (1, None, 1),
    'RAISE_VARARGS': (None, None, None),
    'RETURN_VALUE': (1, None, 1),
    'ROT_FOUR': (None, None, None),
    'ROT_THREE': (None, None, None),
    'ROT_TWO': (None, None, None),
    'SETUP_EXCEPT': (None, None, None),
    'SETUP_FINALLY': (None, None, None),
    'SETUP_LOOP': (None, None, None),
    'SETUP_WITH': (None, None, None),
    'SET_ADD': (None, None, None),
    'SLICE+0': (1, 1, None),
    'SLICE+1': (2, 1, None),
    'SLICE+2': (2, 1, None),
    'SLICE+3': (3, 1, None),
    'STOP_CODE': (None, None, None),
    'STORE_ATTR': (2, None, 1),
    'STORE_DEREF': (1, 0, 1),
    'STORE_FAST': (1, None, 1),
    'STORE_GLOBAL': (1, None, 1),
    'STORE_LOCALS': (None, None, None),
    'STORE_MAP': (1, None, 1),
    'STORE_NAME': (1, None, 1),
    'STORE_SLICE+0': (1, None, 1),
    'STORE_SLICE+1': (2, None, 1),
    'STORE_SLICE+2': (2, None, 1),
    'STORE_SLICE+3': (3, None, 1),
    'STORE_SUBSCR': (3, None, 1),
    'UNARY_CONVERT': (1, 1, None),
    'UNARY_INVERT': (1, 1, None),
    'UNARY_NEGATIVE': (1, 1, None),
    'UNARY_NOT': (1, 1, None),
    'UNARY_POSITIVE': (1, 1, None),
    'UNPACK_EX': (None, None, None),
    'UNPACK_SEQUENCE': (None, None, None),
    'WITH_CLEANUP': (None, None, None),
    'YIELD_VALUE': (1, None, 1),
}

# ______________________________________________________________________
# Module functions

def itercode(code, start = 0):
    """Return a generator of byte-offset, opcode, and argument
    from a byte-code-string
    """
    i = 0
    extended_arg = 0
    if isinstance(code[0], str):
        code = [ord(c) for c in code]
    n = len(code)
    while i < n:
        op = code[i]
        num = i + start
        i = i + 1
        oparg = None
        if op >= opcode.HAVE_ARGUMENT:
            oparg = code[i] + (code[i + 1] * 256) + extended_arg
            extended_arg = 0
            i = i + 2
            if op == opcode.EXTENDED_ARG:
                extended_arg = oparg * 65536

        delta = yield num, op, oparg
        if delta is not None:
            abs_rel, dst = delta
            assert abs_rel == 'abs' or abs_rel == 'rel'
            i = dst if abs_rel == 'abs' else i + dst

# ______________________________________________________________________

def extendlabels(code, labels = None):
    """Extend the set of jump target labels to account for the
    passthrough targets of conditional branches.

    This allows us to create a control flow graph where there is at
    most one branch per basic block.
    """
    if labels is None:
        labels = []
    if isinstance(code[0], str):
        code = [ord(c) for c in code]
    n = len(code)
    i = 0
    while i < n:
        op = code[i]
        i += 1
        if op >= dis.HAVE_ARGUMENT:
            i += 2
            label = -1
            if op in hasjump:
                label = i
            if label >= 0:
                if label not in labels:
                    labels.append(label)
        elif op == opcode.opmap['BREAK_LOOP']:
            if i not in labels:
                labels.append(i)
    return labels

# ______________________________________________________________________

def get_code_object (func):
    return getattr(func, '__code__', getattr(func, 'func_code', None))

# ______________________________________________________________________

def build_basic_blocks (co_obj):
    co_code = co_obj.co_code
    labels = extendlabels(co_code, dis.findlabels(co_code))
    labels.sort()
    blocks = dict((index, list(itercode(co_code[index:next_index], index)))
                  for index, next_index in zip([0] + labels,
                                               labels + [len(co_code)]))
    return blocks

# ______________________________________________________________________
# End of opcode_util.py

########NEW FILE########
__FILENAME__ = phi_injector
# ______________________________________________________________________

from .bytecode_visitor import BytecodeFlowVisitor, BenignBytecodeVisitorMixin

# ______________________________________________________________________

synthetic_opname = []
synthetic_opmap = {}

def def_synth_op (opname):
    global synthetic_opname, synthetic_opmap
    ret_val = -(len(synthetic_opname) + 1)
    synthetic_opname.insert(0, opname)
    synthetic_opmap[opname] = ret_val
    return ret_val

REF_ARG = def_synth_op('REF_ARG')
BUILD_PHI = def_synth_op('BUILD_PHI')
DEFINITION = def_synth_op('DEFINITION')
REF_DEF = def_synth_op('REF_DEF')

# ______________________________________________________________________

class PhiInjector (BenignBytecodeVisitorMixin, BytecodeFlowVisitor):
    '''Transformer responsible for modifying a bytecode flow, removing
    LOAD_FAST and STORE_FAST opcodes, and replacing them with a static
    single assignment (SSA) representation.

    In order to support SSA, PhiInjector adds the following synthetic
    opcodes to transformed flows:

      * REF_ARG: Specifically reference an incomming argument value.

      * BUILD_PHI: Build a phi node to disambiguate between several
        possible definitions at a control flow join.

      * DEFINITION: Unique value definition indexed by the "arg" field
        in the tuple.

      * REF_DEF: Reference a specific value definition.'''

    def visit_cfg (self, cfg, nargs = 0, *args, **kws):
        self.cfg = cfg
        ret_val = self.visit(cfg.blocks, nargs)
        del self.cfg
        return ret_val

    def visit (self, flow, nargs = 0, *args, **kws):
        self.nargs = nargs
        self.definitions = []
        self.phis = []
        self.prev_blocks = []
        self.blocks_locals = dict((block, {})
                                  for block in self.cfg.blocks.keys())
        ret_val = super(PhiInjector, self).visit(flow, *args, **kws)
        for block, _, _, args, _ in self.phis:
            local = args.pop()
            reaching_definitions = self.cfg.reaching_definitions[block]
            for prev in reaching_definitions.keys():
                if 0 in self.cfg.blocks_reaching[prev]:
                    args.append((prev, REF_DEF, 'REF_DEF',
                                 self.blocks_locals[prev][local], ()))
            args.sort()
        del self.blocks_locals
        del self.prev_blocks
        del self.phis
        del self.definitions
        del self.nargs
        return ret_val

    def add_definition (self, index, local, arg):
        definition_index = len(self.definitions)
        definition = (index, DEFINITION, 'DEFINITION', definition_index,
                      (arg,))
        self.definitions.append(definition)
        self.blocks_locals[self.block][local] = definition_index
        return definition

    def add_phi (self, index, local):
        ret_val = (index, BUILD_PHI, 'BUILD_PHI', [local], ())
        self.phis.append(ret_val)
        return ret_val

    def enter_block (self, block):
        ret_val = False
        self.block = block
        if block == 0:
            if self.nargs > 0:
                ret_val = [self.add_definition(-1, arg,
                                                (-1, REF_ARG, 'REF_ARG', arg,
                                                  ()))
                           for arg in range(self.nargs)]
            else:
                ret_val = True
        elif 0 in self.cfg.blocks_reaching[block]:
            ret_val = True
            prev_block_locals = None
            for pred_block in self.cfg.blocks_in[block]:
                if pred_block in self.prev_blocks:
                    prev_block_locals = self.blocks_locals[pred_block]
                    break
            assert prev_block_locals is not None, "Internal translation error"
            self.blocks_locals[block] = prev_block_locals.copy()
            phis_needed = self.cfg.phi_needed(block)
            if phis_needed:
                ret_val = [self.add_definition(block, local,
                                               self.add_phi(block, local))
                           for local in phis_needed]
        return ret_val

    def exit_block (self, block):
        if 0 in self.cfg.blocks_reaching[block]:
            self.prev_blocks.append(block)
        del self.block

    def op_STORE_FAST (self, i, op, arg, *args, **kws):
        assert len(args) == 1
        return [self.add_definition(i, arg, args[0])]

    def op_LOAD_FAST (self, i, op, arg, *args, **kws):
        return [(i, REF_DEF, 'REF_DEF', self.blocks_locals[self.block][arg],
                 args)]

# ______________________________________________________________________

def inject_phis (func):
    '''Given a Python function, return a bytecode flow object that has
    been transformed by a fresh PhiInjector instance.'''
    import byte_control, byte_flow
    argcount = byte_control.opcode_util.get_code_object(func).co_argcount
    cfg = byte_control.build_cfg(func)
    cfg.blocks = byte_flow.BytecodeFlowBuilder().visit_cfg(cfg)
    return PhiInjector().visit_cfg(cfg, argcount)

# ______________________________________________________________________
# Main (self-test) routine

def main (*args):
    import pprint
    from tests import llfuncs
    if not args:
        args = ('doslice',)
    for arg in args:
        pprint.pprint(inject_phis(getattr(llfuncs, arg)))

# ______________________________________________________________________

if __name__ == "__main__":
    import sys
    main(*sys.argv[1:])

# ______________________________________________________________________
# End of phi_injector.py

########NEW FILE########
__FILENAME__ = pyaddfunc
# ______________________________________________________________________

import ctypes

# ______________________________________________________________________
class PyMethodDef (ctypes.Structure):
    _fields_ = [
        ('ml_name', ctypes.c_char_p),
        ('ml_meth', ctypes.c_void_p),
        ('ml_flags', ctypes.c_int),
        ('ml_doc', ctypes.c_char_p),
        ]

PyCFunction_NewEx = ctypes.pythonapi.PyCFunction_NewEx
PyCFunction_NewEx.argtypes = (ctypes.POINTER(PyMethodDef),
                              ctypes.c_void_p,
                              ctypes.c_void_p)
PyCFunction_NewEx.restype = ctypes.py_object

cache = {} # Unsure if this is necessary to keep the PyMethodDef
           # structures from being garbage collected.  Assuming so...

def pyaddfunc (func_name, func_ptr, func_doc = None):
    global cache
    if bytes != str:
        func_name = bytes(ord(ch) for ch in func_name)
    key = (func_name, func_ptr)
    if key in cache:
        _, ret_val = cache[key]
    else:
        mdef = PyMethodDef(bytes(func_name),
                           func_ptr,
                           1, # == METH_VARARGS (hopefully remains so...)
                           func_doc)
        ret_val = PyCFunction_NewEx(ctypes.byref(mdef), 0, 0)
        cache[key] = (mdef, ret_val)
    return ret_val

# ______________________________________________________________________
# End of pyaddfunc.py

########NEW FILE########
__FILENAME__ = llfuncs
# ______________________________________________________________________

def doslice (in_string, lower, upper):
    l = strlen(in_string)
    if lower < lc_size_t(0):
        lower += l
    if upper < lc_size_t(0):
        upper += l
    temp_len = upper - lower
    if temp_len < lc_size_t(0):
        temp_len = lc_size_t(0)
    ret_val = alloca_array(li8, temp_len + lc_size_t(1))
    strncpy(ret_val, in_string + lower, temp_len)
    ret_val[temp_len] = li8(0)
    return ret_val

def ipow (val, exp):
    ret_val = 1
    temp = val
    w = exp
    while w > 0:
        if (w & 1) != 0:
            ret_val *= temp
            # TODO: Overflow check on ret_val
        w >>= 1
        if w == 0: break
        temp *= temp
        # TODO: Overflow check on temp
    return ret_val

def pymod (arg1, arg2):
    ret_val = arg1 % arg2
    if ret_val < 0:
        if arg2 > 0:
            ret_val += arg2
    elif arg2 < 0:
        ret_val += arg2
    return ret_val

# ______________________________________________________________________
# End of llfuncs.py

########NEW FILE########
__FILENAME__ = llfunctys
# ______________________________________________________________________

import llvm.core as lc

from llpython import bytetype

# ______________________________________________________________________

doslice = lc.Type.function(bytetype.li8_ptr, (
        bytetype.li8_ptr, bytetype.lc_size_t, bytetype.lc_size_t))

ipow = lc.Type.function(bytetype.li32, (bytetype.li32,
                                        bytetype.li32))

pymod = lc.Type.function(bytetype.li32, (bytetype.li32,
                                         bytetype.li32))

# ______________________________________________________________________
# End of llfunctys.py

########NEW FILE########
__FILENAME__ = test_sdivmod64
import math
import os
import subprocess
udt = os.path.join('.', 'test_sdivmod64.run')

def testcase(dividend, divisor):
    print 'divmod64(%d, %d)' % (dividend, divisor)

    procargs = ('%s %s %s' % (udt, dividend, divisor)).split()
    result = subprocess.check_output(procargs)
    gotQ, gotR = map(int, result.splitlines())

    expectQ = dividend // divisor
    expectR = dividend % divisor

    print 'Q = %d, R = %d' % (gotQ, gotR)

    if expectQ != gotQ:
        raise ValueError("invalid quotient: got=%d but expect=%d" %
                         (gotQ, expectQ))
    if expectR != gotR:
        raise ValueError("invalid remainder: got=%d but expect=%d" %
                         (gotR, expectR))
    print 'OK'

def testsequence():
    subjects = [
        (0, 1),
        (0, 0xffffffff),
        (1, 2),
        (1, 983219),
        (2, 2),
        (3, 2),
        (1024, 2),
        (2048, 512),
        (21321, 512),
        (9329189, 1031),
        (0xffffffff, 2),
        (0xffffffff, 0xffff),
        (0x1ffffffff, 2),
        (0x1ffffffff, 0xffff),
        (0xffff, 0xffffffff),
        (0x0fffffffffffffff, 0xffff),
        (0x7fffffffffffffff, 0x7fffffffffffffff),
        (0x7fffffffffffffff, 0x7ffffffffffffff0),
        (0x7fffffffffffffff, 87655678587161901),
    ]

    for dvd, dvr in subjects:
        testcase(dvd, dvr)
        testcase(dvd, -dvr)
        testcase(-dvd, dvr)
        testcase(-dvd, -dvr)

if __name__ == '__main__':
    testsequence()

########NEW FILE########
__FILENAME__ = test_udivmod64
import math
import os
import subprocess
udt = os.path.join('.', 'test_udivmod64.run')

def testcase(dividend, divisor):
    print 'divmod64(%d, %d)' % (dividend, divisor)

    procargs = ('%s %s %s' % (udt, dividend, divisor)).split()
    result = subprocess.check_output(procargs)
    gotQ, gotR = map(int, result.splitlines())

    expectQ = dividend // divisor
    expectR = dividend % divisor

    print 'Q = %d, R = %d' % (gotQ, gotR)

    if expectQ != gotQ:
        raise ValueError("invalid quotient: got=%d but expect=%d" %
                         (gotQ, expectQ))
    if expectR != gotR:
        raise ValueError("invalid remainder: got=%d but expect=%d" %
                         (gotR, expectR))
    print 'OK'

def testsequence():
    subjects = [
        (0, 1),
        (0, 0xffffffffffffffff),
        (1, 2),
        (1, 983219),
        (2, 2),
        (3, 2),
        (1024, 2),
        (2048, 512),
        (21321, 512),
        (9329189, 1031),
        (0xffffffff, 2),
        (0xffffffff, 0xffff),
        (0x1ffffffff, 2),
        (0x1ffffffff, 0xffff),
        (0xffff, 0xffffffff),
        (0xffffffffffffffff, 0xffff),
        (0xffffffffffffffff, 0x7fffffffffffffff),
        (0xffffffffffffffff, 0xfffffffffffffff0),
        (0xffffffffffffffff, 87655678587161901),
    ]

    for dvd, dvr in subjects:
        testcase(dvd, dvr)

if __name__ == '__main__':
    testsequence()

########NEW FILE########
__FILENAME__ = striptriple
import sys
import re

buf = []
with open(sys.argv[1], 'r') as fin:
    tripleline = re.compile('^target\s+triple\s+=\s+')
    for line in fin.readlines():
        if not tripleline.match(line):
            buf.append(line)

with open(sys.argv[1], 'w') as fout:
    for line in buf:
        fout.write(line)



########NEW FILE########
__FILENAME__ = core
#
# Copyright (c) 2008-10, Mahadevan R All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#  * Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
#
#  * Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
#  * Neither the name of this software, nor the names of its
#    contributors may be used to endorse or promote products derived from
#    this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#

from io import BytesIO
try:
    from StringIO import StringIO
except ImportError:
    try:
        from cStringIO import StringIO
    except ImportError:
        from io import StringIO

import contextlib, weakref

import llvm
from llvm._intrinsic_ids import *
from llvm.deprecated import deprecated
from llvmpy import api

#===----------------------------------------------------------------------===
# Enumerations
#===----------------------------------------------------------------------===
class Enum(int):
    '''Overload integer to print the name of the enum.
    '''
    def __repr__(self):
        return '%s(%d)' % (type(self).__name__, self)

    @classmethod
    def declare(cls):
        declared = cls._declared_ = {}
        scope = globals()
        for name in filter(lambda s: s.startswith(cls.prefix), dir(cls)):
            n = getattr(cls, name)
            typ = type(name, (cls,), {})
            obj = typ(n)
            declared[n] = obj
            scope[name] = obj

    @classmethod
    def get(cls, num):
        return cls._declared_[num]

# type id (llvm::Type::TypeID)
class TypeEnum(Enum):
    prefix = 'TYPE_'
    TypeID = api.llvm.Type.TypeID

    TYPE_VOID       = TypeID.VoidTyID
    TYPE_HALF       = TypeID.HalfTyID
    TYPE_FLOAT      = TypeID.FloatTyID
    TYPE_DOUBLE     = TypeID.DoubleTyID
    TYPE_X86_FP80   = TypeID.X86_FP80TyID
    TYPE_FP128      = TypeID.FP128TyID
    TYPE_PPC_FP128  = TypeID.PPC_FP128TyID
    TYPE_LABEL      = TypeID.LabelTyID
    TYPE_INTEGER    = TypeID.IntegerTyID
    TYPE_FUNCTION   = TypeID.FunctionTyID
    TYPE_STRUCT     = TypeID.StructTyID
    TYPE_ARRAY      = TypeID.ArrayTyID
    TYPE_POINTER    = TypeID.PointerTyID
    TYPE_VECTOR     = TypeID.VectorTyID
    TYPE_METADATA   = TypeID.MetadataTyID
    TYPE_X86_MMX    = TypeID.X86_MMXTyID

TypeEnum.declare()


# value IDs (llvm::Value::ValueTy enum)
# According to the doxygen docs, it is not a good idea to use these enums.
# There are more values than those declared.
class ValueEnum(Enum):
    prefix = 'VALUE_'
    ValueTy = api.llvm.Value.ValueTy

    VALUE_ARGUMENT                          = ValueTy.ArgumentVal
    VALUE_BASIC_BLOCK                       = ValueTy.BasicBlockVal
    VALUE_FUNCTION                          = ValueTy.FunctionVal
    VALUE_GLOBAL_ALIAS                      = ValueTy.GlobalAliasVal
    VALUE_GLOBAL_VARIABLE                   = ValueTy.GlobalVariableVal
    VALUE_UNDEF_VALUE                       = ValueTy.UndefValueVal
    VALUE_BLOCK_ADDRESS                     = ValueTy.BlockAddressVal
    VALUE_CONSTANT_EXPR                     = ValueTy.ConstantExprVal
    VALUE_CONSTANT_AGGREGATE_ZERO           = ValueTy.ConstantAggregateZeroVal
    VALUE_CONSTANT_DATA_ARRAY               = ValueTy.ConstantDataArrayVal
    VALUE_CONSTANT_DATA_VECTOR              = ValueTy.ConstantDataVectorVal
    VALUE_CONSTANT_INT                      = ValueTy.ConstantIntVal
    VALUE_CONSTANT_FP                       = ValueTy.ConstantFPVal
    VALUE_CONSTANT_ARRAY                    = ValueTy.ConstantArrayVal
    VALUE_CONSTANT_STRUCT                   = ValueTy.ConstantStructVal
    VALUE_CONSTANT_VECTOR                   = ValueTy.ConstantVectorVal
    VALUE_CONSTANT_POINTER_NULL             = ValueTy.ConstantPointerNullVal
    VALUE_MD_NODE                           = ValueTy.MDNodeVal
    VALUE_MD_STRING                         = ValueTy.MDStringVal
    VALUE_INLINE_ASM                        = ValueTy.InlineAsmVal
    VALUE_PSEUDO_SOURCE_VALUE               = ValueTy.PseudoSourceValueVal
    VALUE_FIXED_STACK_PSEUDO_SOURCE_VALUE   = ValueTy.FixedStackPseudoSourceValueVal
    VALUE_INSTRUCTION                       = ValueTy.InstructionVal

ValueEnum.declare()

# instruction opcodes (from include/llvm/Instruction.def)
class OpcodeEnum(Enum):
    prefix = 'OPCODE_'

    OPCODE_RET            = 1
    OPCODE_BR             = 2
    OPCODE_SWITCH         = 3
    OPCODE_INDIRECT_BR    = 4
    OPCODE_INVOKE         = 5
    OPCODE_RESUME         = 6
    OPCODE_UNREACHABLE    = 7
    OPCODE_ADD            = 8
    OPCODE_FADD           = 9
    OPCODE_SUB            = 10
    OPCODE_FSUB           = 11
    OPCODE_MUL            = 12
    OPCODE_FMUL           = 13
    OPCODE_UDIV           = 14
    OPCODE_SDIV           = 15
    OPCODE_FDIV           = 16
    OPCODE_UREM           = 17
    OPCODE_SREM           = 18
    OPCODE_FREM           = 19
    OPCODE_SHL            = 20
    OPCODE_LSHR           = 21
    OPCODE_ASHR           = 22
    OPCODE_AND            = 23
    OPCODE_OR             = 24
    OPCODE_XOR            = 25
    OPCODE_ALLOCA         = 26
    OPCODE_LOAD           = 27
    OPCODE_STORE          = 28
    OPCODE_GETELEMENTPTR  = 29
    OPCODE_FENCE          = 30
    OPCODE_ATOMICCMPXCHG  = 31
    OPCODE_ATOMICRMW      = 32
    OPCODE_TRUNC          = 33
    OPCODE_ZEXT           = 34
    OPCODE_SEXT           = 35
    OPCODE_FPTOUI         = 36
    OPCODE_FPTOSI         = 37
    OPCODE_UITOFP         = 38
    OPCODE_SITOFP         = 39
    OPCODE_FPTRUNC        = 40
    OPCODE_FPEXT          = 41
    OPCODE_PTRTOINT       = 42
    OPCODE_INTTOPTR       = 43
    OPCODE_BITCAST        = 44
    OPCODE_ICMP           = 45
    OPCODE_FCMP           = 46
    OPCODE_PHI            = 47
    OPCODE_CALL           = 48
    OPCODE_SELECT         = 49
    OPCODE_USEROP1        = 50
    OPCODE_USEROP2        = 51
    OPCODE_VAARG          = 52
    OPCODE_EXTRACTELEMENT = 53
    OPCODE_INSERTELEMENT  = 54
    OPCODE_SHUFFLEVECTOR  = 55
    OPCODE_EXTRACTVALUE   = 56
    OPCODE_INSERTVALUE    = 57
    OPCODE_LANDINGPAD     = 58

OpcodeEnum.declare()

# calling conventions

class CCEnum(Enum):
    prefix = 'CC_'

    ID = api.llvm.CallingConv.ID

    CC_C             = ID.C
    CC_FASTCALL      = ID.Fast
    CC_COLDCALL      = ID.Cold
    CC_GHC           = ID.GHC
    CC_X86_STDCALL   = ID.X86_StdCall
    CC_X86_FASTCALL  = ID.X86_FastCall
    CC_ARM_APCS      = ID.ARM_APCS
    CC_ARM_AAPCS     = ID.ARM_AAPCS
    CC_ARM_AAPCS_VFP = ID.ARM_AAPCS_VFP
    CC_MSP430_INTR   = ID.MSP430_INTR
    CC_X86_THISCALL  = ID.X86_ThisCall
    CC_PTX_KERNEL    = ID.PTX_Kernel
    CC_PTX_DEVICE    = ID.PTX_Device

    if llvm.version <= (3, 3):
        CC_MBLAZE_INTR   = ID.MBLAZE_INTR
        CC_MBLAZE_SVOL   = ID.MBLAZE_SVOL

CCEnum.declare()

# int predicates
class ICMPEnum(Enum):
    prefix = 'ICMP_'

    Predicate = api.llvm.CmpInst.Predicate

    ICMP_EQ         = Predicate.ICMP_EQ
    ICMP_NE         = Predicate.ICMP_NE
    ICMP_UGT        = Predicate.ICMP_UGT
    ICMP_UGE        = Predicate.ICMP_UGE
    ICMP_ULT        = Predicate.ICMP_ULT
    ICMP_ULE        = Predicate.ICMP_ULE
    ICMP_SGT        = Predicate.ICMP_SGT
    ICMP_SGE        = Predicate.ICMP_SGE
    ICMP_SLT        = Predicate.ICMP_SLT
    ICMP_SLE        = Predicate.ICMP_SLE

ICMPEnum.declare()
# same as ICMP_xx, for backward compatibility

IPRED_EQ        = ICMP_EQ
IPRED_NE        = ICMP_NE
IPRED_UGT       = ICMP_UGT
IPRED_UGE       = ICMP_UGE
IPRED_ULT       = ICMP_ULT
IPRED_ULE       = ICMP_ULE
IPRED_SGT       = ICMP_SGT
IPRED_SGE       = ICMP_SGE
IPRED_SLT       = ICMP_SLT
IPRED_SLE       = ICMP_SLE

# real predicates

class FCMPEnum(Enum):
    prefix = 'FCMP_'

    Predicate = api.llvm.CmpInst.Predicate

    FCMP_FALSE      = Predicate.FCMP_FALSE
    FCMP_OEQ        = Predicate.FCMP_OEQ
    FCMP_OGT        = Predicate.FCMP_OGT
    FCMP_OGE        = Predicate.FCMP_OGE
    FCMP_OLT        = Predicate.FCMP_OLT
    FCMP_OLE        = Predicate.FCMP_OLE
    FCMP_ONE        = Predicate.FCMP_ONE
    FCMP_ORD        = Predicate.FCMP_ORD
    FCMP_UNO        = Predicate.FCMP_UNO
    FCMP_UEQ        = Predicate.FCMP_UEQ
    FCMP_UGT        = Predicate.FCMP_UGT
    FCMP_UGE        = Predicate.FCMP_UGE
    FCMP_ULT        = Predicate.FCMP_ULT
    FCMP_ULE        = Predicate.FCMP_ULE
    FCMP_UNE        = Predicate.FCMP_UNE
    FCMP_TRUE       = Predicate.FCMP_TRUE

FCMPEnum.declare()

# real predicates

RPRED_FALSE     = FCMP_FALSE
RPRED_OEQ       = FCMP_OEQ
RPRED_OGT       = FCMP_OGT
RPRED_OGE       = FCMP_OGE
RPRED_OLT       = FCMP_OLT
RPRED_OLE       = FCMP_OLE
RPRED_ONE       = FCMP_ONE
RPRED_ORD       = FCMP_ORD
RPRED_UNO       = FCMP_UNO
RPRED_UEQ       = FCMP_UEQ
RPRED_UGT       = FCMP_UGT
RPRED_UGE       = FCMP_UGE
RPRED_ULT       = FCMP_ULT
RPRED_ULE       = FCMP_ULE
RPRED_UNE       = FCMP_UNE
RPRED_TRUE      = FCMP_TRUE

# linkages (see llvm::GlobalValue::LinkageTypes)
class LinkageEnum(Enum):
    prefix = 'LINKAGE_'
    LinkageTypes = api.llvm.GlobalValue.LinkageTypes

    LINKAGE_EXTERNAL                =  LinkageTypes.ExternalLinkage
    LINKAGE_AVAILABLE_EXTERNALLY    =  LinkageTypes.AvailableExternallyLinkage
    LINKAGE_LINKONCE_ANY            =  LinkageTypes.LinkOnceAnyLinkage
    LINKAGE_LINKONCE_ODR            =  LinkageTypes.LinkOnceODRLinkage
    LINKAGE_WEAK_ANY                =  LinkageTypes.WeakAnyLinkage
    LINKAGE_WEAK_ODR                =  LinkageTypes.WeakODRLinkage
    LINKAGE_APPENDING               =  LinkageTypes.AppendingLinkage
    LINKAGE_INTERNAL                =  LinkageTypes.InternalLinkage
    LINKAGE_PRIVATE                 =  LinkageTypes.PrivateLinkage
    LINKAGE_DLLIMPORT               =  LinkageTypes.DLLImportLinkage
    LINKAGE_DLLEXPORT               =  LinkageTypes.DLLExportLinkage
    LINKAGE_EXTERNAL_WEAK           =  LinkageTypes.ExternalWeakLinkage
    LINKAGE_COMMON                  =  LinkageTypes.CommonLinkage
    LINKAGE_LINKER_PRIVATE          =  LinkageTypes.LinkerPrivateLinkage
    LINKAGE_LINKER_PRIVATE_WEAK     =  LinkageTypes.LinkerPrivateWeakLinkage

LinkageEnum.declare()

# visibility (see llvm/GlobalValue.h)
class VisibilityEnum(Enum):
    prefix = 'VISIBILITY_'

    VISIBILITY_DEFAULT   = api.llvm.GlobalValue.VisibilityTypes.DefaultVisibility
    VISIBILITY_HIDDEN    = api.llvm.GlobalValue.VisibilityTypes.HiddenVisibility
    VISIBILITY_PROTECTED = api.llvm.GlobalValue.VisibilityTypes.ProtectedVisibility

VisibilityEnum.declare()

# parameter attributes
#      LLVM 3.2 llvm::Attributes::AttrVal (see llvm/Attributes.h)
#      LLVM 3.3 llvm::Attribute::AttrKind (see llvm/Attributes.h)
class AttrEnum(Enum):
    prefix = 'ATTR_'

    if llvm.version >= (3, 3):
        AttrVal = api.llvm.Attribute.AttrKind
    else:
        AttrVal = api.llvm.Attributes.AttrVal

    ATTR_NONE               = AttrVal.None_
    ATTR_ZEXT               = AttrVal.ZExt
    ATTR_SEXT               = AttrVal.SExt
    ATTR_NO_RETURN          = AttrVal.NoReturn
    ATTR_IN_REG             = AttrVal.InReg
    ATTR_STRUCT_RET         = AttrVal.StructRet
    ATTR_NO_UNWIND          = AttrVal.NoUnwind
    ATTR_NO_ALIAS           = AttrVal.NoAlias
    ATTR_BY_VAL             = AttrVal.ByVal
    ATTR_NEST               = AttrVal.Nest
    ATTR_READ_NONE          = AttrVal.ReadNone
    ATTR_READONLY           = AttrVal.ReadOnly
    ATTR_NO_INLINE          = AttrVal.NoInline
    ATTR_ALWAYS_INLINE      = AttrVal.AlwaysInline
    ATTR_OPTIMIZE_FOR_SIZE  = AttrVal.OptimizeForSize
    ATTR_STACK_PROTECT      = AttrVal.StackProtect
    ATTR_STACK_PROTECT_REQ  = AttrVal.StackProtectReq
    ATTR_ALIGNMENT          = AttrVal.Alignment
    ATTR_NO_CAPTURE         = AttrVal.NoCapture
    ATTR_NO_REDZONE         = AttrVal.NoRedZone
    ATTR_NO_IMPLICIT_FLOAT  = AttrVal.NoImplicitFloat
    ATTR_NAKED              = AttrVal.Naked
    ATTR_INLINE_HINT        = AttrVal.InlineHint
    ATTR_STACK_ALIGNMENT    = AttrVal.StackAlignment

AttrEnum.declare()

class Module(llvm.Wrapper):
    """A Module instance stores all the information related to an LLVM module.

    Modules are the top level container of all other LLVM Intermediate
    Representation (IR) objects. Each module directly contains a list of
    globals variables, a list of functions, a list of libraries (or
    other modules) this module depends on, a symbol table, and various
    data about the target's characteristics.

    Construct a Module only using the static methods defined below, *NOT*
    using the constructor. A correct usage is:

    module_obj = Module.new('my_module')
    """
    __slots__ = '__weakref__'
    __cache = weakref.WeakValueDictionary()

    def __new__(cls, ptr):
        cached = cls.__cache.get(ptr)
        if cached:
            return cached
        obj = object.__new__(cls)
        cls.__cache[ptr] = obj
        return obj

    @staticmethod
    def new(id):
        """Create a new Module instance.

        Creates an instance of Module, having the id `id'.
        """
        context = api.llvm.getGlobalContext()
        m = api.llvm.Module.new(id, context)
        return Module(m)

    @staticmethod
    def from_bitcode(fileobj_or_str):
        """Create a Module instance from the contents of a bitcode
        file.

        fileobj_or_str -- takes a file-like object or string that contains
        a module represented in bitcode.
        """
        if isinstance(fileobj_or_str, bytes):
            bc = fileobj_or_str
        else:
            bc = fileobj_or_str.read()
        errbuf = BytesIO()
        context = api.llvm.getGlobalContext()
        m = api.llvm.ParseBitCodeFile(bc, context, errbuf)
        if not m:
            raise Exception(errbuf.getvalue())
        errbuf.close()
        return Module(m)


    @staticmethod
    def from_assembly(fileobj_or_str):
        """Create a Module instance from the contents of an LLVM
        assembly (.ll) file.


        fileobj_or_str -- takes a file-like object or string that contains
        a module represented in llvm-ir assembly.
        """
        if isinstance(fileobj_or_str, str):
            ir = fileobj_or_str
        else:
            ir = fileobj_or_str.read()
        errbuf = BytesIO()
        context = api.llvm.getGlobalContext()
        m = api.llvm.ParseAssemblyString(ir, None, api.llvm.SMDiagnostic.new(),
                                         context)
        errbuf.close()
        return Module(m)

    def __str__(self):
        """Text representation of a module.

            Returns the textual representation (`llvm assembly') of the
            module. Use it like this:

            ll = str(module_obj)
            print module_obj     # same as `print ll'
            """
        return str(self._ptr)

    def __hash__(self):
        return id(self._ptr)

    def __eq__(self, rhs):
        if isinstance(rhs, Module):
            return self._ptr == rhs._ptr

    def __ne__(self, rhs):
        return not (self == rhs)


    def _get_target(self):
        return self._ptr.getTargetTriple()

    def _set_target(self, value):
        return self._ptr.setTargetTriple(value)

    target = property(_get_target, _set_target,
              doc="The target triple string describing the target host.")


    def _get_data_layout(self):
        return self._ptr.getDataLayout()

    def _set_data_layout(self, value):
        return self._ptr.setDataLayout(value)

    data_layout = property(_get_data_layout, _set_data_layout,
           doc = """The data layout string for the module's target platform.

               The data layout strings is an encoded representation of
               the type sizes and alignments expected by this module.
               """
           )

    @property
    def pointer_size(self):
        return self._ptr.getPointerSize()

    def link_in(self, other, preserve=False):
        """Link the `other' module into this one.

        The `other' module is linked into this one such that types,
        global variables, function, etc. are matched and resolved.

        The `other' module is no longer valid after this method is
        invoked, all refs to it should be dropped.

        In the future, this API might be replaced with a full-fledged
        Linker class.
        """
        assert isinstance(other, Module)
        enum_mode = api.llvm.Linker.LinkerMode
        mode = enum_mode.PreserveSource if preserve else enum_mode.DestroySource

        with contextlib.closing(BytesIO()) as errmsg:
            failed = api.llvm.Linker.LinkModules(self._ptr,
                                                 other._ptr,
                                                 mode,
                                                 errmsg)
            if failed:
                raise llvm.LLVMException(errmsg.getvalue())

    def get_type_named(self, name):
        typ = self._ptr.getTypeByName(name)
        if typ:
            return StructType(typ)

    def add_global_variable(self, ty, name, addrspace=0):
        """Add a global variable of given type with given name."""
        external = api.llvm.GlobalVariable.LinkageTypes.ExternalLinkage
        notthreadlocal = api.llvm.GlobalVariable.ThreadLocalMode.NotThreadLocal
        init = None
        insertbefore = None
        ptr = api.llvm.GlobalVariable.new(self._ptr,
                                     ty._ptr,
                                     False,
                                     external,
                                     init,
                                     name,
                                     insertbefore,
                                     notthreadlocal,
                                     addrspace)
        return _make_value(ptr)

    def get_global_variable_named(self, name):
        """Return a GlobalVariable object for the given name."""
        ptr = self._ptr.getNamedGlobal(name)
        if ptr is None:
            raise llvm.LLVMException("No global named: %s" % name)
        return _make_value(ptr)

    @property
    def global_variables(self):
        return list(map(_make_value, self._ptr.list_globals()))

    def add_function(self, ty, name):
        """Add a function of given type with given name."""
        return Function.new(self, ty, name)
#        fn = self.get_function_named(name)
#        if fn is not None:
#            raise llvm.LLVMException("Duplicated function %s" % name)
#        return self.get_or_insert_function(ty, name)

    def get_function_named(self, name):
        """Return a Function object representing function with given name."""
        return Function.get(self, name)
#        fn = self._ptr.getFunction(name)
#        if fn is not None:
#            return _make_value(fn)

    def get_or_insert_function(self, ty, name):
        """Like get_function_named(), but does add_function() first, if
           function is not present."""
        return Function.get_or_insert(self, ty, name)
#        constant = self._ptr.getOrInsertFunction(name, ty._ptr)
#        try:
#            fn = constant._downcast(api.llvm.Function)
#        except ValueError:
#            # bitcasted to function type
#            return _make_value(constant)
#        else:
#            return _make_value(fn)

    @property
    def functions(self):
        """All functions in this module."""
        return list(map(_make_value, self._ptr.list_functions()))

    def verify(self):
        """Verify module.

            Checks module for errors. Raises `llvm.LLVMException' on any
            error."""
        action = api.llvm.VerifierFailureAction.ReturnStatusAction
        errio = BytesIO()
        broken = api.llvm.verifyModule(self._ptr, action, errio)
        if broken:
            raise llvm.LLVMException(errio.getvalue())

    def to_bitcode(self, fileobj=None):
        """Write bitcode representation of module to given file-like
        object.

        fileobj -- A file-like object to where the bitcode is written.
        If it is None, the bitcode is returned.

        Return value -- Returns None if fileobj is not None.
        Otherwise, return the bitcode as a bytestring.
        """
        ret = False
        if fileobj is None:
            ret = True
            fileobj = BytesIO()
        api.llvm.WriteBitcodeToFile(self._ptr, fileobj)
        if ret:
            return fileobj.getvalue()

    def _get_id(self):
        return self._ptr.getModuleIdentifier()

    def _set_id(self, string):
        self._ptr.setModuleIdentifier(string)

    id = property(_get_id, _set_id)

    def _to_native_something(self, fileobj, cgft):

        cgft = api.llvm.TargetMachine.CodeGenFileType.CGFT_AssemblyFile
        cgft = api.llvm.TargetMachine.CodeGenFileType.CGFT_ObjectFile

        from llvm.ee import TargetMachine
        from llvm.passes import PassManager
        from llvmpy import extra
        tm = TargetMachine.new()._ptr
        pm = PassManager.new()._ptr
        formatted
        failed = tm.addPassesToEmitFile(pm, fileobj, cgft, False)

        if failed:
            raise llvm.LLVMException("Failed to write native object file")
        if ret:
            return fileobj.getvalue()


    def to_native_object(self, fileobj=None):
        '''Outputs the byte string of the module as native object code

        If a fileobj is given, the output is written to it;
        Otherwise, the output is returned
        '''
        ret = False
        if fileobj is None:
            ret = True
            fileobj = BytesIO()
        from llvm.ee import TargetMachine
        tm = TargetMachine.new()
        fileobj.write(tm.emit_object(self))
        if ret:
            return fileobj.getvalue()


    def to_native_assembly(self, fileobj=None):
        '''Outputs the byte string of the module as native assembly code

        If a fileobj is given, the output is written to it;
        Otherwise, the output is returned
        '''
        ret = False
        if fileobj is None:
            ret = True
            fileobj = StringIO()
        from llvm.ee import TargetMachine
        tm = TargetMachine.new()
        asm = tm.emit_assembly(self)
        fileobj.write(asm)
        if ret:
            return fileobj.getvalue()


    def get_or_insert_named_metadata(self, name):
        return NamedMetaData(self._ptr.getOrInsertNamedMetadata(name))

    def get_named_metadata(self, name):
        md = self._ptr.getNamedMetadata(name)
        if md:
            return NamedMetaData(md)

    def clone(self):
        return Module(api.llvm.CloneModule(self._ptr))

class Type(llvm.Wrapper):
    """Represents a type, like a 32-bit integer or an 80-bit x86 float.

    Use one of the static methods to create an instance. Example:
    ty = Type.double()
    """
    __slots__ = '__name__'
    _type_ = api.llvm.Type

    def __init__(self, ptr):
        ptr = ptr._downcast(type(self)._type_)
        super(Type, self).__init__(ptr)

    @property
    def kind(self):
        return self._ptr.getTypeID()

    @staticmethod
    def int(bits=32):
        """Create an integer type having the given bit width."""
        context = api.llvm.getGlobalContext()
        ptr = api.llvm.Type.getIntNTy(context, bits)
        return Type(ptr)

    @staticmethod
    def float():
        """Create a 32-bit floating point type."""
        context = api.llvm.getGlobalContext()
        ptr = api.llvm.Type.getFloatTy(context)
        return Type(ptr)

    @staticmethod
    def double():
        """Create a 64-bit floating point type."""
        context = api.llvm.getGlobalContext()
        ptr = api.llvm.Type.getDoubleTy(context)
        return Type(ptr)

    @staticmethod
    def x86_fp80():
        """Create a 80-bit x86 floating point type."""
        context = api.llvm.getGlobalContext()
        ptr = api.llvm.Type.getX86_FP80Ty(context)
        return Type(ptr)

    @staticmethod
    def fp128():
        """Create a 128-bit floating point type (with 112-bit
            mantissa)."""
        context = api.llvm.getGlobalContext()
        ptr = api.llvm.Type.getFP128Ty(context)
        return Type(ptr)

    @staticmethod
    def ppc_fp128():
        """Create a 128-bit floating point type (two 64-bits)."""
        context = api.llvm.getGlobalContext()
        ptr = api.llvm.Type.getPPC_FP128Ty(context)
        return Type(ptr)


    @staticmethod
    def function(return_ty, param_tys, var_arg=False):
        """Create a function type.

        Creates a function type that returns a value of type
        `return_ty', takes arguments of types as given in the iterable
        `param_tys'. Set `var_arg' to True (default is False) for a
        variadic function."""
        ptr = api.llvm.FunctionType.get(return_ty._ptr,
                                   llvm._extract_ptrs(param_tys),
                                   var_arg)
        return FunctionType(ptr)

    @staticmethod
    def opaque(name):
        """Create a opaque StructType"""
        context = api.llvm.getGlobalContext()
        if not name:
            raise llvm.LLVMException("Opaque type must have a non-empty name")
        ptr = api.llvm.StructType.create(context, name)
        return StructType(ptr)

    @staticmethod
    def struct(element_tys, name=''): # not packed
        """Create a (unpacked) structure type.

        Creates a structure type with elements of types as given in the
        iterable `element_tys'. This method creates a unpacked
        structure. For a packed one, use the packed_struct() method.

        If name is not '', creates a identified type;
        otherwise, creates a literal type."""
        context = api.llvm.getGlobalContext()
        is_packed = False
        if name:
            ptr = api.llvm.StructType.create(context, name)
            ptr.setBody(llvm._extract_ptrs(element_tys), is_packed)
        else:
            ptr = api.llvm.StructType.get(context,
                                          llvm._extract_ptrs(element_tys),
                                          is_packed)


        return StructType(ptr)

    @staticmethod
    def packed_struct(element_tys, name=''):
        """Create a (packed) structure type.

        Creates a structure type with elements of types as given in the
        iterable `element_tys'. This method creates a packed
        structure. For an unpacked one, use the struct() method.

        If name is not '', creates a identified type;
        otherwise, creates a literal type."""
        context = api.llvm.getGlobalContext()
        is_packed = True
        ptr = api.llvm.StructType.create(context, name)
        ptr.setBody(llvm._extract_ptrs(element_tys), is_packed)
        return StructType(ptr)

    @staticmethod
    def array(element_ty, count):
        """Create an array type.

        Creates a type for an array of elements of type `element_ty',
        having 'count' elements."""
        ptr = api.llvm.ArrayType.get(element_ty._ptr, count)
        return ArrayType(ptr)

    @staticmethod
    def pointer(pointee_ty, addr_space=0):
        """Create a pointer type.

        Creates a pointer type, which can point to values of type
        `pointee_ty', in the address space `addr_space'."""
        ptr = api.llvm.PointerType.get(pointee_ty._ptr, addr_space)
        return PointerType(ptr)

    @staticmethod
    def vector(element_ty, count):
        """Create a vector type.

        Creates a type for a vector of elements of type `element_ty',
        having `count' elements."""
        ptr = api.llvm.VectorType.get(element_ty._ptr, count)
        return VectorType(ptr)

    @staticmethod
    def void():
        """Create a void type.

        Represents the `void' type."""
        context = api.llvm.getGlobalContext()
        ptr = api.llvm.Type.getVoidTy(context)
        return Type(ptr)

    @staticmethod
    def label():
        """Create a label type."""
        context = api.llvm.getGlobalContext()
        ptr = api.llvm.Type.getLabelTy(context)
        return Type(ptr)

    def __new__(cls, ptr):
        tyid = ptr.getTypeID()

        idmap = {
            TYPE_HALF:      IntegerType,
            TYPE_INTEGER:   IntegerType,
            TYPE_FUNCTION:  FunctionType,
            TYPE_STRUCT:    StructType,
            TYPE_ARRAY:     ArrayType,
            TYPE_POINTER:   PointerType,
            TYPE_VECTOR:    VectorType,
        }

        try:
            newcls = idmap[tyid]
        except KeyError:
            newcls = Type
        obj = llvm.Wrapper.__new__(newcls)
        return obj

    def __str__(self):
        return str(self._ptr)

    def __hash__(self):
        return hash(self._ptr)

    def __eq__(self, rhs):
        return self._ptr is rhs._ptr

    def __ne__(self, rhs):
        return not (self == rhs)

class IntegerType(Type):
    """Represents an integer type."""
    __slots__ = ()
    _type_ = api.llvm.IntegerType

    @property
    def width(self):
        """The width of the integer type, in bits."""
        return self._ptr.getIntegerBitWidth()

class FunctionType(Type):
    """Represents a function type."""
    __slots__ = ()
    _type_ = api.llvm.FunctionType

    @property
    def return_type(self):
        """The type of the value returned by this function."""
        return Type(self._ptr.getReturnType())

    @property
    def vararg(self):
        """True if this function is variadic."""
        return self._ptr.isVarArg()

    @property
    def args(self):
        """An iterable that yields Type objects, representing the types of the
            arguments accepted by this function, in order."""
        return [Type(self._ptr.getParamType(i)) for i in range(self.arg_count)]

    @property
    def arg_count(self):
        """Number of arguments accepted by this function.

            Same as len(obj.args), but faster."""
        return self._ptr.getNumParams()


class StructType(Type):
    """Represents a structure type."""
    _type_ = api.llvm.StructType
    __slots__ = ()

    @property
    def element_count(self):
        """Number of elements (members) in the structure.

            Same as len(obj.elements), but faster."""
        return self._ptr.getNumElements()

    @property
    def elements(self):
        """An iterable that yields Type objects, representing the types of the
            elements (members) of the structure, in order."""
        return [Type(self._ptr.getElementType(i))
                for i in range(self._ptr.getNumElements())]

    def set_body(self, elems, packed=False):
        """Filled the body of a opaque type.
            """
        # check
        if not self.is_opaque:
            raise llvm.LLVMException("Body is already defined.")

        self._ptr.setBody(llvm._extract_ptrs(elems), packed)

    @property
    def packed(self):
        """True if the structure is packed, False otherwise."""
        return self._ptr.isPacked()

    def _set_name(self, name):
        self._ptr.setName(name)

    def _get_name(self):
        if self._ptr.isLiteral():
           return ""
        else:
           return self._ptr.getName()

    name = property(_get_name, _set_name)

    @property
    def is_literal(self):
        return self._ptr.isLiteral()

    @property
    def is_identified(self):
        return not self.is_literal

    @property
    def is_opaque(self):
        return self._ptr.isOpaque()

    def is_layout_identical(self, other):
        return self._ptr.isLayoutIdentical(other._ptr)

class ArrayType(Type):
    """Represents an array type."""
    _type_ = api.llvm.ArrayType
    __slots__ = ()

    @property
    def element(self):
        return Type(self._ptr.getArrayElementType())

    @property
    def count(self):
        return self._ptr.getNumElements()

class PointerType(Type):
    _type_ = api.llvm.PointerType
    __slots__ = ()

    @property
    def pointee(self):
        return Type(self._ptr.getPointerElementType())

    @property
    def address_space(self):
        return self._ptr.getAddressSpace()

class VectorType(Type):
    _type_ = api.llvm.VectorType
    __slots__ = ()

    @property
    def element(self):
        return Type(self._ptr.getVectorElementType())

    @property
    def count(self):
        return self._ptr.getNumElements()

class Value(llvm.Wrapper):
    _type_ = api.llvm.Value
    __slots__ = '__weakref__'

    def __init__(self, builder, ptr):
        assert builder is _ValueFactory

        if type(self._type_) is type:
            if isinstance(ptr, self._type_): # is not downcast
                casted = ptr
            else:
                casted = ptr._downcast(self._type_)
        else:
            try:
                for ty in self._type_:
                    if isinstance(ptr, ty): # is not downcast
                        casted = ptr
                    else:
                        try:
                            casted = ptr._downcast(ty)
                        except ValueError:
                            pass
                        else:
                            break
                else:
                    casted = ptr
            except TypeError:
                casted = ptr
        super(Value, self).__init__(casted)

    def __str__(self):
        return str(self._ptr)

    def __hash__(self):
        return hash(self._ptr)

    def __eq__(self, rhs):
        if isinstance(rhs, Value):
            return str(self) == str(rhs)
        else:
            return False

    def __ne__(self, rhs):
        return not self == rhs

    def _get_name(self):
        return self._ptr.getName()

    def _set_name(self, value):
        return self._ptr.setName(value)

    name = property(_get_name, _set_name)

    @property
    def value_id(self):
        return self._ptr.getValueID()

    @property
    def type(self):
        return Type(self._ptr.getType())

    @property
    def use_count(self):
        return self._ptr.getNumUses()

    @property
    def uses(self):
        return list(map(_make_value, self._ptr.list_use()))

class User(Value):
    _type_ = api.llvm.User
    __slots__ = ()

    @property
    def operand_count(self):
        return self._ptr.getNumOperands()

    @property
    def operands(self):
        """Yields operands of this instruction."""
        return [_make_value(self._ptr.getOperand(i))
                for i in range(self.operand_count)]


class Constant(User):
    _type_ = api.llvm.Constant
    __slots__ = ()

    @staticmethod
    def null(ty):
        return _make_value(api.llvm.Constant.getNullValue(ty._ptr))

    @staticmethod
    def all_ones(ty):
        return _make_value(api.llvm.Constant.getAllOnesValue(ty._ptr))

    @staticmethod
    def undef(ty):
        return _make_value(api.llvm.UndefValue.get(ty._ptr))

    @staticmethod
    def int(ty, value):
        return _make_value(api.llvm.ConstantInt.get(ty._ptr, int(value), False))

    @staticmethod
    def int_signextend(ty, value):
        return _make_value(api.llvm.ConstantInt.get(ty._ptr, int(value), True))

    @staticmethod
    def real(ty, value):
        return _make_value(api.llvm.ConstantFP.get(ty._ptr, float(value)))

    @staticmethod
    def string(strval): # dont_null_terminate=True
        cxt = api.llvm.getGlobalContext()
        return _make_value(api.llvm.ConstantDataArray.getString(cxt, strval, False))

    @staticmethod
    def stringz(strval): # dont_null_terminate=False
        cxt = api.llvm.getGlobalContext()
        return _make_value(api.llvm.ConstantDataArray.getString(cxt, strval, True))

    @staticmethod
    def array(ty, consts):
        aryty = Type.array(ty, len(consts))
        return _make_value(api.llvm.ConstantArray.get(aryty._ptr,
                                                      llvm._extract_ptrs(consts)))

    @staticmethod
    def struct(consts): # not packed
        return _make_value(api.llvm.ConstantStruct.getAnon(llvm._extract_ptrs(consts),
                                                False))

    @staticmethod
    def packed_struct(consts):
         return _make_value(api.llvm.ConstantStruct.getAnon(llvm._extract_ptrs(consts),
                                                 False))

    @staticmethod
    def vector(consts):
        return _make_value(api.llvm.ConstantVector.get(llvm._extract_ptrs(consts)))

    @staticmethod
    def sizeof(ty):
        return _make_value(api.llvm.ConstantExpr.getSizeOf(ty._ptr))

    def neg(self):
        return _make_value(api.llvm.ConstantExpr.getNeg(self._ptr))

    def not_(self):
        return _make_value(api.llvm.ConstantExpr.getNot(self._ptr))

    def add(self, rhs):
        return _make_value(api.llvm.ConstantExpr.getAdd(self._ptr, rhs._ptr))

    def fadd(self, rhs):
        return _make_value(api.llvm.ConstantExpr.getFAdd(self._ptr, rhs._ptr))

    def sub(self, rhs):
        return _make_value(api.llvm.ConstantExpr.getSub(self._ptr, rhs._ptr))

    def fsub(self, rhs):
        return _make_value(api.llvm.ConstantExpr.getFSub(self._ptr, rhs._ptr))

    def mul(self, rhs):
        return _make_value(api.llvm.ConstantExpr.getMul(self._ptr, rhs._ptr))

    def fmul(self, rhs):
        return _make_value(api.llvm.ConstantExpr.getFMul(self._ptr, rhs._ptr))

    def udiv(self, rhs):
        return _make_value(api.llvm.ConstantExpr.getUDiv(self._ptr, rhs._ptr))

    def sdiv(self, rhs):
        return _make_value(api.llvm.ConstantExpr.getSDiv(self._ptr, rhs._ptr))

    def fdiv(self, rhs):
        return _make_value(api.llvm.ConstantExpr.getFDiv(self._ptr, rhs._ptr))

    def urem(self, rhs):
        return _make_value(api.llvm.ConstantExpr.getURem(self._ptr, rhs._ptr))

    def srem(self, rhs):
        return _make_value(api.llvm.ConstantExpr.getSRem(self._ptr, rhs._ptr))

    def frem(self, rhs):
        return _make_value(api.llvm.ConstantExpr.getFRem(self._ptr, rhs._ptr))

    def and_(self, rhs):
        return _make_value(api.llvm.ConstantExpr.getAnd(self._ptr, rhs._ptr))

    def or_(self, rhs):
        return _make_value(api.llvm.ConstantExpr.getOr(self._ptr, rhs._ptr))

    def xor(self, rhs):
        return _make_value(api.llvm.ConstantExpr.getXor(self._ptr, rhs._ptr))

    def icmp(self, int_pred, rhs):
        return _make_value(api.llvm.ConstantExpr.getICmp(int_pred, self._ptr, rhs._ptr))

    def fcmp(self, real_pred, rhs):
        return _make_value(api.llvm.ConstantExpr.getFCmp(real_pred, self._ptr, rhs._ptr))

    def shl(self, rhs):
        return _make_value(api.llvm.ConstantExpr.getShl(self._ptr, rhs._ptr))

    def lshr(self, rhs):
        return _make_value(api.llvm.ConstantExpr.getLShr(self._ptr, rhs._ptr))

    def ashr(self, rhs):
        return _make_value(api.llvm.ConstantExpr.getAShr(self._ptr, rhs._ptr))

    def gep(self, indices):
        indices = llvm._extract_ptrs(indices)
        return _make_value(api.llvm.ConstantExpr.getGetElementPtr(self._ptr, indices))

    def trunc(self, ty):
        return _make_value(api.llvm.ConstantExpr.getTrunc(self._ptr, ty._ptr))

    def sext(self, ty):
        return _make_value(api.llvm.ConstantExpr.getSExt(self._ptr, ty._ptr))

    def zext(self, ty):
        return _make_value(api.llvm.ConstantExpr.getZExt(self._ptr, ty._ptr))

    def fptrunc(self, ty):
        return _make_value(api.llvm.ConstantExpr.getFPTrunc(self._ptr, ty._ptr))

    def fpext(self, ty):
        return _make_value(api.llvm.ConstantExpr.getFPExtend(self._ptr, ty._ptr))

    def uitofp(self, ty):
        return _make_value(api.llvm.ConstantExpr.getUIToFP(self._ptr, ty._ptr))

    def sitofp(self, ty):
        return _make_value(api.llvm.ConstantExpr.getSIToFP(self._ptr, ty._ptr))

    def fptoui(self, ty):
        return _make_value(api.llvm.ConstantExpr.getFPToUI(self._ptr, ty._ptr))

    def fptosi(self, ty):
        return _make_value(api.llvm.ConstantExpr.getFPToSI(self._ptr, ty._ptr))

    def ptrtoint(self, ty):
        return _make_value(api.llvm.ConstantExpr.getPtrToInt(self._ptr, ty._ptr))

    def inttoptr(self, ty):
        return _make_value(api.llvm.ConstantExpr.getIntToPtr(self._ptr, ty._ptr))

    def bitcast(self, ty):
        return _make_value(api.llvm.ConstantExpr.getBitCast(self._ptr, ty._ptr))

    def select(self, true_const, false_const):
        return _make_value(api.llvm.ConstantExpr.getSelect(self._ptr,
                                                true_const._ptr,
                                                false_const._ptr))

    def extract_element(self, index): # note: self must be a _vector_ constant
        return _make_value(api.llvm.ConstantExpr.getExtractElement(self._ptr, index._ptr))

    def insert_element(self, value, index):
        return _make_value(api.llvm.ConstantExpr.getExtractElement(self._ptr,
                                                        value._ptr,
                                                        index._ptr))

    def shuffle_vector(self, vector_b, mask):
        return _make_value(api.llvm.ConstantExpr.getShuffleVector(self._ptr,
                                                       vector_b._ptr,
                                                       mask._ptr))

class ConstantExpr(Constant):
    _type_ = api.llvm.ConstantExpr
    __slots__ = ()

    @property
    def opcode(self):
        return self._ptr.getOpcode()

    @property
    def opcode_name(self):
        return self._ptr.getOpcodeName()

class ConstantAggregateZero(Constant):
    __slots__ = ()


class ConstantDataArray(Constant):
    __slots__ = ()


class ConstantDataVector(Constant):
    __slots__ = ()


class ConstantInt(Constant):
    _type_ = api.llvm.ConstantInt
    __slots__ = ()

    @property
    def z_ext_value(self):
        '''Obtain the zero extended value for an integer constant value.'''
        # Warning: assertion failure when value does not fit in 64 bits
        return self._ptr.getZExtValue()

    @property
    def s_ext_value(self):
        '''Obtain the sign extended value for an integer constant value.'''
        # Warning: assertion failure when value does not fit in 64 bits
        return self._ptr.getSExtValue()


class ConstantFP(Constant):
    __slots__ = ()


class ConstantArray(Constant):
    __slots__ = ()


class ConstantStruct(Constant):
    __slots__ = ()


class ConstantVector(Constant):
    __slots__ = ()


class ConstantPointerNull(Constant):
    __slots__ = ()


class UndefValue(Constant):
    __slots__ = ()


class GlobalValue(Constant):
    _type_ = api.llvm.GlobalValue
    __slots__ = ()

    def _get_linkage(self):
        return self._ptr.getLinkage()

    def _set_linkage(self, value):
        self._ptr.setLinkage(value)

    linkage = property(_get_linkage, _set_linkage)

    def _get_section(self):
        return self._ptr.getSection()

    def _set_section(self, value):
        return self._ptr.setSection(value)

    section = property(_get_section, _set_section)

    def _get_visibility(self):
        return self._ptr.getVisibility()

    def _set_visibility(self, value):
        return self._ptr.setVisibility(value)

    visibility = property(_get_visibility, _set_visibility)

    def _get_alignment(self):
        return self._ptr.getAlignment()

    def _set_alignment(self, value):
        return self._ptr.setAlignment(value)

    alignment = property(_get_alignment, _set_alignment)

    @property
    def is_declaration(self):
        return self._ptr.isDeclaration()

    @property
    def module(self):
        return Module(self._ptr.getParent())



class GlobalVariable(GlobalValue):
    _type_ = api.llvm.GlobalVariable
    __slots__ = ()

    @staticmethod
    def new(module, ty, name, addrspace=0):
        linkage = api.llvm.GlobalValue.LinkageTypes
        external_linkage = linkage.ExternalLinkage
        tlmode = api.llvm.GlobalVariable.ThreadLocalMode
        not_threadlocal = tlmode.NotThreadLocal
        gv = api.llvm.GlobalVariable.new(module._ptr,
                                     ty._ptr,
                                     False, # is constant
                                     external_linkage,
                                     None, # initializer
                                     name,
                                     None, # insert before
                                     not_threadlocal,
                                     addrspace)
        return _make_value(gv)

    @staticmethod
    def get(module, name):
        gv = _make_value(module._ptr.getNamedGlobal(name))
        if not gv:
            llvm.LLVMException("no global named `%s`" % name)
        return gv

    def delete(self):
        _ValueFactory.delete(self._ptr)
        self._ptr.eraseFromParent()

    def _get_initializer(self):
        if not self._ptr.hasInitializer():
            return None
        return _make_value(self._ptr.getInitializer())

    def _set_initializer(self, const):
        self._ptr.setInitializer(const._ptr)

    def _del_initializer(self):
        self._ptr.setInitializer(None)

    initializer = property(_get_initializer, _set_initializer)

    def _get_is_global_constant(self):
        return self._ptr.isConstant()

    def _set_is_global_constant(self, value):
        self._ptr.setConstant(value)

    global_constant = property(_get_is_global_constant,
                               _set_is_global_constant)

    def _get_thread_local(self):
        return self._ptr.isThreadLocal()

    def _set_thread_local(self, value):
        return self._ptr.setThreadLocal(value)

    thread_local = property(_get_thread_local, _set_thread_local)

class Argument(Value):
    __slots__ = ()
    _type_ = api.llvm.Argument
    _valid_attrs = frozenset([ATTR_BY_VAL, ATTR_NEST, ATTR_NO_ALIAS,
                              ATTR_NO_CAPTURE, ATTR_STRUCT_RET])

    if llvm.version >= (3, 3):
        def add_attribute(self, attr):
            context = api.llvm.getGlobalContext()
            attrbldr = api.llvm.AttrBuilder.new()
            attrbldr.addAttribute(attr)
            attrs = api.llvm.AttributeSet.get(context, 0, attrbldr)
            self._ptr.addAttr(attrs)

            if attr not in self:
                raise ValueError("Attribute %r is not valid for arg %s" %
                                 (attr, self))

        def remove_attribute(self, attr):
            context = api.llvm.getGlobalContext()
            attrbldr = api.llvm.AttrBuilder.new()
            attrbldr.addAttribute(attr)
            attrs = api.llvm.AttributeSet.get(context, 0, attrbldr)
            self._ptr.removeAttr(attrs)

        def _set_alignment(self, align):
            context = api.llvm.getGlobalContext()
            attrbldr = api.llvm.AttrBuilder.new()
            attrbldr.addAlignmentAttr(align)
            attrs = api.llvm.AttributeSet.get(context, 0, attrbldr)
            self._ptr.addAttr(attrs)
    else:
        def add_attribute(self, attr):
            context = api.llvm.getGlobalContext()
            attrbldr = api.llvm.AttrBuilder.new()
            attrbldr.addAttribute(attr)
            attrs = api.llvm.Attributes.get(context, attrbldr)
            self._ptr.addAttr(attrs)
            if attr not in self:
                raise ValueError("Attribute %r is not valid for arg %s" %
                                 (attr, self))

        def remove_attribute(self, attr):
            context = api.llvm.getGlobalContext()
            attrbldr = api.llvm.AttrBuilder.new()
            attrbldr.addAttribute(attr)
            attrs = api.llvm.Attributes.get(context, attrbldr)
            self._ptr.removeAttr(attrs)

        def _set_alignment(self, align):
            context = api.llvm.getGlobalContext()
            attrbldr = api.llvm.AttrBuilder.new()
            attrbldr.addAlignmentAttr(align)
            attrs = api.llvm.Attributes.get(context, attrbldr)
            self._ptr.addAttr(attrs)

    def _get_alignment(self):
        return self._ptr.getParamAlignment()

    alignment = property(_get_alignment,
                         _set_alignment)

    @property
    def attributes(self):
        '''Returns a set of defined attributes.
        '''
        return set(attr for attr in self._valid_attrs if attr in self)

    def __contains__(self, attr):
        if attr == ATTR_BY_VAL:
            return self.has_by_val()
        elif attr == ATTR_NEST:
            return self.has_nest()
        elif attr == ATTR_NO_ALIAS:
            return self.has_no_alias()
        elif attr == ATTR_NO_CAPTURE:
            return self.has_no_capture()
        elif attr == ATTR_STRUCT_RET:
            return self.has_struct_ret()
        else:
            raise ValueError('invalid attribute for argument')

    @property
    def arg_no(self):
        return self._ptr.getArgNo()

    def has_by_val(self):
        return self._ptr.hasByValAttr()

    def has_nest(self):
        return self._ptr.hasNestAttr()

    def has_no_alias(self):
        return self._ptr.hasNoAliasAttr()

    def has_no_capture(self):
        return self._ptr.hasNoCaptureAttr()

    def has_struct_ret(self):
        return self._ptr.hasStructRetAttr()

class Function(GlobalValue):
    __slots__ = ()
    _type_ = api.llvm.Function

    @staticmethod
    def new(module, func_ty, name):
        try:
            fn = Function.get(module, name)
        except llvm.LLVMException:
            return Function.get_or_insert(module, func_ty, name)
        else:
            raise llvm.LLVMException("Duplicated function %s" % name)


    @staticmethod
    def get_or_insert(module, func_ty, name):
        constant = module._ptr.getOrInsertFunction(name, func_ty._ptr)
        try:
            fn = constant._downcast(api.llvm.Function)
        except ValueError:
            # bitcasted to function type
            return _make_value(constant)
        else:
            return _make_value(fn)

    @staticmethod
    def get(module, name):
        fn = module._ptr.getFunction(name)
        if fn is None:
            raise llvm.LLVMException("no function named `%s`" % name)
        else:
            return _make_value(fn)

    @staticmethod
    def intrinsic(module, intrinsic_id, types):
        fn = api.llvm.Intrinsic.getDeclaration(module._ptr,
                                               intrinsic_id,
                                               llvm._extract_ptrs(types))
        return _make_value(fn)

    def delete(self):
        _ValueFactory.delete(self._ptr)
        self._ptr.eraseFromParent()

    @property
    def intrinsic_id(self):
        self._ptr.getIntrinsicID()

    def _get_cc(self):
        return self._ptr.getCallingConv()

    def _set_cc(self, value):
        self._ptr.setCallingConv(value)

    calling_convention = property(_get_cc, _set_cc)

    def _get_coll(self):
        return self._ptr.getGC()

    def _set_coll(self, value):
        return self._ptr.setGC(value)

    collector = property(_get_coll, _set_coll)

    # the nounwind attribute:
    def _get_does_not_throw(self):
        return self._ptr.doesNotThrow()

    def _set_does_not_throw(self,value):
        assert value
        self._ptr.setDoesNotThrow()

    does_not_throw = property(_get_does_not_throw, _set_does_not_throw)

    @property
    def args(self):
        args = self._ptr.getArgumentList()
        return list(map(_make_value, args))

    @property
    def basic_block_count(self):
        return len(self.basic_blocks)

    @property
    def entry_basic_block(self):
        assert self.basic_block_count
        return _make_value(self._ptr.getEntryBlock())

    def get_entry_basic_block(self):
        "Deprecated. Use entry_basic_block instead"
        return self.entry_basic_block

    def append_basic_block(self, name):
        context = api.llvm.getGlobalContext()
        bb = api.llvm.BasicBlock.Create(context, name, self._ptr, None)
        return _make_value(bb)

    @property
    def basic_blocks(self):
        return list(map(_make_value, self._ptr.getBasicBlockList()))

    def viewCFG(self):
        return self._ptr.viewCFG()

    def add_attribute(self, attr):
        self._ptr.addFnAttr(attr)

    def remove_attribute(self, attr):
        context = api.llvm.getGlobalContext()
        attrbldr = api.llvm.AttrBuilder.new()
        attrbldr.addAttribute(attr)
        if llvm.version >= (3, 3):
            attrs = api.llvm.Attribute.get(context, attrbldr)
        else:
            attrs = api.llvm.Attributes.get(context, attrbldr)
        self._ptr.removeFnAttr(attrs)

    def viewCFGOnly(self):
        return self._ptr.viewCFGOnly()

    def verify(self):
        # Although we're just asking LLVM to return the success or
        # failure, it appears to print result to stderr and abort.

        # Note: LLVM has a bug in preverifier that will always abort
        #       the process upon failure.
        actions = api.llvm.VerifierFailureAction
        broken = api.llvm.verifyFunction(self._ptr,
                                         actions.ReturnStatusAction)
        if broken:
            # If broken, then re-run to print the message
            api.llvm.verifyFunction(self._ptr, actions.PrintMessageAction)
            raise llvm.LLVMException("Function %s failed verification" %
                                     self.name)

#===----------------------------------------------------------------------===
# InlineAsm
#===----------------------------------------------------------------------===

class InlineAsm(Value):
    __slots__ = ()
    _type_ = api.llvm.InlineAsm

    @staticmethod
    def get(functype, asm, constrains, side_effect=False,
            align_stack=False, dialect=api.llvm.InlineAsm.AsmDialect.AD_ATT):
        ilasm = api.llvm.InlineAsm.get(functype._ptr, asm, constrains,
                                       side_effect, align_stack, dialect)
        return _make_value(ilasm)

#===----------------------------------------------------------------------===
# MetaData
#===----------------------------------------------------------------------===

class MetaData(Value):
    __slots__ = ()
    _type_ = api.llvm.MDNode

    @staticmethod
    def get(module, values):
        '''
        values -- must be an iterable of Constant or None. None is treated as "null".
        '''
        context = api.llvm.getGlobalContext()
        ptr = api.llvm.MDNode.get(context, llvm._extract_ptrs(values))
        return _make_value(ptr)

    @staticmethod
    def get_named_operands(module, name):
        namedmd = module.get_named_metadata(name)
        if not namedmd:
            return []
        return [_make_value(namedmd._ptr.getOperand(i))
                for i in range(namedmd._ptr.getNumOperands())]

    @staticmethod
    def add_named_operand(module, name, operand):
        namedmd = module.get_or_insert_named_metadata(name)._ptr
        namedmd.addOperand(operand._ptr)

    @property
    def operand_count(self):
        return self._ptr.getNumOperands()

    @property
    def operands(self):
        """Yields operands of this metadata."""
        res = []
        for i in range(self.operand_count):
            op = self._ptr.getOperand(i)
            if op is None:
                res.append(None)
            else:
                res.append(_make_value(op))
        return res

class MetaDataString(Value):
    _type_ = api.llvm.MDString

    @staticmethod
    def get(module, s):
        context = api.llvm.getGlobalContext()
        ptr = api.llvm.MDString.get(context, s)
        return _make_value(ptr)

    @property
    def string(self):
        '''Same as MDString::getString'''
        return self._ptr.getString()


class NamedMetaData(llvm.Wrapper):
    __slots__ = ()

    @staticmethod
    def get_or_insert(mod, name):
        return mod.get_or_insert_named_metadata(name)

    @staticmethod
    def get(mod, name):
        return mod.get_named_metadata(name)

    def delete(self):
        _ValueFactory.delete(self._ptr)
        self._ptr.eraseFromParent()

    @property
    def name(self):
        return self._ptr.getName()

    def __str__(self):
        return str(self._ptr)

    def add(self, operand):
        self._ptr.addOperand(operand._ptr)


#===----------------------------------------------------------------------===
# Instruction
#===----------------------------------------------------------------------===

class Instruction(User):
    __slots__ = ()
    _type_ = api.llvm.Instruction

    @property
    def basic_block(self):
        return _make_value(self._ptr.getParent())

    @property
    def is_terminator(self):
        return self._ptr.isTerminator()

    @property
    def is_binary_op(self):
        return self._ptr.isBinaryOp()

    @property
    def is_shift(self):
        return self._ptr.isShift()

    @property
    def is_cast(self):
        return self._ptr.isCast()

    @property
    def is_logical_shift(self):
        return self._ptr.isLogicalShift()

    @property
    def is_arithmetic_shift(self):
        return self._ptr.isArithmeticShift()

    @property
    def is_associative(self):
        return self._ptr.isAssociative()

    @property
    def is_commutative(self):
        return self._ptr.isCommutative()

    @property
    def is_volatile(self):
        """True if this is a volatile load or store."""
        if api.llvm.LoadInst.classof(self._ptr):
            return self._ptr._downcast(api.llvm.LoadInst).isVolatile()
        elif api.llvm.StoreInst.classof(self._ptr):
            return self._ptr._downcast(api.llvm.StoreInst).isVolatile()
        else:
            return False

    def set_volatile(self, flag):
        if api.llvm.LoadInst.classof(self._ptr):
            return self._ptr._downcast(api.llvm.LoadInst).setVolatile(flag)
        elif api.llvm.StoreInst.classof(self._ptr):
            return self._ptr._downcast(api.llvm.StoreInst).setVolatile(flag)
        else:
            return False

    def set_metadata(self, kind, metadata):
        self._ptr.setMetadata(kind, metadata._ptr)

    def has_metadata(self):
        return self._ptr.hasMetadata()

    def get_metadata(self, kind):
        return self._ptr.getMetadata(kind)

    @property
    def opcode(self):
        return self._ptr.getOpcode()

    @property
    def opcode_name(self):
        return self._ptr.getOpcodeName()

    def erase_from_parent(self):
        return self._ptr.eraseFromParent()

    def replace_all_uses_with(self, inst):
        self._ptr.replaceAllUsesWith(inst)


class CallOrInvokeInstruction(Instruction):
    __slots__ = ()
    _type_ = api.llvm.CallInst, api.llvm.InvokeInst

    def _get_cc(self):
        return self._ptr.getCallingConv()

    def _set_cc(self, value):
        return self._ptr.setCallingConv(value)

    calling_convention = property(_get_cc, _set_cc)

    def add_parameter_attribute(self, idx, attr):
        context = api.llvm.getGlobalContext()
        attrbldr = api.llvm.AttrBuilder.new()
        attrbldr.addAttribute(attr)
        if llvm.version >= (3, 3):
            attrs = api.llvm.Attribute.get(context, attrbldr)
        else:
            attrs = api.llvm.Attributes.get(context, attrbldr)

        self._ptr.addAttribute(idx, attrs)

    def remove_parameter_attribute(self, idx, attr):
        context = api.llvm.getGlobalContext()
        attrbldr = api.llvm.AttrBuilder.new()
        attrbldr.addAttribute(attr)
        if llvm.version >= (3, 3):
            attrs = api.llvm.Attribute.get(context, attrbldr)
        else:
            attrs = api.llvm.Attributes.get(context, attrbldr)

        self._ptr.removeAttribute(idx, attrs)

    def set_parameter_alignment(self, idx, align):
        context = api.llvm.getGlobalContext()
        attrbldr = api.llvm.AttrBuilder.new()
        attrbldr.addAlignmentAttr(align)
        if llvm.version >= (3, 3):
            attrs = api.llvm.Attribute.get(context, attrbldr)
        else:
            attrs = api.llvm.Attributes.get(context, attrbldr)

        self._ptr.addAttribute(idx, attrs)

    def _get_called_function(self):
        function = self._ptr.getCalledFunction()
        if function: # Return value can be None on indirect call/invoke
            return _make_value(function)

    def _set_called_function(self, function):
        self._ptr.setCalledFunction(function._ptr)

    called_function = property(_get_called_function, _set_called_function)


class PHINode(Instruction):
    __slots__ = ()
    _type_ = api.llvm.PHINode

    @property
    def incoming_count(self):
        return self._ptr.getNumIncomingValues()

    def add_incoming(self, value, block):
        self._ptr.addIncoming(value._ptr, block._ptr)

    def get_incoming_value(self, idx):
        return _make_value(self._ptr.getIncomingValue(idx))

    def get_incoming_block(self, idx):
        return _make_value(self._ptr.getIncomingBlock(idx))


class SwitchInstruction(Instruction):
    __slots__ = ()
    _type_ = api.llvm.SwitchInst

    def add_case(self, const, bblk):
        self._ptr.addCase(const._ptr, bblk._ptr)


class CompareInstruction(Instruction):
    __slots__ = ()
    _type_ = api.llvm.CmpInst

    @property
    def predicate(self):
        n = self._ptr.getPredicate()
        try:
            return ICMPEnum.get(n)
        except KeyError:
            return FCMPEnum.get(n)


class AllocaInstruction(Instruction):
    __slots__ = ()
    _type_ = api.llvm.AllocaInst

    @property
    def alignment(self):
        return self._ptr.getAlignment()

    @alignment.setter
    def alignment(self, n):
        self._ptr.setAlignment(n)

    @property
    def array_size(self):
        return self._ptr.getArraySize()

    @array_size.setter
    def array_size(self, value):
        return self._ptr.setArraySize(value._ptr)._ptr

    @property
    def is_array(self):
        return self._ptr.isArrayAllocation()

    @property
    def is_static(self):
        return self._ptr.isStaticAlloca()

#===----------------------------------------------------------------------===
# Basic block
#===----------------------------------------------------------------------===

class BasicBlock(Value):
    __slots__ = ()
    _type_ = api.llvm.BasicBlock

    def insert_before(self, name):
        context = api.llvm.getGlobalContext()
        ptr = api.llvm.BasicBlock.Create(context, name, self.function._ptr,
                                    self._ptr)
        return _make_value(ptr)

    def delete(self):
        _ValueFactory.delete(self._ptr)
        self._ptr.eraseFromParent()

    @property
    def function(self):
        return _make_value(self._ptr.getParent())

    @property
    def instructions(self):
        """
        Returns a list of instructions.
        Note: This function is expensive.  To access the terminator of the
        block, use BasicBlock.terminator.
        """
        return list(map(_make_value, self._ptr.getInstList()))

    @property
    def terminator(self):
        """Returns None or the terminator of this basicblock.
        """
        inst = self._ptr.getTerminator()
        return _make_value(inst) if inst is not None else None

#===----------------------------------------------------------------------===
# Value factory method
#===----------------------------------------------------------------------===


class _ValueFactory(object):
    __slots__ = ()
    cache = weakref.WeakValueDictionary()

    # value ID -> class map
    class_for_valueid = {
        VALUE_ARGUMENT                        : Argument,
        VALUE_BASIC_BLOCK                     : BasicBlock,
        VALUE_FUNCTION                        : Function,
        VALUE_GLOBAL_ALIAS                    : GlobalValue,
        VALUE_GLOBAL_VARIABLE                 : GlobalVariable,
        VALUE_UNDEF_VALUE                     : UndefValue,
        VALUE_CONSTANT_EXPR                   : ConstantExpr,
        VALUE_CONSTANT_AGGREGATE_ZERO         : ConstantAggregateZero,
        VALUE_CONSTANT_DATA_ARRAY             : ConstantDataArray,
        VALUE_CONSTANT_DATA_VECTOR            : ConstantDataVector,
        VALUE_CONSTANT_INT                    : ConstantInt,
        VALUE_CONSTANT_FP                     : ConstantFP,
        VALUE_CONSTANT_ARRAY                  : ConstantArray,
        VALUE_CONSTANT_STRUCT                 : ConstantStruct,
        VALUE_CONSTANT_VECTOR                 : ConstantVector,
        VALUE_CONSTANT_POINTER_NULL           : ConstantPointerNull,
        VALUE_MD_NODE                         : MetaData,
        VALUE_MD_STRING                       : MetaDataString,
        VALUE_INLINE_ASM                      : InlineAsm,
        VALUE_INSTRUCTION + OPCODE_PHI        : PHINode,
        VALUE_INSTRUCTION + OPCODE_CALL       : CallOrInvokeInstruction,
        VALUE_INSTRUCTION + OPCODE_INVOKE     : CallOrInvokeInstruction,
        VALUE_INSTRUCTION + OPCODE_SWITCH     : SwitchInstruction,
        VALUE_INSTRUCTION + OPCODE_ICMP       : CompareInstruction,
        VALUE_INSTRUCTION + OPCODE_FCMP       : CompareInstruction,
        VALUE_INSTRUCTION + OPCODE_ALLOCA     : AllocaInstruction,
    }

    @classmethod
    def build(cls, ptr):
        # try to look in the cache
        addr = ptr._capsule.pointer
        id = ptr.getValueID()
        key = id, addr
        try:
            obj = cls.cache[key]
            return obj
        except KeyError:
            pass
        # find class by value id
        ctorcls = cls.class_for_valueid.get(id)
        if not ctorcls:
            if id > VALUE_INSTRUCTION: # "generic" instruction
                ctorcls = Instruction
            else: # "generic" value
                ctorcls = Value
        # cache the obj
        obj = ctorcls(_ValueFactory, ptr)
        cls.cache[key] = obj
        return obj

    @classmethod
    def delete(cls, ptr):
        del cls.cache[(ptr.getValueID(), ptr._capsule.pointer)]

def _make_value(ptr):
    return _ValueFactory.build(ptr)

#===----------------------------------------------------------------------===
# Builder
#===----------------------------------------------------------------------===

_atomic_orderings = {
    'unordered' : api.llvm.AtomicOrdering.Unordered,
    'monotonic' : api.llvm.AtomicOrdering.Monotonic,
    'acquire'   : api.llvm.AtomicOrdering.Acquire,
    'release'   : api.llvm.AtomicOrdering.Release,
    'acq_rel'   : api.llvm.AtomicOrdering.AcquireRelease,
    'seq_cst'   : api.llvm.AtomicOrdering.SequentiallyConsistent
}

class Builder(llvm.Wrapper):
    __slots__ = ()

    @staticmethod
    def new(basic_block):
        context = api.llvm.getGlobalContext()
        ptr = api.llvm.IRBuilder.new(context)
        ptr.SetInsertPoint(basic_block._ptr)
        return Builder(ptr)

    def position_at_beginning(self, bblk):
        """Position the builder at the beginning of the given block.

        Next instruction inserted will be first one in the block."""

        # Instruction list won't be long anyway,
        # Does not matter much to build a list of all instructions
        instrs = bblk.instructions
        if instrs:
            self.position_before(instrs[0])
        else:
            self.position_at_end(bblk)

    def position_at_end(self, bblk):
        """Position the builder at the end of the given block.

        Next instruction inserted will be last one in the block."""

        self._ptr.SetInsertPoint(bblk._ptr)

    def position_before(self, instr):
        """Position the builder before the given instruction.

            The instruction can belong to a basic block other than the
            current one."""
        self._ptr.SetInsertPoint(instr._ptr)

    @property
    def basic_block(self):
        """The basic block where the builder is positioned."""
        return _make_value(self._ptr.GetInsertBlock())

    # terminator instructions
    def _guard_terminators(self):
        if __debug__:
            import warnings
            for instr in self.basic_block.instructions:
                if instr.is_terminator:
                    warnings.warn("BasicBlock can only have one terminator")

    def ret_void(self):
        self._guard_terminators()
        return _make_value(self._ptr.CreateRetVoid())

    def ret(self, value):
        self._guard_terminators()
        return _make_value(self._ptr.CreateRet(value._ptr))

    def ret_many(self, values):
        self._guard_terminators()
        values = llvm._extract_ptrs(values)
        return _make_value(self._ptr.CreateAggregateRet(values, len(values)))

    def branch(self, bblk):
        self._guard_terminators()
        return _make_value(self._ptr.CreateBr(bblk._ptr))

    def cbranch(self, if_value, then_blk, else_blk):
        self._guard_terminators()
        return _make_value(self._ptr.CreateCondBr(if_value._ptr,
                                            then_blk._ptr,
                                            else_blk._ptr))

    def switch(self, value, else_blk, n=10):
        self._guard_terminators()
        return _make_value(self._ptr.CreateSwitch(value._ptr,
                                                  else_blk._ptr,
                                                  n))

    def invoke(self, func, args, then_blk, catch_blk, name=""):
        self._guard_terminators()
        return _make_value(self._ptr.CreateInvoke(func._ptr,
                                                  then_blk._ptr,
                                                  catch_blk._ptr,
                                                  llvm._extract_ptrs(args)))

    def unreachable(self):
        self._guard_terminators()
        return _make_value(self._ptr.CreateUnreachable())

    # arithmethic, bitwise and logical

    def add(self, lhs, rhs, name="", nuw=False, nsw=False):
        return _make_value(self._ptr.CreateAdd(lhs._ptr, rhs._ptr, name,
                                               nuw, nsw))

    def fadd(self, lhs, rhs, name=""):
        return _make_value(self._ptr.CreateFAdd(lhs._ptr, rhs._ptr, name))

    def sub(self, lhs, rhs, name="", nuw=False, nsw=False):
        return _make_value(self._ptr.CreateSub(lhs._ptr, rhs._ptr, name,
                                               nuw, nsw))

    def fsub(self, lhs, rhs, name=""):
        return _make_value(self._ptr.CreateFSub(lhs._ptr, rhs._ptr, name))

    def mul(self, lhs, rhs, name="", nuw=False, nsw=False):
        return _make_value(self._ptr.CreateMul(lhs._ptr, rhs._ptr, name,
                                               nuw, nsw))

    def fmul(self, lhs, rhs, name=""):
        return _make_value(self._ptr.CreateFMul(lhs._ptr, rhs._ptr, name))

    def udiv(self, lhs, rhs, name="", exact=False):
        return _make_value(self._ptr.CreateUDiv(lhs._ptr, rhs._ptr, name,
                                                exact))

    def sdiv(self, lhs, rhs, name="", exact=False):
        return _make_value(self._ptr.CreateSDiv(lhs._ptr, rhs._ptr, name,
                                                exact))

    def fdiv(self, lhs, rhs, name=""):
        return _make_value(self._ptr.CreateFDiv(lhs._ptr, rhs._ptr, name))

    def urem(self, lhs, rhs, name=""):
        return _make_value(self._ptr.CreateURem(lhs._ptr, rhs._ptr, name))

    def srem(self, lhs, rhs, name=""):
        return _make_value(self._ptr.CreateSRem(lhs._ptr, rhs._ptr, name))

    def frem(self, lhs, rhs, name=""):
        return _make_value(self._ptr.CreateFRem(lhs._ptr, rhs._ptr, name))

    def shl(self, lhs, rhs, name="", nuw=False, nsw=False):
        return _make_value(self._ptr.CreateShl(lhs._ptr, rhs._ptr, name,
                                               nuw, nsw))

    def lshr(self, lhs, rhs, name="", exact=False):
        return _make_value(self._ptr.CreateLShr(lhs._ptr, rhs._ptr, name,
                                                exact))

    def ashr(self, lhs, rhs, name="", exact=False):
        return _make_value(self._ptr.CreateAShr(lhs._ptr, rhs._ptr, name,
                                                exact))

    def and_(self, lhs, rhs, name=""):
        return _make_value(self._ptr.CreateAnd(lhs._ptr, rhs._ptr, name))

    def or_(self, lhs, rhs, name=""):
        return _make_value(self._ptr.CreateOr(lhs._ptr, rhs._ptr, name))

    def xor(self, lhs, rhs, name=""):
        return _make_value(self._ptr.CreateXor(lhs._ptr, rhs._ptr, name))

    def neg(self, val, name="", nuw=False, nsw=False):
        return _make_value(self._ptr.CreateNeg(val._ptr, name, nuw, nsw))

    def not_(self, val, name=""):
        return _make_value(self._ptr.CreateNot(val._ptr, name))

    # memory

    def malloc(self, ty, name=""):
        allocsz = api.llvm.ConstantExpr.getSizeOf(ty._ptr)
        ity = allocsz.getType()
        malloc = api.llvm.CallInst.CreateMalloc(self.basic_block._ptr,
                                                ity,
                                                ty._ptr,
                                                allocsz,
                                                None,
                                                None,
                                                "")
        inst = self._ptr.Insert(malloc, name)
        return _make_value(inst)

    def malloc_array(self, ty, size, name=""):
        allocsz = api.llvm.ConstantExpr.getSizeOf(ty._ptr)
        ity = allocsz.getType()
        malloc = api.llvm.CallInst.CreateMalloc(self.basic_block._ptr,
                                                ity,
                                                ty._ptr,
                                                allocsz,
                                                size._ptr,
                                                None,
                                                "")
        inst = self._ptr.Insert(malloc, name)
        return _make_value(inst)

    def alloca(self, ty, size=None, name=""):
        sizeptr = size._ptr if size else None
        return _make_value(self._ptr.CreateAlloca(ty._ptr, sizeptr, name))

    @deprecated
    def alloca_array(self, ty, size, name=""):
        return self.alloca(ty, size, name=name)

    def free(self, ptr):
        free = api.llvm.CallInst.CreateFree(ptr._ptr, self.basic_block._ptr)
        inst = self._ptr.Insert(free)
        return _make_value(inst)

    def load(self, ptr, name="", align=0, volatile=False, invariant=False):
        inst = _make_value(self._ptr.CreateLoad(ptr._ptr, name))
        if align:
            inst._ptr.setAlignment(align)
        if volatile:
            inst.set_volatile(volatile)
        if invariant:
            mod = self.basic_block.function.module
            md = MetaData.get(mod, []) # empty metadata node
            inst.set_metadata('invariant.load', md)
        return inst

    def store(self, value, ptr, align=0, volatile=False):
        inst = _make_value(self._ptr.CreateStore(value._ptr, ptr._ptr))
        if align:
            inst._ptr.setAlignment(align)
        if volatile:
            inst.set_volatile(volatile)
        return inst

    def gep(self, ptr, indices, name="", inbounds=False):
        if inbounds:
            ret = self._ptr.CreateInBoundsGEP(ptr._ptr,
                                              llvm._extract_ptrs(indices),
                                              name)
        else:
            ret = self._ptr.CreateGEP(ptr._ptr,
                                      llvm._extract_ptrs(indices),
                                      name)
        return _make_value(ret)

    # casts and extensions

    def trunc(self, value, dest_ty, name=""):
        return _make_value(self._ptr.CreateTrunc(value._ptr, dest_ty._ptr, name))

    def zext(self, value, dest_ty, name=""):
        return _make_value(self._ptr.CreateZExt(value._ptr, dest_ty._ptr, name))

    def sext(self, value, dest_ty, name=""):
        return _make_value(self._ptr.CreateSExt(value._ptr, dest_ty._ptr, name))

    def fptoui(self, value, dest_ty, name=""):
        return _make_value(self._ptr.CreateFPToUI(value._ptr, dest_ty._ptr, name))

    def fptosi(self, value, dest_ty, name=""):
        return _make_value(self._ptr.CreateFPToSI(value._ptr, dest_ty._ptr, name))

    def uitofp(self, value, dest_ty, name=""):
        return _make_value(self._ptr.CreateUIToFP(value._ptr, dest_ty._ptr, name))

    def sitofp(self, value, dest_ty, name=""):
        return _make_value(self._ptr.CreateSIToFP(value._ptr, dest_ty._ptr, name))

    def fptrunc(self, value, dest_ty, name=""):
        return _make_value(self._ptr.CreateFPTrunc(value._ptr, dest_ty._ptr, name))

    def fpext(self, value, dest_ty, name=""):
        return _make_value(self._ptr.CreateFPExt(value._ptr, dest_ty._ptr, name))

    def ptrtoint(self, value, dest_ty, name=""):
        return _make_value(self._ptr.CreatePtrToInt(value._ptr, dest_ty._ptr, name))

    def inttoptr(self, value, dest_ty, name=""):
        return _make_value(self._ptr.CreateIntToPtr(value._ptr, dest_ty._ptr, name))

    def bitcast(self, value, dest_ty, name=""):
        return _make_value(self._ptr.CreateBitCast(value._ptr, dest_ty._ptr, name))

    # comparisons

    def icmp(self, ipred, lhs, rhs, name=""):
        return _make_value(self._ptr.CreateICmp(ipred, lhs._ptr, rhs._ptr, name))

    def fcmp(self, rpred, lhs, rhs, name=""):
        return _make_value(self._ptr.CreateFCmp(rpred, lhs._ptr, rhs._ptr, name))

    # misc

    def extract_value(self, retval, idx, name=""):
        if not isinstance(idx, (tuple, list)):
            idx = [idx]
        return _make_value(self._ptr.CreateExtractValue(retval._ptr, idx,
                                                        name))

    # obsolete synonym for extract_value
    getresult = extract_value

    def insert_value(self, retval, rhs, idx, name=""):
        if not isinstance(idx, (tuple, list)):
            idx = [idx]
        return _make_value(self._ptr.CreateInsertValue(retval._ptr,
                                                       rhs._ptr,
                                                       idx,
                                                       name))

    def phi(self, ty, name=""):
        return _make_value(self._ptr.CreatePHI(ty._ptr, 2, name))

    def call(self, fn, args, name=""):
        err_template = 'Argument type mismatch: expected %s but got %s'

        for i, (t, v) in enumerate(zip(fn.type.pointee.args, args)):
            if  t != v.type:
                raise TypeError(err_template % (t, v.type))
        arg_ptrs = llvm._extract_ptrs(args)
        return _make_value(self._ptr.CreateCall(fn._ptr, arg_ptrs, name))

    def select(self, cond, then_value, else_value, name=""):
        return _make_value(self._ptr.CreateSelect(cond._ptr, then_value._ptr,
                                            else_value._ptr, name))

    def vaarg(self, list_val, ty, name=""):
        return _make_value(self._ptr.CreateVAArg(list_val._ptr, ty._ptr, name))

    def extract_element(self, vec_val, idx_val, name=""):
        return _make_value(self._ptr.CreateExtractElement(vec_val._ptr,
                                                          idx_val._ptr,
                                                          name))


    def insert_element(self, vec_val, elt_val, idx_val, name=""):
        return _make_value(self._ptr.CreateInsertElement(vec_val._ptr,
                                                          elt_val._ptr,
                                                          idx_val._ptr,
                                                          name))

    def shuffle_vector(self, vecA, vecB, mask, name=""):
        return _make_value(self._ptr.CreateShuffleVector(vecA._ptr,
                                                         vecB._ptr,
                                                         mask._ptr,
                                                         name))
    # atomics

    def atomic_cmpxchg(self, ptr, old, new, ordering, crossthread=True):
        return _make_value(self._ptr.CreateAtomicCmpXchg(ptr._ptr,
                                                   old._ptr,
                                                   new._ptr,
                                                   _atomic_orderings[ordering],
                                                   _sync_scope(crossthread)))

    def atomic_rmw(self, op, ptr, val, ordering, crossthread=True):
        op_dict = dict((k.lower(), v)
                       for k, v in vars(api.llvm.AtomicRMWInst.BinOp).items())
        op = op_dict[op]
        return _make_value(self._ptr.CreateAtomicRMW(op, ptr._ptr, val._ptr,
                                               _atomic_orderings[ordering],
                                               _sync_scope(crossthread)))

    def atomic_xchg(self, *args, **kwargs):
        return self.atomic_rmw('xchg', *args, **kwargs)

    def atomic_add(self, *args, **kwargs):
        return self.atomic_rmw('add', *args, **kwargs)

    def atomic_sub(self, *args, **kwargs):
        return self.atomic_rmw('sub', *args, **kwargs)

    def atomic_and(self, *args, **kwargs):
        return self.atomic_rmw('and', *args, **kwargs)

    def atomic_nand(self, *args, **kwargs):
        return self.atomic_rmw('nand', *args, **kwargs)

    def atomic_or(self, *args, **kwargs):
        return self.atomic_rmw('or', *args, **kwargs)

    def atomic_xor(self, *args, **kwargs):
        return self.atomic_rmw('xor', *args, **kwargs)

    def atomic_max(self, *args, **kwargs):
        return self.atomic_rmw('max', *args, **kwargs)

    def atomic_min(self, *args, **kwargs):
        return self.atomic_rmw('min', *args, **kwargs)

    def atomic_umax(self, *args, **kwargs):
        return self.atomic_rmw('umax', *args, **kwargs)

    def atomic_umin(self, *args, **kwargs):
        return self.atomic_rmw('umin', *args, **kwargs)

    def atomic_load(self, ptr, ordering, align=1, crossthread=True,
                    volatile=False, name=""):
        inst = self.load(ptr, align=align, volatile=volatile, name=name)
        inst._ptr.setAtomic(_atomic_orderings[ordering],
                            _sync_scope(crossthread))
        return inst

    def atomic_store(self, value, ptr, ordering, align=1, crossthread=True,
                     volatile=False):
        inst = self.store(value, ptr, align=align, volatile=volatile)
        inst._ptr.setAtomic(_atomic_orderings[ordering],
                            _sync_scope(crossthread))
        return inst


    def fence(self, ordering, crossthread=True):
        return _make_value(self._ptr.CreateFence(_atomic_orderings[ordering],
                                                 _sync_scope(crossthread)))

def _sync_scope(crossthread):
    if crossthread:
        scope = api.llvm.SynchronizationScope.CrossThread
    else:
        scope = api.llvm.SynchronizationScope.SingleThread
    return scope

def load_library_permanently(filename):
    """Load a shared library.

    Load the given shared library (filename argument specifies the full
    path of the .so file) using LLVM. Symbols from these are available
    from the execution engine thereafter."""
    with contextlib.closing(BytesIO()) as errmsg:
        failed = api.llvm.sys.DynamicLibrary.LoadPermanentLibrary(filename,
                                                                  errmsg)
        if failed:
            raise llvm.LLVMException(errmsg.getvalue())

def inline_function(call):
    info = api.llvm.InlineFunctionInfo.new()
    return api.llvm.InlineFunction(call._ptr, info)

def parse_environment_options(progname, envname):
    api.llvm.cl.ParseEnvironmentOptions(progname, envname)

if api.llvm.InitializeNativeTarget():
    raise llvm.LLVMException("No native target!?")
if api.llvm.InitializeNativeTargetAsmPrinter():
    # should this be an optional feature?
    # should user trigger the initialization?
    raise llvm.LLVMException("No native asm printer!?")
if api.llvm.InitializeNativeTargetAsmParser():
    # required by MCJIT?
    # should this be an optional feature?
    # should user trigger the initialization?
    raise llvm.LLVMException("No native asm parser!?")

########NEW FILE########
__FILENAME__ = deprecated
"""
Shameless borrowed from Smart_deprecation_warnings
https://wiki.python.org/moin/PythonDecoratorLibrary
"""

import warnings
import functools


def deprecated(func):
    """This is a decorator which can be used to mark functions
    as deprecated. It will result in a warning being emitted
    when the function is used."""

    @functools.wraps(func)
    def new_func(*args, **kwargs):
        warnings.warn_explicit(
            "Call to deprecated function %s." % (func.__name__,),
            category=DeprecationWarning,
            filename=func.func_code.co_filename,
            lineno=func.func_code.co_firstlineno + 1
        )
        return func(*args, **kwargs)

    return new_func

########NEW FILE########
__FILENAME__ = ee
#
# Copyright (c) 2008-10, Mahadevan R All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#  * Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
#
#  * Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
#  * Neither the name of this software, nor the names of its
#    contributors may be used to endorse or promote products derived from
#    this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#

"Execution Engine and related classes."

import sys

import llvm
from llvm import core
from llvm.passes import TargetData, TargetTransformInfo
from llvmpy import api, extra

#===----------------------------------------------------------------------===
# import items which were moved to target module
#===----------------------------------------------------------------------===
from llvm.target import (initialize_all, initialize_target,
    print_registered_targets, get_host_cpu_name, get_default_triple,
    TargetMachine,
    BO_BIG_ENDIAN, BO_LITTLE_ENDIAN,
    CM_DEFAULT, CM_JITDEFAULT, CM_SMALL, CM_KERNEL, CM_MEDIUM, CM_LARGE,
    RELOC_DEFAULT, RELOC_STATIC, RELOC_PIC, RELOC_DYNAMIC_NO_PIC)


#===----------------------------------------------------------------------===
# Generic value
#===----------------------------------------------------------------------===

class GenericValue(llvm.Wrapper):

    @staticmethod
    def int(ty, intval):
        ptr = api.llvm.GenericValue.CreateInt(ty._ptr, int(intval), False)
        return GenericValue(ptr)

    @staticmethod
    def int_signed(ty, intval):
        ptr = api.llvm.GenericValue.CreateInt(ty._ptr, int(intval), True)
        return GenericValue(ptr)

    @staticmethod
    def real(ty, floatval):
        if str(ty) == 'float':
            ptr = api.llvm.GenericValue.CreateFloat(float(floatval))
        elif str(ty) == 'double':
            ptr = api.llvm.GenericValue.CreateDouble(float(floatval))
        else:
            raise Exception('Unreachable')
        return GenericValue(ptr)

    @staticmethod
    def pointer(addr):
        '''
        One argument version takes (addr).
        Two argument version takes (ty, addr). [Deprecated]

        `ty` is unused.
        `addr` is an integer representing an address.

        '''
        ptr = api.llvm.GenericValue.CreatePointer(int(addr))
        return GenericValue(ptr)

    def as_int(self):
        return self._ptr.toUnsignedInt()

    def as_int_signed(self):
        return self._ptr.toSignedInt()

    def as_real(self, ty):
        return self._ptr.toFloat(ty._ptr)

    def as_pointer(self):
        return self._ptr.toPointer()

#===----------------------------------------------------------------------===
# Engine builder
#===----------------------------------------------------------------------===

class EngineBuilder(llvm.Wrapper):
    @staticmethod
    def new(module):
        ptr = api.llvm.EngineBuilder.new(module._ptr)
        return EngineBuilder(ptr)

    def force_jit(self):
        self._ptr.setEngineKind(api.llvm.EngineKind.Kind.JIT)
        return self

    def force_interpreter(self):
        self._ptr.setEngineKind(api.llvm.EngineKind.Kind.Interpreter)
        return self

    def opt(self, level):
        '''
        level valid [0, 1, 2, 3] -- [None, Less, Default, Aggressive]
        '''
        assert 0 <= level <= 3
        self._ptr.setOptLevel(level)
        return self

    def mattrs(self, string):
        '''set machine attributes as a comma/space separated string

        e.g: +sse,-3dnow
        '''
        self._ptr.setMAttrs(string.split(','))
        return self

    def create(self, tm=None):
        '''
        tm --- Optional. Provide a TargetMachine.  Ownership is transfered
        to the returned execution engine.
        '''
        if tm is not None:
            engine = self._ptr.create(tm._ptr)
        elif (sys.platform.startswith('win32') and
                    getattr(self, '_use_mcjit', False)):
            # force ELF generation on MCJIT on win32
            triple = get_default_triple()
            tm = TargetMachine.new('%s-elf' % triple)
            engine = self._ptr.create(tm._ptr)
        else:
            engine = self._ptr.create()
        ee = ExecutionEngine(engine)
        ee.finalize_object()                # no effect for legacy JIT
        return ee

    def select_target(self, *args):
        '''get the corresponding target machine

        Accept no arguments or (triple, march, mcpu, mattrs)
        '''
        if args:
            triple, march, mcpu, mattrs = args
            ptr = self._ptr.selectTarget(triple, march, mcpu,
                                          mattrs.split(','))
        else:
            ptr = self._ptr.selectTarget()
        return TargetMachine(ptr)

    def mcjit(self, enable):
        '''Enable/disable MCJIT
        '''
        self._ptr.setUseMCJIT(enable)
        self._use_mcjit = True
        return self

#===----------------------------------------------------------------------===
# Execution engine
#===----------------------------------------------------------------------===

class ExecutionEngine(llvm.Wrapper):

    @staticmethod
    def new(module, force_interpreter=False):
        eb = EngineBuilder.new(module)
        if force_interpreter:
            eb.force_interpreter()
        return eb.create()

    def disable_lazy_compilation(self, disabled=True):
        self._ptr.DisableLazyCompilation(disabled)

    def run_function(self, fn, args):
        ptr = self._ptr.runFunction(fn._ptr, list(map(lambda x: x._ptr, args)))
        return GenericValue(ptr)

    def get_pointer_to_named_function(self, name, abort=True):
        return self._ptr.getPointerToNamedFunction(name, abort)

    def get_pointer_to_function(self, fn):
        return self._ptr.getPointerToFunction(fn._ptr)

    def get_pointer_to_global(self, val):
        return self._ptr.getPointerToGlobal(val._ptr)

    def add_global_mapping(self, gvar, addr):
        assert addr >= 0, "Address cannot not be negative"
        self._ptr.addGlobalMapping(gvar._ptr, addr)

    def run_static_ctors(self):
        self._ptr.runStaticConstructorsDestructors(False)

    def run_static_dtors(self):
        self._ptr.runStaticConstructorsDestructors(True)

    def free_machine_code_for(self, fn):
        self._ptr.freeMachineCodeForFunction(fn._ptr)

    def add_module(self, module):
        self._ptr.addModule(module._ptr)

    def remove_module(self, module):
        return self._ptr.removeModule(module._ptr)

    def finalize_object(self):
        return self._ptr.finalizeObject()

    @property
    def target_data(self):
        ptr = self._ptr.getDataLayout()
        return TargetData(ptr)


#===----------------------------------------------------------------------===
# Dynamic Library
#===----------------------------------------------------------------------===

def dylib_add_symbol(name, ptr):
    api.llvm.sys.DynamicLibrary.AddSymbol(name, ptr)

def dylib_address_of_symbol(name):
    return api.llvm.sys.DynamicLibrary.SearchForAddressOfSymbol(name)

def dylib_import_library(filename):
    """Permanently import a dynamic library.

    Returns a DynamicLibrary object

    Raises RuntimeError
    """
    return DynamicLibrary(filename)


class DynamicLibrary(object):
    def __init__(self, filename):
        """
        Raises RuntimeError
        """
        self._ptr = api.llvm.sys.DynamicLibrary.getPermanentLibrary(
            filename)

    def get_address_of_symbol(self, symbol):
        """
        Get the address of `symbol` (str) as integer
        """
        return self._ptr.getAddressOfSymbol(symbol)

########NEW FILE########
__FILENAME__ = llrt
import os
import llvm.core as lc
import llvm.passes as lp
import llvm.ee as le

def replace_divmod64(lfunc):
    '''Replaces all 64-bit integer division (sdiv, udiv) and modulo (srem, urem)
    '''
    int64 = lc.Type.int(64)
    int64ptr = lc.Type.pointer(lc.Type.int(64))

    functy = lc.Type.function(int64, [int64, int64])
    udiv64 = lfunc.module.get_or_insert_function(functy, '__llrt_udiv64')
    sdiv64 = lfunc.module.get_or_insert_function(functy, '__llrt_sdiv64')
    umod64 = lfunc.module.get_or_insert_function(functy, '__llrt_umod64')
    smod64 = lfunc.module.get_or_insert_function(functy, '__llrt_smod64')

    builder = lc.Builder.new(lfunc.entry_basic_block)
    for bb in lfunc.basic_blocks:
        for inst in bb.instructions:
            if inst.opcode_name == 'sdiv' and inst.type == int64:
                _replace_with(builder, inst, sdiv64)
            elif inst.opcode_name == 'udiv' and inst.type == int64:
                _replace_with(builder, inst, udiv64)
            elif inst.opcode_name == 'srem' and inst.type == int64:
                _replace_with(builder, inst, smod64)
            elif inst.opcode_name == 'urem' and inst.type == int64:
                _replace_with(builder, inst, umod64)

def _replace_with(builder, inst, func):
    '''Replace instruction with a call to the function with the same operands
    as arguments.
    '''
    builder.position_before(inst)
    replacement = builder.call(func, inst.operands)
    inst.replace_all_uses_with(replacement._ptr)
    inst.erase_from_parent()

def load(arch):
    '''Load the LLRT module corresponding to the given architecture
    Creates a new module and optimizes it using the information from
    the host machine.
    '''
    if arch != 'x86_64':
        arch = 'x86'
    path = os.path.join(os.path.dirname(__file__), 'llrt', 'llrt_%s.ll' % arch)
    with open(path) as fin:
        lib = lc.Module.from_assembly(fin)

    # run passes to optimize
    tm = le.TargetMachine.new()
    pms = lp.build_pass_managers(tm, opt=3, fpm=False)
    pms.pm.run(lib)
    return lib

class LLRT(object):
    def __init__(self):
        arch = le.get_default_triple().split('-', 1)[0]
        self.module = load(arch)
        self.engine = le.EngineBuilder.new(self.module).opt(3).create()
        self.installed_symbols = set()

    def install_symbols(self):
        '''Bind all the external symbols to the global symbol map.
        Any future reference to these symbols will be automatically resolved
        by LLVM.
        '''
        for lfunc in self.module.functions:
            if lfunc.linkage == lc.LINKAGE_EXTERNAL:
                mangled = '__llrt_' + lfunc.name
                self.installed_symbols.add(mangled)
                ptr = self.engine.get_pointer_to_function(lfunc)
                le.dylib_add_symbol(mangled, ptr)

    def uninstall_symbols(self):
        for sym in self.installed_symbols:
            le.dylib_add_symbol(sym, 0)



########NEW FILE########
__FILENAME__ = passes
#
# Copyright (c) 2008-10, Mahadevan R All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#  * Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
#
#  * Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
#  * Neither the name of this software, nor the names of its
#    contributors may be used to endorse or promote products derived from
#    this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#

"""Pass managers and passes.

This module provides the LLVM pass managers and the passes themselves.
All transformation passes listed at http://www.llvm.org/docs/Passes.html
are available.
"""

import llvm                 # top-level, for common stuff
import llvm.core as core    # module, function etc.
from llvmpy import api

#===----------------------------------------------------------------------===
# Pass manager builder
#===----------------------------------------------------------------------===

class PassManagerBuilder(llvm.Wrapper):
    @staticmethod
    def new():
        return PassManagerBuilder(api.llvm.PassManagerBuilder.new())

    def populate(self, pm):
        if isinstance(pm, FunctionPassManager):
            self._ptr.populateFunctionPassManager(pm._ptr)
        else:
            self._ptr.populateModulePassManager(pm._ptr)

    @property
    def opt_level(self):
        return self._ptr.OptLevel

    @opt_level.setter
    def opt_level(self, optlevel):
        self._ptr.OptLevel = optlevel

    @property
    def size_level(self):
        return self._ptr.SizeLevel

    @size_level.setter
    def size_level(self, sizelevel):
        self._ptr.SizeLevel = sizelevel

    if llvm.version >= (3, 3):
        @property
        def bbvectorize(self):
            return self._ptr.BBVectorize

        @bbvectorize.setter
        def bbvectorize(self, enable):
            self._ptr.BBVectorize = enable

        vectorize = bbvectorize

        @property
        def slpvectorize(self):
            return self._ptr.SLPVectorize

        @slpvectorize.setter
        def slpvectorize(self, enable):
            self._ptr.SLPVectorize = enable

    else:
        @property
        def vectorize(self):
            return self._ptr.Vectorize

        @vectorize.setter
        def vectorize(self, enable):
            self._ptr.Vectorize = enable


    @property
    def loop_vectorize(self):
        try:
            return self._ptr.LoopVectorize
        except AttributeError:
            return False

    @loop_vectorize.setter
    def loop_vectorize(self, enable):
        if llvm.version >= (3, 2):
            self._ptr.LoopVectorize = enable
        elif enable:
            warnings.warn("Ignored. LLVM-3.1 & prior do not support loop vectorizer.")

    @property
    def disable_unit_at_a_time(self):
        return self._ptr.DisableUnitAtATime

    @disable_unit_at_a_time.setter
    def disable_unit_at_a_time(self, disable):
        self._ptr.DisableUnitAtATime = disable

    @property
    def disable_unroll_loops(self):
        return self._ptr.DisableUnrollLoops

    @disable_unroll_loops.setter
    def disable_unroll_loops(self, disable):
        self._ptr.DisableUnrollLoops = disable

    if llvm.version <= (3, 3):
        @property
        def disable_simplify_lib_calls(self):
            return self._ptr.DisableSimplifyLibCalls

        @disable_simplify_lib_calls.setter
        def disable_simplify_lib_calls(self, disable):
            self._ptr.DisableSimplifyLibCalls = disable

    def use_inliner_with_threshold(self, threshold):
        self._ptr.Inliner = api.llvm.createFunctionInliningPass(threshold)


#===----------------------------------------------------------------------===
# Pass manager
#===----------------------------------------------------------------------===

class PassManager(llvm.Wrapper):

    @staticmethod
    def new():
        return PassManager(api.llvm.PassManager.new())

    def add(self, pass_obj):
        '''Add a pass to the pass manager.

        pass_obj --- Either a Pass instance, a string name of a pass
        '''
        if isinstance(pass_obj, Pass):
            self._ptr.add(pass_obj._ptr)
        else:
            self._add_pass(str(pass_obj))

    def _add_pass(self, pass_name):
        passreg = api.llvm.PassRegistry.getPassRegistry()
        a_pass = passreg.getPassInfo(pass_name).createPass()
        if not a_pass:
            assert pass_name not in PASSES, "Registered but not found?"
            raise llvm.LLVMException('Invalid pass name "%s"' % pass_name)
        self._ptr.add(a_pass)

    def run(self, module):
        return self._ptr.run(module._ptr)

class FunctionPassManager(PassManager):

    @staticmethod
    def new(module):
        ptr = api.llvm.FunctionPassManager.new(module._ptr)
        return FunctionPassManager(ptr)

    def __init__(self, ptr):
        PassManager.__init__(self, ptr)

    def initialize(self):
        self._ptr.doInitialization()

    def run(self, fn):
        return self._ptr.run(fn._ptr)

    def finalize(self):
        self._ptr.doFinalization()

#===----------------------------------------------------------------------===
# Passes
#===----------------------------------------------------------------------===

class Pass(llvm.Wrapper):
    '''Pass Inferface
        '''

    @staticmethod
    def new(name):
        '''Create a new pass by name.

            Note: Not all pass has a default constructor.  LLVM will kill
            the process if an the pass requires arguments to construct.
            The error cannot be caught.
            '''
        passreg = api.llvm.PassRegistry.getPassRegistry()
        a_pass = passreg.getPassInfo(name).createPass()
        p = Pass(a_pass)
        p.__name = name
        return p

    @property
    def name(self):
        '''The name used in PassRegistry.
        '''
        try:
            return self.__name
        except AttributeError:
            return

    @property
    def description(self):
        return self._ptr.getPassName()

    def dump(self):
        return self._ptr.dump()

#===----------------------------------------------------------------------===
# Target data
#===----------------------------------------------------------------------===

class TargetData(Pass):

    @staticmethod
    def new(strrep):
        ptr = api.llvm.DataLayout.new(strrep)
        return TargetData(ptr)

    def clone(self):
        return TargetData.new(str(self))

    def __str__(self):
        return self._ptr.getStringRepresentation()

    @property
    def byte_order(self):
        if self._ptr.isLittleEndian():
            return 1
        else:
            return 0

    @property
    def pointer_size(self):
        return self._ptr.getPointerSize()

    @property
    def target_integer_type(self):
        context = api.llvm.getGlobalContext()
        return api.llvm.IntegerType(api.llvm.Type.getInt32Ty(context))

    def size(self, ty):
        return self._ptr.getTypeSizeInBits(ty._ptr)

    def store_size(self, ty):
        return self._ptr.getTypeStoreSize(ty._ptr)

    def abi_size(self, ty):
        return self._ptr.getTypeAllocSize(ty._ptr)

    def abi_alignment(self, ty):
        return self._ptr.getABITypeAlignment(ty._ptr)

    def callframe_alignment(self, ty):
        return self._ptr.getCallFrameTypeAlignment(ty._ptr)

    def preferred_alignment(self, ty_or_gv):
        if isinstance(ty_or_gv, core.Type):
            return self._ptr.getPrefTypeAlignment(ty_or_gv._ptr)
        elif isinstance(ty_or_gv, core.GlobalVariable):
            return self._ptr.getPreferredAlignment(ty_or_gv._ptr)
        else:
            raise core.LLVMException("argument is neither a type nor a global variable")

    def element_at_offset(self, ty, ofs):
        return self._ptr.getStructLayout(ty._ptr).getElementContainingOffset(ofs)

    def offset_of_element(self, ty, el):
        return self._ptr.getStructLayout(ty._ptr).getElementOffset(el)

#===----------------------------------------------------------------------===
# Target Library Info
#===----------------------------------------------------------------------===

class TargetLibraryInfo(Pass):
    @staticmethod
    def new(triple):
        triple = api.llvm.Triple.new(str(triple))
        ptr = api.llvm.TargetLibraryInfo.new(triple)
        return TargetLibraryInfo(ptr)

#===----------------------------------------------------------------------===
# Target Transformation Info
#===----------------------------------------------------------------------===

class TargetTransformInfo(Pass):
    @staticmethod
    def new(targetmachine):
        scalartti = targetmachine._ptr.getScalarTargetTransformInfo()
        vectortti = targetmachine._ptr.getVectorTargetTransformInfo()
        ptr = api.llvm.TargetTransformInfo.new(scalartti, vectortti)
        return TargetTransformInfo(ptr)


#===----------------------------------------------------------------------===
# Helpers
#===----------------------------------------------------------------------===

def build_pass_managers(tm, opt=2, size=0, loop_vectorize=False,
                        slp_vectorize=False, vectorize=False,
                        inline_threshold=None, pm=True, fpm=True, mod=None):
    '''
        tm --- The TargetMachine for which the passes are optimizing for.
        The TargetMachine must stay alive until the pass managers
        are removed.
        opt --- [0-3] Optimization level. Default to 2.
        size --- [0-2] Optimize for size. Default to 0.
        loop_vectorize --- [boolean] Whether to use loop-vectorizer.
        vectorize --- [boolean] Whether to use basic-block vectorizer.
        inline_threshold --- [int] Threshold for the inliner.
        features --- [str] CPU feature string.
        pm --- [boolean] Whether to build a module-level pass-manager.
        fpm --- [boolean] Whether to build a function-level pass-manager.
        mod --- [Module] The module object for the FunctionPassManager.
        '''
    if inline_threshold is None:
        if 0 < opt < 3:
            inline_threshold = 225

        if size == 1:
            inline_threshold = 75
        elif size == 2:
            inline_threshold = 25

        if opt >= 3:
            inline_threshold = 275

    if pm:
        pm = PassManager.new()
    if fpm:
        if not mod:
            raise TypeError("Keyword 'mod' must be defined")
        fpm = FunctionPassManager.new(mod)

    # Populate PassManagers with target specific passes
    pmb = PassManagerBuilder.new()
    pmb.opt_level = opt
    pmb.vectorize = vectorize
    pmb.loop_vectorize = loop_vectorize
    if llvm.version >= (3, 3):
        pmb.slp_vectorize = slp_vectorize
    if inline_threshold:
        pmb.use_inliner_with_threshold(inline_threshold)
    if pm:
        pm.add(tm.target_data.clone())
        pm.add(TargetLibraryInfo.new(tm.triple))
        if llvm.version <= (3, 2):
            pm.add(TargetTransformInfo.new(tm))
        else:
            tm.add_analysis_passes(pm)
        pmb.populate(pm)

    if fpm:
        fpm.add(tm.target_data.clone())
        fpm.add(TargetLibraryInfo.new(tm.triple))
        if llvm.version <= (3, 2):
            fpm.add(TargetTransformInfo.new(tm))
        else:
            tm.add_analysis_passes(fpm)
        pmb.populate(fpm)

    from collections import namedtuple
    return namedtuple('passmanagers', ['pm', 'fpm'])(pm=pm, fpm=fpm)

#===----------------------------------------------------------------------===
# Misc.
#===----------------------------------------------------------------------===

# Intialize passes
PASSES = None

def _dump_all_passes():
    passreg = api.llvm.PassRegistry.getPassRegistry()
    for name, desc in passreg.enumerate():
        yield name, desc

def _initialize_passes():
    global PASSES

    passreg = api.llvm.PassRegistry.getPassRegistry()

    api.llvm.initializeCore(passreg)
    api.llvm.initializeScalarOpts(passreg)
    api.llvm.initializeVectorization(passreg)
    api.llvm.initializeIPO(passreg)
    api.llvm.initializeAnalysis(passreg)
    api.llvm.initializeIPA(passreg)
    api.llvm.initializeTransformUtils(passreg)
    api.llvm.initializeInstCombine(passreg)
    api.llvm.initializeInstrumentation(passreg)
    api.llvm.initializeTarget(passreg)

    PASSES = dict(_dump_all_passes())

    # build globals
    def transform(name):
        return "PASS_%s" % (name.upper().replace('-', '_'))

    global_symbols = globals()
    for i in PASSES:
        assert i not in global_symbols
        global_symbols[transform(i)] = i

_initialize_passes()


########NEW FILE########
__FILENAME__ = target
import llvm
from llvmpy import api, extra
from io import BytesIO
import contextlib
from llvm.passes import TargetData

#===----------------------------------------------------------------------===
# Enumerations
#===----------------------------------------------------------------------===

BO_BIG_ENDIAN       = 0
BO_LITTLE_ENDIAN    = 1

# CodeModel
CM_DEFAULT      = api.llvm.CodeModel.Model.Default
CM_JITDEFAULT   = api.llvm.CodeModel.Model.JITDefault
CM_SMALL        = api.llvm.CodeModel.Model.Small
CM_KERNEL       = api.llvm.CodeModel.Model.Kernel
CM_MEDIUM       = api.llvm.CodeModel.Model.Medium
CM_LARGE        = api.llvm.CodeModel.Model.Large

# Reloc
RELOC_DEFAULT        = api.llvm.Reloc.Model.Default
RELOC_STATIC         = api.llvm.Reloc.Model.Static
RELOC_PIC            = api.llvm.Reloc.Model.PIC_
RELOC_DYNAMIC_NO_PIC = api.llvm.Reloc.Model.DynamicNoPIC

def initialize_all():
    api.llvm.InitializeAllTargets()
    api.llvm.InitializeAllTargetInfos()
    api.llvm.InitializeAllTargetMCs()
    api.llvm.InitializeAllAsmPrinters()
    api.llvm.InitializeAllDisassemblers()
    api.llvm.InitializeAllAsmParsers()

def initialize_target(target, noraise=False):
    """Initialize target by name.
    It is safe to initialize the same target multiple times.
    """
    prefix = 'LLVMInitialize'
    postfixes = ['Target', 'TargetInfo', 'TargetMC', 'AsmPrinter', 'AsmParser']
    try:
        for postfix in postfixes:
            getattr(api, '%s%s%s' % (prefix, target, postfix))()
    except AttributeError:
        if noraise:
            return False
        else:
            raise
    else:
        return True


def print_registered_targets():
    '''
    Note: print directly to stdout
    '''
    api.llvm.TargetRegistry.printRegisteredTargetsForVersion()

def get_host_cpu_name():
    '''return the string name of the host CPU
    '''
    return api.llvm.sys.getHostCPUName()

def get_default_triple():
    '''return the target triple of the host in str-rep
    '''
    return api.llvm.sys.getDefaultTargetTriple()

class TargetMachine(llvm.Wrapper):

    @staticmethod
    def new(triple='', cpu='', features='', opt=2, cm=CM_DEFAULT,
            reloc=RELOC_DEFAULT):
        if not triple:
            triple = get_default_triple()
        if not cpu:
            cpu = get_host_cpu_name()
        with contextlib.closing(BytesIO()) as error:
            target = api.llvm.TargetRegistry.lookupTarget(triple, error)
            if not target:
                raise llvm.LLVMException(error.getvalue())
            if not target.hasTargetMachine():
                raise llvm.LLVMException(target, "No target machine.")
            target_options = api.llvm.TargetOptions.new()
            tm = target.createTargetMachine(triple, cpu, features,
                                            target_options,
                                            reloc, cm, opt)
            if not tm:
                raise llvm.LLVMException("Cannot create target machine")
            return TargetMachine(tm)

    @staticmethod
    def lookup(arch, cpu='', features='', opt=2, cm=CM_DEFAULT,
               reloc=RELOC_DEFAULT):
        '''create a targetmachine given an architecture name

            For a list of architectures,
            use: `llc -help`

            For a list of available CPUs,
            use: `llvm-as < /dev/null | llc -march=xyz -mcpu=help`

            For a list of available attributes (features),
            use: `llvm-as < /dev/null | llc -march=xyz -mattr=help`
            '''
        triple = api.llvm.Triple.new()
        with contextlib.closing(BytesIO()) as error:
            target = api.llvm.TargetRegistry.lookupTarget(arch, triple, error)
            if not target:
                raise llvm.LLVMException(error.getvalue())
            if not target.hasTargetMachine():
                raise llvm.LLVMException(target, "No target machine.")
            target_options = api.llvm.TargetOptions.new()
            tm = target.createTargetMachine(str(triple), cpu, features,
                                            target_options,
                                            reloc, cm, opt)
            if not tm:
                raise llvm.LLVMException("Cannot create target machine")
            return TargetMachine(tm)

    @staticmethod
    def x86():
        return TargetMachine.lookup('x86')

    @staticmethod
    def x86_64():
        return TargetMachine.lookup('x86-64')

    @staticmethod
    def arm():
        return TargetMachine.lookup('arm')

    @staticmethod
    def thumb():
        return TargetMachine.lookup('thumb')

    def _emit_file(self, module, cgft):
        pm = api.llvm.PassManager.new()
        os = extra.make_raw_ostream_for_printing()
        pm.add(api.llvm.DataLayout.new(str(self.target_data)))
        failed = self._ptr.addPassesToEmitFile(pm, os, cgft)
        pm.run(module)


        CGFT = api.llvm.TargetMachine.CodeGenFileType
        if cgft == CGFT.CGFT_ObjectFile:
            return os.bytes()
        else:
            return os.str()

    def emit_assembly(self, module):
        '''returns byte string of the module as assembly code of the target machine
        '''
        CGFT = api.llvm.TargetMachine.CodeGenFileType
        return self._emit_file(module._ptr, CGFT.CGFT_AssemblyFile)

    def emit_object(self, module):
        '''returns byte string of the module as native code of the target machine
        '''
        CGFT = api.llvm.TargetMachine.CodeGenFileType
        return self._emit_file(module._ptr, CGFT.CGFT_ObjectFile)

    @property
    def target_data(self):
        '''get target data of this machine
        '''
        return TargetData(self._ptr.getDataLayout())

    @property
    def target_name(self):
        return self._ptr.getTarget().getName()

    @property
    def target_short_description(self):
        return self._ptr.getTarget().getShortDescription()

    @property
    def triple(self):
        return self._ptr.getTargetTriple()

    @property
    def cpu(self):
        return self._ptr.getTargetCPU()

    @property
    def feature_string(self):
        return self._ptr.getTargetFeatureString()

    @property
    def target(self):
        return self._ptr.getTarget()

    if llvm.version >= (3, 3):
        def add_analysis_passes(self, pm):
            self._ptr.addAnalysisPasses(pm._ptr)

    if llvm.version >= (3, 4):
        @property
        def reg_info(self):
            mri = self._ptr.getRegisterInfo()
            if not mri:
                raise llvm.LLVMException("no reg info for this machine")

            return mri

        @property
        def subtarget_info(self):
            sti = self._ptr.getSubtargetImpl()
            if not sti:
                raise llvm.LLVMException("no subtarget info for this machine")

            return sti

        @property
        def asm_info(self):
            ai = self._ptr.getMCAsmInfo()
            if not ai:
                raise llvm.LLVMException("no asm info for this machine")

            return ai

        @property
        def instr_info(self):
            ii = self._ptr.getInstrInfo()
            if not ii:
                raise llvm.LLVMException("no instr info for this machine")

            return ii

        @property
        def instr_analysis(self):
            if not getattr(self, '_mia', False):
                self._mia = self.target.createMCInstrAnalysis(self.instr_info)
            if not self._mia:
                raise llvm.LLVMException("no instr analysis for this machine")

            return self._mia

        @property
        def disassembler(self):
            if not getattr(self, '_dasm', False):
                self._dasm = self.target.createMCDisassembler(self.subtarget_info)
            if not self._dasm:
                raise llvm.LLVMException("no disassembler for this machine")

            return self._dasm

        @property
        def inst_printer(self):
            if not getattr(self, '_mip', False):
                self._mip = self.target.createMCInstPrinter(
                                     self.asm_info.getAssemblerDialect(),
                                     self.asm_info,
                                     self.instr_info,
                                     self.reg_info,
                                     self.subtarget_info
                                     )
            if not self._mip:
                raise llvm.LLVMException("no instr printer for this machine")

            return self._mip

        def is_little_endian(self):
            return self.asm_info.isLittleEndian()


########NEW FILE########
__FILENAME__ = tbaa
from llvm.core import *

class TBAABuilder(object):
    '''Simplify creation of TBAA metadata.

    Each TBAABuidler object operates on a module.
    User can create multiple TBAABuilder on a module
    '''

    def __init__(self, module, rootid):
        '''
        module --- the module to use.
        root --- string name to identify the TBAA root.
        '''
        self.__module = module
        self.__rootid = rootid
        self.__rootmd = self.__new_md(rootid)

    @classmethod
    def new(cls, module, rootid):
        return cls(module, rootid)

    def get_node(self, name, parent=None, const=False):
        '''Returns a MetaData object representing a TBAA node.

        Use loadstore_instruction.set_metadata('tbaa', node) to
        bind a type to a memory.
        '''
        parent = parent or self.root
        const = Constant.int(Type.int(), int(bool(const)))
        return self.__new_md(name, parent, const)

    @property
    def module(self):
        return self.__module

    @property
    def root(self):
        return self.__rootmd

    @property
    def root_name(self):
        return self.__rootid

    def __new_md(self, *args):
        contents = list(args)
        for i, v in enumerate(contents):
            if isinstance(v, str):
                contents[i] = MetaDataString.get(self.module, v)
        return MetaData.get(self.module, contents)


########NEW FILE########
__FILENAME__ = support
from __future__ import print_function, division
import sys
import platform
import unittest
import contextlib
import types
from llvm.tests import tests, isolated_tests # re-expose symbol

IS_PY3K = sys.version_info[0] >= 3
BITS = tuple.__itemsize__ * 8
OS = sys.platform
MACHINE = platform.machine()
INTEL_CPUS = 'i386', 'x86_64'

if sys.version_info[:2] <= (2, 6):
    # create custom TestCase
    class _TestCase(unittest.TestCase):
        def assertIn(self, item, container):
            self.assertTrue(item in container)

        def assertNotIn(self, item, container):
            self.assertFalse(item in container)

        def assertLess(self, a, b):
            self.assertTrue(a < b)

        def assertIs(self, a, b):
            self.assertTrue(a is b)

        @contextlib.contextmanager
        def assertRaises(self, exc):
            try:
                yield
            except exc:
                pass
            else:
                raise self.failureException("Did not raise %s" % exc)

else:
    _TestCase = unittest.TestCase

class TestCase(_TestCase):
    def assertClose(self, got, expect):
        rel = abs(got - expect) / expect
        self.assertTrue(rel < 1e-6, 'relative error = %f' % rel)

#-------------------------------------------------------------------------------
# Tests decorators

def _skipped(name, msg):
    def _test(self):
        if hasattr(unittest, 'SkipTest'):
            raise unittest.SkipTest(msg)
        else:
            print('skipped %s' % name, msg)
    return _test

def skip_if(cond, msg=''):
    def skipper(test):
        if not isinstance(test, types.FunctionType):
            repl = None
        else:
            repl = _skipped(test, msg)
        return repl if cond else test
    return skipper

skip_if_not_64bits = skip_if(BITS != 64, msg='skipped not 64-bit')

skip_if_not_32bits = skip_if(BITS != 32, msg='skipped not 32-bits')

skip_if_win32 = skip_if(OS.startswith('win32'), msg='skipped win32')

skip_if_not_win32 = skip_if(not OS.startswith('win32'),
                            msg='skipped not win32')
skip_if_not_intel_cpu = skip_if(MACHINE not in INTEL_CPUS,
                                msg='skipped not Intel CPU')



########NEW FILE########
__FILENAME__ = test_alloca
import unittest
from llvm.core import Type, Module, Builder, Constant
from .support import TestCase, tests

class TestAlloca(TestCase):
    def test_alloca_alignment(self):
        m = Module.new('')
        f = m.add_function(Type.function(Type.void(), []), "foo")
        b = Builder.new(f.append_basic_block(''))
        inst = b.alloca(Type.int(32))
        inst.alignment = 4
        b.ret_void()
        m.verify()

        self.assertTrue(inst.is_static)
        self.assertFalse(inst.is_array)
        self.assertEqual(inst.alignment, 4)
        self.assertEqual(str(inst.array_size), 'i32 1')

tests.append(TestAlloca)

if __name__ == '__main__':
    unittest.main()


########NEW FILE########
__FILENAME__ = test_arg_attr
import unittest
from llvm.core import Module, Type
import llvm.core as lc
from .support import TestCase, tests

class TestArgAttr(TestCase):
    def test_arg_attr(self):
        m = Module.new('oifjda')
        vptr = Type.pointer(Type.float())
        fnty = Type.function(Type.void(), [vptr] * 5)
        func = m.add_function(fnty, 'foo')
        attrs = [lc.ATTR_STRUCT_RET, lc.ATTR_BY_VAL, lc.ATTR_NEST,
                 lc.ATTR_NO_ALIAS, lc.ATTR_NO_CAPTURE]
        for i, attr in enumerate(attrs):
            arg = func.args[i]
            self.assertEqual(i, arg.arg_no)
            arg.add_attribute(attr)
            self.assertTrue(attr in func.args[i])

tests.append(TestArgAttr)

if __name__ == '__main__':
    unittest.main()


########NEW FILE########
__FILENAME__ = test_arith
import unittest
import llvm
from llvm.core import (Module, Type, Builder)
from llvm.ee import EngineBuilder
from .support import TestCase, tests, skip_if, skip_if_not_64bits

@skip_if(llvm.version < (3, 3))
class TestArith(TestCase):
    '''
    Test basic arithmetic support with LLVM MCJIT
    '''
    def func_template(self, ty, op):
        m = Module.new('dofjaa')
        fnty = Type.function(ty, [ty, ty])
        fn = m.add_function(fnty, 'foo')
        bldr = Builder.new(fn.append_basic_block(''))
        bldr.ret(getattr(bldr, op)(*fn.args))

        engine = EngineBuilder.new(m).mcjit(True).create()
        ptr = engine.get_pointer_to_function(fn)

        from ctypes import c_uint32, c_uint64, c_float, c_double, CFUNCTYPE

        maptypes = {
            Type.int(32): c_uint32,
            Type.int(64): c_uint64,
            Type.float(): c_float,
            Type.double(): c_double,
        }
        cty = maptypes[ty]
        prototype = CFUNCTYPE(*[cty] * 3)
        callee = prototype(ptr)
        callee(12, 23)

    def template(self, iop, fop):
        inttys = [Type.int(32), Type.int(64)]
        flttys = [Type.float(), Type.double()]

        if iop:
            for ty in inttys:
                self.func_template(ty, iop)
        if fop:
            for ty in flttys:
                self.func_template(ty, fop)

    def test_add(self):
        self.template('add', 'fadd')

    def test_sub(self):
        self.template('sub', 'fsub')

    def test_mul(self):
        self.template('mul', 'fmul')

    @skip_if_not_64bits
    def test_div(self):
        '''
        known failure due to unresolved external symbol __udivdi3
        '''
        self.template('udiv', None) # 'fdiv')

    @skip_if_not_64bits
    def test_rem(self):
        '''
        known failure due to unresolved external symbol __umoddi3
        '''
        self.template('urem', None) # 'frem')

tests.append(TestArith)

if __name__ == '__main__':
    unittest.main()


########NEW FILE########
__FILENAME__ = test_asm
import os
import unittest
import tempfile
import shutil
from llvm.core import Module, Type
from .support import TestCase, tests

class TestAsm(TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def create_module(self):
        # create a module
        m = Module.new('module1')
        m.add_global_variable(Type.int(), 'i')
        return m

    def test_asm_roundtrip(self):
        m = self.create_module()

        # write it's assembly representation to a file
        asm = str(m)

        testasm_ll = os.path.join(self.tmpdir, 'testasm.ll')
        with open(testasm_ll, "w") as fout:
            fout.write(asm)

        # read it back into a module
        with open(testasm_ll) as fin:
            m2 = Module.from_assembly(fin)
            # The default `m.id` is '<string>'.
            m2.id = m.id # Copy the name from `m`

        self.assertEqual(str(m2).strip(), asm.strip())

    def test_bitcode_roundtrip(self):
        m = self.create_module()

        testasm_bc = os.path.join(self.tmpdir, 'testasm.bc')
        with open(testasm_bc, "wb") as fout:
            m.to_bitcode(fout)

        # read it back into a module
        with open(testasm_bc, "rb") as fin:
            m2 = Module.from_bitcode(fin)
            # The default `m.id` is '<string>'.
            m2.id = m.id # Copy the name from `m`

        with open(testasm_bc, "rb") as fin:
            m3 = Module.from_bitcode(fin.read())
            # The default `m.id` is '<string>'.
            m3.id = m.id # Copy the name from `m`

        self.assertEqual(str(m2).strip(), str(m).strip())
        self.assertEqual(str(m3).strip(), str(m).strip())

    def test_to_bitcode(self):
        m = self.create_module()
        testasm_bc = os.path.join(self.tmpdir, 'testasm.bc')
        with open(testasm_bc, "wb") as fout:
            m.to_bitcode(fout)
        with open(testasm_bc, "rb") as fin:
            self.assertEqual(fin.read(), m.to_bitcode())


tests.append(TestAsm)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_atomic
import unittest
from llvm.core import (Module, Type, Builder, Constant)
from .support import TestCase, tests

class TestAtomic(TestCase):
    orderings = ['unordered', 'monotonic', 'acquire',
                 'release', 'acq_rel', 'seq_cst']

    atomic_op = ['xchg', 'add', 'sub', 'and', 'nand', 'or', 'xor',
                 'max', 'min', 'umax', 'umin']

    def test_atomic_cmpxchg(self):
        mod = Module.new('mod')
        functype = Type.function(Type.void(), [])
        func = mod.add_function(functype, name='foo')
        bb = func.append_basic_block('entry')
        bldr = Builder.new(bb)
        ptr = bldr.alloca(Type.int())

        old = bldr.load(ptr)
        new = Constant.int(Type.int(), 1234)

        for ordering in self.orderings:
            inst = bldr.atomic_cmpxchg(ptr, old, new, ordering)
            self.assertEqual(ordering, str(inst).strip().split(' ')[-1])

        inst = bldr.atomic_cmpxchg(ptr, old, new, ordering, crossthread=False)
        self.assertEqual('singlethread', str(inst).strip().split(' ')[-2])

    def test_atomic_rmw(self):
        mod = Module.new('mod')
        functype = Type.function(Type.void(), [])
        func = mod.add_function(functype, name='foo')
        bb = func.append_basic_block('entry')
        bldr = Builder.new(bb)
        ptr = bldr.alloca(Type.int())

        val = Constant.int(Type.int(), 1234)

        for ordering in self.orderings:
            inst = bldr.atomic_rmw('xchg', ptr, val, ordering)
            self.assertEqual(ordering, str(inst).split(' ')[-1])

        for op in self.atomic_op:
            inst = bldr.atomic_rmw(op, ptr, val, ordering)
            self.assertEqual(op, str(inst).strip().split(' ')[3])

        inst = bldr.atomic_rmw('xchg', ptr, val, ordering, crossthread=False)
        self.assertEqual('singlethread', str(inst).strip().split(' ')[-2])

        for op in self.atomic_op:
            atomic_op = getattr(bldr, 'atomic_%s' % op)
            inst = atomic_op(ptr, val, ordering)
            self.assertEqual(op, str(inst).strip().split(' ')[3])

    def test_atomic_ldst(self):
        mod = Module.new('mod')
        functype = Type.function(Type.void(), [])
        func = mod.add_function(functype, name='foo')
        bb = func.append_basic_block('entry')
        bldr = Builder.new(bb)
        ptr = bldr.alloca(Type.int())

        for ordering in self.orderings:
            loaded = bldr.atomic_load(ptr, ordering)
            self.assert_('load atomic' in str(loaded))
            self.assertEqual(ordering,
                             str(loaded).strip().split(' ')[-3].rstrip(','))
            self.assert_('align 1' in str(loaded))

            stored = bldr.atomic_store(loaded, ptr, ordering)
            self.assert_('store atomic' in str(stored))
            self.assertEqual(ordering,
                             str(stored).strip().split(' ')[-3].rstrip(','))
            self.assert_('align 1' in str(stored))

            fenced = bldr.fence(ordering)
            self.assertEqual(['fence', ordering],
                             str(fenced).strip().split(' '))

tests.append(TestAtomic)

if __name__ == '__main__':
    unittest.main()


########NEW FILE########
__FILENAME__ = test_attr
import unittest
try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO

from llvm.core import Module
from .support import TestCase, tests

class TestAttr(TestCase):
    def make_module(self):
        test_module = """
            define void @sum(i32*, i32*) {
            entry:
                ret void
            }
        """
        buf = StringIO(test_module)
        return Module.from_assembly(buf)

    def test_align(self):
        m = self.make_module()
        f = m.get_function_named('sum')
        f.args[0].alignment = 16
        self.assert_("align 16" in str(f))
        self.assertEqual(f.args[0].alignment, 16)

tests.append(TestAttr)


if __name__ == '__main__':
    unittest.main()


########NEW FILE########
__FILENAME__ = test_cmp
import unittest
from llvm.core import (Module, Type, Builder, Constant)
import llvm.core as lc
from .support import TestCase, tests

class TestCmp(TestCase):
    def test_arg_attr(self):
        m = Module.new('oifjda')
        fnty = Type.function(Type.void(), [Type.int()])
        func = m.add_function(fnty, 'foo')
        bb = func.append_basic_block('')
        bldr = Builder.new(bb)

        cmpinst = bldr.icmp(lc.ICMP_ULE, func.args[0],
                            Constant.int(Type.int(), 123))
        self.assertTrue(repr(cmpinst.predicate).startswith('ICMP_ULE'))
        self.assertEqual(cmpinst.predicate, lc.ICMP_ULE)
        bldr.ret_void()

        func.verify()

tests.append(TestCmp)

if __name__ == '__main__':
    unittest.main()


########NEW FILE########
__FILENAME__ = test_const_expr
import unittest
from llvm.core import (Module, Type, Builder, Constant)
import llvm.core as lc

from .support import TestCase, tests

class TestConstExpr(TestCase):

    def test_constexpr_opcode(self):
        mod = Module.new('test_constexpr_opcode')
        func = mod.add_function(Type.function(Type.void(), []), name="foo")
        builder = Builder.new(func.append_basic_block('entry'))
        a = builder.inttoptr(Constant.int(Type.int(), 123),
                             Type.pointer(Type.int()))
        self.assertTrue(isinstance(a, lc.ConstantExpr))
        self.assertEqual(a.opcode, lc.OPCODE_INTTOPTR)
        self.assertEqual(a.opcode_name, "inttoptr")

tests.append(TestConstExpr)

if __name__ == '__main__':
    unittest.main()


########NEW FILE########
__FILENAME__ = test_cpu_support
import unittest
import math
from llvm.core import (Module, Type, Function, Builder,
                       Constant)
from llvm.ee import EngineBuilder
import llvm.core as lc
import llvm.ee as le
from llvm.workaround.avx_support import detect_avx_support
from .support import TestCase, tests, skip_if_not_intel_cpu, skip_if

@skip_if_not_intel_cpu
class TestCPUSupport(TestCase):

    def _build_test_module(self):
        mod     = Module.new('test')

        float   = Type.double()
        mysinty = Type.function( float, [float] )
        mysin   = mod.add_function(mysinty, "mysin")
        block   = mysin.append_basic_block("entry")
        b       = Builder.new(block)

        sqrt = Function.intrinsic(mod, lc.INTR_SQRT, [float])
        pow  = Function.intrinsic(mod, lc.INTR_POWI, [float])
        cos  = Function.intrinsic(mod, lc.INTR_COS,  [float])

        mysin.args[0].name = "x"
        x    = mysin.args[0]
        one  = Constant.real(float, "1")
        cosx = b.call(cos, [x], "cosx")
        cos2 = b.call(pow, [cosx, Constant.int(Type.int(), 2)], "cos2")
        onemc2 = b.fsub(one, cos2, "onemc2") # Should use fsub
        sin  = b.call(sqrt, [onemc2], "sin")
        b.ret(sin)
        return mod, mysin

    def _template(self, mattrs):
        mod, func = self._build_test_module()
        ee = self._build_engine(mod, mattrs=mattrs)
        arg = le.GenericValue.real(Type.double(), 1.234)
        retval = ee.run_function(func, [arg])

        golden = math.sin(1.234)
        answer = retval.as_real(Type.double())
        self.assertTrue(abs(answer-golden)/golden < 1e-5)


    def _build_engine(self, mod, mattrs):
        if mattrs:
            return EngineBuilder.new(mod).mattrs(mattrs).create()
        else:
            return EngineBuilder.new(mod).create()

    def test_cpu_support2(self):
        features = 'sse3', 'sse41', 'sse42', 'avx'
        mattrs = ','.join(map(lambda s: '-%s' % s, features))
        print('disable mattrs', mattrs)
        self._template(mattrs)

    def test_cpu_support3(self):
        features = 'sse41', 'sse42', 'avx'
        mattrs = ','.join(map(lambda s: '-%s' % s, features))
        print('disable mattrs', mattrs)
        self._template(mattrs)

    def test_cpu_support4(self):
        features = 'sse42', 'avx'
        mattrs = ','.join(map(lambda s: '-%s' % s, features))
        print('disable mattrs', mattrs)
        self._template(mattrs)

    def test_cpu_support5(self):
        features = 'avx',
        mattrs = ','.join(map(lambda s: '-%s' % s, features))
        print('disable mattrs', mattrs)
        self._template(mattrs)

    @skip_if(not detect_avx_support(), msg="no AVX support")
    def test_cpu_support6(self):
        features = []
        mattrs = ','.join(map(lambda s: '-%s' % s, features))
        print('disable mattrs', mattrs)
        self._template(mattrs)

tests.append(TestCPUSupport)

if __name__ == '__main__':
    unittest.main()


########NEW FILE########
__FILENAME__ = test_engine_builder
import unittest
from llvm.core import Module, Type, Builder, Constant
from llvm.ee import EngineBuilder
import llvm.ee as le
import llvmpy

from .support import TestCase, tests

class TestEngineBuilder(TestCase):

    def make_test_module(self):
        module = Module.new("testmodule")
        fnty = Type.function(Type.int(), [])
        function = module.add_function(fnty, 'foo')
        bb_entry = function.append_basic_block('entry')
        builder = Builder.new(bb_entry)
        builder.ret(Constant.int(Type.int(), 0xcafe))
        module.verify()
        return module

    def run_foo(self, ee, module):
        function = module.get_function_named('foo')
        retval = ee.run_function(function, [])
        self.assertEqual(retval.as_int(), 0xcafe)


    def test_enginebuilder_basic(self):
        module = self.make_test_module()
        self.assertTrue(llvmpy.capsule.has_ownership(module._ptr._ptr))
        ee = EngineBuilder.new(module).create()
        self.assertFalse(llvmpy.capsule.has_ownership(module._ptr._ptr))
        self.run_foo(ee, module)


    def test_enginebuilder_with_tm(self):
        tm = le.TargetMachine.new()
        module = self.make_test_module()
        self.assertTrue(llvmpy.capsule.has_ownership(module._ptr._ptr))
        ee = EngineBuilder.new(module).create(tm)
        self.assertFalse(llvmpy.capsule.has_ownership(module._ptr._ptr))
        self.run_foo(ee, module)

    def test_enginebuilder_force_jit(self):
        module = self.make_test_module()
        ee = EngineBuilder.new(module).force_jit().create()

        self.run_foo(ee, module)
#
#    def test_enginebuilder_force_interpreter(self):
#        module = self.make_test_module()
#        ee = EngineBuilder.new(module).force_interpreter().create()
#
#        self.run_foo(ee, module)

    def test_enginebuilder_opt(self):
        module = self.make_test_module()
        ee = EngineBuilder.new(module).opt(3).create()

        self.run_foo(ee, module)

tests.append(TestEngineBuilder)

if __name__ == '__main__':
    unittest.main()


########NEW FILE########
__FILENAME__ = test_exact
import unittest
from llvm.core import (Module, Type, Builder)
from .support import TestCase, tests

class TestExact(TestCase):
    def make_module(self):
        mod = Module.new('asdfa')
        fnty = Type.function(Type.void(), [Type.int()] * 2)
        func = mod.add_function(fnty, 'foo')
        bldr = Builder.new(func.append_basic_block(''))
        return mod, func, bldr

    def has_exact(self, inst, op):
        self.assertTrue(('%s exact' % op) in str(inst), "exact flag does not work")

    def _test_template(self, opf, opname):
        mod, func, bldr = self.make_module()
        a, b = func.args
        self.has_exact(opf(bldr, a, b, exact=True), opname)

    def test_udiv_exact(self):
        self._test_template(Builder.udiv, 'udiv')

    def test_sdiv_exact(self):
        self._test_template(Builder.sdiv, 'sdiv')

    def test_lshr_exact(self):
        self._test_template(Builder.lshr, 'lshr')

    def test_ashr_exact(self):
        self._test_template(Builder.ashr, 'ashr')

tests.append(TestExact)

if __name__ == '__main__':
    unittest.main()


########NEW FILE########
__FILENAME__ = test_execution_engine
import unittest
from llvm.core import Type
import llvm.core as lc
import llvm.ee as le

from .support import TestCase, tests

class TestExecutionEngine(TestCase):
    def test_get_pointer_to_global(self):
        module = lc.Module.new(str(self))
        gvar = module.add_global_variable(Type.int(), 'hello')
        X = 1234
        gvar.initializer = lc.Constant.int(Type.int(), X)

        ee = le.ExecutionEngine.new(module)
        ptr = ee.get_pointer_to_global(gvar)
        from ctypes import c_void_p, cast, c_int, POINTER
        casted = cast(c_void_p(ptr), POINTER(c_int))
        self.assertEqual(X, casted[0])

    def test_add_global_mapping(self):
        module = lc.Module.new(str(self))
        gvar = module.add_global_variable(Type.int(), 'hello')

        fnty = lc.Type.function(Type.int(), [])
        foo = module.add_function(fnty, name='foo')
        bldr = lc.Builder.new(foo.append_basic_block('entry'))
        bldr.ret(bldr.load(gvar))

        ee = le.ExecutionEngine.new(module)
        from ctypes import c_int, addressof, CFUNCTYPE
        value = 0xABCD
        value_ctype = c_int(value)
        value_pointer = addressof(value_ctype)

        ee.add_global_mapping(gvar, value_pointer)

        foo_addr = ee.get_pointer_to_function(foo)
        prototype = CFUNCTYPE(c_int)
        foo_callable = prototype(foo_addr)
        self.assertEqual(foo_callable(), value)

tests.append(TestExecutionEngine)

if __name__ == '__main__':
    unittest.main()


########NEW FILE########
__FILENAME__ = test_inlining
import unittest
from llvm.core import (Module, Type, Builder, Constant, inline_function)
from .support import TestCase, tests

class TestInlining(TestCase):
    def test_inline_call(self):
        mod = Module.new(__name__)
        callee = mod.add_function(Type.function(Type.int(), [Type.int()]),
                                  name='bar')

        builder = Builder.new(callee.append_basic_block('entry'))
        builder.ret(builder.add(callee.args[0], callee.args[0]))

        caller = mod.add_function(Type.function(Type.int(), []),
                                  name='foo')

        builder = Builder.new(caller.append_basic_block('entry'))
        callinst = builder.call(callee, [Constant.int(Type.int(), 1234)])
        builder.ret(callinst)

        pre_inlining = str(caller)
        self.assertIn('call', pre_inlining)

        self.assertTrue(inline_function(callinst))

        post_inlining = str(caller)
        self.assertNotIn('call', post_inlining)
        self.assertIn('2468', post_inlining)

tests.append(TestInlining)

if __name__ == '__main__':
    unittest.main()


########NEW FILE########
__FILENAME__ = test_intel_native_asm
import sys
import os
import unittest
from llvm.core import Builder, Module, Type
import llvm.core as lc
from .support import TestCase, skip_if_not_intel_cpu, isolated_tests

@skip_if_not_intel_cpu
class TestNativeAsm(TestCase):

    def test_asm(self):
        m = Module.new('module1')

        foo = m.add_function(Type.function(Type.int(),
                                           [Type.int(), Type.int()]),
                             name="foo")
        bldr = Builder.new(foo.append_basic_block('entry'))
        x = bldr.add(foo.args[0], foo.args[1])
        bldr.ret(x)

        att_syntax = m.to_native_assembly()
        os.environ["LLVMPY_OPTIONS"] = "-x86-asm-syntax=intel"
        lc.parse_environment_options(sys.argv[0], "LLVMPY_OPTIONS")
        intel_syntax = m.to_native_assembly()

        self.assertNotEqual(att_syntax, intel_syntax)

isolated_tests.append(__name__)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_intrinsic
import unittest
import sys
import math
from llvm.core import (Module, Type, Function, Builder, Constant)
import llvm.core as lc
import llvm.ee as le
from .support import TestCase, tests, BITS

class TestIntrinsic(TestCase):
    def test_bswap(self):
        # setup a function and a builder
        mod    = Module.new('test')
        functy = Type.function(Type.int(), [])
        func   = mod.add_function(functy, "showme")
        block  = func.append_basic_block("entry")
        b      = Builder.new(block)

        # let's do bswap on a 32-bit integer using llvm.bswap
        val   = Constant.int(Type.int(), 0x42)
        bswap = Function.intrinsic(mod, lc.INTR_BSWAP, [Type.int()])

        bswap_res = b.call(bswap, [val])
        b.ret(bswap_res)

        # logging.debug(mod)

        # the output is:
        #
        #    ; ModuleID = 'test'
        #
        #    define void @showme() {
        #    entry:
        #      %0 = call i32 @llvm.bswap.i32(i32 42)
        #      ret i32 %0
        #    }

        # let's run the function
        ee = le.ExecutionEngine.new(mod)
        retval = ee.run_function(func, [])
        self.assertEqual(retval.as_int(), 0x42000000)

    def test_mysin(self):
        if sys.platform == 'win32' and BITS == 32:
            # float32 support is known to fail on 32-bit Windows
            return

        # mysin(x) = sqrt(1.0 - pow(cos(x), 2))
        mod     = Module.new('test')

        float   = Type.float()
        mysinty = Type.function( float, [float] )
        mysin   = mod.add_function(mysinty, "mysin")
        block   = mysin.append_basic_block("entry")
        b       = Builder.new(block)

        sqrt = Function.intrinsic(mod, lc.INTR_SQRT, [float])
        pow  = Function.intrinsic(mod, lc.INTR_POWI, [float])
        cos  = Function.intrinsic(mod, lc.INTR_COS,  [float])

        mysin.args[0].name = "x"
        x    = mysin.args[0]
        one  = Constant.real(float, "1")
        cosx = b.call(cos, [x], "cosx")
        cos2 = b.call(pow, [cosx, Constant.int(Type.int(), 2)], "cos2")
        onemc2 = b.fsub(one, cos2, "onemc2") # Should use fsub
        sin  = b.call(sqrt, [onemc2], "sin")
        b.ret(sin)
        #logging.debug(mod)

#   ; ModuleID = 'test'
#
#   define void @showme() {
#   entry:
#       call i32 @llvm.bswap.i32( i32 42 )              ; <i32>:0 [#uses
#   }
#
#   declare i32 @llvm.bswap.i32(i32) nounwind readnone
#
#   define float @mysin(float %x) {
#   entry:
#       %cosx = call float @llvm.cos.f32( float %x )            ; <float
#       %cos2 = call float @llvm.powi.f32( float %cosx, i32 2 )
#       %onemc2 = sub float 1.000000e+00, %cos2         ; <float> [#uses
#       %sin = call float @llvm.sqrt.f32( float %onemc2 )
#       ret float %sin
#   }
#
#   declare float @llvm.sqrt.f32(float) nounwind readnone
#
#   declare float @llvm.powi.f32(float, i32) nounwind readnone
#
#   declare float @llvm.cos.f32(float) nounwind readnone

        # let's run the function

        from llvm.workaround.avx_support import detect_avx_support
        if not detect_avx_support():
            ee = le.EngineBuilder.new(mod).mattrs("-avx").create()
        else:
            ee = le.EngineBuilder.new(mod).create()

        arg = le.GenericValue.real(Type.float(), 1.234)
        retval = ee.run_function(mysin, [arg])

        golden = math.sin(1.234)
        answer = retval.as_real(Type.float())
        self.assertTrue(abs(answer-golden)/golden < 1e-5)

tests.append(TestIntrinsic)

if __name__ == '__main__':
    unittest.main()


########NEW FILE########
__FILENAME__ = test_intrinsic_basic
import unittest
import sys
import math
from llvm.core import (Module, Type, Function, Builder)
import llvm.core as lc
import llvm.ee as le
from .support import TestCase, BITS, tests

class TestIntrinsicBasic(TestCase):

    def _build_module(self, float):
        mod     = Module.new('test')
        functy  = Type.function(float, [float])
        func    = mod.add_function(functy, "mytest%s" % float)
        block   = func.append_basic_block("entry")
        b       = Builder.new(block)
        return mod, func, b

    def _template(self, mod, func, pyfunc):
        float = func.type.pointee.return_type

        from llvm.workaround.avx_support import detect_avx_support
        if not detect_avx_support():
            ee = le.EngineBuilder.new(mod).mattrs("-avx").create()
        else:
            ee = le.EngineBuilder.new(mod).create()
        arg = le.GenericValue.real(float, 1.234)
        retval = ee.run_function(func, [arg])
        golden = pyfunc(1.234)
        answer = retval.as_real(float)
        self.assertTrue(abs(answer - golden) / golden < 1e-7)

    def test_sqrt_f32(self):
        float = Type.float()
        mod, func, b = self._build_module(float)
        intr = Function.intrinsic(mod, lc.INTR_SQRT, [float])
        b.ret(b.call(intr, func.args))
        self._template(mod, func, math.sqrt)

    def test_sqrt_f64(self):
        float = Type.double()
        mod, func, b = self._build_module(float)
        intr = Function.intrinsic(mod, lc.INTR_SQRT, [float])
        b.ret(b.call(intr, func.args))
        self._template(mod, func, math.sqrt)

    def test_cos_f32(self):
        if sys.platform == 'win32' and BITS == 32:
            # float32 support is known to fail on 32-bit Windows
            return
        float = Type.float()
        mod, func, b = self._build_module(float)
        intr = Function.intrinsic(mod, lc.INTR_COS, [float])
        b.ret(b.call(intr, func.args))
        self._template(mod, func, math.cos)

    def test_cos_f64(self):
        float = Type.double()
        mod, func, b = self._build_module(float)
        intr = Function.intrinsic(mod, lc.INTR_COS, [float])
        b.ret(b.call(intr, func.args))
        self._template(mod, func, math.cos)

    def test_sin_f32(self):
        if sys.platform == 'win32' and BITS == 32:
            # float32 support is known to fail on 32-bit Windows
            return
        float = Type.float()
        mod, func, b = self._build_module(float)
        intr = Function.intrinsic(mod, lc.INTR_SIN, [float])
        b.ret(b.call(intr, func.args))
        self._template(mod, func, math.sin)

    def test_sin_f64(self):
        float = Type.double()
        mod, func, b = self._build_module(float)
        intr = Function.intrinsic(mod, lc.INTR_SIN, [float])
        b.ret(b.call(intr, func.args))
        self._template(mod, func, math.sin)

    def test_powi_f32(self):
        float = Type.float()
        mod, func, b = self._build_module(float)
        intr = Function.intrinsic(mod, lc.INTR_POWI, [float])
        b.ret(b.call(intr, [func.args[0], lc.Constant.int(Type.int(), 2)]))
        self._template(mod, func, lambda x: x**2)

    def test_powi_f64(self):
        float = Type.double()
        mod, func, b = self._build_module(float)
        intr = Function.intrinsic(mod, lc.INTR_POWI, [float])
        b.ret(b.call(intr, [func.args[0], lc.Constant.int(Type.int(), 2)]))
        self._template(mod, func, lambda x: x**2)

tests.append(TestIntrinsicBasic)

if __name__ == '__main__':
    unittest.main()


########NEW FILE########
__FILENAME__ = test_issue_10
import unittest
from llvm.core import (Module, Type, Builder)
from .support import TestCase, tests

class TestIssue10(TestCase):
    def test_issue10(self):
        m = Module.new('a')
        ti = Type.int()
        tf = Type.function(ti, [ti, ti])

        f = m.add_function(tf, "func1")

        bb = f.append_basic_block('entry')

        b = Builder.new(bb)

        # There are no instructions in bb. Positioning of the
        # builder at beginning (or end) should succeed (trivially).
        b.position_at_end(bb)
        b.position_at_beginning(bb)

tests.append(TestIssue10)

if __name__ == '__main__':
    unittest.main()


########NEW FILE########
__FILENAME__ = test_llrt
import unittest
import llvm.core as lc
import llvm.ee as le
from .support import TestCase, tests

class TestLLRT(TestCase):
    def test_llrt_divmod(self):
        from llvm import llrt
        m = lc.Module.new('testllrt')
        longlong = lc.Type.int(64)
        lfunc = m.add_function(lc.Type.function(longlong, [longlong, longlong]), 'foo')
        bldr = lc.Builder.new(lfunc.append_basic_block(''))
        bldr.ret(bldr.udiv(*lfunc.args))

        llrt.replace_divmod64(lfunc)

        rt = llrt.LLRT()
        rt.install_symbols()

        engine = le.EngineBuilder.new(m).create()
        pointer = engine.get_pointer_to_function(lfunc)

        from ctypes import CFUNCTYPE, c_uint64
        func = CFUNCTYPE(c_uint64, c_uint64, c_uint64)(pointer)
        a, b = 98342, 2231
        self.assertEqual(func(98342, 2231), 98342 // 2231)

        rt.uninstall_symbols()

tests.append(TestLLRT)

if __name__ == '__main__':
    unittest.main()


########NEW FILE########
__FILENAME__ = test_mcjit
import unittest
import sys
import llvm
from llvm.core import (Module, Type, Builder)
from llvm.ee import EngineBuilder

import llvm.ee as le
from .support import TestCase, tests, BITS

class TestMCJIT(TestCase):
    def test_mcjit(self):
        m = Module.new('oidfjs')
        fnty = Type.function(Type.int(), [Type.int(), Type.int()])
        func = m.add_function(fnty, 'foo')
        bb = func.append_basic_block('')
        bldr = Builder.new(bb)
        bldr.ret(bldr.add(*func.args))

        func.verify()

        engine = EngineBuilder.new(m).mcjit(True).create()
        ptr = engine.get_pointer_to_function(func)

        from ctypes import c_int, CFUNCTYPE
        callee = CFUNCTYPE(c_int, c_int, c_int)(ptr)
        self.assertEqual(321 + 123, callee(321, 123))

    def test_multi_module_linking(self):
        # generate external library module
        m = Module.new('external-library-module')
        fnty = Type.function(Type.int(), [Type.int(), Type.int()])
        libfname = 'myadd'
        func = m.add_function(fnty, libfname)
        bb = func.append_basic_block('')
        bldr = Builder.new(bb)
        bldr.ret(bldr.add(*func.args))
        func.verify()

        # JIT the lib module and bind dynamic symbol
        libengine = EngineBuilder.new(m).mcjit(True).create()
        myadd_ptr = libengine.get_pointer_to_function(func)
        le.dylib_add_symbol(libfname, myadd_ptr)

        # reference external library
        m = Module.new('user')
        fnty = Type.function(Type.int(), [Type.int(), Type.int()])
        func = m.add_function(fnty, 'foo')
        bb = func.append_basic_block('')
        bldr = Builder.new(bb)
        extadd = m.get_or_insert_function(fnty, name=libfname)
        bldr.ret(bldr.call(extadd, func.args))
        func.verify()

        # JIT the user module
        engine = EngineBuilder.new(m).mcjit(True).create()
        ptr = engine.get_pointer_to_function(func)
        self.assertEqual(myadd_ptr,
                         engine.get_pointer_to_named_function(libfname))

        from ctypes import c_int, CFUNCTYPE
        callee = CFUNCTYPE(c_int, c_int, c_int)(ptr)
        self.assertEqual(321 + 123, callee(321, 123))


if (llvm.version >= (3, 3) and
    not (sys.platform.startswith('win32') and BITS == 64)):
    # MCJIT broken in 3.2, the test will segfault in OSX?
    # Compatbility problem on windows 7 64-bit?
    tests.append(TestMCJIT)

if __name__ == '__main__':
    unittest.main()


########NEW FILE########
__FILENAME__ = test_metadata
import unittest
from llvm.core import (Module, Type, Constant, MetaData, MetaDataString)
from .support import TestCase, tests

class TestMetaData(TestCase):
    # test module metadata
    def test_metadata(self):
        m = Module.new('a')
        t = Type.int()
        metadata = MetaData.get(m, [Constant.int(t, 100),
                                    MetaDataString.get(m, 'abcdef'),
                                    None])
        MetaData.add_named_operand(m, 'foo', metadata)
        self.assertEqual(MetaData.get_named_operands(m, 'foo'), [metadata])
        self.assertEqual(MetaData.get_named_operands(m, 'bar'), [])
        self.assertEqual(len(metadata.operands), 3)
        self.assertEqual(metadata.operands[0].z_ext_value, 100)
        self.assertEqual(metadata.operands[1].string, 'abcdef')
        self.assertTrue(metadata.operands[2] is None)

tests.append(TestMetaData)

if __name__ == '__main__':
    unittest.main()


########NEW FILE########
__FILENAME__ = test_named_metadata
import unittest
from llvm.core import (Module, Type, Constant, MetaData)
from .support import TestCase, tests


class TestNamedMetaData(TestCase):
    def test_named_md(self):
        m = Module.new('test_named_md')
        nmd = m.get_or_insert_named_metadata('something')
        md = MetaData.get(m, [Constant.int(Type.int(), 0xbeef)])
        nmd.add(md)
        self.assertTrue(str(nmd).startswith('!something'))
        ir = str(m)
        self.assertTrue('!something' in ir)

tests.append(TestNamedMetaData)

if __name__ == '__main__':
    unittest.main()


########NEW FILE########
__FILENAME__ = test_native
import unittest
import os
import sys
import shutil
import subprocess
import tempfile
from distutils.spawn import find_executable
from llvm.core import (Module, Type, Builder, Constant)
from .support import TestCase, IS_PY3K, tests, skip_if

@skip_if(sys.platform in ('win32', 'darwin'))
class TestNative(TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)


    def _make_module(self):
        m = Module.new('module1')
        m.add_global_variable(Type.int(), 'i')

        fty = Type.function(Type.int(), [])
        f = m.add_function(fty, name='main')

        bldr = Builder.new(f.append_basic_block('entry'))
        bldr.ret(Constant.int(Type.int(), 0xab))

        return m

    def _compile(self, src):
        cc = find_executable('cc')
        if not cc:
            return

        dst = os.path.join(self.tmpdir, 'llvmobj.out')
        s = subprocess.call([cc, '-o', dst, src])
        if s != 0:
            raise Exception("Cannot compile")

        s = subprocess.call([dst])
        self.assertEqual(s, 0xab)

    def test_assembly(self):
        #        if sys.platform == 'darwin':
        #            # skip this test on MacOSX for now
        #            return

        m = self._make_module()
        output = m.to_native_assembly()

        src = os.path.join(self.tmpdir, 'llvmasm.s')
        with open(src, 'wb') as fout:
            if IS_PY3K:
                fout.write(output.encode('utf-8'))
            else:
                fout.write(output)

        self._compile(src)

    def test_object(self):
        '''
        Note: Older Darwin with GCC will report missing _main symbol when
              compile the object file to an executable.
        '''
        m = self._make_module()
        output = m.to_native_object()

        src = os.path.join(self.tmpdir, 'llvmobj.o')
        with open(src, 'wb') as fout:
            fout.write(output)

        self._compile(src)

tests.append(TestNative)

if __name__ == '__main__':
    unittest.main()


########NEW FILE########
__FILENAME__ = test_nuw_nsw
import unittest
from llvm.core import Module, Type, Builder
from .support import TestCase, tests

class TestNUWNSW(TestCase):
    def make_module(self):
        mod = Module.new('asdfa')
        fnty = Type.function(Type.void(), [Type.int()] * 2)
        func = mod.add_function(fnty, 'foo')
        bldr = Builder.new(func.append_basic_block(''))
        return mod, func, bldr

    def has_nsw(self, inst, op):
        self.assertTrue(('%s nsw' % op) in str(inst), "NSW flag does not work")

    def has_nuw(self, inst, op):
        self.assertTrue(('%s nuw' % op) in str(inst), "NUW flag does not work")

    def _test_template(self, opf, opname):
        mod, func, bldr = self.make_module()
        a, b = func.args
        self.has_nsw(opf(bldr, a, b, nsw=True), opname)
        self.has_nuw(opf(bldr, a, b, nuw=True), opname)

    def test_add_nuw_nsw(self):
        self._test_template(Builder.add, 'add')

    def test_sub_nuw_nsw(self):
        self._test_template(Builder.sub, 'sub')

    def test_mul_nuw_nsw(self):
        self._test_template(Builder.mul, 'mul')

    def test_shl_nuw_nsw(self):
        self._test_template(Builder.shl, 'shl')

    def test_neg_nuw_nsw(self):
        mod, func, bldr = self.make_module()
        a, b = func.args
        self.has_nsw(bldr.neg(a, nsw=True), 'sub')
        self.has_nuw(bldr.neg(a, nuw=True), 'sub')


tests.append(TestNUWNSW)

if __name__ == '__main__':
    unittest.main()


########NEW FILE########
__FILENAME__ = test_obj_cache
import unittest
from llvm.core import Module, Type, GlobalVariable, Function, Builder
from .support import TestCase, tests

class TestObjCache(TestCase):

    def test_objcache(self):
        # Testing module aliasing
        m1 = Module.new('a')
        t = Type.int()
        ft = Type.function(t, [t])
        f1 = m1.add_function(ft, "func")
        m2 = f1.module
        self.assert_(m1 is m2)

        # Testing global vairable aliasing 1
        gv1 = GlobalVariable.new(m1, t, "gv")
        gv2 = GlobalVariable.get(m1, "gv")
        self.assert_(gv1 is gv2)

        # Testing global vairable aliasing 2
        gv3 = m1.global_variables[0]
        self.assert_(gv1 is gv3)

        # Testing global vairable aliasing 3
        gv2 = None
        gv3 = None

        gv1.delete()

        gv4 = GlobalVariable.new(m1, t, "gv")

        self.assert_(gv1 is not gv4)

        # Testing function aliasing 1
        b1 = f1.append_basic_block('entry')
        f2 = b1.function
        self.assert_(f1 is f2)

        # Testing function aliasing 2
        f3 = m1.get_function_named("func")
        self.assert_(f1 is f3)

        # Testing function aliasing 3
        f4 = Function.get_or_insert(m1, ft, "func")
        self.assert_(f1 is f4)

        # Testing function aliasing 4
        f5 = Function.get(m1, "func")
        self.assert_(f1 is f5)

        # Testing function aliasing 5
        f6 = m1.get_or_insert_function(ft, "func")
        self.assert_(f1 is f6)

        # Testing function aliasing 6
        f7 = m1.functions[0]
        self.assert_(f1 is f7)

        # Testing argument aliasing
        a1 = f1.args[0]
        a2 = f1.args[0]
        self.assert_(a1 is a2)

        # Testing basic block aliasing 1
        b2 = f1.basic_blocks[0]
        self.assert_(b1 is b2)

        # Testing basic block aliasing 2
        b3 = f1.entry_basic_block
        self.assert_(b1 is b3)

        # Testing basic block aliasing 3
        b31 = f1.entry_basic_block
        self.assert_(b1 is b31)

        # Testing basic block aliasing 4
        bldr = Builder.new(b1)
        b4 = bldr.basic_block
        self.assert_(b1 is b4)

        # Testing basic block aliasing 5
        i1 = bldr.ret_void()
        b5 = i1.basic_block
        self.assert_(b1 is b5)

        # Testing instruction aliasing 1
        i2 = b5.instructions[0]
        self.assert_(i1 is i2)

        # phi node
        phi = bldr.phi(t)
        phi.add_incoming(f1.args[0], b1)
        v2 = phi.get_incoming_value(0)
        b6 = phi.get_incoming_block(0)

        # Testing PHI / basic block aliasing 5
        self.assert_(b1 is b6)

        # Testing PHI / value aliasing
        self.assert_(f1.args[0] is v2)

tests.append(TestObjCache)

if __name__ == '__main__':
    unittest.main()


########NEW FILE########
__FILENAME__ = test_opaque
import unittest
import llvm
from llvm.core import Type
from .support import TestCase, tests

class TestOpaque(TestCase):

    def test_opaque(self):
        # Create an opaque type
        ts = Type.opaque('mystruct')
        self.assertTrue('type opaque' in str(ts))
        self.assertTrue(ts.is_opaque)
        self.assertTrue(ts.is_identified)
        self.assertFalse(ts.is_literal)
        #print(ts)

        # Create a recursive type
        ts.set_body([Type.int(), Type.pointer(ts)])

        self.assertEqual(ts.elements[0], Type.int())
        self.assertEqual(ts.elements[1], Type.pointer(ts))
        self.assertEqual(ts.elements[1].pointee, ts)
        self.assertFalse(ts.is_opaque) # is not longer a opaque type
        #print(ts)

        with self.assertRaises(llvm.LLVMException):
            # Cannot redefine
            ts.set_body([])

    def test_opaque_with_no_name(self):
        with self.assertRaises(llvm.LLVMException):
            Type.opaque('')

tests.append(TestOpaque)

if __name__ == '__main__':
    unittest.main()


########NEW FILE########
__FILENAME__ = test_operands
import unittest
try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO

from llvm.core import Module
from .support import TestCase, tests

class TestOperands(TestCase):
    # implement a test function
    test_module = """
define i32 @prod(i32, i32) {
entry:
        %2 = mul i32 %0, %1
        ret i32 %2
}

define i32 @test_func(i32, i32, i32) {
entry:
        %tmp1 = call i32 @prod(i32 %0, i32 %1)
        %tmp2 = add i32 %tmp1, %2
        %tmp3 = add i32 %tmp2, 1
        %tmp4 = add i32 %tmp3, -1
        %tmp5 = add i64 -81985529216486895, 12297829382473034410
        ret i32 %tmp4
}
"""
    def test_operands(self):
        m = Module.from_assembly(StringIO(self.test_module))

        test_func = m.get_function_named("test_func")
        prod = m.get_function_named("prod")

        # test operands
        i1 = test_func.basic_blocks[0].instructions[0]
        i2 = test_func.basic_blocks[0].instructions[1]
        i3 = test_func.basic_blocks[0].instructions[2]
        i4 = test_func.basic_blocks[0].instructions[3]
        i5 = test_func.basic_blocks[0].instructions[4]

        self.assertEqual(i1.operand_count, 3)
        self.assertEqual(i2.operand_count, 2)

        self.assertEqual(i3.operands[1].z_ext_value, 1)
        self.assertEqual(i3.operands[1].s_ext_value, 1)
        self.assertEqual(i4.operands[1].z_ext_value, 0xffffffff)
        self.assertEqual(i4.operands[1].s_ext_value, -1)
        self.assertEqual(i5.operands[0].s_ext_value, -81985529216486895)
        self.assertEqual(i5.operands[1].z_ext_value, 12297829382473034410)

        self.assert_(i1.operands[-1] is prod)
        self.assert_(i1.operands[0] is test_func.args[0])
        self.assert_(i1.operands[1] is test_func.args[1])
        self.assert_(i2.operands[0] is i1)
        self.assert_(i2.operands[1] is test_func.args[2])
        self.assertEqual(len(i1.operands), 3)
        self.assertEqual(len(i2.operands), 2)

        self.assert_(i1.called_function is prod)

tests.append(TestOperands)

if __name__ == '__main__':
    unittest.main()


########NEW FILE########
__FILENAME__ = test_passes
import unittest
try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO
import llvm
from llvm.core import Module
import llvm.passes as lp
import llvm.ee as le
from .support import TestCase, tests


class TestPasses(TestCase):
    # Create a module.
    asm = """

define i32 @test() nounwind {
    ret i32 42
}

define i32 @test1() nounwind  {
entry:
        %tmp = alloca i32
        store i32 42, i32* %tmp, align 4
        %tmp1 = load i32* %tmp, align 4
        %tmp2 = call i32 @test()
        %tmp3 = load i32* %tmp, align 4
        %tmp4 = load i32* %tmp, align 4
    ret i32 %tmp1
}

define i32 @test2() nounwind  {
entry:
        %tmp = call i32 @test()
    ret i32 %tmp
}
"""
    def test_passes(self):
        m = Module.from_assembly(StringIO(self.asm))

        fn_test1 = m.get_function_named('test1')
        fn_test2 = m.get_function_named('test2')

        original_test1 = str(fn_test1)
        original_test2 = str(fn_test2)

        # Let's run a module-level inlining pass. First, create a pass manager.
        pm = lp.PassManager.new()

        # Add the target data as the first "pass". This is mandatory.
        pm.add(le.TargetData.new(''))

        # Add the inlining pass.
        pm.add(lp.PASS_INLINE)

        # Run it!
        pm.run(m)

        # Done with the pass manager.
        del pm

        # Make sure test2 is inlined
        self.assertNotEqual(str(fn_test2).strip(), original_test2.strip())

        bb_entry = fn_test2.basic_blocks[0]

        self.assertEqual(len(bb_entry.instructions), 1)
        self.assertEqual(bb_entry.instructions[0].opcode_name, 'ret')

        # Let's run a DCE pass on the the function 'test1' now. First create a
        # function pass manager.
        fpm = lp.FunctionPassManager.new(m)

        # Add the target data as first "pass". This is mandatory.
        fpm.add(le.TargetData.new(''))

        # Add a DCE pass
        fpm.add(lp.PASS_ADCE)

        # Run the pass on the function 'test1'
        fpm.run(m.get_function_named('test1'))

        # Make sure test1 is modified
        self.assertNotEqual(str(fn_test1).strip(), original_test1.strip())

    def test_passes_with_pmb(self):
        m = Module.from_assembly(StringIO(self.asm))

        fn_test1 = m.get_function_named('test1')
        fn_test2 = m.get_function_named('test2')

        original_test1 = str(fn_test1)
        original_test2 = str(fn_test2)

        # Try out the PassManagerBuilder

        pmb = lp.PassManagerBuilder.new()

        self.assertEqual(pmb.opt_level, 2)  # ensure default is level 2
        pmb.opt_level = 3
        self.assertEqual(pmb.opt_level, 3) # make sure it works

        self.assertEqual(pmb.size_level, 0) # ensure default is level 0
        pmb.size_level = 2
        self.assertEqual(pmb.size_level, 2) # make sure it works

        self.assertFalse(pmb.vectorize) # ensure default is False
        pmb.vectorize = True
        self.assertTrue(pmb.vectorize) # make sure it works

        # make sure the default is False
        self.assertFalse(pmb.disable_unit_at_a_time)
        self.assertFalse(pmb.disable_unroll_loops)
        if llvm.version <= (3, 3):
            self.assertFalse(pmb.disable_simplify_lib_calls)

        pmb.disable_unit_at_a_time = True
        self.assertTrue(pmb.disable_unit_at_a_time)

        # Do function pass
        fpm = lp.FunctionPassManager.new(m)
        pmb.populate(fpm)
        fpm.run(fn_test1)

        # Make sure test1 has changed
        self.assertNotEqual(str(fn_test1).strip(), original_test1.strip())

        # Do module pass
        pm = lp.PassManager.new()
        pmb.populate(pm)
        pm.run(m)

        # Make sure test2 has changed
        self.assertNotEqual(str(fn_test2).strip(), original_test2.strip())

    def test_dump_passes(self):
        self.assertTrue(len(lp.PASSES)>0, msg="Cannot have no passes")

tests.append(TestPasses)

if __name__ == '__main__':
    unittest.main()


########NEW FILE########
__FILENAME__ = test_struct
import unittest
from llvm.core import Type, Module, Builder, Constant
from .support import TestCase, tests

class TestStruct(TestCase):
    def test_struct_identical(self):
        ta = Type.struct([Type.int(32), Type.float()], name='ta')
        tb = Type.struct([Type.int(32), Type.float()])
        self.assertTrue(ta.is_layout_identical(tb))

    def test_struct_extract_value_2d(self):
        ta = Type.struct([Type.int(32), Type.float()])
        tb = Type.struct([ta, Type.float()])
        m = Module.new('')
        f = m.add_function(Type.function(Type.void(), []), "foo")
        b = Builder.new(f.append_basic_block(''))
        v = Constant.undef(tb)
        ins = b.insert_value(v, Constant.real(Type.float(), 1.234), [0, 1])
        ext = b.extract_value(ins, [0, 1])
        b.ret_void()
        m.verify()
        self.assertEqual(str(ext), 'float 0x3FF3BE76C0000000')

tests.append(TestStruct)

if __name__ == '__main__':
    unittest.main()


########NEW FILE########
__FILENAME__ = test_struct_args
from __future__ import print_function
from . import tests
import sys
import unittest
from ctypes import Structure, c_float, c_double, c_uint8, CFUNCTYPE
from llvm import core as lc
from llvm import ee as le

from .support import (skip_if_win32, skip_if_not_win32, skip_if_not_32bits,
                      skip_if_not_64bits, skip_if_not_intel_cpu, TestCase)

class TwoDoubleOneByte(Structure):
    _fields_ = ('x', c_double), ('y', c_double), ('z', c_uint8)

    def __repr__(self):
        return '<x=%f y=%f z=%d>' % (self.x, self.y, self.z)

class TwoDouble(Structure):
    _fields_ = ('x', c_double), ('y', c_double)

    def __repr__(self):
        return '<x=%f y=%f>' % (self.x, self.y)

class TwoFloat(Structure):
    _fields_ = ('x', c_float), ('y', c_float)

    def __repr__(self):
        return '<x=%f y=%f>' % (self.x, self.y)

class OneByte(Structure):
    _fields_ = [('x', c_uint8)]

    def __repr__(self):
        return '<x=%d>' % (self.x,)

@skip_if_not_intel_cpu
@skip_if_win32
class TestStructSystemVABI(TestCase):
    '''
    Non microsoft convention
    '''

    #----------------------------------------------------------------------
    # 64 bits

    @skip_if_not_64bits
    def test_bigger_than_two_words_64(self):
        m = lc.Module.new('test_struct_arg')

        double_type = lc.Type.double()
        uint8_type = lc.Type.int(8)
        struct_type = lc.Type.struct([double_type, double_type, uint8_type])
        struct_ptr_type = lc.Type.pointer(struct_type)
        func_type = lc.Type.function(lc.Type.void(),
                                     [struct_ptr_type, struct_ptr_type])
        func = m.add_function(func_type, name='foo')

        # return value pointer
        func.args[0].add_attribute(lc.ATTR_STRUCT_RET)

        # pass structure by value
        func.args[1].add_attribute(lc.ATTR_BY_VAL)

        # define function body
        builder = lc.Builder.new(func.append_basic_block(''))

        arg = builder.load(func.args[1])
        e1, e2, e3 = [builder.extract_value(arg, i) for i in range(3)]
        se1 = builder.fmul(e1, e2)
        se2 = builder.fdiv(e1, e2)
        ret = builder.insert_value(lc.Constant.undef(struct_type), se1, 0)
        ret = builder.insert_value(ret, se2, 1)
        ret = builder.insert_value(ret, e3, 2)
        builder.store(ret, func.args[0])
        builder.ret_void()

        del builder

        # verify
        m.verify()

        print(m)
        # use with ctypes
        engine = le.EngineBuilder.new(m).create()
        ptr = engine.get_pointer_to_function(func)

        cfunctype = CFUNCTYPE(TwoDoubleOneByte, TwoDoubleOneByte)
        cfunc = cfunctype(ptr)

        arg = TwoDoubleOneByte(x=1.321321, y=6.54352, z=128)
        ret = cfunc(arg)
        print(arg)
        print(ret)

        self.assertClose(arg.x * arg.y, ret.x)
        self.assertClose(arg.x / arg.y, ret.y)
        self.assertEqual(arg.z, ret.z)

    @skip_if_not_64bits
    def test_just_two_words_64(self):
        m = lc.Module.new('test_struct_arg')

        double_type = lc.Type.double()
        struct_type = lc.Type.struct([double_type, double_type])
        func_type = lc.Type.function(struct_type, [struct_type])
        func = m.add_function(func_type, name='foo')

        # define function body
        builder = lc.Builder.new(func.append_basic_block(''))

        arg = func.args[0]
        e1, e2 = [builder.extract_value(arg, i) for i in range(2)]
        se1 = builder.fmul(e1, e2)
        se2 = builder.fdiv(e1, e2)
        ret = builder.insert_value(lc.Constant.undef(struct_type), se1, 0)
        ret = builder.insert_value(ret, se2, 1)
        builder.ret(ret)

        del builder

        # verify
        m.verify()

        print(m)
        # use with ctypes
        engine = le.EngineBuilder.new(m).create()
        ptr = engine.get_pointer_to_function(func)

        cfunctype = CFUNCTYPE(TwoDouble, TwoDouble)
        cfunc = cfunctype(ptr)

        arg = TwoDouble(x=1.321321, y=6.54352)
        ret = cfunc(arg)
        print(arg)
        print(ret)

        self.assertClose(arg.x * arg.y, ret.x)
        self.assertClose(arg.x / arg.y, ret.y)

    @skip_if_not_64bits
    def test_two_halfwords(self):
        '''Arguments smaller or equal to a word is packed into a word.

        Passing as struct { float, float } occupies two XMM registers instead
        of one.
        The output must be in XMM.
        '''
        m = lc.Module.new('test_struct_arg')

        float_type = lc.Type.float()
        struct_type = lc.Type.vector(float_type, 2)
        func_type = lc.Type.function(struct_type, [struct_type])
        func = m.add_function(func_type, name='foo')

        # define function body
        builder = lc.Builder.new(func.append_basic_block(''))

        arg = func.args[0]
        constint = lambda x: lc.Constant.int(lc.Type.int(), x)
        e1, e2 = [builder.extract_element(arg, constint(i))
                  for i in range(2)]
        se1 = builder.fmul(e1, e2)
        se2 = builder.fdiv(e1, e2)
        ret = builder.insert_element(lc.Constant.undef(struct_type), se1,
                                     constint(0))
        ret = builder.insert_element(ret, se2, constint(1))
        builder.ret(ret)

        del builder

        # verify
        m.verify()

        print(m)
        # use with ctypes
        engine = le.EngineBuilder.new(m).create()
        ptr = engine.get_pointer_to_function(func)

        cfunctype = CFUNCTYPE(TwoFloat, TwoFloat)
        cfunc = cfunctype(ptr)

        arg = TwoFloat(x=1.321321, y=6.54352)
        ret = cfunc(arg)
        print(arg)
        print(ret)

        self.assertClose(arg.x * arg.y, ret.x)
        self.assertClose(arg.x / arg.y, ret.y)

    #----------------------------------------------------------------------
    # 32 bits

    @skip_if_not_32bits
    def test_structure_abi_32_1(self):
        '''x86 is simple.  Always pass structure as memory.
        '''
        m = lc.Module.new('test_struct_arg')

        double_type = lc.Type.double()
        uint8_type = lc.Type.int(8)
        struct_type = lc.Type.struct([double_type, double_type, uint8_type])
        struct_ptr_type = lc.Type.pointer(struct_type)
        func_type = lc.Type.function(lc.Type.void(),
                                     [struct_ptr_type, struct_ptr_type])
        func = m.add_function(func_type, name='foo')

        # return value pointer
        func.args[0].add_attribute(lc.ATTR_STRUCT_RET)

        # pass structure by value
        func.args[1].add_attribute(lc.ATTR_BY_VAL)

        # define function body
        builder = lc.Builder.new(func.append_basic_block(''))

        arg = builder.load(func.args[1])
        e1, e2, e3 = [builder.extract_value(arg, i) for i in range(3)]
        se1 = builder.fmul(e1, e2)
        se2 = builder.fdiv(e1, e2)
        ret = builder.insert_value(lc.Constant.undef(struct_type), se1, 0)
        ret = builder.insert_value(ret, se2, 1)
        ret = builder.insert_value(ret, e3, 2)
        builder.store(ret, func.args[0])
        builder.ret_void()

        del builder

        # verify
        m.verify()

        print(m)
        # use with ctypes
        engine = le.EngineBuilder.new(m).create()
        ptr = engine.get_pointer_to_function(func)

        cfunctype = CFUNCTYPE(TwoDoubleOneByte, TwoDoubleOneByte)
        cfunc = cfunctype(ptr)

        arg = TwoDoubleOneByte(x=1.321321, y=6.54352, z=128)
        ret = cfunc(arg)
        print(arg)
        print(ret)

        self.assertClose(arg.x * arg.y, ret.x)
        self.assertClose(arg.x / arg.y, ret.y)
        self.assertEqual(arg.z, ret.z)


    @skip_if_not_32bits
    def test_structure_abi_32_2(self):
        '''x86 is simple.  Always pass structure as memory.
        '''
        m = lc.Module.new('test_struct_arg')

        float_type = lc.Type.float()
        struct_type = lc.Type.struct([float_type, float_type])
        struct_ptr_type = lc.Type.pointer(struct_type)
        func_type = lc.Type.function(lc.Type.void(),
                                     [struct_ptr_type, struct_ptr_type])
        func = m.add_function(func_type, name='foo')

        # return value pointer
        func.args[0].add_attribute(lc.ATTR_STRUCT_RET)

        # pass structure by value
        func.args[1].add_attribute(lc.ATTR_BY_VAL)

        # define function body
        builder = lc.Builder.new(func.append_basic_block(''))

        arg = builder.load(func.args[1])
        e1, e2 = [builder.extract_value(arg, i) for i in range(2)]
        se1 = builder.fmul(e1, e2)
        se2 = builder.fdiv(e1, e2)
        ret = builder.insert_value(lc.Constant.undef(struct_type), se1, 0)
        ret = builder.insert_value(ret, se2, 1)
        builder.store(ret, func.args[0])
        builder.ret_void()

        del builder

        # verify
        m.verify()

        print(m)
        # use with ctypes
        engine = le.EngineBuilder.new(m).create()
        ptr = engine.get_pointer_to_function(func)

        cfunctype = CFUNCTYPE(TwoFloat, TwoFloat)
        cfunc = cfunctype(ptr)

        arg = TwoFloat(x=1.321321, y=6.54352)
        ret = cfunc(arg)
        print(arg)
        print(ret)

        self.assertClose(arg.x * arg.y, ret.x)
        self.assertClose(arg.x / arg.y, ret.y)


    @skip_if_not_32bits
    def test_structure_abi_32_3(self):
        '''x86 is simple.  Always pass structure as memory.
        '''
        m = lc.Module.new('test_struct_arg')

        uint8_type = lc.Type.int(8)
        struct_type = lc.Type.struct([uint8_type])
        struct_ptr_type = lc.Type.pointer(struct_type)
        func_type = lc.Type.function(lc.Type.void(),
                                     [struct_ptr_type, struct_ptr_type])
        func = m.add_function(func_type, name='foo')

        # return value pointer
        func.args[0].add_attribute(lc.ATTR_STRUCT_RET)

        # pass structure by value
        func.args[1].add_attribute(lc.ATTR_BY_VAL)

        # define function body
        builder = lc.Builder.new(func.append_basic_block(''))

        arg = builder.load(func.args[1])
        e1 = builder.extract_value(arg, 0)
        se1 = builder.mul(e1, e1)
        ret = builder.insert_value(lc.Constant.undef(struct_type), se1, 0)
        builder.store(ret, func.args[0])
        builder.ret_void()

        del builder

        # verify
        m.verify()

        print(m)
        # use with ctypes
        engine = le.EngineBuilder.new(m).create()
        ptr = engine.get_pointer_to_function(func)

        cfunctype = CFUNCTYPE(OneByte, OneByte)
        cfunc = cfunctype(ptr)

        arg = OneByte(x=8)
        ret = cfunc(arg)
        print(arg)
        print(ret)

        self.assertEqual(arg.x * arg.x, ret.x)

tests.append(TestStructSystemVABI)

@skip_if_not_intel_cpu
@skip_if_not_win32
class TestStructMicrosoftABI(TestCase):
    '''
    Microsoft convention
    '''

    #----------------------------------------------------------------------
    # 64 bits

    @skip_if_not_64bits
    def test_bigger_than_two_words_64(self):
        m = lc.Module.new('test_struct_arg')

        double_type = lc.Type.double()
        uint8_type = lc.Type.int(8)
        struct_type = lc.Type.struct([double_type, double_type, uint8_type])
        struct_ptr_type = lc.Type.pointer(struct_type)
        func_type = lc.Type.function(lc.Type.void(),
                                     [struct_ptr_type, struct_ptr_type])
        func = m.add_function(func_type, name='foo')

        # return value pointer
        func.args[0].add_attribute(lc.ATTR_STRUCT_RET)

        # pass structure by value
        func.args[1].add_attribute(lc.ATTR_BY_VAL)

        # define function body
        builder = lc.Builder.new(func.append_basic_block(''))

        arg = builder.load(func.args[1])
        e1, e2, e3 = [builder.extract_value(arg, i) for i in range(3)]
        se1 = builder.fmul(e1, e2)
        se2 = builder.fdiv(e1, e2)
        ret = builder.insert_value(lc.Constant.undef(struct_type), se1, 0)
        ret = builder.insert_value(ret, se2, 1)
        ret = builder.insert_value(ret, e3, 2)
        builder.store(ret, func.args[0])
        builder.ret_void()

        del builder

        # verify
        m.verify()

        print(m)
        # use with ctypes
        engine = le.EngineBuilder.new(m).create()
        ptr = engine.get_pointer_to_function(func)

        cfunctype = CFUNCTYPE(TwoDoubleOneByte, TwoDoubleOneByte)
        cfunc = cfunctype(ptr)

        arg = TwoDoubleOneByte(x=1.321321, y=6.54352, z=128)
        ret = cfunc(arg)
        print(arg)
        print(ret)

        self.assertClose(arg.x * arg.y, ret.x)
        self.assertClose(arg.x / arg.y, ret.y)
        self.assertEqual(arg.z, ret.z)

    @skip_if_not_64bits
    def test_just_two_words_64(self):
        m = lc.Module.new('test_struct_arg')

        double_type = lc.Type.double()
        struct_type = lc.Type.struct([double_type, double_type])
        struct_ptr_type = lc.Type.pointer(struct_type)
        func_type = lc.Type.function(lc.Type.void(),
                                     [struct_ptr_type, struct_ptr_type])
        func = m.add_function(func_type, name='foo')

        # return value pointer
        func.args[0].add_attribute(lc.ATTR_STRUCT_RET)

        # pass structure by value
        func.args[1].add_attribute(lc.ATTR_BY_VAL)

        # define function body
        builder = lc.Builder.new(func.append_basic_block(''))

        arg = builder.load(func.args[1])
        e1, e2 = [builder.extract_value(arg, i) for i in range(2)]
        se1 = builder.fmul(e1, e2)
        se2 = builder.fdiv(e1, e2)
        ret = builder.insert_value(lc.Constant.undef(struct_type), se1, 0)
        ret = builder.insert_value(ret, se2, 1)
        builder.store(ret, func.args[0])
        builder.ret_void()

        del builder

        # verify
        m.verify()

        print(m)
        # use with ctypes
        engine = le.EngineBuilder.new(m).create()
        ptr = engine.get_pointer_to_function(func)

        cfunctype = CFUNCTYPE(TwoDouble, TwoDouble)
        cfunc = cfunctype(ptr)

        arg = TwoDouble(x=1.321321, y=6.54352)
        ret = cfunc(arg)
        print(arg)
        print(ret)

        self.assertClose(arg.x * arg.y, ret.x)
        self.assertClose(arg.x / arg.y, ret.y)

    @skip_if_not_64bits
    def test_two_halfwords(self):
        '''Arguments smaller or equal to a word is packed into a word.

        Floats structure are not passed on the XMM.
        Treat it as a i64.
        '''
        m = lc.Module.new('test_struct_arg')

        float_type = lc.Type.float()
        struct_type = lc.Type.struct([float_type, float_type])
        abi_type = lc.Type.int(64)

        func_type = lc.Type.function(abi_type, [abi_type])
        func = m.add_function(func_type, name='foo')

        # define function body
        builder = lc.Builder.new(func.append_basic_block(''))

        arg = func.args[0]

        struct_ptr = builder.alloca(struct_type)
        struct_int_ptr = builder.bitcast(struct_ptr, lc.Type.pointer(abi_type))
        builder.store(arg, struct_int_ptr)

        arg = builder.load(struct_ptr)

        e1, e2 = [builder.extract_value(arg, i) for i in range(2)]
        se1 = builder.fmul(e1, e2)
        se2 = builder.fdiv(e1, e2)
        ret = builder.insert_value(lc.Constant.undef(struct_type), se1, 0)
        ret = builder.insert_value(ret, se2, 1)

        builder.store(ret, struct_ptr)
        ret = builder.load(struct_int_ptr)

        builder.ret(ret)

        del builder

        # verify
        m.verify()

        print(m)
        # use with ctypes
        engine = le.EngineBuilder.new(m).create()
        ptr = engine.get_pointer_to_function(func)

        cfunctype = CFUNCTYPE(TwoFloat, TwoFloat)
        cfunc = cfunctype(ptr)

        arg = TwoFloat(x=1.321321, y=6.54352)
        ret = cfunc(arg)
        print(arg)
        print(ret)

        self.assertClose(arg.x * arg.y, ret.x)
        self.assertClose(arg.x / arg.y, ret.y)

    #----------------------------------------------------------------------
    # 32 bits

    @skip_if_not_32bits
    def test_one_word_register(self):
        '''Argument is passed by memory.
        Return value is passed by register.
        '''
        m = lc.Module.new('test_struct_arg')

        uint8_type = lc.Type.int(8)
        struct_type = lc.Type.struct([uint8_type])
        struct_ptr_type = lc.Type.pointer(struct_type)
        func_type = lc.Type.function(struct_type, [struct_ptr_type])
        func = m.add_function(func_type, name='foo')

        # pass structure by value
        func.args[0].add_attribute(lc.ATTR_BY_VAL)

        # define function body
        builder = lc.Builder.new(func.append_basic_block(''))

        arg = builder.load(func.args[0])
        e1 = builder.extract_value(arg, 0)
        se1 = builder.mul(e1, e1)
        ret = builder.insert_value(lc.Constant.undef(struct_type), se1, 0)

        builder.ret(ret)

        del builder

        # verify
        m.verify()

        print(m)
        # use with ctypes
        engine = le.EngineBuilder.new(m).create()
        ptr = engine.get_pointer_to_function(func)

        cfunctype = CFUNCTYPE(OneByte, OneByte)
        cfunc = cfunctype(ptr)

        arg = OneByte(x=8)
        ret = cfunc(arg)
        print(arg)
        print(ret)

        self.assertEqual(arg.x * arg.x, ret.x)


    @skip_if_not_32bits
    def test_two_floats(self):
        '''Argument is passed by register.
        Return in 2 registers
        '''
        m = lc.Module.new('test_struct_arg')

        float_type = lc.Type.float()
        struct_type = lc.Type.struct([float_type, float_type])

        abi_type = lc.Type.int(64)
        func_type = lc.Type.function(abi_type, [struct_type])
        func = m.add_function(func_type, name='foo')

        # define function body
        builder = lc.Builder.new(func.append_basic_block(''))

        out_ptr = builder.alloca(struct_type)

        arg = func.args[0]
        e1, e2 = [builder.extract_value(arg, i) for i in range(2)]
        se1 = builder.fmul(e1, e2)
        se2 = builder.fdiv(e1, e2)
        ret = builder.insert_value(lc.Constant.undef(struct_type), se1, 0)
        ret = builder.insert_value(ret, se2, 1)
        builder.store(ret, out_ptr)

        out_int_ptr = builder.bitcast(out_ptr, lc.Type.pointer(abi_type))

        builder.ret(builder.load(out_int_ptr))

        del builder

        # verify
        m.verify()

        print(m)
        # use with ctypes
        engine = le.EngineBuilder.new(m).create()
        ptr = engine.get_pointer_to_function(func)

        cfunctype = CFUNCTYPE(TwoFloat, TwoFloat)
        cfunc = cfunctype(ptr)

        arg = TwoFloat(x=1.321321, y=6.54352)
        ret = cfunc(arg)
        print(arg)
        print(ret)

        self.assertClose(arg.x * arg.y, ret.x)
        self.assertClose(arg.x / arg.y, ret.y)

    @skip_if_not_32bits
    def test_bigger_than_two_words(self):
        '''Pass in memory.
        '''
        m = lc.Module.new('test_struct_arg')

        double_type = lc.Type.double()
        uint8_type = lc.Type.int(8)
        struct_type = lc.Type.struct([double_type, double_type, uint8_type])
        struct_ptr_type = lc.Type.pointer(struct_type)
        func_type = lc.Type.function(lc.Type.void(),
                                     [struct_ptr_type, struct_ptr_type])
        func = m.add_function(func_type, name='foo')

        # return value pointer
        func.args[0].add_attribute(lc.ATTR_STRUCT_RET)

        # pass structure by value
        func.args[1].add_attribute(lc.ATTR_BY_VAL)

        # define function body
        builder = lc.Builder.new(func.append_basic_block(''))

        arg = builder.load(func.args[1])
        e1, e2, e3 = [builder.extract_value(arg, i) for i in range(3)]
        se1 = builder.fmul(e1, e2)
        se2 = builder.fdiv(e1, e2)
        ret = builder.insert_value(lc.Constant.undef(struct_type), se1, 0)
        ret = builder.insert_value(ret, se2, 1)
        ret = builder.insert_value(ret, e3, 2)
        builder.store(ret, func.args[0])
        builder.ret_void()

        del builder

        # verify
        m.verify()

        print(m)
        # use with ctypes
        engine = le.EngineBuilder.new(m).create()
        ptr = engine.get_pointer_to_function(func)

        cfunctype = CFUNCTYPE(TwoDoubleOneByte, TwoDoubleOneByte)
        cfunc = cfunctype(ptr)

        arg = TwoDoubleOneByte(x=1.321321, y=6.54352, z=128)
        ret = cfunc(arg)
        print(arg)
        print(ret)

        self.assertClose(arg.x * arg.y, ret.x)
        self.assertClose(arg.x / arg.y, ret.y)
        self.assertEqual(arg.z, ret.z)

tests.append(TestStructMicrosoftABI)

if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_switch
import unittest
from llvm.core import (Module, Type, Builder, Constant)

from .support import TestCase, tests

class TestSwitch(TestCase):
    def test_arg_attr(self):
        m = Module.new('oifjda')
        fnty = Type.function(Type.void(), [Type.int()])
        func = m.add_function(fnty, 'foo')
        bb = func.append_basic_block('')
        bbdef = func.append_basic_block('')
        bbsw1 = func.append_basic_block('')
        bbsw2 = func.append_basic_block('')
        bldr = Builder.new(bb)

        swt = bldr.switch(func.args[0], bbdef, n=2)
        swt.add_case(Constant.int(Type.int(), 0), bbsw1)
        swt.add_case(Constant.int(Type.int(), 1), bbsw2)

        bldr.position_at_end(bbsw1)
        bldr.ret_void()

        bldr.position_at_end(bbsw2)
        bldr.ret_void()

        bldr.position_at_end(bbdef)
        bldr.ret_void()

        func.verify()

tests.append(TestSwitch)

if __name__ == '__main__':
    unittest.main()


########NEW FILE########
__FILENAME__ = test_target_machines
import unittest
import llvm.core as lc
import llvm.ee as le
from llvm.core import Type, Builder
from .support import TestCase, tests, skip_if

# Check PTX backend
if le.initialize_target('PTX', noraise=True):
    PTX_ARCH = 'ptx64'
elif le.initialize_target('NVPTX', noraise=True):
    PTX_ARCH = 'nvptx64'
else:
    PTX_ARCH = None

class TestTargetMachines(TestCase):
    '''Exercise target machines

    Require PTX backend
    '''
    def test_native(self):
        m, _ = self._build_module()
        tm = le.EngineBuilder.new(m).select_target()

        self.assertTrue(tm.target_name)
        self.assertTrue(tm.target_data)
        self.assertTrue(tm.target_short_description)
        self.assertTrue(tm.triple)
        self.assertIn('foo', tm.emit_assembly(m))
        self.assertTrue(le.get_host_cpu_name())

    @skip_if(not PTX_ARCH, msg='LLVM is not compiled with PTX enabled')
    def test_ptx(self):
        arch = PTX_ARCH
        print(arch)
        m, func = self._build_module()
        func.calling_convention = lc.CC_PTX_KERNEL # set calling conv
        ptxtm = le.TargetMachine.lookup(arch=arch, cpu='sm_20')
        self.assertTrue(ptxtm.triple)
        self.assertTrue(ptxtm.cpu)
        ptxasm = ptxtm.emit_assembly(m)
        self.assertIn('foo', ptxasm)
        if arch == 'nvptx64':
            self.assertIn('.address_size 64', ptxasm)
        self.assertIn('sm_20', ptxasm)

    def _build_module(self):
        m = lc.Module.new('TestTargetMachines')

        fnty = Type.function(Type.void(), [])
        func = m.add_function(fnty, name='foo')

        bldr = Builder.new(func.append_basic_block('entry'))
        bldr.ret_void()
        m.verify()
        return m, func


tests.append(TestTargetMachines)

if __name__ == '__main__':
    unittest.main()


########NEW FILE########
__FILENAME__ = test_type_hash
import unittest
from llvm.core import Type
from .support import TestCase, tests

class TestTypeHash(TestCase):
    def test_scalar_type(self):
        i32a = Type.int(32)
        i32b = Type.int(32)
        i64a = Type.int(64)
        i64b = Type.int(64)
        ts = set([i32a, i32b, i64a, i64b])
        self.assertTrue(len(ts))
        self.assertTrue(i32a in ts)
        self.assertTrue(i64b in ts)

    def test_struct_type(self):
        ta = Type.struct([Type.int(32), Type.float()])
        tb = Type.struct([Type.int(32), Type.float()])
        tc = Type.struct([Type.int(32), Type.int(32), Type.float()])
        ts = set([ta, tb, tc])
        self.assertTrue(len(ts) == 2)
        self.assertTrue(ta in ts)
        self.assertTrue(tb in ts)
        self.assertTrue(tc in ts)

tests.append(TestTypeHash)

if __name__ == '__main__':
    unittest.main()


########NEW FILE########
__FILENAME__ = test_uses
import unittest
from llvm.core import Module, Type, Builder, Constant

from .support import TestCase, tests

class TestUses(TestCase):

    def test_uses(self):
        m = Module.new('a')
        t = Type.int()
        ft = Type.function(t, [t, t, t])
        f = m.add_function(ft, "func")
        b = f.append_basic_block('entry')
        bld = Builder.new(b)
        tmp1 = bld.add(Constant.int(t, 100), f.args[0], "tmp1")
        tmp2 = bld.add(tmp1, f.args[1], "tmp2")
        tmp3 = bld.add(tmp1, f.args[2], "tmp3")
        bld.ret(tmp3)

        # Testing use count
        self.assertEqual(f.args[0].use_count, 1)
        self.assertEqual(f.args[1].use_count, 1)
        self.assertEqual(f.args[2].use_count, 1)
        self.assertEqual(tmp1.use_count, 2)
        self.assertEqual(tmp2.use_count, 0)
        self.assertEqual(tmp3.use_count, 1)

        # Testing uses
        self.assert_(f.args[0].uses[0] is tmp1)
        self.assertEqual(len(f.args[0].uses), 1)
        self.assert_(f.args[1].uses[0] is tmp2)
        self.assertEqual(len(f.args[1].uses), 1)
        self.assert_(f.args[2].uses[0] is tmp3)
        self.assertEqual(len(f.args[2].uses), 1)
        self.assertEqual(len(tmp1.uses), 2)
        self.assertEqual(len(tmp2.uses), 0)
        self.assertEqual(len(tmp3.uses), 1)

tests.append(TestUses)

if __name__ == '__main__':
    unittest.main()


########NEW FILE########
__FILENAME__ = test_volatile
import unittest
from llvm.core import Module, Type, Builder
from .support import TestCase, tests

class TestVolatile(TestCase):

    def test_volatile(self):
        mod = Module.new('mod')
        functype = Type.function(Type.void(), [])
        func = mod.add_function(functype, name='foo')
        bb = func.append_basic_block('entry')
        bldr = Builder.new(bb)
        ptr = bldr.alloca(Type.int())

        # test load inst
        val = bldr.load(ptr)
        self.assertFalse(val.is_volatile, "default must be non-volatile")
        val.set_volatile(True)
        self.assertTrue(val.is_volatile, "fail to set volatile")
        val.set_volatile(False)
        self.assertFalse(val.is_volatile, "fail to unset volatile")

        # test store inst
        store_inst = bldr.store(val, ptr)
        self.assertFalse(store_inst.is_volatile, "default must be non-volatile")
        store_inst.set_volatile(True)
        self.assertTrue(store_inst.is_volatile, "fail to set volatile")
        store_inst.set_volatile(False)
        self.assertFalse(store_inst.is_volatile, "fail to unset volatile")

    def test_volatile_another(self):
        mod = Module.new('mod')
        functype = Type.function(Type.void(), [])
        func = mod.add_function(functype, name='foo')
        bb = func.append_basic_block('entry')
        bldr = Builder.new(bb)
        ptr = bldr.alloca(Type.int())

        # test load inst
        val = bldr.load(ptr, volatile=True)
        self.assertTrue(val.is_volatile, "volatile kwarg does not work")
        val.set_volatile(False)
        self.assertFalse(val.is_volatile, "fail to unset volatile")
        val.set_volatile(True)
        self.assertTrue(val.is_volatile, "fail to set volatile")

        # test store inst
        store_inst = bldr.store(val, ptr, volatile=True)
        self.assertTrue(store_inst.is_volatile, "volatile kwarg does not work")
        store_inst.set_volatile(False)
        self.assertFalse(store_inst.is_volatile, "fail to unset volatile")
        store_inst.set_volatile(True)
        self.assertTrue(store_inst.is_volatile, "fail to set volatile")

tests.append(TestVolatile)

if __name__ == '__main__':
    unittest.main()


########NEW FILE########
__FILENAME__ = check_intrinsics
from __future__ import print_function, absolute_import
import sys
from llvm.core import Type, Function, Builder, Module
import llvm.core as lc
import llvm.ee as le
import multiprocessing
from ctypes import *

INTRINSICS = {}

CTYPES_MAP = {
    Type.int(): c_int32,
    Type.int(64): c_int64,
    Type.float(): c_float,
    Type.double(): c_double,
}


def register(name, retty, *args):
    def wrap(fn):
        INTRINSICS[name] = (retty, args), fn
        return fn
    return wrap


def intr_impl(intrcode, *types):
    def impl(module, builder, args):
        intr = Function.intrinsic(module, intrcode, types)
        r = builder.call(intr, args)
        return r
    return impl


register("llvm.powi.f64", Type.double(), Type.double(), Type.int())\
        (intr_impl(lc.INTR_POWI, Type.double()))

register("llvm.powi.f32", Type.float(), Type.float(), Type.int())\
        (intr_impl(lc.INTR_POWI, Type.float()))

register("llvm.pow.f64", Type.double(), Type.double(), Type.double())\
        (intr_impl(lc.INTR_POW, Type.double()))

register("llvm.pow.f32", Type.float(), Type.float(), Type.float())\
        (intr_impl(lc.INTR_POW, Type.float()))

register("llvm.sin.f64", Type.double(), Type.double())\
        (intr_impl(lc.INTR_SIN, Type.double()))

register("llvm.sin.f32", Type.float(), Type.float())\
        (intr_impl(lc.INTR_SIN, Type.float()))

register("llvm.cos.f64", Type.double(), Type.double())\
        (intr_impl(lc.INTR_COS, Type.double()))

register("llvm.cos.f32", Type.float(), Type.float())\
        (intr_impl(lc.INTR_COS, Type.float()))

register("llvm.log.f64", Type.double(), Type.double())\
        (intr_impl(lc.INTR_LOG, Type.double()))

register("llvm.log.f32", Type.float(), Type.float())\
        (intr_impl(lc.INTR_LOG, Type.float()))

register("llvm.log2.f64", Type.double(), Type.double())\
        (intr_impl(lc.INTR_LOG2, Type.double()))

register("llvm.log2.f32", Type.float(), Type.float())\
        (intr_impl(lc.INTR_LOG2, Type.float()))

register("llvm.log10.f64", Type.double(), Type.double())\
        (intr_impl(lc.INTR_LOG10, Type.double()))

register("llvm.log10.f32", Type.float(), Type.float())\
        (intr_impl(lc.INTR_LOG10, Type.float()))

register("llvm.sqrt.f64", Type.double(), Type.double())\
        (intr_impl(lc.INTR_SQRT, Type.double()))

register("llvm.sqrt.f32", Type.float(), Type.float())\
        (intr_impl(lc.INTR_SQRT, Type.float()))

register("llvm.exp.f64", Type.double(), Type.double())\
        (intr_impl(lc.INTR_EXP, Type.double()))

register("llvm.exp.f32", Type.float(), Type.float())\
        (intr_impl(lc.INTR_EXP, Type.float()))

register("llvm.exp2.f64", Type.double(), Type.double())\
        (intr_impl(lc.INTR_EXP2, Type.double()))

register("llvm.exp2.f32", Type.float(), Type.float())\
        (intr_impl(lc.INTR_EXP2, Type.float()))

register("llvm.fabs.f64", Type.double(), Type.double())\
        (intr_impl(lc.INTR_FABS, Type.double()))

register("llvm.fabs.f32", Type.float(), Type.float())\
        (intr_impl(lc.INTR_FABS, Type.float()))

register("llvm.floor.f64", Type.double(), Type.double())\
        (intr_impl(lc.INTR_FLOOR, Type.double()))

register("llvm.floor.f32", Type.float(), Type.float())\
        (intr_impl(lc.INTR_FLOOR, Type.float()))


def build_test(name):
    (retty, args), impl = INTRINSICS[name]
    module = Module.new("test.%s" % name)
    fn = module.add_function(Type.function(retty, args), name="test_%s" % name)
    builder = Builder.new(fn.append_basic_block(""))
    retval = impl(module, builder, fn.args)
    builder.ret(retval)
    fn.verify()
    module.verify()
    return module, fn


def run_test(name):
    module, fn = build_test(name)
    eb = le.EngineBuilder.new(module).mcjit(True)
    engine = eb.create()
    ptr = engine.get_pointer_to_function(fn)

    argtys = fn.type.pointee.args
    retty = fn.type.pointee.return_type
    cargtys = [CTYPES_MAP[a] for a in argtys]
    cretty = CTYPES_MAP[retty]
    cfunc = CFUNCTYPE(cretty, *cargtys)(ptr)
    args = [1] * len(cargtys)
    cfunc(*args)


def spawner(name):
    print("Testing %s" % name)
    proc = multiprocessing.Process(target=run_test, args=(name,))

    print('-' * 80)
    proc.start()
    proc.join()

    if proc.exitcode != 0:
        print("FAILED")
        ok = False
    else:
        print("PASSED")
        ok = True
    print('=' * 80)
    print()

    return ok

USAGE = """
Args: [name]

name: intrinsic name to test

If no name is given, test all intrinsics.

"""


def main(argv=()):
    if len(argv) == 1:
        intrname = argv[1]
        spawner(intrname)
    elif not argv:
        failed = []
        for name in sorted(INTRINSICS):
            if not spawner(name):
                failed.append(name)

        print("Summary:")
        for name in failed:
            print("%s failed" % name)
    else:
        print(USAGE)


if __name__ == '__main__':
    main(argv=sys.argv[1:])

########NEW FILE########
__FILENAME__ = avx_support
"""
Auto-detect avx and xsave

According to Intel manual [0], both AVX and XSAVE features must be present to
use AVX instructions.

References:

[0] Intel Architecture Instruction Set Extensions Programming Reference

http://software.intel.com/sites/default/files/m/a/b/3/4/d/41604-319433-012a.pdf

"""

import sys
import os
import subprocess
import contextlib


def detect_avx_support(option='detect'):
    '''Detect AVX support'''
    option = os.environ.get('LLVMPY_AVX_SUPPORT', option).lower()
    if option in ('disable', '0', 'false'):
        return False
    elif option in ('enable', '1', 'true'):
        return True
    else: # do detection
        plat = sys.platform
        if plat.startswith('darwin'):
            return detect_osx_like()
        elif plat.startswith('win32'):
            return False # don't know how to detect in windows
        else:
            return detect_unix_like()

def detect_unix_like():
    try:
        info = open('/proc/cpuinfo')
    except IOError:
        return False

    with contextlib.closing(info):
        for line in info:
            if line.lstrip().startswith('flags'):
                features = line.split()
                if 'avx' in features and 'xsave' in features:
                    # enable AVX if flags contain AVX
                    return True
        return False


@contextlib.contextmanager
def _close_popen(popen):
    if sys.version_info[0] >= 3:
        with popen:
            yield
    else:
        yield
        popen.stdout.close()


def detect_osx_like():
    try:
        info = subprocess.Popen(['sysctl', '-n', 'machdep.cpu.features'],
                                stdout=subprocess.PIPE)
    except OSError:
        return False

    with _close_popen(info):
        features = info.stdout.read().decode('UTF8')
        features = features.split()
        return 'AVX1.0' in features and 'OSXSAVE' in features and 'XSAVE' in features


if __name__ == '__main__':
    print("AVX support: %s" % detect_avx_support())

########NEW FILE########
__FILENAME__ = _version

IN_LONG_VERSION_PY = True
# This file helps to compute a version number in source trees obtained from
# git-archive tarball (such as those provided by github's download-from-tag
# feature). Distribution tarballs (build by setup.py sdist) and build
# directories (produced by setup.py build) will contain a much shorter file
# that just contains the computed version number.

# This file is released into the public domain. Generated by
# versioneer-0.7+ (https://github.com/warner/python-versioneer)

# these strings will be replaced by git during git-archive
git_refnames = "$Format:%d$"
git_full = "$Format:%H$"
GIT = "git"

import subprocess
import sys

def run_command(args, cwd=None, verbose=False):
    try:
        # remember shell=False, so use git.cmd on windows, not just git
        p = subprocess.Popen(args, stdout=subprocess.PIPE, cwd=cwd)
    except EnvironmentError:
        e = sys.exc_info()[1]
        if verbose:
            print("unable to run %s" % args[0])
            print(e)
        return None
    stdout = p.communicate()[0].strip()
    if sys.version >= '3':
        stdout = stdout.decode()
    if p.returncode != 0:
        if verbose:
            print("unable to run %s (error)" % args[0])
        return None
    return stdout


import sys
import re
import os.path

def get_expanded_variables(versionfile_source):
    # the code embedded in _version.py can just fetch the value of these
    # variables. When used from setup.py, we don't want to import
    # _version.py, so we do it with a regexp instead. This function is not
    # used from _version.py.
    variables = {}
    try:
        for line in open(versionfile_source,"r").readlines():
            if line.strip().startswith("git_refnames ="):
                mo = re.search(r'=\s*"(.*)"', line)
                if mo:
                    variables["refnames"] = mo.group(1)
            if line.strip().startswith("git_full ="):
                mo = re.search(r'=\s*"(.*)"', line)
                if mo:
                    variables["full"] = mo.group(1)
    except EnvironmentError:
        pass
    return variables

def versions_from_expanded_variables(variables, tag_prefix, verbose=False):
    refnames = variables["refnames"].strip()
    if refnames.startswith("$Format"):
        if verbose:
            print("variables are unexpanded, not using")
        return {} # unexpanded, so not in an unpacked git-archive tarball
    refs = set([r.strip() for r in refnames.strip("()").split(",")])
    for ref in list(refs):
        if not re.search(r'\d', ref):
            if verbose:
                print("discarding '%s', no digits" % ref)
            refs.discard(ref)
            # Assume all version tags have a digit. git's %d expansion
            # behaves like git log --decorate=short and strips out the
            # refs/heads/ and refs/tags/ prefixes that would let us
            # distinguish between branches and tags. By ignoring refnames
            # without digits, we filter out many common branch names like
            # "release" and "stabilization", as well as "HEAD" and "master".
    if verbose:
        print("remaining refs: %s" % ",".join(sorted(refs)))
    for ref in sorted(refs):
        # sorting will prefer e.g. "2.0" over "2.0rc1"
        if ref.startswith(tag_prefix):
            r = ref[len(tag_prefix):]
            if verbose:
                print("picking %s" % r)
            return { "version": r,
                     "full": variables["full"].strip() }
    # no suitable tags, so we use the full revision id
    if verbose:
        print("no suitable tags, using full revision id")
    return { "version": variables["full"].strip(),
             "full": variables["full"].strip() }

def versions_from_vcs(tag_prefix, versionfile_source, verbose=False):
    # this runs 'git' from the root of the source tree. That either means
    # someone ran a setup.py command (and this code is in versioneer.py, so
    # IN_LONG_VERSION_PY=False, thus the containing directory is the root of
    # the source tree), or someone ran a project-specific entry point (and
    # this code is in _version.py, so IN_LONG_VERSION_PY=True, thus the
    # containing directory is somewhere deeper in the source tree). This only
    # gets called if the git-archive 'subst' variables were *not* expanded,
    # and _version.py hasn't already been rewritten with a short version
    # string, meaning we're inside a checked out source tree.

    try:
        here = os.path.abspath(__file__)
    except NameError:
        # some py2exe/bbfreeze/non-CPython implementations don't do __file__
        return {} # not always correct

    # versionfile_source is the relative path from the top of the source tree
    # (where the .git directory might live) to this file. Invert this to find
    # the root from __file__.
    root = here
    if IN_LONG_VERSION_PY:
        for i in range(len(versionfile_source.split("/"))):
            root = os.path.dirname(root)
    else:
        root = os.path.dirname(here)
    if not os.path.exists(os.path.join(root, ".git")):
        if verbose:
            print("no .git in %s" % root)
        return {}

    stdout = run_command([GIT, "describe", "--tags", "--dirty", "--always"],
                         cwd=root)
    if stdout is None:
        return {}
    if not stdout.startswith(tag_prefix):
        if verbose:
            print("tag '%s' doesn't start with prefix '%s'" % (stdout, tag_prefix))
        return {}
    tag = stdout[len(tag_prefix):]
    stdout = run_command([GIT, "rev-parse", "HEAD"], cwd=root)
    if stdout is None:
        return {}
    full = stdout.strip()
    if tag.endswith("-dirty"):
        full += "-dirty"
    return {"version": tag, "full": full}


def versions_from_parentdir(parentdir_prefix, versionfile_source, verbose=False):
    if IN_LONG_VERSION_PY:
        # We're running from _version.py. If it's from a source tree
        # (execute-in-place), we can work upwards to find the root of the
        # tree, and then check the parent directory for a version string. If
        # it's in an installed application, there's no hope.
        try:
            here = os.path.abspath(__file__)
        except NameError:
            # py2exe/bbfreeze/non-CPython don't have __file__
            return {} # without __file__, we have no hope
        # versionfile_source is the relative path from the top of the source
        # tree to _version.py. Invert this to find the root from __file__.
        root = here
        for i in range(len(versionfile_source.split("/"))):
            root = os.path.dirname(root)
    else:
        # we're running from versioneer.py, which means we're running from
        # the setup.py in a source tree. sys.argv[0] is setup.py in the root.
        here = os.path.abspath(sys.argv[0])
        root = os.path.dirname(here)

    # Source tarballs conventionally unpack into a directory that includes
    # both the project name and a version string.
    dirname = os.path.basename(root)
    if not dirname.startswith(parentdir_prefix):
        if verbose:
            print("guessing rootdir is '%s', but '%s' doesn't start with prefix '%s'" %
                  (root, dirname, parentdir_prefix))
        return None
    return {"version": dirname[len(parentdir_prefix):], "full": ""}

tag_prefix = ""
parentdir_prefix = "llvmpy-"
versionfile_source = "llvm/_version.py"

def get_versions(default={"version": "unknown", "full": ""}, verbose=False):
    variables = { "refnames": git_refnames, "full": git_full }
    ver = versions_from_expanded_variables(variables, tag_prefix, verbose)
    if not ver:
        ver = versions_from_vcs(tag_prefix, versionfile_source, verbose)
    if not ver:
        ver = versions_from_parentdir(parentdir_prefix, versionfile_source,
                                      verbose)
    if not ver:
        ver = default
    return ver

########NEW FILE########
__FILENAME__ = llvm-config-win32
import re
import sys
from distutils.spawn import find_executable
from os.path import abspath, dirname, isfile, join
from os import listdir
from subprocess import Popen, PIPE


def find_llvm_tblgen():
    path = find_executable('llvm-tblgen')
    if path is None:
        sys.exit('Error: could not locate llvm-tblgen')
    return path


def find_llvm_prefix():
    return abspath(dirname(dirname(find_llvm_tblgen())))


def ensure_file(path):
    if not isfile(path):
        sys.exit('Error: no file: %r' % path)


def get_llvm_version():
    args = [find_llvm_tblgen(), '--version']
    p = Popen(args, stdout=PIPE, stderr=PIPE)
    stdout, stderr = p.communicate()
    if stderr:
        sys.exit("Error: %r stderr is:\n%s" % (args, stderr.decode()))
    out = stdout.decode().strip()
    pat = re.compile(r'llvm\s+version\s+(\d+\.\d+\S*)', re.I)
    m = pat.search(out)
    if m is None:
        sys.exit('Error: could not parse version in:' + out)
    return m.group(1)


def libs_options():
    # NOTE: instead of actually looking at the components requested,
    #       we just print out a bunch of libs
    for lib in """
Advapi32
Shell32
""".split():
        print('-l%s' % lib)

    bpath = join(find_llvm_prefix(), 'lib')
    for filename in listdir(bpath):
        filepath = join(bpath, filename)
        if isfile(filepath) and filename.endswith('.lib') and filename.startswith('LLVM'):
            name = filename.split('.', 1)[0]
            print('-l%s' % name)

def main():
    try:
        option = sys.argv[1]
    except IndexError:
        sys.exit('Error: option missing')

    if option == '--version':
        print(get_llvm_version())

    elif option == '--targets-built':
        print('X86')  # just do X86

    elif option == '--libs':
        libs_options()

    elif option == '--includedir':
        incdir = join(find_llvm_prefix(), 'include')
        ensure_file(join(incdir, 'llvm' , 'Linker.h'))
        print(incdir)

    elif option == '--libdir':
        libdir = join(find_llvm_prefix(), 'lib')
        ensure_file(join(libdir, 'LLVMCore.lib'))
        print(libdir)

    elif option in ('--ldflags', '--components'):
        pass

    else:
        sys.exit('Error: Unrecognized llvm-config option %r' % option)


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = build
from os import chdir
from os.path import dirname
import sys, subprocess

scriptdir = dirname(__file__)
chdir(scriptdir)

subprocess.check_call([sys.executable, 'gen/gen.py', 'api', 'src'])

########NEW FILE########
__FILENAME__ = capsule
from weakref import WeakValueDictionary
from collections import defaultdict
import logging
from llvmpy._capsule import (unwrap, has_ownership, downcast, wrap,
                             getClassName, getName, getPointer, Capsule)


logger = logging.getLogger(__name__)

NO_DEBUG = False


def silent_logger():
    '''
    Silent logger for unless we have a error message.
    '''
    global NO_DEBUG
    logger.setLevel(logging.ERROR)
    NO_DEBUG = True

# comment out the line below to re-enable logging at DEBUG level.
silent_logger()


def set_debug(enabled):
    '''
    Side-effect: configure logger with it is not configured.
    '''
    if enabled:
        # If no handlers are configured for the root logger,
        # build a default handler for debugging.
        # Can we do better?
        if not logger.root.handlers:
            logging.basicConfig()
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.WARNING)


#class Capsule(object):
#    "Wraps PyCapsule so that we can build weakref of it."
#    from ._capsule import check, getClassName, getName, getPointer
#    __slots__ = "capsule"
#
#    def __init__(self, capsule):
#        assert Capsule.valid(capsule)
#        self.capsule = capsule
#
#        #weak = WeakRef(self, _capsule_weakref_dtor)
#        #weak.pointer = self.pointer
#        #weak.capsule = capsule
#        #weak.name = self.name
#        #_capsule2weak[self] = weak
#        _addr2refct[self.pointer] += 1
#
#    @property
#    def classname(self):
#        return self.getClassName(self.capsule)
#
#    @property
#    def name(self):
#        return self.getName(self.capsule)
#
#    @property
#    def pointer(self):
#        return self.getPointer(self.capsule)
#
#    @staticmethod
#    def valid(capsule):
#        return Capsule.check(capsule)
#
#    def get_class(self):
#        return _pyclasses[self.classname]
#
#    def instantiate(self):
#        cls = self.get_class()
#        return cls(self)
#
#    def __eq__(self, other):
#        if isinstance(other, Capsule) and self.pointer == other.pointer:
#            assert self.name == other.name
#            return True
#        else:
#            return False
#
#    def __hash__(self):
#        return hash((self.pointer, self.name))
#
#    def __ne__(self, other):
#        return not (self == other)



_addr2refct = defaultdict(lambda: 0)
#_capsule2weak = WeakKeyDictionary()
_addr2dtor = {}
_pyclasses = {}

# Cache {cls: {addr: obj}}
# NOTE: The same 'addr' may appear in multiple class bins.
_cache = defaultdict(WeakValueDictionary)


def release_ownership(old):
    logger.debug('Release %s', old)
    addr = getPointer(old)
    name = getName(old)
    if _addr2dtor.get((name, addr)) is None:
        clsname = getClassName(old)
        if not _pyclasses[clsname]._has_dtor():
            return
            # Guard duplicated release
        raise Exception("Already released")
    _addr2dtor[(name, addr)] = None


def obtain_ownership(cap):
    cls = cap.get_class()
    if cls._has_dtor():
        addr = cap.pointer
        name = cap.name
        assert _addr2dtor[(name, addr)] is None
        _addr2dtor[(name, addr)] = cls._delete_


#def has_ownership(cap):
#    addr = Capsule.getPointer(cap)
#    name = Capsule.getName(cap)
#    return _addr2dtor.get((name, addr)) is not None


#def wrap(cap, owned=False):
#    '''Wrap a PyCapsule with the corresponding Wrapper class.
#    If `cap` is not a PyCapsule, returns `cap`
#    '''
#    if not Capsule.valid(cap):
#        if isinstance(cap, list):
#            return list(map(wrap, cap))
#        return cap     # bypass if cap is not a PyCapsule and not a list
#
#    cap = Capsule(cap)
#    cls = cap.get_class()
#    addr = cap.pointer
#    name = cap.name
#    # lookup cached object
#    if cls in _cache and addr in _cache[cls]:
#        obj = _cache[cls][addr]
#    else:
#        if not owned and cls._has_dtor():
#            _addr2dtor[(name, addr)] = cls._delete_
#        obj = cap.instantiate()
#        _cache[cls][addr] = obj    # cache it
#    return obj

#def unwrap(obj):
    '''Unwrap a Wrapper instance into the underlying PyCapsule.
    If `obj` is not a Wrapper instance, returns `obj`.
    '''
#    if isinstance(obj, Wrapper):
#        return obj._ptr
#    else:
#        return obj


def register_class(clsname):
    def _wrapped(cls):
        _pyclasses[clsname] = cls
        return cls

    return _wrapped


class Wrapper(object):
    __slots__ = '__capsule'

    def __init__(self, capsule):
        self.__capsule = capsule

    def __del__(self):
        if _addr2refct is None:
            # System is tearing down
            # No need to free anything
            return

        item = self.__capsule
        addr = item.pointer
        name = item.name

        _addr2refct[addr] -= 1
        refct = _addr2refct[addr]
        assert refct >= 0, "RefCt drop below 0"
        if refct == 0:
            dtor = _addr2dtor.pop((name, addr), None)
            if dtor is not None:
                if not NO_DEBUG:
                    # Some globals in logger could be removed by python GC
                    # at interpreter teardown.
                    # That can cause exception raised and ignored message.
                    logger.debug('Destroy %s %s', name, hex(addr))
                dtor(item.capsule)

    @property
    def _capsule(self):
        return self.__capsule

    @property
    def _ptr(self):
        return self._capsule.capsule

    def __hash__(self):
        return hash(self._capsule)

    def __eq__(self, other):
        if isinstance(other, Wrapper):
            return self._capsule == other._capsule

    def __ne__(self, other):
        return not (self == other)

    def _downcast(self, newcls):
        return downcast(self, newcls)

    @classmethod
    def _has_dtor(cls):
        return hasattr(cls, '_delete_')


#def downcast(obj, cls):
#    from . import _api
#
#    if type(obj) is cls:
#        return obj
#    fromty = obj._llvm_type_
#    toty = cls._llvm_type_
#    logger.debug("Downcast %s to %s", fromty, toty)
#    fname = 'downcast_%s_to_%s' % (fromty, toty)
#    fname = fname.replace('::', '_')
#    if not hasattr(_api.downcast, fname):
#        fmt = "Downcast from %s to %s is not supported"
#        raise TypeError(fmt % (fromty, toty))
#    caster = getattr(_api.downcast, fname)
#    old = unwrap(obj)
#    new = caster(old)
#    used_to_own = has_ownership(old)
#    res = wrap(new, owned=not used_to_own)
#    if not res:
#        raise ValueError("Downcast failed")
#    return res

########NEW FILE########
__FILENAME__ = extra
'''
Wrapped the extra functions in _api.so
'''

from llvmpy import capsule
from llvmpy import _api
#
# Re-export the native API from the _api.extra and wrap the functions
#

def _wrapper(func):
    "Wrap the re-exported functions"
    def _core(*args):
        unwrapped = list(map(capsule.unwrap, args))
        ret = func(*unwrapped)
        return capsule.wrap(ret)
    return _core

def _init(glob):
    for k, v in _api.extra.__dict__.items():
        glob[k] = _wrapper(v)

_init(globals())



########NEW FILE########
__FILENAME__ = binding
import inspect, textwrap
import codegen as cg
import os

_rank = 0
namespaces = {}

RESERVED = frozenset(['None'])


def makedir(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)


class SubModule(object):
    def __init__(self):
        self.methods = []
        self.enums = []
        self.classes = []
        self.namespaces = []
        self.attrs = []
        self.includes = set()

    def aggregate_includes(self):
        includes = set(self.includes)
        for unit in self.iter_all():
            if isinstance(unit, SubModule):
                includes |= unit.aggregate_includes()
            else:
                includes |= unit.includes
        return includes

    def aggregate_downcast(self):
        dclist = []
        for cls in self.classes:
            for bcls in cls.downcastables:
                from_to = bcls.fullname, cls.fullname
                name = 'downcast_%s_to_%s' % tuple(map(cg.mangle, from_to))
                fn = Function(namespaces[''], name, ptr(cls), ptr(bcls))
                dclist.append((from_to, fn))
        for ns in self.namespaces:
            dclist.extend(ns.aggregate_downcast())
        return dclist

    def iter_all(self):
        for fn in self.methods:
            yield fn
        for cls in self.classes:
            yield cls
        for enum in self.enums:
            yield enum
        for attr in self.attrs:
            yield attr
        for ns in self.namespaces:
            yield ns


    def generate_method_table(self, println):
        writer = cg.CppCodeWriter(println)
        writer.println('static')
        writer.println('PyMethodDef meth_%s[] = {' % cg.mangle(self.fullname))
        with writer.indent():
            fmt = '{ "%(name)s", (PyCFunction)%(func)s, METH_VARARGS, NULL },'
            for meth in self.methods:
                name = meth.name
                func = meth.c_name
                writer.println(fmt % locals())
            for enumkind in self.enums:
                for enum in enumkind.value_names:
                    name = enum
                    func = enumkind.c_name(enum)
                    writer.println(fmt % locals())
            for attr in self.attrs:
                # getter
                name = attr.getter_name
                func = attr.getter_c_name
                writer.println(fmt % locals())
                # setter
                name = attr.setter_name
                func = attr.setter_c_name
                writer.println(fmt % locals())
            writer.println('{ NULL },')
        writer.println('};')
        writer.println()

#    def generate_downcasts(self, println):
#        for ((fromty, toty), fn) in self.downcastlist:
#            name = fn.name
#            fmt = '''
#static
#%(toty)s* %(name)s(%(fromty)s* arg)
#{
#    return typecast< %(toty)s >::from(arg);
#}
#                '''
#            println(fmt % locals())
#
#            fn.generate_cpp(println)

    def generate_cpp(self, println, extras=()):
        for unit in self.iter_all():
            unit.generate_cpp(println)
        self.generate_method_table(println)
        self.generate_submodule_table(println, extras=extras)

    def generate_submodule_table(self, println, extras=()):
        writer = cg.CppCodeWriter(println)
        writer.println('static')
        name = cg.mangle(self.fullname)
        writer.println('SubModuleEntry submodule_%(name)s[] = {' % locals())
        with writer.indent():
            for cls in self.classes:
                name = cls.name
                table = cg.mangle(cls.fullname)
                writer.println('{ "%(name)s", meth_%(table)s, NULL },' %
                               locals())
            for ns in self.namespaces:
                name = ns.localname
                table = cg.mangle(ns.fullname)
                fmt = '{ "%(name)s", meth_%(table)s, submodule_%(table)s },'
                writer.println(fmt % locals())
            for name, table in extras:
                writer.println('{ "%(name)s", %(table)s, NULL },' % locals())
            writer.println('{ NULL }')
        writer.println('};')
        writer.println('')

    def generate_py(self, rootdir='.', name=''):
        name = name or self.localname
        if self.namespaces: # should make new directory
            path = os.path.join(rootdir, name)
            makedir(path)
            filepath = os.path.join(path, '__init__.py')
        else:
            filepath = os.path.join(rootdir, '%s.py' % name)
        with open(filepath, 'w') as pyfile:
            println = cg.wrap_println_from_file(pyfile)
            println('from llvmpy import _api, capsule')
            for ns in self.namespaces:
                println('from . import %s' % ns.localname)
            println()
            for unit in self.iter_all():
                if not isinstance(unit, Namespace):
                    writer = cg.PyCodeWriter(println)
                    unit.compile_py(writer)

        for ns in self.namespaces:
            ns.generate_py(rootdir=path)


class Namespace(SubModule):
    def __init__(self, name):
        SubModule.__init__(self)
        self.name = name = name.lstrip(':')
        namespaces[name] = self

    def Class(self, *bases):
        cls = Class(self, *bases)
        self.classes.append(cls)
        return cls

    def Function(self, *args):
        fn = Function(self, *args)
        self.methods.append(fn)
        return fn

    def CustomFunction(self, *args):
        fn = CustomFunction(self, *args)
        self.methods.append(fn)
        return fn

    def Enum(self, name, *value_names):
        enum = Enum(*value_names)
        enum.parent = self
        enum.name = name
        self.enums.append(enum)
        assert name not in vars(self), 'Duplicated'
        setattr(self, name, enum)
        return enum

    def Namespace(self, name):
        ns = Namespace('::'.join([self.name, name]))
        self.namespaces.append(ns)
        return ns

    @property
    def fullname(self):
        return self.name

    @property
    def py_name(self):
        return self.name.replace('::', '.')

    @property
    def localname(self):
        return self.name.rsplit('::', 1)[-1]

    def __str__(self):
        return self.name

class _Type(object):
    pass

class BuiltinTypes(_Type):
    def __init__(self, name):
        self.name = name

    @property
    def fullname(self):
        return self.name

    def wrap(self, writer, var):
        return var

    def unwrap(self, writer, var):
        return var

Void = BuiltinTypes('void')
Unsigned = BuiltinTypes('unsigned')
UnsignedLongLong = BuiltinTypes('unsigned long long') # used in llvm-3.2
LongLong = BuiltinTypes('long long')
Float = BuiltinTypes('float')
Double = BuiltinTypes('double')
Uint64 = BuiltinTypes('uint64_t')
Int64 = BuiltinTypes('int64_t')
Int = BuiltinTypes('int')
Size_t = BuiltinTypes('size_t')
VoidPtr = BuiltinTypes('void*')
Bool = BuiltinTypes('bool')
StdString = BuiltinTypes('std::string')
ConstStdString = BuiltinTypes('const std::string')
ConstCharPtr = BuiltinTypes('const char*')
PyObjectPtr = BuiltinTypes('PyObject*')
PyObjectPtr.format='O'

class Class(SubModule, _Type):
    format = 'O'

    def __init__(self, ns, *bases):
        SubModule.__init__(self)
        self.ns = ns
        self.bases = bases
        self._is_defined = False
        self.pymethods = []
        self.downcastables = set()

    def __call__(self, defn):
        assert not self._is_defined
        # process the definition in "defn"
        self.name = getattr(defn, '_name_', defn.__name__)

        for k, v in defn.__dict__.items():
            if isinstance(v, Method):
                self.methods.append(v)
                if isinstance(v, Constructor):
                    for sig in v.signatures:
                        sig[0] = ptr(self)
                v.name = k
                v.parent = self
            elif isinstance(v, Enum):
                self.enums.append(v)
                v.name = k
                v.parent = self
                assert k not in vars(self), "Duplicated: %s" % k
                setattr(self, k, v)
            elif isinstance(v, Attr):
                self.attrs.append(v)
                v.name = k
                v.parent = self
            elif isinstance(v, CustomPythonMethod):
                self.pymethods.append(v)
            elif k == '_include_':
                if isinstance(v, str):
                    self.includes.add(v)
                else:
                    for i in v:
                        self.includes.add(i)
            elif k == '_realname_':
                self.realname = v
            elif k == '_downcast_':
                if isinstance(v, Class):
                    self.downcastables.add(v)
                else:
                    for i in v:
                        self.downcastables.add(i)
        return self

    def compile_py(self, writer):
        clsname = self.name
        bases = 'capsule.Wrapper'
        if self.bases:
            bases = ', '.join(x.name for x in self.bases)
        writer.println('@capsule.register_class("%s")' % self.fullname)
        with writer.block('class %(clsname)s(%(bases)s):' % locals()):
            writer.println('_llvm_type_ = "%s"' % self.fullname)
            if self.bases:
                writer.println('__slots__ = ()')
            else:
                writer.println('__slots__ = "__weakref__"')
            for enum in self.enums:
                enum.compile_py(writer)
            for meth in self.methods:
                meth.compile_py(writer)
            for meth in self.pymethods:
                meth.compile_py(writer)
            for attr in self.attrs:
                attr.compile_py(writer)
        writer.println()

    @property
    def capsule_name(self):
        if self.bases:
            return self.bases[-1].capsule_name
        else:
            return self.fullname

    @property
    def fullname(self):
        try:
            name = self.realname
        except AttributeError:
            name = self.name
        return '::'.join([self.ns.fullname, name])

    @property
    def py_name(self):
        ns = self.ns.name.split('::')
        return '.'.join(ns + [self.name])

    def __str__(self):
        return self.fullname

    def unwrap(self, writer, val):
        fmt = 'PyCapsule_GetPointer(%(val)s, "%(name)s")'
        name = self.capsule_name
        raw = writer.declare('void*', fmt % locals())
        writer.die_if_false(raw, verbose=name)
        ptrty = ptr(self).fullname
        ty = self.fullname
        fmt = 'unwrap_as<%(ty)s, %(name)s >::from(%(raw)s)'
        casted = writer.declare(ptrty, fmt % locals())
        writer.die_if_false(casted)
        return casted

    def wrap(self, writer, val):
        copy = 'new %s(%s)' % (self.fullname, val)
        return writer.pycapsule_new(copy, self.capsule_name, self.fullname)


class Enum(object):
    format = 'O'

    def __init__(self, *value_names):
        self.parent = None
        if len(value_names) == 1:
            value_names = list(filter(bool, value_names[0].replace(',', ' ').split()))
        self.value_names = value_names
        self.includes = set()

    @property
    def fullname(self):
        try:
            name = self.realname
        except AttributeError:
            name = self.name
        return '::'.join([self.parent.fullname, name])

    def __str__(self):
        return self.fullname

    def wrap(self, writer, val):
        ret = writer.declare('PyObject*', 'PyInt_FromLong(%s)' % val)
        return ret

    def unwrap(self, writer, val):
        convert_long_to_enum = '(%s)PyInt_AsLong(%s)' % (self.fullname, val)
        ret = writer.declare(self.fullname, convert_long_to_enum)
        return ret

    def c_name(self, enum):
        return cg.mangle("%s_%s_%s" % (self.parent, self.name, enum))

    def generate_cpp(self, println):
        self.compile_cpp(cg.CppCodeWriter(println))

    def compile_cpp(self, writer):
        for enum in self.value_names:
            with writer.py_function(self.c_name(enum)):
                ret = self.wrap(writer, '::'.join([self.parent.fullname, enum]))
                writer.return_value(ret)

    def compile_py(self, writer):
        with writer.block('class %s:' % self.name):
            writer.println('_llvm_type_ = "%s"' % self.fullname)
            for v in self.value_names:
                if v in RESERVED:
                    k = '%s_' % v
                    fmt = '%(k)s = getattr(%(p)s, "%(v)s")()'
                else:
                    k = v
                    fmt = '%(k)s = %(p)s.%(v)s()'
                p = '.'.join(['_api'] + self.parent.fullname.split('::'))
                writer.println(fmt % locals())
        writer.println()


class Method(object):
    _kind_ = 'meth'

    def __init__(self, return_type=Void, *args):
        self.parent = None
        self.signatures = []
        self.includes = set()
        self._add_signature(return_type, *args)
        self.disowning = False

    def _add_signature(self, return_type, *args):
        prev_lens = set(map(len, self.signatures))
        cur_len = len(args) + 1
        if cur_len in prev_lens:
            raise Exception('Only support overloading with different number'
                            ' of arguments')
        self.signatures.append([return_type] + list(args))

    def __ior__(self, method):
        assert type(self) is type(method)
        for sig in method.signatures:
            self._add_signature(sig[0], *sig[1:])
        return self

    @property
    def fullname(self):
        return '::'.join([self.parent.fullname, self.realname]).lstrip(':')

    @property
    def realname(self):
        try:
            return self.__realname
        except AttributeError:
            return self.name

    @realname.setter
    def realname(self, v):
        self.__realname = v

    @property
    def c_name(self):
        return cg.mangle("%s_%s" % (self.parent, self.name))

    def __str__(self):
        return self.fullname

    def generate_cpp(self, println):
        self.compile_cpp(cg.CppCodeWriter(println))

    def compile_cpp(self, writer):
        with writer.py_function(self.c_name):
            if len(self.signatures) == 1:
                sig = self.signatures[0]
                retty = sig[0]
                argtys = sig[1:]
                self.compile_cpp_body(writer, retty, argtys)
            else:
                nargs = writer.declare('Py_ssize_t', 'PyTuple_Size(args)')
                for sig in self.signatures:
                    retty = sig[0]
                    argtys = sig[1:]
                    expect = len(argtys)
                    if (not isinstance(self, StaticMethod) and
                        isinstance(self.parent, Class)):
                        # Is a instance method, add 1 for "this".
                        expect += 1
                    with writer.block('if (%(expect)d == %(nargs)s)' % locals()):
                        self.compile_cpp_body(writer, retty, argtys)
                writer.raises(TypeError, 'Invalid number of args')

    def compile_cpp_body(self, writer, retty, argtys):
        args = writer.parse_arguments('args', ptr(self.parent), *argtys)
        ret = writer.method_call(self.realname, retty.fullname, *args)
        writer.return_value(retty.wrap(writer, ret))

    def compile_py(self, writer):
        decl = writer.function(self.name, args=('self',), varargs='args')
        with decl as (this, varargs):
            unwrap_this = writer.unwrap(this)
            if self.disowning:
                writer.release_ownership(unwrap_this)
            unwrapped = writer.unwrap_many(varargs)
            self.process_ownedptr_args(writer, unwrapped)
            func = '.'.join([self.parent.py_name, self.name])
            ret = writer.call('_api.%s' % func,
                              args=(unwrap_this,), varargs=unwrapped)

            wrapped = writer.wrap(ret, self.is_return_ownedptr())

            writer.return_value(wrapped)
            writer.println()

    def require_only(self, num):
        '''Require only "num" of argument.
        '''
        assert len(self.signatures) == 1
        sig = self.signatures[0]
        ret = sig[0]
        args = sig[1:]
        arg_ct = len(args)

        for i in range(num, arg_ct):
            self._add_signature(ret, *args[:i])

        return self

    def is_return_ownedptr(self):
        retty = self.signatures[0][0]
        return isinstance(retty, ownedptr)

    def process_ownedptr_args(self, writer, unwrapped):
        argtys = self.signatures[0][1:]
        for i, ty in enumerate(argtys):
            if isinstance(ty, ownedptr):
                with writer.block('if len(%s) > %d:' % (unwrapped, i)):
                    writer.release_ownership('%s[%d]' % (unwrapped, i))


class CustomMethod(Method):
    def __init__(self, methodname, retty, *argtys):
        super(CustomMethod, self).__init__(retty, *argtys)
        self.methodname = methodname

    def compile_cpp_body(self, writer, retty, argtys):
        args = writer.parse_arguments('args', ptr(self.parent), *argtys)
        ret = writer.call(self.methodname, retty.fullname, *args)
        writer.return_value(retty.wrap(writer, ret))


class StaticMethod(Method):

    def compile_cpp_body(self, writer, retty, argtys):
        assert isinstance(self.parent, Class)
        args = writer.parse_arguments('args', *argtys)
        ret = self.compile_cpp_call(writer, retty, args)
        writer.return_value(retty.wrap(writer, ret))

    def compile_cpp_call(self, writer, retty, args):
        ret = writer.call(self.fullname, retty.fullname, *args)
        return ret

    def compile_py(self, writer):
        writer.println('@staticmethod')
        decl = writer.function(self.name, varargs='args')
        with decl as varargs:
            unwrapped = writer.unwrap_many(varargs)
            self.process_ownedptr_args(writer, unwrapped)

            func = '.'.join([self.parent.py_name, self.name])
            ret = writer.call('_api.%s' % func, varargs=unwrapped)
            wrapped = writer.wrap(ret, self.is_return_ownedptr())
            writer.return_value(wrapped)
            writer.println()

class CustomStaticMethod(StaticMethod):
    def __init__(self, methodname, retty, *argtys):
        super(CustomStaticMethod, self).__init__(retty, *argtys)
        self.methodname = methodname

    def compile_cpp_body(self, writer, retty, argtys):
        args = writer.parse_arguments('args', *argtys)
        ret = writer.call(self.methodname, retty.fullname, *args)
        writer.return_value(retty.wrap(writer, ret))

class Function(Method):
    _kind_ = 'func'

    def __init__(self, parent, name, return_type=Void, *args):
        super(Function, self).__init__(return_type, *args)
        self.parent = parent
        self.name = name

    def compile_cpp_body(self, writer, retty, argtys):
        args = writer.parse_arguments('args', *argtys)
        ret = writer.call(self.fullname, retty.fullname, *args)
        writer.return_value(retty.wrap(writer, ret))

    def compile_py(self, writer):
        with writer.function(self.name, varargs='args') as varargs:
            unwrapped = writer.unwrap_many(varargs)
            self.process_ownedptr_args(writer, unwrapped)
            func = '.'.join([self.parent.py_name, self.name]).lstrip('.')
            ret = writer.call('_api.%s' % func, varargs=unwrapped)
            wrapped = writer.wrap(ret, self.is_return_ownedptr())
            writer.return_value(wrapped)
        writer.println()

class CustomFunction(Function):
    def __init__(self, parent, name, realname, return_type=Void, *args):
        super(CustomFunction, self).__init__(parent, name, return_type, *args)
        self.realname = realname

    @property
    def fullname(self):
        return self.realname


class Destructor(Method):
    _kind_ = 'dtor'

    def __init__(self):
        super(Destructor, self).__init__()

    def compile_cpp_body(self, writer, retty, argtys):
        assert isinstance(self.parent, Class)
        assert not argtys
        args = writer.parse_arguments('args', ptr(self.parent), *argtys)
        writer.println('delete %s;' % args[0])
        writer.return_value(None)

    def compile_py(self, writer):
        func = '.'.join([self.parent.py_name, self.name])
        writer.println('_delete_ = _api.%s' % func)


class Constructor(StaticMethod):
    _kind_ = 'ctor'

    def __init__(self, *args):
        super(Constructor, self).__init__(Void, *args)

    def compile_cpp_call(self, writer, retty, args):
        alloctype = retty.fullname.rstrip(' *')
        arglist = ', '.join(args)
        stmt = 'new %(alloctype)s(%(arglist)s)' % locals()
        ret = writer.declare(retty.fullname, stmt)
        return ret


class ref(_Type):
    def __init__(self, element):
        assert isinstance(element, Class), type(element)
        self.element = element
        self.const = False

    def __str__(self):
        return self.fullname

    @property
    def fullname(self):
        if self.const:
            return 'const %s&' % self.element.fullname
        else:
            return '%s&' % self.element.fullname

    @property
    def capsule_name(self):
        return self.element.capsule_name

    @property
    def format(self):
        return self.element.format

    def wrap(self, writer, val):
        p = writer.declare(const(ptr(self.element)).fullname, '&%s' % val)
        return writer.pycapsule_new(p, self.capsule_name, self.element.fullname)

    def unwrap(self, writer, val):
        p = self.element.unwrap(writer, val)
        return writer.declare(self.fullname, '*%s' % p)


class ptr(_Type):
    def __init__(self, element):
        assert isinstance(element, Class)
        self.element = element
        self.const = False

    @property
    def fullname(self):
        if self.const:
            return 'const %s*' % self.element
        else:
            return '%s*' % self.element

    @property
    def format(self):
        return self.element.format

    def unwrap(self, writer, val):
        ret = writer.declare(self.fullname, 'NULL')
        with writer.block('if (%(val)s != Py_None)' % locals()):
            val = self.element.unwrap(writer, val)
            writer.println('%(ret)s = %(val)s;' % locals())
        return ret

    def wrap(self, writer, val):
        return writer.pycapsule_new(val, self.element.capsule_name,
                                    self.element.fullname)


class ownedptr(ptr):
    pass


def const(ptr_or_ref):
    ptr_or_ref.const = True
    return ptr_or_ref


class cast(_Type):
    format = 'O'

    def __init__(self, original, target):
        self.original = original
        self.target = target

    @property
    def fullname(self):
        return self.binding_type.fullname

    @property
    def python_type(self):
        if not isinstance(self.target, _Type):
            return self.target
        else:
            return self.original

    @property
    def binding_type(self):
        if isinstance(self.target, _Type):
            return self.target
        else:
            return self.original

    def wrap(self, writer, val):
        dst = self.python_type.__name__
        if dst == 'int':
            unsigned = set([Unsigned, UnsignedLongLong, Uint64,
                            Size_t, VoidPtr])
            signed = set([LongLong, Int64, Int])
            assert self.binding_type in unsigned|signed
            if self.binding_type in signed:
                signflag = 'signed'
            else:
                signflag = 'unsigned'
            fn = 'py_%(dst)s_from_%(signflag)s' % locals()
        else:
            fn = 'py_%(dst)s_from' % locals()
        return writer.call(fn, 'PyObject*', val)

    def unwrap(self, writer, val):
        src = self.python_type.__name__
        dst = self.binding_type.fullname
        ret = writer.declare(dst)
        fn = 'py_%(src)s_to' % locals()
        status = writer.call(fn, 'int', val, ret)
        writer.die_if_false(status)
        return ret


class CustomPythonMethod(object):
    def __init__(self, fn):
        src = inspect.getsource(fn)
        lines = textwrap.dedent(src).splitlines()
        for i, line in enumerate(lines):
            if not line.startswith('@'):
                break
        self.sourcelines = lines[i:]

    def compile_py(self, writer):
        for line in self.sourcelines:
            writer.println(line)


class CustomPythonStaticMethod(CustomPythonMethod):
    def compile_py(self, writer):
        writer.println('@staticmethod')
        super(CustomPythonStaticMethod, self).compile_py(writer)


class Attr(object):
    def __init__(self, getter, setter):
        self.getter = getter
        self.setter = setter
        self.includes = set()

    @property
    def fullname(self):
        try:
            name = self.realname
        except AttributeError:
            name = self.name
        return '::'.join([self.parent.fullname, name])

    def __str__(self):
        return self.fullname

    @property
    def getter_name(self):
        return '%s_get' % self.name

    @property
    def setter_name(self):
        return '%s_set' % self.name

    @property
    def getter_c_name(self):
        return cg.mangle('%s_get' % self.fullname)

    @property
    def setter_c_name(self):
        return cg.mangle('%s_set' % self.fullname)

    def generate_cpp(self, println):
        self.compile_cpp(cg.CppCodeWriter(println))

    def compile_cpp(self, writer):
        # getter
        with writer.py_function(self.getter_c_name):
            (this,) = writer.parse_arguments('args', ptr(self.parent))
            attr = self.name
            ret = writer.declare(self.getter.fullname,
                                 '%(this)s->%(attr)s' % locals())
            writer.return_value(self.getter.wrap(writer, ret))
        # setter
        with writer.py_function(self.setter_c_name):
            (this, value) = writer.parse_arguments('args', ptr(self.parent),
                                                   self.setter)
            attr = self.name
            writer.println('%(this)s->%(attr)s = %(value)s;' % locals())
            writer.return_value(None)

    def compile_py(self, writer):
        name = self.name
        parent = '.'.join(self.parent.fullname.split('::'))
        getter = '.'.join([parent, self.getter_name])
        setter = '.'.join([parent, self.setter_name])
        writer.println('@property')
        with writer.block('def %(name)s(self):' % locals()):
            unself = writer.unwrap('self')
            ret = writer.new_symbol('ret')
            writer.println('%(ret)s = _api.%(getter)s(%(unself)s)' % locals())
            is_ownedptr = isinstance(self.getter, ownedptr)
            writer.return_value(writer.wrap(ret, is_ownedptr))
        writer.println()
        writer.println('@%(name)s.setter' % locals())
        with writer.block('def %(name)s(self, value):' % locals()):
            unself = writer.unwrap('self')
            unvalue = writer.unwrap('value')
            if isinstance(self.setter, ownedptr):
                writer.release_ownership(unvalue)
            writer.println('return _api.%(setter)s(%(unself)s, %(unvalue)s)' %
                           locals())
        writer.println()


#
# Pick-up environ var
#

TARGETS_BUILT = os.environ.get('LLVM_TARGETS_BUILT', '').split()


def _parse_llvm_version(ver):
    import re
    m = re.compile(r'(\d+)\.(\d+)').match(ver)
    assert m
    major, minor = m.groups()
    return int(major), int(minor)

LLVM_VERSION = _parse_llvm_version(os.environ['LLVMPY_LLVM_VERSION'])


########NEW FILE########
__FILENAME__ = codegen
import re, contextlib

NULL = 'NULL'

_symbols = set()

def wrap_println_from_file(file):
    def println(s=''):
        file.write(s)
        file.write('\n')
    return println

def indent(println):
    def _println(s=''):
        println("%s%s" % (' '* 4, s))
    return _println

def quote(txt):
    return '"%s"' % txt

def new_symbol(name):
    if name in _symbols:
        ct = 1
        orig = name
        while name in _symbols:
            name = '%s%d' % (orig, ct)
            ct += 1
    _symbols.add(name)
    return name

def parse_arguments(println, var, *args):
    typecodes = []
    holders = []
    argvals = []
    for arg in args:
        typecodes.append(arg.format)
        val = declare(println, 'PyObject*')
        argvals.append(val)
        holders.append('&' + val)

    items = [var, '"%s"' % (''.join(typecodes))] + holders
    println('if(!PyArg_ParseTuple(%s)) return NULL;' % ', '.join(items))

    # unwrap
    unwrapped = []
    for arg, val in zip(args, argvals):
        unwrapped.append(arg.unwrap(println, val))

    return unwrapped

_re_mangle_pattern = re.compile(r'[ _<>\*&,]')

def mangle(name):
    def repl(m):
        s = m.group(0)
        if s in '<>*&':
            return ''
        elif s in ' ,':
            return '_'
        elif s in '_':
            return '__'
        else:
            assert False
    name = _re_mangle_pattern.sub(repl, name)
    return name.replace('::', '_')

def pycapsule_new(println, ptr, name, clsname):
    # build capsule
    name_soften = mangle(name)
    var = new_symbol('pycap_%s' % name_soften)
    fmt = 'PyObject* %(var)s = pycapsule_new(%(ptr)s, "%(name)s", "%(clsname)s");'
    println(fmt % locals())
    println('if (!%(var)s) return NULL;' % locals())
    return var


def declare(println, typ, init=None):
    typ_soften = mangle(typ)
    var = new_symbol('var_%s' % typ_soften)
    if init is None:
        println('%(typ)s %(var)s;' % locals())
    else:
        println('%(typ)s %(var)s = %(init)s;' % locals())
    return var


def return_value(println, var):
    println('return %(var)s;' % locals())


def return_none(println):
    println('Py_RETURN_NONE;')


def die_if_null(println, var):
    println('if (!%(var)s) return NULL;' % locals())


class CodeWriterBase(object):
    def __init__(self, println):
        self.println = println
        self.used_symbols = set()

    @contextlib.contextmanager
    def indent(self):
        old = self.println
        self.println = indent(self.println)
        yield
        self.println = old

    @contextlib.contextmanager
    def py_function(self, name):
        self.println('static')
        self.println('PyObject*')
        with self.block('%(name)s(PyObject* self, PyObject* args)' % locals()):
            self.used_symbols.add('self')
            self.used_symbols.add('args')
            yield
        self.println()

    def new_symbol(self, name):
        if name in self.used_symbols:
            ct = 1
            orig = name
            while name in self.used_symbols:
                name = '%s%d' % (orig, ct)
                ct += 1
        self.used_symbols.add(name)
        return name

class CppCodeWriter(CodeWriterBase):
    @contextlib.contextmanager
    def block(self, lead):
        self.println(lead)
        self.println('{')
        with self.indent():
            yield
        self.println('}')

    def declare(self, typ, init=None):
        typ_soften = mangle(typ)
        var = self.new_symbol('var_%s' % typ_soften)
        if init is None:
            self.println('%(typ)s %(var)s;' % locals())
        else:
            self.println('%(typ)s %(var)s = %(init)s;' % locals())
        return var

    def return_value(self, val):
        if val is None:
            self.println('Py_RETURN_NONE;')
        else:
            self.println('return %s;' % val)

    def return_null(self):
        self.return_value(NULL)

    def parse_arguments(self, var, *args):
        typecodes = []
        holders = []
        argvals = []
        for arg in args:
            typecodes.append(arg.format)
            val = self.declare('PyObject*')
            argvals.append(val)
            holders.append('&' + val)

        items = [var, '"%s"' % (''.join(typecodes))] + holders
        with self.block('if(!PyArg_ParseTuple(%s))' % ', '.join(items)):
            self.return_null()

        # unwrap
        unwrapped = []
        for arg, val in zip(args, argvals):
            unwrapped.append(arg.unwrap(self, val))

        return unwrapped

    def call(self, func, retty, *args):
        arglist = ', '.join(args)
        stmt = '%(func)s(%(arglist)s)' % locals()
        if retty == 'void':
            self.println(stmt + ';')
        else:
            return self.declare(retty, stmt)

    def method_call(self, func, retty, *args):
        this = args[0]
        arglist = ', '.join(args[1:])
        if func == 'delete':
            assert not arglist
            stmt = 'delete %(this)s' % locals()
        elif func == 'new':
            alloctype = retty.rstrip(' *')
            stmt = 'new %(alloctype)s(%(arglist)s)' % locals()
        else:
            stmt = '%(this)s->%(func)s(%(arglist)s)' % locals()
        if retty == 'void':
            self.println('%s;' % stmt)
        else:
            return self.declare(retty, stmt)

    def pycapsule_new(self, ptr, name, clsname):
        name_soften = mangle(name)
        cast_to_base = 'cast_to_base<%s >::from(%s)' % (name, ptr)
        ret = self.call('pycapsule_new', 'PyObject*', cast_to_base, quote(name),
                        quote(clsname))
        with self.block('if (!%(ret)s)' % locals()):
            self.return_null()
        return ret

    def die_if_false(self, val, verbose=None):
        with self.block('if(!%(val)s)' % locals()):
            if verbose:
                self.println('puts("Error: %s");' % verbose)
            self.return_null()

    def raises(self, exccls, msg):
        exc = 'PyExc_%s' % exccls.__name__
        self.println('PyErr_SetString(%s, "%s");' % (exc, msg))
        self.return_null()


class PyCodeWriter(CodeWriterBase):
    @contextlib.contextmanager
    def block(self, lead):
        self.println(lead)
        with self.indent():
            yield

    @contextlib.contextmanager
    def function(self, func, args=(), varargs=None):
        with self.scope():
            arguments = []
            for arg in args:
                arguments.append(self.new_symbol(arg))
            if varargs:
                varargs = self.new_symbol(varargs)
                arguments.append('*%s' % varargs)
            arglist = ', '.join(arguments)
            with self.block('def %(func)s(%(arglist)s):' % locals()):
                if arguments:
                    arguments[-1] = arguments[-1].lstrip('*')
                    if len(arguments) > 1:
                        yield arguments
                    else:
                        yield arguments[0]
                else:
                    yield

    @contextlib.contextmanager
    def scope(self):
        self.old = self.used_symbols
        self.used_symbols = set()
        yield
        self.used_symbols = self.old

    def release_ownership(self, val):
        self.println('capsule.release_ownership(%(val)s)' % locals())

    def unwrap_many(self, args):
        unwrapped = self.new_symbol('unwrapped')
        self.println('%(unwrapped)s = list(map(capsule.unwrap, %(args)s))' % locals())
        return unwrapped

    def unwrap(self, val):
        return self.call('capsule.unwrap', args=(val,), ret='unwrapped')

    def wrap(self, val, owned):
        wrapped = self.new_symbol('wrapped')
        self.println('%(wrapped)s = capsule.wrap(%(val)s, %(owned)s)' % locals())
        return wrapped

    def call(self, func, args=(), varargs=None, ret='ret'):
        arguments = []
        for arg in args:
            arguments.append(arg)
        if varargs:
            arguments.append('*%s' % varargs)
        arglist = ', '.join(arguments)
        ret = self.new_symbol(ret)
        self.println('%(ret)s = %(func)s(%(arglist)s)' % locals())
        return ret

    def return_value(self, val=None):
        if val is None:
            val = ''
        self.println('return %s' % val)



########NEW FILE########
__FILENAME__ = gen
import sys, os
from binding import *
import codegen


extension_entry = '''

extern "C" {

#if (PY_MAJOR_VERSION >= 3)

PyMODINIT_FUNC
PyInit_%(module)s(void)
{
PyObject *module = create_python_module("%(module)s", meth_%(ns)s);
if (module) {
if (populate_submodules(module, submodule_%(ns)s))
return module;
}
return NULL;
}

#else

PyMODINIT_FUNC
init%(module)s(void)
{
PyObject *module = create_python_module("%(module)s", meth_%(ns)s);
if (module) {
populate_submodules(module, submodule_%(ns)s);
}
}
#endif

} // end extern C

'''


def populate_headers(println):
    includes = [
                'cstring',
                'Python.h',
                'python3adapt.h',
                'capsulethunk.h',
                'llvm_binding/conversion.h',
                'llvm_binding/binding.h',
                'llvm_binding/capsule_context.h',
                'llvm_binding/extra.h',             # extra submodule to add
                ]
    for inc in includes:
        println('#include "%s"' % inc)
    println()

def main():
    outputfilename = sys.argv[1]
    entry_modname = sys.argv[2]
    sys.path += [os.path.dirname(os.curdir)]
    entry_module = __import__(entry_modname)

    rootns = namespaces['']

    # Generate C++ source
    with open('%s.cpp' % outputfilename, 'w') as cppfile:
        println = codegen.wrap_println_from_file(cppfile)
        populate_headers(println)                  # extra headers
        # print all includes
        for inc in rootns.aggregate_includes():
            println('#include "%s"' % inc)
        println()
        # print all downcast
        downcast_fns = rootns.aggregate_downcast()
        for ((fromty, toty), fn) in downcast_fns:
            name = fn.name
            fmt = '''
static
%(toty)s* %(name)s(%(fromty)s* arg)
{
    return typecast< %(toty)s >::from(arg);
}
'''
            println(fmt % locals())

            fn.generate_cpp(println)

        println('static')
        println('PyMethodDef downcast_methodtable[] = {')
        fmt = '{ "%(name)s", (PyCFunction)%(func)s, METH_VARARGS, NULL },'
        for _, fn in downcast_fns:
            name = fn.name
            func = fn.c_name
            println(fmt % locals())
        println('{ NULL }')
        println('};')
        println()
        # generate submodule
        rootns.generate_cpp(println, extras=[('extra', 'extra_methodtable'),
                                             ('downcast', 'downcast_methodtable')])
        println(extension_entry % {'module' : '_api',
                                   'ns'     : ''})

    # Generate Python source
    rootns.generate_py(rootdir='.', name='api')


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = SmallVector
from binding import *
from ..namespace import llvm

@llvm.Class()
class SmallVector_Type:
    _realname_ = 'SmallVector<llvm::Type*,8>'
    delete = Destructor()

@llvm.Class()
class SmallVector_Value:
    _realname_ = 'SmallVector<llvm::Value*,8>'
    delete = Destructor()

@llvm.Class()
class SmallVector_Unsigned:
    _realname_ = 'SmallVector<unsigned,8>'
    delete = Destructor()

########NEW FILE########
__FILENAME__ = StringRef
from binding import *
from ..namespace import llvm

@llvm.Class()
class StringRef:
    _include_ = "llvm/ADT/StringRef.h"


########NEW FILE########
__FILENAME__ = Triple
from binding import *
from ..namespace import llvm
from .StringRef import StringRef

Triple = llvm.Class()

@Triple
class Triple:
    _include_ = 'llvm/ADT/Triple.h'

    new = Constructor()
    new |= Constructor(cast(str, StringRef))
    new |= Constructor(cast(str, StringRef),
                       cast(str, StringRef), cast(str, StringRef))

    def _return_str():
        return Method(cast(StringRef, str))

    getTriple = _return_str()
    getArchName = _return_str()
    getVendorName = _return_str()
    getOSName = _return_str()
    getEnvironmentName = _return_str()
    getOSAndEnvironmentName = _return_str()

    @CustomPythonMethod
    def __str__(self):
        return self.getTriple()

    def _return_bool(*args):
        return Method(cast(bool, Bool), *args)

    isArch64Bit = _return_bool()
    isArch32Bit = _return_bool()
    isArch16Bit = _return_bool()
    isOSVersionLT = _return_bool(cast(int, Unsigned),
                                 cast(int, Unsigned),
                                 cast(int, Unsigned)).require_only(1)

    isMacOSXVersionLT = _return_bool(cast(int, Unsigned),
                                    cast(int, Unsigned),
                                    cast(int, Unsigned)).require_only(1)

    isMacOSX = _return_bool()
    isOSDarwin = _return_bool()
    isOSCygMing = _return_bool()
    isOSWindows = _return_bool()
    # isOSNaCl = _return_bool()
    isOSBinFormatELF = _return_bool()
    isOSBinFormatCOFF = _return_bool()
    isEnvironmentMachO = _return_bool()

    get32BitArchVariant = Method(Triple)
    get64BitArchVariant = Method(Triple)


########NEW FILE########
__FILENAME__ = Verifier
from binding import *
from ..namespace import llvm
from ..Module import Module
from ..Value import Function

llvm.includes.add('llvm/Analysis/Verifier.h')

VerifierFailureAction = llvm.Enum('VerifierFailureAction',
                                  '''AbortProcessAction
                                     PrintMessageAction
                                     ReturnStatusAction''')

verifyModule = llvm.CustomFunction('verifyModule',
                                   'llvm_verifyModule',
                                   PyObjectPtr,  # boolean -- failed?
                                   ref(Module),
                                   VerifierFailureAction,
                                   PyObjectPtr,       # errmsg
                                   )

verifyFunction = llvm.Function('verifyFunction',
                               cast(Bool, bool),  # failed?
                               ref(Function),
                               VerifierFailureAction)


########NEW FILE########
__FILENAME__ = Argument
from binding import *
from .namespace import llvm
from .Value import Argument, Value
if LLVM_VERSION >= (3, 3):
    from .Attributes import AttributeSet, Attribute
else:
    from .Attributes import Attributes

@Argument
class Argument:
    if LLVM_VERSION >= (3, 3):
        _include_ = 'llvm/IR/Argument.h'
    else:
        _include_ = 'llvm/Argument.h'

    _downcast_ = Value

    if LLVM_VERSION >= (3, 3):
        addAttr = Method(Void, ref(AttributeSet))
        removeAttr = Method(Void, ref(AttributeSet))
    else:
        addAttr = Method(Void, ref(Attributes))
        removeAttr = Method(Void, ref(Attributes))

    getParamAlignment = Method(cast(Unsigned, int))

    getArgNo = Method(cast(Unsigned, int))

    hasByValAttr = Method(cast(Bool, bool))
    hasNestAttr = Method(cast(Bool, bool))
    hasNoAliasAttr = Method(cast(Bool, bool))
    hasNoCaptureAttr = Method(cast(Bool, bool))
    hasStructRetAttr = Method(cast(Bool, bool))

    if LLVM_VERSION > (3, 2):
        hasReturnedAttr = Method(cast(Bool, bool))

########NEW FILE########
__FILENAME__ = AssemblyAnnotationWriter
from binding import *
from ..namespace import llvm

@llvm.Class()
class AssemblyAnnotationWriter:
    _include_ = "llvm/Assembly/AssemblyAnnotationWriter.h"


########NEW FILE########
__FILENAME__ = Parser
from binding import *
from ..namespace import llvm
from ..Module import Module
from ..LLVMContext import LLVMContext
from ..Support.SourceMgr import SMDiagnostic

llvm.includes.add('llvm/Assembly/Parser.h')

ParseAssemblyString = llvm.Function('ParseAssemblyString',
                                    ptr(Module),
                                    cast(str, ConstCharPtr),
                                    ptr(Module), # can be None
                                    ref(SMDiagnostic),
                                    ref(LLVMContext))

########NEW FILE########
__FILENAME__ = Attributes
from binding import *
from .namespace import llvm
from .LLVMContext import LLVMContext

if LLVM_VERSION >= (3, 3):
    llvm.includes.add('llvm/IR/Attributes.h')
else:
    llvm.includes.add('llvm/Attributes.h')


AttrBuilder = llvm.Class()

if LLVM_VERSION >= (3, 3):
    Attribute = llvm.Class()
    AttributeSet = llvm.Class()
else:
    Attributes = llvm.Class()


if LLVM_VERSION >= (3, 3):
    @Attribute
    class Attribute:
        AttrKind = Enum('''None, Alignment, AlwaysInline,
                  ByVal, InlineHint, InReg,
                  MinSize, Naked, Nest, NoAlias,
                  NoBuiltin, NoCapture, NoDuplicate, NoImplicitFloat,
                  NoInline, NonLazyBind, NoRedZone, NoReturn,
                  NoUnwind, OptimizeForSize, ReadNone, ReadOnly,
                  Returned, ReturnsTwice, SExt, StackAlignment,
                  StackProtect, StackProtectReq, StackProtectStrong, StructRet,
                  SanitizeAddress, SanitizeThread, SanitizeMemory, UWTable,
                  ZExt, EndAttrKinds''')

        delete = Destructor()

        get = StaticMethod(Attribute,
                           ref(LLVMContext),
                           AttrKind,
                           cast(int, Uint64)).require_only(2)

    @AttrBuilder
    class AttrBuilder:

        new = Constructor()
        delete = Destructor()

        clear = Method()

        addAttribute = Method(ref(AttrBuilder), Attribute.AttrKind)
        removeAttribute = Method(ref(AttrBuilder), Attribute.AttrKind)

        addAlignmentAttr = Method(ref(AttrBuilder), cast(int, Unsigned))

    @AttributeSet
    class AttributeSet:
        delete = Destructor()

        get = StaticMethod(AttributeSet,
                           ref(LLVMContext),
                           cast(int, Unsigned),
                           ref(AttrBuilder))

else:
    @Attributes
    class Attributes:
        AttrVal = Enum('''None, AddressSafety, Alignment, AlwaysInline,
            ByVal, InlineHint, InReg, MinSize,
            Naked, Nest, NoAlias, NoCapture,
            NoImplicitFloat, NoInline, NonLazyBind, NoRedZone,
            NoReturn, NoUnwind, OptimizeForSize, ReadNone,
            ReadOnly, ReturnsTwice, SExt, StackAlignment,
            StackProtect, StackProtectReq, StructRet, UWTable, ZExt''')

        delete = Destructor()

        get = StaticMethod(Attributes, ref(LLVMContext), ref(AttrBuilder))


    @AttrBuilder
    class AttrBuilder:

        new = Constructor()
        delete = Destructor()

        clear = Method()

        addAttribute = Method(ref(AttrBuilder), Attributes.AttrVal)
        removeAttribute = Method(ref(AttrBuilder), Attributes.AttrVal)

        addAlignmentAttr = Method(ref(AttrBuilder), cast(int, Unsigned))



########NEW FILE########
__FILENAME__ = BasicBlock
from binding import *
from .namespace import llvm
from .Value import Function, BasicBlock, Value
from .Instruction import Instruction, TerminatorInst
from .LLVMContext import LLVMContext
from .ADT.StringRef import StringRef

@BasicBlock
class BasicBlock:
    _downcast_ = Value
    Create = StaticMethod(ptr(BasicBlock), ref(LLVMContext),
                          cast(str, StringRef),
                          ptr(Function),
                          ptr(BasicBlock))

    getParent = Method(ptr(Function))
    getTerminator = Method(ptr(TerminatorInst))

    empty = Method(cast(Bool, bool))
    dropAllReferences = Method()
    isLandingPad = Method(cast(Bool, bool))
    removePredecessor = Method(Void, ptr(BasicBlock), cast(bool, Bool))
    removePredecessor |= Method(Void, ptr(BasicBlock))

    getInstList = CustomMethod('BasicBlock_getInstList', PyObjectPtr)

    eraseFromParent = Method()

    splitBasicBlock = Method(ptr(BasicBlock), ptr(Instruction),
                             cast(str, StringRef)).require_only(1)


########NEW FILE########
__FILENAME__ = ReaderWriter
from binding import *
from ..namespace import llvm
from ..ADT.StringRef import StringRef
from ..Module import Module
from ..LLVMContext import LLVMContext

llvm.includes.add('llvm/Bitcode/ReaderWriter.h')

ParseBitCodeFile = llvm.CustomFunction('ParseBitCodeFile',
                                       'llvm_ParseBitCodeFile',
                                       PyObjectPtr,    # returns Module*
                                       cast(bytes, StringRef),
                                       ref(LLVMContext),
                                       PyObjectPtr,         # file-like object
                                       ).require_only(2)

WriteBitcodeToFile = llvm.CustomFunction('WriteBitcodeToFile',
                                         'llvm_WriteBitcodeToFile',
                                         PyObjectPtr,   # return None
                                         ptr(Module),
                                         PyObjectPtr,   # file-like object
                                         )

getBitcodeTargetTriple = llvm.CustomFunction('getBitcodeTargetTriple',
                                             'llvm_getBitcodeTargetTriple',
                                             PyObjectPtr, # return str
                                             cast(str, StringRef),
                                             ref(LLVMContext),
                                             PyObjectPtr, # file-like object
                                             ).require_only(2)

########NEW FILE########
__FILENAME__ = CallingConv
from binding import *
from .namespace import llvm

ccs = '''
    C, Fast, Cold, GHC, FirstTargetCC, X86_StdCall, X86_FastCall,
    ARM_APCS, ARM_AAPCS, ARM_AAPCS_VFP, MSP430_INTR, X86_ThisCall,
    PTX_Kernel, PTX_Device,
'''

if LLVM_VERSION <= (3, 3):
    ccs += "MBLAZE_INTR, MBLAZE_SVOL,"

ccs += 'SPIR_FUNC, SPIR_KERNEL, Intel_OCL_BI'

CallingConv = llvm.Namespace('CallingConv')
ID = CallingConv.Enum('ID', ccs) # HiPE

########NEW FILE########
__FILENAME__ = MachineCodeInfo
from binding import *
from ..namespace import llvm

MachineCodeInfo = llvm.Class()

@MachineCodeInfo
class MachineCodeInfo:
    _include_ = 'llvm/CodeGen/MachineCodeInfo.h'
    setSize = Method(Void, cast(int, Size_t))
    setAddress = Method(Void, cast(int, VoidPtr))
    size = Method(cast(Size_t, int))
    address = Method(cast(VoidPtr, int))


########NEW FILE########
__FILENAME__ = Constant
from binding import *
from .namespace import llvm
from .Value import Value, User
from .Value import Constant, UndefValue, ConstantInt, ConstantFP, ConstantArray
from .Value import ConstantStruct, ConstantVector, ConstantVector
from .Value import ConstantDataSequential, ConstantDataArray, ConstantExpr
from .LLVMContext import LLVMContext
from .ADT.StringRef import StringRef
from .ADT.SmallVector import SmallVector_Value, SmallVector_Unsigned
from .Type import Type, IntegerType, ArrayType, StructType
from .Instruction import CmpInst

@Constant
class Constant:
    _downcast_ = Value, User

    isNullValue = Method(cast(bool, Bool))
    isAllOnesValue = Method(cast(bool, Bool))
    isNegativeZeroValue = Method(cast(bool, Bool))
    #isZeroValue = Method(cast(bool, Bool))
    canTrap = Method(cast(bool, Bool))
    isThreadDependent = Method(cast(bool, Bool))
    isConstantUsed = Method(cast(bool, Bool))

    _getAggregateElement_by_int = Method(ptr(Constant), cast(int, Unsigned))
    _getAggregateElement_by_int.realname = 'getAggregateElement'
    _getAggregateElement_by_const = Method(ptr(Constant), ptr(Constant))
    _getAggregateElement_by_const.realname = 'getAggregateElement'

    @CustomPythonMethod
    def getAggregateElement(self, elt):
        if isinstance(elt, Constant):
            return self._getAggregateElement_by_const(elt)
        else:
            return self._getAggregateElement_by_int(elt)


    removeDeadConstantUsers = Method()

    getNullValue = StaticMethod(ptr(Constant), ptr(Type))
    getAllOnesValue = StaticMethod(ptr(Constant), ptr(Type))
    getIntegerValue = CustomStaticMethod('Constant_getIntegerValue',
                                         PyObjectPtr, # ptr(Constant),
                                         ptr(Type),
                                         PyObjectPtr)



@UndefValue
class UndefValue:
    getSequentialElement = Method(ptr(UndefValue))
    getStructElement = Method(ptr(UndefValue), cast(int, Unsigned))

    _getElementValue_by_const = Method(ptr(UndefValue), ptr(Constant))
    _getElementValue_by_const.realname = 'getElementValue'

    _getElementValue_by_int = Method(ptr(UndefValue), cast(int, Unsigned))
    _getElementValue_by_int.realname = 'getElementValue'

    @CustomPythonMethod
    def getElementValue(self, idx):
        if isinstance(idx, Constant):
            return self._getElementValue_by_const(idx)
        else:
            return self._getElementValue_by_int(idx)

    destroyConstant = Method()

    get = StaticMethod(ptr(UndefValue), ptr(Type))



@ConstantInt
class ConstantInt:
    _downcast_ = Constant, User, Value

    get = StaticMethod(ptr(ConstantInt),
                       ptr(IntegerType),
                       cast(int, Uint64),
                       cast(bool, Bool),
                       ).require_only(2)
    isValueValidForType = StaticMethod(cast(Bool, bool),
                                       ptr(Type),
                                       cast(int, Int64))
    getZExtValue = Method(cast(Uint64, int))
    getSExtValue = Method(cast(Int64, int))


@ConstantFP
class ConstantFP:
    _downcast_ = Constant, User, Value

    get = StaticMethod(ptr(Constant), ptr(Type), cast(float, Double))
    getNegativeZero = StaticMethod(ptr(ConstantFP), ptr(Type))
    getInfinity = StaticMethod(ptr(ConstantFP), ptr(Type), cast(bool, Bool))

    isZero = Method(cast(Bool, bool))
    isNegative = Method(cast(Bool, bool))
    isNaN = Method(cast(Bool, bool))



@ConstantArray
class ConstantArray:
    _downcast_ = Constant, User, Value

    get = CustomStaticMethod('ConstantArray_get',
                             PyObjectPtr, # ptr(Constant),
                             ptr(ArrayType),
                             PyObjectPtr,    # Constants
                             )


@ConstantStruct
class ConstantStruct:
    _downcast_ = Constant, User, Value

    get = CustomStaticMethod('ConstantStruct_get',
                             PyObjectPtr, # ptr(Constant)
                             ptr(StructType),
                             PyObjectPtr, # Constants
                             )
    getAnon = CustomStaticMethod('ConstantStruct_getAnon',
                                 PyObjectPtr, # ptr(Constant)
                                 PyObjectPtr, # constants
                                 cast(bool, Bool), # packed
                                 ).require_only(1)


@ConstantVector
class ConstantVector:
    _downcast_ = Constant, User, Value

    get = CustomStaticMethod('ConstantVector_get',
                             PyObjectPtr, # ptr(Constant)
                             PyObjectPtr, # constants
                             )


@ConstantDataSequential
class ConstantDataSequential:
    _downcast_ = Constant, User, Value


@ConstantDataArray
class ConstantDataArray:
    _downcast_ = Constant, User, Value

    getString = StaticMethod(ptr(Constant),
                             ref(LLVMContext),
                             cast(str, StringRef),
                             cast(bool, Bool)
                             ).require_only(2)



def _factory(*args):
    return StaticMethod(ptr(Constant), *args)

def _factory_const(*args):
    return _factory(ptr(Constant), *args)

def _factory_const2(*args):
    return _factory(ptr(Constant), ptr(Constant), *args)

def _factory_const_nuw_nsw():
    return _factory_const(cast(bool, Bool), cast(bool, Bool)).require_only(1)

def _factory_const2_nuw_nsw():
    return _factory_const2(cast(bool, Bool), cast(bool, Bool)).require_only(2)

def _factory_const2_exact():
    return _factory_const2(cast(bool, Bool)).require_only(2)

def _factory_const_type():
    return _factory_const(ptr(Type))

@ConstantExpr
class ConstantExpr:
    _downcast_ = Constant, User, Value

    getAlignOf = _factory(ptr(Type))
    getSizeOf = _factory(ptr(Type))
    getOffsetOf = _factory(ptr(Type), ptr(Constant))
    getNeg = _factory_const_nuw_nsw()
    getFNeg = _factory_const()
    getNot = _factory_const()
    getAdd = _factory_const2_nuw_nsw()
    getFAdd = _factory_const2()
    getSub = _factory_const2_nuw_nsw()
    getFSub = _factory_const2()
    getMul = _factory_const2_nuw_nsw()
    getFMul = _factory_const2()
    getUDiv = _factory_const2_exact()
    getSDiv = _factory_const2_exact()
    getFDiv = _factory_const2()
    getURem = _factory_const2()
    getSRem = _factory_const2()
    getFRem = _factory_const2()
    getAnd = _factory_const2()
    getOr = _factory_const2()
    getXor = _factory_const2()
    getShl = _factory_const2_nuw_nsw()
    getLShr = _factory_const2_exact()
    getAShr = _factory_const2_exact()
    getTrunc = _factory_const_type()
    getSExt = _factory_const_type()
    getZExt = _factory_const_type()
    getFPTrunc = _factory_const_type()
    getFPExtend = _factory_const_type()
    getUIToFP = _factory_const_type()
    getSIToFP = _factory_const_type()
    getFPToUI = _factory_const_type()
    getFPToSI = _factory_const_type()
    getPtrToInt = _factory_const_type()
    getIntToPtr = _factory_const_type()
    getBitCast = _factory_const_type()

    getCompare = _factory(CmpInst.Predicate, ptr(Constant), ptr(Constant))
    getICmp = _factory(CmpInst.Predicate, ptr(Constant), ptr(Constant))
    getFCmp = _factory(CmpInst.Predicate, ptr(Constant), ptr(Constant))

    getPointerCast = _factory_const_type()
    getIntegerCast = _factory_const(ptr(Type), cast(bool, Bool))
    getFPCast = _factory_const_type()
    getSelect = _factory(ptr(Constant), ptr(Constant), ptr(Constant))


    _getGEP = _factory(ptr(Constant), ref(SmallVector_Value), cast(bool, Bool))
    _getGEP.require_only(2)
    _getGEP.realname = 'getGetElementPtr'

    @CustomPythonStaticMethod
    def getGetElementPtr(*args):
        from llvmpy import extra
        args = list(args)
        valuelist = args[1]
        args[1] = extra.make_small_vector_from_values(*valuelist)
        return ConstantExpr._getGEP(*args)

    getExtractElement = _factory_const2()
    getInsertElement = _factory_const2(ptr(Constant))
    getShuffleVector = _factory_const2(ptr(Constant))

    _getExtractValue = _factory(ptr(Constant), ref(SmallVector_Unsigned))
    _getExtractValue.realname = 'getExtractValue'

    @CustomPythonStaticMethod
    def getExtractValue(*args):
        from llvmpy import extra
        args = list(args)
        valuelist = args[1]
        args[1] = extra.make_small_vector_from_unsigned(*valuelist)
        return ConstantExpr._getExtractValue(*args)

    _getInsertValue = _factory(ptr(Constant), ptr(Constant),
                               ref(SmallVector_Unsigned))
    _getInsertValue.realname = 'getInsertValue'

    @CustomPythonStaticMethod
    def getInsertValue(*args):
        from llvmpy import extra
        args = list(args)
        valuelist = args[2]
        args[1] = extra.make_small_vector_from_unsigned(*valuelist)
        return ConstantExpr._getInsertValue(*args)

    getOpcode = Method(cast(Unsigned, int))
    getOpcodeName = Method(cast(ConstCharPtr, str))
    isCast = Method(cast(Bool, bool))
    isCompare = Method(cast(Bool, bool))
    hasIndices = Method(cast(Bool, bool))
    isGEPWithNoNotionalOverIndexing = Method(cast(Bool, bool))


########NEW FILE########
__FILENAME__ = DataLayout
from binding import *
from .namespace import llvm
from .Pass import ImmutablePass

DataLayout = llvm.Class(ImmutablePass)
StructLayout = llvm.Class()

from .LLVMContext import LLVMContext
from .ADT.StringRef import StringRef
from .Module import Module
from .Type import Type, IntegerType, StructType
from .ADT.SmallVector import SmallVector_Value
from .GlobalVariable import GlobalVariable


@DataLayout
class DataLayout:
    if LLVM_VERSION >= (3, 3):
        _include_ = 'llvm/IR/DataLayout.h'
    else:
        _include_ = 'llvm/DataLayout.h'

    _new_string = Constructor(cast(str, StringRef))
    _new_module = Constructor(ptr(Module))

    @CustomPythonStaticMethod
    def new(arg):
        if isinstance(arg, Module):
            return DataLayout._new_module(arg)
        else:
            return DataLayout._new_string(arg)

    isLittleEndian = Method(cast(Bool, bool))
    isBigEndian = Method(cast(Bool, bool))

    getStringRepresentation = Method(cast(StdString, str))

    @CustomPythonMethod
    def __str__(self):
        return self.getStringRepresentation()

    isLegalInteger = Method(cast(Bool, bool), cast(int, Unsigned))
    isIllegalInteger = Method(cast(Bool, bool), cast(int, Unsigned))
    exceedsNaturalStackAlignment = Method(cast(Bool, bool), cast(int, Unsigned))
    fitsInLegalInteger = Method(cast(Bool, bool), cast(int, Unsigned))

    getPointerABIAlignment = Method(cast(Unsigned, int),
                                    cast(int, Unsigned)).require_only(0)
    getPointerPrefAlignment = Method(cast(Unsigned, int),
                                     cast(int, Unsigned)).require_only(0)
    getPointerSize = Method(cast(Unsigned, int),
                            cast(int, Unsigned)).require_only(0)
    getPointerSizeInBits = Method(cast(Unsigned, int),
                                  cast(int, Unsigned)).require_only(0)

    getTypeSizeInBits = Method(cast(Uint64, int), ptr(Type))
    getTypeStoreSize = Method(cast(Uint64, int), ptr(Type))
    getTypeStoreSizeInBits = Method(cast(Uint64, int), ptr(Type))
    getTypeAllocSize = Method(cast(Uint64, int), ptr(Type))
    getTypeAllocSizeInBits = Method(cast(Uint64, int), ptr(Type))

    getABITypeAlignment = Method(cast(Unsigned, int), ptr(Type))
    getABIIntegerTypeAlignment = Method(cast(Unsigned, int), cast(int, Unsigned))
    getCallFrameTypeAlignment = Method(cast(Unsigned, int), ptr(Type))
    getPrefTypeAlignment = Method(cast(Unsigned, int), ptr(Type))
    getPreferredTypeAlignmentShift = Method(cast(Unsigned, int), ptr(Type))

    _getIntPtrType = Method(ptr(IntegerType),
                            ref(LLVMContext), cast(int, Unsigned))
    _getIntPtrType.require_only(1)
    _getIntPtrType.realname = 'getIntPtrType'

    _getIntPtrType2 = Method(ptr(Type), ptr(Type))
    _getIntPtrType2.realname = 'getIntPtrType'

    @CustomPythonMethod
    def getIntPtrType(self, *args):
        if isinstance(args[0], LLVMContext):
            return self._getIntPtrType(*args)
        else:
            return self._getIntPtrType(*args)

    _getIndexedOffset = Method(cast(Uint64, int), ptr(Type),
                               ref(SmallVector_Value))
    _getIndexedOffset.realname = 'getIndexedOffset'

    @CustomPythonMethod
    def getIndexedOffset(self, *args):
        from llvmpy import extra
        args = list(args)
        args[1] = extra.make_small_vector_from_values(args[1])
        return self.getIndexedOffset(*args)

    getStructLayout = Method(const(ptr(StructLayout)), ptr(StructType))

    getPreferredAlignment = Method(cast(Unsigned, int), ptr(GlobalVariable))
    getPreferredAlignmentLog = Method(cast(Unsigned, int), ptr(GlobalVariable))

@StructLayout
class StructLayout:
    getSizeInBytes = Method(cast(Uint64, int))
    getSizeInBits = Method(cast(Uint64, int))
    getAlignment = Method(cast(Unsigned, int))
    getElementContainingOffset = Method(cast(Unsigned, int), cast(int, Uint64))
    getElementOffset = Method(cast(Uint64, int), cast(int, Unsigned))
    getElementOffsetInBits = Method(cast(Uint64, int), cast(int, Unsigned))

########NEW FILE########
__FILENAME__ = DebugInfo
from binding import *
from .namespace import llvm

from .ADT.StringRef import StringRef
from .Value import MDNode

DIDescriptor = llvm.Class()
DIEnumerator = llvm.Class(DIDescriptor)
DIScope = llvm.Class(DIDescriptor)
DIType = llvm.Class(DIScope)
DIBasicType = llvm.Class(DIType)
DIDerivedType = llvm.Class(DIType)
DICompositeType = llvm.Class(DIDerivedType)
DIFile = llvm.Class(DIScope)
DIArray = llvm.Class(DIDescriptor)
DISubrange = llvm.Class(DIDescriptor)
DIGlobalVariable = llvm.Class(DIDescriptor)
DIVariable = llvm.Class(DIDescriptor)
DISubprogram = llvm.Class(DIScope)
DINameSpace = llvm.Class(DIScope)
DILexicalBlockFile = llvm.Class(DIScope)
DILexicalBlock = llvm.Class(DIScope)

llvm.includes.add('llvm/DebugInfo.h')

return_bool = cast(Bool, bool)
return_stringref = cast(StringRef, str)
return_unsigned = cast(Unsigned, int)

@DIDescriptor
class DIDescriptor:
    new = Constructor(ptr(MDNode))
    delete = Destructor()

@DIScope
class DIScope:
    pass

@DIFile
class DIFile:
    # getFileNode = Method(ptr(MDNode)) # not in LLVM 3.2?
    Verify = Method(return_bool)

@DIEnumerator
class DIEnumerator:
    getName = Method(return_stringref)
    getEnumValue = Method(cast(Uint64 if LLVM_VERSION <= (3, 3) else Int64, int))
    Verify = Method(return_bool)

@DIType
class DIType:
    getName = Method(return_stringref)
    getLineNumber = Method(return_unsigned)
    Verify = Method(return_bool)

@DIBasicType
class DIBasicType:
    pass

@DIDerivedType
class DIDerivedType:
    pass

@DICompositeType
class DICompositeType:
    pass

@DIArray
class DIArray:
    Verify = Method(return_bool)

@DISubrange
class DISubrange:
    Verify = Method(return_bool)

@DIGlobalVariable
class DIGlobalVariable:
    Verify = Method(return_bool)

@DIVariable
class DIVariable:
    Verify = Method(return_bool)

@DISubprogram
class DISubprogram:
    Verify = Method(return_bool)

@DINameSpace
class DINameSpace:
    Verify = Method(return_bool)

@DILexicalBlockFile
class DILexicalBlockFile:
    Verify = Method(return_bool)

@DILexicalBlock
class DILexicalBlock:
    Verify = Method(return_bool)


########NEW FILE########
__FILENAME__ = DerivedTypes
from binding import *
from .namespace import llvm
from .LLVMContext import LLVMContext
from .Type import Type
from .ADT.SmallVector import SmallVector_Type

FunctionType = llvm.Class(Type)

@FunctionType
class FunctionType:
    if LLVM_VERSION >= (3, 3):
        _include_ = 'llvm/IR/DerivedTypes.h'
    else:
        _include_ = 'llvm/DerivedTypes.h'
    _downcast_ = Type

    _get = StaticMethod(ptr(FunctionType), ptr(Type), cast(bool, Bool))
    _get |= StaticMethod(ptr(FunctionType), ptr(Type), ref(SmallVector_Type),
                         cast(bool, Bool))
    _get.realname = 'get'

    @CustomPythonStaticMethod
    def get(*args):
        from llvmpy import extra
        if len(args) == 3:
            typelist = args[1]
            sv = extra.make_small_vector_from_types(*typelist)
            return FunctionType._get(args[0], sv, args[2])
        else:
            return FunctionType._get(*args)

    isVarArg = Method(cast(Bool, bool))
    getReturnType = Method(ptr(Type))
    getParamType = Method(ptr(Type), cast(int, Unsigned))
    getNumParams = Method(cast(Unsigned, int))


########NEW FILE########
__FILENAME__ = DIBuilder
from binding import *
from .namespace import llvm

DIBuilder = llvm.Class()

from .Module import Module
from .Value import Value, MDNode, Function, BasicBlock
from .Instruction import Instruction
from .DebugInfo import DIFile, DIEnumerator, DIType, DIBasicType, DIDerivedType, DICompositeType
from .DebugInfo import DIDescriptor, DIArray, DISubrange, DIGlobalVariable
from .DebugInfo import DIVariable, DISubprogram, DINameSpace, DILexicalBlockFile
from .DebugInfo import DILexicalBlock
from .ADT.SmallVector import SmallVector_Value
from .ADT.StringRef import StringRef

unsigned_arg = cast(int, Unsigned)
stringref_arg = cast(str, StringRef)
bool_arg = cast(bool, Bool)
uint64_arg = cast(int, Uint64)
int64_arg = cast(int, Int64)

@DIBuilder
class DIBuilder:
    _include_ = 'llvm/DIBuilder.h'
    new = Constructor(ref(Module))
    delete = Destructor()

    if LLVM_VERSION <= (3, 3):
        getCU = Method(const(ptr(MDNode)))
    finalize = Method()

    createCompileUnit = Method(Void,
                               unsigned_arg,  # Lang
                               stringref_arg, # File
                               stringref_arg, # Dir
                               stringref_arg, # Producer
                               bool_arg,      # isOptimized
                               stringref_arg, # Flags,
                               unsigned_arg,  # RV
                               # stringref_arg, # SplitName LLVM3.3
                               )  #.require_only(7)

    createFile = Method(DIFile,
                        stringref_arg,  # Filename
                        stringref_arg,  # Directory
                        )

    createEnumerator = Method(DIEnumerator,
                              stringref_arg,    # Name
                              uint64_arg if LLVM_VERSION <= (3, 3) else int64_arg, # Val
                              )

    if LLVM_VERSION <= (3, 3):
        createNullPtrType = Method(DIType,
                                   stringref_arg,   # Name
                                   )
    else:
        createNullPtrType = Method(DIBasicType)


    createBasicType = Method(DIType,
                             stringref_arg,     # Name
                             uint64_arg,        # SizeIntBits,
                             uint64_arg,        # AlignInBits,
                             unsigned_arg,      # Encoding
                             )

    createQualifiedType = Method(DIType,
                                 unsigned_arg,  # Tag
                                 ref(DIType),   # FromTy
                                 )

    createPointerType = Method(DIType,
                               ref(DIType),  # PointeeTy
                               uint64_arg,   # SizeInBits
                               uint64_arg,   # AlignInBits
                               stringref_arg, # Name
                               ).require_only(2)

    createReferenceType = Method(DIType,
                                 unsigned_arg,  # Tag
                                 ref(DIType),   # RTy
                                 )

    createTypedef = Method(DIType,
                           ref(DIType),        # Ty
                           stringref_arg,     # Name
                           ref(DIFile),       # File
                           unsigned_arg,      # LineNo
                           ref(DIDescriptor), # Context
                           )

    createFriend = Method(DIType if LLVM_VERSION <= (3, 3) else DIDerivedType,
                          ref(DIType),   # Ty
                          ref(DIType), # FriendTy
                          )

    createInheritance = Method(DIType,
                               ref(DIType),       # Ty
                               ref(DIType),       # BaseTy
                               uint64_arg,        # BaseOffset
                               unsigned_arg,      # Flags
                               )

    createMemberType = Method(DIType,
                              ref(DIDescriptor),   # Scope
                              stringref_arg,        # Name
                              ref(DIFile),          # File
                              unsigned_arg,         # LineNo
                              uint64_arg,           # SizeInBits
                              uint64_arg,           # AlignInBits
                              uint64_arg,           # OffsetInBits
                              unsigned_arg,         # Flags
                              ref(DIType),          # Ty
                              )

    createClassType = Method(DIType,
                             ref(DIDescriptor),     # Scope
                             stringref_arg,         # Name
                             ref(DIFile),           # File
                             unsigned_arg,          # LineNum
                             uint64_arg,            # SizeInBits
                             uint64_arg,            # AlignInBits
                             uint64_arg,            # OffsetInBits,
                             unsigned_arg,          # Flags
                             ref(DIType),           # DerivedFrom
                             ref(DIArray),          # Elements
                             ptr(MDNode),           # VTableHolder = 0
                             ptr(MDNode),           # TemplateParms = 0
                             ).require_only(10)

    if LLVM_VERSION >= (3, 3):
        createStructType = Method(DIType,
                                  ref(DIDescriptor),   # Scope
                                  stringref_arg,        # Name
                                  ref(DIFile),          # File
                                  unsigned_arg,         # LineNumber
                                  uint64_arg,           # SizeInBits
                                  uint64_arg,           # AlignInBits
                                  unsigned_arg,         # Flags
                                  ref(DIType),          # DerivedFrom
                                  ref(DIArray),         # Elements
                                  unsigned_arg,         # RunTimeLang = 0
                                  ).require_only(9)
    else:
        createStructType = Method(DIType,
                                  ref(DIDescriptor),   # Scope
                                  stringref_arg,        # Name
                                  ref(DIFile),          # File
                                  unsigned_arg,         # LineNumber
                                  uint64_arg,           # SizeInBits
                                  uint64_arg,           # AlignInBits
                                  unsigned_arg,         # Flags
                                  ref(DIArray),         # Elements
                                  unsigned_arg,         # RunTimeLang = 0
                                  ).require_only(8)

    createUnionType = Method(DIType,
                             ref(DIDescriptor),     # Scope
                             stringref_arg,         # Name
                             ref(DIFile),           # File
                             unsigned_arg,          # LineNum
                             uint64_arg,            # SizeInBits
                             uint64_arg,            # AlignInBits
                             unsigned_arg,          # Flags
                             ref(DIArray),          # Elements
                             unsigned_arg,          # RunTimeLang = 0
                             ).require_only(8)

    createArrayType = Method(DIType,
                             uint64_arg,  # Size
                             uint64_arg,  # AlignInBits
                             ref(DIType),  # Ty
                             ref(DIArray),  # Subscripts
                             )

    createVectorType = Method(DIType if LLVM_VERSION <= (3, 3) else DICompositeType,
                             uint64_arg,  # Size
                             uint64_arg,  # AlignInBits
                             ref(DIType),  # Ty
                             ref(DIArray),  # Subscripts
                             )

    createEnumerationType = Method(DIType,
                                   ref(DIDescriptor),   # Scope
                                   stringref_arg,       # Name
                                   ref(DIFile),         # File
                                   unsigned_arg,        # LineNumber
                                   uint64_arg,          # SizeInBits
                                   uint64_arg,          # AlignInBits
                                   ref(DIArray),        # Elements
                                   ref(DIType),         # ClassType
                                   )

    createSubroutineType = Method(DIType,
                                  ref(DIFile),      # File
                                  ref(DIArray),     # ParameterTypes
                                  )

    createArtificialType = Method(DIType,
                                ref(DIType),      # Ty
                                )

    createObjectPointerType = Method(DIType,
                                ref(DIType),      # Ty
                                )

    #createTemporaryType = Method(DIType, ref(DIFile)).require_only(0)

    createForwardDecl = Method(DIType,
                               unsigned_arg,         # Tag
                               stringref_arg,        # Name
                               ref(DIDescriptor),    # scope
                               ref(DIFile),          # F
                               unsigned_arg,         # Line
                               unsigned_arg,         # RuntimeLang=0
                               uint64_arg,           # SizeInBits=0
                               uint64_arg,           # AlignInBits=0
                               ).require_only(5)

    retainType = Method(Void, ref(DIType))

    createUnspecifiedParameter = Method(DIDescriptor)

    getOrCreateArray = Method(DIArray,
                              ref(SmallVector_Value),   # Elements
                              )

    getOrCreateSubrange = Method(DISubrange,
                                 int64_arg,     # Lo
                                 int64_arg,     # Hi
                                 )

    createGlobalVariable = Method(DIGlobalVariable,
                                  stringref_arg,    # Name
                                  ref(DIFile),      # File
                                  unsigned_arg,     # LineNo
                                  ref(DIType),      # Ty
                                  bool_arg,         # isLocalToUnit
                                  ptr(Value),       # Val
                                  )

    createStaticVariable = Method(DIGlobalVariable,
                                  ref(DIDescriptor), # Context
                                  stringref_arg,     # Name
                                  stringref_arg,     # LinkageName
                                  ref(DIFile),       # File
                                  unsigned_arg,      # LineNo
                                  ref(DIType),       # Ty
                                  bool_arg,          # isLocalToUnit
                                  ptr(Value),        # Val
                                  )

    createLocalVariable = Method(DIVariable,
                                 unsigned_arg,      # Tag,
                                 ref(DIDescriptor), # Scope,
                                 stringref_arg,     # Name,
                                 ref(DIFile),       # File,
                                 unsigned_arg,      # LineNo,
                                 ref(DIType),       # Ty,
                                 bool_arg,          # AlwaysPreserve=false,
                                 unsigned_arg,      # Flags=0,
                                 unsigned_arg,      # ArgNo=0
                                 ).require_only(6)

    createComplexVariable = Method(DIVariable,
                                   unsigned_arg,        # Tag,
                                   ref(DIDescriptor),   # Scope,
                                   stringref_arg,       # Name,
                                   ref(DIFile),         # F,
                                   unsigned_arg,        # LineNo,
                                   ref(DIType),         # Ty,
                                   ref(SmallVector_Value),   # Addr,
                                   unsigned_arg,        # ArgNo=0,
                                   ).require_only(7)

    createFunction = Method(DISubprogram,
                            ref(DIDescriptor),  # Scope
                            stringref_arg,      # Name
                            stringref_arg,      # LinkageName
                            ref(DIFile),        # File
                            unsigned_arg,       # LineNo
                            ref(DIType if LLVM_VERSION <= (3, 3) else DICompositeType), # Ty
                            bool_arg,           # isLocalToUnit
                            bool_arg,           # isDefinition
                            unsigned_arg,       # ScopeLine
                            unsigned_arg,       # Flags=0
                            bool_arg,           # isOptimized=false
                            ptr(Function),      # *Fn=0
                            ptr(MDNode),        # *TParam=0,
                            ptr(MDNode),        # *Decl=0
                            ).require_only(9)


    createMethod = Method(DISubprogram,
                          ref(DIDescriptor),        # Scope
                          stringref_arg,            # Name
                          stringref_arg,            # LinkageName
                          ref(DIFile),              # File
                          unsigned_arg,             # LineNo
                          ref(DIType if LLVM_VERSION <= (3, 3) else DICompositeType), # Ty
                          bool_arg,                 # isLocalToUnit
                          bool_arg,                 # isDefinition
                          unsigned_arg,             # Virtuality=0
                          unsigned_arg,             # VTableIndex=0
                          ptr(MDNode),              # *VTableHolder=0
                          unsigned_arg,             # Flags=0
                          bool_arg,                 # isOptimized=false
                          ptr(Function),            # *Fn=0
                          ptr(MDNode),              # *TParam=0
                          ).require_only(8)


    createNameSpace = Method(DINameSpace,
                             ref(DIDescriptor),     # Scope,
                             stringref_arg,         # Name,
                             ref(DIFile),           # File,
                             unsigned_arg,          # LineNo
                             )

    createLexicalBlockFile = Method(DILexicalBlockFile,
                                    ref(DIDescriptor),  # Scope,
                                    ref(DIFile),        # File
                                    )

    createLexicalBlock = Method(DILexicalBlock,
                                ref(DIDescriptor),  # Scope,
                                ref(DIFile),        # File,
                                unsigned_arg,       # Line,
                                unsigned_arg,       # Col
                                )

    _insertDeclare_1 = Method(ptr(Instruction),
                           ptr(Value),          # Storage,
                           ref(DIVariable),     # VarInfo
                           ptr(BasicBlock),     # *InsertAtEnd
                           )
    _insertDeclare_1.realname = 'insertDeclare'

    _insertDeclare_2 = Method(ptr(Instruction),
                           ptr(Value),          # Storage,
                           ref(DIVariable),     # VarInfo
                           ptr(Instruction),     # *InsertBefore
                           )
    _insertDeclare_2.realname = 'insertDeclare'

    @CustomPythonMethod
    def insertDeclare(self, storage, varinfo, insertpt):
        if isinstance(insertbefore, _api.llvm.Instruction):
            return self._insertDeclare_2(storage, varinfo, insertpt)
        else:
            return self._insertDeclare_1(storage, varinfo, insertpt)

    _insertDbgValueIntrinsic_1 = Method(ptr(Instruction),
                                        ptr(Value),        # *Val
                                        uint64_arg,        # Offset
                                        ref(DIVariable),   # VarInfo
                                        ptr(BasicBlock),   # *InsertAtEnd
                                        )
    _insertDbgValueIntrinsic_1.realname = 'insertDbgValueIntrinsic'

    _insertDbgValueIntrinsic_2 = Method(ptr(Instruction),
                                        ptr(Value),        # *Val
                                        uint64_arg,        # Offset
                                        ref(DIVariable),   # VarInfo
                                        ptr(Instruction),   # *InsertAtEnd
                                        )
    _insertDbgValueIntrinsic_2.realname = 'insertDbgValueIntrinsic'


    @CustomPythonMethod
    def insertDbgValueIntrinsic(self, storage, varinfo, insertpt):
        if isinstance(insertbefore, _api.llvm.Instruction):
            return self._insertDbgValueIntrinsic_2(storage, varinfo, insertpt)
        else:
            return self._insertDbgValueIntrinsic_1(storage, varinfo, insertpt)

########NEW FILE########
__FILENAME__ = EngineBuilder
from binding import *
from .namespace import llvm
from .Module import Module
from .JITMemoryManager import JITMemoryManager
from .Support.CodeGen import CodeGenOpt, Reloc, CodeModel
from .ADT.StringRef import StringRef
from .ExecutionEngine.ExecutionEngine import ExecutionEngine
from .Target.TargetMachine import TargetMachine
from .ADT.Triple import Triple

EngineBuilder = llvm.Class()

EngineKind = llvm.Namespace('EngineKind')
Kind = EngineKind.Enum('Kind', 'JIT', 'Interpreter')

@EngineBuilder
class EngineBuilder:
    new = Constructor(ownedptr(Module))
    delete = Destructor()

    def _setter(*args):
        return Method(ref(EngineBuilder), *args)

    setEngineKind = _setter(Kind)
    setJITMemoryManager = _setter(ptr(JITMemoryManager))
# FIXME
#    setErrorStr = CustomMethod('EngineBuilder_setErrorStr',
#                                PyObjectPtr, PyObjectPtr)

    setOptLevel = _setter(CodeGenOpt.Level)
    #setTargetOptions =
    setRelocationModel = _setter(Reloc.Model)
    setCodeModel = _setter(CodeModel.Model)
    setAllocateGVsWithCode = _setter(cast(bool, Bool))
    setMArch = _setter(cast(str, StringRef))
    setMCPU = _setter(cast(str, StringRef))
    setUseMCJIT = _setter(cast(bool, Bool))
    _setMAttrs = CustomMethod('EngineBuilder_setMAttrs',
                              PyObjectPtr, PyObjectPtr)
    @CustomPythonMethod
    def setMAttrs(self, attrs):
        attrlist = list(str(a) for a in attrs)
        return self._setMAttrs(attrlist)

    create = Method(ptr(ExecutionEngine),
                    ownedptr(TargetMachine)).require_only(0)

    _selectTarget0 = Method(ptr(TargetMachine))
    _selectTarget0.realname = 'selectTarget'

    _selectTarget1 = CustomMethod('EngineBuilder_selectTarget',
                                 PyObjectPtr,
                                 const(ref(Triple)), cast(str, StringRef),
                                 cast(str, StringRef), PyObjectPtr)

    @CustomPythonMethod
    def selectTarget(self, *args):
        if not args:
            return self._selectTarget0()
        else:
            return self._selectTarget1(*args)


########NEW FILE########
__FILENAME__ = ExecutionEngine
from binding import *
from ..namespace import llvm
from ..Module import Module
from ..JITMemoryManager import JITMemoryManager
from ..Support.CodeGen import CodeGenOpt, Reloc, CodeModel
from ..DataLayout import DataLayout
from ..Value import Function, GlobalValue, BasicBlock, Constant
from ..GlobalVariable import GlobalVariable
from ..CodeGen.MachineCodeInfo import MachineCodeInfo
from ..GenericValue import GenericValue
from ..Type import Type

ExecutionEngine = llvm.Class()

@ExecutionEngine
class ExecutionEngine:
    _include_ = ('llvm/ExecutionEngine/ExecutionEngine.h',
                 'llvm/ExecutionEngine/JIT.h') # force linking of jit

    delete = Destructor()

    create = CustomStaticMethod('ExecutionEngine_create',
                                ptr(ExecutionEngine),
                                ownedptr(Module), cast(bool, Bool),
                                PyObjectPtr, CodeGenOpt.Level,
                                cast(bool, Bool)).require_only(1)

    createJIT = CustomStaticMethod('ExecutionEngine_createJIT',
                                   ptr(ExecutionEngine),
                                   ownedptr(Module), PyObjectPtr,
                                   ptr(JITMemoryManager),
                                   CodeGenOpt.Level,
                                   cast(bool, Bool),
                                   Reloc.Model,
                                   CodeModel.Model).require_only(1)

    addModule = Method(Void, ownedptr(Module))
    getDataLayout = Method(const(ownedptr(DataLayout)))
    _removeModule = Method(cast(Bool, bool), ptr(Module))
    _removeModule.realname = 'removeModule'
    @CustomPythonMethod
    def removeModule(self, module):
        if self._removeModule(module):
            capsule.obtain_ownership(module._capsule)
            return True
        return False

    FindFunctionNamed = Method(ptr(Function), cast(str, ConstCharPtr))
    getPointerToNamedFunction = Method(cast(VoidPtr, int),
                                       cast(str, StdString),
                                       cast(bool, Bool)).require_only(1)

    runStaticConstructorsDestructors = Method(Void,
                                              cast(Bool, bool), # is dtor
                                              )
    runStaticConstructorsDestructors |= Method(Void, ptr(Module),
                                              cast(Bool, bool))

    addGlobalMapping = Method(Void, ptr(GlobalValue), cast(int, VoidPtr))
    clearAllGlobalMappings = Method()
    clearGlobalMappingsFromModule = Method(Void, ptr(Module))
    updateGlobalMapping = Method(cast(VoidPtr, int),
                                 ptr(GlobalValue), cast(int, VoidPtr))

    getPointerToGlobalIfAvailable = Method(cast(VoidPtr, int), ptr(GlobalValue))
    getPointerToGlobal = Method(cast(VoidPtr, int), ptr(GlobalValue))
    getPointerToFunction = Method(cast(VoidPtr, int), ptr(Function))
    getPointerToBasicBlock = Method(cast(VoidPtr, int), ptr(BasicBlock))
    getPointerToFunctionOrStub = Method(cast(VoidPtr, int), ptr(Function))

    runJITOnFunction = Method(Void, ptr(Function), ptr(MachineCodeInfo))
    runJITOnFunction.require_only(1)

    getGlobalValueAtAddress = Method(const(ptr(GlobalValue)), cast(int, VoidPtr))

    StoreValueToMemory = Method(Void, ref(GenericValue), ptr(GenericValue),
                                ptr(Type))

    InitializeMemory = Method(Void, ptr(Constant), cast(int, VoidPtr))

    recompileAndRelinkFunction = Method(cast(int, VoidPtr), ptr(Function))

    freeMachineCodeForFunction = Method(Void, ptr(Function))
    getOrEmitGlobalVariable = Method(cast(int, VoidPtr), ptr(GlobalVariable))

    DisableLazyCompilation = Method(Void, cast(bool, Bool))
    isCompilingLazily = Method(cast(Bool, bool))
    isLazyCompilationDisabled = Method(cast(Bool, bool))
    DisableGVCompilation = Method(Void, cast(bool, Bool))
    isSymbolSearchingDisabled = Method(cast(Bool, bool))
    RegisterTable = Method(Void, ptr(Function), cast(int, VoidPtr))
    DeregisterTable = Method(Void, ptr(Function))
    DeregisterAllTables = Method()

    _runFunction = CustomMethod('ExecutionEngine_RunFunction',
                                PyObjectPtr, ptr(Function), PyObjectPtr)

    @CustomPythonMethod
    def runFunction(self, fn, args):
        from llvmpy import capsule
        unwrapped = list(map(capsule.unwrap, args))
        return self._runFunction(fn, tuple(unwrapped))

    finalizeObject = Method(Void)


########NEW FILE########
__FILENAME__ = Function
from binding import *
from .namespace import llvm
from .Value import GlobalValue, Constant, Function, Argument, Value
from .Module import Module
from .BasicBlock import BasicBlock
from .ValueSymbolTable import ValueSymbolTable
if LLVM_VERSION >= (3, 3):
    from .Attributes import Attribute, AttributeSet
else:
    from .Attributes import Attributes
from .Type import Type
from .DerivedTypes import FunctionType
from .LLVMContext import LLVMContext
from .CallingConv import CallingConv

@Function
class Function:
    if LLVM_VERSION >= (3, 3):
        _include_ = 'llvm/IR/Function.h'
    else:
        _include_ = 'llvm/Function.h'

    _downcast_  = GlobalValue, Constant, Value

    getReturnType = Method(ptr(Type))
    getFunctionType = Method(ptr(FunctionType))
    getContext = Method(ref(LLVMContext))
    isVarArg = Method(cast(Bool, bool))
    getIntrinsicID = Method(cast(Unsigned, int))
    isIntrinsic = Method(cast(Bool, bool))

    getCallingConv = Method(CallingConv.ID)
    setCallingConv = Method(Void, CallingConv.ID)

    hasGC = Method(cast(Bool, bool))
    getGC = Method(cast(ConstCharPtr, str))
    setGC = Method(Void, cast(str, ConstCharPtr))


    getArgumentList = CustomMethod('Function_getArgumentList', PyObjectPtr)
    getBasicBlockList = CustomMethod('Function_getBasicBlockList', PyObjectPtr)
    getEntryBlock = Method(ref(BasicBlock))
    getValueSymbolTable = Method(ref(ValueSymbolTable))

    copyAttributesFrom = Method(Void, ptr(GlobalValue))

    setDoesNotThrow = Method()
    doesNotThrow = Method(cast(Bool, bool))
    setDoesNotReturn = Method()
    doesNotReturn = Method(cast(Bool, bool))
    setOnlyReadsMemory = Method()
    onlyReadsMemory = Method(cast(Bool, bool))
    setDoesNotAccessMemory = Method()
    doesNotAccessMemory = Method(cast(Bool, bool))

    deleteBody = Method()
    viewCFG = Method()

    viewCFGOnly = Method()

    if LLVM_VERSION >= (3, 3):
        addFnAttr = Method(Void, Attribute.AttrKind)
        addAttributes = Method(Void, cast(int, Unsigned), ref(AttributeSet))
        removeAttributes = Method(Void, cast(int, Unsigned), ref(AttributeSet))
        #removeFnAttr = Method(Void, Attribute.AttrKind) # 3.4?
    else:
        addFnAttr = Method(Void, Attributes.AttrVal)
        removeFnAttr = Method(Void, ref(Attributes))
    #hasFnAttribute = Method(cast(Bool, bool), Attributes.AttrVal)

    Create = StaticMethod(ptr(Function),
                          ptr(FunctionType),
                          GlobalValue.LinkageTypes,
                          cast(str, ConstCharPtr),
                          ptr(Module)).require_only(2)

    eraseFromParent = Method()
    eraseFromParent.disowning = True


########NEW FILE########
__FILENAME__ = GenericValue
from binding import *
from .namespace import llvm
from .Type import Type

GenericValue = llvm.Class()

@GenericValue
class GenericValue:
    delete = Destructor()

    def _factory(name, *argtys):
         return CustomStaticMethod('GenericValue_' + name,
                                   ptr(GenericValue), *argtys)

    CreateFloat = _factory('CreateFloat', cast(float, Float))

    CreateDouble = _factory('CreateDouble', cast(float, Float))

    CreateInt = _factory('CreateInt', ptr(Type),
                         cast(int, UnsignedLongLong), cast(bool, Bool))

    CreatePointer = _factory('CreatePointer', cast(int, VoidPtr))

    def _accessor(name, *argtys):
        return CustomMethod('GenericValue_' + name, *argtys)

    valueIntWidth = _accessor('ValueIntWidth', cast(Unsigned, int))

    toSignedInt = _accessor('ToSignedInt', cast(LongLong, int))
    toUnsignedInt = _accessor('ToUnsignedInt', cast(UnsignedLongLong, int))

    toFloat = _accessor('ToFloat', cast(Double, float), ptr(Type))

    toPointer = _accessor('ToPointer', cast(VoidPtr, int))

########NEW FILE########
__FILENAME__ = GlobalValue
from binding import *
from .namespace import llvm
from .Value import GlobalValue
from .Module import Module
from .ADT.StringRef import StringRef

@GlobalValue
class GlobalValue:
    if LLVM_VERSION >= (3, 3):
        _include_ = 'llvm/IR/GlobalValue.h'
    else:
        _include_ = 'llvm/GlobalValue.h'

    LinkageTypes = Enum('''
        ExternalLinkage, AvailableExternallyLinkage, LinkOnceAnyLinkage,
        LinkOnceODRLinkage, LinkOnceODRAutoHideLinkage, WeakAnyLinkage,
        WeakODRLinkage, AppendingLinkage, InternalLinkage, PrivateLinkage,
        LinkerPrivateLinkage, LinkerPrivateWeakLinkage, DLLImportLinkage,
        DLLExportLinkage, ExternalWeakLinkage, CommonLinkage
        ''')

    VisibilityTypes = Enum('''DefaultVisibility,
                              HiddenVisibility,
                              ProtectedVisibility''')

    setLinkage = Method(Void, LinkageTypes)
    getLinkage = Method(LinkageTypes)

    setVisibility = Method(Void, VisibilityTypes)
    getVisibility = Method(VisibilityTypes)

    setLinkage = Method(Void, LinkageTypes)
    getLinkage = Method(LinkageTypes)

    getAlignment = Method(cast(Unsigned, int))
    setAlignment = Method(Void, cast(int, Unsigned))

    hasSection = Method(cast(Bool, bool))
    getSection = Method(cast(ConstStdString, str))
    setSection = Method(Void, cast(str, StringRef))

    isDiscardableIfUnused = Method(cast(Bool, bool))
    mayBeOverridden = Method(cast(Bool, bool))
    isWeakForLinker = Method(cast(Bool, bool))
    copyAttributesFrom = Method(Void, ptr(GlobalValue))
    destroyConstant = Method()
    isDeclaration = Method(cast(Bool, bool))
    removeFromParent = Method()
    eraseFromParent = Method()
    eraseFromParent.disowning = True

    getParent = Method(ownedptr(Module))

########NEW FILE########
__FILENAME__ = GlobalVariable
from binding import *
from .namespace import llvm

from .GlobalValue import GlobalValue
GlobalVariable = llvm.Class(GlobalValue)

from .Module import Module
from .Type import Type
from .ADT.StringRef import StringRef
from .Value import Value, User, Constant

@GlobalVariable
class GlobalVariable:
    _downcast_ = Value, User, Constant
    ThreadLocalMode = Enum('''NotThreadLocal, GeneralDynamicTLSModel,
                              LocalDynamicTLSModel, InitialExecTLSModel,
                              LocalExecTLSModel
                           ''')

    new = Constructor(ref(Module),
                      ptr(Type),
                      cast(bool, Bool), # is constant
                      GlobalValue.LinkageTypes,
                      ptr(Constant), # initializer -- can be None
                      cast(str, StringRef), # name
                      ptr(GlobalVariable), # insert before
                      ThreadLocalMode,
                      cast(int, Unsigned), # address-space
                 #     cast(bool, Bool), # externally initialized
                      ).require_only(5)

    setThreadLocal = Method(Void, cast(bool, Bool))
    setThreadLocalMode = Method(Void, ThreadLocalMode)
    isThreadLocal = Method(cast(Bool, bool))

    isConstant = Method(cast(Bool, bool))
    setConstant = Method(Void, cast(bool, Bool))

    setInitializer = Method(Void, ptr(Constant))
    getInitializer = Method(ptr(Constant))
    hasInitializer = Method(cast(Bool, bool))

    hasUniqueInitializer = Method(cast(Bool, bool))
    hasDefinitiveInitializer = Method(cast(Bool, bool))

#    isExternallyInitialized = Method(cast(Bool, bool))
#    setExternallyinitialized = Method(Void, cast(bool, Bool))



########NEW FILE########
__FILENAME__ = InlineAsm
from binding import *
from .namespace import llvm
from .Value import Value
from .DerivedTypes import FunctionType
from .ADT.StringRef import StringRef

if LLVM_VERSION >= (3, 3):
    llvm.includes.add('llvm/IR/InlineAsm.h')
else:
    llvm.includes.add('llvm/InlineAsm.h')

InlineAsm = llvm.Class(Value)

@InlineAsm
class InlineAsm:
    AsmDialect = Enum('AD_ATT', 'AD_Intel')
    ConstraintPrefix = Enum('''isInput, isOutput, isClobber''')

    get = StaticMethod(ptr(InlineAsm),
                       ptr(FunctionType),
                       cast(str, StringRef),    # AsmString
                       cast(str, StringRef),    # Constrains
                       cast(bool, Bool),        # hasSideEffects
                       cast(bool, Bool),        # isAlignStack
                       AsmDialect,              # default = AD_ATT
                       ).require_only(4)


########NEW FILE########
__FILENAME__ = Instruction
from binding import *
from .namespace import llvm
from .Value import Value, MDNode, User, BasicBlock, Function, ConstantInt


Instruction = llvm.Class(User)
AtomicCmpXchgInst = llvm.Class(Instruction)
AtomicRMWInst = llvm.Class(Instruction)
BinaryOperator = llvm.Class(Instruction)
CallInst = llvm.Class(Instruction)
CmpInst = llvm.Class(Instruction)
ExtractElementInst = llvm.Class(Instruction)
FenceInst = llvm.Class(Instruction)
GetElementPtrInst = llvm.Class(Instruction)
InsertElementInst = llvm.Class(Instruction)
InsertValueInst = llvm.Class(Instruction)
LandingPadInst = llvm.Class(Instruction)
PHINode = llvm.Class(Instruction)
SelectInst = llvm.Class(Instruction)
ShuffleVectorInst = llvm.Class(Instruction)
StoreInst = llvm.Class(Instruction)
TerminatorInst = llvm.Class(Instruction)
UnaryInstruction = llvm.Class(Instruction)

IntrinsicInst = llvm.Class(CallInst)

FCmpInst = llvm.Class(CmpInst)
ICmpInst = llvm.Class(CmpInst)

BranchInst = llvm.Class(TerminatorInst)
IndirectBrInst = llvm.Class(TerminatorInst)
InvokeInst = llvm.Class(TerminatorInst)
ResumeInst = llvm.Class(TerminatorInst)
ReturnInst = llvm.Class(TerminatorInst)
SwitchInst = llvm.Class(TerminatorInst)
UnreachableInst = llvm.Class(TerminatorInst)

AllocaInst = llvm.Class(UnaryInstruction)
CastInst = llvm.Class(UnaryInstruction)
ExtractValueInst = llvm.Class(UnaryInstruction)
LoadInst = llvm.Class(UnaryInstruction)
VAArgInst = llvm.Class(UnaryInstruction)

DbgInfoIntrinsic = llvm.Class(IntrinsicInst)
MemIntrinsic = llvm.Class(IntrinsicInst)
VACopyInst = llvm.Class(IntrinsicInst)
VAEndInst = llvm.Class(IntrinsicInst)
VAStartInst = llvm.Class(IntrinsicInst)

BitCastInst = llvm.Class(CastInst)
FPExtInst = llvm.Class(CastInst)
FPToSIInst = llvm.Class(CastInst)
FPToUIInst = llvm.Class(CastInst)
FPTruncInst = llvm.Class(CastInst)

AtomicOrdering = llvm.Enum('AtomicOrdering',
                           'NotAtomic', 'Unordered', 'Monotonic', 'Acquire',
                           'Release', 'AcquireRelease',
                           'SequentiallyConsistent')

SynchronizationScope = llvm.Enum('SynchronizationScope',
                                 'SingleThread', 'CrossThread')



from .ADT.StringRef import StringRef
from .CallingConv import CallingConv
if LLVM_VERSION >= (3, 3):
    from .Attributes import AttributeSet, Attribute
else:
    from .Attributes import Attributes
from .Type import Type



@Instruction
class Instruction:
    _downcast_ = Value, User

    removeFromParent = Method()
    eraseFromParent = Method()
    eraseFromParent.disowning = True

    getParent = Method(ptr(BasicBlock))
    getOpcode = Method(cast(Unsigned, int))
    getOpcodeName = Method(cast(ConstCharPtr, str))

    insertBefore = Method(Void, ptr(Instruction))
    insertAfter = Method(Void, ptr(Instruction))
    moveBefore = Method(Void, ptr(Instruction))

    isTerminator = Method(cast(Bool, bool))
    isBinaryOp = Method(cast(Bool, bool))
    isShift = Method(cast(Bool, bool))
    isCast = Method(cast(Bool, bool))
    isLogicalShift = Method(cast(Bool, bool))
    isArithmeticShift = Method(cast(Bool, bool))
    hasMetadata = Method(cast(Bool, bool))
    hasMetadataOtherThanDebugLoc = Method(cast(Bool, bool))
    isAssociative = Method(cast(Bool, bool))
    isCommutative = Method(cast(Bool, bool))
    isIdempotent = Method(cast(Bool, bool))
    isNilpotent = Method(cast(Bool, bool))
    mayWriteToMemory = Method(cast(Bool, bool))
    mayReadFromMemory = Method(cast(Bool, bool))
    mayReadOrWriteMemory = Method(cast(Bool, bool))
    mayThrow = Method(cast(Bool, bool))
    mayHaveSideEffects = Method(cast(Bool, bool))

    hasMetadata = Method(cast(Bool, bool))
    getMetadata = Method(ptr(MDNode), cast(str, StringRef))
    setMetadata = Method(Void, cast(str, StringRef), ptr(MDNode))

    clone = Method(ptr(Instruction))

    getNextNode = Method(ptr(Instruction))
    getPrevNode = Method(ptr(Instruction))

# LLVM 3.3
#    hasUnsafeAlgebra = Method(cast(Bool, bool))
#    hasNoNans = Method(cast(Bool, bool))
#    hasNoInfs = Method(cast(Bool, bool))
#    hasNoSignedZeros = Method(cast(Bool, bool))
#    hasAllowReciprocal = Method(cast(Bool, bool))


@AtomicCmpXchgInst
class AtomicCmpXchgInst:
    _downcast_ = Value, User, Instruction

@AtomicRMWInst
class AtomicRMWInst:
    _downcast_ = Value, User, Instruction
    BinOp = Enum('Xchg', 'Add', 'Sub', 'And', 'Nand', 'Or', 'Xor', 'Max', 'Min',
                 'UMax', 'UMin', 'FIRST_BINOP', 'LAST_BINOP', 'BAD_BINOP')

@BinaryOperator
class BinaryOperator:
    _downcast_ = Value, User, Instruction

@CallInst
class CallInst:
    _downcast_ = Value, User, Instruction

    getCallingConv = Method(CallingConv.ID)
    setCallingConv = Method(Void, CallingConv.ID)
    getParamAlignment = Method(cast(Unsigned, int), cast(int, Unsigned))
    if LLVM_VERSION >= (3, 3):
        addAttribute = Method(Void, cast(int, Unsigned), Attribute.AttrKind)
        removeAttribute = Method(Void, cast(int, Unsigned), ref(Attribute))
    else:
        addAttribute = Method(Void, cast(int, Unsigned), ref(Attributes))
        removeAttribute = Method(Void, cast(int, Unsigned), ref(Attributes))
    getCalledFunction = Method(ptr(Function))
    getCalledValue = Method(ptr(Value))
    setCalledFunction = Method(Void, ptr(Function))
    isInlineAsm = Method(cast(Bool, bool))

    CreateMalloc = StaticMethod(ptr(Instruction),
                                ptr(BasicBlock),    # insertAtEnd
                                ptr(Type),          # intptrty
                                ptr(Type),          # allocty
                                ptr(Value),         # allocsz
                                ptr(Value),         # array size = 0
                                ptr(Function),      # malloc fn = 0
                                cast(str, StringRef), # name
                                ).require_only(4)

    CreateFree = StaticMethod(ptr(Instruction), ptr(Value), ptr(BasicBlock))

    getNumArgOperands = Method(cast(Unsigned, int))
    getArgOperand = Method(ptr(Value), cast(int, Unsigned))
    setArgOperand = Method(Void, cast(int, Unsigned), ptr(Value))

@CmpInst
class CmpInst:
    _downcast_ = Value, User, Instruction
    Predicate = Enum('FCMP_FALSE', 'FCMP_OEQ', 'FCMP_OGT', 'FCMP_OGE',
                     'FCMP_OLT', 'FCMP_OLE', 'FCMP_ONE', 'FCMP_ORD', 'FCMP_UNO',
                     'FCMP_UEQ', 'FCMP_UGT', 'FCMP_UGE', 'FCMP_ULT', 'FCMP_ULE',
                     'FCMP_UNE', 'FCMP_TRUE', 'FIRST_FCMP_PREDICATE',
                     'LAST_FCMP_PREDICATE',
                     'BAD_FCMP_PREDICATE',
                     'ICMP_EQ', 'ICMP_NE', 'ICMP_UGT', 'ICMP_UGE', 'ICMP_ULT',
                     'ICMP_ULE', 'ICMP_SGT', 'ICMP_SGE', 'ICMP_SLT', 'ICMP_SLE',
                     'FIRST_ICMP_PREDICATE',
                     'LAST_ICMP_PREDICATE',
                     'BAD_ICMP_PREDICATE',)

    getPredicate = Method(Predicate)

@ExtractElementInst
class ExtractElementInst:
    _downcast_ = Value, User, Instruction

@FenceInst
class FenceInst:
    _downcast_ = Value, User, Instruction

@GetElementPtrInst
class GetElementPtrInst:
    _downcast_ = Value, User, Instruction

@InsertElementInst
class InsertElementInst:
    _downcast_ = Value, User, Instruction

@InsertValueInst
class InsertValueInst:
    _downcast_ = Value, User, Instruction

@LandingPadInst
class LandingPadInst:
    _downcast_ = Value, User, Instruction

@PHINode
class PHINode:
    _downcast_ = Value, User, Instruction
    getNumIncomingValues = Method(cast(Unsigned, int))
    getIncomingValue = Method(ptr(Value), cast(int, Unsigned))
    setIncomingValue = Method(Void, cast(int, Unsigned), ptr(Value))
    getIncomingBlock = Method(ptr(BasicBlock), cast(int, Unsigned))
    setIncomingBlock = Method(Void, cast(int, Unsigned), ptr(BasicBlock))
    addIncoming = Method(Void, ptr(Value), ptr(BasicBlock))
    hasConstantValue = Method(ptr(Value))
    getBasicBlockIndex = Method(cast(Int, int), ptr(BasicBlock))

@SelectInst
class SelectInst:
    _downcast_ = Value, User, Instruction

@ShuffleVectorInst
class ShuffleVectorInst:
    _downcast_ = Value, User, Instruction

@StoreInst
class StoreInst:
    _downcast_ = Value, User, Instruction
    isVolatile = Method(cast(Bool, bool))
    isSimple = Method(cast(Bool, bool))
    isUnordered = Method(cast(Bool, bool))
    isAtomic = Method(cast(Bool, bool))

    setVolatile = Method(Void, cast(Bool, bool))

    getAlignment = Method(cast(Unsigned, int))
    setAlignment = Method(Void, cast(int, Unsigned))

    setAtomic = Method(Void,
                       AtomicOrdering,
                       SynchronizationScope).require_only(1)

    getValueOperand = Method(ptr(Value))
    getPointerOperand = Method(ptr(Value))
    getPointerAddressSpace = Method(cast(Unsigned, int))

    classof = StaticMethod(cast(Bool, bool), ptr(Value))

@TerminatorInst
class TerminatorInst:
    _downcast_ = Value, User, Instruction
    getNumSuccessors = Method(cast(Unsigned, int))
    getSuccessor = Method(ptr(BasicBlock), cast(int, Unsigned))
    setSuccessor = Method(Void, cast(int, Unsigned), ptr(BasicBlock))

@UnaryInstruction
class UnaryInstruction:
    _downcast_ = Value, User, Instruction

#call

@IntrinsicInst
class IntrinsicInst:
    if LLVM_VERSION >= (3, 3):
        _include_ = 'llvm/IR/IntrinsicInst.h'
    else:
        _include_ = 'llvm/IntrinsicInst.h'
    _downcast_ = Value, User, Instruction

#compare

@FCmpInst
class FCmpInst:
    _downcast_ = Value, User, Instruction

@ICmpInst
class ICmpInst:
    _downcast_ = Value, User, Instruction

# terminator
@BranchInst
class BranchInst:
    _downcast_ = Value, User, Instruction

@IndirectBrInst
class IndirectBrInst:
    _downcast_ = Value, User, Instruction

@InvokeInst
class InvokeInst:
    _downcast_ = Value, User, Instruction
    getCallingConv = Method(CallingConv.ID)
    setCallingConv = Method(Void, CallingConv.ID)
    getParamAlignment = Method(cast(Unsigned, int), cast(int, Unsigned))
    if LLVM_VERSION >= (3, 3):
        addAttribute = Method(Void, cast(int, Unsigned), Attribute.AttrKind)
        removeAttribute = Method(Void, cast(int, Unsigned), ref(Attribute))
    else:
        addAttribute = Method(Void, cast(int, Unsigned), ref(Attributes))
        removeAttribute = Method(Void, cast(int, Unsigned), ref(Attributes))
    getCalledFunction = Method(ptr(Function))
    getCalledValue = Method(ptr(Value))
    setCalledFunction = Method(Void, ptr(Function))

@ResumeInst
class ResumeInst:
    _downcast_ = Value, User, Instruction

@ReturnInst
class ReturnInst:
    _downcast_ = Value, User, Instruction, TerminatorInst
    getReturnValue = Method(ptr(Value))
    getNumSuccessors = Method(cast(Unsigned, int))

@SwitchInst
class SwitchInst:
    _downcast_ = Value, User, Instruction

    getCondition = Method(ptr(Value))
    setCondition = Method(Void, ptr(Value))
    getDefaultDest = Method(ptr(BasicBlock))
    setDefaultDest = Method(Void, ptr(BasicBlock))
    getNumCases = Method(cast(int, Unsigned))
    addCase = Method(Void, ptr(ConstantInt), ptr(BasicBlock))


@UnreachableInst
class UnreachableInst:
    _downcast_ = Value, User, Instruction

# unary
@AllocaInst
class AllocaInst:
    _downcast_ = Value, User, Instruction
    isArrayAllocation = Method(cast(Bool, bool))
    isStaticAlloca = Method(cast(Bool, bool))
    getArraySize = Method(ptr(Value))
    getAllocatedType = Method(ptr(Type))
    getAlignment = Method(cast(Unsigned, int))
    setAlignment = Method(Void, cast(int, Unsigned))
    getArraySize = Method(ptr(Value))


@CastInst
class CastInst:
    _downcast_ = Value, User, Instruction

@ExtractValueInst
class ExtractValueInst:
    _downcast_ = Value, User, Instruction

@LoadInst
class LoadInst:
    _downcast_ = Value, User, Instruction
    isVolatile = Method(cast(Bool, bool))
    isSimple = Method(cast(Bool, bool))
    isUnordered = Method(cast(Bool, bool))
    isAtomic = Method(cast(Bool, bool))

    setVolatile = Method(Void, cast(Bool, bool))

    getAlignment = Method(cast(Unsigned, int))
    setAlignment = Method(Void, cast(int, Unsigned))

    setAtomic = Method(Void,
                       AtomicOrdering,
                       SynchronizationScope).require_only(1)

    getPointerOperand = Method(ptr(Value))

    classof = StaticMethod(cast(Bool, bool), ptr(Value))

@VAArgInst
class VAArgInst:
    _downcast_ = Value, User, Instruction

# intrinsic
@DbgInfoIntrinsic
class DbgInfoIntrinsic:
    _downcast_ = Value, User, Instruction

@MemIntrinsic
class MemIntrinsic:
    _downcast_ = Value, User, Instruction

@VACopyInst
class VACopyInst:
    _downcast_ = Value, User, Instruction

@VAEndInst
class VAEndInst:
    _downcast_ = Value, User, Instruction

@VAStartInst
class VAStartInst:
    _downcast_ = Value, User, Instruction

@BitCastInst
class BitCastInst:
    _downcast_ = Value, User, Instruction

@FPExtInst
class FPExtInst:
    _downcast_ = Value, User, Instruction

@FPToSIInst
class FPToSIInst:
    _downcast_ = Value, User, Instruction

@FPToUIInst
class FPToUIInst:
    _downcast_ = Value, User, Instruction

@FPTruncInst
class FPTruncInst:
    _downcast_ = Value, User, Instruction


########NEW FILE########
__FILENAME__ = Intrinsics
from binding import *
from .namespace import llvm

from .Module import Module
from .Function import Function


Intrinsic = llvm.Namespace('Intrinsic')

getDeclaration = Intrinsic.CustomFunction('getDeclaration',
                                          'Intrinsic_getDeclaration',
                                          PyObjectPtr,          # Function*
                                          ptr(Module),
                                          cast(int, Unsigned),  # intrinsic id
                                          PyObjectPtr,          # list of Type
                                          ).require_only(2)

########NEW FILE########
__FILENAME__ = IRBuilder
from binding import *
from .namespace import llvm
from .LLVMContext import LLVMContext
from .BasicBlock import BasicBlock
from .Instruction import Instruction
from .Instruction import ReturnInst, CallInst, BranchInst, SwitchInst
from .Instruction import IndirectBrInst, InvokeInst, ResumeInst, PHINode
from .Instruction import UnreachableInst, AllocaInst, LoadInst, StoreInst
from .Instruction import FenceInst, AtomicCmpXchgInst, AtomicRMWInst, CmpInst
from .Instruction import LandingPadInst, VAArgInst
from .Instruction import AtomicOrdering, SynchronizationScope
from .ADT.SmallVector import SmallVector_Value, SmallVector_Unsigned
from .ADT.StringRef import StringRef
from .Value import Value, MDNode
from .Type import Type, IntegerType

IRBuilder = llvm.Class()

@IRBuilder
class IRBuilder:
    if LLVM_VERSION >= (3, 3):
        _include_ = 'llvm/IR/IRBuilder.h'
    else:
        _include_ = 'llvm/IRBuilder.h'

    _realname_ = 'IRBuilder<>'

    new = Constructor(ref(LLVMContext))
    delete = Destructor()

    GetInsertBlock = Method(ptr(BasicBlock))

    _SetInsertPoint_end_of_bb = Method(Void, ptr(BasicBlock))
    _SetInsertPoint_end_of_bb.realname = 'SetInsertPoint'
    _SetInsertPoint_before_instr = Method(Void, ptr(Instruction))
    _SetInsertPoint_before_instr.realname = 'SetInsertPoint'

    @CustomPythonMethod
    def SetInsertPoint(self, pt):
        if isinstance(pt, Instruction):
            return self._SetInsertPoint_before_instr(pt)
        elif isinstance(pt, BasicBlock):
            return self._SetInsertPoint_end_of_bb(pt)
        else:
            raise ValueError("Expected either an Instruction or a BasicBlock")

    isNamePreserving = Method(cast(Bool, bool))

    CreateRetVoid = Method(ptr(ReturnInst))
    CreateRet = Method(ptr(ReturnInst), ptr(Value))
    CreateAggregateRet = CustomMethod('IRBuilder_CreateAggregateRet',
                                      PyObjectPtr,      # ptr(ReturnInst),
                                      PyObjectPtr,      # list of Value
                                      cast(int, Unsigned))

    CreateBr = Method(ptr(BranchInst), ptr(BasicBlock))


    CreateCondBr = Method(ptr(BranchInst), ptr(Value), ptr(BasicBlock),
                          ptr(BasicBlock), ptr(MDNode)).require_only(3)

    CreateSwitch = Method(ptr(SwitchInst), ptr(Value), ptr(BasicBlock),
                          cast(int, Unsigned), ptr(MDNode)).require_only(2)

    CreateIndirectBr = Method(ptr(IndirectBrInst), ptr(Value),
                              cast(int, Unsigned)).require_only(1)

    _CreateInvoke = Method(ptr(InvokeInst), ptr(Value), ptr(BasicBlock),
                          ptr(BasicBlock), ref(SmallVector_Value),
                          cast(str, StringRef)).require_only(4)
    _CreateInvoke.realname = 'CreateInvoke'

    @CustomPythonMethod
    def CreateInvoke(self, *args):
        from llvmpy import extra
        args = list(args)
        valuelist = args[3]
        args[3] = extra.make_small_vector_from_values(*valuelist)
        return self._CreateInvoke(*args)

    CreateResume = Method(ptr(ResumeInst), ptr(Value))

    CreateUnreachable = Method(ptr(UnreachableInst))

    def _binop_has_nsw_nuw():
        sig = [ptr(Value), ptr(Value), ptr(Value), cast(str, StringRef),
               cast(bool, Bool), cast(bool, Bool)]
        op = Method(*sig).require_only(2)
        return op

    CreateAdd = _binop_has_nsw_nuw()
    CreateSub = _binop_has_nsw_nuw()
    CreateMul = _binop_has_nsw_nuw()
    CreateShl = _binop_has_nsw_nuw()

    def _binop_is_exact():
        sig = [ptr(Value), ptr(Value), ptr(Value), cast(str, StringRef),
               cast(bool, Bool)]
        op = Method(*sig).require_only(2)
        return op

    CreateUDiv = _binop_is_exact()
    CreateSDiv = _binop_is_exact()
    CreateLShr = _binop_is_exact()
    CreateAShr = _binop_is_exact()

    def _binop_basic():
        sig = [ptr(Value), ptr(Value), ptr(Value), cast(str, StringRef)]
        op = Method(*sig).require_only(2)
        return op

    CreateURem = _binop_basic()
    CreateSRem = _binop_basic()
    CreateAnd = _binop_basic()
    CreateOr = _binop_basic()
    CreateXor = _binop_basic()

    def _float_binop():
        sig = [ptr(Value), ptr(Value), ptr(Value), cast(str, StringRef),
               ptr(MDNode)]
        op = Method(*sig).require_only(2)
        return op

    CreateFAdd = _float_binop()
    CreateFSub = _float_binop()
    CreateFMul = _float_binop()
    CreateFDiv = _float_binop()
    CreateFRem = _float_binop()

    def _unop_has_nsw_nuw():
        sig = [ptr(Value), ptr(Value), cast(str, StringRef),
               cast(bool, Bool), cast(bool, Bool)]
        op = Method(*sig).require_only(1)
        return op

    CreateNeg = _unop_has_nsw_nuw()

    def _float_unop():
        sig = [ptr(Value), ptr(Value), cast(str, StringRef), ptr(MDNode)]
        op = Method(*sig).require_only(1)
        return op

    CreateFNeg = _float_unop()

    CreateNot = Method(ptr(Value),
                       ptr(Value), cast(str, StringRef)).require_only(1)


    CreateAlloca = Method(ptr(AllocaInst),
                          ptr(Type),            # ty
                          ptr(Value),           # arysize = 0
                          cast(str, StringRef), # name = ''
                          ).require_only(1)

    CreateLoad = Method(ptr(LoadInst),
                        ptr(Value), cast(str, StringRef)).require_only(1)

    CreateStore = Method(ptr(StoreInst), ptr(Value), ptr(Value),
                         cast(bool, Bool)).require_only(2)

    CreateAlignedLoad = Method(ptr(LoadInst), ptr(Value), cast(int, Unsigned),
                               cast(bool, Bool), cast(str, StringRef))
    CreateAlignedLoad.require_only(2)

    CreateAlignedStore = Method(ptr(StoreInst), ptr(Value), ptr(Value),
                                cast(int, Unsigned), cast(bool, Bool))
    CreateAlignedStore.require_only(3)

    CreateFence = Method(ptr(FenceInst),
                         AtomicOrdering, SynchronizationScope).require_only(1)

    CreateAtomicCmpXchg = Method(ptr(AtomicCmpXchgInst), ptr(Value), ptr(Value),
                                 ptr(Value), AtomicOrdering, SynchronizationScope)
    CreateAtomicCmpXchg.require_only(4)

    CreateAtomicRMW = Method(ptr(AtomicRMWInst), AtomicRMWInst.BinOp,
                             ptr(Value), ptr(Value), AtomicOrdering,
                             SynchronizationScope)
    CreateAtomicRMW.require_only(4)

    _CreateGEP = Method(ptr(Value), ptr(Value), ref(SmallVector_Value),
                       cast(str, StringRef))
    _CreateGEP.require_only(2)
    _CreateGEP.realname = 'CreateGEP'

    @CustomPythonMethod
    def CreateGEP(self, *args):
        from llvmpy import extra
        args = list(args)
        valuelist = args[1]
        args[1] = extra.make_small_vector_from_values(*valuelist)
        return self._CreateGEP(*args)

    _CreateInBoundsGEP = Method(ptr(Value), ptr(Value), ref(SmallVector_Value),
                        cast(str, StringRef))
    _CreateInBoundsGEP.require_only(2)
    _CreateInBoundsGEP.realname = 'CreateInBoundsGEP'

    @CustomPythonMethod
    def CreateInBoundsGEP(self, *args):
        from llvmpy import extra
        args = list(args)
        valuelist = args[1]
        args[1] = extra.make_small_vector_from_values(*valuelist)
        return self._CreateInBoundsGEP(*args)

    CreateStructGEP = Method(ptr(Value), ptr(Value), cast(int, Unsigned),
                             cast(str, StringRef)).require_only(2)

    CreateGlobalStringPtr = Method(ptr(Value), cast(str, StringRef),
                                   cast(str, StringRef)).require_only(1)

    def _value_type():
        sig = [ptr(Value), ptr(Value), ptr(Type), cast(str, StringRef)]
        op = Method(*sig).require_only(2)
        return op

    CreateTrunc = _value_type()
    CreateZExt = _value_type()
    CreateSExt = _value_type()
    CreateZExtOrTrunc = Method(ptr(Value), ptr(Value), ptr(IntegerType),
                               cast(str, StringRef)).require_only(2)
    CreateSExtOrTrunc = Method(ptr(Value), ptr(Value), ptr(IntegerType),
                               cast(str, StringRef)).require_only(2)
    CreateFPToUI = _value_type()
    CreateFPToSI = _value_type()
    CreateUIToFP = _value_type()
    CreateSIToFP = _value_type()
    CreateFPTrunc = _value_type()
    CreateFPExt = _value_type()
    CreatePtrToInt = _value_type()
    CreateIntToPtr = _value_type()
    CreateBitCast = _value_type()
    CreateZExtOrBitCast = _value_type()
    CreateSExtOrBitCast = _value_type()
    # Skip CreateCast
    CreateTruncOrBitCast = _value_type()
    CreateIntCast = Method(ptr(Value), ptr(Value), ptr(Type), cast(bool, Bool),
                           cast(str, StringRef)).require_only(3)
    CreateFPCast = _value_type()

    _CreateCall = Method(ptr(CallInst), ptr(Value), ref(SmallVector_Value),
                         cast(str, StringRef)).require_only(2)
    _CreateCall.realname = 'CreateCall'

    @CustomPythonMethod
    def CreateCall(self, *args):
        from llvmpy import extra
        args = list(args)
        valuelist = args[1]
        args[1] = extra.make_small_vector_from_values(*valuelist)
        return self._CreateCall(*args)

    # Skip specialized CreateICmp* and CreateFCmp*

    CreateICmp = Method(ptr(Value), CmpInst.Predicate, ptr(Value), ptr(Value),
                        cast(str, StringRef)).require_only(3)

    CreateFCmp = Method(ptr(Value), CmpInst.Predicate, ptr(Value), ptr(Value),
                        cast(str, StringRef)).require_only(3)

    CreatePHI = Method(ptr(PHINode), ptr(Type), cast(int, Unsigned),
                       cast(str, StringRef)).require_only(2)


    CreateSelect = Method(ptr(Value), ptr(Value), ptr(Value), ptr(Value),
                          cast(str, StringRef)).require_only(3)

    CreateVAArg = Method(ptr(VAArgInst), ptr(Value), ptr(Type),
                         cast(str, StringRef)).require_only(2)

    CreateExtractElement = _binop_basic()

    CreateInsertElement = Method(ptr(Value), ptr(Value), ptr(Value), ptr(Value),
                                 cast(str, StringRef)).require_only(3)

    CreateShuffleVector = Method(ptr(Value), ptr(Value), ptr(Value),
                                 ptr(Value), cast(str, StringRef))
    CreateShuffleVector.require_only(3)

    _CreateExtractValue = Method(ptr(Value), ptr(Value),
                                 ref(SmallVector_Unsigned),
                                 cast(str, StringRef))
    _CreateExtractValue.require_only(2)
    _CreateExtractValue.realname = 'CreateExtractValue'

    @CustomPythonMethod
    def CreateExtractValue(self, *args):
        from llvmpy import extra
        args = list(args)
        valuelist = args[1]
        args[1] = extra.make_small_vector_from_unsigned(*valuelist)
        return self._CreateExtractValue(*args)

    _CreateInsertValue = Method(ptr(Value),
                                ptr(Value), # Agg
                                ptr(Value), # Val
                                ref(SmallVector_Unsigned), # ArrayRef<unsigned>
                                cast(str, StringRef), # name
                                ).require_only(3)
    _CreateInsertValue.realname = 'CreateInsertValue'

    @CustomPythonMethod
    def CreateInsertValue(self, *args):
        from llvmpy import extra
        args = list(args)
        valuelist = args[2]
        args[2] = extra.make_small_vector_from_unsigned(*valuelist)
        return self._CreateInsertValue(*args)

    CreateLandingPad = Method(ptr(LandingPadInst), ptr(Type), ptr(Value),
                              cast(int, Unsigned), cast(str, StringRef))
    CreateLandingPad.require_only(3)

    CreateIsNull = Method(ptr(Value), ptr(Value), cast(str, StringRef))
    CreateIsNull.require_only(1)

    CreateIsNotNull = Method(ptr(Value), ptr(Value), cast(str, StringRef))
    CreateIsNotNull.require_only(1)

    CreatePtrDiff = _binop_basic()

    # New in llvm 3.3
    #CreateVectorSplat = Method(ptr(Value), cast(int, Unsigned), ptr(Value),
    #                           cast(str, StringRef))


    Insert = Method(ptr(Instruction),
                    ptr(Instruction),
                    cast(str, StringRef)).require_only(1)

########NEW FILE########
__FILENAME__ = JITMemoryManager
from binding import *
from .namespace import llvm

@llvm.Class()
class JITMemoryManager:
    pass


########NEW FILE########
__FILENAME__ = Linker
from binding import *
from .namespace import llvm
from .ADT.StringRef import StringRef
from .Module import Module
from .LLVMContext import LLVMContext

llvm.includes.add('llvm/Linker.h')

Linker = llvm.Class()

@Linker
class Linker:
    #ControlFlags = Enum('Verbose, QuietWarnings, QuietErrors')
    LinkerMode = Enum('DestroySource, PreserveSource')

    if LLVM_VERSION >= (3, 3):
        new = Constructor(ptr(Module))
    else:
        _new_w_empty = Constructor(cast(str, StringRef),
                                   cast(str, StringRef),
                                   ref(LLVMContext),
                                   cast(int, Unsigned)).require_only(3)

        _new_w_existing = Constructor(cast(str, StringRef),
                                      ptr(Module),
                                      cast(int, Unsigned)).require_only(2)

        @CustomPythonStaticMethod
        def new(progname, module_or_name, *args):
            if isinstance(module_or_name, Module):
                return _new_w_existing(progname, module_or_name, *args)
            else:
                return _new_w_empty(progname, module_or_name, *args)

    delete = Destructor()

    getModule = Method(ptr(Module))
    #releaseModule = Method(ptr(Module))
    #getLastError = Method(cast(ConstStdString, str))

    LinkInModule = CustomMethod('Linker_LinkInModule',
                                PyObjectPtr, # boolean
                                ptr(Module),
                                PyObjectPtr, # errmsg
                                )

    _LinkModules = CustomStaticMethod('Linker_LinkModules',
                                     PyObjectPtr, # boolean
                                     ptr(Module),
                                     ptr(Module),
                                     LinkerMode,
                                     PyObjectPtr, # errsg
                                     )

    @CustomPythonStaticMethod
    def LinkModules(module, other, mode, errmsg):
        failed = Linker._LinkModules(module, other, mode, errmsg)
        if not failed and mode != Linker.LinkerMode.PreserveSource:
            capsule.release_ownership(other._ptr)
        return failed


########NEW FILE########
__FILENAME__ = LLVMContext
from binding import *
from .namespace import llvm

@llvm.Class()
class LLVMContext:
    if LLVM_VERSION >= (3, 3):
        _include_ = "llvm/IR/LLVMContext.h"
    else:
        _include_ = "llvm/LLVMContext.h"

llvm.Function('getGlobalContext', ref(LLVMContext))

########NEW FILE########
__FILENAME__ = Metadata
from binding import *
from .namespace import llvm
from .Value import Value, MDNode, MDString
from .LLVMContext import LLVMContext
from .ADT.StringRef import StringRef
from .Module import Module
from .Function import Function
from .Support.raw_ostream import raw_ostream
from .Assembly.AssemblyAnnotationWriter import AssemblyAnnotationWriter

@MDNode
class MDNode:
    _downcast_ = Value
    replaceOperandWith = Method(Void, cast(int, Unsigned), ptr(Value))
    getOperand = Method(ptr(Value), cast(int, Unsigned))
    getNumOperands = Method(cast(Unsigned, int))
    isFunctionLocal = Method(cast(Bool, bool))
    getFunction = Method(const(ptr(Function)))

    get = CustomStaticMethod('MDNode_get',
                             PyObjectPtr,           # MDNode*
                             ref(LLVMContext),
                             PyObjectPtr,           # ArrayRef<Value*>
                             )

@MDString
class MDString:
    _downcast_ = Value
    get = StaticMethod(ptr(MDString), ref(LLVMContext), cast(str, StringRef))
    getString = Method(cast(StringRef, str))
    getLength = Method(cast(int, Unsigned))

@llvm.Class()
class NamedMDNode:
    eraseFromParent = Method()
    eraseFromParent.disowning = True

    dropAllReferences = Method()
    getParent = Method(ptr(Module))
    getOperand = Method(ptr(MDNode), cast(int, Unsigned))
    getNumOperands = Method(cast(Unsigned, int))
    getName = Method(cast(StringRef, str))
    addOperand = Method(Void, ptr(MDNode))
    print_ = Method(Void, ref(raw_ostream), ptr(AssemblyAnnotationWriter))
    print_.realname = "print"
    dump = Method()


    @CustomPythonMethod
    def __str__(self):
        from llvmpy import extra
        os = extra.make_raw_ostream_for_printing()
        self.print_(os, None)
        return os.str()

########NEW FILE########
__FILENAME__ = Module
from binding import *
from .namespace import llvm

Module = llvm.Class()

from .LLVMContext import LLVMContext
from .ADT.StringRef import StringRef
from .Constant import Constant
from .GlobalVariable import GlobalVariable
from .Function import Function
from .DerivedTypes import FunctionType
from .Support.raw_ostream import raw_ostream
from .Assembly.AssemblyAnnotationWriter import AssemblyAnnotationWriter
from .Type import Type, StructType
from .Metadata import NamedMDNode

@Module
class Module:
    if LLVM_VERSION >= (3, 3):
        _include_ = "llvm/IR/Module.h"
    else:
        _include_ = "llvm/Module.h"
    # Enumerators
    Endianness = Enum('AnyEndianness', 'LittleEndian', 'BigEndian')
    PointerSize = Enum('AnyPointerSize', 'Pointer32', 'Pointer64')

    # Constructors & Destructors
    new = Constructor(cast(str, StringRef), ref(LLVMContext))
    delete = Destructor()

    # Module Level Accessor
    getModuleIdentifier = Method(cast(ConstStdString, str))
    getDataLayout = Method(cast(ConstStdString, str))
    getTargetTriple = Method(cast(ConstStdString, str))
    getEndianness = Method(Endianness)
    getPointerSize = Method(PointerSize)
    getContext = Method(ref(LLVMContext))
    getModuleInlineAsm = Method(cast(ConstStdString, str))

    # Module Level Mutators
    setModuleIdentifier = Method(Void, cast(str, StringRef))
    setDataLayout = Method(Void, cast(str, StringRef))
    setTargetTriple = Method(Void, cast(str, StringRef))
    setModuleInlineAsm = Method(Void, cast(str, StringRef))
    appendModuleInlineAsm = Method(Void, cast(str, StringRef))

    # Function Accessors
    getOrInsertFunction = Method(ptr(Constant), cast(str, StringRef),
                                 ptr(FunctionType))
    getFunction = Method(ptr(Function), cast(str, StringRef))

    # Function Iteration
    list_functions = CustomMethod('Module_list_functions', PyObjectPtr)

    # GlobalVariabe Accessors
    getGlobalVariable = Method(ptr(GlobalVariable),
                               cast(str, StringRef),
                               cast(bool, Bool),
                               ).require_only(1)
    getNamedGlobal = Method(ptr(GlobalVariable), cast(str, StringRef))
    getOrInsertGlobal = Method(ptr(Constant), cast(str, StringRef), ptr(Type))

    # GlobalVariable Iteration
    list_globals = CustomMethod('Module_list_globals', PyObjectPtr)

    # Named MetaData Accessors
    getNamedMetadata = Method(ptr(NamedMDNode), cast(str, StringRef))
    getOrInsertNamedMetadata = Method(ptr(NamedMDNode), cast(str, StringRef))
    eraseNamedMetadata = Method(Void, ptr(NamedMDNode))

    # Named MetaData Iteration
    list_named_metadata = CustomMethod('Module_list_named_metadata',
                                       PyObjectPtr)


    # Utilities
    dump = Method(Void)
    print_ = Method(Void, ref(raw_ostream), ptr(AssemblyAnnotationWriter))
    print_.realname = 'print'

    @CustomPythonMethod
    def __str__(self):
        from llvmpy import extra
        os = extra.make_raw_ostream_for_printing()
        self.print_(os, None)
        return os.str()

    dropAllReferences = Method()

    getTypeByName = Method(ptr(StructType), cast(str, StringRef))

########NEW FILE########
__FILENAME__ = namespace
from binding import *

default = Namespace('')
llvm = default.Namespace('llvm')
sys = llvm.Namespace('sys')
cl = llvm.Namespace('cl')

########NEW FILE########
__FILENAME__ = Pass
from binding import *
from .namespace import llvm

Pass = llvm.Class()
ModulePass = llvm.Class(Pass)
FunctionPass = llvm.Class(Pass)
ImmutablePass = llvm.Class(ModulePass)

from .ADT.StringRef import StringRef
from .Module import Module
from .Value import Function

@Pass
class Pass:
    _include_ = 'llvm/Pass.h'

    delete = Destructor()
    getPassName = Method(cast(StdString, str))
    dump = Method()

@ModulePass
class ModulePass:
    runOnModule = Method(cast(Bool, bool), ref(Module))


@FunctionPass
class FunctionPass:
    doInitialization = Method(cast(Bool, bool), ref(Module))
    doFinalization = Method(cast(Bool, bool), ref(Module))


@ImmutablePass
class ImmutablePass:
    pass


########NEW FILE########
__FILENAME__ = PassManager
from binding import *
from .namespace import llvm

PassManagerBase = llvm.Class()
PassManager = llvm.Class(PassManagerBase)
FunctionPassManager = llvm.Class(PassManagerBase)

from .Pass import Pass
from .Module import Module
from .Value import Function


@PassManagerBase
class PassManagerBase:
    _include_ = 'llvm/PassManager.h'

    delete = Destructor()

    add = Method(Void, ownedptr(Pass))

@PassManager
class PassManager:
    new = Constructor()

    run = Method(cast(Bool, bool), ref(Module))


@FunctionPassManager
class FunctionPassManager:
    new = Constructor(ptr(Module))

    run = Method(cast(Bool, bool), ref(Function))

    doInitialization = Method(cast(Bool, bool))
    doFinalization = Method(cast(Bool, bool))


########NEW FILE########
__FILENAME__ = PassRegistry
from binding import *
from .namespace import llvm
from src.ADT.StringRef import StringRef

PassRegistry = llvm.Class()

from src.PassSupport import PassInfo

@PassRegistry
class PassRegistry:
    _include_ = 'llvm/PassRegistry.h'

    delete = Destructor()

    getPassRegistry = StaticMethod(ownedptr(PassRegistry))

    getPassInfo = Method(const(ptr(PassInfo)), cast(str, StringRef))

    # This is a custom method that wraps enumerateWith
    # Returns list of tuples of (pass-arg, pass-name)
    enumerate = CustomMethod('PassRegistry_enumerate', PyObjectPtr)

########NEW FILE########
__FILENAME__ = PassSupport
from binding import *
from .namespace import llvm

PassInfo = llvm.Class()

from src.Pass import Pass
from src.PassRegistry import PassRegistry

@PassInfo
class PassInfo:
    _include_ = 'llvm/PassSupport.h'

    createPass = Method(ptr(Pass))

llvm.Function('initializeCore', Void, ref(PassRegistry))
llvm.Function('initializeScalarOpts', Void, ref(PassRegistry))
llvm.Function('initializeVectorization', Void, ref(PassRegistry))
llvm.Function('initializeIPO', Void, ref(PassRegistry))
llvm.Function('initializeAnalysis', Void, ref(PassRegistry))
llvm.Function('initializeIPA', Void, ref(PassRegistry))
llvm.Function('initializeTransformUtils', Void, ref(PassRegistry))
llvm.Function('initializeInstCombine', Void, ref(PassRegistry))
llvm.Function('initializeInstrumentation', Void, ref(PassRegistry))
llvm.Function('initializeTarget', Void, ref(PassRegistry))

########NEW FILE########
__FILENAME__ = CodeGen
from binding import *
from ..namespace import llvm


Reloc = llvm.Namespace('Reloc')
Reloc.Enum('Model',
           'Default', 'Static', 'PIC_', 'DynamicNoPIC')

CodeModel = llvm.Namespace('CodeModel')
CodeModel.Enum('Model',
               'Default', 'JITDefault', 'Small', 'Kernel', 'Medium', 'Large')

TLSModel = llvm.Namespace('TLSModel')
TLSModel.Enum('Model',
             'GeneralDynamic', 'LocalDynamic', 'InitialExec', 'LocalExec')

CodeGenOpt = llvm.Namespace('CodeGenOpt')
CodeGenOpt.Enum('Level',
                'None', 'Less', 'Default', 'Aggressive')


########NEW FILE########
__FILENAME__ = CommandLine
from binding import *
from src.namespace import cl

cl.includes.add('llvm/Support/CommandLine.h')

ParseEnvironmentOptions = cl.Function('ParseEnvironmentOptions',
                                      Void,
                                      cast(str, ConstCharPtr), # progName
                                      cast(str, ConstCharPtr), # envvar
                                      cast(str, ConstCharPtr), # overiew = 0
                                      ).require_only(2)


########NEW FILE########
__FILENAME__ = Dwarf
from binding import *
from ..namespace import llvm

dwarf = llvm.Namespace('dwarf')

dwarf.includes.add('llvm/Support/Dwarf.h')

dwarf_constants = dwarf.Enum('dwarf_constants',
'''
DWARF_VERSION
DW_TAG_array_type
DW_TAG_class_type
DW_TAG_entry_point
DW_TAG_enumeration_type
DW_TAG_formal_parameter
DW_TAG_imported_declaration
DW_TAG_label
DW_TAG_lexical_block
DW_TAG_member
DW_TAG_pointer_type
DW_TAG_reference_type
DW_TAG_compile_unit
DW_TAG_string_type
DW_TAG_structure_type
DW_TAG_subroutine_type
DW_TAG_typedef
DW_TAG_union_type
DW_TAG_unspecified_parameters
DW_TAG_variant
DW_TAG_common_block
DW_TAG_common_inclusion
DW_TAG_inheritance
DW_TAG_inlined_subroutine
DW_TAG_module
DW_TAG_ptr_to_member_type
DW_TAG_set_type
DW_TAG_subrange_type
DW_TAG_with_stmt
DW_TAG_access_declaration
DW_TAG_base_type
DW_TAG_catch_block
DW_TAG_const_type
DW_TAG_constant
DW_TAG_enumerator
DW_TAG_file_type
DW_TAG_friend
DW_TAG_namelist
DW_TAG_namelist_item
DW_TAG_packed_type
DW_TAG_subprogram
DW_TAG_template_type_parameter
DW_TAG_template_value_parameter
DW_TAG_thrown_type
DW_TAG_try_block
DW_TAG_variant_part
DW_TAG_variable
DW_TAG_volatile_type
DW_TAG_dwarf_procedure
DW_TAG_restrict_type
DW_TAG_interface_type
DW_TAG_namespace
DW_TAG_imported_module
DW_TAG_unspecified_type
DW_TAG_partial_unit
DW_TAG_imported_unit
DW_TAG_condition
DW_TAG_shared_type
DW_TAG_type_unit
DW_TAG_rvalue_reference_type
DW_TAG_template_alias
DW_TAG_MIPS_loop
DW_TAG_format_label
DW_TAG_function_template
DW_TAG_class_template
DW_TAG_GNU_template_template_param
DW_TAG_GNU_template_parameter_pack
DW_TAG_GNU_formal_parameter_pack
DW_TAG_lo_user
DW_TAG_APPLE_property
DW_TAG_hi_user
DW_CHILDREN_no
DW_CHILDREN_yes
DW_AT_sibling
DW_AT_location
DW_AT_name
DW_AT_ordering
DW_AT_byte_size
DW_AT_bit_offset
DW_AT_bit_size
DW_AT_stmt_list
DW_AT_low_pc
DW_AT_high_pc
DW_AT_language
DW_AT_discr
DW_AT_discr_value
DW_AT_visibility
DW_AT_import
DW_AT_string_length
DW_AT_common_reference
DW_AT_comp_dir
DW_AT_const_value
DW_AT_containing_type
DW_AT_default_value
DW_AT_inline
DW_AT_is_optional
DW_AT_lower_bound
DW_AT_producer
DW_AT_prototyped
DW_AT_return_addr
DW_AT_start_scope
DW_AT_bit_stride
DW_AT_upper_bound
DW_AT_abstract_origin
DW_AT_accessibility
DW_AT_address_class
DW_AT_artificial
DW_AT_base_types
DW_AT_calling_convention
DW_AT_count
DW_AT_data_member_location
DW_AT_decl_column
DW_AT_decl_file
DW_AT_decl_line
DW_AT_declaration
DW_AT_discr_list
DW_AT_encoding
DW_AT_external
DW_AT_frame_base
DW_AT_friend
DW_AT_identifier_case
DW_AT_macro_info
DW_AT_namelist_item
DW_AT_priority
DW_AT_segment
DW_AT_specification
DW_AT_static_link
DW_AT_type
DW_AT_use_location
DW_AT_variable_parameter
DW_AT_virtuality
DW_AT_vtable_elem_location
DW_AT_allocated
DW_AT_associated
DW_AT_data_location
DW_AT_byte_stride
DW_AT_entry_pc
DW_AT_use_UTF8
DW_AT_extension
DW_AT_ranges
DW_AT_trampoline
DW_AT_call_column
DW_AT_call_file
DW_AT_call_line
DW_AT_description
DW_AT_binary_scale
DW_AT_decimal_scale
DW_AT_small
DW_AT_decimal_sign
DW_AT_digit_count
DW_AT_picture_string
DW_AT_mutable
DW_AT_threads_scaled
DW_AT_explicit
DW_AT_object_pointer
DW_AT_endianity
DW_AT_elemental
DW_AT_pure
DW_AT_recursive
DW_AT_signature
DW_AT_main_subprogram
DW_AT_data_bit_offset
DW_AT_const_expr
DW_AT_enum_class
DW_AT_linkage_name
DW_AT_lo_user
DW_AT_hi_user
DW_AT_MIPS_loop_begin
DW_AT_MIPS_tail_loop_begin
DW_AT_MIPS_epilog_begin
DW_AT_MIPS_loop_unroll_factor
DW_AT_MIPS_software_pipeline_depth
DW_AT_MIPS_linkage_name
DW_AT_MIPS_stride
DW_AT_MIPS_abstract_name
DW_AT_MIPS_clone_origin
DW_AT_MIPS_has_inlines
DW_AT_MIPS_stride_byte
DW_AT_MIPS_stride_elem
DW_AT_MIPS_ptr_dopetype
DW_AT_MIPS_allocatable_dopetype
DW_AT_MIPS_assumed_shape_dopetype
DW_AT_MIPS_assumed_size
DW_AT_sf_names
DW_AT_src_info
DW_AT_mac_info
DW_AT_src_coords
DW_AT_body_begin
DW_AT_body_end
DW_AT_APPLE_optimized
DW_AT_APPLE_flags
DW_AT_APPLE_isa
DW_AT_APPLE_block
DW_AT_APPLE_major_runtime_vers
DW_AT_APPLE_runtime_class
DW_AT_APPLE_omit_frame_ptr
DW_AT_APPLE_property_name
DW_AT_APPLE_property_getter
DW_AT_APPLE_property_setter
DW_AT_APPLE_property_attribute
DW_AT_APPLE_objc_complete_type
DW_AT_APPLE_property
DW_FORM_addr
DW_FORM_block2
DW_FORM_block4
DW_FORM_data2
DW_FORM_data4
DW_FORM_data8
DW_FORM_string
DW_FORM_block
DW_FORM_block1
DW_FORM_data1
DW_FORM_flag
DW_FORM_sdata
DW_FORM_strp
DW_FORM_udata
DW_FORM_ref_addr
DW_FORM_ref1
DW_FORM_ref2
DW_FORM_ref4
DW_FORM_ref8
DW_FORM_ref_udata
DW_FORM_indirect
DW_FORM_sec_offset
DW_FORM_exprloc
DW_FORM_flag_present
DW_FORM_ref_sig8
DW_OP_addr
DW_OP_deref
DW_OP_const1u
DW_OP_const1s
DW_OP_const2u
DW_OP_const2s
DW_OP_const4u
DW_OP_const4s
DW_OP_const8u
DW_OP_const8s
DW_OP_constu
DW_OP_consts
DW_OP_dup
DW_OP_drop
DW_OP_over
DW_OP_pick
DW_OP_swap
DW_OP_rot
DW_OP_xderef
DW_OP_abs
DW_OP_and
DW_OP_div
DW_OP_minus
DW_OP_mod
DW_OP_mul
DW_OP_neg
DW_OP_not
DW_OP_or
DW_OP_plus
DW_OP_plus_uconst
DW_OP_shl
DW_OP_shr
DW_OP_shra
DW_OP_xor
DW_OP_skip
DW_OP_bra
DW_OP_eq
DW_OP_ge
DW_OP_gt
DW_OP_le
DW_OP_lt
DW_OP_ne
DW_OP_lit0
DW_OP_lit1
DW_OP_lit2
DW_OP_lit3
DW_OP_lit4
DW_OP_lit5
DW_OP_lit6
DW_OP_lit7
DW_OP_lit8
DW_OP_lit9
DW_OP_lit10
DW_OP_lit11
DW_OP_lit12
DW_OP_lit13
DW_OP_lit14
DW_OP_lit15
DW_OP_lit16
DW_OP_lit17
DW_OP_lit18
DW_OP_lit19
DW_OP_lit20
DW_OP_lit21
DW_OP_lit22
DW_OP_lit23
DW_OP_lit24
DW_OP_lit25
DW_OP_lit26
DW_OP_lit27
DW_OP_lit28
DW_OP_lit29
DW_OP_lit30
DW_OP_lit31
DW_OP_reg0
DW_OP_reg1
DW_OP_reg2
DW_OP_reg3
DW_OP_reg4
DW_OP_reg5
DW_OP_reg6
DW_OP_reg7
DW_OP_reg8
DW_OP_reg9
DW_OP_reg10
DW_OP_reg11
DW_OP_reg12
DW_OP_reg13
DW_OP_reg14
DW_OP_reg15
DW_OP_reg16
DW_OP_reg17
DW_OP_reg18
DW_OP_reg19
DW_OP_reg20
DW_OP_reg21
DW_OP_reg22
DW_OP_reg23
DW_OP_reg24
DW_OP_reg25
DW_OP_reg26
DW_OP_reg27
DW_OP_reg28
DW_OP_reg29
DW_OP_reg30
DW_OP_reg31
DW_OP_breg0
DW_OP_breg1
DW_OP_breg2
DW_OP_breg3
DW_OP_breg4
DW_OP_breg5
DW_OP_breg6
DW_OP_breg7
DW_OP_breg8
DW_OP_breg9
DW_OP_breg10
DW_OP_breg11
DW_OP_breg12
DW_OP_breg13
DW_OP_breg14
DW_OP_breg15
DW_OP_breg16
DW_OP_breg17
DW_OP_breg18
DW_OP_breg19
DW_OP_breg20
DW_OP_breg21
DW_OP_breg22
DW_OP_breg23
DW_OP_breg24
DW_OP_breg25
DW_OP_breg26
DW_OP_breg27
DW_OP_breg28
DW_OP_breg29
DW_OP_breg30
DW_OP_breg31
DW_OP_regx
DW_OP_fbreg
DW_OP_bregx
DW_OP_piece
DW_OP_deref_size
DW_OP_xderef_size
DW_OP_nop
DW_OP_push_object_address
DW_OP_call2
DW_OP_call4
DW_OP_call_ref
DW_OP_form_tls_address
DW_OP_call_frame_cfa
DW_OP_bit_piece
DW_OP_implicit_value
DW_OP_stack_value
DW_OP_lo_user
DW_OP_hi_user
DW_ATE_address
DW_ATE_boolean
DW_ATE_complex_float
DW_ATE_float
DW_ATE_signed
DW_ATE_signed_char
DW_ATE_unsigned
DW_ATE_unsigned_char
DW_ATE_imaginary_float
DW_ATE_packed_decimal
DW_ATE_numeric_string
DW_ATE_edited
DW_ATE_signed_fixed
DW_ATE_unsigned_fixed
DW_ATE_decimal_float
DW_ATE_UTF
DW_ATE_lo_user
DW_ATE_hi_user
DW_DS_unsigned
DW_DS_leading_overpunch
DW_DS_trailing_overpunch
DW_DS_leading_separate
DW_DS_trailing_separate
DW_END_default
DW_END_big
DW_END_little
DW_END_lo_user
DW_END_hi_user
DW_ACCESS_public
DW_ACCESS_protected
DW_ACCESS_private
DW_VIS_local
DW_VIS_exported
DW_VIS_qualified
DW_VIRTUALITY_none
DW_VIRTUALITY_virtual
DW_VIRTUALITY_pure_virtual
DW_LANG_C89
DW_LANG_C
DW_LANG_Ada83
DW_LANG_C_plus_plus
DW_LANG_Cobol74
DW_LANG_Cobol85
DW_LANG_Fortran77
DW_LANG_Fortran90
DW_LANG_Pascal83
DW_LANG_Modula2
DW_LANG_Java
DW_LANG_C99
DW_LANG_Ada95
DW_LANG_Fortran95
DW_LANG_PLI
DW_LANG_ObjC
DW_LANG_ObjC_plus_plus
DW_LANG_UPC
DW_LANG_D
DW_LANG_Python
DW_LANG_lo_user
DW_LANG_Mips_Assembler
DW_LANG_hi_user
DW_ID_case_sensitive
DW_ID_up_case
DW_ID_down_case
DW_ID_case_insensitive
DW_CC_normal
DW_CC_program
DW_CC_nocall
DW_CC_lo_user
DW_CC_hi_user
DW_INL_not_inlined
DW_INL_inlined
DW_INL_declared_not_inlined
DW_INL_declared_inlined
DW_ORD_row_major
DW_ORD_col_major
DW_DSC_label
DW_DSC_range
DW_LNS_extended_op
DW_LNS_copy
DW_LNS_advance_pc
DW_LNS_advance_line
DW_LNS_set_file
DW_LNS_set_column
DW_LNS_negate_stmt
DW_LNS_set_basic_block
DW_LNS_const_add_pc
DW_LNS_fixed_advance_pc
DW_LNS_set_prologue_end
DW_LNS_set_epilogue_begin
DW_LNS_set_isa
DW_LNE_end_sequence
DW_LNE_set_address
DW_LNE_define_file
DW_LNE_set_discriminator
DW_LNE_lo_user
DW_LNE_hi_user
DW_MACINFO_define
DW_MACINFO_undef
DW_MACINFO_start_file
DW_MACINFO_end_file
DW_MACINFO_vendor_ext
DW_CFA_extended
DW_CFA_nop
DW_CFA_advance_loc
DW_CFA_offset
DW_CFA_restore
DW_CFA_set_loc
DW_CFA_advance_loc1
DW_CFA_advance_loc2
DW_CFA_advance_loc4
DW_CFA_offset_extended
DW_CFA_restore_extended
DW_CFA_undefined
DW_CFA_same_value
DW_CFA_register
DW_CFA_remember_state
DW_CFA_restore_state
DW_CFA_def_cfa
DW_CFA_def_cfa_register
DW_CFA_def_cfa_offset
DW_CFA_def_cfa_expression
DW_CFA_expression
DW_CFA_offset_extended_sf
DW_CFA_def_cfa_sf
DW_CFA_def_cfa_offset_sf
DW_CFA_val_offset
DW_CFA_val_offset_sf
DW_CFA_val_expression
DW_CFA_MIPS_advance_loc8
DW_CFA_GNU_window_save
DW_CFA_GNU_args_size
DW_CFA_lo_user
DW_CFA_hi_user
DW_EH_PE_absptr
DW_EH_PE_omit
DW_EH_PE_uleb128
DW_EH_PE_udata2
DW_EH_PE_udata4
DW_EH_PE_udata8
DW_EH_PE_sleb128
DW_EH_PE_sdata2
DW_EH_PE_sdata4
DW_EH_PE_sdata8
DW_EH_PE_signed
DW_EH_PE_pcrel
DW_EH_PE_textrel
DW_EH_PE_datarel
DW_EH_PE_funcrel
DW_EH_PE_aligned
DW_EH_PE_indirect
DW_APPLE_PROPERTY_readonly
DW_APPLE_PROPERTY_readwrite
DW_APPLE_PROPERTY_assign
DW_APPLE_PROPERTY_retain
DW_APPLE_PROPERTY_copy
DW_APPLE_PROPERTY_nonatomic
''')

### The following enums are not available in LLVM 3.2
#    DW_AT_GNU_dwo_name
#    DW_AT_GNU_vector
#    DW_AT_GNU_template_name
#    DW_AT_GNU_dwo_id
#    DW_AT_GNU_ranges_base
#    DW_AT_GNU_addr_base
#    DW_AT_GNU_pubnames
#    DW_AT_GNU_pubtypes
#    DW_FORM_GNU_addr_index
#    DW_FORM_GNU_str_index
#    DW_OP_GNU_addr_index
#    DW_OP_GNU_const_index

########NEW FILE########
__FILENAME__ = DynamicLibrary
from binding import *
from ..namespace import sys
from ..ADT.StringRef import StringRef

DynamicLibrary = sys.Class()


@DynamicLibrary
class DynamicLibrary:
    _include_ = 'llvm/Support/DynamicLibrary.h'
    isValid = Method(cast(Bool, bool))
    getAddressOfSymbol = Method(cast(VoidPtr, int), cast(str, ConstCharPtr))

    LoadPermanentLibrary = CustomStaticMethod(
                          'DynamicLibrary_LoadLibraryPermanently',
                          PyObjectPtr,             # bool --- failed?
                          cast(str, ConstCharPtr), # filename
                          PyObjectPtr,             # std::string * errmsg = 0
                          ).require_only(1)

    SearchForAddressOfSymbol = StaticMethod(cast(VoidPtr, int), # address
                                            cast(str, ConstCharPtr), # symName
                                            )

    AddSymbol = StaticMethod(Void,
                             cast(str, StringRef), # symbolName
                             cast(int, VoidPtr),   # address
                             )

    getPermanentLibrary = CustomStaticMethod(
                          'DynamicLibrary_getPermanentLibrary',
                          PyObjectPtr,
                          cast(str, ConstCharPtr), # filename
                          PyObjectPtr,             # std::string * errmsg = 0
                          ).require_only(1)

########NEW FILE########
__FILENAME__ = FormattedStream
from binding import *
from ..namespace import llvm
from .raw_ostream import raw_ostream

@llvm.Class(raw_ostream)
class formatted_raw_ostream:
    _include_ = 'llvm/Support/FormattedStream.h'
    _new = Constructor(ref(raw_ostream), cast(bool, Bool))

    @CustomPythonStaticMethod
    def new(stream, destroy=False):
        inst = formatted_raw_ostream._new(stream, destroy)
        inst.__underlying_stream = stream # to prevent it being freed first
        return inst


########NEW FILE########
__FILENAME__ = Host
from binding import *
from src.namespace import sys

getDefaultTargetTriple = sys.Function('getDefaultTargetTriple',
                                      cast(ConstStdString, str))

if LLVM_VERSION >= (3, 3):
    getProcessTriple = sys.Function('getProcessTriple',
                                    cast(ConstStdString, str))

    isLittleEndianHost = sys.CustomFunction('isLittleEndianHost',
                                            'llvm_sys_isLittleEndianHost',
                                            cast(Bool, bool))

    isBigEndianHost = sys.CustomFunction('isBigEndianHost',
                                         'llvm_sys_isBigEndianHost',
                                         cast(Bool, bool))

else:

    isLittleEndianHost = sys.Function('isLittleEndianHost',
                                      cast(Bool, bool))

    isBigEndianHost = sys.Function('isBigEndianHost',
                                   cast(Bool, bool))


getHostCPUName = sys.Function('getHostCPUName',
                              cast(ConstStdString, str))

getHostCPUFeatures = sys.CustomFunction('getHostCPUFeatures',
                                        'llvm_sys_getHostCPUFeatures',
                                        PyObjectPtr, # bool: success?
                                        PyObjectPtr, # dict: store feature map
                                        )


########NEW FILE########
__FILENAME__ = raw_ostream
from binding import *
from ..namespace import llvm
from ..LLVMContext import LLVMContext
from ..ADT.StringRef import StringRef

@llvm.Class()
class raw_ostream:
    _include_ = "llvm/Support/raw_ostream.h"
    delete = Destructor()
    flush = Method()

@llvm.Class(raw_ostream)
class raw_svector_ostream:
    _include_ = "llvm/Support/raw_os_ostream.h"
    _base_ = raw_ostream

    str = Method(cast(str, StringRef))
    bytes = Method(cast(bytes, StringRef))
    bytes.realname = 'str'


########NEW FILE########
__FILENAME__ = SourceMgr
from binding import *
from ..namespace import llvm

llvm.includes.add('llvm/Support/SourceMgr.h')

@llvm.Class()
class SMDiagnostic:
    new = Constructor()
    delete = Destructor()


########NEW FILE########
__FILENAME__ = StringRefMemoryObject
from binding import *
from ..namespace import llvm
from ..ADT.StringRef import StringRef

if LLVM_VERSION >= (3, 4):
    MemoryObject = llvm.Class()
    StringRefMemoryObject = llvm.Class(MemoryObject)

    @MemoryObject
    class MemoryObject:
        _include_ = "llvm/Support/MemoryObject.h"

        getBase = Method(cast(Uint64, int))
        getExtent = Method(cast(Uint64, int))

        readBytes = CustomMethod('MemoryObject_readBytes',
                                 PyObjectPtr,
                                 cast(int, Uint64), #address
                                 cast(int, Uint64)  #size
                                 )
        @CustomPythonMethod
        def readAll(self):
            result = self.readBytes(self.getBase(), self.getExtent())
            if not result:
                raise Exception("expected readBytes to be successful!")
            return result

    @StringRefMemoryObject
    class StringRefMemoryObject:
        _include_ = "llvm/Support/StringRefMemoryObject.h"

        new = Constructor(cast(bytes, StringRef), cast(int, Uint64))

########NEW FILE########
__FILENAME__ = TargetRegistry
from binding import *
from src.namespace import llvm

llvm.includes.add('llvm/Support/TargetRegistry.h')

Target = llvm.Class()
TargetRegistry = llvm.Class()

from src.ADT.Triple import Triple
from src.ADT.StringRef import StringRef
from src.Target.TargetMachine import TargetMachine
from src.Target.TargetOptions import TargetOptions
from src.Support.CodeGen import Reloc, CodeModel, CodeGenOpt

if LLVM_VERSION >= (3, 4):
    from src.MC import MCSubtargetInfo
    from src.MC import MCDisassembler
    from src.MC import MCRegisterInfo
    from src.MC import MCAsmInfo
    from src.MC import MCInstrInfo
    from src.MC import MCInstrAnalysis
    from src.MC import MCInstPrinter

@Target
class Target:
    getNext = Method(const(ownedptr(Target)))

    getName = Method(cast(StdString, str))
    getShortDescription = Method(cast(StdString, str))

    def _has():
        return Method(cast(Bool, bool))

    hasJIT = _has()
    hasTargetMachine = _has()
    hasMCAsmBackend = _has()
    hasMCAsmParser = _has()
    hasAsmPrinter = _has()
    hasMCDisassembler = _has()
    hasMCInstPrinter = _has()
    hasMCCodeEmitter = _has()
    hasMCObjectStreamer = _has()
    hasAsmStreamer = _has()

    createTargetMachine = Method(ptr(TargetMachine),
                                 cast(str, StringRef), # triple
                                 cast(str, StringRef), # cpu
                                 cast(str, StringRef), # features
                                 ref(TargetOptions),
                                 Reloc.Model,       # = Reloc::Default
                                 CodeModel.Model,   # = CodeModel.Default
                                 CodeGenOpt.Level,  # = CodeGenOpt.Default
                                 ).require_only(4)

    if LLVM_VERSION >= (3, 4):
        createMCSubtargetInfo = Method(ptr(MCSubtargetInfo),
                                       cast(str, StringRef), #triple
                                       cast(str, StringRef), #cpu
                                       cast(str, StringRef)  #features
                                       )

        createMCDisassembler = Method(ptr(MCDisassembler), ref(MCSubtargetInfo))

        createMCRegInfo = Method(ptr(MCRegisterInfo),
                                 cast(str, StringRef)        #Triple
                                 )

        createMCAsmInfo = Method(ptr(MCAsmInfo),
                                 const(ref(MCRegisterInfo)), #MRI
                                 cast(str, StringRef)        #Triple
                                 )

        createMCInstrInfo = Method(ptr(MCInstrInfo))

        createMCInstrAnalysis = Method(ptr(MCInstrAnalysis), const(ptr(MCInstrInfo)))

        createMCInstPrinter = Method(ptr(MCInstPrinter),
                                     cast(int, Unsigned),        #SyntaxVariant
                                     const(ref(MCAsmInfo)),      #MAI
                                     const(ref(MCInstrInfo)),    #MII
                                     const(ref(MCRegisterInfo)), #MRI
                                     const(ref(MCSubtargetInfo)) #STI
                                     )
@TargetRegistry
class TargetRegistry:
    printRegisteredTargetsForVersion = StaticMethod()

    lookupTarget = CustomStaticMethod('TargetRegistry_lookupTarget',
                                        PyObjectPtr,         # const Target*
                                        cast(str, ConstCharPtr), # triple
                                        PyObjectPtr,         # std::string &Error
                                        )

    lookupTarget |= CustomStaticMethod('TargetRegistry_lookupTarget',
                                        PyObjectPtr,             # const Target*
                                        cast(str, ConstCharPtr), # arch
                                        ref(Triple),             # triple
                                        PyObjectPtr,         # std::string &Error
                                        )

    getClosestTargetForJIT = CustomStaticMethod(
                                    'TargetRegistry_getClosestTargetForJIT',
                                    PyObjectPtr,          # const Target*
                                    PyObjectPtr,          # std::string &Error
                                    )

    targetsList = CustomStaticMethod('TargetRegistry_targets_list', PyObjectPtr)


########NEW FILE########
__FILENAME__ = TargetSelect
import os
from binding import *
from ..namespace import llvm, default

llvm.includes.add('llvm/Support/TargetSelect.h')



InitializeNativeTarget = llvm.Function('InitializeNativeTarget')
InitializeNativeTargetAsmPrinter = llvm.Function(
                    'InitializeNativeTargetAsmPrinter', cast(Bool, bool))
InitializeNativeTargetAsmParser = llvm.Function(
                    'InitializeNativeTargetAsmParser', cast(Bool, bool))
InitializeNativeTargetDisassembler = llvm.Function(
                    'InitializeNativeTargetDisassembler', cast(Bool, bool))

InitializeAllTargets = llvm.Function('InitializeAllTargets')
InitializeAllTargetInfos = llvm.Function('InitializeAllTargetInfos')
InitializeAllTargetMCs = llvm.Function('InitializeAllTargetMCs')
InitializeAllAsmPrinters = llvm.Function('InitializeAllAsmPrinters')
InitializeAllDisassemblers = llvm.Function('InitializeAllDisassemblers')
InitializeAllAsmParsers = llvm.Function('InitializeAllAsmParsers')


for target in TARGETS_BUILT:
    decls = 'Target', 'TargetInfo', 'TargetMC', 'AsmPrinter'
    for k in map(lambda x: 'LLVMInitialize%s%s' % (target, x), decls):
        if k == 'LLVMInitializeCppBackendAsmPrinter':
            continue
        globals()[k] = default.Function(k)


########NEW FILE########
__FILENAME__ = TargetLibraryInfo
from binding import *
from ..namespace import llvm

from src.Pass import ImmutablePass

TargetLibraryInfo = llvm.Class(ImmutablePass)

LibFunc = llvm.Namespace('LibFunc')
LibFunc.Enum('Func',  '''
                ZdaPv, ZdlPv, Znaj, ZnajRKSt9nothrow_t,
                Znam, ZnamRKSt9nothrow_t, Znwj, ZnwjRKSt9nothrow_t,
                Znwm, ZnwmRKSt9nothrow_t, cxa_atexit, cxa_guard_abort,
                cxa_guard_acquire, cxa_guard_release, memcpy_chk,
                acos, acosf, acosh, acoshf,
                acoshl, acosl, asin, asinf,
                asinh, asinhf, asinhl, asinl,
                atan, atan2, atan2f, atan2l,
                atanf, atanh, atanhf, atanhl,
                atanl, calloc, cbrt, cbrtf,
                cbrtl, ceil, ceilf, ceill,
                copysign, copysignf, copysignl, cos,
                cosf, cosh, coshf, coshl,
                cosl, exp, exp10, exp10f,
                exp10l, exp2, exp2f, exp2l,
                expf, expl, expm1, expm1f,
                expm1l, fabs, fabsf, fabsl,
                fiprintf,
                floor, floorf, floorl, fmod,
                fmodf, fmodl, fputc,
                fputs, free, fwrite, iprintf,
                log, log10, log10f, log10l,
                log1p, log1pf, log1pl, log2,
                log2f, log2l, logb, logbf,
                logbl, logf, logl, malloc,
                memchr, memcmp, memcpy, memmove,
                memset, memset_pattern16, nearbyint, nearbyintf,
                nearbyintl, posix_memalign, pow, powf,
                powl, putchar, puts,
                realloc, reallocf, rint, rintf,
                rintl, round, roundf, roundl,
                sin, sinf, sinh, sinhf,
                sinhl, sinl, siprintf,
                sqrt, sqrtf, sqrtl, stpcpy,
                strcat, strchr, strcmp, strcpy,
                strcspn, strdup, strlen, strncat,
                strncmp, strncpy, strndup, strnlen,
                strpbrk, strrchr, strspn, strstr,
                strtod, strtof, strtol, strtold,
                strtoll, strtoul, strtoull, tan,
                tanf, tanh, tanhf, tanhl,
                tanl, trunc, truncf,
                truncl, valloc, NumLibFuncs''')
                # not in llvm-3.2 abs, ffs, ffsl, ffsll, fprintf, isascii,
                #             isdigit, labs, llabs, printf, sprintf, toascii

from src.ADT.Triple import Triple
from src.ADT.StringRef import StringRef


@TargetLibraryInfo
class TargetLibraryInfo:
    _include_ = 'llvm/Target/TargetLibraryInfo.h'

    new = Constructor()
    new |= Constructor(ref(Triple))

    delete = Destructor()

    has = Method(cast(bool, Bool), LibFunc.Func)
    hasOptimizedCodeGen = Method(cast(bool, Bool), LibFunc.Func)

    getName = Method(cast(str, StringRef), LibFunc.Func)

    setUnavailable = Method(Void, LibFunc.Func)
    setAvailable = Method(Void, LibFunc.Func)
    setAvailableWithName = Method(Void, LibFunc.Func, cast(str, StringRef))
    disableAllFunctions = Method()


########NEW FILE########
__FILENAME__ = TargetMachine
from binding import *
from src.namespace import llvm

TargetMachine = llvm.Class()

from src.Support.TargetRegistry import Target
from src.ADT.StringRef import StringRef
from src.Support.CodeGen import CodeModel, TLSModel, CodeGenOpt, Reloc
from src.GlobalValue import GlobalValue
from src.DataLayout import DataLayout
if LLVM_VERSION >= (3, 4):
    from src.MC import MCAsmInfo, \
                       TargetInstrInfo, \
                       TargetSubtargetInfo, \
                       TargetRegisterInfo

if LLVM_VERSION < (3, 3):
    from src.TargetTransformInfo import (ScalarTargetTransformInfo,
                                         VectorTargetTransformInfo)
from src.PassManager import PassManagerBase
from src.Support.FormattedStream import formatted_raw_ostream

@TargetMachine
class TargetMachine:
    _include_ = 'llvm/Target/TargetMachine.h'

    CodeGenFileType = Enum('''
                           CGFT_AssemblyFile
                           CGFT_ObjectFile
                           CGFT_Null''')

    delete = Destructor()

    getTarget = Method(const(ref(Target)))

    getTargetTriple = Method(cast(StringRef, str))
    getTargetCPU = Method(cast(StringRef, str))
    getTargetFeatureString = Method(cast(StringRef, str))

    getRelocationModel = Method(Reloc.Model)
    getCodeModel = Method(CodeModel.Model)
    getTLSModel = Method(TLSModel.Model, ptr(GlobalValue))
    getOptLevel = Method(CodeGenOpt.Level)

    hasMCUseDwarfDirectory = Method(cast(Bool, bool))
    setMCUseDwarfDirectory = Method(Void, cast(bool, Bool))

    getDataLayout = Method(const(ownedptr(DataLayout)))

    if LLVM_VERSION < (3, 3):
        getScalarTargetTransformInfo = Method(const(
                                          ownedptr(ScalarTargetTransformInfo)))
        getVectorTargetTransformInfo = Method(const(
                                          ownedptr(VectorTargetTransformInfo)))

    else:
        addAnalysisPasses = Method(Void, ref(PassManagerBase))

    addPassesToEmitFile = Method(cast(bool, Bool),
                                 ref(PassManagerBase),
                                 ref(formatted_raw_ostream),
                                 CodeGenFileType,
                                 cast(bool, Bool)
                                 ).require_only(3)

    if LLVM_VERSION >= (3, 4):
        getSubtargetImpl = Method(const(ownedptr(TargetSubtargetInfo)))

        getMCAsmInfo = Method(const(ownedptr(MCAsmInfo)))

        getInstrInfo = Method(const(ownedptr(TargetInstrInfo)))

        getRegisterInfo = Method(const(ownedptr(TargetRegisterInfo)))


########NEW FILE########
__FILENAME__ = TargetOptions
from binding import *
from src.namespace import llvm

llvm.includes.add('llvm/Target/TargetOptions.h')

TargetOptions = llvm.Class()

@TargetOptions
class TargetOptions:
    new = Constructor()
    delete = Destructor()


########NEW FILE########
__FILENAME__ = TargetTransformInfo
from binding import *
from src.namespace import llvm
from src.Pass import ImmutablePass

if LLVM_VERSION >= (3, 3):
    llvm.includes.add('llvm/Analysis/TargetTransformInfo.h')
else:
    llvm.includes.add('llvm/TargetTransformInfo.h')

TargetTransformInfo = llvm.Class(ImmutablePass)
ScalarTargetTransformInfo = llvm.Class()
VectorTargetTransformInfo = llvm.Class()


@ScalarTargetTransformInfo
class ScalarTargetTransformInfo:
    if LLVM_VERSION < (3, 3):
        delete = Destructor()

@VectorTargetTransformInfo
class VectorTargetTransformInfo:
    if LLVM_VERSION < (3, 3):
        delete = Destructor()

@TargetTransformInfo
class TargetTransformInfo:
    if LLVM_VERSION < (3, 3):
        new = Constructor(ptr(ScalarTargetTransformInfo),
                          ptr(VectorTargetTransformInfo))


########NEW FILE########
__FILENAME__ = IPO
from binding import *
from ..namespace import llvm
from ..Pass import Pass

llvm.includes.add('llvm/Transforms/IPO.h')

createFunctionInliningPass = llvm.Function('createFunctionInliningPass',
                                           ptr(Pass),
                                           cast(int, Unsigned)).require_only(0)

########NEW FILE########
__FILENAME__ = PassManagerBuilder
from binding import *
from ..namespace import llvm

PassManagerBuilder = llvm.Class()

from src.PassManager import PassManagerBase, FunctionPassManager
from src.Target.TargetLibraryInfo import TargetLibraryInfo
from src.Pass import Pass

@PassManagerBuilder
class PassManagerBuilder:
    _include_ = 'llvm/Transforms/IPO/PassManagerBuilder.h'

    new = Constructor()
    delete = Destructor()

    populateFunctionPassManager = Method(Void, ref(FunctionPassManager))
    populateModulePassManager = Method(Void, ref(PassManagerBase))
    populateLTOPassManager = Method(Void,
                                    ref(PassManagerBase),
                                    cast(bool, Bool),
                                    cast(bool, Bool),
                                    cast(bool, Bool)).require_only(3)

    def _attr_int():
        return Attr(getter=cast(Unsigned, int),
                    setter=cast(int, Unsigned))

    OptLevel = _attr_int()
    SizeLevel = _attr_int()

    def _attr_bool():
        return Attr(getter=cast(Bool, bool),
                    setter=cast(bool, Bool))

    if LLVM_VERSION <= (3, 3):
        DisableSimplifyLibCalls = _attr_bool()

    DisableUnitAtATime = _attr_bool()
    DisableUnrollLoops = _attr_bool()
    if LLVM_VERSION >= (3, 3):
        BBVectorize = _attr_bool()
        SLPVectorize = _attr_bool()
    else:
        Vectorize = _attr_bool()
    LoopVectorize = _attr_bool()

    LibraryInfo = Attr(getter=ownedptr(TargetLibraryInfo),
                       setter=ownedptr(TargetLibraryInfo))

    Inliner = Attr(getter=ownedptr(Pass),
                   setter=ownedptr(Pass))

########NEW FILE########
__FILENAME__ = BasicBlockUtils
from binding import *
from src.namespace import llvm
from src.Value import MDNode
from src.Instruction import Instruction, TerminatorInst
llvm.includes.add('llvm/Transforms/Utils/BasicBlockUtils.h')

SplitBlockAndInsertIfThen = llvm.Function('SplitBlockAndInsertIfThen',
                                          ptr(TerminatorInst),
                                          ptr(Instruction), # cmp
                                          cast(bool, Bool), # unreachable
                                          ptr(MDNode)) # branchweights

ReplaceInstWithInst = llvm.Function('ReplaceInstWithInst',
                                    Void,
                                    ptr(Instruction), # from
                                    ptr(Instruction)) # to

########NEW FILE########
__FILENAME__ = Cloning
from binding import *
from src.namespace import llvm

llvm.includes.add('llvm/Transforms/Utils/Cloning.h')

InlineFunctionInfo = llvm.Class()


from src.Module import Module
from src.Instruction import CallInst

@InlineFunctionInfo
class InlineFunctionInfo:
    new = Constructor()
    delete = Destructor()


CloneModule = llvm.Function('CloneModule', ptr(Module), ptr(Module))

InlineFunction = llvm.Function('InlineFunction',
                               cast(Bool, bool),    # bool --- failed
                               ptr(CallInst),
                               ref(InlineFunctionInfo),
                               cast(bool, Bool),    # insert lifetime = true
                               ).require_only(2)

########NEW FILE########
__FILENAME__ = Type
from binding import *
from .namespace import llvm
from .LLVMContext import LLVMContext
from .Support.raw_ostream import raw_ostream
from .ADT.StringRef import StringRef

Type = llvm.Class()
IntegerType = llvm.Class(Type)
CompositeType = llvm.Class(Type)
StructType = llvm.Class(CompositeType)
SequentialType = llvm.Class(CompositeType)
ArrayType = llvm.Class(SequentialType)
PointerType = llvm.Class(SequentialType)
VectorType = llvm.Class(SequentialType)

@Type
class Type:
    if LLVM_VERSION >= (3, 3):
        _include_ = 'llvm/IR/Type.h'
    else:
        _include_ = 'llvm/Type.h'

    TypeID = Enum('''
        VoidTyID, HalfTyID, FloatTyID, DoubleTyID,
        X86_FP80TyID, FP128TyID, PPC_FP128TyID, LabelTyID,
        MetadataTyID, X86_MMXTyID, IntegerTyID, FunctionTyID,
        StructTyID, ArrayTyID, PointerTyID, VectorTyID,
        NumTypeIDs, LastPrimitiveTyID, FirstDerivedTyID
        ''')

    getContext = Method(ref(LLVMContext))
    dump = Method()
    print_ = Method(Void, ref(raw_ostream))
    print_.realname = 'print'

    getTypeID = Method(TypeID)

    def type_checker():
        return Method(cast(Bool, bool))

    isVoidTy = type_checker()
    isHalfTy = type_checker()
    isFloatTy = type_checker()
    isDoubleTy = type_checker()
    isX86_FP80Ty = type_checker()
    isFP128Ty = type_checker()
    isPPC_FP128Ty = type_checker()
    isFloatingPointTy = type_checker()
    isX86_MMXTy = type_checker()
    isFPOrFPVectorTy = type_checker()
    isLabelTy = type_checker()
    isMetadataTy = type_checker()
    isIntOrIntVectorTy = type_checker()
    isFunctionTy = type_checker()
    isStructTy = type_checker()
    isArrayTy = type_checker()
    isPointerTy = type_checker()
    isPtrOrPtrVectorTy = type_checker()
    isVectorTy = type_checker()
    isEmptyTy = type_checker()
    isPrimitiveType = type_checker()
    isDerivedType = type_checker()
    isFirstClassType = type_checker()
    isSingleValueType = type_checker()
    isAggregateType = type_checker()
    isSized = type_checker()

    isIntegerTy = Method(cast(Bool, bool))
    isIntegerTy |= Method(cast(Bool, bool), cast(int, Unsigned))

    getIntegerBitWidth = Method(cast(Unsigned, int))
    getFunctionParamType = Method(ptr(Type), cast(int, Unsigned))
    getFunctionNumParams = Method(cast(int, Unsigned))

    isFunctionVarArg = type_checker()

    getStructName = Method(cast(StringRef, str))
    getStructNumElements = Method(cast(Unsigned, int))
    getStructElementType = Method(ptr(Type), cast(int, Unsigned))
    getSequentialElementType = Method(ptr(Type))

    # Factories


    def type_factory():
        return StaticMethod(ptr(Type), ref(LLVMContext))

    getVoidTy = type_factory()
    getLabelTy = type_factory()
    getHalfTy = type_factory()
    getFloatTy = type_factory()
    getDoubleTy = type_factory()
    getMetadataTy = type_factory()
    getX86_FP80Ty = type_factory()
    getFP128Ty = type_factory()
    getPPC_FP128Ty = type_factory()
    getX86_MMXTy = type_factory()

    getIntNTy = StaticMethod(ptr(IntegerType),
                             ref(LLVMContext), cast(Unsigned, int))

    def integer_factory():
        return StaticMethod(ptr(IntegerType), ref(LLVMContext))

    getInt1Ty = integer_factory()
    getInt8Ty = integer_factory()
    getInt16Ty = integer_factory()
    getInt32Ty = integer_factory()
    getInt64Ty = integer_factory()

    def pointer_factory():
        return StaticMethod(ptr(PointerType), ref(LLVMContext))

    getHalfPtrTy = pointer_factory()
    getFloatPtrTy = pointer_factory()
    getDoublePtrTy = pointer_factory()
    getX86_FP80PtrTy = pointer_factory()
    getFP128PtrTy = pointer_factory()
    getPPC_FP128PtrTy = pointer_factory()
    getX86_MMXPtrTy = pointer_factory()
    getInt1PtrTy = pointer_factory()
    getInt8PtrTy = pointer_factory()
    getInt16PtrTy = pointer_factory()
    getInt32PtrTy = pointer_factory()
    getInt64PtrTy = pointer_factory()
    getIntNPtrTy = StaticMethod(ptr(PointerType),
                                ref(LLVMContext), cast(int, Unsigned))

    @CustomPythonMethod
    def __str__(self):
        from llvmpy import extra
        os = extra.make_raw_ostream_for_printing()
        self.print_(os)
        return os.str()

    getContainedType = Method(ptr(Type), cast(int, Unsigned))
    getNumContainedTypes = Method(cast(int, Unsigned))

    getArrayNumElements = Method(cast(Uint64, int))
    getArrayElementType = Method(ptr(Type))

    getVectorNumElements = Method(cast(Unsigned, int))
    getVectorElementType = Method(ptr(Type))

    getPointerElementType = Method(ptr(Type))
    getPointerAddressSpace = Method(cast(Unsigned, int))
    getPointerTo = Method(ptr(PointerType), cast(int, Unsigned))


@IntegerType
class IntegerType:
    _downcast_ = Type


@CompositeType
class CompositeType:
    _downcast_ = Type

@SequentialType
class SequentialType:
    _downcast_ = Type

@ArrayType
class ArrayType:
    _downcast_ = Type
    getNumElements = Method(cast(Uint64, int))
    get = StaticMethod(ptr(ArrayType), ptr(Type), cast(int, Uint64))
    isValidElementType = StaticMethod(cast(Bool, bool), ptr(Type))

@PointerType
class PointerType:
    _downcast_ = Type
    getAddressSpace = Method(cast(Unsigned, int))
    get = StaticMethod(ptr(PointerType), ptr(Type), cast(int, Unsigned))
    getUnqual = StaticMethod(ptr(PointerType), ptr(Type))
    isValidElementType = StaticMethod(cast(Bool, bool), ptr(Type))

@VectorType
class VectorType:
    _downcast_ = Type
    getNumElements = Method(cast(Unsigned, int))
    getBitWidth = Method(cast(Unsigned, int))
    get = StaticMethod(ptr(VectorType), ptr(Type), cast(int, Unsigned))
    getInteger = StaticMethod(ptr(VectorType), ptr(VectorType))
    getExtendedElementVectorType = StaticMethod(ptr(VectorType),
                                                ptr(VectorType))
    getTruncatedElementVectorType = StaticMethod(ptr(VectorType),
                                                 ptr(VectorType))
    isValidElementType = StaticMethod(cast(Bool, bool), ptr(Type))

@StructType
class StructType:
    _downcast_ = Type
    isPacked = Method(cast(Bool, bool))
    isLiteral = Method(cast(Bool, bool))
    isOpaque = Method(cast(Bool, bool))
    hasName = Method(cast(Bool, bool))
    getName = Method(cast(StringRef, str))
    setName = Method(Void, cast(str, StringRef))
    setBody = CustomMethod('StructType_setBody',
                           PyObjectPtr, # None
                           PyObjectPtr, # ArrayRef<Type*>
                           cast(bool, Bool),
                           ).require_only(1)
    getNumElements = Method(cast(Unsigned, int))
    getElementType = Method(ptr(Type), cast(int, Unsigned))

    create = StaticMethod(ptr(StructType),
                          ref(LLVMContext),
                          cast(str, StringRef),
                          ).require_only(1)

    get = CustomStaticMethod('StructType_get',
                             PyObjectPtr,           # StructType*
                             ref(LLVMContext),
                             PyObjectPtr,           # ArrayRef <Type*> elements
                             cast(bool, Bool),      # is packed
                             ).require_only(2)

    isLayoutIdentical = Method(cast(Bool, bool), # identical?
                               ptr(StructType))  # other

    isValidElementType = StaticMethod(cast(Bool, bool), ptr(Type))


########NEW FILE########
__FILENAME__ = User
from binding import *
from .namespace import llvm
from .Value import Value, User

@User
class User:
    _downcast_ = Value
    getOperand = Method(ptr(Value), cast(int, Unsigned))
    setOperand = Method(Void, cast(int, Unsigned), ptr(Value))
    getNumOperands = Method(cast(Unsigned, int))


########NEW FILE########
__FILENAME__ = Value
from binding import *
from .namespace import llvm

# forward declarations
Value = llvm.Class()
Argument = llvm.Class(Value)
MDNode = llvm.Class(Value)
MDString = llvm.Class(Value)
User = llvm.Class(Value)
BasicBlock = llvm.Class(Value)
ValueSymbolTable = llvm.Class()
Constant = llvm.Class(User)
GlobalValue = llvm.Class(Constant)
Function = llvm.Class(GlobalValue)
UndefValue = llvm.Class(Constant)
ConstantInt = llvm.Class(Constant)
ConstantFP = llvm.Class(Constant)
ConstantArray = llvm.Class(Constant)
ConstantStruct = llvm.Class(Constant)
ConstantVector = llvm.Class(Constant)
ConstantDataSequential = llvm.Class(Constant)
ConstantDataArray = llvm.Class(ConstantDataSequential)
ConstantExpr = llvm.Class(Constant)

from .Support.raw_ostream import raw_ostream
from .Assembly.AssemblyAnnotationWriter import AssemblyAnnotationWriter
from .Type import Type
from .LLVMContext import LLVMContext
from .ADT.StringRef import StringRef


@Value
class Value:

    ValueTy = Enum('''
        ArgumentVal, BasicBlockVal, FunctionVal, GlobalAliasVal,
        GlobalVariableVal, UndefValueVal, BlockAddressVal, ConstantExprVal,
        ConstantAggregateZeroVal, ConstantDataArrayVal, ConstantDataVectorVal,
        ConstantIntVal, ConstantFPVal, ConstantArrayVal, ConstantStructVal,
        ConstantVectorVal, ConstantPointerNullVal, MDNodeVal, MDStringVal,
        InlineAsmVal, PseudoSourceValueVal, FixedStackPseudoSourceValueVal,
        InstructionVal, ConstantFirstVal, ConstantLastVal
        ''')

    dump = Method()

    print_ = Method(Void, ref(raw_ostream), ptr(AssemblyAnnotationWriter))
    print_.realname = 'print'

    getType = Method(ptr(Type))
    getContext = Method(ref(LLVMContext))

    hasName = Method(cast(Bool, bool))
    # skip getValueName, setValueName
    getName = Method(cast(StringRef, str))
    setName = Method(Void, cast(str, StringRef))

    replaceAllUsesWith = Method(Void, ptr(Value))

    list_use = CustomMethod('Value_use_iterator_to_list', PyObjectPtr)

    hasOneUse = Method(cast(Bool, bool))
    hasNUses = Method(cast(Bool, bool), cast(int, Unsigned))
    isUsedInBasicBlock = Method(cast(Bool, bool), BasicBlock)
    getNumUses = Method(cast(Unsigned, int))

    @CustomPythonMethod
    def __str__(self):
        from llvmpy import extra
        os = extra.make_raw_ostream_for_printing()
        self.print_(os, None)
        return os.str()

    getValueID = Method(cast(Unsigned, int))

    mutateType = Method(Void, ptr(Type))

########NEW FILE########
__FILENAME__ = ValueSymbolTable
from binding import *
from .Value import ValueSymbolTable, Value
from .ADT.StringRef import StringRef

@ValueSymbolTable
class ValueSymbolTable:
    if LLVM_VERSION >= (3, 3):
        _include_ = 'llvm/IR/ValueSymbolTable.h'
    else:
        _include_ = 'llvm/ValueSymbolTable.h'
    new = Constructor()
    delete = Destructor()
    lookup = Method(ptr(Value), cast(str, StringRef))
    empty = Method(cast(Bool, bool))
    size = Method(cast(Unsigned, int))
    dump = Method(Void)


########NEW FILE########
__FILENAME__ = test_binding
from io import BytesIO, StringIO

from llvmpy.api import llvm
from llvmpy import extra
from llvmpy import _capsule
import llvmpy.capsule
import collections
llvmpy.capsule.set_debug(True)


llvm.InitializeNativeTarget()
llvm.InitializeNativeTargetAsmPrinter()

def test_basic_jit_use():
    context = llvm.getGlobalContext()

    m = llvm.Module.new("modname", context)
    print(m.getModuleIdentifier())
    m.setModuleIdentifier('modname2')
    print(m.getModuleIdentifier())
    print('endianness', m.getEndianness())
    assert m.getEndianness() == llvm.Module.Endianness.AnyEndianness
    print('pointer-size', m.getPointerSize())
    assert m.getPointerSize() == llvm.Module.PointerSize.AnyPointerSize
    m.dump()


    os = extra.make_raw_ostream_for_printing()
    m.print_(os, None)
    print(os.str())


    int1ty = llvm.Type.getInt1Ty(context)
    int1ty.dump()

    assert int1ty.isIntegerTy(1)

    fnty = llvm.FunctionType.get(int1ty, False)
    fnty.dump()

    types = [llvm.Type.getIntNTy(context, 8), llvm.Type.getIntNTy(context, 32)]
    fnty = llvm.FunctionType.get(llvm.Type.getIntNTy(context, 8), types, False)

    print(fnty)

    const = m.getOrInsertFunction("foo", fnty)
    fn = const._downcast(llvm.Function)
    print(fn)
    assert fn.hasName()
    assert 'foo' == fn.getName()
    fn.setName('bar')
    assert 'bar' == fn.getName()

    assert fn.getReturnType().isIntegerTy(8)

    assert fnty is fn.getFunctionType()

    assert fn.isVarArg() == False
    assert fn.getIntrinsicID() == 0
    assert not fn.isIntrinsic()

    fn_uselist = fn.list_use()
    assert isinstance(fn_uselist, list)
    assert len(fn_uselist) == 0

    builder = llvm.IRBuilder.new(context)
    print(builder)

    bb = llvm.BasicBlock.Create(context, "entry", fn, None)
    assert bb.empty()
    builder.SetInsertPoint(bb)

    assert bb.getTerminator() is None

    arg0, arg1 = fn.getArgumentList()
    print(arg0, arg1)

    extended = builder.CreateZExt(arg0, arg1.getType())
    result = builder.CreateAdd(extended, arg1)
    ret = builder.CreateTrunc(result, fn.getReturnType())
    builder.CreateRet(ret)

    print(arg0.list_use())

    print(fn)

    errio = StringIO()
    print(m)

    # verifier
    action = llvm.VerifierFailureAction.ReturnStatusAction

    corrupted = llvm.verifyFunction(fn, action)
    assert not corrupted
    corrupted = llvm.verifyModule(m, action, errio)
    print(corrupted)
    assert not corrupted, errio.getvalue()

    # build pass manager
    pmb = llvm.PassManagerBuilder.new()
    pmb.OptLevel = 3
    assert pmb.OptLevel == 3
    pmb.LibraryInfo = llvm.TargetLibraryInfo.new()
    pmb.Inliner = llvm.createFunctionInliningPass()

    fpm = llvm.FunctionPassManager.new(m)
    pm = llvm.PassManager.new()

    pmb.populateFunctionPassManager(fpm)
    pmb.populateModulePassManager(pm)

    fpm.doInitialization()
    fpm.run(fn)
    fpm.doFinalization()

    pm.run(m)

    print(m)

    # build engine

    ee = llvm.ExecutionEngine.createJIT(m, errio)
    print(ee, errio.getvalue())
    print(ee.getDataLayout().getStringRepresentation())

    datalayout_str = 'e-p:64:64:64-S128-i1:8:8-i8:8:8-i16:16:16-i32:32:32-i64:64:64-f16:16:16-f32:32:32-f64:64:64-f128:128:128-v64:64:64-v128:128:128-a0:0:64-s0:64:64-f80:128:128-n8:16:32:64'

    assert datalayout_str == str(llvm.DataLayout.new(datalayout_str))
    assert datalayout_str == str(llvm.DataLayout.new(str(llvm.DataLayout.new(datalayout_str))))

    fn2 = ee.FindFunctionNamed(fn.getName())
    assert fn2 is fn

    assert ee.getPointerToFunction(fn)
    assert ee.getPointerToNamedFunction('printf')

    gv0 = llvm.GenericValue.CreateInt(arg0.getType(), 12, False)
    gv1 = llvm.GenericValue.CreateInt(arg1.getType(), -32, True)

    assert gv0.valueIntWidth() == arg0.getType().getIntegerBitWidth()
    assert gv1.valueIntWidth() == arg1.getType().getIntegerBitWidth()

    assert gv0.toUnsignedInt() == 12
    assert gv1.toSignedInt() == -32

    gv1 = llvm.GenericValue.CreateInt(arg1.getType(), 32, False)

    gvR = ee.runFunction(fn, (gv0, gv1))

    assert 44 == gvR.toUnsignedInt()

    # write bitcode
    bc_buffer = BytesIO()
    llvm.WriteBitcodeToFile(m, bc_buffer)
    bc = bc_buffer.getvalue()
    bc_buffer.close()

    # read bitcode
    errbuf = BytesIO()
    m2 = llvm.ParseBitCodeFile(bc, context, errbuf)
    if not m2:
        raise Exception(errbuf.getvalue())
    else:
        m2.setModuleIdentifier(m.getModuleIdentifier())
        assert str(m2) == str(m)

    # parse llvm ir
    m3 = llvm.ParseAssemblyString(str(m), None, llvm.SMDiagnostic.new(), context)
    m3.setModuleIdentifier(m.getModuleIdentifier())
    assert str(m3) == str(m)

    # test clone
    m4 = llvm.CloneModule(m)
    assert m4 is not m
    assert str(m4) == str(m)

def test_engine_builder():
    llvm.InitializeNativeTarget()
    context = llvm.getGlobalContext()

    m = llvm.Module.new("modname", context)

    int32ty = llvm.Type.getIntNTy(context, 32)
    fnty = llvm.FunctionType.get(int32ty, [int32ty], False)
    fn = m.getOrInsertFunction("foo", fnty)._downcast(llvm.Function)
    bb = llvm.BasicBlock.Create(context, "entry", fn, None)
    builder = llvm.IRBuilder.new(context)
    builder.SetInsertPoint(bb)
    builder.CreateRet(fn.getArgumentList()[0])

    print(fn)

    eb = llvm.EngineBuilder.new(m)
    eb2 = eb.setEngineKind(llvm.EngineKind.Kind.JIT)
    assert eb is eb2
    eb.setOptLevel(llvm.CodeGenOpt.Level.Aggressive).setUseMCJIT(False)

    tm = eb.selectTarget()

    print('target triple:', tm.getTargetTriple())
    print('target cpu:', tm.getTargetCPU())
    print('target feature string:', tm.getTargetFeatureString())

    target = tm.getTarget()
    print('target name:', target.getName())
    print('target short description:', target.getShortDescription())

    assert target.hasJIT()
    assert target.hasTargetMachine()

    ee = eb.create(tm)

    triple = llvm.Triple.new('x86_64-unknown-linux')
    assert triple.getArchName() == 'x86_64'
    assert triple.getVendorName() == 'unknown'
    assert triple.getOSName() == 'linux'
    assert triple.isArch64Bit()
    assert not triple.isArch32Bit()
    triple_32variant = triple.get32BitArchVariant()
    assert triple_32variant.isArch32Bit()

    print(tm.getDataLayout())

    pm = llvm.PassManager.new()
    pm.add(llvm.DataLayout.new(str(tm.getDataLayout())))
    pm.add(llvm.TargetLibraryInfo.new())

    # write assembly
    pm = llvm.PassManager.new()
    pm.add(llvm.DataLayout.new(str(tm.getDataLayout())))

    raw = extra.make_raw_ostream_for_printing()
    formatted = llvm.formatted_raw_ostream.new(raw, False)

    cgft = llvm.TargetMachine.CodeGenFileType.CGFT_AssemblyFile
    failed = tm.addPassesToEmitFile(pm, formatted, cgft, False)
    assert not failed

    pm.run(m)

    formatted.flush()
    raw.flush()
    asm = raw.str()
    print(asm)
    assert 'foo' in asm


def test_linker():
    context = llvm.getGlobalContext()

    mA = llvm.Module.new("modA", context)
    mB = llvm.Module.new("modB", context)

    def create_function(m, name):
        int32ty = llvm.Type.getIntNTy(context, 32)
        fnty = llvm.FunctionType.get(int32ty, [int32ty], False)
        fn = m.getOrInsertFunction(name, fnty)._downcast(llvm.Function)
        bb = llvm.BasicBlock.Create(context, "entry", fn, None)
        builder = llvm.IRBuilder.new(context)
        builder.SetInsertPoint(bb)
        builder.CreateRet(fn.getArgumentList()[0])

    create_function(mA, 'foo')
    create_function(mB, 'bar')

    errmsg = StringIO()
    linkermode = llvm.Linker.LinkerMode.PreserveSource
    failed = llvm.Linker.LinkModules(mA, mB, linkermode, errmsg)
    assert not failed, errmsg.getvalue()
    assert mA.getFunction('foo')
    assert mA.getFunction('bar')

    assert set(mA.list_functions()) == set([mA.getFunction('foo'),
                                            mA.getFunction('bar')])

def test_structtype():
    context = llvm.getGlobalContext()
    m = llvm.Module.new("modname", context)

    assert m.getTypeByName("truck") is None

    truck = llvm.StructType.create(context, "truck")
    assert 'type opaque' in str(truck)
    elemtys = [llvm.Type.getInt32Ty(context), llvm.Type.getDoubleTy(context)]
    truck.setBody(elemtys)

    assert 'i32' in str(truck)
    assert 'double' in str(truck)

    assert m.getTypeByName("truck") is truck

def test_globalvariable():
    context = llvm.getGlobalContext()
    m = llvm.Module.new("modname", context)

    ty = llvm.Type.getInt32Ty(context)
    LinkageTypes = llvm.GlobalVariable.LinkageTypes
    linkage = LinkageTypes.ExternalLinkage
    gvar = llvm.GlobalVariable.new(m, ty, False, linkage, None, "apple")
    assert '@apple = external global i32' in str(m)

    gvar2 = m.getNamedGlobal('apple')
    assert gvar2 is gvar

    print(m.list_globals())


def test_sequentialtypes():
    context = llvm.getGlobalContext()
    int32ty = llvm.Type.getInt32Ty(context)
    ary_int32x4 = llvm.ArrayType.get(int32ty, 4)
    assert '[4 x i32]' == str(ary_int32x4)
    ptr_int32 = llvm.PointerType.get(int32ty, 1)
    assert 'i32 addrspace(1)*' == str(ptr_int32)
    vec_int32x4 = llvm.VectorType.get(int32ty, 4)
    assert '<4 x i32>' == str(vec_int32x4)


def test_constants():
    context = llvm.getGlobalContext()
    int32ty = llvm.Type.getInt32Ty(context)
    ary_int32x4 = llvm.ArrayType.get(int32ty, 4)
    intconst = llvm.ConstantInt.get(int32ty, 123)
    aryconst = llvm.ConstantArray.get(ary_int32x4, [intconst] * 4)
    assert str(aryconst.getAggregateElement(0)) == str(intconst)

    bignum = 4415104608
    int64ty = llvm.Type.getInt64Ty(context)
    const_bignum = llvm.ConstantInt.get(int64ty, 4415104608)
    assert str(bignum) in str(const_bignum)

def test_intrinsic():
    context = llvm.getGlobalContext()
    m = llvm.Module.new("modname", context)
    INTR_SIN = 1652
    floatty = llvm.Type.getFloatTy(context)
    fn = llvm.Intrinsic.getDeclaration(m, INTR_SIN, [floatty])
    assert 'llvm.sin.f32' in str(fn)
    fn.eraseFromParent()
    assert 'llvm.sin.f32' not in str(m)

def test_passregistry():
    passreg = llvm.PassRegistry.getPassRegistry()

    llvm.initializeScalarOpts(passreg)

    passinfo = passreg.getPassInfo("dce")
    dcepass = passinfo.createPass()
    print(dcepass.getPassName())

    print(passreg.enumerate())

def test_targetregistry():
    llvm.TargetRegistry.printRegisteredTargetsForVersion()
    errmsg = StringIO()

    target = llvm.TargetRegistry.getClosestTargetForJIT(errmsg)
    errmsg.close()

    print(target.getName())
    print(target.getShortDescription())
    assert target.hasJIT()
    assert target.hasTargetMachine()

    next = target.getNext()
    if next:
        print(next.getName())
        print(next.getShortDescription())

    triple = llvm.sys.getDefaultTargetTriple()
    cpu = llvm.sys.getHostCPUName()
    features = {}
    assert not llvm.sys.getHostCPUFeatures(features), "Only for Linux and ARM?"

    targetoptions = llvm.TargetOptions.new()
    tm = target.createTargetMachine(triple, cpu, "", targetoptions)

def main():
    for name, value in list(globals().items()):
        if name.startswith('test_') and isinstance(value, collections.Callable):
            print(name.center(80, '-'))
            value()


if __name__ == '__main__':
    main()


########NEW FILE########
__FILENAME__ = array
# This should be moved to llvmpy
#
# There are different array kinds parameterized by eltype and nd
#
# Contiguous or Fortran
# struct {
#    eltype *data;
#    intp shape[nd];
# } contiguous_array(eltype, nd)
#
# struct {
#    eltype *data;
#    diminfo shape[nd];
# } strided_array(eltype, nd)
#
# struct {
#    eltype *data;
#    intp shape[nd];
#    intp stride[nd];
# } strided_soa_array(eltype, nd)
#
# struct {
#   intp dim;
#   intp stride;
#} diminfo
#
# These are for low-level array-routines that need to know the number
# of dimensions at run-time (not just code-generation time):
#
# The first two are recommended
#
# struct {
#   eltype *data;
#   int32 nd;
#   intp shape[nd];
# } contiguous_array_nd(eltype)
#
# struct {
#    eltype *data;
#    int32 nd;
#    diminfo shape[nd];
# } strided_array_nd(eltype)
#
#
# Backward compatible but deprecated:
# struct {
#    eltype *data;
#    int32 nd;
#    intp shape[nd];
#    intp stride[nd];
# } strided_soa_array_nd(eltype)
#
#
# The most general (where the kind of array is stored as well as number
#                   of dimensions)
# Rarely needed.
#
# struct {
#   eltype *data;
#   int16 nd;
#   int16 dimkind;
#   ???
# } array_nd(eltype)
#
# where ??? is run-time interpreted based on the dimkind to either:
# intp shape[nd];  for dimkind = C_CONTIGUOUS or F_CONTIGUOUS
#
# diminfo shape[nd]; for dimkind = STRIDED
#
# intp shape[ind];
# intp strides[ind]; dimkind = STRIDED_SOA
#

import llvm.core as lc
from llvm.core import Type
import llvm_cbuilder.shortnames as C

# Different Array Types
ARRAYBIT = 1<<4
C_CONTIGUOUS = ARRAYBIT + 0
F_CONTIGUOUS = ARRAYBIT + 1
STRIDED = ARRAYBIT + 2
STRIDED_SOA = ARRAYBIT + 3

HAS_ND = 1<<5
C_CONTIGUOUS_ND = C_CONTIGUOUS + HAS_ND
F_CONTIGUOUS_ND = F_CONTIGUOUS + HAS_ND
STRIDED_ND = STRIDED + HAS_ND
STRIDED_SOA_ND = STRIDED_SOA + HAS_ND

HAS_DIMKIND = 1<<6
C_CONTIGUOUS_DK = C_CONTIGUOUS + HAS_DIMKIND
F_CONTIGUOUS_DK = F_CONTIGUOUS + HAS_DIMKIND
STRIDED_DK = STRIDED + HAS_DIMKIND
STRIDED_SOA_DK = STRIDED_SOA + HAS_DIMKIND

array_kinds = (C_CONTIGUOUS, F_CONTIGUOUS, STRIDED, STRIDED_SOA,
               C_CONTIGUOUS_ND, F_CONTIGUOUS_ND, STRIDED_ND, STRIDED_SOA_DK,
               C_CONTIGUOUS_DK, F_CONTIGUOUS_DK, STRIDED_DK, STRIDED_SOA_DK)

_invmap = {}

def kind_to_str(kind):
    global _invmap
    if not _invmap:
        for key, value in globals().items():
            if isinstance(value, int) and value in array_kinds:
                _invmap[value] = key
    return _invmap[kind]

def str_to_kind(str):
    trial = eval(str)
    if trial not in array_kinds:
        raise ValueError("Invalid Array Kind")
    return trial

void_type = C.void
int32_type = C.int32
char_type = C.char
int16_type = C.int16
intp_type = C.intp

diminfo_type = Type.struct([intp_type,    # shape
                            intp_type     # stride
                            ], name='diminfo')

_cache = {}
# This is the way we define LLVM arrays.
#  CONTIGUOUS and STRIDED are strongly encouraged...
def array_type(nd, kind, el_type=char_type):
    key = (kind, nd, el_type)
    if _cache.has_key(key):
        return _cache[key]

    base = kind & (~(HAS_ND | HAS_DIMKIND))
    if base == C_CONTIGUOUS:
        dimstr = 'Array_C'
    elif base == F_CONTIGUOUS:
        dimstr = 'Array_F'
    elif base == STRIDED:
        dimstr = 'Array_S'
    elif base == STRIDED_SOA:
        dimstr = 'Array_A'
    else:
        raise TypeError("Do not understand Array kind of %d" % kind)

    terms = [Type.pointer(el_type)]        # data

    if (kind & HAS_ND):
        terms.append(int32_type)           # nd
        dimstr += '_ND'
    elif (kind & HAS_DIMKIND):
        terms.extend([int16_type, int16_type]) # nd, dimkind
        dimstr += '_DK'

    if base in [C_CONTIGUOUS, F_CONTIGUOUS]:
        terms.append(Type.array(intp_type, nd))     # shape
    elif base == STRIDED:
        terms.append(Type.array(diminfo_type, nd))       # diminfo
    elif base == STRIDED_SOA:
        terms.extend([Type.array(intp_type, nd),    # shape
                      Type.array(intp_type, nd)])   # strides

    ret = Type.struct(terms, name=dimstr)
    _cache[key] = ret
    return ret


def check_array(arrtyp):
    if not isinstance(arrtyp, lc.StructType):
        return None
    if arrtyp.element_count not in [2, 3, 4, 5]:
        return None

    # Look through _cache and see if it's there
    for key, value in _cache.items():
        if arrtyp is value:
            return key

    return _raw_check_array(arrtyp)

# Manual check
def _raw_check_array(arrtyp):
    a0 = arrtyp.elements[0]
    a1 = arrtyp.elements[1]
    if not isinstance(a0, lc.PointerType) or \
          not (isinstance(a1, lc.ArrayType) or
               (a1 == int32_type) or (a1 == int16_type)):
        return None

    data_type = a0.pointee

    if arrtyp.is_literal:
        c_contig = True
    else:
        if arrtyp.name.startswith('Array_F'):
            c_contig = False
        else:
            c_contig = True


    if a1 == int32_type:
        num = 2
        strided = STRIDED_ND
        strided_soa = STRIDED_SOA_ND
        c_contiguous = C_CONTIGUOUS_ND
        f_contiguous = F_CONTIGUOUS_ND
    elif a1 == int16_type:
        if arrtyp.element_count < 3 or arrtyp.elements[2] != int16_type:
            return None
        num = 3
        strided = STRIDED_DK
        strided_soa = STRIDED_SOA_DK
        c_contiguous = C_CONTIGUOUS_DK
        f_contiguous = F_CONTIGUOUS_DK
    else:
        num = 1
        strided = STRIDED
        strided_soa = STRIDED_SOA
        c_contiguous = C_CONTIGUOUS
        f_contiguous = F_CONTIGUOUS

    elcount = num + 2
    # otherwise we have lc.ArrType as element [1]
    if arrtyp.element_count not in [num+1,num+2]:
        return None
    s1 = arrtyp.elements[num]
    nd = s1.count

    if arrtyp.element_count == elcount:
        if not isinstance(arrtyp.elements[num+1], lc.ArrayType):
            return None
        s2 = arrtyp.elements[num+1]
        if s1.element != intp_type or s2.element != intp_type:
            return None
        if s1.count != s2.count:
            return None
        return strided_soa, nd, data_type

    if s1.element == diminfo_type:
        return strided, nd, data_type
    elif s1.element == intp_type:
        return c_contiguous if c_contig else f_contiguous, nd, data_type
    else:
        return None


def test():
    arr = array_type(5, C_CONTIGUOUS)
    assert check_array(arr) == (C_CONTIGUOUS, 5, char_type)
    arr = array_type(4, STRIDED)
    assert check_array(arr) == (STRIDED, 4, char_type)
    arr = array_type(3, STRIDED_SOA)
    assert check_array(arr) == (STRIDED_SOA, 3, char_type)

if __name__ == '__main__':
    test()

########NEW FILE########
__FILENAME__ = builder
#
# TODO: Add support for vector.
#

import contextlib
import llvm.core as lc
import llvm.ee as le
import llvm.passes as lp
from llvm import LLVMException
from . import shortnames as types

###
#  Utilities
###

class FunctionAlreadyExists(NameError):

    def __init__(self, func):
        self.func = func

def _is_int(ty):
    return isinstance(ty, lc.IntegerType)

def _is_real(ty):
    tys = [ lc.Type.float(),
            lc.Type.double(),
            lc.Type.x86_fp80(),
            lc.Type.fp128(),
            lc.Type.ppc_fp128() ]
    return any(ty == x for x in tys)

def _is_vector(ty, of=None):
    if isinstance(ty, lc.VectorType):
        if of is not None:
            return of(ty.element)
        return True
    else:
        return False

def _is_pointer(ty):
    return isinstance(ty, lc.PointerType)

def _is_block_terminated(bb):
    instrs = bb.instructions
    return len(instrs) > 0 and instrs[-1].is_terminator

def _is_struct(ty):
    return isinstance(ty, lc.StructType)

def _is_cstruct(ty):
    try:
        return issubclass(ty, CStruct)
    except TypeError:
        return False

def _list_values(iterable):
    return [i.value for i in iterable]

def _auto_coerce_index(cbldr, idx):
    if not isinstance(idx, CValue):
        idx = cbldr.constant(types.int, idx)
    return idx

@contextlib.contextmanager
def _change_block_temporarily(builder, bb):
    origbb = builder.basic_block
    builder.position_at_end(bb)
    yield
    builder.position_at_end(origbb)

@contextlib.contextmanager
def _change_block_temporarily_dummy(*args):
    yield

class CastError(TypeError):
    def __init__(self, orig, to):
        super(CastError, self).__init__("Cannot cast from %s to %s" % (orig, to))

class _IfElse(object):
    '''if-else construct.

    Example
    -------
    with cbuilder.ifelse(cond) as ifelse:
        with ifelse.then():
            # code when cond is true
            # this block is mandatory
        with ifelse.otherwise():
            # code when cond is false
            # this block is optional
    '''

    def __init__(self, parent, cond):
        self.parent = parent
        self.cond = cond
        self._to_close = []

    @contextlib.contextmanager
    def then(self):
        self._bbif = self.parent.function.append_basic_block('if.then')
        self._bbelse = self.parent.function.append_basic_block('if.else')

        builder = self.parent.builder
        builder.cbranch(self.cond.value, self._bbif, self._bbelse)

        builder.position_at_end(self._bbif)

        yield

        self._to_close.extend([self._bbif, self._bbelse, builder.basic_block])

    @contextlib.contextmanager
    def otherwise(self):
        builder = self.parent.builder
        builder.position_at_end(self._bbelse)
        yield
        self._to_close.append(builder.basic_block)

    def close(self):
        self._to_close.append(self.parent.builder.basic_block)
        bbend = self.parent.function.append_basic_block('if.end')
        builder = self.parent.builder
        closed_count = 0
        for bb in self._to_close:
            if not _is_block_terminated(bb):
                with _change_block_temporarily(builder, bb):
                    builder.branch(bbend)
                    closed_count += 1
        builder.position_at_end(bbend)
        if not closed_count:
            self.parent.unreachable()

class _Loop(object):
    '''while...do loop.

    Example
    -------
    with cbuilder.loop() as loop:
        with loop.condition() as setcond:
            # Put the condition evaluation here
            setcond( cond )         # set loop condition
            # Do not put code after setcond(...)
        with loop.body():
            # Put the code of the loop body here

    Use loop.break_loop() to break out of the loop.
    Use loop.continue_loop() to jump the condition evaulation.
    '''

    def __init__(self, parent):
        self.parent = parent

    @contextlib.contextmanager
    def condition(self):
        builder = self.parent.builder
        self._bbcond = self.parent.function.append_basic_block('loop.cond')
        self._bbbody = self.parent.function.append_basic_block('loop.body')
        self._bbend = self.parent.function.append_basic_block('loop.end')

        builder.branch(self._bbcond)

        builder.position_at_end(self._bbcond)

        def setcond(cond):
            builder.cbranch(cond.value, self._bbbody, self._bbend)

        yield setcond

    @contextlib.contextmanager
    def body(self):
        builder = self.parent.builder
        builder.position_at_end(self._bbbody)
        yield self
        # close last block
        if not _is_block_terminated(builder.basic_block):
            builder.branch(self._bbcond)

    def break_loop(self):
        self.parent.builder.branch(self._bbend)

    def continue_loop(self):
        self.parent.builder.branch(self._bbcond)

    def close(self):
        builder = self.parent.builder
        builder.position_at_end(self._bbend)

class CBuilder(object):
    '''
    A wrapper class for features in llvm-py package
    to allow user to use C-like high-level language contruct easily.
    '''

    def __init__(self, function):
        '''constructor

        function : is an empty function to be populating.
        '''
        self.function = function
        self.declare_block = self.function.append_basic_block('decl')
        self.first_body_block = self.function.append_basic_block('body')
        self.builder = lc.Builder.new(self.first_body_block)
        self.target_data = le.TargetData.new(self.function.module.data_layout)
        self._auto_inline_list = []
        # Prepare arguments. Make all function arguments behave like variables.
        self.args = []
        for arg in function.args:
            var = self.var(arg.type, arg, name=arg.name)
            self.args.append(var)

    @staticmethod
    def new_function(mod, name, ret, args):
        '''factory method

        Create a new function in the module and return a CBuilder instance.
        '''
        functype = lc.Type.function(ret, args)
        func = mod.add_function(functype, name=name)
        return CBuilder(func)

    def depends(self, fndecl):
        '''add function dependency

        Returns a CFunc instance and define the function if it is not defined.

        fndecl : is a callable that takes a `llvm.core.Module` and returns
                 a function pointer.
        '''
        return CFunc(self, fndecl(self.function.module))

    def printf(self, fmt, *args):
        '''printf() from libc

        fmt : a character string holding printf format string.
        *args : additional variable arguments.
        '''
        from .libc import LibC
        libc = LibC(self)
        ret = libc.printf(fmt, *args)
        return CTemp(self, ret)

    def debug(self, *args):
        '''debug print

        Use printf to dump the values of all arguments.
        '''
        type_mapper = {
            'i8' : '%c',
            'i16': '%hd',
            'i32': '%d',
            'i64': '%ld',
            'double': '%e',
        }
        itemsfmt = []
        items = []
        for i in args:
            if isinstance(i, str):
                itemsfmt.append(i.replace('%', '%%'))
            elif isinstance(i.type, lc.PointerType):
                itemsfmt.append("%p")
                items.append(i)
            else:
                tyname = str(i.type)
                if tyname == 'float':
                    # auto convert float to double
                    ty = '%e'
                    i = i.cast(types.double)
                else:
                    ty = type_mapper[tyname]
                itemsfmt.append(ty)
                items.append(i)
        fmt = ' '.join(itemsfmt) + '\n'
        return self.printf(self.constant_string(fmt), *items)

    def sizeof(self, ty):
        bldr = self.builder
        ptrty = types.pointer(ty)
        first = lc.Constant.null(ptrty)
        second = bldr.gep(first, [lc.Constant.int(types.intp, 1)])

        firstint = bldr.ptrtoint(first, types.intp)
        secondint = bldr.ptrtoint(second, types.intp)
        diff = bldr.sub(secondint, firstint)
        return CTemp(self, diff)

    def min(self, x, y):
        z = self.var(x.type)
        with self.ifelse( x < y ) as ifelse:
            with ifelse.then():
                z.assign(x)
            with ifelse.otherwise():
                z.assign(y)
        return z

    def var(self, ty, value=None, name=''):
        '''allocate variable on the stack

        ty : variable type
        value : [optional] initializer value
        name : [optional] name used in LLVM IR
        '''
        with _change_block_temporarily(self.builder, self.declare_block):
            # goto the first block
            is_cstruct = _is_cstruct(ty)
            if is_cstruct:
                cstruct = ty
                ty = ty.llvm_type()
            ptr = self.builder.alloca(ty, name=name)
        # back to the body
        if value is not None:
            if isinstance(value, CValue):
                value = value.value
            elif not isinstance(value, lc.Value):
                value = self.constant(ty, value).value
            self.builder.store(value, ptr)
        if is_cstruct:
            return cstruct(self, ptr)
        else:
            return CVar(self, ptr)

    def var_copy(self, val, name=''):
        '''allocate a new variable by copying another value

        The new variable has the same type and value of `val`.
        '''
        return self.var(val.type, val, name=name)

    def array(self, ty, count, name=''):
        '''allocate an array on the stack

        ty : array element type
        count : array size; can be python int, llvm.core.Constant, or CValue
        name : [optional] name used in LLVM IR
        '''
        if isinstance(count, int) or isinstance(count, lc.Constant):
            # Only go to the first block if array size is fixed.
            contexthelper = _change_block_temporarily
        else:
            # Do not go to the first block if the array size is dynamic.
            contexthelper = _change_block_temporarily_dummy

        with contexthelper(self.builder, self.declare_block):
            if _is_cstruct(ty): # array of struct?
                cstruct = ty
                ty = ty.llvm_type()

            if isinstance(count, CValue):
                count = count.value
            elif not isinstance(count, lc.Value):
                count = self.constant(types.int, count).value

            ptr = self.builder.alloca(ty, size=count, name=name)
            return CArray(self, ptr)

    def ret(self, val=None):
        '''insert return statement

        val : if is `None`, insert return-void
              else, return `val`
        '''
        retty = self.function.type.pointee.return_type
        if val is not None:
            if val.type != retty:
                errmsg = "Return type mismatch"
                raise TypeError(errmsg)
            self.builder.ret(val.value)
        else:
            if retty != types.void:
                # errmsg = "Cannot return void"
                # raise TypeError(errmsg, retty)
                bb = self.function.append_basic_block('unreachable_bb')
                self.builder.position_at_end(bb)
                self.builder.ret(self.builder.alloca(retty, name='undef'))
            else:
                self.builder.ret_void()

    @contextlib.contextmanager
    def ifelse(self, cond):
        '''start a if-else block

        cond : branch condition
        '''
        cb = _IfElse(self, cond)
        yield cb
        cb.close()

    @contextlib.contextmanager
    def loop(self):
        '''start a loop block
        '''
        cb = _Loop(self)
        yield cb
        cb.close()

    @contextlib.contextmanager
    def forever(self):
        '''start a forever loop block
        '''
        with self.loop() as loop:
            with loop.condition() as setcond:
                NULL = self.constant_null(types.int)
                setcond( NULL == NULL )
            with loop.body():
                yield loop

    @contextlib.contextmanager
    def for_range(self, *args):
        '''start a for-range block.

        *args : same as arguments of builtin `range()`
        '''
        def check_arg(x):
            if isinstance(x, int):
                return self.constant(types.int, x)
            if not isinstance(x, IntegerValue):
                raise TypeError(x, "All args must be of integer type.")
            return x

        if len(args) == 3:
            start, stop, step = map(check_arg, args)
        elif len(args) == 2:
            start, stop = map(check_arg, args)
            step = self.constant(start.type, 1)
        elif len(args) == 1:
            stop = check_arg(args[0])
            start = self.constant(stop.type, 0)
            step = self.constant(stop.type, 1)
        else:
            raise TypeError("Invalid # of arguments: 1, 2 or 3")

        idx = self.var_copy(start)
        with self.loop() as loop:
            with loop.condition() as setcond:
                setcond( idx < stop )
            with loop.body():
                yield loop, idx
                idx += step

    def position_at_end(self, bb):
        '''reposition inserter to the end of basic-block

        bb : a basic block
        '''
        self.basic_block = bb
        self.builder.position_at_end(bb)

    def close(self):
        '''end code generation
        '''
        # Close declaration block
        with _change_block_temporarily(self.builder, self.declare_block):
            self.builder.branch(self.first_body_block)

        # Do the auto inlining
        for callinst in self._auto_inline_list:
            lc.inline_function(callinst)

    def constant(self, ty, val):
        '''create a constant

        ty : data type
        val : initializer
        '''
        if isinstance(ty, lc.IntegerType):
            res = lc.Constant.int(ty, val)
        elif ty == types.float or ty == types.double:
            res = lc.Constant.real(ty, val)
        else:
            raise TypeError("Cannot auto build constant "
                            "from %s and value %s" % (ty, val))
        return CTemp(self, res)

    def constant_null(self, ty):
        '''create a zero filled constant

        ty : data type
        '''
        res = lc.Constant.null(ty)
        return CTemp(self, res)

    def constant_string(self, string):
        '''create a constant string

        This will de-duplication string of same content to minimize memory use.
        '''
        mod = self.function.module
        collision = 0
        name_fmt = '.conststr.%x.%x'
        content = lc.Constant.stringz(string)
        while True:
            name = name_fmt % (hash(string), collision)
            try:
                # check if the name already exists
                globalstr = mod.get_global_variable_named(name)
            except LLVMException:
                # new constant string
                globalstr = mod.add_global_variable(content.type, name=name)
                globalstr.initializer = content
                globalstr.linkage = lc.LINKAGE_LINKONCE_ODR
                globalstr.global_constant = True
            else:
                # compare existing content
                existed = str(globalstr.initializer)
                if existed != str(content):
                    collision += 1
                    continue # loop until we resolve the name collision

            return CTemp(self, globalstr.bitcast(
                                           types.pointer(content.type.element)))


    def get_intrinsic(self, intrinsic_id, tys):
        '''get intrinsic function

        intrinsic_id : numerical ID of target intrinsic
        tys : type argument for the intrinsic
        '''
        lfunc = lc.Function.intrinsic(self.function.module, intrinsic_id, tys)
        return CFunc(self, lfunc)

    def get_function_named(self, name):
        '''get function by name
        '''
        m = self.function.module
        func = m.get_function_named(name)
        return CFunc(self, func)

    def is_terminated(self):
        '''is the current basic-block terminated?
        '''
        return _is_block_terminated(self.builder.basic_block)

    def atomic_cmpxchg(self, ptr, old, val, ordering, crossthread=True):
        '''atomic compare-exchange

        ptr : pointer to data
        old : old value to compare to
        val : new value
        ordering : memory ordering as a string
        crossthread : set to `False` for single-thread code

        Returns the old value on success.
        '''
        res = self.builder.atomic_cmpxchg(ptr.value, old.value, val.value,
                                          ordering, crossthread)
        return CTemp(self, res)

    def atomic_xchg(self, ptr, val, ordering, crossthread=True):
        '''atomic exchange

        ptr : pointer to data
        val : new value
        ordering : memory ordering as a string
        crossthread : set to `False` for single-thread code

        Returns the old value
        '''

        res = self.builder.atomic_xchg(ptr.value, val.value,
                                       ordering, crossthread)
        return CTemp(self, res)

    def atomic_add(self, ptr, val, ordering, crossthread=True):
        '''atomic add

        ptr : pointer to data
        val : new value
        ordering : memory ordering as a string
        crossthread : set to `False` for single-thread code

        Returns the computation result of the operation
        '''

        res = self.builder.atomic_add(ptr.value, val.value,
                                      ordering, crossthread)
        return CTemp(self, res)

    def atomic_sub(self, ptr, val, ordering, crossthread=True):
        '''atomic sub

        See `atomic_add` for parameters documentation
        '''
        res = self.builder.atomic_sub(ptr.value, val.value,
                                      ordering, crossthread)
        return CTemp(self, res)

    def atomic_and(self, ptr, val, ordering, crossthread=True):
        '''atomic bitwise and

        See `atomic_add` for parameters documentation
        '''
        res = self.builder.atomic_and(ptr.value, val.value,
                                      ordering, crossthread)
        return CTemp(self, res)

    def atomic_nand(self, ptr, val, ordering, crossthread=True):
        '''atomic bitwise nand

        See `atomic_add` for parameters documentation
        '''
        res = self.builder.atomic_nand(ptr.value, val.value,
                                       ordering, crossthread)
        return CTemp(self, res)

    def atomic_or(self, ptr, val, ordering, crossthread=True):
        '''atomic bitwise or

        See `atomic_add` for parameters documentation
        '''
        res = self.builder.atomic_or(ptr.value, val.value,
                                     ordering, crossthread)
        return CTemp(self, res)

    def atomic_xor(self, ptr, val, ordering, crossthread=True):
        '''atomic bitwise xor

        See `atomic_add` for parameters documentation
        '''

        res = self.builder.atomic_xor(ptr.value, val.value,
                                      ordering, crossthread)
        return CTemp(self, res)

    def atomic_max(self, ptr, val, ordering, crossthread=True):
        '''atomic signed maximum between value at `ptr` and `val`

        See `atomic_add` for parameters documentation
        '''
        res = self.builder.atomic_max(ptr.value, val.value,
                                      ordering, crossthread)
        return CTemp(self, res)

    def atomic_min(self, ptr, val, ordering, crossthread=True):
        '''atomic signed minimum between value at `ptr` and `val`

        See `atomic_add` for parameters documentation
        '''
        res = self.builder.atomic_min(ptr.value, val.value,
                                      ordering, crossthread)
        return CTemp(self, res)

    def atomic_umax(self, ptr, val, ordering, crossthread=True):
        '''atomic unsigned maximum between value at `ptr` and `val`

        See `atomic_add` for parameters documentation
        '''
        res = self.builder.atomic_umax(ptr.value, val.value,
                                       ordering, crossthread)
        return CTemp(self, res)

    def atomic_umin(self, ptr, val, ordering, crossthread=True):
        '''atomic unsigned minimum between value at `ptr` and `val`

        See `atomic_add` for parameters documentation
        '''
        res = self.builder.atomic_umin(ptr.value, val.value,
                                       ordering, crossthread)
        return CTemp(self, res)

    def atomic_load(self, ptr, ordering, align=1, crossthread=True):
        '''atomic load

        ptr : pointer to the value to load
        align : memory alignment in bytes
        See `atomic_add` for other documentation of other parameters
        '''
        res = self.builder.atomic_load(ptr.value, ordering, align, crossthread)
        return CTemp(self, res)

    def atomic_store(self, val, ptr, ordering, align=1, crossthread=True):
        '''atomic store

        ptr : pointer to where to store
        val : value to store
        align : memory alignment in bytes
        See `atomic_add` for other documentation of other parameters
        '''

        res = self.builder.atomic_store(val.value, ptr.value, ordering,
                                        align, crossthread)
        return CTemp(self, res)

    def fence(self, ordering, crossthread=True):
        '''insert memory fence
        '''
        res = self.builder.fence(ordering, crossthread)
        return CTemp(self, res)

    def alignment(self, ty):
        '''get minimum alignment of `ty`
        '''
        return self.abi.abi_alignment(ty)

    @property
    def abi(self):
        return self.target_data

    def unreachable(self):
        '''insert instruction that causes segfault some platform (Intel),
        or no-op on others.

        It has no defined semantic.
        '''
        self.builder.unreachable()

    def add_auto_inline(self, callinst):
        self._auto_inline_list.append(callinst)


    def set_memop_non_temporal(self, ldst):
        const_one = self.constant(types.int, 1).value
        md = lc.MetaData.get(self.function.module, [const_one])
        ldst.set_metadata('nontemporal', md)


class CFuncRef(object):
    '''create a function reference to use with `CBuilder.depends`

    Either from name, type and pointer,
    Or from  a llvm.core.FunctionType instance
    '''
    def __init__(self, *args, **kwargs):
        def one_arg(fn):
            self._fn = fn
            self._name = fn.name

        def three_arg(name, ty, ptr):
            self._name = name
            self._type = ty
            self._ptr = ptr

        try:
            three_arg(*args, **kwargs)
            self._meth = self._from_pointer
        except TypeError:
            one_arg(*args, **kwargs)
            self._meth = self._from_func

    def __call__(self, module):
        return self._meth()

    def _from_func(self):
        return self._fn

    def _from_pointer(self):
        fnptr = types.pointer(self._type)
        ptr = lc.Constant.int(types.intp, self._ptr)
        ptr = ptr.inttoptr(fnptr)
        return ptr

    def __str__(self):
        return self._name


class CDefinition(object):
    '''represents function definition

    Inherit from this class to create a new function definition.

    Class Members
    -------------
    _name_ : name of the function
    _retty_ : return type
    _argtys_ : argument names and types as list of tuples;
               e.g. [ ( 'myarg', lc.Type.int() ), ... ]
    '''
    _name_ = ''             # name of the function; should overide in subclass
    _retty_  = types.void # return type; can overide in subclass
    _argtys_ = []       # a list of tuple(name, type, [attributes]); can overide in subclass

    def __init__(self, *args, **kwargs):
        self.specialize(*args, **kwargs)
        self.cbuilder = None

    def specialize(self, *args, **kwargs):
        """
        Override in subclasses
        """

    def specialize_name(self):
        """
        Specialize the class name to enable multiple function definitions
        """
        cls = type(self)

        counter = getattr(cls, 'counter', 0)
        cls._name_ = "%s_%d" % (cls._name_, counter)
        cls.counter = counter + 1

    def define(self, module, optimize=True):
        '''define the function in the module.

        Raises NameError if a function of the same name has already been
        defined.
        '''
        functype = lc.Type.function(self._retty_, [arg[1] for arg in self._argtys_])
        name = self._name_
        if not name:
            raise AttributeError("Function name cannot be empty.")

        func = module.get_or_insert_function(functype, name=name)

        if not func.is_declaration: # already defined?
            raise FunctionAlreadyExists(func)

        # Name all arguments
        for i, arginfo in enumerate(self._argtys_):
            name = arginfo[0]
            func.args[i].name = name
            if len(arginfo) > 2:
                for attr in arginfo[2]:
                    func.args[i].add_attribute(attr)

        # Create builder and populate body
        self.cbuilder = CBuilder(func)
        self.body(*self.cbuilder.args)
        self.cbuilder.close()
        self.cbuilder = None

        if optimize:
            fpm = lp.FunctionPassManager.new(module)
            pmb = lp.PassManagerBuilder.new()
            pmb.opt_level = 2
            pmb.populate(fpm)
            fpm.run(func)

        return func

    def __call__(self, module):
        # We don't really have to overload __call__ to do things like
        # defining functions...
        try:
            func = self.define(module)
        except FunctionAlreadyExists as e:
            func = e.func
        return func

    def __getattr__(self, attr):
        return getattr(self.cbuilder, attr)

    def body(self):
        '''overide this function to define the body.
        '''
        raise NotImplementedError

    def __str__(self):
        return self._name_

class CValue(object):
    def __init__(self, parent, handle):
        self.__parent = parent
        self.__handle = handle

    @property
    def handle(self):
        return self.__handle

    @property
    def parent(self):
        return self.__parent

    def _temp(self, val):
        return CTemp(self.parent, val)

def _get_operator_provider(ty):
    if _is_pointer(ty):
        return PointerValue
    elif _is_int(ty):
        return IntegerValue
    elif _is_real(ty):
        return RealValue
    elif _is_vector(ty):
        inner = _get_operator_provider(ty.element)
        return type(str(ty), (inner, VectorIndexing), {})
    elif _is_struct(ty):
        return StructValue
    else:
        assert False, (str(ty), type(ty))

class CTemp(CValue):
    def __new__(cls, parent, handle):
        meta = _get_operator_provider(handle.type)
        base = type(str('%s_%s' % (cls.__name__, handle.type)), (cls, meta), {})
        return object.__new__(base)

    def __init__(self, *args, **kws):
        super(CTemp, self).__init__(*args, **kws)
        self._init_mixin()

    @property
    def value(self):
        return self.handle

    @property
    def type(self):
        return self.value.type

class CVar(CValue):
    def __new__(cls, parent, ptr):
        meta = _get_operator_provider(ptr.type.pointee)
        base = type(str('%s_%s' % (cls.__name__, ptr.type.pointee)), (cls, meta), {})
        return object.__new__(base)

    def __init__(self, parent, ptr):
        super(CVar, self).__init__(parent, ptr)
        self._init_mixin()
        self.invariant = False

    def reference(self):
        return self._temp(self.handle)

    @property
    def ref(self):
        return self.reference()

    @property
    def value(self):
        return self.parent.builder.load(self.ref.value)

    @property
    def type(self):
        return self.ref.type.pointee

    def assign(self, val, **kws):
        if self.invariant:
            raise TypeError("Storing to invariant variable.")
        self.parent.builder.store(val.value, self.ref.value, **kws)
        return self

    def __iadd__(self, rhs):
        return self.assign(self.__add__(rhs))

    def __isub__(self, rhs):
        return self.assign(self.__sub__(rhs))

    def __imul__(self, rhs):
        return self.assign(self.__mul__(rhs))

    def __idiv__(self, rhs):
        return self.assign(self.__div__(rhs))

    def __imod__(self, rhs):
        return self.assign(self.__mod__(rhs))

    def __ilshift__(self, rhs):
        return self.assign(self.__lshift__(rhs))

    def __irshift__(self, rhs):
        return self.assign(self.__rshift__(rhs))

    def __iand__(self, rhs):
        return self.assign(self.__and__(rhs))

    def __ior__(self, rhs):
        return self.assign(self.__or__(rhs))

    def __ixor__(self, rhs):
        return self.assign(self.__xor__(rhs))


class OperatorMixin(object):
    def _init_mixin(self):
        pass

class IntegerValue(OperatorMixin):

    def _init_mixin(self):
        self._unsigned = False

    def _get_unsigned(self):
        return self._unsigned

    def _set_unsigned(self, unsigned):
        self._unsigned = bool(unsigned)

    unsigned = property(_get_unsigned, _set_unsigned)

    def __add__(self, rhs):
        return self._temp(self.parent.builder.add(self.value, rhs.value))

    def __sub__(self, rhs):
        return self._temp(self.parent.builder.sub(self.value, rhs.value))

    def __mul__(self, rhs):
        return self._temp(self.parent.builder.mul(self.value, rhs.value))

    def __div__(self, rhs):
        if self.unsigned:
            return self._temp(self.parent.builder.udiv(self.value, rhs.value))
        else:
            return self._temp(self.parent.builder.sdiv(self.value, rhs.value))

    __truediv__ = __div__
    __floordiv__ = __div__

    def __mod__(self, rhs):
        if self.unsigned:
            return self._temp(self.parent.builder.urem(self.value, rhs.value))
        else:
            return self._temp(self.parent.builder.srem(self.value, rhs.value))

    def __lshift__(self, rhs):
        return self._temp(self.parent.builder.shl(self.value, rhs.value))

    def __rshift__(self, rhs):
        if self.unsigned:
            return self._temp(self.self.parent.builder.lshr(self.value, rhs.value))
        else:
            return self._temp(self.parent.builder.ashr(self.value, rhs.value))

    def __and__(self, rhs):
        return self._temp(self.parent.builder.and_(self.value, rhs.value))

    def __or__(self, rhs):
        return self._temp(self.parent.builder.or_(self.value, rhs.value))

    def __xor__(self, rhs):
        return self._temp(self.parent.builder.xor(self.value, rhs.value))

    def __lt__(self, rhs):
        if self.unsigned:
            return self._temp(self.parent.builder.icmp(lc.ICMP_ULT, self.value, rhs.value))
        else:
            return self._temp(self.parent.builder.icmp(lc.ICMP_SLT, self.value, rhs.value))

    def __le__(self, rhs):
        if self.unsigned:
            return self._temp(self.parent.builder.icmp(lc.ICMP_ULE, self.value, rhs.value))
        else:
            return self._temp(self.parent.builder.icmp(lc.ICMP_SLE, self.value, rhs.value))

    def __eq__(self, rhs):
        return self._temp(self.parent.builder.icmp(lc.ICMP_EQ, self.value, rhs.value))

    def __ne__(self, rhs):
        return self._temp(self.parent.builder.icmp(lc.ICMP_NE, self.value, rhs.value))

    def __gt__(self, rhs):
        if self.unsigned:
            return self._temp(self.parent.builder.icmp(lc.ICMP_UGT, self.value, rhs.value))
        else:
            return self._temp(self.parent.builder.icmp(lc.ICMP_SGT, self.value, rhs.value))

    def __ge__(self, rhs):
        if self.unsigned:
            return self._temp(self.parent.builder.icmp(lc.ICMP_UGE, self.value, rhs.value))
        else:
            return self._temp(self.parent.builder.icmp(lc.ICMP_SGE, self.value, rhs.value))

    def __neg__(self):
        return self._temp(self.parent.builder.neg(self.value))

    def cast(self, ty, unsigned=False):
        if ty == self.type:
            return self._temp(self.value)

        if _is_real(ty):
            if self.unsigned or unsigned:
                return self._temp(self.parent.builder.uitofp(self.value, ty))
            else:
                return self._temp(self.parent.builder.sitofp(self.value, ty))
        elif _is_int(ty):
            if self.parent.abi.size(self.type) < self.parent.abi.size(ty):
                if self.unsigned or unsigned:
                    return self._temp(self.parent.builder.zext(self.value, ty))
                else:
                    return self._temp(self.parent.builder.sext(self.value, ty))
            else:
                return self._temp(self.parent.builder.trunc(self.value, ty))
        elif _is_pointer(ty) and _is_int(self.type):
            return self._temp(self.parent.builder.inttoptr(self.value, ty))
        elif _is_int(ty) and _is_pointer(self.type):
            return self._temp(self.parent.builder.ptrtoint(self.value, ty))

        raise CastError(self.type, ty)

class RealValue(OperatorMixin):
    def __add__(self, rhs):
        return self._temp(self.parent.builder.fadd(self.value, rhs.value))

    def __sub__(self, rhs):
        return self._temp(self.parent.builder.fsub(self.value, rhs.value))

    def __mul__(self, rhs):
        return self._temp(self.parent.builder.fmul(self.value, rhs.value))

    def __div__(self, rhs):
        return self._temp(self.parent.builder.fdiv(self.value, rhs.value))

    __truediv__ = __div__

    def __mod__(self, rhs):
        return self._temp(self.parent.builder.frem(self.value, rhs.value))

    def __lt__(self, rhs):
        return self._temp(self.parent.builder.fcmp(lc.FCMP_OLT, self.value, rhs.value))

    def __le__(self, rhs):
        return self._temp(self.parent.builder.fcmp(lc.FCMP_OLE, self.value, rhs.value))

    def __eq__(self, rhs):
        return self._temp(self.parent.builder.fcmp(lc.FCMP_OEQ, self.value, rhs.value))

    def __ne__(self, rhs):
        return self._temp(self.parent.builder.fcmp(lc.FCMP_ONE, self.value, rhs.value))

    def __gt__(self, rhs):
        return self._temp(self.parent.builder.fcmp(lc.FCMP_OGT, self.value, rhs.value))

    def __ge__(self, rhs):
        return self._temp(self.parent.builder.fcmp(lc.FCMP_OGE, self.value, rhs.value))

    def cast(self, ty, unsigned=False):
        if ty == self.type:
            return self._temp(self.value)

        if _is_int(ty):
            if unsigned:
                return self._temp(self.parent.builder.fptoui(self.value, ty))
            else:
                return self._temp(self.parent.builder.fptosi(self.value, ty))

        if _is_real(ty):
            if self.parent.abi.size(self.type) > self.parent.abi.size(ty):
                return self._temp(self.parent.builder.fptrunc(self.value, ty))
            else:
                return self._temp(self.parent.builder.fpext(self.value, ty))

        raise CastError(self.type, ty)


class PointerIndexing(OperatorMixin):
    def __getitem__(self, idx):
        '''implement access indexing

        Uses GEP.
        '''
        bldr = self.parent.builder
        if type(idx) is slice:
            # just handle case by case
            # Case #1: A[idx:] get pointer offset by idx
            if not idx.step and not idx.stop:
                idx = _auto_coerce_index(self.parent, idx.start)
                ptr = bldr.gep(self.value, [idx.value], inbounds=True)
                return CArray(self.parent, ptr)
        else: # return an variable at idx
            idx = _auto_coerce_index(self.parent, idx)
            ptr = bldr.gep(self.value, [idx.value], inbounds=True)
            return CVar(self.parent, ptr)

    def __setitem__(self, idx, val):
        idx = _auto_coerce_index(self.parent, idx)
        bldr = self.parent.builder
        self[idx].assign(val)

class PointerCasting(OperatorMixin):
    def cast(self, ty):
        if ty == self.type:
            return self._temp(self.value)

        if _is_pointer(ty):
            return self._temp(self.parent.builder.bitcast(self.value, ty))

        if _is_int(ty):
            return self._temp(self.parent.builder.ptrtoint(self.value, ty))

        raise CastError(self.type, ty)



class VectorIndexing(OperatorMixin):
    def __getitem__(self, idx):
        '''implement access indexing

        Uses GEP.
        '''
        bldr = self.parent.builder
        idx = _auto_coerce_index(self.parent, idx)
        val = bldr.extract_element(self.value, idx.value)
        return CTemp(self.parent, val)

    def __setitem__(self, idx, val):
        idx = _auto_coerce_index(self.parent, idx)
        bldr = self.parent.builder
        vec = bldr.insert_element(self.value, val.value, idx.value)
        bldr.store(vec, self.ref.value)

class PointerValue(PointerIndexing, PointerCasting):

    def load(self, **kws):
        return self._temp(self.parent.builder.load(self.value, **kws))

    def store(self, val, nontemporal=False, **kws):
        inst = self.parent.builder.store(val.value, self.value, **kws)
        if nontemporal:
            self.parent.set_memop_non_temporal(inst)
        return inst

    def atomic_load(self, ordering, align=None, crossthread=True):
        '''atomic load memory for pointer types

        align : overide to control memory alignment; otherwise the default
                alignment of the type is used.

        Other parameters are the same as `CBuilder.atomic_load`
        '''
        if align is None:
            align = self.parent.alignment(self.type.pointee)
        inst = self.parent.builder.atomic_load(self.value, ordering, align,
                                               crossthread=crossthread)
        return self._temp(inst)

    def atomic_store(self, value, ordering, align=None,  crossthread=True):
        '''atomic memory store for pointer types

        align : overide to control memory alignment; otherwise the default
                alignment of the type is used.

        Other parameters are the same as `CBuilder.atomic_store`
        '''
        if align is None:
            align = self.parent.alignment(self.type.pointee)
        self.parent.builder.atomic_store(value.ptr, self.value, ordering,
                                         align=align, crossthread=crossthread)

    def atomic_cmpxchg(self, old, new, ordering, crossthread=True):
        '''atomic compare-exchange for pointer types

        Other parameters are the same as `CBuilder.atomic_cmpxchg`
        '''
        inst = self.parent.builder.atomic_cmpxchg(self.value, old.value,
                                                  new.value, ordering,
                                                  crossthread=crossthread)
        return self._temp(inst)

    def as_struct(self, cstruct_class, volatile=False):
        '''load a pointer to a structure and assume a structure interface
        '''
        ptr = self.parent.builder.load(self.value, volatile=volatile)
        return cstruct_class(self.parent, self.value)

class StructValue(OperatorMixin):

    def as_struct(self, cstruct_class):
        '''assume a structure interface
        '''
        return cstruct_class(self.parent, self.ref.value)


class CFunc(CValue, PointerCasting):
    '''Wraps function pointer
    '''
    def __init__(self, parent, func):
        super(CFunc, self).__init__(parent, func)

    @property
    def function(self):
        return self.handle

    def __call__(self, *args, **opts):
        '''Call the function with the given arguments

        *args : variable arguments of CValue instances
        '''
        arg_values = _list_values(args)
        ftype = self.function.type.pointee
        for i, (exp, got) in enumerate(zip(ftype.args, arg_values)):
            if exp != got.type:
                raise TypeError("At call to %s, "
                                "argument %d mismatch: %s != %s"
                                % (self.function.name, i, exp, got.type))
        res = self.parent.builder.call(self.function, arg_values)

        if hasattr(self.function, 'calling_convention'):
            res.calling_convention = self.function.calling_convention

        if opts.get('inline'):
            self.parent.add_auto_inline(res)

        if ftype.return_type != lc.Type.void():
            return CTemp(self.parent, res)

    @property
    def value(self):
        return self.function

    @property
    def type(self):
        return self.function.type


class CArray(CValue, PointerIndexing, PointerCasting):
    '''wraps a array

    Similar to C arrays
    '''
    def __init__(self, parent, base):
        super(CArray, self).__init__(parent, base)

    @property
    def value(self):
        return self.handle

    def reference(self):
        return self._temp(self.value)

    @property
    def type(self):
        return self.value.type

    def vector_load(self, count, align=0):
        parent = self.parent
        builder = parent.builder
        values = [self[i] for i in range(count)]

        vecty = types.vector(self.type.pointee, count)
        vec = builder.load(builder.bitcast(self.value, types.pointer(vecty)),
                           align=align)
        return self._temp(vec)

    def vector_store(self, vec, align=0):
        if vec.type.element != self.type.pointee:
            raise TypeError("Type mismatch; expect %s but got %s" % \
                            (vec.type.element, self.type.pointee))
        parent = self.parent
        builder = parent.builder
        vecptr = builder.bitcast(self.value, types.pointer(vec.type))
        builder.store(vec.value, vecptr, align=align)
        return self


class CStruct(CValue):
    '''Wraps a structure

    Structure in LLVM can be identified by name of layout.

    Subclass to define a new structure. All fields are defined in the
    `_fields_` class attribute as a list of tuple (name, type).

    Can define new methods which gets inlined to the parent CBuilder.
    '''

    def __init__(self, parent, ptr):
        super(CStruct, self).__init__(parent, ptr)
        makeind = lambda x: self.parent.constant(types.int, x).value

        for i, (fd, _) in enumerate(self._fields_):
            gep = self.parent.builder.gep(ptr, [makeind(0), makeind(i)])
            gep.name = "%s.%s" % (type(self).__name__, fd)
            if hasattr(self, fd):
                raise AttributeError("Field name shadows another attribute")
            setattr(self, fd, CVar(self.parent, gep))

        self.type = self.llvm_type()

    def reference(self):
        return self._temp(self.handle)

    @classmethod
    def llvm_type(cls):
        return lc.Type.struct([v for k, v in cls._fields_])

    @classmethod
    def from_numba_struct(cls, context, struct_type):
        class Struct(cls):
            _fields_ = [(name, type.to_llvm(context))
            for name, type in struct_type.fields]
        return Struct


class CExternal(object):
    '''subclass to define external interface

    All class attributes that are `llvm.core.FunctionType` are converted
    to `CFunc` instance during instantiation.
    '''

    _calling_convention_ = None # default

    def __init__(self, cbuilder):
        is_func = lambda x: isinstance(x, lc.FunctionType)
        non_magic = lambda s: not ( s.startswith('__') and s.endswith('__') )

        to_declare = []
        for fname in filter(non_magic, vars(type(self))):
            ftype = getattr(self, fname)
            if is_func(ftype):
                to_declare.append((fname, ftype))

        mod = cbuilder.function.module
        for fname, ftype in to_declare:
            func = mod.get_or_insert_function(ftype, name=fname)
            if self._calling_convention_:
                func.calling_convention = self._calling_convention_

            if func.type.pointee != ftype:
                raise NameError("Function has already been declared "
                                "with a different type: %s != %s"
                                % (func.type, ftype) )
            setattr(self, fname, CFunc(cbuilder, func))



########NEW FILE########
__FILENAME__ = executor
'''
This is mostly a convenience module for testing with ctypes.
'''

from llvm.core import Type, Module
import llvm.ee as le
import ctypes as ct

MAP_CTYPES = {
'void'       :   None,
'bool'       :   ct.c_bool,
'char'       :   ct.c_char,
'uchar'      :   ct.c_ubyte,
'short'      :   ct.c_short,
'ushort'     :   ct.c_ushort,
'int'        :   ct.c_int,
'uint'       :   ct.c_uint,
'long'       :   ct.c_long,
'ulong'      :   ct.c_ulong,

'int8'       :   ct.c_int8,
'uint8'      :   ct.c_uint8,
'int16'      :   ct.c_int16,
'uint16'     :   ct.c_uint16,
'int32'      :   ct.c_int32,
'uint32'     :   ct.c_uint32,
'int64'      :   ct.c_int64,
'uint64'     :   ct.c_uint64,

'float'      :   ct.c_float,
'double'     :   ct.c_double,
'longdouble' :   ct.c_longdouble,
}

class CExecutor(object):
    '''a convenient class for creating ctype functions from LLVM modules
    '''
    def __init__(self, mod_or_engine):
        if isinstance(mod_or_engine, Module):
            self.engine = le.EngineBuilder.new(mod_or_engine).opt(3).create()
        else:
            self.engine = mod_or_engine

    def get_ctype_function(self, fn, *typeinfo):
        '''create a ctype function from a LLVM function

        typeinfo : string of types (see `MAP_CTYPES`) or
                   list of ctypes datatype.
                   First value is the return type.
                   A function that takes no argument and return nothing
                   should use `"void"` or `None`.
        '''
        if len(typeinfo)==1 and isinstance(typeinfo[0], str):
            types = [ MAP_CTYPES[s.strip()] for s in typeinfo[0].split(',') ]
            if not types:
                retty = None
                argtys = []
            else:
                retty = types[0]
                argtys = types[1:]
        else:
            retty = typeinfo[0]
            argtys = typeinfo[1:]
        prototype = ct.CFUNCTYPE(retty, *argtys)
        fnptr = self.engine.get_pointer_to_function(fn)
        return prototype(fnptr)


########NEW FILE########
__FILENAME__ = libc
from .builder import CExternal
import llvm.core as lc
from . import shortnames as types

class LibC(CExternal):
    printf = lc.Type.function(types.int, [types.char_p], True)
    # TODO a lot more to add


########NEW FILE########
__FILENAME__ = shortnames
from llvm.core import Type

void = Type.void()
char = Type.int(8)
short = Type.int(16)
int = Type.int(32)
int16 = short
int32 = int
int64 = Type.int(64)

float = Type.float()
double = Type.double()

# platform dependent

def _determine_sizes():
    import ctypes
    # Makes following assumption:
    # sizeof(py_ssize_t) == sizeof(ssize_t) == sizeof(size_t)
    any_size_t = getattr(ctypes, 'c_ssize_t', ctypes.c_size_t)
    return ctypes.sizeof(ctypes.c_void_p) * 8, ctypes.sizeof(any_size_t) * 8

pointer_size, _py_ssize_t_bits = _determine_sizes()

intp = {32: int32, 64: int64}[pointer_size]

npy_intp = Type.int(pointer_size)
py_ssize_t = Type.int(_py_ssize_t_bits)

# pointers

pointer = Type.pointer

void_p = pointer(char)
char_p = pointer(char)
npy_intp_p = pointer(npy_intp)

# vector
def vector(ty, ct):
    return Type.vector(ty, 4)


########NEW FILE########
__FILENAME__ = test_atomic_add
'''
Base on the test_pthread.py and extend to use atomic instructions
'''

from llvm.core import *
from llvm.passes import *
from llvm.ee import *
from llvm_cbuilder import *
import llvm_cbuilder.shortnames as C
import unittest, logging
import sys

# logging.basicConfig(level=logging.DEBUG)

NUM_OF_THREAD = 4
REPEAT = 10000

def gen_test_worker(mod):
    cb = CBuilder.new_function(mod, 'worker', C.void, [C.pointer(C.int)])
    pval = cb.args[0]
    one = cb.constant(pval.type.pointee, 1)

    ct = cb.var(C.int, 0)
    limit = cb.constant(C.int, REPEAT)
    with cb.loop() as loop:
        with loop.condition() as setcond:
            setcond( ct < limit )

        with loop.body():
            cb.atomic_add(pval, one, 'acq_rel')
            ct += one

    cb.ret()
    cb.close()
    return cb.function

def gen_test_pthread(mod):
    cb = CBuilder.new_function(mod, 'manager', C.int, [C.int])
    arg = cb.args[0]

    worker_func = cb.get_function_named('worker')
    pthread_create = cb.get_function_named('pthread_create')
    pthread_join = cb.get_function_named('pthread_join')


    NULL = cb.constant_null(C.void_p)
    cast_to_null = lambda x: x.cast(C.void_p)

    threads = cb.array(C.void_p, NUM_OF_THREAD)

    for tid in range(NUM_OF_THREAD):
        pthread_create_args = [threads[tid].reference(),
                               NULL,
                               worker_func,
                               arg.reference()]
        pthread_create(*map(cast_to_null, pthread_create_args))

    worker_func(arg.reference())

    for tid in range(NUM_OF_THREAD):
        pthread_join_args = threads[tid], NULL
        pthread_join(*map(cast_to_null, pthread_join_args))


    cb.ret(arg)
    cb.close()
    return cb.function

class TestAtomicAdd(unittest.TestCase):
    @unittest.skipIf(sys.platform == 'win32', "test uses pthreads, not supported on Windows")
    def test_atomic_add(self):
        mod = Module.new(__name__)
        # add pthread functions

        mod.add_function(Type.function(C.int,
                                       [C.void_p, C.void_p, C.void_p, C.void_p]),
                         'pthread_create')

        mod.add_function(Type.function(C.int,
                                       [C.void_p, C.void_p]),
                         'pthread_join')

        lf_test_worker = gen_test_worker(mod)
        lf_test_pthread = gen_test_pthread(mod)
        logging.debug(mod)
        mod.verify()

        # optimize
        fpm = FunctionPassManager.new(mod)
        mpm = PassManager.new()
        pmb = PassManagerBuilder.new()
        pmb.vectorize = True
        pmb.opt_level = 3
        pmb.populate(fpm)
        pmb.populate(mpm)

        fpm.run(lf_test_worker)
        fpm.run(lf_test_pthread)
        mpm.run(mod)
        logging.debug(mod)
        mod.verify()

        # run
        exe = CExecutor(mod)
        exe.engine.get_pointer_to_function(mod.get_function_named('worker'))
        func = exe.get_ctype_function(lf_test_pthread, 'int, int')

        inarg = 1234
        gold = inarg + (NUM_OF_THREAD + 1) * REPEAT

        for _ in range(1000): # run many many times to catch race condition
            self.assertEqual(func(inarg), gold, "Unexpected race condition")


if __name__ == '__main__':
    unittest.main()


########NEW FILE########
__FILENAME__ = test_atomic_cmpxchg
'''
Base on the test_pthread.py and extend to use atomic instructions
'''

from llvm.core import *
from llvm.passes import *
from llvm.ee import *
from llvm_cbuilder import *
import llvm_cbuilder.shortnames as C
import unittest, logging
import sys

# logging.basicConfig(level=logging.DEBUG)

NUM_OF_THREAD = 4
REPEAT = 10000

def gen_test_worker(mod):
    cb = CBuilder.new_function(mod, 'worker', C.void, [C.pointer(C.int)])
    pval = cb.args[0]
    one = cb.constant(pval.type.pointee, 1)

    ct = cb.var(C.int, 0)
    limit = cb.constant(C.int, REPEAT)
    with cb.loop() as loop:
        with loop.condition() as setcond:
            setcond( ct < limit )

        with loop.body():
            oldval = pval.atomic_load('acquire')
            updated = oldval + one
            castmp = pval.atomic_cmpxchg(oldval, updated, 'release')

            with cb.ifelse( castmp == oldval ) as ifelse:
                with ifelse.then():
                    ct += one

    cb.ret()
    cb.close()
    return cb.function

def gen_test_pthread(mod):
    cb = CBuilder.new_function(mod, 'manager', C.int, [C.int])
    arg = cb.args[0]

    worker_func = cb.get_function_named('worker')
    pthread_create = cb.get_function_named('pthread_create')
    pthread_join = cb.get_function_named('pthread_join')


    NULL = cb.constant_null(C.void_p)
    cast_to_null = lambda x: x.cast(C.void_p)

    threads = cb.array(C.void_p, NUM_OF_THREAD)

    for tid in range(NUM_OF_THREAD):
        pthread_create_args = [threads[tid].reference(),
                               NULL,
                               worker_func,
                               arg.reference()]
        pthread_create(*map(cast_to_null, pthread_create_args))

    worker_func(arg.reference())

    for tid in range(NUM_OF_THREAD):
        pthread_join_args = threads[tid], NULL
        pthread_join(*map(cast_to_null, pthread_join_args))


    cb.ret(arg)
    cb.close()
    return cb.function

class TestAtomicCmpXchg(unittest.TestCase):
    @unittest.skipIf(sys.platform == 'win32', "test uses pthreads, not supported on Windows")
    def test_atomic_cmpxchg(self):
        mod = Module.new(__name__)
        # add pthread functions

        mod.add_function(Type.function(C.int,
                                       [C.void_p, C.void_p, C.void_p, C.void_p]),
                         'pthread_create')

        mod.add_function(Type.function(C.int,
                                       [C.void_p, C.void_p]),
                         'pthread_join')

        lf_test_worker = gen_test_worker(mod)
        lf_test_pthread = gen_test_pthread(mod)
        logging.debug(mod)
        mod.verify()

        # optimize
        fpm = FunctionPassManager.new(mod)
        mpm = PassManager.new()
        pmb = PassManagerBuilder.new()
        pmb.vectorize = True
        pmb.opt_level = 3
        pmb.populate(fpm)
        pmb.populate(mpm)

        fpm.run(lf_test_worker)
        fpm.run(lf_test_pthread)
        mpm.run(mod)
        logging.debug(mod)
        mod.verify()

        # run
        exe = CExecutor(mod)
        exe.engine.get_pointer_to_function(mod.get_function_named('worker'))
        func = exe.get_ctype_function(lf_test_pthread, 'int, int')

        inarg = 1234
        gold = inarg + (NUM_OF_THREAD + 1) * REPEAT

        for _ in range(1000): # run many many times to catch race condition
            res = func(inarg)
            self.assertEqual(res, gold,
                             "Unexpected race condition: res = %d" % res)


if __name__ == '__main__':
    unittest.main()


########NEW FILE########
__FILENAME__ = test_cstr_collide
from llvm.core import *
from llvm_cbuilder import *
from llvm_cbuilder import shortnames as C

import unittest

class TestCstrCollide(unittest.TestCase):
    def test_same_string(self):
        mod = Module.new(__name__)
        cb = CBuilder.new_function(mod, 'test_cstr_collide', C.void, [])

        a = cb.constant_string("hello")
        b = cb.constant_string("hello")
        self.assertEqual(a.value, b.value)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_isprime
from llvm.core import *
from llvm.passes import *
from llvm.ee import *
from llvm_cbuilder import *
import llvm_cbuilder.shortnames as C
import unittest, logging

def is_prime(x):
    if x <= 2:
        return True
    if (x % 2) == 0:
        return False
    for y in range(2, int(1 + x**0.5)):
        if (x % y) == 0:
            return False
    return True

def gen_is_prime(mod):
    functype = Type.function(C.int, [C.int])
    func = mod.add_function(functype, 'isprime')

    cb = CBuilder(func)

    arg = cb.args[0]

    two = cb.constant(C.int, 2)
    true = one = cb.constant(C.int, 1)
    false = zero = cb.constant(C.int, 0)

    with cb.ifelse( arg <= two ) as ifelse:
        with ifelse.then():
            cb.ret(true)

    with cb.ifelse( (arg % two) == zero ) as ifelse:
        with ifelse.then():
            cb.ret(false)

    idx = cb.var(C.int, 3, name='idx')
    with cb.loop() as loop:
        with loop.condition() as setcond:
            setcond( idx < arg )

        with loop.body():
            with cb.ifelse( (arg % idx) == zero ) as ifelse:
                with ifelse.then():
                    cb.ret(false)
            # increment
            idx += two

    cb.ret(true)
    cb.close()
    return func


def gen_is_prime_fast(mod):
    functype = Type.function(C.int, [C.int])
    func = mod.add_function(functype, 'isprime_fast')

    cb = CBuilder(func)

    arg = cb.args[0]

    two = cb.constant(C.int, 2)
    true = one = cb.constant(C.int, 1)
    false = zero = cb.constant(C.int, 0)

    with cb.ifelse( arg <= two ) as ifelse:
        with ifelse.then():
            cb.ret(true)

    with cb.ifelse( (arg % two) == zero ) as ifelse:
        with ifelse.then():
            cb.ret(false)

    idx = cb.var(C.int, 3, name='idx')

    sqrt = cb.get_intrinsic(INTR_SQRT, [C.float])

    looplimit = one + sqrt(arg.cast(C.float)).cast(C.int)


    with cb.loop() as loop:
        with loop.condition() as setcond:
            setcond( idx < looplimit )

        with loop.body():
            with cb.ifelse( (arg % idx) == zero ) as ifelse:
                with ifelse.then():
                    cb.ret(false)
            # increment
            idx += two


    cb.ret(true)
    cb.close()
    return func

class TestIsPrime(unittest.TestCase):
    def test_isprime(self):
        mod = Module.new(__name__)
        lf_isprime = gen_is_prime(mod)
        logging.debug(mod)
        mod.verify()

        exe = CExecutor(mod)
        func = exe.get_ctype_function(lf_isprime, 'bool, int')
        for x in range(2, 1000):
            msg = "Failed at x = %d" % x
            self.assertEqual(func(x), is_prime(x), msg)

    def test_isprime_fast(self):
        mod = Module.new(__name__)
        lf_isprime = gen_is_prime_fast(mod)
        logging.debug(mod)
        mod.verify()

        exe = CExecutor(mod)
        func = exe.get_ctype_function(lf_isprime, 'bool, int')
        for x in range(2, 1000):
            msg = "Failed at x = %d" % x
            self.assertEqual(func(x), is_prime(x), msg)

if __name__ == '__main__':
    unittest.main()


########NEW FILE########
__FILENAME__ = test_loopcontrol
from llvm.core import *
from llvm.passes import *
from llvm.ee import *
from llvm_cbuilder import *
import llvm_cbuilder.shortnames as C
import unittest, logging

def loopbreak(d):
    z = 0
    for x in range(100):
        for y in range(100):
            z += x + y
            if z > 50:
                break
        z -= d
    return z

def gen_loopbreak(mod):
    functype = Type.function(C.int, [C.int])
    func = mod.add_function(functype, 'loopbreak')

    cb = CBuilder(func)

    d = cb.args[0]
    x = cb.var(C.int)
    y = cb.var(C.int)
    z = cb.var(C.int)

    one = cb.constant(C.int, 1)
    zero = cb.constant(C.int, 0)
    limit = cb.constant(C.int, 100)
    fifty = cb.constant(C.int, 50)

    z.assign(zero)
    x.assign(zero)
    with cb.loop() as outer:
        with outer.condition() as setcond:
            setcond( x < limit )

        with outer.body():
            y.assign(zero)
            with cb.loop() as inner:
                with inner.condition() as setcond:
                    setcond( y < limit )

                with inner.body():
                    z += x + y
                    with cb.ifelse( z > fifty ) as ifelse:
                        with ifelse.then():
                            inner.break_loop()
                    y += one
            z -= d
            x += one

    cb.ret(z)
    cb.close()
    return func

def loopcontinue(d):
    z = 0
    for x in range(100):
        for y in range(100):
            z += x + y
            if z > 50:
                continue
            z += d
    return z

def gen_loopcontinue(mod):
    functype = Type.function(C.int, [C.int])
    func = mod.add_function(functype, 'loopcontinue')

    cb = CBuilder(func)

    d = cb.args[0]
    x = cb.var(C.int)
    y = cb.var(C.int)
    z = cb.var(C.int)

    one = cb.constant(C.int, 1)
    zero = cb.constant(C.int, 0)
    limit = cb.constant(C.int, 100)
    fifty = cb.constant(C.int, 50)

    z.assign(zero)
    x.assign(zero)
    with cb.loop() as outer:
        with outer.condition() as setcond:
            setcond( x < limit )

        with outer.body():
            y.assign(zero)
            with cb.loop() as inner:
                with inner.condition() as setcond:
                    setcond( y < limit )

                with inner.body():
                    z += x + y
                    y += one
                    with cb.ifelse( z > fifty ) as ifelse:
                        with ifelse.then():
                            inner.continue_loop()
                    z += d
            x += one

    cb.ret(z)
    cb.close()
    return func

class TestLoopControl(unittest.TestCase):
    def test_loopbreak(self):
        mod = Module.new(__name__)
        lfunc = gen_loopbreak(mod)
        logging.debug(mod)
        mod.verify()

        exe = CExecutor(mod)
        func = exe.get_ctype_function(lfunc, 'int, int')
        for x in range(100):
            self.assertEqual(func(x), loopbreak(x))

    def test_loopcontinue(self):
        mod = Module.new(__name__)
        lfunc = gen_loopcontinue(mod)
        logging.debug(mod)
        mod.verify()

        exe = CExecutor(mod)
        func = exe.get_ctype_function(lfunc, 'int, int')
        for x in range(100):
            self.assertEqual(func(x), loopcontinue(x))

if __name__ == '__main__':
    unittest.main()


########NEW FILE########
__FILENAME__ = test_nestedloops
from llvm.core import *
from llvm.passes import *
from llvm.ee import *
from llvm_cbuilder import *
import llvm_cbuilder.shortnames as C
import unittest, logging

def nestedloop1(d):
    z = 0
    for x in range(100):
        for y in range(100):
            z += x * d + int(y / d)
    return z

def gen_nestedloop1(mod):
    functype = Type.function(C.int, [C.int])
    func = mod.add_function(functype, 'nestedloop1')

    cb = CBuilder(func)

    d = cb.args[0]
    x = cb.var(C.int)
    y = cb.var(C.int)
    z = cb.var(C.int)

    one = cb.constant(C.int, 1)
    zero = cb.constant(C.int, 0)
    limit = cb.constant(C.int, 100)

    z.assign(zero)
    x.assign(zero)
    with cb.loop() as outer:
        with outer.condition() as setcond:
            setcond( x < limit )

        with outer.body():
            y.assign(zero)
            with cb.loop() as inner:
                with inner.condition() as setcond:
                    setcond( y < limit )

                with inner.body():
                    z += x * d + y / d
                    y += one
            x += one

    cb.ret(z)
    cb.close()
    return func


def nestedloop2(d):
    z = 0
    for x in range(1, 100):
        for y in range(1, 100):
            if x > y:
                z += int(x / y) * d
            else:
                z += int(y / x) * d
    return z

def gen_nestedloop2(mod):
    functype = Type.function(C.int, [C.int])
    func = mod.add_function(functype, 'nestedloop2')

    cb = CBuilder(func)

    d = cb.args[0]
    x = cb.var(C.int)
    y = cb.var(C.int)
    z = cb.var(C.int)

    one = cb.constant(C.int, 1)
    zero = cb.constant(C.int, 0)
    limit = cb.constant(C.int, 100)

    z.assign(zero)
    x.assign(one)
    with cb.loop() as outer:
        with outer.condition() as setcond:
            setcond( x < limit )

        with outer.body():
            y.assign(one)
            with cb.loop() as inner:
                with inner.condition() as setcond:
                    setcond( y < limit )

                with inner.body():
                    with cb.ifelse(x > y) as ifelse:
                        with ifelse.then():
                            z += x / y * d
                        with ifelse.otherwise():
                            z += y / x * d
                    y += one
            x += one

    cb.ret(z)
    cb.close()
    return func


class TestNestedLoop(unittest.TestCase):
    def test_nestedloop1(self):
        mod = Module.new(__name__)
        lfunc = gen_nestedloop1(mod)
        logging.debug(mod)
        mod.verify()

        exe = CExecutor(mod)
        func = exe.get_ctype_function(lfunc, 'int, int')
        for x in range(1, 100):
            self.assertEqual(func(x), int(nestedloop1(x)))

    def test_nestedloop2(self):
        mod = Module.new(__name__)
        lfunc = gen_nestedloop2(mod)
        logging.debug(mod)
        mod.verify()

        exe = CExecutor(mod)
        func = exe.get_ctype_function(lfunc, 'int, int')
        for x in range(1, 100):
            self.assertEqual(func(x), int(nestedloop2(x)))

if __name__ == '__main__':
    unittest.main()


########NEW FILE########
__FILENAME__ = test_print
from llvm.core import *
from llvm.passes import *
from llvm.ee import *
from llvm_cbuilder import *
import llvm_cbuilder.shortnames as C
import sys, unittest, logging
from subprocess import Popen, PIPE

def gen_debugprint(mod):
    functype = Type.function(C.void, [])
    func = mod.add_function(functype, 'debugprint')

    cb = CBuilder(func)
    fmt = cb.constant_string("Show %d %.3f %.3e\n")

    an_int = cb.constant(C.int, 123)
    a_float = cb.constant(C.double, 1.234)
    a_double = cb.constant(C.double, 1e-31)
    cb.printf(fmt, an_int, a_float, a_double)

    cb.debug('an_int =', an_int, 'a_float =', a_float, 'a_double =', a_double)

    cb.ret()
    cb.close()
    return func

def main_debugprint():
    # generate code
    mod = Module.new(__name__)
    lfunc = gen_debugprint(mod)
    logging.debug(mod)
    mod.verify()
    # run
    exe = CExecutor(mod)
    func = exe.get_ctype_function(lfunc, 'void')
    func()

class TestPrint(unittest.TestCase):
    def test_debugprint(self):
        p = Popen([sys.executable, __file__, "-child"], stdout=PIPE)
        p.wait()

        # The encode(utf-8) is for Python 3 compatibility
        lines = p.stdout.read().encode('utf-8').splitlines(False)

        # Try to account for variations in the system printf
        if lines[0].find('e-031') >= 0:
            expect = [
                'Show 123 1.234 1.000e-031',
                'an_int = 123 a_float = 1.234000e+000 a_double = 1.000000e-031',
                ]
        else:
            expect = [
                'Show 123 1.234 1.000e-31',
                'an_int = 123 a_float = 1.234000e+00 a_double = 1.000000e-31',
                ]
        self.assertEqual(expect, lines)

        p.stdout.close()

if __name__ == '__main__':
    try:
        if sys.argv[1] == '-child':
            main_debugprint()
    except IndexError:
        unittest.main()



########NEW FILE########
__FILENAME__ = test_pthread
from llvm.core import *
from llvm.passes import *
from llvm.ee import *
from llvm_cbuilder import *
import llvm_cbuilder.shortnames as C
import unittest, logging
import sys

# logging.basicConfig(level=logging.DEBUG)

NUM_OF_THREAD = 4

def gen_test_worker(mod):
    cb = CBuilder.new_function(mod, 'worker', C.void, [C.pointer(C.int)])
    pval = cb.args[0]
    val = pval.load()
    one = cb.constant(val.type, 1)
    pval.store(val + one)
    cb.ret()
    cb.close()

def gen_test_pthread(mod):
    cb = CBuilder.new_function(mod, 'manager', C.int, [C.int])
    arg = cb.args[0]

    worker_func = cb.get_function_named('worker')
    pthread_create = cb.get_function_named('pthread_create')
    pthread_join = cb.get_function_named('pthread_join')


    NULL = cb.constant_null(C.void_p)
    cast_to_null = lambda x: x.cast(C.void_p)

    threads = cb.array(C.void_p, NUM_OF_THREAD)

    for tid in range(NUM_OF_THREAD):
        pthread_create_args = [threads[tid].reference(),
                               NULL,
                               worker_func,
                               arg.reference()]
        pthread_create(*map(cast_to_null, pthread_create_args))

    worker_func(arg.reference())

    for tid in range(NUM_OF_THREAD):
        pthread_join_args = threads[tid], NULL
        pthread_join(*map(cast_to_null, pthread_join_args))

    cb.ret(arg)
    cb.close()
    return cb.function

class TestPThread(unittest.TestCase):
    @unittest.skipIf(sys.platform == 'win32', "pthreads not supported on Windows")
    def test_pthread(self):
        mod = Module.new(__name__)
        # add pthread functions

        mod.add_function(Type.function(C.int,
                                       [C.void_p, C.void_p, C.void_p, C.void_p]),
                         'pthread_create')

        mod.add_function(Type.function(C.int,
                                       [C.void_p, C.void_p]),
                         'pthread_join')

        gen_test_worker(mod)
        lf_test_pthread = gen_test_pthread(mod)
        logging.debug(mod)
        mod.verify()

        exe = CExecutor(mod)
        exe.engine.get_pointer_to_function(mod.get_function_named('worker'))
        func = exe.get_ctype_function(lf_test_pthread, 'int, int')

        inarg = 1234
        gold = inarg + NUM_OF_THREAD + 1
        self.assertLessEqual(func(inarg), gold)
        # Cannot determine the exact return value due to untamed race condition

        count_race = 0
        for _ in range(2**12):
            if func(inarg) != gold:
                count_race += 1

        if count_race > 0:
            logging.info("Race condition occured %d times.", count_race)
            logging.info("Race condition is expected.")

if __name__ == '__main__':
    unittest.main()


########NEW FILE########
__FILENAME__ = test_struct
from llvm.core import *
from llvm_cbuilder import *
import llvm_cbuilder.shortnames as C
import unittest, ctypes

class Vector2D(CStruct):
    _fields_ = [
        ('x', C.float),
        ('y', C.float),
    ]

class Vector2DCtype(ctypes.Structure):
    _fields_ = [
        ('x', ctypes.c_float),
        ('y', ctypes.c_float),
    ]

def gen_vector2d_dist(mod):
    functype = Type.function(C.float, [C.pointer(Vector2D.llvm_type())])
    func = mod.add_function(functype, 'vector2d_dist')

    cb = CBuilder(func)
    vec = cb.var(Vector2D, cb.args[0].load())
    dist = vec.x * vec.x + vec.y * vec.y

    cb.ret(dist)
    cb.close()
    return func


class TestStruct(unittest.TestCase):
    def test_vector2d_dist(self):
        # prepare module
        mod = Module.new('mod')
        lfunc = gen_vector2d_dist(mod)
        mod.verify()
        # run
        exe = CExecutor(mod)
        func = exe.get_ctype_function(lfunc, ctypes.c_float, ctypes.POINTER(Vector2DCtype))

        from random import random
        pydist = lambda x, y: x * x + y * y
        for _ in range(100):
            x, y = random(), random()
            vec = Vector2DCtype(x=x, y=y)
            ans = func(ctypes.pointer(vec))
            gold = pydist(x, y)

            self.assertLess(abs(ans-gold)/gold, 1e-6)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_translate

from llvm.core import Module
from llvm_cbuilder import *
from llvm_cbuilder.translator import translate
import llvm_cbuilder.shortnames as C
import unittest, logging

#logging.basicConfig(level=logging.DEBUG)

class FooIf(CDefinition):
    _name_ = 'foo_if'
    _retty_ = C.int
    _argtys_ = [('x', C.int),
                ('y', C.int),]

    def body(self, x, y):
        @translate
        def _():
            if x > y:
                return x - y
            else:
                return y - x


class FooWhile(CDefinition):
    _name_ = 'foo_while'
    _retty_ = C.int
    _argtys_ = [('x', C.int)]

    def body(self, x):
        y = self.var_copy(x)

        @translate
        def _():
            while x > 0:
                x -= 1
                y += x
            return y

class FooForRange(CDefinition):
    _name_ = 'foo_for_range'
    _retty_ = C.int
    _argtys_ = [('x', C.int)]

    def body(self, x):
        y = self.var(x.type, 0)

        @translate
        def _():
            for i in range(x + 1):
                y += i
            return y


class TestTranslate(unittest.TestCase):
    def test_if(self):
        mod = Module.new(__name__)
        lfoo = FooIf()(mod)

        print(mod)
        mod.verify()

        exe = CExecutor(mod)
        foo = exe.get_ctype_function(lfoo, 'int, int')
        self.assertEqual(foo(10, 20), 20 - 10)
        self.assertEqual(foo(23, 17), 23 - 17)

    def test_whileloop(self):
        mod = Module.new(__name__)
        lfoo = FooWhile()(mod)

        print(mod)
        mod.verify()

        exe = CExecutor(mod)
        foo = exe.get_ctype_function(lfoo, 'int')
        self.assertEqual(foo(10), sum(range(10+1)))
        self.assertEqual(foo(1324), sum(range(1324+1)))

    def test_forloop(self):
        mod = Module.new(__name__)
        lfoo = FooForRange()(mod)

        print(mod)
        mod.verify()

        exe = CExecutor(mod)
        foo = exe.get_ctype_function(lfoo, 'int')
        self.assertEqual(foo(10), sum(range(10+1)))
        self.assertEqual(foo(1324), sum(range(1324+1)))

if __name__ == '__main__':
    unittest.main()


########NEW FILE########
__FILENAME__ = test_vectorarith
from llvm_cbuilder import *
from llvm_cbuilder import shortnames as C
from llvm_cbuilder.translator import translate
from ctypes import *
from llvm.core import *
from llvm.passes import *
import numpy as np
import unittest
import logging
floatv4 = C.vector(C.float, 4)

class VectorArith(CDefinition):
    _name_ = 'vector_arith'
    _argtys_ = [('a', floatv4),
                ('b', floatv4),
                ('c', floatv4),]
    _retty_ = floatv4

    def body(self, a, b, c):
        '''
        Arguments
        ---------
        a, b, c -- must be vectors
        '''
        @translate
        def _(): # write like python in here
            return a * b + c

class VectorArithDriver1(CDefinition):
    _name_ = 'vector_arith_driver_1'
    _argtys_ = [('A', C.pointer(C.float)),
                ('B', C.pointer(C.float)),
                ('C', C.pointer(C.float)),
                ('D', C.pointer(C.float)),
                ('n', C.int),]

    def body(self, Aary, Bary, Cary, Dary, n):
        '''
        This version uses vector load to fetch array elements as vectors.

        '''
        vecarith = self.depends(VectorArith())
        elem_per_vec = self.constant(C.int, floatv4.count)
        with self.for_range(0, n, elem_per_vec) as (loop, i):
            # Aary[i:] offset the array at i
            a = Aary[i:].vector_load(4, align=1)  # unaligned vector load
            b = Bary[i:].vector_load(4, align=1)
            c = Cary[i:].vector_load(4, align=1)
            r = vecarith(a, b, c)
            Dary[i:].vector_store(r, align=1)
            #    self.debug(r[0], r[1], r[2], r[3])
        self.ret()


class VectorArithDriver2(CDefinition):
    _name_ = 'vector_arith_driver_2'
    _argtys_ = [('A', C.pointer(C.float)),
                ('B', C.pointer(C.float)),
                ('C', C.pointer(C.float)),
                ('D', C.pointer(C.float)),
                ('n', C.int),]

    def body(self, Aary, Bary, Cary, Dary, n):
        '''
        This version loads element of vector individually.
        This style generates scalar ld/st instead of vector ld/st.
        '''
        vecarith = self.depends(VectorArith())
        a = self.var(floatv4)
        b = self.var(floatv4)
        c = self.var(floatv4)
        elem_per_vec = self.constant(C.int, floatv4.count)
        with self.for_range(0, n, elem_per_vec) as (outer, i):
            with self.for_range(elem_per_vec) as (inner, j):
                a[j] = Aary[i + j]
                b[j] = Bary[i + j]
                c[j] = Cary[i + j]
            r = vecarith(a, b, c)
            Dary[i:].vector_store(r, align=1)
            #    self.debug(r[0], r[1], r[2], r[3])
        self.ret()



def aligned_zeros(shape, boundary=16, dtype=float, order='C'):
    '''
    Is there a better way to allocate aligned memory?
    '''
    N = np.prod(shape)
    d = np.dtype(dtype)
    tmp = np.zeros(N * d.itemsize + boundary, dtype=np.uint8)
    address = tmp.__array_interface__['data'][0]
    offset = (boundary - address % boundary) % boundary
    viewed = tmp[offset:offset + N * d.itemsize].view(dtype=d)
    return viewed.reshape(shape, order=order)

class TestVectorArith(unittest.TestCase):
    def test_vector_arith_1(self):
        self.run_and_test_udt(VectorArithDriver1(), 16) # aligned for SSE
        self.run_and_test_udt(VectorArithDriver1(), 20) # misaligned for SSE

    def test_vector_arith_2(self):
        self.run_and_test_udt(VectorArithDriver2(), 16) # aligned for SSE
        self.run_and_test_udt(VectorArithDriver2(), 20) # misaligned for SSE

    def run_and_test_udt(self, udt, align):
        module = Module.new('mod.test.vectoriarith')

        ldriver = udt(module)

        pm = PassManager.new()
        pmb = PassManagerBuilder.new()
        pmb.opt = 3
        pmb.vectorize = True
        pmb.populate(pm)
        pm.run(module)

        print(module.to_native_assembly())

        exe = CExecutor(module)

        float_p = POINTER(c_float)

        driver = exe.get_ctype_function(ldriver,
                                        None,
                                        float_p, float_p, float_p,
                                        float_p,
                                        c_int)

        # prepare for execution

        n = 4*10

        Aary = aligned_zeros(n, boundary=align, dtype=np.float32)
        Bary = aligned_zeros(n, boundary=align, dtype=np.float32)
        Cary = aligned_zeros(n, boundary=align, dtype=np.float32)
        Dary = aligned_zeros(n, boundary=align, dtype=np.float32)

        Aary[:] = range(n)
        Bary[:] = range(n, 2 * n)
        Cary[:] = range(2 * n, 3 * n)

        golden = Aary * Bary + Cary

        getptr = lambda ary: ary.ctypes.data_as(float_p)

        driver(getptr(Aary), getptr(Bary), getptr(Cary), getptr(Dary), n)

        for x, y in zip(golden, Dary):
            self.assertEqual(x, y)


if __name__ == '__main__':
    unittest.main()



########NEW FILE########
__FILENAME__ = translator
# A handy translator that converts control flow into the appropriate
# llvm_cbuilder constructs
from numba.functions import _get_ast, fix_ast_lineno
import inspect, functools, ast
import logging

logger = logging.getLogger(__name__)

def translate(func):
    # TODO use meta package
    wrapper = functools.wraps(func)
    caller_frame = inspect.currentframe().f_back
    tree = _get_ast(func)
    tree = ast.Module(body=tree.body)
    tree = ExpandControlFlow().visit(tree)
    fix_ast_lineno(tree)

    # prepare locals for execution
    local_dict = locals()
    local_dict.update(caller_frame.f_locals)
    local_dict.update(caller_frame.f_globals)

    try:
        compiled = compile(tree, '<string>', 'exec')
        return eval(compiled)
    except Exception as e:
        logger.debug(ast.dump(tree))
        from ArminRonacher import codegen # uses Armin Ronacher's codegen to debug
        # http://dev.pocoo.org/hg/sandbox/file/852a1248c8eb/ast/codegen.py
        logger.debug(codegen.to_source(tree))
        raise


_if_else_template = '''
with self.ifelse(__CONDITION__) as _ifelse_:
    with _ifelse_.then():
        __THEN__
    with _ifelse_.otherwise():
        __OTHERWISE__
'''

_while_template = '''
with self.loop() as _loop_:
    with _loop_.condition() as _setcond_:
        _setcond_(__CONDITION__)
    with _loop_.body():
        __BODY__
'''

_for_range_template = '''
with self.for_range(*__ARGS__) as (_loop_, __ITER__):
    __BODY__
'''

_return_template = 'self.ret(__RETURN__)'

_const_int_template = 'self.constant(C.int, __VALUE__)'
_const_long_template = 'self.constant(C.long, __VALUE__)'
_const_float_template = 'self.constant(C.double, __VALUE__)'

def load_template(string):
    '''
    Since ast.parse() returns a ast.Module node,
    it is more useful to trim the Module and get to the first item of body
    '''
    tree = ast.parse(string)  # return a Module
    assert isinstance(tree, ast.Module)
    return tree.body[0]       # get the first item of body

class ExpandControlFlow(ast.NodeTransformer):
    '''
    Expand control flow contructs.
    These are the most tedious thing to do in llvm_cbuilder.
    '''

    ## Use breadcumb to track parent nodes
    #    def __init__(self):
    #        self.breadcumb = []
    #
    #    def visit(self, node):
    #        self.breadcumb.append(node)
    #        try:
    #            return super(ExpandControlFlow, self).visit(node)
    #        finally:
    #            self.breadcumb.pop()
    #
    #    @property
    #    def parent(self):
    #        return self.breadcumb[-2]

    def visit_If(self, node):
        mapping = {
            '__CONDITION__' : node.test,
            '__THEN__'      : node.body,
            '__OTHERWISE__' : node.orelse,
        }

        ifelse = load_template(_if_else_template)
        ifelse = MacroExpander(mapping).visit(ifelse)
        newnode = self.generic_visit(ifelse)
        return newnode

    def visit_While(self, node):
        mapping = {
            '__CONDITION__' : node.test,
            '__BODY__'      : node.body,
        }
        whileloop = load_template(_while_template)
        whileloop = MacroExpander(mapping).visit(whileloop)
        newnode = self.generic_visit(whileloop)
        return newnode

    def visit_For(self, node):
        try:
            if node.iter.func.id not in ['range', 'xrange']:
                return node
        except AttributeError:
            return node

        mapping = {
            '__ITER__' : node.target,
            '__BODY__' : node.body,
            '__ARGS__' : ast.Tuple(elts=node.iter.args, ctx=ast.Load()),
        }

        forloop = load_template(_for_range_template)
        forloop = MacroExpander(mapping).visit(forloop)
        newnode = self.generic_visit(forloop)
        return newnode

    def visit_Return(self, node):
        mapping = {'__RETURN__' : node.value}
        ret = load_template(_return_template)
        repl = MacroExpander(mapping).visit(ret)
        return repl

    def visit_Num(self, node):
        '''convert immediate values
        '''
        typemap = {
            int   : _const_int_template,
            long  : _const_long_template,  # TODO: disable long for py3
            float : _const_float_template,
        }

        template = load_template(typemap[type(node.n)])

        mapping = {
            '__VALUE__' : node,
        }
        constant = MacroExpander(mapping).visit(template).value
        newnode = constant
        return newnode

class MacroExpander(ast.NodeTransformer):
    def __init__(self, mapping):
        self.mapping = mapping

    def visit_With(self, node):
        '''
        Expand X in the following:
            with blah:
                X
        Nothing should go before or after X.
        X must be a list of nodes.
        '''
        if (len(node.body)==1 # the body of
          and isinstance(node.body[0], ast.Expr)
          and isinstance(node.body[0].value, ast.Name)):
            try:
                repl = self.mapping.pop(node.body[0].value.id)
            except KeyError:
                pass
            else:
                old = node.body[0]
                node.body = repl

        return self.generic_visit(node) # recursively apply expand all macros

    def visit_Name(self, node):
        '''
        Expand all Name node to simple value
        '''

        try:
            repl = self.mapping.pop(node.id)
        except KeyError:
            pass
        else:
            if repl is not None and not isinstance(repl, list):
                return repl
        return node



########NEW FILE########
__FILENAME__ = call-jit-ctypes
#!/usr/bin/env python

from llvm.core import Module,Type,Builder
from llvm.ee import ExecutionEngine
import llvm.core

import ctypes

import logging
import unittest

class TestCallJITCtypes(unittest.TestCase):
    def test_jit_ctypes(self):

        # This example demonstrates calling an LLVM defined function using
        # ctypes. It illustrates the common C pattern of having an output
        # variable in the argument list to the function. The function also
        # returns an error code upon exit.

        # setup llvm types
        ty_errcode = Type.int()
        ty_float = Type.float()
        ty_ptr_float = Type.pointer(Type.float())
        ty_func = Type.function(ty_errcode, [ty_float, ty_float, ty_ptr_float])

        # setup ctypes types
        ct_errcode = ctypes.c_int
        ct_float = ctypes.c_float
        ct_ptr_float = ctypes.POINTER(ct_float)
        ct_argtypes = [ct_float, ct_float, ct_ptr_float]

        # generate the function using LLVM
        my_module = Module.new('my_module')

        mult = my_module.add_function(ty_func, "mult")
        mult.args[0].name = "a"
        mult.args[1].name = "b"
        mult.args[2].name = "out"
        # add nocapture to output arg
        mult.args[2].add_attribute(llvm.core.ATTR_NO_CAPTURE)
        mult.does_not_throw = True # add nounwind attribute to function

        bb = mult.append_basic_block("entry")
        builder = Builder.new(bb)
        tmp = builder.fmul( mult.args[0], mult.args[1] )
        builder.store( tmp, mult.args[2] )
        builder.ret(llvm.core.Constant.int(ty_errcode, 0))

        # print the created module
        logging.debug(my_module)

        # compile the function
        ee = ExecutionEngine.new(my_module)

        # let ctypes know about the function
        func_ptr_int = ee.get_pointer_to_function( mult )
        FUNC_TYPE = ctypes.CFUNCTYPE(ct_errcode, *ct_argtypes)
        py_mult = FUNC_TYPE(func_ptr_int)

        # now run the function, calling via ctypes
        output_value = ct_float(123456.0)
        errcode = py_mult( 2.0, 3.0, ctypes.byref(output_value) )

        self.assertEqual(errcode, 0, msg='unexpected error')

        self.assertEqual(output_value.value, 6.0)

if __name__=='__main__':
    unittest.main()


########NEW FILE########
__FILENAME__ = clonemodule
#!/usr/bin/env python

# Import the llvm-py modules.
from llvm import *
from llvm.core import *

import logging
import unittest


class TestCloneModule(unittest.TestCase):
    def test_example(self):
        my_module = Module.new('my_module')

        ty_int = Type.int()   # by default 32 bits

        ty_func = Type.function(ty_int, [ty_int, ty_int])

        f_sum = my_module.add_function(ty_func, "sum")

        self.assertEqual(str(f_sum).strip(), 'declare i32 @sum(i32, i32)')

        f_sum.args[0].name = "a"
        f_sum.args[1].name = "b"

        bb = f_sum.append_basic_block("entry")

        builder = Builder.new(bb)

        tmp = builder.add(f_sum.args[0], f_sum.args[1], "tmp")

        self.assertEqual(str(tmp).strip(), '%tmp = add i32 %a, %b')

        builder.ret(tmp)

        cloned = my_module.clone()

        self.assertTrue(id(cloned) != id(my_module))
        self.assertTrue(str(cloned) == str(my_module))
        self.assertTrue(cloned == my_module)



if __name__ == '__main__':
    unittest.main()


########NEW FILE########
__FILENAME__ = constants
#! /usr/bin/env python
'''
Test and stress Constants.
'''
import unittest
import logging

from llvm.core import *
from llvm.ee import *
from ctypes import *


# logging.basicConfig(level=logging.DEBUG)

def _build_test_module(datatype, constants):
    mod = Module.new('module_test_const_%s' % datatype)
    fnty_callback = Type.function(Type.void(), [datatype])
    fnty_subject = Type.function(Type.void(), [Type.pointer(fnty_callback)])
    func_subject = mod.add_function(fnty_subject, 'test_const_%s' % datatype)

    bb_entry = func_subject.append_basic_block('entry')
    builder = Builder.new(bb_entry)

    for k in constants:
        builder.call(func_subject.args[0], [k])

    builder.ret_void()

    func_subject.verify()

    return mod, func_subject

def _build_test_module_array(datatype, constants):
    mod = Module.new('module_test_const_%s' % datatype)
    fnty_callback = Type.function(Type.void(), [datatype])
    fnty_subject = Type.function(Type.void(), [Type.pointer(fnty_callback)])
    func_subject = mod.add_function(fnty_subject, 'test_const_%s' % datatype)

    bb_entry = func_subject.append_basic_block('entry')
    builder = Builder.new(bb_entry)


    for k in constants:
        ptr = builder.alloca(k.type)
        builder.store(k, ptr)
        builder.call(func_subject.args[0],
                     [builder.gep(ptr, [Constant.int(Type.int(), 0)]*2)])

    builder.ret_void()

    func_subject.verify()

    return mod, func_subject

def _build_test_module_struct(datatype, constants):
    mod = Module.new('module_test_const_%s' % datatype)
    fnty_callback = Type.function(Type.void(), [datatype])
    fnty_subject = Type.function(Type.void(), [Type.pointer(fnty_callback)])
    func_subject = mod.add_function(fnty_subject, 'test_const_%s' % datatype)

    bb_entry = func_subject.append_basic_block('entry')
    builder = Builder.new(bb_entry)

    for k in constants:
        ptr = builder.alloca(k.type)
        builder.store(k, ptr)
        builder.call(func_subject.args[0], [ptr])

    builder.ret_void()

    func_subject.verify()

    return mod, func_subject

class TestConstants(unittest.TestCase):
    def test_const_int(self):
        from random import randint
        values = [0, -1, 1, 0xfffffffe, 0xffffffff, 0x100000000]
        values += [randint(0, 0xffffffff) for x in range(100)]

        constant_list = map(lambda X: Constant.int(Type.int(), X), values)
        mod, func_subject = _build_test_module(Type.int(), constant_list)

        # done function generation
        logging.debug(func_subject)

        # prepare execution
        ee = ExecutionEngine.new(mod)

        cf_callback = CFUNCTYPE(None, c_uint32)
        cf_test = CFUNCTYPE(None, cf_callback)

        test_subject = cf_test(ee.get_pointer_to_function(func_subject))

        # setup callback
        results = []
        def callback(value):
            results.append(value)

        test_subject(cf_callback(callback))

        # check result
        for result, golden in zip(results, values):
            self.assertEqual(result, golden & 0xffffffff)

    def test_const_float(self):
        from random import random
        values = [0., 1., -1.] + [random() for x in range(100)]

        constant_list = map(lambda X: Constant.real(Type.float(), X), values)
        mod, func_subject = _build_test_module(Type.float(), constant_list)

        # done function generation
        logging.debug(func_subject)

        # prepare execution
        ee = ExecutionEngine.new(mod)

        cf_callback = CFUNCTYPE(None, c_float)
        cf_test = CFUNCTYPE(None, cf_callback)

        test_subject = cf_test(ee.get_pointer_to_function(func_subject))

        # setup callback
        results = []
        def callback(value):
            results.append(value)

        test_subject(cf_callback(callback))

        # check result
        for result, golden in zip(results, values):
            if golden == 0:
                self.assertEqual(result, golden)
            else:
                self.assert_(abs(result-golden)/golden < 1e-7)

    def test_const_double(self):
        from random import random
        values = [0., 1., -1.] + [random() for x in range(100)]

        constant_list = map(lambda X: Constant.real(Type.double(), X), values)
        mod, func_subject = _build_test_module(Type.double(), constant_list)

        # done function generation
        logging.debug(func_subject)

        # prepare execution
        ee = ExecutionEngine.new(mod)

        cf_callback = CFUNCTYPE(None, c_double)
        cf_test = CFUNCTYPE(None, cf_callback)

        test_subject = cf_test(ee.get_pointer_to_function(func_subject))

        # setup callback
        results = []
        def callback(value):
            results.append(value)

        test_subject(cf_callback(callback))

        # check result
        for result, golden in zip(results, values):
            self.assertEqual(result, golden)

    def test_const_string(self):
        values = ["hello", "world", "", "\n"]

        constant_list = map(Constant.stringz, values)
        mod, func_subject = _build_test_module_array(Type.pointer(Type.int(8)),
                                                     constant_list)

        # done function generation
        logging.debug(func_subject)

        # prepare execution
        ee = ExecutionEngine.new(mod)

        cf_callback = CFUNCTYPE(None, c_char_p)
        cf_test = CFUNCTYPE(None, cf_callback)

        test_subject = cf_test(ee.get_pointer_to_function(func_subject))

        # setup callback
        results = []
        def callback(value):
            results.append(value)

        test_subject(cf_callback(callback))

        # check result
        for result, golden in zip(results, values):
            self.assertEqual(result.decode(), golden)

    def test_const_struct(self):
        from random import randint, random
        values = [
            (0, 0., 0.),
            (-1, -1., -1.),
            (1, 1., 1.),
        ] + [(randint(0, 0xffffffff), random(), random()) for _ in range(100)]

        struct_type = Type.struct([Type.int(), Type.float(), Type.double()])

        def map_constant(packed_values):
            vi, vf, vd = packed_values
            return Constant.struct([
                     Constant.int(Type.int(), vi),
                     Constant.real(Type.float(), vf),
                     Constant.real(Type.double(), vd),
                   ])

        constant_list = map(map_constant, values)

        mod, func_subject = _build_test_module_struct(Type.pointer(struct_type),
                                                      constant_list)

        # done function generation
        logging.debug(func_subject)

        # prepare execution
        ee = ExecutionEngine.new(mod)

        class c_struct_type(Structure):
            _fields_ = [ ('vi', c_uint32),
                         ('vf', c_float),
                         ('vd', c_double), ]

            def __iter__(self):
                return iter([self.vi, self.vf, self.vd])

        cf_callback = CFUNCTYPE(None, POINTER(c_struct_type))
        cf_test = CFUNCTYPE(None, cf_callback)

        test_subject = cf_test(ee.get_pointer_to_function(func_subject))

        # setup callback
        results = []
        def callback(value):
            results.append(tuple(value[0]))

        test_subject(cf_callback(callback))

        # check result
        for result, golden in zip(results, values):
            self.assertEqual(result[0], golden[0] & 0xffffffff)
            if golden[1] == 0:
                self.assertEqual(result[1], golden[1])
            else:
                self.assert_(abs(result[1]-golden[1])/golden[1] < 1e-7)
            self.assertEqual(result[2], golden[2])

    def test_const_vector(self):
        from random import randint
        randgen = lambda: randint(0, 0xffffffff)
        values = [
            (0, 0, 0, 0),
            (1, 1, 1, 1),
            (-1, -1, -1, -1),
        ] + [ (randgen(), randgen(), randgen(), randgen()) for _ in range(100) ]

        def map_constant(packed_values):
            consts = [ Constant.int(Type.int(), i) for i in packed_values ]
            return Constant.vector(consts)

        constant_list = map(map_constant, values)
        mod, func_subject = _build_test_module_array(Type.pointer(Type.int()),
                                                     constant_list)

        # done function generation
        logging.debug(func_subject)

        # prepare execution
        ee = ExecutionEngine.new(mod)

        cf_callback = CFUNCTYPE(None, POINTER(c_uint32))
        cf_test = CFUNCTYPE(None, cf_callback)

        test_subject = cf_test(ee.get_pointer_to_function(func_subject))

        # setup callback
        results = []
        def callback(value):
            results.append(tuple(value[0:4]))

        test_subject(cf_callback(callback))

        # check result
        for result, golden in zip(results, values):
            self.assertEqual(result,
                             tuple(map(lambda X: X & 0xffffffff, golden)))


if __name__ == '__main__':
    unittest.main()


########NEW FILE########
__FILENAME__ = example-disassemble
import llvm

if llvm.version >= (3, 4):

    from llvm.target import TargetMachine
    from llvm import mc
    from llvm.mc import Disassembler

    llvm.target.initialize_all()

    def print_instructions(dasm, bs, align=None):
        branch_properties = [
            'is_branch',
            'is_cond_branch',
            'is_uncond_branch',
            'is_indirect_branch',
            'is_call',
            'is_return',
            'is_terminator',
            'is_barrier'
        ]

        print("print instructions")
        for (addr, data, inst) in dasm.decode(bs, 0x4000, align):

            if inst is None:
                print("\t0x%x => (bad)" % (addr))
            else:
                ops = ", ".join(map(lambda op: repr(op), inst.operands()))
                if isinstance(inst, mc.BadInstr):
                    print("\t0x%x (bad) ops = %s" % (addr, ops))
                else:
                    print("\t0x%x ops = %s" % (addr, ops))

                print("\t\topcode = 0x%x, flags = 0x%x, tsflags = 0x%x" % (inst.opcode, inst.flags, inst.ts_flags))
                for line in str(inst).split("\n"):
                    print("\t\t%-24s %s" % ("".join(map(lambda b: "%02x" % b, data))+":", line.strip()))

                for bp in branch_properties:
                    print("\t\t%-22s%r" % (bp+":", getattr(inst, bp)() ))


    x86 = TargetMachine.x86()
    print("x86: LE=%s" % x86.is_little_endian())
    print_instructions(Disassembler(x86), "\x01\xc3\xc3\xcc\x90")

    x86_64 = TargetMachine.x86_64()
    print("x86-64: LE=%s" % x86_64.is_little_endian())
    print_instructions(Disassembler(x86_64), "\x55\x48\x89\xe8")

    arm = TargetMachine.arm()
    print("arm: LE=%s" % arm.is_little_endian())
    code = [
        "\xe9\x2d\x48\x00",
        "\xea\x00\x00\x06",
        "\xe2\x4d\xd0\x20",
        "\xe2\x8d\xb0\x04",
        "\xe5\x0b\x00\x20",
        "\x03\x30\x22\xe0", #bad instruction to test alignment
        "\x73\x20\xef\xe6", #bad instruction to test alignment
        "\x18\x00\x1b\xe5",
        "\x10\x30\xa0\xe3"
    ]
    print_instructions(Disassembler(arm), "".join(map(lambda s: s[::-1], code)), 4)

########NEW FILE########
__FILENAME__ = example-instruction-info
import llvm.target
from llvmpy import api, extra


def main():
    if llvm.version < (3, 4):
        return 0

    triple = "i386--"

    print("init start")
    api.llvm.InitializeAllTargets()
    api.llvm.InitializeAllTargetInfos()
    api.llvm.InitializeAllTargetMCs()
    api.llvm.InitializeAllAsmParsers()
    api.llvm.InitializeAllAsmPrinters()
    api.llvm.InitializeAllDisassemblers()
    print("init done\n")

    tm = llvm.target.TargetMachine.x86()
    if not tm:
        print("error: failed to lookup target x86 \n")
        return 1

    print("created target machine\n")

    MII = tm.instr_info
    if not MII:
        print("error: no instruction info for target " + triple + "\n")
        return 1

    print("created instr info\n")
    MID = MII.get(919) #int3
    print("INT3(%d): flags=0x%x, tsflags=0x%x\n" % (MID.getOpcode(), MID.getFlags(), MID.TSFlags))

    return 0

exit(main())

########NEW FILE########
__FILENAME__ = example-jit
#!/usr/bin/env python

# Import the llvm-py modules.
from llvm import *
from llvm.core import *
from llvm.ee import *          # new import: ee = Execution Engine

import logging
import unittest


class TestExampleJIT(unittest.TestCase):
    def test_example_jit(self):
        # Create a module, as in the previous example.
        my_module = Module.new('my_module')
        ty_int = Type.int()   # by default 32 bits
        ty_func = Type.function(ty_int, [ty_int, ty_int])
        f_sum = my_module.add_function(ty_func, "sum")
        f_sum.args[0].name = "a"
        f_sum.args[1].name = "b"
        bb = f_sum.append_basic_block("entry")
        builder = Builder.new(bb)
        tmp = builder.add(f_sum.args[0], f_sum.args[1], "tmp")
        builder.ret(tmp)

        # Create an execution engine object. This will create a JIT compiler
        # on platforms that support it, or an interpreter otherwise.
        ee = ExecutionEngine.new(my_module)

        # The arguments needs to be passed as "GenericValue" objects.
        arg1_value = 100
        arg2_value = 42

        arg1 = GenericValue.int(ty_int, arg1_value)
        arg2 = GenericValue.int(ty_int, arg2_value)

        # Now let's compile and run!
        retval = ee.run_function(f_sum, [arg1, arg2])

        # The return value is also GenericValue. Let's print it.
        logging.debug("returned %d", retval.as_int())

        self.assertEqual(retval.as_int(), (arg1_value + arg2_value))


if __name__ == '__main__':
    unittest.main()


########NEW FILE########
__FILENAME__ = example
#!/usr/bin/env python

# Import the llvm-py modules.
from llvm import *
from llvm.core import *

import logging
import unittest


class TestExample(unittest.TestCase):
    def test_example(self):
        # Create an (empty) module.
        my_module = Module.new('my_module')

        # All the types involved here are "int"s. This type is represented
        # by an object of the llvm.core.Type class:
        ty_int = Type.int()   # by default 32 bits

        # We need to represent the class of functions that accept two integers
        # and return an integer. This is represented by an object of the
        # function type (llvm.core.FunctionType):
        ty_func = Type.function(ty_int, [ty_int, ty_int])

        # Now we need a function named 'sum' of this type. Functions are not
        # free-standing (in llvm-py); it needs to be contained in a module.
        f_sum = my_module.add_function(ty_func, "sum")

        self.assertEqual(str(f_sum).strip(), 'declare i32 @sum(i32, i32)')

        # Let's name the function arguments as 'a' and 'b'.
        f_sum.args[0].name = "a"
        f_sum.args[1].name = "b"

        # Our function needs a "basic block" -- a set of instructions that
        # end with a terminator (like return, branch etc.). By convention
        # the first block is called "entry".
        bb = f_sum.append_basic_block("entry")

        # Let's add instructions into the block. For this, we need an
        # instruction builder:
        builder = Builder.new(bb)

        # OK, now for the instructions themselves. We'll create an add
        # instruction that returns the sum as a value, which we'll use
        # a ret instruction to return.
        tmp = builder.add(f_sum.args[0], f_sum.args[1], "tmp")

        self.assertEqual(str(tmp).strip(), '%tmp = add i32 %a, %b')

        builder.ret(tmp)

        # We've completed the definition now! Let's see the LLVM assembly
        # language representation of what we've created:
        logging.debug(my_module)



if __name__ == '__main__':
    unittest.main()


########NEW FILE########
__FILENAME__ = inlineasm
#!/usr/bin/env python

# Import the llvm-py modules.
from llvm import *
from llvm.core import *
from llvm.tests.support import TestCase

import logging
import unittest


class TestInlineAsm(TestCase):
    def test_inline_asm(self):
        mod = Module.new(__name__)
        fnty = Type.function(Type.int(), [Type.int()])
        fn = mod.add_function(fnty, name='test_inline_asm')
        builder = Builder.new(fn.append_basic_block('entry'))

        iaty = Type.function(Type.int(), [Type.int()])
        inlineasm = InlineAsm.get(iaty,  "bswap $0", "=r,r")
        self.assertIn('asm "bswap $0", "=r,r"', str(inlineasm))
        builder.ret(builder.call(inlineasm, [fn.args[0]]))
        print(fn)

if __name__ == '__main__':
    unittest.main()


########NEW FILE########
__FILENAME__ = JITTutorial1
#!/usr/bin/env python

from llvm.core import *

# create a module
module = Module.new ("tut1")

# create a function type taking 3 32-bit integers, return a 32-bit integer
ty_int = Type.int (32)
func_type = Type.function (ty_int, (ty_int,)*3)

# create a function of that type
mul_add = Function.new (module, func_type, "mul_add")
mul_add.calling_convention = CC_C
x = mul_add.args[0]; x.name = "x"
y = mul_add.args[1]; y.name = "y"
z = mul_add.args[2]; z.name = "z"

# implement the function

# new block
blk = mul_add.append_basic_block ("entry")

# IR builder
bldr = Builder.new (blk)
tmp_1 = bldr.mul (x, y, "tmp_1")
tmp_2 = bldr.add (tmp_1, z, "tmp_2")

bldr.ret (tmp_2)

print(module)

########NEW FILE########
__FILENAME__ = JITTutorial2
#!/usr/bin/env python

from llvm.core import *

# create a module
module = Module.new ("tut2")

# create a function type taking 2 integers, return a 32-bit integer
ty_int    = Type.int (32)
func_type = Type.function (ty_int, (ty_int, ty_int))

# create a function of that type
gcd = Function.new (module, func_type, "gcd")

# name function args
x = gcd.args[0]; x.name = "x"
y = gcd.args[1]; y.name = "y"

# implement the function

# blocks...
entry = gcd.append_basic_block ("entry")
ret   = gcd.append_basic_block ("return")
cond_false   = gcd.append_basic_block ("cond_false")
cond_true    = gcd.append_basic_block ("cond_true")
cond_false_2 = gcd.append_basic_block ("cond_false_2")

# create a llvm::IRBuilder
bldr = Builder.new (entry)
x_eq_y = bldr.icmp (IPRED_EQ, x, y, "tmp")
bldr.cbranch (x_eq_y, ret, cond_false)

bldr.position_at_end (ret)
bldr.ret(x)

bldr.position_at_end (cond_false)
x_lt_y = bldr.icmp (IPRED_ULT, x, y, "tmp")
bldr.cbranch (x_lt_y, cond_true, cond_false_2)

bldr.position_at_end (cond_true)
y_sub_x = bldr.sub (y, x, "tmp")
recur_1 = bldr.call (gcd, (x, y_sub_x,), "tmp")
bldr.ret (recur_1)

bldr.position_at_end (cond_false_2)
x_sub_y = bldr.sub (x, y, "x_sub_y")
recur_2 = bldr.call (gcd, (x_sub_y, y,), "tmp")
bldr.ret (recur_2)

print(module)

########NEW FILE########
__FILENAME__ = loopvectorize
from llvm.core import *
from llvm.passes import *
from llvm.ee import *
import llvm
from llvm.tests.support import TestCase
from os.path import dirname, join as join_path


import unittest
import re

class TestLoopVectorizer(TestCase):
    def test_loop_vectorizer(self):
        if llvm.version <= (3, 1):
            return # SKIP

        re_vector = re.compile("<\d+ x \w+>")

        tm = TargetMachine.new(opt=3)

        # Build passes
        pm = build_pass_managers(tm, opt=3, loop_vectorize=True, fpm=False).pm

        # Load test module
        asmfile = join_path(dirname(__file__), 'loopvectorize.ll')
        with open(asmfile) as asm:
            mod = Module.from_assembly(asm)

        before = str(mod)

        pm.run(mod)

        after = str(mod)
        self.assertNotEqual(after, before)

        before_vectors = re_vector.findall(before)
        self.assertFalse(before_vectors)
        after_vectors = re_vector.findall(after)
        self.assertLess(len(before_vectors), len(after_vectors))


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = malloc
from llvm.core import *

def test():
    m = Module.new('sdf')
    f = m.add_function(Type.function(Type.void(), []), 'foo')
    bb = f.append_basic_block('entry')
    b = Builder.new(bb)
    alloc = b.malloc(Type.int(), 'ha')
    inst = b.free(alloc)
    alloc = b.malloc_array(Type.int(), Constant.int(Type.int(), 10), 'hee')
    inst = b.free(alloc)
    b.ret_void()
    print(m)

if __name__ == '__main__':
    test()

########NEW FILE########
__FILENAME__ = metadata
from __future__ import print_function

import unittest
from llvm.tests.support import TestCase
from llvm.core import *

class TestMetaData(TestCase):
    def test_metadata_get(self):
        module = Module.new('test_metadata')
        md = MetaData.get(module, [Constant.int(Type.int(), 1234)])

    def test_meta_load_nt(self):
        module = Module.new('test_meta_load_nt')
        func = module.add_function(Type.function(Type.void(), []),
                                   name='test_load_nt')
        bldr = Builder.new(func.append_basic_block('entry'))
        addr = Constant.int(Type.int(), 0xdeadbeef)
        loadinst = bldr.load(bldr.inttoptr(addr, Type.pointer(Type.int(8))))

        md = MetaData.get(module, [Constant.int(Type.int(), 1)])
        loadinst.set_metadata('nontemporal', md)

        bldr.ret_void()
        module.verify()

        self.assertIn('!nontemporal', str(loadinst))

    def test_meta_load_invariant(self):
        module = Module.new('test_meta_load_invariant')
        func = module.add_function(Type.function(Type.void(), []),
                                   name='test_load_invariant')
        bldr = Builder.new(func.append_basic_block('entry'))
        addr = Constant.int(Type.int(), 0xdeadbeef)
        loadinst = bldr.load(bldr.inttoptr(addr, Type.pointer(Type.int(8))),
                             invariant=True)

        bldr.ret_void()
        module.verify()

        self.assertIn('!invariant.load', str(loadinst))

    def test_tbaa_metadata(self):
        '''just a simple excerise of the code
        '''
        mod = Module.new('test_tbaa_metadata')
        root = MetaData.get(mod, [MetaDataString.get(mod, "root")])
        MetaData.add_named_operand(mod, 'tbaa', root)

        ops = [MetaDataString.get(mod, "int"), root]
        md1 = MetaData.get(mod, ops)
        MetaData.add_named_operand(mod, 'tbaa', md1)
        print(md1)

        ops = [MetaDataString.get(mod, "const float"),
               root,
               Constant.int(Type.int(64), 1)]

        md2 = MetaData.get(mod, ops)
        MetaData.add_named_operand(mod, 'tbaa', md2)
        print(md2)

        print(mod)


if __name__ == '__main__':
    unittest.main()


########NEW FILE########
__FILENAME__ = native_asm
#!/usr/bin/env python

from llvm import *
from llvm.core import *
import sys, os
import unittest

class TestNativeAsm(unittest.TestCase):
    def test_asm(self):
        # create a module
        m = Module.new('module1')

        foo = m.add_function(Type.function(Type.int(), [Type.int(), Type.int()]), name="foo")

        bldr = Builder.new(foo.append_basic_block('entry'))
        x = bldr.add(foo.args[0], foo.args[1])
        bldr.ret(x)

        att_syntax = m.to_native_assembly()
        os.environ["LLVMPY_OPTIONS"] = "-x86-asm-syntax=intel"
        parse_environment_options(sys.argv[0], "LLVMPY_OPTIONS")
        intel_syntax = m.to_native_assembly()

        print(att_syntax)
        print(intel_syntax)
        self.assertNotEqual(att_syntax, intel_syntax)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = operands
#!/usr/bin/env python

# Tests accessing of instruction operands.
import sys
import logging
import unittest

from llvm.core import *
try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO

m = None

#===----------------------------------------------------------------------===

# implement a test function
test_module = """
define i32 @prod(i32, i32) {
entry:
        %2 = mul i32 %0, %1
        ret i32 %2
}

define i32 @test_func(i32, i32, i32) {
entry:
        %tmp1 = call i32 @prod(i32 %0, i32 %1)
        %tmp2 = add i32 %tmp1, %2
        %tmp3 = add i32 %tmp2, 1
        ret i32 %tmp3
}
"""

class TestOperands(unittest.TestCase):

    def test_operands(self):
        m = Module.from_assembly(StringIO(test_module))
        logging.debug("-"*60)
        logging.debug(m)
        logging.debug("-"*60)

        test_func = m.get_function_named("test_func")
        prod      = m.get_function_named("prod")

        #===-----------------------------------------------------------===
        # test operands


        i1 = test_func.basic_blocks[0].instructions[0]
        i2 = test_func.basic_blocks[0].instructions[1]

        logging.debug("Testing User.operand_count ..")

        self.assertEqual(i1.operand_count, 3)
        self.assertEqual(i2.operand_count, 2)

        logging.debug("Testing User.operands ..")

        self.assert_(i1.operands[-1] is prod)
        self.assert_(i1.operands[0] is test_func.args[0])
        self.assert_(i1.operands[1] is test_func.args[1])
        self.assert_(i2.operands[0] is i1)
        self.assert_(i2.operands[1] is test_func.args[2])

        self.assertEqual(len(i1.operands), 3)
        self.assertEqual(len(i2.operands), 2)

        #===-----------------------------------------------------------===
        # show test_function

        logging.debug("Examining test_function `test_test_func':")

        idx = 1
        for inst in test_func.basic_blocks[0].instructions:
            logging.debug("Instruction #%d:", idx)
            logging.debug("  operand_count = %d", inst.operand_count)
            logging.debug("  operands:")
            oidx = 1
            for op in inst.operands:
                logging.debug("    %d: %s", oidx, repr(op))
                oidx += 1
            idx += 1

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = pass
from llvm.core import *
from llvm.passes import *
from llvm.ee import *
import llvm
import unittest

class TestPass(unittest.TestCase):
    def test_execerise_pass_api(self):
        # Test passes
        ps = Pass.new(PASS_DOT_DOM_ONLY)
        self.assertEqual(PASS_DOT_DOM_ONLY, ps.name)
        self.assertTrue(len(ps.description))

        ps = Pass.new(PASS_INLINE)
        self.assertEqual(PASS_INLINE, ps.name)
        self.assertTrue(len(ps.description))

        # Test target specific passes
        pm = PassManager.new()
        pm.add(ps)
        pm.add(TargetData.new("e-p:64:64:64-i1:8:8-i8:8:8-i16:16:16-i32:32:32-i64:64:64-f32:32:32-f64:64:64-v64:64:64-v128:128:128-a0:0:64-s0:64:64-f80:128:128-n8:16:32:64-S128"))

        tm = TargetMachine.new()

        tli = TargetLibraryInfo.new(tm.triple)
        self.assertFalse(tli.name)
        self.assertTrue(tli.description)
        pm.add(tli)

        if llvm.version >= (3, 2) and llvm.version < (3, 3):
            tti = TargetTransformInfo.new(tm)
            self.assertFalse(tti.name)
            self.assertTrue(tti.description)

            pm.add(tti)

        pmb = PassManagerBuilder.new()
        pmb.opt_level = 3
        pmb.loop_vectorize = True

        pmb.populate(pm)



if __name__ == '__main__':
    unittest.main()


########NEW FILE########
__FILENAME__ = target_info
from llvmpy.api import llvm;
llvm.InitializeAllTargets()
llvm.InitializeAllTargetInfos()
llvm.InitializeAllTargetMCs()
llvm.InitializeAllAsmPrinters()
llvm.InitializeAllDisassemblers()
llvm.InitializeAllAsmParsers()

mthds = (
    ("description:",            "getShortDescription"),
    ("has JIT:",                "hasJIT"             ),
    ("has target machine:",     "hasTargetMachine"   ),
    ("has asm backend:",        "hasMCAsmBackend"    ),
    ("has asm parser:",         "hasMCAsmParser"     ),
    ("has asm printer:",        "hasAsmPrinter"      ),
    ("has disassembler:",       "hasMCDisassembler"  ),
    ("has inst printer:",       "hasMCInstPrinter"   ),
    ("has code emitter:",       "hasMCCodeEmitter"   ),
    ("has object streamer:",    "hasMCObjectStreamer"),
    ("has asm streamer:",       "hasAsmStreamer"     )
)

for target in llvm.TargetRegistry.targetsList():
    print("target %s" % target.getName())
    fmt = "%3s%-25s%r"
    for (desc, mthd) in mthds:
        print(fmt % ("", desc, getattr(target, mthd)()))

    print("")


########NEW FILE########
__FILENAME__ = tbaa
from llvm.core import *
from llvm.tbaa import *
from llvm.tests.support import TestCase
import unittest

class TestTBAABuilder(TestCase):
    def test_tbaa_builder(self):
        mod = Module.new('test_tbaa_builder')
        fty = Type.function(Type.void(), [Type.pointer(Type.float())])
        foo = mod.add_function(fty, 'foo')
        bb = foo.append_basic_block('entry')
        bldr = Builder.new(bb)

        tbaa = TBAABuilder.new(mod, "tbaa.root")
        float = tbaa.get_node('float', const=False)
        const_float = tbaa.get_node('const float', float, const=True)


        tbaa = TBAABuilder.new(mod, "tbaa.root")
        old_const_float = const_float
        del const_float

        const_float = tbaa.get_node('const float', float, const=True)

        self.assertIs(old_const_float, const_float)

        ptr = bldr.load(foo.args[0])
        ptr.set_metadata('tbaa', const_float)


        bldr.ret_void()
        print(mod)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test
#!/usr/bin/env python

# watch out for uncollected objects
import gc

import unittest, sys, logging

from llvm import *
from llvm.core import *
from llvm.tests.support import TestCase

class TestModule(TestCase):

    def setUp(self):
        pass

    def testdata_layout(self):
        """Data layout property."""
        m = Module.new("test2.1")
        self.assertEqual(m.data_layout, '')
        m.data_layout = 'some_value'
        self.assertEqual(m.data_layout, 'some_value')
        reqd = '; ModuleID = \'test2.1\'\ntarget datalayout = "some_value"\n'
        self.assertEqual(str(m), reqd)


    def testtarget(self):
        """Target property."""
        m = Module.new("test3.1")
        self.assertEqual(m.target, '')
        m.target = 'some_value'
        self.assertEqual(m.target, 'some_value')
        reqd = '; ModuleID = \'test3.1\'\ntarget triple = "some_value"\n'
        self.assertEqual(str(m), reqd)

    # Type system is rewritten in LLVM 3.0.
    # Only named StructType is supported.
    # See http://blog.llvm.org/2011/11/llvm-30-type-system-rewrite.html
    #
    #    def testtype_name(self):
    #        """Type names."""
    #        m = Module.new("test4.1")
    #        r = m.add_type_name("typename41", Type.int())
    #        self.assertEqual(r, 0)
    #        r = m.add_type_name("typename41", Type.int())
    #        self.assertEqual(r, 1)
    #        reqd = "; ModuleID = 'test4.1'\n\n%typename41 = type i32\n"
    #        self.assertEqual(str(m), reqd)
    #        r = m.delete_type_name("typename41")
    #        reqd = "; ModuleID = 'test4.1'\n"
    #        self.assertEqual(str(m), reqd)
    #        r = m.delete_type_name("no such name") # nothing should happen
    #        reqd = "; ModuleID = 'test4.1'\n"
    #        self.assertEqual(str(m), reqd)

    def testtype_name(self):
        m = Module.new("test4.1")
        struct = Type.struct([Type.int(), Type.int()], name="struct.two.int")
        self.assertEqual(struct.name, "struct.two.int")
        got_struct = m.get_type_named(struct.name)
        self.assertEqual(got_struct.name, struct.name)

        self.assertEqual(got_struct.element_count, struct.element_count)
        self.assertEqual(len(struct.elements), struct.element_count)

        self.assertEqual(struct.elements, got_struct.elements)
        for elty in struct.elements:
            self.assertEqual(elty, Type.int())

        # rename identified type
        struct.name = 'new_name'
        self.assertEqual(struct.name, 'new_name')
        self.assertIs(m.get_type_named("struct.two.int"), None)

        self.assertEqual(got_struct.name, struct.name)

        # remove identified type
        struct.name = ''

        self.assertIs(m.get_type_named("struct.two.int"), None)
        self.assertIs(m.get_type_named("new_name"), None)

        # another name

        struct.name = 'another.name'
        self.assertEqual(struct.name, 'another.name')
        self.assertEqual(got_struct.name, struct.name)

    def testglobal_variable(self):
        """Global variables."""
        m = Module.new("test5.1")
        t = Type.int()
        gv = m.add_global_variable(t, "gv")
        self.assertNotEqual(gv, None)
        self.assertEqual(gv.name, "gv")
        self.assertEqual(gv.type, Type.pointer(t))


def main():
    gc.set_debug(gc.DEBUG_LEAK)

    # run tests
    if sys.version_info[:2] > (2, 6):
        unittest.main(exit=False)  # set exit to False so that it will return.
    else:
        unittest.main()
    # done
    for it in gc.garbage:
        logging.debug('garbage = %s', it)

if __name__ == '__main__':
    main()




########NEW FILE########
__FILENAME__ = testall
#!/usr/bin/env python

#
# This script attempts to achieve 100% function and branch coverage for
# all APIs in the llvm package. It only exercises the APIs, doesn't test
# them for correctness.
#

from llvm import *
from llvm.core import *
from llvm.ee import *
from llvm.passes import *

ti = Type.int()

def do_llvmexception():
    print("    Testing class LLVMException")
    e = LLVMException()


def do_misc():
    print("    Testing miscellaneous functions")
    try:
        load_library_permanently("/usr/lib/libm.so")
    except LLVMException:
        pass
    try:
        print("        ... second one now")
        load_library_permanently("no*such*so")
    except LLVMException:
        pass


def do_llvm():
    print("  Testing module llvm")
    do_llvmexception()
    do_misc()


def do_module():
    print("    Testing class Module")
    m = Module.new('test')
    m.target = 'a'
    a = m.target
    m.data_layout = 'a'
    a = m.data_layout
    # m.add_type_name('a', ti)
    # m.delete_type_name('a')
    Type.struct([ti], name='a')
    m.get_type_named('a').name=''

    s = str(m)
    s = m == Module.new('a')
    m.add_global_variable(ti, 'b')
    m.get_global_variable_named('b')
    gvs = list(m.global_variables)
    ft = Type.function(ti, [ti])
    m.add_function(ft, "func")
    m.get_function_named("func")
    m.get_or_insert_function(ft, "func")
    m.get_or_insert_function(Type.function(ti, []), "func")
    m.get_or_insert_function(ft, "func2")
    fns = list(m.functions)
    try:
        m.verify()
    except LLVMException:
        pass

    class strstream(object):
        def __init__(self):
            self.s = b''

        def write(self, data):
            if not isinstance(data, bytes):
                data = data.encode('utf-8')
            self.s += data

        def read(self):
            return self.s

    ss = strstream()
    m2 = Module.new('test')
    # m2.add_type_name('myint', ti)
    Type.struct([ti], 'myint')

    m2.to_bitcode(ss)
    m3 = Module.from_bitcode(ss)
    t = m2 == m3
    ss2 = strstream()
    ss2.write(str(m))
    m4 = Module.from_assembly(ss2)
    t = m4 == m
    t = m4.pointer_size
    mA = Module.new('ma')
    mB = Module.new('mb')
    mA.link_in(mB)


def do_type():
    print("    Testing class Type")
    for i in range(1,100):
        Type.int(i)
    Type.float()
    Type.double()
    Type.x86_fp80()
    Type.fp128()
    Type.ppc_fp128()
    Type.function(ti, [ti]*100, True)
    Type.function(ti, [ti]*100, False)
    Type.struct([ti]*100)
    Type.packed_struct([ti]*100)
    Type.array(ti, 100)
    ptr = Type.pointer(ti, 4)
    pte = ptr.pointee
    Type.vector(ti, 100)
    Type.void()
    Type.label()

    Type.opaque('an_opaque_type')
    s = str(ti)
    s = ti == Type.float()
    Type.opaque('whatever').set_body([Type.int()])
    s = ti.width
    ft = Type.function(ti, [ti]*10)
    ft.return_type
    ft.vararg
    s = list(ft.args)
    ft.arg_count
    st = Type.struct([ti]*10)
    s = st.element_count
    s = list(st.elements)
    s = st.packed
    st = Type.packed_struct([ti]*10)
    s = st.element_count
    s = list(st.elements)
    s = st.packed
    at = Type.array(ti, 100)
    s = at.element
    s = at.count
    pt = Type.pointer(ti, 10)
    pt.address_space
    vt = Type.vector(ti, 100)
    s = vt.element
    s = vt.count
    Type.int(32) == Type.int(64)
    Type.int(32) != Type.int(64)
    Type.int(32) != Type.float()

### Removed
#def do_typehandle():
#    print("    Testing class TypeHandle")
#    th = TypeHandle.new(Type.opaque())
#    ts = Type.struct([ Type.int(), Type.pointer(th.type) ])
#    th.type.refine(ts)


def do_value():
    print("    Testing class Value")
    k = Constant.int(ti, 42)
    k.name = 'a'
    s = k.name
    t = k.type
    s = str(k)
    s = k == Constant.int(ti, 43)
    i = k.value_id
    i = k.use_count
    i = k.uses


def do_user():
    m = Module.new('a')
    ft = Type.function(ti, [ti]*2)
    f = Function.new(m, ft, 'func')
    b = f.append_basic_block('a')
    bb = Builder.new(b)
    i1 = bb.add(f.args[0], f.args[1])
    i2 = bb.ret(i1)
    i1.operand_count == 2
    i2.operand_count == 1
    i1.operands[0] is f.args[0]
    i1.operands[1] is f.args[1]
    i2.operands[0] is i1


def do_constant():
    print("    Testing class Constant")
    Constant.null(ti)
    Constant.all_ones(ti)
    Constant.undef(ti)
    Constant.int(ti, 10)
    Constant.int_signextend(ti, 10)
    Constant.real(Type.float(), "10.0")
    Constant.real(Type.float(), 3.14)
    Constant.string("test")
    Constant.stringz("test2")
    Constant.array(ti, [Constant.int(ti,42)]*10)
    Constant.struct([Constant.int(ti,42)]*10)
    Constant.packed_struct([Constant.int(ti,42)]*10)
    Constant.vector([Constant.int(ti,42)]*10)

    Constant.sizeof(ti)

    k = Constant.int(ti, 10)
    f = Constant.real(Type.float(), 3.1415)
    k.neg().not_().add(k).sub(k).mul(k).udiv(k).sdiv(k).urem(k)
    k.srem(k).and_(k).or_(k).xor(k).icmp(IPRED_ULT, k)
    f.fdiv(f).frem(f).fcmp(RPRED_ULT, f)
    f.fadd(f).fmul(f).fsub(f)
    vi = Constant.vector([Constant.int(ti,42)]*10)
    vf = Constant.vector([Constant.real(Type.float(), 3.14)]*10)
    k.shl(k).lshr(k).ashr(k)
    return
    # TODO gep
    k.trunc(Type.int(1))
    k.sext(Type.int(64))
    k.zext(Type.int(64))
    Constant.real(Type.double(), 1.0).fptrunc(Type.float())
    Constant.real(Type.float(), 1.0).fpext(Type.double())
    k.uitofp(Type.float())
    k.sitofp(Type.float())
    f.fptoui(ti)
    f.fptosi(ti)
    p = Type.pointer(ti)
    # TODO ptrtoint
    k.inttoptr(p)
    f.bitcast(Type.int(32))
    k.trunc(Type.int(1)).select(k, k)
    vi.extract_element( Constant.int(ti,0) )
    vi.insert_element( k, k )
    vi.shuffle_vector( vi, vi )


def do_global_value():
    print("    Testing class GlobalValue")
    m = Module.new('a')
    gv = GlobalVariable.new(m, Type.int(), 'b')
    s = gv.is_declaration
    m = gv.module
    gv.linkage = LINKAGE_EXTERNAL
    s = gv.linkage
    gv.section = '.text'
    s = gv.section
    gv.visibility = VISIBILITY_HIDDEN
    s = gv.visibility
    gv.alignment = 8
    s = gv.alignment


def do_global_variable():
    print("    Testing class GlobalVariable")
    m = Module.new('a')
    gv = GlobalVariable.new(m, Type.int(), 'b')
    gv = GlobalVariable.get(m, 'b')
    gv.delete()
    gv = GlobalVariable.new(m, Type.int(), 'c')
    gv.initializer = Constant.int( ti, 10 )
    s = gv.initializer
    gv.global_constant = True
    s = gv.global_constant


def do_argument():
    print("    Testing class Argument")
    m = Module.new('a')
    tip = Type.pointer(ti)
    ft = Type.function(tip, [tip])
    f = Function.new(m, ft, 'func')
    a = f.args[0]
    a.add_attribute(ATTR_NEST)
    a.remove_attribute(ATTR_NEST)
    a.alignment = 16
    a1 = a.alignment


def do_function():
    print("    Testing class Function")
    ft = Type.function(ti, [ti]*20)
    zz = Function.new(Module.new('z'), ft, 'foobar')
    del zz
    Function.new(Module.new('zz'), ft, 'foobar')
    m = Module.new('a')
    f = Function.new(m, ft, 'func')
    f.delete()
    ft = Type.function(ti, [ti]*20)
    f = Function.new(m, ft, 'func2')
    has_nounwind = f.does_not_throw
    f.does_not_throw = True
    f2 = Function.intrinsic(m, INTR_COS, [ti])
    g = f.intrinsic_id
    f.calling_convenion = CC_FASTCALL
    g = f.calling_convenion
    f.collector = 'a'
    c = f.collector
    a = list(f.args)
    g = f.basic_block_count
#    g = f.entry_basic_block
#    g = f.append_basic_block('a')
#    g = f.entry_basic_block
    g = list(f.basic_blocks)
    f.add_attribute(ATTR_NO_RETURN)
    f.add_attribute(ATTR_ALWAYS_INLINE)
    #for some reason removeFnAttr is just gone in 3.3
    if version <= (3, 2):
        f.remove_attribute(ATTR_NO_RETURN)

    # LLVM misbehaves:
    #try:
    #    f.verify()
    #except LLVMException:
    #    pass


def do_instruction():
    print("    Testing class Instruction")
    m = Module.new('a')
    ft = Type.function(ti, [ti]*20)
    f = Function.new(m, ft, 'func')
    b = f.append_basic_block('a')
    bb = Builder.new(b)
    i = bb.ret_void()
    bb2 = i.basic_block
    ops = i.operands
    opcount = i.operand_count


def do_callorinvokeinstruction():
    print("    Testing class CallOrInvokeInstruction")
    m = Module.new('a')
    ft = Type.function(ti, [ti])
    f = Function.new(m, ft, 'func')
    b = f.append_basic_block('a')
    bb = Builder.new(b)
    i = bb.invoke(f, [Constant.int(ti, 10)], b, b)
    a = i.calling_convention
    i.calling_convention = CC_FASTCALL
    if version <= (3, 2):
        i.add_parameter_attribute(0, ATTR_SEXT)
        i.remove_parameter_attribute(0, ATTR_SEXT)
        i.set_parameter_alignment(0, 8)
    #tc = i.tail_call
    #i.tail_call = 1


def do_phinode():
    print("    Testing class PhiNode")
    m = Module.new('a')
    ft = Type.function(ti, [ti])
    f = Function.new(m, ft, 'func')
    b = f.append_basic_block('b')
    c = f.append_basic_block('c')
    d = f.append_basic_block('d')
    bb = Builder.new(d)
    p = bb.phi(ti)
    v = p.incoming_count
    p.add_incoming( Constant.int(ti, 10), b )
    p.add_incoming( Constant.int(ti, 10), c )
    p.get_incoming_value(0)
    p.get_incoming_block(0)


def do_switchinstruction():
    print("    Testing class SwitchInstruction")
    m = Module.new('a')
    ft = Type.function(ti, [ti])
    f = Function.new(m, ft, 'func')
    b = f.append_basic_block('b')
    bb = Builder.new(b)
    s = bb.switch(f.args[0], b)
    s.add_case(Constant.int(ti, 10), b)


def do_basicblock():
    print("    Testing class BasicBlock")
    m = Module.new('a')
    ft = Type.function(ti, [ti])
    f = Function.new(m, ft, 'func')
    b = f.append_basic_block('b')
    bb = Builder.new(b)
    s = bb.switch(f.args[0], b)
    s.add_case(Constant.int(ti, 10), b)
    s = list(b.instructions)
    b2 = b.insert_before('before')
    b2.delete()
    ff = b.function
    m2 = ff.module
    t = m == m2


def _do_builder_mrv():
    m = Module.new('mrv')
    ft = Type.function(Type.array(ti, 2), [ti])
    f = Function.new(m, ft, 'divrem')
    blk = f.append_basic_block('b')
    b = Builder.new(blk)
    v = b.call(f, [Constant.int(ti, 1)])
    v1 = b.extract_value(v, 0)
    v2 = b.extract_value(v, 1)
    b.ret_many([v1, v2])
    #print f


def do_builder():
    print("    Testing class Builder")
    m = Module.new('a')
    ft = Type.function(ti, [ti])
    f = Function.new(m, ft, 'func')
    blk = f.append_basic_block('b')
    b = Builder.new(blk)
    b.ret(Constant.int(ti, 10))
    b.position_at_beginning(blk)
    b.position_at_end(blk)
    b.position_before(blk.instructions[0])
    blk2 = b.basic_block
    b.ret_void()
    b.ret(Constant.int(ti, 10))
    _do_builder_mrv()
    #b.ret_many([Constant.int(ti, 10)]*10)
    b.branch(blk)
    b.cbranch(Constant.int(Type.int(1), 1), blk, blk)
    b.switch(f.args[0], blk)
    b.invoke(f, [Constant.int(ti,10)], blk, blk)
    # b.unwind() # removed
    b.unreachable()
    v = f.args[0]
    fv = Constant.real(Type.float(), "1.0")
    k = Constant.int(ti, 10)
    b.add(v, v)
    b.fadd(fv, fv)
    b.sub(v, v)
    b.fsub(fv, fv)
    b.mul(v, v)
    b.fmul(fv, fv)
    b.udiv(v, v)
    b.sdiv(v, v)
    b.fdiv(fv, fv)
    b.urem(v, v)
    b.srem(v, v)
    b.frem(fv, fv)
    b.shl(v, k)
    b.lshr(v, k)
    b.ashr(v, k)
    b.and_(v, v)
    b.or_(v, v)
    b.xor(v, v)
    b.neg(v)
    b.not_(v)
    p = b.malloc(Type.int())
    b.malloc_array(Type.int(), k)
    b.alloca(Type.int())
    b.alloca_array(Type.int(), k)
    b.free(p)
    b.load(p)
    b.store(k, p)
    # TODO gep
    b.trunc(v, Type.int(1))
    b.zext(v, Type.int(64))
    b.sext(v, Type.int(64))
    b.fptoui(fv, ti)
    b.fptosi(fv, ti)
    b.uitofp(k, Type.float())
    b.sitofp(k, Type.float())
    b.fptrunc(Constant.real(Type.double(), "1.0"), Type.float())
    b.fpext(Constant.real(Type.float(), "1.0"), Type.double())
    b.ptrtoint(p, ti)
    b.inttoptr(k, Type.pointer(Type.int()))
    b.bitcast(v, Type.float())
    b.icmp(IPRED_ULT, v, v)
    b.fcmp(RPRED_ULT, fv, fv)
    vi = Constant.vector([Constant.int(ti,42)]*10)
    vi_mask = Constant.vector([Constant.int(ti, X) for X in range(20)])
    vf = Constant.vector([Constant.real(Type.float(), 3.14)]*10)
    # TODO b.extract_value(v, 0)
    b.call(f, [v])
    b.select(Constant.int(Type.int(1), 1), blk, blk)
    b.vaarg(v, Type.int())
    b.extract_element(vi, v)
    b.insert_element(vi, v, v)
    b.shuffle_vector(vi, vi, vi_mask)
    # NOTE: phi nodes without incoming values segfaults in LLVM during
    # destruction.
    i = b.phi(Type.int())
    i.add_incoming(v, blk)
    t = i.is_terminator == False
    t = i.is_binary_op == False
    t = i.is_shift == False
    t = i.is_cast == False
    t = i.is_logical_shift == False
    t = i.is_arithmetic_shift == False
    t = i.is_associative == False
    t = i.is_commutative == False
    t = i.is_volatile == False
    t = i.opcode
    t = i.opcode_name


def do_llvm_core():
    print("  Testing module llvm.core")
    do_module()
    do_type()
    #    do_typehandle()
    do_value()
    do_user()
    do_constant()
    do_global_value()
    do_global_variable()
    do_argument()
    do_function()
    do_instruction()
    do_callorinvokeinstruction()
    do_phinode()
    do_switchinstruction()
    do_basicblock()
    do_builder()


def do_targetdata():
    print("    Testing class TargetData")
    t = TargetData.new('')
    v = str(t)
    v = t.byte_order
    v = t.pointer_size
    v = t.target_integer_type
    ty = Type.int()
    v = t.size(ty)
    v = t.store_size(ty)
    v = t.abi_size(ty)
    v = t.abi_alignment(ty)
    v = t.callframe_alignment(ty)
    v = t.preferred_alignment(ty)
    sty = Type.struct([ty, ty])
    v = t.element_at_offset(sty, 0)
    v = t.offset_of_element(sty, 0)
    m = Module.new('a')
    gv = m.add_global_variable(ty, 'gv')
    v = t.preferred_alignment(gv)


def do_genericvalue():
    print("    Testing class GenericValue")
    v = GenericValue.int(ti, 1)
    v = GenericValue.int_signed(ti, 1)
    v = GenericValue.real(Type.float(), 3.14)
    a = v.as_int()
    a = v.as_int_signed()
    a = v.as_real(Type.float())


def do_executionengine():
    print("    Testing class ExecutionEngine")
    m = Module.new('a')
    ee = ExecutionEngine.new(m, False) # True)
    ft = Type.function(ti, [])
    f = m.add_function(ft, 'func')
    bb = f.append_basic_block('entry')
    b = Builder.new(bb)
    b.ret(Constant.int(ti, 42))
    ee.run_static_ctors()
    gv = ee.run_function(f, [])
    is42 = gv.as_int() == 42
    ee.run_static_dtors()
    ee.free_machine_code_for(f)
    t = ee.target_data
    m2 = Module.new('b')
    ee.add_module(m2)
    m3 = Module.new('c')
    ee2 = ExecutionEngine.new(m3, False)
    m4 = Module.new('d')
    m5 = Module.new('e')
    #ee3 = ExecutionEngine.new(m4, False)
    #ee3.add_module(m5)
    #x = ee3.remove_module(m5)
    #isinstance(x, Module)


def do_llvm_ee():
    print("  Testing module llvm.ee")
    do_targetdata()
    do_genericvalue()
    do_executionengine()


def do_passmanager():
    print("    Testing class PassManager")
    pm = PassManager.new()
    pm.add(TargetData.new(''))

    print('.........Begging for rewrite!!!')
    ### It is not practical to maintain all PASS_* constants.
    #
    #    passes = ('PASS_OPTIMAL_EDGE_PROFILER', 'PASS_EDGE_PROFILER',
    #              'PASS_PROFILE_LOADER', 'PASS_AAEVAL')
    #    all_these = [getattr(llvm.passes, x)
    #                    for x in dir(llvm.passes)
    #                        if x.startswith('PASS_') and x not in passes]
    #    for i in all_these:
    #        print i
    #        pm.add(i)
    pm.run(Module.new('a'))


def do_functionpassmanager():
    print("    Testing class FunctionPassManager")
    m = Module.new('a')
    ft = Type.function(ti, [])
    f = m.add_function(ft, 'func')
    bb = f.append_basic_block('entry')
    b = Builder.new(bb)
    b.ret(Constant.int(ti, 42))
    fpm = FunctionPassManager.new(m)
    fpm.add(TargetData.new(''))
    fpm.add(PASS_ADCE)
    fpm.initialize()
    fpm.run(f)
    fpm.finalize()


def do_llvm_passes():
    print("  Testing module llvm.passes")
    do_passmanager()
    do_functionpassmanager()

def do_llvm_target():
    print("  Testing module llvm.target")
    from llvm import target

    target.initialize_all()
    target.print_registered_targets()
    target.get_host_cpu_name()
    target.get_default_triple()

    tm = TargetMachine.new()
    tm = TargetMachine.lookup("arm")
    tm = TargetMachine.arm()
    tm = TargetMachine.thumb()
    tm = TargetMachine.x86()
    tm = TargetMachine.x86_64()
    tm.target_data
    tm.target_name
    tm.target_short_description
    tm.triple
    tm.cpu
    tm.feature_string
    tm.target

    if llvm.version >= (3, 4):
         tm.reg_info
         tm.subtarget_info
         tm.asm_info
         tm.instr_info
         tm.instr_analysis
         tm.disassembler
         tm.is_little_endian()

def do_llvm_mc():
    if llvm.version < (3, 4):
        return

    from llvm import target
    from llvm import mc

    target.initialize_all()
    tm = TargetMachine.x86()
    dasm = mc.Disassembler(tm)

    for (offset, data, instr) in dasm.decode("c3", 0):
        pass

def main():
    print("Testing package llvm")
    do_llvm()
    do_llvm_core()
    do_llvm_ee()
    do_llvm_passes()
    do_llvm_target()
    do_llvm_mc()

if __name__ == '__main__':
    main()

# to add:
# IntegerType
# FunctionType
# StructType
# ArrayType
# PointerType
# VectorType
# ConstantExpr
# ConstantAggregateZero
# ConstantInt
# ConstantFP
# ConstantArray
# ConstantStruct
# ConstantVector
# ConstantPointerNull
# MemoryBuffer


########NEW FILE########
__FILENAME__ = test_debuginfo
import os
import unittest

import llvm.ee
from llvm.core import *
from llvm import _dwarf, debuginfo
from llvm.tests.support import TestCase

class TestDebugInfo(TestCase):

    def test_dwarf_constants(self):
        dwarf_constants = vars(_dwarf)

        # Version numbers
        self.assertIn("LLVMDebugVersion", dwarf_constants)
        self.assertIn("DWARF_VERSION", dwarf_constants)

        # Tags
        self.assertIn("DW_TAG_compile_unit", dwarf_constants)

        # Language identifiers
        self.assertIn("DW_LANG_Python", dwarf_constants)
        self.assertIn("DW_LANG_C89", dwarf_constants)
        self.assertIn("DW_LANG_C99", dwarf_constants)

        # print sorted([constname for constname in dwarf_constants
        #                             if constname.startswith("DW_LANG_")])

    def test_debug_info_compile_unit(self):
        mod = Module.new('test_debug_info')
        fty = Type.function(Type.float(), [Type.float()])
        square = mod.add_function(fty, 'square')
        bb = square.append_basic_block('entry')
        bldr = Builder.new(bb)

        source_filename = "test_debug_info.py"
        source_filedir = os.path.expanduser("~")

        # Debug info for our file
        filedesc = debuginfo.FileDescriptor(source_filename, source_filedir)

        # Debug info for our function
        subprogram = debuginfo.SubprogramDescriptor(
            filedesc,
            "some_function",
            "some_function",
            "some_function",
            filedesc,
            1,                          # line number
            debuginfo.empty,            # Type descriptor
            llvm_func=square,
        )
        subprograms = debuginfo.MDList([subprogram])

        # Debug info for our basic blocks
        blockdescr1 = debuginfo.BlockDescriptor(subprogram, 2, 4) # lineno, col
        blockdescr2 = debuginfo.BlockDescriptor(blockdescr1, 3, 4) # lineno, col

        # Debug info for our instructions
        posinfo1 = debuginfo.PositionInfoDescriptor(2, 4, blockdescr1)
        posinfo2 = debuginfo.PositionInfoDescriptor(2, 4, blockdescr2)

        # Debug info for our module
        compile_unit = debuginfo.CompileUnitDescriptor(
            # DW_LANG_Python segfaults:
            # llvm/ADT/StringRef.h:79: llvm::StringRef::StringRef(const char*):
            # Assertion `Str && "StringRef cannot be built from a NULL argument"'
            # _dwarf.DW_LANG_Python,
            _dwarf.DW_LANG_C89,
            source_filename,
            source_filedir,
            "my_cool_compiler",
            subprograms=subprograms,
        )

        # Define our module debug data
        compile_unit.define(mod)

        # Build some instructions
        value = square.args[0]
        # result = bldr.fmul(value, value)

        # Generate an instruction that will result in a signal
        result = bldr.fdiv(value, llvm.core.Constant.real(value.type, 0))
        ltrap = llvm.core.Function.intrinsic(mod, INTR_TRAP, [])
        lcall = bldr.call(ltrap, [])
        ret = bldr.ret(result)

        # Annotate instructions with source position
        result.set_metadata("dbg", posinfo1.get_metadata(mod))
        lcall.set_metadata("dbg", posinfo1.get_metadata(mod))
        ret.set_metadata("dbg", posinfo2.get_metadata(mod))

        # ... Aaaand, test...
        # print mod

        modstr = str(mod)

        # Test compile unit
        self.assertIn("my_cool_compiler", modstr)
        self.assertIn(source_filename, modstr)
        self.assertIn(source_filedir, modstr)
        self.assertIn("my_cool_compiler", modstr)

        # Test subprogram
        self.assertIn("some_function", modstr)
        self.assertIn("float (float)* @square", modstr)

        return square


def debug_in_gdb(lfunc):
    # Create an execution engine object. This will create a JIT compiler
    # on platforms that support it, or an interpreter otherwise.
    module = lfunc.module
    ee = llvm.ee.ExecutionEngine.new(module)
    float_type = lfunc.args[0].type

    # The arguments needs to be passed as "GenericValue" objects.
    arg1_value = 5.0
    arg1 = llvm.ee.GenericValue.real(float_type, arg1_value)

    # Now let's compile and run!
    retval = ee.run_function(lfunc, [arg1])
    print(retval.as_real(float_type))


if __name__ == '__main__':
#    TestDebugInfo("test_dwarf_constants").debug()
#    TestDebugInfo("test_debug_info_compile_unit").debug()
#    tester = TestDebugInfo("test_debug_info_compile_unit")
#    debug_in_gdb(tester.test_debug_info_compile_unit())
    unittest.main()

########NEW FILE########
__FILENAME__ = intrgen
#!/usr/bin/env python
#
# Script to generate intrinsic IDs (found in core.py) from
# <llvm>/include/llvm/Intrinsics.gen. Call with path to the
# latter.

import sys

def gen(f, out=sys.stdout):
    intr = []
    maxw = 0
    flag = False
    for line in open(f):
        if line.startswith('#ifdef GET_INTRINSIC_ENUM_VALUES'):
            flag = True
        elif flag:
            if line.startswith('#endif'):
                break
            else:
                item = line.split()[0].replace(',', '')
                if len(item) > maxw:
                    maxw = len(item)
                intr.append(item)

    maxw = len('INTR_') + maxw
    idx = 1
    for i in intr:
        s = 'INTR_' + i.upper()
        out.write('%s = %d\n' % (s.ljust(maxw), idx))
        idx += 1

if __name__ == '__main__':
    gen(sys.argv[1])

########NEW FILE########
__FILENAME__ = intrs_for_doc
#!/usr/bin/env python

import os

NCOLS = 4
INF   = '../llvm/_intrinsic_ids.py'
OUTF  = '../www/src/intrinsics.csv'

intrs = []
for line in file(INF):
    if line.startswith('INTR_'):
        if 'INTR_ALPHA_'  not in line and  \
           'INTR_ARM_'    not in line and  \
           'INTR_BFIN_'   not in line and  \
           'INTR_PPC_'    not in line and  \
           'INTR_SPU_'    not in line and  \
           'INTR_X86_'    not in line and  \
           'INTR_XCORE_'  not in line:
            intrs.append(line.split()[0])

outf = open(OUTF, 'wt')
i = 0
while i < len(intrs):
    print("`" + "`,`".join(intrs[i:min(i+NCOLS,len(intrs)+1)]) + "`", file=outf)
    i += NCOLS

########NEW FILE########
__FILENAME__ = versioneer
#! /usr/bin/python

"""versioneer.py

(like a rocketeer, but for versions)

* https://github.com/warner/python-versioneer
* Brian Warner
* License: Public Domain
* Version: 0.7+

This file helps distutils-based projects manage their version number by just
creating version-control tags.

For developers who work from a VCS-generated tree (e.g. 'git clone' etc),
each 'setup.py version', 'setup.py build', 'setup.py sdist' will compute a
version number by asking your version-control tool about the current
checkout. The version number will be written into a generated _version.py
file of your choosing, where it can be included by your __init__.py

For users who work from a VCS-generated tarball (e.g. 'git archive'), it will
compute a version number by looking at the name of the directory created when
te tarball is unpacked. This conventionally includes both the name of the
project and a version number.

For users who work from a tarball built by 'setup.py sdist', it will get a
version number from a previously-generated _version.py file.

As a result, loading code directly from the source tree will not result in a
real version. If you want real versions from VCS trees (where you frequently
update from the upstream repository, or do new development), you will need to
do a 'setup.py version' after each update, and load code from the build/
directory.

You need to provide this code with a few configuration values:

 versionfile_source:
    A project-relative pathname into which the generated version strings
    should be written. This is usually a _version.py next to your project's
    main __init__.py file. If your project uses src/myproject/__init__.py,
    this should be 'src/myproject/_version.py'. This file should be checked
    in to your VCS as usual: the copy created below by 'setup.py
    update_files' will include code that parses expanded VCS keywords in
    generated tarballs. The 'build' and 'sdist' commands will replace it with
    a copy that has just the calculated version string.

 versionfile_build:
    Like versionfile_source, but relative to the build directory instead of
    the source directory. These will differ when your setup.py uses
    'package_dir='. If you have package_dir={'myproject': 'src/myproject'},
    then you will probably have versionfile_build='myproject/_version.py' and
    versionfile_source='src/myproject/_version.py'.

 tag_prefix: a string, like 'PROJECTNAME-', which appears at the start of all
             VCS tags. If your tags look like 'myproject-1.2.0', then you
             should use tag_prefix='myproject-'. If you use unprefixed tags
             like '1.2.0', this should be an empty string.

 parentdir_prefix: a string, frequently the same as tag_prefix, which
                   appears at the start of all unpacked tarball filenames. If
                   your tarball unpacks into 'myproject-1.2.0', this should
                   be 'myproject-'.

To use it:

 1: include this file in the top level of your project
 2: make the following changes to the top of your setup.py:
     import versioneer
     versioneer.versionfile_source = 'src/myproject/_version.py'
     versioneer.versionfile_build = 'myproject/_version.py'
     versioneer.tag_prefix = '' # tags are like 1.2.0
     versioneer.parentdir_prefix = 'myproject-' # dirname like 'myproject-1.2.0'
 3: add the following arguments to the setup() call in your setup.py:
     version=versioneer.get_version(),
     cmdclass=versioneer.get_cmdclass(),
 4: run 'setup.py update_files', which will create _version.py, and will
    append the following to your __init__.py:
     from _version import __version__
 5: modify your MANIFEST.in to include versioneer.py
 6: add both versioneer.py and the generated _version.py to your VCS
"""

import os
import sys
import re
import subprocess
from distutils.core import Command
from distutils.command.sdist import sdist as _sdist
from distutils.command.build import build as _build

versionfile_source = None
versionfile_build = None
tag_prefix = None
parentdir_prefix = None

VCS = "git"
IN_LONG_VERSION_PY = False
GIT = "git"


LONG_VERSION_PY = '''
IN_LONG_VERSION_PY = True
# This file helps to compute a version number in source trees obtained from
# git-archive tarball (such as those provided by github's download-from-tag
# feature). Distribution tarballs (build by setup.py sdist) and build
# directories (produced by setup.py build) will contain a much shorter file
# that just contains the computed version number.

# This file is released into the public domain. Generated by
# versioneer-0.7+ (https://github.com/warner/python-versioneer)

# these strings will be replaced by git during git-archive
git_refnames = "%(DOLLAR)sFormat:%%d%(DOLLAR)s"
git_full = "%(DOLLAR)sFormat:%%H%(DOLLAR)s"


import subprocess
import sys

def run_command(args, cwd=None, verbose=False):
    try:
        # remember shell=False, so use git.cmd on windows, not just git
        p = subprocess.Popen(args, stdout=subprocess.PIPE, cwd=cwd)
    except EnvironmentError:
        e = sys.exc_info()[1]
        if verbose:
            print("unable to run %%s" %% args[0])
            print(e)
        return None
    stdout = p.communicate()[0].strip()
    if sys.version >= '3':
        stdout = stdout.decode()
    if p.returncode != 0:
        if verbose:
            print("unable to run %%s (error)" %% args[0])
        return None
    return stdout


import sys
import re
import os.path

def get_expanded_variables(versionfile_source):
    # the code embedded in _version.py can just fetch the value of these
    # variables. When used from setup.py, we don't want to import
    # _version.py, so we do it with a regexp instead. This function is not
    # used from _version.py.
    variables = {}
    try:
        for line in open(versionfile_source,"r").readlines():
            if line.strip().startswith("git_refnames ="):
                mo = re.search(r'=\s*"(.*)"', line)
                if mo:
                    variables["refnames"] = mo.group(1)
            if line.strip().startswith("git_full ="):
                mo = re.search(r'=\s*"(.*)"', line)
                if mo:
                    variables["full"] = mo.group(1)
    except EnvironmentError:
        pass
    return variables

def versions_from_expanded_variables(variables, tag_prefix, verbose=False):
    refnames = variables["refnames"].strip()
    if refnames.startswith("$Format"):
        if verbose:
            print("variables are unexpanded, not using")
        return {} # unexpanded, so not in an unpacked git-archive tarball
    refs = set([r.strip() for r in refnames.strip("()").split(",")])
    for ref in list(refs):
        if not re.search(r'\d', ref):
            if verbose:
                print("discarding '%%s', no digits" %% ref)
            refs.discard(ref)
            # Assume all version tags have a digit. git's %%d expansion
            # behaves like git log --decorate=short and strips out the
            # refs/heads/ and refs/tags/ prefixes that would let us
            # distinguish between branches and tags. By ignoring refnames
            # without digits, we filter out many common branch names like
            # "release" and "stabilization", as well as "HEAD" and "master".
    if verbose:
        print("remaining refs: %%s" %% ",".join(sorted(refs)))
    for ref in sorted(refs):
        # sorting will prefer e.g. "2.0" over "2.0rc1"
        if ref.startswith(tag_prefix):
            r = ref[len(tag_prefix):]
            if verbose:
                print("picking %%s" %% r)
            return { "version": r,
                     "full": variables["full"].strip() }
    # no suitable tags, so we use the full revision id
    if verbose:
        print("no suitable tags, using full revision id")
    return { "version": variables["full"].strip(),
             "full": variables["full"].strip() }

def versions_from_vcs(tag_prefix, versionfile_source, verbose=False):
    # this runs 'git' from the root of the source tree. That either means
    # someone ran a setup.py command (and this code is in versioneer.py, so
    # IN_LONG_VERSION_PY=False, thus the containing directory is the root of
    # the source tree), or someone ran a project-specific entry point (and
    # this code is in _version.py, so IN_LONG_VERSION_PY=True, thus the
    # containing directory is somewhere deeper in the source tree). This only
    # gets called if the git-archive 'subst' variables were *not* expanded,
    # and _version.py hasn't already been rewritten with a short version
    # string, meaning we're inside a checked out source tree.

    try:
        here = os.path.abspath(__file__)
    except NameError:
        # some py2exe/bbfreeze/non-CPython implementations don't do __file__
        return {} # not always correct

    # versionfile_source is the relative path from the top of the source tree
    # (where the .git directory might live) to this file. Invert this to find
    # the root from __file__.
    root = here
    if IN_LONG_VERSION_PY:
        for i in range(len(versionfile_source.split("/"))):
            root = os.path.dirname(root)
    else:
        root = os.path.dirname(here)
    if not os.path.exists(os.path.join(root, ".git")):
        if verbose:
            print("no .git in %%s" %% root)
        return {}

    stdout = run_command([GIT, "describe", "--tags", "--dirty", "--always"],
                         cwd=root)
    if stdout is None:
        return {}
    if not stdout.startswith(tag_prefix):
        if verbose:
            print("tag '%%s' doesn't start with prefix '%%s'" %% (stdout, tag_prefix))
        return {}
    tag = stdout[len(tag_prefix):]
    stdout = run_command([GIT, "rev-parse", "HEAD"], cwd=root)
    if stdout is None:
        return {}
    full = stdout.strip()
    if tag.endswith("-dirty"):
        full += "-dirty"
    return {"version": tag, "full": full}


def versions_from_parentdir(parentdir_prefix, versionfile_source, verbose=False):
    if IN_LONG_VERSION_PY:
        # We're running from _version.py. If it's from a source tree
        # (execute-in-place), we can work upwards to find the root of the
        # tree, and then check the parent directory for a version string. If
        # it's in an installed application, there's no hope.
        try:
            here = os.path.abspath(__file__)
        except NameError:
            # py2exe/bbfreeze/non-CPython don't have __file__
            return {} # without __file__, we have no hope
        # versionfile_source is the relative path from the top of the source
        # tree to _version.py. Invert this to find the root from __file__.
        root = here
        for i in range(len(versionfile_source.split("/"))):
            root = os.path.dirname(root)
    else:
        # we're running from versioneer.py, which means we're running from
        # the setup.py in a source tree. sys.argv[0] is setup.py in the root.
        here = os.path.abspath(sys.argv[0])
        root = os.path.dirname(here)

    # Source tarballs conventionally unpack into a directory that includes
    # both the project name and a version string.
    dirname = os.path.basename(root)
    if not dirname.startswith(parentdir_prefix):
        if verbose:
            print("guessing rootdir is '%%s', but '%%s' doesn't start with prefix '%%s'" %%
                  (root, dirname, parentdir_prefix))
        return None
    return {"version": dirname[len(parentdir_prefix):], "full": ""}

tag_prefix = "%(TAG_PREFIX)s"
parentdir_prefix = "%(PARENTDIR_PREFIX)s"
versionfile_source = "%(VERSIONFILE_SOURCE)s"

def get_versions(default={"version": "unknown", "full": ""}, verbose=False):
    variables = { "refnames": git_refnames, "full": git_full }
    ver = versions_from_expanded_variables(variables, tag_prefix, verbose)
    if not ver:
        ver = versions_from_vcs(tag_prefix, versionfile_source, verbose)
    if not ver:
        ver = versions_from_parentdir(parentdir_prefix, versionfile_source,
                                      verbose)
    if not ver:
        ver = default
    return ver

'''

def run_command(args, cwd=None, verbose=False):
    try:
        # remember shell=False, so use git.cmd on windows, not just git
        p = subprocess.Popen(args, stdout=subprocess.PIPE, cwd=cwd)
    except EnvironmentError:
        e = sys.exc_info()[1]
        if verbose:
            print("unable to run %s" % args[0])
            print(e)
        return None
    stdout = p.communicate()[0].strip()
    if sys.version >= '3':
        stdout = stdout.decode()
    if p.returncode != 0:
        if verbose:
            print("unable to run %s (error)" % args[0])
        return None
    return stdout


def get_expanded_variables(versionfile_source):
    # the code embedded in _version.py can just fetch the value of these
    # variables. When used from setup.py, we don't want to import
    # _version.py, so we do it with a regexp instead. This function is not
    # used from _version.py.
    variables = {}
    try:
        for line in open(versionfile_source,"r").readlines():
            if line.strip().startswith("git_refnames ="):
                mo = re.search(r'=\s*"(.*)"', line)
                if mo:
                    variables["refnames"] = mo.group(1)
            if line.strip().startswith("git_full ="):
                mo = re.search(r'=\s*"(.*)"', line)
                if mo:
                    variables["full"] = mo.group(1)
    except EnvironmentError:
        pass
    return variables

def versions_from_expanded_variables(variables, tag_prefix, verbose=False):
    refnames = variables["refnames"].strip()
    if refnames.startswith("$Format"):
        if verbose:
            print("variables are unexpanded, not using")
        return {} # unexpanded, so not in an unpacked git-archive tarball
    refs = set([r.strip() for r in refnames.strip("()").split(",")])
    for ref in list(refs):
        if not re.search(r'\d', ref):
            if verbose:
                print("discarding '%s', no digits" % ref)
            refs.discard(ref)
            # Assume all version tags have a digit. git's %d expansion
            # behaves like git log --decorate=short and strips out the
            # refs/heads/ and refs/tags/ prefixes that would let us
            # distinguish between branches and tags. By ignoring refnames
            # without digits, we filter out many common branch names like
            # "release" and "stabilization", as well as "HEAD" and "master".
    if verbose:
        print("remaining refs: %s" % ",".join(sorted(refs)))
    for ref in sorted(refs):
        # sorting will prefer e.g. "2.0" over "2.0rc1"
        if ref.startswith(tag_prefix):
            r = ref[len(tag_prefix):]
            if verbose:
                print("picking %s" % r)
            return { "version": r,
                     "full": variables["full"].strip() }
    # no suitable tags, so we use the full revision id
    if verbose:
        print("no suitable tags, using full revision id")
    return { "version": variables["full"].strip(),
             "full": variables["full"].strip() }

def versions_from_vcs(tag_prefix, versionfile_source, verbose=False):
    # this runs 'git' from the root of the source tree. That either means
    # someone ran a setup.py command (and this code is in versioneer.py, so
    # IN_LONG_VERSION_PY=False, thus the containing directory is the root of
    # the source tree), or someone ran a project-specific entry point (and
    # this code is in _version.py, so IN_LONG_VERSION_PY=True, thus the
    # containing directory is somewhere deeper in the source tree). This only
    # gets called if the git-archive 'subst' variables were *not* expanded,
    # and _version.py hasn't already been rewritten with a short version
    # string, meaning we're inside a checked out source tree.

    try:
        here = os.path.abspath(__file__)
    except NameError:
        # some py2exe/bbfreeze/non-CPython implementations don't do __file__
        return {} # not always correct

    # versionfile_source is the relative path from the top of the source tree
    # (where the .git directory might live) to this file. Invert this to find
    # the root from __file__.
    root = here
    if IN_LONG_VERSION_PY:
        for i in range(len(versionfile_source.split("/"))):
            root = os.path.dirname(root)
    else:
        root = os.path.dirname(here)
    if not os.path.exists(os.path.join(root, ".git")):
        if verbose:
            print("no .git in %s" % root)
        return {}

    stdout = run_command([GIT, "describe", "--tags", "--dirty", "--always"],
                         cwd=root)
    if stdout is None:
        return {}
    if not stdout.startswith(tag_prefix):
        if verbose:
            print("tag '%s' doesn't start with prefix '%s'" % (stdout, tag_prefix))
        return {}
    tag = stdout[len(tag_prefix):]
    stdout = run_command([GIT, "rev-parse", "HEAD"], cwd=root)
    if stdout is None:
        return {}
    full = stdout.strip()
    if tag.endswith("-dirty"):
        full += "-dirty"
    return {"version": tag, "full": full}


def versions_from_parentdir(parentdir_prefix, versionfile_source, verbose=False):
    if IN_LONG_VERSION_PY:
        # We're running from _version.py. If it's from a source tree
        # (execute-in-place), we can work upwards to find the root of the
        # tree, and then check the parent directory for a version string. If
        # it's in an installed application, there's no hope.
        try:
            here = os.path.abspath(__file__)
        except NameError:
            # py2exe/bbfreeze/non-CPython don't have __file__
            return {} # without __file__, we have no hope
        # versionfile_source is the relative path from the top of the source
        # tree to _version.py. Invert this to find the root from __file__.
        root = here
        for i in range(len(versionfile_source.split("/"))):
            root = os.path.dirname(root)
    else:
        # we're running from versioneer.py, which means we're running from
        # the setup.py in a source tree. sys.argv[0] is setup.py in the root.
        here = os.path.abspath(sys.argv[0])
        root = os.path.dirname(here)

    # Source tarballs conventionally unpack into a directory that includes
    # both the project name and a version string.
    dirname = os.path.basename(root)
    if not dirname.startswith(parentdir_prefix):
        if verbose:
            print("guessing rootdir is '%s', but '%s' doesn't start with prefix '%s'" %
                  (root, dirname, parentdir_prefix))
        return None
    return {"version": dirname[len(parentdir_prefix):], "full": ""}


def do_vcs_install(versionfile_source, ipy):
    run_command([GIT, "add", "versioneer.py"])
    run_command([GIT, "add", versionfile_source])
    run_command([GIT, "add", ipy])
    present = False
    try:
        f = open(".gitattributes", "r")
        for line in f.readlines():
            if line.strip().startswith(versionfile_source):
                if "export-subst" in line.strip().split()[1:]:
                    present = True
        f.close()
    except EnvironmentError:
        pass
    if not present:
        f = open(".gitattributes", "a+")
        f.write("%s export-subst\n" % versionfile_source)
        f.close()
        run_command([GIT, "add", ".gitattributes"])


SHORT_VERSION_PY = """
# This file was generated by 'versioneer.py' (0.7+) from
# revision-control system data, or from the parent directory name of an
# unpacked source archive. Distribution tarballs contain a pre-generated copy
# of this file.

version_version = '%(version)s'
version_full = '%(full)s'
def get_versions(default={}, verbose=False):
    return {'version': version_version, 'full': version_full}

"""

DEFAULT = {"version": "unknown", "full": "unknown"}

def versions_from_file(filename):
    versions = {}
    try:
        f = open(filename)
    except EnvironmentError:
        return versions
    for line in f.readlines():
        mo = re.match("version_version = '([^']+)'", line)
        if mo:
            versions["version"] = mo.group(1)
        mo = re.match("version_full = '([^']+)'", line)
        if mo:
            versions["full"] = mo.group(1)
    return versions

def write_to_version_file(filename, versions):
    f = open(filename, "w")
    f.write(SHORT_VERSION_PY % versions)
    f.close()
    print("set %s to '%s'" % (filename, versions["version"]))


def get_best_versions(versionfile, tag_prefix, parentdir_prefix,
                      default=DEFAULT, verbose=False):
    # returns dict with two keys: 'version' and 'full'
    #
    # extract version from first of _version.py, 'git describe', parentdir.
    # This is meant to work for developers using a source checkout, for users
    # of a tarball created by 'setup.py sdist', and for users of a
    # tarball/zipball created by 'git archive' or github's download-from-tag
    # feature.

    variables = get_expanded_variables(versionfile_source)
    if variables:
        ver = versions_from_expanded_variables(variables, tag_prefix)
        if ver:
            if verbose: print("got version from expanded variable %s" % ver)
            return ver

    ver = versions_from_file(versionfile)
    if ver:
        if verbose: print("got version from file %s %s" % (versionfile, ver))
        return ver

    ver = versions_from_vcs(tag_prefix, versionfile_source, verbose)
    if ver:
        if verbose: print("got version from git %s" % ver)
        return ver

    ver = versions_from_parentdir(parentdir_prefix, versionfile_source, verbose)
    if ver:
        if verbose: print("got version from parentdir %s" % ver)
        return ver

    if verbose: print("got version from default %s" % ver)
    return default

def get_versions(default=DEFAULT, verbose=False):
    assert versionfile_source is not None, "please set versioneer.versionfile_source"
    assert tag_prefix is not None, "please set versioneer.tag_prefix"
    assert parentdir_prefix is not None, "please set versioneer.parentdir_prefix"
    return get_best_versions(versionfile_source, tag_prefix, parentdir_prefix,
                             default=default, verbose=verbose)
def get_version(verbose=False):
    return get_versions(verbose=verbose)["version"]

class cmd_version(Command):
    description = "report generated version string"
    user_options = []
    boolean_options = []
    def initialize_options(self):
        pass
    def finalize_options(self):
        pass
    def run(self):
        ver = get_version(verbose=True)
        print("Version is currently: %s" % ver)


class cmd_build(_build):
    def run(self):
        versions = get_versions(verbose=True)
        _build.run(self)
        # now locate _version.py in the new build/ directory and replace it
        # with an updated value
        target_versionfile = os.path.join(self.build_lib, versionfile_build)
        print("UPDATING %s" % target_versionfile)
        os.unlink(target_versionfile)
        f = open(target_versionfile, "w")
        f.write(SHORT_VERSION_PY % versions)
        f.close()

class cmd_sdist(_sdist):
    def run(self):
        versions = get_versions(verbose=True)
        self._versioneer_generated_versions = versions
        # unless we update this, the command will keep using the old version
        self.distribution.metadata.version = versions["version"]
        return _sdist.run(self)

    def make_release_tree(self, base_dir, files):
        _sdist.make_release_tree(self, base_dir, files)
        # now locate _version.py in the new base_dir directory (remembering
        # that it may be a hardlink) and replace it with an updated value
        target_versionfile = os.path.join(base_dir, versionfile_source)
        print("UPDATING %s" % target_versionfile)
        os.unlink(target_versionfile)
        f = open(target_versionfile, "w")
        f.write(SHORT_VERSION_PY % self._versioneer_generated_versions)
        f.close()

INIT_PY_SNIPPET = """
from ._version import get_versions
__version__ = get_versions()['version']
del get_versions
"""

class cmd_update_files(Command):
    description = "modify __init__.py and create _version.py"
    user_options = []
    boolean_options = []
    def initialize_options(self):
        pass
    def finalize_options(self):
        pass
    def run(self):
        ipy = os.path.join(os.path.dirname(versionfile_source), "__init__.py")
        print(" creating %s" % versionfile_source)
        f = open(versionfile_source, "w")
        f.write(LONG_VERSION_PY % {"DOLLAR": "$",
                                   "TAG_PREFIX": tag_prefix,
                                   "PARENTDIR_PREFIX": parentdir_prefix,
                                   "VERSIONFILE_SOURCE": versionfile_source,
                                   })
        f.close()
        try:
            old = open(ipy, "r").read()
        except EnvironmentError:
            old = ""
        if INIT_PY_SNIPPET not in old:
            print(" appending to %s" % ipy)
            f = open(ipy, "a")
            f.write(INIT_PY_SNIPPET)
            f.close()
        else:
            print(" %s unmodified" % ipy)
        do_vcs_install(versionfile_source, ipy)

def get_cmdclass():
    return {'version': cmd_version,
            'update_files': cmd_update_files,
            'build': cmd_build,
            'sdist': cmd_sdist,
            }

########NEW FILE########
__FILENAME__ = makeweb
#!/usr/bin/env python

# Usage: run "python makeweb.py src web" to update files
# under 'web'. See "python makeweb.py --help" for more options.

import os, sys, shutil
from stat import *
from optparse import OptionParser


# how to process files that match various filename patterns
FILE_ACTION_TBL = [

    # selector_func(infilepath) -> True|False
    # output_filepath_func(outfilepath) -> outfilepath
    # cmd_line_func(opts, infilepath, outfilepath) -> cmdline|None

    ( lambda f: f.endswith('.py'),
      lambda o: o.replace('.py', '.html'),
      lambda opts, i, o: "source-highlight --input='%s' --output='%s'" \
        % (i, o) ),

    ( lambda f: f.endswith('userguide.txt'),
      lambda o: o.replace('.txt', '.html'),
      lambda opts, i, o: "asciidoc --unsafe --conf-file='%s/layout.conf' -a icons -a toc -o '%s' '%s'" \
        % (opts.srcdir, o, i) ),

    ( lambda f: f.endswith('.txt'),
      lambda o: o.replace('.txt', '.html'),
      lambda opts, i, o: "asciidoc --unsafe --conf-file='%s/layout.conf' -a icons -o '%s' '%s'" \
        % (opts.srcdir, o, i) ),

    ( lambda f: f.endswith('layout.conf') or f.endswith('.svn') or f.endswith('.inc'),
      lambda o: o,
      lambda opts, i, o: None )
]


# list of directories to skip
DIR_SKIP_TBL = [
    '.svn'
]


def _is_older(inp, outp):
    older = True
    if os.path.exists(outp):
        modin  = os.stat(inp)[ST_MTIME]
        modout = os.stat(outp)[ST_MTIME]
        older = (modin > modout)
    return older


def _rmtree_warn(fn, path, excinfo):
    print("** WARNING **: error while doing %s on %s" % (fn, path))


def _can_skip(opts, infile, outfile):
    return not _is_older(infile, outfile) and not opts.force


def process_file(opts, infile, outfile):

    for matchfn, outfilefn, cmdfn in FILE_ACTION_TBL:
        if matchfn(infile):
            outfile_actual = outfilefn(outfile)
            cmd = cmdfn(opts, infile, outfile_actual)
            if _can_skip(opts, infile, outfile_actual):
                if opts.verbose >= 2:
                    print("up to date %s -> %s" % (infile, outfile_actual))
                return
            if cmd:
                # do cmd
                if opts.verbose:
                    print("process %s -> %s" % (infile, outfile_actual))
                if opts.verbose >= 3:
                    print("command is [%s]" % cmd)
                if not opts.dryrun:
                    os.system(cmd)
            # else if cmd is None, do nothing
            return

    # nothing matched, default action is to copy
    if not _can_skip(opts, infile, outfile):
        if opts.verbose:
            print("copying %s -> %s" % (infile, outfile))
        if not opts.dryrun:
            shutil.copy(infile, outfile)


def make(opts, indir, outdir):

    # does outdir exists?
    odexists = os.path.exists(outdir)

    # if it exists, it must be a dir!
    if odexists and not os.path.isdir(outdir):
        print("** WARNING **: output dir '%s' exists but is " \
            "not a dir, skipping" % outdir)
        return

    # make outdir if not existing
    if not odexists:
        if opts.verbose:
            print("creating %s" % outdir)
        if not opts.dryrun:
            os.mkdir(outdir)

    # process indir/* -> outdir/*
    for elem in os.listdir(indir):
        inp = os.path.join(indir, elem)
        outp = os.path.join(outdir, elem)

        # process files
        if os.path.isfile(inp):
            if os.path.exists(outp) and not os.path.isfile(outp):
                print("** WARNING **: output '%s' corresponding to " \
                    "input '%s' is not a file, skipping" % (outp, inp))
            else:
                process_file(opts, inp, outp)

        # process directories
        elif os.path.isdir(inp):
            # if dir is in skip list, silently ignore
            if elem in DIR_SKIP_TBL:
                if opts.verbose >= 3:
                    print("skipping %s" % inp)
                continue
            # just recurse
            make(opts, inp, outp)

        # neither a file nor a dir
        else:
            print("** WARNING **: input '%s' is neither file nor " \
                "dir, skipping" % inp)


def get_opts():
    usage = "usage: %prog [options] srcdir destdir"

    p = OptionParser(usage=usage)
    p.add_option("-f", "--force", action="store_true", dest="force", default=False,
        help="ignore timestamps and force build of all files")
    p.add_option("-v", "--verbose", action="count", dest="verbose", default=0,
        help="be chatty (use more v's to be more friendly)")
    p.add_option("-c", "--clean-first", action="store_true", dest="clean", default=False,
        help="remove outdir and everything under it before building")
    p.add_option("-n", "--dry-run", action="store_true", dest="dryrun", default=False,
        help="just print what will happen rather than doing it")

    (opts, args) = p.parse_args()
    if len(args) != 2:
        p.error("incorrect number of arguments")
    srcdir, destdir = args

    if not os.path.exists(srcdir):
        p.error("srcdir (%s) does not exist" % srcdir)
    if not os.path.isdir(args[0]):
        p.error("srcdir (%s) is not a directory" % srcdir)
    if os.path.exists(destdir) and not os.path.isdir(destdir):
        p.error("destdir (%s) is not a directory" % destdir)

    if opts.verbose == None:
        opts.verbose = 0

    # add srcdir and destdir also to opts
    opts.srcdir = srcdir
    opts.destdir = destdir

    return (opts, srcdir, destdir)


def main():
    opts, src, dest = get_opts()
    if opts.verbose >= 3:
        print(("running with options:\nsrc = [%s]\ndest = [%s]\nverbose = [%d]\n" +\
            "dry-run = [%d]\nclean-first = [%d]\nforce = [%d]") %\
            (src, dest, opts.verbose, opts.dryrun, opts.clean, opts.force))
    if opts.dryrun and opts.verbose == 0:
        opts.verbose = 1
    if opts.clean:
        if opts.dryrun or opts.verbose:
            print("removing tree %s" % dest)
        if not opts.dryrun:
            os.rmtree(dest, True, _rmtree_warn)
    make(opts, src, dest)


main()


########NEW FILE########
__FILENAME__ = JITTutorial1
../../../test/JITTutorial1.py
########NEW FILE########
__FILENAME__ = JITTutorial2
../../../test/JITTutorial2.py
########NEW FILE########
