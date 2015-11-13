__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# Motor documentation build configuration file
#
# This file is execfile()d with the current directory set to its containing dir.

import sys, os
sys.path[0:0] = [os.path.abspath('..')]

import motor

# -- General configuration -----------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.doctest', 'sphinx.ext.coverage',
              'sphinx.ext.todo', 'doc.mongo_extensions', 'doc.motor_extensions',
              'sphinx.ext.intersphinx']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'Motor'
copyright = u'2014 MongoDB, Inc.'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = motor.version
# The full version, including alpha/beta/rc tags.
release = motor.version

# List of documents that shouldn't be included in the build.
unused_docs = []

# List of directories, relative to source directory, that shouldn't be searched
# for source files.
exclude_trees = ['_build']

# The reST default role (used for this markup: `text`) to use for all documents.
#default_role = None

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
#show_authors = False

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
add_module_names = True

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# A list of ignored prefixes for module index sorting.
#modindex_common_prefix = []

# -- Options for extensions ----------------------------------------------------
autoclass_content = 'init'

doctest_path = os.path.abspath('..')

# Don't test examples pulled from PyMongo's docstrings just because they start
# with '>>>'
doctest_test_doctest_blocks = False

doctest_global_setup = """
import sys
from datetime import timedelta

from tornado import gen
from tornado.ioloop import IOLoop

import pymongo
from pymongo.mongo_client import MongoClient
sync_client = MongoClient()
sync_client.drop_database("doctest_test")
db = sync_client.doctest_test

import motor
from motor import MotorClient
"""

# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  Major themes that come with
# Sphinx are currently 'default' and 'sphinxdoc'.
html_theme = 'default'
html_theme_options = {'collapsiblesidebar': True}

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
#html_static_path = ['_static']

# Custom sidebar templates, maps document names to template names.
#html_sidebars = {}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# If nonempty, this is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = ''

# Output file base name for HTML help builder.
htmlhelp_basename = 'Motor' + release.replace('.', '_')


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'Motor.tex', u'Motor Documentation',
   u'A. Jesse Jiryu Davis', 'manual'),
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

autodoc_default_flags = ['inherited-members']
autodoc_member_order = 'groupwise'

intersphinx_mapping = {
    'bson': ('http://api.mongodb.org/python/current/', None),
    'gridfs': ('http://api.mongodb.org/python/current/', None),
    'pymongo': ('http://api.mongodb.org/python/current/', None),
    'tornado': ('http://www.tornadoweb.org/en/stable/', None),
}

########NEW FILE########
__FILENAME__ = mongo_extensions
# Copyright 2009-2014 MongoDB, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""MongoDB specific extensions to Sphinx."""

from docutils import nodes
from sphinx import addnodes
from sphinx.util.compat import (Directive,
                                make_admonition)


class mongodoc(nodes.Admonition, nodes.Element):
    pass


class mongoref(nodes.reference):
    pass


def visit_mongodoc_node(self, node):
    self.visit_admonition(node, "seealso")


def depart_mongodoc_node(self, node):
    self.depart_admonition(node)


def visit_mongoref_node(self, node):
    atts = {"class": "reference external",
            "href": node["refuri"],
            "name": node["name"]}
    self.body.append(self.starttag(node, 'a', '', **atts))


def depart_mongoref_node(self, node):
    self.body.append('</a>')
    if not isinstance(node.parent, nodes.TextElement):
        self.body.append('\n')


class MongodocDirective(Directive):

    has_content = True
    required_arguments = 0
    optional_arguments = 0
    final_argument_whitespace = False
    option_spec = {}

    def run(self):
        return make_admonition(mongodoc, self.name,
                               ['See general MongoDB documentation'],
                               self.options, self.content, self.lineno,
                               self.content_offset, self.block_text,
                               self.state, self.state_machine)


def process_mongodoc_nodes(app, doctree, fromdocname):
    for node in doctree.traverse(mongodoc):
        anchor = None
        for name in node.parent.parent.traverse(addnodes.desc_signature):
            anchor = name["ids"][0]
            break
        if not anchor:
            for name in node.parent.traverse(nodes.section):
                anchor = name["ids"][0]
                break
        for para in node.traverse(nodes.paragraph):
            tag = str(para.traverse()[1])
            link = mongoref("", "")
            link["refuri"] = "http://dochub.mongodb.org/core/%s" % tag
            link["name"] = anchor
            link.append(nodes.emphasis(tag, tag))
            new_para = nodes.paragraph()
            new_para += link
            node.replace(para, new_para)


def setup(app):
    app.add_node(mongodoc,
                 html=(visit_mongodoc_node, depart_mongodoc_node),
                 latex=(visit_mongodoc_node, depart_mongodoc_node),
                 text=(visit_mongodoc_node, depart_mongodoc_node))
    app.add_node(mongoref,
                 html=(visit_mongoref_node, depart_mongoref_node))

    app.add_directive("mongodoc", MongodocDirective)

    app.connect("doctree-resolved", process_mongodoc_nodes)

########NEW FILE########
__FILENAME__ = motor_extensions
# Copyright 2012-2014 MongoDB, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Motor specific extensions to Sphinx."""

import inspect

from docutils.nodes import field, list_item, paragraph, title_reference
from docutils.nodes import field_list, field_body, bullet_list, Text, field_name
from sphinx.addnodes import (desc, desc_content, versionmodified,
                             desc_signature, seealso)
from sphinx.util.inspect import safe_getattr

import motor


# This is a place to store info while parsing, to be used before generating.
motor_info = {}


def find_by_path(root, classes):
    if not classes:
        return [root]

    _class = classes[0]
    rv = []
    for child in root.children:
        if isinstance(child, _class):
            rv.extend(find_by_path(child, classes[1:]))

    return rv


def get_parameter_names(parameters_node):
    parameter_names = []
    for list_item_node in find_by_path(parameters_node, [list_item]):
        title_ref_nodes = find_by_path(
            list_item_node, [paragraph, title_reference])

        parameter_names.append(title_ref_nodes[0].astext())

    return parameter_names


def insert_callback(parameters_node):
    # We need to know what params are here already
    parameter_names = get_parameter_names(parameters_node)

    if 'callback' not in parameter_names:
        if '*args' in parameter_names:
            args_pos = parameter_names.index('*args')
        else:
            args_pos = len(parameter_names)

        if '**kwargs' in parameter_names:
            kwargs_pos = parameter_names.index('**kwargs')
        else:
            kwargs_pos = len(parameter_names)

        doc = (
            " (optional): function taking (result, error), executed when"
            " operation completes")

        new_item = list_item(
            '', paragraph(
                '', '',
                title_reference('', 'callback'),
                Text(doc)))

        # Insert "callback" before *args and **kwargs
        parameters_node.insert(min(args_pos, kwargs_pos), new_item)


def process_motor_nodes(app, doctree):
    # Search doctree for Motor's methods and attributes whose docstrings were
    # copied from PyMongo, and fix them up for Motor:
    #   1. Add a 'callback' param (sometimes optional, sometimes required) to
    #      all async methods. If the PyMongo method took no params, we create
    #      a parameter-list from scratch, otherwise we edit PyMongo's list.
    #   2. Remove all version annotations like "New in version 2.0" since
    #      PyMongo's version numbers are meaningless in Motor's docs.
    #   3. Remove "seealso" directives that reference PyMongo's docs.
    #
    # We do this here, rather than by registering a callback to Sphinx's
    # 'autodoc-process-signature' event, because it's way easier to handle the
    # parsed doctree before it's turned into HTML than it is to update the RST.
    for objnode in doctree.traverse(desc):
        if objnode['objtype'] in ('method', 'attribute'):
            signature_node = find_by_path(objnode, [desc_signature])[0]
            name = '.'.join([
                signature_node['module'], signature_node['fullname']])

            assert name.startswith('motor.')
            obj_motor_info = motor_info.get(name)
            if obj_motor_info:
                desc_content_node = find_by_path(objnode, [desc_content])[0]
                if obj_motor_info.get('is_async_method'):
                    try:
                        # Find the parameter list, a bullet_list instance
                        parameters_node = find_by_path(
                            desc_content_node,
                            [field_list, field, field_body, bullet_list])[0]
                    except IndexError:
                        # PyMongo method has no parameters, create an empty
                        # params list
                        parameters_node = bullet_list()
                        parameters_field_list_node = field_list(
                            '',
                            field(
                                '',
                                field_name('', 'Parameters '),
                                field_body('', parameters_node)))

                        desc_content_node.append(parameters_field_list_node)

                    insert_callback(parameters_node)

                    callback_future_text = (
                        "If a callback is passed, returns None, else returns a"
                        " Future.")

                    desc_content_node.append(
                        paragraph('', Text(callback_future_text)))

                if obj_motor_info['is_pymongo_docstring']:
                    # Remove all "versionadded", "versionchanged" and
                    # "deprecated" directives from the docs we imported from
                    # PyMongo
                    version_nodes = find_by_path(
                        desc_content_node, [versionmodified])

                    for version_node in version_nodes:
                        version_node.parent.remove(version_node)

                    # Remove all "seealso" directives that contain :doc:
                    # references from PyMongo's docs
                    seealso_nodes = find_by_path(desc_content_node, [seealso])

                    for seealso_node in seealso_nodes:
                        if 'reftype="doc"' in str(seealso_node):
                            seealso_node.parent.remove(seealso_node)


def get_motor_attr(motor_class, name, *defargs):
    """If any Motor attributes can't be accessed, grab the equivalent PyMongo
    attribute. While we're at it, store some info about each attribute
    in the global motor_info dict.
    """
    attr = safe_getattr(motor_class, name)
    method_class = safe_getattr(attr, 'im_class', None)
    from_pymongo = not safe_getattr(
        method_class, '__module__', '').startswith('motor')

    # Store some info for process_motor_nodes()
    full_name = '%s.%s.%s' % (
        motor_class.__module__, motor_class.__name__, name)

    is_async_method = getattr(attr, 'is_async_method', False)
    is_cursor_method = getattr(attr, 'is_motorcursor_chaining_method', False)
    if is_async_method or is_cursor_method:
        pymongo_method = getattr(
            motor_class.__delegate_class__, attr.pymongo_method_name)
    else:
        pymongo_method = None

    is_pymongo_docstring = from_pymongo or is_async_method or is_cursor_method

    motor_info[full_name] = {
        # These sub-attributes are set in motor.asynchronize()
        'is_async_method': is_async_method,
        'is_pymongo_docstring': is_pymongo_docstring,
        'pymongo_method': pymongo_method,
    }

    return attr


def get_motor_argspec(pymongo_method, is_async_method):
    args, varargs, kwargs, defaults = inspect.getargspec(pymongo_method)

    # This part is copied from Sphinx's autodoc.py
    if args and args[0] in ('cls', 'self'):
        del args[0]

    defaults = list(defaults) if defaults else []

    if is_async_method:
        # Add 'callback=None' argument
        args.append('callback')
        defaults.append(None)

    return args, varargs, kwargs, defaults


# Adapted from MethodDocumenter.format_args
def format_motor_args(pymongo_method, is_async_method):
    argspec = get_motor_argspec(pymongo_method, is_async_method)
    formatted_argspec = inspect.formatargspec(*argspec)
    # escape backslashes for reST
    return formatted_argspec.replace('\\', '\\\\')


def process_motor_signature(
        app, what, name, obj, options, signature, return_annotation):
    if name in motor_info and motor_info[name].get('pymongo_method'):
        # Real sig obscured by decorator, reconstruct it
        pymongo_method = motor_info[name]['pymongo_method']
        is_async_method = motor_info[name]['is_async_method']
        args = format_motor_args(pymongo_method, is_async_method)
        return args, return_annotation


def setup(app):
    app.add_autodoc_attrgetter(type(motor.MotorBase), get_motor_attr)
    app.connect('autodoc-process-signature', process_motor_signature)
    app.connect("doctree-read", process_motor_nodes)

########NEW FILE########
__FILENAME__ = motor_py3_compat
# Copyright 2014 MongoDB, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import unicode_literals, absolute_import

"""Python 2.6+ compatibility utilities for Motor."""

import sys

PY3 = False
if sys.version_info[0] >= 3:
    PY3 = True

if PY3:
    string_types = str,
    integer_types = int,
    text_type = str
    from io import BytesIO as StringIO
else:
    string_types = basestring,
    integer_types = (int, long)
    text_type = unicode

    try:
        from cStringIO import StringIO
    except ImportError:
        from StringIO import StringIO


def add_metaclass(metaclass):
    """Class decorator for creating a class with a metaclass.

    Copied from "six".
    """
    def wrapper(cls):
        orig_vars = cls.__dict__.copy()
        orig_vars.pop('__dict__', None)
        orig_vars.pop('__weakref__', None)
        slots = orig_vars.get('__slots__')
        if slots is not None:
            if isinstance(slots, str):
                slots = [slots]
            for slots_var in slots:
                orig_vars.pop(slots_var)
        return metaclass(cls.__name__, cls.__bases__, orig_vars)
    return wrapper

########NEW FILE########
__FILENAME__ = util
# Copyright 2013-2014 MongoDB, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import unicode_literals

"""A version of PyMongo's thread_util for Motor."""

import datetime

try:
    from time import monotonic as _time
except ImportError:
    from time import time as _time

import greenlet


class MotorGreenletEvent(object):
    """An Event-like class for greenlets."""
    def __init__(self, io_loop):
        self.io_loop = io_loop
        self._flag = False
        self._waiters = []
        self._timeouts = set()

    def is_set(self):
        return self._flag

    isSet = is_set

    def set(self):
        self._flag = True
        timeouts, self._timeouts = self._timeouts, set()
        for timeout in timeouts:
            self.io_loop.remove_timeout(timeout)

        waiters, self._waiters = self._waiters, []
        for waiter in waiters:
            # Defer execution.
            self.io_loop.add_callback(waiter.switch)

    def clear(self):
        self._flag = False

    def wait(self, timeout_seconds=None):
        current = greenlet.getcurrent()
        parent = current.parent
        assert parent is not None, "Should be on child greenlet"
        if not self._flag:
            self._waiters.append(current)

            def on_timeout():
                # Called from IOLoop on main greenlet.
                self._waiters.remove(current)
                self._timeouts.remove(timeout)
                current.switch()

            if timeout_seconds is not None:
                timeout = self.io_loop.add_timeout(
                    datetime.timedelta(seconds=timeout_seconds), on_timeout)

                self._timeouts.add(timeout)
            parent.switch()

########NEW FILE########
__FILENAME__ = web
# Copyright 2011-2014 MongoDB, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import unicode_literals

"""Utilities for using Motor with Tornado web applications."""

import datetime
import email.utils
import mimetypes
import time

import tornado.web
from tornado import gen

import gridfs
import motor


# TODO: this class is not a drop-in replacement for StaticFileHandler.
#   StaticFileHandler provides class method make_static_url, which appends
#   an MD5 of the static file's contents. Templates thus can do
#   {{ static_url('image.png') }} and get "/static/image.png?v=1234abcdef",
#   which is cached forever. Problem is, it calculates the MD5 synchronously.
#   Two options: keep a synchronous GridFS available to get each grid file's
#   MD5 synchronously for every static_url call, or find some other idiom.


class GridFSHandler(tornado.web.RequestHandler):
    """A handler that can serve content from `GridFS`_, very similar to
    :class:`tornado.web.StaticFileHandler`.

    .. code-block:: python

        db = motor.MotorClient().my_database
        application = web.Application([
            (r"/static/(.*)", web.GridFSHandler, {"database": db}),
        ])

    By default, requests' If-Modified-Since headers are honored, but no
    specific cache-control timeout is sent to clients. Thus each request for
    a GridFS file requires a quick check of the file's ``uploadDate`` in
    MongoDB. Override :meth:`get_cache_time` in a subclass to customize this.
    """
    def initialize(self, database, root_collection='fs'):
        self.database = database
        self.root_collection = root_collection

    def get_gridfs_file(self, fs, path):
        """Overridable method to choose a GridFS file to serve at a URL.

        By default, if a URL pattern like ``"/static/(.*)"`` is mapped to this
        ``GridFSHandler``, then the trailing portion of the URL is used as the
        filename, so a request for "/static/image.png" results in a call
        to :meth:`MotorGridFS.get` with "image.png" as the ``filename``
        argument. To customize the mapping of path to GridFS file, override
        ``get_gridfs_file`` and return a Future :class:`~motor.MotorGridOut`
        from it.

        For example, to retrieve the file by ``_id`` instead of filename::

            class CustomGridFSHandler(motor.web.GridFSHandler):
                def get_gridfs_file(self, fs, path):
                    # Path is interpreted as _id instead of name.
                    # Return a Future MotorGridOut.
                    return fs.get(file_id=ObjectId(path))

        :Parameters:
          - `fs`: An open :class:`~motor.MotorGridFS` object
          - `path`: A string, the trailing portion of the URL pattern being
            served

        .. versionchanged:: 0.2
           ``get_gridfs_file`` no longer accepts a callback, instead returns
           a Future.
        """
        return fs.get_last_version(path)  # A Future MotorGridOut

    @gen.coroutine
    def get(self, path, include_body=True):
        fs = motor.MotorGridFS(self.database, self.root_collection)

        try:
            gridout = yield self.get_gridfs_file(fs, path)
        except gridfs.NoFile:
            raise tornado.web.HTTPError(404)

        # If-Modified-Since header is only good to the second.
        modified = gridout.upload_date.replace(microsecond=0)
        self.set_header("Last-Modified", modified)

        # MD5 is calculated on the MongoDB server when GridFS file is created
        self.set_header("Etag", '"%s"' % gridout.md5)

        mime_type = gridout.content_type

        # If content type is not defined, try to check it with mimetypes
        if mime_type is None:
            mime_type, encoding = mimetypes.guess_type(path)

        # Starting from here, largely a copy of StaticFileHandler
        if mime_type:
            self.set_header("Content-Type", mime_type)

        cache_time = self.get_cache_time(path, modified, mime_type)

        if cache_time > 0:
            self.set_header("Expires", datetime.datetime.utcnow() +
                                       datetime.timedelta(seconds=cache_time))
            self.set_header("Cache-Control", "max-age=" + str(cache_time))
        else:
            self.set_header("Cache-Control", "public")

        self.set_extra_headers(path, gridout)

        # Check the If-Modified-Since, and don't send the result if the
        # content has not been modified
        ims_value = self.request.headers.get("If-Modified-Since")
        if ims_value is not None:
            date_tuple = email.utils.parsedate(ims_value)
            if_since = datetime.datetime.fromtimestamp(time.mktime(date_tuple))
            if if_since >= modified:
                self.set_status(304)
                return

        # Same for Etag
        etag = self.request.headers.get("If-None-Match")
        if etag is not None and etag.strip('"') == gridout.md5:
            self.set_status(304)
            return

        self.set_header("Content-Length", gridout.length)
        if include_body:
            yield gridout.stream_to_handler(self)

        # Needed until fix for Tornado bug 751 is released, see
        # https://github.com/facebook/tornado/issues/751 and
        # https://github.com/facebook/tornado/commit/5491685
        self.finish()

    def head(self, path):
        # get() is a coroutine. Return its Future.
        return self.get(path, include_body=False)

    def get_cache_time(self, path, modified, mime_type):
        """Override to customize cache control behavior.

        Return a positive number of seconds to trigger aggressive caching or 0
        to mark resource as cacheable, only. 0 is the default.
        """
        return 0

    def set_extra_headers(self, path, gridout):
        """For subclass to add extra headers to the response"""
        pass

########NEW FILE########
__FILENAME__ = synchrotest
# Copyright 2012-2014 MongoDB, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import unicode_literals

"""Test Motor by testing that Synchro, a fake PyMongo implementation built on
top of Motor, passes the same unittests as PyMongo.

This program monkey-patches sys.modules, so run it alone, rather than as part
of a larger test suite.
"""

import sys

import nose
from nose.config import Config
from nose.plugins import Plugin
from nose.plugins.manager import PluginManager
from nose.plugins.skip import Skip
from nose.plugins.xunit import Xunit
from nose.selector import Selector

import synchro
from motor.motor_py3_compat import PY3

excluded_modules = [
    # Depending on PYTHONPATH, Motor's direct tests may be imported - don't
    # run them now.
    'test.test_motor_',

    # Not worth simulating PyMongo's crazy deprecation semantics for safe and
    # slave_okay in Synchro.
    'test.test_common',

    # Exclude some PyMongo tests that can't be applied to Synchro.
    'test.test_threads',
    'test.test_threads_replica_set_client',
    'test.test_pooling',
    'test.test_pooling_gevent',
    'test.test_paired',
    'test.test_master_slave_connection',
    'test.test_legacy_connections',

    # Complex PyMongo-specific mocking.
    'test.test_replica_set_reconfig',
    'test.test_mongos_ha',
]

excluded_tests = [
    # Depends on requests.
    '*.test_copy_db',
    'TestCollection.test_insert_large_batch',

    # Motor always uses greenlets.
    '*.test_use_greenlets',

    # Motor's reprs aren't the same as PyMongo's.
    '*.test_repr',

    # Not worth simulating PyMongo's crazy deprecation semantics for safe and
    # slave_okay in Synchro.
    'TestClient.test_from_uri',
    'TestReplicaSetClient.test_properties',

    # MotorClient(uri).open() doesn't raise ConfigurationError if the URI has
    # the wrong auth credentials.
    'TestClient.test_auth_from_uri',

    # Motor's pool is different, we test it separately.
    '*.test_waitQueueMultiple',

    # Lazy-connection tests require multithreading; we test concurrent
    # lazy connection directly.
    '_TestLazyConnectMixin.*',
    'TestClientLazyConnect.*',
    'TestClientLazyConnectOneGoodSeed.*',
    'TestClientLazyConnectBadSeeds.*',
    'TestReplicaSetClientLazyConnect.*',
    'TestReplicaSetClientLazyConnectBadSeeds.*',

    # Motor doesn't do requests.
    '*.test_auto_start_request',
    '*.test_nested_request',
    '*.test_request_threads',
    '*.test_operation_failure_with_request',
    'TestClient.test_with_start_request',
    'TestDatabase.test_authenticate_and_request',
    'TestGridfs.test_request',
    'TestGridfs.test_gridfs_request',

    # We test this directly, because it requires monkey-patching either socket
    # or IOStream, depending on whether it's PyMongo or Motor.
    ('TestReplicaSetClient.'
     'test_auto_reconnect_exception_when_read_preference_is_secondary'),

    # No pinning in Motor since there are no requests.
    'TestReplicaSetClient.test_pinned_member',

    # Not allowed to call schedule_refresh directly in Motor.
    'TestReplicaSetClient.test_schedule_refresh',

    # We don't make the same guarantee as PyMongo when connecting an
    # RS client to a standalone.
    'TestReplicaSetClientAgainstStandalone.test_connect',

    # test_read_preference: requires patching MongoReplicaSetClient specially.
    'TestCommandAndReadPreference.*',

    # Motor doesn't support forking or threading.
    '*.test_interrupt_signal',
    '*.test_fork',
    'TestCollection.test_ensure_unique_index_threaded',
    'TestGridfs.test_threaded_writes',
    'TestGridfs.test_threaded_reads',

    # Relies on threads; tested directly.
    'TestCollection.test_parallel_scan',

    # Motor doesn't support PyMongo's syntax, db.system_js['my_func'] = "code",
    # users should just use system.js as a regular collection.
    'TestDatabase.test_system_js',
    'TestDatabase.test_system_js_list',

    # Motor can't raise an index error if a cursor slice is out of range; it
    # just gets no results.
    'TestCursor.test_getitem_index_out_of_range',

    # Weird use-case.
    'TestCursor.test_cursor_transfer',

    # No context-manager protocol for MotorCursor.
    'TestCursor.test_with_statement',

    # Can't iterate a GridOut in Motor.
    'TestGridfs.test_missing_length_iter',
    'TestGridFile.test_iterator',

    # Not worth simulating a user calling GridOutCursor(args).
    'TestGridFile.test_grid_out_cursor_options',

    # Don't need to check that GridFile is deprecated.
    'TestGridFile.test_grid_file',

    # No context-manager protocol for MotorGridIn, and can't set attrs.
    'TestGridFile.test_context_manager',
    'TestGridFile.test_grid_in_default_opts',
    'TestGridFile.test_set_after_close',

    # GridFS always connects lazily in Motor.
    'TestGridfs.test_gridfs_lazy_connect',

    # Testing a deprecated PyMongo API, Motor can skip it.
    'TestCollection.test_insert_message_creation',

    # Complex PyMongo-specific mocking.
    'TestMongoClientFailover.*',
    'TestReplicaSetClientInternalIPs.*',
    'TestReplicaSetClientMaxWriteBatchSize.*',
    'TestClient.test_wire_version_mongos_ha',
    'TestClient.test_max_wire_version',
    '*.test_wire_version',
]


class SynchroNosePlugin(Plugin):
    name = 'synchro'

    def __init__(self, *args, **kwargs):
        # We need a standard Nose selector in order to filter out methods that
        # don't match TestSuite.test_*
        self.selector = Selector(config=None)
        super(SynchroNosePlugin, self).__init__(*args, **kwargs)

    def configure(self, options, conf):
        super(SynchroNosePlugin, self).configure(options, conf)
        self.enabled = True

    def wantModule(self, module):
        for module_name in excluded_modules:
            if module.__name__.startswith(module_name):
                return False

        return True

    def wantMethod(self, method):
        # Run standard Nose checks on name, like "does it start with test_"?
        if not self.selector.matches(method.__name__):
            return False

        for excluded_name in excluded_tests:
            if PY3:
                classname = method.__self__.__class__.__name__
            else:
                classname = method.im_class.__name__

            # Should we exclude this method's whole TestCase?
            suite_name, method_name = excluded_name.split('.')
            suite_matches = (suite_name == classname or suite_name == '*')

            # Should we exclude this particular method?
            method_matches = (
                method.__name__ == method_name or method_name == '*')

            if suite_matches and method_matches:
                return False

        return True


