__FILENAME__ = api
import json
import argparse
import regex
import bottle
from bottle import request, response
import xmltodict
import traceback

from pynab import log
import pynab.api
import config

app = application = bottle.Bottle()

#bottle.debug(True)

@app.get('/scripts/:path#.+#')
def serve_static(path):
    return bottle.static_file(path, root='./webui/dist/scripts/')


@app.get('/styles/:path#.+#')
def serve_static(path):
    return bottle.static_file(path, root='./webui/dist/styles/')


@app.get('/views/:path#.+#')
def serve_static(path):
    return bottle.static_file(path, root='./webui/dist/views/')


@app.get('/fonts/:path#.+#')
def serve_static(path):
    return bottle.static_file(path, root='./webui/dist/fonts/')


@app.get('/bower_components/:path#.+#')
def serve_static(path):
    return bottle.static_file(path, root='./webui/dist/bower_components/')


@app.get('/api')
def api():
    log.debug('Handling request for {0}.'.format(request.fullpath))

    # these are really basic, don't check much
    function = request.query.t or pynab.api.api_error(200)

    for r, func in pynab.api.functions.items():
        # reform s|search into ^s$|^search$
        # if we don't, 's' matches 'caps' (s)
        r = '|'.join(['^{0}$'.format(r) for r in r.split('|')])
        if regex.search(r, function):
            dataset = dict()
            dataset['get_link'] = get_link
            data = func(dataset)
            return switch_output(data)

    # didn't match any functions
    return pynab.api.api_error(202)


@app.get('/')
@app.get('/index.html')
def index():
    if config.api.get('webui'): # disabled by default ? not really useful for a single user install
        raise bottle.static_file('index.html', root='./webui/dist')


@app.get('/favicon.ico')
def index():
    if config.api.get('webui'):
        raise bottle.static_file('favicon.ico', root='./webui/dist')


def switch_output(data):
    output_format = request.query.o or 'xml'
    output_callback = request.query.callback or None

    if output_format == 'xml':
        # return as xml
        response.set_header('Content-type', 'application/rss+xml')
        return data
    elif output_format == 'json':
        if output_callback:
            response.content_type = 'application/javascript'
            return '{}({})'.format(output_callback, json.dumps(xmltodict.parse(data, attr_prefix='')))
        else:
            # bottle auto-converts a python dict into json
            return xmltodict.parse(data, attr_prefix='')
    else:
        return pynab.api.api_error(201)


def get_link(route=''):
    """Gets a link (including domain/subdirs) to a route."""
    url = request.environ['wsgi.url_scheme'] + '://'

    if request.environ.get('HTTP_HOST'):
        url += request.environ['HTTP_HOST']
    else:
        url += request.environ['SERVER_NAME']

        if request.environ['wsgi.url_scheme'] == 'https':
            if request.environ['SERVER_PORT'] != '443':
                url += ':' + request.environ['SERVER_PORT']
        else:
            if request.environ['SERVER_PORT'] != '80':
                url += ':' + request.environ['SERVER_PORT']

    if route:
        url += route

    return url


def daemonize(pidfile):
    try:
        import traceback
        from daemonize import Daemonize
        daemon = Daemonize(app='pynab', pid=pidfile, action=main)
        daemon.start()
    except SystemExit:
        raise
    except:
        log.critical(traceback.format_exc())


def main():
    bottle.run(app=app, host=config.api.get('api_host', '0.0.0.0'), port=config.api.get('api_port', 8080))
    

if __name__ == '__main__':
    argparser = argparse.ArgumentParser(description="Pynab main indexer script")
    argparser.add_argument('-d', '--daemonize', action='store_true', help='run as a daemon')
    argparser.add_argument('-p', '--pid-file', help='pid file (when -d)')

    args = argparser.parse_args()

    if args.daemonize:
        pidfile = args.pid_file or config.api.get('api_pid_file')
        if not pidfile:
            log.error("A pid file is required to run as a daemon, please supply one either in the config file '{}' or as argument".format(config.__file__))
        else:
            daemonize(pidfile)
    else:
        main()

########NEW FILE########
__FILENAME__ = config.sample
import logging

api = {
    # api settings
    # ---------------------

    # title: shows on the rss feed, can be whatever
    'title': 'pynab',

    # description: same deal
    'description': 'a pynab api',

    # don't edit this
    'version': '1.0.0',

    # generally leave this alone too
    'api_version': '0.2.3',

    # your administrator email (shows on rss feed)
    'email': '',

    # enable web interface
    'webui': True,

    # result_limit: maximum search results for rss feeds
    # make sure there's no quotes around it
    'result_limit': 100,

    # result_default: default number if none is specified
    # make sure there's no quotes around it
    'result_default': 20,
    
    # api_host: ip or hostname to bind the api
    # usually '0.0.0.0'
    'api_host': '0.0.0.0',

    # api_port: port number to bind the api
    # usually 8080
    'api_port': 8080,

    # pid_file: process file for the api, if daemonized
    # make sure it's writable, leave blank for nginx
    'pid_file': ''
}

scan = {
    # scanning settings
    # -----------------

    # update_threads: number of processes to spawn for updating
    # realistically, should be the number of cpu cores you have
    # make sure there's no quotes around it
    'update_threads': 4,

    # update_wait: amount of time to wait between update cycles
    # in seconds
    'update_wait': 300,

    # new_group_scan_days: how many days to scan for a new group
    # make sure there's no quotes around it
    'new_group_scan_days': 5,

    # message_scan_limit: number of messages to take from nntp server at once
    # make sure there's no quotes around it
    'message_scan_limit': 20000,

    # backfill_days: number of days to backfill groups (using backfill)
    # make sure there's no quotes around it
    'backfill_days': 10,

    # dead_binary_age: number of days to keep binaries for matching
    # realistically if they're not completed after a day or two, they're not going to be
    # set this to 3 days or so, don't set it to 0
    'dead_binary_age': 3,

    # pid_file: process file for the scanner, if daemonized
    # make sure it's writable, leave blank for nginx
    'pid_file': ''

}

postprocess = {
    # release processing settings
    # ---------------------------

    # min_archives: the minimum number of archives in a binary to form a release
    # setting this to 1 will cut out releases that only contain an nzb, etc.
    'min_archives': 1,

    # min_completion: the minimum completion % that a release should satisfy
    # if it's lower than this, it'll get removed eventually
    # it'll only create releases of this completion if 3 hours have passed to make sure
    # we're not accidentally cutting off the end of a new release
    'min_completion': 99,

    # 100% completion resulted in about 11,000 unmatched releases after 4 weeks over 6 groups
    # lowering that to 99% built an extra 3,500 releases

    # postprocess_wait: time to sleep between postprocess.py loops
    # setting this to 0 may be horrible to online APIs, but if you've got a good
    # local db it should be fine
    'postprocess_wait': 0,

    # process_rars: whether to check for passworded releases, get file size and count
    # this uses extra bandwidth, since it needs to download at least one archive
    # for something like a bluray release, this is quite large
    'process_rars': True,

    # unrar_path: path to unrar binary
    # for windows, this'll be wherever you installed it to
    # for linux, probably just /usr/bin/unrar
    # if windows, make sure to escape slashes, ie.
    # 'C:\\Program Files (x86)\\Unrar\\Unrar.exe'
    'unrar_path': '',

    # delete_passworded: delete releases that are passworded
    'delete_passworded': True,

    # delete_potentially_passworded: delete releases that are probably passworded
    'delete_potentially_passworded': True,

    # delete_bad_releases: delete releases that we can't rename out of misc-other
    'delete_bad_releases': True,

    # process_imdb: match movie releases against IMDB
    # couchpotato sometimes depends on this data for API usage, definitely recommended
    'process_imdb': True,

    # process_tvrage: match TV releases against TVRage
    # sickbeard sometimes depends on this data for API usage, definitely recommended
    'process_tvrage': True,

    # process_nfos: grab NFOs for releases for other use
    # this can be used to clean release names, etc
    'process_nfos': True,

    # fetch_blacklist_duration: the number of days between tvrage/imdb API attempts
    # so if we can't find a match for some movie, wait 7 days before trying that movie again
    # there's really no benefit to setting this low - anywhere from a week to several months is fine
    'fetch_blacklist_duration': 7,
    
    # regex update settings
    # ---------------------

    # regex_url: url to retrieve regex updates from
    # this can be newznab's if you bought plus, include your id, ie.
    # expects data in newznab sql dump format
    # 'http://www.newznab.com/getregex.php?newznabID=<id>'
    'regex_url': '',

    # blacklist_url: url to retrieve blacklists from
    # generally leave alone
    'blacklist_url': 'https://raw.github.com/kevinlekiller/Newznab-Blacklist/master/New/blacklists.txt',

}

log = {
    # logging settings
    # ----------------
    # logging_file: a filepath or None to go to stdout
    'logging_file': None,

    # logging.x where DEBUG, INFO, WARNING, ERROR, etc
    # generally, debug if something goes wrong, info for normal usage
    'logging_level': logging.DEBUG,

    # max_log_size: maximum size of logfiles before they get rotated
    # number, in bytes (this is 50mb)
    'max_log_size': 50*1024*1024,
    
}

# mongodb config
db = {
    # hostname: usually 'localhost'
    'host': '',

    # port: default is 27017
    # make sure there's no quotes around it
    'port': 27017,

    # user: username, if auth is enabled
    'user': '',

    # pass: password, likewise
    'pass': '',

    # db: database name in mongo
    # pick whatever you want, it'll autocreate it
    'db': 'pynab',
}

# usenet server details
news = {
    # host: your usenet server host ('news.supernews.com' or the like)
    'host': '',

    # user: whatever your login name is
    'user': '',

    # password: your password
    'password': '',

    # port: port that your news server runs on
    # make sure there aren't any quotes around it
    'port': 443,

    # ssl: True if you want to use SSL, False if not
    'ssl': True,
}

# only used for convert_from_newznab.py
# you can probably leave this blank unless you know what you're doing
mysql = {
    'host': '',
    'port': 3306,
    'user': '',
    'passwd': '',
    'db': 'newznab',
}

########NEW FILE########
__FILENAME__ = conf
#!/usr/bin/env python
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

# Get the project root dir, which is the parent dir of this
cwd = os.getcwd()
project_root = os.path.dirname(cwd)

# Insert the project root dir as the first element in the PYTHONPATH.
# This lets us ensure that the source package is imported, and that its
# version is used.
sys.path.insert(0, project_root)

