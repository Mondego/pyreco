__FILENAME__ = foobar
# This is a dummy Python code that will be used as a module for Pythonect Interpreter testing purposes

if __name__ == "__main__":

    print "Goodbye, world"

else:

    print "Hello, world"

########NEW FILE########
__FILENAME__ = test_interpreter
# Copyright (c) 2012-2013, Itzik Kotler
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#
#     * Neither the name of the author nor the names of its contributors may
#       be used to endorse or promote products derived from this software without
#       specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

try:

    # If < Python 2.7, use the backported unittest2 package

    import unittest2 as unittest

except ImportError:

    # Probably > Python 2.7, use unittest

    import unittest


import sys
import re
import copy
import imp
import shlex
import os


# Consts

BASE_DIR = os.path.join(os.path.dirname(__file__), os.pardir)
TEST_DIR = os.path.dirname(os.path.abspath(__file__))


# Local imports

pythonect_interpreter = imp.load_source('pythonect_interpreter', BASE_DIR + os.sep + 'pythonect')


def _not_buffered():

    return hasattr(sys.stdout, "getvalue") is False


class TestPythonectInterpreter(unittest.TestCase):

    @unittest.skipIf(_not_buffered(), 'sys.stdout is not buffered')
    def test_command_mode(self):

        pythonect_interpreter.main(argv=shlex.split("""pythonect -c '"Hello, world" -> print'"""))

        self.assertRegexpMatches(sys.stdout.getvalue().strip(), '.*Hello, world.*')

    @unittest.skipIf(_not_buffered(), 'sys.stdout is not buffered')
    def test_script_mode_p2y(self):

        pythonect_interpreter.main(argv=shlex.split('pythonect ' + TEST_DIR + os.sep + 'helloworld.p2y'))

        self.assertRegexpMatches(sys.stdout.getvalue().strip(), '.*Hello, world.*')

    @unittest.skipIf(_not_buffered(), 'sys.stdout is not buffered')
    def test_script_mode_dia(self):

        pythonect_interpreter.main(argv=shlex.split('pythonect ' + TEST_DIR + os.sep + 'helloworld.dia'))

        self.assertRegexpMatches(sys.stdout.getvalue().strip(), '.*Hello, world.*')

    @unittest.skipIf(_not_buffered(), 'sys.stdout is not buffered')
    def test_module_mode(self):

        pythonect_interpreter.main(argv=shlex.split('pythonect -m foobar'))

        self.assertRegexpMatches(sys.stdout.getvalue().strip(), '.*Hello, world.*')

    @unittest.skipIf(_not_buffered(), 'sys.stdout is not buffered')
    def test_maxthreads_cmd_option(self):

        pythonect_interpreter.main(argv=shlex.split('pythonect -mt 1 -c "[1,2,3,4,5,6,7,8,9] -> print"'))

        self.assertTrue(len(set(re.findall('Thread-[\d]', sys.stdout.getvalue().strip()))) == 1)

########NEW FILE########
__FILENAME__ = _preamble
# This makes sure that users don't have to set up their environment
# specially in order to run the interpreter.

# This helper is not intended to be packaged or installed, it is only
# a developer convenience. By the time Pythonect is actually installed
# somewhere, the environment should already be set up properly without
# the help of this tool.


import sys
import os


path = os.path.abspath(sys.argv[0])


while os.path.dirname(path) != path:

    if os.path.exists(os.path.join(path, 'pythonect', '__init__.py')):

        sys.path.insert(0, path)

        break

    path = os.path.dirname(path)

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# Pythonect documentation build configuration file, created by
# sphinx-quickstart on Sat May 11 18:31:27 2013.
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
sys.path.insert(0, os.path.abspath('..'))

import pythonect

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.ifconfig']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'Pythonect'
copyright = u'2013, Itzik Kotler'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '.'.join(pythonect.__version__.split('.')[:2])
# The full version, including alpha/beta/rc tags.
release = pythonect.__version__

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

