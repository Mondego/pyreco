__FILENAME__ = find_todos
#!/usr/bin/env python

keywords = [
    'TODO',
    'TOFIX',
    'FIXME',
    'HACK',
    'XXX',
    'WARN',
]
import os
grep_cmd = """grep -ERn "%s" """ % ("|".join(keywords))
files_and_dirs = [
    'batch-scripts',
    'deployment-scripts',
    'mediadrop',
    'plugins',
    'setup*',
]
exclude_files_and_dirs = [
    'batch-scripts/find_todos.py',
    'mediadrop/public/scripts/third-party/',
    'mediadrop/lib/xhtml/htmlsanitizer.py',
    'mediadrop/public/scripts/mcore-compiled.js',
]

IN, MULT = 1, 2

# File extensions for files that share comment styles.
c_like_files = ['c', 'h', 'java', 'cpp']
html_files = ['xml', 'html', 'xhtml', 'htm']
js_files = ['js']
css_files = ['css']
python_files = ['py']
sql_files = ['sql']
ini_files = ['ini', 'ini_tmpl']

# multiline comment beginning/ending strings
# mapped to the filetypes associated with them.
multiline = {
    ('<!--!', '-->'): html_files + python_files,
    ('"""', '"""'): python_files,
    ('/*', '*/'): c_like_files + js_files + css_files + html_files,
}

# inline comment beginning strings
# mapped to the filetypes associated with them.
inline = {
    '#': python_files + ini_files,
    '//': c_like_files + js_files + html_files,
    '--': sql_files,
}

def get_beginning(lines, line_no, filename):
    # Find the beginning of the enclosing comment block, for the
    # comment on the given line
    line_offset = line_no
    while line_offset >= 0:
        line = lines[line_offset]

        for begin, end in multiline:
            if not any(map(filename.endswith, multiline[(begin, end)])):
                continue
            char_offset = line.find(begin)
            if char_offset >= 0:
                return begin, end, line_offset, char_offset, MULT

        for begin in inline:
            if not any(map(filename.endswith, inline[begin])):
                continue
            char_offset = line.find(begin)
            if char_offset >= 0:
                return begin, None, line_offset, char_offset, IN

        line_offset -= 1
    return None, None, None, None, None

def get_ending(lines, begin, end, begin_line, begin_char, type):
    # Find the ending of the enclosing comment block, given a
    # description of the beginning of the block
    end_line = begin_line
    end_char = 0

    if type == MULT:
        while (end_line < len(lines)):
            start = 0
            if end_line == begin_line:
                start = begin_char + len(begin)
            end_char = lines[end_line].find(end, start)
            if end_char >= 0:
                break
            end_line += 1
        end_line += 1
    elif type == IN:
        while (end_line < len(lines)):
            start = 0
            if end_line == begin_line:
                start = lines[end_line].index(begin)
            if not lines[end_line][start:].strip().startswith(begin):
                break
            end_line += 1

    return end_line, end_char

def get_lines(lines, line_no, filename):
    # FIRST, GET THE ENTIRE CONTAINING COMMENT BLOCK
    begin, end, begin_line, begin_char, type = get_beginning(lines, line_no, filename)
    if (begin,end) == (None, None):
        return None # false alarm, this isn't a comment at all!
    end_line, end_char = get_ending(lines, begin, end, begin_line, begin_char, type)
    lines = map(lambda line: line.strip(), lines[begin_line:end_line])
    # "lines" NOW HOLDS EVERY LINE IN THE CONTAINING COMMENT BLOCK

    # NOW, FIND ONLY THE LINES IN THE SECTION WE CARE ABOUT
    offset = line_no - begin_line
    lines = lines[offset:]
    size = 1
    while size < len(lines):
        line = lines[size].strip().lstrip(begin)
        if line == "":
            break
        size += 1

    return lines[:size]

# Keep track of how many of each keyword we see
counts = { }
for k in keywords:
    counts[k] = 0

# Populate a dict of filename -> [lines of interest]
matched_files = {}
for x in files_and_dirs:
    cmd = grep_cmd + x
    result = os.popen(cmd)
    for line in result.readlines():

        if line.startswith('Binary file'):
            # ignore binary files
            continue

        if any(map(line.startswith, exclude_files_and_dirs)):
            # don't include the specifically excluded dirs
            continue

        file, line_no, rest = line.split(":", 2)

        for k in counts:
            # keep track of how many of each keyword we see
            if k in rest:
                counts[k] += 1

        # Add this entry to the dict.
        if file not in matched_files:
            matched_files[file] = []
        matched_files[file].append(int(line_no))

# Iterate over each filename, printing the found
# todo blocks.
for x in sorted(matched_files.keys()):
    line_nos = matched_files[x]
    f = open(x)
    lines = f.readlines()
    f.close()
    output = ["\nFILE: %s\n-----" % x]
    for i, num in enumerate(line_nos):
        curr_line = line_nos[i]-1
        next_line = None
        if (i+1) < len(line_nos):
            next_line = line_nos[i+1]-1

        todo_lines = get_lines(lines, curr_line, x)
        if not todo_lines:
            continue

        if next_line is not None:
            # ensure that the current 'todo' item doesn't
            # overlap with the next 'todo' item.
            max_length = next_line - curr_line
            todo_lines = todo_lines[:max_length]

        output.append("line: %d\n%s\n" % (num, "\n".join(todo_lines)))

    if len(output) > 1:
        for chunk in output:
            print chunk

# Print our counts
for k in counts:
    print k, counts[k]

########NEW FILE########
__FILENAME__ = pylons-batch-script-template
#!/usr/bin/env python2.5
# -*- coding: utf-8 -*-
from mediadrop.lib.cli_commands import LoadAppCommand, load_app

_script_name = "Batch Script Template"
_script_description = """Use this script as a model for creating new batch scripts for MediaDrop."""
DEBUG = False

if __name__ == "__main__":
    cmd = LoadAppCommand(_script_name, _script_description)
    cmd.parser.add_option(
        '--debug',
        action='store_true',
        dest='debug',
        help='Write debug output to STDOUT.',
        default=False
    )
    load_app(cmd)
    DEBUG = cmd.options.debug

# BEGIN SCRIPT & SCRIPT SPECIFIC IMPORTS
import sys

def main(parser, options, args):
    parser.print_help()
    sys.exit(0)

if __name__ == "__main__":
    main(cmd.parser, cmd.options, cmd.args)

########NEW FILE########
__FILENAME__ = upgrade_from_v09_preserve_facebook_xid_comments
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# This file is a part of MediaDrop, Copyright 2009-2013 MediaDrop contributors
# The source code contained in this file is licensed under the GPL.
# See LICENSE.txt in the main project directory, for more information.
#
# Copyright (c) 2012 Felix Schwarz (www.schwarz.eu)

from mediadrop.lib.cli_commands import LoadAppCommand, load_app

_script_name = "Database Upgrade Script for v0.9.x users with Facebook comments"
_script_description = """Use this script to preserve your existing Facebook
comments.

Specify your ini config file as the first argument to this script.

This script queries Facebook for each media to see if there are already 
comments stored for that media. If so the script will ensure that the old
(XFBML/xid based) Facebook comment plugin is used."""
DEBUG = False

# BEGIN SCRIPT & SCRIPT SPECIFIC IMPORTS
import sys
import urllib

from pylons import app_globals
import simplejson as json
from sqlalchemy.orm import joinedload


class FacebookAPI(object):
    def __init__(self, app_id, app_secret):
        self.app_id = app_id
        self.app_secret = app_secret
        self._token = None
    
    def _request(self, url, **parameters):
        response = urllib.urlopen(url % parameters)
        return response.read().strip()
    
    def access_token(self):
        if self._token:
            return self._token
        oauth_url = 'https://graph.facebook.com/oauth/access_token?type=client_cred&client_id=%(app_id)s&client_secret=%(app_secret)s'
        content = self._request(oauth_url, app_id=self.app_id, app_secret=self.app_secret)
        assert content.startswith('access_token')
        self._token = content.split('access_token=', 1)[1]
        return self._token
    
    def number_xid_comments(self, media):
        token = self.access_token()
        graph_url = 'https://graph.facebook.com/fql?q=select+text+from+comment+where+is_private=0+and+xid=%(xid)d&access_token=%(access_token)s'
        content = self._request(graph_url, xid=media.id, access_token=self.access_token())
        comments_data = json.loads(content)
        if 'error' in comments_data:
            error = comments_data['error']
            print 'Media %d - %s: %s (code %s)' % (media.id, error['type'], error['message'], error['code'])
            sys.exit(2)
        return comments_data['data']
    
    def has_xid_comments(self, media):
        return self.number_xid_comments(media) > 0

class DummyProgressBar(object):
    def __init__(self, maxval=None):
        pass
    
    def start(self):
        return self
    
    def update(self, value):
        sys.stdout.write('.')
        sys.stdout.flush()
    
    def finish(self):
        sys.stdout.write('\n')
        sys.stdout.flush()

try:
    from progressbar import ProgressBar
except ImportError:
    ProgressBar = DummyProgressBar
    print 'Install the progressbar module for nice progress reporting'
    print '    $ pip install http://python-progressbar.googlecode.com/files/progressbar-2.3.tar.gz'
    print

def main(parser, options, args):
    app_globs = app_globals._current_obj()
    app_id = app_globals.settings['facebook_appid']
    if not app_id:
        print 'No Facebook app_id configured, exiting'
        sys.exit(3)
    
    app_secret = options.app_secret
    fb = FacebookAPI(app_id, app_secret)
    
    from mediadrop.model import DBSession, Media
    # eager loading of 'meta' to speed up later check.
    all_media = Media.query.options(joinedload('_meta')).all()
    
    print 'Checking all media for existing Facebook comments'
    progress = ProgressBar(maxval=len(all_media)).start()
    for i, media in enumerate(all_media):
        progress.update(i+1)
        if 'facebook-comment-xid' not in media.meta:
            continue
        if not fb.has_xid_comments(media):
            continue
        media.meta[u'facebook-comment-xid'] = unicode(media.id)
        DBSession.add(media)
        DBSession.commit()

    progress.finish()

if __name__ == "__main__":
    cmd = LoadAppCommand(_script_name, _script_description)
    cmd.parser.add_option(
        '--app-secret',
        action='store',
        dest='app_secret',
        help='Facebook app_secret for the app_id stored in MediaDrop',
    )
    load_app(cmd)
    if len(cmd.args) < 1:
        print 'usage: %s <ini>' % sys.argv[0]
        sys.exit(1)
    elif not cmd.options.app_secret:
        print 'please specify the app_secret with "--app-secret=..."'
        sys.exit(1)
    main(cmd.parser, cmd.options, cmd.args)


########NEW FILE########
__FILENAME__ = autodoc_alchemy
import mediadrop

def omit_sqlalchemy_descriptors(app, what, name, obj, skip, options):
    if obj.__doc__ == 'Public-facing descriptor, placed in the mapped class dictionary.':
        skip = True
    return skip

def setup(app):
    app.connect('autodoc-skip-member', omit_sqlalchemy_descriptors)

########NEW FILE########
__FILENAME__ = autodoc_expose
"""
Sphinx autodoc extension that reads @expose decorator in controllers

"""
import mediadrop

def setup(app):
    app.connect('autodoc-process-docstring', add_expose_info)

def add_expose_info(app, what, name, obj, options, lines):
    if what == 'method' \
    and getattr(obj, 'exposed', False) \
    and obj.im_class.__name__.endswith('Controller') \
    and hasattr(obj, 'template'):
        lines.append("\n")
        lines.append("\n")
        lines.append("Renders: :data:`%s`" % obj.template)

########NEW FILE########
__FILENAME__ = autodoc_urls
"""
Sphinx Extension for creating a map of URLs to controllers and templates

"""

def setup(app):
    pass

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# MediaDrop documentation build configuration file, created by
# sphinx-quickstart on Fri Sep  4 13:43:20 2009.
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
sys.path.append(os.path.abspath('../'))
sys.path.append(os.path.abspath('.'))

import mediadrop


# -- Environment Setup -----------------------------------------------------
# We need a proper request environment to be able to properly import
# controllers and forms for the sake of autodoc.
from mediadrop.lib.test import fake_request, setup_environment_and_database

pylons_config = setup_environment_and_database()
request = fake_request(pylons_config)

# -- General configuration -----------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.autosummary',
    'sphinx.ext.doctest',
    'sphinx.ext.todo',
    'sphinx.ext.coverage',
    'sphinx.ext.intersphinx',
    'autodoc_alchemy',
    'autodoc_expose',
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'MediaDrop'
copyright = u'2009-2014, MediaDrop Contributors'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = mediadrop.__version__
# The full version, including alpha/beta/rc tags.
release = mediadrop.__version__

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
exclude_trees = []

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
htmlhelp_basename = 'MediaDropdoc'


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
# latex_documents = []

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


# Display todos
todo_include_todos = True


intersphinx_mapping = {
    'http://docs.python.org/2.6/': None,
    'http://www.sqlalchemy.org/docs/': None,
    'http://routes.readthedocs.org/en/latest/': None,
    'http://docs.pylonsproject.org/projects/pylons-webframework/en/latest/': None,
    'http://toscawidgets.org/documentation/tw.forms/': None,
    'http://toscawidgets.org/documentation/ToscaWidgets/': None,
}

########NEW FILE########
__FILENAME__ = environment
from mediadrop.config.environment import *

########NEW FILE########
__FILENAME__ = middleware
from mediadrop.config.middleware import *

########NEW FILE########
__FILENAME__ = routing
from mediadrop.config.routing import *

########NEW FILE########
__FILENAME__ = categories
from mediadrop.controllers.admin.categories import *

########NEW FILE########
__FILENAME__ = comments
from mediadrop.controllers.admin.comments import *

########NEW FILE########
__FILENAME__ = groups
from mediadrop.controllers.admin.groups import *

########NEW FILE########
__FILENAME__ = index
from mediadrop.controllers.admin.index import *

########NEW FILE########
__FILENAME__ = media
from mediadrop.controllers.admin.media import *

########NEW FILE########
__FILENAME__ = players
from mediadrop.controllers.admin.players import *

########NEW FILE########
__FILENAME__ = podcasts
from mediadrop.controllers.admin.podcasts import *

########NEW FILE########
__FILENAME__ = settings
from mediadrop.controllers.admin.settings import *

########NEW FILE########
__FILENAME__ = storage
from mediadrop.controllers.admin.storage import *

########NEW FILE########
__FILENAME__ = tags
from mediadrop.controllers.admin.tags import *

########NEW FILE########
__FILENAME__ = users
from mediadrop.controllers.admin.users import *

########NEW FILE########
__FILENAME__ = categories
from mediadrop.controllers.api.categories import *

########NEW FILE########
__FILENAME__ = media
from mediadrop.controllers.api.media import *

########NEW FILE########
__FILENAME__ = categories
from mediadrop.controllers.categories import *

########NEW FILE########
__FILENAME__ = errors
from mediadrop.controllers.errors import *

########NEW FILE########
__FILENAME__ = login
from mediadrop.controllers.login import *

########NEW FILE########
__FILENAME__ = media
from mediadrop.controllers.media import *

########NEW FILE########
__FILENAME__ = podcasts
from mediadrop.controllers.podcasts import *

########NEW FILE########
__FILENAME__ = sitemaps
from mediadrop.controllers.sitemaps import *

########NEW FILE########
__FILENAME__ = upload
from mediadrop.controllers.upload import *

########NEW FILE########
__FILENAME__ = categories
from mediadrop.forms.admin.categories import *

########NEW FILE########
__FILENAME__ = comments
from mediadrop.forms.admin.comments import *

########NEW FILE########
__FILENAME__ = groups
from mediadrop.forms.admin.groups import *

########NEW FILE########
__FILENAME__ = media
from mediadrop.forms.admin.media import *

########NEW FILE########
__FILENAME__ = players
from mediadrop.forms.admin.players import *

########NEW FILE########
__FILENAME__ = podcasts
from mediadrop.forms.admin.podcasts import *

########NEW FILE########
__FILENAME__ = settings
from mediadrop.forms.admin.settings import *

########NEW FILE########
__FILENAME__ = ftp
from mediadrop.forms.admin.storage.ftp import *

########NEW FILE########
__FILENAME__ = localfiles
from mediadrop.forms.admin.storage.localfiles import *

########NEW FILE########
__FILENAME__ = remoteurls
from mediadrop.forms.admin.storage.remoteurls import *

########NEW FILE########
__FILENAME__ = tags
from mediadrop.forms.admin.tags import *

########NEW FILE########
__FILENAME__ = users
from mediadrop.forms.admin.users import *

########NEW FILE########
__FILENAME__ = comments
from mediadrop.forms.comments import *

########NEW FILE########
__FILENAME__ = login
from mediadrop.forms.login import *

########NEW FILE########
__FILENAME__ = uploader
from mediadrop.forms.uploader import *

########NEW FILE########
__FILENAME__ = app_globals
from mediadrop.lib.app_globals import *

########NEW FILE########
__FILENAME__ = attribute_dict
from mediadrop.lib.attribute_dict import *

########NEW FILE########
__FILENAME__ = api
from mediadrop.lib.auth.api import *

########NEW FILE########
__FILENAME__ = group_based_policy
from mediadrop.lib.auth.group_based_policy import *

########NEW FILE########
__FILENAME__ = middleware
from mediadrop.lib.auth.middleware import *

########NEW FILE########
__FILENAME__ = permission_system
from mediadrop.lib.auth.permission_system import *

########NEW FILE########
__FILENAME__ = pylons_glue
from mediadrop.lib.auth.pylons_glue import *

########NEW FILE########
__FILENAME__ = query_result_proxy
from mediadrop.lib.auth.query_result_proxy import *

########NEW FILE########
__FILENAME__ = util
from mediadrop.lib.auth.util import *

########NEW FILE########
__FILENAME__ = base
from mediadrop.lib.base import *

########NEW FILE########
__FILENAME__ = cli_commands
from mediadrop.lib.cli_commands import *

########NEW FILE########
__FILENAME__ = functional
from mediadrop.lib.compat.functional import *

########NEW FILE########
__FILENAME__ = css_delivery
from mediadrop.lib.css_delivery import *

########NEW FILE########
__FILENAME__ = decorators
from mediadrop.lib.decorators import *

########NEW FILE########
__FILENAME__ = email
from mediadrop.lib.email import *

########NEW FILE########
__FILENAME__ = filetypes
from mediadrop.lib.filetypes import *

########NEW FILE########
__FILENAME__ = helpers
from mediadrop.lib.helpers import *

########NEW FILE########
__FILENAME__ = i18n
from mediadrop.lib.i18n import *

########NEW FILE########
__FILENAME__ = js_delivery
from mediadrop.lib.js_delivery import *

########NEW FILE########
__FILENAME__ = paginate
from mediadrop.lib.paginate import *

########NEW FILE########
__FILENAME__ = players
from mediadrop.lib.players import *

########NEW FILE########
__FILENAME__ = facebook
from mediadrop.lib.services.facebook import *

########NEW FILE########
__FILENAME__ = api
from mediadrop.lib.storage.api import *

########NEW FILE########
__FILENAME__ = bliptv
from mediadrop.lib.storage.bliptv import *

########NEW FILE########
__FILENAME__ = dailymotion
from mediadrop.lib.storage.dailymotion import *

########NEW FILE########
__FILENAME__ = ftp
from mediadrop.lib.storage.ftp import *

########NEW FILE########
__FILENAME__ = googlevideo
from mediadrop.lib.storage.googlevideo import *

########NEW FILE########
__FILENAME__ = localfiles
from mediadrop.lib.storage.localfiles import *

########NEW FILE########
__FILENAME__ = remoteurls
from mediadrop.lib.storage.remoteurls import *

########NEW FILE########
__FILENAME__ = vimeo
from mediadrop.lib.storage.vimeo import *

########NEW FILE########
__FILENAME__ = youtube
from mediadrop.lib.storage.youtube import *

########NEW FILE########
__FILENAME__ = templating
from mediadrop.lib.templating import *

########NEW FILE########
__FILENAME__ = controller_testcase
from mediadrop.lib.test.controller_testcase import *

########NEW FILE########
__FILENAME__ = db_testcase
from mediadrop.lib.test.db_testcase import *

########NEW FILE########
__FILENAME__ = pythonic_testcase
from mediadrop.lib.test.pythonic_testcase import *

########NEW FILE########
__FILENAME__ = request_mixin
from mediadrop.lib.test.request_mixin import *

########NEW FILE########
__FILENAME__ = support
from mediadrop.lib.test.support import *

########NEW FILE########
__FILENAME__ = thumbnails
from mediadrop.lib.thumbnails import *

########NEW FILE########
__FILENAME__ = uri
from mediadrop.lib.uri import *

########NEW FILE########
__FILENAME__ = util
from mediadrop.lib.util import *

########NEW FILE########
__FILENAME__ = htmlsanitizer
from mediadrop.lib.xhtml.htmlsanitizer import *

########NEW FILE########
__FILENAME__ = auth
from mediadrop.model.auth import *

########NEW FILE########
__FILENAME__ = authors
from mediadrop.model.authors import *

########NEW FILE########
__FILENAME__ = categories
from mediadrop.model.categories import *

########NEW FILE########
__FILENAME__ = comments
from mediadrop.model.comments import *

########NEW FILE########
__FILENAME__ = media
from mediadrop.model.media import *

########NEW FILE########
__FILENAME__ = meta
from mediadrop.model.meta import *

########NEW FILE########
__FILENAME__ = players
from mediadrop.model.players import *

########NEW FILE########
__FILENAME__ = podcasts
from mediadrop.model.podcasts import *

########NEW FILE########
__FILENAME__ = settings
from mediadrop.model.settings import *

########NEW FILE########
__FILENAME__ = storage
from mediadrop.model.storage import *

########NEW FILE########
__FILENAME__ = tags
from mediadrop.model.tags import *

########NEW FILE########
__FILENAME__ = util
from mediadrop.model.util import *

########NEW FILE########
__FILENAME__ = abc
from mediadrop.plugin.abc import *

########NEW FILE########
__FILENAME__ = events
from mediadrop.plugin.events import *

########NEW FILE########
__FILENAME__ = manager
from mediadrop.plugin.manager import *

########NEW FILE########
__FILENAME__ = plugin
from mediadrop.plugin.plugin import *

########NEW FILE########
__FILENAME__ = limit_feed_items_validator
from mediadrop.validation.limit_feed_items_validator import *

########NEW FILE########
__FILENAME__ = uri_validator
from mediadrop.validation.uri_validator import *

########NEW FILE########
__FILENAME__ = environment
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code contained in this file is licensed under the GPLv3 or
# (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.
"""Pylons environment configuration"""

import os

from formencode.api import get_localedir as get_formencode_localedir
from genshi.filters.i18n import Translator
import pylons
from pylons import translator
from pylons.configuration import PylonsConfig
from sqlalchemy import engine_from_config

import mediadrop.lib.app_globals as app_globals
import mediadrop.lib.helpers

from mediadrop.config.routing import create_mapper, add_routes
from mediadrop.lib.templating import TemplateLoader
from mediadrop.model import Media, Podcast, init_model
from mediadrop.plugin import PluginManager, events

def load_environment(global_conf, app_conf):
    """Configure the Pylons environment via the ``pylons.config`` object"""
    config = PylonsConfig()

    # Pylons paths
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    paths = dict(root=root,
                 controllers=os.path.join(root, 'controllers'),
                 static_files=os.path.join(root, 'public'),
                 templates=[os.path.join(root, 'templates')])

    # Initialize config with the basic options
    config.init_app(global_conf, app_conf, package='mediadrop', paths=paths)
    env_dir = os.path.normpath(os.path.join(config['media_dir'], '..'))
    config.setdefault('env_dir', env_dir)

    # Initialize the plugin manager to load all active plugins
    plugin_mgr = PluginManager(config)

    mapper = create_mapper(config, plugin_mgr.controller_scan)
    events.Environment.before_route_setup(mapper)
    add_routes(mapper)
    events.Environment.after_route_setup(mapper)
    config['routes.map'] = mapper
    config['pylons.app_globals'] = app_globals.Globals(config)
    config['pylons.app_globals'].plugin_mgr = plugin_mgr
    config['pylons.app_globals'].events = events
    config['pylons.h'] = mediadrop.lib.helpers

    # Setup cache object as early as possible
    pylons.cache._push_object(config['pylons.app_globals'].cache)

    i18n_env_dir = os.path.join(config['env_dir'], 'i18n')
    config['locale_dirs'] = plugin_mgr.locale_dirs()
    config['locale_dirs'].update({
        'mediadrop': (os.path.join(root, 'i18n'), i18n_env_dir),
        'FormEncode': (get_formencode_localedir(), i18n_env_dir),
    })

    def enable_i18n_for_template(template):
        translations = Translator(translator)
        translations.setup(template)

    # Create the Genshi TemplateLoader
    config['pylons.app_globals'].genshi_loader = TemplateLoader(
        search_path=paths['templates'] + plugin_mgr.template_loaders(),
        auto_reload=True,
        max_cache_size=100,
        callback=enable_i18n_for_template,
    )

    # Setup the SQLAlchemy database engine
    engine = engine_from_config(config, 'sqlalchemy.')
    init_model(engine, config.get('db_table_prefix', None))
    events.Environment.init_model()

    # CONFIGURATION OPTIONS HERE (note: all config options will override
    #                                   any Pylons config options)

    # TODO: Move as many of these custom options into an .ini file, or at least
    #       to somewhere more friendly.

    # TODO: Rework templates not to rely on this line:
    #       See docstring in pylons.configuration.PylonsConfig for details.
    config['pylons.strict_tmpl_context'] = False

    config['thumb_sizes'] = { # the dimensions (in pixels) to scale thumbnails
        Media._thumb_dir: {
            's': (128,  72),
            'm': (160,  90),
            'l': (560, 315),
        },
        Podcast._thumb_dir: {
            's': (128, 128),
            'm': (160, 160),
            'l': (600, 600),
        },
    }

    # END CUSTOM CONFIGURATION OPTIONS

    events.Environment.loaded(config)

    return config

########NEW FILE########
__FILENAME__ = middleware
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code contained in this file is licensed under the GPLv3 or
# (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.
"""Pylons middleware initialization"""

import logging
import os
import threading

from beaker.middleware import SessionMiddleware
from genshi.template import loader
from genshi.template.plugin import MarkupTemplateEnginePlugin
from paste import gzipper
from paste.cascade import Cascade
from paste.registry import RegistryManager
from paste.response import header_value, remove_header
from paste.urlmap import URLMap
from paste.urlparser import StaticURLParser
from paste.deploy.converters import asbool
from paste.deploy.config import PrefixMiddleware
from pylons.middleware import ErrorHandler, StatusCodeRedirect
from pylons.wsgiapp import PylonsApp as _PylonsApp
from routes.middleware import RoutesMiddleware
import sqlalchemy
from sqlalchemy.pool import Pool
from sqlalchemy.exc import DisconnectionError
from tw.core.view import EngineManager
import tw.api

from mediadrop import monkeypatch_method
from mediadrop.config.environment import load_environment
from mediadrop.lib.auth import add_auth
from mediadrop.migrations.util import MediaDropMigrator
from mediadrop.model import metadata, DBSession
from mediadrop.plugin import events

log = logging.getLogger(__name__)

class PylonsApp(_PylonsApp):
    """
    Subclass PylonsApp to set our settings on the request.

    The settings are cached in ``request.settings`` but it's best to
    check the cache once, then make them accessible as a simple dict for
    the remainder of the request, instead of hitting the cache repeatedly.

    """
    def register_globals(self, environ):
        _PylonsApp.register_globals(self, environ)
        request = environ['pylons.pylons'].request

        if environ['PATH_INFO'] == '/_test_vars':
            # This is a dummy request, probably used inside a test or to build
            # documentation, so we're not guaranteed to have a database
            # connection with which to get the settings.
            request.settings = {
                'intentionally_empty': 'see mediadrop.config.middleware',
            }
        else:
            request.settings = self.globals.settings

def setup_prefix_middleware(app, global_conf, proxy_prefix):
    """Add prefix middleware.

    Essentially replaces request.environ[SCRIPT_NAME] with the prefix defined
    in the .ini file.

    See: http://wiki.pylonshq.com/display/pylonsdocs/Configuration+Files#prefixmiddleware
    """
    app = PrefixMiddleware(app, global_conf, proxy_prefix)
    return app

class DBSessionRemoverMiddleware(object):
    """Ensure the contextual session ends at the end of the request."""
    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        try:
            return self.app(environ, start_response)
        finally:
            DBSession.remove()

class FastCGIScriptStripperMiddleware(object):
    """Strip the given fcgi_script_name from the end of environ['SCRIPT_NAME'].

    Useful for the default FastCGI deployment, where mod_rewrite is used to
    avoid having to put the .fcgi file name into the URL.
    """
    def __init__(self, app, fcgi_script_name='/mediadrop.fcgi'):
        self.app = app
        self.fcgi_script_name = fcgi_script_name
        self.cut = len(fcgi_script_name)

    def __call__(self, environ, start_response):
        script_name = environ.get('SCRIPT_NAME', '')
        if script_name.endswith(self.fcgi_script_name):
            environ['SCRIPT_NAME'] = script_name[:-self.cut]
        return self.app(environ, start_response)

def create_tw_engine_manager(app_globals):
    def filename_suffix_adder(inner_loader, suffix):
        def _add_suffix(filename):
            return inner_loader(filename + suffix)
        return _add_suffix

    # Ensure that the toscawidgets template loader includes the search paths
    # from our main template loader.
    tw_engines = EngineManager(extra_vars_func=None)
    tw_engines['genshi'] = MarkupTemplateEnginePlugin()
    tw_engines['genshi'].loader = app_globals.genshi_loader

    # Disable the built-in package name template resolution.
    tw_engines['genshi'].use_package_naming = False

    # Rebuild package name template resolution using mostly standard Genshi
    # load functions. With our customizations to the TemplateLoader, the
    # absolute paths that the builtin resolution produces are erroneously
    # treated as being relative to the search path.

    # Search the tw templates dir using the pkg_resources API.
    # Expected input: 'input_field.html'
    tw_loader = loader.package('tw.forms', 'templates')

    # Include the .html extension automatically.
    # Expected input: 'input_field'
    tw_loader = filename_suffix_adder(tw_loader, '.html')

    # Apply this loader only when the filename starts with tw.forms.templates.
    # This prefix is stripped off when calling the above loader.
    # Expected input: 'tw.forms.templates.input_field'
    tw_loader = loader.prefixed(**{'tw.forms.templates.': tw_loader})

    # Add this path to our global loader
    tw_engines['genshi'].loader.search_path.append(tw_loader)
    return tw_engines

def setup_tw_middleware(app, config):
    app_globals = config['pylons.app_globals']
    app = tw.api.make_middleware(app, {
        'toscawidgets.framework': 'pylons',
        'toscawidgets.framework.default_view': 'genshi',
        'toscawidgets.framework.engines': create_tw_engine_manager(app_globals),
    })
    return app

class DBSanityCheckingMiddleware(object):
    def __init__(self, app, check_for_leaked_connections=False, 
                 enable_pessimistic_disconnect_handling=False):
        self.app = app
        self._thread_local = threading.local()
        self.is_leak_check_enabled = check_for_leaked_connections
        self.is_alive_check_enabled = enable_pessimistic_disconnect_handling
        self.pool_listeners = {}
        pool = self._pool()
        if self.is_leak_check_enabled or self.is_alive_check_enabled:
            sqlalchemy.event.listen(pool, 'checkout', self.on_connection_checkout)
            self.pool_listeners['checkout'] = self.on_connection_checkout
        if self.is_leak_check_enabled:
            sqlalchemy.event.listen(pool, 'checkin', self.on_connection_checkin)
            self.pool_listeners['checkin'] = self.on_connection_checkin
    
    def _pool(self):
        engine = metadata.bind
        return engine.pool

    def __call__(self, environ, start_response):
        try:
            return self.app(environ, start_response)
        finally:
            leaked_connections = len(self.connections)
            if leaked_connections > 0:
                msg = 'DB connection leakage detected: ' + \
                    '%d db connection(s) not returned to the pool' % leaked_connections
                log.error(msg)
                self.connections.clear()
    
    def tear_down(self):
        pool = self._pool()
        for target, fn in self.pool_listeners.items():
            sqlalchemy.event.remove(pool, target, fn)

    @property
    def connections(self):
        if not hasattr(self._thread_local, 'connections'):
            self._thread_local.connections = dict()
        return self._thread_local.connections
    
    def check_for_live_db_connection(self, dbapi_connection):
        # Try to check that the current DB connection is usable for DB queries
        # by issuing a trivial SQL query. It can happen because the user set
        # the 'sqlalchemy.pool_recycle' time too high or simply because the
        # MySQL server was restarted in the mean time.
        # Without this check a user would get an internal server error and the
        # connection would be reset by the DBSessionRemoverMiddleware at the
        # end of that request.
        # This functionality below will prevent the initial "internal server
        # error".
        #
        # This approach is controversial between DB experts. A good blog post
        # (with an even better discussion highlighting pros and cons) is
        # http://www.mysqlperformanceblog.com/2010/05/05/checking-for-a-live-database-connection-considered-harmful/
        #
        # In MediaDrop the check is only done once per request (skipped for
        # static files) so it should be relatively light on the DB server.
        # Also the check can be disabled using the setting
        # 'sqlalchemy.check_connection_before_request = false'.
        #
        # possible optimization: check each connection only once per minute or so,
        # store last check time in private attribute of connection object.
        
        # code stolen from SQLAlchemy's 'Pessimistic Disconnect Handling' docs
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute('SELECT 1')
        except:
            msg = u'received broken db connection from pool, resetting db session. ' + \
                u'If you see this error regularly and you use MySQL please check ' + \
                u'your "sqlalchemy.pool_recycle" setting (usually it is too high).'
            log.warning(msg)
            # The pool will try to connect again up to three times before
            # raising an exception itself.
            raise DisconnectionError()
        cursor.close()
    
    def on_connection_checkout(self, dbapi_connection, connection_record, connection_proxy):
        if self.is_alive_check_enabled:
            self.check_for_live_db_connection(dbapi_connection)
        if self.is_leak_check_enabled:
#             if len(self.connections) > 0:
#                 import traceback
#                 traceback.print_stack(limit=15)
            self.connections[id(dbapi_connection)] = True
    
    def on_connection_checkin(self, dbapi_connection, connection_record):
        connection_id = id(dbapi_connection)
        # connections might be returned *after* this middleware called
        # 'self.connections.clear()', we should not break in that case...
        if connection_id in self.connections:
            del self.connections[connection_id]


def setup_db_sanity_checks(app, config):
    check_for_leaked_connections = asbool(config.get('db.check_for_leaked_connections', False))
    enable_pessimistic_disconnect_handling = asbool(config.get('db.enable_pessimistic_disconnect_handling', False))
    if (not check_for_leaked_connections) and (not enable_pessimistic_disconnect_handling):
        return app
    
    return DBSanityCheckingMiddleware(app, check_for_leaked_connections=check_for_leaked_connections,
                                      enable_pessimistic_disconnect_handling=enable_pessimistic_disconnect_handling)

def setup_gzip_middleware(app, global_conf):
    """Make paste.gzipper middleware with a monkeypatch to exempt SWFs.

    Gzipping .swf files (application/x-shockwave-flash) provides no
    extra compression and it also breaks Flowplayer 3.2.3, and
    potentially others.

    """
    @monkeypatch_method(gzipper.GzipResponse)
    def gzip_start_response(self, status, headers, exc_info=None):
        self.headers = headers
        ct = header_value(headers, 'content-type')
        ce = header_value(headers, 'content-encoding')
        self.compressible = False
        # This statement is the only change in this monkeypatch:
        if ct and (ct.startswith('text/') or ct.startswith('application/')) \
            and 'zip' not in ct and ct != 'application/x-shockwave-flash':
            self.compressible = True
        if ce:
            self.compressible = False
        if self.compressible:
            headers.append(('content-encoding', 'gzip'))
        remove_header(headers, 'content-length')
        self.headers = headers
        self.status = status
        return self.buffer.write
    return gzipper.make_gzip_middleware(app, global_conf)

def make_app(global_conf, full_stack=True, static_files=True, **app_conf):
    """Create a Pylons WSGI application and return it

    ``global_conf``
        The inherited configuration for this application. Normally from
        the [DEFAULT] section of the Paste ini file.

    ``full_stack``
        Whether this application provides a full WSGI stack (by default,
        meaning it handles its own exceptions and errors). Disable
        full_stack when this application is "managed" by another WSGI
        middleware.

    ``static_files``
        Whether this application serves its own static files; disable
        when another web server is responsible for serving them.

    ``app_conf``
        The application's local configuration. Normally specified in
        the [app:<name>] section of the Paste ini file (where <name>
        defaults to main).

    """
    # Configure the Pylons environment
    config = load_environment(global_conf, app_conf)
    alembic_migrations = MediaDropMigrator.from_config(config, log=log)
    db_is_current = True
    if not alembic_migrations.is_db_scheme_current():
        log.warn('Running with an outdated database scheme. Please upgrade your database.')
        db_is_current = False
    plugin_mgr = config['pylons.app_globals'].plugin_mgr
    db_current_for_plugins = plugin_mgr.is_db_scheme_current_for_all_plugins()
    if db_is_current and not db_current_for_plugins:
        log.warn(db_current_for_plugins.message)
        db_is_current = False
    if db_is_current:
        events.Environment.database_ready()

    # The Pylons WSGI app
    app = PylonsApp(config=config)

    # Allow the plugin manager to tweak our WSGI app
    app = plugin_mgr.wrap_pylons_app(app)

    # Routing/Session/Cache Middleware
    app = RoutesMiddleware(app, config['routes.map'], singleton=False)
    app = SessionMiddleware(app, config)

    # CUSTOM MIDDLEWARE HERE (filtered by error handling middlewares)

    # add repoze.who middleware with our own authorization library
    app = add_auth(app, config)

    # ToscaWidgets Middleware
    app = setup_tw_middleware(app, config)

    # Strip the name of the .fcgi script, if using one, from the SCRIPT_NAME
    app = FastCGIScriptStripperMiddleware(app)

    # If enabled, set up the proxy prefix for routing behind
    # fastcgi and mod_proxy based deployments.
    if config.get('proxy_prefix', None):
        app = setup_prefix_middleware(app, global_conf, config['proxy_prefix'])

    # END CUSTOM MIDDLEWARE

    if asbool(full_stack):
        # Handle Python exceptions
        app = ErrorHandler(app, global_conf, **config['pylons.errorware'])

        # by default Apache uses  a global alias for "/error" in the httpd.conf
        # which means that users can not send error reports through MediaDrop's
        # error page (because that POSTs to /error/report).
        # To make things worse Apache (at least up to 2.4) has no "unalias"
        # functionality. So we work around the issue by using the "/errors"
        # prefix (extra "s" at the end)
        error_path = '/errors/document'
        # Display error documents for 401, 403, 404 status codes (and
        # 500 when debug is disabled)
        if asbool(config['debug']):
            app = StatusCodeRedirect(app, path=error_path)
        else:
            app = StatusCodeRedirect(app, errors=(400, 401, 403, 404, 500),
                                     path=error_path)

    # Cleanup the DBSession only after errors are handled
    app = DBSessionRemoverMiddleware(app)

    # Establish the Registry for this application
    app = RegistryManager(app)

    app = setup_db_sanity_checks(app, config)

    if asbool(static_files):
        # Serve static files from our public directory
        public_app = StaticURLParser(config['pylons.paths']['static_files'])

        static_urlmap = URLMap()
        # Serve static files from all plugins
        for dir, path in plugin_mgr.public_paths().iteritems():
            static_urlmap[dir] = StaticURLParser(path)

        # Serve static media and podcast images from outside our public directory
        for image_type in ('media', 'podcasts'):
            dir = '/images/' + image_type
            path = os.path.join(config['image_dir'], image_type)
            static_urlmap[dir] = StaticURLParser(path)

        # Serve appearance directory outside of public as well
        dir = '/appearance'
        path = os.path.join(config['app_conf']['cache_dir'], 'appearance')
        static_urlmap[dir] = StaticURLParser(path)

        # We want to serve goog closure code for debugging uncompiled js.
        if config['debug']:
            goog_path = os.path.join(config['pylons.paths']['root'], '..',
                'closure-library', 'closure', 'goog')
            if os.path.exists(goog_path):
                static_urlmap['/scripts/goog'] = StaticURLParser(goog_path)

        app = Cascade([public_app, static_urlmap, app])

    if asbool(config.get('enable_gzip', 'true')):
        app = setup_gzip_middleware(app, global_conf)

    app.config = config
    return app

########NEW FILE########
__FILENAME__ = routing
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code contained in this file is licensed under the GPLv3 or
# (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.

"""Routes configuration

The more specific and detailed routes should be defined first so they
may take precedent over the more generic routes. For more information
refer to the routes manual at http://routes.groovie.org/docs/
"""
from routes import Mapper
from routes.util import controller_scan

login_form_url = '/login'
login_handler_url = '/login/submit'
logout_handler_url = '/logout'
post_login_url = '/login/continue'
post_logout_url = '/logout/continue'

def create_mapper(config, controller_scan=controller_scan):
    """Create, configure and return the routes Mapper"""
    map = Mapper(controller_scan=controller_scan,
                 directory=config['pylons.paths']['controllers'],
                 always_scan=config['debug'])
    map.explicit = False
    map.minimization = True # TODO: Rework routes so we can set this to False
    return map

def add_routes(map):
    #################
    # Public Routes #
    #################

    # Media list and non-specific actions
    # These are all mapped without any prefix to indicate the controller
    map.connect('/', controller='media', action='explore')
    map.connect('/media', controller='media', action='index')
    map.connect('/random', controller='media', action='random')

    # Podcasts
    map.connect('/podcasts/feed/{slug}.xml',
        controller='podcasts',
        action='feed')
    map.connect('/podcasts/{slug}',
        controller='podcasts',
        action='view')

    # Sitemaps
    map.connect('/sitemap.xml',
        controller='sitemaps',
        action='google')
    map.connect('/latest.xml',
        controller='sitemaps',
        action='latest')
    map.connect('/featured.xml',
        controller='sitemaps',
        action='featured')
    map.connect('/sitemap{page}.xml',
        controller='sitemaps',
        action='google',
        requirements={'page': r'\d+'})
    map.connect('/mrss.xml',
        controller='sitemaps',
        action='mrss')
    map.connect('/crossdomain.xml',
        controller='sitemaps',
        action='crossdomain_xml')

    # Categories
    map.connect('/categories/feed/{slug}.xml',
        controller='categories',
        action='feed')
    map.connect('/categories/{slug}',
        controller='categories',
        action='index',
        slug=None)
    map.connect('/categories/{slug}/{order}',
        controller='categories',
        action='more',
        requirements={'order': 'latest|popular'})

    # Tags
    map.connect('/tags',
        controller='media',
        action='tags')
    map.connect('/tags/{tag}',
        controller='media',
        action='index')

    # Media
    map.connect('/media/{slug}/{action}',
        controller='media',
        action='view')
    map.connect('/files/{id}-{slug}.{container}',
        controller='media',
        action='serve',
        requirements={'id': r'\d+'})
    map.connect('static_file_url', '/files/{id}.{container}',
        controller='media',
        action='serve',
        requirements={'id': r'\d+'})
    map.connect('/upload/{action}',
        controller='upload',
        action='index')

    # Podcast Episodes
    map.connect('/podcasts/{podcast_slug}/{slug}/{action}',
        controller='media',
        action='view',
        requirements={'action': 'view|rate|comment'})


    ###############
    # Auth Routes #
    ###############

    # XXX: These URLs are also hardcoded at the top of this file
    # This file is initialized by the auth middleware before routing helper
    # methods (ie pylons.url) are available.
    map.connect(login_form_url, controller='login', action='login')
    map.connect(login_handler_url, controller='login', action='login_handler')
    map.connect(logout_handler_url, controller='login', action='logout_handler')
    map.connect(post_login_url, controller='login', action='post_login')
    map.connect(post_logout_url, controller='login', action='post_logout')


    ################
    # Admin routes #
    ################

    map.connect('/admin',
        controller='admin/index',
        action='index')

    map.connect('/admin/settings/categories',
        controller='admin/categories',
        action='index')
    map.connect('/admin/settings/categories/{id}/{action}',
        controller='admin/categories',
        action='edit',
        requirements={'id': r'(\d+|new)'})

    map.connect('/admin/settings/tags',
        controller='admin/tags',
        action='index')
    map.connect('/admin/settings/tags/{id}/{action}',
        controller='admin/tags',
        action='edit',
        requirements={'id': r'(\d+|new)'})

    map.connect('/admin/users',
        controller='admin/users',
        action='index')
    map.connect('/admin/users/{id}/{action}',
        controller='admin/users',
        action='edit',
        requirements={'id': r'(\d+|new)'})
    
    map.connect('/admin/groups',
        controller='admin/groups',
        action='index')
    map.connect('/admin/groups/{id}/{action}',
        controller='admin/groups',
        action='edit',
        requirements={'id': r'(\d+|new)'})

    map.connect('/admin/settings/players',
        controller='admin/players',
        action='index')
    map.connect('/admin/settings/players/{id}/{action}',
        controller='admin/players',
        action='edit',
        requirements={'id': r'(\d+|new)'})

    map.connect('/admin/settings/storage',
        controller='admin/storage',
        action='index')
    map.connect('/admin/settings/storage/{id}/{action}',
        controller='admin/storage',
        action='edit',
        requirements={'id': r'(\d+|new)'})

    map.connect('/admin/media/bulk/{type}',
        controller='admin/media',
        action='bulk')

    map.connect('/admin/media/merge_stubs',
        controller='admin/media',
        action='merge_stubs')


    simple_admin_paths = '|'.join([
        'admin/index',
        'admin/comments',
        'admin/media',
        'admin/podcasts',
        'admin/settings',
    ])

    map.connect('/{controller}',
        action='index',
        requirements={'controller': simple_admin_paths})

    map.connect('/{controller}/{id}/{action}',
        action='edit',
        requirements={'controller': simple_admin_paths, 'id': r'(\d+|new|bulk)'})

    map.connect('/{controller}/{action}',
        requirements={'controller': simple_admin_paths})

    ##############
    # API routes #
    ##############

    map.connect('/api/media/{action}',
        controller='api/media',
        action='index')

    map.connect('/api/categories/{action}',
        controller='api/categories',
        action='index')

    ##################
    # Fallback Route #
    ##################
    map.connect('/{controller}/{action}', action='index')

    return map

########NEW FILE########
__FILENAME__ = categories
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code contained in this file is licensed under the GPLv3 or
# (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.

from pylons import request, tmpl_context
from sqlalchemy import orm

from mediadrop.forms.admin.categories import CategoryForm, CategoryRowForm
from mediadrop.lib.auth import has_permission
from mediadrop.lib.base import BaseController
from mediadrop.lib.decorators import (autocommit, expose, observable, paginate, 
    validate)
from mediadrop.lib.helpers import redirect, url_for
from mediadrop.model import Category, fetch_row, get_available_slug
from mediadrop.model.meta import DBSession
from mediadrop.plugin import events

import logging
log = logging.getLogger(__name__)

category_form = CategoryForm()
category_row_form = CategoryRowForm()

class CategoriesController(BaseController):
    allow_only = has_permission('edit')

    @expose('admin/categories/index.html')
    @paginate('tags', items_per_page=25)
    @observable(events.Admin.CategoriesController.index)
    def index(self, **kwargs):
        """List categories.

        :rtype: Dict
        :returns:
            categories
                The list of :class:`~mediadrop.model.categories.Category`
                instances for this page.
            category_form
                The :class:`~mediadrop.forms.admin.settings.categories.CategoryForm` instance.

        """
        categories = Category.query\
            .order_by(Category.name)\
            .options(orm.undefer('media_count'))\
            .populated_tree()

        return dict(
            categories = categories,
            category_form = category_form,
            category_row_form = category_row_form,
        )

    @expose('admin/categories/edit.html')
    @observable(events.Admin.CategoriesController.edit)
    def edit(self, id, **kwargs):
        """Edit a single category.

        :param id: Category ID
        :rtype: Dict
        :returns:
            categories
                The list of :class:`~mediadrop.model.categories.Category`
                instances for this page.
            category_form
                The :class:`~mediadrop.forms.admin.settings.categories.CategoryForm` instance.

        """
        category = fetch_row(Category, id)

        return dict(
            category = category,
            category_form = category_form,
            category_row_form = category_row_form,
        )

    @expose('json', request_method='POST')
    @validate(category_form)
    @autocommit
    @observable(events.Admin.CategoriesController.save)
    def save(self, id, delete=None, **kwargs):
        """Save changes or create a category.

        See :class:`~mediadrop.forms.admin.settings.categories.CategoryForm` for POST vars.

        :param id: Category ID
        :param delete: If true the category is to be deleted rather than saved.
        :type delete: bool
        :rtype: JSON dict
        :returns:
            success
                bool

        """
        if tmpl_context.form_errors:
            if request.is_xhr:
                return dict(success=False, errors=tmpl_context.form_errors)
            else:
                # TODO: Add error reporting for users with JS disabled?
                return redirect(action='edit')

        cat = fetch_row(Category, id)

        if delete:
            DBSession.delete(cat)
            data = dict(
                success = True,
                id = cat.id,
                parent_options = unicode(category_form.c['parent_id'].display()),
            )
        else:
            cat.name = kwargs['name']
            cat.slug = get_available_slug(Category, kwargs['slug'], cat)

            if kwargs['parent_id']:
                parent = fetch_row(Category, kwargs['parent_id'])
                if parent is not cat and cat not in parent.ancestors():
                    cat.parent = parent
            else:
                cat.parent = None

            DBSession.add(cat)
            DBSession.flush()

            data = dict(
                success = True,
                id = cat.id,
                name = cat.name,
                slug = cat.slug,
                parent_id = cat.parent_id,
                parent_options = unicode(category_form.c['parent_id'].display()),
                depth = cat.depth(),
                row = unicode(category_row_form.display(
                    action = url_for(id=cat.id),
                    category = cat,
                    depth = cat.depth(),
                    first_child = True,
                )),
            )

        if request.is_xhr:
            return data
        else:
            redirect(action='index', id=None)

    @expose('json', request_method='POST')
    @autocommit
    @observable(events.Admin.CategoriesController.bulk)
    def bulk(self, type=None, ids=None, **kwargs):
        """Perform bulk operations on media items

        :param type: The type of bulk action to perform (delete)
        :param ids: A list of IDs.

        """
        if not ids:
            ids = []
        elif not isinstance(ids, list):
            ids = [ids]


        if type == 'delete':
            Category.query.filter(Category.id.in_(ids)).delete(False)
            DBSession.commit()
            success = True
        else:
            success = False

        return dict(
            success = success,
            ids = ids,
            parent_options = unicode(category_form.c['parent_id'].display()),
        )

########NEW FILE########
__FILENAME__ = comments
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code contained in this file is licensed under the GPLv3 or
# (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.
"""
Comment Moderation Controller
"""

from pylons import request
from sqlalchemy import orm

from mediadrop.forms.admin import SearchForm
from mediadrop.forms.admin.comments import EditCommentForm
from mediadrop.lib.auth import has_permission
from mediadrop.lib.base import BaseController
from mediadrop.lib.decorators import (autocommit, expose, expose_xhr,
    observable, paginate)
from mediadrop.lib.helpers import redirect, url_for
from mediadrop.model import Comment, Media, fetch_row
from mediadrop.model.meta import DBSession
from mediadrop.plugin import events

import logging
log = logging.getLogger(__name__)

edit_form = EditCommentForm()
search_form = SearchForm(action=url_for(controller='/admin/comments',
                                        action='index'))

class CommentsController(BaseController):
    allow_only = has_permission('edit')

    @expose_xhr('admin/comments/index.html',
                'admin/comments/index-table.html')
    @paginate('comments', items_per_page=25)
    @observable(events.Admin.CommentsController.index)
    def index(self, page=1, search=None, media_filter=None, **kwargs):
        """List comments with pagination and filtering.

        :param page: Page number, defaults to 1.
        :type page: int
        :param search: Optional search term to filter by
        :type search: unicode or None
        :param media_filter: Optional media ID to filter by
        :type media_filter: int or None
        :rtype: dict
        :returns:
            comments
                The list of :class:`~mediadrop.model.comments.Comment` instances
                for this page.
            edit_form
                The :class:`mediadrop.forms.admin.comments.EditCommentForm` instance,
                to be rendered for each instance in ``comments``.
            search
                The given search term, if any
            search_form
                The :class:`~mediadrop.forms.admin.SearchForm` instance
            media_filter
                The given podcast ID to filter by, if any
            media_filter_title
                The media title for rendering if a ``media_filter`` was specified.

        """
        comments = Comment.query.trash(False)\
            .order_by(Comment.reviewed.asc(),
                      Comment.created_on.desc())

        # This only works since we only have comments on one type of content.
        # It will need re-evaluation if we ever add others.
        comments = comments.options(orm.eagerload('media'))

        if search is not None:
            comments = comments.search(search)

        media_filter_title = media_filter
        if media_filter is not None:
            comments = comments.filter(Comment.media.has(Media.id == media_filter))
            media_filter_title = DBSession.query(Media.title).get(media_filter)
            media_filter = int(media_filter)

        return dict(
            comments = comments,
            edit_form = edit_form,
            media_filter = media_filter,
            media_filter_title = media_filter_title,
            search = search,
            search_form = search_form,
        )

    @expose('json', request_method='POST')
    @autocommit
    @observable(events.Admin.CommentsController.save_status)
    def save_status(self, id, status, ids=None, **kwargs):
        """Approve or delete a comment or comments.

        :param id: A :attr:`~mediadrop.model.comments.Comment.id` if we are
            acting on a single comment, or ``"bulk"`` if we should refer to
            ``ids``.
        :type id: ``int`` or ``"bulk"``
        :param status: ``"approve"`` or ``"trash"`` depending on what action
            the user requests.
        :param ids: An optional string of IDs separated by commas.
        :type ids: ``unicode`` or ``None``
        :rtype: JSON dict
        :returns:
            success
                bool
            ids
                A list of :attr:`~mediadrop.model.comments.Comment.id`
                that have changed.

        """
        if id != 'bulk':
            ids = [id]
        if not isinstance(ids, list):
            ids = [ids]

        if status == 'approve':
            publishable = True
        elif status == 'trash':
            publishable = False
        else:
            # XXX: This form should never be submitted without a valid status.
            raise AssertionError('Unexpected status: %r' % status)

        comments = Comment.query.filter(Comment.id.in_(ids)).all()

        for comment in comments:
            comment.reviewed = True
            comment.publishable = publishable
            DBSession.add(comment)

        DBSession.flush()

        if request.is_xhr:
            return dict(success=True, ids=ids)
        else:
            redirect(action='index')

    @expose('json', request_method='POST')
    @autocommit
    @observable(events.Admin.CommentsController.save_edit)
    def save_edit(self, id, body, **kwargs):
        """Save an edit from :class:`~mediadrop.forms.admin.comments.EditCommentForm`.

        :param id: Comment ID
        :type id: ``int``
        :rtype: JSON dict
        :returns:
            success
                bool
            body
                The edited comment body after validation/filtering

        """
        comment = fetch_row(Comment, id)
        comment.body = body
        DBSession.add(comment)
        return dict(
            success = True,
            body = comment.body,
        )

########NEW FILE########
__FILENAME__ = groups
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code contained in this file is licensed under the GPLv3 or
# (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.

from pylons import request, tmpl_context

from mediadrop.forms.admin.groups import GroupForm
from mediadrop.lib.auth import has_permission
from mediadrop.lib.base import BaseController
from mediadrop.lib.decorators import (autocommit, expose, observable, paginate, validate)
from mediadrop.lib.helpers import redirect, url_for
from mediadrop.model import fetch_row, Group, Permission
from mediadrop.model.meta import DBSession
from mediadrop.plugin import events

group_form = GroupForm()


class GroupsController(BaseController):
    """Admin group actions"""
    allow_only = has_permission('admin')

    @expose('admin/groups/index.html')
    @paginate('groups', items_per_page=50)
    @observable(events.Admin.GroupsController.index)
    def index(self, page=1, **kwargs):
        """List groups with pagination.

        :param page: Page number, defaults to 1.
        :type page: int
        :rtype: Dict
        :returns:
            users
                The list of :class:`~mediadrop.model.auth.Group`
                instances for this page.

        """
        groups = DBSession.query(Group).order_by(Group.display_name, 
                                                 Group.group_name)
        return dict(groups=groups)


    @expose('admin/groups/edit.html')
    @observable(events.Admin.GroupsController.edit)
    def edit(self, id, **kwargs):
        """Display the :class:`~mediadrop.forms.admin.groups.GroupForm` for editing or adding.

        :param id: Group ID
        :type id: ``int`` or ``"new"``
        :rtype: dict
        :returns:
            user
                The :class:`~mediadrop.model.auth.Group` instance we're editing.
            user_form
                The :class:`~mediadrop.forms.admin.groups.GroupForm` instance.
            user_action
                ``str`` form submit url
            group_values
                ``dict`` form values

        """
        group = fetch_row(Group, id)

        if tmpl_context.action == 'save' or id == 'new':
            # Use the values from error_handler or GET for new groups
            group_values = kwargs
        else:
            permission_ids = map(lambda permission: permission.permission_id, group.permissions)
            group_values = dict(
                display_name = group.display_name,
                group_name = group.group_name,
                permissions = permission_ids
            )

        return dict(
            group = group,
            group_form = group_form,
            group_action = url_for(action='save'),
            group_values = group_values,
        )


    @expose(request_method='POST')
    @validate(group_form, error_handler=edit)
    @autocommit
    @observable(events.Admin.GroupsController.save)
    def save(self, id, display_name, group_name, permissions, delete=None, **kwargs):
        """Save changes or create a new :class:`~mediadrop.model.auth.Group` instance.

        :param id: Group ID. If ``"new"`` a new group is created.
        :type id: ``int`` or ``"new"``
        :returns: Redirect back to :meth:`index` after successful save.

        """
        group = fetch_row(Group, id)

        if delete:
            DBSession.delete(group)
            redirect(action='index', id=None)
        
        group.display_name = display_name
        group.group_name = group_name
        if permissions:
            query = DBSession.query(Permission).filter(Permission.permission_id.in_(permissions))
            group.permissions = list(query.all())
        else:
            group.permissions = []
        DBSession.add(group)

        redirect(action='index', id=None)


    @expose('json', request_method='POST')
    @autocommit
    @observable(events.Admin.GroupsController.delete)
    def delete(self, id, **kwargs):
        """Delete a group.

        :param id: Group ID.
        :type id: ``int``
        :returns: Redirect back to :meth:`index` after successful delete.
        """
        group = fetch_row(Group, id)
        DBSession.delete(group)

        if request.is_xhr:
            return dict(success=True)
        redirect(action='index', id=None)


########NEW FILE########
__FILENAME__ = index
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code contained in this file is licensed under the GPLv3 or
# (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.

import webhelpers.paginate

from mediadrop.lib.auth import has_permission
from mediadrop.lib.base import BaseController
from mediadrop.lib.decorators import expose, observable
from mediadrop.model import Comment, Media
from mediadrop.plugin import events

import logging
log = logging.getLogger(__name__)

class IndexController(BaseController):
    """Admin dashboard actions"""
    allow_only = has_permission('edit')

    @expose('admin/index.html')
    @observable(events.Admin.IndexController.index)
    def index(self, **kwargs):
        """List recent and important items that deserve admin attention.

        We do not use the :func:`mediadrop.lib.helpers.paginate` decorator
        because its somewhat incompatible with the way we handle ajax
        fetching with :meth:`video_table`. This should be refactored and
        fixed at a later date.

        :rtype: Dict
        :returns:
            review_page
                A :class:`webhelpers.paginate.Page` instance containing
                :term:`unreviewed` :class:`~mediadrop.model.media.Media`.
            encode_page
                A :class:`webhelpers.paginate.Page` instance containing
                :term:`unencoded` :class:`~mediadrop.model.media.Media`.
            publish_page
                A :class:`webhelpers.paginate.Page` instance containing
                :term:`draft` :class:`~mediadrop.model.media.Media`.
            recent_media
                A list of recently published
                :class:`~mediadrop.model.media.Media`.
            comment_count
                Total num comments
            comment_count_published
                Total approved comments
            comment_count_unreviewed
                Total unreviewed comments
            comment_count_trash
                Total deleted comments

        """
        # Any publishable video that does have a publish_on date that is in the
        # past and is publishable is 'Recently Published'
        recent_media = Media.query.published()\
            .order_by(Media.publish_on.desc())[:5]

        return dict(
            review_page = self._fetch_page('awaiting_review'),
            encode_page = self._fetch_page('awaiting_encoding'),
            publish_page = self._fetch_page('awaiting_publishing'),
            recent_media = recent_media,
            comments = Comment.query,
        )


    @expose('admin/media/dash-table.html')
    @observable(events.Admin.IndexController.media_table)
    def media_table(self, table, page, **kwargs):
        """Fetch XHTML to inject when the 'showmore' ajax action is clicked.

        :param table: ``awaiting_review``, ``awaiting_encoding``, or
            ``awaiting_publishing``.
        :type table: ``unicode``
        :param page: Page number, defaults to 1.
        :type page: int
        :rtype: dict
        :returns:
            media
                A list of :class:`~mediadrop.model.media.Media` instances.

        """
        return dict(
            media = self._fetch_page(table, page).items,
        )


    def _fetch_page(self, type='awaiting_review', page=1, items_per_page=6):
        """Helper method for paginating media results"""
        query = Media.query.order_by(Media.modified_on.desc())

        if type == 'awaiting_review':
            query = query.filter_by(reviewed=False)
        elif type == 'awaiting_encoding':
            query = query.filter_by(reviewed=True, encoded=False)
        elif type == 'awaiting_publishing':
            query = query.filter_by(reviewed=True, encoded=True, publishable=False)

        return webhelpers.paginate.Page(query, page, items_per_page)

########NEW FILE########
__FILENAME__ = media
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code contained in this file is licensed under the GPLv3 or
# (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.
"""
Media Admin Controller
"""

import os
from datetime import datetime

from formencode import Invalid, validators
from pylons import request, tmpl_context
from sqlalchemy import orm

from mediadrop.forms.admin import SearchForm, ThumbForm
from mediadrop.forms.admin.media import AddFileForm, EditFileForm, MediaForm, UpdateStatusForm
from mediadrop.lib import helpers
from mediadrop.lib.auth import has_permission
from mediadrop.lib.base import BaseController
from mediadrop.lib.decorators import (autocommit, expose, expose_xhr,
    observable, paginate, validate, validate_xhr)
from mediadrop.lib.helpers import redirect, url_for
from mediadrop.lib.i18n import _
from mediadrop.lib.storage import add_new_media_file
from mediadrop.lib.templating import render
from mediadrop.lib.thumbnails import thumb_path, thumb_paths, create_thumbs_for, create_default_thumbs_for, has_thumbs, has_default_thumbs, delete_thumbs
from mediadrop.model import (Author, Category, Media, Podcast, Tag, fetch_row,
    get_available_slug, slugify)
from mediadrop.model.meta import DBSession
from mediadrop.plugin import events

import logging
log = logging.getLogger(__name__)

media_form = MediaForm()
add_file_form = AddFileForm()
edit_file_form = EditFileForm()
thumb_form = ThumbForm()
update_status_form = UpdateStatusForm()
search_form = SearchForm(action=url_for(controller='/admin/media', action='index'))

class MediaController(BaseController):
    allow_only = has_permission('edit')

    @expose_xhr('admin/media/index.html', 'admin/media/index-table.html')
    @paginate('media', items_per_page=15)
    @observable(events.Admin.MediaController.index)
    def index(self, page=1, search=None, filter=None, podcast=None,
              category=None, tag=None, **kwargs):
        """List media with pagination and filtering.

        :param page: Page number, defaults to 1.
        :type page: int
        :param search: Optional search term to filter by
        :type search: unicode or None
        :param podcast_filter: Optional podcast to filter by
        :type podcast_filter: int or None
        :rtype: dict
        :returns:
            media
                The list of :class:`~mediadrop.model.media.Media` instances
                for this page.
            search
                The given search term, if any
            search_form
                The :class:`~mediadrop.forms.admin.SearchForm` instance
            podcast
                The podcast object for rendering if filtering by podcast.

        """
        media = Media.query.options(orm.undefer('comment_count_published'))

        if search:
            media = media.admin_search(search)
        else:
            media = media.order_by_status()\
                         .order_by(Media.publish_on.desc(),
                                   Media.modified_on.desc())

        if not filter:
            pass
        elif filter == 'unreviewed':
            media = media.reviewed(False)
        elif filter == 'unencoded':
            media = media.reviewed().encoded(False)
        elif filter == 'drafts':
            media = media.drafts()
        elif filter == 'published':
            media = media.published()

        if category:
            category = fetch_row(Category, slug=category)
            media = media.filter(Media.categories.contains(category))
        if tag:
            tag = fetch_row(Tag, slug=tag)
            media = media.filter(Media.tags.contains(tag))
        if podcast:
            podcast = fetch_row(Podcast, slug=podcast)
            media = media.filter(Media.podcast == podcast)

        return dict(
            media = media,
            search = search,
            search_form = search_form,
            media_filter = filter,
            category = category,
            tag = tag,
            podcast = podcast,
        )

    def json_error(self, *args, **kwargs):
        validation_exception = tmpl_context._current_obj().validation_exception
        return dict(success=False, message=validation_exception.msg)

    @expose('admin/media/edit.html')
    @validate(validators={'podcast': validators.Int()})
    @autocommit
    @observable(events.Admin.MediaController.edit)
    def edit(self, id, **kwargs):
        """Display the media forms for editing or adding.

        This page serves as the error_handler for every kind of edit action,
        if anything goes wrong with them they'll be redirected here.

        :param id: Media ID
        :type id: ``int`` or ``"new"``
        :param \*\*kwargs: Extra args populate the form for ``"new"`` media
        :returns:
            media
                :class:`~mediadrop.model.media.Media` instance
            media_form
                The :class:`~mediadrop.forms.admin.media.MediaForm` instance
            media_action
                ``str`` form submit url
            media_values
                ``dict`` form values
            file_add_form
                The :class:`~mediadrop.forms.admin.media.AddFileForm` instance
            file_add_action
                ``str`` form submit url
            file_edit_form
                The :class:`~mediadrop.forms.admin.media.EditFileForm` instance
            file_edit_action
                ``str`` form submit url
            thumb_form
                The :class:`~mediadrop.forms.admin.ThumbForm` instance
            thumb_action
                ``str`` form submit url
            update_status_form
                The :class:`~mediadrop.forms.admin.media.UpdateStatusForm` instance
            update_status_action
                ``str`` form submit url

        """
        media = fetch_row(Media, id)

        if tmpl_context.action == 'save' or id == 'new':
            # Use the values from error_handler or GET for new podcast media
            media_values = kwargs
            user = request.perm.user
            media_values.setdefault('author_name', user.display_name)
            media_values.setdefault('author_email', user.email_address)
        else:
            # Pull the defaults from the media item
            media_values = dict(
                podcast = media.podcast_id,
                slug = media.slug,
                title = media.title,
                author_name = media.author.name,
                author_email = media.author.email,
                description = media.description,
                tags = ', '.join((tag.name for tag in media.tags)),
                categories = [category.id for category in media.categories],
                notes = media.notes,
            )

        # Re-verify the state of our Media object in case the data is nonsensical
        if id != 'new':
            media.update_status()

        return dict(
            media = media,
            media_form = media_form,
            media_action = url_for(action='save'),
            media_values = media_values,
            category_tree = Category.query.order_by(Category.name).populated_tree(),
            file_add_form = add_file_form,
            file_add_action = url_for(action='add_file'),
            file_edit_form = edit_file_form,
            file_edit_action = url_for(action='edit_file'),
            thumb_form = thumb_form,
            thumb_action = url_for(action='save_thumb'),
            update_status_form = update_status_form,
            update_status_action = url_for(action='update_status'),
        )

    @expose_xhr(request_method='POST')
    @validate_xhr(media_form, error_handler=edit)
    @autocommit
    @observable(events.Admin.MediaController.save)
    def save(self, id, slug, title, author_name, author_email,
             description, notes, podcast, tags, categories,
             delete=None, **kwargs):
        """Save changes or create a new :class:`~mediadrop.model.media.Media` instance.

        Form handler the :meth:`edit` action and the
        :class:`~mediadrop.forms.admin.media.MediaForm`.

        Redirects back to :meth:`edit` after successful editing
        and :meth:`index` after successful deletion.

        """
        media = fetch_row(Media, id)

        if delete:
            self._delete_media(media)
            redirect(action='index', id=None)

        if not slug:
            slug = slugify(title)
        elif slug.startswith('_stub_'):
            slug = slug[len('_stub_'):]
        if slug != media.slug:
            media.slug = get_available_slug(Media, slug, media)
        media.title = title
        media.author = Author(author_name, author_email)
        media.description = description
        media.notes = notes
        media.podcast_id = podcast
        media.set_tags(tags)
        media.set_categories(categories)

        media.update_status()
        DBSession.add(media)
        DBSession.flush()

        if id == 'new' and not has_thumbs(media):
            create_default_thumbs_for(media)

        if request.is_xhr:
            status_form_xhtml = unicode(update_status_form.display(
                action=url_for(action='update_status', id=media.id),
                media=media))

            return dict(
                media_id = media.id,
                values = {'slug': slug},
                link = url_for(action='edit', id=media.id),
                status_form = status_form_xhtml,
            )
        else:
            redirect(action='edit', id=media.id)


    @expose('json', request_method='POST')
    @validate(add_file_form, error_handler=json_error)
    @autocommit
    @observable(events.Admin.MediaController.add_file)
    def add_file(self, id, file=None, url=None, **kwargs):
        """Save action for the :class:`~mediadrop.forms.admin.media.AddFileForm`.

        Creates a new :class:`~mediadrop.model.media.MediaFile` from the
        uploaded file or the local or remote URL.

        :param id: Media ID. If ``"new"`` a new Media stub is created.
        :type id: :class:`int` or ``"new"``
        :param file: The uploaded file
        :type file: :class:`cgi.FieldStorage` or ``None``
        :param url: A URL to a recognizable audio or video file
        :type url: :class:`unicode` or ``None``
        :rtype: JSON dict
        :returns:
            success
                bool
            message
                Error message, if unsuccessful
            media_id
                The :attr:`~mediadrop.model.media.Media.id` which is
                important if new media has just been created.
            file_id
                The :attr:`~mediadrop.model.media.MediaFile.id` for the newly
                created file.
            edit_form
                The rendered XHTML :class:`~mediadrop.forms.admin.media.EditFileForm`
                for this file.
            status_form
                The rendered XHTML :class:`~mediadrop.forms.admin.media.UpdateStatusForm`

        """
        if id == 'new':
            media = Media()
            user = request.perm.user
            media.author = Author(user.display_name, user.email_address)
            # Create a temp stub until we can set it to something meaningful
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            media.title = u'Temporary stub %s' % timestamp
            media.slug = get_available_slug(Media, '_stub_' + timestamp)
            media.reviewed = True
            DBSession.add(media)
            DBSession.flush()
        else:
            media = fetch_row(Media, id)

        media_file = add_new_media_file(media, file, url)
        if media.slug.startswith('_stub_'):
            media.title = media_file.display_name
            media.slug = get_available_slug(Media, '_stub_' + media.title)

        # The thumbs may have been created already by add_new_media_file
        if id == 'new' and not has_thumbs(media):
            create_default_thumbs_for(media)

        media.update_status()

        # Render some widgets so the XHTML can be injected into the page
        edit_form_xhtml = unicode(edit_file_form.display(
            action=url_for(action='edit_file', id=media.id),
            file=media_file))
        status_form_xhtml = unicode(update_status_form.display(
            action=url_for(action='update_status', id=media.id),
            media=media))

        data = dict(
            success = True,
            media_id = media.id,
            file_id = media_file.id,
            file_type = media_file.type,
            edit_form = edit_form_xhtml,
            status_form = status_form_xhtml,
            title = media.title,
            slug = media.slug,
            description = media.description,
            link = url_for(action='edit', id=media.id),
            duration = helpers.duration_from_seconds(media.duration),
        )

        return data


    @expose('json', request_method='POST')
    @autocommit
    @observable(events.Admin.MediaController.edit_file)
    def edit_file(self, id, file_id, file_type=None, duration=None, delete=None, bitrate=None, width_height=None, **kwargs):
        """Save action for the :class:`~mediadrop.forms.admin.media.EditFileForm`.

        Changes or deletes a :class:`~mediadrop.model.media.MediaFile`.

        XXX: We do NOT use the @validate decorator due to complications with
             partial validation. The JS sends only the value it wishes to
             change, so we only want to validate that one value.
             FancyValidator.if_missing seems to eat empty values and assign
             them None, but there's an important difference to us between
             None (no value from the user) and an empty value (the user
             is clearing the value of a field).

        :param id: Media ID
        :type id: :class:`int`
        :rtype: JSON dict
        :returns:
            success
                bool
            message
                Error message, if unsuccessful
            status_form
                Rendered XHTML for the status form, updated to reflect the
                changes made.

        """
        media = fetch_row(Media, id)
        data = dict(success=False)
        file_id = int(file_id) # Just in case validation failed somewhere.

        for file in media.files:
            if file.id == file_id:
                break
        else:
            file = None

        fields = edit_file_form.c
        try:
            if file is None:
                data['message'] = _('File "%s" does not exist.') % file_id
            elif file_type:
                file.type = fields.file_type.validate(file_type)
                data['success'] = True
            elif duration is not None:
                media.duration = fields.duration.validate(duration)
                data['success'] = True
                data['duration'] = helpers.duration_from_seconds(media.duration)
            elif width_height is not None:
                width_height = fields.width_height.validate(width_height)
                file.width, file.height = width_height or (0, 0)
                data['success'] = True
            elif bitrate is not None:
                file.bitrate = fields.bitrate.validate(bitrate)
                data['success'] = True
            elif delete:
                file.storage.delete(file.unique_id)
                DBSession.delete(file)
                DBSession.flush()
                # media.files must be updated to reflect the file deletion above
                DBSession.refresh(media)
                data['success'] = True
            else:
                data['message'] = _('No action to perform.')
        except Invalid, e:
            data['success'] = False
            data['message'] = unicode(e)

        if data['success']:
            data['file_type'] = file.type
            media.update_status()
            DBSession.flush()

            # Return the rendered widget for injection
            status_form_xhtml = unicode(update_status_form.display(
                action=url_for(action='update_status'), media=media))
            data['status_form'] = status_form_xhtml
        return data


    @expose('json', request_method='POST')
    @autocommit
    @observable(events.Admin.MediaController.merge_stubs)
    def merge_stubs(self, orig_id, input_id, **kwargs):
        """Merge in a newly created media item.

        This is merges media that has just been created. It must have:
            1. a non-default thumbnail, or
            2. a file, or
            3. a title, description, etc

        :param orig_id: Media ID to copy data to
        :type orig_id: ``int``
        :param input_id: Media ID to source files, thumbs, etc from
        :type input_id: ``int``
        :returns: JSON dict

        """
        orig = fetch_row(Media, orig_id)
        input = fetch_row(Media, input_id)
        merged_files = []

        # Merge in the file(s) from the input stub
        if input.slug.startswith('_stub_') and input.files:
            for file in input.files[:]:
                # XXX: The filename will still use the old ID
                file.media = orig
                merged_files.append(file)
            DBSession.delete(input)

        # The original is a file or thumb stub, copy in the new values
        elif orig.slug.startswith('_stub_') \
        and not input.slug.startswith('_stub_'):
            DBSession.delete(input)
            DBSession.flush()
            orig.podcast = input.podcast
            orig.title = input.title
            orig.subtitle = input.subtitle
            orig.slug = input.slug
            orig.author = input.author
            orig.description = input.description
            orig.notes = input.notes
            orig.duration = input.duration
            orig.views = input.views
            orig.likes = input.likes
            orig.publish_on = input.publish_on
            orig.publish_until = input.publish_until
            orig.categories = input.categories
            orig.tags = input.tags
            orig.update_popularity()

        # Copy the input thumb over the default thumbnail
        elif input.slug.startswith('_stub_') \
        and has_default_thumbs(orig) \
        and not has_default_thumbs(input):
            for key, dst_path in thumb_paths(orig).iteritems():
                src_path = thumb_path(input, key)
                # This will raise an OSError on Windows, but not *nix
                os.rename(src_path, dst_path)
            DBSession.delete(input)

        # Report an error
        else:
            return dict(
                success = False,
                message = u'No merge operation fits.',
            )

        orig.update_status()

        status_form_xhtml = unicode(update_status_form.display(
            action=url_for(action='update_status', id=orig.id),
            media=orig))

        file_xhtml = {}
        for file in merged_files:
            file_xhtml[file.id] = unicode(edit_file_form.display(
                action=url_for(action='edit_file', id=orig.id),
                file=file))

        return dict(
            success = True,
            media_id = orig.id,
            title = orig.title,
            link = url_for(action='edit', id=orig.id),
            status_form = status_form_xhtml,
            file_forms = file_xhtml,
        )


    @expose('json', request_method='POST')
    @validate(thumb_form, error_handler=json_error)
    @autocommit
    @observable(events.Admin.MediaController.save_thumb)
    def save_thumb(self, id, thumb, **kwargs):
        """Save a thumbnail uploaded with :class:`~mediadrop.forms.admin.ThumbForm`.

        :param id: Media ID. If ``"new"`` a new Media stub is created.
        :type id: ``int`` or ``"new"``
        :param file: The uploaded file
        :type file: :class:`cgi.FieldStorage` or ``None``
        :rtype: JSON dict
        :returns:
            success
                bool
            message
                Error message, if unsuccessful
            id
                The :attr:`~mediadrop.model.media.Media.id` which is
                important if a new media has just been created.

        """
        if id == 'new':
            media = Media()
            user = request.perm.user
            media.author = Author(user.display_name, user.email_address)
            media.title = os.path.basename(thumb.filename)
            media.slug = get_available_slug(Media, '_stub_' + media.title)
            DBSession.add(media)
            DBSession.flush()
        else:
            media = fetch_row(Media, id)

        try:
            # Create JPEG thumbs
            create_thumbs_for(media, thumb.file, thumb.filename)
            success = True
            message = None
        except IOError, e:
            success = False
            if id == 'new':
                DBSession.delete(media)
            if e.errno == 13:
                message = _('Permission denied, cannot write file')
            elif e.message == 'cannot identify image file':
                message = _('Unsupported image type: %s') \
                    % os.path.splitext(thumb.filename)[1].lstrip('.')
            elif e.message == 'cannot read interlaced PNG files':
                message = _('Interlaced PNGs are not supported.')
            else:
                raise
        except Exception:
            if id == 'new':
                DBSession.delete(media)
            raise

        return dict(
            success = success,
            message = message,
            id = media.id,
            title = media.title,
            slug = media.slug,
            link = url_for(action='edit', id=media.id),
        )


    @expose('json', request_method='POST')
    @validate(update_status_form, error_handler=edit)
    @autocommit
    @observable(events.Admin.MediaController.update_status)
    def update_status(self, id, status=None, publish_on=None, publish_until=None, **values):
        """Update the publish status for the given media.

        :param id: Media ID
        :type id: ``int``
        :param update_status: The text of the submit button which indicates
            that the :attr:`~mediadrop.model.media.Media.status` should change.
        :type update_status: ``unicode`` or ``None``
        :param publish_on: A date to set to
            :attr:`~mediadrop.model.media.Media.publish_on`
        :type publish_on: :class:`datetime.datetime` or ``None``
        :param publish_until: A date to set to
            :attr:`~mediadrop.model.media.Media.publish_until`
        :type publish_until: :class:`datetime.datetime` or ``None``
        :rtype: JSON dict
        :returns:
            success
                bool
            message
                Error message, if unsuccessful
            status_form
                Rendered XHTML for the status form, updated to reflect the
                changes made.

        """
        media = fetch_row(Media, id)
        new_slug = None

        # Make the requested change assuming it will be allowed
        if status == 'unreviewed':
            media.reviewed = True
        elif status == 'draft':
            self._publish_media(media, publish_on)
        elif publish_on:
            media.publish_on = publish_on
            media.update_popularity()
        elif publish_until:
            media.publish_until = publish_until

        # Verify the change is valid by re-determining the status
        media.update_status()
        DBSession.flush()

        if request.is_xhr:
            # Return the rendered widget for injection
            status_form_xhtml = unicode(update_status_form.display(
                action=url_for(action='update_status'), media=media))
            return dict(
                success = True,
                status_form = status_form_xhtml,
                slug = new_slug,
            )
        else:
            redirect(action='edit')

    @expose('json', request_method='POST')
    @autocommit
    @observable(events.Admin.MediaController.bulk)
    def bulk(self, type=None, ids=None, **kwargs):
        """Perform bulk operations on media items

        :param type: The type of bulk action to perform (delete)
        :param ids: A list of IDs.

        """
        if not ids:
            ids = []
        elif not isinstance(ids, list):
            ids = [ids]

        media = Media.query.filter(Media.id.in_(ids)).all()
        success = True
        rows = None

        def render_rows(media):
            rows = {}
            for m in media:
                stream = render('admin/media/index-table.html', {'media': [m]})
                rows[m.id] = unicode(stream.select('table/tbody/tr'))
            return rows

        if type == 'review':
            for m in media:
                m.reviewed = True
            rows = render_rows(media)
        elif type == 'publish':
            for m in media:
                m.reviewed = True
                if m.encoded:
                    self._publish_media(m)
            rows = render_rows(media)
        elif type == 'delete':
            for m in media:
                self._delete_media(m)
        else:
            success = False

        return dict(
            success = success,
            ids = ids,
            rows = rows,
        )

    def _publish_media(self, media, publish_on=None):
        media.publishable = True
        media.publish_on = publish_on or media.publish_on or datetime.now()
        media.update_popularity()
        # Remove the stub prefix if the user wants the default media title
        if media.slug.startswith('_stub_'):
            new_slug = get_available_slug(Media, media.slug[len('_stub_'):])
            media.slug = new_slug

    def _delete_media(self, media):
        # FIXME: Ensure that if the first file is deleted from the file system,
        #        then the second fails, the first file is deleted from the
        #        file system and not linking to a nonexistent file.
        # Delete every file from the storage engine
        for file in media.files:
            file.storage.delete(file.unique_id)
            # Remove this item from the DBSession so that the foreign key
            # ON DELETE CASCADE can take effect.
            DBSession.expunge(file)
        # Delete the media
        DBSession.delete(media)
        DBSession.flush()
        # Cleanup the thumbnails
        delete_thumbs(media)

########NEW FILE########
__FILENAME__ = players
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code contained in this file is licensed under the GPLv3 or
# (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.

import logging

from pylons import tmpl_context
from webob.exc import HTTPException

from mediadrop.lib.auth import has_permission
from mediadrop.lib.base import BaseController
from mediadrop.lib.decorators import autocommit, expose, observable, validate
from mediadrop.lib.helpers import redirect, url_for
from mediadrop.lib.players import update_enabled_players
from mediadrop.model import (DBSession, PlayerPrefs, fetch_row,
    cleanup_players_table)
from mediadrop.plugin import events

log = logging.getLogger(__name__)

class PlayersController(BaseController):
    """Admin player preference actions"""
    allow_only = has_permission('admin')

    @expose('admin/players/index.html')
    @observable(events.Admin.PlayersController.index)
    def index(self, **kwargs):
        """List players.

        :rtype: Dict
        :returns:
            players
                The list of :class:`~mediadrop.model.players.PlayerPrefs`
                instances for this page.

        """
        players = PlayerPrefs.query.order_by(PlayerPrefs.priority).all()

        return {
            'players': players,
        }

    @expose('admin/players/edit.html')
    @observable(events.Admin.PlayersController.edit)
    def edit(self, id, name=None, **kwargs):
        """Display the :class:`~mediadrop.model.players.PlayerPrefs` for editing or adding.

        :param id: PlayerPrefs ID
        :type id: ``int`` or ``"new"``
        :rtype: dict
        :returns:

        """
        playerp = fetch_row(PlayerPrefs, id)

        return {
            'player': playerp,
            'form': playerp.settings_form,
            'form_action': url_for(action='save'),
            'form_values': kwargs,
        }

    @expose(request_method='POST')
    @autocommit
    def save(self, id, **kwargs):
        player = fetch_row(PlayerPrefs, id)
        form = player.settings_form

        if id == 'new':
            DBSession.add(player)

        @validate(form, error_handler=self.edit)
        def save(id, **kwargs):
            # Allow the form to modify the player directly
            # since each can have radically different fields.
            save_func = getattr(form, 'save_data')
            save_func(player, **tmpl_context.form_values)
            redirect(controller='/admin/players', action='index')

        return save(id, **kwargs)

    @expose(request_method='POST')
    @autocommit
    @observable(events.Admin.PlayersController.delete)
    def delete(self, id, **kwargs):
        """Delete a PlayerPref.

        After deleting the PlayerPref, cleans up the players table,
        ensuring that each Player class is represented--if the deleted
        PlayerPref is the last example of that Player class, creates a new
        disabled PlayerPref for that Player class with the default settings.

        :param id: Player ID.
        :type id: ``int``
        :returns: Redirect back to :meth:`index` after successful delete.
        """
        player = fetch_row(PlayerPrefs, id)
        DBSession.delete(player)
        DBSession.flush()
        cleanup_players_table()
        redirect(action='index', id=None)

    @expose(request_method='POST')
    @autocommit
    @observable(events.Admin.PlayersController.enable)
    def enable(self, id, **kwargs):
        """Enable a PlayerPref.

        :param id: Player ID.
        :type id: ``int``
        :returns: Redirect back to :meth:`index` after success.
        """
        player = fetch_row(PlayerPrefs, id)
        player.enabled = True
        update_enabled_players()
        redirect(action='index', id=None)

    @expose(request_method='POST')
    @autocommit
    @observable(events.Admin.PlayersController.disable)
    def disable(self, id, **kwargs):
        """Disable a PlayerPref.

        :param id: Player ID.
        :type id: ``int``
        :returns: Redirect back to :meth:`index` after success.
        """
        player = fetch_row(PlayerPrefs, id)
        player.enabled = False
        update_enabled_players()
        redirect(action='index', id=None)

    @expose(request_method='POST')
    @autocommit
    @observable(events.Admin.PlayersController.reorder)
    def reorder(self, id, direction, **kwargs):
        """Reorder a PlayerPref.

        :param id: Player ID.
        :type id: ``int``
        :param direction: ``"up"`` for higher priority, ``"down"`` for
            lower priority
        :type direction: ``unicode``
        :returns: Redirect back to :meth:`index` after success.
        """
        if direction == 'up':
            offset = -1
        elif direction == 'down':
            offset = 1
        else:
            return

        player1 = fetch_row(PlayerPrefs, id)
        new_priority = player1.priority + offset
        try:
            player2 = fetch_row(PlayerPrefs, priority=new_priority)
            player2.priority = player1.priority
            player1.priority = new_priority
        except HTTPException, e:
            if e.code != 404:
                raise

        redirect(action='index', id=None)

########NEW FILE########
__FILENAME__ = podcasts
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code contained in this file is licensed under the GPLv3 or
# (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.

import os

from pylons import request, tmpl_context
from sqlalchemy import orm

from mediadrop.forms.admin import ThumbForm
from mediadrop.forms.admin.podcasts import PodcastForm
from mediadrop.lib.auth import has_permission
from mediadrop.lib.base import BaseController
from mediadrop.lib.decorators import (autocommit, expose, expose_xhr,
    observable, paginate, validate)
from mediadrop.lib.helpers import redirect, url_for
from mediadrop.lib.i18n import _
from mediadrop.lib.thumbnails import (create_default_thumbs_for,
    create_thumbs_for, delete_thumbs)
from mediadrop.model import Author, Podcast, fetch_row, get_available_slug
from mediadrop.model.meta import DBSession
from mediadrop.plugin import events

import logging
log = logging.getLogger(__name__)

podcast_form = PodcastForm()
thumb_form = ThumbForm()

class PodcastsController(BaseController):
    allow_only = has_permission('edit')

    @expose_xhr('admin/podcasts/index.html',
                'admin/podcasts/index-table.html')
    @paginate('podcasts', items_per_page=10)
    @observable(events.Admin.PodcastsController.index)
    def index(self, page=1, **kw):
        """List podcasts with pagination.

        :param page: Page number, defaults to 1.
        :type page: int
        :rtype: Dict
        :returns:
            podcasts
                The list of :class:`~mediadrop.model.podcasts.Podcast`
                instances for this page.
        """
        podcasts = DBSession.query(Podcast)\
            .options(orm.undefer('media_count'))\
            .order_by(Podcast.title)
        return dict(podcasts=podcasts)


    @expose('admin/podcasts/edit.html')
    @observable(events.Admin.PodcastsController.edit)
    def edit(self, id, **kwargs):
        """Display the podcast forms for editing or adding.

        This page serves as the error_handler for every kind of edit action,
        if anything goes wrong with them they'll be redirected here.

        :param id: Podcast ID
        :type id: ``int`` or ``"new"``
        :param \*\*kwargs: Extra args populate the form for ``"new"`` podcasts
        :returns:
            podcast
                :class:`~mediadrop.model.podcasts.Podcast` instance
            form
                :class:`~mediadrop.forms.admin.podcasts.PodcastForm` instance
            form_action
                ``str`` form submit url
            form_values
                ``dict`` form values
            thumb_form
                :class:`~mediadrop.forms.admin.ThumbForm` instance
            thumb_action
                ``str`` form submit url

        """
        podcast = fetch_row(Podcast, id)

        if tmpl_context.action == 'save' or id == 'new':
            form_values = kwargs
            user = request.perm.user
            form_values.setdefault('author_name', user.display_name)
            form_values.setdefault('author_email', user.email_address)
            form_values.setdefault('feed', {}).setdefault('feed_url',
                _('Save the podcast to get your feed URL'))
        else:
            explicit_values = {True: 'yes', False: 'clean', None: 'no'}
            form_values = dict(
                slug = podcast.slug,
                title = podcast.title,
                subtitle = podcast.subtitle,
                author_name = podcast.author and podcast.author.name or None,
                author_email = podcast.author and podcast.author.email or None,
                description = podcast.description,
                details = dict(
                    explicit = explicit_values.get(podcast.explicit),
                    category = podcast.category,
                    copyright = podcast.copyright,
                ),
                feed = dict(
                    feed_url = url_for(controller='/podcasts', action='feed',
                                       slug=podcast.slug, qualified=True),
                    itunes_url = podcast.itunes_url,
                    feedburner_url = podcast.feedburner_url,
                ),
            )

        return dict(
            podcast = podcast,
            form = podcast_form,
            form_action = url_for(action='save'),
            form_values = form_values,
            thumb_form = thumb_form,
            thumb_action = url_for(action='save_thumb'),
        )


    @expose(request_method='POST')
    @validate(podcast_form, error_handler=edit)
    @autocommit
    @observable(events.Admin.PodcastsController.save)
    def save(self, id, slug, title, subtitle, author_name, author_email,
             description, details, feed, delete=None, **kwargs):
        """Save changes or create a new :class:`~mediadrop.model.podcasts.Podcast` instance.

        Form handler the :meth:`edit` action and the
        :class:`~mediadrop.forms.admin.podcasts.PodcastForm`.

        Redirects back to :meth:`edit` after successful editing
        and :meth:`index` after successful deletion.

        """
        podcast = fetch_row(Podcast, id)

        if delete:
            DBSession.delete(podcast)
            DBSession.commit()
            delete_thumbs(podcast)
            redirect(action='index', id=None)

        if not slug:
            slug = title
        if slug != podcast.slug:
            podcast.slug = get_available_slug(Podcast, slug, podcast)
        podcast.title = title
        podcast.subtitle = subtitle
        podcast.author = Author(author_name, author_email)
        podcast.description = description
        podcast.copyright = details['copyright']
        podcast.category = details['category']
        podcast.itunes_url = feed['itunes_url']
        podcast.feedburner_url = feed['feedburner_url']
        podcast.explicit = {'yes': True, 'clean': False}.get(details['explicit'], None)

        if id == 'new':
            DBSession.add(podcast)
            DBSession.flush()
            create_default_thumbs_for(podcast)

        redirect(action='edit', id=podcast.id)


    @expose('json', request_method='POST')
    @validate(thumb_form, error_handler=edit)
    @observable(events.Admin.PodcastsController.save_thumb)
    def save_thumb(self, id, thumb, **values):
        """Save a thumbnail uploaded with :class:`~mediadrop.forms.admin.ThumbForm`.

        :param id: Media ID. If ``"new"`` a new Podcast stub is created.
        :type id: ``int`` or ``"new"``
        :param file: The uploaded file
        :type file: :class:`cgi.FieldStorage` or ``None``
        :rtype: JSON dict
        :returns:
            success
                bool
            message
                Error message, if unsuccessful
            id
                The :attr:`~mediadrop.model.podcasts.Podcast.id` which is
                important if a new podcast has just been created.

        """
        if id == 'new':
            return dict(
                success = False,
                message = u'You must first save the podcast before you can upload a thumbnail',
            )

        podcast = fetch_row(Podcast, id)

        try:
            # Create JPEG thumbs
            create_thumbs_for(podcast, thumb.file, thumb.filename)
            success = True
            message = None
        except IOError, e:
            success = False
            if e.errno == 13:
                message = _('Permission denied, cannot write file')
            elif e.message == 'cannot identify image file':
                message = _('Unsupport image type: %s') \
                    % os.path.splitext(thumb.filename)[1].lstrip('.')
            elif e.message == 'cannot read interlaced PNG files':
                message = _('Interlaced PNGs are not supported.')
            else:
                raise

        return dict(
            success = success,
            message = message,
        )

########NEW FILE########
__FILENAME__ = settings
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code contained in this file is licensed under the GPLv3 or
# (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.

import os
import shutil

from cgi import FieldStorage
from babel.core import Locale
from pylons import config, request, tmpl_context as c

from mediadrop.forms.admin.settings import (AdvertisingForm, AppearanceForm,
    APIForm, AnalyticsForm, CommentsForm, GeneralForm,
    NotificationsForm, PopularityForm, SiteMapsForm, UploadForm)
from mediadrop.lib.base import BaseSettingsController
from mediadrop.lib.decorators import autocommit, expose, observable, validate
from mediadrop.lib.helpers import filter_vulgarity, redirect, url_for
from mediadrop.lib.i18n import LanguageError, Translator
from mediadrop.model import Comment, Media
from mediadrop.model.meta import DBSession
from mediadrop.plugin import events
from mediadrop.websetup import appearance_settings, generate_appearance_css

import logging
log = logging.getLogger(__name__)

notifications_form = NotificationsForm(
    action=url_for(controller='/admin/settings', action='notifications_save'))

comments_form = CommentsForm(
    action=url_for(controller='/admin/settings', action='comments_save'))

api_form = APIForm(
    action=url_for(controller='/admin/settings', action='save_api'))

popularity_form = PopularityForm(
    action=url_for(controller='/admin/settings', action='popularity_save'))

upload_form = UploadForm(
    action=url_for(controller='/admin/settings', action='upload_save'))

analytics_form = AnalyticsForm(
    action=url_for(controller='/admin/settings', action='analytics_save'))

general_form = GeneralForm(
    action=url_for(controller='/admin/settings', action='general_save'))

sitemaps_form = SiteMapsForm(
    action=url_for(controller='/admin/settings', action='sitemaps_save'))

appearance_form = AppearanceForm(
    action=url_for(controller='/admin/settings', action='appearance_save'))

advertising_form = AdvertisingForm(
    action=url_for(controller='/admin/settings', action='advertising_save'))


class SettingsController(BaseSettingsController):
    """
    Dumb controller for display and saving basic settings forms.

    See :class:`mediadrop.lib.base.BaseSettingsController` for more details.

    """
    @expose()
    def index(self, **kwargs):
        redirect(action='general')

    @expose('admin/settings/notifications.html')
    def notifications(self, **kwargs):
        return self._display(notifications_form, values=kwargs)

    @expose(request_method='POST')
    @validate(notifications_form, error_handler=notifications)
    @autocommit
    @observable(events.Admin.SettingsController.notifications_save)
    def notifications_save(self, **kwargs):
        """Save :class:`~mediadrop.forms.admin.settings.NotificationsForm`."""
        return self._save(notifications_form, 'notifications', values=kwargs)

    @expose('admin/settings/comments.html')
    def comments(self, **kwargs):
        return self._display(comments_form, values=kwargs)

    @expose(request_method='POST')
    @validate(comments_form, error_handler=comments)
    @autocommit
    @observable(events.Admin.SettingsController.comments_save)
    def comments_save(self, **kwargs):
        """Save :class:`~mediadrop.forms.admin.settings.CommentsForm`."""
        old_vulgarity_filter = c.settings['vulgarity_filtered_words'].value

        self._save(comments_form, values=kwargs)

        # Run the filter now if it has changed
        if old_vulgarity_filter != c.settings['vulgarity_filtered_words'].value:
            for comment in DBSession.query(Comment):
                comment.body = filter_vulgarity(comment.body)

        redirect(action='comments')

    @expose('admin/settings/api.html')
    def api(self, **kwargs):
        return self._display(api_form, values=kwargs)

    @expose(request_method='POST')
    @validate(api_form, error_handler=comments)
    @autocommit
    @observable(events.Admin.SettingsController.save_api)
    def save_api(self, **kwargs):
        """Save :class:`~mediadrop.forms.admin.settings.APIForm`."""
        return self._save(api_form, 'api', values=kwargs)

    @expose('admin/settings/popularity.html')
    def popularity(self, **kwargs):
        return self._display(popularity_form, values=kwargs)

    @expose(request_method='POST')
    @validate(popularity_form, error_handler=popularity)
    @autocommit
    @observable(events.Admin.SettingsController.popularity_save)
    def popularity_save(self, **kwargs):
        """Save :class:`~mediadrop.forms.admin.settings.PopularityForm`.

        Updates the popularity for every media item based on the submitted
        values.
        """
        self._save(popularity_form, values=kwargs)
        # ".util.calculate_popularity()" uses the popularity settings from
        # the request.settings which are only updated when a new request
        # comes in.
        # update the settings manually so the popularity is actually updated
        # correctly.
        for key in ('popularity_decay_exponent', 'popularity_decay_lifetime'):
            request.settings[key] = kwargs['popularity.'+key]
        for m in Media.query:
            m.update_popularity()
            DBSession.add(m)
        redirect(action='popularity')

    @expose('admin/settings/upload.html')
    def upload(self, **kwargs):
        return self._display(upload_form, values=kwargs)

    @expose(request_method='POST')
    @validate(upload_form, error_handler=upload)
    @autocommit
    @observable(events.Admin.SettingsController.upload_save)
    def upload_save(self, **kwargs):
        """Save :class:`~mediadrop.forms.admin.settings.UploadForm`."""
        return self._save(upload_form, 'upload', values=kwargs)

    @expose('admin/settings/analytics.html')
    def analytics(self, **kwargs):
        return self._display(analytics_form, values=kwargs)

    @expose(request_method='POST')
    @validate(analytics_form, error_handler=analytics)
    @autocommit
    @observable(events.Admin.SettingsController.analytics_save)
    def analytics_save(self, **kwargs):
        """Save :class:`~mediadrop.forms.admin.settings.AnalyticsForm`."""
        return self._save(analytics_form, 'analytics', values=kwargs)

    @expose('admin/settings/general.html')
    def general(self, **kwargs):
        if not c.settings['primary_language'].value:
            kwargs.setdefault('general', {}).setdefault('primary_language', 'en')
        return self._display(general_form, values=kwargs)

    @expose(request_method='POST')
    @validate(general_form, error_handler=general)
    @autocommit
    @observable(events.Admin.SettingsController.general_save)
    def general_save(self, **kwargs):
        """Save :class:`~mediadrop.forms.admin.settings.GeneralForm`."""
        # Ensure this translation actually works before saving it
        lang = kwargs.get('general', {}).get('primary_language')
        if lang:
            locale = Locale.parse(lang)
            t = Translator(locale, config['locale_dirs'])
            try:
                t._load_domain('mediadrop')
            except LanguageError:
                # TODO: Show an error message on the language field
                kwargs['primary_language'] = None
        return self._save(general_form, 'general', values=kwargs)

    @expose('admin/settings/sitemaps.html')
    def sitemaps(self, **kwargs):
        return self._display(sitemaps_form, values=kwargs)

    @expose(request_method='POST')
    @validate(sitemaps_form, error_handler=sitemaps)
    @autocommit
    @observable(events.Admin.SettingsController.sitemaps_save)
    def sitemaps_save(self, **kwargs):
        """Save :class:`~mediadrop.forms.admin.settings.SiteMapsForm`."""
        return self._save(sitemaps_form, 'sitemaps', values=kwargs)

    @expose('admin/settings/appearance.html')
    def appearance(self, **kwargs):
        return self._display(appearance_form, values=kwargs)

    @expose(request_method='POST')
    @validate(appearance_form, error_handler=appearance)
    @autocommit
    @observable(events.Admin.SettingsController.appearance_save)
    def appearance_save(self, **kwargs):
        """Save :class:`~mediadrop.forms.admin.settings.appearanceForm`."""
        settings = request.settings
        accepted_extensions = ('.png', '.jpg', '.jpeg', '.gif')
        upload_field_filenames = [
            ('appearance_logo', 'logo'),
            ('appearance_background_image', 'bg_image'),
        ]

        #Handle a reset to defaults request first
        if kwargs.get('reset', None):
            self._update_settings(dict(appearance_settings))
            generate_appearance_css(appearance_settings)
            return redirect(controller='admin/settings', action='appearance')

        appearance_dir = os.path.join(config['pylons.cache_dir'], 'appearance')

        for field_name, file_name in upload_field_filenames:
            field = kwargs['general'].pop(field_name)
            if isinstance(field, FieldStorage):
                extension = os.path.splitext(field.filename)[1].lower()
                if extension in accepted_extensions:
                    #TODO: Need to sanitize manually here?
                    full_name = '%s%s' % (file_name, extension)
                    permanent_file = open(os.path.join(appearance_dir,
                                                       full_name), 'w')
                    shutil.copyfileobj(field.file, permanent_file)
                    permanent_file.close()
                    field.file.close()
                    kwargs['general'][field_name] = full_name
                    continue
            # Preserve existing setting
            kwargs['general'][field_name] = settings.get(field_name, '')

        self._save(appearance_form, values=kwargs)
        generate_appearance_css(
            [(key, setting.value) for key, setting in c.settings.iteritems()],
        )
        redirect(action='appearance')

    @expose('admin/settings/advertising.html')
    def advertising(self, **kwargs):
        return self._display(advertising_form, values=kwargs)

    @expose(request_method='POST')
    @validate(advertising_form, error_handler=general)
    @autocommit
    @observable(events.Admin.SettingsController.advertising_save)
    def advertising_save(self, **kwargs):
        """Save :class:`~mediadrop.forms.admin.settings.AdvertisingForm`."""
        return self._save(advertising_form, 'advertising', values=kwargs)


########NEW FILE########
__FILENAME__ = storage
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code contained in this file is licensed under the GPLv3 or
# (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.

import logging

from pylons import tmpl_context
from sqlalchemy import orm

from mediadrop.lib.auth import has_permission
from mediadrop.lib.base import BaseController
from mediadrop.lib.decorators import autocommit, expose, observable, validate
from mediadrop.lib.helpers import redirect, url_for
from mediadrop.lib.storage import sort_engines, StorageEngine
from mediadrop.model import DBSession, fetch_row
from mediadrop.plugin import events

log = logging.getLogger(__name__)

class StorageController(BaseController):
    """Admin storage engine actions"""
    allow_only = has_permission('admin')

    @expose('admin/storage/index.html')
    @observable(events.Admin.StorageController.index)
    def index(self, page=1, **kwargs):
        """List storage engines with pagination.

        :rtype: Dict
        :returns:
            engines
                The list of :class:`~mediadrop.lib.storage.StorageEngine`
                instances for this page.

        """
        engines = DBSession.query(StorageEngine)\
            .options(orm.undefer('file_count'),
                     orm.undefer('file_size_sum'))\
            .all()
        engines = list(sort_engines(engines))
        existing_types = set(ecls.engine_type for ecls in engines)
        addable_engines = [
            ecls
            for ecls in StorageEngine
            if not ecls.is_singleton or ecls.engine_type not in existing_types
        ]

        return {
            'engines': engines,
            'addable_engines': addable_engines,
        }

    @expose('admin/storage/edit.html')
    @observable(events.Admin.StorageController.edit)
    def edit(self, id, engine_type=None, **kwargs):
        """Display the :class:`~mediadrop.lib.storage.StorageEngine` for editing or adding.

        :param id: Storage ID
        :type id: ``int`` or ``"new"``
        :rtype: dict
        :returns:

        """
        engine = self.fetch_engine(id, engine_type)

        return {
            'engine': engine,
            'form': engine.settings_form,
            'form_action': url_for(action='save', engine_type=engine_type),
            'form_values': kwargs,
        }

    @expose(request_method='POST')
    @autocommit
    def save(self, id, engine_type=None, **kwargs):
        if id == 'new':
            assert engine_type is not None, 'engine_type must be specified when saving a new StorageEngine.'

        engine = self.fetch_engine(id, engine_type)
        form = engine.settings_form

        if id == 'new':
            DBSession.add(engine)

        @validate(form, error_handler=self.edit)
        def save_engine_params(id, general, **kwargs):
            # Allow the form to modify the StorageEngine directly
            # since each can have radically different fields.
            save_func = getattr(form, 'save_engine_params')
            save_func(engine, **tmpl_context.form_values)
            redirect(controller='/admin/storage', action='index')

        return save_engine_params(id, **kwargs)

    def fetch_engine(self, id, engine_type=None):
        if id != 'new':
            engine = fetch_row(StorageEngine, id)
        else:
            types = dict((cls.engine_type, cls) for cls in StorageEngine)
            engine_cls = types.get(engine_type, None)
            if not engine_cls:
                redirect(controller='/admin/storage', action='index')
            engine = engine_cls()
        return engine

    @expose('json', request_method='POST')
    @autocommit
    @observable(events.Admin.StorageController.delete)
    def delete(self, id, **kwargs):
        """Delete a StorageEngine.

        :param id: Storage ID.
        :type id: ``int``
        :returns: Redirect back to :meth:`index` after successful delete.
        """
        engine = fetch_row(StorageEngine, id)
        files = engine.files
        for f in files:
            engine.delete(f.unique_id)
        DBSession.delete(engine)
        redirect(action='index', id=None)

    @expose(request_method='POST')
    @autocommit
    @observable(events.Admin.StorageController.enable)
    def enable(self, id, **kwargs):
        """Enable a StorageEngine.

        :param id: Storage ID.
        :type id: ``int``
        :returns: Redirect back to :meth:`index` after success.
        """
        engine = fetch_row(StorageEngine, id)
        engine.enabled = True
        redirect(action='index', id=None)

    @expose(request_method='POST')
    @autocommit
    @observable(events.Admin.StorageController.disable)
    def disable(self, id, **kwargs):
        """Disable a StorageEngine.

        :param id: engine ID.
        :type id: ``int``
        :returns: Redirect back to :meth:`index` after success.
        """
        engine = fetch_row(StorageEngine, id)
        engine.enabled = False
        redirect(action='index', id=None)

########NEW FILE########
__FILENAME__ = tags
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code contained in this file is licensed under the GPLv3 or
# (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.

from pylons import request, tmpl_context
from sqlalchemy import orm

from mediadrop.forms.admin.tags import TagForm, TagRowForm
from mediadrop.lib.auth import has_permission
from mediadrop.lib.base import BaseController
from mediadrop.lib.decorators import (autocommit, expose, observable, paginate, 
    validate)
from mediadrop.lib.helpers import redirect
from mediadrop.model import Tag, fetch_row, get_available_slug
from mediadrop.model.meta import DBSession
from mediadrop.plugin import events

import logging
log = logging.getLogger(__name__)

tag_form = TagForm()
tag_row_form = TagRowForm()

class TagsController(BaseController):
    allow_only = has_permission('edit')

    @expose('admin/tags/index.html')
    @paginate('tags', items_per_page=25)
    @observable(events.Admin.TagsController.index)
    def index(self, page=1, **kwargs):
        """List tags with pagination.

        :param page: Page number, defaults to 1.
        :type page: int
        :rtype: Dict
        :returns:
            tags
                The list of :class:`~mediadrop.model.tags.Tag`
                instances for this page.
            tag_form
                The :class:`~mediadrop.forms.admin.settings.tags.TagForm` instance.

        """
        tags = DBSession.query(Tag)\
            .options(orm.undefer('media_count'))\
            .order_by(Tag.name)

        return dict(
            tags = tags,
            tag_form = tag_form,
            tag_row_form = tag_row_form,
        )

    @expose('admin/tags/edit.html')
    @observable(events.Admin.TagsController.edit)
    def edit(self, id, **kwargs):
        """Edit a single tag.

        :param id: Tag ID
        :rtype: Dict
        :returns:
            tags
                The list of :class:`~mediadrop.model.tags.Tag`
                instances for this page.
            tag_form
                The :class:`~mediadrop.forms.admin.settings.tags.TagForm` instance.

        """
        tag = fetch_row(Tag, id)

        return dict(
            tag = tag,
            tag_form = tag_form,
        )

    @expose('json', request_method='POST')
    @validate(tag_form)
    @autocommit
    @observable(events.Admin.TagsController.save)
    def save(self, id, delete=False, **kwargs):
        """Save changes or create a tag.

        See :class:`~mediadrop.forms.admin.settings.tags.TagForm` for POST vars.

        :param id: Tag ID
        :rtype: JSON dict
        :returns:
            success
                bool

        """
        if tmpl_context.form_errors:
            if request.is_xhr:
                return dict(success=False, errors=tmpl_context.form_errors)
            else:
                # TODO: Add error reporting for users with JS disabled?
                return redirect(action='edit')

        tag = fetch_row(Tag, id)

        if delete:
            DBSession.delete(tag)
            data = dict(success=True, id=tag.id)
        else:
            tag.name = kwargs['name']
            tag.slug = get_available_slug(Tag, kwargs['slug'], tag)
            DBSession.add(tag)
            DBSession.flush()
            data = dict(
                success = True,
                id = tag.id,
                name = tag.name,
                slug = tag.slug,
                row = unicode(tag_row_form.display(tag=tag)),
            )

        if request.is_xhr:
            return data
        else:
            redirect(action='index', id=None)

    @expose('json', request_method='POST')
    @autocommit
    @observable(events.Admin.TagsController.bulk)
    def bulk(self, type=None, ids=None, **kwargs):
        """Perform bulk operations on media items

        :param type: The type of bulk action to perform (delete)
        :param ids: A list of IDs.

        """
        if not ids:
            ids = []
        elif not isinstance(ids, list):
            ids = [ids]

        success = True

        if type == 'delete':
            Tag.query.filter(Tag.id.in_(ids)).delete(False)
        else:
            success = False

        return dict(
            success = success,
            ids = ids,
        )

########NEW FILE########
__FILENAME__ = users
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code contained in this file is licensed under the GPLv3 or
# (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.

from pylons import request, tmpl_context
import webob.exc

from mediadrop.forms.admin.users import UserForm
from mediadrop.lib.auth import has_permission
from mediadrop.lib.base import BaseController
from mediadrop.lib.decorators import (autocommit, expose, expose_xhr,
    observable, paginate, validate)
from mediadrop.lib.helpers import redirect, url_for
from mediadrop.model import Group, User, fetch_row
from mediadrop.model.meta import DBSession
from mediadrop.plugin import events

user_form = UserForm()


class UsersController(BaseController):
    """Admin user actions"""
    allow_only = has_permission('admin')

    @expose_xhr('admin/users/index.html')
    @paginate('users', items_per_page=50)
    @observable(events.Admin.UsersController.index)
    def index(self, page=1, **kwargs):
        """List users with pagination.

        :param page: Page number, defaults to 1.
        :type page: int
        :rtype: Dict
        :returns:
            users
                The list of :class:`~mediadrop.model.auth.User`
                instances for this page.

        """
        users = DBSession.query(User).order_by(User.display_name,
                                               User.email_address)
        return dict(users=users)


    @expose('admin/users/edit.html')
    @observable(events.Admin.UsersController.edit)
    def edit(self, id, **kwargs):
        """Display the :class:`~mediadrop.forms.admin.users.UserForm` for editing or adding.

        :param id: User ID
        :type id: ``int`` or ``"new"``
        :rtype: dict
        :returns:
            user
                The :class:`~mediadrop.model.auth.User` instance we're editing.
            user_form
                The :class:`~mediadrop.forms.admin.users.UserForm` instance.
            user_action
                ``str`` form submit url
            user_values
                ``dict`` form values

        """
        user = fetch_row(User, id)

        if tmpl_context.action == 'save' or id == 'new':
            # Use the values from error_handler or GET for new users
            user_values = kwargs
            user_values['login_details.password'] = None
            user_values['login_details.confirm_password'] = None
        else:
            group_ids = None
            if user.groups:
                group_ids = map(lambda group: group.group_id, user.groups)
            user_values = dict(
                display_name = user.display_name,
                email_address = user.email_address,
                login_details = dict(
                    groups = group_ids,
                    user_name = user.user_name,
                ),
            )

        return dict(
            user = user,
            user_form = user_form,
            user_action = url_for(action='save'),
            user_values = user_values,
        )


    @expose(request_method='POST')
    @validate(user_form, error_handler=edit)
    @autocommit
    @observable(events.Admin.UsersController.save)
    def save(self, id, email_address, display_name, login_details,
             delete=None, **kwargs):
        """Save changes or create a new :class:`~mediadrop.model.auth.User` instance.

        :param id: User ID. If ``"new"`` a new user is created.
        :type id: ``int`` or ``"new"``
        :returns: Redirect back to :meth:`index` after successful save.

        """
        user = fetch_row(User, id)

        if delete:
            DBSession.delete(user)
            redirect(action='index', id=None)

        user.display_name = display_name
        user.email_address = email_address
        user.user_name = login_details['user_name']

        password = login_details['password']
        if password is not None and password != '':
            user.password = password

        if login_details['groups']:
            query = DBSession.query(Group).filter(Group.group_id.in_(login_details['groups']))
            user.groups = list(query.all())
        else:
            user.groups = []

        DBSession.add(user)

        # Check if we're changing the logged in user's own password
        if user.id == request.perm.user.id \
        and password is not None and password != '':
            DBSession.commit()
            # repoze.who sees the Unauthorized response and clears the cookie,
            # forcing a fresh login with the new password
            raise webob.exc.HTTPUnauthorized().exception

        redirect(action='index', id=None)


    @expose('json', request_method='POST')
    @autocommit
    @observable(events.Admin.UsersController.delete)
    def delete(self, id, **kwargs):
        """Delete a user.

        :param id: User ID.
        :type id: ``int``
        :returns: Redirect back to :meth:`index` after successful delete.
        """
        user = fetch_row(User, id)
        DBSession.delete(user)

        if request.is_xhr:
            return dict(success=True)
        redirect(action='index', id=None)

########NEW FILE########
__FILENAME__ = categories
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code contained in this file is licensed under the GPLv3 or
# (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.

import logging
from datetime import datetime, timedelta

from paste.util.converters import asbool
from pylons import app_globals, request
from sqlalchemy import orm

from mediadrop.controllers.api import APIException, get_order_by
from mediadrop.lib import helpers
from mediadrop.lib.base import BaseController
from mediadrop.lib.compat import any
from mediadrop.lib.decorators import expose
from mediadrop.lib.helpers import get_featured_category, url_for
from mediadrop.lib.thumbnails import thumb
from mediadrop.model import Category
from mediadrop.model.meta import DBSession

log = logging.getLogger(__name__)

order_columns = {
    'id': Category.id,
    'name': Category.name,
    'slug': Category.slug,
    'media_count': 'media_count %s',
}

class CategoriesController(BaseController):
    """
    JSON Category API
    """

    @expose('json')
    def index(self, order=None, offset=0, limit=10, api_key=None, **kwargs):
        """Query for a flat list of categories.

        :param id: An :attr:`id <mediadrop.model.media.Category.id>` for lookup
        :type id: int

        :param name: A :attr:`name <mediadrop.model.media.Category.name>`
            for lookup
        :type name: str

        :param slug: A :attr:`slug <mediadrop.model.media.Category.slug>`
            for lookup
        :type slug: str

        :param order:
            A column name and 'asc' or 'desc', seperated by a space.
            The column name can be any one of the returned columns.
            Defaults to newest category first (id desc).
        :type order: str

        :param offset:
            Where in the complete resultset to start returning results.
            Defaults to 0, the very beginning. This is useful if you've
            already fetched the first 50 results and want to fetch the
            next 50 and so on.
        :type offset: int

        :param limit:
            Number of results to return in each query. Defaults to 10.
            The maximum allowed value defaults to 50 and is set via
            :attr:`request.settings['api_media_max_results']`.
        :type limit: int

        :param api_key:
            The api access key if required in settings
        :type api_key: unicode or None

        :rtype: JSON-ready dict
        :returns: The returned dict has the following fields:

            count (int)
                The total number of results that match this query.
            categories (list of dicts)
                A list of **category_info** dicts, as generated by the
                :meth:`_info <mediadrop.controllers.api.categories.CategoriesController._info>`
                method. The number of dicts in this list will be the lesser
                of the number of matched items and the requested limit.

        """
        if asbool(request.settings['api_secret_key_required']) \
            and api_key != request.settings['api_secret_key']:
            return dict(error='Authentication Error')

        if any(key in kwargs for key in ('id', 'slug', 'name')):
            kwargs['offset'] = offset
            kwargs['limit'] = limit
            kwargs['tree'] = False
            return self._get_query(**kwargs)

        return self._index_query(order, offset, limit, tree=False)

    @expose('json')
    def tree(self, depth=10, api_key=None, **kwargs):
        """Query for an expanded tree of categories.

        :param id: A :attr:`mediadrop.model.media.Category.id` to lookup the parent node
        :type id: int
        :param name: A :attr:`mediadrop.model.media.Category.name` to lookup the parent node
        :type name: str
        :param slug: A :attr:`mediadrop.model.media.Category.slug` to lookup the parent node
        :type slug: str

        :param depth:
            Number of level deep in children to expand. Defaults to 10.
            The maximum allowed value defaults to 10 and is set via
            :attr:`request.settings['api_tree_max_depth']`.
        :type limit: int
        :param api_key:
            The api access key if required in settings
        :type api_key: unicode or None
        :rtype: JSON-ready dict
        :returns: The returned dict has the following fields:

            count (int)
                The total number of results that match this query.
            categories (list of dicts)
                A list of **category_info** dicts, as generated by the
                :meth:`_info <mediadrop.controllers.api.categories.CategoriesController._info>`
                method. Each of these dicts represents a category at the top
                level of the hierarchy. Each dict has also been modified to
                have an extra 'children' field, which is a list of
                **category_info** dicts representing that category's children
                within the hierarchy.

        """
        if asbool(request.settings['api_secret_key_required']) \
            and api_key != request.settings['api_secret_key']:
            return dict(error='Authentication Error')
        if any(key in kwargs for key in ('id', 'slug', 'name')):
            kwargs['depth'] = depth
            kwargs['tree'] = True
            return self._get_query(**kwargs)

        return self._index_query(depth=depth, tree=True)

    def _index_query(self, order=None, offset=0, limit=10, tree=False, depth=10, **kwargs):
        """Query a list of categories"""
        if asbool(tree):
            query = Category.query.roots()
        else:
            query = Category.query

        if not order:
            order = 'id asc'

        query = query.order_by(get_order_by(order, order_columns))

        start = int(offset)
        limit = min(int(limit), int(request.settings['api_media_max_results']))
        depth = min(int(depth), int(request.settings['api_tree_max_depth']))

        # get the total of all the matches
        count = query.count()

        query = query.offset(start).limit(limit)
        categories = self._expand(query.all(), asbool(tree), depth)

        return dict(
           categories = categories,
           count = count,
        )

    def _get_query(self, id=None, name=None, slug=None, tree=False, depth=10, **kwargs):
        """Query for a specific category item by ID, name or slug and optionally expand the children of this category."""
        query = Category.query
        depth = min(int(depth), int(request.settings['api_tree_max_depth']))

        if id:
            query = query.filter_by(id=id)
        elif name:
            query = query.filter_by(name=name)
        else:
            query = query.filter_by(slug=slug)

        try:
            category = query.one()
        except (orm.exc.NoResultFound, orm.exc.MultipleResultsFound):
            return dict(error='No Match found')

        return dict(
            category = self._expand(category, tree, depth=depth),
        )

    def _expand(self, obj, children=False, depth=0):
        """Expand a category object into json."""
        if isinstance(obj, list):
            data = [self._expand(x, children, depth) for x in obj]
        elif isinstance(obj, Category):
            data = self._info(obj)
            if children and depth > 0:
                data['children'] = self._expand(obj.children, children, depth - 1)
        return data

    def _info(self, cat):
        """Return a JSON-ready dict representing the given category instance.

        :rtype: JSON-Ready dict
        :returns: The returned dict has the following fields:

            id (int)
                The numeric unique identifier,
                :attr:`Category.id <mediadrop.model.categories.Category.id>`
            slug (unicode)
                The more human readable unique identifier,
                :attr:`Category.slug <mediadrop.model.categories.Category.slug>`
            name (unicode)
                The human readable
                :attr:`name <mediadrop.model.categories.Category.name>`
                of the category.
            parent (unicode or None)
                the :attr:`slug <mediadrop.model.categories.Category.slug>`
                of the category's parent in the hierarchy, or None.
            media_count (int)
                The number of media items that are published in this category,
                or in its sub-categories.

        """
        return dict(
            id = cat.id,
            name = cat.name,
            slug = cat.slug,
            parent = cat.parent_id,
            media_count = cat.media_count_published,
        )

########NEW FILE########
__FILENAME__ = media
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code contained in this file is licensed under the GPLv3 or
# (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.

import logging
from datetime import datetime, timedelta

from paste.util.converters import asbool
from pylons import app_globals, config, request, response, session, tmpl_context
from sqlalchemy import orm, sql

from mediadrop.controllers.api import APIException, get_order_by
from mediadrop.lib import helpers
from mediadrop.lib.base import BaseController
from mediadrop.lib.decorators import expose, expose_xhr, observable, paginate, validate
from mediadrop.lib.helpers import get_featured_category, url_for, url_for_media
from mediadrop.lib.thumbnails import thumb
from mediadrop.model import Category, Media, Podcast, Tag, fetch_row, get_available_slug
from mediadrop.model.meta import DBSession
from mediadrop.plugin import events

log = logging.getLogger(__name__)

order_columns = {
    'id': Media.id,
    'slug': Media.slug,
    'type': Media.type,
    'publish_on': Media.publish_on,
    'duration': Media.duration,
    'views': Media.views,
    'likes': Media.likes,
    'popularity': Media.popularity_points,
    'description': Media.description,
    'description_plain': Media.description_plain,
    'comment_count': 'comment_count_published %s'
}

AUTHERROR = "Authentication Error"
INVALIDFORMATERROR = "Invalid format (%s). Only json and mrss are supported"

class MediaController(BaseController):
    """
    JSON Media API
    """

    @expose('json')
    @observable(events.API.MediaController.index)
    def index(self, type=None, podcast=None, tag=None, category=None, search=None,
              max_age=None, min_age=None, order=None, offset=0, limit=10,
              published_after=None, published_before=None, featured=False,
              id=None, slug=None, include_embed=False, api_key=None, format="json", **kwargs):
        """Query for a list of media.

        :param type:
            Filter by '%s' or '%s'. Defaults to any type.

        :param podcast:
            A podcast slug (or slugs) to filter by. Use 0 to include
            only non-podcast media or 1 to include any podcast media.
            For multiple podcasts, separate the slugs with commas.

        :param tag:
            A tag slug to filter by.

        :param category:
            A category slug to filter by.

        :param search:
            A boolean search query. See
            http://dev.mysql.com/doc/refman/5.0/en/fulltext-boolean.html

        :param published_after:
            If given, only media published *on or after* this date is
            returned. The expected format is 'YYYY-MM-DD HH:MM:SS'
            (ISO 8601) and must include the year at a bare minimum.

        :param published_before:
            If given, only media published *on or before* this date is
            returned. The expected format is 'YYYY-MM-DD HH:MM:SS'
            (ISO 8601) and must include the year at a bare minimum.

        :param max_age:
            If given, only media published within this many days is
            returned. This is a convenience shortcut for publish_after
            and will override its value if both are given.
        :type max_age: int

        :param min_age:
            If given, only media published prior to this number of days
            ago will be returned. This is a convenience shortcut for
            publish_before and will override its value if both are given.
        :type min_age: int

        :param order:
            A column name and 'asc' or 'desc', seperated by a space.
            The column name can be any one of the returned columns.
            Defaults to newest media first (publish_on desc).

        :param offset:
            Where in the complete resultset to start returning results.
            Defaults to 0, the very beginning. This is useful if you've
            already fetched the first 50 results and want to fetch the
            next 50 and so on.
        :type offset: int

        :param limit:
            Number of results to return in each query. Defaults to 10.
            The maximum allowed value defaults to 50 and is set via
            :attr:`request.settings['api_media_max_results']`.
        :type limit: int

        :param featured:
            If nonzero, the results will only include media from the
            configured featured category, if there is one.
        :type featured: bool

        :param include_embed:
            If nonzero, the HTML for the embeddable player is included
            for all results.
        :type include_embed: bool

        :param id:
            Filters the results to include the one item with the given ID.
            Note that we still return a list.
        :type id: int or None

        :param slug:
            Filters the results to include the one item with the given slug.
            Note that we still return a list.
        :type slug: unicode or None

        :param api_key:
            The api access key if required in settings
        :type api_key: unicode or None

        :raises APIException:
            If there is an user error in the query params.

        :rtype: JSON-ready dict
        :returns: The returned dict has the following fields:

            count (int)
                The total number of results that match this query.
            media (list of dicts)
                A list of **media_info** dicts, as generated by the
                :meth:`_info <mediadrop.controllers.api.media.MediaController._info>`
                method. The number of dicts in this list will be the lesser
                of the number of matched items and the requested limit.
                **Note**: unless the 'include_embed' option is specified,
                The returned **media_info** dicts will not include the
                'embed' entry.

        """

        if asbool(request.settings['api_secret_key_required']) \
            and api_key != request.settings['api_secret_key']:
            return dict(error=AUTHERROR)

        if format not in ("json", "mrss"):
            return dict(error= INVALIDFORMATERROR % format)

        query = Media.query\
            .published()\
            .options(orm.undefer('comment_count_published'))

        # Basic filters
        if id:
            query = query.filter_by(id=id)
        if slug:
            query = query.filter_by(slug=slug)

        if type:
            query = query.filter_by(type=type)

        if podcast:
            podcast_query = DBSession.query(Podcast.id)\
                .filter(Podcast.slug.in_(podcast.split(',')))
            query = query.filter(Media.podcast_id.in_(podcast_query))

        if tag:
            tag = fetch_row(Tag, slug=tag)
            query = query.filter(Media.tags.contains(tag))

        if category:
            category = fetch_row(Category, slug=category)
            query = query.filter(Media.categories.contains(category))

        if max_age:
            published_after = datetime.now() - timedelta(days=int(max_age))
        if min_age:
            published_before = datetime.now() - timedelta(days=int(min_age))

        # FIXME: Parse the date and catch formatting problems before it
        #        it hits the database. Right now support for partial
        #        dates like '2010-02' is thanks to leniancy in MySQL.
        #        Hopefully this leniancy is common to Postgres etc.
        if published_after:
            query = query.filter(Media.publish_on >= published_after)
        if published_before:
            query = query.filter(Media.publish_on <= published_before)

        query = query.order_by(get_order_by(order, order_columns))

        # Search will supercede the ordering above
        if search:
            query = query.search(search)

        if featured:
            featured_cat = get_featured_category()
            if featured_cat:
                query = query.in_category(featured_cat)

        # Preload podcast slugs so we don't do n+1 queries
        podcast_slugs = dict(DBSession.query(Podcast.id, Podcast.slug))

        # Rudimentary pagination support
        start = int(offset)
        end = start + min(int(limit), int(request.settings['api_media_max_results']))

        if format == "mrss":
            request.override_template = "sitemaps/mrss.xml"
            return dict(
                media = query[start:end],
                title = "Media Feed",
            )

        media = [self._info(m, podcast_slugs, include_embed) for m in query[start:end]]

        return dict(
            media = media,
            count = query.count(),
        )


    @expose('json')
    @observable(events.API.MediaController.get)
    def get(self, id=None, slug=None, api_key=None, format="json", **kwargs):
        """Expose info on a specific media item by ID or slug.

        :param id: An :attr:`id <mediadrop.model.media.Media.id>` for lookup
        :type id: int
        :param slug: A :attr:`slug <mediadrop.model.media.Media.slug>`
            for lookup
        :type slug: str
        :param api_key: The api access key if required in settings
        :type api_key: unicode or None
        :raises webob.exc.HTTPNotFound: If the media doesn't exist.
        :rtype: JSON-ready dict
        :returns:
            The returned dict is a **media_info** dict, generated by the
            :meth:`_info <mediadrop.controllers.api.media.MediaController._info>`
            method.

        """
        if asbool(request.settings['api_secret_key_required']) \
            and api_key != request.settings['api_secret_key']:
            return dict(error=AUTHERROR)

        if format not in ("json", "mrss"):
            return dict(error= INVALIDFORMATERROR % format)

        query = Media.query.published()

        if id:
            query = query.filter_by(id=id)
        else:
            query = query.filter_by(slug=slug)

        try:
            media = query.one()
        except orm.exc.NoResultFound:
            return dict(error="No match found")

        if format == "mrss":
            request.override_template = "sitemaps/mrss.xml"
            return dict(
                media = [media],
                title = "Media Entry",
            )

        return self._info(media, include_embed=True)


    def _info(self, media, podcast_slugs=None, include_embed=False):
        """
        Return a **media_info** dict--a JSON-ready dict for describing a media instance.

        :rtype: JSON-ready dict
        :returns: The returned dict has the following fields:

            author (unicode)
                The name of the
                :attr:`author <mediadrop.model.media.Media.author>` of the
                media instance.
            categories (dict of unicode)
                A JSON-ready dict representing the categories the media
                instance is in. Keys are the unique
                :attr:`slugs <mediadrop.model.podcasts.Podcast.slug>`
                for each category, values are the human-readable
                :attr:`title <mediadrop.model.podcasts.podcast.Title>`
                of that category.
            id (int)
                The numeric unique :attr:`id <mediadrop.model.media.Media.id>` of
                the media instance.
            slug (unicode)
                The more human readable unique identifier
                (:attr:`slug <mediadrop.model.media.Media.slug>`)
                of the media instance.
            url (unicode)
                A permalink (HTTP) to the MediaDrop view page for the media instance.
            embed (unicode)
                HTML code that can be used to embed the video in another site.
            title (unicode)
                The :attr:`title <mediadrop.model.media.Media.title>` of
                the media instance.
            type (string, one of ['%s', '%s'])
                The :attr:`type <mediadrop.model.media.Media.type>` of
                the media instance
            podcast (unicode or None)
                The :attr:`slug <mediadrop.model.podcasts.Podcast.slug>` of the
                :class:`podcast <mediadrop.model.podcasts.Podcast>` that
                the media instance has been published under, or None
            description (unicode)
                An XHTML
                :attr:`description <mediadrop.model.media.Media.description>`
                of the media instance.
            description_plain (unicode)
                A plain text
                :attr:`description <mediadrop.model.media.Media.description_plain>`
                of the media instance.
            comment_count (int)
                The number of published comments on the media instance.
            publish_on (unicode)
                The date of publishing in "YYYY-MM-DD HH:MM:SS" (ISO 8601) format.
                e.g.  "2010-02-16 15:06:49"
            likes (int)
                The number of :attr:`like votes <mediadrop.model.media.Media.likes>`
                that the media instance has received.
            views (int)
                The number of :attr:`views <mediadrop.model.media.Media.views>`
                that the media instance has received.
            thumbs (dict)
                A dict of dicts containing URLs, width and height of
                different sizes of thumbnails. The default sizes
                are 's', 'm' and 'l'. Using medium for example::

                    medium_url = thumbs['m']['url']
                    medium_width = thumbs['m']['x']
                    medium_height = thumbs['m']['y']
        """
        if media.podcast_id:
            media_url = url_for(controller='/media', action='view', slug=media.slug,
                                podcast_slug=media.podcast.slug, qualified=True)
        else:
            media_url = url_for_media(media, qualified=True)

        if media.podcast_id is None:
            podcast_slug = None
        elif podcast_slugs:
            podcast_slug = podcast_slugs[media.podcast_id]
        else:
            podcast_slug = DBSession.query(Podcast.slug)\
                .filter_by(id=media.podcast_id).scalar()

        thumbs = {}
        for size in config['thumb_sizes'][media._thumb_dir].iterkeys():
            thumbs[size] = thumb(media, size, qualified=True)

        info = dict(
            id = media.id,
            slug = media.slug,
            url = media_url,
            title = media.title,
            author = media.author.name,
            type = media.type,
            podcast = podcast_slug,
            description = media.description,
            description_plain = media.description_plain,
            comment_count = media.comment_count_published,
            publish_on = unicode(media.publish_on),
            likes = media.likes,
            views = media.views,
            thumbs = thumbs,
            categories = dict((c.slug, c.name) for c in list(media.categories)),
        )

        if include_embed:
            info['embed'] = unicode(helpers.embed_player(media))

        return info


    @expose('json')
    def files(self, id=None, slug=None, api_key=None, **kwargs):
        """List all files related to specific media.

        :param id: A :attr:`mediadrop.model.media.Media.id` for lookup
        :type id: int
        :param slug: A :attr:`mediadrop.model.media.Media.slug` for lookup
        :type slug: str
        :param api_key: The api access key if required in settings
        :type api_key: unicode or None
        :raises webob.exc.HTTPNotFound: If the media doesn't exist.

        :rtype: JSON-ready dict
        :returns: The returned dict has the following fields:

            files
                A list of **file_info** dicts, as generated by the
                :meth:`_file_info <mediadrop.controllers.api.media.MediaController._file_info>`
                method.

        """
        if asbool(request.settings['api_secret_key_required']) \
            and api_key != request.settings['api_secret_key']:
            return dict(error='Authentication Error')

        query = Media.query.published()

        if id:
            query = query.filter_by(id=id)
        else:
            query = query.filter_by(slug=slug)

        try:
            media = query.one()
        except orm.exc.NoResultFound:
            return dict(error='No match found')

        return dict(
            files = [self._file_info(f, media) for f in media.files],
        )

    def _file_info(self, file, media):
        """
        Return a **file_info** dict--a JSON-ready dict for describing a media file.

        :rtype: JSON-ready dict
        :returns: The returned dict has the following fields:

            container (unicode)
                The file extension of the file's container format.
            type (unicode)
                The :attr:`file type <mediadrop.model.media.MediaFile.type>`.
                One of (%s) or a custom type defined in a plugin.
            display_name (unicode)
                The :attr:`display_name <mediadrop.model.media.MediaFile.display_name>`
                of the file. Usually the original name of the uploaded file.
            created (unicode)
                The date/time that the file was added to MediaDrop, in
                "YYYY-MM-DDTHH:MM:SS" (ISO 8601) format.
                e.g. "2011-01-04T16:23:37"
            url (unicode)
                A permalink (HTTP) to the MediaDrop view page for the
                media instance associated with this file.
            uris (list of dicts)
                Each dict in this list represents a URI via which the file may
                be accessible. These dicts have the following fields:

                    scheme (unicode)
                        The
                        :attr:`scheme <mediadrop.lib.uri.StorageUri.scheme>`
                        (e.g. 'http' in the URI 'http://mediadrop.net/docs/',
                        'rtmp' in the URI 'rtmp://mediadrop.net/docs/', or
                        'file' in the URI 'file:///some/local/file.mp4')
                    server (unicode)
                        The
                        :attr:`server name <mediadrop.lib.uri.StorageUri.server_uri>`
                        (e.g. 'mediadrop.net' in the URI
                        'http://mediadrop.net/docs')
                    file (unicode)
                        The
                        :attr:`file path <mediadrop.lib.uri.StorageUri.file_uri>`
                        part of the URI.  (e.g. 'docs' in the URI
                        'http://mediadrop.net/docs')
                    uri (unicode)
                        The full URI string (minus scheme) built from the
                        server_uri and file_uri.
                        See :attr:`mediadrop.lib.uri.StorageUri.__str__`.
                        (e.g. 'mediadrop.net/docs' in the URI
                        'http://mediadrop.net/docs')

        """
        uris = []
        info = dict(
            container = file.container,
            type = file.type,
            display_name = file.display_name,
            created = file.created_on.isoformat(),
            url = url_for_media(media, qualified=True),
            uris = uris,
        )
        for uri in file.get_uris():
            uris.append({
                'scheme': uri.scheme,
                'uri': str(uri),
                'server': uri.server_uri,
                'file': uri.file_uri,
            })
        return info

#XXX: Dirty hack to set the actual strings for filetypes, in our docstrings,
#     based on the canonical definitions in the filetypes module.
from mediadrop.lib.filetypes import registered_media_types, AUDIO, VIDEO
_types_list = "'%s'" % ("', '".join(id for id, name in registered_media_types()))
MediaController._file_info.im_func.__doc__ = \
        MediaController._file_info.im_func.__doc__ % _types_list
MediaController._info.im_func.__doc__ = \
        MediaController._info.im_func.__doc__ % (AUDIO, VIDEO)
MediaController.index.im_func.__doc__ = \
        MediaController.index.im_func.__doc__ % (AUDIO, VIDEO)

########NEW FILE########
__FILENAME__ = categories
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code contained in this file is licensed under the GPLv3 or
# (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.

from pylons import request, response, tmpl_context as c
from pylons.controllers.util import abort
from sqlalchemy import orm

from mediadrop.lib.base import BaseController
from mediadrop.lib.decorators import (beaker_cache, expose, observable, 
    paginate, validate)
from mediadrop.lib.helpers import content_type_for_response, url_for, viewable_media
from mediadrop.lib.i18n import _
from mediadrop.model import Category, Media, fetch_row
from mediadrop.plugin import events
from mediadrop.validation import LimitFeedItemsValidator

import logging
log = logging.getLogger(__name__)

class CategoriesController(BaseController):
    """
    Categories Controller

    Handles the display of the category hierarchy, displaying the media
    associated with any given category and its descendants.

    """

    def __before__(self, *args, **kwargs):
        """Load all our category data before each request."""
        BaseController.__before__(self, *args, **kwargs)

        c.categories = Category.query\
            .order_by(Category.name)\
            .options(orm.undefer('media_count_published'))\
            .populated_tree()

        counts = dict((cat.id, cat.media_count_published)
                      for cat, depth in c.categories.traverse())
        c.category_counts = counts.copy()
        for cat, depth in c.categories.traverse():
            count = counts[cat.id]
            if count:
                for ancestor in cat.ancestors():
                    c.category_counts[ancestor.id] += count

        category_slug = request.environ['pylons.routes_dict'].get('slug', None)
        if category_slug:
            c.category = fetch_row(Category, slug=category_slug)
            c.breadcrumb = c.category.ancestors()
            c.breadcrumb.append(c.category)

    @expose('categories/index.html')
    @observable(events.CategoriesController.index)
    def index(self, slug=None, **kwargs):
        media = Media.query.published()

        if c.category:
            media = media.in_category(c.category)
            
            response.feed_links.append((
                url_for(controller='/categories', action='feed', slug=c.category.slug),
                _('Latest media in %s') % c.category.name
            ))

        latest = media.order_by(Media.publish_on.desc())
        popular = media.order_by(Media.popularity_points.desc())

        latest = viewable_media(latest)[:5]
        popular = viewable_media(popular.exclude(latest))[:5]

        return dict(
            latest = latest,
            popular = popular,
        )

    @expose('categories/more.html')
    @paginate('media', items_per_page=20)
    @observable(events.CategoriesController.more)
    def more(self, slug, order, page=1, **kwargs):
        media = Media.query.published()\
            .in_category(c.category)

        if order == 'latest':
            media = media.order_by(Media.publish_on.desc())
        else:
            media = media.order_by(Media.popularity_points.desc())

        return dict(
            media = viewable_media(media),
            order = order,
        )

    @validate(validators={'limit': LimitFeedItemsValidator()})
    @beaker_cache(expire=60 * 3, query_args=True)
    @expose('sitemaps/mrss.xml')
    @observable(events.CategoriesController.feed)
    def feed(self, limit=None, **kwargs):
        """ Generate a media rss feed of the latest media

        :param limit: the max number of results to return. Defaults to 30

        """
        if request.settings['rss_display'] != 'True':
            abort(404)

        response.content_type = content_type_for_response(
            ['application/rss+xml', 'application/xml', 'text/xml'])

        media = Media.query.published()

        if c.category:
            media = media.in_category(c.category)

        media_query = media.order_by(Media.publish_on.desc())
        media = viewable_media(media_query)
        if limit is not None:
            media = media.limit(limit)

        return dict(
            media = media,
            title = u'%s Media' % c.category.name,
        )

########NEW FILE########
__FILENAME__ = errors
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code contained in this file is licensed under the GPLv3 or
# (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.

from mediadrop.lib import email as libemail
from mediadrop.lib.base import BaseController
from mediadrop.lib.decorators import expose, observable
from mediadrop.lib.helpers import redirect, clean_xhtml
from mediadrop.lib.i18n import _
from mediadrop.plugin import events

class ErrorsController(BaseController):
    """Generates error documents as and when they are required.

    The ErrorDocuments middleware forwards to ErrorController when error
    related status codes are returned from the application.

    This behaviour can be altered by changing the parameters to the
    ErrorDocuments middleware in your config/middleware.py file.
    """
    @expose('error.html')
    @observable(events.ErrorController.document)
    def document(self, *args, **kwargs):
        """Render the error document for the general public.

        Essentially, when an error occurs, a second request is initiated for
        the URL ``/error/document``. The URL is set on initialization of the
        :class:`pylons.middleware.StatusCodeRedirect` object, and can be
        overridden in :func:`tg.configuration.add_error_middleware`. Also,
        before this method is called, some potentially useful environ vars
        are set in :meth:`pylons.middleware.StatusCodeRedirect.__call__`
        (access them via :attr:`tg.request.environ`).

        :rtype: Dict
        :returns:
            prefix
                The environ SCRIPT_NAME.
            vars
                A dict containing the first 2 KB of the original request.
            code
                Integer error code thrown by the original request, but it can
                also be overriden by setting ``tg.request.params['code']``.
            message
                A message to display to the user. Pulled from
                ``tg.request.params['message']``.

        """
        request = self._py_object.request
        environ = request.environ
        original_request = environ.get('pylons.original_request', None)
        original_response = environ.get('pylons.original_response', None)
        default_message = '<p>%s</p>' % _("We're sorry but we weren't able "
                                          "to process this request.")

        message = request.params.get('message', default_message)
        message = clean_xhtml(message)

        return dict(
            prefix = environ.get('SCRIPT_NAME', ''),
            code = int(request.params.get('code', getattr(original_response,
                                                          'status_int', 500))),
            message = message,
            vars = dict(POST_request=unicode(original_request)[:2048]),
        )

    @expose(request_method='POST')
    @observable(events.ErrorController.report)
    def report(self, email='', description='', **kwargs):
        """Email a support request that's been submitted on :meth:`document`.

        Redirects back to the root URL ``/``.

        """
        url = ''
        get_vars = post_vars = {}
        for x in kwargs:
            if x.startswith('GET_'):
                get_vars[x] = kwargs[x]
            elif x.startswith('POST_'):
                post_vars[x] = kwargs[x]
        libemail.send_support_request(email, url, description, get_vars, post_vars)
        redirect('/')

########NEW FILE########
__FILENAME__ = login
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code contained in this file is licensed under the GPLv3 or
# (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.

from formencode import Invalid
from pylons import request, tmpl_context

from mediadrop.forms.login import LoginForm
from mediadrop.lib.base import BaseController
from mediadrop.lib.helpers import redirect, url_for
from mediadrop.lib.i18n import _
from mediadrop.lib.decorators import expose, observable
from mediadrop.plugin import events

import logging
log = logging.getLogger(__name__)

login_form = LoginForm()

class LoginController(BaseController):
    @expose('login.html')
    @observable(events.LoginController.login)
    def login(self, came_from=None, **kwargs):
        if request.environ.get('repoze.who.identity'):
            redirect(came_from or '/')
        
        # the friendlyform plugin requires that these values are set in the
        # query string
        form_url = url_for('/login/submit', 
            came_from=(came_from or '').encode('utf-8'), 
            __logins=str(self._is_failed_login()))
        
        login_errors = None
        if self._is_failed_login():
            login_errors = Invalid('dummy', None, {}, error_dict={
                '_form': Invalid(_('Invalid username or password.'), None, {}),
                'login': Invalid('dummy', None, {}),
                'password': Invalid('dummy', None, {}),
            })
        return dict(
            login_form = login_form,
            form_action = form_url,
            form_values = kwargs,
            login_errors = login_errors,
        )

    @expose()
    def login_handler(self):
        """This is a dummy method.

        Without a dummy method, Routes will throw a NotImplemented exception.
        Calls that would route to this method are intercepted by
        repoze.who, as defined in mediadrop.lib.auth
        """
        pass

    @expose()
    def logout_handler(self):
        """This is a dummy method.

        Without a dummy method, Routes will throw a NotImplemented exception.
        Calls that would route to this method are intercepted by
        repoze.who, as defined in mediadrop.lib.auth
        """
        pass

    @expose()
    @observable(events.LoginController.post_login)
    def post_login(self, came_from=None, **kwargs):
        if not request.identity:
            # The FriendlyForm plugin will always issue a redirect to 
            # /login/continue (post login url) even for failed logins.
            # If 'came_from' is a protected page (i.e. /admin) we could just 
            # redirect there and the login form will be displayed again with
            # our login error message.
            # However if the user tried to login from the front page, this 
            # mechanism doesn't work so go to the login method directly here.
            self._increase_number_of_failed_logins()
            return self.login(came_from=came_from)
        if came_from:
            redirect(came_from)
        # It is important to return absolute URLs (if app mounted in subdirectory)
        if request.perm.contains_permission(u'edit') or request.perm.contains_permission(u'admin'):
            redirect(url_for('/admin', qualified=True))
        redirect(url_for('/', qualified=True))

    @expose()
    @observable(events.LoginController.post_logout)
    def post_logout(self, came_from=None, **kwargs):
        redirect('/')

    def _is_failed_login(self):
        # repoze.who.logins will always be an integer even if the HTTP login 
        # counter variable contained a non-digit string
        return (request.environ.get('repoze.who.logins', 0) > 0)
    
    def _increase_number_of_failed_logins(self):
        request.environ['repoze.who.logins'] += 1
    
    def __call__(self, environ, start_response):
        """Invoke the Controller"""
        # BaseController.__call__ dispatches to the Controller method
        # the request is routed to. This routing information is
        # available in environ['pylons.routes_dict']
        request.identity = request.environ.get('repoze.who.identity')
        tmpl_context.identity = request.identity
        return BaseController.__call__(self, environ, start_response)

########NEW FILE########
__FILENAME__ = media
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code contained in this file is licensed under the GPLv3 or
# (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.

"""
Publicly Facing Media Controllers
"""
import logging
import os.path

from akismet import Akismet
from paste.fileapp import FileApp
from paste.util import mimeparse
from pylons import config, request, response
from pylons.controllers.util import abort, forward
from sqlalchemy import orm, sql
from sqlalchemy.exc import OperationalError
from webob.exc import HTTPNotAcceptable, HTTPNotFound

from mediadrop import USER_AGENT
from mediadrop.forms.comments import PostCommentSchema
from mediadrop.lib import helpers
from mediadrop.lib.base import BaseController
from mediadrop.lib.decorators import expose, expose_xhr, observable, paginate, validate_xhr, autocommit
from mediadrop.lib.email import send_comment_notification
from mediadrop.lib.helpers import (filter_vulgarity, redirect, url_for, 
    viewable_media)
from mediadrop.lib.i18n import _
from mediadrop.lib.services import Facebook
from mediadrop.lib.templating import render
from mediadrop.model import (DBSession, fetch_row, Media, MediaFile, Comment, 
    Tag, Category, AuthorWithIP, Podcast)
from mediadrop.plugin import events

log = logging.getLogger(__name__)

comment_schema = PostCommentSchema()

class MediaController(BaseController):
    """
    Media actions -- for both regular and podcast media
    """

    @expose('media/index.html')
    @paginate('media', items_per_page=10)
    @observable(events.MediaController.index)
    def index(self, page=1, show='latest', q=None, tag=None, **kwargs):
        """List media with pagination.

        The media paginator may be accessed in the template with
        :attr:`c.paginators.media`, see :class:`webhelpers.paginate.Page`.

        :param page: Page number, defaults to 1.
        :type page: int
        :param show: 'latest', 'popular' or 'featured'
        :type show: unicode or None
        :param q: A search query to filter by
        :type q: unicode or None
        :param tag: A tag slug to filter for
        :type tag: unicode or None
        :rtype: dict
        :returns:
            media
                The list of :class:`~mediadrop.model.media.Media` instances
                for this page.
            result_count
                The total number of media items for this query
            search_query
                The query the user searched for, if any

        """
        media = Media.query.published()

        media, show = helpers.filter_library_controls(media, show)

        if q:
            media = media.search(q, bool=True)

        if tag:
            tag = fetch_row(Tag, slug=tag)
            media = media.filter(Media.tags.contains(tag))

        if (request.settings['rss_display'] == 'True') and (not (q or tag)):
            if show == 'latest':
                response.feed_links.extend([
                    (url_for(controller='/sitemaps', action='latest'), _(u'Latest RSS')),
                ])
            elif show == 'featured':
                response.feed_links.extend([
                    (url_for(controller='/sitemaps', action='featured'), _(u'Featured RSS')),
                ])

        media = viewable_media(media)
        return dict(
            media = media,
            result_count = media.count(),
            search_query = q,
            show = show,
            tag = tag,
        )

    @expose('media/tags.html')
    def tags(self, **kwargs):
        """Display a listing of all tags."""
        tags = Tag.query\
            .options(orm.undefer('media_count_published'))\
            .filter(Tag.media_count_published > 0)
        return dict(
            tags = tags,
        )

    @expose('media/explore.html')
    @observable(events.MediaController.explore)
    def explore(self, **kwargs):
        """Display the most recent 15 media.

        :rtype: Dict
        :returns:
            latest
                Latest media
            popular
                Latest media

        """
        media = Media.query.published()

        latest = media.order_by(Media.publish_on.desc())
        popular = media.order_by(Media.popularity_points.desc())

        featured = None
        featured_cat = helpers.get_featured_category()
        if featured_cat:
            featured = viewable_media(latest.in_category(featured_cat)).first()
        if not featured:
            featured = viewable_media(popular).first()

        latest = viewable_media(latest.exclude(featured))[:8]
        popular = viewable_media(popular.exclude(featured, latest))[:5]
        if request.settings['sitemaps_display'] == 'True':
            response.feed_links.extend([
                (url_for(controller='/sitemaps', action='google'), _(u'Sitemap XML')),
                (url_for(controller='/sitemaps', action='mrss'), _(u'Sitemap RSS')),
            ])
        if request.settings['rss_display'] == 'True':
            response.feed_links.extend([
                (url_for(controller='/sitemaps', action='latest'), _(u'Latest RSS')),
            ])

        return dict(
            featured = featured,
            latest = latest,
            popular = popular,
            categories = Category.query.populated_tree(),
        )

    @expose()
    def random(self, **kwargs):
        """Redirect to a randomly selected media item."""
        # TODO: Implement something more efficient than ORDER BY RAND().
        #       This method does a full table scan every time.
        random_query = Media.query.published().order_by(sql.func.random())
        media = viewable_media(random_query).first()

        if media is None:
            redirect(action='explore')
        if media.podcast_id:
            podcast_slug = DBSession.query(Podcast.slug).get(media.podcast_id)
        else:
            podcast_slug = None
        redirect(action='view', slug=media.slug, podcast_slug=podcast_slug)

    @expose('media/view.html')
    @observable(events.MediaController.view)
    def view(self, slug, podcast_slug=None, **kwargs):
        """Display the media player, info and comments.

        :param slug: The :attr:`~mediadrop.models.media.Media.slug` to lookup
        :param podcast_slug: The :attr:`~mediadrop.models.podcasts.Podcast.slug`
            for podcast this media belongs to. Although not necessary for
            looking up the media, it tells us that the podcast slug was
            specified in the URL and therefore we reached this action by the
            preferred route.
        :rtype dict:
        :returns:
            media
                The :class:`~mediadrop.model.media.Media` instance for display.
            related_media
                A list of :class:`~mediadrop.model.media.Media` instances that
                rank as topically related to the given media item.
            comments
                A list of :class:`~mediadrop.model.comments.Comment` instances
                associated with the selected media item.
            comment_form_action
                ``str`` comment form action
            comment_form_values
                ``dict`` form values
            next_episode
                The next episode in the podcast series, if this media belongs to
                a podcast, another :class:`~mediadrop.model.media.Media`
                instance.

        """
        media = fetch_row(Media, slug=slug)
        request.perm.assert_permission(u'view', media.resource)

        if media.podcast_id is not None:
            # Always view podcast media from a URL that shows the context of the podcast
            if url_for() != url_for(podcast_slug=media.podcast.slug):
                redirect(podcast_slug=media.podcast.slug)

        try:
            media.increment_views()
            DBSession.commit()
        except OperationalError:
            DBSession.rollback()

        if request.settings['comments_engine'] == 'facebook':
            response.facebook = Facebook(request.settings['facebook_appid'])

        related_media = viewable_media(Media.query.related(media))[:6]
        # TODO: finish implementation of different 'likes' buttons
        #       e.g. the default one, plus a setting to use facebook.
        return dict(
            media = media,
            related_media = related_media,
            comments = media.comments.published().all(),
            comment_form_action = url_for(action='comment'),
            comment_form_values = kwargs,
        )

    @expose('players/iframe.html')
    @observable(events.MediaController.embed_player)
    def embed_player(self, slug, w=None, h=None, **kwargs):
        media = fetch_row(Media, slug=slug)
        request.perm.assert_permission(u'view', media.resource)
        return dict(
            media = media,
            width = w and int(w) or None,
            height = h and int(h) or None,
        )

    @expose(request_method="POST")
    @autocommit
    @observable(events.MediaController.rate)
    def rate(self, slug, up=None, down=None, **kwargs):
        """Say 'I like this' for the given media.

        :param slug: The media :attr:`~mediadrop.model.media.Media.slug`
        :rtype: unicode
        :returns:
            The new number of likes

        """
        media = fetch_row(Media, slug=slug)
        request.perm.assert_permission(u'view', media.resource)

        if up:
            if not request.settings['appearance_show_like']:
                abort(status_code=403)
            media.increment_likes()
        elif down:
            if not request.settings['appearance_show_dislike']:
                abort(status_code=403)
            media.increment_dislikes()

        if request.is_xhr:
            return u''
        else:
            redirect(action='view')

    @expose_xhr(request_method='POST')
    @validate_xhr(comment_schema, error_handler=view)
    @autocommit
    @observable(events.MediaController.comment)
    def comment(self, slug, name='', email=None, body='', **kwargs):
        """Post a comment from :class:`~mediadrop.forms.comments.PostCommentForm`.

        :param slug: The media :attr:`~mediadrop.model.media.Media.slug`
        :returns: Redirect to :meth:`view` page for media.

        """
        def result(success, message=None, comment=None):
            if request.is_xhr:
                result = dict(success=success, message=message)
                if comment:
                    result['comment'] = render('comments/_list.html',
                        {'comment_to_render': comment},
                        method='xhtml')
                return result
            elif success:
                return redirect(action='view')
            else:
                return self.view(slug, name=name, email=email, body=body,
                                 **kwargs)

        if request.settings['comments_engine'] != 'builtin':
            abort(404)
        akismet_key = request.settings['akismet_key']
        if akismet_key:
            akismet = Akismet(agent=USER_AGENT)
            akismet.key = akismet_key
            akismet.blog_url = request.settings['akismet_url'] or \
                url_for('/', qualified=True)
            akismet.verify_key()
            data = {'comment_author': name.encode('utf-8'),
                    'user_ip': request.environ.get('REMOTE_ADDR'),
                    'user_agent': request.environ.get('HTTP_USER_AGENT', ''),
                    'referrer': request.environ.get('HTTP_REFERER',  'unknown'),
                    'HTTP_ACCEPT': request.environ.get('HTTP_ACCEPT')}

            if akismet.comment_check(body.encode('utf-8'), data):
                return result(False, _(u'Your comment has been rejected.'))

        media = fetch_row(Media, slug=slug)
        request.perm.assert_permission(u'view', media.resource)

        c = Comment()

        name = filter_vulgarity(name)
        c.author = AuthorWithIP(name, email, request.environ['REMOTE_ADDR'])
        c.subject = 'Re: %s' % media.title
        c.body = filter_vulgarity(body)

        require_review = request.settings['req_comment_approval']
        if not require_review:
            c.reviewed = True
            c.publishable = True

        media.comments.append(c)
        DBSession.flush()
        send_comment_notification(media, c)

        if require_review:
            message = _('Thank you for your comment! We will post it just as '
                        'soon as a moderator approves it.')
            return result(True, message=message)
        else:
            return result(True, comment=c)

    @expose()
    def serve(self, id, download=False, **kwargs):
        """Serve a :class:`~mediadrop.model.media.MediaFile` binary.

        :param id: File ID
        :type id: ``int``
        :param bool download: If true, serve with an Content-Disposition that
            makes the file download to the users computer instead of playing
            in the browser.
        :raises webob.exc.HTTPNotFound: If no file exists with this ID.
        :raises webob.exc.HTTPNotAcceptable: If an Accept header field
            is present, and if the mimetype of the requested file doesn't
            match, then a 406 (not acceptable) response is returned.

        """
        file = fetch_row(MediaFile, id=id)
        request.perm.assert_permission(u'view', file.media.resource)

        file_type = file.mimetype.encode('utf-8')
        file_name = file.display_name.encode('utf-8')

        file_path = helpers.file_path(file)
        if file_path is None:
            log.warn('No path exists for requested media file: %r', file)
            raise HTTPNotFound()
        file_path = file_path.encode('utf-8')

        if not os.path.exists(file_path):
            log.warn('No such file or directory: %r', file_path)
            raise HTTPNotFound()

        # Ensure the request accepts files with this container
        accept = request.environ.get('HTTP_ACCEPT', '*/*')
        if not mimeparse.best_match([file_type], accept):
            raise HTTPNotAcceptable() # 406

        method = config.get('file_serve_method', None)
        headers = []

        # Serving files with this header breaks playback on iPhone
        if download:
            headers.append(('Content-Disposition',
                            'attachment; filename="%s"' % file_name))

        if method == 'apache_xsendfile':
            # Requires mod_xsendfile for Apache 2.x
            # XXX: Don't send Content-Length or Etag headers,
            #      Apache handles them for you.
            response.headers['X-Sendfile'] = file_path
            response.body = ''

        elif method == 'nginx_redirect':
            # Requires NGINX server configuration:
            # NGINX must have a location block configured that matches
            # the /__mediadrop_serve__ path below (the value configured by
            # setting  "nginx_serve_path" option in the configuration). It
            # should also be configured as an "internal" location to prevent
            # people from surfing directly to it.
            # For more information see: http://wiki.nginx.org/XSendfile
            serve_path = config.get('nginx_serve_path', '__mediadrop_serve__')
            if not serve_path.startswith('/'):
                serve_path = '/' + serve_path
            redirect_filename = '%s/%s' % (serve_path, os.path.basename(file_path))
            response.headers['X-Accel-Redirect'] = redirect_filename


        else:
            app = FileApp(file_path, headers, content_type=file_type)
            return forward(app)

        response.headers['Content-Type'] = file_type
        for header, value in headers:
            response.headers[header] = value

        return None

########NEW FILE########
__FILENAME__ = podcasts
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code contained in this file is licensed under the GPLv3 or
# (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.

from pylons import request, response
from sqlalchemy import orm

from mediadrop.lib.auth.util import viewable_media
from mediadrop.lib import helpers
from mediadrop.lib.base import BaseController
from mediadrop.lib.decorators import (beaker_cache, expose, observable, 
    paginate, validate)
from mediadrop.lib.helpers import content_type_for_response, url_for, redirect
from mediadrop.model import Media, Podcast, fetch_row
from mediadrop.plugin import events
from mediadrop.validation import LimitFeedItemsValidator

import logging
log = logging.getLogger(__name__)

class PodcastsController(BaseController):
    """
    Podcast Series Controller

    This handles episode collections, individual episodes are handled as
    regular media by :mod:`mediadrop.controllers.media`.
    """

    @expose('podcasts/index.html')
    @observable(events.PodcastsController.index)
    def index(self, **kwargs):
        """List podcasts and podcast media.

        :rtype: dict
        :returns:
            podcasts
                The :class:`~mediadrop.model.podcasts.Podcast` instance

        """
        podcasts = Podcast.query\
            .options(orm.undefer('media_count_published'))\
            .all()

        if len(podcasts) == 1:
            redirect(action='view', slug=podcasts[0].slug)

        podcast_episodes = {}
        for podcast in podcasts:
            episode_query = podcast.media.published().order_by(Media.publish_on.desc())
            podcast_episodes[podcast] = viewable_media(episode_query)[:4]

        return dict(
            podcasts = podcasts,
            podcast_episodes = podcast_episodes,
        )


    @expose('podcasts/view.html')
    @paginate('episodes', items_per_page=10)
    @observable(events.PodcastsController.view)
    def view(self, slug, page=1, show='latest', **kwargs):
        """View a podcast and the media that belongs to it.

        :param slug: A :attr:`~mediadrop.model.podcasts.Podcast.slug`
        :param page: Page number, defaults to 1.
        :type page: int
        :rtype: dict
        :returns:
            podcast
                A :class:`~mediadrop.model.podcasts.Podcast` instance.
            episodes
                A list of :class:`~mediadrop.model.media.Media` instances
                that belong to the ``podcast``.
            podcasts
                A list of all the other podcasts

        """
        podcast = fetch_row(Podcast, slug=slug)
        episodes = podcast.media.published()

        episodes, show = helpers.filter_library_controls(episodes, show)

        episodes = viewable_media(episodes)
        
        if request.settings['rss_display'] == 'True':
            response.feed_links.append(
               (url_for(action='feed'), podcast.title)
            )

        return dict(
            podcast = podcast,
            episodes = episodes,
            result_count = episodes.count(),
            show = show,
        )

    @validate(validators={'limit': LimitFeedItemsValidator()})
    @beaker_cache(expire=60 * 20)
    @expose('podcasts/feed.xml')
    @observable(events.PodcastsController.feed)
    def feed(self, slug, limit=None, **kwargs):
        """Serve the feed as RSS 2.0.

        If :attr:`~mediadrop.model.podcasts.Podcast.feedburner_url` is
        specified for this podcast, we redirect there if the useragent
        does not contain 'feedburner', as described here:
        http://www.google.com/support/feedburner/bin/answer.py?hl=en&answer=78464

        :param feedburner_bypass: If true, the redirect to feedburner is disabled.
        :rtype: Dict
        :returns:
            podcast
                A :class:`~mediadrop.model.podcasts.Podcast` instance.
            episodes
                A list of :class:`~mediadrop.model.media.Media` instances
                that belong to the ``podcast``.

        Renders: :data:`podcasts/feed.xml` XML

        """
        podcast = fetch_row(Podcast, slug=slug)

        if (podcast.feedburner_url
            and not 'feedburner' in request.environ.get('HTTP_USER_AGENT', '').lower()
            and not kwargs.get('feedburner_bypass', False)):
            redirect(podcast.feedburner_url.encode('utf-8'))

        response.content_type = content_type_for_response(
            ['application/rss+xml', 'application/xml', 'text/xml'])

        episode_query = podcast.media.published().order_by(Media.publish_on.desc())
        episodes = viewable_media(episode_query)
        if limit is not None:
            episodes = episodes.limit(limit)

        return dict(
            podcast = podcast,
            episodes = episodes,
        )

########NEW FILE########
__FILENAME__ = sitemaps
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code contained in this file is licensed under the GPLv3 or
# (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.

"""
Sitemaps Controller
"""
import logging
import math
import os

from formencode import validators
from paste.fileapp import FileApp
from pylons import config, request, response
from pylons.controllers.util import abort, forward
from webob.exc import HTTPNotFound

from mediadrop.plugin import events
from mediadrop.lib.base import BaseController
from mediadrop.lib.decorators import expose, beaker_cache, observable, validate
from mediadrop.lib.helpers import (content_type_for_response, 
    get_featured_category, url_for, viewable_media)
from mediadrop.model import Media
from mediadrop.validation import LimitFeedItemsValidator

log = logging.getLogger(__name__)

# Global cache of the FileApp used to serve the crossdomain.xml file
# when static_files is disabled and no Apache alias is configured.
crossdomain_app = None


class SitemapsController(BaseController):
    """
    Sitemap generation
    """

    @validate(validators={
        'page': validators.Int(if_empty=None, if_missing=None, if_invalid=None), 
        'limit': validators.Int(if_empty=10000, if_missing=10000, if_invalid=10000)
    })
    @beaker_cache(expire=60 * 60 * 4)
    @expose('sitemaps/google.xml')
    @observable(events.SitemapsController.google)
    def google(self, page=None, limit=10000, **kwargs):
        """Generate a sitemap which contains googles Video Sitemap information.

        This action may return a <sitemapindex> or a <urlset>, depending
        on how many media items are in the database, and the values of the
        page and limit params.

        :param page: Page number, defaults to 1.
        :type page: int
        :param page: max records to display on page, defaults to 10000.
        :type page: int

        """
        if request.settings['sitemaps_display'] != 'True':
            abort(404)

        response.content_type = \
            content_type_for_response(['application/xml', 'text/xml'])

        media = viewable_media(Media.query.published())

        if page is None:
            if media.count() > limit:
                return dict(pages=math.ceil(media.count() / float(limit)))
        else:
            page = int(page)
            media = media.offset(page * limit).limit(limit)

        if page:
            links = []
        else:
            links = [
                url_for(controller='/', qualified=True),
                url_for(controller='/media', show='popular', qualified=True),
                url_for(controller='/media', show='latest', qualified=True),
                url_for(controller='/categories', qualified=True),
            ]

        return dict(
            media = media,
            page = page,
            links = links,
        )

    @beaker_cache(expire=60 * 60, query_args=True)
    @expose('sitemaps/mrss.xml')
    @observable(events.SitemapsController.mrss)
    def mrss(self, **kwargs):
        """Generate a media rss (mRSS) feed of all the sites media."""
        if request.settings['sitemaps_display'] != 'True':
            abort(404)


        response.content_type = content_type_for_response(
            ['application/rss+xml', 'application/xml', 'text/xml'])

        media = viewable_media(Media.query.published())

        return dict(
            media = media,
            title = 'MediaRSS Sitemap',
        )

    @validate(validators={
        'limit': LimitFeedItemsValidator(),
        'skip': validators.Int(if_empty=0, if_missing=0, if_invalid=0)
    })
    @beaker_cache(expire=60 * 3)
    @expose('sitemaps/mrss.xml')
    @observable(events.SitemapsController.latest)
    def latest(self, limit=None, skip=0, **kwargs):
        """Generate a media rss (mRSS) feed of all the sites media."""
        if request.settings['rss_display'] != 'True':
            abort(404)

        response.content_type = content_type_for_response(
            ['application/rss+xml', 'application/xml', 'text/xml'])

        media_query = Media.query.published().order_by(Media.publish_on.desc())
        media = viewable_media(media_query)
        if limit is not None:
            media = media.limit(limit)

        if skip > 0:
            media = media.offset(skip)

        return dict(
            media = media,
            title = 'Latest Media',
        )

    @validate(validators={
        'limit': LimitFeedItemsValidator(),
        'skip': validators.Int(if_empty=0, if_missing=0, if_invalid=0)
    })
    @beaker_cache(expire=60 * 3)
    @expose('sitemaps/mrss.xml')
    @observable(events.SitemapsController.featured)
    def featured(self, limit=None, skip=0, **kwargs):
        """Generate a media rss (mRSS) feed of the sites featured media."""
        if request.settings['rss_display'] != 'True':
            abort(404)

        response.content_type = content_type_for_response(
            ['application/rss+xml', 'application/xml', 'text/xml'])

        media_query = Media.query.in_category(get_featured_category())\
            .published()\
            .order_by(Media.publish_on.desc())
        media = viewable_media(media_query)
        if limit is not None:
            media = media.limit(limit)

        if skip > 0:
            media = media.offset(skip)

        return dict(
            media = media,
            title = 'Featured Media',
        )

    @expose()
    def crossdomain_xml(self, **kwargs):
        """Serve the crossdomain XML file manually if static_files is disabled.

        If someone forgets to add this Alias we might as well serve this file
        for them and save everyone the trouble. This only works when MediaDrop
        is served out of the root of a domain and if Cooliris is enabled.
        """
        global crossdomain_app

        if not request.settings['appearance_enable_cooliris']:
            # Ensure the cache is cleared if cooliris is suddenly disabled
            if crossdomain_app:
                crossdomain_app = None
            raise HTTPNotFound()

        if not crossdomain_app:
            relpath = 'mediadrop/public/crossdomain.xml'
            abspath = os.path.join(config['here'], relpath)
            crossdomain_app = FileApp(abspath)

        return forward(crossdomain_app)

########NEW FILE########
__FILENAME__ = login_test
# -*- coding: utf-8 -*-
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code contained in this file is licensed under the GPLv3 or
# (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.

from pylons import config

from mediadrop.controllers.login import LoginController
from mediadrop.lib.auth.permission_system import MediaDropPermissionSystem
from mediadrop.lib.test import ControllerTestCase
from mediadrop.lib.test.pythonic_testcase import *
from mediadrop.model import DBSession, Group, User, Permission


class LoginControllerTest(ControllerTestCase):
    def test_non_editors_are_redirect_to_home_page_after_login(self):
        user = User.example()
        perm = MediaDropPermissionSystem.permissions_for_user(user, config)
        assert_false(perm.contains_permission(u'edit'))
        assert_false(perm.contains_permission(u'admin'))
        
        response = self.call_post_login(user)
        assert_equals('http://server.example:80/', response.location)
    
    def test_admins_are_redirect_to_admin_area_after_login(self):
        admin = self._create_user_with_admin_permission_only()
        
        response = self.call_post_login(admin)
        assert_equals('http://server.example:80/admin', response.location)
    
    def test_editors_are_redirect_to_admin_area_after_login(self):
        editor = self._create_user_with_edit_permission_only()
        
        response = self.call_post_login(editor)
        assert_equals('http://server.example:80/admin', response.location)
    
    def test_uses_correct_redirect_url_if_mediadrop_is_mounted_in_subdirectory(self):
        user = User.example()
        
        request = self.init_fake_request(server_name='server.example',
            request_uri='/login/post_login')
        request.environ['SCRIPT_NAME'] = 'my_media'
        
        response = self.call_post_login(user, request=request)
        assert_equals('http://server.example:80/my_media/', response.location)
    
    # - helpers ---------------------------------------------------------------
    
    def call_post_login(self, user, request=None):
        if request is None:
            request = self.init_fake_request(method='GET', 
                server_name='server.example', request_uri='/login/post_login')
        self.set_authenticated_user(user)
        response = self.assert_redirect(lambda: self.call_controller(LoginController, request))
        return response
    
    def editor_group(self):
        return DBSession.query(Group).filter(Group.group_name == u'editors').one()
    
    def _create_user_with_admin_permission_only(self):
        admin_perm = DBSession.query(Permission).filter(Permission.permission_name == u'admin').one()
        second_admin_group = Group.example(name=u'Second admin group')
        admin_perm.groups.append(second_admin_group)
        admin = User.example(groups=[second_admin_group])
        DBSession.commit()
        perm = MediaDropPermissionSystem.permissions_for_user(admin, config)
        assert_true(perm.contains_permission(u'admin'))
        assert_false(perm.contains_permission(u'edit'))
        return admin
    
    def _create_user_with_edit_permission_only(self):
        editor = User.example(groups=[self.editor_group()])
        perm = MediaDropPermissionSystem.permissions_for_user(editor, config)
        assert_true(perm.contains_permission(u'edit'))
        assert_false(perm.contains_permission(u'admin'))
        return editor


import unittest

def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(LoginControllerTest))
    return suite

########NEW FILE########
__FILENAME__ = upload_test
# -*- coding: utf-8 -*-
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code contained in this file is licensed under the GPLv3 or
# (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.

from StringIO import StringIO

import simplejson

from mediadrop.lib.attribute_dict import AttrDict
from mediadrop.lib.players import AbstractFlashPlayer, FlowPlayer
from mediadrop.lib.test import ControllerTestCase
from mediadrop.lib.test.pythonic_testcase import *
from mediadrop.model import fetch_row, Media


class UploadControllerTest(ControllerTestCase):
    def setUp(self):
        super(UploadControllerTest, self).setUp()
        AbstractFlashPlayer.register(FlowPlayer)
        FlowPlayer.inject_in_db(enable_player=True)
    
    def test_can_request_upload_form(self):
        request = self.init_fake_request(method='GET', request_uri='/upload')
        response = self._upload(request)
        assert_equals(200, response.status_int)
    
    def _upload(self, request):
        from mediadrop.controllers.upload import UploadController
        response = self.call_controller(UploadController, request)
        return response
    
    def _upload_parameters(self):
        fake_file = StringIO('fake mp3 file content')
        parameters = dict(
            name = 'John Doe',
            email = 'john.doe@site.example',
            title = 'testing mp3 async upload',
            description = 'a great song',
            url = '',
            file = AttrDict(read=fake_file.read, filename='awesome-song.mp3'),
        )
        return parameters
    
    def _assert_succesful_media_upload(self):
        media = fetch_row(Media, slug=u'testing-mp3-async-upload')
        assert_equals('John Doe', media.author.name)
        assert_equals('john.doe@site.example', media.author.email)
        assert_equals('testing mp3 async upload', media.title)
        assert_equals('<p>a great song</p>', media.description)
        
        assert_length(1, media.files)
        media_file = media.files[0]
        assert_equals('mp3', media_file.container)
        assert_equals('awesome-song.mp3', media_file.display_name)
        return media
    
    def test_can_upload_file_with_js(self):
        request = self.init_fake_request(method='POST', request_uri='/upload/submit_async', 
            post_vars=self._upload_parameters())
        response = self._upload(request)
        
        assert_equals(200, response.status_int)
        assert_equals('application/json', response.headers['Content-Type'])
        assert_equals({'redirect': '/upload/success', 'success': True}, 
                      simplejson.loads(response.body))
        self._assert_succesful_media_upload()
    
    def test_can_submit_upload_with_plain_html_form(self):
        request = self.init_fake_request(method='POST', request_uri='/upload/submit', 
            post_vars=self._upload_parameters())
        response = self.assert_redirect(lambda: self._upload(request))
        assert_equals('http://mediadrop.example/upload/success', response.location)
        self._assert_succesful_media_upload()


import unittest

def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(UploadControllerTest))
    return suite

########NEW FILE########
__FILENAME__ = upload
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code contained in this file is licensed under the GPLv3 or
# (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.

import simplejson as json

from pylons import request, tmpl_context
from pylons.controllers.util import abort

from mediadrop.forms.uploader import UploadForm
from mediadrop.lib import email
from mediadrop.lib.base import BaseController
from mediadrop.lib.decorators import autocommit, expose, observable, validate
from mediadrop.lib.helpers import redirect, url_for
from mediadrop.lib.storage import add_new_media_file
from mediadrop.lib.thumbnails import create_default_thumbs_for, has_thumbs
from mediadrop.model import Author, DBSession, get_available_slug, Media
from mediadrop.plugin import events

import logging
log = logging.getLogger(__name__)

upload_form = UploadForm(
    action = url_for(controller='/upload', action='submit'),
    async_action = url_for(controller='/upload', action='submit_async')
)

class UploadController(BaseController):
    """
    Media Upload Controller
    """

    def __before__(self, *args, **kwargs):
        if not request.settings['appearance_enable_user_uploads']:
            abort(404)
        result = BaseController.__before__(self, *args, **kwargs)
        # BareBonesController will set request.perm
        if not request.perm.contains_permission('upload'):
            abort(404)
        return result

    @expose('upload/index.html')
    @observable(events.UploadController.index)
    def index(self, **kwargs):
        """Display the upload form.

        :rtype: Dict
        :returns:
            legal_wording
                XHTML legal wording for rendering
            support_email
                An help contact address
            upload_form
                The :class:`~mediadrop.forms.uploader.UploadForm` instance
            form_values
                ``dict`` form values, if any

        """
        support_emails = request.settings['email_support_requests']
        support_emails = email.parse_email_string(support_emails)
        support_email = support_emails and support_emails[0] or None

        return dict(
            legal_wording = request.settings['wording_user_uploads'],
            support_email = support_email,
            upload_form = upload_form,
            form_values = kwargs,
        )

    @expose('json', request_method='POST')
    @validate(upload_form)
    @autocommit
    @observable(events.UploadController.submit_async)
    def submit_async(self, **kwargs):
        """Ajax form validation and/or submission.

        This is the save handler for :class:`~mediadrop.forms.media.UploadForm`.

        When ajax is enabled this action is called for each field as the user
        fills them in. Although the entire form is validated, the JS only
        provides the value of one field at a time,

        :param validate: A JSON list of field names to check for validation
        :parma \*\*kwargs: One or more form field values.
        :rtype: JSON dict
        :returns:
            :When validating one or more fields:

            valid
                bool
            err
                A dict of error messages keyed by the field names

            :When saving an upload:

            success
                bool
            redirect
                If valid, the redirect url for the upload successful page.

        """
        if 'validate' in kwargs:
            # we're just validating the fields. no need to worry.
            fields = json.loads(kwargs['validate'])
            err = {}
            for field in fields:
                if field in tmpl_context.form_errors:
                    err[field] = tmpl_context.form_errors[field]

            data = dict(
                valid = len(err) == 0,
                err = err
            )
        else:
            # We're actually supposed to save the fields. Let's do it.
            if len(tmpl_context.form_errors) != 0:
                # if the form wasn't valid, return failure
                tmpl_context.form_errors['success'] = False
                data = tmpl_context.form_errors
            else:
                # else actually save it!
                kwargs.setdefault('name')

                media_obj = self.save_media_obj(
                    kwargs['name'], kwargs['email'],
                    kwargs['title'], kwargs['description'],
                    None, kwargs['file'], kwargs['url'],
                )
                email.send_media_notification(media_obj)
                data = dict(
                    success = True,
                    redirect = url_for(action='success')
                )

        return data

    @expose(request_method='POST')
    @validate(upload_form, error_handler=index)
    @autocommit
    @observable(events.UploadController.submit)
    def submit(self, **kwargs):
        """
        """
        kwargs.setdefault('name')

        # Save the media_obj!
        media_obj = self.save_media_obj(
            kwargs['name'], kwargs['email'],
            kwargs['title'], kwargs['description'],
            None, kwargs['file'], kwargs['url'],
        )
        email.send_media_notification(media_obj)

        # Redirect to success page!
        redirect(action='success')

    @expose('upload/success.html')
    @observable(events.UploadController.success)
    def success(self, **kwargs):
        return dict()

    @expose('upload/failure.html')
    @observable(events.UploadController.failure)
    def failure(self, **kwargs):
        return dict()

    def save_media_obj(self, name, email, title, description, tags, uploaded_file, url):
        # create our media object as a status-less placeholder initially
        media_obj = Media()
        media_obj.author = Author(name, email)
        media_obj.title = title
        media_obj.slug = get_available_slug(Media, title)
        media_obj.description = description
        if request.settings['wording_display_administrative_notes']:
            media_obj.notes = request.settings['wording_administrative_notes']
        media_obj.set_tags(tags)

        # Give the Media object an ID.
        DBSession.add(media_obj)
        DBSession.flush()

        # Create a MediaFile object, add it to the media_obj, and store the file permanently.
        media_file = add_new_media_file(media_obj, file=uploaded_file, url=url)

        # The thumbs may have been created already by add_new_media_file
        if not has_thumbs(media_obj):
            create_default_thumbs_for(media_obj)

        media_obj.update_status()
        DBSession.flush()

        return media_obj

########NEW FILE########
__FILENAME__ = categories
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code contained in this file is licensed under the GPLv3 or
# (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.

from tw.api import WidgetsList
from tw.forms import CheckBoxList, HiddenField, SingleSelectField
from tw.forms.validators import NotEmpty

from mediadrop.model.categories import Category
from mediadrop.forms import Form, ListForm, ResetButton, SubmitButton, TextField
from mediadrop.lib import helpers
from mediadrop.lib.i18n import N_
from mediadrop.plugin import events

def option_tree(cats):
    indent = helpers.decode_entities(u'&nbsp;') * 4
    return [(None, None)] + \
        [(c.id, indent * depth + c.name) for c, depth in cats.traverse()]

def category_options():
    return option_tree(Category.query.order_by(Category.name.asc()).populated_tree())

class CategoryForm(ListForm):
    template = 'admin/tags_and_categories_form.html'
    id = None
    css_classes = ['category-form', 'form']
    submit_text = None
    
    event = events.Admin.CategoryForm

    # required to support multiple named buttons to differentiate between Save & Delete?
    _name = 'vf'

    class fields(WidgetsList):
        name = TextField(validator=TextField.validator(not_empty=True), label_text=N_('Name'))
        slug = TextField(validator=NotEmpty, label_text=N_('Permalink'))
        parent_id = SingleSelectField(label_text=N_('Parent Category'), options=category_options)
        cancel = ResetButton(default=N_('Cancel'), css_classes=['btn', 'f-lft', 'btn-cancel'])
        save = SubmitButton(default=N_('Save'), named_button=True, css_classes=['f-rgt', 'btn', 'blue', 'btn-save'])

class CategoryCheckBoxList(CheckBoxList):
    params = ['category_tree']
    template = 'admin/categories/selection_list.html'

class CategoryRowForm(Form):
    template = 'admin/categories/row-form.html'
    id = None
    submit_text = None
    params = ['category', 'depth', 'first_child']
    
    event = events.Admin.CategoryRowForm

    class fields(WidgetsList):
        name = HiddenField()
        slug = HiddenField()
        parent_id = HiddenField()
        delete = SubmitButton(default=N_('Delete'), css_classes=['btn', 'table-row', 'delete', 'btn-inline-delete'])

########NEW FILE########
__FILENAME__ = comments
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code contained in this file is licensed under the GPLv3 or
# (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.

from tw.forms.validators import NotEmpty
from tw.api import WidgetsList

from mediadrop.forms import ListForm, ResetButton, SubmitButton, TextArea
from mediadrop.lib.i18n import N_
from mediadrop.plugin import events

class EditCommentForm(ListForm):
    template = 'admin/comments/edit.html'
    id = None
    css_class = 'edit-comment-form'
    
    event = events.Admin.EditCommentForm
    
    class fields(WidgetsList):
        body = TextArea(validator=NotEmpty, label_text=N_('Comment'), attrs=dict(rows=5, cols=25))
        submit = SubmitButton(default=N_('Save'), css_classes=['btn', 'btn-save', 'blue', 'f-rgt'])
        cancel = ResetButton(default=N_('Cancel'), css_classes=['btn', 'btn-cancel'])


########NEW FILE########
__FILENAME__ = groups
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code contained in this file is licensed under the GPLv3 or
# (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.

from pylons import request
from tw.forms import CheckBoxList
from tw.forms.validators import All, FancyValidator, Invalid, PlainText

from mediadrop.forms import ListForm, SubmitButton, TextField
from mediadrop.lib.i18n import N_, _
from mediadrop.model import DBSession
from mediadrop.model.auth import Group, Permission
from mediadrop.plugin import events


class UniqueGroupname(FancyValidator):
    def _to_python(self, value, state):
        id = request.environ['pylons.routes_dict']['id']

        query = DBSession.query(Group).filter_by(group_name=value)
        if id != 'new':
            query = query.filter(Group.group_id != id)

        if query.count() != 0:
            raise Invalid(_('Group name already exists'), value, state)
        return value

class GroupForm(ListForm):
    template = 'admin/box-form.html'
    id = 'group-form'
    css_class = 'form'
    submit_text = None
    show_children_errors = True
    
    event = events.Admin.GroupForm
    
    fields = [
        TextField('display_name', label_text=N_('Display Name'), validator=TextField.validator(not_empty=True), maxlength=255),
        TextField('group_name', label_text=N_('Groupname'), validator=All(PlainText(not_empty=True), UniqueGroupname()), maxlength=16),
        CheckBoxList('permissions', label_text=N_('Group Permissions'), 
            css_classes=['details_fieldset'],
            options=lambda: DBSession.query(Permission.permission_id, Permission.description).all()
        ),
        SubmitButton('save', default=N_('Save'), named_button=True, css_classes=['btn', 'btn-save', 'blue', 'f-rgt']),
        SubmitButton('delete', default=N_('Delete'), named_button=True, css_classes=['btn', 'btn-delete']),
    ]


########NEW FILE########
__FILENAME__ = media
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code contained in this file is licensed under the GPLv3 or
# (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.


from pylons import request
from tw.api import WidgetsList
from formencode import Invalid
from formencode.validators import FancyValidator
from tw.forms import HiddenField, SingleSelectField
from tw.forms.validators import Int, DateTimeConverter, FieldStorageUploadConverter, OneOf

from mediadrop.lib import helpers
from mediadrop.lib.filetypes import registered_media_types
from mediadrop.lib.i18n import N_, _
from mediadrop.forms import FileField, Form, ListForm, SubmitButton, TextArea, TextField, XHTMLTextArea, email_validator
from mediadrop.forms.admin.categories import CategoryCheckBoxList
from mediadrop.model import Category, DBSession, Podcast
from mediadrop.plugin import events
from mediadrop.validation import URIValidator

class DurationValidator(FancyValidator):
    """
    Duration to Seconds Converter
    """
    def _to_python(self, value, state=None):
        try:
            return helpers.duration_to_seconds(value)
        except ValueError:
            msg = _('Bad duration formatting, use Hour:Min:Sec')
            # Colons have special meaning in error messages
            msg.replace(':', '&#058;')
            raise Invalid(msg, value, state)

    def _from_python(self, value, state):
        return helpers.duration_from_seconds(value)

class WXHValidator(FancyValidator):
    """
    width by height validator.
    example input 1: "800x600"
    example output 2: (800, 600)

    example input 2: ""
    example output 2: (None, None)

    example input 3: "0x0"
    example output 3:" (None, None)
    """
    def _to_python(self, value, state=None):
        if not value.strip():
            return (None, None)

        try:
            width, height = value.split('x')
        except ValueError, e:
            raise Invalid(
                _('Value must be in the format wxh; e.g. 200x300'),
                value, state)
        errors = []
        try:
            width = int(width)
        except ValueError, e:
            errors.append(_('Width must be a valid integer'))
        try:
            height = int(height)
        except ValueError, e:
            errors.append(_('Height must be a valid integer'))
        if errors:
            raise Invalid(u'; '.join(errors), value, state)

        if (width, height) == (0, 0):
            return (None, None)

        return width, height


    def _from_python(self, value, state):
        if value == (None, None):
            return "0x0"

        width, height = value
        return u"%dx%d" % (width, height)

class OneOfGenerator(OneOf):
    __unpackargs__ = ('generator',)
    def validate_python(self, value, state):
        if not value in self.generator():
            if self.hideList:
                raise Invalid(self.message('invalid', state), value, state)
            else:
                items = '; '.join(map(str, self.list))
                raise Invalid(
                    self.message('notIn', state, items=items, value=value),
                    value,
                    state
                )

class AddFileForm(ListForm):
    template = 'admin/media/file-add-form.html'
    id = 'add-file-form'
    submit_text = None
    
    event = events.Admin.AddFileForm
    
    fields = [
        FileField('file', label_text=N_('Select an encoded video or audio file on your computer'), validator=FieldStorageUploadConverter(not_empty=False, label_text=N_('Upload'))),
        SubmitButton('add_url', default=N_('Add URL'), named_button=True, css_class='btn grey btn-add-url f-rgt'),
        TextField('url', validator=URIValidator, suppress_label=True, attrs=lambda: {'title': _('YouTube, Vimeo, Amazon S3 or any other link')}, maxlength=255),
    ]

file_type_options = lambda: registered_media_types()
file_types = lambda: (id for id, name in registered_media_types())
file_type_validator = OneOfGenerator(file_types, if_missing=None)

class EditFileForm(ListForm):
    template = 'admin/media/file-edit-form.html'
    submit_text = None
    _name = 'fileeditform'
    params = ['file']
    
    event = events.Admin.EditFileForm
    
    class fields(WidgetsList):
        file_id = TextField(validator=Int())
        file_type = SingleSelectField(validator=file_type_validator, options=file_type_options, attrs={'id': None, 'autocomplete': 'off'})
        duration = TextField(validator=DurationValidator, attrs={'id': None, 'autocomplete': 'off'})
        width_height = TextField(validator=WXHValidator, attrs={'id': None, 'autocomplete': 'off'})
        bitrate = TextField(validator=Int, attrs={'id': None, 'autocomplete': 'off'})
        delete = SubmitButton(default=N_('Delete file'), named_button=True, css_class='file-delete', attrs={'id': None})


class MediaForm(ListForm):
    template = 'admin/box-form.html'
    id = 'media-form'
    css_class = 'form'
    submit_text = None
    show_children_errors = True
    _name = 'media-form' # TODO: Figure out why this is required??
    
    event = events.Admin.MediaForm
    
    fields = [
        SingleSelectField('podcast', label_text=N_('Include in the Podcast'), css_classes=['dropdown-select'], help_text=N_('Optional'), options=lambda: [(None, None)] + DBSession.query(Podcast.id, Podcast.title).all()),
        TextField('slug', label_text=N_('Permalink'), maxlength=50),
        TextField('title', label_text=N_('Title'), validator=TextField.validator(not_empty=True), maxlength=255),
        TextField('author_name', label_text=N_('Author Name'), maxlength=50),
        TextField('author_email', label_text=N_('Author Email'), validator=email_validator(not_empty=True), maxlength=255),
        XHTMLTextArea('description', label_text=N_('Description'), attrs=dict(rows=5, cols=25)),
        CategoryCheckBoxList('categories', label_text=N_('Categories'), options=lambda: DBSession.query(Category.id, Category.name).all()),
        TextArea('tags', label_text=N_('Tags'), attrs=dict(rows=3, cols=15), help_text=N_(u'e.g.: puppies, great dane, adorable')),
        TextArea('notes',
            label_text=N_('Administrative Notes'),
            attrs=dict(rows=3, cols=25),
            container_attrs = lambda: ({'class': 'hidden'}, {})[bool(request.settings.get('wording_display_administrative_notes', ''))],
            default=lambda: request.settings['wording_administrative_notes']),
        SubmitButton('save', default=N_('Save'), named_button=True, css_classes=['btn', 'blue', 'f-rgt']),
        SubmitButton('delete', default=N_('Delete'), named_button=True, css_classes=['btn', 'f-lft']),
    ]


class UpdateStatusForm(Form):
    template = 'admin/media/update-status-form.html'
    id = 'update-status-form'
    css_class = 'form'
    submit_text = None
    params = ['media']
    media = None
    _name = 'usf'
    
    event = events.Admin.UpdateStatusForm

    class fields(WidgetsList):
        # TODO: handle format with babel localization
        publish_on = HiddenField(validator=DateTimeConverter(format='%b %d %Y @ %H:%M'))
        publish_until = HiddenField(validator=DateTimeConverter(format='%b %d %Y @ %H:%M'))
        status = HiddenField(validator=None)
        update_button = SubmitButton()

########NEW FILE########
__FILENAME__ = players
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code contained in this file is licensed under the GPLv3 or
# (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.
import logging
from formencode.validators import Int

from tw.forms import CheckBox, RadioButtonList
from tw.forms.validators import StringBool

from mediadrop.forms import ListFieldSet, ListForm, SubmitButton, TextField
from mediadrop.lib.i18n import N_, _
from mediadrop.lib.util import merge_dicts
from mediadrop.plugin import events

log = logging.getLogger(__name__)

class PlayerPrefsForm(ListForm):
    template = 'admin/box-form.html'
    id = 'player-form'
    css_class = 'form playerform'
    submit_text = None
    show_children_errors = True
    _name = 'player-form' # TODO: Figure out why this is required??
    params = ['player']

    fields = [
        ListFieldSet('general',
            legend=N_('General Options:'),
            suppress_label=True,
            children=[
                TextField('display_name',
                    label_text=N_('Display Name'),
                    validator=TextField.validator(not_empty=True),
                    maxlength=100,
                ),
            ],
        ),
    ]

    buttons = [
        SubmitButton('save',
            default=N_('Save'),
            css_classes=['btn', 'btn-save', 'blue', 'f-rgt'],
        ),
    ]

    def display(self, value, player, **kwargs):
        """Display the form with default values from the given player.

        If the value dict is not fully populated, populate any missing entries
        with the values from the given player's
        :attr:`_data <mediadrop.model.player.PlayerPrefs._data>` dict.

        :param value: A (sparse) dict of values to populate the form with.
        :type value: dict
        :param player: The player prefs mapped object to retrieve the default
            values from.
        :type player: :class:`mediadrop.model.player.PlayerPrefs` subclass

        """
        return ListForm.display(self, value, **kwargs)

    def save_data(self, player, **kwargs):
        """Map validated field values to `PlayerPrefs.data`.

        Since form widgets may be nested or named differently than the keys
        in the :attr:`mediadrop.lib.storage.StorageEngine._data` dict, it is
        necessary to manually map field values to the data dictionary.

        :type player: :class:`mediadrop.model.player.PlayerPrefs` subclass
        :param player: The player prefs mapped object to store the data in.
        :param \*\*kwargs: Validated and filtered form values.
        :raises formencode.Invalid: If some post-validation error is detected
            in the user input. This will trigger the same error handling
            behaviour as with the @validate decorator.

        """

class HTML5OrFlashPrefsForm(PlayerPrefsForm):
    fields = [
        RadioButtonList('prefer_flash',
            options=lambda: (
                (False, _('Yes, use the Flash Player when the device supports it.')),
                (True, _('No, use the HTML5 Player when the device supports it.')),
            ),
            css_classes=['options'],
            label_text=N_('Prefer the Flash Player when possible'),
            validator=StringBool,
        ),
    ] + PlayerPrefsForm.buttons
    
    event = events.Admin.Players.HTML5OrFlashPrefsForm

    def display(self, value, player, **kwargs):
        value.setdefault('prefer_flash', player.data.get('prefer_flash', False))
        return PlayerPrefsForm.display(self, value, player, **kwargs)

    def save_data(self, player, prefer_flash, **kwargs):
        player.data['prefer_flash'] = prefer_flash

class SublimePlayerPrefsForm(PlayerPrefsForm):
    event = events.Admin.Players.SublimePlayerPrefsForm
    
    fields = [
        TextField('script_tag',
            label_text=N_('Script Tag'),
            help_text=N_('The unique script tag given for your site.'),
        ),
    ] + PlayerPrefsForm.buttons

    def display(self, value, player, **kwargs):
        value.setdefault('script_tag', player.data.get('script_tag', ''))
        return PlayerPrefsForm.display(self, value, player, **kwargs)

    def save_data(self, player, script_tag, **kwargs):
        player.data['script_tag'] = script_tag or None
        if not script_tag and player.enabled:
            player.enabled = False

class YoutubePlayerPrefsForm(PlayerPrefsForm):
    event = events.Admin.Players.YoutubeFlashPlayerPrefsForm
    
    fields = [
        ListFieldSet('options',
            suppress_label=True,
            legend=N_('Player Options:'),
            children=[
                RadioButtonList('version',
                    options=lambda: (
                        (2, _('Use the deprecated AS2 player.')),
                        (3, _('Use the AS3/HTML5 player.')),
                    ),
                    css_label_classes=['container-list-label'],
                    label_text=N_("YouTube player version"),
                    validator=Int,
                ),
                RadioButtonList('iv_load_policy',
                    options=lambda: (
                        (1, _('Show video annotations by default.')),
                        (3, _('Hide video annotations by default.')),
                    ),
                    css_label_classes=['container-list-label'],
                    label_text=N_("Video annotations"),
                    validator=Int,
                ),
                CheckBox('disablekb', label_text=N_('Disable the player keyboard controls.'),
                    help_text=N_('Not supported by HTML5 player.')),
                CheckBox('autoplay', label_text=N_('Autoplay the video when the player loads.')),
                CheckBox('modestbranding', label_text=N_('Do not show YouTube logo in the player controls'), 
                    help_text=N_('Not supported by AS2 player.')),
                CheckBox('fs', label_text=N_('Display fullscreen button.')),
                CheckBox('hd', label_text=N_('Enable high-def quality by default.'), 
                    help_text=N_('Applies only for the AS2 player, the AS3 player will choose the most appropriate version of the video version (e.g. considering the user\'s bandwidth)')),
                CheckBox('rel', label_text=N_('Display related videos after playback of the initial video ends.')),
                CheckBox('showsearch', label_text=N_('Show the search box when the video is minimized. The related videos option must be enabled for this to work.'),
                    help_text=N_('AS2 player only')),
                CheckBox('showinfo', label_text=N_('Display information like the video title and uploader before the video starts playing.')),
                CheckBox('wmode', label_text=N_('Enable window-less mode (wmode)'), 
                    help_text=N_('wmode allows HTML/CSS elements to be placed over the actual Flash video but requires more CPU power.')),
                RadioButtonList('autohide',
                    options=lambda: (
                        (0, _('Always show player controls.')),
                        (1, _('Autohide all player controls after a video starts playing.')),
                        (2, _('Autohide only the progress bar after a video starts playing.')),
                    ),
                    css_label_classes=['container-list-label'],
                    label_text=N_("Player control hiding"),
                    validator=Int,
                ),
            ],
            css_classes=['options'],
        )
    ] + PlayerPrefsForm.buttons

    def display(self, value, player, **kwargs):
        newvalue = {}
        defaults = {'options': player.data}
        merge_dicts(newvalue, defaults, value)
        return PlayerPrefsForm.display(self, newvalue, player, **kwargs)

    def save_data(self, player, options, **kwargs):
        for field, value in options.iteritems():
            player.data[field] = int(value)

########NEW FILE########
__FILENAME__ = podcasts
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code contained in this file is licensed under the GPLv3 or
# (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.

from formencode.validators import URL
from tw.forms import SingleSelectField
from tw.forms.validators import NotEmpty

from mediadrop.forms import ListForm, ListFieldSet, SubmitButton, TextField, XHTMLTextArea, email_validator
from mediadrop.lib.i18n import N_, _
from mediadrop.plugin import events

class PodcastForm(ListForm):
    template = 'admin/box-form.html'
    id = 'podcast-form'
    css_class = 'form'
    submit_text = None
    
    event = events.Admin.PodcastForm
    
    # required to support multiple named buttons to differentiate between Save & Delete?
    _name = 'vf'

    explicit_options = lambda: (
        ('no', ''),
        ('yes', _('Parental Advisory')),
        ('clean', _('Clean')),
    )
    category_options = [
        'Arts',
        'Arts > Design',
        'Arts > Fashion & Beauty',
        'Arts > Food',
        'Arts > Literature',
        'Arts > Performing Arts',
        'Arts > Visual Arts',
        'Business',
        'Business > Business News',
        'Business > Careers',
        'Business > Investing',
        'Business > Management & Marketing',
        'Business > Shopping',
        'Comedy',
        'Education',
        'Education > Education Technology',
        'Education > Higher Education',
        'Education > K-12',
        'Education > Language Courses',
        'Education > Training',
        'Games & Hobbies',
        'Games & Hobbies > Automotive',
        'Games & Hobbies > Aviation',
        'Games & Hobbies > Hobbies',
        'Games & Hobbies > Other Games',
        'Games & Hobbies > Video Games',
        'Government & Organizations',
        'Government & Organizations > Local',
        'Government & Organizations > National',
        'Government & Organizations > Non-Profit',
        'Government & Organizations > Regional',
        'Health',
        'Health > Alternative Health',
        'Health > Fitness & Nutrition',
        'Health > Self-Help',
        'Health > Sexuality',
        'Kids & Family',
        'Music',
        'News & Politics',
        'Religion & Spirituality',
        'Religion & Spirituality > Buddhism',
        'Religion & Spirituality > Christianity',
        'Religion & Spirituality > Hinduism',
        'Religion & Spirituality > Islam',
        'Religion & Spirituality > Judaism',
        'Religion & Spirituality > Other',
        'Religion & Spirituality > Spirituality',
        'Science & Medicine',
        'Science & Medicine > Medicine',
        'Science & Medicine > Natural Sciences',
        'Science & Medicine > Social Sciences',
        'Society & Culture',
        'Society & Culture > History',
        'Society & Culture > Personal Journals',
        'Society & Culture > Philosophy',
        'Society & Culture > Places & Travel',
        'Sports & Recreation',
        'Sports & Recreation > Amateur',
        'Sports & Recreation > College & High School',
        'Sports & Recreation > Outdoor',
        'Sports & Recreation > Professional',
        'Technology',
        'Technology > Gadgets',
        'Technology > Tech News',
        'Technology > Podcasting',
        'Technology > Software How-To',
        'TV & Film',
    ]

    fields = [
        TextField('slug', label_text=N_('Permalink'), validator=NotEmpty, maxlength=50),
        TextField('title', label_text=N_('Title'), validator=TextField.validator(not_empty=True), maxlength=50),
        TextField('subtitle', label_text=N_('Subtitle'), maxlength=255),
        TextField('author_name', label_text=N_('Author Name'), validator=TextField.validator(not_empty=True), maxlength=50),
        TextField('author_email', label_text=N_('Author Email'), validator=email_validator(not_empty=True), maxlength=50),
        XHTMLTextArea('description', label_text=N_('Description'), attrs=dict(rows=5, cols=25)),
        ListFieldSet('details', suppress_label=True, legend=N_('Podcast Details:'), css_classes=['details_fieldset'], children=[
            SingleSelectField('explicit', label_text=N_('Explicit?'), options=explicit_options),
            SingleSelectField('category', label_text=N_('Category'), options=category_options),
            TextField('copyright', label_text=N_('Copyright'), maxlength=50),
        ]),
        ListFieldSet('feed', suppress_label=True, legend=N_('Advanced Options:'), css_classes=['details_fieldset'], template='/admin/podcasts/feed_fieldset.html', children=[
            TextField('feed_url', maxlength=50, label_text=N_('Your Feed URL'), attrs={'readonly': True}),
            TextField('itunes_url', validator=URL, label_text=N_('iTunes URL'), maxlength=80),
            TextField('feedburner_url', validator=URL, label_text=N_('Feedburner URL'), maxlength=80),
        ]),
        SubmitButton('save', default=N_('Save'), named_button=True, css_classes=['btn', 'blue', 'f-rgt']),
        SubmitButton('delete', default=N_('Delete'), named_button=True, css_classes=['btn']),
    ]

########NEW FILE########
__FILENAME__ = settings
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code contained in this file is licensed under the GPLv3 or
# (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.

from operator import itemgetter

from babel.core import Locale
from pylons import request
from tw.forms import RadioButtonList, SingleSelectField
from tw.forms.fields import CheckBox
from tw.forms.validators import (Bool, FieldStorageUploadConverter,
    Int, OneOf, Regex, StringBool)

from mediadrop.forms import (FileField, ListFieldSet, ListForm,
    SubmitButton, TextArea, TextField, XHTMLTextArea,
    email_validator, email_list_validator)
from mediadrop.forms.admin.categories import category_options
from mediadrop.lib.i18n import N_, _, get_available_locales
from mediadrop.plugin import events

comments_enable_disable = lambda: (
    ('builtin', _("Built-in comments")),
    ('facebook', _('Facebook comments (requires a Facebook application ID)')),
    ('disabled', _('Disable comments')),
)
comments_enable_validator = OneOf(('builtin', 'facebook', 'disabled'))

title_options = lambda: (
    ('prepend', _('Prepend')),
    ('append', _('Append')),
)
rich_text_editors = lambda: (
    ('plain', _('Plain <textarea> fields (0kB)')),
    ('tinymce', _('Enable TinyMCE for <textarea> fields accepting XHTML (281kB)')),
)
rich_text_editors_validator = OneOf(('plain', 'tinymce'))
navbar_colors = lambda: (
    ('brown', _('Brown')),
    ('blue', _('Blue')),
    ('green', _('Green')),
    ('tan', _('Tan')),
    ('white', _('White')),
    ('purple', _('Purple')),
    ('black', _('Black')),
)

hex_validation_regex = "^#\w{3,6}$"
# End Appearance Settings #

def languages():
    # Note the extra space between English and [en]. This makes it sort above
    # the other translations of english, but is invisible to the user.
    result = [('en', u'English  [en]')]
    for name in get_available_locales():
        locale = Locale.parse(name)
        lang = locale.languages[locale.language].capitalize()
        if locale.territory:
            lang += u' (%s)' % locale.territories[locale.territory]
        else:
            lang += u' '
        lang += u' [%s]' % locale
        result.append((name, lang))
    result.sort(key=itemgetter(1))
    return result


def boolean_radiobuttonlist(name, **kwargs):
    return RadioButtonList(
        name,
        options=lambda: ((True, _('Yes')), (False, _('No'))),
        validator=StringBool,
        **kwargs
    )

class NotificationsForm(ListForm):
    template = 'admin/box-form.html'
    id = 'settings-form'
    css_class = 'form'
    submit_text = None
    
    event = events.Admin.Settings.NotificationsForm
    
    fields = [
        ListFieldSet('email', suppress_label=True, legend=N_('Email Notifications:'), css_classes=['details_fieldset'], children=[
            TextField('email_media_uploaded', validator=email_list_validator, label_text=N_('Media Uploaded'), maxlength=255),
            TextField('email_comment_posted', validator=email_list_validator, label_text=N_('Comment Posted'), maxlength=255),
            TextField('email_support_requests', validator=email_list_validator, label_text=N_('Support Requested'), maxlength=255),
            TextField('email_send_from', validator=email_validator, label_text=N_('Send Emails From'), maxlength=255),
        ]),
        SubmitButton('save', default=N_('Save'), css_classes=['btn', 'btn-save', 'blue', 'f-rgt']),
    ]


class PopularityForm(ListForm):
    template = 'admin/box-form.html'
    id = 'settings-form'
    css_class = 'form'
    submit_text = None
    
    event = events.Admin.Settings.PopularityForm
    
    fields = [
        ListFieldSet('popularity',
            suppress_label=True,
            css_classes=['details_fieldset'],
            legend=N_('Popularity Algorithm Variables:'),
            children=[
                TextField('popularity_decay_exponent', validator=Int(not_empty=True, min=1), label_text=N_('Decay Exponent')),
                TextField('popularity_decay_lifetime', validator=Int(not_empty=True, min=1), label_text=N_('Decay Lifetime')),
            ]
        ),
        SubmitButton('save', default=N_('Save'), css_classes=['btn', 'btn-save', 'blue', 'f-rgt']),
    ]

class MegaByteValidator(Int):
    """
    Integer Validator that accepts megabytes and translates to bytes.
    """
    def _to_python(self, value, state=None):
        try:
            value = int(value) * 1024 ** 2
        except ValueError:
            pass
        return super(MegaByteValidator, self)._to_python(value, state)

    def _from_python(self, value, state):
        try:
            value = int(value) / 1024 ** 4
        except ValueError:
            pass
        return super(MegaByteValidator, self)._from_python(value, state)

class UploadForm(ListForm):
    template = 'admin/box-form.html'
    id = 'settings-form'
    css_class = 'form'
    submit_text = None
    
    event = events.Admin.Settings.UploadForm
    
    fields = [
        TextField('max_upload_size', label_text=N_('Max. allowed upload file size in megabytes'), validator=MegaByteValidator(not_empty=True, min=0)),
        ListFieldSet('legal_wording', suppress_label=True, legend=N_('Legal Wording:'), css_classes=['details_fieldset'], children=[
            XHTMLTextArea('wording_user_uploads', label_text=N_('User Uploads'), attrs=dict(rows=15, cols=25)),
        ]),
        SubmitButton('save', default=N_('Save'), css_classes=['btn', 'btn-save', 'blue', 'f-rgt']),
    ]

class AnalyticsForm(ListForm):
    template = 'admin/box-form.html'
    id = 'settings-form'
    css_class = 'form'
    submit_text = None
    
    event = events.Admin.Settings.AnalyticsForm
    
    fields = [
        ListFieldSet('google', suppress_label=True, legend=N_('Google Analytics Details:'), css_classes=['details_fieldset'], children=[
            TextField('google_analytics_uacct', maxlength=255, label_text=N_('Tracking Code')),
        ]),
        SubmitButton('save', default=N_('Save'), css_classes=['btn', 'btn-save', 'blue', 'f-rgt']),
    ]

class SiteMapsForm(ListForm):
    template = 'admin/box-form.html'
    id = 'settings-form'
    css_class = 'form'
    submit_text = None
    
    event = events.Admin.Settings.SiteMapsForm
    
    fields = [
        ListFieldSet('rss', suppress_label=True,
            legend='',
            css_classes=['details_fieldset'],
            children=[
                CheckBox('sitemaps_display',
                    css_classes=['checkbox-left'],
                    label_text=N_('Site Maps'),
                    validator=Bool(if_missing='')),
                CheckBox('rss_display',
                    css_classes=['checkbox-left'],
                    label_text=N_('RSS Feeds'),
                    validator=Bool(if_missing='')),
            ]
        ),
        ListFieldSet('feeds',
            suppress_label=True,
            css_classes=['details_fieldset'],
            legend=N_('RSS Feed Defaults:'),
            children=[
                TextField(u'default_feed_results', validator=Int(not_empty=True, min=1, if_missing=30), 
                    label_text=N_(u'number of items'),
                    help_text=N_(u'The number of items in the feed can be overriden per request '
                                 U'if you add "?limit=X" to the feed URL. If the "limit" parameter '
                                 u'is absent, the default above is used.'),
                ),
            ]
        ),
        SubmitButton('save', default=N_('Save'), css_classes=['btn', 'btn-save', 'blue', 'f-rgt']),
    ]

class GeneralForm(ListForm):
    template = 'admin/box-form.html'
    id = 'settings-form'
    css_class = 'form'
    submit_text = None
    
    event = events.Admin.Settings.GeneralForm
    
    fields = [
        ListFieldSet('general', suppress_label=True, legend=N_('General Settings:'), css_classes=['details_fieldset'], children=[
            TextField('general_site_name', maxlength=255,
                label_text=N_('Site Name')),
            SingleSelectField('general_site_title_display_order',
                label_text=N_('Display Site Name'),
                options=title_options,
            ),
            SingleSelectField('primary_language',
                label_text=N_('Default Language'), # TODO v0.9.1: Change to 'Primary Language'
                options=languages,
            ),
            SingleSelectField('featured_category',
                label_text=N_('Featured Category'),
                options=category_options,
                validator=Int(),
            ),
            RadioButtonList('rich_text_editor',
                label_text=N_('Rich Text Editing'),
                options=rich_text_editors,
                validator=rich_text_editors_validator,
            ),
        ]),
        SubmitButton('save', default=N_('Save'), css_classes=['btn', 'btn-save', 'blue', 'f-rgt']),
    ]

class CommentsForm(ListForm):
    template = 'admin/box-form.html'
    id = 'settings-form'
    css_class = 'form'
    submit_text = None
    
    event = events.Admin.Settings.CommentsForm
    
    fields = [
       RadioButtonList('comments_engine',
            label_text=N_('Comment Engine'),
            options=comments_enable_disable,
            validator=comments_enable_validator,
        ),
        ListFieldSet('builtin', suppress_label=True, legend=N_('Built-in Comments:'), css_classes=['details_fieldset'], children=[

            CheckBox('req_comment_approval',
                label_text=N_('Moderation'),
                help_text=N_('Require comments to be approved by an admin'),
                css_classes=['checkbox-inline-help'],
                validator=Bool(if_missing='')),
            TextField('akismet_key', label_text=N_('Akismet Key')),
            TextField('akismet_url', label_text=N_('Akismet URL')),
            TextArea('vulgarity_filtered_words', label_text=N_('Filtered Words'),
                attrs=dict(rows=3, cols=15),
                help_text=N_('Enter words to be filtered separated by a comma.')),
        ]),
        ListFieldSet('facebook', suppress_label=True, legend=N_('Facebook Comments:'), css_classes=['details_fieldset'], children=[
            TextField('facebook_appid', label_text=N_('Application ID'),
                help_text=N_('See: https://developers.facebook.com/apps')),
        ]),
        SubmitButton('save', default=N_('Save'), css_classes=['btn', 'btn-save', 'blue', 'f-rgt']),
    ]

class APIForm(ListForm):
    template = 'admin/box-form.html'
    id = 'settings-form'
    css_class = 'form'
    submit_text = None
    
    event = events.Admin.Settings.APIForm
    
    fields = [
        boolean_radiobuttonlist('api_secret_key_required', label_text=N_('Require a key to access the API')),
        ListFieldSet('key', suppress_label=True, legend=N_('API Key:'), css_classes=['details_fieldset'], children=[
            TextField('api_secret_key', label_text=N_('Access Key')),
        ]),
        ListFieldSet('prefs', suppress_label=True, legend=N_('API Settings:'), css_classes=['details_fieldset'], children=[
            TextField('api_media_max_results', label_text=N_('Max media results')),
            TextField('api_tree_max_depth', label_text=N_('Max tree depth')),
        ]),
        SubmitButton('save', default='Save', css_classes=['btn', 'btn-save', 'blue', 'f-rgt']),
    ]

class AppearanceForm(ListForm):
    template = 'admin/box-form.html'
    id = 'settings-form'
    css_class = 'form'
    submit_text = None
    
    event = events.Admin.Settings.AppearanceForm
    
    fields = [
        ListFieldSet('general', suppress_label=True, legend=N_('General'),
            css_classes=['details_fieldset'],
            children=[
                FileField('appearance_logo', label_text=N_('Logo'),
                    validator=FieldStorageUploadConverter(not_empty=False,
                        label_text=N_('Upload Logo')),
                    css_classes=[],
                    default=lambda: request.settings.get('appearance_logo', \
                                                             'logo.png'),
                    template='./admin/settings/appearance_input_field.html'),
                FileField('appearance_background_image', label_text=N_('Background Image'),
                    validator=FieldStorageUploadConverter(not_empty=False,
                        label_text=N_('Upload Background')),
                    css_classes=[],
                    default=lambda: request.settings.get('appearance_background_image', \
                                                             'bg_image.png'),
                    template='./admin/settings/appearance_input_field.html'),
                TextField('appearance_background_color', maxlength=255,
                    label_text=N_('Background color'),
                    validator=Regex(hex_validation_regex, strip=True)),
                TextField('appearance_link_color', maxlength=255,
                    label_text=N_('Link color'),
                    validator=Regex(hex_validation_regex, strip=True)),
                TextField('appearance_visited_link_color', maxlength=255,
                    label_text=N_('Visited Link color'),
                    validator=Regex(hex_validation_regex, strip=True)),
                TextField('appearance_text_color', maxlength=255,
                    validator=Regex(hex_validation_regex, strip=True),
                    label_text=N_('Text color')),
                TextField('appearance_heading_color', maxlength=255,
                    label_text=N_('Heading color'),
                    validator=Regex(hex_validation_regex, strip=True)),
                SingleSelectField('appearance_navigation_bar_color',
                    label_text=N_('Color Scheme'),
                    options=navbar_colors),
            ]
        ),
        ListFieldSet('options', suppress_label=True, legend=N_('Options'),
            css_classes=['details_fieldset'],
            children=[
                CheckBox('appearance_enable_cooliris',
                    css_classes=['checkbox-left'],
                    label_text=N_('Enable Cooliris on the Explore Page'),
                    help_text=N_('Cooliris support is deprecated and will be ' + \
                        'removed in the next major version of MediaDrop ' + \
                        'unless someone is interested in maintaining it.'),
                    validator=Bool(if_missing='')),
                CheckBox(u'appearance_display_login',
                    css_classes=['checkbox-left'],
                    label_text=N_('Display login link for all users'),
                    validator=Bool(if_missing='')),
                CheckBox('appearance_enable_featured_items',
                    label_text=N_('Enable Featured Items on the Explore Page'),
                    css_classes=['checkbox-left'],
                    validator=Bool(if_missing='')),
                CheckBox('appearance_enable_podcast_tab',
                    label_text=N_('Enable Podcast Tab'),
                    css_classes=['checkbox-left'],
                    validator=Bool(if_missing='')),
                CheckBox('appearance_enable_user_uploads',
                    label_text=N_('Enable User Uploads'),
                    css_classes=['checkbox-left'],
                    validator=Bool(if_missing='')),
                CheckBox('appearance_enable_widescreen_view',
                    label_text=N_('Enable widescreen media player by default'),
                    css_classes=['checkbox-left'],
                    validator=Bool(if_missing='')),
                CheckBox('appearance_display_logo',
                    label_text=N_('Display Logo'),
                    css_classes=['checkbox-left'],
                    validator=Bool(if_missing='')),
                CheckBox('appearance_display_background_image',
                    label_text=N_('Display Background Image'),
                    css_classes=['checkbox-left'],
                    validator=Bool(if_missing='')),
                CheckBox('appearance_display_mediadrop_footer',
                    label_text=N_('Display MediaDrop Footer'),
                    css_classes=['checkbox-left'],
                    validator=Bool(if_missing='')),
                CheckBox('appearance_display_mediadrop_credits',
                    label_text=N_('Display MediaDrop Credits in Footer'),
                    css_classes=['checkbox-left'],
                    validator=Bool(if_missing='')),
            ],
            template='./admin/settings/appearance_list_fieldset.html',
        ),
        ListFieldSet('player', suppress_label=True, legend=N_('Player Menu Options'),
            css_classes=['details_fieldset'],
            children=[
                CheckBox('appearance_show_download',
                    css_classes=['checkbox-left'],
                    label_text=N_('Enable Download button on player menu bar.'),
                    validator=Bool(if_missing='')),
                CheckBox('appearance_show_share',
                    css_classes=['checkbox-left'],
                    label_text=N_('Enable Share button on player menu bar.'),
                    validator=Bool(if_missing='')),
                CheckBox('appearance_show_embed',
                    css_classes=['checkbox-left'],
                    label_text=N_('Enable Embed button on player menu bar.'),
                    validator=Bool(if_missing='')),
                CheckBox('appearance_show_widescreen',
                    css_classes=['checkbox-left'],
                    label_text=N_('Enable Widescreen toggle button on player menu bar.'),
                    validator=Bool(if_missing='')),
                CheckBox('appearance_show_popout',
                    css_classes=['checkbox-left'],
                    label_text=N_('Enable Popout button on player menu bar.'),
                    validator=Bool(if_missing='')),
                CheckBox('appearance_show_like',
                    css_classes=['checkbox-left'],
                    label_text=N_('Enable Like button on player menu bar.'),
                    validator=Bool(if_missing='')),
                CheckBox('appearance_show_dislike',
                    css_classes=['checkbox-left'],
                    label_text=N_('Enable Dislike button on player menu bar.'),
                    validator=Bool(if_missing='')),
            ],
            template='./admin/settings/appearance_list_fieldset.html',
        ),
        ListFieldSet('advanced', suppress_label=True, legend=N_('Advanced'),
            css_classes=['details_fieldset'],
            children=[
                TextArea('appearance_custom_css',
                    label_text=N_('Custom CSS'),
                    attrs=dict(rows=15, cols=25)),
                TextArea('appearance_custom_header_html',
                    label_text=N_('Custom Header HTML'),
                    attrs=dict(rows=15, cols=25)),
                TextArea('appearance_custom_footer_html',
                    label_text=N_('Custom Footer HTML'),
                    attrs=dict(rows=15, cols=25)),
                TextArea('appearance_custom_head_tags',
                    label_text=N_('Custom <head> Tags'),
                    help_text=N_('These HTML tags are inserted into the HTML '
                        '<head> section. Bad input can cause ugly rendering of '
                        'your site. You can always restore your page by '
                        'the box above.'),
                    attrs=dict(rows=15, cols=25)),
            ],
        ),
        SubmitButton('save', default=N_('Save'), css_classes=['btn', 'btn-save', 'blue', 'f-rgt']),
        SubmitButton('reset', default=N_('Reset to Defaults'),
            css_classes=['btn', 'btn-cancel', 'reset-confirm']),
    ]

class AdvertisingForm(ListForm):
    template = 'admin/box-form.html'
    id = 'settings-form'
    css_class = 'form'
    submit_text = None
    
    event = events.Admin.Settings.AdvertisingForm
    
    fields = [
        ListFieldSet('advanced', suppress_label=True, legend='',
            css_classes=['details_fieldset'],
            children=[
                TextArea('advertising_banner_html',
                    label_text=N_('Banner HTML'),
                    attrs=dict(rows=15, cols=25)),
                TextArea('advertising_sidebar_html',
                    label_text=N_('Sidebar HTML'),
                    attrs=dict(rows=15, cols=25)),
            ],
        ),
        SubmitButton('save', default=N_('Save'), css_classes=['btn', 'btn-save', 'blue', 'f-rgt']),
    ]



########NEW FILE########
__FILENAME__ = ftp
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code contained in this file is licensed under the GPLv3 or
# (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.

from formencode.validators import Int

from mediadrop.forms import ListFieldSet, TextField
from mediadrop.forms.admin.storage import StorageForm
from mediadrop.lib.i18n import N_
from mediadrop.lib.storage.ftp import (FTP_SERVER,
    FTP_USERNAME, FTP_PASSWORD,
    FTP_UPLOAD_DIR, FTP_MAX_INTEGRITY_RETRIES,
    HTTP_DOWNLOAD_URI, RTMP_SERVER_URI)
from mediadrop.plugin import events

class FTPStorageForm(StorageForm):
    event = events.Admin.Storage.FTPStorageForm

    fields = StorageForm.fields + [
        ListFieldSet('ftp',
            suppress_label=True,
            legend=N_('FTP Server Details:'),
            children=[
                TextField('server', label_text=N_('Server Hostname')),
                TextField('user', label_text=N_('Username')),
                TextField('password', label_text=N_('Password')),
                TextField('upload_dir', label_text=N_('Subdirectory on server to upload to')),
                TextField('upload_integrity_retries', label_text=N_('How many times should MediaDrop try to verify the FTP upload before declaring it a failure?'), validator=Int()),
                TextField('http_download_uri', label_text=N_('HTTP URL to access remotely stored files')),
                TextField('rtmp_server_uri', label_text=N_('RTMP Server URL to stream remotely stored files (Optional)')),
            ]
        ),
    ] + StorageForm.buttons

    def display(self, value, engine, **kwargs):
        """Display the form with default values from the given StorageEngine.

        If the value dict is not fully populated, populate any missing entries
        with the values from the given StorageEngine's
        :attr:`_data <mediadrop.lib.storage.StorageEngine._data>` dict.

        :param value: A (sparse) dict of values to populate the form with.
        :type value: dict
        :param engine: An instance of the storage engine implementation.
        :type engine: :class:`mediadrop.lib.storage.StorageEngine` subclass

        """
        data = engine._data
        ftp = value.setdefault('ftp', {})
        ftp.setdefault('server', data.get(FTP_SERVER, None))
        ftp.setdefault('user', data.get(FTP_USERNAME, None))
        ftp.setdefault('password', data.get(FTP_PASSWORD, None))
        ftp.setdefault('upload_dir', data.get(FTP_UPLOAD_DIR, None))
        ftp.setdefault('upload_integrity_retries', data.get(FTP_MAX_INTEGRITY_RETRIES, None))
        ftp.setdefault('http_download_uri', data.get(HTTP_DOWNLOAD_URI, None))
        ftp.setdefault('rtmp_server_uri', data.get(RTMP_SERVER_URI, None))
        return StorageForm.display(self, value, engine, **kwargs)

    def save_engine_params(self, engine, **kwargs):
        """Map validated field values to engine data.

        Since form widgets may be nested or named differently than the keys
        in the :attr:`mediadrop.lib.storage.StorageEngine._data` dict, it is
        necessary to manually map field values to the data dictionary.

        :type engine: :class:`mediadrop.lib.storage.StorageEngine` subclass
        :param engine: An instance of the storage engine implementation.
        :param \*\*kwargs: Validated and filtered form values.
        :raises formencode.Invalid: If some post-validation error is detected
            in the user input. This will trigger the same error handling
            behaviour as with the @validate decorator.

        """
        StorageForm.save_engine_params(self, engine, **kwargs)
        ftp = kwargs['ftp']
        engine._data[FTP_SERVER] = ftp['server']
        engine._data[FTP_USERNAME] = ftp['user']
        engine._data[FTP_PASSWORD] = ftp['password']
        engine._data[FTP_UPLOAD_DIR] = ftp['upload_dir']
        engine._data[FTP_MAX_INTEGRITY_RETRIES] = ftp['upload_integrity_retries']
        engine._data[HTTP_DOWNLOAD_URI] = ftp['http_download_uri']
        engine._data[RTMP_SERVER_URI] = ftp['rtmp_server_uri']

########NEW FILE########
__FILENAME__ = localfiles
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code contained in this file is licensed under the GPLv3 or
# (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.

from mediadrop.forms import ListFieldSet, TextField
from mediadrop.forms.admin.storage import StorageForm
from mediadrop.lib.i18n import N_
from mediadrop.plugin import events

class LocalFileStorageForm(StorageForm):
    event = events.Admin.Storage.LocalFileStorageForm

    fields = StorageForm.fields + [
        ListFieldSet('specifics',
            suppress_label=True,
            legend=N_('Options specific to Local File Storage:'),
            children=[
                TextField('path',
                    label_text=N_('Path to store files under'),
                    help_text=N_('Defaults to the "data_dir" from your INI file.'),
                ),
                TextField('rtmp_server_uri',
                    label_text=N_('RTMP Server URL'),
                    help_text=N_('Files must be accessible under the same name as they are stored with locally.'),
                ),
            ],
        )
    ] + StorageForm.buttons


    def display(self, value, engine, **kwargs):
        """Display the form with default values from the given StorageEngine.

        If the value dict is not fully populated, populate any missing entries
        with the values from the given StorageEngine's
        :attr:`_data <mediadrop.lib.storage.StorageEngine._data>` dict.

        :param value: A (sparse) dict of values to populate the form with.
        :type value: dict
        :param engine: An instance of the storage engine implementation.
        :type engine: :class:`mediadrop.lib.storage.StorageEngine` subclass

        """
        specifics = value.setdefault('specifics', {})
        specifics.setdefault('path', engine._data.get('path', None))
        specifics.setdefault('rtmp_server_uri', engine._data.get('rtmp_server_uri', None))
        return StorageForm.display(self, value, engine, **kwargs)

    def save_engine_params(self, engine, **kwargs):
        """Map validated field values to engine data.

        Since form widgets may be nested or named differently than the keys
        in the :attr:`mediadrop.lib.storage.StorageEngine._data` dict, it is
        necessary to manually map field values to the data dictionary.

        :type engine: :class:`mediadrop.lib.storage.StorageEngine` subclass
        :param engine: An instance of the storage engine implementation.
        :param \*\*kwargs: Validated and filtered form values.
        :raises formencode.Invalid: If some post-validation error is detected
            in the user input. This will trigger the same error handling
            behaviour as with the @validate decorator.

        """
        StorageForm.save_engine_params(self, engine, **kwargs)
        specifics = kwargs['specifics']
        engine._data['path'] = specifics['path'] or None
        engine._data['rtmp_server_uri'] = specifics['rtmp_server_uri'] or None

########NEW FILE########
__FILENAME__ = remoteurls
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code contained in this file is licensed under the GPLv3 or
# (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.

from formencode import Invalid
from formencode.validators import FancyValidator
from tw.api import JSSource
from tw.forms import FormFieldRepeater

from mediadrop.forms import ListFieldSet, TextField
from mediadrop.forms.admin.storage import StorageForm
from mediadrop.lib.i18n import N_, _
from mediadrop.plugin import events


# Sure this could be abstracted into something more reusable.
# But at this point there's no need. Refactor later if needed.
class TranslateableRTMPServerJSSource(JSSource):
    def render(self, *args, **kwargs):
        src = JSSource.render(self, *args, **kwargs)
        return src % {'add_url': _('Add another URL')}

rtmp_server_js = TranslateableRTMPServerJSSource("""
    window.addEvent('domready', function(){
        var fields = $('rtmp').getElement('li');
        var addButton = new Element('span', {
            'class': 'add-another clickable',
            'text': '%(add_url)s'
        });
        addButton.inject(fields, 'bottom').addEvent('click', function(){
            var lastInput = addButton.getPrevious();
            var fullname = lastInput.get('name');
            var sepindex = fullname.indexOf('-') + 1;
            var name = fullname.substr(0, sepindex);
            var nextNum = fullname.substr(sepindex).toInt() + 1;
            var el = new Element('input', {
                'type': 'text',
                'name': name + nextNum,
                'class': 'textfield repeatedtextfield rtmp-server-uri'
            });
            el.inject(lastInput, 'after').focus();
        });
    });
""", location='headbottom')

class RTMPURLValidator(FancyValidator):
    def _to_python(self, value, state=None):
        if value.startswith('rtmp://'):
            return value.rstrip('/')
        raise Invalid(_('RTMP server URLs must begin with rtmp://'),
                      value, state)

class RemoteURLStorageForm(StorageForm):
    event = events.Admin.Storage.RemoteURLStorageForm

    fields = StorageForm.fields + [
        ListFieldSet('rtmp',
            legend=N_('RTMP Servers:'),
            suppress_label=True,
            children=[
                # FIXME: Display errors from the RTMPURLValidator
                FormFieldRepeater('known_servers',
                    widget=TextField(
                        css_classes=['textfield rtmp-server-uri'],
                        validator=RTMPURLValidator(),
                    ),
                    suppress_label=True,
                    repetitions=1,
                ),
            ],
        )
    ] + StorageForm.buttons

    javascript = [rtmp_server_js]

    def display(self, value, engine, **kwargs):
        """Display the form with default values from the given StorageEngine.

        If the value dict is not fully populated, populate any missing entries
        with the values from the given StorageEngine's
        :attr:`_data <mediadrop.lib.storage.StorageEngine._data>` dict.

        :param value: A (sparse) dict of values to populate the form with.
        :type value: dict
        :param engine: An instance of the storage engine implementation.
        :type engine: :class:`mediadrop.lib.storage.StorageEngine` subclass

        """
        rtmp = value.setdefault('rtmp', {})
        rtmp.setdefault('known_servers', engine._data.get('rtmp_server_uris', ()))
        return StorageForm.display(self, value, engine, **kwargs)

    def save_engine_params(self, engine, **kwargs):
        """Map validated field values to engine data.

        Since form widgets may be nested or named differently than the keys
        in the :attr:`mediadrop.lib.storage.StorageEngine._data` dict, it is
        necessary to manually map field values to the data dictionary.

        :type engine: :class:`mediadrop.lib.storage.StorageEngine` subclass
        :param engine: An instance of the storage engine implementation.
        :param \*\*kwargs: Validated and filtered form values.
        :raises formencode.Invalid: If some post-validation error is detected
            in the user input. This will trigger the same error handling
            behaviour as with the @validate decorator.

        """
        StorageForm.save_engine_params(self, engine, **kwargs)
        rtmp = kwargs.get('rtmp', {})
        rtmp_servers = rtmp.get('known_servers', ())
        engine._data['rtmp_server_uris'] = [x for x in rtmp_servers if x]

########NEW FILE########
__FILENAME__ = tags
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code contained in this file is licensed under the GPLv3 or
# (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.

import re

from tw.forms import HiddenField
from tw.forms.validators import FancyValidator, NotEmpty

from mediadrop.forms import Form, ListForm, SubmitButton, ResetButton, TextField
from mediadrop.lib.i18n import N_
from mediadrop.plugin import events

excess_whitespace = re.compile('\s\s+', re.M)

class TagNameValidator(FancyValidator):
    def _to_python(self, value, state=None):
        value = value.strip()
        value = excess_whitespace.sub(' ', value)
        if super(TagNameValidator, self)._to_python:
            value = super(TagNameValidator, self)._to_python(value, state)
        return value

class TagForm(ListForm):
    template = 'admin/tags_and_categories_form.html'
    id = None
    css_classes = ['form', 'tag-form']
    submit_text = None
    
    event = events.Admin.TagForm

    # required to support multiple named buttons to differentiate between Save & Delete?
    _name = 'vf'

    fields = [
        TextField('name', label_text=N_('Name'), css_classes=['tag-name'], validator=TagNameValidator(not_empty=True)),
        TextField('slug', label_text=N_('Permalink'), css_classes=['tag-slug'], validator=NotEmpty),
        ResetButton('cancel', default=N_('Cancel'), css_classes=['btn', 'f-lft', 'btn-cancel']),
        SubmitButton('save', default=N_('Save'), css_classes=['f-rgt', 'btn', 'blue', 'btn-save']),
    ]

class TagRowForm(Form):
    template = 'admin/tags/row-form.html'
    id = None
    submit_text = None
    params = ['tag']
    
    event = events.Admin.TagRowForm

    fields = [
        HiddenField('name'),
        HiddenField('slug'),
        SubmitButton('delete', default=N_('Delete'), css_classes=['btn', 'table-row', 'delete', 'btn-inline-delete']),
    ]

########NEW FILE########
__FILENAME__ = users
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code contained in this file is licensed under the GPLv3 or
# (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.

from pylons import request
from tw.forms import CheckBoxList, PasswordField
from tw.forms.validators import All, FancyValidator, FieldsMatch, Invalid, NotEmpty, PlainText, Schema

from mediadrop.forms import ListFieldSet, ListForm, SubmitButton, TextField, email_validator
from mediadrop.lib.i18n import N_, _
from mediadrop.model import DBSession
from mediadrop.model.auth import Group, User
from mediadrop.plugin import events


class UniqueUsername(FancyValidator):
    def _to_python(self, value, state):
        id = request.environ['pylons.routes_dict']['id']

        query = DBSession.query(User).filter_by(user_name=value)
        if id != 'new':
            query = query.filter(User.id != id)

        if query.count() != 0:
            raise Invalid(_('User name already exists'), value, state)
        return value

class UserForm(ListForm):
    template = 'admin/box-form.html'
    id = 'user-form'
    css_class = 'form'
    submit_text = None
    show_children_errors = True
    _name = 'user-form' # TODO: Figure out why this is required??
    
    event = events.Admin.UserForm
    
    fields = [
        TextField('display_name', label_text=N_('Display Name'), validator=TextField.validator(not_empty=True), maxlength=255),
        TextField('email_address', label_text=N_('Email Address'), validator=email_validator(not_empty=True), maxlength=255),
        ListFieldSet('login_details', suppress_label=True, legend=N_('Login Details:'),
            css_classes=['details_fieldset'],
            validator = Schema(chained_validators=[
                FieldsMatch('password', 'confirm_password',
                messages={'invalidNoMatch': N_("Passwords do not match"),})]
            ),
            children=[
                CheckBoxList('groups', label_text=N_('Groups'), 
                    options=lambda: Group.custom_groups(Group.group_id, Group.display_name).all()),
                TextField('user_name', label_text=N_('Username'), maxlength=16, validator=All(PlainText(), UniqueUsername(not_empty=True))),
                PasswordField('password', label_text=N_('Password'), validators=NotEmpty, maxlength=80, attrs={'autocomplete': 'off'}),
                PasswordField('confirm_password', label_text=N_('Confirm password'), validators=NotEmpty, maxlength=80, attrs={'autocomplete': 'off'}),
            ]
        ),
        SubmitButton('save', default=N_('Save'), named_button=True, css_classes=['btn', 'btn-save', 'blue', 'f-rgt']),
        SubmitButton('delete', default=N_('Delete'), named_button=True, css_classes=['btn', 'btn-delete']),
    ]

########NEW FILE########
__FILENAME__ = comments
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code contained in this file is licensed under the GPLv3 or
# (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.

from formencode import Schema

from mediadrop.forms import TextField, XHTMLValidator, email_validator
from mediadrop.lib.i18n import N_

class PostCommentSchema(Schema):
    name = TextField.validator(not_empty=True, maxlength=50,
        messages={'empty': N_('Please enter your name!')})
    email = email_validator()
    body = XHTMLValidator(not_empty=True)

########NEW FILE########
__FILENAME__ = login
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code contained in this file is licensed under the GPLv3 or
# (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.

from tw.forms import PasswordField

from mediadrop.forms import ListForm, TextField, SubmitButton

from mediadrop.lib.i18n import N_
from mediadrop.plugin import events

__all__ = ['LoginForm']

class LoginForm(ListForm):
    template = 'forms/box_form.html'
    method = 'POST'
    id = 'login-form'
    css_class = 'form clearfix'
    submit_text = None
    # For login failures we display only a generic (bad username or password) 
    # error message which is not related to any particular field. 
    # However I'd like to mark the input widgets as faulty without displaying 
    # the dummy errors (injected by LoginController programmatically as this 
    # form is not used for credential validation) so this will prevent the error
    # text from being displayed. However the actual input fields will be marked
    # with css classes anyway.
    show_children_errors = False

    fields = [
        TextField('login', label_text=N_('Username'), 
            # 'autofocus' is actually not XHTML-compliant
            attrs={'autofocus': True}),
        PasswordField('password', label_text=N_('Password')),
        
        SubmitButton('login_button', default=N_('Login'), 
            css_classes=['mcore-btn', 'btn-submit', 'f-rgt'])
    ]

    def post_init(self, *args, **kwargs):
        events.LoginForm(self)



########NEW FILE########
__FILENAME__ = uploader
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code contained in this file is licensed under the GPLv3 or
# (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.

from tw.api import WidgetsList
from tw.forms.validators import FieldStorageUploadConverter

from mediadrop.lib.i18n import N_
from mediadrop.forms import ListForm, TextField, XHTMLTextArea, FileField, SubmitButton, email_validator
from mediadrop.plugin import events

validators = dict(
    description = XHTMLTextArea.validator(
        messages = {'empty': N_('At least give it a short description...')},
        not_empty = True,
    ),
    name = TextField.validator(
        messages = {'empty': N_("You've gotta have a name!")},
        not_empty = True,
    ),
    title = TextField.validator(
        messages = {'empty': N_("You've gotta have a title!")},
        not_empty = True,
    ),
    url = TextField.validator(
        if_missing = None,
    ),
)

class UploadForm(ListForm):
    template = 'upload/form.html'
    id = 'upload-form'
    css_class = 'form'
    show_children_errors = False
    params = ['async_action']
    
    events = events.UploadForm
    
    class fields(WidgetsList):
        name = TextField(validator=validators['name'], label_text=N_('Your Name:'), maxlength=50)
        email = TextField(validator=email_validator(not_empty=True), label_text=N_('Your Email:'), help_text=N_('(will never be published)'), maxlength=255)
        title = TextField(validator=validators['title'], label_text=N_('Title:'), maxlength=255)
        description = XHTMLTextArea(validator=validators['description'], label_text=N_('Description:'), attrs=dict(rows=5, cols=25))
        url = TextField(validator=validators['url'], label_text=N_('Add a YouTube, Vimeo or Amazon S3 link:'), maxlength=255)
        file = FileField(validator=FieldStorageUploadConverter(if_missing=None, messages={'empty':N_('Oops! You forgot to enter a file.')}), label_text=N_('OR:'))
        submit = SubmitButton(default=N_('Submit'), css_classes=['mcore-btn', 'btn-submit'])

########NEW FILE########
__FILENAME__ = app_globals
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code contained in this file is licensed under the GPLv3 or
# (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.
"""The application's Globals object"""

from beaker.cache import CacheManager
from beaker.util import parse_cache_config_options

class Globals(object):
    """Globals acts as a container for objects available throughout the
    life of the application

    """
    def __init__(self, config):
        """One instance of Globals is created during application
        initialization and is available during requests via the
        'app_globals' variable

        """
        self.cache = cache = CacheManager(**parse_cache_config_options(config))
        self.settings_cache = cache.get_cache('app_settings',
                                              expire=3600,
                                              type='memory')

        # We'll store the primary translator here for sharing between requests
        self.primary_language = None
        self.primary_translator = None

    @property
    def settings(self):
        def fetch_settings():
            from mediadrop.model import DBSession, Setting
            settings_dict = dict(DBSession.query(Setting.key, Setting.value))
            return settings_dict
        return self.settings_cache.get(createfunc=fetch_settings, key=None)

########NEW FILE########
__FILENAME__ = attribute_dict
# -*- coding: UTF-8 -*-

# License: Public Domain
# Authors: Felix Schwarz <felix.schwarz@oss.schwarz.eu>
# 
# Version 1.0

# 1.0 (06.02.2010)
#   - initial release

__all__ = ['AttrDict']


class AttrDict(dict):
    def __getattr__(self, name):
        if name not in self:
            raise AttributeError("'%s' object has no attribute '%s'" % (self.__class__.__name__, name))
        return self[name]



########NEW FILE########
__FILENAME__ = api
# -*- coding: utf-8 -*-
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code in this file is dual licensed under the MIT license or
# the GPLv3 or (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.

__all__ = ['Resource', 'InsufficientPermissionsError', 'IPermissionPolicy', 
    'UserPermissions', 'PermissionSystem']


class Resource(object):
    def __init__(self, realm, id, **kwargs):
        self.realm = realm
        self.id = id
        self.data = kwargs


class IPermissionPolicy(object):
    permissions = ()
    
    def permits(self, permission, user_permissions, resource):
        return None
    
    def can_apply_access_restrictions_to_query(self, query, permission):
        return False
    
    def access_condition_for_query(self, query, permission, perm):
        return None


class InsufficientPermissionsError(Exception):
    def __init__(self, permission, resource=None):
        self.permission = permission
        self.resource = resource


class UserPermissions(object):
    
    def __init__(self, user, permission_system, groups=None):
        self.user = user
        if groups is None:
            groups = user.groups
        self.groups = set(groups)
        self.permission_system = permission_system
        self.data = {}
    
    def assert_permission(self, permission, resource=None):
        self.permission_system.assert_permission(permission, self, resource)
    
    def contains_permission(self, permission, resource=None):
        return self.permission_system.has_permission(permission, self, resource)



class PermissionSystem(object):
    def __init__(self, policies):
        self.policies = tuple(policies)
    
    def policies_for_permission(self, permission):
        applicable_policies = []
        for policy in self.policies:
            if permission in policy.permissions:
                applicable_policies.append(policy)
        return applicable_policies
    
    def assert_permission(self, permission, user_permissions, resource=None):
        decision = self.has_permission(permission, user_permissions, resource)
        if decision == False:
            self.raise_error(permission, resource)
    
    def has_permission(self, permission, user_permissions, resource=None):
        for policy in self.policies_for_permission(permission):
            decision = policy.permits(permission, user_permissions, resource)
            if decision in (True, False):
                return decision
        return False
    
    def raise_error(self, permission, resource):
        raise InsufficientPermissionsError(permission, resource)


########NEW FILE########
__FILENAME__ = group_based_policy
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code contained in this file is licensed under the GPLv3 or
# (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.

from mediadrop.lib.auth.api import IPermissionPolicy
from mediadrop.lib.auth.permission_system import PermissionPolicies
from mediadrop.model import DBSession, Permission


__all__ = ['GroupBasedPermissionsPolicy']

class GroupBasedPermissionsPolicy(IPermissionPolicy):
    @property
    def permissions(self):
        db_permissions = DBSession.query(Permission).all()
        return tuple([permission.permission_name for permission in db_permissions])
    
    def _permissions(self, perm):
        if 'permissions' not in perm.data:
            if perm.groups is None:
                return ()
            permissions = []
            for group in perm.groups:
                permissions.extend([p.permission_name for p in group.permissions])
            perm.data['permissions'] = permissions
        return perm.data['permissions']
    
    def permits(self, permission, perm, resource):
        if permission in self._permissions(perm):
            return True
        # there may be other policies still which can permit the access...
        return None
    
    def can_apply_access_restrictions_to_query(self, query, permission):
        return True
    
    def access_condition_for_query(self, query, permission, perm):
        if perm.contains_permission(permission):
            return True
        return None

PermissionPolicies.register(GroupBasedPermissionsPolicy)


########NEW FILE########
__FILENAME__ = middleware
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code contained in this file is licensed under the GPLv3 or
# (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.

import re

from repoze.who.classifiers import default_challenge_decider, default_request_classifier
from repoze.who.middleware import PluggableAuthenticationMiddleware
from repoze.who.plugins.auth_tkt import AuthTktCookiePlugin
from repoze.who.plugins.friendlyform import FriendlyFormPlugin
from repoze.who.plugins.sa import SQLAlchemyAuthenticatorPlugin
from webob.request import Request

from mediadrop.config.routing import login_form_url, login_handler_url, \
    logout_handler_url, post_login_url, post_logout_url

from mediadrop.lib.auth.permission_system import MediaDropPermissionSystem



__all__ = ['add_auth', 'classifier_for_flash_uploads']

class MediaDropAuthenticatorPlugin(SQLAlchemyAuthenticatorPlugin):
    def authenticate(self, environ, identity):
        login = super(MediaDropAuthenticatorPlugin, self).authenticate(environ, identity)
        if login is None:
            return None
        user = self.get_user(login)
        # The return value of this method is used to identify the user later on.
        # As the username can be changed, that's not really secure and may 
        # lead to confusion (user is logged out unexpectedly, best case) or 
        # account take-over (impersonation, worst case).
        # The user ID is considered constant and likely the best choice here.
        return user.id
    
    @classmethod
    def by_attribute(cls, attribute_name=None):
        from mediadrop.model import DBSession, User
        authenticator = MediaDropAuthenticatorPlugin(User, DBSession)
        if attribute_name:
            authenticator.translations['user_name'] = attribute_name
        return authenticator


class MediaDropCookiePlugin(AuthTktCookiePlugin):
    def __init__(self, secret, **kwargs):
        if kwargs.get('userid_checker') is not None:
            raise TypeError("__init__() got an unexpected keyword argument 'userid_checker'")
        kwargs['userid_checker'] = self._check_userid
        super(MediaDropCookiePlugin, self).__init__(secret, **kwargs)
    
    def _check_userid(self, user_id):
        # only accept numeric user_ids. In MediaCore < 0.10 the cookie contained
        # the user name, so invalidate all these old sessions.
        if re.search('[^0-9]', user_id):
            return False
        return True


def who_args(config):
    auth_by_username = MediaDropAuthenticatorPlugin.by_attribute('user_name')
    
    form = FriendlyFormPlugin(
        login_form_url,
        login_handler_url,
        post_login_url,
        logout_handler_url,
        post_logout_url,
        rememberer_name='cookie',
        charset='utf-8',
    )
    cookie_secret = config['sa_auth.cookie_secret']
    seconds_30_days = 30*24*60*60 # session expires after 30 days
    cookie = MediaDropCookiePlugin(cookie_secret, 
        cookie_name='authtkt', 
        timeout=seconds_30_days, # session expires after 30 days
        reissue_time=seconds_30_days/2, # reissue cookie after 15 days
    )
    
    who_args = {
        'authenticators': [
            ('auth_by_username', auth_by_username)
        ],
        'challenge_decider': default_challenge_decider,
        'challengers': [('form', form)],
        'classifier': classifier_for_flash_uploads,
        'identifiers': [('main_identifier', form), ('cookie', cookie)],
        'mdproviders': [],
    }
    return who_args


def authentication_middleware(app, config):
    return PluggableAuthenticationMiddleware(app, **who_args(config))


class AuthorizationMiddleware(object):
    def __init__(self, app, config):
        self.app = app
        self.config = config
    
    def __call__(self, environ, start_response):
        environ['mediadrop.perm'] = \
            MediaDropPermissionSystem.permissions_for_request(environ, self.config)
        return self.app(environ, start_response)


def add_auth(app, config):
    authorization_app = AuthorizationMiddleware(app, config)
    return authentication_middleware(authorization_app, config)


def classifier_for_flash_uploads(environ):
    """Normally classifies the request as browser, dav or xmlpost.

    When the Flash uploader is sending a file, it appends the authtkt session
    ID to the POST data so we spoof the cookie header so that the auth code
    will think this was a normal request. In the process, we overwrite any
    pseudo-cookie data that is sent by Flash.

    TODO: Currently overwrites the HTTP_COOKIE, should ideally append.
    """
    classification = default_request_classifier(environ)
    if classification == 'browser' \
    and environ['REQUEST_METHOD'] == 'POST' \
    and 'Flash' in environ.get('HTTP_USER_AGENT', ''):
        session_key = environ['repoze.who.plugins']['cookie'].cookie_name
        # Construct a temporary request object since this is called before
        # pylons.request is populated. Re-instantiation later comes cheap.
        request = Request(environ)
        try:
            session_id = str(request.POST[session_key])
            environ['HTTP_COOKIE'] = '%s=%s' % (session_key, session_id)
        except (KeyError, UnicodeEncodeError):
            pass
    return classification



########NEW FILE########
__FILENAME__ = permission_system
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code contained in this file is licensed under the GPLv3 or
# (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.

import re

from pylons.controllers.util import abort
from sqlalchemy import or_

from mediadrop.lib.auth.api import PermissionSystem, UserPermissions
from mediadrop.lib.auth.query_result_proxy import QueryResultProxy, StaticQuery
from mediadrop.model import DBSession, Group, User
from mediadrop.plugin.abc import AbstractClass, abstractmethod


__all__ = ['MediaDropPermissionSystem', 'PermissionPolicies']

class PermissionPolicies(AbstractClass):
    @abstractmethod
    def permits(self, permission, perm, resource):
        pass
    
    @abstractmethod
    def can_apply_access_restrictions_to_query(self, query, permission):
        pass
    
    @abstractmethod
    def access_condition_for_query(self, query, permission, perm):
        pass
    
    @classmethod
    def configured_policies(cls, config):
        def policy_from_name(policy_name):
            for policy in cls:
                if policy.__name__ == policy_name:
                    return policy()
            raise AssertionError('No such policy: %s' % repr(policy_name))
        
        policy_names = re.split('\s*,\s*', config.get('permission_policies', ''))
        if policy_names == ['']:
            policy_names = ['GroupBasedPermissionsPolicy']
        return map(policy_from_name, policy_names)


class MediaDropPermissionSystem(PermissionSystem):
    def __init__(self, config):
        policies = PermissionPolicies.configured_policies(config)
        super(MediaDropPermissionSystem, self).__init__(policies)
    
    @classmethod
    def permissions_for_request(cls, environ, config):
        identity = environ.get('repoze.who.identity', {})
        user_id = identity.get('repoze.who.userid')
        user = None
        if user_id is not None:
            user = DBSession.query(User).filter(User.id==user_id).first()
        return cls.permissions_for_user(user, config)
    
    @classmethod
    def permissions_for_user(cls, user, config):
        if user is None:
            user = User()
            user.display_name = u'Anonymous User'
            user.user_name = u'anonymous'
            user.email_address = 'invalid@mediadrop.example'
            anonymous_group = Group.by_name(u'anonymous')
            groups = filter(None, [anonymous_group])
        else:
            meta_groups = Group.query.filter(Group.group_name.in_([u'anonymous', u'authenticated']))
            groups = list(user.groups) + list(meta_groups)
        return UserPermissions(user, cls(config), groups=groups)
    
    def filter_restricted_items(self, query, permission_name, perm):
        if self._can_apply_access_restrictions_to_query(query, permission_name):
            return self._apply_access_restrictions_to_query(query, permission_name, perm)
        
        can_access_item = \
            lambda item: perm.contains_permission(permission_name, item.resource)
        return QueryResultProxy(query, filter_=can_access_item)
    
    def raise_error(self, permission, resource):
        abort(404)
    # --- private API ---------------------------------------------------------
    
    def _can_apply_access_restrictions_to_query(self, query, permission_name):
        for policy in self.policies_for_permission(permission_name):
            if not policy.can_apply_access_restrictions_to_query(query, permission_name):
                return False
        return True
    
    def _apply_access_restrictions_to_query(self, query, permission_name, perm):
        conditions = []
        for policy in self.policies_for_permission(permission_name):
            result = policy.access_condition_for_query(query, permission_name, perm)
            if result == True:
                return QueryResultProxy(query)
            elif result == False:
                return StaticQuery([])
            elif result is None:
                continue
            
            condition = result
            if isinstance(result, tuple):
                condition, query = result
            conditions.append(condition)
        
        if len(conditions) == 0:
            # if there is no condition which can possibly allow the access, 
            # we should not return any items
            return StaticQuery([])
        restricted_query = query.distinct().filter(or_(*conditions))
        return QueryResultProxy(restricted_query)


########NEW FILE########
__FILENAME__ = pylons_glue
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code contained in this file is licensed under the GPLv3 or
# (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.

import new

from decorator import decorator
from pylons import request
from pylons.controllers.util import abort

__all__ = ['ControllerProtector', 'FunctionProtector', 'has_permission', 
    'Predicate']


class Predicate(object):
    def has_required_permission(self, environ):
        raise NotImplementedError()


class has_permission(Predicate):
    def __init__(self, permission_name):
        self.permission_name = permission_name
    
    def has_required_permission(self, request):
        environ = request.environ
        # potentially wrapping the BaseController which sets up request.perm,
        # therefore we have to get the perm object from the environ
        return environ['mediadrop.perm'].contains_permission(self.permission_name)


class FunctionProtector(object):
    def __init__(self, predicate):
        self.predicate = predicate
    
    def wrap(self, function):
        def _wrap(function_, *args, **kwargs):
            if self.predicate.has_required_permission(request):
                return function_(*args, **kwargs)
            is_user_authenticated = request.environ.get('repoze.who.identity')
            if is_user_authenticated:
                abort(403)
            abort(401)
        return decorator(_wrap, function)
    
    # using the FunctionProtector as a decorator (e.g. in the panda plugin)
    def __call__(self, action_):
        return self.wrap(action_)


class ControllerProtector(object):
    def __init__(self, predicate):
        self.predicate = predicate
    
    def __call__(self, instance):
        import inspect
        assert not inspect.isclass(instance)
        klass = instance.__class__
        before_method = self._wrap__before__(klass)
        instance.__before__ = new.instancemethod(before_method, instance, klass)
        return instance
    
    def _wrap__before__(self, klass):
        before = lambda *args, **kwargs: None
        before.__name__ = '__before__'
        if hasattr(klass, '__before__'):
            before = klass.__before__.im_func
        return FunctionProtector(self.predicate).wrap(before)



########NEW FILE########
__FILENAME__ = query_result_proxy
# -*- coding: utf-8 -*-
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code in this file is dual licensed under the MIT license or
# the GPLv3 or (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.


__all__ = ['QueryResultProxy', 'StaticQuery']

class QueryResultProxy(object):
    def __init__(self, query, start=0, filter_=None, default_fetch=10):
        self.query = query
        self._items_retrieved = start
        self._items_returned = 0
        self._limit = None
        self._filter = filter_
        self._default_fetch = default_fetch
        self._prefetched_items = []
    
    def fetch(self, n=1):
        assert n >= 1
        if self._limit is not None:
            if self._items_returned + n > self._limit:
                n = self._limit - self._items_returned
                if n < 1:
                    return []
        new_items = []
        if len(self._prefetched_items) > 0:
            new_items.extend(self._prefetched_items[:n])
            self._prefetched_items = self._prefetched_items[n:]
        # don't adapt number of items to fetch during the loops - otherwise we
        # might have to do a lot of queries to get the last missing items in a
        # situation where only few items from a big list are acceptable to the
        # filter
        n_ = n - len(new_items)
        while len(new_items) < n:
            number_of_items_to_fetch = max(n_+1, self._default_fetch)
            fetched_items = self._fetch(number_of_items_to_fetch)
            retrieved_items = filter(self._filter, fetched_items)
            new_items.extend(retrieved_items)
            if len(fetched_items) <= n_:
                # if there were only "n_" items left (though we requested 'n_+1'
                # we're done, we consumed all available items.
                break
        self._prefetched_items.extend(new_items[n:])
        
        items = new_items[:n]
        self._items_returned += len(items)
        return items
    
    def _fetch(self, n):
        fetched_items = self.query.offset(self._items_retrieved).limit(n).all()
        self._items_retrieved += len(fetched_items)
        return fetched_items
    
    def more_available(self):
        if len(self._prefetched_items) == 0:
            next_items = self.fetch(n=1)
            if len(next_items) > 0:
                # fetch will increase the number if items returned but we won't
                # return the actual item here.
                self._items_returned -= len(next_items)
                self._prefetched_items.insert(0, next_items[0])
        return len(self._prefetched_items) > 0
    
    def first(self):
        "Returns the next available item or None if there are no items anymore."
        item = self.fetch(1)
        if len(item) == 0:
            return None
        return item[0]
    
    # --- pagination support ---------------------------------------------------
    
    def __iter__(self):
        return self
    
    def next(self):
        items = self.fetch(n=1)
        if len(items) > 0:
            return items[0]
        raise StopIteration
    
    def _prefetch_all(self):
        # yes, that's very inefficient but works for now
        prefetched_items = []
        def _prefetch():
            next_items = self.fetch(n=1000)
            self._items_returned -= len(next_items)
            prefetched_items.extend(next_items)
            prefetched_items.extend(self._prefetched_items)
            self._prefetched_items = []
            return (len(next_items) == 1000)
        while _prefetch():
            pass
        self._prefetched_items = prefetched_items
    
    def __len__(self):
        if self.more_available():
            self._prefetch_all()
        return self._items_returned + len(self._prefetched_items)
    count = __len__
    
    def __getitem__(self, key):
        def is_slice(item):
            return hasattr(key, 'indices')
        
        if is_slice(key):
            start, stop, step = key.indices(len(self))
            # TODO: if start < self._items_returned
            index_start = start - self._items_returned
            index_stop = index_start + (stop - start)
            
            # TODO: support step
            return self._prefetched_items[index_start:index_stop]
        raise TypeError
    
    def limit(self, n):
        n = int(n)
        assert n >= 1
        self._limit = n
        return self
    
    def offset(self, n):
        n = int(n)
        assert n >= 0
        assert self._items_retrieved == 0
        assert self._items_returned == 0
        self._items_retrieved = n
        return self


class StaticQuery(object):
    def __init__(self, items):
        self._all_items = items
        self._items = None
        
        self._items_returned = 0
        self._offset = 0
        self._limit = None
    
    @property
    def items(self):
        if self._items is not None:
            return self._items[self._items_returned:]
        self._items = self._items_in_query()
        return self._items
    
    def _items_in_query(self):
        if self._limit is None:
            last_index = len(self._all_items)
        else:
            last_index = self._offset + self._limit
        return self._all_items[self._offset:last_index]
    
    # --- iteration -----------------------------------------------------------
    def __iter__(self):
        return self
    
    def next(self):
        if len(self.items) == 0:
            raise StopIteration
        first_item = self.items[0]
        self._items_returned += 1
        return first_item
    
    def __len__(self):
        return len(self._items_in_query())
    count = __len__
    
    def __getitem__(self, key):
        return self.items[key]
    
    # --- query methods -------------------------------------------------------
    def offset(self, n):
        assert self._items_returned == 0
        self._offset = n
        return self
    
    def limit(self, n):
        assert self._items_returned == 0
        self._limit = n
        return self
    
    def all(self):
        assert self._items_returned == 0
        items = self.items
        self._items_returned += len(items)
        return items
    
    def first(self):
        try:
            return self.next()
        except StopIteration:
            return None


########NEW FILE########
__FILENAME__ = filtering_restricted_items_test
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code contained in this file is licensed under the GPLv3 or
# (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.

from mediadrop.lib.auth.api import IPermissionPolicy, UserPermissions
from mediadrop.lib.auth.group_based_policy import GroupBasedPermissionsPolicy
from mediadrop.lib.auth.permission_system import MediaDropPermissionSystem, PermissionPolicies
from mediadrop.lib.test.db_testcase import DBTestCase
from mediadrop.lib.test.pythonic_testcase import *
from mediadrop.model import DBSession, Media, User


class FilteringRestrictedItemsTest(DBTestCase):
    def setUp(self):
        super(FilteringRestrictedItemsTest, self).setUp()
        
        # without explicit re-registration of the default policy unit tests 
        # failed when running 'python setup.py test'
        self._register_default_policy()
        # get rid of default media
        Media.query.delete()
        self.private_media = Media.example(slug=u'private')
        self.public_media = Media.example(slug=u'public')
        self.permission_system = MediaDropPermissionSystem(self.pylons_config)
        self.media_query = Media.query
        user = self._create_user_without_groups()
        self.perm = UserPermissions(user, self.permission_system)
    
    def _register_default_policy(self):
        PermissionPolicies.register(GroupBasedPermissionsPolicy)
    
    def _create_user_without_groups(self):
        user = User()
        user.user_name = u'joe'
        user.email_address = u'joe@mediadrop.example'
        user.display_name = u'Joe'
        user.groups = []
        DBSession.add(user)
        DBSession.flush()
        return user
    
    # --- tests ---------------------------------------------------------------
    def test_can_use_policies_to_return_only_accessible_items(self):
        assert_equals(2, self.media_query.count())
        fake_policy = self._fake_view_policy(lambda media: (u'public' in media.slug))
        self.permission_system.policies = [fake_policy]
        
        results = self._media_query_results(u'view')
        assert_equals(1, results.count())
        assert_equals(self.public_media, list(results)[0])
    
    # --- tests with access filtering -----------------------------------------
    def test_can_add_filter_criteria_to_base_query(self):
        self.permission_system.policies = [
            self._fake_view_policy_with_query_conditions()
        ]
        results = self._media_query_results(u'view')
        assert_equals(1, results.count())
        assert_equals(self.private_media, list(results)[0])
        
        assert_equals(0, self._media_query_results(u'unknown').count())
    
    def test_only_adds_filter_criteria_to_query_if_all_policies_agree(self):
        self.permission_system.policies = [
            self._fake_view_policy_with_query_conditions(),
            self._fake_view_policy(lambda media: (u'public' in media.slug))
        ]
        results = self._media_query_results(u'view')
        assert_equals(1, results.count())
        assert_equals(self.public_media, list(results)[0])
    
    def test_policies_can_return_true_as_a_shortcut_to_prevent_further_result_filtering(self):
        class FakePolicy(IPermissionPolicy):
            permissions = (u'view', )
            
            def can_apply_access_restrictions_to_query(self, query, permission):
                return True
            
            def access_condition_for_query(self, query, permission, perm):
                return True
        self.permission_system.policies = [FakePolicy()]
        
        results = self._media_query_results(u'view')
        assert_equals(2, results.count())
    
    def test_policies_can_return_false_to_suppress_all_items(self):
        class FakePolicy(IPermissionPolicy):
            permissions = (u'view', )
            
            def can_apply_access_restrictions_to_query(self, query, permission):
                return True
            
            def access_condition_for_query(self, query, permission, perm):
                return False
        self.permission_system.policies = [FakePolicy()]
        
        results = self._media_query_results(u'view')
        assert_equals(0, results.count())
    
    def test_policies_can_return_none_as_access_condition(self):
        class FakePolicy(IPermissionPolicy):
            permissions = (u'view', )
            
            def can_apply_access_restrictions_to_query(self, query, permission):
                return True
            
            def access_condition_for_query(self, query, permission, perm):
                return None
        
        self.permission_system.policies = [FakePolicy()]
        results = self._media_query_results(u'view')
        assert_equals(0, results.count())
        
        self.permission_system.policies = [
            FakePolicy(), 
            self._fake_view_policy_with_query_conditions()
        ]
        results = self._media_query_results(u'view')
        assert_equals(1, results.count())
    
    def test_policies_can_return_query_and_condition(self):
        test_self = self
        class FakePolicy(IPermissionPolicy):
            permissions = (u'view', )
            
            def can_apply_access_restrictions_to_query(self, query, permission):
                return True
            
            def access_condition_for_query(self, query, permission, perm):
                query = query.filter(Media.id == test_self.private_media.id)
                return None, query
        self.permission_system.policies = [FakePolicy()]
        
        results = self._media_query_results(u'view')
        assert_equals(1, results.count())
        assert_equals(self.private_media, results.first())
    
    # --- helpers -------------------------------------------------------------
    
    def _media_query_results(self, permission):
        return self.permission_system.filter_restricted_items(self.media_query, permission, self.perm)
    
    def _fake_view_policy(self, condition):
        class FakeViewPolicy(IPermissionPolicy):
            permissions = (u'view', )
            
            def permits(self, permission, user_permissions, resource):
                media = resource.data['media']
                return condition(media)
        return FakeViewPolicy()
    
    def _fake_view_policy_with_query_conditions(self):
        test_self = self
        class FakePolicy(IPermissionPolicy):
            permissions = (u'view', )
            
            def permits(self, permission, user_permissions, resource):
                return (resource.data['media'].id == test_self.public_media.id)
            
            def can_apply_access_restrictions_to_query(self, query, permission):
                return True
            
            def access_condition_for_query(self, query, permission, perm):
                return (Media.id == test_self.private_media.id)
        return FakePolicy()


import unittest
def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(FilteringRestrictedItemsTest))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')

########NEW FILE########
__FILENAME__ = group_based_permissions_policy_test
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code contained in this file is licensed under the GPLv3 or
# (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.

from mediadrop.lib.auth.api import UserPermissions
from mediadrop.lib.auth.group_based_policy import GroupBasedPermissionsPolicy
from mediadrop.lib.auth.permission_system import (MediaDropPermissionSystem,
    PermissionPolicies)
from mediadrop.lib.test.pythonic_testcase import *
from mediadrop.lib.test.db_testcase import DBTestCase
from mediadrop.model import DBSession, Media, Permission, User


class GroupBasedPermissionsPolicyTest(DBTestCase):
    def setUp(self):
        super(GroupBasedPermissionsPolicyTest, self).setUp()
        PermissionPolicies.register(GroupBasedPermissionsPolicy)
        self.policy = GroupBasedPermissionsPolicy()
    
    def test_applies_to_all_permissions_in_db(self):
        Permission.example(name=u'custom')
        assert_contains(u'edit', self.policy.permissions)
        assert_contains(u'admin', self.policy.permissions)
        assert_contains(u'custom', self.policy.permissions)
    
    def perm(self):
        system = MediaDropPermissionSystem(self.pylons_config)
        system.policies = [self.policy]
        
        user = DBSession.query(User).filter(User.user_name == u'admin').one()
        return UserPermissions(user, system)
    
    def test_can_restrict_queries(self):
        query = Media.query
        permission = u'view'
        perm = self.perm()
        
        assert_true(self.policy.can_apply_access_restrictions_to_query(query, permission))
        assert_true(self.policy.access_condition_for_query(query, permission, perm))
    
    def test_can_restrict_query_if_user_does_not_have_the_required_permission(self):
        query = Media.query
        permission = u'view'
        perm = self.perm()
        view_permission = DBSession.query(Permission).filter(Permission.permission_name == permission).one()
        view_permission.groups = []
        DBSession.flush()
        
        assert_none(self.policy.access_condition_for_query(query, permission, perm))


import unittest
def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(GroupBasedPermissionsPolicyTest))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')

########NEW FILE########
__FILENAME__ = mediadrop_permission_system_test
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code contained in this file is licensed under the GPLv3 or
# (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.

from mediadrop.lib.auth.permission_system import MediaDropPermissionSystem
from mediadrop.lib.test.db_testcase import DBTestCase
from mediadrop.lib.test.pythonic_testcase import *
from mediadrop.model.auth import Group, User
from mediadrop.model.meta import DBSession


class MediaDropPermissionSystemTest(DBTestCase):
    def setUp(self):
        super(MediaDropPermissionSystemTest, self).setUp()
        
        self.anonymous = Group.by_name(u'anonymous')
        self.authenticated = Group.by_name(u'authenticated')
    
    def test_anonymous_users_belong_to_anonymous_group(self):
        self.assert_user_groups([self.anonymous], None)
    
    def test_authenticated_users_belong_to_anonymous_and_authenticated_groups(self):
        user = User.example()
        self.assert_user_groups([self.anonymous, self.authenticated], user)
    
    def test_metagroup_assignment_does_not_fail_if_groups_are_not_found_in_db(self):
        DBSession.delete(self.anonymous)
        DBSession.delete(self.authenticated)
        DBSession.flush()
        
        user = User.example()
        self.assert_user_groups([], user)
    
    # --- helpers -------------------------------------------------------------
    
    def assert_user_groups(self, groups, user):
        perm = MediaDropPermissionSystem.permissions_for_user(user, self.pylons_config)
        assert_equals(set(groups), set(perm.groups))


import unittest
def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(MediaDropPermissionSystemTest))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')

########NEW FILE########
__FILENAME__ = permission_system_test
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code contained in this file is licensed under the GPLv3 or
# (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.

from mediadrop.lib.attribute_dict import AttrDict
from mediadrop.lib.auth.api import IPermissionPolicy, PermissionSystem, Resource,\
    UserPermissions
from mediadrop.lib.test.pythonic_testcase import *


class PermissionSystemTest(PythonicTestCase):
    def setUp(self):
        self.system = PermissionSystem([])
        user = AttrDict(groups=[])
        self.perm = UserPermissions(user, self.system)
    
    def test_can_return_relevant_policies_for_permission(self):
        assert_length(0, self.system.policies_for_permission(u'foobar'))
        
        fake_policy = self._fake_policy(u'foobar', lambda r: True)
        self.system.policies = [fake_policy]
        
        assert_equals([fake_policy], 
                      self.system.policies_for_permission(u'foobar'))
        assert_length(0, self.system.policies_for_permission(u'unknown'))
    
    def test_can_tell_if_user_has_permission(self):
        self.system.policies = [self._fake_policy(u'view', lambda resource: resource.id == 1)]
        
        public_resource = Resource('foo', 1)
        private_resource = Resource(u'foo', 42)
        assert_true(self._has_permission(u'view', public_resource))
        assert_false(self._has_permission(u'view', private_resource))
    
    def test_restricts_access_if_no_policies_present(self):
        self.system.policies = []
        assert_false(self._has_permission(u'view', Resource('foo', 1)))
    
    def test_queries_next_policy_if_first_does_not_decides(self):
        def is_one_or_none(resource):
            if resource.id == 1:
                return True
            return None
        self.system.policies = [
            self._fake_policy(u'view', is_one_or_none),
            self._fake_policy(u'view', lambda r: r.id < 10),
        ]
        
        assert_true(self._has_permission(u'view', Resource('foo', 1)))
        assert_true(self._has_permission(u'view', Resource('foo', 5)))
        assert_false(self._has_permission(u'view', Resource('foo', 20)))
    
    def test_policy_can_block_access(self):
        self.system.policies = [
            self._fake_policy(u'view', lambda r: r.id == 1),
            self._fake_policy(u'view', lambda r: True),
        ]
        assert_true(self._has_permission(u'view', Resource('foo', 1)))
        assert_false(self._has_permission(u'view', Resource('foo', 2)))
    
    def test_asks_only_applicable_policies(self):
        self.system.policies = [self._fake_policy(u'view', lambda resource: resource.id == 1)]
        
        resource = Resource('foo', 1)
        assert_true(self._has_permission(u'view', resource))
        assert_false(self._has_permission(u'unknown', resource))
    
    # --- helpers -------------------------------------------------------------
    
    def _fake_policy(self, permission, condition):
        class FakePolicy(IPermissionPolicy):
            permissions = (permission, )
            
            def permits(self, permission, user_permissions, resource):
                return condition(resource)
        return FakePolicy()
    
    def _has_permission(self, permission, resource):
        return self.system.has_permission(permission, self.perm, resource)


import unittest
def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(PermissionSystemTest))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')

########NEW FILE########
__FILENAME__ = query_result_proxy_test
# -*- coding: utf-8 -*-
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code in this file is dual licensed under the MIT license or
# the GPLv3 or (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.

from sqlalchemy import Column, Integer, String
from sqlalchemy import asc, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from mediadrop.lib.auth.query_result_proxy import QueryResultProxy
from mediadrop.lib.test.pythonic_testcase import *


Base = declarative_base()
class User(Base):
    __tablename__ = 'test_queryresultproxy_users'
    
    id = Column(Integer, primary_key=True)
    name = Column(String)
    activity = Column(Integer)
    
    def __init__(self, name, activity):
        self.name = name
        self.activity = activity
    
    def __repr__(self):
        return 'User(name=%s, activity=%s)' % (repr(self.name), repr(self.activity))



class QueryResultProxyTest(PythonicTestCase):
    def setUp(self):
        self.engine = create_engine('sqlite:///:memory:')
        self.session = self._create_session()
        self._populate_database()
        self.query = self.session.query(User).order_by(asc(User.id))
        self.proxy = QueryResultProxy(self.query)
    
    def _tearDown(self):
        Base.metadata.drop_all(self.engine)
    
    def _create_session(self):
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        return Session()
    
    def _populate_database(self):
        for i, name in enumerate(('foo', 'bar', 'baz', 'quux', 'quuux')):
            self.session.add(User(name, i))
        self.session.commit()
    
    def _next_name(self):
        items = self.proxy.fetch(n=1)
        return items[0].name
    
    def _next_names(self, n=1):
        return self._names(self.proxy.fetch(n=n))
    
    def _names(self, results):
        return [item.name for item in results]
    
    def _name(self, result):
        return result.name
    
    def test_can_fetch_next_item(self):
        assert_equals('foo', self._next_name())
        assert_equals('bar', self._next_name())
        assert_equals('baz', self._next_name())
    
    def test_can_fetch_single_item(self):
        filter_ = lambda item: item.activity >= 4
        self.proxy = QueryResultProxy(self.query, filter_=filter_)
        assert_equals('quuux', self._name(self.proxy.first()))
        assert_equals(None, self.proxy.first())
    
    def test_can_fetch_multiple_items_at_once(self):
        assert_equals(['foo', 'bar'], self._next_names(n=2))
        assert_equals(['baz', 'quux'], self._next_names(n=2))
        assert_equals(['quuux'], self._next_names(n=2))
        assert_equals([], self._next_names(n=2))
    
    def test_regression_do_not_skipped_items_because_of_prefetching(self):
        assert_equals('foo', self._next_name())
        assert_equals(['bar', 'baz'], self._next_names(n=2))
        assert_equals(['quux', 'quuux'], self._next_names(n=2))
    
    def test_can_tell_if_more_items_are_available_even_before_explicit_fetching(self):
        assert_true(self.proxy.more_available())
        assert_equals('foo', self._next_name())
    
    def test_can_tell_if_no_more_items_are_available(self):
        assert_equals(['foo', 'bar', 'baz', 'quux'], self._next_names(n=4))
        assert_true(self.proxy.more_available())
        
        assert_equals('quuux', self._next_name())
        assert_false(self.proxy.more_available())
    
    def test_does_not_omit_prefetched_items_after_asking_if_more_are_available(self):
        assert_true(self.proxy.more_available())
        assert_equals(['foo', 'bar'], self._next_names(n=2))
    
    def test_does_not_omit_prefetched_items_if_many_prefetched_items_were_available(self):
        assert_true(self.proxy.more_available())
        # more_available() should have fetched more than one item so we have 
        # actually 2+ items prefetched.
        assert_not_equals(0, len(self.proxy._prefetched_items))
        # .next() consumes only one item so there should be one left
        # (._prefetched_items were overwritten in this step)
        assert_equals(['foo'], self._names([self.proxy.next()]))
        assert_not_equals(0, len(self.proxy._prefetched_items))
        
        assert_equals(['bar', 'baz'], self._next_names(n=2))
    
    def test_can_initialize_proxy_with_offset(self):
        self.proxy = QueryResultProxy(self.query, start=2)
        assert_equals(['baz', 'quux'], self._next_names(n=2))
    
    def test_can_specify_filter_callable(self):
        filter_ = lambda item: item.activity % 2 == 1
        self.proxy = QueryResultProxy(self.query, filter_=filter_)
        assert_equals(['bar', 'quux'], self._next_names(n=5))
        assert_false(self.proxy.more_available())
    
    def test_proxy_returns_always_specified_number_of_items_if_possible(self):
        filter_ = lambda item: item.activity >= 2
        self.proxy = QueryResultProxy(self.query, filter_=filter_)
        assert_equals(['baz', 'quux', 'quuux'], self._next_names(n=3))
        assert_false(self.proxy.more_available())
    
    # --- limit ----------------------------------------------------------------
    
    def test_can_limit_items_returned_by_iteration(self):
        self.proxy = QueryResultProxy(self.query).limit(2)
        assert_equals(['foo', 'bar'], self._names(self.proxy))
        
        self.proxy = QueryResultProxy(self.query).limit(20)
        assert_equals(['foo', 'bar', 'baz', 'quux', 'quuux'], self._names(self.proxy))
    
    def test_accepts_strings_for_limit(self):
        # that's what SQLAlchemy does (sic!)
        self.proxy = QueryResultProxy(self.query).limit('1')
        assert_equals(['foo'], self._names(self.proxy))
    
    # --- offset ---------------------------------------------------------------
    
    def test_can_offset_for_iteration(self):
        self.proxy = QueryResultProxy(self.query).offset(3)
        assert_equals(['quux', 'quuux'], self._names(self.proxy))
    
    def test_accepts_strings_for_offset(self):
        # that's what SQLAlchemy does (sic!)
        self.proxy = QueryResultProxy(self.query).offset('1')
        assert_equals(['bar', 'baz', 'quux', 'quuux'], self._names(self.proxy))
    
    # --- iteration ------------------------------------------------------------
    
    def test_can_iterate_over_results(self):
        filter_ = lambda item: item.activity >= 2
        self.proxy = QueryResultProxy(self.query, filter_=filter_)
        assert_true(hasattr(self.proxy, '__iter__'))
        
        results = list(self.proxy)
        assert_equals(['baz', 'quux', 'quuux'], self._names(results))
    
    # --- length ---------------------------------------------------------------
    
    def test_can_tell_length_if_no_more_items_available(self):
        filter_ = lambda item: item.activity >= 2
        self.proxy = QueryResultProxy(self.query, filter_=filter_)
        assert_true(hasattr(self.proxy, '__len__'))
        
        assert_length(3, self.proxy.fetch(10))
        assert_false(self.proxy.more_available())
        assert_length(3, self.proxy)
    
    def test_can_tell_length(self):
        filter_ = lambda item: item.activity >= 2
        self.proxy = QueryResultProxy(self.query, filter_=filter_)
        assert_length(3, self.proxy)
    
    def test_can_specify_how_many_items_should_be_fetched_by_default(self):
        self.proxy = QueryResultProxy(self.query, default_fetch=3)
        self.proxy.more_available()
        assert_equals(3, len(self.proxy._prefetched_items))
    
    # --- slicing --------------------------------------------------------------
    
    def test_supports_simple_slicing(self):
        assert_equals(['foo', 'bar'], self._names(self.proxy[0:2]))
        # slicing does not consume items
        assert_equals(['foo'], self._names([self.proxy.next()]))
        
        assert_equals(['baz', 'quux', 'quuux'], self._names(self.proxy[2:5]))
    
    # TODO: slice before start

import unittest
def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(QueryResultProxyTest))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')

########NEW FILE########
__FILENAME__ = static_query_test
# -*- coding: utf-8 -*-
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code in this file is dual licensed under the MIT license or
# the GPLv3 or (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.

from mediadrop.lib.auth.query_result_proxy import StaticQuery
from mediadrop.lib.test.pythonic_testcase import *


class StaticQueryTest(PythonicTestCase):
    def setUp(self):
        self.query = StaticQuery([1, 2, 3, 4, 5])
    
    def test_can_return_all_items(self):
        assert_equals([1, 2, 3, 4, 5], self.query.all())
    
    def test_can_return_all_items_with_iteration(self):
        assert_equals([1, 2, 3, 4, 5], list(self.query))
    
    def test_can_use_offset(self):
        assert_equals([3, 4, 5], self.query.offset(2).all())
    
    def test_can_build_static_query(self):
        assert_equals([1, 2], list(self.query.limit(2)))
    
    def test_knows_number_of_items(self):
        all_items = self.query.offset(1).all()
        assert_length(4, all_items)
        assert_equals(4, self.query.count())
        assert_equals(4, len(self.query))
    
    def test_supports_slicing(self):
        assert_equals([3, 4, 5], self.query[2:])
        assert_equals(3, self.query.offset(1)[2])
    
    def test_can_return_first_item(self):
        assert_equals(1, self.query.first())
        list(self.query) # consume all other items
        assert_none(self.query.first())


import unittest
def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(StaticQueryTest))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')

########NEW FILE########
__FILENAME__ = util
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code contained in this file is licensed under the GPLv3 or
# (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.

from pylons import config, request

from mediadrop.lib.auth.permission_system import MediaDropPermissionSystem


__all__ = ['viewable_media']

def viewable_media(query):
    permission_system = MediaDropPermissionSystem(config)
    return permission_system.filter_restricted_items(query, u'view', request.perm)


########NEW FILE########
__FILENAME__ = base
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code contained in this file is licensed under the GPLv3 or
# (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.
"""
The Base Controller API

Provides controller classes for subclassing.
"""
import os
import time
import urllib2

from paste.deploy.converters import asbool
from pylons import app_globals, config, request, response, tmpl_context
from pylons.controllers import WSGIController
from pylons.controllers.util import abort
from tw.forms.fields import ContainerMixin as _ContainerMixin

from mediadrop.lib import helpers
from mediadrop.lib.auth import ControllerProtector, has_permission, Predicate
from mediadrop.lib.css_delivery import StyleSheets
from mediadrop.lib.i18n import Translator
from mediadrop.lib.js_delivery import Scripts
from mediadrop.model import DBSession, Setting

__all__ = [
    'BareBonesController',
    'BaseController',
    'BaseSettingsController',
]

class BareBonesController(WSGIController):
    """
    The Bare Bones extension of a WSGIController needed for this app to function
    """
    def __init__(self, *args, **kwargs):
        """Implements TG2 style controller-level permissions requirements.

        If the allow_only class attribute has been set, wrap the __before__
        method with an ActionProtector using the predicate defined there.
        """
        if hasattr(self, 'allow_only') \
        and isinstance(self.allow_only, Predicate):
            # ControllerProtector wraps the __before__ method of this instance.
            cp = ControllerProtector(self.allow_only)
            self = cp(self)
        WSGIController.__init__(self, *args, **kwargs)

    def _get_method_args(self):
        """Retrieve the method arguments to use with inspect call.

        By default, this uses Routes to retrieve the arguments,
        override this method to customize the arguments your controller
        actions are called with.

        For MediaDrop, we extend this to include all GET and POST params.

        NOTE: If the action does not define \*\*kwargs, then only the kwargs
              that it defines will be passed to it when it is called.
        """
        kwargs = request.params.mixed()
        kwargs.update(WSGIController._get_method_args(self))
        return kwargs

    def __before__(self, *args, **kwargs):
        """This method is called before your action is.

        It should be used for setting up variables/objects, restricting access
        to other actions, or other tasks which should be executed before the
        action is called.

        NOTE: If this method is wrapped in an ActionProtector, all methods of
              the class will be protected it. See :meth:`__init__`.
        """
        self.setup_translator()
        response.scripts = Scripts()
        response.stylesheets = StyleSheets()
        response.feed_links = []
        response.facebook = None
        response.warnings = []
        request.perm = request.environ['mediadrop.perm']

        action_method = getattr(self, kwargs['action'], None)
        # The expose decorator sets the exposed attribute on controller
        # actions. If the method does not exist or is not exposed, raise
        # an HTTPNotFound exception.
        if not getattr(action_method, 'exposed', False):
            abort(status_code=404)

    def setup_translator(self):
        # Load the primary translator on first request and reactivate it for
        # each subsequent request until the primary language is changed.
        app_globs = app_globals._current_obj()
        lang = app_globs.settings['primary_language'] or 'en'
        if app_globs.primary_language == lang and app_globs.primary_translator:
            translator = app_globs.primary_translator
        else:
            translator = Translator(lang, config['locale_dirs'])
            app_globs.primary_translator = translator
            app_globs.primary_language = lang
        translator.install_pylons_global()

class BaseController(BareBonesController):
    """
    The BaseController for all our controllers.

    Adds functionality for fetching and updating an externally generated
    template.
    """
    def __init__(self, *args, **kwargs):
        """Initialize the controller and hook in the external template, if any.

        These settings used are pulled from your INI config file:

            external_template
                Flag to enable or disable use of the external template
            external_template_name
                The name to load/save the external template as
            external_template_url
                The URL to pull the external template from
            external_template_timeout
                The number of seconds before the template should be refreshed

        See also :meth:`update_external_template` for more information.
        """
        tmpl_context.layout_template = config['layout_template']
        tmpl_context.external_template = None

        # FIXME: This external template is only ever updated on server startup
        if asbool(config.get('external_template')):
            tmpl_name = config['external_template_name']
            tmpl_url = config['external_template_url']
            timeout = config['external_template_timeout']
            tmpl_context.external_template = tmpl_name

            try:
                self.update_external_template(tmpl_url, tmpl_name, timeout)
            except:
                # Catch the error because the external template is noncritical.
                # TODO: Add error reporting here.
                pass

        BareBonesController.__init__(self, *args, **kwargs)

    def update_external_template(self, tmpl_url, tmpl_name, timeout):
        """Conditionally fetch and cache the remote template.

        This method will only work on \*nix systems.

        :param tmpl_url: The URL to fetch the Genshi template from.
        :param tmpl_name: The template name to save under.
        :param timeout: Number of seconds to wait before refreshing
        :rtype: bool
        :returns: ``True`` if updated successfully, ``False`` if unnecessary.
        :raises Exception: If update fails unexpectedly due to IO problems.

        """
        current_dir = os.path.dirname(__file__)
        tmpl_path = '%s/../templates/%s.html' % (current_dir, tmpl_name)
        tmpl_tmp_path = '%s/../templates/%s_new.html' % (current_dir, tmpl_name)

        # Stat the main template file.
        try:
            statinfo = os.stat(tmpl_path)[:10]
            st_mode, st_ino, st_dev, st_nlink,\
                st_uid, st_gid, st_size, st_ntime,\
                st_mtime, st_ctime = statinfo

            # st_mtime and now are both unix timestamps.
            now = time.time()
            diff = now - st_mtime

            # if the template file is less than 5 minutes old, return
            if diff < float(timeout):
                return False
        except OSError, e:
            # Continue if the external template hasn't ever been created yet.
            if e.errno != 2:
                raise e

        try:
            # If the tmpl_tmp_path file exists
            # That means that another instance of MediaDrop is writing to it
            # Return immediately
            os.stat(tmpl_tmp_path)
            return False
        except OSError, e:
            # If the stat call failed, create the file. and continue.
            tmpl_tmp_file = open(tmpl_tmp_path, 'w')

        # Download the template, replace windows style newlines
        tmpl_contents = urllib2.urlopen(tmpl_url)
        s = tmpl_contents.read().replace("\r\n", "\n")
        tmpl_contents.close()

        # Write to the temp template file.
        tmpl_tmp_file.write(s)
        tmpl_tmp_file.close()

        # Rename the temp file to the main template file
        # NOTE: This only works on *nix, and is only guaranteed to work if the
        #       files are on the same filesystem.
        #       see http://docs.python.org/library/os.html#os.rename
        os.rename(tmpl_tmp_path, tmpl_path)

class BaseSettingsController(BaseController):
    """
    Dumb controller for display and saving basic settings forms

    This maps forms from :class:`mediadrop.forms.admin.settings` to our
    model :class:`~mediadrop.model.settings.Setting`. This controller
    doesn't care what settings are used, the form dictates everything.
    The form field names should exactly match the name in the model,
    regardless of it's nesting in the form.

    If and when setting values need to be altered for display purposes,
    or before it is saved to the database, it should be done with a
    field validator instead of adding complexity here.

    """
    allow_only = has_permission('admin')

    def __before__(self, *args, **kwargs):
        """Load all our settings before each request."""
        BaseController.__before__(self, *args, **kwargs)
        from mediadrop.model import Setting
        tmpl_context.settings = dict(DBSession.query(Setting.key, Setting))

    def _update_settings(self, values):
        """Modify the settings associated with the given dictionary."""
        for name, value in values.iteritems():
            if name in tmpl_context.settings:
                setting = tmpl_context.settings[name]
            else:
                setting = Setting(key=name, value=value)
            if value is None:
                value = u''
            else:
                value = unicode(value)
            if setting.value != value:
                setting.value = value
                DBSession.add(setting)
        DBSession.flush()

        # Clear the settings cache unless there are multiple processes.
        # We have no way of notifying the other processes that they need
        # to clear their caches too, so we've just gotta let it play out
        # until all the caches expire.
        if not request.environ.get('wsgi.multiprocess', False):
            app_globals.settings_cache.clear()
        else:
            # uWSGI provides an automagically included module
            # that we can use to call a graceful restart of all
            # the uwsgi processes.
            # http://projects.unbit.it/uwsgi/wiki/uWSGIReload
            try:
                import uwsgi
                uwsgi.reload()
            except ImportError:
                pass

    def _display(self, form, values=None, action=None):
        """Return the template variables for display of the form.

        :rtype: dict
        :returns:
            form
                The passed in form instance.
            form_values
                ``dict`` form values
        """
        form_values = self._nest_settings_for_form(tmpl_context.settings, form)
        if values:
            form_values.update(values)
        return dict(
            form = form,
            form_action = action,
            form_values = form_values,
        )

    def _save(self, form, redirect_action=None, values=None):
        """Save the values from the passed in form instance."""
        values = self._flatten_settings_from_form(form, values)
        self._update_settings(values)
        if redirect_action:
            helpers.redirect(action=redirect_action)

    def _is_button(self, field):
        return getattr(field, 'type', None) in ('button', 'submit', 'reset', 'image')

    def _nest_settings_for_form(self, settings, form):
        """Create a dict of setting values nested to match the form."""
        form_values = {}
        for field in form.c:
            if isinstance(field, _ContainerMixin):
                form_values[field._name] = self._nest_settings_for_form(
                    settings, field
                )
            elif field._name in settings:
                form_values[field._name] = settings[field._name].value
        return form_values

    def _flatten_settings_from_form(self, form, form_values):
        """Take a nested dict and return a flat dict of setting values."""
        setting_values = {}
        for field in form.c:
            if isinstance(field, _ContainerMixin):
                setting_values.update(self._flatten_settings_from_form(
                    field, form_values[field._name]
                ))
            elif not self._is_button(field):
                setting_values[field._name] = form_values[field._name]
        return setting_values

########NEW FILE########
__FILENAME__ = util
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code contained in this file is licensed under the GPLv3 or
# (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.


from __future__ import absolute_import

import os
import sys

import paste
from paste.fixture import TestApp
from paste.deploy import appconfig, loadapp
from paste.script.util import logging_config


__all__ = ['init_mediadrop']


def init_mediadrop(config_filename, here_dir=None, disable_logging=False):
    if not os.path.exists(config_filename):
        raise IOError('Config file %r does not exist.' % config_filename)
    if here_dir is None:
        here_dir = os.getcwd()
    if not disable_logging:
        logging_config.fileConfig(config_filename)

    config_name = 'config:%s' % config_filename
    # XXX: Note, initializing CONFIG here is Legacy support. pylons.config
    # will automatically be initialized and restored via the registry
    # restorer along with the other StackedObjectProxys
    # Load app config into paste.deploy to simulate request config
    # Setup the Paste CONFIG object, adding app_conf/global_conf for legacy
    # code
    conf = appconfig(config_name, relative_to=here_dir)
    conf.update(dict(app_conf=conf.local_conf,
                     global_conf=conf.global_conf))
    paste.deploy.config.CONFIG.push_thread_config(conf)

    # Load locals and populate with objects for use in shell
    sys.path.insert(0, here_dir)

    # WebOb 1.2+ does not support unicode_errors/decode_param_names anymore for
    # the Request() class so we need to override Pylons' defaults to prevent
    # DeprecationWarnings (only shown in Python 2.6 by default).
    webob_request_options = {
        'charset': 'utf-8',
        'errors': None,
        'decode_param_names': None,
        'language': 'en-us',
    }
    global_conf = {'pylons.request_options': webob_request_options}
    # Load the wsgi app first so that everything is initialized right
    wsgiapp = loadapp(config_name, relative_to=here_dir, global_conf=global_conf)
    test_app = TestApp(wsgiapp)

    # Query the test app to setup the environment
    tresponse = test_app.get('/_test_vars')
    request_id = int(tresponse.body)

    # Disable restoration during test_app requests
    test_app.pre_request_hook = lambda self: paste.registry.restorer.restoration_end()
    test_app.post_request_hook = lambda self: paste.registry.restorer.restoration_begin(request_id)

    # Restore the state of the Pylons special objects (StackedObjectProxies)
    paste.registry.restorer.restoration_begin(request_id)


########NEW FILE########
__FILENAME__ = cli_commands
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code contained in this file is licensed under the GPLv3 or
# (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.
"""Paster Command Subclasses for use in utilities."""


from __future__ import absolute_import

import os
import sys

import paste.fixture
import paste.registry
import paste.deploy.config
from paste.deploy import loadapp, appconfig
from paste.script.command import Command, BadCommand

import pylons
from .cli import init_mediadrop

__all__ = [
    'LoadAppCommand',
    'load_app',
]

class LoadAppCommand(Command):
    """Load the app and all associated StackedObjectProxies.

    Useful for batch scripts.

    The optional CONFIG_FILE argument specifies the config file to use for
    the interactive shell. CONFIG_FILE defaults to 'development.ini'.

    This allows you to test your mapper, models, and simulate web requests
    using ``paste.fixture``.

    This class has been adapted from pylons.commands.ShellCommand.
    """
    summary = __doc__.splitlines()[0]

    min_args = 0
    max_args = 1
    group_name = 'pylons'

    parser = Command.standard_parser()

    parser.add_option('-q',
                      action='count',
                      dest='quiet',
                      default=0,
                      help="Do not load logging configuration from the config file")

    def __init__(self, name, summary):
        self.summary = summary
        Command.__init__(self, name)

    def command(self):
        """Main command to create a new shell"""
        self.verbose = 3
        if len(self.args) == 0:
            # Assume the .ini file is ./development.ini
            config_file = 'development.ini'
            if not os.path.isfile(config_file):
                raise BadCommand('CONFIG_FILE not found at: .%s%s\n'
                                 'Please specify a CONFIG_FILE' % \
                                 (os.path.sep, config_file)
                                )
        else:
            config_file = self.args[0]

        init_mediadrop(config_file, here_dir=os.getcwd(), disable_logging=self.options.quiet)

    def parse_args(self, args):
        self.options, self.args = self.parser.parse_args(args)

def load_app(cmd):
    cmd.parser.usage = "%%prog [options] [CONFIG_FILE]\n%s" % cmd.summary
    try:
        cmd.run(sys.argv[1:])
    except Exception, e:
        print >> sys.stderr, "ERROR:"
        print >> sys.stderr, e
        print >> sys.stderr, ""
        cmd.parser.print_help()
        sys.exit(1)
    return cmd

########NEW FILE########
__FILENAME__ = functional
"""Functional utilities for Python 2.4 compatibility.

Source: http://code.djangoproject.com/browser/django/trunk/django/utils/functional.py

"""
# License for code in this file that was taken from Python 2.5.

# PYTHON SOFTWARE FOUNDATION LICENSE VERSION 2
# --------------------------------------------
#
# 1. This LICENSE AGREEMENT is between the Python Software Foundation
# ("PSF"), and the Individual or Organization ("Licensee") accessing and
# otherwise using this software ("Python") in source or binary form and
# its associated documentation.
#
# 2. Subject to the terms and conditions of this License Agreement, PSF
# hereby grants Licensee a nonexclusive, royalty-free, world-wide
# license to reproduce, analyze, test, perform and/or display publicly,
# prepare derivative works, distribute, and otherwise use Python
# alone or in any derivative version, provided, however, that PSF's
# License Agreement and PSF's notice of copyright, i.e., "Copyright (c)
# 2001, 2002, 2003, 2004, 2005, 2006, 2007 Python Software Foundation;
# All Rights Reserved" are retained in Python alone or in any derivative
# version prepared by Licensee.
#
# 3. In the event Licensee prepares a derivative work that is based on
# or incorporates Python or any part thereof, and wants to make
# the derivative work available to others as provided herein, then
# Licensee hereby agrees to include in any such work a brief summary of
# the changes made to Python.
#
# 4. PSF is making Python available to Licensee on an "AS IS"
# basis.  PSF MAKES NO REPRESENTATIONS OR WARRANTIES, EXPRESS OR
# IMPLIED.  BY WAY OF EXAMPLE, BUT NOT LIMITATION, PSF MAKES NO AND
# DISCLAIMS ANY REPRESENTATION OR WARRANTY OF MERCHANTABILITY OR FITNESS
# FOR ANY PARTICULAR PURPOSE OR THAT THE USE OF PYTHON WILL NOT
# INFRINGE ANY THIRD PARTY RIGHTS.
#
# 5. PSF SHALL NOT BE LIABLE TO LICENSEE OR ANY OTHER USERS OF PYTHON
# FOR ANY INCIDENTAL, SPECIAL, OR CONSEQUENTIAL DAMAGES OR LOSS AS
# A RESULT OF MODIFYING, DISTRIBUTING, OR OTHERWISE USING PYTHON,
# OR ANY DERIVATIVE THEREOF, EVEN IF ADVISED OF THE POSSIBILITY THEREOF.
#
# 6. This License Agreement will automatically terminate upon a material
# breach of its terms and conditions.
#
# 7. Nothing in this License Agreement shall be deemed to create any
# relationship of agency, partnership, or joint venture between PSF and
# Licensee.  This License Agreement does not grant permission to use PSF
# trademarks or trade name in a trademark sense to endorse or promote
# products or services of Licensee, or any third party.
#
# 8. By copying, installing or otherwise using Python, Licensee
# agrees to be bound by the terms and conditions of this License
# Agreement.

### Begin from Python 2.5 functools.py ########################################

# Summary of changes made to the Python 2.5 code below:
#   * swapped ``partial`` for ``curry`` to maintain backwards-compatibility
#     in Django.
#   * Wrapped the ``setattr`` call in ``update_wrapper`` with a try-except
#     block to make it compatible with Python 2.3, which doesn't allow
#     assigning to ``__name__``.

# Copyright (c) 2001, 2002, 2003, 2004, 2005, 2006, 2007 Python Software
# Foundation. All Rights Reserved.

###############################################################################

# update_wrapper() and wraps() are tools to help write
# wrapper functions that can handle naive introspection

def _compat_curry(fun, *args, **kwargs):
    """New function with partial application of the given arguments
    and keywords."""

    def _curried(*addargs, **addkwargs):
        return fun(*(args + addargs), **dict(kwargs, **addkwargs))
    return _curried


try:
    from functools import partial as curry
except ImportError:
    curry = _compat_curry

WRAPPER_ASSIGNMENTS = ('__module__', '__name__', '__doc__')
WRAPPER_UPDATES = ('__dict__',)
def _compat_update_wrapper(wrapper, wrapped, assigned=WRAPPER_ASSIGNMENTS,
        updated=WRAPPER_UPDATES):
    """Update a wrapper function to look like the wrapped function

       wrapper is the function to be updated
       wrapped is the original function
       assigned is a tuple naming the attributes assigned directly
       from the wrapped function to the wrapper function (defaults to
       functools.WRAPPER_ASSIGNMENTS)
       updated is a tuple naming the attributes off the wrapper that
       are updated with the corresponding attribute from the wrapped
       function (defaults to functools.WRAPPER_UPDATES)

    """
    for attr in assigned:
        try:
            setattr(wrapper, attr, getattr(wrapped, attr))
        except TypeError: # Python 2.3 doesn't allow assigning to __name__.
            pass
    for attr in updated:
        getattr(wrapper, attr).update(getattr(wrapped, attr))
    # Return the wrapper so this can be used as a decorator via curry()
    return wrapper

try:
    from functools import update_wrapper
except ImportError:
    update_wrapper = _compat_update_wrapper


def _compat_wraps(wrapped, assigned=WRAPPER_ASSIGNMENTS,
        updated=WRAPPER_UPDATES):
    """Decorator factory to apply update_wrapper() to a wrapper function

    Returns a decorator that invokes update_wrapper() with the decorated
    function as the wrapper argument and the arguments to wraps() as the
    remaining arguments. Default arguments are as for update_wrapper().
    This is a convenience function to simplify applying curry() to
    update_wrapper().

    """
    return curry(update_wrapper, wrapped=wrapped,
                 assigned=assigned, updated=updated)

try:
    from functools import wraps
except ImportError:
    wraps = _compat_wraps

### End from Python 2.5 functools.py ##########################################

########NEW FILE########
__FILENAME__ = css_delivery
# -*- coding: utf-8 -*-
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code in this file is dual licensed under the MIT license or
# the GPLv3 or (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.

from mediadrop.lib.js_delivery import ResourcesCollection

__all__ = ['StyleSheet', 'StyleSheets']

class StyleSheet(object):
    def __init__(self, url, key=None, media=None):
        self.url = url
        self.key = key
        self.media = media
    
    def render(self):
        template = '<link href="%s" rel="stylesheet" type="text/css"%s></link>'
        media = self.media and (' media="%s"' % self.media) or ''
        return template % (self.url, media)
    
    def __unicode__(self):
        return self.render()
    
    def __repr__(self):
        template = 'StyleSheet(%r, key=%r%s)'
        media = self.media and (', media=%r' % self.media) or ''
        return template % (self.url, self.key, media)
    
    def __eq__(self, other):
        if (not hasattr(other, 'url')) or (self.url != other.url):
            return False
        if (not hasattr(other, 'media')) or (self.media != other.media):
            return False
        return True
    
    def __ne__(self, other):
        return not (self == other)


class StyleSheets(ResourcesCollection):
    def add(self, stylesheet):
        if stylesheet in self._resources:
            return
        self._resources.append(stylesheet)
    
    def add_all(self, *stylesheets):
        for stylesheet in stylesheets:
            self.add(stylesheet)
    
    # --- some interface polishing ---------------------------------------------
    @property
    def stylesheets(self):
        return self._resources
    
    def replace_stylesheet_with_key(self, stylesheet):
        self.replace_resource_with_key(stylesheet)


########NEW FILE########
__FILENAME__ = decorators
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code contained in this file is licensed under the GPLv3 or
# (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.

import logging
import warnings
import simplejson
import time

import formencode
import tw.forms

from decorator import decorator
from paste.deploy.converters import asbool
from pylons import config, request, response, tmpl_context, translator
from pylons.decorators.cache import create_cache_key, _make_dict_from_args
from pylons.decorators.util import get_pylons
from webob.exc import HTTPException, HTTPMethodNotAllowed

from mediadrop.lib.paginate import paginate
from mediadrop.lib.templating import render

__all__ = [
    'ValidationState',
    'autocommit',
    'beaker_cache',
    'expose',
    'expose_xhr',
    'memoize',
    'observable',
    'paginate',
    'validate',
    'validate_xhr',
]

log = logging.getLogger(__name__)

# TODO: Rework all decorators to use the decorators module. By using it,
#       the function signature of the original action method is preserved,
#       allowing pylons.controllers.core.WSGIController._inspect_call to
#       do its job properly.

_func_attrs = [
    # Attributes that define useful information or context for functions
    '__dict__', '__doc__', '__name__', 'im_class', 'im_func', 'im_self',
    'exposed', # custom attribute to allow web access
]

def _copy_func_attrs(f1, f2):
    """Copy relevant attributes from f1 to f2

    TODO: maybe replace this with the use of functools.wraps
    http://docs.python.org/library/functools.html#functools.wraps
    """

    for x in _func_attrs:
        if hasattr(f1, x):
            setattr(f2, x, getattr(f1, x))

def _get_func_attrs(f):
    """Return a dict of attributes. Used for debugging."""
    result = {}
    for x in _func_attrs:
        result[x] = getattr(f, x, (None,))
    return result

def _expose_wrapper(f, template, request_method=None, permission=None):
    """Returns a function that will render the passed in function according
    to the passed in template"""
    f.exposed = True

    # Shortcut for simple expose of strings
    if template == 'string' and not request_method and not permission:
        return f

    if request_method:
        request_method = request_method.upper()

    def wrapped_f(*args, **kwargs):
        if request_method and request_method != request.method:
            raise HTTPMethodNotAllowed().exception

        result = f(*args, **kwargs)
        tmpl = template

        if hasattr(request, 'override_template'):
            tmpl = request.override_template

        if tmpl == 'string':
            return result

        if tmpl == 'json':
            if isinstance(result, (list, tuple)):
                msg = ("JSON responses with Array envelopes are susceptible "
                       "to cross-site data leak attacks, see "
                       "http://wiki.pylonshq.com/display/pylonsfaq/Warnings")
                if config['debug']:
                    raise TypeError(msg)
                warnings.warn(msg, Warning, 2)
                log.warning(msg)
            response.headers['Content-Type'] = 'application/json'
            return simplejson.dumps(result)

        if request.environ.get('paste.testing', False):
            # Make the vars passed from action to template accessible to tests
            request.environ['paste.testing_variables']['tmpl_vars'] = result

            # Serve application/xhtml+xml instead of text/html during testing.
            # This allows us to query the response xhtml as ElementTree XML
            # instead of BeautifulSoup HTML.
            # NOTE: We do not serve true xhtml to all clients that support it
            #       because of a bug in Mootools Swiff as of v1.2.4:
            #       https://mootools.lighthouseapp.com/projects/2706/tickets/758
            if response.content_type == 'text/html':
                response.content_type = 'application/xhtml+xml'

        return render(tmpl, tmpl_vars=result, method='auto')

    if permission:
        from mediadrop.lib.auth import FunctionProtector, has_permission
        wrapped_f = FunctionProtector(has_permission(permission)).wrap(wrapped_f)

    return wrapped_f

def expose(template='string', request_method=None, permission=None):
    """Simple expose decorator for controller actions.

    Transparently wraps a method in a function that will render the method's
    return value with the given template.

    Sets the 'exposed' and 'template' attributes of the wrapped method,
    marking it as safe to be accessed via HTTP request.

    Example, using a genshi template::

        class MyController(BaseController):

            @expose('path/to/template.html')
            def sample_action(self, *args):
                # do something
                return dict(message='Hello World!')

    :param template:
        One of:
            * The path to a genshi template, relative to the project's
              template directory
            * 'string'
            * 'json'
    :type template: string or unicode

    :param request_method: Optional request method to verify. If GET or
        POST is given and the method of the current request does not match,
        a 405 Method Not Allowed error is raised.

    """
    def wrap(f):
        wrapped_f = _expose_wrapper(f, template, request_method, permission)
        _copy_func_attrs(f, wrapped_f)
        return wrapped_f
    return wrap

def expose_xhr(template_norm='string', template_xhr='json',
               request_method=None, permission=None):
    """
    Expose different templates for normal vs XMLHttpRequest requests.

    Example, using two genshi templates::

        class MyController(BaseController):

            @expose_xhr('items/main_list.html', 'items/ajax_list.html')
            def sample_action(self, *args):
                # do something
                return dict(items=get_items_list())
    """
    def wrap(f):
        norm = _expose_wrapper(f, template_norm, request_method, permission)
        xhr = _expose_wrapper(f, template_xhr, request_method, permission)

        def choose(*args, **kwargs):
            if request.is_xhr:
                return xhr(*args, **kwargs)
            else:
                return norm(*args, **kwargs)
        _copy_func_attrs(f, choose)
        return choose
    return wrap

class ValidationState(object):
    """A ``state`` for FormEncode validate API with a smart ``_`` hook.

    This idea and explanation borrowed from Pylons, modified to work with
    our custom Translator object.

    The FormEncode library used by validate() decorator has some
    provision for localizing error messages. In particular, it looks
    for attribute ``_`` in the application-specific state object that
    gets passed to every ``.to_python()`` call. If it is found, the
    ``_`` is assumed to be a gettext-like function and is called to
    localize error messages.

    One complication is that FormEncode ships with localized error
    messages for standard validators so the user may want to re-use
    them instead of gathering and translating everything from scratch.
    To allow this, we pass as ``_`` a function which looks up
    translation both in application and formencode message catalogs.

    """
    @staticmethod
    def _(msgid):
        """Get a translated string from the 'mediadrop' or FormEncode domains.

        This allows us to "merge" localized error messages from built-in
        FormEncode's validators with application-specific validators.

        :type msgid: ``str``
        :param msgid: A byte string to retrieve translations for.
        :rtype: ``unicode``
        :returns: The translated string, or the original msgid if no
            translation was found.
        """
        gettext = translator.gettext
        trans = gettext(msgid)
        if trans == msgid:
            trans = gettext(msgid, domain='FormEncode')
        return trans

class validate(object):
    """Registers which validators ought to be applied to the following action

    Copies the functionality of TurboGears2.0, rather than that of Pylons1.0,
    except that we validate request.params, not kwargs. TurboGears has the
    unfortunate need to validate all kwargs because it uses object dispatch.
    We really only need to validate request.params: if we do need to
    validate the kw/routing args we can and should do that in our routes.

    If you want to validate the contents of your form,
    you can use the ``@validate()`` decorator to register
    the validators that ought to be called.

    :Parameters:
      validators
        Pass in a dictionary of FormEncode validators.
        The keys should match the form field names.
      error_handler
        Pass in the controller method which should be used
        to handle any form errors
      form
        Pass in a ToscaWidget based form with validators

    The first positional parameter can either be a dictionary of validators,
    a FormEncode schema validator, or a callable which acts like a FormEncode
    validator.
    """
    def __init__(self, validators=None, error_handler=None, form=None,
                 state=ValidationState):
        if form:
            self.validators = form
        if validators:
            self.validators = validators
        self.error_handler = error_handler
        self.state = state

    def __call__(self, func):
        self.func = func
        def validate(*args, **kwargs):
            # Initialize validation context
            tmpl_context.form_errors = {}
            tmpl_context.form_values = {}
            try:
                # Perform the validation
                values = self._to_python(request.params.mixed())
                tmpl_context.form_values = values
                # We like having our request params as kwargs but this is optional
                kwargs.update(values)
                # Call the decorated function
                return self.func(*args, **kwargs)
            except formencode.api.Invalid, inv:
                # Unless the input was in valid. In which case...
                return self._handle_validation_errors(args, kwargs, inv)
        _copy_func_attrs(func, validate)
        return validate

    def _handle_validation_errors(self, args, kwargs, exception):
        """
        Sets up tmpl_context.form_values and tmpl_context.form_errors to assist
        generating a form with given values and the validation failure
        messages.
        """
        c = tmpl_context._current_obj()
        c.validation_exception = exception

        # Set up the tmpl_context.form_values dict with the invalid values
        c.form_values = exception.value

        # Set up the tmpl_context.form_errors dict
        c.form_errors = exception.unpack_errors()
        if not isinstance(c.form_errors, dict):
            c.form_errors = {'_the_form': c.form_errors}

        return self._call_error_handler(args, kwargs)

    def _call_error_handler(self, args, kwargs):
        # Get the correct error_handler function
        error_handler = self.error_handler
        if error_handler is None:
            error_handler = self.func
        return error_handler(*args, **kwargs)

    def _to_python(self, params):
        """
        self.validators can be in three forms:

        1) A dictionary, with key being the request parameter name, and value a
           FormEncode validator.

        2) A FormEncode Schema object

        3) Any object with a "validate" method that takes a dictionary of the
           request variables.

        Validation can "clean" or otherwise modify the parameters that were
        passed in, not just raise an exception.  Validation exceptions should
        be FormEncode Invalid objects.
        """
        if isinstance(self.validators, dict):
            new_params = {}
            errors = {}
            for field, validator in self.validators.iteritems():
                try:
                    new_params[field] = validator.to_python(params.get(field),
                                                            self.state)
                # catch individual validation errors into the errors dictionary
                except formencode.api.Invalid, inv:
                    errors[field] = inv

            # If there are errors, create a compound validation error based on
            # the errors dictionary, and raise it as an exception
            if errors:
                raise formencode.api.Invalid(
                    formencode.schema.format_compound_error(errors),
                    params, None, error_dict=errors)
            return new_params

        elif isinstance(self.validators, formencode.Schema):
            # A FormEncode Schema object - to_python converts the incoming
            # parameters to sanitized Python values
            return self.validators.to_python(params, self.state)

        elif isinstance(self.validators, tw.forms.InputWidget) \
        or hasattr(self.validators, 'validate'):
            # A tw.forms.InputWidget object. validate converts the incoming
            # parameters to sanitized Python values
            # - OR -
            # An object with a "validate" method - call it with the parameters
            # This is a generic case for classes mimicking tw.forms.InputWidget
            return self.validators.validate(params, self.state)

        # No validation was done. Just return the original params.
        return params

class validate_xhr(validate):
    """
    Special validation that returns JSON dicts for Ajax requests.

    Regular synchronous requests are handled normally.

    Example Usage::

        @expose_xhr()
        @validate_xhr(my_form_instance, error_handler=edit)
        def save(self, id, **kwargs):
            something = make_something()
            if request.is_xhr:
                return dict(my_id=something.id)
            else:
                redirect(action='view', id=id)

    On success, returns this in addition to whatever dict you provide::

        {'success': True, 'values': {}, 'my_id': 123}

    On validation error, returns::

        {'success': False, 'values': {}, 'errors': {}}

    """
    def __call__(self, func):
        """Catch redirects in the controller action and return JSON."""
        self.validate_func = super(validate_xhr, self).__call__(func)
        def validate_wrapper(*args, **kwargs):
            result = self.validate_func(*args, **kwargs)
            if request.is_xhr:
                if not isinstance(result, dict):
                    result = {}
                result.setdefault('success', True)
                values = result.get('values', {})
                for key, value in tmpl_context.form_values.iteritems():
                    values.setdefault(key, value)
            return result
        _copy_func_attrs(func, validate_wrapper)
        return validate_wrapper

    def _call_error_handler(self, args, kwargs):
        if request.is_xhr:
            return {'success': False, 'errors': tmpl_context.form_errors}
        else:
            return super(validate_xhr, self)._call_error_handler(args, kwargs)

def beaker_cache(key="cache_default", expire="never", type=None,
                 query_args=False,
                 cache_headers=('content-type', 'content-length'),
                 invalidate_on_startup=False,
                 cache_response=True, **b_kwargs):
    """Cache decorator utilizing Beaker. Caches action or other
    function that returns a pickle-able object as a result.

    Optional arguments:

    ``key``
        None - No variable key, uses function name as key
        "cache_default" - Uses all function arguments as the key
        string - Use kwargs[key] as key
        list - Use [kwargs[k] for k in list] as key
    ``expire``
        Time in seconds before cache expires, or the string "never".
        Defaults to "never"
    ``type``
        Type of cache to use: dbm, memory, file, memcached, or None for
        Beaker's default
    ``query_args``
        Uses the query arguments as the key, defaults to False
    ``cache_headers``
        A tuple of header names indicating response headers that
        will also be cached.
    ``invalidate_on_startup``
        If True, the cache will be invalidated each time the application
        starts or is restarted.
    ``cache_response``
        Determines whether the response at the time beaker_cache is used
        should be cached or not, defaults to True.

        .. note::
            When cache_response is set to False, the cache_headers
            argument is ignored as none of the response is cached.

    If cache_enabled is set to False in the .ini file, then cache is
    disabled globally.

    """
    if invalidate_on_startup:
        starttime = time.time()
    else:
        starttime = None
    cache_headers = set(cache_headers)

    def wrapper(func, *args, **kwargs):
        """Decorator wrapper"""
        pylons = get_pylons(args)
        log.debug("Wrapped with key: %s, expire: %s, type: %s, query_args: %s",
                  key, expire, type, query_args)
        enabled = pylons.config.get("cache_enabled", "True")
        if not asbool(enabled):
            log.debug("Caching disabled, skipping cache lookup")
            return func(*args, **kwargs)

        if key:
            key_dict = kwargs.copy()
            key_dict.update(_make_dict_from_args(func, args))

            ## FIXME: if we can stop there variables from being passed to the
            # controller action (also the Genshi Markup/pickle problem is
            # fixed, see below) then we can use the stock beaker_cache.
            # Remove some system variables that can cause issues while generating cache keys
            [key_dict.pop(x, None) for x in ("pylons", "start_response", "environ")]

            if query_args:
                key_dict.update(pylons.request.GET.mixed())

            if key != "cache_default":
                if isinstance(key, list):
                    key_dict = dict((k, key_dict[k]) for k in key)
                else:
                    key_dict = {key: key_dict[key]}
        else:
            key_dict = None

        self = None
        if args:
            self = args[0]
        namespace, cache_key = create_cache_key(func, key_dict, self)

        if type:
            b_kwargs['type'] = type

        cache_obj = getattr(pylons.app_globals, 'cache', None)
        if not cache_obj:
            cache_obj = getattr(pylons, 'cache', None)
        if not cache_obj:
            raise Exception('No cache object found')
        my_cache = cache_obj.get_cache(namespace, **b_kwargs)

        if expire == "never":
            cache_expire = None
        else:
            cache_expire = expire

        def create_func():
            log.debug("Creating new cache copy with key: %s, type: %s",
                      cache_key, type)
            result = func(*args, **kwargs)
            # This is one of the two changes to the stock beaker_cache
            # decorator
            if hasattr(result, '__html__'):
                # Genshi Markup object, can not be pickled
                result = unicode(result.__html__())
            glob_response = pylons.response
            headers = glob_response.headerlist
            status = glob_response.status
            full_response = dict(headers=headers, status=status,
                                 cookies=None, content=result)
            return full_response

        response = my_cache.get_value(cache_key, createfunc=create_func,
                                      expiretime=cache_expire,
                                      starttime=starttime)
        if cache_response:
            glob_response = pylons.response
            glob_response.headerlist = [header for header in response['headers']
                                        if header[0].lower() in cache_headers]
            glob_response.status = response['status']

        return response['content']
    return decorator(wrapper)

def observable(event):
    """Filter the result of the decorated action through the events observers.

    :param event: An instance of :class:`mediadrop.plugin.events.Event`
        whose observers are called.
    :returns: A decorator function.
    """
    def wrapper(func, *args, **kwargs):
        for observer in event.pre_observers:
            args, kwargs = observer(*args, **kwargs)
        result = func(*args, **kwargs)
        for observer in event.post_observers:
            result = observer(**result)
        return result
    return decorator(wrapper)

def _memoize(func, *args, **kwargs):
    if kwargs: # frozenset is used to ensure hashability
        key = args, frozenset(kwargs.iteritems())
    else:
        key = args
    cache = func.cache # attributed added by memoize
    if key in cache:
        return cache[key]
    else:
        cache[key] = result = func(*args, **kwargs)
        return result

def memoize(func):
    """Decorate this function so cached results are returned indefinitely.

    Copied from docs for the decorator module by Michele Simionato:
    http://micheles.googlecode.com/hg/decorator/documentation.html#the-solution
    """
    func.cache = {}
    return decorator(_memoize, func)

@decorator
def autocommit(func, *args, **kwargs):
    """Handle database transactions for the decorated controller actions.

    This decorator supports firing callbacks immediately after the
    transaction is committed or rolled back. This is useful when some
    external process needs to be called to process some new data, since
    it should only be called once that data is readable by new transactions.

    .. note:: If your callback makes modifications to the database, you must
        manually handle the transaction, or apply the @autocommit decorator
        to the callback itself.

    On the ingress, two attributes are added to the :class:`webob.Request`:

        ``request.commit_callbacks``
            A list of callback functions that should be called immediately
            after the DBSession has been committed by this decorator.

        ``request.rollback_callbacks``
            A list of callback functions that should be called immediately
            after the DBSession has been rolled back by this decorator.

    On the egress, we determine which callbacks should be called, remove
    the above attributes from the request, and then call the appropriate
    callbacks.

    """
    req = request._current_obj()
    req.commit_callbacks = []
    req.rollback_callbacks = []
    try:
        result = func(*args, **kwargs)
    except HTTPException, e:
        if 200 <= e.code < 400:
            _autocommit_commit(req)
        else:
            _autocommit_rollback(req)
        raise
    except:
        _autocommit_rollback(req)
        raise
    else:
        _autocommit_commit(req)
        return result

def _autocommit_commit(req):
    from mediadrop.model.meta import DBSession
    try:
        DBSession.commit()
    except:
        _autocommit_rollback(req)
        raise
    else:
        _autocommit_fire_callbacks(req, req.commit_callbacks)

def _autocommit_rollback(req):
    from mediadrop.model.meta import DBSession
    if not DBSession.is_active:
        return
    DBSession.rollback()
    _autocommit_fire_callbacks(req, req.rollback_callbacks)

def _autocommit_fire_callbacks(req, callbacks):
    # Clear the callback lists from the request so doing crazy things
    # like applying the autocommit decorator to an autocommit callback won't
    # conflict.
    del req.commit_callbacks
    del req.rollback_callbacks
    if callbacks:
        log.debug('@autocommit firing these callbacks: %r', callbacks)
        for cb in callbacks:
            cb()

########NEW FILE########
__FILENAME__ = email
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code contained in this file is licensed under the GPLv3 or
# (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.

"""
Email Helpers

.. todo::

    Clean this module up and use genshi text templates.

.. autofunction:: send

.. autofunction:: send_media_notification

.. autofunction:: send_comment_notification

.. autofunction:: parse_email_string

"""

import smtplib

from pylons import config, request

from mediadrop.lib.helpers import (line_break_xhtml, strip_xhtml, url_for, 
    url_for_media)
from mediadrop.lib.i18n import _

def parse_email_string(string):
    """
    Convert a string of comma separated email addresses to a list of
    separate strings.
    """
    if not string:
        elist = []
    elif ',' in string:
        elist = string.split(',')
        elist = [email.strip() for email in elist]
    else:
        elist = [string]
    return elist

def send(to_addrs, from_addr, subject, body):
    """A simple method to send a simple email.

    :param to_addrs: Comma separated list of email addresses to send to.
    :type to_addrs: unicode

    :param from_addr: Email address to put in the 'from' field
    :type from_addr: unicode

    :param subject: Subject line of the email.
    :type subject: unicode

    :param body: Body text of the email, optionally marked up with HTML.
    :type body: unicode
    """
    smtp_server = config.get('smtp_server', 'localhost')
    server = smtplib.SMTP(smtp_server)
    if isinstance(to_addrs, basestring):
        to_addrs = parse_email_string(to_addrs)

    to_addrs = ", ".join(to_addrs)

    msg = ("To: %(to_addrs)s\n"
           "From: %(from_addr)s\n"
           "Subject: %(subject)s\n\n"
           "%(body)s\n") % locals()

    smtp_username = config.get('smtp_username')
    smtp_password = config.get('smtp_password')
    if smtp_username and smtp_password:
        server.login(smtp_username, smtp_password)

    server.sendmail(from_addr, to_addrs, msg.encode('utf-8'))
    server.quit()


def send_media_notification(media_obj):
    """
    Send a creation notification email that a new Media object has been
    created.

    Sends to the address configured in the 'email_media_uploaded' address,
    if one has been created.

    :param media_obj: The media object to send a notification about.
    :type media_obj: :class:`~mediadrop.model.media.Media` instance
    """
    send_to = request.settings['email_media_uploaded']
    if not send_to:
        # media notification emails are disabled!
        return

    edit_url = url_for(controller='/admin/media', action='edit',
                       id=media_obj.id, qualified=True)

    clean_description = strip_xhtml(line_break_xhtml(line_break_xhtml(media_obj.description)))

    type = media_obj.type
    title = media_obj.title
    author_name = media_obj.author.name
    author_email = media_obj.author.email
    subject = _('New %(type)s: %(title)s') % locals()
    body = _("""A new %(type)s file has been uploaded!

Title: %(title)s

Author: %(author_name)s (%(author_email)s)

Admin URL: %(edit_url)s

Description: %(clean_description)s
""") % locals()

    send(send_to, request.settings['email_send_from'], subject, body)

def send_comment_notification(media_obj, comment):
    """
    Helper method to send a email notification that a comment has been posted.

    Sends to the address configured in the 'email_comment_posted' setting,
    if it is configured.

    :param media_obj: The media object to send a notification about.
    :type media_obj: :class:`~mediadrop.model.media.Media` instance

    :param comment: The newly posted comment.
    :type comment: :class:`~mediadrop.model.comments.Comment` instance
    """
    send_to = request.settings['email_comment_posted']
    if not send_to:
        # Comment notification emails are disabled!
        return

    author_name = media_obj.author.name
    comment_subject = comment.subject
    post_url = url_for_media(media_obj, qualified=True)
    comment_body = strip_xhtml(line_break_xhtml(line_break_xhtml(comment.body)))
    subject = _('New Comment: %(comment_subject)s') % locals()
    body = _("""A new comment has been posted!

Author: %(author_name)s
Post: %(post_url)s

Body: %(comment_body)s
""") % locals()

    send(send_to, request.settings['email_send_from'], subject, body)

def send_support_request(email, url, description, get_vars, post_vars):
    """
    Helper method to send a Support Request email in response to a server
    error.

    Sends to the address configured in the 'email_support_requests' setting,
    if it is configured.

    :param email: The requesting user's email address.
    :type email: unicode

    :param url: The url that the user requested assistance with.
    :type url: unicode

    :param description: The user's description of their problem.
    :type description: unicode

    :param get_vars: The GET variables sent with the failed request.
    :type get_vars: dict of str -> str

    :param post_vars: The POST variables sent with the failed request.
    :type post_vars: dict of str -> str
    """
    send_to = request.settings['email_support_requests']
    if not send_to:
        return

    get_vars = "\n\n  ".join(x + " :  " + get_vars[x] for x in get_vars)
    post_vars = "\n\n  ".join([x + " :  " + post_vars[x] for x in post_vars])
    subject = _('New Support Request: %(email)s') % locals()
    body = _("""A user has asked for support

Email: %(email)s

URL: %(url)s

Description: %(description)s

GET_VARS:
%(get_vars)s


POST_VARS:
%(post_vars)s
""") % locals()

    send(send_to, request.settings['email_send_from'], subject, body)

########NEW FILE########
__FILENAME__ = filesize
# encoding: utf-8
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code in this file is is dual licensed under the MIT license or
# the GPLv3 or (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.

from __future__ import division

from decimal import Decimal

from babel import Locale
from babel.numbers import format_decimal


__all__ = ['format_filesize', 'human_readable_size']

# -----------------------------------------------------------------------------
# Code initially from StackOverflow but modified by Felix Schwarz so the
# formatting aspect is separated from finding the right unit. Also it uses
# Python's Decimal instead of floats
# http://stackoverflow.com/a/1094933/138526
def human_readable_size(value):
    if not isinstance(value, Decimal):
        value = Decimal(str(value))
    for unit in ('B','KB','MB','GB'):
        if value < 1024 and value > -1024:
            return (value, unit)
        value = value / 1024
    return (value, 'TB')
# -----------------------------------------------------------------------------

def format_filesize(size, locale='en'):
    locale = Locale.parse(locale)
    value, unit = human_readable_size(size)
    return format_decimal(value, format=u'#,##0.#', locale=locale) + u'\xa0' + unit


########NEW FILE########
__FILENAME__ = filetypes
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code contained in this file is licensed under the GPLv3 or
# (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.

from mediadrop.lib.i18n import _
from mediadrop.plugin.events import (media_types as registered_media_types,
    observes)

__all__ = [
    'guess_container_format',
    'guess_media_type',
    'guess_mimetype',
    'registered_media_types',
]

AUDIO = u'audio'
VIDEO = u'video'
AUDIO_DESC = u'audio_desc'
CAPTIONS = u'captions'

@observes(registered_media_types)
def register_default_types():
    default_types = [
        (VIDEO, _('Video')),
        (AUDIO, _('Audio')),
        (AUDIO_DESC, _('Audio Description')),
        (CAPTIONS, _('Captions')),
    ]
    for t in default_types:
        yield t

# Mimetypes for all file extensions accepted by the front and backend uploaders
#
# OTHER USES:
# 1) To determine the mimetype to serve, based on a MediaFile's container type.
# 2) In conjunction with the container_lookup dict below to determine the
#    container type for a MediaFile, based on the uploaded file's extension.
#
# XXX: The keys in this dict are sometimes treated as names for container types
#      and sometimes treated as file extensions. Caveat coder.
# TODO: Replace with a more complete list or (even better) change the logic
#       to detect mimetypes from something other than the file extension.
mimetype_lookup = {
    u'flac': u'audio/flac',
    u'mp3':  u'audio/mpeg',
    u'mp4':  u'%s/mp4',
    u'm4a':  u'audio/mp4',
    u'm4v':  u'video/mp4',
    u'ogg':  u'%s/ogg',
    u'oga':  u'audio/ogg',
    u'ogv':  u'video/ogg',
    u'mka':  u'audio/x-matroska',
    u'mkv':  u'video/x-matroska',
    u'3gp':  u'%s/3gpp',
    u'avi':  u'video/avi',
    u'dv':   u'video/x-dv',
    u'flv':  u'video/x-flv', # made up, it's what everyone uses anyway.
    u'mov':  u'video/quicktime',
    u'mpeg': u'%s/mpeg',
    u'mpg':  u'%s/mpeg',
    u'webm': u'%s/webm',
    u'wmv':  u'video/x-ms-wmv',
    u'm3u8': u'application/x-mpegURL',
    u'xml':  u'application/ttml+xml',
    u'srt':  u'text/plain',
}

# Default container format (and also file extension) for each mimetype we allow
# users to upload.
container_lookup = {
    u'audio/flac': u'flac',
    u'audio/mp4': u'mp4',
    u'audio/mpeg': u'mp3',
    u'audio/ogg': u'ogg',
    u'audio/x-matroska': u'mka',
    u'audio/webm': u'webm',
    u'video/3gpp': u'3gp',
    u'video/avi': u'avi',
    u'video/mp4': u'mp4',
    u'video/mpeg': u'mpg',
    u'video/ogg': u'ogg',
    u'video/quicktime': u'mov',
    u'video/x-dv': u'dv',
    u'video/x-flv': u'flv',
    u'video/x-matroska': u'mkv',
    u'video/x-ms-wmv': u'wmv',
    u'video/x-vob': u'vob',
    u'video/webm': u'webm',
    u'application/x-mpegURL': 'm3u8',
    u'application/ttml+xml': u'xml',
    u'text/plain': u'srt',
}

# When media_obj.container doesn't match a key in the mimetype_lookup dict...
default_media_mimetype = 'application/octet-stream'

# File extension map to audio, video or captions
guess_media_type_map = {
    'mp3':  AUDIO,
    'm4a':  AUDIO,
    'flac': AUDIO,
    'mp4':  VIDEO,
    'm4v':  VIDEO,
    'ogg':  VIDEO,
    'oga':  AUDIO,
    'ogv':  VIDEO,
    'mka':  AUDIO,
    'mkv':  VIDEO,
    '3gp':  VIDEO,
    'avi':  VIDEO,
    'dv':   VIDEO,
    'flv':  VIDEO,
    'mov':  VIDEO,
    'mpeg': VIDEO,
    'mpg':  VIDEO,
    'webm': VIDEO,
    'wmv':  VIDEO,
    'xml':  CAPTIONS,
    'srt':  CAPTIONS,
}

def guess_container_format(extension):
    """Return the most likely container format based on the file extension.

    This standardizes to an audio/video-agnostic form of the container, if
    applicable. For example m4v becomes mp4.

    :param extension: the file extension, without a preceding period.
    :type extension: string
    :rtype: string

    """
    mt = guess_mimetype(extension, default=True)
    if mt is True:
        return extension
    return container_lookup.get(mt)

def guess_media_type(extension=None, default=VIDEO):
    """Return the most likely media type based on the container or embed site.

    :param extension: The file extension without a preceding period.
    :param default: Default to video if we don't have any other guess.
    :returns: AUDIO, VIDEO, CAPTIONS, or None

    """
    return guess_media_type_map.get(extension, default)

def guess_mimetype(container, type_=None, default=None):
    """Return the best guess mimetype for the given container.

    If the type (audio or video) is not provided, we make our best guess
    as to which is will probably be, using :func:`guess_container_type`.
    Note that this value is ignored for certain mimetypes: it's useful
    only when a container can be both audio and video.

    :param container: The file extension
    :param type_: AUDIO, VIDEO, or CAPTIONS
    :param default: Default mimetype for when guessing fails
    :returns: A mime string or None.

    """
    if type_ is None:
        type_ = guess_media_type(container)
    mt = mimetype_lookup.get(container, None)
    if mt is None:
        return default or default_media_mimetype
    try:
        return mt % type_
    except (ValueError, TypeError):
        return mt

########NEW FILE########
__FILENAME__ = helpers
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code contained in this file is licensed under the GPLv3 or
# (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.
"""Helper functions

Consists of functions to typically be used within templates, but also
available to Controllers. This module is available to templates as 'h'.
"""
import re
import simplejson
import time
import warnings

from datetime import datetime
from urllib import quote, unquote, urlencode
from urlparse import urlparse

from genshi.core import Stream
from paste.util import mimeparse
from pylons import app_globals, config, request, response, translator
from webhelpers import date, feedgenerator, html, number, misc, text, paginate, containers
from webhelpers.html import tags
from webhelpers.html.builder import literal
from webhelpers.html.converters import format_paragraphs

from mediadrop.lib.auth import viewable_media
from mediadrop.lib.compat import any, md5
from mediadrop.lib.filesize import format_filesize
from mediadrop.lib.i18n import (N_, _, format_date, format_datetime, 
    format_decimal, format_time)
from mediadrop.lib.players import (embed_player, embed_iframe, media_player,
    pick_any_media_file, pick_podcast_media_file)
from mediadrop.lib.thumbnails import thumb, thumb_url
from mediadrop.lib.uri import (best_link_uri, download_uri, file_path,
    pick_uri, pick_uris, web_uri)
from mediadrop.lib.util import (current_url, delete_files, merge_dicts, 
    redirect, url, url_for, url_for_media)
from mediadrop.lib.xhtml import (clean_xhtml, decode_entities, encode_entities,
    excerpt_xhtml, line_break_xhtml, list_acceptable_xhtml, strip_xhtml,
    truncate_xhtml)
from mediadrop.plugin.events import (meta_description, meta_keywords,
    meta_robots_noindex, observes, page_title)

__all__ = [
    # Imports that should be exported:
    'any',
    'clean_xhtml',
    'current_url',
    'config', # is this appropriate to export here?
    'containers',
    'content_type_for_response',
    'date',
    'decode_entities',
    'encode_entities',
    'excerpt_xhtml',
    'feedgenerator',
    'format_date',
    'format_datetime',
    'format_decimal',
    'format_paragraphs',
    'format_time',
    'html',
    'line_break_xhtml',
    'list_acceptable_xhtml',
    'literal',
    'meta_description',
    'meta_keywords', # XXX: imported from mediadrop.plugin.events
    'meta_robots_noindex',
    'misc',
    'number',
    'page_title', # XXX: imported from mediadrop.plugin.events
    'paginate',
    'quote',
    'strip_xhtml',
    'tags',
    'text',
    'thumb', # XXX: imported from  mediadrop.lib.thumbnails, for template use.
    'thumb_url', # XXX: imported from  mediadrop.lib.thumbnails, for template use.
    'truncate_xhtml',
    'unquote',
    'url',
    'url_for',
    'url_for_media',
    'urlencode',
    'urlparse',
    'viewable_media',

    # Locally defined functions that should be exported:
    'append_class_attr',
    'best_translation',
    'can_edit',
    'delete_files',
    'doc_link',
    'duration_from_seconds',
    'duration_to_seconds',
    'filter_library_controls',
    'filter_vulgarity',
    'get_featured_category',
    'gravatar_from_email',
    'is_admin',
    'js',
    'mediadrop_version',
    'pick_any_media_file',
    'pick_podcast_media_file',
    'pretty_file_size',
    'redirect',
    'store_transient_message',
    'truncate',
    'wrap_long_words',
]
__all__.sort()

js_sources = {
    'mootools_more': '/scripts/third-party/mootools-1.2.4.4-more-yui-compressed.js',
    'mootools_core': '/scripts/third-party/mootools-1.2.6-core-2013-01-16.min.js',
}
js_sources_debug = {
    'mootools_more': '/scripts/third-party/mootools-1.2.4.4-more.js',
    'mootools_core': '/scripts/third-party/mootools-1.2.6-core-2013-01-16.js',
}

def js(source):
    if config['debug'] and source in js_sources_debug:
        return url_for(js_sources_debug[source])
    return url_for(js_sources[source])

def mediadrop_version():
    import mediadrop
    return mediadrop.__version__

def duration_from_seconds(total_sec, shortest=True):
    """Return the HH:MM:SS duration for a given number of seconds.

    Does not support durations longer than 24 hours.

    :param total_sec: Number of seconds to convert into hours, mins, sec
    :type total_sec: int
    :param shortest: If True, return the shortest possible timestamp.
        Defaults to True.
    :rtype: unicode
    :returns: String HH:MM:SS, omitting the hours if less than one.

    """
    if not total_sec:
        return u''
    total = time.gmtime(total_sec)
    if not shortest:
        return u'%02d:%02d:%02d' % total[3:6]
    elif total.tm_hour > 0:
        return u'%d:%02d:%02d' % total[3:6]
    else:
        return u'%d:%02d' % total[4:6]

def duration_to_seconds(duration):
    """Return the number of seconds in a given HH:MM:SS.

    Does not support durations longer than 24 hours.

    :param duration: A HH:MM:SS or MM:SS formatted string
    :type duration: unicode
    :rtype: int
    :returns: seconds
    :raises ValueError: If the input doesn't matched the accepted formats

    """
    if not duration:
        return 0
    try:
        total = time.strptime(duration, '%H:%M:%S')
    except ValueError:
        total = time.strptime(duration, '%M:%S')
    return total.tm_hour * 60 * 60 + total.tm_min * 60 + total.tm_sec

def content_type_for_response(available_formats):
    content_type = mimeparse.best_match(
        available_formats,
        request.environ.get('HTTP_ACCEPT', '*/*')
    )
    # force a content-type: if the user agent did not specify any acceptable
    # content types (e.g. just 'text/html' like some bots) we still need to
    # set a content type, otherwise the WebOb will generate an exception
    # AttributeError: You cannot access Response.unicode_body unless charset
    # the only alternative to forcing a "bad" content type would be not to 
    # deliver any content at all - however most bots are just faulty and they
    # requested something like 'sitemap.xml'.
    return content_type or available_formats[0]

def truncate(string, size, whole_word=True):
    """Truncate a plaintext string to roughly a given size (full words).

    :param string: plaintext
    :type string: unicode
    :param size: Max length
    :param whole_word: Whether to prefer truncating at the end of a word.
        Defaults to True.
    :rtype: unicode
    """
    return text.truncate(string, size, whole_word=whole_word)

html_entities = re.compile(r'&(\#x?[0-9a-f]{2,6}|[a-z]{2,10});')
long_words = re.compile(r'((\w|' + html_entities.pattern + '){5})([^\b])')

def wrap_long_words(string, _encode_entities=True):
    """Inject <wbr> periodically to let the browser wrap the string.

    The <wbr /> tag is widely deployed and included in HTML5,
    but it isn't XHTML-compliant. See this for more info:
    http://dev.w3.org/html5/spec/text-level-semantics.html#the-wbr-element

    :type string: unicode
    :rtype: literal
    """
    if _encode_entities:
        string = encode_entities(string)
    def inject_wbr(match):
        groups = match.groups()
        return u'%s<wbr />%s' % (groups[0], groups[-1])
    string = long_words.sub(inject_wbr, string)
    string = u'.<wbr />'.join(string.split('.'))
    return literal(string)

def attrs_to_dict(attrs):
    """Return a dict for any input that Genshi's py:attrs understands.

    For example::

        <link py:match="link" py:if="h.attrs_to_dict(select('@*'))['rel'] == 'alternate'">

    XXX: There is an edge case where a function may be passed in as a result of using a lambda in a
         Tosca Widgets form definition to generate a dynamic container_attr value.
         In this rare case we are checking for a callable, and using that value.

    :param attrs: A collection of attrs
    :type attrs: :class:`genshi.core.Stream`, :class:`genshi.core.Attrs`, :function:
        ``list`` of 2-tuples, ``dict``
    :returns: All attrs
    :rtype: ``dict``
    """
    if isinstance(attrs, Stream):
        attrs = list(attrs)
        attrs = attrs and attrs[0] or []
    if callable(attrs):
        attrs = attrs()
    if not isinstance(attrs, dict):
        attrs = dict(attrs or ())
    return attrs

def append_class_attr(attrs, class_name):
    """Append to the class for any input that Genshi's py:attrs understands.

    This is useful when using XIncludes and you want to append a class
    to the body tag, while still allowing all other tags to remain
    unchanged.

    For example::

        <body py:match="body" py:attrs="h.append_class_attr(select('@*'), 'extra_special')">

    :param attrs: A collection of attrs
    :type attrs: :class:`genshi.core.Stream`, :class:`genshi.core.Attrs`,
        ``list`` of 2-tuples, ``dict``
    :param class_name: The class name to append
    :type class_name: unicode
    :returns: All attrs
    :rtype: ``dict``

    """
    attrs = attrs_to_dict(attrs)
    classes = attrs.get('class', None)
    if not classes:
        attrs['class'] = class_name
        return attrs
    class_list = classes.split(' ')
    if class_name not in class_list:
        class_list.append(class_name)
        attrs['class'] = ' '.join(class_list)
    return attrs

spaces_between_tags = re.compile('>\s+<', re.M)

def get_featured_category():
    from mediadrop.model import Category
    feat_id = request.settings['featured_category']
    if not feat_id:
        return None
    feat_id = int(feat_id)
    return Category.query.get(feat_id)

def filter_library_controls(query, show='latest'):
    from mediadrop.model import Media
    if show == 'latest':
        query = query.order_by(Media.publish_on.desc())
    elif show == 'popular':
        query = query.order_by(Media.popularity_points.desc())
    elif show == 'featured':
        featured_cat = get_featured_category()
        if featured_cat:
            query = query.in_category(featured_cat)
    return query, show

def has_permission(permission_name):
    """Return True if the logged in user has the given permission.

    This always returns false if the given user is not logged in."""
    return request.perm.contains_permission(permission_name)

def is_admin():
    """Return True if the logged in user has the "admin" permission.

    For a default install a user has the "admin" permission if he is a member
    of the "admins" group.

    :returns: Whether or not the current user has "admin" permission.
    :rtype: bool
    """
    return has_permission(u'admin')

def can_edit(item=None):
    """Return True if the logged in user has the "edit" permission.

    For a default install this is true for all members of the "admins" group.

    :param item: unused parameter (deprecated)
    :type item: unimplemented

    :returns: Whether or not the current user has "edit" permission.
    :rtype: bool
    """
    if item is not None:
        warnings.warn(u'"item" parameter for can_edit() is deprecated', 
          DeprecationWarning, stacklevel=2)
    return has_permission(u'edit')

def gravatar_from_email(email, size):
    """Return the URL for a gravatar image matching the provided email address.

    :param email: the email address
    :type email: string or unicode or None
    :param size: the width (or height) of the desired image
    :type size: int
    """
    if email is None:
        email = ''
    # Set your variables here
    gravatar_url = "http://www.gravatar.com/avatar/%s?size=%d" % \
        (md5(email).hexdigest(), size)
    return gravatar_url

def pretty_file_size(size):
    """Return the given file size in the largest possible unit of bytes."""
    if not size:
        return u'-'
    return format_filesize(size, locale=translator.locale)

def store_transient_message(cookie_name, text, time=None, path='/', **kwargs):
    """Store a JSON message dict in the named cookie.

    The cookie will expire at the end of the session, but should be
    explicitly deleted by whoever reads it.

    :param cookie_name: The cookie name for this message.
    :param text: Message text
    :param time: Optional time to report. Defaults to now.
    :param path: Optional cookie path
    :param kwargs: Passed into the JSON dict
    :returns: The message python dict
    :rtype: dict

    """
    time = datetime.now().strftime('%H:%M, %B %d, %Y')
    msg = kwargs
    msg['text'] = text
    msg['time'] = time or datetime.now().strftime('%H:%M, %B %d, %Y')
    new_data = quote(simplejson.dumps(msg))
    response.set_cookie(cookie_name, new_data, path=path)
    return msg

def doc_link(page=None, anchor='', text=N_('Help'), **kwargs):
    """Return a link (anchor element) to the documentation on the project site.

    XXX: Target attribute is not XHTML compliant.
    """
    attrs = {
        'href': 'http://mediadrop.net/docs/user/%s.html#%s' % (page, anchor),
        'target': '_blank',
    }
    if kwargs:
        attrs.update(kwargs)
    attrs_string = ' '.join(['%s="%s"' % (key, attrs[key]) for key in attrs])
    out = '<a %s>%s</a>' % (attrs_string, _(text))
    return literal(out)

@observes(page_title)
def default_page_title(default=None, **kwargs):
    settings = request.settings
    title_order = settings.get('general_site_title_display_order', None)
    site_name = settings.get('general_site_name', default)
    if not default:
        return site_name
    if not title_order:
        return '%s | %s' % (default, site_name)
    elif title_order.lower() == 'append':
        return '%s | %s' % (default, site_name)
    else:
        return '%s | %s' % (site_name, default)

@observes(meta_description)
def default_media_meta_description(default=None, media=None, **kwargs):
    if media and media != 'all' and media.description_plain:
        return truncate(media.description_plain, 249)
    return None

@observes(meta_keywords)
def default_media_meta_keywords(default=None, media=None, **kwargs):
    if media and media != 'all' and media.tags:
        return ', '.join(tag.name for tag in media.tags[:15])
    return None

def filter_vulgarity(text):
    """Return a sanitized version of the given string.

    Words are defined in the Comments settings and are
    replaced with \*'s representing the length of the filtered word.

    :param text: The string to be filtered.
    :type text: str

    :returns: The filtered string.
    :rtype: str

    """
    vulgar_words = request.settings.get('vulgarity_filtered_words', None)
    if vulgar_words:
        words = (word.strip() for word in vulgar_words.split(','))
        word_pattern = '|'.join(re.escape(word) for word in words if word)
        word_expr = re.compile(word_pattern, re.IGNORECASE)
        def word_replacer(matchobj):
            word = matchobj.group(0)
            return '*' * len(word)
        text = word_expr.sub(word_replacer, text)
    return text

def best_translation(a, b):
    """Return the best translation given a preferred and a fallback string.

    If we have a translation for our preferred string 'a' or if we are using
    English, return 'a'. Otherwise, return a translation for the fallback string 'b'.

    :param a: The preferred string to translate.
    :param b: The fallback string to translate.
    :returns: The best translation
    :rtype: string
    """
    translated_a = _(a)
    if a != translated_a or translator.locale.language == 'en':
        return translated_a
    else:
        return _(b)

########NEW FILE########
__FILENAME__ = i18n
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code contained in this file is licensed under the GPLv3 or
# (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.

import logging
import os

from gettext import NullTranslations, translation as gettext_translation

from babel.core import Locale
from babel.dates import (format_date as _format_date,
    format_datetime as _format_datetime, format_time as _format_time)
from babel.numbers import format_decimal as _format_decimal
from babel.support import Translations
from babel.util import LOCALTZ
from pylons import config, request, translator
from pylons.i18n.translation import lazify
from mediadrop.lib.listify import tuplify


__all__ = ['_', 'N_', 'format_date', 'format_datetime', 'format_decimal',
    'format_time']

log = logging.getLogger(__name__)

MEDIADROP = 'mediadrop'
"""The primary MediaDrop domain name."""

class LanguageError(Exception):
    pass

class DomainError(Exception):
    pass

class Translator(object):
    """
    Multi-Domain Translator for a single Locale.

    """
    def __init__(self, locale, locale_dirs):
        """Initialize this translator for the given locale.

        :type locale: :class:`babel.Locale` or ``str``.
        :param locale: The locale to load translations for.
        :type locale_dirs: dict
        :param locale_dirs: A mapping of translation domain names to the
            localedir where they can be found. See :func:`gettext.translation`
            for more details.
        :raises DomainError: If no locale dir has been configured for this
            domain and the fallback is off.
        :raises LanguageError: If no translations could be found for this
            locale in the 'mediadrop' domain and the fallback is off.
        """
        self.locale = locale = Locale.parse(locale)

        # Save configuration required for loading translations
        self._locale_dirs = locale_dirs

        # If the locale is pt_BR, look for both pt_BR and pt translations
        self._languages = [str(locale)]
        if locale.territory:
            self._languages.append(locale.language)

        # Storage for all message catalogs keyed by their domain name
        self._domains = {}

        # Fetch the 'mediadrop' domain immediately & cache a direct ref for perf
        self._mediadrop = self._load_domain(MEDIADROP)

    def install_pylons_global(self):
        """Replace the current pylons.translator SOP with this instance.

        This is specific to the current request.
        """
        environ = request.environ
        environ['pylons.pylons'].translator = self
        environ['paste.registry'].replace(translator, self)

    def _load_domain(self, domain, fallback=True):
        """Load the given domain from one of the pre-configured locale dirs.

        Returns a :class:`gettext.NullTranslations` instance if no
        translations could be found for a non-critical domain. This
        allows untranslated plugins to be rendered in English instead
        of an error being raised.

        :param domain: A domain name.
        :param fallback: An optional flag that, when True, returns a
            :class:`gettext.NullTranslations` instance if no translations
            file could be found for the given language(s).
        :rtype: :class:`gettext.GNUTranslations`
        :returns: The native python translator instance for this domain.
        :raises DomainError: If no locale dir has been configured for this
            domain and the fallback is off.
        :raises LanguageError: If no translations could be found for this
            domain in this locale and the fallback is off.
        """
        locale_dirs = self._locale_dirs.get(domain, None)
        if locale_dirs:
            if isinstance(locale_dirs, basestring):
                locale_dirs = (locale_dirs, )
            translation_list = self._load_translations(domain, locale_dirs, fallback)
            if (not fallback) and len(translation_list) == 0:
                msg = 'No %r translations found for %r in %r.'
                raise LanguageError(msg % (domain, self._languages, locale_dirs))
            translations = Translations(domain=domain)
            for translation in translation_list:
                translations.merge(translation)
        elif fallback:
            translations = NullTranslations()
        else:
            raise DomainError('No localedir specified for domain %r' % domain)
        self._domains[domain] = translations
        return translations

    @tuplify
    def _load_translations(self, domain, locale_dirs, fallback):
        for locale_dir in locale_dirs:
            try:
                yield gettext_translation(domain, locale_dir, self._languages, fallback=fallback)
            except IOError:
                # This only occurs when fallback is false and no translation was
                # found in <locale_dir>.
                pass

    def gettext(self, msgid, domain=None):
        """Translate the given msgid in this translator's locale.

        :type msgid: ``str``
        :param msgid: A byte string to retrieve translations for.
        :type domain: ``str``
        :param domain: An optional domain to use, if not 'mediadrop'.
        :rtype: ``unicode``
        :returns: The translated string, or the original msgid if no
            translation was found.
        """
        if not msgid:
            return u''
        if domain is None and isinstance(msgid, _TranslateableUnicode):
            domain = msgid.domain
        if domain is None or domain == MEDIADROP:
            t = self._mediadrop
        else:
            try:
                t = self._domains[domain]
            except KeyError:
                t = self._load_domain(domain)
        return t.ugettext(msgid)

    def ngettext(self, singular, plural, n, domain=None):
        """Pluralize the given number in this translator's locale.

        :type singular: ``str``
        :param singular: A byte string msgid for the singular form.
        :type plural: ``str``
        :param plural: A byte string msgid for the plural form.
        :type n: ``int``
        :param n: The number of items.
        :type domain: ``str``
        :param domain: An optional domain to use, if not 'mediadrop'.
        :rtype: ``unicode``
        :returns: The translated string, or the original msgid if no
            translation was found.
        """
        if domain is None or domain == MEDIADROP:
            t = self._mediadrop
        else:
            try:
                t = self._domains[domain]
            except KeyError:
                t = self._load_domain(domain)
        return t.ungettext(singular, plural, n)

    def dgettext(self, domain, msgid):
        """Alternate syntax needed for :module:`genshi.filters.i18n`.

        This is only called when the ``i18n:domain`` directive is used."""
        return self.gettext(msgid, domain)

    def dngettext(self, domain, singular, plural, n):
        """Alternate syntax needed for :module:`genshi.filters.i18n`.

        This is only called when the ``i18n:domain`` directive is used."""
        return self.ngettext(singular, plural, n, domain)

    # We always return unicode so these can be simple aliases
    ugettext = gettext
    ungettext = ngettext
    dugettext = dgettext
    dungettext = dngettext


def gettext(msgid, domain=None):
    """Get the translated string for this msgid in the given domain.

    :type msgid: ``str``
    :param msgid: A byte string to retrieve translations for.
    :type domain: ``str``
    :param domain: An optional domain to use, if not 'mediadrop'.
    :rtype: ``unicode``
    :returns: The translated string, or the original msgid if no
        translation was found.
    """
    translator_obj = translator._current_obj()
    if not isinstance(translator_obj, Translator):
        if config['debug']:
            log.warn('_, ugettext, or gettext called with msgid "%s" before '\
                     'pylons.translator has been replaced with our custom '\
                     'version.' % msgid)
        return translator_obj.gettext(msgid)
    return translator_obj.gettext(msgid, domain)
_ = ugettext = gettext

def ngettext(singular, plural, n, domain=None):
    """Pluralize the given number using the current translator.

    This uses the ``pylons.translator`` SOP to access the translator
    appropriate for the current request.

    :type singular: ``str``
    :param singular: A byte string msgid for the singular form.
    :type plural: ``str``
    :param plural: A byte string msgid for the plural form.
    :type n: ``int``
    :param n: The number of items.
    :type domain: ``str``
    :param domain: An optional domain to use, if not 'mediadrop'.
    :rtype: ``unicode``
    :returns: The pluralized translation.
    """
    return translator.ngettext(singular, plural, n, domain)

class _TranslateableUnicode(unicode):
    """A special string that remembers what domain it belongs to.

    This class should not be constructed directly, use :func:`N_` instead.
    If you do choose to call this class directly, be sure the domain
    attribute is set, as the :class:`Translator` assumes it is defined
    for performance reasons.

    """
    __slots__ = ('domain',)

def gettext_noop(msgid, domain=None):
    """Mark the given msgid for later translation.

    Ordinarily this simply returns the original msgid unaltered. Babel's
    message extractors recognize the form ``N_('xyz')`` and include 'xyz'
    in the POT file so that it can be ready for translation when it is
    finally passed through :func:`gettext`.

    If the domain name is given, a slightly altered string is returned:
    a special unicode string stores the domain stored as a property. The
    domain is then retrieved by :func:`gettext` when translation occurs,
    ensuring the translation comes from the correct domain.

    """
    if domain is not None:
        msgid = _TranslateableUnicode(msgid)
        msgid.domain = domain
    return msgid
N_ = gettext_noop

# Lazy functions that evaluate when cast to unicode or str.
# These are not to be confused with N_ which returns the msgid unmodified.
# AFAIK these aren't currently in use and may be removed.
lazy_gettext = lazy_ugettext = lazify(gettext)
lazy_ngettext = lazy_ungettext = lazify(ngettext)


def format_date(date=None, format='medium'):
    """Return a date formatted according to the given pattern.

    This uses the locale of the current request's ``pylons.translator``.

    :param date: the ``date`` or ``datetime`` object; if `None`, the current
                 date is used
    :param format: one of "full", "long", "medium", or "short", or a custom
                   date/time pattern
    :rtype: `unicode`
    """
    return _format_date(date, format, translator.locale)

def format_datetime(datetime=None, format='medium', tzinfo=None):
    """Return a date formatted according to the given pattern.

    This uses the locale of the current request's ``pylons.translator``.

    :param datetime: the `datetime` object; if `None`, the current date and
                     time is used
    :param format: one of "full", "long", "medium", or "short", or a custom
                   date/time pattern
    :param tzinfo: the timezone to apply to the time for display
    :rtype: `unicode`
    """
    if datetime and (datetime.tzinfo is None):
        datetime = datetime.replace(tzinfo=LOCALTZ)
    return _format_datetime(datetime, format, tzinfo, translator.locale)

def format_decimal(number):
    """Return a formatted number (using the correct decimal mark).

    This uses the locale of the current request's ``pylons.translator``.

    :param number: the ``int``, ``float`` or ``decimal`` object
    :rtype: `unicode`
    """
    return _format_decimal(number, locale=translator.locale)

def format_time(time=None, format='medium', tzinfo=None):
    """Return a time formatted according to the given pattern.

    This uses the locale of the current request's ``pylons.translator``.

    :param time: the ``time`` or ``datetime`` object; if `None`, the current
                 time in UTC is used
    :param format: one of "full", "long", "medium", or "short", or a custom
                   date/time pattern
    :param tzinfo: the time-zone to apply to the time for display
    :rtype: `unicode`
    """
    if time and (time.tzinfo is None):
        time = time.replace(tzinfo=LOCALTZ)
    return _format_time(time, format, tzinfo, translator.locale)

def get_available_locales():
    """Yield all the locale names for which we have translations.

    Considers only the 'mediadrop' domain, not plugins.
    """
    i18n_dir = os.path.join(config['pylons.paths']['root'], 'i18n')
    for name in os.listdir(i18n_dir):
        mo_path = os.path.join(i18n_dir, name, 'LC_MESSAGES/mediadrop.mo')
        if os.path.exists(mo_path):
            yield name

########NEW FILE########
__FILENAME__ = js_delivery
# -*- coding: utf-8 -*-
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code in this file is dual licensed under the MIT license or
# the GPLv3 or (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.

from decimal import Decimal

import simplejson
from simplejson.encoder import JSONEncoderForHTML
from sqlalchemy.orm.properties import NoneType

__all__ = ['InlineJS', 'Script', 'Scripts']


class Script(object):
    def __init__(self, url, async=False, key=None):
        self.url = url
        self.async = async
        self.key = key
    
    def render(self):
        async = self.async and ' async="async"' or ''
        return '<script src="%s"%s type="text/javascript"></script>' % (self.url, async)
    
    def __unicode__(self):
        return self.render()
    
    def __repr__(self):
        return 'Script(%r, async=%r, key=%r)' % (self.url, self.async, self.key)
    
    def __eq__(self, other):
        # please note that two Script instances are considered equal when they
        # point to the same URL. The async attribute is not checked, let's not
        # include the same source code twice.
        if not hasattr(other, 'url'):
            return False
        return self.url == other.url
    
    def __ne__(self, other):
        return not (self == other)


class InlineJS(object):
    def __init__(self, code, key=None, params=None):
        self.code = code
        self.key = key
        self.params = params
    
    def as_safe_json(self, s):
        return simplejson.dumps(s, cls=JSONEncoderForHTML)
    
    def _escaped_parameters(self, params):
        escaped_params = dict()
        for key, value in params.items():
            if isinstance(value, (bool, NoneType)):
                # this condition must come first because "1 == True" in Python
                # but "1 !== true" in JavaScript and the "int" check below
                # would pass True unmodified
                escaped_params[key] = self.as_safe_json(value)
            elif isinstance(value, (int, long, float)):
                # use these numeric values directly as format string
                # parameters - they are mapped to JS types perfectly and don't
                # need any escaping.
                escaped_params[key] = value
            elif isinstance(value, (basestring, dict, tuple, list, Decimal)):
                escaped_params[key] = self.as_safe_json(value)
            else:
                klassname = value.__class__.__name__
                raise ValueError('unknown type %s' % klassname)
        return escaped_params
    
    def render(self):
        js = self.code
        if self.params is not None:
            js = self.code % self._escaped_parameters(self.params)
        return '<script type="text/javascript">%s</script>' % js
    
    def __unicode__(self):
        return self.render()
    
    def __repr__(self):
        return 'InlineJS(%r, key=%r)' % (self.code, self.key)
    
    def __eq__(self, other):
        # extremely simple equality check: two InlineJS instances are equal if 
        # the code is exactly the same! No trimming of whitespaces or any other
        # analysis is done.
        if not hasattr(other, 'render'):
            return False
        return self.render() == other.render()
    
    def __ne__(self, other):
        return not (self == other)


class SearchResult(object):
    def __init__(self, item, index):
        self.item = item
        self.index = index


class ResourcesCollection(object):
    def __init__(self, *args):
        self._resources = list(args)
    
    def replace_resource_with_key(self, new_resource):
        result = self._find_resource_with_key(new_resource.key)
        if result is None:
            raise AssertionError('No script with key %r' % new_resource.key)
        self._resources[result.index] = new_resource
    
    def render(self):
        markup = u''
        for resource in self._resources:
            markup = markup + resource.render()
        return markup
    
    def __len__(self):
        return len(self._resources)
    
    # --- internal api ---------------------------------------------------------
    
    def _get(self, resource):
        result = self._find_resource(resource)
        if result is not None:
            return result
        raise AssertionError('Resource %r not found' % resource)
    
    def _get_by_key(self, key):
        result = self._find_resource_with_key(key)
        if result is not None:
            return result
        raise AssertionError('No script with key %r' % key)
    
    def _find_resource(self, a_resource):
        for i, resource in enumerate(self._resources):
            if resource == a_resource:
                return SearchResult(resource, i)
        return None
    
    def _find_resource_with_key(self, key):
        for i, resource in enumerate(self._resources):
            if resource.key == key:
                return SearchResult(resource, i)
        return None


class Scripts(ResourcesCollection):
    def add(self, script):
        if script in self._resources:
            if not hasattr(script, 'async'):
                return
            # in case the same script is added twice and only one should be 
            # loaded asynchronously, use the non-async variant to be on the safe
            # side
            older_script = self._get(script).item
            older_script.async = older_script.async and script.async
            return
        self._resources.append(script)
    
    def add_all(self, *scripts):
        for script in scripts:
            self.add(script)
    
    # --- some interface polishing ---------------------------------------------
    @property
    def scripts(self):
        return self._resources
    
    def replace_script_with_key(self, script):
        self.replace_resource_with_key(script)


########NEW FILE########
__FILENAME__ = listify
# -*- coding: UTF-8 -*-
# Copyright 2014 Felix Schwarz
# The source code in this file is licensed under the MIT license.

from decorator import decorator


__all__ = ['dictify', 'listify', 'setify', 'tuplify']


def listify(func, iterable=list):
    def listify_wrapper(function, *args, **kwargs):
        results = []
        for result in function(*args, **kwargs):
            results.append(result)

        if isinstance(results, iterable):
            return results
        return iterable(results)
    return decorator(listify_wrapper, func)

def tuplify(func):
    return listify(func, iterable=tuple)

def setify(func):
    return listify(func, iterable=set)

def dictify(func):
    return listify(func, iterable=dict)

########NEW FILE########
__FILENAME__ = paginate
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code contained in this file is licensed under the GPLv3 or
# (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.

import inspect
import warnings

from pylons import request, tmpl_context
from webhelpers.paginate import get_wrapper
from webob.multidict import MultiDict
from webhelpers.paginate import Page

from mediadrop.lib.compat import wraps

# TODO: Move the paginate decorator to mediadrop.lib.decorators,
#       and rework it to use the decorators module. This whole
#       module could be greatly simplified, and my CustomPage
#       class can be removed since it is no longer used as of
#       the v0.8.0 frontend redesign.

# FIXME: The following class is taken from TG2.0.3. Find a way to replace it.
# This is not an ideal solution, but avoids the immediate need to rewrite the
# paginate and CustomPage methods below.
# TG license: http://turbogears.org/2.0/docs/main/License.html
class Bunch(dict):
    """A dictionary that provides attribute-style access."""

    def __getitem__(self, key):
        return  dict.__getitem__(self, key)

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            return get_partial_dict(name, self)

    __setattr__ = dict.__setitem__

    def __delattr__(self, name):
        try:
            del self[name]
        except KeyError:
            raise AttributeError(name)

# The following method is taken from TG2.0.3 (tg/util.py).
def get_partial_dict(prefix, dictionary):
    """Given a dictionary and a prefix, return a Bunch, with just items
    that start with prefix

    The returned dictionary will have 'prefix.' stripped so:

    get_partial_dict('prefix', {'prefix.xyz':1, 'prefix.zyx':2, 'xy':3})

    would return:

    {'xyz':1,'zyx':2}
    """

    match = prefix + "."

    new_dict = Bunch([(key.lstrip(match), dictionary[key])
                       for key in dictionary.iterkeys()
                       if key.startswith(match)])
    if new_dict:
        return new_dict
    else:
        raise AttributeError

# FIXME: The following function is taken from TG2.0.3. Find a way to replace it.
# This is not an ideal solution, but avoids the immediate need to rewrite the
# paginate and CustomPage methods below.
# TG license: http://turbogears.org/2.0/docs/main/License.html
def partial(*args, **create_time_kwds):
    func = args[0]
    create_time_args = args[1:]
    def curried_function(*call_time_args, **call_time_kwds):
        args = create_time_args + call_time_args
        kwds = create_time_kwds.copy()
        kwds.update(call_time_kwds)
        return func(*args, **kwds)
    return curried_function

def paginate(name, items_per_page=10, use_prefix=False, items_first_page=None):
    """Paginate a given collection.

    Duplicates and extends the functionality of :func:`tg.decorators.paginate` to:

        * Copy the docstring of the exposed method to the decorator, allowing
          :mod:`sphinx.ext.autodoc` to read docstring.
        * Support our :class:`CustomPage` extension -- used any time
          ``items_first_page`` is provided.

    This decorator is mainly exposing the functionality
    of :func:`webhelpers.paginate`.

    You use this decorator as follows::

     class MyController(object):

         @expose()
         @paginate("collection")
         def sample(self, *args):
             collection = get_a_collection()
             return dict(collection=collection)

    To render the actual pager, use::

      ${tmpl_context.paginators.<name>.pager()}

    where c is the tmpl_context.

    It is possible to have several :func:`paginate`-decorators for
    one controller action to paginate several collections independently
    from each other. If this is desired, don't forget to set the :attr:`use_prefix`-parameter
    to :const:`True`.

    :Parameters:
      name
        the collection to be paginated.
      items_per_page
        the number of items to be rendered. Defaults to 10
      use_prefix
        if True, the parameters the paginate
        decorator renders and reacts to are prefixed with
        "<name>_". This allows for multi-pagination.
      items_first_page
        the number of items to be rendered on the first page. Defaults to the
        value of ``items_per_page``

    """
    prefix = ""
    if use_prefix:
        prefix = name + "_"
    own_parameters = dict(
        page="%spage" % prefix,
        items_per_page="%sitems_per_page" % prefix
        )
    #@decorator
    def _d(f):
        @wraps(f)
        def _w(*args, **kwargs):
            page = int(kwargs.pop(own_parameters["page"], 1))
            real_items_per_page = int(
                    kwargs.pop(
                            own_parameters['items_per_page'],
                            items_per_page))

            # Iterate over all of the named arguments expected by the function f
            # if any of those arguments have values present in the kwargs dict,
            # add the value to the positional args list, and remove it from the
            # kwargs dict
            argvars = inspect.getargspec(f)[0][1:]
            if argvars:
                args = list(args)
                for i, var in enumerate(args):
                    if i>=len(argvars):
                        break;
                    var = argvars[i]
                    if var in kwargs:
                        if i+1 >= len(args):
                            args.append(kwargs[var])
                        else:
                            args[i+1] = kwargs[var]
                        del kwargs[var]

            res = f(*args, **kwargs)
            if isinstance(res, dict) and name in res:
                additional_parameters = MultiDict()
                for key, value in request.params.iteritems():
                    if key not in own_parameters:
                        additional_parameters.add(key, value)

                collection = res[name]

                # Use CustomPage if our extra custom arg was provided
                if items_first_page is not None:
                    page_class = CustomPage
                else:
                    page_class = Page

                page = page_class(
                    collection,
                    page,
                    items_per_page=real_items_per_page,
                    items_first_page=items_first_page,
                    **additional_parameters.dict_of_lists()
                    )
                # wrap the pager so that it will render
                # the proper page-parameter
                page.pager = partial(page.pager,
                        page_param=own_parameters["page"])
                res[name] = page
                # this is a bit strange - it appears
                # as if c returns an empty
                # string for everything it dosen't know.
                # I didn't find that documented, so I
                # just put this in here and hope it works.
                if not hasattr(tmpl_context, 'paginators') or type(tmpl_context.paginators) == str:
                    tmpl_context.paginators = Bunch()
                tmpl_context.paginators[name] = page
            return res
        return _w
    return _d


class CustomPage(Page):
    """A list/iterator of items representing one page in a larger
    collection.

    An instance of the "Page" class is created from a collection of things.
    The instance works as an iterator running from the first item to the
    last item on the given page. The collection can be:

    - a sequence
    - an SQLAlchemy query - e.g.: Session.query(MyModel)
    - an SQLAlchemy select - e.g.: sqlalchemy.select([my_table])

    A "Page" instance maintains pagination logic associated with each
    page, where it begins, what the first/last item on the page is, etc.
    The pager() method creates a link list allowing the user to go to
    other pages.

    **WARNING:** Unless you pass in an item_count, a count will be
    performed on the collection every time a Page instance is created.
    If using an ORM, it's advised to pass in the number of items in the
    collection if that number is known.

    Instance attributes:

    original_collection
        Points to the collection object being paged through

    item_count
        Number of items in the collection

    page
        Number of the current page

    items_per_page
        Maximal number of items displayed on a page

    first_page
        Number of the first page - starts with 1

    last_page
        Number of the last page

    page_count
        Number of pages

    items
        Sequence/iterator of items on the current page

    first_item
        Index of first item on the current page - starts with 1

    last_item
        Index of last item on the current page

    """
    def __init__(self, collection, page=1, items_per_page=20,
        items_first_page=None,
        item_count=None, sqlalchemy_session=None, *args, **kwargs):
        """Create a "Page" instance.

        Parameters:

        collection
            Sequence, SQLAlchemy select object or SQLAlchemy ORM-query
            representing the collection of items to page through.

        page
            The requested page number - starts with 1. Default: 1.

        items_per_page
            The maximal number of items to be displayed per page.
            Default: 20.

        item_count (optional)
            The total number of items in the collection - if known.
            If this parameter is not given then the paginator will count
            the number of elements in the collection every time a "Page"
            is created. Giving this parameter will speed up things.

        sqlalchemy_session (optional)
            If you want to use an SQLAlchemy (0.4) select object as a
            collection then you need to provide an SQLAlchemy session object.
            Select objects do not have a database connection attached so it
            would not be able to execute the SELECT query.

        Further keyword arguments are used as link arguments in the pager().
        """
        # 'page_nr' is deprecated.
        if 'page_nr' in kwargs:
            warnings.warn("'page_nr' is deprecated. Please use 'page' instead.")
            page = kwargs['page_nr']
            del kwargs['page_nr']

        # 'current_page' is also deprecated.
        if 'current_page' in kwargs:
            warnings.warn("'current_page' is deprecated. Please use 'page' instead.")
            page = kwargs['current_page']
            del kwargs['current_page']

        # Safe the kwargs class-wide so they can be used in the pager() method
        self.kwargs = kwargs

        # Save a reference to the collection
        self.original_collection = collection

        # Decorate the ORM/sequence object with __getitem__ and __len__
        # functions to be able to get slices.
        if collection:
            # Determine the type of collection and use a wrapper for ORMs
            self.collection = get_wrapper(collection, sqlalchemy_session)
        else:
            self.collection = []

        # The self.page is the number of the current page.
        # The first page has the number 1!
        try:
            self.page = int(page) # make it int() if we get it as a string
        except ValueError:
            self.page = 1

        self.items_per_page = items_per_page
        self.items_first_page = items_first_page # Adddddd

        # Unless the user tells us how many items the collections has
        # we calculate that ourselves.
        if item_count is not None:
            self.item_count = item_count
        else:
            self.item_count = len(self.collection)

        # Compute the number of the first and last available page
        if self.item_count > 0:
            self.first_page = 1

            if self.items_first_page is None:
                # Go ahead with the default behaviour
                self.page_count = \
                    ((self.item_count - 1) / self.items_per_page) + 1
            else:
                other_items = self.item_count - self.items_first_page
                if other_items <= 0:
                    self.page_count = 1
                else:
                    self.page_count = \
                        ((other_items - 1) / self.items_per_page) + 1 + 1
            self.last_page = self.first_page + self.page_count - 1

            # Make sure that the requested page number is the range of valid pages
            if self.page > self.last_page:
                self.page = self.last_page
            elif self.page < self.first_page:
                self.page = self.first_page

            # Note: the number of items on this page can be less than
            #       items_per_page if the last page is not full
            if self.items_first_page is None:
                # Go ahead with the default behaviour again
                self.first_item = (self.page - 1) * items_per_page + 1
                self.last_item = min(self.first_item + items_per_page - 1, self.item_count)
            else:
                if self.page == 1:
                    self.first_item = 1
                    self.last_item = min(self.items_first_page, self.item_count)
                else:
                    self.first_item = (self.page - 2) * items_per_page + 1 + self.items_first_page
                    self.last_item = min(self.first_item + items_per_page - 1, self.item_count)

            # We subclassed "list" so we need to call its init() method
            # and fill the new list with the items to be displayed on the page.
            # We use list() so that the items on the current page are retrieved
            # only once. Otherwise it would run the actual SQL query everytime
            # .items would be accessed.
            self.items = list(self.collection[self.first_item-1:self.last_item])

            # Links to previous and next page
            if self.page > self.first_page:
                self.previous_page = self.page-1
            else:
                self.previous_page = None

            if self.page < self.last_page:
                self.next_page = self.page+1
            else:
                self.next_page = None

        # No items available
        else:
            self.first_page = None
            self.page_count = 0
            self.last_page = None
            self.first_item = None
            self.last_item = None
            self.previous_page = None
            self.next_page = None
            self.items = []

        # This is a subclass of the 'list' type. Initialise the list now.
        list.__init__(self, self.items)


########NEW FILE########
__FILENAME__ = players
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code contained in this file is licensed under the GPLv3 or
# (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.

from datetime import datetime
from itertools import izip
import logging
from urllib import urlencode

from genshi.builder import Element
from genshi.core import Markup
import simplejson
from sqlalchemy import sql

from mediadrop.forms.admin import players as player_forms
from mediadrop.lib.compat import any
from mediadrop.lib.filetypes import AUDIO, VIDEO, AUDIO_DESC, CAPTIONS
from mediadrop.lib.i18n import N_
from mediadrop.lib.templating import render
from mediadrop.lib.thumbnails import thumb_url
from mediadrop.lib.uri import pick_uris
from mediadrop.lib.util import url_for
#from mediadrop.model.players import fetch_players XXX: Import at EOF
from mediadrop.plugin.abc import AbstractClass, abstractmethod, abstractproperty

log = logging.getLogger(__name__)

HTTP, RTMP = 'http', 'rtmp'

###############################################################################

class AbstractPlayer(AbstractClass):
    """
    Player Base Class that all players must implement.
    """

    name = abstractproperty()
    """A unicode string identifier for this class."""

    display_name = abstractproperty()
    """A unicode display name for the class, to be used in the settings UI."""

    settings_form_class = None
    """An optional :class:`mediadrop.forms.admin.players.PlayerPrefsForm`."""

    default_data = {}
    """An optional default data dictionary for user preferences."""

    supports_resizing = True
    """A flag that allows us to mark the few players that can't be resized.

    Setting this to False ensures that the resize (expand/shrink) controls will
    not be shown in our player control bar.
    """

    @abstractmethod
    def can_play(cls, uris):
        """Test all the given URIs to see if they can be played by this player.

        This is a class method, not an instance or static method.

        :type uris: list
        :param uris: A collection of StorageURI tuples to test.
        :rtype: tuple
        :returns: Boolean result for each of the given URIs.

        """

    def render_markup(self, error_text=None):
        """Render the XHTML markup for this player instance.

        :param error_text: Optional error text that should be included in
            the final markup if appropriate for the player.
        :rtype: ``unicode`` or :class:`genshi.core.Markup`
        :returns: XHTML that will not be escaped by Genshi.

        """
        return error_text or u''

    @abstractmethod
    def render_js_player(self):
        """Render a javascript string to instantiate a javascript player.

        Each player has a client-side component to provide a consistent
        way of initializing and interacting with the player. For more
        information see :file:`mediadrop/public/scripts/mcore/players/`.

        :rtype: ``unicode``
        :returns: A javascript string which will evaluate to an instance
            of a JS player class. For example: ``new mcore.Html5Player()``.

        """

    def __init__(self, media, uris, data=None, width=None, height=None,
                 autoplay=False, autobuffer=False, qualified=False, **kwargs):
        """Initialize the player with the media that it will be playing.

        :type media: :class:`mediadrop.model.media.Media` instance
        :param media: The media object that will be rendered.
        :type uris: list
        :param uris: The StorageURIs this player has said it :meth:`can_play`.
        :type data: dict or None
        :param data: Optional player preferences from the database.
        :type elem_id: unicode, None, Default
        :param elem_id: The element ID to use when rendering. If left
            undefined, a sane default value is provided. Use None to disable.

        """
        self.media = media
        self.uris = uris
        self.data = data or {}
        self.width = width or 400
        self.height = height or 225
        self.autoplay = autoplay
        self.autobuffer = autobuffer
        self.qualified = qualified
        self.elem_id = kwargs.pop('elem_id', '%s-player' % media.slug)

    _width_diff = 0
    _height_diff = 0

    @property
    def adjusted_width(self):
        """Return the desired viewable width + any extra for the player."""
        return self.width + self._width_diff

    @property
    def adjusted_height(self):
        """Return the desired viewable height + the height of the controls."""
        return self.height + self._height_diff

    def get_uris(self, **kwargs):
        """Return a subset of the :attr:`uris` for this player.

        This allows for easy filtering of URIs by feeding any number of
        kwargs to this function. See :func:`mediadrop.lib.uri.pick_uris`.

        """
        return pick_uris(self.uris, **kwargs)
    
    @classmethod
    def inject_in_db(cls, enable_player=False):
        from mediadrop.model import DBSession
        from mediadrop.model.players import players as players_table, PlayerPrefs
        
        prefs = PlayerPrefs()
        prefs.name = cls.name
        prefs.enabled = enable_player
        
        # MySQL does not allow referencing the same table in a subquery
        # (i.e. insert, max): http://stackoverflow.com/a/14302701/138526
        # Therefore we need to alias the table in max
        current_max_query = sql.select([sql.func.max(players_table.alias().c.priority)])
        # sql.func.coalesce == "set default value if func.max does "
        # In case there are no players in the database the current max is NULL. With
        # coalesce we can set a default value.
        new_priority_query = sql.func.coalesce(
            current_max_query.as_scalar()+1,
            1
        )
        prefs.priority = new_priority_query
        
        prefs.created_on = datetime.now()
        prefs.modified_on = datetime.now()
        prefs.data = cls.default_data
        DBSession.add(prefs)
        DBSession.commit()



###############################################################################

class FileSupportMixin(object):
    """
    Mixin that provides a can_play test on a number of common parameters.
    """
    supported_containers = abstractproperty()
    supported_schemes = set([HTTP])
    supported_types = set([AUDIO, VIDEO])

    @classmethod
    def can_play(cls, uris):
        """Test all the given URIs to see if they can be played by this player.

        This is a class method, not an instance or static method.

        :type uris: list
        :param uris: A collection of StorageURI tuples to test.
        :rtype: tuple
        :returns: Boolean result for each of the given URIs.

        """
        return tuple(uri.file.container in cls.supported_containers
                     and uri.scheme in cls.supported_schemes
                     and uri.file.type in cls.supported_types
                     for uri in uris)

class FlashRenderMixin(object):
    """
    Mixin for rendering flash players. Used by embedtypes as well as flash.
    """

    def render_object_embed(self, error_text=None):
        object_tag = self.render_object()
        orig_id = self.elem_id
        self.elem_id = None
        embed_tag = self.render_embed(error_text)
        self.elem_id = orig_id
        return object_tag(embed_tag)

    def render_embed(self, error_text=None):
        swf_url = self.swf_url()
        flashvars = urlencode(self.flashvars())

        tag = Element('embed', type='application/x-shockwave-flash',
                      allowfullscreen='true', allowscriptaccess='always',
                      width=self.adjusted_width, height=self.adjusted_height,
                      src=swf_url, flashvars=flashvars, id=self.elem_id)
        if error_text:
            tag(error_text)
        return tag

    def render_object(self, error_text=None):
        swf_url = self.swf_url()
        flashvars = urlencode(self.flashvars())

        tag = Element('object', type='application/x-shockwave-flash',
                      width=self.adjusted_width, height=self.adjusted_height,
                      data=swf_url, id=self.elem_id)
        tag(Element('param', name='movie', value=swf_url))
        tag(Element('param', name='flashvars', value=flashvars))
        tag(Element('param', name='allowfullscreen', value='true'))
        tag(Element('param', name='allowscriptaccess', value='always'))
        if error_text:
            tag(error_text)
        return tag

    def render_js_player(self):
        """Render a javascript string to instantiate a javascript player.

        Each player has a client-side component to provide a consistent
        way of initializing and interacting with the player. For more
        information see ``mediadrop/public/scripts/mcore/players/``.

        :rtype: ``unicode``
        :returns: A javascript string which will evaluate to an instance
            of a JS player class. For example: ``new mcore.Html5Player()``.

        """
        return Markup("new mcore.FlashPlayer('%s', %d, %d, %s)" % (
            self.swf_url(),
            self.adjusted_width,
            self.adjusted_height,
            simplejson.dumps(self.flashvars()),
        ))

###############################################################################

class AbstractFlashPlayer(FileSupportMixin, FlashRenderMixin, AbstractPlayer):
    """
    Base Class for standard Flash Players.

    This does not typically include flash players from other vendors
    such as embed types.

    """
    supported_containers = set(['mp3', 'mp4', 'flv', 'f4v', 'flac'])

    @abstractmethod
    def flashvars(self):
        """Return a python dict of flashvars for this player."""

    @abstractmethod
    def swf_url(self):
        """Return the flash player URL."""

class AbstractRTMPFlashPlayer(AbstractFlashPlayer):
    """
    Dummy Base Class for Flash Players that can stream over RTMP.

    """
    supported_schemes = set([HTTP, RTMP])

class FlowPlayer(AbstractFlashPlayer):
    """
    FlowPlayer (Flash)
    """
    name = u'flowplayer'
    """A unicode string identifier for this class."""

    display_name = N_(u'Flowplayer')
    """A unicode display name for the class, to be used in the settings UI."""

    supported_schemes = set([HTTP])

    def swf_url(self):
        """Return the flash player URL."""
        return url_for('/scripts/third-party/flowplayer/flowplayer-3.2.14.swf',
                       qualified=self.qualified)

    def flashvars(self):
        """Return a python dict of flashvars for this player."""
        http_uri = self.uris[0]

        playlist = []
        vars = {
            'canvas': {'backgroundColor': '#000', 'backgroundGradient': 'none'},
            'plugins': {
                'controls': {'autoHide': True},
            },
            'clip': {'scaling': 'fit'},
            'playlist': playlist,
        }

        # Show a preview image
        if self.media.type == AUDIO or not self.autoplay:
            playlist.append({
                'url': thumb_url(self.media, 'l', qualified=self.qualified),
                'autoPlay': True,
                'autoBuffer': True,
            })

        playlist.append({
            'url': str(http_uri),
            'autoPlay': self.autoplay,
            'autoBuffer': self.autoplay or self.autobuffer,
        })

        # Flowplayer wants these options passed as an escaped JSON string
        # inside a single 'config' flashvar. When using the flowplayer's
        # own JS, this is automatically done, but since we use Swiff, a
        # SWFObject clone, we have to do this ourselves.
        vars = {'config': simplejson.dumps(vars, separators=(',', ':'))}
        return vars

AbstractFlashPlayer.register(FlowPlayer)

###############################################################################

class AbstractEmbedPlayer(AbstractPlayer):
    """
    Abstract Embed Player for third-party services like YouTube

    Typically embed players will play only their own content, and that is
    the only way such content can be played. Therefore each embed type has
    been given its own :attr:`~mediadrop.lib.uri.StorageURI.scheme` which
    uniquely identifies it.

    For example, :meth:`mediadrop.lib.storage.YoutubeStorage.get_uris`
    returns URIs with a scheme of `'youtube'`, and the special
    :class:`YoutubePlayer` would overload :attr:`scheme` to also be
    `'youtube'`. This would allow the Youtube player to play only those URIs.

    """
    scheme = abstractproperty()
    """The `StorageURI.scheme` which uniquely identifies this embed type."""

    @classmethod
    def can_play(cls, uris):
        """Test all the given URIs to see if they can be played by this player.

        This is a class method, not an instance or static method.

        :type uris: list
        :param uris: A collection of StorageURI tuples to test.
        :rtype: tuple
        :returns: Boolean result for each of the given URIs.

        """
        return tuple(uri.scheme == cls.scheme for uri in uris)

class AbstractIframeEmbedPlayer(AbstractEmbedPlayer):
    """
    Abstract Embed Player for services that provide an iframe player.

    """
    def render_js_player(self):
        """Render a javascript string to instantiate a javascript player.

        Each player has a client-side component to provide a consistent
        way of initializing and interacting with the player. For more
        information see ``mediadrop/public/scripts/mcore/players/``.

        :rtype: ``unicode``
        :returns: A javascript string which will evaluate to an instance
            of a JS player class. For example: ``new mcore.Html5Player()``.

        """
        return Markup("new mcore.IframePlayer()")

class AbstractFlashEmbedPlayer(FlashRenderMixin, AbstractEmbedPlayer):
    """
    Simple Abstract Flash Embed Player

    Provides sane defaults for most flash-based embed players from
    third-party vendors, which typically never need any flashvars
    or special configuration.

    """
    def swf_url(self):
        """Return the flash player URL."""
        return str(self.uris[0])

    def flashvars(self):
        """Return a python dict of flashvars for this player."""
        return {}


class VimeoUniversalEmbedPlayer(AbstractIframeEmbedPlayer):
    """
    Vimeo Universal Player

    This simple player handles media with files that stored using
    :class:`mediadrop.lib.storage.VimeoStorage`.

    This player has seamless HTML5 and Flash support.

    """
    name = u'vimeo'
    """A unicode string identifier for this class."""

    display_name = N_(u'Vimeo')
    """A unicode display name for the class, to be used in the settings UI."""

    scheme = u'vimeo'
    """The `StorageURI.scheme` which uniquely identifies this embed type."""

    def render_markup(self, error_text=None):
        """Render the XHTML markup for this player instance.

        :param error_text: Optional error text that should be included in
            the final markup if appropriate for the player.
        :rtype: ``unicode`` or :class:`genshi.core.Markup`
        :returns: XHTML that will not be escaped by Genshi.

        """
        uri = self.uris[0]
        tag = Element('iframe', src=uri, frameborder=0,
                      width=self.adjusted_width, height=self.adjusted_height)
        return tag

AbstractIframeEmbedPlayer.register(VimeoUniversalEmbedPlayer)


class DailyMotionEmbedPlayer(AbstractIframeEmbedPlayer):
    """
    Daily Motion Universal Player

    This simple player handles media with files that stored using
    :class:`mediadrop.lib.storage.DailyMotionStorage`.

    This player has seamless HTML5 and Flash support.

    """
    name = u'dailymotion'
    """A unicode string identifier for this class."""

    display_name = N_(u'Daily Motion')
    """A unicode display name for the class, to be used in the settings UI."""

    scheme = u'dailymotion'
    """The `StorageURI.scheme` which uniquely identifies this embed type."""

    def render_markup(self, error_text=None):
        """Render the XHTML markup for this player instance.

        :param error_text: Optional error text that should be included in
            the final markup if appropriate for the player.
        :rtype: ``unicode`` or :class:`genshi.core.Markup`
        :returns: XHTML that will not be escaped by Genshi.

        """
        uri = self.uris[0]
        data = urlencode({
            'width': 560, # XXX: The native height for this width is 420
            'theme': 'none',
            'iframe': 1,
            'autoPlay': 0,
            'hideInfos': 1,
            'additionalInfos': 1,
            'foreground': '#F7FFFD',
            'highlight': '#FFC300',
            'background': '#171D1B',
        })
        tag = Element('iframe', src='%s?%s' % (uri, data), frameborder=0,
                      width=self.adjusted_width, height=self.adjusted_height)
        if error_text:
            tag(error_text)
        return tag

AbstractIframeEmbedPlayer.register(DailyMotionEmbedPlayer)


class YoutubePlayer(AbstractIframeEmbedPlayer):
    """
    YouTube Player

    This simple player handles media with files that stored using
    :class:`mediadrop.lib.storage.YoutubeStorage`.

    """
    name = u'youtube'
    """A unicode string identifier for this class."""

    display_name = N_(u'YouTube')
    """A unicode display name for the class, to be used in the settings UI."""

    scheme = u'youtube'
    """The `StorageURI.scheme` which uniquely identifies this embed type."""

    settings_form_class = player_forms.YoutubePlayerPrefsForm
    """An optional :class:`mediadrop.forms.admin.players.PlayerPrefsForm`."""

    default_data = {
        'version': 3,
        'disablekb': 0,
        'autohide': 2,
        'autoplay': 0,
        'iv_load_policy': 1,
        'modestbranding': 1,
        'fs': 1,
        'hd': 0,
        'showinfo': 0,
        'rel': 0,
        'showsearch': 0,
        'wmode': 0,
    }
    _height_diff = 25

    def render_markup(self, error_text=None):
        """Render the XHTML markup for this player instance.

        :param error_text: Optional error text that should be included in
            the final markup if appropriate for the player.
        :rtype: ``unicode`` or :class:`genshi.core.Markup`
        :returns: XHTML that will not be escaped by Genshi.

        """
        uri = self.uris[0]
        
        data = self.data.copy()
        wmode = data.pop('wmode', 0)
        if wmode:
            # 'wmode' is subject to a lot of myths and half-true statements, 
            # these are the best resources I could find:
            # http://stackoverflow.com/questions/886864/differences-between-using-wmode-transparent-opaque-or-window-for-an-embed
            # http://kb2.adobe.com/cps/127/tn_12701.html#main_Using_Window_Mode__wmode__values_
            data['wmode'] = 'opaque'
        data_qs = urlencode(data)
        iframe_attrs = dict(
            frameborder=0,
            width=self.adjusted_width,
            height=self.adjusted_height,
        )
        if bool(data.get('fs')):
            iframe_attrs.update(dict(
                allowfullscreen='',
                # non-standard attributes, required to enable YouTube's HTML5 
                # full-screen capabilities
                mozallowfullscreen='',
                webkitallowfullscreen='',
            ))
        tag = Element('iframe', src='%s?%s' % (uri, data_qs), **iframe_attrs)
        if error_text:
            tag(error_text)
        return tag


AbstractIframeEmbedPlayer.register(YoutubePlayer)


class GoogleVideoFlashPlayer(AbstractFlashEmbedPlayer):
    """
    Google Video Player

    This simple player handles media with files that stored using
    :class:`mediadrop.lib.storage.GoogleVideoStorage`.

    """
    name = u'googlevideo'
    """A unicode string identifier for this class."""

    display_name = N_(u'Google Video')
    """A unicode display name for the class, to be used in the settings UI."""

    scheme = u'googlevideo'
    """The `StorageURI.scheme` which uniquely identifies this embed type."""

    _height_diff = 27

AbstractFlashEmbedPlayer.register(GoogleVideoFlashPlayer)


class BlipTVFlashPlayer(AbstractFlashEmbedPlayer):
    """
    BlipTV Player

    This simple player handles media with files that stored using
    :class:`mediadrop.lib.storage.BlipTVStorage`.

    """
    name = u'bliptv'
    """A unicode string identifier for this class."""

    display_name = N_(u'BlipTV')
    """A unicode display name for the class, to be used in the settings UI."""

    scheme = u'bliptv'
    """The `StorageURI.scheme` which uniquely identifies this embed type."""


AbstractFlashEmbedPlayer.register(BlipTVFlashPlayer)

###############################################################################

class AbstractHTML5Player(FileSupportMixin, AbstractPlayer):
    """
    HTML5 <audio> / <video> tag.

    References:

        - http://dev.w3.org/html5/spec/Overview.html#audio
        - http://dev.w3.org/html5/spec/Overview.html#video
        - http://developer.apple.com/safari/library/documentation/AudioVideo/Conceptual/Using_HTML5_Audio_Video/Introduction/Introduction.html

    """
    supported_containers = set(['mp3', 'mp4', 'ogg', 'webm', 'm3u8'])
    supported_schemes = set([HTTP])

    def __init__(self, *args, **kwargs):
        super(AbstractHTML5Player, self).__init__(*args, **kwargs)
        # Move mp4 files to the front of the list because the iPad has
        # a bug that prevents it from playing but the first file.
        self.uris.sort(key=lambda uri: uri.file.container != 'mp4')
        self.uris.sort(key=lambda uri: uri.file.container != 'm3u8')

    def html5_attrs(self):
        attrs = {
            'id': self.elem_id,
            'controls': 'controls',
            'width': self.adjusted_width,
            'height': self.adjusted_height,
        }
        if self.autoplay:
            attrs['autoplay'] = 'autoplay'
        elif self.autobuffer:
            # This isn't included in the HTML5 spec, but Safari supports it
            attrs['autobuffer'] = 'autobuffer'
        if self.media.type == VIDEO:
            attrs['poster'] = thumb_url(self.media, 'l',
                                        qualified=self.qualified)
        return attrs

    def render_markup(self, error_text=None):
        """Render the XHTML markup for this player instance.

        :param error_text: Optional error text that should be included in
            the final markup if appropriate for the player.
        :rtype: ``unicode`` or :class:`genshi.core.Markup`
        :returns: XHTML that will not be escaped by Genshi.

        """
        attrs = self.html5_attrs()
        tag = Element(self.media.type, **attrs)
        for uri in self.uris:
            # Providing a type attr breaks for m3u8 breaks iPhone playback.
            # Tried: application/x-mpegURL, vnd.apple.mpegURL, video/MP2T
            if uri.file.container == 'm3u8':
                mimetype = None
            else:
                mimetype = uri.file.mimetype
            tag(Element('source', src=uri, type=mimetype))
        if error_text:
            tag(error_text)
        return tag

    def render_js_player(self):
        return Markup("new mcore.Html5Player()")


class HTML5Player(AbstractHTML5Player):
    """
    HTML5 Player Implementation.

    Seperated from :class:`AbstractHTML5Player` to make it easier to subclass
    and provide a custom HTML5 player.

    """
    name = u'html5'
    """A unicode string identifier for this class."""

    display_name = N_(u'Plain HTML5 Player')
    """A unicode display name for the class, to be used in the settings UI."""

AbstractHTML5Player.register(HTML5Player)

###############################################################################

class HTML5PlusFlowPlayer(AbstractHTML5Player):
    """
    HTML5 Player with fallback to FlowPlayer.

    """
    name = u'html5+flowplayer'
    """A unicode string identifier for this class."""

    display_name = N_(u'HTML5 + Flowplayer Fallback')
    """A unicode display name for the class, to be used in the settings UI."""

    settings_form_class = player_forms.HTML5OrFlashPrefsForm
    """An optional :class:`mediadrop.forms.admin.players.PlayerPrefsForm`."""

    default_data = {'prefer_flash': False}
    """An optional default data dictionary for user preferences."""

    supported_containers = HTML5Player.supported_containers \
                         | FlowPlayer.supported_containers
    supported_schemes = HTML5Player.supported_schemes \
                      | FlowPlayer.supported_schemes

    def __init__(self, media, uris, **kwargs):
        super(HTML5PlusFlowPlayer, self).__init__(media, uris, **kwargs)
        self.flowplayer = None
        self.prefer_flash = self.data.get('prefer_flash', False)
        self.uris = [u for u, p in izip(uris, AbstractHTML5Player.can_play(uris)) if p]
        flow_uris = [u for u, p in izip(uris, FlowPlayer.can_play(uris)) if p]
        if flow_uris:
            self.flowplayer = FlowPlayer(media, flow_uris, **kwargs)

    def render_js_player(self):
        flash = self.flowplayer and self.flowplayer.render_js_player()
        html5 = self.uris and super(HTML5PlusFlowPlayer, self).render_js_player()
        if html5 and flash:
            return Markup("new mcore.MultiPlayer([%s, %s])" % \
                (self.prefer_flash and (flash, html5) or (html5, flash)))
        if html5 or flash:
            return html5 or flash
        return None

    def render_markup(self, error_text=None):
        """Render the XHTML markup for this player instance.

        :param error_text: Optional error text that should be included in
            the final markup if appropriate for the player.
        :rtype: ``unicode`` or :class:`genshi.core.Markup`
        :returns: XHTML that will not be escaped by Genshi.

        """
        if self.uris:
            return super(HTML5PlusFlowPlayer, self).render_markup(error_text)
        return error_text or u''

AbstractHTML5Player.register(HTML5PlusFlowPlayer)

###############################################################################

class JWPlayer(AbstractHTML5Player):
    """
    JWPlayer (Flash)
    """
    name = u'jwplayer'
    """A unicode string identifier for this class."""

    display_name = N_(u'JWPlayer')
    """A unicode display name for the class, to be used in the settings UI."""

    supported_containers = AbstractHTML5Player.supported_containers \
                         | AbstractRTMPFlashPlayer.supported_containers \
                         | set(['xml', 'srt'])
#    supported_containers.add('youtube')
    supported_types = set([AUDIO, VIDEO, AUDIO_DESC, CAPTIONS])
    supported_schemes = set([HTTP, RTMP])

    # Height adjustment in pixels to accomodate the control bar and stay 16:9
    _height_diff = 24

    providers = {
        AUDIO: 'sound',
        VIDEO: 'video',
    }

    def __init__(self, media, uris, **kwargs):
        html5_uris = [uri
            for uri, p in izip(uris, AbstractHTML5Player.can_play(uris)) if p]
        flash_uris = [uri
            for uri, p in izip(uris, AbstractRTMPFlashPlayer.can_play(uris)) if p]
        super(JWPlayer, self).__init__(media, html5_uris, **kwargs)
        self.all_uris = uris
        self.flash_uris = flash_uris
        self.rtmp_uris = pick_uris(flash_uris, scheme=RTMP)

    def swf_url(self):
        return url_for('/scripts/third-party/jw_player/player.swf',
                       qualified=self.qualified)

    def js_url(self):
        return url_for('/scripts/third-party/jw_player/jwplayer.min.js',
                       qualified=self.qualified)

    def player_vars(self):
        """Return a python dict of vars for this player."""
        vars = {
            'autostart': self.autoplay,
            'height': self.adjusted_height,
            'width': self.adjusted_width,
            'controlbar': 'bottom',
            'players': [
                # XXX: Currently flash *must* come first for the RTMP/HTTP logic.
                {'type': 'flash', 'src': self.swf_url()},
                {'type': 'html5'},
                {'type': 'download'},
            ],
        }
        playlist = self.playlist()
        plugins = self.plugins()
        if playlist:
            vars['playlist'] = playlist
        if plugins:
            vars['plugins'] = plugins

        # Playlists have 'image's and <video> elements have provide 'poster's,
        # but <audio> elements have no 'poster' attribute. Set an image via JS:
        if self.media.type == AUDIO and not playlist:
            vars['image'] = thumb_url(self.media, 'l', qualified=self.qualified)

        return vars

    def playlist(self):
        if self.uris:
            return None

        if self.rtmp_uris:
            return self.rtmp_playlist()

        uri = self.flash_uris[0]
        return [{
            'image': thumb_url(self.media, 'l', qualified=self.qualified),
            'file': str(uri),
            'duration': self.media.duration,
            'provider': self.providers[uri.file.type],
        }]

    def rtmp_playlist(self):
        levels = []
        item = {'streamer': self.rtmp_uris[0].server_uri,
                'provider': 'rtmp',
                'levels': levels,
                'duration': self.media.duration}
        # If no HTML5 uris exist, no <video> tag will be output, so we have to
        # say which thumb image to use. Otherwise it's unnecessary bytes.
        if not self.uris:
            item['image'] = thumb_url(self.media, 'l', qualified=self.qualified)
        for uri in self.rtmp_uris:
            levels.append({
                'file': uri.file_uri,
                'bitrate': uri.file.bitrate,
                'width': uri.file.width,
            })
        playlist = [item]
        return playlist

    def plugins(self):
        plugins = {}
        audio_desc = pick_uris(self.all_uris, type=AUDIO_DESC)
        captions = pick_uris(self.all_uris, type=CAPTIONS)
        if audio_desc:
            plugins['audiodescription'] = {'file': str(audio_desc[0])}
        if captions:
            plugins['captions'] = {'file': str(captions[0])}
        return plugins

    def flash_override_playlist(self):
        # Use this hook only when HTML5 and RTMP uris exist.
        if self.uris and self.rtmp_uris:
            return self.rtmp_playlist()

    def render_js_player(self):
        vars = simplejson.dumps(self.player_vars())
        flash_playlist = simplejson.dumps(self.flash_override_playlist())
        return Markup("new mcore.JWPlayer(%s, %s)" % (vars, flash_playlist))

    def render_markup(self, error_text=None):
        """Render the XHTML markup for this player instance.

        :param error_text: Optional error text that should be included in
            the final markup if appropriate for the player.
        :rtype: ``unicode`` or :class:`genshi.core.Markup`
        :returns: XHTML that will not be escaped by Genshi.

        """
        if self.uris:
            html5_tag = super(JWPlayer, self).render_markup(error_text)
        else:
            html5_tag = ''
        script_tag = Markup(
            '<script type="text/javascript" src="%s"></script>' % self.js_url())
        return html5_tag + script_tag

AbstractHTML5Player.register(JWPlayer)

###############################################################################

class SublimePlayer(AbstractHTML5Player):
    """
    Sublime Video Player with a builtin flash fallback
    """
    name = u'sublime'
    """A unicode string identifier for this class."""

    display_name = N_(u'Sublime Video Player')
    """A unicode display name for the class, to be used in the settings UI."""

    settings_form_class = player_forms.SublimePlayerPrefsForm
    """An optional :class:`mediadrop.forms.admin.players.PlayerPrefsForm`."""

    default_data = {'script_tag': ''}
    """An optional default data dictionary for user preferences."""

    supported_types = set([VIDEO])
    """Sublime does not support AUDIO at this time."""

    supports_resizing = False
    """A flag that allows us to mark the few players that can't be resized.

    Setting this to False ensures that the resize (expand/shrink) controls will
    not be shown in our player control bar.
    """

    def html5_attrs(self):
        attrs = super(SublimePlayer, self).html5_attrs()
        attrs['class'] = (attrs.get('class', '') + ' sublime').strip()
        return attrs

    def render_js_player(self):
        return Markup('new mcore.SublimePlayer()')

    def render_markup(self, error_text=None):
        """Render the XHTML markup for this player instance.

        :param error_text: Optional error text that should be included in
            the final markup if appropriate for the player.
        :rtype: ``unicode`` or :class:`genshi.core.Markup`
        :returns: XHTML that will not be escaped by Genshi.

        """
        video_tag = super(SublimePlayer, self).render_markup(error_text)
        return video_tag + Markup(self.data['script_tag'])

AbstractHTML5Player.register(SublimePlayer)

###############################################################################

class iTunesPlayer(FileSupportMixin, AbstractPlayer):
    """
    A dummy iTunes Player that allows us to test if files :meth:`can_play`.
    """
    name = u'itunes'
    """A unicode string identifier for this class."""

    display_name = N_(u'iTunes Player')
    """A unicode display name for the class, to be used in the settings UI."""

    supported_containers = set(['mp3', 'mp4'])
    supported_schemes = set([HTTP])

###############################################################################

def preferred_player_for_media(media, **kwargs):
    uris = media.get_uris()

    from mediadrop.model.players import fetch_enabled_players
    # Find the first player that can play any uris
    for player_cls, player_data in fetch_enabled_players():
        can_play = player_cls.can_play(uris)
        if any(can_play):
            break
    else:
        return None

    # Grab just the uris that the chosen player can play
    playable_uris = [uri for uri, plays in izip(uris, can_play) if plays]
    kwargs['data'] = player_data
    return player_cls(media, playable_uris, **kwargs)


def media_player(media, is_widescreen=False, show_like=True, show_dislike=True,
                 show_download=False, show_embed=False, show_playerbar=True,
                 show_popout=True, show_resize=False, show_share=True,
                 js_init=None, **kwargs):
    """Instantiate and render the preferred player that can play this media.

    We make no effort to pick the "best" player here, we simply return
    the first player that *can* play any of the URIs associated with
    the given media object. It's up to the user to declare their own
    preferences wisely.

    Player preferences are fetched from the database and the
    :attr:`mediadrop.model.players.c.data` dict is passed as kwargs to
    :meth:`AbstractPlayer.__init__`.

    :type media: :class:`mediadrop.model.media.Media`
    :param media: A media instance to play.

    :param js_init: Optional function to call after the javascript player
        controller has been instantiated. Example of a function literal:
        ``function(controller){ controller.setFillScreen(true); }``.
        Any function reference can be used as long as it is defined
        in all pages and accepts the JS player controller as its first
        and only argument.

    :param \*\*kwargs: Extra kwargs for :meth:`AbstractPlayer.__init__`.

    :rtype: `str` or `None`
    :returns: A rendered player.
    """
    player = preferred_player_for_media(media, **kwargs)
    return render('players/html5_or_flash.html', {
        'player': player,
        'media': media,
        'uris': media.get_uris(),
        'is_widescreen': is_widescreen,
        'js_init': js_init,
        'show_like': show_like,
        'show_dislike': show_dislike,
        'show_download': show_download,
        'show_embed': show_embed,
        'show_playerbar': show_playerbar,
        'show_popout': show_popout,
        'show_resize': show_resize and (player and player.supports_resizing),
        'show_share': show_share,
    })

def pick_podcast_media_file(media):
    """Return a file playable in the most podcasting client: iTunes.

    :param media: A :class:`~mediadrop.model.media.Media` instance.
    :returns: A :class:`~mediadrop.model.media.MediaFile` object or None
    """
    uris = media.get_uris()
    for i, plays in enumerate(iTunesPlayer.can_play(uris)):
        if plays:
            return uris[i]
    return None

def pick_any_media_file(media):
    """Return a file playable in at least one of the configured players.

    :param media: A :class:`~mediadrop.model.media.Media` instance.
    :returns: A :class:`~mediadrop.model.media.MediaFile` object or None
    """
    uris = media.get_uris()
    from mediadrop.model.players import fetch_enabled_players
    for player_cls, player_data in fetch_enabled_players():
        for i, plays in enumerate(player_cls.can_play(uris)):
            if plays:
                return uris[i]
    return None

def update_enabled_players():
    """Ensure that the encoding status of all media is up to date with the new
    set of enabled players.

    The encoding status of Media objects is dependent on there being an
    enabled player that supports that format. Call this method after changing
    the set of enabled players, to ensure encoding statuses are up to date.
    """
    from mediadrop.model import DBSession, Media
    media = DBSession.query(Media)
    for m in media:
        m.update_status()

def embed_iframe(media, width=400, height=225, frameborder=0, **kwargs):
    """Return an <iframe> tag that loads our universal player.

    :type media: :class:`mediadrop.model.media.Media`
    :param media: The media object that is being rendered, to be passed
        to all instantiated player objects.
    :rtype: :class:`genshi.builder.Element`
    :returns: An iframe element stream.

    """
    src = url_for(controller='/media', action='embed_player', slug=media.slug,
                  qualified=True)
    tag = Element('iframe', src=src, width=width, height=height,
                  frameborder=frameborder, **kwargs)
    # some software is known not to work with self-closing iframe tags 
    # ('<iframe ... />'). Several WordPress instances are affected as well as
    # TWiki http://mediadrop.net/community/topic/embed-iframe-closing-tag
    tag.append('')
    return tag

embed_player = embed_iframe

########NEW FILE########
__FILENAME__ = result
# -*- coding: UTF-8 -*-
# Copyright 2013 Felix Friedrich, Felix Schwarz
# The source code in this file is licensed under the MIT license.


__all__ = ['Result', 'ValidationResult']

class Result(object):
    def __init__(self, value, message=None):
        self.value = value
        self.message = message

    def __repr__(self):
        klassname = self.__class__.__name__
        return '%s(%r, message=%r)' % (klassname, self.value, self.message)

    def __eq__(self, other):
        if isinstance(other, self.value.__class__):
            return self.value == other
        elif hasattr(other, 'value'):
            return self.value == other.value
        return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def __nonzero__(self):
        return self.value


class ValidationResult(Result):
    def __init__(self, value, validated_document=None, errors=None):
        self.value = value
        self.validated_document = validated_document
        self.errors = errors

    def __repr__(self):
        return 'ValidationResult(%r, validated_document=%r, errors=%r)' % (self.value, self.validated_document, self.errors)


########NEW FILE########
__FILENAME__ = facebook
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code contained in this file is licensed under the GPLv3 or
# (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.

__all__ = ['Facebook']

from mediadrop.lib.js_delivery import InlineJS, Script, Scripts

class FacebookSDKScript(InlineJS):
    def __init__(self, app_id, extra_code=None):
        code = u'''
		window.fbAsyncInit = function() {
			FB.init({
				appId  : '%s',
				status : true, // check login status
				cookie : true, // enable cookies to allow the server to access the session
				xfbml  : true  // parse XFBML
			});
			%s
		};''' % (app_id, extra_code or '')
        super(FacebookSDKScript, self).__init__(code, key='fb_async_init')


class Facebook(object):
    def __init__(self, app_id):
        self.app_id = app_id
        self.scripts = Scripts(
            FacebookSDKScript(self.app_id), 
            # '//' is a protocol-relative URL, uses HTTPS if the page uses HTTPS
            Script('//connect.facebook.net/en_US/all.js', async=True)
        )
    
    def init_code(self):
        return u'<div id="fb-root"></div>' + self.scripts.render()


########NEW FILE########
__FILENAME__ = api
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code contained in this file is licensed under the GPLv3 or
# (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.

import logging
import os
import re

from cStringIO import StringIO
from operator import attrgetter
from urllib2 import URLError, urlopen

from mediadrop.lib.compat import defaultdict, SEEK_END
from mediadrop.lib.decorators import memoize
from mediadrop.lib.filetypes import guess_container_format, guess_media_type
from mediadrop.lib.i18n import _
from mediadrop.lib.thumbnails import (create_thumbs_for, has_thumbs,
    has_default_thumbs)
from mediadrop.lib.xhtml import clean_xhtml
from mediadrop.plugin.abc import (AbstractClass, abstractmethod,
    abstractproperty)

__all__ = ['add_new_media_file', 'sort_engines', 'CannotTranscode', 
    'FileStorageEngine', 'StorageError', 'StorageEngine', 
    'UnsuitableEngineError', 'UserStorageError',
]

log = logging.getLogger(__name__)


class StorageError(Exception):
    """Base class for all storage exceptions."""

class UserStorageError(StorageError):
    """A storage error that occurs due to the user input.

    The message will be displayed to the user."""

class UnsuitableEngineError(StorageError):
    """Error to indicate that StorageEngine.parse can't parse its input."""

class CannotTranscode(StorageError):
    """Exception to indicate that StorageEngine.transcode can't or won't transcode a given file."""

class StorageEngine(AbstractClass):
    """
    Base class for all Storage Engine implementations.
    """

    engine_type = abstractproperty()
    """A unique identifying unicode string for the StorageEngine."""

    default_name = abstractproperty()
    """A user-friendly display name that identifies this StorageEngine."""

    is_singleton = abstractproperty()
    """A flag that indicates whether this engine should be added only once."""

    settings_form_class = None
    """Your :class:`mediadrop.forms.Form` class for changing :attr:`_data`."""

    _default_data = {}
    """The default data dictionary to create from the start.

    If you plan to store something in :attr:`_data`, declare it in
    this dict for documentation purposes, if nothing else. Down the
    road, we may validate data against this dict to ensure that only
    known keys are used.
    """

    try_before = []
    """Storage Engines that should :meth:`parse` after this class has.

    This is a list of StorageEngine class objects which is used to
    perform a topological sort of engines. See :func:`sort_engines`
    and :func:`add_new_media_file`.
    """

    try_after = []
    """Storage Engines that should :meth:`parse` before this class has.

    This is a list of StorageEngine class objects which is used to
    perform a topological sort of engines. See :func:`sort_engines`
    and :func:`add_new_media_file`.
    """

    def __init__(self, display_name=None, data=None):
        """Initialize with the given data, or the class defaults.

        :type display_name: unicode
        :param display_name: Name, defaults to :attr:`default_name`.
        :type data: dict
        :param data: The unique parameters of this engine instance.

        """
        self.display_name = display_name or self.default_name
        self._data = data or self._default_data

    def engine_params(self):
        """Return the unique parameters of this engine instance.

        :rtype: dict
        :returns: All the data necessary to create a functionally
            equivalent instance of this engine.

        """
        return self._data

    @property
    @memoize
    def settings_form(self):
        """Return an instance of :attr:`settings_form_class` if defined.

        :rtype: :class:`mediadrop.forms.Form` or None
        :returns: A memoized form instance, since instantiation is expensive.

        """
        if self.settings_form_class is None:
            return None
        return self.settings_form_class()

    @abstractmethod
    def parse(self, file=None, url=None):
        """Return metadata for the given file or URL, or raise an error.

        It is expected that different storage engines will be able to
        extract different metadata.

        **Required metadata keys**:

            * type (generally 'audio' or 'video')

        **Optional metadata keys**:

            * unique_id
            * container
            * display_name
            * title
            * size
            * width
            * height
            * bitrate
            * thumbnail_file
            * thumbnail_url

        :type file: :class:`cgi.FieldStorage` or None
        :param file: A freshly uploaded file object.
        :type url: unicode or None
        :param url: A remote URL string.
        :rtype: dict
        :returns: Any extracted metadata.
        :raises UnsuitableEngineError: If file information cannot be parsed.

        """

    def store(self, media_file, file=None, url=None, meta=None):
        """Store the given file or URL and return a unique identifier for it.

        This method is called with a newly persisted instance of
        :class:`~mediadrop.model.media.MediaFile`. The instance has
        been flushed and therefore has its primary key, but it has
        not yet been committed. An exception here will trigger a rollback.

        This method need not necessarily return anything. If :meth:`parse`
        returned a `unique_id` key, this can return None. It is only when
        this method generates the unique ID, or if it must override the
        unique ID from :meth:`parse`, that it should be returned here.

        This method SHOULD NOT modify the `media_file`. It is provided
        for informational purposes only, so that a unique ID may be
        generated with the primary key from the database.

        :type media_file: :class:`~mediadrop.model.media.MediaFile`
        :param media_file: The associated media file object.
        :type file: :class:`cgi.FieldStorage` or None
        :param file: A freshly uploaded file object.
        :type url: unicode or None
        :param url: A remote URL string.
        :type meta: dict
        :param meta: The metadata returned by :meth:`parse`.
        :rtype: unicode or None
        :returns: The unique ID string. Return None if not generating it here.

        """

    def postprocess(self, media_file):
        """Perform additional post-processing after the save is complete.

        This is called after :meth:`parse`, :meth:`store`, thumbnails
        have been saved and the changes to database flushed.

        :type media_file: :class:`~mediadrop.model.media.MediaFile`
        :param media_file: The associated media file object.
        :returns: None

        """

    def delete(self, unique_id):
        """Delete the stored file represented by the given unique ID.

        :type unique_id: unicode
        :param unique_id: The identifying string for this file.
        :rtype: boolean
        :returns: True if successful, False if an error occurred.

        """

    def transcode(self, media_file):
        """Transcode an existing MediaFile.

        The MediaFile may be stored already by another storage engine.
        New MediaFiles will be created for each transcoding generated by this
        method.

        :type media_file: :class:`~mediadrop.model.media.MediaFile`
        :param media_file: The MediaFile object to transcode.
        :raises CannotTranscode: If this storage engine can't or won't transcode the file.
        :rtype: NoneType
        :returns: Nothing

        """
        raise CannotTranscode('This StorageEngine does not support transcoding.')

    @abstractmethod
    def get_uris(self, media_file):
        """Return a list of URIs from which the stored file can be accessed.

        :type media_file: :class:`~mediadrop.model.media.MediaFile`
        :param media_file: The associated media file object.
        :rtype: list
        :returns: All :class:`StorageURI` tuples for this file.

        """

class FileStorageEngine(StorageEngine):
    """
    Helper subclass that parses file uploads for basic metadata.
    """

    is_singleton = False

    def parse(self, file=None, url=None):
        """Return metadata for the given file or raise an error.

        :type file: :class:`cgi.FieldStorage` or None
        :param file: A freshly uploaded file object.
        :type url: unicode or None
        :param url: A remote URL string.
        :rtype: dict
        :returns: Any extracted metadata.
        :raises UnsuitableEngineError: If file information cannot be parsed.

        """
        if file is None:
            raise UnsuitableEngineError

        filename = os.path.basename(file.filename)
        name, ext = os.path.splitext(filename)
        ext = ext.lstrip('.').lower()
        container = guess_container_format(ext)

        return {
            'type': guess_media_type(container),
            'container': container,
            'display_name': u'%s.%s' % (name, container or ext),
            'size': get_file_size(file.file),
        }

class EmbedStorageEngine(StorageEngine):
    """
    A specialized URL storage engine for URLs that match a certain pattern.
    """

    is_singleton = True

    try_after = [FileStorageEngine]

    url_pattern = abstractproperty()
    """A compiled pattern object that uses named groupings for matches."""

    def parse(self, file=None, url=None):
        """Return metadata for the given URL or raise an error.

        If the given URL matches :attr:`url_pattern` then :meth:`_parse`
        is called with the named matches as kwargs and the result returned.

        :type file: :class:`cgi.FieldStorage` or None
        :param file: A freshly uploaded file object.
        :type url: unicode or None
        :param url: A remote URL string.
        :rtype: dict
        :returns: Any extracted metadata.
        :raises UnsuitableEngineError: If file information cannot be parsed.

        """
        if url is None:
            raise UnsuitableEngineError
        match = self.url_pattern.match(url)
        if match is None:
            raise UnsuitableEngineError
        return self._parse(url, **match.groupdict())

    @abstractmethod
    def _parse(self, url, **kwargs):
        """Return metadata for the given URL that matches :attr:`url_pattern`.

        :type url: unicode
        :param url: A remote URL string.
        :param \*\*kwargs: The named matches from the url match object.
        :rtype: dict
        :returns: Any extracted metadata.

        """

def enabled_engines():
    from mediadrop.model import DBSession
    engines = DBSession.query(StorageEngine)\
        .filter(StorageEngine.enabled == True)\
        .all()
    return list(sort_engines(engines))

def add_new_media_file(media, file=None, url=None):
    """Create a MediaFile instance from the given file or URL.

    This function MAY modify the given media object.

    :type media: :class:`~mediadrop.model.media.Media` instance
    :param media: The media object that this file or URL will belong to.
    :type file: :class:`cgi.FieldStorage` or None
    :param file: A freshly uploaded file object.
    :type url: unicode or None
    :param url: A remote URL string.
    :rtype: :class:`~mediadrop.model.media.MediaFile`
    :returns: A newly created media file instance.
    :raises StorageError: If the input file or URL cannot be
        stored with any of the registered storage engines.

    """
    sorted_engines = enabled_engines()
    for engine in sorted_engines:
        try:
            meta = engine.parse(file=file, url=url)
            log.debug('Engine %r returned meta %r', engine, meta)
            break
        except UnsuitableEngineError:
            log.debug('Engine %r unsuitable for %r/%r', engine, file, url)
            continue
    else:
        raise StorageError(_('Unusable file or URL provided.'), None, None)

    from mediadrop.model import DBSession, MediaFile
    mf = MediaFile()
    mf.storage = engine
    mf.media = media

    mf.type = meta['type']
    mf.display_name = meta.get('display_name', default_display_name(file, url))
    mf.unique_id = meta.get('unique_id', None)

    mf.container = meta.get('container', None)
    mf.size = meta.get('size', None)
    mf.bitrate = meta.get('bitrate', None)
    mf.width = meta.get('width', None)
    mf.height = meta.get('height', None)

    media.files.append(mf)
    DBSession.flush()

    unique_id = engine.store(media_file=mf, file=file, url=url, meta=meta)

    if unique_id:
        mf.unique_id = unique_id
    elif not mf.unique_id:
        raise StorageError('Engine %r returned no unique ID.', engine)

    if not media.duration and meta.get('duration', 0):
        media.duration = meta['duration']
    if not media.description and meta.get('description'):
        media.description = clean_xhtml(meta['description'])
    if not media.title:
        media.title = meta.get('title', None) or mf.display_name
    if media.type is None:
        media.type = mf.type

    if ('thumbnail_url' in meta or 'thumbnail_file' in meta) \
    and (not has_thumbs(media) or has_default_thumbs(media)):
        thumb_file = meta.get('thumbnail_file', None)

        if thumb_file is not None:
            thumb_filename = thumb_file.filename
        else:
            thumb_url = meta['thumbnail_url']
            thumb_filename = os.path.basename(thumb_url)

            # Download the image to a buffer and wrap it as a file-like object
            try:
                temp_img = urlopen(thumb_url)
                thumb_file = StringIO(temp_img.read())
                temp_img.close()
            except URLError, e:
                log.exception(e)

        if thumb_file is not None:
            create_thumbs_for(media, thumb_file, thumb_filename)
            thumb_file.close()

    DBSession.flush()

    engine.postprocess(mf)

    # Try to transcode the file.
    for engine in sorted_engines:
        try:
            engine.transcode(mf)
            log.debug('Engine %r has agreed to transcode %r', engine, mf)
            break
        except CannotTranscode:
            log.debug('Engine %r unsuitable for transcoding %r', engine, mf)
            continue

    return mf

def sort_engines(engines):
    """Yield a topological sort of the given list of engines.

    :type engines: list
    :param engines: Unsorted instances of :class:`StorageEngine`.

    """
    # Partial ordering of engine classes, keys come before values.
    edges = defaultdict(set)

    # Collection of engine instances grouped by their class.
    engine_objs = defaultdict(set)

    # Find all edges between registered engine classes
    for engine in engines:
        engine_cls = engine.__class__
        engine_objs[engine_cls].add(engine)
        for edge_cls in engine.try_before:
            edges[edge_cls].add(engine_cls)
            for edge_cls_implementation in edge_cls:
                edges[edge_cls_implementation].add(engine_cls)
        for edge_cls in engine.try_after:
            edges[engine_cls].add(edge_cls)
            for edge_cls_implementation in edge_cls:
                edges[engine_cls].add(edge_cls_implementation)

    # Iterate over the engine classes
    todo = set(engine_objs.iterkeys())
    while todo:
        # Pull out classes that have no unsatisfied edges
        output = set()
        for engine_cls in todo:
            if not todo.intersection(edges[engine_cls]):
                output.add(engine_cls)
        if not output:
            raise RuntimeError('Circular dependency detected.')
        todo.difference_update(output)

        # Collect all the engine instances we'll be returning in this round,
        # ordering them by ID to give consistent results each time we run this.
        output_instances = []
        for engine_cls in output:
            output_instances.extend(engine_objs[engine_cls])
        output_instances.sort(key=attrgetter('id'))

        for engine in output_instances:
            yield engine

def get_file_size(file):
    if hasattr(file, 'fileno'):
        size = os.fstat(file.fileno())[6]
    else:
        file.seek(0, SEEK_END)
        size = file.tell()
        file.seek(0)
    return size

def default_display_name(file=None, url=None):
    if file is not None:
        return file.filename
    return os.path.basename(url or '')

_filename_filter = re.compile(r'[^a-z0-9_-]')

def safe_file_name(media_file, hint=None):
    """Return a safe filename for the given MediaFile.

    The base path, extension and non-alphanumeric characters are
    stripped from the filename hint so all that remains is what the
    user named the file, to give some idea of what the file contains
    when viewing the filesystem.

    :param media_file: A :class:`~mediadrop.model.media.MediaFile`
        instance that has been flushed to the database.
    :param hint: Optionally the filename provided by the user.
    :returns: A filename with the MediaFile.id, a filtered hint
        and the MediaFile.container.

    """
    if not isinstance(hint, basestring):
        hint = u''
    # Prevent malicious paths like /etc/passwd
    hint = os.path.basename(hint)
    # IE provides full file paths instead of names C:\path\to\file.mp4
    hint = hint.split('\\')[-1]
    hint, orig_ext = os.path.splitext(hint)
    hint = hint.lower()
    # Remove any non-alphanumeric characters
    hint = _filename_filter.sub('', hint)
    if hint:
        hint = u'-%s' % hint
    if media_file.container:
        ext = u'.%s' % media_file.container
    else:
        ext = u''
    return u'%d%s%s' % (media_file.id, hint, ext)


########NEW FILE########
__FILENAME__ = bliptv
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code contained in this file is licensed under the GPLv3 or
# (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.

import logging
import re

from urllib2 import Request, urlopen, URLError

from mediadrop.lib.compat import ElementTree
from mediadrop.lib.filetypes import VIDEO
from mediadrop.lib.i18n import N_, _
from mediadrop.lib.storage.api import EmbedStorageEngine, UserStorageError
from mediadrop.lib.uri import StorageURI

log = logging.getLogger(__name__)

class BlipTVStorage(EmbedStorageEngine):

    engine_type = u'BlipTVStorage'
    """A uniquely identifying unicode string for the StorageEngine."""

    default_name = N_(u'BlipTV')

    url_pattern = re.compile(r'^(http(s?)://)?(\w+\.)?blip.tv/(?P<id>.+)')
    """A compiled pattern object that uses named groupings for matches."""

    def _parse(self, url, id, **kwargs):
        """Return metadata for the given URL that matches :attr:`url_pattern`.

        :type url: unicode
        :param url: A remote URL string.

        :param \*\*kwargs: The named matches from the url match object.

        :rtype: dict
        :returns: Any extracted metadata.

        """
        if '?' in url:
            url += '&skin=api'
        else:
            url += '?skin=api'

        req = Request(url)

        try:
            temp_data = urlopen(req)
            xmlstring = temp_data.read()
            try:
                try:
                    xmltree = ElementTree.fromstring(xmlstring)
                except:
                    temp_data.close()
                    raise
            except SyntaxError:
                raise UserStorageError(
                    _('Invalid BlipTV URL. This video does not exist.'))
        except URLError, e:
            log.exception(e)
            raise

        asset = xmltree.find('payload/asset')
        meta = {'type': VIDEO}
        embed_lookup = asset.findtext('embedLookup')
        meta['unique_id'] = '%s %s' % (id, embed_lookup)
        meta['display_name'] = asset.findtext('title')
        meta['description'] = asset.findtext('description')
        meta['duration'] = int(asset.findtext('mediaList/media/duration') or 0) or None
#        meta['bitrate'] = int(xmltree.findtext('audiobitrate') or 0)\
#                        + int(xmltree.findtext('videobitrate') or 0) or None
        return meta

    def get_uris(self, media_file):
        """Return a list of URIs from which the stored file can be accessed.

        :type media_file: :class:`~mediadrop.model.media.MediaFile`
        :param media_file: The associated media file object.
        :rtype: list
        :returns: All :class:`StorageURI` tuples for this file.

        """
        web_id, embed_lookup = media_file.unique_id.split(' ')
        play_url = 'http://blip.tv/play/%s' % embed_lookup

        # Old blip.tv URLs had a numeric ID in the URL, now they're wordy.
        try:
            web_url = 'http://blip.tv/file/%s' % int(web_id, 10)
        except ValueError:
            web_url = 'http://blip.tv/%s' % web_id

        return [
            StorageURI(media_file, 'bliptv', play_url, None),
            StorageURI(media_file, 'www', web_url, None),
        ]

EmbedStorageEngine.register(BlipTVStorage)

########NEW FILE########
__FILENAME__ = dailymotion
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code contained in this file is licensed under the GPLv3 or
# (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.

import logging
import re
import simplejson

from urllib import urlencode
from urllib2 import Request, urlopen, URLError

from mediadrop import USER_AGENT
from mediadrop.lib.filetypes import VIDEO
from mediadrop.lib.i18n import N_, _
from mediadrop.lib.storage.api import EmbedStorageEngine, UserStorageError
from mediadrop.lib.uri import StorageURI

log = logging.getLogger(__name__)

class DailyMotionStorage(EmbedStorageEngine):

    engine_type = u'DailyMotionStorage'
    """A uniquely identifying unicode string for the StorageEngine."""

    default_name = N_(u'Daily Motion')

    url_pattern = re.compile(
        r'^(http(s?)://)?(\w+\.)?dailymotion.(\w+.?\w*)/video/(?P<id>[^_\?&#]+)_'
    )
    """A compiled pattern object that uses named groupings for matches."""

    def _parse(self, url, **kwargs):
        """Return metadata for the given URL that matches :attr:`url_pattern`.

        :type url: unicode
        :param url: A remote URL string.

        :param \*\*kwargs: The named matches from the url match object.

        :rtype: dict
        :returns: Any extracted metadata.

        """
        id = kwargs['id']
        # Ensure the video uses the .com TLD for the API request.
        url = 'http://www.dailymotion.com/video/%s' % id
        data_url = 'http://www.dailymotion.com/services/oembed?' + \
            urlencode({'format': 'json', 'url': url})

        headers = {'User-Agent': USER_AGENT}
        req = Request(data_url, headers=headers)

        try:
            temp_data = urlopen(req)
            try:
                data_string = temp_data.read()
                if data_string == 'This video cannot be embeded.':
                    raise UserStorageError(
                        _('This DailyMotion video does not allow embedding.'))
                data = simplejson.loads(data_string)
            finally:
                temp_data.close()
        except URLError, e:
            log.exception(e)
            data = {}

        return {
            'unique_id': id,
            'display_name': unicode(data.get('title', u'')),
            'thumbnail_url': data.get('thumbnail_url', None),
            'type': VIDEO,
        }

    def get_uris(self, media_file):
        """Return a list of URIs from which the stored file can be accessed.

        :type media_file: :class:`~mediadrop.model.media.MediaFile`
        :param media_file: The associated media file object.
        :rtype: list
        :returns: All :class:`StorageURI` tuples for this file.

        """
        uid = media_file.unique_id
        play_url = 'http://www.dailymotion.com/embed/video/%s' % uid
        web_url = 'http://www.dailymotion.com/video/%s' % uid
        return [
            StorageURI(media_file, 'dailymotion', play_url, None),
            StorageURI(media_file, 'www', web_url, None),
        ]

EmbedStorageEngine.register(DailyMotionStorage)

########NEW FILE########
__FILENAME__ = ftp
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code contained in this file is licensed under the GPLv3 or
# (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.

import logging
import time
import os

from ftplib import FTP, all_errors as ftp_errors
from urllib2 import HTTPError, urlopen

from formencode import Invalid

from mediadrop.lib.compat import sha1
from mediadrop.lib.i18n import N_, _
from mediadrop.lib.storage.api import FileStorageEngine, safe_file_name
from mediadrop.lib.uri import StorageURI

log = logging.getLogger(__name__)

FTP_SERVER = 'ftp_server'
FTP_USERNAME = 'ftp_username'
FTP_PASSWORD = 'ftp_password'
FTP_UPLOAD_DIR = 'ftp_upload_dir'
FTP_MAX_INTEGRITY_RETRIES = 'ftp_max_integrity_retries'

HTTP_DOWNLOAD_URI = 'http_download_uri'
RTMP_SERVER_URI = 'rtmp_server_uri'

from mediadrop.forms.admin.storage.ftp import FTPStorageForm

class FTPUploadError(Invalid):
    pass

class FTPStorage(FileStorageEngine):

    engine_type = u'FTPStorage'
    """A uniquely identifying string for each StorageEngine implementation."""

    default_name = N_(u'FTP Storage')
    """A user-friendly display name that identifies this StorageEngine."""

    settings_form_class = FTPStorageForm

    _default_data = {
        FTP_SERVER: '',
        FTP_USERNAME: '',
        FTP_PASSWORD: '',
        FTP_UPLOAD_DIR: '',
        FTP_MAX_INTEGRITY_RETRIES: 0,
        HTTP_DOWNLOAD_URI: '',
        RTMP_SERVER_URI: '',
    }

    def store(self, media_file, file=None, url=None, meta=None):
        """Store the given file or URL and return a unique identifier for it.

        :type media_file: :class:`~mediadrop.model.media.MediaFile`
        :param media_file: The associated media file object.

        :type file: :class:`cgi.FieldStorage` or None
        :param file: A freshly uploaded file object.

        :type url: unicode or None
        :param url: A remote URL string.

        :type meta: dict
        :param meta: The metadata returned by :meth:`parse`.

        :rtype: unicode or None
        :returns: The unique ID string. Return None if not generating it here.

        :raises FTPUploadError: If storing the file fails.

        """
        file_name = safe_file_name(media_file, file.filename)

        file_url = os.path.join(self._data[HTTP_DOWNLOAD_URI], file_name)
        upload_dir = self._data[FTP_UPLOAD_DIR]
        stor_cmd = 'STOR ' + file_name

        ftp = self._connect()
        try:
            if upload_dir:
                ftp.cwd(upload_dir)
            ftp.storbinary(stor_cmd, file.file)

            # Raise a FTPUploadError if the file integrity check fails
            # TODO: Delete the file if the integrity check fails
            self._verify_upload_integrity(file.file, file_url)
            ftp.quit()
        except ftp_errors, e:
            log.exception(e)
            ftp.quit()
            msg = _('Could not upload the file from your FTP server: %s')\
                % e.message
            raise FTPUploadError(msg, None, None)

        return file_name

    def delete(self, unique_id):
        """Delete the stored file represented by the given unique ID.

        :type unique_id: unicode
        :param unique_id: The identifying string for this file.

        :rtype: boolean
        :returns: True if successful, False if an error occurred.

        """
        upload_dir = self._data[FTP_UPLOAD_DIR]
        ftp = self._connect()
        try:
            if upload_dir:
                ftp.cwd(upload_dir)
            ftp.delete(unique_id)
            ftp.quit()
            return True
        except ftp_errors, e:
            log.exception(e)
            ftp.quit()
            return False

    def get_uris(self, media_file):
        """Return a list of URIs from which the stored file can be accessed.

        :type media_file: :class:`~mediadrop.model.media.MediaFile`
        :param media_file: The associated media file object.
        :rtype: list
        :returns: All :class:`StorageURI` tuples for this file.

        """
        uid = media_file.unique_id
        url = os.path.join(self._data[HTTP_DOWNLOAD_URI], uid)
        uris = [StorageURI(media_file, 'http', url, None)]
        rtmp_server = self._data.get(RTMP_SERVER_URI, None)
        if rtmp_server:
            uris.append(StorageURI(media_file, 'rtmp', uid, rtmp_server))
        return uris

    def _connect(self):
        """Open a connection to the FTP server."""
        data = self._data
        return FTP(data[FTP_SERVER], data[FTP_USERNAME], data[FTP_PASSWORD])

    def _verify_upload_integrity(self, file, file_url):
        """Download the given file from the URL and compare the SHA1s.

        :type file: :class:`cgi.FieldStorage`
        :param file: A freshly uploaded file object, that has just been
            sent to the FTP server.

        :type file_url: str
        :param file_url: A publicly accessible URL where the uploaded file
            can be downloaded.

        :returns: `True` if the integrity check succeeds or is disabled.

        :raises FTPUploadError: If the file cannot be downloaded after
            the max number of retries, or if the the downloaded file
            doesn't match the original.

        """
        max_tries = int(self._data[FTP_MAX_INTEGRITY_RETRIES])
        if max_tries < 1:
            return True

        file.seek(0)
        orig_hash = sha1(file.read()).hexdigest()

        # Try to download the file. Increase the number of retries, or the
        # timeout duration, if the server is particularly slow.
        # eg: Akamai usually takes 3-15 seconds to make an uploaded file
        #     available over HTTP.
        for i in xrange(max_tries):
            try:
                temp_file = urlopen(file_url)
                dl_hash = sha1(temp_file.read()).hexdigest()
                temp_file.close()
            except HTTPError, http_err:
                # Don't raise the exception now, wait until all attempts fail
                time.sleep(3)
            else:
                # If the downloaded file matches, success! Otherwise, we can
                # be pretty sure that it got corrupted during FTP transfer.
                if orig_hash == dl_hash:
                    return True
                else:
                    msg = _('The file transferred to your FTP server is '\
                            'corrupted. Please try again.')
                    raise FTPUploadError(msg, None, None)

        # Raise the exception from the last download attempt
        msg = _('Could not download the file from your FTP server: %s')\
            % http_err.message
        raise FTPUploadError(msg, None, None)

FileStorageEngine.register(FTPStorage)

########NEW FILE########
__FILENAME__ = googlevideo
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code contained in this file is licensed under the GPLv3 or
# (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.

import logging
import re

from urllib2 import urlopen, URLError

from mediadrop.lib.filetypes import VIDEO
from mediadrop.lib.i18n import N_
from mediadrop.lib.storage.api import EmbedStorageEngine
from mediadrop.lib.uri import StorageURI
from mediadrop.lib.xhtml import decode_entities

log = logging.getLogger(__name__)

class GoogleVideoStorage(EmbedStorageEngine):

    engine_type = u'GoogleVideoStorage'
    """A uniquely identifying unicode string for the StorageEngine."""

    default_name = N_(u'Google Video')

    url_pattern = re.compile(
        r'^(http(s?)://)?video.google.com/videoplay\?(.*&)?docid=(?P<id>-?\d+)'
    )
    """A compiled pattern object that uses named groupings for matches."""

    xml_thumb = re.compile(r'media:thumbnail url="([^"]*)"')
    xml_duration = re.compile(r'duration="([^"]*)"')
    xhtml_title = re.compile(r'<title>([^<]*)</title>')

    def _parse(self, url, **kwargs):
        """Return metadata for the given URL that matches :attr:`url_pattern`.

        :type url: unicode
        :param url: A remote URL string.

        :param \*\*kwargs: The named matches from the url match object.

        :rtype: dict
        :returns: Any extracted metadata.

        """
        id = kwargs['id']
        meta = {
            'unique_id': id,
            'type': VIDEO,
        }

        google_play_url = 'http://video.google.com/videoplay?docid=%s' % id
        google_data_url = 'http://video.google.com/videofeed?docid=%s' % id

        # Fetch the video title from the main video player page
        try:
            temp_data = urlopen(google_play_url)
            data = temp_data.read()
            temp_data.close()
        except URLError, e:
            log.exception(e)
        else:
            title_match = self.xhtml_title.search(data)
            if title_match:
                meta['display_name'] = title_match.group(1)

        # Fetch the meta data from a MediaRSS feed for this video
        try:
            temp_data = urlopen(google_data_url)
            data = temp_data.read()
            temp_data.close()
        except URLError, e:
            log.exception(e)
        else:
            thumb_match = self.xml_thumb.search(data)
            duration_match = self.xml_duration.search(data)
            if thumb_match:
                meta['thumbnail_url'] = decode_entities(thumb_match.group(1))
            if duration_match:
                meta['duration'] = int(duration_match.group(1))

        return meta

    def get_uris(self, media_file):
        """Return a list of URIs from which the stored file can be accessed.

        :type media_file: :class:`~mediadrop.model.media.MediaFile`
        :param media_file: The associated media file object.
        :rtype: list
        :returns: All :class:`StorageURI` tuples for this file.

        """
        uid = media_file.unique_id
        play_url = ('http://video.google.com/googleplayer.swf'
                    '?docid=%s'
                    '&hl=en'
                    '&fs=true') % uid
        web_url = 'http://video.google.com/videoplay?docid=%s' % uid
        return [
            StorageURI(media_file, 'googlevideo', play_url, None),
            StorageURI(media_file, 'www', web_url, None),
        ]

EmbedStorageEngine.register(GoogleVideoStorage)

########NEW FILE########
__FILENAME__ = localfiles
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code contained in this file is licensed under the GPLv3 or
# (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.

import os

from shutil import copyfileobj
from urlparse import urlunsplit

from pylons import config

from mediadrop.forms.admin.storage.localfiles import LocalFileStorageForm
from mediadrop.lib.i18n import N_
from mediadrop.lib.storage.api import safe_file_name, FileStorageEngine
from mediadrop.lib.uri import StorageURI
from mediadrop.lib.util import delete_files, url_for

class LocalFileStorage(FileStorageEngine):

    engine_type = u'LocalFileStorage'
    """A uniquely identifying unicode string for the StorageEngine."""

    default_name = N_(u'Local File Storage')

    settings_form_class = LocalFileStorageForm
    """Your :class:`mediadrop.forms.Form` class for changing :attr:`_data`."""

    _default_data = {
        'path': None,
        'rtmp_server_uri': None,
    }

    def store(self, media_file, file=None, url=None, meta=None):
        """Store the given file or URL and return a unique identifier for it.

        :type media_file: :class:`~mediadrop.model.media.MediaFile`
        :param media_file: The associated media file object.
        :type file: :class:`cgi.FieldStorage` or None
        :param file: A freshly uploaded file object.
        :type url: unicode or None
        :param url: A remote URL string.
        :type meta: dict
        :param meta: The metadata returned by :meth:`parse`.
        :rtype: unicode or None
        :returns: The unique ID string. Return None if not generating it here.

        """
        file_name = safe_file_name(media_file, file.filename)
        file_path = self._get_path(file_name)

        temp_file = file.file
        temp_file.seek(0)
        permanent_file = open(file_path, 'wb')
        copyfileobj(temp_file, permanent_file)
        temp_file.close()
        permanent_file.close()

        return file_name

    def delete(self, unique_id):
        """Delete the stored file represented by the given unique ID.

        :type unique_id: unicode
        :param unique_id: The identifying string for this file.
        :rtype: boolean
        :returns: True if successful, False if an error occurred.

        """
        file_path = self._get_path(unique_id)
        return delete_files([file_path], 'media')

    def get_uris(self, media_file):
        """Return a list of URIs from which the stored file can be accessed.

        :type media_file: :class:`~mediadrop.model.media.MediaFile`
        :param media_file: The associated media file object.
        :rtype: list
        :returns: All :class:`StorageURI` tuples for this file.

        """
        uris = []

        # Remotely accessible URL
        url = url_for(controller='/media', action='serve', id=media_file.id,
                      slug=media_file.media.slug, container=media_file.container,
                      qualified=True)
        uris.append(StorageURI(media_file, 'http', url, None))

        # An optional streaming RTMP URI
        rtmp_server_uri = self._data.get('rtmp_server_uri', None)
        if rtmp_server_uri:
            uris.append(StorageURI(media_file, 'rtmp', media_file.unique_id, rtmp_server_uri))

        # Remotely *download* accessible URL
        url = url_for(controller='/media', action='serve', id=media_file.id,
                      slug=media_file.media.slug, container=media_file.container,
                      qualified=True, download=1)
        uris.append(StorageURI(media_file, 'download', url, None))

        # Internal file URI that will be used by MediaController.serve
        path = urlunsplit(('file', '', self._get_path(media_file.unique_id), '', ''))
        uris.append(StorageURI(media_file, 'file', path, None))

        return uris

    def _get_path(self, unique_id):
        """Return the local file path for the given unique ID.

        This method is exclusive to this engine.
        """
        basepath = self._data.get('path', None)
        if not basepath:
            basepath = config['media_dir']
        return os.path.join(basepath, unique_id)

FileStorageEngine.register(LocalFileStorage)

########NEW FILE########
__FILENAME__ = remoteurls
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code contained in this file is licensed under the GPLv3 or
# (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.

import logging
import os

from mediadrop.forms.admin.storage.remoteurls import RemoteURLStorageForm
from mediadrop.lib.filetypes import guess_container_format, guess_media_type
from mediadrop.lib.i18n import N_, _
from mediadrop.lib.storage.api import (EmbedStorageEngine, StorageEngine,
    UnsuitableEngineError, UserStorageError)
from mediadrop.lib.uri import StorageURI

log = logging.getLogger(__name__)

RTMP_SERVER_URIS = 'rtmp_server_uris'
RTMP_URI_DIVIDER = '$^'

class RemoteURLStorage(StorageEngine):

    engine_type = u'RemoteURLStorage'
    """A uniquely identifying unicode string for the StorageEngine."""

    default_name = N_(u'Remote URLs')

    settings_form_class = RemoteURLStorageForm

    try_after = [EmbedStorageEngine]

    is_singleton = True

    _default_data = {
        RTMP_SERVER_URIS: [],
    }

    def parse(self, file=None, url=None):
        """Return metadata for the given file or raise an error.

        :type file: :class:`cgi.FieldStorage` or None
        :param file: A freshly uploaded file object.
        :type url: unicode or None
        :param url: A remote URL string.
        :rtype: dict
        :returns: Any extracted metadata.
        :raises UnsuitableEngineError: If file information cannot be parsed.

        """
        if url is None:
            raise UnsuitableEngineError

        if url.startswith('rtmp://'):
            known_server_uris = self._data.setdefault(RTMP_SERVER_URIS, ())

            if RTMP_URI_DIVIDER in url:
                # Allow the user to explicitly mark the server/file separation
                parts = url.split(RTMP_URI_DIVIDER)
                server_uri = parts[0].rstrip('/')
                file_uri = ''.join(parts[1:]).lstrip('/')
                if server_uri not in known_server_uris:
                    known_server_uris.append(server_uri)
            else:
                # Get the rtmp server from our list of known servers or fail
                for server_uri in known_server_uris:
                    if url.startswith(server_uri):
                        file_uri = url[len(server_uri.rstrip('/') + '/'):]
                        break
                else:
                    raise UserStorageError(
                        _('This RTMP server has not been configured. Add it '
                          'by going to Settings > Storage Engines > '
                          'Remote URLs.'))
            unique_id = ''.join((server_uri, RTMP_URI_DIVIDER, file_uri))
        else:
            unique_id = url

        filename = os.path.basename(url)
        name, ext = os.path.splitext(filename)
        ext = unicode(ext).lstrip('.').lower()

        container = guess_container_format(ext)

        # FIXME: Replace guess_container_format with something that takes
        #        into consideration the supported formats of all the custom
        #        players that may be installed.
#        if not container or container == 'unknown':
#            raise UnsuitableEngineError

        return {
            'type': guess_media_type(ext),
            'container': container,
            'display_name': u'%s.%s' % (name, container or ext),
            'unique_id': unique_id,
        }

    def get_uris(self, media_file):
        """Return a list of URIs from which the stored file can be accessed.

        :type media_file: :class:`~mediadrop.model.media.MediaFile`
        :param media_file: The associated media file object.
        :rtype: list
        :returns: All :class:`StorageURI` tuples for this file.

        """
        uid = media_file.unique_id
        if uid.startswith('rtmp://'):
            sep_index = uid.find(RTMP_URI_DIVIDER) # can raise ValueError
            if sep_index < 0:
                log.warn('File %r has an invalidly formatted unique ID for RTMP.', media_file)
                return []
            server_uri = uid[:sep_index]
            file_uri = uid[sep_index + len(RTMP_URI_DIVIDER):]
            return [StorageURI(media_file, 'rtmp', file_uri, server_uri)]
        return [StorageURI(media_file, 'http', uid, None)]

StorageEngine.register(RemoteURLStorage)

########NEW FILE########
__FILENAME__ = youtube_storage_test
# -*- coding: utf-8 -*-
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code contained in this file is licensed under the GPLv3 or
# (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.

from mediadrop.lib.storage.youtube import YoutubeStorage
from mediadrop.lib.test.pythonic_testcase import *


class YoutubeStorageTest(PythonicTestCase):
    
    def youtube_id(self, url):
        match = YoutubeStorage.url_pattern.match(url)
        if match is None:
            return None
        return match.group('id')
    
    def assert_can_parse(self, url):
        assert_equals('RIk8A4TrCIY', self.youtube_id(url))
    
    def test_can_parse_youtube_com_watch_link(self):
        self.assert_can_parse('http://youtube.com/watch?v=RIk8A4TrCIY')
        self.assert_can_parse('http://www.youtube.com/watch?v=RIk8A4TrCIY')
        self.assert_can_parse('http://www.youtube.com/watch?feature=player_embedded&v=RIk8A4TrCIY')
    
    def test_accepts_https(self):
        self.assert_can_parse('https://youtube.com/watch?v=RIk8A4TrCIY')
        self.assert_can_parse('https://www.youtube.com/watch?v=RIk8A4TrCIY')
    
    def test_accepts_embeded_player(self):
        self.assert_can_parse('http://youtube.com/embed/RIk8A4TrCIY')
        self.assert_can_parse('https://www.youtube.com/embed/RIk8A4TrCIY')


import unittest

def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(YoutubeStorageTest))
    return suite
    
if __name__ == '__main__':
    unittest.main(defaultTest='suite')

########NEW FILE########
__FILENAME__ = vimeo
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code contained in this file is licensed under the GPLv3 or
# (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.

import logging
import re
import simplejson

from urllib2 import Request, urlopen, URLError

from mediadrop import USER_AGENT
from mediadrop.lib.filetypes import VIDEO
from mediadrop.lib.i18n import N_
from mediadrop.lib.storage.api import EmbedStorageEngine
from mediadrop.lib.uri import StorageURI

log = logging.getLogger(__name__)

class VimeoStorage(EmbedStorageEngine):

    engine_type = u'VimeoStorage'
    """A uniquely identifying unicode string for the StorageEngine."""

    default_name = N_(u'Vimeo')

    url_pattern = re.compile(r'^(http(s?)://)?(\w+\.)?vimeo.com/(?P<id>\d+)')
    """A compiled pattern object that uses named groupings for matches."""

    def _parse(self, url, **kwargs):
        """Return metadata for the given URL that matches :attr:`url_pattern`.

        :type url: unicode
        :param url: A remote URL string.

        :param \*\*kwargs: The named matches from the url match object.

        :rtype: dict
        :returns: Any extracted metadata.

        """
        id = kwargs['id']
        vimeo_data_url = 'http://vimeo.com/api/v2/video/%s.%s' % (id, 'json')

        # Vimeo API requires us to give a user-agent, to avoid 403 errors.
        headers = {'User-Agent': USER_AGENT}
        req = Request(vimeo_data_url, headers=headers)

        try:
            temp_data = urlopen(req)
            try:
                data = simplejson.loads(temp_data.read())[0]
            finally:
                temp_data.close()
        except URLError, e:
            log.exception(e)
            data = {}

        return {
            'unique_id': id,
            'description': unicode(data.get('description', u'')),
            'duration': int(data.get('duration', 0)),
            'display_name': unicode(data.get('title', u'')),
            'thumbnail_url': data.get('thumbnail_large', None),
            'type': VIDEO,
        }

    def get_uris(self, media_file):
        """Return a list of URIs from which the stored file can be accessed.

        :type media_file: :class:`~mediadrop.model.media.MediaFile`
        :param media_file: The associated media file object.
        :rtype: list
        :returns: All :class:`StorageURI` tuples for this file.

        """
        uid = media_file.unique_id
        play_url = 'http://player.vimeo.com/video/%s' % uid
        web_url = 'http://vimeo.com/%s' % uid
        return [
            StorageURI(media_file, 'vimeo', play_url, None),
            StorageURI(media_file, 'www', web_url, None),
        ]

EmbedStorageEngine.register(VimeoStorage)

########NEW FILE########
__FILENAME__ = youtube
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code contained in this file is licensed under the GPLv3 or
# (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.

import re

from operator import attrgetter
from urllib import urlencode

import gdata.service
import gdata.youtube
import gdata.youtube.service

from mediadrop.lib.compat import max
from mediadrop.lib.filetypes import VIDEO
from mediadrop.lib.i18n import N_, _
from mediadrop.lib.storage.api import EmbedStorageEngine, UserStorageError
from mediadrop.lib.uri import StorageURI

class YoutubeStorage(EmbedStorageEngine):

    engine_type = u'YoutubeStorage'
    """A uniquely identifying unicode string for the StorageEngine."""

    default_name = N_(u'YouTube')

    url_pattern = re.compile(r'''
        ^(http(s?)://)?                         # http:// or https://
        (youtu\.be/                             # youtu.be short url OR:
        |(\w+\.)?youtube\.com/watch\?(.*&)?v=   # www.youtube.com/watch?v= OR
        |(\w+\.)?youtube\.com/embed/)           # www.youtube.com/embed/ OR
        (?P<id>[^&#]+)                          # video unique ID
    ''', re.VERBOSE)
    """A compiled pattern object that uses named groupings for matches."""

    def _parse(self, url, **kwargs):
        """Return metadata for the given URL that matches :attr:`url_pattern`.

        :type url: unicode
        :param url: A remote URL string.

        :param \*\*kwargs: The named matches from the url match object.

        :rtype: dict
        :returns: Any extracted metadata.

        """
        id = kwargs['id']

        yt_service = gdata.youtube.service.YouTubeService()
        yt_service.ssl = False

        try:
            entry = yt_service.GetYouTubeVideoEntry(video_id=id)
        except gdata.service.RequestError, request_error:
            e = request_error.args[0]
            if e['status'] == 403 and e['body'] == 'Private video':
                raise UserStorageError(
                    _('This video is private and cannot be embedded.'))
            elif e['status'] == 400 and e['body'] == 'Invalid id':
                raise UserStorageError(
                    _('Invalid YouTube URL. This video does not exist.'))
            raise UserStorageError(_('YouTube Error: %s') % e['body'])

        try:
            thumb = max(entry.media.thumbnail, key=attrgetter('width')).url
        except (AttributeError, ValueError, TypeError):
            # At least one video has been found to return no thumbnails.
            # Try adding this later http://www.youtube.com/watch?v=AQTYoRpCXwg
            thumb = None

        # Some videos at some times do not return a complete response, and these
        # attributes are missing. We can just ignore this.
        try:
            description = unicode(entry.media.description.text, 'utf-8') or None
        except (AttributeError, ValueError, TypeError, UnicodeDecodeError):
            description = None
        try:
            title = unicode(entry.media.title.text, 'utf-8')
        except (AttributeError, ValueError, TypeError, UnicodeDecodeError):
            title = None
        try:
            duration = int(entry.media.duration.seconds)
        except (AttributeError, ValueError, TypeError):
            duration = None

        return {
            'unique_id': id,
            'duration': duration,
            'display_name': title,
            'description': description,
            'thumbnail_url': thumb,
            'type': VIDEO,
        }

    def get_uris(self, media_file):
        """Return a list of URIs from which the stored file can be accessed.

        :type media_file: :class:`~mediadrop.model.media.MediaFile`
        :param media_file: The associated media file object.
        :rtype: list
        :returns: All :class:`StorageURI` tuples for this file.

        """
        params = self._data.get('player_params', {})
        params = dict((k, int(v)) for k, v in params.iteritems())
        play_url = 'http://youtube%s.com/embed/%s?%s' % (
            self._data.get('nocookie', False) and '-nocookie' or '',
            media_file.unique_id,
            urlencode(params, True),
        )
        web_url = 'http://youtube.com/watch?v=%s' % media_file.unique_id
        return [
            StorageURI(media_file, 'youtube', play_url, None),
            StorageURI(media_file, 'www', web_url, None),
        ]

EmbedStorageEngine.register(YoutubeStorage)

########NEW FILE########
__FILENAME__ = templating
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code contained in this file is licensed under the GPLv3 or
# (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.

import logging
import os.path

from genshi import Markup, XML
from genshi.output import XHTMLSerializer
from genshi.template import TemplateError, NewTextTemplate
from genshi.template.loader import (directory,
    TemplateLoader as _TemplateLoader, TemplateNotFound)
from pylons import app_globals, config, request, response, tmpl_context, translator

from mediadrop.lib.i18n import N_

__all__ = [
    'TemplateLoader',
    'XHTMLPlusSerializer',
    'render',
    'render_stream',
]

log = logging.getLogger(__name__)

def tmpl_globals():
    """Create and return a dictionary of global variables for all templates.

    This function was adapted from :func:`pylons.templating.pylons_globals`
    to better suite our needs. In particular we inject our own gettext
    functions and get a performance boost from following the translator SOP
    once here instead of on every gettext call.

    """
    conf = config._current_obj()
    g = conf['pylons.app_globals']
    c = tmpl_context._current_obj()
    t = translator._current_obj()
    req = request._current_obj()
    return {
        'config': conf,
        'c': c,
        'tmpl_context': c,
        'g': g,
        'app_globals': g,
        'h': conf['pylons.h'],
        'request': req,
        'settings': req.settings,
        'response': response, # don't eval the SOP because this is rarely used
        'translator': t,
        'ngettext': t.ngettext,
        'ungettext': t.ungettext, # compat with standard pylons_globals()
        '_': t.gettext,
        'N_': N_,
        'XML': XML,
    }

def render(template, tmpl_vars=None, method=None):
    """Generate a markup stream from the given template and vars.

    :param template: A template path.
    :param tmpl_vars: A dict of variables to pass into the template.
    :param method: Optional serialization method for Genshi to use.
        If None, we don't serialize the markup stream into a string.
        Provide 'auto' to use the best guess. See :func:`render_stream`.
    :rtype: :class:`genshi.Stream` or :class:`genshi.Markup`
    :returns: An iterable markup stream, or a serialized markup string
        if `method` was not None.

    """
    if tmpl_vars is None:
        tmpl_vars = {}
    assert isinstance(tmpl_vars, dict), \
        'tmpl_vars must be a dict or None, given: %r' % tmpl_vars

    tmpl_vars.update(tmpl_globals())

    # Pass in all the plugin templates that will manipulate this template
    # The idea is that these paths should be <xi:include> somewhere in the
    # top of the template file.
    plugin_templates = app_globals.plugin_mgr.match_templates(template)
    tmpl_vars['plugin_templates'] = plugin_templates

    # Grab a template reference and apply the template context
    if method == 'text':
        tmpl = app_globals.genshi_loader.load(template, cls=NewTextTemplate)
    else:
        tmpl = app_globals.genshi_loader.load(template)

    stream = tmpl.generate(**tmpl_vars)

    if method is None:
        return stream
    else:
        return render_stream(stream, method=method, template_name=template)

def render_stream(stream, method='auto', template_name=None):
    """Render the given stream to a unicode Markup string.

    We substitute the standard XHTMLSerializer with our own
    :class:`XHTMLPlusSerializer` which is (more) HTML5-aware.

    :type stream: :class:`genshi.Stream`
    :param stream: An iterable markup stream.
    :param method: The serialization method for Genshi to use.
        If given 'auto', the default value, we assume xhtml unless
        a template name is given with an xml extension.
    :param template_name: Optional template name which we use only to
        guess what method to use, if one hasn't been explicitly provided.
    :rtype: :class:`genshi.Markup`
    :returns: A subclassed `unicode` object.

    """
    if method == 'auto':
        if template_name and template_name.endswith('.xml'):
            method = 'xml'
        else:
            method = 'xhtml'

    if method == 'xhtml':
        method = XHTMLPlusSerializer

    return Markup(stream.render(method=method, encoding=None))

class XHTMLPlusSerializer(XHTMLSerializer):
    """
    XHTML+HTML5 Serializer that produces XHTML text from an event stream.

    This serializer is aware that <source/> tags are empty, which is
    required for it to be valid (working) HTML5 in some browsers.

    """
    _EMPTY_ELEMS = frozenset(set(['source']) | XHTMLSerializer._EMPTY_ELEMS)

class TemplateLoader(_TemplateLoader):
    def load(self, filename, relative_to=None, cls=None, encoding=None):
        """Load the template with the given name.

        XXX: This code copied and modified from Genshi 0.6

        If the `filename` parameter is relative, this method searches the
        search path trying to locate a template matching the given name. If the
        file name is an absolute path, the search path is ignored.

        If the requested template is not found, a `TemplateNotFound` exception
        is raised. Otherwise, a `Template` object is returned that represents
        the parsed template.

        Template instances are cached to avoid having to parse the same
        template file more than once. Thus, subsequent calls of this method
        with the same template file name will return the same `Template`
        object (unless the ``auto_reload`` option is enabled and the file was
        changed since the last parse.)

        If the `relative_to` parameter is provided, the `filename` is
        interpreted as being relative to that path.

        :param filename: the relative path of the template file to load
        :param relative_to: the filename of the template from which the new
                            template is being loaded, or ``None`` if the
                            template is being loaded directly
        :param cls: the class of the template object to instantiate
        :param encoding: the encoding of the template to load; defaults to the
                         ``default_encoding`` of the loader instance
        :return: the loaded `Template` instance
        :raises TemplateNotFound: if a template with the given name could not
                                  be found
        """
        if cls is None:
            cls = self.default_class
        search_path = self.search_path

        # Make the filename relative to the template file its being loaded
        # from, but only if that file is specified as a relative path, or no
        # search path has been set up
        if relative_to and (not search_path or not os.path.isabs(relative_to)):
            filename = os.path.join(os.path.dirname(relative_to), filename)

        filename = os.path.normpath(filename)
        cachekey = filename

        self._lock.acquire()
        try:
            # First check the cache to avoid reparsing the same file
            try:
                tmpl = self._cache[cachekey]
                if not self.auto_reload:
                    return tmpl
                uptodate = self._uptodate[cachekey]
                if uptodate is not None and uptodate():
                    return tmpl
            except (KeyError, OSError):
                pass

            isabs = False

            retry_vars = {}
            if os.path.isabs(filename):
                # Set up secondary search options for template paths that don't
                # resolve with our relative path trick below.
                retry_vars = dict(
                    filename = os.path.basename(filename),
                    relative_to = os.path.dirname(filename) + '/',
                    cls = cls,
                    encoding = encoding
                )
                # Make absolute paths relative to the base search path.
                log.debug('Modifying the default TemplateLoader behaviour '
                          'for path %r; treating the absolute template path '
                          'as relative to the template search path.', filename)
                relative_to = None
                filename = filename[1:] # strip leading slash

            if relative_to and os.path.isabs(relative_to):
                # Make sure that the directory containing the including
                # template is on the search path
                dirname = os.path.dirname(relative_to)
                if dirname not in search_path:
                    search_path = list(search_path) + [dirname]
                isabs = True

            elif not search_path:
                # Uh oh, don't know where to look for the template
                raise TemplateError('Search path for templates not configured')

            for loadfunc in search_path:
                if isinstance(loadfunc, basestring):
                    loadfunc = directory(loadfunc)
                try:
                    filepath, filename, fileobj, uptodate = loadfunc(filename)
                except IOError:
                    continue
                except TemplateNotFound:
                    continue
                else:
                    try:
                        if isabs:
                            # If the filename of either the included or the
                            # including template is absolute, make sure the
                            # included template gets an absolute path, too,
                            # so that nested includes work properly without a
                            # search path
                            filename = filepath
                        tmpl = self._instantiate(cls, fileobj, filepath,
                                                 filename, encoding=encoding)
                        if self.callback:
                            self.callback(tmpl)
                        self._cache[cachekey] = tmpl
                        self._uptodate[cachekey] = uptodate
                    finally:
                        if hasattr(fileobj, 'close'):
                            fileobj.close()
                    return tmpl

            if retry_vars:
                return self.load(**retry_vars)

            raise TemplateNotFound(filename, search_path)

        finally:
            self._lock.release()

########NEW FILE########
__FILENAME__ = controller_testcase
# -*- coding: utf-8 -*-
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code contained in this file is licensed under the GPLv3 or
# (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.

from routes.util import URLGenerator
import pylons
from pylons.controllers.util import Response
from webob.exc import HTTPFound

from mediadrop.lib.test.request_mixin import RequestMixin
from mediadrop.lib.test.db_testcase import DBTestCase
from mediadrop.lib.test.pythonic_testcase import *


__all__ = ['ControllerTestCase']

class ControllerTestCase(DBTestCase, RequestMixin):
    def call_controller(self, controller_class, request, user=None):
        controller = controller_class()
        controller._py_object = pylons
        if user or not hasattr(request, 'perm'):
            self.set_authenticated_user(user, request.environ)
        self._inject_url_generator_for_request(request)
        
        response_info = dict()
        def fake_start_response(status, headers, exc_info=None):
            response_info['status'] = status
            response_info['headerlist'] = headers
        response_body_lines = controller(request.environ, fake_start_response)
        
        template_vars = None
        if isinstance(response_body_lines, dict):
            template_vars = response_body_lines
            body = None
        else:
            body = '\n'.join(response_body_lines)
        response = Response(body=body, **response_info)
        response.template_vars = template_vars
        return response
    
    def assert_redirect(self, call_controller):
        try:
            response = call_controller()
        except Exception, e:
            if not isinstance(e, HTTPFound):
                raise
            response = e
        assert_equals(302, response.status_int)
        return response
    
    def _inject_url_generator_for_request(self, request):
        url_mapper = self.pylons_config['routes.map']
        url_generator = URLGenerator(url_mapper, request.environ)
        
        routes_dict = url_mapper.match(environ=request.environ)
        request.environ.update({
            'routes.url': url_generator,
            'wsgiorg.routing_args': (url_generator, routes_dict),
            'pylons.routes_dict': routes_dict,
        })
        return url_generator


########NEW FILE########
__FILENAME__ = db_testcase
# -*- coding: utf-8 -*-
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code in this file is dual licensed under the MIT license or
# the GPLv3 or (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.

import os
import shutil
import tempfile

import pylons
from pylons.configuration import config

from mediadrop.lib.test.pythonic_testcase import *
from mediadrop.lib.test.support import setup_environment_and_database
from mediadrop.model.meta import DBSession, metadata
from mediadrop.websetup import add_default_data


class DBTestCase(PythonicTestCase):
    
    enabled_plugins = ''
    
    def setUp(self):
        super(DBTestCase, self).setUp()
        self.env_dir = self._create_environment_folders()
        self.pylons_config = setup_environment_and_database(self.env_dir, 
            enabled_plugins=self.enabled_plugins)
        add_default_data()
        DBSession.commit()
        
        config.push_process_config(self.pylons_config)
    
    def _create_environment_folders(self):
        j = lambda *args: os.path.join(*args)
        
        env_dir = tempfile.mkdtemp()
        for name in ('appearance', 'images', j('images', 'media'), 'media', ):
            dirname = j(env_dir, name)
            os.mkdir(dirname)
        return env_dir
    
    def tearDown(self):
        self._tear_down_db()
        self._tear_down_pylons()
        shutil.rmtree(self.env_dir)
        super(DBTestCase, self).tearDown()
    
    def _tear_down_db(self):
        metadata.drop_all(bind=DBSession.bind)
        DBSession.close_all()
    
    def _tear_down_pylons(self):
        pylons.cache._pop_object()
        try:
            pylons.app_globals.settings_cache.clear()
            pylons.app_globals._pop_object()
        except TypeError:
            # The test might have not set up any app_globals
            # No object (name: app_globals) has been registered for this thread
            pass
        config.pop_process_config()
        DBSession.registry.clear()


########NEW FILE########
__FILENAME__ = pythonic_testcase
# -*- coding: UTF-8 -*-
#
# The MIT License
# 
# Copyright (c) 2011-2013 Felix Schwarz <felix.schwarz@oss.schwarz.eu>
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#
# I believe the license above is permissible enough so you can actually 
# use/relicense the code in any other project without license proliferation. 
# I'm happy to relicense this code if necessary for inclusion in other free 
# software projects.

# TODO / nice to have
#  - raising assertions (with message building) should be unified
#  - shorted tracebacks for cascaded calls so it's easier to look at the 
#    traceback as a user 
#      see jinja2/debug.py for some code that does such hacks:
#          https://github.com/mitsuhiko/jinja2/blob/master/jinja2/debug.py

from unittest import TestCase

__all__ = ['assert_almost_equals', 'assert_callable', 'assert_contains', 
           'assert_dict_contains', 'assert_equals', 'assert_false', 'assert_falseish',
           'assert_greater',
           'assert_isinstance', 'assert_is_empty', 'assert_is_not_empty', 
           'assert_length', 'assert_none', 
           'assert_not_contains', 'assert_not_none', 'assert_not_equals', 
           'assert_raises', 'assert_smaller', 'assert_true', 'assert_trueish', 
           'create_spy', 'PythonicTestCase', ]


def assert_raises(exception, callable, message=None):
    try:
        callable()
    except exception, e:
        return e
    default_message = u'%s not raised!' % exception.__name__
    if message is None:
        raise AssertionError(default_message)
    raise AssertionError(default_message + ' ' + message)

def assert_equals(expected, actual, message=None):
    if expected == actual:
        return
    default_message = '%s != %s' % (repr(expected), repr(actual))
    if message is None:
        raise AssertionError(default_message)
    raise AssertionError(default_message + ': ' + message)

def assert_none(actual, message=None):
    assert_equals(None, actual, message=message)

def assert_false(actual, message=None):
    assert_equals(False, actual, message=message)

def assert_falseish(actual, message=None):
    if not actual:
        return
    default_message = '%s is not falseish' % repr(actual)
    if message is None:
        raise AssertionError(default_message)
    raise AssertionError(default_message + ': ' + message)

def assert_true(actual, message=None):
    assert_equals(True, actual, message=message)

def assert_trueish(actual, message=None):
    if actual:
        return
    default_message = '%s is not trueish' % repr(actual)
    if message is None:
        raise AssertionError(default_message)
    raise AssertionError(default_message + ': ' + message)

def assert_length(expected_length, actual_iterable, message=None):
    assert_equals(expected_length, len(actual_iterable), message=message)

def assert_not_equals(expected, actual, message=None):
    if expected != actual:
        return
    default_message = '%s == %s' % (repr(expected), repr(actual))
    if message is None:
        raise AssertionError(default_message)
    raise AssertionError(default_message + ': ' + message)

def assert_almost_equals(expected, actual, max_delta=None, message=None):
    if expected == actual:
        return
    if (max_delta is not None) and (abs(expected - actual) <= max_delta):
        return
    
    if max_delta is None:
        default_message = '%s != %s' % (repr(expected), repr(actual))
    else:
        default_message = '%s != %s +/- %s' % (repr(expected), repr(actual), repr(max_delta))
    if message is None:
        raise AssertionError(default_message)
    raise AssertionError(default_message + ': ' + message)

def assert_not_none(actual, message=None):
    assert_not_equals(None, actual, message=message)

def assert_contains(expected_value, actual_iterable, message=None):
    if expected_value in actual_iterable:
        return
    default_message = '%s not in %s' % (repr(expected_value), repr(actual_iterable))
    if message is None:
        raise AssertionError(default_message)
    raise AssertionError(default_message + ': ' + message)

def assert_not_contains(expected_value, actual_iterable, message=None):
    if expected_value not in actual_iterable:
        return
    default_message = '%s in %s' % (repr(expected_value), repr(actual_iterable))
    if message is None:
        raise AssertionError(default_message)
    raise AssertionError(default_message + ': ' + message)

def assert_dict_contains(expected_sub_dict, actual_super_dict, message=None):
    for key, value in expected_sub_dict.items():
        assert_contains(key, actual_super_dict, message=message)
        if value != actual_super_dict[key]:
            failure_message = '%(key)s=%(expected)s != %(key)s=%(actual)s' % \
                dict(key=repr(key), expected=repr(value), actual=repr(actual_super_dict[key]))
            if message is not None:
                failure_message += ': ' + message
            raise AssertionError(failure_message)

def assert_is_empty(actual, message=None):
    if len(actual) == 0:
        return
    default_message = '%s is not empty' % (repr(actual))
    if message is None:
        raise AssertionError(default_message)
    raise AssertionError(default_message + ': ' + message)

def assert_is_not_empty(actual, message=None):
    if len(actual) > 0:
        return
    default_message = '%s is empty' % (repr(actual))
    if message is None:
        raise AssertionError(default_message)
    raise AssertionError(default_message + ': ' + message)

def assert_callable(value, message=None):
    if callable(value):
        return
    default_message = "%s is not callable" % repr(value)
    if message is None:
        raise AssertionError(default_message)
    raise AssertionError(default_message + ': ' + message)

def assert_isinstance(value, klass, message=None):
    if isinstance(value, klass):
        return

    def class_name(instance_or_klass):
        if isinstance(instance_or_klass, type):
            return instance_or_klass.__name__
        return instance_or_klass.__class__.__name__
    default_message = "%s (%s) is not an instance of %s" % (repr(value), class_name(value), class_name(klass))
    if message is None:
        raise AssertionError(default_message)
    raise AssertionError(default_message + ': ' + message)

def assert_smaller(smaller, greater, message=None):
    if smaller < greater:
        return
    default_message = '%s >= %s' % (repr(smaller), repr(greater))
    if message is None:
        raise AssertionError(default_message)
    raise AssertionError(default_message + ': ' + message)

def assert_greater(greater, smaller, message=None):
    if greater > smaller:
        return
    default_message = '%s <= %s' % (repr(greater), repr(smaller))
    if message is None:
        raise AssertionError(default_message)
    raise AssertionError(default_message + ': ' + message)

def create_spy(name=None):
    class Spy(object):
        def __init__(self, name=None):
            self.name = name
            self.reset()
        
        # pretend to be a python method / function
        @property
        def func_name(self):
            return self.name
        
        def __str__(self):
            if self.was_called:
                return "<Spy(%s) was called with args: %s kwargs: %s>" \
                    % (self.name, self.args, self.kwargs)
            else:
                return "<Spy(%s) was not called yet>" % self.name
        
        def reset(self):
            self.args = None
            self.kwargs = None
            self.was_called = False
            self.return_value = None
        
        def __call__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs
            self.was_called = True
            return self.return_value
        
        def and_return(self, value):
            self.return_value = value
            return self
        
        def assert_was_called_with(self, *args, **kwargs):
            assert_true(self.was_called, message=str(self))
            assert_equals(args, self.args, message=str(self))
            assert_equals(kwargs, self.kwargs, message=str(self))
        
        def assert_was_called(self):
            assert_true(self.was_called, message=str(self))
            
        def assert_was_not_called(self):
            assert_false(self.was_called, message=str(self))
    
    return Spy(name=name)


class PythonicTestCase(TestCase):
    def __getattr__(self, name):
        if name in globals():
            return globals()[name]
        return getattr(super(PythonicTestCase, self), name)

# is_callable


########NEW FILE########
__FILENAME__ = request_mixin
# -*- coding: utf-8 -*-
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code in this file is dual licensed under the MIT license or
# the GPLv3 or (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.

import pylons

from mediadrop.lib.auth.permission_system import MediaDropPermissionSystem
from mediadrop.lib.test.support import fake_request


__all__ = ['RequestMixin']

class RequestMixin(object):
    def init_fake_request(self, **kwargs):
        return fake_request(self.pylons_config, **kwargs)
    
    def set_authenticated_user(self, user, wsgi_environ=None):
        if wsgi_environ is None:
            wsgi_environ = pylons.request.environ
        
        if (user is None) and ('repoze.who.identity' in wsgi_environ):
            del wsgi_environ['repoze.who.identity']
        elif user is not None:
            identity = wsgi_environ.setdefault('repoze.who.identity', {})
            identity.update({
                'user': user,
                'repoze.who.userid': user.id,
            })
        perm = MediaDropPermissionSystem.permissions_for_request(wsgi_environ, self.pylons_config)
        wsgi_environ['mediadrop.perm'] = perm
        pylons.request.perm = perm
    
    def remove_globals(self):
        for global_ in (pylons.request, pylons.response, pylons.session, 
                        pylons.tmpl_context, pylons.translator, pylons.url,):
            try:
                if hasattr(global_, '_pop_object'):
                    global_._pop_object()
            except AssertionError:
                # AssertionError: No object has been registered for this thread
                pass


########NEW FILE########
__FILENAME__ = support
# -*- coding: utf-8 -*-
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code in this file is dual licensed under the MIT license or
# the GPLv3 or (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.

from cStringIO import StringIO
import os
import urllib

from beaker.session import SessionObject
from paste.registry import Registry, StackedObjectProxy
import pylons
from pylons.controllers.util import Request, Response
from pylons.util import AttribSafeContextObj, ContextObj
from routes.util import URLGenerator
import tw
from tw.mods.pylonshf import PylonsHostFramework
from webob.request import environ_from_url

import mediadrop
from mediadrop.config.environment import load_environment
from mediadrop.config.middleware import create_tw_engine_manager
from mediadrop.lib.paginate import Bunch
from mediadrop.lib.i18n import Translator
from mediadrop.model.meta import DBSession, metadata


__all__ = [
    'build_http_body', 
    'create_wsgi_environ',
    'fake_request',
    'setup_environment_and_database',
]

def setup_environment_and_database(env_dir=None, enabled_plugins=''):
    global_config = {}
    env_dir = env_dir or '/invalid'
    app_config = {
        'plugins': enabled_plugins,
        'sqlalchemy.url': 'sqlite://',
        'layout_template': 'layout',
        'external_template': 'false',
        'image_dir': os.path.join(env_dir, 'images'),
        'media_dir': os.path.join(env_dir, 'media'),
    }
    pylons_config = load_environment(global_config, app_config)
    metadata.create_all(bind=DBSession.bind, checkfirst=True)
    return pylons_config

# -----------------------------------------------------------------------------
# unfortunately neither Python 2.4 nor any existing MediaDrop dependencies come
# with reusable methods to create a HTTP request body so I build a very basic 
# implementation myself. 
# The code is only used for unit tests so it doesn't have to be rock solid.
WWW_FORM_URLENCODED = 'application/x-www-form-urlencoded'

def encode_multipart_formdata(fields, files):
    lines = []
    BOUNDARY = '---some_random_boundary-string$'
    for key, value in fields:
        lines.extend([
            '--%s' % BOUNDARY,
            'Content-Disposition: form-data; name="%s"' % key,
            '',
            str(value)
        ])
    for key, file_ in files:
        if hasattr(file_, 'filename'):
            filename = file_.filename
        else:
            filename = file_.name
        lines.extend([
            '--%s' % BOUNDARY,
            'Content-Disposition: form-data; name="%s"; filename="%s"' % (key, filename),
            'Content-Type: application/octet-stream',
            '',
            file_.read()
        ])
    
    body = '\r\n'.join(lines)
    content_type = 'multipart/form-data; boundary=%s' % BOUNDARY
    return content_type, body


def build_http_body(data, force_multipart=False):
    if isinstance(data, basestring):
        return WWW_FORM_URLENCODED, data
    if hasattr(data, 'items'):
        data = data.items()
    
    fields = []
    files = []
    for key, value in data:
        if hasattr(value, 'read') and (hasattr(value, 'name') or hasattr(value, 'filename')):
            files.append((key, value))
        else:
            fields.append((key, value))
    if (not force_multipart) and len(files) == 0:
        return WWW_FORM_URLENCODED, urllib.urlencode(data)
    
    return encode_multipart_formdata(fields, files)
# -----------------------------------------------------------------------------

def create_wsgi_environ(url, request_method, request_body=None):
        wsgi_environ = environ_from_url(url)
        wsgi_environ.update({
            'REQUEST_METHOD': request_method,
        })
        if request_body:
            content_type, request_body = build_http_body(request_body)
            wsgi_environ.update({
                'wsgi.input': StringIO(request_body),
                'CONTENT_LENGTH': str(len(request_body)),
                'CONTENT_TYPE': content_type,
            })
        return wsgi_environ


def setup_translator(language='en', registry=None, locale_dirs=None):
    if not locale_dirs:
        mediadrop_i18n_path = os.path.join(os.path.dirname(mediadrop.__file__), 'i18n')
        locale_dirs = {'mediadrop': mediadrop_i18n_path}
    translator = Translator(language, locale_dirs=locale_dirs)
    
    # not sure why but sometimes pylons.translator is not a StackedObjectProxy
    # but just a regular Translator.
    if not hasattr(pylons.translator, '_push_object'):
        pylons.translator = StackedObjectProxy()
    if registry is None:
        registry = pylons.request.environ['paste.registry']
    registry.replace(pylons.translator, translator)

def fake_request(pylons_config, server_name='mediadrop.example', language='en',
                 method='GET', request_uri='/', post_vars=None):
    app_globals = pylons_config['pylons.app_globals']
    pylons.app_globals._push_object(app_globals)
    
    if post_vars and method.upper() != 'POST':
        raise ValueError('You must not specify post_vars for request method %r' % method)
    wsgi_environ = create_wsgi_environ('http://%s%s' % (server_name, request_uri),
        method.upper(), request_body=post_vars)
    request = Request(wsgi_environ, charset='utf-8')
    request.language = language
    request.settings = app_globals.settings
    pylons.request._push_object(request)
    response = Response(content_type='application/xml', charset='utf-8')
    pylons.response._push_object(response)
    
    session = SessionObject(wsgi_environ)
    pylons.session._push_object(session)

    routes_url = URLGenerator(pylons_config['routes.map'], wsgi_environ)
    pylons.url._push_object(routes_url)

    # Use ContextObj() when we get rid of 'pylons.strict_tmpl_context=False' in
    # mediadrop.lib.environment
    tmpl_context = AttribSafeContextObj()
    tmpl_context.paginators = Bunch()
    pylons.tmpl_context._push_object(tmpl_context)
    # some parts of Pylons (e.g. Pylons.controllers.core.WSGIController)
    # use the '.c' alias instead.
    pylons.c = pylons.tmpl_context
    
    paste_registry = Registry()
    paste_registry.prepare()
    engines = create_tw_engine_manager(app_globals)
    host_framework = PylonsHostFramework(engines=engines)
    paste_registry.register(tw.framework, host_framework)
    setup_translator(language=language, registry=paste_registry,
        locale_dirs=pylons_config.get('locale_dirs'))
    
    wsgi_environ.update({
        'pylons.pylons': pylons,
        'paste.registry': paste_registry,
    })
    return request

########NEW FILE########
__FILENAME__ = css_delivery_test
# -*- coding: utf-8 -*-
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code in this file is dual licensed under the MIT license or
# the GPLv3 or (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.

from mediadrop.lib.css_delivery import StyleSheet, StyleSheets
from mediadrop.lib.test.pythonic_testcase import *


class StyleSheetTest(PythonicTestCase):
    def test_repr(self):
        assert_equals("StyleSheet('/foo.css', key=None)", repr(StyleSheet('/foo.css')))
        assert_equals("StyleSheet('/foo.css', key=None, media='screen')", 
                      repr(StyleSheet('/foo.css', media='screen')))
    
    def test_can_tell_if_another_script_is_equal(self):
        first = StyleSheet('/foo.css')
        second = StyleSheet('/foo.css')
        assert_equals(first, first)
        assert_equals(first, second)
        assert_equals(second, first)
        assert_equals(StyleSheet('/foo.css', media='screen'), 
                      StyleSheet('/foo.css', media='screen'))
    
    def test_can_tell_that_another_script_is_not_equal(self):
        first = StyleSheet('/foo.css')
        assert_not_equals(first, StyleSheet('/bar.css'))
        assert_not_equals(first, None)
        assert_not_equals(StyleSheet('/foo.css', media='screen'), 
                          StyleSheet('/foo.css', media='print'))
    
    def test_can_render_as_html(self):
        assert_equals('<link href="/foo.css" rel="stylesheet" type="text/css"></link>',
                      StyleSheet('/foo.css').render())
        assert_equals('<link href="/foo.css" rel="stylesheet" type="text/css" media="screen"></link>',
                      StyleSheet('/foo.css', media='screen').render())


class StyleSheetsTest(PythonicTestCase):
    # --- add stylesheets ----------------------------------------------------------
    def test_can_add_a_stylesheet(self):
        stylesheets = StyleSheets()
        stylesheets.add(StyleSheet('/foo.css'))
        assert_length(1, stylesheets)
    
    def test_can_multiple_stylesheets(self):
        scripts = StyleSheets()
        scripts.add_all(StyleSheet('/foo.css'), StyleSheet('/bar.css'))
        assert_length(2, scripts)

    def test_can_add_stylesheets_during_instantiation(self):
        stylesheets = StyleSheets(StyleSheet('/foo.css'), StyleSheet('/bar.css'))
        assert_length(2, stylesheets)

    # --- duplicate handling ---------------------------------------------------
    
    def test_does_not_add_duplicate_stylesheets(self):
        stylesheets = StyleSheets()
        stylesheets.add(StyleSheet('/foo.css'))
        stylesheets.add(StyleSheet('/foo.css'))
        assert_length(1, stylesheets)
    
    # --- replacing stylesheets ----------------------------------------------------

    def test_can_replace_stylesheet_with_key(self):
        foo_script = StyleSheet('/foo.css', key='foo')
        bar_script = StyleSheet('/bar.css', key='foo')
        
        stylesheets = StyleSheets()
        stylesheets.add(foo_script)
        stylesheets.replace_stylesheet_with_key(bar_script)
        assert_length(1, stylesheets)
        assert_contains(bar_script, stylesheets.stylesheets)
    
    # --- rendering ------------------------------------------------------------
    def test_can_render_markup_for_all_stylesheets(self):
        foo_script = StyleSheet('/foo.css')
        bar_script = StyleSheet('/bar.css')
        stylesheets = StyleSheets()
        stylesheets.add(foo_script)
        stylesheets.add(bar_script)
        assert_equals(unicode(foo_script)+unicode(bar_script), stylesheets.render())


import unittest
def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(StyleSheetTest))
    suite.addTest(unittest.makeSuite(StyleSheetsTest))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')

########NEW FILE########
__FILENAME__ = current_url_test
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code contained in this file is licensed under the GPLv3 or
# (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.

import re

from pylons.controllers.util import Request
from routes.util import URLGenerator

from mediadrop.config.routing import add_routes, create_mapper
from mediadrop.lib.test.db_testcase import DBTestCase
from mediadrop.lib.test.pythonic_testcase import *
from mediadrop.lib.test.request_mixin import RequestMixin
from mediadrop.lib.test.support import create_wsgi_environ
from mediadrop.lib.util import current_url


class CurrentURLTest(DBTestCase, RequestMixin):
    def test_can_return_url(self):
        request = self.init_fake_request(server_name='server.example', request_uri='/media/view')
        self._inject_url_generator_for_request(request)
        assert_equals('/media/view', current_url(qualified=False))
        assert_equals('http://server.example:80/media/view', current_url(qualified=True))
    
    def _inject_url_generator_for_request(self, request):
        url_mapper = add_routes(create_mapper(self.pylons_config))
        url_generator = URLGenerator(url_mapper, request.environ)
        
        match = re.search('^.*?/([^/]+)(?:/([^/]+))?$', request.environ['PATH_INFO'])
        controller = match.group(1)
        action = match.group(2) or 'index'
        
        request.environ.update({
            'routes.url': url_generator,
            'wsgiorg.routing_args': (
                url_generator,
                dict(controller=controller, action=action),
            )
        })
        return url_generator
    
    def test_can_return_url_with_query_string(self):
        request = self.init_fake_request(server_name='server.example', 
            request_uri='/media/view?id=123')
        self._inject_url_generator_for_request(request)
        assert_equals('/media/view?id=123', current_url(qualified=False))
    
    def test_can_return_correct_url_even_for_whoopsidasy_page(self):
        user_url = 'http://server.example:8080/media/view?id=123'
        user_environ = create_wsgi_environ(user_url, 'GET')
        user_request = Request(user_environ, charset='utf-8')
        self._inject_url_generator_for_request(user_request)
        
        error_request = self.init_fake_request(request_uri='/error/document')
        self._inject_url_generator_for_request(error_request)
        error_request.environ['pylons.original_request'] = user_request
        
        assert_equals(user_url, current_url())
    
    def test_wsgi_deployment_in_a_subdirectory(self):
        request = self.init_fake_request(server_name='server.example', request_uri='/media/view')
        request.environ['SCRIPT_NAME'] = 'my_media'
        self._inject_url_generator_for_request(request)
        assert_equals('my_media/media/view', current_url(qualified=False))
    
    def test_proxy_deployment(self):
        self.pylons_config['proxy_prefix'] = '/proxy'
        request = self.init_fake_request(server_name='server.example', request_uri='/media/view')
        request.environ['SCRIPT_NAME'] = '/proxy'
        self._inject_url_generator_for_request(request)
        
        assert_equals('/proxy/media/view', current_url(qualified=False))


import unittest
def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(CurrentURLTest))
    return suite


########NEW FILE########
__FILENAME__ = helpers_test
# -*- coding: utf-8 -*-
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code contained in this file is licensed under the GPLv3 or
# (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.


from mediadrop.lib.test.db_testcase import DBTestCase
from mediadrop.lib.test.pythonic_testcase import *
from mediadrop.lib.test.request_mixin import RequestMixin


class DefaultPageTitleTest(DBTestCase, RequestMixin):
    def setUp(self):
        super(DefaultPageTitleTest, self).setUp()
        self.init_fake_request()
    
    def test_default_page_title_ignores_default_if_not_specified(self):
        # mediadrop.lib.helpers imports 'pylons.request' on class load time
        # so we import the symbol locally after we injected a fake request
        from mediadrop.lib.helpers import default_page_title
        assert_equals('MediaDrop', default_page_title())


import unittest
def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(DefaultPageTitleTest))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')

########NEW FILE########
__FILENAME__ = human_readable_size_test
# encoding: utf-8
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code in this file is is dual licensed under the MIT license or
# the GPLv3 or (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.

from __future__ import absolute_import

from decimal import Decimal

from ..filesize import format_filesize, human_readable_size
from mediadrop.lib.test.pythonic_testcase import *


class HumanReadableSizeTestCase(PythonicTestCase):
    def test_finds_highest_unit(self):
        assert_equals((Decimal(425), 'B'), human_readable_size(425))
        assert_equals((Decimal(12), 'KB'), human_readable_size(12*1024))
        assert_equals((Decimal(12), 'MB'), human_readable_size(12*1024**2))
        assert_equals((Decimal(12), 'GB'), human_readable_size(12*1024**3))
        assert_equals((Decimal(12), 'TB'), human_readable_size(12*1024**4))
        assert_equals((Decimal(10240), 'TB'), human_readable_size(10*1024**5))

    def test_finds_correct_units_for_negative_sizes(self):
        assert_equals((Decimal(-425), 'B'), human_readable_size(-425))
        assert_equals((Decimal(-12), 'KB'), human_readable_size(-12*1024))
        assert_equals((Decimal(-12), 'MB'), human_readable_size(-12*1024**2))
        assert_equals((Decimal(-12), 'GB'), human_readable_size(-12*1024**3))
        assert_equals((Decimal(-12), 'TB'), human_readable_size(-12*1024**4))
        assert_equals((Decimal(-10240), 'TB'), human_readable_size(-10*1024**5))


class FormatFilesizeTestCase(PythonicTestCase):
    def test_can_return_formatted_string_for_default_locale(self):
        assert_equals(u'12.8\xa0MB', format_filesize(12.8*1024**2))
        assert_equals(u'-10,240\xa0TB', format_filesize(-10*1024**5))

    def test_can_return_formatted_string_for_specified_locale(self):
        assert_equals(u'5\xa0KB', format_filesize(5*1024, locale='de'),
            message='do not render decimal places if not necessary')
        assert_equals(u'1,2\xa0MB', format_filesize(1.2*1024**2, locale='de'))
        assert_equals(u'12,9\xa0MB', format_filesize(12.854*1024**2, locale='de'),
            message='render at most one decimal digit')
        assert_equals(u'-10.240\xa0TB', format_filesize(-10*1024**5, locale='de'))

import unittest
def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(HumanReadableSizeTestCase))
    suite.addTest(unittest.makeSuite(FormatFilesizeTestCase))
    return suite


########NEW FILE########
__FILENAME__ = js_delivery_test
# -*- coding: utf-8 -*-
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code in this file is dual licensed under the MIT license or
# the GPLv3 or (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.

import re

from mediadrop.lib.js_delivery import InlineJS, Script, Scripts
from mediadrop.lib.test.pythonic_testcase import *


class ScriptTest(PythonicTestCase):
    def test_can_tell_if_another_script_is_equal(self):
        first = Script('/foo.js')
        second = Script('/foo.js')
        assert_equals(first, first)
        assert_equals(first, second)
        assert_equals(second, first)
    
    def test_can_tell_that_another_script_is_not_equal(self):
        first = Script('/foo.js')
        assert_not_equals(first, Script('/bar.js'))
        assert_not_equals(first, None)
    
    def test_can_render_as_html(self):
        assert_equals('<script src="/foo.js" type="text/javascript"></script>',
                      Script('/foo.js', async=False).render())
        assert_equals('<script src="/foo.js" async="async" type="text/javascript"></script>',
                      Script('/foo.js', async=True).render())


class InlineJSTest(PythonicTestCase):
    def test_can_tell_if_another_inlinescript_is_equal(self):
        first = InlineJS('var a = 42;')
        second = InlineJS('var a = 42;')
        assert_equals(first, first)
        assert_equals(first, second)
        assert_equals(second, first)
        assert_equals(first, InlineJS('var a = %(a)s;', params=dict(a=42)))
    
    def test_can_tell_that_another_inlinescript_is_not_equal(self):
        first = InlineJS('var a = 42;')
        assert_not_equals(first, InlineJS('var a = null;'))
        assert_not_equals(first, InlineJS('var a  =  null;'))
        assert_not_equals(first, None)
    
    def test_can_render_as_html(self):
        assert_equals('<script type="text/javascript">var a = 42;</script>',
                      InlineJS('var a = 42;').render())
    
    def _js_code(self, script):
        match = re.search('^<script[^>]*?>(.*)</script>$', script.render())
        return match.group(1)
    
    def test_can_treat_js_as_template_and_inject_specified_parameters(self):
        script = InlineJS('var a = %(a)d;', params=dict(a=42))
        assert_equals('var a = 42;', self._js_code(script))
    
    def test_can_escape_string_parameters(self):
        script = InlineJS('var a = %(a)s;', params=dict(a='<script>'))
        assert_equals('var a = "\u003cscript\u003e";', self._js_code(script))
    
    def test_can_escape_list_parameter(self):
        script = InlineJS('var a = %(a)s;', params=dict(a=['<script>', 'b']))
        assert_equals('var a = ["\u003cscript\u003e", "b"];', self._js_code(script))
        
        script = InlineJS('var a = %(a)s;', params=dict(a=('<script>', 'b')))
        assert_equals('var a = ["\u003cscript\u003e", "b"];', self._js_code(script))
    
    def test_can_escape_dict_parameter(self):
        script = InlineJS('var a = %(a)s;', params=dict(a={'foo': '<script>'}))
        assert_equals('var a = {"foo": "\u003cscript\u003e"};', self._js_code(script))
    
    def test_does_not_escape_numbers(self):
        script = InlineJS('var a=%(a)d, b=%(b)s, c=%(c)0.2f;',
            params=dict(a=21, b=10l, c=1.5))
        assert_equals('var a=21, b=10, c=1.50;', self._js_code(script))
    
    def test_can_convert_simple_parameters(self):
        script = InlineJS('var a=%(a)s, b=%(b)s, c=%(c)s;',
          params=dict(a=True, b=False, c=None))
        assert_equals('var a=true, b=false, c=null;', self._js_code(script))
    
    def test_can_escape_nested_parameters_correctly(self):
        script = InlineJS('var a = %(a)s;', params=dict(a=[True, dict(b=12, c=["foo"])]))
        assert_equals('var a = [true, {"c": ["foo"], "b": 12}];', self._js_code(script))
     
    def test_raise_exception_for_unknown_parameters(self):
        script = InlineJS('var a = %(a)s;', params=dict(a=complex(2,3)))
        assert_raises(ValueError, script.render)


class ScriptsTest(PythonicTestCase):
    # --- add scripts ----------------------------------------------------------
    def test_can_add_a_script(self):
        scripts = Scripts()
        scripts.add(Script('/foo.js'))
        assert_length(1, scripts)
    
    def test_can_multiple_scripts(self):
        scripts = Scripts()
        scripts.add_all(Script('/foo.js'), Script('/bar.js'))
        assert_length(2, scripts)
    
    def test_can_add_scripts_during_instantiation(self):
        scripts = Scripts(Script('/foo.js'), Script('/bar.js'))
        assert_length(2, scripts)

    # --- duplicate handling ---------------------------------------------------
    
    def test_does_not_add_duplicate_scripts(self):
        scripts = Scripts()
        scripts.add(Script('/foo.js'))
        scripts.add(Script('/foo.js'))
        assert_length(1, scripts)
        
    def test_uses_non_async_if_conflicting_variants_are_added(self):
        scripts = Scripts()
        scripts.add(Script('/foo.js', async=True))
        assert_length(1, scripts)
        assert_true(scripts.scripts[0].async)
        
        scripts.add(Script('/foo.js'))
        assert_length(1, scripts)
        assert_false(scripts.scripts[0].async)
    
    # --- replacing scripts ----------------------------------------------------

    def test_can_replace_script_with_key(self):
        foo_script = Script('/foo.js', key='foo')
        bar_script = Script('/bar.js', key='foo')
        
        scripts = Scripts()
        scripts.add(foo_script)
        scripts.replace_script_with_key(bar_script)
        assert_length(1, scripts)
        assert_contains(bar_script, scripts.scripts)
    
    # --- rendering ------------------------------------------------------------
    def test_can_render_markup_for_all_scripts(self):
        foo_script = Script('/foo.js')
        bar_script = Script('/bar.js')
        scripts = Scripts()
        scripts.add(foo_script)
        scripts.add(bar_script)
        assert_equals(foo_script.render()+bar_script.render(), scripts.render())



import unittest
def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(ScriptTest))
    suite.addTest(unittest.makeSuite(InlineJSTest))
    suite.addTest(unittest.makeSuite(ScriptsTest))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')

########NEW FILE########
__FILENAME__ = observable_test
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code contained in this file is licensed under the GPLv3 or
# (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.

from mediadrop.lib.test.pythonic_testcase import *

from mediadrop.plugin.events import Event, observes
from mediadrop.lib.decorators import observable


class ObservableDecoratorTest(PythonicTestCase):
    
    def probe(self, **result):
        result['probe'] = True
        return result
    
    def test_calls_observers_after_function_was_executed(self):
        event = Event([])
        observes(event)(self.probe)
        
        def function(*args, **kwargs):
            return {'args': list(args), 'kwargs': kwargs}
        decorated_function = observable(event)(function)
        
        result = decorated_function('foo', bar=True)
        assert_equals({'args': ['foo'], 'kwargs': {'bar': True}, 'probe': True},
                      result)
    
    def test_can_call_observers_before_executing_decorated_message(self):
        event = Event([])
        observes(event)(self.probe)
        def guard_probe(*args, **kwargs):
            assert_not_contains('probe', kwargs)
            kwargs['guard_probe'] = True
            return (args, kwargs)
        observes(event, run_before=True)(guard_probe)
        
        def function(*args, **kwargs):
            return {'args': list(args), 'kwargs': kwargs}
        decorated_function = observable(event)(function)
        
        expected = {
            'args': ['foo'], 
            'kwargs': {'bar': True, 'guard_probe': True}, 
            'probe': True
        }
        assert_equals(expected, decorated_function('foo', bar=True))


import unittest
def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(ObservableDecoratorTest))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')

########NEW FILE########
__FILENAME__ = request_mixin_test
# -*- coding: utf-8 -*-
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code in this file is dual licensed under the MIT license or
# the GPLv3 or (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.

import cgi
from cStringIO import StringIO
import re

from mediadrop.lib.attribute_dict import AttrDict
from mediadrop.lib.helpers import has_permission
from mediadrop.lib.test.db_testcase import DBTestCase
from mediadrop.lib.test.pythonic_testcase import *
from mediadrop.lib.test import build_http_body, RequestMixin
from mediadrop.model import DBSession, User


class EncodeMultipartFormdataTest(PythonicTestCase):
    
    def encode_and_parse(self, values):
        content_type, body = build_http_body(values, force_multipart=True)
        boundary = re.search('multipart/form-data; boundary=(.+)$', content_type).group(1)
        parsed = cgi.parse_multipart(StringIO(body), {'boundary': boundary})
        
        results = dict()
        for key, values in parsed.items():
            assert_length(1, values)
            results[key] = values[0]
        return results
    
    def test_can_encode_simple_fields(self):
        results = self.encode_and_parse([('foo', 12), ('bar', 21)])
        assert_equals(dict(foo='12', bar='21'), results)
    
    def test_can_encode_simple_fields_from_dict(self):
        values = dict(foo='12', bar='21')
        
        results = self.encode_and_parse(values)
        assert_equals(values, results)
    
    def test_can_encode_file(self):
        fake_fp = AttrDict(name='foo.txt', read=lambda: 'foobar')
        results = self.encode_and_parse([('file', fake_fp)])
        assert_equals(dict(file='foobar'), results)


class FakeRequestWithAuthorizationTest(DBTestCase, RequestMixin):
    def test_can_fake_logged_in_user(self):
        admin = DBSession.query(User).filter(User.user_name==u'admin').one()
        assert_true(admin.has_permission(u'admin'))
        self.init_fake_request()
        self.set_authenticated_user(admin)
        
        assert_true(has_permission(u'admin'))


import unittest
def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(EncodeMultipartFormdataTest))
    suite.addTest(unittest.makeSuite(FakeRequestWithAuthorizationTest))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')


########NEW FILE########
__FILENAME__ = translator_test
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code contained in this file is licensed under the GPLv3 or
# (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.

import os
import tempfile
import shutil

from babel.messages import Catalog
from babel.messages.mofile import write_mo

from mediadrop.lib.test import DBTestCase
from mediadrop.lib.test.pythonic_testcase import *
from mediadrop.lib.i18n import Translator


class TranslatorTest(DBTestCase):
    def setUp(self):
        super(TranslatorTest, self).setUp()
        self._tempdir = None
    
    def tearDown(self):
        if self._tempdir is not None:
            shutil.rmtree(self._tempdir)
        super(TranslatorTest, self).tearDown()
    
    def test_returns_input_for_unknown_domain(self):
        translator = Translator('de', {})
        assert_equals(u'foo', translator.gettext(u'foo', domain=u'unknown'))
    
    def _create_catalog(self, path_id, domain=u'foo', locale=u'de', **messages):
        i18n_dir = os.path.join(self._tempdir, path_id)
        path = os.path.join(i18n_dir, locale, 'LC_MESSAGES')
        os.makedirs(path)
        mo_filename = os.path.join(path, '%s.mo' % domain)
        assert_false(os.path.exists(mo_filename))
        
        catalog = Catalog(locale=locale, domain=domain, fuzzy=False)
        for message_id, translation in messages.items():
            catalog.add(message_id, translation)
        mo_fp = file(mo_filename, 'wb')
        write_mo(mo_fp, catalog)
        mo_fp.close()
        return i18n_dir
    
    def test_supports_multiple_locale_paths_for_single_domain(self):
        self._tempdir = tempfile.mkdtemp()
        first_path = self._create_catalog('first', something=u'foobar')
        second_path = self._create_catalog('second', something=u'baz')
        translator = Translator('de', {'foo': (first_path, second_path)})
        assert_equals('baz', translator.gettext('something', domain='foo'))


import unittest
def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TranslatorTest))
    return suite


########NEW FILE########
__FILENAME__ = url_for_test
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code contained in this file is licensed under the GPLv3 or
# (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.

from mediadrop.lib.test.db_testcase import DBTestCase
from mediadrop.lib.test.pythonic_testcase import *
from mediadrop.lib.test.request_mixin import RequestMixin
from mediadrop.lib.util import url_for


class URLForTest(DBTestCase, RequestMixin):
    def test_can_generate_static_url_with_proxy_prefix(self):
        self.pylons_config['proxy_prefix'] = '/proxy'
        request = self.init_fake_request(server_name='server.example')
        request.environ['SCRIPT_NAME'] = '/proxy'
        
        assert_equals('/proxy/media', url_for('/media'))
        qualified_media_url = url_for('/media', qualified=True)
        assert_equals('http://server.example:80/proxy/media', qualified_media_url)


import unittest
def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(URLForTest))
    return suite


########NEW FILE########
__FILENAME__ = xhtml_normalization_test
# -*- coding: utf-8 -*-
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code contained in this file is licensed under the GPLv3 or
# (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.

from mediadrop.lib.helpers import clean_xhtml, line_break_xhtml
from mediadrop.lib.test.pythonic_testcase import *


class XHTMLNormalizationTest(PythonicTestCase):
    
    def test_can_replace_linebreaks_with_p_tags(self):
        htmlified_text = clean_xhtml('first\nline\n\nsecond line')
        assert_equals('<p>first line</p><p>second line</p>', htmlified_text)
        assert_equals(htmlified_text, clean_xhtml(htmlified_text))
    
    def test_trailing_newlines_are_removed_in_output(self):
        assert_equals(clean_xhtml('first\n'), clean_xhtml('first\n\n'))

    def test_text_do_not_change_after_a_clean_xhtml_and_line_break_xhtml_cycle(self):
        """Mimics the input -> clean -> display -> input... cycle of the 
        XHTMLTextArea widget.
        """
        expected_html = '<p>first line</p><p>second line</p>'
        htmlified_text = clean_xhtml('first\nline\n\nsecond line')
        assert_equals(expected_html, htmlified_text)
        
        # Ensure that re-cleaning the XHTML provides the same result.
        display_text = line_break_xhtml(htmlified_text)
        assert_equals('<p>first line</p>\n<p>second line</p>', display_text)
        assert_equals(expected_html, clean_xhtml(display_text))


import unittest
def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(XHTMLNormalizationTest))
    return suite


########NEW FILE########
__FILENAME__ = thumbnails
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code contained in this file is licensed under the GPLv3 or
# (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.

import filecmp
import os
import re
import shutil

from PIL import Image
# XXX: note that pylons.url is imported here. Make sure to only use it with
#      absolute paths (ie. those starting with a /) to avoid differences in
#      behavior from mediadrop.lib.helpers.url_for
from pylons import config, url as url_for

import mediadrop
from mediadrop.lib.util import delete_files

__all__ = [
    'create_default_thumbs_for', 'create_thumbs_for', 'delete_thumbs',
    'has_thumbs', 'has_default_thumbs',
    'ThumbDict', 'thumb', 'thumb_path', 'thumb_paths', 'thumb_url',
]

def _normalize_thumb_item(item):
    """Pass back the image subdir and id when given a media or podcast."""
    try:
        return item._thumb_dir, item.id or 'new'
    except AttributeError:
        return item

def thumb_path(item, size, exists=False, ext='jpg'):
    """Get the thumbnail path for the given item and size.

    :param item: A 2-tuple with a subdir name and an ID. If given a
        ORM mapped class with _thumb_dir and id attributes, the info
        can be extracted automatically.
    :type item: ``tuple`` or mapped class instance
    :param size: Size key to display, see ``thumb_sizes`` in
        :mod:`mediadrop.config.app_config`
    :type size: str
    :param exists: If enabled, checks to see if the file actually exists.
        If it doesn't exist, ``None`` is returned.
    :type exists: bool
    :param ext: The extension to use, defaults to jpg.
    :type ext: str
    :returns: The absolute system path or ``None``.
    :rtype: str

    """
    if not item:
        return None

    image_dir, item_id = _normalize_thumb_item(item)
    image = '%s/%s%s.%s' % (image_dir, item_id, size, ext)
    image_path = os.path.join(config['image_dir'], image)

    if exists and not os.path.isfile(image_path):
        return None
    return image_path

def thumb_paths(item, **kwargs):
    """Return a list of paths to all sizes of thumbs for a given item.

    :param item: A 2-tuple with a subdir name and an ID. If given a
        ORM mapped class with _thumb_dir and id attributes, the info
        can be extracted automatically.
    :type item: ``tuple`` or mapped class instance
    :returns: thumb sizes and their paths
    :rtype: ``dict``

    """
    image_dir, item_id = _normalize_thumb_item(item)
    paths = dict((key, thumb_path(item, key, **kwargs))
                 for key in config['thumb_sizes'][image_dir].iterkeys())
    # We can only find the original image but examining the file system,
    # so only return it if exists is True.
    if kwargs.get('exists', False):
        for extname in ('jpg', 'png'):
            path = thumb_path(item, 'orig', **kwargs)
            if path:
                paths['orig'] = path
                break
    return paths

def thumb_url(item, size, qualified=False, exists=False):
    """Get the thumbnail url for the given item and size.

    :param item: A 2-tuple with a subdir name and an ID. If given a
        ORM mapped class with _thumb_dir and id attributes, the info
        can be extracted automatically.
    :type item: ``tuple`` or mapped class instance
    :param size: Size key to display, see ``thumb_sizes`` in
        :mod:`mediadrop.config.app_config`
    :type size: str
    :param qualified: If ``True`` return the full URL including the domain.
    :type qualified: bool
    :param exists: If enabled, checks to see if the file actually exists.
        If it doesn't exist, ``None`` is returned.
    :type exists: bool
    :returns: The relative or absolute URL.
    :rtype: str

    """
    if not item:
        return None

    image_dir, item_id = _normalize_thumb_item(item)
    image = '%s/%s%s.jpg' % (image_dir, item_id, size)
    image_path = os.path.join(config['image_dir'], image)

    if exists and not os.path.isfile(image_path):
        return None
    return url_for('/images/%s' % image, qualified=qualified)

class ThumbDict(dict):
    """Dict wrapper with convenient attribute access"""

    def __init__(self, url, dimensions):
        dict.__init__(self)
        self['url'] = url
        self['x'], self['y'] = dimensions

    def __getattr__(self, name):
        return self[name]

def thumb(item, size, qualified=False, exists=False):
    """Get the thumbnail url & dimensions for the given item and size.

    :param item: A 2-tuple with a subdir name and an ID. If given a
        ORM mapped class with _thumb_dir and id attributes, the info
        can be extracted automatically.
    :type item: ``tuple`` or mapped class instance
    :param size: Size key to display, see ``thumb_sizes`` in
        :mod:`mediadrop.config.app_config`
    :type size: str
    :param qualified: If ``True`` return the full URL including the domain.
    :type qualified: bool
    :param exists: If enabled, checks to see if the file actually exists.
        If it doesn't exist, ``None`` is returned.
    :type exists: bool
    :returns: The url, width (x) and height (y).
    :rtype: :class:`ThumbDict` with keys url, x, y OR ``None``

    """
    if not item:
        return None

    image_dir, item_id = _normalize_thumb_item(item)
    url = thumb_url(item, size, qualified, exists)

    if not url:
        return None
    return ThumbDict(url, config['thumb_sizes'][image_dir][size])

def resize_thumb(img, size, filter=Image.ANTIALIAS):
    """Resize an image without any stretching by cropping when necessary.

    If the given image has a different aspect ratio than the requested
    size, the tops or sides will be cropped off before resizing.

    Note that stretching will still occur if the target size is larger
    than the given image.

    :param img: Any open image
    :type img: :class:`PIL.Image`
    :param size: The desired width and height
    :type size: tuple
    :param filter: The downsampling filter to use when resizing.
        Defaults to PIL.Image.ANTIALIAS, the highest possible quality.
    :returns: A new, resized image instance

    """
    X, Y, X2, Y2 = 0, 1, 2, 3 # aliases for readability

    src_ratio = float(img.size[X]) / img.size[Y]
    dst_ratio = float(size[X]) / size[Y]

    if dst_ratio != src_ratio and (img.size[X] >= size[X] and
                                   img.size[Y] >= size[Y]):
        crop_size = list(img.size)
        crop_rect = [0, 0, 0, 0] # X, Y, X2, Y2

        if dst_ratio < src_ratio:
            crop_size[X] = int(crop_size[Y] * dst_ratio)
            crop_rect[X] = int(float(img.size[X] - crop_size[X]) / 2)
        else:
            crop_size[Y] = int(crop_size[X] / dst_ratio)
            crop_rect[Y] = int(float(img.size[Y] - crop_size[Y]) / 2)

        crop_rect[X2] = crop_rect[X] + crop_size[X]
        crop_rect[Y2] = crop_rect[Y] + crop_size[Y]

        img = img.crop(crop_rect)

    return img.resize(size, filter)

_ext_filter = re.compile(r'^\.([a-z0-9]*)')

def create_thumbs_for(item, image_file, image_filename):
    """Creates thumbnails in all sizes for a given Media or Podcast object.

    Side effects: Closes the open file handle passed in as image_file.

    :param item: A 2-tuple with a subdir name and an ID. If given a
        ORM mapped class with _thumb_dir and id attributes, the info
        can be extracted automatically.
    :type item: ``tuple`` or mapped class instance
    :param image_file: An open file handle for the original image file.
    :type image_file: file
    :param image_filename: The original filename of the thumbnail image.
    :type image_filename: unicode
    """
    image_dir, item_id = _normalize_thumb_item(item)
    img = Image.open(image_file)

    # TODO: Allow other formats?
    for key, xy in config['thumb_sizes'][item._thumb_dir].iteritems():
        path = thumb_path(item, key)
        thumb_img = resize_thumb(img, xy)
        if thumb_img.mode != "RGB":
            thumb_img = thumb_img.convert("RGB")
        thumb_img.save(path, quality=90)

    # Backup the original image, ensuring there's no odd chars in the ext.
    # Thumbs from DailyMotion include an extra query string that needs to be
    # stripped off here.
    ext = os.path.splitext(image_filename)[1].lower()
    ext_match = _ext_filter.match(ext)
    if ext_match:
        backup_type = ext_match.group(1)
        backup_path = thumb_path(item, 'orig', ext=backup_type)
        backup_file = open(backup_path, 'w+b')
        image_file.seek(0)
        shutil.copyfileobj(image_file, backup_file)
        image_file.close()
        backup_file.close()

def create_default_thumbs_for(item):
    """Create copies of the default thumbs for the given item.

    This copies the default files (all named with an id of 'new') to
    use the given item's id. This means there could be lots of duplicate
    copies of the default thumbs, but at least we can always use the
    same url when rendering.

    :param item: A 2-tuple with a subdir name and an ID. If given a
        ORM mapped class with _thumb_dir and id attributes, the info
        can be extracted automatically.
    :type item: ``tuple`` or mapped class instance
    """
    mediadrop_dir = os.path.join(os.path.dirname(mediadrop.__file__), '..')
    image_dir, item_id = _normalize_thumb_item(item)
    for key in config['thumb_sizes'][image_dir].iterkeys():
        src_file = thumb_path((image_dir, 'new'), key)
        if not os.path.exists(src_file):
            default_image_dir = os.path.join(mediadrop_dir, 'data', 'images', image_dir)
            src_file = thumb_path((default_image_dir, 'new'), key)
        dst_file = thumb_path(item, key)
        shutil.copyfile(src_file, dst_file)

def delete_thumbs(item):
    """Delete the thumbnails associated with the given item.

    :param item: A 2-tuple with a subdir name and an ID. If given a
        ORM mapped class with _thumb_dir and id attributes, the info
        can be extracted automatically.
    :type item: ``tuple`` or mapped class instance
    """
    image_dir, item_id = _normalize_thumb_item(item)
    thumbs = thumb_paths(item, exists=True).itervalues()
    delete_files(thumbs, image_dir)

def has_thumbs(item):
    """Return True if a thumb exists for this item.

    :param item: A 2-tuple with a subdir name and an ID. If given a
        ORM mapped class with _thumb_dir and id attributes, the info
        can be extracted automatically.
    :type item: ``tuple`` or mapped class instance
    """
    return bool(thumb_path(item, 's', exists=True))

def has_default_thumbs(item):
    """Return True if the thumbs for the given item are the defaults.

    :param item: A 2-tuple with a subdir name and an ID. If given a
        ORM mapped class with _thumb_dir and id attributes, the info
        can be extracted automatically.
    :type item: ``tuple`` or mapped class instance
    """
    image_dir, item_id = _normalize_thumb_item(item)
    return filecmp.cmp(thumb_path((image_dir, item_id), 's'),
                       thumb_path((image_dir, 'new'), 's'))

########NEW FILE########
__FILENAME__ = uri
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code contained in this file is licensed under the GPLv3 or
# (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.

import os

from urlparse import urlsplit

from mediadrop.lib.compat import all

class StorageURI(object):
    """
    An access point for a :class:`mediadrop.model.media.MediaFile`.

    A single file may be accessed in several different ways. Each `StorageURI`
    represents one such access point.

    .. attribute:: file

        The :class:`mediadrop.model.media.MediaFile` this URI points to.

    .. attribute:: scheme

        The protocol, URI scheme, or other internally meaningful
        string. Don't be fooled into thinking this is always going to be
        the URI scheme (such as "rtmp://..") -- it may differ.

        Some examples include:
            * http
            * rtmp
            * youtube
            * www

    .. attribute:: file_uri

        The file-specific portion of the URI. In the case of
        HTTP URLs, for example, this will include the entire URL. Only
        when the server must be defined separately does this not include
        the entire URI.

    .. attribute:: server_uri

        An optional server URI. This is useful for RTMP
        streaming servers and the like, where a streaming server must
        be declared separately from the file.

    """
    __slots__ = ('file', 'scheme', 'file_uri', 'server_uri', '__weakref__')

    def __init__(self, file, scheme, file_uri, server_uri=None):
        self.file = file
        self.scheme = scheme
        self.file_uri = file_uri
        self.server_uri = server_uri

    def __str__(self):
        """Return the best possible string representation of the URI.

        NOTE: This string may not actually be usable for playing back
              certain kinds of media. Be careful with RTMP URIs.

        """
        if self.server_uri is not None:
            return os.path.join(self.server_uri, self.file_uri)
        return self.file_uri

    def __unicode__(self):
        return unicode(self.__str__())

    def __repr__(self):
        return "<StorageURI '%s'>" % self.__str__()

    def __getattr__(self, name):
        """Return attributes from the file as if they were defined on the URI.

        This method is called when an attribute lookup fails on this StorageURI
        instance. Before throwing an AttributeError, we first try the lookup
        on our :class:`~mediadrop.model.media.MediaFile` instance.

        For example::

            self.scheme          # an attribute of this StorageURI
            self.file.container  # clearly an attribute of the MediaFile
            self.container       # the same attribute of the MediaFile

        :param name: Attribute name
        :raises AttributeError: If the lookup fails on the file.

        """
        if hasattr(self.file, name):
            return getattr(self.file, name)
        raise AttributeError('%r has no attribute %r, nor does the file '
                             'it contains.' % (self.__class__.__name__, name))

def pick_uris(uris, **kwargs):
    """Return a subset of the given URIs whose attributes match the kwargs.

    This function attempts to simplify the somewhat unwieldly process of
    filtering a list of :class:`mediadrop.lib.storage.StorageURI` instances
    for a specific type, protocol, container, etc::

        pick_uris(uris, scheme='rtmp', container='mp4', type='video')

    :type uris: iterable or :class:`~mediadrop.model.media.Media` or
        :class:`~mediadrop.model.media.MediaFile` instance
    :params uris: A collection of :class:`~mediadrop.lib.storage.StorageURI`
        instances, including Media and MediaFile objects.
    :param \*\*kwargs: Required attribute values. These attributes can be
        on the `StorageURI` instance or, failing that, on the `StorageURI.file`
        instance within it.
    :rtype: list
    :returns: A subset of the input `uris`.

    """
    if not isinstance(uris, (list, tuple)):
        from mediadrop.model.media import Media, MediaFile
        if isinstance(uris, (Media, MediaFile)):
            uris = uris.get_uris()
    if not uris or not kwargs:
        return uris
    return [uri
            for uri in uris
            if all(getattr(uri, k) == v for k, v in kwargs.iteritems())]

def pick_uri(uris, **kwargs):
    """Return the first URL that meets the given criteria.

    See: :func:`pick_uris`.

    :returns: A :class:`mediadrop.lib.storage.StorageURI` instance or None.
    """
    uris = pick_uris(uris, **kwargs)
    if uris:
        return uris[0]
    return None

def download_uri(uris):
    """Pick out the best possible URI for downloading purposes.

    :returns: A :class:`mediadrop.lib.storage.StorageURI` instance or None.
    """
    uris = pick_uris(uris, scheme='download')\
        or pick_uris(uris, scheme='http')
    uris.sort(key=lambda uri: uri.file.size, reverse=True)
    if uris:
        return uris[0]
    return None

def web_uri(uris):
    """Pick out the web link URI for viewing an embed in its original context.

    :returns: A :class:`mediadrop.lib.storage.StorageURI` instance or None.
    """
    return pick_uri(uris, scheme='www')\
        or None

def best_link_uri(uris):
    """Pick out the best general purpose URI from those given.

    :returns: A :class:`mediadrop.lib.storage.StorageURI` instance or None.
    """
    return pick_uri(uris, scheme='www')\
        or pick_uri(uris, scheme='download')\
        or pick_uri(uris, scheme='http')\
        or pick_uri(uris)\
        or None

def file_path(uris):
    """Pick out the local file path from the given list of URIs.

    Local file paths are passed around as urlencoded strings in
    :class:`mediadrop.lib.storage.StorageURI`. The form is:

        file:///path/to/file

    :rtype: `str` or `unicode` or `None`
    :returns: Absolute /path/to/file
    """
    uris = pick_uris(uris, scheme='file')
    if uris:
        scheme, netloc, path, query, fragment = urlsplit(uris[0].file_uri)
        return path
    return None

########NEW FILE########
__FILENAME__ = util
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code contained in this file is licensed under the GPLv3 or
# (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.
"""
Library Utilities

"""
import math
import os
import shutil
from datetime import datetime
from urlparse import urlparse

from pylons import app_globals, config, request, url as pylons_url
from webob.exc import HTTPFound

__all__ = [
    'calculate_popularity',
    'current_url',
    'delete_files',
    'merge_dicts',
    'redirect',
    'url',
    'url_for',
    'url_for_media',
]

def current_url(with_qs=True, qualified=True):
    """This method returns the "current" (as in "url as request by the user")
    url.
    
    The default "url_for()" returns the current URL in most cases however when
    the error controller is triggered "url_for()" will return the url of the
    error document ('<host>/error/document') instead of the url requested by the
    user."""
    original_request = request.environ.get('pylons.original_request')
    if original_request:
        request_ = original_request
        url_generator = original_request.environ.get('routes.url')
        url = url_generator.current(qualified=qualified)
    else:
        request_ = request
        url = url_for(qualified=qualified)
    query_string = request_.environ.get('QUERY_STRING')
    if with_qs and query_string:
        return url + '?' + query_string
    return url

def url(*args, **kwargs):
    """Compose a URL with :func:`pylons.url`, all arguments are passed."""
    return _generate_url(pylons_url, *args, **kwargs)

def url_for(*args, **kwargs):
    """Compose a URL :func:`pylons.url.current`, all arguments are passed."""
    return _generate_url(pylons_url.current, *args, **kwargs)

# Mirror the behaviour you'd expect from pylons.url
url.current = url_for

def url_for_media(media, qualified=False):
    """Return the canonical URL for that media ('/media/view')."""
    return url_for(controller='/media', action='view', slug=media.slug, qualified=qualified)

def _generate_url(url_func, *args, **kwargs):
    """Generate a URL using the given callable."""
    # Convert unicode to str utf-8 for routes
    def to_utf8(value):
        if isinstance(value, unicode):
            return value.encode('utf-8')
        return value

    if args:
        args = [to_utf8(val) for val in args]
    if kwargs:
        kwargs = dict((key, to_utf8(val)) for key, val in kwargs.iteritems())

    # TODO: Rework templates so that we can avoid using .current, and use named
    # routes, as described at http://routes.readthedocs.org/en/latest/generating.html#generating-routes-based-on-the-current-url
    # NOTE: pylons.url is a StackedObjectProxy wrapping the routes.url method.
    url = url_func(*args, **kwargs)

    # If the proxy_prefix config directive is set up, then we need to make sure
    # that the SCRIPT_NAME is prepended to the URL. This SCRIPT_NAME prepending
    # is necessary for mod_proxy'd deployments, and for FastCGI deployments.
    # XXX: Leaking abstraction below. This code is tied closely to Routes 1.12
    #      implementation of routes.util.URLGenerator.__call__()
    # If the arguments given didn't describe a raw URL, then Routes 1.12 didn't
    # prepend the SCRIPT_NAME automatically--we'll need to feed the new URL
    # back to the routing method to prepend the SCRIPT_NAME.
    prefix = config.get('proxy_prefix', None)
    script_name = request.environ.get('SCRIPT_NAME', None)
    if prefix and (prefix != script_name):
        if args:
            named_route = config['routes.map']._routenames.get(args[0])
            protocol = urlparse(args[0]).scheme
            static = not named_route and (args[0][0]=='/' or protocol)
        else:
            static = False
            protocol = ''

        if not static:
            if kwargs.get('qualified', False):
                offset = len(urlparse(url).scheme+"://")
            else:
                offset = 0
            path_index = url.index('/', offset)
            url = url[:path_index] + prefix + url[path_index:]

    return url

def redirect(*args, **kwargs):
    """Compose a URL using :func:`url_for` and raise a redirect.

    :raises: :class:`webob.exc.HTTPFound`
    """
    url = url_for(*args, **kwargs)
    raise HTTPFound(location=url)

def delete_files(paths, subdir=None):
    """Move the given files to the 'deleted' folder, or just delete them.

    If the config contains a deleted_files_dir setting, then files are
    moved there. If that setting does not exist, or is empty, then the
    files will be deleted permanently instead.

    :param paths: File paths to delete. These files do not necessarily
        have to exist.
    :type paths: iterable
    :param subdir: A subdir within the configured deleted_files_dir to
        move the given files to. If this folder does not yet exist, it
        will be created.
    :type subdir: str or ``None``

    """
    deleted_dir = config.get('deleted_files_dir', None)
    if deleted_dir and subdir:
        deleted_dir = os.path.join(deleted_dir, subdir)
    if deleted_dir and not os.path.exists(deleted_dir):
        os.mkdir(deleted_dir)
    for path in paths:
        if path and os.path.exists(path):
            if deleted_dir:
                shutil.move(path, deleted_dir)
            else:
                os.remove(path)

def merge_dicts(dst, *srcs):
    """Recursively merge two or more dictionaries.

    Code adapted from Manuel Muradas' example at
    http://code.activestate.com/recipes/499335-recursively-update-a-dictionary-without-hitting-py/
    """
    for src in srcs:
        stack = [(dst, src)]
        while stack:
            current_dst, current_src = stack.pop()
            for key in current_src:
                if key in current_dst \
                and isinstance(current_src[key], dict) \
                and isinstance(current_dst[key], dict):
                    stack.append((current_dst[key], current_src[key]))
                else:
                    current_dst[key] = current_src[key]
    return dst

def calculate_popularity(publish_date, score):
    """Calculate how 'hot' an item is given its response since publication.

    In our ranking algorithm, being base_life_hours newer is equivalent
    to having log_base times more votes.

    :type publish_date: datetime.datetime
    :param publish_date: The date of publication. An older date reduces
        the popularity score.
    :param int score: The number of likes, dislikes or likes - dislikes.
    :rtype: int
    :returns: Popularity points.

    """
    settings = request.settings
    log_base = int(settings['popularity_decay_exponent'])
    base_life = int(settings['popularity_decay_lifetime']) * 3600
    # FIXME: The current algorithm assumes that the earliest publication
    #        date is January 1, 2000.
    if score > 0:
        sign = 1
    elif score < 0:
        sign = -1
    else:
        sign = 0
    delta = publish_date - datetime(2000, 1, 1) # since January 1, 2000
    t = delta.days * 86400 + delta.seconds
    popularity = math.log(max(abs(score), 1), log_base) + sign * t / base_life
    return max(int(popularity), 0)

########NEW FILE########
__FILENAME__ = htmlsanitizer
# -*- coding: UTF-8 -*-
"""
Repository: https://code.launchpad.net/~python-scrapers/python-html-sanitizer/trunk
Revision: r10
Site: https://launchpad.net/python-html-sanitizer
Licence: Simplified BSD License

some input filters, for regularising the html fragments from screen scraping and
browser-based editors into some semblance of sanity

TODO: turn the messy setting[method_name]=True filter syntax into a list of cleaning methods to invoke, so that they can be invoked in a specific order and multiple times.

AUTHORS:
Dan MacKinlay - https://launchpad.net/~dan-possumpalace
Collin Grady - http://launchpad.net/~collin-collingrady
Andreas Gustafsson - https://bugs.launchpad.net/~gson
Håkan W - https://launchpad.net/~hwaara-gmail
"""

import BeautifulSoup
import re
import sys
import copy

from mediadrop.lib.compat import any

s = lambda x: unicode(x)[:20].replace("\n", "")

"""
html5lib compatibility. Basically, we need to know that this still works whether html5lib
is imported or not. Should run complete suites of tests for both possible configs -
or test in virtual environments, but for now a basic sanity check will do.
>>> if html5:
>>>     c=Cleaner(html5=False)
>>>     c(u'<p>foo</p>)
u'<p>foo</p>'
"""
try:
    import html5lib
    from html5lib import sanitizer, treebuilders
    parser = html5lib.HTMLParser(
        tree=treebuilders.getTreeBuilder("beautifulsoup"),
        tokenizer=sanitizer.HTMLSanitizer
    )
    html5 = True
except ImportError:
    html5 = False

ANTI_JS_RE=re.compile('j\s*a\s*v\s*a\s*s\s*c\s*r\s*i\s*p\s*t\s*:', re.IGNORECASE)
#These tags and attrs are sufficently liberal to let microformats through...
#it ruthlessly culls all the rdf, dublin core metadata and so on.
valid_tags = dict.fromkeys('p i em strong b u a h1 h2 h3 pre abbr br img dd dt ol ul li span sub sup ins del blockquote table tr td th address cite'.split()) #div?
valid_attrs = dict.fromkeys('href src rel title'.split())
valid_schemes = dict.fromkeys('http https ssh sftp ftp'.split())
elem_map = {'b' : 'strong', 'i': 'em'}
attrs_considered_links = dict.fromkeys("src href".split()) #should include
#courtesy http://developer.mozilla.org/en/docs/HTML:Block-level_elements
block_elements = dict.fromkeys(["p", "h1","h2", "h3", "h4", "h5", "h6", "ol", "ul", "pre", "address", "blockquote", "dl", "div", "fieldset", "form", "hr", "noscript", "table"])

#convenient default filter lists.
paranoid_filters = ["strip_comments", "strip_tags", "strip_attrs", "encode_xml_specials",
  "strip_schemes", "rename_tags", "wrap_string", "strip_empty_tags", ]
complete_filters = ["strip_comments", "rename_tags", "strip_tags", "strip_attrs", "encode_xml_specials",
    "strip_cdata", "strip_schemes",  "wrap_string", "strip_empty_tags", "rebase_links", "reparse"]

#set some conservative default string processings
default_settings = {
    "filters" : paranoid_filters,
    "block_elements" : block_elements, #xml or None for a more liberal version
    "convert_entities" : "html", #xml or None for a more liberal version
    "valid_tags" : valid_tags,
    "valid_attrs" : valid_attrs,
    "valid_schemes" : valid_schemes,
    "attrs_considered_links" : attrs_considered_links,
    "elem_map" : elem_map,
    "wrapping_element" : "p",
    "auto_clean" : False,
    "original_url" : "",
    "new_url" : "",
    "html5" : html5
}
#processes I'd like but haven't implemented
#"encode_xml_specials", "ensure complete xhtml doc", "ensure_xhtml_fragment_only"
# and some handling of permitted namespaces for tags. for RDF, say. maybe.

# TLDs from:
# http://data.iana.org/TLD/tlds-alpha-by-domain.txt (july 2009)
tlds = "AC|AD|AE|AERO|AF|AG|AI|AL|AM|AN|AO|AQ|AR|ARPA|AS|ASIA|AT|AU|AW|AX|AZ|BA|BB|BD|BE|BF|BG|BH|BI|BIZ|BJ|BM|BN|BO|BR|BS|BT|BV|BW|BY|BZ|CA|CAT|CC|CD|CF|CG|CH|CI|CK|CL|CM|CN|CO|COM|COOP|CR|CU|CV|CX|CY|CZ|DE|DJ|DK|DM|DO|DZ|EC|EDU|EE|EG|ER|ES|ET|EU|FI|FJ|FK|FM|FO|FR|GA|GB|GD|GE|GF|GG|GH|GI|GL|GM|GN|GOV|GP|GQ|GR|GS|GT|GU|GW|GY|HK|HM|HN|HR|HT|HU|ID|IE|IL|IM|IN|INFO|INT|IO|IQ|IR|IS|IT|JE|JM|JO|JOBS|JP|KE|KG|KH|KI|KM|KN|KP|KR|KW|KY|KZ|LA|LB|LC|LI|LK|LR|LS|LT|LU|LV|LY|MA|MC|MD|ME|MG|MH|MIL|MK|ML|MM|MN|MO|MOBI|MP|MQ|MR|MS|MT|MU|MUSEUM|MV|MW|MX|MY|MZ|NA|NAME|NC|NE|NET|NF|NG|NI|NL|NO|NP|NR|NU|NZ|OM|ORG|PA|PE|PF|PG|PH|PK|PL|PM|PN|PR|PRO|PS|PT|PW|PY|QA|RE|RO|RS|RU|RW|SA|SB|SC|SD|SE|SG|SH|SI|SJ|SK|SL|SM|SN|SO|SR|ST|SU|SV|SY|SZ|TC|TD|TEL|TF|TG|TH|TJ|TK|TL|TM|TN|TO|TP|TR|TRAVEL|TT|TV|TW|TZ|UA|UG|UK|US|UY|UZ|VA|VC|VE|VG|VI|VN|VU|WF|WS|YE|YT|YU|ZA|ZM|ZW"
# Sort the list of TLDs so that the longest TLDs come first.
# This forces the regex to match the longest possible TLD.
tlds = "|".join(sorted(tlds.split("|"), lambda a,b: cmp(len(b), len(a))))

# This might not be the full regex. It is modified from the discussion at:
# http://geekswithblogs.net/casualjim/archive/2005/12/01/61722.aspx
url_regex = r"(?#Protocol)(?:([a-z\d]+)\:\/\/|~/|/)?" \
          + r"(?#Username:Password)(?:\w+:\w+@)?" \
          + r"(?#Host)(" \
              + r"((?#Subdomains)(?:(?:[-\w]+\.)+)" \
              + r"(?#TopLevel Domains)(?:%s))" % tlds \
              + r"|" \
              + r"(?#IPAddr)(([\d]{1,3}\.){3}[\d]{1,3})" \
          + r")" \
          + r"(?#Port)(?::[\d]{1,5})?" \
          + r"(?#Directories)(?:(?:(?:/(?:[-\w~!$+|.,=]|%[a-f\d]{2})+)+|/)+|\?|#)?" \
          + r"(?#Query)(?:(?:\?(?:[-\w~!$+|.,*:]|%[a-f\d{2}])+=(?:[-\w~!$+|.,*:=]|%[a-f\d]{2})*)(?:&(?:[-\w~!$+|.,*:]|%[a-f\d{2}])+=(?:[-\w~!$+|.,*:=]|%[a-f\d]{2})*)*)*" \
          + r"(?#Anchor)(?:#(?:[-\w~!$+|.,*:=]|%[a-f\d]{2})*)?"

# NB: The order of these entities is very important
#     when performing search and replace!
XML_ENTITIES = [
    (u"&", u"&amp;"),
#    (u"'", u"&#39;"),
    (u'"', u"&quot;"),
    (u"<", u"&lt;"),
    (u">", u"&gt;")
]
LINE_EXTRACTION_RE = re.compile(".+", re.MULTILINE)
BR_EXTRACTION_RE = re.compile("</?br ?/?>", re.MULTILINE)
URL_RE = re.compile(url_regex, re.IGNORECASE)

def entities_to_unicode(text):
    """Converts HTML entities to unicode.  For example '&amp;' becomes '&'.

    FIXME:
    WARNING: There is a bug between sgmllib.SGMLParser.goahead() and
    BeautifulSoup.BeautifulStoneSoup.handle_entityref() where entity-like
    strings that don't match known entities are guessed at (if they come in
    the middle of the text) or are omitted (if they come at the end of the
    text).

    Further, unrecognized entities will have their leading ampersand escaped
    and trailing semicolon (if it exists) stripped. Examples:

    Inputs "...&bob;...", "...&bob&...", "...&bob;", and "...&bob" will give
    outputs "...&amp;bob...", "...&amp;bob&...", "...&amp;bob", and "...",
    respectively.
    """
    soup = BeautifulSoup.BeautifulStoneSoup(text,
        convertEntities=BeautifulSoup.BeautifulStoneSoup.ALL_ENTITIES)
    string = unicode(soup)
    # for some reason plain old instances of &amp; aren't converted to & ??
    string = string.replace('&amp;', '&')
    return string

def encode_xhtml_entities(text):
    """Escapes only those entities that are required for XHTML compliance"""
    for e in XML_ENTITIES:
        text = text.replace(e[0], e[1])
    return text

class Stop:
    """
    handy class that we use as a stop input for our state machine in lieu of falling
    off the end of lists
    """
    pass


class Cleaner(object):
    r"""
    powerful and slow arbitrary HTML sanitisation. can deal (i hope) with most XSS
    vectors and layout-breaking badness.
    Probably overkill for content from trusted sources; defaults are accordingly
    set to be paranoid.
    >>> bad_html = '<p style="forbidden markup"><!-- XSS attach -->content</p'
    >>> good_html = u'<p>content</p>'
    >>> c = Cleaner()
    >>> c.string = bad_html
    >>> c.clean()
    >>> c.string == good_html
    True

    Also supports shorthand syntax:
    >>> c = Cleaner()
    >>> c(bad_html) == c(good_html)
    True
    """

    def __init__(self, string_or_soup="", *args,  **kwargs):
        self.settings = copy.deepcopy(default_settings)
        self.settings.update(kwargs)
        if args :
            self.settings['filters'] = args
        super(Cleaner, self).__init__()
        self.string = string_or_soup

    def __call__(self, string = None, **kwargs):
        """
        convenience method allowing one-step calling of an instance and returning
        a cleaned string.

        TODO: make this method preserve internal state- perhaps by creating a new
        instance.

        >>> s = 'input string'
        >>> c1 = Cleaner(s, auto_clean=True)
        >>> c2 = Cleaner("")
        >>> c1.string == c2(s)
        True

        """
        self.settings.update(kwargs)
        if not string == None :
            self.string = string
        self.clean()
        return self.string

    def _set_contents(self, string_or_soup):
        if isinstance(string_or_soup, BeautifulSoup.BeautifulSoup) :
            self._set_soup(string_or_soup)
        else :
            self._set_string(string_or_soup)

    def _set_string(self, html_fragment_string):
        if self.settings['html5']:
            s = parser.parse(html_fragment_string).body
        else:
            s = BeautifulSoup.BeautifulSoup(
                    html_fragment_string,
                    convertEntities=self.settings['convert_entities'])
        self._set_soup(s)

    def _set_soup(self, soup):
        """
        Does all the work of set_string, but bypasses a potential autoclean to avoid
        loops upon internal string setting ops.
        """
        self._soup = BeautifulSoup.BeautifulSoup(
            '<rootrootroot></rootrootroot>'
        )
        self.root=self._soup.contents[0]

        if len(soup.contents) :
            backwards_soup = [i for i in soup.contents]
            backwards_soup.reverse()
        else :
            backwards_soup = []
        for i in backwards_soup :
            i.extract()
            self.root.insert(0, i)

    def set_string(self, string) :
        ur"""
            sets the string to process and does the necessary input encoding too
        really intended to be invoked as a property.
        note the godawful rootrootroot element which we need because the
        BeautifulSoup object has all the same methods as a Tag, but
        behaves differently, silently failing on some inserts and appends

        >>> c = Cleaner(convert_entities="html")
        >>> c.string = '&eacute;'
        >>> c.string
        u'\xe9'
        >>> c = Cleaner(convert_entities="xml")
        >>> c.string = u'&eacute;'
        >>> c.string
        u'&eacute;'
        """
        self._set_string(string)
        if len(string) and self.settings['auto_clean'] : self.clean()

    def get_string(self):
        return self.root.renderContents().decode('utf-8')

    string = property(get_string, set_string)

    def checkit(self, method):
        np = lambda x, y: y.parent is None and sys.stderr.write('%s HAS NO PARENT: %s\n' % (x, y)) or None
        a = self.root.findAllNext(True)
        a.extend(self.root.findAllNext(text=True))
        b = self.root.findAll(True)
        b.extend(self.root.findAll(text=True))
        for x in a:
            np('A', x)
            if x not in b:
                print method, [s(x)], "NOT IN B"
        for x in b:
            np('B', x)
            if x not in a:
                print method, [s(x)], "NOT IN A"

    def clean(self):
        """
        invoke all cleaning processes stipulated in the settings
        """
        for method in self.settings['filters'] :
            print_error = lambda: sys.stderr.write('Warning, called unimplemented method %s\n' % method)

            try :
                getattr(self, method, print_error)()
                # Uncomment when running in development mode, under paster.
                # self.checkit(method)
            except NotImplementedError:
                print_error()

    def strip_comments(self):
        r"""
        XHTML comments are used as an XSS attack vector. they must die.

        >>> c = Cleaner("", "strip_comments")
        >>> c('<p>text<!-- comment --> More text</p>')
        u'<p>text More text</p>'
        """
        for comment in self.root.findAll(
            text = lambda text: isinstance(text, BeautifulSoup.Comment)
        ):
            comment.extract()

    def strip_cdata(self):
        for cdata in self.root.findAll(
            text = lambda text: isinstance(text, BeautifulSoup.CData)
        ):
            cdata.extract()

    def strip_tags(self):
        r"""
        ill-considered tags break our layout. they must die.
        >>> c = Cleaner("", "strip_tags", auto_clean=True)
        >>> c.string = '<div>A <strong>B C</strong></div>'
        >>> c.string
        u'A <strong>B C</strong>'
        >>> c.string = '<div>A <div>B C</div></div>'
        >>> c.string
        u'A B C'
        >>> c.string = '<div>A <br /><div>B C</div></div>'
        >>> c.string
        u'A <br />B C'
        >>> c.string = '<p>A <div>B C</div></p>'
        >>> c.string
        u'<p>A B C</p>'
        >>> c.string = 'A<div>B<div>C<div>D</div>E</div>F</div>G'
        >>> c.string
        u'ABCDEFG'
        >>> c.string = '<div>B<div>C<div>D</div>E</div>F</div>'
        >>> c.string
        u'BCDEF'
        """
        # Beautiful Soup doesn't support dynamic .findAll results when the tree is
        # modified in place.
        # going backwards doesn't seem to help.
        # so find one at a time
        while True :
            next_bad_tag = self.root.find(
              lambda tag : not tag.name in (self.settings['valid_tags'])
            )
            if next_bad_tag :
                self.disgorge_elem(next_bad_tag)
            else:
                break

    def strip_attrs(self):
        """
        preserve only those attributes we need in the soup
        >>> c = Cleaner("", "strip_attrs")
        >>> c('<div title="v" bad="v">A <strong title="v" bad="v">B C</strong></div>')
        u'<div title="v">A <strong title="v">B C</strong></div>'
        """
        for tag in self.root.findAll(True):
            tag.attrs = [(attr, val) for attr, val in tag.attrs
                         if attr in self.settings['valid_attrs']]

    def _all_links(self):
        """
        finds all tags with link attributes sequentially. safe against modification
        of said attributes in-place.
        """
        start = self.root
        while True:
            tag = start.findNext(
              lambda tag : any(
                [(tag.get(i) for i in self.settings['attrs_considered_links'])]
              ))
            if tag:
                start = tag
                yield tag
            else :
                break

    def _all_elems(self, *args, **kwargs):
        """
        replacement for self.root.findAll(**kwargs)
        finds all elements with the specified strainer properties
        safe against modification of said attributes in-place.
        """
        start = self.root
        while True:
            tag = start.findNext(*args, **kwargs)
            if tag:
                start = tag
                yield tag
            else :
                break

    def strip_schemes(self):
        """
        >>> c = Cleaner("", "strip_schemes")
        >>> c('<img src="javascript:alert();" />')
        u'<img />'
        >>> c('<a href="javascript:alert();">foo</a>')
        u'<a>foo</a>'
        """
        for tag in self._all_links() :
            for key in self.settings['attrs_considered_links'] :
                scheme_bits = tag.get(key, u"").split(u':',1)
                if len(scheme_bits) == 1 :
                    pass #relative link
                else:
                    if not scheme_bits[0] in self.settings['valid_schemes']:
                        del(tag[key])

    def clean_whitespace(self):
        """
        >>> c = Cleaner("", "strip_whitespace")
        >>> c('<p>\n\t\tfoo</p>"
        u'<p> foo</p>'
        >>> c('<p>\t  <span> bar</span></p>')
        u'<p> <span>bar</span></p>')
        """
        def is_text(node):
            return isinstance(node, BeautifulSoup.NavigableString)

        def is_tag(node):
            return isinstance(node, BeautifulSoup.Tag)

        def dfs(node, func):
            if isinstance(node, BeautifulSoup.Tag):
                for x in node.contents:
                    dfs(x, func)
            func(node)

        any_space = re.compile("\s+", re.M)
        start_space = re.compile("^\s+")

        def condense_whitespace():
            # Go over every string, replacing all whitespace with a single space
            for string in self.root.findAll(text=True):
                s = unicode(string)
                s = any_space.sub(" ", s)
                s = BeautifulSoup.NavigableString(s)
                string.replaceWith(s)

        def separate_strings(current, next):
            if is_text(current):
                if is_text(next):
                    # Two strings are beside eachother, merge them!
                    next.extract()
                    s = unicode(current) + unicode(next)
                    s = BeautifulSoup.NavigableString(s)
                    current.replaceWith(s)
                    return s
                else:
                    # The current string is as big as its going to get.
                    # Check if you can split off some whitespace from
                    # the beginning.
                    p = unicode(current)
                    split = start_space.split(p)

                    if len(split) > 1 and split[1]:
                        # BeautifulSoup can't cope when we insert
                        # an empty text node.

                        par = current.parent
                        index = par.contents.index(current)
                        current.extract()

                        w = BeautifulSoup.NavigableString(" ")
                        s = BeautifulSoup.NavigableString(split[1])

                        par.insert(index, s)
                        par.insert(index, w)
            return next

        def separate_all_strings(node):
            if is_tag(node):
                contents = [elem for elem in node.contents]
                contents.append(None)

                current = None
                for next in contents:
                    current = separate_strings(current, next)

        def reassign_whitespace():
            strings = self.root.findAll(text=True)
            i = len(strings) - 1

            after = None
            while i >= 0:
                current = strings[i]
                if is_text(after) and not after.strip():
                    # if 'after' holds only whitespace,
                    # remove it, and append it to 'current'
                    s = unicode(current) + unicode(after)
                    s = BeautifulSoup.NavigableString(s)
                    current.replaceWith(s)
                    after.extract()

                    current = s

                after = current
                i -= 1

        condense_whitespace()
        dfs(self.root, separate_all_strings)
        reassign_whitespace()
        condense_whitespace()


    def br_to_p(self):
        """
        >>> c = Cleaner("", "br_to_p")
        >>> c('<p>A<br />B</p>')
        u'<p>A</p><p>B</p>'
        >>> c('A<br />B')
        u'<p>A</p><p>B</p>'
        """
        block_elems = self.settings['block_elements'].copy()
        block_elems['br'] = None
        block_elems['p'] = None

        while True :
            next_br = self.root.find('br')
            if not next_br: break
            parent = next_br.parent
            self.wrap_string('p', start_at=parent, block_elems = block_elems)
            while True:
                useless_br=parent.find('br', recursive=False)
                if not useless_br: break
                useless_br.extract()
            if parent.name == 'p':
                self.disgorge_elem(parent)

    def add_nofollow(self):
        """
        >>> c = Cleaner("", "add_nofollow")
        >>> c('<p><a href="mysite.com">site</a></p>')
        u'<p><a href="mysite.com" rel="nofollow">site</a></p>'
        """
        for a in self.root.findAll(name='a'):
            rel = a.get('rel', u"")
            sep = u" "
            nofollow = u"nofollow"

            r = rel.split(sep)
            if not nofollow in r:
                r.append(nofollow)
            rel = sep.join(r).strip()
            a['rel'] = rel

    def make_links(self):
        """
        Search through all text nodes, creating <a>
        tags for text that looks like a URL.
        >>> c = Cleaner("", "make_links")
        >>> c('check out my website at mysite.com')
        u'check out my website at <a href="mysite.com">mysite.com</a>'
        """
        def linkify_text_node(node):
            index = node.parent.contents.index(node)
            parent = node.parent
            string = unicode(node)

            matches = URL_RE.finditer(string)
            end_re = re.compile('\W')
            new_content = []
            o = 0
            for m in matches:
                s, e = m.span()

                # if there are no more characters after the link
                # or if the character after the link is not a 'word character'
                if e >= len(string) or end_re.match(string[e]):
                    link = BeautifulSoup.Tag(self._soup, 'a', attrs=[('href',m.group())])
                    link_text = BeautifulSoup.NavigableString(m.group())
                    link.insert(0, link_text)
                    if o < s: # BeautifulSoup can't cope when we insert an empty text node
                        previous_text = BeautifulSoup.NavigableString(string[o:s])
                        new_content.append(previous_text)
                    new_content.append(link)
                    o = e

            # Only do actual replacement if necessary
            if o > 0:
                if o < len(string):
                    final_text = BeautifulSoup.NavigableString(string[o:])
                    new_content.append(final_text)

                # replace the text node with the new text
                node.extract()
                for x in new_content:
                    parent.insert(index, x)
                    index += 1

        # run the algorithm
        for node in self.root.findAll(text=True):
            # Only linkify if this node is not a decendant of a link already
            if not node.findParents(name='a'):
                linkify_text_node(node)



    def rename_tags(self):
        """
        >>> c = Cleaner("", "rename_tags", elem_map={'i': 'em'})
        >>> c('<b>A<i>B</i></b>')
        u'<b>A<em>B</em></b>'
        """
        for tag in self.root.findAll(self.settings['elem_map']) :
            tag.name = self.settings['elem_map'][tag.name]

    def wrap_string(self, wrapping_element = None, start_at=None, block_elems=None):
        """
        takes an html fragment, which may or may not have a single containing element,
        and guarantees what the tag name of the topmost elements are.
        TODO: is there some simpler way than a state machine to do this simple thing?
        >>> c = Cleaner("", "wrap_string")
        >>> c('A <strong>B C</strong>D')
        u'<p>A <strong>B C</strong>D</p>'
        >>> c('A <p>B C</p>D')
        u'<p>A </p><p>B C</p><p>D</p>'
        """
        if not start_at : start_at = self.root
        if not block_elems : block_elems = self.settings['block_elements']
        e = (wrapping_element or self.settings['wrapping_element'])
        paragraph_list = []
        children = [elem for elem in start_at.contents]

        # Remove all the children
        for elem in children:
            elem.extract()
        children.append(Stop())

        last_state = 'block'
        paragraph = BeautifulSoup.Tag(self._soup, e)

        # Wrap each inline element a tag specified by 'e'
        for node in children :
            if isinstance(node, Stop) :
                state = 'end'
            elif hasattr(node, 'name') and node.name in block_elems:
                state = 'block'
            else:
                state = 'inline'

            if last_state == 'block' and state == 'inline':
                #collate inline elements
                paragraph = BeautifulSoup.Tag(self._soup, e)

            if state == 'inline' :
                paragraph.append(node)

            if ((state <> 'inline') and last_state == 'inline') :
                paragraph_list.append(paragraph)

            if state == 'block' :
                paragraph_list.append(node)

            last_state = state

        # Add all of the newly wrapped children back
        paragraph_list.reverse()
        for paragraph in paragraph_list:
            start_at.insert(0, paragraph)

    def strip_empty_tags(self):
        """
        strip out all empty tags
        >>> c = Cleaner("", "strip_empty_tags")
        >>> c('<p>A</p><p></p><p>B</p><p></p>')
        u'<p>A</p><p>B</p>'
        >>> c('<p><a></a></p>')
        u'<p></p>'
        """
        def is_text(node):
            return isinstance(node, BeautifulSoup.NavigableString)

        def is_tag(node):
            return isinstance(node, BeautifulSoup.Tag)

        def is_empty(node):
            if is_text(node):
                a = not unicode(node)

            if is_tag(node):
                a = not node.contents

            return bool(a)

        def contains_only_whitespace(node):
            if is_tag(node):
                if not any([not is_text(s) for s in node.contents]):
                    if not any([unicode(s).strip() for s in node.contents]):
                        return True
            return False


        def dfs(node, func, i=1):
            if is_tag(node):
                contents = [x for x in node.contents]
                for x in contents:
                    dfs(x, func, i+1)
            func(node, i)

        def strip_empty(node, i):
            if is_empty(node):
                node.extract()
            elif contains_only_whitespace(node):
                try:
                    self.disgorge_elem(node)
                except AttributeError:
                    # Don't complain when trying to disgorge the root element,
                    # as it'll be removed later anyway.
                    pass

        dfs(self.root, strip_empty)

    def rebase_links(self, original_url="", new_url ="") :
        if not original_url : original_url = self.settings.get('original_url', '')
        if not new_url : new_url = self.settings.get('new_url', '')
        raise NotImplementedError

    def encode_xml_specials(self) :
        """
        BeautifulSoup will let some dangerous xml entities hang around
        in the navigable strings. destroy all monsters.
        >>> c = Cleaner(auto_clean=True, encode_xml_specials=True)
        >>> c('<<<<<')
        u'&lt;&lt;&lt;&lt;'
        """
        for string in self.root.findAll(text=True):
            s = unicode(string)
            s = encode_xhtml_entities(s)
            s = BeautifulSoup.NavigableString(s)
            string.replaceWith(s)

    def disgorge_elem(self, elem):
        """
        remove the given element from the soup and replaces it with its own contents
        actually tricky, since you can't replace an element with an list of elements
        using replaceWith
        >>> disgorgeable_string = '<body>A <em>B</em> C</body>'
        >>> c = Cleaner()
        >>> c.string = disgorgeable_string
        >>> elem = c._soup.find('em')
        >>> c.disgorge_elem(elem)
        >>> c.string
        u'<body>A B C</body>'
        >>> c.string = disgorgeable_string
        >>> elem = c._soup.find('body')
        >>> c.disgorge_elem(elem)
        >>> c.string
        u'A <em>B</em> C'
        >>> c.string = '<div>A <div id="inner">B C</div></div>'
        >>> elem = c._soup.find(id="inner")
        >>> c.disgorge_elem(elem)
        >>> c.string
        u'<div>A B C</div>'
        """
        if elem == self.root :
            raise AttributeError, "Can't disgorge root"

        # With in-place modification, BeautifulSoup occasionally can return
        # elements that think they are orphans
        # this lib is full of workarounds, but it's worth checking
        parent = elem.parent
        if parent == None:
            raise AttributeError, "AAAAAAAAGH! NO PARENTS! DEATH!"

        i = None
        for i in range(len(parent.contents)) :
            if parent.contents[i] == elem :
                index = i
                break

        elem.extract()

        #the proceeding method breaks horribly, sporadically.
        # for i in range(len(elem.contents)) :
        #     elem.contents[i].extract()
        #     parent.contents.insert(index+i, elem.contents[i])
        # return
        self._safe_inject(parent, index, elem.contents)

    def _safe_inject(self, dest, dest_index, node_list):
        #BeautifulSoup result sets look like lists but don't behave right
        # i.e. empty ones are still True,
        if not len(node_list) : return
        node_list = [i for i in node_list]
        node_list.reverse()
        for i in node_list :
            dest.insert(dest_index, i)


class Htmlator(object) :
    """
    converts a string into a series of html paragraphs
    """
    settings = {
        "encode_xml_specials" : True,
        "is_plaintext" : True,
        "convert_newlines" : False,
        "make_links" : True,
        "auto_convert" : False,
        "valid_schemes" : valid_schemes,
    }
    def __init__(self, string = "",  **kwargs):
        self.settings.update(kwargs)
        super(Htmlator, self).__init__(string, **kwargs)
        self.string = string

    def _set_string(self, string):
        self._string = unicode(string)
        if self.settings['auto_convert'] : self.convert()

    def _get_string(self):
        return self._string

    string = property(_get_string, _set_string)

    def __call__(self, string):
        """
        convenience method supporting one-step calling of an instance
        as a string cleaning function
        """
        self.string = string
        self.convert()
        return self.string

    def convert(self):
        for method in ["encode_xml_specials", "convert_newlines",
          "make_links"] :
            if self.settings.get(method, False):
                getattr(self, method)()

    def encode_xml_specials(self) :
        self._string = entities_to_unicode(self._string)
        self._string = encode_xhtml_entities(self._string)


    def make_links(self):
        matches = URL_RE.finditer(self._string)
        end_re = re.compile('\W')
        o = 0
        for m in matches:
            s, e = m.span()

            # if there are no more characters after the link
            # or if the character after the link is not a 'word character'
            if e > len(self._string) or end_re.match(self._string[e]):
                # take into account the added length of previous links
                s, e = s+o, e+o
                link = "<a href=\"%s\">%s</a>" % (m.group(), m.group())
                o += len(link) - len(m.group())
                self._string = self._string[:s] + link + self._string[e:]

    def convert_newlines(self) :
        # remove whitespace
        self._string = "\n".join([l.strip() for l in self.string.split("\n")])
        # remove duplicate line breaks
        self._string = re.sub("\n+", "\n", self._string).strip("\n")
        # wrap each line in <p> tags.
        self.string = ''.join([
            '<p>' + line.strip() + '</p>' for line in self.string.split('\n')
        ])

def _test():
    import doctest
    doctest.testmod()

if __name__ == "__main__":
    _test()


# def cast_input_to_soup(fn):
#     """
#     Decorate function to handle strings as BeautifulSoups transparently
#     """
#     def stringy_version(input, *args, **kwargs) :
#         if not isinstance(input,BeautifulSoup) :
#             input=BeautifulSoup(input)
#         return fn(input, *args, **kwargs)
#     return stringy_version

########NEW FILE########
__FILENAME__ = env

from alembic import context
from sqlalchemy import engine_from_config, pool

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

if config.config_file_name is not None:
    # set up loggers
    from logging.config import fileConfig
    fileConfig(config.config_file_name)

db_url = config.get_main_option("sqlalchemy.url")
version_table_name = config.get_main_option('version_table') or None
configure_opts = dict()
if version_table_name:
    configure_opts['version_table'] = version_table_name

def run_migrations_offline():
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    context.configure(url=db_url, **configure_opts)
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    engine = engine_from_config(
                config.get_section(config.config_ini_section),
                prefix='sqlalchemy.',
                poolclass=pool.NullPool)

    connection = engine.connect()
    context.configure(connection=connection, **configure_opts)

    try:
        with context.begin_transaction():
            context.run_migrations()
    finally:
        connection.close()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()


########NEW FILE########
__FILENAME__ = util
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code contained in this file is licensed under the GPLv3 or
# (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.

import logging

from alembic.config import Config
from alembic.environment import EnvironmentContext
from alembic.script import ScriptDirectory
from sqlalchemy import Column, Integer, MetaData, Table, Unicode, UnicodeText

from mediadrop.model import metadata, DBSession

__all__ = ['MediaDropMigrator', 'PluginDBMigrator']

migrate_to_alembic_mapping = {
    49: None,
    50: u'50258ad7a96d',
    51: u'51c050c6bca0',
    52: u'432df7befe8d',
    53: u'4d27ff5680e5',
    54: u'280565a54124',
    55: u'16ed4c91d1aa',
    56: u'30bb0d88d139',
    57: u'3b2f74a50399',
}

fake_meta = MetaData()
migrate_table = Table('migrate_version', fake_meta,
    Column('repository_id', Unicode(250), autoincrement=True, primary_key=True),
    Column('repository_path', UnicodeText, nullable=True),
    Column('version', Integer, nullable=True),
)

def prefix_table_name(conf, table_name):
    table_prefix = conf.get('db_table_prefix', None)
    if not table_prefix:
        return table_name
    # treat 'foo' and 'foo_' the same so we're not too harsh on the users
    normalized_prefix = table_prefix.rstrip('_')
    return normalized_prefix + '_' + table_name


class AlembicMigrator(object):
    def __init__(self, context=None, log=None, plugin_name=None, default_data_callable=None):
        self.context = context
        self.log = log or logging.getLogger(__name__)
        self.plugin_name = plugin_name
        self.default_data_callable = default_data_callable
    
    @classmethod
    def init_environment_context(cls, conf):
        file_template = conf.get('alembic.file_template', '%%(day).3d-%%(rev)s-%%(slug)s')
        script_location = conf.get('alembic.script_location', 'mediadrop:migrations')
        version_table = conf.get('alembic.version_table', 'alembic_migrations')
        
        alembic_cfg = Config(ini_section='main')
        alembic_cfg.set_main_option('script_location', script_location)
        alembic_cfg.set_main_option('sqlalchemy.url', conf['sqlalchemy.url'])
        # TODO: add other sqlalchemy options
        alembic_cfg.set_main_option('file_template', file_template)
        
        script = ScriptDirectory.from_config(alembic_cfg)
        def upgrade(current_db_revision, context):
            return script._upgrade_revs('head', current_db_revision)
        
        table_name = prefix_table_name(conf, table_name=version_table)
        return EnvironmentContext(alembic_cfg, script, fn=upgrade, version_table=table_name)
    
    def db_needs_upgrade(self):
        return (self.head_revision() != self.current_revision())
    
    def is_db_scheme_current(self):
        return (not self.db_needs_upgrade())
    
    def current_revision(self):
        if not self.alembic_table_exists():
            return None
        self.context.configure(connection=metadata.bind.connect(), transactional_ddl=True)
        migration_context = self.context.get_context()
        return migration_context.get_current_revision()
    
    def head_revision(self):
        return self.context.get_head_revision()
    
    def _table_exists(self, table_name):
        engine = metadata.bind
        db_connection = engine.connect()
        exists = engine.dialect.has_table(db_connection, table_name)
        return exists
    
    def alembic_table_exists(self):
        table_name = self.context.context_opts.get('version_table')
        return self._table_exists(table_name)
    
    def migrate_db(self):
        target = 'MediaDrop'
        if self.plugin_name:
            target = self.plugin_name + ' plugin'
        
        if self.current_revision() is None:
            if self.alembic_table_exists() and (self.head_revision() is None):
                # The plugin has no migrations but db_defaults: adding default
                # data should only happen once.
                # alembic will create the migration table after the first run
                # but as we don't have any migrations "self.head_revision()"
                # is still None.
                return
            self.log.info('Initializing database for %s.' % target)
            self.init_db()
            return
        self.log.info('Running any new migrations for %s, if there are any' % target)
        self.context.configure(connection=metadata.bind.connect(), transactional_ddl=True)
        with self.context:
            self.context.run_migrations()
    
    def init_db(self, revision='head'):
        self.stamp(revision)
    
    # -----------------------------------------------------------------------------
    # mostly copied from alembic 0.5.0
    # The problem in alembic.command.stamp() is that it builds a new 
    # EnvironmentContext which does not have any ability to configure the
    # version table name and MediaDrop uses a custom table name.
    def stamp(self, revision):
        """'stamp' the revision table with the given revision; don't
        run any migrations."""
        script = self.context.script
        def do_stamp(rev, context):
            if context.as_sql:
                current = False
            else:
                current = context._current_rev()
            dest = script.get_revision(revision)
            if dest is not None:
                dest = dest.revision
            context._update_current_rev(current, dest)
            return []
        
        context_opts = self.context.context_opts.copy()
        context_opts.update(dict(
            script=script,
            fn=do_stamp,
        ))
        stamp_context = EnvironmentContext(self.context.config, **context_opts)
        with stamp_context:
            script.run_env()
    # --------------------------------------------------------------------------


class MediaDropMigrator(AlembicMigrator):
    @classmethod
    def from_config(cls, conf, **kwargs):
        context = cls.init_environment_context(conf)
        return cls(context=context, **kwargs)
    
    def map_migrate_version(self):
        migrate_version_query = migrate_table.select(
            migrate_table.c.repository_id == u'MediaCore Migrations'
        )
        result = DBSession.execute(migrate_version_query).fetchone()
        db_migrate_version = result.version
        if db_migrate_version in migrate_to_alembic_mapping:
            return migrate_to_alembic_mapping[db_migrate_version]
        
        earliest_upgradable_version = sorted(migrate_to_alembic_mapping)[0]
        if db_migrate_version < earliest_upgradable_version:
            error_msg = ('Upgrading from such an old version of MediaDrop is not '
                'supported. Your database is at version %d but upgrades are only '
                'supported from MediaCore CE 0.9.0 (DB version %d). Please upgrade '
                '0.9.0 first.')
            self.log.error(error_msg % (db_migrate_version, earliest_upgradable_version))
        else:
            self.log.error('Unknown DB version %s. Can not upgrade to alembic' % db_migrate_version)
        raise AssertionError('unsupported DB migration version.')
    
    def migrate_table_exists(self):
        return self._table_exists('migrate_version')


class PluginDBMigrator(AlembicMigrator):
    @classmethod
    def from_config(cls, plugin, conf, **kwargs):
        config = {
            'alembic.version_table': plugin.name+'_migrations',
            'alembic.script_location': '%s:%s' % (plugin.package_name, 'migrations'),
            'sqlalchemy.url': conf['sqlalchemy.url'],
        }
        context = cls.init_environment_context(config)
        return PluginDBMigrator(context=context, plugin_name=plugin.name,
            default_data_callable=plugin.add_db_defaults, **kwargs)
    
    # LATER: this code goes into the main AlembicMigrator once the MediaDrop
    # initialiation code is moved from websetup.py to db_defaults.py
    def init_db(self, revision='head'):
        if self.default_data_callable:
            self.default_data_callable()
            self.stamp(revision)
        else:
            self.migrate_db()

########NEW FILE########
__FILENAME__ = 000-50258ad7a96d-add-display-footer-setting
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code contained in this file is licensed under the GPLv3 or
# (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.
"""add display footer setting

add a setting to configure footer visibility (previously migrate script v050)

added: 2011-02-06 (v0.9.1)
previously migrate script v050

Revision ID: 50258ad7a96d
Revises: None
Create Date: 2013-05-14 14:45:23.119676
"""

# revision identifiers, used by Alembic.
revision = '50258ad7a96d'
down_revision = None

from alembic.op import execute, inline_literal
from sqlalchemy import Integer, Unicode, UnicodeText
from sqlalchemy import Column, MetaData,  Table

# -- table definition ---------------------------------------------------------
metadata = MetaData()
settings = Table('settings', metadata,
    Column('id', Integer, autoincrement=True, primary_key=True),
    Column('key', Unicode(255), nullable=False, unique=True),
    Column('value', UnicodeText),
    mysql_engine='InnoDB',
    mysql_charset='utf8',
)

# -- helpers ------------------------------------------------------------------
def insert_setting(key, value):
    execute(
        settings.insert().\
            values({
                'key': inline_literal(key),
                'value': inline_literal(value),
            })
    )

def delete_setting(key):
    execute(
        settings.delete().\
            where(settings.c.key==inline_literal(key))
    )
# -----------------------------------------------------------------------------

SETTINGS = [
    (u'appearance_display_mediacore_footer', u'True'),
    (u'appearance_display_mediacore_credits', u'True'),
]

def upgrade():
    for key, value in SETTINGS:
        insert_setting(key, value)

def downgrade():
    for key, value in SETTINGS:
        delete_setting(key)

########NEW FILE########
__FILENAME__ = 001-51c050c6bca0-add_player_appearance_settings
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code contained in this file is licensed under the GPLv3 or
# (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.
"""Add player appearance settings

add configuration settings for buttons on the player bar

added: 2011-02-07 (v0.9.1)
previously migrate script v051

Revision ID: 51c050c6bca0
Revises: 50258ad7a96d
Create Date: 2013-05-14 22:35:41.914345
"""

# revision identifiers, used by Alembic.
revision = '51c050c6bca0'
down_revision = '50258ad7a96d'

from alembic.op import execute, inline_literal
from sqlalchemy import Integer, Unicode, UnicodeText
from sqlalchemy import Column, MetaData,  Table

# -- table definition ---------------------------------------------------------
metadata = MetaData()
settings = Table('settings', metadata,
    Column('id', Integer, autoincrement=True, primary_key=True),
    Column('key', Unicode(255), nullable=False, unique=True),
    Column('value', UnicodeText),
    mysql_engine='InnoDB',
    mysql_charset='utf8',
)

# -- helpers ------------------------------------------------------------------
def insert_setting(key, value):
    execute(
        settings.insert().\
            values({
                'key': inline_literal(key),
                'value': inline_literal(value),
            })
    )

def delete_setting(key):
    execute(
        settings.delete().\
            where(settings.c.key==inline_literal(key))
    )
# -----------------------------------------------------------------------------

SETTINGS = [
    (u'appearance_show_download', u'True'),
    (u'appearance_show_share', u'True'),
    (u'appearance_show_embed', u'True'),
    (u'appearance_show_widescreen', u'True'),
    (u'appearance_show_popout', u'True'),
    (u'appearance_show_like', u'True'),
    (u'appearance_show_dislike', u'True'),
]

def upgrade():
    for key, value in SETTINGS:
        insert_setting(key, value)

def downgrade():
    for key, value in SETTINGS:
        delete_setting(key)

########NEW FILE########
__FILENAME__ = 002-432df7befe8d-add_facebook_comments_settings
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code contained in this file is licensed under the GPLv3 or
# (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.
"""Add facebook comments settings

added: 2011-01-27 (v0.9.1)
previously migrate script v052

Revision ID: 432df7befe8d
Revises: 51c050c6bca0
Create Date: 2013-05-14 22:36:07.772713
"""

# revision identifiers, used by Alembic.
revision = '432df7befe8d'
down_revision = '51c050c6bca0'

from alembic.op import execute, inline_literal
from sqlalchemy import Integer, Unicode, UnicodeText
from sqlalchemy import Column, MetaData,  Table

# -- table definition ---------------------------------------------------------
metadata = MetaData()
settings = Table('settings', metadata,
    Column('id', Integer, autoincrement=True, primary_key=True),
    Column('key', Unicode(255), nullable=False, unique=True),
    Column('value', UnicodeText),
    mysql_engine='InnoDB',
    mysql_charset='utf8',
)

# -- helpers ------------------------------------------------------------------
def insert_setting(key, value):
    execute(
        settings.insert().\
            values({
                'key': inline_literal(key),
                'value': inline_literal(value),
            })
    )

def delete_setting(key):
    execute(
        settings.delete().\
            where(settings.c.key==inline_literal(key))
    )
# -----------------------------------------------------------------------------

SETTINGS = [
    (u'comments_engine', u'mediacore'),
    (u'facebook_appid', u''),
]

def upgrade():
    for key, value in SETTINGS:
        insert_setting(key, value)

def downgrade():
    for key, value in SETTINGS:
        delete_setting(key)


########NEW FILE########
__FILENAME__ = 003-4d27ff5680e5-normalize_comment_approval_setting
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code contained in this file is licensed under the GPLv3 or
# (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.
"""Normalize comment approval setting

normalize value for comment approval setting so that it can be used a boolean 
directly. This migration can not be run offline.

added: 2011-03-13 (v0.9.1)
previously migrate script v053

Revision ID: 4d27ff5680e5
Revises: 432df7befe8d
Create Date: 2013-05-14 22:36:27.130301
"""

# revision identifiers, used by Alembic.
revision = '4d27ff5680e5'
down_revision = '432df7befe8d'

from alembic import context
from alembic.op import execute, inline_literal
from sqlalchemy import Integer, Unicode, UnicodeText
from sqlalchemy import Column, MetaData,  Table

# -- table definition ---------------------------------------------------------
metadata = MetaData()
settings = Table('settings', metadata,
    Column('id', Integer, autoincrement=True, primary_key=True),
    Column('key', Unicode(255), nullable=False, unique=True),
    Column('value', UnicodeText),
    mysql_engine='InnoDB',
    mysql_charset='utf8',
)

# -- helpers ------------------------------------------------------------------
def insert_setting(key, value):
    execute(
        settings.insert().\
            values({
                'key': inline_literal(key),
                'value': inline_literal(value),
            })
    )

def delete_setting(key):
    execute(
        settings.delete().\
            where(settings.c.key==inline_literal(key))
    )
# -----------------------------------------------------------------------------

SETTING_KEY = u'req_comment_approval'


def upgrade():
    if context.is_offline_mode():
        raise AssertionError('This migration can not be run in offline mode.')
    connection = context.get_context().connection
    query = settings.select(settings.c.key == SETTING_KEY)
    result = connection.execute(query).fetchone()
    
    current_value = result.value
    if current_value == u'true':
        new_value = u'True'
    else:
        new_value = u''
    execute(
        settings.update().\
            where(settings.c.key==inline_literal(SETTING_KEY)).\
            values({
                'value': inline_literal(new_value),
            })
    )

def downgrade():
    # no action necessary
    pass

########NEW FILE########
__FILENAME__ = 004-280565a54124-add_custom_head_tags
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code contained in this file is licensed under the GPLv3 or
# (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.
"""add custom head tags

add setting for custom tags (HTML) in <head> section

added: 2012-02-13 (v0.10dev)
previously migrate script v054

Revision ID: 280565a54124
Revises: 4d27ff5680e5
Create Date: 2013-05-14 22:38:02.552230
"""

# revision identifiers, used by Alembic.
revision = '280565a54124'
down_revision = '4d27ff5680e5'

from alembic.op import execute, inline_literal
from sqlalchemy import Integer, Unicode, UnicodeText
from sqlalchemy import Column, MetaData,  Table

# -- table definition ---------------------------------------------------------
metadata = MetaData()
settings = Table('settings', metadata,
    Column('id', Integer, autoincrement=True, primary_key=True),
    Column('key', Unicode(255), nullable=False, unique=True),
    Column('value', UnicodeText),
    mysql_engine='InnoDB',
    mysql_charset='utf8',
)

# -- helpers ------------------------------------------------------------------
def insert_setting(key, value):
    execute(
        settings.insert().\
            values({
                'key': inline_literal(key),
                'value': inline_literal(value),
            })
    )

def delete_setting(key):
    execute(
        settings.delete().\
            where(settings.c.key==inline_literal(key))
    )
# -----------------------------------------------------------------------------

SETTINGS = [
    (u'appearance_custom_head_tags', u''),
]

def upgrade():
    for key, value in SETTINGS:
        insert_setting(key, value)

def downgrade():
    for key, value in SETTINGS:
        delete_setting(key)


########NEW FILE########
__FILENAME__ = 005-16ed4c91d1aa-add_anonymous_and_authenticated_groups
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code contained in this file is licensed under the GPLv3 or
# (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.
"""add anonymous and authenticated groups

create groups for "anonymous" and "authenticated" users

added: 2012-12-11 (v0.10dev)
previously migrate script v055

Revision ID: 16ed4c91d1aa
Revises: 280565a54124
Create Date: 2013-05-14 22:38:25.194543
"""

# revision identifiers, used by Alembic.
revision = '16ed4c91d1aa'
down_revision = '280565a54124'

from datetime import datetime

from alembic.op import execute, inline_literal
from sqlalchemy import Column, MetaData, Table
from sqlalchemy import DateTime, ForeignKey, Integer, Unicode, UnicodeText

# -- table definition ---------------------------------------------------------
metadata = MetaData()
groups = Table('groups', metadata,
    Column('group_id', Integer, autoincrement=True, primary_key=True),
    Column('group_name', Unicode(16), unique=True, nullable=False),
    Column('display_name', Unicode(255)),
    Column('created', DateTime, default=datetime.now),
    mysql_engine='InnoDB',
    mysql_charset='utf8',
)


def add_group(group_name, display_name):
    execute(
        groups.insert().\
            values({
                'group_name': inline_literal(group_name),
                'display_name': inline_literal(display_name),
            })
    )

def upgrade():
    add_group(group_name=u'anonymous', display_name=u'Everyone (including guests)')
    add_group(group_name=u'authenticated', display_name=u'Logged in users')

def downgrade():
    execute(
        groups.delete().\
            where(groups.c.group_name.in_([u'anonymous', u'authenticated']))
    )
    # assignments of users to 'anonymous' and 'authenticated' are deleted 
    # automatically because of existing ForeignKey constraint in the DB
    # (ON DELETE CASCADE ON UPDATE CASCADE)


########NEW FILE########
__FILENAME__ = 006-30bb0d88d139-add_view_permission
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code contained in this file is licensed under the GPLv3 or
# (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.
"""add view permission

added: 2012-12-11 (v0.10dev)
previously migrate script v056

Revision ID: 30bb0d88d139
Revises: 16ed4c91d1aa
Create Date: 2013-05-14 22:38:38.751713
"""

# revision identifiers, used by Alembic.
revision = '30bb0d88d139'
down_revision = '16ed4c91d1aa'

from datetime import datetime

from alembic.op import execute, inline_literal
from sqlalchemy import Column, MetaData, Table
from sqlalchemy import and_, DateTime, ForeignKey, Integer, Unicode, UnicodeText
from sqlalchemy.sql import select

# -- table definition ---------------------------------------------------------
metadata = MetaData()
groups = Table('groups', metadata,
    Column('group_id', Integer, autoincrement=True, primary_key=True),
    Column('group_name', Unicode(16), unique=True, nullable=False),
    Column('display_name', Unicode(255)),
    Column('created', DateTime, default=datetime.now),
    mysql_engine='InnoDB',
    mysql_charset='utf8',
)

permissions = Table('permissions', metadata,
    Column('permission_id', Integer, autoincrement=True, primary_key=True),
    Column('permission_name', Unicode(16), unique=True, nullable=False),
    Column('description', Unicode(255)),
    mysql_engine='InnoDB',
    mysql_charset='utf8',
)

groups_permissions = Table('groups_permissions', metadata,
    Column('group_id', Integer, ForeignKey('groups.group_id',
        onupdate="CASCADE", ondelete="CASCADE")),
    Column('permission_id', Integer, ForeignKey('permissions.permission_id',
        onupdate="CASCADE", ondelete="CASCADE")),
    mysql_engine='InnoDB',
    mysql_charset='utf8',
)

# -- helpers ------------------------------------------------------------------
def insert_permission(permission_name, description):
    execute(
        permissions.insert().\
            values({
                'permission_name': inline_literal(permission_name),
                'description': inline_literal(description),
            })
    )

def delete_permission(permission_name):
    execute(
        permissions.delete().\
            where(permissions.c.permission_name==inline_literal(permission_name))
    )

def grant_permission_for_group(permission_name, group_name):
    execute(
        groups_permissions.insert().values(
            group_id=select([groups.c.group_id]).where(groups.c.group_name == group_name),
            permission_id=select([permissions.c.permission_id]).where(permissions.c.permission_name == permission_name)
        )
    )

def revoke_permission_for_group(permission_name, group_name):
    group_subquery = select([groups.c.group_id]).\
        where(groups.c.group_name == group_name)
    permission_subquery = select([permissions.c.permission_id]).\
        where(permissions.c.permission_name == permission_name)
    
    execute(
        groups_permissions.delete().where(and_(
            groups_permissions.c.group_id == group_subquery,
            groups_permissions.c.permission_id == permission_subquery
        ))
    )

# -----------------------------------------------------------------------------


GROUP_NAMES = [u'anonymous', u'admins', u'editors']

def upgrade():
    insert_permission(u'view', u'View published media')
    for group_name in GROUP_NAMES:
        grant_permission_for_group(u'view', group_name)

def downgrade():
    for group_name in GROUP_NAMES:
        revoke_permission_for_group(u'view', group_name)
    delete_permission(u'view')


########NEW FILE########
__FILENAME__ = 007-3b2f74a50399-add_upload_permissio
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code contained in this file is licensed under the GPLv3 or
# (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.
"""add upload permission

added: 2012-12-22 (v0.10dev)
previously migrate script v057

Revision ID: 3b2f74a50399
Revises: 30bb0d88d139
Create Date: 2013-05-14 22:38:42.221082
"""

# revision identifiers, used by Alembic.
revision = '3b2f74a50399'
down_revision = '30bb0d88d139'

from datetime import datetime

from alembic.op import execute, inline_literal
from sqlalchemy import Column, MetaData, Table
from sqlalchemy import and_, DateTime, ForeignKey, Integer, Unicode, UnicodeText
from sqlalchemy.sql import select

# -- table definition ---------------------------------------------------------
metadata = MetaData()
groups = Table('groups', metadata,
    Column('group_id', Integer, autoincrement=True, primary_key=True),
    Column('group_name', Unicode(16), unique=True, nullable=False),
    Column('display_name', Unicode(255)),
    Column('created', DateTime, default=datetime.now),
    mysql_engine='InnoDB',
    mysql_charset='utf8',
)

permissions = Table('permissions', metadata,
    Column('permission_id', Integer, autoincrement=True, primary_key=True),
    Column('permission_name', Unicode(16), unique=True, nullable=False),
    Column('description', Unicode(255)),
    mysql_engine='InnoDB',
    mysql_charset='utf8',
)

groups_permissions = Table('groups_permissions', metadata,
    Column('group_id', Integer, ForeignKey('groups.group_id',
        onupdate="CASCADE", ondelete="CASCADE")),
    Column('permission_id', Integer, ForeignKey('permissions.permission_id',
        onupdate="CASCADE", ondelete="CASCADE")),
    mysql_engine='InnoDB',
    mysql_charset='utf8',
)

# -- helpers ------------------------------------------------------------------
def insert_permission(permission_name, description):
    execute(
        permissions.insert().\
            values({
                'permission_name': inline_literal(permission_name),
                'description': inline_literal(description),
            })
    )

def delete_permission(permission_name):
    execute(
        permissions.delete().\
            where(permissions.c.permission_name==inline_literal(permission_name))
    )

def grant_permission_for_group(permission_name, group_name):
    execute(
        groups_permissions.insert().values(
            group_id=select([groups.c.group_id]).where(groups.c.group_name == group_name),
            permission_id=select([permissions.c.permission_id]).where(permissions.c.permission_name == permission_name)
        )
    )

def revoke_permission_for_group(permission_name, group_name):
    group_subquery = select([groups.c.group_id]).\
        where(groups.c.group_name == group_name)
    permission_subquery = select([permissions.c.permission_id]).\
        where(permissions.c.permission_name == permission_name)
    
    execute(
        groups_permissions.delete().where(and_(
            groups_permissions.c.group_id == group_subquery,
            groups_permissions.c.permission_id == permission_subquery
        ))
    )

# -----------------------------------------------------------------------------


GROUP_NAMES = [u'anonymous', u'admins', u'editors']

def upgrade():
    insert_permission(u'upload', u'Can upload new media')
    for group_name in GROUP_NAMES:
        grant_permission_for_group(u'upload', group_name)

def downgrade():
    for group_name in GROUP_NAMES:
        revoke_permission_for_group(u'upload', group_name)
    delete_permission(u'upload')


########NEW FILE########
__FILENAME__ = 008-4c9f4cfc6085-drop_sqlalchemy_migrate_table
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code contained in this file is licensed under the GPLv3 or
# (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.
"""clear SQLAlchemy migrate information for MediaCore (switching to alembic)

added: 2013-05-15 (v0.11dev)

Revision ID: 4c9f4cfc6085
Revises: 3b2f74a50399
Create Date: 2013-05-14 22:42:51.320534
"""

from alembic.op import execute, inline_literal

from sqlalchemy import Integer, Unicode, UnicodeText
from sqlalchemy.sql import column, table

# revision identifiers, used by Alembic.
revision = '4c9f4cfc6085'
down_revision = '3b2f74a50399'


migrate_table = table('migrate_version', 
    column('repository_id', Unicode(250)),
    column('repository_path', UnicodeText),
    column('version', Integer),
)


def upgrade():
    # let's stay on the safe side: theoretically the migrate table might have
    # been used by other plugins.
    execute(
        migrate_table.delete().\
            where(migrate_table.c.repository_id==inline_literal(u'MediaCore Migrations'))
    )

def downgrade():
    execute(
        migrate_table.insert().\
            values({
                'repository_id': inline_literal(u'MediaCore Migrations'),
                'version': inline_literal(57),
            })
    )


########NEW FILE########
__FILENAME__ = 009-47f9265e77e5-mediadrop_comments_engine
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code contained in this file is licensed under the GPLv3 or
# (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.
"""MediaDrop comments engine

replace the comments engine settings value 'mediacore' with 'builtin'

added: 2013-11-01 (v0.11dev)

Revision ID: 47f9265e77e5
Revises: 4c9f4cfc6085
Create Date: 2013-11-01 10:15:02.948019
"""

# revision identifiers, used by Alembic.
revision = '47f9265e77e5'
down_revision = '4c9f4cfc6085'

from alembic.op import execute, inline_literal
from sqlalchemy import and_
from sqlalchemy.types import Integer, Unicode, UnicodeText
from sqlalchemy.schema import Column, MetaData, Table

# -- table definition ---------------------------------------------------------
metadata = MetaData()
settings = Table('settings', metadata,
    Column('id', Integer, autoincrement=True, primary_key=True),
    Column('key', Unicode(255), nullable=False, unique=True),
    Column('value', UnicodeText),
    mysql_engine='InnoDB',
    mysql_charset='utf8',
)

# -----------------------------------------------------------------------------

def upgrade():
    update_setting(u'comments_engine', u'mediacore', u'builtin')

def downgrade():
    update_setting(u'comments_engine', u'builtin', u'mediacore')


# -- helpers ------------------------------------------------------------------

def update_setting(key, current_value, new_value):
    execute(
        settings.update().\
            where(and_(
                settings.c.key == key,
                settings.c.value == current_value)).\
            values({
                'value': inline_literal(new_value),
            })
    )


########NEW FILE########
__FILENAME__ = 010-e1488bb4dd-rename_mediacore_settings
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code contained in this file is licensed under the GPLv3 or
# (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.
"""rename MediaCore settings

added: 2013-11-01 (v0.11dev)

Revision ID: e1488bb4dd
Revises: 47f9265e77e5
Create Date: 2013-11-01 10:28:04.982852
"""

# revision identifiers, used by Alembic.
revision = 'e1488bb4dd'
down_revision = '47f9265e77e5'

from alembic.op import execute, inline_literal
from sqlalchemy import and_
from sqlalchemy.types import Integer, Unicode, UnicodeText
from sqlalchemy.schema import Column, MetaData, Table

# -- table definition ---------------------------------------------------------
metadata = MetaData()
settings = Table('settings', metadata,
    Column('id', Integer, autoincrement=True, primary_key=True),
    Column('key', Unicode(255), nullable=False, unique=True),
    Column('value', UnicodeText),
    mysql_engine='InnoDB',
    mysql_charset='utf8',
)

# -----------------------------------------------------------------------------

def upgrade():
    update_setting(u'general_site_name', u'MediaCore', u'MediaDrop')
    update_settings_key(
        u'appearance_display_mediacore_footer',
        u'appearance_display_mediadrop_footer')
    update_settings_key(
        u'appearance_display_mediacore_credits',
        u'appearance_display_mediadrop_credits')

def downgrade():
    update_setting(u'general_site_name', u'MediaDrop', u'MediaCore')
    update_settings_key(
        u'appearance_display_mediadrop_footer',
        u'appearance_display_mediacore_footer')
    update_settings_key(
        u'appearance_display_mediadrop_credits',
        u'appearance_display_mediacore_credits')


# -- helpers ------------------------------------------------------------------

def update_setting(key, current_value, new_value):
    execute(
        settings.update().\
            where(and_(
                settings.c.key == key,
                settings.c.value == current_value)).\
            values({
                'value': inline_literal(new_value),
            })
    )

def update_settings_key(current_key, new_key):
    execute(
        settings.update().\
            where(and_(
                settings.c.key == current_key,
            )).\
            values({
                'key': inline_literal(new_key),
            })
    )


########NEW FILE########
__FILENAME__ = auth
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code contained in this file is licensed under the GPLv3 or
# (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.
import os
from datetime import datetime

from sqlalchemy import Table, ForeignKey, Column, not_
from sqlalchemy.types import Unicode, Integer, DateTime
from sqlalchemy.orm import mapper, relation, synonym

from mediadrop.model.meta import DBSession, metadata
from mediadrop.lib.compat import any, sha1
from mediadrop.plugin import events

users = Table('users', metadata,
    Column('user_id', Integer, autoincrement=True, primary_key=True),
    Column('user_name', Unicode(16), unique=True, nullable=False),
    Column('email_address', Unicode(255), unique=True, nullable=False),
    Column('display_name', Unicode(255)),
    Column('password', Unicode(80)),
    Column('created', DateTime, default=datetime.now),
    mysql_engine='InnoDB',
    mysql_charset='utf8',
)

users_groups = Table('users_groups', metadata,
    Column('user_id', Integer, ForeignKey('users.user_id',
        onupdate="CASCADE", ondelete="CASCADE")),
    Column('group_id', Integer, ForeignKey('groups.group_id',
        onupdate="CASCADE", ondelete="CASCADE")),
    mysql_engine='InnoDB',
    mysql_charset='utf8',
)

groups = Table('groups', metadata,
    Column('group_id', Integer, autoincrement=True, primary_key=True),
    Column('group_name', Unicode(16), unique=True, nullable=False),
    Column('display_name', Unicode(255)),
    Column('created', DateTime, default=datetime.now),
    mysql_engine='InnoDB',
    mysql_charset='utf8',
)

groups_permissions = Table('groups_permissions', metadata,
    Column('group_id', Integer, ForeignKey('groups.group_id',
        onupdate="CASCADE", ondelete="CASCADE")),
    Column('permission_id', Integer, ForeignKey('permissions.permission_id',
        onupdate="CASCADE", ondelete="CASCADE")),
    mysql_engine='InnoDB',
    mysql_charset='utf8',
)

permissions = Table('permissions', metadata,
    Column('permission_id', Integer, autoincrement=True, primary_key=True),
    Column('permission_name', Unicode(16), unique=True, nullable=False),
    Column('description', Unicode(255)),
    mysql_engine='InnoDB',
    mysql_charset='utf8',
)


class User(object):
    """
    Basic User definition
    """
    query = DBSession.query_property()

    def __repr__(self):
        return '<User: email=%r, display name=%r>' % (
                self.email_address, self.display_name)

    def __unicode__(self):
        return self.display_name or self.user_name

    @property
    def permissions(self):
        perms = set()
        for g in self.groups:
            perms = perms | set(g.permissions)
        return perms

    def has_permission(self, permission_name):
        return any(perm.permission_name == permission_name
                   for perm in self.permissions)

    @classmethod
    def by_email_address(cls, email):
        # TODO: Move this function to User.query
        return DBSession.query(cls).filter(cls.email_address==email).first()

    @classmethod
    def by_user_name(cls, username):
        # TODO: Move this function to User.query
        return DBSession.query(cls).filter(cls.user_name==username).first()

    @classmethod
    def example(cls, **kwargs):
        user = User()
        defaults = dict(
            user_name = u'joe',
            email_address = u'joe@site.example',
            display_name = u'Joe Smith',
            created = datetime.now(),
        )
        defaults.update(kwargs)
        for key, value in defaults.items():
            setattr(user, key, value)
        
        DBSession.add(user)
        DBSession.flush()
        return user

    def _set_password(self, password):
        """Hash password on the fly."""
        if isinstance(password, unicode):
            password_8bit = password.encode('UTF-8')
        else:
            password_8bit = password

        salt = sha1()
        salt.update(os.urandom(60))
        hash_ = sha1()
        hash_.update(password_8bit + salt.hexdigest())
        hashed_password = salt.hexdigest() + hash_.hexdigest()

        # make sure the hashed password is an UTF-8 object at the end of the
        # process because SQLAlchemy _wants_ a unicode object for Unicode columns
        if not isinstance(hashed_password, unicode):
            hashed_password = hashed_password.decode('UTF-8')
        self._password = hashed_password

    def _get_password(self):
        return self._password

    password = property(_get_password, _set_password)

    def validate_password(self, password):
        """Check the password against existing credentials.

        :param password: the password that was provided by the user to
            try and authenticate. This is the clear text version that we will
            need to match against the hashed one in the database.
        :type password: unicode object.
        :return: Whether the password is valid.
        :rtype: bool

        """
        hashed_pass = sha1()
        hashed_pass.update(password + self.password[:40])
        return self.password[40:] == hashed_pass.hexdigest()


class Group(object):
    """
    An ultra-simple group definition.
    """

    query = DBSession.query_property()

    def __init__(self, name=None, display_name=None):
        self.group_name = name
        self.display_name = display_name

    def __repr__(self):
        return '<Group: name=%r>' % self.group_name

    def __unicode__(self):
        return self.group_name
    
    @classmethod
    def custom_groups(cls, *columns):
        query_object = columns or (Group, )
        return DBSession.query(*query_object).\
            filter(
                not_(Group.group_name.in_([u'anonymous', u'authenticated']))
            )

    @classmethod
    def by_name(cls, name):
        return cls.query.filter(cls.group_name == name).first()
    
    @classmethod
    def example(cls, **kwargs):
        defaults = dict(
            name = u'baz_users',
            display_name = u'Baz Users',
        )
        defaults.update(kwargs)
        group = Group(**defaults)
        DBSession.add(group)
        DBSession.flush()
        return group


class Permission(object):
    """
    A relationship that determines what each Group can do
    """
    def __init__(self, name=None, description=None, groups=None):
        self.permission_name = name
        self.description = description
        if groups is not None:
            self.groups = groups

    def __unicode__(self):
        return self.permission_name
    
    def __repr__(self):
        return '<Permission: name=%r>' % self.permission_name
    
    @classmethod
    def example(cls, **kwargs):
        defaults = dict(
            name=u'foo',
            description = u'foo permission',
            groups = None,
        )
        defaults.update(kwargs)
        permission = Permission(**defaults)
        DBSession.add(permission)
        DBSession.flush()
        return permission


mapper(
    User, users,
    extension=events.MapperObserver(events.User),
    properties={
        'id': users.c.user_id,
        'password': synonym('_password', map_column=True),
    },
)

mapper(
    Group, groups,
    properties={
        'users': relation(User, secondary=users_groups, backref='groups'),
    },
)

mapper(
    Permission, permissions,
    properties={
        'groups': relation(Group,
            secondary=groups_permissions,
            backref='permissions',
        ),
    },
)

########NEW FILE########
__FILENAME__ = authors
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code contained in this file is licensed under the GPLv3 or
# (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.

import socket
import struct
from mediadrop.lib.compat import inet_aton


class Author(object):
    """Basic Author Info Wrapper

    Intended to standardize access to author data across various models
    as if we were using a separate 'authors' table. Someday we will need
    to do that, so we might as well write all our controller/view code to
    handle that from the get go.

    """
    def __init__(self, name=None, email=None):
        self.name = name
        self.email = email

    def __composite_values__(self):
        return [self.name, self.email]

    def __eq__(self, other):
        if isinstance(other, Author):
            return self.name == other.name and self.email == other.email
        return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        return '<Author: %r>' % self.name


def _pack_ip(ip_dot_str):
    """Convert an IP address string in dot notation to an 32-bit integer"""
    if not ip_dot_str:
        return None
    return struct.unpack('!L', inet_aton(str(ip_dot_str)))[0]

def _unpack_ip(ip_int):
    """Convert an 32-bit integer IP to a dot-notated string"""
    if not ip_int:
        return None
    return socket.inet_ntoa(struct.pack('!L', long(ip_int)))


class AuthorWithIP(Author):
    """Author Info Wrapper with an extra column for an IP"""
    def __init__(self, name=None, email=None, ip=None):
        super(AuthorWithIP, self).__init__(name, email)
        self.ip = ip

    def __composite_values__(self):
        values = super(AuthorWithIP, self).__composite_values__()
        values.append(_pack_ip(self.ip))
        return values

    def __eq__(self, other):
        if isinstance(other, AuthorWithIP):
            return super(AuthorWithIP, self).__eq__(other) and self.ip == other.ip
        return False

    def __repr__(self):
        return '<Author: %r %s>' % (self.name, self.ip)

    def _get_ip(self):
        return getattr(self, '_ip', None)

    def _set_ip(self, value):
        try:
            self._ip = _unpack_ip(value)
        except:
            self._ip = value

    ip = property(_get_ip, _set_ip)

########NEW FILE########
__FILENAME__ = categories
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code contained in this file is licensed under the GPLv3 or
# (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.

from sqlalchemy import Table, ForeignKey, Column
from sqlalchemy.types import Unicode, Integer
from sqlalchemy.orm import mapper, relation, backref, validates, Query
from sqlalchemy.orm.attributes import set_committed_value

from mediadrop.lib.compat import defaultdict
from mediadrop.model import get_available_slug, SLUG_LENGTH, slugify
from mediadrop.model.meta import DBSession, metadata
from mediadrop.plugin import events


categories = Table('categories', metadata,
    Column('id', Integer, autoincrement=True, primary_key=True),
    Column('name', Unicode(50), nullable=False, index=True),
    Column('slug', Unicode(SLUG_LENGTH), nullable=False, unique=True),
    Column('parent_id', Integer, ForeignKey('categories.id', onupdate='CASCADE', ondelete='CASCADE')),
    mysql_engine='InnoDB',
    mysql_charset='utf8'
)

class CategoryNestingException(Exception):
    pass

def traverse(cats, depth=0, ancestors=None):
    """Iterate through a depth-first traversal of the given categories.

    Yields a 2-tuple of the :class:`Category` instance and it's
    relative depth in the tree.

    :param cats: A list of :class:`Category` instances.
    :param depth: Distance from the root
    :param ancestors: Visited ancestors, tracked to prevent infinite
        loops on circular nesting.
    :type ancestors: dict

    """
    if ancestors is None:
        ancestors = {}
    for cat in cats:
        if cat.id in ancestors:
            raise CategoryNestingException, 'Category tree contains ' \
                'invalid nesting: %s is a parent to one of its ' \
                'ancestors %s.' % (cat, ancestors)
        child_anc = ancestors.copy()
        child_anc[cat.id] = True

        yield cat, depth
        for subcat, subdepth in traverse(cat.children, depth + 1, child_anc):
            yield subcat, subdepth

def populated_tree(cats):
    """Return the root categories with children populated to any depth.

    Adjacency lists are notoriously inefficient for fetching deeply
    nested trees, and since our dataset will always be reasonably
    small, this method should greatly improve efficiency. Only one
    query is necessary to fetch a tree of any depth. This isn't
    always the solution, but for some situations, it is worthwhile.

    For example, printing the entire tree can be done with one query::

        query = Category.query.options(undefer('media_count'))
        for cat, depth in query.populated_tree().traverse():
            print "    " * depth, cat.name, '(%d)' % cat.media_count

    Without this method, especially with the media_count undeferred,
    this would require a lot of extra queries for nested categories.

    NOTE: If the tree contains circular nesting, the circular portion
          of the tree will be silently omitted from the results.

    """
    children = defaultdict(CategoryList)
    for cat in cats:
        children[cat.parent_id].append(cat)
    for cat in cats:
        set_committed_value(cat, 'children', children[cat.id])
    return children[None]

class CategoryQuery(Query):
    traverse = traverse
    """Iterate over all categories and nested children in depth-first order."""

    def all(self):
        return CategoryList(self)

    def roots(self):
        """Filter for just root, parentless categories."""
        return self.filter(Category.parent_id == None)

    def populated_tree(self):
        return populated_tree(self.all())


class CategoryList(list):
    traverse = traverse
    """Iterate over all categories and nested children in depth-first order."""

    def __unicode__(self):
        return ', '.join(cat.name for cat in self.itervalues())

    def populated_tree(self):
        return populated_tree(self)

class Category(object):
    """
    Category Mapped Class
    """
    query = DBSession.query_property(CategoryQuery)

    def __init__(self, name=None, slug=None):
        self.name = name or None
        self.slug = slug or name or None

    def __repr__(self):
        return '<Category: %r>' % self.name

    def __unicode__(self):
        return self.name

    @classmethod
    def example(cls, **kwargs):
        category = Category()
        defaults = dict(
            name=u'Foo',
            parent_id=0
        )
        defaults.update(kwargs)
        defaults.setdefault('slug', get_available_slug(Category, defaults['name']))

        for key, value in defaults.items():
            assert hasattr(category, key)
            setattr(category, key, value)

        DBSession.add(category)
        DBSession.flush()
        return category

    @validates('slug')
    def validate_slug(self, key, slug):
        return slugify(slug)

    def traverse(self):
        """Iterate over all nested categories in depth-first order."""
        return traverse(self.children)

    def descendants(self):
        """Return a list of descendants in depth-first order."""
        return [desc for desc, depth in self.traverse()]

    def ancestors(self):
        """Return a list of ancestors, starting with the root node.

        This method is optimized for when all categories have already
        been fetched in the current DBSession::

            >>> Category.query.all()    # run one query
            >>> row = Category.query.get(50)   # doesn't use a query
            >>> row.parent    # the DBSession recognized the primary key
            <Category: parent>
            >>> print row.ancestors()
            [...,
             <Category: great-grand-parent>,
             <Category: grand-parent>,
             <Category: parent>]

        """
        ancestors = CategoryList()
        anc = self.parent
        while anc:
            if anc is self:
                raise CategoryNestingException, 'Category %s is defined as a ' \
                    'parent of one of its ancestors.' % anc
            ancestors.insert(0, anc)
            anc = anc.parent
        return ancestors

    def depth(self):
        """Return this category's distance from the root of the tree."""
        return len(self.ancestors())


mapper(Category, categories,
    order_by=categories.c.name,
    extension=events.MapperObserver(events.Category),
    properties={
        'children': relation(Category,
            backref=backref('parent', remote_side=[categories.c.id]),
            order_by=categories.c.name.asc(),
            collection_class=CategoryList,
            join_depth=2),
    })

########NEW FILE########
__FILENAME__ = comments
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code contained in this file is licensed under the GPLv3 or
# (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.

"""
Comment Model

Comments come with two status flags:

    * reviewed
    * publishable

"""
from datetime import datetime
from sqlalchemy import Table, ForeignKey, Column, sql
from sqlalchemy.types import BigInteger, Boolean, DateTime, Integer, Unicode, UnicodeText
from sqlalchemy.orm import mapper, relation, backref, synonym, composite, column_property, validates, interfaces, Query

from mediadrop.model import AuthorWithIP
from mediadrop.model.meta import DBSession, metadata
from mediadrop.plugin import events


comments = Table('comments', metadata,
    Column('id', Integer, autoincrement=True, primary_key=True),
    Column('media_id', Integer, ForeignKey('media.id', onupdate='CASCADE', ondelete='CASCADE')),
    Column('subject', Unicode(100)),
    Column('created_on', DateTime, default=datetime.now, nullable=False),
    Column('modified_on', DateTime, default=datetime.now, onupdate=datetime.now, nullable=False),
    Column('reviewed', Boolean, default=False, nullable=False),
    Column('publishable', Boolean, default=False, nullable=False),
    Column('author_name', Unicode(50), nullable=False),
    Column('author_email', Unicode(255)),
    Column('author_ip', BigInteger, nullable=False),
    Column('body', UnicodeText, nullable=False),
    mysql_engine='InnoDB',
    mysql_charset='utf8',
)

class CommentQuery(Query):
    def published(self, flag=True):
        return self.filter(Comment.publishable == flag)

    def reviewed(self, flag=True):
        return self.filter(Comment.reviewed == flag)

    def trash(self, flag=True):
        filter = sql.and_(Comment.reviewed == True,
                          Comment.publishable == False)
        if flag:
            return self.filter(filter)
        else:
            return self.filter(sql.not_(filter))

    def search(self, q):
        q = '%' + q + '%'
        return self.filter(sql.or_(
            Comment.subject.like(q),
            Comment.body.like(q),
        ))


class Comment(object):
    """Comment Model

    .. attribute:: type

        The relation name to use when looking up the parent object of this Comment.
        This is the name of the backref property which can be used to find the
        object that this Comment belongs to. Our convention is to have a controller
        by this name, with a 'view' action which accepts a slug, so we can
        auto-generate links to any comment's parent.

    .. attribute:: author

        An instance of :class:`mediadrop.model.author.AuthorWithIP`.

    """

    query = DBSession.query_property(CommentQuery)

    def __repr__(self):
        return '<Comment: %r subject=%r>' % (self.id, self.subject)

    def __unicode__(self):
        return self.subject

    @property
    def type(self):
        if self.media_id:
            return 'media'
        return None

    def _get_parent(self):
        return self.media or None
    def _set_parent(self, parent):
        self.media = parent
    parent = property(_get_parent, _set_parent, None, """
        The object this Comment belongs to, provided for convenience mostly.
        If the parent has not been eagerloaded, a query is executed automatically.
    """)


mapper(Comment, comments, order_by=comments.c.created_on, extension=events.MapperObserver(events.Comment), properties={
    'author': composite(AuthorWithIP,
        comments.c.author_name,
        comments.c.author_email,
        comments.c.author_ip),
})

########NEW FILE########
__FILENAME__ = media
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code contained in this file is licensed under the GPLv3 or
# (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.

"""
Media Models

SQLAlchemy ORM definitions for:

* :class:`Media`: metadata for a collection of one or more files.
* :class:`MediaFile`: a single audio or video file.

Additionally, :class:`Media` may be considered at podcast episode if it
belongs to a :class:`mediadrop.model.podcasts.Podcast`.

.. moduleauthor:: Nathan Wright <nathan@mediacore.com>

"""

from datetime import datetime

from sqlalchemy import Table, ForeignKey, Column, event, sql
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.orm import (attributes, backref, class_mapper, column_property,
    composite, dynamic_loader, mapper, Query, relation, validates)
from sqlalchemy.orm.collections import attribute_mapped_collection
from sqlalchemy.schema import DDL
from sqlalchemy.types import Boolean, DateTime, Integer, Unicode, UnicodeText

from mediadrop.lib.auth import Resource
from mediadrop.lib.compat import any
from mediadrop.lib.filetypes import AUDIO, AUDIO_DESC, VIDEO, guess_mimetype
from mediadrop.lib.players import pick_any_media_file, pick_podcast_media_file
from mediadrop.lib.util import calculate_popularity
from mediadrop.lib.xhtml import line_break_xhtml, strip_xhtml
from mediadrop.model import (get_available_slug, SLUG_LENGTH, 
    _mtm_count_property, _properties_dict_from_labels, MatchAgainstClause)
from mediadrop.model.meta import DBSession, metadata
from mediadrop.model.authors import Author
from mediadrop.model.categories import Category, CategoryList
from mediadrop.model.comments import Comment, CommentQuery, comments
from mediadrop.model.tags import Tag, TagList, extract_tags, fetch_and_create_tags
from mediadrop.plugin import events


media = Table('media', metadata,
    Column('id', Integer, autoincrement=True, primary_key=True, doc=\
        """The primary key ID."""),

    Column('type', Unicode(8), doc=\
        """Indicates whether the media is to be considered audio or video.

        If this object has no files, the type is None.
        See :meth:`Media.update_type` for details on how this is determined."""),

    Column('slug', Unicode(SLUG_LENGTH), unique=True, nullable=False, doc=\
        """A unique URL-friendly permalink string for looking up this object.

        Be sure to call :func:`mediadrop.model.get_available_slug` to ensure
        the slug is unique."""),

    Column('podcast_id', Integer, ForeignKey('podcasts.id', onupdate='CASCADE', ondelete='SET NULL'), doc=\
        """The primary key of a podcast to publish this media under."""),

    Column('reviewed', Boolean, default=False, nullable=False, doc=\
        """A flag to indicate whether this file has passed review by an admin."""),

    Column('encoded', Boolean, default=False, nullable=False, doc=\
        """A flag to indicate whether this file is encoded in a web-ready state."""),

    Column('publishable', Boolean, default=False, nullable=False, doc=\
        """A flag to indicate if this media should be published in between its
        publish_on and publish_until dates. If this is false, this is
        considered to be in draft state and will not appear on the site."""),

    Column('created_on', DateTime, default=datetime.now, nullable=False, doc=\
        """The date and time this player was first created."""),

    Column('modified_on', DateTime, default=datetime.now, onupdate=datetime.now, nullable=False, doc=\
        """The date and time this player was last modified."""),

    Column('publish_on', DateTime, doc=\
        """A datetime range during which this object should be published.
        The range may be open ended by leaving ``publish_until`` empty."""),

    Column('publish_until', DateTime, doc=\
        """A datetime range during which this object should be published.
        The range may be open ended by leaving ``publish_until`` empty."""),

    Column('title', Unicode(255), nullable=False, doc=\
        """Display title."""),

    Column('subtitle', Unicode(255), doc=\
        """An optional subtitle intended mostly for podcast episodes.
        If none is provided, the title is concatenated and used in its place."""),

    Column('description', UnicodeText, doc=\
        """A public-facing XHTML description. Should be a paragraph or more."""),

    Column('description_plain', UnicodeText, doc=\
        """A public-facing plaintext description. Should be a paragraph or more."""),

    Column('notes', UnicodeText, doc=\
        """Notes for administrative use -- never displayed publicly."""),

    Column('duration', Integer, default=0, nullable=False, doc=\
        """Play time in seconds."""),

    Column('views', Integer, default=0, nullable=False, doc=\
        """The number of times the public media page has been viewed."""),

    Column('likes', Integer, default=0, nullable=False, doc=\
        """The number of users who clicked 'i like this'."""),

    Column('dislikes', Integer, default=0, nullable=False, doc=\
        """The number of users who clicked 'i DONT like this'."""),

    Column('popularity_points', Integer, default=0, nullable=False, doc=\
        """An integer score of how 'hot' (likes - dislikes) this media is.

        Newer items with some likes are favoured over older items with
        more likes. In other words, ordering on this column will always
        bring the newest most liked items to the top. `More info
        <http://amix.dk/blog/post/19588>`_."""),

    Column('popularity_likes', Integer, default=0, nullable=False, doc=\
        """An integer score of how 'hot' liking this media is.

        Newer items with some likes are favoured over older items with
        more likes. In other words, ordering on this column will always
        bring the newest most liked items to the top. `More info
        <http://amix.dk/blog/post/19588>`_."""),

    Column('popularity_dislikes', Integer, default=0, nullable=False, doc=\
        """An integer score of how 'hot' disliking this media is.

        Newer items with some likes are favoured over older items with
        more likes. In other words, ordering on this column will always
        bring the newest most liked items to the top. `More info
        <http://amix.dk/blog/post/19588>`_."""),

    Column('author_name', Unicode(50), nullable=False),
    Column('author_email', Unicode(255), nullable=False),

    mysql_engine='InnoDB',
    mysql_charset='utf8',
)

media_meta = Table('media_meta', metadata,
    Column('id', Integer, autoincrement=True, primary_key=True),
    Column('media_id', Integer, ForeignKey('media.id', onupdate='CASCADE', ondelete='CASCADE'), nullable=False),
    Column('key', Unicode(64), nullable=False),
    Column('value', UnicodeText, default=None),

    mysql_engine='InnoDB',
    mysql_charset='utf8',
)

media_files = Table('media_files', metadata,
    Column('id', Integer, autoincrement=True, primary_key=True),
    Column('media_id', Integer, ForeignKey('media.id', onupdate='CASCADE', ondelete='CASCADE'), nullable=False),
    Column('storage_id', Integer, ForeignKey('storage.id', onupdate='CASCADE', ondelete='CASCADE'), nullable=False),

    Column('type', Unicode(16), nullable=False),
    Column('container', Unicode(10)),
    Column('display_name', Unicode(255), nullable=False),
    Column('unique_id', Unicode(255)),
    Column('size', Integer),

    Column('created_on', DateTime, default=datetime.now, nullable=False),
    Column('modified_on', DateTime, default=datetime.now, onupdate=datetime.now, nullable=False),

    Column('bitrate', Integer),
    Column('width', Integer),
    Column('height', Integer),

    mysql_engine='InnoDB',
    mysql_charset='utf8',
)

media_files_meta = Table('media_files_meta', metadata,
    Column('id', Integer, autoincrement=True, primary_key=True),
    Column('media_files_id', Integer, ForeignKey('media_files.id', onupdate='CASCADE', ondelete='CASCADE'), nullable=False),
    Column('key', Unicode(64), nullable=False),
    Column('value', UnicodeText, default=None),

    mysql_engine='InnoDB',
    mysql_charset='utf8',
)

media_tags = Table('media_tags', metadata,
    Column('media_id', Integer, ForeignKey('media.id', onupdate='CASCADE', ondelete='CASCADE'),
        primary_key=True),
    Column('tag_id', Integer, ForeignKey('tags.id', onupdate='CASCADE', ondelete='CASCADE'),
        primary_key=True),
    mysql_engine='InnoDB',
    mysql_charset='utf8',
)

media_categories = Table('media_categories', metadata,
    Column('media_id', Integer, ForeignKey('media.id', onupdate='CASCADE', ondelete='CASCADE'),
        primary_key=True),
    Column('category_id', Integer, ForeignKey('categories.id', onupdate='CASCADE', ondelete='CASCADE'),
        primary_key=True),
    mysql_engine='InnoDB',
    mysql_charset='utf8',
)

media_fulltext = Table('media_fulltext', metadata,
    Column('media_id', Integer, ForeignKey('media.id'), primary_key=True),
    Column('title', Unicode(255), nullable=False),
    Column('subtitle', Unicode(255)),
    Column('description_plain', UnicodeText),
    Column('notes', UnicodeText),
    Column('author_name', Unicode(50), nullable=False),
    Column('tags', UnicodeText),
    Column('categories', UnicodeText),
    mysql_engine='MyISAM',
    mysql_charset='utf8',
)

# Columns grouped by their FULLTEXT index
_fulltext_indexes = {
    'admin': (
        media_fulltext.c.title, media_fulltext.c.subtitle,
        media_fulltext.c.tags, media_fulltext.c.categories,
        media_fulltext.c.description_plain, media_fulltext.c.notes,
    ),
    'public': (
        media_fulltext.c.title, media_fulltext.c.subtitle,
        media_fulltext.c.tags, media_fulltext.c.categories,
        media_fulltext.c.description_plain,
    ),
}

def _setup_mysql_fulltext_indexes():
    for name, cols in _fulltext_indexes.iteritems():
        sql = (
            'ALTER TABLE %%(table)s '
            'ADD FULLTEXT INDEX media_fulltext_%(name)s (%(cols)s)'
        ) % {
            'name': name,
            'cols': ', '.join(col.name for col in cols)
        }
        event.listen(
            media_fulltext,
            u'after_create',
            DDL(sql).execute_if(dialect=u'mysql')
        )
_setup_mysql_fulltext_indexes()

class MediaQuery(Query):
    def reviewed(self, flag=True):
        return self.filter(Media.reviewed == flag)

    def encoded(self, flag=True):
        return self.filter(Media.encoded == flag)

    def drafts(self, flag=True):
        drafts = sql.and_(
            Media.publishable == False,
            Media.reviewed == True,
            Media.encoded == True,
        )
        if flag:
            return self.filter(drafts)
        else:
            return self.filter(sql.not_(drafts))

    def published(self, flag=True):
        published = sql.and_(
            Media.reviewed == True,
            Media.encoded == True,
            Media.publishable == True,
            Media.publish_on <= datetime.now(),
            sql.or_(Media.publish_until == None,
                    Media.publish_until >= datetime.now()),
        )
        if flag:
            return self.filter(published)
        else:
            return self.filter(sql.not_(published))

    def order_by_status(self):
        return self.order_by(Media.reviewed.asc(),
                             Media.encoded.asc(),
                             Media.publishable.asc())

    def order_by_popularity(self):
        return self.order_by(Media.popularity_points.desc())

    def search(self, search, bool=False, order_by=True):
        search_cols = _fulltext_indexes['public']
        return self._search(search_cols, search, bool, order_by)

    def admin_search(self, search, bool=False, order_by=True):
        search_cols = _fulltext_indexes['admin']
        return self._search(search_cols, search, bool, order_by)

    def _search(self, search_cols, search, bool=False, order_by=True):
        # XXX: If full text searching is not enabled, we use a very
        #      rudimentary fallback.
        if not self._fulltext_enabled():
            return self.filter(sql.or_(Media.title.ilike("%%%s%%" % search),
                                       Media.description_plain.ilike("%%%s%%" % search)))

        filter = MatchAgainstClause(search_cols, search, bool)
        query = self.join(MediaFullText).filter(filter)
        if order_by:
            # MySQL automatically orders natural lang searches by relevance,
            # so override any existing ordering
            query = query.order_by(None)
            if bool:
                # To mimic the same behaviour in boolean mode, we must do an
                # extra natural language search on our boolean-filtered results
                relevance = MatchAgainstClause(search_cols, search, bool=False)
                query = query.order_by(relevance)
        return query

    def _fulltext_enabled(self):
        connection = self.session.connection()
        if connection.dialect.name == 'mysql':
            # use a fun trick to see if the media_fulltext table is being used
            # thanks to this guy: http://data.agaric.com/node/2241#comment-544
            select = sql.select('1').select_from(media_fulltext).limit(1)
            result = connection.execute(select)
            if result.scalar() is not None:
                return True
        return False

    def in_category(self, cat):
        """Filter results to Media in the given category"""
        return self.in_categories([cat])

    def in_categories(self, cats):
        """Filter results to Media in at least one of the given categories"""
        if len(cats) == 0:
            # SQLAlchemy complains about an empty IN-predicate
            return self.filter(media_categories.c.media_id == -1)
        all_cats = cats[:]
        for cat in cats:
            all_cats.extend(cat.descendants())
        all_ids = [c.id for c in all_cats]
        return self.filter(sql.exists(sql.select(
            [media_categories.c.media_id],
            sql.and_(media_categories.c.media_id == Media.id,
                     media_categories.c.category_id.in_(all_ids))
        )))

    def exclude(self, *args):
        """Exclude the given Media rows or IDs from the results.

        Accepts any number of arguments of Media instances, ids,
        lists of both, or None.
        """
        def _flatten(*args):
            ids = []
            for arg in args:
                if isinstance(arg, list):
                    ids.extend(_flatten(*arg))
                elif isinstance(arg, Media):
                    ids.append(int(arg.id))
                elif arg is not None:
                    ids.append(int(arg))
            return ids
        ids = _flatten(*args)
        if ids:
            return self.filter(sql.not_(Media.id.in_(ids)))
        else:
            return self

    def related(self, media):
        query = self.published().filter(Media.id != media.id)

        # XXX: If full text searching is not enabled, we simply return media
        #      in the same categories.
        if not self._fulltext_enabled():
            return query.in_categories(media.categories)

        search_terms = '%s %s %s' % (
            media.title,
            media.fulltext and media.fulltext.tags or '',
            media.fulltext and media.fulltext.categories or '',
        )
        return query.search(search_terms, bool=True)

class Meta(object):
    """
    Metadata related to a media object

    .. attribute:: id

    .. attribute:: key

        A lookup key

    .. attribute:: value

        The metadata value

    """
    def __init__(self, key, value):
        self.key = key
        self.value = value

class MediaMeta(Meta):
    pass

class MediaFilesMeta(Meta):
    pass

class Media(object):
    """
    Media metadata and a collection of related files.

    """
    meta = association_proxy('_meta', 'value', creator=MediaMeta)

    query = DBSession.query_property(MediaQuery)

    # TODO: replace '_thumb_dir' with something more generic, like 'name',
    #       so that its other uses throughout the code make more sense.
    _thumb_dir = 'media'

    def __init__(self):
        if self.author is None:
            self.author = Author()

    def __repr__(self):
        return '<Media: %r>' % self.slug

    @classmethod
    def example(cls, **kwargs):
        media = Media()
        defaults = dict(
            title=u'Foo Media',
            author=Author(u'Joe', u'joe@site.example'),
            
            type = None,
        )
        defaults.update(kwargs)
        defaults.setdefault('slug', get_available_slug(Media, defaults['title']))
        for key, value in defaults.items():
            assert hasattr(media, key)
            setattr(media, key, value)
        DBSession.add(media)
        DBSession.flush()
        return media

    def set_tags(self, tags):
        """Set the tags relations of this media, creating them as needed.

        :param tags: A list or comma separated string of tags to use.
        """
        if isinstance(tags, basestring):
            tags = extract_tags(tags)
        if isinstance(tags, list) and tags:
            tags = fetch_and_create_tags(tags)
        self.tags = tags or []

    def set_categories(self, cats):
        """Set the related categories of this media.

        :param cats: A list of category IDs to set.
        """
        if cats:
            cats = Category.query.filter(Category.id.in_(cats)).all()
        self.categories = cats or []

    def update_status(self):
        """Ensure the type (audio/video) and encoded flag are properly set.

        Call this after modifying any files belonging to this item.

        """
        was_encoded = self.encoded
        self.type = self._update_type()
        self.encoded = self._update_encoding()
        if self.encoded and not was_encoded:
            events.Media.encoding_done(self)

    def _update_type(self):
        """Update the type of this Media object.

        If there's a video file, mark this as a video type, else fallback
        to audio, if possible, or unknown (None)
        """
        if any(file.type == VIDEO for file in self.files):
            return VIDEO
        elif any(file.type == AUDIO for file in self.files):
            return AUDIO
        return None

    def _update_encoding(self):
        # Test to see if we can find a workable file/player combination
        # for the most common podcasting app w/ the POOREST format support
        if self.podcast_id and not pick_podcast_media_file(self):
            return False
        # Test to see if we can find a workable file/player combination
        # for the browser w/ the BEST format support
        if not pick_any_media_file(self):
            return False
        return True

    @property
    def is_published(self):
        if self.id is None:
            return False
        return self.publishable and self.reviewed and self.encoded\
           and (self.publish_on is not None and self.publish_on <= datetime.now())\
           and (self.publish_until is None or self.publish_until >= datetime.now())

    @property
    def resource(self):
        return Resource('media', self.id, media=self)

    def increment_views(self):
        """Increment the number of views in the database.

        We avoid concurrency issues by incrementing JUST the views and
        not allowing modified_on to be updated automatically.

        """
        if self.id is None:
            self.views += 1
            return self.views

        DBSession.execute(media.update()\
            .values(views=media.c.views + 1)\
            .where(media.c.id == self.id))

        # Increment the views by one for the rest of the request,
        # but don't allow the ORM to increment the views too.
        attributes.set_committed_value(self, 'views', self.views + 1)
        return self.views

    def increment_likes(self):
        self.likes += 1
        self.update_popularity()
        return self.likes

    def increment_dislikes(self):
        self.dislikes += 1
        self.update_popularity()
        return self.dislikes

    def update_popularity(self):
        if self.is_published:
            self.popularity_points = calculate_popularity(
                self.publish_on,
                self.likes - self.dislikes,
            )
            self.popularity_likes = calculate_popularity(
                self.publish_on,
                self.likes,
            )
            self.popularity_dislikes = calculate_popularity(
                self.publish_on,
                self.dislikes,
            )
        else:
            self.popularity_points = 0
            self.popularity_likes = 0
            self.popularity_dislikes = 0

    @validates('description')
    def _validate_description(self, key, value):
        self.description_plain = line_break_xhtml(
            line_break_xhtml(value)
        )
        return value

    @validates('description_plain')
    def _validate_description_plain(self, key, value):
        return strip_xhtml(value, True)

    def get_uris(self):
        uris = []
        for file in self.files:
            uris.extend(file.get_uris())
        return uris

class MediaFileQuery(Query):
    pass

class MediaFile(object):
    """
    Audio or Video File

    """
    meta = association_proxy('_meta', 'value', creator=MediaFilesMeta)
    query = DBSession.query_property(MediaFileQuery)

    def __repr__(self):
        return '<MediaFile: %r %r unique_id=%r>' \
            % (self.type, self.storage.display_name, self.unique_id)

    @property
    def mimetype(self):
        """The best-guess mimetype based on this file's container format.

        Defaults to 'application/octet-stream'.
        """
        type = self.type
        if type == AUDIO_DESC:
            type = AUDIO
        return guess_mimetype(self.container, type)

    def get_uris(self):
        """Return a list all possible playback URIs for this file.

        :rtype: list
        :returns: :class:`mediadrop.lib.storage.StorageURI` instances.

        """
        return self.storage.get_uris(self)

class MediaFullText(object):
    query = DBSession.query_property()

mapper(MediaFullText, media_fulltext)
mapper(MediaMeta, media_meta)
mapper(MediaFilesMeta, media_files_meta)

_media_files_mapper = mapper(
    MediaFile, media_files,
    extension=events.MapperObserver(events.MediaFile),
    properties={
        '_meta': relation(
            MediaFilesMeta,
            collection_class=attribute_mapped_collection('key'),
            passive_deletes=True,
        ),
    },
)

_media_mapper = mapper(
    Media, media,
    order_by=media.c.title,
    extension=events.MapperObserver(events.Media),
    properties={
        'fulltext': relation(
            MediaFullText,
            uselist=False,
            passive_deletes=True,
        ),
        'author': composite(
            Author,
            media.c.author_name,
            media.c.author_email,
            doc="""An instance of :class:`mediadrop.model.authors.Author`.
                   Although not actually a relation, it is implemented as if it were.
                   This was decision was made to make it easier to integrate with
                   :class:`mediadrop.model.auth.User` down the road."""
        ),
        'files': relation(
            MediaFile,
            backref='media',
            order_by=media_files.c.type.asc(),
            passive_deletes=True,
            doc="""A list of :class:`MediaFile` instances."""
        ),
        'tags': relation(
            Tag,
            secondary=media_tags,
            backref=backref('media', lazy='dynamic', query_class=MediaQuery),
            collection_class=TagList,
            passive_deletes=True,
            doc="""A list of :class:`mediadrop.model.tags.Tag`."""
        ),
        'categories': relation(
            Category,
            secondary=media_categories,
            backref=backref('media', lazy='dynamic', query_class=MediaQuery),
            collection_class=CategoryList,
            passive_deletes=True,
            doc="""A list of :class:`mediadrop.model.categories.Category`."""
        ),
        '_meta': relation(
            MediaMeta,
            collection_class=attribute_mapped_collection('key'),
            passive_deletes=True,
        ),
        'comments': dynamic_loader(
            Comment,
            backref='media',
            query_class=CommentQuery,
            passive_deletes=True,
            doc="""A query pre-filtered for associated comments.
                   Returns :class:`mediadrop.model.comments.CommentQuery`."""
        ),
        'comment_count': column_property(
            sql.select(
                [sql.func.count(comments.c.id)],
                media.c.id == comments.c.media_id,
            ).label('comment_count'),
            deferred=True,
        ),
        'comment_count_published': column_property(
            sql.select(
                [sql.func.count(comments.c.id)],
                sql.and_(
                    comments.c.media_id == media.c.id,
                    comments.c.publishable == True,
                )
            ).label('comment_count_published'),
            deferred=True,
        ),
})

# Add properties for counting how many media items have a given Tag
_tags_mapper = class_mapper(Tag, compile=False)
_tags_mapper.add_properties(_properties_dict_from_labels(
    _mtm_count_property('media_count', media_tags),
    _mtm_count_property('media_count_published', media_tags, [
        media.c.reviewed == True,
        media.c.encoded == True,
        media.c.publishable == True,
        media.c.publish_on <= sql.func.current_timestamp(),
        sql.or_(
            media.c.publish_until == None,
            media.c.publish_until >= sql.func.current_timestamp(),
        ),
    ]),
))

# Add properties for counting how many media items have a given Category
_categories_mapper = class_mapper(Category, compile=False)
_categories_mapper.add_properties(_properties_dict_from_labels(
    _mtm_count_property('media_count', media_categories),
    _mtm_count_property('media_count_published', media_categories, [
        media.c.reviewed == True,
        media.c.encoded == True,
        media.c.publishable == True,
        media.c.publish_on <= sql.func.current_timestamp(),
        sql.or_(
            media.c.publish_until == None,
            media.c.publish_until >= sql.func.current_timestamp(),
        ),
    ]),
))

########NEW FILE########
__FILENAME__ = meta
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code contained in this file is licensed under the GPLv3 or
# (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.

"""SQLAlchemy Metadata and Session object"""
from sqlalchemy import MetaData
from sqlalchemy.orm import scoped_session, sessionmaker

__all__ = [
    'DBSession',
    'metadata',
]

# SQLAlchemy session manager. Updated by model.init_model()
# DBSession() returns the session object appropriate for the current request.
maker = sessionmaker()
DBSession = scoped_session(maker)

metadata = MetaData()

########NEW FILE########
__FILENAME__ = players
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code contained in this file is licensed under the GPLv3 or
# (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.
"""
Player Preferences

The :attr:`players` table defined here is used to persist the user's
preferences for, and the relative priority of, the different players
that MediaDrop should try to play media with.

"""

import logging
from datetime import datetime

from sqlalchemy import Column, sql, Table
from sqlalchemy.orm import mapper
from sqlalchemy.types import Boolean, DateTime, Integer, Unicode

from mediadrop.lib.decorators import memoize
from mediadrop.lib.i18n import _
from mediadrop.lib.players import AbstractPlayer
from mediadrop.model.meta import DBSession, metadata
from mediadrop.model.util import JSONType

log = logging.getLogger(__name__)

players = Table('players', metadata,
    Column('id', Integer, primary_key=True, autoincrement=True, doc=\
        """The primary key ID."""),

    Column('name', Unicode(30), nullable=False, doc=\
        """The internal name used to identify this player.

        Maps to :attr:`mediadrop.lib.players.AbstractPlayer.name`.
        """),

    Column('enabled', Boolean, nullable=False, default=True, doc=\
        """A simple flag to disable the use of this player."""),

    Column('priority', Integer, nullable=False, default=0, doc=\
        """Order of preference in ascending order (0 is first)."""),

    Column('created_on', DateTime, nullable=False, default=datetime.now, doc=\
        """The date and time this player was first created."""),

    Column('modified_on', DateTime, nullable=False, default=datetime.now,
                                                    onupdate=datetime.now, doc=\
        """The date and time this player was last modified."""),

    Column('data', JSONType, nullable=False, default=dict, doc=\
        """The user preferences for this player (if any).

        This dictionary is passed as `data` kwarg when
        :func:`mediadrop.lib.players.media_player` instantiates the
        :class:`mediadrop.lib.players.AbstractPlayer` class associated
        with this row.

        """),

    mysql_engine='InnoDB',
    mysql_charset='utf8',
)

class PlayerPrefs(object):
    """
    Player Preferences

    A wrapper containing the administrator's preferences for an individual
    player. Each row maps to a :class:`mediadrop.lib.players.AbstractPlayer`
    implementation.

    """
    query = DBSession.query_property()

    @property
    def player_cls(self):
        """Return the class object that is mapped to this row."""
        for player_cls in reversed(tuple(AbstractPlayer)):
            if self.name == player_cls.name:
                return player_cls
        return None

    @property
    def display_name(self):
        """Return the user-friendly display name for this player class.

        This string is expected to be i18n-ready. Simply wrap it in a
        call to :func:`mediadrop.lib.i18n._`.

        :rtype: unicode
        :returns: A i18n-ready string name.
        """
        if self.player_cls is None:
            # do not break the admin interface (admin/settings/players) if the
            # player is still in the database but the actual player class is not
            # available anymore (this can happen especially for players provided
            # by external plugins.
            return _(u'%s (broken)') % self.name
        return self.player_cls.display_name

    @property
    @memoize
    def settings_form(self):
        cls = self.player_cls
        if cls and cls.settings_form_class:
            return cls.settings_form_class()
        return None

mapper(
    PlayerPrefs, players,
    order_by=(
        players.c.enabled.desc(),
        players.c.priority,
        players.c.id.desc(),
    ),
)

def fetch_enabled_players():
    """Return player classes and their data dicts in ascending priority.

    Warnings are logged any time a row is found that does not match up to
    one of the classes that are currently registered. A warning will also
    be raised if there are no players configured/enabled.

    :rtype: list of tuples
    :returns: :class:`~mediadrop.lib.players.AbstractPlayer` subclasses
        and the configured data associated with them.

    """
    player_classes = dict((p.name, p) for p in AbstractPlayer)
    query = sql.select((players.c.name, players.c.data))\
        .where(players.c.enabled == True)\
        .order_by(players.c.priority.asc(), players.c.id.desc())
    query_data = DBSession.execute(query).fetchall()
    while query_data:
        try:
            return [(player_classes[name], data) for name, data in query_data]
        except KeyError:
            log.warn('Player name %r exists in the database but has not '
                     'been registered.' % name)
            query_data.remove((name, data))
    log.warn('No registered players are configured in your database.')
    return []

def cleanup_players_table(enabled=False):
    """
    Ensure that all available players are added to the database
    and that players are prioritized in incrementally increasing order.

    :param enabled: Should the default players be enabled upon creation?
    :type enabled: bool
    """
    from mediadrop.lib.players import (BlipTVFlashPlayer,
        DailyMotionEmbedPlayer, GoogleVideoFlashPlayer, JWPlayer,
        VimeoUniversalEmbedPlayer, YoutubePlayer)

    # When adding players, prefer them in the following order:
    default_players = [
        JWPlayer,
        YoutubePlayer,
        VimeoUniversalEmbedPlayer,
        GoogleVideoFlashPlayer,
        BlipTVFlashPlayer,
        DailyMotionEmbedPlayer,
    ]
    unordered_players = [p for p in AbstractPlayer if p not in default_players]
    all_players = default_players + unordered_players

    # fetch the players that are already in the database
    s = players.select().order_by('priority')
    existing_players_query = DBSession.execute(s)
    existing_player_rows = [p for p in existing_players_query]
    existing_player_names = [p['name'] for p in existing_player_rows]

    # Ensure all priorities are monotonically increasing from 1..n
    priority = 0
    for player_row in existing_player_rows:
        priority += 1
        if player_row['priority'] != priority:
            u = players.update()\
                       .where(players.c.id == player_row['id'])\
                       .values(priority=priority)
            DBSession.execute(u)

    # Ensure that all available players are in the database
    for player_cls in all_players:
        if player_cls.name not in existing_player_names:
            enable_player = enabled and player_cls in default_players
            priority += 1
            DBSession.execute(players.insert().values(
                name=player_cls.name,
                enabled=enable_player,
                data=player_cls.default_data,
                priority=priority,
            ))

########NEW FILE########
__FILENAME__ = podcasts
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code contained in this file is licensed under the GPLv3 or
# (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.

"""
Podcast Models

SQLAlchemy ORM definitions for:

* :class:`Podcast`

.. moduleauthor:: Nathan Wright <nathan@mediacore.com>

"""
from datetime import datetime
from sqlalchemy import Table, ForeignKey, Column, sql
from sqlalchemy.types import Unicode, UnicodeText, Integer, DateTime, Boolean, Float
from sqlalchemy.orm import mapper, relation, backref, synonym, composite, validates, dynamic_loader, column_property
from pylons import request

from mediadrop.model import Author, SLUG_LENGTH, slugify, get_available_slug
from mediadrop.model.meta import DBSession, metadata
from mediadrop.model.media import Media, MediaQuery, media
from mediadrop.plugin import events


podcasts = Table('podcasts', metadata,
    Column('id', Integer, autoincrement=True, primary_key=True, doc=\
        """The primary key ID."""),

    Column('slug', Unicode(SLUG_LENGTH), unique=True, nullable=False, doc=\
        """A unique URL-friendly permalink string for looking up this object.

        Be sure to call :func:`mediadrop.model.get_available_slug` to ensure
        the slug is unique."""),

    Column('created_on', DateTime, default=datetime.now, nullable=False, doc=\
        """The date and time this player was first created."""),

    Column('modified_on', DateTime, default=datetime.now, onupdate=datetime.now, nullable=False, doc=\
        """The date and time this player was last modified."""),

    Column('title', Unicode(50), nullable=False, doc=\
        """Display title."""),

    Column('subtitle', Unicode(255)),

    Column('description', UnicodeText),

    Column('category', Unicode(50), doc=\
        """The `iTunes category <http://www.apple.com/itunes/podcasts/specs.html#categories>`_

        Values with a ``>`` are parsed with special meaning. ``Arts > Design``
        implies that this pertains to the Design subcategory of Arts, and the
        feed markup reflects that."""),

    Column('author_name', Unicode(50), nullable=False),
    Column('author_email', Unicode(50), nullable=False),

    Column('explicit', Boolean, default=None, doc=\
        """The `iTunes explicit <http://www.apple.com/itunes/podcasts/specs.html#explicit>`_
        value.

            * ``True`` means 'yes'
            * ``None`` means no advisory displays, ie. 'no'
            * ``False`` means 'clean'

        """),

    Column('copyright', Unicode(50)),
    Column('itunes_url', Unicode(80), doc=\
        """Optional iTunes subscribe URL."""),

    Column('feedburner_url', Unicode(80), doc=\
        """Optional Feedburner URL.

        If set, requests for this podcast's feed will be forwarded to
        this address -- unless, of course, the request is coming from
        Feedburner."""),

    mysql_engine='InnoDB',
    mysql_charset='utf8',
)


class Podcast(object):
    """
    Podcast Metadata

    """
    query = DBSession.query_property()

    # TODO: replace '_thumb_dir' with something more generic, like 'name',
    #       so that its other uses throughout the code make more sense.
    _thumb_dir = 'podcasts'

    def __repr__(self):
        return '<Podcast: %r>' % self.slug

    @validates('slug')
    def validate_slug(self, key, slug):
        return slugify(slug)


mapper(Podcast, podcasts, order_by=podcasts.c.title, extension=events.MapperObserver(events.Podcast), properties={
    'author': composite(Author,
        podcasts.c.author_name,
        podcasts.c.author_email,
        doc="""An instance of :class:`mediadrop.model.authors.Author`.
               Although not actually a relation, it is implemented as if it were.
               This was decision was made to make it easier to integrate with
               :class:`mediadrop.model.auth.User` down the road."""),

    'media': dynamic_loader(Media, backref='podcast', query_class=MediaQuery, passive_deletes=True, doc=\
        """A query pre-filtered to media published under this podcast.
        Returns :class:`mediadrop.model.media.MediaQuery`."""),

    'media_count':
        column_property(
            sql.select(
                [sql.func.count(media.c.id)],
                media.c.podcast_id == podcasts.c.id,
            ).label('media_count'),
            deferred=True,
            doc="The total number of :class:`mediadrop.model.media.Media` episodes."
        ),
    'media_count_published':
        column_property(
            sql.select(
                [sql.func.count(media.c.id)],
                sql.and_(
                    media.c.podcast_id == podcasts.c.id,
                    media.c.reviewed == True,
                    media.c.encoded == True,
                    media.c.publishable == True,
                    media.c.publish_on <= sql.func.current_timestamp(),
                    sql.or_(
                        media.c.publish_until == None,
                        media.c.publish_until >= sql.func.current_timestamp(),
                    ),
                )
            ).label('media_count_published'),
            deferred=True,
            doc="The number of :class:`mediadrop.model.media.Media` episodes that are currently published."
        )
})

########NEW FILE########
__FILENAME__ = settings
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code contained in this file is licensed under the GPLv3 or
# (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.

"""
Settings Model

A very rudimentary settings implementation which is intended to store our
non-mission-critical options which can be edited via the admin UI.

.. todo:

    Rather than fetch one option at a time, load all settings into an object
    with attribute-style access.

"""
from sqlalchemy import Table, ForeignKey, Column
from sqlalchemy.exc import IntegrityError, ProgrammingError
from sqlalchemy.types import Unicode, UnicodeText, Integer, Boolean, Float
from sqlalchemy.orm import mapper, relation, backref, synonym, interfaces, validates
from urlparse import urlparse

from mediadrop.model.meta import DBSession, metadata
from mediadrop.plugin import events

settings = Table('settings', metadata,
    Column('id', Integer, autoincrement=True, primary_key=True),
    Column('key', Unicode(255), nullable=False, unique=True),
    Column('value', UnicodeText),
    mysql_engine='InnoDB',
    mysql_charset='utf8',
)

multisettings = Table('settings_multi', metadata,
    Column('id', Integer, autoincrement=True, primary_key=True),
    Column('key', Unicode(255), nullable=False),
    Column('value', UnicodeText, nullable=False),
    mysql_engine='InnoDB',
    mysql_charset='utf8',
)

class Setting(object):
    """
    A Single Setting
    """
    query = DBSession.query_property()

    def __init__(self, key=None, value=None):
        self.key = key or None
        self.value = value or None

    def __repr__(self):
        return '<Setting: %s = %r>' % (self.key, self.value)

    def __unicode__(self):
        return self.value

class MultiSetting(object):
    """
    A MultiSetting
    """
    query = DBSession.query_property()

    def __init__(self, key=None, value=None):
        self.key = key or None
        self.value = value or None

    def __repr__(self):
        return '<MultiSetting: %s = %r>' % (self.key, self.value)

    def __unicode__(self):
        return self.value

mapper(Setting, settings, extension=events.MapperObserver(events.Setting))
mapper(MultiSetting, multisettings, extension=events.MapperObserver(events.MultiSetting))

def insert_settings(defaults):
    """Insert the given setting if they don't exist yet.

    XXX: Does not include any support for MultiSetting. This approach
         won't work for that. We'll need to use a migration script.

    :type defaults: list
    :param defaults: Key and value pairs
    :rtype: list
    :returns: Any settings that have just been created.
    """
    inserted = []
    try:
        settings_query = DBSession.query(Setting.key)\
            .filter(Setting.key.in_([key for key, value in defaults]))
        existing_settings = set(x[0] for x in settings_query)
    except ProgrammingError:
        # If we are running paster setup-app on a fresh database with a
        # plugin which tries to use this function every time the
        # Environment.loaded event fires, the settings table will not
        # exist and this exception will be thrown, but its safe to ignore.
        # The settings will be created the next time the event fires,
        # which will likely be the first time the app server starts up.
        return inserted
    for key, value in defaults:
        if key in existing_settings:
            continue
        transaction = DBSession.begin_nested()
        try:
            s = Setting(key, value)
            DBSession.add(s)
            transaction.commit()
            inserted.append(s)
        except IntegrityError:
            transaction.rollback()
    if inserted:
        DBSession.commit()
    return inserted

def fetch_and_create_multi_setting(key, value):
    multisettings = MultiSetting.query\
        .filter(MultiSetting.key==key)\
        .all()
    for ms in multisettings:
        if ms.value == value:
            return ms
    ms = MultiSetting(key, value)
    DBSession.add(ms)
    return ms

########NEW FILE########
__FILENAME__ = storage
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code contained in this file is licensed under the GPLv3 or
# (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.

import logging

from datetime import datetime

from sqlalchemy import Column, sql, Table
from sqlalchemy.orm import column_property, dynamic_loader, mapper
from sqlalchemy.types import Boolean, DateTime, Integer, Unicode

from mediadrop.lib.storage import StorageEngine
from mediadrop.model.media import MediaFile, MediaFileQuery, media_files
from mediadrop.model.meta import metadata
from mediadrop.model.util import JSONType

log = logging.getLogger(__name__)

storage = Table('storage', metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('engine_type', Unicode(30), nullable=False),
    Column('display_name', Unicode(100), nullable=False, unique=True),
    Column('enabled', Boolean, nullable=False, default=True),
    Column('created_on', DateTime, nullable=False, default=datetime.now),
    Column('modified_on', DateTime, nullable=False, default=datetime.now,
                                                    onupdate=datetime.now),
    Column('data', JSONType, nullable=False, default=dict),
    mysql_engine='InnoDB',
    mysql_charset='utf8',
)

storage_mapper = mapper(
    StorageEngine, storage,
    polymorphic_on=storage.c.engine_type,
    properties={
        '_data': storage.c.data,

        # Avoid conflict with the abstract StorageEngine.engine_type property
        '_engine_type': storage.c.engine_type,

        # Make the storage engine available on MediaFile instances
        'files': dynamic_loader(
            MediaFile,
            backref='storage',
            query_class=MediaFileQuery,
            passive_deletes=True,
        ),
        'file_count': column_property(
            sql.select(
                [sql.func.count(media_files.c.id)],
                storage.c.id == media_files.c.storage_id,
            ).label('file_count'),
            deferred=True,
        ),
        'file_size_sum': column_property(
            sql.select(
                [sql.func.sum(media_files.c.size)],
                storage.c.id == media_files.c.storage_id,
            ).label('file_size_sum'),
            deferred=True,
        ),
    },
)

def add_engine_type(engine_cls):
    """Register this storage engine with the ORM."""
    log.debug('Registering engine %r: %r', engine_cls.engine_type, engine_cls)
    mapper(engine_cls,
           inherits=storage_mapper,
           polymorphic_identity=engine_cls.engine_type)

# Add our built-in storage engines to the polymorphic ORM mapping.
for engine in StorageEngine:
    add_engine_type(engine)

# Automatically add new engines as they're registered by plugins.
StorageEngine.add_register_observer(add_engine_type)

########NEW FILE########
__FILENAME__ = tags
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code contained in this file is licensed under the GPLv3 or
# (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.
"""
Tag-based Categorization

Content can be labelled in an ad-hoc fashion with tags. Typically tags will
be displayed on the frontend using a 'tag cloud', rather than listing all
tags. This means you can tag all you want!
"""

import re

from itertools import izip
from sqlalchemy import Table, Column, sql, func
from sqlalchemy.types import Unicode, Integer
from sqlalchemy.orm import mapper, validates

from mediadrop.model import SLUG_LENGTH, slugify
from mediadrop.model.meta import DBSession, metadata
from mediadrop.plugin import events


tags = Table('tags', metadata,
    Column('id', Integer, autoincrement=True, primary_key=True),
    Column('name', Unicode(50), unique=True, nullable=False),
    Column('slug', Unicode(SLUG_LENGTH), unique=True, nullable=False),
    mysql_engine='InnoDB',
    mysql_charset='utf8'
)

class Tag(object):
    """
    Tag (keyword) for labelling content

    .. attribute:: id

    .. attribute:: name

        Display name

    .. attribute:: slug

        A unique URL-friendly permalink string for looking up this object.

    .. attribute:: media_content

    .. attribute:: media_count_published

    """
    query = DBSession.query_property()

    def __init__(self, name=None, slug=None):
        self.name = name or None
        self.slug = slug or name or None

    def __repr__(self):
        return '<Tag: %r>' % self.name

    def __unicode__(self):
        return self.name

    @validates('slug')
    def validate_slug(self, key, slug):
        return slugify(slug)

class TagList(list):
    """
    List for easy rendering

    Automatically prints the contained tags separated by commas::

        >>> tags = TagList(['abc', 'def', 'ghi'])
        >>> tags
        abc, def, ghi

    """
    def __unicode__(self):
        return ', '.join([tag.name for tag in self.values()])

mapper(Tag, tags, order_by=tags.c.name, extension=events.MapperObserver(events.Tag))

excess_whitespace = re.compile('\s\s+', re.M)

def extract_tags(string):
    """Convert a comma separated string into a list of tag names.

    NOTE: The space-stripping here is necessary to patch a leaky abstraction.
          MySQL's string comparison with varchar columns is pretty fuzzy
          when it comes to space characters, and is even inconsistent between
          versions. We strip all preceding/trailing/duplicated spaces to be
          safe.

    """
    # count linebreaks as commas -- we assume user negligence
    string = string.replace("\n", ',')
    # strip repeating whitespace with a single space
    string = excess_whitespace.sub(' ', string)
    # make a tags list without any preceding and trailing whitespace
    tags = [tag.strip() for tag in string.split(',')]
    # remove duplicate and empty tags
    tags = set(tag for tag in tags if tag)
    return list(tags)

def fetch_and_create_tags(tag_names):
    """Return a list of Tag instances that match the given names.

    Tag names that don't yet exist are created automatically and
    returned alongside the results that did already exist.

    If you try to create a new tag that would have the same slug
    as an already existing tag, the existing tag is used instead.

    :param tag_names: The display :attr:`Tag.name`
    :type tag_names: list
    :returns: A list of :class:`Tag` instances.
    :rtype: :class:`TagList` instance

    """
    lower_names = [name.lower() for name in tag_names]
    slugs = [slugify(name) for name in lower_names]

    # Grab all the tags that exist already, whether its the name or slug
    # that matches. Slugs can be changed by the tag settings UI so we can't
    # rely on each tag name evaluating to the same slug every time.
    results = Tag.query.filter(sql.or_(func.lower(Tag.name).in_(lower_names),
                                       Tag.slug.in_(slugs))).all()

    # Filter out any tag names that already exist (case insensitive), and
    # any tag names evaluate to slugs that already exist.
    for tag in results:
        # Remove the match from our three lists until its completely gone
        while True:
            try:
                try:
                    index = slugs.index(tag.slug)
                except ValueError:
                    index = lower_names.index(tag.name.lower())
                tag_names.pop(index)
                lower_names.pop(index)
                slugs.pop(index)
            except ValueError:
                break

    # Any remaining tag names need to be created.
    if tag_names:
        # We may still have multiple tag names which evaluate to the same slug.
        # Load it into a dict so that duplicates are overwritten.
        uniques = dict((slug, name) for slug, name in izip(slugs, tag_names))
        # Do a bulk insert to create the tag rows.
        new_tags = [{'name': n, 'slug': s} for s, n in uniques.iteritems()]
        DBSession.execute(tags.insert(), new_tags)
        DBSession.flush()
        # Query for our newly created rows and append them to our result set.
        results += Tag.query.filter(Tag.slug.in_(uniques.keys())).all()

    return results

########NEW FILE########
__FILENAME__ = category_example_test
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code contained in this file is licensed under the GPLv3 or
# (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.

from mediadrop.lib.test.db_testcase import DBTestCase
from mediadrop.lib.test.pythonic_testcase import *
from mediadrop.model import Category


class CategoryExampleTest(DBTestCase):
    def test_can_create_example_category(self):
        category = Category.example()
        assert_not_none(category)
        assert_equals(u'Foo', category.name)
        assert_equals(u'foo', category.slug)
        assert_equals(0, category.parent_id)

    def test_can_override_example_data(self):
        category = Category.example(name=u'Bar')
        assert_equals(u'Bar', category.name)
        assert_equals(u'bar', category.slug)

    def test_can_override_only_existing_attributes(self):
        # should raise AssertionError
        assert_raises(AssertionError, lambda: Category.example(foo=u'bar'))


import unittest
def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(CategoryExampleTest))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')

########NEW FILE########
__FILENAME__ = group_example_test
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code contained in this file is licensed under the GPLv3 or
# (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.

from datetime import datetime, timedelta

from mediadrop.model import Group
from mediadrop.lib.test.db_testcase import DBTestCase
from mediadrop.lib.test.pythonic_testcase import *


class GroupExampleTest(DBTestCase):
    def test_can_create_example_group(self):
        group = Group.example()
        
        assert_not_none(group.group_id)
        assert_equals(u'baz_users', group.group_name)
        assert_equals(u'Baz Users', group.display_name)
        assert_almost_equals(datetime.now(), group.created, 
                             max_delta=timedelta(seconds=1))
    
    def test_can_override_example_data(self):
        group = Group.example(name=u'bar', display_name=u'Bar Foo')
        
        assert_equals(u'Bar Foo', group.display_name)
        assert_equals(u'bar', group.group_name)


import unittest
def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(GroupExampleTest))
    return suite

########NEW FILE########
__FILENAME__ = media_example_test
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code contained in this file is licensed under the GPLv3 or
# (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.

from mediadrop.model import Author, Media
from mediadrop.lib.test.db_testcase import DBTestCase
from mediadrop.lib.test.pythonic_testcase import *



class MediaExampleTest(DBTestCase):
    def test_can_create_example_media(self):
        media = Media.example()
        
        assert_not_none(media.id)
        assert_equals(u'Foo Media', media.title)
        assert_equals(u'foo-media', media.slug)
        assert_equals(Author(u'Joe', u'joe@site.example'), media.author)
        assert_length(0, media.files)
        
        assert_none(media.type)
        assert_none(media.podcast_id)
        
        assert_false(media.publishable)
        assert_false(media.reviewed)
        assert_false(media.encoded)
        assert_none(media.publish_on)
        assert_none(media.publish_until)
        assert_false(media.is_published)
    
    def test_can_override_example_data(self):
        media = Media.example(title=u'Bar Foo')
        
        assert_equals(u'Bar Foo', media.title)
        assert_equals(u'bar-foo', media.slug)


import unittest
def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(MediaExampleTest))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')

########NEW FILE########
__FILENAME__ = media_status_test
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code contained in this file is licensed under the GPLv3 or
# (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.

from ddt import ddt as DataDrivenTestCase, data

from mediadrop.model import DBSession, Media
from mediadrop.lib.filetypes import (guess_media_type_map, AUDIO, AUDIO_DESC, 
    CAPTIONS, VIDEO)
from mediadrop.lib.players import AbstractFlashPlayer, FlowPlayer
from mediadrop.lib.storage.api import add_new_media_file
from mediadrop.lib.test.db_testcase import DBTestCase
from mediadrop.lib.test.pythonic_testcase import *
from mediadrop.plugin import events
from mediadrop.plugin.events import observes

#import logging
#logging.basicConfig(level=logging.DEBUG)
media_suffixes = guess_media_type_map.keys()
video_types = filter(lambda key: guess_media_type_map[key] == VIDEO, media_suffixes)
audio_types = filter(lambda key: guess_media_type_map[key] == AUDIO, media_suffixes)
caption_types = filter(lambda key: guess_media_type_map[key] == CAPTIONS, media_suffixes)

@DataDrivenTestCase
class MediaStatusUpdatesTypeTest(DBTestCase):
    def setUp(self):
        super(MediaStatusUpdatesTypeTest, self).setUp()
        # prevent warning about missing handlers for logger 
        # "mediadrop.model.players" ("fetch_enabled_players()")
        self.init_flowplayer()
        self.media = Media.example()
    
    def init_flowplayer(self):
        AbstractFlashPlayer.register(FlowPlayer)
        FlowPlayer.inject_in_db(enable_player=True)
    
    def add_external_file(self, media, file_suffix='mp4'):
        url = u'http://site.example/videos.%s' % file_suffix
        previous_files = len(media.files)
        media_file = add_new_media_file(media, url=url)
        # add_new_media_file will set media_file.media AND media.files.append
        # so we have two files for the media until the session is refreshed.
        DBSession.refresh(media)
        assert_length(previous_files+1, media.files)
        return media_file
    
    @data(*video_types)
    def test_can_detect_video_files(self, suffix):
        media = Media.example()
        assert_not_equals(VIDEO, media.type)
        self.add_external_file(media, suffix)
        media.update_status()
        assert_equals(VIDEO, media.type, message='did not detect %s as VIDEO type' % suffix)
    
    @data(*audio_types)
    def test_can_detect_audio_files(self, suffix):
        media = Media.example()
        assert_not_equals(AUDIO, media.type)
        self.add_external_file(media, suffix)
        media.update_status()
        assert_equals(AUDIO, media.type, message='did not detect %s as AUDIO type' % suffix)
    
    @data(*audio_types)
    def test_does_not_set_type_if_only_audio_description_files_are_attached(self, suffix):
        media = Media.example()
        assert_none(media.type)
        media_file = self.add_external_file(media, suffix)
        media_file.type = AUDIO_DESC
        media.update_status()
        assert_none(media.type, message='did detect media with audio description file as %s' % media.type)
    
    @data(*caption_types)
    def test_does_not_set_type_if_only_caption_files_are_attached(self, suffix):
        media = Media.example()
        assert_none(media.type)
        self.add_external_file(media, suffix)
        media.update_status()
        assert_none(media.type, message='did detect media with caption file as %s' % media.type)
    
    def test_sets_video_type_if_media_contains_audio_and_video_files(self):
        media = Media.example()
        assert_none(media.type)
        self.add_external_file(media, 'mp4')
        self.add_external_file(media, 'mp3')
        media.update_status()
        assert_equals(VIDEO, media.type, message='did not detect mixed video/audio media as VIDEO type')
        


import unittest
def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(MediaStatusUpdatesTypeTest))
    return suite


########NEW FILE########
__FILENAME__ = media_test
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code contained in this file is licensed under the GPLv3 or
# (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.

from mediadrop.model import DBSession, Media
from mediadrop.lib.filetypes import VIDEO
from mediadrop.lib.players import AbstractFlashPlayer, FlowPlayer
from mediadrop.lib.storage.api import add_new_media_file
from mediadrop.lib.test.db_testcase import DBTestCase
from mediadrop.lib.test.pythonic_testcase import *
from mediadrop.plugin import events
from mediadrop.plugin.events import observes


class MediaTest(DBTestCase):
    def setUp(self):
        super(MediaTest, self).setUp()
        self.init_flowplayer()
        self.media = Media.example()
        self.encoding_event = self.create_spy_on_event(events.Media.encoding_done)
    
    def init_flowplayer(self):
        AbstractFlashPlayer.register(FlowPlayer)
        FlowPlayer.inject_in_db(enable_player=True)
    
    def create_spy_on_event(self, event):
        encoding_event = create_spy()
        observes(event)(encoding_event)
        return encoding_event
    
    def add_external_file(self, media, url=u'http://site.example/videos.mp4'):
        previous_files = len(media.files)
        media_file = add_new_media_file(media, url=url)
        # add_new_media_file will set media_file.media AND media.files.append
        # so we have two files for the media until the session is refreshed.
        DBSession.refresh(media)
        assert_length(previous_files+1, media.files)
        return media_file
    
    def test_can_update_status(self):
        assert_false(self.media.encoded)
        
        self.media.update_status()
        assert_false(self.media.encoded)
        self.encoding_event.assert_was_not_called()
    
    def test_triggers_event_when_media_was_encoded(self):
        self.add_external_file(self.media)
        assert_false(self.media.encoded)
        self.media.update_status()
        
        assert_equals(VIDEO, self.media.type)
        assert_true(self.media.encoded)
        self.encoding_event.assert_was_called_with(self.media)
        
        # only send event when the encoding status changes!
        second_encoding_event = self.create_spy_on_event(events.Media.encoding_done)
        self.media.update_status()
        second_encoding_event.assert_was_not_called()


import unittest
def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(MediaTest))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')

########NEW FILE########
__FILENAME__ = user_example_test
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code contained in this file is licensed under the GPLv3 or
# (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.

from datetime import datetime, timedelta

from mediadrop.model import User
from mediadrop.lib.test.db_testcase import DBTestCase
from mediadrop.lib.test.pythonic_testcase import *


class UserExampleTest(DBTestCase):
    def test_can_create_example_user(self):
        user = User.example()
        
        assert_not_none(user.id)
        assert_equals(u'joe', user.user_name)
        assert_equals(u'Joe Smith', user.display_name)
        assert_equals(u'joe@site.example', user.email_address)
        assert_almost_equals(datetime.now(), user.created, 
                             max_delta=timedelta(seconds=1))
    
    def test_can_override_example_data(self):
        user = User.example(display_name=u'Bar Foo')
        
        assert_equals(u'Bar Foo', user.display_name)


import unittest
def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(UserExampleTest))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')

########NEW FILE########
__FILENAME__ = util
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.

__all__ = ['JSONType']


# copied straight from the SQLAlchemy 0.8.1 manual:
# ORM Extensions > Mutation Tracking > Establishing Mutability on Scalar Column Values
import collections

import simplejson
from sqlalchemy.ext.mutable import Mutable
from sqlalchemy.types import Text, TypeDecorator

class JSONEncodedDict(TypeDecorator):
    "Represents an immutable structure as a json-encoded string."

    impl = Text

    def process_bind_param(self, value, dialect):
        if value is not None:
            value = simplejson.dumps(value)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            value = simplejson.loads(value)
        return value


class MutableDict(Mutable, dict):
    @classmethod
    def coerce(cls, key, value):
        "Convert plain dictionaries to MutableDict."

        if not isinstance(value, MutableDict):
            if isinstance(value, dict):
                return MutableDict(value)

            # this call will raise ValueError
            return Mutable.coerce(key, value)
        else:
            return value

    def __setitem__(self, key, value):
        "Detect dictionary set events and emit change events."

        dict.__setitem__(self, key, value)
        self.changed()

    def __delitem__(self, key):
        "Detect dictionary del events and emit change events."

        dict.__delitem__(self, key)
        self.changed()

JSONType = MutableDict.as_mutable(JSONEncodedDict)


########NEW FILE########
__FILENAME__ = abc
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code contained in this file is licensed under the GPLv3 or
# (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.

from itertools import chain

from mediadrop.lib.compat import defaultdict

class AbstractMetaClass(type):
    """
    Abstract Class Manager

    This combines concepts from the Trac ComponentMeta class and
    Python 2.6's abc module:

        * http://www.python.org/dev/peps/pep-3119/#specification
        * http://svn.python.org/view/python/trunk/Lib/abc.py?view=markup
        * http://trac.edgewall.org/browser/trunk/trac/core.py#L85

    """
    _registry = defaultdict(list)
    _abstracts = {}
    _observers = {}

    def __new__(mcls, name, bases, namespace):
        """Create a class object for an abstract class or its implementation.

        For abstract classes, we store the set of abstract attributes
        that have been defined. We use this data in :meth:`register`
        to validate all subclasses to ensure it has a complete
        implementation.

        """
        cls = type.__new__(mcls, name, bases, namespace)
        abstracts = set(key
                        for key, value in namespace.iteritems()
                        if getattr(value, '_isabstract', False))
        for base in bases:
            for name in AbstractMetaClass._abstracts.get(base, ()):
                cls_attr = getattr(cls, name, None)
                if getattr(cls_attr, '_isabstract', False):
                    abstracts.add(name)
        AbstractMetaClass._abstracts[cls] = abstracts
        return cls

    def register(cls, subclass):
        """Register an implementation of the abstract class.

        :param cls: The abstract class
        :param subclass: A complete implementation of the abstract class.
        :raises ImplementationError: If the subclass contains any
            unimplemented abstract methods or properties.

        """
        # If an attr was abstract when the class was created, check again
        # to see if it was implemented after the fact (by monkepatch etc).
        missing = []
        for name in AbstractMetaClass._abstracts.get(subclass, ()):
            attr = getattr(subclass, name)
            if getattr(attr, '_isabstract', False):
                missing.append(name)
        if missing:
            raise ImplementationError(
                'Cannot register %r under %r because it contains abstract '
                'methods/properties: %s' % (subclass, cls, ', '.join(missing))
            )
        # Register the subclass, calling observers all the way up the
        # inheritance tree as we go.
        for base in chain((subclass,), cls.__mro__):
            if base.__class__ is AbstractMetaClass:
                if base is subclass:
                    AbstractMetaClass._registry[base]
                else:
                    AbstractMetaClass._registry[base].append(subclass)
                for observer in AbstractMetaClass._observers.get(base, ()):
                    observer(subclass)

    def add_register_observer(cls, callable):
        """Notify this callable when a subclass of this abstract is registered.

        This is useful when some action must be taken for each new
        implementation of an abstract class. This observer will also be
        called any time any of its sub-abstract classes are implemented.

        :param cls: The abstract class
        :param callable: A function that expects a subclass as its
            first and only argument.

        """
        AbstractMetaClass._observers.setdefault(cls, []).append(callable)

    def remove_register_observer(cls, callable):
        """Cancel notifications to this callable for this abstract class.

        :param cls: The abstract class
        :param callable: A function that expects a subclass as its
            first and only argument.
        :raises ValueError: If the callable has not been registered.

        """
        AbstractMetaClass._observers.setdefault(cls, []).remove(callable)

    def __iter__(cls):
        """Iterate over all implementations of the given abstract class."""
        return iter(AbstractMetaClass._registry[cls])

    def __contains__(cls, subclass):
        """Return True if the first class is a parent of the second class."""
        return subclass in AbstractMetaClass._registry[cls]

class AbstractClass(object):
    """
    An optional base for abstract classes to subclass.
    """
    __metaclass__ = AbstractMetaClass

def abstractmethod(func):
    func._isabstract = True
    return func

class abstractproperty(property):
    _isabstract = True

def isabstract(x):
    """Return True if given an abstract class, method, or property."""
    if isinstance(x, AbstractMetaClass):
        return x in AbstractMetaClass._registry \
            and not AbstractMetaClass._abstracts.get(x, ())
    elif isinstance(x, (abstractmethod, abstractproperty)):
        return x._isabstract
    else:
        raise NotImplementedError

class ImplementationError(Exception):
    """
    Error raised when a partial abstract class implementation is registered.
    """

def _reset_registry():
    AbstractMetaClass._registry.clear()
    AbstractMetaClass._abstracts.clear()
    AbstractMetaClass._observers.clear()

########NEW FILE########
__FILENAME__ = events
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code contained in this file is licensed under the GPLv3 or
# (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.
"""
Abstract events which plugins subscribe to and are called by the app.
"""
from collections import deque
import logging

from sqlalchemy.orm.interfaces import MapperExtension


__all__ = ['Event', 'GeneratorEvent', 'FetchFirstResultEvent', 'observes']

log = logging.getLogger(__name__)

class Event(object):
    """
    An arbitrary event that's triggered and observed by different parts of the app.

        >>> e = Event()
        >>> e.observers.append(lambda x: x)
        >>> e('x')
    """
    def __init__(self, args=()):
        self.args = args and tuple(args) or None
        self.pre_observers = deque()
        self.post_observers = deque()
    
    @property
    def observers(self):
        return tuple(self.pre_observers) + tuple(self.post_observers)

    def __call__(self, *args, **kwargs):
        # This is helpful for events which are triggered explicitly in the code
        # (e.g. Environment.loaded)
        for observer in self.observers:
            observer(*args, **kwargs)

    def __iter__(self):
        return iter(self.observers)

class GeneratorEvent(Event):
    """
    An arbitrary event that yields all results from all observers.
    """
    def is_list_like(self, value):
        if isinstance(value, basestring):
            return False
        try:
            iter(value)
        except TypeError:
            return False
        return True
    
    def __call__(self, *args, **kwargs):
        for observer in self.observers:
            result = observer(*args, **kwargs)
            if self.is_list_like(result):
                for item in result:
                    yield item
            else:
                yield result


class FetchFirstResultEvent(Event):
    """
    An arbitrary event that return the first result from its observers
    """
    def __call__(self, *args, **kwargs):
        for observer in self.observers:
            result = observer(*args, **kwargs)
            if result is not None:
                return result
        return None

class observes(object):
    """
    Register the decorated function as an observer of the given event.
    """
    def __init__(self, *events, **kwargs):
        self.events = events
        self.appendleft = kwargs.pop('appendleft', False)
        self.run_before = kwargs.pop('run_before', False)
        if kwargs:
            first_key = list(kwargs)[0]
            raise TypeError('TypeError: observes() got an unexpected keyword argument %r' % first_key)

    def __call__(self, func):
        for event in self.events:
            observers = event.post_observers
            if self.run_before:
                observers = event.pre_observers
            
            if self.appendleft:
                observers.appendleft(func)
            else:
                observers.append(func)
        return func

class MapperObserver(MapperExtension):
    """
    Fire events whenever the mapper triggers any kind of row modification.
    """
    def __init__(self, event_group):
        self.event_group = event_group

    def after_delete(self, mapper, connection, instance):
        self.event_group.after_delete(instance)

    def after_insert(self, mapper, connection, instance):
        self.event_group.after_insert(instance)

    def after_update(self, mapper, connection, instance):
        self.event_group.after_update(instance)

    def before_delete(self, mapper, connection, instance):
        self.event_group.before_delete(instance)

    def before_insert(self, mapper, connection, instance):
        self.event_group.before_insert(instance)

    def before_update(self, mapper, connection, instance):
        self.event_group.before_update(instance)

###############################################################################
# Application Setup

class Environment(object):
    before_route_setup = Event(['mapper'])
    after_route_setup = Event(['mapper'])
    # TODO: deprecation warning
    routes = after_route_setup
    
    routes = Event(['mapper'])
    init_model = Event([])
    loaded = Event(['config'])
    
    # fires when a new database was initialized (tables created)
    database_initialized = Event([])
    
    # an existing database was migrated to a newer DB schema
    database_migrated = Event([])
    
    # the environment has been loaded, the database is ready to use
    database_ready = Event([])

###############################################################################
# Controllers

class Admin(object):

    class CategoriesController(object):
        index = Event(['**kwargs'])
        bulk = Event(['**kwargs'])
        edit = Event(['**kwargs'])
        save = Event(['**kwargs'])

    class CommentsController(object):
        index = Event(['**kwargs'])
        save_status = Event(['**kwargs'])
        save_edit = Event(['**kwargs'])

    class IndexController(object):
        index = Event(['**kwargs'])
        media_table = Event(['**kwargs'])

    class MediaController(object):
        bulk = Event(['type=None, ids=None, **kwargs'])
        index = Event(['**kwargs'])
        edit = Event(['**kwargs'])
        save = Event(['**kwargs'])
        add_file = Event(['**kwargs'])
        edit_file = Event(['**kwargs'])
        merge_stubs = Event(['**kwargs'])
        save_thumb = Event(['**kwargs'])
        update_status = Event(['**kwargs'])

    class PodcastsController(object):
        index = Event(['**kwargs'])
        edit = Event(['**kwargs'])
        save = Event(['**kwargs'])
        save_thumb = Event(['**kwargs'])

    class TagsController(object):
        index = Event(['**kwargs'])
        edit = Event(['**kwargs'])
        save = Event(['**kwargs'])
        bulk = Event(['**kwargs'])

    class UsersController(object):
        index = Event(['**kwargs'])
        edit = Event(['**kwargs'])
        save = Event(['**kwargs'])
        delete = Event(['**kwargs'])

    class GroupsController(object):
        index = Event(['**kwargs'])
        edit = Event(['**kwargs'])
        save = Event(['**kwargs'])
        delete = Event(['**kwargs'])
    
    class Players(object):
        HTML5OrFlashPrefsForm = Event(['form'])
        SublimePlayerPrefsForm = Event(['form'])
        YoutubeFlashPlayerPrefsForm = Event(['form'])
    
    class PlayersController(object):
        delete = Event(['**kwargs'])
        disable = Event(['**kwargs'])
        edit = Event(['**kwargs'])
        enable = Event(['**kwargs'])
        index = Event(['**kwargs'])
        reorder = Event(['**kwargs'])
    
    class Settings(object):
        AdvertisingForm = Event(['form'])
        AnalyticsForm = Event(['form'])
        APIForm = Event(['form'])
        AppearanceForm = Event(['form'])
        CommentsForm = Event(['form'])
        GeneralForm = Event(['form'])
        NotificationsForm = Event(['form'])
        PopularityForm = Event(['form'])
        SiteMapsForm = Event(['form'])
        UploadForm = Event(['form'])
    
    class SettingsController(object):
        advertising_save = Event(['**kwargs'])
        analytics_save = Event(['**kwargs'])
        appearance_save = Event(['**kwargs'])
        comments_save = Event(['**kwargs'])
        general_save = Event(['**kwargs'])
        notifications_save = Event(['**kwargs'])
        popularity_save = Event(['**kwargs'])
        # probably this event will be renamed to 'api_save' in a future version
        save_api = Event(['**kwargs'])
        sitemaps_save = Event(['**kwargs'])
        upload_save = Event(['**kwargs'])
    
    class Storage(object):
        LocalFileStorageForm = Event(['form'])
        FTPStorageForm = Event(['form'])
        RemoteURLStorageForm = Event(['form'])
    
    class StorageController(object):
        delete = Event(['**kwargs'])
        disable = Event(['**kwargs'])
        edit = Event(['**kwargs'])
        enable = Event(['**kwargs'])
        index = Event(['**kwargs'])


class API(object):
    class MediaController(object):
        index = Event(['**kwargs'])
        get = Event(['**kwargs'])

class CategoriesController(object):
    index = Event(['**kwargs'])
    more = Event(['**kwargs'])
    # feed observers (if they are not marked as "run_before=True") must support
    # pure string output (from beaker cache) instead of a dict with template
    # variables.
    feed = Event(['limit', '**kwargs'])

class ErrorController(object):
    document = Event(['**kwargs'])
    report = Event(['**kwargs'])

class LoginController(object):
    login = Event(['**kwargs'])
    login_handler = Event(['**kwargs'])
    logout_handler = Event(['**kwargs'])
    post_login = Event(['**kwargs'])
    post_logout = Event(['**kwargs'])

class MediaController(object):
    index = Event(['**kwargs'])
    comment = Event(['**kwargs'])
    explore = Event(['**kwargs'])
    embed_player = Event(['xhtml'])
    jwplayer_rtmp_mrss = Event(['**kwargs'])
    rate = Event(['**kwargs'])
    view = Event(['**kwargs'])

class PodcastsController(object):
    index = Event(['**kwargs'])
    view = Event(['**kwargs'])
    feed = Event(['**kwargs'])

class SitemapsController(object):
    # observers (if they are not marked as "run_before=True") must support pure 
    # string output (from beaker cache) instead of a dict with template variables.
    google = Event(['page', 'limit', '**kwargs'])
    mrss = Event(['**kwargs'])
    latest = Event(['limit', 'skip', '**kwargs'])
    featured = Event(['limit', 'skip', '**kwargs'])

class UploadController(object):
    index = Event(['**kwargs'])
    submit = Event(['**kwargs'])
    submit_async = Event(['**kwargs'])
    success = Event(['**kwargs'])
    failure = Event(['**kwargs'])

###############################################################################
# Models

class Media(object):
    before_delete = Event(['instance'])
    after_delete = Event(['instance'])
    before_insert = Event(['instance'])
    after_insert = Event(['instance'])
    before_update = Event(['instance'])
    after_update = Event(['instance'])
    
    # event is triggered when the encoding status changes from 'not encoded' to
    # 'encoded'
    encoding_done = Event(['instance'])

class MediaFile(object):
    before_delete = Event(['instance'])
    after_delete = Event(['instance'])
    before_insert = Event(['instance'])
    after_insert = Event(['instance'])
    before_update = Event(['instance'])
    after_update = Event(['instance'])

class Podcast(object):
    before_delete = Event(['instance'])
    after_delete = Event(['instance'])
    before_insert = Event(['instance'])
    after_insert = Event(['instance'])
    before_update = Event(['instance'])
    after_update = Event(['instance'])

class Comment(object):
    before_delete = Event(['instance'])
    after_delete = Event(['instance'])
    before_insert = Event(['instance'])
    after_insert = Event(['instance'])
    before_update = Event(['instance'])
    after_update = Event(['instance'])

class Category(object):
    before_delete = Event(['instance'])
    after_delete = Event(['instance'])
    before_insert = Event(['instance'])
    after_insert = Event(['instance'])
    before_update = Event(['instance'])
    after_update = Event(['instance'])

class Tag(object):
    before_delete = Event(['instance'])
    after_delete = Event(['instance'])
    before_insert = Event(['instance'])
    after_insert = Event(['instance'])
    before_update = Event(['instance'])
    after_update = Event(['instance'])

class Setting(object):
    before_delete = Event(['instance'])
    after_delete = Event(['instance'])
    before_insert = Event(['instance'])
    after_insert = Event(['instance'])
    before_update = Event(['instance'])
    after_update = Event(['instance'])

class MultiSetting(object):
    before_delete = Event(['instance'])
    after_delete = Event(['instance'])
    before_insert = Event(['instance'])
    after_insert = Event(['instance'])
    before_update = Event(['instance'])
    after_update = Event(['instance'])

class User(object):
    before_delete = Event(['instance'])
    after_delete = Event(['instance'])
    before_insert = Event(['instance'])
    after_insert = Event(['instance'])
    before_update = Event(['instance'])
    after_update = Event(['instance'])

###############################################################################
# Forms

PostCommentForm = Event(['form'])
UploadForm = Event(['form'])
LoginForm = Event(['form'])
Admin.CategoryForm = Event(['form'])
Admin.CategoryRowForm = Event(['form'])
Admin.EditCommentForm = Event(['form'])
Admin.MediaForm = Event(['form'])
Admin.AddFileForm = Event(['form'])
Admin.EditFileForm = Event(['form'])
Admin.UpdateStatusForm = Event(['form'])
Admin.SearchForm = Event(['form'])
Admin.PodcastForm = Event(['form'])
Admin.PodcastFilterForm = Event(['form'])
Admin.UserForm = Event(['form'])
Admin.GroupForm = Event(['form'])
Admin.TagForm = Event(['form'])
Admin.TagRowForm = Event(['form'])
Admin.ThumbForm = Event(['form'])

###############################################################################
# Miscellaneous... may require refactoring

media_types = GeneratorEvent([])
plugin_settings_links = GeneratorEvent([])
EncodeMediaFile = Event(['media_file'])
page_title = FetchFirstResultEvent('default=None, category=None, \
    media=None, podcast=None, upload=None, **kwargs')
meta_keywords = FetchFirstResultEvent('category=None, media=None, \
    podcast=None, upload=None, **kwargs')
meta_description = FetchFirstResultEvent('category=None, media=None, \
    podcast=None, upload=None, **kwargs')
meta_robots_noindex = FetchFirstResultEvent('categories=None, rss=None, **kwargs')

########NEW FILE########
__FILENAME__ = manager
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code contained in this file is licensed under the GPLv3 or
# (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.

import logging
import os
import re

from genshi.template import loader
from pkg_resources import iter_entry_points
from pylons.wsgiapp import PylonsApp
from routes.util import controller_scan

from mediadrop.plugin.plugin import MediaDropPlugin
from mediadrop.lib.result import Result


__all__ = ['PluginManager']

log = logging.getLogger(__name__)


class PluginManager(object):
    """
    Plugin Loading and Management

    This class is responsible for loading plugins that define an entry point
    within the group 'mediadrop.plugin'. It introspects the plugin module to
    find any templates, public static files, or controllers it may provide.
    Names and paths are based on the name of the entry point, and should be
    unique.

    Plugins may also register event observers and/or implement interfaces
    as a result of being loaded, but we do not handle any of that here.

    """
    def __init__(self, config):
        log.debug('Initializing plugins')
        self.config = config
        self.DEBUG = config['debug']
        self.plugins = {}
        self._match_templates = {}

        # all plugins are enabled by default (for compatibility with MediaCore < 0.10)
        enabled_plugins = re.split('\s*,\s*', config.get('plugins', '*'))
        mediadrop_epoints = self._discover_plugins('mediadrop.plugin')
        self.plugins = self._initialize_enabled_plugins(mediadrop_epoints, enabled_plugins)

        # compat with MediaCore < 0.11
        mediacore_epoints = self._discover_plugins('mediacore.plugin')
        legacy_plugins = self._initialize_enabled_plugins(mediacore_epoints,
            enabled_plugins, plugins_to_skip=self.plugins.keys())
        self.plugins.update(legacy_plugins)
        if legacy_plugins:
            legacy_ids = ', '.join(legacy_plugins.keys())
            log.info('Loaded legacy MediaCore CE plugin(s): %s' % legacy_ids)

    def _discover_plugins(self, entry_point_name):
        for epoint in iter_entry_points(entry_point_name):
            yield epoint

    def _initialize_enabled_plugins(self, entry_points, enabled_plugins, plugins_to_skip=()):
        plugins = dict()
        for epoint in entry_points:
            plugin_id = epoint.name
            if plugin_id in plugins_to_skip:
                continue
            if (plugin_id not in enabled_plugins) and ('*' not in enabled_plugins):
                log.debug('Skipping plugin %s: not enabled' % plugin_id)
                continue
            plugins[plugin_id] = self.plugin_from_entry_point(epoint)
            log.debug('Plugin loaded: %r', epoint)
        return plugins

    def plugin_from_entry_point(self, epoint):
        module = epoint.load()
        plugin_class = getattr(module, '__plugin__', MediaDropPlugin)
        return plugin_class(module, epoint.name)

    def public_paths(self):
        """Return a dict of all 'public' folders in the loaded plugins.

        :returns: A dict keyed by the plugin public directory for use in
            URLs, the value being the absolute path to the directory that
            contains the static files.
        """
        paths = {}
        for name, plugin in self.plugins.iteritems():
            if plugin.public_path:
                paths['/' + name + '/public'] = plugin.public_path
        log.debug('Public paths: %r', paths)
        return paths

    def locale_dirs(self):
        """Return a dict of all i18n locale dirs needed by the loaded plugins.

        :returns: A dict whose keys are i18n domain names and values are the
            path to the locale dir where messages can be loaded.
        """
        locale_dirs = {}
        i18n_env_dir = os.path.join(self.config['env_dir'], 'i18n')
        for plugin in self.plugins.itervalues():
            if plugin.locale_dirs:
                for domain, plugin_i18n_dir in plugin.locale_dirs.items():
                    locale_dirs[domain] = (plugin_i18n_dir, i18n_env_dir)
        return locale_dirs

    def template_loaders(self):
        """Return genshi loaders for all the plugins that provide templates.

        Plugin template are found under its module name::

            <xi:include "{plugin.name}/index.html" />

        Maps to::

            `{path_to_module}/templates/index.html`

        :rtype: list
        :returns: Instances of :class:`genshi.template.loader.TemplateLoader`
        """
        loaders = {}
        for name, plugin in self.plugins.iteritems():
            if plugin.templates_path:
                loaders[name + '/'] = plugin.templates_path
        if loaders:
            log.debug('Template loaders: %r', loaders)
            return [loader.prefixed(**loaders)]
        return []

    def match_templates(self, template):
        """Return plugin templates that should be included into to the given template.

        This is easiest explained by example: to extend the `media/view.html` template,
        your plugin should provide its own `media/view.html` file in its templates
        directory. This override template would be directly includable like so::

            /{plugin.name}/media/view.html

        Typically this file would use Genshi's `py:match directive
        <http://genshi.edgewall.org/wiki/Documentation/xml-templates.html#id5>`_
        to hook and wrap or replace certain tags within the core output.

        :param template: A relative template include path, which the Genshi
            loader will later resolve.
        :rtype: list
        :returns: Relative paths ready for use in <xi:include> in a Genshi template.
        """
        template = os.path.normpath(template)
        if template in self._match_templates and not self.DEBUG:
            matches = self._match_templates[template]
        else:
            matches = self._match_templates[template] = []
            for name, plugin in self.plugins.iteritems():
                templates_path = plugin.templates_path
                if templates_path is not None \
                and os.path.exists(os.path.join(templates_path, template)):
                    matches.append(os.path.sep + os.path.join(name, template))
        return matches

    def migrators(self):
        for plugin in self.plugins.itervalues():
            migrator_class = getattr(plugin, 'migrator_class')
            if plugin.contains_migrations():
                migrator = migrator_class.from_config(plugin, self.config, log=log)
                yield migrator

    def is_db_scheme_current_for_all_plugins(self):
        for migrator in self.migrators():
            if migrator.db_needs_upgrade():
                return Result(False, message='Database should be updated for plugin %r.' % migrator.plugin_name)
        return True

    def controller_classes(self):
        """Return a dict of controller classes that plugins have defined.

        Plugin modules are introspected for an attribute named either:

            * `__controller__` or
            * `{Modulename}Controller`

        In both cases, the controller "name" as far as the application
        (including routes) is concerned is the module name.

        :rtype: dict
        :returns: A mapping of controller names to controller classes.
        """
        classes = {}
        for plugin in self.plugins.itervalues():
            classes.update(plugin.controllers)
        return classes

    def controller_scan(self, directory):
        """Extend the controller discovery by routes with our plugin controllers.

        :param directory: The full path to the core controllers directory.
        :rtype: list
        :returns: Controller names
        """
        return controller_scan(directory) + self.controller_classes().keys()

    def wrap_pylons_app(self, app):
        """Pass PylonsApp our controllers to bypass its autodiscovery.

        :meth:`pylons.wsgiapp.PylonsApp.find_controller` is pretty limited
        in where it will try to import controllers from. However, it does
        cache the controllers it has imported in a public dictionary. We
        pass the plugin controllers that we've discovered to bypass the
        standard Pylons discovery method.

        XXX: This relies on an undocumented feature of PylonsApp. We'll
             need to subclass instead if this API changes.

        :param app: The :class:`pylons.wsgiapp.PylonsApp` instance.
        :returns: The :class:`pylons.wsgiapp.PylonsApp` instance.
        """
        if isinstance(app, PylonsApp):
            app.controller_classes = self.controller_classes()
            log.debug('App wrapped')
        else:
            log.warn('The given app %r is NOT an instance of PylonsApp', app)
        return app

########NEW FILE########
__FILENAME__ = plugin
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code contained in this file is licensed under the GPLv3 or
# (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.

import logging
import os

from importlib import import_module
import pkg_resources
from pkg_resources import resource_exists, resource_filename
from pylons.util import class_name_from_module_name
from routes.util import controller_scan


__all__ = ['MediaDropPlugin']

log = logging.getLogger(__name__)


class MediaDropPlugin(object):
    """
    Plugin Metadata

    This houses all the conventions for where resources should be found
    within a plugin module. A plugin author could potentially extend this
    class to redefine these conventions according to their needs. Besides
    that, it gives us a convenient place to store this data for repeated
    use.

    """
    def __init__(self, module, name, templates_path=None,
                 public_path=None, controllers=None, locale_dirs=None):
        self.module = module
        self.modname = module.__name__
        self.name = name
        self.package_name = self._package_name()
        self.templates_path = templates_path or self._default_templates_path()
        self.public_path = public_path or self._default_public_path()
        self.controllers = controllers or self._default_controllers()
        self.locale_dirs = locale_dirs or self._default_locale_dirs()
        # migrations.util imports model and that causes all kind of recursive
        # import trouble with mediadrop.plugin (events)
        from mediadrop.migrations import PluginDBMigrator
        self.migrator_class = PluginDBMigrator
        self.add_db_defaults = self._db_default_callable()

    def _package_name(self):
        pkg_provider = pkg_resources.get_provider(self.modname)
        module_path = self.modname.replace('.', os.sep)
        is_package = pkg_provider.module_path.endswith(module_path)
        if is_package:
            return self.modname
        return self.modname.rsplit('.', 1)[0]

    def _default_templates_path(self):
        if resource_exists(self.modname, 'templates'):
            return resource_filename(self.modname, 'templates')
        return None

    def _default_locale_dirs(self):
        if resource_exists(self.modname, 'i18n'):
            localedir = resource_filename(self.modname, 'i18n')
            return {self.name: localedir}
        return None

    def _default_public_path(self):
        if resource_exists(self.modname, 'public'):
            return resource_filename(self.modname, 'public')
        return None

    def _default_controllers(self):
        # Find controllers in the root plugin __init__.py
        controller_class = _controller_class_from_module(self.module, self.name)
        if controller_class:
            class_name = controller_class.__module__ + '.' + controller_class.__name__
            log.debug('Controller loaded; "%s" = %s' % (self.name, class_name))
            return {self.name: controller_class}

        # Search a controllers directory, standard pylons style
        if not resource_exists(self.package_name, 'controllers'):
            log.debug('no controllers found for %r plugin.' % self.name)
            return {}
        controllers = {}
        directory = resource_filename(self.package_name, 'controllers')
        for name in controller_scan(directory):
            module_name = '.'.join([self.package_name, 'controllers',
                                    name.replace('/', '.')])
            module = import_module(module_name)
            mycontroller = _controller_class_from_module(module, name)
            if mycontroller is None:
                log.warn('Controller %r expected but not found in: %r', name, module)
                continue
            controllers[self.name + '/' + name] = mycontroller
            class_name = mycontroller.__module__ + '.' + mycontroller.__name__
            log.debug('Controller loaded; "%s" = %s' % (self.name + '/' + name, class_name))
        return controllers

    def contains_migrations(self):
        return (resource_exists(self.package_name, 'migrations') and 
            not resource_exists(self.package_name+'.migrations', 'alembic.ini'))

    def _db_default_callable(self):
        if not resource_exists(self.package_name, 'db_defaults.py'):
            return None
        defaults_module = import_module(self.package_name+'.db_defaults')
        add_default_data = getattr(defaults_module, 'add_default_data', None)
        if add_default_data is None:
            log.warn('DB defaults setup for plugin %r lacks_"add_default_data()" callable.')
        return add_default_data

def _controller_class_from_module(module, name):
    c = getattr(module, '__controller__', None)
    if c is None:
        name = name.rsplit('/', 1)[-1]
        class_name = class_name_from_module_name(name) + 'Controller'
        c = getattr(module, class_name, None)
    return c

########NEW FILE########
__FILENAME__ = abstract_class_registration_test
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code contained in this file is licensed under the GPLv3 or
# (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.

from mediadrop.lib.test.pythonic_testcase import *

from mediadrop.plugin.abc import (AbstractClass, AbstractMetaClass, 
    abstractmethod, ImplementationError)


class AbstractClassRegistrationTest(PythonicTestCase):
    class NameInterface(AbstractClass):
        @abstractmethod
        def name(self):
            pass
    
    class NameSizeInterface(NameInterface):
        @abstractmethod
        def size(self):
            pass
    
    class NameComponent(NameInterface):
        def name(self):
            return u'NameComponent'
    
    class NameSizeComponent(NameSizeInterface):
        def name(self):
            return u'NameSizeComponent'
        
        def size(self):
            return 42
    def tearDown(self):
        AbstractMetaClass._registry.clear()
    
    
    # --- tests ---------------------------------------------------------------
    
    def test_can_register_subclass(self):
        assert_length(0, list(self.NameInterface))
        
        self.NameInterface.register(self.NameComponent)
        assert_equals([self.NameComponent], list(self.NameInterface))
    
    def test_registration_checks_implementation_of_abstract_methods(self):
        class IncompleteImplementation(self.NameInterface):
            pass
        assert_raises(ImplementationError, 
                      lambda: self.NameInterface.register(IncompleteImplementation))
    
    def test_one_class_can_be_registered_for_multiple_base_classes_at_once(self):
        self.NameSizeInterface.register(self.NameSizeComponent)
        assert_equals([self.NameSizeComponent], list(self.NameInterface))
        assert_equals([self.NameSizeComponent], list(self.NameSizeInterface))
        
        self.NameInterface.register(self.NameComponent)
        assert_equals(set([self.NameComponent, self.NameSizeComponent]), 
                      set(self.NameInterface))


import unittest
def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(AbstractClassRegistrationTest))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')

########NEW FILE########
__FILENAME__ = events_test
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code contained in this file is licensed under the GPLv3 or
# (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.

from mediadrop.lib.test.pythonic_testcase import *

from mediadrop.plugin.events import Event, FetchFirstResultEvent, GeneratorEvent


class EventTest(PythonicTestCase):
    def setUp(self):
        self.observers_called = 0
        self.event = Event()
    
    def probe(self):
        self.observers_called += 1
    
    def test_can_notify_all_observers(self):
        self.event.post_observers.append(self.probe)
        self.event.pre_observers.append(self.probe)
        
        assert_equals(0, self.observers_called)
        self.event()
        assert_equals(2, self.observers_called)


class FetchFirstResultEventTest(PythonicTestCase):
    def test_returns_first_non_null_result(self):
        event = FetchFirstResultEvent([])
        event.post_observers.append(lambda: None)
        event.post_observers.append(lambda: 1)
        event.post_observers.append(lambda: 2)
        
        assert_equals(1, event())
    
    def test_passes_all_event_parameters_to_observers(self):
        event = FetchFirstResultEvent([])
        event.post_observers.append(lambda foo, bar=None: foo)
        event.post_observers.append(lambda foo, bar=None: bar or foo)
        
        assert_equals(4, event(4))
        assert_equals(6, event(None, bar=6))


class GeneratorEventTest(PythonicTestCase):
    def test_can_unroll_lists(self):
        event = GeneratorEvent([])
        event.post_observers.append(lambda: [1, 2, 3])
        event.post_observers.append(lambda: ('a', 'b'))
        
        assert_equals([1, 2, 3, 'a', 'b'], list(event()))
    
    def test_can_return_non_iterable_items(self):
        event = GeneratorEvent([])
        event.post_observers.append(lambda: [1, ])
        event.post_observers.append(lambda: None)
        event.post_observers.append(lambda: 5)
        event.post_observers.append(lambda: 'some value')
        
        assert_equals([1, None, 5, 'some value'], list(event()))



import unittest
def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(EventTest))
    suite.addTest(unittest.makeSuite(FetchFirstResultEventTest))
    suite.addTest(unittest.makeSuite(GeneratorEventTest))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')

########NEW FILE########
__FILENAME__ = observes_test
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code contained in this file is licensed under the GPLv3 or
# (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.

from mediadrop.lib.test.pythonic_testcase import *

from mediadrop.plugin.events import Event, observes


class ObserveDecoratorTest(PythonicTestCase):
    
    def test_catches_unknown_keyword_parameters_in_constructor(self):
        e = assert_raises(TypeError, lambda: observes(Event(), invalid=True))
        assert_equals("TypeError: observes() got an unexpected keyword argument 'invalid'",
                      e.args[0])
    
    def probe(self, result):
        pass
    
    def test_can_observe_event(self):
        event = Event([])
        observes(event)(self.probe)
        
        assert_length(1, event.observers)
        assert_equals(self.probe, event.observers[0])
    
    def test_observers_can_request_priority(self):
        def second_probe(result):
            pass
        event = Event([])
        observes(event)(self.probe)
        observes(event, appendleft=True)(second_probe)
        
        assert_length(2, event.observers)
        assert_equals([second_probe, self.probe], list(event.observers))


import unittest
def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(ObserveDecoratorTest))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')

########NEW FILE########
__FILENAME__ = test_admin_media
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code contained in this file is licensed under the GPLv3 or
# (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.

import os
import pylons
import simplejson
import webob.exc
from mediadrop.tests import *
from mediadrop.model import DBSession, Media, MediaFile, fetch_row
from sqlalchemy.exc import SQLAlchemyError

class TestMediaController(TestController):
    def __init__(self, *args, **kwargs):
        TestController.__init__(self, *args, **kwargs)

        # Initialize pylons.app_globals, etc. for use in main thread.
        self.response = self.app.get('/_test_vars')
        pylons.app_globals._push_object(self.response.app_globals)
        pylons.config._push_object(self.response.config)

        # So that Pylons.url can generate fully qualified URLs.
        pylons.url.environ['SERVER_NAME'] = 'test_value'
        pylons.url.environ['SERVER_PORT'] = '80'

    def _login(self):
        test_user = 'admin'
        test_password = 'admin'
        login_form_url = url(controller='login', action='login')
        # Request, and fill out, the login form.
        login_page = self.app.get(login_form_url, status=200)
        login_page.form['login'] = test_user
        login_page.form['password'] = test_password
        # Submitting the login form should redirect us to the 'post_login' page
        login_handler_page = login_page.form.submit(status=302)

    def test_index(self):
        response = self.app.get(url(controller='admin/media', action='index'))
        # Test response...

    def test_add_new_media(self):
        new_url = url(controller='admin/media', action='edit', id='new')
        save_url = url(controller='admin/media', action='save', id='new')

        title = 'Add New Media Test'
        slug = u'add-new-media-test' # this should be unique
        name = 'Frederick Awesomeson'
        email = 'fake_address@mailinator.com'
        description = 'This media item was created to test the "admin/media/edit/new" method'
        htmlized_description = '<p>This media item was created to test the &quot;admin/media/edit/new&quot; method</p>'

        self._login()
        new_response = self.app.get(new_url, status=200)
        form = new_response.forms['media-form']
        form['title'] = title
        form['author_name'] = name
        form['author_email'] = email
        form['description'] = description
        # form['categories']
        # form['tags']
        form['notes'] = ''
        assert form.action == save_url

        save_response = form.submit()

        # Ensure that the correct redirect was issued
        assert save_response.status_int == 302
        media = fetch_row(Media, slug=slug)
        edit_url = url(controller='admin/media', action='edit', id=media.id)
        assert save_response.location == 'http://localhost%s' % edit_url

        # Ensure that the media object was correctly created
        assert media.title == title
        assert media.author.name == name
        assert media.author.email == email
        assert media.description == htmlized_description

        # Ensure that the edit form is correctly filled out
        edit_response = save_response.follow()
        form = edit_response.forms['media-form']
        assert form['title'].value == title
        assert form['author_name'].value == name
        assert form['author_email'].value == email
        assert form['slug'].value == slug
        assert form['description'].value == htmlized_description
        assert form['notes'].value == ''

    def test_edit_media(self):
        title = u'Edit Existing Media Test'
        slug = u'edit-existing-media-test' # this should be unique

        # Values that we will change during the edit process
        name = u'Frederick Awesomeson'
        email = u'fake_address@mailinator.com'
        description = u'This media item was created to test the "admin/media/edit/someID" method'
        htmlized_description = '<p>This media item was created to test the &quot;admin/media/edit/someID&quot; method</p>'
        notes = u'Some Notes!'

        try:
            media = self._new_publishable_media(slug, title)
            media.publishable = False
            media.reviewed = False
            DBSession.add(media)
            DBSession.commit()
            media_id = media.id
        except SQLAlchemyError, e:
            DBSession.rollback()
            raise e

        edit_url = url(controller='admin/media', action='edit', id=media_id)
        save_url = url(controller='admin/media', action='save', id=media_id)

        # render the edit form
        self._login()
        edit_response = self.app.get(edit_url, status=200)

        # ensure the form submits like we want it to
        form = edit_response.forms['media-form']
        assert form.action == save_url

        # Fill out the edit form, and submit it
        form['title'] = title
        form['author_name'] = name
        form['author_email'] = email
        form['description'] = description
        # form['categories']
        # form['tags']
        form['notes'] = notes
        save_response = form.submit()

        # Ensure that the correct redirect was issued
        assert save_response.status_int == 302
        assert save_response.location == 'http://localhost%s' % edit_url

        # Ensure that the media object was correctly updated
        media = fetch_row(Media, media_id)
        assert media.title == title
        assert media.slug == slug
        assert media.notes == notes
        assert media.description == htmlized_description
        assert media.author.name == name
        assert media.author.email == email

    def test_add_file(self):
        slug = u'test-add-file'
        title = u'Test Adding File on Media Edit Page.'

        try:
            media = self._new_publishable_media(slug, title)
            media.publishable = False
            media.reviewed = False
            DBSession.add(media)
            DBSession.commit()
            media_id = media.id
        except SQLAlchemyError, e:
            DBSession.rollback()
            raise e

        edit_url = url(controller='admin/media', action='edit', id=media_id)
        add_url = url(controller='admin/media', action='add_file', id=media_id)
        files = [
            ('file', '/some/fake/filename.mp3', 'FILE CONTENT: This is not an MP3 file at all, but this random string will work for our purposes.')
        ]
        fields = {
            'url': '',
        }
        # render the edit form
        self._login()
        edit_response = self.app.get(edit_url, status=200)

        # Ensure that the add-file-form rendered correctly.
        form = edit_response.forms['add-file-form']
        assert form.action == add_url
        for x in fields:
            form[x] = fields[x]
        form['file'] = files[0][1]

        # Submit the form with a regular POST request anyway, because
        # webtest.Form objects can't handle file uploads.
        add_response = self.app.post(add_url, params=fields, upload_files=files)
        assert add_response.status_int == 200
        assert add_response.headers['Content-Type'] == 'application/json'

        # Ensure the media file was created properly.
        media = fetch_row(Media, slug=slug)
        assert media.files[0].container == 'mp3'
        assert media.files[0].type == 'audio'
        assert media.type == 'audio'

        # Ensure that the response content was correct.
        add_json = simplejson.loads(add_response.body)
        assert add_json['success'] == True
        assert add_json['media_id'] == media_id
        assert add_json['file_id'] == media.files[0].id
        assert 'message' not in add_json

        # Ensure that the file was properly created.
        file_uri = [u for u in media_1.files[0].get_uris() if u.scheme == 'file'][0]
        file_name = file_uri.file_uri
        file_path = os.sep.join((pylons.config['media_dir'], file_name))
        assert os.path.exists(file_path)
        file = open(file_path)
        content = file.read()
        file.close()
        assert content == files[0][2]

    def test_add_file_url(self):
        slug = u'test-add-file-url'
        title = u'Test Adding File by URL on Media Edit Page.'

        try:
            media = self._new_publishable_media(slug, title)
            media.publishable = False
            media.reviewed = False
            DBSession.add(media)
            DBSession.commit()
            media_id = media.id
        except SQLAlchemyError, e:
            DBSession.rollback()
            raise e

        edit_url = url(controller='admin/media', action='edit', id=media_id)
        add_url = url(controller='admin/media', action='add_file', id=media_id)
        fields = {
            'url': 'http://www.youtube.com/watch?v=uLTIowBF0kE',
        }
        # render the edit form
        self._login()
        edit_response = self.app.get(edit_url, status=200)

        # Ensure that the add-file-form rendered correctly.
        form = edit_response.forms['add-file-form']
        assert form.action == add_url
        for x in fields:
            form[x] = fields[x]

        # Submit the form with a regular POST request anyway, because
        # webtest.Form objects can't handle file uploads.
        add_response = self.app.post(add_url, params=fields)
        assert add_response.status_int == 200
        assert add_response.headers['Content-Type'] == 'application/json'

        # Ensure the media file was created properly.
        media = fetch_row(Media, slug=slug)
        assert media.files[0].get_uris()[0].scheme == 'youtube'
        assert media.files[0].type == 'video'
        assert media.type == 'video'

        # Ensure that the response content was correct.
        add_json = simplejson.loads(add_response.body)
        assert add_json['success'] == True
        assert add_json['media_id'] == media_id
        assert add_json['file_id'] == media.files[0].id
        assert 'message' not in add_json

    def test_merge_stubs(self):
        new_url = url(controller='admin/media', action='edit', id='new')
        save_url = url(controller='admin/media', action='save', id='new')
        add_url = url(controller='admin/media', action='add_file', id='new')

        title = 'Merge Stubs Test'
        slug = u'merge-stubs-test' # this should be unique
        name = 'Frederick Awesomeson'
        email = 'fake_address@mailinator.com'
        description = 'This media item was created to test the "admin/media/merge_stubs" method'
        htmlized_description = '<p>This media item was created to test the &quot;admin/media/merge_stubs&quot; method</p>'

        ## Log in and render the New Media page.
        self._login()
        new_response = self.app.get(new_url, status=200)

        # Make a new media object by filling out the form.
        form = new_response.forms['media-form']
        form['title'] = title
        form['author_name'] = name
        form['author_email'] = email
        form['description'] = description
        form['notes'] = ''
        assert form.action == save_url
        save_response = form.submit()
        assert save_response.status_int == 302
        media_1 = fetch_row(Media, slug=slug)
        media_1_id = media_1.id
        edit_url = url(controller='admin/media', action='edit', id=media_1.id)
        assert save_response.location == 'http://localhost%s' % edit_url

        # Make a new media object by adding a new file
        files = [
            ('file', '/some/fake/filename.mp3', 'FILE CONTENT: This is not an MP3 file at all, but this random string will work for our purposes.')
        ]
        fields = {
            'url': '',
        }
        add_response = self.app.post(add_url, params=fields, upload_files=files)
        assert add_response.status_int == 200
        assert add_response.headers['Content-Type'] == 'application/json'
        add_json = simplejson.loads(add_response.body)
        assert add_json['success'] == True
        assert 'message' not in add_json
        media_2_id = add_json['media_id']
        file_2_id = add_json['file_id']

        # Assert that the stub file was named properly.
        file_2 = fetch_row(MediaFile, file_2_id)
        file_2_uri = [u for u in file_2.get_uris() if u.scheme == 'file'][0]
        file_2_basename = os.path.basename(file_2_uri.file_uri)
        assert file_2_basename.startswith('%d_%d_' % (media_2_id, file_2_id))
        assert file_2_basename.endswith('.mp3')

        # Merge the objects!
        merge_url = url(controller='admin/media', action='merge_stubs', orig_id=media_1_id, input_id=media_2_id)
        merge_response = self.app.get(merge_url)
        merge_json = simplejson.loads(merge_response.body)
        assert merge_json['success'] == True
        assert merge_json['media_id'] == media_1_id

        # Ensure that the correct objects were created/destroyed
        try:
            media_2 = fetch_row(Media, media_2_id)
            raise Exception('Stub media object not properly deleted!')
        except webob.exc.HTTPException, e:
            if e.code != 404:
                raise

        media_1 = fetch_row(Media, media_1_id)
        file_1 = media_1.files[0]

        # Ensure that the file was correctly renamed and has the right content.
        assert media_1.type == 'audio'
        assert file_1.type == 'audio'
        assert file_1.container == 'mp3'
        file_uri = [u for u in file_1.get_uris() if u.scheme == 'file'][0]
        file_path = file_uri.file_uri[len("file://"):]
        base_name = os.path.basename(file_path)
        expected_base_name = '%d_%d_%s.%s' % (media_1.id, file_1.id, media_1.slug, file_1.container)
        assert base_name == expected_base_name, "Got basename %s, but expected %s" % (base_name, expected_base_name)
        assert os.path.exists(file_path)
        file = open(file_path)
        content = file.read()
        file.close()
        assert content == files[0][2]

########NEW FILE########
__FILENAME__ = test_login
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code contained in this file is licensed under the GPLv3 or
# (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.

from mediadrop.tests import *

test_user = 'admin'
test_password = 'admin'
local = 'http://localhost%s'

# TODO: Determine why test_voluntary_login_and_logout needs this value
#       instead of simply localhost with no port, as with test_forced_login.
local_with_port = 'http://localhost:80%s'

class TestLoginController(TestController):

    def test_forced_login(self):
        """
        Anonymous users should be redirected to the login form when they
        request a protected area.
        """
        restricted_url = url(controller='admin', action='index')
        login_form_url = url(controller='login', action='login')
        post_login_url = url(controller='login', action='post_login')

        # Requesting a protected area as anonymous should redirect to the
        # login form page
        restricted_page = self.app.get(restricted_url, status=302)

        assert restricted_page.location.startswith(local % login_form_url), \
            "Restricted page is redirecting to %s, but %s... was expected." % (
                restricted_page.location, local % login_form_url)

        # Follow the redirect to the login page and fill out the login form.
        login_page = restricted_page.follow(status=200)
        login_page.form['login'] = test_user
        login_page.form['password'] = test_password

        # Submitting the login form should redirect us to the 'post_login' page
        # TODO: Figure out why this post_login page is necessary, or at least why
        #       it's not mentioned in the repoze.who-testutil docs.
        login_handler_page = login_page.form.submit(status=302)

        assert login_handler_page.location.startswith(local % post_login_url), \
            "Login handler is redirecting to %s, but %s... was expected." % (
                login_handler_page.location, local % post_login_url)

        # The post_login page should set up our authentication cookies
        # and redirect to the initially requested page.
        post_login_handler_page = login_handler_page.follow(status=302)

        assert post_login_handler_page.location == local % restricted_url, \
            "Post-login handler is redirecting to %s, but %s was expected." % (
                post_login_handler_page.location, local % restricted_url)

        assert 'authtkt' in post_login_handler_page.request.cookies, \
           "Session cookie wasn't defined: %s" % (
                post_login_handler_page.request.cookies)

        # Follow the redirect to check that we were correctly authenticated:
        initial_page = post_login_handler_page.follow(status=200)

    def test_voluntary_login_and_logout(self):
        """
        Voluntary logins should redirect to the main admin page on
        success. Logout should redirect to the main / page.
        """
        admin_url = restricted_url = url(controller='admin', action='index')
        login_form_url = url(controller='login', action='login')
        post_login_url = url(controller='login', action='post_login')
        logout_handler_url = url(controller='login', action='logout_handler')
        post_logout_url = url(controller='login', action='post_logout')
        home_url = url('/')

        # Request, and fill out, the login form.
        login_page = self.app.get(login_form_url, status=200)
        login_page.form['login'] = test_user
        login_page.form['password'] = test_password

        # Submitting the login form should redirect us to the 'post_login' page
        login_handler_page = login_page.form.submit(status=302)

        assert login_handler_page.location.startswith(local % post_login_url), \
            "Login handler is redirecting to %s, but %s... was expected." % (
                login_handler_page.location, local % post_login_url)

        # The post_login page should set up our authentication cookies
        # and redirect to the initially requested page.
        post_login_handler_page = login_handler_page.follow(status=302)

        assert post_login_handler_page.location == local_with_port % admin_url, \
            "Post-login handler is redirecting to %s, but %s was expected." % (
                post_login_handler_page.location, local % restricted_url)

        assert 'authtkt' in post_login_handler_page.request.cookies, \
               "Session cookie wasn't defined: %s" % post_login_handler_page.request.cookies

        # Follow the redirect to check that we were correctly authenticated:
        admin_page = post_login_handler_page.follow(status=200)

        # Now 'click' the logout link.
        # This sends all relevant cookies, and ensures that the logout link is
        # actually displayed on the admin page.
        logout_handler_page = admin_page.click(linkid='logout', href=logout_handler_url)

        assert logout_handler_page.location.startswith(local % post_logout_url), \
            "Logout handler is redirecting to %s, but %s... was expected." % (
                login_handler_page.location, local % post_logout_url)

        # Follow the first logout redirect.
        # This should invalidate our authtkt cookie.
        post_logout_page = logout_handler_page.follow(status=302)

        assert post_logout_page.location == local % home_url, \
            "Post-login handler is redirecting to %s, but %s was expected." % (
                post_login_handler_page.location, local % home_url)

        assert post_logout_page.request.cookies['authtkt'] == 'INVALID', \
            "Post-login handler did not set 'authtkt' cookie to 'INVALID'"

        # Follow the final logout redirect, back to the home page.
        home_page = post_logout_page.follow(status=200)

########NEW FILE########
__FILENAME__ = limit_feed_items_validator
# -*- coding: utf-8 -*-
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code contained in this file is licensed under the GPLv3 or
# (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.

from formencode.validators import Int
from pylons import request


__all__ = ['LimitFeedItemsValidator']

class LimitFeedItemsValidator(Int):
    min = 1
    
    def empty_value(self, value):
        return self.default_limit(request.settings)
    
    @property
    def if_missing(self):
        return self.default_limit(request.settings)
    
    @property
    def if_invalid(self):
        return self.default_limit(request.settings)
    
    def default_limit(self, settings):
        default_feed_results = settings.get('default_feed_results')
        if default_feed_results in ('', '-1'):
            return None
        elif default_feed_results is None:
            return 30
        return int(default_feed_results)

########NEW FILE########
__FILENAME__ = limit_feed_items_validator_test
# -*- coding: utf-8 -*-
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code contained in this file is licensed under the GPLv3 or
# (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.

from formencode.schema import Schema
from pylons import app_globals

from mediadrop.lib.test import *
from mediadrop.validation import LimitFeedItemsValidator


__all__ = ['LimitFeedItemsValidator']

class LimitFeedItemsValidatorTest(DBTestCase, RequestMixin):
    def setUp(self):
        super(LimitFeedItemsValidatorTest, self).setUp()
        self.init_fake_request()
        # just to be sure all settings have been cleared.
        assert_none(app_globals.settings.get('default_feed_results'))
        app_globals.settings['default_feed_results'] = 42
        self.validator = LimitFeedItemsValidator()
    
    def tearDown(self):
        self.remove_globals()
        super(LimitFeedItemsValidatorTest, self).tearDown()
    
    def to_python(self, value):
        return self.validator.to_python(value)
    
    def test_specified_value_overrides_default(self):
        assert_equals(12, self.to_python('12'))
    
    def test_returns_default_for_empty_items(self):
        assert_equals(42, self.to_python(''))
        assert_equals(42, self.to_python(None))
    
    def test_can_return_unlimited_items(self):
        app_globals.settings['default_feed_results'] = ''
        assert_none(self.to_python(''))
        
        app_globals.settings['default_feed_results'] = '-1'
        assert_none(self.to_python(''))
    
    def test_ignores_missing_setting(self):
        del app_globals.settings['default_feed_results']
        assert_equals(30, self.to_python(''))
    
    def test_returns_default_number_for_invalid_input(self):
        assert_equals(42, self.to_python('invalid'))
        assert_equals(42, self.to_python(-1))
    
    def test_returns_default_for_missing_items(self):
        schema = Schema()
        schema.add_field('limit', self.validator)
        assert_equals(dict(limit=42), schema.to_python({}))



def suite():
    import unittest
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(LimitFeedItemsValidatorTest))
    return suite


########NEW FILE########
__FILENAME__ = uri_validator_test
# -*- coding: utf-8 -*-
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code contained in this file is licensed under the GPLv3 or
# (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.

from formencode.api import Invalid

from mediadrop.lib.test import *
from mediadrop.validation import URIValidator


__all__ = ['URIValidatorTest']

class URIValidatorTest(DBTestCase, RequestMixin):
    def setUp(self):
        super(URIValidatorTest, self).setUp()
        # set's up pylons.translator
        self.init_fake_request()
        self.validator = URIValidator()
    
    def tearDown(self):
        self.remove_globals()
        super(URIValidatorTest, self).tearDown()
    
    def to_python(self, value):
        return self.validator.to_python(value)
    
    def test_accepts_http_url(self):
        url = u'http://site.example/foo/video.ogv'
        assert_equals(url, self.to_python(url))
    
    def test_accepts_rtmp_url(self):
        url = u'rtmp://site.example/foo/video.ogv'
        assert_equals(url, self.to_python(url))
    
    def assert_invalid(self, value):
        return assert_raises(Invalid, lambda: self.to_python(value))
    
    def test_rejects_invalid_url(self):
        self.assert_invalid(u'invalid')
        self.assert_invalid(u'http://?foo=bar')
        # important to check details of the Python 2.4 urlsplit workaround
        self.assert_invalid(u'rtmp://')
        self.assert_invalid(u'rtmp:')


def suite():
    import unittest
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(URIValidatorTest))
    return suite


########NEW FILE########
__FILENAME__ = uri_validator
# -*- coding: utf-8 -*-
# This file is a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code contained in this file is licensed under the GPLv3 or
# (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.

from urlparse import urlsplit

from formencode.validators import UnicodeString
from formencode.api import Invalid

from mediadrop.lib.i18n import _


__all__ = ['URIValidator']

class URIValidator(UnicodeString):
    def raise_error_bad_url(self, value, state):
        msg = _('That is not a valid URL.')
        raise Invalid(msg, value, state)
    
    def validate_python(self, value, state):
        try:
            splitted_url = urlsplit(value)
        except:
            self.raise_error_bad_url(value, state)
        scheme = splitted_url[0] # '.scheme' in Python 2.5+
        netloc = splitted_url[1] # '.netloc' in Python 2.5+
        path = splitted_url[2] # '.path' in Python 2.5+
        # Python 2.4 does not fill netloc when parsing urls with unknown
        # schemes (e.g. 'rtmp://')
        netloc_given = (len(netloc) > 0) or (path.startswith('//') and path != '//')
        if (scheme == '') or not netloc_given:
            self.raise_error_bad_url(value, state)


########NEW FILE########
