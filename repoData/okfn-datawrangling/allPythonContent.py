__FILENAME__ = cordis
from urlparse import urljoin
from lxml import html

INITIAL_URL = 'http://cordis.europa.eu/fetch?CALLER=FP7_PROJ_EN'

def get_index():
    """ Traverse the search results of an empty query for projects in 
    the CORDIS database. """

    # fetch an initial page:
    doc = html.parse(INITIAL_URL)
    # infinite loop isn't nice, but we'll break when no 'next' link is
    # available.
    while True:
        # iterate over the links for all projects on this page
        for project_link in doc.findall('//div[@id="PResults"]//a'):

            # join up URLs to generate the proper path
            href = project_link.get('href').replace('..', '')
            yield urljoin(INITIAL_URL, href)

        next_url = None

        # look at all links in the navigation section of the listing
        for nav in doc.findall('//p[@class="PNav"]/a'):

            # if the link is a 'next' link, follow it
            if 'Next' in nav.text:
                href = nav.get('href').replace('..','')
                next_url = urljoin(INITIAL_URL, href)

                # replace the document to traverse the next page in
                # the following iteration
                doc = html.parse(next_url)

        # no next link was found, so cancel
        if not next_url:
            break

if __name__ == '__main__':
    for link in get_index():
        print link

########NEW FILE########
__FILENAME__ = csv2sqlite
#!/usr/bin/env python
# A simple Python script to convert csv files to sqlite (with type guessing)
#
# @author: Rufus Pollock
# Placed in the Public Domain
import csv
import sqlite3

def convert(filepath_or_fileobj, dbpath, table='data'):
    if isinstance(filepath_or_fileobj, basestring):
        fo = open(filepath_or_fileobj)
    else:
        fo = filepath_or_fileobj
    reader = csv.reader(fo)

    types = _guess_types(fo)
    fo.seek(0)
    headers = reader.next()

    _columns = ','.join(
        ['%s %s' % (header, _type) for (header,_type) in zip(headers, types)]
        )

    conn = sqlite3.connect(dbpath)
    c = conn.cursor()
    c.execute('CREATE table %s (%s)' % (table, _columns))

    _insert_tmpl = 'insert into %s values (%s)' % (table,
        ','.join(['?']*len(headers)))
    for row in reader:
        c.execute(_insert_tmpl, row)

    conn.commit()
    c.close()

def _guess_types(fileobj, max_sample_size=100):
    '''Guess column types (as for SQLite) of CSV.

    :param fileobj: read-only file object for a CSV file.
    '''
    reader = csv.reader(fileobj)
    # skip header
    _headers = reader.next()
    types = ['text'] * len(_headers)
    # order matters
    # (order in form of type you want used in case of tie to be last)
    options = [
        ('real', float),
        ('integer', int),
        ('text', unicode)
        # 'date',
        ]
    # for each column a set of bins for each type counting successful casts
    perresult = {
        'integer': 0,
        'real': 0,
        'text': 0
        }
    results = [ dict(perresult) for x in range(len(_headers)) ]
    for count,row in enumerate(reader):
        for idx,cell in enumerate(row):
            cell = cell.strip()
            for key,cast in options:
                try:
                    # for null cells we can assume success
                    if cell:
                        cast(cell)
                    results[idx][key] = (results[idx][key]*count + 1) / float(count+1)
                except (ValueError), inst:
                    pass
        if count >= max_sample_size:
            break
    for idx,colresult in enumerate(results):
        for _type, dontcare in options:
            if colresult[_type] == 1.0:
                types[idx] = _type
    return types

def test():
    '''Simple test case'''
    import StringIO
    import os
    fileobj = StringIO.StringIO(
'''heading_1,heading_2,heading_3
abc,1,1.0
xyz,2,2.0
efg,3,3.0'''
    )
    dbpath = '/tmp/csv2sqlite-test-data.db'
    if os.path.exists(dbpath):
        os.remove(dbpath)
    table = 'data'
    convert(fileobj, dbpath, table)
    conn = sqlite3.connect(dbpath)
    c = conn.cursor()
    c.execute('select count(*) from %s' % table);
    row = c.next()
    assert row[0] == 3, row