import pynab

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
project = u'pynab'
copyright = u'2013, James Meneghello'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = pynab.__version__
# The full version, including alpha/beta/rc tags.
release = pynab.__version__

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
htmlhelp_basename = 'pynabdoc'


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
  ('index', 'pynab.tex', u'pynab Documentation',
   u'James Meneghello', 'manual'),
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
    ('index', 'pynab', u'pynab Documentation',
     [u'James Meneghello'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'pynab', u'pynab Documentation',
   u'James Meneghello', 'pynab', 'One line description of project.',
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
__FILENAME__ = install
import sys
import json

if __name__ == '__main__':
    print('Welcome to Pynab.')
    print('-----------------')
    print()
    print('Please ensure that you have copied and renamed config.sample.py to config.py before proceeding.')
    print(
        'You need to put in your details, too. If you are migrating from Newznab, check out scripts/convert_from_newznab.py first.')
    print()
    print('This script is destructive. Ensure that the database credentials and settings are correct.')
    print('The supplied database really should be empty, but it\'ll just drop anything it wants to overwrite.')
    print()
    input('To continue, press enter. To exit, press ctrl-c.')

    try:
        import config
        from pynab.db import db
        import pynab.util
        import scripts.ensure_indexes
    except ImportError:
        print('Could not load config.py.')
        sys.exit(0)

    print('Copying users into Mongo...')
    with open('db/initial/users.json', encoding='utf-8', errors='ignore') as f:
        data = json.load(f)
        try:
            db.users.drop()
            db.users.insert(data)
        except:
            print('Problem inserting data into MongoDB.')
            sys.exit(0)

    print('Copying groups into Mongo...')
    with open('db/initial/groups.json', encoding='utf-8', errors='ignore') as f:
        data = json.load(f)
        try:
            db.groups.drop()
            db.groups.insert(data)
        except:
            print('Problem inserting data into MongoDB.')
            sys.exit(0)

    print('Copying categories into Mongo...')
    with open('db/initial/categories.json', encoding='utf-8', errors='ignore') as f:
        data = json.load(f)
        try:
            db.categories.drop()
            db.categories.insert(data)
        except:
            print('Problem inserting data into MongoDB.')
            sys.exit(0)

    print('Copying tvrage into Mongo...')
    with open('db/initial/tvrage.json', encoding='utf-8', errors='ignore') as f:
        data = json.load(f)
        try:
            db.tvrage.drop()
            db.tvrage.insert(data)
        except:
            print('Problem inserting data into MongoDB.')
            sys.exit(0)

    print('Copying imdb into Mongo...')
    with open('db/initial/imdb.json', encoding='utf-8', errors='ignore') as f:
        data = json.load(f)
        try:
            db.imdb.drop()
            db.imdb.insert(data)
        except:
            print('Problem inserting data into MongoDB.')
            sys.exit(0)

    print('Copying tvdb into Mongo...')
    with open('db/initial/tvdb.json', encoding='utf-8', errors='ignore') as f:
        data = json.load(f)
        try:
            db.tvdb.drop()
            db.tvdb.insert(data)
        except:
            print('Problem inserting data into MongoDB.')
            sys.exit(0)

    if config.postprocess.get('regex_url'):
        print('Updating regex...')
        pynab.util.update_regex()
    else:
        print('Could not update regex - no update url/key in config.py.')
        print('If you don\'t have one, buy a Newznab+ license or find your own regexes.')
        print('You won\'t be able to build releases without appropriate regexes.')

    if config.postprocess.get('blacklist_url'):
        print('Updating binary blacklist...')
        pynab.util.update_blacklist()
    else:
        print(
            'Could not update blacklist. Try the URL in config.py manually - if it doesn\'t work, post an issue on Github.')

    print('Creating indexes on collections...')
    scripts.ensure_indexes.create_indexes()

    print('Install theoretically completed - the rest of the collections will be made as they\'re needed.')
    print('Now: activate some groups, activate desired blacklists, and run start.py with python3.')

########NEW FILE########
__FILENAME__ = nntplib
"""An NNTP client class based on:
- RFC 977: Network News Transfer Protocol
- RFC 2980: Common NNTP Extensions
- RFC 3977: Network News Transfer Protocol (version 2)

Example:

>>> from nntplib import NNTP
>>> s = NNTP('news')
>>> resp, count, first, last, name = s.group('comp.lang.python')
>>> print('Group', name, 'has', count, 'articles, range', first, 'to', last)
Group comp.lang.python has 51 articles, range 5770 to 5821
>>> resp, subs = s.xhdr('subject', '{0}-{1}'.format(first, last))
>>> resp = s.quit()
>>>

Here 'resp' is the server response line.
Error responses are turned into exceptions.

To post an article from a file:
>>> f = open(filename, 'rb') # file containing article, including header
>>> resp = s.post(f)
>>>

For descriptions of all methods, read the comments in the code below.
Note that all arguments and return values representing article numbers
are strings, not numbers, since they are rarely used for calculations.
"""

# RFC 977 by Brian Kantor and Phil Lapsley.
# xover, xgtitle, xpath, date methods by Kevan Heydon

# Incompatible changes from the 2.x nntplib:
# - all commands are encoded as UTF-8 data (using the "surrogateescape"
#   error handler), except for raw message data (POST, IHAVE)
# - all responses are decoded as UTF-8 data (using the "surrogateescape"
#   error handler), except for raw message data (ARTICLE, HEAD, BODY)
# - the `file` argument to various methods is keyword-only
#
# - NNTP.date() returns a datetime object
# - NNTP.newgroups() and NNTP.newnews() take a datetime (or date) object,
#   rather than a pair of (date, time) strings.
# - NNTP.newgroups() and NNTP.list() return a list of GroupInfo named tuples
# - NNTP.descriptions() returns a dict mapping group names to descriptions
# - NNTP.xover() returns a list of dicts mapping field names (header or metadata)
#   to field values; each dict representing a message overview.
# - NNTP.article(), NNTP.head() and NNTP.body() return a (response, ArticleInfo)
#   tuple.
# - the "internal" methods have been marked private (they now start with
#   an underscore)

# Other changes from the 2.x/3.1 nntplib:
# - automatic querying of capabilities at connect
# - New method NNTP.getcapabilities()
# - New method NNTP.over()
# - New helper function decode_header()
# - NNTP.post() and NNTP.ihave() accept file objects, bytes-like objects and
#   arbitrary iterables yielding lines.
# - An extensive test suite :-)

# TODO:
# - return structured data (GroupInfo etc.) everywhere
# - support HDR

# Imports
import regex
import socket
import collections
import datetime
import warnings
import zlib

try:
    import ssl
except ImportError:
    _have_ssl = False
else:
    _have_ssl = True

from email.header import decode_header as _email_decode_header
from socket import _GLOBAL_DEFAULT_TIMEOUT

__all__ = ["NNTP",
           "NNTPReplyError", "NNTPTemporaryError", "NNTPPermanentError",
           "NNTPProtocolError", "NNTPDataError",
           "decode_header",
           ]

# Exceptions raised when an error or invalid response is received
class NNTPError(Exception):
    """Base class for all nntplib exceptions"""
    def __init__(self, *args):
        Exception.__init__(self, *args)
        try:
            self.response = args[0]
        except IndexError:
            self.response = 'No response given'

class NNTPReplyError(NNTPError):
    """Unexpected [123]xx reply"""
    pass

class NNTPTemporaryError(NNTPError):
    """4xx errors"""
    pass

class NNTPPermanentError(NNTPError):
    """5xx errors"""
    pass

class NNTPProtocolError(NNTPError):
    """Response does not begin with [1-5]"""
    pass

class NNTPDataError(NNTPError):
    """Error in response data"""
    pass


# Standard port used by NNTP servers
NNTP_PORT = 119
NNTP_SSL_PORT = 563

# Response numbers that are followed by additional text (e.g. article)
_LONGRESP = {
    '100',   # HELP
    '101',   # CAPABILITIES
    '211',   # LISTGROUP   (also not multi-line with GROUP)
    '215',   # LIST
    '220',   # ARTICLE
    '221',   # HEAD, XHDR
    '222',   # BODY
    '224',   # OVER, XOVER
    '225',   # HDR
    '230',   # NEWNEWS
    '231',   # NEWGROUPS
    '282',   # XGTITLE
}

# Default decoded value for LIST OVERVIEW.FMT if not supported
_DEFAULT_OVERVIEW_FMT = [
    "subject", "from", "date", "message-id", "references", ":bytes", ":lines"]

# Alternative names allowed in LIST OVERVIEW.FMT response
_OVERVIEW_FMT_ALTERNATIVES = {
    'bytes': ':bytes',
    'lines': ':lines',
}

# Line terminators (we always output CRLF, but accept any of CRLF, CR, LF)
_CRLF = b'\r\n'

GroupInfo = collections.namedtuple('GroupInfo',
                                   ['group', 'last', 'first', 'flag'])

ArticleInfo = collections.namedtuple('ArticleInfo',
                                     ['number', 'message_id', 'lines'])


# Helper function(s)
def decode_header(header_str):
    """Takes an unicode string representing a munged header value
    and decodes it as a (possibly non-ASCII) readable value."""
    parts = []
    for v, enc in _email_decode_header(header_str):
        if isinstance(v, bytes):
            parts.append(v.decode(enc or 'ascii'))
        else:
            parts.append(v)
    return ''.join(parts)

def _parse_overview_fmt(lines):
    """Parse a list of string representing the response to LIST OVERVIEW.FMT
    and return a list of header/metadata names.
    Raises NNTPDataError if the response is not compliant
    (cf. RFC 3977, section 8.4)."""
    fmt = []
    for line in lines:
        if line[0] == ':':
            # Metadata name (e.g. ":bytes")
            name, _, suffix = line[1:].partition(':')
            name = ':' + name
        else:
            # Header name (e.g. "Subject:" or "Xref:full")
            name, _, suffix = line.partition(':')
        name = name.lower()
        name = _OVERVIEW_FMT_ALTERNATIVES.get(name, name)
        # Should we do something with the suffix?
        fmt.append(name)
    defaults = _DEFAULT_OVERVIEW_FMT
    if len(fmt) < len(defaults):
        raise NNTPDataError("LIST OVERVIEW.FMT response too short")
    if fmt[:len(defaults)] != defaults:
        raise NNTPDataError("LIST OVERVIEW.FMT redefines default fields")
    return fmt

def _parse_overview(lines, fmt, data_process_func=None):
    """Parse the response to a OVER or XOVER command according to the
    overview format `fmt`."""
    n_defaults = len(_DEFAULT_OVERVIEW_FMT)
    overview = []
    for line in lines:
        fields = {}
        article_number, *tokens = line.split('\t')
        article_number = int(article_number)
        for i, token in enumerate(tokens):
            if i >= len(fmt):
                # XXX should we raise an error? Some servers might not
                # support LIST OVERVIEW.FMT and still return additional
                # headers.
                continue
            field_name = fmt[i]
            is_metadata = field_name.startswith(':')
            if i >= n_defaults and not is_metadata:
                # Non-default header names are included in full in the response
                # (unless the field is totally empty)
                h = field_name + ": "
                if token and token[:len(h)].lower() != h:
                    raise NNTPDataError("OVER/XOVER response doesn't include "
                                        "names of additional headers")
                token = token[len(h):] if token else None
            fields[fmt[i]] = token
        overview.append((article_number, fields))
    return overview

def _parse_datetime(date_str, time_str=None):
    """Parse a pair of (date, time) strings, and return a datetime object.
    If only the date is given, it is assumed to be date and time
    concatenated together (e.g. response to the DATE command).
    """
    if time_str is None:
        time_str = date_str[-6:]
        date_str = date_str[:-6]
    hours = int(time_str[:2])
    minutes = int(time_str[2:4])
    seconds = int(time_str[4:])
    year = int(date_str[:-4])
    month = int(date_str[-4:-2])
    day = int(date_str[-2:])
    # RFC 3977 doesn't say how to interpret 2-char years.  Assume that
    # there are no dates before 1970 on Usenet.
    if year < 70:
        year += 2000
    elif year < 100:
        year += 1900
    return datetime.datetime(year, month, day, hours, minutes, seconds)

def _unparse_datetime(dt, legacy=False):
    """Format a date or datetime object as a pair of (date, time) strings
    in the format required by the NEWNEWS and NEWGROUPS commands.  If a
    date object is passed, the time is assumed to be midnight (00h00).

    The returned representation depends on the legacy flag:
    * if legacy is False (the default):
      date has the YYYYMMDD format and time the HHMMSS format
    * if legacy is True:
      date has the YYMMDD format and time the HHMMSS format.
    RFC 3977 compliant servers should understand both formats; therefore,
    legacy is only needed when talking to old servers.
    """
    if not isinstance(dt, datetime.datetime):
        time_str = "000000"
    else:
        time_str = "{0.hour:02d}{0.minute:02d}{0.second:02d}".format(dt)
    y = dt.year
    if legacy:
        y = y % 100
        date_str = "{0:02d}{1.month:02d}{1.day:02d}".format(y, dt)
    else:
        date_str = "{0:04d}{1.month:02d}{1.day:02d}".format(y, dt)
    return date_str, time_str


if _have_ssl:

    def _encrypt_on(sock, context):
        """Wrap a socket in SSL/TLS. Arguments:
        - sock: Socket to wrap
        - context: SSL context to use for the encrypted connection
        Returns:
        - sock: New, encrypted socket.
        """
        # Generate a default SSL context if none was passed.
        if context is None:
            context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
            # SSLv2 considered harmful.
            context.options |= ssl.OP_NO_SSLv2
        return context.wrap_socket(sock)


# The classes themselves
class _NNTPBase:
    # UTF-8 is the character set for all NNTP commands and responses: they
    # are automatically encoded (when sending) and decoded (and receiving)
    # by this class.
    # However, some multi-line data blocks can contain arbitrary bytes (for
    # example, latin-1 or utf-16 data in the body of a message). Commands
    # taking (POST, IHAVE) or returning (HEAD, BODY, ARTICLE) raw message
    # data will therefore only accept and produce bytes objects.
    # Furthermore, since there could be non-compliant servers out there,
    # we use 'surrogateescape' as the error handler for fault tolerance
    # and easy round-tripping. This could be useful for some applications
    # (e.g. NNTP gateways).

    encoding = 'utf-8'
    errors = 'surrogateescape'

    def __init__(self, file, host,
                 readermode=None, timeout=_GLOBAL_DEFAULT_TIMEOUT):
        """Initialize an instance.  Arguments:
        - file: file-like object (open for read/write in binary mode)
        - host: hostname of the server
        - readermode: if true, send 'mode reader' command after
                      connecting.
        - timeout: timeout (in seconds) used for socket connections

        readermode is sometimes necessary if you are connecting to an
        NNTP server on the local machine and intend to call
        reader-specific commands, such as `group'.  If you get
        unexpected NNTPPermanentErrors, you might need to set
        readermode.
        """
        self.host = host
        self.file = file
        self.debugging = 0
        self.welcome = self._getresp()

        # Inquire about capabilities (RFC 3977).
        self._caps = None
        self.getcapabilities()

        # 'MODE READER' is sometimes necessary to enable 'reader' mode.
        # However, the order in which 'MODE READER' and 'AUTHINFO' need to
        # arrive differs between some NNTP servers. If _setreadermode() fails
        # with an authorization failed error, it will set this to True;
        # the login() routine will interpret that as a request to try again
        # after performing its normal function.
        # Enable only if we're not already in READER mode anyway.
        self.readermode_afterauth = False
        if readermode and 'READER' not in self._caps:
            self._setreadermode()
            if not self.readermode_afterauth:
                # Capabilities might have changed after MODE READER
                self._caps = None
                self.getcapabilities()

        # RFC 4642 2.2.2: Both the client and the server MUST know if there is
        # a TLS session active.  A client MUST NOT attempt to start a TLS
        # session if a TLS session is already active.
        self.tls_on = False

        # Log in and encryption setup order is left to subclasses.
        self.authenticated = False

    def __enter__(self):
        return self

    def __exit__(self, *args):
        is_connected = lambda: hasattr(self, "file")
        if is_connected():
            try:
                self.quit()
            except (socket.error, EOFError):
                pass
            finally:
                if is_connected():
                    self._close()

    def getwelcome(self):
        """Get the welcome message from the server
        (this is read and squirreled away by __init__()).
        If the response code is 200, posting is allowed;
        if it 201, posting is not allowed."""

        if self.debugging: print('*welcome*', repr(self.welcome))
        return self.welcome

    def getcapabilities(self):
        """Get the server capabilities, as read by __init__().
        If the CAPABILITIES command is not supported, an empty dict is
        returned."""
        if self._caps is None:
            self.nntp_version = 1
            self.nntp_implementation = None
            try:
                resp, caps = self.capabilities()
            except (NNTPPermanentError, NNTPTemporaryError):
                # Server doesn't support capabilities
                self._caps = {}
            else:
                self._caps = caps
                if 'VERSION' in caps:
                    # The server can advertise several supported versions,
                    # choose the highest.
                    self.nntp_version = max(map(int, caps['VERSION']))
                if 'IMPLEMENTATION' in caps:
                    self.nntp_implementation = ' '.join(caps['IMPLEMENTATION'])
        return self._caps

    def set_debuglevel(self, level):
        """Set the debugging level.  Argument 'level' means:
        0: no debugging output (default)
        1: print commands and responses but not body text etc.
        2: also print raw lines read and sent before stripping CR/LF"""

        self.debugging = level
    debug = set_debuglevel

    def _putline(self, line):
        """Internal: send one line to the server, appending CRLF.
        The `line` must be a bytes-like object."""
        line = line + _CRLF
        if self.debugging > 1: print('*put*', repr(line))
        self.file.write(line)
        self.file.flush()

    def _putcmd(self, line):
        """Internal: send one command to the server (through _putline()).
        The `line` must be an unicode string."""
        if self.debugging: print('*cmd*', repr(line))
        line = line.encode(self.encoding, self.errors)
        self._putline(line)

    def _getline(self, strip_crlf=True):
        """Internal: return one line from the server, stripping _CRLF.
        Raise EOFError if the connection is closed.
        Returns a bytes object."""
        line = self.file.readline()
        if self.debugging > 1:
            print('*get*', repr(line))
        if not line: raise EOFError
        if strip_crlf:
            if line[-2:] == _CRLF:
                line = line[:-2]
            elif line[-1:] in _CRLF:
                line = line[:-1]
        return line

    def _getresp(self):
        """Internal: get a response from the server.
        Raise various errors if the response indicates an error.
        Returns an unicode string."""
        resp = self._getline()
        if self.debugging: print('*resp*', repr(resp))
        resp = resp.decode(self.encoding, self.errors)
        c = resp[:1]
        if c == '4':
            raise NNTPTemporaryError(resp)
        if c == '5':
            raise NNTPPermanentError(resp)
        if c not in '123':
            raise NNTPProtocolError(resp)
        return resp

    def _getlongresp(self, file=None):
        """Internal: get a response plus following text from the server.
        Raise various errors if the response indicates an error.

        Returns a (response, lines) tuple where `response` is an unicode
        string and `lines` is a list of bytes objects.
        If `file` is a file-like object, it must be open in binary mode.
        """

        openedFile = None
        try:
            # If a string was passed then open a file with that name
            if isinstance(file, (str, bytes)):
                openedFile = file = open(file, "wb")

            resp = self._getresp()
            if resp[:3] not in _LONGRESP:
                raise NNTPReplyError(resp)

            lines = []
            if file is not None:
                # XXX lines = None instead?
                terminators = (b'.' + _CRLF, b'.\n')
                while 1:
                    line = self._getline(False)
                    if line in terminators:
                        break
                    if line.startswith(b'..'):
                        line = line[1:]
                    file.write(line)
            else:
                terminator = b'.'
                while 1:
                    line = self._getline()
                    if line == terminator:
                        break
                    if line.startswith(b'..'):
                        line = line[1:]
                    lines.append(line)
        finally:
            # If this method created the file, then it must close it
            if openedFile:
                openedFile.close()

        return resp, lines

    def _getcompresp(self, file=None):
        """Modified _getlongresp for reading gzip data from the
        XOVER command.

        Note: The file variable has not been tested.
        """

        # Get the response.
        resp = self._getresp()
        # Check the response.
        if resp[:3] != '224':
            raise NNTPReplyError(resp)

        lines = b''
        terminator = False
        while 1:
            # Check if we found a possible terminator (.\r\n)
            if terminator:
                # The socket is non blocking, so it throws an
                # exception if the server sends back nothing.
                try:
                    # The server sent back something.
                    line = self._getline(False)
                    # So set back the socket to blocking.
                    self.sock.settimeout(120)
                    # And reset the terminator check.
                    terminator = False
                # The socket buffer was empty.
                except Exception as e:
                    # This was the final line, so remove the
                    # terminator and append it.
                    lines += termline[:-3]
                    # Set the socket back to blocking.
                    self.sock.settimeout(120)
                    # And break out of the loop.
                    break
                # The buffer was not empty, so write the last line.
                lines += termline
                # And write the current line.
                lines += line
            else:
                # We didn't find a terminator, so fetch the next line.
                line = self._getline(False)
                # We found a terminator.
                if line[-3:] == b'.\r\n':
                    # So add the line to a temp line for later.
                    termline = line
                    # And set the socket to non blocking.
                    self.sock.settimeout(0)
                    # And mark that we found a terminator.
                    terminator = True
                else:
                    # Add the current line to the final buffer.
                    lines += line

        try:
            # Try to decompress.
            dc_obj = zlib.decompressobj()
            decomp = dc_obj.decompress(lines)
            # Remove the last crlf and split the line into a list @crlf's
            if decomp[-2:] == b'\r\n':
                decomp = decomp[:-2].split(b'\r\n')
            else:
                decomp = decomp.split(b'\r\n')
        except Exception as e:
            raise NNTPDataError('Data from NNTP could not be decompressed.')

        # Check if the decompressed string is not empty.
        if decomp[0] == b'':
            raise NNTPDataError('Data from NNTP is empty gzip string.')

        openedFile = None
        try:
            # If a string was passed then open a file with that name
            if isinstance(file, (str, bytes)):
                openedFile = file = open(file, "wb")

            # Write the lines to the file.
            if file is not None:
                for header in decomp:
                    file.write("%s\n" % header)

        finally:
            # If this method created the file, then it must close it
            if openedFile:
                openedFile.close()

        return resp, decomp

    def _shortcmd(self, line):
        """Internal: send a command and get the response.
        Same return value as _getresp()."""
        self._putcmd(line)
        return self._getresp()

    def _longcmd(self, line, file=None):
        """Internal: send a command and get the response plus following text.
        Same return value as _getlongresp()."""
        self._putcmd(line)
        return self._getlongresp(file)

    def _longcmdstring(self, line, file=None):
        """Internal: send a command and get the response plus following text.
        Same as _longcmd() and _getlongresp(), except that the returned `lines`
        are unicode strings rather than bytes objects.
        """
        self._putcmd(line)
        resp, list = self._getlongresp(file)
        return resp, [line.decode(self.encoding, self.errors)
                      for line in list]

    def _compressedcmd(self, line, file=None):
        """Identical to _loncmdstring, but uses __getcompresp to
        read gzip data from the XOVER command.
        """
        self._putcmd(line)
        resp, list = self._getcompresp(file)
        return resp, [line.decode(self.encoding, self.errors)
                      for line in list]

    def _getoverviewfmt(self):
        """Internal: get the overview format. Queries the server if not
        already done, else returns the cached value."""
        try:
            return self._cachedoverviewfmt
        except AttributeError:
            pass
        try:
            resp, lines = self._longcmdstring("LIST OVERVIEW.FMT")
        except NNTPPermanentError:
            # Not supported by server?
            fmt = _DEFAULT_OVERVIEW_FMT[:]
        else:
            fmt = _parse_overview_fmt(lines)
        self._cachedoverviewfmt = fmt
        return fmt

    def _grouplist(self, lines):
        # Parse lines into "group last first flag"
        return [GroupInfo(*line.split()) for line in lines]

    def capabilities(self):
        """Process a CAPABILITIES command.  Not supported by all servers.
        Return:
        - resp: server response if successful
        - caps: a dictionary mapping capability names to lists of tokens
        (for example {'VERSION': ['2'], 'OVER': [], LIST: ['ACTIVE', 'HEADERS'] })
        """
        caps = {}
        resp, lines = self._longcmdstring("CAPABILITIES")
        for line in lines:
            name, *tokens = line.split()
            caps[name] = tokens
        return resp, caps

    def newgroups(self, date, *, file=None):
        """Process a NEWGROUPS command.  Arguments:
        - date: a date or datetime object
        Return:
        - resp: server response if successful
        - list: list of newsgroup names
        """
        if not isinstance(date, (datetime.date, datetime.date)):
            raise TypeError(
                "the date parameter must be a date or datetime object, "
                "not '{:40}'".format(date.__class__.__name__))
        date_str, time_str = _unparse_datetime(date, self.nntp_version < 2)
        cmd = 'NEWGROUPS {0} {1}'.format(date_str, time_str)
        resp, lines = self._longcmdstring(cmd, file)
        return resp, self._grouplist(lines)

    def newnews(self, group, date, *, file=None):
        """Process a NEWNEWS command.  Arguments:
        - group: group name or '*'
        - date: a date or datetime object
        Return:
        - resp: server response if successful
        - list: list of message ids
        """
        if not isinstance(date, (datetime.date, datetime.date)):
            raise TypeError(
                "the date parameter must be a date or datetime object, "
                "not '{:40}'".format(date.__class__.__name__))
        date_str, time_str = _unparse_datetime(date, self.nntp_version < 2)
        cmd = 'NEWNEWS {0} {1} {2}'.format(group, date_str, time_str)
        return self._longcmdstring(cmd, file)

    def list(self, group_pattern=None, *, file=None):
        """Process a LIST or LIST ACTIVE command. Arguments:
        - group_pattern: a pattern indicating which groups to query
        - file: Filename string or file object to store the result in
        Returns:
        - resp: server response if successful
        - list: list of (group, last, first, flag) (strings)
        """
        if group_pattern is not None:
            command = 'LIST ACTIVE ' + group_pattern
        else:
            command = 'LIST'
        resp, lines = self._longcmdstring(command, file)
        return resp, self._grouplist(lines)

    def _getdescriptions(self, group_pattern, return_all):
        line_pat = regex.compile('^(?P<group>[^ \t]+)[ \t]+(.*)$')
        # Try the more std (acc. to RFC2980) LIST NEWSGROUPS first
        resp, lines = self._longcmdstring('LIST NEWSGROUPS ' + group_pattern)
        if not resp.startswith('215'):
            # Now the deprecated XGTITLE.  This either raises an error
            # or succeeds with the same output structure as LIST
            # NEWSGROUPS.
            resp, lines = self._longcmdstring('XGTITLE ' + group_pattern)
        groups = {}
        for raw_line in lines:
            match = line_pat.search(raw_line.strip())
            if match:
                name, desc = match.group(1, 2)
                if not return_all:
                    return desc
                groups[name] = desc
        if return_all:
            return resp, groups
        else:
            # Nothing found
            return ''

    def description(self, group):
        """Get a description for a single group.  If more than one
        group matches ('group' is a pattern), return the first.  If no
        group matches, return an empty string.

        This elides the response code from the server, since it can
        only be '215' or '285' (for xgtitle) anyway.  If the response
        code is needed, use the 'descriptions' method.

        NOTE: This neither checks for a wildcard in 'group' nor does
        it check whether the group actually exists."""
        return self._getdescriptions(group, False)

    def descriptions(self, group_pattern):
        """Get descriptions for a range of groups."""
        return self._getdescriptions(group_pattern, True)

    def group(self, name):
        """Process a GROUP command.  Argument:
        - group: the group name
        Returns:
        - resp: server response if successful
        - count: number of articles
        - first: first article number
        - last: last article number
        - name: the group name
        """
        resp = self._shortcmd('GROUP ' + name)
        if not resp.startswith('211'):
            raise NNTPReplyError(resp)
        words = resp.split()
        count = first = last = 0
        n = len(words)
        if n > 1:
            count = words[1]
            if n > 2:
                first = words[2]
                if n > 3:
                    last = words[3]
                    if n > 4:
                        name = words[4].lower()
        return resp, int(count), int(first), int(last), name

    def help(self, *, file=None):
        """Process a HELP command. Argument:
        - file: Filename string or file object to store the result in
        Returns:
        - resp: server response if successful
        - list: list of strings returned by the server in response to the
                HELP command
        """
        return self._longcmdstring('HELP', file)

    def _statparse(self, resp):
        """Internal: parse the response line of a STAT, NEXT, LAST,
        ARTICLE, HEAD or BODY command."""
        if not resp.startswith('22'):
            raise NNTPReplyError(resp)
        words = resp.split()
        art_num = int(words[1])
        message_id = words[2]
        return resp, art_num, message_id

    def _statcmd(self, line):
        """Internal: process a STAT, NEXT or LAST command."""
        resp = self._shortcmd(line)
        return self._statparse(resp)

    def stat(self, message_spec=None):
        """Process a STAT command.  Argument:
        - message_spec: article number or message id (if not specified,
          the current article is selected)
        Returns:
        - resp: server response if successful
        - art_num: the article number
        - message_id: the message id
        """
        if message_spec:
            return self._statcmd('STAT {0}'.format(message_spec))
        else:
            return self._statcmd('STAT')

    def next(self):
        """Process a NEXT command.  No arguments.  Return as for STAT."""
        return self._statcmd('NEXT')

    def last(self):
        """Process a LAST command.  No arguments.  Return as for STAT."""
        return self._statcmd('LAST')

    def _artcmd(self, line, file=None):
        """Internal: process a HEAD, BODY or ARTICLE command."""
        resp, lines = self._longcmd(line, file)
        resp, art_num, message_id = self._statparse(resp)
        return resp, ArticleInfo(art_num, message_id, lines)

    def head(self, message_spec=None, *, file=None):
        """Process a HEAD command.  Argument:
        - message_spec: article number or message id
        - file: filename string or file object to store the headers in
        Returns:
        - resp: server response if successful
        - ArticleInfo: (article number, message id, list of header lines)
        """
        if message_spec is not None:
            cmd = 'HEAD {0}'.format(message_spec)
        else:
            cmd = 'HEAD'
        return self._artcmd(cmd, file)

    def body(self, message_spec=None, *, file=None):
        """Process a BODY command.  Argument:
        - message_spec: article number or message id
        - file: filename string or file object to store the body in
        Returns:
        - resp: server response if successful
        - ArticleInfo: (article number, message id, list of body lines)
        """
        if message_spec is not None:
            cmd = 'BODY {0}'.format(message_spec)
        else:
            cmd = 'BODY'
        return self._artcmd(cmd, file)

    def article(self, message_spec=None, *, file=None):
        """Process an ARTICLE command.  Argument:
        - message_spec: article number or message id
        - file: filename string or file object to store the article in
        Returns:
        - resp: server response if successful
        - ArticleInfo: (article number, message id, list of article lines)
        """
        if message_spec is not None:
            cmd = 'ARTICLE {0}'.format(message_spec)
        else:
            cmd = 'ARTICLE'
        return self._artcmd(cmd, file)

    def slave(self):
        """Process a SLAVE command.  Returns:
        - resp: server response if successful
        """
        return self._shortcmd('SLAVE')

    def xhdr(self, hdr, str, *, file=None):
        """Process an XHDR command (optional server extension).  Arguments:
        - hdr: the header type (e.g. 'subject')
        - str: an article nr, a message id, or a range nr1-nr2
        - file: Filename string or file object to store the result in
        Returns:
        - resp: server response if successful
        - list: list of (nr, value) strings
        """
        pat = regex.compile('^([0-9]+) ?(.*)\n?')
        resp, lines = self._longcmdstring('XHDR {0} {1}'.format(hdr, str), file)
        def remove_number(line):
            m = pat.match(line)
            return m.group(1, 2) if m else line
        return resp, [remove_number(line) for line in lines]

    def compression(self):
        """Process an XFEATURE GZIP COMPRESS command.
        Returns:
        - bool: Did the server understand the command?
        """
        try:
            resp = self._shortcmd('XFEATURE COMPRESS GZIP')
            if resp[:3] == '290':
                return True
            else:
                return False
        except Exception as e:
            return False

    def xover(self, start, end, *, file=None):
        """Process an XOVER command (optional server extension) Arguments:
        - start: start of range
        - end: end of range
        - file: Filename string or file object to store the result in
        Returns:
        - resp: server response if successful
        - list: list of dicts containing the response fields
        """
        if self.compressionstatus:
            resp, lines = self._compressedcmd('XOVER {0}-{1}'.format(start, end), file)
        else:
            resp, lines = self._longcmdstring('XOVER {0}-{1}'.format(start, end), file)
        fmt = self._getoverviewfmt()
        return resp, _parse_overview(lines, fmt)

    def over(self, message_spec, *, file=None):
        """Process an OVER command.  If the command isn't supported, fall
        back to XOVER. Arguments:
        - message_spec:
            - either a message id, indicating the article to fetch
              information about
            - or a (start, end) tuple, indicating a range of article numbers;
              if end is None, information up to the newest message will be
              retrieved
            - or None, indicating the current article number must be used
        - file: Filename string or file object to store the result in
        Returns:
        - resp: server response if successful
        - list: list of dicts containing the response fields

        NOTE: the "message id" form isn't supported by XOVER
        """
        cmd = 'OVER' if 'OVER' in self._caps else 'XOVER'
        if isinstance(message_spec, (tuple, list)):
            start, end = message_spec
            cmd += ' {0}-{1}'.format(start, end or '')
        elif message_spec is not None:
            cmd = cmd + ' ' + message_spec
        if self.compressionstatus:
            resp, lines = self._compressedcmd(cmd, file)
        else:
            resp, lines = self._longcmdstring(cmd, file)
        fmt = self._getoverviewfmt()
        return resp, _parse_overview(lines, fmt)

    def xgtitle(self, group, *, file=None):
        """Process an XGTITLE command (optional server extension) Arguments:
        - group: group name wildcard (i.e. news.*)
        Returns:
        - resp: server response if successful
        - list: list of (name,title) strings"""
        warnings.warn("The XGTITLE extension is not actively used, "
                      "use descriptions() instead",
                      DeprecationWarning, 2)
        line_pat = regex.compile('^([^ \t]+)[ \t]+(.*)$')
        resp, raw_lines = self._longcmdstring('XGTITLE ' + group, file)
        lines = []
        for raw_line in raw_lines:
            match = line_pat.search(raw_line.strip())
            if match:
                lines.append(match.group(1, 2))
        return resp, lines

    def xpath(self, id):
        """Process an XPATH command (optional server extension) Arguments:
        - id: Message id of article
        Returns:
        resp: server response if successful
        path: directory path to article
        """
        warnings.warn("The XPATH extension is not actively used",
                      DeprecationWarning, 2)

        resp = self._shortcmd('XPATH {0}'.format(id))
        if not resp.startswith('223'):
            raise NNTPReplyError(resp)
        try:
            [resp_num, path] = resp.split()
        except ValueError:
            raise NNTPReplyError(resp)
        else:
            return resp, path

    def date(self):
        """Process the DATE command.
        Returns:
        - resp: server response if successful
        - date: datetime object
        """
        resp = self._shortcmd("DATE")
        if not resp.startswith('111'):
            raise NNTPReplyError(resp)
        elem = resp.split()
        if len(elem) != 2:
            raise NNTPDataError(resp)
        date = elem[1]
        if len(date) != 14:
            raise NNTPDataError(resp)
        return resp, _parse_datetime(date, None)

    def _post(self, command, f):
        resp = self._shortcmd(command)
        # Raises a specific exception if posting is not allowed
        if not resp.startswith('3'):
            raise NNTPReplyError(resp)
        if isinstance(f, (bytes, bytearray)):
            f = f.splitlines()
        # We don't use _putline() because:
        # - we don't want additional CRLF if the file or iterable is already
        #   in the right format
        # - we don't want a spurious flush() after each line is written
        for line in f:
            if not line.endswith(_CRLF):
                line = line.rstrip(b"\r\n") + _CRLF
            if line.startswith(b'.'):
                line = b'.' + line
            self.file.write(line)
        self.file.write(b".\r\n")
        self.file.flush()
        return self._getresp()

    def post(self, data):
        """Process a POST command.  Arguments:
        - data: bytes object, iterable or file containing the article
        Returns:
        - resp: server response if successful"""
        return self._post('POST', data)

    def ihave(self, message_id, data):
        """Process an IHAVE command.  Arguments:
        - message_id: message-id of the article
        - data: file containing the article
        Returns:
        - resp: server response if successful
        Note that if the server refuses the article an exception is raised."""
        return self._post('IHAVE {0}'.format(message_id), data)

    def _close(self):
        self.file.close()
        del self.file

    def quit(self):
        """Process a QUIT command and close the socket.  Returns:
        - resp: server response if successful"""
        try:
            resp = self._shortcmd('QUIT')
        finally:
            self._close()
        return resp

    def login(self, user=None, password=None, usenetrc=True):
        if self.authenticated:
            raise ValueError("Already logged in.")
        if not user and not usenetrc:
            raise ValueError(
                "At least one of `user` and `usenetrc` must be specified")
        # If no login/password was specified but netrc was requested,
        # try to get them from ~/.netrc
        # Presume that if .netrc has an entry, NNRP authentication is required.
        try:
            if usenetrc and not user:
                import netrc
                credentials = netrc.netrc()
                auth = credentials.authenticators(self.host)
                if auth:
                    user = auth[0]
                    password = auth[2]
        except IOError:
            pass
        # Perform NNTP authentication if needed.
        if not user:
            return
        resp = self._shortcmd('authinfo user ' + user)
        if resp.startswith('381'):
            if not password:
                raise NNTPReplyError(resp)
            else:
                resp = self._shortcmd('authinfo pass ' + password)
                if not resp.startswith('281'):
                    raise NNTPPermanentError(resp)
        # Capabilities might have changed after login
        self._caps = None
        self.getcapabilities()
        # Attempt to send mode reader if it was requested after login.
        # Only do so if we're not in reader mode already.
        if self.readermode_afterauth and 'READER' not in self._caps:
            self._setreadermode()
            # Capabilities might have changed after MODE READER
            self._caps = None
            self.getcapabilities()

    def _setreadermode(self):
        try:
            self.welcome = self._shortcmd('mode reader')
        except NNTPPermanentError:
            # Error 5xx, probably 'not implemented'
            pass
        except NNTPTemporaryError as e:
            if e.response.startswith('480'):
                # Need authorization before 'mode reader'
                self.readermode_afterauth = True
            else:
                raise

    if _have_ssl:
        def starttls(self, context=None):
            """Process a STARTTLS command. Arguments:
            - context: SSL context to use for the encrypted connection
            """
            # Per RFC 4642, STARTTLS MUST NOT be sent after authentication or if
            # a TLS session already exists.
            if self.tls_on:
                raise ValueError("TLS is already enabled.")
            if self.authenticated:
                raise ValueError("TLS cannot be started after authentication.")
            resp = self._shortcmd('STARTTLS')
            if resp.startswith('382'):
                self.file.close()
                self.sock = _encrypt_on(self.sock, context)
                self.file = self.sock.makefile("rwb")
                self.tls_on = True
                # Capabilities may change after TLS starts up, so ask for them
                # again.
                self._caps = None
                self.getcapabilities()
            else:
                raise NNTPError("TLS failed to start.")


class NNTP(_NNTPBase):

    def __init__(self, host, port=NNTP_PORT, user=None, password=None,
                 readermode=None, usenetrc=False,
                 timeout=_GLOBAL_DEFAULT_TIMEOUT, compression=True):
        """Initialize an instance.  Arguments:
        - host: hostname to connect to
        - port: port to connect to (default the standard NNTP port)
        - user: username to authenticate with
        - password: password to use with username
        - readermode: if true, send 'mode reader' command after
                      connecting.
        - usenetrc: allow loading username and password from ~/.netrc file
                    if not specified explicitly
        - timeout: timeout (in seconds) used for socket connections
        - compression: To try to enable header compression or not.

        readermode is sometimes necessary if you are connecting to an
        NNTP server on the local machine and intend to call
        reader-specific commands, such as `group'.  If you get
        unexpected NNTPPermanentErrors, you might need to set
        readermode.
        """
        self.host = host
        self.port = port
        self.sock = socket.create_connection((host, port), timeout)
        file = self.sock.makefile("rwb")
        _NNTPBase.__init__(self, file, host,
                           readermode, timeout)
        if user or usenetrc:
            self.login(user, password, usenetrc)

        if compression:
            self.compressionstatus = self.compression()
        else:
            self.compressionstatus = False

    def _close(self):
        try:
            _NNTPBase._close(self)
        finally:
            self.sock.close()


if _have_ssl:
    class NNTP_SSL(_NNTPBase):

        def __init__(self, host, port=NNTP_SSL_PORT,
                    user=None, password=None, ssl_context=None,
                    readermode=None, usenetrc=False,
                    timeout=_GLOBAL_DEFAULT_TIMEOUT, compression=True):
            """This works identically to NNTP.__init__, except for the change
            in default port and the `ssl_context` argument for SSL connections.
            """
            self.sock = socket.create_connection((host, port), timeout)
            self.sock = _encrypt_on(self.sock, ssl_context)
            file = self.sock.makefile("rwb")
            _NNTPBase.__init__(self, file, host,
                               readermode=readermode, timeout=timeout)
            if user or usenetrc:
                self.login(user, password, usenetrc)

            if compression:
                self.compressionstatus = self.compression()
            else:
                self.compressionstatus = False

        def _close(self):
            try:
                _NNTPBase._close(self)
            finally:
                self.sock.close()

    __all__.append("NNTP_SSL")


# Test retrieval when run as a script.
if __name__ == '__main__':
    import argparse
    from email.utils import parsedate

    parser = argparse.ArgumentParser(description="""\
        nntplib built-in demo - display the latest articles in a newsgroup""")
    parser.add_argument('-g', '--group', default='gmane.comp.python.general',
                        help='group to fetch messages from (default: %(default)s)')
    parser.add_argument('-s', '--server', default='news.gmane.org',
                        help='NNTP server hostname (default: %(default)s)')
    parser.add_argument('-p', '--port', default=-1, type=int,
                        help='NNTP port number (default: %s / %s)' % (NNTP_PORT, NNTP_SSL_PORT))
    parser.add_argument('-n', '--nb-articles', default=10, type=int,
                        help='number of articles to fetch (default: %(default)s)')
    parser.add_argument('-S', '--ssl', action='store_true', default=False,
                        help='use NNTP over SSL')
    args = parser.parse_args()

    port = args.port
    if not args.ssl:
        if port == -1:
            port = NNTP_PORT
        s = NNTP(host=args.server, port=port)
    else:
        if port == -1:
            port = NNTP_SSL_PORT
        s = NNTP_SSL(host=args.server, port=port)

    caps = s.getcapabilities()
    if 'STARTTLS' in caps:
        s.starttls()
    resp, count, first, last, name = s.group(args.group)
    print('Group', name, 'has', count, 'articles, range', first, 'to', last)

    def cut(s, lim):
        if len(s) > lim:
            s = s[:lim - 4] + "..."
        return s

    first = str(int(last) - args.nb_articles + 1)
    resp, overviews = s.xover(first, last)
    for artnum, over in overviews:
        author = decode_header(over['from']).split('<', 1)[0]
        subject = decode_header(over['subject'])
        lines = int(over[':lines'])
        print("{:7} {:20} {:42} ({})".format(
              artnum, cut(author, 20), cut(subject, 42), lines)
              )

    s.quit()
    

########NEW FILE########
__FILENAME__ = rar
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
A pure-Python module for identifying and examining RAR files developed without
any exposure to the original unrar code. (Just format docs from wotsit.org)

It was, however, influenced by the zipfile module in the Python standard
library as, having already decided to match the zipfile.ZipFile API as closely
as feasibly possible, I didn't see a point to doing extra work to come up with
new ways of laying out my code for no good reason.

@todo: Determine how rarfile (http://rarfile.berlios.de/) compares to this in
various target metrics. If it is superior or close enough on all fronts,
patch it as necessary and plan a migration path. Otherwise, do the following:
 - Complete the parsing of the RAR metadata.
   (eg. Get data from archive header, check CRCs, read cleartext comments, etc.)
 - Optimize further and write a test suite.
 - Double-check that ZipFile/ZipInfo API compatibility has been maintained
   wherever feasible.
 - Support extraction of files stored with no compression.
 - Look into supporting split and password-protected RARs.
 - Some password-protected RAR files use blocks with types 0x30, 0x60, and 0xAD
   according to this code. Figure out whether it's a bug or whether they're really
   completely new kinds of blocks. (Encrypted headers for filename-hiding?)
 - When the appropriate code is available, use the following message for failure
   to extract compressed files::
    For reasions of patent, performance, and a general lack of motivation on the
    author's part, this module does not extract compressed files.
"""

__appname__ = "rar.py"
__author__ = "Stephan Sokolow (deitarion/SSokolow)"
__version__ = "0.2.99.0"
__license__ = "PSF License 2.4 or higher (The Python License)"

#{ Settings for findRarHeader()
CHUNK_SIZE = 4096
MARKER_BLOCK = b"\x52\x61\x72\x21\x1a\x07\x00"
FIND_LIMIT = 1024 ** 2 #: 1MiB
# A Compromise. Override FIND_LIMIT with 0 to be sure but potentially very slow.

#{ Packing method values
RAR_STORED = 0x30
RAR_FASTEST = 0x31
RAR_FAST = 0x32
RAR_NORMAL = 0x33
RAR_GOOD = 0x34
RAR_BEST = 0x35
#}

import math
import struct
import sys
import time
import zlib

_struct_blockHeader = struct.Struct("<HBHH")
_struct_addSize = struct.Struct('<L')
_struct_fileHead_add1 = struct.Struct("<LBLLBBHL") # Plus FILE_NAME and everything after it


class BadRarFile(Exception):
    """Raised when no valid RAR header is found in a given file."""


class RarInfo(object):
    """The metadata for a file stored in a RAR archive.

    @attention: API compatibility with ZipInfo could not be maintained in the
    following fields:
     - C{create_version} (Not stored in RAR files)
     - C{flag_bits} (Zip and RAR use different file header flags)
     - C{volume} (Zip files specify volume number. RAR files just have
       "File is continued from previous" and "File continues in next" flags and
       an archive-level "is volume" flag)
     - C{comment} (RAR files may have multiple comments per file and they may be
       stored using compression... which rar.py doesn't support)

    @todo: How do I interpret the raw file timestamp?
    @todo: Is the file's CRC of the compressed or uncompressed data?
    @todo: Does RAR perform any kind of path separator normalization?
    """

    os_map = ['MS DOS', 'OS/2', 'Win32', 'Unix'] #: Interpretations for possible L{create_system} values.

    compress_size = None    #: File's compressed size
    compress_type = None    #: Packing method (C{0x30} indicates no compression)
    create_system = None    #: Type of system on which the file originated (See L{os_map})
    date_time = None        #: File's timestamp
    external_attr = None    #: File's attributes
    extract_version = None  #: Minimum RAR version needed to extract (major * 10 + minor)
    filename = None         #: Filename relative to the archive root
    file_size = None        #: File's uncompressed size
    flag_bits = 0           #: Raw flag bits from the RAR header
    header_offset = None    #: Offset of the compressed data within the file
    is_directory = False    #: The entry describes a folder/directory
    is_encrypted = False    #: The file has been encrypted with a password
    is_solid = False        #: Information from previous files has been used
    not_first_piece = False #: File is continued from previous volume
    not_last_piece = False  #: File continues in next volume
    CRC = None              #: File's CRC
    _raw_time = None        #: Raw integer time value extracted from the header

    #TODO: comment, extra, reserved, internal_attr

    def __init__(self, filename, ftime=0):
        """
        @param filename: The file's name and path relative to the archive root.

        @note: Since I know of no filesystem which allows null bytes in paths,
        this borrows a trick from C{ZipInfo} and truncates L{filename} at the
        first null byte to protect against certain kinds of virus tricks.

        @todo: Implement support for taking ints OR tuples for L{ftime}.
        """
        filename = filename.decode('ISO-8859-1')
        null_byte = filename.find(chr(0))
        if null_byte >= 0:
            filename = filename[0:null_byte]

        self.filename = filename
        self.orig_filename = filename # Match ZipInfo for better compatibility
        self._raw_time = ftime
        self.date_time = time.gmtime(self._raw_time) #TODO: Verify this is correct.


class RarFile(object):
    """A simple parser for RAR archives capable of retrieving content metadata
    and, possibly in the future, of extracting entries stored without
    compression.

    @note: Whenever feasible, this class replicates the API of
        C{zipfile.ZipFile}. As a side-effect, design decisions the author
        has no strong feelings about (eg. naming of private methods)
        will generally closely follow those made C{in zipfile.ZipFile}.
    """

    _block_types = {
        0x72: 'Marker Block ( MARK_HEAD )',
        0x73: 'Archive Heaver ( MAIN_HEAD )',
        0x74: 'File Header',
        0x75: 'Comment Header',
        0x76: 'Extra Info',
        0x77: 'Subblock',
        0x78: 'Recovery Record',
        0x7b: 'Terminator?'
    } #: Raw HEAD_TYPE values used in block headers.

    # According to the comment in zipfile.ZipFile, __del__ needs fp here.
    fp = None          #: The file handle used to read the metadata.
    _filePassed = None #: Whether an already-open file handle was passed in.

    # I just put all public members here as a matter of course.
    filelist = None #: A C{list} of L{RarInfo} objects corresponding to the contents.
    debug = 0       #: Debugging verbosity. Effective range is currently 0 to 1.

    def __init__(self, handle):
        # If we've been given a path, get our desired file-like object.
        if isinstance(handle, str):
            self_filePassed = False
            self.filename = handle
            self.fp = open(handle, 'rb')
        else:
            self._filePassed = True
            self.fp = handle
            self.filename = getattr(handle, 'name', None)

        # Find the header, skipping the SFX module if present.
        start_offset = findRarHeader(self.fp)
        if start_offset:
            self.fp.seek(start_offset)
        else:
            if not self._filePassed:
                self.fp.close()
                self.fp = None
            raise BadRarFile("Not a valid RAR file")

        self.filelist = []

        # Actually read the file metadata.
        self._getContents()

    def __del__(self):
        """Close the file handle if we opened it... just in case the underlying
        Python implementation doesn't do refcount closing."""
        if self.fp and not self._filePassed:
            self.fp.close()

    def _getContents(self):
        """Content-reading code is here separated from L{__init__} so that, if
        the author so chooses, writing of uncompressed RAR files may be
        implemented in a later version more easily.
        """
        while True:
            offset = self.fp.tell()

            # Read the fields present in every type of block header
            try:
                head_crc, head_type, head_flags, head_size = self._read_struct(_struct_blockHeader)
            except struct.error:
                # If it fails here, we've reached the end of the file.
                return

            # Read the optional field ADD_SIZE if present.
            if head_flags & 0x8000:
                add_size = self._read_struct(_struct_addSize)[0]
            else:
                add_size = 0

            # TODO: Rework handling of archive headers.
            if head_type == 0x73:
                #TODO: Try to factor this out to reduce time spent in syscalls.
                self.fp.seek(offset + 2) # Seek to just after HEAD_CRC

            # TODO: Rework handling of file headers.
            elif head_type == 0x74:
                unp_size, host_os, file_crc, ftime, unp_ver, method, name_size, attr = self._read_struct(
                    _struct_fileHead_add1)

                # FIXME: What encoding does WinRAR use for filenames?
                # TODO: Verify that ftime is seconds since the epoch as it seems
                fileinfo = RarInfo(self.fp.read(name_size), ftime)
                fileinfo.compress_size = add_size
                fileinfo.header_offset = offset
                fileinfo.file_size = unp_size   #TODO: What about >2GiB files? (Zip64 equivalent?)
                fileinfo.CRC = file_crc         #TODO: Verify the format matches that ZipInfo uses.
                fileinfo.compress_type = method

                # Note: RAR seems to have copied the encoding methods used by
                # Zip for these values.
                fileinfo.create_system = host_os
                fileinfo.extract_version = unp_ver
                fileinfo.external_attr = attr  #TODO: Verify that this is correct.

                # Handle flags
                fileinfo.flag_bits = head_flags
                fileinfo.not_first_piece = head_flags & 0x01
                fileinfo.not_last_piece = head_flags & 0x02
                fileinfo.is_encrypted = head_flags & 0x04
                #TODO: Handle comments
                fileinfo.is_solid = head_flags & 0x10

                # TODO: Verify this is correct handling of bits 7,6,5 == 111
                fileinfo.is_directory = head_flags & 0xe0

                self.filelist.append(fileinfo)
            elif self.debug > 0:
                sys.stderr.write(
                    "Unhandled block: %s\n" % self._block_types.get(head_type, 'Unknown (0x%x)' % head_type))

            # Line up for the next block
            #TODO: Try to factor this out to reduce time spent in syscalls.
            if head_size == 0 and add_size == 0:
                return

            self.fp.seek(offset + head_size + add_size)

    def _read_struct(self, fmt):
        """Simplifies the process of extracting a struct from the open file."""
        return fmt.unpack(self.fp.read(fmt.size))

    def _check_crc(self, data, crc):
        """Check some data against a stored CRC.

        Note: For header CRCs, RAR calculates a CRC32 and then throws out the high-order bytes.

        @bug: This method of parsing is deprecated.
        @todo: I've only tested this out on 2-byte CRCs, not 4-byte file data CRCs.
        @todo: Isn't there some better way to do the check for CRC bitwidth?
        @bug: Figure out why I can't get a match on valid File Header CRCs.
        """
        if isinstance(crc, int):
            if crc < 65536:
                crc = struct.pack('>H', crc)
            else:
                crc = struct.pack('>L', crc)
        return struct.pack('>L', zlib.crc32(data)).endswith(crc)

    def infolist(self):
        """Return a list of L{RarInfo} instances for the files in the archive."""
        return self.filelist

    def namelist(self):
        """Return a list of filenames for the files in the archive."""
        return [x.filename for x in self.filelist]


def findRarHeader(handle, limit=FIND_LIMIT):
    """Searches a file-like object for a RAR header.

    @returns: The in-file offset of the first byte after the header block or
    C{None} if no RAR header was found.

    @warning: The given file-like object must support C{seek()} up to the size
    of C{limit}.

    @note: C{limit} is rounded up to the nearest multiple of L{CHUNK_SIZE}.

    @todo: Audit this to ensure it can't raise an exception L{is_rarfile()}
    won't catch.
    """
    startPos, chunk = handle.tell(), b""
    limit = math.ceil(limit / float(CHUNK_SIZE)) * CHUNK_SIZE

    # Find the RAR header and line up for further reads. (Support SFX bundles)
    while True:
        temp = handle.read(CHUNK_SIZE)
        curr_pos = handle.tell()

        # If we hit the end of the file without finding a RAR marker block...
        if not temp or (limit > 0 and curr_pos > limit):
            handle.seek(startPos)
            return None

        chunk += temp
        marker_offset = chunk.find(MARKER_BLOCK)
        if marker_offset > -1:
            handle.seek(startPos)
            return curr_pos - len(chunk) + marker_offset + len(MARKER_BLOCK)

        # Obviously we haven't found the marker yet...
        chunk = chunk[len(temp):] # Use a rolling window to minimize memory consumption.


def is_rarfile(filename, limit=FIND_LIMIT):
    """Convenience wrapper for L{findRarHeader} equivalent to C{is_zipfile}.

    Returns C{True} if C{filename} is a valid RAR file based on its magic
    number, otherwise returns C{False}.

    Optionally takes a limiting value for the maximum amount of data to sift
    through. Defaults to L{FIND_LIMIT} to set a sane bound on performance. Set
    it to 0 to perform an exhaustive search for a RAR header.

    @note: findRarHeader rounds this limit up to the nearest multiple of
    L{CHUNK_SIZE}.
    """
    try:
        handle = open(filename, 'rb')
        return findRarHeader(handle, limit) is not None
    except IOError:
        pass
    return False


if __name__ == '__main__':
    from optparse import OptionParser

    parser = OptionParser(description=__doc__.split('\n\n')[0],
                          version="%%prog v%s" % __version__, usage="%prog <path> ...")

    opts, args = parser.parse_args()

    if args:
        RarFile.debug = 1
        for fpath in args:
            print("File: %s" % fpath)
            if is_rarfile(fpath):
                for line in RarFile(fpath).namelist():
                    print("\t%s" % line)
            else:
                print("Not a RAR file")

########NEW FILE########
__FILENAME__ = postprocess
import multiprocessing
import time
import logging

from pynab import log
from pynab.db import db

import pynab.groups
import pynab.binaries
import pynab.releases
import pynab.tvrage
import pynab.rars
import pynab.nfos
import pynab.imdb

import scripts.quick_postprocess
import scripts.rename_bad_releases

import config

def mp_error(msg, *args):
    return multiprocessing.get_logger().error(msg, *args)


def process_tvrage():
    pynab.tvrage.process(500)


def process_nfos():
    pynab.nfos.process(500)


def process_rars():
    pynab.rars.process(500)


def process_imdb():
    pynab.imdb.process(500)


if __name__ == '__main__':
    log.info('Starting post-processing...')

    # print MP log as well
    multiprocessing.log_to_stderr().setLevel(logging.DEBUG)

    # start with a quick post-process
    log.info('starting with a quick post-process to clear out the cruft that\'s available locally...')
    scripts.quick_postprocess.local_postprocess()

    while True:
        # take care of REQ releases first
        for release in db.releases.find({'search_name': {'$regex': 'req', '$options': '-i'}}):
            pynab.releases.strip_req(release)

        # delete passworded releases first so we don't bother processing them
        if config.postprocess.get('delete_passworded', True):
            if config.postprocess.get('delete_potentially_passworded', True):
                query = {'passworded': {'$in': [True, 'potentially']}}
            else:
                query = {'passworded': True}
            db.releases.remove(query)

        # delete any nzbs that don't have an associated release
        # and delete any releases that don't have an nzb


        # grab and append tvrage data to tv releases
        tvrage_p = None
        if config.postprocess.get('process_tvrage', True):
            tvrage_p = multiprocessing.Process(target=process_tvrage)
            tvrage_p.start()

        imdb_p = None
        if config.postprocess.get('process_imdb', True):
            imdb_p = multiprocessing.Process(target=process_imdb)
            imdb_p.start()

        # grab and append nfo data to all releases
        nfo_p = None
        if config.postprocess.get('process_nfos', True):
            nfo_p = multiprocessing.Process(target=process_nfos)
            nfo_p.start()

        # check for passwords, file count and size
        rar_p = None
        if config.postprocess.get('process_rars', True):
            rar_p = multiprocessing.Process(target=process_rars)
            rar_p.start()

        if rar_p:
            rar_p.join()

        if imdb_p:
            imdb_p.join()

        if tvrage_p:
            tvrage_p.join()

        if nfo_p:
            nfo_p.join()

        # rename misc->other and all ebooks
        scripts.rename_bad_releases.rename_bad_releases(8010)
        scripts.rename_bad_releases.rename_bad_releases(7020)

        if config.postprocess.get('delete_bad_releases', False):
            pass
            #log.info('Deleting bad releases...')
            # not confident in this yet

        # wait for the configured amount of time between cycles
        postprocess_wait = config.postprocess.get('postprocess_wait', 1)
        log.info('sleeping for {:d} seconds...'.format(postprocess_wait))
        time.sleep(postprocess_wait)
########NEW FILE########
__FILENAME__ = api
import datetime
import os
import gzip
import pymongo
import pprint

from mako.template import Template
from mako import exceptions
from bottle import request, response

from pynab.db import db, fs
from pynab import log, root_dir
import config


def api_error(code):
    xml_header = '<?xml version="1.0" encoding="UTF-8"?>'

    errors = {
        100: 'Incorrect user credentials',
        101: 'Account suspended',
        102: 'Insufficient privileges/not authorized',
        103: 'Registration denied',
        104: 'Registrations are closed',
        105: 'Invalid registration (Email Address Taken)',
        106: 'Invalid registration (Email Address Bad Format)',
        107: 'Registration Failed (Data error)',
        200: 'Missing parameter',
        201: 'Incorrect parameter',
        202: 'No such function. (Function not defined in this specification).',
        203: 'Function not available. (Optional function is not implemented).',
        300: 'No such item.',
        301: 'Item already exists.',
        900: 'Unknown error',
        910: 'API Disabled',
    }

    if code in errors:
        error = errors[code]
    else:
        error = 'Something really, really bad happened.'

    return '{0}\n<error code=\"{1:d}\" description=\"{2}\" />'.format(xml_header, code, error)


def get_nfo(dataset=None):
    if auth():
        guid = request.query.guid or None
        if guid:
            release = db.releases.find_one({'id': guid})
            if release:
                data = fs.get(release['nfo']).read()
                response.set_header('Content-type', 'application/x-nfo')
                response.set_header('Content-Disposition', 'attachment; filename="{0}"'
                .format(release['search_name'].replace(' ', '_') + '.nfo')
                )
                return gzip.decompress(data)
            else:
                return api_error(300)
        else:
            return api_error(200)
    else:
        return api_error(100)


def get_nzb(dataset=None):
    if auth():
        guid = request.query.guid or None
        if not guid:
            guid = request.query.id or None

        if guid:
            release = db.releases.find_one({'id': guid})
            if release:
                data = fs.get(release['nzb']).read()
                response.set_header('Content-type', 'application/x-nzb')
                response.set_header('X-DNZB-Name', release['search_name'])
                response.set_header('X-DNZB-Category', release['category']['name'])
                response.set_header('Content-Disposition', 'attachment; filename="{0}"'
                .format(release['search_name'].replace(' ', '_') + '.nzb')
                )
                return gzip.decompress(data)
            else:
                return api_error(300)
        else:
            return api_error(200)
    else:
        return api_error(100)


def auth():
    api_key = request.query.apikey or ''

    user = db.users.find_one({'api_key': api_key})
    if user:
        return api_key
    else:
        return False


def movie_search(dataset=None):
    if auth():
        query = dict()
        query['category._id'] = {'$in': [2020, 2030, 2040, 2050, 2060]}

        try:
            imdb_id = request.query.imdbid or None
            if imdb_id:
                query['imdb._id'] = 'tt' + imdb_id

            genres = request.query.genre or None
            if genres:
                genres = genres.split(',')
                query['imdb.genre'] = {'$in': genres}
        except:
            return api_error(201)

        return search(dataset, query)
    else:
        return api_error(100)


def tv_search(dataset=None):
    if auth():
        query = dict()
        query['category._id'] = {'$in': [5030, 5040, 5050, 5060, 5070, 5080]}

        try:
            tvrage_id = request.query.rid or None
            if tvrage_id:
                query['tvrage._id'] = int(tvrage_id)

            season = request.query.season or None
            if season:
                if season.isdigit():
                    query['tv.season'] = 'S{:02d}'.format(int(season))
                else:
                    query['tv.season'] = season

            episode = request.query.ep or None
            if episode:
                if episode.isdigit():
                    query['tv.episode'] = 'E{:02d}'.format(int(episode))
                else:
                    query['tv.episode'] = episode
        except:
            return api_error(201)

        return search(dataset, query)
    else:
        return api_error(100)


def details(dataset=None):
    if auth():
        if request.query.id:
            release = db.releases.find_one({'id': request.query.id})
            if release:
                dataset['releases'] = [release]
                dataset['detail'] = True
                dataset['api_key'] = request.query.apikey

                try:
                    tmpl = Template(
                        filename=os.path.join(root_dir, 'templates/api/result.mako'))
                    return tmpl.render(**dataset)
                except:
                    log.error('Failed to deliver page: {0}'.format(exceptions.text_error_template().render()))
                    return None
            else:
                return api_error(300)
        else:
            return api_error(200)
    else:
        return api_error(100)


def caps(dataset=None):
    dataset['app_version'] = config.api.get('version', '1.0.0')
    dataset['api_version'] = config.api.get('api_version', '0.2.3')
    dataset['email'] = config.api.get('email', '')
    dataset['result_limit'] = config.api.get('result_limit', 20)
    dataset['result_default'] = config.api.get('result_default', 20)

    categories = {}
    for category in db.categories.find():
        if category.get('parent_id'):
            categories[category.get('parent_id')]['categories'].append(category)
        else:
            categories[category.get('_id')] = category
            categories[category.get('_id')]['categories'] = []
    dataset['categories'] = categories

    try:
        tmpl = Template(
            filename=os.path.join(root_dir, 'templates/api/caps.mako'))
        return tmpl.render(**dataset)
    except:
        log.error('Failed to deliver page: {0}'.format(exceptions.text_error_template().render()))
        return None


def search(dataset=None, params=None):
    if auth():
        # build the mongo query
        # add params if coming from a tv-search or something
        if params:
            query = dict(params)
        else:
            query = dict()

        try:
            # set limit to request or default
            # this will also match limit == 0, which would be infinite
            limit = request.query.limit or None
            if limit and int(limit) <= int(config.api.get('result_limit', 100)):
                limit = int(limit)
            else:
                limit = int(config.api.get('result_default', 20))

            # offset is only available for rss searches and won't work with text
            offset = request.query.offset or None
            if offset and int(offset) > 0:
                offset = int(offset)
            else:
                offset = 0

            # get categories
            cat_ids = request.query.cat or []
            if cat_ids:
                cat_ids = [int(c) for c in cat_ids.split(',')]
                categories = []
                for category in db.categories.find({'_id': {'$in': cat_ids}}):
                    if 'parent_id' not in category:
                        for child in db.categories.find({'parent_id': category['_id']}):
                            categories.append(child['_id'])
                    else:
                        categories.append(category['_id'])
                if 'category._id' in query:
                    query['category._id'].update({'$in': categories})
                else:
                    query['category._id'] = {'$in': categories}

            # group names
            grp_names = request.query.group or []
            if grp_names:
                grp_names = grp_names.split(',')
                groups = [g['_id'] for g in db.groups.find({'name': {'$in': grp_names}})]
                query['group._id'] = {'$in': groups}

            # max age
            max_age = request.query.maxage or None
            if max_age:
                oldest = datetime.datetime.now() - datetime.timedelta(int(max_age))
                query['posted'] = {'$gte': oldest}
        except Exception as e:
            # normally a try block this long would make me shudder
            # but we don't distinguish between errors, so it's fine
            log.error('Incorrect API Paramter or parsing error: {}'.format(e))
            return api_error(201)

        log.debug('Query parameters: {0}'.format(query))

        search_terms = request.query.q or None
        if search_terms:
            # we're searching specifically for a show or something

            # mash search terms into a single string
            # we remove carets because mongo's FT search is probably smart enough
            terms = ''
            if search_terms:
                terms = ' '.join(['\"{}\"'.format(term) for term in search_terms.replace('^', '').split(' ')])

            # build the full query - db.command() uses a different format
            full = {
                'command': 'text',
                'value': 'releases',
                'search': terms,
                'filter': query,
                'limit': limit,
            }

            results = db.command(**full)['results']

            if results:
                results = [r['obj'] for r in results]
            else:
                results = []

            # since FT searches don't support offsets
            total = limit
            offset = 0
        else:
            # we're looking for an rss feed
            # return results and sort by postdate ascending
            total = db.releases.find(query).count()
            results = db.releases.find(query, limit=int(limit), skip=int(offset)).sort('posted', pymongo.DESCENDING)

        dataset['releases'] = results
        dataset['offset'] = offset
        dataset['total'] = total
        dataset['search'] = True
        dataset['api_key'] = request.query.apikey

        try:
            tmpl = Template(
                filename=os.path.join(root_dir, 'templates/api/result.mako'))
            return tmpl.render(**dataset)
        except:
            log.error('Failed to deliver page: {0}'.format(exceptions.text_error_template().render()))
            return None
    else:
        return api_error(100)


functions = {
    's|search': search,
    'c|caps': caps,
    'd|details': details,
    'tv|tvsearch': tv_search,
    'm|movie': movie_search,
    'g|get': get_nzb,
    'gn|getnfo': get_nfo,
}

########NEW FILE########
__FILENAME__ = binaries
import regex
import time
import datetime
import pytz

from pynab.db import db
from pynab import log


CHUNK_SIZE = 500


def merge(a, b, path=None):
    """Merge multi-level dictionaries.
    Kudos: http://stackoverflow.com/questions/7204805/python-dictionaries-of-dictionaries-merge/
    """
    if path is None:
        path = []
    for key in b:
        if key in a:
            if isinstance(a[key], dict) and isinstance(b[key], dict):
                merge(a[key], b[key], path + [str(key)])
            elif a[key] == b[key]:
                pass  # same leaf value
            else:
                a[key] = b[key]
                #raise Exception('Conflict at {}: {} {}'.format('.'.join(path + [str(key)]), a[key], b[key]))
        else:
            a[key] = b[key]
    return a


def save(binary):
    """Save a single binary to the DB, including all
    segments/parts (which takes the longest).
    --
    Note: Much quicker. Hooray!
    """

    existing_binary = db.binaries.find_one({'name': binary['name']})
    try:
        if existing_binary:
            merge(existing_binary['parts'], binary['parts'])
            db.binaries.update({'_id': existing_binary['_id']}, {
                '$set': {
                    'parts': existing_binary['parts']
                }
            })
        else:
            db.binaries.insert({
                'name': binary['name'],
                'group_name': binary['group_name'],
                'posted': binary['posted'],
                'posted_by': binary['posted_by'],
                'category_id': binary['category_id'],
                'regex_id': binary['regex_id'],
                'req_id': binary['req_id'],
                'xref': binary['xref'],
                'total_parts': binary['total_parts'],
                'parts': binary['parts']
            })
    except:
        log.error('binary: binary was too large to fit in DB!')


def save_and_clear(binaries=None, parts=None):
    """Helper function to save a set of binaries
    and delete associated parts from the DB. This
    is a lot faster than Newznab's part deletion,
    which routinely took 10+ hours on my server.
    Turns out MySQL kinda sucks at deleting lots
    of shit. If we need more speed, move the parts
    away and drop the temporary table instead."""
    for binary in binaries.values():
        save(binary)

    if parts:
        db.parts.remove({'_id': {'$in': parts}})


def process():
    """Helper function to process parts into binaries
    based on regex in DB. Copies parts/segments across
    to the binary document. Keeps a list of parts that
    were processed for deletion."""

    start = time.time()

    binaries = {}
    orphan_binaries = []
    processed_parts = []

    # new optimisation: if we only have parts from a couple of groups,
    # we don't want to process the regex for every single one.
    # this removes support for "alt.binaries.games.*", but those weren't
    # used anyway, aside from just * (which it does work with)

    # to re-enable that feature in future, mongo supports reverse-regex through
    # where(), but it's slow as hell because it's processed by the JS engine
    relevant_groups = db.parts.distinct('group_name')
    for part in db.parts.find({'group_name': {'$in': relevant_groups}}, exhaust=True):
        for reg in db.regexes.find({'group_name': {'$in': [part['group_name'], '*']}}).sort('ordinal', 1):
            # convert php-style regex to python
            # ie. /(\w+)/i -> (\w+), regex.I
            # no need to handle s, as it doesn't exist in python

            # why not store it as python to begin with? some regex
            # shouldn't be case-insensitive, and this notation allows for that
            r = reg['regex']
            flags = r[r.rfind('/') + 1:]
            r = r[r.find('/') + 1:r.rfind('/')]
            regex_flags = regex.I if 'i' in flags else 0

            try:
                result = regex.search(r, part['subject'], regex_flags)
            except:
                log.error('binary: broken regex detected. _id: {:d}, removing...'.format(reg['_id']))
                db.regexes.remove({'_id': reg['_id']})
                continue

            match = result.groupdict() if result else None
            if match:
                # remove whitespace in dict values
                try:
                    match = {k: v.strip() for k, v in match.items()}
                except:
                    pass

                # fill name if reqid is available
                if match.get('reqid') and not match.get('name'):
                    match['name'] = match['reqid']

                # make sure the regex returns at least some name
                if not match.get('name'):
                    continue

                # if the binary has no part count and is 3 hours old
                # turn it into something anyway
                timediff = pytz.utc.localize(datetime.datetime.now()) \
                           - pytz.utc.localize(part['posted'])

                # if regex are shitty, look for parts manually
                # segment numbers have been stripped by this point, so don't worry
                # about accidentally hitting those instead
                if not match.get('parts'):
                    result = regex.search('(\d{1,3}\/\d{1,3})', part['subject'])
                    if result:
                        match['parts'] = result.group(1)

                # probably an nzb
                if not match.get('parts') and timediff.seconds / 60 / 60 > 3:
                    orphan_binaries.append(match['name'])
                    match['parts'] = '00/00'

                if match.get('name') and match.get('parts'):
                    if match['parts'].find('/') == -1:
                        match['parts'] = match['parts'].replace('-', '/') \
                            .replace('~', '/').replace(' of ', '/') \

                    match['parts'] = match['parts'].replace('[', '').replace(']', '') \
                        .replace('(', '').replace(')', '')

                    current, total = match['parts'].split('/')

                    # if the binary is already in our chunk,
                    # just append to it to reduce query numbers
                    if match['name'] in binaries:
                        binaries[match['name']]['parts'][current] = part
                    else:
                        b = {
                            'name': match['name'],
                            'posted': part['posted'],
                            'posted_by': part['posted_by'],
                            'group_name': part['group_name'],
                            'xref': part['xref'],
                            'regex_id': reg['_id'],
                            'category_id': reg['category_id'],
                            'req_id': match.get('reqid'),
                            'total_parts': int(total),
                            'parts': {current: part}
                        }

                        binaries[match['name']] = b
                    break

        # add the part to a list so we can delete it later
        processed_parts.append(part['_id'])

        # save and delete stuff in chunks
        if len(processed_parts) >= CHUNK_SIZE:
            save_and_clear(binaries, processed_parts)
            processed_parts = []
            binaries = {}

    # clear off whatever's left
    save_and_clear(binaries, processed_parts)

    end = time.time()

    log.info('binary: processed {} parts in {:.2f}s'
        .format(db.parts.count(), end - start)
    )


def parse_xref(xref):
    """Parse the header XREF into groups."""
    groups = []
    raw_groups = xref.split(' ')
    for raw_group in raw_groups:
        result = regex.search('^([a-z0-9\.\-_]+):(\d+)?$', raw_group, regex.I)
        if result:
            groups.append(result.group(1))
    return groups

########NEW FILE########
__FILENAME__ = categories
import regex
import collections
from pynab import log
from pynab.db import db

# category codes
# these are stored in the db, as well
CAT_GAME_NDS = 1010
CAT_GAME_PSP = 1020
CAT_GAME_WII = 1030
CAT_GAME_XBOX = 1040
CAT_GAME_XBOX360 = 1050
CAT_GAME_WIIWARE = 1060
CAT_GAME_XBOX360DLC = 1070
CAT_GAME_PS3 = 1080
CAT_MOVIE_FOREIGN = 2010
CAT_MOVIE_OTHER = 2020
CAT_MOVIE_SD = 2030
CAT_MOVIE_HD = 2040
CAT_MOVIE_BLURAY = 2050
CAT_MOVIE_3D = 2060
CAT_MUSIC_MP3 = 3010
CAT_MUSIC_VIDEO = 3020
CAT_MUSIC_AUDIOBOOK = 3030
CAT_MUSIC_LOSSLESS = 3040
CAT_PC_0DAY = 4010
CAT_PC_ISO = 4020
CAT_PC_MAC = 4030
CAT_PC_MOBILEOTHER = 4040
CAT_PC_GAMES = 4050
CAT_PC_MOBILEIOS = 4060
CAT_PC_MOBILEANDROID = 4070
CAT_TV_FOREIGN = 5020
CAT_TV_SD = 5030
CAT_TV_HD = 5040
CAT_TV_OTHER = 5050
CAT_TV_SPORT = 5060
CAT_TV_ANIME = 5070
CAT_TV_DOCU = 5080
CAT_XXX_DVD = 6010
CAT_XXX_WMV = 6020
CAT_XXX_XVID = 6030
CAT_XXX_X264 = 6040
CAT_XXX_PACK = 6050
CAT_XXX_IMAGESET = 6060
CAT_XXX_OTHER = 6070
CAT_BOOK_MAGS = 7010
CAT_BOOK_EBOOK = 7020
CAT_BOOK_COMICS = 7030

CAT_MISC_OTHER = 8010

CAT_PARENT_GAME = 1000
CAT_PARENT_MOVIE = 2000
CAT_PARENT_MUSIC = 3000
CAT_PARENT_PC = 4000
CAT_PARENT_TV = 5000
CAT_PARENT_XXX = 6000
CAT_PARENT_BOOK = 7000
CAT_PARENT_MISC = 8000

"""
This dict maps groups to potential categories. Some groups tend
to favour some release types over others, so you can specify those
here. If none of the suggestions for that group match, it'll just
try all possible categories. Categories are listed in order of priority.

There are two options for the list: either a parent category, or a subcategory.
If a parent category is supplied, the release will be checked against every
sub-category. If a subcategory is supplied, the release will automatically
be categorised as that.

ie.
[CAT_PARENT_PC, CAT_PC_0DAY]

Will attempt to categorise the release by every subcategory of PC. If no
match is found, it'll tag it as PC_0DAY.

You can also just leave it with only parent categories, in which case
the algorithm will fall through to attempting every single subcat (or failing).
A release is only categorised here on no-match if the array ends on a subcategory.
"""
group_regex = {
    regex.compile('alt\.binaries\.0day', regex.I): [
        CAT_PARENT_BOOK, CAT_PARENT_PC, CAT_PC_0DAY
    ],
    regex.compile('alt\.binaries\.ath', regex.I): [
        CAT_PARENT_XXX, CAT_PARENT_GAME, CAT_PARENT_PC, CAT_PARENT_TV, CAT_PARENT_MOVIE, CAT_PARENT_MUSIC,
        CAT_MISC_OTHER
    ],
    regex.compile('alt\.binaries\.b4e', regex.I): [
        CAT_PARENT_PC, CAT_PARENT_BOOK
    ],
    regex.compile('alt\.binaries\..*?audiobook', regex.I): [
        CAT_MUSIC_AUDIOBOOK
    ],
    regex.compile('lossless|flac', regex.I): [
        CAT_MUSIC_LOSSLESS
    ],
    regex.compile('alt\.binaries\.sounds|alt\.binaries\.mp3|alt\.binaries\.mp3', regex.I): [
        CAT_PARENT_MUSIC, CAT_MISC_OTHER
    ],
    regex.compile('alt\.binaries\.console.ps3', regex.I): [
        CAT_PARENT_GAME, CAT_GAME_PS3
    ],
    regex.compile('alt\.binaries\.games\.xbox', regex.I): [
        CAT_PARENT_GAME, CAT_PARENT_XXX, CAT_PARENT_TV, CAT_PARENT_MOVIE
    ],
    regex.compile('alt\.binaries\.games$', regex.I): [
        CAT_PARENT_GAME, CAT_PC_GAMES
    ],
    regex.compile('alt\.binaries\.games\.wii', regex.I): [
        CAT_PARENT_GAME
    ],
    regex.compile('alt\.binaries\.dvd', regex.I): [
        CAT_PARENT_BOOK, CAT_PARENT_PC, CAT_PARENT_XXX, CAT_PARENT_TV, CAT_PARENT_MOVIE
    ],
    regex.compile('alt\.binaries\.hdtv|alt\.binaries\.x264|alt\.binaries\.tv$', regex.I): [
        CAT_PARENT_MUSIC, CAT_PARENT_XXX, CAT_PARENT_TV, CAT_PARENT_MOVIE
    ],
    regex.compile('alt\.binaries\.nospam\.cheerleaders', regex.I): [
        CAT_PARENT_MUSIC, CAT_PARENT_XXX, CAT_PARENT_TV, CAT_PARENT_PC, CAT_PARENT_MOVIE
    ],
    regex.compile('alt\.binaries\.classic\.tv', regex.I): [
        CAT_PARENT_TV, CAT_TV_OTHER
    ],
    regex.compile('alt\.binaries\.multimedia$', regex.I): [
        CAT_PARENT_MOVIE, CAT_PARENT_TV
    ],
    regex.compile('alt\.binaries\.multimedia\.anime', regex.I): [
        CAT_TV_ANIME
    ],
    regex.compile('alt\.binaries\.anime', regex.I): [
        CAT_TV_ANIME
    ],
    regex.compile('alt\.binaries\.e(-|)book', regex.I): [
        CAT_PARENT_BOOK, CAT_BOOK_EBOOK
    ],
    regex.compile('alt\.binaries\.comics', regex.I): [
        CAT_BOOK_COMICS
    ],
    regex.compile('alt\.binaries\.cores', regex.I): [
        CAT_PARENT_BOOK, CAT_PARENT_XXX, CAT_PARENT_GAME, CAT_PARENT_PC, CAT_PARENT_MUSIC, CAT_PARENT_TV,
        CAT_PARENT_MOVIE, CAT_MISC_OTHER
    ],
    regex.compile('alt\.binaries\.lou', regex.I): [
        CAT_PARENT_BOOK, CAT_PARENT_XXX, CAT_PARENT_GAME, CAT_PARENT_PC, CAT_PARENT_TV, CAT_PARENT_MOVIE,
        CAT_PARENT_MUSIC, CAT_MISC_OTHER
    ],
    regex.compile('alt\.binaries\.cd.image|alt\.binaries\.audio\.warez', regex.I): [
        CAT_PARENT_XXX, CAT_PARENT_PC, CAT_PC_0DAY
    ],
    regex.compile('alt\.binaries\.pro\-wrestling', regex.I): [
        CAT_TV_SPORT
    ],
    regex.compile('alt\.binaries\.sony\.psp', regex.I): [
        CAT_GAME_PSP
    ],
    regex.compile('alt\.binaries\.nintendo\.ds|alt\.binaries\.games\.nintendods', regex.I): [
        CAT_GAME_NDS
    ],
    regex.compile('alt\.binaries\.mpeg\.video\.music', regex.I): [
        CAT_MUSIC_VIDEO
    ],
    regex.compile('alt\.binaries\.mac', regex.I): [
        CAT_PC_MAC
    ],
    regex.compile('linux', regex.I): [
        CAT_PC_ISO
    ],
    regex.compile('alt\.binaries\.illuminaten', regex.I): [
        CAT_PARENT_PC, CAT_PARENT_XXX, CAT_PARENT_MUSIC, CAT_PARENT_GAME, CAT_PARENT_TV, CAT_PARENT_MOVIE,
        CAT_MISC_OTHER
    ],
    regex.compile('alt\.binaries\.ipod\.videos\.tvshows', regex.I): [
        CAT_TV_OTHER
    ],
    regex.compile('alt\.binaries\.documentaries', regex.I): [
        CAT_TV_DOCU
    ],
    regex.compile('alt\.binaries\.drummers', regex.I): [
        CAT_PARENT_BOOK, CAT_PARENT_XXX, CAT_PARENT_TV, CAT_PARENT_MOVIE
    ],
    regex.compile('alt\.binaries\.tv\.swedish', regex.I): [
        CAT_TV_FOREIGN
    ],
    regex.compile('alt\.binaries\.tv\.deutsch', regex.I): [
        CAT_TV_FOREIGN
    ],
    regex.compile('alt\.binaries\.erotica\.divx', regex.I): [
        CAT_PARENT_XXX, CAT_XXX_OTHER
    ],
    regex.compile('alt\.binaries\.ghosts', regex.I): [
        CAT_PARENT_BOOK, CAT_PARENT_XXX, CAT_PARENT_PC, CAT_PARENT_MUSIC, CAT_PARENT_GAME, CAT_PARENT_TV,
        CAT_PARENT_MOVIE
    ],
    regex.compile('alt\.binaries\.mom', regex.I): [
        CAT_PARENT_BOOK, CAT_PARENT_XXX, CAT_PARENT_PC, CAT_PARENT_MUSIC, CAT_PARENT_GAME, CAT_PARENT_TV,
        CAT_PARENT_MOVIE, CAT_MISC_OTHER
    ],
    regex.compile('alt\.binaries\.mma|alt\.binaries\.multimedia\.sports', regex.I): [
        CAT_TV_SPORT
    ],
    regex.compile('alt\.binaries\.b4e$', regex.I): [
        CAT_PARENT_PC
    ],
    regex.compile('alt\.binaries\.warez\.smartphone', regex.I): [
        CAT_PARENT_PC
    ],
    regex.compile('alt\.binaries\.warez\.ibm\-pc\.0\-day|alt\.binaries\.warez', regex.I): [
        CAT_PARENT_GAME, CAT_PARENT_BOOK, CAT_PARENT_XXX, CAT_PARENT_MUSIC, CAT_PARENT_PC, CAT_PARENT_TV,
        CAT_PARENT_MOVIE, CAT_PC_0DAY
    ],
    regex.compile('erotica|ijsklontje|kleverig', regex.I): [
        CAT_PARENT_XXX, CAT_XXX_OTHER
    ],
    regex.compile('french', regex.I): [
        CAT_PARENT_XXX, CAT_PARENT_TV, CAT_MOVIE_FOREIGN
    ],
    regex.compile('alt\.binaries\.movies\.xvid|alt\.binaries\.movies\.divx|alt\.binaries\.movies', regex.I): [
        CAT_PARENT_BOOK, CAT_PARENT_GAME, CAT_PARENT_XXX, CAT_PARENT_TV, CAT_PARENT_MOVIE, CAT_PARENT_PC, CAT_MISC_OTHER
    ],
    regex.compile('wmvhd', regex.I): [
        CAT_PARENT_XXX, CAT_PARENT_TV, CAT_PARENT_MOVIE
    ],
    regex.compile('inner\-sanctum', regex.I): [
        CAT_PARENT_XXX, CAT_PARENT_PC, CAT_PARENT_BOOK, CAT_PARENT_MUSIC, CAT_PARENT_TV, CAT_MISC_OTHER
    ],
    regex.compile('alt\.binaries\.worms', regex.I): [
        CAT_PARENT_XXX, CAT_PARENT_TV, CAT_PARENT_MUSIC, CAT_PARENT_MOVIE
    ],
    regex.compile('alt\.binaries\.x264', regex.I): [
        CAT_PARENT_XXX, CAT_PARENT_TV, CAT_PARENT_MOVIE, CAT_MOVIE_OTHER
    ],
    regex.compile('dk\.binaer\.ebooks', regex.I): [
        CAT_PARENT_BOOK, CAT_BOOK_EBOOK
    ],
    regex.compile('dk\.binaer\.film', regex.I): [
        CAT_PARENT_TV, CAT_PARENT_MOVIE, CAT_MISC_OTHER
    ],
    regex.compile('dk\.binaer\.musik', regex.I): [
        CAT_PARENT_MUSIC, CAT_MISC_OTHER
    ],
    regex.compile('alt\.binaries\.(teevee|tv|tvseries)', regex.I): [
        CAT_PARENT_TV, CAT_PARENT_MOVIE, CAT_PARENT_XXX, CAT_MISC_OTHER
    ],
    regex.compile('alt\.binaries\.multimedia$', regex.I): [
        CAT_PARENT_XXX, CAT_PARENT_GAME, CAT_PARENT_MUSIC, CAT_PARENT_TV, CAT_PARENT_PC, CAT_PARENT_MOVIE,
        CAT_MISC_OTHER
    ],
}

"""
This dict holds parent categories, initial regexes and potential actions.

Dict is called in parts (ie. just the. CAT_PARENT_TV section)
In order, the library will try to match the release name against
each parent regex - on success, it will proceed to execute individual
category regex in the order supplied. If there's no match, it'll try the
next parent regex - if none match, the function will return False. This
means that the next category suggested by the group will be tried.

Note that if the array ends on an OTHER subcategory (ie. a category not listed
in category_regex), it'll automatically tag the release as that.

As an example, we attempt to match the release to every type of movie
before failing through to CAT_MOVIE_OTHER if 'xvid' is in the title. In
that example, if it matches no category and doesn't have xvid in the title,
it'll be returned to whatever called it for further processing.
"""
parent_category_regex = {
    CAT_PARENT_TV: collections.OrderedDict([
        (regex.compile('(S?(\d{1,2})\.?(E|X|D)(\d{1,2})[\. _-]+)|(dsr|pdtv|hdtv)[\.\-_]', regex.I), [
            CAT_TV_FOREIGN, CAT_TV_SPORT, CAT_TV_DOCU, CAT_TV_HD, CAT_TV_SD, CAT_TV_OTHER
        ]),
        (regex.compile(
            '( S\d{1,2} |\.S\d{2}\.|\.S\d{2}|s\d{1,2}e\d{1,2}|(\.| |\b|\-)EP\d{1,2}\.|\.E\d{1,2}\.|special.*?HDTV|HDTV.*?special|PDTV|\.\d{3}\.DVDrip|History( |\.|\-)Channel|trollhd|trollsd|HDTV.*?BTL|C4TV|WEB DL|web\.dl|WWE|season \d{1,2}|(?!collectors).*?series|\.TV\.|\.dtv\.|UFC|TNA|staffel|episode|special\.\d{4})',
            regex.I), [
             CAT_TV_FOREIGN, CAT_TV_SPORT, CAT_TV_DOCU, CAT_TV_HD, CAT_TV_SD, CAT_TV_OTHER
        ]),
        (regex.compile('seizoen', regex.I), [
            CAT_TV_FOREIGN
        ]),
        (regex.compile('\[([0-9A-F]{8})\]$', regex.I), [
            CAT_TV_ANIME
        ]),
        (regex.compile('(SD|HD|PD)TV', regex.I), [
            CAT_TV_HD, CAT_TV_SD
        ]),
    ]),
    CAT_PARENT_MOVIE: collections.OrderedDict([
        (regex.compile('[-._ ]AVC|[-._ ]|(B|H)(D|R)RIP|Bluray|BD[-._ ]?(25|50)?|BR|Camrip|[-._ ]\d{4}[-._ ].+(720p|1080p|Cam)|DIVX|[-._ ]DVD[-._ ]|DVD-?(5|9|R|Rip)|Untouched|VHSRip|XVID|[-._ ](DTS|TVrip)[-._ ]', regex.I), [
            CAT_MOVIE_FOREIGN, CAT_MOVIE_SD, CAT_MOVIE_3D, CAT_MOVIE_BLURAY, CAT_MOVIE_HD, CAT_MOVIE_OTHER
        ])
    ]),
    CAT_PARENT_PC: collections.OrderedDict([
        (regex.compile('', regex.I), [
            CAT_PC_MOBILEANDROID, CAT_PC_MOBILEIOS, CAT_PC_MOBILEOTHER, CAT_PC_ISO, CAT_PC_MAC, CAT_PC_GAMES,
            CAT_PC_0DAY
        ])
    ]),
    CAT_PARENT_XXX: collections.OrderedDict([
        (regex.compile(
            '(XXX|Porn|PORNOLATiON|SWE6RUS|masturbation|masturebate|lesbian|Imageset|Squirt|Transsexual|a\.b\.erotica|pictures\.erotica\.anime|cumming|ClubSeventeen|Errotica|Erotica|EroticaX|nymph|sexontv|My_Stepfather_Made_Me|slut|\bwhore\b)',
            regex.I), [
             CAT_XXX_DVD, CAT_XXX_IMAGESET, CAT_XXX_PACK, CAT_XXX_WMV, CAT_XXX_X264, CAT_XXX_XVID, CAT_XXX_OTHER
         ]),
        (regex.compile('^Penthouse', regex.I), [
            CAT_XXX_DVD, CAT_XXX_IMAGESET, CAT_XXX_PACK, CAT_XXX_WMV, CAT_XXX_X264, CAT_XXX_XVID, CAT_XXX_OTHER
        ])
    ]),
    CAT_PARENT_GAME: collections.OrderedDict([
        (regex.compile('', regex.I), [
            CAT_GAME_NDS, CAT_GAME_PS3, CAT_GAME_PSP, CAT_GAME_WIIWARE, CAT_GAME_WIIWARE, CAT_GAME_XBOX360DLC,
            CAT_GAME_XBOX360, CAT_GAME_XBOX
        ])
    ]),
    CAT_PARENT_MUSIC: collections.OrderedDict([
        (regex.compile('', regex.I), [
            CAT_MUSIC_VIDEO, CAT_MUSIC_LOSSLESS, CAT_MUSIC_AUDIOBOOK, CAT_MUSIC_MP3
        ])
    ]),
    CAT_PARENT_BOOK: collections.OrderedDict([
        (regex.compile('', regex.I), [
            CAT_BOOK_COMICS, CAT_BOOK_MAGS, CAT_BOOK_EBOOK
        ])
    ])
}

"""
This contains acceptable regex for each category. Again, it's called in
chunks - one category at a time. Functions will attempt each regex (in
order) until it matches (and returns that category) or fails.

Each element in the array can be three things:
- a Dict
- a Tuple
- or anything else (generally a compiled regex pattern)

--Dicts--
CAT_MOVIE_3D: [
    {
        regex.compile('3D', regex.I): True,
        regex.compile('[\-\. _](H?SBS|OU)([\-\. _]|$)', regex.I): True
    }
]
The dict signifies that both regexes must match their supplied values
for the category to be applied. In this case, both regexes must match.
If we wanted one to match and one to not, we'd mark one as False.

--Lists--
(regex.compile('DVDRIP|XVID.*?AC3|DIVX\-GERMAN', regex.I), False)
In this example, we set the category to fail if the regex matches.
Consider it as: (regex, categorise?)

--Patterns--
CAT_TV_HD: [
    regex.compile('1080|720', regex.I)
],
The majority of entries look like this: match this release to this category
if this regex matches.
"""
category_regex = {
    CAT_TV_FOREIGN: [
        regex.compile(
            '(seizoen|staffel|danish|flemish|(\.| |\b|\-)(HU|NZ)|dutch|Deutsch|nl\.?subbed|nl\.?sub|\.NL|\.ITA|norwegian|swedish|swesub|french|german|spanish)[\.\- \b]',
            regex.I),
        regex.compile(
            '\.des\.(?!moines)|Chinese\.Subbed|vostfr|Hebrew\.Dubbed|\.HEB\.|Nordic|Hebdub|NLSubs|NL\-Subs|NLSub|Deutsch| der |German | NL |staffel|videomann',
            regex.I),
        regex.compile(
            '(danish|flemish|nlvlaams|dutch|nl\.?sub|swedish|swesub|icelandic|finnish|french|truefrench[\.\- ](?:.dtv|dvd|br|bluray|720p|1080p|LD|dvdrip|internal|r5|bdrip|sub|cd\d|dts|dvdr)|german|nl\.?subbed|deutsch|espanol|SLOSiNH|VOSTFR|norwegian|[\.\- ]pl|pldub|norsub|[\.\- ]ITA)[\.\- ]',
            regex.I),
        regex.compile('(french|german)$', regex.I)
    ],
    CAT_TV_SPORT: [
        regex.compile(
            '(f1\.legends|epl|motogp|bellator|strikeforce|the\.ultimate\.fighter|supercup|wtcc|red\.bull.*?race|tour\.de\.france|bundesliga|la\.liga|uefa|EPL|ESPN|WWE\.|WWF\.|WCW\.|MMA\.|UFC\.|(^|[\. ])FIA\.|PGA\.|NFL\.|NCAA\.)',
            regex.I),
        regex.compile(
            'Twenty20|IIHF|wimbledon|Kentucky\.Derby|WBA|Rugby\.|TNA\.|DTM\.|NASCAR|SBK|NBA(\.| )|NHL\.|NRL\.|MLB\.|Playoffs|FIFA\.|Serie.A|netball\.anz|formula1|indycar|Superleague|V8\.Supercars|((19|20)\d{2}.*?olympics?|olympics?.*?(19|20)\d{2})|x(\ |\.|\-)games',
            regex.I),
        regex.compile(
            '(\b|\_|\.| )(Daegu|AFL|La.Vuelta|BMX|Gymnastics|IIHF|NBL|FINA|Drag.Boat|HDNET.Fights|Horse.Racing|WWF|World.Championships|Tor.De.France|Le.Triomphe|Legends.Of.Wrestling)(\b|\_|\.| )',
            regex.I),
        regex.compile(
            '(\b|\_|\.| )(Fighting.Championship|tour.de.france|Boxing|Cycling|world.series|Formula.Renault|FA.Cup|WRC|GP3|WCW|Road.Racing|AMA|MFC|Grand.Prix|Basketball|MLS|Wrestling|World.Cup)(\b|\_|\.| )',
            regex.I),
        regex.compile(
            '(\b|\_|\.| )(Swimming.*?Men|Swimming.*?Women|swimming.*?champion|WEC|World.GP|CFB|Rally.Challenge|Golf|Supercross|WCK|Darts|SPL|Snooker|League Cup|Ligue1|Ligue)(\b|\_|\.| )',
            regex.I),
        regex.compile(
            '(\b|\_|\.| )(Copa.del.rey|League.Cup|Carling.Cup|Cricket|The.Championship|World.Max|KNVB|GP2|Soccer|PGR3|Cage.Contender|US.Open|CFL|Weightlifting|New.Delhi|Euro|WBC)(\b|\_|\.| )',
            regex.I),
        regex.compile('^london(\.| )2012', regex.I)
    ],
    CAT_TV_DOCU: [
        (regex.compile('\-DOCUMENT', regex.I), False),
        regex.compile(
            '(?!.*?S\d{2}.*?)(?!.*?EP?\d{2}.*?)(48\.Hours\.Mystery|Discovery.Channel|BBC|History.Channel|National.Geographic|Nat Geo|Shark.Week)',
            regex.I),
        regex.compile(
            '(?!.*?S\d{2}.*?)(?!.*?EP?\d{2}.*?)((\b|_)(docu|BBC|document|a.and.e|National.geographic|Discovery.Channel|History.Channel|Travel.Channel|Science.Channel|Biography|Modern.Marvels|Inside.story|Hollywood.story|E.True|Documentary)(\b|_))',
            regex.I),
        regex.compile(
            '(?!.*?S\d{2}.*?)(?!.*?EP?\d{2}.*?)((\b|_)(Science.Channel|National.geographi|History.Chanel|Colossal|Discovery.travel|Planet.Science|Animal.Planet|Discovery.Sci|Regents|Discovery.World|Discovery.truth|Discovery.body|Dispatches|Biography|The.Investigator|Private.Life|Footballs.Greatest|Most.Terrifying)(\b|_))',
            regex.I),
        regex.compile('Documentary', regex.I),
    ],
    CAT_TV_HD: [
        regex.compile('1080|720', regex.I)
    ],
    CAT_TV_SD: [
        regex.compile('(SDTV|HDTV|XVID|DIVX|PDTV|WEBDL|WEBRIP|DVDR|DVD-RIP|WEB-DL|x264|dvd)', regex.I)
    ],
    CAT_TV_ANIME: [
        regex.compile('[-._ ]Anime[-._ ]|^\(\[AST\]\s|\[(HorribleSubs|a4e|A-Destiny|AFFTW|Ahodomo|Anxious-He|Ayako-Fansubs|Broken|Chihiro|CoalGirls|CoalGuys|CMS|Commie|CTTS|Darksouls-Subs|Delicio.us|Doki|Doutei|Doremi Fansubs|Elysium|EveTaku|FFF|FFFpeeps|GG|GotWoot?|GotSpeed?|GX_ST|Hadena|Hatsuyuki|KiraKira|Hiryuu|HorribleSubs|Hybrid-Subs|IB|Kira-Fansub|KiteSeekers|m.3.3.w|Mazui|Muteki|Oyatsu|PocketMonsters|Ryuumaru|sage|Saitei|Sayonara-Group|Seto-Otaku|Shimeji|Shikakku|SHiN-gx|Static-Subs|SubDESU (Hentai)|SubSmith|Underwater|UTW|Warui-chan|Whine-Subs|WhyNot Subs|Yibis|Zenyaku|Zorori-Project)\]|\[[0-9A-Z]{8}\]$', regex.I)
    ],
    CAT_MOVIE_FOREIGN: [
        regex.compile(
            '(\.des\.|danish|flemish|dutch|(\.| |\b|\-)(HU|FINA)|Deutsch|nl\.?subbed|nl\.?sub|\.NL|\.ITA|norwegian|swedish|swesub|french|german|spanish)[\.\- |\b]',
            regex.I),
        regex.compile(
            'Chinese\.Subbed|vostfr|Hebrew\.Dubbed|\.Heb\.|Hebdub|NLSubs|NL\-Subs|NLSub|Deutsch| der |German| NL |turkish',
            regex.I),
        regex.compile(
            '(danish|flemish|nlvlaams|dutch|nl\.?sub|swedish|swesub|icelandic|finnish|french|truefrench[\.\- ](?:dvd|br|bluray|720p|1080p|LD|dvdrip|internal|r5|bdrip|sub|cd\d|dts|dvdr)|german|nl\.?subbed|deutsch|espanol|SLOSiNH|VOSTFR|norwegian|[\.\- ]pl|pldub|norsub|[\.\- ]ITA)[\.\- ]',
            regex.I)
    ],
    CAT_MOVIE_SD: [
        regex.compile('(dvdscr|extrascene|dvdrip|\.CAM|dvdr|dvd9|dvd5|[\.\-\ ]ts)[\.\-\ ]', regex.I),
        {
            regex.compile('(divx|xvid|(\.| )r5(\.| ))', regex.I): True,
            regex.compile('(720|1080)', regex.I): False,
        },
        regex.compile('[\.\-\ ]BeyondHD', regex.I)
    ],
    CAT_MOVIE_3D: [
        {
            regex.compile('3D', regex.I): True,
            regex.compile('[\-\. _](H?SBS|OU)([\-\. _]|$)', regex.I): True
        }
    ],
    CAT_MOVIE_HD: [
        regex.compile('x264|AVC|VC\-?1|wmvhd|web\-dl|XvidHD|BRRIP|HDRIP|HDDVD|bddvd|BDRIP|webscr|720p|1080p', regex.I)
    ],
    CAT_MOVIE_BLURAY: [
        regex.compile('bluray|bd?25|bd?50|blu-ray|VC1|VC\-1|AVC|BDREMUX', regex.I)
    ],
    CAT_PC_MOBILEANDROID: [
        regex.compile('Android', regex.I)
    ],
    CAT_PC_MOBILEIOS: [
        regex.compile('(?!.*?Winall.*?)(IPHONE|ITOUCH|IPAD|Ipod)', regex.I)
    ],
    CAT_PC_MOBILEOTHER: [
        regex.compile('COREPDA|symbian|xscale|wm5|wm6|J2ME', regex.I)
    ],
    CAT_PC_0DAY: [
        (regex.compile('DVDRIP|XVID.*?AC3|DIVX\-GERMAN', regex.I), False),
        regex.compile(
            '[\.\-_ ](x32|x64|x86|win64|winnt|win9x|win2k|winxp|winnt2k2003serv|win9xnt|win9xme|winnt2kxp|win2kxp|win2kxp2k3|keygen|regged|keymaker|winall|win32|template|Patch|GAMEGUiDE|unix|irix|solaris|freebsd|hpux|linux|windows|multilingual|software|Pro v\d{1,3})[\.\-_ ]',
            regex.I),
        regex.compile(
            '(?!MDVDR).*?\-Walmart|PHP|\-SUNiSO|\.Portable\.|Adobe|CYGNUS|GERMAN\-|v\d{1,3}.*?Pro|MULTiLANGUAGE|Cracked|lz0|\-BEAN|MultiOS|\-iNViSiBLE|\-SPYRAL|WinAll|Keymaker|Keygen|Lynda\.com|FOSI|Keyfilemaker|DIGERATI|\-UNION|\-DOA|Laxity',
            regex.I)
    ],
    CAT_PC_MAC: [
        regex.compile('osx|os\.x|\.mac\.|MacOSX', regex.I)
    ],
    CAT_PC_ISO: [
        regex.compile('\-DYNAMiCS', regex.I)
    ],
    CAT_PC_GAMES: [
        regex.compile('\-Heist|\-RELOADED|\.GAME\-|\-SKIDROW|PC GAME|FASDOX|v\d{1,3}.*?\-TE|RIP\-unleashed|Razor1911',
                   regex.I)
    ],
    CAT_XXX_X264: [
        regex.compile('x264|720|1080', regex.I)
    ],
    CAT_XXX_XVID: [
        regex.compile('xvid|dvdrip|bdrip|brrip|pornolation|swe6|nympho|detoxication|tesoro|mp4', regex.I)
    ],
    CAT_XXX_WMV: [
        regex.compile('wmv|f4v|flv|mov(?!ie)|mpeg|isom|realmedia|multiformat', regex.I)
    ],
    CAT_XXX_DVD: [
        regex.compile('dvdr[^ip]|dvd5|dvd9', regex.I)
    ],
    CAT_XXX_PACK: [
        regex.compile('[\._](pack)[\.\-_]', regex.I)
    ],
    CAT_XXX_IMAGESET: [
        regex.compile('imageset', regex.I)
    ],
    CAT_GAME_NDS: [
        regex.compile('(\b|\-| |\.)(3DS|NDS)(\b|\-| |\.)', regex.I)
    ],
    CAT_GAME_PS3: [
        regex.compile('PS3\-', regex.I)
    ],
    CAT_GAME_PSP: [
        regex.compile('PSP\-', regex.I)
    ],
    CAT_GAME_WIIWARE: [
        regex.compile('WIIWARE|WII.*?VC|VC.*?WII|WII.*?DLC|DLC.*?WII|WII.*?CONSOLE|CONSOLE.*?WII', regex.I)
    ],
    CAT_GAME_WII: [
        (regex.compile('WWII.*?(?!WII)', regex.I), False),
        regex.compile('Wii', regex.I)
    ],
    CAT_GAME_XBOX360DLC: [
        regex.compile('(DLC.*?xbox360|xbox360.*?DLC|XBLA.*?xbox360|xbox360.*?XBLA)', regex.I)
    ],
    CAT_GAME_XBOX360: [
        regex.compile('XBOX360|x360', regex.I)
    ],
    CAT_GAME_XBOX: [
        regex.compile('XBOX', regex.I)
    ],
    CAT_MUSIC_VIDEO: [
        (regex.compile('(HDTV|S\d{1,2}|\-1920)', regex.I), False),
        regex.compile(
            '\-DDC\-|mbluray|\-VFI|m4vu|retail.*?(?!bluray.*?)x264|\-assass1ns|\-uva|(?!HDTV).*?\-SRP|x264.*?Fray|JESTERS|iuF|MDVDR|(?!HDTV).*?\-BTL|\-WMVA|\-GRMV|\-iLUV|x264\-(19|20)\d{2}',
            regex.I)
    ],
    CAT_MUSIC_AUDIOBOOK: [
        regex.compile('(audiobook|\bABOOK\b)', regex.I)
    ],
    CAT_MUSIC_MP3: [
        (regex.compile('dvdrip|xvid|(x|h)264|720p|1080(i|p)|Bluray', regex.I), False),
        regex.compile(
            '( |\_)Int$|\-(19|20)\d{2}\-[a-z0-9]+$|^V A |Top.*?Charts|Promo CDS|Greatest(\_| )Hits|VBR|NMR|CDM|WEB(STREAM|MP3)|\-DVBC\-|\-CD\-|\-CDR\-|\-TAPE\-|\-Live\-\d{4}|\-DAB\-|\-LINE\-|CDDA|-Bootleg-|WEB\-\d{4}|\-CD\-|(\-|)EP\-|\-FM\-|2cd|\-Vinyl\-|\-SAT\-|\-LP\-|\-DE\-|\-cable\-|Radio\-\d{4}|Radio.*?Live\-\d{4}|\-SBD\-|\d{1,3}(CD|TAPE)',
            regex.I),
        regex.compile('^VA(\-|\_|\ )', regex.I)
    ],
    CAT_MUSIC_LOSSLESS: [
        (regex.compile('dvdrip|xvid|264|720p|1080|Bluray', regex.I), False),
        regex.compile('Lossless|FLAC', regex.I)
    ],
    CAT_BOOK_COMICS: [
        regex.compile('cbr|cbz', regex.I)
    ],
    CAT_BOOK_MAGS: [
        regex.compile('Mag(s|azin|azine|azines)', regex.I)
    ],
    CAT_BOOK_EBOOK: [
        regex.compile('^(.* - (?:\[.*\] -)? .* (?:\[.*\])? \(\w{3,4}\))', regex.I),
        regex.compile('Ebook|E?\-book|\) WW|\[Springer\]| epub|ISBN', regex.I),
        regex.compile('[\(\[](?:(?:html|epub|pdf|mobi|azw|doc).?)+[\)\]]', regex.I)
    ]
}


def get_category_name(id):
    category = db.categories.find_one({'_id': id})
    parent_category = db.categories.find_one({'_id': category['parent_id']})

    return '{} > {}'.format(parent_category['name'], category['name'])


def determine_category(name, group_name=''):
    """Categorise release based on release name and group name."""

    category = ''

    if is_hashed(name):
        category = CAT_MISC_OTHER
    else:
        if group_name:
            category = check_group_category(name, group_name)

    if not category:
        for parent_category in parent_category_regex.keys():
            category = check_parent_category(name, parent_category)
            if category:
                break

    if not category:
        category = CAT_MISC_OTHER

    log.info('category: ({}) [{}]: {} ({})'.format(
        group_name,
        name,
        get_category_name(category),
        category
    ))
    return category


def is_hashed(name):
    """Check if the release name is a hash."""
    return not regex.match('( |\.|\-)', name, regex.I) and regex.match('^[a-f0-9]{16,}$', name, regex.I)


def check_group_category(name, group_name):
    """Check the group name against our list and
    take appropriate action - match against categories
    as dictated in the dicts above."""
    for regex, actions in group_regex.items():
        if regex.match(group_name):
            for action in actions:
                if action in parent_category_regex.keys():
                    category = check_parent_category(name, action)
                    if category:
                        return category
                elif action in category_regex.keys():
                    return action


def check_parent_category(name, parent_category):
    """Check the release against a single parent category, which will
    call appropriate sub-category checks."""

    for test, actions in parent_category_regex[parent_category].items():
        if test.search(name) is not None:
            for category in actions:
                if category in category_regex:
                    if check_single_category(name, category):
                        return category
                else:
                    return category

    return False


def check_single_category(name, category):
    """Check release against a single category."""

    log.info('checking {}'.format(category))

    for regex in category_regex[category]:
        if isinstance(regex, collections.Mapping):
            if all(bool(expr.search(name)) == expected for expr, expected in regex.items()):
                return True
        elif isinstance(regex, tuple):
            (r, ret) = regex
            if r.search(name) is not None:
                return ret
        else:
            if regex.search(name) is not None:
                return True
    return False

########NEW FILE########
__FILENAME__ = db
import pymongo
import gridfs
import config


class DB:
    def __init__(self):
        self.mongo = None
        self.gridfs = None
        self.config = config.db
        self.connect()

    def connect(self):
        """Create a MongoDB connection for use."""
        #TODO: txMongo
        self.mongo = pymongo.MongoClient(self.config['host'], self.config['port'])

    def db(self):
        """Return the database instance."""
        return self.mongo[self.config['db']]

    def fs(self):
        """Return the GridFS instance for file saves."""
        return gridfs.GridFS(self.mongo[self.config['db']])

    def close(self):
        """Close the MongoDB connection."""
        self.mongo.close()


base = DB()

# allow for "from pynab.db import db, fs"
db = base.db()
fs = base.fs()
########NEW FILE########
__FILENAME__ = groups
from pynab import log
from pynab.db import db
from pynab.server import Server
from pynab import parts
import config

MESSAGE_LIMIT = config.scan.get('message_scan_limit', 20000)


def backfill(group_name, date=None):
    log.info('group: {}: backfilling group'.format(group_name))

    server = Server()
    _, count, first, last, _ = server.group(group_name)

    if date:
        target_article = server.day_to_post(group_name, server.days_old(date))
    else:
        target_article = server.day_to_post(group_name, config.scan.get('backfill_days', 10))

    group = db.groups.find_one({'name': group_name})
    if group:
        # if the group hasn't been updated before, quit
        if not group['first']:
            log.error('group: {}: run a normal update prior to backfilling'.format(group_name))
            if server.connection:
                server.connection.quit()
            return False

        # if the first article we have is lower than the target
        if target_article >= group['first']:
            log.info('group: {}: Nothing to do, we already have the target post.'.format(group_name))
            if server.connection:
                server.connection.quit()
            return True

        # or if the target is below the server's first
        if target_article < first:
            target_article = first

        total = group['first'] - target_article
        end = group['first'] - 1
        start = end - MESSAGE_LIMIT + 1
        if target_article > start:
            start = target_article

        retries = 0
        while True:
            messages = server.scan(group_name, start, end)

            if messages:
                if parts.save_all(messages):
                    db.groups.update({
                                         '_id': group['_id']
                                     },
                                     {
                                         '$set': {
                                             'first': start
                                         }
                                     })
                    retries = 0
                else:
                    log.error('group: {}: failed while saving parts'.format(group_name))
                    if server.connection:
                        server.connection.quit()
                    return False
            else:
                    log.error('group: {}: problem updating group - trying again'.format(group_name))
                    retries += 1
                    # keep trying the same block 3 times, then skip
                    if retries <= 3:
                        continue

            if start == target_article:
                if server.connection:
                    server.connection.quit()
                return True
            else:
                end = start - 1
                start = end - MESSAGE_LIMIT + 1
                if target_article > start:
                    start = target_article
    else:
        log.error('group: {}: group doesn\'t exist in db.'.format(group_name))
        if server.connection:
            server.connection.quit()
        return False


def update(group_name):
    log.info('group: {}: updating group'.format(group_name))

    server = Server()
    _, count, first, last, _ = server.group(group_name)

    group = db.groups.find_one({'name': group_name})
    if group:
        # if the group has been scanned before
        if group['last']:
            # pick up where we left off
            start = group['last'] + 1

            # if our last article is newer than the server's, something's wrong
            if last < group['last']:
                log.error('group: {}: last article {:d} on server is older than the local {:d}'.format(group_name, last,
                                                                                                group['last']))
                if server.connection:
                    try:
                        server.connection.quit()
                    except:
                        pass
                return False
        else:
            # otherwise, start from x days old
            start = server.day_to_post(group_name, config.scan.get('new_group_scan_days', 5))
            if not start:
                log.error('group: {}: couldn\'t determine a start point for group'.format(group_name))
                if server.connection:
                    try:
                        server.connection.quit()
                    except:
                        pass
                return False
            else:
                db.groups.update({
                                     '_id': group['_id']
                                 },
                                 {
                                     '$set': {
                                         'first': start
                                     }
                                 })

        # either way, we're going upwards so end is the last available
        end = last

        # if total > 0, we have new parts
        total = end - start + 1

        start_date = server.post_date(group_name, start)
        end_date = server.post_date(group_name, end)

        if start_date and end_date:
            total_date = end_date - start_date

            log.info('group: {}: pulling {} - {} ({}d, {}h, {}m)'.format(
                group_name,
                start, end,
                total_date.days,
                total_date.seconds // 3600,
                (total_date.seconds // 60) % 60
            ))
        else:
            log.info('group: {}: pulling {} - {}'.format(group_name, start, end))

        if total > 0:
            if not group['last']:
                log.info('group: {}: starting new group with {:d} days and {:d} new parts'
                    .format(group_name, config.scan.get('new_group_scan_days', 5), total))
            else:
                log.info('group: {}: group has {:d} new parts.'.format(group_name, total))

            retries = 0
            # until we're finished, loop
            while True:
                # break the load into segments
                if total > MESSAGE_LIMIT:
                    if start + MESSAGE_LIMIT > last:
                        end = last
                    else:
                        end = start + MESSAGE_LIMIT - 1

                messages = server.scan(group_name, start, end)
                if messages:
                    if parts.save_all(messages):
                        db.groups.update({
                                             '_id': group['_id']
                                         },
                                         {
                                             '$set': {
                                                 'last': end
                                             }
                                         })
                        retries = 0
                    else:
                        log.error('group: {}: failed while saving parts'.format(group_name))
                        if server.connection:
                            try:
                                server.connection.quit()
                            except:
                                pass
                        return False

                if end == last:
                    if server.connection:
                        try:
                            server.connection.quit()
                        except:
                            pass
                    return True
                else:
                    start = end + 1
        else:
            log.info('group: {}: no new messages'.format(group_name))
            if server.connection:
                server.connection.quit()
            return True
    else:
        log.error('group: {}: no group in db'.format(group_name))
        if server.connection:
            server.connection.quit()
        return False
########NEW FILE########
__FILENAME__ = imdb
import regex
import unicodedata
import difflib
import datetime
import pymongo
import requests
import pytz

from pynab.db import db
from pynab import log
import config


OMDB_SEARCH_URL = 'http://www.omdbapi.com/?s='
OMDB_DETAIL_URL = 'http://www.omdbapi.com/?i='


def process_release(release, online=True):
    name, year = parse_movie(release['search_name'])
    if name and year:
        method = 'local'
        imdb = db.imdb.find_one({'name': clean_name(name), 'year': year})
        if not imdb and online:
            method = 'online'
            movie = search(clean_name(name), year)
            if movie and movie['Type'] == 'movie':
                db.imdb.update(
                    {'_id': movie['imdbID']},
                    {
                        '$set': {
                            'name': movie['Title'],
                            'year': movie['Year']
                        }
                    },
                    upsert=True
                )
                imdb = db.imdb.find_one({'_id': movie['imdbID']})

        if imdb:
            log.info('[{}] - [{}] - imdb added: {}'.format(
                release['_id'],
                release['search_name'],
                method
            ))
            db.releases.update({'_id': release['_id']}, {
                '$set': {
                    'imdb': imdb
                }
            })
        elif not imdb and online:
            log.warning('[{}] - [{}] - imdb not found: online'.format(
                release['_id'],
                release['search_name']
            ))
            db.releases.update({'_id': release['_id']}, {
                '$set': {
                    'imdb': {
                        'attempted': datetime.datetime.now(pytz.utc)
                    }
                }
            })
        else:
            log.warning('[{}] - [{}] - imdb not found: local'.format(
                release['_id'],
                release['search_name']
            ))
    else:
        log.error('[{}] - [{}] - imdb not found: no suitable regex for movie name'.format(
            release['_id'],
            release['search_name']
        ))
        db.releases.update({'_id': release['_id']}, {
            '$set': {
                'imdb': {
                    'possible': False
                }
            }
        })


def process(limit=100, online=True):
    """Process movies without imdb data and append said data."""
    expiry = datetime.datetime.now(pytz.utc) - datetime.timedelta(config.postprocess.get('fetch_blacklist_duration', 7))

    query = {
        'imdb._id': {'$exists': False},
        'category.parent_id': 2000,
    }

    if online:
        query.update({
            'imdb.possible': {'$exists': False},
            '$or': [
                {'imdb.attempted': {'$exists': False}},
                {'imdb.attempted': {'$lte': expiry}}
            ]
        })
    for release in db.releases.find(query).limit(limit).sort('posted', pymongo.DESCENDING).batch_size(50):
        process_release(release, online)


def search(name, year):
    """Search OMDB for a movie and return the IMDB ID."""

    # if we managed to parse the year from the name
    # include it, since it'll narrow results
    if year:
        year_query = '&y={}'.format(year.replace('(', '').replace(')', ''))
    else:
        year_query = ''

    r = requests.get(OMDB_SEARCH_URL + name + year_query)
    try:
        data = r.json()
    except:
        log.critical('There was a problem accessing the IMDB API page.')
        return None

    if 'Search' in data:
        for movie in data['Search']:
            # doublecheck, but the api should've searched properly
            ratio = difflib.SequenceMatcher(None, clean_name(name), clean_name(movie['Title'])).ratio()
            if ratio > 0.8 and year == movie['Year'] and movie['Type'] == 'movie':
                return movie


def get_details(id):
    r = requests.get(OMDB_DETAIL_URL + id)
    data = r.json()

    if 'Response' in data:
        imdb = {
            '_id': data['imdbID'],
            'title': data['Title'],
            'year': data['Year'],
            'genre': data['Genre'].split(',')
        }
        return imdb
    else:
        return None


def parse_movie(search_name):
    """Parses a movie name into name / year."""
    result = regex.search('^(?P<name>.*)[\.\-_\( ](?P<year>19\d{2}|20\d{2})', search_name, regex.I)
    if result:
        result = result.groupdict()
        if 'year' not in result:
            result = regex.search(
                '^(?P<name>.*)[\.\-_ ](?:dvdrip|bdrip|brrip|bluray|hdtv|divx|xvid|proper|repack|real\.proper|sub\.?fix|sub\.?pack|ac3d|unrated|1080i|1080p|720p|810p)',
                search_name, regex.I)
            if result:
                result = result.groupdict()

        if 'name' in result:
            name = regex.sub('\(.*?\)|\.|_', ' ', result['name'])
            if 'year' in result:
                year = result['year']
            else:
                year = ''
            return name, year

    return None, None


def clean_name(name):
    """Cleans a show name for searching (against omdb)."""
    name = unicodedata.normalize('NFKD', name)
    name = regex.sub('[._\-]', ' ', name)
    name = regex.sub('[\':!"#*’,()?$&]', '', name)
    return name
########NEW FILE########
__FILENAME__ = nfos
import gzip
import pymongo
import regex

import pynab.nzbs
import pynab.util

from pynab import log
from pynab.db import db, fs
from pynab.server import Server

NFO_MAX_FILESIZE = 50000

NFO_REGEX = [
    regex.compile('((?>\w+[.\-_])+(?:\w+-\d*[a-zA-Z][a-zA-Z0-9]*))', regex.I),

]

def attempt_parse(nfo):
    potential_names = []

    for regex in NFO_REGEX:
        result = regex.search(nfo)
        if result:
            potential_names.append(result.group(0))

    return potential_names


def get(nfo_id):
    """Retrieves and un-gzips an NFO from GridFS."""
    if nfo_id:
        return gzip.decompress(fs.get(nfo_id).read())
    else:
        return None


def process(limit=5, category=0):
    """Process releases for NFO parts and download them."""

    with Server() as server:
        query = {'nfo': None}
        if category:
            query['category._id'] = int(category)

        for release in db.releases.find(query).limit(limit).sort('posted', pymongo.DESCENDING).batch_size(50):
            nzb = pynab.nzbs.get_nzb_dict(release['nzb'])

            if nzb:
                nfos = []
                if nzb['nfos']:
                    for nfo in nzb['nfos']:
                        if not isinstance(nfo['segments']['segment'], list):
                            nfo['segments']['segment'] = [nfo['segments']['segment'], ]
                        for part in nfo['segments']['segment']:
                            if int(part['@bytes']) > NFO_MAX_FILESIZE:
                                continue
                            nfos.append(part)

                if nfos:
                    for nfo in nfos:
                        try:
                            article = server.get(release['group']['name'], [nfo['#text'], ])
                        except:
                            article = None

                        if article:
                            data = gzip.compress(article.encode('utf-8'))
                            nfo_file = fs.put(data, filename='.'.join([release['name'], 'nfo', 'gz']))

                            if nfo_file:
                                db.releases.update({'_id': release['_id']}, {
                                    '$set': {
                                        'nfo': nfo_file
                                    }
                                })

                                log.info('nfo: [{}] - [{}] - nfo added'.format(
                                    release['_id'],
                                    release['search_name']
                                ))
                                break
                        else:
                            log.warning('nfo: [{}] - [{}] - nfo unavailable'.format(
                                release['_id'],
                                release['search_name']
                            ))
                            continue
                else:
                    log.warning('nfo: [{}] - [{}] - no nfo in release'.format(
                        release['_id'],
                        release['search_name']
                    ))
                    db.releases.update({'_id': release['_id']}, {
                        '$set': {
                            'nfo': False
                        }
                    })
########NEW FILE########
__FILENAME__ = nzbs
import gzip
import sys
import os
import xml.etree.cElementTree as cet
import hashlib
import uuid
import datetime
import regex

import pytz
import xmltodict
from mako.template import Template
from mako import exceptions

from pynab.db import fs, db
from pynab import log, root_dir
import pynab

nfo_regex = '[ "\(\[].*?\.(nfo|ofn)[ "\)\]]'
rar_regex = '.*\W(?:part0*1|(?!part\d+)[^.]+)\.(rar|001)[ "\)\]]'
rar_part_regex = '\.(rar|r\d{2,3})(?!\.)'
metadata_regex = '\.(par2|vol\d+\+|sfv|nzb)'
par2_regex = '\.par2(?!\.)'
par_vol_regex = 'vol\d+\+'
zip_regex = '\.zip(?!\.)'


def get_nzb_dict(nzb_id):
    """Returns a JSON-like Python dict of NZB contents, including extra information
    such as a list of any nfos/rars that the NZB references."""
    data = xmltodict.parse(gzip.decompress(fs.get(nzb_id).read()))

    nfos = []
    rars = []
    pars = []
    rar_count = 0
    par_count = 0
    zip_count = 0

    if 'file' not in data['nzb']:
        return None

    if not isinstance(data['nzb']['file'], list):
        data['nzb']['file'] = [data['nzb']['file'], ]

    for part in data['nzb']['file']:
        if regex.search(rar_part_regex, part['@subject'], regex.I):
            rar_count += 1
        if regex.search(nfo_regex, part['@subject'], regex.I) and not regex.search(metadata_regex, part['@subject'], regex.I):
            nfos.append(part)
        if regex.search(rar_regex, part['@subject'], regex.I) and not regex.search(metadata_regex, part['@subject'], regex.I):
            rars.append(part)
        if regex.search(par2_regex, part['@subject'], regex.I):
            par_count += 1
            if not regex.search(par_vol_regex, part['@subject'], regex.I):
                pars.append(part)
        if regex.search(zip_regex, part['@subject'], regex.I) and not regex.search(metadata_regex, part['@subject'], regex.I):
            zip_count += 1

    data['nfos'] = nfos
    data['rars'] = rars
    data['pars'] = pars
    data['rar_count'] = rar_count
    data['par_count'] = par_count
    data['zip_count'] = zip_count

    return data


def create(gid, name, binary):
    """Create the NZB, store it in GridFS and return the ID
    to be linked to the release."""
    if binary['category_id']:
        category = db.categories.find_one({'id': binary['category_id']})
    else:
        category = None

    xml = ''
    try:
        tpl = Template(filename=os.path.join(root_dir, 'templates/nzb.mako'))
        xml = tpl.render(version=pynab.__version__, name=name, category=category, binary=binary)
    except:
        log.error('nzb: failed to create NZB: {0}'.format(exceptions.text_error_template().render()))
        return None

    data = gzip.compress(xml.encode('utf-8'))
    return fs.put(data, filename='.'.join([gid, 'nzb', 'gz'])), sys.getsizeof(data, 0)


def import_nzb(filepath, quick=True):
    """Import an NZB and directly load it into releases."""
    file, ext = os.path.splitext(filepath)

    if ext == '.gz':
        f = gzip.open(filepath, 'rt', encoding='utf-8', errors='ignore')
    else:
        f = open(filepath, 'r', encoding='utf-8', errors='ignore')

    if quick:
        release = {'added': pytz.utc.localize(datetime.datetime.now()), 'size': None, 'spotnab_id': None,
                   'completion': None, 'grabs': 0, 'passworded': None, 'file_count': None, 'tvrage': None,
                   'tvdb': None, 'imdb': None, 'nfo': None, 'tv': None, 'total_parts': 0}

        try:
            for event, elem in cet.iterparse(f):
                if 'meta' in elem.tag:
                    release[elem.attrib['type']] = elem.text
                if 'file' in elem.tag:
                    release['total_parts'] += 1
                    release['posted'] = elem.get('date')
                    release['posted_by'] = elem.get('poster')
                if 'group' in elem.tag and 'groups' not in elem.tag:
                    release['group_name'] = elem.text
        except:
            log.error('nzb: error parsing NZB files: file appears to be corrupt.')
            return False

        if 'name' not in release:
            log.error('nzb: failed to import nzb: {0}'.format(filepath))
            return False

        # check that it doesn't exist first
        r = db.releases.find_one({'name': release['name']})
        if not r:
            release['id'] = hashlib.md5(uuid.uuid1().bytes).hexdigest()
            release['search_name'] = release['name']

            release['status'] = 2

            if 'posted' in release:
                release['posted'] = datetime.datetime.fromtimestamp(int(release['posted']), pytz.utc)
            else:
                release['posted'] = None

            if 'category' in release:
                parent, child = release['category'].split(' > ')

                parent_category = db.categories.find_one({'name': parent})
                if parent_category:
                    child_category = db.categories.find_one({'name': child, 'parent_id': parent_category['_id']})

                    if child_category:
                        release['category'] = child_category
                        release['category']['parent'] = parent_category
                    else:
                        release['category'] = None
                else:
                    release['category'] = None
            else:
                release['category'] = None

            # make sure the release belongs to a group we have in our db
            if 'group_name' in release:
                group = db.groups.find_one({'name': release['group_name']}, {'name': 1})
                if not group:
                    log.error('nzb: could not add release - group {0} doesn\'t exist.'.format(release['group_name']))
                    return False
                release['group'] = group
                del release['group_name']

            # rebuild the nzb, gzipped
            f.seek(0)
            data = gzip.compress(f.read().encode('utf-8'))
            release['nzb'] = fs.put(data, filename='.'.join([release['id'], 'nzb', 'gz']))
            release['nzb_size'] = sys.getsizeof(data, 0)

            try:
                db.releases.insert(release)
            except:
                log.error('nzb: problem saving release: {0}'.format(release))
                return False
            f.close()

            return True
        else:
            log.error('nzb: release already exists: {0}'.format(release['name']))
            return False


########NEW FILE########
__FILENAME__ = parts
import regex

import pymongo.errors

from pynab.db import db
from pynab import log


def save(part):
    """Save a single part and segment set to the DB.
    Probably really slow. Some Mongo updates would help
    a lot with this.
    ---
    Note: no longer as slow.
    """
    # because for some reason we can't do a batch find_and_modify
    # upsert into nested embedded dicts
    # i'm probably doing it wrong
    try:
        existing_part = db.parts.find_one({'subject': part['subject']})
        if existing_part:
            existing_part['segments'].update(part['segments'])
            db.parts.update({'_id': existing_part['_id']}, {
                '$set': {
                    'segments': existing_part['segments']
                }
            })
        else:
            db.parts.insert({
                'subject': part['subject'],
                'group_name': part['group_name'],
                'posted': part['posted'],
                'posted_by': part['posted_by'],
                'xref': part['xref'],
                'total_segments': part['total_segments'],
                'segments': part['segments']
            })

    except pymongo.errors.PyMongoError as e:
        raise e


def save_all(parts):
    """Save a set of parts to the DB, in a batch if possible."""

    # if possible, do a quick batch insert
    # rarely possible!
    # TODO: filter this more - batch import if first set in group?
    try:
        if db.parts.count() == 0:
            db.parts.insert([value for key, value in parts.items()])
            return True
        else:
            # otherwise, it's going to be slow
            for key, part in parts.items():
                save(part)
            return True
    except pymongo.errors.PyMongoError as e:
        log.error('parts: could not write to db: {0}'.format(e))
        return False


def is_blacklisted(subject, group_name):
    #log.debug('{0}: Checking {1} against active blacklists...'.format(group_name, subject))
    blacklists = db.blacklists.find({'status': 1})
    for blacklist in blacklists:
        if regex.search(blacklist['group_name'], group_name):
            # too spammy
            #log.debug('{0}: Checking blacklist {1}...'.format(group_name, blacklist['regex']))
            if regex.search(blacklist['regex'], subject):
                return True
    return False
########NEW FILE########
__FILENAME__ = rars
import tempfile
import os
import regex
import shutil
import subprocess
import pymongo

import lib.rar
from pynab import log
from pynab.db import db
import pynab.nzbs
import pynab.releases
import pynab.util
from pynab.server import Server
import config


MAYBE_PASSWORDED_REGEX = regex.compile('\.(ace|cab|tar|gz|url)$', regex.I)
PASSWORDED_REGEX = regex.compile('password\.url', regex.I)


def attempt_parse(file):
    name = ''
    match = pynab.util.Match()

    # Directory\Title.Year.Format.Group.mkv
    if match.match('(?<=\\\).*?BLURAY.(1080|720)P.*?KNORLOADING(?=\.MKV)', file, regex.I):
        name = match.match_obj.group(0)
    # Title.Format.ReleaseGroup.mkv
    elif match.match('.*?(1080|720)(|P).(SON)', file, regex.I):
        name = match.match_obj.group(0).replace('_', '.')
    # EBook
    elif match.match('.*\.(epub|mobi|azw3|pdf|prc)', file, regex.I):
        name = match.match_obj.group(0)\
            .replace('.epub', '')\
            .replace('.mobi', '')\
            .replace('.azw3', '')\
            .replace('.pdf', '')\
            .replace('.prc', '')
    # scene format generic
    elif match.match('([a-z0-9\'\-\.\_\(\)\+\ ]+\-[a-z0-9\'\-\.\_\(\)\ ]+)(.*?\\\\.*?|)\.(?:\w{3,4})$', file, regex.I):
        gen_s = match.match_obj.group(0)
        # scene format no folder
        if match.match('^([a-z0-9\.\_\- ]+\-[a-z0-9\_]+)(\\\\|)$', gen_s, regex.I):
            if len(match.match_obj.group(1)) > 15:
                name = match.match_obj.group(1)
        # check if file is in a folder, and use folder if so
        elif match.match('^(.*?\\\\)(.*?\\\\|)(.*?)$', gen_s, regex.I):
            folder_name = match.match_obj.group(1)
            folder_2_name = match.match_obj.group(2)
            if match.match('^([a-z0-9\.\_\- ]+\-[a-z0-9\_]+)(\\\\|)$', folder_name, regex.I):
                name = match.match_obj.group(1)
            elif match.match('(?!UTC)([a-z0-9]+[a-z0-9\.\_\- \'\)\(]+(\d{4}|HDTV).*?\-[a-z0-9]+)', folder_name, regex.I):
                name = match.match_obj.group(1)
            elif match.match('^([a-z0-9\.\_\- ]+\-[a-z0-9\_]+)(\\\\|)$', folder_2_name, regex.I):
                name = match.match_obj.group(1)
            elif match.match('^([a-z0-9\.\_\- ]+\-(?:.+)\(html\))\\\\', folder_name, regex.I):
                name = match.match_obj.group(1)
        elif match.match('(?!UTC)([a-z0-9]+[a-z0-9\.\_\- \'\)\(]+(\d{4}|HDTV).*?\-[a-z0-9]+)', gen_s, regex.I):
            name = match.match_obj.group(1)

    if not name:
        name = file

    return name


def check_rar(filename):
    """Determines whether a rar is passworded or not.
    Returns either a list of files (if the file is a rar and unpassworded),
    False if it's not a RAR, and True if it's a passworded/encrypted RAR.
    """
    try:
        rar = lib.rar.RarFile(filename)
    except:
        # wasn't a rar
        raise lib.rar.BadRarFile

    if rar:
        # was a rar! check for passworded inner rars
        if any([r.is_encrypted for r in rar.infolist()]):
            return False
        else:
            return rar.infolist()
    else:
        # probably an encrypted rar!
        return False


def get_rar_info(server, group_name, messages):
    try:
        data = server.get(group_name, messages)
    except:
        data = None

    if data:
        # if we got the requested articles, save them to a temp rar
        t = None
        with tempfile.NamedTemporaryFile('wb', suffix='.rar', delete=False) as t:
            t.write(data.encode('ISO-8859-1'))
            t.flush()

        try:
            files = check_rar(t.name)
        except lib.rar.BadRarFile:
            os.remove(t.name)
            return None

        # build a summary to return

        info = {
            'files.count': 0,
            'files.size': 0,
            'files.names': []
        }

        passworded = False
        if files:
            info = {
                'files.count': len(files),
                'files.size': sum([r.file_size for r in files]),
                'files.names': [r.filename for r in files]
            }

            unrar_path = config.postprocess.get('unrar_path', '/usr/bin/unrar')
            if not (unrar_path and os.path.isfile(unrar_path) and os.access(unrar_path, os.X_OK)):
                log.error('rar: skipping archive decompression because unrar_path is not set or incorrect')
                log.error('rar: if the rar is not password protected, but contains an inner archive that is, we will not know')
            else:
                # make a tempdir to extract rar to
                tmp_dir = tempfile.mkdtemp()
                exe = [
                    '"{}"'.format(unrar_path),
                    'e', '-ai', '-ep', '-r', '-kb',
                    '-c-', '-id', '-p-', '-y', '-inul',
                    '"{}"'.format(t.name),
                    '"{}"'.format(tmp_dir)
                ]
    
                try:
                    subprocess.check_call(' '.join(exe), stderr=subprocess.STDOUT, shell=True)
                except subprocess.CalledProcessError as cpe:
                    log.debug('rar: issue while extracting rar: {}: {} {}'.format(cpe.cmd, cpe.returncode, cpe.output))

                inner_passwords = []
                for file in files:
                    fpath = os.path.join(tmp_dir, file.filename)
                    try:
                        inner_files = check_rar(fpath)
                    except lib.rar.BadRarFile:
                        continue
    
                    if inner_files:
                        inner_passwords += [r.is_encrypted for r in inner_files]
                    else:
                        passworded = True
                        break
    
                if not passworded:
                    passworded = any(inner_passwords)

                os.remove(t.name)
                shutil.rmtree(tmp_dir)
        else:
            passworded = True
            os.remove(t.name)

        info['passworded'] = passworded

        return info


def check_release_files(server, group_name, nzb):
    """Retrieves rar metadata for release files."""

    for rar in nzb['rars']:
        messages = []
        if not rar['segments']:
            continue

        if not isinstance(rar['segments']['segment'], list):
            rar['segments']['segment'] = [rar['segments']['segment'], ]

        for s in rar['segments']['segment']:
            messages.append(s['#text'])
            break

        if messages:
            info = get_rar_info(server, group_name, messages)

            if info and not info['passworded']:
                passworded = False
                for file in info['files.names']:
                    result = MAYBE_PASSWORDED_REGEX.search(file)
                    if result:
                        passworded = 'potentially'
                        break

                    result = PASSWORDED_REGEX.search(file)
                    if result:
                        passworded = True
                        break

                if passworded:
                    info['passworded'] = passworded

            return info

    return None


def process(limit=20, category=0):
    """Processes release rarfiles to check for passwords and filecounts."""

    with Server() as server:
        query = {'passworded': None}
        if category:
            query['category._id'] = int(category)
        for release in db.releases.find(query).limit(limit).sort('posted', pymongo.DESCENDING).batch_size(50):
            nzb = pynab.nzbs.get_nzb_dict(release['nzb'])

            if nzb and 'rars' in nzb:
                info = check_release_files(server, release['group']['name'], nzb)
                if info:
                    log.info('[{}] - [{}] - file info: added'.format(
                        release['_id'],
                        release['search_name']
                    ))
                    db.releases.update({'_id': release['_id']}, {
                        '$set': {
                            'files.count': info['files.count'],
                            'files.size': info['files.size'],
                            'files.names': info['files.names'],
                            'passworded': info['passworded']
                        }
                    })

                    continue

            log.warning('rar: [{}] - [{}] - file info: no rars in release'.format(
                release['_id'],
                release['search_name']
            ))
            db.releases.update({'_id': release['_id']}, {
                '$set': {
                    'files.count': 0,
                    'files.size': 0,
                    'files.names': [],
                    'passworded': 'unknown'
                }
            })

########NEW FILE########
__FILENAME__ = releases
import datetime
import time
import hashlib
import uuid
import regex
import math

import pytz
from bson.code import Code

from pynab import log
from pynab.db import db
import config
import pynab.nzbs
import pynab.categories
import pynab.nfos
import pynab.util
import pynab.rars


def strip_req(release):
    """Strips REQ IDs out of releases and cleans them up so they can be properly matched
    in post-processing."""
    regexes = [
        regex.compile('^a\.b\.mmEFNet - REQ (?P<reqid>.+) - (?P<name>.*)', regex.I)
    ]

    for r in regexes:
        result = r.search(release['search_name'])
        if result:
            result_dict = result.groupdict()
            if 'name' in result_dict and 'reqid' in result_dict:
                db.releases.update({'_id': release['_id']}, {
                    '$set': {
                        'search_name': result_dict['name'],
                        'req_id': result_dict['reqid']
                    }
                })
                return


def names_from_nfos(release):
    """Attempt to grab a release name from its NFO."""
    nfo = pynab.nfos.get(release['nfo']).decode('ascii', 'ignore')
    if nfo:
        return pynab.nfos.attempt_parse(nfo)
    else:
        return []


def names_from_files(release):
    """Attempt to grab a release name from filenames inside the release."""
    if release['files']['names']:
        potential_names = []
        for file in release['files']['names']:
            name = pynab.rars.attempt_parse(file)
            if name:
                potential_names.append(name)

        return potential_names
    else:
        return []


def discover_name(release):
    """Attempts to fix a release name by nfo or filelist."""
    potential_names = [release['search_name'],]

    if 'files' in release:
        potential_names += names_from_files(release)

    if release['nfo']:
        potential_names += names_from_nfos(release)

    if len(potential_names) > 1:
        old_category = release['category']['_id']
        calculated_old_category = pynab.categories.determine_category(release['search_name'])

        for name in potential_names:
            new_category = pynab.categories.determine_category(name)

            # the release may already be categorised by the group it came from
            # so if we check the name and it doesn't fit a category, it's probably
            # a shitty name
            if (math.floor(calculated_old_category / 1000) * 1000) == pynab.categories.CAT_PARENT_MISC:
                # sometimes the group categorisation is better than name-based
                # so check if they're in the same parent and that parent isn't misc
                if (math.floor(new_category / 1000) * 1000) == pynab.categories.CAT_PARENT_MISC:
                    # ignore this name, since it's apparently gibberish
                    continue
                else:
                    if (math.floor(new_category / 1000) * 1000) == (math.floor(old_category / 1000) * 1000)\
                            or (math.floor(old_category / 1000) * 1000) == pynab.categories.CAT_PARENT_MISC:
                        # if they're the same parent, use the new category
                        # or, if the old category was misc>other, fix it
                        search_name = name
                        category_id = new_category

                        log.info('release: [{}] - [{}] - rename: {} ({} -> {} -> {})'.format(
                            release['_id'],
                            release['search_name'],
                            search_name,
                            old_category,
                            calculated_old_category,
                            category_id
                        ))

                        return search_name, category_id
                    else:
                        # if they're not the same parent and they're not misc, ignore
                        continue
            else:
                # the old name was apparently fine
                log.info('release: [{}] - [{}] - old name was fine'.format(
                    release['_id'],
                    release['search_name']
                ))
                return True, False

    log.info('release: [{}] - [{}] - no good name candidates'.format(
        release['_id'],
        release['search_name']
    ))
    return None, None


def clean_release_name(name):
    """Strip dirty characters out of release names. The API
    will match against clean names."""
    chars = ['#', '@', '$', '%', '^', '§', '¨', '©', 'Ö']
    for c in chars:
        name = name.replace(c, '')
    return name.replace('_', ' ')


def process():
    """Helper function to begin processing binaries. Checks
    for 100% completion and will create NZBs/releases for
    each complete release. Will also categorise releases,
    and delete old binaries."""

    binary_count = 0
    added_count = 0

    start = time.time()

    # mapreduce isn't really supposed to be run in real-time
    # then again, processing releases isn't a real-time op
    mapper = Code("""
        function() {
            var complete = true;
            var total_segments = 0;
            var available_segments = 0;

            parts_length = Object.keys(this.parts).length;

            // we should have at least one segment from each part
            if (parts_length >= this.total_parts) {
                for (var key in this.parts) {
                    segments_length = Object.keys(this.parts[key].segments).length;
                    available_segments += segments_length;

                    total_segments += this.parts[key].total_segments;
                    if (segments_length < this.parts[key].total_segments) {
                        complete = false
                    }
                }
            } else {
                complete = false
            }
            var completion = available_segments / parseFloat(total_segments) * 100.0;
            if (complete || completion >= """ + str(config.postprocess.get('min_completion', 99)) + """)
                emit(this._id, completion)

        }
    """)

    # no reduce needed, since we're returning single values
    reducer = Code("""function(key, values){}""")

    # returns a list of _ids, so we need to get each binary
    for result in db.binaries.inline_map_reduce(mapper, reducer):
        if result['value']:
            binary_count += 1
            binary = db.binaries.find_one({'_id': result['_id']})

            # check to make sure we have over the configured minimum files
            nfos = []
            rars = []
            pars = []
            rar_count = 0
            par_count = 0
            zip_count = 0

            if 'parts' in binary:
                for number, part in binary['parts'].items():
                    if regex.search(pynab.nzbs.rar_part_regex, part['subject'], regex.I):
                        rar_count += 1
                    if regex.search(pynab.nzbs.nfo_regex, part['subject'], regex.I) and not regex.search(pynab.nzbs.metadata_regex,
                                                                                                part['subject'], regex.I):
                        nfos.append(part)
                    if regex.search(pynab.nzbs.rar_regex, part['subject'], regex.I) and not regex.search(pynab.nzbs.metadata_regex,
                                                                                                part['subject'], regex.I):
                        rars.append(part)
                    if regex.search(pynab.nzbs.par2_regex, part['subject'], regex.I):
                        par_count += 1
                        if not regex.search(pynab.nzbs.par_vol_regex, part['subject'], regex.I):
                            pars.append(part)
                    if regex.search(pynab.nzbs.zip_regex, part['subject'], regex.I) and not regex.search(pynab.nzbs.metadata_regex,
                                                                                                part['subject'], regex.I):
                        zip_count += 1

                if rar_count + zip_count < config.postprocess.get('min_archives', 1):
                    log.info('release: [{}] - removed (less than minimum archives)'.format(
                        binary['name']
                    ))
                    db.binaries.remove({'_id': binary['_id']})
                    continue

                # generate a gid, not useful since we're storing in GridFS
                gid = hashlib.md5(uuid.uuid1().bytes).hexdigest()

                # clean the name for searches
                clean_name = clean_release_name(binary['name'])

                # if the regex used to generate the binary gave a category, use that
                category = None
                if binary['category_id']:
                    category = db.categories.find_one({'_id': binary['category_id']})

                # otherwise, categorise it with our giant regex blob
                if not category:
                    id = pynab.categories.determine_category(binary['name'], binary['group_name'])
                    category = db.categories.find_one({'_id': id})

                # if this isn't a parent category, add those details as well
                if 'parent_id' in category:
                    category['parent'] = db.categories.find_one({'_id': category['parent_id']})

                # create the nzb, store it in GridFS and link it here
                nzb, nzb_size = pynab.nzbs.create(gid, clean_name, binary)
                if nzb:
                    added_count += 1

                    log.debug('release: [{}]: added release ({} rars, {} rarparts)'.format(
                        binary['name'],
                        len(rars),
                        rar_count
                    ))

                    db.releases.update(
                        {
                            'search_name': binary['name'],
                            'posted': binary['posted']
                        },
                        {
                            '$setOnInsert': {
                                'id': gid,
                                'added': pytz.utc.localize(datetime.datetime.now()),
                                'size': None,
                                'spotnab_id': None,
                                'completion': None,
                                'grabs': 0,
                                'passworded': None,
                                'file_count': None,
                                'tvrage': None,
                                'tvdb': None,
                                'imdb': None,
                                'nfo': None,
                                'tv': None,
                            },
                            '$set': {
                                'name': clean_name,
                                'search_name': clean_name,
                                'total_parts': binary['total_parts'],
                                'posted': binary['posted'],
                                'posted_by': binary['posted_by'],
                                'status': 1,
                                'updated': pytz.utc.localize(datetime.datetime.now()),
                                'group': db.groups.find_one({'name': binary['group_name']}, {'name': 1}),
                                'regex': db.regexes.find_one({'_id': binary['regex_id']}),
                                'category': category,
                                'nzb': nzb,
                                'nzb_size': nzb_size
                            }
                        },
                        upsert=True
                    )

                # delete processed binaries
                db.binaries.remove({'_id': binary['_id']})

    end = time.time()
    log.info('release: added {} out of {} binaries in {:.2f}s'.format(
        added_count,
        binary_count,
        end - start
    ))

########NEW FILE########
__FILENAME__ = server
import lib.nntplib as nntplib
import regex
import time
import datetime
import math

import dateutil.parser
import pytz

from pynab import log
import pynab.parts
import pynab.yenc
import config


class Server:
    def __init__(self):
        self.connection = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.connection:
            try:
                self.connection.quit()
            except Exception as e:
                pass


    def group(self, group_name):
        self.connect()

        try:
            response, count, first, last, name = self.connection.group(group_name)
        except nntplib.NNTPError:
            log.error('server: Problem sending group command to server.')
            return False

        return response, count, first, last, name

    def connect(self, compression=True):
        """Creates a connection to a news server."""
        if not self.connection:
            news_config = config.news.copy()

            # i do this because i'm lazy
            ssl = news_config.pop('ssl', False)

            try:
                if ssl:
                    self.connection = nntplib.NNTP_SSL(compression=compression, **news_config)
                else:
                    self.connection = nntplib.NNTP(compression=compression, **news_config)
            except Exception as e:
                log.error('server: Could not connect to news server: {}'.format(e))
                return False

        return True

    def get(self, group_name, messages=None):
        """Get a set of messages from the server for the specified group."""

        data = ''
        if messages:
            try:
                _, total, first, last, _ = self.connection.group(group_name)
                for message in messages:
                    article = '<{}>'.format(message)
                    response, (number, message_id, lines) = self.connection.body(article)
                    res = pynab.yenc.yenc_decode(lines)
                    if res:
                        data += res
                    else:
                        return None
            except nntplib.NNTPError as nntpe:
                log.error('server: [{}]: Problem retrieving messages: {}.'.format(group_name, nntpe))
                return None

            return data
        else:
            return None

    def scan(self, group_name, first, last):
        """Scan a group for segments and return a list."""

        start = time.time()
        try:
            # grab the headers we're after
            self.connection.group(group_name)
            status, overviews = self.connection.over((first, last))
        except nntplib.NNTPError as nntpe:
            log.debug('NNTP Error: ' + str(nntpe))
            return {}

        messages = {}
        ignored = 0
        received = []
        for (id, overview) in overviews:
            # keep track of which messages we received so we can
            # optionally check for ones we missed later
            received.append(id)

            # get the current segment number
            results = regex.findall('\((\d+)[\/](\d+)\)', overview['subject'])

            # it might match twice, so just get the last one
            # the first is generally the part number
            if results:
                (segment_number, total_segments) = results[-1]
            else:
                # if there's no match at all, it's probably not a binary
                ignored += 1
                continue

            # make sure the header contains everything we need
            if ':bytes' not in overview:
                continue

            # assuming everything didn't fuck up, continue
            if int(segment_number) > 0 and int(total_segments) > 0:
                # strip the segment number off the subject so
                # we can match binary parts together
                subject = nntplib.decode_header(overview['subject'].replace(
                    '(' + str(segment_number) + '/' + str(total_segments) + ')', ''
                ).strip()).encode('utf-8', 'replace').decode('latin-1')

                # this is spammy as shit, for obvious reasons
                #pynab.log.debug('Binary part found: ' + subject)

                # build the segment, make sure segment number and size are ints
                segment = {
                    'message_id': overview['message-id'][1:-1],
                    'segment': int(segment_number),
                    'size': int(overview[':bytes']),
                }

                # if we've already got a binary by this name, add this segment
                if subject in messages:
                    messages[subject]['segments'][segment_number] = segment
                    messages[subject]['available_segments'] += 1
                else:
                    # dateutil will parse the date as whatever and convert to UTC
                    # some subjects/posters have odd encoding, which will break pymongo
                    # so we make sure it doesn't
                    message = {
                        'subject': subject,
                        'posted': dateutil.parser.parse(overview['date']),
                        'posted_by': nntplib.decode_header(overview['from']).encode('utf-8', 'replace').decode(
                            'latin-1'),
                        'group_name': group_name,
                        'xref': overview['xref'],
                        'total_segments': int(total_segments),
                        'available_segments': 1,
                        'segments': {segment_number: segment, },
                    }

                    messages[subject] = message
            else:
                # :getout:
                ignored += 1

        # instead of checking every single individual segment, package them first
        # so we typically only end up checking the blacklist for ~150 parts instead of thousands
        blacklist = [k for k in messages if pynab.parts.is_blacklisted(k, group_name)]
        blacklisted_parts = len(blacklist)
        total_parts = len(messages)
        for k in blacklist:
            del messages[k]

        # TODO: implement re-checking of missed messages, or maybe not
        # most parts that get ko'd these days aren't coming back anyway
        messages_missed = list(set(range(first, last)) - set(received))

        end = time.time()

        log.info('server: [{}]: retrieved {} - {} in {:.2f}s [{} recv, {} pts, {} ign, {} blk]'.format(
            group_name,
            first, last,
            end - start,
            len(received),
            total_parts,
            ignored,
            blacklisted_parts
        ))

        return messages

    def post_date(self, group_name, article):
        """Retrieves the date of the specified post."""

        i = 0
        while i < 10:
            articles = []

            try:
                self.connection.group(group_name)
                _, articles = self.connection.over('{0:d}-{0:d}'.format(article))
            except nntplib.NNTPError as e:
                log.debug(e)
                # leave this alone - we don't expect any data back
                pass

            try:
                art_num, overview = articles[0]
            except IndexError:
                # if the server is missing an article, it's usually part of a large group
                # so skip along quickishly, the datefinder will autocorrect itself anyway
                article += int(article * 0.0001)
                #article += 1
                i += 1
                continue

            if art_num and overview:
                return dateutil.parser.parse(overview['date']).astimezone(pytz.utc)
            else:
                return None

    def day_to_post(self, group_name, days):
        """Converts a datetime to approximate article number for the specified group."""

        _, count, first, last, _ = self.connection.group(group_name)
        target_date = datetime.datetime.now(pytz.utc) - datetime.timedelta(days)

        first_date = self.post_date(group_name, first)
        last_date = self.post_date(group_name, last)

        if first_date and last_date:
            if target_date < first_date:
                return first
            elif target_date > last_date:
                return False

            upper = last
            lower = first
            interval = math.floor((upper - lower) * 0.5)
            next_date = last_date

            while self.days_old(next_date) < days:
                skip = 1
                temp_date = self.post_date(group_name, upper - interval)
                if temp_date:
                    while temp_date > target_date:
                        upper = upper - interval - (skip - 1)
                        skip *= 2
                        temp_date = self.post_date(group_name, upper - interval)

                interval = math.ceil(interval / 2)
                if interval <= 0:
                    break
                skip = 1

                next_date = self.post_date(group_name, upper - 1)
                if next_date:
                    while not next_date:
                        upper = upper - skip
                        skip *= 2
                        next_date = self.post_date(group_name, upper - 1)

            log.debug('server: {}: article {:d} is {:d} days old.'.format(group_name, upper, self.days_old(next_date)))
            return upper
        else:
            log.error('server: {}: could not get group information.'.format(group_name))
            return False

    @staticmethod
    def days_old(date):
        """Returns the age of the given date, in days."""
        return (datetime.datetime.now(pytz.utc) - date).days
########NEW FILE########
__FILENAME__ = tvrage
import regex
import unicodedata
import difflib
import datetime
import time
import roman
import requests
import xmltodict
import pytz
import pymongo
from lxml import etree
from collections import defaultdict

from pynab.db import db
from pynab import log
import pynab.util
import config


TVRAGE_FULL_SEARCH_URL = 'http://services.tvrage.com/feeds/full_search.php'


# use compiled xpaths and regex for speedup
XPATH_SHOW = etree.XPath('//show')
XPATH_NAME = etree.XPath('name/text()')
XPATH_AKA = etree.XPath('akas/aka/text()')
XPATH_LINK = etree.XPath('link/text()')
XPATH_COUNTRY = etree.XPath('country/text()')

RE_LINK = regex.compile('tvrage\.com\/((?!shows)[^\/]*)$', regex.I)


def process(limit=100, online=True):
    """Processes [limit] releases to add TVRage information."""

    expiry = datetime.datetime.now(pytz.utc) - datetime.timedelta(config.postprocess.get('fetch_blacklist_duration', 7))

    query = {
        'tvrage._id': {'$exists': False},
        'category.parent_id': 5000,
    }

    if online:
        query.update({
            'tvrage.possible': {'$exists': False},
            '$or': [
             {'tvrage.attempted': {'$exists': False}},
             {'tvrage.attempted': {'$lte': expiry}}
            ]
        })

    for release in db.releases.find(query).limit(limit).sort('posted', pymongo.DESCENDING).batch_size(25):
        method = ''

        show = parse_show(release['search_name'])
        if show:
            db.releases.update({'_id': release['_id']}, {
                '$set': {
                    'tv': show
                }
            })

            rage = db.tvrage.find_one({'name': show['clean_name']})
            if not rage and 'and' in show['clean_name']:
                rage = db.tvrage.find_one({'name': show['clean_name'].replace(' and ', ' & ')})

            if rage:
                method = 'local'
            elif not rage and online:
                rage_data = search(show)
                if rage_data:
                    method = 'online'
                    db.tvrage.update(
                        {'_id': int(rage_data['showid'])},
                        {
                            '$set': {
                                'name': rage_data['name']
                            }
                        },
                        upsert=True
                    )
                    rage = db.tvrage.find_one({'_id': int(rage_data['showid'])})

                # wait slightly so we don't smash the api
                time.sleep(1)

            if rage:
                log.info('tvrage: [{}] - [{}] - tvrage added: {}'.format(
                    release['_id'],
                    release['search_name'],
                    method
                ))

                db.releases.update({'_id': release['_id']}, {
                    '$set': {
                        'tvrage': rage
                    }
                })
            elif not rage and online:
                log.warning('tvrage: [{}] - [{}] - tvrage failed: {}'.format(
                    release['_id'],
                    release['search_name'],
                    'no show found (online)'
                ))

                db.releases.update({'_id': release['_id']}, {
                    '$set': {
                        'tvrage': {
                            'attempted': datetime.datetime.now(pytz.utc)
                        },
                    }
                })
            else:
                log.warning('tvrage: [{}] - [{}] - tvrage failed: {}'.format(
                    release['_id'],
                    release['search_name'],
                    'no show found (local)'
                ))
        else:
            log.error('tvrage: [{}] - [{}] - tvrage failed: {}'.format(
                    release['_id'],
                    release['search_name'],
                    'no suitable regex for show name'
                ))
            db.releases.update({'_id': release['_id']}, {
                '$set': {
                    'tvrage': {
                        'possible': False
                    },
                }
            })


def search(show):
    """Search TVRage's online API for show data."""
    try:
        r = requests.get(TVRAGE_FULL_SEARCH_URL, params={'show': show['clean_name']})
    except Exception as e:
        log.error(e)
        return None
    
    content = r.content
    return search_lxml(show, content)


def extract_names(xmlshow):
    """Extract all possible show names for matching from an lxml show tree, parsed from tvrage search"""
    yield from XPATH_NAME(xmlshow)
    yield from XPATH_AKA(xmlshow)
    link = XPATH_LINK(xmlshow)[0]
    link_result = RE_LINK.search(link)
    if link_result:
        yield from link_result.groups()


def search_lxml(show, content):
    """Search TVRage online API for show data."""
    try:
        tree = etree.fromstring(content)
    except:
        log.critical('Problem parsing XML with lxml')
        return None

    matches = defaultdict(list)
    # parse show names in the same order as returned by tvrage, first one is usually the good one
    for xml_show in XPATH_SHOW(tree):
        for name in extract_names(xml_show):
            ratio = int(difflib.SequenceMatcher(None, show['clean_name'], clean_name(name)).ratio() * 100)
            if ratio == 100:
                return xmltodict.parse(etree.tostring(xml_show))['show']
            matches[ratio].append(xml_show)
                
    # if no 100% is found, check highest ratio matches
    for ratio, xml_matches in sorted(matches.items(), reverse=True):
        for xml_match in xml_matches:
            if ratio >= 80:
                return xmltodict.parse(etree.tostring(xml_match))['show']
            elif 80 > ratio > 60:
                if 'country' in show and show['country'] and XPATH_COUNTRY(xml_match):
                    if str.lower(show['country']) == str.lower(XPATH_COUNTRY(xml_match)[0]):
                        return xmltodict.parse(etree.tostring(xml_match))['show']


def clean_name(name):
    """Cleans a show name for searching (against tvrage)."""
    name = unicodedata.normalize('NFKD', name)

    name = regex.sub('[._\-]', ' ', name)
    name = regex.sub('[\':!"#*’,()?]', '', name)
    name = regex.sub('\s{2,}', ' ', name)
    name = regex.sub('\[.*?\]', '', name)

    replace_chars = {
        '$': 's',
        '&': 'and',
        'ß': 'ss'
    }

    for k, v in replace_chars.items():
        name = name.replace(k, v)

    pattern = regex.compile(r'\b(hdtv|dvd|divx|xvid|mpeg2|x264|aac|flac|bd|dvdrip|10 bit|264|720p|1080p\d+x\d+)\b', regex.I)
    name = pattern.sub('', name)

    return name.lower()


def parse_show(search_name):
    """Parses a show name for show name, season and episode information."""

    # i fucking hate this function and there has to be a better way of doing it
    # named capturing groups in a list and semi-intelligent processing?

    show = {}
    match = pynab.util.Match()
    if match.match('^(.*?)[\. \-]s(\d{1,2})\.?e(\d{1,3})(?:\-e?|\-?e)(\d{1,3})\.', search_name, regex.I):
        show = {
            'name': match.match_obj.group(1),
            'season': int(match.match_obj.group(2)),
            'episode': [int(match.match_obj.group(3)), int(match.match_obj.group(4))],
        }
    elif match.match('^(.*?)[\. \-]s(\d{2})\.?e(\d{2})(\d{2})\.', search_name, regex.I):
        show = {
            'name': match.match_obj.group(1),
            'season': int(match.match_obj.group(2)),
            'episode': [int(match.match_obj.group(3)), int(match.match_obj.group(4))],
        }
    elif match.match('^(.*?)[\. \-]s(\d{1,2})\.?e(\d{1,3})\.?', search_name, regex.I):
        show = {
            'name': match.match_obj.group(1),
            'season': int(match.match_obj.group(2)),
            'episode': int(match.match_obj.group(3)),
        }
    elif match.match('^(.*?)[\. \-]s(\d{1,2})\.', search_name, regex.I):
        show = {
            'name': match.match_obj.group(1),
            'season': int(match.match_obj.group(2)),
            'episode': 'all',
        }
    elif match.match('^(.*?)[\. \-]s(\d{1,2})d\d{1}\.', search_name, regex.I):
        show = {
            'name': match.match_obj.group(1),
            'season': int(match.match_obj.group(2)),
            'episode': 'all',
        }
    elif match.match('^(.*?)[\. \-](\d{1,2})x(\d{1,3})\.', search_name, regex.I):
        show = {
            'name': match.match_obj.group(1),
            'season': int(match.match_obj.group(2)),
            'episode': int(match.match_obj.group(3)),
        }
    elif match.match('^(.*?)[\. \-](19|20)(\d{2})[\.\-](\d{2})[\.\-](\d{2})\.', search_name, regex.I):
        show = {
            'name': match.match_obj.group(1),
            'season': match.match_obj.group(2) + match.match_obj.group(3),
            'episode': '{}/{}'.format(match.match_obj.group(4), match.match_obj.group(5)),
            'air_date': '{}{}-{}-{}'.format(match.match_obj.group(2), match.match_obj.group(3),
                                            match.match_obj.group(4), match.match_obj.group(5))
        }
    elif match.match('^(.*?)[\. \-](\d{2}).(\d{2})\.(19|20)(\d{2})\.', search_name, regex.I):
        show = {
            'name': match.match_obj.group(1),
            'season': match.match_obj.group(4) + match.match_obj.group(5),
            'episode': '{}/{}'.format(match.match_obj.group(2), match.match_obj.group(3)),
            'air_date': '{}{}-{}-{}'.format(match.match_obj.group(4), match.match_obj.group(5),
                                            match.match_obj.group(2), match.match_obj.group(3))
        }
    elif match.match('^(.*?)[\. \-](\d{2}).(\d{2})\.(\d{2})\.', search_name, regex.I):
        # this regex is particularly awful, but i don't think it gets used much
        # seriously, > 15? that's going to be a problem in 2 years
        if 15 < int(match.match_obj.group(4)) <= 99:
            season = '19' + match.match_obj.group(4)
        else:
            season = '20' + match.match_obj.group(4)

        show = {
            'name': match.match_obj.group(1),
            'season': season,
            'episode': '{}/{}'.format(match.match_obj.group(2), match.match_obj.group(3)),
            'air_date': '{}-{}-{}'.format(season, match.match_obj.group(2), match.match_obj.group(3))
        }
    elif match.match('^(.*?)[\. \-]20(\d{2})\.e(\d{1,3})\.', search_name, regex.I):
        show = {
            'name': match.match_obj.group(1),
            'season': '20' + match.match_obj.group(2),
            'episode': int(match.match_obj.group(3)),
        }
    elif match.match('^(.*?)[\. \-]20(\d{2})\.Part(\d{1,2})\.', search_name, regex.I):
        show = {
            'name': match.match_obj.group(1),
            'season': '20' + match.match_obj.group(2),
            'episode': int(match.match_obj.group(3)),
        }
    elif match.match('^(.*?)[\. \-](?:Part|Pt)\.?(\d{1,2})\.', search_name, regex.I):
        show = {
            'name': match.match_obj.group(1),
            'season': 1,
            'episode': int(match.match_obj.group(2)),
        }
    elif match.match('^(.*?)[\. \-](?:Part|Pt)\.?([ivx]+)', search_name, regex.I):
        show = {
            'name': match.match_obj.group(1),
            'season': 1,
            'episode': roman.fromRoman(str.upper(match.match_obj.group(2)))
        }
    elif match.match('^(.*?)[\. \-]EP?\.?(\d{1,3})', search_name, regex.I):
        show = {
            'name': match.match_obj.group(1),
            'season': 1,
            'episode': int(match.match_obj.group(2)),
        }
    elif match.match('^(.*?)[\. \-]Seasons?\.?(\d{1,2})', search_name, regex.I):
        show = {
            'name': match.match_obj.group(1),
            'season': int(match.match_obj.group(2)),
            'episode': 'all'
        }

    if 'name' in show and show['name']:
        # check for country code or name (Biggest Loser Australia etc)
        country = regex.search('[\._ ](US|UK|AU|NZ|CA|NL|Canada|Australia|America)', show['name'], regex.I)
        if country:
            if str.lower(country.group(1)) == 'canada':
                show['country'] = 'CA'
            elif str.lower(country.group(1)) == 'australia':
                show['country'] = 'AU'
            elif str.lower(country.group(1)) == 'america':
                show['country'] = 'US'
            else:
                show['country'] = str.upper(country.group(1))

        show['clean_name'] = clean_name(show['name'])

        if not isinstance(show['season'], int) and len(show['season']) == 4:
            show['series_full'] = '{}/{}'.format(show['season'], show['episode'])
        else:
            year = regex.search('[\._ ](19|20)(\d{2})', search_name, regex.I)
            if year:
                show['year'] = year.group(1) + year.group(2)

            show['season'] = 'S{:02d}'.format(show['season'])

            # check to see what episode ended up as
            if isinstance(show['episode'], list):
                show['episode'] = ''.join(['E{:02d}'.format(s) for s in show['episode']])
            elif isinstance(show['episode'], int):
                show['episode'] = 'E{:02d}'.format(int(show['episode']))
                # if it's a date string, leave it as that

            show['series_full'] = show['season'] + show['episode']

        return show

    return False






########NEW FILE########
__FILENAME__ = users
import hashlib
import uuid

from pynab.db import db
from pynab import log


def create(email):
    """Creates a user by email with a random API key."""
    log.info('Creating user {}...'.format(email))

    api_key = hashlib.md5(uuid.uuid4().bytes).hexdigest()

    user = {
        'email': email,
        'api_key': api_key,
        'grabs': 0
    }

    db.users.update({'email': email}, user, upsert=True)

    return api_key
########NEW FILE########
__FILENAME__ = util
import regex

import requests

from pynab.db import db
from pynab import log
import config


class Match(object):
    """Holds a regex match result so we can use it in chained if statements."""

    def __init__(self):
        self.match_obj = None

    def match(self, *args, **kwds):
        self.match_obj = regex.search(*args, **kwds)
        return self.match_obj is not None


def update_blacklist():
    """Check for Blacklist update and load them into Mongo."""
    blacklist_url = config.postprocess.get('blacklist_url')
    if blacklist_url:
        response = requests.get(blacklist_url)
        lines = response.text.splitlines()

        for line in lines:
            elements = line.split('\t\t')
            if len(elements) == 4:
                log.debug('Updating blacklist {}...'.format(elements[1]))
                db.blacklists.update(
                    {
                        'regex': elements[1]
                    },
                    {
                        '$setOnInsert': {
                            'status': 0
                        },
                        '$set': {
                            'group_name': elements[0],
                            'regex': elements[1],
                            'description': elements[3],
                        }
                    },
                    upsert=True
                )
        return True
    else:
        log.error('No blacklist update url in config.')
        return False


def update_regex():
    """Check for NN+ regex update and load them into Mongo."""
    regex_url = config.postprocess.get('regex_url')
    if regex_url:
        response = requests.get(regex_url)
        lines = response.text.splitlines()

        # get the revision by itself
        first_line = lines.pop(0)
        revision = regex.search('\$Rev: (\d+) \$', first_line)
        if revision:
            revision = int(revision.group(1))
            log.info('Regex at revision: {:d}'.format(revision))

        # and parse the rest of the lines, since they're an sql dump
        regexes = []
        for line in lines:
            reg = regex.search('\((\d+), \'(.*)\', \'(.*)\', (\d+), (\d+), (.*), (.*)\);$', line)
            if reg:
                try:
                    if reg.group(6) == 'NULL':
                        description = ''
                    else:
                        description = reg.group(6).replace('\'', '')

                    if reg.group(7) == 'NULL':
                        category_id = None
                    else:
                        category_id = int(reg.group(7))

                    regexes.append({
                        '_id': int(reg.group(1)),
                        'group_name': reg.group(2),
                        'regex': reg.group(3).replace('\\\\', '\\'),
                        'ordinal': int(reg.group(4)),
                        'status': int(reg.group(5)),
                        'description': description,
                        'category_id': category_id
                    })
                except:
                    log.error('Problem importing regex dump.')
                    return False

        # if the parsing actually worked
        if len(regexes) > 0:
            curr_total = db.regexes.count()
            change = len(regexes) - curr_total

            # this will show a negative if we add our own, but who cares for the moment
            log.info('Retrieved {:d} regexes, {:d} new.'.format(len(regexes), change))

            if change != 0:
                log.info('We either lost or gained regex, so dump them and reload.')

                db.regexes.remove({'_id': {'$lte': 100000}})
                db.regexes.insert(regexes)

                return True
            else:
                log.info('Appears to be no change, leaving alone.')
                return False
    else:
        log.error('No config item set for regex_url - do you own newznab plus?')
        return False


########NEW FILE########
__FILENAME__ = yenc
"""With big thanks to SABNZBD, since they're maybe the only ones with yenc code that
works in Python 3"""

import regex

from pynab import log

YDEC_TRANS = ''.join([chr((i + 256 - 42) % 256) for i in range(256)])


def yenc_decode(lines):
    """Decodes a yEnc-encoded fileobj.
    Should use python-yenc 0.4 for this, but it's not py3.3 compatible.
    """

    data = yenc_strip([l.decode('ISO-8859-1') for l in lines])

    if data:
        yenc, data = yenc_check(data)
        ybegin, ypart, yend = yenc

        if ybegin and yend:
            data = ''.join(data)
            for i in (0, 9, 10, 13, 27, 32, 46, 61):
                j = '=%c' % (i + 64)
                data = data.replace(j, chr(i))
            return data.translate(YDEC_TRANS)
        else:
            log.debug('File wasn\'t yenc.')
            log.debug(data)
    else:
        log.debug('Problem parsing lines.')

    return None


def yenc_check(data):
    ybegin = None
    ypart = None
    yend = None

    ## Check head
    for i in range(min(40, len(data))):
        try:
            if data[i].startswith('=ybegin '):
                splits = 3
                if data[i].find(' part=') > 0:
                    splits += 1
                if data[i].find(' total=') > 0:
                    splits += 1

                ybegin = yenc_split(data[i], splits)

                if data[i + 1].startswith('=ypart '):
                    ypart = yenc_split(data[i + 1])
                    data = data[i + 2:]
                    break
                else:
                    data = data[i + 1:]
                    break
        except IndexError:
            break

    ## Check tail
    for i in range(-1, -11, -1):
        try:
            if data[i].startswith('=yend '):
                yend = yenc_split(data[i])
                data = data[:i]
                break
        except IndexError:
            break

    return (ybegin, ypart, yend), data


YSPLIT_RE = regex.compile(r'([a-zA-Z0-9]+)=')


def yenc_split(line, splits=None):
    fields = {}

    if splits:
        parts = YSPLIT_RE.split(line, splits)[1:]
    else:
        parts = YSPLIT_RE.split(line)[1:]

    if len(parts) % 2:
        return fields

    for i in range(0, len(parts), 2):
        key, value = parts[i], parts[i + 1]
        fields[key] = value.strip()

    return fields


def yenc_strip(data):
    while data and not data[0]:
        data.pop(0)

    while data and not data[-1]:
        data.pop()

    for i in range(len(data)):
        if data[i][:2] == '..':
            data[i] = data[i][1:]
    return data
########NEW FILE########
__FILENAME__ = backfill
import argparse
import os
import sys
import dateutil.parser
import pytz

sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), '..'))

import pynab.groups
from pynab.db import db

parser = argparse.ArgumentParser(description='''
Backfill:
Fetch and parse parts and messages for active groups.

Updating a specific group will force an update regardless of whether the group is active.
Updating all groups will only update active groups.
''')
parser.add_argument('-g', '--group', nargs='?', help='Group to backfill (leave blank for all)')
parser.add_argument('-d', '--date', nargs='?', help='Date to backfill to (leave blank to use default backfill_days)')

args = parser.parse_args()

if args.group:
    group = db.groups.find_one({'name': args.group})
    if group:
        if not args.date:
            args.date = None
        if pynab.groups.backfill(group['name'], pytz.utc.localize(dateutil.parser.parse(args.date))):
            print('Group {0} successfully backfilled!'.format(group['name']))
        else:
            print('Problem backfilling group {0}.'.format(group['name']))
    else:
        print('No group called {0} exists in the db.'.format(args.group))
else:
    for group in db.groups.find({'active': 1}):
        if pynab.groups.backfill(group['name']):
            print('Group {0} successfully backfilled!'.format(group['name']))
        else:
            print('Problem backfilling group {0}.'.format(group['name']))
########NEW FILE########
__FILENAME__ = clean_dead_releases
import pymongo
import os
import sys

sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), '..'))

