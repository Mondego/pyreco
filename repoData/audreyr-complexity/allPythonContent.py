__FILENAME__ = conf
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
complexity.conf
-------------------

Functions for reading a `complexity.yml` configuration file and doing various
configuration-related things.
"""

import logging
import os
import yaml


def read_conf(directory):
    """
    Reads and parses the `complexity.yml` configuration file from a
    directory, if one is present.
    :param directory: Directory to look for a `complexity.yml` file.
    :returns: A conf dict, or False if no `complexity.yml` is present.
    """

    logging.debug("About to look for a conf file in {0}".format(directory))
    conf_file = os.path.join(directory, 'complexity.yml')

    if os.path.isfile(conf_file):
        with open(conf_file) as f:
            conf_dict = yaml.safe_load(f.read())
            return conf_dict
    return False


def get_unexpanded_list(conf_dict):
    """
    Given a configuration dict, returns the list of templates that were
    specified as unexpanded.
    """
    
    return conf_dict.get('unexpanded_templates', ())

########NEW FILE########
__FILENAME__ = exceptions
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
complexity.exceptions
---------------------

All exceptions used in the Complexity code base are defined here.
"""


class ComplexityException(Exception):
    """
    Base exception class. All Complexity-specific exceptions subclass
    `ComplexityException`.
    """


class MissingTemplateDirException(ComplexityException):
    """
    Raised when a project is missing a `templates/` subdirectory.
    """


class NonHTMLFileException(ComplexityException):
    """
    Raised when a project's `templates/` directory contains a non-HTML file.
    """


class OutputDirExistsException(ComplexityException):
    """
    Raised when a project's output_dir exists and no_input=True.
    """

########NEW FILE########
__FILENAME__ = generate
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
complexity.generate
-------------------

