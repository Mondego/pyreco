__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# Pyblosxom documentation build configuration file, created by
# sphinx-quickstart on Mon Feb 16 00:26:34 2009.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# The contents of this file are pickled, so don't put values in the namespace
# that aren't pickleable (module imports are okay, they're removed automatically).
#
# All configuration values have a default value; values that are commented out
# serve to show the default value.

import sys, os

# If your extensions are in another directory, add it here. If the directory
# is relative to the documentation root, use os.path.abspath to make it
# absolute, like shown here.
#sys.path.append(os.path.abspath('some/directory'))

# General configuration
# ---------------------

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The master toctree document.
master_doc = 'index'

# General substitutions.
project = 'PyBlosxom'
copyright = 'Creative Commons CC0 - http://creativecommons.org/publicdomain/zero/1.0/'

# The default replacements for |version| and |release|, also used in various
# other places throughout the built documents.
#
# The short X.Y version.
version = '1.5.2'
# The full version, including alpha/beta/rc tags.
release = '1.5.2'

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
today_fmt = '%B %d, %Y'

# List of documents that shouldn't be included in the build.
#unused_docs = []

# List of directories, relative to source directories, that shouldn't be searched
# for source files.
#exclude_dirs = []

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


# Options for HTML output
# -----------------------

# The style sheet to use for HTML and HTML Help pages. A file of that name
# must exist either in Sphinx' static/ path, or in one of the custom paths
# given in html_static_path.
html_style = 'default.css'

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
#html_title = None

# A shorter title for the navigation bar.  Default is the same as html_title.
#html_short_title = None

# The name of an image file (within the static path) to place at the top of
# the sidebar.
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
#html_use_modindex = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, the reST sources are included in the HTML build as _sources/<name>.
#html_copy_source = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# If nonempty, this is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = ''

# Output file base name for HTML help builder.
htmlhelp_basename = 'Pyblosxomdoc'


# Options for LaTeX output
# ------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, document class [howto/manual]).
latex_documents = [
  ('index', 'Pyblosxom.tex', 'Pyblosxom Documentation',
   'PyBlosxom CC0', 'manual'),
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
__FILENAME__ = extract_docs_from_plugins
#!/usr/bin/python

#######################################################################
# This file is part of Pyblosxom.
#
# Copyright (c) 2011 Will Kahn-Greene
#
# Pyblosxom is distributed under the MIT license.  See the file
# LICENSE for distribution details.
#######################################################################

"""
This script generates documentation for plugins from the plugin docstrings.
"""

import os
import ast
import sys


# skip these because they're not plugins
SKIP = ("akismet.py", "__init__.py")


HELP = """extract_docs_from_plugins

This goes through the plugins in ../Pyblosxom/plugins/, extracts the
docstrings, and generates docs files for each one.  It puts them all in
a plugins/ directory here.

Docstrings for plugins should be formatted in restructured text.
"""

TEMPLATE = """
.. only:: text

   This document file was automatically generated.  If you want to edit
   the documentation, DON'T do it here--do it in the docstring of the
   appropriate plugin.  Plugins are located in ``Pyblosxom/plugins/``.

%(line)s
%(title)s
%(line)s

%(body)s


License
=======

Plugin is distributed under license: %(license)s
"""

def get_info(node, info_name):
    # FIXME - this is inefficient since it'll traverse the entire ast
    # but we only really need to look at the top level.
    for mem in ast.walk(node):
        if not isinstance(mem, ast.Assign):
            continue

        for target in mem.targets:
            if not isinstance(target, ast.Name):
                continue

            if target.id == info_name:                
                return mem.value.s

    print "missing %s" % info_name
    return None


def build_docs_file(filepath):
    try:
        fp = open(filepath, "r")
    except (IOError, OSError):
        return False

    node = ast.parse(fp.read(), filepath, 'exec')

    title = (" %s - %s... " % (
            os.path.splitext(os.path.basename(filepath))[0],
            get_info(node, "__description__")[:35]))
    line = "=" * len(title)
    body = ast.get_docstring(node, True)
    license_ = get_info(node, "__license__")

    return (TEMPLATE % {
            "line": line,
            "title": title,
            "body": body,
            "license": license_})


def save_entry(filepath, entry):
    parent = os.path.dirname(filepath)
    if not os.path.exists(parent):
        os.makedirs(parent)

    f = open(filepath, "w")
    f.write(entry)
    f.close()


def get_plugins(plugindir, outputdir):
    for root, dirs, files in os.walk(plugindir):
        # remove skipped directories so we don't walk through them
        for mem in SKIP:
            if mem in dirs:
                dirs.remove(mem)
                break

        for file_ in files:
            if ((file_.startswith("_") or not file_.endswith(".py") or
                 file_ in SKIP)):
                continue

            filename = os.path.join(root, file_)
            print "working on %s" % filename

            entry = build_docs_file(filename)

            output_filename = os.path.basename(filename)
            output_filename = os.path.splitext(output_filename)[0] + ".rst"
            output_filename = os.path.join(outputdir, output_filename)

            save_entry(output_filename, entry)


def main(args):
    print "update_registry.py"

    outputdir = "./plugins/"

    plugindir = "../Pyblosxom/plugins/"

    print "plugindir: %s" % plugindir
    if not os.path.exists(plugindir):
        print "Plugindir doesn't exist."
        sys.exit(1)

    print "outputdir: %s" % outputdir
    if not os.path.exists(outputdir):
        os.makedirs(outputdir)

    get_plugins(plugindir, outputdir)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

########NEW FILE########
__FILENAME__ = blosxom
import locale
import os
import sys
import time
from Pyblosxom import tools
from Pyblosxom.entries.fileentry import FileEntry


def blosxom_handler(request):
    """This is the default blosxom handler.

    It calls the renderer callback to get a renderer.  If there is no
    renderer, it uses the blosxom renderer.

    It calls the pathinfo callback to process the path_info http
    variable.

    It calls the filelist callback to build a list of entries to
    display.

    It calls the prepare callback to do any additional preparation
    before rendering the entries.

    Then it tells the renderer to render the entries.

    :param request: the request object.
    """
    config = request.get_configuration()
    data = request.get_data()

    # go through the renderer callback to see if anyone else wants to
    # render.  this renderer gets stored in the data dict for
    # downstream processing.
    rend = tools.run_callback('renderer',
                              {'request': request},
                              donefunc=lambda x: x is not None,
                              defaultfunc=lambda x: None)

    if not rend:
        # get the renderer we want to use
        rend = config.get("renderer", "blosxom")

        # import the renderer
        rend = tools.importname("Pyblosxom.renderers", rend)

        # get the renderer object
        rend = rend.Renderer(request, config.get("stdoutput", sys.stdout))

    data['renderer'] = rend

    # generate the timezone variable
    data["timezone"] = time.tzname[time.localtime()[8]]

    # process the path info to determine what kind of blog entry(ies)
    # this is
    tools.run_callback("pathinfo",
                       {"request": request},
                       donefunc=lambda x: x is not None,
                       defaultfunc=blosxom_process_path_info)

    # call the filelist callback to generate a list of entries
    data["entry_list"] = tools.run_callback(
        "filelist",
        {"request": request},
        donefunc=lambda x: x is not None,
        defaultfunc=blosxom_file_list_handler)

    # figure out the blog-level mtime which is the mtime of the head
    # of the entry_list
    entry_list = data["entry_list"]
    if isinstance(entry_list, list) and len(entry_list) > 0:
        mtime = entry_list[0].get("mtime", time.time())
    else:
        mtime = time.time()
    mtime_tuple = time.localtime(mtime)
    mtime_gmtuple = time.gmtime(mtime)

    data["latest_date"] = time.strftime('%a, %d %b %Y', mtime_tuple)

    # Make sure we get proper 'English' dates when using standards
    loc = locale.getlocale(locale.LC_ALL)
    locale.setlocale(locale.LC_ALL, 'C')

    data["latest_w3cdate"] = time.strftime('%Y-%m-%dT%H:%M:%SZ',
                                           mtime_gmtuple)
    data['latest_rfc822date'] = time.strftime('%a, %d %b %Y %H:%M GMT',
                                              mtime_gmtuple)

    # set the locale back
    locale.setlocale(locale.LC_ALL, loc)

    # we pass the request with the entry_list through the prepare
    # callback giving everyone a chance to transform the data.  the
    # request is modified in place.
    tools.run_callback("prepare", {"request": request})

    # now we pass the entry_list through the renderer
    entry_list = data["entry_list"]
    renderer = data['renderer']

    if renderer and not renderer.rendered:
        if entry_list:
            renderer.set_content(entry_list)
            # Log it as success
            tools.run_callback("logrequest",
                               {'filename': config.get('logfile', ''),
                                'return_code': '200',
                                'request': request})
        else:
            renderer.add_header('Status', '404 Not Found')
            renderer.set_content(
                {'title': 'The page you are looking for is not available',
                 'body': 'Somehow I cannot find the page you want. ' +
                         'Go Back to <a href="%s">%s</a>?'
                         % (config["base_url"], config["blog_title"])})
            # Log it as failure
            tools.run_callback("logrequest",
                               {'filename': config.get('logfile', ''),
                                'return_code': '404',
                                'request': request})
        renderer.render()

    elif not renderer:
        output = config.get('stdoutput', sys.stdout)
        output.write("Content-Type: text/plain\n\n" +
                     "There is something wrong with your setup.\n" +
                     "Check your config files and verify that your " +
                     "configuration is correct.\n")

    cache = tools.get_cache(request)
    if cache:
        cache.close()


def blosxom_entry_parser(filename, request):
    """Open up a ``.txt`` file and read its contents.  The first line
    becomes the title of the entry.  The other lines are the body of
    the entry.

    :param filename: a filename to extract data and metadata from
    :param request: a standard request object

    :returns: dict containing parsed data and meta data with the
              particular file (and plugin)
    """
    config = request.get_configuration()

    entry_data = {}

    f = open(filename, "r")
    lines = f.readlines()
    f.close()

    # the file has nothing in it...  so we're going to return a blank
    # entry data object.
    if len(lines) == 0:
        return {"title": "", "body": ""}

    # the first line is the title
    entry_data["title"] = lines.pop(0).strip()

    # absorb meta data lines which begin with a #
    while lines and lines[0].startswith("#"):
        meta = lines.pop(0)
        # remove the hash
        meta = meta[1:].strip()
        meta = meta.split(" ", 1)
        # if there's no value, we append a 1
        if len(meta) == 1:
            meta.append("1")
        entry_data[meta[0].strip()] = meta[1].strip()

    # call the preformat function
    args = {'parser': entry_data.get('parser', config.get('parser', 'plain')),
            'story': lines,
            'request': request}
    entry_data["body"] = tools.run_callback(
        'preformat',
        args,
        donefunc=lambda x: x is not None,
        defaultfunc=lambda x: ''.join(x['story']))

    # call the postformat callbacks
    tools.run_callback('postformat',
                       {'request': request,
                        'entry_data': entry_data})

    return entry_data


def blosxom_file_list_handler(args):
    """This is the default handler for getting entries.  It takes the
    request object in and figures out which entries based on the
    default behavior that we want to show and generates a list of
    EntryBase subclass objects which it returns.

    :param args: dict containing the incoming Request object

    :returns: the content we want to render
    """
    request = args["request"]

    data = request.get_data()
    config = request.get_configuration()

    if data['bl_type'] == 'dir':
        file_list = tools.walk(request,
                               data['root_datadir'],
                               int(config.get("depth", "0")))
    elif data['bl_type'] == 'file':
        file_list = [data['root_datadir']]
    else:
        file_list = []

    entry_list = [FileEntry(request, e, data["root_datadir"]) for e in file_list]

    # if we're looking at a set of archives, remove all the entries
    # that aren't in the archive
    if data.get("pi_yr", ""):
        tmp_pi_mo = data.get("pi_mo", "")
        date_str = "%s%s%s" % (data.get("pi_yr", ""),
                               tools.month2num.get(tmp_pi_mo, tmp_pi_mo),
                               data.get("pi_da", ""))
        entry_list = [x for x in entry_list
                      if time.strftime("%Y%m%d%H%M%S", x["timetuple"]).startswith(date_str)]

    args = {"request": request, "entry_list": entry_list}
    entry_list = tools.run_callback("sortlist",
                                    args,
                                    donefunc=lambda x: x != None,
                                    defaultfunc=blosxom_sort_list_handler)

    args = {"request": request, "entry_list": entry_list}
    entry_list = tools.run_callback("truncatelist",
                                    args,
                                    donefunc=lambda x: x != None,
                                    defaultfunc=blosxom_truncate_list_handler)

    return entry_list


def blosxom_sort_list_handler(args):
    """Sorts the list based on ``_mtime`` attribute such that
    most recently written entries are at the beginning of the list
    and oldest entries are at the end.

    :param args: args dict with ``request`` object and ``entry_list``
                 list of entries

    :returns: the sorted ``entry_list``
    """
    entry_list = args["entry_list"]

    entry_list = [(e._mtime, e) for e in entry_list]
    entry_list.sort()
    entry_list.reverse()
    entry_list = [e[1] for e in entry_list]

    return entry_list


def blosxom_process_path_info(args):
    """Process HTTP ``PATH_INFO`` for URI according to path
    specifications, fill in data dict accordingly.

    The paths specification looks like this:

    - ``/foo.html`` and ``/cat/foo.html`` - file foo.* in / and /cat
    - ``/cat`` - category
    - ``/2002`` - category
    - ``/2002`` - year
    - ``/2002/Feb`` and ``/2002/02`` - Year and Month
    - ``/cat/2002/Feb/31`` and ``/cat/2002/02/31``- year and month day
      in category.

    :param args: dict containing the incoming Request object
    """
    request = args['request']
    config = request.get_configuration()
    data = request.get_data()
    py_http = request.get_http()

    form = request.get_form()

    # figure out which flavour to use.  the flavour is determined by
    # looking at the "flav" post-data variable, the "flav" query
    # string variable, the "default_flavour" setting in the config.py
    # file, or "html"
    flav = config.get("default_flavour", "html")
    if form.has_key("flav"):
        flav = form["flav"].value

    data['flavour'] = flav

    data['pi_yr'] = ''
    data['pi_mo'] = ''
    data['pi_da'] = ''

    path_info = py_http.get("PATH_INFO", "")

    data['root_datadir'] = config['datadir']

    data["pi_bl"] = path_info

    # first we check to see if this is a request for an index and we
    # can pluck the extension (which is certainly a flavour) right
    # off.
    new_path, ext = os.path.splitext(path_info)
    if new_path.endswith("/index") and ext:
        # there is a flavour-like thing, so that's our new flavour and
        # we adjust the path_info to the new filename
        data["flavour"] = ext[1:]
        path_info = new_path

    while path_info and path_info.startswith("/"):
        path_info = path_info[1:]

    absolute_path = os.path.join(config["datadir"], path_info)

    path_info = path_info.split("/")

    if os.path.isdir(absolute_path):

        # this is an absolute path

        data['root_datadir'] = absolute_path
        data['bl_type'] = 'dir'

    elif absolute_path.endswith("/index") and \
            os.path.isdir(absolute_path[:-6]):

        # this is an absolute path with /index at the end of it

        data['root_datadir'] = absolute_path[:-6]
        data['bl_type'] = 'dir'

    else:
        # this is either a file or a date

        ext = tools.what_ext(data["extensions"].keys(), absolute_path)
        if not ext:
            # it's possible we didn't find the file because it's got a
            # flavour thing at the end--so try removing it and
            # checking again.
            new_path, flav = os.path.splitext(absolute_path)
            if flav:
                ext = tools.what_ext(data["extensions"].keys(), new_path)
                if ext:
                    # there is a flavour-like thing, so that's our new
                    # flavour and we adjust the absolute_path and
                    # path_info to the new filename
                    data["flavour"] = flav[1:]
                    absolute_path = new_path
                    path_info, flav = os.path.splitext("/".join(path_info))
                    path_info = path_info.split("/")

        if ext:
            # this is a file
            data["bl_type"] = "file"
            data["root_datadir"] = absolute_path + "." + ext

        else:
            data["bl_type"] = "dir"

            # it's possible to have category/category/year/month/day
            # (or something like that) so we pluck off the categories
            # here.
            pi_bl = ""
            while len(path_info) > 0 and \
                    not (len(path_info[0]) == 4 and path_info[0].isdigit()):
                pi_bl = os.path.join(pi_bl, path_info.pop(0))

            # handle the case where we do in fact have a category
            # preceding the date.
            if pi_bl:
                pi_bl = pi_bl.replace("\\", "/")
                data["pi_bl"] = pi_bl
                data["root_datadir"] = os.path.join(config["datadir"], pi_bl)

            if len(path_info) > 0:
                item = path_info.pop(0)
                # handle a year token
                if len(item) == 4 and item.isdigit():
                    data['pi_yr'] = item
                    item = ""

                    if len(path_info) > 0:
                        item = path_info.pop(0)
                        # handle a month token
                        if item in tools.MONTHS:
                            data['pi_mo'] = item
                            item = ""

                            if len(path_info) > 0:
                                item = path_info.pop(0)
                                # handle a day token
                                if len(item) == 2 and item.isdigit():
                                    data["pi_da"] = item
                                    item = ""

                                    if len(path_info) > 0:
                                        item = path_info.pop(0)

                # if the last item we picked up was "index", then we
                # just ditch it because we don't need it.
                if item == "index":
                    item = ""

                # if we picked off an item we don't recognize and/or
                # there is still stuff in path_info to pluck out, then
                # it's likely this wasn't a date.
                if item or len(path_info) > 0:
                    data["bl_type"] = "dir"
                    data["root_datadir"] = absolute_path

    # construct our final URL
    url = config['base_url']
    if data['pi_bl'].startswith("/") and url.endswith("/"):
        url = url[:-1] + data['pi_bl']
    elif data['pi_bl'].startswith("/") or url.endswith("/"):
        url = url + data["pi_bl"]
    else:
        url = url + "/" + data['pi_bl']
    data['url'] = url

    # set path_info to our latest path_info
    data['path_info'] = path_info

    if data.get("pi_yr"):
        data["truncate"] = config.get("truncate_date", False)
    elif data.get("bl_type") == "dir":
        if data["path_info"] == [''] or data["path_info"] == ['index']:
            data["truncate"] = config.get("truncate_frontpage", True)
        else:
            data["truncate"] = config.get("truncate_category", True)
    else:
        data["truncate"] = False


def blosxom_truncate_list_handler(args):
    """If ``config["num_entries"]`` is not 0 and ``data["truncate"]``
    is not 0, then this truncates ``args["entry_list"]`` by
    ``config["num_entries"]``.

    :param args: args dict with ``request`` object and ``entry_list``
                 list of entries

    :returns: the truncated ``entry_list``.
    """
    request = args["request"]
    entry_list = args["entry_list"]

    data = request.data
    config = request.config

    num_entries = config.get("num_entries", 5)
    truncate = data.get("truncate", 0)
    if num_entries and truncate:
        entry_list = entry_list[:num_entries]
    return entry_list


########NEW FILE########
__FILENAME__ = base
#######################################################################
# This file is part of Pyblosxom.
#
# Copyright (C) 2003-2011 by the Pyblosxom team.  See AUTHORS.
#
# Pyblosxom is distributed under the MIT license.  See the file
# LICENSE for distribution details.
#######################################################################

"""
The cache base class.  Subclasses of this class provide caching for
blog entry data in Pyblosxom.
"""

class BlosxomCacheBase:
    """
    Base Class for Caching stories in pyblosxom.

    A cache is a disposable piece of data that gets updated when an entry
    is in a fresh state.

    Drivers are to subclass this object, overriding methods defined in
    this class.  If there is an error in creating cache data, be as quite
    as possible, document how a user could check whether his cache works.

    Driver should expect empty caches and should attempt to create them from
    scratch.

    @ivar _config: String containing config on where to store the cache.
        The value of config is derived from C{py['cacheConfig']} in config.py.
    @type _config: string
    """
    def __init__(self, req, config):
        """
        Constructor - setup and load up the cache

        @param req: the request object
        @type req: Request

        @param config: String containing config on where to store the cache
        @type config: string
        """
        self._request = req
        self._config = config

        self._entryid = ""
        self._entrydata = {}

    def load(self, entryid):
        """
        Try to load up the cache with entryid (a unique key for the entry)

        @param entryid: The key identifier for your cache
        @type entryid: string
        """
        self._entryid = entryid # The filename of the entry
        self._entrydata = {}    # The data of the entry

    def getEntry(self):
        """
        Gets the data from the cache, returns a dict or an empty dict.
        """
        return self._entrydata

    def isCached(self):
        """
        Returns 0 or 1 based on whether there is cached data, returns 0 is
        cache data is stale

        @returns: 0 or 1 based on cache
        @rtype: boolean
        """
        return 0

    def saveEntry(self, entrydata):
        """
        Store entrydata in cache

        @param entrydata: The payload, usually a dict
        @type entrydata: dict
        """
        pass

    def rmEntry(self):
        """
        Remove cache entry: This is not used by pyblosxom, but used by
        utilities.
        """
        pass

    def close(self):
        """
        Override this to close your cache if necessary.
        """
        pass

    def __getitem__(self, key):
        """
        Convenience function to make this class look like a dict.
        """
        self.load(key)
        if not self.has_key(key):
            raise KeyError
        return self.getEntry()

    def __setitem__(self, key, value):
        """
        Synonymous to L{saveEntry}
        """
        self.load(key)
        self.saveEntry(value)

    def __delitem__(self, key):
        """
        Convenience function to make this look more like a dict.
        """
        self.load(key)
        self.rmEntry()

    def has_key(self, key):
        """
        Convenience function to make this look more like a dict.
        """
        self.load(key)
        return self.isCached()

    def keys(self):
        """
        List out a list of keys for the cache, to be overridden by a subclass
        if a full dict interface is required.
        """
        return []

    def get(self, key, default=None):
        """
        Convenience function to make this look more like a dict.
        """
        try:
            return self.__getitem__(key)
        except KeyError:
            return default


class BlosxomCache(BlosxomCacheBase):
    """
    A null cache.
    """
    pass

########NEW FILE########
__FILENAME__ = entrypickle
#######################################################################
# This file is part of Pyblosxom.
#
# Copyright (C) 2003-2011 by the Pyblosxom team.  See AUTHORS.
#
# Pyblosxom is distributed under the MIT license.  See the file
# LICENSE for distribution details.
#######################################################################

"""
This cache driver creates pickled data as cache in a directory.

To use this driver, add the following configuration options in your config.py

py['cacheDriver'] = 'entrypickle'
py['cacheConfig'] = '/path/to/a/cache/directory'

If successful, you will see the cache directory filled up with files that ends
with .entryplugin extention in the drectory.
"""

from Pyblosxom import tools
from Pyblosxom.cache.base import BlosxomCacheBase

import cPickle as pickle
import os
from os import makedirs
from os.path import normpath, dirname, exists, abspath


class BlosxomCache(BlosxomCacheBase):
    """
    This cache stores each entry as a separate pickle file of the
    entry's contents.
    """
    def __init__(self, req, config):
        """
        Takes in a Pyblosxom request object and a configuration string
        which determines where to store the pickle files.
        """
        BlosxomCacheBase.__init__(self, req, config)
        self._cachefile = ""

    def load(self, entryid):
        """
        Takes an entryid and keeps track of the filename.  We only
        open the file when it's requested with getEntry.
        """
        BlosxomCacheBase.load(self, entryid)
        filename = os.path.join(self._config, entryid.replace('/', '_'))
        self._cachefile = filename + '.entrypickle'

    def getEntry(self):
        """
        Open the pickle file and return the data therein.  If this
        fails, then we return None.
        """
        try:
            filep = open(self._cachefile, 'rb')
            data = pickle.load(filep)
            filep.close()
            return data
        except IOError:
            return None

    def isCached(self):
        """
        Check to see if the file is updated.
        """
        return os.path.isfile(self._cachefile) and \
            os.stat(self._cachefile)[8] >= os.stat(self._entryid)[8]

    def saveEntry(self, entrydata):
        """
        Save the data in the entry object to a pickle file.
        """
        filep = None
        try:
            self.__makepath(self._cachefile)
            filep = open(self._cachefile, "w+b")
            entrydata.update({'realfilename': self._entryid})
            pickle.dump(entrydata, filep, 1)
        except IOError:
            pass

        if filep:
            filep.close()

    def rmEntry(self):
        """
        Removes the pickle file for this entry if it exists.
        """
        if os.path.isfile(self._cachefile):
            os.remove(self._cachefile)

    def keys(self):
        """
        Returns a list of the keys found in this entrypickle instance.
        This corresponds to the list of entries that are cached.

        @returns: list of full paths to entries that are cached
        @rtype: list of strings
        """
        import re
        keys = []
        cached = []
        if os.path.isdir(self._config):
            cached = tools.walk(self._request,
                                self._config,
                                1,
                                re.compile(r'.*\.entrypickle$'))
        for cache in cached:
            cache_data = pickle.load(open(cache))
            key = cache_data.get('realfilename', '')
            if not key and os.path.isfile(cache):
                os.remove(cache)
            self.load(key)
            if not self.isCached():
                self.rmEntry()
            else:
                keys.append(key)
        return keys

    def __makepath(self, path):
        """
        Creates the directory and all parent directories for a
        specified path.

        @param path: the path to create
        @type  path: string

        @returns: the normalized absolute path
        @rtype: string
        """
        dpath = normpath(dirname(path))
        if not exists(dpath):
            makedirs(dpath)
        return normpath(abspath(path))

########NEW FILE########
__FILENAME__ = entryshelve
#######################################################################
# This file is part of Pyblosxom.
#
# Copyright (C) 2003-2011 by the Pyblosxom team.  See AUTHORS.
#
# Pyblosxom is distributed under the MIT license.  See the file
# LICENSE for distribution details.
#######################################################################

"""
This cache driver creates shelved data as cache in a dbm file.

To use this driver, add the following configuration options in your config.py

py['cacheDriver'] = 'entryshelve'
py['cacheConfig'] = '/path/to/a/cache/dbm/file'

If successful, you will see the cache file. Be sure that you have write access
to the cache file.
"""

from Pyblosxom.cache.base import BlosxomCacheBase
import shelve
import os


class BlosxomCache(BlosxomCacheBase):
    """
    This stores entries in shelves in a .dbm file.
    """
    def __init__(self, req, config):
        """
        Initializes BlosxomCacheBase.__init__ and also opens the
        shelf file.
        """
        BlosxomCacheBase.__init__(self, req, config)
        self._db = shelve.open(self._config)

    def load(self, entryid):
        """
        Loads a specific entryid.
        """
        BlosxomCacheBase.load(self, entryid)

    def getEntry(self):
        """
        Get an entry from the shelf.
        """
        data = self._db.get(self._entryid, {})
        return data.get('entrydata', {})

    def isCached(self):
        """
        Returns true if the entry is cached and the cached version is
        not stale.  Returns false otherwise.
        """
        data = self._db.get(self._entryid, {'mtime':0})
        if os.path.isfile(self._entryid):
            return data['mtime'] == os.stat(self._entryid)[8]
        else:
            return None

    def saveEntry(self, entrydata):
        """
        Save data in the pickled file.
        """
        payload = {}
        payload['mtime'] = os.stat(self._entryid)[8]
        payload['entrydata'] = entrydata

        self._db[self._entryid] = payload

    def rmEntry(self):
        """
        Removes an entry from the shelf.
        """
        if self._db.has_key(self._entryid):
            del self._db[self._entryid]

    def keys(self):
        """
        Returns a list of entries that are cached in the shelf.

        @returns: list of entry paths
        @rtype: list of strings
        """
        ret = []
        for key in self._db.keys():
            self.load(key)
            if self.isCached():
                ret.append(key)
            else:
                # Remove this key, why is it there in the first place?
                del self._db[self._entryid]
        return ret

    def close(self):
        """
        Closes the db file.
        """
        self._db.close()
        self._db = None

########NEW FILE########
__FILENAME__ = commandline
#######################################################################
# This file is part of Pyblosxom.
#
# Copyright (C) 2008-2011 by the Pyblosxom team.  See AUTHORS.
#
# Pyblosxom is distributed under the MIT license.  See the file
# LICENSE for distribution details.
#######################################################################

"""
This module holds commandline related stuff.  Installation
verification, blog creation, commandline argument parsing, ...
"""

import os
import os.path
import sys
import random
import time
from optparse import OptionParser

from Pyblosxom import __version__
from Pyblosxom.pyblosxom import Pyblosxom
from Pyblosxom.tools import run_callback, pwrap, pwrap_error
from Pyblosxom import plugin_utils

USAGE = "%prog [options] [command] [command-options]"
VERSION = "%prog " + __version__


def build_pyblosxom():
    """Imports config.py and builds an empty Pyblosxom object.
    """
    pwrap("Trying to import the config module....")
    try:
        from config import py as cfg
    except StandardError:
        h, t = os.path.split(sys.argv[0])
        script_name = t or h

        pwrap_error("ERROR: Cannot find your config.py file.  Please execute "
                    "%s in the directory with the config.py file in it or use "
                    "the --config flag.\n\n"
                    "See \"%s --help\" for more details." % (script_name,
                                                             script_name))
        return None

    return Pyblosxom(cfg, {})


def build_parser(usage):
    parser = OptionParser(usage=usage, version=VERSION)
    parser.add_option("-q", "--quiet",
                      action="store_false", dest="verbose", default=True,
                      help="If the quiet flag is specified, then Pyblosxom "
                      "will run quietly.")
    parser.add_option("--config",
                      help="This specifies the directory that the config.py "
                      "for the blog you want to work with is in.  If the "
                      "config.py file is in the current directory, then "
                      "you don't need to specify this.  All commands except "
                      "the 'create' command need a config.py file.")

    return parser


def generate_entries(command, argv):
    """
    This function is primarily for testing purposes.  It creates
    a bunch of blog entries with random text in them.
    """
    parser = build_parser("%prog entries [options] <num_entries>")
    (options, args) = parser.parse_args()

    if args:
        try:
            num_entries = int(args[0])
            assert num_entries > 0
        except ValueError:
            pwrap_error("ERROR: num_entries must be a positive integer.")
            return 0
    else:
        num_entries = 5

    verbose = options.verbose

    p = build_pyblosxom()
    if not p:
        return 0

    datadir = p.get_request().config["datadir"]

    sm_para = "<p>Lorem ipsum dolor sit amet.</p>"
    med_para = """<p>
  Lorem ipsum dolor sit amet, consectetur adipiscing elit. Phasellus
  in mi lacus, sed interdum nisi. Vestibulum commodo urna et libero
  vestibulum gravida. Vivamus hendrerit justo quis lorem auctor
  consectetur. Aenean ornare, tortor in sollicitudin imperdiet, neque
  diam pellentesque risus, vitae.
</p>"""
    lg_para = """<p>
  Lorem ipsum dolor sit amet, consectetur adipiscing elit. Mauris
  dictum tortor orci. Lorem ipsum dolor sit amet, consectetur
  adipiscing elit. Etiam quis lectus vel odio convallis tincidunt sed
  et magna. Suspendisse at dolor suscipit eros ullamcorper iaculis. In
  aliquet ornare libero eget rhoncus. Sed ac ipsum eget eros fringilla
  aliquet ut eget velit. Curabitur dui nibh, eleifend non suscipit at,
  laoreet ac purus. Morbi id sem diam. Cras sit amet ante lacus, nec
  euismod urna. Curabitur iaculis, lorem at fringilla malesuada, nunc
  ligula eleifend nisi, at bibendum libero est quis
  tellus. Pellentesque habitant morbi tristique senectus et netus et
  malesuada.
</p>"""
    paras = [sm_para, med_para, lg_para]

    if verbose:
        print "Creating %d entries" % num_entries

    now = time.time()

    for i in range(num_entries):
        title = "post number %d\n" % (i + 1)
        body = []
        for _ in range(random.randrange(1, 6)):
            body.append(random.choice(paras))

        fn = os.path.join(datadir, "post%d.txt" % (i + 1))
        f = open(fn, "w")
        f.write(title)
        f.write("\n".join(body))
        f.close()

        mtime = now - ((num_entries - i) * 3600)
        os.utime(fn, (mtime, mtime))
        
        if verbose:
            print "Creating '%s'..." % fn

    if verbose:
        print "Done!"
    return 0


def test_installation(command, argv):
    """
    This function gets called when someone starts up pyblosxom.cgi
    from the command line with no REQUEST_METHOD environment variable.
    It:

    1. verifies config.py file properties
    2. initializes all the plugins they have installed
    3. runs ``cb_verify_installation``--plugins can print out whether
       they are installed correctly (i.e. have valid config property
       settings and can read/write to data files)

    The goal is to be as useful and informative to the user as we can
    be without being overly verbose and confusing.

    This is designed to make it easier for a user to verify their
    Pyblosxom installation is working and also to install new plugins
    and verify that their configuration is correct.
    """
    parser = build_parser("%prog test [options]")
    parser.parse_args()

    p = build_pyblosxom()
    if not p:
        return 0

    request = p.get_request()
    config = request.config

    pwrap("System Information")
    pwrap("==================")
    pwrap("")

    pwrap("- pyblosxom:    %s" % __version__)
    pwrap("- sys.version:  %s" % sys.version.replace("\n", " "))
    pwrap("- os.name:      %s" % os.name)
    codebase = os.path.dirname(os.path.dirname(__file__))
    pwrap("- codebase:     %s" % config.get("codebase", codebase))
    pwrap("")

    pwrap("Checking config.py file")
    pwrap("=======================")
    pwrap("- properties set: %s" % len(config))

    config_keys = config.keys()

    if "datadir" not in config_keys:
        pwrap_error("- ERROR: 'datadir' must be set.  Refer to installation "
              "documentation.")

    elif not os.path.isdir(config["datadir"]):
        pwrap_error("- ERROR: datadir '%s' does not exist."
                    "  You need to create your datadir and give it "
                    " appropriate permissions." % config["datadir"])
    else:
        pwrap("- datadir '%s' exists." % config["datadir"])

    if "flavourdir" not in config_keys:
        pwrap("- WARNING: You should consider setting flavourdir and putting "
              "your flavour templates there.  See the documentation for "
              "more details.")
    elif not os.path.isdir(config["flavourdir"]):
        pwrap_error("- ERROR: flavourdir '%s' does not exist."
                    "  You need to create your flavourdir and give it "
                    " appropriate permissions." % config["flavourdir"])
    else:
        pwrap("- flavourdir '%s' exists." % config["flavourdir"])

    if (("blog_encoding" in config_keys
         and config["blog_encoding"].lower() != "utf-8")):
        pwrap_error("- WARNING: 'blog_encoding' is set to something other "
                    "than 'utf-8'.  As of Pyblosxom 1.5, "
                    "this isn't a good idea unless you're absolutely certain "
                    "it's going to work for your blog.")
    pwrap("")

    pwrap("Checking plugin configuration")
    pwrap("=============================")

    import traceback

    no_verification_support = []

    if len(plugin_utils.plugins) + len(plugin_utils.bad_plugins) == 0:
        pwrap(" - There are no plugins installed.")

    else:
        if len(plugin_utils.bad_plugins) > 0:
            pwrap("- Some plugins failed to load.")
            pwrap("")
            pwrap("----")
            for mem in plugin_utils.bad_plugins:
                pwrap("plugin:  %s" % mem[0])
                print "%s" % mem[1]
                pwrap("----")
            pwrap_error("FAIL")
            return(1)

        if len(plugin_utils.plugins) > 0:
            pwrap("- This goes through your plugins and asks each of them "
                  "to verify configuration and installation.")
            pwrap("")
            pwrap("----")
            for mem in plugin_utils.plugins:
                if hasattr(mem, "verify_installation"):
                    pwrap("plugin:  %s" % mem.__name__)
                    print "file:    %s" % mem.__file__
                    print "version: %s" % (str(getattr(mem, "__version__")))

                    try:
                        if mem.verify_installation(request) == 1:
                            pwrap("PASS")
                        else:
                            pwrap_error("FAIL")
                    except StandardError:
                        pwrap_error("FAIL: Exception thrown:")
                        traceback.print_exc(file=sys.stdout)

                    pwrap("----")
                else:
                    mn = mem.__name__
                    mf = mem.__file__
                    no_verification_support.append( "'%s' (%s)" % (mn, mf))

            if len(no_verification_support) > 0:
                pwrap("")
                pwrap("The following plugins do not support installation "
                      "verification:")
                no_verification_support.sort()
                for mem in no_verification_support:
                    print "- %s" % mem

    pwrap("")
    pwrap("Verification complete.  Correct any errors and warnings above.")


def create_blog(command, argv):
    """
    Creates a blog in the specified directory.  Mostly this involves
    copying things over, but there are a few cases where we expand
    template variables.
    """
    parser = build_parser("%prog create [options] <dir>")
    (options, args) = parser.parse_args()

    if args:
        d = args[0]
    else:
        d = "."

    if d == ".":
        d = "." + os.sep + "blog"

    d = os.path.abspath(d)

    verbose = options.verbose

    if os.path.isfile(d) or os.path.isdir(d):
        pwrap_error("ERROR: Cannot create '%s'--something is in the way." % d)
        return 0

    def _mkdir(d):
        if verbose:
            print "Creating '%s'..." % d
        os.makedirs(d)

    _mkdir(d)
    _mkdir(os.path.join(d, "entries"))
    _mkdir(os.path.join(d, "plugins"))

    source = os.path.join(os.path.dirname(__file__), "flavours")

    for root, dirs, files in os.walk(source):
        if ".svn" in root:
            continue

        dest = os.path.join(d, "flavours", root[len(source)+1:])
        if not os.path.isdir(dest):
            if verbose:
                print "Creating '%s'..." % dest
            os.mkdir(dest)

        for mem in files:
            if verbose:
                print "Creating file '%s'..." % os.path.join(dest, mem)
            fpin = open(os.path.join(root, mem), "r")
            fpout = open(os.path.join(dest, mem), "w")

            fpout.write(fpin.read())

            fpout.close()
            fpin.close()

    def _copyfile(frompath, topath, fn, fix=False):
        if verbose:
            print "Creating file '%s'..." % os.path.join(topath, fn)
        fp = open(os.path.join(frompath, fn), "r")
        filedata = fp.readlines()
        fp.close()

        if fix:
            basedir = topath
            if not basedir.endswith(os.sep):
                basedir = basedir + os.sep
            if os.sep == "\\":
                basedir = basedir.replace(os.sep, os.sep + os.sep)
            datamap = { "basedir": basedir,
                        "codedir": os.path.dirname(os.path.dirname(__file__)) }
            filedata = [line % datamap for line in filedata]

        fp = open(os.path.join(topath, fn), "w")
        fp.write("".join(filedata))
        fp.close()

    source = os.path.join(os.path.dirname(__file__), "data")

    _copyfile(source, d, "config.py", fix=True)
    _copyfile(source, d, "blog.ini", fix=True)
    _copyfile(source, d, "pyblosxom.cgi", fix=True)

    datadir = os.path.join(d, "entries")
    firstpost = os.path.join(datadir, "firstpost.txt")
    if verbose:
        print "Creating file '%s'..." % firstpost
    fp = open(firstpost, "w")
    fp.write("""First post!
<p>
  This is your first post!  If you can see this with a web-browser,
  then it's likely that everything's working nicely!
</p>
""")
    fp.close()

    if verbose:
        print "Done!"
    return 0


def render_url(command, argv):
    """Renders a single url.
    """
    parser = build_parser("%prog renderurl [options] <url> [<url>...]")

    parser.add_option("--headers",
                      action="store_true", dest="headers", default=False,
                      help="Option that causes headers to be displayed "
                      "when rendering a single url.")

    (options, args) = parser.parse_args()

    if not args:
        parser.print_help()
        return 0

    for url in args:
        p = build_pyblosxom()

        base_url = p.get_request().config.get("base_url", "")
        if url.startswith(base_url):
            url = url[len(base_url):]
        p.run_render_one(url, options.headers)

    return 0


def run_static_renderer(command, argv):
    parser = build_parser("%prog staticrender [options]")
    parser.add_option("--incremental",
                      action="store_true", dest="incremental", default=False,
                      help="Option that causes static rendering to be "
                      "incremental.")

    (options, args) = parser.parse_args()

    # Turn on memcache.
    from Pyblosxom import memcache
    memcache.usecache = True

    p = build_pyblosxom()
    if not p:
        return 0

    return p.run_static_renderer(options.incremental)

DEFAULT_HANDLERS = (
    ("create", create_blog, "Creates directory structure for a new blog."),
    ("test", test_installation,
     "Tests installation and configuration for a blog."),
    ("staticrender", run_static_renderer,
     "Statically renders your blog into an HTML site."),
    ("renderurl", render_url, "Renders a single url of your blog."),
    ("generate", generate_entries, "Generates random entries--helps "
     "with blog setup.")
)


def get_handlers():
    try:
        from config import py as cfg
        plugin_utils.initialize_plugins(cfg.get("plugin_dirs", []),
                                        cfg.get("load_plugins", None))
    except ImportError:
        pass

    handlers_dict = dict([(v[0], (v[1], v[2])) for v in DEFAULT_HANDLERS])
    handlers_dict = run_callback("commandline", handlers_dict,
                                 mappingfunc=lambda x, y: y,
                                 defaultfunc=lambda x: x)

    # test the handlers, drop any that aren't the right return type,
    # and print a warning.
    handlers = []
    for k, v in handlers_dict.items():
        if not len(v) == 2 or not callable(v[0]) or not isinstance(v[1], str):
            print "Plugin returned '%s' for commandline." % ((k, v),)
            continue
        handlers.append((k, v[0], v[1]))

    return handlers


def command_line_handler(scriptname, argv):
    if "--silent" in argv:
        sys.stdout = open(os.devnull, "w")
        argv.remove("--silent")

    print "%s version %s" % (scriptname, __version__)

    # slurp off the config file setting and add it to sys.path.
    # this needs to be first to pick up plugin-based command handlers.
    config_dir = None
    for i, mem in enumerate(argv):
        if mem.startswith("--config"):
            if "=" in mem:
                _, config_dir = mem.split("=")
                break
            else:
                try:
                    config_dir = argv[i+1]
                    break
                except IndexError:
                    pwrap_error("Error: no config file argument specified.")
                    pwrap_error("Exiting.")
                    return 1

    if config_dir is not None:
        if config_dir.endswith("config.py"):
            config_dir = config_dir[0:-9]

        if not os.path.exists(config_dir):
            pwrap_error("ERROR: '%s' does not exist--cannot find config.py "
                        "file." % config_dir)
            pwrap_error("Exiting.")
            return 1

        if not "config.py" in os.listdir(config_dir):
            pwrap_error("Error: config.py not in '%s'.  "
                        "Cannot find config.py file." % config_dir)
            pwrap_error("Exiting.")
            return 1

        sys.path.insert(0, config_dir)
        print "Inserting %s to beginning of sys.path...." % config_dir

    handlers = get_handlers()

    if len(argv) == 1 or (len(argv) == 2 and argv[1] in ("-h", "--help")):
        parser = build_parser("%prog [command]")
        parser.print_help()
        print ""
        print "Commands:"
        for command_str, _, command_help in handlers:
            print "    %-14s %s" % (command_str, command_help)
        return 0

    if argv[1] == "--version":
        return 0

    # then we execute the named command with options, or print help
    if argv[1].startswith("-"):
        pwrap_error("Command '%s' does not exist." % argv[1])
        pwrap_error('')
        pwrap_error("Commands:")
        for command_str, _, command_help in handlers:
            pwrap_error ( "    %-14s %s" % (command_str, command_help))
        return 1

    command = argv.pop(1)
    for (c, f, h) in handlers:
        if c == command:
            return f(command, argv)

    pwrap_error("Command '%s' does not exist." % command)
    for command_str, command_func, command_help in handlers:
        pwrap_error("    %-14s %s" % (command_str, command_help))
    return 1

########NEW FILE########
__FILENAME__ = crashhandling
#######################################################################
# This file is part of Pyblosxom.
#
# Copyright (C) 2011 by the Pyblosxom team.  See AUTHORS.
#
# Pyblosxom is distributed under the MIT license.  See the file
# LICENSE for distribution details.
#######################################################################

"""
This module has the code for handling crashes.

.. Note::

   This is a leaf node module!  It should never import other Pyblosxom
   modules or packages.
"""

import sys
import StringIO
import cgi
import traceback

_e = cgi.escape


class Response:
    """This is a minimal response that is returned by the crash
    handler.
    """
    def __init__(self, status, headers, body):
        self.status = status
        self.headers = headers
        self.body = body

        self.seek = body.seek
        self.read = body.read


class CrashHandler:
    def __init__(self, httpresponse=False, environ=None):
        """
        :param httpresponse: boolean representing whether when
            handling a crash, we do http response headers
        """
        self.httpresponse = httpresponse

        if environ:
            self.environ = environ
        else:
            self.environ = {}

    def __call__(self, exc_type, exc_value, exc_tb):
        response = self.handle(exc_type, exc_value, exc_tb)
        if self.httpresponse:
            response.headers.append(
                "Content-Length: %d" % httpresponse.body.len)
        sys.output.write("HTTP/1.0 %s\n" % response.status)
        for key, val in response.headers.items():
            sys.output.write("%s: %s\n" % (key, val))
        sys.output.write("\n")
        sys.output.write(response.body.read())
        sys.output.flush()

    def handle_by_response(self, exc_type, exc_value, exc_tb):
        """Returns a basic response object holding crash information
        for display.
        """
        headers = {}
        output = StringIO.StringIO()

        headers["Content-Type"] = "text/html"
        # FIXME - are there other userful headers?

        output.write("<html>")
        output.write("<title>HTTP 500: Oops!</title>")
        output.write("<body>")
        output.write("<h1>HTTP 500: Oops!</h1>")
        output.write(
            "<p>A problem has occurred while Pyblosxom was rendering "
            "this page.</p>")

        output.write(
            "<p>If this is your blog and you've just upgraded Pyblosxom, "
            "check the manual for changes you need to make to your "
            "config.py, pyblosxom.cgi, blog.ini, plugins, and flavour "
            "files.  This is usually covered in the Upgrade and What's New "
            "chapters.</p>\n"
            "<p>If you need help, contact us on IRC or the pyblosxom-users "
            "mailing list.</p>\n"
            "<p>The manual and details on IRC and the pyblosxom-users "
            "mailing list are all on the "
            "<a href=\"http://pyblosxom.github.com/\">website</a>.</p>")

        output.write("<p>Here is some useful information to track down "
            "the root cause of the problem:</p>")

        output.write("<div style=\"border: 1px solid black; padding: 10px;\">")

        try:
            import Pyblosxom
            version = Pyblosxom.__version__
        except:
            version = "unknown"

        output.write("<p>Pyblosxom version: %s</p>" % _e(version))
        output.write("<p>Python version: %s" % _e(sys.version))

        output.write("<p>Error traceback:</p>")
        output.write("<pre>")
        tb = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        output.write(_e(tb))
        output.write("</pre>")

        output.write("<p>HTTP environment:</p>")
        output.write("<pre>")
        for key, val in self.environ.items():
            output.write("%s: %s\n" % (_e(repr(key)), _e(repr(val))))
        output.write("</pre>")

        output.write("</div>")

        output.write("</body>")
        output.write("</html>")

        headers["Content-Length"] = str(output.len)
        return Response("500 Server Error", headers, output)


def enable_excepthook(httpresponse=False):
    """This attaches the :ref:`CrashHandler` to the sys.excepthook.
    This will handle any exceptions thrown that don't get
    handled anywhere else.

    If you're running Pyblosxom as a WSGI application or as a CGI
    script, you should create a :ref:`CrashHandler` instance and call
    ``handle_by_response`` directly.  See
    :ref:`pyblosxom.PyblosxomWSGIApp`.
    """
    sys.excepthook = CrashHandler(httpresponse=httpresponse)

########NEW FILE########
__FILENAME__ = config
# -*- coding: utf-8 -*-
# =================================================================
# This is the config file for Pyblosxom.  You should go through 
# this file and fill in values for the various properties.  This 
# affects the behavior of your blog.
#
# This is a Python code file and as such must be written in
# Python.
#
# There are configuration properties that are not detailed in
# this file.  These are the properties that are most often used.
# To see a full list of configuration properties as well as
# additional documentation, see the Pyblosxom documentation on
# the web-site for your version of Pyblosxom.
# =================================================================

# Don't touch this next line.
py = {}


# Codebase configuration
# ======================

# If you did not install Pyblosxom as a library (i.e. python setup.py install)
# then uncomment this next line and point it to your Pyblosxom installation
# directory.
# 
# Note, this should be the parent directory of the "Pyblosxom" directory
# (note the case--uppercase P lowercase b!).
#py["codebase"] = "%(codedir)s"

import os

blogdir = "%(basedir)s"

# Blog configuration
# ==================

# What is the title of this blog?
py["blog_title"] = "Another pyblosxom blog"

# What is the description of this blog?
py["blog_description"] = "blosxom with a touch of python"

# Who are the author(s) of this blog?
py["blog_author"] = "name"

# What is the email address through which readers of the blog may contact
# the authors?
py["blog_email"] = "email@example.com"

# These are the rights you give to others in regards to the content
# on your blog.  Generally, this is the copyright information.
# This is used in the Atom feeds.  Leaving this blank or not filling
# it in correctly could result in a feed that doesn't validate.
py["blog_rights"] = "Copyright 2005 Joe Bobb"

# What is this blog's primary language (for outgoing RSS feed)?
py["blog_language"] = "en"

# Encoding for output.  This defaults to utf-8.
py["blog_encoding"] = "utf-8"

# What is the locale for this blog?  This is used when formatting dates
# and other locale-sensitive things.  Make sure the locale is valid for
# your system.  See the configuration chapter in the Pyblosxom documentation
# for details.
#py["locale"] = "en_US.iso-8859-1"

# Where are this blog's entries kept?
py["datadir"] = os.path.join(blogdir, "entries")

# Where are this blog's flavours kept?
py["flavourdir"] = os.path.join(blogdir, "flavours")

# List of strings with directories that should be ignored (e.g. "CVS")
# ex: py['ignore_directories'] = ["CVS", "temp"]
py["ignore_directories"] = []

# Should I stick only to the datadir for items or travel down the directory
# hierarchy looking for items?  If so, to what depth?
# 0 = infinite depth (aka grab everything)
# 1 = datadir only
# n = n levels down
py["depth"] = 0

# How many entries should I show on the home page and category pages?
# If you put 0 here, then I will show all pages.
# Note: this doesn't affect date-based archive pages.
py["num_entries"] = 5

# What is the default flavour you want to use when the user doesn't
# specify a flavour in the request?
py["default_flavour"] = "html"



# Logging configuration
# =====================

# Where should Pyblosxom write logged messages to?
# If set to "NONE" log messages are silently ignored.
# Falls back to sys.stderr if the file can't be opened for writing.
#py["log_file"] = os.path.join(blogdir, "logs", "pyblosxom.log")

# At what level should we log to log_file?
# One of: "critical", "error", "warning", "info", "debug"
# For production, "warning" or "error' is recommended.
#py["log_level"] = "warning"

# This lets you specify which channels should be logged.
# If specified, only messages from the listed channels are logged.
# Each plugin logs to it's own channel, therefor channelname == pluginname.
# Application level messages are logged to a channel named "root".
# If you use log_filter and ommit the "root" channel here, app level messages 
# are not logged! log_filter is mainly interesting to debug a specific plugin.
#py["log_filter"] = ["root", "plugin1", "plugin2"]



# Plugin configuration
# ====================

# Plugin directories:
# This allows you to specify which directories have plugins that you
# want to load.  You can list as many plugin directories as you
# want.
# Example: py['plugin_dirs'] = ["/home/joe/blog/plugins",
#                               "/var/lib/pyblosxom/plugins"]
py["plugin_dirs"] = [os.path.join(blogdir, "plugins")]

# There are two ways for Pyblosxom to load plugins:
# 
# The first is the default way where Pyblosxom loads all plugins it
# finds in the directories specified by "plugins_dir" in alphanumeric
# order by filename.
# 
# The second is by specifying a "load_plugins" key here.  Specifying
# "load_plugins" will cause Pyblosxom to load only the plugins you name 
# and in in the order you name them.
# 
# The "load_plugins" key is a list of strings where each string is
# the name of a plugin module (i.e. the filename without the .py at
# the end).
# 
# If you specify an empty list, then this will load no plugins.
# ex: py["load_plugins"] = ["pycalendar", "pyfortune", "pyarchives"]
py["load_plugins"] = []



# ======================
# Optional Configuration
# ======================

# What should this blog use as its base url?
#py["base_url"] = "http://www.example.com/weblog"

# Default parser/preformatter. Defaults to plain (does nothing)
#py["parser"] = "plain"



# Static rendering
# ================

# Doing static rendering?  Static rendering essentially "compiles" your
# blog into a series of static html pages.  For more details, see the
# documentation.
# 
# What directory do you want your static html pages to go into?
#py["static_dir"] = "/path/to/static/dir"

# What flavours should get generated?
#py["static_flavours"] = ["html"]

# What other paths should we statically render?
# This is for additional urls handled by other plugins like the booklist
# and plugin_info plugins.  If there are multiple flavours you want
# to capture, specify each:
# ex: py["static_urls"] = ["/booklist.rss", "/booklist.html"]
#py["static_urls"] = ["/path/to/url1", "/path/to/url2"]

# Whether (True) or not (False) you want to generate date indexes with month
# names?  (ex. /2004/Apr/01)  Defaults to True.
#py["static_monthnames"] = True

# Whether (True) or not (False) you want to generate date indexes
# using month numbers?  (ex. /2004/04/01)  Defaults to False.
#py["static_monthnumbers"] = False

# Whether (True) or not (False) you want to generate year indexes?
# (ex. /2004)  Defaults to True.
#py["static_yearindexes"] = True


########NEW FILE########
__FILENAME__ = base
#######################################################################
# This file is part of Pyblosxom.
#
# Copyright (C) 2003-2011 by the Pyblosxom team.  See AUTHORS.
#
# Pyblosxom is distributed under the MIT license.  See the file
# LICENSE for distribution details.
#######################################################################

"""
This module contains the base class for all the Entry classes.  The
EntryBase class is essentially the API for entries in Pyblosxom.  Reading
through the comments for this class will walk you through building your
own EntryBase derivatives.

This module also holds a generic generate_entry function which will generate
a BaseEntry with data that you provide for it.
"""

import time
import locale
from Pyblosxom import tools

BIGNUM = 2000000000
CONTENT_KEY = "body"
DOESNOTEXIST = "THISKEYDOESNOTEXIST"
DOESNOTEXIST2 = "THISKEYDOESNOTEXIST2"


class EntryBase:
    """
    EntryBase is the base class for all the Entry classes.  Each
    instance of an Entry class represents a single entry in the
    weblog, whether it came from a file, or a database, or even
    somewhere off the InterWeeb.

    EntryBase derivatives are dict-like except for one key difference:
    when doing ``__getitem__`` on a nonexistent key, it returns None by
    default.  For example:

    >>> entry = EntryBase('some fake request')
    >>> None == entry["some_nonexistent_key"]
    True
    """

    def __init__(self, request):
        self._data = ""
        self._metadata = dict(tools.STANDARD_FILTERS)
        self._id = ""
        self._mtime = BIGNUM
        self._request = request

    def __repr__(self):
        """
        Returns a friendly debug-able representation of self. Useful
        to know on what entry pyblosxom fails on you (though unlikely)

        :returns: Identifiable representation of object
        """
        return "<Entry instance: %s>\n" % self.getId()

    def get_id(self):
        """
        This should return an id that's unique enough for caching
        purposes.

        Override this.

        :returns: string id
        """
        return self._id

    getId = tools.deprecated_function(get_id)

    def get_data(self):
        """
        Returns the data string.  This method should be overridden to
        provide from pulling the data from other places.

        Override this.

        :returns: the data as a string
        """
        return str(self._data)

    getData = tools.deprecated_function(get_data)

    def set_data(self, data):
        """
        Sets the data content for this entry.  If you are not creating
        the entry, then you have no right to set the data of the
        entry.  Doing so could be hazardous depending on what
        EntryBase subclass you're dealing with.

        Override this.

        :param data: the data
        """
        self._data = data

    setData = tools.deprecated_function(set_data)

    def get_metadata(self, key, default=None):
        """
        Returns a given piece of metadata.

        Override this.

        :param key: the key being sought

        :param default: the default to return if the key does not
                        exist

        :return: either the default (if the key did not exist) or the
                 value of the key in the metadata dict
        """
        return self._metadata.get(key, default)

    getMetadata = tools.deprecated_function(get_metadata)

    def set_metadata(self, key, value):
        """
        Sets a key/value pair in the metadata dict.

        Override this.

        :param key: the key string

        :param value: the value string
        """
        self._metadata[key] = value

    setMetadata = tools.deprecated_function(set_metadata)

    def get_metadata_keys(self):
        """
        Returns the list of keys for which we have values in our
        stored metadata.

        .. Note::

            This list gets modified later downstream.  If you cache
            your list of metadata keys, then this method should return
            a copy of that list and not the list itself lest it get
            adjusted.

        Override this.

        :returns: list of metadata keys
        """
        return self._metadata.keys()

    getMetadataKeys = tools.deprecated_function(get_metadata_keys)

    def get_from_cache(self, entryid):
        """
        Retrieves information from the cache that pertains to this
        specific entryid.

        This is a helper method--call this to get data from the cache.
        Do not override it.

        :param entryid: a unique key for the information you're retrieving

        :returns: dict with the values or None if there's nothing for that
                  entryid
        """
        cache = tools.get_cache(self._request)

        # cache.__getitem__ returns None if the id isn't there
        if cache.has_key(entryid):
            return cache[entryid]

        return None

    getFromCache = tools.deprecated_function(get_from_cache)

    def add_to_cache(self, entryid, data):
        """
        Over-writes the cached dict for key entryid with the data
        dict.

        This is a helper method--call this to add data to the cache.
        Do not override it.

        :param entryid: a unique key for the information you're
                        storing

        :param data: the data to store--this should probably be a dict
        """
        mycache = tools.get_cache(self._request)
        if mycache:
            # This could be extended to cover all keys used by
            # set_time(), but this is the key most likely to turn
            # up in metadata. If #date is not blocked from caching
            # here, the templates will use the raw string value
            # from the user metadata, rather than the value
            # derived from mtime.
            if data.has_key('date'):
                data.pop('date')
            mycache[entryid] = data

    addToCache = tools.deprecated_function(add_to_cache)

    def set_time(self, timetuple):
        """
        This takes in a given time tuple and sets all the magic
        metadata variables we have according to the items in the time
        tuple.

        :param timetuple: the timetuple to use to set the data
                          with--this is the same thing as the
                          mtime/atime portions of an os.stat.  This
                          time is expected to be local time, not UTC.
        """
        self['timetuple'] = timetuple
        self._mtime = time.mktime(timetuple)
        gmtimetuple = time.gmtime(self._mtime)
        self['mtime'] = self._mtime
        self['ti'] = time.strftime('%H:%M', timetuple)
        self['mo'] = time.strftime('%b', timetuple)
        self['mo_num'] = time.strftime('%m', timetuple)
        self['da'] = time.strftime('%d', timetuple)
        self['dw'] = time.strftime('%A', timetuple)
        self['yr'] = time.strftime('%Y', timetuple)
        self['fulltime'] = time.strftime('%Y%m%d%H%M%S', timetuple)
        self['date'] = time.strftime('%a, %d %b %Y', timetuple)

        # YYYY-MM-DDThh:mm:ssZ
        self['w3cdate'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', gmtimetuple)

        # Temporarily disable the set locale, so RFC-compliant date is
        # really RFC-compliant: directives %a and %b are locale
        # dependent.  Technically, we're after english locale, but
        # only 'C' locale is guaranteed to exist.
        loc = locale.getlocale(locale.LC_ALL)
        locale.setlocale(locale.LC_ALL, 'C')

        self['rfc822date'] = time.strftime('%a, %d %b %Y %H:%M GMT', \
                                           gmtimetuple)

        # set the locale back
        locale.setlocale(locale.LC_ALL, loc)

    setTime = tools.deprecated_function(set_time)

    # everything below this point involves convenience functions
    # that work with the above functions.

    def __getitem__(self, key, default=None):
        """
        Retrieves an item from this dict based on the key given.  If
        the item does not exist, then we return the default.

        If the item is ``CONTENT_KEY``, it calls ``get_data``,
        otherwise it calls ``get_metadata``.  Don't override this.

        .. Warning::

            There's no reason to override this--override ``get_data``
            and ``get_metadata`` instead.

        :param key: the key being sought

        :param default: the default to return if the key does not
                        exist

        :returns: the value of ``get_metadata`` or ``get_data``
        """
        if key == CONTENT_KEY:
            return self.get_data()

        return self.get_metadata(key, default)

    def get(self, key, default=None):
        """
        Retrieves an item from the internal dict based on the key
        given.

        All this does is turn aroun and call ``__getitem__``.

        .. Warning::

            There's no reason to override this--override ``get_data``
            and ``get_metadata`` instead.

        :param key: the key being sought

        :param default: the default to return if the key does not
                        exist

        :returns: the value of ``get_metadata`` or ``get_data``
                  (through ``__getitem__``)
        """
        return self.__getitem__(key, default)

    def __setitem__(self, key, value):
        """
        Sets the metadata[key] to the given value.

        This uses ``set_data`` and ``set_metadata``.  Don't override
        this.

        :param key: the given key name

        :param value: the given value
        """
        if key == CONTENT_KEY:
            self.set_data(value)
        else:
            self.set_metadata(key, value)

    def update(self, newdict):
        """
        Updates the contents in this entry with the contents in the
        dict.  It does so by calling ``set_data`` and
        ``set_metadata``.

        .. Warning::

            There's no reason to override this--override ``set_data``
            and ``set_metadata`` instead.

        :param newdict: the dict we're updating this one with
        """
        for mem in newdict.keys():
            if mem == CONTENT_KEY:
                self.set_data(newdict[mem])
            else:
                self.set_metadata(mem, newdict[mem])

    def has_key(self, key):
        """
        Returns whether a given key is in the metadata dict.  If the
        key is the ``CONTENT_KEY``, then we automatically return true.

        .. Warning::

            There's no reason to override this--override
            ``get_metadata`` instead.

        :param key: the key to check in the metadata dict for

        :returns: whether (True) or not (False) the key exists
        """
        if key == CONTENT_KEY or key == CONTENT_KEY + "_escaped":
            return True

        value = self.get_metadata(key, DOESNOTEXIST)
        if value == DOESNOTEXIST:
            value = self.get_metadata(key, DOESNOTEXIST2)
            if value == DOESNOTEXIST2:
                return False

        return True

    def keys(self):
        """
        Returns a list of the keys that can be accessed through
        ``__getitem__``.

        .. Warning::

            There's no reason to override this--override
            ``get_metadata_keys`` instead.

        :returns: list of key names
        """
        keys = self.get_metadata_keys()
        if CONTENT_KEY not in keys:
            keys.append(CONTENT_KEY)
        return keys


def generate_entry(request, properties, data, mtime=None):
    """
    Takes a properties dict and a data string and generates a generic
    entry using the data you provided.

    :param request: the Request object

    :param properties: the dict of properties for the entry

    :param data: the data content for the entry

    :param mtime: the mtime tuple (as given by ``time.localtime()``).
                  if you pass in None, then we'll use localtime.
    """
    entry = EntryBase(request)

    entry.update(properties)
    entry.set_data(data)
    if mtime:
        entry.set_time(mtime)
    else:
        entry.set_time(time.localtime())
    return entry

########NEW FILE########
__FILENAME__ = fileentry
#######################################################################
# This file is part of Pyblosxom.
#
# Copyright (C) 2003-2011 by the Pyblosxom team.  See AUTHORS.
#
# Pyblosxom is distributed under the MIT license.  See the file
# LICENSE for distribution details.
#######################################################################

"""
This module contains FileEntry class which is used to retrieve entries
from a file system.  Since pulling data from the file system and
parsing it is expensive (especially when you have 100s of entries) we
delay fetching data until it's demanded.

The FileEntry calls EntryBase methods addToCache and getFromCache to
handle caching.
"""

import time
import os
import re
from Pyblosxom import tools
from Pyblosxom.entries import base


class FileEntry(base.EntryBase):
    """
    This class gets it's data and metadata from the file specified
    by the filename argument.
    """
    def __init__(self, request, filename, root, datadir=""):
        """
        :param request: the Request object

        :param filename: the complete filename for the file in question
                         including path

        :param root: i have no clue what this is

        :param datadir: the datadir
        """
        base.EntryBase.__init__(self, request)
        self._config = request.get_configuration()
        self._filename = filename.replace(os.sep, '/')
        self._root = root.replace(os.sep, '/')

        self._datadir = datadir or self._config["datadir"]
        if self._datadir.endswith(os.sep):
            self._datadir = self._datadir[:-1]

        self._timetuple = tools.filestat(self._request, self._filename)
        self._mtime = time.mktime(self._timetuple)
        self._fulltime = time.strftime("%Y%m%d%H%M%S", self._timetuple)

        self._populated_data = 0

    def __repr__(self):
        return "<fileentry f'%s' r'%s'>" % (self._filename, self._root)

    def get_id(self):
        """
        Returns the id for this content item--in this case, it's the
        filename.

        :returns: the id of the fileentry (the filename)
        """
        return self._filename

    getId = tools.deprecated_function(get_id)

    def get_data(self):
        """
        Returns the data for this file entry.  The data is the parsed
        (via the entryparser) content of the entry.  We do this on-demand
        by checking to see if we've gotten it and if we haven't then
        we get it at that point.

        :returns: the content for this entry
        """
        if self._populated_data == 0:
            self._populatedata()
        return self._data

    getData = tools.deprecated_function(get_data)

    def get_metadata(self, key, default=None):
        """
        This overrides the ``base.EntryBase`` ``get_metadata`` method.

        .. Note::

            We populate our metadata lazily--only when it's requested.
            This delays parsing of the file as long as we can.
        """
        if self._populated_data == 0:
            self._populatedata()

        return self._metadata.get(key, default)

    getMetadata = tools.deprecated_function(get_metadata)

    def _populatedata(self):
        """
        Fills the metadata dict with metadata about the given file.
        This metadata consists of things we pick up from an os.stat
        call as well as knowledge of the filename and the root
        directory.  We then parse the file and fill in the rest of the
        information that we know.
        """
        file_basename = os.path.basename(self._filename)

        path = self._filename.replace(self._root, '')
        path = path.replace(os.path.basename(self._filename), '')
        path = path[:-1]

        absolute_path = self._filename.replace(self._datadir, '', 1)
        absolute_path = absolute_path.replace(file_basename, '')
        absolute_path = absolute_path[1:][:-1]

        if absolute_path and absolute_path[-1] == "/":
            absolute_path = absolute_path[0:-1]

        filename_no_ext = os.path.splitext(file_basename)[0]
        if absolute_path == '':
            file_path = filename_no_ext
        else:
            file_path = '/'.join((absolute_path, filename_no_ext))

        tb_id = '%s/%s' % (absolute_path, filename_no_ext)
        tb_id = re.sub(r'[^A-Za-z0-9]', '_', tb_id)

        self['path'] = path
        self['tb_id'] = tb_id
        self['absolute_path'] = absolute_path
        self['file_path'] = file_path
        self['fn'] = filename_no_ext
        self['filename'] = self._filename

        self.set_time(self._timetuple)

        data = self._request.get_data()

        entry_dict = self.get_from_cache(self._filename)
        if not entry_dict:
            file_ext = os.path.splitext(self._filename)
            if file_ext:
                file_ext = file_ext[1][1:]

            eparser = data['extensions'][file_ext]
            entry_dict = eparser(self._filename, self._request)
            self.add_to_cache(self._filename, entry_dict)

        self.update(entry_dict)
        self._populated_data = 1

########NEW FILE########
__FILENAME__ = memcache
#######################################################################
# This file is part of Pyblosxom.
#
# Copyright (C) 2003-2011 by the Pyblosxom team.  See AUTHORS.
#
# Pyblosxom is distributed under the MIT license.  See the file
# LICENSE for distribution details.
#######################################################################

"""Holds memcache functions.
"""

# Whether or not to use memcache.
usecache = False

_memcache_cache = {}


def memcache_decorator(scope, instance=False):
    """Caches function results in memory

    This is a pretty classic memoization system for plugins. There's
    no expiration of cached data---it just hangs out in memory
    forever.

    This is great for static rendering, but probably not for running
    as a CGI/WSGI application.

    This is disabled by default. It must be explicitly enabled
    to have effect.

    Some notes:

    1. the function arguments MUST be hashable--no dicts, lists, etc.
    2. this probably does not play well with
       non-static-rendering--that should get checked.
    3. TODO: the two arguments are poorly named--that should get fixed.

    :arg scope: string defining the scope. e.g. 'pycategories'.
    :arg instance: whether or not the function being decorated is
        bound to an instance (i.e. is the first argument "self" or
        "cls"?)
    """
    def _memcache(fun):
        def _memcache_decorated(*args, **kwargs):
            if not usecache:
                return fun(*args, **kwargs)

            try:
                if instance:
                    hash_key = hash((args[1:], frozenset(sorted(kwargs.items()))))
                else:
                    hash_key = hash((args, frozenset(sorted(kwargs.items()))))
            except TypeError:
                print repr((args, kwargs))
                hash_key = None

            if not hash_key:
                return fun(*args, **kwargs)

            try:
                ret = _memcache_cache.setdefault(scope, {})[hash_key]
            except KeyError:
                ret = fun(*args, **kwargs)
                _memcache_cache[scope][hash_key] = ret
            return ret
        return _memcache_decorated
    return _memcache

########NEW FILE########
__FILENAME__ = acronyms
#######################################################################
# This file is part of Pyblosxom.
#
# Copyright (c) 2010, 2011 Will Kahn-Greene
#
# Pyblosxom is distributed under the MIT license.  See the file
# LICENSE for distribution details.
#######################################################################

"""
Summary
=======

This plugin marks abbreviations and acronyms based on an
acronyms/abbreviations files.


Install
=======

This plugin comes with Pyblosxom.  To install, do the following:

1. In your ``config.py`` file, add ``Pyblosxom.plugins.acronyms`` to the
   ``load_plugins`` variable.

2. Create an acronyms file with acronyms and abbreviations in it.

   See below for the syntax.

3. (optional) In your ``config.py`` file, add a line like this::

      py["acronyms_file"] = "/path/to/file"

   Make sure to use the complete path to your acronyms file in place of
   ``"/path/to/file"``.

   This defaults to ``acronyms.txt`` in the parent directory of your
   datadir.


Building the acronyms file
==========================

The file should be a text file with one acronym or abbreviation
followed by an = followed by the explanation.  The
acronym/abbreviation is a regular expression and can contain regular
expression bits.

An acronym is upper or lower case letters that is NOT followed by a
period.  If it's followed by a period, then you need to explicitly
state it's an acronym.

    <acronym> = explanation
    <acronym> = acronym|explanation

Examples::

    ASCII = American Standard Code for Information Interchange
    CGI = Common Gateway Interface; Computer Generated Imagery
    CSS = Cascading Stylesheets
    HTML = Hypertext Markup Language
    HTTP = Hypertext Transport Protocol
    RDF = Resource Description Framework
    RSS = Really Simple Syndication
    URL = Uniform Resource Locator
    URI = Uniform Resource Indicator
    WSGI = Web Server Gateway Interface
    XHTML = Extensible Hypertext Markup Language
    XML = Extensible Markup Language

This one is explicitly labeled an acronym::

    X.M.L. = acronym|Extensible Markup Language

This one uses regular expression to match both ``UTF-8`` and
``UTF8``::

    UTF\-?8 = 8-bit UCS/Unicode Transformation Format

An abbreviation is a series of characters followed by a period.  If
it's not followed by a period, then you need to explicitly state that
it's an abbreviation.

    <abbreviation> = explanation
    <abbreviation> = abbr|explanation

Examples::

    dr. = doctor

This one is explicitly labeled an abbreviation::

    dr = abbr|doctor

.. Note::

   If the first part is an improperly formed regular expression, then
   it will be skipped.

   You can verify that your file is properly formed by running
   ``pyblosxom-cmd test``.


Using acronyms in your blog entries
===================================

When writing a blog entry, write the acronyms and abbreviations
and they'll be marked up by the plugin in the story callback.

If you're writing an entry that you don't want to have marked up, add
this to the metadata for the entry::

    #noacronyms 1


Styling
=======

You might want to add something like this to your CSS::

    acronym {
        border-bottom: 1px dashed #aaa;
        cursor: help;
    }

    abbr {
        border-bottom: 1px dashed #aaa;
        cursor: help;
    }


Origins
=======

Based on the Blosxom acronyms plugin by Axel Beckert at
http://noone.org/blosxom/acronyms .
"""

__author__ = "Will Kahn-Greene"
__email__ = "willg at bluesock dot org"
__version__ = "2011-10-21"
__url__ = "http://pyblosxom.github.com/"
__description__ = "Marks acronyms and abbreviations in blog entries."
__category__ = "text"
__license__ = "MIT"
__registrytags__ = "1.5, core"


import os
import re

from Pyblosxom import tools
from Pyblosxom.tools import pwrap_error


def get_acronym_file(cfg):
    datadir = cfg["datadir"]
    filename = cfg.get("acronym_file",
                       os.path.join(datadir, os.pardir, "acronyms.txt"))
    return filename


def verify_installation(request):
    config = request.get_configuration()
    filename = get_acronym_file(config)
    if not os.path.exists(filename):
        pwrap_error("There is no acronym file at %s." % filename)
        pwrap_error(
            "You should create one.  Refer to documentation for examples.")
        return False

    try:
        fp = open(filename, "r")
    except IOError:
        pwrap_error(
            "Your acronyms file %s cannot be opened for reading.  Please "
            "adjust the permissions." % filename)
        return False

    malformed = False

    # FIXME - this is a repeat of build_acronyms
    for line in fp.readlines():
        line = line.strip()
        firstpart = line.split("=", 1)[0]
        firstpart = "(\\b" + firstpart.strip() + "\\b)"
        try:
            re.compile(firstpart)
        except re.error, s:
            pwrap_error("- '%s' is not a properly formed regexp.  (%s)" %
                        (line, s))
            malformed = True
    fp.close()
    if malformed:
        return False
    return True


def build_acronyms(lines):
    acronyms = []
    for line in lines:
        line = line.split("=", 1)
        firstpart = line[0].strip()

        try:
            firstpartre = re.compile("(\\b" + firstpart + "\\b)")
        except re.error:
            logger = tools.get_logger()
            logger.error("acronyms: '%s' is not a regular expression",
                         firstpart)
            continue

        secondpart = line[1].strip()
        secondpart = secondpart.replace("\"", "&quot;")

        if secondpart.startswith("abbr|") or firstpart.endswith("."):
            if secondpart.startswith("abbr|"):
                secondpart = secondpart[5:]
            repl = "<abbr title=\"%s\">\\1</abbr>" % secondpart
        else:
            if secondpart.startswith("acronym|"):
                secondpart = secondpart[8:]
            repl = "<acronym title=\"%s\">\\1</acronym>" % secondpart

        acronyms.append((firstpartre, repl))
    return acronyms


def cb_start(args):
    request = args["request"]
    config = request.get_configuration()
    filename = get_acronym_file(config)

    try:
        fp = open(filename, "r")
    except IOError:
        return

    lines = fp.readlines()
    fp.close()

    request.get_data()["acronyms"] = build_acronyms(lines)


TAG_RE = re.compile("<\D.*?>")
TAG_DIGIT_RE = re.compile("<\d+?>")


def cb_story(args):
    request = args["request"]
    acrolist = request.get_data()["acronyms"]
    entry = args["entry"]

    if entry.get("noacronyms"):
        return args

    body = entry.get("body", "")

    tags = {}

    def matchrepl(matchobj):
        ret = "<%d>" % len(tags)
        tags[ret] = matchobj.group(0)
        return ret

    body = TAG_RE.sub(matchrepl, body)

    for reob, repl in acrolist:
        body = reob.sub(repl, body)

    def matchrepl(matchobj):
        return tags[matchobj.group(0)]

    body = TAG_DIGIT_RE.sub(matchrepl, body)

    entry["body"] = body
    return args

########NEW FILE########
__FILENAME__ = akismetcomments
#######################################################################
# Copyright (C) 2006 Benjamin Mako Hill <mako@atdot.cc>
#                    Blake Winton <bwinton+blog@latte.ca>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA 02110-1301
# USA
#######################################################################

"""
Summary
=======

Run comments and trackbacks through `Akismet <http://akismet.com/>`_
to see whether to reject them or not.


Install
=======

Requires the ``comments`` plugin.

This plugin comes with Pyblosxom.  To install, do the following:

1. Add ``Pyblosxom.plugins.akismetcomments`` to the ``load_plugins``
   list in your ``config.py`` file.

2. Install the ``akismet`` library.  You can get it at
   http://www.voidspace.org.uk/python/modules.shtml#akismet

3. Set up a Wordpress.com API key.  You can find more information from
   http://faq.wordpress.com/2005/10/19/api-key/ .

4. Use this key to put put the following line into your config.py
   file::

       py['akismet_api_key'] = 'MYKEYID'

5. Add ``$(comment_message)`` to the comment-form template if it isn't
   there already.

   When akismetcomments rejects a comment, it'll populate that
   variable with a message explaining what happened.


History
=======

This plugin merges the work done on the ``akismetComments.py`` plugin
by Blake Winton with the the ``akismet.py`` plugin by Benjamin Mako
Hill.
"""

__author__ = "Benjamin Mako Hill"
__version__ = "0.2"
__email__ = ""
__url__ = "http://pyblosxom.github.com/"
__description__ = "Rejects comments using akismet"
__category__ = "comments"
__license__ = "GPLv2"
__registrytags__ = "1.4, 1.5, core"


from Pyblosxom.tools import pwrap_error


def verify_installation(request):
    try:
        from akismet import Akismet
    except ImportError:
        pwrap_error(
            "Missing module 'akismet'.  See documentation for getting it.")
        return False

    config = request.get_configuration()

    # try to check to se make sure that the config file has a key
    if not "akismet_api_key" in config:
        pwrap_error("Missing required configuration value 'akismet_key'")
        return False

    a = Akismet(config['akismet_api_key'], config['base_url'],
                agent='Pyblosxom/1.3')
    if not a.verify_key():
        pwrap_error("Could not verify akismet API key.")
        return False

    return True


def cb_comment_reject(args):
    from akismet import Akismet, AkismetError

    request = args['request']
    comment = args['comment']
    config = request.get_configuration()

    http = request.get_http()

    fields = {'comment': 'description',
              'comment_author_email': 'email',
              'comment_author': 'author',
              'comment_author_url': 'link',
              'comment_type': 'type',
              }
    data = {}
    for field in fields:
        if fields[field] in comment:
            data[field] = ""
            for char in list(comment[fields[field]]):
                try:
                    char.encode('ascii')
                # FIXME - bare except--bad!
                except:
                    data[field] = data[field] + "&#" + str(ord(char)) + ";"
                else:
                    data[field] = data[field] + char

    if not data.get('comment'):
        pwrap_error("Comment info not enough.")
        return False
    body = data['comment']

    if 'ipaddress' in comment:
        data['user_ip'] = comment['ipaddress']
    data['user_agent'] = http.get('HTTP_USER_AGENT', '')
    data['referrer'] = http.get('HTTP_REFERER', '')

    api_key = config.get('akismet_api_key')
    base_url = config.get('base_url')

    # initialize the api
    api = Akismet(api_key, base_url, agent='Pyblosxom/1.5')

    if not api.verify_key():
        pwrap_error("Could not verify akismet API key. Comments accepted.")
        return False

    # false is ham, true is spam
    try:
        if api.comment_check(body, data):
            pwrap_error("Rejecting comment")
            return (True,
                    'I\'m sorry, but your comment was rejected by '
                    'the <a href="http://akismet.com/">Akismet</a> '
                    'spam filtering system.')
        else:
            return False
    except AkismetError:
        pwrap_error("Rejecting comment (AkismetError)")
        return (True, "Missing essential data (e.g., a UserAgent string).")


# akismet can handle trackback spam too
cb_trackback_reject = cb_comment_reject

########NEW FILE########
__FILENAME__ = check_blacklist
#######################################################################
# This file is part of Pyblosxom.
#
# Copyright (C) 2002-2011 Will Kahn-Greene
#
# Pyblosxom is distributed under the MIT license.  See the file
# LICENSE for distribution details.
#######################################################################

"""
Summary
=======

This works in conjunction with the comments plugin and allows you to
xreduce comment spam by a words blacklist.  Any comment that contains
one of the blacklisted words will be rejected immediately.

This shouldn't be the only way you reduce comment spam.  It's probably
not useful to everyone, but would be useful to some people as a quick
way of catching some of the comment spam they're getting.


Install
=======

This requires the ``comments`` plugin.

This plugin comes with Pyblosxom.  To install, do the following:

1. Add ``Pyblosxom.plugins.check_blacklist`` to the ``load_plugins``
   list in your ``config.py`` file.

2. Configure as documented below.


Usage
=====

For setup, all you need to do is set the comment_rejected_words
property in your config.py file.  For example, the following will
reject any incoming comments with the words ``gambling`` or ``casino``
in them::

   py["comment_rejected_words"] = ["gambling", "casino"]


The comment_rejected_words property takes a list of strings as a
value.

.. Note::

   There's a deficiency in the algorithm.  Currently, it will match
   substrings, too.  So if you blacklist the word "word", that'll nix
   comments with "word" in it as well as comments with "crossword"
   because "word" is a substring of "crossword".

   Pick your blacklisted words carefully or fix the algorithm!


.. Note::

   This checks all parts of the comment including the ip address of
   the poster.  Blacklisting ip addresses is as easy as adding the ip
   address to the list::

      py["comment_rejected_words"] = ["192.168.1.1", ...]


Additionally, the wbgcomments_blacklist plugin can log when it
blacklisted a comment and what word was used to blacklist it.
Sometimes this information is interesting.  True, "yes, I want to log"
and False (default) if "no, i don't want to log".  Example::

   py["comment_rejected_words_log"] = False
"""

__author__ = "Will Kahn-Greene"
__email__ = "willg at bluesock dot org"
__version__ = "2011-10-25"
__url__ = "http://pyblosxom.github.com/"
__description__ = "Rejects comments using a word blacklist."
__category__ = "comments"
__license__ = "MIT"
__registrytags__ = "1.4, 1.5, core"


import time
import os.path
from Pyblosxom.tools import pwrap_error


def verify_installation(request):
    config = request.get_configuration()
    if not "comment_rejected_words" in config:
        pwrap_error(
            "The \"comment_rejected_words\" property must be set in your "
            "config.py file.  It takes a list of strings as a value.  "
            "Refer to the documentation for more details.")
        return False

    crw = config["comment_rejected_words"]
    if not isinstance(crw, (list, tuple)):
        pwrap_error(
            "The \"comment_rejected_words\" property is incorrectly set in "
            "your config.py file.  It takes a list of strings as a value.  "
            "Refer to the documentation at the top of the comment_blacklist "
            "plugin for more details.")
        return False
    return True


def cb_comment_reject(args):
    r = args["request"]
    c = args["comment"]

    config = r.get_configuration()

    badwords = config.get("comment_rejected_words", [])
    for mem in c.values():
        mem = mem.lower()
        for word in badwords:
            # FIXME - this matches on substrings, too.  should use
            # word-boundaries.
            if mem.find(word) != -1:
                if ((config.get("comment_rejected_words_log", False) and
                     "logdir" in config)):
                    fn = os.path.join(config["logdir"], "blacklist.log")
                    f = open(fn, "a")
                    f.write("%s: %s %s\n" % (
                            time.ctime(), c.get("ipaddress", None), word))
                    f.close()
                return (True, "Comment rejected: contains blacklisted words.")

    return False

########NEW FILE########
__FILENAME__ = check_javascript
#######################################################################
# Copyright (c) 2006 Ryan Barrett
# Copyright (c) 2011 Will Kahn-Greene
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#######################################################################

"""
Summary
=======

This plugin filters spam with a dash of JavaScript on the client side.
The JavaScript sets a hidden input field ``secretToken`` in the
comment form to the blog's title.  This plugin checks the
``secretToken`` URL parameter and rejects the comment if it's not set
correctly.

The benefit of JavaScript as an anti-spam technique is that it's very
successful.  It has extremely low false positive and false negative
rates, as compared to conventional techniques like CAPTCHAs, bayesian
filtering, and keyword detection.

Of course, JavaScript has its own drawbacks, primarily that it's not
supported in extremely old browsers, and that users can turn it off.
That's a very small minority of cases, though.  Its effectiveness as
an anti-spam technique usually make that tradeoff worthwhile.


Install
=======

Requires the ``comments`` plugin.

This plugin comes with Pyblosxom.  To install, do the following:

1. Add ``Pyblosxom.plugins.check_javascript`` to the ``load_plugins``
   list in your ``config.py`` file.

2. Configure as documented below.


Configure
=========

1. Make sure you have ``blog_title`` set in your ``config.py``.

2. Add the following bits to your ``comment-form`` template inside
   the ``<form>`` tags::

      <input type="hidden" name="secretToken" id="secretTokenInput"
        value="pleaseDontSpam" />

      <script type="text/javascript">
      // used by check_javascript.py. this is almost entirely backwards
      // compatible, back to 4.x browsers.
      document.getElementById("secretTokenInput").value = "$(blog_title)";
      </script>

"""
__author__ = "Ryan Barrett"
__email__ = "pyblosxom at ryanb dot org"
__version__ = "2011-10-25"
__url__ = "http://pyblosxom.github.com/"
__description__ = "Rejects comments using JavaScript"
__category__ = "comments"
__license__ = "GPLv2"
__registrytags__ = "1.4, 1.5, core"


from Pyblosxom import tools


def verify_installation(request):
    return True


def cb_comment_reject(args):
    request = args["request"]
    config = request.get_configuration()
    http = request.get_http()
    form = http['form']

    if (('secretToken' in form and
         form['secretToken'].value == config['blog_title'])):
        return False

    dump = '\n'.join(['%s: %s' % (arg.name, arg.value)
                      for arg in dict(form).values()])
    logger = tools.get_logger()
    logger.info('Comment rejected from %s:\n%s' % (
            http['REMOTE_ADDR'], dump))
    return True

########NEW FILE########
__FILENAME__ = check_nonhuman
#######################################################################
# This file is part of Pyblosxom.
#
# Copyright (c) 2006-2011 Will Kahn-Greene
#
# Pyblosxom is distributed under the MIT license.  See the file
# LICENSE for distribution details.
#######################################################################

"""
Summary
=======

This works in conjunction with the comments plugin and allows you to
significantly reduce comment spam by adding a "I am human" checkbox to
your form.  Any comments that aren't "from a human" get rejected
immediately.

This shouldn't be the only way you reduce comment spam.  It's probably
not useful to everyone, but would be useful to some people as a quick
way of catching some of the comment spam they're getting.

Usually this works for a while, then spam starts coming in again.  At
that point, I change the ``nonhuman_name`` config.py variable value
and I stop getting comment spam.


Install
=======

Requires the ``comments`` plugin.

This plugin comes with Pyblosxom.  To install, do the following:

1. Add ``Pyblosxom.plugins.check_nonhuman`` to the ``load_plugins`` list
   in your ``config.py`` file.

2. Configure as documented below.


Usage
=====

For setup, copy the plugin to your plugins directory and add it to
your load_plugins list in your config.py file.

Then add the following item to your config.py (this defaults to
"iamhuman")::

   py["nonhuman_name"] = "iamhuman"


Then add the following to your comment-form template just above the
submit button (make sure to match the input name to your configured
input name)::

   <input type="checkbox" name="iamhuman" value="yes">
   Yes, I am human!


Alternatively, if you set the ``nonhuman_name`` property, then you should
do this::

   <input type="checkbox" name="$(nonhuman_name)" value="yes">
   Yes, I am human!


Additionally, the nonhuman plugin can log when it rejected a comment.
This is good for statistical purposes.  1 if "yes, I want to log" and
0 (default) if "no, i don't want to log".  Example::

   py["nonhuman_log"] = 1


And that's it!

The idea came from::

   http://www.davidpashley.com/cgi/pyblosxom.cgi/2006/04/28#blog-spam
"""

__author__ = "Will Kahn-Greene"
__email__ = "willg at bluesock dot org"
__version__ = "2011-10-25"
__url__ = "http://pyblosxom.github.com/"
__description__ = "Rejects non-human comments."
__category__ = "comments"
__license__ = "MIT"
__registrytags__ = "1.4, 1.5, core"


import os
import time
from Pyblosxom.tools import pwrap


def verify_installation(request):
    config = request.get_configuration()
    if not "nonhuman_name" in config:
        pwrap("missing optional property: 'nonhuman_name'")

    return True


def cb_comment_reject(args):
    r = args["request"]
    c = args["comment"]

    config = r.get_configuration()

    if not config.get("nonhuman_name", "iamhuman") in c:
        if config.get("nonhuman_log", 0) and "logdir" in config:
            fn = os.path.join(config["logdir"], "nothuman.log")
            f = open(fn, "a")
            f.write("%s: %s\n" % (
                    time.ctime(), c.get("ipaddress", None)))
            f.close()
        return True, "Comment rejected: I don't think you're human."

    return False

########NEW FILE########
__FILENAME__ = comments
#######################################################################
# This file is part of Pyblosxom.
#
# Copyright (C) 2003-2011 by the Pyblosxom team.  See AUTHORS.
#
# Pyblosxom is distributed under the MIT license.  See the file
# LICENSE for distribution details.
#######################################################################

"""
Summary
=======

Adds comments to your blog.  Supports preview, AJAX posting, SMTP
notifications, plugins for rejecting comments (and thus reducing
spam), ...

Comments are stored in a directory that parallels the data directory.
The comments themselves are stored as XML files named
entryname-datetime.suffix.  The comment system allows you to specify
the directory where the comment directory tree will stored, and the
suffix used for comment files.  You need to make sure that this
directory is writable by whatever is running Pyblosxom.

Comments are stored one or more per file in a parallel hierarchy to
the datadir hierarchy.  The filename of the comment is the filename of
the blog entry, plus the creation time of the comment as a float, plus
the comment extension.

Comments now follow the ``blog_encoding`` variable specified in
``config.py``.  If you don't include a ``blog_encoding`` variable,
this will default to utf-8.

Comments will be shown for a given page if one of the following is
true:

1. the page has only one blog entry on it and the request is for a
   specific blog entry as opposed to a category with only one entry
   in it

2. if "showcomments=yes" is in the querystring then comments will
   be shown


.. Note::

   This comments plugin does not work with static rendering.  If you
   are using static rendering to build your blog, you won't be able to
   use this plugin.


Install
=======

This plugin comes with Pyblosxom.  To install, do the following:

1. Add ``Pyblosxom.plugins.comments`` to the ``load_plugins`` list of
   your ``config.py`` file.

   Example::

       py["load_plugins"] = ["Pyblosxom.plugins.comments"]

2. Configure as documented below in the Configuration section.

3. Add templates to your html flavour as documented in the Flavour
   templates section.


Configuration
=============

1. Set ``py['comment_dir']`` to the directory (in your data directory)
   where you want the comments to be stored.  The default value is a
   directory named "comments" in your datadir.

2. (optional) The comment system can notify you via e-mail when new
   comments/trackbacks/pingbacks are posted.  If you want to enable
   this feature, create the following config.py entries:

      py['comment_smtp_from'] - the email address sending the notification
      py['comment_smtp_to']   - the email address receiving the notification

   If you want to use an SMTP server, then set::

      py['comment_smtp_server'] - your SMTP server hostname/ip address

   **OR** if you want to use a mail command, set::

      py['comment_mta_cmd']     - the path to your MTA, e.g. /usr/bin/mail

   Example 1::

      py['comment_smtp_from']   = "joe@joe.com"
      py['comment_smtp_to']     = "joe@joe.com"
      py['comment_smtp_server'] = "localhost"

   Example 2::

      py['comment_smtp_from']   = "joe@joe.com"
      py['comment_smtp_to']     = "joe@joe.com"
      py['comment_mta_cmd']     = "/usr/bin/mail"

3. (optional) Set ``py['comment_ext']`` to the change comment file
   extension.  The default file extension is "cmt".


This module supports the following config parameters (they are not
required):

``comment_dir``

   The directory we're going to store all our comments in.  This
   defaults to datadir + "comments".

   Example::

      py["comment_dir"] = "/home/joe/blog/comments/"

``comment_ext``

   The file extension used to denote a comment file.  This defaults
   to "cmt".

``comment_draft_ext``

   The file extension used for new comments that have not been
   manually approved by you.  This defaults to the value in
   ``comment_ext``---i.e. there is no draft stage.

``comment_smtp_server``

   The smtp server to send comments notifications through.

``comment_mta_cmd``

   Alternatively, a command line to invoke your MTA (e.g.  sendmail)
   to send comment notifications through.

``comment_smtp_from``

   The email address comment notifications will be from.  If you're
   using SMTP, this should be an email address accepted by your SMTP
   server.  If you omit this, the from address will be the e-mail
   address as input in the comment form.

``comment_smtp_to``

   The email address to send comment notifications to.

``comment_nofollow``

   Set this to 1 to add ``rel="nofollow"`` attributes to links in the
   description---these attributes are embedded in the stored
   representation.

``comment_disable_after_x_days``

   Set this to a positive integer and users won't be able to leave
   comments on entries older than x days.


Related files
=============

.. only:: text

   You can find the comment-story file in the docs at
   http://pyblosxom.github.com/ or in the tarball under
   docs/_static/plugins/comments/.


This plugin has related files like flavour templates, javascript file,
shell scripts and such.  All of these files can be gotten from `here
<../_static/plugins/comments/>`_


Flavour templates
=================

The comments plugin requires at least the ``comment-story``,
``comment``, and ``comment-form`` templates.

The way the comments plugin assembles flavour files is like this::

    comment-story
    comment (zero or more)
    comment-form

Thus if you want to have your entire comment section in a div
container, you'd start the div container at the top of
``comment-story`` and end it at the bottom of ``comment-form``.


comment-story
-------------

The ``comment-story`` template comes at the beginning of the comment
section before the comments and the comment form.


Variables available:

   $num_comments - Contains an integer count of the number of comments
                   associated with this entry


.. only:: text

   You can find the comment-story file in the docs at
   http://pyblosxom.github.com/ or in the tarball under
   docs/_static/plugins/comments/.


Link to file: `comment-story <../_static/plugins/comments/comment-story>`_

.. literalinclude:: ../_static/plugins/comments/comment-story
   :language: html


comment
-------

The ``comment`` template is used to format a single entry that has
comments.

Variables available::

   $cmt_title - the title of the comment
   $cmt_description - the content of the comment or excerpt of the
                      trackback/pingback
   $cmt_link - the pingback link referring to this entry
   $cmt_author - the author of the comment or trackback
   $cmt_optionally_linked_author - the author, wrapped in an <a href> tag
                                   to their link if one was provided
   $cmt_pubDate - the date and time of the comment/trackback/pingback
   $cmt_source - the source of the trackback


.. only:: text

   You can find the comment-story file in the docs at
   http://pyblosxom.github.com/ or in the tarball under
   docs/_static/plugins/comments/.


Link to file: `comment <../_static/plugins/comments/comment>`_

.. literalinclude:: ../_static/plugins/comments/comment
   :language: html


comment-form
------------

The ``comment-form`` comes at the end of all the comments.  It has the
comment form used to enter new comments.

.. only:: text

   You can find the comment-story file in the docs at
   http://pyblosxom.github.com/ or in the tarball under
   docs/_static/plugins/comments/.


Link to file: `comment-form <../_static/plugins/comments/comment-form>`_

.. literalinclude:: ../_static/plugins/comments/comment-form
   :language: html


Dealing with comment spam
=========================

You'll probably have comment spam.  There are a bunch of core plugins
that will help you reduce the comment spam that come with Pyblosxom as
well as ones that don't.

Best to check the core plugins first.


Compacting comments
===================

This plugin always writes each comment to its own file, but as an
optimization, it supports files that contain multiple comments.  You
can use ``compact_comments.sh`` to compact comments into a single file
per entry.

.. only:: text

   compact_comments.sh is located in docs/_static/plugins/comments/


You can find ``compact_comments.sh`` `here
<../_static/plugins/comments/>`_.


Implementing comment preview
============================

.. Note::

   Comment preview is implemented by default---all the bits listed
   below are in the comment-form and comment-preview templates.

   This documentation is here in case you had an older version of the
   comments plugin or you want to know what to remove to remove
   comment preview.


If you would like comment previews, you need to do 2 things.

1. Add a preview button to the ``comment-form`` template like this::

      <input name="preview" type="submit" value="Preview" />

   You may change the contents of the value attribute, but the name of
   the input must be "preview".  I put it next to the "Submit" button.

2. Still in your ``comment-form.html`` template, you need to use the
   comment values to fill in the values of your input fields like so::

      <input name="author" type="text" value="$(cmt_author)">
      <input name="email" type="text" value="$(cmt_email)">
      <input name="url" type="text" value="$(cmt_link)">
      <textarea name="body">$(cmt_description)</textarea>

   If there is no preview available, these variables will be stripped
   from the text and cause no problem.

3. Create a ``comment-preview`` template.  This can be a copy of your
   ``comment`` template if you like with some additional text along the
   lines of **"This is a preview!"**

   All of the available variables from the ``comment`` template are
   available in the ``comment-preview`` template.

.. only:: text

   You can find the comment-story file in the docs at
   http://pyblosxom.github.com/ or in the tarball under
   docs/_static/plugins/comments/.


comment-preview
---------------

Link to file: `comment-preview <../_static/plugins/comments/comment-preview>`_

.. literalinclude:: ../_static/plugins/comments/comment-preview
   :language: html


AJAX support
============

Comment previewing and posting can optionally use AJAX, as opposed to
full HTTP POST requests. This avoids a full-size roundtrip and
re-render, so commenting feels faster and more lightweight.

AJAX commenting degrades gracefully in older browsers.  If JavaScript
is disabled or not supported in the user's browser, or if it doesn't
support XmlHttpRequest, comment posting and preview will use normal
HTTP POST.  This will also happen if comment plugins that use
alternative protocols are detected, like ``comments_openid.py``.

To add AJAX support, you need to make the following modifications to your
``comment-form`` template:

1. The comment-anchor tag must be the first thing in the
   ``comment-form`` template::

      <p id="comment-anchor" />

2. Change the ``<form...>`` tag to something like this::

      <form method="post" action="$(base_url)/$(file_path)#comment-anchor"
         name="comments_form" id="comments_form" onsubmit="return false;">

   .. Note::

      If you run pyblosxom inside cgiwrap, you'll probably need to
      remove ``#comment-anchor`` from the URL in the action attribute.
      They're incompatible.

      Your host may even be using cgiwrap without your knowledge. If
      AJAX comment previewing and posting don't work, try removing
      ``#comment-anchor``.

3. Add ``onclick`` handlers to the button input tags::

      <input value="Preview" name="preview" type="button" id="preview"
          onclick="send_comment('preview');" />
      <input value="Submit" name="submit" type="button" id="post"
          onclick="send_comment('post');" />

4. Copy ``comments.js`` file to a location on your server that's
   servable by your web server.

   You can find this file `here <../_static/plugins/comments/>`_.

   .. only:: text

      You can find comments.js in docs/_static/plugins/comments/.

5. Include this script tag somewhere after the ``</form>`` closing tag::

      <script type="text/javascript" src="/comments.js"></script>

   Set the url for ``comments.js`` to the url for where
   ``comments.js`` is located on your server from step 4.

   .. Note::

      Note the separate closing ``</script>`` tag!  It's for IE;
      without it, IE won't actually run the code in ``comments.js``.


nofollow support
================

This implements Google's nofollow support for links in the body of the
comment.  If you display the link of the comment poster in your HTML
template then you must add the ``rel="nofollow"`` attribute to your
template as well


Note to developers who are writing plugins that create comments
===============================================================

Each entry has to have the following properties in order to work with
comments:

1. ``absolute_path`` - the category of the entry.

   Example: "dev/pyblosxom" or ""

2. ``fn`` - the filename of the entry without the file extension and without
   the directory.

   Example: "staticrendering"

3. ``file_path`` - the absolute_path plus the fn.

   Example: "dev/pyblosxom/staticrendering"

Also, if you don't want comments for an entry, add::

   #nocomments 1

to the entry or set ``nocomments`` to ``1`` in the properties of the
entry.

"""

__author__ = "Ted Leung, et al"
__email__ = "pyblosxom-devel at sourceforge dot net"
__version__ = "2011-12-17"
__url__ = "http://pyblosxom.github.com/"
__description__ = "Adds comments to a blog entry."
__category__ = "comments"
__license__ = "MIT"
__registrytags__ = "1.4, 1.5, core"


import cgi
import glob
import re
import time
import cPickle
import os
import codecs
import sys
import subprocess
import traceback

from email.MIMEText import MIMEText
from xml.sax.saxutils import escape
from Pyblosxom import tools
from Pyblosxom.renderers import blosxom
from Pyblosxom.tools import pwrap, pwrap_error

LATEST_PICKLE_FILE = 'LATEST.cmt'


def cb_start(args):
    request = args["request"]
    config = request.get_configuration()

    if not 'comment_dir' in config:
        config['comment_dir'] = os.path.join(config['datadir'],'comments')
    if not 'comment_ext' in config:
        config['comment_ext'] = 'cmt'
    if not 'comment_draft_ext' in config:
        config['comment_draft_ext'] = config['comment_ext']
    if not 'comment_nofollow' in config:
        config['comment_nofollow'] = 0


def verify_installation(request):
    config = request.get_configuration()

    retval = True

    if 'comment_dir' in config and not os.path.isdir(config['comment_dir']):
        pwrap_error(
            'The "comment_dir" property in the config file must refer '
            'to a directory')
        retval = False

    smtp_keys_defined = []
    smtp_keys=[
        'comment_smtp_server',
        'comment_smtp_from',
        'comment_smtp_to']
    for k in smtp_keys:
        if k in config:
            smtp_keys_defined.append(k)

    if smtp_keys_defined:
        for i in smtp_keys:
            if i not in smtp_keys_defined:
                pwrap_error("Missing comment SMTP property: '%s'" % i)
                retval = False

    optional_keys = [
        'comment_dir',
        'comment_ext',
        'comment_draft_ext',
        'comment_nofollow',
        'comment_disable_after_x_days']
    for i in optional_keys:
        if not i in config:
            pwrap("missing optional property: '%s'" % i)

    if 'comment_disable_after_x_days' in config:
        if ((not isinstance(config['comment_disable_after_x_days'], int) or
             config['comment_disable_after_x_days'] <= 0)):
            pwrap("comment_disable_after_x_days has a non-positive "
                  "integer value.")

    return retval


def createhtmlmail(html, headers):
    """
    Create a mime-message that will render HTML in popular
    MUAs, text in better ones

    Based on: http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/67083
    """
    import MimeWriter
    import mimetools
    import cStringIO

    out = cStringIO.StringIO() # output buffer for our message
    htmlin = cStringIO.StringIO(html)

    text = re.sub('<.*?>', '', html)
    txtin = cStringIO.StringIO(text)

    # FIXME MimeWriter is deprecated as of Python 2.6
    writer = MimeWriter.MimeWriter(out)
    for header,value in headers:
        writer.addheader(header, value)
    writer.addheader("MIME-Version", "1.0")
    writer.startmultipartbody("alternative")
    writer.flushheaders()

    subpart = writer.nextpart()
    subpart.addheader("Content-Transfer-Encoding", "quoted-printable")
    pout = subpart.startbody("text/plain", [("charset", 'us-ascii')])
    mimetools.encode(txtin, pout, 'quoted-printable')
    txtin.close()

    subpart = writer.nextpart()
    subpart.addheader("Content-Transfer-Encoding", "quoted-printable")
    pout = subpart.startbody("text/html", [("charset", 'us-ascii')])
    mimetools.encode(htmlin, pout, 'quoted-printable')
    htmlin.close()

    writer.lastpart()
    msg = out.getvalue()
    out.close()

    return msg


def read_comments(entry, config):
    """
    @param: a file entry
    @type: dict

    @returns: a list of comment dicts
    """
    filelist = glob.glob(cmt_expr(entry, config))
    comments = []
    for f in filelist:
        comments += read_file(f, config)
    comments = [(cmt['cmt_time'], cmt) for cmt in comments]
    comments.sort()
    return [c[1] for c in comments]


def cmt_expr(entry, config):
    """
    Return a string containing the regular expression for comment entries

    @param: a file entry
    @type: dict
    @returns: a string with the directory path for the comment

    @param: configuratioin dictionary
    @type: dict

    @returns: a string containing the regular expression for comment entries
    """
    cmt_dir = os.path.join(config['comment_dir'], entry['absolute_path'])
    cmt_expr = os.path.join(cmt_dir, entry['fn'] + '-*.' + config['comment_ext'])
    return cmt_expr


def read_file(filename, config):
    """
    Read comment(s) from filename

    @param filename: filename containing comment(s)
    @type filename: string

    @param config: the pyblosxom configuration settings
    @type config: dictionary

    @returns: a list of comment dicts
    """
    from xml.sax import make_parser
    from xml.sax.handler import feature_namespaces, ContentHandler

    class cmt_handler(ContentHandler):
        def __init__(self, cmts):
            self.cmts = cmts
        def startElement(self, name, atts):
            if name == 'item':
                self.cur_cmt = {}
            self._data = ""
        def endElement(self, name):
            self.cur_cmt['cmt_' + name] = self._data
            if name == 'item':
                self.cmts.append(self.cur_cmt)
        def characters(self, content):
            self._data += content

    cmts = []

    try:
        parser = make_parser()
        parser.setFeature(feature_namespaces, 0)
        handler = cmt_handler(cmts)
        parser.setContentHandler(handler)
        parser.parse(filename)

    # FIXME - bare except here--bad!
    except:
        logger = tools.get_logger()
        logger.error("bad comment file: %s\nerror was: %s" %
                     (filename, traceback.format_exception(*sys.exc_info())))
        return []

    for cmt in cmts:
        # time.time()
        cmt['cmt_time'] = float(cmt['cmt_pubDate'])
        # pretty time
        cmt['cmt_pubDate'] = time.ctime(float(cmt['cmt_pubDate']))
        cmt['cmt_w3cdate'] = time.strftime('%Y-%m-%dT%H:%M:%SZ',
                                           time.gmtime(cmt['cmt_time']))
        cmt['cmt_date'] = time.strftime('%a %d %b %Y',
                                        time.gmtime(cmt['cmt_time']))
        if cmt['cmt_link']:
            link = add_dont_follow('<a href="%s">%s</a>' %
                                   (cmt['cmt_link'], cmt['cmt_author']),
                                   config)
            cmt['cmt_optionally_linked_author'] = link
        else:
            cmt['cmt_optionally_linked_author'] = cmt['cmt_author']

    return cmts


def write_comment(request, config, data, comment, encoding):
    """
    Write a comment

    @param config: dict containing pyblosxom config info
    @type  config: dict

    @param data: dict containing entry info
    @type  data: dict

    @param comment: dict containing comment info
    @type  comment: dict

    @return: The success or failure of creating the comment.
    @rtype: string
    """
    entry_list = data.get("entry_list", [])
    if not entry_list:
        return "No such entry exists."

    entry = data['entry_list'][0]
    cdir = os.path.join(config['comment_dir'], entry['absolute_path'])
    cdir = os.path.normpath(cdir)
    if not os.path.isdir(cdir):
        os.makedirs(cdir)

    cfn = os.path.join(cdir, entry['fn'] + "-" + comment['pubDate'] + "." + config['comment_draft_ext'])

    def make_xml_field(name, field):
        return "<" + name + ">" + cgi.escape(field.get(name, "")) + "</"+name+">\n";

    filedata = '<?xml version="1.0" encoding="%s"?>\n' % encoding
    filedata += "<item>\n"
    for key in comment:
        filedata += make_xml_field(key, comment)
    filedata += "</item>\n"

    try :
        cfile = codecs.open(cfn, "w", encoding)
    except IOError:
        logger = tools.get_logger()
        logger.error("couldn't open comment file '%s' for writing" % cfn)
        return "Internal error: Your comment could not be saved."

    cfile.write(filedata)
    cfile.close()

    # write latest pickle
    latest = None
    latest_filename = os.path.join(config['comment_dir'], LATEST_PICKLE_FILE)
    try:
        latest = open(latest_filename, "w")
    except IOError:
        logger = tools.get_logger()
        logger.error("couldn't open latest comment pickle for writing")
        return "Couldn't open latest comment pickle for writing."
    else:
        mod_time = float(comment['pubDate'])

    try:
        cPickle.dump(mod_time, latest)
        latest.close()
    except IOError:
        if latest:
            latest.close()

        logger = tools.get_logger()
        logger.error("comment may not have been saved to pickle file.")
        return "Internal error: Your comment may not have been saved."

    if ((('comment_mta_cmd' in config
          or 'comment_smtp_server' in config)
         and 'comment_smtp_to' in config)):
        # FIXME - removed grabbing send_email's return error message
        # so there's no way to know if email is getting sent or not.
        send_email(config, entry, comment, cdir, cfn)

    # figure out if the comment was submitted as a draft
    if config["comment_ext"] != config["comment_draft_ext"]:
        return "Comment was submitted for approval.  Thanks!"

    return "Comment submitted.  Thanks!"


def send_email(config, entry, comment, comment_dir, comment_filename):
    """Send an email to the blog owner on a new comment

    @param config: configuration as parsed by Pyblosxom
    @type config: dictionary

    @param entry: a file entry
    @type config: dictionary

    @param comment: comment as generated by read_comments
    @type comment: dictionary

    @param comment_dir: the comment directory
    @type comment_dir: string

    @param comment_filename: file name of current comment
    @type comment_filename: string
    """
    import smtplib
    # import the formatdate function which is in a different
    # place in Python 2.3 and up.
    try:
        from email.Utils import formatdate
    except ImportError:
        from rfc822 import formatdate
    from socket import gethostbyaddr

    author = escape_smtp_commands(clean_author(comment['author']))
    description = escape_smtp_commands(comment['description'])
    ipaddress = escape_smtp_commands(comment.get('ipaddress', '?'))

    if 'comment_smtp_from' in config:
        email = config['comment_smtp_from']
    else:
        email = escape_smtp_commands(clean_author(comment['email']))

    try:
        curl = "%s/%s" % (config['base_url'],
                          tools.urlencode_text(entry['file_path']))
        comment_dir = os.path.join(config['comment_dir'], entry['absolute_path'])

        # create the message
        message = []
        message.append("Name: %s" % author)
        if 'email' in comment:
            message.append("Email: %s" % comment['email'])
        if 'link' in comment:
            message.append("URL: %s" % comment['link'])
        try:
            host_name = gethostbyaddr(ipaddress)[0]
            message.append("Hostname: %s (%s)" % (host_name, ipaddress))
        # FIXME - bare except here--bad!
        except:
            message.append("IP: %s" % ipaddress)
        message.append("Entry URL: %s" % curl)
        message.append("Comment location: %s" % comment_filename)
        message.append("\n\n%s" % description)

        if 'comment_mta_cmd' in config:
            # set the message headers
            message.insert(0, "")
            message.insert(0, "Subject: comment on %s" % curl)
            message.insert(0, "Date: %s" % formatdate(float(comment['pubDate'])))
            message.insert(0, "To: %s" % config["comment_smtp_to"])
            message.insert(0, "From: %s" % email)

            body = '\n'.join(message).encode('utf-8')

            argv = [config['comment_mta_cmd'],
                    '-s',
                    '"comment on %s"' % curl,
                    config['comment_smtp_to']]

            process = subprocess.Popen(
                argv, stdin=subprocess.PIPE,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            process.stdin.write(body)
            process.stdin.close()
            process.wait()
            stdout = process.stdout.read()
            stderr = process.stderr.read()
            tools.get_logger().debug('Ran MTA command: ' + ' '.join(argv))
            tools.get_logger().debug('Received stdout: ' + stdout)
            tools.get_logger().debug('Received stderr: ' + stderr)
            # the except clause below will catch this
            assert stderr == '', stderr

        else:
            assert 'comment_smtp_server' in config
            server = smtplib.SMTP(config['comment_smtp_server'])
            mimemsg = MIMEText("\n".join(message).encode("utf-8"), 'plain', 'utf-8')

            # set the message headers
            mimemsg["From"] = email
            mimemsg["To"] = config["comment_smtp_to"]
            mimemsg["Date"] = formatdate(float(comment["pubDate"]))
            mimemsg["Subject"] = ("comment on %s" % curl)

            # send the message via smtp
            server.sendmail(from_addr=email,
                            to_addrs=config['comment_smtp_to'],
                            msg=mimemsg.as_string())
            server.quit()

    except Exception, e:
        tools.get_logger().error("error sending email: %s" %
                                traceback.format_exception(*sys.exc_info()))


def check_comments_disabled(config, entry):
    disabled_after_x_days = config.get("comment_disable_after_x_days", 0)
    if not isinstance(disabled_after_x_days, int):
        # FIXME - log an error?
        return False

    if disabled_after_x_days <= 0:
        # FIXME - log an error?
        return False

    if not entry.has_key('mtime'):
        return False

    entry_age = (time.time() - entry['mtime']) / (60 * 60 * 24)
    if entry_age > disabled_after_x_days:
        return True
    return False


def clean_author(s):
    """
    Guard against blasterattacko style attacks that embedd SMTP commands in
    author field.

    If author field is more than one line, reduce to one line

    @param the string to be checked
    @type string

    @returns the sanitized string
    """
    return s.splitlines()[0]


def escape_smtp_commands(s):
    """
    Guard against blasterattacko style attacks that embed SMTP commands by
    using an HTML span to make the command syntactically invalid to SMTP but
    renderable by HTML

    @param the string to be checked
    @type string

    @returns the sanitized string
    """
    def repl_fn(mo):
        return '<span>'+mo.group(0)+'</span>'
    s = re.sub('([Tt]o:.*)',repl_fn,s)
    s = re.sub('([Ff]rom:.*)',repl_fn,s)
    s = re.sub('([Ss]ubject:.*)',repl_fn,s)
    return s


def sanitize(body):
    """
    This code shamelessly lifted from Sam Ruby's mombo/post.py
    """
    body=re.sub(r'\s+$','',body)
    body=re.sub('\r\n?','\n', body)

    # naked urls become hypertext links
    body=re.sub('(^|[\\s.:;?\\-\\]<])' +
                '(http://[-\\w;/?:@&=+$.!~*\'()%,#]+[\\w/])' +
                '(?=$|[\\s.:;?\\-\\[\\]>])',
                '\\1<a href="\\2">\\2</a>',body)

    # html characters used in text become escaped
    body = escape(body)

    # passthru <a href>, <em>, <i>, <b>, <blockquote>, <br/>, <p>,
    # <abbr>, <acronym>, <big>, <cite>, <code>, <dfn>, <kbd>, <pre>, <small>
    # <strong>, <sub>, <sup>, <tt>, <var>, <ul>, <ol>, <li>
    body = re.sub('&lt;a href="([^"]*)"&gt;([^&]*)&lt;/a&gt;',
                  '<a href="\\1">\\2</a>', body)
    body = re.sub('&lt;a href=\'([^\']*)\'&gt;([^&]*)&lt;/a&gt;',
                  '<a href="\\1">\\2</a>', body)
    body = re.sub('&lt;em&gt;([^&]*)&lt;/em&gt;', '<em>\\1</em>', body)
    body = re.sub('&lt;i&gt;([^&]*)&lt;/i&gt;', '<i>\\1</i>', body)
    body = re.sub('&lt;b&gt;([^&]*)&lt;/b&gt;', '<b>\\1</b>', body)
    body = re.sub('&lt;blockquote&gt;([^&]*)&lt;/blockquote&gt;',
                  '<blockquote>\\1</blockquote>', body)
    body = re.sub('&lt;br\s*/?&gt;\n?', '\n', body)

    body = re.sub('&lt;abbr&gt;([^&]*)&lt;/abbr&gt;', '<abbr>\\1</abbr>', body)
    body = re.sub('&lt;acronym&gt;([^&]*)&lt;/acronym&gt;', '<acronym>\\1</acronym>', body)
    body = re.sub('&lt;big&gt;([^&]*)&lt;/big&gt;', '<big>\\1</big>', body)
    body = re.sub('&lt;cite&gt;([^&]*)&lt;/cite&gt;', '<cite>\\1</cite>', body)
    body = re.sub('&lt;code&gt;([^&]*)&lt;/code&gt;', '<code>\\1</code>', body)
    body = re.sub('&lt;dfn&gt;([^&]*)&lt;/dfn&gt;', '<dfn>\\1</dfn>', body)
    body = re.sub('&lt;kbd&gt;([^&]*)&lt;/kbd&gt;', '<kbd>\\1</kbd>', body)
    body = re.sub('&lt;pre&gt;([^&]*)&lt;/pre&gt;', '<pre>\\1</pre>', body)
    body = re.sub('&lt;small&gt;([^&]*)&lt;/small&gt;', '<small>\\1</small>', body)
    body = re.sub('&lt;strong&gt;([^&]*)&lt;/strong&gt;', '<strong>\\1</strong>', body)
    body = re.sub('&lt;sub&gt;([^&]*)&lt;/sub&gt;', '<sub>\\1</sub>', body)
    body = re.sub('&lt;sup&gt;([^&]*)&lt;/sup&gt;', '<sup>\\1</sup>', body)
    body = re.sub('&lt;tt&gt;([^&]*)&lt;/tt&gt;', '<tt>\\1</tt>', body)
    body = re.sub('&lt;var&gt;([^&]*)&lt;/var&gt;', '<var>\\1</var>', body)

    # handle lists
    body = re.sub('&lt;ul&gt;\s*', '<ul>', body)
    body = re.sub('&lt;/ul&gt;\s*', '</ul>', body)
    body = re.sub('&lt;ol&gt;\s*', '<ol>', body)
    body = re.sub('&lt;/ol&gt;\s*', '</ol>', body)
    body = re.sub('&lt;li&gt;([^&]*)&lt;/li&gt;\s*', '<li>\\1</li>', body)
    body = re.sub('&lt;li&gt;', '<li>', body)

    body = re.sub('&lt;/?p&gt;', '\n\n', body).strip()

    # wiki like support: _em_, *b*, [url title]
    body = re.sub(r'\b_(\w.*?)_\b', r'<em>\1</em>', body)
    body = re.sub(r'\*(\w.*?)\*', r'<b>\1</b>', body)
    body = re.sub(r'\[(\w+:\S+\.gif) (.*?)\]', r'<img src="\1" alt="\2" />', body)
    body = re.sub(r'\[(\w+:\S+\.jpg) (.*?)\]', r'<img src="\1" alt="\2" />', body)
    body = re.sub(r'\[(\w+:\S+\.png) (.*?)\]', r'<img src="\1" alt="\2" />', body)
    body = re.sub(r'\[(\w+:\S+) (.*?)\]', r'<a href="\1">\2</a>', body).strip()

    # unordered lists: consecutive lines starting with spaces and an asterisk
    chunk = re.compile(r'^( *\*.*(?:\n *\*.*)+)',re.M).split(body)
    for i in range(1, len(chunk), 2):
        html, stack = '', ['']
        for indent, line in re.findall(r'( +)\* +(.*)', chunk[i]) + [('','')]:
            if indent > stack[-1]:
                stack, html = stack + [indent], html + '<ul>\r'
            while indent<stack[-1]:
                stack, html = stack[:-1], html + '</ul>\r'
            if line:
                html += '<li>' + line + '</li>\r'
            chunk[i] = html

    # white space
    chunk = re.split('\n\n+', ''.join(chunk))
    body = re.sub('\n', '<br />\n', body)
    body = re.compile('<p>(<ul>.*?</ul>)\r</p>?', re.M).sub(r'\1', body)
    body = re.compile('<p>(<blockquote>.*?</blockquote>)</p>?', re.M).sub(r'\1', body)
    body = re.sub('\r', '\n', body)
    body = re.sub('  +', '&nbsp; ', body)

    return body


def dont_follow(mo):
    return '<a rel="nofollow" ' + mo.group(1) + '>'


def add_dont_follow(s, config):
    url_pat_str = '<a ([^>]+)>'
    url_pat = re.compile(url_pat_str)
    if config['comment_nofollow'] == 1:
        return url_pat.sub(dont_follow, s)
    else:
        return s


def cb_prepare(args):
    """
    Handle comment related HTTP POST's.

    @param request: pyblosxom request object
    @type request: a Pyblosxom request object
    """
    request = args["request"]
    form = request.get_http()['form']
    config = request.get_configuration()
    data = request.get_data()
    py_http = request.get_http()

    # first we check to see if we're going to print out comments
    # the default is not to show comments
    data['display_comment_default'] = False

    # check to see if they have "showcomments=yes" in the querystring
    qstr = py_http.get('QUERY_STRING', None)
    if qstr != None:
        parsed_qs = cgi.parse_qs(qstr)
        if 'showcomments' in parsed_qs:
            if parsed_qs['showcomments'][0] == 'yes':
                data['display_comment_default'] = True

    # check to see if the bl_type is "file"
    if "bl_type" in data and data["bl_type"] == "file":
        data["bl_type_file"] = "yes"
        data['display_comment_default'] = True

    # second, we check to see if they're posting a comment and we
    # need to write the comment to disk.
    posting = (('ajax' in form and form['ajax'].value == 'post') or
               not "preview" in form)
    if (("title" in form and "author" in form
         and "body" in form and posting)):

        entry = data.get("entry_list", [])
        if len(entry) == 0:
            data["rejected"] = True
            data["comment_message"] = "No such entry exists."
            return
        entry = entry[0]

        if check_comments_disabled(config, entry):
            data["rejected"] = True
            data["comment_message"] = "Comments for that entry are disabled."
            return

        encoding = config.get('blog_encoding', 'utf-8')
        decode_form(form, encoding)

        body = form['body'].value
        author = form['author'].value
        title = form['title'].value
        url = ('url' in form and [form['url'].value] or [''])[0]

        # sanitize incoming data
        body = sanitize(body)
        author = sanitize(author)
        title = sanitize(title)

        # it doesn't make sense to add nofollow to link here, but we should
        # escape it. If you don't like the link escaping, I'm not attached
        # to it.
        cmt_time = time.time()
        w3cdate = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(cmt_time))
        date = time.strftime('%a %d %b %Y', time.gmtime(cmt_time))
        cdict = {'title': title,
                 'author': author,
                 'pubDate': str(cmt_time),
                 'w3cdate': w3cdate,
                 'date': date,
                 'link': massage_link(url),
                 'source': '',
                 'description': add_dont_follow(body, config)}

        keys = form.keys()
        keys = [k for k in keys
                if k not in ["title", "url", "author", "body", "description"]]
        for k in keys:
            cdict[k] = form[k].value

        if 'email' in form:
            cdict['email'] = form['email'].value

        cdict['ipaddress'] = py_http.get('REMOTE_ADDR', '')

        # record the comment's timestamp, so we can extract it and send it
        # back alone, without the rest of the page, if the request was ajax.
        data['cmt_time'] = float(cdict['pubDate'])

        argdict = {"request": request, "comment": cdict}
        reject = tools.run_callback("comment_reject",
                                    argdict,
                                    donefunc=lambda x:x != 0)
        if (((isinstance(reject, tuple) or isinstance(reject, list))
             and len(reject) == 2)):
            reject_code, reject_message = reject
        else:
            reject_code, reject_message = reject, "Comment rejected."
        if reject_code == 1:
            data["comment_message"] = reject_message
            data["rejected"] = True
        else:
            data["comment_message"] = write_comment(request, config, data, \
                                                   cdict, encoding)


class AjaxRenderer(blosxom.Renderer):
    """ The renderer used when responding to AJAX requests to preview
    and post comments. Renders *only* the comment and comment-preview
    divs.
    """
    def __init__(self, request, data):
        out = request.get_configuration().get('stdoutput', sys.stdout)
        blosxom.Renderer.__init__(self, request, out)
        self._ajax_type = request.get_http()['form']['ajax'].value
        self._config = request.get_configuration()
        self._data = data

    def _should_output(self, entry, template_name):
        """ Return whether we should output this template, depending on the
        type of ajax request we're responding to.
        """

        if (self._ajax_type == 'post' and template_name == 'story'):
            entry['comments'] = read_comments(entry, self._config)
            return False

        if self._ajax_type == 'preview' and template_name == 'comment-preview':
            return True
        elif (self._ajax_type == 'post' and template_name == 'comment'
              and round(self._data.get('cmt_time', 0)) == round(entry['cmt_time'])):
            return True
        else:
            return False

    def render_template(self, entry, template_name, override=0):
        if self._should_output(entry, template_name):
            return blosxom.Renderer.render_template(
                self, entry, template_name, override)
        else: return ""

    def _output_flavour(self, entry, template_name):
        if self._should_output(entry, template_name):
            blosxom.Renderer._output_flavour(self, entry, template_name)


def cb_renderer(args):
    request = args['request']
    config = request.get_configuration()
    http = request.get_http()
    form = http['form']

    # intercept ajax requests with our renderer
    if 'ajax' in form and http.get('REQUEST_METHOD', '') == 'POST':
        data = '&'.join(['%s=%s' % (arg.name, arg.value) for arg in form.list])
        tools.get_logger().info('AJAX request: %s' % data)
        return AjaxRenderer(request, request.get_data())


def cb_handle(args):
    request = args['request']
    config = request.get_configuration()

    # serve /comments.js for ajax comments
    if request.get_http()['PATH_INFO'] == '/comments.js':
        response = request.get_response()
        response.add_header('Content-Type', 'text/javascript')

        # look for it in each of the plugin_dirs
        for dir in config['plugin_dirs']:
            comments_js = os.path.join(dir, 'comments.js')
            if os.path.isfile(comments_js):
                f = open(comments_js, 'r')
                response.write(f.read())
                f.close()
                return True


def massage_link(linkstring):
    """Don't allow html in the link string. Prepend http:// if there isn't
    already a protocol."""
    for c in "<>'\"":
        linkstring = linkstring.replace(c, '')
    if linkstring and linkstring.find(':') == -1:
        linkstring = 'http://' + linkstring
    return linkstring


def decode_form(d, blog_encoding):
    """Attempt to decode the POST data with a few likely character encodings.

    If the Content-type header in the HTTP request includes a charset, try
    that first. Then, try the encoding specified in the pybloscom config file.
    if Those fail, try iso-8859-1, utf-8, and ascii.
    """
    encodings = [blog_encoding, 'iso-8859-1', 'utf-8', 'ascii']
    charset = get_content_type_charset()
    if charset:
        encodings = [charset] + encodings

    for key in d.keys():
        for e in encodings:
            try:
                d[key].value = d[key].value.decode(e)
                break
            # FIXME - bare except--bad!
            except:
                continue


def get_content_type_charset():
    """Extract and return the charset part of the HTTP Content-Type
    header.

    Returns None if the Content-Type header doesn't specify a charset.
    """
    content_type = os.environ.get('CONTENT_TYPE', '')
    match = re.match('.+; charset=([^;]+)', content_type)
    if match:
        return match.group(1)
    else:
        return None


def cb_head(args):
    renderer = args['renderer']
    template = args['template']

    if 'comment-head' in renderer.flavour and len(renderer.getContent()) == 1:
        args['template'] = renderer.flavour['comment-head']

        # expand all of entry vars for expansion
        entry = args['entry']
        single_entry = entry['entry_list'][0]
        single_entry['title'] # force lazy evaluation
        entry.update(single_entry)
        args['entry'] = entry
    return template


def cb_story(args):
    """For single entry requests, when commenting is enabled and the
    flavour has a comment-story template, append its contents to the
    story template's.
    """
    renderer = args['renderer']
    entry = args['entry']
    template = args['template']
    request = args["request"]
    data = request.get_data()
    config = request.get_configuration()
    # FIXME - entry is currently broken and doesn't support "in"
    if entry.has_key('absolute_path') and not entry.has_key('nocomments'):
        entry['comments'] = read_comments(entry, config)
        entry['num_comments'] = len(entry['comments'])
        if ((len(renderer.get_content()) == 1
             and 'comment-story' in renderer.flavour
             and data['display_comment_default'])):
            template = renderer.flavour.get('comment-story', '')
            args['template'] = args['template'] + template

    return template


def build_preview_comment(form, entry, config):
    """Build a prevew comment by brute force

    @param form: cgi form object (or compatible)
    @type form: Dictionary of objects with a .value propery

    @param entry: pyblosxom entry object
    @type entry: pyblosxom entry object

    @param config: the pyblosxom configuration settings
    @type config: dictionary

    @return: the comment HTML, a string
    """
    c = {}
    # required fields
    try:
        c['cmt_time'] = float(time.time())
        c['cmt_author'] = form['author'].value
        c['cmt_title'] = form['title'].value
        c['cmt_item'] = sanitize(form['body'].value)
        cmt_time = time.time()
        c['cmt_pubDate'] = time.ctime(cmt_time)
        c['cmt_w3cdate'] = time.strftime('%Y-%m-%dT%H:%M:%SZ',
                                         (time.gmtime(cmt_time)))
        c['cmt_date'] = time.strftime('%a %d %b %Y',
                                      time.gmtime(cmt_time))
        c['cmt_description'] = sanitize(form['body'].value)

        # optional fields
        c['cmt_optionally_linked_author'] = c['cmt_author']
        if 'url' in form:
            c['cmt_link'] = massage_link(form['url'].value)
            if c['cmt_link']:
                link = add_dont_follow('<a href="%s">%s</a>' %
                                       (c['cmt_link'], c['cmt_author']),
                                       config)
                c['cmt_optionally_linked_author'] = link

        if 'openid_url' in form:
            c['cmt_openid_url'] = massage_link(form['openid_url'].value)

        if 'email' in form:
            c['cmt_email'] = form['email'].value

    except KeyError, e:
        c['cmt_error'] = 'Missing value: %s' % e

    entry.update(c)
    return c


def cb_story_end(args):
    renderer = args['renderer']
    entry = args['entry']
    template = args['template']
    request = args["request"]
    data = request.get_data()
    form = request.get_http()['form']
    config = request.get_configuration()
    # FIXME - entry is currently broken and doesn't support "in"
    if ((entry.has_key('absolute_path')
         and len(renderer.get_content()) == 1
         and 'comment-story' in renderer.flavour
         and not entry.has_key('nocomments')
         and data['display_comment_default'])):
        output = []
        if entry.get('comments', []):
            comment_entry_base = dict(entry)
            del comment_entry_base['comments']
            for comment in entry['comments']:
                comment_entry = dict(comment_entry_base)
                comment_entry.update(comment)
                output.append(renderer.render_template(comment_entry, 'comment'))
        if (('preview' in form
             and 'comment-preview' in renderer.flavour)):
            com = build_preview_comment(form, entry, config)
            output.append(renderer.render_template(com, 'comment-preview'))
        elif 'rejected' in data:
            rejected = build_preview_comment(form, entry, config)
            msg = '<span class="error">%s</span>' % data["comment_message"]
            rejected['cmt_description'] = msg
            rejected['cmt_description_escaped'] = escape(msg)
            output.append(renderer.render_template(rejected, 'comment'))
        if not check_comments_disabled(config, entry):
            output.append(renderer.render_template(entry, 'comment-form'))
        args['template'] = template + "".join(output)

    return template

########NEW FILE########
__FILENAME__ = conditionalhttp
#######################################################################
# This file is part of Pyblosxom.
#
# Copyright (c) 2004, 2005 Wari Wahab
# Copyright (c) 2010, 2011 Will Kahn-Greene
#
# Pyblosxom is distributed under the MIT license.  See the file
# LICENSE for distribution details.
#######################################################################

"""
Summary
=======

This plugin can help save bandwidth for low bandwidth quota sites.

This is done by output-ing cache friendly HTTP header tags like Last-Modified
and ETag. These values are calculated from the first entry returned by
``entry_list``.


Install
=======

This plugin comes with Pyblosxom.  To install, do the following:

1. In your ``config.py`` file, add ``Pyblosxom.plugins.conditionalhttp`` to
   the ``load_plugins`` variable.
"""

__author__ = "Wari Wahab"
__email__ = "pyblosxom at wari dot per dot sg"
__version__ = "2011-10-22"
__url__ = "http://pyblosxom.github.com/"
__description__ = "Allows browser-side caching with if-not-modified-since."
__category__ = "headers"
__license__ = "MIT"
__registrytags__ = "1.4, 1.5, core"


import time
import os
import cPickle
import calendar

from Pyblosxom import tools


def verify_installation(request):
    # This should just work--no configuration needed.
    return True


def cb_prepare(args):
    request = args["request"]

    data = request.get_data()
    config = request.get_configuration()
    http = request.get_http()
    entry_list = data["entry_list"]
    renderer = data["renderer"]

    if entry_list and entry_list[0].has_key('mtime'):
        # FIXME - this should be generalized to a callback for updated
        # things.
        mtime = entry_list[0]['mtime']
        latest_cmtime = - 1
        if 'comment_dir' in config:
            latest_filename = os.path.join(config['comment_dir'], 'LATEST.cmt')

            if os.path.exists(latest_filename):
                latest = open(latest_filename)
                latest_cmtime = cPickle.load(latest)
                latest.close()

        if latest_cmtime > mtime:
            mtime = latest_cmtime

        # Get our first file timestamp for ETag and Last Modified
        # Last-Modified: Wed, 20 Nov 2002 10:08:12 GMT
        # ETag: "2bdc4-7b5-3ddb5f0c"
        last_modified = time.strftime(
            '%a, %d %b %Y %H:%M:%S GMT', time.gmtime(mtime))
        modified_since = http.get('HTTP_IF_MODIFIED_SINCE', '')

        if ((http.get('HTTP_IF_NONE_MATCH', '') == '"%s"' % mtime) or
             (http.get('HTTP_IF_NONE_MATCH', '') == '%s' % mtime) or
             (modified_since and calendar.timegm(time.strptime(modified_since,'%a, %d %b %Y %H:%M:%S GMT' )) >= int(mtime))):

            renderer.add_header('Status', '304 Not Modified')
            renderer.add_header('ETag', '"%s"' % mtime)
            renderer.add_header('Last-Modified', '%s' % last_modified)

            # whack the content here so that we don't then go render it
            renderer.set_content(None)

            renderer.render()

            # Log request as "We have it!"
            tools.run_callback("logrequest",
                               {'filename': config.get('logfile', ''),
                                'return_code': '304',
                                'request': request})

            return

        renderer.add_header('ETag', '"%s"' % mtime)
        renderer.add_header('Last-Modified', '%s' % last_modified)

########NEW FILE########
__FILENAME__ = disqus
#######################################################################
# This file is part of Pyblosxom.
#
# Copyright (c) 2011 Blake Winton
# Copyright (c) 2011 Will Kahn-Greene
#
# Pyblosxom is distributed under the MIT license.  See the file
# LICENSE for distribution details.
#######################################################################

"""
Summary
=======

Plugin for adding Disqus comments.

It's not hard to do this by hand, but this plugin makes it so that comments
only show up when you're looking at a single blog entry.


Install
=======

This plugin comes with Pyblosxom.  To install, do the following:

1. In your ``config.py`` file, add ``Pyblosxom.plugins.disqus`` to the
   ``load_plugins`` variable.

2. Set ``disqus_shortname`` in your ``config.py`` file.  This comes from
   Disqus when you set up your account.

   For help, see http://docs.disqus.com/help/2/ .

3. Save the ``comment_form`` template into your html flavour.


comment_form template::

    <div id="disqus_thread"></div>
    <script type="text/javascript">
      var disqus_shortname = '$(escape(disqus_shortname))';
      var disqus_identifier = '$(escape(disqus_id))';
      var disqus_title = '$(escape(title))';
  
      /* * * DON'T EDIT BELOW THIS LINE * * */
      (function() {
        var dsq = document.createElement('script');
        dsq.type = 'text/javascript';
        dsq.async = true;
        dsq.src = 'http://' + disqus_shortname + '.disqus.com/embed.js';
        (document.getElementsByTagName('head')[0] ||
         document.getElementsByTagName('body')[0]).appendChild(dsq);
      })();
    </script>
    <noscript>Please enable JavaScript to view the
      <a href="http://disqus.com/?ref_noscript">comments powered by Disqus.</a>
    </noscript>
    <a href="http://disqus.com" class="dsq-brlink"
      >blog comments powered by <span class="logo-disqus">Disqus</span></a>
"""

__author__ = "Blake Winton"
__email__ = "willg at bluesock dot org"
__version__ = "2011-12-12"
__url__ = "http://pyblosxom.github.com/"
__description__ = "Lets me use Disqus for comments."
__category__ = "comments"
__license__ = "MIT"
__registrytags__ = "1.5, core"


import os
from Pyblosxom.tools import pwrap_error


def verify_installation(request):
    config = request.get_configuration()

    if not config.has_key('disqus_shortname'):
        pwrap_error(
            "missing required config property 'disqus_shortname' which"
            "is necessary to determine which disqus site to link to.")
        return False

    return True


def cb_story(args):
    renderer = args['renderer']
    entry = args['entry']
    template = args['template']
    request = args["request"]
    config = request.get_configuration()

    did = os.path.realpath(entry['filename'])
    did = did.replace(entry['datadir'], '')
    did = os.path.splitext(did)[0]
    entry['disqus_id'] = did
    entry['disqus_shortname'] = config.get(
        'disqus_shortname', 'missing disqus_shortname')

    # This uses the same logic as comments.py for determining when
    # to show the comments.
    if ((entry.has_key('absolute_path')
         and len(renderer.getContent()) == 1
         and 'comment_form' in renderer.flavour
         and not entry.has_key('nocomments'))):

        # entry.getId() contains the path.
        output = []
        renderer.output_template(output, entry, 'comment_form')
        args['template'] = template + "".join(output)
    return args

########NEW FILE########
__FILENAME__ = entrytitle
#######################################################################
# This file is part of Pyblosxom.
#
# Copyright (C) 2010, 2011 by the Pyblosxom team.  See AUTHORS.
#
# Pyblosxom is distributed under the MIT license.  See the file
# LICENSE for distribution details.
#######################################################################

"""
Summary
=======

If Pyblosxom is rendering a single entry (i.e. entry_list has 1 item in it),
then this populates the ``entry_title`` variable for the header template.


Install
=======

This plugin comes with Pyblosxom.  To install, do the following:

1. Add ``Pyblosxom.plugins.entrytitle`` to the ``load_plugins`` list
   of your ``config.py`` file.

2. Configure as documented below.


Configuration
=============

To use, add the ``entry_title`` variable to your header template in
the ``<title>`` area.

Example::

    <title>$(blog_title)$(entry_title)</title>

The default ``$(entry_title)`` starts with a ``::`` and ends with the
title of the entry.  For example::

    :: Guess what happened today

You can set the entry title template in the configuration properties
with the ``entry_title_template`` variable::

    config["entry_title_template"] = ":: %(title)s"

.. Note::

   ``%(title)s`` is a Python string formatter that gets filled in with
   the entry title.
"""

__author__ = "Will Kahn-Greene"
__email__ = "willg at bluesock dot org"
__version__ = "2011-10-22"
__url__ = "http://pyblosxom.github.com/"
__description__ = "Puts entry title in page title."
__category__ = "date"
__license__ = "MIT"
__registrytags__ = "1.4, 1.5, core"


def verify_installation(request):
    # This needs no verification.
    return True


def cb_head(args):
    req = args["request"]
    entry = args["entry"]

    data = req.get_data()
    entry_list = data.get("entry_list", [])
    if len(entry_list) == 1:
        config = req.get_configuration()
        tmpl = config.get("entry_title_template", ":: %(title)s")
        entry["entry_title"] = (tmpl %
            {"title": entry_list[0].get("title", "No title")})

    return args

########NEW FILE########
__FILENAME__ = firstdaydiv
#######################################################################
# This file is part of Pyblosxom.
#
# Copyright (c) 2004, 2005 Blake Winton
# Copyright (c) 2010, 2011 Will Kahn-Greene
#
# Pyblosxom is distributed under the MIT license.  See the file
# LICENSE for distribution details.
#######################################################################

"""
Summary
=======

Adds a token which allows you to differentiate between the first day
of entries in a series of entries to be displayed from the other days.


Install
=======

This plugin comes with Pyblosxom.  To install, do the following:

1. In your ``config.py`` file, add ``Pyblosxom.plugins.firstdaydiv``
   to the ``load_plugins`` list.

2. (optional) Set the ``firstDayDiv`` config variable.  This defaults
   to ``blosxomFirstDayDiv``.

   Example::

      py['firstDayDiv'] = 'blosxomFirstDayDiv'


Usage
=====

This denotes the first day with the css class set in the
``firstDayDiv`` config variable.  This is available in the
``$(dayDivClass)`` template variable.  You probably want to put this
in your ``date_head`` template in a ``<div...>`` tag.

For example, in your ``date_head``, you could have::

   <div class="$dayDivClass">
   <span class="blosxomDate">$date</span>

and in your ``date_foot``, you'd want to close that ``<div>`` off::

   </div>

Feel free to use this in other ways.
"""

__author__ = "Blake Winton"
__email__ = "bwinton@latte.ca"
__version__ = "2011-10-22"
__url__ = "http://pyblosxom.github.com/"
__description__ = ("Adds a token which tells us whether "
                   "we're the first day being displayed or not.")
__category__ = "date"
__license__ = "MIT"
__registrytags__ = "1.4, 1.5, core"


class PyFirstDate:
    """
    This class stores the state needed to determine whether we're
    supposed to return the first-day-div class or the
    not-the-first-day-div class.

    """
    def __init__(self, request):
        config = request.get_configuration()
        self._day_div = config.get("firstDayDiv", "blosxomFirstDayDiv")
        self._count = 0

    def __str__(self):
        if self._count == 0:
            self._count = 1
        else:
            self._day_div = "blosxomDayDiv"
        return self._day_div


def cb_prepare(args):
    """
    Populate the ``Pyblosxom.pyblosxom.Request`` with an instance of
    the ``PyFirstDate`` class in the ``dayDivClass`` key.

    """
    request = args["request"]

    data = request.get_data()
    data["dayDivClass"] = PyFirstDate(request)

########NEW FILE########
__FILENAME__ = flavourfiles
#######################################################################
# This file is part of Pyblosxom.
#
# Copyright (c) 2010, 2011 Will Kahn-Greene
#
# Pyblosxom is distributed under the MIT license.  See the file
# LICENSE for distribution details.
#######################################################################

"""
Summary
=======

This plugin allows flavour templates to use file urls that will
resolve to files in the flavour directory.  Those files will then get
served by Pyblosxom.

This solves the problem that flavour packs are currently difficult to
package, install, and maintain because static files (images, css, js,
...) have to get put somewhere else and served by the web server and
this is difficult to walk a user through.

It handles urls that start with ``flavourfiles/``, then the flavour
name, then the path to the file.

For example::

    http://example.com/blog/flavourfiles/html/style.css


.. Note::

   This plugin is very beta!  It's missing important functionality,
   probably has bugs, and hasn't been well tested!


Install
=======

This plugin comes with Pyblosxom.  To install, do the following:

1. Add ``Pyblosxom.plugins.flavourfiles`` to the ``load_plugins`` list
   of your ``config.py`` file.

2. In templates you want to use flavourfiles, use urls like this::

       $(base_url)/flavourfiles/$(flavour)/path-to-file

   For example::

       <img src="$(base_url)/flavourfiles/$(flavour)/header_image.jpg">

The ``$(base_url)`` will get filled in with the correct url root.

The ``$(flavour)`` will get filled in with the name of the url.  This
allows users to change the flavour name without having to update all
the templates.

"""

__author__ = "Will Kahn-Greene"
__email__ = "willg at bluesock dot org"
__version__ = "2011-10-22"
__url__ = "http://pyblosxom.github.com/"
__description__ = "Serves static files related to flavours (css, js, ...)"
__license__ = "MIT License"
__registrytags__ = "1.5, core, experimental"

import os
import mimetypes
import sys

from Pyblosxom.renderers import base

TRIGGER = "/flavourfiles/"


class FileRenderer(base.RendererBase):
    def set_filepath(self, filepath):
        self.filepath = filepath

    def render(self, header=True):
        if not os.path.exists(self.filepath):
            self.render_404()
            self.rendered = 1
            return

        # FIXME - handle e-tag/etc conditional stuff here

        try:
            fp = open(self.filepath, "r")
        except OSError:
            # FIXME - this could be a variety of issues, but is
            # probably a permission denied error.  should catch the
            # error message and send it to the 403 page.
            self.render_403()
            self.rendered = 1
            return

        # mimetype
        mimetype = mimetypes.guess_type(self.filepath)
        if mimetype:
            mimetype = mimetype[0]
        if mimetype is None:
            mimetype = "application/octet-stream"
        self.add_header('Content-type', mimetype)

        # content length
        length = os.stat(self.filepath)[6]
        self.add_header('Content-Length', str(length))

        if header:
            self.show_headers()

        self.write(fp.read())
        fp.close()
        self.rendered = 1

    def render_403(self):
        resp = self._request.getResponse()
        resp.set_status("403 Forbidden")

    def render_404(self):
        resp = self._request.getResponse()
        resp.set_status("404 Not Found")


def cb_handle(args):
    """This is the flavour file handler.

    This handles serving static files related to flavours.  It handles
    paths like /flavourfiles/<flavour>/<path-to-file>.

    It calls the prepare callback to do any additional preparation
    before rendering the entries.

    Then it tells the renderer to render the entries.

    :param request: the request object.
    """
    request = args["request"]

    path_info = request.get_http()["PATH_INFO"]
    if not path_info.startswith(TRIGGER):
        return

    config = request.get_configuration()
    data = request.get_data()

    # get the renderer object
    rend = FileRenderer(request, config.get("stdoutput", sys.stdout))

    data['renderer'] = rend

    filepath = path_info.replace(TRIGGER, "")
    while filepath.startswith(("/", os.sep)):
        filepath = filepath[1:]

    if not filepath:
        rend.render_404()
        return

    filepath = filepath.split("/")
    flavour = filepath[0]
    filepath = "/".join(filepath[1:])

    root = config.get("flavourdir", config["datadir"])
    root = os.path.join(root, flavour + ".flav")
    filepath = os.path.join(root, filepath)

    filepath = os.path.normpath(filepath)
    if not filepath.startswith(root) or not os.path.exists(filepath):
        rend.render_404()
        return

    rend.set_filepath(filepath)
    rend.render()
    return 1

########NEW FILE########
__FILENAME__ = magicword
#######################################################################
# This file is part of Pyblosxom.
#
# Copyright (c) 2005 Nathaniel Gray
#
# Pyblosxom is distributed under the MIT license.  See the file
# LICENSE for distribution details.
#######################################################################


"""
Summary
=======

This is about the simplest anti-comment-spam measure you can imagine,
but it's probably effective enough for all but the most popular blogs.
Here's how it works.  You pick a question and put a field on your
comment for for the answer to the question.  If the user answers it
correctly, his comment is accepted.  Otherwise it's rejected.  Here's
how it works:


Install
=======

Requires the ``comments`` plugin.

This plugin comes with Pyblosxom.  To install, do the following:

1. Add ``Pyblosxom.plugins.magicword`` to the ``load_plugins`` list in
   your ``config.py`` file.

2. Configure as documented below.


Configure
=========

Here's an example of what to put in config.py::

    py['mw_question'] = "What is the first word in this sentence?"
    py['mw_answer'] = "what"

Note that ``mw_answer`` must be lowercase and without leading or
trailing whitespace, even if you expect the user to enter capital
letters.  Their input will be lowercased and stripped before it is
compared to ``mw_answer``.

Here's what you put in your ``comment-form`` file::

    The Magic Word:<br />
    <i>$(mw_question)</i><br />
    <input maxlenth="32" name="magicword" size="50" type="text" /><br />

It's important that the name of the input field is exactly "magicword".


Security note
=============

In order for this to be secure(ish) you need to protect your
``config.py`` file.  This is a good idea anyway!

If your ``config.py`` file is in your web directory, protect it from
being seen by creating or modifying a ``.htaccess`` file in the
directory where ``config.py`` lives with the following contents::

    <Files config.py>
    Order allow,deny
    deny from all
    </Files>

This will prevent people from being able to view ``config.py`` by
browsing to it.

"""

__author__ = "Nathaniel Gray"
__email__ = "n8gray /at/ caltech /dot/ edu"
__version__ = "2011-10-28"
__url__ = "http://pyblosxom.github.com/"
__description__ = "Magic word method for reducing comment spam"
__category__ = "comments"
__license__ = "MIT"
__registrytags__ = "1.4, 1.5, core"


from Pyblosxom.tools import pwrap_error


def verify_installation(request):
    config = request.get_configuration()

    status = True
    if not 'mw_question' in config:
        pwrap_error("Missing required property: mw_question")
        status = False

    if not 'mw_answer' in config:
        pwrap_error("Missing required property: mw_answer")
        return False

    a = config["mw_answer"]
    if a != a.strip().lower():
        pwrap_error("mw_answer must be lowercase, without leading "
                    "or trailing whitespace")
        return False

    return status


def cb_comment_reject(args):
    """
    Verifies that the commenter answered with the correct magic word.

    @param args: a dict containing: pyblosxom request, comment dict
    @type config: C{dict}
    @return: True if the comment should be rejected, False otherwise
    @rtype: C{bool}
    """
    request = args['request']
    form = request.get_form()
    config = request.get_configuration()

    try:
        mw = form["magicword"].value.strip().lower()
        if mw == config["mw_answer"]:
            return False
    except KeyError:
        pass
    return True

########NEW FILE########
__FILENAME__ = markdown_parser
#######################################################################
# Copyright (C) 2005, 2011 Benjamin Mako Hill
# Copyright (c) 2009, 2010, seanh
# Copyright (c) 2011 Blake Winton
# Copyright (c) 2011 Will Kahn-Greene
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at
# your option) any later version.
#######################################################################

"""
Summary
=======

A Markdown entry formatter for Pyblosxom.


Install
=======

Requires python-markdown to be installed.  See
http://www.freewisdom.org/projects/python-markdown/ for details.

1. Add ``Pyblosxom.plugins.markdown_parser`` to the ``load_plugins``
   list in your ``config.py`` file


Usage
=====

Write entries using Markdown markup.  Entry filenames can end in
``.markdown``, ``.md``, and ``.mkd``.

You can also configure this as your default preformatter for ``.txt``
files by configuring it in your config file as follows::

   py['parser'] = 'markdown'

Additionally, you can do this on an entry-by-entry basis by adding a
``#parser markdown`` line in the metadata section.  For example::

   My Little Blog Entry
   #parser markdown
   My main story...

"""

__author__ = (
    "Benjamin Mako Hill <mako@atdot.cc>, seanh <snhmnd@gmail.com>, "
    "Blake Winton <bwinton@latte.ca>")
__email__ = ""
__version__ = "2011-11-02"
__url__ = "http://pyblosxom.github.com/"
__description__ = "Markdown entry parser"
__category__ = "text"
__license__ = "GPLv3 or later"
__registrytags__ = "1.5, core"

PREFORMATTER_ID = "markdown"
FILENAME_EXTENSIONS = ("markdown", "md", "mkd")

import markdown
from Pyblosxom import tools

md = markdown.Markdown(output_format="html4",
                       extensions=["footnotes", "codehilite"])


def verify_installation(args):
    # no configuration needed
    return 1


def cb_entryparser(args):
    for ext in FILENAME_EXTENSIONS:
        args[ext] = readfile
    return args


def cb_preformat(args):
    if args.get("parser", None) == PREFORMATTER_ID:
        return parse("".join(args["story"]), args["request"])


def parse(story, request):
    body = md.convert(story.decode("utf-8")).encode("utf-8")
    md.reset()
    return body


def readfile(filename, request):
    logger = tools.get_logger()
    logger.info("Calling readfile for %s", filename)
    entry_data = {}
    lines = open(filename).readlines()

    if len(lines) == 0:
        return {"title": "", "body": ""}

    title = lines.pop(0).strip()

    # absorb meta data
    while lines and lines[0].startswith("#"):
        meta = lines.pop(0)
        # remove the hash
        meta = meta[1:].strip()
        meta = meta.split(" ", 1)
        # if there's no value, we append a 1
        if len(meta) == 1:
            meta.append("1")
        entry_data[meta[0].strip()] = meta[1].strip()

    body = parse("".join(lines), request)
    entry_data["title"] = title
    entry_data["body"] = body

    # Call the postformat callbacks
    tools.run_callback("postformat", {"request": request,
                                      "entry_data": entry_data})
    logger.info("Returning %r", entry_data)
    return entry_data

########NEW FILE########
__FILENAME__ = no_old_comments
#######################################################################
# Copyright (c) 2006 Blake Winton
#
# Released into the Public Domain.
#######################################################################

"""
Summary
=======

This plugin implements the ``comment_reject`` callback of the comments
plugin.

If someone tries to comment on an entry that's older than 28 days, the
comment is rejected.


Install
=======

Requires the ``comments`` plugin.

This plugin comes with Pyblosxom.  To install, do the following:

1. Add ``Pyblosxom.plugins.no_old_comments`` to the ``load_plugins``
   list in your ``config.py`` file.


Revisions
=========

1.0 - August 5th 2006: First released.
"""

__author__ = "Blake Winton"
__email__ = "bwinton+blog@latte.ca"
__version__ = "2011-10-28"
__url__ = "http://pyblosxom.github.com/"
__description__ = "Prevent comments on entries older than a month."
__category__ = "comments"
__license__ = "Public Domain"
__registrytags__ = "1.4, 1.5, core"


import time
from Pyblosxom import tools


def verify_installation(request):
    return True


def cb_comment_reject(args):
    req = args["request"]
    comment = args["comment"]
    blog_config = req.get_configuration()

    max_age = blog_config.get('no_old_comments_max_age', 2419200)

    data = req.get_data()
    entry = data['entry_list'][0]

    logger = tools.get_logger()

    logger.debug('%s -> %s', entry['mtime'], comment)

    if (time.time() - entry['mtime']) >= max_age:
        logger.info('Entry too old, comment not posted!')
        return 1

    logger.info('Entry ok, comment posted!')
    return 0

########NEW FILE########
__FILENAME__ = pages
#######################################################################
# This file is part of Pyblosxom.
#
# Copyright (c) 2002-2011 Will Kahn-Greene
#
# Pyblosxom is distributed under the MIT license.  See the file
# LICENSE for distribution details.
#######################################################################

"""
Summary
=======

Blogs don't always consist solely of blog entries.  Sometimes you want
to add other content to your blog that's not a blog entry.  For
example, an "about this blog" page or a page covering a list of your
development projects.

This plugin allows you to have pages served by Pyblosxom that aren't
blog entries.

Additionally, this plugin allows you to have a non-blog-entry front
page.  This makes it easier to use Pyblosxom to run your entire
website.


Install
=======

This plugin comes with Pyblosxom.  To install, do the following:

1. add ``Pyblosxom.plugins.pages`` to the ``load_plugins`` list in
   your ``config.py`` file.

2. configure the plugin using the configuration variables below


``pagesdir``

    This is the directory that holds the pages files.

    For example, if you wanted your pages in
    ``/home/foo/blog/pages/``, then you would set it to::

        py["pagesdir"] = "/home/foo/blog/pages/"

    If you have ``blogdir`` defined in your ``config.py`` file which
    holds your ``datadir`` and ``flavourdir`` directories, then you
    could set it to::

        py["pagesdir"] = os.path.join(blogdir, "pages")


``pages_trigger`` (optional)

    Defaults to ``pages``.

    This is the url trigger that causes the pages plugin to look for
    pages.

        py["pages_trigger"] = "pages"


``pages_frontpage`` (optional)

    Defaults to False.

    If set to True, then pages will show the ``frontpage`` page for
    the front page.

    This requires you to have a ``frontpage`` file in your pages
    directory.  The extension for this file works the same way as blog
    entries.  So if your blog entries end in ``.txt``, then you would
    need a ``frontpage.txt`` file.

    Example::

        py["pages_frontpage"] = True


Usage
=====

Pages looks for urls that start with the trigger ``pages_trigger``
value as set in your ``config.py`` file.  For example, if your
``pages_trigger`` was ``pages``, then it would look for urls like
this::

    /pages/blah
    /pages/blah.html

and pulls up the file ``blah.txt`` [1]_ which is located in the path
specified in the config file as ``pagesdir``.

If the file is not there, it kicks up a 404.

.. [1] The file ending (the ``.txt`` part) can be any file ending
   that's valid for entries on your blog.  For example, if you have
   the textile entryparser installed, then ``.txtl`` is also a valid
   file ending.


Template
========

pages formats the page using the ``pages`` template.  So you need a
``pages`` template in the flavours that you want these pages to be
rendered in.  I copy my ``story`` template and remove some bits.

For example, if you're using the html flavour and that is stored in
``/home/foo/blog/flavours/html.flav/``, then you could copy the
``story`` file in that directory to ``pages`` and that would become
your ``pages`` template.


Python code blocks
==================

pages handles evaluating python code blocks.  Enclose python code in
``<%`` and ``%>``.  The assumption is that only you can edit your
pages files, so there are no restrictions (security or otherwise).

For example::

   <%
   print "testing"
   %>

   <%
   x = { "apple": 5, "banana": 6, "pear": 4 }
   for mem in x.keys():
      print "<li>%s - %s</li>" % (mem, x[mem])
   %>

The request object is available in python code blocks.  Reference it
by ``request``.  Example::

   <%
   config = request.get_configuration()
   print "your datadir is: %s" % config["datadir"]
   %>

"""

__author__ = "Will Kahn-Greene"
__email__ = "willg at bluesock dot org"
__version__ = "2011-10-22"
__url__ = "http://pyblosxom.github.com/"
__description__ = (
    "Allows you to include non-blog-entry files in your site and have a "
    "non-blog-entry front page.")
__category__ = "content"
__license__ = "MIT"
__registrytags__ = "1.4, 1.5, core"


import os
import StringIO
import sys
import os.path
from Pyblosxom.entries.fileentry import FileEntry
from Pyblosxom import tools
from Pyblosxom.tools import pwrap_error


TRIGGER = "pages"
INIT_KEY = "pages_pages_file_initiated"


def verify_installation(req):
    config = req.get_configuration()

    retval = True

    if not 'pagesdir' in config:
        pwrap_error("'pagesdir' property is not set in the config file.")
        retval = False
    elif not os.path.isdir(config["pagesdir"]):
        pwrap_error(
            "'pagesdir' directory does not exist. %s" % config["pagesdir"])
        retval = False

    return retval


def cb_date_head(args):
    req = args["request"]
    data = req.get_data()
    if INIT_KEY in data:
        args["template"] = ""
    return args


def cb_date_foot(args):
    return cb_date_head(args)


def eval_python_blocks(req, body):
    localsdict = {"request": req}
    globalsdict = {}

    old_stdout = sys.stdout
    old_stderr = sys.stderr

    try:
        start = 0
        while body.find("<%", start) != -1:
            start = body.find("<%")
            end = body.find("%>", start)

            if start != -1 and end != -1:
                codeblock = body[start + 2:end].lstrip()

                sys.stdout = StringIO.StringIO()
                sys.stderr = StringIO.StringIO()

                try:
                    exec codeblock in localsdict, globalsdict
                except Exception, e:
                    print "ERROR in processing: %s" % e

                output = sys.stdout.getvalue() + sys.stderr.getvalue()
                body = body[:start] + output + body[end + 2:]

    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr

    return body


def is_frontpage(pyhttp, config):
    if not config.get("pages_frontpage"):
        return False
    pathinfo = pyhttp.get("PATH_INFO", "")
    if pathinfo == "/":
        return True
    path, ext = os.path.splitext(pathinfo)
    if path == "/index" and not ext in [".rss20", ".atom", ".rss"]:
        return True
    return False


def is_trigger(pyhttp, config):
    trigger = config.get("pages_trigger", TRIGGER)
    if not trigger.startswith("/"):
        trigger = "/" + trigger

    return pyhttp["PATH_INFO"].startswith(trigger)


def cb_filelist(args):
    req = args["request"]

    pyhttp = req.get_http()
    data = req.get_data()
    config = req.get_configuration()
    page_name = None

    if not (is_trigger(pyhttp, config) or is_frontpage(pyhttp, config)):
        return

    data[INIT_KEY] = 1
    datadir = config["datadir"]
    data['root_datadir'] = config['datadir']
    pagesdir = config["pagesdir"]

    pagesdir = pagesdir.replace("/", os.sep)
    if not pagesdir[-1] == os.sep:
        pagesdir = pagesdir + os.sep

    pathinfo = pyhttp.get("PATH_INFO", "")
    path, ext = os.path.splitext(pathinfo)
    if pathinfo == "/" or path == "/index":
        page_name = "frontpage"
    else:
        page_name = pyhttp["PATH_INFO"][len("/" + TRIGGER) + 1:]

    if not page_name:
        return

    # FIXME - need to do a better job of sanitizing
    page_name = page_name.replace(os.sep, "/")

    if not page_name:
        return

    if page_name[-1] == os.sep:
        page_name = page_name[:-1]
    if page_name.find("/") > 0:
        page_name = page_name[page_name.rfind("/"):]

    # if the page has a flavour, we use that.  otherwise
    # we default to the default flavour.
    page_name, flavour = os.path.splitext(page_name)
    if flavour:
        data["flavour"] = flavour[1:]

    ext = tools.what_ext(data["extensions"].keys(), pagesdir + page_name)

    if not ext:
        return []

    data['root_datadir'] = page_name + '.' + ext
    data['bl_type'] = 'file'
    filename = pagesdir + page_name + "." + ext

    if not os.path.isfile(filename):
        return []

    fe = FileEntry(req, filename, pagesdir)
    # now we evaluate python code blocks
    body = fe.get_data()
    body = eval_python_blocks(req, body)
    body = ("<!-- PAGES PAGE START -->\n\n" +
            body +
            "<!-- PAGES PAGE END -->\n")
    fe.set_data(body)

    fe["absolute_path"] = TRIGGER
    fe["fn"] = page_name
    fe["file_path"] = TRIGGER + "/" + page_name
    fe["template_name"] = "pages"

    data['blog_title_with_path'] = (
        config.get("blog_title", "") + " : " + fe.get("title", ""))

    # set the datadir back
    config["datadir"] = datadir

    return [fe]

########NEW FILE########
__FILENAME__ = paginate
#######################################################################
# This file is part of Pyblosxom.
#
# Copyright (c) 2004-2012 Will Kahn-Greene
#
# Pyblosxom is distributed under the MIT license.  See the file
# LICENSE for distribution details.
#######################################################################

"""
Summary
=======

Plugin for paging long index pages.

Pyblosxom uses the ``num_entries`` configuration variable to prevent
more than ``num_entries`` being rendered by cutting the list down to
``num_entries`` entries.  So if your ``num_entries`` is set to 20, you
will only see the first 20 entries rendered.

The paginate plugin overrides this functionality and allows for
paging.


Install
=======

This plugin comes with Pyblosxom.  To install, do the following:

1. Add ``Pyblosxom.plugins.paginate`` to your ``load_plugins`` list
   variable in your ``config.py`` file.

   Make sure it's the first plugin in the ``load_plugins`` list so
   that it has a chance to operate on the entry list before other
   plugins.

2. add the ``$(page_navigation)`` variable to your head or foot (or
   both) templates.  this is where the page navigation HTML will
   appear.


Here are some additional configuration variables to adjust the
behavior::

``paginate_count_from``

   Defaults to 0.

   This is the number to start counting from.  Some folks like their
   pages to start at 0 and others like it to start at 1.  This enables
   you to set it as you like.

   Example::

      py["paginate_count_from"] = 1


``paginate_previous_text``

   Defaults to "&lt;&lt;".

   This is the text for the "previous page" link.


``paginate_next_text``

   Defaults to "&gt;&gt;".

   This is the text for the "next page" link.


``paginate_linkstyle``

   Defaults to 1.

   This allows you to change the link style of the paging.

   Style 0::

       [1] 2 3 4 5 6 7 8 9 ... >>

   Style 1::

      Page 1 of 4 >>

   If you want a style different than that, you'll have to copy the
   plugin and implement your own style.


Note about static rendering
===========================

This plugin works fine with static rendering, but the urls look
different. Instead of adding a ``page=4`` kind of thing to the
querystring, this adds it to the url.

For example, say your front page was ``/index.html`` and you had 5
pages of entries. Then the urls would look like this::

    /index.html           first page
    /index_page2.html     second page
    /index_page3.html     third page
    ...

"""

__author__ = "Will Kahn-Greene"
__email__ = "willg at bluesock dot org"
__version__ = "2011-10-22"
__url__ = "http://pyblosxom.github.com/"
__description__ = (
    "Allows navigation by page for indexes that have too many entries.")
__category__ = "display"
__license__ = "MIT"
__registrytags__ = "1.5, core"


import os

from Pyblosxom.tools import pwrap_error, render_url_statically


def verify_installation(request):
    config = request.get_configuration()
    if config.get("num_entries", 0) == 0:
        pwrap_error(
            "Missing config property 'num_entries'.  paginate won't do "
            "anything without num_entries set.  Either set num_entries "
            "to a positive integer, or disable the paginate plugin."
            "See the documentation at the top of the paginate plugin "
            "code file for more details.")
        return False
    return True


class PageDisplay:
    def __init__(self, url_template, current_page, max_pages, count_from,
                 previous_text, next_text, linkstyle):
        self._url_template = url_template
        self._current_page = current_page
        self._max_pages = max_pages
        self._count_from = count_from
        self._previous = previous_text
        self._next = next_text
        self._linkstyle = linkstyle

    def __str__(self):
        output = []
        # prev
        if self._current_page != self._count_from:
            prev_url = self._url_template % (self._current_page - 1)
            output.append('<a href="%s">%s</a>&nbsp;' %
                          (prev_url, self._previous))

        # pages
        if self._linkstyle == 0:
            for i in range(self._count_from, self._max_pages):
                if i == self._current_page:
                    output.append('[%d]' % i)
                else:
                    page_url = self._url_template % i
                    output.append('<a href="%s">%d</a>' % (page_url, i))
        elif self._linkstyle == 1:
            output.append(' Page %s of %s ' %
                          (self._current_page, self._max_pages - 1))

        # next
        if self._current_page < self._max_pages - 1:
            next_url = self._url_template % (self._current_page + 1)
            output.append('&nbsp;<a href="%s">%s</a>' %
                          (next_url, self._next))

        return " ".join(output)


def page(request, num_entries, entry_list):
    http = request.get_http()
    config = request.get_configuration()
    data = request.get_data()

    previous_text = config.get("paginate_previous_text", "&lt;&lt;")
    next_text = config.get("paginate_next_text", "&gt;&gt;")

    link_style = config.get("paginate_linkstyle", 1)
    if link_style > 1:
        link_style = 1

    entries_per_page = num_entries
    count_from = config.get("paginate_count_from", 0)

    if isinstance(entry_list, list) and 0 < entries_per_page < len(entry_list):

        page = count_from
        url = http.get("REQUEST_URI", http.get("HTTP_REQUEST_URI", ""))
        url_template = url
        if not data.get("STATIC"):
            form = request.get_form()

            if form:
                try:
                    page = int(form.getvalue("page"))
                except (TypeError, ValueError):
                    page = count_from

            # Restructure the querystring so that page= is at the end
            # where we can fill in the next/previous pages.
            if url_template.find("?") != -1:
                query = url_template[url_template.find("?") + 1:]
                url_template = url_template[:url_template.find("?")]

                query = query.split("&")
                query = [m for m in query if not m.startswith("page=")]
                if len(query) == 0:
                    url_template = url_template + "?" + "page=%d"
                else:
                    # Note: We're using &amp; here because it needs to
                    # be url_templateencoded.
                    url_template = (url_template + "?" + "&amp;".join(query) +
                                    "&amp;page=%d")
            else:
                url_template += "?page=%d"

        else:
            try:
                page = data["paginate_page"]
            except KeyError:
                page = count_from

            # The REQUEST_URI isn't the full url here--it's only the
            # path and so we need to add the base_url.
            base_url = config["base_url"].rstrip("/")
            url_template = base_url + url_template

            url_template = url_template.split("/")
            ret = url_template[-1].rsplit("_", 1)
            if len(ret) == 1:
                fn, ext = os.path.splitext(ret[0])
                pageno = "_page%d"
            else:
                fn, pageno = ret
                pageno, ext = os.path.splitext(pageno)
                pageno = "_page%d"
            url_template[-1] = fn + pageno + ext
            url_template = "/".join(url_template)

        begin = (page - count_from) * entries_per_page
        end = (page + 1 - count_from) * entries_per_page
        if end > len(entry_list):
            end = len(entry_list)

        max_pages = ((len(entry_list) - 1) / entries_per_page) + 1 + count_from

        data["entry_list"] = entry_list[begin:end]

        data["page_navigation"] = PageDisplay(
            url_template, page, max_pages, count_from, previous_text,
            next_text, link_style)

        # If we're static rendering and there wasn't a page specified
        # and this is one of the flavours to statically render, then
        # this is the first page and we need to render all the rest of
        # the pages, so we do that here.
        static_flavours = config.get("static_flavours", ["html"])
        if ((data.get("STATIC") and page == count_from
             and data.get("flavour") in static_flavours)):
            # Turn http://example.com/index.html into
            # http://example.com/index_page5.html for each page.
            url = url.split('/')
            fn = url[-1]
            fn, ext = os.path.splitext(fn)
            template = '/'.join(url[:-1]) + '/' + fn + '_page%d'
            if ext:
                template = template + ext

            for i in range(count_from + 1, max_pages):
                print "   rendering page %s ..." % (template % i)
                render_url_statically(dict(config), template % i, '')


def cb_truncatelist(args):
    request = args["request"]
    entry_list = args["entry_list"]

    page(request, request.config.get("num_entries", 10), entry_list)
    return request.data.get("entry_list", entry_list)


def cb_pathinfo(args):
    request = args["request"]
    data = request.get_data()

    # This only kicks in during static rendering.
    if not data.get("STATIC"):
        return

    http = request.get_http()
    pathinfo = http.get("PATH_INFO", "").split("/")

    # Handle the http://example.com/index_page5.html case. If we see
    # that, put the page information in the data dict under
    # "paginate_page" and "fix" the pathinfo.
    if pathinfo and "_page" in pathinfo[-1]:
        fn, pageno = pathinfo[-1].rsplit("_")
        pageno, ext = os.path.splitext(pageno)
        try:
            pageno = int(pageno[4:])
        except (ValueError, TypeError):
            # If it's not a valid page number, then we shouldn't be
            # doing anything here.
            return

        pathinfo[-1] = fn
        pathinfo = "/".join(pathinfo)
        if ext:
            pathinfo += ext

        http["PATH_INFO"] = pathinfo
        data["paginate_page"] = pageno

########NEW FILE########
__FILENAME__ = pyarchives
#######################################################################
# This file is part of Pyblosxom.
#
# Copyright (C) 2004-2011 by the Pyblosxom team.  See AUTHORS.
#
# Pyblosxom is distributed under the MIT license.  See the file
# LICENSE for distribution details.
#######################################################################

"""
Summary
=======

Walks through your blog root figuring out all the available monthly
archives in your blogs.  It generates html with this information and
stores it in the ``$(archivelinks)`` variable which you can use in
your head and foot templates.


Install
=======

This plugin comes with Pyblosxom.  To install, do the following:

1. Add ``Pyblosxom.plugins.pyarchives`` to the ``load_plugins`` list
   in your ``config.py`` file.

2. Configure using the following configuration variables.

``archive_template``

    Let's you change the format of the output for an archive link.

    For example::

        py['archive_template'] = ('<li><a href="%(base_url)s/%(Y)s/%(b)s">'
                                  '%(m)s/%(y)s</a></li>')

    This displays the archives as list items, with a month number,
    then a slash, then the year number.

    The formatting variables available in the ``archive_template``
    are::

        b         'Jun'
        m         '6'
        Y         '1978'
        y         '78'

    These work the same as ``time.strftime`` in python.

    Additionally, you can use variables from config and data.

    .. Note::

       The syntax used here is the Python string formatting
       syntax---not the Pyblosxom template rendering syntax!


Usage
=====

Add ``$(archivelinks)`` to your head and/or foot templates.

"""

__author__ = "Wari Wahab"
__email__ = "wari at wari dot per dot sg"
__version__ = "2011-10-22"
__url__ = "http://pyblosxom.github.com/"
__description__ = "Builds month/year-based archives listing."
__category__ = "archives"
__license__ = "MIT"
__registrytags__ = "1.4, 1.5, core"

from Pyblosxom import tools
from Pyblosxom.memcache import memcache_decorator
from Pyblosxom.tools import pwrap
import time


def verify_installation(request):
    config = request.get_configuration()
    if not "archive_template" in config:
        pwrap(
            "missing optional config property 'archive_template' which "
            "allows you to specify how the archive links are created.  "
            "refer to pyarchive plugin documentation for more details.")
    return True


class PyblArchives:
    def __init__(self, request):
        self._request = request
        self._archives = None

    @memcache_decorator('pyarchives', True)
    def __str__(self):
        if self._archives == None:
            self.gen_linear_archive()
        return self._archives

    def gen_linear_archive(self):
        config = self._request.get_configuration()
        data = self._request.get_data()
        root = config["datadir"]
        archives = {}
        archive_list = tools.walk(self._request, root)
        full_dict = {}
        full_dict.update(config)
        full_dict.update(data)

        template = config.get('archive_template',
                              '<a href="%(base_url)s/%(Y)s/%(b)s">%(Y)s-%(b)s</a><br />')
        for mem in archive_list:
            timetuple = tools.filestat(self._request, mem)
            time_dict = {}
            for x in ["B", "b", "m", "Y", "y"]:
                time_dict[x] = time.strftime("%" + x, timetuple)

            full_dict.update(time_dict)
            if not (time_dict['Y'] + time_dict['m']) in archives:
                archives[time_dict['Y'] + time_dict['m']] = (template % full_dict)

        arc_keys = archives.keys()
        arc_keys.sort()
        arc_keys.reverse()
        result = []
        for key in arc_keys:
            result.append(archives[key])
        self._archives = '\n'.join(result)


def cb_prepare(args):
    request = args["request"]
    data = request.get_data()
    data["archivelinks"] = PyblArchives(request)

########NEW FILE########
__FILENAME__ = pycalendar
#######################################################################
# This is placed in the Public Domain.
#######################################################################

"""
Summary
=======

Generates a calendar along the lines of this one (with month and day names in
the configured locale)::

    <   January 2003   >
    Mo Tu We Th Fr Sa Su
           1  2  3  4  5
     6  7  8  9 10 11 12
    13 14 15 16 17 18 19
    20 21 22 23 24 25 26
    27 28 29 30 31

It walks through all your entries and marks the dates that have entries
so you can click on the date and see entries for that date.


Install
=======

This plugin comes with Pyblosxom.  To install, do the following:

1. Add ``Pyblosxom.plugins.pycalendar`` to your ``load_plugins`` list in your
   ``config.py`` file.

2. Configure it as documented below.

3. Add the ``$(calendar)`` variable to your head and/or foot template.


Configuration
=============

You can set the start of the week using the ``calendar_firstweekday``
configuration setting, for example::

   py['calendar_firstweekday'] = 0

will make the week start on Monday (day '0'), instead of Sunday (day '6').

Pycalendar is locale-aware.  If you set the ``locale`` config property,
then month and day names will be displayed according to your locale.

It uses the following CSS classes:

* blosxomCalendar: for the calendar table
* blosxomCalendarHead: for the month year header (January 2003)
* blosxomCalendarWeekHeader: for the week header (Su, Mo, Tu, ...)
* blosxomCalendarEmpty: for filler days
* blosxomCalendarCell: for calendar days that aren't today
* blosxomCalendarBlogged: for calendar days that aren't today that
  have entries
* blosxomCalendarSpecificDay: for the specific day we're looking at
  (if we're looking at a specific day)
* blosxomCalendarToday: for today's calendar day

"""

__author__ = "Will Kahn-Greene"
__email__ = "willg at bluesock dot org"
__version__ = "2011-10-23"
__url__ = "http://pyblosxom.github.com/"
__description__ = "Displays a calendar on your blog."
__category__ = "date"
__license__ = "Public domain"
__registrytags__ = "1.4, 1.5, core"


import time
import calendar
import string

from Pyblosxom import tools
from Pyblosxom.memcache import memcache_decorator


def verify_installation(request):
    # there's no configuration needed for this plugin.
    return True


class PyblCalendar:
    def __init__(self, request):
        self._request = request
        self._cal = None

        self._today = None
        self._view = None
        self._specificday = None

        self._entries = {}

    @memcache_decorator('pycalendar', True)
    def __str__(self):
        """
        Returns the on-demand generated string.
        """
        if self._cal == None:
            self.generate_calendar()

        return self._cal

    def generate_calendar(self):
        """
        Generates the calendar.  We'd like to walk the archives
        for things that happen in this month and mark the dates
        accordingly.  After doing that we pass it to a formatting
        method which turns the thing into HTML.
        """
        config = self._request.get_configuration()
        data = self._request.get_data()
        entry_list = data["entry_list"]

        root = config["datadir"]
        baseurl = config.get("base_url", "")

        self._today = time.localtime()

        if len(entry_list) == 0:
            # if there are no entries, we shouldn't even try to
            # do something fancy.
            self._cal = ""
            return

        view = list(entry_list[0]["timetuple"])

        # this comes in as '', 2001, 2002, 2003, ...  so we can convert it
        # without an issue
        temp = data.get("pi_yr")
        if not temp:
            view[0] = int(self._today[0])
        else:
            view[0] = int(temp)

        # the month is a bit harder since it can come in as "08", "", or
        # "Aug" (in the example of August).
        temp = data.get("pi_mo")
        if temp and temp.isdigit():
            view[1] = int(temp)
        elif temp and temp in tools.month2num:
            view[1] = int(tools.month2num[temp])
        else:
            view[1] = int(self._today[1])

        self._view = view = tuple(view)

        # if we're looking at a specific day, we figure out what it is
        if data.get("pi_yr") and data.get("pi_mo") and data.get("pi_da"):
            if data["pi_mo"].isdigit():
                mon = data["pi_mo"]
            else:
                mon = tools.month2num[data["pi_mo"]]

            self._specificday = (int(data.get("pi_yr", self._today[0])),
                                 int(mon),
                                 int(data.get("pi_da", self._today[2])))

        archive_list = tools.walk(self._request, root)

        yearmonth = {}

        for mem in archive_list:
            timetuple = tools.filestat(self._request, mem)

            # if we already have an entry for this date, we skip to the
            # next one because we've already done this processing
            day = str(timetuple[2]).rjust(2)
            if day in self._entries:
                continue

            # add an entry for yyyymm so we can figure out next/previous
            year = str(timetuple[0])
            dayzfill = string.zfill(timetuple[1], 2)
            yearmonth[year + dayzfill] = time.strftime("%b", timetuple)

            # if the entry isn't in the year/month we're looking at with
            # the calendar, then we skip to the next one
            if timetuple[0:2] != view[0:2]:
                continue

            # mark the entry because it's one we want to show
            if config.get("static_monthnumbers"):
                datepiece = time.strftime("%Y/%m/%d", timetuple)
            else:
                datepiece = time.strftime("%Y/%b/%d", timetuple)
            self._entries[day] = (baseurl + "/" + datepiece, day)

        # Set the first day of the week (Sunday by default)
        first = config.get('calendar_firstweekday', 6)
        calendar.setfirstweekday(first)

        # create the calendar
        cal = calendar.monthcalendar(view[0], view[1])

        # insert the days of the week
        cal.insert(0, calendar.weekheader(2).split())

        # figure out next and previous links by taking the dict of
        # yyyymm strings we created, turning it into a list, sorting
        # them, and then finding "today"'s entry.  then the one before
        # it (index-1) is prev, and the one after (index+1) is next.
        keys = yearmonth.keys()
        keys.sort()
        thismonth = time.strftime("%Y%m", view)

        # do some quick adjustment to make sure we didn't pick a
        # yearmonth that's outside the yearmonths of the entries we
        # know about.
        if thismonth in keys:
            index = keys.index(thismonth)
        elif len(keys) == 0 or keys[0] > thismonth:
            index = 0
        else:
            index = len(keys) - 1

        # build the prev link
        if index == 0 or len(keys) == 0:
            prev = None
        else:
            prev = ("%s/%s/%s" % (baseurl, keys[index - 1][:4],
                                  yearmonth[keys[index - 1]]),
                    "&lt;")

        # build the next link
        if index == len(yearmonth) - 1 or len(keys) == 0:
            next = None
        else:
            next = ("%s/%s/%s" % (baseurl, keys[index + 1][:4],
                                  yearmonth[keys[index + 1]]),
                    "&gt;")

        # insert the month name and next/previous links
        cal.insert(0, [prev, time.strftime("%B %Y", view), next])

        self._cal = self.format_with_css(cal)

    def _fixlink(self, link):
        if link:
            return "<a href=\"%s\">%s</a>" % (link[0], link[1])
        else:
            return " "

    def _fixday(self, day):
        if day == 0:
            return "<td class=\"blosxomCalendarEmpty\">&nbsp;</td>"

        strday = str(day).rjust(2)
        if strday in self._entries:
            entry = self._entries[strday]
            link = "<a href=\"%s\">%s</a>" % (entry[0], entry[1])
        else:
            link = strday

        td_class_str = ""

        # if it's today
        if (self._view[0], self._view[1], day) == self._today[0:3]:
            td_class_str += "blosxomCalendarToday "

        if self._specificday:
        # if it's the day we're viewing
            if (self._view[0], self._view[1], day) == self._specificday:
                td_class_str += "blosxomCalendarSpecificDay "

        # if it's a day that's been blogged
        if strday in self._entries:
            td_class_str += "blosxomCalendarBlogged"

        if td_class_str != "":
            td_class_str = "<td class=\"" + td_class_str + "\">%s</td>" % link
        else:
            td_class_str = "<td class=\"blosxomCalendarCell\">%s</td>" % strday

        return td_class_str

    def _fixweek(self, item):
        return "<td class=\"blosxomCalendarWeekHeader\">%s</td>" % item

    def format_with_css(self, cal):
        """
        This formats the calendar using HTML table and CSS.  The output
        can be made to look prettier.
        """
        cal2 = ["<table class=\"blosxomCalendar\">"]
        cal2.append("<tr>")
        cal2.append("<td align=\"left\">" + self._fixlink(cal[0][0]) +
                    "</td>")
        cal2.append(
            '<td colspan="5" align="center" class="blosxomCalendarHead">' +
            cal[0][1] + '</td>')
        cal2.append("<td align=\"right\">" + self._fixlink(cal[0][2]) +
                    "</td>")
        cal2.append("</tr>")

        cal2.append("<tr>%s</tr>" %
                    "".join([self._fixweek(m) for m in cal[1]]))

        for mem in cal[2:]:
            mem = [self._fixday(m) for m in mem]
            cal2.append("<tr>" + "".join(mem) + "</tr>")

        cal2.append("</table>")

        return "\n".join(cal2)


def cb_prepare(args):
    request = args["request"]
    data = request.get_data()
    if data.get('entry_list', None):
        data["calendar"] = PyblCalendar(request)

########NEW FILE########
__FILENAME__ = pycategories
#######################################################################
# This file is part of Pyblosxom.
#
# Copyright (C) 2004-2011 by the Pyblosxom team.  See AUTHORS.
#
# Pyblosxom is distributed under the MIT license.  See the file
# LICENSE for distribution details.
#######################################################################

"""
Summary
=======

Walks through your blog root figuring out all the categories you have
and how many entries are in each category.  It generates html with
this information and stores it in the ``$(categorylinks)`` variable
which you can use in your head or foot templates.


Install
=======

This plugin comes with Pyblosxom.  To install, do the following:

1. Add ``Pyblosxom.plugins.pycategories`` to the ``load_plugins`` list
   in your ``config.py`` file.

2. Add ``$(categorylinks)`` to your head and/or foot templates.


Configuration
=============

You can format the output by setting ``category_begin``,
``category_item``, and ``category_end`` properties.

Categories exist in a hierarchy.  ``category_start`` starts the
category listing and is only used at the very beginning.  The
``category_begin`` property begins a new category group and the
``category_end`` property ends that category group.  The
``category_item`` property is the template for each category item.
Then after all the categories are printed, ``category_finish`` ends
the category listing.

For example, the following properties will use ``<ul>`` to open a
category, ``</ul>`` to close a category and ``<li>`` for each item::

    py["category_start"] = "<ul>"
    py["category_begin"] = "<ul>"
    py["category_item"] = (
        r'<li><a href="%(base_url)s/%(category_urlencoded)sindex">'
        r'%(category)s</a></li>')
    py["category_end"] = "</ul>"
    py["category_finish"] = "</ul>"


Another example, the following properties don't have a begin or an end
but instead use indentation for links and displays the number of
entries in that category::

    py["category_start"] = ""
    py["category_begin"] = ""
    py["category_item"] = (
        r'%(indent)s<a href="%(base_url)s/%(category_urlencoded)sindex">'
        r'%(category)s</a> (%(count)d)<br />')
    py["category_end"] = ""
    py["category_finish"] = ""

There are no variables available in the ``category_begin`` or
``category_end`` templates.

Available variables in the category_item template:

=======================  ==========================  ====================
variable                 example                     datatype
=======================  ==========================  ====================
base_url                 http://joe.com/blog/        string
fullcategory_urlencoded  'dev/pyblosxom/status/'     string
fullcategory             'dev/pyblosxom/status/'     string (urlencoded)
category                 'status/'                   string
category_urlencoded      'status/'                   string (urlencoed)
flavour                  'html'                      string
count                    70                          int
indent                   '&nbsp;&nbsp;&nbsp;&nbsp;'  string
=======================  ==========================  ====================
"""

__author__ = "Will Kahn-Greene"
__email__ = "willg at bluesock dot org"
__version__ = "$Id$"
__url__ = "http://pyblosxom.github.com/"
__description__ = "Builds a list of categories."
__category__ = "category"
__license__ = "MIT"
__registrytags__ = "1.4, 1.5, core"


from Pyblosxom import tools
from Pyblosxom.memcache import memcache_decorator
from Pyblosxom.tools import pwrap
import os


DEFAULT_START = r'<ul class="categorygroup">'
DEFAULT_BEGIN = r'<li><ul class="categorygroup">'
DEFAULT_ITEM = (
    r'<li><a href="%(base_url)s/%(fullcategory_urlencoded)sindex.%(flavour)s">'
    r'%(category)s</a> (%(count)d)</li>')
DEFAULT_END = "</ul></li>"
DEFAULT_FINISH = "</ul>"


def verify_installation(request):
    config = request.get_configuration()
    if not "category_item" in config:
        pwrap(
            "missing optional config property 'category_item' which allows "
            "you to specify how the category hierarchy is rendered.  see"
            "the documentation at the top of the pycategories plugin code "
            "file for more details.")
    return True


class PyblCategories:
    def __init__(self, request):
        self._request = request
        self._categories = None

    @memcache_decorator('pycategories', True)
    def __str__(self):
        if self._categories is None:
            self.gen_categories()
        return self._categories

    def gen_categories(self):
        config = self._request.get_configuration()
        root = config["datadir"]

        start_t = config.get("category_start", DEFAULT_START)
        begin_t = config.get("category_begin", DEFAULT_BEGIN)
        item_t = config.get("category_item", DEFAULT_ITEM)
        end_t = config.get("category_end", DEFAULT_END)
        finish_t = config.get("category_finish", DEFAULT_FINISH)

        self._baseurl = config.get("base_url", "")

        form = self._request.get_form()

        if form.has_key('flav'):
            flavour = form['flav'].value
        else:
            flavour = config.get('default_flavour', 'html')

        # build the list of all entries in the datadir
        elist = tools.walk(self._request, root)

        # peel off the root dir from the list of entries
        elist = [mem[len(root) + 1:] for mem in elist]

        # go through the list of entries and build a map that
        # maintains a count of how many entries are in each category
        elistmap = {}
        for mem in elist:
            mem = os.path.dirname(mem)
            elistmap[mem] = 1 + elistmap.get(mem, 0)
        self._elistmap = elistmap

        # go through the elistmap keys (which is the list of
        # categories) and for each piece in the key (i.e. the key
        # could be "dev/pyblosxom/releases" and the pieces would be
        # "dev", "pyblosxom", and "releases") we build keys for the
        # category list map (i.e. "dev", "dev/pyblosxom",
        # "dev/pyblosxom/releases")
        clistmap = {}
        for mem in elistmap.keys():
            mem = mem.split(os.sep)
            for index in range(len(mem) + 1):
                p = os.sep.join(mem[0:index])
                clistmap[p] = 0

        # then we take the category list from the clistmap and sort it
        # alphabetically
        clist = clistmap.keys()
        clist.sort()

        output = []
        indent = 0

        output.append(start_t)
        # then we generate each item in the list
        for item in clist:
            itemlist = item.split(os.sep)

            num = 0
            for key in self._elistmap.keys():
                if item == '' or key == item or key.startswith(item + os.sep):
                    num = num + self._elistmap[key]

            if not item:
                tab = ""
            else:
                tab = len(itemlist) * "&nbsp;&nbsp;"

            if itemlist != ['']:
                if indent > len(itemlist):
                    for i in range(indent - len(itemlist)):
                        output.append(end_t)

                elif indent < len(itemlist):
                    for i in range(len(itemlist) - indent):
                        output.append(begin_t)

            # now we build the dict with the values for substitution
            d = {"base_url": self._baseurl,
                 "fullcategory": item + "/",
                 "category": itemlist[-1] + "/",
                 "flavour": flavour,
                 "count": num,
                 "indent": tab}

            # this prevents a double / in the root category url
            if item == "":
                d["fullcategory"] = item

            # this adds urlencoded versions
            d["fullcategory_urlencoded"] = (
                tools.urlencode_text(d["fullcategory"]))
            d["category_urlencoded"] = tools.urlencode_text(d["category"])

            # and we toss it in the thing
            output.append(item_t % d)

            if itemlist != ['']:
                indent = len(itemlist)

        output.append(end_t * indent)
        output.append(finish_t)

        # then we join the list and that's the final string
        self._categories = "\n".join(output)


def cb_prepare(args):
    request = args["request"]
    data = request.get_data()
    data["categorylinks"] = PyblCategories(request)

########NEW FILE########
__FILENAME__ = pyfilenamemtime
#######################################################################
# This file is part of Pyblosxom.
#
# Copyright (c) 2004, 2005 Tim Roberts
# Copyright (c) 2011 Will Kahn-Greene
#
# Pyblosxom is distributed under the MIT license.  See the file
# LICENSE for distribution details.
#######################################################################

"""
Summary
=======

Allows you to specify the mtime for a file in the file name.

If a filename contains a timestamp in the form of
``YYYY-MM-DD-hh-mm``, change the mtime to be the timestamp instead of
the one kept by the filesystem.

For example, a valid filename would be ``foo-2002-04-01-00-00.txt``
for April fools day on the year 2002.  It is also possible to use
timestamps in the form of ``YYYY-MM-DD``.

http://www.probo.com/timr/blog/


Install
=======

This plugin comes with Pyblosxom.  To install, do the following:

1. Add ``Pyblosxom.plugins.pyfilenamemtime`` to the ``load_plugins``
   list of your ``config.py`` file.

2. Use date stamps in your entry filenames.

"""

__author__ = "Tim Roberts"
__email__ = ""
__version__ = "2011-10-23"
__url__ = "http://pyblosxom.github.com/"
__description__ = "Allows you to codify the mtime in the filename."
__category__ = "date"
__license__ = "MIT"
__registrytags__ = "1.4, 1.5, core"


import os
import re
import time

from Pyblosxom import tools
from Pyblosxom.memcache import memcache_decorator

DAYMATCH = re.compile(
    '([0-9]{4})-'
    '([0-1][0-9])-'
    '([0-3][0-9])'
    '(-([0-2][0-9])-([0-5][0-9]))?.[\w]+$')

@memcache_decorator('pyfilenamemtime')
def get_mtime(filename):
    mtime = 0
    mtch = DAYMATCH.search(os.path.basename(filename))
    if mtch:
        try:
            year = int(mtch.group(1))
            mo = int(mtch.group(2))
            day = int(mtch.group(3))
            if mtch.group(4) is None:
                hr = 0
                minute = 0
            else:
                hr = int(mtch.group(5))
                minute = int(mtch.group(6)) 
            mtime = time.mktime((year, mo, day, hr, minute, 0, 0, 0, -1))
        except StandardError:
            # TODO: Some sort of debugging code here?
            pass
        return mtime
    return None


def cb_filestat(args):
    filename = args["filename"]
    stattuple = args["mtime"]
    
    mtime = get_mtime(filename)

    if mtime is not None:
        args["mtime"] = (
            tuple(list(stattuple[:8]) + [mtime] + list(stattuple[9:])))

    return args

########NEW FILE########
__FILENAME__ = readmore
#######################################################################
# This file is part of Pyblosxom.
#
# Copyright (c) 2010 Menno Smits
# Copyright (c) 2011 Will Kahn-Greene
#
# Pyblosxom is distributed under the MIT license.  See the file
# LICENSE for distribution details.
#######################################################################

"""
Summary
=======

Allows you to break a long entry into a summary and the rest making it
easier to show just the summary in indexes.


Install
=======

This plugin comes with Pyblosxom.  To install, do the following:

1. Add ``Pyblosxom.plugins.readmore`` to the ``load_plugins`` list in
   your ``config.py`` file.

   .. Note::

      If you're using the rst_parser plugin, make sure this plugin
      shows up in load_plugins list before the rst_parser plugin.

      See the rst_parser section below.

2. Configure as documented below.


Configuration
=============

``readmore_breakpoint``

   (optional) string; defaults to "BREAK"

   This is the text that you'll use in your blog entry that breaks the
   body into the summary part above and the rest of the blog entry
   below.

   For example::

      py["readmore_breakpoint"] = "BREAK"

``readmore_template``

   (optional) string; defaults to::

       '<p class="readmore"><a href="%(url)s">read more after the break...</a></p>'

   When the entry is being shown in an index with other entries, then
   the ``readmore_breakpoint`` text is replaced with this text.  This
   text is done with HTML markup.

   Variables available:

   * ``%(url)s``       - the full path to the story
   * ``%(base_url)s``  - base_url
   * ``%(flavour)s``   - the flavour selected now
   * ``%(file_path)s`` - path to the story (without extension)

   .. Note::

      This template is formatted using Python string formatting---not
      Pyblosxom template formatting!


Usage
=====

For example, if the value of ``readmore_breakpoint`` is ``"BREAK"``,
then you could have a blog entry like this::

    First post
    <p>
      This is my first post.  In this post, I set out to explain why
      it is that I'm blogging and what I hope to accomplish with this
      blog.  See more below the break.
    </p>
    BREAK
    <p>
      Ha ha!  Made you look below the break!
    </p>


Usage with rst_parser
=====================

Since the rst_parser parses the restructured text and turns it into
HTML and this plugin operates on HTML in the story callback, we have
to do a two-step replacement.

Thus, instead of using BREAK or whatever you have set in
``readmore_breakpoint`` in your blog entry, you use the break
directive::

    First post

    This is my first post.  In this post, I set out to explain why
    it is that I'm blogging and what I hope to accomplish with this
    blog.

    .. break::

    Ha ha!  Made you look below the break!


History
=======

This is based on the original readmore plugin written by IWS years
ago.  It's since been reworked.

Additionally, I folded in the rst_break plugin break directive from
Menno Smits at http://freshfoo.com/wiki/CodeIndex .
"""

__author__ = "Will Kahn-Greene"
__email__ = "willg at bluesock dot org"
__version__ = "2011-11-05"
__url__ = "http://pyblosxom.github.com/"
__description__ = "Breaks blog entries into summary and details"
__category__ = "display"
__license__ = "MIT"
__registrytags__ = "1.5, core"


import re
from Pyblosxom.tools import pwrap


READMORE_BREAKPOINT = "BREAK"
READMORE_TEMPLATE = (
    '<p class="readmore">'
    '<a href="%(url)s">read more after the break...</a>'
    '</p>')


def verify_installation(request):
    config = request.get_configuration()

    for mem in ("readmore_template", "readmore_breakpoint"):
        if mem not in config:
            pwrap("missing optional config property '%s'" % mem)

    return True


def cb_start(args):
    """Register a break directive if docutils is installed."""
    try:
        from docutils import nodes
        from docutils.parsers.rst import directives, Directive
    except ImportError:
        return

    request = args['request']
    config = request.get_configuration()
    breakpoint = config.get("readmore_breakpoint", READMORE_BREAKPOINT)

    class Break(Directive):
        """
        Transform a break directive (".. break::") into the text that
        the Pyblosxom readmore plugin looks for.  This allows blog
        entries written in reST to use this plugin.
        """
        required_arguments = 0
        optional_arguments = 0
        final_argument_whitespace = True
        has_content = False

        def run(self):
            return [nodes.raw("", breakpoint + "\n", format="html")]

    directives.register_directive("break", Break)


def cb_story(args):
    entry = args["entry"]
    if not entry.has_key("body"):
        return

    request = args["request"]
    data = request.get_data()
    config = request.get_configuration()

    breakpoint = config.get("readmore_breakpoint", READMORE_BREAKPOINT)
    template = config.get("readmore_template", READMORE_TEMPLATE)

    # check to see if the breakpoint is in the body.
    match = re.search(breakpoint, entry["body"])

    # if not, return because we don't have to do anything
    if not match:
        return

    # if we're showing just one entry, then we show the whole thing
    if data["bl_type"] == 'file':
        entry["body"] = re.sub(breakpoint, "", entry["body"])
        return

    # otherwise we replace the breakpoint with the template
    base_url = config["base_url"]
    file_path = entry["file_path"]
    flavour = config.get("default_flavour", "html")
    url = '%s/%s.%s' % (base_url, file_path, flavour)

    link = (template % {"url": url,
                        "base_url": base_url,
                        "file_path": file_path,
                        "flavour": flavour})

    entry["just_summary"] = 1
    entry["body"] = entry["body"][:match.start()] + link

########NEW FILE########
__FILENAME__ = rst_parser
#######################################################################
# This file is part of Pyblosxom.
#
# Copyright (c) 2003, 2004, 2005 Sean Bowman
# Copyright (c) 2011 Will Kahn-Greene
#
# Pyblosxom is distributed under the MIT license.  See the file
# LICENSE for distribution details.
#######################################################################

"""
Summary
=======

A reStructuredText entry formatter for pyblosxom.  reStructuredText is
part of the docutils project (http://docutils.sourceforge.net/).  To
use, you need a *recent* version of docutils.  A development snapshot
(http://docutils.sourceforge.net/#development-snapshots) will work
fine.


Install
=======

This plugin comes with Pyblosxom.  To install, do the following:

1. Add ``Pyblosxom.plugins.rst_parser`` to the ``load_plugins`` list
   in your ``config.py`` file.

2. Install docutils.  Instructions are at
   http://docutils.sourceforge.net/


Usage
=====

Blog entries with a ``.rst`` extension will be parsed as
restructuredText.

You can also configure this as your default preformatter for ``.txt``
files by configuring it in your config file as follows::

   py['parser'] = 'reST'

Additionally, you can do this on an entry-by-entry basis by adding a
``#parser reST`` line in the metadata section.  For example::

   My Little Blog Entry
   #parser reST
   My main story...


Configuration
=============

There's two optional configuration parameter you can for additional
control over the rendered HTML::

   # To set the starting level for the rendered heading elements.
   # 1 is the default.
   py['reST_initial_header_level'] = 1

   # Enable or disable the promotion of a lone top-level section title to
   # document title (and subsequent section title to document subtitle
   # promotion); enabled by default.
   py['reST_transform_doctitle'] = 1


.. Note::

   If you're not seeing headings that you think should be there, try
   changing the ``reST_initial_header_level`` property to 0.
"""

__author__ = "Sean Bowman"
__email__ = "sean dot bowman at acm dot org"
__version__ = "2011-10-23"
__url__ = "http://pyblosxom.github.com/"
__description__ = "restructured text support for blog entries"
__category__ = "text"
__license__ = "MIT"
__registrytags__ = "1.5, core"


from docutils.core import publish_parts

from Pyblosxom import tools
from Pyblosxom.memcache import memcache_decorator


PREFORMATTER_ID = 'reST'
FILE_EXT = 'rst'


def verify_installation(args):
    # no configuration needed
    return 1


def cb_entryparser(args):
    args[FILE_EXT] = readfile
    return args


def cb_preformat(args):
    if args.get("parser", None) == PREFORMATTER_ID:
        return parse(''.join(args['story']), args['request'])

@memcache_decorator('rst_parser')
def _parse(initial_header_level, transform_doctitle, story):
    parts = publish_parts(
        story,
        writer_name='html',
        settings_overrides={
            'initial_header_level': initial_header_level,
            'doctitle_xform': transform_doctitle,
            'syntax_highlight': 'short'
            })
    return parts['body']


def parse(story, request):
    config = request.getConfiguration()
    initial_header_level = config.get('reST_initial_header_level', 1)
    transform_doctitle = config.get('reST_transform_doctitle', 1)

    return _parse(initial_header_level, transform_doctitle, story)


def readfile(filename, request):
    entry_data = {}
    lines = open(filename).readlines()

    if len(lines) == 0:
        return {"title": "", "body": ""}

    title = lines.pop(0).strip()

    # absorb meta data
    while lines and lines[0].startswith("#"):
        meta = lines.pop(0)
        # remove the hash
        meta = meta[1:].strip()
        meta = meta.split(" ", 1)
        # if there's no value, we append a 1
        if len(meta) == 1:
            meta.append("1")
        entry_data[meta[0].strip()] = meta[1].strip()

    body = parse(''.join(lines), request)
    entry_data["title"] = title
    entry_data["body"] = body

    # Call the postformat callbacks
    tools.run_callback('postformat', {'request': request,
                                      'entry_data': entry_data})
    return entry_data

########NEW FILE########
__FILENAME__ = tags
#######################################################################
# This file is part of Pyblosxom.
#
# Copyright (c) 2009, 2010, 2011 Will Kahn-Greene
#
# Pyblosxom is distributed under the MIT license.  See the file
# LICENSE for distribution details.
#######################################################################

"""
Summary
=======

This is a tags plugin.  It uses Pyblosxom's command line abilities to
split generation of tags index data from display of tags index data.

It creates a ``$(tagslist)`` variable for head and foot templates
which lists all the tags.

It creates a ``$(tags)`` variable for story templates which lists tags
for the story.

It creates a ``$(tagcloud)`` variable for the tag cloud.


Install
=======

This plugin comes with Pyblosxom.  To install, do the following:

1. Add ``Pyblosxom.plugins.tags`` to the ``load_plugins`` list in your
   ``config.py`` file.

2. Configure as documented below.


Configuration
=============

The following config properties define where the tags file is located,
how tag metadata is formatted, and how tag lists triggered.

``tags_separator``

    This defines the separator between tags in the metadata line.
    Defaults to ",".

    After splitting on the separator, each individual tag is stripped
    of whitespace before and after the text.

    For example::

       Weather in Boston
       #tags weather, boston
       <p>
         The weather in Boston today is pretty nice.
       </p>

    returns tags ``weather`` and ``boston``.

    If the ``tags_separator`` is::

       py["tags_separator"] = "::"

    then tags could be declared in the entries like this::

       Weather in Boston
       #tags weather::boston
       <p>
         The weather in Boston today is pretty nice.
       </p>

``tags_filename``

    This is the file that holds indexed tags data.  Defaults to
    datadir + os.pardir + ``tags.index``.

    This file needs to be readable by the process that runs your blog.
    This file needs to be writable by the process that creates the
    index.

``tags_trigger``

    This is the url trigger to indicate that the tags plugin should
    handle the file list based on the tag.  Defaults to ``tag``.

``truncate_tags``

    If this is True, then tags index listings will get passed through
    the truncate callback.  If this is False, then the tags index
    listing will not be truncated.

    If you're using a paging plugin, then setting this to True will
    allow your tags index to be paged.

    Example::

        py["truncate_tags"] = True

    Defaults to True.


In the head and foot templates, you can list all the tags with the
``$(tagslist)`` variable.  The templates for this listing use the
following three config properties:

``tags_list_start``

    Printed before the list.  Defaults to ``<p>``.

``tags_list_item``

    Used for each tag in the list.  There are a bunch of variables you can
    use:

    * ``base_url`` - the baseurl for your blog
    * ``flavour`` - the default flavour or flavour currently showing
    * ``tag`` - the tag name
    * ``count`` - the number of items that are tagged with this tag
    * ``tagurl`` - url composed of baseurl, trigger, and tag

    Defaults to ``<a href="%(tagurl)s">%(tag)s</a>``.

``tags_list_finish``

    Printed after the list.  Defaults to ``</p>``.


In the head and foot templates, you can also add a tag cloud with the
``$(tagcloud)`` variable.  The templates for the cloud use the
following three config properties:

``tags_cloud_start``

    Printed before the cloud.  Defaults to ``<p>``.

``tags_cloud_item``

    Used for each tag in the cloud list.  There are a bunch of
    variables you can use:

    * ``base_url`` - the baseurl for your blog
    * ``flavour`` - the default flavour or flavour currently showing
    * ``tag`` - the tag name
    * ``count`` - the number of items that are tagged with this tag
    * ``class`` - biggestTag, bigTag, mediumTag, smallTag or smallestTag--the
      css class for this tag representing the frequency the tag is used
    * ``tagurl`` - url composed of baseurl, trigger, and tag

    Defaults to ``<a href="%(tagurl)s">%(tag)s</a>``.

``tags_cloud_finish``

    Printed after the cloud.  Defaults to ``</p>``.

You'll also want to add CSS classes for the size classes to your CSS.
For example, you could add this::

   .biggestTag { font-size: 16pt; }
   .bigTag { font-size: 14pt }
   .mediumTag { font-size: 12pt }
   .smallTag { font-size: 10pt ]
   .smallestTag { font-size: 8pt ]


You can list the tags for a given entry in the story template with the
``$(tags)`` variable.  The tag items in the story are formatted with one
configuration property:

``tags_item``

    This is the template for a single tag for an entry.  It can use the
    following bits:

    * ``base_url`` - the baseurl for this blog
    * ``flavour`` - the default flavour or flavour currently being viewed
    * ``tag`` - the tag
    * ``tagurl`` - url composed of baseurl, trigger and tag

    Defaults to ``<a href="%(tagurl)s">%(tag)s</a>``.

    Tags are joined together with ``,``.


Creating the tags index file
============================

Run::

    pyblosxom-cmd buildtags

from the directory your ``config.py`` is in or::

    pyblosxom-cmd buildtags --config=/path/to/config/file

from anywhere.

This builds the tags index file that the tags plugin requires to
generate tags-based bits for the request.

Until you rebuild the tags index file, the entry will not have its
tags indexed.  Thus you should either rebuild the tags file after writing
or updating an entry or you should rebuild the tags file as a cron job.

.. Note::

   If you're using static rendering, you need to build the tags
   index before you statically render your blog.


Converting from categories to tags
==================================

This plugin has a command that goes through your entries and adds tag
metadata based on the category.  There are some caveats:

1. it assumes entries are in the blosxom format of title, then
   metadata, then the body.

2. it only operates on entries in the datadir.

It maintains the atime and mtime of the file.  My suggestion is to
back up your files (use tar or something that maintains file stats),
then try it out and see how well it works, and figure out if that
works or not.

To run the command do::

    pyblosxom-cmd categorytotags

from the directory your ``config.py`` is in or::

    pyblosxom-cmd categorytotags --config=/path/to/config/file

from anywhere.
"""

__author__ = "Will Kahn-Greene"
__email__ = "willg at bluesock dot org"
__version__ = "2011-10-23"
__url__ = "http://pyblosxom.github.com/"
__description__ = "Tags plugin"
__category__ = "tags"
__license__ = "MIT"
__registrytags__ = "1.5, core"


import os
import cPickle as pickle
import shutil

from Pyblosxom.memcache import memcache_decorator


def savefile(path, tagdata):
    """Saves tagdata to file at path."""
    fp = open(path + ".new", "w")
    pickle.dump(tagdata, fp)
    fp.close()

    shutil.move(path + ".new", path)


@memcache_decorator('tags')
def loadfile(path):
    """Loads tagdata from file at path."""
    fp = open(path, "r")
    tagdata = pickle.load(fp)
    fp.close()
    return tagdata


def get_tagsfile(cfg):
    """Generates tagdata filename."""
    datadir = cfg["datadir"]
    tagsfile = cfg.get("tags_filename",
                       os.path.join(datadir, os.pardir, "tags.index"))
    return tagsfile


def buildtags(command, argv):
    """Command for building the tags index."""
    import config

    datadir = config.py.get("datadir")
    if not datadir:
        raise ValueError("config.py has no datadir property.")

    sep = config.py.get("tags_separator", ",")
    tagsfile = get_tagsfile(config.py)

    from Pyblosxom.pyblosxom import Pyblosxom
    from Pyblosxom import tools
    from Pyblosxom.entries import fileentry

    # build a Pyblosxom object, initialize it, and run the start
    # callback.  this gives entry parsing related plugins a chance to
    # get their stuff together so that they work correctly.
    p = Pyblosxom(config.py, {})
    p.initialize()
    req = p.get_request()
    tools.run_callback("start", {"request": req})

    # grab all the entries in the datadir
    filelist = tools.walk(req, datadir)
    entrylist = [fileentry.FileEntry(req, e, datadir) for e in filelist]

    tags_to_files = {}
    for mem in entrylist:
        tagsline = mem["tags"]
        if not tagsline:
            continue
        tagsline = [t.strip() for t in tagsline.split(sep)]
        for t in tagsline:
            tags_to_files.setdefault(t, []).append(mem["filename"])

    savefile(tagsfile, tags_to_files)
    return 0


def category_to_tags(command, argv):
    """Goes through all entries and converts the category to tags
    metadata.

    It adds the tags line as the second line.

    It maintains the mtime for the file.
    """
    import config

    datadir = config.py.get("datadir")
    if not datadir:
        raise ValueError("config.py has no datadir property.")

    sep = config.py.get("tags_separator", ",")

    from Pyblosxom.pyblosxom import Request
    from Pyblosxom.blosxom import blosxom_entry_parser
    from Pyblosxom import tools

    data = {}

    # register entryparsers so that we parse all possible file types.
    data["extensions"] = tools.run_callback("entryparser",
                                            {"txt": blosxom_entry_parser},
                                            mappingfunc=lambda x, y: y,
                                            defaultfunc=lambda x: x)

    req = Request(config.py, {}, data)

    # grab all the entries in the datadir
    filelist = tools.walk(req, datadir)

    if not datadir.endswith(os.sep):
        datadir = datadir + os.sep

    for mem in filelist:
        print "working on %s..." % mem

        category = os.path.dirname(mem)[len(datadir):]
        tags = category.split(os.sep)
        print "   adding tags %s" % tags
        tags = "#tags %s\n" % (sep.join(tags))

        atime, mtime = os.stat(mem)[7:9]

        fp = open(mem, "r")
        data = fp.readlines()
        fp.close()

        data.insert(1, tags)

        fp = open(mem, "w")
        fp.write("".join(data))
        fp.close()

        os.utime(mem, (atime, mtime))

    return 0


def cb_commandline(args):
    args["buildtags"] = (buildtags, "builds the tags index")
    args["categorytotags"] = (
        category_to_tags,
        "builds tag metadata from categories for entries")
    return args


def cb_start(args):
    request = args["request"]
    data = request.get_data()
    tagsfile = get_tagsfile(request.get_configuration())
    if os.path.exists(tagsfile):
        try:
            tagsdata = loadfile(tagsfile)
        except IOError:
            tagsdata = {}
    else:
        tagsdata = {}
    data["tagsdata"] = tagsdata


def cb_filelist(args):
    from Pyblosxom.blosxom import blosxom_truncate_list_handler
    from Pyblosxom import tools

    # handles /trigger/tag to show all the entries tagged that
    # way
    req = args["request"]

    pyhttp = req.get_http()
    data = req.get_data()
    config = req.get_configuration()

    trigger = "/" + config.get("tags_trigger", "tag")
    if not pyhttp["PATH_INFO"].startswith(trigger):
        return

    datadir = config["datadir"]
    tagsfile = get_tagsfile(config)
    tagsdata = loadfile(tagsfile)

    tag = pyhttp["PATH_INFO"][len(trigger) + 1:]
    filelist = tagsdata.get(tag, [])
    if not filelist:
        tag, ext = os.path.splitext(tag)
        filelist = tagsdata.get(tag, [])
        if filelist:
            data["flavour"] = ext[1:]

    from Pyblosxom.entries import fileentry
    entrylist = [fileentry.FileEntry(req, e, datadir) for e in filelist]

    # sort the list by mtime
    entrylist = [(e._mtime, e) for e in entrylist]
    entrylist.sort()
    entrylist.reverse()
    entrylist = [e[1] for e in entrylist]

    data["truncate"] = config.get("truncate_tags", True)

    args = {"request": req, "entry_list": entrylist}
    entrylist = tools.run_callback("truncatelist",
                                   args,
                                   donefunc=lambda x: x != None,
                                   defaultfunc=blosxom_truncate_list_handler)

    return entrylist


def cb_story(args):
    # adds tags to the entry properties
    request = args["request"]
    entry = args["entry"]
    config = request.get_configuration()

    sep = config.get("tags_separator", ",")
    tags = [t.strip() for t in entry.get("tags", "").split(sep)]
    tags.sort()
    entry["tags_raw"] = tags

    form = request.get_form()
    try:
        flavour = form["flav"].value
    except KeyError:
        flavour = config.get("default_flavour", "html")
    baseurl = config.get("base_url", "")
    trigger = config.get("tags_trigger", "tag")
    template = config.get("tags_item", '<a href="%(tagurl)s">%(tag)s</a>')

    tags = [template % {"base_url": baseurl,
                        "flavour": flavour,
                        "tag": tag,
                        "tagurl": "/".join([baseurl, trigger, tag])}
            for tag in tags]
    entry["tags"] = ", ".join(tags)
    return args


def cb_head(args):
    # adds a taglist to header/footer
    request = args["request"]
    entry = args["entry"]
    data = request.get_data()
    config = request.get_configuration()
    tagsdata = data.get("tagsdata", {})

    # first, build the tags list
    tags = tagsdata.keys()
    tags.sort()

    start_t = config.get("tags_list_start", '<p>')
    item_t = config.get("tags_list_item", ' <a href="%(tagurl)s">%(tag)s</a> ')
    finish_t = config.get("tags_list_finish", '</p>')

    output = []

    form = request.get_form()
    try:
        flavour = form["flav"].value
    except KeyError:
        flavour = config.get("default_flavour", "html")
    baseurl = config.get("base_url", "")
    trigger = config.get("tags_trigger", "tag")

    output.append(start_t)
    for item in tags:
        d = {"base_url": baseurl,
             "flavour": flavour,
             "tag": item,
             "count": len(tagsdata[item]),
             "tagurl": "/".join([baseurl, trigger, item])}
        output.append(item_t % d)
    output.append(finish_t)

    entry["tagslist"] = "\n".join(output)

    # second, build the tags cloud
    tags_by_file = tagsdata.items()

    start_t = config.get("tags_cloud_start", "<p>")
    item_t = config.get("tags_cloud_item",
                        '<a class="%(class)s" href="%(tagurl)s">%(tag)s</a>')
    finish_t = config.get("tags_cloud_finish", "</p>")

    tagcloud = [start_t]

    if len(tags_by_file) > 0:
        tags_by_file.sort(key=lambda x: len(x[1]))
        # the most popular tag is at the end--grab the number of files
        # that have that tag
        max_count = len(tags_by_file[-1][1])
        min_count = len(tags_by_file[0])

        # figure out the bin size for the tag size classes
        b = (max_count - min_count) / 5

        range_and_class = (
            (min_count + (b * 4), "biggestTag"),
            (min_count + (b * 3), "bigTag"),
            (min_count + (b * 2), "mediumTag"),
            (min_count + b, "smallTag"),
            (0, "smallestTag")
            )

        # sorts it alphabetically
        tags_by_file.sort()

        for tag, files in tags_by_file:
            len_files = len(files)
            for tag_range, tag_size_class in range_and_class:
                if len_files > tag_range:
                    tag_class = tag_size_class
                    break

            d = {"base_url": baseurl,
                 "flavour": flavour,
                 "class": tag_class,
                 "tag": tag,
                 "count": len(tagsdata[tag]),
                 "tagurl": "/".join([baseurl, trigger, tag])}

            tagcloud.append(item_t % d)

    tagcloud.append(finish_t)
    entry["tagcloud"] = "\n".join(tagcloud)

    return args


cb_foot = cb_head


def cb_staticrender_filelist(args):
    req = args["request"]

    # We call our own cb_start() here because we need to initialize
    # the tagsdata.
    cb_start({"request": req})

    config = req.get_configuration()
    filelist = args["filelist"]

    tagsdata = req.get_data()["tagsdata"]
    index_flavours = config.get("static_index_flavours", ["html"])
    trigger = "/" + config.get("tags_trigger", "tag")

    # Go through and add an index.flav for each index_flavour
    # for each tag.
    for tag in tagsdata.keys():
        for flavour in index_flavours:
            filelist.append((trigger + "/" + tag + "." + flavour, ""))

########NEW FILE########
__FILENAME__ = trackback
#######################################################################
# This file is part of Pyblosxom.
#
# Copyright (c) 2003-2005 Ted Leung
#
# Pyblosxom is distributed under the MIT license.  See the file
# LICENSE for distribution details.
#######################################################################

"""
Summary
=======

This plugin allows pyblosxom to process trackback
http://www.sixapart.com/pronet/docs/trackback_spec pings.


Install
=======

Requires the ``comments`` plugin.  Though you don't need to have
comments enabled on your blog in order for trackbacks to work.

This plugin comes with Pyblosxom.  To install, do the following:

1. Add ``Pyblosxom.plugins.trackback`` to the ``load_plugins`` list
   in your ``config.py`` file.

2. Add this to your ``config.py`` file::

       py['trackback_urltrigger'] = "/trackback"

   These web forms are useful for testing.  You can use them to send
   trackback pings with arbitrary content to the URL of your choice:

   * http://kalsey.com/tools/trackback/
   * http://www.reedmaniac.com/scripts/trackback_form.php

3. Now you need to advertise the trackback ping link.  Add this to your
   ``story`` template::

       <a href="$(base_url)/trackback/$(file_path)" title="Trackback">TB</a>

4. You can supply an embedded RDF description of the trackback ping, too.
   Add this to your ``story`` or ``comment-story`` template::

       <!--
       <rdf:RDF
       xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
       xmlns:dc="http://purl.org/dc/elements/1.1/"
       xmlns:trackback="http://madskills.com/public/xml/rss/module/trackback/">
       <rdf:Description
            about="$(base_url)/$(file_path)"
            dc:title="$(title)"
            dc:identifier="$(base_url)/$(file_path)"
            trackback:ping="$(base_url)/trackback/$(file_path)"
       />
       </rdf:RDF>
       -->

"""

__author__ = "Ted Leung"
__email__ = ""
__version__ = ""
__url__ = "http://pyblosxom.github.com/"
__description__ = "Trackback support."
__category__ = "comments"
__license__ = "MIT"
__registrytags__ = "1.4, core"


from Pyblosxom import tools
from Pyblosxom.tools import pwrap


tb_good_response = """<?xml version="1.0" encoding="iso-8859-1"?>
<response>
<error>0</error>
</response>"""


tb_bad_response = """<?xml version="1.0" encoding="iso-8859-1"?>
<response>
<error>1</error>
<message>%s</message>
</response>"""


def verify_installation(request):
    config = request.get_configuration()

    # all config properties are optional
    if not 'trackback_urltrigger' in config:
        pwrap("missing optional property: 'trackback_urltrigger'")

    return True


def cb_handle(args):
    request = args['request']
    pyhttp = request.get_http()
    config = request.get_configuration()

    urltrigger = config.get('trackback_urltrigger', '/trackback')

    logger = tools.get_logger()

    path_info = pyhttp['PATH_INFO']
    if path_info.startswith(urltrigger):
        response = request.get_response()
        response.add_header("Content-type", "text/xml")

        form = request.get_form()

        message = ("A trackback must have at least a URL field (see "
                   "http://www.sixapart.com/pronet/docs/trackback_spec)")

        if "url" in form:
            from comments import decode_form
            encoding = config.get('blog_encoding', 'iso-8859-1')
            decode_form(form, encoding)
            import time
            cdict = {'title': form.getvalue('title', ''),
                     'author': form.getvalue('blog_name', ''),
                     'pubDate': str(time.time()),
                     'link': form['url'].value,
                     'source': form.getvalue('blog_name', ''),
                     'description': form.getvalue('excerpt', ''),
                     'ipaddress': pyhttp.get('REMOTE_ADDR', ''),
                     'type': 'trackback'
                     }
            argdict = {"request": request, "comment": cdict}
            reject = tools.run_callback("trackback_reject",
                                        argdict,
                                        donefunc=lambda x: x != 0)
            if isinstance(reject, (tuple, list)) and len(reject) == 2:
                reject_code, reject_message = reject
            else:
                reject_code, reject_message = reject, "Trackback rejected."

            if reject_code == 1:
                print >> response, tb_bad_response % reject_message
                return 1

            from Pyblosxom.entries.fileentry import FileEntry

            datadir = config['datadir']

            from comments import writeComment
            try:
                import os
                pi = path_info.replace(urltrigger, '')
                path = os.path.join(datadir, pi[1:])
                data = request.get_data()
                ext = tools.what_ext(data['extensions'].keys(), path)
                entry = FileEntry(request, '%s.%s' % (path, ext), datadir)
                data = {}
                data['entry_list'] = [entry]
                # Format Author
                cdict['author'] = (
                    'Trackback from %s' % form.getvalue('blog_name', ''))
                writeComment(request, config, data, cdict, encoding)
                print >> response, tb_good_response
            except OSError:
                message = 'URI ' + path_info + " doesn't exist"
                logger.error(message)
                print >> response, tb_bad_response % message

        else:
            logger.error(message)
            print >> response, tb_bad_response % message

        # no further handling is needed
        return 1
    return 0

########NEW FILE########
__FILENAME__ = w3cdate
#######################################################################
# This file is part of Pyblosxom.
#
# Copyright (c) 2003-2005 Ted Leung
# Copyright (c) 2010, 2011 Will Kahn-Greene
#
# Pyblosxom is distributed under the MIT license.  See the file
# LICENSE for distribution details.
#######################################################################

"""
Summary
=======

Adds a ``$(w3cdate)`` variable to the head and foot templates which has
the mtime of the first entry in the entrylist being displayed (this is
often the youngest/most-recent entry).


Install
=======

.. Note::

   If you have pyxml installed, then this will work better than if you don't.
   If you don't have it installed, it uses home-brew code to compute the
   w3cdate.

This plugin comes with Pyblosxom.  To install, do the following:

1. Add ``Pyblosxom.plugins.w3cdate`` to the beginning of the
   ``load_plugins`` list of your ``config.py`` file.

2. Add the ``$(w3cdate)`` variable to the place you need it in your head
   and/or foot templates.


Thanks
======

Thanks to Matej Cepl for the hacked iso8601 code that doesn't require
PyXML.
"""

__author__ = "Ted Leung"
__email__ = "twl at sauria dot com"
__version__ = "2011-10-23"
__url__ = "http://pyblosxom.github.com/"
__description__ = (
    "Adds a 'w3cdate' variable which is the mtime in ISO8601 format.")
__category__ = "date"
__license__ = "MIT"
__registrytags__ = "1.4, 1.5, core"


import time


def iso8601_hack_tostring(t, timezone):
    timezone = int(timezone)
    if timezone:
        sign = (timezone < 0) and "+" or "-"
        timezone = abs(timezone)
        hours = timezone / (60 * 60)
        minutes = (timezone % (60 * 60)) / 60
        tzspecifier = "%c%02d:%02d" % (sign, hours, minutes)
    else:
        tzspecifier = "Z"
    psecs = t - int(t)
    t = time.gmtime(int(t) - timezone)
    year, month, day, hours, minutes, seconds = t[:6]
    if seconds or psecs:
        if psecs:
            psecs = int(round(psecs * 100))
            f = "%4d-%02d-%02dT%02d:%02d:%02d.%02d%s"
            v = (year, month, day, hours, minutes, seconds, psecs, tzspecifier)
        else:
            f = "%4d-%02d-%02dT%02d:%02d:%02d%s"
            v = (year, month, day, hours, minutes, seconds, tzspecifier)
    else:
        f = "%4d-%02d-%02dT%02d:%02d%s"
        v = (year, month, day, hours, minutes, tzspecifier)
    return f % v


try:
    from xml.utils import iso8601
    format_date = iso8601.tostring

except (ImportError, AttributeError):
    format_date = iso8601_hack_tostring


def get_formatted_date(entry):
    if not entry:
        return ""

    time_tuple = entry['timetuple']
    tzoffset = time.timezone

    # if is_dst flag set, adjust for daylight savings time
    if time_tuple[8] == 1:
        tzoffset = time.altzone
    return format_date(time.mktime(time_tuple), tzoffset)


def cb_story(args):
    entry = args['entry']
    entry["w3cdate"] = get_formatted_date(entry)


def cb_head(args):
    entry = args["entry"]

    req = args["request"]
    data = req.get_data()

    entrylist = data.get("entry_list", None)
    if not entrylist:
        return args

    entry["w3cdate"] = get_formatted_date(entrylist[0])
    return args


cb_foot = cb_head

########NEW FILE########
__FILENAME__ = xmlrpc_pingback
#######################################################################
# This file is part of Pyblosxom.
#
# Copyright (c) 2003-2006 Ted Leung, Ryan Barrett
#
# Pyblosxom is distributed under the MIT license.  See the file
# LICENSE for distribution details.
#######################################################################

"""
Summary
=======

This module contains an XML-RPC extension to support pingback
http://www.hixie.ch/specs/pingback/pingback pings.


Install
=======

Requires the ``comments`` plugin, but you don't have to enable
comments on your blog for pingbacks to work.

This plugin comes with Pyblosxom.  To install, do the following:

1. Add ``Pyblosxom.plugins.xmlrpc_pingback`` to the ``load_plugins``
   list of your ``config.py`` file

2. Set the ``xmlrpc_trigger`` variable in your ``config.py`` file to a
   trigger for this plugin.  For example::

      py["xmlrpc_trigger"] = "RPC"

3. Add to the ``<head>`` section of your ``head`` template::

      <link rel="pingback" href="$(base_url)/RPC" />


This test blog, maintained by Ian Hickson, is useful for testing. You
can post to it, linking to a post on your site, and it will send a
pingback.

* http://www.dummy-blog.org/

"""
from Pyblosxom.blosxom import blosxom_file_list_handler, blosxom_process_path_info

__author__ = "Ted Leung, Ryan Barrett"
__email__ = ""
__version__ = "2011-10-28"
__url__ = "http://pyblosxom.github.com/"
__description__ = "XMLRPC pingback support."
__category__ = "comments"
__license__ = "MIT"
__registrytags__ = "1.4, core"


from Pyblosxom import tools
from xmlrpclib import Fault

import re
import sgmllib
import time
import urllib
import urlparse


def verify_installation(request):
    # no config parameters
    return True


class parser(sgmllib.SGMLParser):
    """ Shamelessly grabbed from Sam Ruby
    from http://www.intertwingly.net/code/mombo/pingback.py
    """
    intitle = 0
    title = ""
    hrefs = []

    def do_a(self, attrs):
        attrs = dict(attrs)
        if 'href' in attrs:
            self.hrefs.append(attrs['href'])

    def do_title(self, attrs):
        if self.title == "":
            self.intitle = 1

    def unknown_starttag(self, tag, attrs):
        self.intitle = 0

    def unknown_endtag(self, tag):
        self.intitle = 0

    def handle_charref(self, ref):
        if self.intitle:
            self.title = self.title + ("&#%s;" % ref)

    def handle_data(self, text):
        if self.intitle:
            self.title = self.title + text


def fileFor(req, uri):
    config = req.get_configuration()
    urldata = urlparse.urlsplit(uri)

    # Reconstruct uri to something sane
    uri = "%s://%s%s" % (urldata[0], urldata[1], urldata[2])
    fragment = urldata[4]

    # We get our path here
    path = uri.replace(config['base_url'], '')
    req.add_http({'PATH_INFO': path, "form": {}})
    blosxom_process_path_info({'request': req})

    args = {'request': req}
    es = blosxom_file_list_handler(args)

    # We're almost there
    if len(es) == 1 and path.find(es[0]['file_path']) >= 0:
        return es[0]

    # Could be a fragment link
    for i in es:
        if i['fn'] == fragment:
            return i

    # Point of no return
    if len(es) >= 1:
        raise Fault(0x0021, "%s cannot be used as a target" % uri)
    else:
        raise Fault(0x0020, "%s does not exist")


def pingback(request, source, target):
    logger = tools.get_logger()
    logger.info("pingback started")
    source_file = urllib.urlopen(source.split('#')[0])
    if source_file.headers.get('error', '') == '404':
        raise Fault(0x0010, "Target %s not exists" % target)
    source_page = parser()
    source_page.feed(source_file.read())
    source_file.close()

    if source_page.title == "":
        source_page.title = source

    if not target in source_page.hrefs:
        raise Fault(0x0011, "%s does not point to %s" % (source, target))

    target_entry = fileFor(request, target)

    body = ''
    try:
        from rssfinder import getFeeds
        from rssparser import parse

        baseurl = source.split("#")[0]
        for feed in getFeeds(baseurl):
            for item in parse(feed)['items']:
                if item['link'] == source:
                    if 'title' in item:
                        source_page.title = item['title']
                    if 'content_encoded' in item:
                        body = item['content_encoded'].strip()
                    if 'description' in item:
                        body = item['description'].strip() or body
                    body = re.compile('<.*?>', re.S).sub('', body)
                    body = re.sub('\s+', ' ', body)
                    body = body[:body.rfind(' ', 0, 250)][:250] + " ...<br />"
    except:
        pass

    cmt = {'title': source_page.title,
           'author': 'Pingback from %s' % source_page.title,
           'pubDate': str(time.time()),
           'link': source,
           'source': '',
           'description': body}

    # run anti-spam plugins
    argdict = {"request": request, "comment": cmt}
    reject = tools.run_callback("trackback_reject",
                                argdict,
                                donefunc=lambda x: x != 0)
    if isinstance(reject, (tuple, list)) and len(reject) == 2:
        reject_code, reject_message = reject
    else:
        reject_code, reject_message = reject, "Pingback rejected."
    if reject_code == 1:
        raise Fault(0x0031, reject_message)

    from comments import writeComment
    config = request.get_configuration()
    data = request.get_data()
    data['entry_list'] = [target_entry]

    # TODO: Check if comment from the URL exists
    writeComment(request, config, data, cmt, config['blog_encoding'])

    return "success pinging %s from %s\n" % (target, source)


def cb_xmlrpc_register(args):
    """
    Register as a pyblosxom XML-RPC plugin
    """
    args['methods'].update({'pingback.ping': pingback})
    return args

########NEW FILE########
__FILENAME__ = yeararchives
#######################################################################
# This file is part of Pyblosxom.
#
# Copyright (C) 2004-2011 by the Pyblosxom team.  See AUTHORS.
#
# Pyblosxom is distributed under the MIT license.  See the file
# LICENSE for distribution details.
#######################################################################

"""
Summary
=======

Walks through your blog root figuring out all the available years for
the archives list.  It stores the years with links to year summaries
in the variable ``$(archivelinks)``.  You should put this variable in
either your head or foot template.


Install
=======

This plugin comes with Pyblosxom.  To install, do the following:

1. Add ``Pyblosxom.plugins.yeararchives`` to the ``load_plugins`` list
   in your ``config.py`` file.

2. Add ``$(archivelinks)`` to your head and/or foot templates.

3. Configure as documented below.


Usage
=====

When the user clicks on one of the year links
(e.g. ``http://base_url/2004/``), then yeararchives will display a
summary page for that year.  The summary is generated using the
``yearsummarystory`` template for each month in the year.

My ``yearsummarystory`` template looks like this::

   <div class="blosxomEntry">
   <span class="blosxomTitle">$title</span>
   <div class="blosxomBody">
   <table>
   $body
   </table>
   </div>
   </div>


The ``$(archivelinks)`` link can be configured with the
``archive_template`` config variable.  It uses the Python string
formatting syntax.

Example::

    py['archive_template'] = (
        '<a href="%(base_url)s/%(Y)s/index.%(f)s">'
        '%(Y)s</a><br />')

The vars available with typical example values are::

    Y      4-digit year   ex: '1978'
    y      2-digit year   ex: '78'
    f      the flavour    ex: 'html'

.. Note::

   The ``archive_template`` variable value is formatted using Python
   string formatting rules--not Pyblosxom template rules!

"""

__author__ = "Will Kahn-Greene"
__email__ = "willg at bluesock dot org"
__version__ = "2010-05-08"
__url__ = "http://pyblosxom.github.com/"
__description__ = "Builds year-based archives listing."
__category__ = "archives"
__license__ = "MIT"
__registrytags__ = "1.4, 1.5, core"


from Pyblosxom import tools, entries
from Pyblosxom.memcache import memcache_decorator
from Pyblosxom.tools import pwrap
import time


def verify_installation(request):
    config = request.get_configuration()
    if not 'archive_template' in config:
        pwrap(
            "missing optional config property 'archive_template' which "
            "allows you to specify how the archive links are created.  "
            "refer to yeararchives plugin documentation for more details.")

    return True


class YearArchives:
    def __init__(self, request):
        self._request = request
        self._archives = None
        self._items = None

    @memcache_decorator('yeararchives', True)
    def __str__(self):
        if self._archives is None:
            self.gen_linear_archive()
        return self._archives

    def gen_linear_archive(self):
        config = self._request.get_configuration()
        data = self._request.get_data()
        root = config["datadir"]

        archives = {}
        archive_list = tools.walk(self._request, root)
        items = []

        fulldict = {}
        fulldict.update(config)
        fulldict.update(data)

        flavour = data.get(
            "flavour", config.get("default_flavour", "html"))

        template = config.get(
            'archive_template',
            '<a href="%(base_url)s/%(Y)s/index.%(f)s">%(Y)s</a><br />')

        for mem in archive_list:
            timetuple = tools.filestat(self._request, mem)

            timedict = {}
            for x in ["m", "Y", "y", "d"]:
                timedict[x] = time.strftime("%" + x, timetuple)

            fulldict.update(timedict)
            fulldict["f"] = flavour
            year = fulldict["Y"]

            if not year in archives:
                archives[year] = template % fulldict
            items.append(
                ["%(Y)s-%(m)s" % fulldict,
                 "%(Y)s-%(m)s-%(d)s" % fulldict,
                 time.mktime(timetuple),
                 mem])

        arc_keys = archives.keys()
        arc_keys.sort()
        arc_keys.reverse()

        result = []
        for key in arc_keys:
            result.append(archives[key])
        self._archives = '\n'.join(result)
        self._items = items


def new_entry(request, yearmonth, body):
    """
    Takes a bunch of variables and generates an entry out of it.  It
    creates a timestamp so that conditionalhttp can handle it without
    getting all fussy.
    """
    entry = entries.base.EntryBase(request)

    entry['title'] = yearmonth
    entry['filename'] = yearmonth + "/summary"
    entry['file_path'] = yearmonth
    entry._id = yearmonth + "::summary"

    entry["template_name"] = "yearsummarystory"
    entry["nocomments"] = "yes"

    entry["absolute_path"] = ""
    entry["fn"] = ""

    entry.set_time(time.strptime(yearmonth, "%Y-%m"))
    entry.set_data(body)

    return entry


INIT_KEY = "yeararchives_initiated"


def cb_prepare(args):
    request = args["request"]
    data = request.get_data()
    data["archivelinks"] = YearArchives(request)


def cb_date_head(args):
    request = args["request"]
    data = request.get_data()

    if INIT_KEY in data:
        args["template"] = ""
    return args


def parse_path_info(path):
    """Returns None or (year, flav) tuple.

    Handles urls of this type:

    - /2003
    - /2003/
    - /2003/index
    - /2003/index.flav
    """
    path = path.split("/")
    path = [m for m in path if m]
    if not path:
        return

    year = path[0]
    if not year.isdigit() or not len(year) == 4:
        return

    if len(path) == 1:
        return (year, None)

    if len(path) == 2 and path[1].startswith("index"):
        flav = None
        if "." in path[1]:
            flav = path[1].split(".", 1)[1]
        return (year, flav)

    return


def cb_filelist(args):
    request = args["request"]
    pyhttp = request.get_http()
    data = request.get_data()
    config = request.get_configuration()
    baseurl = config.get("base_url", "")

    path = pyhttp["PATH_INFO"]

    ret = parse_path_info(path)
    if ret == None:
        return

    # note: returned flavour is None if there is no .flav appendix
    year, flavour = ret

    data[INIT_KEY] = 1

    # get all the entries
    wa = YearArchives(request)
    wa.gen_linear_archive()
    items = wa._items

    # peel off the items for this year
    items = [m for m in items if m[0].startswith(year)]

    items.sort()
    items.reverse()

    # Set and use current (or default) flavour for permalinks
    if not flavour:
        flavour = data.get(
            "flavour", config.get("default_flavour", "html"))

    data["flavour"] = flavour

    l = ("(%(path)s) <a href=\"" + baseurl +
         "/%(file_path)s." + flavour + "\">%(title)s</a><br>")
    e = "<tr>\n<td valign=\"top\" align=\"left\">%s</td>\n<td>%s</td></tr>\n"
    d = ""
    m = ""

    day = []
    month = []
    entrylist = []

    for mem in items:
        if not m:
            m = mem[0]
        if not d:
            d = mem[1]

        if m != mem[0]:
            month.append(e % (d, "\n".join(day)))
            entrylist.append(new_entry(request, m, "\n".join(month)))
            m = mem[0]
            d = mem[1]
            day = []
            month = []

        elif d != mem[1]:
            month.append(e % (d, "\n".join(day)))
            d = mem[1]
            day = []
        entry = entries.fileentry.FileEntry(
            request, mem[3], config['datadir'])
        day.append(l % entry)

    if day:
        month.append(e % (d, "\n".join(day)))
    if month:
        entrylist.append(new_entry(request, m, "\n".join(month)))

    return entrylist

########NEW FILE########
__FILENAME__ = plugin_utils
#######################################################################
# This file is part of Pyblosxom.
#
# Copyright (C) 2003-2011 by the Pyblosxom team.  See AUTHORS.
#
# Pyblosxom is distributed under the MIT license.  See the file
# LICENSE for distribution details.
#######################################################################

"""
Holds a series of utility functions for cataloguing, retrieving, and
manipulating callback functions and chains.  Refer to the documentation
for which callbacks are available and their behavior.
"""

import os
import glob
import sys
import os.path
import traceback


# this holds the list of plugins that have been loaded.  if you're running
# Pyblosxom as a long-running process, this only gets cleared when the
# process is restarted.
plugins = []

# this holds a list of callbacks (any function that begins with cp_) and the
# list of function instances that support that callback.
# if you're running Pyblosxom as a long-running process, this only
# gets cleared when the process is restarted.
callbacks = {}

# this holds a list of (plugin name, exception) tuples for plugins that
# didn't import.
bad_plugins = []


def catalogue_plugin(plugin_module):
    """
    Goes through the plugin's contents and catalogues all the functions
    that start with cb_.  Functions that start with cb_ are callbacks.

    :param plugin_module: the module to catalogue
    """
    listing = dir(plugin_module)

    listing = [item for item in listing if item.startswith("cb_")]

    for mem in listing:
        func = getattr(plugin_module, mem)
        memadj = mem[3:]
        if callable(func):
            callbacks.setdefault(memadj, []).append(func)


def get_callback_chain(chain):
    """
    Returns a list of functions registered with the callback.

    @returns: list of functions registered with the callback (or an
        empty list)
    @rtype: list of functions
    """
    return callbacks.get(chain, [])


def initialize_plugins(plugin_dirs, plugin_list):
    """
    Imports and initializes plugins from the directories in the list
    specified by "plugins_dir".  If no such list exists, then we don't
    load any plugins.

    If the user specifies a "load_plugins" list of plugins to load, then
    we explicitly load those plugins in the order they're listed.  If the
    load_plugins key does not exist, then we load all the plugins in the
    plugins directory using an alphanumeric sorting order.

    .. Note::

       If Pyblosxom is part of a long-running process, you must
       restart Pyblosxom in order to pick up any changes to your plugins.

    :param plugin_dirs: the list of directories to add to the sys.path
                        because that's where our plugins are located.

    :param plugin_list: the list of plugins to load, or if None, we'll
                        load all the plugins we find in those dirs.
    """
    if plugins or bad_plugins:
        return

    # we clear out the callbacks dict so we can rebuild them
    callbacks.clear()

    # handle plugin_dirs here
    for mem in plugin_dirs:
        if os.path.isdir(mem):
            sys.path.append(mem)
        else:
            raise Exception("Plugin directory '%s' does not exist.  " \
                            "Please check your config file." % mem)

    plugin_list = get_plugin_list(plugin_list, plugin_dirs)

    for mem in plugin_list:
        try:
            _module = __import__(mem)
        except (SystemExit, KeyboardInterrupt):
            raise
        except:
            # this needs to be a catch-all
            bad_plugins.append((mem, "".join(traceback.format_exc())))
            continue

        for comp in mem.split(".")[1:]:
            _module = getattr(_module, comp)
        catalogue_plugin(_module)
        plugins.append(_module)


def get_plugin_by_name(name):
    """
    This retrieves a plugin instance (it's a Python module instance)
    by name.

    :param name: the name of the plugin to retrieve (ex: "xmlrpc")

    :returns: the Python module instance for the plugin or None
    """
    if plugins:
        for mem in plugins:
            if mem.__name__ == name:
                return mem
    return None


def get_module_name(filename):
    """
    Takes a filename and returns the module name from the filename.

    Example: passing in "/blah/blah/blah/module.ext" returns "module"

    :param filename: the filename in question (with a full path)

    :returns: the filename without path or extension
    """
    return os.path.splitext(os.path.split(filename)[1])[0]


def get_plugin_list(plugin_list, plugin_dirs):
    """
    This handles the situation where the user has provided a series of
    plugin dirs, but has not specified which plugins they want to load
    from those dirs.  In this case, we load all possible plugins except
    the ones whose names being with _ .

    :param plugin_list: List of plugins to load

    :param plugin_dirs: A list of directories where plugins can be loaded from

    :return: list of python module names of the plugins to load
    """
    if plugin_list is None:
        plugin_list = []
        for mem in plugin_dirs:
            file_list = glob.glob(os.path.join(mem, "*.py"))

            file_list = [get_module_name(filename) for filename in file_list]

            # remove plugins that start with a _
            file_list = [plugin for plugin in file_list \
                         if not plugin.startswith('_')]
            plugin_list += file_list

        plugin_list.sort()

    return plugin_list

########NEW FILE########
__FILENAME__ = pyblosxom
#######################################################################
# This file is part of Pyblosxom.
#
# Copyright (C) 2003-2011 by the Pyblosxom team.  See AUTHORS.
#
# Pyblosxom is distributed under the MIT license.  See the file
# LICENSE for distribution details.
#######################################################################


"""This is the main module for Pyblosxom functionality.  Pyblosxom's
setup and default handlers are defined here.
"""

from __future__ import nested_scopes, generators

# Python imports
import cgi
import locale
import os
import sys
import time
from Pyblosxom.blosxom import blosxom_entry_parser, blosxom_handler

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

# Pyblosxom imports
from Pyblosxom import __version__
from Pyblosxom import crashhandling
from Pyblosxom import tools
from Pyblosxom import plugin_utils


VERSION = __version__


class Pyblosxom:
    """Main class for Pyblosxom functionality.  It handles
    initialization, defines default behavior, and also pushes the
    request through all the steps until the output is rendered and
    we're complete.
    """

    def __init__(self, config, environ, data=None):
        """Sets configuration and environment and creates the Request
        object.

        :param config: dict containing the configuration variables.
        :param environ: dict containing the environment variables.
        :param data: dict containing data variables.
        """
        # FIXME: These shouldn't be here.
        config['pyblosxom_name'] = "pyblosxom"
        config['pyblosxom_version'] = __version__

        self._config = config
        self._request = Request(config, environ, data)

    def initialize(self):
        """The initialize step further initializes the Request by
        setting additional information in the ``data`` dict,
        registering plugins, and entryparsers.
        """
        data = self._request.get_data()
        py_http = self._request.get_http()
        config = self._request.get_configuration()

        # initialize the locale, if wanted (will silently fail if locale
        # is not available)
        if config.get('locale', None):
            try:
                locale.setlocale(locale.LC_ALL, config['locale'])
            except locale.Error:
                # invalid locale
                pass

        # initialize the tools module
        tools.initialize(config)

        data["pyblosxom_version"] = __version__
        data['pi_bl'] = ''

        # if the user specifies base_url in config, we use that.
        # otherwise we compose it from SCRIPT_NAME in the environment
        # or we leave it blank.
        if not "base_url" in config:
            if py_http.has_key('SCRIPT_NAME'):
                # allow http and https
                config['base_url'] = '%s://%s%s' % \
                                     (py_http['wsgi.url_scheme'],
                                      py_http['HTTP_HOST'],
                                      py_http['SCRIPT_NAME'])
            else:
                config["base_url"] = ""

        # take off the trailing slash for base_url
        if config['base_url'].endswith("/"):
            config['base_url'] = config['base_url'][:-1]

        data_dir = config["datadir"]
        if data_dir.endswith("/") or data_dir.endswith("\\"):
            data_dir = data_dir[:-1]
            config['datadir'] = data_dir

        # import and initialize plugins
        plugin_utils.initialize_plugins(config.get("plugin_dirs", []),
                                        config.get("load_plugins", None))

        # entryparser callback is run here first to allow other
        # plugins register what file extensions can be used
        data['extensions'] = tools.run_callback("entryparser",
                                                {'txt': blosxom_entry_parser},
                                                mappingfunc=lambda x, y: y,
                                                defaultfunc=lambda x: x)

    def cleanup(self):
        """This cleans up Pyblosxom after a run.

        This should be called when Pyblosxom has done everything it
        needs to do before exiting.
        """
        # log some useful stuff for debugging
        # this will only be logged if the log_level is "debug"
        log = tools.getLogger()
        response = self.get_response()
        log.debug("status = %s" % response.status)
        log.debug("headers = %s" % response.headers)

    def get_request(self):
        """Returns the Request object for this Pyblosxom instance.
        """
        return self._request

    getRequest = tools.deprecated_function(get_request)

    def get_response(self):
        """Returns the Response object associated with this Request.
        """
        return self._request.getResponse()

    getResponse = tools.deprecated_function(get_response)

    def run(self, static=False):
        """This is the main loop for Pyblosxom.  This method will run
        the handle callback to allow registered handlers to handle the
        request.  If nothing handles the request, then we use the
        ``default_blosxom_handler``.

        :param static: True if Pyblosxom should execute in "static rendering
                       mode" and False otherwise.
        """
        self.initialize()

        # buffer the input stream in a StringIO instance if dynamic
        # rendering is used.  This is done to have a known/consistent
        # way of accessing incoming data.
        if not static:
            self.get_request().buffer_input_stream()

        # run the start callback
        tools.run_callback("start", {'request': self._request})

        # allow anyone else to handle the request at this point
        handled = tools.run_callback("handle",
                                     {'request': self._request},
                                     mappingfunc=lambda x, y: x,
                                     donefunc=lambda x: x)

        if not handled == 1:
            blosxom_handler(self._request)

        # do end callback
        tools.run_callback("end", {'request': self._request})

        # we're done, clean up.
        # only call this if we're not in static rendering mode.
        if not static:
            self.cleanup()

    def run_callback(self, callback="help"):
        """This method executes the start callback (initializing
        plugins), executes the requested callback, and then executes
        the end callback.

        This is useful for scripts outside of Pyblosxom that need to
        do things inside of the Pyblosxom framework.

        If you want to run a callback from a plugin, use
        ``tools.run_callback`` instead.

        :param callback: the name of the callback to execute.

        :returns: the results of the callback.
        """
        self.initialize()

        # run the start callback
        tools.run_callback("start", {'request': self._request})

        # invoke all callbacks for the 'callback'
        handled = tools.run_callback(callback,
                                     {'request': self._request},
                                     mappingfunc=lambda x, y: x,
                                     donefunc=lambda x: x)

        # do end callback
        tools.run_callback("end", {'request': self._request})

        return handled

    runCallback = tools.deprecated_function(run_callback)

    def run_render_one(self, url, headers):
        """Renders a single page from the blog.

        :param url: the url to render--this has to be relative to the
                    base url for this blog.

        :param headers: True if you want headers to be rendered and
                        False if not.
        """
        self.initialize()

        config = self._request.get_configuration()

        if url.find("?") != -1:
            url = url[:url.find("?")]
            query = url[url.find("?") + 1:]
        else:
            query = ""

        url = url.replace(os.sep, "/")
        response = tools.render_url(config, url, query)
        if headers:
            response.send_headers(sys.stdout)
        response.send_body(sys.stdout)

        print response.read()

        # we're done, clean up
        self.cleanup()

    def run_static_renderer(self, incremental=False):
        """This will go through all possible things in the blog and
        statically render everything to the ``static_dir`` specified
        in the config file.

        This figures out all the possible ``path_info`` settings and
        calls ``self.run()`` a bazillion times saving each file.

        :param incremental: Whether (True) or not (False) to
                            incrementally render the pages.  If we're
                            incrementally rendering pages, then we
                            render only the ones that have changed.
        """
        self.initialize()

        config = self._request.get_configuration()
        data = self._request.get_data()
        print "Performing static rendering."
        if incremental:
            print "Incremental is set."

        static_dir = config.get("static_dir", "")
        data_dir = config["datadir"]

        if not static_dir:
            print "Error: You must set static_dir in your config file."
            return 0

        flavours = config.get("static_flavours", ["html"])
        index_flavours = config.get("static_index_flavours", ["html"])

        render_me = []

        month_names = config.get("static_monthnames", True)
        month_numbers = config.get("static_monthnumbers", False)
        year_indexes = config.get("static_yearindexes", True)

        dates = {}
        categories = {}

        # first we handle entries and categories
        listing = tools.walk(self._request, data_dir)

        for mem in listing:
            # skip the ones that have bad extensions
            ext = mem[mem.rfind(".") + 1:]
            if not ext in data["extensions"].keys():
                continue

            # grab the mtime of the entry file
            mtime = time.mktime(tools.filestat(self._request, mem))

            # remove the datadir from the front and the bit at the end
            mem = mem[len(data_dir):mem.rfind(".")]

            # this is the static filename
            fn = os.path.normpath(static_dir + mem)

            # grab the mtime of one of the statically rendered file
            try:
                smtime = os.stat(fn + "." + flavours[0])[8]
            except:
                smtime = 0

            # if the entry is more recent than the static, we want to
            # re-render
            if smtime < mtime or not incremental:

                # grab the categories
                temp = os.path.dirname(mem).split(os.sep)
                for i in range(len(temp) + 1):
                    p = os.sep.join(temp[0:i])
                    categories[p] = 0

                # grab the date
                mtime = time.localtime(mtime)
                year = time.strftime("%Y", mtime)
                month = time.strftime("%m", mtime)
                day = time.strftime("%d", mtime)

                if year_indexes:
                    dates[year] = 1

                if month_numbers:
                    dates[year + "/" + month] = 1
                    dates[year + "/" + month + "/" + day] = 1

                if month_names:
                    monthname = tools.num2month[month]
                    dates[year + "/" + monthname] = 1
                    dates[year + "/" + monthname + "/" + day] = 1

                # toss in the render queue
                for f in flavours:
                    render_me.append((mem + "." + f, ""))

        print "rendering %d entries." % len(render_me)

        # handle categories
        categories = categories.keys()
        categories.sort()

        # if they have stuff in their root category, it'll add a "/"
        # to the category list and we want to remove that because it's
        # a duplicate of "".
        if "/" in categories:
            categories.remove("/")

        print "rendering %d category indexes." % len(categories)

        for mem in categories:
            mem = os.path.normpath(mem + "/index.")
            for f in index_flavours:
                render_me.append((mem + f, ""))

        # now we handle dates
        dates = dates.keys()
        dates.sort()

        dates = ["/" + d for d in dates]

        print "rendering %d date indexes." % len(dates)

        for mem in dates:
            mem = os.path.normpath(mem + "/index.")
            for f in index_flavours:
                render_me.append((mem + f, ""))

        # now we handle arbitrary urls
        additional_stuff = config.get("static_urls", [])
        print "rendering %d arbitrary urls." % len(additional_stuff)

        for mem in additional_stuff:
            if mem.find("?") != -1:
                url = mem[:mem.find("?")]
                query = mem[mem.find("?") + 1:]
            else:
                url = mem
                query = ""

            render_me.append((url, query))

        # now we pass the complete render list to all the plugins via
        # cb_staticrender_filelist and they can add to the filelist
        # any (url, query) tuples they want rendered.
        print "(before) building %s files." % len(render_me)
        tools.run_callback("staticrender_filelist",
                           {'request': self._request,
                            'filelist': render_me,
                            'flavours': flavours,
                            'incremental': incremental})

        render_me = sorted(set(render_me))

        print "building %s files." % len(render_me)

        for url, q in render_me:
            url = url.replace(os.sep, "/")
            print "rendering '%s' ..." % url

            tools.render_url_statically(dict(config), url, q)

        # we're done, clean up
        self.cleanup()


Pyblosxom = Pyblosxom


class PyblosxomWSGIApp:
    """This class is the WSGI application for Pyblosxom.
    """

    def __init__(self, environ=None, start_response=None, configini=None):
        """
        Make WSGI app for Pyblosxom.

        :param environ: FIXME

        :param start_response: FIXME

        :param configini: Dict encapsulating information from a
                          ``config.ini`` file or any other property
                          file that will override the ``config.py``
                          file.
        """
        self.environ = environ
        self.start_response = start_response

        if configini is None:
            configini = {}

        _config = tools.convert_configini_values(configini)

        import config

        self.config = dict(config.py)

        self.config.update(_config)
        if "codebase" in _config:
            sys.path.insert(0, _config["codebase"])

    def run_pyblosxom(self, env, start_response):
        """
        Executes a single run of Pyblosxom wrapped in the crash handler.
        """
        try:
            # ensure that PATH_INFO exists. a few plugins break if this is
            # missing.
            if "PATH_INFO" not in env:
                env["PATH_INFO"] = ""

            p = Pyblosxom(dict(self.config), env)
            p.run()

            response = p.get_response()

        except Exception:
            ch = crashhandling.CrashHandler(True, env)
            response = ch.handle_by_response(*sys.exc_info())

        start_response(response.status, list(response.headers.items()))
        response.seek(0)
        return response.read()

    def __call__(self, env, start_response):
        return [self.run_pyblosxom(env, start_response)]

    def __iter__(self):
        yield self.run_pyblosxom(self.environ, self.start_response)


# Do this for historical reasons
PyblosxomWSGIApp = PyblosxomWSGIApp


def pyblosxom_app_factory(global_config, **local_config):
    """App factory for paste.

    :returns: WSGI application
    """
    conf = global_config.copy()
    conf.update(local_config)
    conf.update(dict(local_config=local_config, global_config=global_config))

    if "configpydir" in conf:
        sys.path.insert(0, conf["configpydir"])

    return PyblosxomWSGIApp(configini=conf)


class EnvDict(dict):
    """Wrapper around a dict to provide a backwards compatible way to
    get the ``form`` with syntax as::

        request.get_http()['form']

    instead of::

        request.get_form()
    """

    def __init__(self, request, env):
        """Wraps an environment (which is a dict) and a request.

        :param request: the Request object for this request.
        :param env: the environment dict for this request.
        """
        dict.__init__(self)
        self._request = request
        self.update(env)

    def __getitem__(self, key):
        """If the key argument is ``form``, we return
        ``_request.get_form()``.  Otherwise this returns the item for
        that key in the wrapped dict.
        """
        if key == "form":
            return self._request.get_form()

        return dict.__getitem__(self, key)


class Request(object):
    """
    This class holds the Pyblosxom request.  It holds configuration
    information, HTTP/CGI information, and data that we calculate and
    transform over the course of execution.

    There should be only one instance of this class floating around
    and it should get created by ``pyblosxom.cgi`` and passed into the
    Pyblosxom instance which will do further manipulation on the
    Request instance.
    """

    def __init__(self, config, environ, data):
        """Sets configuration and environment.

        Creates the Response object which handles all output related
        functionality.

        :param config: dict containing configuration variables.
        :param environ: dict containing environment variables.
        :param data: dict containing data variables.
        """
        # this holds configuration data that the user changes in
        # config.py
        self._configuration = config

        # this holds HTTP/CGI oriented data specific to the request
        # and the environment in which the request was created
        self._http = EnvDict(self, environ)

        # this holds run-time data which gets created and transformed
        # by pyblosxom during execution
        if data is None:
            self._data = dict()
        else:
            self._data = data

        # this holds the input stream.  initialized for dynamic
        # rendering in Pyblosxom.run.  for static rendering there is
        # no input stream.
        self._in = StringIO()

        # copy methods to the Request object.
        self.read = self._in.read
        self.readline = self._in.readline
        self.readlines = self._in.readlines
        self.seek = self._in.seek
        self.tell = self._in.tell

        # this holds the FieldStorage instance.
        # initialized when request.get_form is called the first time
        self._form = None

        self._response = None

        # create and set the Response
        self.setResponse(Response(self))

    def __iter__(self):
        """
        Can't copy the __iter__ method over from the StringIO instance
        cause iter looks for the method in the class instead of the
        instance.

        See http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/252151
        """
        return self._in

    def buffer_input_stream(self):
        """
        Buffer the input stream in a StringIO instance.  This is done
        to have a known/consistent way of accessing incoming data.
        For example the input stream passed by mod_python does not
        offer the same functionality as ``sys.stdin``.
        """
        # TODO: tests on memory consumption when uploading huge files
        py_http = self.get_http()
        winput = py_http['wsgi.input']
        method = py_http["REQUEST_METHOD"]

        # there's no data on stdin for a GET request.  pyblosxom
        # will block indefinitely on the read for a GET request with
        # thttpd.
        if method != "GET":
            try:
                length = int(py_http.get("CONTENT_LENGTH", 0))
            except ValueError:
                length = 0

            if length > 0:
                self._in.write(winput.read(length))
                # rewind to start
                self._in.seek(0)

    def set_response(self, response):
        """Sets the Response object.
        """
        self._response = response
        # for backwards compatibility
        self.get_configuration()['stdoutput'] = response

    setResponse = tools.deprecated_function(set_response)

    def get_response(self):
        """Returns the Response for this request.
        """
        return self._response

    getResponse = tools.deprecated_function(get_response)

    def _getform(self):
        form = cgi.FieldStorage(fp=self._in,
                                environ=self._http,
                                keep_blank_values=0)
        # rewind the input buffer
        self._in.seek(0)
        return form

    def get_form(self):
        """Returns the form data submitted by the client.  The
        ``form`` instance is created only when requested to prevent
        overhead and unnecessary consumption of the input stream.

        :returns: a ``cgi.FieldStorage`` instance.
        """
        if self._form is None:
            self._form = self._getform()
        return self._form

    getForm = tools.deprecated_function(get_form)

    def get_configuration(self):
        """Returns the *actual* configuration dict.  The configuration
        dict holds values that the user sets in their ``config.py``
        file.

        Modifying the contents of the dict will affect all downstream
        processing.
        """
        return self._configuration

    getConfiguration = tools.deprecated_function(get_configuration)

    def get_http(self):
        """Returns the *actual* http dict.  Holds HTTP/CGI data
        derived from the environment of execution.

        Modifying the contents of the dict will affect all downstream
        processing.
        """
        return self._http

    getHttp = tools.deprecated_function(get_http)

    def get_data(self):
        """Returns the *actual* data dict.  Holds run-time data which
        is created and transformed by pyblosxom during execution.

        Modifying the contents of the dict will affect all downstream
        processing.
        """
        return self._data

    getData = tools.deprecated_function(get_data)

    def add_http(self, d):
        """Takes in a dict and adds/overrides values in the existing
        http dict with the new values.
        """
        self._http.update(d)

    addHttp = tools.deprecated_function(add_http)

    def add_data(self, d):
        """Takes in a dict and adds/overrides values in the existing
        data dict with the new values.
        """
        self._data.update(d)

    addData = tools.deprecated_function(add_data)

    def add_configuration(self, newdict):
        """Takes in a dict and adds/overrides values in the existing
        configuration dict with the new values.
        """
        self._configuration.update(newdict)

    addConfiguration = tools.deprecated_function(add_configuration)

    def __getattr__(self, name):
        if name in ["config", "configuration", "conf"]:
            return self._configuration

        if name == "data":
            return self._data

        if name == "http":
            return self._http

        raise AttributeError, name

    def __repr__(self):
        return "Request"


class Response(object):
    """Response class to handle all output related tasks in one place.

    This class is basically a wrapper arround a ``StringIO`` instance.
    It also provides methods for managing http headers.
    """

    def __init__(self, request):
        """Sets the ``Request`` object that leaded to this response.
        Creates a ``StringIO`` that is used as a output buffer.
        """
        self._request = request
        self._out = StringIO()
        self._headers_sent = False
        self.headers = {}
        self.status = "200 OK"

        self.close = self._out.close
        self.flush = self._out.flush
        self.read = self._out.read
        self.readline = self._out.readline
        self.readlines = self._out.readlines
        self.seek = self._out.seek
        self.tell = self._out.tell
        self.write = self._out.write
        self.writelines = self._out.writelines

    def __iter__(self):
        """Can't copy the ``__iter__`` method over from the
        ``StringIO`` instance because iter looks for the method in the
        class instead of the instance.

        See
        http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/252151
        """
        return self._out

    def set_status(self, status):
        """Sets the status code for this response.  The status should
        be a valid HTTP response status.

        Examples:

        >>> resp = Response('some fake request')
        >>> resp.set_status("200 OK")
        >>> resp.set_status("404 Not Found")

        :param status: the status string.
        """
        self.status = status

    setStatus = tools.deprecated_function(set_status)

    def get_status(self):
        """Returns the status code and message of this response.
        """
        return self.status

    def add_header(self, key, value):
        """Populates the HTTP header with lines of text.  Sets the
        status code on this response object if the given argument list
        contains a 'Status' header.

        Example:

        >>> resp = Response('some fake request')
        >>> resp.add_header("Content-type", "text/plain")
        >>> resp.add_header("Content-Length", "10500")

        :raises ValueError: This happens when the parameters are
                            not correct.
        """
        key = key.strip()
        if key.find(' ') != -1 or key.find(':') != -1:
            raise ValueError, 'There should be no spaces in header keys'
        value = value.strip()
        if key.lower() == "status":
            self.setStatus(str(value))
        else:
            self.headers.update({key: str(value)})

    addHeader = tools.deprecated_function(add_header)

    def get_headers(self):
        """Returns the headers.
        """
        return self.headers

    getHeaders = tools.deprecated_function(get_headers)

    def send_headers(self, out):
        """Send HTTP Headers to the given output stream.

        .. Note::

            This prints the headers and then the ``\\n\\n`` that
            separates headers from the body.

        :param out: The file-like object to print headers to.
        """
        out.write("Status: %s\n" % self.status)
        out.write('\n'.join(['%s: %s' % (hkey, self.headers[hkey])
                             for hkey in self.headers.keys()]))
        out.write('\n\n')
        self._headers_sent = True

    sendHeaders = tools.deprecated_function(send_headers)

    def send_body(self, out):
        """Send the response body to the given output stream.

        :param out: the file-like object to print the body to.
        """
        self.seek(0)
        try:
            out.write(self.read())
        except IOError:
            # this is usually a Broken Pipe because the client dropped the
            # connection.  so we skip it.
            pass

    sendBody = tools.deprecated_function(send_body)


def run_pyblosxom():
    """Executes Pyblosxom either as a commandline script or CGI
    script.
    """
    from config import py as cfg

    env = {}

    # if there's no REQUEST_METHOD, then this is being run on the
    # command line and we should execute the command_line_handler.
    if not "REQUEST_METHOD" in os.environ:
        from Pyblosxom.commandline import command_line_handler

        if len(sys.argv) <= 1:
            sys.argv.append("test")

        sys.exit(command_line_handler("pyblosxom.cgi", sys.argv))

    # names taken from wsgi instead of inventing something new
    env['wsgi.input'] = sys.stdin
    env['wsgi.errors'] = sys.stderr

    # figure out what the protocol is for the wsgi.url_scheme
    # property.  we look at the base_url first and if there's nothing
    # set there, we look at environ.
    if 'base_url' in cfg:
        env['wsgi.url_scheme'] = cfg['base_url'][:cfg['base_url'].find("://")]

    else:
        if os.environ.get("HTTPS", "off") in ("on", "1"):
            env["wsgi.url_scheme"] = "https"

        else:
            env['wsgi.url_scheme'] = "http"

    try:
        # try running as a WSGI-CGI
        from wsgiref.handlers import CGIHandler

        CGIHandler().run(PyblosxomWSGIApp())

    except ImportError:
        # run as a regular CGI

        if os.environ.get("HTTPS") in ("yes", "on", "1"):
            env['wsgi.url_scheme'] = "https"

        for mem in ["HTTP_HOST", "HTTP_USER_AGENT", "HTTP_REFERER",
                    "PATH_INFO", "QUERY_STRING", "REMOTE_ADDR",
                    "REQUEST_METHOD", "REQUEST_URI", "SCRIPT_NAME",
                    "HTTP_IF_NONE_MATCH", "HTTP_IF_MODIFIED_SINCE",
                    "HTTP_COOKIE", "CONTENT_LENGTH", "CONTENT_TYPE",
                    "HTTP_ACCEPT", "HTTP_ACCEPT_ENCODING"]:
            env[mem] = os.environ.get(mem, "")

        p = Pyblosxom(dict(cfg), env)

        p.run()
        response = p.get_response()
        response.send_headers(sys.stdout)
        response.send_body(sys.stdout)

########NEW FILE########
__FILENAME__ = base
#######################################################################
# This file is part of Pyblosxom.
#
# Copyright (C) 2003-2011 by the Pyblosxom team.  See AUTHORS.
#
# Pyblosxom is distributed under the MIT license.  See the file
# LICENSE for distribution details.
#######################################################################

"""
The is the base renderer module.  If you were to dislike the blosxom
renderer and wanted to build a renderer that used a different
templating system, you would extend the RendererBase class and
implement the functionality required by the other rendering system.

For examples, look at the BlosxomRenderer and the Renderer in the
debug module.
"""

import sys
import time

from Pyblosxom import tools


class RendererBase:
    """
    Pyblosxom core handles the Input and Process of the system and
    passes the result of the process to the Renderers for output. All
    renderers are child classes of RendererBase. RenderBase will
    contain the public interfaces for all Renderer object.
    """
    def __init__(self, request, stdoutput=sys.stdout):
        """
        Constructor: Initializes the Renderer

        :param request: The ``Pyblosxom.pyblosxom.Request`` object
        :param stdoutput: File like object to print to.
        """
        self._request = request

        # this is a list of tuples of the form (key, value)
        self._header = []

        self._out = stdoutput
        self._content = None
        self._content_mtime = None
        self._needs_content_type = 1
        self.rendered = None

    def write(self, data):
        """
        Convenience method for programs to use instead of accessing
        self._out.write()

        Other classes can override this if there is a unique way to
        write out data, for example, a two stream output, e.g. one
        output stream and one output log stream.

        Another use for this could be a plugin that writes out binary
        files, but because renderers and other frameworks may probably
        not want you to write to ``stdout`` directly, this method
        assists you nicely. For example::

            def cb_start(args):
                req = args['request']
                renderer = req['renderer']

                if reqIsGif and gifFileExists(theGifFile):
                    # Read the file
                    data = open(theGifFile).read()

                    # Modify header
                    renderer.addHeader('Content-type', 'image/gif')
                    renderer.addHeader('Content-Length', len(data))
                    renderer.showHeaders()

                    # Write to output
                    renderer.write(data)

                    # Tell pyblosxom not to render anymore as data is
                    # processed already
                    renderer.rendered = 1

        This simple piece of pseudo-code explains what you could do
        with this method, though I highly don't recommend this, unless
        pyblosxom is running continuously.

        :param data: Piece of string you want printed
        """
        self._out.write(data)

    def add_header(self, *args):
        """
        Populates the HTTP header with lines of text

        :param args: Paired list of headers

        :raises ValueError: This happens when the parameters are not
                            correct
        """
        args = list(args)
        if len(args) % 2 != 0:
            raise ValueError('Headers recieved are not in the correct form')

        while args:
            key = args.pop(0).strip()
            if key.find(' ') != -1 or key.find(':') != -1:
                raise ValueError('There should be no spaces in header keys')
            value = args.pop(0).strip()
            self._header.append( (key, value) )

    addHeader = tools.deprecated_function(add_header)

    def set_content(self, content):
        """
        Sets the content.  The content can be any of the following:

        * dict
        * list of entries

        :param content: the content to be displayed
        """
        self._content = content
        if isinstance(self._content, dict):
            mtime = self._content.get("mtime", time.time())
        elif isinstance(self._content, list):
            mtime = self._content[0].get("mtime", time.time())
        else:
            mtime = time.time()
        self._content_mtime = mtime

    setContent = tools.deprecated_function(set_content)

    def get_content(self):
        """
        Return the content field

        This is exposed for blosxom callbacks.

        :returns: content
        """
        return self._content

    getContent = tools.deprecated_function(get_content)

    def needs_content_type(self, flag):
        """
        Use the renderer to determine 'Content-Type: x/x' default is
        to use the renderer for Content-Type, set flag to None to
        indicate no Content-Type generation.

        :param flag: True of false value
        """
        self._needs_content_type = flag

    needsContentType = tools.deprecated_function(needs_content_type)

    def show_headers(self):
        """
        Updated the headers of the
        ``Response<Pyblosxom.pyblosxom.Response>`` instance.

        This is here for backwards compatibility.
        """
        response = self._request.getResponse()
        for k, v in self._header:
            response.addHeader(k, v)

    showHeaders = tools.deprecated_function(show_headers)

    def render(self, header=True):
        """
        Do final rendering.

        :param header: whether (True) or not (False) to show the
                       headers
        """
        if header:
            if self._header:
                self.show_headers()
            else:
                self.add_header('Content-Type', 'text/plain')
                self.show_headers()

        if self._content:
            self.write(self._content)
        self.rendered = 1


class Renderer(RendererBase):
    """
    This is a null renderer.
    """
    pass

########NEW FILE########
__FILENAME__ = blosxom
#######################################################################
# This file is part of Pyblosxom.
#
# Copyright (C) 2003-2011 by the Pyblosxom team.  See AUTHORS.
#
# Pyblosxom is distributed under the MIT license.  See the file
# LICENSE for distribution details.
#######################################################################

"""
This is the default blosxom renderer.  It tries to match the behavior
of the blosxom renderer.
"""

import os
import sys

from Pyblosxom import tools
from Pyblosxom.renderers.base import RendererBase


class NoSuchFlavourException(Exception):
    """
    This exception gets thrown when the flavour requested is not
    available in this blog.
    """
    pass


def get_included_flavour(taste):
    """
    Pyblosxom comes with flavours in taste.flav directories in the flavours
    subdirectory of the Pyblosxom package.  This method pulls the template
    files for the associated taste (assuming it exists) or None if it
    doesn't.

    :param taste: The name of the taste.  e.g. "html", "rss", ...

    :returns: A dict of template type to template file or None
    """
    path = __file__[:__file__.rfind(os.sep)]
    path = path[:path.rfind(os.sep)+1] + "flavours" + os.sep

    path = path + taste + ".flav"

    if os.path.isdir(path):
        template_files = os.listdir(path)
        template_d = {}
        for mem in template_files:
            name, ext = os.path.splitext(mem)
            if ext not in ["." + taste, ""] or name.startswith("."):
                continue
            template_d[name] = os.path.join(path, mem)
        return template_d

    return None


def get_flavour_from_dir(path, taste):
    """
    Tries to get the template files for the flavour of a certain
    taste (html, rss, atom10, ...) in a directory.  The files could
    be in the directory or in a taste.flav subdirectory.

    :param path: the path of the directory to look for the flavour
                 templates in

    :param taste: the flavour files to look for (e.g. html, rss, atom10, ...)

    :returns: the map of template name to template file path
    """
    template_d = {}

    # if we have a taste.flav directory, we check there
    if os.path.isdir(path + os.sep + taste + ".flav"):
        newpath = path + os.sep + taste + ".flav"
        template_files = os.listdir(newpath)
        for mem in template_files:
            name, ext = os.path.splitext(mem)
            if ext not in ["." + taste, ""]:
                continue
            template_d[name] = os.path.join(path + os.sep + taste + ".flav",
                                            mem)
        return template_d

    # now we check the directory itself for flavour templates
    template_files = os.listdir(path)
    for mem in template_files:
        if not mem.endswith("." + taste):
            continue
        template_d[os.path.splitext(mem)[0]] = path + os.sep + mem

    if template_d:
        return template_d

    return None


class BlosxomRenderer(RendererBase):
    """
    This is the default blosxom renderer.  It tries to match the behavior
    of the blosxom renderer.
    """
    def __init__(self, request, stdoutput=sys.stdout):
        RendererBase.__init__(self, request, stdoutput)
        config = request.get_configuration()
        self._request = request
        self.flavour = None

    def get_parse_vars(self):
        """Returns a dict starting with standard filters, config
        information, then data information.  This allows vars
        to override each other correctly.  For example, plugins
        should be adding to the data dict which will override
        stuff in the config dict.
        """
        parsevars = dict(tools.STANDARD_FILTERS)
        parsevars.update(self._request.config)
        parsevars.update(self._request.data)
        return parsevars

    def get_flavour(self, taste='html'):
        """
        This retrieves all the template files for a given flavour
        taste.  This will first pull the templates for the default
        flavour of this taste if there are any.  Then it looks at
        EITHER the configured datadir OR the flavourdir (if
        configured).  It'll go through directories overriding the
        template files it has already picked up descending the
        category path of the Pyblosxom request.

        For example, if the user requested the ``html`` flavour and is
        looking at an entry in the category ``dev/pyblosxom``, then
        ``get_flavour`` will:

        1. pick up the flavour files in the default html flavour
        2. start in EITHER datadir OR flavourdir (if configured)
        3. override the default html flavour files with html flavour
           files in this directory or in ``html.flav/`` subdirectory
        4. override the html flavour files it's picked up so far
           with html files in ``dev/`` or ``dev/html.flav/``
        5. override the html flavour files it's picked up so far
           with html files in ``dev/pyblosxom/`` or
           ``dev/pyblosxom/html.flav/``

        If it doesn't find any flavour files at all, then it returns
        None which indicates the flavour doesn't exist in this blog.

        :param taste: the taste to retrieve flavour files for.

        :returns: mapping of template name to template file data
        """
        data = self._request.get_data()
        config = self._request.get_configuration()
        datadir = config["datadir"]

        # if they have flavourdir set, then we look there.  otherwise
        # we look in the datadir.
        flavourdir = config.get("flavourdir", datadir)

        # first we grab the flavour files for the included flavour (if
        # we have one).
        template_d = get_included_flavour(taste)
        if not template_d:
            template_d = {}

        pathinfo = list(data["path_info"])

        # check the root of flavourdir for templates
        new_files = get_flavour_from_dir(flavourdir, taste)
        if new_files:
            template_d.update(new_files)

        # go through all the directories from the flavourdir all
        # the way up to the root_datadir.  this way template files
        # can override template files in parent directories.
        while len(pathinfo) > 0:
            flavourdir = os.path.join(flavourdir, pathinfo.pop(0))
            if os.path.isfile(flavourdir):
                break

            if not os.path.isdir(flavourdir):
                break

            new_files = get_flavour_from_dir(flavourdir, taste)
            if new_files:
                template_d.update(new_files)

        # if we still haven't found our flavour files, we raise an exception
        if not template_d:
            raise NoSuchFlavourException("Flavour '%s' does not exist." % taste)

        for k in template_d.keys():
            try:
                flav_template = open(template_d[k]).read()
                template_d[k] = flav_template
            except (OSError, IOError):
                pass

        return template_d

    def render_content(self, content):
        """
        Processes the content for the story portion of a page.

        :param content: the content to be rendered

        :returns: the content string
        """
        data = self._request.get_data()

        outputbuffer = []

        if callable(content):
            # if the content is a callable function, then we just spit out
            # whatever it returns as a string
            outputbuffer.append(content())

        elif isinstance(content, dict):
            # if the content is a dict, then we parse it as if it were an
            # entry--except it's distinctly not an EntryBase derivative
            var_dict = self.get_parse_vars()
            var_dict.update(content)

            output = tools.parse(self._request, var_dict, self.flavour['story'])
            outputbuffer.append(output)

        elif isinstance(content, list):
            if len(content) > 0:
                current_date = content[0]["date"]

                if current_date and "date_head" in self.flavour:
                    parse_vars = self.get_parse_vars()
                    parse_vars.update({"date": current_date,
                                       "yr": content[0]["yr"],
                                       "mo": content[0]["mo"],
                                       "da": content[0]["da"]})
                    outputbuffer.append(
                        self.render_template(parse_vars, "date_head"))

                for entry in content:
                    if entry["date"] and entry["date"] != current_date:
                        if "date_foot" in self.flavour:
                            parse_vars = self.get_parse_vars()
                            parse_vars.update({"date": current_date,
                                               "yr": content[0]["yr"],
                                               "mo": content[0]["mo"],
                                               "da": content[0]["da"]})

                            outputbuffer.append(
                                self.render_template(parse_vars, "date_foot"))

                        if "date_head" in self.flavour:
                            current_date = entry["date"]
                            parse_vars = self.get_parse_vars()
                            parse_vars.update({"date": current_date,
                                               "yr": content[0]["yr"],
                                               "mo": content[0]["mo"],
                                               "da": content[0]["da"]})
                            outputbuffer.append(
                                self.render_template(parse_vars, "date_head"))

                    if data['content-type'] == 'text/plain':
                        s = tools.Stripper()
                        s.feed(entry.get_data())
                        s.close()
                        p = ['  ' + line for line in s.gettext().split('\n')]
                        entry.set_data('\n'.join(p))

                    parse_vars = self.get_parse_vars()
                    parse_vars.update(entry)

                    outputbuffer.append(
                        self.render_template(parse_vars, "story", override=1))

                    args = {"entry": parse_vars, "template": ""}
                    args = self._run_callback("story_end", args)
                    outputbuffer.append(args["template"])

                if current_date and "date_foot" in self.flavour:
                    parse_vars = self.get_parse_vars()
                    parse_vars.update({"date": current_date})
                    outputbuffer.append(
                        self.render_template(parse_vars, "date_foot"))

        return outputbuffer

    renderContent = tools.deprecated_function(render_content)

    def render(self, header=True):
        """
        Figures out flavours and such and then renders the content according
        to which flavour we're using.

        :param header: whether (True) or not (False) to render the HTTP headers
        """
        # if we've already rendered, then we don't want to do so again
        if self.rendered:
            return

        data = self._request.get_data()
        config = self._request.get_configuration()

        try:
            self.flavour = self.get_flavour(data.get("flavour", "html"))

        except NoSuchFlavourException, nsfe:
            error_msg = str(nsfe)
            try:
                self.flavour = self.get_flavour("error")
            except NoSuchFlavourException:
                self.flavour = get_included_flavour("error")
                error_msg += "  And your error flavour doesn't exist, either."

            resp = self._request.getResponse()
            resp.set_status("404 Not Found")
            self._content = {"title": "HTTP 404: Flavour error",
                             "body": error_msg}

        data['content-type'] = self.flavour['content_type'].strip()
        if header:
            if self._needs_content_type and data['content-type'] != "":
                self.add_header('Content-type', '%(content-type)s' % data)

            self.show_headers()

        if self._content:
            if "head" in self.flavour:
                self.write(self.render_template(self.get_parse_vars(), "head"))
            if "story" in self.flavour:
                content = self.render_content(self._content)
                for i, mem in enumerate(content):
                    if isinstance(mem, unicode):
                        content[i] = mem.encode("utf-8")
                content = "".join(content)
                self.write(content)
            if "foot" in self.flavour:
                self.write(self.render_template(self.get_parse_vars(), "foot"))

        self.rendered = 1

    def render_template(self, entry, template_name, override=0):
        """
        Find the flavour template for template_name, run any blosxom
        callbacks, substitute entry into it and render the template.

        If the entry has a ``template_name`` property and override is
        True (this happens in the story template), then we'll use that
        template instead.

        :param entry: the entry/variable-dict to use for expanding variables

        :param template_name: template name (gets looked up in self.flavour)

        :param override: whether (True) or not (False) this template can
            be overriden with the ``template_name`` value in the entry
        """
        template = ""
        if override:
            # here we do a quick override...  if the entry has a
            # template field we use that instead of the template_name
            # argument passed in.
            actual_template_name = entry.get("template_name", template_name)
            template = self.flavour.get(actual_template_name, '')

        if not template:
            template = self.flavour.get(template_name, '')

        # we run this through the regular callbacks
        args = self._run_callback(template_name,
                                  {"entry": entry, "template": template})

        template = args["template"]

        # FIXME - the finaltext.replace(...) below causes \$ to get
        # unescaped in title and body text which is wrong.  this
        # fix alleviates that somewhat, but there are still edge
        # cases regarding function data.  need a real template
        # engine with a real parser here.
        entry = dict(args["entry"])
        for k, v in entry.items():
            if isinstance(v, basestring):
                entry[k] = v.replace(r"\$", r"\\$")

        finaltext = tools.parse(self._request, entry, template)
        return finaltext.replace(r'\$', '$')

    renderTemplate = tools.deprecated_function(render_template)

    def _run_callback(self, chain, input):
        """
        Makes calling blosxom callbacks a bit easier since they all
        have the same mechanics.  This function merely calls
        run_callback with the arguments given and a mappingfunc.

        The mappingfunc copies the ``template`` value from the output to
        the input for the next function.

        Refer to run_callback for more details.
        """
        input.update({"renderer": self})
        input.update({"request": self._request})

        return tools.run_callback(chain, input,
                                  mappingfunc=lambda x,y: x,
                                  defaultfunc=lambda x:x)

    def output_template(self, output, entry, template_name):
        """
        Deprecated.  Here for backwards compatibility.
        """
        output.append(self.render_template(entry, template_name))

    outputTemplate = tools.deprecated_function(output_template)


class Renderer(BlosxomRenderer):
    pass

########NEW FILE########
__FILENAME__ = debug
#######################################################################
# This file is part of Pyblosxom.
#
# Copyright (C) 2003-2011 by the Pyblosxom team.  See AUTHORS.
#
# Pyblosxom is distributed under the MIT license.  See the file
# LICENSE for distribution details.
#######################################################################

"""
This is the debug renderer.  This is very useful for debugging plugins
and templates.
"""

from Pyblosxom.renderers.base import RendererBase
from Pyblosxom import tools, plugin_utils


def escv(s):
    """
    Takes in a value.  If it's not a string, we repr it and turn it into
    a string.  Then we escape it so it can be printed in HTML safely.

    :param s: any value

    :returns: a safe-to-print-in-html string representation of the value
    """
    if not s:
        return ""

    if not isinstance(s, str):
        s = repr(s)

    return tools.escape_text(s)


def print_map(printfunc, keymap):
    """
    Takes a map of keys to values and applies the function f to a pretty
    printed version of each key/value pair.

    :param printfunc: function for printing

    :param keymap: a mapping of key/value pairs
    """
    keys = keymap.keys()
    keys.sort()
    for key in keys:
        printfunc("<font color=\"#0000ff\">%s</font> -&gt; %s\n" % \
                  (escv(key), escv(keymap[key])))


class Renderer(RendererBase):
    """
    This is the debug renderer.  This is very useful for debugging
    plugins and templates.
    """
    def render(self, header=True):
        """
        Renders a Pyblosxom request after we've gone through all the
        motions of converting data and getting entries to render.

        :param header: either prints (True) or does not print (True)
                       the http headers.
        """
        pyhttp = self._request.get_http()
        config = self._request.get_configuration()
        data = self._request.get_data()
        printout = self.write

        hbar = "------------------------------------------------------\n"


        if header:
            self.add_header('Content-type', 'text/html')
            self.show_headers()

        printout("<html>")
        printout("<body>")
        printout("<pre>")
        printout("Welcome to debug mode!\n")
        printout("You requested the %(flavour)s flavour.\n" % data)

        printout(hbar)
        printout("HTTP return headers:\n")
        printout(hbar)
        for k, v in self._header:
            printout("<font color=\"#0000ff\">%s</font> -&gt; %s\n" % \
                     (escv(k), escv(v)))

        printout(hbar)
        printout("The OS environment contains:\n")
        printout(hbar)
        import os
        print_map(printout, os.environ)

        printout(hbar)
        printout("Plugins:\n")
        printout(hbar)
        printout("Plugins that loaded:\n")
        if plugin_utils.plugins:
            for plugin in plugin_utils.plugins:
                printout(" * " + escv(plugin) + "\n")
        else:
            printout("None\n")

        printout("\n")

        printout("Plugins that didn't load:\n")
        if plugin_utils.bad_plugins:
            for plugin, exc in plugin_utils.bad_plugins:
                exc = "    " + "\n    ".join(exc.splitlines()) + "\n"
                printout(" * " + escv(plugin) + "\n")
                printout(escv(exc))
        else:
            printout("None\n")

        printout(hbar)
        printout("Request.get_http() dict contains:\n")
        printout(hbar)
        print_map(printout, pyhttp)

        printout(hbar)
        printout("Request.get_configuration() dict contains:\n")
        printout(hbar)
        print_map(printout, config)

        printout(hbar)
        printout("Request.get_data() dict contains:\n")
        printout(hbar)
        print_map(printout, data)

        printout(hbar)
        printout("Entries to process:\n")
        printout(hbar)
        for content in self._content:
            if not isinstance(content, str):
                printout("%s\n" %
                         escv(content.get('filename', 'No such file\n')))

        printout(hbar)
        printout("Entries processed:\n")
        printout(hbar)
        for content in self._content:
            if not isinstance(content, str):
                printout(hbar)
                emsg = escv(content.get('filename', 'No such file\n'))
                printout("Items for %s:\n" % emsg)
                printout(hbar)
                print_map(printout, content)

        printout(hbar)
        if not config.has_key("cacheDriver"):
            printout("No cache driver configured.")
        else:
            printout("Cached Titles:\n")
            printout(hbar)
            cache = tools.get_cache(self._request)
            for content in self._content:
                if not isinstance(content, str):
                    filename = content['filename']

                    if cache.has_key(filename):
                        printout("%s\n" % escv(cache[filename]['title']))
                    cache.close()

            printout(hbar)
            printout("Cached Entry Bodies:\n")
            printout(hbar)
            for content in self._content:
                if not isinstance(content, str):
                    filename = content['filename']
                    if cache.has_key(filename):
                        printout("%s\n" % escv(cache[filename]['title']))
                        printout(hbar.replace("-", "="))
                        printout("%s\n" % escv(cache[filename]['body']))
                    else:
                        printout("Contents of %s is not cached\n" % \
                                 escv(filename))
                    cache.close()
                    printout(hbar)

        printout("</body>")
        printout("</html>")

########NEW FILE########
__FILENAME__ = testrunner
#######################################################################
# This file is part of Pyblosxom.
#
# Copyright (C) 2010-2011 by the Pyblosxom team.  See AUTHORS.
#
# Pyblosxom is distributed under the MIT license.  See the file
# LICENSE for distribution details.
#######################################################################

import unittest
import os

def get_suite():
    names = os.listdir(os.path.dirname(__file__))
    names = ["Pyblosxom.tests.%s" % m[:-3]
             for m in names
             if m.startswith("test_") and m.endswith(".py")]
    suite = unittest.TestLoader().loadTestsFromNames(names)
    return suite

test_suite = get_suite()

def main():
    unittest.TextTestRunner().run(test_suite)

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = test_acronyms
#######################################################################
# This file is part of Pyblosxom.
#
# Copyright (C) 2010-2011 by the Pyblosxom team.  See AUTHORS.
#
# Pyblosxom is distributed under the MIT license.  See the file
# LICENSE for distribution details.
#######################################################################

import time
import os
import re

from Pyblosxom import pyblosxom
from Pyblosxom.tests import PluginTest, TIMESTAMP
from Pyblosxom.plugins import acronyms

class Test_acronyms(PluginTest):
    def setUp(self):
        PluginTest.setUp(self, acronyms)

    def tearDown(self):
        PluginTest.tearDown(self)

    def test_get_acronym_file(self):
        config = dict(self.config_base)
        self.assert_(acronyms.get_acronym_file(config),
                     os.path.join(self.datadir, os.pardir, "acronyms.txt"))

        config["acronym_file"] = os.path.join(self.datadir, "foo.txt")
        self.assert_(acronyms.get_acronym_file(config),
                     os.path.join(self.datadir, "foo.txt"))

    def test_verify_installation(self):
        config = dict(self.config_base)
        req = pyblosxom.Request(config, self.environ, {})
        self.assert_(acronyms.verify_installation(req) == 0)

        config["acronym_file"] = os.path.join(self.datadir, "foo.txt")
        req = pyblosxom.Request(config, self.environ, {})
        filename = acronyms.get_acronym_file(config)
        fp = open(filename, "w")
        fp.write("...")
        fp.close()
        
        self.assert_(acronyms.verify_installation(req) == 1)

    def test_build_acronyms(self):
        def check_this(lines, output):
            for inmem, outmem in zip(acronyms.build_acronyms(lines), output):
                self.assertEquals(inmem[0].pattern, outmem[0])
                self.assertEquals(inmem[1], outmem[1])

        check_this(["FOO = bar"],
                   [("(\\bFOO\\b)", "<acronym title=\"bar\">\\1</acronym>")])
        check_this(["FOO. = bar"],
                   [("(\\bFOO.\\b)", "<abbr title=\"bar\">\\1</abbr>")])
        check_this(["FOO = abbr|bar"],
                   [("(\\bFOO\\b)", "<abbr title=\"bar\">\\1</abbr>")])
        check_this(["FOO = acronym|bar"],
                   [("(\\bFOO\\b)", "<acronym title=\"bar\">\\1</acronym>")])
        # this re doesn't compile, so it gets skipped
        check_this(["FOO[ = bar"], [])

    def test_cb_story(self):
        req = pyblosxom.Request(
            self.config, self.environ,
            {"acronyms":acronyms.build_acronyms(["FOO = bar"])})

        # basic test
        args = {"request": req,
                "entry": {"body": "<p>This is FOO!</p>"}}

        ret = acronyms.cb_story(args)

        self.assertEquals(
            args["entry"]["body"],
            "<p>This is <acronym title=\"bar\">FOO</acronym>!</p>")

        # test to make sure substitutions don't happen in tags
        args = {"request": req,
                "entry": {"body": "<FOO>This is FOO!</FOO>"}}

        ret = acronyms.cb_story(args)

        self.assertEquals(
            args["entry"]["body"],
            "<FOO>This is <acronym title=\"bar\">FOO</acronym>!</FOO>")

########NEW FILE########
__FILENAME__ = test_akismetcomments
#######################################################################
# This file is part of Pyblosxom.
#
# Copyright (C) 2010-2011 by the Pyblosxom team.  See AUTHORS.
#
# Pyblosxom is distributed under the MIT license.  See the file
# LICENSE for distribution details.
#######################################################################

"""
Tests for the akismetcomments plugin.
"""

__author__ = 'Ryan Barrett <pyblosxom@ryanb.org>'
__url__ = 'http://pyblosxom.github.com/wiki/index.php/Framework_for_testing_plugins'

from Pyblosxom.tests import PluginTest
from Pyblosxom.plugins import akismetcomments
import sys

# FIXME: we do some icky things here to mock Akismet.  It'd be better
# to have a real mocking module like Mock or Fudge.

class MockAkismet:
    """A mock Akismet class."""
    GOOD_KEY = 'my_test_key'
    IPADDRESS = '12.34.56.78'
    BLOG_URL = 'http://blog.url/'
    comment_check_return = None
    comment_check_error = False

    def __init__(self, key=None, blog_url=None, agent=None):
        self.key = key
        assert MockAkismet.BLOG_URL == blog_url

    def verify_key(self):
        return self.key == MockAkismet.GOOD_KEY

    def comment_check(self, comment, data=None, build_data=True, DEBUG=False):
        if MockAkismet.comment_check_error:
            MockAkismet.comment_check_error = False
            raise akismet.AkismetError()
        else:
            assert 'foo' == comment
            ret = MockAkismet.comment_check_return
            MockAkismet.comment_check_return = None
            return ret

    @classmethod
    def inject_comment_check(cls, ret):
        cls.comment_check_return = ret

    @classmethod
    def inject_comment_check_error(cls):
        cls.comment_check_error = True

class Mockakismet:
    class AkismetError(Exception):
        pass

    Akismet = MockAkismet

sys.modules['akismet'] = Mockakismet
import akismet


class TestAkismetComments(PluginTest):
    """Test class for the akismetcomments plugin.
    """
    def setUp(self):
        PluginTest.setUp(self, akismetcomments)

        akismet.Akismet = MockAkismet

        self.config['base_url'] = MockAkismet.BLOG_URL
        self.config['akismet_api_key'] = MockAkismet.GOOD_KEY
        self.args['comment'] = {'description': "foo",
                                'ipaddress': MockAkismet.IPADDRESS}

    def test_verify_installation(self):
        """verify_installation should check for an api key and verify it."""
        self.assertEquals(
            True, akismetcomments.verify_installation(self.request))

        # try without an akismet_api_key config var
        del self.config['akismet_api_key']
        self.assertEquals(
            False, akismetcomments.verify_installation(self.request))

        # try with an import error
        akismet = sys.modules['akismet']
        del sys.modules['akismet']
        self.assertEquals(
            False, akismetcomments.verify_installation(self.request))
        sys.modules['akismet'] = akismet

        # try with a key that doesn't verify
        self.config['akismet_api_key'] = 'bad_key'
        orig_verify_key = akismet.Akismet.verify_key
        self.assertEquals(False, akismetcomments.verify_installation(self.request))

    def test_comment_reject(self):
        """comment_reject() should pass the comment through to akismet."""
        # no comment to reject
        assert 'comment' not in self.data
        self.assertEquals(
            False,
            akismetcomments.cb_comment_reject(self.args))

        self.set_form_data({})
        self.assertEquals(
            False, akismetcomments.cb_comment_reject(self.args))
        self.set_form_data({'body': 'body'})

    def test_bad_api_key_reject(self):
        # bad api key
        self.config['akismet_api_key'] = 'bad_key'
        self.assertEquals(
            False, akismetcomments.cb_comment_reject(self.args))
        self.config['akismet_api_key'] = MockAkismet.GOOD_KEY

    def test_akismet_error(self):
        # akismet error
        MockAkismet.inject_comment_check_error()
        print akismet.Akismet.comment_check_error
        self.assertEquals(
            (True, 'Missing essential data (e.g., a UserAgent string).'),
            akismetcomments.cb_comment_reject(self.args))

    def test_akismet_ham(self):
        # akismet says ham
        MockAkismet.inject_comment_check(False)
        self.assertEquals(
            False, akismetcomments.cb_comment_reject(self.args))

    def test_akismet_spam(self):
        # akismet says spam
        MockAkismet.inject_comment_check(True)
        self.assertEquals(
            (True, 'I\'m sorry, but your comment was rejected by the <a href="'
             'http://akismet.com/">Akismet</a> spam filtering system.'),
            akismetcomments.cb_comment_reject(self.args))

########NEW FILE########
__FILENAME__ = test_backwards_compatibility
#######################################################################
# This file is part of Pyblosxom.
#
# Copyright (C) 2010-2011 by the Pyblosxom team.  See AUTHORS.
#
# Pyblosxom is distributed under the MIT license.  See the file
# LICENSE for distribution details.
#######################################################################

from Pyblosxom.tests import UnitTestBase
from Pyblosxom.pyblosxom import Request

class TestRequest(UnitTestBase):
    """Need to be backwards compatible with pre-existing methods of
    getting config, data and http dicts from the Request object.
    """
    def test_conf(self):
        r = Request({"foo": "bar"}, {}, {})

        conf = r.get_configuration()

        for mem in (r.conf, r.config, r.configuration):
            yield self.eq_, mem, conf

    def test_http(self):
        r = Request({}, {"foo": "bar"}, {})

        self.eq_(r.http, r.get_http())

    def test_data(self):
        r = Request({}, {}, {"foo": "bar"})

        self.eq_(r.data, r.get_data())

########NEW FILE########
__FILENAME__ = test_blog
#######################################################################
# This file is part of Pyblosxom.
#
# Copyright (C) 2010 by the Pyblosxom team.  See AUTHORS.
#
# Pyblosxom is distributed under the MIT license.  See the file
# LICENSE for distribution details.
#######################################################################

import os
import time
import shutil

from Pyblosxom.tests import UnitTestBase
from Pyblosxom import tools

def gen_time(s):
    """
    Takes a string in YYYY/MM/DD hh:mm format and converts it to
    a float of seconds since the epoch.

    For example:
   
    >>> gen_time("2007/02/14 14:14")
    1171480440.0
    """
    return time.mktime(time.strptime(s, "%Y/%m/%d %H:%M"))

class BlogTest(UnitTestBase):
    def get_datadir(self):
        tempdir = self.get_temp_dir()
        return os.path.join(tempdir, "datadir")
    
    def setup_blog(self, blist):
        datadir = self.get_datadir()
        for mem in blist:
            tools.create_entry(datadir,
                               mem["category"],
                               mem["filename"],
                               mem["mtime"],
                               mem["title"],
                               mem["metadata"],
                               mem["body"])

    def cleanup_blog(self):
        shutil.rmtree(self.get_datadir(), ignore_errors=True)

class TestBlogTest(BlogTest):
    blog = [{"category": "cat1",
             "filename": "entry1.txt",
             "mtime": gen_time("2007/02/14 14:14"),
             "title": "Happy Valentine's Day!",
             "metadata": {},
             "body": "<p>Today is Valentine's Day!  w00t!</p>"}]

    def test_harness(self):
        tempdir = self.get_temp_dir()

        # this is kind of a bogus assert, but if we get this far
        # without raising an exception, then our test harness is
        # probably working.

        try:
            self.setup_blog(TestBlogTest.blog)
            self.eq_(1, 1)
        finally:
            self.cleanup_blog()
            self.eq_(1, 1)


########NEW FILE########
__FILENAME__ = test_blosxom_renderer
#######################################################################
# This file is part of Pyblosxom.
#
# Copyright (C) 2011 by the Pyblosxom team.  See AUTHORS.
#
# Pyblosxom is distributed under the MIT license.  See the file
# LICENSE for distribution details.
#######################################################################

from StringIO import StringIO

from Pyblosxom.tests import UnitTestBase
from Pyblosxom.pyblosxom import Request
from Pyblosxom.renderers import blosxom

req = Request({}, {}, {})

class TestBlosxomRenderer(UnitTestBase):
    def test_dollar_parse_problem(self):
        output = StringIO()
        renderer = blosxom.BlosxomRenderer(req, output)
        renderer.flavour = {"story": "$(body)"}

        # mocking out _run_callback to just return the args dict
        renderer._run_callback = lambda c, args: args

        entry = {"body": r'PS1="\u@\h \[\$foo \]\W\[$RST\] \$"'}

        # the rendered template should be exactly the same as the body
        # in the entry--no \$ -> $ silliness.
        self.eq_(renderer.render_template(entry, "story"),
                 entry["body"])

    def test_date_head(self):
        output = StringIO()
        renderer = blosxom.BlosxomRenderer(req, output)
        renderer.flavour = {"date_head": "$(yr) $(mo) $(da) $(date)"}

        # mocking out _run_callback to just return the args dict
        renderer._run_callback = lambda c, args: args

        vardict = {
            "yr": "2011",
            "mo": "01",
            "da": "25",
            "date": "Tue, 25 Jan 2011"
            }

        self.eq_(renderer.render_template(vardict, "date_head"),
                 "2011 01 25 Tue, 25 Jan 2011")

########NEW FILE########
__FILENAME__ = test_check_blacklist
#######################################################################
# This file is part of Pyblosxom.
#
# Copyright (C) 2010-2011 by the Pyblosxom team.  See AUTHORS.
#
# Pyblosxom is distributed under the MIT license.  See the file
# LICENSE for distribution details.
#######################################################################

import unittest

from Pyblosxom.tests import PluginTest
from Pyblosxom.plugins import check_blacklist

class TestCheckBlacklist(PluginTest):
    def setUp(self):
        PluginTest.setUp(self, check_blacklist)

    def test_comment_reject(self):
        comment = {}
        self.args['comment'] = comment
        cfg = self.args["request"].get_configuration()

        # no comment_rejected_words--so it passes
        ret = check_blacklist.cb_comment_reject(self.args)
        self.assertEquals(False, ret)

        # rejected words, but none in the comment
        cfg["comment_rejected_words"] = ["foo"]
        comment["body"] = "this is a happy comment"
        ret = check_blacklist.cb_comment_reject(self.args)
        self.assertEquals(False, ret)

        # rejected words, one is in the comment
        cfg["comment_rejected_words"] = ["this"]
        ret = check_blacklist.cb_comment_reject(self.args)
        self.assertEquals(True, ret[0])

########NEW FILE########
__FILENAME__ = test_check_javascript
#######################################################################
# This file is part of Pyblosxom.
#
# Copyright (C) 2010-2011 by the Pyblosxom team.  See AUTHORS.
#
# Pyblosxom is distributed under the MIT license.  See the file
# LICENSE for distribution details.
#######################################################################

"""
Tests for the check_javascript plugin.
"""

__author__ = 'Ryan Barrett <pyblosxom@ryanb.org>'
__url__ = 'http://pyblosxom.github.com/wiki/index.php/Framework_for_testing_plugins'

from Pyblosxom.tests import PluginTest
from Pyblosxom.plugins import check_javascript

class TestCheckJavascript(PluginTest):
    """Test class for the check_javascript plugin.
    """
    def setUp(self):
        PluginTest.setUp(self, check_javascript)
        self.config['blog_title'] = 'test title'

    def test_comment_reject(self):
        """check_javascript should check the secretToken query argument."""
        # no secretToken
        assert 'secretToken' not in self.http
        self.assertEquals(True, check_javascript.cb_comment_reject(self.args))

        # bad secretToken
        self.set_form_data({'secretToken': 'not the title'})
        self.assertEquals(True, check_javascript.cb_comment_reject(self.args))

        # good secretToken
        self.set_form_data({'secretToken': 'test title'})
        self.assertEquals(False, check_javascript.cb_comment_reject(self.args))

########NEW FILE########
__FILENAME__ = test_check_nonhuman
#######################################################################
# This file is part of Pyblosxom.
#
# Copyright (C) 2010-2011 by the Pyblosxom team.  See AUTHORS.
#
# Pyblosxom is distributed under the MIT license.  See the file
# LICENSE for distribution details.
#######################################################################

import unittest

from Pyblosxom.tests import PluginTest, TIMESTAMP
from Pyblosxom.plugins import check_nonhuman

class TestCheckNonhuman(PluginTest):
    def setUp(self):
        PluginTest.setUp(self, check_nonhuman)

    def test_comment_reject(self):
        comment = {}
        self.args['comment'] = comment

        # no iamhuman, rejection!
        ret = check_nonhuman.cb_comment_reject(self.args)
        self.assertEquals(True, ret[0])

        # iamhuman, so it passes
        comment['iamhuman'] = 'yes'
        ret = check_nonhuman.cb_comment_reject(self.args)
        self.assertEquals(False, ret)

        # foo, so it passes
        del comment['iamhuman']
        self.args["request"].get_configuration()["nonhuman_name"] = "foo"
        comment['foo'] = 'yes'
        ret = check_nonhuman.cb_comment_reject(self.args)
        self.assertEquals(False, ret)

########NEW FILE########
__FILENAME__ = test_comments
#######################################################################
# This file is part of Pyblosxom.
#
# Copyright (C) 2010-2011 by the Pyblosxom team.  See AUTHORS.
#
# Pyblosxom is distributed under the MIT license.  See the file
# LICENSE for distribution details.
#######################################################################

"""
Tests for the comments plugin.
"""

from Pyblosxom.tests import PluginTest, FrozenTime, TIMESTAMP
from Pyblosxom.plugins import comments

import cgi
import cPickle
import os


class TestComments(PluginTest):
    """Test class for the comments plugin.
    """
    def setUp(self):
        PluginTest.setUp(self, comments)

        # add comment templates
        self.renderer.flavour.update({'comment-story': 'comment-story',
                                      'comment': 'comment'})

        # inject the frozen time module
        comments.time = self.frozen_time

        # populate with default config vars
        comments.cb_start(self.args)

    def tearDown(self):
        PluginTest.tearDown(self)

    def comment_path(self):
        """Returns the comment path that would currently be created."""
        filename = '%s-%0.1f.%s' % (self.entry_name, self.timestamp,
                                    self.config['comment_draft_ext'])
        return os.path.join(self.config['comment_dir'], filename)

    def comment(self, title='title', author='author', body='body', url=None,
                email=None, ipaddress=None, encoding=None, preview=None,
                **kwargs):
        """Posts a comment with the given contents."""
        # set the encoding in the config. it should default to utf-8
        if encoding:
            self.config['blog_encoding'] = encoding

        # build up the form data and post the comment
        args = [(arg, vars()[arg])
                for arg in ('title', 'author', 'body', 'url', 'email', 'preview')
                if vars()[arg] is not None]
        self.set_form_data(dict(args))
        comments.cb_prepare(self.args)

    def check_comment_file(self, title='title', author='author', body='body',
                           url='', email='', encoding=None, ipaddress='',
                           expected_title=None, expected_author=None,
                           expected_body=None, expected_url=None, preview=None,
                           delete_datadir=True):
        """Posts a comment and checks its contents on disk."""
        self.comment(title, author, body, url, email, ipaddress, encoding,
                     preview)

        if encoding is None:
            encoding = 'utf-8'
        if expected_title is None:
            expected_title = title
        if expected_author is None:
            expected_author = author
        if expected_body is None:
            expected_body = body
        if expected_url is None:
            expected_url = url

        # check the files in the comments directory
        files = os.listdir(self.config['comment_dir'])
        self.assert_(os.path.basename(self.comment_path()) in files)
        self.assert_(comments.LATEST_PICKLE_FILE in files)

        # check the coment file's contents
        expected_lines = [
            '<?xml version="1.0" encoding="%s"?>\n' % encoding,
            '<item>\n',
            '<description>%s</description>\n' % cgi.escape(expected_body),
            '<pubDate>%0.1f</pubDate>\n' % self.timestamp,
            '<author>%s</author>\n' % cgi.escape(expected_author),
            '<title>%s</title>\n' % cgi.escape(expected_title),
            '<source></source>\n',
            '<link>%s</link>\n' % cgi.escape(expected_url),
            '<w3cdate>%s</w3cdate>\n' % self.timestamp_w3c,
            '<date>%s</date>\n' % self.timestamp_date,
            '<ipaddress>%s</ipaddress>\n' % ipaddress,
            '</item>\n',
            ]
        if email:
            expected_lines.insert(-1, '<email>%s</email>\n' % email)

        file = open(self.comment_path())
        actual_lines = file.readlines()
        file.close()

        expected_lines.sort()
        actual_lines.sort()
        for expected, actual in zip(expected_lines, actual_lines):
            self.assertEquals(expected, actual)

        if delete_datadir:
            self.delete_datadir()

    def check_comment_output(self, expected, delete_datadir=True, **kwargs):
        """Posts a comment and checks its rendered output.

        Note that this deletes the datadir before it posts the
        comment!
        """
        self.data['display_comment_default'] = True

        self.comment(**kwargs)
        comments.cb_story(self.args)
        self.args['template'] = ''
        comments.cb_story_end(self.args)
        self.assertEquals(expected, self.args['template'])

        if delete_datadir:
            self.delete_datadir()

    def test_sanitize(self):
        # test <ul> ... </ul>
        ulbody = (
            "<ul>\n"
            "<li>entry within a ul list</li>\n"
            "<li>entry within a ul list, with\n"
            "newlines in between\n"
            "</li>\n"
            "</ul>")

        self.assertEquals(
            comments.sanitize(ulbody),
            "<ul>"
            "<li>entry within a ul list</li>"
            "<li>entry within a ul list, with<br />\n"
            "newlines in between<br />\n"
            "</li>"
            "</ul>")

        # test <ol> ... </ol>
        ulbody = (
            "<ol>\n"
            "<li>entry within a ol list</li>\n"
            "<li>entry within a ol list, with\n"
            "newlines in between\n"
            "</li>\n"
            "</ol>")

        self.assertEquals(
            comments.sanitize(ulbody),
            "<ol>"
            "<li>entry within a ol list</li>"
            "<li>entry within a ol list, with<br />\n"
            "newlines in between<br />\n"
            "</li>"
            "</ol>")


    def test_cb_start(self):
        """cb_start() should set defaults for some config variables."""
        self.config = self.config_base
        comments.cb_start(self.args)

        self.assertEquals(os.path.join(self.datadir, 'comments'),
                          self.config['comment_dir'])
        self.assertEquals('cmt', self.config['comment_ext'])
        self.assertEquals('cmt', self.config['comment_draft_ext'])
        self.assertEquals(0, self.config['comment_nofollow'])

    def test_verify_installation(self):
        """verify_installation should check the comment dir and smtp
        config."""
        # comment_dir must exist
        assert not os.path.exists('/not/a/directory')
        self.config['comment_dir'] = '/not/a/directory'
        self.assertEquals(0, comments.verify_installation(self.request))
        del self.config['comment_dir']

        # either all smtp config variables must be defined, or none
        smtp_vars = ['comment_smtp_server', 'comment_smtp_from',
                     'comment_smtp_to']
        for smtp_var in smtp_vars:
            [self.config.pop(var, '') for var in smtp_vars]
            self.config[smtp_var] = 'abc'
            self.assertEquals(0, comments.verify_installation(self.request))

        del self.config[smtp_vars[-1]]

        self.assertEquals(1, comments.verify_installation(self.request))

    def test_check_comments_disabled(self):
        time = FrozenTime(TIMESTAMP)

        entry = self.entry
        config = self.config
        key = "comment_disable_after_x_days"
        day = 60 * 60 * 24

        # not set -> False
        self.eq_(comments.check_comments_disabled(config, entry), False)

        # set to non-int -> False
        config[key] = "abc"
        self.eq_(comments.check_comments_disabled(config, entry), False)

        # set to negative int -> False
        config[key] = -10
        self.eq_(comments.check_comments_disabled(config, entry), False)

        # entry has no mtime -> False
        config[key] = 10
        self.eq_(comments.check_comments_disabled(config, entry), False)

        # inside range -> False
        config[key] = 10 # 10 days
        entry['mtime'] = time.time() - (5 * day)
        self.eq_(comments.check_comments_disabled(config, entry), False)

        # outside range -> True
        config[key] = 10 # 10 days
        entry['mtime'] = time.time() - (15 * day)
        self.eq_(comments.check_comments_disabled(config, entry), True)

    # def test_cb_handle(self):
    #     """cb_handle() should intercept requests for /comments.js."""
    #     self.assertEquals(None, comments.cb_handle(self.args))

    #     self.request.add_http({'PATH_INFO': '/not_comments.js'})
    #     self.assertEquals(None, comments.cb_handle(self.args))

    #     self.request.add_http({'PATH_INFO': '/comments.js'})
    #     self.assertEquals(True, comments.cb_handle(self.args))

    #     response = self.request.get_response()
    #     self.assertEquals('text/javascript',
    #                       response.get_headers()['Content-Type'])

    #     out = cStringIO.StringIO()
    #     response.send_body(out)
    #     self.assert_(out.getvalue().startswith(
    #         '/* AJAX comment support for pyblosxom'))

    def test_cb_prepare_showcomments(self):
        """cb_prepare() should set display_comment_default to show
        comments."""
        # default is to not show comments
        del self.data['bl_type']
        comments.cb_prepare(self.args)
        self.assertEquals(False, self.data['display_comment_default'])

        # show them if the bl_type config var is 'file'
        self.data['bl_type'] = 'db'
        comments.cb_prepare(self.args)
        self.assertEquals(False, self.data['display_comment_default'])

        self.data['bl_type'] = 'file'
        comments.cb_prepare(self.args)
        self.assertEquals(True, self.data['display_comment_default'])

        # or if the query string has showcomments=yes
        del self.data['bl_type']
        self.request.add_http({'QUERY_STRING': 'x=yes&showcomments=no7&y=no'})
        comments.cb_prepare(self.args)
        self.assertEquals(False, self.data['display_comment_default'])

        self.request.add_http({'QUERY_STRING': 'x=yes&showcomments=yes&y=no'})
        comments.cb_prepare(self.args)
        self.assertEquals(True, self.data['display_comment_default'])

    def test_cb_prepare_new_comment(self):
        """A new comment should be packaged in XML and stored in a new file."""
        self.check_comment_file(title='title', author='author', body='body')

        # url is optional. try setting it.
        self.check_comment_file(url='http://home/')

        # previewed comments shouldn't be stored
        self.comment(preview='yes')
        self.assert_(not os.path.exists(self.comment_path()))

    def test_cb_prepare_encoding(self):
        """If the blog_encoding config var is set, it should be used."""
        self.check_comment_file(encoding='us-ascii')

    def test_cb_prepare_massage_link(self):
        """User-provided URLs should be scrubbed and linkified if
        necessary."""
        # html control characters should be stripped
        self.check_comment_file(url='<script arg=\'val"ue"\'>',
                                expected_url='http://script arg=value')

        # http:// should only be added if there isn't already a protocol
        self.check_comment_file(url='xmpp:me@jabber.org')

    def test_cb_prepare_nofollow(self):
        """Nofollow support should add rel="nofollow" to links in the
        body."""
        body = '<a href="/dest">x</a>'

        # default is off
        self.assert_(self.config['comment_nofollow'] == False)
        self.check_comment_file(body=body)

        # turned on
        self.config['comment_nofollow'] = True
        nofollow_body = '<a rel="nofollow" href="/dest">x</a>'
        self.check_comment_file(body=body, expected_body=nofollow_body)

    def test_cb_prepare_email(self):
        """User-provided URLs should be scrubbed and linkified if necessary."""
        self.check_comment_file(email='a@b.c')

    def test_cb_prepare_ipaddress(self):
        """If provided, IP address should be recorded."""
        ipaddress = '12.34.56.78'
        self.request.add_http({'REMOTE_ADDR': ipaddress})
        self.check_comment_file(ipaddress=ipaddress)

    def test_cb_reject(self):
        """Comments should be filtered with cb_comment_reject()."""
        # try rejecting the comment, with and without a message
        for return_value, msg in ((True, 'Comment rejected.'),
                                  ((True, 'bad!'), 'bad!')
                                  ):
            self.inject_callback('comment_reject', lambda: return_value)
            self.comment()
            self.assert_(not os.path.exists(self.comment_path()))
            self.assertEquals(True, self.data['rejected'])
            self.assertEquals(msg, self.data['comment_message'])

        del self.data['rejected']

        # try accepting the comment, with and without a message
        for return_value in [False, (False, 'ok')]:
            self.inject_callback('comment_reject', lambda: return_value)
            self.check_comment_file()

            self.assert_('rejected' not in self.data)
            self.assertEquals('Comment submitted.  Thanks!',
                              self.data['comment_message'])

    def test_cb_prepare_latest_pickle(self):
        """The "latest" file should contain the last comment's timestamp."""
        self.comment()
        latest_path = os.path.join(self.config['comment_dir'],
                                   comments.LATEST_PICKLE_FILE)
        timestamp = cPickle.load(open(latest_path))
        self.assertEquals(self.timestamp, timestamp)

    def test_cb_prepare_draft(self):
        """For draft support, comment_draft_ext should override comment_ext."""
        self.config['comment_draft_ext'] = 'draft'
        self.check_comment_file()

    def test_cb_head(self):
        """cb_head() should expand template variables in single-entry lists."""
        template = self.args['template']

        # only expand if we have a comment-head template
        self.assert_('comment-head' not in self.renderer.flavour)
        self.assertEquals(template, comments.cb_head(self.args))
        self.assert_(not self.entry.has_key('title'))

        # don't expand if we're displaying more than one entry
        self.renderer.flavour['comment-head'] = ''
        self.renderer.set_content([self.entry, self.entry])
        self.assertEquals(template, comments.cb_head(self.args))
        self.assert_(not self.entry.has_key('title'))

        # we have comment-head and only one entry. expand!
        class MockEntry(dict):
            """Intercepts __getitem__ and records the key."""
            def __getitem__(self, key):
                self.key = key

        mock_entry = MockEntry()

        self.renderer.set_content([self.entry])
        self.args['entry'] = {'entry_list': [mock_entry]}
        self.assertEquals(template, comments.cb_head(self.args))
        self.assertEquals('title', mock_entry.key)

    def test_cb_renderer(self):
        """cb_renderer() should return an AjaxRenderer for ajax
        requests."""
        self.assert_(not isinstance(comments.cb_renderer(self.args),
                                    comments.AjaxRenderer))

        self.set_form_data({'ajax': 'true'})
        self.assert_(isinstance(comments.cb_renderer(self.args),
                                comments.AjaxRenderer))

    def test_ajax_renderer(self):
        """AjaxRenderer should only output previewed and posted
        comments."""
        def should_output(template_name):
            renderer = comments.AjaxRenderer(self.request, self.data)
            return renderer._should_output(self.entry,
                                           template_name)

        # a comment preview
        self.set_form_data({'ajax': 'preview'})
        self.assertEquals(True, should_output('comment-preview'))
        self.assertEquals(False, should_output('story'))

        # a comment that was just posted
        self.set_form_data({'ajax': 'post'})
        self.assertEquals(False, should_output('story'))

        self.entry['cmt_time'] = self.timestamp
        self.assert_('cmt_time' not in self.data)
        self.assertEquals(False, should_output('comment'))

        self.data['cmt_time'] = self.timestamp
        self.assertEquals(True, should_output('comment'))

    def test_num_comments(self):
        """cb_story() should count the number of comments."""
        self.data['display_comment_default'] = True

        def check_num_comments(expected):
            if self.entry.has_key("num_comments"):
                self.entry["num_comments"] = None
            comments.cb_story(self.args)
            self.assertEquals(expected, self.entry['num_comments'])

        check_num_comments(0)
        self.comment()
        check_num_comments(1)

        self.frozen_time.timestamp += 1
        self.comment()
        check_num_comments(2)

    def test_when_to_render_comments(self):
        # cb_story[_end]() should only render comment templates when
        # appropriate
        def check_for_comments(expected):
            args_template = self.args['template']
            comments.cb_story(self.args)
            self.assertEquals(expected, self.args['template'])
            comments.cb_story_end(self.args)
            self.assertEquals(expected, self.args['template'])
            self.args['template'] = args_template

        # this is required by the comments plugin
        self.entry['absolute_path'] = ''

        # with no comment-story template, there's nothing
        del self.renderer.flavour['comment-story']
        self.renderer.set_content([self.entry])
        check_for_comments('template starts:')
        self.renderer.flavour['comment-story'] = 'comment-story'

        # with a comment-story template and a single entry, we show
        # the template once
        self.renderer.set_content([self.entry])
        self.data['display_comment_default'] = True
        check_for_comments('template starts:comment-story')


        # with a comment-story template and a multiple entries, we
        # don't show the template
        self.renderer.set_content([self.entry, self.entry])
        self.data['display_comment_default'] = True
        check_for_comments('template starts:')

        # if display_comment_default is set to False, we don't
        # show the template
        self.renderer.set_content([self.entry])
        self.data['display_comment_default'] = False
        check_for_comments('template starts:')

        # if nocomments is true, we don't show the template
        self.renderer.set_content([self.entry])
        self.data['display_comment_default'] = True
        self.entry['nocomments'] = True
        check_for_comments('template starts:')

    def test_cb_story_comment_story_template(self):
        # check that cb_story() appends the comment-story template
        self.data['display_comment_default'] = True
        self.assert_(self.renderer.flavour['comment-story'] == 'comment-story')
        comments.cb_story(self.args)
        self.assertEquals('template starts:comment-story',
                          self.args['template'])

    def test_cb_story_end_renders_comments(self):
        self.comment()

        # check that cb_story_end() renders comments.
        self.data['display_comment_default'] = True

        # no comments.  check both cb_story_end's return value and
        # args['template'].
        self.args['template'] = 'foo'
        self.assertEquals('foo', comments.cb_story_end(self.args))
        self.assertEquals('foo', self.args['template'])

        # one comment
        self.renderer.flavour['comment'] = '$cmt_time '
        expected = '%s ' % self.timestamp
        self.check_comment_output(expected, delete_datadir=False)

        # two comments
        self.frozen_time.timestamp += 1
        expected += '%s ' % self.frozen_time.timestamp
        self.check_comment_output(expected)

    def test_template_variables(self):
        """Check the comment template variables."""
        self.data['display_comment_default'] = True

        # these will sent in the form data
        args = {
            'body': 'body=with"chars',
            'author': 'author',
            'title': 'title',
            'url': 'http://snarfed.org/',
            'email': 'pyblosxom@ryanb.org',
            }

        # these will be used as template variables, prefixed with $cmt_
        vars = dict(args)

        for old, new in [('body', 'description'), ('url', 'link')]:
            vars[new] = vars[old]
            del vars[old]

        vars.update({
            # these are generated by pyblosxom
            'time': str(self.timestamp),
            'w3cdate': self.timestamp_w3c,
            'date': self.timestamp_date,
            'pubDate': self.timestamp_asc,
            'description': 'body=with"chars',
            })

        # these depends on the fact that dict.keys() and dict.values() return
        # items in the same order. so far, python guarantees this.
        def make_template():
            return '\n'.join('$cmt_%s' % name for name in vars.keys())

        def make_expected():
            return '\n'.join(vars.values())

        # a normal comment
        self.renderer.flavour['comment'] = 'comment:\n' + make_template()
        self.check_comment_output('comment:\n' + make_expected(), **args)

        # a previewed comment
        self.renderer.flavour['comment-preview'] = 'preview:\n' + make_template()
        args['preview'] = 'yes'
        self.check_comment_output('preview:\n' + make_expected(), **args)

        # a rejected comment
        del args['preview']
        self.inject_callback('comment_reject', lambda: (True, 'foo'))
        vars['description'] = '<span class="error">foo</span>'
        self.renderer.flavour['comment'] = 'comment:\n' + make_template()
        self.check_comment_output('comment:\n' + make_expected(), **args)

    def test_optionally_linked_author(self):
        """Test the cmt_optionally_linked_author template variable."""
        self.renderer.flavour['comment'] = '$cmt_optionally_linked_author'

        self.assert_(self.config['comment_nofollow'] == False)
        self.check_comment_output('me', author='me', url='')
        self.check_comment_output('<a href="http://home">me</a>',
                                  author='me', url='home')

        self.config['comment_nofollow'] = True
        self.check_comment_output('me', author='me', url='')
        self.check_comment_output('<a rel="nofollow" href="http://home">me</a>',
                                  author='me', url='home')

########NEW FILE########
__FILENAME__ = test_entries
#######################################################################
# This file is part of Pyblosxom.
#
# Copyright (C) 2010-2011 by the Pyblosxom team.  See AUTHORS.
#
# Pyblosxom is distributed under the MIT license.  See the file
# LICENSE for distribution details.
#######################################################################

from os import environ
import time

from Pyblosxom.tests import req_, UnitTestBase

from Pyblosxom.tools import STANDARD_FILTERS
from Pyblosxom.entries.base import EntryBase, generate_entry

TIME1 = (2008, 7, 21, 12, 51, 47, 0, 203, 1)

class TestEntryBase(UnitTestBase):
    def test_data(self):
        e = EntryBase(req_())
        self.eq_(e.get_data(), "")

        s1 = "la la la la la"
        e.set_data(s1)
        self.eq_(e.get_data(), s1)
        self.eq_(type(e.get_data()), str)

        s2 = u"foo foo foo foo foo"
        e.set_data(s2)
        self.eq_(e.get_data(), s2)
        self.eq_(type(e.get_data()), str)

        s3 = "foo bar"
        e.set_data(s3)
        self.eq_(e.get_data(), s3)

    def test_metadata(self):
        e = EntryBase(req_())
        self.eq_(e.get_metadata_keys(), STANDARD_FILTERS.keys())
        self.eq_(e.get_metadata("foo"), None)
        self.eq_(e.get_metadata("foo", "bar"), "bar")
        e.set_metadata("foo", "bar")
        self.eq_(e.get_metadata("foo"), "bar")

    def test_time(self):
        e = EntryBase(req_())
        # set_time takes local time, and results depend on time zone.
        self.__force_tz()
        e.set_time(TIME1)
        self.__restore_tz()
        for mem in (("timetuple", TIME1),
                    ("mtime", 1216659107.0),
                    ("ti", "12:51"),
                    ("mo", "Jul"),
                    ("mo_num", "07"),
                    ("da", "21"),
                    ("dw", "Monday"),
                    ("yr", "2008"),
                    ("fulltime", "20080721125147"),
                    ("date", "Mon, 21 Jul 2008"),
                    ("w3cdate", "2008-07-21T16:51:47Z"),
                    ("rfc822date", "Mon, 21 Jul 2008 16:51 GMT")):
            self.eq_(e[mem[0]], mem[1], \
                  "%s != %s (note: this is a time zone dependent test)" % (mem[0], mem[1]))

    def test_dictlike(self):
        e = EntryBase(req_())
        e["foo"] = "bar"
        e["body"] = "entry body"

        def sortlist(l):
            l.sort()
            return l

        self.eq_(sortlist(e.keys()), sortlist(STANDARD_FILTERS.keys() + ["foo", "body"]))

        self.eq_(e["foo"], "bar")
        self.eq_(e.get("foo"), "bar")
        self.eq_(e.get("foo", "fickle"), "bar")
        self.eq_(e.get_metadata("foo"), "bar")
        self.eq_(e.get_metadata("foo", "fickle"), "bar")

        self.eq_(e["body"], "entry body", "e[\"body\"]")
        self.eq_(e.get("body"), "entry body", "e.get(\"body\")")
        self.eq_(e.getData(), "entry body", "e.getData()")

        self.eq_(e.get("missing_key", "default"), "default")
        self.eq_(e.get("missing_key"), None)

        # e.set("faz", "baz")
        # yield eq_, e.get("faz"), "baz"

        self.eq_(e.has_key("foo"), True)
        self.eq_(e.has_key("foo2"), False)
        self.eq_(e.has_key("body"), True)

        # FIXME - EntryBase doesn't support "in" operator.
        # self.eq_("foo" in e, True)
        # self.eq_("foo2" in e, False)
        # self.eq_("foo2" not in e, True)
        # self.eq_("body" in e, True)

        e.update({"foo": "bah", "faux": "pearls"})
        self.eq_(e["foo"], "bah")
        self.eq_(e["faux"], "pearls")

        e.update({"body": "new body data"})
        self.eq_(e["body"], "new body data")
        self.eq_(e.get_data(), "new body data")

        # del e["foo"]
        # yield eq_, e.get("foo"), None

    # @raises(KeyError)
    # def test_delitem_keyerror(self):
    #     e = EntryBase(req_())
    #     del e["missing_key"]

    # @raises(ValueError)
    # def test_delitem_valueerror(self):
    #     e = EntryBase(req_())
    #     del e["body"]

    def test_generate_entry(self):
        # generate_entry takes local time, and we test the resulting
        # rfc822date which is UTC.  Result depends on time zone.
        self.__force_tz()
        e = generate_entry(req_(), {"foo": "bar"}, "entry body", TIME1)
        self.__restore_tz()

        self.eq_(e["foo"], "bar")
        self.eq_(e["body"], "entry body")
        self.eq_(e["rfc822date"], "Mon, 21 Jul 2008 16:51 GMT")

        e = generate_entry(req_(), {"foo": "bar"}, "entry body")

    def test_repr(self):
        # it doesn't really matter what __repr__ sends back--it's only used
        # for logging/debugging.  so this test adds coverage for that line to
        # make sure it doesn't error out.
        e = EntryBase(req_())
        repr(e)

    def __force_tz(self):
        """
        Force time zone to 'US/Eastern'.

        Some of the above tests are time zone dependent.
        """
        self.__tz = environ.get('TZ')
        environ['TZ'] = 'US/Eastern'
        time.tzset()
    
    def __restore_tz(self):
        """
        Restore time zone to what it was before __force_tz() call.
        """
        if self.__tz:
            environ['TZ'] = self.__tz
            self.__tz = None
        else:
            del environ['TZ']
        time.tzset()

########NEW FILE########
__FILENAME__ = test_entryparser
#######################################################################
# This file is part of Pyblosxom.
#
# Copyright (C) 2010-2011 by the Pyblosxom team.  See AUTHORS.
#
# Pyblosxom is distributed under the MIT license.  See the file
# LICENSE for distribution details.
#######################################################################

import os
from Pyblosxom.blosxom import blosxom_entry_parser

from Pyblosxom.tests import UnitTestBase


class Testentryparser(UnitTestBase):
    """pyblosxom.blosxom_entry_parser

    This tests parsing entry files.
    """
    def _basic_test(self, req, filedata, output_dict):
        datadir = req.get_configuration()["datadir"]
        if not os.path.exists(datadir):
            os.makedirs(datadir)

        filename = os.path.join(datadir, "firstpost.txt")

        fp = open(filename, "w")
        fp.write(filedata)
        fp.close()

        entry_dict = blosxom_entry_parser(filename, req)

        self.cmpdict(output_dict, entry_dict)

    def test_basic_entry(self):
        req = self.build_request()
        entry = ("First post!\n"
                 "<p>\n"
                 "First post!\n"
                 "</p>")

        self._basic_test(
            req, entry,
            {"title": "First post!", "body": "<p>\nFirst post!\n</p>"})

    def test_meta_data(self):
        req = self.build_request()
        entry = ("First post!\n"
                 "#music the doors\n"
                 "#mood happy\n"
                 "<p>\n"
                 "First post!\n"
                 "</p>")

        self._basic_test(
            req, entry,
            {"title": "First post!",
             "mood": "happy",
             "music": "the doors",
             "body": "<p>\nFirst post!\n</p>"})

    def test_meta_no_value(self):
        req = self.build_request()
        entry = ("First post!\n"
                 "#foo\n"
                 "<p>\n"
                 "First post!\n"
                 "</p>")

        self._basic_test(
            req, entry,
            {"title": "First post!", "foo": "1",
             "body": "<p>\nFirst post!\n</p>"})

########NEW FILE########
__FILENAME__ = test_entrytitle
#######################################################################
# This file is part of Pyblosxom.
#
# Copyright (C) 2010-2011 by the Pyblosxom team.  See AUTHORS.
#
# Pyblosxom is distributed under the MIT license.  See the file
# LICENSE for distribution details.
#######################################################################

import time
import os

from Pyblosxom import pyblosxom
from Pyblosxom.tests import PluginTest, TIMESTAMP
from Pyblosxom.plugins import entrytitle

class Test_entrytitle(PluginTest):
    def setUp(self):
        PluginTest.setUp(self, entrytitle)

    def test_cb_head(self):
        # no entries yields no entry_title
        args = {
            "request": pyblosxom.Request({}, {}, {}),
            "entry": {}
            }
        newargs = entrytitle.cb_head(args)
        self.assertEquals(newargs["entry"].get("entry_title", ""), "")

        # one entry yields entry_title
        args = {
            "request": pyblosxom.Request(
                {},
                {},
                {"entry_list": [{"title": "foobar"}]}),
            "entry": {}
            }
        newargs = entrytitle.cb_head(args)
        self.assertEquals(newargs["entry"]["entry_title"], ":: foobar")

        # one entry with no title yields entry_title with "No title"
        args = {
            "request": pyblosxom.Request(
                {},
                {},
                {"entry_list": [{}]}),
            "entry": {}
            }
        newargs = entrytitle.cb_head(args)
        self.assertEquals(newargs["entry"]["entry_title"], ":: No title")

        # one entry yields entry_title, using entry_title_template
        # configuration property
        args = {
            "request": pyblosxom.Request(
                {"entry_title_template": "%(title)s ::"},
                {},
                {"entry_list": [{"title": "foobar"}]}),
            "entry": {}
            }
        newargs = entrytitle.cb_head(args)
        self.assertEquals(newargs["entry"]["entry_title"], "foobar ::")

        # multiple entries yields no title
        args = {
            "request": pyblosxom.Request(
                {},
                {},
                {"entry_list": [{"title": "foobar"}, {"title": "foobar2"}]}),
            "entry": {}
            }
        newargs = entrytitle.cb_head(args)
        self.assertEquals(newargs["entry"].get("entry_title", ""), "")

    def test_verify_installation(self):
        self.assert_(entrytitle.verify_installation(self.request))

########NEW FILE########
__FILENAME__ = test_pages
#######################################################################
# This file is part of Pyblosxom.
#
# Copyright (C) 2010-2011 by the Pyblosxom team.  See AUTHORS.
#
# Pyblosxom is distributed under the MIT license.  See the file
# LICENSE for distribution details.
#######################################################################

from Pyblosxom.tests import PluginTest
from Pyblosxom.plugins import pages

class PagesTest(PluginTest):
    def setUp(self):
        PluginTest.setUp(self, pages)

    def test_is_frontpage(self):
        # test setup-related is_frontpage = False possibilities
        self.assertEquals(pages.is_frontpage({}, {}), False)
        self.assertEquals(pages.is_frontpage({"PATH_INFO": "/"}, {}),
                          False)
        self.assertEquals(pages.is_frontpage({"PATH_INFO": "/"},
                                             {"pages_frontpage": False}),
                          False)

        # test path-related possibilities
        for path, expected in (("/", True),
                               ("/index", True),
                               ("/index.html", True),
                               ("/index.xml", True),
                               ("/foo", False)):
            pyhttp = {"PATH_INFO": path}
            cfg = {"pages_frontpage": True}
            self.assertEquals(pages.is_frontpage(pyhttp, cfg), expected)

########NEW FILE########
__FILENAME__ = test_pathinfo
#######################################################################
# This file is part of Pyblosxom.
#
# Copyright (C) 2010-2011 by the Pyblosxom team.  See AUTHORS.
#
# Pyblosxom is distributed under the MIT license.  See the file
# LICENSE for distribution details.
#######################################################################
from Pyblosxom.blosxom import blosxom_process_path_info

from Pyblosxom.tests import UnitTestBase
from Pyblosxom import tools


class Testpathinfo(UnitTestBase):
    """pyblosxom.blosxom_process_path_info

    This tests default parsing of the path.
    """
    def _basic_test(self, pathinfo, expected, cfg=None, http=None, data=None):
        _http = {"PATH_INFO": pathinfo}
        if http:
            _http.update(http)
        req = self.build_request(cfg=cfg, http=_http, data=data)
        blosxom_process_path_info(args={"request": req})
        # print repr(expected), repr(req.data)
        self.cmpdict(expected, req.data)
 
    def test_root(self):
        entries = self.build_file_set([])

        self.setup_files(entries)
        try:
            # /
            self._basic_test("/",
                             {"bl_type": "dir",
                              "pi_yr": "", "pi_mo": "", "pi_da": "",
                              "flavour": "html"})
            # /index
            self._basic_test("/index", 
                             {"bl_type": "dir",
                              "pi_yr": "", "pi_mo": "", "pi_da": "",
                              "flavour": "html"})
            # /index.xml
            self._basic_test("/index.xml", 
                             {"bl_type": "dir",
                              "pi_yr": "", "pi_mo": "", "pi_da": "",
                              "flavour": "xml"})
        finally:
            self.tearDown()

    def test_files(self):
        entries = self.build_file_set(["file1.txt",
                                       "cata/file2.txt",
                                       "catb/file3.txt"])

        self.setup_files(entries)
        try:
            # /file1
            self._basic_test("/file1",
                             {"bl_type": "file",
                              "pi_yr": "", "pi_mo": "", "pi_da": "",
                              "flavour": "html"})
            # /cata/file2
            self._basic_test("/cata/file2",
                             {"bl_type": "file",
                              "pi_yr": "", "pi_mo": "", "pi_da": "",
                              "flavour": "html"})
        finally:
            self.tearDown()

    def test_categories(self):
        entries = self.build_file_set(["cata/entry1.txt",
                                       "cata/suba/entry1.txt",
                                       "catb/entry1.txt"])

        self.setup_files(entries)
        try:
            # /cata
            self._basic_test("/cata", 
                             {"bl_type": "dir",
                              "pi_yr": "", "pi_mo": "", "pi_da": "",
                              "flavour": "html"})
            # /cata/
            self._basic_test("/cata/", 
                             {"bl_type": "dir",
                              "pi_yr": "", "pi_mo": "", "pi_da": "",
                              "flavour": "html"})
            # /cata/suba
            self._basic_test("/cata/suba", 
                             {"bl_type": "dir",
                              "pi_yr": "", "pi_mo": "", "pi_da": "",
                              "flavour": "html"})
            # /cata/suba
            self._basic_test("/cata/suba/entry1.html", 
                             {"bl_type": "file",
                              "pi_yr": "", "pi_mo": "", "pi_da": "",
                              "flavour": "html"})
        finally:
            self.tearDown()

    def test_dates(self):
        tools.initialize({})

        self._basic_test("/2002",
                         {"bl_type": "dir",
                          "pi_yr": "2002", "pi_mo": "", "pi_da": "",
                          "flavour": "html"})
        self._basic_test("/2002/02",
                         {"bl_type": "dir",
                          "pi_yr": "2002", "pi_mo": "02", "pi_da": "",
                          "flavour": "html"})
        self._basic_test("/2002/02/04", 
                         {"bl_type": "dir",
                          "pi_yr": "2002", "pi_mo": "02", "pi_da": "04",
                          "flavour": "html"})

    def test_categories_and_dates(self):
        tools.initialize({})
        entries = self.build_file_set(["cata/entry1.txt",
                                       "cata/suba/entry1.txt",
                                       "catb/entry1.txt"])

        self.setup_files(entries)
        try:
            # /2006/cata/
            self._basic_test("/2006/cata/", 
                             {"bl_type": "dir",
                              "pi_yr": "2006", "pi_mo": "", "pi_da": "",
                              "flavour": "html"})
            # /2006/04/cata/
            self._basic_test("/2006/04/cata/", 
                             {"bl_type": "dir",
                              "pi_yr": "2006", "pi_mo": "04", "pi_da": "",
                              "flavour": "html"})
            # /2006/04/02/cata/
            self._basic_test("/2006/04/02/cata/", 
                             {"bl_type": "dir",
                              "pi_yr": "2006", "pi_mo": "04", "pi_da": "02",
                              "flavour": "html"})
            # /2006/04/02/cata/suba/
            self._basic_test("/2006/04/02/cata/suba/", 
                             {"bl_type": "dir",
                              "pi_yr": "2006", "pi_mo": "04", "pi_da": "02",
                              "flavour": "html"})

        finally:
            self.tearDown()

    def test_date_categories(self):
        tools.initialize({})
        entries = self.build_file_set(["2007/entry1.txt",
                                       "2007/05/entry3.txt",
                                       "cata/entry2.txt"])

        self.setup_files(entries)
        try:
            # /2007/              2007 here is a category
            self._basic_test("/2007/",
                             {"bl_type": "dir",
                              "pi_yr": "", "pi_mo": "", "pi_da": "",
                              "flavour": "html"})
            # /2007/05            2007/05 here is a category
            self._basic_test("/2007/05",
                             {"bl_type": "dir",
                              "pi_yr": "", "pi_mo": "", "pi_da": "",
                              "flavour": "html"})
            # /2007/05/entry3     2007/05/entry3 is a file
            self._basic_test("/2007/05/entry3.html",
                             {"bl_type": "file",
                              "pi_yr": "", "pi_mo": "", "pi_da": "",
                              "flavour": "html"})

        finally:
            self.tearDown()

    def test_flavour(self):
        # flavour var tests
        # The flavour is the default flavour, the extension of the request,
        # or the flav= querystring.
        root = self.get_temp_dir()

        tools.initialize({})
        entries = self.build_file_set(["2007/entry1.txt", 
                                       "2007/05/entry3.txt", 
                                       "cata/entry2.txt"])

        self.setup_files(entries)

        try:
            self._basic_test("/", {"flavour": "html"})
            self._basic_test("/index.xml", {"flavour": "xml"})
            self._basic_test("/cata/index.foo", {"flavour": "foo"})

            # FIXME - need a test for querystring
            # self._basic_test( "/cata/index.foo", http={ "QUERY_STRING": "flav=bar" },
            #                   expected={ "flavour": "bar" } )

            # test that we pick up the default_flavour config variable
            self._basic_test("/", cfg={"default_flavour": "foo"},
                             expected={"flavour": "foo"})

            # FIXME - need tests for precedence of flavour indicators

        finally:
            self.tearDown()

    def test_url(self):
        # url var tests
        # The url is the HTTP PATH_INFO env variable.
        tools.initialize({})
        entries = self.build_file_set(["2007/entry1.txt", 
                                       "2007/05/entry3.txt", 
                                       "cata/entry2.txt"])

        self.setup_files(entries)

        try:
            self._basic_test("/", {"url": "http://www.example.com/"})
            self._basic_test("/index.xml", {"url": "http://www.example.com/index.xml"})
            self._basic_test("/cata/index.foo", {"url": "http://www.example.com/cata/index.foo"})

        finally:
            self.tearDown()

    def test_pi_bl(self):
        # pi_bl var tests
        # pi_bl is the entry the user requested to see if the request indicated
        # a specific entry.  It's the empty string otherwise.
        tools.initialize({})
        entries = self.build_file_set(["2007/entry1.txt", 
                                       "2007/05/entry3.txt", 
                                       "cata/entry2.txt"]) 

        self.setup_files(entries)

        try:
            self._basic_test("", {"pi_bl": ""})
            self._basic_test("/", {"pi_bl": "/"})
            self._basic_test("/index.xml", {"pi_bl": "/index.xml"})
            self._basic_test("/2007/index.xml", {"pi_bl": "/2007/index.xml"})
            self._basic_test("/cata/entry2", {"pi_bl": "/cata/entry2"})

        finally:
            self.tearDown()

########NEW FILE########
__FILENAME__ = test_pycalendar
#######################################################################
# This file is part of Pyblosxom.
#
# Copyright (C) 2010-2011 by the Pyblosxom team.  See AUTHORS.
#
# Pyblosxom is distributed under the MIT license.  See the file
# LICENSE for distribution details.
#######################################################################

from Pyblosxom.plugins import pycalendar

import os
import unittest
import tempfile
import shutil

class PyCalendarTest(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        if hasattr(self, 'tmpdir'):
            shutil.rmtree(self.tmpdir)

    def get_datadir(self):
        return os.path.join(self.tmpdir, "datadir")

    entry1 = {"timetuple": (2010, 1, 17, 15, 48, 20, 6, 17, 0)}

    def test_generate_calendar(self):
        entry1 = dict(PyCalendarTest.entry1)

        from Pyblosxom.pyblosxom import Request
        req = Request({"datadir": self.get_datadir()},
                      {},
                      {"entry_list": [entry1],
                       "extensions": {}})
        pycalendar.cb_prepare({"request": req})

        data = req.get_data()
        cal = data["calendar"]

        cal.generate_calendar()

########NEW FILE########
__FILENAME__ = test_pycategories
#######################################################################
# This file is part of Pyblosxom.
#
# Copyright (C) 2010-2011 by the Pyblosxom team.  See AUTHORS.
#
# Pyblosxom is distributed under the MIT license.  See the file
# LICENSE for distribution details.
#######################################################################

import time
import os

from Pyblosxom.entries.base import generate_entry

from Pyblosxom.tests import PluginTest, TIMESTAMP
from Pyblosxom.plugins import pycategories

def parse_text():
    return

class Test_pycategories(PluginTest):
    def setUp(self):
        PluginTest.setUp(self, pycategories)
        self.request.get_data()["extensions"] = {"txt": parse_text}

    def tearDown(self):
        PluginTest.tearDown(self)

    def test_cb_prepare(self):
        self.assert_("categorylinks" not in self.request.get_data())
        pycategories.cb_prepare(self.args)
        self.assert_("categorylinks" in self.request.get_data())

    def test_verify_installation(self):
        self.assert_(pycategories.verify_installation)

    def test_no_categories(self):
        pycategories.cb_prepare(self.args)
        self.assertEquals(
            str(self.request.get_data()["categorylinks"]),
            "<ul class=\"categorygroup\">\n\n</ul>")

    def generate_entry(self, filename):
        filename = os.path.join(self.datadir, filename)
        if not os.path.exists(os.path.dirname(filename)):
            os.makedirs(os.path.dirname(filename))
            
        file = open(filename, "w")
        file.write("Test entry at %s\nbody body body\n" % filename)
        file.close()

    def test_categories(self):
        self.generate_entry("test1.txt")
        self.generate_entry("cat1/test_cat1.txt")
        self.generate_entry("cat2/test_cat2.txt")

        pycategories.cb_prepare(self.args)
        self.assertEquals(
            str(self.request.get_data()["categorylinks"]),
            "\n".join(
                ['<ul class="categorygroup">',
                 '<li><a href="http://bl.og//index.html">/</a> (3)</li>',
                 '<li><ul class="categorygroup">',
                 '<li><a href="http://bl.og//cat1/index.html">cat1/</a> (1)</li>',
                 '<li><a href="http://bl.og//cat2/index.html">cat2/</a> (1)</li>',
                 '</ul></li>',
                 '</ul>']))

########NEW FILE########
__FILENAME__ = test_pyfilenamemtime
#######################################################################
# This file is part of Pyblosxom.
#
# Copyright (C) 2011 by the Pyblosxom team.  See AUTHORS.
#
# Pyblosxom is distributed under the MIT license.  See the file
# LICENSE for distribution details.
#######################################################################


from Pyblosxom.tests import PluginTest
from Pyblosxom.plugins import pyfilenamemtime
import time


def mtime_to_date(mtime):
    return time.strftime('%Y-%m-%d-%H-%M', time.localtime(mtime))


class Test_pyfilenamemtime(PluginTest):
    def setUp(self):
        PluginTest.setUp(self, pyfilenamemtime)

    def test_good_filenames(self):
        get_mtime = pyfilenamemtime.get_mtime
        for mem in (('foo-2011-10-23.txt', '2011-10-23-00-00'),
                    ('foo-2011-09-22-12-00.txt', '2011-09-22-12-00')):
            mtime = get_mtime(mem[0])
            print mtime, mem[1]
            self.assertEquals(mtime_to_date(mtime), mem[1])
            
    def test_bad_filenames(self):
        get_mtime = pyfilenamemtime.get_mtime
        for mem in ('foo-2011.txt',
                    'foo-2011-10.txt',
                    'foo.txt'):
            self.assertEquals(get_mtime(mem[0]), None)

########NEW FILE########
__FILENAME__ = test_readmore
#######################################################################
# This file is part of Pyblosxom.
#
# Copyright (C) 2011 by the Pyblosxom team.  See AUTHORS.
#
# Pyblosxom is distributed under the MIT license.  See the file
# LICENSE for distribution details.
#######################################################################

import sys


from Pyblosxom.tests import PluginTest
from Pyblosxom.plugins import readmore
from Pyblosxom.pyblosxom import Request


class ReadmoreTest(PluginTest):
    def setUp(self):
        PluginTest.setUp(self, readmore)

    def test_story_no_break(self):
        req = Request({"base_url": "/"}, {}, {"bl_type": "file"})

        args = {"entry": {"body": "no break",
                          "file_path": ""},
                "request": req}

        readmore.cb_story(args)
        self.assertEquals(args["entry"]["body"], "no break")

    def test_story_break_single_file(self):
        # if showing a single file, then we nix the BREAK bit.
        req = Request({"base_url": "/"}, {}, {"bl_type": "file"})

        args = {"entry": {"body": "no BREAK break",
                          "file_path": ""},
                "request": req}

        readmore.cb_story(args)
        self.assertEquals(args["entry"]["body"], "no  break")

    def test_story_break_index(self):
        # if showing the entry in an index, then we replace the BREAK
        # with the template and nix everything after BREAK.
        req = Request({"readmore_template": "FOO", "base_url": "/"},
                      {},
                      {"bl_type": "dir"})

        args = {"entry": {"body": "no BREAK break",
                          "file_path": ""},
                "request": req}

        readmore.cb_story(args)
        self.assertEquals(args["entry"]["body"], "no FOO")

    # FIXME: write test for cb_start -- requires docutils or
    # mocking framework

########NEW FILE########
__FILENAME__ = test_tags
#######################################################################
# This file is part of Pyblosxom.
#
# Copyright (C) 2010-2011 by the Pyblosxom team.  See AUTHORS.
#
# Pyblosxom is distributed under the MIT license.  See the file
# LICENSE for distribution details.
#######################################################################

import tempfile
import shutil
import os

from Pyblosxom.tests import PluginTest
from Pyblosxom.plugins import tags
from Pyblosxom.pyblosxom import Request

class TagsTest(PluginTest):
    def setUp(self):
        PluginTest.setUp(self, tags)
        self.tmpdir = tempfile.mkdtemp() 

    def get_datadir(self):
        return os.path.join(self.tmpdir, "datadir")

    def tearDown(self):
        PluginTest.tearDown(self)
        try:
            shutil.rmtree(self.tmpdir)
        except OSError:
            pass
                
    def test_get_tagsfile(self):
        req = Request({"datadir": self.get_datadir()}, {}, {})

        cfg = {"datadir": self.get_datadir()}
        self.assertEquals(tags.get_tagsfile(cfg),
                          os.path.join(self.get_datadir(), os.pardir,
                                       "tags.index"))
        
        tags_filename = os.path.join(self.get_datadir(), "tags.db")
        cfg = {"datadir": self.get_datadir(), "tags_filename": tags_filename}
        self.assertEquals(tags.get_tagsfile(cfg), tags_filename)

    def test_tag_cloud_no_tags(self):
        # test no tags
        self.request.get_data()["tagsdata"] = {}
        
        tags.cb_head(self.args)
        self.assertEquals(
            str(self.args["entry"]["tagcloud"]),
            "\n".join(
                ["<p>",
                 "</p>"]))

    def test_tag_cloud_one_tag(self):
        # test no tags
        self.request.get_data()["tagsdata"] = {
            "tag2": ["a"],
            }
        
        tags.cb_head(self.args)
        self.assertEquals(
            str(self.args["entry"]["tagcloud"]),
            "\n".join(
                ["<p>",
                 '<a class="biggestTag" href="http://bl.og//tag/tag2">tag2</a>',
                 "</p>"]))

    def test_tag_cloud_many_tags(self):
        # test no tags
        self.request.get_data()["tagsdata"] = {
            "tag1": ["a", "b", "c", "d", "e", "f"],
            "tag2": ["a", "b", "c", "d"],
            "tag3": ["a"]
            }
        
        tags.cb_head(self.args)
        self.assertEquals(
            str(self.args["entry"]["tagcloud"]),
            "\n".join(
                ["<p>",
                 '<a class="biggestTag" href="http://bl.og//tag/tag1">tag1</a>',
                 '<a class="biggestTag" href="http://bl.og//tag/tag2">tag2</a>',
                 '<a class="smallestTag" href="http://bl.og//tag/tag3">tag3</a>',
                 "</p>"]))

########NEW FILE########
__FILENAME__ = test_tools
# -*- coding: utf-8 -*-
#######################################################################
# This file is part of Pyblosxom.
#
# Copyright (C) 2010-2011 by the Pyblosxom team.  See AUTHORS.
#
# Pyblosxom is distributed under the MIT license.  See the file
# LICENSE for distribution details.
#######################################################################

import string
import os
import os.path

from Pyblosxom.tests import UnitTestBase
from Pyblosxom import tools, pyblosxom

class TestVAR_REGEXP(UnitTestBase):
    """tools._VAR_REGEXP

    This tests the various syntaxes for variables in Pyblosxom
    templates.
    """
    def _get_match(self, compiled_regexp, s):
        r = compiled_regexp.search(s)
        # print repr(r)
        return r and r.group(1)

    def test_escaped_variables(self):
        self.eq_(self._get_match(tools._VAR_REGEXP, "\\$test"), None)
        # FIXME - this is bad behavior
        self.eq_(self._get_match(tools._VAR_REGEXP, "\\\\$test"), None)

    def test_dollar_then_string(self):
        for mem in (("$test", "test"),
                    ("$test-test", "test-test"),
                    ("$test_test", "test_test"),
                    (" $test", "test"),
                    ("other stuff $test", "test"),
                    ("other $test stuff", "test"),
                    ("other $test $test2 stuff", "test"),
                    ("español $test stuff", "test")):
            self.eq_(self._get_match(tools._VAR_REGEXP, mem[0]), mem[1])

    def test_delimiters(self):
        for c in ('|', '=', '+', ' ', '$', '<', '>'):
            self.eq_(self._get_match(tools._VAR_REGEXP, "$test%s1" % c), "test")

    def test_namespace(self):
        for mem in (("$foo::bar", "foo::bar"),
                    (" $foo::bar ", "foo::bar"),
                    ("other $foo::bar stuff", "foo::bar")):
            self.eq_(self._get_match(tools._VAR_REGEXP, mem[0]), mem[1])

    def test_single_function(self):
        for mem in (("$foo()", "foo()"),
                    (" $foo() ", "foo()"),
                    ("other $foo() stuff", "foo()"),
                    ("other $foo::bar() stuff", "foo::bar()")):
            self.eq_(self._get_match(tools._VAR_REGEXP, mem[0]), mem[1])

    def test_function_with_arguments(self):
        for mem in (('$foo("arg1")', 'foo("arg1")'),
                    ('$foo("arg1", 1)', 'foo("arg1", 1)'),
                    ('$foo("español", 1)', 'foo("español", 1)')):
            self.eq_(self._get_match(tools._VAR_REGEXP, mem[0]), mem[1])

    def test_parens(self):
        for mem in (("$(foo)", "(foo)"),
                    ("$(foo())", "(foo())"),
                    ("$(foo::bar)", "(foo::bar)"),
                    ("$(foo::bar())", "(foo::bar())"),
                    ("$(foo::bar(1, 2, 3))", "(foo::bar(1, 2, 3))")):
            self.eq_(self._get_match(tools._VAR_REGEXP, mem[0]), mem[1])

req = pyblosxom.Request({}, {}, {})

class Testparse(UnitTestBase):
    """tools.parse"""
    def setUp(self):
        UnitTestBase.setUp(self)

    def test_simple(self):
        env = {"foo": "FOO",
               "country": "España"}

        for mem in (("foo foo foo", "foo foo foo"),
                    ("foo $foo foo", "foo FOO foo"),
                    ("foo $foor foo", "foo  foo"),
                    ("foo $country foo", "foo España foo")):
            self.eq_(tools.parse(req, env, mem[0]), mem[1])

    def test_delimited(self):
        env = {"foo": "FOO",
               "country": "España"}

        for mem in (("foo $(foo) foo", "foo FOO foo"),
                    ("foo $(foor) foo", "foo  foo"),
                    ("foo $(country) foo", "foo España foo")):
            self.eq_(tools.parse(req, env, mem[0]), mem[1])

    def test_functions(self):
        for mem in (({"foo": lambda req, vd: "FOO"}, "foo foo foo", "foo foo foo"),
                    ({"foo": lambda req, vd: "FOO"}, "foo $foo() foo", "foo FOO foo"),
                    ({"foo": lambda req, vd, z: z}, "foo $foo('a') foo", "foo a foo"),
                    ({"foo": lambda req, vd, z: z}, "foo $foo(1) foo", "foo 1 foo"),
                    ({"foo": lambda req, vd, z: z}, "foo $foo($money) foo", "foo $money foo"),
                    ({"foo": lambda req, vd, z: z, "bar": "BAR"}, "foo $foo(bar) foo", "foo BAR foo"),
                    ({"foo": lambda req, vd, z: z, "bar": "BAR"}, "foo $foo($bar) foo", "foo BAR foo"),
                    ({"lang": lambda req, vd: "español"}, "foo $(lang) foo", "foo español foo"),
                    # Note: functions can return unicode which will get 
                    # converted to blog_encoding
                    ({"lang": lambda req, vd: u"español"}, "español $(lang)", "español español")):
            self.eq_(tools.parse(req, mem[0], mem[1]), mem[2])

    def test_functions_old_behavior(self):
        # test the old behavior that allowed for functions that have no
        # arguments--in this case we don't pass a request object in
        self.eq_(tools.parse(req, {"foo": (lambda : "FOO")}, "foo $foo() foo"), "foo FOO foo")

    def test_functions_with_args_that_have_commas(self):
        env = {"foo": lambda req, vd, x: (x + "A"),
               "foo2": lambda req, vd, x, y: (y + x)}

        for mem in (('$foo("ba,ar")', "ba,arA"),
                    ('$foo2("a,b", "c,d")', "c,da,b")):
            self.eq_(tools.parse(req, env, mem[0]), mem[1])

    def test_functions_with_var_args(self):
        def pt(d, t):
            return tools.parse(req, d, t)

        vd = {"foo": lambda req, vd, x: (x + "A"),
              "bar": "BAR",
              "lang": "Español",
              "ulang": u"Español"}

        for mem in (
                    # this bar is a string
                    ("foo $foo('bar') foo", "foo barA foo"),

                    # this bar is also a string
                    ('foo $foo("bar") foo', "foo barA foo"),

                    # this bar is an identifier which we lookup in the 
                    # var_dict and pass into the foo function
                    ("foo $foo(bar) foo", "foo BARA foo"),

                    # variables that have utf-8 characters
                    ("foo $foo(lang) foo", "foo EspañolA foo"),
                    ("foo $foo(ulang) foo", "foo EspañolA foo")):
            self.eq_(tools.parse(req, vd, mem[0]), mem[1])

    def test_escaped(self):
        def pt(d, t):
            ret = tools.parse(req, d, t)
            # print ret
            return ret

        vd = dict(tools.STANDARD_FILTERS)
        vd.update({"foo": "'foo'",
                   "lang": "'español'"})
        for mem in (
                    # this is old behavior
                    ("$foo_escaped", "&#x27;foo&#x27;"),

                    # this is the new behavior using the escape filter
                    ("$escape(foo)", "&#x27;foo&#x27;"),

                    # escaping with utf-8 characters
                    ("$escape(lang)", "&#x27;español&#x27;")):
            self.eq_(pt(vd, mem[0]), mem[1])


class Testcommasplit(UnitTestBase):
    """tools.commasplit"""
    def test_commasplit(self):
        tcs = tools.commasplit
        for mem in ((None, []),
                    ("", [""]),
                    ("a", ["a"]),
                    ("a b c", ["a b c"]),
                    ("a, b, c", ["a", " b", " c"]),
                    ("a, 'b, c'", ["a", " 'b, c'"]),
                    ("a, \"b, c\"", ["a", " \"b, c\""])):
            self.eq_(tools.commasplit(mem[0]), mem[1])
 
class Testis_year(UnitTestBase):
    """tools.is_year"""
    def test_must_be_four_digits(self):
        for mem in (("abab", 0),
                    ("ab", 0),
                    ("199", 0),
                    ("19999", 0),
                    ("1997", 1),
                    ("2097", 1)):
            self.eq_(tools.is_year(mem[0]), mem[1])

    def test_must_start_with_19_or_20(self):
        for mem in (("3090", 0),
                    ("0101", 0)):
            self.eq_(tools.is_year(mem[0]), mem[1])

    def test_everything_else_returns_false(self):
        for mem in ((None, 0),
                    ("", 0),
                    ("ab", 0),
                    ("97", 0)):
            self.eq_(tools.is_year(mem[0]), mem[1])

class Test_generate_rand_str(UnitTestBase):
    """tools.generate_rand_str

    Note: This is a mediocre test because generate_rand_str produces a
    string that's of random length and random content.  It's possible
    for this test to pass even when the code is bad.
    """
    def _gen_checker(self, s, minlen, maxlen):
        assert len(s) >= minlen and len(s) <= maxlen
        for c in s:
            assert c in string.letters or c in string.digits

    def test_generates_a_random_string(self):
        for i in range(5):
            self._gen_checker(tools.generate_rand_str(), 5, 10)

    def test_generates_a_random_string_between_minlen_and_maxlen(self):
        for i in range(5):
             self._gen_checker(tools.generate_rand_str(4, 10), 4, 10)

        for i in range(5):
            self._gen_checker(tools.generate_rand_str(3, 12), 3, 12)

class Testescape_text(UnitTestBase):
    """tools.escape_text"""
    def test_none_to_none(self):
        self.eq_(tools.escape_text(None), None)

    def test_empty_string_to_empty_string(self):
        self.eq_(tools.escape_text(""), "")

    def test_single_quote_to_pos(self):
        self.eq_(tools.escape_text("a'b"), "a&#x27;b")

    def test_double_quote_to_quot(self):
        self.eq_(tools.escape_text("a\"b"), "a&quot;b")

    def test_greater_than(self):
        self.eq_(tools.escape_text("a>b"), "a&gt;b")

    def test_lesser_than(self):
        self.eq_(tools.escape_text("a<b"), "a&lt;b")

    def test_ampersand(self):
        self.eq_(tools.escape_text("a&b"), "a&amp;b")

    def test_complicated_case(self):
        self.eq_(tools.escape_text("a&>b"), "a&amp;&gt;b")

    def test_everything_else_unchanged(self):
        for mem in ((None, None),
                    ("", ""),
                    ("abc", "abc")):
            self.eq_(tools.escape_text(mem[0]), mem[1])

class Testurlencode_text(UnitTestBase):
    """tools.urlencode_text"""
    def test_none_to_none(self):
        self.eq_(tools.urlencode_text(None), None)

    def test_empty_string_to_empty_string(self):
        self.eq_(tools.urlencode_text(""), "")

    def test_equals_to_3D(self):
        self.eq_(tools.urlencode_text("a=c"), "a%3Dc")

    def test_ampersand_to_26(self):
        self.eq_(tools.urlencode_text("a&c"), "a%26c")

    def test_space_to_20(self):
        self.eq_(tools.urlencode_text("a c"), "a%20c")

    def test_utf8(self):
        self.eq_(tools.urlencode_text("español"), "espa%C3%B1ol")

    def test_everything_else_unchanged(self):
        for mem in ((None, None),
                    ("", ""),
                    ("abc", "abc")):
            self.eq_(tools.urlencode_text(mem[0]), mem[1])

class TestStripper(UnitTestBase):
    """tools.Stripper class"""

    def _strip(self, text):
        s = tools.Stripper()
        s.feed(text)
        s.close()
        return s.gettext()

    def test_replaces_html_markup_from_string_with_space(self):
        s = tools.Stripper()
        for mem in (("", ""),
                    ("abc", "abc"),
                    ("<b>abc</b>", " abc "),
                    ("abc<br />", "abc "),
                    ("abc <b>def</b> ghi", "abc  def  ghi"),
                    ("abc <b>español</b> ghi", "abc  español  ghi")):
            self.eq_(self._strip(mem[0]), mem[1])

class Testimportname(UnitTestBase):
    """tools.importname"""
    def setUp(self):
        UnitTestBase.setUp(self)
        tools._config = {}

    def tearDown(self):
        UnitTestBase.tearDown(self)
        if "_config" in tools.__dict__:
            del tools.__dict__["_config"]

    def _c(self, mn, n):
        m = tools.importname(mn, n)
        # print repr(m)
        return m

    def test_goodimport(self):
        import string
        self.eq_(tools.importname("", "string"), string)

        import os.path
        self.eq_(tools.importname("os", "path"), os.path)

    def test_badimport(self):
        self.eq_(tools.importname("", "foo"), None)

class Testwhat_ext(UnitTestBase):
    """tools.what_ext"""
    def get_ext_dir(self):
        return os.path.join(self.get_temp_dir(), "ext")
        
    def setUp(self):
        """
        Creates the directory with some files in it.
        """
        UnitTestBase.setUp(self)
        self._files = ["a.txt", "b.html", "c.txtl", "español.txt"]
        os.mkdir(self.get_ext_dir())

        for mem in self._files:
            f = open(os.path.join(self.get_ext_dir(), mem), "w")
            f.write("lorem ipsum")
            f.close()

    def test_returns_extension_if_file_has_extension(self):
        d = self.get_ext_dir()
        self.eq_(tools.what_ext(["txt", "html"], os.path.join(d, "a")),
                 "txt")
        self.eq_(tools.what_ext(["txt", "html"], os.path.join(d, "b")),
                 "html")
        self.eq_(tools.what_ext(["txt", "html"], os.path.join(d, "español")),
                 "txt")

    def test_returns_None_if_extension_not_present(self):
        d = self.get_ext_dir()
        self.eq_(tools.what_ext([], os.path.join(d, "a")), None)
        self.eq_(tools.what_ext(["html"], os.path.join(d, "a")), None)

## class Testrun_callback:
##     """tools.run_callback

##     This tests run_callback functionality.
##     """
##     def test_run_callback(self):
##         def fun1(args):
##             eq_(args["x"], 0)
##             return {"x": 1}

##         def fun2(args):
##             eq_(args["x"], 1)
##             return {"x": 2}

##         def fun3(args):
##             eq_(args["x"], 2)
##             return {"x": 3}

##         args = {"x": 0}
##         ret = tools.run_callback([fun1, fun2, fun3], args,
##                                  mappingfunc=lambda x,y: y)
##         eq_(ret["x"], 3)

class Testconvert_configini_values(UnitTestBase):
    """tools.convert_configini_values

    This tests config.ini -> config conversions.
    """
    def test_empty(self):
        self.eq_(tools.convert_configini_values({}), {})

    def test_no_markup(self):
        self.eq_(tools.convert_configini_values({"a": "b"}), {"a": "b"})

    def test_integers(self):
        for mem in (({"a": "1"}, {"a": 1}),
                    ({"a": "1", "b": "2"}, {"a": 1, "b": 2}),
                    ({"a": "10"}, {"a": 10}),
                    ({"a": "100"}, {"a": 100}),
                    ({"a": " 100  "}, {"a": 100})):
            self.eq_(tools.convert_configini_values(mem[0]), mem[1])

    def test_strings(self):
        for mem in (({"a": "'b'"}, {"a": "b"}),
                    ({"a": "\"b\""}, {"a": "b"}),
                    ({"a": "   \"b\" "}, {"a": "b"}),
                    ({"a": "español"}, {"a": "español"}),
                    ({"a": "'español'"}, {"a": "español"})):
            self.eq_(tools.convert_configini_values(mem[0]), mem[1])

    def test_lists(self):
        for mem in (({"a": "[]"}, {"a": []}),
                    ({"a": "[1]"}, {"a": [1]}),
                    ({"a": "[1, 2]"}, {"a": [1, 2]}),
                    ({"a": "  [1 ,2 , 3]"}, {"a": [1, 2, 3]}),
                    ({"a": "['1' ,\"2\" , 3]"}, {"a": ["1", "2", 3]})):
            self.eq_(tools.convert_configini_values(mem[0]), mem[1])

    def test_syntax_exceptions(self):
        for mem in ({"a": "'b"},
                    {"a": "b'"},
                    {"a": "\"b"},
                    {"a": "b\""},
                    {"a": "[b"},
                    {"a": "b]"}):
            self.assertRaises(tools.ConfigSyntaxErrorException,
                              tools.convert_configini_values, mem)

    # FIXME - test tools.walk

    # FIXME - test filestat

########NEW FILE########
__FILENAME__ = test_w3cdate
#######################################################################
# This file is part of Pyblosxom.
#
# Copyright (C) 2010-2011 by the Pyblosxom team.  See AUTHORS.
#
# Pyblosxom is distributed under the MIT license.  See the file
# LICENSE for distribution details.
#######################################################################

from Pyblosxom.plugins import w3cdate

import os
import unittest
import time

class W3CDateTest(unittest.TestCase):
    entry1 = {"timetuple": (2010, 1, 17, 15, 48, 20, 6, 17, 0)}
    entry2 = {"timetuple": (2010, 1, 17, 15, 58, 45, 6, 17, 0)}
    entry3 = {"timetuple": (2010, 1, 11, 21, 6, 26, 0, 11, 0)}

    def test_get_formatted_date(self):
        gfd = w3cdate.get_formatted_date
        #save old TZ environment for restoring
        tz = os.environ.get('TZ')
        #we expect US EASTERN time without DST
        os.environ['TZ'] = 'EST+05EST+05,M4.1.0,M10.5.0'
        time.tzset()
        self.assertEquals(gfd(W3CDateTest.entry1),
                          "2010-01-17T15:48:20-05:00")
        # reset time zone to whatever it was
        if tz is None:
            del os.environ['TZ']
        else:
            os.environ['TZ'] = tz
        time.tzset()

    def test_head_and_foot(self):
        from Pyblosxom.pyblosxom import Request
        gfd = w3cdate.get_formatted_date

        entry1 = dict(W3CDateTest.entry1)
        entry2 = dict(W3CDateTest.entry2)
        entry3 = dict(W3CDateTest.entry3)

        req = Request({}, {}, {"entry_list": [entry1, entry2, entry3]})
        entry = {}
        args = {"entry": entry, "request": req}
        w3cdate.cb_head(args)
        self.assertEquals(entry["w3cdate"], gfd(self.entry1))

        req = Request({}, {}, {"entry_list": [entry3, entry2, entry1]})
        entry = {}
        args = {"entry": entry, "request": req}
        w3cdate.cb_head(args)
        self.assertEquals(entry["w3cdate"], gfd(self.entry3))

    def test_story(self):
        entry = dict(self.entry1)
        args = {"entry": entry}
        w3cdate.cb_story(args)
        self.assertEquals(entry['w3cdate'], w3cdate.get_formatted_date(entry))

########NEW FILE########
__FILENAME__ = test_yeararchives
#######################################################################
# This file is part of Pyblosxom.
#
# Copyright (C) 2010-2011 by the Pyblosxom team.  See AUTHORS.
#
# Pyblosxom is distributed under the MIT license.  See the file
# LICENSE for distribution details.
#######################################################################

import time
import os

from Pyblosxom.tests import PluginTest, TIMESTAMP
from Pyblosxom.plugins import yeararchives

class Test_yeararchives(PluginTest):
    def setUp(self):
        PluginTest.setUp(self, yeararchives)

    def tearDown(self):
        PluginTest.tearDown(self)

    def test_parse_path_info(self):
        for testin, testout in [
            ("", None),
            ("/", None),
            ("/2003", ("2003", None)),
            ("/2003/", ("2003", None)),
            ("/2003/index", ("2003", None)),
            ("/2003/index.flav", ("2003", "flav")),
            ]:
 
            self.assertEquals(yeararchives.parse_path_info(testin),
                              testout)

########NEW FILE########
__FILENAME__ = tools
#######################################################################
# This file is part of Pyblosxom.
#
# Copyright (C) 2003-2011 by the Pyblosxom team.  See AUTHORS.
#
# Pyblosxom is distributed under the MIT license.  See the file
# LICENSE for distribution details.
#######################################################################

"""Utility module for functions that are useful to Pyblosxom and plugins.
"""

import sgmllib
import re
import os
import time
import os.path
import stat
import sys
import locale
import urllib
import inspect
import textwrap

# Pyblosxom imports
from Pyblosxom import plugin_utils

# Note: month names tend to differ with locale

# month name (Jan) to number (1)
month2num = None
# month number (1) to name (Jan)
num2month = None
# list of all month numbers and names
MONTHS    = None

# regular expression for detection and substituion of variables.
_VAR_REGEXP = re.compile(r"""
    (?<!\\)   # if the $ is escaped, then this isn't a variable
    \$        # variables start with a $
    (
        (?:\w|\-|::\w)+       # word char, - or :: followed by a word char
        (?:
            \(                # an open paren
            .*?               # followed by non-greedy bunch of stuff
            (?<!\\)\)         # with an end paren that's not escaped
        )?    # 0 or 1 of these ( ... ) blocks
    |
        \(
        (?:\w|\-|::\w)+       # word char, - or :: followed by a word char
        (?:
            \(                # an open paren
            .*?               # followed by non-greedy bunch of stuff
            (?<!\\)\)         # with an end paren that's not escaped
        )?    # 0 or 1 of these ( ... ) blocks
        \)
    )
    """, re.VERBOSE)

# reference to the pyblosxom config dict
_config = {}


def initialize(config):
    """Initializes the tools module.

    This gives the module a chance to use configuration from the
    pyblosxom config.py file.

    This should be called from ``Pyblosxom.pyblosxom.Pyblosxom.initialize``.
    """
    global _config
    _config = config

    # Month names tend to differ with locale
    global month2num

    try:
        month2num = {'nil': '00',
                     locale.nl_langinfo(locale.ABMON_1): '01',
                     locale.nl_langinfo(locale.ABMON_2): '02',
                     locale.nl_langinfo(locale.ABMON_3): '03',
                     locale.nl_langinfo(locale.ABMON_4): '04',
                     locale.nl_langinfo(locale.ABMON_5): '05',
                     locale.nl_langinfo(locale.ABMON_6): '06',
                     locale.nl_langinfo(locale.ABMON_7): '07',
                     locale.nl_langinfo(locale.ABMON_8): '08',
                     locale.nl_langinfo(locale.ABMON_9): '09',
                     locale.nl_langinfo(locale.ABMON_10): '10',
                     locale.nl_langinfo(locale.ABMON_11): '11',
                     locale.nl_langinfo(locale.ABMON_12): '12'}

    except AttributeError:
        # Windows doesn't have nl_langinfo, so we use one that
        # only return English.
        # FIXME - need a better hack for this issue.
        month2num = {'nil': '00',
                     "Jan": '01',
                     "Feb": '02',
                     "Mar": '03',
                     "Apr": '04',
                     "May": '05',
                     "Jun": '06',
                     "Jul": '07',
                     "Aug": '08',
                     "Sep": '09',
                     "Oct": '10',
                     "Nov": '11',
                     "Dec": '12'}

    # This is not python 2.1 compatible (Nifty though)
    # num2month = dict(zip(month2num.itervalues(), month2num))
    global num2month
    num2month = {}
    for month_abbr, month_num in month2num.items():
        num2month[month_num] = month_abbr
        num2month[int(month_num)] = month_abbr

    # all the valid month possibilities
    global MONTHS
    MONTHS = num2month.keys() + month2num.keys()


def pwrap(s):
    """Wraps the text and prints it.
    """
    starter = ""
    linesep = os.linesep
    if s.startswith("- "):
        starter = "- "
        s = s[2:]
        linesep = os.linesep + "  "

    print starter + linesep.join(textwrap.wrap(s, 72))


def pwrap_error(s):
    """Wraps an error message and prints it to stderr.
    """
    starter = ""
    linesep = os.linesep
    if s.startswith("- "):
        starter = "- "
        s = s[2:]
        linesep = os.linesep + "  "

    sys.stderr.write(starter + linesep.join(textwrap.wrap(s, 72)) + "\n")


def deprecated_function(func):
    def _deprecated_function(*args, **kwargs):
        return func(*args, **kwargs)

    _deprecated_function.__doc__ = ("DEPRECATED.  Use %s instead." %
                                    func.__name__)
    _deprecated_function.__dict__.update(func.__dict__)
    return _deprecated_function


class ConfigSyntaxErrorException(Exception):
    """Thrown when ``convert_configini_values`` encounters a syntax
    error.
    """
    pass


def convert_configini_values(configini):
    """Takes a dict containing config.ini style keys and values, converts
    the values, and returns a new config dict.

    :param confini: dict containing the config.ini style keys and values

    :raises ConfigSyntaxErrorException: when there's a syntax error

    :returns: new config dict
    """
    def s_or_i(text):
        """
        Takes a string and if it begins with \" or \' and ends with
        \" or \', then it returns the string.  If it's an int, returns
        the int.  Otherwise it returns the text.
        """
        text = text.strip()
        if (((text.startswith('"') and not text.endswith('"'))
             or (not text.startswith('"') and text.endswith('"')))):
            raise ConfigSyntaxErrorException(
                "config syntax error: string '%s' missing start or end \"" %
                text)
        elif (((text.startswith("'") and not text.endswith("'"))
               or (not text.startswith("'") and text.endswith("'")))):
            raise ConfigSyntaxErrorException(
                "config syntax error: string '%s' missing start or end '" %
                text)
        elif text.startswith('"') and text.endswith('"'):
            return text[1:-1]
        elif text.startswith("'") and text.endswith("'"):
            return text[1:-1]
        elif text.isdigit():
            return int(text)
        return text

    config = {}
    for key, value in configini.items():
        # in configini.items, we pick up a local_config which seems
        # to be a copy of what's in configini.items--puzzling.
        if isinstance(value, dict):
            continue

        value = value.strip()
        if (((value.startswith("[") and not value.endswith("]"))
             or (not value.startswith("[") and value.endswith("]")))):
            raise ConfigSyntaxErrorException(
                "config syntax error: list '%s' missing [ or ]" %
                value)
        elif value.startswith("[") and value.endswith("]"):
            value2 = value[1:-1].strip().split(",")
            if len(value2) == 1 and value2[0] == "":
                # handle the foo = [] case
                config[key] = []
            else:
                config[key] = [s_or_i(s.strip()) for s in value2]
        else:
            config[key] = s_or_i(value)

    return config


def escape_text(s):
    """Takes in a string and converts:

    * ``&`` to ``&amp;``
    * ``>`` to ``&gt;``
    * ``<`` to ``&lt;``
    * ``\"`` to ``&quot;``
    * ``'`` to ``&#x27;``
    * ``/`` to ``&#x2F;``

    Note: if ``s`` is ``None``, then we return ``None``.

    >>> escape_text(None)
    >>> escape_text("")
    ''
    >>> escape_text("a'b")
    'a&#x27;b'
    >>> escape_text('a"b')
    'a&quot;b'
    """
    if not s:
        return s

    for mem in (("&", "&amp;"), (">", "&gt;"), ("<", "&lt;"), ("\"", "&quot;"),
                ("'", "&#x27;"), ("/", "&#x2F;")):
        s = s.replace(mem[0], mem[1])
    return s


def urlencode_text(s):
    """Calls ``urllib.quote`` on the string ``s``.

    Note: if ``s`` is ``None``, then we return ``None``.

    >>> urlencode_text(None)
    >>> urlencode_text("")
    ''
    >>> urlencode_text("a c")
    'a%20c'
    >>> urlencode_text("a&c")
    'a%26c'
    >>> urlencode_text("a=c")
    'a%3Dc'

    """
    if not s:
        return s

    return urllib.quote(s)

STANDARD_FILTERS = {"escape": lambda req, vd, s: escape_text(s),
                    "urlencode": lambda req, vd, s: urlencode_text(s)}


class Stripper(sgmllib.SGMLParser):
    """
    SGMLParser that removes HTML formatting code.
    """
    def __init__(self):
        """
        Initializes the instance.
        """
        self.data = []
        sgmllib.SGMLParser.__init__(self)

    def unknown_starttag(self, tag, attrs):
        """
        Implements unknown_starttag.  Appends a space to the buffer.
        """
        self.data.append(" ")

    def unknown_endtag(self, tag):
        """
        Implements unknown_endtag.  Appends a space to the buffer.
        """
        self.data.append(" ")

    def handle_data(self, data):
        """
        Implements handle_data.  Appends data to the buffer.
        """
        self.data.append(data)

    def gettext(self):
        """
        Returns the buffer.
        """
        return "".join(self.data)


def commasplit(s):
    """
    Splits a string that contains strings by comma.  This is
    more involved than just an ``s.split(",")`` because this handles
    commas in strings correctly.

    Note: commasplit doesn't remove extranneous spaces.

    >>> commasplit(None)
    []
    >>> commasplit("")
    ['']
    >>> commasplit("a")
    ['a']
    >>> commasplit("a, b, c")
    ['a', ' b', ' c']
    >>> commasplit("'a', 'b, c'")
    ["'a'", " 'b, c'"]
    >>> commasplit("'a', \\"b, c\\"")
    ["'a'", ' \"b, c\"']

    :param s: the string to split

    :returns: list of strings
    """
    if s is None:
        return []

    if not s:
        return [""]

    start_string = None
    t = []
    l = []

    for c in s:
        if c == start_string:
            start_string = None
            t.append(c)
        elif c == "'" or c == '"':
            start_string = c
            t.append(c)
        elif not start_string and c == ",":
            l.append("".join(t))
            t = []
        else:
            t.append(c)
    if t:
        l.append("".join(t))
    return l


class Replacer:
    """
    Class for replacing variables in a template

    This class is a utility class used to provide a bound method to the
    ``re.sub()`` function.  Originally from OPAGCGI.
    """
    def __init__(self, request, encoding, var_dict):
        """
        Its only duty is to populate itself with the replacement
        dictionary passed.

        :param request: the Request object
        :param encoding: the encoding to use.  ``utf-8`` is good.
        :param var_dict: the dict containing variable substitutions
        """
        self._request = request
        self._encoding = encoding
        self.var_dict = var_dict

    def replace(self, matchobj):
        """
        This is passed a match object by ``re.sub()`` which represents
        a template variable without the ``$``.  parse manipulates the
        variable and returns the expansion of that variable using the
        following rules:

        1. if the variable ``v`` is an identifier, but not in the
           variable dict, then we return the empty string, or

        2. if the variable ``v`` is an identifier in the variable
           dict, then we return ``var_dict[v]``, or

        3. if the variable ``v`` is a function call where the function
           is an identifier in the variable dict, then

           - if ``v`` has no passed arguments and the function takes
             no arguments we return ``var_dict[v]()`` (this is the old
             behavior

           - if ``v`` has no passed arguments and the function takes
             two arguments we return ``var_dict[v](request, vd)``

           - if ``v`` has passed arguments, we return
             ``var_dict[v](request, vd, *args)`` after some mild
             processing of the arguments

        Also, for backwards compatibility reasons, we convert things
        like::

            $id_escaped
            $id_urlencoded
            $(id_escaped)
            $(id_urlencoded)

        to::

            $escape(id)
            $urlencode(id)

        :param matchobj: the regular expression match object

        :returns: the substituted string
        """
        vd = self.var_dict
        request = self._request
        key = matchobj.group(1)

        # if the variable is using $(foo) syntax, then we strip the
        # outer parens here.
        if key.startswith("(") and key.endswith(")"):
            key = key[1:-1]

        # do this for backwards-compatibility reasons
        if key.endswith("_escaped"):
            key = "escape(%s)" % key[:-8]
        elif key.endswith("_urlencoded"):
            key = "urlencode(%s)" % key[:-11]

        if key.find("(") != -1 and key.rfind(")") > key.find("("):
            args = key[key.find("(")+1:key.rfind(")")]
            key = key[:key.find("(")]
        else:
            args = None

        if not vd.has_key(key):
            return ""

        r = vd[key]

        # if the value turns out to be a function, then we call it
        # with the args that we were passed.
        if callable(r):
            if args:
                def fix(s, vd=vd):
                    # if it's an int, return an int
                    if s.isdigit():
                        return int(s)
                    # if it's a string, return a string
                    if s.startswith("'") or s.startswith('"'):
                        return s[1:-1]
                    # otherwise it might be an identifier--check
                    # the vardict and return the value if it's in
                    # there
                    if vd.has_key(s):
                        return vd[s]
                    if s.startswith("$") and vd.has_key(s[1:]):
                        return vd[s[1:]]
                    return s
                args = [fix(arg.strip()) for arg in commasplit(args)]

                # stick the request and var_dict in as the first and
                # second arguments
                args.insert(0, vd)
                args.insert(0, request)

                r = r(*args)

            elif len(inspect.getargspec(r)[0]) == 2:
                r = r(request, vd)

            else:
                # this case is here for handling the old behavior
                # where functions took no arguments
                r = r()

        # convert non-strings to strings
        if not isinstance(r, str):
            if isinstance(r, unicode):
                r = r.encode(self._encoding)
            else:
                r = str(r)

        return r


def parse(request, var_dict, template):
    """
    This method parses the ``template`` passed in using ``Replacer``
    to expand template variables using values in the ``var_dict``.

    Originally based on OPAGCGI, but mostly re-written.

    :param request: the Request object
    :param var_dict: the dict holding name/value pair variable replacements
    :param template: the string template we're expanding variables in.

    :returns: the template string with template variables expanded.
    """
    encoding = request.config.get("blog_encoding", "utf-8")
    replacer = Replacer(request, encoding, var_dict)
    return _VAR_REGEXP.sub(replacer.replace, template)


def walk(request, root='.', recurse=0, pattern='', return_folders=0):
    """
    This function walks a directory tree starting at a specified root
    folder, and returns a list of all of the files (and optionally
    folders) that match our pattern(s). Taken from the online Python
    Cookbook and modified to own needs.

    It will look at the config "ignore_directories" for a list of
    directories to ignore.  It uses a regexp that joins all the things
    you list.  So the following::

       config.py["ignore_directories"] = ["CVS", "dev/pyblosxom"]

    turns into the regexp::

       .*?(CVS|dev/pyblosxom)$

    It will also skip all directories that start with a period.

    :param request: the Request object
    :param root: the root directory to walk
    :param recurse: the depth of recursion; defaults to 0 which goes all
                    the way down
    :param pattern: the regexp object for matching files; defaults to
                    '' which causes Pyblosxom to return files with
                    file extensions that match those the entryparsers
                    handle
    :param return_folders: True if you want only folders, False if you
                    want files AND folders

    :returns: a list of file paths.
    """
    # expand pattern
    if not pattern:
        ext = request.get_data()['extensions']
        pattern = re.compile(r'.*\.(' + '|'.join(ext.keys()) + r')$')

    ignore = request.get_configuration().get("ignore_directories", None)
    if isinstance(ignore, str):
        ignore = [ignore]

    if ignore:
        ignore = [re.escape(i) for i in ignore]
        ignorere = re.compile(r'.*?(' + '|'.join(ignore) + r')$')
    else:
        ignorere = None

    # must have at least root folder
    if not os.path.isdir(root):
        return []

    return _walk_internal(root, recurse, pattern, ignorere, return_folders)

# We do this for backwards compatibility reasons.
Walk = deprecated_function(walk)


def _walk_internal(root, recurse, pattern, ignorere, return_folders):
    """
    Note: This is an internal function--don't use it and don't expect
    it to stay the same between Pyblosxom releases.
    """
    # FIXME - we should either ditch this function and use os.walk or
    # something similar, or optimize this version by removing the
    # multiple stat calls that happen as a result of islink, isdir and
    # isfile.

    # initialize
    result = []

    try:
        names = os.listdir(root)
    except OSError:
        return []

    # check each file
    for name in names:
        fullname = os.path.normpath(os.path.join(root, name))

        # grab if it matches our pattern and entry type
        if pattern.match(name):
            if ((os.path.isfile(fullname) and not return_folders) or
                (return_folders and os.path.isdir(fullname) and
                 (not ignorere or not ignorere.match(fullname)))):
                result.append(fullname)

        # recursively scan other folders, appending results
        if (recurse == 0) or (recurse > 1):
            if name[0] != "." and os.path.isdir(fullname) and \
                    not os.path.islink(fullname) and \
                    (not ignorere or not ignorere.match(fullname)):
                result = result + \
                         _walk_internal(fullname,
                                        (recurse > 1 and [recurse - 1] or [0])[0],
                                        pattern, ignorere, return_folders)

    return result


def filestat(request, filename):
    """
    Returns the filestat on a given file.  We store the filestat in
    case we've already retrieved it during this Pyblosxom request.

    This returns the mtime of the file (same as returned by
    ``time.localtime()``) -- tuple of 9 ints.

    :param request: the Request object
    :param filename: the file name of the file to stat

    :returns: the filestat (tuple of 9 ints) on the given file
    """
    data = request.getData()
    filestat_cache = data.setdefault("filestat_cache", {})

    if filestat_cache.has_key(filename):
        return filestat_cache[filename]

    argdict = {"request": request,
               "filename": filename,
               "mtime": (0,) * 10}

    MT = stat.ST_MTIME

    argdict = run_callback("filestat",
                           argdict,
                           mappingfunc=lambda x, y: y,
                           donefunc=lambda x: x and x["mtime"][MT] != 0,
                           defaultfunc=lambda x: x)

    # no plugin handled cb_filestat; we default to asking the
    # filesystem
    if argdict["mtime"][MT] == 0:
        argdict["mtime"] = os.stat(filename)

    timetuple = time.localtime(argdict["mtime"][MT])
    filestat_cache[filename] = timetuple

    return timetuple


def what_ext(extensions, filepath):
    """
    Takes in a filepath and a list of extensions and tries them all
    until it finds the first extension that works.

    :param extensions: the list of extensions to test
    :param filepath: the complete file path (minus the extension) to
                     test and find the extension for

    :returns: the extension (string) of the file or ``None``.
    """
    for ext in extensions:
        if os.path.isfile(filepath + '.' + ext):
            return ext
    return None


def is_year(s):
    """
    Checks to see if the string is likely to be a year or not.  In
    order to be considered to be a year, it must pass the following
    criteria:

    1. four digits
    2. first two digits are either 19 or 20.

    :param s: the string to check for "year-hood"

    :returns: ``True`` if it is a year and ``False`` otherwise.
    """
    if not s:
        return False

    if len(s) == 4 and s.isdigit() and \
            (s.startswith("19") or s.startswith("20")):
        return True
    return False


def importname(module_name, name):
    """
    Safely imports modules for runtime importing.

    :param module_name: the package name of the module to import from
    :param name: the name of the module to import

    :returns: the module object or ``None`` if there were problems
              importing.
    """
    logger = getLogger()
    if not module_name:
        m = name
    else:
        m = "%s.%s" % (module_name, name)

    try:
        module = __import__(m)
        for c in m.split(".")[1:]:
            module = getattr(module, c)
        return module

    except ImportError, ie:
        logger.error("Module %s in package %s won't import: %s" % \
                     (repr(module_name), repr(name), ie))

    except StandardError, e:
        logger.error("Module %s not in in package %s: %s" % \
                     (repr(module_name), repr(name), e))

    return None


def generate_rand_str(minlen=5, maxlen=10):
    """
    Generate a random string between ``minlen`` and ``maxlen``
    characters long.

    The generated string consists of letters and numbers.

    :param minlen: the minimum length of the generated random string
    :param maxlen: the maximum length of the generated random string

    :returns: generated string
    """
    import random, string
    chars = string.letters + string.digits
    randstr = []
    randstr_size = random.randint(minlen, maxlen)
    x = 0
    while x < randstr_size:
        randstr.append(random.choice(chars))
        x += 1
    return "".join(randstr)

generateRandStr = deprecated_function(generate_rand_str)


def run_callback(chain, input,
                 mappingfunc=lambda x, y: x,
                 donefunc=lambda x: 0,
                 defaultfunc=None):
    """
    Executes a callback chain on a given piece of data.  passed in is
    a dict of name/value pairs.  Consult the documentation for the
    specific callback chain you're executing.

    Callback chains should conform to their documented behavior.  This
    function allows us to do transforms on data, handling data, and
    also callbacks.

    The difference in behavior is affected by the mappingfunc passed
    in which converts the output of a given function in the chain to
    the input for the next function.

    If this is confusing, read through the code for this function.

    Returns the transformed input dict.

    :param chain: the name of the callback chain to run

    :param input: dict with name/value pairs that gets passed as the
                  args dict to all callback functions

    :param mappingfunc: the function that maps output arguments to
                        input arguments for the next iteration.  It
                        must take two arguments: the original dict and
                        the return from the previous function.  It
                        defaults to returning the original dict.

    :param donefunc: this function tests whether we're done doing what
                     we're doing.  This function takes as input the
                     output of the most recent iteration.  If this
                     function returns True then we'll drop out of the
                     loop.  For example, if you wanted a callback to
                     stop running when one of the registered functions
                     returned a 1, then you would pass in:
                     ``donefunc=lambda x: x`` .

    :param defaultfunc: if this is set and we finish going through all
                        the functions in the chain and none of them
                        have returned something that satisfies the
                        donefunc, then we'll execute the defaultfunc
                        with the latest version of the input dict.

    :returns: varies
    """
    chain = plugin_utils.get_callback_chain(chain)

    output = None

    for func in chain:
        # we call the function with the input dict it returns an
        # output.
        output = func(input)

        # we fun the output through our donefunc to see if we should
        # stop iterating through the loop.  if the donefunc returns
        # something true, then we're all done; otherwise we continue.
        if donefunc(output):
            break

        # we pass the input we just used and the output we just got
        # into the mappingfunc which will give us the input for the
        # next iteration.  in most cases, this consists of either
        # returning the old input or the old output--depending on
        # whether we're transforming the data through the chain or
        # not.
        input = mappingfunc(input, output)

    # if we have a defaultfunc and we haven't satisfied the donefunc
    # conditions, then we return whatever the defaultfunc returns when
    # given the current version of the input.
    if callable(defaultfunc) and not donefunc(output):
        return defaultfunc(input)

    # we didn't call the defaultfunc--so we return the most recent
    # output.
    return output


def addcr(text):
    """Adds a cr if it needs one.

    >>> addcr("foo")
    'foo\\n'
    >>> addcr("foo\\n")
    'foo\\n'

    :returns: string with \\n at the end
    """
    if not text.endswith("\n"):
        return text + "\n"
    return text


def create_entry(datadir, category, filename, mtime, title, metadata, body):
    """
    Creates a new entry in the blog.

    This is primarily used by the testing system, but it could be used
    by scripts and other tools.

    :param datadir: the datadir
    :param category: the category the entry should go in
    :param filename: the name of the blog entry (filename and
                     extension--no directory)
    :param mtime: the mtime (float) for the entry in seconds since the
                  epoch
    :param title: the title for the entry
    :param metadata: dict of key/value metadata pairs
    :param body: the body of the entry

    :raises IOError: if the datadir + category directory exists, but
                     isn't a directory
    """

    # format the metadata lines for the entry
    metadatalines = ["#%s %s" % (key, metadata[key])
                     for key in metadata.keys()]

    entry = addcr(title) + "\n".join(metadatalines) + body

    # create the category directories
    d = os.path.join(datadir, category)
    if not os.path.exists(d):
        os.makedirs(d)

    if not os.path.isdir(d):
        raise IOError("%s exists, but isn't a directory." % d)

    # create the filename
    fn = os.path.join(datadir, category, filename)

    # write the entry to disk
    f = open(fn, "w")
    f.write(entry)
    f.close()

    # set the mtime on the entry
    os.utime(fn, (mtime, mtime))


def get_cache(request):
    """
    Retrieves the cache from the request or fetches a new CacheDriver
    instance.

    :param request: the Request object

    :returns: a BlosxomCache object
    """
    data = request.getData()
    mycache = data.get("data_cache", "")

    if not mycache:
        config = request.getConfiguration()

        cache_driver_config = config.get('cacheDriver', 'base')
        cache_config = config.get('cacheConfig', '')

        cache_driver = importname('Pyblosxom.cache', cache_driver_config)
        mycache = cache_driver.BlosxomCache(request, cache_config)

        data["data_cache"] = mycache

    return mycache


def update_static_entry(cdict, entry_filename):
    """
    This is a utility function that allows plugins to easily update
    statically rendered entries without going through all the
    rigmarole.

    First we figure out whether this blog is set up for static
    rendering.  If not, then we return--no harm done.

    If we are, then we call ``render_url`` for each ``static_flavour``
    of the entry and then for each ``static_flavour`` of the index
    page.

    :param cdict: the config.py dict
    :param entry_filename: the url path of the entry to be updated;
                           example: ``/movies/xmen2``
    """
    static_dir = cdict.get("static_dir", "")

    if not static_dir:
        return

    static_flavours = cdict.get("static_flavours", ["html"])

    render_me = []
    for mem in static_flavours:
        render_me.append("/index" + "." + mem, "")
        render_me.append(entry_filename + "." + mem, "")

    for mem in render_me:
        render_url_statically(cdict, mem[0], mem[1])


def render_url_statically(cdict, url, querystring):
    """Renders a url and saves the rendered output to the
    filesystem.

    :param cdict: config dict
    :param url: url to render
    :param querystring: querystring of the url to render or ""
    """
    static_dir = cdict.get("static_dir", "")

    # if there is no static_dir, then they're not set up for static
    # rendering.
    if not static_dir:
        raise Exception("You must set static_dir in your config file.")

    response = render_url(cdict, url, querystring)
    response.seek(0)

    fn = os.path.normpath(static_dir + os.sep + url)
    if not os.path.isdir(os.path.dirname(fn)):
        os.makedirs(os.path.dirname(fn))

    # by using the response object the cheesy part of removing the
    # HTTP headers from the file is history.
    f = open(fn, "w")
    f.write(response.read())
    f.close()


def render_url(cdict, pathinfo, querystring=""):
    """
    Takes a url and a querystring and renders the page that
    corresponds with that by creating a Request and a Pyblosxom object
    and passing it through.  It then returns the resulting Response.

    :param cdict: the config.py dict
    :param pathinfo: the ``PATH_INFO`` string;
                     example: ``/dev/pyblosxom/firstpost.html``
    :param querystring: the querystring (if any); example: debug=yes

    :returns: a Pyblosxom ``Response`` object.
    """
    from pyblosxom import Pyblosxom

    if querystring:
        request_uri = pathinfo + "?" + querystring
    else:
        request_uri = pathinfo

    env = {
        "HTTP_HOST": "localhost",
        "HTTP_REFERER": "",
        "HTTP_USER_AGENT": "static renderer",
        "PATH_INFO": pathinfo,
        "QUERY_STRING": querystring,
        "REMOTE_ADDR": "",
        "REQUEST_METHOD": "GET",
        "REQUEST_URI": request_uri,
        "SCRIPT_NAME": "",
        "wsgi.errors": sys.stderr,
        "wsgi.input": None
    }
    data = {"STATIC": 1}
    p = Pyblosxom(cdict, env, data)
    p.run(static=True)
    return p.get_response()


#******************************
# Logging
#******************************

import logging

# A dict to keep track of created log handlers.  Used to prevent
# multiple handlers from being added to the same logger.
_loghandler_registry = {}


class LogFilter(object):
    """
    Filters out messages from log-channels that are not listed in the
    log_filter config variable.
    """
    def __init__(self, names=None):
        """
        Initializes the filter to the list provided by the names
        argument (or ``[]`` if ``names`` is ``None``).

        :param names: list of strings to filter out
        """
        if names == None:
            names = []
        self.names = names

    def filter(self, record):
        if record.name in self.names:
            return 1
        return 0


def get_logger(log_file=None):
    """Creates and returns a log channel.

    If no log_file is given the system-wide logfile as defined in
    config.py is used. If a log_file is given that's where the created
    logger logs to.

    :param log_file: the file to log to.  defaults to None which
                     causes Pyblosxom to check for the ``log_file``
                     config.py property and if that's blank, then the
                     log_file is stderr

    :returns: a log channel (logger instance) which you can call
              ``error``, ``warning``, ``debug``, ``info``, ... on.
    """
    custom_log_file = False
    if log_file is None:
        log_file = _config.get('log_file', 'stderr')
        f = sys._getframe(1)
        filename = f.f_code.co_filename
        module = f.f_globals["__name__"]
        # by default use the root logger
        log_name = ""
        for path in _config.get('plugin_dirs', []):
            if filename.startswith(path):
                # if it's a plugin, use the module name as the log
                # channels name
                log_name = module
                break
        # default to log level WARNING if it's not defined in
        # config.py
        log_level = _config.get('log_level', 'warning')
    else:
        # handle custom log_file
        custom_log_file = True
        # figure out a name for the log channel
        log_name = os.path.splitext(os.path.basename(log_file))[0]
        # assume log_level debug (show everything)
        log_level = "debug"

    global _loghandler_registry

    # get the logger for this channel
    logger = logging.getLogger(log_name)
    # don't propagate messages up the logger hierarchy
    logger.propagate = 0

    # setup the handler if it doesn't already exist.  only add one
    # handler per log channel.
    key = "%s|%s" % (log_file, log_name)
    if not key in _loghandler_registry:

        # create the handler
        if log_file == "stderr":
            hdlr = logging.StreamHandler(sys.stderr)
        else:
            if log_file == "NONE": # user disabled logging
                if os.name == 'nt': # windoze
                    log_file = "NUL"
                else: # assume *nix
                    log_file = "/dev/null"
            try:
                hdlr = logging.FileHandler(log_file)
            except IOError:
                # couldn't open logfile, fallback to stderr
                hdlr = logging.StreamHandler(sys.stderr)

        # create and set the formatter
        if log_name:
            fmtr_s = '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
        else: # root logger
            fmtr_s = '%(asctime)s [%(levelname)s]: %(message)s'

        hdlr.setFormatter(logging.Formatter(fmtr_s))

        logger.addHandler(hdlr)
        int_level = getattr(logging, log_level.upper())
        logger.setLevel(int_level)

        if not custom_log_file:
            # only log messages from plugins listed in log_filter.
            # add 'root' to the log_filter list to still allow
            # application level messages.
            log_filter = _config.get('log_filter', None)
            if log_filter:
                lfilter = LogFilter(log_filter)
                logger.addFilter(lfilter)

        # remember that we've seen this handler
        _loghandler_registry[key] = True

    return logger

getLogger = deprecated_function(get_logger)


def log_exception(log_file=None):
    """
    Logs an exception to the given file.  Uses the system-wide
    log_file as defined in config.py if none is given here.

    :param log_file: the file to log to.  defaults to None which
                     causes Pyblosxom to check for the ``log_file``
                     config.py property and if that's blank, then the
                     log_file is stderr
    """
    log = getLogger(log_file)
    log.exception("Exception occured:")


def log_caller(frame_num=1, log_file=None):
    """
    Logs some info about the calling function/method.  Useful for
    debugging.

    Usage:

    >>> import tools
    >>> tools.log_caller()     # logs frame 1
    >>> tools.log_caller(2)
    >>> tools.log_caller(3, log_file="/path/to/file")

    :param frame_num: the index of the frame to log; defaults to 1

    :param log_file: the file to log to.  defaults to None which
                     causes Pyblosxom to check for the ``log_file``
                     config.py property and if that's blank, then the
                     log_file is stderr
    """
    f = sys._getframe(frame_num)
    module = f.f_globals["__name__"]
    filename = f.f_code.co_filename
    line = f.f_lineno
    subr = f.f_code.co_name

    log = getLogger(log_file)
    log.info("\n  module: %s\n  filename: %s\n  line: %s\n  subroutine: %s",
             module, filename, line, subr)

########NEW FILE########
__FILENAME__ = _version
#######################################################################
# This file is part of Pyblosxom.
#
# Copyright (C) 2003-2011 by the Pyblosxom team.  See AUTHORS.
#
# Pyblosxom is distributed under the MIT license.  See the file
# LICENSE for distribution details.
#######################################################################

# valid version formats:
# * x.y      - final release
# * x.ya1    - alpha 1
# * x.yb1    - beta 1
# * x.yrc1   - release candidate 1
# * x.y.dev  - dev

# see http://www.python.org/dev/peps/pep-0386/

__version__ = "1.5.4.dev"


########NEW FILE########