# So that e.g. 'from pymongo.mongo_client import MongoClient' gets the
# Synchro MongoClient, not the real one. We include
# master_slave_connection, connection, etc. even though Motor doesn't support
# them and we exclude them from tests, so that the import doesn't fail.
pymongo_modules = set([
    'gridfs',
    'gridfs.errors',
    'gridfs.grid_file',
    'pymongo',
    'pymongo.auth',
    'pymongo.collection',
    'pymongo.common',
    'pymongo.connection',
    'pymongo.command_cursor',
    'pymongo.cursor',
    'pymongo.cursor_manager',
    'pymongo.database',
    'pymongo.helpers',
    'pymongo.errors',
    'pymongo.master_slave_connection',
    'pymongo.member',
    'pymongo.mongo_client',
    'pymongo.mongo_replica_set_client',
    'pymongo.pool',
    'pymongo.read_preferences',
    'pymongo.replica_set_connection',
    'pymongo.son_manipulator',
    'pymongo.ssl_match_hostname',
    'pymongo.thread_util',
    'pymongo.uri_parser',
])


class SynchroModuleFinder(object):
    def find_module(self, fullname, path=None):
        for module_name in pymongo_modules:
            if fullname.endswith(module_name):
                return SynchroModuleLoader(path)

        # Let regular module search continue.
        return None


class SynchroModuleLoader(object):
    def __init__(self, path):
        self.path = path

    def load_module(self, fullname):
        return synchro


if __name__ == '__main__':
    # Monkey-patch all pymongo's unittests so they think Synchro is the
    # real PyMongo.
    sys.meta_path[0:0] = [SynchroModuleFinder()]

    # Ensure time.sleep() acts as PyMongo's tests expect: background tasks
    # can run to completion while foreground pauses.
    sys.modules['time'] = synchro.TimeModule()

    nose.main(
        config=Config(plugins=PluginManager()),
        addplugins=[SynchroNosePlugin(), Skip(), Xunit()])

########NEW FILE########
__FILENAME__ = ha_tools
# Copyright 2009-2014 MongoDB, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import print_function, unicode_literals

# TODO: this is simply copied from PyMongo, for now - remove it once we've
#   standardized on something for all driver tests

"""Tools for testing high availability in PyMongo."""

import os
import random
import shutil
import signal
import socket
import subprocess
import sys
import time

from stat import S_IRUSR

import pymongo
import pymongo.errors
from pymongo.read_preferences import ReadPreference

home = os.environ.get('HOME')
default_dbpath = os.path.join(home, 'data', 'pymongo_high_availability')
dbpath = os.environ.get('DBPATH', default_dbpath)
default_logpath = os.path.join(home, 'log', 'pymongo_high_availability')
logpath = os.environ.get('LOGPATH', default_logpath)
hostname = os.environ.get('HOSTNAME', socket.gethostname())
port = int(os.environ.get('DBPORT', 27017))
mongod = os.environ.get('MONGOD', 'mongod')
mongos = os.environ.get('MONGOS', 'mongos')
set_name = os.environ.get('SETNAME', 'repl0')
use_greenlets = bool(os.environ.get('GREENLETS'))
ha_tools_debug = bool(os.environ.get('HA_TOOLS_DEBUG'))


nodes = {}
routers = {}
cur_port = port
key_file = None


def kill_members(members, sig, hosts=nodes):
    for member in sorted(members):
        try:
            if ha_tools_debug:
                print('killing', member)
            proc = hosts[member]['proc']
            # Not sure if cygwin makes sense here...
            if sys.platform in ('win32', 'cygwin'):
                os.kill(proc.pid, signal.CTRL_C_EVENT)
            else:
                os.kill(proc.pid, sig)
        except OSError:
            if ha_tools_debug:
                print(member, 'already dead?')


def kill_all_members():
    kill_members(nodes.keys(), 2, nodes)
    kill_members(routers.keys(), 2, routers)


def wait_for(proc, port_num):
    trys = 0
    while proc.poll() is None and trys < 160:
        trys += 1
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            try:
                s.connect((hostname, port_num))
                return True
            except (IOError, socket.error):
                time.sleep(0.25)
        finally:
            s.close()

    kill_all_members()
    return False


def start_replica_set(members, auth=False, fresh=True):
    global cur_port, key_file

    if fresh:
        if os.path.exists(dbpath):
            try:
                shutil.rmtree(dbpath)
            except OSError:
                pass

        try:
            os.makedirs(dbpath)
        except OSError as e:
            print(e)
            print("\tWhile creating", dbpath)

    if auth:
        key_file = os.path.join(dbpath, 'key.txt')
        if not os.path.exists(key_file):
            f = open(key_file, 'w')
            try:
                f.write("my super secret system password")
            finally:
                f.close()
            os.chmod(key_file, S_IRUSR)

    for i in range(len(members)):
        host = '%s:%d' % (hostname, cur_port)
        members[i].update({'_id': i, 'host': host})
        path = os.path.join(dbpath, 'db' + str(i))
        if not os.path.exists(path):
            os.makedirs(path)
        member_logpath = os.path.join(logpath, 'db' + str(i) + '.log')
        if not os.path.exists(os.path.dirname(member_logpath)):
            os.makedirs(os.path.dirname(member_logpath))
        cmd = [mongod,
               '--dbpath', path,
               '--port', str(cur_port),
               '--replSet', set_name,
               '--nojournal', '--oplogSize', '64',
               '--logappend', '--logpath', member_logpath]
        if auth:
            cmd += ['--keyFile', key_file]

        if ha_tools_debug:
            print('starting', ' '.join(cmd))

        proc = subprocess.Popen(cmd,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT)
        nodes[host] = {'proc': proc, 'cmd': cmd}
        res = wait_for(proc, cur_port)

        cur_port += 1

        if not res:
            return None

    config = {'_id': set_name, 'members': members}
    primary = members[0]['host']
    c = pymongo.MongoClient(primary, use_greenlets=use_greenlets)
    try:
        if ha_tools_debug:
            print('rs.initiate(%s)' % config)

        c.admin.command('replSetInitiate', config)
    except pymongo.errors.OperationFailure as e:
        # Already initialized from a previous run?
        if ha_tools_debug:
            print(e)

    expected_arbiters = 0
    for member in members:
        if member.get('arbiterOnly'):
            expected_arbiters += 1
    expected_secondaries = len(members) - expected_arbiters - 1

    # Wait for 8 minutes for replica set to come up
    patience = 8
    for i in range(int(patience * 60 / 2)):
        time.sleep(2)
        try:
            if (get_primary() and
                    len(get_secondaries()) == expected_secondaries and
                    len(get_arbiters()) == expected_arbiters):
                break
        except pymongo.errors.ConnectionFailure:
            # Keep waiting
            pass

        if ha_tools_debug:
            print('waiting for RS', i)
    else:
        kill_all_members()
        raise Exception(
            "Replica set still not initalized after %s minutes" % patience)
    return primary, set_name


def create_sharded_cluster(num_routers=3):
    global cur_port

    # Start a config server
    configdb_host = '%s:%d' % (hostname, cur_port)
    path = os.path.join(dbpath, 'configdb')
    if not os.path.exists(path):
        os.makedirs(path)
    configdb_logpath = os.path.join(logpath, 'configdb.log')
    cmd = [mongod,
           '--dbpath', path,
           '--port', str(cur_port),
           '--nojournal', '--logappend',
           '--logpath', configdb_logpath]
    proc = subprocess.Popen(cmd,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT)
    nodes[configdb_host] = {'proc': proc, 'cmd': cmd}
    res = wait_for(proc, cur_port)
    if not res:
        return None

    # ...and a shard server
    cur_port += 1
    shard_host = '%s:%d' % (hostname, cur_port)
    path = os.path.join(dbpath, 'shard1')
    if not os.path.exists(path):
        os.makedirs(path)
    db_logpath = os.path.join(logpath, 'shard1.log')
    cmd = [mongod,
           '--dbpath', path,
           '--port', str(cur_port),
           '--nojournal', '--logappend',
           '--logpath', db_logpath]
    proc = subprocess.Popen(cmd,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT)
    nodes[shard_host] = {'proc': proc, 'cmd': cmd}
    res = wait_for(proc, cur_port)
    if not res:
        return None

    # ...and a few mongos instances
    cur_port += 1
    for i in range(num_routers):
        cur_port += 1
        host = '%s:%d' % (hostname, cur_port)
        mongos_logpath = os.path.join(logpath, 'mongos' + str(i) + '.log')
        cmd = [mongos,
               '--port', str(cur_port),
               '--logappend',
               '--logpath', mongos_logpath,
               '--configdb', configdb_host]
        proc = subprocess.Popen(cmd,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT)
        routers[host] = {'proc': proc, 'cmd': cmd}
        res = wait_for(proc, cur_port)
        if not res:
            return None

    # Add the shard
    client = pymongo.MongoClient('%s:%d' % (hostname, cur_port))
    try:
        client.admin.command({'addshard': shard_host})
    except pymongo.errors.OperationFailure:
        # Already configured.
        pass

    return get_mongos_seed_list()


# Connect to a random member
def get_client():
    return pymongo.MongoClient(
        nodes.keys(),
        read_preference=ReadPreference.PRIMARY_PREFERRED,
        use_greenlets=use_greenlets)


def get_mongos_seed_list():
    members = routers.keys()
    return ','.join(members)


def kill_mongos(host):
    kill_members([host], 2, hosts=routers)
    return host


def restart_mongos(host):
    restart_members([host], True)


def get_members_in_state(state):
    status = get_client().admin.command('replSetGetStatus')
    members = status['members']
    return [k['name'] for k in members if k['state'] == state]


def get_primary():
    try:
        primaries = get_members_in_state(1)
        assert len(primaries) <= 1
        if primaries:
            return primaries[0]
    except pymongo.errors.ConnectionFailure:
        pass

    return None


def get_random_secondary():
    secondaries = get_members_in_state(2)
    if len(secondaries):
        return random.choice(secondaries)
    return None


def get_secondaries():
    return get_members_in_state(2)


def get_arbiters():
    return get_members_in_state(7)


def get_recovering():
    return get_members_in_state(3)


def get_passives():
    return get_client().admin.command('ismaster').get('passives', [])


def get_hosts():
    return get_client().admin.command('ismaster').get('hosts', [])


def get_hidden_members():
    # Both 'hidden' and 'slaveDelay'
    secondaries = get_secondaries()
    readers = get_hosts() + get_passives()
    for member in readers:
        try:
            secondaries.remove(member)
        except KeyError:
            # Skip primary
            pass
    return secondaries


def get_tags(member):
    config = get_client().local.system.replset.find_one()
    for m in config['members']:
        if m['host'] == member:
            return m.get('tags', {})

    raise Exception('member %s not in config' % repr(member))


def kill_primary(sig=2):
    primary = get_primary()
    kill_members([primary], sig)
    return primary


def kill_secondary(sig=2):
    secondary = get_random_secondary()
    kill_members([secondary], sig)
    return secondary


def kill_all_secondaries(sig=2):
    secondaries = get_secondaries()
    kill_members(secondaries, sig)
    return secondaries


# TODO: refactor w/ start_replica_set
def add_member(auth=False):
    global cur_port
    host = '%s:%d' % (hostname, cur_port)
    primary = get_primary()
    c = pymongo.MongoClient(primary, use_greenlets=use_greenlets)
    config = c.local.system.replset.find_one()
    _id = max([member['_id'] for member in config['members']]) + 1
    member = {'_id': _id, 'host': host}
    path = os.path.join(dbpath, 'db' + str(_id))
    if os.path.exists(path):
        shutil.rmtree(path)

    os.makedirs(path)
    member_logpath = os.path.join(logpath, 'db' + str(_id) + '.log')
    if not os.path.exists(os.path.dirname(member_logpath)):
        os.makedirs(os.path.dirname(member_logpath))
    cmd = [mongod,
           '--dbpath', path,
           '--port', str(cur_port),
           '--replSet', set_name,
           '--nojournal', '--oplogSize', '64',
           '--logappend', '--logpath', member_logpath]
    if auth:
        cmd += ['--keyFile', key_file]

    if ha_tools_debug:
        print('starting', ' '.join(cmd))

    proc = subprocess.Popen(cmd,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT)
    nodes[host] = {'proc': proc, 'cmd': cmd}
    res = wait_for(proc, cur_port)

    cur_port += 1

    config['members'].append(member)
    config['version'] += 1

    if ha_tools_debug:
        print({'replSetReconfig': config})

    response = c.admin.command({'replSetReconfig': config})
    if ha_tools_debug:
        print(response)

    if not res:
        return None
    return host


def stepdown_primary():
    primary = get_primary()
    if primary:
        if ha_tools_debug:
            print('stepping down primary:', primary)
        c = pymongo.MongoClient(primary, use_greenlets=use_greenlets)
        # replSetStepDown causes mongod to close all connections
        try:
            c.admin.command('replSetStepDown', 20)
        except Exception as e:
            if ha_tools_debug:
                print('Exception from replSetStepDown:', e)
        if ha_tools_debug:
            print('\tcalled replSetStepDown')
    elif ha_tools_debug:
        print('stepdown_primary() found no primary')


def set_maintenance(member, value):
    """Put a member into RECOVERING state if value is True, else normal state.
    """
    c = pymongo.MongoClient(member, use_greenlets=use_greenlets)
    c.admin.command('replSetMaintenance', value)
    start = time.time()
    while value != (member in get_recovering()):
        assert (time.time() - start) <= 10, (
            "Member %s never switched state" % member)

        time.sleep(0.25)


def restart_members(members, router=False):
    restarted = []
    for member in members:
        if router:
            cmd = routers[member]['cmd']
        else:
            cmd = nodes[member]['cmd']
        proc = subprocess.Popen(cmd,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT)
        if router:
            routers[member]['proc'] = proc
        else:
            nodes[member]['proc'] = proc
        res = wait_for(proc, int(member.split(':')[1]))
        if res:
            restarted.append(member)
    return restarted

########NEW FILE########
__FILENAME__ = test_motor_ha
# Copyright 2012-2014 MongoDB, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Test replica set operations and failures. A Motor version of PyMongo's
   test/high_availability/test_ha.py