import pynab.releases
import pynab.nzbs
from pynab.db import db


def clean_dead_releases():
    i = 0
    for release in db.releases.find({'nzb_size': {'$lt': 1000}}).sort('posted', pymongo.ASCENDING).batch_size(50):
        if not pynab.nzbs.get_nzb_dict(release['nzb']):
            print('Deleting {} ({})...'.format(release['search_name'], release['nzb_size']))
            db.releases.remove({'id': release['id']})

        i += 1
        if i % 50 == 0:
            print('Processed {} releases...'.format(i))

if __name__ == '__main__':
    print('''
    Clean Dead Releases

    This will delete any releases whose NZB contains no files - dead releases.
    ''')
    print('Warning: Obviously, this is destructive.')
    input('To continue, press enter. To exit, press ctrl-c.')

    clean_dead_releases()
########NEW FILE########
__FILENAME__ = convert_from_newznab
"""
Functions to convert a Newznab installation to Pynab.

NOTE: DESTRUCTIVE. DO NOT RUN ON ACTIVE PYNAB INSTALL.
(unless you know what you're doing)

"""

# if you're using pycharm, don't install the bson package
# it comes with pymongo
import os
import sys

import cymysql
import pymongo.errors


sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), '..'))

from pynab.db import db
import config


def dupe_notice():
    error_text = '''
        If there are duplicate rageID/tvdbID/imdbID's in their
        respective tables, you'll need to trim duplicates first
        or these scripts will fail. You can do so with:

        alter ignore table tvrage add unique key (rageid);

        If they're running InnoDB you can't always do this, so
        you'll need to do:

        alter table tvrage engine myisam;
        alter ignore table tvrage add unique key (rageid);
        alter table tvrage engine innodb;
    '''

    print(error_text)


