__FILENAME__ = dxr-build
#!/usr/bin/env python2
"""Command to build a DXR instance from one or more source trees"""

from optparse import OptionParser
import os.path
from os.path import isdir
from sys import exit, stderr

from dxr.build import build_instance


def main():
    parser = OptionParser(
        usage='usage: %prog [options] [folder containing dxr.config | config '
              'file]',
        description='If no args are given, defaults to looking for a config '
                    'file called dxr.config in the current working directory.')
    parser.add_option('-f', '--file', dest='config_file',
                      help='A DXR config file. [Deprecated. Use the first '
                           'positional arg instead.]')
    parser.add_option('-t', '--tree', dest='tree',
                      help='An INI section title in the config file, '
                           'specifying a source tree to build. (Default: all '
                           'trees.)')
    parser.add_option('-j', '--jobs', dest='jobs',
                      type='int',
                      default=None,
                      help='Number of parallel processes to use, (Default: the'
                           ' value of nb_jobs in the config file)')
    parser.add_option('-v', '--verbose', dest='verbose',
                      action='store_true', default=False,
                      help='Display the build logs during the build instead of'
                           ' only on error.')
    options, args = parser.parse_args()
    if len(args) > 1:
        parser.print_usage()

    if args:
        # Handle deprecated --file arg:
        if options.config_file:
            print >> stderr, ('Warning: overriding the --file or -f flag with '
                              'the first positional argument.')
        options.config_file = (os.path.join(args[0], 'dxr.config') if
                               isdir(args[0]) else args[0])
    elif not options.config_file:
        # Assume dxr.config in the cwd:
        options.config_file = 'dxr.config'

    return build_instance(options.config_file,
                          nb_jobs=options.jobs,
                          tree=options.tree,
                          verbose=options.verbose)


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = dxr-serve
#!/usr/bin/env python2
"""A simple test server for DXR, not suitable for production

Use a web server with WSGI support for actual deployments.

"""
from optparse import OptionParser
from os.path import abspath

from dxr.app import make_app


def main():
    parser = OptionParser(usage='usage: %prog [options] build-folder',
                          add_help_option=False)
    parser.add_option('--help', action='help')
    parser.add_option('-a', '--all', dest='host',
                      action='store_const',
                      const='0.0.0.0',
                      help='Serve on all interfaces.  Equivalent to --host 0.0.0.0')
    parser.add_option('-h', '--host', dest='host',
                      type='string',
                      default='localhost',
                      help='The host address to serve on')
    parser.add_option('-j', '--jobs', dest='processes',
                      type='int',
                      default=1,
                      help='The number of processes to use')
    parser.add_option('-p', '--port', dest='port',
                      type='int',
                      default=8000,
                      help='The port to serve on')
    parser.add_option('-t', '--threaded', dest='threaded',
                      action='store_true',
                      default=False,
                      help='Use a separate thread for each request')
    options, args = parser.parse_args()
    if len(args) == 1:
        app = make_app(abspath(args[0]))
        app.debug = True
        app.run(host=options.host, port=options.port,
                processes=options.processes, threaded=options.threaded)
    else:
        parser.print_usage()


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = deploy
"""Continuous deployment script for DXR

Glossary
========

build directory - A folder, typically in the ``builds`` folder, containing
    these folders...

    dxr - A checkout of the DXR source code
    target - A symlink to the instance to serve
    virtualenv - A virtualenv with DXR and its dependencies installed

    Builds are named after an excerpt of their git hashes and are symlinked
    into the base directory.

base directory - The folder containing these folders...

    builds - A folder of builds, including the current production and staging
        ones
    dxr-prod - A symlink to the current production build
    dxr-staging - A symlink to the current staging build
    instances - A folder of DXR instances organized according to format version

"""
# When we need to make this work across multiple nodes:
# I really have no reason to use Commander over Fabric: I don't need Chief, and
# nearly all the features and conveniences Commander had over Fabric have been
# since implemented in Fabric. Fabric has more features and more support and
# was released more recently. OTOH, Fabric's argument conventions are crazy.

# TODO: Update the deployment script first, and use the new version to deploy.
# That way, each version is deployed by the deployment script that ships with
# it.

from contextlib import contextmanager
from optparse import OptionParser
import os
from os import chdir, O_CREAT, O_EXCL, remove, getcwd
from os.path import join, exists
from pipes import quote
from subprocess import check_output
from tempfile import mkdtemp, gettempdir

import requests


def main():
    """Handle command-line munging, and pass off control to the interesting
    stuff."""
    parser = OptionParser(
        usage='usage: %prog [options] <staging | prod>',
        description='Deploy a new version of DXR.')
    parser.add_option('-b', '--base', dest='base_path',
                      help='Path to the dir containing the builds, instances, '
                           'and deployment links')
    parser.add_option('-c', '--branch', dest='branch',
                      help='Deploy the revision from this branch which last '
                           'passed Jenkins.')
    parser.add_option('-p', '--python', dest='python_path',
                      help='Path to the Python executable on which to base the'
                           ' virtualenvs')
    parser.add_option('-e', '--repo', dest='repo',
                      help='URL of the git repo from which to download DXR. '
                           'Use HTTPS if possible to ward off spoofing.')
    parser.add_option('-r', '--rev', dest='manual_rev',
                      help='A hash of the revision to deploy. Defaults to the '
                           'last successful Jenkins build on the branch '
                           'specified by -c (or master, by default).')

    options, args = parser.parse_args()
    if len(args) == 1:
        non_none_options = dict((k, getattr(options, k)) for k in
                                (o.dest for o in parser.option_list if o.dest)
                                if getattr(options, k))
        Deployment(args[0], **non_none_options).deploy_if_appropriate()
    else:
        parser.print_usage()


class Deployment(object):
    """A little inversion-of-control framework for deployments

    Maybe someday we'll plug in methods to handle a different project.

    """
    def __init__(self,
                 kind,
                 base_path='/data',
                 python_path='/usr/bin/python2.7',
                 repo='https://github.com/mozilla/dxr.git',
                 branch='master',
                 manual_rev=None):
        """Construct.

        :arg kind: The type of deployment this is, either "staging" or "prod".
            Affects only some folder names.
        :arg base_path: Path to the dir containing the builds, instances, and
            deployment links
        :arg python_path: Path to the Python executable on which to base the
            virtualenvs
        :arg repo: URL of the git repo from which to download DXR. Use HTTPS if
            possible to ward off spoofing.
        :arg branch: The most recent passing Jenkins build from this branch
            will be deployed by default.
        :arg manual_rev: A hash of the revision to deploy. Defaults to the last
            successful Jenkins build on ``branch``.
        """
        self.kind = kind
        self.base_path = base_path
        self.python_path = python_path
        self.repo = repo
        self.branch = branch
        self.manual_rev = manual_rev

    def rev_to_deploy(self):
        """Return the VCS revision identifier of the version we should
        deploy.

        If we shouldn't deploy for some reason (like if we're already at the
        newest revision or nobody has pressed the Deploy button since the last
        deploy), raise ShouldNotDeploy.

        """
        with cd(join(self._deployment_path(), 'dxr')):
            old_hash = run('git rev-parse --verify HEAD').strip()
        new_hash = self._latest_successful_build()
        if old_hash == new_hash:
            raise ShouldNotDeploy('The latest test-passing revision is already'
                                  ' deployed.')
        return new_hash

    def _latest_successful_build(self):
        """Return the SHA of the latest test-passing commit on master."""
        response = requests.get('https://ci.mozilla.org/job/dxr/'
                                'lastSuccessfulBuild/git/api/json',
                                verify=True)
        return (response.json()['buildsByBranchName']
                               ['origin/%s' % self.branch]
                               ['revision']
                               ['SHA1'])

    def build(self, rev):
        """Create and return the path of a new directory containing a new
        deployment of the given revision of the source.

        If it turns out we shouldn't deploy this build after all (perhaps
        because some additional data yielded by an asynchronous build process
        isn't yet available in the new format) but there hasn't been a
        programming error that would warrant a more serious exception, raise
        ShouldNotDeploy.

        """
        VENV_NAME = 'virtualenv'
        new_build_path = mkdtemp(prefix='%s-' % rev[:6],
                                 dir=join(self.base_path, 'builds'))
        with cd(new_build_path):
            # Make a fresh, blank virtualenv:
            run('virtualenv -p {python} --no-site-packages {venv_name}',
                python=self.python_path,
                venv_name=VENV_NAME)

            # Check out the source, and install DXR and dependencies:
            run('git clone {repo}', repo=self.repo)
            with cd('dxr'):
                run('git checkout -q {rev}', rev=rev)

                # If there's no instance of a suitable version, bail out:
                with open('format') as format_file:
                    format = format_file.read().rstrip()
                target_path = '{base_path}/instances/{format}/target'.format(
                    base_path=self.base_path, format=format)
                if not exists(target_path):
                    raise ShouldNotDeploy('A version-{format} instance is not ready yet.'.format(format=format))

                run('git submodule update -q --init --recursive')
                # Make sure a malicious server didn't slip us a mickey. TODO:
                # Does this recurse into submodules?
                run('git fsck --no-dangling')

                # Install stuff, using the new copy of peep from the checkout:
                python = join(new_build_path, VENV_NAME, 'bin', 'python')
                run('{python} ./peep.py install -r requirements.txt',
                    python=python)
                # Compile nunjucks templates:
                run('make templates &> /dev/null')
                # Quiet the complaint about there being no matches for *.so:
                run('{python} setup.py install 2>/dev/null', python=python)

            # After installing, you always have to re-run this, even if we
            # were reusing a venv:
            run('virtualenv --relocatable {venv}',
                venv=join(new_build_path, VENV_NAME))

            # Link to the built DXR instance:
            run('ln -s {points_to} target', points_to=target_path)

            run('chmod 755 .')  # mkdtemp uses a very conservative mask.
        return new_build_path

    def install(self, new_build_path):
        """Install a build at ``self.deployment_path``.

        Avoid race conditions as much as possible. If it turns out we should
        not deploy for some anticipated reason, raise ShouldNotDeploy.

        """
        with cd(new_build_path):
            run('ln -s {points_to} {sits_at}',
                points_to=new_build_path,
                sits_at='new-link')
            # Big, fat atomic (nay, nuclear) mv:
            run('mv -T new-link {dest}', dest=self._deployment_path())
        # TODO: Delete the old build or maybe all the builds that aren't this
        # one or the previous one (which we can get by reading the old symlink).

        # TODO: Does just frobbing the symlink count as touching the wsgi file?

    def deploy_if_appropriate(self):
        """Deploy a new build if we should."""
        with nonblocking_lock('dxr-deploy-%s' % self.kind) as got_lock:
            if got_lock:
                try:
                    rev = self.manual_rev or self.rev_to_deploy()
                    new_build_path = self.build(rev)
                    self.install(new_build_path)
                except ShouldNotDeploy:
                    pass
                else:
                    # if not self.passes_smoke_test():
                    #     self.rollback()
                    pass

    def _deployment_path(self):
        """Return the path of the symlink to the deployed build of DXR."""
        return join(self.base_path, 'dxr-%s' % self.kind)


def run(command, **kwargs):
    """Return the output of a command.

    Pass in any kind of shell-executable line you like, with one or more
    commands, pipes, etc. Any kwargs will be shell-escaped and then subbed into
    the command using ``format()``::

        >>> run('echo hi')
        "hi"
        >>> run('echo {name}', name='Fred')
        "Fred"

    This is optimized for callsite readability. Internalizing ``format()``
    keeps noise off the call. If you use named substitution tokens, individual
    commands are almost as readable as in a raw shell script. The command
    doesn't need to be read out of order, as with anonymous tokens.

    """
    output = check_output(
        command.format(**dict((k, quote(v)) for k, v in kwargs.iteritems())),
        shell=True)
    return output


@contextmanager
def cd(path):
    """Change the working dir on enter, and change it back on exit."""
    old_dir = getcwd()
    chdir(path)
    yield
    chdir(old_dir)


@contextmanager
def nonblocking_lock(lock_name):
    """Context manager that acquires and releases a file-based lock.

    If it cannot immediately acquire it, it falls through and returns False.
    Otherwise, it returns True.

    """
    lock_path = join(gettempdir(), lock_name + '.lock')
    try:
        fd = os.open(lock_path, O_CREAT | O_EXCL, 0644)
    except OSError:
        got = False
    else:
        got = True

    try:
        yield got
    finally:
        if got:
            os.close(fd)
            remove(lock_path)


class ShouldNotDeploy(Exception):
    """We should not deploy this build at the moment, though there was no
    programming error."""


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# DXR: Code Search and Cross-Reference Tool documentation build configuration file, created by
# sphinx-quickstart on Fri Mar 14 18:40:04 2014.
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

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#sys.path.insert(0, os.path.abspath('.'))

# -- General configuration ------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.doctest',
    'sphinx.ext.intersphinx',
    'sphinx.ext.todo',
    'sphinx.ext.coverage',
    'sphinx.ext.pngmath',
    'sphinx.ext.mathjax',
    'sphinx.ext.ifconfig',
    'sphinx.ext.viewcode',
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'DXR: Code Search and Cross-Reference Tool'
copyright = u'2014, various'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '0.1'
# The full version, including alpha/beta/rc tags.
release = '0.1'

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

# The reST default role (used for this markup: `text`) to use for all
# documents.
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


# -- Options for HTML output ----------------------------------------------

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

# Add any extra paths that contain custom files (such as robots.txt or
# .htaccess) here, relative to this directory. These files are copied
# directly to the root of the documentation.
#html_extra_path = []

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
htmlhelp_basename = 'DXRCodeSearchandCross-ReferenceTooldoc'


# -- Options for LaTeX output ---------------------------------------------