"""

from __future__ import print_function, unicode_literals

import time
import unittest
from tornado import gen, testing

import pymongo
from pymongo import ReadPreference
from pymongo.mongo_replica_set_client import Member, Monitor, _partition_node
from pymongo.errors import AutoReconnect, OperationFailure
from tornado.testing import gen_test

import motor
import ha_tools
from test.utils import one
from test import assert_raises, PauseMixin
from test_motor_ha_utils import assert_read_from, assert_read_from_all


# Override default 30-second interval for faster testing
Monitor._refresh_interval = MONITOR_INTERVAL = 0.5


# To make the code terser, copy modes into module scope
PRIMARY = ReadPreference.PRIMARY
PRIMARY_PREFERRED = ReadPreference.PRIMARY_PREFERRED
SECONDARY = ReadPreference.SECONDARY
SECONDARY_PREFERRED = ReadPreference.SECONDARY_PREFERRED
NEAREST = ReadPreference.NEAREST


class MotorHATestCase(PauseMixin, testing.AsyncTestCase):
    """A test case for Motor connections to replica sets or mongos."""

    def tearDown(self):
        ha_tools.kill_all_members()
        ha_tools.nodes.clear()
        ha_tools.routers.clear()
        time.sleep(1)  # Let members really die.


class MotorTestDirectConnection(MotorHATestCase):
    def setUp(self):
        super(MotorTestDirectConnection, self).setUp()
        members = [{}, {}, {'arbiterOnly': True}]
        res = ha_tools.start_replica_set(members)
        self.seed, self.name = res
        self.c = None

    @gen_test
    def test_secondary_connection(self):
        self.c = yield motor.MotorReplicaSetClient(
            self.seed, replicaSet=self.name).open()

        self.assertTrue(bool(len(self.c.secondaries)))
        db = self.c.motor_test
        yield db.test.remove({}, w=len(self.c.secondaries))

        # Wait for replication...
        w = len(self.c.secondaries) + 1
        yield db.test.insert({'foo': 'bar'}, w=w)

        # Test direct connection to a primary or secondary
        primary_host, primary_port = ha_tools.get_primary().split(':')
        primary_port = int(primary_port)
        (secondary_host,
         secondary_port) = ha_tools.get_secondaries()[0].split(':')
        secondary_port = int(secondary_port)
        arbiter_host, arbiter_port = ha_tools.get_arbiters()[0].split(':')
        arbiter_port = int(arbiter_port)

        # A connection succeeds no matter the read preference
        for kwargs in [
            {'read_preference': PRIMARY},
            {'read_preference': PRIMARY_PREFERRED},
            {'read_preference': SECONDARY},
            {'read_preference': SECONDARY_PREFERRED},
            {'read_preference': NEAREST},
        ]:
            client = yield motor.MotorClient(
                primary_host, primary_port, **kwargs).open()

            self.assertEqual(primary_host, client.host)
            self.assertEqual(primary_port, client.port)
            self.assertTrue(client.is_primary)

            # Direct connection to primary can be queried with any read pref
            self.assertTrue((yield client.motor_test.test.find_one()))

            client = yield motor.MotorClient(
                secondary_host, secondary_port, **kwargs).open()
            self.assertEqual(secondary_host, client.host)
            self.assertEqual(secondary_port, client.port)
            self.assertFalse(client.is_primary)

            # Direct connection to secondary can be queried with any read pref
            # but PRIMARY
            if kwargs.get('read_preference') != PRIMARY:
                self.assertTrue((
                    yield client.motor_test.test.find_one()))
            else:
                with assert_raises(AutoReconnect):
                    yield client.motor_test.test.find_one()

            # Since an attempt at an acknowledged write to a secondary from a
            # direct connection raises AutoReconnect('not master'), MotorClient
            # should do the same for unacknowledged writes.
            try:
                yield client.motor_test.test.insert({}, w=0)
            except AutoReconnect as e:
                self.assertEqual('not master', e.args[0])
            else:
                self.fail(
                    'Unacknowledged insert into secondary client %s should'
                    'have raised exception' % client)

            # Test direct connection to an arbiter
            client = yield motor.MotorClient(
                arbiter_host, arbiter_port, **kwargs).open()

            self.assertEqual(arbiter_host, client.host)
            self.assertEqual(arbiter_port, client.port)
            self.assertFalse(client.is_primary)

            # See explanation above
            try:
                yield client.motor_test.test.insert({}, w=0)
            except AutoReconnect as e:
                self.assertEqual('not master', e.args[0])
            else:
                self.fail(
                    'Unacknowledged insert into arbiter connection %s should'
                    'have raised exception' % client)

    def tearDown(self):
        self.c.close()
        super(MotorTestDirectConnection, self).tearDown()


class MotorTestPassiveAndHidden(MotorHATestCase):
    def setUp(self):
        super(MotorTestPassiveAndHidden, self).setUp()
        members = [
            {},
            {'priority': 0},
            {'arbiterOnly': True},
            {'priority': 0, 'hidden': True},
            {'priority': 0, 'slaveDelay': 5}]

        res = ha_tools.start_replica_set(members)
        self.seed, self.name = res

    @gen_test
    def test_passive_and_hidden(self):
        self.c = motor.MotorReplicaSetClient(self.seed, replicaSet=self.name)
        yield self.c.open()

        passives = ha_tools.get_passives()
        passives = [_partition_node(member) for member in passives]
        self.assertEqual(self.c.secondaries, set(passives))

        for mode in SECONDARY, SECONDARY_PREFERRED:
            yield assert_read_from_all(self, self.c, passives, mode)

        ha_tools.kill_members(ha_tools.get_passives(), 2)
        yield self.pause(2 * MONITOR_INTERVAL)
        yield assert_read_from(
            self, self.c, self.c.primary, SECONDARY_PREFERRED)

    def tearDown(self):
        self.c.close()
        super(MotorTestPassiveAndHidden, self).tearDown()


class MotorTestMonitorRemovesRecoveringMember(MotorHATestCase):
    # Members in STARTUP2 or RECOVERING states are shown in the primary's
    # isMaster response, but aren't secondaries and shouldn't be read from.
    # Verify that if a secondary goes into RECOVERING mode, the Monitor removes
    # it from the set of readers.

    def setUp(self):
        super(MotorTestMonitorRemovesRecoveringMember, self).setUp()
        members = [{}, {'priority': 0}, {'priority': 0}]
        res = ha_tools.start_replica_set(members)
        self.seed, self.name = res

    @gen_test
    def test_monitor_removes_recovering_member(self):
        self.c = motor.MotorReplicaSetClient(self.seed, replicaSet=self.name)
        yield self.c.open()
        secondaries = ha_tools.get_secondaries()

        for mode in SECONDARY, SECONDARY_PREFERRED:
            partitioned_secondaries = [_partition_node(s) for s in secondaries]
            yield assert_read_from_all(
                self, self.c, partitioned_secondaries, mode)

        secondary, recovering_secondary = secondaries
        ha_tools.set_maintenance(recovering_secondary, True)
        yield self.pause(2 * MONITOR_INTERVAL)

        for mode in SECONDARY, SECONDARY_PREFERRED:
            # Don't read from recovering member
            yield assert_read_from(
                self, self.c, _partition_node(secondary), mode)

    def tearDown(self):
        self.c.close()
        super(MotorTestMonitorRemovesRecoveringMember, self).tearDown()


class MotorTestTriggeredRefresh(MotorHATestCase):
    # Verify that if a secondary goes into RECOVERING mode or if the primary
    # changes, the next exception triggers an immediate refresh.
    def setUp(self):
        super(MotorTestTriggeredRefresh, self).setUp()
        members = [{}, {}]
        res = ha_tools.start_replica_set(members)
        self.seed, self.name = res

        # Disable periodic refresh
        Monitor._refresh_interval = 1e6

    @gen_test
    def test_recovering_member_triggers_refresh(self):
        # To test that find_one() and count() trigger immediate refreshes,
        # we'll create a separate client for each
        self.c_find_one, self.c_count = yield [
            motor.MotorReplicaSetClient(
                self.seed, replicaSet=self.name, read_preference=SECONDARY
            ).open() for _ in range(2)]

        # We've started the primary and one secondary
        primary = ha_tools.get_primary()
        secondary = ha_tools.get_secondaries()[0]

        # Pre-condition: just make sure they all connected OK
        for c in self.c_find_one, self.c_count:
            self.assertEqual(one(c.secondaries), _partition_node(secondary))

        ha_tools.set_maintenance(secondary, True)

        # Trigger a refresh in various ways
        with assert_raises(AutoReconnect):
            yield self.c_find_one.test.test.find_one()

        with assert_raises(AutoReconnect):
            yield self.c_count.test.test.count()

        # Wait for the immediate refresh to complete - we're not waiting for
        # the periodic refresh, which has been disabled
        yield self.pause(1)

        for c in self.c_find_one, self.c_count:
            self.assertFalse(c.secondaries)
            self.assertEqual(_partition_node(primary), c.primary)

    @gen_test
    def test_stepdown_triggers_refresh(self):
        c_find_one = yield motor.MotorReplicaSetClient(
            self.seed, replicaSet=self.name).open()

        # We've started the primary and one secondary
        primary = ha_tools.get_primary()
        secondary = ha_tools.get_secondaries()[0]
        self.assertEqual(
            one(c_find_one.secondaries), _partition_node(secondary))

        ha_tools.stepdown_primary()

        # Make sure the stepdown completes
        yield self.pause(1)

        # Trigger a refresh
        with assert_raises(AutoReconnect):
            yield c_find_one.test.test.find_one()

        # Wait for the immediate refresh to complete - we're not waiting for
        # the periodic refresh, which has been disabled
        yield self.pause(1)

        # We've detected the stepdown
        self.assertTrue(
            not c_find_one.primary
            or primary != _partition_node(c_find_one.primary))

    def tearDown(self):
        Monitor._refresh_interval = MONITOR_INTERVAL
        super(MotorTestTriggeredRefresh, self).tearDown()


class MotorTestHealthMonitor(MotorHATestCase):
    def setUp(self):
        super(MotorTestHealthMonitor, self).setUp()
        res = ha_tools.start_replica_set([{}, {}, {}])
        self.seed, self.name = res

    @gen_test(timeout=30)
    def test_primary_failure(self):
        c = motor.MotorReplicaSetClient(self.seed, replicaSet=self.name)
        yield c.open()
        self.assertTrue(c.secondaries)
        primary = c.primary
        secondaries = c.secondaries
        killed = ha_tools.kill_primary()
        self.assertTrue(bool(len(killed)))
        yield self.pause(1)

        # Wait for new primary to step up, and for MotorReplicaSetClient
        # to detect it.
        for _ in range(30):
            if c.primary != primary and c.secondaries != secondaries:
                break
            yield self.pause(1)
        else:
            self.fail("New primary not detected")

    @gen_test
    def test_secondary_failure(self):
        c = motor.MotorReplicaSetClient(self.seed, replicaSet=self.name)
        yield c.open()
        self.assertTrue(c.secondaries)
        primary = c.primary

        killed = ha_tools.kill_secondary()
        self.assertTrue(bool(len(killed)))
        self.assertEqual(primary, c.primary)

        yield self.pause(2 * MONITOR_INTERVAL)
        secondaries = c.secondaries

        ha_tools.restart_members([killed])
        self.assertEqual(primary, c.primary)

        # Wait for secondary to join, and for MotorReplicaSetClient
        # to detect it.
        for _ in range(30):
            if c.secondaries != secondaries:
                break
            yield self.pause(1)
        else:
            self.fail("Dead secondary not detected")

    @gen_test
    def test_primary_stepdown(self):
        c = motor.MotorReplicaSetClient(self.seed, replicaSet=self.name)
        yield c.open()
        self.assertTrue(bool(len(c.secondaries)))
        primary = c.primary
        secondaries = c.secondaries.copy()
        ha_tools.stepdown_primary()

        # Wait for primary to step down, and for MotorReplicaSetClient
        # to detect it.
        for _ in range(30):
            if c.primary != primary and secondaries != c.secondaries:
                break
            yield self.pause(1)
        else:
            self.fail("New primary not detected")


class MotorTestWritesWithFailover(MotorHATestCase):
    def setUp(self):
        super(MotorTestWritesWithFailover, self).setUp()
        res = ha_tools.start_replica_set([{}, {}, {}])
        self.seed, self.name = res

    @gen_test(timeout=30)
    def test_writes_with_failover(self):
        c = motor.MotorReplicaSetClient(self.seed, replicaSet=self.name)
        yield c.open()
        primary = c.primary
        db = c.motor_test
        w = len(c.secondaries) + 1
        yield db.test.remove(w=w)
        yield db.test.insert({'foo': 'bar'}, w=w)
        result = yield db.test.find_one()
        self.assertEqual('bar', result['foo'])

        killed = ha_tools.kill_primary(9)
        self.assertTrue(bool(len(killed)))
        yield self.pause(2)

        for _ in range(30):
            try:
                yield db.test.insert({'bar': 'baz'})

                # Success
                break
            except AutoReconnect:
                yield self.pause(1)
        else:
            self.fail("Couldn't insert after primary killed")

        self.assertTrue(primary != c.primary)
        result = yield db.test.find_one({'bar': 'baz'})
        self.assertEqual('baz', result['bar'])


class MotorTestReadWithFailover(MotorHATestCase):
    def setUp(self):
        super(MotorTestReadWithFailover, self).setUp()
        res = ha_tools.start_replica_set([{}, {}, {}])
        self.seed, self.name = res

    @gen_test
    def test_read_with_failover(self):
        c = motor.MotorReplicaSetClient(self.seed, replicaSet=self.name)
        yield c.open()
        self.assertTrue(c.secondaries)

        db = c.motor_test
        w = len(c.secondaries) + 1
        db.test.remove({}, w=w)
        # Force replication
        yield db.test.insert([{'foo': i} for i in range(10)], w=w)
        self.assertEqual(10, (yield db.test.count()))

        db.read_preference = SECONDARY
        cursor = db.test.find().batch_size(5)
        yield cursor.fetch_next
        self.assertEqual(5, cursor.delegate._Cursor__retrieved)
        for i in range(5):
            cursor.next_object()
        ha_tools.kill_primary()
        yield self.pause(2)

        # Primary failure shouldn't interrupt the cursor
        yield cursor.fetch_next
        self.assertEqual(10, cursor.delegate._Cursor__retrieved)


class MotorTestShipOfTheseus(MotorHATestCase):
    # If all of a replica set's members are replaced with new ones, is it still
    # the same replica set, or a different one?
    def setUp(self):
        super(MotorTestShipOfTheseus, self).setUp()
        res = ha_tools.start_replica_set([{}, {}])
        self.seed, self.name = res

    @gen_test(timeout=240)
    def test_ship_of_theseus(self):
        c = motor.MotorReplicaSetClient(self.seed, replicaSet=self.name)
        yield c.open()
        db = c.motor_test
        w = len(c.secondaries) + 1
        db.test.insert({}, w=w)

        primary = ha_tools.get_primary()
        secondary1 = ha_tools.get_random_secondary()
        ha_tools.add_member()
        ha_tools.add_member()
        ha_tools.add_member()

        # Wait for new members to join
        for _ in range(120):
            if ha_tools.get_primary() and len(ha_tools.get_secondaries()) == 4:
                break

            yield self.pause(1)
        else:
            self.fail("New secondaries didn't join")

        ha_tools.kill_members([primary, secondary1], 9)

        # Wait for primary
        for _ in range(30):
            if ha_tools.get_primary() and len(ha_tools.get_secondaries()) == 2:
                break

            yield self.pause(1)
        else:
            self.fail("No failover")

        # Ensure monitor picks up new members
        yield self.pause(2 * MONITOR_INTERVAL)

        try:
            yield db.test.find_one()
        except AutoReconnect:
            # Might take one try to reconnect
            yield self.pause(1)

        # No error
        yield db.test.find_one()
        yield db.test.find_one(read_preference=SECONDARY)


class MotorTestReadPreference(MotorHATestCase):
    def setUp(self):
        super(MotorTestReadPreference, self).setUp()
        members = [
            # primary
            {'tags': {'dc': 'ny', 'name': 'primary'}},

            # secondary
            {'tags': {'dc': 'la', 'name': 'secondary'}, 'priority': 0},

            # other_secondary
            {'tags': {'dc': 'ny', 'name': 'other_secondary'}, 'priority': 0},
        ]

        res = ha_tools.start_replica_set(members)
        self.seed, self.name = res

        primary = ha_tools.get_primary()
        self.primary = _partition_node(primary)
        self.primary_tags = ha_tools.get_tags(primary)
        # Make sure priority worked
        self.assertEqual('primary', self.primary_tags['name'])

        self.primary_dc = {'dc': self.primary_tags['dc']}

        secondaries = ha_tools.get_secondaries()

        (secondary, ) = [
            s for s in secondaries
            if ha_tools.get_tags(s)['name'] == 'secondary']

        self.secondary = _partition_node(secondary)
        self.secondary_tags = ha_tools.get_tags(secondary)
        self.secondary_dc = {'dc': self.secondary_tags['dc']}

        (other_secondary, ) = [
            s for s in secondaries
            if ha_tools.get_tags(s)['name'] == 'other_secondary']

        self.other_secondary = _partition_node(other_secondary)
        self.other_secondary_tags = ha_tools.get_tags(other_secondary)
        self.other_secondary_dc = {'dc': self.other_secondary_tags['dc']}

        # Synchronous PyMongo interfaces for convenience
        self.c = pymongo.mongo_replica_set_client.MongoReplicaSetClient(
            self.seed, replicaSet=self.name)
        self.db = self.c.motor_test
        self.w = len(self.c.secondaries) + 1
        self.db.test.remove({}, w=self.w)
        self.db.test.insert(
            [{'foo': i} for i in range(10)], w=self.w)

        self.clear_ping_times()

    def set_ping_time(self, host, ping_time_seconds):
        Member._host_to_ping_time[host] = ping_time_seconds

    def clear_ping_times(self):
        Member._host_to_ping_time.clear()

    @gen_test(timeout=240)
    def test_read_preference(self):
        # This is long, but we put all the tests in one function to save time
        # on setUp, which takes about 30 seconds to bring up a replica set.
        # We pass through four states:
        #
        #       1. A primary and two secondaries
        #       2. Primary down
        #       3. Primary up, one secondary down
        #       4. Primary up, all secondaries down
        #
        # For each state, we verify the behavior of PRIMARY,
        # PRIMARY_PREFERRED, SECONDARY, SECONDARY_PREFERRED, and NEAREST
        c = motor.MotorReplicaSetClient(self.seed, replicaSet=self.name)
        yield c.open()

        @gen.coroutine
        def read_from_which_host(
            rsc,
            mode,
            tag_sets=None,
            latency=15,
        ):
            db = rsc.motor_test
            db.read_preference = mode
            if isinstance(tag_sets, dict):
                tag_sets = [tag_sets]
            db.tag_sets = tag_sets or [{}]
            db.secondary_acceptable_latency_ms = latency

            cursor = db.test.find()
            try:
                yield cursor.fetch_next
                raise gen.Return(cursor.delegate._Cursor__connection_id)
            except AutoReconnect:
                raise gen.Return(None)

        @gen.coroutine
        def assert_read_from(member, *args, **kwargs):
            for _ in range(10):
                used = yield read_from_which_host(c, *args, **kwargs)
                self.assertEqual(member, used)

        @gen.coroutine
        def assert_read_from_all(members, *args, **kwargs):
            members = set(members)
            all_used = set()
            for _ in range(100):
                used = yield read_from_which_host(c, *args, **kwargs)
                all_used.add(used)
                if members == all_used:
                    raise gen.Return()  # Success

            # This will fail
            self.assertEqual(members, all_used)

        def unpartition_node(node):
            host, port = node
            return '%s:%s' % (host, port)

        primary = self.primary
        secondary = self.secondary
        other_secondary = self.other_secondary

        bad_tag = {'bad': 'tag'}

        # 1. THREE MEMBERS UP -------------------------------------------------
        #       PRIMARY
        yield assert_read_from(primary, PRIMARY)

        #       PRIMARY_PREFERRED
        # Trivial: mode and tags both match
        yield assert_read_from(primary, PRIMARY_PREFERRED, self.primary_dc)

        # Secondary matches but not primary, choose primary
        yield assert_read_from(primary, PRIMARY_PREFERRED, self.secondary_dc)

        # Chooses primary, ignoring tag sets
        yield assert_read_from(primary, PRIMARY_PREFERRED, self.primary_dc)

        # Chooses primary, ignoring tag sets
        yield assert_read_from(primary, PRIMARY_PREFERRED, bad_tag)
        yield assert_read_from(primary, PRIMARY_PREFERRED, [bad_tag, {}])

        #       SECONDARY
        yield assert_read_from_all(
            [secondary, other_secondary], SECONDARY, latency=9999999)

        #       SECONDARY_PREFERRED
        yield assert_read_from_all(
            [secondary, other_secondary], SECONDARY_PREFERRED, latency=9999999)

        # Multiple tags
        yield assert_read_from(
            secondary, SECONDARY_PREFERRED, self.secondary_tags)

        # Fall back to primary if it's the only one matching the tags
        yield assert_read_from(
            primary, SECONDARY_PREFERRED, {'name': 'primary'})

        # No matching secondaries
        yield assert_read_from(primary, SECONDARY_PREFERRED, bad_tag)

        # Fall back from non-matching tag set to matching set
        yield assert_read_from_all(
            [secondary, other_secondary],
            SECONDARY_PREFERRED, [bad_tag, {}], latency=9999999)

        yield assert_read_from(
            other_secondary,
            SECONDARY_PREFERRED, [bad_tag, {'dc': 'ny'}])

        #       NEAREST
        self.clear_ping_times()

        yield assert_read_from_all(
            [primary, secondary, other_secondary], NEAREST, latency=9999999)

        yield assert_read_from_all(
            [primary, other_secondary],
            NEAREST, [bad_tag, {'dc': 'ny'}], latency=9999999)

        self.set_ping_time(primary, 0)
        self.set_ping_time(secondary, .03)  # 30 milliseconds.
        self.set_ping_time(other_secondary, 10)

        # Nearest member, no tags
        yield assert_read_from(primary, NEAREST)

        # Tags override nearness
        yield assert_read_from(primary, NEAREST, {'name': 'primary'})
        yield assert_read_from(secondary, NEAREST, self.secondary_dc)

        # Make secondary fast
        self.set_ping_time(primary, .03)  # 30 milliseconds.
        self.set_ping_time(secondary, 0)

        yield assert_read_from(secondary, NEAREST)

        # Other secondary fast
        self.set_ping_time(secondary, 10)
        self.set_ping_time(other_secondary, 0)

        yield assert_read_from(other_secondary, NEAREST)

        # High secondaryAcceptableLatencyMS, should read from all members
        yield assert_read_from_all(
            [primary, secondary, other_secondary],
            NEAREST, latency=9999999)

        self.clear_ping_times()

        yield assert_read_from_all(
            [primary, other_secondary], NEAREST, [{'dc': 'ny'}],
            latency=9999999)

        # 2. PRIMARY DOWN -----------------------------------------------------
        killed = ha_tools.kill_primary()

        # Let monitor notice primary's gone
        yield self.pause(2 * MONITOR_INTERVAL)

        #       PRIMARY
        yield assert_read_from(None, PRIMARY)

        #       PRIMARY_PREFERRED
        # No primary, choose matching secondary
        yield assert_read_from_all(
            [secondary, other_secondary], PRIMARY_PREFERRED, latency=9999999)

        yield assert_read_from(
            secondary, PRIMARY_PREFERRED, {'name': 'secondary'})

        # No primary or matching secondary
        yield assert_read_from(None, PRIMARY_PREFERRED, bad_tag)

        #       SECONDARY
        yield assert_read_from_all(
            [secondary, other_secondary], SECONDARY, latency=9999999)

        # Only primary matches
        yield assert_read_from(None, SECONDARY, {'name': 'primary'})

        # No matching secondaries
        yield assert_read_from(None, SECONDARY, bad_tag)

        #       SECONDARY_PREFERRED
        yield assert_read_from_all(
            [secondary, other_secondary], SECONDARY_PREFERRED, latency=9999999)

        # Mode and tags both match
        yield assert_read_from(
            secondary, SECONDARY_PREFERRED, {'name': 'secondary'})

        #       NEAREST
        self.clear_ping_times()

        yield assert_read_from_all(
            [secondary, other_secondary], NEAREST, latency=9999999)

        # 3. PRIMARY UP, ONE SECONDARY DOWN -----------------------------------
        ha_tools.restart_members([killed])

        for _ in range(30):
            if ha_tools.get_primary():
                break
            yield self.pause(1)
        else:
            self.fail("Primary didn't come back up")

        ha_tools.kill_members([unpartition_node(secondary)], 2)
        self.assertTrue(pymongo.MongoClient(
            unpartition_node(primary),
            slave_okay=True
        ).admin.command('ismaster')['ismaster'])

        yield self.pause(2 * MONITOR_INTERVAL)

        #       PRIMARY
        yield assert_read_from(primary, PRIMARY)

        #       PRIMARY_PREFERRED
        yield assert_read_from(primary, PRIMARY_PREFERRED)

        #       SECONDARY
        yield assert_read_from(other_secondary, SECONDARY)
        yield assert_read_from(
            other_secondary, SECONDARY, self.other_secondary_dc)

        # Only the down secondary matches
        yield assert_read_from(None, SECONDARY, {'name': 'secondary'})

        #       SECONDARY_PREFERRED
        yield assert_read_from(other_secondary, SECONDARY_PREFERRED)
        yield assert_read_from(
            other_secondary, SECONDARY_PREFERRED, self.other_secondary_dc)

        # The secondary matching the tag is down, use primary
        yield assert_read_from(
            primary, SECONDARY_PREFERRED, {'name': 'secondary'})

        #       NEAREST
        yield assert_read_from_all(
            [primary, other_secondary], NEAREST, latency=9999999)

        yield assert_read_from(
            other_secondary, NEAREST, {'name': 'other_secondary'})

        yield assert_read_from(primary, NEAREST, {'name': 'primary'})

        # 4. PRIMARY UP, ALL SECONDARIES DOWN ---------------------------------
        ha_tools.kill_members([unpartition_node(other_secondary)], 2)
        self.assertTrue(pymongo.MongoClient(
            unpartition_node(primary),
            slave_okay=True
        ).admin.command('ismaster')['ismaster'])

        #       PRIMARY
        yield assert_read_from(primary, PRIMARY)

        #       PRIMARY_PREFERRED
        yield assert_read_from(primary, PRIMARY_PREFERRED)
        yield assert_read_from(primary, PRIMARY_PREFERRED, self.secondary_dc)

        #       SECONDARY
        yield assert_read_from(None, SECONDARY)
        yield assert_read_from(None, SECONDARY, self.other_secondary_dc)
        yield assert_read_from(None, SECONDARY, {'dc': 'ny'})

        #       SECONDARY_PREFERRED
        yield assert_read_from(primary, SECONDARY_PREFERRED)
        yield assert_read_from(primary, SECONDARY_PREFERRED, self.secondary_dc)
        yield assert_read_from(
            primary, SECONDARY_PREFERRED, {'name': 'secondary'})

        yield assert_read_from(primary, SECONDARY_PREFERRED, {'dc': 'ny'})

        #       NEAREST
        yield assert_read_from(primary, NEAREST)
        yield assert_read_from(None, NEAREST, self.secondary_dc)
        yield assert_read_from(None, NEAREST, {'name': 'secondary'})

        # Even if primary's slow, still read from it
        self.set_ping_time(primary, 100)
        yield assert_read_from(primary, NEAREST)
        yield assert_read_from(None, NEAREST, self.secondary_dc)

        self.clear_ping_times()

    def tearDown(self):
        self.c.close()
        self.clear_ping_times()
        super(MotorTestReadPreference, self).tearDown()


class MotorTestReplicaSetAuth(MotorHATestCase):
    def setUp(self):
        super(MotorTestReplicaSetAuth, self).setUp()
        members = [
            {},
            {'priority': 0},
            {'priority': 0},
        ]

        res = ha_tools.start_replica_set(members, auth=True)
        self.seed, self.name = res
        self.c = pymongo.mongo_replica_set_client.MongoReplicaSetClient(
            self.seed, replicaSet=self.name)

        # Add an admin user to enable auth
        try:
            self.c.admin.add_user('admin', 'adminpass')
        except OperationFailure:
            # SERVER-4225
            pass
        self.c.admin.authenticate('admin', 'adminpass')
        self.c.pymongo_ha_auth.add_user('user', 'userpass')

    @gen_test
    def test_auth_during_failover(self):
        c = motor.MotorReplicaSetClient(self.seed, replicaSet=self.name)
        yield c.open()
        db = c.pymongo_ha_auth
        res = yield db.authenticate('user', 'userpass')
        self.assertTrue(res)
        yield db.foo.insert({'foo': 'bar'}, w=3, wtimeout=1000)
        yield db.logout()
        with assert_raises(OperationFailure):
            yield db.foo.find_one()

        primary = '%s:%d' % self.c.primary
        ha_tools.kill_members([primary], 2)

        # Let monitor notice primary's gone
        yield self.pause(2 * MONITOR_INTERVAL)

        # Make sure we can still authenticate
        res = yield db.authenticate('user', 'userpass')
        self.assertTrue(res)

        # And still query.
        db.read_preference = PRIMARY_PREFERRED
        res = yield db.foo.find_one()
        self.assertEqual('bar', res['foo'])
        c.close()

    def tearDown(self):
        self.c.close()
        super(MotorTestReplicaSetAuth, self).tearDown()


class MotorTestAlive(MotorHATestCase):
    def setUp(self):
        super(MotorTestAlive, self).setUp()
        members = [{}, {}]
        self.seed, self.name = ha_tools.start_replica_set(members)

    @gen_test
    def test_alive(self):
        primary = ha_tools.get_primary()
        secondary = ha_tools.get_random_secondary()
        primary_cx = yield motor.MotorClient(primary).open()
        secondary_cx = yield motor.MotorClient(secondary).open()
        rsc = motor.MotorReplicaSetClient(self.seed, replicaSet=self.name)
        yield rsc.open()
        try:
            self.assertTrue((yield primary_cx.alive()))
            self.assertTrue((yield secondary_cx.alive()))
            self.assertTrue((yield rsc.alive()))

            ha_tools.kill_primary()
            yield self.pause(0.5)

            self.assertFalse((yield primary_cx.alive()))
            self.assertTrue((yield secondary_cx.alive()))
            self.assertFalse((yield rsc.alive()))

            ha_tools.kill_members([secondary], 2)
            yield self.pause(0.5)

            self.assertFalse((yield primary_cx.alive()))
            self.assertFalse((yield secondary_cx.alive()))
            self.assertFalse((yield rsc.alive()))
        finally:
            rsc.close()


class MotorTestMongosHighAvailability(MotorHATestCase):
    def setUp(self):
        super(MotorTestMongosHighAvailability, self).setUp()
        self.seed_list = ha_tools.create_sharded_cluster()

    @gen_test
    def test_mongos_ha(self):
        dbname = 'pymongo_mongos_ha'
        c = yield motor.MotorClient(self.seed_list).open()
        yield c.drop_database(dbname)
        coll = c[dbname].test
        yield coll.insert({'foo': 'bar'})

        first = '%s:%d' % (c.host, c.port)
        ha_tools.kill_mongos(first)
        yield self.pause(1)
        # Fail first attempt
        with assert_raises(AutoReconnect):
            yield coll.count()
        # Find new mongos
        self.assertEqual(1, (yield coll.count()))

        second = '%s:%d' % (c.host, c.port)
        self.assertNotEqual(first, second)
        ha_tools.kill_mongos(second)
        yield self.pause(1)
        # Fail first attempt
        with assert_raises(AutoReconnect):
            yield coll.count()
        # Find new mongos
        self.assertEqual(1, (yield coll.count()))

        third = '%s:%d' % (c.host, c.port)
        self.assertNotEqual(second, third)
        ha_tools.kill_mongos(third)
        yield self.pause(1)
        # Fail first attempt
        with assert_raises(AutoReconnect):
            yield coll.count()

        # We've killed all three, restart one.
        ha_tools.restart_mongos(first)
        yield self.pause(1)

        # Find new mongos
        self.assertEqual(1, (yield coll.count()))


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_motor_ha_utils
# Copyright 2013-2014 MongoDB, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import print_function, unicode_literals

"""Help test MotorReplicaSetClient and read preferences.