Functions for static site generation.
"""

import json
import logging
import os
import shutil

from binaryornot.check import is_binary
from jinja2 import FileSystemLoader
from jinja2.environment import Environment

from .exceptions import MissingTemplateDirException
from .utils import make_sure_path_exists, unicode_open


def get_output_filename(template_filepath, output_dir, force_unexpanded):
    """
    Given an input filename, return the corresponding output filename.

    :param template_filepath: Name of template file relative to template dir,
                          e.g. art/index.html
    :param output_dir: The Complexity output directory, e.g. `www/`.
    :paramtype output_dir: directory
    """

    template_filepath = os.path.normpath(template_filepath)

    basename = os.path.basename(template_filepath)
    dirname = os.path.dirname(template_filepath)

    # Base files don't have output.
    if basename.startswith('base'):
        return False
    # Put index and unexpanded templates in the root.
    elif force_unexpanded or basename == 'index.html':
        output_filename = os.path.join(output_dir, template_filepath)
    # Put other pages in page/index.html, for better URL formatting.
    else:
        stem = basename.split('.')[0]
        output_filename = os.path.join(
            output_dir,
            dirname,
            '{0}/index.html'.format(stem)
        )
    return output_filename


def generate_html_file(template_filepath, output_dir, env, context, force_unexpanded=False):
    """
    Renders and writes a single HTML file to its corresponding output location.

    :param template_filepath: Name of template file to be rendered. Should be
                              relative to template dir, e.g. art/index.html
    :param output_dir: The Complexity output directory, e.g. `www/`.
    :paramtype output_dir: directory
    :param env: Jinja2 environment with a loader already set up.
    :param context: Jinja2 context that holds template variables. See
        http://jinja.pocoo.org/docs/api/#the-context
    """

    # Ignore templates starting with "base". They're treated as special cases.
    if template_filepath.startswith('base'):
        return False

    tmpl = env.get_template(template_filepath)
    rendered_html = tmpl.render(**context)

    output_filename = get_output_filename(template_filepath, output_dir, force_unexpanded)
    if output_filename:
        make_sure_path_exists(os.path.dirname(output_filename))

        # Write the generated file
        with unicode_open(output_filename, 'w') as fh:
            fh.write(rendered_html)
            return True


def generate_html(templates_dir, output_dir, context=None, unexpanded_templates=()):
    """
    Renders the HTML templates from `templates_dir`, and writes them to
    `output_dir`.

    :param templates_dir: The Complexity templates directory,
        e.g. `project/templates/`.
    :paramtype templates_dir: directory
    :param output_dir: The Complexity output directory, e.g. `www/`.
    :paramtype output_dir: directory
    :param context: Jinja2 context that holds template variables. See
        http://jinja.pocoo.org/docs/api/#the-context
    """

    logging.debug('Templates dir is {0}'.format(templates_dir))
    if not os.path.exists(templates_dir):
        raise MissingTemplateDirException(
            'Your project is missing a templates/ directory containing your \
            HTML templates.'
        )

    context = context or {}
    env = Environment()
    # os.chdir(templates_dir)
    env.loader = FileSystemLoader(templates_dir)

    # Create the output dir if it doesn't already exist
    make_sure_path_exists(output_dir)

    for root, dirs, files in os.walk(templates_dir):
        for f in files:
            # print(f)
            template_filepath = os.path.relpath(
                os.path.join(root, f),
                templates_dir
            )

            force_unexpanded = template_filepath in unexpanded_templates
            logging.debug('Is {0} in {1}? {2}'.format(
                template_filepath,
                unexpanded_templates,
                force_unexpanded
            ))

            if is_binary(os.path.join(templates_dir, template_filepath)):
                print('Non-text file found: {0}. Skipping.'.format(template_filepath))
            else:
                outfile = get_output_filename(template_filepath, output_dir, force_unexpanded)
                print('Copying {0} to {1}'.format(template_filepath, outfile))
                generate_html_file(template_filepath, output_dir, env, context, force_unexpanded)


def generate_context(context_dir):
    """
    Generates the context for all Complexity pages.

    :param context_dir: Directory containing `.json` file(s) to be turned into
                        context variables for Jinja2.

    Description:

        Iterates through the contents of `context_dir` and finds all JSON
        files. Loads the JSON file as a Python object with the key being the
        JSON file name.

    Example:

        Assume the following files exist::

            context/
            ├── names.json
            └── numbers.json

        Depending on their content, might generate a context as follows:

        .. code-block:: json

            context = {
                    "names": ['Audrey', 'Danny'],
                    "numbers": [1, 2, 3, 4]
                   }
    """
    context = {}

    json_files = os.listdir(context_dir)

    for file_name in json_files:

        if file_name.endswith('json'):

            # Open the JSON file and convert to Python object
            json_file = os.path.join(context_dir, file_name)
            with unicode_open(json_file) as f:
                obj = json.load(f)

            # Add the Python object to the context dictionary
            context[file_name[:-5]] = obj

    return context


def copy_assets(assets_dir, output_dir):
    """
    Copies static assets over from `assets_dir` to `output_dir`.

    :param assets_dir: The Complexity project assets directory,
        e.g. `project/assets/`.
    :paramtype assets_dir: directory
    :param output_dir: The Complexity output directory, e.g. `www/`.
    :paramtype output_dir: directory
    """

    assets = os.listdir(assets_dir)
    for item in assets:
        item_path = os.path.join(assets_dir, item)

        # Only copy allowed dirs
        if os.path.isdir(item_path) and item != 'scss' and item != 'less':
            new_dir = os.path.join(output_dir, item)
            print('Copying directory {0} to {1}'.format(item, new_dir))
            shutil.copytree(item_path, new_dir)

        # Copy over files in the root of assets_dir
        if os.path.isfile(item_path):
            new_file = os.path.join(output_dir, item)
            print('Copying file {0} to {1}'.format(item, new_file))
            shutil.copyfile(item_path, new_file)

########NEW FILE########
__FILENAME__ = main
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
complexity.main
---------------

Main entry point for the `complexity` command.

The code in this module is also a good example of how to use Complexity as a
library rather than a script.
"""

import argparse
import logging
import os
import sys

from .conf import read_conf, get_unexpanded_list
from .exceptions import OutputDirExistsException
from .generate import generate_context, copy_assets, generate_html
from .prep import prompt_and_delete_cruft
from .serve import serve_static_site


logger = logging.getLogger(__name__)