def mysql_connect(mysql_config):
    mysql = cymysql.connect(
        host=mysql_config['host'],
        port=mysql_config['port'],
        user=mysql_config['user'],
        passwd=mysql_config['passwd'],
        db=mysql_config['db']
    )

    return mysql


def convert_groups(mysql):
    """Converts Newznab groups table into Pynab. Only really
    copies backfill records and status."""
    # removed minsize/minfiles, since we're not really using them
    # most of the groups I index don't come up with too many stupid
    # releases, so if anyone has problem groups they can re-add it
    from_query = """
        SELECT name, first_record, last_record, active
        FROM groups;
    """

    print('Converting groups...')

    cursor = mysql.cursor()
    cursor.execute(from_query)

    if 'groups' in db.collection_names():
        db.groups.drop()

    groups = []
    for r in cursor.fetchall():
        group = {
            'name': r[0],
            'first': r[1],
            'last': r[2],
            'active': r[3]
        }
        groups.append(group)

    db.groups.insert(groups)


def convert_categories(mysql):
    """Convert Newznab categories table into Pynab."""
    from_query = """
        SELECT ID, title, parentID, minsizetoformrelease, maxsizetoformrelease
        FROM category;
    """

    print('Converting categories...')

    cursor = mysql.cursor()
    cursor.execute(from_query)

    if 'categories' in db.collection_names():
        db.categories.drop()

    categories = {}
    for r in cursor.fetchall():
        category = {
            '_id': r[0],
            'name': r[1],
            'parent_id': r[2],
            'min_size': r[3],
            'max_size': r[4]
        }

        db.categories.insert(category)