if __name__ == '__main__':
    import sys
    if len(sys.argv) < 3:
        print('''csv2sqlite.py {csv-file-path} {sqlite-db-path} [{table-name}]

Convert a csv file to a table in an sqlite database (which need not yet exist).

* table-name is optional and defaults to 'data'
''')
        sys.exit(1)
    convert(*sys.argv[1:])


########NEW FILE########
__FILENAME__ = threads
import logging
from Queue import Queue
from threading import Thread

def threaded(items, func, num_threads=10, max_queue=200):
    """ Run a function against each output of a given 
    generator, distributing load over a given number of 
    threads. A queue size can be specfied to define the 
    number of items that will at most be stored on the 
    task queue before blocking the generator.
    """
    def queue_consumer():
        # This closure will be run as the main loop of each 
        # thread, handling exceptions in a slightly brutal 
        # manner (i.e. you may want to document them in a 
        # seperate table of the database you scrape into).
        while True:
            item = queue.get(True)
            try:
                func(item)
            except Exception, e:
                logging.exception(e)
            queue.task_done()

    queue = Queue(maxsize=max_queue)

    for i in range(num_threads):
        # Create the worker threads.
        t = Thread(target=queue_consumer)
        t.daemon = True
        t.start()

    for item in items:
        # Fill up the queue. This will block when max_size 
        # has been reached and only continue when items 
        # have been processed off the queue. This means that
        # when you are scraping a (quasi-)infinite listing,
        # only the required section of the listing will be 
        # read.
        queue.put(item, True)

    # wait for all tasks to be processed.
    queue.join()

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# datapatterns documentation build configuration file, created by
# sphinx-quickstart on Wed Jul 20 14:46:06 2011.
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

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.intersphinx', 'sphinx.ext.todo', 'sphinx.ext.pngmath']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u"Data Wrangling Handbook" 
copyright = u'&copy; 2011-2012, Open Knowledge Foundation'

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

# The reST default role (used for this markup: `text`) to use for all documents.
#default_role = None

# If true, '()' will be appended to :func: etc. cross-reference text.
#add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
#add_module_names = True

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
show_authors = True

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# A list of ignored prefixes for module index sorting.
#modindex_common_prefix = []


# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
sys.path.append(os.path.abspath('_themes'))
html_theme_path = ['_themes']
html_theme = 'sphinx-theme-okfn'

html_theme_options = {
        'logo_icon': 'http://assets.okfn.org/p/datapatterns/img/datapatterns-header-logo.png',
        'google_analytics_id': 'UA-8271754-43'
    }
html_use_modindex = False
html_sidebars = {
    '**':       ['localtoc.html', 'globaltoc.html','relations.html']
}

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
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
html_show_sourcelink = False

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
html_show_sphinx = False

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is True.
#html_show_copyright = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# This is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = None

# Output file base name for HTML help builder.
htmlhelp_basename = 'datapatternsdoc'


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'datawrangling-handbook.tex', u'Data Wrangling Handbook',
   u'Open Knowledge Foundation', 'manual'),
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
    ('index', 'datawrangling', u'Data Wrangling Handbook',
     [u'Open Knowledge Foundation'], 1)
]


# -- Options for Epub output ---------------------------------------------------

# Bibliographic Dublin Core info.
epub_title = u'Data Wrangling Handbook'
epub_author = u'Open Knowledge Foundation'
epub_publisher = u'Open Knowledge Foundation'
epub_copyright = u'2011, Open Knowledge Foundation'

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

# HTML files that should be inserted before the pages created by sphinx.
# The format is a list of tuples containing the path and title.
#epub_pre_files = []

# HTML files shat should be inserted after the pages created by sphinx.
# The format is a list of tuples containing the path and title.
#epub_post_files = []

# A list of files that should not be packed into the epub file.
#epub_exclude_files = []

# The depth of the table of contents in toc.ncx.
#epub_tocdepth = 3

# Allow duplicate toc entries.
#epub_tocdup = True


# Example configuration for intersphinx: refer to the Python standard library.
intersphinx_mapping = {'http://docs.python.org/': None}