def complexity(project_dir, no_input=True):
    """
    API equivalent to using complexity at the command line.

    :param project_dir: The Complexity project directory, e.g. `project/`.
    :paramtype project_dir: directory

    :param no_input: If true, don't prompt about whether to delete
        pre-existing `www/` directory. Instead, throw exception if one is
        found.

    .. note:: You must delete `output_dir` before calling this. This also does
       not start the Complexity development server; you can do that from your
       code if desired.
    """

    # Get the configuration dictionary, if config exists
    defaults = {
        "templates_dir": "templates/",
        "assets_dir": "assets/",
        "context_dir": "context/",
        "output_dir": "../www/"
    }
    conf_dict = read_conf(project_dir) or defaults

    output_dir = os.path.normpath(
        os.path.join(project_dir, conf_dict['output_dir'])
    )

    # If output_dir exists, prompt before deleting.
    # Abort if it can't be deleted.
    if no_input:
        if os.path.exists(output_dir):
            raise OutputDirExistsException(
                'Please delete {0} manually and try again.'
            )
    else:
        if not prompt_and_delete_cruft(output_dir):
            sys.exit()

    # Generate the context data
    context = None
    if 'context_dir' in conf_dict:
        context_dir = os.path.join(project_dir, conf_dict['context_dir'])
        if os.path.exists(context_dir):
            context = generate_context(context_dir)

    # Generate and serve the HTML site
    unexpanded_templates = get_unexpanded_list(conf_dict)
    templates_dir = os.path.join(project_dir, conf_dict['templates_dir'])
    generate_html(templates_dir, output_dir, context, unexpanded_templates)

    if 'assets_dir' in conf_dict:
        assets_dir = os.path.join(project_dir, conf_dict['assets_dir'])
        copy_assets(assets_dir, output_dir)

    return output_dir


def get_complexity_args():
    """
    Get the command line input/output arguments passed in to Complexity.
    """

    parser = argparse.ArgumentParser(
        description='A refreshingly simple static site generator, for those'
        'who like to work in HTML.'
    )
    parser.add_argument(
        'project_dir',
        default='project/',
        help='Your project directory containing the files to be processed by'
        'Complexity.'
    )
    parser.add_argument(
        '--port',
        type=int,
        default=9090,
        help='Port number to serve files on.'
    )
    parser.add_argument(
        '--noserver',
        action='store_true',
        help='Don\'t run the server.'
    )
    args = parser.parse_args()
    return args


def main():
    """ Entry point for the package, as defined in `setup.py`. """

    args = get_complexity_args()

    output_dir = complexity(project_dir=args.project_dir, no_input=False)
    if not args.noserver:
        serve_static_site(output_dir=output_dir, port=args.port)


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = prep
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
complexity.prep
---------------

Functions for preparing a Complexity project for static site generation,
before it actually happens.
"""

import os
import shutil

from . import utils


def prompt_and_delete_cruft(output_dir):
    """
    Asks if it's okay to delete `output_dir/`.
    If so, go ahead and delete it.

    :param output_dir: The Complexity output directory, e.g. `www/`.
    :paramtype output_dir: directory
    """
    if not os.path.exists(output_dir):
        return True

    ok_to_delete = utils.query_yes_no(
        'Is it okay to delete {0}?'.format(output_dir)
    )
    if ok_to_delete:
        shutil.rmtree(output_dir)
        return True
    else:
        print(
            "Aborting. Please manually remove {0} and retry."
            .format(output_dir)
        )
        return False

########NEW FILE########
__FILENAME__ = serve
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
complexity.serve
-------------------

Functions for serving a static HTML website locally.
"""

import os
import sys


PY3 = sys.version > '3'
if PY3:
    import http.server as httpserver
    import socketserver
else:
    import SimpleHTTPServer as httpserver
    import SocketServer as socketserver


def serve_static_site(output_dir, port=9090):
    """
    Serve a directory containing static HTML files, on a specified port.

    :param output_dir: Output directory to be served.
    """
    os.chdir(output_dir)
    Handler = httpserver.SimpleHTTPRequestHandler

    # See http://stackoverflow.com/questions/16433522/socketserver-getting-rid-
    #      of-errno-98-address-already-in-use
    socketserver.TCPServer.allow_reuse_address = True

    httpd = socketserver.TCPServer(("", port), Handler)
    print("serving at port", port)

    try:
        httpd.serve_forever()
    except (KeyboardInterrupt, SystemExit):
        print("Shutting down...")
        httpd.socket.close()
        sys.exit()

########NEW FILE########
__FILENAME__ = utils
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
complexity.utils
----------------