Motor's version of some replica set testing functions in PyMongo's test.utils.
"""

from tornado import gen
from pymongo.errors import AutoReconnect


@gen.coroutine
def read_from_which_host(
        rsc, mode,
        tag_sets=None, secondary_acceptable_latency_ms=15):
    """Read from a MongoReplicaSetClient with the given Read Preference mode,
       tags, and acceptable latency. Return the 'host:port' which was read from.

    :Parameters:
      - `rsc`: A MongoReplicaSetClient
      - `mode`: A ReadPreference
      - `tag_sets`: List of dicts of tags for data-center-aware reads
      - `secondary_acceptable_latency_ms`: a float
    """
    db = rsc.motor_test
    db.read_preference = mode
    if isinstance(tag_sets, dict):
        tag_sets = [tag_sets]
    db.tag_sets = tag_sets or [{}]
    db.secondary_acceptable_latency_ms = secondary_acceptable_latency_ms

    cursor = db.test.find()
    try:
        yield cursor.fetch_next
        host = cursor.delegate._Cursor__connection_id
    except AutoReconnect:
        host = None

    raise gen.Return(host)


@gen.coroutine
def assert_read_from(
        testcase, rsc, member, mode,
        tag_sets=None, secondary_acceptable_latency_ms=15):
    """Check that a query with the given mode, tag_sets, and
       secondary_acceptable_latency_ms reads from the expected replica-set
       member

    :Parameters:
      - `testcase`: A unittest.TestCase
      - `rsc`: A MongoReplicaSetClient
      - `member`: Member expected to be used
      - `mode`: A ReadPreference
      - `tag_sets`: List of dicts of tags for data-center-aware reads
      - `secondary_acceptable_latency_ms`: a float
      - `callback`: Function taking (None, error)
    """
    nsamples = 10
    used = yield [
        read_from_which_host(
            rsc, mode, tag_sets, secondary_acceptable_latency_ms)
        for _ in range(nsamples)
    ]

    testcase.assertEqual([member] * nsamples, used)


@gen.coroutine
def assert_read_from_all(
        testcase, rsc, members, mode,
        tag_sets=None, secondary_acceptable_latency_ms=15):
    """Check that a query with the given mode, tag_sets, and
    secondary_acceptable_latency_ms reads from all members in a set, and
    only members in that set.

    :Parameters:
      - `testcase`: A unittest.TestCase
      - `rsc`: A MotorReplicaSetClient
      - `members`: Sequence of expected host:port to be used
      - `mode`: A ReadPreference
      - `tag_sets` (optional): List of dicts of tags for data-center-aware reads
      - `secondary_acceptable_latency_ms` (optional): a float
      - `callback`: Function taking (None, error)
    """
    nsamples = 100
    members = set(members)
    used = set((yield [
        read_from_which_host(
            rsc, mode, tag_sets, secondary_acceptable_latency_ms)
        for _ in range(nsamples)
    ]))

    testcase.assertEqual(members, used)

########NEW FILE########
__FILENAME__ = motor_client_test_generic
# Copyright 2012-2014 MongoDB, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import unicode_literals

"""Generic tests for MotorClient and MotorReplicaSetClient."""
import time

import pymongo.errors
import pymongo.mongo_replica_set_client
from tornado import gen
from tornado.testing import gen_test

import motor
from test import assert_raises
from test.utils import server_is_master_with_slave, remove_all_users
from test.utils import skip_if_mongos


class MotorClientTestMixin(object):
    def get_client(self):
        raise NotImplementedError()

    def test_requests(self):
        for method in 'start_request', 'in_request', 'end_request':
            self.assertRaises(TypeError, getattr(self.get_client(), method))

    @gen_test
    def test_copy_db_argument_checking(self):
        cx = self.get_client()
        with assert_raises(TypeError):
            yield cx.copy_database(4, 'foo')

        with assert_raises(TypeError):
            yield cx.copy_database('foo', 4)

        with assert_raises(pymongo.errors.InvalidName):
            yield cx.copy_database('foo', '$foo')

    @gen_test
    def test_copy_db_callback(self):
        cx = self.get_client()
        yield cx.drop_database('target')
        name = cx.motor_test.name
        (result, error), _ = yield gen.Task(
            cx.copy_database, name, 'target')

        self.assertTrue(isinstance(result, dict))
        self.assertEqual(error, None)

        yield cx.drop_database('target')

        client = motor.MotorClient('doesntexist', connectTimeoutMS=10)
        (result, error), _ = yield gen.Task(
            client.copy_database, name, 'target')

        self.assertEqual(result, None)
        self.assertTrue(isinstance(error, Exception))

    @gen.coroutine
    def drop_databases(self, database_names, authenticated_client=None):
        cx = authenticated_client or self.get_client()
        for test_db_name in database_names:
            yield cx.drop_database(test_db_name)

        # Due to SERVER-2329, databases may not disappear from a master
        # in a master-slave pair.
        if not (yield server_is_master_with_slave(cx)):
            start = time.time()

            # There may be a race condition in the server's dropDatabase. Wait
            # for it to update its namespaces.
            db_names = yield cx.database_names()
            while time.time() - start < 30:
                remaining_test_dbs = (
                    set(database_names).intersection(db_names))

                if not remaining_test_dbs:
                    # All test DBs are removed.
                    break

                yield self.pause(0.1)
                db_names = yield cx.database_names()

            for test_db_name in database_names:
                self.assertFalse(
                    test_db_name in db_names,
                    "%s not dropped" % test_db_name)

    @gen.coroutine
    def check_copydb_results(self, doc, test_db_names):
        cx = self.get_client()
        for test_db_name in test_db_names:
            self.assertEqual(
                doc,
                (yield cx[test_db_name].test_collection.find_one()))

    @gen_test
    def test_copy_db(self):
        cx = self.get_client()
        target_db_name = 'motor_test_2'

        yield cx.drop_database(target_db_name)
        yield self.collection.insert({'_id': 1})
        result = yield cx.copy_database("motor_test", target_db_name)
        self.assertTrue(isinstance(result, dict))
        self.assertEqual(
            {'_id': 1},
            (yield cx[target_db_name].test_collection.find_one()))

        yield cx.drop_database(target_db_name)

    @gen_test(timeout=300)
    def test_copy_db_concurrent(self):
        n_copies = 2
        target_db_names = ['motor_test_%s' % i for i in range(n_copies)]

        # 1. Drop old test DBs
        cx = self.get_client()
        yield cx.drop_database('motor_test')
        yield self.drop_databases(target_db_names)

        # 2. Copy a test DB N times at once
        collection = cx.motor_test.test_collection
        yield collection.insert({'_id': 1})
        results = yield [
            cx.copy_database('motor_test', test_db_name)
            for test_db_name in target_db_names]

        self.assertTrue(all(isinstance(i, dict) for i in results))
        yield self.check_copydb_results({'_id': 1}, target_db_names)
        yield self.drop_databases(target_db_names)

    @gen_test
    def test_copy_db_auth(self):
        # See SERVER-6427.
        cx = self.get_client()
        yield skip_if_mongos(cx)

        target_db_name = 'motor_test_2'

        collection = cx.motor_test.test_collection
        yield collection.remove()
        yield collection.insert({'_id': 1})

        yield cx.admin.add_user('admin', 'password')
        yield cx.admin.authenticate('admin', 'password')

        try:
            yield cx.motor_test.add_user('mike', 'password')

            with assert_raises(pymongo.errors.OperationFailure):
                yield cx.copy_database(
                    'motor_test', target_db_name,
                    username='foo', password='bar')

            with assert_raises(pymongo.errors.OperationFailure):
                yield cx.copy_database(
                    'motor_test', target_db_name,
                    username='mike', password='bar')

            # Copy a database using name and password.
            yield cx.copy_database(
                'motor_test', target_db_name,
                username='mike', password='password')

            self.assertEqual(
                {'_id': 1},
                (yield cx[target_db_name].test_collection.find_one()))

            yield cx.drop_database(target_db_name)
        finally:
            yield remove_all_users(cx.motor_test)
            yield cx.admin.remove_user('admin')

    @gen_test(timeout=30)
    def test_copy_db_auth_concurrent(self):
        cx = self.get_client()
        yield skip_if_mongos(cx)

        n_copies = 2
        test_db_names = ['motor_test_%s' % i for i in range(n_copies)]

        # 1. Drop old test DBs
        yield cx.drop_database('motor_test')
        yield self.drop_databases(test_db_names)

        # 2. Copy a test DB N times at once
        collection = cx.motor_test.test_collection
        yield collection.remove()
        yield collection.insert({'_id': 1})

        yield cx.admin.add_user('admin', 'password', )
        yield cx.admin.authenticate('admin', 'password')

        try:
            yield cx.motor_test.add_user('mike', 'password')

            results = yield [
                cx.copy_database(
                    'motor_test', test_db_name,
                    username='mike', password='password')
                for test_db_name in test_db_names]

            self.assertTrue(all(isinstance(i, dict) for i in results))
            yield self.check_copydb_results({'_id': 1}, test_db_names)

        finally:
            yield remove_all_users(cx.motor_test)
            yield self.drop_databases(test_db_names, authenticated_client=cx)
            yield cx.admin.remove_user('admin')

########NEW FILE########
__FILENAME__ = test_motor_basic
# Copyright 2013-2014 MongoDB, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import unicode_literals, absolute_import

"""Test Motor, an asynchronous driver for MongoDB and Tornado."""

import pymongo
from pymongo.errors import ConfigurationError
from pymongo.read_preferences import ReadPreference
from tornado.testing import gen_test

import motor
import test
from test import host, port, assert_raises, MotorTest, setUpModule


class MotorTestBasic(MotorTest):
    def test_repr(self):
        self.assertTrue(repr(self.cx).startswith('MotorClient'))
        self.assertTrue(repr(self.db).startswith('MotorDatabase'))
        self.assertTrue(repr(self.collection).startswith('MotorCollection'))
        cursor = self.collection.find()
        self.assertTrue(repr(cursor).startswith('MotorCursor'))

    @gen_test
    def test_write_concern(self):
        # Default empty dict means "w=1"
        self.assertEqual({}, self.cx.write_concern)

        yield self.collection.insert({'_id': 0})

        for gle_options in [
            {},
            {'w': 0},
            {'w': 1},
            {'wtimeout': 1000},
        ]:
            cx = self.motor_client(host, port, **gle_options)
            expected_wc = gle_options.copy()
            self.assertEqual(expected_wc, cx.write_concern)

            db = cx.motor_test
            self.assertEqual(expected_wc, db.write_concern)

            collection = db.test_collection
            self.assertEqual(expected_wc, collection.write_concern)

            if gle_options.get('w') == 0:
                yield collection.insert({'_id': 0})  # No error
            else:
                with assert_raises(pymongo.errors.DuplicateKeyError):
                    yield collection.insert({'_id': 0})

            # No error
            yield collection.insert({'_id': 0}, w=0)
            cx.close()

        collection = self.db.test_collection
        collection.write_concern['w'] = 2

        # No error
        yield collection.insert({'_id': 0}, w=0)

        cxw2 = self.motor_client(w=2)
        yield cxw2.motor_test.test_collection.insert({'_id': 0}, w=0)

        # Test write concerns passed to MotorClient, set on collection, or
        # passed to insert.
        if test.is_replica_set:
            with assert_raises(pymongo.errors.DuplicateKeyError):
                yield cxw2.motor_test.test_collection.insert({'_id': 0})

            with assert_raises(pymongo.errors.DuplicateKeyError):
                yield collection.insert({'_id': 0})

            with assert_raises(pymongo.errors.DuplicateKeyError):
                yield self.collection.insert({'_id': 0}, w=2)
        else:
            # w > 1 and no replica set
            with assert_raises(pymongo.errors.OperationFailure):
                yield cxw2.motor_test.test_collection.insert({'_id': 0})

            with assert_raises(pymongo.errors.OperationFailure):
                yield collection.insert({'_id': 0})

            with assert_raises(pymongo.errors.OperationFailure):
                yield self.collection.insert({'_id': 0}, w=2)

        # Important that the last operation on each MotorClient was
        # acknowledged, so lingering messages aren't delivered in the middle of
        # the next test. Also, a quirk of tornado.testing.AsyncTestCase:  we
        # must relinquish all file descriptors before its tearDown calls
        # self.io_loop.close(all_fds=True).
        cxw2.close()

    @gen_test
    def test_read_preference(self):
        # Check the default
        cx = motor.MotorClient(host, port, io_loop=self.io_loop)
        self.assertEqual(ReadPreference.PRIMARY, cx.read_preference)

        # We can set mode, tags, and latency.
        cx = self.motor_client(
            read_preference=ReadPreference.SECONDARY,
            tag_sets=[{'foo': 'bar'}],
            secondary_acceptable_latency_ms=42)

        self.assertEqual(ReadPreference.SECONDARY, cx.read_preference)
        self.assertEqual([{'foo': 'bar'}], cx.tag_sets)
        self.assertEqual(42, cx.secondary_acceptable_latency_ms)

        # Make a MotorCursor and get its PyMongo Cursor
        motor_cursor = cx.motor_test.test_collection.find(
            io_loop=self.io_loop,
            read_preference=ReadPreference.NEAREST,
            tag_sets=[{'yay': 'jesse'}],
            secondary_acceptable_latency_ms=17)

        cursor = motor_cursor.delegate

        self.assertEqual(
            ReadPreference.NEAREST, cursor._Cursor__read_preference)

        self.assertEqual([{'yay': 'jesse'}], cursor._Cursor__tag_sets)
        self.assertEqual(17, cursor._Cursor__secondary_acceptable_latency_ms)

        cx.close()

    @gen_test
    def test_safe(self):
        # Motor doesn't support 'safe'
        self.assertRaises(
            ConfigurationError,
            motor.MotorClient, host, port, io_loop=self.io_loop, safe=True)

        self.assertRaises(
            ConfigurationError,
            motor.MotorClient, host, port, io_loop=self.io_loop, safe=False)

        self.assertRaises(
            ConfigurationError, self.collection.insert, {}, safe=False)

        self.assertRaises(
            ConfigurationError, self.collection.insert, {}, safe=True)

    @gen_test
    def test_slave_okay(self):
        # Motor doesn't support 'slave_okay'
        self.assertRaises(
            ConfigurationError,
            motor.MotorClient, host, port,
            io_loop=self.io_loop, slave_okay=True)

        self.assertRaises(
            ConfigurationError,
            motor.MotorClient, host, port,
            io_loop=self.io_loop, slave_okay=False)

        self.assertRaises(
            ConfigurationError,
            motor.MotorClient, host, port,
            io_loop=self.io_loop, slaveok=True)

        self.assertRaises(
            ConfigurationError,
            motor.MotorClient, host, port,
            io_loop=self.io_loop, slaveok=False)

        collection = self.cx.motor_test.test_collection

        self.assertRaises(
            ConfigurationError,
            collection.find_one, slave_okay=True)

        self.assertRaises(
            ConfigurationError,
            collection.find_one, slaveok=True)

########NEW FILE########
__FILENAME__ = test_motor_bulk
# Copyright 2014 MongoDB, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import unicode_literals

"""Test Motor's bulk API."""

import unittest

from pymongo.errors import BulkWriteError
from tornado.testing import gen_test

import motor
from test import MotorTest, setUpModule


class MotorBulkTest(MotorTest):

    # This is just a smattering of tests, since the logic is all in PyMongo.

    @gen_test
    def test_multiple_error_ordered_batch(self):
        yield self.collection.remove()
        yield self.collection.ensure_index('a', unique=True)
        try:
            bulk = self.collection.initialize_ordered_bulk_op()
            self.assertTrue(isinstance(bulk, motor.MotorBulkOperationBuilder))
            bulk.insert({'b': 1, 'a': 1})
            bulk.find({'b': 2}).upsert().update_one({'$set': {'a': 1}})
            bulk.find({'b': 3}).upsert().update_one({'$set': {'a': 2}})
            bulk.find({'b': 2}).upsert().update_one({'$set': {'a': 1}})
            bulk.insert({'b': 4, 'a': 3})
            bulk.insert({'b': 5, 'a': 1})

            try:
                yield bulk.execute()
            except BulkWriteError as exc:
                result = exc.details
                self.assertEqual(exc.code, 65)
            else:
                self.fail("Error not raised")

            self.assertEqual(1, result['nInserted'])
            self.assertEqual(1, len(result['writeErrors']))

            error = result['writeErrors'][0]
            self.assertEqual(1, error['index'])

            failed = error['op']
            self.assertEqual(2, failed['q']['b'])
            self.assertEqual(1, failed['u']['$set']['a'])
            self.assertFalse(failed['multi'])
            self.assertTrue(failed['upsert'])
            
            cursor = self.collection.find({}, {'_id': False})
            docs = yield cursor.to_list(None)
            self.assertEqual([{'a': 1, 'b': 1}], docs)
        finally:
            yield self.collection.drop_index([('a', 1)])

    @gen_test
    def test_single_unordered_batch(self):
        yield self.collection.remove()

        bulk = self.collection.initialize_unordered_bulk_op()
        self.assertTrue(isinstance(bulk, motor.MotorBulkOperationBuilder))
        bulk.insert({'a': 1})
        bulk.find({'a': 1}).update_one({'$set': {'b': 1}})
        bulk.find({'a': 2}).upsert().update_one({'$set': {'b': 2}})
        bulk.insert({'a': 3})
        bulk.find({'a': 3}).remove()
        result = yield bulk.execute()
        self.assertEqual(0, len(result['writeErrors']))
        upserts = result['upserted']
        self.assertEqual(1, len(upserts))
        self.assertEqual(2, upserts[0]['index'])
        self.assertTrue(upserts[0].get('_id'))

        a_values = yield self.collection.distinct('a')
        self.assertEqual(
            set([1, 2]),
            set(a_values))

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_motor_client
# Copyright 2012-2014 MongoDB, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import unicode_literals

"""Test Motor, an asynchronous driver for MongoDB and Tornado."""

import os
import socket
import unittest
import sys

import pymongo
from pymongo.errors import ConfigurationError, OperationFailure
from pymongo.errors import ConnectionFailure
from tornado import gen
from tornado.concurrent import Future
from tornado.ioloop import IOLoop
from tornado.testing import gen_test, netutil

import motor
import test
from test import host, port, assert_raises, MotorTest, setUpModule, SkipTest
from test.motor_client_test_generic import MotorClientTestMixin
from test.utils import server_started_with_auth, remove_all_users, delay


class MotorClientTest(MotorTest):
    @gen_test
    def test_client_open(self):
        cx = motor.MotorClient(host, port, io_loop=self.io_loop)
        self.assertEqual(cx, (yield cx.open()))
        self.assertEqual(cx, (yield cx.open()))  # Same the second time.

    @gen_test
    def test_client_lazy_connect(self):
        test.sync_cx.motor_test.test_client_lazy_connect.remove()

        # Create client without connecting; connect on demand.
        cx = motor.MotorClient(host, port, io_loop=self.io_loop)
        collection = cx.motor_test.test_client_lazy_connect
        future0 = collection.insert({'foo': 'bar'})
        future1 = collection.insert({'foo': 'bar'})
        yield [future0, future1]

        self.assertEqual(2, (yield collection.find({'foo': 'bar'}).count()))

        cx.close()

    @gen_test
    def test_disconnect(self):
        cx = self.motor_client()
        cx.disconnect()
        self.assertEqual(None, cx._get_primary_pool())

    @gen_test
    def test_unix_socket(self):
        if not hasattr(socket, "AF_UNIX"):
            raise SkipTest("UNIX-sockets are not supported on this system")

        if (sys.platform == 'darwin' and
                (yield server_started_with_auth(self.cx))):
            raise SkipTest("SERVER-8492")

        mongodb_socket = '/tmp/mongodb-27017.sock'
        if not os.access(mongodb_socket, os.R_OK):
            raise SkipTest("Socket file is not accessible")

        yield motor.MotorClient(
            "mongodb://%s" % mongodb_socket, io_loop=self.io_loop).open()

        client = yield motor.MotorClient(
            "mongodb://%s" % mongodb_socket, io_loop=self.io_loop).open()

        yield client.motor_test.test.save({"dummy": "object"})

        # Confirm we can read via the socket.
        dbs = yield client.database_names()
        self.assertTrue("motor_test" in dbs)
        client.close()

        # Confirm it fails with a missing socket.
        client = motor.MotorClient(
            "mongodb:///tmp/non-existent.sock", io_loop=self.io_loop)

        with assert_raises(ConnectionFailure):
            yield client.open()

    def test_io_loop(self):
        with assert_raises(TypeError):
            motor.MotorClient(host, port, io_loop='foo')

    def test_open_sync(self):
        loop = IOLoop()
        cx = loop.run_sync(motor.MotorClient(host, port, io_loop=loop).open)
        self.assertTrue(isinstance(cx, motor.MotorClient))

    def test_database_named_delegate(self):
        self.assertTrue(
            isinstance(self.cx.delegate, pymongo.mongo_client.MongoClient))
        self.assertTrue(isinstance(self.cx['delegate'], motor.MotorDatabase))

    @gen_test
    def test_timeout(self):
        # Launch two slow find_ones. The one with a timeout should get an error
        no_timeout = self.motor_client()
        timeout = self.motor_client(host, port, socketTimeoutMS=100)
        query = {'$where': delay(0.5), '_id': 1}

        # Need a document, or the $where clause isn't executed.
        yield no_timeout.motor_test.test_collection.insert({'_id': 1})
        timeout_fut = timeout.motor_test.test_collection.find_one(query)
        notimeout_fut = no_timeout.motor_test.test_collection.find_one(query)

        error = None
        try:
            yield [timeout_fut, notimeout_fut]
        except pymongo.errors.AutoReconnect as e:
            error = e

        self.assertEqual(str(error), 'timed out')
        self.assertEqual({'_id': 1}, notimeout_fut.result())
        no_timeout.close()
        timeout.close()

    @gen_test
    def test_connection_failure(self):
        # Assuming there isn't anything actually running on this port
        client = motor.MotorClient('localhost', 8765, io_loop=self.io_loop)

        # Test the Future interface.
        with assert_raises(ConnectionFailure):
            yield client.open()

        # Test with a callback.
        (result, error), _ = yield gen.Task(client.open)
        self.assertEqual(None, result)
        self.assertTrue(isinstance(error, ConnectionFailure))

    @gen_test
    def test_connection_timeout(self):
        # Motor merely tries to time out a connection attempt within the
        # specified duration; DNS lookup in particular isn't charged against
        # the timeout. So don't measure how long this takes.
        client = motor.MotorClient(
            'example.com', port=12345,
            connectTimeoutMS=1, io_loop=self.io_loop)

        with assert_raises(ConnectionFailure):
            yield client.open()

    @gen_test
    def test_max_pool_size_validation(self):
        with assert_raises(ConfigurationError):
            motor.MotorClient(host=host, port=port, max_pool_size=-1)

        with assert_raises(ConfigurationError):
            motor.MotorClient(host=host, port=port, max_pool_size='foo')

        cx = motor.MotorClient(
            host=host, port=port, max_pool_size=100, io_loop=self.io_loop)

        self.assertEqual(cx.max_pool_size, 100)
        cx.close()

    @gen_test
    def test_high_concurrency(self):
        yield self.make_test_data()

        concurrency = 100
        cx = self.motor_client(max_pool_size=concurrency)
        test.sync_db.insert_collection.drop()
        self.assertEqual(200, test.sync_collection.count())
        expected_finds = 200 * concurrency
        n_inserts = 100

        collection = cx.motor_test.test_collection
        insert_collection = cx.motor_test.insert_collection

        ndocs = [0]
        insert_future = Future()

        @gen.coroutine
        def find():
            cursor = collection.find()
            while (yield cursor.fetch_next):
                cursor.next_object()
                ndocs[0] += 1

                # Half-way through, start an insert loop
                if ndocs[0] == expected_finds / 2:
                    insert()

        @gen.coroutine
        def insert():
            for i in range(n_inserts):
                yield insert_collection.insert({'s': hex(i)})

            insert_future.set_result(None)  # Finished

        yield [find() for _ in range(concurrency)]
        yield insert_future
        self.assertEqual(expected_finds, ndocs[0])
        self.assertEqual(n_inserts, test.sync_db.insert_collection.count())
        test.sync_db.insert_collection.drop()

    @gen_test
    def test_drop_database(self):
        # Make sure we can pass a MotorDatabase instance to drop_database
        db = self.cx.test_drop_database
        yield db.test_collection.insert({})
        names = yield self.cx.database_names()
        self.assertTrue('test_drop_database' in names)
        yield self.cx.drop_database(db)
        names = yield self.cx.database_names()
        self.assertFalse('test_drop_database' in names)

    @gen_test
    def test_auth_from_uri(self):
        if not (yield server_started_with_auth(self.cx)):
            raise SkipTest('Authentication is not enabled on server')

        yield remove_all_users(self.db)
        yield remove_all_users(self.cx.admin)
        yield self.cx.admin.add_user('admin', 'pass')
        yield self.cx.admin.authenticate('admin', 'pass')

        db = self.db
        try:
            yield db.add_user(
                'mike', 'password',
                roles=['userAdmin', 'readWrite'])

            client = motor.MotorClient('mongodb://foo:bar@%s:%d' % (host, port))

            # Note: open() only calls ismaster, doesn't throw auth errors.
            yield client.open()

            with assert_raises(OperationFailure):
                yield client.db.collection.find_one()

            client.close()

            client = motor.MotorClient(
                'mongodb://user:pass@%s:%d/%s' %
                (host, port, db.name))

            yield client.open()
            client.close()

            client = motor.MotorClient(
                'mongodb://mike:password@%s:%d/%s' %
                (host, port, db.name))

            yield client[db.name].collection.find_one()
            client.close()

        finally:
            yield db.remove_user('mike')
            yield self.cx.admin.remove_user('admin')


class MotorResolverTest(MotorTest):
    nonexistent_domain = 'doesntexist'

    def setUp(self):
        super(MotorResolverTest, self).setUp()

        # Caching the lookup helps prevent timeouts, at least on Mac OS.
        try:
            socket.getaddrinfo(self.nonexistent_domain, port)
        except socket.gaierror:
            pass

    # Helper method.
    @gen.coroutine
    def test_resolver(self, resolver_name):
        config = netutil.Resolver._save_configuration()
        try:
            netutil.Resolver.configure(resolver_name)
            client = motor.MotorClient(host, port, io_loop=self.io_loop)
            yield client.open()  # No error.

            with assert_raises(pymongo.errors.ConnectionFailure):
                client = motor.MotorClient(
                    self.nonexistent_domain,
                    connectTimeoutMS=100,
                    io_loop=self.io_loop)

                yield client.open()

        finally:
            netutil.Resolver._restore_configuration(config)

    test_resolver.__test__ = False

    @gen_test
    def test_blocking_resolver(self):
        yield self.test_resolver('tornado.netutil.BlockingResolver')

    @gen_test
    def test_threaded_resolver(self):
        try:
            import concurrent.futures
        except ImportError:
            raise SkipTest('concurrent.futures module not available')

        yield self.test_resolver('tornado.netutil.ThreadedResolver')

    @gen_test
    def test_twisted_resolver(self):
        try:
            import twisted
        except ImportError:
            raise SkipTest('Twisted not installed')
        yield self.test_resolver('tornado.platform.twisted.TwistedResolver')

    @gen_test(timeout=30)
    def test_cares_resolver(self):
        try:
            import pycares
        except ImportError:
            raise SkipTest('pycares not installed')
        yield self.test_resolver(
            'tornado.platform.caresresolver.CaresResolver')


class MotorClientTestGeneric(MotorClientTestMixin, MotorTest):
    def get_client(self):
        return self.cx


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_motor_collection
# Copyright 2012-2014 MongoDB, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import unicode_literals

"""Test Motor, an asynchronous driver for MongoDB and Tornado."""

import unittest

import bson
from bson.objectid import ObjectId
from pymongo import ReadPreference
from pymongo.errors import DuplicateKeyError
from tornado import gen
from tornado.concurrent import Future
from tornado.testing import gen_test

import motor
import test
from test import MotorTest, assert_raises, version, setUpModule, SkipTest
from test.utils import delay, skip_if_mongos