def convert_regex(mysql):
    """Converts Newznab releaseregex table into Pynab form. We leave the regex in
    PHP-form because it includes case sensitivity flags etc in the string."""
    from_query = """
        SELECT groupname, regex, ordinal, releaseregex.status, category.title, releaseregex.description
        FROM releaseregex
            LEFT JOIN category ON releaseregex.CategoryID = category.ID
        ORDER BY groupname;
        """

    print('Converting regex...')

    cursor = mysql.cursor()
    cursor.execute(from_query)

    if 'regexes' in db.collection_names():
        db.regexes.drop()

    regexes = []
    for r in cursor.fetchall():
        if r[4]:
            c_id = db.categories.find_one({'name': r[4]})['_id']
        else:
            c_id = None

        regex = {
            'group_name': r[0],
            'regex': r[1],
            'ordinal': r[2],
            'status': r[3],
            'description': r[5],
            'category_id': c_id
        }

        regexes.append(regex)

    db.regexes.insert(regexes)


def convert_blacklist(mysql):
    """Converts Newznab binaryblacklist table into Pynab format.
    This isn't actually used yet."""
    from_query = """
        SELECT groupname, regex, status, description
        FROM binaryblacklist
        ORDER BY id;
        """

    print('Converting blacklist...')

    cursor = mysql.cursor()
    cursor.execute(from_query)

    if 'blacklists' in db.collection_names():
        db.blacklists.drop()

    blacklists = []
    for r in cursor.fetchall():
        blacklist = {
            'group_name': r[0],
            'regex': r[1],
            'status': r[2],
            'description': r[3]
        }

        blacklists.append(blacklist)

    db.blacklists.insert(blacklists)