Helper functions used throughout Complexity.
"""

import errno
import os
import sys

PY3 = sys.version > '3'
if PY3:
    pass
else:
    import codecs
    input = raw_input


def make_sure_path_exists(path):
    """
    Ensures that a directory exists.

    :param path: A directory path.
    """
    try:
        os.makedirs(path)
    except OSError as exception:
        if exception.errno != errno.EEXIST:
            return False
    return True


def unicode_open(filename, *args, **kwargs):
    """
    Opens a file as usual on Python 3, and with UTF-8 encoding on Python 2.

    :param filename: Name of file to open.
    """
    if PY3:
        return open(filename, *args, **kwargs)
    kwargs['encoding'] = "utf-8"
    return codecs.open(filename, *args, **kwargs)


def query_yes_no(question, default="yes"):
    """
    Ask a yes/no question via `raw_input()` and return their answer.

    :param question: A string that is presented to the user.
    :param default: The presumed answer if the user just hits <Enter>.
        It must be "yes" (the default), "no" or None (meaning
        an answer is required of the user).

    The "answer" return value is one of "yes" or "no".

    Adapted from
    http://stackoverflow.com/questions/3041986/python-command-line-yes-no-input
    http://code.activestate.com/recipes/577058/

    """
    valid = {"yes": True, "y": True, "ye": True, "no": False, "n": False}
    if default is None:
        prompt = " [y/n] "
    elif default == "yes":
        prompt = " [Y/n] "
    elif default == "no":
        prompt = " [y/N] "
    else:
        raise ValueError("invalid default answer: '%s'" % default)

    while True:
        sys.stdout.write(question + prompt)
        choice = input().lower()

        if default is not None and choice == '':
            return valid[default]
        elif choice in valid:
            return valid[choice]
        else:
            sys.stdout.write("Please respond with 'yes' or 'no' "
                             "(or 'y' or 'n').\n")

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# complexity documentation build configuration file, created by
# sphinx-quickstart on Tue Jul  9 22:26:36 2013.
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

# Append parent dir
cwd = os.getcwd()
parent = os.path.dirname(cwd)
sys.path.append(parent)

# Append docs/_themes/ dir
sys.path.append(os.path.abspath('_themes'))

import complexity

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
project = u'complexity'
copyright = u'2013, Audrey Roy'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = complexity.__version__
# The full version, including alpha/beta/rc tags.
release = complexity.__version__

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
html_theme = 'complexity'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
html_theme_path = ['_themes']

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
htmlhelp_basename = 'complexitydoc'


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
  ('index', 'complexity.tex', u'Complexity Documentation',
   u'Audrey Roy', 'manual'),
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
    ('index', 'complexity', u'Complexity Documentation',
     [u'Audrey Roy'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'complexity', u'Complexity Documentation',
   u'Audrey Roy', 'complexity', 'One line description of project.',
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
__FILENAME__ = complexity_theme_support
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Complexity Pygments styles. 
Heavily customized for Complexity.
Based on Armin Ronacher's flasky extensions. flasky pygments style based on tango style.
"""
from pygments.style import Style
from pygments.token import Keyword, Name, Comment, String, Error, \
     Number, Operator, Generic, Whitespace, Punctuation, Other, Literal