latex_elements = {
# The paper size ('letterpaper' or 'a4paper').
#'papersize': 'letterpaper',

# The font size ('10pt', '11pt' or '12pt').
#'pointsize': '10pt',

# Additional stuff for the LaTeX preamble.
#'preamble': '',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title,
#  author, documentclass [howto, manual, or own class]).
latex_documents = [
  ('index', 'DXRCodeSearchandCross-ReferenceTool.tex', u'DXR: Code Search and Cross-Reference Tool Documentation',
   u'various', 'manual'),
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


# -- Options for manual page output ---------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'dxrcodesearchandcross-referencetool', u'DXR: Code Search and Cross-Reference Tool Documentation',
     [u'various'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output -------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'DXRCodeSearchandCross-ReferenceTool', u'DXR: Code Search and Cross-Reference Tool Documentation',
   u'various', 'DXRCodeSearchandCross-ReferenceTool', 'One line description of project.',
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


# -- Options for Epub output ----------------------------------------------

# Bibliographic Dublin Core info.
epub_title = u'DXR: Code Search and Cross-Reference Tool'
epub_author = u'various'
epub_publisher = u'various'
epub_copyright = u'2014, various'

# The basename for the epub file. It defaults to the project name.
#epub_basename = u'DXR: Code Search and Cross-Reference Tool'

# The HTML theme for the epub output. Since the default themes are not optimized
# for small screen space, using the same theme for HTML and epub output is
# usually not wise. This defaults to 'epub', a theme designed to save visual
# space.
#epub_theme = 'epub'

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

# A tuple containing the cover image and cover page html template filenames.
#epub_cover = ()

# A sequence of (type, uri, title) tuples for the guide element of content.opf.
#epub_guide = ()

# HTML files that should be inserted before the pages created by sphinx.
# The format is a list of tuples containing the path and title.
#epub_pre_files = []

# HTML files shat should be inserted after the pages created by sphinx.
# The format is a list of tuples containing the path and title.
#epub_post_files = []

# A list of files that should not be packed into the epub file.
epub_exclude_files = ['search.html']

# The depth of the table of contents in toc.ncx.
#epub_tocdepth = 3

# Allow duplicate toc entries.
#epub_tocdup = True

# Choose between 'default' and 'includehidden'.
#epub_tocscope = 'default'

# Fix unsupported image types using the PIL.
#epub_fix_images = False

# Scale large images.
#epub_max_image_width = 0

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#epub_show_urls = 'inline'

# If false, no index is generated.
#epub_use_index = True


# Example configuration for intersphinx: refer to the Python standard library.
intersphinx_mapping = {'http://docs.python.org/': None}

########NEW FILE########
__FILENAME__ = app
from logging import StreamHandler
from os.path import isdir, isfile, join
from sys import stderr
from time import time
from urllib import quote_plus

from flask import (Blueprint, Flask, send_from_directory, current_app,
                   send_file, request, redirect, jsonify, render_template)

from dxr.query import Query, filter_menu_items
from dxr.utils import connect_db, non_negative_int, search_url, TEMPLATE_DIR, sqlite3  # Make sure we load trilite before possibly importing the wrong version of sqlite3.


# Look in the 'dxr' package for static files, etc.:
dxr_blueprint = Blueprint('dxr_blueprint', 'dxr', template_folder=TEMPLATE_DIR)


def make_app(instance_path):
    """Return a DXR application which looks in the given folder for
    configuration.

    Also set up the static and template folder according to the configured
    template.

    """
    # TODO: Actually obey the template selection in the config file by passing
    # a different static_folder and template_folder to Flask().
    app = Flask('dxr', instance_path=instance_path)
    app.register_blueprint(dxr_blueprint)

    # Load the special config file generated by dxr-build:
    app.config.from_pyfile(join(app.instance_path, 'config.py'))

    # Log to Apache's error log in production:
    app.logger.addHandler(StreamHandler(stderr))
    return app


@dxr_blueprint.route('/')
def index():
    config = current_app.config
    wwwroot = config['WWW_ROOT']    
    tree = config['DEFAULT_TREE']
    return redirect('%s/%s/source/' % (wwwroot, tree))


@dxr_blueprint.route('/<tree>/search')
def search(tree):
    """Search by regex, caller, superclass, or whatever."""
    # TODO: This function still does too much.
    querystring = request.values

    offset = non_negative_int(querystring.get('offset'), 0)
    limit = min(non_negative_int(querystring.get('limit'), 100), 1000)

    config = current_app.config
    www_root = config['WWW_ROOT']
    trees = config['TREES']

    # Arguments for the template:
    arguments = {
        # Common template variables
        'wwwroot': www_root,
        'generated_date': config['GENERATED_DATE']}

    error = warning = ''
    status_code = None

    if tree in trees:
        arguments['tree'] = tree

        # Connect to database
        try:
            conn = connect_db(join(current_app.instance_path, 'trees', tree))
        except sqlite3.Error:
            error = 'Failed to establish database connection.'
        else:
            # Parse the search query
            qtext = querystring.get('q', '')
            is_case_sensitive = querystring.get('case') == 'true'
            q = Query(conn,
                      qtext,
                      should_explain='explain' in querystring,
                      is_case_sensitive=is_case_sensitive)

            # Try for a direct result:
            if querystring.get('redirect') == 'true':
                result = q.direct_result()
                if result:
                    path, line = result
                    # TODO: Does this escape qtext properly?
                    return redirect(
                        '%s/%s/source/%s?from=%s%s#%i' %
                        (www_root,
                         tree,
                         path,
                         qtext,
                         '&case=true' if is_case_sensitive else '', line))

            # Return multiple results:
            template = 'search.html'
            start = time()
            try:
                results = list(q.results(offset, limit))
            except sqlite3.OperationalError as e:
                if e.message.startswith('REGEXP:'):
                    # Malformed regex
                    warning = e.message[7:]
                    results = []
                elif e.message.startswith('QUERY:'):
                    warning = e.message[6:]
                    results = []
                else:
                    error = 'Database error: %s' % e.message
            if not error:
                # Search template variables:
                arguments['time'] = time() - start
                arguments['query'] = qtext
                arguments['search_url'] = search_url(www_root,
                                                     arguments['tree'],
                                                     qtext,
                                                     redirect=False)
                arguments['results'] = results
                arguments['offset'] = offset
                arguments['limit'] = limit
                arguments['is_case_sensitive'] = is_case_sensitive
                arguments['tree_tuples'] = [
                        (t,
                         search_url(www_root,
                                    t,
                                    qtext,
                                    case=True if is_case_sensitive else None),
                         description)
                        for t, description in trees.iteritems()]
    else:
        arguments['tree'] = trees.keys()[0]
        error = "Tree '%s' is not a valid tree." % tree
        status_code = 404

    if warning or error:
        arguments['error'] = error or warning

    if querystring.get('format') == 'json':
        if error:
            # Return a non-OK code so the live search doesn't try to replace
            # the results with our empty ones:
            return jsonify(arguments), status_code or 500

        # Tuples are encoded as lists in JSON, and these are not real
        # easy to unpack or read in Javascript. So for ease of use, we
        # convert to dictionaries before returning the json results.
        # If further discrepancies are introduced, please document them in
        # templating.mkd.
        arguments['results'] = [
            {'icon': icon,
             'path': path,
             'lines': [{'line_number': nb, 'line': l} for nb, l in lines]}
                for icon, path, lines in arguments['results']]
        return jsonify(arguments)

    if error:
        return render_template('error.html', **arguments), status_code or 500
    else:
        arguments['filters'] = filter_menu_items(config['FILTER_LANGUAGE'])
        return render_template('search.html', **arguments)


@dxr_blueprint.route('/<tree>/source/')
@dxr_blueprint.route('/<tree>/source/<path:path>')
def browse(tree, path=''):
    """Show a directory listing or a single file from one of the trees."""
    tree_folder = _tree_folder(tree)
    return send_from_directory(tree_folder, _html_file_path(tree_folder, path))


@dxr_blueprint.route('/<tree>/')
@dxr_blueprint.route('/<tree>')
def tree_root(tree):
    """Redirect requests for the tree root instead of giving 404s."""
    return redirect(tree + '/source/')


@dxr_blueprint.route('/<tree>/parallel/')
@dxr_blueprint.route('/<tree>/parallel/<path:path>')
def parallel(tree, path=''):
    """If a file or dir parallel to the given path exists in the given tree,
    redirect to it. Otherwise, redirect to the root of the given tree.

    We do this with the future in mind, in which pages may be rendered at
    request time. To make that fast, we wouldn't want to query every one of 50
    other trees, when drawing the Switch Tree menu, to see if a parallel file
    or folder exists. So we use this controller to put off the querying until
    the user actually choose another tree.

    """
    tree_folder = _tree_folder(tree)
    disk_path = _html_file_path(tree_folder, path)
    www_root = current_app.config['WWW_ROOT']
    if isfile(join(tree_folder, disk_path)):
        return redirect('{root}/{tree}/source/{path}'.format(
            root=www_root,
            tree=tree,
            path=path))
    else:
        return redirect('{root}/{tree}/source/'.format(
            root=www_root,
            tree=tree))


def _tree_folder(tree):
    """Return the on-disk path to the root of the given tree's folder in the
    instance."""
    return join(current_app.instance_path, 'trees', tree)


def _html_file_path(tree_folder, url_path):
    """Return the on-disk path, relative to the tree folder, of the HTML file
    that should be served when a certain path is browsed to.

    :arg tree_folder: The on-disk path to the tree's folder in the instance
    :arg url_path: The URL path browsed to, rooted just inside the tree

    If you provide a path to a non-existent file or folder, I will happily
    return a path which has no corresponding FS entity.

    """
    if isdir(join(tree_folder, url_path)):
        # It's a bare directory. Add the index file to the end:
        return join(url_path, current_app.config['DIRECTORY_INDEX'])
    else:
        # It's a file. Add the .html extension:
        return url_path + '.html'

########NEW FILE########
__FILENAME__ = build
from codecs import getdecoder
import cgi
from datetime import datetime
from errno import ENOENT
from fnmatch import fnmatchcase
from heapq import merge
from itertools import chain, groupby, izip_longest
import json
from operator import itemgetter
import os
from os import stat
from os.path import dirname, islink
import shutil
import subprocess
import sys
from sys import exc_info
from traceback import format_exc
from warnings import warn

from concurrent.futures import as_completed, ProcessPoolExecutor
from jinja2 import Markup
from ordereddict import OrderedDict

from dxr.config import Config
from dxr.plugins import load_htmlifiers, load_indexers
import dxr.languages
import dxr.mime
from dxr.query import filter_menu_items
from dxr.utils import connect_db, load_template_env, open_log, browse_url

try:
    from itertools import compress
except ImportError:
    from itertools import izip
    def compress(data, selectors):
        return (d for d, s in izip(data, selectors) if s)

def linked_pathname(path, tree_name):
    """Return a list of (server-relative URL, subtree name) tuples that can be
    used to display linked path components in the headers of file or folder
    pages.

    :arg path: The path that will be split

    """
    # Hold the root of the tree:
    components = [('/%s/source' % tree_name, tree_name)]

    # Populate each subtree:
    dirs = path.split(os.sep)  # TODO: Trips on \/ in path.

    # A special case when we're dealing with the root tree. Without
    # this, it repeats:
    if not path:
        return components

    for idx in range(1, len(dirs)+1):
        subtree_path = os.path.join('/', tree_name, 'source', *dirs[:idx])
        subtree_name = os.path.split(subtree_path)[1] or tree_name
        components.append((subtree_path, subtree_name))

    return components


def build_instance(config_path, nb_jobs=None, tree=None, verbose=False):
    """Build a DXR instance.

    :arg config_path: The path to a config file
    :arg nb_jobs: The number of parallel jobs to pass into ``make``. Defaults
        to whatever the config file says.
    :arg tree: A single tree to build. Defaults to all the trees in the config
        file.

    """
    # Load configuration file
    # (this will abort on inconsistencies)
    overrides = {}
    if nb_jobs:
        # TODO: Remove this brain-dead cast when we get the types right in the
        # Config object:
        overrides['nb_jobs'] = str(nb_jobs)
    config = Config(config_path, **overrides)

    skip_indexing = 'index' in config.skip_stages

    # Find trees to make, fail if requested tree isn't available
    if tree:
        trees = [t for t in config.trees if t.name == tree]
        if len(trees) == 0:
            print >> sys.stderr, "Tree '%s' is not defined in config file!" % tree
            sys.exit(1)
    else:
        # Build everything if no tree is provided
        trees = config.trees

    # Create config.target_folder (if not exists)
    print "Generating target folder"
    ensure_folder(config.target_folder, False)
    ensure_folder(config.temp_folder, not skip_indexing)
    ensure_folder(config.log_folder, not skip_indexing)

    jinja_env = load_template_env(config.temp_folder, config.dxrroot)

    # We don't want to load config file on the server, so we just write all the
    # setting into the config.py script, simple as that.
    _fill_and_write_template(
        jinja_env,
        'config.py.jinja',
        os.path.join(config.target_folder, 'config.py'),
        dict(trees=repr(OrderedDict((t.name, t.description)
                                    for t in config.trees)),
             wwwroot=repr(config.wwwroot),
             generated_date=repr(config.generated_date),
             directory_index=repr(config.directory_index),
             default_tree=repr(config.default_tree),
             filter_language=repr(config.filter_language)))

    # Create jinja cache folder in target folder
    ensure_folder(os.path.join(config.target_folder, 'jinja_dxr_cache'))

    # TODO Make open-search.xml things (or make the server so it can do them!)

    # Build trees requested
    ensure_folder(os.path.join(config.target_folder, 'trees'))
    for tree in trees:
        # Note starting time
        start_time = datetime.now()

        # Create folders (delete if exists)
        ensure_folder(tree.target_folder, not skip_indexing) # <config.target_folder>/<tree.name>
        ensure_folder(tree.object_folder,                    # Object folder (user defined!)
            tree.source_folder != tree.object_folder)        # Only clean if not the srcdir
        ensure_folder(tree.temp_folder,   not skip_indexing) # <config.temp_folder>/<tree.name>
                                                             # (or user defined)
        ensure_folder(tree.log_folder,    not skip_indexing) # <config.log_folder>/<tree.name>
                                                             # (or user defined)
        # Temporary folders for plugins
        ensure_folder(os.path.join(tree.temp_folder, 'plugins'), not skip_indexing)
        for plugin in tree.enabled_plugins:     # <tree.config>/plugins/<plugin>
            ensure_folder(os.path.join(tree.temp_folder, 'plugins', plugin), not skip_indexing)

        # Connect to database (exits on failure: sqlite_version, tokenizer, etc)
        conn = connect_db(tree.target_folder)

        if skip_indexing:
            print " - Skipping indexing (due to 'index' in 'skip_stages')"
        else:
            # Create database tables
            create_tables(tree, conn)

            # Index all source files (for full text search)
            # Also build all folder listing while we're at it
            index_files(tree, conn)

            # Build tree
            build_tree(tree, conn, verbose)

            # Optimize and run integrity check on database
            finalize_database(conn)

            # Commit database
            conn.commit()

        if 'html' in config.skip_stages:
            print " - Skipping htmlifying (due to 'html' in 'skip_stages')"
        else:
            print "Building HTML for the '%s' tree." % tree.name

            max_file_id = conn.execute("SELECT max(files.id) FROM files").fetchone()[0]
            if config.disable_workers:
                print " - Worker pool disabled (due to 'disable_workers')"
                _build_html_for_file_ids(tree, 0, max_file_id)
            else:
                run_html_workers(tree, config, max_file_id)

        # Close connection
        conn.commit()
        conn.close()

        # Save the tree finish time
        delta = datetime.now() - start_time
        print "(finished building '%s' in %s)" % (tree.name, delta)

    # Print a neat summary


def ensure_folder(folder, clean=False):
    """Ensure the existence of a folder.

    :arg clean: Whether to ensure that the folder is empty

    """
    if clean and os.path.isdir(folder):
        shutil.rmtree(folder, False)
    if not os.path.isdir(folder):
        os.mkdir(folder)


def create_tables(tree, conn):
    print "Creating tables"
    conn.execute("CREATE VIRTUAL TABLE trg_index USING trilite")
    conn.executescript(dxr.languages.language_schema.get_create_sql())


def _unignored_folders(folders, source_path, ignore_patterns, ignore_paths):
    """Yield the folders from ``folders`` which are not ignored by the given
    patterns and paths.

    :arg source_path: Relative path to the source directory
    :arg ignore_patterns: Non-path-based globs to be ignored
    :arg ignore_paths: Path-based globs to be ignored

    """
    for folder in folders:
        if not any(fnmatchcase(folder, p) for p in ignore_patterns):
            folder_path = '/' + os.path.join(source_path, folder).replace(os.sep, '/') + '/'
            if not any(fnmatchcase(folder_path, p) for p in ignore_paths):
                yield folder


def index_files(tree, conn):
    """Build the ``files`` table, the trigram index, and the HTML folder listings."""
    print "Indexing files from the '%s' tree" % tree.name
    start_time = datetime.now()
    cur = conn.cursor()
    # Walk the directory tree top-down, this allows us to modify folders to
    # exclude folders matching an ignore_pattern
    for root, folders, files in os.walk(tree.source_folder, topdown=True):
        # Find relative path
        rel_path = os.path.relpath(root, tree.source_folder)
        if rel_path == '.':
            rel_path = ""

        # List of file we indexed (ie. add to folder listing)
        indexed_files = []
        for f in files:
            # Ignore file if it matches an ignore pattern
            if any(fnmatchcase(f, e) for e in tree.ignore_patterns):
                continue  # Ignore the file.

            # file_path and path
            file_path = os.path.join(root, f)
            path = os.path.join(rel_path, f)

            # Ignore file if its path (relative to the root) matches an ignore path
            if any(fnmatchcase("/" + path.replace(os.sep, "/"), e) for e in tree.ignore_paths):
                continue  # Ignore the file.

            # the file
            try:
                with open(file_path, 'r') as source_file:
                    data = source_file.read()
            except IOError as exc:
                if exc.errno == ENOENT and islink(file_path):
                    # It's just a bad symlink (or a symlink that was swiped out
                    # from under us--whatever):
                    continue
                else:
                    raise

            # Discard non-text files
            if not dxr.mime.is_text(file_path, data):
                continue

            # Find an icon (ideally dxr.mime should use magic numbers, etc.)
            # that's why it makes sense to save this result in the database
            icon = dxr.mime.icon(path)

            # Insert this file
            cur.execute("INSERT INTO files (path, icon, encoding) VALUES (?, ?, ?)",
                        (path, icon, tree.source_encoding))
            # Index this file
            sql = "INSERT INTO trg_index (id, text) VALUES (?, ?)"
            cur.execute(sql, (cur.lastrowid, data))

            # Okay to this file was indexed
            indexed_files.append(f)

        # Exclude folders that match an ignore pattern.
        # os.walk listens to any changes we make in `folders`.
        folders[:] = _unignored_folders(
            folders, rel_path, tree.ignore_patterns, tree.ignore_paths)

        indexed_files.sort()
        folders.sort()
        # Now build folder listing and folders for indexed_files
        build_folder(tree, conn, rel_path, indexed_files, folders)

    # Okay, let's commit everything
    conn.commit()

    # Print time
    print "(finished in %s)" % (datetime.now() - start_time)


def build_folder(tree, conn, folder, indexed_files, indexed_folders):
    """Build an HTML index file for a single folder."""
    # Create the subfolder if it doesn't exist:
    ensure_folder(os.path.join(tree.target_folder, folder))

    # Build the folder listing:
    # Name is either basename (or if that is "" name of tree)
    name = os.path.basename(folder) or tree.name

    # Generate list of folders and their mod dates:
    folders = [('folder',
                f,
                datetime.fromtimestamp(stat(os.path.join(tree.source_folder,
                                                         folder,
                                                         f)).st_mtime),
                # TODO: DRY with Flask route. Use url_for:
                _join_url(tree.name, 'source', folder, f))
               for f in indexed_folders]

    # Generate list of files:
    files = []
    for f in indexed_files:
        # Get file path on disk
        path = os.path.join(tree.source_folder, folder, f)
        file_info = stat(path)
        files.append((dxr.mime.icon(path),
                      f,
                      datetime.fromtimestamp(file_info.st_mtime),
                      file_info.st_size,
                      _join_url(tree.name, 'source', folder, f)))

    # Lay down the HTML:
    jinja_env = load_template_env(tree.config.temp_folder,
                                  tree.config.dxrroot)
    dst_path = os.path.join(tree.target_folder,
                            folder,
                            tree.config.directory_index)

    _fill_and_write_template(
        jinja_env,
        'folder.html',
        dst_path,
        {# Common template variables:
         'wwwroot': tree.config.wwwroot,
         'tree': tree.name,
         'tree_tuples': [(t.name,
                          browse_url(t.name, tree.config.wwwroot, folder),
                          t.description)
                         for t in tree.config.sorted_tree_order],
         'generated_date': tree.config.generated_date,
         'paths_and_names': linked_pathname(folder, tree.name),
         'filters': filter_menu_items(tree.config.filter_language),
         # Autofocus only at the root of each tree:
         'should_autofocus_query': folder == '',

         # Folder template variables:
         'name': name,
         'path': folder,
         'folders': folders,
         'files': files})

def _join_url(*args):
    """Join URL path segments with "/", skipping empty segments."""
    return '/'.join(a for a in args if a)


def _fill_and_write_template(jinja_env, template_name, out_path, vars):
    """Get the template `template_name` from the template folder, substitute in
    `vars`, and write the result to `out_path`."""
    template = jinja_env.get_template(template_name)
    template.stream(**vars).dump(out_path, encoding='utf-8')


def build_tree(tree, conn, verbose):
    """Build the tree, pre_process, build and post_process."""
    # Load indexers
    indexers = load_indexers(tree)

    # Get system environment variables
    environ = {}
    for key, val in os.environ.items():
        environ[key] = val

    # Let plugins preprocess
    # modify environ, change makefile, hack things whatever!
    for indexer in indexers:
        indexer.pre_process(tree, environ)

    # Add source and build directories to the command
    environ["source_folder"] = tree.source_folder
    environ["build_folder"] = tree.object_folder

    # Open log file
    with open_log(tree, 'build.log', verbose) as log:
        # Call the make command
        print "Building the '%s' tree" % tree.name
        r = subprocess.call(
            tree.build_command.replace('$jobs', tree.config.nb_jobs),
            shell   = True,
            stdout  = log,
            stderr  = log,
            env     = environ,
            cwd     = tree.object_folder
        )

    # Abort if build failed!
    if r != 0:
        print >> sys.stderr, ("Build command for '%s' failed, exited non-zero."
                              % tree.name)
        if not verbose:
            print >> sys.stderr, 'Log follows:'
            with open(log.name) as log_file:
                print >> sys.stderr, '    | %s ' % '    | '.join(log_file)
        sys.exit(1)

    # Let plugins post process
    for indexer in indexers:
        indexer.post_process(tree, conn)


def finalize_database(conn):
    """Finalize the database."""
    print "Finalize database:"

    print " - Building database statistics for query optimization"
    conn.execute("ANALYZE");

    print " - Running integrity check"
    isOkay = None
    for row in conn.execute("PRAGMA integrity_check"):
        if row[0] == "ok" and isOkay is None:
            isOkay = True
        else:
            if isOkay is not False:
                print >> sys.stderr, "Database integerity check failed"
            isOkay = False
            print >> sys.stderr, "  | %s" % row[0]
    if not isOkay:
        sys.exit(1)

    conn.commit()


def build_sections(tree, conn, path, text, htmlifiers):
    """ Build navigation sections for template """
    # Chain links from different htmlifiers
    links = chain(*(htmlifier.links() for htmlifier in htmlifiers))
    # Sort by importance (resolve tries by section name)
    links = sorted(links, key = lambda section: (section[0], section[1]))
    # Return list of section and items (without importance)
    return [(section, list(items)) for importance, section, items in links]


def _sliced_range_bounds(a, b, slice_size):
    """Divide ``range(a, b)`` into slices of size ``slice_size``, and
    return the min and max values of each slice."""
    this_min = a
    while this_min == a or this_max < b:
        this_max = min(b, this_min + slice_size - 1)
        yield this_min, this_max
        this_min = this_max + 1


def run_html_workers(tree, config, max_file_id):
    """Farm out the building of HTML to a pool of processes."""

    print ' - Initializing worker pool'

    with ProcessPoolExecutor(max_workers=int(tree.config.nb_jobs)) as pool:
        print ' - Enqueuing jobs'
        futures = [pool.submit(_build_html_for_file_ids, tree, start, end) for
                   (start, end) in _sliced_range_bounds(1, max_file_id, 500)]
        print ' - Waiting for workers to complete'
        for num_done, future in enumerate(as_completed(futures), 1):
            print '%s of %s HTML workers done.' % (num_done, len(futures))
            result = future.result()
            if result:
                formatted_tb, type, value, id, path = result
                print 'A worker failed while htmlifying %s, id=%s:' % (path, id)
                print formatted_tb
                # Abort everything if anything fails:
                raise type, value  # exits with non-zero


def _build_html_for_file_ids(tree, start, end):
    """Write HTML files for file IDs from ``start`` to ``end``. Return None if
    all goes well, a tuple of (stringified exception, exc type, exc value, file
    ID, file path) if something goes wrong while htmlifying a file.

    This is the top-level function of an HTML worker process. Log progress to a
    file named "build-html-<start>-<end>.log".

    """
    path = '(no file yet)'
    id = -1
    try:
        # We might as well have this write its log directly rather than returning
        # them to the master process, since it's already writing the built HTML
        # directly, since that probably yields better parallelism.

        conn = connect_db(tree.target_folder)
        # TODO: Replace this ad hoc logging with the logging module (or something
        # more humane) so we can get some automatic timestamps. If we get
        # timestamps spit out in the parent process, we don't need any of the
        # timing or counting code here.
        with open_log(tree, 'build-html-%s-%s.log' % (start, end)) as log:
            # Load htmlifier plugins:
            plugins = load_htmlifiers(tree)
            for plugin in plugins:
                plugin.load(tree, conn)

            start_time = datetime.now()

            # Fetch and htmlify each document:
            for num_files, (id, path, icon, text) in enumerate(
                    conn.execute("""
                                 SELECT files.id, path, icon, trg_index.text
                                 FROM trg_index, files
                                 WHERE trg_index.id = files.id
                                 AND trg_index.id >= ?
                                 AND trg_index.id <= ?
                                 """,
                                 [start, end]),
                    1):
                dst_path = os.path.join(tree.target_folder, path + '.html')
                log.write('Starting %s.\n' % path)
                htmlify(tree, conn, icon, path, text, dst_path, plugins)

            conn.commit()
            conn.close()

            # Write time information:
            time = datetime.now() - start_time
            log.write('Finished %s files in %s.\n' % (num_files, time))
    except Exception as exc:
        type, value, traceback = exc_info()
        return format_exc(), type, value, id, path


def htmlify(tree, conn, icon, path, text, dst_path, plugins):
    """ Build HTML for path, text save it to dst_path """
    # Create htmlifiers for this source
    htmlifiers = []
    for plugin in plugins:
        htmlifier = plugin.htmlify(path, text)
        if htmlifier:
            htmlifiers.append(htmlifier)
    # Load template
    env = load_template_env(tree.config.temp_folder,
                            tree.config.dxrroot)

    arguments = {
        # Set common template variables
        'wwwroot': tree.config.wwwroot,
        'tree': tree.name,
        'tree_tuples': [(t.name,
                         browse_url(t.name, tree.config.wwwroot, path),
                         t.description)
                        for t in tree.config.sorted_tree_order],
        'generated_date': tree.config.generated_date,
        'filters': filter_menu_items(tree.config.filter_language),

        # Set file template variables
        'paths_and_names': linked_pathname(path, tree.name),
        'icon': icon,
        'path': path,
        'name': os.path.basename(path),

        # Someday, it would be great to stream this and not concretize the
        # whole thing in RAM. The template will have to quit looping through
        # the whole thing 3 times.
        'lines': list(lines_and_annotations(build_lines(text, htmlifiers,
                                                        tree.source_encoding),
                                            htmlifiers)),

        'sections': build_sections(tree, conn, path, text, htmlifiers)
    }

    _fill_and_write_template(env, 'file.html', dst_path, arguments)


class Line(object):
    """Representation of a line's beginning and ending as the contents of a tag

    Exists to motivate the balancing machinery to close all the tags at the end
    of every line (and reopen any afterward that span lines).

    """
    sort_order = 0  # Sort Lines outermost.
    def __repr__(self):
        return 'Line()'

LINE = Line()


class TagWriter(object):
    """A thing that hangs onto a tag's payload (like the class of a span) and
    knows how to write its opening and closing tags"""

    def __init__(self, payload):
        self.payload = payload

    # __repr__ comes in handy for debugging.
    def __repr__(self):
        return '%s("%s")' % (self.__class__.__name__, self.payload)


class Region(TagWriter):
    """Thing to open and close <span> tags"""
    sort_order = 2  # Sort Regions innermost, as it doesn't matter if we split
                    # them.

    def opener(self):
        return u'<span class="%s">' % cgi.escape(self.payload, True)

    def closer(self):
        return u'</span>'


class Ref(TagWriter):
    """Thing to open and close <a> tags"""
    sort_order = 1

    def opener(self):
        menu, qualname, value = self.payload
        menu = cgi.escape(json.dumps(menu), True)
        css_class = ''
        if qualname:
            css_class = ' class=\"tok' + str(hash(qualname)) +'\"'
        title = ''
        if value:
            title = ' title="' + cgi.escape(value, True) + '"'
        return u'<a data-menu="%s"%s%s>' % (menu, css_class, title)

    def closer(self):
        return u'</a>'


def html_lines(tags, slicer):
    """Render tags to HTML, and interleave them with the text they decorate.

    :arg tags: An iterable of ordered, non-overlapping, non-empty tag
        boundaries with Line endpoints at (and outermost at) the index of the
        end of each line.
    :arg slicer: A callable taking the args (start, end), returning a Unicode
        slice of the source code we're decorating. ``start`` and ``end`` are
        Python-style slice args.

    """
    up_to = 0
    segments = []

    for point, is_start, payload in tags:
        segments.append(cgi.escape(slicer(up_to, point).strip(u'\r\n')))
        up_to = point
        if payload is LINE:
            if not is_start and segments:
                yield Markup(u''.join(segments))
                segments = []

        else:
            segments.append(payload.opener() if is_start else payload.closer())


def balanced_tags(tags):
    """Come up with a balanced series of tags which express the semantics of
    the given sorted interleaved ones.

    Return an iterable of (point, is_start, Region/Reg/Line) without any
    (pointless) zero-width tag spans. The output isn't necessarily optimal, but
    it's fast and not embarrassingly wasteful of space.

    """
    return without_empty_tags(balanced_tags_with_empties(tags))


def without_empty_tags(tags):
    """Filter zero-width tagged spans out of a sorted, balanced tag stream.

    Maintain tag order. Line break tags are considered self-closing.

    """
    buffer = []  # tags
    depth = 0

    for tag in tags:
        point, is_start, payload = tag

        if is_start:
            buffer.append(tag)
            depth += 1
        else:
            top_point, _, top_payload = buffer[-1]
            if top_payload is payload and top_point == point:
                # It's a closer, and it matches the last thing in buffer and, it
                # and that open tag form a zero-width span. Cancel the last thing
                # in buffer.
                buffer.pop()
            else:
                # It's an end tag that actually encloses some stuff.
                buffer.append(tag)
            depth -= 1

            # If we have a balanced set of non-zero-width tags, emit them:
            if not depth:
                for b in buffer:
                    yield b
                del buffer[:]


def balanced_tags_with_empties(tags):
    """Come up with a balanced series of tags which express the semantics of
    the given sorted interleaved ones.

    Return an iterable of (point, is_start, Region/Reg/Line), possibly
    including some zero-width tag spans. Each line is enclosed within Line tags.

    :arg tags: An iterable of (offset, is_start, payload) tuples, with one
        closer for each opener but possibly interleaved. There is one tag for
        each line break, with a payload of LINE and an is_start of False. Tags
        are ordered with closers first, then line breaks, then openers.

    """
    def close(to=None):
        """Return an iterable of closers for open tags up to (but not
        including) the one with the payload ``to``."""
        # Loop until empty (if we're not going "to" anything in particular) or
        # until the corresponding opener is at the top of the stack. We check
        # that "to is None" just to surface any stack-tracking bugs that would
        # otherwise cause opens to empty too soon.
        while opens if to is None else opens[-1] is not to:
            intermediate_payload = opens.pop()
            yield point, False, intermediate_payload
            closes.append(intermediate_payload)

    def reopen():
        """Yield open tags for all temporarily closed ones."""
        while closes:
            intermediate_payload = closes.pop()
            yield point, True, intermediate_payload
            opens.append(intermediate_payload)

    opens = []  # payloads of tags which are currently open
    closes = []  # payloads of tags which we've had to temporarily close so we could close an overlapping tag
    point = 0

    yield 0, True, LINE
    for point, is_start, payload in tags:
        if is_start:
            yield point, is_start, payload
            opens.append(payload)
        elif payload is LINE:
            # Close all open tags before a line break (since each line is
            # wrapped in its own <code> tag pair), and reopen them afterward.
            for t in close():  # I really miss "yield from".
                yield t

            # Since preserving self-closing linebreaks would throw off
            # without_empty_tags(), we convert to explicit closers here. We
            # surround each line with them because empty balanced ones would
            # get filtered out.
            yield point, False, LINE
            yield point, True, LINE

            for t in reopen():
                yield t
        else:
            # Temporarily close whatever's been opened between the start tag of
            # the thing we're trying to close and here:
            for t in close(to=payload):
                yield t

            # Close the current tag:
            yield point, False, payload
            opens.pop()

            # Reopen the temporarily closed ones:
            for t in reopen():
                yield t
    yield point, False, LINE


def tag_boundaries(htmlifiers):
    """Return a sequence of (offset, is_start, Region/Ref/Line) tuples.

    Basically, split the atomic tags that come out of plugins into separate
    start and end points, which can then be thrown together in a bag and sorted
    as the first step in the tag-balancing process.

    Like in Python slice notation, the offset of a tag refers to the index of
    the source code char it comes before.

    """
    for h in htmlifiers:
        for intervals, cls in [(h.regions(), Region), (h.refs(), Ref)]:
            for start, end, data in intervals:
                tag = cls(data)
                # Filter out zero-length spans which don't do any good and
                # which can cause starts to sort after ends, crashing the tag
                # balancer. Incidentally filter out spans where start tags come
                # after end tags, though that should never happen.
                #
                # Also filter out None starts and ends. I don't know where they
                # come from. That shouldn't happen and should be fixed in the
                # plugins.
                if start is not None and end is not None and start < end:
                    yield start, True, tag
                    yield end, False, tag


def line_boundaries(text):
    """Return a tag for the end of each line in a string.

    :arg text: A UTF-8-encoded string

    Endpoints and start points are coincident: right after a (universal)
    newline.

    """
    up_to = 0
    for line in text.splitlines(True):
        up_to += len(line)
        yield up_to, False, LINE


def non_overlapping_refs(tags):
    """Yield a False for each Ref in ``tags`` that overlaps a subsequent one,
    a True for the rest.

    Assumes the incoming tags, while not necessarily well balanced, have the
    start tag come before the end tag, if both are present. (Lines are weird.)

    """
    blacklist = set()
    open_ref = None
    for point, is_start, payload in tags:
        if isinstance(payload, Ref):
            if payload in blacklist:  # It's the evil close tag of a misnested tag.
                blacklist.remove(payload)
                yield False
            elif open_ref is None:  # and is_start: (should always be true if input is sane)
                assert is_start
                open_ref = payload
                yield True
            elif open_ref is payload:  # it's the closer
                open_ref = None
                yield True
            else:  # It's an evil open tag of a misnested tag.
                warn('htmlifier plugins requested overlapping <a> tags. Fix the plugins.')
                blacklist.add(payload)
                yield False
        else:
            yield True


def remove_overlapping_refs(tags):
    """For any series of <a> tags that overlap each other, filter out all but
    the first.

    There's no decent way to represent that sort of thing in the UI, so we
    don't support it.

    :arg tags: A list of (point, is_start, payload) tuples, sorted by point.
        The tags do not need to be properly balanced.

    """
    # Reuse the list so we don't use any more memory.
    i = None
    for i, tag in enumerate(compress(tags, non_overlapping_refs(tags))):
        tags[i] = tag
    if i is not None:
        del tags[i + 1:]


def nesting_order((point, is_start, payload)):
    """Return a sorting key that places coincident Line boundaries outermost,
    then Ref boundaries, and finally Region boundaries.

    The Line bit saves some empty-tag elimination. The Ref bit saves splitting
    an <a> tag (and the attendant weird UI) for the following case::

        Ref    ____________  # The Ref should go on the outside.
        Region _____

    Other scenarios::

        Reg _______________        # Would be nice if Reg ended before Ref
        Ref      ________________  # started. We'll see about this later.

        Reg _____________________  # Works either way
        Ref _______

        Reg _____________________
        Ref               _______  # This should be fine.

        Reg         _____________  # This should be fine as well.
        Ref ____________

        Reg _____
        Ref _____  # This is fine either way.

    Also, endpoints sort before coincident start points to save work for the
    tag balancer.

    """
    return point, is_start, (payload.sort_order if is_start else
                             -payload.sort_order)


def build_lines(text, htmlifiers, encoding='utf-8'):
    """Yield lines of Markup, with decorations from the htmlifier plugins
    applied.

    :arg text: UTF-8-encoded string. (In practice, this is not true if the
        input file wasn't UTF-8. We should make it true.)

    """
    decoder = getdecoder(encoding)
    def decoded_slice(start, end):
        return decoder(text[start:end], errors='replace')[0]

    # For now, we make the same assumption the old build_lines() implementation
    # did, just so we can ship: plugins return byte offsets, not Unicode char
    # offsets. However, I think only the clang plugin returns byte offsets. I
    # bet Pygments returns char ones. We should homogenize one way or the
    # other.
    tags = list(tag_boundaries(htmlifiers))  # start and endpoints of intervals
    tags.extend(line_boundaries(text))
    tags.sort(key=nesting_order)  # Balanced_tags undoes this, but we tolerate
                                  # that in html_lines().
    remove_overlapping_refs(tags)
    return html_lines(balanced_tags(tags), decoded_slice)


def lines_and_annotations(lines, htmlifiers):
    """Collect all the annotations for each line into a list, and yield a tuple
    of (line of HTML, annotations list) for each line.

    :arg lines: An iterable of Markup objects, each representing a line of
        HTMLified source code

    """
    def non_sparse_annotations(annotations):
        """De-sparsify the annotations iterable so we can just zip it together
        with the HTML lines.

        Return an iterable of annotations iterables, one for each line.

        """
        next_unannotated_line = 0
        for line, annotations in groupby(annotations, itemgetter(0)):
            for next_unannotated_line in xrange(next_unannotated_line,
                                                line - 1):
                yield []
            yield [data for line_num, data in annotations]
            next_unannotated_line = line
    return izip_longest(lines,
                        non_sparse_annotations(merge(*[h.annotations() for h in
                                                       htmlifiers])),
                        fillvalue=[])

########NEW FILE########
__FILENAME__ = config
from ConfigParser import ConfigParser
from datetime import datetime
from ordereddict import OrderedDict
from operator import attrgetter
import os
from os.path import isdir
import sys

import dxr


# Please keep these config objects as simple as possible and in sync with
# docs/source/configuration.rst. I'm well aware that this is not the most compact way
# of writing things, but it sure is doomed to fail when user forgets an important
# key. It's also fairly easy to extract default values, and config keys from
# this code, so enjoy.

class Config(object):
    """ Configuration for DXR """
    def __init__(self, configfile, **override):
        # Create parser with sane defaults
        parser = ConfigParser({
            'dxrroot':          os.path.dirname(dxr.__file__),
            'plugin_folder':    "%(dxrroot)s/plugins",
            'nb_jobs':          "1",
            'temp_folder':      "/tmp/dxr-temp",
            'log_folder':       "%(temp_folder)s/logs",
            'wwwroot':          "/",
            'enabled_plugins':  "*",
            'disabled_plugins': " ",
            'directory_index':  ".dxr-directory-index.html",
            'generated_date':   datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S +0000"),
            'disable_workers':  "",
            'skip_stages':      "",
            'default_tree':     "",
            'filter_language':  "C"
        }, dict_type=OrderedDict)
        parser.read(configfile)

        # Set config values
        self.dxrroot          = parser.get('DXR', 'dxrroot',          False, override)
        self.plugin_folder    = parser.get('DXR', 'plugin_folder',    False, override)
        self.nb_jobs          = parser.get('DXR', 'nb_jobs',          False, override)
        self.temp_folder      = parser.get('DXR', 'temp_folder',      False, override)
        self.target_folder    = parser.get('DXR', 'target_folder',    False, override)
        self.log_folder       = parser.get('DXR', 'log_folder',       False, override)
        self.wwwroot          = parser.get('DXR', 'wwwroot',          False, override)
        self.enabled_plugins  = parser.get('DXR', 'enabled_plugins',  False, override)
        self.disabled_plugins = parser.get('DXR', 'disabled_plugins', False, override)
        self.directory_index  = parser.get('DXR', 'directory_index',  False, override)
        self.generated_date   = parser.get('DXR', 'generated_date',   False, override)
        self.disable_workers  = parser.get('DXR', 'disable_workers',  False, override)
        self.skip_stages      = parser.get('DXR', 'skip_stages',      False, override)
        self.default_tree     = parser.get('DXR', 'default_tree',     False, override)
        self.filter_language  = parser.get('DXR', 'filter_language',  False, override)
        # Set configfile
        self.configfile       = configfile
        self.trees            = []

        # Read all plugin_ keys
        for key, value in parser.items('DXR'):
            if key.startswith('plugin_'):
                setattr(self, key, value)

        # Render all paths absolute
        self.dxrroot          = os.path.abspath(self.dxrroot)
        self.plugin_folder    = os.path.abspath(self.plugin_folder)
        self.temp_folder      = os.path.abspath(self.temp_folder)
        self.log_folder       = os.path.abspath(self.log_folder)
        self.target_folder    = os.path.abspath(self.target_folder)

        # Make sure wwwroot doesn't end in /
        if self.wwwroot[-1] == '/':
            self.wwwroot = self.wwwroot[:-1]

        # Convert disabled plugins to a list
        if self.disabled_plugins == "*":
            self.disabled_plugins = os.listdir(self.plugin_folder)
        else:
            self.disabled_plugins = self.disabled_plugins.split()

        # Convert skipped stages to a list
        self.skip_stages = self.skip_stages.split()

        # Convert enabled plugins to a list
        if self.enabled_plugins == "*":
            self.enabled_plugins = [
                p for p in os.listdir(self.plugin_folder) if
                isdir(os.path.join(self.plugin_folder, p)) and
                p not in self.disabled_plugins]
        else:
            self.enabled_plugins = self.enabled_plugins.split()

        # Test for conflicting plugins settings
        conflicts = [p for p in self.disabled_plugins if p in self.enabled_plugins]
        if conflicts:
            msg = "Plugin: '%s' is both enabled and disabled"
            for p in conflicts:
                print >> sys.stderr, msg % p
            sys.exit(1)

        # Load trees
        for tree in parser.sections():
            if tree != 'DXR':
                self.trees.append(TreeConfig(self, self.configfile, tree))

        # Trees in alphabetical order for Switch Tree menu:
        self.sorted_tree_order = sorted(self.trees, key=attrgetter('name'))

        # Make sure that default_tree is defined
        if not self.default_tree:
            self.default_tree = self.sorted_tree_order[0].name



class TreeConfig(object):
    """ Tree configuration for DXR """
    def __init__(self, config, configfile, name):
        # Create parser with sane defaults
        parser = ConfigParser({
            'enabled_plugins':  "*",
            'disabled_plugins': "",
            'temp_folder':      os.path.join(config.temp_folder, name),
            'log_folder':       os.path.join(config.log_folder, name),
            'ignore_patterns':  ".hg .git CVS .svn .bzr .deps .libs",
            'build_command':    "make -j $jobs",
            'source_encoding':  'utf-8',
            'description':  ''
        })
        parser.read(configfile)

        # Set config values
        self.enabled_plugins  = parser.get(name, 'enabled_plugins')
        self.disabled_plugins = parser.get(name, 'disabled_plugins')
        self.temp_folder      = parser.get(name, 'temp_folder')
        self.log_folder       = parser.get(name, 'log_folder')
        self.object_folder    = parser.get(name, 'object_folder')
        self.source_folder    = parser.get(name, 'source_folder')
        self.build_command    = parser.get(name, 'build_command')
        self.ignore_patterns  = parser.get(name, 'ignore_patterns')
        self.source_encoding  = parser.get(name, 'source_encoding')
        self.description      = parser.get(name, 'description')

        # You cannot redefine the target folder!
        self.target_folder    = os.path.join(config.target_folder, 'trees', name)
        # Set config file and DXR config object reference
        self.configfile       = configfile
        self.config           = config
        self.name             = name

        # Read all plugin_ keys
        for key, value in parser.items(name):
            if key.startswith('plugin_'):
                setattr(self, key, value)

        # Convert ignore patterns to list
        self.ignore_patterns  = self.ignore_patterns.split()
        self.ignore_paths     = filter(lambda p: p.startswith("/"), self.ignore_patterns)
        self.ignore_patterns  = filter(lambda p: not p.startswith("/"), self.ignore_patterns)

        # Render all path absolute
        self.temp_folder      = os.path.abspath(self.temp_folder)
        self.log_folder       = os.path.abspath(self.log_folder)
        self.object_folder    = os.path.abspath(self.object_folder)
        self.source_folder    = os.path.abspath(self.source_folder)

        # Convert disabled plugins to a list
        if self.disabled_plugins == "*":
            self.disabled_plugins = config.enabled_plugins
        else:
            self.disabled_plugins = self.disabled_plugins.split()
            for p in config.disabled_plugins:
                if p not in self.disabled_plugins:
                    self.disabled_plugins.append(p)

        # Convert enabled plugins to a list
        if self.enabled_plugins == "*":
            self.enabled_plugins = [p for p in config.enabled_plugins
                                    if p not in self.disabled_plugins]
        else:
            self.enabled_plugins = self.enabled_plugins.split()

        # Test for conflicting plugins settings
        conflicts = [p for p in self.disabled_plugins if p in self.enabled_plugins]
        if conflicts:
            msg = "Plugin: '%s' is both enabled and disabled in '%s'"
            for p in conflicts:
                print >> sys.stderr, msg % (p, name)
            sys.exit(1)

        # Warn if $jobs isn't used...
        if "$jobs" not in self.build_command:
            msg = "Warning: $jobs is not used in build_command for '%s'"
            print >> sys.stderr, msg % name

########NEW FILE########
__FILENAME__ = languages
import dxr.schema


# The following schema is the common global schema, so no matter which plugins
# are used, this schema will always be present. Most tables have a language
# column which indicates the source language that the type is written in.
language_schema = dxr.schema.Schema({
    # Scope definitions: a scope is anything that is both interesting (i.e., not
    # a namespace) and can contain other objects. The IDs for this scope should be
    # IDs in other tables as well; the table its in can disambiguate which type of
    # scope you're looking at.
    "files" : [
        ("id", "INTEGER", False),
        ("path", "VARCHAR(1024)", True),
        ("icon", "VARCHAR(64)", True),
        ("encoding", "VARCHAR(16)", False),
        ("_key", "id"),
        ("_index", "path"),               # TODO: Make this a unique index
    ],
    "scopes": [
        ("id", "INTEGER", False),         # An ID for this scope
        ("name", "VARCHAR(256)", True),   # Name of the scope
        ("language", "_language", False), # The language of the scope
        ("_location", True),
        ("_key", "id")
    ],
    # Type definitions: anything that defines a type per the relevant specs.
    "types": [
        ("id", "INTEGER", False),            # Unique ID for the type
        ("scopeid", "INTEGER", True),        # Scope this type is defined in
        ("name", "VARCHAR(256)", False),     # Simple name of the type
        ("qualname", "VARCHAR(256)", False), # Fully-qualified name of the type
        ("kind", "VARCHAR(32)", True),       # Kind of type (e.g., class, union, struct, enum)
        ("language", "_language", True),     # Language of the type
        ("extent_start", "INTEGER", True),
        ("extent_end", "INTEGER", True),
        ("_location", True),
        ("_key", "id"),
        ("_fkey", "scopeid", "scopes", "id"),
        ("_index", "qualname"),
    ],
    # Inheritance relations: note that we store the full transitive closure in
    # this table, so if A extends B and B extends C, we'd have (A, C) stored in
    # the table as well; this is necessary to make SQL queries work, since there's
    # no "transitive closure lookup expression".
    "impl": [
        ("tbase", "INTEGER", False),      # tid of base type
        ("tderived", "INTEGER", False),   # tid of derived type
        ("inhtype", "VARCHAR(32)", True), # Type of inheritance; NULL is indirect
        ("_key", "tbase", "tderived")
    ],
    # Functions: functions, methods, constructors, operator overloads, etc.
    "functions": [
        ("id", "INTEGER", False),            # Function ID (also in scopes)
        ("scopeid", "INTEGER", True),        # Scope defined in
        ("name", "VARCHAR(256)", False),     # Short name (no args)
        ("qualname", "VARCHAR(512)", False), # Fully qualified name, excluding args
        ("args", "VARCHAR(256)", False),     # Argument string, including parens
        ("type", "VARCHAR(256)", False),     # Full return type, as a string
        ("modifiers", "VARCHAR(256)", True),  # Modifiers (e.g., private)
        ("language", "_language", True),     # Language of the function
        ("extent_start", "INTEGER", True),
        ("extent_end", "INTEGER", True),
        ("_location", True),
        ("_key", "id"),
        ("_fkey", "scopeid", "scopes", "id"),
        ("_index", "qualname"),
    ],
    # Variables: class, global, local, enum constants; they're all in here
    # Variables are of course not scopes, but for ease of use, they use IDs from
    # the same namespace, no scope will have the same ID as a variable and v.v.
    "variables": [
        ("id", "INTEGER", False),           # Variable ID
        ("scopeid", "INTEGER", True),       # Scope defined in
        ("name", "VARCHAR(256)", False),    # Short name
        ("qualname", "VARCHAR(256)", False),# Fully qualified name
        ("type", "VARCHAR(256)", True),     # Full type (including pointer stuff)
        ("modifiers", "VARCHAR(256)", True), # Modifiers for the declaration
        ("language", "_language", True),    # Language of the function
        ("value", "VARCHAR(32)", True),
        ("extent_start", "INTEGER", True),
        ("extent_end", "INTEGER", True),
        ("_location", True),
        ("_key", "id"),
        ("_fkey", "scopeid", "scopes", "id"),
        ("_index", "qualname"),
    ],
    "crosslang": [
        ("canonid", "INTEGER", False),
        ("otherid", "INTEGER", False),
        ("otherlanguage", "VARCHAR(32)", False),
        ("_key", "otherid")
    ],
})

########NEW FILE########
__FILENAME__ = mime
from os.path import splitext

# Current implementation is very simple, if utf-8 decoding works we declare it
# text, otherwise we say it's binary.
# To find an icon we file extension, ultimately we use libmagic and resolve
# mimetypes to icons.

def icon(path):
    root, ext = splitext(path)
    return "mimetypes/" + ext_map.get(ext[1:], "unknown")


def is_text(path, data):
    # Simple stupid test that apparently works rather well :)
    return '\0' not in data


# File extension known as this point
ext_map = {
    "html":       'html',
    "xhtml":      'html',
    "htm":        'html',
    "js":         'js',
    "h":          'h',
    "hpp":        'h',
    "cpp":        'cpp',
    "cc":         'cpp',
    "cxx":        'cpp',
    "c":          'c',
    "xul":        'ui',
    "svg":        'svg',
    "in":         'build',
    "idl":        'conf',
    "java":       'java',
    "xml":        'xml',
    "py":         'py',
    "css":        'css',
    "mk":         'build',
    "txt":        'txt',
    "sh":         'sh',
    "ini":        'conf',
    "properties": 'conf',
    "dtd":        'xml',
    "patch":      'diff',
    "asm":        'asm',
    "jsm":        'js',
    "cfg":        'conf',
    "m4":         'conf',
    "webidl":     'conf',
    "vcproj":     'vs',
    "vcxproj":    'vs',
    "xsl":        'xml',
    "hxx":        'h',
    "sln":        'vs',
    "diff":       'diff',
    "cs":         'cs',
    "iso":        'iso',
    "php":        'php',
    "rb":         'rb',
    "ipdl":       'conf',
    "mm":         'mm',
    "tex":        'tex',
    "vsprops":    'vs'
}

########NEW FILE########
__FILENAME__ = htmlifier
import cgi
import re
import sys

import dxr.plugins


# Global variables
url       = None
name      = None
bug_finder = None


# Load global variables
def load(tree, conn):
    global url, name, bug_finder

    # Get bug tracker name
    if hasattr(tree, 'plugin_buglink_name'):
        name = tree.plugin_buglink_name
    else:
        print >> sys.stderr, 'buglink plugin needs plugin_buglink_name configuration key'
        sys.exit(1)

    # Get link
    # The plugin_buglink_bugzilla option behaves identically but is deprecated.
    url = getattr(tree, 'plugin_buglink_url',
                        getattr(tree, 'plugin_buglink_bugzilla', None))
    if url is None:
        print >> sys.stderr, 'buglink plugin needs plugin_buglink_url configuration key'
        sys.exit(1)

    # Get bug finder regex
    bug_finder = re.compile(getattr(tree,
                                    'plugin_buglink_regex',
                                    r'(?i)bug\s+#?([0-9]+)'))


class BugLinkHtmlifier(object):
    def __init__(self, text):
        self.text = text

    def refs(self):
        global name
        for m in bug_finder.finditer(self.text):
            bug = m.group(1)
            yield m.start(0), m.end(0), ([{
                'html': cgi.escape("Lookup #%s" % bug),
                'title': "Find this bug number at %s" % name,
                'href': url % bug,
                'icon': 'buglink'
            }], '', None)

    def regions(self):
        return []

    def annotations(self):
        return []

    def links(self):
        return []


def htmlify(path, text):
    return BugLinkHtmlifier(text)


__all__ = dxr.plugins.htmlifier_exports()

########NEW FILE########
__FILENAME__ = indexer
import dxr.plugins

# Nothing to do here, but we must implement indexer.py to explicitly declare
# that these functions are no-op. Otherwise DXR shall assume the file or the
# implementation is missing, and thus, something is badly wrong.

def pre_process(tree, environ):
    pass

def post_process(tree, conn):
    pass

__all__ = dxr.plugins.indexer_exports()

########NEW FILE########
__FILENAME__ = htmlifier
import dxr.plugins
import os, sys
import fnmatch
import urllib, re

from dxr.utils import search_url


class ClangHtmlifier(object):
    def __init__(self, tree, conn, path, text, file_id):
        self.tree    = tree
        self.conn    = conn
        self.path    = path
        self.text    = text
        self.file_id = file_id

    def regions(self):
        return []

    def refs(self):
        """ Generate reference menus """
        # We'll need this argument for all queries here
        args = (self.file_id,)

        # Extents for functions defined here
        sql = """
            SELECT extent_start, extent_end, qualname,
                EXISTS (SELECT targetid FROM targets WHERE funcid=functions.id) AS isvirtual
                FROM functions
              WHERE file_id = ?
        """
        for start, end, qualname, isvirtual in self.conn.execute(sql, args):
            yield start, end, (self.function_menu(qualname, isvirtual), qualname, None)

        # Extents for functions declared here
        sql = """
            SELECT decldef.extent_start,
                          decldef.extent_end,
                          functions.qualname,
                          (SELECT path FROM files WHERE files.id = functions.file_id),
                          functions.file_line,
                          EXISTS (SELECT targetid FROM targets WHERE funcid=functions.id) AS isvirtual
                FROM function_decldef AS decldef, functions
              WHERE decldef.defid = functions.id
                  AND decldef.file_id = ?
        """
        for start, end, qualname, path, line, isvirtual in self.conn.execute(sql, args):
            menu = self.function_menu(qualname, isvirtual)
            self.add_jump_definition(menu, path, line)
            yield start, end, (menu, qualname, None)

        # Extents for variables defined here
        sql = """
            SELECT extent_start, extent_end, qualname, value
                FROM variables
              WHERE file_id = ?
        """
        for start, end, qualname, value in self.conn.execute(sql, args):
            yield start, end, (self.variable_menu(qualname), qualname, value)

        # Extents for variables declared here
        sql = """
            SELECT decldef.extent_start,
                          decldef.extent_end,
                          variables.qualname,
                          variables.value,
                          (SELECT path FROM files WHERE files.id = variables.file_id),
                          variables.file_line
                FROM variable_decldef AS decldef, variables
              WHERE decldef.defid = variables.id
                  AND decldef.file_id = ?
        """
        for start, end, qualname, value, path, line in self.conn.execute(sql, args):
            menu = self.variable_menu(qualname)
            self.add_jump_definition(menu, path, line)
            yield start, end, (menu, qualname, value)

        # Extents for types defined here
        sql = """
            SELECT extent_start, extent_end, qualname, kind
                FROM types
              WHERE file_id = ?
        """
        for start, end, qualname, kind in self.conn.execute(sql, args):
            yield start, end, (self.type_menu(qualname, kind), qualname, None)

        # Extents for types declared here
        sql = """
            SELECT decldef.extent_start,
                          decldef.extent_end,
                          types.qualname,
                          types.kind,
                          (SELECT path FROM files WHERE files.id = types.file_id),
                          types.file_line
                FROM type_decldef AS decldef, types
              WHERE decldef.defid = types.id
                  AND decldef.file_id = ?
        """
        for start, end, qualname, kind, path, line in self.conn.execute(sql, args):
            menu = self.type_menu(qualname, kind)
            self.add_jump_definition(menu, path, line)
            yield start, end, (menu, qualname, None)

        # Extents for typedefs defined here
        sql = """
            SELECT extent_start, extent_end, qualname
                FROM typedefs
              WHERE file_id = ?
        """
        for start, end, qualname in self.conn.execute(sql, args):
            yield start, end, (self.typedef_menu(qualname), qualname, None)

        # Extents for namespaces defined here
        sql = """
            SELECT extent_start, extent_end, qualname
                FROM namespaces
              WHERE file_id = ?
        """
        for start, end, qualname in self.conn.execute(sql, args):
            yield start, end, (self.namespace_menu(qualname), qualname, None)

        # Extents for namespace aliases defined here
        sql = """
            SELECT extent_start, extent_end, qualname
                FROM namespace_aliases
              WHERE file_id = ?
        """
        for start, end, qualname in self.conn.execute(sql, args):
            yield start, end, (self.namespace_alias_menu(qualname), qualname, None)

        # Extents for macros defined here
        sql = """
            SELECT extent_start, extent_end, name, text
                FROM macros
              WHERE file_id = ?
        """
        for start, end, name, value in self.conn.execute(sql, args):
            yield start, end, (self.macro_menu(name), name, value)

        # Add references to types
        sql = """
            SELECT refs.extent_start, refs.extent_end,
                          types.qualname,
                          types.kind,
                          (SELECT path FROM files WHERE files.id = types.file_id),
                          types.file_line
                FROM types, type_refs AS refs
              WHERE types.id = refs.refid AND refs.file_id = ?
        """
        for start, end, qualname, kind, path, line in self.conn.execute(sql, args):
            menu = self.type_menu(qualname, kind)
            self.add_jump_definition(menu, path, line)
            yield start, end, (menu, qualname, None)

        # Add references to typedefs
        sql = """
            SELECT refs.extent_start, refs.extent_end,
                          typedefs.qualname,
                          (SELECT path FROM files WHERE files.id = typedefs.file_id),
                          typedefs.file_line
                FROM typedefs, typedef_refs AS refs
              WHERE typedefs.id = refs.refid AND refs.file_id = ?
        """
        for start, end, qualname, path, line in self.conn.execute(sql, args):
            menu = self.typedef_menu(qualname)
            self.add_jump_definition(menu, path, line)
            yield start, end, (menu, qualname, None)

        # Add references to functions
        sql = """
            SELECT refs.extent_start, refs.extent_end,
                          functions.qualname,
                          (SELECT path FROM files WHERE files.id = functions.file_id),
                          functions.file_line,
                          EXISTS (SELECT targetid FROM targets WHERE funcid=functions.id) AS isvirtual
                FROM functions, function_refs AS refs
              WHERE functions.id = refs.refid AND refs.file_id = ?
        """
        for start, end, qualname, path, line, isvirtual in self.conn.execute(sql, args):
            menu = self.function_menu(qualname, isvirtual)
            self.add_jump_definition(menu, path, line)
            yield start, end, (menu, qualname, None)

        # Add references to variables
        sql = """
            SELECT refs.extent_start, refs.extent_end,
                          variables.qualname,
                          variables.value,
                          (SELECT path FROM files WHERE files.id = variables.file_id),
                          variables.file_line
                FROM variables, variable_refs AS refs
              WHERE variables.id = refs.refid AND refs.file_id = ?
        """
        for start, end, qualname, value, path, line in self.conn.execute(sql, args):
            menu = self.variable_menu(qualname)
            self.add_jump_definition(menu, path, line)
            yield start, end, (menu, qualname, value)

        # Add references to namespaces
        sql = """
            SELECT refs.extent_start, refs.extent_end,
                          namespaces.qualname,
                          (SELECT path FROM files WHERE files.id = namespaces.file_id),
                          namespaces.file_line
                FROM namespaces, namespace_refs AS refs
              WHERE namespaces.id = refs.refid AND refs.file_id = ?
        """
        for start, end, qualname, path, line in self.conn.execute(sql, args):
            menu = self.namespace_menu(qualname)
            yield start, end, (menu, qualname, None)

        # Add references to namespace aliases
        sql = """
            SELECT refs.extent_start, refs.extent_end,
                          namespace_aliases.qualname,
                          (SELECT path FROM files WHERE files.id = namespace_aliases.file_id),
                          namespace_aliases.file_line
                FROM namespace_aliases, namespace_alias_refs AS refs
              WHERE namespace_aliases.id = refs.refid AND refs.file_id = ?
        """
        for start, end, qualname, path, line in self.conn.execute(sql, args):
            menu = self.namespace_alias_menu(qualname)
            self.add_jump_definition(menu, path, line)
            yield start, end, (menu, qualname, None)

        # Add references to macros
        sql = """
            SELECT refs.extent_start, refs.extent_end,
                          macros.name,
                          macros.text,
                          (SELECT path FROM files WHERE files.id = macros.file_id),
                          macros.file_line
                FROM macros, macro_refs AS refs
              WHERE macros.id = refs.refid AND refs.file_id = ?
        """
        for start, end, name, value, path, line in self.conn.execute(sql, args):
            menu = self.macro_menu(name)
            self.add_jump_definition(menu, path, line)
            yield start, end, (menu, name, value)

        # Link all the #includes in this file to the files they reference.
        for start, end, path in self.conn.execute(
                'SELECT extent_start, extent_end, path FROM includes '
                'INNER JOIN files ON files.id=includes.target_id '
                'WHERE includes.file_id = ?', args):
            yield start, end, ([{'html': 'Jump to file',
                                 'title': 'Jump to what is included here.',
                                 'href': self.tree.config.wwwroot + '/' +
                                         self.tree.name + '/source/' + path,
                                 'icon': 'jump'}], '', None)

    def search(self, query):
        """ Auxiliary function for getting the search url for query """
        return search_url(self.tree.config.wwwroot,
                          self.tree.name,
                          query)

    def quote(self, qualname):
        """ Wrap qualname in quotes if it contains spaces """
        if ' ' in qualname:
            qualname = '"' + qualname + '"'
        return qualname

    def add_jump_definition(self, menu, path, line):
        """ Add a jump to definition to the menu """
        # Definition url
        url = self.tree.config.wwwroot + '/' + self.tree.name + '/source/' + path
        url += "#%s" % line
        menu.insert(0, { 
            'html':   "Jump to definition",
            'title':  "Jump to the definition in '%s'" % os.path.basename(path),
            'href':   url,
            'icon':   'jump'
        })

    def type_menu(self, qualname, kind):
        """ Build menu for type """
        menu = []
        # Things we can do with qualname
        menu.append({
            'html':   "Find declarations",
            'title':  "Find declarations of this class",
            'href':   self.search("+type-decl:%s" % self.quote(qualname)),
            'icon':   'reference'  # FIXME?
        })
        if kind == 'class' or kind == 'struct':
            menu.append({
                'html':   "Find sub classes",
                'title':  "Find sub classes of this class",
                'href':   self.search("+derived:%s" % self.quote(qualname)),
                'icon':   'type'
            })
            menu.append({
                'html':   "Find base classes",
                'title':  "Find base classes of this class",
                'href':   self.search("+bases:%s" % self.quote(qualname)),
                'icon':   'type'
            })
        menu.append({
            'html':   "Find members",
            'title':  "Find members of this class",
            'href':   self.search("+member:%s" % self.quote(qualname)),
            'icon':   'members'
        })
        menu.append({
            'html':   "Find references",
            'title':  "Find references to this class",
            'href':   self.search("+type-ref:%s" % self.quote(qualname)),
            'icon':   'reference'
        })
        return menu


    def typedef_menu(self, qualname):
        """ Build menu for typedef """
        menu = []
        menu.append({
            'html':   "Find references",
            'title':  "Find references to this typedef",
            'href':   self.search("+type-ref:%s" % self.quote(qualname)),
            'icon':   'reference'
        })
        return menu


    def variable_menu(self, qualname):
        """ Build menu for a variable """
        menu = []
        menu.append({
            'html':   "Find declarations",
            'title':  "Find declarations of this variable",
            'href':   self.search("+var-decl:%s" % self.quote(qualname)),
            'icon':   'reference' # FIXME?
        })
        menu.append({
            'html':   "Find references",
            'title':  "Find reference to this variable",
            'href':   self.search("+var-ref:%s" % self.quote(qualname)),
            'icon':   'field'
        })
        # TODO Investigate whether assignments and usages is possible and useful?
        return menu


    def namespace_menu(self, qualname):
        """ Build menu for a namespace """
        menu = []
        menu.append({
            'html':   "Find definitions",
            'title':  "Find definitions of this namespace",
            'href':   self.search("+namespace:%s" % self.quote(qualname)),
            'icon':   'jump'
        })
        menu.append({
            'html':   "Find references",
            'title':  "Find references to this namespace",
            'href':   self.search("+namespace-ref:%s" % self.quote(qualname)),
            'icon':   'reference'
        })
        return menu


    def namespace_alias_menu(self, qualname):
        """ Build menu for a namespace """
        menu = []
        menu.append({
            'html':   "Find references",
            'title':  "Find references to this namespace alias",
            'href':   self.search("+namespace-alias-ref:%s" % self.quote(qualname)),
            'icon':   'reference'
        })
        return menu


    def macro_menu(self, name):
        menu = []
        # Things we can do with macros
        menu.append({
            'html':   "Find references",
            'title':  "Find references to macros with this name",
            'href':    self.search("+macro-ref:%s" % name),
            'icon':   'reference'
        })
        return menu


    def function_menu(self, qualname, isvirtual):
        """ Build menu for a function """
        menu = []
        # Things we can do with qualified name
        menu.append({
            'html':   "Find declarations",
            'title':  "Find declarations of this function",
            'href':   self.search("+function-decl:%s" % self.quote(qualname)),
            'icon':   'reference'  # FIXME?
        })
        menu.append({
            'html':   "Find callers",
            'title':  "Find functions that call this function",
            'href':   self.search("+callers:%s" % self.quote(qualname)),
            'icon':   'method'
        })
        menu.append({
            'html':   "Find callees",
            'title':  "Find functions that are called by this function",
            'href':   self.search("+called-by:%s" % self.quote(qualname)),
            'icon':   'method'
        })
        menu.append({
            'html':   "Find references",
            'title':  "Find references to this function",
            'href':   self.search("+function-ref:%s" % self.quote(qualname)),
            'icon':   'reference'
        })
        if isvirtual:
            menu.append({
                'html':   "Find overridden",
                'title':  "Find functions that this function overrides",
                'href':   self.search("+overridden:%s" % self.quote(qualname)),
                'icon':   'method'
            })
            menu.append({
                'html':   "Find overrides",
                'title':  "Find overrides of this function",
                'href':   self.search("+overrides:%s" % self.quote(qualname)),
                'icon':   'method'
            })
        return menu


    def annotations(self):
        icon = "background-image: url('%s/static/icons/warning.png');" % self.tree.config.wwwroot
        sql = "SELECT msg, opt, file_line FROM warnings WHERE file_id = ? ORDER BY file_line"
        for msg, opt, line in self.conn.execute(sql, (self.file_id,)):
            if opt:
                msg = msg + " [" + opt + "]"
            yield line, {
                'title': msg,
                'class': "note note-warning",
                'style': icon
            }

    def links(self):
        # For each type add a section with members
        sql = "SELECT name, id, file_line, kind FROM types WHERE file_id = ?"
        for name, tid, line, kind in self.conn.execute(sql, (self.file_id,)):
            if len(name) == 0: continue
            links = []
            links += list(self.member_functions(tid))
            links += list(self.member_variables(tid))

            # Sort them by line
            links = sorted(links, key = lambda link: link[1])

            # Make sure we have a sane limitation of kind
            if kind not in ('class', 'struct', 'enum', 'union'):
                print >> sys.stderr, "kind '%s' was replaced for 'type'!" % kind
                kind = 'type'

            # Add the outer type as the first link
            links.insert(0, (kind, name, "#%s" % line))

            # Now return the type
            yield (30, name, links)

        # Add all macros to the macro section
        links = []
        sql = "SELECT name, file_line FROM macros WHERE file_id = ?"
        for name, line in self.conn.execute(sql, (self.file_id,)):
            links.append(('macro', name, "#%s" % line))
        if links:
            yield (100, "Macros", links)

    def member_functions(self, tid):
        """ Fetch member functions given a type id """
        sql = """
            SELECT name, file_line
            FROM functions
            WHERE file_id = ? AND scopeid = ?
        """
        for name, line in self.conn.execute(sql, (self.file_id, tid)):
            # Skip nameless things
            if len(name) == 0: continue
            yield 'method', name, "#%s" % line

    def member_variables(self, tid):
        """ Fetch member variables given a type id """
        sql = """
            SELECT name, file_line
            FROM variables
            WHERE file_id = ? AND scopeid = ?
        """
        for name, line in self.conn.execute(sql, (self.file_id, tid)):
            # Skip nameless things
            if len(name) == 0: continue
            yield 'field', name, "#%s" % line


_tree = None
_conn = None
def load(tree, conn):
    global _tree, _conn
    _tree = tree
    _conn = conn


_patterns = ('*.c', '*.cc', '*.cpp', '*.cxx', '*.h', '*.hpp')
def htmlify(path, text):
    fname = os.path.basename(path)
    if any((fnmatch.fnmatchcase(fname, p) for p in _patterns)):
        # Get file_id, skip if not in database
        sql = "SELECT files.id FROM files WHERE path = ? LIMIT 1"
        row = _conn.execute(sql, (path,)).fetchone()
        if row:
            return ClangHtmlifier(_tree, _conn, path, text, row[0])
    return None


__all__ = dxr.plugins.htmlifier_exports()

########NEW FILE########
__FILENAME__ = indexer
import csv, cgi
import json
import dxr.plugins
import dxr.schema
import os, sys
import re, urllib
from dxr.languages import language_schema


PLUGIN_NAME   = 'clang'

__all__ = dxr.plugins.indexer_exports()


def pre_process(tree, env):
    # Setup environment variables for inspecting clang as runtime
    # We'll store all the havested metadata in the plugins temporary folder.
    temp_folder   = os.path.join(tree.temp_folder, 'plugins', PLUGIN_NAME)
    plugin_folder = os.path.join(tree.config.plugin_folder, PLUGIN_NAME)
    flags = [
        '-load', os.path.join(plugin_folder, 'libclang-index-plugin.so'),
        '-add-plugin', 'dxr-index',
        '-plugin-arg-dxr-index', tree.source_folder
    ]
    flags_str = ""
    for flag in flags:
        flags_str += ' -Xclang ' + flag
    env['CC']   = "clang %s"   % flags_str
    env['CXX']  = "clang++ %s" % flags_str
    env['DXR_CC'] = env['CC']
    env['DXR_CXX'] = env['CXX']
    env['DXR_CLANG_FLAGS'] = flags_str
    env['DXR_CXX_CLANG_OBJECT_FOLDER']  = tree.object_folder
    env['DXR_CXX_CLANG_TEMP_FOLDER']    = temp_folder


def post_process(tree, conn):
    print "cxx-clang post-processing:"
    print " - Adding tables"
    conn.executescript(schema.get_create_sql())

    print " - Processing files"
    temp_folder = os.path.join(tree.temp_folder, 'plugins', PLUGIN_NAME)
    for f in os.listdir(temp_folder):
        csv_path = os.path.join(temp_folder, f)
        dump_indexer_output(conn, csv_path)

    fixup_scope(conn)
    
    print " - Generating callgraph"
    generate_callgraph(conn)
    
    print " - Generating inheritance graph"
    generate_inheritance(conn)

    print " - Updating definitions"
    update_defids(conn)

    print " - Updating references"
    update_refs(conn)

    print " - Committing changes"
    conn.commit()



schema = dxr.schema.Schema({
    # Typedef information in the tables
    "typedefs": [
        ("id", "INTEGER", False),              # The typedef's id
        ("name", "VARCHAR(256)", False),       # Simple name of the typedef
        ("qualname", "VARCHAR(256)", False),   # Fully-qualified name of the typedef
        ("extent_start", "INTEGER", True),
        ("extent_end", "INTEGER", True),
        ("_location", True),
        ("_key", "id"),
        ("_index", "qualname"),
    ],
    # Namespaces
    "namespaces": [
        ("id", "INTEGER", False),              # The namespaces's id
        ("name", "VARCHAR(256)", False),       # Simple name of the namespace
        ("qualname", "VARCHAR(256)", False),   # Fully-qualified name of the namespace
        ("extent_start", "INTEGER", True),
        ("extent_end", "INTEGER", True),
        ("_location", True),
        ("_key", "id"),
        ("_index", "qualname"),
    ],
    # References to namespaces
    "namespace_refs": [
        ("refid", "INTEGER", True),      # ID of the namespace being referenced
        ("extent_start", "INTEGER", True),
        ("extent_end", "INTEGER", True),
        ("_location", True),
        ("_location", True, 'referenced'),
        ("_fkey", "refid", "namespaces", "id"),
        ("_index", "refid"),
    ],
    # Namespace aliases
    "namespace_aliases": [
        ("id", "INTEGER", False),              # The namespace alias's id
        ("name", "VARCHAR(256)", False),       # Simple name of the namespace alias
        ("qualname", "VARCHAR(256)", False),   # Fully-qualified name of the namespace alias
        ("extent_start", "INTEGER", True),
        ("extent_end", "INTEGER", True),
        ("_location", True),
        ("_key", "id"),
        ("_index", "qualname"),
    ],
    # References to namespace aliases
    "namespace_alias_refs": [
        ("refid", "INTEGER", True),      # ID of the namespace alias being referenced
        ("extent_start", "INTEGER", True),
        ("extent_end", "INTEGER", True),
        ("_location", True),
        ("_location", True, 'referenced'),
        ("_fkey", "refid", "namespace_aliases", "id"),
        ("_index", "refid"),
    ],
    # References to functions
    "function_refs": [
        ("refid", "INTEGER", True),      # ID of the function being referenced
        ("extent_start", "INTEGER", True),
        ("extent_end", "INTEGER", True),
        ("_location", True),
        ("_location", True, 'referenced'),
        ("_fkey", "refid", "functions", "id"),
        ("_index", "refid"),
    ],
    # References to macros
    "macro_refs": [
        ("refid", "INTEGER", True),      # ID of the macro being referenced
        ("extent_start", "INTEGER", True),
        ("extent_end", "INTEGER", True),
        ("_location", True),
        ("_location", True, 'referenced'),
        ("_fkey", "refid", "macros", "id"),
        ("_index", "refid"),
    ],
    # References to types
    "type_refs": [
        ("refid", "INTEGER", True),      # ID of the type being referenced
        ("extent_start", "INTEGER", True),
        ("extent_end", "INTEGER", True),
        ("_location", True),
        ("_location", True, 'referenced'),
        ("_fkey", "refid", "types", "id"),
        ("_index", "refid"),
    ],
    # References to typedefs
    "typedef_refs": [
        ("refid", "INTEGER", True),      # ID of the typedef being referenced
        ("extent_start", "INTEGER", True),
        ("extent_end", "INTEGER", True),
        ("_location", True),
        ("_location", True, 'referenced'),
        ("_fkey", "refid", "typedefs", "id"),
        ("_index", "refid"),
    ],
    # References to variables
    "variable_refs": [
        ("refid", "INTEGER", True),      # ID of the variable being referenced
        ("extent_start", "INTEGER", True),
        ("extent_end", "INTEGER", True),
        ("_location", True),
        ("_location", True, 'referenced'),
        ("_fkey", "refid", "variables", "id"),
        ("_index", "refid"),
    ],
    # Warnings found while compiling
    "warnings": [
        ("msg", "VARCHAR(256)", False), # Text of the warning
        ("opt", "VARCHAR(64)", True),   # option controlling this warning (-Wxxx)
        ("extent_start", "INTEGER", True),
        ("extent_end", "INTEGER", True),
        ("_location", True),
    ],
    # Declaration/definition mapping for functions
    "function_decldef": [
        ("defid", "INTEGER", True),    # ID of the definition instance
        ("_location", True),
        ("_location", True, 'definition'),
        # Extents of the declaration
        ("extent_start", "INTEGER", True),
        ("extent_end", "INTEGER", True),
        ("_fkey", "defid", "functions", "id"),
        ("_index", "defid"),
    ],
    # Declaration/definition mapping for types
    "type_decldef": [
        ("defid", "INTEGER", True),    # ID of the definition instance
        ("_location", True),
        ("_location", True, 'definition'),
        # Extents of the declaration
        ("extent_start", "INTEGER", True),
        ("extent_end", "INTEGER", True),
        ("_fkey", "defid", "types", "id"),
        ("_index", "defid"),
    ],
    # Declaration/definition mapping for variables
    "variable_decldef": [
        ("defid", "INTEGER", True),    # ID of the definition instance
        ("_location", True),
        ("_location", True, 'definition'),
        # Extents of the declaration
        ("extent_start", "INTEGER", True),
        ("extent_end", "INTEGER", True),
        ("_fkey", "defid", "variables", "id"),
        ("_index", "defid"),
    ],
    # Macros: this is a table of all of the macros we come across in the code.
    "macros": [
        ("id", "INTEGER", False),        # The macro id, for references
        ("name", "VARCHAR(256)", False), # The name of the macro
        ("args", "VARCHAR(256)", True),  # The args of the macro (if any)
        ("text", "TEXT", True),          # The macro contents
        ("extent_start", "INTEGER", True),
        ("extent_end", "INTEGER", True),
        ("_location", True),
        ("_key", "id"),
    ],
    # #include and #import directives
    # If we can't resolve the target to a file in the tree, we just omit the
    # row.
    "includes": [
        ("id", "INTEGER", False),  # surrogate key
        ("file_id", "INTEGER", False),  # file where the #include directive is
        ("extent_start", "INTEGER", False),
        ("extent_end", "INTEGER", False),
        ("target_id", "INTEGER", False),  # file pointed to by the #include
        ("_key", "id"),  # so it autoincrements
        ("_fkey", "file_id", "files", "id"),
        ("_fkey", "target_id", "files", "id"),
        ("_index", "file_id"),
    ],
    # The following two tables are combined to form the callgraph implementation.
    # In essence, the callgraph can be viewed as a kind of hypergraph, where the
    # edges go from functions to sets of functions and variables. For use in the
    # database, we are making some big assumptions: the targetid is going to be
    # either a function or variable (the direct thing we called); if the function
    # is virtual or the target is a variable, we use the targets table to identify
    # what the possible implementations could be.
    "callers": [
        ("callerid", "INTEGER", False), # The function in which the call occurs
        ("targetid", "INTEGER", False), # The target of the call
        ("_key", "callerid", "targetid"),
        ("_fkey", "callerid", "functions", "id")
    ],
    "targets": [
        ("targetid", "INTEGER", False), # The target of the call
        ("funcid", "INTEGER", False),   # One of the functions in the target set
        ("_key", "targetid", "funcid"),
        ("_fkey", "funcid", "functions", "id"),
        ("_index", "funcid"),
    ]
})


file_cache = {}
decl_master = {}
inheritance = {}
calls = {}
overrides = {}

def getFileID(conn, path):
    global file_cache

    file_id = file_cache.get(path, False)

    if file_id is not False:
        return file_id

    cur = conn.cursor()
    row = cur.execute("SELECT id FROM files where path=?", (path,)).fetchone()
    file_id = None
    if row:
        file_id = row[0]
    file_cache[path] = file_id
    return file_id

def splitLoc(conn, value):
    arr = value.split(':')
    return (getFileID(conn, arr[0]), int(arr[1]), int(arr[2]))

def fixupEntryPath(args, file_key, conn, prefix=None):
    value = args[file_key]
    loc = splitLoc(conn, value)

    if prefix is not None:
        prefix = prefix + "_"
    else:
        prefix = ''

    args[prefix + 'file_id'] = loc[0]
    args[prefix + 'file_line'] = loc[1]
    args[prefix + 'file_col'] = loc[2]
    return loc[0] is not None

def fixupExtent(args, extents_key='extent'):
    if extents_key not in args:
        return

    value = args[extents_key]
    arr = value.split(':')

    args['extent_start'] = int(arr[0])
    args['extent_end'] = int(arr[1])
    del args[extents_key]

def getScope(args, conn):
    row = conn.execute("SELECT id FROM scopes WHERE file_id=? AND file_line=? AND file_col=?",
                                          (args['file_id'], args['file_line'], args['file_col'])).fetchone()

    if row is not None:
        return row[0]

    return None

def addScope(args, conn, name, id):
    scope = {}
    scope['name'] = args[name]
    scope['id'] = args[id]
    scope['file_id'] = args['file_id']
    scope['file_line'] = args['file_line']
    scope['file_col'] = args['file_col']
    scope['language'] = 'native'

    stmt = language_schema.get_insert_sql('scopes', scope)
    conn.execute(stmt[0], stmt[1])

def handleScope(args, conn, canonicalize=False):
    scope = {}

    if 'scopename' not in args:
        return

    scope['name'] = args['scopename']
    scope['loc'] = args['scopeloc']
    scope['language'] = 'native'
    if not fixupEntryPath(scope, 'loc', conn):
        return None

    if canonicalize is True:
        decl = canonicalize_decl(scope['name'], scope['file_id'], scope['file_line'], scope['file_col'])
        scope['file_id'], scope['file_line'], scope['file_col'] = decl[1], decl[2], decl[3]

    scopeid = getScope(scope, conn)

    if scopeid is None:
        scope['id'] = scopeid = dxr.utils.next_global_id()
        stmt = language_schema.get_insert_sql('scopes', scope)
        conn.execute(stmt[0], stmt[1])

    if scopeid is not None:
        args['scopeid'] = scopeid

def _truncate(s, length=32):
    if len(s) <= length:
        return s
    return s[:length - 3] + '...'

def process_decldef(args, conn):
    if 'kind' not in args:
        return None

    # Store declaration map basics on memory
    qualname, defloc, declloc = args['qualname'], args['defloc'], args['declloc']
    defid, defline, defcol = splitLoc(conn, args['defloc'])
    declid, declline, declcol = splitLoc (conn, args['declloc'])
    if defid is None or declid is None:
        return None

    # FIXME: should kind be included in this mapping?
    decl_master[(qualname, declid, declline, declcol)] = (defid, defline, defcol)
    decl_master[(qualname, defid, defline, defcol)] = (defid, defline, defcol)

    if not fixupEntryPath(args, 'declloc', conn):
        return None
    if not fixupEntryPath(args, 'defloc', conn, 'definition'):
        return None
    fixupExtent(args, 'extent')
    
    return schema.get_insert_sql(args['kind'] + '_decldef', args)

def process_type(args, conn):
    if not fixupEntryPath(args, 'loc', conn):
        return None

    # Scope might have been previously added to satisfy other process_* call
    scopeid = getScope(args, conn)

    if scopeid is not None:
        args['id'] = scopeid
    else:
        args['id'] = dxr.utils.next_global_id()
        addScope(args, conn, 'name', 'id')

    handleScope(args, conn)
    fixupExtent(args, 'extent')

    return language_schema.get_insert_sql('types', args)

def process_typedef(args, conn):
    args['id'] = dxr.utils.next_global_id()
    if not fixupEntryPath(args, 'loc', conn):
        return None
    fixupExtent(args, 'extent')
#  handleScope(args, conn)
    return schema.get_insert_sql('typedefs', args)

def process_function(args, conn):
    if not fixupEntryPath(args, 'loc', conn):
        return None
    scopeid = getScope(args, conn)

    if scopeid is not None:
        args['id'] = scopeid
    else:
        args['id'] = dxr.utils.next_global_id()
        addScope(args, conn, 'name', 'id')

    if 'overridename' in args:
        overrides[args['id']] = (args['overridename'], args['overrideloc'])

    handleScope(args, conn)
    fixupExtent(args, 'extent')
    return language_schema.get_insert_sql('functions', args)

def process_impl(args, conn):
    inheritance[args['tbname'], args['tbloc'], args['tcname'], args['tcloc']] = args
    return None

def process_variable(args, conn):
    args['id'] = dxr.utils.next_global_id()
    if 'value' in args:
        args['value'] = _truncate(args['value'])
    if not fixupEntryPath(args, 'loc', conn):
        return None
    handleScope(args, conn)
    fixupExtent(args, 'extent')
    return language_schema.get_insert_sql('variables', args)

def process_ref(args, conn):
    if 'extent' not in args:
        return None
    if 'kind' not in args:
        return None

    if not fixupEntryPath(args, 'loc', conn):
        return None
    if not fixupEntryPath(args, 'declloc', conn, 'referenced'):
        return None
    fixupExtent(args, 'extent')

    return schema.get_insert_sql(args['kind'] + '_refs', args)

def process_warning(args, conn):
    if not fixupEntryPath(args, 'loc', conn):
        return None
    fixupExtent(args, 'extent')
    return schema.get_insert_sql('warnings', args)

def process_macro(args, conn):
    args['id'] = dxr.utils.next_global_id()
    if 'text' in args:
        args['text'] = args['text'].replace("\\\n", "\n").strip()
        args['text'] = _truncate(args['text'])
    if not fixupEntryPath(args, 'loc', conn):
        return None
    fixupExtent(args, 'extent')
    return schema.get_insert_sql('macros', args)

def process_call(args, conn):
    if 'callername' in args:
        calls[args['callername'], args['callerloc'],
                    args['calleename'], args['calleeloc']] = args
    else:
        calls[args['calleename'], args['calleeloc']] = args

    return None

def process_namespace(args, conn):
    if not fixupEntryPath(args, 'loc', conn):
        return None
    args['id'] = dxr.utils.next_global_id()
    fixupExtent(args, 'extent')
    return schema.get_insert_sql('namespaces', args)

def process_namespace_alias(args, conn):
    if not fixupEntryPath(args, 'loc', conn):
        return None
    args['id'] = dxr.utils.next_global_id()
    fixupExtent(args, 'extent')
    return schema.get_insert_sql('namespace_aliases', args)

def process_include(args, conn):
    """Turn an "include" line from a CSV into a row in the "includes" table."""
    fixupExtent(args)
    # If the ignore_patterns in the config file keep an #included file from
    # making it into the files table, just pretend that include doesn't exist.
    # Thus, IGNORE.
    return ('INSERT OR IGNORE INTO includes '
            '(file_id, extent_start, extent_end, target_id) '
            'VALUES ((SELECT id FROM files WHERE path=?), ?, ?, '
                    '(SELECT id FROM files WHERE path=?))',
            (args['source_path'], args['extent_start'], args['extent_end'], args['target_path']))

def load_indexer_output(fname):
    f = open(fname, "rb")
    try:
        parsed_iter = csv.reader(f)
        for line in parsed_iter:
            # Our first column is the type that we're reading; the others are
            # just an args array to be passed in.
            argobj = {}
            for i in range(1, len(line), 2):
                argobj[line[i]] = line[i + 1]
            globals()['process_' + line[0]](argobj)
    except Exception:
        print fname, line
        raise
    finally:
        f.close()

def dump_indexer_output(conn, fname):
    f = open(fname, 'r')
    limit = 0

    try:
        parsed_iter = csv.reader(f)
        for line in parsed_iter:
            args = {}
            # Our first column is the type that we're reading, the others are just
            # a key/value pairs array to be passed in
            for i in range(1, len(line), 2):
                args[line[i]] = line[i + 1]

            stmt = globals()['process_' + line[0]](args, conn)

            if stmt is None:
                continue

            if isinstance(stmt, list):
                for elem in list:
                    conn.execute(elem[0], elem[1])
            elif isinstance(stmt, tuple):
                try:
                    conn.execute(stmt[0], stmt[1])
                except Exception:
                    print line
                    print stmt
                    raise
            else:
                conn.execute(stmt)

            limit = limit + 1

            if limit > 10000:
                limit = 0
                conn.commit()
    except IndexError:
        raise
    finally:
        f.close()

def canonicalize_decl(name, id, line, col):
    value = decl_master.get((name, id, line, col), None)

    if value is None:
        return (name, id, line, col)
    else:
        return (name, value[0], value[1], value[2])

def recanon_decl(name, loc):
    decl_master[name, loc] = loc
    return (name, loc)

def fixup_scope(conn):
    conn.execute ("UPDATE types SET scopeid = (SELECT id FROM scopes WHERE " +
                                "scopes.file_id = types.file_id AND scopes.file_line = types.file_line " +
                                "AND scopes.file_col = types.file_col) WHERE scopeid IS NULL")
    conn.execute ("UPDATE functions SET scopeid = (SELECT id from scopes where " +
                                "scopes.file_id = functions.file_id AND scopes.file_line = functions.file_line " +
                                "AND scopes.file_col = functions.file_col) WHERE scopeid IS NULL")
    conn.execute ("UPDATE variables SET scopeid = (SELECT id from scopes where " +
                                "scopes.file_id = variables.file_id AND scopes.file_line = variables.file_line " +
                                "AND scopes.file_col = variables.file_col) WHERE scopeid IS NULL")


def build_inherits(base, child, direct):
    db = { 'tbase': base, 'tderived': child }
    if direct is not None:
        db['inhtype'] = direct
    return db

def generate_inheritance(conn):
    childMap, parentMap = {}, {}
    types = {}

    for row in conn.execute("SELECT qualname, file_id, file_line, file_col, id from types").fetchall():
        types[(row[0], row[1], row[2], row[3])] = row[4]

    for infoKey in inheritance:
        info = inheritance[infoKey]
        try:
            base_loc = splitLoc(conn, info['tbloc'])
            child_loc = splitLoc(conn, info['tcloc'])
            if base_loc[0] is None or child_loc[0] is None:
                continue

            base = types[canonicalize_decl(info['tbname'], base_loc[0], base_loc[1], base_loc[2])]
            child = types[canonicalize_decl(info['tcname'], child_loc[0], child_loc[1], child_loc[2])]
        except KeyError:
            continue

        conn.execute("INSERT OR IGNORE INTO impl(tbase, tderived, inhtype) VALUES (?, ?, ?)",
                                  (base, child, info.get('access', '')))

        # Get all known relations
        subs = childMap.setdefault(child, [])
        supers = parentMap.setdefault(base, [])
        # Use this information
        for sub in subs:
            conn.execute("INSERT OR IGNORE INTO impl(tbase, tderived) VALUES (?, ?)",
                                      (base, sub))
            parentMap[sub].append(base)
        for sup in supers:
            conn.execute("INSERT OR IGNORE INTO impl(tbase, tderived) VALUES (?, ?)",
                                      (sup, child))
            childMap[sup].append(child)

        # Carry through these relations
        newsubs = childMap.setdefault(base, [])
        newsubs.append(child)
        newsubs.extend(subs)
        newsupers = parentMap.setdefault(child, [])
        newsupers.append(base)
        newsupers.extend(supers)


def generate_callgraph(conn):
    global calls
    functions = {}
    variables = {}
    callgraph = []

    for row in conn.execute("SELECT qualname, file_id, file_line, file_col, id FROM functions").fetchall():
        functions[(row[0], row[1], row[2], row[3])] = row[4]

    for row in conn.execute("SELECT name, file_id, file_line, file_col, id FROM variables").fetchall():
        variables[(row[0], row[1], row[2], row[3])] = row[4]

    # Generate callers table
    for call in calls.values():
        if 'callername' in call:
            caller_loc = splitLoc(conn, call['callerloc'])
            if caller_loc[0] is None:
                continue
            source = canonicalize_decl(call['callername'], caller_loc[0], caller_loc[1], caller_loc[2])
            call['callerid'] = functions.get(source)

            if call['callerid'] is None:
                continue
        else:
            call['callerid'] = 0

        target_loc = splitLoc(conn, call['calleeloc'])
        if target_loc[0] is None:
            continue
        target = canonicalize_decl(call['calleename'], target_loc[0], target_loc[1], target_loc[2])
        targetid = functions.get(target)

        if targetid is None:
            targetid = variables.get(target)

        if targetid is not None:
            call['targetid'] = targetid
            callgraph.append(call)

    del variables

    # Generate targets table
    overridemap = {}

    for func, funcid in functions.iteritems():
        override = overrides.get(funcid)

        if override is None:
            continue

        override_loc = splitLoc(conn, override[1])
        if override_loc[0] is None:
            continue
        base = canonicalize_decl(override[0], override_loc[0], override_loc[1], override_loc[2])
        basekey = functions.get(base)

        if basekey is None:
            continue

        overridemap.setdefault(basekey, set()).add(funcid)

    rescan = [x for x in overridemap]
    while len(rescan) > 0:
        base = rescan.pop(0)
        childs = overridemap[base]
        prev = len(childs)
        temp = childs.union(*(overridemap.get(sub, []) for sub in childs))
        childs.update(temp)
        if len(childs) != prev:
            rescan.append(base)

    for base, childs in overridemap.iteritems():
        conn.execute("INSERT OR IGNORE INTO targets (targetid, funcid) VALUES (?, ?)",
                                  (-base, base));

        for child in childs:
            conn.execute("INSERT OR IGNORE INTO targets (targetid, funcid) VALUES (?, ?)",
                                      (-base, child));

    for call in callgraph:
        if call['calltype'] == 'virtual':
            targetid = call['targetid']
            call['targetid'] = -targetid
            if targetid not in overridemap:
                overridemap[targetid] = set()
                conn.execute("INSERT OR IGNORE INTO targets (targetid, funcid) VALUES (?, ?)",
                                          (-targetid, targetid));
        conn.execute("INSERT OR IGNORE INTO callers (callerid, targetid) VALUES (?, ?)",
                                    (call['callerid'], call['targetid']))


def update_defids(conn):
    sql = """
        UPDATE type_decldef SET defid = (
              SELECT id
                FROM types AS def
               WHERE def.file_id   = definition_file_id
                 AND def.file_line = definition_file_line
                 AND def.file_col  = definition_file_col
        )"""
    conn.execute(sql)
    sql = """
        UPDATE function_decldef SET defid = (
              SELECT id
                FROM functions AS def
               WHERE def.file_id   = definition_file_id
                 AND def.file_line = definition_file_line
                 AND def.file_col  = definition_file_col
        )"""
    conn.execute(sql)
    sql = """
        UPDATE variable_decldef SET defid = (
              SELECT id
                FROM variables AS def
               WHERE def.file_id   = definition_file_id
                 AND def.file_line = definition_file_line
                 AND def.file_col  = definition_file_col
        )"""
    conn.execute(sql)


def update_refs(conn):
    # References to declarations
    sql = """
        UPDATE type_refs SET refid = (
                SELECT defid
                  FROM type_decldef AS decl
                 WHERE decl.file_id   = referenced_file_id
                   AND decl.file_line = referenced_file_line
                   AND decl.file_col  = referenced_file_col
        ) WHERE refid IS NULL"""
    conn.execute(sql)
    sql = """
        UPDATE function_refs SET refid = (
                SELECT defid
                  FROM function_decldef AS decl
                 WHERE decl.file_id   = referenced_file_id
                   AND decl.file_line = referenced_file_line
                   AND decl.file_col  = referenced_file_col
        ) WHERE refid IS NULL"""
    conn.execute(sql)
    sql = """
        UPDATE variable_refs SET refid = (
                SELECT defid
                  FROM variable_decldef AS decl
                 WHERE decl.file_id   = referenced_file_id
                   AND decl.file_line = referenced_file_line
                   AND decl.file_col  = referenced_file_col
        ) WHERE refid IS NULL"""
    conn.execute(sql)

    # References to definitions
    sql = """
        UPDATE macro_refs SET refid = (
                SELECT id
                  FROM macros AS def
                 WHERE def.file_id    = referenced_file_id
                   AND def.file_line  = referenced_file_line
                   AND def.file_col   = referenced_file_col
        ) WHERE refid IS NULL"""
    conn.execute(sql)
    sql = """
        UPDATE type_refs SET refid = (
                SELECT id
                  FROM types AS def
                 WHERE def.file_id    = referenced_file_id
                   AND def.file_line  = referenced_file_line
                   AND def.file_col   = referenced_file_col
        ) WHERE refid IS NULL"""
    conn.execute(sql)
    sql = """
        UPDATE typedef_refs SET refid = (
                SELECT id
                  FROM typedefs AS def
                 WHERE def.file_id    = referenced_file_id
                   AND def.file_line  = referenced_file_line
                   AND def.file_col   = referenced_file_col
        ) WHERE refid IS NULL"""
    conn.execute(sql)
    sql = """
        UPDATE function_refs SET refid = (
                SELECT id
                  FROM functions AS def
                 WHERE def.file_id    = referenced_file_id
                   AND def.file_line  = referenced_file_line
                   AND def.file_col   = referenced_file_col
        ) WHERE refid IS NULL"""
    conn.execute(sql)
    sql = """
        UPDATE variable_refs SET refid = (
                SELECT id
                  FROM variables AS def
                 WHERE def.file_id    = referenced_file_id
                   AND def.file_line  = referenced_file_line
                   AND def.file_col   = referenced_file_col
        ) WHERE refid IS NULL"""
    conn.execute(sql)
    sql = """
        UPDATE namespace_refs SET refid = (
                SELECT id
                  FROM namespaces AS def
                 WHERE def.file_id    = referenced_file_id
                   AND def.file_line  = referenced_file_line
                   AND def.file_col   = referenced_file_col
        ) WHERE refid IS NULL"""
    conn.execute(sql)
    sql = """
        UPDATE namespace_alias_refs SET refid = (
                SELECT id
                  FROM namespace_aliases AS def
                 WHERE def.file_id    = referenced_file_id
                   AND def.file_line  = referenced_file_line
                   AND def.file_col   = referenced_file_col
        ) WHERE refid IS NULL"""
    conn.execute(sql)

########NEW FILE########
__FILENAME__ = htmlifier
import marshal
import os
import subprocess
import urlparse

import dxr.plugins

"""Omniglot - Speaking all commonly-used version control systems.
At present, this plugin is still under development, so not all features are
fully implemented.

Omniglot first scans the project directory looking for the hallmarks of a VCS
(such as the .hg or .git directory). It also looks for these in parent
directories in case DXR is only parsing a fraction of the repository. Once this
information is found, it attempts to extract upstream information about the
repository. From this information, it builds the necessary information to
reproduce the links.

Currently supported VCSes and upstream views:
- git (github)
- mercurial (hgweb)

Todos:
- add gitweb support for git
- add cvs, svn, bzr support
- produce in-DXR blame information using VCSs
- check if the mercurial paths are specific to Mozilla's customization or not.
"""

# Global variables
tree = None
source_repositories = {}

class VCS(object):
    """A class representing an abstract notion of a version-control system.
    In general, all path arguments to query methods should be normalized to be
    relative to the root directory of the VCS.
    """

    def __init__(self, root):
        self.root = root
        self.untracked_files = set()

    def get_root_dir(self):
        """Return the directory that is at the root of the VCS."""
        return self.root

    def get_vcs_name(self):
        """Return a recognizable name for the VCS."""
        return type(self).__name__

    def invoke_vcs(self, args):
        """Return the result of invoking said command on the repository, with
        the current working directory set to the root directory.
        """
        return subprocess.check_output(args, cwd=self.get_root_dir())

    def is_tracked(self, path):
        """Does the repository track this file?"""
        return path not in self.untracked_files

    def get_rev(self, path):
        """Return a human-readable revision identifier for the repository."""
        raise NotImplemented

    def generate_log(self, path):
        """Return a URL for a page that lists revisions for this file."""
        raise NotImplemented

    def generate_blame(self, path):
        """Return a URL for a page that lists source annotations for lines in
        this file.
        """
        raise NotImplemented

    def generate_diff(self, path):
        """Return a URL for a page that shows the last change made to this file.
        """
        raise NotImplemented

    def generate_raw(self, path):
        """Return a URL for a page that returns a raw copy of this file."""
        raise NotImplemented


class Mercurial(VCS):
    def __init__(self, root):
        super(Mercurial, self).__init__(root)
        # Find the revision
        self.revision = self.invoke_vcs(['hg', 'id', '-i']).strip()
        # Sometimes hg id returns + at the end.
        if self.revision.endswith("+"):
            self.revision = self.revision[:-1]

        # Make and normalize the upstream URL
        upstream = urlparse.urlparse(self.invoke_vcs(['hg', 'paths', 'default']).strip())
        recomb = list(upstream)
        if upstream.scheme == 'ssh':
            recomb[0] == 'http'
        recomb[1] = upstream.hostname # Eliminate any username stuff
        recomb[2] = '/' + recomb[2].lstrip('/') # strip all leading '/', add one back
        if not upstream.path.endswith('/'):
            recomb[2] += '/' # Make sure we have a '/' on the end
        recomb[3] = recomb[4] = recomb[5] = '' # Just those three
        self.upstream = urlparse.urlunparse(recomb)

        # Find all untracked files
        self.untracked_files = set(line.split()[1] for line in
            self.invoke_vcs(['hg', 'status', '-u', '-i']).split('\n')[:-1])

    @staticmethod
    def claim_vcs_source(path, dirs):
        if '.hg' in dirs:
            dirs.remove('.hg')
            return Mercurial(path)
        return None

    def get_rev(self, path):
        return self.revision

    def generate_log(self, path):
        return self.upstream + 'filelog/' + self.revision + '/' + path

    def generate_blame(self, path):
        return self.upstream + 'annotate/' + self.revision + '/' + path

    def generate_diff(self, path):
        return self.upstream + 'diff/' + self.revision + '/' + path

    def generate_raw(self, path):
        return self.upstream + 'raw-file/' + self.revision + '/' + path


class Git(VCS):
    def __init__(self, root):
        super(Git, self).__init__(root)
        self.untracked_files = set(line for line in
            self.invoke_vcs(['git', 'ls-files', '-o']).split('\n')[:-1])
        self.revision = self.invoke_vcs(['git', 'rev-parse', 'HEAD'])
        source_urls = self.invoke_vcs(['git', 'remote', '-v']).split('\n')
        for src_url in source_urls:
            name, url, _ = src_url.split()
            if name == 'origin':
                self.upstream = self.synth_web_url(url)
                break

    @staticmethod
    def claim_vcs_source(path, dirs):
        if '.git' in dirs:
            dirs.remove('.git')
            return Git(path)
        return None

    def get_rev(self, path):
        return self.revision[:10]

    def generate_log(self, path):
        return self.upstream + "/commits/" + self.revision + "/" + path

    def generate_blame(self, path):
        return self.upstream + "/blame/" + self.revision + "/" + path

    def generate_diff(self, path):
        # I really want to make this anchor on the file in question, but github
        # doesn't seem to do that nicely
        return self.upstream + "/commit/" + self.revision

    def generate_raw(self, path):
        return self.upstream + "/raw/" + self.revision + "/" + path

    def synth_web_url(self, repo):
        if repo.startswith("git@github.com:"):
            self._is_github = True
            return "https://github.com/" + repo[len("git@github.com:"):]
        elif repo.startswith("git://github.com/"):
            self._is_github = True
            if repo.endswith(".git"):
                repo = repo[:-len(".git")]
            return "https" + repo[len("git"):]
        raise Exception("I don't know what's going on")


class Perforce(VCS):
    def __init__(self, root):
        super(Perforce, self).__init__(root)
        have = self._p4run(['have'])
        self.have = dict((x['path'][len(root) + 1:], x) for x in have)
        try:
            self.upstream = tree.plugin_omniglot_p4web
        except AttributeError:
            self.upstream = "http://p4web/"

    @staticmethod
    def claim_vcs_source(path, dirs):
        if 'P4CONFIG' not in os.environ:
            return None
        if os.path.exists(os.path.join(path, os.environ['P4CONFIG'])):
            return Perforce(path)
        return None

    def _p4run(self, args):
        ret = []
        env = os.environ
        env["PWD"] = self.root
        proc = subprocess.Popen(['p4', '-G'] + args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            cwd=self.root,
            env=env)
        while True:
            try:
                x = marshal.load(proc.stdout)
            except EOFError:
                break
            ret.append(x)
        return ret

    def is_tracked(self, path):
        return path in self.have

    def get_rev(self, path):
        info = self.have[path]
        return '#' + info['haveRev']

    def generate_log(self, path):
        info = self.have[path]
        return self.upstream + info['depotFile'] + '?ac=22#' + info['haveRev']

    def generate_blame(self, path):
        info = self.have[path]
        return self.upstream + info['depotFile'] + '?ac=193'

    def generate_diff(self, path):
        info = self.have[path]
        haveRev = info['haveRev']
        prevRev = str(int(haveRev) - 1)
        return (self.upstream + info['depotFile'] + '?ac=19&rev1=' + prevRev +
                '&rev2=' + haveRev)

    def generate_raw(self, path):
        info = self.have[path]
        return self.upstream + info['depotFile'] + '?ac=98&rev1=' + info['haveRev']


every_vcs = [Mercurial, Git, Perforce]


# Load global variables
def load(tree_, conn):
    global tree, lookup_order
    tree = tree_
    # Find all of the VCS's in the source directory
    for cwd, dirs, files in os.walk(tree.source_folder):
        for vcs in every_vcs:
            attempt = vcs.claim_vcs_source(cwd, dirs)
            if attempt is not None:
                source_repositories[attempt.root] = attempt

    # It's possible that the root of the tree is not a VCS by itself, so walk up
    # the hierarchy until we find a parent folder that is a VCS. If we can't
    # find any, than no VCSs exist for the top-level of this repository.
    directory = tree.source_folder
    while directory != '/' and directory not in source_repositories:
        directory = os.path.dirname(directory)
        for vcs in every_vcs:
            attempt = vcs.claim_vcs_source(directory, os.listdir(directory))
            if attempt is not None:
                source_repositories[directory] = attempt
    # Note: we want to make sure that we look up source repositories by deepest
    # directory first.
    lookup_order = source_repositories.keys()
    lookup_order.sort(key=len, reverse=True)


def find_vcs_for_file(path):
    """Given an absolute path, find a source repository we know about that
    claims to track that file.
    """
    for directory in lookup_order:
        # This seems to be the easiest way to find "is path in the subtree
        # rooted at directory?"
        if os.path.relpath(path, directory).startswith('..'):
            continue
        vcs = source_repositories[directory]
        if vcs.is_tracked(os.path.relpath(path, vcs.get_root_dir())):
            return vcs
    return None


class LinksHtmlifier(object):
    """Htmlifier which adds blame and external links to VCS web utilities."""
    def __init__(self, path):
        if not os.path.isabs(path):
            path = os.path.join(tree.source_folder, path)
        self.vcs = find_vcs_for_file(path)
        if self.vcs is not None:
            self.path = os.path.relpath(path, self.vcs.get_root_dir())
            self.name = self.vcs.get_vcs_name()

    def refs(self):
        return []

    def regions(self):
        return []

    def annotations(self):
        return []

    def links(self):
        if self.vcs is None:
            yield 5, 'Untracked file', []
            return
        def items():
            yield 'log', "Log", self.vcs.generate_log(self.path)
            yield 'blame', "Blame", self.vcs.generate_blame(self.path)
            yield 'diff',  "Diff", self.vcs.generate_diff(self.path)
            yield 'raw', "Raw", self.vcs.generate_raw(self.path)
        yield 5, '%s (%s)' % (self.name, self.vcs.get_rev(self.path)), items()


def htmlify(path, text):
    return LinksHtmlifier(path)


__all__ = dxr.plugins.htmlifier_exports()

########NEW FILE########
__FILENAME__ = indexer
import dxr.plugins

# Nothing to do here, but we must implement indexer.py to explicitely declared
# that these functions are no-op. Otherwise DXR shall assume the file or the
# implementation is missing, and thus, something is badly wrong.

def pre_process(tree, environ):
    pass

def post_process(tree, conn):
    pass

__all__ = dxr.plugins.indexer_exports()

########NEW FILE########
__FILENAME__ = htmlifier
from os.path import basename
import re

import pygments
from pygments.lexers import get_lexer_for_filename, JavascriptLexer
from pygments.lexer import inherit
from pygments.token import Token, Comment

import dxr.plugins


token_classes = {Token.Comment.Preproc: 'p'}
token_classes.update((t, 'k') for t in [Token.Keyword,
                                        Token.Keyword.Constant,
                                        Token.Keyword.Declaration,
                                        Token.Keyword.Namespace,
                                        Token.Keyword.Pseudo,
                                        Token.Keyword.Reserved,
                                        Token.Keyword.Type])
token_classes.update((t, 'str') for t in [Token.String,
                                          Token.String.Backtick,
                                          Token.String.Char,
                                          Token.String.Doc,
                                          Token.String.Double,
                                          Token.String.Escape,
                                          Token.String.Heredoc,
                                          Token.String.Interpol,
                                          Token.String.Other,
                                          Token.String.Regex,
                                          Token.String.Single,
                                          Token.String.Symbol])
token_classes.update((t, 'c') for t in [Token.Comment,
                                        Token.Comment.Multiline,
                                        Token.Comment.Single,
                                        Token.Comment.Special])


# Extend the Pygments Javascript lexer to handle preprocessor directives.
class JavascriptPreprocLexer(JavascriptLexer):
    """
    For Javascript with Mozilla build preprocessor directives.
    See https://developer.mozilla.org/en-US/docs/Build/Text_Preprocessor .
    """

    name = 'JavaScriptPreproc'
    filenames = []
    mimetypes = []

    tokens = {
        'commentsandwhitespace': [
            # python-style comment
            (r'#\s[^\n]*\n', Comment.Single),
            # preprocessor directives
            (r'#(includesubst|include|expand|define|undef|ifdef|ifndef|elifdef|'
             r'elifndef|if|elif|else|endif|filter|unfilter|literal|error)',
             Comment.Preproc),
            pygments.lexer.inherit
        ]
    }

class Pygmentizer(object):
    """Pygmentizer to apply CSS classes to syntax-highlit regions"""

    def __init__(self, text, lexer):
        self.text = text
        self.lexer = lexer

    def refs(self):
        return []

    def regions(self):
        for index, token, text in self.lexer.get_tokens_unprocessed(self.text):
            cls = token_classes.get(token)
            if cls:
                yield index, index + len(text), cls

    def annotations(self):
        return []

    def links(self):
        return []


def load(tree, conn):
    pass


def htmlify(path, text):
    # Options and filename
    options = {'encoding': 'utf-8'}
    filename = basename(path)

    # Use a custom lexer for js/jsm files to highlight prepocessor directives
    if filename.endswith('.js') or filename.endswith('.jsm'):
        lexer = JavascriptPreprocLexer(**options)
    else:
        try:
            # Lex .h files as C++ so occurrences of "class" and such get colored;
            # Pygments expects .H, .hxx, etc. This is okay even for uses of
            # keywords that would be invalid in C++, like 'int class = 3;'.
            lexer = get_lexer_for_filename('dummy.cpp' if filename.endswith('.h')
                                                       else filename,
                                           **options)
        except pygments.util.ClassNotFound:
            return None

    return Pygmentizer(text, lexer)


__all__ = dxr.plugins.htmlifier_exports()

########NEW FILE########
__FILENAME__ = indexer
import dxr.plugins


def pre_process(tree, environ):
    pass


def post_process(tree, conn):
    pass


__all__ = dxr.plugins.indexer_exports()

########NEW FILE########
__FILENAME__ = htmlifier
# -*- coding: utf-8 -*-
import dxr.plugins
import re
import cgi
import urllib

""" Regular expression for matching urls
Credits to: http://stackoverflow.com/a/1547940
"""
pat  = "\[(https?://[A-Za-z0-9\-\._~:\/\?#[\]@!\$&'()*\+,;=%]+\.[A-Za-z0-9\-\._~:\/\?#[\]@!\$&'()*\+,;=%]+)\]"
pat += "|\((https?://[A-Za-z0-9\-\._~:\/\?#[\]@!\$&'()*\+,;=%]+\.[A-Za-z0-9\-\._~:\/\?#[\]@!\$&'()*\+,;=%]+)\)"
pat += "|(https?://[A-Za-z0-9\-\._~:\/\?#[\]@!\$&'()*\+,;=%]+\.[A-Za-z0-9\-\._~:\/\?#[\]@!\$&'()*\+,;=%]+)"
urlFinder = re.compile(pat)

def load(tree, conn):
    # Nothing to do here
    pass

class UrlHtmlifier(object):
    def __init__(self, text):
        self.text = text
    
    def refs(self):
        for m in urlFinder.finditer(self.text):
            try:
                if m.group(1):
                    url = m.group(1).decode('utf-8')
                    start, end = m.start(1), m.end(1)
                elif m.group(2):
                    url = m.group(2).decode('utf-8')
                    start, end = m.start(2), m.end(2)
                else:
                    url = m.group(3).decode('utf-8')
                    start, end = m.start(3), m.end(3)
            except UnicodeDecodeError:
                pass
            else:
                yield start, end, ([{
                    'html':   "Follow link",
                    'title':  "Visit %s" % url,
                    'href':   url,
                    'icon':   'external_link'
                }], '', None)
    
    def regions(self):
        return []

    def annotations(self):
        return []

    def links(self):
        return []


def htmlify(path, text):
    return UrlHtmlifier(text)

__all__ = dxr.plugins.htmlifier_exports()

########NEW FILE########
__FILENAME__ = indexer
import dxr.plugins

# Nothing to do here, but we must implement indexer.py to explicitely declared
# that these functions are no-op. Otherwise DXR shall assume the file or the
# implementation is missing, and thus, something is badly wrong.

def pre_process(tree, environ):
    pass

def post_process(tree, conn):
    pass

__all__ = dxr.plugins.indexer_exports()

########NEW FILE########
__FILENAME__ = plugins
import os, sys
import imp


def indexer_exports():
    """ Indexer files should export these, for use as __all__"""
    return ['pre_process', 'post_process']


def htmlifier_exports():
    """ Htmlifier files should export these, for use as __all__"""
    return ['htmlify', 'load']


def load_indexers(tree):
    """ Load indexers for a given tree """
    # Allow plugins to load from the plugin folder
    sys.path.append(tree.config.plugin_folder)
    plugins = []
    for name in tree.enabled_plugins:
        path = os.path.join(tree.config.plugin_folder, name)
        f, mod_path, desc = imp.find_module("indexer", [path])
        plugin = imp.load_module('dxr.plugins.' + name + "_indexer", f, mod_path, desc)
        f.close()
        plugins.append(plugin)
    return plugins


def load_htmlifiers(tree):
    """ Load htmlifiers for a given tree """
    # Allow plugins to load from the plugin folder
    sys.path.append(tree.config.plugin_folder)
    plugins = []
    for name in tree.enabled_plugins:
        path = os.path.join(tree.config.plugin_folder, name)
        f, mod_path, desc = imp.find_module("htmlifier", [path])
        plugin = imp.load_module('dxr.plugins.' + name + "_htmlifier", f, mod_path, desc)
        f.close()
        plugins.append(plugin)
    return plugins

########NEW FILE########
__FILENAME__ = query
import cgi
from itertools import chain, groupby
import re
import struct
import time

from jinja2 import Markup
from parsimonious import Grammar
from parsimonious.nodes import NodeVisitor


# TODO: Some kind of UI feedback for bad regexes


# TODO
#   - Special argument files-only to just search for file names
#   - If no plugin returns an extents query, don't fetch content


# Pattern for matching a file and line number filename:n
_line_number = re.compile("^.*:[0-9]+$")

class Query(object):
    """Query object, constructor will parse any search query"""

    def __init__(self, conn, querystr, should_explain=False, is_case_sensitive=True):
        self.conn = conn
        self._should_explain = should_explain
        self._sql_profile = []
        self.is_case_sensitive = is_case_sensitive

        # A dict with a key for each filter type (like "regexp") in the query.
        # There is also a special "text" key where free text ends up.
        self.terms = QueryVisitor(is_case_sensitive=is_case_sensitive).visit(query_grammar.parse(querystr))

    def single_term(self):
        """Return the single textual term comprising the query.

        If there is more than one term in the query or if the single term is a
        non-textual one, return None.

        """
        if self.terms.keys() == ['text'] and len(self.terms['text']) == 1:
            return self.terms['text'][0]['arg']

    #TODO Use named place holders in filters, this would make the filters easier to write

    def execute_sql(self, sql, *parameters):
        if self._should_explain:
            self._sql_profile.append({
                "sql" : sql,
                "parameters" : parameters[0] if len(parameters) >= 1 else [],
                "explanation" : self.conn.execute("EXPLAIN QUERY PLAN " + sql, *parameters)
            })
            start_time = time.time()
        res = self.conn.execute(sql, *parameters)
        if self._should_explain:
            # fetch results eagerly so we can get an accurate time for the entire operation
            res = res.fetchall()
            self._sql_profile[-1]["elapsed_time"] = time.time() - start_time
            self._sql_profile[-1]["nrows"] = len(res)
        return res

    # Fetch results using a query,
    # See: queryparser.py for details in query specification
    def results(self,
                offset=0, limit=100,
                markup='<b>', markdown='</b>'):
        """Return search results as an iterable of these::

            (icon,
             path within tree,
             (line_number, highlighted_line_of_code)), ...

        """
        sql = """
            SELECT files.path, files.icon, files.encoding, trg_index.text, files.id,
            extents(trg_index.contents)
                FROM trg_index, files
              WHERE %s ORDER BY files.path LIMIT ? OFFSET ?
        """
        conditions = " files.id = trg_index.id "
        arguments = []

        # Give each registered filter an opportunity to contribute to the
        # query. This query narrows down the universe to a set of matching
        # files:
        has_extents = False
        for f in filters:
            for conds, args, exts in f.filter(self.terms):
                has_extents = exts or has_extents
                conditions += " AND " + conds
                arguments += args

        sql %= conditions
        arguments += [limit, offset]

        #TODO Actually do something with the has_extents, ie. don't fetch contents

        cursor = self.execute_sql(sql, arguments)

        # For each returned file (including, only in the case of the trilite
        # filter, a set of extents)...
        for path, icon, encoding, content, file_id, extents in cursor:
            elist = []

            # Special hack for TriLite extents
            if extents:
                matchExtents = []
                for i in xrange(0, len(extents), 8):
                    s, e = struct.unpack("II", extents[i:i+8])
                    matchExtents.append((s, e, []))
                elist.append(fix_extents_overlap(sorted(matchExtents)))

            # Let each filter do one or more additional queries to find the
            # extents to highlight:
            for f in filters:
                for e in f.extents(self.terms, self.execute_sql, file_id):
                    elist.append(e)
            offsets = list(merge_extents(*elist))

            if self._should_explain:
                continue

            # Yield the file, metadata, and iterable of highlighted offsets:
            yield icon, path, _highlit_lines(content, offsets, markup, markdown, encoding)


        # TODO: Decouple and lexically evacuate this profiling stuff from
        # results():
        def number_lines(arr):
            ret = []
            for i in range(len(arr)):
                if arr[i] == "":
                    ret.append((i, " "))  # empty lines cause the <div> to collapse and mess up the formatting
                else:
                    ret.append((i, arr[i]))
            return ret

        for i in range(len(self._sql_profile)):
            profile = self._sql_profile[i]
            yield ("",
                          "sql %d (%d row(s); %s seconds)" % (i, profile["nrows"], profile["elapsed_time"]),
                          number_lines(profile["sql"].split("\n")))
            yield ("",
                          "parameters %d" % i,
                          number_lines(map(lambda parm: repr(parm), profile["parameters"])));
            yield ("",
                          "explanation %d" % i,
                          number_lines(map(lambda row: row["detail"], profile["explanation"])))


    def direct_result(self):
        """Return a single search result that is an exact match for the query.

        If there is such a result, return a tuple of (path from root of tree,
        line number). Otherwise, return None.

        """
        term = self.single_term()
        if not term:
            return None
        cur = self.conn.cursor()

        line_number = -1
        if _line_number.match(term):
            parts = term.split(":")
            if len(parts) == 2:
                term = parts[0]
                line_number = int(parts[1])

        # See if we can find only one file match
        cur.execute("""
            SELECT path FROM files WHERE
                path = :term
                OR path LIKE :termPre
            LIMIT 2
        """, {"term": term,
              "termPre": "%/" + term})

        rows = cur.fetchall()
        if rows and len(rows) == 1:
            if line_number >= 0:
                return (rows[0]['path'], line_number)
            return (rows[0]['path'], 1)

        # Case sensitive type matching
        cur.execute("""
            SELECT
                (SELECT path FROM files WHERE files.id = types.file_id) as path,
                types.file_line
              FROM types WHERE types.name = ? LIMIT 2
        """, (term,))
        rows = cur.fetchall()
        if rows and len(rows) == 1:
            return (rows[0]['path'], rows[0]['file_line'])

        # Case sensitive function names
        cur.execute("""
            SELECT
                    (SELECT path FROM files WHERE files.id = functions.file_id) as path,
                    functions.file_line
                FROM functions WHERE functions.name = ? LIMIT 2
        """, (term,))
        rows = cur.fetchall()
        if rows and len(rows) == 1:
            return (rows[0]['path'], rows[0]['file_line'])

        # Try fully qualified names
        if '::' in term:
            # Case insensitive type matching
            cur.execute("""
                SELECT
                      (SELECT path FROM files WHERE files.id = types.file_id) as path,
                      types.file_line
                    FROM types WHERE types.qualname LIKE ? LIMIT 2
            """, (term,))
            rows = cur.fetchall()
            if rows and len(rows) == 1:
                return (rows[0]['path'], rows[0]['file_line'])

            # Case insensitive function names
            cur.execute("""
            SELECT
                  (SELECT path FROM files WHERE files.id = functions.file_id) as path,
                  functions.file_line
                FROM functions WHERE functions.qualname LIKE ? LIMIT 2
            """, (term + '%',))  # Trailing % to eat "(int x)" etc.
            rows = cur.fetchall()
            if rows and len(rows) == 1:
                return (rows[0]['path'], rows[0]['file_line'])

        # Case insensitive type matching
        cur.execute("""
        SELECT
              (SELECT path FROM files WHERE files.id = types.file_id) as path,
              types.file_line
            FROM types WHERE types.name LIKE ? LIMIT 2
        """, (term,))
        rows = cur.fetchall()
        if rows and len(rows) == 1:
            return (rows[0]['path'], rows[0]['file_line'])

        # Case insensitive function names
        cur.execute("""
        SELECT
              (SELECT path FROM files WHERE files.id = functions.file_id) as path,
              functions.file_line
            FROM functions WHERE functions.name LIKE ? LIMIT 2
        """, (term,))
        rows = cur.fetchall()
        if rows and len(rows) == 1:
            return (rows[0]['path'], rows[0]['file_line'])

        # Okay we've got nothing
        return None


def _highlit_line(content, offsets, markup, markdown, encoding):
    """Return a line of string ``content`` with the given ``offsets`` prefixed
    by ``markup`` and suffixed by ``markdown``.

    We assume that none of the offsets split a multibyte character. Leading
    whitespace is stripped.

    """
    def chunks():
        try:
            # Start on the line the highlights are on:
            chars_before = content.rindex('\n', 0, offsets[0][0]) + 1
        except ValueError:
            chars_before = None
        for start, end in offsets:
            yield cgi.escape(content[chars_before:start].decode(encoding,
                                                                'replace'))
            yield markup
            yield cgi.escape(content[start:end].decode(encoding, 'replace'))
            yield markdown
            chars_before = end
        # Make sure to get the rest of the line after the last highlight:
        try:
            next_newline = content.index('\n', chars_before)
        except ValueError:  # eof
            next_newline = None
        yield cgi.escape(content[chars_before:next_newline].decode(encoding,
                                                                   'replace'))
    return ''.join(chunks()).lstrip()


def _highlit_lines(content, offsets, markup, markdown, encoding):
    """Return a list of (line number, highlit line) tuples.

    :arg content: The contents of the file against which the offsets are
        reported, as a bytestring. (We need to operate in terms of bytestrings,
        because those are the terms in which the C compiler gives us offsets.)
    :arg offsets: A sequence of non-overlapping (start offset, end offset,
        [keylist (presently unused)]) tuples describing each extent to
        highlight. The sequence must be in order by start offset.

    Assumes no newlines are highlit.

    """
    line_extents = []  # [(line_number, (start, end)), ...]
    lines_before = 1
    chars_before = 0
    for start, end, _ in offsets:
        # How many lines we've skipped since we last knew what line we were on:
        lines_since = content.count('\n', chars_before, start)

        # Figure out what line we're on, and throw this extent into its bucket:
        line = lines_before + lines_since
        line_extents.append((line, (start, end)))

        lines_before = line
        chars_before = end

    # Bucket highlit ranges by line, and build up the marked up strings:
    return [(line, _highlit_line(content,
                                 [extent for line, extent in lines_and_extents],
                                 markup,
                                 markdown,
                                 encoding)) for
            line, lines_and_extents in groupby(line_extents, lambda (l, e): l)]


def like_escape(val):
    """Escape for usage in as argument to the LIKE operator """
    return (val.replace("\\", "\\\\")
               .replace("_", "\\_")
               .replace("%", "\\%")
               .replace("?", "_")
               .replace("*", "%"))

class genWrap(object):
    """Auxiliary class for wrapping a generator and make it nicer"""
    def __init__(self, gen):
        self.gen = gen
        self.value = None
    def next(self):
        try:
            self.value = self.gen.next()
            return True
        except StopIteration:
            self.value = None
            return False


def merge_extents(*elist):
    """
        Take a list of extents generators and merge them into one stream of extents
        overlapping extents will be split in two, this means that they will start
        and stop at same location.
        Here we assume that each extent is a triple as follows:
            (start, end, keyset)

        Where keyset is a list of something that should be applied to the extent
        between start and end.
    """
    elist = [genWrap(e) for e in elist]
    elist = [e for e in elist if e.next()]
    while len(elist) > 0:
        start = min((e.value[0] for e in elist))
        end = min((e.value[1] for e in elist if e.value[0] == start))
        keylist = []
        for e in (e for e in elist if e.value[0] == start):
            for k in e.value[2]:
                if k not in keylist:
                    keylist.append(k)
            e.value = (end, e.value[1], e.value[2])
        yield start, end, keylist
        elist = [e for e in elist if e.value[0] < e.value[1] or e.next()]


def fix_extents_overlap(extents):
    """
        Take a sorted list of extents and yield the extents without overlapings.
        Assumes extents are of similar format as in merge_extents
    """
    # There must be two extents for there to be an overlap
    while len(extents) >= 2:
        # Take the two next extents
        start1, end1, keys1 = extents[0]
        start2, end2, keys2 = extents[1]
        # Check for overlap
        if end1 <= start2:
            # If no overlap, yield first extent
            yield start1, end1, keys1
            extents = extents[1:]
            continue
        # If overlap, yield extent from start1 to start2
        if start1 != start2:
            yield start1, start2, keys1
        extents[0] = (start2, end1, keys1 + keys2)
        extents[1] = (end1, end2, keys2)
    if len(extents) > 0:
        yield extents[0]


class SearchFilter(object):
    """Base class for all search filters, plugins subclasses this class and
            registers an instance of them calling register_filter
    """
    def __init__(self, description='', languages=None):
        self.description = description
        self.languages = languages or []

    def filter(self, terms):
        """Yield tuples of (SQL conditions, list of arguments, and True) if
        this filter offers extents for results.

        SQL conditions must be string and condition on files.id.

        :arg terms: A dictionary with keys for each filter name I handle (as
            well as others, possibly, which should be ignored). Example::

                {'function': [{'arg': 'o hai',
                               'not': False,
                               'case_sensitive': False,
                               'qualified': False},
                               {'arg': 'what::next',
                                'not': True,
                                'case_sensitive': False,
                                'qualified': True}],
                  ...}

        """
        return []

    def extents(self, terms, execute_sql, file_id):
        """Return an ordered iterable of extents to highlight. Or an iterable
        of generators. It seems to vary.

        :arg execute_sql: A callable that takes some SQL and an iterable of
            params and executes it, returning the result
        :arg file_id: The ID of the file from which to return extents
        :arg kwargs: A dictionary with keys for each filter name I handle (as
            well as others, possibly), as in filter()

        """
        return []

    def names(self):
        """Return a list of filter names this filter handles.

        This smooths out the difference between the trilite filter (which
        handles 2 different params) and the other filters (which handle only 1).

        """
        return [self.param] if hasattr(self, 'param') else self.params

    def menu_item(self):
        """Return the item I contribute to the Filters menu.

        Return a dicts with ``name`` and ``description`` keys.

        """
        return dict(name=self.param, description=self.description)

    def valid_for_language(self, language):
        return language in self.languages


class TriLiteSearchFilter(SearchFilter):
    params = ['text', 'regexp']

    def filter(self, terms):
        not_conds = []
        not_args  = []
        for term in terms.get('text', []):
            if term['arg']:
                if term['not']:
                    not_conds.append("trg_index.contents MATCH ?")
                    not_args.append(('substr:' if term['case_sensitive']
                                               else 'isubstr:') +
                                    term['arg'])
                else:
                    yield ("trg_index.contents MATCH ?",
                           [('substr-extents:' if term['case_sensitive']
                                               else 'isubstr-extents:') +
                            term['arg']],
                           True)
        for term in terms.get('re', []) + terms.get('regexp', []):
            if term['arg']:
                if term['not']:
                    not_conds.append("trg_index.contents MATCH ?")
                    not_args.append("regexp:" + term['arg'])
                else:
                    yield ("trg_index.contents MATCH ?",
                           ["regexp-extents:" + term['arg']],
                           True)

        if not_conds:
            yield (""" files.id NOT IN (SELECT id FROM trg_index WHERE %s) """
                       % " AND ".join(not_conds),
                   not_args,
                   False)

    # Notice that extents is more efficiently handled in the search query
    # Sorry to break the pattern, but it's significantly faster.

    def menu_item(self):
        return {'name': 'regexp',
                'description': Markup(r'Regular expression. Examples: <code>regexp:(?i)\bs?printf</code> <code>regexp:"(three|3) mice"</code>')}

    def valid_for_language(self, language):
        return True

class SimpleFilter(SearchFilter):
    """Search filter for limited results.
            This filter take 5 parameters, defined as follows:
                param           Search parameter from query
                filter_sql      Sql condition for limited using argument to param
                neg_filter_sql  Sql condition for limited using argument to param negated.
                ext_sql         Sql statement fetch an ordered list of extents, given
                                                file-id and argument to param as parameters.
                                                (None if not applicable)
                formatter       Function/lambda expression for formatting the argument
    """
    def __init__(self, param, filter_sql, neg_filter_sql, ext_sql, formatter, **kwargs):
        super(SimpleFilter, self).__init__(**kwargs)
        self.param = param
        self.filter_sql = filter_sql
        self.neg_filter_sql = neg_filter_sql
        self.ext_sql = ext_sql
        self.formatter = formatter

    def filter(self, terms):
        for term in terms.get(self.param, []):
            arg = term['arg']
            if term['not']:
                yield self.neg_filter_sql, self.formatter(arg), False
            else:
                yield self.filter_sql, self.formatter(arg), self.ext_sql is not None

    def extents(self, terms, execute_sql, file_id):
        if self.ext_sql:
            for term in terms.get(self.param, []):
                for start, end in execute_sql(self.ext_sql,
                                              [file_id] + self.formatter(term['arg'])):
                    yield start, end, []


class ExistsLikeFilter(SearchFilter):
    """Search filter for asking of something LIKE this EXISTS,
            This filter takes 5 parameters, param is the search query parameter,
            "-" + param is a assumed to be the negated search filter.
            The filter_sql must be an (SELECT 1 FROM ... WHERE ... %s ...), sql condition on files.id,
            s.t. replacing %s with "qual_name = ?" or "like_name LIKE %?%" where ? is arg given to param
            in search query, and prefixing with EXISTS or NOT EXISTS will yield search
            results as desired :)
            (BTW, did I mention that 'as desired' is awesome way of writing correct specifications)
            ext_sql, must be an sql statement for a list of extent start and end,
            given arguments (file_id, %arg%), where arg is the argument given to
            param. Again %s will be replaced with " = ?" or "LIKE %?%" depending on
            whether or not param is prefixed +
    """
    def __init__(self, param, filter_sql, ext_sql, qual_name, like_name, **kwargs):
        super(ExistsLikeFilter, self).__init__(**kwargs)
        self.param = param
        self.filter_sql = filter_sql
        self.ext_sql = ext_sql
        self.qual_expr = " %s = ? " % qual_name
        self.like_expr = """ %s LIKE ? ESCAPE "\\" """ % like_name

    def filter(self, terms):
        for term in terms.get(self.param, []):
            is_qualified = term['qualified']
            arg = term['arg']
            filter_sql = (self.filter_sql % (self.qual_expr if is_qualified
                                             else self.like_expr))
            sql_params = [arg if is_qualified else like_escape(arg)]
            if term['not']:
                yield 'NOT EXISTS (%s)' % filter_sql, sql_params, False
            else:
                yield 'EXISTS (%s)' % filter_sql, sql_params, self.ext_sql is not None

    def extents(self, terms, execute_sql, file_id):
        def builder():
            for term in terms.get(self.param, []):
                arg = term['arg']
                escaped_arg, sql_expr = (
                    (arg, self.qual_expr) if term['qualified']
                    else (like_escape(arg), self.like_expr))
                for start, end in execute_sql(self.ext_sql % sql_expr,
                                              [file_id, escaped_arg]):
                    # Nones used to occur in the DB. Is this still true?
                    if start and end:
                        yield start, end, []
        if self.ext_sql:
            yield builder()


class UnionFilter(SearchFilter):
    """Provides a filter matching the union of the given filters.

            For when you want OR instead of AND.
    """
    def __init__(self, filters, **kwargs):
        super(UnionFilter, self).__init__(**kwargs)
        # For the moment, UnionFilter supports only single-param filters. There
        # is no reason this can't change.
        unique_params = set(f.param for f in filters)
        if len(unique_params) > 1:
            raise ValueError('All filters that make up a union filter must have the same name, but we got %s.' % ' and '.join(unique_params))
        self.param = unique_params.pop()  # for consistency with other filters
        self.filters = filters

    def filter(self, terms):
        for res in zip(*(filt.filter(terms) for filt in self.filters)):
            yield ('(' + ' OR '.join(conds for (conds, args, exts) in res) + ')',
                   [arg for (conds, args, exts) in res for arg in args],
                   any(exts for (conds, args, exts) in res))

    def extents(self, terms, execute_sql, file_id):
        def builder():
            for filt in self.filters:
                for hits in filt.extents(terms, execute_sql, file_id):
                    for hit in hits:
                        yield hit
        def sorter():
            for hits in groupby(sorted(builder())):
                yield hits[0]
        yield sorter()


# Register filters by adding them to this list:
filters = [
    # path filter
    SimpleFilter(
        param             = "path",
        description       = Markup('File or directory sub-path to search within. <code>*</code> and <code>?</code> act as shell wildcards.'),
        filter_sql        = """files.path LIKE ? ESCAPE "\\" """,
        neg_filter_sql    = """files.path NOT LIKE ? ESCAPE "\\" """,
        ext_sql           = None,
        formatter         = lambda arg: ['%' + like_escape(arg) + '%'],
        languages          = ["C"]
    ),

    # ext filter
    SimpleFilter(
        param             = "ext",
        description       = Markup('Filename extension: <code>ext:cpp</code>'),
        filter_sql        = """files.path LIKE ? ESCAPE "\\" """,
        neg_filter_sql    = """files.path NOT LIKE ? ESCAPE "\\" """,
        ext_sql           = None,
        formatter         = lambda arg: ['%' +
            like_escape(arg if arg.startswith(".") else "." + arg)],
        languages          = ["C"]
    ),

    TriLiteSearchFilter(),

    # function filter
    ExistsLikeFilter(
        description   = Markup('Function or method definition: <code>function:foo</code>'),
        param         = "function",
        filter_sql    = """SELECT 1 FROM functions
                           WHERE %s
                             AND functions.file_id = files.id
                        """,
        ext_sql       = """SELECT functions.extent_start, functions.extent_end FROM functions
                           WHERE functions.file_id = ?
                             AND %s
                           ORDER BY functions.extent_start
                        """,
        like_name     = "functions.name",
        qual_name     = "functions.qualname",
        languages      = ["C"]
    ),

    # function-ref filter
    ExistsLikeFilter(
        description   = 'Function or method references',
        param         = "function-ref",
        filter_sql    = """SELECT 1 FROM functions, function_refs AS refs
                           WHERE %s
                             AND functions.id = refs.refid AND refs.file_id = files.id
                        """,
        ext_sql       = """SELECT refs.extent_start, refs.extent_end FROM function_refs AS refs
                           WHERE refs.file_id = ?
                             AND EXISTS (SELECT 1 FROM functions
                                         WHERE %s
                                           AND functions.id = refs.refid)
                           ORDER BY refs.extent_start
                        """,
        like_name     = "functions.name",
        qual_name     = "functions.qualname",
        languages      = ["C"]
    ),

    # function-decl filter
    ExistsLikeFilter(
        description   = 'Function or method declaration',
        param         = "function-decl",
        filter_sql    = """SELECT 1 FROM functions, function_decldef as decldef
                           WHERE %s
                             AND functions.id = decldef.defid AND decldef.file_id = files.id
                        """,
        ext_sql       = """SELECT decldef.extent_start, decldef.extent_end FROM function_decldef AS decldef
                           WHERE decldef.file_id = ?
                             AND EXISTS (SELECT 1 FROM functions
                                         WHERE %s
                                           AND functions.id = decldef.defid)
                           ORDER BY decldef.extent_start
                        """,
        like_name     = "functions.name",
        qual_name     = "functions.qualname",
        languages      = ["C"]
    ),

    UnionFilter([
      # callers filter (direct-calls)
      ExistsLikeFilter(
          param         = "callers",
          filter_sql    = """SELECT 1
                              FROM functions as caller, functions as target, callers
                             WHERE %s
                               AND callers.targetid = target.id
                               AND callers.callerid = caller.id
                               AND caller.file_id = files.id
                          """,
          ext_sql       = """SELECT functions.extent_start, functions.extent_end
                              FROM functions
                             WHERE functions.file_id = ?
                               AND EXISTS (SELECT 1 FROM functions as target, callers
                                            WHERE %s
                                              AND callers.targetid = target.id
                                              AND callers.callerid = functions.id
                                          )
                             ORDER BY functions.extent_start
                          """,
          like_name     = "target.name",
          qual_name     = "target.qualname"
      ),

      # callers filter (indirect-calls)
      ExistsLikeFilter(
          param         = "callers",
          filter_sql    = """SELECT 1
                              FROM functions as caller, functions as target, callers, targets
                             WHERE %s
                               AND targets.funcid = target.id
                               AND targets.targetid = callers.targetid
                               AND callers.callerid = caller.id
                               AND caller.file_id = files.id
                          """,
          ext_sql       = """SELECT functions.extent_start, functions.extent_end
                              FROM functions
                             WHERE functions.file_id = ?
                               AND EXISTS (SELECT 1 FROM functions as target, callers, targets
                                            WHERE %s
                                              AND targets.funcid = target.id
                                              AND targets.targetid = callers.targetid
                                              AND callers.callerid = functions.id
                                          )
                             ORDER BY functions.extent_start
                          """,
          like_name     = "target.name",
          qual_name     = "target.qualname")],

      description = Markup('Functions which call the given function or method: <code>callers:GetStringFromName</code>'),
      languages    = ["C"]
    ),

    UnionFilter([
      # called-by filter (direct calls)
      ExistsLikeFilter(
          param         = "called-by",
          filter_sql    = """SELECT 1
                               FROM functions as target, functions as caller, callers
                              WHERE %s
                                AND callers.callerid = caller.id
                                AND callers.targetid = target.id
                                AND target.file_id = files.id
                          """,
          ext_sql       = """SELECT functions.extent_start, functions.extent_end
                              FROM functions
                             WHERE functions.file_id = ?
                               AND EXISTS (SELECT 1 FROM functions as caller, callers
                                            WHERE %s
                                              AND caller.id = callers.callerid
                                              AND callers.targetid = functions.id
                                          )
                             ORDER BY functions.extent_start
                          """,
          like_name     = "caller.name",
          qual_name     = "caller.qualname"
      ),

      # called-by filter (indirect calls)
      ExistsLikeFilter(
          param         = "called-by",
          filter_sql    = """SELECT 1
                               FROM functions as target, functions as caller, callers, targets
                              WHERE %s
                                AND callers.callerid = caller.id
                                AND targets.funcid = target.id
                                AND targets.targetid = callers.targetid
                                AND target.file_id = files.id
                          """,
          ext_sql       = """SELECT functions.extent_start, functions.extent_end
                              FROM functions
                             WHERE functions.file_id = ?
                               AND EXISTS (SELECT 1 FROM functions as caller, callers, targets
                                            WHERE %s
                                              AND caller.id = callers.callerid
                                              AND targets.funcid = functions.id
                                              AND targets.targetid = callers.targetid
                                          )
                             ORDER BY functions.extent_start
                          """,
          like_name     = "caller.name",
          qual_name     = "caller.qualname"
      )],

      description = 'Functions or methods which are called by the given one',
      languages    = ["C"]
    ),

    # type filter
    UnionFilter([
      ExistsLikeFilter(
        param         = "type",
        filter_sql    = """SELECT 1 FROM types
                           WHERE %s
                             AND types.file_id = files.id
                        """,
        ext_sql       = """SELECT types.extent_start, types.extent_end FROM types
                           WHERE types.file_id = ?
                             AND %s
                           ORDER BY types.extent_start
                        """,
        like_name     = "types.name",
        qual_name     = "types.qualname"
      ),
      ExistsLikeFilter(
        param         = "type",
        filter_sql    = """SELECT 1 FROM typedefs
                           WHERE %s
                             AND typedefs.file_id = files.id
                        """,
        ext_sql       = """SELECT typedefs.extent_start, typedefs.extent_end FROM typedefs
                           WHERE typedefs.file_id = ?
                             AND %s
                           ORDER BY typedefs.extent_start
                        """,
        like_name     = "typedefs.name",
        qual_name     = "typedefs.qualname")],
      description=Markup('Type or class definition: <code>type:Stack</code>'),
      languages   = ["C"]
    ),

    # type-ref filter
    UnionFilter([
      ExistsLikeFilter(
        param         = "type-ref",
        filter_sql    = """SELECT 1 FROM types, type_refs AS refs
                           WHERE %s
                             AND types.id = refs.refid AND refs.file_id = files.id
                        """,
        ext_sql       = """SELECT refs.extent_start, refs.extent_end FROM type_refs AS refs
                           WHERE refs.file_id = ?
                             AND EXISTS (SELECT 1 FROM types
                                         WHERE %s
                                           AND types.id = refs.refid)
                           ORDER BY refs.extent_start
                        """,
        like_name     = "types.name",
        qual_name     = "types.qualname"
      ),
      ExistsLikeFilter(
        param         = "type-ref",
        filter_sql    = """SELECT 1 FROM typedefs, typedef_refs AS refs
                           WHERE %s
                             AND typedefs.id = refs.refid AND refs.file_id = files.id
                        """,
        ext_sql       = """SELECT refs.extent_start, refs.extent_end FROM typedef_refs AS refs
                           WHERE refs.file_id = ?
                             AND EXISTS (SELECT 1 FROM typedefs
                                         WHERE %s
                                           AND typedefs.id = refs.refid)
                           ORDER BY refs.extent_start
                        """,
        like_name     = "typedefs.name",
        qual_name     = "typedefs.qualname")],
      description='Type or class references, uses, or instantiations',
      languages   = ["C"]
    ),

    # type-decl filter
    ExistsLikeFilter(
      description   = 'Type or class declaration',
      param         = "type-decl",
      languages      = ["C"],
      filter_sql    = """SELECT 1 FROM types, type_decldef AS decldef
                         WHERE %s
                           AND types.id = decldef.defid AND decldef.file_id = files.id
                      """,
      ext_sql       = """SELECT decldef.extent_start, decldef.extent_end FROM type_decldef AS decldef
                         WHERE decldef.file_id = ?
                           AND EXISTS (SELECT 1 FROM types
                                       WHERE %s
                                         AND types.id = decldef.defid)
                         ORDER BY decldef.extent_start
                      """,
      like_name     = "types.name",
      qual_name     = "types.qualname"
    ),

    # var filter
    ExistsLikeFilter(
        description   = 'Variable definition',
        param         = "var",
        filter_sql    = """SELECT 1 FROM variables
                           WHERE %s
                             AND variables.file_id = files.id
                        """,
        ext_sql       = """SELECT variables.extent_start, variables.extent_end FROM variables
                           WHERE variables.file_id = ?
                             AND %s
                           ORDER BY variables.extent_start
                        """,
        like_name     = "variables.name",
        qual_name     = "variables.qualname",
        languages      = ["C"]
    ),

    # var-ref filter
    ExistsLikeFilter(
        description   = 'Variable uses (lvalue, rvalue, dereference, etc.)',
        param         = "var-ref",
        filter_sql    = """SELECT 1 FROM variables, variable_refs AS refs
                           WHERE %s
                             AND variables.id = refs.refid AND refs.file_id = files.id
                        """,
        ext_sql       = """SELECT refs.extent_start, refs.extent_end FROM variable_refs AS refs
                           WHERE refs.file_id = ?
                             AND EXISTS (SELECT 1 FROM variables
                                         WHERE %s
                                           AND variables.id = refs.refid)
                           ORDER BY refs.extent_start
                        """,
        like_name     = "variables.name",
        qual_name     = "variables.qualname",
        languages      = ["C"]
    ),

    # var-decl filter
    ExistsLikeFilter(
        description   = 'Variable declaration',
        param         = "var-decl",
        filter_sql    = """SELECT 1 FROM variables, variable_decldef AS decldef
                           WHERE %s
                             AND variables.id = decldef.defid AND decldef.file_id = files.id
                        """,
        ext_sql       = """SELECT decldef.extent_start, decldef.extent_end FROM variable_decldef AS decldef
                           WHERE decldef.file_id = ?
                             AND EXISTS (SELECT 1 FROM variables
                                         WHERE %s
                                           AND variables.id = decldef.defid)
                           ORDER BY decldef.extent_start
                        """,
        like_name     = "variables.name",
        qual_name     = "variables.qualname",
        languages      = ["C"]
    ),

    # macro filter
    ExistsLikeFilter(
        description   = 'Macro definition',
        param         = "macro",
        filter_sql    = """SELECT 1 FROM macros
                           WHERE %s
                             AND macros.file_id = files.id
                        """,
        ext_sql       = """SELECT macros.extent_start, macros.extent_end FROM macros
                           WHERE macros.file_id = ?
                             AND %s
                           ORDER BY macros.extent_start
                        """,
        like_name     = "macros.name",
        qual_name     = "macros.name",
        languages      = ["C"]
    ),

    # macro-ref filter
    ExistsLikeFilter(
        description   = 'Macro uses',
        param         = "macro-ref",
        filter_sql    = """SELECT 1 FROM macros, macro_refs AS refs
                           WHERE %s
                             AND macros.id = refs.refid AND refs.file_id = files.id
                        """,
        ext_sql       = """SELECT refs.extent_start, refs.extent_end FROM macro_refs AS refs
                           WHERE refs.file_id = ?
                             AND EXISTS (SELECT 1 FROM macros
                                         WHERE %s
                                           AND macros.id = refs.refid)
                           ORDER BY refs.extent_start
                        """,
        like_name     = "macros.name",
        qual_name     = "macros.name",
        languages      = ["C"]
    ),

    # namespace filter
    ExistsLikeFilter(
        description   = 'Namespace definition',
        param         = "namespace",
        filter_sql    = """SELECT 1 FROM namespaces
                           WHERE %s
                             AND namespaces.file_id = files.id
                        """,
        ext_sql       = """SELECT namespaces.extent_start, namespaces.extent_end FROM namespaces
                           WHERE namespaces.file_id = ?
                             AND %s
                           ORDER BY namespaces.extent_start
                        """,
        like_name     = "namespaces.name",
        qual_name     = "namespaces.qualname",
        languages      = ["C"]
    ),

    # namespace-ref filter
    ExistsLikeFilter(
        description   = 'Namespace references',
        param         = "namespace-ref",
        filter_sql    = """SELECT 1 FROM namespaces, namespace_refs AS refs
                           WHERE %s
                             AND namespaces.id = refs.refid AND refs.file_id = files.id
                        """,
        ext_sql       = """SELECT refs.extent_start, refs.extent_end FROM namespace_refs AS refs
                           WHERE refs.file_id = ?
                             AND EXISTS (SELECT 1 FROM namespaces
                                         WHERE %s
                                           AND namespaces.id = refs.refid)
                           ORDER BY refs.extent_start
                        """,
        like_name     = "namespaces.name",
        qual_name     = "namespaces.qualname",
        languages      = ["C"]
    ),

    # namespace-alias filter
    ExistsLikeFilter(
        description   = 'Namespace alias',
        param         = "namespace-alias",
        filter_sql    = """SELECT 1 FROM namespace_aliases
                           WHERE %s
                             AND namespace_aliases.file_id = files.id
                        """,
        ext_sql       = """SELECT namespace_aliases.extent_start, namespace_aliases.extent_end FROM namespace_aliases
                           WHERE namespace_aliases.file_id = ?
                             AND %s
                           ORDER BY namespace_aliases.extent_start
                        """,
        like_name     = "namespace_aliases.name",
        qual_name     = "namespace_aliases.qualname",
        languages      = ["C"]
    ),

    # namespace-alias-ref filter
    ExistsLikeFilter(
        description   = 'Namespace alias references',
        param         = "namespace-alias-ref",
        filter_sql    = """SELECT 1 FROM namespace_aliases, namespace_alias_refs AS refs
                           WHERE %s
                             AND namespace_aliases.id = refs.refid AND refs.file_id = files.id
                        """,
        ext_sql       = """SELECT refs.extent_start, refs.extent_end FROM namespace_alias_refs AS refs
                           WHERE refs.file_id = ?
                             AND EXISTS (SELECT 1 FROM namespace_aliases
                                         WHERE %s
                                           AND namespace_aliases.id = refs.refid)
                           ORDER BY refs.extent_start
                        """,
        like_name     = "namespace_aliases.name",
        qual_name     = "namespace_aliases.qualname",
        languages      = ["C"]
    ),

    # bases filter -- reorder these things so more frequent at top.
    ExistsLikeFilter(
        description   = Markup('Superclasses of a class: <code>bases:SomeSubclass</code>'),
        param         = "bases",
        filter_sql    = """SELECT 1 FROM types as base, impl, types
                            WHERE %s
                              AND impl.tbase = base.id
                              AND impl.tderived = types.id
                              AND base.file_id = files.id""",
        ext_sql       = """SELECT base.extent_start, base.extent_end
                            FROM types as base
                           WHERE base.file_id = ?
                             AND EXISTS (SELECT 1 FROM impl, types
                                         WHERE impl.tbase = base.id
                                           AND impl.tderived = types.id
                                           AND %s
                                        )
                        """,
        like_name     = "types.name",
        qual_name     = "types.qualname",
        languages      = ["C"]
    ),

    # derived filter
    ExistsLikeFilter(
        description   = Markup('Subclasses of a class: <code>derived:SomeSuperclass</code>'),
        param         = "derived",
        filter_sql    = """SELECT 1 FROM types as sub, impl, types
                            WHERE %s
                              AND impl.tbase = types.id
                              AND impl.tderived = sub.id
                              AND sub.file_id = files.id""",
        ext_sql       = """SELECT sub.extent_start, sub.extent_end
                            FROM types as sub
                           WHERE sub.file_id = ?
                             AND EXISTS (SELECT 1 FROM impl, types
                                         WHERE impl.tbase = types.id
                                           AND impl.tderived = sub.id
                                           AND %s
                                        )
                        """,
        like_name     = "types.name",
        qual_name     = "types.qualname",
        languages      = ["C"]
   ),

    UnionFilter([
      # member filter for functions
      ExistsLikeFilter(
        param         = "member",
        filter_sql    = """SELECT 1 FROM types as type, functions as mem
                            WHERE %s
                              AND mem.scopeid = type.id AND mem.file_id = files.id
                        """,
        ext_sql       = """ SELECT extent_start, extent_end
                              FROM functions as mem WHERE mem.file_id = ?
                                      AND EXISTS ( SELECT 1 FROM types as type
                                                    WHERE %s
                                                      AND type.id = mem.scopeid)
                           ORDER BY mem.extent_start
                        """,
        like_name     = "type.name",
        qual_name     = "type.qualname"
      ),
      # member filter for types
      ExistsLikeFilter(
        param         = "member",
        filter_sql    = """SELECT 1 FROM types as type, types as mem
                            WHERE %s
                              AND mem.scopeid = type.id AND mem.file_id = files.id
                        """,
        ext_sql       = """ SELECT extent_start, extent_end
                              FROM types as mem WHERE mem.file_id = ?
                                      AND EXISTS ( SELECT 1 FROM types as type
                                                    WHERE %s
                                                      AND type.id = mem.scopeid)
                           ORDER BY mem.extent_start
                        """,
        like_name     = "type.name",
        qual_name     = "type.qualname"
      ),
      # member filter for variables
      ExistsLikeFilter(
        param         = "member",
        filter_sql    = """SELECT 1 FROM types as type, variables as mem
                            WHERE %s
                              AND mem.scopeid = type.id AND mem.file_id = files.id
                        """,
        ext_sql       = """ SELECT extent_start, extent_end
                              FROM variables as mem WHERE mem.file_id = ?
                                      AND EXISTS ( SELECT 1 FROM types as type
                                                    WHERE %s
                                                      AND type.id = mem.scopeid)
                           ORDER BY mem.extent_start
                        """,
        like_name     = "type.name",
        qual_name     = "type.qualname")],

      description = Markup('Member variables, types, or methods of a class: <code>member:SomeClass</code>'),
      languages    = ["C"]
    ),

    # overridden filter
    ExistsLikeFilter(
        description   = Markup('Methods which are overridden by the given one. Useful mostly with fully qualified methods, like <code>+overridden:Derived::foo()</code>.'),
        param         = "overridden",
        languages      = ["C"],
        filter_sql    = """SELECT 1
                             FROM functions as base, functions as derived, targets
                            WHERE %s
                              AND base.id = -targets.targetid
                              AND derived.id = targets.funcid
                              AND base.id <> derived.id
                              AND base.file_id = files.id
                        """,
        ext_sql       = """SELECT functions.extent_start, functions.extent_end
                            FROM functions
                           WHERE functions.file_id = ?
                             AND EXISTS (SELECT 1 FROM functions as derived, targets
                                          WHERE %s
                                            AND functions.id = -targets.targetid
                                            AND derived.id = targets.funcid
                                            AND functions.id <> derived.id
                                        )
                           ORDER BY functions.extent_start
                        """,
        like_name     = "derived.name",
        qual_name     = "derived.qualname"
    ),

    # overrides filter
    ExistsLikeFilter(
        description   = Markup('Methods which override the given one: <code>overrides:someMethod</code>'),
        param         = "overrides",
        filter_sql    = """SELECT 1
                             FROM functions as base, functions as derived, targets
                            WHERE %s
                              AND base.id = -targets.targetid
                              AND derived.id = targets.funcid
                              AND base.id <> derived.id
                              AND derived.file_id = files.id
                        """,
        ext_sql       = """SELECT functions.extent_start, functions.extent_end
                            FROM functions
                           WHERE functions.file_id = ?
                             AND EXISTS (SELECT 1 FROM functions as base, targets
                                          WHERE %s
                                            AND base.id = -targets.targetid
                                            AND functions.id = targets.funcid
                                            AND base.id <> functions.id
                                        )
                           ORDER BY functions.extent_start
                        """,
        like_name     = "base.name",
        qual_name     = "base.qualname",
        languages      = ["C"]
    ),

    #warning filter
    ExistsLikeFilter(
        description   = 'Compiler warning messages',
        param         = "warning",
        filter_sql    = """SELECT 1 FROM warnings
                            WHERE %s
                              AND warnings.file_id = files.id """,
        ext_sql       = """SELECT warnings.extent_start, warnings.extent_end
                             FROM warnings
                            WHERE warnings.file_id = ?
                              AND %s
                           ORDER BY warnings.extent_start
                        """,
        like_name     = "warnings.msg",
        qual_name     = "warnings.msg",
        languages      = ["C"]
    ),

    #warning-opt filter
    ExistsLikeFilter(
        description   = 'More (less severe?) warning messages',
        param         = "warning-opt",
        filter_sql    = """SELECT 1 FROM warnings
                            WHERE %s
                              AND warnings.file_id = files.id """,
        ext_sql       = """SELECT warnings.extent_start, warnings.extent_end
                             FROM warnings
                            WHERE warnings.file_id = ?
                              AND %s
                           ORDER BY warnings.extent_start
                        """,
        like_name     = "warnings.opt",
        qual_name     = "warnings.opt",
        languages      = ["C"]
    )
]


query_grammar = Grammar(ur'''
    query = _ term*
    term = not_term / positive_term
    not_term = not positive_term
    positive_term = filtered_term / text

    # A term with a filter name prepended:
    filtered_term = maybe_plus filter ":" text

    # Bare or quoted text, possibly with spaces. Not empty.
    text = (double_quoted_text / single_quoted_text / bare_text) _

    filter = ~r"''' +
        # regexp, function, etc. No filter is a prefix of a later one. This
        # avoids premature matches.
        '|'.join(sorted(chain.from_iterable(map(re.escape, f.names()) for f in filters),
                        key=len,
                        reverse=True)) + ur'''"

    not = "-"

    # You can stick a plus in front of anything, and it'll parse, but it has
    # meaning only with the filters where it makes sense.
    maybe_plus = "+"?

    # Unquoted text until a space or EOL:
    bare_text = ~r"[^ ]+"

    # A string starting with a double quote and extending to {a double quote
    # followed by a space} or {a double quote followed by the end of line} or
    # {simply the end of line}, ignoring (that is, including) backslash-escaped
    # quotes. The intent is to take quoted strings like `"hi \there"woo"` and
    # take a good guess at what you mean even while you're still typing, before
    # you've closed the quote. The motivation for providing backslash-escaping
    # is so you can express trailing quote-space pairs without having the
    # scanner prematurely end.
    double_quoted_text = ~r'"(?P<content>(?:[^"\\]*(?:\\"|\\|"[^ ])*)*)(?:"(?= )|"$|$)'
    # A symmetric rule for single quotes:
    single_quoted_text = ~r"'(?P<content>(?:[^'\\]*(?:\\'|\\|'[^ ])*)*)(?:'(?= )|'$|$)"

    _ = ~r"[ \t]*"
    ''')


class QueryVisitor(NodeVisitor):
    visit_positive_term = NodeVisitor.lift_child

    def __init__(self, is_case_sensitive=False):
        """Construct.

        :arg is_case_sensitive: What "case_sensitive" value to set on every
            term. This is meant to be temporary, until we expose per-term case
            sensitivity to the user.

        """
        super(NodeVisitor, self).__init__()
        self.is_case_sensitive = is_case_sensitive

    def visit_query(self, query, (_, terms)):
        """Group terms into a dict of lists by filter type, and return it."""
        d = {}
        for filter_name, subdict in terms:
            d.setdefault(filter_name, []).append(subdict)
        return d

    def visit_term(self, term, ((filter_name, subdict),)):
        """Set the case-sensitive bit and, if not already set, a default not
        bit."""
        subdict['case_sensitive'] = self.is_case_sensitive
        subdict.setdefault('not', False)
        subdict.setdefault('qualified', False)
        return filter_name, subdict

    def visit_not_term(self, not_term, (not_, (filter_name, subdict))):
        """Add "not" bit to the subdict."""
        subdict['not'] = True
        return filter_name, subdict

    def visit_filtered_term(self, filtered_term, (plus, filter, colon, (text_type, subdict))):
        """Add fully-qualified indicator to the term subdict, and return it and
        the filter name."""
        subdict['qualified'] = plus.text == '+'
        return filter.text, subdict

    def visit_text(self, text, ((some_text,), _)):
        """Create the subdictionary that lives in Query.terms. Return it and
        'text', indicating that this is a bare or quoted run of text. If it is
        actually an argument to a filter, ``visit_filtered_term`` will
        overrule us later.

        """
        return 'text', {'arg': some_text}

    def visit_maybe_plus(self, plus, wtf):
        """Keep the plus from turning into a list half the time. That makes it
        awkward to compare against."""
        return plus

    def visit_bare_text(self, bare_text, visited_children):
        return bare_text.text

    def visit_double_quoted_text(self, quoted_text, visited_children):
        return quoted_text.match.group('content').replace(r'\"', '"')

    def visit_single_quoted_text(self, quoted_text, visited_children):
        return quoted_text.match.group('content').replace(r"\'", "'")

    def generic_visit(self, node, visited_children):
        """Replace childbearing nodes with a list of their children; keep
        others untouched.

        """
        return visited_children or node


def filter_menu_items(language):
    """Return the additional template variables needed to render filter.html."""
    return (f.menu_item() for f in filters if f.valid_for_language(language))

########NEW FILE########
__FILENAME__ = schema
class Schema(object):
    """ A representation of SQL table data.

        This class allows for easy ways to handle SQL data given blob information,
        and is probably the preferred format for storing the schema.

        The input schema is a dictionary whose keys are the table names and whose
        values are dictionaries for table schemas.
      
        This class interprets blob data as a dictionary of tables; each table is
        either a dictionary of {key:row} elements or a list of {key:row} elements.
        The rows are dictionaries of {col:value} elements; only those values that
        are actually present in the schema will be serialized in the get_data_sql
        function. """
    def __init__(self, schema):
        """ Creates a new schema with the given definition. See the class docs for
                this and SchemaTable for what syntax looks like. """
        self.tables = {}
        for tbl in schema:
            self.tables[tbl] = SchemaTable(tbl, schema[tbl])

    def get_create_sql(self):
        """ Returns the SQL that creates the tables in this schema. """
        return '\n'.join([tbl.get_create_sql() for tbl in self.tables.itervalues()])

    def get_insert_sql(self, tblname, args):
        return self.tables[tblname].get_insert_sql(args)


class SchemaTable(object):
    """ A table schema dictionary has column names as keys and information tuples
        as values: "col": (type, mayBeNull)
          type is the type string (e.g., VARCHAR(256) or INTEGER), although it
            may have special values
          mayBeNull is an optional attribute that specifies if the column may
            contain null values. not specifying is equivalent to True
      
        Any column name that begins with a `_' is metadata about the table:
          _key: the result tuple is a tuple for the primary key of the table.

        Special values for type strings are as follows:
          _location: A file:loc[:col] value for the column. A boolean element
              in the tuple declares whether a compound index of (file ID, line,
              column) should be added.

        Since the order of columns matter in SQL and python dicts are unordered,
        we will accept a list or tuple of tuples as an alternative specifier:
        "table": [
          ("col", type, False),
          ("col2", (type, False)),
          ...
    """
    def __init__(self, tblname, tblschema):
        self.name = tblname
        self.key = None
        self.index = None
        self.fkeys = []
        self.columns = []
        self.needLang = False
        self.needFileKey = False
        defaults = ['VARCHAR(256)', True]
        for col in tblschema:
            if isinstance(tblschema, tuple) or isinstance(tblschema, list):
                col, spec = col[0], col[1:]
            else:
                spec = tblschema[col]
            if not isinstance(spec, tuple):
                spec = (spec,)
            if col == '_key':
                self.key = spec
            elif col == '_fkey':
                self.fkeys.append(spec)
            elif col == '_index':
                self.index = spec
            elif col == '_location':
                if len(spec) <= 1:
                    prefix = ''
                else:
                    prefix = spec[1] + "_"

                self.columns.append((prefix + "file_id", ["INTEGER", True]))
                self.columns.append((prefix + "file_line", ["INTEGER", True]))
                self.columns.append((prefix + "file_col", ["INTEGER", True]))
                self.needFileKey = spec[0]
            elif col[0] != '_':
                # if spec is deficient, we need to full it in with default tuples
                values = list(spec)
                if len(spec) < len(defaults):
                    values.extend(defaults[len(spec):])
                self.columns.append((col, spec))

    def get_create_sql(self):
        sql = 'DROP TABLE IF EXISTS %s;\n' % (self.name)
        sql += 'CREATE TABLE %s (\n  ' % (self.name)
        colstrs = []
        special_types = {
            '_language': 'VARCHAR(32)'
        }
        for col, spec in self.columns:
            specsql = col + ' '
            if spec[0][0] == '_':
                specsql += special_types[spec[0]]
            else:
                specsql += spec[0]
            if len(spec) > 1 and spec[1] == False:
                specsql += ' NOT NULL'
            colstrs.append(specsql)

        if self.needFileKey is True:
            colstrs.append('FOREIGN KEY (file_id) REFERENCES files(ID)')

        for spec in self.fkeys:
            colstrs.append('FOREIGN KEY (%s) REFERENCES %s(%s)' % (spec[0], spec[1], spec[2]))
        if self.key is not None:
            colstrs.append('PRIMARY KEY (%s)' % ', '.join(self.key))
        sql += ',\n  '.join(colstrs)
        sql += '\n);\n'
        if self.index is not None:
            sql += 'CREATE INDEX %s_%s_index on %s (%s);\n' % (self.name, '_'.join(self.index), self.name, ','.join(self.index))
        if self.needFileKey is True:
            has_extents = 'extent_start' in [x[0] for x in self.columns]
            sql += ('CREATE UNIQUE INDEX %s_file_index on %s (file_id, file_line, file_col%s);' %
                    (self.name, self.name, ', extent_start, extent_end' if has_extents else ''))
        return sql

    def get_insert_sql(self, args):
        colset = set(col[0] for col in self.columns)
        unwanted = []

        # Only add the keys in the columns
        for key in args.iterkeys():
            if key not in colset:
                unwanted.append(key)

        for key in unwanted:
            del args[key]

        return ('INSERT OR IGNORE INTO %s (%s) VALUES (%s)' %
                        (self.name, ','.join(args.keys()), ','.join('?' for k in range(0, len(args)))),
                        args.values())

########NEW FILE########
__FILENAME__ = testing
from commands import getstatusoutput
import json
from os import chdir, mkdir
import os.path
from os.path import dirname
from shutil import rmtree
import sys
from tempfile import mkdtemp
import unittest
from urllib2 import quote

from nose.tools import eq_

try:
    from nose.tools import assert_in
except ImportError:
    from nose.tools import ok_
    def assert_in(item, container, msg=None):
        ok_(item in container, msg=msg or '%r not in %r' % (item, container))

from dxr.app import make_app


# ---- This crap is very temporary: ----


class CommandFailure(Exception):
    """A command exited with a non-zero status code."""

    def __init__(self, command, status, output):
        self.command, self.status, self.output = command, status, output

    def __str__(self):
        return "'%s' exited with status %s. Output:\n%s" % (self.command,
                                                            self.status,
                                                            self.output)


def run(command):
    """Run a shell command, and return its stdout. On failure, raise
    `CommandFailure`.

    """
    status, output = getstatusoutput(command)
    if status:
        raise CommandFailure(command, status, output)
    return output


# ---- More permanent stuff: ----


class TestCase(unittest.TestCase):
    """Abstract container for general convenience functions for DXR tests"""

    def client(self):
        # TODO: DRY between here and the config file with 'target'.
        app = make_app(os.path.join(self._config_dir_path, 'target'))

        app.config['TESTING'] = True  # Disable error trapping during requests.
        return app.test_client()

    def found_files(self, query, is_case_sensitive=True):
        """Return the set of paths of files found by a search query."""
        return set(result['path'] for result in
                   self.search_results(query,
                                       is_case_sensitive=is_case_sensitive))

    def found_files_eq(self, query, filenames, is_case_sensitive=True):
        """Assert that executing the search ``query`` finds the paths
        ``filenames``."""
        eq_(self.found_files(query,
                             is_case_sensitive=is_case_sensitive),
            set(filenames))

    def found_line_eq(self, query, content, line):
        """Assert that a query returns a single file and single matching line
        and that its line number and content are as expected, modulo leading
        and trailing whitespace.

        This is a convenience function for searches that return only one
        matching file and only one line within it so you don't have to do a
        zillion dereferences in your test.

        """
        self.found_lines_eq(query, [(content, line)])

    def found_lines_eq(self, query, success_lines):
        """Assert that a query returns a single file and that the highlighted
        lines are as expected, modulo leading and trailing whitespace."""
        results = self.search_results(query)
        num_results = len(results)
        eq_(num_results, 1, msg='Query passed to found_lines_eq() returned '
                                 '%s files, not one.' % num_results)
        lines = results[0]['lines']
        eq_([(line['line'].strip(), line['line_number']) for line in lines],
            success_lines)

    def found_nothing(self, query, is_case_sensitive=True):
        """Assert that a query returns no hits."""
        results = self.search_results(query,
                                      is_case_sensitive=is_case_sensitive)
        eq_(results, [])

    def search_results(self, query, is_case_sensitive=True):
        """Return the raw results of a JSON search query.

        Example::

          [
            {
              "path": "main.c",
              "lines": [
                {
                  "line_number": 7,
                  "line": "int <b>main</b>(int argc, char* argv[]) {"
                }
              ],
              "icon": "mimetypes/c"
            }
          ]

        """
        response = self.client().get(
            '/code/search?format=json&q=%s&redirect=false&case=%s' %
            (quote(query), 'true' if is_case_sensitive else 'false'))
        return json.loads(response.data)['results']


class DxrInstanceTestCase(TestCase):
    """Test case which builds an actual DXR instance that lives on the
    filesystem and then runs its tests

    This is suitable for complex tests with many files where the FS is the
    least confusing place to express them.

    """
    @classmethod
    def setup_class(cls):
        """Build the instance."""
        # nose does some amazing magic that makes this work even if there are
        # multiple test modules with the same name:
        cls._config_dir_path = dirname(sys.modules[cls.__module__].__file__)
        chdir(cls._config_dir_path)
        run('make')

    @classmethod
    def teardown_class(cls):
        chdir(cls._config_dir_path)
        run('make clean')


class SingleFileTestCase(TestCase):
    """Container for tests that need only a single source file

    You can express the source as a string rather than creating a whole bunch
    of files in the FS. I'll slam it down into a temporary DXR instance and
    then kick off the usual build process, deleting the instance afterward.

    """
    # Set this to False in a subclass to keep the generated instance around and
    # print its path so you can examine it:
    should_delete_instance = True

    @classmethod
    def setup_class(cls):
        """Create a temporary DXR instance on the FS, and build it."""
        cls._config_dir_path = mkdtemp()
        code_path = os.path.join(cls._config_dir_path, 'code')
        mkdir(code_path)
        _make_file(code_path, 'main.cpp', cls.source)
        # $CXX gets injected by the clang DXR plugin:
        _make_file(cls._config_dir_path, 'dxr.config', """
[DXR]
enabled_plugins = pygmentize clang
temp_folder = {config_dir_path}/temp
target_folder = {config_dir_path}/target
nb_jobs = 4

[code]
source_folder = {config_dir_path}/code
object_folder = {config_dir_path}/code
build_command = $CXX -o main main.cpp
""".format(config_dir_path=cls._config_dir_path))

        chdir(cls._config_dir_path)
        run('dxr-build.py')

    @classmethod
    def teardown_class(cls):
        if cls.should_delete_instance:
            rmtree(cls._config_dir_path)
        else:
            print 'Not deleting instance in %s.' % cls._config_dir_path

    def _source_for_query(self, s):
        return (s.replace('<b>', '')
                 .replace('</b>', '')
                 .replace('&lt;', '<')
                 .replace('&gt;', '>')
                 .replace('&quot;', '"')
                 .replace('&amp;', '&'))

    def found_line_eq(self, query, content, line=None):
        """A specialization of ``found_line_eq`` that computes the line number
        if not given

        :arg line: The expected line number. If omitted, we'll compute it,
            given a match for ``content`` (minus ``<b>`` tags) in
            ``self.source``.

        """
        if not line:
            line = self.source.count( '\n', 0, self.source.index(
                self._source_for_query(content))) + 1
        super(SingleFileTestCase, self).found_line_eq(query, content, line)


def _make_file(path, filename, contents):
    """Make file ``filename`` within ``path``, full of unicode ``contents``."""
    with open(os.path.join(path, filename), 'w') as file:
        file.write(contents.encode('utf-8'))


# Tests that don't otherwise need a main() can append this one just to get
# their code to compile:
MINIMAL_MAIN = """
    int main(int argc, char* argv[]) {
        return 0;
    }
    """

########NEW FILE########
__FILENAME__ = utils
import ctypes

# Load the trilite plugin.
#
# If you ``import sqlite3`` before doing this, it's likely that the system
# version of sqlite will be loaded, and then trilite, if built against a
# different version, will fail to load. If you're having trouble getting
# trilite to load, make sure you're not importing sqlite3 beforehand. Afterward
# is fine.
ctypes.CDLL('libtrilite.so').load_trilite_extension()

import os
from os import dup
from os.path import join
import jinja2
import sqlite3
import string
from sys import stdout
from urllib import quote, quote_plus


TEMPLATE_DIR = 'static/templates'

_template_env = None
def load_template_env(temp_folder, dxr_root):
    """Load template environment (lazily)"""
    global _template_env
    if not _template_env:
        # Cache folder for jinja2
        tmpl_cache = os.path.join(temp_folder, 'jinja2_cache')
        if not os.path.isdir(tmpl_cache):
            os.mkdir(tmpl_cache)
        # Create jinja2 environment
        _template_env = jinja2.Environment(
                loader=jinja2.FileSystemLoader(
                        join(dxr_root, TEMPLATE_DIR)),
                auto_reload=False,
                bytecode_cache=jinja2.FileSystemBytecodeCache(tmpl_cache),
                autoescape=lambda template_name: template_name is None or template_name.endswith('.html')
        )
    return _template_env


_next_id = 1
def next_global_id():
    """Source of unique ids"""
    #TODO Please stop using this, it makes distribution and parallelization hard
    # Also it's just stupid!!! When whatever SQL database we use supports this
    global _next_id
    n = _next_id
    _next_id += 1
    return n


def open_log(config_or_tree, name, use_stdout=False):
    """Return a writable file-like object representing a log file.

    :arg config_or_tree: a Config or Tree object which tells us which folder to
        put the log file in
    :arg name: The name of the log file
    :arg use_stdout: If True, return a handle to stdout for verbose output,
        duplicated so it can be closed with impunity.

    """
    if use_stdout:
        return os.fdopen(dup(stdout.fileno()), 'w')
    return open(os.path.join(config_or_tree.log_folder, name), 'w', 1)


def non_negative_int(s, default):
    """Parse a string into an int >= 0. If parsing fails or the result is out
    of bounds, return a default."""
    try:
        i = int(s)
        if i >= 0:
            return i
    except (ValueError, TypeError):
        pass
    return default


def search_url(www_root, tree, query, **query_string_params):
    """Return the URL to the search endpoint."""
    ret = '%s/%s/search?q=%s' % (www_root,
                                 quote(tree),
                                 # quote_plus needs a string.
                                 quote_plus(query.encode('utf-8')))
    for key, value in query_string_params.iteritems():
        if value is not None:
            ret += '&%s=%s' % (key, ('true' if value else 'false'))
    return ret


def browse_url(tree, www_root, path):
    """Return a URL that will redirect to a given path in a given tree."""
    return quote_plus('{www_root}/{tree}/parallel/{path}'.format(
                          www_root=www_root,
                          tree=tree,
                          path=path),
                      '/')
    # TODO: Stop punting on path components that actually have '/' in them
    # once we define a consistent handling of escapes in build.py. Same for
    # search_url().


def connect_db(dir):
    """Return the database connection for a tree.

    :arg dir: The directory containing the .dxr-xref.sqlite file

    """
    conn = sqlite3.connect(join(dir, ".dxr-xref.sqlite"))
    conn.text_factory = str
    conn.execute("PRAGMA synchronous=off")
    conn.execute("PRAGMA page_size=32768")
    conn.row_factory = sqlite3.Row
    return conn

########NEW FILE########
__FILENAME__ = wsgi
from dxr.app import make_app
import os


def application(environ, start_response):
    """Pull the instance path out of an env var, and then instantiate the WSGI
    app as normal.

    This prefers the Apache SetEnv sort of environment; but if that's missing,
    try the process-level env var instead since it's easier to set for some
    users, like those using Stackato.

    """
    try:
        dxr_folder = environ['DXR_FOLDER']
    except KeyError:
        # Not found in WSGI env. Try process env:
        # If this still fails, this is a fatal error.
        dxr_folder = os.environ['DXR_FOLDER']
    return make_app(dxr_folder)(environ, start_response)

########NEW FILE########
__FILENAME__ = peep
#!/usr/bin/env python
"""peep ("prudently examine every package") verifies that packages conform to a
trusted, locally stored hash and only then installs them::

    peep install -r requirements.txt

This makes your deployments verifiably repeatable without having to maintain a
local PyPI mirror or use a vendor lib. Just update the version numbers and
hashes in requirements.txt, and you're all set.

"""
from base64 import urlsafe_b64encode
from contextlib import contextmanager
from hashlib import sha256
from itertools import chain
from linecache import getline
from optparse import OptionParser
from os import listdir
from os.path import join, basename
import re
import shlex
from shutil import rmtree
from sys import argv, exit
from tempfile import mkdtemp

from pkg_resources import require, VersionConflict, DistributionNotFound

# We don't admit our dependency on pip in setup.py, lest a naive user simply
# say `pip install peep.tar.gz` and thus pull down an untrusted copy of pip
# from PyPI. Instead, we make sure it's installed and new enough here and spit
# out an error message if not:
def activate(specifier):
    """Make a compatible version of pip importable. Raise a RuntimeError if we
    couldn't."""
    try:
        for distro in require(specifier):
            distro.activate()
    except (VersionConflict, DistributionNotFound):
        raise RuntimeError('The installed version of pip is too old; peep '
                           'requires ' + specifier)

activate('pip>=0.6.2')  # Before 0.6.2, the log module wasn't there, so some
                        # of our monkeypatching fails. It probably wouldn't be
                        # much work to support even earlier, though.

import pip
from pip.log import logger
from pip.req import parse_requirements


__version__ = 1, 0, 0


ITS_FINE_ITS_FINE = 0
SOMETHING_WENT_WRONG = 1
# "Traditional" for command-line errors according to optparse docs:
COMMAND_LINE_ERROR = 2


class PipException(Exception):
    """When I delegated to pip, it exited with an error."""

    def __init__(self, error_code):
        self.error_code = error_code


def encoded_hash(sha):
    """Return a short, 7-bit-safe representation of a hash.

    If you pass a sha256, this results in the hash algorithm that the Wheel
    format (PEP 427) uses, except here it's intended to be run across the
    downloaded archive before unpacking.

    """
    return urlsafe_b64encode(sha.digest()).rstrip('=')


@contextmanager
def ephemeral_dir():
    dir = mkdtemp(prefix='peep-')
    try:
        yield dir
    finally:
        rmtree(dir)


def run_pip(initial_args):
    """Delegate to pip the given args (starting with the subcommand), and raise
    ``PipException`` if something goes wrong."""
    status_code = pip.main(initial_args=initial_args)

    # Clear out the registrations in the pip "logger" singleton. Otherwise,
    # loggers keep getting appended to it with every run. Pip assumes only one
    # command invocation will happen per interpreter lifetime.
    logger.consumers = []

    if status_code:
        raise PipException(status_code)


def pip_download(req, argv, temp_path):
    """Download a package, and return its filename.

    :arg req: The InstallRequirement which describes the package
    :arg argv: Arguments to be passed along to pip, starting after the
        subcommand
    :arg temp_path: The path to the directory to download to

    """
    # Get the original line out of the reqs file:
    line = getline(*requirements_path_and_line(req))

    # Remove any requirement file args.
    argv = (['install', '--no-deps', '--download', temp_path] +
            list(requirement_args(argv, want_other=True)) +  # other args
            shlex.split(line))  # ['nose==1.3.0']. split() removes trailing \n.

    # Remember what was in the dir so we can backtrack and tell what we've
    # downloaded (disgusting):
    old_contents = set(listdir(temp_path))

    # pip downloads the tarball into a second temp dir it creates, then it
    # copies it to our specified download dir, then it unpacks it into the
    # build dir in the venv (probably to read metadata out of it), then it
    # deletes that. Don't be afraid: the tarball we're hashing is the pristine
    # one downloaded from PyPI, not a fresh tarring of unpacked files.
    run_pip(argv)

    return (set(listdir(temp_path)) - old_contents).pop()


def pip_install_archives_from(temp_path):
    """pip install the archives from the ``temp_path`` dir, omitting
    dependencies."""
    # TODO: Make this preserve any pip options passed in, but strip off -r
    # options and other things that don't make sense at this point in the
    # process.
    for filename in listdir(temp_path):
        archive_path = join(temp_path, filename)
        run_pip(['install', '--no-deps', archive_path])


def hash_of_file(path):
    """Return the hash of a downloaded file."""
    with open(path, 'r') as archive:
        sha = sha256()
        while True:
            data = archive.read(2 ** 20)
            if not data:
                break
            sha.update(data)
    return encoded_hash(sha)


def version_of_archive(filename, package_name):
    """Deduce the version number of a downloaded package from its filename."""
    # Since we know the project_name, we can strip that off the left, strip any
    # archive extensions off the right, and take the rest as the version.
    # And for Wheel files (http://legacy.python.org/dev/peps/pep-0427/#file-name-convention)
    # we know the format bits are '-' separated.
    if filename.endswith('.whl'):
        whl_package_name, version, _rest = filename.split('-', 2)
        # Do the alteration to package_name from PEP 427:
        our_package_name = re.sub(r'[^\w\d.]+', '_', package_name, re.UNICODE)
        if whl_package_name != our_package_name:
            raise RuntimeError("The archive '%s' didn't start with the package name '%s', so I couldn't figure out the version number. My bad; improve me." %
                               (filename, whl_package_name))
        return version

    extensions = ['.tar.gz', '.tgz', '.tar', '.zip']
    for ext in extensions:
        if filename.endswith(ext):
            filename = filename[:-len(ext)]
            break
    if not filename.startswith(package_name):
        # TODO: What about safe/unsafe names?
        raise RuntimeError("The archive '%s' didn't start with the package name '%s', so I couldn't figure out the version number. My bad; improve me." %
                           (filename, package_name))
    return filename[len(package_name) + 1:]  # Strip off '-' before version.


def requirement_args(argv, want_paths=False, want_other=False):
    """Return an iterable of filtered arguments.

    :arg want_paths: If True, the returned iterable includes the paths to any
        requirements files following a ``-r`` or ``--requirement`` option.
    :arg want_other: If True, the returned iterable includes the args that are
        not a requirement-file path or a ``-r`` or ``--requirement`` flag.

    """
    was_r = False
    for arg in argv:
        # Allow for requirements files named "-r", don't freak out if there's a
        # trailing "-r", etc.
        if was_r:
            if want_paths:
                yield arg
            was_r = False
        elif arg in ['-r', '--requirement']:
            was_r = True
        else:
            if want_other:
                yield arg


def requirements_path_and_line(req):
    """Return the path and line number of the file from which an
    InstallRequirement came."""
    path, line = (re.match(r'-r (.*) \(line (\d+)\)$',
                  req.comes_from).groups())
    return path, int(line)


def hashes_of_requirements(requirements):
    """Return a map of package names to lists of known-good hashes, given
    multiple requirements files."""
    def hashes_above(path, line_number):
        """Yield hashes from contiguous comment lines before line
        ``line_number``."""
        for line_number in xrange(line_number - 1, 0, -1):
            # If we hit a non-comment line, abort:
            line = getline(path, line_number)
            if not line.startswith('#'):
                break

            # If it's a hash line, add it to the pile:
            if line.startswith('# sha256: '):
                yield line.split(':', 1)[1].strip()

    expected_hashes = {}
    missing_hashes = []

    for req in requirements:  # InstallRequirements
        path, line_number = requirements_path_and_line(req)
        hashes = list(hashes_above(path, line_number))
        if hashes:
            hashes.reverse()  # because we read them backwards
            expected_hashes[req.name] = hashes
        else:
            missing_hashes.append(req.name)
    return expected_hashes, missing_hashes


def hash_mismatches(expected_hash_map, downloaded_hashes):
    """Yield the list of allowed hashes, package name, and download-hash of
    each package whose download-hash didn't match one allowed for it in the
    requirements file.

    If a package is missing from ``download_hashes``, ignore it; that means
    it's already installed and we're not risking anything.

    """
    for package_name, expected_hashes in expected_hash_map.iteritems():
        try:
            hash_of_download = downloaded_hashes[package_name]
        except KeyError:
            pass
        else:
            if hash_of_download not in expected_hashes:
                yield expected_hashes, package_name, hash_of_download


def peep_hash(argv):
    """Return the peep hash of one or more files, returning a shell status code
    or raising a PipException.

    :arg argv: The commandline args, starting after the subcommand

    """
    parser = OptionParser(
        usage='usage: %prog hash file [file ...]',
        description='Print a peep hash line for one or more files: for '
                    'example, "# sha256: '
                    'oz42dZy6Gowxw8AelDtO4gRgTW_xPdooH484k7I5EOY".')
    _, paths = parser.parse_args(args=argv)
    if paths:
        for path in paths:
            print '# sha256:', hash_of_file(path)
        return ITS_FINE_ITS_FINE
    else:
        parser.print_usage()
        return COMMAND_LINE_ERROR


class EmptyOptions(object):
    """Fake optparse options for compatibility with pip<1.2

    pip<1.2 had a bug in parse_requirments() in which the ``options`` kwarg
    was required. We work around that by passing it a mock object.

    """
    default_vcs = None
    skip_requirements_regex = None


def peep_install(argv):
    """Perform the ``peep install`` subcommand, returning a shell status code
    or raising a PipException.

    :arg argv: The commandline args, starting after the subcommand

    """
    req_paths = list(requirement_args(argv, want_paths=True))
    if not req_paths:
        print "You have to specify one or more requirements files with the -r option, because"
        print "otherwise there's nowhere for peep to look up the hashes."
        return COMMAND_LINE_ERROR

    # We're a "peep install" command, and we have some requirement paths.
    requirements = list(chain(*(parse_requirements(path,
                                                   options=EmptyOptions())
                                for path in req_paths)))
    downloaded_hashes, downloaded_versions, satisfied_reqs = {}, {}, []
    with ephemeral_dir() as temp_path:
        for req in requirements:
            req.check_if_exists()
            if req.satisfied_by:  # This is already installed.
                satisfied_reqs.append(req)
            else:
                name = req.req.project_name
                archive_filename = pip_download(req, argv, temp_path)
                downloaded_hashes[name] = hash_of_file(join(temp_path, archive_filename))
                downloaded_versions[name] = version_of_archive(archive_filename, name)

        expected_hashes, missing_hashes = hashes_of_requirements(requirements)
        mismatches = list(hash_mismatches(expected_hashes, downloaded_hashes))

        # Remove satisfied_reqs from missing_hashes, preserving order:
        satisfied_req_names = set(req.name for req in satisfied_reqs)
        missing_hashes = [m for m in missing_hashes if m not in satisfied_req_names]

        # Skip a line after pip's "Cleaning up..." so the important stuff
        # stands out:
        if mismatches or missing_hashes:
            print

        # Mismatched hashes:
        if mismatches:
            print "THE FOLLOWING PACKAGES DIDN'T MATCHES THE HASHES SPECIFIED IN THE REQUIREMENTS"
            print "FILE. If you have updated the package versions, update the hashes. If not,"
            print "freak out, because someone has tampered with the packages.\n"
        for expected_hashes, package_name, hash_of_download in mismatches:
            hash_of_download = downloaded_hashes[package_name]
            preamble = '    %s: expected%s' % (
                    package_name,
                    ' one of' if len(expected_hashes) > 1 else '')
            print preamble,
            print ('\n' + ' ' * (len(preamble) + 1)).join(expected_hashes)
            print ' ' * (len(preamble) - 4), 'got', hash_of_download
        if mismatches:
            print  # Skip a line before "Not proceeding..."

        # Missing hashes:
        if missing_hashes:
            print 'The following packages had no hashes specified in the requirements file, which'
            print 'leaves them open to tampering. Vet these packages to your satisfaction, then'
            print 'add these "sha256" lines like so:\n'
        for package_name in missing_hashes:
            print '# sha256: %s' % downloaded_hashes[package_name]
            print '%s==%s\n' % (package_name,
                                downloaded_versions[package_name])

        if mismatches or missing_hashes:
            print '-------------------------------'
            print 'Not proceeding to installation.'
            return SOMETHING_WENT_WRONG
        else:
            pip_install_archives_from(temp_path)

            if satisfied_reqs:
                print "These packages were already installed, so we didn't need to download or build"
                print "them again. If you installed them with peep in the first place, you should be"
                print "safe. If not, uninstall them, then re-attempt your install with peep."
                for req in satisfied_reqs:
                    print '   ', req.req

    return ITS_FINE_ITS_FINE


def main():
    """Be the top-level entrypoint. Return a shell status code."""
    commands = {'hash': peep_hash,
                'install': peep_install}
    try:
        if len(argv) >= 2 and argv[1] in commands:
            return commands[argv[1]](argv[2:])
        else:
            # Fall through to top-level pip main() for everything else:
            return pip.main()
    except PipException as exc:
        return exc.error_code

if __name__ == '__main__':
    exit(main())

########NEW FILE########
__FILENAME__ = test_anon_ns
from dxr.testing import DxrInstanceTestCase


class AnonymousNamespaceTests(DxrInstanceTestCase):
    """Tests for anonymous namespaces"""

    def test_function(self):
        self.found_line_eq('+function:"<anonymous namespace in main.cpp>::foo()"',
                           'void <b>foo</b>() /* in main */', 5)
        self.found_line_eq('+function:"<anonymous namespace in main2.cpp>::foo()"',
                           'void <b>foo</b>() /* in main2 */', 5)

    def test_function_ref(self):
        self.found_line_eq('+function-ref:"<anonymous namespace in main.cpp>::foo()"',
                           '<b>foo</b>();  /* calling foo in main */', 12)
        self.found_line_eq('+function-ref:"<anonymous namespace in main2.cpp>::foo()"',
                           '<b>foo</b>();  /* calling foo in main2 */', 12)

########NEW FILE########
__FILENAME__ = test_bad_symlink
from dxr.testing import DxrInstanceTestCase


class BadSymlinkTests(DxrInstanceTestCase):
    def test_missing_target(self):
        """Tolerate symlinks that point to nonexistent files or dirs.
        
        This actually happens in mozilla-central from time to time.
        
        """
        # If we get here, the build succeeded, which is most of the test. But
        # let's make sure we indexed the good file while we're at it:
        self.found_files_eq('happily', ['README.mkd'])

########NEW FILE########
__FILENAME__ = test_basic
from dxr.testing import DxrInstanceTestCase

from nose.tools import eq_, ok_


class BasicTests(DxrInstanceTestCase):
    """Tests for functionality that isn't specific to particular filters"""

    def test_text(self):
        """Assert that a plain text search works."""
        self.found_files_eq('main', ['main.c', 'makefile'])

    def test_case_sensitive(self):
        """Make sure case-sensitive searching is case-sensitive.

        This tests trilite's substr-extents query type.

        """
        self.found_files_eq('really',
                            ['README.mkd'],
                            is_case_sensitive=True)
        self.found_nothing('REALLY',
                           is_case_sensitive=True)

    def test_case_insensitive(self):
        """Test case-insensitive free-text searching without extents.

        This tests trilite's isubstr query type.

        """
        found_paths = self.found_files(
            '-MAIN', is_case_sensitive=False)
        ok_('main.c' not in found_paths)
        ok_('makefile' not in found_paths)

    def test_case_insensitive_extents(self):
        """Test case-insensitive free-text searching with extents.

        This tests trilite's isubstr-extents query type.

        """
        self.found_files_eq('MAIN',
                            ['main.c', 'makefile'],
                            is_case_sensitive=False)

    def test_index(self):
        """Make sure the index controller redirects."""
        response = self.client().get('/')
        eq_(response.status_code, 302)
        ok_(response.headers['Location'].endswith('/code/source/'))

########NEW FILE########
__FILENAME__ = test_build
"""Tests for the machinery that takes offsets and markup bits from plugins and
decorates source code with them to create HTML"""

from unittest import TestCase
import warnings
from warnings import catch_warnings

from nose.tools import eq_

from dxr.build import (line_boundaries, remove_overlapping_refs, Region, LINE,
                       Ref, balanced_tags, build_lines, tag_boundaries,
                       html_lines, nesting_order, balanced_tags_with_empties,
                       lines_and_annotations)


def test_line_boundaries():
    """Make sure we find the correct line boundaries with all sorts of line
    endings, even in files that don't end with a newline."""
    eq_(list((point, is_start) for point, is_start, _ in
             line_boundaries('abc\ndef\r\nghi\rjkl')),
        [(4, False),
         (9, False),
         (13, False),
         (16, False)])


class RemoveOverlappingTests(TestCase):
    def test_misbalanced(self):
        """Make sure we cleanly excise a tag pair from a pair of interleaved
        tags."""
        # A  _________          (2, 6)
        # B        ____________ (5, 9)
        a = Ref('a')
        b = Ref('b')
        tags = [(2, True, a),
                (5, True, b),
                (6, False, a),
                (9, False, b)]
        with catch_warnings():
            warnings.simplefilter('ignore')
            remove_overlapping_refs(tags)
        eq_(tags, [(2, True, a), (6, False, a)])

    def test_overlapping_regions(self):
        """Regions (as opposed to refs) are allowed to overlap and shouldn't be
        disturbed::

            A           _________          (2, 6)
            B (region)        ____________ (5, 9)

        """
        a = Ref('a')
        b = Region('b')
        tags = [(2, True, a),
                (5, True, b),
                (6, False, a),
                (9, False, b)]
        original_tags = tags[:]
        remove_overlapping_refs(tags)
        eq_(tags, original_tags)


def spaced_tags(tags):
    """Render (point, is_start, payload) triples as human-readable
    representations."""
    segments = []
    for point, is_start, payload in tags:
        segments.append(' ' * point + ('<%s%s>' % ('' if is_start else '/',
                                                   'L' if payload is LINE else
                                                        payload.payload)))
    return '\n'.join(segments)


def tags_from_text(text):
    """Return unsorted tags based on an ASCII art representation."""
    for line in text.splitlines():
        start = line.find('_')
        label, prespace, underscores = line[0], line[2:start], line[start:]
        ref = Region(label)
        yield len(prespace), True, ref
        yield len(prespace) + len(underscores) - 1, False, ref


def test_tags_from_text():
    # str() so the Region objs compare equal
    eq_(str(list(tags_from_text('a ______________\n'
                                'b ______\n'
                                'c     _____'))),
        '[(0, True, Region("a")), (13, False, Region("a")), '
        '(0, True, Region("b")), (5, False, Region("b")), '
        '(4, True, Region("c")), (8, False, Region("c"))]')


class BalancedTagTests(TestCase):
    def test_horrors(self):
        """Try a fairly horrific scenario::

            A _______________            (0, 7)
            B     _________              (2, 6)
            C           ____________     (5, 9)
            D                    _______ (8, 11)
            E                         __ (10, 11)
              0   2     5 6 7    8 9

        A contains B. B closes while C's still going on. D and E end at the
        same time. There's even a Region in there.

        """
        a, b, c, d, e = Ref('a'), Region('b'), Ref('c'), Ref('d'), Ref('e')
        tags = [(0, True, a), (2, True, b), (5, True, c), (6, False, b),
                (7, False, a), (8, True, d), (9, False, c), (10, True, e),
                (11, False, e), (11, False, d)]

        eq_(spaced_tags(balanced_tags(tags)),
            '<L>\n'
            '<a>\n'
            '  <b>\n'
            '     <c>\n'
            '      </c>\n'
            '      </b>\n'
            '      <c>\n'
            '       </c>\n'
            '       </a>\n'
            '       <c>\n'
            '        <d>\n'
            '         </d>\n'
            '         </c>\n'
            '         <d>\n'
            '          <e>\n'
            '           </e>\n'
            '           </d>\n'
            '           </L>')

    def test_coincident(self):
        """We shouldn't emit pointless empty tags when tempted to."""
        tags = sorted(tags_from_text('a _____\n'
                                     'b _____\n'
                                     'c _____\n'), key=nesting_order)
        eq_(spaced_tags(balanced_tags(tags)),
            '<L>\n'
            '<a>\n'
            '<b>\n'
            '<c>\n'
            '    </c>\n'
            '    </b>\n'
            '    </a>\n'
            '    </L>')

    def test_coincident_ends(self):
        """We shouldn't emit empty tags even when coincidently-ending tags
        don't start together."""
        # These Regions aren't in startpoint order. That makes tags_from_test()
        # instantiate them in a funny order, which makes them sort in the wrong
        # order, which is realistic.
        tags = sorted(tags_from_text('d      _______\n'
                                     'c    _________\n'
                                     'b  ___________\n'
                                     'a ____________\n'
                                     'e     ___________\n'), key=nesting_order)
        eq_(spaced_tags(balanced_tags(tags)),
            '<L>\n'
            '<a>\n'
            ' <b>\n'
            '   <c>\n'
            '    <e>\n'
            '     <d>\n'
            '           </d>\n'
            '           </e>\n'
            '           </c>\n'
            '           </b>\n'
            '           </a>\n'
            '           <e>\n'
            '              </e>\n'
            '              </L>')

    def test_multiline_comment(self):
        """Multi-line spans should close at the end of one line and reopen at
        the beginning of the next."""
        c = Region('c')
        c2 = Region('c')
        l = LINE
        tags = [(0, True, c),
                (79, False, c),
                (80, False, l),

                (80, True, c2),
                (151, False, l),

                (222, False, l),

                (284, False, c2),
                (285, False, l),

                (286, False, l)]
        text = u"""/* -*- Mode: C++; tab-width: 2; indent-tabs-mode: nil; c-basic-offset: 2 -*- */
/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

"""
        eq_(list(html_lines(balanced_tags(tags), text.__getslice__)),
            ['<span class="c">/* -*- Mode: C++; tab-width: 2; indent-tabs-mode: nil; c-basic-offset: 2 -*- */</span>',
             '<span class="c">/* This Source Code Form is subject to the terms of the Mozilla Public</span>',
             '<span class="c"> * License, v. 2.0. If a copy of the MPL was not distributed with this</span>',
             '<span class="c"> * file, You can obtain one at http://mozilla.org/MPL/2.0/. */</span>',
             ''])


    def test_empty(self):
        """Some files are empty. Make sure they work."""
        eq_(list(balanced_tags([])), [])


class Htmlifier(object):
    def __init__(self, regions=None, refs=None, annotations=None):
        self._regions = regions or []
        self._refs = refs or []
        self._annotations = annotations or []

    def regions(self):
        return self._regions

    def refs(self):
        return self._refs

    def annotations(self):
        return self._annotations


def test_tag_boundaries():
    """Sanity-check ``tag_boundaries()``."""
    eq_(str(list(tag_boundaries([Htmlifier(regions=[(0, 3, 'a'), (3, 5, 'b')])]))),
        '[(0, True, Region("a")), (3, False, Region("a")), '
        '(3, True, Region("b")), (5, False, Region("b"))]')


def test_simple_html_lines():
    """See if the offsets are right in simple HTML stitching."""
    a = Region('a')
    b = Region('b')
    line = LINE
    eq_(''.join(html_lines([(0, True, line),
                            (0, True, a), (3, False, a),
                            (3, True, b), (5, False, b),
                            (5, False, line)],
                           'hello'.__getslice__)),
        '<span class="a">hel</span><span class="b">lo</span>')


class AnnotationsTests(TestCase):
    def _expand_group(self, group):
        """Turn ``group_by``'s annoying iterators into something we can test
        equality against."""
        return [(k, list(v)) for k, v in group]

    def test_sanity(self):
        """Make sure annotations are pulled from htmlifiers and paired with HTML
        lines sanely, handling sparsely distributed annotations and multiple
        htmlifiers annotating a single line."""
        h1 = Htmlifier(annotations=[(1, {'a': 'b'}), (3, {'e': 'f'}), (6, {'g': 'h'})])
        h2 = Htmlifier(annotations=[(1, {'c': 'd'})])

        results = self._expand_group(lines_and_annotations(
                    ['one', 'two', 'three', 'four', 'five', 'six'], [h1, h2]))
        eq_(results,
            [('one', [{'a': 'b'}, {'c': 'd'}]),
             ('two', []),
             ('three', [{'e': 'f'}]),
             ('four', []),
             ('five', []),
             ('six', [{'g': 'h'}])])

    def test_jump_ahead(self):
        """Make sure annotations show up on the correct line even when there is
        no annotation for the first line."""
        h1 = Htmlifier(annotations=[(3, {'e': 'f'})])

        results = self._expand_group(lines_and_annotations(
                    ['one', 'two', 'three', 'four'], [h1]))
        eq_(results,
            [('one', []),
             ('two', []),
             ('three', [{'e': 'f'}]),
             ('four', [])])

    def test_none(self):
        """If there are no annotations, or if the annotations run short of the
        lines, don't stop emitting lines."""
        eq_(self._expand_group(lines_and_annotations(['one', 'two'], [Htmlifier(annotations=[])])),
            [('one', []),
             ('two', [])])


class IntegrationTests(TestCase):
    """Tests for several layers at once, though not necessarily all of them"""

    def test_simple(self):
        """Sanity-check build_lines, which ties the whole shootin' match
        together."""
        eq_(''.join(build_lines('hello',
                                [Htmlifier(regions=[(0, 3, 'a'), (3, 5, 'b')])])),
            u'<span class="a">hel</span><span class="b">lo</span>')

    def test_split_anchor_avoidance(self):
        """Don't split anchor tags when we can avoid it."""
        eq_(''.join(build_lines('this that',
                                [Htmlifier(regions=[(0, 4, 'k')],
                                           refs=[(0, 9, ({}, '', None))])])),
            u'<a data-menu="{}"><span class="k">this</span> that</a>')

    def test_split_anchor_across_lines(self):
        """Support unavoidable splits of an anchor across lines."""
        eq_(list(build_lines('this\nthat',
                             [Htmlifier(refs=[(0, 9, ({}, '', None))])])),
            [u'<a data-menu="{}">this</a>', u'<a data-menu="{}">that</a>'])

    def test_horrors(self):
        """Untangle a circus of interleaved tags, tags that start where others
        end, and other untold wretchedness."""
        # This is a little brittle. All we really want to test is that each
        # span of text is within the right spans. We don't care what order the
        # span tags are in.
        eq_(list(build_lines('this&that',
                             [Htmlifier(regions=[(0, 9, 'a'), (1, 8, 'b'),
                                                 (4, 7, 'c'), (3, 4, 'd'),
                                                 (3, 5, 'e'), (0, 4, 'm'),
                                                 (5, 9, 'n')])])),
            [u'<span class="a"><span class="m">t<span class="b">hi<span class="d"><span class="e">s</span></span></span></span><span class="b"><span class="e"><span class="c">&amp;</span></span><span class="c"><span class="n">th</span></span><span class="n">a</span></span><span class="n">t</span></span>'])

    def test_empty_tag_boundaries(self):
        """Zero-length tags should be filtered out by ``tag_boundaries()``.

        If they are not, the start of a tag can sort after the end, crashing
        the tag balancer.

        """
        list(build_lines('hello!',
                         [Htmlifier(regions=[(3, 3, 'a'), (3, 5, 'b')])]))

########NEW FILE########
__FILENAME__ = test_build_failure
"""Tests for handling failed builds"""

from dxr.testing import SingleFileTestCase, CommandFailure


class BuildFailureTests(SingleFileTestCase):
    source = r"""A bunch of garbage"""

    @classmethod
    def setup_class(cls):
        """Make sure a failed build returns a non-zero status code."""
        try:
            super(BuildFailureTests, cls).setup_class()
        except CommandFailure:
            pass
        else:
            raise AssertionError('A failed build returned an exit code of 0.')

    def test_nothing(self):
        """A null test just to make the setup method run"""

########NEW FILE########
__FILENAME__ = test_callers
"""Tests for searches using callers and called-by"""

from dxr.testing import SingleFileTestCase, MINIMAL_MAIN


class DirectCallTests(SingleFileTestCase):
    """Tests for searches involving direct calls"""

    source = r"""
        void orphan()
        {
        }

        void called_once()
        {
        }

        void called_twice()
        {
        }

        void call_two()
        {
            called_twice();
            called_once();
        }

        int main()
        {
            called_twice();
            return 0;
        }
        """

    def test_no_caller(self):
        self.found_nothing('callers:orphan')

    def test_no_callees(self):
        self.found_nothing('called-by:orphan')

    def test_one_caller(self):
        self.found_line_eq('callers:called_once', 'void <b>call_two</b>()')

    def test_two_callers(self):
        self.found_lines_eq('callers:called_twice', [
            ('void <b>call_two</b>()', 14),
            ('int <b>main</b>()', 20)])

    def test_one_callee(self):
        self.found_line_eq('called-by:main', 'void <b>called_twice</b>()')

    def test_two_callees(self):
        self.found_lines_eq('called-by:call_two', [
            ('void <b>called_once</b>()', 6),
            ('void <b>called_twice</b>()', 10)])


class IndirectCallTests(SingleFileTestCase):
    """Tests for searches involving indirect (virtual) calls"""

    source = r"""
        class Base
        {
        public:
            Base() {}
            virtual void foo() {}
        };

        class Derived : public Base
        {
        public:
            Derived() {}
            virtual void foo() {}
        };

        void c1(Base &b)
        {
            b.foo();
        }

        void c2(Derived &d)
        {
            d.foo();
        }
        """ + MINIMAL_MAIN

    def test_callers(self):
        self.found_line_eq('+callers:Base::foo()', 'void <b>c1</b>(Base &amp;b)')
        self.found_lines_eq('+callers:Derived::foo()', [
            ('void <b>c1</b>(Base &amp;b)', 16),
            ('void <b>c2</b>(Derived &amp;d)', 21)])

    def test_callees(self):
        self.found_lines_eq('called-by:c1', [
            ('virtual void <b>foo</b>() {}', 6),
            ('virtual void <b>foo</b>() {}', 13)])
        self.found_line_eq('called-by:c2', 'virtual void <b>foo</b>() {}', 13)

########NEW FILE########
__FILENAME__ = test_c_vardecl
from dxr.testing import DxrInstanceTestCase


class CVarDeclTests(DxrInstanceTestCase):
    """Tests matching up C global variables"""

    def test_decl(self):
        """Search for C variable declaration."""
        self.found_line_eq('var-decl:global', u'extern int <b>global</b>;', 5)

    def test_defn(self):
        """Search for C variable definition."""
        self.found_line_eq('var:global', u'int <b>global</b>;', 3)

########NEW FILE########
__FILENAME__ = test_decl
"""Tests for searches for declarations"""

from dxr.testing import SingleFileTestCase, MINIMAL_MAIN


class TypeDeclarationTests(SingleFileTestCase):
    """Tests for declarations of types"""

    source = r"""
        class MyClass;
        class MyClass
        {
        };
        """ + MINIMAL_MAIN

    def test_type(self):
        """Try searching for type declarations."""
        self.found_line_eq(
            'type-decl:MyClass', 'class <b>MyClass</b>;')


class FunctionDeclarationTests(SingleFileTestCase):
    """Tests for declarations of functions"""

    source = r"""
        void foo();
        void foo()
        {
        };
        """ + MINIMAL_MAIN

    def test_function(self):
        """Try searching for function declarations."""
        self.found_line_eq(
            'function-decl:foo', 'void <b>foo</b>();')


class VariableDeclarationTests(SingleFileTestCase):
    """Tests for declarations of variables"""

    source = r"""
        extern int x;
        int x = 0;
        void foo()
        {
            extern int x;
        }
        """ + MINIMAL_MAIN

    def test_variable(self):
        """Try searching for variable declarations."""
        self.found_lines_eq('var-decl:x', [
            ('extern int <b>x</b>;', 2),
            ('extern int <b>x</b>;', 6)])

########NEW FILE########
__FILENAME__ = test_direct
import os.path

from dxr.query import Query
from dxr.utils import connect_db
from dxr.testing import SingleFileTestCase, MINIMAL_MAIN

from nose.tools import eq_


class MemberFunctionTests(SingleFileTestCase):
    source = """
        class MemberFunction {
            public:
                void member_function(int a);  // Don't assume the qualname
                                              // field in the DB ends in just
                                              // ().

            class InnerClass {
            };
        };

        void MemberFunction::member_function(int a) {
        }
        """ + MINIMAL_MAIN

    def direct_result_eq(self, query_text, line_num):
        conn = connect_db(os.path.join(self._config_dir_path, 'target', 'trees', 'code'))
        eq_(Query(conn, query_text).direct_result(), ('main.cpp', line_num))

    def test_qualified_function_name_prefix(self):
        """A unique, case-insensitive prefix match on fully qualified function
        name should take you directly to the result."""
        self.direct_result_eq('MemberFunction::member_FUNCTION', 12)

    def test_qualified_type_name(self):
        """A unique, case-insensitive prefix match on fully qualified type name
        should take you directly to the result."""
        self.direct_result_eq('MemberFunction::InnerCLASS', 8)

    def test_line_number(self):
        """A file name and line number should take you directly to that
           file and line number."""
        self.direct_result_eq('main.cpp:6', 6)
        
########NEW FILE########
__FILENAME__ = test_extensions
from dxr.testing import DxrInstanceTestCase


class FileExtensionsTests(DxrInstanceTestCase):
    """Tests searching for files by extension"""

    def test_extensions(self):
        """Try search by filename extension."""
        self.found_files_eq('ext:c', ['main.c', 'dot_c.c'])
        self.found_files_eq('ext:cpp', ['hello-world.cpp'])
        self.found_files_eq('ext:inc', ['hello-world.inc'])

    def test_extensions_formatting(self):
        """Extensions can be preceeded by a dot"""
        self.found_files_eq('ext:.c', ['main.c', 'dot_c.c'])

########NEW FILE########
__FILENAME__ = test_functions
"""Tests for searches about functions"""

from dxr.testing import SingleFileTestCase, MINIMAL_MAIN


class ReferenceTests(SingleFileTestCase):
    """Tests for finding out where functions are referenced or declared"""

    source = r"""
        #include <stdio.h>

        const char* getHello() {
            return "Hello World";
        }

        int main(int argc, char* argv[]) {
          printf("%s\n", getHello());
          return 0;
        }
        """

    def test_functions(self):
        """Try searching for function declarations."""
        self.found_line_eq(
            'function:main', 'int <b>main</b>(int argc, char* argv[]) {')
        self.found_line_eq(
            'function:getHello', 'const char* <b>getHello</b>() {')


class TemplateClassMemberReferenceTests(SingleFileTestCase):
    """Tests for finding out where member functions of a template class are referenced or declared"""

    source = r"""
        template <typename T>
        class Foo
        {
        public:
            void bar();
        };

        template <typename T>
        void Foo<T>::bar()
        {
        }

        void baz()
        {
            Foo<int>().bar();
        }
        """ + MINIMAL_MAIN

    def test_function_decl(self):
        """Try searching for function declaration."""
        self.found_line_eq('+function-decl:Foo::bar()', 'void <b>bar</b>();')

    def test_function(self):
        """Try searching for function definition."""
        self.found_lines_eq('+function:Foo::bar()',
                            [('void Foo&lt;T&gt;::<b>bar</b>()', 10)])

    def test_function_ref(self):
        """Try searching for function references."""
        self.found_lines_eq('+function-ref:Foo::bar()',
                            [('Foo&lt;int&gt;().<b>bar</b>();', 16)])


class ConstTests(SingleFileTestCase):
    source = """
        class ConstOverload
        {
            public:
                void foo();
                void foo() const;
        };

        void ConstOverload::foo() {
        }

        void ConstOverload::foo() const {
        }
        """ + MINIMAL_MAIN

    def test_const_functions(self):
        """Make sure const functions are indexed separately from non-const but
        otherwise identical signatures."""
        self.found_line_eq('+function:ConstOverload::foo()',
                           'void ConstOverload::<b>foo</b>() {')
        self.found_line_eq('+function:"ConstOverload::foo() const"',
                            'void ConstOverload::<b>foo</b>() const {')


class PrototypeParamTests(SingleFileTestCase):
    source = """
        int prototype_parameter_function(int prototype_parameter);

        int prototype_parameter_function(int prototype_parameter) {
            return prototype_parameter;
        }
        """ + MINIMAL_MAIN

    def test_prototype_params(self):
        # I have no idea what this tests.
        self.found_line_eq(
            '+var:prototype_parameter_function(int)::prototype_parameter',
            'int prototype_parameter_function(int <b>prototype_parameter</b>) {')
        self.found_line_eq(
            '+var-ref:prototype_parameter_function(int)::prototype_parameter',
            'return <b>prototype_parameter</b>;')

########NEW FILE########
__FILENAME__ = test_ignores
from nose.tools import ok_

from dxr.testing import DxrInstanceTestCase, assert_in


class IgnorePatternTests(DxrInstanceTestCase):
    """Test for our handling of ignore_pattern"""

    def _top_level_index(self):
        """Return the HTML of the front browse page."""
        return self.client().get('/code/source/').data

    def test_non_path(self):
        """Test that non-path-based ignore patterns are obeyed."""
        html = self._top_level_index()
        assert_in('main.c', html)  # just to make sure we have the
                                            # right page
        ok_('hello.h' not in html)

    def test_consecutive(self):
        """Make sure one folder being ignored doesn't accidentally eliminate
        the possibility of the next one being ignored."""
        ok_('hello2' not in self._top_level_index())

    # TODO: Test path-based ignores.

########NEW FILE########
__FILENAME__ = test_macros
from dxr.testing import SingleFileTestCase, MINIMAL_MAIN


class MacroRefTests(SingleFileTestCase):
    """Tests for ``+macro-ref`` queries"""

    source = """
        #define MACRO

        #ifdef MACRO
        #endif

        #ifndef MACRO
        #endif
        
        #if defined(MACRO)
        #endif

        #undef MACRO
        """ + MINIMAL_MAIN

    def test_refs(self):
        self.found_lines_eq('+macro-ref:MACRO', [
            # Test that a macro mentioned in an #ifdef directive is treated as
            # a reference:
            ('#ifdef <b>MACRO</b>', 4),

            # Test that a macro mentioned in an #ifndef directive is treated as
            # a reference:
            ('#ifndef <b>MACRO</b>', 7),

            # Test that a macro mentioned in an #if defined() expression is
            # treated as a reference:
            ('#if defined(<b>MACRO</b>)', 10),

            # Test that a macro mentioned in an #undef directive is treated as
            # a reference:
            ('#undef <b>MACRO</b>', 13)])


class MacroArgumentReferenceTests(SingleFileTestCase):
    source = """
        #define ID2(x) (x)
        #define ID(x) ID2(x)
        #define ADD(x, y) ((x) + (y))
        int foo()
        {
            int x = 0;
            int y = 0;
            return
                ID(x) +
                ID(y) +
                ADD(x, y);
        }
        """ + MINIMAL_MAIN

    def test_refs(self):
        """Test variables referenced in macro arguments"""
        self.found_lines_eq('+var-ref:foo()::x', [
            ('ID(<b>x</b>) +', 10),
            ('ADD(<b>x</b>, y);', 12)])
        self.found_lines_eq('+var-ref:foo()::y', [
            ('ID(<b>y</b>) +', 11),
            ('ADD(x, <b>y</b>);', 12)])


class MacroArgumentFieldReferenceTests(SingleFileTestCase):
    source = """
        #define ID2(x) (x)
        #define ID(x) ID2(x)
        #define FOO(x) foo.x
        #define FIELD(s, x) s.x

        struct Foo
        {
            int bar;
        };

        int baz()
        {
            Foo foo = { 0 };
            return
                ID(foo.bar) +
                FOO(bar) +
                FIELD(foo, bar);
        }
        """ + MINIMAL_MAIN

    def test_refs(self):
        """Test struct fields referenced in macro arguments"""
        self.found_lines_eq('+var-ref:baz()::foo', [
            ('ID(<b>foo</b>.bar) +', 16),
            ('FIELD(<b>foo</b>, bar);', 18)])
        self.found_lines_eq('+var-ref:Foo::bar', [
            ('ID(foo.<b>bar</b>) +', 16),
            ('FOO(<b>bar</b>) +', 17),
            ('FIELD(foo, <b>bar</b>);', 18)])


class MacroArgumentDeclareTests(SingleFileTestCase):
    source = """
        #define ID2(x) x
        #define ID(x) ID2(x)
        #define DECLARE(x) int x = 0
        #define DECLARE2(x, y) int x = 0, y = 0
        void foo()
        {
            ID(int a = 0);
            DECLARE(b);
            DECLARE2(c, d);
        }
        """ + MINIMAL_MAIN

    def test_decls(self):
        """Test variables declared in macro arguments"""
        self.found_line_eq('+var:foo()::a', 'ID(int <b>a</b> = 0);')
        self.found_line_eq('+var:foo()::b', 'DECLARE(<b>b</b>);')
        self.found_line_eq('+var:foo()::c', 'DECLARE2(<b>c</b>, d);')
        self.found_line_eq('+var:foo()::d', 'DECLARE2(c, <b>d</b>);')


########NEW FILE########