########NEW FILE########
__FILENAME__ = upload
''' Upload datawrangling handbook to wordpress site.

Copy this file to same directory as your sphinx build directory and then do

    python upload.py -h

NB: You need to enable XML-RPC access to the wordpress site (via Settings -> Writing)

NB: this requires pywordpress (pip install pywordpress) and associated config
file - see https://github.com/rgrp/pywordpress
'''

import os
import optparse
import pywordpress
import itertools
from pyquery import PyQuery
import re
import pprint
import datetime


def strip_if_not_pre(lines):
  """strip line feeds if not in a <pre>"""
  lines=(i for i in lines) # convert lines to a generator 
  pre=False
  ispre=re.compile("<pre>")
  ispreout=re.compile("</pre>")
  line=lines.next()
  while line:
    if ispre.search(line):
      pre=True
    if ispreout.search(line):
      pre=False
    yield line if pre else line.strip() + " "
    line=lines.next()  

# TODO: deal with utf8 encoding
def prepare_html(fileobj):
    """ prepares the html for wordpress pages """
    pq=PyQuery("".join(strip_if_not_pre(fileobj))) 
    
    pq("a.headerlink").remove()
    # Do we want title at all?
    if pq("div.section h1"):
      title= pq("div.section h1")[0].text
      pq("div.section h1:first").remove()
    else:
      title=""

    # TODO: insert toc (??)

    out = PyQuery(pq("div.content").outerHtml() )
    # insert after h1 on 4th ine
    # lines = out.split('\n')
    # out = '\n'.join(lines[:4] + [ '[toc]' ] + lines[4:])

    # now various regex
    
    out.append("<p><small>%s</small></p>"%pq("p.meta").text())
    out=out.outerHtml()
    # replace .html with / and index.html with simple ./
    pattern = '(internal" href=".[^"]*)index\.html"'
    out = re.sub(pattern, '\\1"', out)
    pattern = 'internal" href="index\.html"'
    out = re.sub(pattern, 'href="./"', out)
    pattern = '(internal" href="[^"]*).html"'
    out = re.sub(pattern, '\\1/"', out)
    pattern = '(internal" href="[^"]*).html#([^"]*)"'
    out = re.sub(pattern, '\\1/#\\2"', out)
    pattern = '(internal" href="[^"]*/)index/#([^"]*)"'
    out = re.sub(pattern, '\\1/#\\2"', out)
    
    
    return (out, title)

def upload(wordpress_site_url='', handbook_path='/handbook/'):
    '''Convert and upload built sphinx content to destination site

    1. Clean up and extract html for uploading
    2. Upload

    NB: you'll need a config.ini to exist as per pywordpress requirements
    '''
    pages = {}
    for (root, dirs, files) in os.walk('build/html'):
        files=itertools.ifilter(lambda x: re.search(".html$",x),files)
        if '_sources' in root:
            continue
        for f in files:
            path = os.path.join(root, f)
            print path
            subpath = os.path.join(
                root[len('build/html'):].lstrip('/'),
                # index.html => /
                f.replace('index.html', '')
                )
            urlpath = handbook_path + os.path.splitext(subpath)[0]
            # everything has a trailing '/' e.g. /handbook/introduction/
            if not urlpath.endswith('/'):
                urlpath += '/'
            (out, title) = prepare_html(open(path))
            pages[urlpath] = {
                'title': title,
                'description': out,
                # http://codex.wordpress.org/XML-RPC_WordPress_API/Pages#wp.newPage
                'mt_allow_comments': 'open'
            }

    # do the upload
    wp = pywordpress.Wordpress.init_from_config('config.ini')
    wp.verbose =True
    print 'Creating pages in wordpress'
    changes = wp.create_many_pages(pages)
    print 'Summary of changes'
    pprint.pprint(changes)


if __name__ == '__main__':
    usage = '''%prog {action}

    upload: upload handbook to website
    '''
    parser = optparse.OptionParser(usage)
    options, args = parser.parse_args()
    if len(args) < 1:
        parser.print_help()
        sys.exit(1)
    action = args[0]
    if action == 'upload':
        upload()
    else:
        parser.print_help()
        sys.exit(1)

########NEW FILE########