class ComplexityStyle(Style):
    # background_color = "#D6FBFF" Actually defined in complexity.css_t
    default_style = ""

    styles = {
        # No corresponding class for the following:
        #Text:                     "", # class:  ''
        Whitespace:                "underline #f8f8f8",      # class: 'w'
        Error:                     "#a40000 border:#ef2929", # class: 'err'
        Other:                     "#000000",                # class 'x'

        Comment:                   "italic #8f5902", # class: 'c'
        Comment.Preproc:           "noitalic",       # class: 'cp'

        Keyword:                   "bold #004461",   # class: 'k'
        Keyword.Constant:          "bold #004461",   # class: 'kc'
        Keyword.Declaration:       "bold #004461",   # class: 'kd'
        Keyword.Namespace:         "bold #004461",   # class: 'kn'
        Keyword.Pseudo:            "bold #004461",   # class: 'kp'
        Keyword.Reserved:          "bold #004461",   # class: 'kr'
        Keyword.Type:              "bold #004461",   # class: 'kt'

        Operator:                  "#582800",   # class: 'o'
        Operator.Word:             "bold #004461",   # class: 'ow' - like keywords

        Punctuation:               "bold #000000",   # class: 'p'

        # because special names such as Name.Class, Name.Function, etc.
        # are not recognized as such later in the parsing, we choose them
        # to look the same as ordinary variables.
        Name:                      "#000000",        # class: 'n'
        Name.Attribute:            "#c4a000",        # class: 'na' - to be revised
        Name.Builtin:              "#004461",        # class: 'nb'
        Name.Builtin.Pseudo:       "#3465a4",        # class: 'bp'
        Name.Class:                "#000000",        # class: 'nc' - to be revised
        Name.Constant:             "#000000",        # class: 'no' - to be revised
        Name.Decorator:            "#888",           # class: 'nd' - to be revised
        Name.Entity:               "#ce5c00",        # class: 'ni'
        Name.Exception:            "bold #cc0000",   # class: 'ne'
        Name.Function:             "#000000",        # class: 'nf'
        Name.Property:             "#000000",        # class: 'py'
        Name.Label:                "#f57900",        # class: 'nl'
        Name.Namespace:            "#000000",        # class: 'nn' - to be revised
        Name.Other:                "#000000",        # class: 'nx'
        Name.Tag:                  "bold #004461",   # class: 'nt' - like a keyword
        Name.Variable:             "#000000",        # class: 'nv' - to be revised
        Name.Variable.Class:       "#000000",        # class: 'vc' - to be revised
        Name.Variable.Global:      "#000000",        # class: 'vg' - to be revised
        Name.Variable.Instance:    "#000000",        # class: 'vi' - to be revised

        Number:                    "#990000",        # class: 'm'

        Literal:                   "#000000",        # class: 'l'
        Literal.Date:              "#000000",        # class: 'ld'

        String:                    "#4e9a06",        # class: 's'
        String.Backtick:           "#4e9a06",        # class: 'sb'
        String.Char:               "#4e9a06",        # class: 'sc'
        String.Doc:                "italic #8f5902", # class: 'sd' - like a comment
        String.Double:             "#4e9a06",        # class: 's2'
        String.Escape:             "#4e9a06",        # class: 'se'
        String.Heredoc:            "#4e9a06",        # class: 'sh'
        String.Interpol:           "#4e9a06",        # class: 'si'
        String.Other:              "#4e9a06",        # class: 'sx'
        String.Regex:              "#4e9a06",        # class: 'sr'
        String.Single:             "#4e9a06",        # class: 's1'
        String.Symbol:             "#4e9a06",        # class: 'ss'

        Generic:                   "#000000",        # class: 'g'
        Generic.Deleted:           "#a40000",        # class: 'gd'
        Generic.Emph:              "italic #000000", # class: 'ge'
        Generic.Error:             "#ef2929",        # class: 'gr'
        Generic.Heading:           "bold #000080",   # class: 'gh'
        Generic.Inserted:          "#00A000",        # class: 'gi'
        Generic.Output:            "#888",           # class: 'go'
        Generic.Prompt:            "#745334",        # class: 'gp'
        Generic.Strong:            "bold #000000",   # class: 'gs'
        Generic.Subheading:        "bold #800080",   # class: 'gu'
        Generic.Traceback:         "bold #a40000",   # class: 'gt'
    }

########NEW FILE########
__FILENAME__ = test_conf
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
test_conf
------------

Tests for `complexity.conf` module.
"""

import logging
import sys

from complexity import conf

if sys.version_info[:2] < (2, 7):
    import unittest2 as unittest
else:
    import unittest


# Log debug and above to console
logging.basicConfig(format='%(levelname)s: %(message)s', level=logging.DEBUG)


class TestConf(unittest.TestCase):

    def test_read_conf(self):
        conf_dict = conf.read_conf('tests/conf_proj')
        logging.debug("read_conf returned {0}".format(conf_dict))
        self.assertTrue(conf_dict)
        self.assertEqual(
            conf_dict,
            {
                'output_dir': '../www',
                'templates_dir': 'templates',
                'unexpanded_templates': ['404.html', '500.html']
            }
        )

    def test_get_unexpanded_list(self):
        conf_dict = {
            'output_dir': '../www',
            'templates_dir': 'templates',
            'unexpanded_templates': ['404.html', '500.html']
        }
        self.assertEqual(
            conf.get_unexpanded_list(conf_dict),
            ['404.html', '500.html']
        )

    def test_get_unexpanded_list_empty(self):
        self.assertEqual(conf.get_unexpanded_list({}), ())

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_examples
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
test_examples
--------------

Tests for the Complexity example repos.
"""