class MotorCollectionTest(MotorTest):
    @gen_test
    def test_collection(self):
        # Test that we can create a collection directly, not just from
        # MotorClient's accessors
        collection = motor.MotorCollection(self.db, 'test_collection')

        # Make sure we got the right collection and it can do an operation
        self.assertEqual('test_collection', collection.name)
        test.sync_collection.insert({'_id': 1})
        doc = yield collection.find_one({'_id': 1})
        self.assertEqual(1, doc['_id'])

        # If you pass kwargs to PyMongo's Collection(), it calls
        # db.create_collection(). Motor can't do I/O in a constructor
        # so this is prohibited.
        self.assertRaises(
            TypeError,
            motor.MotorCollection, self.db, 'test_collection', capped=True)

    @gen_test
    def test_dotted_collection_name(self):
        # Ensure that remove, insert, and find work on collections with dots
        # in their names.
        for coll in (
                self.db.foo.bar,
                self.db.foo.bar.baz):
            yield coll.remove()
            self.assertEqual('xyzzy', (yield coll.insert({'_id': 'xyzzy'})))
            result = yield coll.find_one({'_id': 'xyzzy'})
            self.assertEqual(result['_id'], 'xyzzy')
            yield coll.remove()
            self.assertEqual(None, (yield coll.find_one({'_id': 'xyzzy'})))

    def test_call(self):
        # Prevents user error with nice message.
        try:
            self.db.foo()
        except TypeError as e:
            self.assertTrue('no such method exists' in str(e))
        else:
            self.fail('Expected TypeError')

    @gen_test
    def test_find_is_async(self):
        # Confirm find() is async by launching two operations which will finish
        # out of order. Also test that MotorClient doesn't reuse sockets
        # incorrectly.

        # Launch find operations for _id's 1 and 2 which will finish in order
        # 2, then 1.
        coll = self.collection
        yield coll.insert([{'_id': 1}, {'_id': 2}])
        results = []

        futures = [Future(), Future()]

        def callback(result, error):
            if result:
                results.append(result)
                futures.pop().set_result(None)

        # This find() takes 0.5 seconds.
        coll.find({'_id': 1, '$where': delay(0.5)}).limit(1).each(callback)

        # Very fast lookup.
        coll.find({'_id': 2}).limit(1).each(callback)

        yield futures

        # Results were appended in order 2, 1.
        self.assertEqual([{'_id': 2}, {'_id': 1}], results)

    @gen_test
    def test_find_and_cancel(self):
        collection = self.collection
        yield collection.insert([{'_id': i} for i in range(3)])

        results = []

        future = Future()

        def callback(doc, error):
            if error:
                raise error

            results.append(doc)

            if len(results) == 2:
                future.set_result(None)
                # cancel iteration
                return False

        cursor = collection.find().sort('_id')
        cursor.each(callback)
        yield future

        # There are 3 docs, but we canceled after 2
        self.assertEqual([{'_id': 0}, {'_id': 1}], results)

        yield cursor.close()

    @gen_test(timeout=10)
    def test_find_one_is_async(self):
        # Confirm find_one() is async by launching two operations which will
        # finish out of order.
        # Launch 2 find_one operations for _id's 1 and 2, which will finish in
        # order 2 then 1.
        coll = self.collection
        yield coll.insert([{'_id': 1}, {'_id': 2}])
        results = []

        futures = [Future(), Future()]

        def callback(result, error):
            if result:
                results.append(result)
                futures.pop().set_result(None)

        # This find_one() takes 3 seconds.
        coll.find_one({'_id': 1, '$where': delay(3)}, callback=callback)

        # Very fast lookup.
        coll.find_one({'_id': 2}, callback=callback)

        yield futures

        # Results were appended in order 2, 1.
        self.assertEqual([{'_id': 2}, {'_id': 1}], results)

    @gen_test
    def test_update(self):
        yield self.collection.insert({'_id': 1})
        result = yield self.collection.update(
            {'_id': 1}, {'$set': {'foo': 'bar'}})

        self.assertEqual(1, result['ok'])
        self.assertEqual(True, result['updatedExisting'])
        self.assertEqual(1, result['n'])
        self.assertEqual(None, result.get('err'))

    @gen_test
    def test_update_bad(self):
        # Violate a unique index, make sure we handle error well
        coll = self.db.unique_collection
        yield coll.ensure_index('s', unique=True)

        try:
            yield coll.insert([{'s': 1}, {'s': 2}])
            with assert_raises(DuplicateKeyError):
                yield coll.update({'s': 2}, {'$set': {'s': 1}})

        finally:
            yield coll.drop()

    @gen_test
    def test_update_callback(self):
        yield self.check_optional_callback(
            self.collection.update, {}, {})

    @gen_test
    def test_insert(self):
        collection = self.collection
        self.assertEqual(201, (yield collection.insert({'_id': 201})))

    @gen_test
    def test_insert_many_one_bad(self):
        collection = self.collection
        yield collection.insert({'_id': 2})

        # Violate a unique index in one of many updates, handle error.
        with assert_raises(DuplicateKeyError):
            yield collection.insert([
                {'_id': 1},
                {'_id': 2},  # Already exists
                {'_id': 3}])

        # First insert should have succeeded, but not second or third.
        self.assertEqual(
            set([1, 2]),
            set((yield collection.distinct('_id'))))

    @gen_test
    def test_save_callback(self):
        yield self.check_optional_callback(
            self.collection.save, {})

    @gen_test
    def test_save_with_id(self):
        # save() returns the _id, in this case 5.
        self.assertEqual(
            5,
            (yield self.collection.save({'_id': 5})))

    @gen_test
    def test_save_without_id(self):
        collection = self.collection
        result = yield collection.save({'fiddle': 'faddle'})

        # save() returns the new _id
        self.assertTrue(isinstance(result, ObjectId))

    @gen_test
    def test_save_bad(self):
        coll = self.db.unique_collection
        yield coll.ensure_index('s', unique=True)
        yield coll.save({'s': 1})

        try:
            with assert_raises(DuplicateKeyError):
                yield coll.save({'s': 1})
        finally:
            yield coll.drop()

    @gen_test
    def test_remove(self):
        # Remove a document twice, check that we get a success response first
        # time and an error the second time.
        yield self.collection.insert({'_id': 1})
        result = yield self.collection.remove({'_id': 1})

        # First time we remove, n = 1
        self.assertEqual(1, result['n'])
        self.assertEqual(1, result['ok'])
        self.assertEqual(None, result.get('err'))

        result = yield self.collection.remove({'_id': 1})

        # Second time, document is already gone, n = 0
        self.assertEqual(0, result['n'])
        self.assertEqual(1, result['ok'])
        self.assertEqual(None, result.get('err'))

    @gen_test
    def test_remove_callback(self):
        yield self.check_optional_callback(self.collection.remove)

    @gen_test
    def test_unacknowledged_remove(self):
        coll = self.collection
        yield coll.remove()
        yield coll.insert([{'_id': i} for i in range(3)])

        # Don't yield the futures.
        coll.remove({'_id': 0})
        coll.remove({'_id': 1})
        coll.remove({'_id': 2})

        # Wait for them to complete
        while (yield coll.count()):
            yield self.pause(0.1)

        coll.database.connection.close()

    @gen_test
    def test_unacknowledged_insert(self):
        # Test that unsafe inserts with no callback still work

        # Insert id 1 without a callback or w=1.
        coll = self.db.test_unacknowledged_insert
        coll.insert({'_id': 1})

        # The insert is eventually executed.
        while not (yield coll.count()):
            yield self.pause(0.1)

        # DuplicateKeyError not raised.
        future = coll.insert({'_id': 1})
        yield coll.insert({'_id': 1}, w=0)

        with assert_raises(DuplicateKeyError):
            yield future

    @gen_test
    def test_unacknowledged_save(self):
        # Test that unsafe saves with no callback still work
        collection_name = 'test_unacknowledged_save'
        coll = self.db[collection_name]
        coll.save({'_id': 201})

        while not test.sync_db[collection_name].find({'_id': 201}).count():
            yield self.pause(0.1)

        # DuplicateKeyError not raised
        coll.save({'_id': 201})
        yield coll.save({'_id': 201}, w=0)
        coll.database.connection.close()

    @gen_test
    def test_unacknowledged_update(self):
        # Test that unsafe updates with no callback still work
        coll = self.collection
        yield coll.insert({'_id': 1})
        coll.update({'_id': 1}, {'$set': {'a': 1}})

        while not test.sync_db.test_collection.find({'a': 1}).count():
            yield self.pause(0.1)

        coll.database.connection.close()

    @gen_test
    def test_nested_callbacks(self):
        results = [0]
        future = Future()
        yield self.collection.insert({'_id': 1})

        def callback(result, error):
            if error:
                raise error

            if not result:
                # Done iterating
                return

            results[0] += 1
            if results[0] < 1000:
                self.collection.find({'_id': 1}).each(callback)
            else:
                future.set_result(None)

        self.collection.find({'_id': 1}).each(callback)

        yield future
        self.assertEqual(1000, results[0])

    @gen_test
    def test_map_reduce(self):
        # Count number of documents with even and odd _id
        yield self.make_test_data()
        expected_result = [{'_id': 0, 'value': 100}, {'_id': 1, 'value': 100}]
        map_fn = bson.Code('function map() { emit(this._id % 2, 1); }')
        reduce_fn = bson.Code('''
        function reduce(key, values) {
            r = 0;
            values.forEach(function(value) { r += value; });
            return r;
        }''')

        yield self.db.tmp_mr.drop()

        # First do a standard mapreduce, should return MotorCollection
        collection = self.collection
        tmp_mr = yield collection.map_reduce(map_fn, reduce_fn, 'tmp_mr')

        self.assertTrue(
            isinstance(tmp_mr, motor.MotorCollection),
            'map_reduce should return MotorCollection, not %s' % tmp_mr)

        result = yield tmp_mr.find().sort([('_id', 1)]).to_list(length=1000)
        self.assertEqual(expected_result, result)

        # Standard mapreduce with full response
        yield self.db.tmp_mr.drop()
        response = yield collection.map_reduce(
            map_fn, reduce_fn, 'tmp_mr', full_response=True)

        self.assertTrue(
            isinstance(response, dict),
            'map_reduce should return dict, not %s' % response)

        self.assertEqual('tmp_mr', response['result'])
        result = yield tmp_mr.find().sort([('_id', 1)]).to_list(length=1000)
        self.assertEqual(expected_result, result)

        # Inline mapreduce
        yield self.db.tmp_mr.drop()
        result = yield collection.inline_map_reduce(
            map_fn, reduce_fn)

        result.sort(key=lambda doc: doc['_id'])
        self.assertEqual(expected_result, result)

    @gen_test
    def test_indexes(self):
        test_collection = self.collection

        # Create an index
        idx_name = yield test_collection.create_index([('foo', 1)])
        index_info = yield test_collection.index_information()
        self.assertEqual([('foo', 1)], index_info[idx_name]['key'])

        # Ensure the same index, test that callback is executed
        result = yield test_collection.ensure_index([('foo', 1)])
        self.assertEqual(None, result)
        result2 = yield test_collection.ensure_index([('foo', 1)])
        self.assertEqual(None, result2)

        # Ensure an index that doesn't exist, test it's created
        yield test_collection.ensure_index([('bar', 1)])
        index_info = yield test_collection.index_information()
        self.assertTrue(any([
            info['key'] == [('bar', 1)] for info in index_info.values()]))

        # Don't test drop_index or drop_indexes -- Synchro tests them

    @gen_test
    def test_aggregation_cursor(self):
        if not (yield version.at_least(self.cx, (2, 5, 1))):
            raise SkipTest("Aggregation cursor requires MongoDB >= 2.5.1")

        db = self.db

        # A small collection which returns only an initial batch,
        # and a larger one that requires a getMore.
        for collection_size in (10, 1000):
            yield db.drop_collection("test")
            yield db.test.insert([{'_id': i} for i in range(collection_size)])
            expected_sum = sum(range(collection_size))
            cursor = yield db.test.aggregate(
                {'$project': {'_id': '$_id'}}, cursor={})

            docs = yield cursor.to_list(collection_size)
            self.assertEqual(
                expected_sum,
                sum(doc['_id'] for doc in docs))

    @gen_test(timeout=30)
    def test_parallel_scan(self):
        if not (yield version.at_least(self.cx, (2, 5, 5))):
            raise SkipTest("Requires MongoDB >= 2.5.5")

        yield skip_if_mongos(self.cx)

        collection = self.collection

        # Enough documents that each cursor requires multiple batches.
        yield collection.remove()
        yield collection.insert(({'_id': i} for i in range(8000)), w=test.w)
        if test.is_replica_set:
            client = motor.MotorReplicaSetClient(
                '%s:%s' % (test.host, test.port),
                io_loop=self.io_loop,
                replicaSet=test.rs_name)

            # Test that getMore messages are sent to the right server.
            client.read_preference = ReadPreference.SECONDARY

            collection = client.motor_test.test_collection

        docs = []

        @gen.coroutine
        def f(cursor):
            self.assertTrue(isinstance(cursor, motor.MotorCommandCursor))

            while (yield cursor.fetch_next):
                docs.append(cursor.next_object())

        cursors = yield collection.parallel_scan(3)
        yield [f(cursor) for cursor in cursors]
        self.assertEqual(len(docs), (yield collection.count()))

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_motor_cursor
# Copyright 2012-2014 MongoDB, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import unicode_literals

"""Test Motor, an asynchronous driver for MongoDB and Tornado."""

import datetime
import sys
import unittest
from functools import partial

import greenlet
import pymongo
from tornado import gen
from pymongo.errors import InvalidOperation, ExecutionTimeout
from pymongo.errors import OperationFailure
from tornado.concurrent import Future
from tornado.testing import gen_test

import motor
import test
from test import MotorTest, assert_raises, host, port, setUpModule, SkipTest
from test.utils import server_is_mongos, version, get_command_line


class MotorCursorTest(MotorTest):
    def test_cursor(self):
        cursor = self.collection.find()
        self.assertTrue(isinstance(cursor, motor.MotorCursor))
        self.assertFalse(cursor.started, "Cursor shouldn't start immediately")

    @gen_test
    def test_count_callback(self):
        yield self.check_optional_callback(self.collection.find().count)

    @gen_test
    def test_count(self):
        yield self.make_test_data()
        coll = self.collection
        self.assertEqual(200, (yield coll.find().count()))
        self.assertEqual(100, (yield coll.find({'_id': {'$gt': 99}}).count()))
        where = 'this._id % 2 == 0 && this._id >= 50'
        self.assertEqual(75, (yield coll.find({'$where': where}).count()))
        self.assertEqual(75, (yield coll.find().where(where).count()))
        self.assertEqual(
            25,
            (yield coll.find({'_id': {'$lt': 100}}).where(where).count()))

        self.assertEqual(
            25,
            (yield coll.find({'_id': {'$lt': 100}, '$where': where}).count()))

    @gen_test
    def test_fetch_next(self):
        yield self.make_test_data()
        coll = self.collection
        # 200 results, only including _id field, sorted by _id
        cursor = coll.find({}, {'_id': 1}).sort(
            [('_id', pymongo.ASCENDING)]).batch_size(75)

        self.assertEqual(None, cursor.cursor_id)
        self.assertEqual(None, cursor.next_object())  # Haven't fetched yet
        i = 0
        while (yield cursor.fetch_next):
            self.assertEqual({'_id': i}, cursor.next_object())
            i += 1
            # With batch_size 75 and 200 results, cursor should be exhausted on
            # the server by third fetch
            if i <= 150:
                self.assertNotEqual(0, cursor.cursor_id)
            else:
                self.assertEqual(0, cursor.cursor_id)

        self.assertEqual(False, (yield cursor.fetch_next))
        self.assertEqual(None, cursor.next_object())
        self.assertEqual(0, cursor.cursor_id)
        self.assertEqual(200, i)

    @gen_test
    def test_fetch_next_delete(self):
        coll = self.collection
        yield coll.insert({})

        # Decref'ing the cursor eventually closes it on the server; yielding
        # clears the engine Runner's reference to the cursor.
        cursor = coll.find()
        yield cursor.fetch_next
        cursor_id = cursor.cursor_id
        retrieved = cursor.delegate._Cursor__retrieved
        del cursor
        yield gen.Task(self.io_loop.add_callback)
        yield self.wait_for_cursor(coll, cursor_id, retrieved)

    @gen_test
    def test_fetch_next_without_results(self):
        coll = self.collection
        # Nothing matches this query
        cursor = coll.find({'foo': 'bar'})
        self.assertEqual(None, cursor.next_object())
        self.assertEqual(False, (yield cursor.fetch_next))
        self.assertEqual(None, cursor.next_object())
        # Now cursor knows it's exhausted
        self.assertEqual(0, cursor.cursor_id)

    @gen_test
    def test_fetch_next_is_idempotent(self):
        # Subsequent calls to fetch_next don't do anything
        yield self.make_test_data()
        coll = self.collection
        cursor = coll.find()
        self.assertEqual(None, cursor.cursor_id)
        yield cursor.fetch_next
        self.assertTrue(cursor.cursor_id)
        self.assertEqual(101, cursor._buffer_size())
        yield cursor.fetch_next  # Does nothing
        self.assertEqual(101, cursor._buffer_size())

    @gen_test
    def test_fetch_next_exception(self):
        coll = self.collection
        cursor = coll.find()
        cursor.delegate._Cursor__id = 1234  # Not valid on server

        with assert_raises(OperationFailure):
            yield cursor.fetch_next

        # Avoid the cursor trying to close itself when it goes out of scope
        cursor.delegate._Cursor__id = None

    @gen_test
    def test_each_callback(self):
        cursor = self.collection.find()
        self.assertRaises(TypeError, cursor.each, callback='foo')
        self.assertRaises(TypeError, cursor.each, callback=None)
        self.assertRaises(TypeError, cursor.each)  # No callback.

        # Should not raise
        (result, error), _ = yield gen.Task(cursor.each)
        if error:
            raise error

    @gen_test
    def test_each(self):
        yield self.make_test_data()
        cursor = self.collection.find({}, {'_id': 1})
        cursor.sort([('_id', pymongo.ASCENDING)])
        future = Future()
        results = []

        def callback(result, error):
            if error:
                raise error

            if result is not None:
                results.append(result)
            else:
                # Done iterating.
                future.set_result(True)

        cursor.each(callback)
        yield future
        expected = [{'_id': i} for i in range(200)]
        self.assertEqual(expected, results)

    @gen_test
    def test_to_list_argument_checking(self):
        # We need more than 10 documents so the cursor stays alive.
        yield self.make_test_data()
        coll = self.collection
        cursor = coll.find()
        yield self.check_optional_callback(cursor.to_list, 10)
        cursor = coll.find()
        with assert_raises(ValueError):
            yield cursor.to_list(-1)

        with assert_raises(TypeError):
            yield cursor.to_list('foo')

    @gen_test
    def test_to_list_callback(self):
        yield self.make_test_data()
        cursor = self.collection.find({}, {'_id': 1})
        cursor.sort([('_id', pymongo.ASCENDING)])
        expected = [{'_id': i} for i in range(200)]
        (result, error), _ = yield gen.Task(cursor.to_list, length=1000)
        self.assertEqual(expected, result)

        cursor = self.collection.find().where('return foo')
        (result, error), _ = yield gen.Task(cursor.to_list, length=1000)
        self.assertEqual(None, result)
        self.assertTrue(isinstance(error, OperationFailure))

    @gen_test
    def test_to_list_with_length(self):
        yield self.make_test_data()
        coll = self.collection
        cursor = coll.find().sort('_id')
        self.assertEqual([], (yield cursor.to_list(0)))

        def expected(start, stop):
            return [{'_id': i} for i in range(start, stop)]

        self.assertEqual(expected(0, 10), (yield cursor.to_list(10)))
        self.assertEqual(expected(10, 100), (yield cursor.to_list(90)))

        # Test particularly rigorously around the 101-doc mark, since this is
        # where the first batch ends
        self.assertEqual(expected(100, 101), (yield cursor.to_list(1)))
        self.assertEqual(expected(101, 102), (yield cursor.to_list(1)))
        self.assertEqual(expected(102, 103), (yield cursor.to_list(1)))
        self.assertEqual([], (yield cursor.to_list(0)))
        self.assertEqual(expected(103, 105), (yield cursor.to_list(2)))

        # Only 95 docs left, make sure length=100 doesn't error or hang
        self.assertEqual(expected(105, 200), (yield cursor.to_list(100)))
        self.assertEqual(0, cursor.cursor_id)

    @gen_test
    def test_to_list_with_length_of_none(self):
        yield self.make_test_data()
        collection = self.collection
        cursor = collection.find()
        docs = yield cursor.to_list(None)  # Unlimited.
        count = yield collection.count()
        self.assertEqual(count, len(docs))

    def test_to_list_tailable(self):
        coll = self.collection
        cursor = coll.find(tailable=True)

        # Can't call to_list on tailable cursor.
        with assert_raises(InvalidOperation):
            yield cursor.to_list(10)

    @gen_test
    def test_limit_zero(self):
        # Limit of 0 is a weird case that PyMongo handles specially, make sure
        # Motor does too. cursor.limit(0) means "remove limit", but cursor[:0]
        # or cursor[5:5] sets the cursor to "empty".
        coll = self.collection
        yield coll.insert({'_id': 1})

        self.assertEqual(False, (yield coll.find()[:0].fetch_next))
        self.assertEqual(False, (yield coll.find()[5:5].fetch_next))

        # each() with limit 0 runs its callback once with args (None, None).
        (result, error), _ = yield gen.Task(coll.find()[:0].each)
        self.assertEqual((None, None), (result, error))
        (result, error), _ = yield gen.Task(coll.find()[:0].each)
        self.assertEqual((None, None), (result, error))

        self.assertEqual([], (yield coll.find()[:0].to_list(length=1000)))
        self.assertEqual([], (yield coll.find()[5:5].to_list(length=1000)))

    @gen_test
    def test_cursor_explicit_close(self):
        yield self.make_test_data()
        collection = self.collection
        yield self.check_optional_callback(collection.find().close)
        cursor = collection.find()
        yield cursor.fetch_next
        self.assertTrue(cursor.alive)
        yield cursor.close()

        # Cursor reports it's alive because it has buffered data, even though
        # it's killed on the server
        self.assertTrue(cursor.alive)
        retrieved = cursor.delegate._Cursor__retrieved
        yield self.wait_for_cursor(collection, cursor.cursor_id, retrieved)

    @gen_test
    def test_each_cancel(self):
        yield self.make_test_data()
        loop = self.io_loop
        collection = self.collection
        results = []
        future = Future()

        def cancel(result, error):
            if error:
                future.set_exception(error)

            else:
                results.append(result)
                loop.add_callback(canceled)
                return False  # Cancel iteration.

        def canceled():
            try:
                self.assertFalse(cursor.delegate._Cursor__killed)
                self.assertTrue(cursor.alive)

                # Resume iteration
                cursor.each(each)
            except Exception as e:
                future.set_exception(e)

        def each(result, error):
            if error:
                future.set_exception(error)
            elif result:
                pass
                results.append(result)
            else:
                # Complete
                future.set_result(None)

        cursor = collection.find()
        cursor.each(cancel)
        yield future
        self.assertEqual(test.sync_collection.count(), len(results))

    @gen_test
    def test_each_close(self):
        yield self.make_test_data()  # 200 documents.
        loop = self.io_loop
        collection = self.collection
        results = []
        future = Future()

        def callback(result, error):
            if error:
                future.set_exception(error)

            else:
                results.append(result)
                if len(results) == 50:
                    # Prevent further calls.
                    cursor.close()

                    # Soon, finish this test. Leave a little time for further
                    # calls to ensure we've really canceled them by calling
                    # cursor.close().
                    # future.set_result(None)
                    loop.add_timeout(
                        datetime.timedelta(milliseconds=10),
                        partial(future.set_result, None))

        cursor = collection.find()
        cursor.each(callback)
        yield future
        self.assertEqual(50, len(results))

    def test_cursor_slice_argument_checking(self):
        collection = self.collection

        for arg in '', None, {}, []:
            self.assertRaises(TypeError, lambda: collection.find()[arg])

        self.assertRaises(IndexError, lambda: collection.find()[-1])

    @gen_test
    def test_cursor_slice(self):
        # This is an asynchronous copy of PyMongo's test_getitem_slice_index in
        # test_cursor.py
        yield self.make_test_data()
        coll = self.collection

        self.assertRaises(IndexError, lambda: coll.find()[-1])
        self.assertRaises(IndexError, lambda: coll.find()[1:2:2])
        self.assertRaises(IndexError, lambda: coll.find()[2:1])

        result = yield coll.find()[0:].to_list(length=1000)
        self.assertEqual(200, len(result))

        result = yield coll.find()[20:].to_list(length=1000)
        self.assertEqual(180, len(result))

        result = yield coll.find()[99:].to_list(length=1000)
        self.assertEqual(101, len(result))

        result = yield coll.find()[1000:].to_list(length=1000)
        self.assertEqual(0, len(result))

        result = yield coll.find()[20:25].to_list(length=1000)
        self.assertEqual(5, len(result))

        # Any slice overrides all previous slices
        result = yield coll.find()[20:25][20:].to_list(length=1000)
        self.assertEqual(180, len(result))

        result = yield coll.find()[20:25].limit(0).skip(20).to_list(length=1000)
        self.assertEqual(180, len(result))

        result = yield coll.find().limit(0).skip(20)[20:25].to_list(length=1000)
        self.assertEqual(5, len(result))

        result = yield coll.find()[:1].to_list(length=1000)
        self.assertEqual(1, len(result))

        result = yield coll.find()[:5].to_list(length=1000)
        self.assertEqual(5, len(result))

    @gen_test(timeout=30)
    def test_cursor_index(self):
        yield self.make_test_data()
        coll = self.collection
        cursor = coll.find().sort([('_id', 1)])[0]
        yield cursor.fetch_next
        self.assertEqual({'_id': 0}, cursor.next_object())

        self.assertEqual(
            [{'_id': 5}],
            (yield coll.find().sort([('_id', 1)])[5].to_list(100)))

        # Only 200 documents, so 1000th doc doesn't exist. PyMongo raises
        # IndexError here, but Motor simply returns None.
        cursor = coll.find()[1000]
        self.assertFalse((yield cursor.fetch_next))
        self.assertEqual(None, cursor.next_object())
        self.assertEqual([], (yield coll.find()[1000].to_list(100)))

    @gen_test
    def test_cursor_index_each(self):
        yield self.make_test_data()
        coll = self.collection

        results = set()
        futures = [Future() for _ in range(3)]

        def each(result, error):
            if error:
                raise error

            if result:
                results.add(result['_id'])
            else:
                futures.pop().set_result(None)

        coll.find({}, {'_id': 1}).sort([('_id', 1)])[0].each(each)
        coll.find({}, {'_id': 1}).sort([('_id', 1)])[5].each(each)

        # Only 200 documents, so 1000th doc doesn't exist. PyMongo raises
        # IndexError here, but Motor simply returns None, which won't show up
        # in results.
        coll.find()[1000].each(each)

        yield futures
        self.assertEqual(set([0, 5]), results)

    @gen_test
    def test_rewind(self):
        yield self.collection.insert([{}, {}, {}])
        cursor = self.collection.find().limit(2)

        count = 0
        while (yield cursor.fetch_next):
            cursor.next_object()
            count += 1
        self.assertEqual(2, count)

        cursor.rewind()
        count = 0
        while (yield cursor.fetch_next):
            cursor.next_object()
            count += 1
        self.assertEqual(2, count)

        cursor.rewind()
        count = 0
        while (yield cursor.fetch_next):
            cursor.next_object()
            break

        cursor.rewind()
        while (yield cursor.fetch_next):
            cursor.next_object()
            count += 1

        self.assertEqual(2, count)
        self.assertEqual(cursor, cursor.rewind())

    @gen_test
    def test_del_on_main_greenlet(self):
        # Since __del__ can happen on any greenlet, MotorCursor must be
        # prepared to close itself correctly on main or a child.
        yield self.make_test_data()
        collection = self.collection
        cursor = collection.find()
        yield cursor.fetch_next
        cursor_id = cursor.cursor_id
        retrieved = cursor.delegate._Cursor__retrieved

        # Clear the FetchNext reference from this gen.Runner so it's deleted
        # and decrefs the cursor
        yield gen.Task(self.io_loop.add_callback)
        del cursor
        yield self.wait_for_cursor(collection, cursor_id, retrieved)

    @gen_test
    def test_del_on_child_greenlet(self):
        # Since __del__ can happen on any greenlet, MotorCursor must be
        # prepared to close itself correctly on main or a child.
        yield self.make_test_data()
        collection = self.collection
        cursor = [collection.find()]
        yield cursor[0].fetch_next
        cursor_id = cursor[0].cursor_id
        retrieved = cursor[0].delegate._Cursor__retrieved

        # Clear the FetchNext reference from this gen.Runner so it's deleted
        # and decrefs the cursor
        yield gen.Task(self.io_loop.add_callback)

        def f():
            # Last ref, should trigger __del__ immediately in CPython and
            # allow eventual __del__ in PyPy.
            del cursor[0]

        greenlet.greenlet(f).switch()
        yield self.wait_for_cursor(collection, cursor_id, retrieved)

    @gen_test
    def test_exhaust(self):
        if (yield server_is_mongos(self.cx)):
            self.assertRaises(InvalidOperation,
                              self.db.test.find, exhaust=True)
            return

        self.assertRaises(TypeError, self.db.test.find, exhaust=5)

        cur = self.db.test.find(exhaust=True)
        self.assertRaises(InvalidOperation, cur.limit, 5)
        cur = self.db.test.find(limit=5)
        self.assertRaises(InvalidOperation, cur.add_option, 64)
        cur = self.db.test.find()
        cur.add_option(64)
        self.assertRaises(InvalidOperation, cur.limit, 5)

        yield self.db.drop_collection("test")

        # Insert enough documents to require more than one batch.
        yield self.db.test.insert([{} for _ in range(150)])

        client = motor.MotorClient(host, port, max_pool_size=1)
        # Ensure a pool.
        yield client.db.collection.find_one()
        socks = client._get_primary_pool().sockets

        # Make sure the socket is returned after exhaustion.
        cur = client[self.db.name].test.find(exhaust=True)
        has_next = yield cur.fetch_next
        self.assertTrue(has_next)
        self.assertEqual(0, len(socks))

        while (yield cur.fetch_next):
            cur.next_object()

        self.assertEqual(1, len(socks))

        # Same as previous but with to_list instead of next_object.
        docs = yield client[self.db.name].test.find(exhaust=True).to_list(None)
        self.assertEqual(1, len(socks))
        self.assertEqual(
            (yield self.db.test.count()),
            len(docs))

        # If the Cursor instance is discarded before being
        # completely iterated we have to close and
        # discard the socket.
        cur = client[self.db.name].test.find(exhaust=True)
        has_next = yield cur.fetch_next
        self.assertTrue(has_next)
        self.assertEqual(0, len(socks))
        if 'PyPy' in sys.version:
            # Don't wait for GC or use gc.collect(), it's unreliable.
            cur.close()
        cur = None
        # The socket should be discarded.
        self.assertEqual(0, len(socks))