def convert_users(mysql):
    """Converts Newznab users table into Pynab format. More or less
    of this may be necessary depending on what people want. I'm pretty
    much just after bare API access, so we only really need rsstoken."""
    from_query = """
        SELECT username, email, password, rsstoken, userseed, grabs
        FROM users
        ORDER BY id;
        """

    print('Converting users...')

    cursor = mysql.cursor()
    cursor.execute(from_query)

    if 'users' in db.collection_names():
        db.users.drop()

    users = []
    for r in cursor.fetchall():
        user = {
            'email': r[1],
            'api_key': r[3],
            'grabs': r[5]
        }

        users.append(user)

    db.users.insert(users)


def convert_tvdb(mysql):
    """Converts Newznab tvdb table into Pynab format. Actually
    useful, since we re-use the same data regardless."""
    from_query = """
        SELECT tvdbID, seriesname
        FROM thetvdb
        WHERE tvdbID != 0 AND seriesname != ""
        ORDER BY seriesname;
        """

    print('Converting tvdb...')

    cursor = mysql.cursor()
    cursor.execute(from_query)

    if 'tvdb' in db.collection_names():
        db.tvdb.drop()

    tvdbs = []
    for r in cursor.fetchall():
        tvdb = {
            '_id': r[0],
            'name': r[1]
        }

        tvdbs.append(tvdb)

    try:
        db.tvdb.insert(tvdbs)
    except pymongo.errors.DuplicateKeyError:
        print('Error: Duplicate keys in TVDB MySQL table.')
        dupe_notice()
        print('Stopping script...')
        sys.exit(1)