import os
import shutil
import sys

from complexity import main

if sys.version_info[:2] < (2, 7):
    import unittest2 as unittest
else:
    import unittest


class TestExample(unittest.TestCase):

    def setUp(self):
        os.system(
            'git clone https://github.com/audreyr/complexity-example.git'
        )

    def test_complexity_example(self):
        """
        Tests that https://github.com/audreyr/complexity-example.git works.
        """

        main.complexity('complexity-example/project/')
        self.assertTrue(os.path.isfile('complexity-example/www/index.html'))
        self.assertTrue(
            os.path.isfile('complexity-example/www/about/index.html')
        )
        self.assertTrue(
            os.path.isfile(
                'complexity-example/www/img/glyphicons-halflings.png'
            )
        )

    def tearDown(self):
        shutil.rmtree('complexity-example')


class TestExample2(unittest.TestCase):

    def setUp(self):
        os.system(
            'git clone https://github.com/audreyr/complexity-example2.git'
        )

    def test_complexity_example(self):
        """
        Tests that https://github.com/audreyr/complexity-example2.git works.
        """

        main.complexity('complexity-example2/project/')
        self.assertTrue(
            os.path.isfile('complexity-example2/www/index.html')
        )
        self.assertTrue(os.path.isfile(
            'complexity-example2/www/about/index.html')
        )
        self.assertTrue(
            os.path.isfile('complexity-example2/www/repos/index.html')
        )
        self.assertTrue(
            os.path.isfile(
                'complexity-example2/www/img/glyphicons-halflings.png'
            )
        )
        self.assertTrue(
            os.path.isfile('complexity-example2/www/charts/index.html')
        )
        self.assertTrue(
            os.path.isfile('complexity-example2/www/charts/bar/index.html')
        )
        self.assertTrue(
            os.path.isfile('complexity-example2/www/charts/pie/index.html')
        )
        self.assertTrue(
            os.path.isfile(
                'complexity-example2/www/charts/pie/basic/index.html'
            )
        )
        self.assertTrue(
            os.path.isfile(
                'complexity-example2/www/charts/pie/donut/index.html'
            )
        )

    def tearDown(self):
        shutil.rmtree('complexity-example2')

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_generate
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
test_generate
--------------