class MotorCursorMaxTimeMSTest(MotorTest):
    def setUp(self):
        super(MotorCursorMaxTimeMSTest, self).setUp()
        self.io_loop.run_sync(self.maybe_skip)

    def tearDown(self):
        self.io_loop.run_sync(self.disable_timeout)
        super(MotorCursorMaxTimeMSTest, self).tearDown()

    @gen.coroutine
    def maybe_skip(self):
        if not (yield version.at_least(self.cx, (2, 5, 3, -1))):
            raise SkipTest("maxTimeMS requires MongoDB >= 2.5.3")

        if "enableTestCommands=1" not in (yield get_command_line(self.cx)):
            raise SkipTest("testing maxTimeMS requires failpoints")

    @gen.coroutine
    def enable_timeout(self):
        yield self.cx.admin.command("configureFailPoint",
                                    "maxTimeAlwaysTimeOut",
                                    mode="alwaysOn")

    @gen.coroutine
    def disable_timeout(self):
        self.cx.admin.command("configureFailPoint",
                              "maxTimeAlwaysTimeOut",
                              mode="off")

    @gen_test
    def test_max_time_ms_query(self):
        # Cursor parses server timeout error in response to initial query.
        yield self.enable_timeout()
        cursor = self.collection.find().max_time_ms(1000)
        with assert_raises(ExecutionTimeout):
            yield cursor.fetch_next

        cursor = self.collection.find().max_time_ms(1000)
        with assert_raises(ExecutionTimeout):
            yield cursor.to_list(10)

        with assert_raises(ExecutionTimeout):
            yield self.collection.find_one(max_time_ms=1000)

    @gen_test(timeout=30)
    def test_max_time_ms_getmore(self):
        # Cursor handles server timeout during getmore, also.
        yield self.collection.insert({} for _ in range(200))
        try:
            # Send initial query.
            cursor = self.collection.find().max_time_ms(1000)
            yield cursor.fetch_next
            cursor.next_object()

            # Test getmore timeout.
            yield self.enable_timeout()
            with assert_raises(ExecutionTimeout):
                while (yield cursor.fetch_next):
                    cursor.next_object()

            # Send another initial query.
            yield self.disable_timeout()
            cursor = self.collection.find().max_time_ms(1000)
            yield cursor.fetch_next
            cursor.next_object()

            # Test getmore timeout.
            yield self.enable_timeout()
            with assert_raises(ExecutionTimeout):
                yield cursor.to_list(None)

            # Avoid 'IOLoop is closing' warning.
            yield cursor.close()
        finally:
            # Cleanup.
            yield self.disable_timeout()
            yield self.collection.remove()

    @gen_test
    def test_max_time_ms_each_query(self):
        # Cursor.each() handles server timeout during initial query.
        yield self.enable_timeout()
        cursor = self.collection.find().max_time_ms(1000)
        future = Future()

        def callback(result, error):
            if error:
                future.set_exception(error)
            elif not result:
                # Done.
                future.set_result(None)

        with assert_raises(ExecutionTimeout):
            cursor.each(callback)
            yield future

    @gen_test(timeout=30)
    def test_max_time_ms_each_getmore(self):
        # Cursor.each() handles server timeout during getmore.
        yield self.collection.insert({} for _ in range(200))
        try:
            # Send initial query.
            cursor = self.collection.find().max_time_ms(1000)
            yield cursor.fetch_next
            cursor.next_object()

            future = Future()

            def callback(result, error):
                if error:
                    future.set_exception(error)
                elif not result:
                    # Done.
                    future.set_result(None)

            yield self.enable_timeout()
            with assert_raises(ExecutionTimeout):
                cursor.each(callback)
                yield future
        finally:
            # Cleanup.
            yield self.disable_timeout()
            yield self.collection.remove()


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_motor_database
# Copyright 2012-2014 MongoDB, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import unicode_literals

"""Test Motor, an asynchronous driver for MongoDB and Tornado."""

import unittest

import pymongo.database
from pymongo.errors import OperationFailure, CollectionInvalid
from pymongo.son_manipulator import AutoReference, NamespaceInjector
from tornado.testing import gen_test

import motor
import test
from test import version, MotorTest, assert_raises, setUpModule
from test.utils import remove_all_users


class MotorDatabaseTest(MotorTest):
    @gen_test
    def test_database(self):
        # Test that we can create a db directly, not just from MotorClient's
        # accessors
        db = motor.MotorDatabase(self.cx, 'motor_test')

        # Make sure we got the right DB and it can do an operation
        self.assertEqual('motor_test', db.name)
        test.sync_collection.insert({'_id': 1})
        doc = yield db.test_collection.find_one({'_id': 1})
        self.assertEqual(1, doc['_id'])

    def test_collection_named_delegate(self):
        db = self.db
        self.assertTrue(isinstance(db.delegate, pymongo.database.Database))
        self.assertTrue(isinstance(db['delegate'], motor.MotorCollection))
        db.connection.close()

    def test_call(self):
        # Prevents user error with nice message.
        try:
            self.cx.foo()
        except TypeError as e:
            self.assertTrue('no such method exists' in str(e))
        else:
            self.fail('Expected TypeError')

        try:
            # First line of applications written for Motor 0.1.
            self.cx.open_sync()
        except TypeError as e:
            self.assertTrue('unnecessary' in str(e))
        else:
            self.fail('Expected TypeError')

    @gen_test
    def test_database_callbacks(self):
        db = self.db
        yield self.check_optional_callback(db.drop_collection, 'c')

        # check_optional_callback would call create_collection twice, and the
        # second call would raise "already exists", so test manually.
        self.assertRaises(TypeError, db.create_collection, 'c', callback='foo')
        self.assertRaises(TypeError, db.create_collection, 'c', callback=1)
        
        # No error without callback
        db.create_collection('c', callback=None)
        
        # Wait for create_collection to complete
        for _ in range(10):
            yield self.pause(0.5)
            if 'c' in (yield db.collection_names()):
                break

        yield self.check_optional_callback(db.validate_collection, 'c')

    @gen_test
    def test_command(self):
        result = yield self.cx.admin.command("buildinfo")
        self.assertEqual(int, type(result['bits']))

    @gen_test
    def test_create_collection(self):
        # Test creating collection, return val is wrapped in MotorCollection,
        # creating it again raises CollectionInvalid.
        db = self.db
        yield db.drop_collection('test_collection2')
        collection = yield db.create_collection('test_collection2')
        self.assertTrue(isinstance(collection, motor.MotorCollection))
        self.assertTrue(
            'test_collection2' in (yield db.collection_names()))

        with assert_raises(CollectionInvalid):
            yield db.create_collection('test_collection2')

        yield db.drop_collection('test_collection2')

        # Test creating capped collection
        collection = yield db.create_collection(
            'test_capped', capped=True, size=4096)

        self.assertTrue(isinstance(collection, motor.MotorCollection))
        self.assertEqual(
            {"capped": True, 'size': 4096},
            (yield db.test_capped.options()))
        yield db.drop_collection('test_capped')

    @gen_test
    def test_drop_collection(self):
        # Make sure we can pass a MotorCollection instance to drop_collection
        db = self.db
        collection = db.test_drop_collection
        yield collection.insert({})
        names = yield db.collection_names()
        self.assertTrue('test_drop_collection' in names)
        yield db.drop_collection(collection)
        names = yield db.collection_names()
        self.assertFalse('test_drop_collection' in names)

    @gen_test
    def test_command_callback(self):
        yield self.check_optional_callback(
            self.cx.admin.command, 'buildinfo', check=False)

    @gen_test
    def test_auto_ref_and_deref(self):
        # Test same functionality as in PyMongo's test_database.py; the
        # implementation for Motor for async is a little complex so we test
        # that it works here, and we don't just rely on synchrotest
        # to cover it.
        db = self.db

        # We test a special hack where add_son_manipulator corrects our mistake
        # if we pass a MotorDatabase, instead of Database, to AutoReference.
        db.add_son_manipulator(AutoReference(db))
        db.add_son_manipulator(NamespaceInjector())

        a = {"hello": "world"}
        b = {"test": a}
        c = {"another test": b}

        yield db.a.remove({})
        yield db.b.remove({})
        yield db.c.remove({})
        yield db.a.save(a)
        yield db.b.save(b)
        yield db.c.save(c)
        a["hello"] = "mike"
        yield db.a.save(a)
        result_a = yield db.a.find_one()
        result_b = yield db.b.find_one()
        result_c = yield db.c.find_one()

        self.assertEqual(a, result_a)
        self.assertEqual(a, result_b["test"])
        self.assertEqual(a, result_c["another test"]["test"])
        self.assertEqual(b, result_b)
        self.assertEqual(b, result_c["another test"])
        self.assertEqual(c, result_c)

    @gen_test
    def test_authenticate(self):
        db = self.db
        try:
            yield self.cx.admin.add_user("admin", "password")
            yield self.cx.admin.authenticate("admin", "password")
            yield db.add_user("mike", "password")

            # Authenticate many times at once to test concurrency.
            yield [db.authenticate("mike", "password") for _ in range(10)]

            # just make sure there are no exceptions here
            yield db.remove_user("mike")
            yield db.logout()
            if (yield version.at_least(self.cx, (2, 5, 4))):
                info = yield db.command("usersInfo", "mike")
                users = info.get('users', [])
            else:
                users = yield db.system.users.find().to_list(length=10)

            self.assertFalse("mike" in [u['user'] for u in users])

        finally:
            yield remove_all_users(db)
            yield self.cx.admin.remove_user('admin')
            test.sync_cx.disconnect()

    @gen_test
    def test_validate_collection(self):
        db = self.db

        with assert_raises(TypeError):
            yield db.validate_collection(5)
        with assert_raises(TypeError):
            yield db.validate_collection(None)
        with assert_raises(OperationFailure):
            yield db.validate_collection("test.doesnotexist")
        with assert_raises(OperationFailure):
            yield db.validate_collection(db.test.doesnotexist)

        yield db.test.save({"dummy": "object"})
        self.assertTrue((yield db.validate_collection("test")))
        self.assertTrue((yield db.validate_collection(db.test)))


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_motor_gen
# Copyright 2012-2014 MongoDB, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import unicode_literals

"""Test Motor, an asynchronous driver for MongoDB and Tornado."""

import unittest
import warnings

import pymongo.errors
from tornado.testing import gen_test

import motor
import test
from test import MotorTest, assert_raises, setUpModule


class MotorGenTest(MotorTest):
    def tearDown(self):
        test.sync_db.test_collection2.drop()
        super(MotorGenTest, self).tearDown()

    @gen_test
    def test_op(self):
        # motor.Op is deprecated in Motor 0.2, superseded by Tornado 3 Futures.
        # Just make sure it still works.

        collection = self.collection
        doc = {'_id': 'jesse'}

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            # Op works.
            _id = yield motor.Op(collection.insert, doc)
            self.assertEqual('jesse', _id)

            # Raised a DeprecationWarning.
            self.assertEqual(1, len(w))
            warning = w[-1]
            self.assertTrue(issubclass(warning.category, DeprecationWarning))
            message = str(warning.message)
            self.assertTrue("deprecated" in message)
            self.assertTrue("insert" in message)

        result = yield motor.Op(collection.find_one, doc)
        self.assertEqual(doc, result)

        # Make sure it works with no args.
        result = yield motor.Op(collection.find_one)
        self.assertTrue(isinstance(result, dict))

        with assert_raises(pymongo.errors.DuplicateKeyError):
            yield motor.Op(collection.insert, doc)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_motor_greenlet_event
# Copyright 2013-2014 MongoDB, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import unicode_literals

"""Test MotorGreenletEvent."""
import greenlet
from functools import partial

from tornado import testing, gen
from tornado.testing import gen_test

from motor.util import MotorGreenletEvent
from test import setUpModule


class MotorTestEvent(testing.AsyncTestCase):
    @gen.coroutine
    def tick(self):
        # Yield to loop for one iteration.
        yield gen.Task(self.io_loop.add_callback)

    @gen_test
    def test_event_basic(self):
        event = MotorGreenletEvent(self.io_loop)
        self.assertFalse(event.is_set())

        waiter = greenlet.greenlet(event.wait)
        waiter.switch()
        yield self.tick()
        self.assertTrue(waiter)     # Blocked: not finished yet.
        event.set()
        yield self.tick()
        self.assertFalse(waiter)    # Complete.

        self.assertTrue(event.is_set())

    @gen_test
    def test_event_multi(self):
        # Two greenlets are run, FIFO, after being unblocked.
        event = MotorGreenletEvent(self.io_loop)
        order = []

        def wait():
            event.wait()
            order.append(greenlet.getcurrent())

        waiter0 = greenlet.greenlet(wait)
        waiter1 = greenlet.greenlet(wait)
        waiter0.switch()
        waiter1.switch()
        event.set()
        yield self.tick()
        self.assertEqual([waiter0, waiter1], order)

    @gen_test
    def test_event_timeout(self):
        event = MotorGreenletEvent(self.io_loop)
        waiter = greenlet.greenlet(partial(event.wait, timeout_seconds=0))
        waiter.switch()
        yield self.tick()
        self.assertFalse(waiter)  # Unblocked, finished.

########NEW FILE########
__FILENAME__ = test_motor_gridfs
# -*- coding: utf-8 -*-
# Copyright 2012-2014 MongoDB, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import unicode_literals

"""Test GridFS with Motor, an asynchronous driver for MongoDB and Tornado."""

import unittest
from functools import partial
from bson import ObjectId

from gridfs.errors import FileExists, NoFile
from pymongo import MongoClient
from pymongo.errors import AutoReconnect, ConfigurationError
from pymongo.read_preferences import ReadPreference
from tornado import gen
from tornado.testing import gen_test

import motor
import test
from motor.motor_py3_compat import StringIO
from test import host, port, MotorTest, MotorReplicaSetTestBase, assert_raises
from test import setUpModule


class MotorGridfsTest(MotorTest):
    def _reset(self):
        test.sync_db.drop_collection("fs.files")
        test.sync_db.drop_collection("fs.chunks")
        test.sync_db.drop_collection("alt.files")
        test.sync_db.drop_collection("alt.chunks")

    def setUp(self):
        super(MotorGridfsTest, self).setUp()
        self._reset()
        self.fs = motor.MotorGridFS(self.db)

    def tearDown(self):
        self._reset()
        super(MotorGridfsTest, self).tearDown()

    @gen_test
    def test_gridfs(self):
        self.assertRaises(TypeError, motor.MotorGridFS, "foo")
        self.assertRaises(TypeError, motor.MotorGridFS, 5)

    @gen_test
    def test_get_version(self):
        # new_file creates a MotorGridIn.
        gin = yield self.fs.new_file(_id=1, filename='foo', field=0)
        yield gin.write(b'a')
        yield gin.close()

        yield self.fs.put(b'', filename='foo', field=1)
        yield self.fs.put(b'', filename='foo', field=2)

        gout = yield self.fs.get_version('foo')
        self.assertEqual(2, gout.field)
        gout = yield self.fs.get_version('foo', -3)
        self.assertEqual(0, gout.field)

        gout = yield self.fs.get_last_version('foo')
        self.assertEqual(2, gout.field)

    @gen_test
    def test_gridfs_callback(self):
        yield self.check_optional_callback(self.fs.new_file)
        yield self.check_optional_callback(partial(self.fs.put, b'a'))

        yield self.fs.put(b'foo', _id=1, filename='f')
        yield self.check_optional_callback(self.fs.get, 1)
        yield self.check_optional_callback(self.fs.get_version, 'f')
        yield self.check_optional_callback(self.fs.get_last_version, 'f')
        yield self.check_optional_callback(partial(self.fs.delete, 1))
        yield self.check_optional_callback(self.fs.list)
        yield self.check_optional_callback(self.fs.exists)

    @gen_test
    def test_basic(self):
        oid = yield self.fs.put(b"hello world")
        out = yield self.fs.get(oid)
        self.assertEqual(b"hello world", (yield out.read()))
        self.assertEqual(1, (yield self.db.fs.files.count()))
        self.assertEqual(1, (yield self.db.fs.chunks.count()))

        yield self.fs.delete(oid)
        with assert_raises(NoFile):
            yield self.fs.get(oid)

        self.assertEqual(0, (yield self.db.fs.files.count()))
        self.assertEqual(0, (yield self.db.fs.chunks.count()))

        with assert_raises(NoFile):
            yield self.fs.get("foo")
        
        self.assertEqual(
            "foo", (yield self.fs.put(b"hello world", _id="foo")))
        
        gridout = yield self.fs.get("foo")
        self.assertEqual(b"hello world", (yield gridout.read()))

    @gen_test
    def test_list(self):
        self.assertEqual([], (yield self.fs.list()))
        yield self.fs.put(b"hello world")
        self.assertEqual([], (yield self.fs.list()))

        yield self.fs.put(b"", filename="mike")
        yield self.fs.put(b"foo", filename="test")
        yield self.fs.put(b"", filename="hello world")

        self.assertEqual(set(["mike", "test", "hello world"]),
                         set((yield self.fs.list())))

    @gen_test
    def test_alt_collection(self):
        db = self.db
        alt = motor.MotorGridFS(db, 'alt')
        oid = yield alt.put(b"hello world")
        gridout = yield alt.get(oid)
        self.assertEqual(b"hello world", (yield gridout.read()))
        self.assertEqual(1, (yield self.db.alt.files.count()))
        self.assertEqual(1, (yield self.db.alt.chunks.count()))

        yield alt.delete(oid)
        with assert_raises(NoFile):
            yield alt.get(oid)

        self.assertEqual(0, (yield self.db.alt.files.count()))
        self.assertEqual(0, (yield self.db.alt.chunks.count()))

        with assert_raises(NoFile):
            yield alt.get("foo")
        oid = yield alt.put(b"hello world", _id="foo")
        self.assertEqual("foo", oid)
        gridout = yield alt.get("foo")
        self.assertEqual(b"hello world", (yield gridout.read()))

        yield alt.put(b"", filename="mike")
        yield alt.put(b"foo", filename="test")
        yield alt.put(b"", filename="hello world")

        self.assertEqual(set(["mike", "test", "hello world"]),
                         set((yield alt.list())))

    @gen_test
    def test_put_filelike(self):
        oid = yield self.fs.put(StringIO(b"hello world"), chunk_size=1)
        self.assertEqual(11, (yield self.cx.motor_test.fs.chunks.count()))
        gridout = yield self.fs.get(oid)
        self.assertEqual(b"hello world", (yield gridout.read()))

    @gen_test
    def test_put_callback(self):
        (oid, error), _ = yield gen.Task(self.fs.put, b"hello")
        self.assertTrue(isinstance(oid, ObjectId))
        self.assertEqual(None, error)

        (result, error), _ = yield gen.Task(self.fs.put, b"hello", _id=oid)
        self.assertEqual(None, result)
        self.assertTrue(isinstance(error, FileExists))

    @gen_test
    def test_put_duplicate(self):
        oid = yield self.fs.put(b"hello")
        with assert_raises(FileExists):
            yield self.fs.put(b"world", _id=oid)

    @gen_test
    def test_put_kwargs(self):
        # 'w' is not special here.
        oid = yield self.fs.put(b"hello", foo='bar', w=0)
        gridout = yield self.fs.get(oid)
        self.assertEqual('bar', gridout.foo)
        self.assertEqual(0, gridout.w)

    @gen_test
    def test_put_unacknowledged(self):
        client = self.motor_client(w=0)
        fs = motor.MotorGridFS(client.motor_test)
        with assert_raises(ConfigurationError):
            yield fs.put(b"hello")

        client.close()

    @gen_test
    def test_gridfs_find(self):
        yield self.fs.put(b"test2", filename="two")
        yield self.fs.put(b"test2+", filename="two")
        yield self.fs.put(b"test1", filename="one")
        yield self.fs.put(b"test2++", filename="two")
        cursor = self.fs.find().sort("_id", -1).skip(1).limit(2)
        self.assertTrue((yield cursor.fetch_next))
        grid_out = cursor.next_object()
        self.assertTrue(isinstance(grid_out, motor.MotorGridOut))
        self.assertEqual(b"test1", (yield grid_out.read()))

        cursor.rewind()
        self.assertTrue((yield cursor.fetch_next))
        grid_out = cursor.next_object()
        self.assertEqual(b"test1", (yield grid_out.read()))
        self.assertTrue((yield cursor.fetch_next))
        grid_out = cursor.next_object()
        self.assertEqual(b"test2+", (yield grid_out.read()))
        self.assertFalse((yield cursor.fetch_next))
        self.assertEqual(None, cursor.next_object())

        self.assertRaises(TypeError, self.fs.find, {}, {"_id": True})


class TestGridfsReplicaSet(MotorReplicaSetTestBase):
    @gen_test
    def test_gridfs_replica_set(self):
        rsc = yield self.motor_rsc(
            w=test.w, wtimeout=5000,
            read_preference=ReadPreference.SECONDARY)

        fs = motor.MotorGridFS(rsc.motor_test)
        oid = yield fs.put(b'foo')
        gridout = yield fs.get(oid)
        content = yield gridout.read()
        self.assertEqual(b'foo', content)

    @gen_test
    def test_gridfs_secondary(self):
        primary_host, primary_port = test.primary
        primary_client = self.motor_client(primary_host, primary_port)

        secondary_host, secondary_port = test.secondaries[0]
        secondary_client = self.motor_client(
            secondary_host, secondary_port,
            read_preference=ReadPreference.SECONDARY)

        yield primary_client.motor_test.drop_collection("fs.files")
        yield primary_client.motor_test.drop_collection("fs.chunks")

        # Should detect it's connected to secondary and not attempt to
        # create index
        fs = motor.MotorGridFS(secondary_client.motor_test)

        # This won't detect secondary, raises error
        with assert_raises(AutoReconnect):
            yield fs.put(b'foo')

    def tearDown(self):
        c = MongoClient(host, port)
        c.motor_test.drop_collection('fs.files')
        c.motor_test.drop_collection('fs.chunks')