def convert_tvrage(mysql):
    """Converts Newznab tvrage table into Pynab format."""
    from_query = """
        SELECT rageID, releasetitle
        FROM tvrage
        WHERE rageID > 0
        ORDER BY rageID
        """

    print('Converting tvrage...')

    cursor = mysql.cursor()
    cursor.execute(from_query)

    if 'tvrage' in db.collection_names():
        db.tvrage.drop()

    tvrages = []
    for r in cursor.fetchall():
        tvrage = {
            '_id': r[0],
            'name': r[1]
        }

        tvrages.append(tvrage)

    try:
        db.tvrage.insert(tvrages)
    except pymongo.errors.DuplicateKeyError:
        print('Error: Duplicate keys in TVRage MySQL table.')
        dupe_notice()
        print('Stopping script...')
        sys.exit(1)


def convert_imdb(mysql):
    """Converts Newznab imdb table into Pynab format."""
    from_query = """
        SELECT imdbID, title, year, language, genre
        FROM movieinfo
        WHERE imdbID > 0
        ORDER BY imdbID
        """

    print('Converting imdb...')

    cursor = mysql.cursor()
    cursor.execute(from_query)

    if 'imdb' in db.collection_names():
        db.imdb.drop()

    imdbs = []
    for r in cursor.fetchall():
        imdb = {
            '_id': r[0],
            'name': r[1],
            'year': r[2],
            'lang': r[3],
            'genre': [g.strip() for g in r[4].split(',')]
        }

        imdbs.append(imdb)

    try:
        db.imdb.insert(imdbs)
    except pymongo.errors.DuplicateKeyError:
        print('Error: Duplicate keys in IMDB MySQL table.')
        dupe_notice()
        print('Stopping script...')
        sys.exit(1)