Tests for `complexity.generate` module.
"""

import os
import shutil
import sys

from jinja2 import FileSystemLoader
from jinja2.environment import Environment

from complexity import generate

if sys.version_info[:2] < (2, 7):
    import unittest2 as unittest
else:
    import unittest


class TestGetOutputFilename(unittest.TestCase):

    def test_get_output_filename(self):
        outfile = generate.get_output_filename(
            './index.html',
            'www',
            force_unexpanded=False
        )
        self.assertEqual(outfile, 'www/index.html')

    def test_get_output_filename_about(self):
        outfile = generate.get_output_filename(
            './about.html',
            'www',
            force_unexpanded=False
        )
        self.assertEqual(outfile, 'www/about/index.html')

    def test_get_output_filename_base(self):
        outfile = generate.get_output_filename(
            './base.html',
            'www',
            force_unexpanded=False
        )
        self.assertFalse(outfile)

    def test_get_output_filename_base_design(self):
        outfile = generate.get_output_filename(
            './base_design.html',
            'www',
            force_unexpanded=False
        )
        self.assertFalse(outfile)

    def test_get_output_filename_art(self):
        outfile = generate.get_output_filename(
            './art/index.html',
            'www',
            force_unexpanded=False
        )
        self.assertEqual(outfile, 'www/art/index.html')
        outfile = generate.get_output_filename(
            'art/index.html',
            'www',
            force_unexpanded=False
        )
        self.assertEqual(outfile, 'www/art/index.html')

    def test_get_output_filename_color(self):
        outfile = generate.get_output_filename(
            './art/color.html',
            'www',
            force_unexpanded=False
        )
        self.assertEqual(outfile, 'www/art/color/index.html')


class TestGenerateHTMLFile(unittest.TestCase):
    def setUp(self):
        os.mkdir('tests/www/')
        self.env = Environment()
        self.env.loader = FileSystemLoader('tests/project/templates/')

    def test_generate_html_file(self):
        generate.generate_html_file(
            template_filepath='index.html',
            output_dir='tests/www/',
            env=self.env,
            context={}
        )
        self.assertTrue(os.path.isfile('tests/www/index.html'))
        self.assertFalse(os.path.isfile('tests/www/about/index.html'))
        self.assertFalse(os.path.isfile('tests/www/base/index.html'))

    def test_generate_html_file_art(self):
        generate.generate_html_file(
            template_filepath='art/index.html',
            output_dir='tests/www/',
            env=self.env,
            context={}
        )
        self.assertTrue(os.path.isfile('tests/www/art/index.html'))
        self.assertFalse(os.path.isfile('tests/www/index.html'))
        self.assertFalse(os.path.isfile('tests/www/about/index.html'))
        self.assertFalse(os.path.isfile('tests/www/base/index.html'))

    def tearDown(self):
        shutil.rmtree('tests/www')


class TestGenerateHTMLFileUnicode(unittest.TestCase):
    def setUp(self):
        os.mkdir('tests/www/')
        self.env = Environment()
        self.env.loader = FileSystemLoader('tests/files/')

    def test_generate_html_file_unicode(self):
        generate.generate_html_file(
            template_filepath='unicode.html',
            output_dir='tests/www/',
            env=self.env,
            context={}
        )
        self.assertTrue(os.path.isfile('tests/www/unicode/index.html'))
        with open('tests/files/unicode.html') as infile:
            with open('tests/www/unicode/index.html') as outfile:
                self.assertEqual(infile.read(), outfile.read())

    def test_generate_html_file_unicode2(self):
        generate.generate_html_file(
            template_filepath='unicode2.html',
            output_dir='tests/www/',
            env=self.env,
            context={}
        )
        self.assertTrue(os.path.isfile('tests/www/unicode2/index.html'))
        expected = """<!DOCTYPE html>
<html>
<body>

<p>This is the unicode test page.</p>
<p>Polish: Ą Ł Ż</p>
<p>Chinese: 倀 倁 倂 倃 倄 倅 倆 倇 倈</p>
<p>Musical Notes: ♬ ♫ ♯</p>
<h3 class="panel-title">Paški sir</h3>
<p>Croatian: š š</p>

</body>
</html>"""
        with open('tests/www/unicode2/index.html') as outfile:
            self.assertEqual(expected, outfile.read())

    def tearDown(self):
        shutil.rmtree('tests/www')


class TestGenerateHTML(unittest.TestCase):
    def test_generate_html(self):
        generate.generate_html(
            templates_dir='tests/project/templates/',
            output_dir='tests/www/',
            context=None,
            unexpanded_templates=[]
        )
        self.assertTrue(os.path.isfile('tests/www/index.html'))
        self.assertTrue(os.path.isfile('tests/www/about/index.html'))
        self.assertFalse(os.path.isfile('tests/www/base/index.html'))
        self.assertTrue(os.path.isfile('tests/www/art/index.html'))
        self.assertTrue(os.path.isfile('tests/www/art/color/index.html'))
        self.assertTrue(os.path.isfile('tests/www/art/cupcakes/index.html'))
        self.assertTrue(
            os.path.isfile('tests/www/art/cupcakes/chocolate/index.html')
        )
        self.assertFalse(os.path.isfile('tests/www/bad_templated_binary.png'))
        shutil.rmtree('tests/www')


class TestGenerateHTMLUnexpanded(unittest.TestCase):
    def test_generate_html_unexpanded(self):
        generate.generate_html(
            templates_dir='tests/project/templates/',
            output_dir='tests/www',
            context=None,
            unexpanded_templates=[
                '404.html',
                '500.html',
                "long/path/to/folder/dont-expand.html"
            ]
        )
        self.assertTrue(os.path.isfile('tests/www/index.html'))
        self.assertTrue(os.path.isfile('tests/www/about/index.html'))
        self.assertFalse(os.path.isfile('tests/www/base/index.html'))
        self.assertTrue(os.path.isfile('tests/www/art/index.html'))
        self.assertTrue(os.path.isfile('tests/www/art/color/index.html'))
        self.assertTrue(os.path.isfile('tests/www/art/cupcakes/index.html'))
        self.assertTrue(
            os.path.isfile('tests/www/art/cupcakes/chocolate/index.html')
        )
        self.assertTrue(os.path.isfile('tests/www/404.html'))
        self.assertTrue(os.path.isfile('tests/www/500.html'))
        self.assertTrue(
            os.path.isfile('tests/www/long/path/to/folder/dont-expand.html')
        )

    def tearDown(self):
        if os.path.isdir('tests/www'):
            shutil.rmtree('tests/www')


class TestGenerateContext(unittest.TestCase):
    def test_generate_context(self):
        context = generate.generate_context(
            context_dir='tests/project/context/'
        )
        self.assertEqual(context, {"test": {"1": 2}})


class TestCopyAssets(unittest.TestCase):
    def test_copy_assets(self):
        os.mkdir('tests/www/')
        generate.copy_assets(
            assets_dir='tests/project/assets/',
            output_dir='tests/www/'
        )
        self.assertTrue(
            os.path.isfile('tests/www/css/bootstrap-responsive.min.css')
        )
        self.assertTrue(os.path.isfile('tests/www/css/bootstrap.min.css'))
        self.assertTrue(
            os.path.isfile('tests/www/img/glyphicons-halflings.png')
        )
        self.assertTrue(os.path.isfile('tests/www/js/bootstrap.min.js'))
        self.assertTrue(os.path.isfile('tests/www/robots.txt'))
        shutil.rmtree('tests/www')


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_main
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
test_main
----------------

Tests for `complexity.main` module.
"""