if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_motor_grid_file
# -*- coding: utf-8 -*-
# Copyright 2012-2014 MongoDB, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import unicode_literals

"""Test GridFS with Motor, an asynchronous driver for MongoDB and Tornado."""

import datetime
import unittest
from functools import partial

from bson.objectid import ObjectId
from gridfs.errors import NoFile
from tornado.testing import gen_test
from pymongo.errors import InvalidOperation

import motor
import test
from test import MotorTest, assert_raises, setUpModule


class MotorGridFileTest(MotorTest):
    def _reset(self):
        test.sync_db.drop_collection("fs.files")
        test.sync_db.drop_collection("fs.chunks")
        test.sync_db.drop_collection("alt.files")
        test.sync_db.drop_collection("alt.chunks")

    def setUp(self):
        super(MotorGridFileTest, self).setUp()
        self._reset()

    def tearDown(self):
        self._reset()
        super(MotorGridFileTest, self).tearDown()

    @gen_test
    def test_grid_in_callback(self):
        f = motor.MotorGridIn(self.db.fs, filename="test")
        yield self.check_optional_callback(partial(f.set, 'name', 'value'))
        yield self.check_optional_callback(partial(f.write, b'a'))
        yield self.check_optional_callback(partial(f.writelines, [b'a']))

        self.assertRaises(TypeError, f.close, callback='foo')
        self.assertRaises(TypeError, f.close, callback=1)
        f.close(callback=None)  # No error

    @gen_test
    def test_grid_out_callback(self):
        # Some setup: we need to make a GridOut.
        f = motor.MotorGridIn(self.db.fs, filename="test")
        yield f.close()

        g = motor.MotorGridOut(self.db.fs, f._id)
        yield self.check_optional_callback(g.open)

        g = yield motor.MotorGridOut(self.db.fs, f._id).open()
        yield self.check_optional_callback(g.read)
        yield self.check_optional_callback(g.readline)

    @gen_test
    def test_attributes(self):
        f = motor.MotorGridIn(
            self.db.fs,
            filename="test",
            foo="bar",
            content_type="text")

        yield f.close()

        g = motor.MotorGridOut(self.db.fs, f._id)
        attr_names = (
            '_id',
            'filename',
            'name',
            'name',
            'content_type',
            'length',
            'chunk_size',
            'upload_date',
            'aliases',
            'metadata',
            'md5')

        for attr_name in attr_names:
            self.assertRaises(InvalidOperation, getattr, g, attr_name)

        yield g.open()
        for attr_name in attr_names:
            getattr(g, attr_name)

    @gen_test
    def test_iteration(self):
        fs = motor.MotorGridFS(self.db)
        _id = yield fs.put(b'foo')
        g = motor.MotorGridOut(self.db.fs, _id)

        # Iteration is prohibited.
        self.assertRaises(TypeError, iter, g)

    @gen_test
    def test_basic(self):
        f = motor.MotorGridIn(self.db.fs, filename="test")
        yield f.write(b"hello world")
        yield f.close()
        self.assertEqual(1, (yield self.db.fs.files.find().count()))
        self.assertEqual(1, (yield self.db.fs.chunks.find().count()))

        g = motor.MotorGridOut(self.db.fs, f._id)
        self.assertEqual(b"hello world", (yield g.read()))

        f = motor.MotorGridIn(self.db.fs, filename="test")
        yield f.close()
        self.assertEqual(2, (yield self.db.fs.files.find().count()))
        self.assertEqual(1, (yield self.db.fs.chunks.find().count()))

        g = motor.MotorGridOut(self.db.fs, f._id)
        self.assertEqual(b"", (yield g.read()))

    @gen_test
    def test_readchunk(self):
        in_data = b'a' * 10
        f = motor.MotorGridIn(self.db.fs, chunkSize=3)
        yield f.write(in_data)
        yield f.close()

        g = motor.MotorGridOut(self.db.fs, f._id)

        # This is starting to look like Lisp.
        self.assertEqual(3, len((yield g.readchunk())))

        self.assertEqual(2, len((yield g.read(2))))
        self.assertEqual(1, len((yield g.readchunk())))

        self.assertEqual(3, len((yield g.read(3))))

        self.assertEqual(1, len((yield g.readchunk())))

        self.assertEqual(0, len((yield g.readchunk())))

    @gen_test
    def test_alternate_collection(self):
        yield self.db.alt.files.remove()
        yield self.db.alt.chunks.remove()

        f = motor.MotorGridIn(self.db.alt)
        yield f.write(b"hello world")
        yield f.close()

        self.assertEqual(1, (yield self.db.alt.files.find().count()))
        self.assertEqual(1, (yield self.db.alt.chunks.find().count()))

        g = motor.MotorGridOut(self.db.alt, f._id)
        self.assertEqual(b"hello world", (yield g.read()))

        # test that md5 still works...
        self.assertEqual("5eb63bbbe01eeed093cb22bb8f5acdc3", g.md5)

    @gen_test
    def test_grid_in_default_opts(self):
        self.assertRaises(TypeError, motor.MotorGridIn, "foo")

        a = motor.MotorGridIn(self.db.fs)

        self.assertTrue(isinstance(a._id, ObjectId))
        self.assertRaises(AttributeError, setattr, a, "_id", 5)

        self.assertEqual(None, a.filename)

        # This raises AttributeError because you can't directly set properties
        # in Motor, have to use set()
        def setter():
            a.filename = "my_file"
        self.assertRaises(AttributeError, setter)

        # This method of setting attributes works in Motor
        yield a.set("filename", "my_file")
        self.assertEqual("my_file", a.filename)

        self.assertEqual(None, a.content_type)
        yield a.set("content_type", "text/html")
        self.assertEqual("text/html", a.content_type)

        self.assertRaises(AttributeError, getattr, a, "length")
        self.assertRaises(AttributeError, setattr, a, "length", 5)

        self.assertEqual(255 * 1024, a.chunk_size)
        self.assertRaises(AttributeError, setattr, a, "chunk_size", 5)

        self.assertRaises(AttributeError, getattr, a, "upload_date")
        self.assertRaises(AttributeError, setattr, a, "upload_date", 5)

        self.assertRaises(AttributeError, getattr, a, "aliases")
        yield a.set("aliases", ["foo"])
        self.assertEqual(["foo"], a.aliases)

        self.assertRaises(AttributeError, getattr, a, "metadata")
        yield a.set("metadata", {"foo": 1})
        self.assertEqual({"foo": 1}, a.metadata)

        self.assertRaises(AttributeError, getattr, a, "md5")
        self.assertRaises(AttributeError, setattr, a, "md5", 5)

        yield a.close()

        self.assertTrue(isinstance(a._id, ObjectId))
        self.assertRaises(AttributeError, setattr, a, "_id", 5)

        self.assertEqual("my_file", a.filename)

        self.assertEqual("text/html", a.content_type)

        self.assertEqual(0, a.length)
        self.assertRaises(AttributeError, setattr, a, "length", 5)

        self.assertEqual(255 * 1024, a.chunk_size)
        self.assertRaises(AttributeError, setattr, a, "chunk_size", 5)

        self.assertTrue(isinstance(a.upload_date, datetime.datetime))
        self.assertRaises(AttributeError, setattr, a, "upload_date", 5)

        self.assertEqual(["foo"], a.aliases)

        self.assertEqual({"foo": 1}, a.metadata)

        self.assertEqual("d41d8cd98f00b204e9800998ecf8427e", a.md5)
        self.assertRaises(AttributeError, setattr, a, "md5", 5)

    @gen_test
    def test_grid_in_custom_opts(self):
        self.assertRaises(TypeError, motor.MotorGridIn, "foo")
        a = motor.MotorGridIn(
            self.db.fs, _id=5, filename="my_file",
            contentType="text/html", chunkSize=1000, aliases=["foo"],
            metadata={"foo": 1, "bar": 2}, bar=3, baz="hello")

        self.assertEqual(5, a._id)
        self.assertEqual("my_file", a.filename)
        self.assertEqual("text/html", a.content_type)
        self.assertEqual(1000, a.chunk_size)
        self.assertEqual(["foo"], a.aliases)
        self.assertEqual({"foo": 1, "bar": 2}, a.metadata)
        self.assertEqual(3, a.bar)
        self.assertEqual("hello", a.baz)
        self.assertRaises(AttributeError, getattr, a, "mike")

        b = motor.MotorGridIn(
            self.db.fs,
            content_type="text/html",
            chunk_size=1000,
            baz=100)

        self.assertEqual("text/html", b.content_type)
        self.assertEqual(1000, b.chunk_size)
        self.assertEqual(100, b.baz)

    @gen_test
    def test_grid_out_default_opts(self):
        self.assertRaises(TypeError, motor.MotorGridOut, "foo")
        gout = motor.MotorGridOut(self.db.fs, 5)
        with assert_raises(NoFile):
            yield gout.open()

        a = motor.MotorGridIn(self.db.fs)
        yield a.close()

        b = yield motor.MotorGridOut(self.db.fs, a._id).open()

        self.assertEqual(a._id, b._id)
        self.assertEqual(0, b.length)
        self.assertEqual(None, b.content_type)
        self.assertEqual(255 * 1024, b.chunk_size)
        self.assertTrue(isinstance(b.upload_date, datetime.datetime))
        self.assertEqual(None, b.aliases)
        self.assertEqual(None, b.metadata)
        self.assertEqual("d41d8cd98f00b204e9800998ecf8427e", b.md5)

    @gen_test
    def test_grid_out_custom_opts(self):
        one = motor.MotorGridIn(
            self.db.fs, _id=5, filename="my_file",
            contentType="text/html", chunkSize=1000, aliases=["foo"],
            metadata={"foo": 1, "bar": 2}, bar=3, baz="hello")

        yield one.write(b"hello world")
        yield one.close()

        two = yield motor.MotorGridOut(self.db.fs, 5).open()

        self.assertEqual(5, two._id)
        self.assertEqual(11, two.length)
        self.assertEqual("text/html", two.content_type)
        self.assertEqual(1000, two.chunk_size)
        self.assertTrue(isinstance(two.upload_date, datetime.datetime))
        self.assertEqual(["foo"], two.aliases)
        self.assertEqual({"foo": 1, "bar": 2}, two.metadata)
        self.assertEqual(3, two.bar)
        self.assertEqual("5eb63bbbe01eeed093cb22bb8f5acdc3", two.md5)

    @gen_test
    def test_grid_out_file_document(self):
        one = motor.MotorGridIn(self.db.fs)
        yield one.write(b"foo bar")
        yield one.close()

        file_document = yield self.db.fs.files.find_one()
        two = motor.MotorGridOut(self.db.fs, file_document=file_document)
        self.assertEqual(b"foo bar", (yield two.read()))

        file_document = yield self.db.fs.files.find_one()
        three = motor.MotorGridOut(self.db.fs, 5, file_document)
        self.assertEqual(b"foo bar", (yield three.read()))

        with assert_raises(NoFile):
            yield motor.MotorGridOut(self.db.fs, file_document={}).open()

    @gen_test
    def test_write_file_like(self):
        one = motor.MotorGridIn(self.db.fs)
        yield one.write(b"hello world")
        yield one.close()

        two = motor.MotorGridOut(self.db.fs, one._id)
        three = motor.MotorGridIn(self.db.fs)
        yield three.write(two)
        yield three.close()

        four = motor.MotorGridOut(self.db.fs, three._id)
        self.assertEqual(b"hello world", (yield four.read()))

    @gen_test
    def test_set_after_close(self):
        f = motor.MotorGridIn(self.db.fs, _id="foo", bar="baz")

        self.assertEqual("foo", f._id)
        self.assertEqual("baz", f.bar)
        self.assertRaises(AttributeError, getattr, f, "baz")
        self.assertRaises(AttributeError, getattr, f, "uploadDate")
        self.assertRaises(AttributeError, setattr, f, "_id", 5)

        f.bar = "foo"
        f.baz = 5

        self.assertEqual("foo", f.bar)
        self.assertEqual(5, f.baz)
        self.assertRaises(AttributeError, getattr, f, "uploadDate")

        yield f.close()

        self.assertEqual("foo", f._id)
        self.assertEqual("foo", f.bar)
        self.assertEqual(5, f.baz)
        self.assertTrue(f.uploadDate)

        self.assertRaises(AttributeError, setattr, f, "_id", 5)
        yield f.set("bar", "a")
        yield f.set("baz", "b")
        self.assertRaises(AttributeError, setattr, f, "upload_date", 5)

        g = yield motor.MotorGridOut(self.db.fs, f._id).open()
        self.assertEqual("a", g.bar)
        self.assertEqual("b", g.baz)

    @gen_test
    def test_stream_to_handler(self):
        class MockRequestHandler(object):
            def __init__(self):
                self.n_written = 0

            def write(self, data):
                self.n_written += len(data)

            def flush(self):
                pass

        fs = motor.MotorGridFS(self.db)

        for content_length in (0, 1, 100, 100 * 1000):
            _id = yield fs.put(b'a' * content_length)
            gridout = yield fs.get(_id)
            handler = MockRequestHandler()
            yield gridout.stream_to_handler(handler)
            self.assertEqual(content_length, handler.n_written)
            yield fs.delete(_id)

if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_motor_ipv6
# Copyright 2012-2014 MongoDB, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import unicode_literals

"""Test Motor, an asynchronous driver for MongoDB and Tornado."""

import unittest

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from tornado.testing import gen_test

import motor
from test import host, port, MotorTest, setUpModule, SkipTest


class MotorIPv6Test(MotorTest):
    @gen_test
    def test_ipv6(self):
        assert host in ('localhost', '127.0.0.1'), (
            "This unittest isn't written to test IPv6 with host %s" % repr(host)
        )

        try:
            MongoClient("[::1]")
        except ConnectionFailure:
            # Either mongod was started without --ipv6
            # or the OS doesn't support it (or both).
            raise SkipTest("No IPV6")

        cx_string = "mongodb://[::1]:%d" % port
        cx = motor.MotorClient(cx_string, io_loop=self.io_loop)
        collection = cx.motor_test.test_collection
        yield collection.insert({"dummy": "object"})
        self.assertTrue((yield collection.find_one({"dummy": "object"})))


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_motor_pool
# Copyright 2013-2014 MongoDB, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import unicode_literals

"""Test Motor, an asynchronous driver for MongoDB and Tornado."""

import functools
import greenlet
import random
import unittest

import pymongo.errors
from tornado import stack_context
from tornado.concurrent import Future
from tornado.testing import gen_test

import test
from test import MotorTest, assert_raises, setUpModule, SkipTest
from test.utils import delay


class MotorPoolTest(MotorTest):
    @gen_test
    def test_max_size_default(self):
        yield self.cx.open()
        pool = self.cx._get_primary_pool()

        # Current defaults
        self.assertEqual(100, pool.max_size)
        self.assertEqual(None, pool.wait_queue_timeout)
        self.assertEqual(None, pool.wait_queue_multiple)

    @gen_test(timeout=30)
    def test_max_size(self):
        if not test.sync_cx.server_info().get('javascriptEngine') == 'V8':
            raise SkipTest("Need multithreaded Javascript in mongod for test")

        max_pool_size = 5
        cx = self.motor_client(max_pool_size=max_pool_size)

        # Lazy connection.
        self.assertEqual(None, cx._get_primary_pool())
        yield cx.motor_test.test_collection.remove()
        pool = cx._get_primary_pool()
        self.assertEqual(max_pool_size, pool.max_size)
        self.assertEqual(1, len(pool.sockets))
        self.assertEqual(1, pool.motor_sock_counter)

        # Grow to max_pool_size.
        ops_completed = Future()
        nops = 100
        results = []

        def callback(i, result, error):
            self.assertFalse(error)
            results.append(i)
            if len(results) == nops:
                ops_completed.set_result(None)

        collection = cx.motor_test.test_collection
        yield collection.insert({})  # Need a document.

        for i in range(nops):
            # Introduce random delay, avg 5ms, just to make sure we're async.
            collection.find_one(
                {'$where': delay(random.random() / 10)},
                callback=functools.partial(callback, i))

        yield ops_completed

        # All ops completed, but not in order.
        self.assertEqual(list(range(nops)), sorted(results))
        self.assertNotEqual(list(range(nops)), results)

        self.assertEqual(max_pool_size, len(pool.sockets))
        self.assertEqual(max_pool_size, pool.motor_sock_counter)
        cx.close()

    @gen_test(timeout=30)
    def test_wait_queue_timeout(self):
        # Do a find_one that takes 1 second, and set waitQueueTimeoutMS to 500,
        # 5000, and None. Verify timeout iff max_wait_time < 1 sec.
        where_delay = 1
        yield self.collection.insert({})
        for waitQueueTimeoutMS in (500, 5000, None):
            cx = self.motor_client(
                max_pool_size=1, waitQueueTimeoutMS=waitQueueTimeoutMS)

            yield cx.open()
            pool = cx._get_primary_pool()
            if waitQueueTimeoutMS:
                self.assertEqual(
                    waitQueueTimeoutMS, pool.wait_queue_timeout * 1000)
            else:
                self.assertTrue(pool.wait_queue_timeout is None)

            collection = cx.motor_test.test_collection
            future = collection.find_one({'$where': delay(where_delay)})
            if waitQueueTimeoutMS and waitQueueTimeoutMS < where_delay * 1000:
                with assert_raises(pymongo.errors.ConnectionFailure):
                    yield collection.find_one()
            else:
                # No error
                yield collection.find_one()
            yield future
            cx.close()

    @gen_test
    def test_connections_unacknowledged_writes(self):
        # Verifying that unacknowledged writes don't open extra connections
        collection = self.cx.motor_test.test_collection
        yield collection.drop()
        pool = self.cx._get_primary_pool()
        self.assertEqual(1, pool.motor_sock_counter)

        nops = 10
        for i in range(nops - 1):
            collection.insert({'_id': i}, w=0)

            # We have only one socket open, and it's already back in the pool
            self.assertEqual(1, pool.motor_sock_counter)
            self.assertEqual(1, len(pool.sockets))

        # Acknowledged write; uses same socket and blocks for all inserts
        yield collection.insert({'_id': nops - 1})
        self.assertEqual(1, pool.motor_sock_counter)

        # Socket is back in the idle pool
        self.assertEqual(1, len(pool.sockets))

        # All ops completed
        docs = yield collection.find().sort('_id').to_list(length=100)
        self.assertEqual(list(range(nops)), [doc['_id'] for doc in docs])

    @gen_test
    def test_stack_context(self):
        # See http://tornadoweb.org/en/stable/stack_context.html
        # MotorPool.get_socket can block waiting for a callback in another
        # context to return a socket. We verify MotorPool's stack-context
        # handling by testing that exceptions raised in get_socket's
        # continuation are caught in get_socket's stack context, not
        # return_socket's.

        loop = self.io_loop
        history = []
        cx = self.motor_client(max_pool_size=1)

        # Open a socket
        yield cx.motor_test.test_collection.find_one()

        pool = cx._get_primary_pool()
        self.assertEqual(1, len(pool.sockets))
        sock_info = pool.get_socket()

        main_gr = greenlet.getcurrent()

        def catch_get_sock_exc(exc_type, exc_value, exc_traceback):
            history.extend(['get_sock_exc', exc_value])
            return True  # Don't propagate

        def catch_return_sock_exc(exc_type, exc_value, exc_traceback):
            history.extend(['return_sock_exc', exc_value])
            return True  # Don't propagate

        def get_socket():
            # Blocks until socket is available, since max_pool_size is 1.
            pool.get_socket()
            loop.add_callback(raise_callback)

        my_assert = AssertionError('foo')

        def raise_callback():
            history.append('raise')
            raise my_assert

        def return_socket():
            with stack_context.ExceptionStackContext(catch_return_sock_exc):
                pool.maybe_return_socket(sock_info)

            main_gr.switch()

        with stack_context.ExceptionStackContext(catch_get_sock_exc):
            loop.add_callback(greenlet.greenlet(get_socket).switch)

        greenlet.greenlet(return_socket).switch()
        yield self.pause(0.1)

        # 'return_sock_exc' was *not* added to history, because stack context
        # wasn't leaked from return_socket to get_socket.
        self.assertEqual(['raise', 'get_sock_exc', my_assert], history)
        cx.close()


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_motor_replica_set
# Copyright 2012-2014 MongoDB, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import unicode_literals

"""Test Motor, an asynchronous driver for MongoDB and Tornado."""

import unittest

import pymongo.errors
import pymongo.mongo_replica_set_client
from tornado import iostream, gen
from tornado.testing import gen_test

import motor
import test
from test import host, port, MotorReplicaSetTestBase, assert_raises, MotorTest
from test import setUpModule, SkipTest
from test.motor_client_test_generic import MotorClientTestMixin


class MotorReplicaSetTest(MotorReplicaSetTestBase):
    @gen_test
    def test_replica_set_client(self):
        cx = motor.MotorReplicaSetClient(
            '%s:%s' % (host, port),
            replicaSet=test.rs_name,
            io_loop=self.io_loop)

        self.assertEqual(cx, (yield cx.open()))
        self.assertEqual(cx, (yield cx.open()))  # Same the second time.
        self.assertTrue(isinstance(
            cx.delegate._MongoReplicaSetClient__monitor,
            motor.MotorReplicaSetMonitor))

        self.assertEqual(
            self.io_loop,
            cx.delegate._MongoReplicaSetClient__monitor.io_loop)

        cx.close()

    @gen_test
    def test_open_callback(self):
        cx = motor.MotorReplicaSetClient(
            '%s:%s' % (host, port),
            replicaSet=test.rs_name,
            io_loop=self.io_loop)

        yield self.check_optional_callback(cx.open)
        cx.close()

    def test_io_loop(self):
        with assert_raises(TypeError):
            motor.MotorReplicaSetClient(
                '%s:%s' % (host, port),
                replicaSet=test.rs_name,
                io_loop='foo')

    @gen_test
    def test_auto_reconnect_exception_when_read_preference_is_secondary(self):
        old_write = iostream.IOStream.write
        iostream.IOStream.write = lambda self, data: self.close()

        try:
            cursor = self.rsc.motor_test.test_collection.find(
                read_preference=pymongo.ReadPreference.SECONDARY)

            with assert_raises(pymongo.errors.AutoReconnect):
                yield cursor.fetch_next
        finally:
            iostream.IOStream.write = old_write

    @gen_test
    def test_connection_failure(self):
        # Assuming there isn't anything actually running on this port
        client = motor.MotorReplicaSetClient(
            'localhost:8765', replicaSet='rs', io_loop=self.io_loop)

        # Test the Future interface.
        with assert_raises(pymongo.errors.ConnectionFailure):
            yield client.open()

        # Test with a callback.
        (result, error), _ = yield gen.Task(client.open)
        self.assertEqual(None, result)
        self.assertTrue(isinstance(error, pymongo.errors.ConnectionFailure))


class MotorReplicaSetClientTestGeneric(
        MotorClientTestMixin,
        MotorReplicaSetTestBase):

    def get_client(self):
        return self.rsc


class TestReplicaSetClientAgainstStandalone(MotorTest):
    """This is a funny beast -- we want to run tests for MotorReplicaSetClient
    but only if the database at DB_IP and DB_PORT is a standalone.
    """
    def setUp(self):
        super(TestReplicaSetClientAgainstStandalone, self).setUp()
        if test.is_replica_set:
            raise SkipTest(
                "Connected to a replica set, not a standalone mongod")

    @gen_test
    def test_connect(self):
        with assert_raises(pymongo.errors.ConnectionFailure):
            yield motor.MotorReplicaSetClient(
                '%s:%s' % (host, port), replicaSet='anything',
                connectTimeoutMS=600).test.test.find_one()


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_motor_son_manipulator
# Copyright 2013-2014 MongoDB, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import unicode_literals

"""Test Motor, an asynchronous driver for MongoDB and Tornado."""

import pymongo.son_manipulator
from tornado.testing import gen_test

import test
from test import MotorTest, setUpModule


class CustomSONManipulator(pymongo.son_manipulator.SONManipulator):
    """A pymongo outgoing SON Manipulator that adds
    ``{'added_field' : 42}``
    """
    def will_copy(self):
        return False

    def transform_outgoing(self, son, collection):
        assert 'added_field' not in son
        son['added_field'] = 42
        return son