if __name__ == '__main__':
    print('Convert Newznab to Pynab script.')
    print('Please note that this script is destructive and will wipe the following Mongo collections:')
    print('Groups, Categories, Regexes, Blacklists, Users, TVRage, IMDB, TVDB.')
    print('If you don\'t want some of these to be replaced, edit this script and comment those lines out.')
    print('Also ensure that you\'ve edited config.py to include the details of your MySQL server.')
    input('To continue, press enter. To exit, press ctrl-c.')

    mysql = mysql_connect(config.mysql)

    # comment lines out if you don't want those collections replaced
    convert_groups(mysql)
    convert_categories(mysql)
    convert_regex(mysql)
    convert_blacklist(mysql)
    convert_imdb(mysql)
    convert_tvdb(mysql)
    convert_tvrage(mysql)
    convert_users(mysql)

    print('Completed transfer. You can think about shutting down / removing MySQL from your server now.')
    print('Unless you\'re using it for something else, in which case that\'d be dumb.')
########NEW FILE########
__FILENAME__ = convert_omdb_dump
import sys
import os
import pymongo.errors

sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), '..'))

from pynab.db import db


def convert_omdb_dump():
    db.imdb.drop()
    with open('C:\\temp\\omdb.txt', encoding='latin1') as f:
        f.readline()
        for line in f:
            data = line.split('\t')
            imdb = {
                '_id': data[1],
                'name': data[2],
                'year': data[3],
                'genre': [d.strip() for d in data[6].split(',')]
            }
            try:
                db.imdb.insert(imdb)
            except pymongo.errors.DuplicateKeyError as e:
                pass
            print('{}'.format(data[2]))


if __name__ == '__main__':
    convert_omdb_dump()
########NEW FILE########
__FILENAME__ = create_user
import argparse
import os
import sys

sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), '..'))

import pynab.users

parser = argparse.ArgumentParser(description='''Create a new user.''')
parser.add_argument('email', help='Email address of user')

args = parser.parse_args()

if args.email:
    key = pynab.users.create(args.email)
    print('User created. API key is: {}'.format(key))
########NEW FILE########
__FILENAME__ = ensure_indexes
import sys
import os

import pymongo


sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), '..'))

from pynab.db import db
from pynab import log


def create_indexes():
    """Ensures that indexes for collections exist.
    Add all new appropriate indexes here. Gets called
    once per script run."""
    # rather than scatter index creation everywhere, centralise it so it only runs once

    # categories
    db.categories.ensure_index('name', pymongo.ASCENDING)
    db.categories.ensure_index('parent_id', pymongo.ASCENDING)

    # regexes
    db.regexes.ensure_index([
        ('ordinal', pymongo.ASCENDING),
        ('group_name', pymongo.ASCENDING)
    ], background=True)

    # groups
    db.groups.ensure_index('name', pymongo.ASCENDING)

    # users
    db.users.ensure_index('username', pymongo.ASCENDING)
    db.users.ensure_index('email', pymongo.ASCENDING)
    db.users.ensure_index('rsstoken', pymongo.ASCENDING)

    # tvrage
    db.tvrage.ensure_index('_id', pymongo.ASCENDING, background=True)
    db.tvrage.ensure_index('name', pymongo.ASCENDING, background=True)

    # tvdb
    db.tvdb.ensure_index('_id', pymongo.ASCENDING)
    db.tvdb.ensure_index('name', pymongo.ASCENDING)

    # blacklists
    db.blacklists.ensure_index('group_name', pymongo.ASCENDING)

    # imdb
    db.imdb.ensure_index('_id', pymongo.ASCENDING)
    db.imdb.ensure_index('name', pymongo.ASCENDING)
    db.imdb.ensure_index([
        ('name', pymongo.ASCENDING),
        ('year', pymongo.ASCENDING)
    ], background=True)


    # binaries
    db.binaries.ensure_index('name', pymongo.ASCENDING, background=True)
    db.binaries.ensure_index('group_name', pymongo.ASCENDING, background=True)
    db.binaries.ensure_index('total_parts', pymongo.ASCENDING, background=True)

    # parts
    db.parts.ensure_index('subject', pymongo.ASCENDING, background=True)
    db.parts.ensure_index('group_name', pymongo.ASCENDING, background=True)

    # releases
    db.releases.ensure_index('id', pymongo.ASCENDING, background=True)
    db.releases.ensure_index('name', pymongo.ASCENDING, background=True)
    db.releases.ensure_index('category._id', pymongo.ASCENDING, background=True)
    db.releases.ensure_index('category', pymongo.ASCENDING, background=True)
    db.releases.ensure_index('rage._id', pymongo.ASCENDING, background=True)
    db.releases.ensure_index('imdb._id', pymongo.ASCENDING, background=True)
    db.releases.ensure_index('tvdb._id', pymongo.ASCENDING, background=True)
    db.releases.ensure_index('posted', pymongo.DESCENDING, background=True)
    db.releases.ensure_index([
                                 ('search_name', 'text'),
                                 ('posted', pymongo.ASCENDING)
                             ], background=True)
    db.releases.ensure_index([
                                 ('search_name', pymongo.ASCENDING),
                                 ('posted', pymongo.ASCENDING)
                             ], background=True)
    db.releases.ensure_index([
                                 ('tvrage._id', pymongo.ASCENDING),
                                 ('category._id', pymongo.ASCENDING)
                             ], background=True)
    db.releases.ensure_index([
                                 ('posted', pymongo.DESCENDING),
                                 ('category._id', pymongo.ASCENDING)
                             ], background=True)
    db.releases.ensure_index([
                                 ('posted', pymongo.ASCENDING),
                                 ('nfo', pymongo.ASCENDING)
                             ], background=True)
    db.releases.ensure_index([
                                 ('posted', pymongo.ASCENDING),
                                 ('tvrage._id', pymongo.ASCENDING),
                                 ('category._id', pymongo.ASCENDING)
                             ], background=True)
    db.releases.ensure_index([
                                 ('passworded', pymongo.ASCENDING),
                                 ('posted', pymongo.DESCENDING),
                             ], background=True)


if __name__ == '__main__':
    log.info('Creating indexes...')
    create_indexes()
    log.info('Completed. Mongo will build indexes in the background.')

########NEW FILE########
__FILENAME__ = groups
import argparse
import os
import re
import string
import sys

sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), '..'))

from pynab.db import db

VALID_CHARS = string.ascii_lowercase + string.digits + '.-_'


def is_valid_group_name(name):
    return all(i in VALID_CHARS for i in set(name)) \
       and name[0] in string.ascii_lowercase \
       and name[-1] in string.ascii_lowercase
       
def wildcard_to_regex(filter):
    ' converts a group name with a wildcard character (*) to a valid regex ' 
    regex = '^{}$'.format(filter.replace('.', '\\.').replace('*', '.*'))
    return re.compile(regex)

def find_matching_groups(names, expand=True):
    ' find all groups in the db that match any of >names< '
    ' some names may have the wildcard character * '
    # if no name if provided, return all groups
    if not names:
        return list(db.groups.find()), ()
    
    # if a single name if provided instead of a list,
    # make a list so we can process it
    if isinstance(names, str):
        names = [names]
    
    matched_groups = []
    skipped_names = []
        
    for groupname in names:
        # handle wildcard character '*'
        # regex search is done only if needed
        if '*' in groupname and expand:
            regex = wildcard_to_regex(groupname)
            groups = db.groups.find({'name': regex})
            if groups:
                matched_groups.extend(groups)
            else:
                skipped_names.append(groupname)
        else:
            group = db.groups.find_one({'name': groupname})
            if group:
                matched_groups.append(group)
            else:
                skipped_names.append(groupname)
                
    return matched_groups, skipped_names


def add(args):
    enable = 0 if args.disabled else 1
    existing_groups, new_names = find_matching_groups(args.groups, expand=False)
    for group in existing_groups:
        print('Group {} is already in the database, skipping'.format(group['name']))
    for groupname in new_names:
        if is_valid_group_name(groupname):
            db.groups.insert({'name': groupname, 'active': enable})
        else:
            print("Group name '{}' is not valid".format(groupname))
        
def remove(args):
    groups, skipped_names = find_matching_groups(args.groups)
    for group in groups:
        db.groups.remove(group['_id'])
    if skipped_names:
        print('These groups were not in the database and were skipped:')
        for name in skipped_names:
            print('  ', name)

def enable(args):
    groups, skipped_names = find_matching_groups(args.groups)
    for group in groups:
        db.groups.update({'_id': group['_id']}, {'$set': {'active': 1}})
    if skipped_names:
        print('These groups were not in the database and were skipped:')
        for name in skipped_names:
            print('  ', name)

def disable(args):
    groups, skipped_names = find_matching_groups(args.groups)
    for group in groups:
        db.groups.update({'_id': group['_id']}, {'$set': {'active': 0}})
    if skipped_names:
        print('These groups were not in the database and were skipped:')
        for name in skipped_names:
            print('  ', name)

def list_(args):
    groups, skipped_names = find_matching_groups(args.filter)
    groups.sort(key=lambda group: group['name'])

    for group in groups:
        if group['active']:
            print(group['name'])
        else:
            print("{} (disabled)".format(group['name']))


def main(argv):

    parser = argparse.ArgumentParser(description='Manages groups. Added groups are enabled by default')
    subparsers = parser.add_subparsers()
    
    parser_add = subparsers.add_parser("add", aliases=["a"])
    parser_add.add_argument("groups", nargs="+", help="group names to add")
    parser_add.add_argument("-d", "--disabled", action="store_true", help="set added groups as disabled")
    parser_add.set_defaults(func=add)
    
    parser_remove = subparsers.add_parser("remove", aliases=["r", "rem"])
    parser_remove.add_argument("groups", nargs="+", help="group names to remove")
    parser_remove.set_defaults(func=remove)
    
    parser_enable = subparsers.add_parser("enable", aliases=["e"])
    parser_enable.add_argument("groups", nargs="+", help="group names to enable")
    parser_enable.set_defaults(func=enable)
    
    parser_disable = subparsers.add_parser("disable", aliases=["d"])
    parser_disable.add_argument("groups", nargs="+", help="group names to disable")
    parser_disable.set_defaults(func=disable)
    
    parser_list = subparsers.add_parser("list", aliases=["l"])
    parser_list.add_argument("filter", nargs="*", help="search filter(s)")
    parser_list.set_defaults(func=list_)
    
    args = parser.parse_args(argv)
    if hasattr(args, 'func'):
        args.func(args)
    else:
        parser.print_help()
        

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
    

########NEW FILE########
__FILENAME__ = import
import argparse
import os
import sys

sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), '..'))

from pynab import log
import pynab.nzbs
import scripts.process_uncategorised

parser = argparse.ArgumentParser(
    description='Recursively import NZBs into Pynab. NOTE: DESTRUCTIVE. Will delete NZB upon successful import. Don\'t run it on a directory you may need to use again.')
parser.add_argument('directory')

if __name__ == '__main__':
    args = parser.parse_args()

    print(
        'NOTE: DESTRUCTIVE. Will delete NZB upon successful import. Don\'t run it on a directory you may need to use again.')
    input('To continue, press enter. To exit, press ctrl-c.')

    for root, dirs, files in os.walk(args.directory):
        for name in files:
            print('Importing {0}...'.format(os.path.join(root, name)))
            if pynab.nzbs.import_nzb(os.path.join(root, name)):
                os.remove(os.path.join(root, name))

    log.info('Import completed. Running scripts/process_uncategorised.py to fix release categories...')
    scripts.process_uncategorised.fix_uncategorised()
    log.info('Completed.')
########NEW FILE########
__FILENAME__ = postprocess_nfos_rars
import argparse
import os
import sys

sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), '..'))

import pynab.groups
import pynab.nfos
import pynab.rars

parser = argparse.ArgumentParser(description='''
Post-process NFOs and RARs for a particular category.

Note that this will process all of the releases in the specified category,
and could take a long time.
''')
parser.add_argument('category', help='(Sub)Category ID to post-process')

args = parser.parse_args()

if args.category:
    pynab.nfos.process(0, args.category)
    pynab.rars.process(0, args.category)
########NEW FILE########
__FILENAME__ = process
import argparse
import os
import sys

sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), '..'))

import pynab.binaries
import pynab.releases

parser = argparse.ArgumentParser(description='''
Process binaries and releases for all parts stored in the database.

This pretty much just runs automatically and does its own thing.
''')

args = parser.parse_args()

pynab.binaries.process()
pynab.releases.process()
########NEW FILE########
__FILENAME__ = process_min_archives
import os
import sys

sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), '..'))

from pynab.db import db
import pynab.nzbs
import config


def process_minarchives():
    """Delete releases that don't conform to min_archives directive."""
    for release in db.releases.find():
        data = pynab.nzbs.get_nzb_dict(release['nzb'])

        if data['rar_count'] + data['zip_count'] < config.postprocess.get('min_archives', 1):
            print('DELETING: Release {} has {} rars and {} zips.'.format(release['search_name'], data['rar_count'],
                                                                         data['zip_count']))
            db.releases.remove({'_id': release['_id']})


if __name__ == '__main__':
    print('Process and enforce min_files script.')
    print('Please note that this script is destructive and will delete releases.')
    print('This will clear releases that do not fit the min_archives dictated in config.py.')
    print('This action is permanent and cannot be undone.')
    input('To continue, press enter. To exit, press ctrl-c.')

    process_minarchives()

    print('Completed.')
########NEW FILE########
__FILENAME__ = process_uncategorised
"""
This script will categorise un-categorised releases.

These can pop up from time to time - sometimes from NZB imports with no specified category.

If you get an error about releases without groups, try this in mongo:
# db.releases.find({group:null}).count()
There shouldn't be too many - if not, remove them.
"""
import os
import sys

sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), '..'))

from pynab.db import db
from pynab import log

import pynab.categories


def fix_uncategorised():
    releases = db.releases.find({'$or': [{'category._id': {'$exists': False}}, {'category': None}]})
    total = releases.count()

    found = 0
    for release in releases:
        log.info('Scanning release: {}'.format(release['search_name']))

        if 'group' not in release:
            log.error('Release had no group! Think about deleting releases without groups.')
            continue

        category_id = pynab.categories.determine_category(release['search_name'], release['group']['name'])
        if category_id:
            category = db.categories.find_one({'_id': category_id})
            # if this isn't a parent category, add those details as well
            if 'parent_id' in category:
                category['parent'] = db.categories.find_one({'_id': category['parent_id']})

            db.releases.update({'_id': release['_id']}, {'$set': {'category': category}})
            found += 1

    log.info('Categorised {:d}/{:d} uncategorised releases.'.format(found, total))


if __name__ == '__main__':
    fix_uncategorised()
########NEW FILE########
__FILENAME__ = quick_postprocess
import sys
import os

sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), '..'))

import pynab.tvrage
import pynab.imdb


def local_postprocess():
    pynab.tvrage.process(0, False)
    pynab.imdb.process(0, False)


if __name__ == '__main__':
    print('This script will attempt to post-process releases against local databases.')
    print('After importing or collecting a large batch of releases, you can run this once prior to start.py.')
    print('This will check all local matches first, leaving start.py to just do remote matching.')
    print('It\'ll really just save some time.')
    print()
    input('To continue, press enter. To exit, press ctrl-c.')
    local_postprocess()
########NEW FILE########
__FILENAME__ = rename_bad_releases
import argparse
import os
import sys

sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), '..'))

import pynab.releases
from pynab.db import db
from pynab import log


def rename_bad_releases(category):
    count = 0
    s_count = 0
    for release in db.releases.find({'category._id': int(category), 'unwanted': {'$ne': True}, '$or': [{'nfo': {'$nin': [None, False]}}, {'files.count': {'$exists': True}}]}):
        count += 1
        name, category_id = pynab.releases.discover_name(release)

        if name and not category_id:
            # don't change anything, it was fine
            pass
        elif name and category_id:
            # we found a new name!
            s_count += 1

            category = db.categories.find_one({'_id': category_id})
            category['parent'] = db.categories.find_one({'_id': category['parent_id']})

            db.releases.update({'_id': release['_id']},
                {
                    '$set': {
                        'search_name': pynab.releases.clean_release_name(name),
                        'category': category,
                    }
                }
            )

        else:
            # bad release!
            log.info('Noting unwanted release {} ({:d})...'.format(
                release['search_name'], release['category']['_id'],
            ))

            db.releases.update({'_id': release['_id']},
                {
                    '$set': {
                        'unwanted': True
                    }
                }
            )

    log.info('rename: successfully renamed {} of {} releases'.format(s_count, count))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='''
    Rename Bad Releases

    Takes either a regex_id or category_id and renames releases from their NFO or filenames.
    Note that you really need to finish post-processing before you can do this.
    ''')
    # not supported yet
    #parser.add_argument('--regex', nargs='?', help='Regex ID of releases to rename')
    parser.add_argument('category', help='Category to rename')

    args = parser.parse_args()

    print('Note: Don\'t run this on a category like TV, only Misc-Other and Books.')
    input('To continue, press enter. To exit, press ctrl-c.')

    if args.category:
        rename_bad_releases(args.category)
########NEW FILE########
__FILENAME__ = update
import argparse
import os
import sys

sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), '..'))

import pynab.groups
from pynab.db import db

parser = argparse.ArgumentParser(description='''
Fetch and parse parts and messages for active groups.

Updating a specific group will force an update regardless of whether the group is active.
Updating all groups will only update active groups.
''')
parser.add_argument('group', nargs='?', help='Group to update (leave blank for all)')

args = parser.parse_args()

if args.group:
    group = db.groups.find_one({'name': args.group})
    if group:
        if pynab.groups.update(group['name']):
            print('Group {0} successfully updated!'.format(group['name']))
        else:
            print('Problem updating group {0}.'.format(group['name']))
    else:
        print('No group called {0} exists in the db.'.format(args.group))
else:
    for group in db.groups.find({'active': 1}):
        if pynab.groups.update(group['name']):
            print('Group {0} successfully updated!'.format(group['name']))
        else:
            print('Problem updating group {0}.'.format(group['name']))
########NEW FILE########
__FILENAME__ = update_regex
import argparse
import os
import sys

sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), '..'))

import pynab.util

parser = argparse.ArgumentParser(description='''
Updates regex collection.
''')

args = parser.parse_args()

pynab.util.update_regex()
########NEW FILE########
__FILENAME__ = start
import argparse
import multiprocessing
import time
import logging
import pytz
import datetime
import traceback

from pynab import log, log_descriptor
from pynab.db import db

import pynab.groups
import pynab.binaries
import pynab.releases
import pynab.tvrage
import pynab.rars
import pynab.nfos
import pynab.imdb
import config


def mp_error(msg, *args):
    return multiprocessing.get_logger().exception(msg, *args)


def update(group_name):
    pynab.groups.update(group_name)


def process_tvrage(limit):
    pynab.tvrage.process(limit)


def process_nfos(limit):
    pynab.nfos.process(limit)


def process_rars(limit):
    pynab.rars.process(limit)


def process_imdb(limit):
    pynab.imdb.process(limit)


def daemonize(pidfile):
    try:
        import traceback
        from daemonize import Daemonize

        fds = []
        if log_descriptor:
            fds = [log_descriptor]

        daemon = Daemonize(app='pynab', pid=pidfile, action=main, keep_fds=fds)
        daemon.start()
    except SystemExit:
        raise
    except:
        log.critical(traceback.format_exc())


def main():
    log.info('starting update...')

    # print MP log as well
    multiprocessing.log_to_stderr().setLevel(logging.DEBUG)

    while True:
        active_groups = [group['name'] for group in db.groups.find({'active': 1})]
        if active_groups:
            # if maxtasksperchild is more than 1, everything breaks
            # they're long processes usually, so no problem having one task per child
            pool = multiprocessing.Pool(processes=config.scan.get('update_threads', 4), maxtasksperchild=1)
            result = pool.map_async(update, active_groups)
            try:
                result.get()
            except Exception as e:
                mp_error(e)

            pool.terminate()
            pool.join()

            # process binaries
            # TODO: benchmark threading for this - i suspect it won't do much (mongo table lock)
            pynab.binaries.process()

            # process releases
            # TODO: likewise
            pynab.releases.process()

            # clean up dead binaries
            dead_time = pytz.utc.localize(datetime.datetime.now()) - datetime.timedelta(days=config.scan.get('dead_binary_age', 3))
            db.binaries.remove({'posted': {'$lte': dead_time}})

            # wait for the configured amount of time between cycles
            update_wait = config.scan.get('update_wait', 300)
            log.info('sleeping for {:d} seconds...'.format(update_wait))
            time.sleep(update_wait)
        else:
            log.info('no groups active, cancelling start.py...')
            break
        
        
if __name__ == '__main__':
    argparser = argparse.ArgumentParser(description="Pynab main indexer script")
    argparser.add_argument('-d', '--daemonize', action='store_true', help='run as a daemon')
    argparser.add_argument('-p', '--pid-file', help='pid file (when -d)')

    args = argparser.parse_args()

    if args.daemonize:
        pidfile = args.pid_file or config.scan.get('pid_file')
        if not pidfile:
            log.error("A pid file is required to run as a daemon, please supply one either in the config file '{}' or as argument".format(config.__file__))
        else:
            daemonize(pidfile)
    else:
        main()

########NEW FILE########
__FILENAME__ = test_pynab
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
test_pynab
----------------------------------

Tests for `pynab` module.
"""

import unittest
import pprint

from pynab.server import Server
from pynab.db import db
import pynab.binaries
import pynab.releases
import pynab.parts
import pynab.categories
import pynab.groups
import pynab.nzbs
import pynab.tvrage
import pynab.imdb
import pynab.rars
import pynab.nfos


class TestPynab(unittest.TestCase):
    def setUp(self):
        self.server = None

    def test_connect(self):
        self.server = Server()
        self.server.connect()
        self.assertTrue(self.server)

    def test_capabilities(self):
        self.test_connect()
        print(self.server.connection.getcapabilities())

    def test_fetch_headers(self):
        self.test_connect()
        groups = ['alt.binaries.teevee', 'alt.binaries.e-book', 'alt.binaries.moovee']
        for group in groups:
            (_, _, first, last, _) = self.server.connection.group(group)
            for x in range(0, 20000, 10000):
                y = x + 10000 - 1
                parts = self.server.scan(group, last - y, last - x)
                pynab.parts.save_all(parts)

    def test_process_binaries(self):
        pynab.binaries.process()

    def test_process_releases(self):
        pynab.releases.process()

    def test_all(self):
        self.test_fetch_headers()
        self.test_process_binaries()
        self.test_process_releases()

    def test_print_binaries(self):
        pprint.pprint([b for b in db.binaries.find()])

    def test_day_to_post(self):
        self.test_connect()
        self.server.day_to_post('alt.binaries.teevee', 5)

    def test_group_update(self):
        pynab.groups.update('alt.binaries.teevee')

    def test_group_backfill(self):
        pynab.groups.backfill('alt.binaries.teevee')

    def test_tvrage_process(self):
        pynab.tvrage.process(100)

    def test_omdb_search(self):
        print(pynab.imdb.search('South Park Bigger Longer Uncut', '1999'))

    def test_omdb_get_details(self):
        print(pynab.imdb.get_details('tt1285016'))

    def test_nzb_get(self):
        release = db.releases.find_one()
        pprint.pprint(pynab.nzbs.get_nzb_dict(release['nzb']))

    def test_rar_process(self):
        pynab.rars.process(5)

    def test_nfo_process(self):
        pynab.nfos.process(5)

    def test_compress(self):
        server = Server()
        server.connect()
        server.scan('alt.binaries.teevee', 563011234, 563031234)

    def test_uncompress(self):
        server = Server()
        server.connect(False)
        server.scan('alt.binaries.teevee', 563011234, 563031234)

    def tearDown(self):
        try:
            self.server.connection.quit()
        except:
            pass


if __name__ == '__main__':
    unittest.main()
########NEW FILE########
__FILENAME__ = test_scripts
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
test_scripts
----------------------------------

Tests for `scripts` module.
"""

import unittest

import config as project_config
import pynab.util
from scripts import convert_from_newznab


class TestScripts(unittest.TestCase):
    def setUp(self):
        self.test_connect()

    def test_connect(self):
        self.mysql = convert_from_newznab.mysql_connect(project_config.mysql)

        self.assertTrue(self.mysql)

    def test_convert_groups(self):
        convert_from_newznab.convert_groups(self.mysql)

    def test_convert_categories(self):
        convert_from_newznab.convert_categories(self.mysql)

    def test_convert_regex(self):
        convert_from_newznab.convert_regex(self.mysql)

    def test_convert_blacklist(self):
        convert_from_newznab.convert_blacklist(self.mysql)

    def test_convert_users(self):
        convert_from_newznab.convert_users(self.mysql)

    def test_convert_tvdb(self):
        convert_from_newznab.convert_tvdb(self.mysql)

    def test_convert_tvrage(self):
        convert_from_newznab.convert_tvrage(self.mysql)

    def test_convert_imdb(self):
        convert_from_newznab.convert_imdb(self.mysql)

    def test_update_regex(self):
        pynab.util.update_regex()

    def test_update_blacklist(self):
        pynab.util.update_blacklist()

    def test_convert_all(self):
        self.test_convert_groups()
        self.test_convert_categories()
        self.test_convert_regex()
        self.test_convert_blacklist()
        self.test_convert_users()
        self.test_convert_tvdb()
        self.test_convert_tvrage()
        self.test_convert_imdb()

    def tearDown(self):
        self.mysql.close()


if __name__ == '__main__':
    unittest.main()
########NEW FILE########
__FILENAME__ = test_tvrage
import logging
import time
import unittest

from pynab.db import db
from pynab import tvrage 


tvrage.log.setLevel(logging.DEBUG)

class TestTvRage(unittest.TestCase):
    def test_search(self):
        for release in db.releases.find({'tvrage.possible': {'$exists': False}}):
            show = tvrage.parse_show(release['search_name'])
            if show:
                rage_data = tvrage.search(show)
                time.sleep(1)

if __name__ == '__main__':
    unittest.main()
########NEW FILE########