import logging
import os
import shutil
import sys

from complexity import main

if sys.version_info[:2] < (2, 7):
    import unittest2 as unittest
else:
    import unittest


# Log debug and above to console
# logging.basicConfig(format='%(levelname)s: %(message)s', level=logging.DEBUG)


class TestMain(unittest.TestCase):

    def test_get_complexity_args(self):
        """ TODO: figure out how to test argparse here. """
        pass


class TestConfProj(unittest.TestCase):

    def test_conf_proj_with_complexity(self):
        main.complexity('tests/conf_proj')
        self.assertTrue(os.path.isfile('tests/www/index.html'))
        self.assertTrue(os.path.isfile('tests/www/about/index.html'))

    def tearDown(self):
        if os.path.isdir('tests/www'):
            shutil.rmtree('tests/www')


class TestConfProj2(unittest.TestCase):

    def test_conf_proj2_with_complexity(self):
        main.complexity('tests/conf_proj2')
        self.assertTrue(os.path.isfile('tests/conf_proj2/wwwz/index.html'))
        self.assertTrue(
            os.path.isfile('tests/conf_proj2/wwwz/about/index.html')
        )

    def tearDown(self):
        if os.path.isdir('tests/conf_proj2/wwwz'):
            shutil.rmtree('tests/conf_proj2/wwwz')


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_utils
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
test_utils
------------

Tests for `complexity.utils` module.
"""

import shutil
import sys

from complexity import utils

if sys.version_info[:2] < (2, 7):
    import unittest2 as unittest
else:
    import unittest


class TestUtils(unittest.TestCase):

    def test_make_sure_path_exists(self):
        self.assertTrue(utils.make_sure_path_exists('/usr/'))
        self.assertTrue(utils.make_sure_path_exists('tests/blah'))
        self.assertTrue(utils.make_sure_path_exists('tests/trailingslash/'))
        self.assertFalse(
            utils.make_sure_path_exists(
                '/this-dir-does-not-exist-and-cant-be-created/'
            )
        )
        shutil.rmtree('tests/blah/')
        shutil.rmtree('tests/trailingslash/')

    def test_unicode_open(self):
        """ Test unicode_open(filename, *args, **kwargs). """

        unicode_text = u"""Polish: Ą Ł Ż
Chinese: 倀 倁 倂 倃 倄 倅 倆 倇 倈
Musical Notes: ♬ ♫ ♯"""

        with utils.unicode_open('tests/files/unicode.txt') as f:
            opened_text = f.read()
            self.assertEqual(unicode_text, opened_text)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