class SONManipulatorTest(MotorTest):
    def setUp(self):
        super(SONManipulatorTest, self).setUp()

    def tearDown(self):
        test.sync_db.son_manipulator_test_collection.remove()
        super(SONManipulatorTest, self).tearDown()

    @gen_test
    def test_with_find_one(self):
        coll = self.cx.motor_test.son_manipulator_test_collection
        _id = yield coll.insert({'foo': 'bar'})
        self.assertEqual(
            {'_id': _id, 'foo': 'bar'},
            (yield coll.find_one()))

        # Add SONManipulator and test again.
        coll.database.add_son_manipulator(CustomSONManipulator())
        self.assertEqual(
            {'_id': _id, 'foo': 'bar', 'added_field': 42},
            (yield coll.find_one()))

    @gen_test
    def test_with_fetch_next(self):
        coll = self.cx.motor_test.son_manipulator_test_collection
        coll.database.add_son_manipulator(CustomSONManipulator())
        _id = yield coll.insert({'foo': 'bar'})
        cursor = coll.find()
        self.assertTrue((yield cursor.fetch_next))
        self.assertEqual(
            {'_id': _id, 'foo': 'bar', 'added_field': 42},
            cursor.next_object())

    @gen_test
    def test_with_to_list(self):
        coll = self.cx.motor_test.son_manipulator_test_collection
        _id1, _id2 = yield coll.insert([{}, {}])
        found = yield coll.find().sort([('_id', 1)]).to_list(length=2)
        self.assertEqual([{'_id': _id1}, {'_id': _id2}], found)

        coll.database.add_son_manipulator(CustomSONManipulator())
        expected = [
            {'_id': _id1, 'added_field': 42},
            {'_id': _id2, 'added_field': 42}]

        found = yield coll.find().sort([('_id', 1)]).to_list(length=2)
        self.assertEqual(expected, found)

########NEW FILE########
__FILENAME__ = test_motor_ssl
# Copyright 2012-2014 MongoDB, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import unicode_literals

"""Test Motor, an asynchronous driver for MongoDB and Tornado."""

import socket
import ssl

try:
    # Python 2.
    from urllib import quote_plus
except ImportError:
    # Python 3.
    from urllib.parse import quote_plus

from pymongo.common import HAS_SSL
from pymongo.errors import (ConfigurationError,
                            ConnectionFailure,
                            OperationFailure)
from tornado.testing import gen_test

import motor
import test
from test import MotorTest, host, port, version, setUpModule, SkipTest
from test import HAVE_SSL, CLIENT_PEM, CA_PEM
from test.utils import server_started_with_auth, remove_all_users


# Whether 'server' is a resolvable hostname.
SERVER_IS_RESOLVABLE = False
MONGODB_X509_USERNAME = \
    "CN=client,OU=kerneluser,O=10Gen,L=New York City,ST=New York,C=US"

# Start a mongod instance (built with SSL support) like so:
#
# mongod --dbpath /path/to/data/directory --sslOnNormalPorts \
# --sslPEMKeyFile /path/to/mongo/jstests/libs/server.pem \
# --sslCAFile /path/to/mongo/jstests/libs/ca.pem \
# --sslCRLFile /path/to/mongo/jstests/libs/crl.pem
#
# Optionally, also pass --sslWeakCertificateValidation to run test_simple_ssl.
#
# For all tests to pass with MotorReplicaSetClient, the replica set
# configuration must use 'server' for the hostname of all hosts.
# Make sure you have 'server' as an alias for localhost in /etc/hosts.


def is_server_resolvable():
    """Returns True if 'server' is resolvable."""
    socket_timeout = socket.getdefaulttimeout()
    socket.setdefaulttimeout(1)
    try:
        socket.gethostbyname('server')
        return True
    except socket.error:
        return False
    finally:
        socket.setdefaulttimeout(socket_timeout)


def setup_module():
    global SERVER_IS_RESOLVABLE

    if HAVE_SSL and test.mongod_validates_client_cert:
        SERVER_IS_RESOLVABLE = is_server_resolvable()


class MotorNoSSLTest(MotorTest):
    ssl = True

    def test_no_ssl(self):
        # Test that ConfigurationError is raised if the ssl
        # module isn't available.
        if HAS_SSL:
            raise SkipTest(
                "We have SSL compiled into Python, can't test what happens "
                "without SSL")

        # ssl=True is passed explicitly.
        self.assertRaises(ConfigurationError,
                          motor.MotorClient, ssl=True)
        self.assertRaises(ConfigurationError,
                          motor.MotorReplicaSetClient,
                          replicaSet='rs',
                          ssl=True)

        # ssl=True is implied.
        self.assertRaises(ConfigurationError,
                          motor.MotorClient,
                          ssl_certfile=CLIENT_PEM)
        self.assertRaises(ConfigurationError,
                          motor.MotorReplicaSetClient,
                          replicaSet='rs',
                          ssl_certfile=CLIENT_PEM)


class MotorSSLTest(MotorTest):
    ssl = True

    def setUp(self):
        if not HAS_SSL:
            raise SkipTest("The ssl module is not available.")

        super(MotorSSLTest, self).setUp()

    def test_config_ssl(self):
        self.assertRaises(ConfigurationError, motor.MotorClient, ssl='foo')
        self.assertRaises(ConfigurationError,
                          motor.MotorClient,
                          ssl=False,
                          ssl_certfile=CLIENT_PEM)

        self.assertRaises(ConfigurationError,
                          motor.MotorReplicaSetClient,
                          replicaSet='rs',
                          ssl='foo')

        self.assertRaises(ConfigurationError,
                          motor.MotorReplicaSetClient,
                          replicaSet='rs',
                          ssl=False,
                          ssl_certfile=CLIENT_PEM)

        self.assertRaises(IOError, motor.MotorClient, ssl_certfile="NoFile")
        self.assertRaises(TypeError, motor.MotorClient, ssl_certfile=True)
        self.assertRaises(IOError, motor.MotorClient, ssl_keyfile="NoFile")
        self.assertRaises(TypeError, motor.MotorClient, ssl_keyfile=True)

    @gen_test
    def test_simple_ssl(self):
        if test.mongod_validates_client_cert:
            raise SkipTest("mongod validates SSL certs")

        # Expects the server to be running with ssl and with
        # no --sslPEMKeyFile or with --sslWeakCertificateValidation.
        client = motor.MotorClient(host, port, ssl=True)
        yield client.db.collection.find_one()
        response = yield client.admin.command('ismaster')
        if 'setName' in response:
            client = motor.MotorReplicaSetClient(
                '%s:%d' % (host, port),
                replicaSet=response['setName'],
                ssl=True)

            yield client.db.collection.find_one()

    @gen_test
    def test_cert_ssl(self):
        # Expects the server to be running with the server.pem, ca.pem
        # and crl.pem provided in mongodb and the server tests e.g.:
        #
        #   --sslPEMKeyFile=jstests/libs/server.pem
        #   --sslCAFile=jstests/libs/ca.pem
        #   --sslCRLFile=jstests/libs/crl.pem
        #
        # Also requires an /etc/hosts entry where "server" is resolvable.
        if not test.mongod_validates_client_cert:
            raise SkipTest("No mongod available over SSL with certs")

        if not SERVER_IS_RESOLVABLE:
            raise SkipTest("No hosts entry for 'server'. Cannot validate "
                           "hostname in the certificate")

        client = motor.MotorClient(host, port, ssl_certfile=CLIENT_PEM)
        yield client.db.collection.find_one()
        response = yield client.admin.command('ismaster')
        if 'setName' in response:
            client = motor.MotorReplicaSetClient(
                '%s:%d' % (host, port),
                replicaSet=response['setName'],
                ssl=True,
                ssl_certfile=CLIENT_PEM)

            yield client.db.collection.find_one()

    @gen_test
    def test_cert_ssl_validation(self):
        # Expects the server to be running with the server.pem, ca.pem
        # and crl.pem provided in mongodb and the server tests e.g.:
        #
        #   --sslPEMKeyFile=jstests/libs/server.pem
        #   --sslCAFile=jstests/libs/ca.pem
        #   --sslCRLFile=jstests/libs/crl.pem
        #
        # Also requires an /etc/hosts entry where "server" is resolvable.
        if not test.mongod_validates_client_cert:
            raise SkipTest("No mongod available over SSL with certs")

        if not SERVER_IS_RESOLVABLE:
            raise SkipTest("No hosts entry for 'server'. Cannot validate "
                           "hostname in the certificate")

        client = motor.MotorClient(
            'server',
            ssl_certfile=CLIENT_PEM,
            ssl_cert_reqs=ssl.CERT_REQUIRED,
            ssl_ca_certs=CA_PEM)

        yield client.db.collection.find_one()
        response = yield client.admin.command('ismaster')

        if 'setName' in response:
            if response['primary'].split(":")[0] != 'server':
                raise SkipTest("No hosts in the replicaset for 'server'. "
                               "Cannot validate hostname in the certificate")

            client = motor.MotorReplicaSetClient(
                'server',
                replicaSet=response['setName'],
                ssl_certfile=CLIENT_PEM,
                ssl_cert_reqs=ssl.CERT_REQUIRED,
                ssl_ca_certs=CA_PEM)

            yield client.db.collection.find_one()

    @gen_test
    def test_cert_ssl_validation_optional(self):
        # Expects the server to be running with the server.pem, ca.pem
        # and crl.pem provided in mongodb and the server tests e.g.:
        #
        #   --sslPEMKeyFile=jstests/libs/server.pem
        #   --sslCAFile=jstests/libs/ca.pem
        #   --sslCRLFile=jstests/libs/crl.pem
        #
        # Also requires an /etc/hosts entry where "server" is resolvable.
        if not test.mongod_validates_client_cert:
            raise SkipTest("No mongod available over SSL with certs")

        if not SERVER_IS_RESOLVABLE:
            raise SkipTest("No hosts entry for 'server'. Cannot validate "
                           "hostname in the certificate")

        client = motor.MotorClient(
            'server',
            ssl_certfile=CLIENT_PEM,
            ssl_cert_reqs=ssl.CERT_OPTIONAL,
            ssl_ca_certs=CA_PEM)

        response = yield client.admin.command('ismaster')
        if 'setName' in response:
            if response['primary'].split(":")[0] != 'server':
                raise SkipTest("No hosts in the replicaset for 'server'. "
                               "Cannot validate hostname in the certificate")

            client = motor.MotorReplicaSetClient(
                'server',
                replicaSet=response['setName'],
                ssl_certfile=CLIENT_PEM,
                ssl_cert_reqs=ssl.CERT_OPTIONAL,
                ssl_ca_certs=CA_PEM)

            yield client.db.collection.find_one()

    @gen_test
    def test_cert_ssl_validation_hostname_fail(self):
        # Expects the server to be running with the server.pem, ca.pem
        # and crl.pem provided in mongodb and the server tests e.g.:
        #
        #   --sslPEMKeyFile=jstests/libs/server.pem
        #   --sslCAFile=jstests/libs/ca.pem
        #   --sslCRLFile=jstests/libs/crl.pem
        if not test.mongod_validates_client_cert:
            raise SkipTest("No mongod available over SSL with certs")

        client = motor.MotorClient(
            host, port, ssl=True, ssl_certfile=CLIENT_PEM)

        response = yield client.admin.command('ismaster')
        try:
            # Create client with hostname 'localhost' or whatever, not
            # the name 'server', which is what the server cert presents.
            client = motor.MotorClient(
                host, port,
                ssl_certfile=CLIENT_PEM,
                ssl_cert_reqs=ssl.CERT_REQUIRED,
                ssl_ca_certs=CA_PEM)

            yield client.db.collection.find_one()
            self.fail("Invalid hostname should have failed")
        except ConnectionFailure:
            pass

        if 'setName' in response:
            try:
                client = motor.MotorReplicaSetClient(
                    '%s:%d' % (host, port),
                    replicaSet=response['setName'],
                    ssl_certfile=CLIENT_PEM,
                    ssl_cert_reqs=ssl.CERT_REQUIRED,
                    ssl_ca_certs=CA_PEM)

                yield client.db.collection.find_one()
                self.fail("Invalid hostname should have failed")
            except ConnectionFailure:
                pass

    @gen_test
    def test_mongodb_x509_auth(self):
        # Expects the server to be running with the server.pem, ca.pem
        # and crl.pem provided in mongodb and the server tests as well as
        # --auth:
        #
        #   --sslPEMKeyFile=jstests/libs/server.pem
        #   --sslCAFile=jstests/libs/ca.pem
        #   --sslCRLFile=jstests/libs/crl.pem
        #   --auth
        if not test.mongod_validates_client_cert:
            raise SkipTest("No mongod available over SSL with certs")

        client = motor.MotorClient(host, port, ssl_certfile=CLIENT_PEM)
        if not (yield version.at_least(client, (2, 5, 3, -1))):
            raise SkipTest("MONGODB-X509 tests require MongoDB 2.5.3 or newer")

        if not (yield server_started_with_auth(client)):
            raise SkipTest('Authentication is not enabled on server')

        # Give admin all necessary privileges.
        yield client['$external'].add_user(MONGODB_X509_USERNAME, roles=[
            {'role': 'readWriteAnyDatabase', 'db': 'admin'},
            {'role': 'userAdminAnyDatabase', 'db': 'admin'}])

        collection = client.motor_test.test
        with test.assert_raises(OperationFailure):
            yield collection.count()

        yield client.admin.authenticate(
            MONGODB_X509_USERNAME, mechanism='MONGODB-X509')

        yield collection.remove()
        uri = ('mongodb://%s@%s:%d/?authMechanism='
               'MONGODB-X509' % (
               quote_plus(MONGODB_X509_USERNAME), host, port))

        # SSL options aren't supported in the URI....
        auth_uri_client = motor.MotorClient(uri, ssl_certfile=CLIENT_PEM)
        yield auth_uri_client.db.collection.find_one()

        # Cleanup.
        yield remove_all_users(client['$external'])
        yield client['$external'].logout()

########NEW FILE########
__FILENAME__ = test_motor_tail
# Copyright 2012-2014 MongoDB, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import unicode_literals

"""Test Motor, an asynchronous driver for MongoDB and Tornado."""

import threading
import time
import unittest

from tornado.testing import gen_test

import test
from test import MotorTest, setUpModule


class MotorTailTest(MotorTest):
    def setUp(self):
        super(MotorTailTest, self).setUp()
        test.sync_db.capped.drop()
        # autoIndexId catches test bugs that try to insert duplicate _id's
        test.sync_db.create_collection(
            'capped', capped=True, size=1000, autoIndexId=True)

        test.sync_db.uncapped.drop()
        test.sync_db.uncapped.insert({})

    def start_insertion_thread(self, pauses):
        """A thread that gradually inserts documents into a capped collection
        """
        def add_docs():
            i = 0
            for pause in pauses:
                time.sleep(pause)
                test.sync_db.capped.insert({'_id': i})
                i += 1

        t = threading.Thread(target=add_docs)
        t.start()
        return t

    # Need at least one pause > 4.5 seconds to ensure we recover when
    # getMore times out
    tail_pauses = (0, 1, 0, 1, 0, 5, 0, 0)
    expected_duration = sum(tail_pauses) + 10  # Add 10 sec of fudge

    @gen_test(timeout=expected_duration)
    def test_tail(self):
        expected = [{'_id': i} for i in range(len(self.tail_pauses))]
        t = self.start_insertion_thread(self.tail_pauses)
        capped = self.db.capped
        results = []
        time = self.io_loop.time
        start = time()
        cursor = capped.find(tailable=True, await_data=True)

        while (results != expected
               and time() - start < MotorTailTest.expected_duration):

            while (yield cursor.fetch_next):
                doc = cursor.next_object()
                results.append(doc)

            # If cursor was created while capped collection had no documents
            # (i.e., before the thread inserted first doc), it dies
            # immediately. Just restart it.
            if not cursor.alive:
                cursor = capped.find(tailable=True, await_data=True)

        t.join()
        self.assertEqual(expected, results)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_motor_web
# Copyright 2012-2014 MongoDB, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import unicode_literals

"""Test utilities for using Motor with Tornado web applications."""

import datetime
import email
import hashlib
import time
import re
import unittest

import gridfs
from tornado.testing import AsyncHTTPTestCase
from tornado.web import Application

import motor
import motor.web
import test
from test import host, port, setUpModule


# We're using Tornado's AsyncHTTPTestCase instead of our own MotorTestCase for
# the convenience of self.fetch().
class GridFSHandlerTestBase(AsyncHTTPTestCase):
    def setUp(self):
        super(GridFSHandlerTestBase, self).setUp()

        self.fs = gridfs.GridFS(test.sync_db)

        # Make a 500k file in GridFS with filename 'foo'
        self.contents = b'Jesse' * 100 * 1024
        self.contents_hash = hashlib.md5(self.contents).hexdigest()

        # Record when we created the file, to check the Last-Modified header
        self.put_start = datetime.datetime.utcnow().replace(microsecond=0)
        self.file_id = 'id'
        self.fs.delete(self.file_id)
        self.fs.put(
            self.contents, _id='id', filename='foo', content_type='my type')

        self.put_end = datetime.datetime.utcnow().replace(microsecond=0)
        self.assertTrue(self.fs.get_last_version('foo'))

    def motor_db(self):
        return motor.MotorClient(host, port, io_loop=self.io_loop).motor_test

    def tearDown(self):
        self.fs.delete(self.file_id)
        super(GridFSHandlerTestBase, self).tearDown()
        
    def get_app(self):
        return Application([
            ('/(.+)', motor.web.GridFSHandler, {'database': self.motor_db()})])

    def stop(self, *args, **kwargs):
        # A stop() method more permissive about the number of its positional
        # arguments than AsyncHTTPTestCase.stop
        if len(args) == 1:
            AsyncHTTPTestCase.stop(self, args[0], **kwargs)
        else:
            AsyncHTTPTestCase.stop(self, args, **kwargs)

    def parse_date(self, d):
        date_tuple = email.utils.parsedate(d)
        return datetime.datetime.fromtimestamp(time.mktime(date_tuple))

    def last_mod(self, response):
        """Parse the 'Last-Modified' header from an HTTP response into a
           datetime.
        """
        return self.parse_date(response.headers['Last-Modified'])

    def expires(self, response):
        return self.parse_date(response.headers['Expires'])


class GridFSHandlerTest(GridFSHandlerTestBase):
    def test_basic(self):
        # First request
        response = self.fetch('/foo')

        self.assertEqual(200, response.code)
        self.assertEqual(self.contents, response.body)
        self.assertEqual(
            len(self.contents), int(response.headers['Content-Length']))
        self.assertEqual('my type', response.headers['Content-Type'])
        self.assertEqual('public', response.headers['Cache-Control'])
        self.assertTrue('Expires' not in response.headers)

        etag = response.headers['Etag']
        last_mod_dt = self.last_mod(response)
        self.assertEqual(self.contents_hash, etag.strip('"'))
        self.assertTrue(self.put_start <= last_mod_dt <= self.put_end)

        # Now check we get 304 NOT MODIFIED responses as appropriate
        for ims_value in (
            last_mod_dt,
            last_mod_dt + datetime.timedelta(seconds=1)
        ):
            response = self.fetch('/foo', if_modified_since=ims_value)
            self.assertEqual(304, response.code)
            self.assertEqual(b'', response.body)

        # If-Modified-Since in the past, get whole response back
        response = self.fetch(
            '/foo',
            if_modified_since=last_mod_dt - datetime.timedelta(seconds=1))
        self.assertEqual(200, response.code)
        self.assertEqual(self.contents, response.body)

        # Matching Etag
        response = self.fetch('/foo', headers={'If-None-Match': etag})
        self.assertEqual(304, response.code)
        self.assertEqual(b'', response.body)

        # Mismatched Etag
        response = self.fetch('/foo', headers={'If-None-Match': etag + 'a'})
        self.assertEqual(200, response.code)
        self.assertEqual(self.contents, response.body)

    def test_404(self):
        response = self.fetch('/bar')
        self.assertEqual(404, response.code)

    def test_head(self):
        response = self.fetch('/foo', method='HEAD')

        # Get Etag and parse Last-Modified into a datetime
        etag = response.headers['Etag']
        last_mod_dt = self.last_mod(response)

        # Test the result
        self.assertEqual(200, response.code)
        self.assertEqual(b'', response.body)  # Empty body for HEAD request
        self.assertEqual(
            len(self.contents), int(response.headers['Content-Length']))
        self.assertEqual('my type', response.headers['Content-Type'])
        self.assertEqual(self.contents_hash, etag.strip('"'))
        self.assertTrue(self.put_start <= last_mod_dt <= self.put_end)
        self.assertEqual('public', response.headers['Cache-Control'])

    def test_content_type(self):
        # Check that GridFSHandler uses file extension to guess Content-Type
        # if not provided
        for filename, expected_type in [
            ('foo.jpg', 'jpeg'),
            ('foo.png', 'png'),
            ('ht.html', 'html'),
            ('jscr.js', 'javascript'),
        ]:
            # 'fs' is PyMongo's blocking GridFS
            self.fs.put(b'', filename=filename)
            for method in 'GET', 'HEAD':
                response = self.fetch('/' + filename, method=method)
                self.assertEqual(200, response.code)
                # mimetypes are platform-defined, be fuzzy
                self.assertTrue(
                    response.headers['Content-Type'].lower().endswith(
                        expected_type))


class CustomGridFSHandlerTest(GridFSHandlerTestBase):
    def get_app(self):
        class CustomGridFSHandler(motor.web.GridFSHandler):
            def get_gridfs_file(self, fs, path):
                # Test overriding the get_gridfs_file() method, path is
                # interpreted as file_id instead of filename.
                return fs.get(file_id=path)  # A Future MotorGridOut

            def get_cache_time(self, path, modified, mime_type):
                return 10

            def set_extra_headers(self, path, gridout):
                self.set_header('quux', 'fizzledy')

        return Application([
            ('/(.+)', CustomGridFSHandler, {'database': self.motor_db()})])

    def test_get_gridfs_file(self):
        # We overrode get_gridfs_file so we expect getting by filename *not* to
        # work now; we'll get a 404. We have to get by file_id now.
        response = self.fetch('/foo')
        self.assertEqual(404, response.code)

        response = self.fetch('/' + str(self.file_id))
        self.assertEqual(200, response.code)

        self.assertEqual(self.contents, response.body)
        cache_control = response.headers['Cache-Control']
        self.assertTrue(re.match(r'max-age=\d+', cache_control))
        self.assertEqual(10, int(cache_control.split('=')[1]))
        expires = self.expires(response)

        # It should expire about 10 seconds from now
        self.assertTrue(
            datetime.timedelta(seconds=8)
            < expires - datetime.datetime.utcnow()
            < datetime.timedelta(seconds=12))

        self.assertEqual('fizzledy', response.headers['quux'])


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_test
# Copyright 2013-2014 MongoDB, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import unicode_literals

"""Test Motor's test helpers."""

from tornado.concurrent import Future
from tornado.testing import gen_test

from motor import callback_type_error
from test import MotorTest, assert_raises, setUpModule


# Example function to be tested, helps verify that check_optional_callback
# works.
def require_callback(callback=None):
    if not callable(callback):
        raise callback_type_error
    callback(None, None)


def dont_require_callback(callback=None):
    if callback:
        if not callable(callback):
            raise callback_type_error

        callback(None, None)
    else:
        future = Future()
        future.set_result(None)
        return future


class MotorCallbackTestTest(MotorTest):
    @gen_test
    def test_check_optional_callback(self):
        yield self.check_optional_callback(dont_require_callback)
        with assert_raises(Exception):
            yield self.check_optional_callback(require_callback)

########NEW FILE########
__FILENAME__ = utils
# Copyright 2012-2014 MongoDB, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import unicode_literals

"""Utilities for testing Motor
"""

from tornado import gen

from test import version, SkipTest


def one(s):
    """Get one element of a set"""
    return next(iter(s))


def delay(sec):
    # Javascript sleep() available in MongoDB since version ~1.9
    return 'sleep(%s * 1000); return true' % sec


@gen.coroutine
def get_command_line(client):
    command_line = yield client.admin.command('getCmdLineOpts')
    assert command_line['ok'] == 1, "getCmdLineOpts() failed"
    raise gen.Return(command_line['argv'])


@gen.coroutine
def server_started_with_auth(client):
    argv = yield get_command_line(client)
    raise gen.Return('--auth' in argv or '--keyFile' in argv)


@gen.coroutine
def server_is_master_with_slave(client):
    command_line = yield get_command_line(client)
    raise gen.Return('--master' in command_line)


@gen.coroutine
def server_is_mongos(client):
    ismaster_response = yield client.admin.command('ismaster')
    raise gen.Return(ismaster_response.get('msg') == 'isdbgrid')


@gen.coroutine
def skip_if_mongos(client):
    is_mongos = yield server_is_mongos(client)
    if is_mongos:
        raise SkipTest("connected to mongos")


@gen.coroutine
def remove_all_users(db):
    version_check = yield version.at_least(db.connection, (2, 5, 4))
    if version_check:
        yield db.command({"dropAllUsersFromDatabase": 1})
    else:
        yield db.system.users.remove({})

########NEW FILE########
__FILENAME__ = version
# Copyright 2009-2014 MongoDB, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import unicode_literals, absolute_import

"""Some tools for running tests based on MongoDB server version."""

from tornado import gen


def _padded(iter, length, padding=0):
    l = list(iter)
    if len(l) < length:
        for _ in range(length - len(l)):
            l.append(0)
    return l


def _parse_version_string(version_string):
    mod = 0
    if version_string.endswith("+"):
        version_string = version_string[0:-1]
        mod = 1
    elif version_string.endswith("-pre-"):
        version_string = version_string[0:-5]
        mod = -1
    elif version_string.endswith("-"):
        version_string = version_string[0:-1]
        mod = -1
    # Deal with '-rcX' substrings
    if version_string.find('-rc') != -1:
        version_string = version_string[0:version_string.find('-rc')]
        mod = -1

    version = [int(part) for part in version_string.split(".")]
    version = _padded(version, 3)
    version.append(mod)

    return tuple(version)


@gen.coroutine
def version(client):
    info = yield client.server_info()
    raise gen.Return(_parse_version_string(info["version"]))


@gen.coroutine
def at_least(client, min_version):
    client_version = yield version(client)
    raise gen.Return(client_version >= tuple(_padded(min_version, 4)))

########NEW FILE########