# If true, keep warnings as "system message" paragraphs in the built documents.
#keep_warnings = False


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
htmlhelp_basename = 'Pythonectdoc'


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
  ('index', 'Pythonect.tex', u'Pythonect Documentation',
   u'Itzik Kotler', 'manual'),
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
    ('index', 'pythonect', u'Pythonect Documentation',
     [u'Itzik Kotler'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'Pythonect', u'Pythonect Documentation',
   u'Itzik Kotler', 'Pythonect', 'One line description of project.',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'

# If true, do not generate a @detailmenu in the "Top" node's menu.
#texinfo_no_detailmenu = False

########NEW FILE########
__FILENAME__ = eval
# Copyright (c) 2012-2013, Itzik Kotler
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#
#     * Neither the name of the author nor the names of its contributors may
#       be used to endorse or promote products derived from this software without
#       specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import __builtin__ as python
import threading
import copy
import logging
import importlib
import site
import os
import multiprocessing
import multiprocessing.dummy
import multiprocessing.pool
import pickle
import networkx
import re
import pprint


# Local imports

import parsers
import lang
import _graph


# Consts

SUB_EXPRESSION = re.compile("`(?P<sub_expr>.*)`")


# Global variables

global_interpreter_lock = threading.Lock()


# Classes

class _PythonectResult(object):

    def __init__(self, values):

        self.values = values


class _PythonectLazyRunner(object):

    def __init__(self, node):

        self.node = node

    def go(self, graph, reduces):

        reduced_value = []

        # TODO: Merge dicts and not pick the 1st one

        locals_ = reduces[self.node][0]['locals']

        globals_ = reduces[self.node][0]['globals']

        for values in reduces[self.node]:

            reduced_value.append(values['last_value'])

        locals_['_'] = globals_['_'] = reduced_value

        return _run(graph, self.node, globals_, locals_, {'as_reduce': True}, None, False)


# Functions

def __isiter(object):

    try:

        iter(object)

        return True

    except TypeError:

        return False


def __pickle_safe_dict(locals_or_globals):

    result = dict(locals_or_globals)

    for k, v in locals_or_globals.iteritems():

        try:

            # NOTE: Is there a better/faster way?

            pickle.dump(v, open(os.devnull, 'w'))

        except Exception:

            del result[k]

    return result


def __create_pool(globals_, locals_):

    return multiprocessing.dummy.Pool(locals_.get('__MAX_THREADS_PER_FLOW__', multiprocessing.cpu_count() + 1))


def __resolve_and_merge_results(results_list):

    resolved = []

    try:

        for element in results_list:

            if isinstance(element, multiprocessing.pool.ApplyResult):

                element = element.get()

            if isinstance(element, list):

                for sub_element in element:

                    resolved.append(sub_element)

            else:

                resolved.append(element)

    except TypeError:

        resolved = results_list

    return resolved


def _run_next_virtual_nodes(graph, node, globals_, locals_, flags, pool, result):

    operator = graph.node[node].get('OPERATOR', None)

    return_value = []

    not_safe_to_iter = False

    is_head_result = True

    head_result = None

    # "Hello, world" or {...}

    if isinstance(result, (basestring, dict)) or not __isiter(result):

        not_safe_to_iter = True

    # [[1]]

    if isinstance(result, list) and len(result) == 1 and isinstance(result[0], list):

        result = result[0]

        not_safe_to_iter = True

    # More nodes ahead?

    if operator:

        if not_safe_to_iter:

            logging.debug('not_safe_to_iter is True for %s' % result)

            head_result = result

            tmp_globals = copy.copy(globals_)

            tmp_locals = copy.copy(locals_)

            tmp_globals['_'] = tmp_locals['_'] = head_result

            return_value = __resolve_and_merge_results(_run(graph, node, tmp_globals, tmp_locals, {}, None, True))

        else:

            # Originally this was implemented using result[0] and result[1:] but xrange() is not slice-able, thus, I have changed it to `for` with buffer for 1st result

            for res_value in result:

                logging.debug('Now at %s from %s' % (res_value, result))

                if is_head_result:

                    logging.debug('is_head_result is True for %s' % res_value)

                    is_head_result = False

                    head_result = res_value

                    tmp_globals = copy.copy(globals_)

                    tmp_locals = copy.copy(locals_)

                    tmp_globals['_'] = tmp_locals['_'] = head_result

                    return_value.insert(0, _run(graph, node, tmp_globals, tmp_locals, {}, None, True))

                    continue

                tmp_globals = copy.copy(globals_)

                tmp_locals = copy.copy(locals_)

                tmp_globals['_'] = tmp_locals['_'] = res_value

                # Synchronous

                if operator == '|':

                    return_value.append(pool.apply(_run, args=(graph, node, tmp_globals, tmp_locals, {}, None, True)))

                # Asynchronous

                if operator == '->':

                    return_value.append(pool.apply_async(_run, args=(graph, node, tmp_globals, tmp_locals, {}, None, True)))

            pool.close()

            pool.join()

            pool.terminate()

            logging.debug('return_value = %s' % return_value)

            return_value = __resolve_and_merge_results(return_value)

    # Loopback

    else:

        # AS IS

        if not_safe_to_iter:

            return_value = [result]

        # Iterate for all possible *return values*

        else:

            for res_value in result:

                return_value.append(res_value)

            # Unbox

            if len(return_value) == 1:

                return_value = return_value[0]

    return return_value


def __import_module_from_exception(exception, globals_):

    # NameError: name 'os' is not defined
    #  - OR -
    # NameError: global name 'os' is not defined

    mod_name = exception.message[exception.message.index("'") + 1:exception.message.rindex("'")]

    globals_.update({mod_name: importlib.import_module(mod_name)})


def __pythonect_preprocessor(current_value):

    current_value = current_value.strip()

    flags = {'spawn_as_process': False, 'spawn_as_reduce': False}

    # foobar(_!)

    if current_value.find('_!') != -1:

        current_value = current_value.replace('_!', '_')

        flags['spawn_as_reduce'] = True

    # foobar &

    if current_value.endswith('&'):

        current_value = current_value[:-1].strip()

        flags['spawn_as_process'] = True

    # foobar@xmlrpc://...

    for function_address in re.findall('.*\@.*', current_value):

        (fcn_name, fcn_host) = function_address.split('@')

        left_parenthesis = fcn_name.find('(')

        right_parenthesis = fcn_name.find(')')

        # foobar(1,2,3)@xmlrpc://...

        if left_parenthesis > -1 and right_parenthesis > -1:

            # `1,2,3`

            fcn_args = fcn_name[left_parenthesis + 1:right_parenthesis]

            # `foobar`

            fcn_name = fcn_name.split('(')[0]

            current_value = current_value.replace(function_address, '__builtins__.remotefunction(\'' + fcn_name + '\',\'' + fcn_host + '\',' + fcn_args + ')')

        # foobar@xmlrpc://...

        else:

            current_value = current_value.replace(function_address, '__builtins__.remotefunction(\'' + fcn_name + '\',\'' + fcn_host + '\')')

    # foobar(`1 -> _+1`)

    current_value = SUB_EXPRESSION.sub("__builtins__.expr(\'\g<sub_expr>\')(globals(), locals())", current_value)

    # Replace `print` with `print_`

    if current_value == 'print':

        current_value = 'print_'

    if current_value.startswith('print'):

        current_value = 'print_(' + current_value[5:] + ')'

    return current_value, flags


def __node_main(current_value, last_value, globals_, locals_):

    logging.info('In __node_main, current_value = %s, last_value = %s' % (current_value, last_value))

    return_value = None

    try:

        ###################################
        # Try to eval()uate current_value #
        ###################################

        try:

            return_value = python.eval(current_value, globals_, locals_)

        # Autoloader Try & Catch

        except NameError as e:

            try:

                __import_module_from_exception(e, globals_)

                return_value = python.eval(current_value, globals_, locals_)

            except Exception as e1:

                raise e1

        # Current value is already Python Object

        except TypeError as e:

            # Due to eval()?

            if (e.message == 'eval() arg 1 must be a string or code object'):

                return_value = current_value

            else:

                raise e

        ##########################
        # eval() Post Processing #
        ##########################

        if isinstance(return_value, lang.remotefunction):

            return_value.evaluate_host(globals_, locals_)

        if isinstance(return_value, dict):

            if last_value is not None:

                return_value = return_value.get(last_value, False)

        if return_value is None or (isinstance(return_value, bool) and return_value is True):

            return_value = last_value

        if callable(return_value):

            # Ignore "copyright", "credits", "license", and "help"

            if isinstance(return_value, (site._Printer, site._Helper)):

                return_value = return_value()

            else:

                try:

                    return_value = return_value(last_value)

                except TypeError as e:

                    if e.args[0].find('takes no arguments') != -1:

                        return_value = return_value()

                    else:

                        raise e

                if return_value is None:

                    return_value = last_value

    except SyntaxError as e:

        ##################################
        # Try to exec()ute current_value #
        ##################################

        try:

            exec current_value in globals_, locals_

        # Autoloader Try & Catch

        except NameError as e:

            try:

                __import_module_from_exception(e, globals_)

                exec current_value in globals_, locals_

            except Exception as e1:

                raise e1

        return_value = last_value

    return return_value


def _run_next_graph_nodes(graph, node, globals_, locals_, pool):

    operator = graph.node[node].get('OPERATOR', None)

    nodes_return_value = []

    return_value = None

    # False? Terminate Flow.

    if isinstance(locals_['_'], bool) and locals_['_'] is False:

        return False

    if operator:

        #   -->  (a)
        #   --> / | \
        #    (b) (c) (d)
        #       \ | /
        #        (e)

        next_nodes = sorted(graph.successors(node))

        # N-1

        for next_node in next_nodes[1:]:

            # Synchronous

            if operator == '|':

                nodes_return_value.append(pool.apply(_run, args=(graph, next_node, globals_, locals_, {}, None, False)))

            # Asynchronous

            if operator == '->':

                nodes_return_value.append(pool.apply_async(_run, args=(graph, next_node, globals_, locals_, {}, None, False)))

        # 1

        nodes_return_value.insert(0, _run(graph, next_nodes[0], globals_, locals_, {}, None, False))

        pool.close()

        pool.join()

        pool.terminate()

        return_value = __resolve_and_merge_results(nodes_return_value)

    else:

        #        (a)
        #       / | \
        #    (b) (c) (d)
        #       \ | /
        #    --> (e)

        return_value = locals_['_']

    return return_value


def __apply_current(func, args=(), kwds={}):

    return func(*args, **kwds)


def _run(graph, node, globals_, locals_, flags, pool=None, is_virtual_node=False):

    return_value = None

    if not pool:

        pool = __create_pool(globals_, locals_)

    if is_virtual_node:

        #   `[1,2,3] -> print`
        #
        #       =
        #
        #   ([1,2,3])
        #       |
        #    (print)
        #
        #       =
        #
        #   ([1,2,3])
        #   /   |   \
        #  {1} {2} {3} <-- virtual node
        #   \   |   /
        #    (print)

        # Call original `node` successors with `_` set as `virtual_node_value`

        return_value = _run_next_graph_nodes(graph, node, globals_, locals_, pool)

    else:

        #   `[1,2,3] -> print`
        #
        #       =
        #
        #   ([1,2,3])
        #       |
        #    (print)
        #
        #       =
        #
        #   ([1,2,3]) <-- node
        #   /   |   \
        #  {1} {2} {3}
        #   \   |   /
        #    (print)

        current_value = graph.node[node]['CONTENT']

        last_value = globals_.get('_', locals_.get('_', None))

        runner = __apply_current

        input_value = None

        code_flags = {}

        # Code or Literal?

        if not current_value.startswith('"') and not current_value.startswith("'") and not current_value[0] in [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]:

            # Preprocess Code

            try:

                logging.debug('Before __pythonect_preprocessor, value = %s' % current_value)

                input_value, code_flags = __pythonect_preprocessor(current_value)

                logging.debug('After __pythonect_preprocessor, value = %s' % input_value)

            except:

                # AS IS (Already Python Object)

                input_value = current_value

            # Run as Reduce?

            if code_flags.get('spawn_as_reduce', False) and flags.get('as_reduce', False) is False:

                return _PythonectResult({'node': node, 'input_value': input_value, 'last_value': last_value, 'locals': locals_, 'globals': globals_})

            # Run as a New Process?

            if code_flags.get('spawn_as_process', False):

                runner = multiprocessing.Pool(1).apply

                globals_ = __pickle_safe_dict(globals_)

                locals_ = __pickle_safe_dict(locals_)

        else:

            # Literal

            input_value = current_value

        # Run Code

        result = runner(__node_main, args=(input_value, last_value, globals_, locals_))

        # Call self with each result value as `virtual_node`

        return_value = _run_next_virtual_nodes(graph, node, globals_, locals_, flags, pool, result)

    return return_value


def __extend_builtins(globals_):

    # TODO: Is there any advantage to manually duplicate __builtins__, instead of passing our own?

    globals_['__builtins__'] = python

    # Add `pythonect.lang` to Python's `__builtins__`

    for name in dir(lang):

        # i.e. __builtins__.print_ = pythonect.lang.print_

        setattr(globals_['__builtins__'], name, getattr(lang, name))

    # Add GIL

    setattr(globals_['__builtins__'], '__GIL__', global_interpreter_lock)

    # Fix "copyright", "credits", and "license"

    setattr(globals_['__builtins__'], 'copyright', site._Printer("copyright", "Copyright (c) 2012-2013 by Itzik Kotler and others.\nAll Rights Reserved."))
    setattr(globals_['__builtins__'], 'credits', site._Printer("credits", "See www.pythonect.org for more information."))
    setattr(globals_['__builtins__'], 'license', site._Printer("license", "See https://github.com/ikotler/pythonect/blob/master/LICENSE", ["LICENSE"], [os.path.abspath(__file__ + "/../../../")]))

    # Map eval() to Pythonect's eval, and __eval__ to Python's eval

    globals_['__eval__'] = getattr(globals_['__builtins__'], 'eval')
    globals_['eval'] = eval

    # Default `iterate_literal_arrays`

    if not '__ITERATE_LITERAL_ARRAYS__' in globals_:

        globals_['__ITERATE_LITERAL_ARRAYS__'] = True

    return globals_


def _is_referencing_underscore(graph, node):

    if graph.node[node]['CONTENT'] == '_':

        return True

    return False


def parse(source):
    """Parse the source into a directed graph (i.e. networkx.DiGraph)

    Args:
        source: A string representing a Pythonect code.

    Returns:
        A directed graph (i.e. networkx.DiGraph) of Pythonect symbols.

    Raises:
        SyntaxError: An error occurred parsing the code.
    """

    graph = _graph.Graph()

    for ext, parser in parsers.get_parsers(os.path.abspath(os.path.join(os.path.dirname(parsers.__file__), '..', 'parsers'))).items():

        logging.debug('Trying to parse %s with %s' % (source, parser))

        tmp_graph = parser.parse(source)

        if tmp_graph is not None:

            logging.debug('Parsed successfully with %s, total nodes = %d' % (parser, len(tmp_graph.nodes())))

            if len(tmp_graph.nodes()) > len(graph.nodes()):

                graph = tmp_graph

    logging.info('Parsed graph contains %d nodes' % len(graph.nodes()))

    return graph


def eval(source, globals_={}, locals_={}):
    """Evaluate Pythonect code in the context of globals and locals.

    Args:
        source: A string representing a Pythonect code or a networkx.DiGraph() as
            returned by parse()
        globals: A dictionary.
        locals: Any mapping.

    Returns:
        The return value is the result of the evaluated code.

    Raises:
        SyntaxError: An error occurred parsing the code.
    """

    return_value = None

    # Meaningful program?

    if source != "pass":

        logging.info('Program is meaningful')

        return_value = []

        return_values = []

        globals_values = []

        locals_values = []

        tasks = []

        reduces = {}

        logging.debug('Evaluating %s with globals_ = %s and locals_ %s' % (source, globals_, locals_))

        if not isinstance(source, networkx.DiGraph):

            logging.info('Parsing program...')

            graph = parse(source)

        else:

            logging.info('Program is already parsed! Using source AS IS')

            graph = source

        root_nodes = sorted([node for node, degree in graph.in_degree().items() if degree == 0])

        if not root_nodes:

            cycles = networkx.simple_cycles(graph)

            if cycles:

                logging.info('Found cycles: %s in graph, using nodes() 1st node (i.e. %s) as root node' % (cycles, graph.nodes()[0]))

                root_nodes = [graph.nodes()[0]]

        logging.info('There are %d root node(s)' % len(root_nodes))

        logging.debug('Root node(s) are: %s' % root_nodes)

        # Extend Python's __builtin__ with Pythonect's `lang`

        start_globals_ = __extend_builtins(globals_)

        logging.debug('Initial globals_:\n%s' % pprint.pformat(start_globals_))

        # Default input

        start_globals_['_'] = start_globals_.get('_', locals_.get('_', None))

        logging.info('_ equal %s', start_globals_['_'])

        # Execute Pythonect program

        pool = __create_pool(globals_, locals_)

        # N-1

        for root_node in root_nodes[1:]:

            if globals_.get('__IN_EVAL__', None) is None and not _is_referencing_underscore(graph, root_node):

                # Reset '_'

                globals_['_'] = locals_['_'] = None

            if globals_.get('__IN_EVAL__', None) is None:

                globals_['__IN_EVAL__'] = True

            temp_globals_ = copy.copy(globals_)

            temp_locals_ = copy.copy(locals_)

            task_result = pool.apply_async(_run, args=(graph, root_node, temp_globals_, temp_locals_, {}, None, False))

            tasks.append((task_result, temp_locals_, temp_globals_))

        # 1

        if globals_.get('__IN_EVAL__', None) is None and not _is_referencing_underscore(graph, root_nodes[0]):

            # Reset '_'

            globals_['_'] = locals_['_'] = None

        if globals_.get('__IN_EVAL__', None) is None:

            globals_['__IN_EVAL__'] = True

        result = _run(graph, root_nodes[0], globals_, locals_, {}, None, False)

        # 1

        for expr_return_value in result:

            globals_values.append(globals_)

            locals_values.append(locals_)

            return_values.append([expr_return_value])

        # N-1

        for (task_result, task_locals_, task_globals_) in tasks:

            return_values.append(task_result.get())

            locals_values.append(task_locals_)

            globals_values.append(task_globals_)

        # Reduce + _PythonectResult Grouping

        for item in return_values:

            # Is there _PythonectResult in item list?

            for sub_item in item:

                if isinstance(sub_item, _PythonectResult):

                    # 1st Time?

                    if sub_item.values['node'] not in reduces:

                        reduces[sub_item.values['node']] = []

                        # Add Place holder to mark the position in the return value list

                        return_value.append(_PythonectLazyRunner(sub_item.values['node']))

                    reduces[sub_item.values['node']] = reduces[sub_item.values['node']] + [sub_item.values]

                else:

                    return_value.append(sub_item)

        # Any _PythonectLazyRunner's?

        if reduces:

            for return_item_idx in xrange(0, len(return_value)):

                if isinstance(return_value[return_item_idx], _PythonectLazyRunner):

                    # Swap list[X] with list[X.go(reduces)]

                    return_value[return_item_idx] = pool.apply_async(return_value[return_item_idx].go, args=(graph, reduces))

            return_value = __resolve_and_merge_results(return_value)

        # [...] ?

        if return_value:

            # Single return value? (e.g. [1])

            if len(return_value) == 1:

                return_value = return_value[0]

            # Update globals_ and locals_

#            globals_, locals_ = __merge_all_globals_and_locals(globals_, locals_, globals_values, {}, locals_values, {})

        # Set `return value` as `_`

        globals_['_'] = locals_['_'] = return_value

        if globals_.get('__IN_EVAL__', None) is not None:

            del globals_['__IN_EVAL__']

        pool.close()

        pool.join()

        pool.terminate()

    return return_value

########NEW FILE########
__FILENAME__ = lang
# Copyright (c) 2012-2013, Itzik Kotler
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#
#     * Neither the name of the author nor the names of its contributors may
#       be used to endorse or promote products derived from this software without
#       specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""This file content extends the Python's __builtins__"""

import __builtin__


# Functions

def print_(object_):

    import threading

    import sys

    # START OF CRITICAL SECTION

    __builtin__.__GIL__.acquire()

    try:

        import multiprocessing

        if multiprocessing.current_process().name == 'MainProcess':

            sys.stdout.write("<%s:%s> : %s\n" % (multiprocessing.current_process().name, threading.current_thread().name, object_))

        else:

            sys.stdout.write("<PID #%d> : %s\n" % (multiprocessing.current_process().pid, object_))

    except ImportError:

            sys.stdout.write("<%s> : %s\n" % (threading.current_thread().name, object_))

    sys.stdout.flush()

    __builtin__.__GIL__.release()

    # END OF CRITICAL SECTION

    return None


# Classes

class expr(object):

    def __init__(self, expression):

        self.__expression = expression

    def __repr__(self):

        return self.__expression

    def __call__(self, globals_, locals_):

        import eval

        return eval.eval(self.__expression, globals_, locals_)


class remotefunction(object):

    def __init__(self, name, host, *args, **kwargs):

        self.__name = name.strip()

        self.__host = host

        self.__remote_fcn = None

        self.__remote_fcn_args = args

        self.__remote_fcn_kwargs = kwargs

        self.__locals = None

        self.__globals = None

    def __repr__(self):

        if self.__remote_fcn:

            return repr(self.__remote_fcn)

        else:

            return "%s(%s,%s)@%s" % (self.__name, self.__remote_fcn_args, self.__remote_fcn_kwargs, self.__host)

    def evaluate_host(self, globals_, locals_):

        self.__locals = locals_

        self.__globals = globals_

        try:

            self.__host = eval(self.__host, globals_, locals_)

        except SyntaxError as e:

            # CONST? As it is

            pass

    def __call__(self, *args, **kwargs):

        call_args = args

        call_kwargs = kwargs

        if self.__remote_fcn_args or self.__remote_fcn_kwargs:

            call_args = self.__remote_fcn_args

            call_kwargs = self.__remote_fcn_kwargs

        # Pseudo Protocol

        if self.__host is None or self.__host.startswith('None'):

            self.__remote_fcn = eval(self.__name, self.__globals, self.__locals)

        # Python XML-RPC

        elif self.__host.startswith('xmlrpc://'):

            import xmlrpclib

            # xmlrpc:// = http://, xmlrpcs:// = https://

            remote_srv = xmlrpclib.ServerProxy(self.__host.replace('xmlrpc', 'http', 1))

            self.__remote_fcn = getattr(remote_srv, self.__name)

        return self.__remote_fcn(*call_args, **call_kwargs)

########NEW FILE########
__FILENAME__ = dia
# Copyright (c) 2012-2013, Itzik Kotler
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#
#     * Neither the name of the author nor the names of its contributors may
#       be used to endorse or promote products derived from this software without
#       specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import networkx
import xml.sax
import gzip
import StringIO


# Local imports

import pythonect.internal.parsers
import pythonect.internal._graph


# Tested on dia-bin 0.97.2

class _DiaParser(xml.sax.handler.ContentHandler):

    def __init__(self):

        xml.sax.handler.ContentHandler.__init__(self)

        self._in_dia_object = False

        self._in_dia_string = False

        self.node_name = None

        self.edge = []

        self.node_value = {'OPERATOR': '->'}

    def startElement(self, name, attrs):

        if self._in_dia_object:

            if name == 'dia:string':

                self._in_dia_string = True

            if name == 'dia:connection':

                self.edge.append(attrs['to'])

                if len(self.edge) == 2:

                    self._graph.add_edge(self.edge[0], self.edge[1])

                    self.edge = []

        else:

            if name == 'dia:object':

                if self._graph is None:

                    self._graph = pythonect.internal._graph.Graph()

                self._in_dia_object = True

                self.node_name = attrs['id']

                self._graph.add_node(self.node_name)

    def endElement(self, name):

        if name == 'dia:object':

            self._graph.node[self.node_name].update(self.node_value)

            if self._graph.node[self.node_name].get('CONTENT', None) is None:

                self._graph.remove_node(self.node_name)

            self.node_name = None

            self.node_value = {'OPERATOR': '->'}

            self._in_dia_object = False

        if name == 'dia:string':

            self._in_dia_string = False

    def characters(self, content):

        if self._in_dia_string:

            # Strip leading and trailing '#'

            self.node_value.update({'CONTENT': content[1:-1]})

    def endDocument(self):

        if self._graph is None:

            self._graph = pythonect.internal._graph.Graph()

    def parse(self, source):

        self._graph = None

        try:

            # Compressed?

            try:

                # UTF-8?

                try:

                    source = source.encode('utf-8')

                except UnicodeDecodeError:

                    pass

                source = gzip.GzipFile(fileobj=StringIO.StringIO(source), mode='rb').read()

            except IOError:

                pass

            xml.sax.parseString(source, self)

            # Delete 'OPERATOR' from tail nodes

            tail_nodes = [node for node, degree in self._graph.out_degree().items() if degree == 0]

            for node in tail_nodes:

                del self._graph.node[node]['OPERATOR']

        except xml.sax._exceptions.SAXParseException:

            pass

        return self._graph


class PythonectDiaParser(pythonect.internal.parsers.PythonectInputFileFormatParser):

    def parse(self, source):

        graph = _DiaParser().parse(source)

        return graph

    FILE_EXTS = ['dia']

########NEW FILE########
__FILENAME__ = p2y
# Copyright (c) 2012-2013, Itzik Kotler
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#
#     * Neither the name of the author nor the names of its contributors may
#       be used to endorse or promote products derived from this software without
#       specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import networkx
import tokenize
import StringIO
import re


# Local imports

import pythonect.internal.parsers
import pythonect.internal._graph


def _create_and_link(graph, new_node_name, new_node_kwargs):

    # Add Node

    graph.add_node(new_node_name, **new_node_kwargs)

    # Connect Any Tail Nodes to Node

    for tail_node in [node for node, degree in graph.out_degree().items() if degree == 0 and node != new_node_name]:

        graph.add_edge(tail_node, new_node_name)


def _make_graph(code, node_prefix='', depth=0, in_brackets=False):

    meaningful_graph = False

    update_tail_nodes_operator = False

    create_node = False

    node_value = ""

    edge_value = ""

    previous_tokval = None

    in_literal_scope = 0

    graph = pythonect.internal._graph.Graph()

    tokens = tokenize.generate_tokens(StringIO.StringIO(code).readline)

    token_pos = -1

    seek = 0

    in_statement = False

    in_url = False

    graphs = []

    for toknum, tokval, (srow, scol), (erow, ecol), line in tokens:

        extra_string = ''

        # print "[Row %d, Col %d]: Received (#%d) %s" % (srow, scol, toknum, tokval)

        # Skip over INDENT/NL

        if toknum in [tokenize.INDENT, tokenize.NL, tokenize.NEWLINE, tokenize.DEDENT]:

            continue

        token_pos = token_pos + 1

        # Fast Forward

        if seek > 0:

            seek = seek - 1

            continue

        if not in_url and ((toknum == tokenize.NAME and tokval != '_') or tokval == ':'):

            extra_string = ' '

        node_value = node_value + tokval + extra_string

        # Within '(....)' or '{...}' ?

        if in_literal_scope:

            if tokval in ')}' or in_statement and tokval in ']':

                in_literal_scope = in_literal_scope - 1

            # i.e. ({ ... })

            if tokval in '({' or in_statement and tokval in '[':

                in_literal_scope = in_literal_scope + 1

            continue

        # Start of '@xmlrpc://...' ?

        if tokval == '@':

            in_url = True

            continue

        # Not Within '@xmlrpc://...' ...

        if not in_url:

            # Start of Python Statement Scope?

            if tokval in [':', '=']:

                in_statement = True

                continue

            # Start of '(...)' or '{...}' ?

            if tokval in '({' or in_statement and tokval in '[':

                in_literal_scope = in_literal_scope + 1

                continue

        # '->' Operator?

        if tokval == '>' and previous_tokval == '-':

            meaningful_graph = True

            in_statement = False

            in_url = False

            edge_value = '->'

            # Trim trailing '->'

            node_value = node_value[:-2]

            if node_value:

                create_node = True

            else:

                update_tail_nodes_operator = True

        # '|' Operator?

        if tokval == '|':

            meaningful_graph = True

            in_url = False

            in_statement = False

            edge_value = '|'

            # Trim trailing '|'

            node_value = node_value[:-1]

            if node_value:

                create_node = True

            else:

                update_tail_nodes_operator = True

        # New Node?

        if create_node:

            create_node = False

            _create_and_link(graph, node_prefix + str(len(graphs)) + "." + str(len(graph.nodes())), {'CONTENT': node_value, 'OPERATOR': edge_value, 'TOKEN_TYPE': tokval})

            node_value = ""

        # Update Tail Node(s) Operator? (i.e. [ A , B ] -> C ; -> is of 'A' and 'B')

        if update_tail_nodes_operator:

            update_tail_nodes_operator = False

            for tail_node in [node for node, degree in graph.out_degree().items() if degree == 0]:

                graph.node[tail_node].update({'OPERATOR': edge_value})

        # Start of '[...]'

        if node_value == tokval == '[':

            # Supress '['

            node_value = node_value[:-1]

            # Start New Graph

            (next_token_pos, ret_graph) = _make_graph(code[scol + 1:], node_prefix + str(len(graphs)) + "." + str(len(graph.nodes())) + '.', depth + 1, True)

            # ['1 2 3'.split()]

            if len(ret_graph.nodes()) == 1 and ret_graph.node[ret_graph.nodes()[0]]['CONTENT'].find('(') != -1:

                # AS IS

                node_value = '[' + ret_graph.node[ret_graph.nodes()[0]]['CONTENT'] + ']'

            # [1], [string.split], or [1, 2, 3, ..]

            else:

                in_nodes = [node for node, degree in ret_graph.in_degree().items() if degree == 0]

                out_nodes = [node for node, degree in graph.out_degree().items() if degree == 0]

                graph = networkx.union(graph, ret_graph)

                for in_node in in_nodes:

                    for out_node in out_nodes:

                        graph.add_edge(out_node, in_node)

            seek = next_token_pos

        if tokval == ']' and in_brackets:

            in_brackets = False

            # Trim trailing ']'

            node_value = node_value[:-1]

            if not meaningful_graph and not node_value:

                node_value = '[[' + ','.join([graph.node[node]['CONTENT'] for node in sorted(graph.nodes())]) + ']]'

                graph.clear()

            # Flush node_value

            if node_value:

                _create_and_link(graph, node_prefix + str(len(graphs)) + "." + str(len(graph.nodes())), {'CONTENT': node_value, 'TOKEN_TYPE': tokval})

                node_value = ""

            # Merge graphs? (i.e. [ A -> B , C -> D ])

            if graphs:

                graphs = [graph] + graphs

                graph = reduce(networkx.union, graphs)

            # End Graph

            return (token_pos + 1, graph)

        if tokval == ',':

            meaningful_graph = True

            # Flush node_value

            # Trim trailing ','

            node_value = node_value[:-1]

            _create_and_link(graph, node_prefix + str(len(graphs)) + "." + str(len(graph.nodes())), {'CONTENT': node_value, 'TOKEN_TYPE': tokval})

            node_value = ""

            # Replace graph

            graphs.append(graph)

            # New graph

            graph = pythonect.internal._graph.Graph()

        previous_tokval = tokval

    # EOF

    if node_value:

        _create_and_link(graph, node_prefix + str(len(graphs)) + "." + str(len(graph.nodes())), {'CONTENT': node_value, 'TOKEN_TYPE': tokval})

        node_value = ""

    # Merge graphs? (i.e. [ A -> B , C -> D ])

    if graphs:

        graphs = [graph] + graphs

        graph = reduce(networkx.union, graphs)

    # End Graph

    return (token_pos + 1, graph)


class PythonectScriptParser(pythonect.internal.parsers.PythonectInputFileFormatParser):

    def parse(self, source):

        graph = None

        try:

            (ignored_ret, graph) = _make_graph(re.sub('#.*', '', source.strip()))

        except tokenize.TokenError:

            pass

        return graph

    FILE_EXTS = ['p2y']

########NEW FILE########
__FILENAME__ = test_dia
# Copyright (c) 2012-2013, Itzik Kotler
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#
#     * Neither the name of the author nor the names of its contributors may
#       be used to endorse or promote products derived from this software without
#       specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import unittest
import networkx
import os


# Local imports

import pythonect.internal.parsers.dia


# Consts

BASE_DIR = os.path.join(os.path.dirname(__file__), os.pardir)
TEST_DIR = os.path.dirname(os.path.abspath(__file__))


class TestPythonectDiaParser(unittest.TestCase):

    def test_program_empty(self):

        g = networkx.DiGraph()

        self.assertEqual(len(pythonect.internal.parsers.dia.PythonectDiaParser().parse(open(TEST_DIR + os.sep + 'dia_examples' + os.sep + 'program_empty.dia').read()).nodes()) == len(g.nodes()), True)

    def test_expr_atom(self):

        g = networkx.DiGraph()

        g.add_node('1')

        self.assertEqual(len(pythonect.internal.parsers.dia.PythonectDiaParser().parse(open(TEST_DIR + os.sep + 'dia_examples' + os.sep + 'expr_atom.dia').read()).nodes()) == len(g.nodes()), True)

    def test_even_expr_atom_op_expr(self):

        g = networkx.DiGraph()

        g.add_node('1')

        g.add_node('2')

        g.add_edge('1', '2')

        self.assertEqual(len(pythonect.internal.parsers.dia.PythonectDiaParser().parse(open(TEST_DIR + os.sep + 'dia_examples' + os.sep + 'even_expr_atom_op_expr.dia').read()).edges()) == len(g.edges()), True)

    def test_odd_expr_atom_op_expr(self):

        g = networkx.DiGraph()

        g.add_node('1')

        g.add_node('2')

        g.add_node('3')

        g.add_edge('1', '2')

        g.add_edge('2', '3')

        self.assertEqual(len(pythonect.internal.parsers.dia.PythonectDiaParser().parse(open(TEST_DIR + os.sep + 'dia_examples' + os.sep + 'odd_expr_atom_op_expr.dia').read()).edges()) == len(g.edges()), True)

    def test_gzipped_odd_expr_atom_op_expr(self):

        g = networkx.DiGraph()

        g.add_node('1')

        g.add_node('2')

        g.add_node('3')

        g.add_edge('1', '2')

        g.add_edge('2', '3')

        self.assertEqual(len(pythonect.internal.parsers.dia.PythonectDiaParser().parse(open(TEST_DIR + os.sep + 'dia_examples' + os.sep + 'odd_expr_atom_op_expr_gzipped.dia').read()).edges()) == len(g.edges()), True)

    def test_program_expr_list(self):

        g = networkx.DiGraph()

        g.add_node('1')

        g.add_node('2')

        self.assertEqual(len(pythonect.internal.parsers.dia.PythonectDiaParser().parse(open(TEST_DIR + os.sep + 'dia_examples' + os.sep + 'program_expr_list.dia').read()).nodes()) == len(g.nodes()), True)

########NEW FILE########
__FILENAME__ = test_p2y
# Copyright (c) 2012-2013, Itzik Kotler
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#
#     * Neither the name of the author nor the names of its contributors may
#       be used to endorse or promote products derived from this software without
#       specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import unittest
import networkx


# Local imports

import pythonect.internal.parsers.p2y


class TestPythonectScriptParser(unittest.TestCase):

    def test_program_empty(self):

        g = networkx.DiGraph()

        self.assertEqual(len(pythonect.internal.parsers.p2y.PythonectScriptParser().parse('').nodes()) == len(g.nodes()), True)

    def test_expr_atom(self):

        g = networkx.DiGraph()

        g.add_node('1')

        self.assertEqual(len(pythonect.internal.parsers.p2y.PythonectScriptParser().parse('1').nodes()) == len(g.nodes()), True)

    def test_shebang_line_with_even_expr_atom_op_expr(self):

        g = networkx.DiGraph()

        g.add_node('1')

        g.add_node('2')

        g.add_edge('1', '2')

        self.assertEqual(len(pythonect.internal.parsers.p2y.PythonectScriptParser().parse('#! /usr/bin/env pythonect\n1 -> 1').edges()) == len(g.edges()), True)

    def test_even_expr_atom_op_expr(self):

        g = networkx.DiGraph()

        g.add_node('1')

        g.add_node('2')

        g.add_edge('1', '2')

        self.assertEqual(len(pythonect.internal.parsers.p2y.PythonectScriptParser().parse('1 -> 1').edges()) == len(g.edges()), True)

    def test_odd_expr_atom_op_expr(self):

        g = networkx.DiGraph()

        g.add_node('1')

        g.add_node('2')

        g.add_node('3')

        g.add_edge('1', '2')

        g.add_edge('2', '3')

        self.assertEqual(len(pythonect.internal.parsers.p2y.PythonectScriptParser().parse('1 -> 1 -> 1').edges()) == len(g.edges()), True)

    def test_program_expr_list(self):

        g = networkx.DiGraph()

        g.add_node('1')

        g.add_node('2')

        self.assertEqual(len(pythonect.internal.parsers.p2y.PythonectScriptParser().parse('1 , 2').nodes()) == len(g.nodes()), True)

########NEW FILE########
__FILENAME__ = test_vdx07
# Copyright (c) 2012-2013, Itzik Kotler
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#
#     * Neither the name of the author nor the names of its contributors may
#       be used to endorse or promote products derived from this software without
#       specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import unittest
import networkx
import os


# Local imports

import pythonect.internal.parsers.vdx


# Consts

BASE_DIR = os.path.join(os.path.dirname(__file__), os.pardir)
TEST_DIR = os.path.dirname(os.path.abspath(__file__))


class TestPythonectVisioParser(unittest.TestCase):

    def test_program_empty(self):

        g = networkx.DiGraph()

        self.assertEqual(len(pythonect.internal.parsers.vdx.PythonectVisioParser().parse(open(TEST_DIR + os.sep + 'vdx07_examples' + os.sep + 'program_empty.vdx').read()).nodes()) == len(g.nodes()), True)

    def test_expr_atom(self):

        g = networkx.DiGraph()

        g.add_node('1')

        self.assertEqual(len(pythonect.internal.parsers.vdx.PythonectVisioParser().parse(open(TEST_DIR + os.sep + 'vdx07_examples' + os.sep + 'expr_atom.vdx').read()).nodes()) == len(g.nodes()), True)

    def test_even_expr_atom_op_expr(self):

        g = networkx.DiGraph()

        g.add_node('1')

        g.add_node('2')

        g.add_edge('1', '2')

        self.assertEqual(len(pythonect.internal.parsers.vdx.PythonectVisioParser().parse(open(TEST_DIR + os.sep + 'vdx07_examples' + os.sep + 'even_expr_atom_op_expr.vdx').read()).edges()) == len(g.edges()), True)

    def test_odd_expr_atom_op_expr(self):

        g = networkx.DiGraph()

        g.add_node('1')

        g.add_node('2')

        g.add_node('3')

        g.add_edge('1', '2')

        g.add_edge('2', '3')

        self.assertEqual(len(pythonect.internal.parsers.vdx.PythonectVisioParser().parse(open(TEST_DIR + os.sep + 'vdx07_examples' + os.sep + 'odd_expr_atom_op_expr.vdx').read()).edges()) == len(g.edges()), True)

    def test_program_expr_list(self):

        g = networkx.DiGraph()

        g.add_node('1')

        g.add_node('2')

        self.assertEqual(len(pythonect.internal.parsers.vdx.PythonectVisioParser().parse(open(TEST_DIR + os.sep + 'vdx07_examples' + os.sep + 'program_expr_list.vdx').read()).nodes()) == len(g.nodes()), True)

########NEW FILE########
__FILENAME__ = test_vdx10
# Copyright (c) 2012-2013, Itzik Kotler
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#
#     * Neither the name of the author nor the names of its contributors may
#       be used to endorse or promote products derived from this software without
#       specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import unittest
import networkx
import os


# Local imports

import pythonect.internal.parsers.vdx


# Consts

BASE_DIR = os.path.join(os.path.dirname(__file__), os.pardir)
TEST_DIR = os.path.dirname(os.path.abspath(__file__))


class TestPythonectVisioParser(unittest.TestCase):

    def test_program_empty(self):

        g = networkx.DiGraph()

        self.assertEqual(len(pythonect.internal.parsers.vdx.PythonectVisioParser().parse(open(TEST_DIR + os.sep + 'vdx10_examples' + os.sep + 'program_empty.vdx').read()).nodes()) == len(g.nodes()), True)

    def test_expr_atom(self):

        g = networkx.DiGraph()

        g.add_node('1')

        self.assertEqual(len(pythonect.internal.parsers.vdx.PythonectVisioParser().parse(open(TEST_DIR + os.sep + 'vdx10_examples' + os.sep + 'expr_atom.vdx').read()).nodes()) == len(g.nodes()), True)

    def test_even_expr_atom_op_expr(self):

        g = networkx.DiGraph()

        g.add_node('1')

        g.add_node('2')

        g.add_edge('1', '2')

        self.assertEqual(len(pythonect.internal.parsers.vdx.PythonectVisioParser().parse(open(TEST_DIR + os.sep + 'vdx10_examples' + os.sep + 'even_expr_atom_op_expr.vdx').read()).edges()) == len(g.edges()), True)

    def test_odd_expr_atom_op_expr(self):

        g = networkx.DiGraph()

        g.add_node('1')

        g.add_node('2')

        g.add_node('3')

        g.add_edge('1', '2')

        g.add_edge('2', '3')

        self.assertEqual(len(pythonect.internal.parsers.vdx.PythonectVisioParser().parse(open(TEST_DIR + os.sep + 'vdx10_examples' + os.sep + 'odd_expr_atom_op_expr.vdx').read()).edges()) == len(g.edges()), True)

    def test_program_expr_list(self):

        g = networkx.DiGraph()

        g.add_node('1')

        g.add_node('2')

        self.assertEqual(len(pythonect.internal.parsers.vdx.PythonectVisioParser().parse(open(TEST_DIR + os.sep + 'vdx10_examples' + os.sep + 'program_expr_list.vdx').read()).nodes()) == len(g.nodes()), True)

########NEW FILE########
__FILENAME__ = vdx
# Copyright (c) 2012-2013, Itzik Kotler
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#
#     * Neither the name of the author nor the names of its contributors may
#       be used to endorse or promote products derived from this software without
#       specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import networkx
import xml.sax


# Local imports

import pythonect.internal.parsers


# Tested on dia-bin 0.97.2

class _VisioParser(xml.sax.handler.ContentHandler):

    def __init__(self):

        xml.sax.handler.ContentHandler.__init__(self)

        self._in_shape_object = False

        self._in_text = False

        self.node_name = None

        self.edge = []

        self.node_value = {'OPERATOR': '->'}

    def startElement(self, name, attrs):

        if self._in_shape_object:

            if name == 'Text':

                self._in_text = True

        else:

            if name == 'Connect':

                self.edge.append(attrs['ToSheet'])

                if len(self.edge) == 2:

                    self._graph.add_edge(self.edge[0], self.edge[1])

                    self.edge = []

            if name == 'Shape':

                if self._graph is None:

                    self._graph = networkx.DiGraph()

                self._in_shape_object = True

                self.node_name = attrs['ID']

                self._graph.add_node(self.node_name)

    def endElement(self, name):

        if name == 'Shape':

            self._graph.node[self.node_name].update(self.node_value)

            if self._graph.node[self.node_name].get('CONTENT', None) is None:

                self._graph.remove_node(self.node_name)

            self.node_name = None

            self.node_value = {'OPERATOR': '->'}

            self._in_shape_object = False

        if name == 'Text':

            self._in_text = False

    def characters(self, content):

        if self._in_text:

            if self.node_value.get('CONTENT', None) is None:

                if isinstance(content, unicode):

                    # TODO: This is a hack to replace u'\u201cHello, world\u201d to "Hello, world"

                    content = content.encode('ascii', 'replace').replace('?', '"')

                self.node_value.update({'CONTENT': content})

    def endDocument(self):

        if self._graph is None:

            self._graph = networkx.DiGraph()

    def parse(self, source):

        self._graph = None

        try:

            xml.sax.parseString(source, self)

            # Delete 'OPERATOR' from tail nodes

            tail_nodes = [node for node, degree in self._graph.out_degree().items() if degree == 0]

            for node in tail_nodes:

                del self._graph.node[node]['OPERATOR']

        except xml.sax._exceptions.SAXParseException:

            pass

        return self._graph


class PythonectVisioParser(pythonect.internal.parsers.PythonectInputFileFormatParser):

    def parse(self, source):

        graph = _VisioParser().parse(source)

        return graph

    FILE_EXTS = ['vdx']

########NEW FILE########
__FILENAME__ = _graph
# Copyright (c) 2012-2013, Itzik Kotler
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#
#     * Neither the name of the author nor the names of its contributors may
#       be used to endorse or promote products derived from this software without
#       specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import networkx
import networkx.convert


# Local imports

import _ordereddict


class Graph(networkx.DiGraph):

    def __init__(self, data=None, **attr):

        networkx.DiGraph.__init__(self, data, **attr)

        # Line #202 - 216 ; networkx/classes/digraph.py

        self.graph = _ordereddict.OrderedDict()  # dictionary for graph attributes
        self.node = _ordereddict.OrderedDict()  # dictionary for node attributes
        # We store two adjacency lists:
        # the  predecessors of node n are stored in the dict self.pred
        # the successors of node n are stored in the dict self.succ=self.adj
        self.adj = _ordereddict.OrderedDict()   # empty adjacency dictionary
        self.pred = _ordereddict.OrderedDict()   # predecessor
        self.succ = self.adj  # successor

        # attempt to load graph with data
        if data is not None:
            networkx.convert.to_networkx_graph(data, create_using=self)
        # load graph attributes (must be after convert)
        self.graph.update(attr)
        self.edge = self.adj

########NEW FILE########
__FILENAME__ = _ordereddict
# Copyright (c) 2012-2013, Itzik Kotler
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#
#     * Neither the name of the author nor the names of its contributors may
#       be used to endorse or promote products derived from this software without
#       specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

try:

    # Python 2.7+

    from collections import OrderedDict

except Exception as e:

    # Python2.6

    from ordereddict import OrderedDict

########NEW FILE########
__FILENAME__ = eval_tst_gen
#!/usr/bin/env python
# Copyright (c) 2012-2013, Itzik Kotler
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#
#     * Neither the name of the author nor the names of its contributors may
#       be used to endorse or promote products derived from this software without
#       specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import sys
import os


# Add `internal` directory (i.e. ../) to sys.path

sys.path.append(os.path.abspath('../'))


# Local imports

import internal.eval


ATOM = [
    ('literal_underscore', '_'),
    ('literal_true_expr', '1 == 1'),
    ('literal_false_expr', '1 != 1'),
    ('literal_int', '1'),
    ('literal_float', '0.5'),
    ('literal_string', '\"foobar\"'),
    ('literal_true', 'True'),
    ('literal_false', 'False'),
    ('literal_none', 'None'),
    ('import_stmt', 'import math'),
    ('assignment_stmt', 'x = 0'),
    ('python_expr', '1+1'),
    ('pythonect_expr', '$[1->1]')
]


OPERATOR = [
    (None, None),
    ('comma', ','),
    ('async', '->'),
    ('sync', '|')
]


# ATOM OPERATOR ATOM OPERATOR ATOM

MAX_DEPTH = 5


def __type_wrapper(data):

    if isinstance(data, str):

        return '\'%s\'' % (data)

    return data


def pythonect_expr_generator(name=[], expr=[], depth=0):

    for (type, value) in ATOM:

        name.append(type)

        expr.append(value)

        # ATOM AND OPERATOR

        if (depth + 2 < MAX_DEPTH):

            for (type, value) in OPERATOR:

                if type is None:

                    yield (name, expr)

                    continue

                name.append(type)

                expr.append(value)

                for (return_type, return_value) in pythonect_expr_generator([], [], depth + 2):

                    yield(name + return_type, expr + return_value)

                name.pop()

                expr.pop()

        # ATOM

        else:

            yield (name, expr)

        name.pop()

        expr.pop()


def main():

    for (name, expr) in pythonect_expr_generator():

        try:

            print '\tdef test_%s(self):\n\n\t\tself.assertEqual( internal.eval.eval(\'%s\', {}, {}) , %s )\n' % \
                ('_'.join(name), ' '.join(expr), __type_wrapper(internal.eval.eval(' '.join(expr), {}, {})))

        except Exception as e:

            print "%s raises Exception %s" % (' '.join(expr), str(e))

if __name__ == "__main__":

    sys.exit(main())

########NEW FILE########
__FILENAME__ = test_eval
# Copyright (c) 2012-2013, Itzik Kotler
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#
#     * Neither the name of the author nor the names of its contributors may
#       be used to endorse or promote products derived from this software without
#       specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

try:

    # If < Python 2.7, use the backported unittest2 package

    import unittest2 as unittest

except ImportError:

    # Probably > Python 2.7, use unittest

    import unittest


import os
import sys
import copy


# Local imports

import pythonect


def _not_python27():

    major, minor = sys.version_info[:2]

    return not (major > 2 or (major == 2 and minor >= 7))


def _installed_module(name):

    try:

        __import__(name)

        return True

    except ImportError:

        return False


class TestPythonect(unittest.TestCase):

    def setUp(self):

        self.input = None

        self.locals_ = {'__MAX_THREADS_PER_FLOW__': 2}

        self.globals_ = {'__MAX_THREADS_PER_FLOW__': 2}

    def test_literal_hex(self):

        self.assertEqual(pythonect.eval('0x01', copy.copy(self.globals_), copy.copy(self.locals_)), 1)

    def test_sub_expr_literal_hex(self):

        self.assertEqual(pythonect.eval('`0x01`', copy.copy(self.globals_), copy.copy(self.locals_)), 1)

    def test_literal_bin(self):

        self.assertEqual(pythonect.eval('0b1', copy.copy(self.globals_), copy.copy(self.locals_)), 1)

    def test_literal_float(self):

        self.assertEqual(pythonect.eval('1.0', copy.copy(self.globals_), copy.copy(self.locals_)), 1)

    def test_literal_int(self):

        self.assertEqual(pythonect.eval('1', copy.copy(self.globals_), copy.copy(self.locals_)), 1)

    def test_python_stmt_import(self):

        self.assertEqual(pythonect.eval('import math', copy.copy(self.globals_), copy.copy(self.locals_)), self.input)

    def test_sub_expr_python_stmt_import(self):

        self.assertEqual(pythonect.eval('`import math`', copy.copy(self.globals_), copy.copy(self.locals_)), self.input)

    def test_python_stmt_assignment(self):

        self.assertEqual(pythonect.eval('x = 1', copy.copy(self.globals_), copy.copy(self.locals_)), self.input)

    def test_sub_expr_python_stmt_assignment(self):

        self.assertEqual(pythonect.eval('`x = 1`', copy.copy(self.globals_), copy.copy(self.locals_)), self.input)

    def test_python_expr_int(self):

        self.assertEqual(pythonect.eval('1 + 1', copy.copy(self.globals_), copy.copy(self.locals_)), 2)

    def test_sub_expr_python_expr_int(self):

        self.assertEqual(pythonect.eval('`1 + 1`', copy.copy(self.globals_), copy.copy(self.locals_)), 2)

    def test_python_expr_str_1(self):

        self.assertEqual(pythonect.eval('"Hello World"', copy.copy(self.globals_), copy.copy(self.locals_)), "Hello World")

    def test_sub_expr_python_expr_str_1(self):

        self.assertEqual(pythonect.eval('`"Hello World"`', copy.copy(self.globals_), copy.copy(self.locals_)), "Hello World")

    def test_python_expr_str_2(self):

        self.assertEqual(pythonect.eval("'Hello World'", copy.copy(self.globals_), copy.copy(self.locals_)), "Hello World")

    def test_python_expr_str_3(self):

        self.assertEqual(pythonect.eval('"Hello \'W\'orld"', copy.copy(self.globals_), copy.copy(self.locals_)), "Hello 'W'orld")

    def test_python_expr_str_4(self):

        self.assertEqual(pythonect.eval("'Hello \"W\"orld'", copy.copy(self.globals_), copy.copy(self.locals_)), 'Hello "W"orld')

    def test_python_expr_list(self):

        self.assertEqual(pythonect.eval('[[1, 2, 3]]', copy.copy(self.globals_), copy.copy(self.locals_)), [1, 2, 3])

#   TODO: Supported in Pythonect < 0.6 ; is worth maintaining in Pythonect 0.6+?
#
#    def test_sub_expr_python_expr_list(self):
#
#       self.assertEqual(pythonect.eval('`[[1, 2, 3]]`', copy.copy(self.globals_), copy.copy(self.locals_)), [1, 2, 3])

    def test_python_true_expr_literal_eq_literal(self):

        self.assertEqual(pythonect.eval('1 == 1', copy.copy(self.globals_), copy.copy(self.locals_)), self.input)

    def test_sub_expr_python_true_expr_literal_eq_literal(self):

        self.assertEqual(pythonect.eval('`1 == 1`', copy.copy(self.globals_), copy.copy(self.locals_)), self.input)

    def test_python_false_expr_literal_neq_literal(self):

        self.assertEqual(pythonect.eval('1 == 0', copy.copy(self.globals_), copy.copy(self.locals_)), False)

    def test_python_true_expr_underscore_eq_underscore(self):

        self.assertEqual(pythonect.eval('_ == _', copy.copy(self.globals_), copy.copy(self.locals_)), self.input)

    def test_python_false_expr_underscore_neq_repr_underscore(self):

        self.assertEqual(pythonect.eval('_ == repr(_)', copy.copy(self.globals_), copy.copy(self.locals_)), False)

    def test_literal_int_async_none(self):

        self.assertEqual(pythonect.eval('1 -> None', copy.copy(self.globals_), copy.copy(self.locals_)), 1)

    def test_literal_int_sync_none(self):

        self.assertEqual(pythonect.eval('1 | None', copy.copy(self.globals_), copy.copy(self.locals_)), 1)

    def test_literal_int_async_dict(self):

        self.assertEqual(pythonect.eval('1 -> {1: "One", 2: "Two"}', copy.copy(self.globals_), copy.copy(self.locals_)), "One")

    def test_literal_int_sync_dict(self):

        self.assertEqual(pythonect.eval('1 | {1: "One", 2: "Two"}', copy.copy(self.globals_), copy.copy(self.locals_)), "One")

    def test_literal_str_async_autoload(self):

        self.assertEqual(pythonect.eval('"Hello world" -> string.split', copy.copy(self.globals_), copy.copy(self.locals_)), ["Hello", "world"])

    def test_literal_str_sync_autoload(self):

        self.assertItemsEqual(pythonect.eval('"Hello world" | string.split', copy.copy(self.globals_), copy.copy(self.locals_)), ["Hello", "world"])

    def test_literal_int_async_literal_int(self):

        self.assertEqual(pythonect.eval('1 -> 1', copy.copy(self.globals_), copy.copy(self.locals_)), 1)

    def test_literal_int_sync_literal_int(self):

        self.assertEqual(pythonect.eval('1 | 1', copy.copy(self.globals_), copy.copy(self.locals_)), 1)

    def test_literal_int_async_literal_array_int_float(self):

        self.assertItemsEqual(pythonect.eval('1 -> [int,float]', copy.copy(self.globals_), copy.copy(self.locals_)), [1, 1.0])

    def test_literal_int_sync_literal_array_int_float(self):

        self.assertEqual(pythonect.eval('1 | [int,float]', copy.copy(self.globals_), copy.copy(self.locals_)), [1, 1.0])

    def test_python_stmt_assignment_async_literal_int(self):

        self.assertEqual(pythonect.eval('[x = 0] -> 1', copy.copy(self.globals_), copy.copy(self.locals_)), 1)

    def test_python_stmt_assignment_sync_literal_int(self):

        self.assertEqual(pythonect.eval('[x = 0] | 1', copy.copy(self.globals_), copy.copy(self.locals_)), 1)

    def test_python_stmt_assignment_sync_variable(self):

        self.assertEqual(pythonect.eval('[x = 0] | x', copy.copy(self.globals_), copy.copy(self.locals_)), 0)

    def test_python_stmt_assignment_async_variable(self):

        self.assertEqual(pythonect.eval('[x = 0] -> x', copy.copy(self.globals_), copy.copy(self.locals_)), 0)

    def test_literal_array_int_int_sync_none(self):

        self.assertEqual(pythonect.eval('[1, 2] | None', copy.copy(self.globals_), copy.copy(self.locals_)), [1, 2])

    def test_literal_array_int_int_async_none(self):

        self.assertItemsEqual(pythonect.eval('[1, 2] -> None', copy.copy(self.globals_), copy.copy(self.locals_)), [1, 2])

    def test_literal_array_int_int_sync_dict(self):

        self.assertEqual(pythonect.eval('[1, 2] | {1: "One", 2: "Two"}', copy.copy(self.globals_), copy.copy(self.locals_)), ["One", "Two"])

    def test_literal_array_int_int_async_dict(self):

        self.assertItemsEqual(pythonect.eval('[1, 2] -> {1: "One", 2: "Two"}', copy.copy(self.globals_), copy.copy(self.locals_)), ["One", "Two"])

    def test_literal_array_int_str_async_none(self):

        self.assertItemsEqual(pythonect.eval('[1, "Hello"] -> None', copy.copy(self.globals_), copy.copy(self.locals_)), [1, "Hello"])

    def test_literal_array_int_str_sync_none(self):

        self.assertEqual(pythonect.eval('[1, "Hello"] | None', copy.copy(self.globals_), copy.copy(self.locals_)), [1, "Hello"])

    def test_literal_array_int_str_async_int(self):

        self.assertItemsEqual(pythonect.eval('[1, "Hello"] -> 1', copy.copy(self.globals_), copy.copy(self.locals_)), [1, 1])

    def test_literal_array_int_str_sync_int(self):

        self.assertEqual(pythonect.eval('[1, "Hello"] | 1', copy.copy(self.globals_), copy.copy(self.locals_)), [1, 1])

    def test_literal_array_int_int_sync_literal_int(self):

        self.assertEqual(pythonect.eval('[1, 2] | 1', copy.copy(self.globals_), copy.copy(self.locals_)), [1, 1])

    def test_literal_array_int_int_async_literal_int(self):

        self.assertEqual(pythonect.eval('[1, 2] -> 1', copy.copy(self.globals_), copy.copy(self.locals_)), [1, 1])

    def test_literal_array_int_int_sync_literal_array_int_int(self):

        self.assertEqual(pythonect.eval('[1, 2] | [3, 4]', copy.copy(self.globals_), copy.copy(self.locals_)), [3, 4, 3, 4])

    def test_literal_array_int_int_async_literal_array_int_int(self):

        self.assertItemsEqual(pythonect.eval('[1, 2] -> [3, 4]', copy.copy(self.globals_), copy.copy(self.locals_)), [3, 3, 4, 4])

    def test_literal_int_async_stmt_single_return_value_function_async_single_return_value_function(self):

        self.assertEqual(pythonect.eval('1 -> def foobar(x): return x+1 -> foobar', copy.copy(self.globals_), copy.copy(self.locals_)), 2)

    def test_literal_int_async_stmt_single_return_value_function_sync_single_return_value_function(self):

        self.assertEqual(pythonect.eval('1 -> def foobar(x): return x+1 | foobar', copy.copy(self.globals_), copy.copy(self.locals_)), 2)

    def test_literal_int_sync_stmt_single_return_value_function_async_single_return_value_function(self):

        self.assertEqual(pythonect.eval('1 | def foobar(x): return x+1 -> foobar', copy.copy(self.globals_), copy.copy(self.locals_)), 2)

    def test_literal_int_sync_stmt_single_return_value_function_sync_single_return_value_function(self):

        self.assertEqual(pythonect.eval('1 | def foobar(x): return x+1 | foobar', copy.copy(self.globals_), copy.copy(self.locals_)), 2)

    def test_literal_int_async_stmt_multiple_return_value_function_async_multiple_return_value_function(self):

        self.assertItemsEqual(pythonect.eval('1 -> def foobar(x): return [x,x+1] -> foobar', copy.copy(self.globals_), copy.copy(self.locals_)), [1, 2])

    def test_literal_int_async_stmt_multiple_return_value_function_sync_multiple_return_value_function(self):

        self.assertEqual(pythonect.eval('1 -> def foobar(x): return [x,x+1] | foobar', copy.copy(self.globals_), copy.copy(self.locals_)), [1, 2])

    def test_literal_int_sync_stmt_multiple_return_value_function_async_multiple_return_value_function(self):

        self.assertEqual(pythonect.eval('1 | def foobar(x): return [x,x+1] -> foobar', copy.copy(self.globals_), copy.copy(self.locals_)), [1, 2])

    def test_literal_int_sync_stmt_multiple_return_value_function_sync_multiple_return_value_function(self):

        self.assertEqual(pythonect.eval('1 | def foobar(x): return [x,x+1] | foobar', copy.copy(self.globals_), copy.copy(self.locals_)), [1, 2])

    def test_literal_int_async_stmt_generator_return_value_function_async_generator_return_value_function(self):

        self.assertItemsEqual(pythonect.eval('1 -> def foobar(x): yield x; yield x+1 -> foobar', copy.copy(self.globals_), copy.copy(self.locals_)), [1, 2])

    def test_literal_int_async_stmt_generator_return_value_function_sync_generator_return_value_function(self):

        self.assertEqual(pythonect.eval('1 -> def foobar(x): yield x; yield x+1 | foobar', copy.copy(self.globals_), copy.copy(self.locals_)), [1, 2])

    def test_literal_int_sync_stmt_generator_return_value_function_async_generator_return_value_function(self):

        self.assertEqual(pythonect.eval('1 | def foobar(x): yield x; yield x+1 -> foobar', copy.copy(self.globals_), copy.copy(self.locals_)), [1, 2])

    def test_literal_int_sync_stmt_generator_return_value_function_sync_generator_return_value_function(self):

        self.assertEqual(pythonect.eval('1 | def foobar(x): yield x; yield x+1 | foobar', copy.copy(self.globals_), copy.copy(self.locals_)), [1, 2])

    def test_singlethread_program_async(self):

        self.assertEqual(pythonect.eval('import threading -> x = threading.current_thread().name -> y = threading.current_thread().name -> x == y', copy.copy(self.globals_), copy.copy(self.locals_)), None)

    def test_singlethread_program_sync(self):

        self.assertEqual(pythonect.eval('import threading | x = threading.current_thread().name | y = threading.current_thread().name | x == y', copy.copy(self.globals_), copy.copy(self.locals_)), None)

    def test_multithread_program_async(self):

        r_array = pythonect.eval('import threading -> [threading.current_thread().name, threading.current_thread().name]', copy.copy(self.globals_), copy.copy(self.locals_))

        self.assertEqual(r_array[0] != r_array[1], True)

    def test_multithread_program_sync(self):

        r_array = pythonect.eval('import threading | [threading.current_thread().name, threading.current_thread().name]', copy.copy(self.globals_), copy.copy(self.locals_))

        self.assertEqual(r_array[0] != r_array[1], True)

    @unittest.skipIf(_not_python27(), 'Current Python implementation does not support multiprocessing (buggy)')
    def test_multiprocess_program_async(self):

        r_array = pythonect.eval('import threading -> [multiprocessing.current_process().pid &, multiprocessing.current_process().pid &]', copy.copy(self.globals_), copy.copy(self.locals_))

        self.assertEqual(r_array[0] != r_array[1], True)

#        self.assertEqual(pythonect.eval('import multiprocessing -> start_pid = multiprocessing.current_process().pid -> start_pid -> str & -> current_pid = multiprocessing.current_process().pid -> 1 -> current_pid != start_pid', copy.copy(self.globals_), copy.copy(self.locals_)), 1)

    @unittest.skipIf(_not_python27(), 'Current Python implementation does not support multiprocessing (buggy)')
    def test_multiprocess_program_sync(self):

        r_array = pythonect.eval('import multiprocessing | [multiprocessing.current_process().pid &, multiprocessing.current_process().pid &]', copy.copy(self.globals_), copy.copy(self.locals_))

        self.assertEqual(r_array[0] != r_array[1], True)

#        self.assertEqual(pythonect.eval('import multiprocessing | start_pid = multiprocessing.current_process().pid | start_pid | str & | current_pid = multiprocessing.current_process().pid | 1 | current_pid != start_pid', copy.copy(self.globals_), copy.copy(self.locals_)), 1)

    def test_pseudo_none_const_as_url(self):

        self.assertEqual(pythonect.eval('def foobar(x): return x+1 -> 1 -> foobar@None', copy.copy(self.globals_), copy.copy(self.locals_)), 2)

    def test_pseudo_none_str_as_url(self):

        self.assertEqual(pythonect.eval('def foobar(x): return x+1 -> 1 -> foobar@"None"', copy.copy(self.globals_), copy.copy(self.locals_)), 2)

    def test_pseudo_none_value_fcn_return_value_as_url(self):

        self.assertEqual(pythonect.eval('def ret_none(): return None -> def foobar(x): return x+1 -> 1 -> foobar@ret_none()', copy.copy(self.globals_), copy.copy(self.locals_)), 2)

    def test_pseudo_none_str_fcn_return_value_as_url(self):

        self.assertEqual(pythonect.eval('def ret_none(): return "None" -> def foobar(x): return x+1 -> 1 -> foobar@ret_none()', copy.copy(self.globals_), copy.copy(self.locals_)), 2)

    def test_pythonect_eval_fcn(self):

        self.assertEqual(pythonect.eval("eval('1->1', {'__MAX_THREADS_PER_FLOW__': 2}, {'__MAX_THREADS_PER_FLOW__': 2})", copy.copy(self.globals_), copy.copy(self.locals_)), 1)

    def test_python_eval_within_pythonect_program(self):

        self.assertEqual(pythonect.eval("__eval__('1')", copy.copy(self.globals_), copy.copy(self.locals_)), 1)

    def test_void_function(self):

        self.assertEqual(pythonect.eval("def void_foobar(): return 2 -> 1 -> void_foobar", copy.copy(self.globals_), copy.copy(self.locals_)), 2)

    ############################################################
    # Ticket numbers in this file can be looked up by visiting #
    # http://github.com/ikotler/pythonect/issues/<number>      #
    ############################################################

    # Bug #11

    def test_autloader_within_array(self):

        self.assertItemsEqual(pythonect.eval('"Hello world" | [string.split]', copy.copy(self.globals_), copy.copy(self.locals_)), ["Hello", "world"])

    # Bug #14

    def test_print_like_statement(self):

        self.assertItemsEqual(pythonect.eval('range(1,10) -> print("Thread A")', copy.copy(self.globals_), copy.copy(self.locals_)), [1, 2, 3, 4, 5, 6, 7, 8, 9])

    def test_multiple_stateful_x_eq_5_statement(self):

        locals_ = copy.copy(self.locals_)

        globals_ = copy.copy(self.globals_)

        pythonect.eval('xrange(1, 10) -> x = _', globals_, locals_)

        self.assertEqual('x' not in locals_ and 'x' not in globals_, True)

        # i.e.

        # >>> xrange(x, 10) -> x = _
        # >>> x
        # NameError: name 'x' is not defined

    def test_stateful_x_eq_5_statement(self):

        locals_ = copy.copy(self.locals_)

        globals_ = copy.copy(self.globals_)

        pythonect.eval('x = 5', globals_, locals_)

        self.assertEqual(pythonect.eval('1 -> [x == 5]', globals_, locals_), 1)

        # i.e.

        # >>> x = 5
        # >>> 1 -> [x == 5]
        # 1

    # Bug #16

    def test_typeerror_exception_not_due_to_eval(self):

        with self.assertRaisesRegexp(TypeError, 'takes exactly'):

            pythonect.eval('1 -> socket.socket(socket.AF_INET, socket.SOCK_STREAM) -> _.connect("A","B")', copy.copy(self.globals_), copy.copy(self.locals_))

    # Bug #21

    def test_list_with_str_with_comma(self):

        self.assertEqual(pythonect.eval('["Hello, world"]', copy.copy(self.globals_), copy.copy(self.locals_)), 'Hello, world')

    # Bug #27

#    @unittest.skipIf(not _installed_module('multiprocessing'), 'Current Python implementation does not support multiprocessing')
#    def test_multi_processing_and_multi_threading(self):
#
#        try:
#
#            self.assertEqual(pythonect.eval('"Hello, world" -> [print, print &]', copy.copy(self.globals_), copy.copy(self.locals_)), ['Hello, world', 'Hello, world'])
#
#        except OSError as e:
#
#            # i.e. OSError: [Errno 13] Permission denied
#
#            return 1

    # Bug #30

    def test_non_string_literals_in_list(self):

        self.assertEqual(pythonect.eval('[1,2,3] -> _ + 1', copy.copy(self.globals_), copy.copy(self.locals_)), [2, 3, 4])

    # Feature #35

    def test_eval_with_expressions_list_as_input(self):

        expressions = pythonect.parse('"Hello, world" -> 1 | 2')

        self.assertEqual(pythonect.eval(expressions, copy.copy(self.globals_), copy.copy(self.locals_)), 2)

    # Enhancement #45

    def test_literal_dict_as_input(self):

        self.assertEqual(pythonect.eval('{"foobar": "foobar"}', copy.copy(self.globals_), copy.copy(self.locals_)), {"foobar": "foobar"})

    def test_dict_as_return_value_as_input(self):

        self.assertEqual(pythonect.eval("def foobar(): return {'foobar': 'foobar'} -> foobar() -> print", copy.copy(self.globals_), copy.copy(self.locals_)), {"foobar": "foobar"})

    # Bug #48

    def test_print_B_in_ABC(self):

        self.assertEqual(pythonect.eval('1 -> print "B" in "ABC"', copy.copy(self.globals_), copy.copy(self.locals_)), 1)

    def test_print_2_is_2(self):

        self.assertEqual(pythonect.eval('1 -> print 2 is 2', copy.copy(self.globals_), copy.copy(self.locals_)), 1)

    # Bug #69

    def test_alt_print__fcn(self):

        self.assertEqual(pythonect.eval('1 -> print', copy.copy(self.globals_), {'print_': lambda x: 123}), 123)

    # Feature 70 (Freeze on Python 2.6 and Mac OS X Python 2.7.2)
    #
    #def test_max_threads_eq_0(self):
    #
    #    with self.assertRaisesRegexp(ValueError, 'Number of processes must be at least'):
    #
    #        pythonect.eval('range(1, 3) -> _+1', copy.copy(self.globals_), {'__MAX_THREADS_PER_FLOW__': 0})

########NEW FILE########
__FILENAME__ = test_xmlrpc_app
# Copyright (c) 2012-2013, Itzik Kotler
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#
#     * Neither the name of the author nor the names of its contributors may
#       be used to endorse or promote products derived from this software without
#       specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from SimpleXMLRPCServer import SimpleXMLRPCServer
from SimpleXMLRPCServer import SimpleXMLRPCRequestHandler

from select import select
import unittest
import socket
import threading
import os
import sys


# Local imports

import pythonect


## {{{ http://code.activestate.com/recipes/520583/ (r1)
class XMLRPCServer(SimpleXMLRPCServer):
    """
    A variant of SimpleXMLRPCServer that can be stopped.
    """
    def __init__(self, *args, **kwargs):
        SimpleXMLRPCServer.__init__(self, *args, **kwargs)
        self.logRequests = 0
        self.closed = False

    def serve_until_stopped(self):
        self.socket.setblocking(0)
        while not self.closed:
            self.handle_request()

    def stop_serving(self):
        self.closed = True

    def get_request(self):
        inputObjects = []
        while not inputObjects and not self.closed:
            inputObjects, outputObjects, errorObjects = \
                select([self.socket], [], [], 0.2)
            try:
                return self.socket.accept()
            except socket.error:
                raise
## end of http://code.activestate.com/recipes/520583/ }}}


# Global Variables

thread = None
server = None


def setUpModule():

    global thread

    global server

    # Restrict to a particular path.

    class RequestHandler(SimpleXMLRPCRequestHandler):
        rpc_paths = ('/RPC2',)

    # Create a stopable XMLRPC Server

    server = XMLRPCServer(("localhost", 8000), requestHandler=RequestHandler)

    server.register_introspection_functions()

    # Register a simple function
    def inc_function(x):
        return x + 1

    server.register_function(inc_function, 'inc')

    print "*** Starting XMLRPCServer on localhost:8000 with registered function \'inc\'"

    # Run the server's main loop (in a thread)

    thread = threading.Thread(target=server.serve_until_stopped)

    thread.start()

    server = server


def tearDownModule():

    print "*** Shutting down XMLRPCServer (localhost:8000)"

    server.stop_serving()

    thread.join(None)


class TestPythonectRemoting(unittest.TestCase):

    def test_int_async_remotefunction_const_host(self):

        self.assertEqual(pythonect.eval('1 -> inc@xmlrpc://localhost:8000', {}, {}), 2)

    def test_int_sync_remotefunction_const_host(self):

        self.assertEqual(pythonect.eval('1 | inc@xmlrpc://localhost:8000', {}, {}), 2)

    def test_int_async_remotefunction_with_args_const_host(self):

        self.assertEqual(pythonect.eval('1 -> inc(1)@xmlrpc://localhost:8000', {}, {}), 2)

    def test_int_sync_remotefunction_with_args_const_host(self):

        self.assertEqual(pythonect.eval('1 | inc(1)@xmlrpc://localhost:8000', {}, {}), 2)

    def test_int_async_remotefunction_literal_expr(self):

        self.assertEqual(pythonect.eval('1 -> inc@"xmlrpc://" + "localhost:8000"', {}, {}), 2)

    def test_int_sync_remotefunction_literal_expr(self):

        self.assertEqual(pythonect.eval('1 | inc@"xmlrpc://" + "localhost:8000"', {}, {}), 2)

    def test_int_async_remotefunction_with_args_literal_expr(self):

        self.assertEqual(pythonect.eval('1 -> inc(1)@"xmlrpc://" + "localhost:8000"', {}, {}), 2)

    def test_int_sync_remotefunction_with_args_literal_expr(self):

        self.assertEqual(pythonect.eval('1 | inc(1)@"xmlrpc://" + "localhost:8000"', {}, {}), 2)

    def test_int_async_remotefunction_expr(self):

        self.assertEqual(pythonect.eval('[host = "localhost"] -> 1 -> inc@"xmlrpc://" + host + ":8000"', {}, {}), 2)

    def test_int_sync_remotefunction_expr(self):

        self.assertEqual(pythonect.eval('[host = "localhost"] -> 1 | inc@"xmlrpc://" + host + ":8000"', {}, {}), 2)

    def test_int_async_remotefunction_with_args_expr(self):

        self.assertEqual(pythonect.eval('[host = "localhost"] -> 1 -> inc(1)@"xmlrpc://" + host + ":8000"', {}, {}), 2)

    def test_int_sync_remotefunction_with_args_expr(self):

        self.assertEqual(pythonect.eval('[host = "localhost"] -> 1 | inc(1)@"xmlrpc://" + host + ":8000"', {}, {}), 2)

# Standard XML-RPC does not support **kwargs

#       def test_int_async_remotefunction_with_kwargs(self):
#               self.assertEqual( pythonect.eval('1 -> inc(x=1)@xmlrpc://localhost:8000', {}, {}) , 2 )

#       def test_int_sync_remotefunction_with_kwargs(self):
#               self.assertEqual( pythonect.eval('1 | inc(x=1)@xmlrpc://localhost:8000', {}, {}) , 2 )

########NEW FILE########
__FILENAME__ = _version
__version__ = '0.6.0'

########NEW FILE########
