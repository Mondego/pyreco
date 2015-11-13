__FILENAME__ = benchmark
#!/usr/bin/env python

import timeit


def cprofile_main():
    from pymongo import Connection
    connection = Connection()
    connection.drop_database('timeit_test')
    connection.disconnect()

    from mongoengine import Document, DictField, connect
    connect("timeit_test")

    class Noddy(Document):
        fields = DictField()

    for i in xrange(1):
        noddy = Noddy()
        for j in range(20):
            noddy.fields["key" + str(j)] = "value " + str(j)
        noddy.save()


def main():
    """
    0.4 Performance Figures ...

    ----------------------------------------------------------------------------------------------------
    Creating 10000 dictionaries - Pymongo
    3.86744189262
    ----------------------------------------------------------------------------------------------------
    Creating 10000 dictionaries - MongoEngine
    6.23374891281
    ----------------------------------------------------------------------------------------------------
    Creating 10000 dictionaries - MongoEngine, safe=False, validate=False
    5.33027005196
    ----------------------------------------------------------------------------------------------------
    Creating 10000 dictionaries - MongoEngine, safe=False, validate=False, cascade=False
    pass - No Cascade

    0.5.X
    ----------------------------------------------------------------------------------------------------
    Creating 10000 dictionaries - Pymongo
    3.89597702026
    ----------------------------------------------------------------------------------------------------
    Creating 10000 dictionaries - MongoEngine
    21.7735359669
    ----------------------------------------------------------------------------------------------------
    Creating 10000 dictionaries - MongoEngine, safe=False, validate=False
    19.8670389652
    ----------------------------------------------------------------------------------------------------
    Creating 10000 dictionaries - MongoEngine, safe=False, validate=False, cascade=False
    pass - No Cascade

    0.6.X
    ----------------------------------------------------------------------------------------------------
    Creating 10000 dictionaries - Pymongo
    3.81559205055
    ----------------------------------------------------------------------------------------------------
    Creating 10000 dictionaries - MongoEngine
    10.0446798801
    ----------------------------------------------------------------------------------------------------
    Creating 10000 dictionaries - MongoEngine, safe=False, validate=False
    9.51354718208
    ----------------------------------------------------------------------------------------------------
    Creating 10000 dictionaries - MongoEngine, safe=False, validate=False, cascade=False
    9.02567505836
    ----------------------------------------------------------------------------------------------------
    Creating 10000 dictionaries - MongoEngine, force=True
    8.44933390617

    0.7.X
    ----------------------------------------------------------------------------------------------------
    Creating 10000 dictionaries - Pymongo
    3.78801012039
    ----------------------------------------------------------------------------------------------------
    Creating 10000 dictionaries - MongoEngine
    9.73050498962
    ----------------------------------------------------------------------------------------------------
    Creating 10000 dictionaries - MongoEngine, safe=False, validate=False
    8.33456707001
    ----------------------------------------------------------------------------------------------------
    Creating 10000 dictionaries - MongoEngine, safe=False, validate=False, cascade=False
    8.37778115273
    ----------------------------------------------------------------------------------------------------
    Creating 10000 dictionaries - MongoEngine, force=True
    8.36906409264
    0.8.X
    ----------------------------------------------------------------------------------------------------
    Creating 10000 dictionaries - Pymongo
    3.69964408875
    ----------------------------------------------------------------------------------------------------
    Creating 10000 dictionaries - Pymongo write_concern={"w": 0}
    3.5526599884
    ----------------------------------------------------------------------------------------------------
    Creating 10000 dictionaries - MongoEngine
    7.00959801674
    ----------------------------------------------------------------------------------------------------
    Creating 10000 dictionaries without continual assign - MongoEngine
    5.60943293571
    ----------------------------------------------------------------------------------------------------
    Creating 10000 dictionaries - MongoEngine - write_concern={"w": 0}, cascade=True
    6.715102911
    ----------------------------------------------------------------------------------------------------
    Creating 10000 dictionaries - MongoEngine, write_concern={"w": 0}, validate=False, cascade=True
    5.50644683838
    ----------------------------------------------------------------------------------------------------
    Creating 10000 dictionaries - MongoEngine, write_concern={"w": 0}, validate=False
    4.69851183891
    ----------------------------------------------------------------------------------------------------
    Creating 10000 dictionaries - MongoEngine, force_insert=True, write_concern={"w": 0}, validate=False
    4.68946313858
    ----------------------------------------------------------------------------------------------------
    """

    setup = """
from pymongo import MongoClient
connection = MongoClient()
connection.drop_database('timeit_test')
"""

    stmt = """
from pymongo import MongoClient
connection = MongoClient()

db = connection.timeit_test
noddy = db.noddy

for i in xrange(10000):
    example = {'fields': {}}
    for j in range(20):
        example['fields']["key"+str(j)] = "value "+str(j)

    noddy.save(example)

myNoddys = noddy.find()
[n for n in myNoddys] # iterate
"""

    print "-" * 100
    print """Creating 10000 dictionaries - Pymongo"""
    t = timeit.Timer(stmt=stmt, setup=setup)
    print t.timeit(1)

    stmt = """
from pymongo import MongoClient
connection = MongoClient()

db = connection.timeit_test
noddy = db.noddy

for i in xrange(10000):
    example = {'fields': {}}
    for j in range(20):
        example['fields']["key"+str(j)] = "value "+str(j)

    noddy.save(example, write_concern={"w": 0})

myNoddys = noddy.find()
[n for n in myNoddys] # iterate
"""

    print "-" * 100
    print """Creating 10000 dictionaries - Pymongo write_concern={"w": 0}"""
    t = timeit.Timer(stmt=stmt, setup=setup)
    print t.timeit(1)

    setup = """
from pymongo import MongoClient
connection = MongoClient()
connection.drop_database('timeit_test')
connection.disconnect()

from mongoengine import Document, DictField, connect
connect("timeit_test")

class Noddy(Document):
    fields = DictField()
"""

    stmt = """
for i in xrange(10000):
    noddy = Noddy()
    for j in range(20):
        noddy.fields["key"+str(j)] = "value "+str(j)
    noddy.save()

myNoddys = Noddy.objects()
[n for n in myNoddys] # iterate
"""

    print "-" * 100
    print """Creating 10000 dictionaries - MongoEngine"""
    t = timeit.Timer(stmt=stmt, setup=setup)
    print t.timeit(1)

    stmt = """
for i in xrange(10000):
    noddy = Noddy()
    fields = {}
    for j in range(20):
        fields["key"+str(j)] = "value "+str(j)
    noddy.fields = fields
    noddy.save()

myNoddys = Noddy.objects()
[n for n in myNoddys] # iterate
"""

    print "-" * 100
    print """Creating 10000 dictionaries without continual assign - MongoEngine"""
    t = timeit.Timer(stmt=stmt, setup=setup)
    print t.timeit(1)

    stmt = """
for i in xrange(10000):
    noddy = Noddy()
    for j in range(20):
        noddy.fields["key"+str(j)] = "value "+str(j)
    noddy.save(write_concern={"w": 0}, cascade=True)

myNoddys = Noddy.objects()
[n for n in myNoddys] # iterate
"""

    print "-" * 100
    print """Creating 10000 dictionaries - MongoEngine - write_concern={"w": 0}, cascade = True"""
    t = timeit.Timer(stmt=stmt, setup=setup)
    print t.timeit(1)

    stmt = """
for i in xrange(10000):
    noddy = Noddy()
    for j in range(20):
        noddy.fields["key"+str(j)] = "value "+str(j)
    noddy.save(write_concern={"w": 0}, validate=False, cascade=True)

myNoddys = Noddy.objects()
[n for n in myNoddys] # iterate
"""

    print "-" * 100
    print """Creating 10000 dictionaries - MongoEngine, write_concern={"w": 0}, validate=False, cascade=True"""
    t = timeit.Timer(stmt=stmt, setup=setup)
    print t.timeit(1)

    stmt = """
for i in xrange(10000):
    noddy = Noddy()
    for j in range(20):
        noddy.fields["key"+str(j)] = "value "+str(j)
    noddy.save(validate=False, write_concern={"w": 0})

myNoddys = Noddy.objects()
[n for n in myNoddys] # iterate
"""

    print "-" * 100
    print """Creating 10000 dictionaries - MongoEngine, write_concern={"w": 0}, validate=False"""
    t = timeit.Timer(stmt=stmt, setup=setup)
    print t.timeit(1)

    stmt = """
for i in xrange(10000):
    noddy = Noddy()
    for j in range(20):
        noddy.fields["key"+str(j)] = "value "+str(j)
    noddy.save(force_insert=True, write_concern={"w": 0}, validate=False)

myNoddys = Noddy.objects()
[n for n in myNoddys] # iterate
"""

    print "-" * 100
    print """Creating 10000 dictionaries - MongoEngine, force_insert=True, write_concern={"w": 0}, validate=False"""
    t = timeit.Timer(stmt=stmt, setup=setup)
    print t.timeit(1)


if __name__ == "__main__":
    main()
########NEW FILE########
__FILENAME__ = tumblelog
from mongoengine import *

connect('tumblelog')

class Comment(EmbeddedDocument):
    content = StringField()
    name = StringField(max_length=120)

class User(Document):
    email = StringField(required=True)
    first_name = StringField(max_length=50)
    last_name = StringField(max_length=50)

class Post(Document):
    title = StringField(max_length=120, required=True)
    author = ReferenceField(User)
    tags = ListField(StringField(max_length=30))
    comments = ListField(EmbeddedDocumentField(Comment))

class TextPost(Post):
    content = StringField()

class ImagePost(Post):
    image_path = StringField()

class LinkPost(Post):
    link_url = StringField()

Post.drop_collection()

john = User(email='jdoe@example.com', first_name='John', last_name='Doe')
john.save()

post1 = TextPost(title='Fun with MongoEngine', author=john)
post1.content = 'Took a look at MongoEngine today, looks pretty cool.'
post1.tags = ['mongodb', 'mongoengine']
post1.save()

post2 = LinkPost(title='MongoEngine Documentation', author=john)
post2.link_url = 'http://tractiondigital.com/labs/mongoengine/docs'
post2.tags = ['mongoengine']
post2.save()

print 'ALL POSTS'
print
for post in Post.objects:
    print post.title
    print '=' * post.title.count()

    if isinstance(post, TextPost):
        print post.content

    if isinstance(post, LinkPost):
        print 'Link:', post.link_url

    print
print

print 'POSTS TAGGED \'MONGODB\''
print
for post in Post.objects(tags='mongodb'):
    print post.title
print

num_posts = Post.objects(tags='mongodb').count()
print 'Found %d posts with tag "mongodb"' % num_posts

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# MongoEngine documentation build configuration file, created by
# sphinx-quickstart on Sun Nov 22 18:14:13 2009.
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

# -- General configuration -----------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.todo']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'MongoEngine'
copyright = u'2009, MongoEngine Authors'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
import mongoengine
# The short X.Y version.
version = mongoengine.get_version()
# The full version, including alpha/beta/rc tags.
release = mongoengine.get_version()

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
html_theme = 'sphinx_rtd_theme'

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
html_favicon = "favicon.ico"

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
#html_static_path = ['_static']

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
#html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
html_sidebars = {
    'index': ['globaltoc.html', 'searchbox.html'],
    '**': ['localtoc.html', 'relations.html', 'searchbox.html']
}


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
htmlhelp_basename = 'MongoEnginedoc'


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
latex_paper_size = 'a4'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'MongoEngine.tex', 'MongoEngine Documentation',
   'Ross Lawley', 'manual'),
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

autoclass_content = 'both'

html_theme_options = dict(
    canonical_url='http://docs.mongoengine.org/en/latest/'
)

########NEW FILE########
__FILENAME__ = common
from mongoengine.errors import NotRegistered

__all__ = ('ALLOW_INHERITANCE', 'get_document', '_document_registry')

ALLOW_INHERITANCE = False

_document_registry = {}


def get_document(name):
    doc = _document_registry.get(name, None)
    if not doc:
        # Possible old style name
        single_end = name.split('.')[-1]
        compound_end = '.%s' % single_end
        possible_match = [k for k in _document_registry.keys()
                          if k.endswith(compound_end) or k == single_end]
        if len(possible_match) == 1:
            doc = _document_registry.get(possible_match.pop(), None)
    if not doc:
        raise NotRegistered("""
            `%s` has not been registered in the document registry.
            Importing the document class automatically registers it, has it
            been imported?
        """.strip() % name)
    return doc

########NEW FILE########
__FILENAME__ = datastructures
import weakref
from mongoengine.common import _import_class

__all__ = ("BaseDict", "BaseList")


class BaseDict(dict):
    """A special dict so we can watch any changes
    """

    _dereferenced = False
    _instance = None
    _name = None

    def __init__(self, dict_items, instance, name):
        Document = _import_class('Document')
        EmbeddedDocument = _import_class('EmbeddedDocument')

        if isinstance(instance, (Document, EmbeddedDocument)):
            self._instance = weakref.proxy(instance)
        self._name = name
        return super(BaseDict, self).__init__(dict_items)

    def __getitem__(self, *args, **kwargs):
        value = super(BaseDict, self).__getitem__(*args, **kwargs)

        EmbeddedDocument = _import_class('EmbeddedDocument')
        if isinstance(value, EmbeddedDocument) and value._instance is None:
            value._instance = self._instance
        return value

    def __setitem__(self, *args, **kwargs):
        self._mark_as_changed()
        return super(BaseDict, self).__setitem__(*args, **kwargs)

    def __delete__(self, *args, **kwargs):
        self._mark_as_changed()
        return super(BaseDict, self).__delete__(*args, **kwargs)

    def __delitem__(self, *args, **kwargs):
        self._mark_as_changed()
        return super(BaseDict, self).__delitem__(*args, **kwargs)

    def __delattr__(self, *args, **kwargs):
        self._mark_as_changed()
        return super(BaseDict, self).__delattr__(*args, **kwargs)

    def __getstate__(self):
        self.instance = None
        self._dereferenced = False
        return self

    def __setstate__(self, state):
        self = state
        return self

    def clear(self, *args, **kwargs):
        self._mark_as_changed()
        return super(BaseDict, self).clear(*args, **kwargs)

    def pop(self, *args, **kwargs):
        self._mark_as_changed()
        return super(BaseDict, self).pop(*args, **kwargs)

    def popitem(self, *args, **kwargs):
        self._mark_as_changed()
        return super(BaseDict, self).popitem(*args, **kwargs)

    def update(self, *args, **kwargs):
        self._mark_as_changed()
        return super(BaseDict, self).update(*args, **kwargs)

    def _mark_as_changed(self):
        if hasattr(self._instance, '_mark_as_changed'):
            self._instance._mark_as_changed(self._name)


class BaseList(list):
    """A special list so we can watch any changes
    """

    _dereferenced = False
    _instance = None
    _name = None

    def __init__(self, list_items, instance, name):
        Document = _import_class('Document')
        EmbeddedDocument = _import_class('EmbeddedDocument')

        if isinstance(instance, (Document, EmbeddedDocument)):
            self._instance = weakref.proxy(instance)
        self._name = name
        return super(BaseList, self).__init__(list_items)

    def __getitem__(self, *args, **kwargs):
        value = super(BaseList, self).__getitem__(*args, **kwargs)

        EmbeddedDocument = _import_class('EmbeddedDocument')
        if isinstance(value, EmbeddedDocument) and value._instance is None:
            value._instance = self._instance
        return value

    def __setitem__(self, *args, **kwargs):
        self._mark_as_changed()
        return super(BaseList, self).__setitem__(*args, **kwargs)

    def __delitem__(self, *args, **kwargs):
        self._mark_as_changed()
        return super(BaseList, self).__delitem__(*args, **kwargs)

    def __setslice__(self, *args, **kwargs):
        self._mark_as_changed()
        return super(BaseList, self).__setslice__(*args, **kwargs)

    def __delslice__(self, *args, **kwargs):
        self._mark_as_changed()
        return super(BaseList, self).__delslice__(*args, **kwargs)

    def __getstate__(self):
        self.instance = None
        self._dereferenced = False
        return self

    def __setstate__(self, state):
        self = state
        return self

    def append(self, *args, **kwargs):
        self._mark_as_changed()
        return super(BaseList, self).append(*args, **kwargs)

    def extend(self, *args, **kwargs):
        self._mark_as_changed()
        return super(BaseList, self).extend(*args, **kwargs)

    def insert(self, *args, **kwargs):
        self._mark_as_changed()
        return super(BaseList, self).insert(*args, **kwargs)

    def pop(self, *args, **kwargs):
        self._mark_as_changed()
        return super(BaseList, self).pop(*args, **kwargs)

    def remove(self, *args, **kwargs):
        self._mark_as_changed()
        return super(BaseList, self).remove(*args, **kwargs)

    def reverse(self, *args, **kwargs):
        self._mark_as_changed()
        return super(BaseList, self).reverse(*args, **kwargs)

    def sort(self, *args, **kwargs):
        self._mark_as_changed()
        return super(BaseList, self).sort(*args, **kwargs)

    def _mark_as_changed(self):
        if hasattr(self._instance, '_mark_as_changed'):
            self._instance._mark_as_changed(self._name)

########NEW FILE########
__FILENAME__ = document
import copy
import operator
import numbers
from collections import Hashable
from functools import partial

import pymongo
from bson import json_util, ObjectId
from bson.dbref import DBRef
from bson.son import SON

from mongoengine import signals
from mongoengine.common import _import_class
from mongoengine.errors import (ValidationError, InvalidDocumentError,
                                LookUpError)
from mongoengine.python_support import (PY3, UNICODE_KWARGS, txt_type,
                                        to_str_keys_recursive)

from mongoengine.base.common import get_document, ALLOW_INHERITANCE
from mongoengine.base.datastructures import BaseDict, BaseList
from mongoengine.base.fields import ComplexBaseField

__all__ = ('BaseDocument', 'NON_FIELD_ERRORS')

NON_FIELD_ERRORS = '__all__'


class BaseDocument(object):

    _dynamic = False
    _created = True
    _dynamic_lock = True
    _initialised = False

    def __init__(self, *args, **values):
        """
        Initialise a document or embedded document

        :param __auto_convert: Try and will cast python objects to Object types
        :param values: A dictionary of values for the document
        """
        if args:
            # Combine positional arguments with named arguments.
            # We only want named arguments.
            field = iter(self._fields_ordered)
            # If its an automatic id field then skip to the first defined field
            if self._auto_id_field:
                next(field)
            for value in args:
                name = next(field)
                if name in values:
                    raise TypeError("Multiple values for keyword argument '" + name + "'")
                values[name] = value
        __auto_convert = values.pop("__auto_convert", True)
        signals.pre_init.send(self.__class__, document=self, values=values)

        self._data = {}
        self._dynamic_fields = SON()

        # Assign default values to instance
        for key, field in self._fields.iteritems():
            if self._db_field_map.get(key, key) in values:
                continue
            value = getattr(self, key, None)
            setattr(self, key, value)

        # Set passed values after initialisation
        if self._dynamic:
            dynamic_data = {}
            for key, value in values.iteritems():
                if key in self._fields or key == '_id':
                    setattr(self, key, value)
                elif self._dynamic:
                    dynamic_data[key] = value
        else:
            FileField = _import_class('FileField')
            for key, value in values.iteritems():
                if key == '__auto_convert':
                    continue
                key = self._reverse_db_field_map.get(key, key)
                if key in self._fields or key in ('id', 'pk', '_cls'):
                    if __auto_convert and value is not None:
                        field = self._fields.get(key)
                        if field and not isinstance(field, FileField):
                            value = field.to_python(value)
                    setattr(self, key, value)
                else:
                    self._data[key] = value

        # Set any get_fieldname_display methods
        self.__set_field_display()

        if self._dynamic:
            self._dynamic_lock = False
            for key, value in dynamic_data.iteritems():
                setattr(self, key, value)

        # Flag initialised
        self._initialised = True
        signals.post_init.send(self.__class__, document=self)

    def __delattr__(self, *args, **kwargs):
        """Handle deletions of fields"""
        field_name = args[0]
        if field_name in self._fields:
            default = self._fields[field_name].default
            if callable(default):
                default = default()
            setattr(self, field_name, default)
        else:
            super(BaseDocument, self).__delattr__(*args, **kwargs)

    def __setattr__(self, name, value):
        # Handle dynamic data only if an initialised dynamic document
        if self._dynamic and not self._dynamic_lock:

            field = None
            if not hasattr(self, name) and not name.startswith('_'):
                DynamicField = _import_class("DynamicField")
                field = DynamicField(db_field=name)
                field.name = name
                self._dynamic_fields[name] = field
                self._fields_ordered += (name,)

            if not name.startswith('_'):
                value = self.__expand_dynamic_values(name, value)

            # Handle marking data as changed
            if name in self._dynamic_fields:
                self._data[name] = value
                if hasattr(self, '_changed_fields'):
                    self._mark_as_changed(name)

        if (self._is_document and not self._created and
           name in self._meta.get('shard_key', tuple()) and
           self._data.get(name) != value):
            OperationError = _import_class('OperationError')
            msg = "Shard Keys are immutable. Tried to update %s" % name
            raise OperationError(msg)

        # Check if the user has created a new instance of a class
        if (self._is_document and self._initialised
           and self._created and name == self._meta['id_field']):
                super(BaseDocument, self).__setattr__('_created', False)

        super(BaseDocument, self).__setattr__(name, value)

    def __getstate__(self):
        data = {}
        for k in ('_changed_fields', '_initialised', '_created',
                  '_dynamic_fields', '_fields_ordered'):
            if hasattr(self, k):
                data[k] = getattr(self, k)
        data['_data'] = self.to_mongo()
        return data

    def __setstate__(self, data):
        if isinstance(data["_data"], SON):
            data["_data"] = self.__class__._from_son(data["_data"])._data
        for k in ('_changed_fields', '_initialised', '_created', '_data',
                  '_fields_ordered', '_dynamic_fields'):
            if k in data:
                setattr(self, k, data[k])
        dynamic_fields = data.get('_dynamic_fields') or SON()
        for k in dynamic_fields.keys():
            setattr(self, k, data["_data"].get(k))

    def __iter__(self):
        return iter(self._fields_ordered)

    def __getitem__(self, name):
        """Dictionary-style field access, return a field's value if present.
        """
        try:
            if name in self._fields_ordered:
                return getattr(self, name)
        except AttributeError:
            pass
        raise KeyError(name)

    def __setitem__(self, name, value):
        """Dictionary-style field access, set a field's value.
        """
        # Ensure that the field exists before settings its value
        if name not in self._fields:
            raise KeyError(name)
        return setattr(self, name, value)

    def __contains__(self, name):
        try:
            val = getattr(self, name)
            return val is not None
        except AttributeError:
            return False

    def __len__(self):
        return len(self._data)

    def __repr__(self):
        try:
            u = self.__str__()
        except (UnicodeEncodeError, UnicodeDecodeError):
            u = '[Bad Unicode data]'
        repr_type = type(u)
        return repr_type('<%s: %s>' % (self.__class__.__name__, u))

    def __str__(self):
        if hasattr(self, '__unicode__'):
            if PY3:
                return self.__unicode__()
            else:
                return unicode(self).encode('utf-8')
        return txt_type('%s object' % self.__class__.__name__)

    def __eq__(self, other):
        if isinstance(other, self.__class__) and hasattr(other, 'id'):
            if self.id == other.id:
                return True
        return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        if getattr(self, 'pk', None) is None:
            # For new object
            return super(BaseDocument, self).__hash__()
        else:
            return hash(self.pk)

    def clean(self):
        """
        Hook for doing document level data cleaning before validation is run.

        Any ValidationError raised by this method will not be associated with
        a particular field; it will have a special-case association with the
        field defined by NON_FIELD_ERRORS.
        """
        pass

    def to_mongo(self):
        """Return as SON data ready for use with MongoDB.
        """
        data = SON()
        data["_id"] = None
        data['_cls'] = self._class_name

        for field_name in self:
            value = self._data.get(field_name, None)
            field = self._fields.get(field_name)
            if field is None and self._dynamic:
                field = self._dynamic_fields.get(field_name)

            if value is not None:
                value = field.to_mongo(value)

            # Handle self generating fields
            if value is None and field._auto_gen:
                value = field.generate()
                self._data[field_name] = value

            if value is not None:
                data[field.db_field] = value

        # If "_id" has not been set, then try and set it
        Document = _import_class("Document")
        if isinstance(self, Document):
            if data["_id"] is None:
                data["_id"] = self._data.get("id", None)

        if data['_id'] is None:
            data.pop('_id')

        # Only add _cls if allow_inheritance is True
        if (not hasattr(self, '_meta') or
           not self._meta.get('allow_inheritance', ALLOW_INHERITANCE)):
            data.pop('_cls')

        return data

    def validate(self, clean=True):
        """Ensure that all fields' values are valid and that required fields
        are present.
        """
        # Ensure that each field is matched to a valid value
        errors = {}
        if clean:
            try:
                self.clean()
            except ValidationError, error:
                errors[NON_FIELD_ERRORS] = error

        # Get a list of tuples of field names and their current values
        fields = [(self._fields.get(name, self._dynamic_fields.get(name)),
                   self._data.get(name)) for name in self._fields_ordered]

        EmbeddedDocumentField = _import_class("EmbeddedDocumentField")
        GenericEmbeddedDocumentField = _import_class("GenericEmbeddedDocumentField")

        for field, value in fields:
            if value is not None:
                try:
                    if isinstance(field, (EmbeddedDocumentField,
                                          GenericEmbeddedDocumentField)):
                        field._validate(value, clean=clean)
                    else:
                        field._validate(value)
                except ValidationError, error:
                    errors[field.name] = error.errors or error
                except (ValueError, AttributeError, AssertionError), error:
                    errors[field.name] = error
            elif field.required and not getattr(field, '_auto_gen', False):
                errors[field.name] = ValidationError('Field is required',
                                                     field_name=field.name)

        if errors:
            pk = "None"
            if hasattr(self, 'pk'):
                pk = self.pk
            elif self._instance:
                pk = self._instance.pk
            message = "ValidationError (%s:%s) " % (self._class_name, pk)
            raise ValidationError(message, errors=errors)

    def to_json(self, *args, **kwargs):
        """Converts a document to JSON"""
        return json_util.dumps(self.to_mongo(),  *args, **kwargs)

    @classmethod
    def from_json(cls, json_data):
        """Converts json data to an unsaved document instance"""
        return cls._from_son(json_util.loads(json_data))

    def __expand_dynamic_values(self, name, value):
        """expand any dynamic values to their correct types / values"""
        if not isinstance(value, (dict, list, tuple)):
            return value

        is_list = False
        if not hasattr(value, 'items'):
            is_list = True
            value = dict([(k, v) for k, v in enumerate(value)])

        if not is_list and '_cls' in value:
            cls = get_document(value['_cls'])
            return cls(**value)

        data = {}
        for k, v in value.items():
            key = name if is_list else k
            data[k] = self.__expand_dynamic_values(key, v)

        if is_list:  # Convert back to a list
            data_items = sorted(data.items(), key=operator.itemgetter(0))
            value = [v for k, v in data_items]
        else:
            value = data

        # Convert lists / values so we can watch for any changes on them
        if (isinstance(value, (list, tuple)) and
           not isinstance(value, BaseList)):
            value = BaseList(value, self, name)
        elif isinstance(value, dict) and not isinstance(value, BaseDict):
            value = BaseDict(value, self, name)

        return value

    def _mark_as_changed(self, key):
        """Marks a key as explicitly changed by the user
        """
        if not key:
            return
        key = self._db_field_map.get(key, key)
        if (hasattr(self, '_changed_fields') and
           key not in self._changed_fields):
            self._changed_fields.append(key)

    def _clear_changed_fields(self):
        """Using get_changed_fields iterate and remove any fields that are
        marked as changed"""
        for changed in self._get_changed_fields():
            parts = changed.split(".")
            data = self
            for part in parts:
                if isinstance(data, list):
                    try:
                        data = data[int(part)]
                    except IndexError:
                        data = None
                elif isinstance(data, dict):
                    data = data.get(part, None)
                else:
                    data = getattr(data, part, None)
                if hasattr(data, "_changed_fields"):
                    data._changed_fields = []
        self._changed_fields = []

    def _nestable_types_changed_fields(self, changed_fields, key, data, inspected):
        # Loop list / dict fields as they contain documents
        # Determine the iterator to use
        if not hasattr(data, 'items'):
            iterator = enumerate(data)
        else:
            iterator = data.iteritems()

        for index, value in iterator:
            list_key = "%s%s." % (key, index)
            if hasattr(value, '_get_changed_fields'):
                changed = value._get_changed_fields(inspected)
                changed_fields += ["%s%s" % (list_key, k)
                                    for k in changed if k]
            elif isinstance(value, (list, tuple, dict)):
                self._nestable_types_changed_fields(changed_fields, list_key, value, inspected)

    def _get_changed_fields(self, inspected=None):
        """Returns a list of all fields that have explicitly been changed.
        """
        EmbeddedDocument = _import_class("EmbeddedDocument")
        DynamicEmbeddedDocument = _import_class("DynamicEmbeddedDocument")
        ReferenceField = _import_class("ReferenceField")
        changed_fields = []
        changed_fields += getattr(self, '_changed_fields', [])
        inspected = inspected or set()
        if hasattr(self, 'id') and isinstance(self.id, Hashable):
            if self.id in inspected:
                return changed_fields
            inspected.add(self.id)

        for field_name in self._fields_ordered:
            db_field_name = self._db_field_map.get(field_name, field_name)
            key = '%s.' % db_field_name
            data = self._data.get(field_name, None)
            field = self._fields.get(field_name)

            if hasattr(data, 'id'):
                if data.id in inspected:
                    continue
                inspected.add(data.id)
            if isinstance(field, ReferenceField):
                continue
            elif (isinstance(data, (EmbeddedDocument, DynamicEmbeddedDocument))
               and db_field_name not in changed_fields):
                 # Find all embedded fields that have been changed
                changed = data._get_changed_fields(inspected)
                changed_fields += ["%s%s" % (key, k) for k in changed if k]
            elif (isinstance(data, (list, tuple, dict)) and
                    db_field_name not in changed_fields):
                if (hasattr(field, 'field') and
                    isinstance(field.field, ReferenceField)):
                    continue
                self._nestable_types_changed_fields(changed_fields, key, data, inspected)
        return changed_fields

    def _delta(self):
        """Returns the delta (set, unset) of the changes for a document.
        Gets any values that have been explicitly changed.
        """
        # Handles cases where not loaded from_son but has _id
        doc = self.to_mongo()

        set_fields = self._get_changed_fields()
        unset_data = {}
        parts = []
        if hasattr(self, '_changed_fields'):
            set_data = {}
            # Fetch each set item from its path
            for path in set_fields:
                parts = path.split('.')
                d = doc
                new_path = []
                for p in parts:
                    if isinstance(d, (ObjectId, DBRef)):
                        break
                    elif isinstance(d, list) and p.isdigit():
                        d = d[int(p)]
                    elif hasattr(d, 'get'):
                        d = d.get(p)
                    new_path.append(p)
                path = '.'.join(new_path)
                set_data[path] = d
        else:
            set_data = doc
            if '_id' in set_data:
                del(set_data['_id'])

        # Determine if any changed items were actually unset.
        for path, value in set_data.items():
            if value or isinstance(value, (numbers.Number, bool)):
                continue

            # If we've set a value that ain't the default value dont unset it.
            default = None
            if (self._dynamic and len(parts) and parts[0] in
               self._dynamic_fields):
                del(set_data[path])
                unset_data[path] = 1
                continue
            elif path in self._fields:
                default = self._fields[path].default
            else:  # Perform a full lookup for lists / embedded lookups
                d = self
                parts = path.split('.')
                db_field_name = parts.pop()
                for p in parts:
                    if isinstance(d, list) and p.isdigit():
                        d = d[int(p)]
                    elif (hasattr(d, '__getattribute__') and
                          not isinstance(d, dict)):
                        real_path = d._reverse_db_field_map.get(p, p)
                        d = getattr(d, real_path)
                    else:
                        d = d.get(p)

                if hasattr(d, '_fields'):
                    field_name = d._reverse_db_field_map.get(db_field_name,
                                                             db_field_name)
                    if field_name in d._fields:
                        default = d._fields.get(field_name).default
                    else:
                        default = None

            if default is not None:
                if callable(default):
                    default = default()

            if default != value:
                continue

            del(set_data[path])
            unset_data[path] = 1
        return set_data, unset_data

    @classmethod
    def _get_collection_name(cls):
        """Returns the collection name for this class.
        """
        return cls._meta.get('collection', None)

    @classmethod
    def _from_son(cls, son, _auto_dereference=True):
        """Create an instance of a Document (subclass) from a PyMongo SON.
        """

        # get the class name from the document, falling back to the given
        # class if unavailable
        class_name = son.get('_cls', cls._class_name)
        data = dict(("%s" % key, value) for key, value in son.iteritems())
        if not UNICODE_KWARGS:
            # python 2.6.4 and lower cannot handle unicode keys
            # passed to class constructor example: cls(**data)
            to_str_keys_recursive(data)

        # Return correct subclass for document type
        if class_name != cls._class_name:
            cls = get_document(class_name)

        changed_fields = []
        errors_dict = {}

        fields = cls._fields
        if not _auto_dereference:
            fields = copy.copy(fields)

        for field_name, field in fields.iteritems():
            field._auto_dereference = _auto_dereference
            if field.db_field in data:
                value = data[field.db_field]
                try:
                    data[field_name] = (value if value is None
                                        else field.to_python(value))
                    if field_name != field.db_field:
                        del data[field.db_field]
                except (AttributeError, ValueError), e:
                    errors_dict[field_name] = e
            elif field.default:
                default = field.default
                if callable(default):
                    default = default()
                if isinstance(default, BaseDocument):
                    changed_fields.append(field_name)

        if errors_dict:
            errors = "\n".join(["%s - %s" % (k, v)
                     for k, v in errors_dict.items()])
            msg = ("Invalid data to create a `%s` instance.\n%s"
                   % (cls._class_name, errors))
            raise InvalidDocumentError(msg)

        obj = cls(__auto_convert=False, **data)
        obj._changed_fields = changed_fields
        obj._created = False
        if not _auto_dereference:
            obj._fields = fields
        return obj

    @classmethod
    def _build_index_specs(cls, meta_indexes):
        """Generate and merge the full index specs
        """

        geo_indices = cls._geo_indices()
        unique_indices = cls._unique_with_indexes()
        index_specs = [cls._build_index_spec(spec)
                       for spec in meta_indexes]

        def merge_index_specs(index_specs, indices):
            if not indices:
                return index_specs

            spec_fields = [v['fields']
                           for k, v in enumerate(index_specs)]
            # Merge unqiue_indexes with existing specs
            for k, v in enumerate(indices):
                if v['fields'] in spec_fields:
                    index_specs[spec_fields.index(v['fields'])].update(v)
                else:
                    index_specs.append(v)
            return index_specs

        index_specs = merge_index_specs(index_specs, geo_indices)
        index_specs = merge_index_specs(index_specs, unique_indices)
        return index_specs

    @classmethod
    def _build_index_spec(cls, spec):
        """Build a PyMongo index spec from a MongoEngine index spec.
        """
        if isinstance(spec, basestring):
            spec = {'fields': [spec]}
        elif isinstance(spec, (list, tuple)):
            spec = {'fields': list(spec)}
        elif isinstance(spec, dict):
            spec = dict(spec)

        index_list = []
        direction = None

        # Check to see if we need to include _cls
        allow_inheritance = cls._meta.get('allow_inheritance',
                                          ALLOW_INHERITANCE)
        include_cls = (allow_inheritance and not spec.get('sparse', False) and
                       spec.get('cls',  True))
        if "cls" in spec:
            spec.pop('cls')
        for key in spec['fields']:
            # If inherited spec continue
            if isinstance(key, (list, tuple)):
                continue

            # ASCENDING from +,
            # DESCENDING from -
            # GEO2D from *
            direction = pymongo.ASCENDING
            if key.startswith("-"):
                direction = pymongo.DESCENDING
            elif key.startswith("*"):
                direction = pymongo.GEO2D
            if key.startswith(("+", "-", "*")):
                key = key[1:]

            # Use real field name, do it manually because we need field
            # objects for the next part (list field checking)
            parts = key.split('.')
            if parts in (['pk'], ['id'], ['_id']):
                key = '_id'
                fields = []
            else:
                fields = cls._lookup_field(parts)
                parts = [field if field == '_id' else field.db_field
                         for field in fields]
                key = '.'.join(parts)
            index_list.append((key, direction))

        # Don't add cls to a geo index
        if include_cls and direction is not pymongo.GEO2D:
            index_list.insert(0, ('_cls', 1))

        if index_list:
            spec['fields'] = index_list
        if spec.get('sparse', False) and len(spec['fields']) > 1:
            raise ValueError(
                'Sparse indexes can only have one field in them. '
                'See https://jira.mongodb.org/browse/SERVER-2193')

        return spec

    @classmethod
    def _unique_with_indexes(cls, namespace=""):
        """
        Find and set unique indexes
        """
        unique_indexes = []
        for field_name, field in cls._fields.items():
            sparse = False
            # Generate a list of indexes needed by uniqueness constraints
            if field.unique:
                field.required = True
                unique_fields = [field.db_field]

                # Add any unique_with fields to the back of the index spec
                if field.unique_with:
                    if isinstance(field.unique_with, basestring):
                        field.unique_with = [field.unique_with]

                    # Convert unique_with field names to real field names
                    unique_with = []
                    for other_name in field.unique_with:
                        parts = other_name.split('.')
                        # Lookup real name
                        parts = cls._lookup_field(parts)
                        name_parts = [part.db_field for part in parts]
                        unique_with.append('.'.join(name_parts))
                        # Unique field should be required
                        parts[-1].required = True
                        sparse = (not sparse and
                                  parts[-1].name not in cls.__dict__)
                    unique_fields += unique_with

                # Add the new index to the list
                fields = [("%s%s" % (namespace, f), pymongo.ASCENDING)
                          for f in unique_fields]
                index = {'fields': fields, 'unique': True, 'sparse': sparse}
                unique_indexes.append(index)

            # Grab any embedded document field unique indexes
            if (field.__class__.__name__ == "EmbeddedDocumentField" and
               field.document_type != cls):
                field_namespace = "%s." % field_name
                doc_cls = field.document_type
                unique_indexes += doc_cls._unique_with_indexes(field_namespace)

        return unique_indexes

    @classmethod
    def _geo_indices(cls, inspected=None, parent_field=None):
        inspected = inspected or []
        geo_indices = []
        inspected.append(cls)

        geo_field_type_names = ["EmbeddedDocumentField", "GeoPointField",
                                "PointField", "LineStringField", "PolygonField"]

        geo_field_types = tuple([_import_class(field) for field in geo_field_type_names])

        for field in cls._fields.values():
            if not isinstance(field, geo_field_types):
                continue
            if hasattr(field, 'document_type'):
                field_cls = field.document_type
                if field_cls in inspected:
                    continue
                if hasattr(field_cls, '_geo_indices'):
                    geo_indices += field_cls._geo_indices(inspected, parent_field=field.db_field)
            elif field._geo_index:
                field_name = field.db_field
                if parent_field:
                    field_name = "%s.%s" % (parent_field, field_name)
                geo_indices.append({'fields':
                                   [(field_name, field._geo_index)]})
        return geo_indices

    @classmethod
    def _lookup_field(cls, parts):
        """Lookup a field based on its attribute and return a list containing
        the field's parents and the field.
        """

        ListField = _import_class("ListField")

        if not isinstance(parts, (list, tuple)):
            parts = [parts]
        fields = []
        field = None

        for field_name in parts:
            # Handle ListField indexing:
            if field_name.isdigit() and isinstance(field, ListField):
                new_field = field.field
                fields.append(field_name)
                continue

            if field is None:
                # Look up first field from the document
                if field_name == 'pk':
                    # Deal with "primary key" alias
                    field_name = cls._meta['id_field']
                if field_name in cls._fields:
                    field = cls._fields[field_name]
                elif cls._dynamic:
                    DynamicField = _import_class('DynamicField')
                    field = DynamicField(db_field=field_name)
                else:
                    raise LookUpError('Cannot resolve field "%s"'
                                      % field_name)
            else:
                ReferenceField = _import_class('ReferenceField')
                GenericReferenceField = _import_class('GenericReferenceField')
                if isinstance(field, (ReferenceField, GenericReferenceField)):
                    raise LookUpError('Cannot perform join in mongoDB: %s' %
                                      '__'.join(parts))
                if hasattr(getattr(field, 'field', None), 'lookup_member'):
                    new_field = field.field.lookup_member(field_name)
                else:
                   # Look up subfield on the previous field
                    new_field = field.lookup_member(field_name)
                if not new_field and isinstance(field, ComplexBaseField):
                    fields.append(field_name)
                    continue
                elif not new_field:
                    raise LookUpError('Cannot resolve field "%s"'
                                      % field_name)
                field = new_field  # update field to the new field type
            fields.append(field)
        return fields

    @classmethod
    def _translate_field_name(cls, field, sep='.'):
        """Translate a field attribute name to a database field name.
        """
        parts = field.split(sep)
        parts = [f.db_field for f in cls._lookup_field(parts)]
        return '.'.join(parts)

    def __set_field_display(self):
        """Dynamically set the display value for a field with choices"""
        for attr_name, field in self._fields.items():
            if field.choices:
                setattr(self,
                        'get_%s_display' % attr_name,
                        partial(self.__get_field_display, field=field))

    def __get_field_display(self, field):
        """Returns the display value for a choice field"""
        value = getattr(self, field.name)
        if field.choices and isinstance(field.choices[0], (list, tuple)):
            return dict(field.choices).get(value, value)
        return value

########NEW FILE########
__FILENAME__ = fields
import operator
import warnings
import weakref

from bson import DBRef, ObjectId, SON
import pymongo

from mongoengine.common import _import_class
from mongoengine.errors import ValidationError

from mongoengine.base.common import ALLOW_INHERITANCE
from mongoengine.base.datastructures import BaseDict, BaseList

__all__ = ("BaseField", "ComplexBaseField", "ObjectIdField", "GeoJsonBaseField")


class BaseField(object):
    """A base class for fields in a MongoDB document. Instances of this class
    may be added to subclasses of `Document` to define a document's schema.

    .. versionchanged:: 0.5 - added verbose and help text
    """

    name = None
    _geo_index = False
    _auto_gen = False  # Call `generate` to generate a value
    _auto_dereference = True

    # These track each time a Field instance is created. Used to retain order.
    # The auto_creation_counter is used for fields that MongoEngine implicitly
    # creates, creation_counter is used for all user-specified fields.
    creation_counter = 0
    auto_creation_counter = -1

    def __init__(self, db_field=None, name=None, required=False, default=None,
                 unique=False, unique_with=None, primary_key=False,
                 validation=None, choices=None, verbose_name=None,
                 help_text=None):
        """
        :param db_field: The database field to store this field in
            (defaults to the name of the field)
        :param name: Depreciated - use db_field
        :param required: If the field is required. Whether it has to have a
            value or not. Defaults to False.
        :param default: (optional) The default value for this field if no value
            has been set (or if the value has been unset).  It Can be a
            callable.
        :param unique: Is the field value unique or not.  Defaults to False.
        :param unique_with: (optional) The other field this field should be
            unique with.
        :param primary_key: Mark this field as the primary key. Defaults to False.
        :param validation: (optional) A callable to validate the value of the
            field.  Generally this is deprecated in favour of the
            `FIELD.validate` method
        :param choices: (optional) The valid choices
        :param verbose_name: (optional)  The verbose name for the field.
            Designed to be human readable and is often used when generating
            model forms from the document model.
        :param help_text: (optional) The help text for this field and is often
            used when generating model forms from the document model.
        """
        self.db_field = (db_field or name) if not primary_key else '_id'
        if name:
            msg = "Fields' 'name' attribute deprecated in favour of 'db_field'"
            warnings.warn(msg, DeprecationWarning)
        self.required = required or primary_key
        self.default = default
        self.unique = bool(unique or unique_with)
        self.unique_with = unique_with
        self.primary_key = primary_key
        self.validation = validation
        self.choices = choices
        self.verbose_name = verbose_name
        self.help_text = help_text

        # Adjust the appropriate creation counter, and save our local copy.
        if self.db_field == '_id':
            self.creation_counter = BaseField.auto_creation_counter
            BaseField.auto_creation_counter -= 1
        else:
            self.creation_counter = BaseField.creation_counter
            BaseField.creation_counter += 1

    def __get__(self, instance, owner):
        """Descriptor for retrieving a value from a field in a document.
        """
        if instance is None:
            # Document class being used rather than a document object
            return self

        # Get value from document instance if available
        return instance._data.get(self.name)

    def __set__(self, instance, value):
        """Descriptor for assigning a value to a field in a document.
        """

        # If setting to None and theres a default
        # Then set the value to the default value
        if value is None and self.default is not None:
            value = self.default
            if callable(value):
                value = value()

        if instance._initialised:
            try:
                if (self.name not in instance._data or
                   instance._data[self.name] != value):
                    instance._mark_as_changed(self.name)
            except:
                # Values cant be compared eg: naive and tz datetimes
                # So mark it as changed
                instance._mark_as_changed(self.name)

        EmbeddedDocument = _import_class('EmbeddedDocument')
        if isinstance(value, EmbeddedDocument) and value._instance is None:
            value._instance = weakref.proxy(instance)
        instance._data[self.name] = value

    def error(self, message="", errors=None, field_name=None):
        """Raises a ValidationError.
        """
        field_name = field_name if field_name else self.name
        raise ValidationError(message, errors=errors, field_name=field_name)

    def to_python(self, value):
        """Convert a MongoDB-compatible type to a Python type.
        """
        return value

    def to_mongo(self, value):
        """Convert a Python type to a MongoDB-compatible type.
        """
        return self.to_python(value)

    def prepare_query_value(self, op, value):
        """Prepare a value that is being used in a query for PyMongo.
        """
        return value

    def validate(self, value, clean=True):
        """Perform validation on a value.
        """
        pass

    def _validate(self, value, **kwargs):
        Document = _import_class('Document')
        EmbeddedDocument = _import_class('EmbeddedDocument')
        # check choices
        if self.choices:
            is_cls = isinstance(value, (Document, EmbeddedDocument))
            value_to_check = value.__class__ if is_cls else value
            err_msg = 'an instance' if is_cls else 'one'
            if isinstance(self.choices[0], (list, tuple)):
                option_keys = [k for k, v in self.choices]
                if value_to_check not in option_keys:
                    msg = ('Value must be %s of %s' %
                           (err_msg, unicode(option_keys)))
                    self.error(msg)
            elif value_to_check not in self.choices:
                msg = ('Value must be %s of %s' %
                       (err_msg, unicode(self.choices)))
                self.error(msg)

        # check validation argument
        if self.validation is not None:
            if callable(self.validation):
                if not self.validation(value):
                    self.error('Value does not match custom validation method')
            else:
                raise ValueError('validation argument for "%s" must be a '
                                 'callable.' % self.name)

        self.validate(value, **kwargs)


class ComplexBaseField(BaseField):
    """Handles complex fields, such as lists / dictionaries.

    Allows for nesting of embedded documents inside complex types.
    Handles the lazy dereferencing of a queryset by lazily dereferencing all
    items in a list / dict rather than one at a time.

    .. versionadded:: 0.5
    """

    field = None

    def __get__(self, instance, owner):
        """Descriptor to automatically dereference references.
        """
        if instance is None:
            # Document class being used rather than a document object
            return self

        ReferenceField = _import_class('ReferenceField')
        GenericReferenceField = _import_class('GenericReferenceField')
        dereference = (self._auto_dereference and
                       (self.field is None or isinstance(self.field,
                        (GenericReferenceField, ReferenceField))))

        _dereference = _import_class("DeReference")()

        self._auto_dereference = instance._fields[self.name]._auto_dereference
        if instance._initialised and dereference and instance._data.get(self.name):
            instance._data[self.name] = _dereference(
                instance._data.get(self.name), max_depth=1, instance=instance,
                name=self.name
            )

        value = super(ComplexBaseField, self).__get__(instance, owner)

        # Convert lists / values so we can watch for any changes on them
        if (isinstance(value, (list, tuple)) and
           not isinstance(value, BaseList)):
            value = BaseList(value, instance, self.name)
            instance._data[self.name] = value
        elif isinstance(value, dict) and not isinstance(value, BaseDict):
            value = BaseDict(value, instance, self.name)
            instance._data[self.name] = value

        if (self._auto_dereference and instance._initialised and
           isinstance(value, (BaseList, BaseDict))
           and not value._dereferenced):
            value = _dereference(
                value, max_depth=1, instance=instance, name=self.name
            )
            value._dereferenced = True
            instance._data[self.name] = value

        return value

    def to_python(self, value):
        """Convert a MongoDB-compatible type to a Python type.
        """
        Document = _import_class('Document')

        if isinstance(value, basestring):
            return value

        if hasattr(value, 'to_python'):
            return value.to_python()

        is_list = False
        if not hasattr(value, 'items'):
            try:
                is_list = True
                value = dict([(k, v) for k, v in enumerate(value)])
            except TypeError:  # Not iterable return the value
                return value

        if self.field:
            value_dict = dict([(key, self.field.to_python(item))
                               for key, item in value.items()])
        else:
            value_dict = {}
            for k, v in value.items():
                if isinstance(v, Document):
                    # We need the id from the saved object to create the DBRef
                    if v.pk is None:
                        self.error('You can only reference documents once they'
                                   ' have been saved to the database')
                    collection = v._get_collection_name()
                    value_dict[k] = DBRef(collection, v.pk)
                elif hasattr(v, 'to_python'):
                    value_dict[k] = v.to_python()
                else:
                    value_dict[k] = self.to_python(v)

        if is_list:  # Convert back to a list
            return [v for k, v in sorted(value_dict.items(),
                                         key=operator.itemgetter(0))]
        return value_dict

    def to_mongo(self, value):
        """Convert a Python type to a MongoDB-compatible type.
        """
        Document = _import_class("Document")
        EmbeddedDocument = _import_class("EmbeddedDocument")
        GenericReferenceField = _import_class("GenericReferenceField")

        if isinstance(value, basestring):
            return value

        if hasattr(value, 'to_mongo'):
            if isinstance(value, Document):
                return GenericReferenceField().to_mongo(value)
            cls = value.__class__
            val = value.to_mongo()
            # If we its a document thats not inherited add _cls
            if (isinstance(value, EmbeddedDocument)):
                val['_cls'] = cls.__name__
            return val

        is_list = False
        if not hasattr(value, 'items'):
            try:
                is_list = True
                value = dict([(k, v) for k, v in enumerate(value)])
            except TypeError:  # Not iterable return the value
                return value

        if self.field:
            value_dict = dict([(key, self.field.to_mongo(item))
                               for key, item in value.iteritems()])
        else:
            value_dict = {}
            for k, v in value.iteritems():
                if isinstance(v, Document):
                    # We need the id from the saved object to create the DBRef
                    if v.pk is None:
                        self.error('You can only reference documents once they'
                                   ' have been saved to the database')

                    # If its a document that is not inheritable it won't have
                    # any _cls data so make it a generic reference allows
                    # us to dereference
                    meta = getattr(v, '_meta', {})
                    allow_inheritance = (
                        meta.get('allow_inheritance', ALLOW_INHERITANCE)
                        is True)
                    if not allow_inheritance and not self.field:
                        value_dict[k] = GenericReferenceField().to_mongo(v)
                    else:
                        collection = v._get_collection_name()
                        value_dict[k] = DBRef(collection, v.pk)
                elif hasattr(v, 'to_mongo'):
                    cls = v.__class__
                    val = v.to_mongo()
                    # If we its a document thats not inherited add _cls
                    if (isinstance(v, (Document, EmbeddedDocument))):
                        val['_cls'] = cls.__name__
                    value_dict[k] = val
                else:
                    value_dict[k] = self.to_mongo(v)

        if is_list:  # Convert back to a list
            return [v for k, v in sorted(value_dict.items(),
                                         key=operator.itemgetter(0))]
        return value_dict

    def validate(self, value):
        """If field is provided ensure the value is valid.
        """
        errors = {}
        if self.field:
            if hasattr(value, 'iteritems') or hasattr(value, 'items'):
                sequence = value.iteritems()
            else:
                sequence = enumerate(value)
            for k, v in sequence:
                try:
                    self.field._validate(v)
                except ValidationError, error:
                    errors[k] = error.errors or error
                except (ValueError, AssertionError), error:
                    errors[k] = error

            if errors:
                field_class = self.field.__class__.__name__
                self.error('Invalid %s item (%s)' % (field_class, value),
                           errors=errors)
        # Don't allow empty values if required
        if self.required and not value:
            self.error('Field is required and cannot be empty')

    def prepare_query_value(self, op, value):
        return self.to_mongo(value)

    def lookup_member(self, member_name):
        if self.field:
            return self.field.lookup_member(member_name)
        return None

    def _set_owner_document(self, owner_document):
        if self.field:
            self.field.owner_document = owner_document
        self._owner_document = owner_document

    def _get_owner_document(self, owner_document):
        self._owner_document = owner_document

    owner_document = property(_get_owner_document, _set_owner_document)


class ObjectIdField(BaseField):
    """A field wrapper around MongoDB's ObjectIds.
    """

    def to_python(self, value):
        if not isinstance(value, ObjectId):
            value = ObjectId(value)
        return value

    def to_mongo(self, value):
        if not isinstance(value, ObjectId):
            try:
                return ObjectId(unicode(value))
            except Exception, e:
                # e.message attribute has been deprecated since Python 2.6
                self.error(unicode(e))
        return value

    def prepare_query_value(self, op, value):
        return self.to_mongo(value)

    def validate(self, value):
        try:
            ObjectId(unicode(value))
        except:
            self.error('Invalid Object ID')


class GeoJsonBaseField(BaseField):
    """A geo json field storing a geojson style object.
    .. versionadded:: 0.8
    """

    _geo_index = pymongo.GEOSPHERE
    _type = "GeoBase"

    def __init__(self, auto_index=True, *args, **kwargs):
        """
        :param auto_index: Automatically create a "2dsphere" index. Defaults
            to `True`.
        """
        self._name = "%sField" % self._type
        if not auto_index:
            self._geo_index = False
        super(GeoJsonBaseField, self).__init__(*args, **kwargs)

    def validate(self, value):
        """Validate the GeoJson object based on its type
        """
        if isinstance(value, dict):
            if set(value.keys()) == set(['type', 'coordinates']):
                if value['type'] != self._type:
                    self.error('%s type must be "%s"' % (self._name, self._type))
                return self.validate(value['coordinates'])
            else:
                self.error('%s can only accept a valid GeoJson dictionary'
                           ' or lists of (x, y)' % self._name)
                return
        elif not isinstance(value, (list, tuple)):
            self.error('%s can only accept lists of [x, y]' % self._name)
            return

        validate = getattr(self, "_validate_%s" % self._type.lower())
        error = validate(value)
        if error:
            self.error(error)

    def _validate_polygon(self, value):
        if not isinstance(value, (list, tuple)):
            return 'Polygons must contain list of linestrings'

        # Quick and dirty validator
        try:
            value[0][0][0]
        except:
            return "Invalid Polygon must contain at least one valid linestring"

        errors = []
        for val in value:
            error = self._validate_linestring(val, False)
            if not error and val[0] != val[-1]:
                error = 'LineStrings must start and end at the same point'
            if error and error not in errors:
                errors.append(error)
        if errors:
            return "Invalid Polygon:\n%s" % ", ".join(errors)

    def _validate_linestring(self, value, top_level=True):
        """Validates a linestring"""
        if not isinstance(value, (list, tuple)):
            return 'LineStrings must contain list of coordinate pairs'

        # Quick and dirty validator
        try:
            value[0][0]
        except:
            return "Invalid LineString must contain at least one valid point"

        errors = []
        for val in value:
            error = self._validate_point(val)
            if error and error not in errors:
                errors.append(error)
        if errors:
            if top_level:
                return "Invalid LineString:\n%s" % ", ".join(errors)
            else:
                return "%s" % ", ".join(errors)

    def _validate_point(self, value):
        """Validate each set of coords"""
        if not isinstance(value, (list, tuple)):
            return 'Points must be a list of coordinate pairs'
        elif not len(value) == 2:
            return "Value (%s) must be a two-dimensional point" % repr(value)
        elif (not isinstance(value[0], (float, int)) or
              not isinstance(value[1], (float, int))):
            return "Both values (%s) in point must be float or int" % repr(value)

    def to_mongo(self, value):
        if isinstance(value, dict):
            return value
        return SON([("type", self._type), ("coordinates", value)])

########NEW FILE########
__FILENAME__ = metaclasses
import warnings

import pymongo

from mongoengine.common import _import_class
from mongoengine.errors import InvalidDocumentError
from mongoengine.python_support import PY3
from mongoengine.queryset import (DO_NOTHING, DoesNotExist,
                                  MultipleObjectsReturned,
                                  QuerySet, QuerySetManager)

from mongoengine.base.common import _document_registry, ALLOW_INHERITANCE
from mongoengine.base.fields import BaseField, ComplexBaseField, ObjectIdField

__all__ = ('DocumentMetaclass', 'TopLevelDocumentMetaclass')


class DocumentMetaclass(type):
    """Metaclass for all documents.
    """

    def __new__(cls, name, bases, attrs):
        flattened_bases = cls._get_bases(bases)
        super_new = super(DocumentMetaclass, cls).__new__

        # If a base class just call super
        metaclass = attrs.get('my_metaclass')
        if metaclass and issubclass(metaclass, DocumentMetaclass):
            return super_new(cls, name, bases, attrs)

        attrs['_is_document'] = attrs.get('_is_document', False)

        # EmbeddedDocuments could have meta data for inheritance
        if 'meta' in attrs:
            attrs['_meta'] = attrs.pop('meta')

        # EmbeddedDocuments should inherit meta data
        if '_meta' not in attrs:
            meta = MetaDict()
            for base in flattened_bases[::-1]:
                # Add any mixin metadata from plain objects
                if hasattr(base, 'meta'):
                    meta.merge(base.meta)
                elif hasattr(base, '_meta'):
                    meta.merge(base._meta)
            attrs['_meta'] = meta

        # Handle document Fields

        # Merge all fields from subclasses
        doc_fields = {}
        for base in flattened_bases[::-1]:
            if hasattr(base, '_fields'):
                doc_fields.update(base._fields)

            # Standard object mixin - merge in any Fields
            if not hasattr(base, '_meta'):
                base_fields = {}
                for attr_name, attr_value in base.__dict__.iteritems():
                    if not isinstance(attr_value, BaseField):
                        continue
                    attr_value.name = attr_name
                    if not attr_value.db_field:
                        attr_value.db_field = attr_name
                    base_fields[attr_name] = attr_value

                doc_fields.update(base_fields)

        # Discover any document fields
        field_names = {}
        for attr_name, attr_value in attrs.iteritems():
            if not isinstance(attr_value, BaseField):
                continue
            attr_value.name = attr_name
            if not attr_value.db_field:
                attr_value.db_field = attr_name
            doc_fields[attr_name] = attr_value

            # Count names to ensure no db_field redefinitions
            field_names[attr_value.db_field] = field_names.get(
                attr_value.db_field, 0) + 1

        # Ensure no duplicate db_fields
        duplicate_db_fields = [k for k, v in field_names.items() if v > 1]
        if duplicate_db_fields:
            msg = ("Multiple db_fields defined for: %s " %
                   ", ".join(duplicate_db_fields))
            raise InvalidDocumentError(msg)

        # Set _fields and db_field maps
        attrs['_fields'] = doc_fields
        attrs['_db_field_map'] = dict([(k, getattr(v, 'db_field', k))
                                      for k, v in doc_fields.iteritems()])
        attrs['_reverse_db_field_map'] = dict(
            (v, k) for k, v in attrs['_db_field_map'].iteritems())

        attrs['_fields_ordered'] = tuple(i[1] for i in sorted(
                                         (v.creation_counter, v.name)
                                         for v in doc_fields.itervalues()))

        #
        # Set document hierarchy
        #
        superclasses = ()
        class_name = [name]
        for base in flattened_bases:
            if (not getattr(base, '_is_base_cls', True) and
               not getattr(base, '_meta', {}).get('abstract', True)):
                # Collate heirarchy for _cls and _subclasses
                class_name.append(base.__name__)

            if hasattr(base, '_meta'):
                # Warn if allow_inheritance isn't set and prevent
                # inheritance of classes where inheritance is set to False
                allow_inheritance = base._meta.get('allow_inheritance',
                                                   ALLOW_INHERITANCE)
                if (allow_inheritance is not True and
                   not base._meta.get('abstract')):
                    raise ValueError('Document %s may not be subclassed' %
                                     base.__name__)

        # Get superclasses from last base superclass
        document_bases = [b for b in flattened_bases
                          if hasattr(b, '_class_name')]
        if document_bases:
            superclasses = document_bases[0]._superclasses
            superclasses += (document_bases[0]._class_name, )

        _cls = '.'.join(reversed(class_name))
        attrs['_class_name'] = _cls
        attrs['_superclasses'] = superclasses
        attrs['_subclasses'] = (_cls, )
        attrs['_types'] = attrs['_subclasses']  # TODO depreciate _types

        # Create the new_class
        new_class = super_new(cls, name, bases, attrs)

        # Set _subclasses
        for base in document_bases:
            if _cls not in base._subclasses:
                base._subclasses += (_cls,)
            base._types = base._subclasses   # TODO depreciate _types

        Document, EmbeddedDocument, DictField = cls._import_classes()

        if issubclass(new_class, Document):
            new_class._collection = None

        # Add class to the _document_registry
        _document_registry[new_class._class_name] = new_class

        # In Python 2, User-defined methods objects have special read-only
        # attributes 'im_func' and 'im_self' which contain the function obj
        # and class instance object respectively.  With Python 3 these special
        # attributes have been replaced by __func__ and __self__.  The Blinker
        # module continues to use im_func and im_self, so the code below
        # copies __func__ into im_func and __self__ into im_self for
        # classmethod objects in Document derived classes.
        if PY3:
            for key, val in new_class.__dict__.items():
                if isinstance(val, classmethod):
                    f = val.__get__(new_class)
                    if hasattr(f, '__func__') and not hasattr(f, 'im_func'):
                        f.__dict__.update({'im_func': getattr(f, '__func__')})
                    if hasattr(f, '__self__') and not hasattr(f, 'im_self'):
                        f.__dict__.update({'im_self': getattr(f, '__self__')})

        # Handle delete rules
        for field in new_class._fields.itervalues():
            f = field
            f.owner_document = new_class
            delete_rule = getattr(f, 'reverse_delete_rule', DO_NOTHING)
            if isinstance(f, ComplexBaseField) and hasattr(f, 'field'):
                delete_rule = getattr(f.field,
                                      'reverse_delete_rule',
                                      DO_NOTHING)
                if isinstance(f, DictField) and delete_rule != DO_NOTHING:
                    msg = ("Reverse delete rules are not supported "
                           "for %s (field: %s)" %
                           (field.__class__.__name__, field.name))
                    raise InvalidDocumentError(msg)

                f = field.field

            if delete_rule != DO_NOTHING:
                if issubclass(new_class, EmbeddedDocument):
                    msg = ("Reverse delete rules are not supported for "
                           "EmbeddedDocuments (field: %s)" % field.name)
                    raise InvalidDocumentError(msg)
                f.document_type.register_delete_rule(new_class,
                                                     field.name, delete_rule)

            if (field.name and hasattr(Document, field.name) and
               EmbeddedDocument not in new_class.mro()):
                msg = ("%s is a document method and not a valid "
                       "field name" % field.name)
                raise InvalidDocumentError(msg)

        return new_class

    def add_to_class(self, name, value):
        setattr(self, name, value)

    @classmethod
    def _get_bases(cls, bases):
        if isinstance(bases, BasesTuple):
            return bases
        seen = []
        bases = cls.__get_bases(bases)
        unique_bases = (b for b in bases if not (b in seen or seen.append(b)))
        return BasesTuple(unique_bases)

    @classmethod
    def __get_bases(cls, bases):
        for base in bases:
            if base is object:
                continue
            yield base
            for child_base in cls.__get_bases(base.__bases__):
                yield child_base

    @classmethod
    def _import_classes(cls):
        Document = _import_class('Document')
        EmbeddedDocument = _import_class('EmbeddedDocument')
        DictField = _import_class('DictField')
        return (Document, EmbeddedDocument, DictField)


class TopLevelDocumentMetaclass(DocumentMetaclass):
    """Metaclass for top-level documents (i.e. documents that have their own
    collection in the database.
    """

    def __new__(cls, name, bases, attrs):
        flattened_bases = cls._get_bases(bases)
        super_new = super(TopLevelDocumentMetaclass, cls).__new__

        # Set default _meta data if base class, otherwise get user defined meta
        if (attrs.get('my_metaclass') == TopLevelDocumentMetaclass):
            # defaults
            attrs['_meta'] = {
                'abstract': True,
                'max_documents': None,
                'max_size': None,
                'ordering': [],  # default ordering applied at runtime
                'indexes': [],  # indexes to be ensured at runtime
                'id_field': None,
                'index_background': False,
                'index_drop_dups': False,
                'index_opts': None,
                'delete_rules': None,
                'allow_inheritance': None,
            }
            attrs['_is_base_cls'] = True
            attrs['_meta'].update(attrs.get('meta', {}))
        else:
            attrs['_meta'] = attrs.get('meta', {})
            # Explictly set abstract to false unless set
            attrs['_meta']['abstract'] = attrs['_meta'].get('abstract', False)
            attrs['_is_base_cls'] = False

        # Set flag marking as document class - as opposed to an object mixin
        attrs['_is_document'] = True

        # Ensure queryset_class is inherited
        if 'objects' in attrs:
            manager = attrs['objects']
            if hasattr(manager, 'queryset_class'):
                attrs['_meta']['queryset_class'] = manager.queryset_class

        # Clean up top level meta
        if 'meta' in attrs:
            del(attrs['meta'])

        # Find the parent document class
        parent_doc_cls = [b for b in flattened_bases
                        if b.__class__ == TopLevelDocumentMetaclass]
        parent_doc_cls = None if not parent_doc_cls else parent_doc_cls[0]

        # Prevent classes setting collection different to their parents
        # If parent wasn't an abstract class
        if (parent_doc_cls and 'collection' in attrs.get('_meta', {})
            and not parent_doc_cls._meta.get('abstract', True)):
                msg = "Trying to set a collection on a subclass (%s)" % name
                warnings.warn(msg, SyntaxWarning)
                del(attrs['_meta']['collection'])

        # Ensure abstract documents have abstract bases
        if attrs.get('_is_base_cls') or attrs['_meta'].get('abstract'):
            if (parent_doc_cls and
                not parent_doc_cls._meta.get('abstract', False)):
                msg = "Abstract document cannot have non-abstract base"
                raise ValueError(msg)
            return super_new(cls, name, bases, attrs)

        # Merge base class metas.
        # Uses a special MetaDict that handles various merging rules
        meta = MetaDict()
        for base in flattened_bases[::-1]:
            # Add any mixin metadata from plain objects
            if hasattr(base, 'meta'):
                meta.merge(base.meta)
            elif hasattr(base, '_meta'):
                meta.merge(base._meta)

            # Set collection in the meta if its callable
            if (getattr(base, '_is_document', False) and
                not base._meta.get('abstract')):
                collection = meta.get('collection', None)
                if callable(collection):
                    meta['collection'] = collection(base)

        meta.merge(attrs.get('_meta', {}))  # Top level meta

        # Only simple classes (direct subclasses of Document)
        # may set allow_inheritance to False
        simple_class = all([b._meta.get('abstract')
                            for b in flattened_bases if hasattr(b, '_meta')])
        if (not simple_class and meta['allow_inheritance'] is False and
           not meta['abstract']):
            raise ValueError('Only direct subclasses of Document may set '
                             '"allow_inheritance" to False')

        # Set default collection name
        if 'collection' not in meta:
            meta['collection'] = ''.join('_%s' % c if c.isupper() else c
                                         for c in name).strip('_').lower()
        attrs['_meta'] = meta

        # Call super and get the new class
        new_class = super_new(cls, name, bases, attrs)

        meta = new_class._meta

        # Set index specifications
        meta['index_specs'] = new_class._build_index_specs(meta['indexes'])

        # If collection is a callable - call it and set the value
        collection = meta.get('collection')
        if callable(collection):
            new_class._meta['collection'] = collection(new_class)

        # Provide a default queryset unless exists or one has been set
        if 'objects' not in dir(new_class):
            new_class.objects = QuerySetManager()

        # Validate the fields and set primary key if needed
        for field_name, field in new_class._fields.iteritems():
            if field.primary_key:
                # Ensure only one primary key is set
                current_pk = new_class._meta.get('id_field')
                if current_pk and current_pk != field_name:
                    raise ValueError('Cannot override primary key field')

                # Set primary key
                if not current_pk:
                    new_class._meta['id_field'] = field_name
                    new_class.id = field

        # Set primary key if not defined by the document
        new_class._auto_id_field = False
        if not new_class._meta.get('id_field'):
            new_class._auto_id_field = True
            new_class._meta['id_field'] = 'id'
            new_class._fields['id'] = ObjectIdField(db_field='_id')
            new_class._fields['id'].name = 'id'
            new_class.id = new_class._fields['id']

        # Prepend id field to _fields_ordered
        if 'id' in new_class._fields and 'id' not in new_class._fields_ordered:
            new_class._fields_ordered = ('id', ) + new_class._fields_ordered

        # Merge in exceptions with parent hierarchy
        exceptions_to_merge = (DoesNotExist, MultipleObjectsReturned)
        module = attrs.get('__module__')
        for exc in exceptions_to_merge:
            name = exc.__name__
            parents = tuple(getattr(base, name) for base in flattened_bases
                         if hasattr(base, name)) or (exc,)
            # Create new exception and set to new_class
            exception = type(name, parents, {'__module__': module})
            setattr(new_class, name, exception)

        return new_class


class MetaDict(dict):
    """Custom dictionary for meta classes.
    Handles the merging of set indexes
    """
    _merge_options = ('indexes',)

    def merge(self, new_options):
        for k, v in new_options.iteritems():
            if k in self._merge_options:
                self[k] = self.get(k, []) + v
            else:
                self[k] = v


class BasesTuple(tuple):
    """Special class to handle introspection of bases tuple in __new__"""
    pass

########NEW FILE########
__FILENAME__ = common
_class_registry_cache = {}


def _import_class(cls_name):
    """Cache mechanism for imports.

    Due to complications of circular imports mongoengine needs to do lots of
    inline imports in functions.  This is inefficient as classes are
    imported repeated throughout the mongoengine code.  This is
    compounded by some recursive functions requiring inline imports.

    :mod:`mongoengine.common` provides a single point to import all these
    classes.  Circular imports aren't an issue as it dynamically imports the
    class when first needed.  Subsequent calls to the
    :func:`~mongoengine.common._import_class` can then directly retrieve the
    class from the :data:`mongoengine.common._class_registry_cache`.
    """
    if cls_name in _class_registry_cache:
        return _class_registry_cache.get(cls_name)

    doc_classes = ('Document', 'DynamicEmbeddedDocument', 'EmbeddedDocument',
                   'MapReduceDocument')
    field_classes = ('DictField', 'DynamicField', 'EmbeddedDocumentField',
                     'FileField', 'GenericReferenceField',
                     'GenericEmbeddedDocumentField', 'GeoPointField',
                     'PointField', 'LineStringField', 'ListField',
                     'PolygonField', 'ReferenceField', 'StringField',
                     'ComplexBaseField', 'GeoJsonBaseField')
    queryset_classes = ('OperationError',)
    deref_classes = ('DeReference',)

    if cls_name in doc_classes:
        from mongoengine import document as module
        import_classes = doc_classes
    elif cls_name in field_classes:
        from mongoengine import fields as module
        import_classes = field_classes
    elif cls_name in queryset_classes:
        from mongoengine import queryset as module
        import_classes = queryset_classes
    elif cls_name in deref_classes:
        from mongoengine import dereference as module
        import_classes = deref_classes
    else:
        raise ValueError('No import set for: ' % cls_name)

    for cls in import_classes:
        _class_registry_cache[cls] = getattr(module, cls)

    return _class_registry_cache.get(cls_name)

########NEW FILE########
__FILENAME__ = connection
import pymongo
from pymongo import MongoClient, MongoReplicaSetClient, uri_parser


__all__ = ['ConnectionError', 'connect', 'register_connection',
           'DEFAULT_CONNECTION_NAME']


DEFAULT_CONNECTION_NAME = 'default'


class ConnectionError(Exception):
    pass


_connection_settings = {}
_connections = {}
_dbs = {}


def register_connection(alias, name, host=None, port=None,
                        is_slave=False, read_preference=False, slaves=None,
                        username=None, password=None, **kwargs):
    """Add a connection.

    :param alias: the name that will be used to refer to this connection
        throughout MongoEngine
    :param name: the name of the specific database to use
    :param host: the host name of the :program:`mongod` instance to connect to
    :param port: the port that the :program:`mongod` instance is running on
    :param is_slave: whether the connection can act as a slave
      ** Depreciated pymongo 2.0.1+
    :param read_preference: The read preference for the collection
       ** Added pymongo 2.1
    :param slaves: a list of aliases of slave connections; each of these must
        be a registered connection that has :attr:`is_slave` set to ``True``
    :param username: username to authenticate with
    :param password: password to authenticate with
    :param kwargs: allow ad-hoc parameters to be passed into the pymongo driver

    """
    global _connection_settings

    conn_settings = {
        'name': name,
        'host': host or 'localhost',
        'port': port or 27017,
        'is_slave': is_slave,
        'slaves': slaves or [],
        'username': username,
        'password': password,
        'read_preference': read_preference
    }

    # Handle uri style connections
    if "://" in conn_settings['host']:
        uri_dict = uri_parser.parse_uri(conn_settings['host'])
        conn_settings.update({
            'name': uri_dict.get('database') or name,
            'username': uri_dict.get('username'),
            'password': uri_dict.get('password'),
            'read_preference': read_preference,
        })
        if "replicaSet" in conn_settings['host']:
            conn_settings['replicaSet'] = True

    conn_settings.update(kwargs)
    _connection_settings[alias] = conn_settings


def disconnect(alias=DEFAULT_CONNECTION_NAME):
    global _connections
    global _dbs

    if alias in _connections:
        get_connection(alias=alias).disconnect()
        del _connections[alias]
    if alias in _dbs:
        del _dbs[alias]


def get_connection(alias=DEFAULT_CONNECTION_NAME, reconnect=False):
    global _connections
    # Connect to the database if not already connected
    if reconnect:
        disconnect(alias)

    if alias not in _connections:
        if alias not in _connection_settings:
            msg = 'Connection with alias "%s" has not been defined' % alias
            if alias == DEFAULT_CONNECTION_NAME:
                msg = 'You have not defined a default connection'
            raise ConnectionError(msg)
        conn_settings = _connection_settings[alias].copy()

        if hasattr(pymongo, 'version_tuple'):  # Support for 2.1+
            conn_settings.pop('name', None)
            conn_settings.pop('slaves', None)
            conn_settings.pop('is_slave', None)
            conn_settings.pop('username', None)
            conn_settings.pop('password', None)
        else:
            # Get all the slave connections
            if 'slaves' in conn_settings:
                slaves = []
                for slave_alias in conn_settings['slaves']:
                    slaves.append(get_connection(slave_alias))
                conn_settings['slaves'] = slaves
                conn_settings.pop('read_preference', None)

        connection_class = MongoClient
        if 'replicaSet' in conn_settings:
            conn_settings['hosts_or_uri'] = conn_settings.pop('host', None)
            # Discard port since it can't be used on MongoReplicaSetClient
            conn_settings.pop('port', None)
            # Discard replicaSet if not base string
            if not isinstance(conn_settings['replicaSet'], basestring):
                conn_settings.pop('replicaSet', None)
            connection_class = MongoReplicaSetClient

        try:
            _connections[alias] = connection_class(**conn_settings)
        except Exception, e:
            raise ConnectionError("Cannot connect to database %s :\n%s" % (alias, e))
    return _connections[alias]


def get_db(alias=DEFAULT_CONNECTION_NAME, reconnect=False):
    global _dbs
    if reconnect:
        disconnect(alias)

    if alias not in _dbs:
        conn = get_connection(alias)
        conn_settings = _connection_settings[alias]
        db = conn[conn_settings['name']]
        # Authenticate if necessary
        if conn_settings['username'] and conn_settings['password']:
            db.authenticate(conn_settings['username'],
                            conn_settings['password'])
        _dbs[alias] = db
    return _dbs[alias]


def connect(db, alias=DEFAULT_CONNECTION_NAME, **kwargs):
    """Connect to the database specified by the 'db' argument.

    Connection settings may be provided here as well if the database is not
    running on the default port on localhost. If authentication is needed,
    provide username and password arguments as well.

    Multiple databases are supported by using aliases.  Provide a separate
    `alias` to connect to a different instance of :program:`mongod`.

    .. versionchanged:: 0.6 - added multiple database support.
    """
    global _connections
    if alias not in _connections:
        register_connection(alias, db, **kwargs)

    return get_connection(alias)


# Support old naming convention
_get_connection = get_connection
_get_db = get_db

########NEW FILE########
__FILENAME__ = context_managers
from mongoengine.common import _import_class
from mongoengine.connection import DEFAULT_CONNECTION_NAME, get_db
from mongoengine.queryset import QuerySet


__all__ = ("switch_db", "switch_collection", "no_dereference",
           "no_sub_classes", "query_counter")


class switch_db(object):
    """ switch_db alias context manager.

    Example ::

        # Register connections
        register_connection('default', 'mongoenginetest')
        register_connection('testdb-1', 'mongoenginetest2')

        class Group(Document):
            name = StringField()

        Group(name="test").save()  # Saves in the default db

        with switch_db(Group, 'testdb-1') as Group:
            Group(name="hello testdb!").save()  # Saves in testdb-1

    """

    def __init__(self, cls, db_alias):
        """ Construct the switch_db context manager

        :param cls: the class to change the registered db
        :param db_alias: the name of the specific database to use
        """
        self.cls = cls
        self.collection = cls._get_collection()
        self.db_alias = db_alias
        self.ori_db_alias = cls._meta.get("db_alias", DEFAULT_CONNECTION_NAME)

    def __enter__(self):
        """ change the db_alias and clear the cached collection """
        self.cls._meta["db_alias"] = self.db_alias
        self.cls._collection = None
        return self.cls

    def __exit__(self, t, value, traceback):
        """ Reset the db_alias and collection """
        self.cls._meta["db_alias"] = self.ori_db_alias
        self.cls._collection = self.collection


class switch_collection(object):
    """ switch_collection alias context manager.

    Example ::

        class Group(Document):
            name = StringField()

        Group(name="test").save()  # Saves in the default db

        with switch_collection(Group, 'group1') as Group:
            Group(name="hello testdb!").save()  # Saves in group1 collection

    """

    def __init__(self, cls, collection_name):
        """ Construct the switch_collection context manager

        :param cls: the class to change the registered db
        :param collection_name: the name of the collection to use
        """
        self.cls = cls
        self.ori_collection = cls._get_collection()
        self.ori_get_collection_name = cls._get_collection_name
        self.collection_name = collection_name

    def __enter__(self):
        """ change the _get_collection_name and clear the cached collection """

        @classmethod
        def _get_collection_name(cls):
            return self.collection_name

        self.cls._get_collection_name = _get_collection_name
        self.cls._collection = None
        return self.cls

    def __exit__(self, t, value, traceback):
        """ Reset the collection """
        self.cls._collection = self.ori_collection
        self.cls._get_collection_name = self.ori_get_collection_name


class no_dereference(object):
    """ no_dereference context manager.

    Turns off all dereferencing in Documents for the duration of the context
    manager::

        with no_dereference(Group) as Group:
            Group.objects.find()

    """

    def __init__(self, cls):
        """ Construct the no_dereference context manager.

        :param cls: the class to turn dereferencing off on
        """
        self.cls = cls

        ReferenceField = _import_class('ReferenceField')
        GenericReferenceField = _import_class('GenericReferenceField')
        ComplexBaseField = _import_class('ComplexBaseField')

        self.deref_fields = [k for k, v in self.cls._fields.iteritems()
                             if isinstance(v, (ReferenceField,
                                               GenericReferenceField,
                                               ComplexBaseField))]

    def __enter__(self):
        """ change the objects default and _auto_dereference values"""
        for field in self.deref_fields:
            self.cls._fields[field]._auto_dereference = False
        return self.cls

    def __exit__(self, t, value, traceback):
        """ Reset the default and _auto_dereference values"""
        for field in self.deref_fields:
            self.cls._fields[field]._auto_dereference = True
        return self.cls


class no_sub_classes(object):
    """ no_sub_classes context manager.

    Only returns instances of this class and no sub (inherited) classes::

        with no_sub_classes(Group) as Group:
            Group.objects.find()

    """

    def __init__(self, cls):
        """ Construct the no_sub_classes context manager.

        :param cls: the class to turn querying sub classes on
        """
        self.cls = cls

    def __enter__(self):
        """ change the objects default and _auto_dereference values"""
        self.cls._all_subclasses = self.cls._subclasses
        self.cls._subclasses = (self.cls,)
        return self.cls

    def __exit__(self, t, value, traceback):
        """ Reset the default and _auto_dereference values"""
        self.cls._subclasses = self.cls._all_subclasses
        delattr(self.cls, '_all_subclasses')
        return self.cls


class QuerySetNoDeRef(QuerySet):
    """Special no_dereference QuerySet"""
    def __dereference(items, max_depth=1, instance=None, name=None):
            return items


class query_counter(object):
    """ Query_counter context manager to get the number of queries. """

    def __init__(self):
        """ Construct the query_counter. """
        self.counter = 0
        self.db = get_db()

    def __enter__(self):
        """ On every with block we need to drop the profile collection. """
        self.db.set_profiling_level(0)
        self.db.system.profile.drop()
        self.db.set_profiling_level(2)
        return self

    def __exit__(self, t, value, traceback):
        """ Reset the profiling level. """
        self.db.set_profiling_level(0)

    def __eq__(self, value):
        """ == Compare querycounter. """
        counter = self._get_count()
        return value == counter

    def __ne__(self, value):
        """ != Compare querycounter. """
        return not self.__eq__(value)

    def __lt__(self, value):
        """ < Compare querycounter. """
        return self._get_count() < value

    def __le__(self, value):
        """ <= Compare querycounter. """
        return self._get_count() <= value

    def __gt__(self, value):
        """ > Compare querycounter. """
        return self._get_count() > value

    def __ge__(self, value):
        """ >= Compare querycounter. """
        return self._get_count() >= value

    def __int__(self):
        """ int representation. """
        return self._get_count()

    def __repr__(self):
        """ repr query_counter as the number of queries. """
        return u"%s" % self._get_count()

    def _get_count(self):
        """ Get the number of queries. """
        ignore_query = {"ns": {"$ne": "%s.system.indexes" % self.db.name}}
        count = self.db.system.profile.find(ignore_query).count() - self.counter
        self.counter += 1
        return count

########NEW FILE########
__FILENAME__ = dereference
from bson import DBRef, SON

from base import (BaseDict, BaseList, TopLevelDocumentMetaclass, get_document)
from fields import (ReferenceField, ListField, DictField, MapField)
from connection import get_db
from queryset import QuerySet
from document import Document, EmbeddedDocument


class DeReference(object):

    def __call__(self, items, max_depth=1, instance=None, name=None):
        """
        Cheaply dereferences the items to a set depth.
        Also handles the convertion of complex data types.

        :param items: The iterable (dict, list, queryset) to be dereferenced.
        :param max_depth: The maximum depth to recurse to
        :param instance: The owning instance used for tracking changes by
            :class:`~mongoengine.base.ComplexBaseField`
        :param name: The name of the field, used for tracking changes by
            :class:`~mongoengine.base.ComplexBaseField`
        :param get: A boolean determining if being called by __get__
        """
        if items is None or isinstance(items, basestring):
            return items

        # cheapest way to convert a queryset to a list
        # list(queryset) uses a count() query to determine length
        if isinstance(items, QuerySet):
            items = [i for i in items]

        self.max_depth = max_depth
        doc_type = None

        if instance and isinstance(instance, (Document, EmbeddedDocument,
                                              TopLevelDocumentMetaclass)):
            doc_type = instance._fields.get(name)
            if hasattr(doc_type, 'field'):
                doc_type = doc_type.field

            if isinstance(doc_type, ReferenceField):
                field = doc_type
                doc_type = doc_type.document_type
                is_list = not hasattr(items, 'items')

                if is_list and all([i.__class__ == doc_type for i in items]):
                    return items
                elif not is_list and all([i.__class__ == doc_type
                                         for i in items.values()]):
                    return items
                elif not field.dbref:
                    if not hasattr(items, 'items'):
                        items = [field.to_python(v)
                             if not isinstance(v, (DBRef, Document)) else v
                             for v in items]
                    else:
                        items = dict([
                            (k, field.to_python(v))
                            if not isinstance(v, (DBRef, Document)) else (k, v)
                            for k, v in items.iteritems()]
                        )

        self.reference_map = self._find_references(items)
        self.object_map = self._fetch_objects(doc_type=doc_type)
        return self._attach_objects(items, 0, instance, name)

    def _find_references(self, items, depth=0):
        """
        Recursively finds all db references to be dereferenced

        :param items: The iterable (dict, list, queryset)
        :param depth: The current depth of recursion
        """
        reference_map = {}
        if not items or depth >= self.max_depth:
            return reference_map

        # Determine the iterator to use
        if not hasattr(items, 'items'):
            iterator = enumerate(items)
        else:
            iterator = items.iteritems()

        # Recursively find dbreferences
        depth += 1
        for k, item in iterator:
            if isinstance(item, Document):
                for field_name, field in item._fields.iteritems():
                    v = item._data.get(field_name, None)
                    if isinstance(v, (DBRef)):
                        reference_map.setdefault(field.document_type, []).append(v.id)
                    elif isinstance(v, (dict, SON)) and '_ref' in v:
                        reference_map.setdefault(get_document(v['_cls']), []).append(v['_ref'].id)
                    elif isinstance(v, (dict, list, tuple)) and depth <= self.max_depth:
                        field_cls = getattr(getattr(field, 'field', None), 'document_type', None)
                        references = self._find_references(v, depth)
                        for key, refs in references.iteritems():
                            if isinstance(field_cls, (Document, TopLevelDocumentMetaclass)):
                                key = field_cls
                            reference_map.setdefault(key, []).extend(refs)
            elif isinstance(item, (DBRef)):
                reference_map.setdefault(item.collection, []).append(item.id)
            elif isinstance(item, (dict, SON)) and '_ref' in item:
                reference_map.setdefault(get_document(item['_cls']), []).append(item['_ref'].id)
            elif isinstance(item, (dict, list, tuple)) and depth - 1 <= self.max_depth:
                references = self._find_references(item, depth - 1)
                for key, refs in references.iteritems():
                    reference_map.setdefault(key, []).extend(refs)

        return reference_map

    def _fetch_objects(self, doc_type=None):
        """Fetch all references and convert to their document objects
        """
        object_map = {}
        for col, dbrefs in self.reference_map.iteritems():
            keys = object_map.keys()
            refs = list(set([dbref for dbref in dbrefs if unicode(dbref).encode('utf-8') not in keys]))
            if hasattr(col, 'objects'):  # We have a document class for the refs
                references = col.objects.in_bulk(refs)
                for key, doc in references.iteritems():
                    object_map[key] = doc
            else:  # Generic reference: use the refs data to convert to document
                if isinstance(doc_type, (ListField, DictField, MapField,)):
                    continue

                if doc_type:
                    references = doc_type._get_db()[col].find({'_id': {'$in': refs}})
                    for ref in references:
                        doc = doc_type._from_son(ref)
                        object_map[doc.id] = doc
                else:
                    references = get_db()[col].find({'_id': {'$in': refs}})
                    for ref in references:
                        if '_cls' in ref:
                            doc = get_document(ref["_cls"])._from_son(ref)
                        elif doc_type is None:
                            doc = get_document(
                                ''.join(x.capitalize()
                                    for x in col.split('_')))._from_son(ref)
                        else:
                            doc = doc_type._from_son(ref)
                        object_map[doc.id] = doc
        return object_map

    def _attach_objects(self, items, depth=0, instance=None, name=None):
        """
        Recursively finds all db references to be dereferenced

        :param items: The iterable (dict, list, queryset)
        :param depth: The current depth of recursion
        :param instance: The owning instance used for tracking changes by
            :class:`~mongoengine.base.ComplexBaseField`
        :param name: The name of the field, used for tracking changes by
            :class:`~mongoengine.base.ComplexBaseField`
        """
        if not items:
            if isinstance(items, (BaseDict, BaseList)):
                return items

            if instance:
                if isinstance(items, dict):
                    return BaseDict(items, instance, name)
                else:
                    return BaseList(items, instance, name)

        if isinstance(items, (dict, SON)):
            if '_ref' in items:
                return self.object_map.get(items['_ref'].id, items)
            elif '_cls' in items:
                doc = get_document(items['_cls'])._from_son(items)
                doc._data = self._attach_objects(doc._data, depth, doc, None)
                return doc

        if not hasattr(items, 'items'):
            is_list = True
            as_tuple = isinstance(items, tuple)
            iterator = enumerate(items)
            data = []
        else:
            is_list = False
            iterator = items.iteritems()
            data = {}

        depth += 1
        for k, v in iterator:
            if is_list:
                data.append(v)
            else:
                data[k] = v

            if k in self.object_map and not is_list:
                data[k] = self.object_map[k]
            elif isinstance(v, Document):
                for field_name, field in v._fields.iteritems():
                    v = data[k]._data.get(field_name, None)
                    if isinstance(v, (DBRef)):
                        data[k]._data[field_name] = self.object_map.get(v.id, v)
                    elif isinstance(v, (dict, SON)) and '_ref' in v:
                        data[k]._data[field_name] = self.object_map.get(v['_ref'].id, v)
                    elif isinstance(v, dict) and depth <= self.max_depth:
                        data[k]._data[field_name] = self._attach_objects(v, depth, instance=instance, name=name)
                    elif isinstance(v, (list, tuple)) and depth <= self.max_depth:
                        data[k]._data[field_name] = self._attach_objects(v, depth, instance=instance, name=name)
            elif isinstance(v, (dict, list, tuple)) and depth <= self.max_depth:
                data[k] = self._attach_objects(v, depth - 1, instance=instance, name=name)
            elif hasattr(v, 'id'):
                data[k] = self.object_map.get(v.id, v)

        if instance and name:
            if is_list:
                return tuple(data) if as_tuple else BaseList(data, instance, name)
            return BaseDict(data, instance, name)
        depth += 1
        return data

########NEW FILE########
__FILENAME__ = auth
from mongoengine import *

from django.utils.encoding import smart_str
from django.contrib.auth.models import _user_has_perm, _user_get_all_permissions, _user_has_module_perms
from django.db import models
from django.contrib.contenttypes.models import ContentTypeManager
from django.contrib import auth
from django.contrib.auth.models import AnonymousUser
from django.utils.translation import ugettext_lazy as _

from .utils import datetime_now

REDIRECT_FIELD_NAME = 'next'

try:
    from django.contrib.auth.hashers import check_password, make_password
except ImportError:
    """Handle older versions of Django"""
    from django.utils.hashcompat import md5_constructor, sha_constructor

    def get_hexdigest(algorithm, salt, raw_password):
        raw_password, salt = smart_str(raw_password), smart_str(salt)
        if algorithm == 'md5':
            return md5_constructor(salt + raw_password).hexdigest()
        elif algorithm == 'sha1':
            return sha_constructor(salt + raw_password).hexdigest()
        raise ValueError('Got unknown password algorithm type in password')

    def check_password(raw_password, password):
        algo, salt, hash = password.split('$')
        return hash == get_hexdigest(algo, salt, raw_password)

    def make_password(raw_password):
        from random import random
        algo = 'sha1'
        salt = get_hexdigest(algo, str(random()), str(random()))[:5]
        hash = get_hexdigest(algo, salt, raw_password)
        return '%s$%s$%s' % (algo, salt, hash)


class ContentType(Document):
    name = StringField(max_length=100)
    app_label = StringField(max_length=100)
    model = StringField(max_length=100, verbose_name=_('python model class name'),
                        unique_with='app_label')
    objects = ContentTypeManager()

    class Meta:
        verbose_name = _('content type')
        verbose_name_plural = _('content types')
        # db_table = 'django_content_type'
        # ordering = ('name',)
        # unique_together = (('app_label', 'model'),)

    def __unicode__(self):
        return self.name

    def model_class(self):
        "Returns the Python model class for this type of content."
        from django.db import models
        return models.get_model(self.app_label, self.model)

    def get_object_for_this_type(self, **kwargs):
        """
        Returns an object of this type for the keyword arguments given.
        Basically, this is a proxy around this object_type's get_object() model
        method. The ObjectNotExist exception, if thrown, will not be caught,
        so code that calls this method should catch it.
        """
        return self.model_class()._default_manager.using(self._state.db).get(**kwargs)

    def natural_key(self):
        return (self.app_label, self.model)


class SiteProfileNotAvailable(Exception):
    pass


class PermissionManager(models.Manager):
    def get_by_natural_key(self, codename, app_label, model):
        return self.get(
            codename=codename,
            content_type=ContentType.objects.get_by_natural_key(app_label, model)
        )


class Permission(Document):
    """The permissions system provides a way to assign permissions to specific
    users and groups of users.

    The permission system is used by the Django admin site, but may also be
    useful in your own code. The Django admin site uses permissions as follows:

        - The "add" permission limits the user's ability to view the "add"
          form and add an object.
        - The "change" permission limits a user's ability to view the change
          list, view the "change" form and change an object.
        - The "delete" permission limits the ability to delete an object.

    Permissions are set globally per type of object, not per specific object
    instance. It is possible to say "Mary may change news stories," but it's
    not currently possible to say "Mary may change news stories, but only the
    ones she created herself" or "Mary may only change news stories that have
    a certain status or publication date."

    Three basic permissions -- add, change and delete -- are automatically
    created for each Django model.
    """
    name = StringField(max_length=50, verbose_name=_('username'))
    content_type = ReferenceField(ContentType)
    codename = StringField(max_length=100, verbose_name=_('codename'))
        # FIXME: don't access field of the other class
        # unique_with=['content_type__app_label', 'content_type__model'])

    objects = PermissionManager()

    class Meta:
        verbose_name = _('permission')
        verbose_name_plural = _('permissions')
        # unique_together = (('content_type', 'codename'),)
        # ordering = ('content_type__app_label', 'content_type__model', 'codename')

    def __unicode__(self):
        return u"%s | %s | %s" % (
            unicode(self.content_type.app_label),
            unicode(self.content_type),
            unicode(self.name))

    def natural_key(self):
        return (self.codename,) + self.content_type.natural_key()
    natural_key.dependencies = ['contenttypes.contenttype']


class Group(Document):
    """Groups are a generic way of categorizing users to apply permissions,
    or some other label, to those users. A user can belong to any number of
    groups.

    A user in a group automatically has all the permissions granted to that
    group. For example, if the group Site editors has the permission
    can_edit_home_page, any user in that group will have that permission.

    Beyond permissions, groups are a convenient way to categorize users to
    apply some label, or extended functionality, to them. For example, you
    could create a group 'Special users', and you could write code that would
    do special things to those users -- such as giving them access to a
    members-only portion of your site, or sending them members-only
    e-mail messages.
    """
    name = StringField(max_length=80, unique=True, verbose_name=_('name'))
    permissions = ListField(ReferenceField(Permission, verbose_name=_('permissions'), required=False))

    class Meta:
        verbose_name = _('group')
        verbose_name_plural = _('groups')

    def __unicode__(self):
        return self.name


class UserManager(models.Manager):
    def create_user(self, username, email, password=None):
        """
        Creates and saves a User with the given username, e-mail and password.
        """
        now = datetime_now()

        # Normalize the address by lowercasing the domain part of the email
        # address.
        try:
            email_name, domain_part = email.strip().split('@', 1)
        except ValueError:
            pass
        else:
            email = '@'.join([email_name, domain_part.lower()])

        user = self.model(username=username, email=email, is_staff=False,
                          is_active=True, is_superuser=False, last_login=now,
                          date_joined=now)

        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email, password):
        u = self.create_user(username, email, password)
        u.is_staff = True
        u.is_active = True
        u.is_superuser = True
        u.save(using=self._db)
        return u

    def make_random_password(self, length=10, allowed_chars='abcdefghjkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789'):
        "Generates a random password with the given length and given allowed_chars"
        # Note that default value of allowed_chars does not have "I" or letters
        # that look like it -- just to avoid confusion.
        from random import choice
        return ''.join([choice(allowed_chars) for i in range(length)])


class User(Document):
    """A User document that aims to mirror most of the API specified by Django
    at http://docs.djangoproject.com/en/dev/topics/auth/#users
    """
    username = StringField(max_length=30, required=True,
                           verbose_name=_('username'),
                           help_text=_("Required. 30 characters or fewer. Letters, numbers and @/./+/-/_ characters"))

    first_name = StringField(max_length=30,
                             verbose_name=_('first name'))

    last_name = StringField(max_length=30,
                            verbose_name=_('last name'))
    email = EmailField(verbose_name=_('e-mail address'))
    password = StringField(max_length=128,
                           verbose_name=_('password'),
                           help_text=_("Use '[algo]$[iterations]$[salt]$[hexdigest]' or use the <a href=\"password/\">change password form</a>."))
    is_staff = BooleanField(default=False,
                            verbose_name=_('staff status'),
                            help_text=_("Designates whether the user can log into this admin site."))
    is_active = BooleanField(default=True,
                             verbose_name=_('active'),
                             help_text=_("Designates whether this user should be treated as active. Unselect this instead of deleting accounts."))
    is_superuser = BooleanField(default=False,
                                verbose_name=_('superuser status'),
                                help_text=_("Designates that this user has all permissions without explicitly assigning them."))
    last_login = DateTimeField(default=datetime_now,
                               verbose_name=_('last login'))
    date_joined = DateTimeField(default=datetime_now,
                                verbose_name=_('date joined'))

    user_permissions = ListField(ReferenceField(Permission), verbose_name=_('user permissions'),
                                                help_text=_('Permissions for the user.'))

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email']

    meta = {
        'allow_inheritance': True,
        'indexes': [
            {'fields': ['username'], 'unique': True, 'sparse': True}
        ]
    }

    def __unicode__(self):
        return self.username

    def get_full_name(self):
        """Returns the users first and last names, separated by a space.
        """
        full_name = u'%s %s' % (self.first_name or '', self.last_name or '')
        return full_name.strip()

    def is_anonymous(self):
        return False

    def is_authenticated(self):
        return True

    def set_password(self, raw_password):
        """Sets the user's password - always use this rather than directly
        assigning to :attr:`~mongoengine.django.auth.User.password` as the
        password is hashed before storage.
        """
        self.password = make_password(raw_password)
        self.save()
        return self

    def check_password(self, raw_password):
        """Checks the user's password against a provided password - always use
        this rather than directly comparing to
        :attr:`~mongoengine.django.auth.User.password` as the password is
        hashed before storage.
        """
        return check_password(raw_password, self.password)

    @classmethod
    def create_user(cls, username, password, email=None):
        """Create (and save) a new user with the given username, password and
        email address.
        """
        now = datetime_now()

        # Normalize the address by lowercasing the domain part of the email
        # address.
        if email is not None:
            try:
                email_name, domain_part = email.strip().split('@', 1)
            except ValueError:
                pass
            else:
                email = '@'.join([email_name, domain_part.lower()])

        user = cls(username=username, email=email, date_joined=now)
        user.set_password(password)
        user.save()
        return user

    def get_group_permissions(self, obj=None):
        """
        Returns a list of permission strings that this user has through his/her
        groups. This method queries all available auth backends. If an object
        is passed in, only permissions matching this object are returned.
        """
        permissions = set()
        for backend in auth.get_backends():
            if hasattr(backend, "get_group_permissions"):
                permissions.update(backend.get_group_permissions(self, obj))
        return permissions

    def get_all_permissions(self, obj=None):
        return _user_get_all_permissions(self, obj)

    def has_perm(self, perm, obj=None):
        """
        Returns True if the user has the specified permission. This method
        queries all available auth backends, but returns immediately if any
        backend returns True. Thus, a user who has permission from a single
        auth backend is assumed to have permission in general. If an object is
        provided, permissions for this specific object are checked.
        """

        # Active superusers have all permissions.
        if self.is_active and self.is_superuser:
            return True

        # Otherwise we need to check the backends.
        return _user_has_perm(self, perm, obj)

    def has_module_perms(self, app_label):
        """
        Returns True if the user has any permissions in the given app label.
        Uses pretty much the same logic as has_perm, above.
        """
        # Active superusers have all permissions.
        if self.is_active and self.is_superuser:
            return True

        return _user_has_module_perms(self, app_label)

    def email_user(self, subject, message, from_email=None):
        "Sends an e-mail to this User."
        from django.core.mail import send_mail
        send_mail(subject, message, from_email, [self.email])

    def get_profile(self):
        """
        Returns site-specific profile for this user. Raises
        SiteProfileNotAvailable if this site does not allow profiles.
        """
        if not hasattr(self, '_profile_cache'):
            from django.conf import settings
            if not getattr(settings, 'AUTH_PROFILE_MODULE', False):
                raise SiteProfileNotAvailable('You need to set AUTH_PROFILE_MO'
                                              'DULE in your project settings')
            try:
                app_label, model_name = settings.AUTH_PROFILE_MODULE.split('.')
            except ValueError:
                raise SiteProfileNotAvailable('app_label and model_name should'
                        ' be separated by a dot in the AUTH_PROFILE_MODULE set'
                        'ting')

            try:
                model = models.get_model(app_label, model_name)
                if model is None:
                    raise SiteProfileNotAvailable('Unable to load the profile '
                        'model, check AUTH_PROFILE_MODULE in your project sett'
                        'ings')
                self._profile_cache = model._default_manager.using(self._state.db).get(user__id__exact=self.id)
                self._profile_cache.user = self
            except (ImportError, ImproperlyConfigured):
                raise SiteProfileNotAvailable
        return self._profile_cache


class MongoEngineBackend(object):
    """Authenticate using MongoEngine and mongoengine.django.auth.User.
    """

    supports_object_permissions = False
    supports_anonymous_user = False
    supports_inactive_user = False
    _user_doc = False

    def authenticate(self, username=None, password=None):
        user = self.user_document.objects(username=username).first()
        if user:
            if password and user.check_password(password):
                backend = auth.get_backends()[0]
                user.backend = "%s.%s" % (backend.__module__, backend.__class__.__name__)
                return user
        return None

    def get_user(self, user_id):
        return self.user_document.objects.with_id(user_id)

    @property
    def user_document(self):
        if self._user_doc is False:
            from .mongo_auth.models import get_user_document
            self._user_doc = get_user_document()
        return self._user_doc

def get_user(userid):
    """Returns a User object from an id (User.id). Django's equivalent takes
    request, but taking an id instead leaves it up to the developer to store
    the id in any way they want (session, signed cookie, etc.)
    """
    if not userid:
        return AnonymousUser()
    return MongoEngineBackend().get_user(userid) or AnonymousUser()

########NEW FILE########
__FILENAME__ = models
from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import UserManager
from django.core.exceptions import ImproperlyConfigured
from django.db import models
from django.utils.importlib import import_module
from django.utils.translation import ugettext_lazy as _


__all__ = (
    'get_user_document',
)


MONGOENGINE_USER_DOCUMENT = getattr(
    settings, 'MONGOENGINE_USER_DOCUMENT', 'mongoengine.django.auth.User')


def get_user_document():
    """Get the user document class used for authentication.

    This is the class defined in settings.MONGOENGINE_USER_DOCUMENT, which
    defaults to `mongoengine.django.auth.User`.

    """

    name = MONGOENGINE_USER_DOCUMENT
    dot = name.rindex('.')
    module = import_module(name[:dot])
    return getattr(module, name[dot + 1:])


class MongoUserManager(UserManager):
    """A User manager wich allows the use of MongoEngine documents in Django.

    To use the manager, you must tell django.contrib.auth to use MongoUser as
    the user model. In you settings.py, you need:

        INSTALLED_APPS = (
            ...
            'django.contrib.auth',
            'mongoengine.django.mongo_auth',
            ...
        )
        AUTH_USER_MODEL = 'mongo_auth.MongoUser'

    Django will use the model object to access the custom Manager, which will
    replace the original queryset with MongoEngine querysets.

    By default, mongoengine.django.auth.User will be used to store users. You
    can specify another document class in MONGOENGINE_USER_DOCUMENT in your
    settings.py.

    The User Document class has the same requirements as a standard custom user
    model: https://docs.djangoproject.com/en/dev/topics/auth/customizing/

    In particular, the User Document class must define USERNAME_FIELD and
    REQUIRED_FIELDS.

    `AUTH_USER_MODEL` has been added in Django 1.5.

    """

    def contribute_to_class(self, model, name):
        super(MongoUserManager, self).contribute_to_class(model, name)
        self.dj_model = self.model
        self.model = get_user_document()

        self.dj_model.USERNAME_FIELD = self.model.USERNAME_FIELD
        username = models.CharField(_('username'), max_length=30, unique=True)
        username.contribute_to_class(self.dj_model, self.dj_model.USERNAME_FIELD)

        self.dj_model.REQUIRED_FIELDS = self.model.REQUIRED_FIELDS
        for name in self.dj_model.REQUIRED_FIELDS:
            field = models.CharField(_(name), max_length=30)
            field.contribute_to_class(self.dj_model, name)


    def get(self, *args, **kwargs):
        try:
            return self.get_query_set().get(*args, **kwargs)
        except self.model.DoesNotExist:
            # ModelBackend expects this exception
            raise self.dj_model.DoesNotExist

    @property
    def db(self):
        raise NotImplementedError

    def get_empty_query_set(self):
        return self.model.objects.none()

    def get_query_set(self):
        return self.model.objects


class MongoUser(models.Model):
    """"Dummy user model for Django.

    MongoUser is used to replace Django's UserManager with MongoUserManager.
    The actual user document class is mongoengine.django.auth.User or any
    other document class specified in MONGOENGINE_USER_DOCUMENT.

    To get the user document class, use `get_user_document()`.

    """

    objects = MongoUserManager()

    class Meta:
        app_label = 'mongo_auth'

    def set_password(self, password):
        """Doesn't do anything, but works around the issue with Django 1.6."""
        make_password(password)

########NEW FILE########
__FILENAME__ = sessions
from bson import json_util
from django.conf import settings
from django.contrib.sessions.backends.base import SessionBase, CreateError
from django.core.exceptions import SuspiciousOperation
try:
    from django.utils.encoding import force_unicode
except ImportError:
    from django.utils.encoding import force_text as force_unicode

from mongoengine.document import Document
from mongoengine import fields
from mongoengine.queryset import OperationError
from mongoengine.connection import DEFAULT_CONNECTION_NAME

from .utils import datetime_now


MONGOENGINE_SESSION_DB_ALIAS = getattr(
    settings, 'MONGOENGINE_SESSION_DB_ALIAS',
    DEFAULT_CONNECTION_NAME)

# a setting for the name of the collection used to store sessions
MONGOENGINE_SESSION_COLLECTION = getattr(
    settings, 'MONGOENGINE_SESSION_COLLECTION',
    'django_session')

# a setting for whether session data is stored encoded or not
MONGOENGINE_SESSION_DATA_ENCODE = getattr(
    settings, 'MONGOENGINE_SESSION_DATA_ENCODE',
    True)


class MongoSession(Document):
    session_key = fields.StringField(primary_key=True, max_length=40)
    session_data = fields.StringField() if MONGOENGINE_SESSION_DATA_ENCODE \
                                        else fields.DictField()
    expire_date = fields.DateTimeField()

    meta = {
        'collection': MONGOENGINE_SESSION_COLLECTION,
        'db_alias': MONGOENGINE_SESSION_DB_ALIAS,
        'allow_inheritance': False,
        'indexes': [
            {
                'fields': ['expire_date'],
                'expireAfterSeconds': 0
            }
        ]
    }

    def get_decoded(self):
        return SessionStore().decode(self.session_data)


class SessionStore(SessionBase):
    """A MongoEngine-based session store for Django.
    """

    def _get_session(self, *args, **kwargs):
        sess = super(SessionStore, self)._get_session(*args, **kwargs)
        if sess.get('_auth_user_id', None):
            sess['_auth_user_id'] = str(sess.get('_auth_user_id'))
        return sess

    def load(self):
        try:
            s = MongoSession.objects(session_key=self.session_key,
                                     expire_date__gt=datetime_now)[0]
            if MONGOENGINE_SESSION_DATA_ENCODE:
                return self.decode(force_unicode(s.session_data))
            else:
                return s.session_data
        except (IndexError, SuspiciousOperation):
            self.create()
            return {}

    def exists(self, session_key):
        return bool(MongoSession.objects(session_key=session_key).first())

    def create(self):
        while True:
            self._session_key = self._get_new_session_key()
            try:
                self.save(must_create=True)
            except CreateError:
                continue
            self.modified = True
            self._session_cache = {}
            return

    def save(self, must_create=False):
        if self.session_key is None:
            self._session_key = self._get_new_session_key()
        s = MongoSession(session_key=self.session_key)
        if MONGOENGINE_SESSION_DATA_ENCODE:
            s.session_data = self.encode(self._get_session(no_load=must_create))
        else:
            s.session_data = self._get_session(no_load=must_create)
        s.expire_date = self.get_expiry_date()
        try:
            s.save(force_insert=must_create)
        except OperationError:
            if must_create:
                raise CreateError
            raise

    def delete(self, session_key=None):
        if session_key is None:
            if self.session_key is None:
                return
            session_key = self.session_key
        MongoSession.objects(session_key=session_key).delete()


class BSONSerializer(object):
    """
    Serializer that can handle BSON types (eg ObjectId).
    """
    def dumps(self, obj):
        return json_util.dumps(obj, separators=(',', ':')).encode('ascii')

    def loads(self, data):
        return json_util.loads(data.decode('ascii'))


########NEW FILE########
__FILENAME__ = shortcuts
from mongoengine.queryset import QuerySet
from mongoengine.base import BaseDocument
from mongoengine.errors import ValidationError

def _get_queryset(cls):
    """Inspired by django.shortcuts.*"""
    if isinstance(cls, QuerySet):
        return cls
    else:
        return cls.objects

def get_document_or_404(cls, *args, **kwargs):
    """
    Uses get() to return an document, or raises a Http404 exception if the document
    does not exist.

    cls may be a Document or QuerySet object. All other passed
    arguments and keyword arguments are used in the get() query.

    Note: Like with get(), an MultipleObjectsReturned will be raised if more than one
    object is found.

    Inspired by django.shortcuts.*
    """
    queryset = _get_queryset(cls)
    try:
        return queryset.get(*args, **kwargs)
    except (queryset._document.DoesNotExist, ValidationError):
        from django.http import Http404
        raise Http404('No %s matches the given query.' % queryset._document._class_name)

def get_list_or_404(cls, *args, **kwargs):
    """
    Uses filter() to return a list of documents, or raise a Http404 exception if
    the list is empty.

    cls may be a Document or QuerySet object. All other passed
    arguments and keyword arguments are used in the filter() query.

    Inspired by django.shortcuts.*
    """
    queryset = _get_queryset(cls)
    obj_list = list(queryset.filter(*args, **kwargs))
    if not obj_list:
        from django.http import Http404
        raise Http404('No %s matches the given query.' % queryset._document._class_name)
    return obj_list

########NEW FILE########
__FILENAME__ = storage
import os
import itertools
import urlparse

from mongoengine import *
from django.conf import settings
from django.core.files.storage import Storage
from django.core.exceptions import ImproperlyConfigured


class FileDocument(Document):
    """A document used to store a single file in GridFS.
    """
    file = FileField()


class GridFSStorage(Storage):
    """A custom storage backend to store files in GridFS
    """

    def __init__(self, base_url=None):

        if base_url is None:
            base_url = settings.MEDIA_URL
        self.base_url = base_url
        self.document = FileDocument
        self.field = 'file'

    def delete(self, name):
        """Deletes the specified file from the storage system.
        """
        if self.exists(name):
            doc = self.document.objects.first()
            field = getattr(doc, self.field)
            self._get_doc_with_name(name).delete()  # Delete the FileField
            field.delete()                          # Delete the FileDocument

    def exists(self, name):
        """Returns True if a file referened by the given name already exists in the
        storage system, or False if the name is available for a new file.
        """
        doc = self._get_doc_with_name(name)
        if doc:
            field = getattr(doc, self.field)
            return bool(field.name)
        else:
            return False

    def listdir(self, path=None):
        """Lists the contents of the specified path, returning a 2-tuple of lists;
        the first item being directories, the second item being files.
        """
        def name(doc):
            return getattr(doc, self.field).name
        docs = self.document.objects
        return [], [name(d) for d in docs if name(d)]

    def size(self, name):
        """Returns the total size, in bytes, of the file specified by name.
        """
        doc = self._get_doc_with_name(name)
        if doc:
            return getattr(doc, self.field).length
        else:
            raise ValueError("No such file or directory: '%s'" % name)

    def url(self, name):
        """Returns an absolute URL where the file's contents can be accessed
        directly by a web browser.
        """
        if self.base_url is None:
            raise ValueError("This file is not accessible via a URL.")
        return urlparse.urljoin(self.base_url, name).replace('\\', '/')

    def _get_doc_with_name(self, name):
        """Find the documents in the store with the given name
        """
        docs = self.document.objects
        doc = [d for d in docs if hasattr(getattr(d, self.field), 'name') and getattr(d, self.field).name == name]
        if doc:
            return doc[0]
        else:
            return None

    def _open(self, name, mode='rb'):
        doc = self._get_doc_with_name(name)
        if doc:
            return getattr(doc, self.field)
        else:
            raise ValueError("No file found with the name '%s'." % name)

    def get_available_name(self, name):
        """Returns a filename that's free on the target storage system, and
        available for new content to be written to.
        """
        file_root, file_ext = os.path.splitext(name)
        # If the filename already exists, add an underscore and a number (before
        # the file extension, if one exists) to the filename until the generated
        # filename doesn't exist.
        count = itertools.count(1)
        while self.exists(name):
            # file_ext includes the dot.
            name = os.path.join("%s_%s%s" % (file_root, count.next(), file_ext))

        return name

    def _save(self, name, content):
        doc = self.document()
        getattr(doc, self.field).put(content, filename=name)
        doc.save()

        return name

########NEW FILE########
__FILENAME__ = tests
#coding: utf-8
from nose.plugins.skip import SkipTest

from mongoengine.python_support import PY3
from mongoengine import connect

try:
    from django.test import TestCase
    from django.conf import settings
except Exception as err:
    if PY3:
        from unittest import TestCase
        # Dummy value so no error
        class settings:
            MONGO_DATABASE_NAME = 'dummy'
    else:
        raise err


class MongoTestCase(TestCase):

    def setUp(self):
        if PY3:
            raise SkipTest('django does not have Python 3 support')

    """
    TestCase class that clear the collection between the tests
    """
    db_name = 'test_%s' % settings.MONGO_DATABASE_NAME
    def __init__(self, methodName='runtest'):
        self.db = connect(self.db_name).get_db()
        super(MongoTestCase, self).__init__(methodName)

    def _post_teardown(self):
        super(MongoTestCase, self)._post_teardown()
        for collection in self.db.collection_names():
            if collection == 'system.indexes':
                continue
            self.db.drop_collection(collection)

########NEW FILE########
__FILENAME__ = utils
try:
    # django >= 1.4
    from django.utils.timezone import now as datetime_now
except ImportError:
    from datetime import datetime
    datetime_now = datetime.now

########NEW FILE########
__FILENAME__ = document
import warnings

import hashlib
import pymongo
import re

from pymongo.read_preferences import ReadPreference
from bson import ObjectId
from bson.dbref import DBRef
from mongoengine import signals
from mongoengine.common import _import_class
from mongoengine.base import (DocumentMetaclass, TopLevelDocumentMetaclass,
                              BaseDocument, BaseDict, BaseList,
                              ALLOW_INHERITANCE, get_document)
from mongoengine.errors import ValidationError
from mongoengine.queryset import OperationError, NotUniqueError, QuerySet
from mongoengine.connection import get_db, DEFAULT_CONNECTION_NAME
from mongoengine.context_managers import switch_db, switch_collection

__all__ = ('Document', 'EmbeddedDocument', 'DynamicDocument',
           'DynamicEmbeddedDocument', 'OperationError',
           'InvalidCollectionError', 'NotUniqueError', 'MapReduceDocument')


def includes_cls(fields):
    """ Helper function used for ensuring and comparing indexes
    """

    first_field = None
    if len(fields):
        if isinstance(fields[0], basestring):
            first_field = fields[0]
        elif isinstance(fields[0], (list, tuple)) and len(fields[0]):
            first_field = fields[0][0]
    return first_field == '_cls'


class InvalidCollectionError(Exception):
    pass


class EmbeddedDocument(BaseDocument):
    """A :class:`~mongoengine.Document` that isn't stored in its own
    collection.  :class:`~mongoengine.EmbeddedDocument`\ s should be used as
    fields on :class:`~mongoengine.Document`\ s through the
    :class:`~mongoengine.EmbeddedDocumentField` field type.

    A :class:`~mongoengine.EmbeddedDocument` subclass may be itself subclassed,
    to create a specialised version of the embedded document that will be
    stored in the same collection. To facilitate this behaviour a `_cls`
    field is added to documents (hidden though the MongoEngine interface).
    To disable this behaviour and remove the dependence on the presence of
    `_cls` set :attr:`allow_inheritance` to ``False`` in the :attr:`meta`
    dictionary.
    """

    # The __metaclass__ attribute is removed by 2to3 when running with Python3
    # my_metaclass is defined so that metaclass can be queried in Python 2 & 3
    my_metaclass  = DocumentMetaclass
    __metaclass__ = DocumentMetaclass

    _instance = None

    def __init__(self, *args, **kwargs):
        super(EmbeddedDocument, self).__init__(*args, **kwargs)
        self._changed_fields = []

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.to_mongo() == other.to_mongo()
        return False

    def __ne__(self, other):
        return not self.__eq__(other)


class Document(BaseDocument):
    """The base class used for defining the structure and properties of
    collections of documents stored in MongoDB. Inherit from this class, and
    add fields as class attributes to define a document's structure.
    Individual documents may then be created by making instances of the
    :class:`~mongoengine.Document` subclass.

    By default, the MongoDB collection used to store documents created using a
    :class:`~mongoengine.Document` subclass will be the name of the subclass
    converted to lowercase. A different collection may be specified by
    providing :attr:`collection` to the :attr:`meta` dictionary in the class
    definition.

    A :class:`~mongoengine.Document` subclass may be itself subclassed, to
    create a specialised version of the document that will be stored in the
    same collection. To facilitate this behaviour a `_cls`
    field is added to documents (hidden though the MongoEngine interface).
    To disable this behaviour and remove the dependence on the presence of
    `_cls` set :attr:`allow_inheritance` to ``False`` in the :attr:`meta`
    dictionary.

    A :class:`~mongoengine.Document` may use a **Capped Collection** by
    specifying :attr:`max_documents` and :attr:`max_size` in the :attr:`meta`
    dictionary. :attr:`max_documents` is the maximum number of documents that
    is allowed to be stored in the collection, and :attr:`max_size` is the
    maximum size of the collection in bytes. If :attr:`max_size` is not
    specified and :attr:`max_documents` is, :attr:`max_size` defaults to
    10000000 bytes (10MB).

    Indexes may be created by specifying :attr:`indexes` in the :attr:`meta`
    dictionary. The value should be a list of field names or tuples of field
    names. Index direction may be specified by prefixing the field names with
    a **+** or **-** sign.

    Automatic index creation can be disabled by specifying
    attr:`auto_create_index` in the :attr:`meta` dictionary. If this is set to
    False then indexes will not be created by MongoEngine.  This is useful in
    production systems where index creation is performed as part of a
    deployment system.

    By default, _cls will be added to the start of every index (that
    doesn't contain a list) if allow_inheritance is True. This can be
    disabled by either setting cls to False on the specific index or
    by setting index_cls to False on the meta dictionary for the document.
    """

    # The __metaclass__ attribute is removed by 2to3 when running with Python3
    # my_metaclass is defined so that metaclass can be queried in Python 2 & 3
    my_metaclass  = TopLevelDocumentMetaclass
    __metaclass__ = TopLevelDocumentMetaclass

    def pk():
        """Primary key alias
        """
        def fget(self):
            return getattr(self, self._meta['id_field'])

        def fset(self, value):
            return setattr(self, self._meta['id_field'], value)
        return property(fget, fset)
    pk = pk()

    @classmethod
    def _get_db(cls):
        """Some Model using other db_alias"""
        return get_db(cls._meta.get("db_alias", DEFAULT_CONNECTION_NAME))

    @classmethod
    def _get_collection(cls):
        """Returns the collection for the document."""
        if not hasattr(cls, '_collection') or cls._collection is None:
            db = cls._get_db()
            collection_name = cls._get_collection_name()
            # Create collection as a capped collection if specified
            if cls._meta['max_size'] or cls._meta['max_documents']:
                # Get max document limit and max byte size from meta
                max_size = cls._meta['max_size'] or 10000000  # 10MB default
                max_documents = cls._meta['max_documents']

                if collection_name in db.collection_names():
                    cls._collection = db[collection_name]
                    # The collection already exists, check if its capped
                    # options match the specified capped options
                    options = cls._collection.options()
                    if options.get('max') != max_documents or \
                       options.get('size') != max_size:
                        msg = (('Cannot create collection "%s" as a capped '
                               'collection as it already exists')
                               % cls._collection)
                        raise InvalidCollectionError(msg)
                else:
                    # Create the collection as a capped collection
                    opts = {'capped': True, 'size': max_size}
                    if max_documents:
                        opts['max'] = max_documents
                    cls._collection = db.create_collection(
                        collection_name, **opts
                    )
            else:
                cls._collection = db[collection_name]
            if cls._meta.get('auto_create_index', True):
                cls.ensure_indexes()
        return cls._collection

    def save(self, force_insert=False, validate=True, clean=True,
             write_concern=None,  cascade=None, cascade_kwargs=None,
             _refs=None, **kwargs):
        """Save the :class:`~mongoengine.Document` to the database. If the
        document already exists, it will be updated, otherwise it will be
        created.

        :param force_insert: only try to create a new document, don't allow
            updates of existing documents
        :param validate: validates the document; set to ``False`` to skip.
        :param clean: call the document clean method, requires `validate` to be
            True.
        :param write_concern: Extra keyword arguments are passed down to
            :meth:`~pymongo.collection.Collection.save` OR
            :meth:`~pymongo.collection.Collection.insert`
            which will be used as options for the resultant
            ``getLastError`` command.  For example,
            ``save(..., write_concern={w: 2, fsync: True}, ...)`` will
            wait until at least two servers have recorded the write and
            will force an fsync on the primary server.
        :param cascade: Sets the flag for cascading saves.  You can set a
            default by setting "cascade" in the document __meta__
        :param cascade_kwargs: (optional) kwargs dictionary to be passed throw
            to cascading saves.  Implies ``cascade=True``.
        :param _refs: A list of processed references used in cascading saves

        .. versionchanged:: 0.5
            In existing documents it only saves changed fields using
            set / unset.  Saves are cascaded and any
            :class:`~bson.dbref.DBRef` objects that have changes are
            saved as well.
        .. versionchanged:: 0.6
            Added cascading saves
        .. versionchanged:: 0.8
            Cascade saves are optional and default to False.  If you want
            fine grain control then you can turn off using document
            meta['cascade'] = True.  Also you can pass different kwargs to
            the cascade save using cascade_kwargs which overwrites the
            existing kwargs with custom values.
        """
        signals.pre_save.send(self.__class__, document=self)

        if validate:
            self.validate(clean=clean)

        if write_concern is None:
            write_concern = {"w": 1}

        doc = self.to_mongo()

        created = ('_id' not in doc or self._created or force_insert)

        signals.pre_save_post_validation.send(self.__class__, document=self, created=created)

        try:
            collection = self._get_collection()
            if created:
                if force_insert:
                    object_id = collection.insert(doc, **write_concern)
                else:
                    object_id = collection.save(doc, **write_concern)
            else:
                object_id = doc['_id']
                updates, removals = self._delta()
                # Need to add shard key to query, or you get an error
                select_dict = {'_id': object_id}
                shard_key = self.__class__._meta.get('shard_key', tuple())
                for k in shard_key:
                    actual_key = self._db_field_map.get(k, k)
                    select_dict[actual_key] = doc[actual_key]

                def is_new_object(last_error):
                    if last_error is not None:
                        updated = last_error.get("updatedExisting")
                        if updated is not None:
                            return not updated
                    return created

                update_query = {}

                if updates:
                    update_query["$set"] = updates
                if removals:
                    update_query["$unset"] = removals
                if updates or removals:
                    last_error = collection.update(select_dict, update_query,
                                                   upsert=True, **write_concern)
                    created = is_new_object(last_error)

            if cascade is None:
                cascade = self._meta.get('cascade', False) or cascade_kwargs is not None

            if cascade:
                kwargs = {
                    "force_insert": force_insert,
                    "validate": validate,
                    "write_concern": write_concern,
                    "cascade": cascade
                }
                if cascade_kwargs:  # Allow granular control over cascades
                    kwargs.update(cascade_kwargs)
                kwargs['_refs'] = _refs
                self.cascade_save(**kwargs)
        except pymongo.errors.DuplicateKeyError, err:
            message = u'Tried to save duplicate unique keys (%s)'
            raise NotUniqueError(message % unicode(err))
        except pymongo.errors.OperationFailure, err:
            message = 'Could not save document (%s)'
            if re.match('^E1100[01] duplicate key', unicode(err)):
                # E11000 - duplicate key error index
                # E11001 - duplicate key on update
                message = u'Tried to save duplicate unique keys (%s)'
                raise NotUniqueError(message % unicode(err))
            raise OperationError(message % unicode(err))
        id_field = self._meta['id_field']
        if id_field not in self._meta.get('shard_key', []):
            self[id_field] = self._fields[id_field].to_python(object_id)

        self._clear_changed_fields()
        self._created = False
        signals.post_save.send(self.__class__, document=self, created=created)
        return self

    def cascade_save(self, *args, **kwargs):
        """Recursively saves any references /
           generic references on an objects"""
        _refs = kwargs.get('_refs', []) or []

        ReferenceField = _import_class('ReferenceField')
        GenericReferenceField = _import_class('GenericReferenceField')

        for name, cls in self._fields.items():
            if not isinstance(cls, (ReferenceField,
                                    GenericReferenceField)):
                continue

            ref = self._data.get(name)
            if not ref or isinstance(ref, DBRef):
                continue

            if not getattr(ref, '_changed_fields', True):
                continue

            ref_id = "%s,%s" % (ref.__class__.__name__, str(ref._data))
            if ref and ref_id not in _refs:
                _refs.append(ref_id)
                kwargs["_refs"] = _refs
                ref.save(**kwargs)
                ref._changed_fields = []

    @property
    def _qs(self):
        """
        Returns the queryset to use for updating / reloading / deletions
        """
        if not hasattr(self, '__objects'):
            self.__objects = QuerySet(self, self._get_collection())
        return self.__objects

    @property
    def _object_key(self):
        """Dict to identify object in collection
        """
        select_dict = {'pk': self.pk}
        shard_key = self.__class__._meta.get('shard_key', tuple())
        for k in shard_key:
            select_dict[k] = getattr(self, k)
        return select_dict

    def update(self, **kwargs):
        """Performs an update on the :class:`~mongoengine.Document`
        A convenience wrapper to :meth:`~mongoengine.QuerySet.update`.

        Raises :class:`OperationError` if called on an object that has not yet
        been saved.
        """
        if not self.pk:
            if kwargs.get('upsert', False):
                query = self.to_mongo()
                if "_cls" in query:
                    del(query["_cls"])
                return self._qs.filter(**query).update_one(**kwargs)
            else:
                raise OperationError('attempt to update a document not yet saved')

        # Need to add shard key to query, or you get an error
        return self._qs.filter(**self._object_key).update_one(**kwargs)

    def delete(self, **write_concern):
        """Delete the :class:`~mongoengine.Document` from the database. This
        will only take effect if the document has been previously saved.

        :param write_concern: Extra keyword arguments are passed down which
            will be used as options for the resultant
            ``getLastError`` command.  For example,
            ``save(..., write_concern={w: 2, fsync: True}, ...)`` will
            wait until at least two servers have recorded the write and
            will force an fsync on the primary server.
        """
        signals.pre_delete.send(self.__class__, document=self)

        try:
            self._qs.filter(**self._object_key).delete(write_concern=write_concern, _from_doc_delete=True)
        except pymongo.errors.OperationFailure, err:
            message = u'Could not delete document (%s)' % err.message
            raise OperationError(message)
        signals.post_delete.send(self.__class__, document=self)

    def switch_db(self, db_alias):
        """
        Temporarily switch the database for a document instance.

        Only really useful for archiving off data and calling `save()`::

            user = User.objects.get(id=user_id)
            user.switch_db('archive-db')
            user.save()

        If you need to read from another database see
        :class:`~mongoengine.context_managers.switch_db`

        :param db_alias: The database alias to use for saving the document
        """
        with switch_db(self.__class__, db_alias) as cls:
            collection = cls._get_collection()
            db = cls._get_db()
        self._get_collection = lambda: collection
        self._get_db = lambda: db
        self._collection = collection
        self._created = True
        self.__objects = self._qs
        self.__objects._collection_obj = collection
        return self

    def switch_collection(self, collection_name):
        """
        Temporarily switch the collection for a document instance.

        Only really useful for archiving off data and calling `save()`::

            user = User.objects.get(id=user_id)
            user.switch_collection('old-users')
            user.save()

        If you need to read from another database see
        :class:`~mongoengine.context_managers.switch_db`

        :param collection_name: The database alias to use for saving the
            document
        """
        with switch_collection(self.__class__, collection_name) as cls:
            collection = cls._get_collection()
        self._get_collection = lambda: collection
        self._collection = collection
        self._created = True
        self.__objects = self._qs
        self.__objects._collection_obj = collection
        return self

    def select_related(self, max_depth=1):
        """Handles dereferencing of :class:`~bson.dbref.DBRef` objects to
        a maximum depth in order to cut down the number queries to mongodb.

        .. versionadded:: 0.5
        """
        DeReference = _import_class('DeReference')
        DeReference()([self], max_depth + 1)
        return self

    def reload(self, max_depth=1):
        """Reloads all attributes from the database.

        .. versionadded:: 0.1.2
        .. versionchanged:: 0.6  Now chainable
        """
        if not self.pk:
            raise self.DoesNotExist("Document does not exist")
        obj = self._qs.read_preference(ReadPreference.PRIMARY).filter(
                    **self._object_key).limit(1).select_related(max_depth=max_depth)


        if obj:
            obj = obj[0]
        else:
            raise self.DoesNotExist("Document does not exist")
        for field in self._fields_ordered:
            setattr(self, field, self._reload(field, obj[field]))
        self._changed_fields = obj._changed_fields
        self._created = False
        return obj

    def _reload(self, key, value):
        """Used by :meth:`~mongoengine.Document.reload` to ensure the
        correct instance is linked to self.
        """
        if isinstance(value, BaseDict):
            value = [(k, self._reload(k, v)) for k, v in value.items()]
            value = BaseDict(value, self, key)
        elif isinstance(value, BaseList):
            value = [self._reload(key, v) for v in value]
            value = BaseList(value, self, key)
        elif isinstance(value, (EmbeddedDocument, DynamicEmbeddedDocument)):
            value._instance = None
            value._changed_fields = []
        return value

    def to_dbref(self):
        """Returns an instance of :class:`~bson.dbref.DBRef` useful in
        `__raw__` queries."""
        if not self.pk:
            msg = "Only saved documents can have a valid dbref"
            raise OperationError(msg)
        return DBRef(self.__class__._get_collection_name(), self.pk)

    @classmethod
    def register_delete_rule(cls, document_cls, field_name, rule):
        """This method registers the delete rules to apply when removing this
        object.
        """
        classes = [get_document(class_name)
                    for class_name in cls._subclasses
                    if class_name != cls.__name__] + [cls]
        documents = [get_document(class_name)
                     for class_name in document_cls._subclasses
                     if class_name != document_cls.__name__] + [document_cls]

        for cls in classes:
            for document_cls in documents:
                delete_rules = cls._meta.get('delete_rules') or {}
                delete_rules[(document_cls, field_name)] = rule
                cls._meta['delete_rules'] = delete_rules

    @classmethod
    def drop_collection(cls):
        """Drops the entire collection associated with this
        :class:`~mongoengine.Document` type from the database.
        """
        cls._collection = None
        db = cls._get_db()
        db.drop_collection(cls._get_collection_name())

    @classmethod
    def ensure_index(cls, key_or_list, drop_dups=False, background=False,
        **kwargs):
        """Ensure that the given indexes are in place.

        :param key_or_list: a single index key or a list of index keys (to
            construct a multi-field index); keys may be prefixed with a **+**
            or a **-** to determine the index ordering
        """
        index_spec = cls._build_index_spec(key_or_list)
        index_spec = index_spec.copy()
        fields = index_spec.pop('fields')
        index_spec['drop_dups'] = drop_dups
        index_spec['background'] = background
        index_spec.update(kwargs)

        return cls._get_collection().ensure_index(fields, **index_spec)

    @classmethod
    def ensure_indexes(cls):
        """Checks the document meta data and ensures all the indexes exist.

        Global defaults can be set in the meta - see :doc:`guide/defining-documents`

        .. note:: You can disable automatic index creation by setting
                  `auto_create_index` to False in the documents meta data
        """
        background = cls._meta.get('index_background', False)
        drop_dups = cls._meta.get('index_drop_dups', False)
        index_opts = cls._meta.get('index_opts') or {}
        index_cls = cls._meta.get('index_cls', True)

        collection = cls._get_collection()
        if collection.read_preference > 1:
            return

        # determine if an index which we are creating includes
        # _cls as its first field; if so, we can avoid creating
        # an extra index on _cls, as mongodb will use the existing
        # index to service queries against _cls
        cls_indexed = False

        # Ensure document-defined indexes are created
        if cls._meta['index_specs']:
            index_spec = cls._meta['index_specs']
            for spec in index_spec:
                spec = spec.copy()
                fields = spec.pop('fields')
                cls_indexed = cls_indexed or includes_cls(fields)
                opts = index_opts.copy()
                opts.update(spec)
                collection.ensure_index(fields, background=background,
                                        drop_dups=drop_dups, **opts)

        # If _cls is being used (for polymorphism), it needs an index,
        # only if another index doesn't begin with _cls
        if (index_cls and not cls_indexed and
           cls._meta.get('allow_inheritance', ALLOW_INHERITANCE) is True):
            collection.ensure_index('_cls', background=background,
                                    **index_opts)

    @classmethod
    def list_indexes(cls, go_up=True, go_down=True):
        """ Lists all of the indexes that should be created for given
        collection. It includes all the indexes from super- and sub-classes.
        """

        if cls._meta.get('abstract'):
            return []

        # get all the base classes, subclasses and sieblings
        classes = []
        def get_classes(cls):

            if (cls not in classes and
               isinstance(cls, TopLevelDocumentMetaclass)):
                classes.append(cls)

            for base_cls in cls.__bases__:
                if (isinstance(base_cls, TopLevelDocumentMetaclass) and
                   base_cls != Document and
                   not base_cls._meta.get('abstract') and
                   base_cls._get_collection().full_name == cls._get_collection().full_name and
                   base_cls not in classes):
                    classes.append(base_cls)
                    get_classes(base_cls)
            for subclass in cls.__subclasses__():
                if (isinstance(base_cls, TopLevelDocumentMetaclass) and
                   subclass._get_collection().full_name == cls._get_collection().full_name and
                   subclass not in classes):
                    classes.append(subclass)
                    get_classes(subclass)

        get_classes(cls)

        # get the indexes spec for all of the gathered classes
        def get_indexes_spec(cls):
            indexes = []

            if cls._meta['index_specs']:
                index_spec = cls._meta['index_specs']
                for spec in index_spec:
                    spec = spec.copy()
                    fields = spec.pop('fields')
                    indexes.append(fields)
            return indexes

        indexes = []
        for cls in classes:
            for index in get_indexes_spec(cls):
                if index not in indexes:
                    indexes.append(index)

        # finish up by appending { '_id': 1 } and { '_cls': 1 }, if needed
        if [(u'_id', 1)] not in indexes:
            indexes.append([(u'_id', 1)])
        if (cls._meta.get('index_cls', True) and
           cls._meta.get('allow_inheritance', ALLOW_INHERITANCE) is True):
             indexes.append([(u'_cls', 1)])

        return indexes

    @classmethod
    def compare_indexes(cls):
        """ Compares the indexes defined in MongoEngine with the ones existing
        in the database. Returns any missing/extra indexes.
        """

        required = cls.list_indexes()
        existing = [info['key'] for info in cls._get_collection().index_information().values()]
        missing = [index for index in required if index not in existing]
        extra = [index for index in existing if index not in required]

        # if { _cls: 1 } is missing, make sure it's *really* necessary
        if [(u'_cls', 1)] in missing:
            cls_obsolete = False
            for index in existing:
                if includes_cls(index) and index not in extra:
                    cls_obsolete = True
                    break
            if cls_obsolete:
                missing.remove([(u'_cls', 1)])

        return {'missing': missing, 'extra': extra}


class DynamicDocument(Document):
    """A Dynamic Document class allowing flexible, expandable and uncontrolled
    schemas.  As a :class:`~mongoengine.Document` subclass, acts in the same
    way as an ordinary document but has expando style properties.  Any data
    passed or set against the :class:`~mongoengine.DynamicDocument` that is
    not a field is automatically converted into a
    :class:`~mongoengine.fields.DynamicField` and data can be attributed to that
    field.

    .. note::

        There is one caveat on Dynamic Documents: fields cannot start with `_`
    """

    # The __metaclass__ attribute is removed by 2to3 when running with Python3
    # my_metaclass is defined so that metaclass can be queried in Python 2 & 3
    my_metaclass  = TopLevelDocumentMetaclass
    __metaclass__ = TopLevelDocumentMetaclass

    _dynamic = True

    def __delattr__(self, *args, **kwargs):
        """Deletes the attribute by setting to None and allowing _delta to unset
        it"""
        field_name = args[0]
        if field_name in self._dynamic_fields:
            setattr(self, field_name, None)
        else:
            super(DynamicDocument, self).__delattr__(*args, **kwargs)


class DynamicEmbeddedDocument(EmbeddedDocument):
    """A Dynamic Embedded Document class allowing flexible, expandable and
    uncontrolled schemas. See :class:`~mongoengine.DynamicDocument` for more
    information about dynamic documents.
    """

    # The __metaclass__ attribute is removed by 2to3 when running with Python3
    # my_metaclass is defined so that metaclass can be queried in Python 2 & 3
    my_metaclass  = DocumentMetaclass
    __metaclass__ = DocumentMetaclass

    _dynamic = True

    def __delattr__(self, *args, **kwargs):
        """Deletes the attribute by setting to None and allowing _delta to unset
        it"""
        field_name = args[0]
        if field_name in self._fields:
            default = self._fields[field_name].default
            if callable(default):
                default = default()
            setattr(self, field_name, default)
        else:
            setattr(self, field_name, None)


class MapReduceDocument(object):
    """A document returned from a map/reduce query.

    :param collection: An instance of :class:`~pymongo.Collection`
    :param key: Document/result key, often an instance of
                :class:`~bson.objectid.ObjectId`. If supplied as
                an ``ObjectId`` found in the given ``collection``,
                the object can be accessed via the ``object`` property.
    :param value: The result(s) for this key.

    .. versionadded:: 0.3
    """

    def __init__(self, document, collection, key, value):
        self._document = document
        self._collection = collection
        self.key = key
        self.value = value

    @property
    def object(self):
        """Lazy-load the object referenced by ``self.key``. ``self.key``
        should be the ``primary_key``.
        """
        id_field = self._document()._meta['id_field']
        id_field_type = type(id_field)

        if not isinstance(self.key, id_field_type):
            try:
                self.key = id_field_type(self.key)
            except:
                raise Exception("Could not cast key as %s" % \
                                id_field_type.__name__)

        if not hasattr(self, "_key_object"):
            self._key_object = self._document.objects.with_id(self.key)
            return self._key_object
        return self._key_object

########NEW FILE########
__FILENAME__ = errors
from collections import defaultdict

from mongoengine.python_support import txt_type


__all__ = ('NotRegistered', 'InvalidDocumentError', 'LookUpError',
           'DoesNotExist', 'MultipleObjectsReturned', 'InvalidQueryError',
           'OperationError', 'NotUniqueError', 'ValidationError')


class NotRegistered(Exception):
    pass


class InvalidDocumentError(Exception):
    pass


class LookUpError(AttributeError):
    pass


class DoesNotExist(Exception):
    pass


class MultipleObjectsReturned(Exception):
    pass


class InvalidQueryError(Exception):
    pass


class OperationError(Exception):
    pass


class NotUniqueError(OperationError):
    pass


class ValidationError(AssertionError):
    """Validation exception.

    May represent an error validating a field or a
    document containing fields with validation errors.

    :ivar errors: A dictionary of errors for fields within this
        document or list, or None if the error is for an
        individual field.
    """

    errors = {}
    field_name = None
    _message = None

    def __init__(self, message="", **kwargs):
        self.errors = kwargs.get('errors', {})
        self.field_name = kwargs.get('field_name')
        self.message = message

    def __str__(self):
        return txt_type(self.message)

    def __repr__(self):
        return '%s(%s,)' % (self.__class__.__name__, self.message)

    def __getattribute__(self, name):
        message = super(ValidationError, self).__getattribute__(name)
        if name == 'message':
            if self.field_name:
                message = '%s' % message
            if self.errors:
                message = '%s(%s)' % (message, self._format_errors())
        return message

    def _get_message(self):
        return self._message

    def _set_message(self, message):
        self._message = message

    message = property(_get_message, _set_message)

    def to_dict(self):
        """Returns a dictionary of all errors within a document

        Keys are field names or list indices and values are the
        validation error messages, or a nested dictionary of
        errors for an embedded document or list.
        """

        def build_dict(source):
            errors_dict = {}
            if not source:
                return errors_dict
            if isinstance(source, dict):
                for field_name, error in source.iteritems():
                    errors_dict[field_name] = build_dict(error)
            elif isinstance(source, ValidationError) and source.errors:
                return build_dict(source.errors)
            else:
                return unicode(source)
            return errors_dict
        if not self.errors:
            return {}
        return build_dict(self.errors)

    def _format_errors(self):
        """Returns a string listing all errors within a document"""

        def generate_key(value, prefix=''):
            if isinstance(value, list):
                value = ' '.join([generate_key(k) for k in value])
            if isinstance(value, dict):
                value = ' '.join(
                        [generate_key(v, k) for k, v in value.iteritems()])

            results = "%s.%s" % (prefix, value) if prefix else value
            return results

        error_dict = defaultdict(list)
        for k, v in self.to_dict().iteritems():
            error_dict[generate_key(v)].append(k)
        return ' '.join(["%s: %s" % (k, v) for k, v in error_dict.iteritems()])

########NEW FILE########
__FILENAME__ = fields
import datetime
import decimal
import itertools
import re
import time
import urllib2
import uuid
import warnings
from operator import itemgetter

try:
    import dateutil
except ImportError:
    dateutil = None
else:
    import dateutil.parser

import pymongo
import gridfs
from bson import Binary, DBRef, SON, ObjectId

from mongoengine.errors import ValidationError
from mongoengine.python_support import (PY3, bin_type, txt_type,
                                        str_types, StringIO)
from base import (BaseField, ComplexBaseField, ObjectIdField, GeoJsonBaseField,
                  get_document, BaseDocument)
from queryset import DO_NOTHING, QuerySet
from document import Document, EmbeddedDocument
from connection import get_db, DEFAULT_CONNECTION_NAME

try:
    from PIL import Image, ImageOps
except ImportError:
    Image = None
    ImageOps = None

__all__ = ['StringField',  'URLField',  'EmailField',  'IntField',  'LongField',
           'FloatField',  'DecimalField',  'BooleanField',  'DateTimeField',
           'ComplexDateTimeField',  'EmbeddedDocumentField', 'ObjectIdField',
           'GenericEmbeddedDocumentField',  'DynamicField',  'ListField',
           'SortedListField',  'DictField',  'MapField',  'ReferenceField',
           'GenericReferenceField',  'BinaryField',  'GridFSError',
           'GridFSProxy',  'FileField',  'ImageGridFsProxy',
           'ImproperlyConfigured',  'ImageField',  'GeoPointField', 'PointField',
           'LineStringField', 'PolygonField', 'SequenceField',  'UUIDField',
           'GeoJsonBaseField']


RECURSIVE_REFERENCE_CONSTANT = 'self'


class StringField(BaseField):
    """A unicode string field.
    """

    def __init__(self, regex=None, max_length=None, min_length=None, **kwargs):
        self.regex = re.compile(regex) if regex else None
        self.max_length = max_length
        self.min_length = min_length
        super(StringField, self).__init__(**kwargs)

    def to_python(self, value):
        if isinstance(value, unicode):
            return value
        try:
            value = value.decode('utf-8')
        except:
            pass
        return value

    def validate(self, value):
        if not isinstance(value, basestring):
            self.error('StringField only accepts string values')

        if self.max_length is not None and len(value) > self.max_length:
            self.error('String value is too long')

        if self.min_length is not None and len(value) < self.min_length:
            self.error('String value is too short')

        if self.regex is not None and self.regex.match(value) is None:
            self.error('String value did not match validation regex')

    def lookup_member(self, member_name):
        return None

    def prepare_query_value(self, op, value):
        if not isinstance(op, basestring):
            return value

        if op.lstrip('i') in ('startswith', 'endswith', 'contains', 'exact'):
            flags = 0
            if op.startswith('i'):
                flags = re.IGNORECASE
                op = op.lstrip('i')

            regex = r'%s'
            if op == 'startswith':
                regex = r'^%s'
            elif op == 'endswith':
                regex = r'%s$'
            elif op == 'exact':
                regex = r'^%s$'

            # escape unsafe characters which could lead to a re.error
            value = re.escape(value)
            value = re.compile(regex % value, flags)
        return value


class URLField(StringField):
    """A field that validates input as an URL.

    .. versionadded:: 0.3
    """

    _URL_REGEX = re.compile(
        r'^(?:http|ftp)s?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)

    def __init__(self, verify_exists=False, url_regex=None, **kwargs):
        self.verify_exists = verify_exists
        self.url_regex = url_regex or self._URL_REGEX
        super(URLField, self).__init__(**kwargs)

    def validate(self, value):
        if not self.url_regex.match(value):
            self.error('Invalid URL: %s' % value)
            return

        if self.verify_exists:
            warnings.warn(
                "The URLField verify_exists argument has intractable security "
                "and performance issues. Accordingly, it has been deprecated.",
                DeprecationWarning)
            try:
                request = urllib2.Request(value)
                urllib2.urlopen(request)
            except Exception, e:
                self.error('This URL appears to be a broken link: %s' % e)


class EmailField(StringField):
    """A field that validates input as an E-Mail-Address.

    .. versionadded:: 0.4
    """

    EMAIL_REGEX = re.compile(
        r"(^[-!#$%&'*+/=?^_`{}|~0-9A-Z]+(\.[-!#$%&'*+/=?^_`{}|~0-9A-Z]+)*"  # dot-atom
        r'|^"([\001-\010\013\014\016-\037!#-\[\]-\177]|\\[\001-011\013\014\016-\177])*"'  # quoted-string
        r')@(?:[A-Z0-9](?:[A-Z0-9-]{0,253}[A-Z0-9])?\.)+[A-Z]{2,6}$', re.IGNORECASE  # domain
    )

    def validate(self, value):
        if not EmailField.EMAIL_REGEX.match(value):
            self.error('Invalid Mail-address: %s' % value)
        super(EmailField, self).validate(value)


class IntField(BaseField):
    """An 32-bit integer field.
    """

    def __init__(self, min_value=None, max_value=None, **kwargs):
        self.min_value, self.max_value = min_value, max_value
        super(IntField, self).__init__(**kwargs)

    def to_python(self, value):
        try:
            value = int(value)
        except ValueError:
            pass
        return value

    def validate(self, value):
        try:
            value = int(value)
        except:
            self.error('%s could not be converted to int' % value)

        if self.min_value is not None and value < self.min_value:
            self.error('Integer value is too small')

        if self.max_value is not None and value > self.max_value:
            self.error('Integer value is too large')

    def prepare_query_value(self, op, value):
        if value is None:
            return value

        return int(value)


class LongField(BaseField):
    """An 64-bit integer field.
    """

    def __init__(self, min_value=None, max_value=None, **kwargs):
        self.min_value, self.max_value = min_value, max_value
        super(LongField, self).__init__(**kwargs)

    def to_python(self, value):
        try:
            value = long(value)
        except ValueError:
            pass
        return value

    def validate(self, value):
        try:
            value = long(value)
        except:
            self.error('%s could not be converted to long' % value)

        if self.min_value is not None and value < self.min_value:
            self.error('Long value is too small')

        if self.max_value is not None and value > self.max_value:
            self.error('Long value is too large')

    def prepare_query_value(self, op, value):
        if value is None:
            return value

        return long(value)


class FloatField(BaseField):
    """An floating point number field.
    """

    def __init__(self, min_value=None, max_value=None, **kwargs):
        self.min_value, self.max_value = min_value, max_value
        super(FloatField, self).__init__(**kwargs)

    def to_python(self, value):
        try:
            value = float(value)
        except ValueError:
            pass
        return value

    def validate(self, value):
        if isinstance(value, int):
            value = float(value)
        if not isinstance(value, float):
            self.error('FloatField only accepts float values')

        if self.min_value is not None and value < self.min_value:
            self.error('Float value is too small')

        if self.max_value is not None and value > self.max_value:
            self.error('Float value is too large')

    def prepare_query_value(self, op, value):
        if value is None:
            return value

        return float(value)


class DecimalField(BaseField):
    """A fixed-point decimal number field.

    .. versionchanged:: 0.8
    .. versionadded:: 0.3
    """

    def __init__(self, min_value=None, max_value=None, force_string=False,
                 precision=2, rounding=decimal.ROUND_HALF_UP, **kwargs):
        """
        :param min_value: Validation rule for the minimum acceptable value.
        :param max_value: Validation rule for the maximum acceptable value.
        :param force_string: Store as a string.
        :param precision: Number of decimal places to store.
        :param rounding: The rounding rule from the python decimal libary:

            - decimal.ROUND_CEILING (towards Infinity)
            - decimal.ROUND_DOWN (towards zero)
            - decimal.ROUND_FLOOR (towards -Infinity)
            - decimal.ROUND_HALF_DOWN (to nearest with ties going towards zero)
            - decimal.ROUND_HALF_EVEN (to nearest with ties going to nearest even integer)
            - decimal.ROUND_HALF_UP (to nearest with ties going away from zero)
            - decimal.ROUND_UP (away from zero)
            - decimal.ROUND_05UP (away from zero if last digit after rounding towards zero would have been 0 or 5; otherwise towards zero)

            Defaults to: ``decimal.ROUND_HALF_UP``

        """
        self.min_value = min_value
        self.max_value = max_value
        self.force_string = force_string
        self.precision = decimal.Decimal(".%s" % ("0" * precision))
        self.rounding = rounding

        super(DecimalField, self).__init__(**kwargs)

    def to_python(self, value):
        if value is None:
            return value

        # Convert to string for python 2.6 before casting to Decimal
        try:
            value = decimal.Decimal("%s" % value)
        except decimal.InvalidOperation:
            return value
        return value.quantize(self.precision, rounding=self.rounding)

    def to_mongo(self, value):
        if value is None:
            return value
        if self.force_string:
            return unicode(value)
        return float(self.to_python(value))

    def validate(self, value):
        if not isinstance(value, decimal.Decimal):
            if not isinstance(value, basestring):
                value = unicode(value)
            try:
                value = decimal.Decimal(value)
            except Exception, exc:
                self.error('Could not convert value to decimal: %s' % exc)

        if self.min_value is not None and value < self.min_value:
            self.error('Decimal value is too small')

        if self.max_value is not None and value > self.max_value:
            self.error('Decimal value is too large')

    def prepare_query_value(self, op, value):
        return self.to_mongo(value)


class BooleanField(BaseField):
    """A boolean field type.

    .. versionadded:: 0.1.2
    """

    def to_python(self, value):
        try:
            value = bool(value)
        except ValueError:
            pass
        return value

    def validate(self, value):
        if not isinstance(value, bool):
            self.error('BooleanField only accepts boolean values')


class DateTimeField(BaseField):
    """A datetime field.

    Uses the python-dateutil library if available alternatively use time.strptime
    to parse the dates.  Note: python-dateutil's parser is fully featured and when
    installed you can utilise it to convert varing types of date formats into valid
    python datetime objects.

    Note: Microseconds are rounded to the nearest millisecond.
      Pre UTC microsecond support is effecively broken.
      Use :class:`~mongoengine.fields.ComplexDateTimeField` if you
      need accurate microsecond support.
    """

    def validate(self, value):
        new_value = self.to_mongo(value)
        if not isinstance(new_value, (datetime.datetime, datetime.date)):
            self.error(u'cannot parse date "%s"' % value)

    def to_mongo(self, value):
        if value is None:
            return value
        if isinstance(value, datetime.datetime):
            return value
        if isinstance(value, datetime.date):
            return datetime.datetime(value.year, value.month, value.day)
        if callable(value):
            return value()

        if not isinstance(value, basestring):
            return None

        # Attempt to parse a datetime:
        if dateutil:
            try:
                return dateutil.parser.parse(value)
            except (TypeError, ValueError):
                return None

        # split usecs, because they are not recognized by strptime.
        if '.' in value:
            try:
                value, usecs = value.split('.')
                usecs = int(usecs)
            except ValueError:
                return None
        else:
            usecs = 0
        kwargs = {'microsecond': usecs}
        try:  # Seconds are optional, so try converting seconds first.
            return datetime.datetime(*time.strptime(value,
                                     '%Y-%m-%d %H:%M:%S')[:6], **kwargs)
        except ValueError:
            try:  # Try without seconds.
                return datetime.datetime(*time.strptime(value,
                                         '%Y-%m-%d %H:%M')[:5], **kwargs)
            except ValueError:  # Try without hour/minutes/seconds.
                try:
                    return datetime.datetime(*time.strptime(value,
                                             '%Y-%m-%d')[:3], **kwargs)
                except ValueError:
                    return None

    def prepare_query_value(self, op, value):
        return self.to_mongo(value)


class ComplexDateTimeField(StringField):
    """
    ComplexDateTimeField handles microseconds exactly instead of rounding
    like DateTimeField does.

    Derives from a StringField so you can do `gte` and `lte` filtering by
    using lexicographical comparison when filtering / sorting strings.

    The stored string has the following format:

        YYYY,MM,DD,HH,MM,SS,NNNNNN

    Where NNNNNN is the number of microseconds of the represented `datetime`.
    The `,` as the separator can be easily modified by passing the `separator`
    keyword when initializing the field.

    .. versionadded:: 0.5
    """

    def __init__(self, separator=',', **kwargs):
        self.names = ['year', 'month', 'day', 'hour', 'minute', 'second',
                      'microsecond']
        self.separtor = separator
        super(ComplexDateTimeField, self).__init__(**kwargs)

    def _leading_zero(self, number):
        """
        Converts the given number to a string.

        If it has only one digit, a leading zero so as it has always at least
        two digits.
        """
        if int(number) < 10:
            return "0%s" % number
        else:
            return str(number)

    def _convert_from_datetime(self, val):
        """
        Convert a `datetime` object to a string representation (which will be
        stored in MongoDB). This is the reverse function of
        `_convert_from_string`.

        >>> a = datetime(2011, 6, 8, 20, 26, 24, 192284)
        >>> RealDateTimeField()._convert_from_datetime(a)
        '2011,06,08,20,26,24,192284'
        """
        data = []
        for name in self.names:
            data.append(self._leading_zero(getattr(val, name)))
        return ','.join(data)

    def _convert_from_string(self, data):
        """
        Convert a string representation to a `datetime` object (the object you
        will manipulate). This is the reverse function of
        `_convert_from_datetime`.

        >>> a = '2011,06,08,20,26,24,192284'
        >>> ComplexDateTimeField()._convert_from_string(a)
        datetime.datetime(2011, 6, 8, 20, 26, 24, 192284)
        """
        data = data.split(',')
        data = map(int, data)
        values = {}
        for i in range(7):
            values[self.names[i]] = data[i]
        return datetime.datetime(**values)

    def __get__(self, instance, owner):
        data = super(ComplexDateTimeField, self).__get__(instance, owner)
        if data is None:
            return datetime.datetime.now()
        if isinstance(data, datetime.datetime):
            return data
        return self._convert_from_string(data)

    def __set__(self, instance, value):
        value = self._convert_from_datetime(value) if value else value
        return super(ComplexDateTimeField, self).__set__(instance, value)

    def validate(self, value):
        value = self.to_python(value)
        if not isinstance(value, datetime.datetime):
            self.error('Only datetime objects may used in a '
                       'ComplexDateTimeField')

    def to_python(self, value):
        original_value = value
        try:
            return self._convert_from_string(value)
        except:
            return original_value

    def to_mongo(self, value):
        value = self.to_python(value)
        return self._convert_from_datetime(value)

    def prepare_query_value(self, op, value):
        return self._convert_from_datetime(value)


class EmbeddedDocumentField(BaseField):
    """An embedded document field - with a declared document_type.
    Only valid values are subclasses of :class:`~mongoengine.EmbeddedDocument`.
    """

    def __init__(self, document_type, **kwargs):
        if not isinstance(document_type, basestring):
            if not issubclass(document_type, EmbeddedDocument):
                self.error('Invalid embedded document class provided to an '
                           'EmbeddedDocumentField')
        self.document_type_obj = document_type
        super(EmbeddedDocumentField, self).__init__(**kwargs)

    @property
    def document_type(self):
        if isinstance(self.document_type_obj, basestring):
            if self.document_type_obj == RECURSIVE_REFERENCE_CONSTANT:
                self.document_type_obj = self.owner_document
            else:
                self.document_type_obj = get_document(self.document_type_obj)
        return self.document_type_obj

    def to_python(self, value):
        if not isinstance(value, self.document_type):
            return self.document_type._from_son(value)
        return value

    def to_mongo(self, value):
        if not isinstance(value, self.document_type):
            return value
        return self.document_type.to_mongo(value)

    def validate(self, value, clean=True):
        """Make sure that the document instance is an instance of the
        EmbeddedDocument subclass provided when the document was defined.
        """
        # Using isinstance also works for subclasses of self.document
        if not isinstance(value, self.document_type):
            self.error('Invalid embedded document instance provided to an '
                       'EmbeddedDocumentField')
        self.document_type.validate(value, clean)

    def lookup_member(self, member_name):
        return self.document_type._fields.get(member_name)

    def prepare_query_value(self, op, value):
        return self.to_mongo(value)


class GenericEmbeddedDocumentField(BaseField):
    """A generic embedded document field - allows any
    :class:`~mongoengine.EmbeddedDocument` to be stored.

    Only valid values are subclasses of :class:`~mongoengine.EmbeddedDocument`.

    .. note ::
        You can use the choices param to limit the acceptable
        EmbeddedDocument types
    """

    def prepare_query_value(self, op, value):
        return self.to_mongo(value)

    def to_python(self, value):
        if isinstance(value, dict):
            doc_cls = get_document(value['_cls'])
            value = doc_cls._from_son(value)

        return value

    def validate(self, value, clean=True):
        if not isinstance(value, EmbeddedDocument):
            self.error('Invalid embedded document instance provided to an '
                       'GenericEmbeddedDocumentField')

        value.validate(clean=clean)

    def to_mongo(self, document):
        if document is None:
            return None

        data = document.to_mongo()
        if not '_cls' in data:
            data['_cls'] = document._class_name
        return data


class DynamicField(BaseField):
    """A truly dynamic field type capable of handling different and varying
    types of data.

    Used by :class:`~mongoengine.DynamicDocument` to handle dynamic data"""

    def to_mongo(self, value):
        """Convert a Python type to a MongoDBcompatible type.
        """

        if isinstance(value, basestring):
            return value

        if hasattr(value, 'to_mongo'):
            cls = value.__class__
            val = value.to_mongo()
            # If we its a document thats not inherited add _cls
            if (isinstance(value, Document)):
                val = {"_ref": value.to_dbref(), "_cls": cls.__name__}
            if (isinstance(value, EmbeddedDocument)):
                val['_cls'] = cls.__name__
            return val

        if not isinstance(value, (dict, list, tuple)):
            return value

        is_list = False
        if not hasattr(value, 'items'):
            is_list = True
            value = dict([(k, v) for k, v in enumerate(value)])

        data = {}
        for k, v in value.iteritems():
            data[k] = self.to_mongo(v)

        value = data
        if is_list:  # Convert back to a list
            value = [v for k, v in sorted(data.iteritems(), key=itemgetter(0))]
        return value

    def to_python(self, value):
        if isinstance(value, dict) and '_cls' in value:
            doc_cls = get_document(value['_cls'])
            if '_ref' in value:
                value = doc_cls._get_db().dereference(value['_ref'])
            return doc_cls._from_son(value)

        return super(DynamicField, self).to_python(value)

    def lookup_member(self, member_name):
        return member_name

    def prepare_query_value(self, op, value):
        if isinstance(value, basestring):
            from mongoengine.fields import StringField
            return StringField().prepare_query_value(op, value)
        return self.to_mongo(value)

    def validate(self, value, clean=True):
        if hasattr(value, "validate"):
            value.validate(clean=clean)


class ListField(ComplexBaseField):
    """A list field that wraps a standard field, allowing multiple instances
    of the field to be used as a list in the database.

    If using with ReferenceFields see: :ref:`one-to-many-with-listfields`

    .. note::
        Required means it cannot be empty - as the default for ListFields is []
    """

    def __init__(self, field=None, **kwargs):
        self.field = field
        kwargs.setdefault('default', lambda: [])
        super(ListField, self).__init__(**kwargs)

    def validate(self, value):
        """Make sure that a list of valid fields is being used.
        """
        if (not isinstance(value, (list, tuple, QuerySet)) or
           isinstance(value, basestring)):
            self.error('Only lists and tuples may be used in a list field')
        super(ListField, self).validate(value)

    def prepare_query_value(self, op, value):
        if self.field:
            if op in ('set', 'unset') and (not isinstance(value, basestring)
               and not isinstance(value, BaseDocument)
               and hasattr(value, '__iter__')):
                return [self.field.prepare_query_value(op, v) for v in value]
            return self.field.prepare_query_value(op, value)
        return super(ListField, self).prepare_query_value(op, value)


class SortedListField(ListField):
    """A ListField that sorts the contents of its list before writing to
    the database in order to ensure that a sorted list is always
    retrieved.

    .. warning::
        There is a potential race condition when handling lists.  If you set /
        save the whole list then other processes trying to save the whole list
        as well could overwrite changes.  The safest way to append to a list is
        to perform a push operation.

    .. versionadded:: 0.4
    .. versionchanged:: 0.6 - added reverse keyword
    """

    _ordering = None
    _order_reverse = False

    def __init__(self, field, **kwargs):
        if 'ordering' in kwargs.keys():
            self._ordering = kwargs.pop('ordering')
        if 'reverse' in kwargs.keys():
            self._order_reverse = kwargs.pop('reverse')
        super(SortedListField, self).__init__(field, **kwargs)

    def to_mongo(self, value):
        value = super(SortedListField, self).to_mongo(value)
        if self._ordering is not None:
            return sorted(value, key=itemgetter(self._ordering),
                          reverse=self._order_reverse)
        return sorted(value, reverse=self._order_reverse)

def key_not_string(d):
    """ Helper function to recursively determine if any key in a dictionary is
    not a string.
    """
    for k, v in d.items():
        if not isinstance(k, basestring) or (isinstance(v, dict) and key_not_string(v)):
            return True

def key_has_dot_or_dollar(d):
    """ Helper function to recursively determine if any key in a dictionary
    contains a dot or a dollar sign.
    """
    for k, v in d.items():
        if ('.' in k or '$' in k) or (isinstance(v, dict) and key_has_dot_or_dollar(v)):
            return True

class DictField(ComplexBaseField):
    """A dictionary field that wraps a standard Python dictionary. This is
    similar to an embedded document, but the structure is not defined.

    .. note::
        Required means it cannot be empty - as the default for ListFields is []

    .. versionadded:: 0.3
    .. versionchanged:: 0.5 - Can now handle complex / varying types of data
    """

    def __init__(self, basecls=None, field=None, *args, **kwargs):
        self.field = field
        self.basecls = basecls or BaseField
        if not issubclass(self.basecls, BaseField):
            self.error('DictField only accepts dict values')
        kwargs.setdefault('default', lambda: {})
        super(DictField, self).__init__(*args, **kwargs)

    def validate(self, value):
        """Make sure that a list of valid fields is being used.
        """
        if not isinstance(value, dict):
            self.error('Only dictionaries may be used in a DictField')

        if key_not_string(value):
            msg = ("Invalid dictionary key - documents must "
                   "have only string keys")
            self.error(msg)
        if key_has_dot_or_dollar(value):
            self.error('Invalid dictionary key name - keys may not contain "."'
                       ' or "$" characters')
        super(DictField, self).validate(value)

    def lookup_member(self, member_name):
        return DictField(basecls=self.basecls, db_field=member_name)

    def prepare_query_value(self, op, value):
        match_operators = ['contains', 'icontains', 'startswith',
                           'istartswith', 'endswith', 'iendswith',
                           'exact', 'iexact']

        if op in match_operators and isinstance(value, basestring):
            return StringField().prepare_query_value(op, value)

        if hasattr(self.field, 'field'):
            return self.field.prepare_query_value(op, value)

        return super(DictField, self).prepare_query_value(op, value)


class MapField(DictField):
    """A field that maps a name to a specified field type. Similar to
    a DictField, except the 'value' of each item must match the specified
    field type.

    .. versionadded:: 0.5
    """

    def __init__(self, field=None, *args, **kwargs):
        if not isinstance(field, BaseField):
            self.error('Argument to MapField constructor must be a valid '
                       'field')
        super(MapField, self).__init__(field=field, *args, **kwargs)


class ReferenceField(BaseField):
    """A reference to a document that will be automatically dereferenced on
    access (lazily).

    Use the `reverse_delete_rule` to handle what should happen if the document
    the field is referencing is deleted.  EmbeddedDocuments, DictFields and
    MapFields do not support reverse_delete_rules and an `InvalidDocumentError`
    will be raised if trying to set on one of these Document / Field types.

    The options are:

      * DO_NOTHING  - don't do anything (default).
      * NULLIFY     - Updates the reference to null.
      * CASCADE     - Deletes the documents associated with the reference.
      * DENY        - Prevent the deletion of the reference object.
      * PULL        - Pull the reference from a :class:`~mongoengine.fields.ListField`
                      of references

    Alternative syntax for registering delete rules (useful when implementing
    bi-directional delete rules)

    .. code-block:: python

        class Bar(Document):
            content = StringField()
            foo = ReferenceField('Foo')

        Bar.register_delete_rule(Foo, 'bar', NULLIFY)

    .. note ::
        `reverse_delete_rules` do not trigger pre / post delete signals to be
        triggered.

    .. versionchanged:: 0.5 added `reverse_delete_rule`
    """

    def __init__(self, document_type, dbref=False,
                 reverse_delete_rule=DO_NOTHING, **kwargs):
        """Initialises the Reference Field.

        :param dbref:  Store the reference as :class:`~pymongo.dbref.DBRef`
          or as the :class:`~pymongo.objectid.ObjectId`.id .
        :param reverse_delete_rule: Determines what to do when the referring
          object is deleted
        """
        if not isinstance(document_type, basestring):
            if not issubclass(document_type, (Document, basestring)):
                self.error('Argument to ReferenceField constructor must be a '
                           'document class or a string')

        self.dbref = dbref
        self.document_type_obj = document_type
        self.reverse_delete_rule = reverse_delete_rule
        super(ReferenceField, self).__init__(**kwargs)

    @property
    def document_type(self):
        if isinstance(self.document_type_obj, basestring):
            if self.document_type_obj == RECURSIVE_REFERENCE_CONSTANT:
                self.document_type_obj = self.owner_document
            else:
                self.document_type_obj = get_document(self.document_type_obj)
        return self.document_type_obj

    def __get__(self, instance, owner):
        """Descriptor to allow lazy dereferencing.
        """
        if instance is None:
            # Document class being used rather than a document object
            return self

        # Get value from document instance if available
        value = instance._data.get(self.name)
        self._auto_dereference = instance._fields[self.name]._auto_dereference
        # Dereference DBRefs
        if self._auto_dereference and isinstance(value, DBRef):
            value = self.document_type._get_db().dereference(value)
            if value is not None:
                instance._data[self.name] = self.document_type._from_son(value)

        return super(ReferenceField, self).__get__(instance, owner)

    def to_mongo(self, document):
        if isinstance(document, DBRef):
            if not self.dbref:
                return document.id
            return document

        id_field_name = self.document_type._meta['id_field']
        id_field = self.document_type._fields[id_field_name]

        if isinstance(document, Document):
            # We need the id from the saved object to create the DBRef
            id_ = document.pk
            if id_ is None:
                self.error('You can only reference documents once they have'
                           ' been saved to the database')
        else:
            id_ = document

        id_ = id_field.to_mongo(id_)
        if self.dbref:
            collection = self.document_type._get_collection_name()
            return DBRef(collection, id_)

        return id_

    def to_python(self, value):
        """Convert a MongoDB-compatible type to a Python type.
        """
        if (not self.dbref and
           not isinstance(value, (DBRef, Document, EmbeddedDocument))):
            collection = self.document_type._get_collection_name()
            value = DBRef(collection, self.document_type.id.to_python(value))
        return value

    def prepare_query_value(self, op, value):
        if value is None:
            return None
        return self.to_mongo(value)

    def validate(self, value):

        if not isinstance(value, (self.document_type, DBRef)):
            self.error("A ReferenceField only accepts DBRef or documents")

        if isinstance(value, Document) and value.id is None:
            self.error('You can only reference documents once they have been '
                       'saved to the database')

    def lookup_member(self, member_name):
        return self.document_type._fields.get(member_name)


class GenericReferenceField(BaseField):
    """A reference to *any* :class:`~mongoengine.document.Document` subclass
    that will be automatically dereferenced on access (lazily).

    .. note ::
        * Any documents used as a generic reference must be registered in the
          document registry.  Importing the model will automatically register
          it.

        * You can use the choices param to limit the acceptable Document types

    .. versionadded:: 0.3
    """

    def __get__(self, instance, owner):
        if instance is None:
            return self

        value = instance._data.get(self.name)
        self._auto_dereference = instance._fields[self.name]._auto_dereference
        if self._auto_dereference and isinstance(value, (dict, SON)):
            instance._data[self.name] = self.dereference(value)

        return super(GenericReferenceField, self).__get__(instance, owner)

    def validate(self, value):
        if not isinstance(value, (Document, DBRef, dict, SON)):
            self.error('GenericReferences can only contain documents')

        if isinstance(value, (dict, SON)):
            if '_ref' not in value or '_cls' not in value:
                self.error('GenericReferences can only contain documents')

        # We need the id from the saved object to create the DBRef
        elif isinstance(value, Document) and value.id is None:
            self.error('You can only reference documents once they have been'
                       ' saved to the database')

    def dereference(self, value):
        doc_cls = get_document(value['_cls'])
        reference = value['_ref']
        doc = doc_cls._get_db().dereference(reference)
        if doc is not None:
            doc = doc_cls._from_son(doc)
        return doc

    def to_mongo(self, document):
        if document is None:
            return None

        if isinstance(document, (dict, SON)):
            return document

        id_field_name = document.__class__._meta['id_field']
        id_field = document.__class__._fields[id_field_name]

        if isinstance(document, Document):
            # We need the id from the saved object to create the DBRef
            id_ = document.id
            if id_ is None:
                self.error('You can only reference documents once they have'
                           ' been saved to the database')
        else:
            id_ = document

        id_ = id_field.to_mongo(id_)
        collection = document._get_collection_name()
        ref = DBRef(collection, id_)
        return SON((
            ('_cls', document._class_name),
            ('_ref', ref)
        ))

    def prepare_query_value(self, op, value):
        if value is None:
            return None

        return self.to_mongo(value)


class BinaryField(BaseField):
    """A binary data field.
    """

    def __init__(self, max_bytes=None, **kwargs):
        self.max_bytes = max_bytes
        super(BinaryField, self).__init__(**kwargs)

    def __set__(self, instance, value):
        """Handle bytearrays in python 3.1"""
        if PY3 and isinstance(value, bytearray):
            value = bin_type(value)
        return super(BinaryField, self).__set__(instance, value)

    def to_mongo(self, value):
        return Binary(value)

    def validate(self, value):
        if not isinstance(value, (bin_type, txt_type, Binary)):
            self.error("BinaryField only accepts instances of "
                       "(%s, %s, Binary)" % (
                       bin_type.__name__, txt_type.__name__))

        if self.max_bytes is not None and len(value) > self.max_bytes:
            self.error('Binary value is too long')


class GridFSError(Exception):
    pass


class GridFSProxy(object):
    """Proxy object to handle writing and reading of files to and from GridFS

    .. versionadded:: 0.4
    .. versionchanged:: 0.5 - added optional size param to read
    .. versionchanged:: 0.6 - added collection name param
    """

    _fs = None

    def __init__(self, grid_id=None, key=None,
                 instance=None,
                 db_alias=DEFAULT_CONNECTION_NAME,
                 collection_name='fs'):
        self.grid_id = grid_id                  # Store GridFS id for file
        self.key = key
        self.instance = instance
        self.db_alias = db_alias
        self.collection_name = collection_name
        self.newfile = None                     # Used for partial writes
        self.gridout = None

    def __getattr__(self, name):
        attrs = ('_fs', 'grid_id', 'key', 'instance', 'db_alias',
                 'collection_name', 'newfile', 'gridout')
        if name in attrs:
            return self.__getattribute__(name)
        obj = self.get()
        if hasattr(obj, name):
            return getattr(obj, name)
        raise AttributeError

    def __get__(self, instance, value):
        return self

    def __nonzero__(self):
        return bool(self.grid_id)

    def __getstate__(self):
        self_dict = self.__dict__
        self_dict['_fs'] = None
        return self_dict

    def __copy__(self):
        copied = GridFSProxy()
        copied.__dict__.update(self.__getstate__())
        return copied

    def __deepcopy__(self, memo):
        return self.__copy__()

    def __repr__(self):
        return '<%s: %s>' % (self.__class__.__name__, self.grid_id)

    def __str__(self):
        name = getattr(self.get(), 'filename', self.grid_id) if self.get() else '(no file)'
        return '<%s: %s>' % (self.__class__.__name__, name)

    def __eq__(self, other):
        if isinstance(other, GridFSProxy):
            return ((self.grid_id == other.grid_id) and
                    (self.collection_name == other.collection_name) and
                    (self.db_alias == other.db_alias))
        else:
            return False

    @property
    def fs(self):
        if not self._fs:
            self._fs = gridfs.GridFS(get_db(self.db_alias), self.collection_name)
        return self._fs

    def get(self, id=None):
        if id:
            self.grid_id = id
        if self.grid_id is None:
            return None
        try:
            if self.gridout is None:
                self.gridout = self.fs.get(self.grid_id)
            return self.gridout
        except:
            # File has been deleted
            return None

    def new_file(self, **kwargs):
        self.newfile = self.fs.new_file(**kwargs)
        self.grid_id = self.newfile._id

    def put(self, file_obj, **kwargs):
        if self.grid_id:
            raise GridFSError('This document already has a file. Either delete '
                              'it or call replace to overwrite it')
        self.grid_id = self.fs.put(file_obj, **kwargs)
        self._mark_as_changed()

    def write(self, string):
        if self.grid_id:
            if not self.newfile:
                raise GridFSError('This document already has a file. Either '
                                  'delete it or call replace to overwrite it')
        else:
            self.new_file()
        self.newfile.write(string)

    def writelines(self, lines):
        if not self.newfile:
            self.new_file()
            self.grid_id = self.newfile._id
        self.newfile.writelines(lines)

    def read(self, size=-1):
        gridout = self.get()
        if gridout is None:
            return None
        else:
            try:
                return gridout.read(size)
            except:
                return ""

    def delete(self):
        # Delete file from GridFS, FileField still remains
        self.fs.delete(self.grid_id)
        self.grid_id = None
        self.gridout = None
        self._mark_as_changed()

    def replace(self, file_obj, **kwargs):
        self.delete()
        self.put(file_obj, **kwargs)

    def close(self):
        if self.newfile:
            self.newfile.close()

    def _mark_as_changed(self):
        """Inform the instance that `self.key` has been changed"""
        if self.instance:
            self.instance._mark_as_changed(self.key)


class FileField(BaseField):
    """A GridFS storage field.

    .. versionadded:: 0.4
    .. versionchanged:: 0.5 added optional size param for read
    .. versionchanged:: 0.6 added db_alias for multidb support
    """
    proxy_class = GridFSProxy

    def __init__(self,
                 db_alias=DEFAULT_CONNECTION_NAME,
                 collection_name="fs", **kwargs):
        super(FileField, self).__init__(**kwargs)
        self.collection_name = collection_name
        self.db_alias = db_alias

    def __get__(self, instance, owner):
        if instance is None:
            return self

        # Check if a file already exists for this model
        grid_file = instance._data.get(self.name)
        if not isinstance(grid_file, self.proxy_class):
            grid_file = self.get_proxy_obj(key=self.name, instance=instance)
            instance._data[self.name] = grid_file

        if not grid_file.key:
            grid_file.key = self.name
            grid_file.instance = instance
        return grid_file

    def __set__(self, instance, value):
        key = self.name
        if ((hasattr(value, 'read') and not
             isinstance(value, GridFSProxy)) or isinstance(value, str_types)):
            # using "FileField() = file/string" notation
            grid_file = instance._data.get(self.name)
            # If a file already exists, delete it
            if grid_file:
                try:
                    grid_file.delete()
                except:
                    pass

            # Create a new proxy object as we don't already have one
            instance._data[key] = self.get_proxy_obj(key=key, instance=instance)
            instance._data[key].put(value)
        else:
            instance._data[key] = value

        instance._mark_as_changed(key)

    def get_proxy_obj(self, key, instance, db_alias=None, collection_name=None):
        if db_alias is None:
            db_alias = self.db_alias
        if collection_name is None:
            collection_name = self.collection_name

        return self.proxy_class(key=key, instance=instance,
                                db_alias=db_alias,
                                collection_name=collection_name)

    def to_mongo(self, value):
        # Store the GridFS file id in MongoDB
        if isinstance(value, self.proxy_class) and value.grid_id is not None:
            return value.grid_id
        return None

    def to_python(self, value):
        if value is not None:
            return self.proxy_class(value,
                                    collection_name=self.collection_name,
                                    db_alias=self.db_alias)

    def validate(self, value):
        if value.grid_id is not None:
            if not isinstance(value, self.proxy_class):
                self.error('FileField only accepts GridFSProxy values')
            if not isinstance(value.grid_id, ObjectId):
                self.error('Invalid GridFSProxy value')


class ImageGridFsProxy(GridFSProxy):
    """
    Proxy for ImageField

    versionadded: 0.6
    """
    def put(self, file_obj, **kwargs):
        """
        Insert a image in database
        applying field properties (size, thumbnail_size)
        """
        field = self.instance._fields[self.key]
        # Handle nested fields
        if hasattr(field, 'field') and isinstance(field.field, FileField):
            field = field.field

        try:
            img = Image.open(file_obj)
            img_format = img.format
        except Exception, e:
            raise ValidationError('Invalid image: %s' % e)

        if (field.size and (img.size[0] > field.size['width'] or
                            img.size[1] > field.size['height'])):
            size = field.size

            if size['force']:
                img = ImageOps.fit(img,
                                   (size['width'],
                                    size['height']),
                                   Image.ANTIALIAS)
            else:
                img.thumbnail((size['width'],
                               size['height']),
                              Image.ANTIALIAS)

        thumbnail = None
        if field.thumbnail_size:
            size = field.thumbnail_size

            if size['force']:
                thumbnail = ImageOps.fit(img, (size['width'], size['height']), Image.ANTIALIAS)
            else:
                thumbnail = img.copy()
                thumbnail.thumbnail((size['width'],
                                     size['height']),
                                    Image.ANTIALIAS)

        if thumbnail:
            thumb_id = self._put_thumbnail(thumbnail, img_format)
        else:
            thumb_id = None

        w, h = img.size

        io = StringIO()
        img.save(io, img_format)
        io.seek(0)

        return super(ImageGridFsProxy, self).put(io,
                                                 width=w,
                                                 height=h,
                                                 format=img_format,
                                                 thumbnail_id=thumb_id,
                                                 **kwargs)

    def delete(self, *args, **kwargs):
        #deletes thumbnail
        out = self.get()
        if out and out.thumbnail_id:
            self.fs.delete(out.thumbnail_id)

        return super(ImageGridFsProxy, self).delete(*args, **kwargs)

    def _put_thumbnail(self, thumbnail, format, **kwargs):
        w, h = thumbnail.size

        io = StringIO()
        thumbnail.save(io, format)
        io.seek(0)

        return self.fs.put(io, width=w,
                           height=h,
                           format=format,
                           **kwargs)

    @property
    def size(self):
        """
        return a width, height of image
        """
        out = self.get()
        if out:
            return out.width, out.height

    @property
    def format(self):
        """
        return format of image
        ex: PNG, JPEG, GIF, etc
        """
        out = self.get()
        if out:
            return out.format

    @property
    def thumbnail(self):
        """
        return a gridfs.grid_file.GridOut
        representing a thumbnail of Image
        """
        out = self.get()
        if out and out.thumbnail_id:
            return self.fs.get(out.thumbnail_id)

    def write(self, *args, **kwargs):
        raise RuntimeError("Please use \"put\" method instead")

    def writelines(self, *args, **kwargs):
        raise RuntimeError("Please use \"put\" method instead")


class ImproperlyConfigured(Exception):
    pass


class ImageField(FileField):
    """
    A Image File storage field.

    @size (width, height, force):
        max size to store images, if larger will be automatically resized
        ex: size=(800, 600, True)

    @thumbnail (width, height, force):
        size to generate a thumbnail

    .. versionadded:: 0.6
    """
    proxy_class = ImageGridFsProxy

    def __init__(self, size=None, thumbnail_size=None,
                 collection_name='images', **kwargs):
        if not Image:
            raise ImproperlyConfigured("PIL library was not found")

        params_size = ('width', 'height', 'force')
        extra_args = dict(size=size, thumbnail_size=thumbnail_size)
        for att_name, att in extra_args.items():
            value = None
            if isinstance(att, (tuple, list)):
                if PY3:
                    value = dict(itertools.zip_longest(params_size, att,
                                                       fillvalue=None))
                else:
                    value = dict(map(None, params_size, att))

            setattr(self, att_name, value)

        super(ImageField, self).__init__(
            collection_name=collection_name,
            **kwargs)


class SequenceField(BaseField):
    """Provides a sequental counter see:
     http://www.mongodb.org/display/DOCS/Object+IDs#ObjectIDs-SequenceNumbers

    .. note::

             Although traditional databases often use increasing sequence
             numbers for primary keys. In MongoDB, the preferred approach is to
             use Object IDs instead.  The concept is that in a very large
             cluster of machines, it is easier to create an object ID than have
             global, uniformly increasing sequence numbers.

    Use any callable as `value_decorator` to transform calculated counter into
    any value suitable for your needs, e.g. string or hexadecimal
    representation of the default integer counter value.

    .. versionadded:: 0.5

    .. versionchanged:: 0.8 added `value_decorator`
    """

    _auto_gen = True
    COLLECTION_NAME = 'mongoengine.counters'
    VALUE_DECORATOR = int

    def __init__(self, collection_name=None, db_alias=None, sequence_name=None,
                 value_decorator=None, *args, **kwargs):
        self.collection_name = collection_name or self.COLLECTION_NAME
        self.db_alias = db_alias or DEFAULT_CONNECTION_NAME
        self.sequence_name = sequence_name
        self.value_decorator = (callable(value_decorator) and
                                value_decorator or self.VALUE_DECORATOR)
        return super(SequenceField, self).__init__(*args, **kwargs)

    def generate(self):
        """
        Generate and Increment the counter
        """
        sequence_name = self.get_sequence_name()
        sequence_id = "%s.%s" % (sequence_name, self.name)
        collection = get_db(alias=self.db_alias)[self.collection_name]
        counter = collection.find_and_modify(query={"_id": sequence_id},
                                             update={"$inc": {"next": 1}},
                                             new=True,
                                             upsert=True)
        return self.value_decorator(counter['next'])

    def set_next_value(self, value):
        """Helper method to set the next sequence value"""
        sequence_name = self.get_sequence_name()
        sequence_id = "%s.%s" % (sequence_name, self.name)
        collection = get_db(alias=self.db_alias)[self.collection_name]
        counter = collection.find_and_modify(query={"_id": sequence_id},
                                             update={"$set": {"next": value}},
                                             new=True,
                                             upsert=True)
        return self.value_decorator(counter['next'])

    def get_next_value(self):
        """Helper method to get the next value for previewing.

        .. warning:: There is no guarantee this will be the next value
        as it is only fixed on set.
        """
        sequence_name = self.get_sequence_name()
        sequence_id = "%s.%s" % (sequence_name, self.name)
        collection = get_db(alias=self.db_alias)[self.collection_name]
        data = collection.find_one({"_id": sequence_id})

        if data:
            return self.value_decorator(data['next']+1)

        return self.value_decorator(1)

    def get_sequence_name(self):
        if self.sequence_name:
            return self.sequence_name
        owner = self.owner_document
        if issubclass(owner, Document):
            return owner._get_collection_name()
        else:
            return ''.join('_%s' % c if c.isupper() else c
                           for c in owner._class_name).strip('_').lower()

    def __get__(self, instance, owner):
        value = super(SequenceField, self).__get__(instance, owner)
        if value is None and instance._initialised:
            value = self.generate()
            instance._data[self.name] = value
            instance._mark_as_changed(self.name)

        return value

    def __set__(self, instance, value):

        if value is None and instance._initialised:
            value = self.generate()

        return super(SequenceField, self).__set__(instance, value)

    def to_python(self, value):
        if value is None:
            value = self.generate()
        return value


class UUIDField(BaseField):
    """A UUID field.

    .. versionadded:: 0.6
    """
    _binary = None

    def __init__(self, binary=True, **kwargs):
        """
        Store UUID data in the database

        :param binary: if False store as a string.

        .. versionchanged:: 0.8.0
        .. versionchanged:: 0.6.19
        """
        self._binary = binary
        super(UUIDField, self).__init__(**kwargs)

    def to_python(self, value):
        if not self._binary:
            original_value = value
            try:
                if not isinstance(value, basestring):
                    value = unicode(value)
                return uuid.UUID(value)
            except:
                return original_value
        return value

    def to_mongo(self, value):
        if not self._binary:
            return unicode(value)
        elif isinstance(value, basestring):
            return uuid.UUID(value)
        return value

    def prepare_query_value(self, op, value):
        if value is None:
            return None
        return self.to_mongo(value)

    def validate(self, value):
        if not isinstance(value, uuid.UUID):
            if not isinstance(value, basestring):
                value = str(value)
            try:
                value = uuid.UUID(value)
            except Exception, exc:
                self.error('Could not convert to UUID: %s' % exc)


class GeoPointField(BaseField):
    """A list storing a latitude and longitude.

    .. versionadded:: 0.4
    """

    _geo_index = pymongo.GEO2D

    def validate(self, value):
        """Make sure that a geo-value is of type (x, y)
        """
        if not isinstance(value, (list, tuple)):
            self.error('GeoPointField can only accept tuples or lists '
                       'of (x, y)')

        if not len(value) == 2:
            self.error("Value (%s) must be a two-dimensional point" % repr(value))
        elif (not isinstance(value[0], (float, int)) or
              not isinstance(value[1], (float, int))):
            self.error("Both values (%s) in point must be float or int" % repr(value))


class PointField(GeoJsonBaseField):
    """A geo json field storing a latitude and longitude.

    The data is represented as:

    .. code-block:: js

        { "type" : "Point" ,
          "coordinates" : [x, y]}

    You can either pass a dict with the full information or a list
    to set the value.

    Requires mongodb >= 2.4
    .. versionadded:: 0.8
    """
    _type = "Point"


class LineStringField(GeoJsonBaseField):
    """A geo json field storing a line of latitude and longitude coordinates.

    The data is represented as:

    .. code-block:: js

        { "type" : "LineString" ,
          "coordinates" : [[x1, y1], [x1, y1] ... [xn, yn]]}

    You can either pass a dict with the full information or a list of points.

    Requires mongodb >= 2.4
    .. versionadded:: 0.8
    """
    _type = "LineString"


class PolygonField(GeoJsonBaseField):
    """A geo json field storing a polygon of latitude and longitude coordinates.

    The data is represented as:

    .. code-block:: js

        { "type" : "Polygon" ,
          "coordinates" : [[[x1, y1], [x1, y1] ... [xn, yn]],
                           [[x1, y1], [x1, y1] ... [xn, yn]]}

    You can either pass a dict with the full information or a list
    of LineStrings. The first LineString being the outside and the rest being
    holes.

    Requires mongodb >= 2.4
    .. versionadded:: 0.8
    """
    _type = "Polygon"

########NEW FILE########
__FILENAME__ = python_support
"""Helper functions and types to aid with Python 2.5 - 3 support."""

import sys

PY3 = sys.version_info[0] == 3
PY25 = sys.version_info[:2] == (2, 5)
UNICODE_KWARGS = int(''.join([str(x) for x in sys.version_info[:3]])) > 264

if PY3:
    import codecs
    from io import BytesIO as StringIO
    # return s converted to binary.  b('test') should be equivalent to b'test'
    def b(s):
        return codecs.latin_1_encode(s)[0]

    bin_type = bytes
    txt_type   = str
else:
    try:
        from cStringIO import StringIO
    except ImportError:
        from StringIO import StringIO

    # Conversion to binary only necessary in Python 3
    def b(s):
        return s

    bin_type = str
    txt_type = unicode

str_types = (bin_type, txt_type)

if PY25:
    def product(*args, **kwds):
        pools = map(tuple, args) * kwds.get('repeat', 1)
        result = [[]]
        for pool in pools:
            result = [x + [y] for x in result for y in pool]
        for prod in result:
            yield tuple(prod)
    reduce = reduce
else:
    from itertools import product
    from functools import reduce


# For use with Python 2.5
# converts all keys from unicode to str for d and all nested dictionaries
def to_str_keys_recursive(d):
    if isinstance(d, list):
        for val in d:
            if isinstance(val, (dict, list)):
                to_str_keys_recursive(val)
    elif isinstance(d, dict):
        for key, val in d.items():
            if isinstance(val, (dict, list)):
                to_str_keys_recursive(val)
            if isinstance(key, unicode):
                d[str(key)] = d.pop(key)
    else:
        raise ValueError("non list/dict parameter not allowed")

########NEW FILE########
__FILENAME__ = base
from __future__ import absolute_import

import copy
import itertools
import operator
import pprint
import re
import warnings

from bson.code import Code
from bson import json_util
import pymongo
from pymongo.common import validate_read_preference

from mongoengine import signals
from mongoengine.common import _import_class
from mongoengine.base.common import get_document
from mongoengine.errors import (OperationError, NotUniqueError,
                                InvalidQueryError, LookUpError)

from mongoengine.queryset import transform
from mongoengine.queryset.field_list import QueryFieldList
from mongoengine.queryset.visitor import Q, QNode


__all__ = ('BaseQuerySet', 'DO_NOTHING', 'NULLIFY', 'CASCADE', 'DENY', 'PULL')

# Delete rules
DO_NOTHING = 0
NULLIFY = 1
CASCADE = 2
DENY = 3
PULL = 4

RE_TYPE = type(re.compile(''))


class BaseQuerySet(object):
    """A set of results returned from a query. Wraps a MongoDB cursor,
    providing :class:`~mongoengine.Document` objects as the results.
    """
    __dereference = False
    _auto_dereference = True

    def __init__(self, document, collection):
        self._document = document
        self._collection_obj = collection
        self._mongo_query = None
        self._query_obj = Q()
        self._initial_query = {}
        self._where_clause = None
        self._loaded_fields = QueryFieldList()
        self._ordering = []
        self._snapshot = False
        self._timeout = True
        self._class_check = True
        self._slave_okay = False
        self._read_preference = None
        self._iter = False
        self._scalar = []
        self._none = False
        self._as_pymongo = False
        self._as_pymongo_coerce = False

        # If inheritance is allowed, only return instances and instances of
        # subclasses of the class being used
        if document._meta.get('allow_inheritance') is True:
            if len(self._document._subclasses) == 1:
                self._initial_query = {"_cls": self._document._subclasses[0]}
            else:
                self._initial_query = {"_cls": {"$in": self._document._subclasses}}
            self._loaded_fields = QueryFieldList(always_include=['_cls'])
        self._cursor_obj = None
        self._limit = None
        self._skip = None
        self._hint = -1  # Using -1 as None is a valid value for hint

    def __call__(self, q_obj=None, class_check=True, slave_okay=False,
                 read_preference=None, **query):
        """Filter the selected documents by calling the
        :class:`~mongoengine.queryset.QuerySet` with a query.

        :param q_obj: a :class:`~mongoengine.queryset.Q` object to be used in
            the query; the :class:`~mongoengine.queryset.QuerySet` is filtered
            multiple times with different :class:`~mongoengine.queryset.Q`
            objects, only the last one will be used
        :param class_check: If set to False bypass class name check when
            querying collection
        :param slave_okay: if True, allows this query to be run against a
            replica secondary.
        :params read_preference: if set, overrides connection-level
            read_preference from `ReplicaSetConnection`.
        :param query: Django-style query keyword arguments
        """
        query = Q(**query)
        if q_obj:
            # make sure proper query object is passed
            if not isinstance(q_obj, QNode):
                msg = ("Not a query object: %s. "
                       "Did you intend to use key=value?" % q_obj)
                raise InvalidQueryError(msg)
            query &= q_obj

        if read_preference is None:
            queryset = self.clone()
        else:
            # Use the clone provided when setting read_preference
            queryset = self.read_preference(read_preference)

        queryset._query_obj &= query
        queryset._mongo_query = None
        queryset._cursor_obj = None
        queryset._class_check = class_check

        return queryset

    def __getitem__(self, key):
        """Support skip and limit using getitem and slicing syntax.
        """
        queryset = self.clone()

        # Slice provided
        if isinstance(key, slice):
            try:
                queryset._cursor_obj = queryset._cursor[key]
                queryset._skip, queryset._limit = key.start, key.stop
                if key.start and key.stop:
                    queryset._limit = key.stop - key.start
            except IndexError, err:
                # PyMongo raises an error if key.start == key.stop, catch it,
                # bin it, kill it.
                start = key.start or 0
                if start >= 0 and key.stop >= 0 and key.step is None:
                    if start == key.stop:
                        queryset.limit(0)
                        queryset._skip = key.start
                        queryset._limit = key.stop - start
                        return queryset
                raise err
            # Allow further QuerySet modifications to be performed
            return queryset
        # Integer index provided
        elif isinstance(key, int):
            if queryset._scalar:
                return queryset._get_scalar(
                    queryset._document._from_son(queryset._cursor[key],
                                                 _auto_dereference=self._auto_dereference))
            if queryset._as_pymongo:
                return queryset._get_as_pymongo(queryset._cursor.next())
            return queryset._document._from_son(queryset._cursor[key],
                                                _auto_dereference=self._auto_dereference)
        raise AttributeError

    def __iter__(self):
        raise NotImplementedError

    # Core functions

    def all(self):
        """Returns all documents."""
        return self.__call__()

    def filter(self, *q_objs, **query):
        """An alias of :meth:`~mongoengine.queryset.QuerySet.__call__`
        """
        return self.__call__(*q_objs, **query)

    def get(self, *q_objs, **query):
        """Retrieve the the matching object raising
        :class:`~mongoengine.queryset.MultipleObjectsReturned` or
        `DocumentName.MultipleObjectsReturned` exception if multiple results
        and :class:`~mongoengine.queryset.DoesNotExist` or
        `DocumentName.DoesNotExist` if no results are found.

        .. versionadded:: 0.3
        """
        queryset = self.clone()
        queryset = queryset.limit(2)
        queryset = queryset.filter(*q_objs, **query)

        try:
            result = queryset.next()
        except StopIteration:
            msg = ("%s matching query does not exist."
                   % queryset._document._class_name)
            raise queryset._document.DoesNotExist(msg)
        try:
            queryset.next()
        except StopIteration:
            return result

        queryset.rewind()
        message = u'%d items returned, instead of 1' % queryset.count()
        raise queryset._document.MultipleObjectsReturned(message)

    def create(self, **kwargs):
        """Create new object. Returns the saved object instance.

        .. versionadded:: 0.4
        """
        return self._document(**kwargs).save()

    def get_or_create(self, write_concern=None, auto_save=True,
                      *q_objs, **query):
        """Retrieve unique object or create, if it doesn't exist. Returns a
        tuple of ``(object, created)``, where ``object`` is the retrieved or
        created object and ``created`` is a boolean specifying whether a new
        object was created. Raises
        :class:`~mongoengine.queryset.MultipleObjectsReturned` or
        `DocumentName.MultipleObjectsReturned` if multiple results are found.
        A new document will be created if the document doesn't exists; a
        dictionary of default values for the new document may be provided as a
        keyword argument called :attr:`defaults`.

        .. note:: This requires two separate operations and therefore a
            race condition exists.  Because there are no transactions in
            mongoDB other approaches should be investigated, to ensure you
            don't accidently duplicate data when using this method.  This is
            now scheduled to be removed before 1.0

        :param write_concern: optional extra keyword arguments used if we
            have to create a new document.
            Passes any write_concern onto :meth:`~mongoengine.Document.save`

        :param auto_save: if the object is to be saved automatically if
            not found.

        .. deprecated:: 0.8
        .. versionchanged:: 0.6 - added `auto_save`
        .. versionadded:: 0.3
        """
        msg = ("get_or_create is scheduled to be deprecated.  The approach is "
               "flawed without transactions. Upserts should be preferred.")
        warnings.warn(msg, DeprecationWarning)

        defaults = query.get('defaults', {})
        if 'defaults' in query:
            del query['defaults']

        try:
            doc = self.get(*q_objs, **query)
            return doc, False
        except self._document.DoesNotExist:
            query.update(defaults)
            doc = self._document(**query)

            if auto_save:
                doc.save(write_concern=write_concern)
            return doc, True

    def first(self):
        """Retrieve the first object matching the query.
        """
        queryset = self.clone()
        try:
            result = queryset[0]
        except IndexError:
            result = None
        return result

    def insert(self, doc_or_docs, load_bulk=True, write_concern=None):
        """bulk insert documents

        :param docs_or_doc: a document or list of documents to be inserted
        :param load_bulk (optional): If True returns the list of document
            instances
        :param write_concern: Extra keyword arguments are passed down to
                :meth:`~pymongo.collection.Collection.insert`
                which will be used as options for the resultant
                ``getLastError`` command.  For example,
                ``insert(..., {w: 2, fsync: True})`` will wait until at least
                two servers have recorded the write and will force an fsync on
                each server being written to.

        By default returns document instances, set ``load_bulk`` to False to
        return just ``ObjectIds``

        .. versionadded:: 0.5
        """
        Document = _import_class('Document')

        if write_concern is None:
            write_concern = {}

        docs = doc_or_docs
        return_one = False
        if isinstance(docs, Document) or issubclass(docs.__class__, Document):
            return_one = True
            docs = [docs]

        raw = []
        for doc in docs:
            if not isinstance(doc, self._document):
                msg = ("Some documents inserted aren't instances of %s"
                       % str(self._document))
                raise OperationError(msg)
            if doc.pk and not doc._created:
                msg = "Some documents have ObjectIds use doc.update() instead"
                raise OperationError(msg)
            raw.append(doc.to_mongo())

        signals.pre_bulk_insert.send(self._document, documents=docs)
        try:
            ids = self._collection.insert(raw, **write_concern)
        except pymongo.errors.DuplicateKeyError, err:
            message = 'Could not save document (%s)';
            raise NotUniqueError(message % unicode(err))
        except pymongo.errors.OperationFailure, err:
            message = 'Could not save document (%s)';
            if re.match('^E1100[01] duplicate key', unicode(err)):
                # E11000 - duplicate key error index
                # E11001 - duplicate key on update
                message = u'Tried to save duplicate unique keys (%s)'
                raise NotUniqueError(message % unicode(err))
            raise OperationError(message % unicode(err))

        if not load_bulk:
            signals.post_bulk_insert.send(
                self._document, documents=docs, loaded=False)
            return return_one and ids[0] or ids

        documents = self.in_bulk(ids)
        results = []
        for obj_id in ids:
            results.append(documents.get(obj_id))
        signals.post_bulk_insert.send(
            self._document, documents=results, loaded=True)
        return return_one and results[0] or results

    def count(self, with_limit_and_skip=True):
        """Count the selected elements in the query.

        :param with_limit_and_skip (optional): take any :meth:`limit` or
            :meth:`skip` that has been applied to this cursor into account when
            getting the count
        """
        if self._limit == 0 and with_limit_and_skip or self._none:
            return 0
        return self._cursor.count(with_limit_and_skip=with_limit_and_skip)

    def delete(self, write_concern=None, _from_doc_delete=False):
        """Delete the documents matched by the query.

        :param write_concern: Extra keyword arguments are passed down which
            will be used as options for the resultant
            ``getLastError`` command.  For example,
            ``save(..., write_concern={w: 2, fsync: True}, ...)`` will
            wait until at least two servers have recorded the write and
            will force an fsync on the primary server.
        :param _from_doc_delete: True when called from document delete therefore
            signals will have been triggered so don't loop.
        """
        queryset = self.clone()
        doc = queryset._document

        if write_concern is None:
            write_concern = {}

        # Handle deletes where skips or limits have been applied or
        # there is an untriggered delete signal
        has_delete_signal = signals.signals_available and (
            signals.pre_delete.has_receivers_for(self._document) or
            signals.post_delete.has_receivers_for(self._document))

        call_document_delete = (queryset._skip or queryset._limit or
                                has_delete_signal) and not _from_doc_delete

        if call_document_delete:
            for doc in queryset:
                doc.delete(write_concern=write_concern)
            return

        delete_rules = doc._meta.get('delete_rules') or {}
        # Check for DENY rules before actually deleting/nullifying any other
        # references
        for rule_entry in delete_rules:
            document_cls, field_name = rule_entry
            rule = doc._meta['delete_rules'][rule_entry]
            if rule == DENY and document_cls.objects(
                    **{field_name + '__in': self}).count() > 0:
                msg = ("Could not delete document (%s.%s refers to it)"
                       % (document_cls.__name__, field_name))
                raise OperationError(msg)

        for rule_entry in delete_rules:
            document_cls, field_name = rule_entry
            rule = doc._meta['delete_rules'][rule_entry]
            if rule == CASCADE:
                ref_q = document_cls.objects(**{field_name + '__in': self})
                ref_q_count = ref_q.count()
                if (doc != document_cls and ref_q_count > 0
                   or (doc == document_cls and ref_q_count > 0)):
                    ref_q.delete(write_concern=write_concern)
            elif rule == NULLIFY:
                document_cls.objects(**{field_name + '__in': self}).update(
                    write_concern=write_concern, **{'unset__%s' % field_name: 1})
            elif rule == PULL:
                document_cls.objects(**{field_name + '__in': self}).update(
                    write_concern=write_concern,
                    **{'pull_all__%s' % field_name: self})

        queryset._collection.remove(queryset._query, write_concern=write_concern)

    def update(self, upsert=False, multi=True, write_concern=None,
               full_result=False, **update):
        """Perform an atomic update on the fields matched by the query.

        :param upsert: Any existing document with that "_id" is overwritten.
        :param multi: Update multiple documents.
        :param write_concern: Extra keyword arguments are passed down which
            will be used as options for the resultant
            ``getLastError`` command.  For example,
            ``save(..., write_concern={w: 2, fsync: True}, ...)`` will
            wait until at least two servers have recorded the write and
            will force an fsync on the primary server.
        :param full_result: Return the full result rather than just the number
            updated.
        :param update: Django-style update keyword arguments

        .. versionadded:: 0.2
        """
        if not update and not upsert:
            raise OperationError("No update parameters, would remove data")

        if write_concern is None:
            write_concern = {}

        queryset = self.clone()
        query = queryset._query
        update = transform.update(queryset._document, **update)

        # If doing an atomic upsert on an inheritable class
        # then ensure we add _cls to the update operation
        if upsert and '_cls' in query:
            if '$set' in update:
                update["$set"]["_cls"] = queryset._document._class_name
            else:
                update["$set"] = {"_cls": queryset._document._class_name}
        try:
            result = queryset._collection.update(query, update, multi=multi,
                                                 upsert=upsert, **write_concern)
            if full_result:
                return result
            elif result:
                return result['n']
        except pymongo.errors.OperationFailure, err:
            if unicode(err) == u'multi not coded yet':
                message = u'update() method requires MongoDB 1.1.3+'
                raise OperationError(message)
            raise OperationError(u'Update failed (%s)' % unicode(err))

    def update_one(self, upsert=False, write_concern=None, **update):
        """Perform an atomic update on first field matched by the query.

        :param upsert: Any existing document with that "_id" is overwritten.
        :param write_concern: Extra keyword arguments are passed down which
            will be used as options for the resultant
            ``getLastError`` command.  For example,
            ``save(..., write_concern={w: 2, fsync: True}, ...)`` will
            wait until at least two servers have recorded the write and
            will force an fsync on the primary server.
        :param update: Django-style update keyword arguments

        .. versionadded:: 0.2
        """
        return self.update(
            upsert=upsert, multi=False, write_concern=write_concern, **update)

    def with_id(self, object_id):
        """Retrieve the object matching the id provided.  Uses `object_id` only
        and raises InvalidQueryError if a filter has been applied. Returns
        `None` if no document exists with that id.

        :param object_id: the value for the id of the document to look up

        .. versionchanged:: 0.6 Raises InvalidQueryError if filter has been set
        """
        queryset = self.clone()
        if not queryset._query_obj.empty:
            msg = "Cannot use a filter whilst using `with_id`"
            raise InvalidQueryError(msg)
        return queryset.filter(pk=object_id).first()

    def in_bulk(self, object_ids):
        """Retrieve a set of documents by their ids.

        :param object_ids: a list or tuple of ``ObjectId``\ s
        :rtype: dict of ObjectIds as keys and collection-specific
                Document subclasses as values.

        .. versionadded:: 0.3
        """
        doc_map = {}

        docs = self._collection.find({'_id': {'$in': object_ids}},
                                     **self._cursor_args)
        if self._scalar:
            for doc in docs:
                doc_map[doc['_id']] = self._get_scalar(
                    self._document._from_son(doc))
        elif self._as_pymongo:
            for doc in docs:
                doc_map[doc['_id']] = self._get_as_pymongo(doc)
        else:
            for doc in docs:
                doc_map[doc['_id']] = self._document._from_son(doc)

        return doc_map

    def none(self):
        """Helper that just returns a list"""
        queryset = self.clone()
        queryset._none = True
        return queryset

    def no_sub_classes(self):
        """
        Only return instances of this document and not any inherited documents
        """
        if self._document._meta.get('allow_inheritance') is True:
            self._initial_query = {"_cls": self._document._class_name}

        return self

    def clone(self):
        """Creates a copy of the current
          :class:`~mongoengine.queryset.QuerySet`

        .. versionadded:: 0.5
        """
        return self.clone_into(self.__class__(self._document, self._collection_obj))

    def clone_into(self, cls):
        """Creates a copy of the current
          :class:`~mongoengine.queryset.base.BaseQuerySet` into another child class
        """
        if not isinstance(cls, BaseQuerySet):
            raise OperationError('%s is not a subclass of BaseQuerySet' % cls.__name__)

        copy_props = ('_mongo_query', '_initial_query', '_none', '_query_obj',
                      '_where_clause', '_loaded_fields', '_ordering', '_snapshot',
                      '_timeout', '_class_check', '_slave_okay', '_read_preference',
                      '_iter', '_scalar', '_as_pymongo', '_as_pymongo_coerce',
                      '_limit', '_skip', '_hint', '_auto_dereference')

        for prop in copy_props:
            val = getattr(self, prop)
            setattr(cls, prop, copy.copy(val))

        if self._cursor_obj:
            cls._cursor_obj = self._cursor_obj.clone()

        return cls

    def select_related(self, max_depth=1):
        """Handles dereferencing of :class:`~bson.dbref.DBRef` objects or
        :class:`~bson.object_id.ObjectId` a maximum depth in order to cut down
        the number queries to mongodb.

        .. versionadded:: 0.5
        """
        # Make select related work the same for querysets
        max_depth += 1
        queryset = self.clone()
        return queryset._dereference(queryset, max_depth=max_depth)

    def limit(self, n):
        """Limit the number of returned documents to `n`. This may also be
        achieved using array-slicing syntax (e.g. ``User.objects[:5]``).

        :param n: the maximum number of objects to return
        """
        queryset = self.clone()
        if n == 0:
            queryset._cursor.limit(1)
        else:
            queryset._cursor.limit(n)
        queryset._limit = n
        # Return self to allow chaining
        return queryset

    def skip(self, n):
        """Skip `n` documents before returning the results. This may also be
        achieved using array-slicing syntax (e.g. ``User.objects[5:]``).

        :param n: the number of objects to skip before returning results
        """
        queryset = self.clone()
        queryset._cursor.skip(n)
        queryset._skip = n
        return queryset

    def hint(self, index=None):
        """Added 'hint' support, telling Mongo the proper index to use for the
        query.

        Judicious use of hints can greatly improve query performance. When
        doing a query on multiple fields (at least one of which is indexed)
        pass the indexed field as a hint to the query.

        Hinting will not do anything if the corresponding index does not exist.
        The last hint applied to this cursor takes precedence over all others.

        .. versionadded:: 0.5
        """
        queryset = self.clone()
        queryset._cursor.hint(index)
        queryset._hint = index
        return queryset

    def distinct(self, field):
        """Return a list of distinct values for a given field.

        :param field: the field to select distinct values from

        .. note:: This is a command and won't take ordering or limit into
           account.

        .. versionadded:: 0.4
        .. versionchanged:: 0.5 - Fixed handling references
        .. versionchanged:: 0.6 - Improved db_field refrence handling
        """
        queryset = self.clone()
        try:
            field = self._fields_to_dbfields([field]).pop()
        finally:
            distinct = self._dereference(queryset._cursor.distinct(field), 1,
                                         name=field, instance=self._document)

            # We may need to cast to the correct type eg. ListField(EmbeddedDocumentField)
            doc_field = getattr(self._document._fields.get(field), "field", None)
            instance = getattr(doc_field, "document_type", False)
            if instance:
                distinct = [instance(**doc) for doc in distinct]
            return distinct

    def only(self, *fields):
        """Load only a subset of this document's fields. ::

            post = BlogPost.objects(...).only("title", "author.name")

        .. note :: `only()` is chainable and will perform a union ::
            So with the following it will fetch both: `title` and `author.name`::

                post = BlogPost.objects.only("title").only("author.name")

        :func:`~mongoengine.queryset.QuerySet.all_fields` will reset any
        field filters.

        :param fields: fields to include

        .. versionadded:: 0.3
        .. versionchanged:: 0.5 - Added subfield support
        """
        fields = dict([(f, QueryFieldList.ONLY) for f in fields])
        return self.fields(True, **fields)

    def exclude(self, *fields):
        """Opposite to .only(), exclude some document's fields. ::

            post = BlogPost.objects(...).exclude("comments")

        .. note :: `exclude()` is chainable and will perform a union ::
            So with the following it will exclude both: `title` and `author.name`::

                post = BlogPost.objects.exclude("title").exclude("author.name")

        :func:`~mongoengine.queryset.QuerySet.all_fields` will reset any
        field filters.

        :param fields: fields to exclude

        .. versionadded:: 0.5
        """
        fields = dict([(f, QueryFieldList.EXCLUDE) for f in fields])
        return self.fields(**fields)

    def fields(self, _only_called=False, **kwargs):
        """Manipulate how you load this document's fields.  Used by `.only()`
        and `.exclude()` to manipulate which fields to retrieve.  Fields also
        allows for a greater level of control for example:

        Retrieving a Subrange of Array Elements:

        You can use the $slice operator to retrieve a subrange of elements in
        an array. For example to get the first 5 comments::

            post = BlogPost.objects(...).fields(slice__comments=5)

        :param kwargs: A dictionary identifying what to include

        .. versionadded:: 0.5
        """

        # Check for an operator and transform to mongo-style if there is
        operators = ["slice"]
        cleaned_fields = []
        for key, value in kwargs.items():
            parts = key.split('__')
            op = None
            if parts[0] in operators:
                op = parts.pop(0)
                value = {'$' + op: value}
            key = '.'.join(parts)
            cleaned_fields.append((key, value))

        fields = sorted(cleaned_fields, key=operator.itemgetter(1))
        queryset = self.clone()
        for value, group in itertools.groupby(fields, lambda x: x[1]):
            fields = [field for field, value in group]
            fields = queryset._fields_to_dbfields(fields)
            queryset._loaded_fields += QueryFieldList(fields, value=value, _only_called=_only_called)

        return queryset

    def all_fields(self):
        """Include all fields. Reset all previously calls of .only() or
        .exclude(). ::

            post = BlogPost.objects.exclude("comments").all_fields()

        .. versionadded:: 0.5
        """
        queryset = self.clone()
        queryset._loaded_fields = QueryFieldList(
            always_include=queryset._loaded_fields.always_include)
        return queryset

    def order_by(self, *keys):
        """Order the :class:`~mongoengine.queryset.QuerySet` by the keys. The
        order may be specified by prepending each of the keys by a + or a -.
        Ascending order is assumed.

        :param keys: fields to order the query results by; keys may be
            prefixed with **+** or **-** to determine the ordering direction
        """
        queryset = self.clone()
        queryset._ordering = queryset._get_order_by(keys)
        return queryset

    def explain(self, format=False):
        """Return an explain plan record for the
        :class:`~mongoengine.queryset.QuerySet`\ 's cursor.

        :param format: format the plan before returning it
        """
        plan = self._cursor.explain()
        if format:
            plan = pprint.pformat(plan)
        return plan

    def snapshot(self, enabled):
        """Enable or disable snapshot mode when querying.

        :param enabled: whether or not snapshot mode is enabled

        ..versionchanged:: 0.5 - made chainable
        """
        queryset = self.clone()
        queryset._snapshot = enabled
        return queryset

    def timeout(self, enabled):
        """Enable or disable the default mongod timeout when querying.

        :param enabled: whether or not the timeout is used

        ..versionchanged:: 0.5 - made chainable
        """
        queryset = self.clone()
        queryset._timeout = enabled
        return queryset

    def slave_okay(self, enabled):
        """Enable or disable the slave_okay when querying.

        :param enabled: whether or not the slave_okay is enabled
        """
        queryset = self.clone()
        queryset._slave_okay = enabled
        return queryset

    def read_preference(self, read_preference):
        """Change the read_preference when querying.

        :param read_preference: override ReplicaSetConnection-level
            preference.
        """
        validate_read_preference('read_preference', read_preference)
        queryset = self.clone()
        queryset._read_preference = read_preference
        return queryset

    def scalar(self, *fields):
        """Instead of returning Document instances, return either a specific
        value or a tuple of values in order.

        Can be used along with
        :func:`~mongoengine.queryset.QuerySet.no_dereference` to turn off
        dereferencing.

        .. note:: This effects all results and can be unset by calling
                  ``scalar`` without arguments. Calls ``only`` automatically.

        :param fields: One or more fields to return instead of a Document.
        """
        queryset = self.clone()
        queryset._scalar = list(fields)

        if fields:
            queryset = queryset.only(*fields)
        else:
            queryset = queryset.all_fields()

        return queryset

    def values_list(self, *fields):
        """An alias for scalar"""
        return self.scalar(*fields)

    def as_pymongo(self, coerce_types=False):
        """Instead of returning Document instances, return raw values from
        pymongo.

        :param coerce_type: Field types (if applicable) would be use to
            coerce types.
        """
        queryset = self.clone()
        queryset._as_pymongo = True
        queryset._as_pymongo_coerce = coerce_types
        return queryset

    # JSON Helpers

    def to_json(self, *args, **kwargs):
        """Converts a queryset to JSON"""
        return json_util.dumps(self.as_pymongo(), *args, **kwargs)

    def from_json(self, json_data):
        """Converts json data to unsaved objects"""
        son_data = json_util.loads(json_data)
        return [self._document._from_son(data) for data in son_data]

    # JS functionality

    def map_reduce(self, map_f, reduce_f, output, finalize_f=None, limit=None,
                   scope=None):
        """Perform a map/reduce query using the current query spec
        and ordering. While ``map_reduce`` respects ``QuerySet`` chaining,
        it must be the last call made, as it does not return a maleable
        ``QuerySet``.

        See the :meth:`~mongoengine.tests.QuerySetTest.test_map_reduce`
        and :meth:`~mongoengine.tests.QuerySetTest.test_map_advanced`
        tests in ``tests.queryset.QuerySetTest`` for usage examples.

        :param map_f: map function, as :class:`~bson.code.Code` or string
        :param reduce_f: reduce function, as
                         :class:`~bson.code.Code` or string
        :param output: output collection name, if set to 'inline' will try to
           use :class:`~pymongo.collection.Collection.inline_map_reduce`
           This can also be a dictionary containing output options
           see: http://docs.mongodb.org/manual/reference/command/mapReduce/#dbcmd.mapReduce
        :param finalize_f: finalize function, an optional function that
                           performs any post-reduction processing.
        :param scope: values to insert into map/reduce global scope. Optional.
        :param limit: number of objects from current query to provide
                      to map/reduce method

        Returns an iterator yielding
        :class:`~mongoengine.document.MapReduceDocument`.

        .. note::

            Map/Reduce changed in server version **>= 1.7.4**. The PyMongo
            :meth:`~pymongo.collection.Collection.map_reduce` helper requires
            PyMongo version **>= 1.11**.

        .. versionchanged:: 0.5
           - removed ``keep_temp`` keyword argument, which was only relevant
             for MongoDB server versions older than 1.7.4

        .. versionadded:: 0.3
        """
        queryset = self.clone()

        MapReduceDocument = _import_class('MapReduceDocument')

        if not hasattr(self._collection, "map_reduce"):
            raise NotImplementedError("Requires MongoDB >= 1.7.1")

        map_f_scope = {}
        if isinstance(map_f, Code):
            map_f_scope = map_f.scope
            map_f = unicode(map_f)
        map_f = Code(queryset._sub_js_fields(map_f), map_f_scope)

        reduce_f_scope = {}
        if isinstance(reduce_f, Code):
            reduce_f_scope = reduce_f.scope
            reduce_f = unicode(reduce_f)
        reduce_f_code = queryset._sub_js_fields(reduce_f)
        reduce_f = Code(reduce_f_code, reduce_f_scope)

        mr_args = {'query': queryset._query}

        if finalize_f:
            finalize_f_scope = {}
            if isinstance(finalize_f, Code):
                finalize_f_scope = finalize_f.scope
                finalize_f = unicode(finalize_f)
            finalize_f_code = queryset._sub_js_fields(finalize_f)
            finalize_f = Code(finalize_f_code, finalize_f_scope)
            mr_args['finalize'] = finalize_f

        if scope:
            mr_args['scope'] = scope

        if limit:
            mr_args['limit'] = limit

        if output == 'inline' and not queryset._ordering:
            map_reduce_function = 'inline_map_reduce'
        else:
            map_reduce_function = 'map_reduce'
            mr_args['out'] = output

        results = getattr(queryset._collection, map_reduce_function)(
                          map_f, reduce_f, **mr_args)

        if map_reduce_function == 'map_reduce':
            results = results.find()

        if queryset._ordering:
            results = results.sort(queryset._ordering)

        for doc in results:
            yield MapReduceDocument(queryset._document, queryset._collection,
                                    doc['_id'], doc['value'])

    def exec_js(self, code, *fields, **options):
        """Execute a Javascript function on the server. A list of fields may be
        provided, which will be translated to their correct names and supplied
        as the arguments to the function. A few extra variables are added to
        the function's scope: ``collection``, which is the name of the
        collection in use; ``query``, which is an object representing the
        current query; and ``options``, which is an object containing any
        options specified as keyword arguments.

        As fields in MongoEngine may use different names in the database (set
        using the :attr:`db_field` keyword argument to a :class:`Field`
        constructor), a mechanism exists for replacing MongoEngine field names
        with the database field names in Javascript code. When accessing a
        field, use square-bracket notation, and prefix the MongoEngine field
        name with a tilde (~).

        :param code: a string of Javascript code to execute
        :param fields: fields that you will be using in your function, which
            will be passed in to your function as arguments
        :param options: options that you want available to the function
            (accessed in Javascript through the ``options`` object)
        """
        queryset = self.clone()

        code = queryset._sub_js_fields(code)

        fields = [queryset._document._translate_field_name(f) for f in fields]
        collection = queryset._document._get_collection_name()

        scope = {
            'collection': collection,
            'options': options or {},
        }

        query = queryset._query
        if queryset._where_clause:
            query['$where'] = queryset._where_clause

        scope['query'] = query
        code = Code(code, scope=scope)

        db = queryset._document._get_db()
        return db.eval(code, *fields)

    def where(self, where_clause):
        """Filter ``QuerySet`` results with a ``$where`` clause (a Javascript
        expression). Performs automatic field name substitution like
        :meth:`mongoengine.queryset.Queryset.exec_js`.

        .. note:: When using this mode of query, the database will call your
                  function, or evaluate your predicate clause, for each object
                  in the collection.

        .. versionadded:: 0.5
        """
        queryset = self.clone()
        where_clause = queryset._sub_js_fields(where_clause)
        queryset._where_clause = where_clause
        return queryset

    def sum(self, field):
        """Sum over the values of the specified field.

        :param field: the field to sum over; use dot-notation to refer to
            embedded document fields

        .. versionchanged:: 0.5 - updated to map_reduce as db.eval doesnt work
            with sharding.
        """
        map_func = """
            function() {
                var path = '{{~%(field)s}}'.split('.'),
                field = this;

                for (p in path) {
                    if (typeof field != 'undefined')
                       field = field[path[p]];
                    else
                       break;
                }

                if (field && field.constructor == Array) {
                    field.forEach(function(item) {
                        emit(1, item||0);
                    });
                } else if (typeof field != 'undefined') {
                    emit(1, field||0);
                }
            }
        """ % dict(field=field)

        reduce_func = Code("""
            function(key, values) {
                var sum = 0;
                for (var i in values) {
                    sum += values[i];
                }
                return sum;
            }
        """)

        for result in self.map_reduce(map_func, reduce_func, output='inline'):
            return result.value
        else:
            return 0

    def average(self, field):
        """Average over the values of the specified field.

        :param field: the field to average over; use dot-notation to refer to
            embedded document fields

        .. versionchanged:: 0.5 - updated to map_reduce as db.eval doesnt work
            with sharding.
        """
        map_func = """
            function() {
                var path = '{{~%(field)s}}'.split('.'),
                field = this;

                for (p in path) {
                    if (typeof field != 'undefined')
                       field = field[path[p]];
                    else
                       break;
                }

                if (field && field.constructor == Array) {
                    field.forEach(function(item) {
                        emit(1, {t: item||0, c: 1});
                    });
                } else if (typeof field != 'undefined') {
                    emit(1, {t: field||0, c: 1});
                }
            }
        """ % dict(field=field)

        reduce_func = Code("""
            function(key, values) {
                var out = {t: 0, c: 0};
                for (var i in values) {
                    var value = values[i];
                    out.t += value.t;
                    out.c += value.c;
                }
                return out;
            }
        """)

        finalize_func = Code("""
            function(key, value) {
                return value.t / value.c;
            }
        """)

        for result in self.map_reduce(map_func, reduce_func,
                                      finalize_f=finalize_func, output='inline'):
            return result.value
        else:
            return 0

    def item_frequencies(self, field, normalize=False, map_reduce=True):
        """Returns a dictionary of all items present in a field across
        the whole queried set of documents, and their corresponding frequency.
        This is useful for generating tag clouds, or searching documents.

        .. note::

            Can only do direct simple mappings and cannot map across
            :class:`~mongoengine.fields.ReferenceField` or
            :class:`~mongoengine.fields.GenericReferenceField` for more complex
            counting a manual map reduce call would is required.

        If the field is a :class:`~mongoengine.fields.ListField`, the items within
        each list will be counted individually.

        :param field: the field to use
        :param normalize: normalize the results so they add to 1.0
        :param map_reduce: Use map_reduce over exec_js

        .. versionchanged:: 0.5 defaults to map_reduce and can handle embedded
                            document lookups
        """
        if map_reduce:
            return self._item_frequencies_map_reduce(field,
                                                     normalize=normalize)
        return self._item_frequencies_exec_js(field, normalize=normalize)

    # Iterator helpers

    def next(self):
        """Wrap the result in a :class:`~mongoengine.Document` object.
        """
        if self._limit == 0 or self._none:
            raise StopIteration

        raw_doc = self._cursor.next()
        if self._as_pymongo:
            return self._get_as_pymongo(raw_doc)
        doc = self._document._from_son(raw_doc,
                                       _auto_dereference=self._auto_dereference)
        if self._scalar:
            return self._get_scalar(doc)

        return doc

    def rewind(self):
        """Rewind the cursor to its unevaluated state.

        .. versionadded:: 0.3
        """
        self._iter = False
        self._cursor.rewind()

    # Properties

    @property
    def _collection(self):
        """Property that returns the collection object. This allows us to
        perform operations only if the collection is accessed.
        """
        return self._collection_obj

    @property
    def _cursor_args(self):
        cursor_args = {
            'snapshot': self._snapshot,
            'timeout': self._timeout
        }
        if self._read_preference is not None:
            cursor_args['read_preference'] = self._read_preference
        else:
            cursor_args['slave_okay'] = self._slave_okay
        if self._loaded_fields:
            cursor_args['fields'] = self._loaded_fields.as_dict()
        return cursor_args

    @property
    def _cursor(self):
        if self._cursor_obj is None:

            self._cursor_obj = self._collection.find(self._query,
                                                     **self._cursor_args)
            # Apply where clauses to cursor
            if self._where_clause:
                where_clause = self._sub_js_fields(self._where_clause)
                self._cursor_obj.where(where_clause)

            if self._ordering:
                # Apply query ordering
                self._cursor_obj.sort(self._ordering)
            elif self._document._meta['ordering']:
                # Otherwise, apply the ordering from the document model
                order = self._get_order_by(self._document._meta['ordering'])
                self._cursor_obj.sort(order)

            if self._limit is not None:
                self._cursor_obj.limit(self._limit)

            if self._skip is not None:
                self._cursor_obj.skip(self._skip)

            if self._hint != -1:
                self._cursor_obj.hint(self._hint)

        return self._cursor_obj

    def __deepcopy__(self, memo):
        """Essential for chained queries with ReferenceFields involved"""
        return self.clone()

    @property
    def _query(self):
        if self._mongo_query is None:
            self._mongo_query = self._query_obj.to_query(self._document)
            if self._class_check:
                self._mongo_query.update(self._initial_query)
        return self._mongo_query

    @property
    def _dereference(self):
        if not self.__dereference:
            self.__dereference = _import_class('DeReference')()
        return self.__dereference

    def no_dereference(self):
        """Turn off any dereferencing for the results of this queryset.
        """
        queryset = self.clone()
        queryset._auto_dereference = False
        return queryset

    # Helper Functions

    def _item_frequencies_map_reduce(self, field, normalize=False):
        map_func = """
            function() {
                var path = '{{~%(field)s}}'.split('.');
                var field = this;

                for (p in path) {
                    if (typeof field != 'undefined')
                       field = field[path[p]];
                    else
                       break;
                }
                if (field && field.constructor == Array) {
                    field.forEach(function(item) {
                        emit(item, 1);
                    });
                } else if (typeof field != 'undefined') {
                    emit(field, 1);
                } else {
                    emit(null, 1);
                }
            }
        """ % dict(field=field)
        reduce_func = """
            function(key, values) {
                var total = 0;
                var valuesSize = values.length;
                for (var i=0; i < valuesSize; i++) {
                    total += parseInt(values[i], 10);
                }
                return total;
            }
        """
        values = self.map_reduce(map_func, reduce_func, 'inline')
        frequencies = {}
        for f in values:
            key = f.key
            if isinstance(key, float):
                if int(key) == key:
                    key = int(key)
            frequencies[key] = int(f.value)

        if normalize:
            count = sum(frequencies.values())
            frequencies = dict([(k, float(v) / count)
                                for k, v in frequencies.items()])

        return frequencies

    def _item_frequencies_exec_js(self, field, normalize=False):
        """Uses exec_js to execute"""
        freq_func = """
            function(path) {
                var path = path.split('.');

                var total = 0.0;
                db[collection].find(query).forEach(function(doc) {
                    var field = doc;
                    for (p in path) {
                        if (field)
                            field = field[path[p]];
                         else
                            break;
                    }
                    if (field && field.constructor == Array) {
                       total += field.length;
                    } else {
                       total++;
                    }
                });

                var frequencies = {};
                var types = {};
                var inc = 1.0;

                db[collection].find(query).forEach(function(doc) {
                    field = doc;
                    for (p in path) {
                        if (field)
                            field = field[path[p]];
                        else
                            break;
                    }
                    if (field && field.constructor == Array) {
                        field.forEach(function(item) {
                            frequencies[item] = inc + (isNaN(frequencies[item]) ? 0: frequencies[item]);
                        });
                    } else {
                        var item = field;
                        types[item] = item;
                        frequencies[item] = inc + (isNaN(frequencies[item]) ? 0: frequencies[item]);
                    }
                });
                return [total, frequencies, types];
            }
        """
        total, data, types = self.exec_js(freq_func, field)
        values = dict([(types.get(k), int(v)) for k, v in data.iteritems()])

        if normalize:
            values = dict([(k, float(v) / total) for k, v in values.items()])

        frequencies = {}
        for k, v in values.iteritems():
            if isinstance(k, float):
                if int(k) == k:
                    k = int(k)

            frequencies[k] = v

        return frequencies

    def _fields_to_dbfields(self, fields, subdoc=False):
        """Translate fields paths to its db equivalents"""
        ret = []
        subclasses = []
        document = self._document
        if document._meta['allow_inheritance']:
            subclasses = [get_document(x)
                          for x in document._subclasses][1:]
        for field in fields:
            try:
                field = ".".join(f.db_field for f in
                                 document._lookup_field(field.split('.')))
                ret.append(field)
            except LookUpError, err:
                found = False
                for subdoc in subclasses:
                    try:
                        subfield = ".".join(f.db_field for f in
                                        subdoc._lookup_field(field.split('.')))
                        ret.append(subfield)
                        found = True
                        break
                    except LookUpError, e:
                        pass

                if not found:
                    raise err
        return ret

    def _get_order_by(self, keys):
        """Creates a list of order by fields
        """
        key_list = []
        for key in keys:
            if not key:
                continue
            direction = pymongo.ASCENDING
            if key[0] == '-':
                direction = pymongo.DESCENDING
            if key[0] in ('-', '+'):
                key = key[1:]
            key = key.replace('__', '.')
            try:
                key = self._document._translate_field_name(key)
            except:
                pass
            key_list.append((key, direction))

        if self._cursor_obj:
            self._cursor_obj.sort(key_list)
        return key_list

    def _get_scalar(self, doc):

        def lookup(obj, name):
            chunks = name.split('__')
            for chunk in chunks:
                obj = getattr(obj, chunk)
            return obj

        data = [lookup(doc, n) for n in self._scalar]
        if len(data) == 1:
            return data[0]

        return tuple(data)

    def _get_as_pymongo(self, row):
        # Extract which fields paths we should follow if .fields(...) was
        # used. If not, handle all fields.
        if not getattr(self, '__as_pymongo_fields', None):
            self.__as_pymongo_fields = []

            for field in self._loaded_fields.fields - set(['_cls']):
                self.__as_pymongo_fields.append(field)
                while '.' in field:
                    field, _ = field.rsplit('.', 1)
                    self.__as_pymongo_fields.append(field)

        all_fields = not self.__as_pymongo_fields

        def clean(data, path=None):
            path = path or ''

            if isinstance(data, dict):
                new_data = {}
                for key, value in data.iteritems():
                    new_path = '%s.%s' % (path, key) if path else key

                    if all_fields:
                        include_field = True
                    elif self._loaded_fields.value == QueryFieldList.ONLY:
                        include_field = new_path in self.__as_pymongo_fields
                    else:
                        include_field = new_path not in self.__as_pymongo_fields

                    if include_field:
                        new_data[key] = clean(value, path=new_path)
                data = new_data
            elif isinstance(data, list):
                data = [clean(d, path=path) for d in data]
            else:
                if self._as_pymongo_coerce:
                    # If we need to coerce types, we need to determine the
                    # type of this field and use the corresponding
                    # .to_python(...)
                    from mongoengine.fields import EmbeddedDocumentField
                    obj = self._document
                    for chunk in path.split('.'):
                        obj = getattr(obj, chunk, None)
                        if obj is None:
                            break
                        elif isinstance(obj, EmbeddedDocumentField):
                            obj = obj.document_type
                    if obj and data is not None:
                        data = obj.to_python(data)
            return data
        return clean(row)

    def _sub_js_fields(self, code):
        """When fields are specified with [~fieldname] syntax, where
        *fieldname* is the Python name of a field, *fieldname* will be
        substituted for the MongoDB name of the field (specified using the
        :attr:`name` keyword argument in a field's constructor).
        """
        def field_sub(match):
            # Extract just the field name, and look up the field objects
            field_name = match.group(1).split('.')
            fields = self._document._lookup_field(field_name)
            # Substitute the correct name for the field into the javascript
            return u'["%s"]' % fields[-1].db_field

        def field_path_sub(match):
            # Extract just the field name, and look up the field objects
            field_name = match.group(1).split('.')
            fields = self._document._lookup_field(field_name)
            # Substitute the correct name for the field into the javascript
            return ".".join([f.db_field for f in fields])

        code = re.sub(u'\[\s*~([A-z_][A-z_0-9.]+?)\s*\]', field_sub, code)
        code = re.sub(u'\{\{\s*~([A-z_][A-z_0-9.]+?)\s*\}\}', field_path_sub,
                      code)
        return code

    # Deprecated
    def ensure_index(self, **kwargs):
        """Deprecated use :func:`Document.ensure_index`"""
        msg = ("Doc.objects()._ensure_index() is deprecated. "
               "Use Doc.ensure_index() instead.")
        warnings.warn(msg, DeprecationWarning)
        self._document.__class__.ensure_index(**kwargs)
        return self

    def _ensure_indexes(self):
        """Deprecated use :func:`~Document.ensure_indexes`"""
        msg = ("Doc.objects()._ensure_indexes() is deprecated. "
               "Use Doc.ensure_indexes() instead.")
        warnings.warn(msg, DeprecationWarning)
        self._document.__class__.ensure_indexes()

########NEW FILE########
__FILENAME__ = field_list

__all__ = ('QueryFieldList',)


class QueryFieldList(object):
    """Object that handles combinations of .only() and .exclude() calls"""
    ONLY = 1
    EXCLUDE = 0

    def __init__(self, fields=None, value=ONLY, always_include=None, _only_called=False):
        """The QueryFieldList builder

        :param fields: A list of fields used in `.only()` or `.exclude()`
        :param value: How to handle the fields; either `ONLY` or `EXCLUDE`
        :param always_include: Any fields to always_include eg `_cls`
        :param _only_called: Has `.only()` been called?  If so its a set of fields
           otherwise it performs a union.
        """
        self.value = value
        self.fields = set(fields or [])
        self.always_include = set(always_include or [])
        self._id = None
        self._only_called = _only_called
        self.slice = {}

    def __add__(self, f):
        if isinstance(f.value, dict):
            for field in f.fields:
                self.slice[field] = f.value
            if not self.fields:
                self.fields = f.fields
        elif not self.fields:
            self.fields = f.fields
            self.value = f.value
            self.slice = {}
        elif self.value is self.ONLY and f.value is self.ONLY:
            self._clean_slice()
            if self._only_called:
                self.fields = self.fields.union(f.fields)
            else:
                self.fields = f.fields
        elif self.value is self.EXCLUDE and f.value is self.EXCLUDE:
            self.fields = self.fields.union(f.fields)
            self._clean_slice()
        elif self.value is self.ONLY and f.value is self.EXCLUDE:
            self.fields -= f.fields
            self._clean_slice()
        elif self.value is self.EXCLUDE and f.value is self.ONLY:
            self.value = self.ONLY
            self.fields = f.fields - self.fields
            self._clean_slice()

        if '_id' in f.fields:
            self._id = f.value

        if self.always_include:
            if self.value is self.ONLY and self.fields:
                if sorted(self.slice.keys()) != sorted(self.fields):
                    self.fields = self.fields.union(self.always_include)
            else:
                self.fields -= self.always_include

        if getattr(f, '_only_called', False):
            self._only_called = True
        return self

    def __nonzero__(self):
        return bool(self.fields)

    def as_dict(self):
        field_list = dict((field, self.value) for field in self.fields)
        if self.slice:
            field_list.update(self.slice)
        if self._id is not None:
            field_list['_id'] = self._id
        return field_list

    def reset(self):
        self.fields = set([])
        self.slice = {}
        self.value = self.ONLY

    def _clean_slice(self):
        if self.slice:
            for field in set(self.slice.keys()) - self.fields:
                del self.slice[field]

########NEW FILE########
__FILENAME__ = manager
from functools import partial
from mongoengine.queryset.queryset import QuerySet

__all__ = ('queryset_manager', 'QuerySetManager')


class QuerySetManager(object):
    """
    The default QuerySet Manager.

    Custom QuerySet Manager functions can extend this class and users can
    add extra queryset functionality.  Any custom manager methods must accept a
    :class:`~mongoengine.Document` class as its first argument, and a
    :class:`~mongoengine.queryset.QuerySet` as its second argument.

    The method function should return a :class:`~mongoengine.queryset.QuerySet`
    , probably the same one that was passed in, but modified in some way.
    """

    get_queryset = None
    default = QuerySet

    def __init__(self, queryset_func=None):
        if queryset_func:
            self.get_queryset = queryset_func

    def __get__(self, instance, owner):
        """Descriptor for instantiating a new QuerySet object when
        Document.objects is accessed.
        """
        if instance is not None:
            # Document class being used rather than a document object
            return self

        # owner is the document that contains the QuerySetManager
        queryset_class = owner._meta.get('queryset_class', self.default)
        queryset = queryset_class(owner, owner._get_collection())
        if self.get_queryset:
            arg_count = self.get_queryset.func_code.co_argcount
            if arg_count == 1:
                queryset = self.get_queryset(queryset)
            elif arg_count == 2:
                queryset = self.get_queryset(owner, queryset)
            else:
                queryset = partial(self.get_queryset, owner, queryset)
        return queryset


def queryset_manager(func):
    """Decorator that allows you to define custom QuerySet managers on
    :class:`~mongoengine.Document` classes. The manager must be a function that
    accepts a :class:`~mongoengine.Document` class as its first argument, and a
    :class:`~mongoengine.queryset.QuerySet` as its second argument. The method
    function should return a :class:`~mongoengine.queryset.QuerySet`, probably
    the same one that was passed in, but modified in some way.
    """
    return QuerySetManager(func)

########NEW FILE########
__FILENAME__ = queryset
from mongoengine.errors import OperationError
from mongoengine.queryset.base import (BaseQuerySet, DO_NOTHING, NULLIFY,
                                       CASCADE, DENY, PULL)

__all__ = ('QuerySet', 'QuerySetNoCache', 'DO_NOTHING', 'NULLIFY', 'CASCADE',
           'DENY', 'PULL')

# The maximum number of items to display in a QuerySet.__repr__
REPR_OUTPUT_SIZE = 20
ITER_CHUNK_SIZE = 100


class QuerySet(BaseQuerySet):
    """The default queryset, that builds queries and handles a set of results
    returned from a query.

    Wraps a MongoDB cursor, providing :class:`~mongoengine.Document` objects as
    the results.
    """

    _has_more = True
    _len = None
    _result_cache = None

    def __iter__(self):
        """Iteration utilises a results cache which iterates the cursor
        in batches of ``ITER_CHUNK_SIZE``.

        If ``self._has_more`` the cursor hasn't been exhausted so cache then
        batch.  Otherwise iterate the result_cache.
        """
        self._iter = True
        if self._has_more:
            return self._iter_results()

        # iterating over the cache.
        return iter(self._result_cache)

    def __len__(self):
        """Since __len__ is called quite frequently (for example, as part of
        list(qs) we populate the result cache and cache the length.
        """
        if self._len is not None:
            return self._len
        if self._has_more:
            # populate the cache
            list(self._iter_results())

        self._len = len(self._result_cache)
        return self._len

    def __repr__(self):
        """Provides the string representation of the QuerySet
        """
        if self._iter:
            return '.. queryset mid-iteration ..'

        self._populate_cache()
        data = self._result_cache[:REPR_OUTPUT_SIZE + 1]
        if len(data) > REPR_OUTPUT_SIZE:
            data[-1] = "...(remaining elements truncated)..."
        return repr(data)


    def _iter_results(self):
        """A generator for iterating over the result cache.

        Also populates the cache if there are more possible results to yield.
        Raises StopIteration when there are no more results"""
        if self._result_cache is None:
            self._result_cache = []
        pos = 0
        while True:
            upper = len(self._result_cache)
            while pos < upper:
                yield self._result_cache[pos]
                pos = pos + 1
            if not self._has_more:
                raise StopIteration
            if len(self._result_cache) <= pos:
                self._populate_cache()

    def _populate_cache(self):
        """
        Populates the result cache with ``ITER_CHUNK_SIZE`` more entries
        (until the cursor is exhausted).
        """
        if self._result_cache is None:
            self._result_cache = []
        if self._has_more:
            try:
                for i in xrange(ITER_CHUNK_SIZE):
                    self._result_cache.append(self.next())
            except StopIteration:
                self._has_more = False

    def count(self, with_limit_and_skip=True):
        """Count the selected elements in the query.

        :param with_limit_and_skip (optional): take any :meth:`limit` or
            :meth:`skip` that has been applied to this cursor into account when
            getting the count
        """
        if with_limit_and_skip is False:
            return super(QuerySet, self).count(with_limit_and_skip)

        if self._len is None:
            self._len = super(QuerySet, self).count(with_limit_and_skip)

        return self._len

    def no_cache(self):
        """Convert to a non_caching queryset

        .. versionadded:: 0.8.3 Convert to non caching queryset
        """
        if self._result_cache is not None:
            raise OperationError("QuerySet already cached")
        return self.clone_into(QuerySetNoCache(self._document, self._collection))


class QuerySetNoCache(BaseQuerySet):
    """A non caching QuerySet"""

    def cache(self):
        """Convert to a caching queryset

        .. versionadded:: 0.8.3 Convert to caching queryset
        """
        return self.clone_into(QuerySet(self._document, self._collection))

    def __repr__(self):
        """Provides the string representation of the QuerySet

        .. versionchanged:: 0.6.13 Now doesnt modify the cursor
        """
        if self._iter:
            return '.. queryset mid-iteration ..'

        data = []
        for i in xrange(REPR_OUTPUT_SIZE + 1):
            try:
                data.append(self.next())
            except StopIteration:
                break
        if len(data) > REPR_OUTPUT_SIZE:
            data[-1] = "...(remaining elements truncated)..."

        self.rewind()
        return repr(data)

    def __iter__(self):
        queryset = self
        if queryset._iter:
            queryset = self.clone()
        queryset.rewind()
        return queryset

########NEW FILE########
__FILENAME__ = transform
from collections import defaultdict

import pymongo
from bson import SON

from mongoengine.common import _import_class
from mongoengine.errors import InvalidQueryError, LookUpError

__all__ = ('query', 'update')


COMPARISON_OPERATORS = ('ne', 'gt', 'gte', 'lt', 'lte', 'in', 'nin', 'mod',
                        'all', 'size', 'exists', 'not')
GEO_OPERATORS        = ('within_distance', 'within_spherical_distance',
                        'within_box', 'within_polygon', 'near', 'near_sphere',
                        'max_distance', 'geo_within', 'geo_within_box',
                        'geo_within_polygon', 'geo_within_center',
                        'geo_within_sphere', 'geo_intersects')
STRING_OPERATORS     = ('contains', 'icontains', 'startswith',
                        'istartswith', 'endswith', 'iendswith',
                        'exact', 'iexact')
CUSTOM_OPERATORS     = ('match',)
MATCH_OPERATORS      = (COMPARISON_OPERATORS + GEO_OPERATORS +
                        STRING_OPERATORS + CUSTOM_OPERATORS)

UPDATE_OPERATORS     = ('set', 'unset', 'inc', 'dec', 'pop', 'push',
                        'push_all', 'pull', 'pull_all', 'add_to_set',
                        'set_on_insert')


def query(_doc_cls=None, _field_operation=False, **query):
    """Transform a query from Django-style format to Mongo format.
    """
    mongo_query = {}
    merge_query = defaultdict(list)
    for key, value in sorted(query.items()):
        if key == "__raw__":
            mongo_query.update(value)
            continue

        parts = key.split('__')
        indices = [(i, p) for i, p in enumerate(parts) if p.isdigit()]
        parts = [part for part in parts if not part.isdigit()]
        # Check for an operator and transform to mongo-style if there is
        op = None
        if len(parts) > 1 and parts[-1] in MATCH_OPERATORS:
            op = parts.pop()

        negate = False
        if len(parts) > 1 and parts[-1] == 'not':
            parts.pop()
            negate = True

        if _doc_cls:
            # Switch field names to proper names [set in Field(name='foo')]
            try:
                fields = _doc_cls._lookup_field(parts)
            except Exception, e:
                raise InvalidQueryError(e)
            parts = []

            cleaned_fields = []
            for field in fields:
                append_field = True
                if isinstance(field, basestring):
                    parts.append(field)
                    append_field = False
                else:
                    parts.append(field.db_field)
                if append_field:
                    cleaned_fields.append(field)

            # Convert value to proper value
            field = cleaned_fields[-1]

            singular_ops = [None, 'ne', 'gt', 'gte', 'lt', 'lte', 'not']
            singular_ops += STRING_OPERATORS
            if op in singular_ops:
                if isinstance(field, basestring):
                    if (op in STRING_OPERATORS and
                       isinstance(value, basestring)):
                        StringField = _import_class('StringField')
                        value = StringField.prepare_query_value(op, value)
                    else:
                        value = field
                else:
                    value = field.prepare_query_value(op, value)
            elif op in ('in', 'nin', 'all', 'near') and not isinstance(value, dict):
                # 'in', 'nin' and 'all' require a list of values
                value = [field.prepare_query_value(op, v) for v in value]

        # if op and op not in COMPARISON_OPERATORS:
        if op:
            if op in GEO_OPERATORS:
                value = _geo_operator(field, op, value)
            elif op in CUSTOM_OPERATORS:
                if op == 'match':
                    value = field.prepare_query_value(op, value)
                    value = {"$elemMatch": value}
                else:
                    NotImplementedError("Custom method '%s' has not "
                                        "been implemented" % op)
            elif op not in STRING_OPERATORS:
                value = {'$' + op: value}

        if negate:
            value = {'$not': value}

        for i, part in indices:
            parts.insert(i, part)
        key = '.'.join(parts)
        if op is None or key not in mongo_query:
            mongo_query[key] = value
        elif key in mongo_query:
            if key in mongo_query and isinstance(mongo_query[key], dict):
                mongo_query[key].update(value)
                # $maxDistance needs to come last - convert to SON
                if '$maxDistance' in mongo_query[key]:
                    value_dict = mongo_query[key]
                    value_son = SON()
                    for k, v in value_dict.iteritems():
                        if k == '$maxDistance':
                            continue
                        value_son[k] = v
                    value_son['$maxDistance'] = value_dict['$maxDistance']
                    mongo_query[key] = value_son
            else:
                # Store for manually merging later
                merge_query[key].append(value)

    # The queryset has been filter in such a way we must manually merge
    for k, v in merge_query.items():
        merge_query[k].append(mongo_query[k])
        del mongo_query[k]
        if isinstance(v, list):
            value = [{k: val} for val in v]
            if '$and' in mongo_query.keys():
                mongo_query['$and'].append(value)
            else:
                mongo_query['$and'] = value

    return mongo_query


def update(_doc_cls=None, **update):
    """Transform an update spec from Django-style format to Mongo format.
    """
    mongo_update = {}
    for key, value in update.items():
        if key == "__raw__":
            mongo_update.update(value)
            continue
        parts = key.split('__')
        # Check for an operator and transform to mongo-style if there is
        op = None
        if parts[0] in UPDATE_OPERATORS:
            op = parts.pop(0)
            # Convert Pythonic names to Mongo equivalents
            if op in ('push_all', 'pull_all'):
                op = op.replace('_all', 'All')
            elif op == 'dec':
                # Support decrement by flipping a positive value's sign
                # and using 'inc'
                op = 'inc'
                if value > 0:
                    value = -value
            elif op == 'add_to_set':
                op = 'addToSet'
            elif op == 'set_on_insert':
                op = "setOnInsert"

        match = None
        if parts[-1] in COMPARISON_OPERATORS:
            match = parts.pop()

        if _doc_cls:
            # Switch field names to proper names [set in Field(name='foo')]
            try:
                fields = _doc_cls._lookup_field(parts)
            except Exception, e:
                raise InvalidQueryError(e)
            parts = []

            cleaned_fields = []
            appended_sub_field = False
            for field in fields:
                append_field = True
                if isinstance(field, basestring):
                    # Convert the S operator to $
                    if field == 'S':
                        field = '$'
                    parts.append(field)
                    append_field = False
                else:
                    parts.append(field.db_field)
                if append_field:
                    appended_sub_field = False
                    cleaned_fields.append(field)
                    if hasattr(field, 'field'):
                        cleaned_fields.append(field.field)
                        appended_sub_field = True

            # Convert value to proper value
            if appended_sub_field:
                field = cleaned_fields[-2]
            else:
                field = cleaned_fields[-1]

            GeoJsonBaseField = _import_class("GeoJsonBaseField")
            if isinstance(field, GeoJsonBaseField):
                value = field.to_mongo(value)

            if op in (None, 'set', 'push', 'pull'):
                if field.required or value is not None:
                    value = field.prepare_query_value(op, value)
            elif op in ('pushAll', 'pullAll'):
                value = [field.prepare_query_value(op, v) for v in value]
            elif op in ('addToSet', 'setOnInsert'):
                if isinstance(value, (list, tuple, set)):
                    value = [field.prepare_query_value(op, v) for v in value]
                elif field.required or value is not None:
                    value = field.prepare_query_value(op, value)
            elif op == "unset":
                value = 1

        if match:
            match = '$' + match
            value = {match: value}

        key = '.'.join(parts)

        if not op:
            raise InvalidQueryError("Updates must supply an operation "
                                    "eg: set__FIELD=value")

        if 'pull' in op and '.' in key:
            # Dot operators don't work on pull operations
            # unless they point to a list field
            # Otherwise it uses nested dict syntax
            if op == 'pullAll':
                raise InvalidQueryError("pullAll operations only support "
                                        "a single field depth")

            # Look for the last list field and use dot notation until there
            field_classes = [c.__class__ for c in cleaned_fields]
            field_classes.reverse()
            ListField = _import_class('ListField')
            if ListField in field_classes:
                # Join all fields via dot notation to the last ListField
                # Then process as normal
                last_listField = len(cleaned_fields) - field_classes.index(ListField)
                key = ".".join(parts[:last_listField])
                parts = parts[last_listField:]
                parts.insert(0, key)

            parts.reverse()
            for key in parts:
                value = {key: value}
        elif op == 'addToSet' and isinstance(value, list):
            value = {key: {"$each": value}}
        else:
            value = {key: value}
        key = '$' + op

        if key not in mongo_update:
            mongo_update[key] = value
        elif key in mongo_update and isinstance(mongo_update[key], dict):
            mongo_update[key].update(value)

    return mongo_update


def _geo_operator(field, op, value):
    """Helper to return the query for a given geo query"""
    if field._geo_index == pymongo.GEO2D:
        if op == "within_distance":
            value = {'$within': {'$center': value}}
        elif op == "within_spherical_distance":
            value = {'$within': {'$centerSphere': value}}
        elif op == "within_polygon":
            value = {'$within': {'$polygon': value}}
        elif op == "near":
            value = {'$near': value}
        elif op == "near_sphere":
            value = {'$nearSphere': value}
        elif op == 'within_box':
            value = {'$within': {'$box': value}}
        elif op == "max_distance":
            value = {'$maxDistance': value}
        else:
            raise NotImplementedError("Geo method '%s' has not "
                                      "been implemented for a GeoPointField" % op)
    else:
        if op == "geo_within":
            value = {"$geoWithin": _infer_geometry(value)}
        elif op == "geo_within_box":
            value = {"$geoWithin": {"$box": value}}
        elif op == "geo_within_polygon":
            value = {"$geoWithin": {"$polygon": value}}
        elif op == "geo_within_center":
            value = {"$geoWithin": {"$center": value}}
        elif op == "geo_within_sphere":
            value = {"$geoWithin": {"$centerSphere": value}}
        elif op == "geo_intersects":
            value = {"$geoIntersects": _infer_geometry(value)}
        elif op == "near":
            value = {'$near': _infer_geometry(value)}
        elif op == "max_distance":
            value = {'$maxDistance': value}
        else:
            raise NotImplementedError("Geo method '%s' has not "
                                      "been implemented for a %s " % (op, field._name))
    return value


def _infer_geometry(value):
    """Helper method that tries to infer the $geometry shape for a given value"""
    if isinstance(value, dict):
        if "$geometry" in value:
            return value
        elif 'coordinates' in value and 'type' in value:
            return {"$geometry": value}
        raise InvalidQueryError("Invalid $geometry dictionary should have "
                                "type and coordinates keys")
    elif isinstance(value, (list, set)):
        try:
            value[0][0][0]
            return {"$geometry": {"type": "Polygon", "coordinates": value}}
        except:
            pass
        try:
            value[0][0]
            return {"$geometry": {"type": "LineString", "coordinates": value}}
        except:
            pass
        try:
            value[0]
            return {"$geometry": {"type": "Point", "coordinates": value}}
        except:
            pass

    raise InvalidQueryError("Invalid $geometry data. Can be either a dictionary "
                            "or (nested) lists of coordinate(s)")

########NEW FILE########
__FILENAME__ = visitor
import copy

from mongoengine.errors import InvalidQueryError
from mongoengine.python_support import product, reduce

from mongoengine.queryset import transform

__all__ = ('Q',)


class QNodeVisitor(object):
    """Base visitor class for visiting Q-object nodes in a query tree.
    """

    def visit_combination(self, combination):
        """Called by QCombination objects.
        """
        return combination

    def visit_query(self, query):
        """Called by (New)Q objects.
        """
        return query


class DuplicateQueryConditionsError(InvalidQueryError):
    pass


class SimplificationVisitor(QNodeVisitor):
    """Simplifies query trees by combinging unnecessary 'and' connection nodes
    into a single Q-object.
    """

    def visit_combination(self, combination):
        if combination.operation == combination.AND:
            # The simplification only applies to 'simple' queries
            if all(isinstance(node, Q) for node in combination.children):
                queries = [n.query for n in combination.children]
                try:
                    return Q(**self._query_conjunction(queries))
                except DuplicateQueryConditionsError:
                    # Cannot be simplified
                    pass
        return combination

    def _query_conjunction(self, queries):
        """Merges query dicts - effectively &ing them together.
        """
        query_ops = set()
        combined_query = {}
        for query in queries:
            ops = set(query.keys())
            # Make sure that the same operation isn't applied more than once
            # to a single field
            intersection = ops.intersection(query_ops)
            if intersection:
                raise DuplicateQueryConditionsError()

            query_ops.update(ops)
            combined_query.update(copy.deepcopy(query))
        return combined_query


class QueryCompilerVisitor(QNodeVisitor):
    """Compiles the nodes in a query tree to a PyMongo-compatible query
    dictionary.
    """

    def __init__(self, document):
        self.document = document

    def visit_combination(self, combination):
        operator = "$and"
        if combination.operation == combination.OR:
            operator = "$or"
        return {operator: combination.children}

    def visit_query(self, query):
        return transform.query(self.document, **query.query)


class QNode(object):
    """Base class for nodes in query trees.
    """

    AND = 0
    OR = 1

    def to_query(self, document):
        query = self.accept(SimplificationVisitor())
        query = query.accept(QueryCompilerVisitor(document))
        return query

    def accept(self, visitor):
        raise NotImplementedError

    def _combine(self, other, operation):
        """Combine this node with another node into a QCombination object.
        """
        if getattr(other, 'empty', True):
            return self

        if self.empty:
            return other

        return QCombination(operation, [self, other])

    @property
    def empty(self):
        return False

    def __or__(self, other):
        return self._combine(other, self.OR)

    def __and__(self, other):
        return self._combine(other, self.AND)


class QCombination(QNode):
    """Represents the combination of several conditions by a given logical
    operator.
    """

    def __init__(self, operation, children):
        self.operation = operation
        self.children = []
        for node in children:
            # If the child is a combination of the same type, we can merge its
            # children directly into this combinations children
            if isinstance(node, QCombination) and node.operation == operation:
                self.children += node.children
            else:
                self.children.append(node)

    def accept(self, visitor):
        for i in range(len(self.children)):
            if isinstance(self.children[i], QNode):
                self.children[i] = self.children[i].accept(visitor)

        return visitor.visit_combination(self)

    @property
    def empty(self):
        return not bool(self.children)


class Q(QNode):
    """A simple query object, used in a query tree to build up more complex
    query structures.
    """

    def __init__(self, **query):
        self.query = query

    def accept(self, visitor):
        return visitor.visit_query(self)

    @property
    def empty(self):
        return not bool(self.query)

########NEW FILE########
__FILENAME__ = signals
# -*- coding: utf-8 -*-

__all__ = ['pre_init', 'post_init', 'pre_save', 'pre_save_post_validation',
           'post_save', 'pre_delete', 'post_delete']

signals_available = False
try:
    from blinker import Namespace
    signals_available = True
except ImportError:
    class Namespace(object):
        def signal(self, name, doc=None):
            return _FakeSignal(name, doc)

    class _FakeSignal(object):
        """If blinker is unavailable, create a fake class with the same
        interface that allows sending of signals but will fail with an
        error on anything else.  Instead of doing anything on send, it
        will just ignore the arguments and do nothing instead.
        """

        def __init__(self, name, doc=None):
            self.name = name
            self.__doc__ = doc

        def _fail(self, *args, **kwargs):
            raise RuntimeError('signalling support is unavailable '
                               'because the blinker library is '
                               'not installed.')
        send = lambda *a, **kw: None
        connect = disconnect = has_receivers_for = receivers_for = \
            temporarily_connected_to = _fail
        del _fail

# the namespace for code signals.  If you are not mongoengine code, do
# not put signals in here.  Create your own namespace instead.
_signals = Namespace()

pre_init = _signals.signal('pre_init')
post_init = _signals.signal('post_init')
pre_save = _signals.signal('pre_save')
pre_save_post_validation = _signals.signal('pre_save_post_validation')
post_save = _signals.signal('post_save')
pre_delete = _signals.signal('pre_delete')
post_delete = _signals.signal('post_delete')
pre_bulk_insert = _signals.signal('pre_bulk_insert')
post_bulk_insert = _signals.signal('post_bulk_insert')

########NEW FILE########
__FILENAME__ = class_methods
# -*- coding: utf-8 -*-
import sys
sys.path[0:0] = [""]
import unittest

from mongoengine import *

from mongoengine.queryset import NULLIFY, PULL
from mongoengine.connection import get_db

__all__ = ("ClassMethodsTest", )


class ClassMethodsTest(unittest.TestCase):

    def setUp(self):
        connect(db='mongoenginetest')
        self.db = get_db()

        class Person(Document):
            name = StringField()
            age = IntField()

            non_field = True

            meta = {"allow_inheritance": True}

        self.Person = Person

    def tearDown(self):
        for collection in self.db.collection_names():
            if 'system.' in collection:
                continue
            self.db.drop_collection(collection)

    def test_definition(self):
        """Ensure that document may be defined using fields.
        """
        self.assertEqual(['age', 'id', 'name'],
                         sorted(self.Person._fields.keys()))
        self.assertEqual(["IntField", "ObjectIdField", "StringField"],
                        sorted([x.__class__.__name__ for x in
                                self.Person._fields.values()]))

    def test_get_db(self):
        """Ensure that get_db returns the expected db.
        """
        db = self.Person._get_db()
        self.assertEqual(self.db, db)

    def test_get_collection_name(self):
        """Ensure that get_collection_name returns the expected collection
        name.
        """
        collection_name = 'person'
        self.assertEqual(collection_name, self.Person._get_collection_name())

    def test_get_collection(self):
        """Ensure that get_collection returns the expected collection.
        """
        collection_name = 'person'
        collection = self.Person._get_collection()
        self.assertEqual(self.db[collection_name], collection)

    def test_drop_collection(self):
        """Ensure that the collection may be dropped from the database.
        """
        collection_name = 'person'
        self.Person(name='Test').save()
        self.assertTrue(collection_name in self.db.collection_names())

        self.Person.drop_collection()
        self.assertFalse(collection_name in self.db.collection_names())

    def test_register_delete_rule(self):
        """Ensure that register delete rule adds a delete rule to the document
        meta.
        """
        class Job(Document):
            employee = ReferenceField(self.Person)

        self.assertEqual(self.Person._meta.get('delete_rules'), None)

        self.Person.register_delete_rule(Job, 'employee', NULLIFY)
        self.assertEqual(self.Person._meta['delete_rules'],
                         {(Job, 'employee'): NULLIFY})

    def test_compare_indexes(self):
        """ Ensure that the indexes are properly created and that
        compare_indexes identifies the missing/extra indexes
        """

        class BlogPost(Document):
            author = StringField()
            title = StringField()
            description = StringField()
            tags = StringField()

            meta = {
                'indexes': [('author', 'title')]
            }

        BlogPost.drop_collection()

        BlogPost.ensure_indexes()
        self.assertEqual(BlogPost.compare_indexes(), { 'missing': [], 'extra': [] })

        BlogPost.ensure_index(['author', 'description'])
        self.assertEqual(BlogPost.compare_indexes(), { 'missing': [], 'extra': [[('author', 1), ('description', 1)]] })

        BlogPost._get_collection().drop_index('author_1_description_1')
        self.assertEqual(BlogPost.compare_indexes(), { 'missing': [], 'extra': [] })

        BlogPost._get_collection().drop_index('author_1_title_1')
        self.assertEqual(BlogPost.compare_indexes(), { 'missing': [[('author', 1), ('title', 1)]], 'extra': [] })

    def test_compare_indexes_inheritance(self):
        """ Ensure that the indexes are properly created and that
        compare_indexes identifies the missing/extra indexes for subclassed
        documents (_cls included)
        """

        class BlogPost(Document):
            author = StringField()
            title = StringField()
            description = StringField()

            meta = {
                'allow_inheritance': True
            }

        class BlogPostWithTags(BlogPost):
            tags = StringField()
            tag_list = ListField(StringField())

            meta = {
                'indexes': [('author', 'tags')]
            }

        BlogPost.drop_collection()

        BlogPost.ensure_indexes()
        BlogPostWithTags.ensure_indexes()
        self.assertEqual(BlogPost.compare_indexes(), { 'missing': [], 'extra': [] })

        BlogPostWithTags.ensure_index(['author', 'tag_list'])
        self.assertEqual(BlogPost.compare_indexes(), { 'missing': [], 'extra': [[('_cls', 1), ('author', 1), ('tag_list', 1)]] })

        BlogPostWithTags._get_collection().drop_index('_cls_1_author_1_tag_list_1')
        self.assertEqual(BlogPost.compare_indexes(), { 'missing': [], 'extra': [] })

        BlogPostWithTags._get_collection().drop_index('_cls_1_author_1_tags_1')
        self.assertEqual(BlogPost.compare_indexes(), { 'missing': [[('_cls', 1), ('author', 1), ('tags', 1)]], 'extra': [] })

    def test_compare_indexes_multiple_subclasses(self):
        """ Ensure that compare_indexes behaves correctly if called from a
        class, which base class has multiple subclasses
        """

        class BlogPost(Document):
            author = StringField()
            title = StringField()
            description = StringField()

            meta = {
                'allow_inheritance': True
            }

        class BlogPostWithTags(BlogPost):
            tags = StringField()
            tag_list = ListField(StringField())

            meta = {
                'indexes': [('author', 'tags')]
            }

        class BlogPostWithCustomField(BlogPost):
            custom = DictField()

            meta = {
                'indexes': [('author', 'custom')]
            }

        BlogPost.ensure_indexes()
        BlogPostWithTags.ensure_indexes()
        BlogPostWithCustomField.ensure_indexes()

        self.assertEqual(BlogPost.compare_indexes(), { 'missing': [], 'extra': [] })
        self.assertEqual(BlogPostWithTags.compare_indexes(), { 'missing': [], 'extra': [] })
        self.assertEqual(BlogPostWithCustomField.compare_indexes(), { 'missing': [], 'extra': [] })

    def test_list_indexes_inheritance(self):
        """ ensure that all of the indexes are listed regardless of the super-
        or sub-class that we call it from
        """

        class BlogPost(Document):
            author = StringField()
            title = StringField()
            description = StringField()

            meta = {
                'allow_inheritance': True
            }

        class BlogPostWithTags(BlogPost):
            tags = StringField()

            meta = {
                'indexes': [('author', 'tags')]
            }

        class BlogPostWithTagsAndExtraText(BlogPostWithTags):
            extra_text = StringField()

            meta = {
                'indexes': [('author', 'tags', 'extra_text')]
            }

        BlogPost.drop_collection()

        BlogPost.ensure_indexes()
        BlogPostWithTags.ensure_indexes()
        BlogPostWithTagsAndExtraText.ensure_indexes()

        self.assertEqual(BlogPost.list_indexes(),
                         BlogPostWithTags.list_indexes())
        self.assertEqual(BlogPost.list_indexes(),
                         BlogPostWithTagsAndExtraText.list_indexes())
        self.assertEqual(BlogPost.list_indexes(),
                         [[('_cls', 1), ('author', 1), ('tags', 1)],
                         [('_cls', 1), ('author', 1), ('tags', 1), ('extra_text', 1)],
                         [(u'_id', 1)], [('_cls', 1)]])

    def test_register_delete_rule_inherited(self):

        class Vaccine(Document):
            name = StringField(required=True)

            meta = {"indexes": ["name"]}

        class Animal(Document):
            family = StringField(required=True)
            vaccine_made = ListField(ReferenceField("Vaccine", reverse_delete_rule=PULL))

            meta = {"allow_inheritance": True, "indexes": ["family"]}

        class Cat(Animal):
            name = StringField(required=True)

        self.assertEqual(Vaccine._meta['delete_rules'][(Animal, 'vaccine_made')], PULL)
        self.assertEqual(Vaccine._meta['delete_rules'][(Cat, 'vaccine_made')], PULL)

    def test_collection_naming(self):
        """Ensure that a collection with a specified name may be used.
        """

        class DefaultNamingTest(Document):
            pass
        self.assertEqual('default_naming_test',
                         DefaultNamingTest._get_collection_name())

        class CustomNamingTest(Document):
            meta = {'collection': 'pimp_my_collection'}

        self.assertEqual('pimp_my_collection',
                         CustomNamingTest._get_collection_name())

        class DynamicNamingTest(Document):
            meta = {'collection': lambda c: "DYNAMO"}
        self.assertEqual('DYNAMO', DynamicNamingTest._get_collection_name())

        # Use Abstract class to handle backwards compatibility
        class BaseDocument(Document):
            meta = {
                'abstract': True,
                'collection': lambda c: c.__name__.lower()
            }

        class OldNamingConvention(BaseDocument):
            pass
        self.assertEqual('oldnamingconvention',
                         OldNamingConvention._get_collection_name())

        class InheritedAbstractNamingTest(BaseDocument):
            meta = {'collection': 'wibble'}
        self.assertEqual('wibble',
                         InheritedAbstractNamingTest._get_collection_name())

        # Mixin tests
        class BaseMixin(object):
            meta = {
                'collection': lambda c: c.__name__.lower()
            }

        class OldMixinNamingConvention(Document, BaseMixin):
            pass
        self.assertEqual('oldmixinnamingconvention',
                          OldMixinNamingConvention._get_collection_name())

        class BaseMixin(object):
            meta = {
                'collection': lambda c: c.__name__.lower()
            }

        class BaseDocument(Document, BaseMixin):
            meta = {'allow_inheritance': True}

        class MyDocument(BaseDocument):
            pass

        self.assertEqual('basedocument', MyDocument._get_collection_name())

    def test_custom_collection_name_operations(self):
        """Ensure that a collection with a specified name is used as expected.
        """
        collection_name = 'personCollTest'

        class Person(Document):
            name = StringField()
            meta = {'collection': collection_name}

        Person(name="Test User").save()
        self.assertTrue(collection_name in self.db.collection_names())

        user_obj = self.db[collection_name].find_one()
        self.assertEqual(user_obj['name'], "Test User")

        user_obj = Person.objects[0]
        self.assertEqual(user_obj.name, "Test User")

        Person.drop_collection()
        self.assertFalse(collection_name in self.db.collection_names())

    def test_collection_name_and_primary(self):
        """Ensure that a collection with a specified name may be used.
        """

        class Person(Document):
            name = StringField(primary_key=True)
            meta = {'collection': 'app'}

        Person(name="Test User").save()

        user_obj = Person.objects.first()
        self.assertEqual(user_obj.name, "Test User")

        Person.drop_collection()


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = delta
# -*- coding: utf-8 -*-
import sys
sys.path[0:0] = [""]
import unittest

from bson import SON
from mongoengine import *
from mongoengine.connection import get_db

__all__ = ("DeltaTest",)


class DeltaTest(unittest.TestCase):

    def setUp(self):
        connect(db='mongoenginetest')
        self.db = get_db()

        class Person(Document):
            name = StringField()
            age = IntField()

            non_field = True

            meta = {"allow_inheritance": True}

        self.Person = Person

    def tearDown(self):
        for collection in self.db.collection_names():
            if 'system.' in collection:
                continue
            self.db.drop_collection(collection)

    def test_delta(self):
        self.delta(Document)
        self.delta(DynamicDocument)

    def delta(self, DocClass):

        class Doc(DocClass):
            string_field = StringField()
            int_field = IntField()
            dict_field = DictField()
            list_field = ListField()

        Doc.drop_collection()
        doc = Doc()
        doc.save()

        doc = Doc.objects.first()
        self.assertEqual(doc._get_changed_fields(), [])
        self.assertEqual(doc._delta(), ({}, {}))

        doc.string_field = 'hello'
        self.assertEqual(doc._get_changed_fields(), ['string_field'])
        self.assertEqual(doc._delta(), ({'string_field': 'hello'}, {}))

        doc._changed_fields = []
        doc.int_field = 1
        self.assertEqual(doc._get_changed_fields(), ['int_field'])
        self.assertEqual(doc._delta(), ({'int_field': 1}, {}))

        doc._changed_fields = []
        dict_value = {'hello': 'world', 'ping': 'pong'}
        doc.dict_field = dict_value
        self.assertEqual(doc._get_changed_fields(), ['dict_field'])
        self.assertEqual(doc._delta(), ({'dict_field': dict_value}, {}))

        doc._changed_fields = []
        list_value = ['1', 2, {'hello': 'world'}]
        doc.list_field = list_value
        self.assertEqual(doc._get_changed_fields(), ['list_field'])
        self.assertEqual(doc._delta(), ({'list_field': list_value}, {}))

        # Test unsetting
        doc._changed_fields = []
        doc.dict_field = {}
        self.assertEqual(doc._get_changed_fields(), ['dict_field'])
        self.assertEqual(doc._delta(), ({}, {'dict_field': 1}))

        doc._changed_fields = []
        doc.list_field = []
        self.assertEqual(doc._get_changed_fields(), ['list_field'])
        self.assertEqual(doc._delta(), ({}, {'list_field': 1}))

    def test_delta_recursive(self):
        self.delta_recursive(Document, EmbeddedDocument)
        self.delta_recursive(DynamicDocument, EmbeddedDocument)
        self.delta_recursive(Document, DynamicEmbeddedDocument)
        self.delta_recursive(DynamicDocument, DynamicEmbeddedDocument)

    def delta_recursive(self, DocClass, EmbeddedClass):

        class Embedded(EmbeddedClass):
            string_field = StringField()
            int_field = IntField()
            dict_field = DictField()
            list_field = ListField()

        class Doc(DocClass):
            string_field = StringField()
            int_field = IntField()
            dict_field = DictField()
            list_field = ListField()
            embedded_field = EmbeddedDocumentField(Embedded)

        Doc.drop_collection()
        doc = Doc()
        doc.save()

        doc = Doc.objects.first()
        self.assertEqual(doc._get_changed_fields(), [])
        self.assertEqual(doc._delta(), ({}, {}))

        embedded_1 = Embedded()
        embedded_1.string_field = 'hello'
        embedded_1.int_field = 1
        embedded_1.dict_field = {'hello': 'world'}
        embedded_1.list_field = ['1', 2, {'hello': 'world'}]
        doc.embedded_field = embedded_1

        self.assertEqual(doc._get_changed_fields(), ['embedded_field'])

        embedded_delta = {
            'string_field': 'hello',
            'int_field': 1,
            'dict_field': {'hello': 'world'},
            'list_field': ['1', 2, {'hello': 'world'}]
        }
        self.assertEqual(doc.embedded_field._delta(), (embedded_delta, {}))
        self.assertEqual(doc._delta(),
                         ({'embedded_field': embedded_delta}, {}))

        doc.save()
        doc = doc.reload(10)

        doc.embedded_field.dict_field = {}
        self.assertEqual(doc._get_changed_fields(),
                         ['embedded_field.dict_field'])
        self.assertEqual(doc.embedded_field._delta(), ({}, {'dict_field': 1}))
        self.assertEqual(doc._delta(), ({}, {'embedded_field.dict_field': 1}))
        doc.save()
        doc = doc.reload(10)
        self.assertEqual(doc.embedded_field.dict_field, {})

        doc.embedded_field.list_field = []
        self.assertEqual(doc._get_changed_fields(),
                         ['embedded_field.list_field'])
        self.assertEqual(doc.embedded_field._delta(), ({}, {'list_field': 1}))
        self.assertEqual(doc._delta(), ({}, {'embedded_field.list_field': 1}))
        doc.save()
        doc = doc.reload(10)
        self.assertEqual(doc.embedded_field.list_field, [])

        embedded_2 = Embedded()
        embedded_2.string_field = 'hello'
        embedded_2.int_field = 1
        embedded_2.dict_field = {'hello': 'world'}
        embedded_2.list_field = ['1', 2, {'hello': 'world'}]

        doc.embedded_field.list_field = ['1', 2, embedded_2]
        self.assertEqual(doc._get_changed_fields(),
                         ['embedded_field.list_field'])

        self.assertEqual(doc.embedded_field._delta(), ({
            'list_field': ['1', 2, {
                '_cls': 'Embedded',
                'string_field': 'hello',
                'dict_field': {'hello': 'world'},
                'int_field': 1,
                'list_field': ['1', 2, {'hello': 'world'}],
            }]
        }, {}))

        self.assertEqual(doc._delta(), ({
            'embedded_field.list_field': ['1', 2, {
                '_cls': 'Embedded',
                'string_field': 'hello',
                'dict_field': {'hello': 'world'},
                'int_field': 1,
                'list_field': ['1', 2, {'hello': 'world'}],
            }]
        }, {}))
        doc.save()
        doc = doc.reload(10)

        self.assertEqual(doc.embedded_field.list_field[0], '1')
        self.assertEqual(doc.embedded_field.list_field[1], 2)
        for k in doc.embedded_field.list_field[2]._fields:
            self.assertEqual(doc.embedded_field.list_field[2][k],
                             embedded_2[k])

        doc.embedded_field.list_field[2].string_field = 'world'
        self.assertEqual(doc._get_changed_fields(),
                         ['embedded_field.list_field.2.string_field'])
        self.assertEqual(doc.embedded_field._delta(),
                         ({'list_field.2.string_field': 'world'}, {}))
        self.assertEqual(doc._delta(),
                         ({'embedded_field.list_field.2.string_field': 'world'}, {}))
        doc.save()
        doc = doc.reload(10)
        self.assertEqual(doc.embedded_field.list_field[2].string_field,
                         'world')

        # Test multiple assignments
        doc.embedded_field.list_field[2].string_field = 'hello world'
        doc.embedded_field.list_field[2] = doc.embedded_field.list_field[2]
        self.assertEqual(doc._get_changed_fields(),
                         ['embedded_field.list_field'])
        self.assertEqual(doc.embedded_field._delta(), ({
            'list_field': ['1', 2, {
            '_cls': 'Embedded',
            'string_field': 'hello world',
            'int_field': 1,
            'list_field': ['1', 2, {'hello': 'world'}],
            'dict_field': {'hello': 'world'}}]}, {}))
        self.assertEqual(doc._delta(), ({
            'embedded_field.list_field': ['1', 2, {
                '_cls': 'Embedded',
                'string_field': 'hello world',
                'int_field': 1,
                'list_field': ['1', 2, {'hello': 'world'}],
                'dict_field': {'hello': 'world'}}
            ]}, {}))
        doc.save()
        doc = doc.reload(10)
        self.assertEqual(doc.embedded_field.list_field[2].string_field,
                         'hello world')

        # Test list native methods
        doc.embedded_field.list_field[2].list_field.pop(0)
        self.assertEqual(doc._delta(),
                         ({'embedded_field.list_field.2.list_field':
                          [2, {'hello': 'world'}]}, {}))
        doc.save()
        doc = doc.reload(10)

        doc.embedded_field.list_field[2].list_field.append(1)
        self.assertEqual(doc._delta(),
                         ({'embedded_field.list_field.2.list_field':
                          [2, {'hello': 'world'}, 1]}, {}))
        doc.save()
        doc = doc.reload(10)
        self.assertEqual(doc.embedded_field.list_field[2].list_field,
                         [2, {'hello': 'world'}, 1])

        doc.embedded_field.list_field[2].list_field.sort(key=str)
        doc.save()
        doc = doc.reload(10)
        self.assertEqual(doc.embedded_field.list_field[2].list_field,
                         [1, 2, {'hello': 'world'}])

        del(doc.embedded_field.list_field[2].list_field[2]['hello'])
        self.assertEqual(doc._delta(),
                         ({'embedded_field.list_field.2.list_field': [1, 2, {}]}, {}))
        doc.save()
        doc = doc.reload(10)

        del(doc.embedded_field.list_field[2].list_field)
        self.assertEqual(doc._delta(),
                         ({}, {'embedded_field.list_field.2.list_field': 1}))

        doc.save()
        doc = doc.reload(10)

        doc.dict_field['Embedded'] = embedded_1
        doc.save()
        doc = doc.reload(10)

        doc.dict_field['Embedded'].string_field = 'Hello World'
        self.assertEqual(doc._get_changed_fields(),
                         ['dict_field.Embedded.string_field'])
        self.assertEqual(doc._delta(),
                         ({'dict_field.Embedded.string_field': 'Hello World'}, {}))

    def test_circular_reference_deltas(self):
        self.circular_reference_deltas(Document, Document)
        self.circular_reference_deltas(Document, DynamicDocument)
        self.circular_reference_deltas(DynamicDocument, Document)
        self.circular_reference_deltas(DynamicDocument, DynamicDocument)

    def circular_reference_deltas(self, DocClass1, DocClass2):

        class Person(DocClass1):
            name = StringField()
            owns = ListField(ReferenceField('Organization'))

        class Organization(DocClass2):
            name = StringField()
            owner = ReferenceField('Person')

        Person.drop_collection()
        Organization.drop_collection()

        person = Person(name="owner").save()
        organization = Organization(name="company").save()

        person.owns.append(organization)
        organization.owner = person

        person.save()
        organization.save()

        p = Person.objects[0].select_related()
        o = Organization.objects.first()
        self.assertEqual(p.owns[0], o)
        self.assertEqual(o.owner, p)

    def test_circular_reference_deltas_2(self):
        self.circular_reference_deltas_2(Document, Document)
        self.circular_reference_deltas_2(Document, DynamicDocument)
        self.circular_reference_deltas_2(DynamicDocument, Document)
        self.circular_reference_deltas_2(DynamicDocument, DynamicDocument)

    def circular_reference_deltas_2(self, DocClass1, DocClass2, dbref=True):

        class Person(DocClass1):
            name = StringField()
            owns = ListField(ReferenceField('Organization', dbref=dbref))
            employer = ReferenceField('Organization', dbref=dbref)

        class Organization(DocClass2):
            name = StringField()
            owner = ReferenceField('Person', dbref=dbref)
            employees = ListField(ReferenceField('Person', dbref=dbref))

        Person.drop_collection()
        Organization.drop_collection()

        person = Person(name="owner").save()
        employee = Person(name="employee").save()
        organization = Organization(name="company").save()

        person.owns.append(organization)
        organization.owner = person

        organization.employees.append(employee)
        employee.employer = organization

        person.save()
        organization.save()
        employee.save()

        p = Person.objects.get(name="owner")
        e = Person.objects.get(name="employee")
        o = Organization.objects.first()

        self.assertEqual(p.owns[0], o)
        self.assertEqual(o.owner, p)
        self.assertEqual(e.employer, o)

        return person, organization, employee

    def test_delta_db_field(self):
        self.delta_db_field(Document)
        self.delta_db_field(DynamicDocument)

    def delta_db_field(self, DocClass):

        class Doc(DocClass):
            string_field = StringField(db_field='db_string_field')
            int_field = IntField(db_field='db_int_field')
            dict_field = DictField(db_field='db_dict_field')
            list_field = ListField(db_field='db_list_field')

        Doc.drop_collection()
        doc = Doc()
        doc.save()

        doc = Doc.objects.first()
        self.assertEqual(doc._get_changed_fields(), [])
        self.assertEqual(doc._delta(), ({}, {}))

        doc.string_field = 'hello'
        self.assertEqual(doc._get_changed_fields(), ['db_string_field'])
        self.assertEqual(doc._delta(), ({'db_string_field': 'hello'}, {}))

        doc._changed_fields = []
        doc.int_field = 1
        self.assertEqual(doc._get_changed_fields(), ['db_int_field'])
        self.assertEqual(doc._delta(), ({'db_int_field': 1}, {}))

        doc._changed_fields = []
        dict_value = {'hello': 'world', 'ping': 'pong'}
        doc.dict_field = dict_value
        self.assertEqual(doc._get_changed_fields(), ['db_dict_field'])
        self.assertEqual(doc._delta(), ({'db_dict_field': dict_value}, {}))

        doc._changed_fields = []
        list_value = ['1', 2, {'hello': 'world'}]
        doc.list_field = list_value
        self.assertEqual(doc._get_changed_fields(), ['db_list_field'])
        self.assertEqual(doc._delta(), ({'db_list_field': list_value}, {}))

        # Test unsetting
        doc._changed_fields = []
        doc.dict_field = {}
        self.assertEqual(doc._get_changed_fields(), ['db_dict_field'])
        self.assertEqual(doc._delta(), ({}, {'db_dict_field': 1}))

        doc._changed_fields = []
        doc.list_field = []
        self.assertEqual(doc._get_changed_fields(), ['db_list_field'])
        self.assertEqual(doc._delta(), ({}, {'db_list_field': 1}))

        # Test it saves that data
        doc = Doc()
        doc.save()

        doc.string_field = 'hello'
        doc.int_field = 1
        doc.dict_field = {'hello': 'world'}
        doc.list_field = ['1', 2, {'hello': 'world'}]
        doc.save()
        doc = doc.reload(10)

        self.assertEqual(doc.string_field, 'hello')
        self.assertEqual(doc.int_field, 1)
        self.assertEqual(doc.dict_field, {'hello': 'world'})
        self.assertEqual(doc.list_field, ['1', 2, {'hello': 'world'}])

    def test_delta_recursive_db_field(self):
        self.delta_recursive_db_field(Document, EmbeddedDocument)
        self.delta_recursive_db_field(Document, DynamicEmbeddedDocument)
        self.delta_recursive_db_field(DynamicDocument, EmbeddedDocument)
        self.delta_recursive_db_field(DynamicDocument, DynamicEmbeddedDocument)

    def delta_recursive_db_field(self, DocClass, EmbeddedClass):

        class Embedded(EmbeddedClass):
            string_field = StringField(db_field='db_string_field')
            int_field = IntField(db_field='db_int_field')
            dict_field = DictField(db_field='db_dict_field')
            list_field = ListField(db_field='db_list_field')

        class Doc(DocClass):
            string_field = StringField(db_field='db_string_field')
            int_field = IntField(db_field='db_int_field')
            dict_field = DictField(db_field='db_dict_field')
            list_field = ListField(db_field='db_list_field')
            embedded_field = EmbeddedDocumentField(Embedded,
                                    db_field='db_embedded_field')

        Doc.drop_collection()
        doc = Doc()
        doc.save()

        doc = Doc.objects.first()
        self.assertEqual(doc._get_changed_fields(), [])
        self.assertEqual(doc._delta(), ({}, {}))

        embedded_1 = Embedded()
        embedded_1.string_field = 'hello'
        embedded_1.int_field = 1
        embedded_1.dict_field = {'hello': 'world'}
        embedded_1.list_field = ['1', 2, {'hello': 'world'}]
        doc.embedded_field = embedded_1

        self.assertEqual(doc._get_changed_fields(), ['db_embedded_field'])

        embedded_delta = {
            'db_string_field': 'hello',
            'db_int_field': 1,
            'db_dict_field': {'hello': 'world'},
            'db_list_field': ['1', 2, {'hello': 'world'}]
        }
        self.assertEqual(doc.embedded_field._delta(), (embedded_delta, {}))
        self.assertEqual(doc._delta(),
            ({'db_embedded_field': embedded_delta}, {}))

        doc.save()
        doc = doc.reload(10)

        doc.embedded_field.dict_field = {}
        self.assertEqual(doc._get_changed_fields(),
            ['db_embedded_field.db_dict_field'])
        self.assertEqual(doc.embedded_field._delta(),
            ({}, {'db_dict_field': 1}))
        self.assertEqual(doc._delta(),
            ({}, {'db_embedded_field.db_dict_field': 1}))
        doc.save()
        doc = doc.reload(10)
        self.assertEqual(doc.embedded_field.dict_field, {})

        doc.embedded_field.list_field = []
        self.assertEqual(doc._get_changed_fields(),
            ['db_embedded_field.db_list_field'])
        self.assertEqual(doc.embedded_field._delta(),
            ({}, {'db_list_field': 1}))
        self.assertEqual(doc._delta(),
            ({}, {'db_embedded_field.db_list_field': 1}))
        doc.save()
        doc = doc.reload(10)
        self.assertEqual(doc.embedded_field.list_field, [])

        embedded_2 = Embedded()
        embedded_2.string_field = 'hello'
        embedded_2.int_field = 1
        embedded_2.dict_field = {'hello': 'world'}
        embedded_2.list_field = ['1', 2, {'hello': 'world'}]

        doc.embedded_field.list_field = ['1', 2, embedded_2]
        self.assertEqual(doc._get_changed_fields(),
            ['db_embedded_field.db_list_field'])
        self.assertEqual(doc.embedded_field._delta(), ({
            'db_list_field': ['1', 2, {
                '_cls': 'Embedded',
                'db_string_field': 'hello',
                'db_dict_field': {'hello': 'world'},
                'db_int_field': 1,
                'db_list_field': ['1', 2, {'hello': 'world'}],
            }]
        }, {}))

        self.assertEqual(doc._delta(), ({
            'db_embedded_field.db_list_field': ['1', 2, {
                '_cls': 'Embedded',
                'db_string_field': 'hello',
                'db_dict_field': {'hello': 'world'},
                'db_int_field': 1,
                'db_list_field': ['1', 2, {'hello': 'world'}],
            }]
        }, {}))
        doc.save()
        doc = doc.reload(10)

        self.assertEqual(doc.embedded_field.list_field[0], '1')
        self.assertEqual(doc.embedded_field.list_field[1], 2)
        for k in doc.embedded_field.list_field[2]._fields:
            self.assertEqual(doc.embedded_field.list_field[2][k],
                             embedded_2[k])

        doc.embedded_field.list_field[2].string_field = 'world'
        self.assertEqual(doc._get_changed_fields(),
            ['db_embedded_field.db_list_field.2.db_string_field'])
        self.assertEqual(doc.embedded_field._delta(),
            ({'db_list_field.2.db_string_field': 'world'}, {}))
        self.assertEqual(doc._delta(),
            ({'db_embedded_field.db_list_field.2.db_string_field': 'world'},
             {}))
        doc.save()
        doc = doc.reload(10)
        self.assertEqual(doc.embedded_field.list_field[2].string_field,
                        'world')

        # Test multiple assignments
        doc.embedded_field.list_field[2].string_field = 'hello world'
        doc.embedded_field.list_field[2] = doc.embedded_field.list_field[2]
        self.assertEqual(doc._get_changed_fields(),
            ['db_embedded_field.db_list_field'])
        self.assertEqual(doc.embedded_field._delta(), ({
            'db_list_field': ['1', 2, {
            '_cls': 'Embedded',
            'db_string_field': 'hello world',
            'db_int_field': 1,
            'db_list_field': ['1', 2, {'hello': 'world'}],
            'db_dict_field': {'hello': 'world'}}]}, {}))
        self.assertEqual(doc._delta(), ({
            'db_embedded_field.db_list_field': ['1', 2, {
                '_cls': 'Embedded',
                'db_string_field': 'hello world',
                'db_int_field': 1,
                'db_list_field': ['1', 2, {'hello': 'world'}],
                'db_dict_field': {'hello': 'world'}}
            ]}, {}))
        doc.save()
        doc = doc.reload(10)
        self.assertEqual(doc.embedded_field.list_field[2].string_field,
                        'hello world')

        # Test list native methods
        doc.embedded_field.list_field[2].list_field.pop(0)
        self.assertEqual(doc._delta(),
            ({'db_embedded_field.db_list_field.2.db_list_field':
                [2, {'hello': 'world'}]}, {}))
        doc.save()
        doc = doc.reload(10)

        doc.embedded_field.list_field[2].list_field.append(1)
        self.assertEqual(doc._delta(),
            ({'db_embedded_field.db_list_field.2.db_list_field':
                [2, {'hello': 'world'}, 1]}, {}))
        doc.save()
        doc = doc.reload(10)
        self.assertEqual(doc.embedded_field.list_field[2].list_field,
            [2, {'hello': 'world'}, 1])

        doc.embedded_field.list_field[2].list_field.sort(key=str)
        doc.save()
        doc = doc.reload(10)
        self.assertEqual(doc.embedded_field.list_field[2].list_field,
            [1, 2, {'hello': 'world'}])

        del(doc.embedded_field.list_field[2].list_field[2]['hello'])
        self.assertEqual(doc._delta(),
            ({'db_embedded_field.db_list_field.2.db_list_field':
                [1, 2, {}]}, {}))
        doc.save()
        doc = doc.reload(10)

        del(doc.embedded_field.list_field[2].list_field)
        self.assertEqual(doc._delta(), ({},
            {'db_embedded_field.db_list_field.2.db_list_field': 1}))

    def test_delta_for_dynamic_documents(self):
        class Person(DynamicDocument):
            name = StringField()
            meta = {'allow_inheritance': True}

        Person.drop_collection()

        p = Person(name="James", age=34)
        self.assertEqual(p._delta(), (
            SON([('_cls', 'Person'), ('name', 'James'), ('age', 34)]), {}))

        p.doc = 123
        del(p.doc)
        self.assertEqual(p._delta(), (
            SON([('_cls', 'Person'), ('name', 'James'), ('age', 34)]), {}))

        p = Person()
        p.name = "Dean"
        p.age = 22
        p.save()

        p.age = 24
        self.assertEqual(p.age, 24)
        self.assertEqual(p._get_changed_fields(), ['age'])
        self.assertEqual(p._delta(), ({'age': 24}, {}))

        p = Person.objects(age=22).get()
        p.age = 24
        self.assertEqual(p.age, 24)
        self.assertEqual(p._get_changed_fields(), ['age'])
        self.assertEqual(p._delta(), ({'age': 24}, {}))

        p.save()
        self.assertEqual(1, Person.objects(age=24).count())

    def test_dynamic_delta(self):

        class Doc(DynamicDocument):
            pass

        Doc.drop_collection()
        doc = Doc()
        doc.save()

        doc = Doc.objects.first()
        self.assertEqual(doc._get_changed_fields(), [])
        self.assertEqual(doc._delta(), ({}, {}))

        doc.string_field = 'hello'
        self.assertEqual(doc._get_changed_fields(), ['string_field'])
        self.assertEqual(doc._delta(), ({'string_field': 'hello'}, {}))

        doc._changed_fields = []
        doc.int_field = 1
        self.assertEqual(doc._get_changed_fields(), ['int_field'])
        self.assertEqual(doc._delta(), ({'int_field': 1}, {}))

        doc._changed_fields = []
        dict_value = {'hello': 'world', 'ping': 'pong'}
        doc.dict_field = dict_value
        self.assertEqual(doc._get_changed_fields(), ['dict_field'])
        self.assertEqual(doc._delta(), ({'dict_field': dict_value}, {}))

        doc._changed_fields = []
        list_value = ['1', 2, {'hello': 'world'}]
        doc.list_field = list_value
        self.assertEqual(doc._get_changed_fields(), ['list_field'])
        self.assertEqual(doc._delta(), ({'list_field': list_value}, {}))

        # Test unsetting
        doc._changed_fields = []
        doc.dict_field = {}
        self.assertEqual(doc._get_changed_fields(), ['dict_field'])
        self.assertEqual(doc._delta(), ({}, {'dict_field': 1}))

        doc._changed_fields = []
        doc.list_field = []
        self.assertEqual(doc._get_changed_fields(), ['list_field'])
        self.assertEqual(doc._delta(), ({}, {'list_field': 1}))

    def test_delta_with_dbref_true(self):
        person, organization, employee = self.circular_reference_deltas_2(Document, Document, True)
        employee.name = 'test'

        self.assertEqual(organization._get_changed_fields(), [])

        updates, removals = organization._delta()
        self.assertEqual({}, removals)
        self.assertEqual({}, updates)

        organization.employees.append(person)
        updates, removals = organization._delta()
        self.assertEqual({}, removals)
        self.assertTrue('employees' in updates)

    def test_delta_with_dbref_false(self):
        person, organization, employee = self.circular_reference_deltas_2(Document, Document, False)
        employee.name = 'test'

        self.assertEqual(organization._get_changed_fields(), [])

        updates, removals = organization._delta()
        self.assertEqual({}, removals)
        self.assertEqual({}, updates)

        organization.employees.append(person)
        updates, removals = organization._delta()
        self.assertEqual({}, removals)
        self.assertTrue('employees' in updates)

    def test_nested_nested_fields_mark_as_changed(self):
        class EmbeddedDoc(EmbeddedDocument):
            name = StringField()

        class MyDoc(Document):
            subs = MapField(MapField(EmbeddedDocumentField(EmbeddedDoc)))
            name = StringField()

        MyDoc.drop_collection()

        mydoc = MyDoc(name='testcase1', subs={'a': {'b': EmbeddedDoc(name='foo')}}).save()

        mydoc = MyDoc.objects.first()
        subdoc = mydoc.subs['a']['b']
        subdoc.name = 'bar'

        self.assertEqual(["name"], subdoc._get_changed_fields())
        self.assertEqual(["subs.a.b.name"], mydoc._get_changed_fields())

        mydoc._clear_changed_fields()
        self.assertEqual([], mydoc._get_changed_fields())

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = dynamic
import unittest
import sys
sys.path[0:0] = [""]

from mongoengine import *
from mongoengine.connection import get_db

__all__ = ("DynamicTest", )


class DynamicTest(unittest.TestCase):

    def setUp(self):
        connect(db='mongoenginetest')
        self.db = get_db()

        class Person(DynamicDocument):
            name = StringField()
            meta = {'allow_inheritance': True}

        Person.drop_collection()

        self.Person = Person

    def test_simple_dynamic_document(self):
        """Ensures simple dynamic documents are saved correctly"""

        p = self.Person()
        p.name = "James"
        p.age = 34

        self.assertEqual(p.to_mongo(), {"_cls": "Person", "name": "James",
                                        "age": 34})
        self.assertEqual(p.to_mongo().keys(), ["_cls", "name", "age"])
        p.save()
        self.assertEqual(p.to_mongo().keys(), ["_id", "_cls", "name", "age"])

        self.assertEqual(self.Person.objects.first().age, 34)

        # Confirm no changes to self.Person
        self.assertFalse(hasattr(self.Person, 'age'))

    def test_change_scope_of_variable(self):
        """Test changing the scope of a dynamic field has no adverse effects"""
        p = self.Person()
        p.name = "Dean"
        p.misc = 22
        p.save()

        p = self.Person.objects.get()
        p.misc = {'hello': 'world'}
        p.save()

        p = self.Person.objects.get()
        self.assertEqual(p.misc, {'hello': 'world'})

    def test_delete_dynamic_field(self):
        """Test deleting a dynamic field works"""
        self.Person.drop_collection()
        p = self.Person()
        p.name = "Dean"
        p.misc = 22
        p.save()

        p = self.Person.objects.get()
        p.misc = {'hello': 'world'}
        p.save()

        p = self.Person.objects.get()
        self.assertEqual(p.misc, {'hello': 'world'})
        collection = self.db[self.Person._get_collection_name()]
        obj = collection.find_one()
        self.assertEqual(sorted(obj.keys()), ['_cls', '_id', 'misc', 'name'])

        del(p.misc)
        p.save()

        p = self.Person.objects.get()
        self.assertFalse(hasattr(p, 'misc'))

        obj = collection.find_one()
        self.assertEqual(sorted(obj.keys()), ['_cls', '_id', 'name'])

    def test_dynamic_document_queries(self):
        """Ensure we can query dynamic fields"""
        p = self.Person()
        p.name = "Dean"
        p.age = 22
        p.save()

        self.assertEqual(1, self.Person.objects(age=22).count())
        p = self.Person.objects(age=22)
        p = p.get()
        self.assertEqual(22, p.age)

    def test_complex_dynamic_document_queries(self):
        class Person(DynamicDocument):
            name = StringField()

        Person.drop_collection()

        p = Person(name="test")
        p.age = "ten"
        p.save()

        p1 = Person(name="test1")
        p1.age = "less then ten and a half"
        p1.save()

        p2 = Person(name="test2")
        p2.age = 10
        p2.save()

        self.assertEqual(Person.objects(age__icontains='ten').count(), 2)
        self.assertEqual(Person.objects(age__gte=10).count(), 1)

    def test_complex_data_lookups(self):
        """Ensure you can query dynamic document dynamic fields"""
        p = self.Person()
        p.misc = {'hello': 'world'}
        p.save()

        self.assertEqual(1, self.Person.objects(misc__hello='world').count())

    def test_complex_embedded_document_validation(self):
        """Ensure embedded dynamic documents may be validated"""
        class Embedded(DynamicEmbeddedDocument):
            content = URLField()

        class Doc(DynamicDocument):
            pass

        Doc.drop_collection()
        doc = Doc()

        embedded_doc_1 = Embedded(content='http://mongoengine.org')
        embedded_doc_1.validate()

        embedded_doc_2 = Embedded(content='this is not a url')
        self.assertRaises(ValidationError, embedded_doc_2.validate)

        doc.embedded_field_1 = embedded_doc_1
        doc.embedded_field_2 = embedded_doc_2
        self.assertRaises(ValidationError, doc.validate)

    def test_inheritance(self):
        """Ensure that dynamic document plays nice with inheritance"""
        class Employee(self.Person):
            salary = IntField()

        Employee.drop_collection()

        self.assertTrue('name' in Employee._fields)
        self.assertTrue('salary' in Employee._fields)
        self.assertEqual(Employee._get_collection_name(),
                         self.Person._get_collection_name())

        joe_bloggs = Employee()
        joe_bloggs.name = "Joe Bloggs"
        joe_bloggs.salary = 10
        joe_bloggs.age = 20
        joe_bloggs.save()

        self.assertEqual(1, self.Person.objects(age=20).count())
        self.assertEqual(1, Employee.objects(age=20).count())

        joe_bloggs = self.Person.objects.first()
        self.assertTrue(isinstance(joe_bloggs, Employee))

    def test_embedded_dynamic_document(self):
        """Test dynamic embedded documents"""
        class Embedded(DynamicEmbeddedDocument):
            pass

        class Doc(DynamicDocument):
            pass

        Doc.drop_collection()
        doc = Doc()

        embedded_1 = Embedded()
        embedded_1.string_field = 'hello'
        embedded_1.int_field = 1
        embedded_1.dict_field = {'hello': 'world'}
        embedded_1.list_field = ['1', 2, {'hello': 'world'}]
        doc.embedded_field = embedded_1

        self.assertEqual(doc.to_mongo(), {
            "embedded_field": {
                "_cls": "Embedded",
                "string_field": "hello",
                "int_field": 1,
                "dict_field": {"hello": "world"},
                "list_field": ['1', 2, {'hello': 'world'}]
            }
        })
        doc.save()

        doc = Doc.objects.first()
        self.assertEqual(doc.embedded_field.__class__, Embedded)
        self.assertEqual(doc.embedded_field.string_field, "hello")
        self.assertEqual(doc.embedded_field.int_field, 1)
        self.assertEqual(doc.embedded_field.dict_field, {'hello': 'world'})
        self.assertEqual(doc.embedded_field.list_field,
                            ['1', 2, {'hello': 'world'}])

    def test_complex_embedded_documents(self):
        """Test complex dynamic embedded documents setups"""
        class Embedded(DynamicEmbeddedDocument):
            pass

        class Doc(DynamicDocument):
            pass

        Doc.drop_collection()
        doc = Doc()

        embedded_1 = Embedded()
        embedded_1.string_field = 'hello'
        embedded_1.int_field = 1
        embedded_1.dict_field = {'hello': 'world'}

        embedded_2 = Embedded()
        embedded_2.string_field = 'hello'
        embedded_2.int_field = 1
        embedded_2.dict_field = {'hello': 'world'}
        embedded_2.list_field = ['1', 2, {'hello': 'world'}]

        embedded_1.list_field = ['1', 2, embedded_2]
        doc.embedded_field = embedded_1

        self.assertEqual(doc.to_mongo(), {
            "embedded_field": {
                "_cls": "Embedded",
                "string_field": "hello",
                "int_field": 1,
                "dict_field": {"hello": "world"},
                "list_field": ['1', 2,
                    {"_cls": "Embedded",
                    "string_field": "hello",
                    "int_field": 1,
                    "dict_field": {"hello": "world"},
                    "list_field": ['1', 2, {'hello': 'world'}]}
                ]
            }
        })
        doc.save()
        doc = Doc.objects.first()
        self.assertEqual(doc.embedded_field.__class__, Embedded)
        self.assertEqual(doc.embedded_field.string_field, "hello")
        self.assertEqual(doc.embedded_field.int_field, 1)
        self.assertEqual(doc.embedded_field.dict_field, {'hello': 'world'})
        self.assertEqual(doc.embedded_field.list_field[0], '1')
        self.assertEqual(doc.embedded_field.list_field[1], 2)

        embedded_field = doc.embedded_field.list_field[2]

        self.assertEqual(embedded_field.__class__, Embedded)
        self.assertEqual(embedded_field.string_field, "hello")
        self.assertEqual(embedded_field.int_field, 1)
        self.assertEqual(embedded_field.dict_field, {'hello': 'world'})
        self.assertEqual(embedded_field.list_field, ['1', 2,
                                                        {'hello': 'world'}])

    def test_dynamic_and_embedded(self):
        """Ensure embedded documents play nicely"""

        class Address(EmbeddedDocument):
            city = StringField()

        class Person(DynamicDocument):
            name = StringField()

        Person.drop_collection()

        Person(name="Ross", address=Address(city="London")).save()

        person = Person.objects.first()
        person.address.city = "Lundenne"
        person.save()

        self.assertEqual(Person.objects.first().address.city, "Lundenne")

        person = Person.objects.first()
        person.address = Address(city="Londinium")
        person.save()

        self.assertEqual(Person.objects.first().address.city, "Londinium")

        person = Person.objects.first()
        person.age = 35
        person.save()
        self.assertEqual(Person.objects.first().age, 35)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = indexes
# -*- coding: utf-8 -*-
import unittest
import sys
sys.path[0:0] = [""]

import os
import pymongo

from nose.plugins.skip import SkipTest
from datetime import datetime

from mongoengine import *
from mongoengine.connection import get_db, get_connection

__all__ = ("IndexesTest", )


class IndexesTest(unittest.TestCase):

    def setUp(self):
        connect(db='mongoenginetest')
        self.db = get_db()

        class Person(Document):
            name = StringField()
            age = IntField()

            non_field = True

            meta = {"allow_inheritance": True}

        self.Person = Person

    def tearDown(self):
        for collection in self.db.collection_names():
            if 'system.' in collection:
                continue
            self.db.drop_collection(collection)

    def test_indexes_document(self):
        """Ensure that indexes are used when meta[indexes] is specified for
        Documents
        """
        self._index_test(Document)

    def test_indexes_dynamic_document(self):
        """Ensure that indexes are used when meta[indexes] is specified for
        Dynamic Documents
        """
        self._index_test(DynamicDocument)

    def _index_test(self, InheritFrom):

        class BlogPost(InheritFrom):
            date = DateTimeField(db_field='addDate', default=datetime.now)
            category = StringField()
            tags = ListField(StringField())
            meta = {
                'indexes': [
                    '-date',
                    'tags',
                    ('category', '-date')
                ]
            }

        expected_specs = [{'fields': [('addDate', -1)]},
                          {'fields': [('tags', 1)]},
                          {'fields': [('category', 1), ('addDate', -1)]}]
        self.assertEqual(expected_specs, BlogPost._meta['index_specs'])

        BlogPost.ensure_indexes()
        info = BlogPost.objects._collection.index_information()
        # _id, '-date', 'tags', ('cat', 'date')
        self.assertEqual(len(info), 4)
        info = [value['key'] for key, value in info.iteritems()]
        for expected in expected_specs:
            self.assertTrue(expected['fields'] in info)

    def _index_test_inheritance(self, InheritFrom):

        class BlogPost(InheritFrom):
            date = DateTimeField(db_field='addDate', default=datetime.now)
            category = StringField()
            tags = ListField(StringField())
            meta = {
                'indexes': [
                    '-date',
                    'tags',
                    ('category', '-date')
                ],
                'allow_inheritance': True
            }

        expected_specs = [{'fields': [('_cls', 1), ('addDate', -1)]},
                          {'fields': [('_cls', 1), ('tags', 1)]},
                          {'fields': [('_cls', 1), ('category', 1),
                                      ('addDate', -1)]}]
        self.assertEqual(expected_specs, BlogPost._meta['index_specs'])

        BlogPost.ensure_indexes()
        info = BlogPost.objects._collection.index_information()
        # _id, '-date', 'tags', ('cat', 'date')
        # NB: there is no index on _cls by itself, since
        # the indices on -date and tags will both contain
        # _cls as first element in the key
        self.assertEqual(len(info), 4)
        info = [value['key'] for key, value in info.iteritems()]
        for expected in expected_specs:
            self.assertTrue(expected['fields'] in info)

        class ExtendedBlogPost(BlogPost):
            title = StringField()
            meta = {'indexes': ['title']}

        expected_specs.append({'fields': [('_cls', 1), ('title', 1)]})
        self.assertEqual(expected_specs, ExtendedBlogPost._meta['index_specs'])

        BlogPost.drop_collection()

        ExtendedBlogPost.ensure_indexes()
        info = ExtendedBlogPost.objects._collection.index_information()
        info = [value['key'] for key, value in info.iteritems()]
        for expected in expected_specs:
            self.assertTrue(expected['fields'] in info)

    def test_indexes_document_inheritance(self):
        """Ensure that indexes are used when meta[indexes] is specified for
        Documents
        """
        self._index_test_inheritance(Document)

    def test_indexes_dynamic_document_inheritance(self):
        """Ensure that indexes are used when meta[indexes] is specified for
        Dynamic Documents
        """
        self._index_test_inheritance(DynamicDocument)

    def test_inherited_index(self):
        """Ensure index specs are inhertited correctly"""

        class A(Document):
            title = StringField()
            meta = {
                'indexes': [
                        {
                        'fields': ('title',),
                        },
                ],
                'allow_inheritance': True,
                }

        class B(A):
            description = StringField()

        self.assertEqual(A._meta['index_specs'], B._meta['index_specs'])
        self.assertEqual([{'fields': [('_cls', 1), ('title', 1)]}],
                         A._meta['index_specs'])

    def test_index_no_cls(self):
        """Ensure index specs are inhertited correctly"""

        class A(Document):
            title = StringField()
            meta = {
                'indexes': [
                        {'fields': ('title',), 'cls': False},
                ],
                'allow_inheritance': True,
                'index_cls': False
                }

        self.assertEqual([('title', 1)], A._meta['index_specs'][0]['fields'])
        A._get_collection().drop_indexes()
        A.ensure_indexes()
        info = A._get_collection().index_information()
        self.assertEqual(len(info.keys()), 2)

    def test_build_index_spec_is_not_destructive(self):

        class MyDoc(Document):
            keywords = StringField()

            meta = {
                'indexes': ['keywords'],
                'allow_inheritance': False
            }

        self.assertEqual(MyDoc._meta['index_specs'],
                         [{'fields': [('keywords', 1)]}])

        # Force index creation
        MyDoc.ensure_indexes()

        self.assertEqual(MyDoc._meta['index_specs'],
                        [{'fields': [('keywords', 1)]}])

    def test_embedded_document_index_meta(self):
        """Ensure that embedded document indexes are created explicitly
        """
        class Rank(EmbeddedDocument):
            title = StringField(required=True)

        class Person(Document):
            name = StringField(required=True)
            rank = EmbeddedDocumentField(Rank, required=False)

            meta = {
                'indexes': [
                    'rank.title',
                ],
                'allow_inheritance': False
            }

        self.assertEqual([{'fields': [('rank.title', 1)]}],
                        Person._meta['index_specs'])

        Person.drop_collection()

        # Indexes are lazy so use list() to perform query
        list(Person.objects)
        info = Person.objects._collection.index_information()
        info = [value['key'] for key, value in info.iteritems()]
        self.assertTrue([('rank.title', 1)] in info)

    def test_explicit_geo2d_index(self):
        """Ensure that geo2d indexes work when created via meta[indexes]
        """
        class Place(Document):
            location = DictField()
            meta = {
                'allow_inheritance': True,
                'indexes': [
                    '*location.point',
                ]
            }

        self.assertEqual([{'fields': [('location.point', '2d')]}],
                         Place._meta['index_specs'])

        Place.ensure_indexes()
        info = Place._get_collection().index_information()
        info = [value['key'] for key, value in info.iteritems()]
        self.assertTrue([('location.point', '2d')] in info)

    def test_explicit_geo2d_index_embedded(self):
        """Ensure that geo2d indexes work when created via meta[indexes]
        """
        class EmbeddedLocation(EmbeddedDocument):
            location = DictField()

        class Place(Document):
            current = DictField(field=EmbeddedDocumentField('EmbeddedLocation'))
            meta = {
                'allow_inheritance': True,
                'indexes': [
                    '*current.location.point',
                ]
            }

        self.assertEqual([{'fields': [('current.location.point', '2d')]}],
                         Place._meta['index_specs'])

        Place.ensure_indexes()
        info = Place._get_collection().index_information()
        info = [value['key'] for key, value in info.iteritems()]
        self.assertTrue([('current.location.point', '2d')] in info)

    def test_dictionary_indexes(self):
        """Ensure that indexes are used when meta[indexes] contains
        dictionaries instead of lists.
        """
        class BlogPost(Document):
            date = DateTimeField(db_field='addDate', default=datetime.now)
            category = StringField()
            tags = ListField(StringField())
            meta = {
                'indexes': [
                    {'fields': ['-date'], 'unique': True, 'sparse': True},
                ],
            }

        self.assertEqual([{'fields': [('addDate', -1)], 'unique': True,
                          'sparse': True}],
                         BlogPost._meta['index_specs'])

        BlogPost.drop_collection()

        info = BlogPost.objects._collection.index_information()
        # _id, '-date'
        self.assertEqual(len(info), 2)

        # Indexes are lazy so use list() to perform query
        list(BlogPost.objects)
        info = BlogPost.objects._collection.index_information()
        info = [(value['key'],
                 value.get('unique', False),
                 value.get('sparse', False))
                for key, value in info.iteritems()]
        self.assertTrue(([('addDate', -1)], True, True) in info)

        BlogPost.drop_collection()

    def test_abstract_index_inheritance(self):

        class UserBase(Document):
            user_guid = StringField(required=True)
            meta = {
                'abstract': True,
                'indexes': ['user_guid'],
                'allow_inheritance': True
            }

        class Person(UserBase):
            name = StringField()

            meta = {
                'indexes': ['name'],
            }
        Person.drop_collection()

        Person(name="test", user_guid='123').save()

        self.assertEqual(1, Person.objects.count())
        info = Person.objects._collection.index_information()
        self.assertEqual(sorted(info.keys()),
                         ['_cls_1_name_1', '_cls_1_user_guid_1', '_id_'])

    def test_disable_index_creation(self):
        """Tests setting auto_create_index to False on the connection will
        disable any index generation.
        """
        class User(Document):
            meta = {
                'allow_inheritance': True,
                'indexes': ['user_guid'],
                'auto_create_index': False
            }
            user_guid = StringField(required=True)

        class MongoUser(User):
            pass

        User.drop_collection()

        User(user_guid='123').save()
        MongoUser(user_guid='123').save()

        self.assertEqual(2, User.objects.count())
        info = User.objects._collection.index_information()
        self.assertEqual(info.keys(), ['_id_'])

        User.ensure_indexes()
        info = User.objects._collection.index_information()
        self.assertEqual(sorted(info.keys()), ['_cls_1_user_guid_1', '_id_'])
        User.drop_collection()

    def test_embedded_document_index(self):
        """Tests settings an index on an embedded document
        """
        class Date(EmbeddedDocument):
            year = IntField(db_field='yr')

        class BlogPost(Document):
            title = StringField()
            date = EmbeddedDocumentField(Date)

            meta = {
                'indexes': [
                    '-date.year'
                ],
            }

        BlogPost.drop_collection()

        info = BlogPost.objects._collection.index_information()
        self.assertEqual(sorted(info.keys()), ['_id_', 'date.yr_-1'])
        BlogPost.drop_collection()

    def test_list_embedded_document_index(self):
        """Ensure list embedded documents can be indexed
        """
        class Tag(EmbeddedDocument):
            name = StringField(db_field='tag')

        class BlogPost(Document):
            title = StringField()
            tags = ListField(EmbeddedDocumentField(Tag))

            meta = {
                'indexes': [
                    'tags.name'
                ]
            }

        BlogPost.drop_collection()

        info = BlogPost.objects._collection.index_information()
        # we don't use _cls in with list fields by default
        self.assertEqual(sorted(info.keys()), ['_id_', 'tags.tag_1'])

        post1 = BlogPost(title="Embedded Indexes tests in place",
                         tags=[Tag(name="about"), Tag(name="time")])
        post1.save()
        BlogPost.drop_collection()

    def test_recursive_embedded_objects_dont_break_indexes(self):

        class RecursiveObject(EmbeddedDocument):
            obj = EmbeddedDocumentField('self')

        class RecursiveDocument(Document):
            recursive_obj = EmbeddedDocumentField(RecursiveObject)
            meta = {'allow_inheritance': True}

        RecursiveDocument.ensure_indexes()
        info = RecursiveDocument._get_collection().index_information()
        self.assertEqual(sorted(info.keys()), ['_cls_1', '_id_'])

    def test_covered_index(self):
        """Ensure that covered indexes can be used
        """

        class Test(Document):
            a = IntField()

            meta = {
                'indexes': ['a'],
                'allow_inheritance': False
            }

        Test.drop_collection()

        obj = Test(a=1)
        obj.save()

        # Need to be explicit about covered indexes as mongoDB doesn't know if
        # the documents returned might have more keys in that here.
        query_plan = Test.objects(id=obj.id).exclude('a').explain()
        self.assertFalse(query_plan['indexOnly'])

        query_plan = Test.objects(id=obj.id).only('id').explain()
        self.assertTrue(query_plan['indexOnly'])

        query_plan = Test.objects(a=1).only('a').exclude('id').explain()
        self.assertTrue(query_plan['indexOnly'])

    def test_index_on_id(self):

        class BlogPost(Document):
            meta = {
                'indexes': [
                    ['categories', 'id']
                ]
            }

            title = StringField(required=True)
            description = StringField(required=True)
            categories = ListField()

        BlogPost.drop_collection()

        indexes = BlogPost.objects._collection.index_information()
        self.assertEqual(indexes['categories_1__id_1']['key'],
                                 [('categories', 1), ('_id', 1)])

    def test_hint(self):

        class BlogPost(Document):
            tags = ListField(StringField())
            meta = {
                'indexes': [
                    'tags',
                ],
            }

        BlogPost.drop_collection()

        for i in xrange(0, 10):
            tags = [("tag %i" % n) for n in xrange(0, i % 2)]
            BlogPost(tags=tags).save()

        self.assertEqual(BlogPost.objects.count(), 10)
        self.assertEqual(BlogPost.objects.hint().count(), 10)
        self.assertEqual(BlogPost.objects.hint([('tags', 1)]).count(), 10)

        self.assertEqual(BlogPost.objects.hint([('ZZ', 1)]).count(), 10)

        def invalid_index():
            BlogPost.objects.hint('tags')
        self.assertRaises(TypeError, invalid_index)

        def invalid_index_2():
            return BlogPost.objects.hint(('tags', 1))
        self.assertRaises(Exception, invalid_index_2)

    def test_unique(self):
        """Ensure that uniqueness constraints are applied to fields.
        """
        class BlogPost(Document):
            title = StringField()
            slug = StringField(unique=True)

        BlogPost.drop_collection()

        post1 = BlogPost(title='test1', slug='test')
        post1.save()

        # Two posts with the same slug is not allowed
        post2 = BlogPost(title='test2', slug='test')
        self.assertRaises(NotUniqueError, post2.save)

        # Ensure backwards compatibilty for errors
        self.assertRaises(OperationError, post2.save)

    def test_unique_with(self):
        """Ensure that unique_with constraints are applied to fields.
        """
        class Date(EmbeddedDocument):
            year = IntField(db_field='yr')

        class BlogPost(Document):
            title = StringField()
            date = EmbeddedDocumentField(Date)
            slug = StringField(unique_with='date.year')

        BlogPost.drop_collection()

        post1 = BlogPost(title='test1', date=Date(year=2009), slug='test')
        post1.save()

        # day is different so won't raise exception
        post2 = BlogPost(title='test2', date=Date(year=2010), slug='test')
        post2.save()

        # Now there will be two docs with the same slug and the same day: fail
        post3 = BlogPost(title='test3', date=Date(year=2010), slug='test')
        self.assertRaises(OperationError, post3.save)

        BlogPost.drop_collection()

    def test_unique_embedded_document(self):
        """Ensure that uniqueness constraints are applied to fields on embedded documents.
        """
        class SubDocument(EmbeddedDocument):
            year = IntField(db_field='yr')
            slug = StringField(unique=True)

        class BlogPost(Document):
            title = StringField()
            sub = EmbeddedDocumentField(SubDocument)

        BlogPost.drop_collection()

        post1 = BlogPost(title='test1',
                         sub=SubDocument(year=2009, slug="test"))
        post1.save()

        # sub.slug is different so won't raise exception
        post2 = BlogPost(title='test2',
                         sub=SubDocument(year=2010, slug='another-slug'))
        post2.save()

        # Now there will be two docs with the same sub.slug
        post3 = BlogPost(title='test3',
                         sub=SubDocument(year=2010, slug='test'))
        self.assertRaises(NotUniqueError, post3.save)

        BlogPost.drop_collection()

    def test_unique_with_embedded_document_and_embedded_unique(self):
        """Ensure that uniqueness constraints are applied to fields on
        embedded documents.  And work with unique_with as well.
        """
        class SubDocument(EmbeddedDocument):
            year = IntField(db_field='yr')
            slug = StringField(unique=True)

        class BlogPost(Document):
            title = StringField(unique_with='sub.year')
            sub = EmbeddedDocumentField(SubDocument)

        BlogPost.drop_collection()

        post1 = BlogPost(title='test1',
                         sub=SubDocument(year=2009, slug="test"))
        post1.save()

        # sub.slug is different so won't raise exception
        post2 = BlogPost(title='test2',
                         sub=SubDocument(year=2010, slug='another-slug'))
        post2.save()

        # Now there will be two docs with the same sub.slug
        post3 = BlogPost(title='test3',
                         sub=SubDocument(year=2010, slug='test'))
        self.assertRaises(NotUniqueError, post3.save)

        # Now there will be two docs with the same title and year
        post3 = BlogPost(title='test1',
                         sub=SubDocument(year=2009, slug='test-1'))
        self.assertRaises(NotUniqueError, post3.save)

        BlogPost.drop_collection()

    def test_ttl_indexes(self):

        class Log(Document):
            created = DateTimeField(default=datetime.now)
            meta = {
                'indexes': [
                    {'fields': ['created'], 'expireAfterSeconds': 3600}
                ]
            }

        Log.drop_collection()

        if pymongo.version_tuple[0] < 2 and pymongo.version_tuple[1] < 3:
            raise SkipTest('pymongo needs to be 2.3 or higher for this test')

        connection = get_connection()
        version_array = connection.server_info()['versionArray']
        if version_array[0] < 2 and version_array[1] < 2:
            raise SkipTest('MongoDB needs to be 2.2 or higher for this test')

        # Indexes are lazy so use list() to perform query
        list(Log.objects)
        info = Log.objects._collection.index_information()
        self.assertEqual(3600,
                         info['created_1']['expireAfterSeconds'])

    def test_unique_and_indexes(self):
        """Ensure that 'unique' constraints aren't overridden by
        meta.indexes.
        """
        class Customer(Document):
            cust_id = IntField(unique=True, required=True)
            meta = {
                'indexes': ['cust_id'],
                'allow_inheritance': False,
            }

        Customer.drop_collection()
        cust = Customer(cust_id=1)
        cust.save()

        cust_dupe = Customer(cust_id=1)
        try:
            cust_dupe.save()
            raise AssertionError("We saved a dupe!")
        except NotUniqueError:
            pass
        Customer.drop_collection()

    def test_unique_and_primary(self):
        """If you set a field as primary, then unexpected behaviour can occur.
        You won't create a duplicate but you will update an existing document.
        """

        class User(Document):
            name = StringField(primary_key=True, unique=True)
            password = StringField()

        User.drop_collection()

        user = User(name='huangz', password='secret')
        user.save()

        user = User(name='huangz', password='secret2')
        user.save()

        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(User.objects.get().password, 'secret2')

        User.drop_collection()

    def test_index_with_pk(self):
        """Ensure you can use `pk` as part of a query"""

        class Comment(EmbeddedDocument):
            comment_id = IntField(required=True)

        try:
            class BlogPost(Document):
                comments = EmbeddedDocumentField(Comment)
                meta = {'indexes': [
                            {'fields': ['pk', 'comments.comment_id'],
                             'unique': True}]}
        except UnboundLocalError:
            self.fail('Unbound local error at index + pk definition')

        info = BlogPost.objects._collection.index_information()
        info = [value['key'] for key, value in info.iteritems()]
        index_item = [('_id', 1), ('comments.comment_id', 1)]
        self.assertTrue(index_item in info)

    def test_compound_key_embedded(self):

        class CompoundKey(EmbeddedDocument):
            name = StringField(required=True)
            term = StringField(required=True)

        class Report(Document):
            key = EmbeddedDocumentField(CompoundKey, primary_key=True)
            text = StringField()

        Report.drop_collection()

        my_key = CompoundKey(name="n", term="ok")
        report = Report(text="OK", key=my_key).save()

        self.assertEqual({'text': 'OK', '_id': {'term': 'ok', 'name': 'n'}},
                         report.to_mongo())
        self.assertEqual(report, Report.objects.get(pk=my_key))

    def test_compound_key_dictfield(self):

        class Report(Document):
            key = DictField(primary_key=True)
            text = StringField()

        Report.drop_collection()

        my_key = {"name": "n", "term": "ok"}
        report = Report(text="OK", key=my_key).save()

        self.assertEqual({'text': 'OK', '_id': {'term': 'ok', 'name': 'n'}},
                         report.to_mongo())
        self.assertEqual(report, Report.objects.get(pk=my_key))

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = inheritance
# -*- coding: utf-8 -*-
import sys
sys.path[0:0] = [""]
import unittest
import warnings

from datetime import datetime

from tests.fixtures import Base

from mongoengine import Document, EmbeddedDocument, connect
from mongoengine.connection import get_db
from mongoengine.fields import (BooleanField, GenericReferenceField,
                                IntField, StringField)

__all__ = ('InheritanceTest', )


class InheritanceTest(unittest.TestCase):

    def setUp(self):
        connect(db='mongoenginetest')
        self.db = get_db()

    def tearDown(self):
        for collection in self.db.collection_names():
            if 'system.' in collection:
                continue
            self.db.drop_collection(collection)

    def test_superclasses(self):
        """Ensure that the correct list of superclasses is assembled.
        """
        class Animal(Document):
            meta = {'allow_inheritance': True}
        class Fish(Animal): pass
        class Guppy(Fish): pass
        class Mammal(Animal): pass
        class Dog(Mammal): pass
        class Human(Mammal): pass

        self.assertEqual(Animal._superclasses, ())
        self.assertEqual(Fish._superclasses, ('Animal',))
        self.assertEqual(Guppy._superclasses, ('Animal', 'Animal.Fish'))
        self.assertEqual(Mammal._superclasses, ('Animal',))
        self.assertEqual(Dog._superclasses, ('Animal', 'Animal.Mammal'))
        self.assertEqual(Human._superclasses, ('Animal', 'Animal.Mammal'))

    def test_external_superclasses(self):
        """Ensure that the correct list of super classes is assembled when
        importing part of the model.
        """
        class Animal(Base): pass
        class Fish(Animal): pass
        class Guppy(Fish): pass
        class Mammal(Animal): pass
        class Dog(Mammal): pass
        class Human(Mammal): pass

        self.assertEqual(Animal._superclasses, ('Base', ))
        self.assertEqual(Fish._superclasses, ('Base', 'Base.Animal',))
        self.assertEqual(Guppy._superclasses, ('Base', 'Base.Animal',
                                               'Base.Animal.Fish'))
        self.assertEqual(Mammal._superclasses, ('Base', 'Base.Animal',))
        self.assertEqual(Dog._superclasses, ('Base', 'Base.Animal',
                                             'Base.Animal.Mammal'))
        self.assertEqual(Human._superclasses, ('Base', 'Base.Animal',
                                               'Base.Animal.Mammal'))

    def test_subclasses(self):
        """Ensure that the correct list of _subclasses (subclasses) is
        assembled.
        """
        class Animal(Document):
            meta = {'allow_inheritance': True}
        class Fish(Animal): pass
        class Guppy(Fish): pass
        class Mammal(Animal): pass
        class Dog(Mammal): pass
        class Human(Mammal): pass

        self.assertEqual(Animal._subclasses, ('Animal',
                                         'Animal.Fish',
                                         'Animal.Fish.Guppy',
                                         'Animal.Mammal',
                                         'Animal.Mammal.Dog',
                                         'Animal.Mammal.Human'))
        self.assertEqual(Fish._subclasses, ('Animal.Fish',
                                       'Animal.Fish.Guppy',))
        self.assertEqual(Guppy._subclasses, ('Animal.Fish.Guppy',))
        self.assertEqual(Mammal._subclasses, ('Animal.Mammal',
                                         'Animal.Mammal.Dog',
                                         'Animal.Mammal.Human'))
        self.assertEqual(Human._subclasses, ('Animal.Mammal.Human',))

    def test_external_subclasses(self):
        """Ensure that the correct list of _subclasses (subclasses) is
        assembled when importing part of the model.
        """
        class Animal(Base): pass
        class Fish(Animal): pass
        class Guppy(Fish): pass
        class Mammal(Animal): pass
        class Dog(Mammal): pass
        class Human(Mammal): pass

        self.assertEqual(Animal._subclasses, ('Base.Animal',
                                              'Base.Animal.Fish',
                                              'Base.Animal.Fish.Guppy',
                                              'Base.Animal.Mammal',
                                              'Base.Animal.Mammal.Dog',
                                              'Base.Animal.Mammal.Human'))
        self.assertEqual(Fish._subclasses, ('Base.Animal.Fish',
                                            'Base.Animal.Fish.Guppy',))
        self.assertEqual(Guppy._subclasses, ('Base.Animal.Fish.Guppy',))
        self.assertEqual(Mammal._subclasses, ('Base.Animal.Mammal',
                                              'Base.Animal.Mammal.Dog',
                                              'Base.Animal.Mammal.Human'))
        self.assertEqual(Human._subclasses, ('Base.Animal.Mammal.Human',))

    def test_dynamic_declarations(self):
        """Test that declaring an extra class updates meta data"""

        class Animal(Document):
            meta = {'allow_inheritance': True}

        self.assertEqual(Animal._superclasses, ())
        self.assertEqual(Animal._subclasses, ('Animal',))

        # Test dynamically adding a class changes the meta data
        class Fish(Animal):
            pass

        self.assertEqual(Animal._superclasses, ())
        self.assertEqual(Animal._subclasses, ('Animal', 'Animal.Fish'))

        self.assertEqual(Fish._superclasses, ('Animal', ))
        self.assertEqual(Fish._subclasses, ('Animal.Fish',))

        # Test dynamically adding an inherited class changes the meta data
        class Pike(Fish):
            pass

        self.assertEqual(Animal._superclasses, ())
        self.assertEqual(Animal._subclasses, ('Animal', 'Animal.Fish',
                                              'Animal.Fish.Pike'))

        self.assertEqual(Fish._superclasses, ('Animal', ))
        self.assertEqual(Fish._subclasses, ('Animal.Fish', 'Animal.Fish.Pike'))

        self.assertEqual(Pike._superclasses, ('Animal', 'Animal.Fish'))
        self.assertEqual(Pike._subclasses, ('Animal.Fish.Pike',))

    def test_inheritance_meta_data(self):
        """Ensure that document may inherit fields from a superclass document.
        """
        class Person(Document):
            name = StringField()
            age = IntField()

            meta = {'allow_inheritance': True}

        class Employee(Person):
            salary = IntField()

        self.assertEqual(['age', 'id', 'name', 'salary'],
                         sorted(Employee._fields.keys()))
        self.assertEqual(Employee._get_collection_name(),
                         Person._get_collection_name())

    def test_inheritance_to_mongo_keys(self):
        """Ensure that document may inherit fields from a superclass document.
        """
        class Person(Document):
            name = StringField()
            age = IntField()

            meta = {'allow_inheritance': True}

        class Employee(Person):
            salary = IntField()

        self.assertEqual(['age', 'id', 'name', 'salary'],
                         sorted(Employee._fields.keys()))
        self.assertEqual(Person(name="Bob", age=35).to_mongo().keys(),
                         ['_cls', 'name', 'age'])
        self.assertEqual(Employee(name="Bob", age=35, salary=0).to_mongo().keys(),
                         ['_cls', 'name', 'age', 'salary'])
        self.assertEqual(Employee._get_collection_name(),
                         Person._get_collection_name())

    def test_indexes_and_multiple_inheritance(self):
        """ Ensure that all of the indexes are created for a document with
        multiple inheritance.
        """

        class A(Document):
            a = StringField()

            meta = {
                'allow_inheritance': True,
                'indexes': ['a']
            }

        class B(Document):
            b = StringField()

            meta = {
                'allow_inheritance': True,
                'indexes': ['b']
            }

        class C(A, B):
            pass

        A.drop_collection()
        B.drop_collection()
        C.drop_collection()

        C.ensure_indexes()

        self.assertEqual(
            sorted([idx['key'] for idx in C._get_collection().index_information().values()]),
            sorted([[(u'_cls', 1), (u'b', 1)], [(u'_id', 1)], [(u'_cls', 1), (u'a', 1)]])
        )

    def test_polymorphic_queries(self):
        """Ensure that the correct subclasses are returned from a query
        """

        class Animal(Document):
            meta = {'allow_inheritance': True}
        class Fish(Animal): pass
        class Mammal(Animal): pass
        class Dog(Mammal): pass
        class Human(Mammal): pass

        Animal.drop_collection()

        Animal().save()
        Fish().save()
        Mammal().save()
        Dog().save()
        Human().save()

        classes = [obj.__class__ for obj in Animal.objects]
        self.assertEqual(classes, [Animal, Fish, Mammal, Dog, Human])

        classes = [obj.__class__ for obj in Mammal.objects]
        self.assertEqual(classes, [Mammal, Dog, Human])

        classes = [obj.__class__ for obj in Human.objects]
        self.assertEqual(classes, [Human])

    def test_allow_inheritance(self):
        """Ensure that inheritance may be disabled on simple classes and that
        _cls and _subclasses will not be used.
        """

        class Animal(Document):
            name = StringField()

        def create_dog_class():
            class Dog(Animal):
                pass

        self.assertRaises(ValueError, create_dog_class)

        # Check that _cls etc aren't present on simple documents
        dog = Animal(name='dog').save()
        self.assertEqual(dog.to_mongo().keys(), ['_id', 'name'])

        collection = self.db[Animal._get_collection_name()]
        obj = collection.find_one()
        self.assertFalse('_cls' in obj)

    def test_cant_turn_off_inheritance_on_subclass(self):
        """Ensure if inheritance is on in a subclass you cant turn it off
        """

        class Animal(Document):
            name = StringField()
            meta = {'allow_inheritance': True}

        def create_mammal_class():
            class Mammal(Animal):
                meta = {'allow_inheritance': False}
        self.assertRaises(ValueError, create_mammal_class)

    def test_allow_inheritance_abstract_document(self):
        """Ensure that abstract documents can set inheritance rules and that
        _cls will not be used.
        """
        class FinalDocument(Document):
            meta = {'abstract': True,
                    'allow_inheritance': False}

        class Animal(FinalDocument):
            name = StringField()

        def create_mammal_class():
            class Mammal(Animal):
                pass
        self.assertRaises(ValueError, create_mammal_class)

        # Check that _cls isn't present in simple documents
        doc = Animal(name='dog')
        self.assertFalse('_cls' in doc.to_mongo())

    def test_allow_inheritance_embedded_document(self):
        """Ensure embedded documents respect inheritance
        """

        class Comment(EmbeddedDocument):
            content = StringField()

        def create_special_comment():
            class SpecialComment(Comment):
                pass

        self.assertRaises(ValueError, create_special_comment)

        doc = Comment(content='test')
        self.assertFalse('_cls' in doc.to_mongo())

        class Comment(EmbeddedDocument):
            content = StringField()
            meta = {'allow_inheritance': True}

        doc = Comment(content='test')
        self.assertTrue('_cls' in doc.to_mongo())

    def test_document_inheritance(self):
        """Ensure mutliple inheritance of abstract documents
        """
        class DateCreatedDocument(Document):
            meta = {
                'allow_inheritance': True,
                'abstract': True,
            }

        class DateUpdatedDocument(Document):
            meta = {
                'allow_inheritance': True,
                'abstract': True,
            }

        try:
            class MyDocument(DateCreatedDocument, DateUpdatedDocument):
                pass
        except:
            self.assertTrue(False, "Couldn't create MyDocument class")

    def test_abstract_documents(self):
        """Ensure that a document superclass can be marked as abstract
        thereby not using it as the name for the collection."""

        defaults = {'index_background': True,
                    'index_drop_dups': True,
                    'index_opts': {'hello': 'world'},
                    'allow_inheritance': True,
                    'queryset_class': 'QuerySet',
                    'db_alias': 'myDB',
                    'shard_key': ('hello', 'world')}

        meta_settings = {'abstract': True}
        meta_settings.update(defaults)

        class Animal(Document):
            name = StringField()
            meta = meta_settings

        class Fish(Animal): pass
        class Guppy(Fish): pass

        class Mammal(Animal):
            meta = {'abstract': True}
        class Human(Mammal): pass

        for k, v in defaults.iteritems():
            for cls in [Animal, Fish, Guppy]:
                self.assertEqual(cls._meta[k], v)

        self.assertFalse('collection' in Animal._meta)
        self.assertFalse('collection' in Mammal._meta)

        self.assertEqual(Animal._get_collection_name(), None)
        self.assertEqual(Mammal._get_collection_name(), None)

        self.assertEqual(Fish._get_collection_name(), 'fish')
        self.assertEqual(Guppy._get_collection_name(), 'fish')
        self.assertEqual(Human._get_collection_name(), 'human')

        def create_bad_abstract():
            class EvilHuman(Human):
                evil = BooleanField(default=True)
                meta = {'abstract': True}
        self.assertRaises(ValueError, create_bad_abstract)

    def test_inherited_collections(self):
        """Ensure that subclassed documents don't override parents'
        collections
        """

        class Drink(Document):
            name = StringField()
            meta = {'allow_inheritance': True}

        class Drinker(Document):
            drink = GenericReferenceField()

        try:
            warnings.simplefilter("error")

            class AcloholicDrink(Drink):
                meta = {'collection': 'booze'}

        except SyntaxWarning:
            warnings.simplefilter("ignore")

            class AlcoholicDrink(Drink):
                meta = {'collection': 'booze'}

        else:
            raise AssertionError("SyntaxWarning should be triggered")

        warnings.resetwarnings()

        Drink.drop_collection()
        AlcoholicDrink.drop_collection()
        Drinker.drop_collection()

        red_bull = Drink(name='Red Bull')
        red_bull.save()

        programmer = Drinker(drink=red_bull)
        programmer.save()

        beer = AlcoholicDrink(name='Beer')
        beer.save()
        real_person = Drinker(drink=beer)
        real_person.save()

        self.assertEqual(Drinker.objects[0].drink.name, red_bull.name)
        self.assertEqual(Drinker.objects[1].drink.name, beer.name)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = instance
# -*- coding: utf-8 -*-
import sys
sys.path[0:0] = [""]

import bson
import os
import pickle
import unittest
import uuid

from datetime import datetime
from bson import DBRef
from tests.fixtures import (PickleEmbedded, PickleTest, PickleSignalsTest,
                            PickleDyanmicEmbedded, PickleDynamicTest)

from mongoengine import *
from mongoengine.errors import (NotRegistered, InvalidDocumentError,
                                InvalidQueryError)
from mongoengine.queryset import NULLIFY, Q
from mongoengine.connection import get_db
from mongoengine.base import get_document
from mongoengine.context_managers import switch_db, query_counter
from mongoengine import signals

TEST_IMAGE_PATH = os.path.join(os.path.dirname(__file__),
                               '../fields/mongoengine.png')

__all__ = ("InstanceTest",)


class InstanceTest(unittest.TestCase):

    def setUp(self):
        connect(db='mongoenginetest')
        self.db = get_db()

        class Person(Document):
            name = StringField()
            age = IntField()

            non_field = True

            meta = {"allow_inheritance": True}

        self.Person = Person

    def tearDown(self):
        for collection in self.db.collection_names():
            if 'system.' in collection:
                continue
            self.db.drop_collection(collection)

    def test_capped_collection(self):
        """Ensure that capped collections work properly.
        """
        class Log(Document):
            date = DateTimeField(default=datetime.now)
            meta = {
                'max_documents': 10,
                'max_size': 90000,
            }

        Log.drop_collection()

        # Ensure that the collection handles up to its maximum
        for _ in range(10):
            Log().save()

        self.assertEqual(Log.objects.count(), 10)

        # Check that extra documents don't increase the size
        Log().save()
        self.assertEqual(Log.objects.count(), 10)

        options = Log.objects._collection.options()
        self.assertEqual(options['capped'], True)
        self.assertEqual(options['max'], 10)
        self.assertEqual(options['size'], 90000)

        # Check that the document cannot be redefined with different options
        def recreate_log_document():
            class Log(Document):
                date = DateTimeField(default=datetime.now)
                meta = {
                    'max_documents': 11,
                }
            # Create the collection by accessing Document.objects
            Log.objects
        self.assertRaises(InvalidCollectionError, recreate_log_document)

        Log.drop_collection()

    def test_repr(self):
        """Ensure that unicode representation works
        """
        class Article(Document):
            title = StringField()

            def __unicode__(self):
                return self.title

        doc = Article(title=u'привет мир')

        self.assertEqual('<Article: привет мир>', repr(doc))

    def test_queryset_resurrects_dropped_collection(self):
        self.Person.drop_collection()

        self.assertEqual([], list(self.Person.objects()))

        class Actor(self.Person):
            pass

        # Ensure works correctly with inhertited classes
        Actor.objects()
        self.Person.drop_collection()
        self.assertEqual([], list(Actor.objects()))

    def test_polymorphic_references(self):
        """Ensure that the correct subclasses are returned from a query when
        using references / generic references
        """
        class Animal(Document):
            meta = {'allow_inheritance': True}
        class Fish(Animal): pass
        class Mammal(Animal): pass
        class Dog(Mammal): pass
        class Human(Mammal): pass

        class Zoo(Document):
            animals = ListField(ReferenceField(Animal))

        Zoo.drop_collection()
        Animal.drop_collection()

        Animal().save()
        Fish().save()
        Mammal().save()
        Dog().save()
        Human().save()

        # Save a reference to each animal
        zoo = Zoo(animals=Animal.objects)
        zoo.save()
        zoo.reload()

        classes = [a.__class__ for a in Zoo.objects.first().animals]
        self.assertEqual(classes, [Animal, Fish, Mammal, Dog, Human])

        Zoo.drop_collection()

        class Zoo(Document):
            animals = ListField(GenericReferenceField(Animal))

        # Save a reference to each animal
        zoo = Zoo(animals=Animal.objects)
        zoo.save()
        zoo.reload()

        classes = [a.__class__ for a in Zoo.objects.first().animals]
        self.assertEqual(classes, [Animal, Fish, Mammal, Dog, Human])

        Zoo.drop_collection()
        Animal.drop_collection()

    def test_reference_inheritance(self):
        class Stats(Document):
            created = DateTimeField(default=datetime.now)

            meta = {'allow_inheritance': False}

        class CompareStats(Document):
            generated = DateTimeField(default=datetime.now)
            stats = ListField(ReferenceField(Stats))

        Stats.drop_collection()
        CompareStats.drop_collection()

        list_stats = []

        for i in xrange(10):
            s = Stats()
            s.save()
            list_stats.append(s)

        cmp_stats = CompareStats(stats=list_stats)
        cmp_stats.save()

        self.assertEqual(list_stats, CompareStats.objects.first().stats)

    def test_db_field_load(self):
        """Ensure we load data correctly
        """
        class Person(Document):
            name = StringField(required=True)
            _rank = StringField(required=False, db_field="rank")

            @property
            def rank(self):
                return self._rank or "Private"

        Person.drop_collection()

        Person(name="Jack", _rank="Corporal").save()

        Person(name="Fred").save()

        self.assertEqual(Person.objects.get(name="Jack").rank, "Corporal")
        self.assertEqual(Person.objects.get(name="Fred").rank, "Private")

    def test_db_embedded_doc_field_load(self):
        """Ensure we load embedded document data correctly
        """
        class Rank(EmbeddedDocument):
            title = StringField(required=True)

        class Person(Document):
            name = StringField(required=True)
            rank_ = EmbeddedDocumentField(Rank,
                                          required=False,
                                          db_field='rank')

            @property
            def rank(self):
                if self.rank_ is None:
                    return "Private"
                return self.rank_.title

        Person.drop_collection()

        Person(name="Jack", rank_=Rank(title="Corporal")).save()
        Person(name="Fred").save()

        self.assertEqual(Person.objects.get(name="Jack").rank, "Corporal")
        self.assertEqual(Person.objects.get(name="Fred").rank, "Private")

    def test_custom_id_field(self):
        """Ensure that documents may be created with custom primary keys.
        """
        class User(Document):
            username = StringField(primary_key=True)
            name = StringField()

            meta = {'allow_inheritance': True}

        User.drop_collection()

        self.assertEqual(User._fields['username'].db_field, '_id')
        self.assertEqual(User._meta['id_field'], 'username')

        def create_invalid_user():
            User(name='test').save()  # no primary key field
        self.assertRaises(ValidationError, create_invalid_user)

        def define_invalid_user():
            class EmailUser(User):
                email = StringField(primary_key=True)
        self.assertRaises(ValueError, define_invalid_user)

        class EmailUser(User):
            email = StringField()

        user = User(username='test', name='test user')
        user.save()

        user_obj = User.objects.first()
        self.assertEqual(user_obj.id, 'test')
        self.assertEqual(user_obj.pk, 'test')

        user_son = User.objects._collection.find_one()
        self.assertEqual(user_son['_id'], 'test')
        self.assertTrue('username' not in user_son['_id'])

        User.drop_collection()

        user = User(pk='mongo', name='mongo user')
        user.save()

        user_obj = User.objects.first()
        self.assertEqual(user_obj.id, 'mongo')
        self.assertEqual(user_obj.pk, 'mongo')

        user_son = User.objects._collection.find_one()
        self.assertEqual(user_son['_id'], 'mongo')
        self.assertTrue('username' not in user_son['_id'])

        User.drop_collection()

    def test_document_not_registered(self):

        class Place(Document):
            name = StringField()

            meta = {'allow_inheritance': True}

        class NicePlace(Place):
            pass

        Place.drop_collection()

        Place(name="London").save()
        NicePlace(name="Buckingham Palace").save()

        # Mimic Place and NicePlace definitions being in a different file
        # and the NicePlace model not being imported in at query time.
        from mongoengine.base import _document_registry
        del(_document_registry['Place.NicePlace'])

        def query_without_importing_nice_place():
            print Place.objects.all()
        self.assertRaises(NotRegistered, query_without_importing_nice_place)

    def test_document_registry_regressions(self):

        class Location(Document):
            name = StringField()
            meta = {'allow_inheritance': True}

        class Area(Location):
            location = ReferenceField('Location', dbref=True)

        Location.drop_collection()

        self.assertEqual(Area, get_document("Area"))
        self.assertEqual(Area, get_document("Location.Area"))

    def test_creation(self):
        """Ensure that document may be created using keyword arguments.
        """
        person = self.Person(name="Test User", age=30)
        self.assertEqual(person.name, "Test User")
        self.assertEqual(person.age, 30)

    def test_to_dbref(self):
        """Ensure that you can get a dbref of a document"""
        person = self.Person(name="Test User", age=30)
        self.assertRaises(OperationError, person.to_dbref)
        person.save()

        person.to_dbref()

    def test_reload(self):
        """Ensure that attributes may be reloaded.
        """
        person = self.Person(name="Test User", age=20)
        person.save()

        person_obj = self.Person.objects.first()
        person_obj.name = "Mr Test User"
        person_obj.age = 21
        person_obj.save()

        self.assertEqual(person.name, "Test User")
        self.assertEqual(person.age, 20)

        person.reload()
        self.assertEqual(person.name, "Mr Test User")
        self.assertEqual(person.age, 21)

    def test_reload_sharded(self):
        class Animal(Document):
            superphylum = StringField()
            meta = {'shard_key': ('superphylum',)}

        Animal.drop_collection()
        doc = Animal(superphylum='Deuterostomia')
        doc.save()
        doc.reload()
        Animal.drop_collection()

    def test_reload_referencing(self):
        """Ensures reloading updates weakrefs correctly
        """
        class Embedded(EmbeddedDocument):
            dict_field = DictField()
            list_field = ListField()

        class Doc(Document):
            dict_field = DictField()
            list_field = ListField()
            embedded_field = EmbeddedDocumentField(Embedded)

        Doc.drop_collection()
        doc = Doc()
        doc.dict_field = {'hello': 'world'}
        doc.list_field = ['1', 2, {'hello': 'world'}]

        embedded_1 = Embedded()
        embedded_1.dict_field = {'hello': 'world'}
        embedded_1.list_field = ['1', 2, {'hello': 'world'}]
        doc.embedded_field = embedded_1
        doc.save()

        doc = doc.reload(10)
        doc.list_field.append(1)
        doc.dict_field['woot'] = "woot"
        doc.embedded_field.list_field.append(1)
        doc.embedded_field.dict_field['woot'] = "woot"

        self.assertEqual(doc._get_changed_fields(), [
            'list_field', 'dict_field', 'embedded_field.list_field',
            'embedded_field.dict_field'])
        doc.save()

        doc = doc.reload(10)
        self.assertEqual(doc._get_changed_fields(), [])
        self.assertEqual(len(doc.list_field), 4)
        self.assertEqual(len(doc.dict_field), 2)
        self.assertEqual(len(doc.embedded_field.list_field), 4)
        self.assertEqual(len(doc.embedded_field.dict_field), 2)

    def test_reload_doesnt_exist(self):
        class Foo(Document):
            pass

        f = Foo()
        try:
            f.reload()
        except Foo.DoesNotExist:
            pass
        except Exception as ex:
            self.assertFalse("Threw wrong exception")

        f.save()
        f.delete()
        try:
            f.reload()
        except Foo.DoesNotExist:
            pass
        except Exception as ex:
            self.assertFalse("Threw wrong exception")

    def test_dictionary_access(self):
        """Ensure that dictionary-style field access works properly.
        """
        person = self.Person(name='Test User', age=30)
        self.assertEqual(person['name'], 'Test User')

        self.assertRaises(KeyError, person.__getitem__, 'salary')
        self.assertRaises(KeyError, person.__setitem__, 'salary', 50)

        person['name'] = 'Another User'
        self.assertEqual(person['name'], 'Another User')

        # Length = length(assigned fields + id)
        self.assertEqual(len(person), 3)

        self.assertTrue('age' in person)
        person.age = None
        self.assertFalse('age' in person)
        self.assertFalse('nationality' in person)

    def test_embedded_document_to_mongo(self):
        class Person(EmbeddedDocument):
            name = StringField()
            age = IntField()

            meta = {"allow_inheritance": True}

        class Employee(Person):
            salary = IntField()

        self.assertEqual(Person(name="Bob", age=35).to_mongo().keys(),
                         ['_cls', 'name', 'age'])
        self.assertEqual(Employee(name="Bob", age=35, salary=0).to_mongo().keys(),
                         ['_cls', 'name', 'age', 'salary'])

    def test_embedded_document_to_mongo_id(self):
        class SubDoc(EmbeddedDocument):
            id = StringField(required=True)

        sub_doc = SubDoc(id="abc")
        self.assertEqual(sub_doc.to_mongo().keys(), ['id'])

    def test_embedded_document(self):
        """Ensure that embedded documents are set up correctly.
        """
        class Comment(EmbeddedDocument):
            content = StringField()

        self.assertTrue('content' in Comment._fields)
        self.assertFalse('id' in Comment._fields)

    def test_embedded_document_instance(self):
        """Ensure that embedded documents can reference parent instance
        """
        class Embedded(EmbeddedDocument):
            string = StringField()

        class Doc(Document):
            embedded_field = EmbeddedDocumentField(Embedded)

        Doc.drop_collection()
        Doc(embedded_field=Embedded(string="Hi")).save()

        doc = Doc.objects.get()
        self.assertEqual(doc, doc.embedded_field._instance)

    def test_embedded_document_complex_instance(self):
        """Ensure that embedded documents in complex fields can reference
        parent instance"""
        class Embedded(EmbeddedDocument):
            string = StringField()

        class Doc(Document):
            embedded_field = ListField(EmbeddedDocumentField(Embedded))

        Doc.drop_collection()
        Doc(embedded_field=[Embedded(string="Hi")]).save()

        doc = Doc.objects.get()
        self.assertEqual(doc, doc.embedded_field[0]._instance)

    def test_instance_is_set_on_setattr(self):

        class Email(EmbeddedDocument):
            email = EmailField()
            def clean(self):
                print "instance:"
                print self._instance

        class Account(Document):
            email = EmbeddedDocumentField(Email)

        Account.drop_collection()
        acc = Account()
        acc.email = Email(email='test@example.com')
        self.assertTrue(hasattr(acc._data["email"], "_instance"))
        acc.save()

        acc1 = Account.objects.first()
        self.assertTrue(hasattr(acc1._data["email"], "_instance"))

    def test_document_clean(self):
        class TestDocument(Document):
            status = StringField()
            pub_date = DateTimeField()

            def clean(self):
                if self.status == 'draft' and self.pub_date is not None:
                    msg = 'Draft entries may not have a publication date.'
                    raise ValidationError(msg)
                # Set the pub_date for published items if not set.
                if self.status == 'published' and self.pub_date is None:
                    self.pub_date = datetime.now()

        TestDocument.drop_collection()

        t = TestDocument(status="draft", pub_date=datetime.now())

        try:
            t.save()
        except ValidationError, e:
            expect_msg = "Draft entries may not have a publication date."
            self.assertTrue(expect_msg in e.message)
            self.assertEqual(e.to_dict(), {'__all__': expect_msg})

        t = TestDocument(status="published")
        t.save(clean=False)

        self.assertEqual(t.pub_date, None)

        t = TestDocument(status="published")
        t.save(clean=True)

        self.assertEqual(type(t.pub_date), datetime)

    def test_document_embedded_clean(self):
        class TestEmbeddedDocument(EmbeddedDocument):
            x = IntField(required=True)
            y = IntField(required=True)
            z = IntField(required=True)

            meta = {'allow_inheritance': False}

            def clean(self):
                if self.z:
                    if self.z != self.x + self.y:
                        raise ValidationError('Value of z != x + y')
                else:
                    self.z = self.x + self.y

        class TestDocument(Document):
            doc = EmbeddedDocumentField(TestEmbeddedDocument)
            status = StringField()

        TestDocument.drop_collection()

        t = TestDocument(doc=TestEmbeddedDocument(x=10, y=25, z=15))
        try:
            t.save()
        except ValidationError, e:
            expect_msg = "Value of z != x + y"
            self.assertTrue(expect_msg in e.message)
            self.assertEqual(e.to_dict(), {'doc': {'__all__': expect_msg}})

        t = TestDocument(doc=TestEmbeddedDocument(x=10, y=25)).save()
        self.assertEqual(t.doc.z, 35)

        # Asserts not raises
        t = TestDocument(doc=TestEmbeddedDocument(x=15, y=35, z=5))
        t.save(clean=False)

    def test_save(self):
        """Ensure that a document may be saved in the database.
        """
        # Create person object and save it to the database
        person = self.Person(name='Test User', age=30)
        person.save()
        # Ensure that the object is in the database
        collection = self.db[self.Person._get_collection_name()]
        person_obj = collection.find_one({'name': 'Test User'})
        self.assertEqual(person_obj['name'], 'Test User')
        self.assertEqual(person_obj['age'], 30)
        self.assertEqual(person_obj['_id'], person.id)
        # Test skipping validation on save

        class Recipient(Document):
            email = EmailField(required=True)

        recipient = Recipient(email='root@localhost')
        self.assertRaises(ValidationError, recipient.save)

        try:
            recipient.save(validate=False)
        except ValidationError:
            self.fail()

    def test_save_to_a_value_that_equates_to_false(self):

        class Thing(EmbeddedDocument):
            count = IntField()

        class User(Document):
            thing = EmbeddedDocumentField(Thing)

        User.drop_collection()

        user = User(thing=Thing(count=1))
        user.save()
        user.reload()

        user.thing.count = 0
        user.save()

        user.reload()
        self.assertEqual(user.thing.count, 0)

    def test_save_max_recursion_not_hit(self):

        class Person(Document):
            name = StringField()
            parent = ReferenceField('self')
            friend = ReferenceField('self')

        Person.drop_collection()

        p1 = Person(name="Wilson Snr")
        p1.parent = None
        p1.save()

        p2 = Person(name="Wilson Jr")
        p2.parent = p1
        p2.save()

        p1.friend = p2
        p1.save()

        # Confirm can save and it resets the changed fields without hitting
        # max recursion error
        p0 = Person.objects.first()
        p0.name = 'wpjunior'
        p0.save()

    def test_save_max_recursion_not_hit_with_file_field(self):

        class Foo(Document):
            name = StringField()
            picture = FileField()
            bar = ReferenceField('self')

        Foo.drop_collection()

        a = Foo(name='hello').save()

        a.bar = a
        with open(TEST_IMAGE_PATH, 'rb') as test_image:
            a.picture = test_image
            a.save()

            # Confirm can save and it resets the changed fields without hitting
            # max recursion error
            b = Foo.objects.with_id(a.id)
            b.name = 'world'
            b.save()

            self.assertEqual(b.picture, b.bar.picture, b.bar.bar.picture)

    def test_save_cascades(self):

        class Person(Document):
            name = StringField()
            parent = ReferenceField('self')

        Person.drop_collection()

        p1 = Person(name="Wilson Snr")
        p1.parent = None
        p1.save()

        p2 = Person(name="Wilson Jr")
        p2.parent = p1
        p2.save()

        p = Person.objects(name="Wilson Jr").get()
        p.parent.name = "Daddy Wilson"
        p.save(cascade=True)

        p1.reload()
        self.assertEqual(p1.name, p.parent.name)

    def test_save_cascade_kwargs(self):

        class Person(Document):
            name = StringField()
            parent = ReferenceField('self')

        Person.drop_collection()

        p1 = Person(name="Wilson Snr")
        p1.parent = None
        p1.save()

        p2 = Person(name="Wilson Jr")
        p2.parent = p1
        p1.name = "Daddy Wilson"
        p2.save(force_insert=True, cascade_kwargs={"force_insert": False})

        p1.reload()
        p2.reload()
        self.assertEqual(p1.name, p2.parent.name)

    def test_save_cascade_meta_false(self):

        class Person(Document):
            name = StringField()
            parent = ReferenceField('self')

            meta = {'cascade': False}

        Person.drop_collection()

        p1 = Person(name="Wilson Snr")
        p1.parent = None
        p1.save()

        p2 = Person(name="Wilson Jr")
        p2.parent = p1
        p2.save()

        p = Person.objects(name="Wilson Jr").get()
        p.parent.name = "Daddy Wilson"
        p.save()

        p1.reload()
        self.assertNotEqual(p1.name, p.parent.name)

        p.save(cascade=True)
        p1.reload()
        self.assertEqual(p1.name, p.parent.name)

    def test_save_cascade_meta_true(self):

        class Person(Document):
            name = StringField()
            parent = ReferenceField('self')

            meta = {'cascade': False}

        Person.drop_collection()

        p1 = Person(name="Wilson Snr")
        p1.parent = None
        p1.save()

        p2 = Person(name="Wilson Jr")
        p2.parent = p1
        p2.save(cascade=True)

        p = Person.objects(name="Wilson Jr").get()
        p.parent.name = "Daddy Wilson"
        p.save()

        p1.reload()
        self.assertNotEqual(p1.name, p.parent.name)

    def test_save_cascades_generically(self):

        class Person(Document):
            name = StringField()
            parent = GenericReferenceField()

        Person.drop_collection()

        p1 = Person(name="Wilson Snr")
        p1.save()

        p2 = Person(name="Wilson Jr")
        p2.parent = p1
        p2.save()

        p = Person.objects(name="Wilson Jr").get()
        p.parent.name = "Daddy Wilson"
        p.save()

        p1.reload()
        self.assertNotEqual(p1.name, p.parent.name)

        p.save(cascade=True)
        p1.reload()
        self.assertEqual(p1.name, p.parent.name)

    def test_update(self):
        """Ensure that an existing document is updated instead of be
        overwritten."""
        # Create person object and save it to the database
        person = self.Person(name='Test User', age=30)
        person.save()

        # Create same person object, with same id, without age
        same_person = self.Person(name='Test')
        same_person.id = person.id
        same_person.save()

        # Confirm only one object
        self.assertEqual(self.Person.objects.count(), 1)

        # reload
        person.reload()
        same_person.reload()

        # Confirm the same
        self.assertEqual(person, same_person)
        self.assertEqual(person.name, same_person.name)
        self.assertEqual(person.age, same_person.age)

        # Confirm the saved values
        self.assertEqual(person.name, 'Test')
        self.assertEqual(person.age, 30)

        # Test only / exclude only updates included fields
        person = self.Person.objects.only('name').get()
        person.name = 'User'
        person.save()

        person.reload()
        self.assertEqual(person.name, 'User')
        self.assertEqual(person.age, 30)

        # test exclude only updates set fields
        person = self.Person.objects.exclude('name').get()
        person.age = 21
        person.save()

        person.reload()
        self.assertEqual(person.name, 'User')
        self.assertEqual(person.age, 21)

        # Test only / exclude can set non excluded / included fields
        person = self.Person.objects.only('name').get()
        person.name = 'Test'
        person.age = 30
        person.save()

        person.reload()
        self.assertEqual(person.name, 'Test')
        self.assertEqual(person.age, 30)

        # test exclude only updates set fields
        person = self.Person.objects.exclude('name').get()
        person.name = 'User'
        person.age = 21
        person.save()

        person.reload()
        self.assertEqual(person.name, 'User')
        self.assertEqual(person.age, 21)

        # Confirm does remove unrequired fields
        person = self.Person.objects.exclude('name').get()
        person.age = None
        person.save()

        person.reload()
        self.assertEqual(person.name, 'User')
        self.assertEqual(person.age, None)

        person = self.Person.objects.get()
        person.name = None
        person.age = None
        person.save()

        person.reload()
        self.assertEqual(person.name, None)
        self.assertEqual(person.age, None)

    def test_inserts_if_you_set_the_pk(self):
        p1 = self.Person(name='p1', id=bson.ObjectId()).save()
        p2 = self.Person(name='p2')
        p2.id = bson.ObjectId()
        p2.save()

        self.assertEqual(2, self.Person.objects.count())

    def test_can_save_if_not_included(self):

        class EmbeddedDoc(EmbeddedDocument):
            pass

        class Simple(Document):
            pass

        class Doc(Document):
            string_field = StringField(default='1')
            int_field = IntField(default=1)
            float_field = FloatField(default=1.1)
            boolean_field = BooleanField(default=True)
            datetime_field = DateTimeField(default=datetime.now)
            embedded_document_field = EmbeddedDocumentField(
                EmbeddedDoc, default=lambda: EmbeddedDoc())
            list_field = ListField(default=lambda: [1, 2, 3])
            dict_field = DictField(default=lambda: {"hello": "world"})
            objectid_field = ObjectIdField(default=bson.ObjectId)
            reference_field = ReferenceField(Simple, default=lambda:
                                             Simple().save())
            map_field = MapField(IntField(), default=lambda: {"simple": 1})
            decimal_field = DecimalField(default=1.0)
            complex_datetime_field = ComplexDateTimeField(default=datetime.now)
            url_field = URLField(default="http://mongoengine.org")
            dynamic_field = DynamicField(default=1)
            generic_reference_field = GenericReferenceField(
                default=lambda: Simple().save())
            sorted_list_field = SortedListField(IntField(),
                                                default=lambda: [1, 2, 3])
            email_field = EmailField(default="ross@example.com")
            geo_point_field = GeoPointField(default=lambda: [1, 2])
            sequence_field = SequenceField()
            uuid_field = UUIDField(default=uuid.uuid4)
            generic_embedded_document_field = GenericEmbeddedDocumentField(
                default=lambda: EmbeddedDoc())

        Simple.drop_collection()
        Doc.drop_collection()

        Doc().save()
        my_doc = Doc.objects.only("string_field").first()
        my_doc.string_field = "string"
        my_doc.save()

        my_doc = Doc.objects.get(string_field="string")
        self.assertEqual(my_doc.string_field, "string")
        self.assertEqual(my_doc.int_field, 1)

    def test_document_update(self):

        def update_not_saved_raises():
            person = self.Person(name='dcrosta')
            person.update(set__name='Dan Crosta')

        self.assertRaises(OperationError, update_not_saved_raises)

        author = self.Person(name='dcrosta')
        author.save()

        author.update(set__name='Dan Crosta')
        author.reload()

        p1 = self.Person.objects.first()
        self.assertEqual(p1.name, author.name)

        def update_no_value_raises():
            person = self.Person.objects.first()
            person.update()

        self.assertRaises(OperationError, update_no_value_raises)

        def update_no_op_raises():
            person = self.Person.objects.first()
            person.update(name="Dan")

        self.assertRaises(InvalidQueryError, update_no_op_raises)

    def test_embedded_update(self):
        """
        Test update on `EmbeddedDocumentField` fields
        """

        class Page(EmbeddedDocument):
            log_message = StringField(verbose_name="Log message",
                                      required=True)

        class Site(Document):
            page = EmbeddedDocumentField(Page)

        Site.drop_collection()
        site = Site(page=Page(log_message="Warning: Dummy message"))
        site.save()

        # Update
        site = Site.objects.first()
        site.page.log_message = "Error: Dummy message"
        site.save()

        site = Site.objects.first()
        self.assertEqual(site.page.log_message, "Error: Dummy message")

    def test_embedded_update_db_field(self):
        """
        Test update on `EmbeddedDocumentField` fields when db_field is other
        than default.
        """

        class Page(EmbeddedDocument):
            log_message = StringField(verbose_name="Log message",
                                      db_field="page_log_message",
                                      required=True)

        class Site(Document):
            page = EmbeddedDocumentField(Page)

        Site.drop_collection()

        site = Site(page=Page(log_message="Warning: Dummy message"))
        site.save()

        # Update
        site = Site.objects.first()
        site.page.log_message = "Error: Dummy message"
        site.save()

        site = Site.objects.first()
        self.assertEqual(site.page.log_message, "Error: Dummy message")

    def test_save_only_changed_fields(self):
        """Ensure save only sets / unsets changed fields
        """

        class User(self.Person):
            active = BooleanField(default=True)

        User.drop_collection()

        # Create person object and save it to the database
        user = User(name='Test User', age=30, active=True)
        user.save()
        user.reload()

        # Simulated Race condition
        same_person = self.Person.objects.get()
        same_person.active = False

        user.age = 21
        user.save()

        same_person.name = 'User'
        same_person.save()

        person = self.Person.objects.get()
        self.assertEqual(person.name, 'User')
        self.assertEqual(person.age, 21)
        self.assertEqual(person.active, False)

    def test_query_count_when_saving(self):
        """Ensure references don't cause extra fetches when saving"""
        class Organization(Document):
            name = StringField()

        class User(Document):
            name = StringField()
            orgs = ListField(ReferenceField('Organization'))

        class Feed(Document):
            name = StringField()

        class UserSubscription(Document):
            name = StringField()
            user = ReferenceField(User)
            feed = ReferenceField(Feed)

        Organization.drop_collection()
        User.drop_collection()
        Feed.drop_collection()
        UserSubscription.drop_collection()

        o1 = Organization(name="o1").save()
        o2 = Organization(name="o2").save()

        u1 = User(name="Ross", orgs=[o1, o2]).save()
        f1 = Feed(name="MongoEngine").save()

        sub = UserSubscription(user=u1, feed=f1).save()

        user = User.objects.first()
        # Even if stored as ObjectId's internally mongoengine uses DBRefs
        # As ObjectId's aren't automatically derefenced
        self.assertTrue(isinstance(user._data['orgs'][0], DBRef))
        self.assertTrue(isinstance(user.orgs[0], Organization))
        self.assertTrue(isinstance(user._data['orgs'][0], Organization))

        # Changing a value
        with query_counter() as q:
            self.assertEqual(q, 0)
            sub = UserSubscription.objects.first()
            self.assertEqual(q, 1)
            sub.name = "Test Sub"
            sub.save()
            self.assertEqual(q, 2)

        # Changing a value that will cascade
        with query_counter() as q:
            self.assertEqual(q, 0)
            sub = UserSubscription.objects.first()
            self.assertEqual(q, 1)
            sub.user.name = "Test"
            self.assertEqual(q, 2)
            sub.save(cascade=True)
            self.assertEqual(q, 3)

        # Changing a value and one that will cascade
        with query_counter() as q:
            self.assertEqual(q, 0)
            sub = UserSubscription.objects.first()
            sub.name = "Test Sub 2"
            self.assertEqual(q, 1)
            sub.user.name = "Test 2"
            self.assertEqual(q, 2)
            sub.save(cascade=True)
            self.assertEqual(q, 4)  # One for the UserSub and one for the User

        # Saving with just the refs
        with query_counter() as q:
            self.assertEqual(q, 0)
            sub = UserSubscription(user=u1.pk, feed=f1.pk)
            self.assertEqual(q, 0)
            sub.save()
            self.assertEqual(q, 1)

        # Saving with just the refs on a ListField
        with query_counter() as q:
            self.assertEqual(q, 0)
            User(name="Bob", orgs=[o1.pk, o2.pk]).save()
            self.assertEqual(q, 1)

        # Saving new objects
        with query_counter() as q:
            self.assertEqual(q, 0)
            user = User.objects.first()
            self.assertEqual(q, 1)
            feed = Feed.objects.first()
            self.assertEqual(q, 2)
            sub = UserSubscription(user=user, feed=feed)
            self.assertEqual(q, 2)  # Check no change
            sub.save()
            self.assertEqual(q, 3)

    def test_set_unset_one_operation(self):
        """Ensure that $set and $unset actions are performed in the same
        operation.
        """
        class FooBar(Document):
            foo = StringField(default=None)
            bar = StringField(default=None)

        FooBar.drop_collection()

        # write an entity with a single prop
        foo = FooBar(foo='foo').save()

        self.assertEqual(foo.foo, 'foo')
        del foo.foo
        foo.bar = 'bar'

        with query_counter() as q:
            self.assertEqual(0, q)
            foo.save()
            self.assertEqual(1, q)

    def test_save_only_changed_fields_recursive(self):
        """Ensure save only sets / unsets changed fields
        """

        class Comment(EmbeddedDocument):
            published = BooleanField(default=True)

        class User(self.Person):
            comments_dict = DictField()
            comments = ListField(EmbeddedDocumentField(Comment))
            active = BooleanField(default=True)

        User.drop_collection()

        # Create person object and save it to the database
        person = User(name='Test User', age=30, active=True)
        person.comments.append(Comment())
        person.save()
        person.reload()

        person = self.Person.objects.get()
        self.assertTrue(person.comments[0].published)

        person.comments[0].published = False
        person.save()

        person = self.Person.objects.get()
        self.assertFalse(person.comments[0].published)

        # Simple dict w
        person.comments_dict['first_post'] = Comment()
        person.save()

        person = self.Person.objects.get()
        self.assertTrue(person.comments_dict['first_post'].published)

        person.comments_dict['first_post'].published = False
        person.save()

        person = self.Person.objects.get()
        self.assertFalse(person.comments_dict['first_post'].published)

    def test_delete(self):
        """Ensure that document may be deleted using the delete method.
        """
        person = self.Person(name="Test User", age=30)
        person.save()
        self.assertEqual(self.Person.objects.count(), 1)
        person.delete()
        self.assertEqual(self.Person.objects.count(), 0)

    def test_save_custom_id(self):
        """Ensure that a document may be saved with a custom _id.
        """
        # Create person object and save it to the database
        person = self.Person(name='Test User', age=30,
                             id='497ce96f395f2f052a494fd4')
        person.save()
        # Ensure that the object is in the database with the correct _id
        collection = self.db[self.Person._get_collection_name()]
        person_obj = collection.find_one({'name': 'Test User'})
        self.assertEqual(str(person_obj['_id']), '497ce96f395f2f052a494fd4')

    def test_save_custom_pk(self):
        """Ensure that a document may be saved with a custom _id using pk alias.
        """
        # Create person object and save it to the database
        person = self.Person(name='Test User', age=30,
                             pk='497ce96f395f2f052a494fd4')
        person.save()
        # Ensure that the object is in the database with the correct _id
        collection = self.db[self.Person._get_collection_name()]
        person_obj = collection.find_one({'name': 'Test User'})
        self.assertEqual(str(person_obj['_id']), '497ce96f395f2f052a494fd4')

    def test_save_list(self):
        """Ensure that a list field may be properly saved.
        """
        class Comment(EmbeddedDocument):
            content = StringField()

        class BlogPost(Document):
            content = StringField()
            comments = ListField(EmbeddedDocumentField(Comment))
            tags = ListField(StringField())

        BlogPost.drop_collection()

        post = BlogPost(content='Went for a walk today...')
        post.tags = tags = ['fun', 'leisure']
        comments = [Comment(content='Good for you'), Comment(content='Yay.')]
        post.comments = comments
        post.save()

        collection = self.db[BlogPost._get_collection_name()]
        post_obj = collection.find_one()
        self.assertEqual(post_obj['tags'], tags)
        for comment_obj, comment in zip(post_obj['comments'], comments):
            self.assertEqual(comment_obj['content'], comment['content'])

        BlogPost.drop_collection()

    def test_list_search_by_embedded(self):
        class User(Document):
            username = StringField(required=True)

            meta = {'allow_inheritance': False}

        class Comment(EmbeddedDocument):
            comment = StringField()
            user = ReferenceField(User,
                                  required=True)

            meta = {'allow_inheritance': False}

        class Page(Document):
            comments = ListField(EmbeddedDocumentField(Comment))
            meta = {'allow_inheritance': False,
                    'indexes': [
                        {'fields': ['comments.user']}
                    ]}

        User.drop_collection()
        Page.drop_collection()

        u1 = User(username="wilson")
        u1.save()

        u2 = User(username="rozza")
        u2.save()

        u3 = User(username="hmarr")
        u3.save()

        p1 = Page(comments=[Comment(user=u1, comment="Its very good"),
                            Comment(user=u2, comment="Hello world"),
                            Comment(user=u3, comment="Ping Pong"),
                            Comment(user=u1, comment="I like a beer")])
        p1.save()

        p2 = Page(comments=[Comment(user=u1, comment="Its very good"),
                            Comment(user=u2, comment="Hello world")])
        p2.save()

        p3 = Page(comments=[Comment(user=u3, comment="Its very good")])
        p3.save()

        p4 = Page(comments=[Comment(user=u2, comment="Heavy Metal song")])
        p4.save()

        self.assertEqual([p1, p2], list(Page.objects.filter(comments__user=u1)))
        self.assertEqual([p1, p2, p4], list(Page.objects.filter(comments__user=u2)))
        self.assertEqual([p1, p3], list(Page.objects.filter(comments__user=u3)))

    def test_save_embedded_document(self):
        """Ensure that a document with an embedded document field may be
        saved in the database.
        """
        class EmployeeDetails(EmbeddedDocument):
            position = StringField()

        class Employee(self.Person):
            salary = IntField()
            details = EmbeddedDocumentField(EmployeeDetails)

        # Create employee object and save it to the database
        employee = Employee(name='Test Employee', age=50, salary=20000)
        employee.details = EmployeeDetails(position='Developer')
        employee.save()

        # Ensure that the object is in the database
        collection = self.db[self.Person._get_collection_name()]
        employee_obj = collection.find_one({'name': 'Test Employee'})
        self.assertEqual(employee_obj['name'], 'Test Employee')
        self.assertEqual(employee_obj['age'], 50)
        # Ensure that the 'details' embedded object saved correctly
        self.assertEqual(employee_obj['details']['position'], 'Developer')

    def test_embedded_update_after_save(self):
        """
        Test update of `EmbeddedDocumentField` attached to a newly saved
        document.
        """
        class Page(EmbeddedDocument):
            log_message = StringField(verbose_name="Log message",
                                      required=True)

        class Site(Document):
            page = EmbeddedDocumentField(Page)

        Site.drop_collection()
        site = Site(page=Page(log_message="Warning: Dummy message"))
        site.save()

        # Update
        site.page.log_message = "Error: Dummy message"
        site.save()

        site = Site.objects.first()
        self.assertEqual(site.page.log_message, "Error: Dummy message")

    def test_updating_an_embedded_document(self):
        """Ensure that a document with an embedded document field may be
        saved in the database.
        """
        class EmployeeDetails(EmbeddedDocument):
            position = StringField()

        class Employee(self.Person):
            salary = IntField()
            details = EmbeddedDocumentField(EmployeeDetails)

        # Create employee object and save it to the database
        employee = Employee(name='Test Employee', age=50, salary=20000)
        employee.details = EmployeeDetails(position='Developer')
        employee.save()

        # Test updating an embedded document
        promoted_employee = Employee.objects.get(name='Test Employee')
        promoted_employee.details.position = 'Senior Developer'
        promoted_employee.save()

        promoted_employee.reload()
        self.assertEqual(promoted_employee.name, 'Test Employee')
        self.assertEqual(promoted_employee.age, 50)

        # Ensure that the 'details' embedded object saved correctly
        self.assertEqual(promoted_employee.details.position, 'Senior Developer')

        # Test removal
        promoted_employee.details = None
        promoted_employee.save()

        promoted_employee.reload()
        self.assertEqual(promoted_employee.details, None)

    def test_object_mixins(self):

        class NameMixin(object):
            name = StringField()

        class Foo(EmbeddedDocument, NameMixin):
            quantity = IntField()

        self.assertEqual(['name', 'quantity'], sorted(Foo._fields.keys()))

        class Bar(Document, NameMixin):
            widgets = StringField()

        self.assertEqual(['id', 'name', 'widgets'], sorted(Bar._fields.keys()))

    def test_mixin_inheritance(self):
        class BaseMixIn(object):
            count = IntField()
            data = StringField()

        class DoubleMixIn(BaseMixIn):
            comment = StringField()

        class TestDoc(Document, DoubleMixIn):
            age = IntField()

        TestDoc.drop_collection()
        t = TestDoc(count=12, data="test",
                    comment="great!", age=19)

        t.save()

        t = TestDoc.objects.first()

        self.assertEqual(t.age, 19)
        self.assertEqual(t.comment, "great!")
        self.assertEqual(t.data, "test")
        self.assertEqual(t.count, 12)

    def test_save_reference(self):
        """Ensure that a document reference field may be saved in the database.
        """

        class BlogPost(Document):
            meta = {'collection': 'blogpost_1'}
            content = StringField()
            author = ReferenceField(self.Person)

        BlogPost.drop_collection()

        author = self.Person(name='Test User')
        author.save()

        post = BlogPost(content='Watched some TV today... how exciting.')
        # Should only reference author when saving
        post.author = author
        post.save()

        post_obj = BlogPost.objects.first()

        # Test laziness
        self.assertTrue(isinstance(post_obj._data['author'],
                                   bson.DBRef))
        self.assertTrue(isinstance(post_obj.author, self.Person))
        self.assertEqual(post_obj.author.name, 'Test User')

        # Ensure that the dereferenced object may be changed and saved
        post_obj.author.age = 25
        post_obj.author.save()

        author = list(self.Person.objects(name='Test User'))[-1]
        self.assertEqual(author.age, 25)

        BlogPost.drop_collection()

    def test_duplicate_db_fields_raise_invalid_document_error(self):
        """Ensure a InvalidDocumentError is thrown if duplicate fields
        declare the same db_field"""

        def throw_invalid_document_error():
            class Foo(Document):
                name = StringField()
                name2 = StringField(db_field='name')

        self.assertRaises(InvalidDocumentError, throw_invalid_document_error)

    def test_invalid_son(self):
        """Raise an error if loading invalid data"""
        class Occurrence(EmbeddedDocument):
            number = IntField()

        class Word(Document):
            stem = StringField()
            count = IntField(default=1)
            forms = ListField(StringField(), default=list)
            occurs = ListField(EmbeddedDocumentField(Occurrence), default=list)

        def raise_invalid_document():
            Word._from_son({'stem': [1, 2, 3], 'forms': 1, 'count': 'one',
                            'occurs': {"hello": None}})

        self.assertRaises(InvalidDocumentError, raise_invalid_document)

    def test_reverse_delete_rule_cascade_and_nullify(self):
        """Ensure that a referenced document is also deleted upon deletion.
        """

        class BlogPost(Document):
            content = StringField()
            author = ReferenceField(self.Person, reverse_delete_rule=CASCADE)
            reviewer = ReferenceField(self.Person, reverse_delete_rule=NULLIFY)

        self.Person.drop_collection()
        BlogPost.drop_collection()

        author = self.Person(name='Test User')
        author.save()

        reviewer = self.Person(name='Re Viewer')
        reviewer.save()

        post = BlogPost(content='Watched some TV')
        post.author = author
        post.reviewer = reviewer
        post.save()

        reviewer.delete()
        self.assertEqual(BlogPost.objects.count(), 1)  # No effect on the BlogPost
        self.assertEqual(BlogPost.objects.get().reviewer, None)

        # Delete the Person, which should lead to deletion of the BlogPost, too
        author.delete()
        self.assertEqual(BlogPost.objects.count(), 0)

    def test_reverse_delete_rule_with_document_inheritance(self):
        """Ensure that a referenced document is also deleted upon deletion
        of a child document.
        """

        class Writer(self.Person):
            pass

        class BlogPost(Document):
            content = StringField()
            author = ReferenceField(self.Person, reverse_delete_rule=CASCADE)
            reviewer = ReferenceField(self.Person, reverse_delete_rule=NULLIFY)

        self.Person.drop_collection()
        BlogPost.drop_collection()

        author = Writer(name='Test User')
        author.save()

        reviewer = Writer(name='Re Viewer')
        reviewer.save()

        post = BlogPost(content='Watched some TV')
        post.author = author
        post.reviewer = reviewer
        post.save()

        reviewer.delete()
        self.assertEqual(BlogPost.objects.count(), 1)
        self.assertEqual(BlogPost.objects.get().reviewer, None)

        # Delete the Writer should lead to deletion of the BlogPost
        author.delete()
        self.assertEqual(BlogPost.objects.count(), 0)

    def test_reverse_delete_rule_cascade_and_nullify_complex_field(self):
        """Ensure that a referenced document is also deleted upon deletion for
        complex fields.
        """

        class BlogPost(Document):
            content = StringField()
            authors = ListField(ReferenceField(self.Person, reverse_delete_rule=CASCADE))
            reviewers = ListField(ReferenceField(self.Person, reverse_delete_rule=NULLIFY))

        self.Person.drop_collection()

        BlogPost.drop_collection()

        author = self.Person(name='Test User')
        author.save()

        reviewer = self.Person(name='Re Viewer')
        reviewer.save()

        post = BlogPost(content='Watched some TV')
        post.authors = [author]
        post.reviewers = [reviewer]
        post.save()

        # Deleting the reviewer should have no effect on the BlogPost
        reviewer.delete()
        self.assertEqual(BlogPost.objects.count(), 1)
        self.assertEqual(BlogPost.objects.get().reviewers, [])

        # Delete the Person, which should lead to deletion of the BlogPost, too
        author.delete()
        self.assertEqual(BlogPost.objects.count(), 0)

    def test_reverse_delete_rule_cascade_triggers_pre_delete_signal(self):
        ''' ensure the pre_delete signal is triggered upon a cascading deletion
        setup a blog post with content, an author and editor
        delete the author which triggers deletion of blogpost via cascade
        blog post's pre_delete signal alters an editor attribute
        '''
        class Editor(self.Person):
            review_queue = IntField(default=0)

        class BlogPost(Document):
            content = StringField()
            author = ReferenceField(self.Person, reverse_delete_rule=CASCADE)
            editor = ReferenceField(Editor)

            @classmethod
            def pre_delete(cls, sender, document, **kwargs):
                # decrement the docs-to-review count
                document.editor.update(dec__review_queue=1)

        signals.pre_delete.connect(BlogPost.pre_delete, sender=BlogPost)

        self.Person.drop_collection()
        BlogPost.drop_collection()
        Editor.drop_collection()

        author = self.Person(name='Will S.').save()
        editor = Editor(name='Max P.', review_queue=1).save()
        BlogPost(content='wrote some books', author=author,
                 editor=editor).save()

        # delete the author, the post is also deleted due to the CASCADE rule
        author.delete()
        # the pre-delete signal should have decremented the editor's queue
        editor = Editor.objects(name='Max P.').get()
        self.assertEqual(editor.review_queue, 0)

    def test_two_way_reverse_delete_rule(self):
        """Ensure that Bi-Directional relationships work with
        reverse_delete_rule
        """

        class Bar(Document):
            content = StringField()
            foo = ReferenceField('Foo')

        class Foo(Document):
            content = StringField()
            bar = ReferenceField(Bar)

        Bar.register_delete_rule(Foo, 'bar', NULLIFY)
        Foo.register_delete_rule(Bar, 'foo', NULLIFY)

        Bar.drop_collection()
        Foo.drop_collection()

        b = Bar(content="Hello")
        b.save()

        f = Foo(content="world", bar=b)
        f.save()

        b.foo = f
        b.save()

        f.delete()

        self.assertEqual(Bar.objects.count(), 1)  # No effect on the BlogPost
        self.assertEqual(Bar.objects.get().foo, None)

    def test_invalid_reverse_delete_rules_raise_errors(self):

        def throw_invalid_document_error():
            class Blog(Document):
                content = StringField()
                authors = MapField(ReferenceField(self.Person, reverse_delete_rule=CASCADE))
                reviewers = DictField(field=ReferenceField(self.Person, reverse_delete_rule=NULLIFY))

        self.assertRaises(InvalidDocumentError, throw_invalid_document_error)

        def throw_invalid_document_error_embedded():
            class Parents(EmbeddedDocument):
                father = ReferenceField('Person', reverse_delete_rule=DENY)
                mother = ReferenceField('Person', reverse_delete_rule=DENY)

        self.assertRaises(InvalidDocumentError, throw_invalid_document_error_embedded)

    def test_reverse_delete_rule_cascade_recurs(self):
        """Ensure that a chain of documents is also deleted upon cascaded
        deletion.
        """

        class BlogPost(Document):
            content = StringField()
            author = ReferenceField(self.Person, reverse_delete_rule=CASCADE)

        class Comment(Document):
            text = StringField()
            post = ReferenceField(BlogPost, reverse_delete_rule=CASCADE)

        self.Person.drop_collection()
        BlogPost.drop_collection()
        Comment.drop_collection()

        author = self.Person(name='Test User')
        author.save()

        post = BlogPost(content = 'Watched some TV')
        post.author = author
        post.save()

        comment = Comment(text = 'Kudos.')
        comment.post = post
        comment.save()

        # Delete the Person, which should lead to deletion of the BlogPost, and,
        # recursively to the Comment, too
        author.delete()
        self.assertEqual(Comment.objects.count(), 0)

        self.Person.drop_collection()
        BlogPost.drop_collection()
        Comment.drop_collection()

    def test_reverse_delete_rule_deny(self):
        """Ensure that a document cannot be referenced if there are still
        documents referring to it.
        """

        class BlogPost(Document):
            content = StringField()
            author = ReferenceField(self.Person, reverse_delete_rule=DENY)

        self.Person.drop_collection()
        BlogPost.drop_collection()

        author = self.Person(name='Test User')
        author.save()

        post = BlogPost(content = 'Watched some TV')
        post.author = author
        post.save()

        # Delete the Person should be denied
        self.assertRaises(OperationError, author.delete)  # Should raise denied error
        self.assertEqual(BlogPost.objects.count(), 1)  # No objects may have been deleted
        self.assertEqual(self.Person.objects.count(), 1)

        # Other users, that don't have BlogPosts must be removable, like normal
        author = self.Person(name='Another User')
        author.save()

        self.assertEqual(self.Person.objects.count(), 2)
        author.delete()
        self.assertEqual(self.Person.objects.count(), 1)

        self.Person.drop_collection()
        BlogPost.drop_collection()

    def subclasses_and_unique_keys_works(self):

        class A(Document):
            pass

        class B(A):
            foo = BooleanField(unique=True)

        A.drop_collection()
        B.drop_collection()

        A().save()
        A().save()
        B(foo=True).save()

        self.assertEqual(A.objects.count(), 2)
        self.assertEqual(B.objects.count(), 1)
        A.drop_collection()
        B.drop_collection()

    def test_document_hash(self):
        """Test document in list, dict, set
        """
        class User(Document):
            pass

        class BlogPost(Document):
            pass

        # Clear old datas
        User.drop_collection()
        BlogPost.drop_collection()

        u1 = User.objects.create()
        u2 = User.objects.create()
        u3 = User.objects.create()
        u4 = User()  # New object

        b1 = BlogPost.objects.create()
        b2 = BlogPost.objects.create()

        # in List
        all_user_list = list(User.objects.all())

        self.assertTrue(u1 in all_user_list)
        self.assertTrue(u2 in all_user_list)
        self.assertTrue(u3 in all_user_list)
        self.assertFalse(u4 in all_user_list)  # New object
        self.assertFalse(b1 in all_user_list)  # Other object
        self.assertFalse(b2 in all_user_list)  # Other object

        # in Dict
        all_user_dic = {}
        for u in User.objects.all():
            all_user_dic[u] = "OK"

        self.assertEqual(all_user_dic.get(u1, False), "OK")
        self.assertEqual(all_user_dic.get(u2, False), "OK")
        self.assertEqual(all_user_dic.get(u3, False), "OK")
        self.assertEqual(all_user_dic.get(u4, False), False)  # New object
        self.assertEqual(all_user_dic.get(b1, False), False)  # Other object
        self.assertEqual(all_user_dic.get(b2, False), False)  # Other object

        # in Set
        all_user_set = set(User.objects.all())

        self.assertTrue(u1 in all_user_set)

    def test_picklable(self):

        pickle_doc = PickleTest(number=1, string="One", lists=['1', '2'])
        pickle_doc.embedded = PickleEmbedded()
        pickled_doc = pickle.dumps(pickle_doc)  # make sure pickling works even before the doc is saved
        pickle_doc.save()

        pickled_doc = pickle.dumps(pickle_doc)
        resurrected = pickle.loads(pickled_doc)

        self.assertEqual(resurrected, pickle_doc)

        # Test pickling changed data
        pickle_doc.lists.append("3")
        pickled_doc = pickle.dumps(pickle_doc)
        resurrected = pickle.loads(pickled_doc)

        self.assertEqual(resurrected, pickle_doc)
        resurrected.string = "Two"
        resurrected.save()

        pickle_doc = PickleTest.objects.first()
        self.assertEqual(resurrected, pickle_doc)
        self.assertEqual(pickle_doc.string, "Two")
        self.assertEqual(pickle_doc.lists, ["1", "2", "3"])

    def test_dynamic_document_pickle(self):

        pickle_doc = PickleDynamicTest(name="test", number=1, string="One", lists=['1', '2'])
        pickle_doc.embedded = PickleDyanmicEmbedded(foo="Bar")
        pickled_doc = pickle.dumps(pickle_doc)  # make sure pickling works even before the doc is saved

        pickle_doc.save()

        pickled_doc = pickle.dumps(pickle_doc)
        resurrected = pickle.loads(pickled_doc)

        self.assertEqual(resurrected, pickle_doc)
        self.assertEqual(resurrected._fields_ordered,
                         pickle_doc._fields_ordered)
        self.assertEqual(resurrected._dynamic_fields.keys(),
                         pickle_doc._dynamic_fields.keys())

        self.assertEqual(resurrected.embedded, pickle_doc.embedded)
        self.assertEqual(resurrected.embedded._fields_ordered,
                         pickle_doc.embedded._fields_ordered)
        self.assertEqual(resurrected.embedded._dynamic_fields.keys(),
                         pickle_doc.embedded._dynamic_fields.keys())

    def test_picklable_on_signals(self):
        pickle_doc = PickleSignalsTest(number=1, string="One", lists=['1', '2'])
        pickle_doc.embedded = PickleEmbedded()
        pickle_doc.save()
        pickle_doc.delete()

    def test_throw_invalid_document_error(self):

        # test handles people trying to upsert
        def throw_invalid_document_error():
            class Blog(Document):
                validate = DictField()

        self.assertRaises(InvalidDocumentError, throw_invalid_document_error)

    def test_mutating_documents(self):

        class B(EmbeddedDocument):
            field1 = StringField(default='field1')

        class A(Document):
            b = EmbeddedDocumentField(B, default=lambda: B())

        A.drop_collection()
        a = A()
        a.save()
        a.reload()
        self.assertEqual(a.b.field1, 'field1')

        class C(EmbeddedDocument):
            c_field = StringField(default='cfield')

        class B(EmbeddedDocument):
            field1 = StringField(default='field1')
            field2 = EmbeddedDocumentField(C, default=lambda: C())

        class A(Document):
            b = EmbeddedDocumentField(B, default=lambda: B())

        a = A.objects()[0]
        a.b.field2.c_field = 'new value'
        a.save()

        a.reload()
        self.assertEqual(a.b.field2.c_field, 'new value')

    def test_can_save_false_values(self):
        """Ensures you can save False values on save"""
        class Doc(Document):
            foo = StringField()
            archived = BooleanField(default=False, required=True)

        Doc.drop_collection()
        d = Doc()
        d.save()
        d.archived = False
        d.save()

        self.assertEqual(Doc.objects(archived=False).count(), 1)

    def test_can_save_false_values_dynamic(self):
        """Ensures you can save False values on dynamic docs"""
        class Doc(DynamicDocument):
            foo = StringField()

        Doc.drop_collection()
        d = Doc()
        d.save()
        d.archived = False
        d.save()

        self.assertEqual(Doc.objects(archived=False).count(), 1)

    def test_do_not_save_unchanged_references(self):
        """Ensures cascading saves dont auto update"""
        class Job(Document):
            name = StringField()

        class Person(Document):
            name = StringField()
            age = IntField()
            job = ReferenceField(Job)

        Job.drop_collection()
        Person.drop_collection()

        job = Job(name="Job 1")
        # job should not have any changed fields after the save
        job.save()

        person = Person(name="name", age=10, job=job)

        from pymongo.collection import Collection
        orig_update = Collection.update
        try:
            def fake_update(*args, **kwargs):
                self.fail("Unexpected update for %s" % args[0].name)
                return orig_update(*args, **kwargs)

            Collection.update = fake_update
            person.save()
        finally:
            Collection.update = orig_update

    def test_db_alias_tests(self):
        """ DB Alias tests """
        # mongoenginetest - Is default connection alias from setUp()
        # Register Aliases
        register_connection('testdb-1', 'mongoenginetest2')
        register_connection('testdb-2', 'mongoenginetest3')
        register_connection('testdb-3', 'mongoenginetest4')

        class User(Document):
            name = StringField()
            meta = {"db_alias": "testdb-1"}

        class Book(Document):
            name = StringField()
            meta = {"db_alias": "testdb-2"}

        # Drops
        User.drop_collection()
        Book.drop_collection()

        # Create
        bob = User.objects.create(name="Bob")
        hp = Book.objects.create(name="Harry Potter")

        # Selects
        self.assertEqual(User.objects.first(), bob)
        self.assertEqual(Book.objects.first(), hp)

        # DeReference
        class AuthorBooks(Document):
            author = ReferenceField(User)
            book = ReferenceField(Book)
            meta = {"db_alias": "testdb-3"}

        # Drops
        AuthorBooks.drop_collection()

        ab = AuthorBooks.objects.create(author=bob, book=hp)

        # select
        self.assertEqual(AuthorBooks.objects.first(), ab)
        self.assertEqual(AuthorBooks.objects.first().book, hp)
        self.assertEqual(AuthorBooks.objects.first().author, bob)
        self.assertEqual(AuthorBooks.objects.filter(author=bob).first(), ab)
        self.assertEqual(AuthorBooks.objects.filter(book=hp).first(), ab)

        # DB Alias
        self.assertEqual(User._get_db(), get_db("testdb-1"))
        self.assertEqual(Book._get_db(), get_db("testdb-2"))
        self.assertEqual(AuthorBooks._get_db(), get_db("testdb-3"))

        # Collections
        self.assertEqual(User._get_collection(), get_db("testdb-1")[User._get_collection_name()])
        self.assertEqual(Book._get_collection(), get_db("testdb-2")[Book._get_collection_name()])
        self.assertEqual(AuthorBooks._get_collection(), get_db("testdb-3")[AuthorBooks._get_collection_name()])

    def test_db_alias_overrides(self):
        """db_alias can be overriden
        """
        # Register a connection with db_alias testdb-2
        register_connection('testdb-2', 'mongoenginetest2')

        class A(Document):
            """Uses default db_alias
            """
            name = StringField()
            meta = {"allow_inheritance": True}

        class B(A):
            """Uses testdb-2 db_alias
            """
            meta = {"db_alias": "testdb-2"}

        A.objects.all()

        self.assertEqual('testdb-2', B._meta.get('db_alias'))
        self.assertEqual('mongoenginetest',
                         A._get_collection().database.name)
        self.assertEqual('mongoenginetest2',
                         B._get_collection().database.name)

    def test_db_alias_propagates(self):
        """db_alias propagates?
        """
        register_connection('testdb-1', 'mongoenginetest2')

        class A(Document):
            name = StringField()
            meta = {"db_alias": "testdb-1", "allow_inheritance": True}

        class B(A):
            pass

        self.assertEqual('testdb-1', B._meta.get('db_alias'))

    def test_db_ref_usage(self):
        """ DB Ref usage  in dict_fields"""

        class User(Document):
            name = StringField()

        class Book(Document):
            name = StringField()
            author = ReferenceField(User)
            extra = DictField()
            meta = {
                'ordering': ['+name']
            }

            def __unicode__(self):
                return self.name

            def __str__(self):
                return self.name

        # Drops
        User.drop_collection()
        Book.drop_collection()

        # Authors
        bob = User.objects.create(name="Bob")
        jon = User.objects.create(name="Jon")

        # Redactors
        karl = User.objects.create(name="Karl")
        susan = User.objects.create(name="Susan")
        peter = User.objects.create(name="Peter")

        # Bob
        Book.objects.create(name="1", author=bob, extra={
            "a": bob.to_dbref(), "b": [karl.to_dbref(), susan.to_dbref()]})
        Book.objects.create(name="2", author=bob, extra={
            "a": bob.to_dbref(), "b": karl.to_dbref()})
        Book.objects.create(name="3", author=bob, extra={
            "a": bob.to_dbref(), "c": [jon.to_dbref(), peter.to_dbref()]})
        Book.objects.create(name="4", author=bob)

        # Jon
        Book.objects.create(name="5", author=jon)
        Book.objects.create(name="6", author=peter)
        Book.objects.create(name="7", author=jon)
        Book.objects.create(name="8", author=jon)
        Book.objects.create(name="9", author=jon,
                            extra={"a": peter.to_dbref()})

        # Checks
        self.assertEqual(",".join([str(b) for b in Book.objects.all()]),
                         "1,2,3,4,5,6,7,8,9")
        # bob related books
        self.assertEqual(",".join([str(b) for b in Book.objects.filter(
                                  Q(extra__a=bob) |
                                  Q(author=bob) |
                                  Q(extra__b=bob))]),
                         "1,2,3,4")

        # Susan & Karl related books
        self.assertEqual(",".join([str(b) for b in Book.objects.filter(
                                   Q(extra__a__all=[karl, susan]) |
                                   Q(author__all=[karl, susan]) |
                                   Q(extra__b__all=[
                                     karl.to_dbref(), susan.to_dbref()]))
                                   ]), "1")

        # $Where
        self.assertEqual(u",".join([str(b) for b in Book.objects.filter(
                                    __raw__={
                                        "$where": """
                                            function(){
                                                return this.name == '1' ||
                                                       this.name == '2';}"""
                                    })]),
                         "1,2")

    def test_switch_db_instance(self):
        register_connection('testdb-1', 'mongoenginetest2')

        class Group(Document):
            name = StringField()

        Group.drop_collection()
        with switch_db(Group, 'testdb-1') as Group:
            Group.drop_collection()

        Group(name="hello - default").save()
        self.assertEqual(1, Group.objects.count())

        group = Group.objects.first()
        group.switch_db('testdb-1')
        group.name = "hello - testdb!"
        group.save()

        with switch_db(Group, 'testdb-1') as Group:
            group = Group.objects.first()
            self.assertEqual("hello - testdb!", group.name)

        group = Group.objects.first()
        self.assertEqual("hello - default", group.name)

        # Slightly contrived now - perform an update
        # Only works as they have the same object_id
        group.switch_db('testdb-1')
        group.update(set__name="hello - update")

        with switch_db(Group, 'testdb-1') as Group:
            group = Group.objects.first()
            self.assertEqual("hello - update", group.name)
            Group.drop_collection()
            self.assertEqual(0, Group.objects.count())

        group = Group.objects.first()
        self.assertEqual("hello - default", group.name)

        # Totally contrived now - perform a delete
        # Only works as they have the same object_id
        group.switch_db('testdb-1')
        group.delete()

        with switch_db(Group, 'testdb-1') as Group:
            self.assertEqual(0, Group.objects.count())

        group = Group.objects.first()
        self.assertEqual("hello - default", group.name)

    def test_no_overwritting_no_data_loss(self):

        class User(Document):
            username = StringField(primary_key=True)
            name = StringField()

            @property
            def foo(self):
                return True

        User.drop_collection()

        user = User(username="Ross", foo="bar")
        self.assertTrue(user.foo)

        User._get_collection().save({"_id": "Ross", "foo": "Bar",
                                     "data": [1, 2, 3]})

        user = User.objects.first()
        self.assertEqual("Ross", user.username)
        self.assertEqual(True, user.foo)
        self.assertEqual("Bar", user._data["foo"])
        self.assertEqual([1, 2, 3], user._data["data"])

    def test_spaces_in_keys(self):

        class Embedded(DynamicEmbeddedDocument):
            pass

        class Doc(DynamicDocument):
            pass

        Doc.drop_collection()
        doc = Doc()
        setattr(doc, 'hello world', 1)
        doc.save()

        one = Doc.objects.filter(**{'hello world': 1}).count()
        self.assertEqual(1, one)

    def test_shard_key(self):
        class LogEntry(Document):
            machine = StringField()
            log = StringField()

            meta = {
                'shard_key': ('machine',)
            }

        LogEntry.drop_collection()

        log = LogEntry()
        log.machine = "Localhost"
        log.save()

        log.log = "Saving"
        log.save()

        def change_shard_key():
            log.machine = "127.0.0.1"

        self.assertRaises(OperationError, change_shard_key)

    def test_shard_key_primary(self):
        class LogEntry(Document):
            machine = StringField(primary_key=True)
            log = StringField()

            meta = {
                'shard_key': ('machine',)
            }

        LogEntry.drop_collection()

        log = LogEntry()
        log.machine = "Localhost"
        log.save()

        log.log = "Saving"
        log.save()

        def change_shard_key():
            log.machine = "127.0.0.1"

        self.assertRaises(OperationError, change_shard_key)

    def test_kwargs_simple(self):

        class Embedded(EmbeddedDocument):
            name = StringField()

        class Doc(Document):
            doc_name = StringField()
            doc = EmbeddedDocumentField(Embedded)

        classic_doc = Doc(doc_name="my doc", doc=Embedded(name="embedded doc"))
        dict_doc = Doc(**{"doc_name": "my doc",
                          "doc": {"name": "embedded doc"}})

        self.assertEqual(classic_doc, dict_doc)
        self.assertEqual(classic_doc._data, dict_doc._data)

    def test_kwargs_complex(self):

        class Embedded(EmbeddedDocument):
            name = StringField()

        class Doc(Document):
            doc_name = StringField()
            docs = ListField(EmbeddedDocumentField(Embedded))

        classic_doc = Doc(doc_name="my doc", docs=[
                          Embedded(name="embedded doc1"),
                          Embedded(name="embedded doc2")])
        dict_doc = Doc(**{"doc_name": "my doc",
                          "docs": [{"name": "embedded doc1"},
                                   {"name": "embedded doc2"}]})

        self.assertEqual(classic_doc, dict_doc)
        self.assertEqual(classic_doc._data, dict_doc._data)

    def test_positional_creation(self):
        """Ensure that document may be created using positional arguments.
        """
        person = self.Person("Test User", 42)
        self.assertEqual(person.name, "Test User")
        self.assertEqual(person.age, 42)

    def test_mixed_creation(self):
        """Ensure that document may be created using mixed arguments.
        """
        person = self.Person("Test User", age=42)
        self.assertEqual(person.name, "Test User")
        self.assertEqual(person.age, 42)

    def test_mixed_creation_dynamic(self):
        """Ensure that document may be created using mixed arguments.
        """
        class Person(DynamicDocument):
            name = StringField()

        person = Person("Test User", age=42)
        self.assertEqual(person.name, "Test User")
        self.assertEqual(person.age, 42)

    def test_bad_mixed_creation(self):
        """Ensure that document gives correct error when duplicating arguments
        """
        def construct_bad_instance():
            return self.Person("Test User", 42, name="Bad User")

        self.assertRaises(TypeError, construct_bad_instance)

    def test_data_contains_id_field(self):
        """Ensure that asking for _data returns 'id'
        """
        class Person(Document):
            name = StringField()

        Person.drop_collection()
        Person(name="Harry Potter").save()

        person = Person.objects.first()
        self.assertTrue('id' in person._data.keys())
        self.assertEqual(person._data.get('id'), person.id)

    def test_complex_nesting_document_and_embedded_document(self):

        class Macro(EmbeddedDocument):
            value = DynamicField(default="UNDEFINED")

        class Parameter(EmbeddedDocument):
            macros = MapField(EmbeddedDocumentField(Macro))

            def expand(self):
                self.macros["test"] = Macro()

        class Node(Document):
            parameters = MapField(EmbeddedDocumentField(Parameter))

            def expand(self):
                self.flattened_parameter = {}
                for parameter_name, parameter in self.parameters.iteritems():
                    parameter.expand()

        class System(Document):
            name = StringField(required=True)
            nodes = MapField(ReferenceField(Node, dbref=False))

            def save(self, *args, **kwargs):
                for node_name, node in self.nodes.iteritems():
                    node.expand()
                    node.save(*args, **kwargs)
                super(System, self).save(*args, **kwargs)

        System.drop_collection()
        Node.drop_collection()

        system = System(name="system")
        system.nodes["node"] = Node()
        system.save()
        system.nodes["node"].parameters["param"] = Parameter()
        system.save()

        system = System.objects.first()
        self.assertEqual("UNDEFINED", system.nodes["node"].parameters["param"].macros["test"].value)

    def test_embedded_document_equality(self):

        class Test(Document):
            field = StringField(required=True)

        class Embedded(EmbeddedDocument):
            ref = ReferenceField(Test)

        Test.drop_collection()
        test = Test(field='123').save()      # has id

        e = Embedded(ref=test)
        f1 = Embedded._from_son(e.to_mongo())
        f2 = Embedded._from_son(e.to_mongo())

        self.assertEqual(f1, f2)
        f1.ref  # Dereferences lazily
        self.assertEqual(f1, f2)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = json_serialisation
import sys
sys.path[0:0] = [""]

import unittest
import uuid

from nose.plugins.skip import SkipTest
from datetime import datetime
from bson import ObjectId

import pymongo

from mongoengine import *

__all__ = ("TestJson",)


class TestJson(unittest.TestCase):

    def setUp(self):
        connect(db='mongoenginetest')

    def test_json_simple(self):

        class Embedded(EmbeddedDocument):
            string = StringField()

        class Doc(Document):
            string = StringField()
            embedded_field = EmbeddedDocumentField(Embedded)

        doc = Doc(string="Hi", embedded_field=Embedded(string="Hi"))

        doc_json = doc.to_json(sort_keys=True, separators=(',', ':'))
        expected_json = """{"embedded_field":{"string":"Hi"},"string":"Hi"}"""
        self.assertEqual(doc_json, expected_json)

        self.assertEqual(doc, Doc.from_json(doc.to_json()))

    def test_json_complex(self):

        if pymongo.version_tuple[0] <= 2 and pymongo.version_tuple[1] <= 3:
            raise SkipTest("Need pymongo 2.4 as has a fix for DBRefs")

        class EmbeddedDoc(EmbeddedDocument):
            pass

        class Simple(Document):
            pass

        class Doc(Document):
            string_field = StringField(default='1')
            int_field = IntField(default=1)
            float_field = FloatField(default=1.1)
            boolean_field = BooleanField(default=True)
            datetime_field = DateTimeField(default=datetime.now)
            embedded_document_field = EmbeddedDocumentField(EmbeddedDoc,
                                        default=lambda: EmbeddedDoc())
            list_field = ListField(default=lambda: [1, 2, 3])
            dict_field = DictField(default=lambda: {"hello": "world"})
            objectid_field = ObjectIdField(default=ObjectId)
            reference_field = ReferenceField(Simple, default=lambda:
                                                        Simple().save())
            map_field = MapField(IntField(), default=lambda: {"simple": 1})
            decimal_field = DecimalField(default=1.0)
            complex_datetime_field = ComplexDateTimeField(default=datetime.now)
            url_field = URLField(default="http://mongoengine.org")
            dynamic_field = DynamicField(default=1)
            generic_reference_field = GenericReferenceField(
                                            default=lambda: Simple().save())
            sorted_list_field = SortedListField(IntField(),
                                                default=lambda: [1, 2, 3])
            email_field = EmailField(default="ross@example.com")
            geo_point_field = GeoPointField(default=lambda: [1, 2])
            sequence_field = SequenceField()
            uuid_field = UUIDField(default=uuid.uuid4)
            generic_embedded_document_field = GenericEmbeddedDocumentField(
                                        default=lambda: EmbeddedDoc())

        doc = Doc()
        self.assertEqual(doc, Doc.from_json(doc.to_json()))


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = validation
# -*- coding: utf-8 -*-
import sys
sys.path[0:0] = [""]

import unittest
from datetime import datetime

from mongoengine import *

__all__ = ("ValidatorErrorTest",)


class ValidatorErrorTest(unittest.TestCase):

    def setUp(self):
        connect(db='mongoenginetest')

    def test_to_dict(self):
        """Ensure a ValidationError handles error to_dict correctly.
        """
        error = ValidationError('root')
        self.assertEqual(error.to_dict(), {})

        # 1st level error schema
        error.errors = {'1st': ValidationError('bad 1st'), }
        self.assertTrue('1st' in error.to_dict())
        self.assertEqual(error.to_dict()['1st'], 'bad 1st')

        # 2nd level error schema
        error.errors = {'1st': ValidationError('bad 1st', errors={
            '2nd': ValidationError('bad 2nd'),
        })}
        self.assertTrue('1st' in error.to_dict())
        self.assertTrue(isinstance(error.to_dict()['1st'], dict))
        self.assertTrue('2nd' in error.to_dict()['1st'])
        self.assertEqual(error.to_dict()['1st']['2nd'], 'bad 2nd')

        # moar levels
        error.errors = {'1st': ValidationError('bad 1st', errors={
            '2nd': ValidationError('bad 2nd', errors={
                '3rd': ValidationError('bad 3rd', errors={
                    '4th': ValidationError('Inception'),
                }),
            }),
        })}
        self.assertTrue('1st' in error.to_dict())
        self.assertTrue('2nd' in error.to_dict()['1st'])
        self.assertTrue('3rd' in error.to_dict()['1st']['2nd'])
        self.assertTrue('4th' in error.to_dict()['1st']['2nd']['3rd'])
        self.assertEqual(error.to_dict()['1st']['2nd']['3rd']['4th'],
                         'Inception')

        self.assertEqual(error.message, "root(2nd.3rd.4th.Inception: ['1st'])")

    def test_model_validation(self):

        class User(Document):
            username = StringField(primary_key=True)
            name = StringField(required=True)

        try:
            User().validate()
        except ValidationError, e:
            self.assertTrue("User:None" in e.message)
            self.assertEqual(e.to_dict(), {
                'username': 'Field is required',
                'name': 'Field is required'})

        user = User(username="RossC0", name="Ross").save()
        user.name = None
        try:
            user.save()
        except ValidationError, e:
            self.assertTrue("User:RossC0" in e.message)
            self.assertEqual(e.to_dict(), {
                'name': 'Field is required'})

    def test_fields_rewrite(self):
        class BasePerson(Document):
            name = StringField()
            age = IntField()
            meta = {'abstract': True}

        class Person(BasePerson):
            name = StringField(required=True)

        p = Person(age=15)
        self.assertRaises(ValidationError, p.validate)

    def test_embedded_document_validation(self):
        """Ensure that embedded documents may be validated.
        """
        class Comment(EmbeddedDocument):
            date = DateTimeField()
            content = StringField(required=True)

        comment = Comment()
        self.assertRaises(ValidationError, comment.validate)

        comment.content = 'test'
        comment.validate()

        comment.date = 4
        self.assertRaises(ValidationError, comment.validate)

        comment.date = datetime.now()
        comment.validate()
        self.assertEqual(comment._instance, None)

    def test_embedded_db_field_validate(self):

        class SubDoc(EmbeddedDocument):
            val = IntField(required=True)

        class Doc(Document):
            id = StringField(primary_key=True)
            e = EmbeddedDocumentField(SubDoc, db_field='eb')

        try:
            Doc(id="bad").validate()
        except ValidationError, e:
            self.assertTrue("SubDoc:None" in e.message)
            self.assertEqual(e.to_dict(), {
                "e": {'val': 'OK could not be converted to int'}})

        Doc.drop_collection()

        Doc(id="test", e=SubDoc(val=15)).save()

        doc = Doc.objects.first()
        keys = doc._data.keys()
        self.assertEqual(2, len(keys))
        self.assertTrue('e' in keys)
        self.assertTrue('id' in keys)

        doc.e.val = "OK"
        try:
            doc.save()
        except ValidationError, e:
            self.assertTrue("Doc:test" in e.message)
            self.assertEqual(e.to_dict(), {
                "e": {'val': 'OK could not be converted to int'}})


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = fields
# -*- coding: utf-8 -*-
import sys
sys.path[0:0] = [""]

import datetime
import unittest
import uuid

try:
    import dateutil
except ImportError:
    dateutil = None

from decimal import Decimal

from bson import Binary, DBRef, ObjectId

from mongoengine import *
from mongoengine.connection import get_db
from mongoengine.base import _document_registry
from mongoengine.errors import NotRegistered
from mongoengine.python_support import PY3, b, bin_type

__all__ = ("FieldTest", )


class FieldTest(unittest.TestCase):

    def setUp(self):
        connect(db='mongoenginetest')
        self.db = get_db()

    def tearDown(self):
        self.db.drop_collection('fs.files')
        self.db.drop_collection('fs.chunks')

    def test_default_values_nothing_set(self):
        """Ensure that default field values are used when creating a document.
        """
        class Person(Document):
            name = StringField()
            age = IntField(default=30, required=False)
            userid = StringField(default=lambda: 'test', required=True)
            created = DateTimeField(default=datetime.datetime.utcnow)

        person = Person(name="Ross")

        # Confirm saving now would store values
        data_to_be_saved = sorted(person.to_mongo().keys())
        self.assertEqual(data_to_be_saved, ['age', 'created', 'name', 'userid'])

        self.assertTrue(person.validate() is None)

        self.assertEqual(person.name, person.name)
        self.assertEqual(person.age, person.age)
        self.assertEqual(person.userid, person.userid)
        self.assertEqual(person.created, person.created)

        self.assertEqual(person._data['name'], person.name)
        self.assertEqual(person._data['age'], person.age)
        self.assertEqual(person._data['userid'], person.userid)
        self.assertEqual(person._data['created'], person.created)

        # Confirm introspection changes nothing
        data_to_be_saved = sorted(person.to_mongo().keys())
        self.assertEqual(data_to_be_saved, ['age', 'created', 'name', 'userid'])

    def test_default_values_set_to_None(self):
        """Ensure that default field values are used when creating a document.
        """
        class Person(Document):
            name = StringField()
            age = IntField(default=30, required=False)
            userid = StringField(default=lambda: 'test', required=True)
            created = DateTimeField(default=datetime.datetime.utcnow)

        # Trying setting values to None
        person = Person(name=None, age=None, userid=None, created=None)

        # Confirm saving now would store values
        data_to_be_saved = sorted(person.to_mongo().keys())
        self.assertEqual(data_to_be_saved, ['age', 'created', 'userid'])

        self.assertTrue(person.validate() is None)

        self.assertEqual(person.name, person.name)
        self.assertEqual(person.age, person.age)
        self.assertEqual(person.userid, person.userid)
        self.assertEqual(person.created, person.created)

        self.assertEqual(person._data['name'], person.name)
        self.assertEqual(person._data['age'], person.age)
        self.assertEqual(person._data['userid'], person.userid)
        self.assertEqual(person._data['created'], person.created)

        # Confirm introspection changes nothing
        data_to_be_saved = sorted(person.to_mongo().keys())
        self.assertEqual(data_to_be_saved, ['age', 'created', 'userid'])

    def test_default_values_when_setting_to_None(self):
        """Ensure that default field values are used when creating a document.
        """
        class Person(Document):
            name = StringField()
            age = IntField(default=30, required=False)
            userid = StringField(default=lambda: 'test', required=True)
            created = DateTimeField(default=datetime.datetime.utcnow)

        person = Person()
        person.name = None
        person.age = None
        person.userid = None
        person.created = None

        # Confirm saving now would store values
        data_to_be_saved = sorted(person.to_mongo().keys())
        self.assertEqual(data_to_be_saved, ['age', 'created', 'userid'])

        self.assertTrue(person.validate() is None)

        self.assertEqual(person.name, person.name)
        self.assertEqual(person.age, person.age)
        self.assertEqual(person.userid, person.userid)
        self.assertEqual(person.created, person.created)

        self.assertEqual(person._data['name'], person.name)
        self.assertEqual(person._data['age'], person.age)
        self.assertEqual(person._data['userid'], person.userid)
        self.assertEqual(person._data['created'], person.created)

        # Confirm introspection changes nothing
        data_to_be_saved = sorted(person.to_mongo().keys())
        self.assertEqual(data_to_be_saved, ['age', 'created', 'userid'])

    def test_default_values_when_deleting_value(self):
        """Ensure that default field values are used when creating a document.
        """
        class Person(Document):
            name = StringField()
            age = IntField(default=30, required=False)
            userid = StringField(default=lambda: 'test', required=True)
            created = DateTimeField(default=datetime.datetime.utcnow)

        person = Person(name="Ross")
        del person.name
        del person.age
        del person.userid
        del person.created

        data_to_be_saved = sorted(person.to_mongo().keys())
        self.assertEqual(data_to_be_saved, ['age', 'created', 'userid'])

        self.assertTrue(person.validate() is None)

        self.assertEqual(person.name, person.name)
        self.assertEqual(person.age, person.age)
        self.assertEqual(person.userid, person.userid)
        self.assertEqual(person.created, person.created)

        self.assertEqual(person._data['name'], person.name)
        self.assertEqual(person._data['age'], person.age)
        self.assertEqual(person._data['userid'], person.userid)
        self.assertEqual(person._data['created'], person.created)

        # Confirm introspection changes nothing
        data_to_be_saved = sorted(person.to_mongo().keys())
        self.assertEqual(data_to_be_saved, ['age', 'created', 'userid'])

    def test_required_values(self):
        """Ensure that required field constraints are enforced.
        """
        class Person(Document):
            name = StringField(required=True)
            age = IntField(required=True)
            userid = StringField()

        person = Person(name="Test User")
        self.assertRaises(ValidationError, person.validate)
        person = Person(age=30)
        self.assertRaises(ValidationError, person.validate)

    def test_not_required_handles_none_in_update(self):
        """Ensure that every fields should accept None if required is False.
        """

        class HandleNoneFields(Document):
            str_fld = StringField()
            int_fld = IntField()
            flt_fld = FloatField()
            comp_dt_fld = ComplexDateTimeField()

        HandleNoneFields.drop_collection()

        doc = HandleNoneFields()
        doc.str_fld = u'spam ham egg'
        doc.int_fld = 42
        doc.flt_fld = 4.2
        doc.com_dt_fld = datetime.datetime.utcnow()
        doc.save()

        res = HandleNoneFields.objects(id=doc.id).update(
            set__str_fld=None,
            set__int_fld=None,
            set__flt_fld=None,
            set__comp_dt_fld=None,
        )
        self.assertEqual(res, 1)

        # Retrive data from db and verify it.
        ret = HandleNoneFields.objects.all()[0]
        self.assertEqual(ret.str_fld, None)
        self.assertEqual(ret.int_fld, None)
        self.assertEqual(ret.flt_fld, None)

        # Return current time if retrived value is None.
        self.assertTrue(isinstance(ret.comp_dt_fld, datetime.datetime))

    def test_not_required_handles_none_from_database(self):
        """Ensure that every fields can handle null values from the database.
        """

        class HandleNoneFields(Document):
            str_fld = StringField(required=True)
            int_fld = IntField(required=True)
            flt_fld = FloatField(required=True)
            comp_dt_fld = ComplexDateTimeField(required=True)

        HandleNoneFields.drop_collection()

        doc = HandleNoneFields()
        doc.str_fld = u'spam ham egg'
        doc.int_fld = 42
        doc.flt_fld = 4.2
        doc.com_dt_fld = datetime.datetime.utcnow()
        doc.save()

        collection = self.db[HandleNoneFields._get_collection_name()]
        obj = collection.update({"_id": doc.id}, {"$unset": {
            "str_fld": 1,
            "int_fld": 1,
            "flt_fld": 1,
            "comp_dt_fld": 1}
        })

        # Retrive data from db and verify it.
        ret = HandleNoneFields.objects.all()[0]

        self.assertEqual(ret.str_fld, None)
        self.assertEqual(ret.int_fld, None)
        self.assertEqual(ret.flt_fld, None)
        # Return current time if retrived value is None.
        self.assertTrue(isinstance(ret.comp_dt_fld, datetime.datetime))

        self.assertRaises(ValidationError, ret.validate)

    def test_int_and_float_ne_operator(self):
        class TestDocument(Document):
            int_fld = IntField()
            float_fld = FloatField()

        TestDocument.drop_collection()

        TestDocument(int_fld=None, float_fld=None).save()
        TestDocument(int_fld=1, float_fld=1).save()

        self.assertEqual(1, TestDocument.objects(int_fld__ne=None).count())
        self.assertEqual(1, TestDocument.objects(float_fld__ne=None).count())

    def test_long_ne_operator(self):
        class TestDocument(Document):
            long_fld = LongField()

        TestDocument.drop_collection()

        TestDocument(long_fld=None).save()
        TestDocument(long_fld=1).save()

        self.assertEqual(1, TestDocument.objects(long_fld__ne=None).count())

    def test_object_id_validation(self):
        """Ensure that invalid values cannot be assigned to string fields.
        """
        class Person(Document):
            name = StringField()

        person = Person(name='Test User')
        self.assertEqual(person.id, None)

        person.id = 47
        self.assertRaises(ValidationError, person.validate)

        person.id = 'abc'
        self.assertRaises(ValidationError, person.validate)

        person.id = '497ce96f395f2f052a494fd4'
        person.validate()

    def test_string_validation(self):
        """Ensure that invalid values cannot be assigned to string fields.
        """
        class Person(Document):
            name = StringField(max_length=20)
            userid = StringField(r'[0-9a-z_]+$')

        person = Person(name=34)
        self.assertRaises(ValidationError, person.validate)

        # Test regex validation on userid
        person = Person(userid='test.User')
        self.assertRaises(ValidationError, person.validate)

        person.userid = 'test_user'
        self.assertEqual(person.userid, 'test_user')
        person.validate()

        # Test max length validation on name
        person = Person(name='Name that is more than twenty characters')
        self.assertRaises(ValidationError, person.validate)

        person.name = 'Shorter name'
        person.validate()

    def test_url_validation(self):
        """Ensure that URLFields validate urls properly.
        """
        class Link(Document):
            url = URLField()

        link = Link()
        link.url = 'google'
        self.assertRaises(ValidationError, link.validate)

        link.url = 'http://www.google.com:8080'
        link.validate()

    def test_int_validation(self):
        """Ensure that invalid values cannot be assigned to int fields.
        """
        class Person(Document):
            age = IntField(min_value=0, max_value=110)

        person = Person()
        person.age = 50
        person.validate()

        person.age = -1
        self.assertRaises(ValidationError, person.validate)
        person.age = 120
        self.assertRaises(ValidationError, person.validate)
        person.age = 'ten'
        self.assertRaises(ValidationError, person.validate)

    def test_long_validation(self):
        """Ensure that invalid values cannot be assigned to long fields.
        """
        class TestDocument(Document):
            value = LongField(min_value=0, max_value=110)

        doc = TestDocument()
        doc.value = 50
        doc.validate()

        doc.value = -1
        self.assertRaises(ValidationError, doc.validate)
        doc.age = 120
        self.assertRaises(ValidationError, doc.validate)
        doc.age = 'ten'
        self.assertRaises(ValidationError, doc.validate)

    def test_float_validation(self):
        """Ensure that invalid values cannot be assigned to float fields.
        """
        class Person(Document):
            height = FloatField(min_value=0.1, max_value=3.5)

        person = Person()
        person.height = 1.89
        person.validate()

        person.height = '2.0'
        self.assertRaises(ValidationError, person.validate)
        person.height = 0.01
        self.assertRaises(ValidationError, person.validate)
        person.height = 4.0
        self.assertRaises(ValidationError, person.validate)

        person_2 = Person(height='something invalid')
        self.assertRaises(ValidationError, person_2.validate)

    def test_decimal_validation(self):
        """Ensure that invalid values cannot be assigned to decimal fields.
        """
        class Person(Document):
            height = DecimalField(min_value=Decimal('0.1'),
                                  max_value=Decimal('3.5'))

        Person.drop_collection()

        Person(height=Decimal('1.89')).save()
        person = Person.objects.first()
        self.assertEqual(person.height, Decimal('1.89'))

        person.height = '2.0'
        person.save()
        person.height = 0.01
        self.assertRaises(ValidationError, person.validate)
        person.height = Decimal('0.01')
        self.assertRaises(ValidationError, person.validate)
        person.height = Decimal('4.0')
        self.assertRaises(ValidationError, person.validate)
        person.height = 'something invalid'
        self.assertRaises(ValidationError, person.validate)

        person_2 = Person(height='something invalid')
        self.assertRaises(ValidationError, person_2.validate)

        Person.drop_collection()

    def test_decimal_comparison(self):

        class Person(Document):
            money = DecimalField()

        Person.drop_collection()

        Person(money=6).save()
        Person(money=8).save()
        Person(money=10).save()

        self.assertEqual(2, Person.objects(money__gt=Decimal("7")).count())
        self.assertEqual(2, Person.objects(money__gt=7).count())
        self.assertEqual(2, Person.objects(money__gt="7").count())

    def test_decimal_storage(self):
        class Person(Document):
            btc = DecimalField(precision=4)

        Person.drop_collection()
        Person(btc=10).save()
        Person(btc=10.1).save()
        Person(btc=10.11).save()
        Person(btc="10.111").save()
        Person(btc=Decimal("10.1111")).save()
        Person(btc=Decimal("10.11111")).save()

        # How its stored
        expected = [{'btc': 10.0}, {'btc': 10.1}, {'btc': 10.11},
                    {'btc': 10.111}, {'btc': 10.1111}, {'btc': 10.1111}]
        actual = list(Person.objects.exclude('id').as_pymongo())
        self.assertEqual(expected, actual)

        # How it comes out locally
        expected = [Decimal('10.0000'), Decimal('10.1000'), Decimal('10.1100'),
                    Decimal('10.1110'), Decimal('10.1111'), Decimal('10.1111')]
        actual = list(Person.objects().scalar('btc'))
        self.assertEqual(expected, actual)

    def test_boolean_validation(self):
        """Ensure that invalid values cannot be assigned to boolean fields.
        """
        class Person(Document):
            admin = BooleanField()

        person = Person()
        person.admin = True
        person.validate()

        person.admin = 2
        self.assertRaises(ValidationError, person.validate)
        person.admin = 'Yes'
        self.assertRaises(ValidationError, person.validate)

    def test_uuid_field_string(self):
        """Test UUID fields storing as String
        """
        class Person(Document):
            api_key = UUIDField(binary=False)

        Person.drop_collection()

        uu = uuid.uuid4()
        Person(api_key=uu).save()
        self.assertEqual(1, Person.objects(api_key=uu).count())
        self.assertEqual(uu, Person.objects.first().api_key)

        person = Person()
        valid = (uuid.uuid4(), uuid.uuid1())
        for api_key in valid:
            person.api_key = api_key
            person.validate()

        invalid = ('9d159858-549b-4975-9f98-dd2f987c113g',
                   '9d159858-549b-4975-9f98-dd2f987c113')
        for api_key in invalid:
            person.api_key = api_key
            self.assertRaises(ValidationError, person.validate)

    def test_uuid_field_binary(self):
        """Test UUID fields storing as Binary object
        """
        class Person(Document):
            api_key = UUIDField(binary=True)

        Person.drop_collection()

        uu = uuid.uuid4()
        Person(api_key=uu).save()
        self.assertEqual(1, Person.objects(api_key=uu).count())
        self.assertEqual(uu, Person.objects.first().api_key)

        person = Person()
        valid = (uuid.uuid4(), uuid.uuid1())
        for api_key in valid:
            person.api_key = api_key
            person.validate()

        invalid = ('9d159858-549b-4975-9f98-dd2f987c113g',
                   '9d159858-549b-4975-9f98-dd2f987c113')
        for api_key in invalid:
            person.api_key = api_key
            self.assertRaises(ValidationError, person.validate)

    def test_datetime_validation(self):
        """Ensure that invalid values cannot be assigned to datetime fields.
        """
        class LogEntry(Document):
            time = DateTimeField()

        log = LogEntry()
        log.time = datetime.datetime.now()
        log.validate()

        log.time = datetime.date.today()
        log.validate()

        log.time = datetime.datetime.now().isoformat(' ')
        log.validate()

        if dateutil:
            log.time = datetime.datetime.now().isoformat('T')
            log.validate()

        log.time = -1
        self.assertRaises(ValidationError, log.validate)
        log.time = 'ABC'
        self.assertRaises(ValidationError, log.validate)

    def test_datetime_tz_aware_mark_as_changed(self):
        from mongoengine import connection

        # Reset the connections
        connection._connection_settings = {}
        connection._connections = {}
        connection._dbs = {}

        connect(db='mongoenginetest', tz_aware=True)

        class LogEntry(Document):
            time = DateTimeField()

        LogEntry.drop_collection()

        LogEntry(time=datetime.datetime(2013, 1, 1, 0, 0, 0)).save()

        log = LogEntry.objects.first()
        log.time = datetime.datetime(2013, 1, 1, 0, 0, 0)
        self.assertEqual(['time'], log._changed_fields)

    def test_datetime(self):
        """Tests showing pymongo datetime fields handling of microseconds.
        Microseconds are rounded to the nearest millisecond and pre UTC
        handling is wonky.

        See: http://api.mongodb.org/python/current/api/bson/son.html#dt
        """
        class LogEntry(Document):
            date = DateTimeField()

        LogEntry.drop_collection()

        # Test can save dates
        log = LogEntry()
        log.date = datetime.date.today()
        log.save()
        log.reload()
        self.assertEqual(log.date.date(), datetime.date.today())

        LogEntry.drop_collection()

        # Post UTC - microseconds are rounded (down) nearest millisecond and dropped
        d1 = datetime.datetime(1970, 01, 01, 00, 00, 01, 999)
        d2 = datetime.datetime(1970, 01, 01, 00, 00, 01)
        log = LogEntry()
        log.date = d1
        log.save()
        log.reload()
        self.assertNotEqual(log.date, d1)
        self.assertEqual(log.date, d2)

        # Post UTC - microseconds are rounded (down) nearest millisecond
        d1 = datetime.datetime(1970, 01, 01, 00, 00, 01, 9999)
        d2 = datetime.datetime(1970, 01, 01, 00, 00, 01, 9000)
        log.date = d1
        log.save()
        log.reload()
        self.assertNotEqual(log.date, d1)
        self.assertEqual(log.date, d2)

        if not PY3:
            # Pre UTC dates microseconds below 1000 are dropped
            # This does not seem to be true in PY3
            d1 = datetime.datetime(1969, 12, 31, 23, 59, 59, 999)
            d2 = datetime.datetime(1969, 12, 31, 23, 59, 59)
            log.date = d1
            log.save()
            log.reload()
            self.assertNotEqual(log.date, d1)
            self.assertEqual(log.date, d2)

        LogEntry.drop_collection()

    def test_datetime_usage(self):
        """Tests for regular datetime fields"""
        class LogEntry(Document):
            date = DateTimeField()

        LogEntry.drop_collection()

        d1 = datetime.datetime(1970, 01, 01, 00, 00, 01)
        log = LogEntry()
        log.date = d1
        log.validate()
        log.save()

        for query in (d1, d1.isoformat(' ')):
            log1 = LogEntry.objects.get(date=query)
            self.assertEqual(log, log1)

        if dateutil:
            log1 = LogEntry.objects.get(date=d1.isoformat('T'))
            self.assertEqual(log, log1)

        LogEntry.drop_collection()

        # create 60 log entries
        for i in xrange(1950, 2010):
            d = datetime.datetime(i, 01, 01, 00, 00, 01)
            LogEntry(date=d).save()

        self.assertEqual(LogEntry.objects.count(), 60)

        # Test ordering
        logs = LogEntry.objects.order_by("date")
        count = logs.count()
        i = 0
        while i == count - 1:
            self.assertTrue(logs[i].date <= logs[i + 1].date)
            i += 1

        logs = LogEntry.objects.order_by("-date")
        count = logs.count()
        i = 0
        while i == count - 1:
            self.assertTrue(logs[i].date >= logs[i + 1].date)
            i += 1

        # Test searching
        logs = LogEntry.objects.filter(date__gte=datetime.datetime(1980, 1, 1))
        self.assertEqual(logs.count(), 30)

        logs = LogEntry.objects.filter(date__lte=datetime.datetime(1980, 1, 1))
        self.assertEqual(logs.count(), 30)

        logs = LogEntry.objects.filter(
            date__lte=datetime.datetime(2011, 1, 1),
            date__gte=datetime.datetime(2000, 1, 1),
        )
        self.assertEqual(logs.count(), 10)

        LogEntry.drop_collection()

    def test_complexdatetime_storage(self):
        """Tests for complex datetime fields - which can handle microseconds
        without rounding.
        """
        class LogEntry(Document):
            date = ComplexDateTimeField()

        LogEntry.drop_collection()

        # Post UTC - microseconds are rounded (down) nearest millisecond and dropped - with default datetimefields
        d1 = datetime.datetime(1970, 01, 01, 00, 00, 01, 999)
        log = LogEntry()
        log.date = d1
        log.save()
        log.reload()
        self.assertEqual(log.date, d1)

        # Post UTC - microseconds are rounded (down) nearest millisecond - with default datetimefields
        d1 = datetime.datetime(1970, 01, 01, 00, 00, 01, 9999)
        log.date = d1
        log.save()
        log.reload()
        self.assertEqual(log.date, d1)

        # Pre UTC dates microseconds below 1000 are dropped - with default datetimefields
        d1 = datetime.datetime(1969, 12, 31, 23, 59, 59, 999)
        log.date = d1
        log.save()
        log.reload()
        self.assertEqual(log.date, d1)

        # Pre UTC microseconds above 1000 is wonky - with default datetimefields
        # log.date has an invalid microsecond value so I can't construct
        # a date to compare.
        for i in xrange(1001, 3113, 33):
            d1 = datetime.datetime(1969, 12, 31, 23, 59, 59, i)
            log.date = d1
            log.save()
            log.reload()
            self.assertEqual(log.date, d1)
            log1 = LogEntry.objects.get(date=d1)
            self.assertEqual(log, log1)

        LogEntry.drop_collection()

    def test_complexdatetime_usage(self):
        """Tests for complex datetime fields - which can handle microseconds
        without rounding.
        """
        class LogEntry(Document):
            date = ComplexDateTimeField()

        LogEntry.drop_collection()

        d1 = datetime.datetime(1970, 01, 01, 00, 00, 01, 999)
        log = LogEntry()
        log.date = d1
        log.save()

        log1 = LogEntry.objects.get(date=d1)
        self.assertEqual(log, log1)

        LogEntry.drop_collection()

        # create 60 log entries
        for i in xrange(1950, 2010):
            d = datetime.datetime(i, 01, 01, 00, 00, 01, 999)
            LogEntry(date=d).save()

        self.assertEqual(LogEntry.objects.count(), 60)

        # Test ordering
        logs = LogEntry.objects.order_by("date")
        count = logs.count()
        i = 0
        while i == count - 1:
            self.assertTrue(logs[i].date <= logs[i + 1].date)
            i += 1

        logs = LogEntry.objects.order_by("-date")
        count = logs.count()
        i = 0
        while i == count - 1:
            self.assertTrue(logs[i].date >= logs[i + 1].date)
            i += 1

        # Test searching
        logs = LogEntry.objects.filter(date__gte=datetime.datetime(1980, 1, 1))
        self.assertEqual(logs.count(), 30)

        logs = LogEntry.objects.filter(date__lte=datetime.datetime(1980, 1, 1))
        self.assertEqual(logs.count(), 30)

        logs = LogEntry.objects.filter(
            date__lte=datetime.datetime(2011, 1, 1),
            date__gte=datetime.datetime(2000, 1, 1),
        )
        self.assertEqual(logs.count(), 10)

        LogEntry.drop_collection()

    def test_list_validation(self):
        """Ensure that a list field only accepts lists with valid elements.
        """
        class User(Document):
            pass

        class Comment(EmbeddedDocument):
            content = StringField()

        class BlogPost(Document):
            content = StringField()
            comments = ListField(EmbeddedDocumentField(Comment))
            tags = ListField(StringField())
            authors = ListField(ReferenceField(User))
            generic = ListField(GenericReferenceField())

        post = BlogPost(content='Went for a walk today...')
        post.validate()

        post.tags = 'fun'
        self.assertRaises(ValidationError, post.validate)
        post.tags = [1, 2]
        self.assertRaises(ValidationError, post.validate)

        post.tags = ['fun', 'leisure']
        post.validate()
        post.tags = ('fun', 'leisure')
        post.validate()

        post.comments = ['a']
        self.assertRaises(ValidationError, post.validate)
        post.comments = 'yay'
        self.assertRaises(ValidationError, post.validate)

        comments = [Comment(content='Good for you'), Comment(content='Yay.')]
        post.comments = comments
        post.validate()

        post.authors = [Comment()]
        self.assertRaises(ValidationError, post.validate)

        post.authors = [User()]
        self.assertRaises(ValidationError, post.validate)

        user = User()
        user.save()
        post.authors = [user]
        post.validate()

        post.generic = [1, 2]
        self.assertRaises(ValidationError, post.validate)

        post.generic = [User(), Comment()]
        self.assertRaises(ValidationError, post.validate)

        post.generic = [Comment()]
        self.assertRaises(ValidationError, post.validate)

        post.generic = [user]
        post.validate()

        User.drop_collection()
        BlogPost.drop_collection()

    def test_sorted_list_sorting(self):
        """Ensure that a sorted list field properly sorts values.
        """
        class Comment(EmbeddedDocument):
            order = IntField()
            content = StringField()

        class BlogPost(Document):
            content = StringField()
            comments = SortedListField(EmbeddedDocumentField(Comment),
                                       ordering='order')
            tags = SortedListField(StringField())

        post = BlogPost(content='Went for a walk today...')
        post.save()

        post.tags = ['leisure', 'fun']
        post.save()
        post.reload()
        self.assertEqual(post.tags, ['fun', 'leisure'])

        comment1 = Comment(content='Good for you', order=1)
        comment2 = Comment(content='Yay.', order=0)
        comments = [comment1, comment2]
        post.comments = comments
        post.save()
        post.reload()
        self.assertEqual(post.comments[0].content, comment2.content)
        self.assertEqual(post.comments[1].content, comment1.content)

        BlogPost.drop_collection()

    def test_reverse_list_sorting(self):
        '''Ensure that a reverse sorted list field properly sorts values'''

        class Category(EmbeddedDocument):
            count = IntField()
            name = StringField()

        class CategoryList(Document):
            categories = SortedListField(EmbeddedDocumentField(Category),
                                         ordering='count', reverse=True)
            name = StringField()

        catlist = CategoryList(name="Top categories")
        cat1 = Category(name='posts', count=10)
        cat2 = Category(name='food', count=100)
        cat3 = Category(name='drink', count=40)
        catlist.categories = [cat1, cat2, cat3]
        catlist.save()
        catlist.reload()

        self.assertEqual(catlist.categories[0].name, cat2.name)
        self.assertEqual(catlist.categories[1].name, cat3.name)
        self.assertEqual(catlist.categories[2].name, cat1.name)

        CategoryList.drop_collection()

    def test_list_field(self):
        """Ensure that list types work as expected.
        """
        class BlogPost(Document):
            info = ListField()

        BlogPost.drop_collection()

        post = BlogPost()
        post.info = 'my post'
        self.assertRaises(ValidationError, post.validate)

        post.info = {'title': 'test'}
        self.assertRaises(ValidationError, post.validate)

        post.info = ['test']
        post.save()

        post = BlogPost()
        post.info = [{'test': 'test'}]
        post.save()

        post = BlogPost()
        post.info = [{'test': 3}]
        post.save()

        self.assertEqual(BlogPost.objects.count(), 3)
        self.assertEqual(BlogPost.objects.filter(info__exact='test').count(), 1)
        self.assertEqual(BlogPost.objects.filter(info__0__test='test').count(), 1)

        # Confirm handles non strings or non existing keys
        self.assertEqual(BlogPost.objects.filter(info__0__test__exact='5').count(), 0)
        self.assertEqual(BlogPost.objects.filter(info__100__test__exact='test').count(), 0)
        BlogPost.drop_collection()

    def test_list_field_passed_in_value(self):
        class Foo(Document):
            bars = ListField(ReferenceField("Bar"))

        class Bar(Document):
            text = StringField()

        bar = Bar(text="hi")
        bar.save()

        foo = Foo(bars=[])
        foo.bars.append(bar)
        self.assertEqual(repr(foo.bars), '[<Bar: Bar object>]')


    def test_list_field_strict(self):
        """Ensure that list field handles validation if provided a strict field type."""

        class Simple(Document):
            mapping = ListField(field=IntField())

        Simple.drop_collection()

        e = Simple()
        e.mapping = [1]
        e.save()

        def create_invalid_mapping():
            e.mapping = ["abc"]
            e.save()

        self.assertRaises(ValidationError, create_invalid_mapping)

        Simple.drop_collection()

    def test_list_field_rejects_strings(self):
        """Strings aren't valid list field data types"""

        class Simple(Document):
            mapping = ListField()

        Simple.drop_collection()
        e = Simple()
        e.mapping = 'hello world'

        self.assertRaises(ValidationError, e.save)

    def test_complex_field_required(self):
        """Ensure required cant be None / Empty"""

        class Simple(Document):
            mapping = ListField(required=True)

        Simple.drop_collection()
        e = Simple()
        e.mapping = []

        self.assertRaises(ValidationError, e.save)

        class Simple(Document):
            mapping = DictField(required=True)

        Simple.drop_collection()
        e = Simple()
        e.mapping = {}

        self.assertRaises(ValidationError, e.save)

    def test_complex_field_same_value_not_changed(self):
        """
        If a complex field is set to the same value, it should not be marked as
        changed.
        """
        class Simple(Document):
            mapping = ListField()

        Simple.drop_collection()
        e = Simple().save()
        e.mapping = []
        self.assertEqual([], e._changed_fields)

        class Simple(Document):
            mapping = DictField()

        Simple.drop_collection()
        e = Simple().save()
        e.mapping = {}
        self.assertEqual([], e._changed_fields)

    def test_slice_marks_field_as_changed(self):

        class Simple(Document):
            widgets = ListField()

        simple = Simple(widgets=[1, 2, 3, 4]).save()
        simple.widgets[:3] = []
        self.assertEqual(['widgets'], simple._changed_fields)
        simple.save()

        simple = simple.reload()
        self.assertEqual(simple.widgets, [4])

    def test_del_slice_marks_field_as_changed(self):

        class Simple(Document):
            widgets = ListField()

        simple = Simple(widgets=[1, 2, 3, 4]).save()
        del simple.widgets[:3]
        self.assertEqual(['widgets'], simple._changed_fields)
        simple.save()

        simple = simple.reload()
        self.assertEqual(simple.widgets, [4])

    def test_list_field_complex(self):
        """Ensure that the list fields can handle the complex types."""

        class SettingBase(EmbeddedDocument):
            meta = {'allow_inheritance': True}

        class StringSetting(SettingBase):
            value = StringField()

        class IntegerSetting(SettingBase):
            value = IntField()

        class Simple(Document):
            mapping = ListField()

        Simple.drop_collection()
        e = Simple()
        e.mapping.append(StringSetting(value='foo'))
        e.mapping.append(IntegerSetting(value=42))
        e.mapping.append({'number': 1, 'string': 'Hi!', 'float': 1.001,
                          'complex': IntegerSetting(value=42),
                          'list': [IntegerSetting(value=42),
                                   StringSetting(value='foo')]})
        e.save()

        e2 = Simple.objects.get(id=e.id)
        self.assertTrue(isinstance(e2.mapping[0], StringSetting))
        self.assertTrue(isinstance(e2.mapping[1], IntegerSetting))

        # Test querying
        self.assertEqual(Simple.objects.filter(mapping__1__value=42).count(), 1)
        self.assertEqual(Simple.objects.filter(mapping__2__number=1).count(), 1)
        self.assertEqual(Simple.objects.filter(mapping__2__complex__value=42).count(), 1)
        self.assertEqual(Simple.objects.filter(mapping__2__list__0__value=42).count(), 1)
        self.assertEqual(Simple.objects.filter(mapping__2__list__1__value='foo').count(), 1)

        # Confirm can update
        Simple.objects().update(set__mapping__1=IntegerSetting(value=10))
        self.assertEqual(Simple.objects.filter(mapping__1__value=10).count(), 1)

        Simple.objects().update(
            set__mapping__2__list__1=StringSetting(value='Boo'))
        self.assertEqual(Simple.objects.filter(mapping__2__list__1__value='foo').count(), 0)
        self.assertEqual(Simple.objects.filter(mapping__2__list__1__value='Boo').count(), 1)

        Simple.drop_collection()

    def test_dict_field(self):
        """Ensure that dict types work as expected.
        """
        class BlogPost(Document):
            info = DictField()

        BlogPost.drop_collection()

        post = BlogPost()
        post.info = 'my post'
        self.assertRaises(ValidationError, post.validate)

        post.info = ['test', 'test']
        self.assertRaises(ValidationError, post.validate)

        post.info = {'$title': 'test'}
        self.assertRaises(ValidationError, post.validate)

        post.info = {'nested': {'$title': 'test'}}
        self.assertRaises(ValidationError, post.validate)

        post.info = {'the.title': 'test'}
        self.assertRaises(ValidationError, post.validate)

        post.info = {'nested': {'the.title': 'test'}}
        self.assertRaises(ValidationError, post.validate)

        post.info = {1: 'test'}
        self.assertRaises(ValidationError, post.validate)

        post.info = {'title': 'test'}
        post.save()

        post = BlogPost()
        post.info = {'details': {'test': 'test'}}
        post.save()

        post = BlogPost()
        post.info = {'details': {'test': 3}}
        post.save()

        self.assertEqual(BlogPost.objects.count(), 3)
        self.assertEqual(BlogPost.objects.filter(info__title__exact='test').count(), 1)
        self.assertEqual(BlogPost.objects.filter(info__details__test__exact='test').count(), 1)

        # Confirm handles non strings or non existing keys
        self.assertEqual(BlogPost.objects.filter(info__details__test__exact=5).count(), 0)
        self.assertEqual(BlogPost.objects.filter(info__made_up__test__exact='test').count(), 0)

        post = BlogPost.objects.create(info={'title': 'original'})
        post.info.update({'title': 'updated'})
        post.save()
        post.reload()
        self.assertEqual('updated', post.info['title'])

        BlogPost.drop_collection()

    def test_dictfield_strict(self):
        """Ensure that dict field handles validation if provided a strict field type."""

        class Simple(Document):
            mapping = DictField(field=IntField())

        Simple.drop_collection()

        e = Simple()
        e.mapping['someint'] = 1
        e.save()

        def create_invalid_mapping():
            e.mapping['somestring'] = "abc"
            e.save()

        self.assertRaises(ValidationError, create_invalid_mapping)

        Simple.drop_collection()

    def test_dictfield_complex(self):
        """Ensure that the dict field can handle the complex types."""

        class SettingBase(EmbeddedDocument):
            meta = {'allow_inheritance': True}

        class StringSetting(SettingBase):
            value = StringField()

        class IntegerSetting(SettingBase):
            value = IntField()

        class Simple(Document):
            mapping = DictField()

        Simple.drop_collection()
        e = Simple()
        e.mapping['somestring'] = StringSetting(value='foo')
        e.mapping['someint'] = IntegerSetting(value=42)
        e.mapping['nested_dict'] = {'number': 1, 'string': 'Hi!',
                                    'float': 1.001,
                                    'complex': IntegerSetting(value=42),
                                    'list': [IntegerSetting(value=42),
                                             StringSetting(value='foo')]}
        e.save()

        e2 = Simple.objects.get(id=e.id)
        self.assertTrue(isinstance(e2.mapping['somestring'], StringSetting))
        self.assertTrue(isinstance(e2.mapping['someint'], IntegerSetting))

        # Test querying
        self.assertEqual(Simple.objects.filter(mapping__someint__value=42).count(), 1)
        self.assertEqual(Simple.objects.filter(mapping__nested_dict__number=1).count(), 1)
        self.assertEqual(Simple.objects.filter(mapping__nested_dict__complex__value=42).count(), 1)
        self.assertEqual(Simple.objects.filter(mapping__nested_dict__list__0__value=42).count(), 1)
        self.assertEqual(Simple.objects.filter(mapping__nested_dict__list__1__value='foo').count(), 1)

        # Confirm can update
        Simple.objects().update(
            set__mapping={"someint": IntegerSetting(value=10)})
        Simple.objects().update(
            set__mapping__nested_dict__list__1=StringSetting(value='Boo'))
        self.assertEqual(Simple.objects.filter(mapping__nested_dict__list__1__value='foo').count(), 0)
        self.assertEqual(Simple.objects.filter(mapping__nested_dict__list__1__value='Boo').count(), 1)

        Simple.drop_collection()

    def test_mapfield(self):
        """Ensure that the MapField handles the declared type."""

        class Simple(Document):
            mapping = MapField(IntField())

        Simple.drop_collection()

        e = Simple()
        e.mapping['someint'] = 1
        e.save()

        def create_invalid_mapping():
            e.mapping['somestring'] = "abc"
            e.save()

        self.assertRaises(ValidationError, create_invalid_mapping)

        def create_invalid_class():
            class NoDeclaredType(Document):
                mapping = MapField()

        self.assertRaises(ValidationError, create_invalid_class)

        Simple.drop_collection()

    def test_complex_mapfield(self):
        """Ensure that the MapField can handle complex declared types."""

        class SettingBase(EmbeddedDocument):
            meta = {"allow_inheritance": True}

        class StringSetting(SettingBase):
            value = StringField()

        class IntegerSetting(SettingBase):
            value = IntField()

        class Extensible(Document):
            mapping = MapField(EmbeddedDocumentField(SettingBase))

        Extensible.drop_collection()

        e = Extensible()
        e.mapping['somestring'] = StringSetting(value='foo')
        e.mapping['someint'] = IntegerSetting(value=42)
        e.save()

        e2 = Extensible.objects.get(id=e.id)
        self.assertTrue(isinstance(e2.mapping['somestring'], StringSetting))
        self.assertTrue(isinstance(e2.mapping['someint'], IntegerSetting))

        def create_invalid_mapping():
            e.mapping['someint'] = 123
            e.save()

        self.assertRaises(ValidationError, create_invalid_mapping)

        Extensible.drop_collection()

    def test_embedded_mapfield_db_field(self):

        class Embedded(EmbeddedDocument):
            number = IntField(default=0, db_field='i')

        class Test(Document):
            my_map = MapField(field=EmbeddedDocumentField(Embedded),
                                    db_field='x')

        Test.drop_collection()

        test = Test()
        test.my_map['DICTIONARY_KEY'] = Embedded(number=1)
        test.save()

        Test.objects.update_one(inc__my_map__DICTIONARY_KEY__number=1)

        test = Test.objects.get()
        self.assertEqual(test.my_map['DICTIONARY_KEY'].number, 2)
        doc = self.db.test.find_one()
        self.assertEqual(doc['x']['DICTIONARY_KEY']['i'], 2)

    def test_mapfield_numerical_index(self):
        """Ensure that MapField accept numeric strings as indexes."""
        class Embedded(EmbeddedDocument):
            name = StringField()

        class Test(Document):
            my_map = MapField(EmbeddedDocumentField(Embedded))

        Test.drop_collection()

        test = Test()
        test.my_map['1'] = Embedded(name='test')
        test.save()
        test.my_map['1'].name = 'test updated'
        test.save()

        Test.drop_collection()

    def test_map_field_lookup(self):
        """Ensure MapField lookups succeed on Fields without a lookup method"""

        class Log(Document):
            name = StringField()
            visited = MapField(DateTimeField())

        Log.drop_collection()
        Log(name="wilson", visited={'friends': datetime.datetime.now()}).save()

        self.assertEqual(1, Log.objects(
                                visited__friends__exists=True).count())

    def test_embedded_db_field(self):

        class Embedded(EmbeddedDocument):
            number = IntField(default=0, db_field='i')

        class Test(Document):
            embedded = EmbeddedDocumentField(Embedded, db_field='x')

        Test.drop_collection()

        test = Test()
        test.embedded = Embedded(number=1)
        test.save()

        Test.objects.update_one(inc__embedded__number=1)

        test = Test.objects.get()
        self.assertEqual(test.embedded.number, 2)
        doc = self.db.test.find_one()
        self.assertEqual(doc['x']['i'], 2)

    def test_embedded_document_validation(self):
        """Ensure that invalid embedded documents cannot be assigned to
        embedded document fields.
        """
        class Comment(EmbeddedDocument):
            content = StringField()

        class PersonPreferences(EmbeddedDocument):
            food = StringField(required=True)
            number = IntField()

        class Person(Document):
            name = StringField()
            preferences = EmbeddedDocumentField(PersonPreferences)

        person = Person(name='Test User')
        person.preferences = 'My Preferences'
        self.assertRaises(ValidationError, person.validate)

        # Check that only the right embedded doc works
        person.preferences = Comment(content='Nice blog post...')
        self.assertRaises(ValidationError, person.validate)

        # Check that the embedded doc is valid
        person.preferences = PersonPreferences()
        self.assertRaises(ValidationError, person.validate)

        person.preferences = PersonPreferences(food='Cheese', number=47)
        self.assertEqual(person.preferences.food, 'Cheese')
        person.validate()

    def test_embedded_document_inheritance(self):
        """Ensure that subclasses of embedded documents may be provided to
        EmbeddedDocumentFields of the superclass' type.
        """
        class User(EmbeddedDocument):
            name = StringField()

            meta = {'allow_inheritance': True}

        class PowerUser(User):
            power = IntField()

        class BlogPost(Document):
            content = StringField()
            author = EmbeddedDocumentField(User)

        post = BlogPost(content='What I did today...')
        post.author = PowerUser(name='Test User', power=47)
        post.save()

        self.assertEqual(47, BlogPost.objects.first().author.power)

    def test_reference_validation(self):
        """Ensure that invalid docment objects cannot be assigned to reference
        fields.
        """
        class User(Document):
            name = StringField()

        class BlogPost(Document):
            content = StringField()
            author = ReferenceField(User)

        User.drop_collection()
        BlogPost.drop_collection()

        self.assertRaises(ValidationError, ReferenceField, EmbeddedDocument)

        user = User(name='Test User')

        # Ensure that the referenced object must have been saved
        post1 = BlogPost(content='Chips and gravy taste good.')
        post1.author = user
        self.assertRaises(ValidationError, post1.save)

        # Check that an invalid object type cannot be used
        post2 = BlogPost(content='Chips and chilli taste good.')
        post1.author = post2
        self.assertRaises(ValidationError, post1.validate)

        user.save()
        post1.author = user
        post1.save()

        post2.save()
        post1.author = post2
        self.assertRaises(ValidationError, post1.validate)

        User.drop_collection()
        BlogPost.drop_collection()

    def test_dbref_reference_fields(self):

        class Person(Document):
            name = StringField()
            parent = ReferenceField('self', dbref=True)

        Person.drop_collection()

        p1 = Person(name="John").save()
        Person(name="Ross", parent=p1).save()

        col = Person._get_collection()
        data = col.find_one({'name': 'Ross'})
        self.assertEqual(data['parent'], DBRef('person', p1.pk))

        p = Person.objects.get(name="Ross")
        self.assertEqual(p.parent, p1)

    def test_dbref_to_mongo(self):
        class Person(Document):
            name = StringField()
            parent = ReferenceField('self', dbref=False)

        p1 = Person._from_son({'name': "Yakxxx",
                               'parent': "50a234ea469ac1eda42d347d"})
        mongoed = p1.to_mongo()
        self.assertTrue(isinstance(mongoed['parent'], ObjectId))

    def test_objectid_reference_fields(self):

        class Person(Document):
            name = StringField()
            parent = ReferenceField('self', dbref=False)

        Person.drop_collection()

        p1 = Person(name="John").save()
        Person(name="Ross", parent=p1).save()

        col = Person._get_collection()
        data = col.find_one({'name': 'Ross'})
        self.assertEqual(data['parent'], p1.pk)

        p = Person.objects.get(name="Ross")
        self.assertEqual(p.parent, p1)

    def test_list_item_dereference(self):
        """Ensure that DBRef items in ListFields are dereferenced.
        """
        class User(Document):
            name = StringField()

        class Group(Document):
            members = ListField(ReferenceField(User))

        User.drop_collection()
        Group.drop_collection()

        user1 = User(name='user1')
        user1.save()
        user2 = User(name='user2')
        user2.save()

        group = Group(members=[user1, user2])
        group.save()

        group_obj = Group.objects.first()

        self.assertEqual(group_obj.members[0].name, user1.name)
        self.assertEqual(group_obj.members[1].name, user2.name)

        User.drop_collection()
        Group.drop_collection()

    def test_recursive_reference(self):
        """Ensure that ReferenceFields can reference their own documents.
        """
        class Employee(Document):
            name = StringField()
            boss = ReferenceField('self')
            friends = ListField(ReferenceField('self'))

        Employee.drop_collection()
        bill = Employee(name='Bill Lumbergh')
        bill.save()

        michael = Employee(name='Michael Bolton')
        michael.save()

        samir = Employee(name='Samir Nagheenanajar')
        samir.save()

        friends = [michael, samir]
        peter = Employee(name='Peter Gibbons', boss=bill, friends=friends)
        peter.save()

        peter = Employee.objects.with_id(peter.id)
        self.assertEqual(peter.boss, bill)
        self.assertEqual(peter.friends, friends)

    def test_recursive_embedding(self):
        """Ensure that EmbeddedDocumentFields can contain their own documents.
        """
        class Tree(Document):
            name = StringField()
            children = ListField(EmbeddedDocumentField('TreeNode'))

        class TreeNode(EmbeddedDocument):
            name = StringField()
            children = ListField(EmbeddedDocumentField('self'))

        Tree.drop_collection()
        tree = Tree(name="Tree")

        first_child = TreeNode(name="Child 1")
        tree.children.append(first_child)

        second_child = TreeNode(name="Child 2")
        first_child.children.append(second_child)
        tree.save()

        tree = Tree.objects.first()
        self.assertEqual(len(tree.children), 1)

        self.assertEqual(len(tree.children[0].children), 1)

        third_child = TreeNode(name="Child 3")
        tree.children[0].children.append(third_child)
        tree.save()

        self.assertEqual(len(tree.children), 1)
        self.assertEqual(tree.children[0].name, first_child.name)
        self.assertEqual(tree.children[0].children[0].name, second_child.name)
        self.assertEqual(tree.children[0].children[1].name, third_child.name)

        # Test updating
        tree.children[0].name = 'I am Child 1'
        tree.children[0].children[0].name = 'I am Child 2'
        tree.children[0].children[1].name = 'I am Child 3'
        tree.save()

        self.assertEqual(tree.children[0].name, 'I am Child 1')
        self.assertEqual(tree.children[0].children[0].name, 'I am Child 2')
        self.assertEqual(tree.children[0].children[1].name, 'I am Child 3')

        # Test removal
        self.assertEqual(len(tree.children[0].children), 2)
        del(tree.children[0].children[1])

        tree.save()
        self.assertEqual(len(tree.children[0].children), 1)

        tree.children[0].children.pop(0)
        tree.save()
        self.assertEqual(len(tree.children[0].children), 0)
        self.assertEqual(tree.children[0].children, [])

        tree.children[0].children.insert(0, third_child)
        tree.children[0].children.insert(0, second_child)
        tree.save()
        self.assertEqual(len(tree.children[0].children), 2)
        self.assertEqual(tree.children[0].children[0].name, second_child.name)
        self.assertEqual(tree.children[0].children[1].name, third_child.name)

    def test_undefined_reference(self):
        """Ensure that ReferenceFields may reference undefined Documents.
        """
        class Product(Document):
            name = StringField()
            company = ReferenceField('Company')

        class Company(Document):
            name = StringField()

        Product.drop_collection()
        Company.drop_collection()

        ten_gen = Company(name='10gen')
        ten_gen.save()
        mongodb = Product(name='MongoDB', company=ten_gen)
        mongodb.save()

        me = Product(name='MongoEngine')
        me.save()

        obj = Product.objects(company=ten_gen).first()
        self.assertEqual(obj, mongodb)
        self.assertEqual(obj.company, ten_gen)

        obj = Product.objects(company=None).first()
        self.assertEqual(obj, me)

        obj, created = Product.objects.get_or_create(company=None)

        self.assertEqual(created, False)
        self.assertEqual(obj, me)

    def test_reference_query_conversion(self):
        """Ensure that ReferenceFields can be queried using objects and values
        of the type of the primary key of the referenced object.
        """
        class Member(Document):
            user_num = IntField(primary_key=True)

        class BlogPost(Document):
            title = StringField()
            author = ReferenceField(Member, dbref=False)

        Member.drop_collection()
        BlogPost.drop_collection()

        m1 = Member(user_num=1)
        m1.save()
        m2 = Member(user_num=2)
        m2.save()

        post1 = BlogPost(title='post 1', author=m1)
        post1.save()

        post2 = BlogPost(title='post 2', author=m2)
        post2.save()

        post = BlogPost.objects(author=m1).first()
        self.assertEqual(post.id, post1.id)

        post = BlogPost.objects(author=m2).first()
        self.assertEqual(post.id, post2.id)

        Member.drop_collection()
        BlogPost.drop_collection()

    def test_reference_query_conversion_dbref(self):
        """Ensure that ReferenceFields can be queried using objects and values
        of the type of the primary key of the referenced object.
        """
        class Member(Document):
            user_num = IntField(primary_key=True)

        class BlogPost(Document):
            title = StringField()
            author = ReferenceField(Member, dbref=True)

        Member.drop_collection()
        BlogPost.drop_collection()

        m1 = Member(user_num=1)
        m1.save()
        m2 = Member(user_num=2)
        m2.save()

        post1 = BlogPost(title='post 1', author=m1)
        post1.save()

        post2 = BlogPost(title='post 2', author=m2)
        post2.save()

        post = BlogPost.objects(author=m1).first()
        self.assertEqual(post.id, post1.id)

        post = BlogPost.objects(author=m2).first()
        self.assertEqual(post.id, post2.id)

        Member.drop_collection()
        BlogPost.drop_collection()

    def test_generic_reference(self):
        """Ensure that a GenericReferenceField properly dereferences items.
        """
        class Link(Document):
            title = StringField()
            meta = {'allow_inheritance': False}

        class Post(Document):
            title = StringField()

        class Bookmark(Document):
            bookmark_object = GenericReferenceField()

        Link.drop_collection()
        Post.drop_collection()
        Bookmark.drop_collection()

        link_1 = Link(title="Pitchfork")
        link_1.save()

        post_1 = Post(title="Behind the Scenes of the Pavement Reunion")
        post_1.save()

        bm = Bookmark(bookmark_object=post_1)
        bm.save()

        bm = Bookmark.objects(bookmark_object=post_1).first()

        self.assertEqual(bm.bookmark_object, post_1)
        self.assertTrue(isinstance(bm.bookmark_object, Post))

        bm.bookmark_object = link_1
        bm.save()

        bm = Bookmark.objects(bookmark_object=link_1).first()

        self.assertEqual(bm.bookmark_object, link_1)
        self.assertTrue(isinstance(bm.bookmark_object, Link))

        Link.drop_collection()
        Post.drop_collection()
        Bookmark.drop_collection()

    def test_generic_reference_list(self):
        """Ensure that a ListField properly dereferences generic references.
        """
        class Link(Document):
            title = StringField()

        class Post(Document):
            title = StringField()

        class User(Document):
            bookmarks = ListField(GenericReferenceField())

        Link.drop_collection()
        Post.drop_collection()
        User.drop_collection()

        link_1 = Link(title="Pitchfork")
        link_1.save()

        post_1 = Post(title="Behind the Scenes of the Pavement Reunion")
        post_1.save()

        user = User(bookmarks=[post_1, link_1])
        user.save()

        user = User.objects(bookmarks__all=[post_1, link_1]).first()

        self.assertEqual(user.bookmarks[0], post_1)
        self.assertEqual(user.bookmarks[1], link_1)

        Link.drop_collection()
        Post.drop_collection()
        User.drop_collection()

    def test_generic_reference_document_not_registered(self):
        """Ensure dereferencing out of the document registry throws a
        `NotRegistered` error.
        """
        class Link(Document):
            title = StringField()

        class User(Document):
            bookmarks = ListField(GenericReferenceField())

        Link.drop_collection()
        User.drop_collection()

        link_1 = Link(title="Pitchfork")
        link_1.save()

        user = User(bookmarks=[link_1])
        user.save()

        # Mimic User and Link definitions being in a different file
        # and the Link model not being imported in the User file.
        del(_document_registry["Link"])

        user = User.objects.first()
        try:
            user.bookmarks
            raise AssertionError("Link was removed from the registry")
        except NotRegistered:
            pass

        Link.drop_collection()
        User.drop_collection()

    def test_generic_reference_is_none(self):

        class Person(Document):
            name = StringField()
            city = GenericReferenceField()

        Person.drop_collection()
        Person(name="Wilson Jr").save()

        self.assertEqual(repr(Person.objects(city=None)),
                            "[<Person: Person object>]")


    def test_generic_reference_choices(self):
        """Ensure that a GenericReferenceField can handle choices
        """
        class Link(Document):
            title = StringField()

        class Post(Document):
            title = StringField()

        class Bookmark(Document):
            bookmark_object = GenericReferenceField(choices=(Post,))

        Link.drop_collection()
        Post.drop_collection()
        Bookmark.drop_collection()

        link_1 = Link(title="Pitchfork")
        link_1.save()

        post_1 = Post(title="Behind the Scenes of the Pavement Reunion")
        post_1.save()

        bm = Bookmark(bookmark_object=link_1)
        self.assertRaises(ValidationError, bm.validate)

        bm = Bookmark(bookmark_object=post_1)
        bm.save()

        bm = Bookmark.objects.first()
        self.assertEqual(bm.bookmark_object, post_1)

    def test_generic_reference_list_choices(self):
        """Ensure that a ListField properly dereferences generic references and
        respects choices.
        """
        class Link(Document):
            title = StringField()

        class Post(Document):
            title = StringField()

        class User(Document):
            bookmarks = ListField(GenericReferenceField(choices=(Post,)))

        Link.drop_collection()
        Post.drop_collection()
        User.drop_collection()

        link_1 = Link(title="Pitchfork")
        link_1.save()

        post_1 = Post(title="Behind the Scenes of the Pavement Reunion")
        post_1.save()

        user = User(bookmarks=[link_1])
        self.assertRaises(ValidationError, user.validate)

        user = User(bookmarks=[post_1])
        user.save()

        user = User.objects.first()
        self.assertEqual(user.bookmarks, [post_1])

        Link.drop_collection()
        Post.drop_collection()
        User.drop_collection()

    def test_generic_reference_list_item_modification(self):
        """Ensure that modifications of related documents (through generic reference) don't influence on querying
        """
        class Post(Document):
            title = StringField()

        class User(Document):
            username = StringField()
            bookmarks = ListField(GenericReferenceField())

        Post.drop_collection()
        User.drop_collection()

        post_1 = Post(title="Behind the Scenes of the Pavement Reunion")
        post_1.save()

        user = User(bookmarks=[post_1])
        user.save()

        post_1.title = "Title was modified"
        user.username = "New username"
        user.save()

        user = User.objects(bookmarks__all=[post_1]).first()

        self.assertNotEqual(user, None)
        self.assertEqual(user.bookmarks[0], post_1)

        Post.drop_collection()
        User.drop_collection()

    def test_binary_fields(self):
        """Ensure that binary fields can be stored and retrieved.
        """
        class Attachment(Document):
            content_type = StringField()
            blob = BinaryField()

        BLOB = b('\xe6\x00\xc4\xff\x07')
        MIME_TYPE = 'application/octet-stream'

        Attachment.drop_collection()

        attachment = Attachment(content_type=MIME_TYPE, blob=BLOB)
        attachment.save()

        attachment_1 = Attachment.objects().first()
        self.assertEqual(MIME_TYPE, attachment_1.content_type)
        self.assertEqual(BLOB, bin_type(attachment_1.blob))

        Attachment.drop_collection()

    def test_binary_validation(self):
        """Ensure that invalid values cannot be assigned to binary fields.
        """
        class Attachment(Document):
            blob = BinaryField()

        class AttachmentRequired(Document):
            blob = BinaryField(required=True)

        class AttachmentSizeLimit(Document):
            blob = BinaryField(max_bytes=4)

        Attachment.drop_collection()
        AttachmentRequired.drop_collection()
        AttachmentSizeLimit.drop_collection()

        attachment = Attachment()
        attachment.validate()
        attachment.blob = 2
        self.assertRaises(ValidationError, attachment.validate)

        attachment_required = AttachmentRequired()
        self.assertRaises(ValidationError, attachment_required.validate)
        attachment_required.blob = Binary(b('\xe6\x00\xc4\xff\x07'))
        attachment_required.validate()

        attachment_size_limit = AttachmentSizeLimit(blob=b('\xe6\x00\xc4\xff\x07'))
        self.assertRaises(ValidationError, attachment_size_limit.validate)
        attachment_size_limit.blob = b('\xe6\x00\xc4\xff')
        attachment_size_limit.validate()

        Attachment.drop_collection()
        AttachmentRequired.drop_collection()
        AttachmentSizeLimit.drop_collection()

    def test_binary_field_primary(self):

        class Attachment(Document):
            id = BinaryField(primary_key=True)

        Attachment.drop_collection()

        att = Attachment(id=uuid.uuid4().bytes).save()
        att.delete()

        self.assertEqual(0, Attachment.objects.count())

    def test_choices_validation(self):
        """Ensure that value is in a container of allowed values.
        """
        class Shirt(Document):
            size = StringField(max_length=3, choices=(
                ('S', 'Small'), ('M', 'Medium'), ('L', 'Large'),
                ('XL', 'Extra Large'), ('XXL', 'Extra Extra Large')))

        Shirt.drop_collection()

        shirt = Shirt()
        shirt.validate()

        shirt.size = "S"
        shirt.validate()

        shirt.size = "XS"
        self.assertRaises(ValidationError, shirt.validate)

        Shirt.drop_collection()

    def test_choices_get_field_display(self):
        """Test dynamic helper for returning the display value of a choices
        field.
        """
        class Shirt(Document):
            size = StringField(max_length=3, choices=(
                    ('S', 'Small'), ('M', 'Medium'), ('L', 'Large'),
                    ('XL', 'Extra Large'), ('XXL', 'Extra Extra Large')))
            style = StringField(max_length=3, choices=(
                ('S', 'Small'), ('B', 'Baggy'), ('W', 'wide')), default='S')

        Shirt.drop_collection()

        shirt = Shirt()

        self.assertEqual(shirt.get_size_display(), None)
        self.assertEqual(shirt.get_style_display(), 'Small')

        shirt.size = "XXL"
        shirt.style = "B"
        self.assertEqual(shirt.get_size_display(), 'Extra Extra Large')
        self.assertEqual(shirt.get_style_display(), 'Baggy')

        # Set as Z - an invalid choice
        shirt.size = "Z"
        shirt.style = "Z"
        self.assertEqual(shirt.get_size_display(), 'Z')
        self.assertEqual(shirt.get_style_display(), 'Z')
        self.assertRaises(ValidationError, shirt.validate)

        Shirt.drop_collection()

    def test_simple_choices_validation(self):
        """Ensure that value is in a container of allowed values.
        """
        class Shirt(Document):
            size = StringField(max_length=3,
                              choices=('S', 'M', 'L', 'XL', 'XXL'))

        Shirt.drop_collection()

        shirt = Shirt()
        shirt.validate()

        shirt.size = "S"
        shirt.validate()

        shirt.size = "XS"
        self.assertRaises(ValidationError, shirt.validate)

        Shirt.drop_collection()

    def test_simple_choices_get_field_display(self):
        """Test dynamic helper for returning the display value of a choices
        field.
        """
        class Shirt(Document):
            size = StringField(max_length=3,
                               choices=('S', 'M', 'L', 'XL', 'XXL'))
            style = StringField(max_length=3,
                                choices=('Small', 'Baggy', 'wide'),
                                default='Small')

        Shirt.drop_collection()

        shirt = Shirt()

        self.assertEqual(shirt.get_size_display(), None)
        self.assertEqual(shirt.get_style_display(), 'Small')

        shirt.size = "XXL"
        shirt.style = "Baggy"
        self.assertEqual(shirt.get_size_display(), 'XXL')
        self.assertEqual(shirt.get_style_display(), 'Baggy')

        # Set as Z - an invalid choice
        shirt.size = "Z"
        shirt.style = "Z"
        self.assertEqual(shirt.get_size_display(), 'Z')
        self.assertEqual(shirt.get_style_display(), 'Z')
        self.assertRaises(ValidationError, shirt.validate)

        Shirt.drop_collection()

    def test_simple_choices_validation_invalid_value(self):
        """Ensure that error messages are correct.
        """
        SIZES = ('S', 'M', 'L', 'XL', 'XXL')
        COLORS = (('R', 'Red'), ('B', 'Blue'))
        SIZE_MESSAGE = u"Value must be one of ('S', 'M', 'L', 'XL', 'XXL')"
        COLOR_MESSAGE = u"Value must be one of ['R', 'B']"

        class Shirt(Document):
            size = StringField(max_length=3, choices=SIZES)
            color = StringField(max_length=1, choices=COLORS)

        Shirt.drop_collection()

        shirt = Shirt()
        shirt.validate()

        shirt.size = "S"
        shirt.color = "R"
        shirt.validate()

        shirt.size = "XS"
        shirt.color = "G"

        try:
            shirt.validate()
        except ValidationError, error:
            # get the validation rules
            error_dict = error.to_dict()
            self.assertEqual(error_dict['size'], SIZE_MESSAGE)
            self.assertEqual(error_dict['color'], COLOR_MESSAGE)

        Shirt.drop_collection()

    def test_ensure_unique_default_instances(self):
        """Ensure that every field has it's own unique default instance."""
        class D(Document):
            data = DictField()
            data2 = DictField(default=lambda: {})

        d1 = D()
        d1.data['foo'] = 'bar'
        d1.data2['foo'] = 'bar'
        d2 = D()
        self.assertEqual(d2.data, {})
        self.assertEqual(d2.data2, {})

    def test_sequence_field(self):
        class Person(Document):
            id = SequenceField(primary_key=True)
            name = StringField()

        self.db['mongoengine.counters'].drop()
        Person.drop_collection()

        for x in xrange(10):
            Person(name="Person %s" % x).save()

        c = self.db['mongoengine.counters'].find_one({'_id': 'person.id'})
        self.assertEqual(c['next'], 10)

        ids = [i.id for i in Person.objects]
        self.assertEqual(ids, range(1, 11))

        c = self.db['mongoengine.counters'].find_one({'_id': 'person.id'})
        self.assertEqual(c['next'], 10)

        Person.id.set_next_value(1000)
        c = self.db['mongoengine.counters'].find_one({'_id': 'person.id'})
        self.assertEqual(c['next'], 1000)


    def test_sequence_field_get_next_value(self):
        class Person(Document):
            id = SequenceField(primary_key=True)
            name = StringField()

        self.db['mongoengine.counters'].drop()
        Person.drop_collection()

        for x in xrange(10):
            Person(name="Person %s" % x).save()

        self.assertEqual(Person.id.get_next_value(), 11)
        self.db['mongoengine.counters'].drop()

        self.assertEqual(Person.id.get_next_value(), 1)

        class Person(Document):
            id = SequenceField(primary_key=True, value_decorator=str)
            name = StringField()

        self.db['mongoengine.counters'].drop()
        Person.drop_collection()

        for x in xrange(10):
            Person(name="Person %s" % x).save()

        self.assertEqual(Person.id.get_next_value(), '11')
        self.db['mongoengine.counters'].drop()

        self.assertEqual(Person.id.get_next_value(), '1')

    def test_sequence_field_sequence_name(self):
        class Person(Document):
            id = SequenceField(primary_key=True, sequence_name='jelly')
            name = StringField()

        self.db['mongoengine.counters'].drop()
        Person.drop_collection()

        for x in xrange(10):
            Person(name="Person %s" % x).save()

        c = self.db['mongoengine.counters'].find_one({'_id': 'jelly.id'})
        self.assertEqual(c['next'], 10)

        ids = [i.id for i in Person.objects]
        self.assertEqual(ids, range(1, 11))

        c = self.db['mongoengine.counters'].find_one({'_id': 'jelly.id'})
        self.assertEqual(c['next'], 10)

        Person.id.set_next_value(1000)
        c = self.db['mongoengine.counters'].find_one({'_id': 'jelly.id'})
        self.assertEqual(c['next'], 1000)

    def test_multiple_sequence_fields(self):
        class Person(Document):
            id = SequenceField(primary_key=True)
            counter = SequenceField()
            name = StringField()

        self.db['mongoengine.counters'].drop()
        Person.drop_collection()

        for x in xrange(10):
            Person(name="Person %s" % x).save()

        c = self.db['mongoengine.counters'].find_one({'_id': 'person.id'})
        self.assertEqual(c['next'], 10)

        ids = [i.id for i in Person.objects]
        self.assertEqual(ids, range(1, 11))

        counters = [i.counter for i in Person.objects]
        self.assertEqual(counters, range(1, 11))

        c = self.db['mongoengine.counters'].find_one({'_id': 'person.id'})
        self.assertEqual(c['next'], 10)

        Person.id.set_next_value(1000)
        c = self.db['mongoengine.counters'].find_one({'_id': 'person.id'})
        self.assertEqual(c['next'], 1000)

        Person.counter.set_next_value(999)
        c = self.db['mongoengine.counters'].find_one({'_id': 'person.counter'})
        self.assertEqual(c['next'], 999)

    def test_sequence_fields_reload(self):
        class Animal(Document):
            counter = SequenceField()
            name = StringField()

        self.db['mongoengine.counters'].drop()
        Animal.drop_collection()

        a = Animal(name="Boi").save()

        self.assertEqual(a.counter, 1)
        a.reload()
        self.assertEqual(a.counter, 1)

        a.counter = None
        self.assertEqual(a.counter, 2)
        a.save()

        self.assertEqual(a.counter, 2)

        a = Animal.objects.first()
        self.assertEqual(a.counter, 2)
        a.reload()
        self.assertEqual(a.counter, 2)

    def test_multiple_sequence_fields_on_docs(self):

        class Animal(Document):
            id = SequenceField(primary_key=True)

        class Person(Document):
            id = SequenceField(primary_key=True)

        self.db['mongoengine.counters'].drop()
        Animal.drop_collection()
        Person.drop_collection()

        for x in xrange(10):
            Animal(name="Animal %s" % x).save()
            Person(name="Person %s" % x).save()

        c = self.db['mongoengine.counters'].find_one({'_id': 'person.id'})
        self.assertEqual(c['next'], 10)

        c = self.db['mongoengine.counters'].find_one({'_id': 'animal.id'})
        self.assertEqual(c['next'], 10)

        ids = [i.id for i in Person.objects]
        self.assertEqual(ids, range(1, 11))

        id = [i.id for i in Animal.objects]
        self.assertEqual(id, range(1, 11))

        c = self.db['mongoengine.counters'].find_one({'_id': 'person.id'})
        self.assertEqual(c['next'], 10)

        c = self.db['mongoengine.counters'].find_one({'_id': 'animal.id'})
        self.assertEqual(c['next'], 10)

    def test_sequence_field_value_decorator(self):
        class Person(Document):
            id = SequenceField(primary_key=True, value_decorator=str)
            name = StringField()

        self.db['mongoengine.counters'].drop()
        Person.drop_collection()

        for x in xrange(10):
            p = Person(name="Person %s" % x)
            p.save()

        c = self.db['mongoengine.counters'].find_one({'_id': 'person.id'})
        self.assertEqual(c['next'], 10)

        ids = [i.id for i in Person.objects]
        self.assertEqual(ids, map(str, range(1, 11)))

        c = self.db['mongoengine.counters'].find_one({'_id': 'person.id'})
        self.assertEqual(c['next'], 10)

    def test_embedded_sequence_field(self):
        class Comment(EmbeddedDocument):
            id = SequenceField()
            content = StringField(required=True)

        class Post(Document):
            title = StringField(required=True)
            comments = ListField(EmbeddedDocumentField(Comment))

        self.db['mongoengine.counters'].drop()
        Post.drop_collection()

        Post(title="MongoEngine",
             comments=[Comment(content="NoSQL Rocks"),
                       Comment(content="MongoEngine Rocks")]).save()
        c = self.db['mongoengine.counters'].find_one({'_id': 'comment.id'})
        self.assertEqual(c['next'], 2)
        post = Post.objects.first()
        self.assertEqual(1, post.comments[0].id)
        self.assertEqual(2, post.comments[1].id)


    def test_generic_embedded_document(self):
        class Car(EmbeddedDocument):
            name = StringField()

        class Dish(EmbeddedDocument):
            food = StringField(required=True)
            number = IntField()

        class Person(Document):
            name = StringField()
            like = GenericEmbeddedDocumentField()

        Person.drop_collection()

        person = Person(name='Test User')
        person.like = Car(name='Fiat')
        person.save()

        person = Person.objects.first()
        self.assertTrue(isinstance(person.like, Car))

        person.like = Dish(food="arroz", number=15)
        person.save()

        person = Person.objects.first()
        self.assertTrue(isinstance(person.like, Dish))

    def test_generic_embedded_document_choices(self):
        """Ensure you can limit GenericEmbeddedDocument choices
        """
        class Car(EmbeddedDocument):
            name = StringField()

        class Dish(EmbeddedDocument):
            food = StringField(required=True)
            number = IntField()

        class Person(Document):
            name = StringField()
            like = GenericEmbeddedDocumentField(choices=(Dish,))

        Person.drop_collection()

        person = Person(name='Test User')
        person.like = Car(name='Fiat')
        self.assertRaises(ValidationError, person.validate)

        person.like = Dish(food="arroz", number=15)
        person.save()

        person = Person.objects.first()
        self.assertTrue(isinstance(person.like, Dish))

    def test_generic_list_embedded_document_choices(self):
        """Ensure you can limit GenericEmbeddedDocument choices inside a list
        field
        """
        class Car(EmbeddedDocument):
            name = StringField()

        class Dish(EmbeddedDocument):
            food = StringField(required=True)
            number = IntField()

        class Person(Document):
            name = StringField()
            likes = ListField(GenericEmbeddedDocumentField(choices=(Dish,)))

        Person.drop_collection()

        person = Person(name='Test User')
        person.likes = [Car(name='Fiat')]
        self.assertRaises(ValidationError, person.validate)

        person.likes = [Dish(food="arroz", number=15)]
        person.save()

        person = Person.objects.first()
        self.assertTrue(isinstance(person.likes[0], Dish))

    def test_recursive_validation(self):
        """Ensure that a validation result to_dict is available.
        """
        class Author(EmbeddedDocument):
            name = StringField(required=True)

        class Comment(EmbeddedDocument):
            author = EmbeddedDocumentField(Author, required=True)
            content = StringField(required=True)

        class Post(Document):
            title = StringField(required=True)
            comments = ListField(EmbeddedDocumentField(Comment))

        bob = Author(name='Bob')
        post = Post(title='hello world')
        post.comments.append(Comment(content='hello', author=bob))
        post.comments.append(Comment(author=bob))

        self.assertRaises(ValidationError, post.validate)
        try:
            post.validate()
        except ValidationError, error:
            # ValidationError.errors property
            self.assertTrue(hasattr(error, 'errors'))
            self.assertTrue(isinstance(error.errors, dict))
            self.assertTrue('comments' in error.errors)
            self.assertTrue(1 in error.errors['comments'])
            self.assertTrue(isinstance(error.errors['comments'][1]['content'],
                            ValidationError))

            # ValidationError.schema property
            error_dict = error.to_dict()
            self.assertTrue(isinstance(error_dict, dict))
            self.assertTrue('comments' in error_dict)
            self.assertTrue(1 in error_dict['comments'])
            self.assertTrue('content' in error_dict['comments'][1])
            self.assertEqual(error_dict['comments'][1]['content'],
                             u'Field is required')

        post.comments[1].content = 'here we go'
        post.validate()

    def test_email_field(self):
        class User(Document):
            email = EmailField()

        user = User(email="ross@example.com")
        self.assertTrue(user.validate() is None)

        user = User(email="ross@example.co.uk")
        self.assertTrue(user.validate() is None)

        user = User(email=("Kofq@rhom0e4klgauOhpbpNdogawnyIKvQS0wk2mjqrgGQ5S"
                           "ucictfqpdkK9iS1zeFw8sg7s7cwAF7suIfUfeyueLpfosjn3"
                           "aJIazqqWkm7.net"))
        self.assertTrue(user.validate() is None)

        user = User(email='me@localhost')
        self.assertRaises(ValidationError, user.validate)

        user = User(email="ross@example.com.")
        self.assertRaises(ValidationError, user.validate)

    def test_email_field_honors_regex(self):
        class User(Document):
            email = EmailField(regex=r'\w+@example.com')

        # Fails regex validation
        user = User(email='me@foo.com')
        self.assertRaises(ValidationError, user.validate)

        # Passes regex validation
        user = User(email='me@example.com')
        self.assertTrue(user.validate() is None)

    def test_tuples_as_tuples(self):
        """
        Ensure that tuples remain tuples when they are
        inside a ComplexBaseField
        """
        from mongoengine.base import BaseField

        class EnumField(BaseField):

            def __init__(self, **kwargs):
                super(EnumField, self).__init__(**kwargs)

            def to_mongo(self, value):
                return value

            def to_python(self, value):
                return tuple(value)

        class TestDoc(Document):
            items = ListField(EnumField())

        TestDoc.drop_collection()
        tuples = [(100, 'Testing')]
        doc = TestDoc()
        doc.items = tuples
        doc.save()
        x = TestDoc.objects().get()
        self.assertTrue(x is not None)
        self.assertTrue(len(x.items) == 1)
        self.assertTrue(tuple(x.items[0]) in tuples)
        self.assertTrue(x.items[0] in tuples)

    def test_dynamic_fields_class(self):

        class Doc2(Document):
            field_1 = StringField(db_field='f')

        class Doc(Document):
            my_id = IntField(required=True, unique=True, primary_key=True)
            embed_me = DynamicField(db_field='e')
            field_x = StringField(db_field='x')

        Doc.drop_collection()
        Doc2.drop_collection()

        doc2 = Doc2(field_1="hello")
        doc = Doc(my_id=1, embed_me=doc2, field_x="x")
        self.assertRaises(OperationError, doc.save)

        doc2.save()
        doc.save()

        doc = Doc.objects.get()
        self.assertEqual(doc.embed_me.field_1, "hello")

    def test_dynamic_fields_embedded_class(self):

        class Embed(EmbeddedDocument):
            field_1 = StringField(db_field='f')

        class Doc(Document):
            my_id = IntField(required=True, unique=True, primary_key=True)
            embed_me = DynamicField(db_field='e')
            field_x = StringField(db_field='x')

        Doc.drop_collection()

        Doc(my_id=1, embed_me=Embed(field_1="hello"), field_x="x").save()

        doc = Doc.objects.get()
        self.assertEqual(doc.embed_me.field_1, "hello")

    def test_invalid_dict_value(self):
        class DictFieldTest(Document):
            dictionary = DictField(required=True)

        DictFieldTest.drop_collection()

        test = DictFieldTest(dictionary=None)
        test.dictionary # Just access to test getter
        self.assertRaises(ValidationError, test.validate)

        test = DictFieldTest(dictionary=False)
        test.dictionary # Just access to test getter
        self.assertRaises(ValidationError, test.validate)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = file_tests
# -*- coding: utf-8 -*-
import sys
sys.path[0:0] = [""]

import copy
import os
import unittest
import tempfile

import gridfs

from nose.plugins.skip import SkipTest
from mongoengine import *
from mongoengine.connection import get_db
from mongoengine.python_support import PY3, b, StringIO

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

TEST_IMAGE_PATH = os.path.join(os.path.dirname(__file__), 'mongoengine.png')
TEST_IMAGE2_PATH = os.path.join(os.path.dirname(__file__), 'mongodb_leaf.png')


class FileTest(unittest.TestCase):

    def setUp(self):
        connect(db='mongoenginetest')
        self.db = get_db()

    def tearDown(self):
        self.db.drop_collection('fs.files')
        self.db.drop_collection('fs.chunks')

    def test_file_field_optional(self):
        # Make sure FileField is optional and not required
        class DemoFile(Document):
            the_file = FileField()
        DemoFile.objects.create()

    def test_file_fields(self):
        """Ensure that file fields can be written to and their data retrieved
        """

        class PutFile(Document):
            the_file = FileField()

        PutFile.drop_collection()

        text = b('Hello, World!')
        content_type = 'text/plain'

        putfile = PutFile()
        putfile.the_file.put(text, content_type=content_type, filename="hello")
        putfile.save()

        result = PutFile.objects.first()
        self.assertTrue(putfile == result)
        self.assertEqual("%s" % result.the_file, "<GridFSProxy: hello>")
        self.assertEqual(result.the_file.read(), text)
        self.assertEqual(result.the_file.content_type, content_type)
        result.the_file.delete()  # Remove file from GridFS
        PutFile.objects.delete()

        # Ensure file-like objects are stored
        PutFile.drop_collection()

        putfile = PutFile()
        putstring = StringIO()
        putstring.write(text)
        putstring.seek(0)
        putfile.the_file.put(putstring, content_type=content_type)
        putfile.save()

        result = PutFile.objects.first()
        self.assertTrue(putfile == result)
        self.assertEqual(result.the_file.read(), text)
        self.assertEqual(result.the_file.content_type, content_type)
        result.the_file.delete()

    def test_file_fields_stream(self):
        """Ensure that file fields can be written to and their data retrieved
        """
        class StreamFile(Document):
            the_file = FileField()

        StreamFile.drop_collection()

        text = b('Hello, World!')
        more_text = b('Foo Bar')
        content_type = 'text/plain'

        streamfile = StreamFile()
        streamfile.the_file.new_file(content_type=content_type)
        streamfile.the_file.write(text)
        streamfile.the_file.write(more_text)
        streamfile.the_file.close()
        streamfile.save()

        result = StreamFile.objects.first()
        self.assertTrue(streamfile == result)
        self.assertEqual(result.the_file.read(), text + more_text)
        self.assertEqual(result.the_file.content_type, content_type)
        result.the_file.seek(0)
        self.assertEqual(result.the_file.tell(), 0)
        self.assertEqual(result.the_file.read(len(text)), text)
        self.assertEqual(result.the_file.tell(), len(text))
        self.assertEqual(result.the_file.read(len(more_text)), more_text)
        self.assertEqual(result.the_file.tell(), len(text + more_text))
        result.the_file.delete()

        # Ensure deleted file returns None
        self.assertTrue(result.the_file.read() == None)

    def test_file_fields_set(self):

        class SetFile(Document):
            the_file = FileField()

        text = b('Hello, World!')
        more_text = b('Foo Bar')

        SetFile.drop_collection()

        setfile = SetFile()
        setfile.the_file = text
        setfile.save()

        result = SetFile.objects.first()
        self.assertTrue(setfile == result)
        self.assertEqual(result.the_file.read(), text)

        # Try replacing file with new one
        result.the_file.replace(more_text)
        result.save()

        result = SetFile.objects.first()
        self.assertTrue(setfile == result)
        self.assertEqual(result.the_file.read(), more_text)
        result.the_file.delete()

    def test_file_field_no_default(self):

        class GridDocument(Document):
            the_file = FileField()

        GridDocument.drop_collection()

        with tempfile.TemporaryFile() as f:
            f.write(b("Hello World!"))
            f.flush()

            # Test without default
            doc_a = GridDocument()
            doc_a.save()

            doc_b = GridDocument.objects.with_id(doc_a.id)
            doc_b.the_file.replace(f, filename='doc_b')
            doc_b.save()
            self.assertNotEqual(doc_b.the_file.grid_id, None)

            # Test it matches
            doc_c = GridDocument.objects.with_id(doc_b.id)
            self.assertEqual(doc_b.the_file.grid_id, doc_c.the_file.grid_id)

            # Test with default
            doc_d = GridDocument(the_file=b(''))
            doc_d.save()

            doc_e = GridDocument.objects.with_id(doc_d.id)
            self.assertEqual(doc_d.the_file.grid_id, doc_e.the_file.grid_id)

            doc_e.the_file.replace(f, filename='doc_e')
            doc_e.save()

            doc_f = GridDocument.objects.with_id(doc_e.id)
            self.assertEqual(doc_e.the_file.grid_id, doc_f.the_file.grid_id)

        db = GridDocument._get_db()
        grid_fs = gridfs.GridFS(db)
        self.assertEqual(['doc_b', 'doc_e'], grid_fs.list())

    def test_file_uniqueness(self):
        """Ensure that each instance of a FileField is unique
        """
        class TestFile(Document):
            name = StringField()
            the_file = FileField()

        # First instance
        test_file = TestFile()
        test_file.name = "Hello, World!"
        test_file.the_file.put(b('Hello, World!'))
        test_file.save()

        # Second instance
        test_file_dupe = TestFile()
        data = test_file_dupe.the_file.read()  # Should be None

        self.assertTrue(test_file.name != test_file_dupe.name)
        self.assertTrue(test_file.the_file.read() != data)

        TestFile.drop_collection()

    def test_file_saving(self):
        """Ensure you can add meta data to file"""

        class Animal(Document):
            genus = StringField()
            family = StringField()
            photo = FileField()

        Animal.drop_collection()
        marmot = Animal(genus='Marmota', family='Sciuridae')

        marmot_photo = open(TEST_IMAGE_PATH, 'rb')  # Retrieve a photo from disk
        marmot.photo.put(marmot_photo, content_type='image/jpeg', foo='bar')
        marmot.photo.close()
        marmot.save()

        marmot = Animal.objects.get()
        self.assertEqual(marmot.photo.content_type, 'image/jpeg')
        self.assertEqual(marmot.photo.foo, 'bar')

    def test_file_reassigning(self):
        class TestFile(Document):
            the_file = FileField()
        TestFile.drop_collection()

        test_file = TestFile(the_file=open(TEST_IMAGE_PATH, 'rb')).save()
        self.assertEqual(test_file.the_file.get().length, 8313)

        test_file = TestFile.objects.first()
        test_file.the_file = open(TEST_IMAGE2_PATH, 'rb')
        test_file.save()
        self.assertEqual(test_file.the_file.get().length, 4971)

    def test_file_boolean(self):
        """Ensure that a boolean test of a FileField indicates its presence
        """
        class TestFile(Document):
            the_file = FileField()
        TestFile.drop_collection()

        test_file = TestFile()
        self.assertFalse(bool(test_file.the_file))
        test_file.the_file.put(b('Hello, World!'), content_type='text/plain')
        test_file.save()
        self.assertTrue(bool(test_file.the_file))

        test_file = TestFile.objects.first()
        self.assertEqual(test_file.the_file.content_type, "text/plain")

    def test_file_cmp(self):
        """Test comparing against other types"""
        class TestFile(Document):
            the_file = FileField()

        test_file = TestFile()
        self.assertFalse(test_file.the_file in [{"test": 1}])

    def test_image_field(self):
        if not HAS_PIL:
            raise SkipTest('PIL not installed')

        class TestImage(Document):
            image = ImageField()

        TestImage.drop_collection()

        with tempfile.TemporaryFile() as f:
            f.write(b("Hello World!"))
            f.flush()

            t = TestImage()
            try:
                t.image.put(f)
                self.fail("Should have raised an invalidation error")
            except ValidationError, e:
                self.assertEqual("%s" % e, "Invalid image: cannot identify image file")

        t = TestImage()
        t.image.put(open(TEST_IMAGE_PATH, 'rb'))
        t.save()

        t = TestImage.objects.first()

        self.assertEqual(t.image.format, 'PNG')

        w, h = t.image.size
        self.assertEqual(w, 371)
        self.assertEqual(h, 76)

        t.image.delete()

    def test_image_field_reassigning(self):
        if not HAS_PIL:
            raise SkipTest('PIL not installed')

        class TestFile(Document):
            the_file = ImageField()
        TestFile.drop_collection()

        test_file = TestFile(the_file=open(TEST_IMAGE_PATH, 'rb')).save()
        self.assertEqual(test_file.the_file.size, (371, 76))

        test_file = TestFile.objects.first()
        test_file.the_file = open(TEST_IMAGE2_PATH, 'rb')
        test_file.save()
        self.assertEqual(test_file.the_file.size, (45, 101))

    def test_image_field_resize(self):
        if not HAS_PIL:
            raise SkipTest('PIL not installed')

        class TestImage(Document):
            image = ImageField(size=(185, 37))

        TestImage.drop_collection()

        t = TestImage()
        t.image.put(open(TEST_IMAGE_PATH, 'rb'))
        t.save()

        t = TestImage.objects.first()

        self.assertEqual(t.image.format, 'PNG')
        w, h = t.image.size

        self.assertEqual(w, 185)
        self.assertEqual(h, 37)

        t.image.delete()

    def test_image_field_resize_force(self):
        if not HAS_PIL:
            raise SkipTest('PIL not installed')

        class TestImage(Document):
            image = ImageField(size=(185, 37, True))

        TestImage.drop_collection()

        t = TestImage()
        t.image.put(open(TEST_IMAGE_PATH, 'rb'))
        t.save()

        t = TestImage.objects.first()

        self.assertEqual(t.image.format, 'PNG')
        w, h = t.image.size

        self.assertEqual(w, 185)
        self.assertEqual(h, 37)

        t.image.delete()

    def test_image_field_thumbnail(self):
        if not HAS_PIL:
            raise SkipTest('PIL not installed')

        class TestImage(Document):
            image = ImageField(thumbnail_size=(92, 18))

        TestImage.drop_collection()

        t = TestImage()
        t.image.put(open(TEST_IMAGE_PATH, 'rb'))
        t.save()

        t = TestImage.objects.first()

        self.assertEqual(t.image.thumbnail.format, 'PNG')
        self.assertEqual(t.image.thumbnail.width, 92)
        self.assertEqual(t.image.thumbnail.height, 18)

        t.image.delete()

    def test_file_multidb(self):
        register_connection('test_files', 'test_files')

        class TestFile(Document):
            name = StringField()
            the_file = FileField(db_alias="test_files",
                                 collection_name="macumba")

        TestFile.drop_collection()

        # delete old filesystem
        get_db("test_files").macumba.files.drop()
        get_db("test_files").macumba.chunks.drop()

        # First instance
        test_file = TestFile()
        test_file.name = "Hello, World!"
        test_file.the_file.put(b('Hello, World!'),
                          name="hello.txt")
        test_file.save()

        data = get_db("test_files").macumba.files.find_one()
        self.assertEqual(data.get('name'), 'hello.txt')

        test_file = TestFile.objects.first()
        self.assertEqual(test_file.the_file.read(),
                          b('Hello, World!'))

        test_file = TestFile.objects.first()
        test_file.the_file = b('HELLO, WORLD!')
        test_file.save()

        test_file = TestFile.objects.first()
        self.assertEqual(test_file.the_file.read(),
                          b('HELLO, WORLD!'))

    def test_copyable(self):
        class PutFile(Document):
            the_file = FileField()

        PutFile.drop_collection()

        text = b('Hello, World!')
        content_type = 'text/plain'

        putfile = PutFile()
        putfile.the_file.put(text, content_type=content_type)
        putfile.save()

        class TestFile(Document):
            name = StringField()

        self.assertEqual(putfile, copy.copy(putfile))
        self.assertEqual(putfile, copy.deepcopy(putfile))

    def test_get_image_by_grid_id(self):

        if not HAS_PIL:
            raise SkipTest('PIL not installed')

        class TestImage(Document):

            image1 = ImageField()
            image2 = ImageField()

        TestImage.drop_collection()

        t = TestImage()
        t.image1.put(open(TEST_IMAGE_PATH, 'rb'))
        t.image2.put(open(TEST_IMAGE2_PATH, 'rb'))
        t.save()

        test = TestImage.objects.first()
        grid_id = test.image1.grid_id

        self.assertEqual(1, TestImage.objects(Q(image1=grid_id)
                                              or Q(image2=grid_id)).count())

    def test_complex_field_filefield(self):
        """Ensure you can add meta data to file"""

        class Animal(Document):
            genus = StringField()
            family = StringField()
            photos = ListField(FileField())

        Animal.drop_collection()
        marmot = Animal(genus='Marmota', family='Sciuridae')

        marmot_photo = open(TEST_IMAGE_PATH, 'rb')  # Retrieve a photo from disk

        photos_field = marmot._fields['photos'].field
        new_proxy = photos_field.get_proxy_obj('photos', marmot)
        new_proxy.put(marmot_photo, content_type='image/jpeg', foo='bar')
        marmot_photo.close()

        marmot.photos.append(new_proxy)
        marmot.save()

        marmot = Animal.objects.get()
        self.assertEqual(marmot.photos[0].content_type, 'image/jpeg')
        self.assertEqual(marmot.photos[0].foo, 'bar')
        self.assertEqual(marmot.photos[0].get().length, 8313)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = geo
# -*- coding: utf-8 -*-
import sys
sys.path[0:0] = [""]

import unittest

from mongoengine import *
from mongoengine.connection import get_db

__all__ = ("GeoFieldTest", )


class GeoFieldTest(unittest.TestCase):

    def setUp(self):
        connect(db='mongoenginetest')
        self.db = get_db()

    def _test_for_expected_error(self, Cls, loc, expected):
        try:
            Cls(loc=loc).validate()
            self.fail()
        except ValidationError, e:
            self.assertEqual(expected, e.to_dict()['loc'])

    def test_geopoint_validation(self):
        class Location(Document):
            loc = GeoPointField()

        invalid_coords = [{"x": 1, "y": 2}, 5, "a"]
        expected = 'GeoPointField can only accept tuples or lists of (x, y)'

        for coord in invalid_coords:
            self._test_for_expected_error(Location, coord, expected)

        invalid_coords = [[], [1], [1, 2, 3]]
        for coord in invalid_coords:
            expected = "Value (%s) must be a two-dimensional point" % repr(coord)
            self._test_for_expected_error(Location, coord, expected)

        invalid_coords = [[{}, {}], ("a", "b")]
        for coord in invalid_coords:
            expected = "Both values (%s) in point must be float or int" % repr(coord)
            self._test_for_expected_error(Location, coord, expected)

    def test_point_validation(self):
        class Location(Document):
            loc = PointField()

        invalid_coords = {"x": 1, "y": 2}
        expected = 'PointField can only accept a valid GeoJson dictionary or lists of (x, y)'
        self._test_for_expected_error(Location, invalid_coords, expected)

        invalid_coords = {"type": "MadeUp", "coordinates": []}
        expected = 'PointField type must be "Point"'
        self._test_for_expected_error(Location, invalid_coords, expected)

        invalid_coords = {"type": "Point", "coordinates": [1, 2, 3]}
        expected = "Value ([1, 2, 3]) must be a two-dimensional point"
        self._test_for_expected_error(Location, invalid_coords, expected)

        invalid_coords = [5, "a"]
        expected = "PointField can only accept lists of [x, y]"
        for coord in invalid_coords:
            self._test_for_expected_error(Location, coord, expected)

        invalid_coords = [[], [1], [1, 2, 3]]
        for coord in invalid_coords:
            expected = "Value (%s) must be a two-dimensional point" % repr(coord)
            self._test_for_expected_error(Location, coord, expected)

        invalid_coords = [[{}, {}], ("a", "b")]
        for coord in invalid_coords:
            expected = "Both values (%s) in point must be float or int" % repr(coord)
            self._test_for_expected_error(Location, coord, expected)

        Location(loc=[1, 2]).validate()
        Location(loc={
            "type": "Point",
            "coordinates": [
              81.4471435546875,
              23.61432859499169
            ]}).validate()

    def test_linestring_validation(self):
        class Location(Document):
            loc = LineStringField()

        invalid_coords = {"x": 1, "y": 2}
        expected = 'LineStringField can only accept a valid GeoJson dictionary or lists of (x, y)'
        self._test_for_expected_error(Location, invalid_coords, expected)

        invalid_coords = {"type": "MadeUp", "coordinates": [[]]}
        expected = 'LineStringField type must be "LineString"'
        self._test_for_expected_error(Location, invalid_coords, expected)

        invalid_coords = {"type": "LineString", "coordinates": [[1, 2, 3]]}
        expected = "Invalid LineString:\nValue ([1, 2, 3]) must be a two-dimensional point"
        self._test_for_expected_error(Location, invalid_coords, expected)

        invalid_coords = [5, "a"]
        expected = "Invalid LineString must contain at least one valid point"
        self._test_for_expected_error(Location, invalid_coords, expected)

        invalid_coords = [[1]]
        expected = "Invalid LineString:\nValue (%s) must be a two-dimensional point" % repr(invalid_coords[0])
        self._test_for_expected_error(Location, invalid_coords, expected)

        invalid_coords = [[1, 2, 3]]
        expected = "Invalid LineString:\nValue (%s) must be a two-dimensional point" % repr(invalid_coords[0])
        self._test_for_expected_error(Location, invalid_coords, expected)

        invalid_coords = [[[{}, {}]], [("a", "b")]]
        for coord in invalid_coords:
            expected = "Invalid LineString:\nBoth values (%s) in point must be float or int" % repr(coord[0])
            self._test_for_expected_error(Location, coord, expected)

        Location(loc=[[1, 2], [3, 4], [5, 6], [1,2]]).validate()

    def test_polygon_validation(self):
        class Location(Document):
            loc = PolygonField()

        invalid_coords = {"x": 1, "y": 2}
        expected = 'PolygonField can only accept a valid GeoJson dictionary or lists of (x, y)'
        self._test_for_expected_error(Location, invalid_coords, expected)

        invalid_coords = {"type": "MadeUp", "coordinates": [[]]}
        expected = 'PolygonField type must be "Polygon"'
        self._test_for_expected_error(Location, invalid_coords, expected)

        invalid_coords = {"type": "Polygon", "coordinates": [[[1, 2, 3]]]}
        expected = "Invalid Polygon:\nValue ([1, 2, 3]) must be a two-dimensional point"
        self._test_for_expected_error(Location, invalid_coords, expected)

        invalid_coords = [[[5, "a"]]]
        expected = "Invalid Polygon:\nBoth values ([5, 'a']) in point must be float or int"
        self._test_for_expected_error(Location, invalid_coords, expected)

        invalid_coords = [[[]]]
        expected = "Invalid Polygon must contain at least one valid linestring"
        self._test_for_expected_error(Location, invalid_coords, expected)

        invalid_coords = [[[1, 2, 3]]]
        expected = "Invalid Polygon:\nValue ([1, 2, 3]) must be a two-dimensional point"
        self._test_for_expected_error(Location, invalid_coords, expected)

        invalid_coords = [[[{}, {}]], [("a", "b")]]
        expected = "Invalid Polygon:\nBoth values ([{}, {}]) in point must be float or int, Both values (('a', 'b')) in point must be float or int"
        self._test_for_expected_error(Location, invalid_coords, expected)

        invalid_coords = [[[1, 2], [3, 4]]]
        expected = "Invalid Polygon:\nLineStrings must start and end at the same point"
        self._test_for_expected_error(Location, invalid_coords, expected)

        Location(loc=[[[1, 2], [3, 4], [5, 6], [1, 2]]]).validate()

    def test_indexes_geopoint(self):
        """Ensure that indexes are created automatically for GeoPointFields.
        """
        class Event(Document):
            title = StringField()
            location = GeoPointField()

        geo_indicies = Event._geo_indices()
        self.assertEqual(geo_indicies, [{'fields': [('location', '2d')]}])

    def test_geopoint_embedded_indexes(self):
        """Ensure that indexes are created automatically for GeoPointFields on
        embedded documents.
        """
        class Venue(EmbeddedDocument):
            location = GeoPointField()
            name = StringField()

        class Event(Document):
            title = StringField()
            venue = EmbeddedDocumentField(Venue)

        geo_indicies = Event._geo_indices()
        self.assertEqual(geo_indicies, [{'fields': [('venue.location', '2d')]}])

    def test_indexes_2dsphere(self):
        """Ensure that indexes are created automatically for GeoPointFields.
        """
        class Event(Document):
            title = StringField()
            point = PointField()
            line = LineStringField()
            polygon = PolygonField()

        geo_indicies = Event._geo_indices()
        self.assertTrue({'fields': [('line', '2dsphere')]} in geo_indicies)
        self.assertTrue({'fields': [('polygon', '2dsphere')]} in geo_indicies)
        self.assertTrue({'fields': [('point', '2dsphere')]} in geo_indicies)

    def test_indexes_2dsphere_embedded(self):
        """Ensure that indexes are created automatically for GeoPointFields.
        """
        class Venue(EmbeddedDocument):
            name = StringField()
            point = PointField()
            line = LineStringField()
            polygon = PolygonField()

        class Event(Document):
            title = StringField()
            venue = EmbeddedDocumentField(Venue)

        geo_indicies = Event._geo_indices()
        self.assertTrue({'fields': [('venue.line', '2dsphere')]} in geo_indicies)
        self.assertTrue({'fields': [('venue.polygon', '2dsphere')]} in geo_indicies)
        self.assertTrue({'fields': [('venue.point', '2dsphere')]} in geo_indicies)

    def test_geo_indexes_recursion(self):

        class Location(Document):
            name = StringField()
            location = GeoPointField()

        class Parent(Document):
            name = StringField()
            location = ReferenceField(Location)

        Location.drop_collection()
        Parent.drop_collection()

        list(Parent.objects)

        collection = Parent._get_collection()
        info = collection.index_information()

        self.assertFalse('location_2d' in info)

        self.assertEqual(len(Parent._geo_indices()), 0)
        self.assertEqual(len(Location._geo_indices()), 1)

    def test_geo_indexes_auto_index(self):

        # Test just listing the fields
        class Log(Document):
            location = PointField(auto_index=False)
            datetime = DateTimeField()

            meta = {
                'indexes': [[("location", "2dsphere"), ("datetime", 1)]]
            }

        self.assertEqual([], Log._geo_indices())

        Log.drop_collection()
        Log.ensure_indexes()

        info = Log._get_collection().index_information()
        self.assertEqual(info["location_2dsphere_datetime_1"]["key"],
                         [('location', '2dsphere'), ('datetime', 1)])

        # Test listing explicitly
        class Log(Document):
            location = PointField(auto_index=False)
            datetime = DateTimeField()

            meta = {
                'indexes': [
                    {'fields': [("location", "2dsphere"), ("datetime", 1)]}
                ]
            }

        self.assertEqual([], Log._geo_indices())

        Log.drop_collection()
        Log.ensure_indexes()

        info = Log._get_collection().index_information()
        self.assertEqual(info["location_2dsphere_datetime_1"]["key"],
                         [('location', '2dsphere'), ('datetime', 1)])


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = fixtures
import pickle
from datetime import datetime

from mongoengine import *
from mongoengine import signals


class PickleEmbedded(EmbeddedDocument):
    date = DateTimeField(default=datetime.now)


class PickleTest(Document):
    number = IntField()
    string = StringField(choices=(('One', '1'), ('Two', '2')))
    embedded = EmbeddedDocumentField(PickleEmbedded)
    lists = ListField(StringField())
    photo = FileField()


class PickleDyanmicEmbedded(DynamicEmbeddedDocument):
    date = DateTimeField(default=datetime.now)


class PickleDynamicTest(DynamicDocument):
    number = IntField()


class PickleSignalsTest(Document):
    number = IntField()
    string = StringField(choices=(('One', '1'), ('Two', '2')))
    embedded = EmbeddedDocumentField(PickleEmbedded)
    lists = ListField(StringField())

    @classmethod
    def post_save(self, sender, document, created, **kwargs):
        pickled = pickle.dumps(document)

    @classmethod
    def post_delete(self, sender, document, **kwargs):
        pickled = pickle.dumps(document)

signals.post_save.connect(PickleSignalsTest.post_save, sender=PickleSignalsTest)
signals.post_delete.connect(PickleSignalsTest.post_delete, sender=PickleSignalsTest)


class Mixin(object):
    name = StringField()


class Base(Document):
    meta = {'allow_inheritance': True}

########NEW FILE########
__FILENAME__ = convert_to_new_inheritance_model
# -*- coding: utf-8 -*-
import unittest

from mongoengine import Document, connect
from mongoengine.connection import get_db
from mongoengine.fields import StringField

__all__ = ('ConvertToNewInheritanceModel', )


class ConvertToNewInheritanceModel(unittest.TestCase):

    def setUp(self):
        connect(db='mongoenginetest')
        self.db = get_db()

    def tearDown(self):
        for collection in self.db.collection_names():
            if 'system.' in collection:
                continue
            self.db.drop_collection(collection)

    def test_how_to_convert_to_the_new_inheritance_model(self):
        """Demonstrates migrating from 0.7 to 0.8
        """

        # 1. Declaration of the class
        class Animal(Document):
            name = StringField()
            meta = {
                'allow_inheritance': True,
                'indexes': ['name']
            }

        # 2. Remove _types
        collection = Animal._get_collection()
        collection.update({}, {"$unset": {"_types": 1}}, multi=True)

        # 3. Confirm extra data is removed
        count = collection.find({'_types': {"$exists": True}}).count()
        self.assertEqual(0, count)

        # 4. Remove indexes
        info = collection.index_information()
        indexes_to_drop = [key for key, value in info.iteritems()
                           if '_types' in dict(value['key'])]
        for index in indexes_to_drop:
            collection.drop_index(index)

        # 5. Recreate indexes
        Animal.ensure_indexes()

########NEW FILE########
__FILENAME__ = decimalfield_as_float
 # -*- coding: utf-8 -*-
import unittest
import decimal
from decimal import Decimal

from mongoengine import Document, connect
from mongoengine.connection import get_db
from mongoengine.fields import StringField, DecimalField, ListField

__all__ = ('ConvertDecimalField', )


class ConvertDecimalField(unittest.TestCase):

    def setUp(self):
        connect(db='mongoenginetest')
        self.db = get_db()

    def test_how_to_convert_decimal_fields(self):
        """Demonstrates migrating from 0.7 to 0.8
        """

        # 1. Old definition - using dbrefs
        class Person(Document):
            name = StringField()
            money = DecimalField(force_string=True)
            monies = ListField(DecimalField(force_string=True))

        Person.drop_collection()
        Person(name="Wilson Jr", money=Decimal("2.50"),
               monies=[Decimal("2.10"), Decimal("5.00")]).save()

        # 2. Start the migration by changing the schema
        # Change DecimalField - add precision and rounding settings
        class Person(Document):
            name = StringField()
            money = DecimalField(precision=2, rounding=decimal.ROUND_HALF_UP)
            monies = ListField(DecimalField(precision=2,
                                            rounding=decimal.ROUND_HALF_UP))

        # 3. Loop all the objects and mark parent as changed
        for p in Person.objects:
            p._mark_as_changed('money')
            p._mark_as_changed('monies')
            p.save()

        # 4. Confirmation of the fix!
        wilson = Person.objects(name="Wilson Jr").as_pymongo()[0]
        self.assertTrue(isinstance(wilson['money'], float))
        self.assertTrue(all([isinstance(m, float) for m in wilson['monies']]))

########NEW FILE########
__FILENAME__ = refrencefield_dbref_to_object_id
# -*- coding: utf-8 -*-
import unittest

from mongoengine import Document, connect
from mongoengine.connection import get_db
from mongoengine.fields import StringField, ReferenceField, ListField

__all__ = ('ConvertToObjectIdsModel', )


class ConvertToObjectIdsModel(unittest.TestCase):

    def setUp(self):
        connect(db='mongoenginetest')
        self.db = get_db()

    def test_how_to_convert_to_object_id_reference_fields(self):
        """Demonstrates migrating from 0.7 to 0.8
        """

        # 1. Old definition - using dbrefs
        class Person(Document):
            name = StringField()
            parent = ReferenceField('self', dbref=True)
            friends = ListField(ReferenceField('self', dbref=True))

        Person.drop_collection()

        p1 = Person(name="Wilson", parent=None).save()
        f1 = Person(name="John", parent=None).save()
        f2 = Person(name="Paul", parent=None).save()
        f3 = Person(name="George", parent=None).save()
        f4 = Person(name="Ringo", parent=None).save()
        Person(name="Wilson Jr", parent=p1, friends=[f1, f2, f3, f4]).save()

        # 2. Start the migration by changing the schema
        # Change ReferenceField as now dbref defaults to False
        class Person(Document):
            name = StringField()
            parent = ReferenceField('self')
            friends = ListField(ReferenceField('self'))

        # 3. Loop all the objects and mark parent as changed
        for p in Person.objects:
            p._mark_as_changed('parent')
            p._mark_as_changed('friends')
            p.save()

        # 4. Confirmation of the fix!
        wilson = Person.objects(name="Wilson Jr").as_pymongo()[0]
        self.assertEqual(p1.id, wilson['parent'])
        self.assertEqual([f1.id, f2.id, f3.id, f4.id], wilson['friends'])

########NEW FILE########
__FILENAME__ = turn_off_inheritance
# -*- coding: utf-8 -*-
import unittest

from mongoengine import Document, connect
from mongoengine.connection import get_db
from mongoengine.fields import StringField

__all__ = ('TurnOffInheritanceTest', )


class TurnOffInheritanceTest(unittest.TestCase):

    def setUp(self):
        connect(db='mongoenginetest')
        self.db = get_db()

    def tearDown(self):
        for collection in self.db.collection_names():
            if 'system.' in collection:
                continue
            self.db.drop_collection(collection)

    def test_how_to_turn_off_inheritance(self):
        """Demonstrates migrating from allow_inheritance = True to False.
        """

        # 1. Old declaration of the class

        class Animal(Document):
            name = StringField()
            meta = {
                'allow_inheritance': True,
                'indexes': ['name']
            }

        # 2. Turn off inheritance
        class Animal(Document):
            name = StringField()
            meta = {
                'allow_inheritance': False,
                'indexes': ['name']
            }

        # 3. Remove _types and _cls
        collection = Animal._get_collection()
        collection.update({}, {"$unset": {"_types": 1, "_cls": 1}}, multi=True)

        # 3. Confirm extra data is removed
        count = collection.find({"$or": [{'_types': {"$exists": True}},
                                         {'_cls': {"$exists": True}}]}).count()
        assert count == 0

        # 4. Remove indexes
        info = collection.index_information()
        indexes_to_drop = [key for key, value in info.iteritems()
                           if '_types' in dict(value['key'])
                              or '_cls' in dict(value['key'])]
        for index in indexes_to_drop:
            collection.drop_index(index)

        # 5. Recreate indexes
        Animal.ensure_indexes()

########NEW FILE########
__FILENAME__ = uuidfield_to_binary
# -*- coding: utf-8 -*-
import unittest
import uuid

from mongoengine import Document, connect
from mongoengine.connection import get_db
from mongoengine.fields import StringField, UUIDField, ListField

__all__ = ('ConvertToBinaryUUID', )


class ConvertToBinaryUUID(unittest.TestCase):

    def setUp(self):
        connect(db='mongoenginetest')
        self.db = get_db()

    def test_how_to_convert_to_binary_uuid_fields(self):
        """Demonstrates migrating from 0.7 to 0.8
        """

        # 1. Old definition - using dbrefs
        class Person(Document):
            name = StringField()
            uuid = UUIDField(binary=False)
            uuids = ListField(UUIDField(binary=False))

        Person.drop_collection()
        Person(name="Wilson Jr", uuid=uuid.uuid4(),
               uuids=[uuid.uuid4(), uuid.uuid4()]).save()

        # 2. Start the migration by changing the schema
        # Change UUIDFIeld as now binary defaults to True
        class Person(Document):
            name = StringField()
            uuid = UUIDField()
            uuids = ListField(UUIDField())

        # 3. Loop all the objects and mark parent as changed
        for p in Person.objects:
            p._mark_as_changed('uuid')
            p._mark_as_changed('uuids')
            p.save()

        # 4. Confirmation of the fix!
        wilson = Person.objects(name="Wilson Jr").as_pymongo()[0]
        self.assertTrue(isinstance(wilson['uuid'], uuid.UUID))
        self.assertTrue(all([isinstance(u, uuid.UUID) for u in wilson['uuids']]))

########NEW FILE########
__FILENAME__ = field_list
import sys
sys.path[0:0] = [""]

import unittest

from mongoengine import *
from mongoengine.queryset import QueryFieldList

__all__ = ("QueryFieldListTest", "OnlyExcludeAllTest")


class QueryFieldListTest(unittest.TestCase):

    def test_empty(self):
        q = QueryFieldList()
        self.assertFalse(q)

        q = QueryFieldList(always_include=['_cls'])
        self.assertFalse(q)

    def test_include_include(self):
        q = QueryFieldList()
        q += QueryFieldList(fields=['a', 'b'], value=QueryFieldList.ONLY, _only_called=True)
        self.assertEqual(q.as_dict(), {'a': 1, 'b': 1})
        q += QueryFieldList(fields=['b', 'c'], value=QueryFieldList.ONLY)
        self.assertEqual(q.as_dict(), {'a': 1, 'b': 1, 'c': 1})

    def test_include_exclude(self):
        q = QueryFieldList()
        q += QueryFieldList(fields=['a', 'b'], value=QueryFieldList.ONLY)
        self.assertEqual(q.as_dict(), {'a': 1, 'b': 1})
        q += QueryFieldList(fields=['b', 'c'], value=QueryFieldList.EXCLUDE)
        self.assertEqual(q.as_dict(), {'a': 1})

    def test_exclude_exclude(self):
        q = QueryFieldList()
        q += QueryFieldList(fields=['a', 'b'], value=QueryFieldList.EXCLUDE)
        self.assertEqual(q.as_dict(), {'a': 0, 'b': 0})
        q += QueryFieldList(fields=['b', 'c'], value=QueryFieldList.EXCLUDE)
        self.assertEqual(q.as_dict(), {'a': 0, 'b': 0, 'c': 0})

    def test_exclude_include(self):
        q = QueryFieldList()
        q += QueryFieldList(fields=['a', 'b'], value=QueryFieldList.EXCLUDE)
        self.assertEqual(q.as_dict(), {'a': 0, 'b': 0})
        q += QueryFieldList(fields=['b', 'c'], value=QueryFieldList.ONLY)
        self.assertEqual(q.as_dict(), {'c': 1})

    def test_always_include(self):
        q = QueryFieldList(always_include=['x', 'y'])
        q += QueryFieldList(fields=['a', 'b', 'x'], value=QueryFieldList.EXCLUDE)
        q += QueryFieldList(fields=['b', 'c'], value=QueryFieldList.ONLY)
        self.assertEqual(q.as_dict(), {'x': 1, 'y': 1, 'c': 1})

    def test_reset(self):
        q = QueryFieldList(always_include=['x', 'y'])
        q += QueryFieldList(fields=['a', 'b', 'x'], value=QueryFieldList.EXCLUDE)
        q += QueryFieldList(fields=['b', 'c'], value=QueryFieldList.ONLY)
        self.assertEqual(q.as_dict(), {'x': 1, 'y': 1, 'c': 1})
        q.reset()
        self.assertFalse(q)
        q += QueryFieldList(fields=['b', 'c'], value=QueryFieldList.ONLY)
        self.assertEqual(q.as_dict(), {'x': 1, 'y': 1, 'b': 1, 'c': 1})

    def test_using_a_slice(self):
        q = QueryFieldList()
        q += QueryFieldList(fields=['a'], value={"$slice": 5})
        self.assertEqual(q.as_dict(), {'a': {"$slice": 5}})


class OnlyExcludeAllTest(unittest.TestCase):

    def setUp(self):
        connect(db='mongoenginetest')

        class Person(Document):
            name = StringField()
            age = IntField()
            meta = {'allow_inheritance': True}

        Person.drop_collection()
        self.Person = Person

    def test_mixing_only_exclude(self):

        class MyDoc(Document):
            a = StringField()
            b = StringField()
            c = StringField()
            d = StringField()
            e = StringField()
            f = StringField()

        include = ['a', 'b', 'c', 'd', 'e']
        exclude = ['d', 'e']
        only = ['b', 'c']

        qs = MyDoc.objects.fields(**dict(((i, 1) for i in include)))
        self.assertEqual(qs._loaded_fields.as_dict(),
                         {'a': 1, 'b': 1, 'c': 1, 'd': 1, 'e': 1})
        qs = qs.only(*only)
        self.assertEqual(qs._loaded_fields.as_dict(), {'b': 1, 'c': 1})
        qs = qs.exclude(*exclude)
        self.assertEqual(qs._loaded_fields.as_dict(), {'b': 1, 'c': 1})

        qs = MyDoc.objects.fields(**dict(((i, 1) for i in include)))
        qs = qs.exclude(*exclude)
        self.assertEqual(qs._loaded_fields.as_dict(), {'a': 1, 'b': 1, 'c': 1})
        qs = qs.only(*only)
        self.assertEqual(qs._loaded_fields.as_dict(), {'b': 1, 'c': 1})

        qs = MyDoc.objects.exclude(*exclude)
        qs = qs.fields(**dict(((i, 1) for i in include)))
        self.assertEqual(qs._loaded_fields.as_dict(), {'a': 1, 'b': 1, 'c': 1})
        qs = qs.only(*only)
        self.assertEqual(qs._loaded_fields.as_dict(), {'b': 1, 'c': 1})

    def test_slicing(self):

        class MyDoc(Document):
            a = ListField()
            b = ListField()
            c = ListField()
            d = ListField()
            e = ListField()
            f = ListField()

        include = ['a', 'b', 'c', 'd', 'e']
        exclude = ['d', 'e']
        only = ['b', 'c']

        qs = MyDoc.objects.fields(**dict(((i, 1) for i in include)))
        qs = qs.exclude(*exclude)
        qs = qs.only(*only)
        qs = qs.fields(slice__b=5)
        self.assertEqual(qs._loaded_fields.as_dict(),
                         {'b': {'$slice': 5}, 'c': 1})

        qs = qs.fields(slice__c=[5, 1])
        self.assertEqual(qs._loaded_fields.as_dict(),
                         {'b': {'$slice': 5}, 'c': {'$slice': [5, 1]}})

        qs = qs.exclude('c')
        self.assertEqual(qs._loaded_fields.as_dict(),
                         {'b': {'$slice': 5}})

    def test_only(self):
        """Ensure that QuerySet.only only returns the requested fields.
        """
        person = self.Person(name='test', age=25)
        person.save()

        obj = self.Person.objects.only('name').get()
        self.assertEqual(obj.name, person.name)
        self.assertEqual(obj.age, None)

        obj = self.Person.objects.only('age').get()
        self.assertEqual(obj.name, None)
        self.assertEqual(obj.age, person.age)

        obj = self.Person.objects.only('name', 'age').get()
        self.assertEqual(obj.name, person.name)
        self.assertEqual(obj.age, person.age)

        obj = self.Person.objects.only(*('id', 'name',)).get()
        self.assertEqual(obj.name, person.name)
        self.assertEqual(obj.age, None)

        # Check polymorphism still works
        class Employee(self.Person):
            salary = IntField(db_field='wage')

        employee = Employee(name='test employee', age=40, salary=30000)
        employee.save()

        obj = self.Person.objects(id=employee.id).only('age').get()
        self.assertTrue(isinstance(obj, Employee))

        # Check field names are looked up properly
        obj = Employee.objects(id=employee.id).only('salary').get()
        self.assertEqual(obj.salary, employee.salary)
        self.assertEqual(obj.name, None)

    def test_only_with_subfields(self):
        class User(EmbeddedDocument):
            name = StringField()
            email = StringField()

        class Comment(EmbeddedDocument):
            title = StringField()
            text = StringField()

        class BlogPost(Document):
            content = StringField()
            author = EmbeddedDocumentField(User)
            comments = ListField(EmbeddedDocumentField(Comment))

        BlogPost.drop_collection()

        post = BlogPost(content='Had a good coffee today...')
        post.author = User(name='Test User')
        post.comments = [Comment(title='I aggree', text='Great post!'), Comment(title='Coffee', text='I hate coffee')]
        post.save()

        obj = BlogPost.objects.only('author.name',).get()
        self.assertEqual(obj.content, None)
        self.assertEqual(obj.author.email, None)
        self.assertEqual(obj.author.name, 'Test User')
        self.assertEqual(obj.comments, [])

        obj = BlogPost.objects.only('content', 'comments.title',).get()
        self.assertEqual(obj.content, 'Had a good coffee today...')
        self.assertEqual(obj.author, None)
        self.assertEqual(obj.comments[0].title, 'I aggree')
        self.assertEqual(obj.comments[1].title, 'Coffee')
        self.assertEqual(obj.comments[0].text, None)
        self.assertEqual(obj.comments[1].text, None)

        obj = BlogPost.objects.only('comments',).get()
        self.assertEqual(obj.content, None)
        self.assertEqual(obj.author, None)
        self.assertEqual(obj.comments[0].title, 'I aggree')
        self.assertEqual(obj.comments[1].title, 'Coffee')
        self.assertEqual(obj.comments[0].text, 'Great post!')
        self.assertEqual(obj.comments[1].text, 'I hate coffee')

        BlogPost.drop_collection()

    def test_exclude(self):
        class User(EmbeddedDocument):
            name = StringField()
            email = StringField()

        class Comment(EmbeddedDocument):
            title = StringField()
            text = StringField()

        class BlogPost(Document):
            content = StringField()
            author = EmbeddedDocumentField(User)
            comments = ListField(EmbeddedDocumentField(Comment))

        BlogPost.drop_collection()

        post = BlogPost(content='Had a good coffee today...')
        post.author = User(name='Test User')
        post.comments = [Comment(title='I aggree', text='Great post!'), Comment(title='Coffee', text='I hate coffee')]
        post.save()

        obj = BlogPost.objects.exclude('author', 'comments.text').get()
        self.assertEqual(obj.author, None)
        self.assertEqual(obj.content, 'Had a good coffee today...')
        self.assertEqual(obj.comments[0].title, 'I aggree')
        self.assertEqual(obj.comments[0].text, None)

        BlogPost.drop_collection()

    def test_exclude_only_combining(self):
        class Attachment(EmbeddedDocument):
            name = StringField()
            content = StringField()

        class Email(Document):
            sender = StringField()
            to = StringField()
            subject = StringField()
            body = StringField()
            content_type = StringField()
            attachments = ListField(EmbeddedDocumentField(Attachment))

        Email.drop_collection()
        email = Email(sender='me', to='you', subject='From Russia with Love', body='Hello!', content_type='text/plain')
        email.attachments = [
            Attachment(name='file1.doc', content='ABC'),
            Attachment(name='file2.doc', content='XYZ'),
        ]
        email.save()

        obj = Email.objects.exclude('content_type').exclude('body').get()
        self.assertEqual(obj.sender, 'me')
        self.assertEqual(obj.to, 'you')
        self.assertEqual(obj.subject, 'From Russia with Love')
        self.assertEqual(obj.body, None)
        self.assertEqual(obj.content_type, None)

        obj = Email.objects.only('sender', 'to').exclude('body', 'sender').get()
        self.assertEqual(obj.sender, None)
        self.assertEqual(obj.to, 'you')
        self.assertEqual(obj.subject, None)
        self.assertEqual(obj.body, None)
        self.assertEqual(obj.content_type, None)

        obj = Email.objects.exclude('attachments.content').exclude('body').only('to', 'attachments.name').get()
        self.assertEqual(obj.attachments[0].name, 'file1.doc')
        self.assertEqual(obj.attachments[0].content, None)
        self.assertEqual(obj.sender, None)
        self.assertEqual(obj.to, 'you')
        self.assertEqual(obj.subject, None)
        self.assertEqual(obj.body, None)
        self.assertEqual(obj.content_type, None)

        Email.drop_collection()

    def test_all_fields(self):

        class Email(Document):
            sender = StringField()
            to = StringField()
            subject = StringField()
            body = StringField()
            content_type = StringField()

        Email.drop_collection()

        email = Email(sender='me', to='you', subject='From Russia with Love', body='Hello!', content_type='text/plain')
        email.save()

        obj = Email.objects.exclude('content_type', 'body').only('to', 'body').all_fields().get()
        self.assertEqual(obj.sender, 'me')
        self.assertEqual(obj.to, 'you')
        self.assertEqual(obj.subject, 'From Russia with Love')
        self.assertEqual(obj.body, 'Hello!')
        self.assertEqual(obj.content_type, 'text/plain')

        Email.drop_collection()

    def test_slicing_fields(self):
        """Ensure that query slicing an array works.
        """
        class Numbers(Document):
            n = ListField(IntField())

        Numbers.drop_collection()

        numbers = Numbers(n=[0, 1, 2, 3, 4, 5, -5, -4, -3, -2, -1])
        numbers.save()

        # first three
        numbers = Numbers.objects.fields(slice__n=3).get()
        self.assertEqual(numbers.n, [0, 1, 2])

        # last three
        numbers = Numbers.objects.fields(slice__n=-3).get()
        self.assertEqual(numbers.n, [-3, -2, -1])

        # skip 2, limit 3
        numbers = Numbers.objects.fields(slice__n=[2, 3]).get()
        self.assertEqual(numbers.n, [2, 3, 4])

        # skip to fifth from last, limit 4
        numbers = Numbers.objects.fields(slice__n=[-5, 4]).get()
        self.assertEqual(numbers.n, [-5, -4, -3, -2])

        # skip to fifth from last, limit 10
        numbers = Numbers.objects.fields(slice__n=[-5, 10]).get()
        self.assertEqual(numbers.n, [-5, -4, -3, -2, -1])

        # skip to fifth from last, limit 10 dict method
        numbers = Numbers.objects.fields(n={"$slice": [-5, 10]}).get()
        self.assertEqual(numbers.n, [-5, -4, -3, -2, -1])

    def test_slicing_nested_fields(self):
        """Ensure that query slicing an embedded array works.
        """

        class EmbeddedNumber(EmbeddedDocument):
            n = ListField(IntField())

        class Numbers(Document):
            embedded = EmbeddedDocumentField(EmbeddedNumber)

        Numbers.drop_collection()

        numbers = Numbers()
        numbers.embedded = EmbeddedNumber(n=[0, 1, 2, 3, 4, 5, -5, -4, -3, -2, -1])
        numbers.save()

        # first three
        numbers = Numbers.objects.fields(slice__embedded__n=3).get()
        self.assertEqual(numbers.embedded.n, [0, 1, 2])

        # last three
        numbers = Numbers.objects.fields(slice__embedded__n=-3).get()
        self.assertEqual(numbers.embedded.n, [-3, -2, -1])

        # skip 2, limit 3
        numbers = Numbers.objects.fields(slice__embedded__n=[2, 3]).get()
        self.assertEqual(numbers.embedded.n, [2, 3, 4])

        # skip to fifth from last, limit 4
        numbers = Numbers.objects.fields(slice__embedded__n=[-5, 4]).get()
        self.assertEqual(numbers.embedded.n, [-5, -4, -3, -2])

        # skip to fifth from last, limit 10
        numbers = Numbers.objects.fields(slice__embedded__n=[-5, 10]).get()
        self.assertEqual(numbers.embedded.n, [-5, -4, -3, -2, -1])

        # skip to fifth from last, limit 10 dict method
        numbers = Numbers.objects.fields(embedded__n={"$slice": [-5, 10]}).get()
        self.assertEqual(numbers.embedded.n, [-5, -4, -3, -2, -1])


    def test_exclude_from_subclasses_docs(self):

        class Base(Document):
            username = StringField()

            meta = {'allow_inheritance': True}

        class Anon(Base):
            anon = BooleanField()

        class User(Base):
            password = StringField()
            wibble = StringField()

        Base.drop_collection()
        User(username="mongodb", password="secret").save()

        user = Base.objects().exclude("password", "wibble").first()
        self.assertEqual(user.password, None)

        self.assertRaises(LookUpError, Base.objects.exclude, "made_up")

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = geo
import sys
sys.path[0:0] = [""]

import unittest
from datetime import datetime, timedelta
from mongoengine import *

__all__ = ("GeoQueriesTest",)


class GeoQueriesTest(unittest.TestCase):

    def setUp(self):
        connect(db='mongoenginetest')

    def test_geospatial_operators(self):
        """Ensure that geospatial queries are working.
        """
        class Event(Document):
            title = StringField()
            date = DateTimeField()
            location = GeoPointField()

            def __unicode__(self):
                return self.title

        Event.drop_collection()

        event1 = Event(title="Coltrane Motion @ Double Door",
                       date=datetime.now() - timedelta(days=1),
                       location=[-87.677137, 41.909889]).save()
        event2 = Event(title="Coltrane Motion @ Bottom of the Hill",
                       date=datetime.now() - timedelta(days=10),
                       location=[-122.4194155, 37.7749295]).save()
        event3 = Event(title="Coltrane Motion @ Empty Bottle",
                       date=datetime.now(),
                       location=[-87.686638, 41.900474]).save()

        # find all events "near" pitchfork office, chicago.
        # note that "near" will show the san francisco event, too,
        # although it sorts to last.
        events = Event.objects(location__near=[-87.67892, 41.9120459])
        self.assertEqual(events.count(), 3)
        self.assertEqual(list(events), [event1, event3, event2])

        # find events within 5 degrees of pitchfork office, chicago
        point_and_distance = [[-87.67892, 41.9120459], 5]
        events = Event.objects(location__within_distance=point_and_distance)
        self.assertEqual(events.count(), 2)
        events = list(events)
        self.assertTrue(event2 not in events)
        self.assertTrue(event1 in events)
        self.assertTrue(event3 in events)

        # ensure ordering is respected by "near"
        events = Event.objects(location__near=[-87.67892, 41.9120459])
        events = events.order_by("-date")
        self.assertEqual(events.count(), 3)
        self.assertEqual(list(events), [event3, event1, event2])

        # find events within 10 degrees of san francisco
        point = [-122.415579, 37.7566023]
        events = Event.objects(location__near=point, location__max_distance=10)
        self.assertEqual(events.count(), 1)
        self.assertEqual(events[0], event2)

        # find events within 10 degrees of san francisco
        point_and_distance = [[-122.415579, 37.7566023], 10]
        events = Event.objects(location__within_distance=point_and_distance)
        self.assertEqual(events.count(), 1)
        self.assertEqual(events[0], event2)

        # find events within 1 degree of greenpoint, broolyn, nyc, ny
        point_and_distance = [[-73.9509714, 40.7237134], 1]
        events = Event.objects(location__within_distance=point_and_distance)
        self.assertEqual(events.count(), 0)

        # ensure ordering is respected by "within_distance"
        point_and_distance = [[-87.67892, 41.9120459], 10]
        events = Event.objects(location__within_distance=point_and_distance)
        events = events.order_by("-date")
        self.assertEqual(events.count(), 2)
        self.assertEqual(events[0], event3)

        # check that within_box works
        box = [(-125.0, 35.0), (-100.0, 40.0)]
        events = Event.objects(location__within_box=box)
        self.assertEqual(events.count(), 1)
        self.assertEqual(events[0].id, event2.id)

        polygon = [
            (-87.694445, 41.912114),
            (-87.69084, 41.919395),
            (-87.681742, 41.927186),
            (-87.654276, 41.911731),
            (-87.656164, 41.898061),
        ]
        events = Event.objects(location__within_polygon=polygon)
        self.assertEqual(events.count(), 1)
        self.assertEqual(events[0].id, event1.id)

        polygon2 = [
            (-1.742249, 54.033586),
            (-1.225891, 52.792797),
            (-4.40094, 53.389881)
        ]
        events = Event.objects(location__within_polygon=polygon2)
        self.assertEqual(events.count(), 0)

    def test_geo_spatial_embedded(self):

        class Venue(EmbeddedDocument):
            location = GeoPointField()
            name = StringField()

        class Event(Document):
            title = StringField()
            venue = EmbeddedDocumentField(Venue)

        Event.drop_collection()

        venue1 = Venue(name="The Rock", location=[-87.677137, 41.909889])
        venue2 = Venue(name="The Bridge", location=[-122.4194155, 37.7749295])

        event1 = Event(title="Coltrane Motion @ Double Door",
                       venue=venue1).save()
        event2 = Event(title="Coltrane Motion @ Bottom of the Hill",
                       venue=venue2).save()
        event3 = Event(title="Coltrane Motion @ Empty Bottle",
                       venue=venue1).save()

        # find all events "near" pitchfork office, chicago.
        # note that "near" will show the san francisco event, too,
        # although it sorts to last.
        events = Event.objects(venue__location__near=[-87.67892, 41.9120459])
        self.assertEqual(events.count(), 3)
        self.assertEqual(list(events), [event1, event3, event2])

    def test_spherical_geospatial_operators(self):
        """Ensure that spherical geospatial queries are working
        """
        class Point(Document):
            location = GeoPointField()

        Point.drop_collection()

        # These points are one degree apart, which (according to Google Maps)
        # is about 110 km apart at this place on the Earth.
        north_point = Point(location=[-122, 38]).save()  # Near Concord, CA
        south_point = Point(location=[-122, 37]).save()  # Near Santa Cruz, CA

        earth_radius = 6378.009  # in km (needs to be a float for dividing by)

        # Finds both points because they are within 60 km of the reference
        # point equidistant between them.
        points = Point.objects(location__near_sphere=[-122, 37.5])
        self.assertEqual(points.count(), 2)

        # Same behavior for _within_spherical_distance
        points = Point.objects(
            location__within_spherical_distance=[[-122, 37.5], 60/earth_radius]
        )
        self.assertEqual(points.count(), 2)

        points = Point.objects(location__near_sphere=[-122, 37.5],
                               location__max_distance=60 / earth_radius)
        self.assertEqual(points.count(), 2)

        # Finds both points, but orders the north point first because it's
        # closer to the reference point to the north.
        points = Point.objects(location__near_sphere=[-122, 38.5])
        self.assertEqual(points.count(), 2)
        self.assertEqual(points[0].id, north_point.id)
        self.assertEqual(points[1].id, south_point.id)

        # Finds both points, but orders the south point first because it's
        # closer to the reference point to the south.
        points = Point.objects(location__near_sphere=[-122, 36.5])
        self.assertEqual(points.count(), 2)
        self.assertEqual(points[0].id, south_point.id)
        self.assertEqual(points[1].id, north_point.id)

        # Finds only one point because only the first point is within 60km of
        # the reference point to the south.
        points = Point.objects(
            location__within_spherical_distance=[[-122, 36.5], 60/earth_radius])
        self.assertEqual(points.count(), 1)
        self.assertEqual(points[0].id, south_point.id)

    def test_2dsphere_point(self):

        class Event(Document):
            title = StringField()
            date = DateTimeField()
            location = PointField()

            def __unicode__(self):
                return self.title

        Event.drop_collection()

        event1 = Event(title="Coltrane Motion @ Double Door",
                       date=datetime.now() - timedelta(days=1),
                       location=[-87.677137, 41.909889])
        event1.save()
        event2 = Event(title="Coltrane Motion @ Bottom of the Hill",
                       date=datetime.now() - timedelta(days=10),
                       location=[-122.4194155, 37.7749295]).save()
        event3 = Event(title="Coltrane Motion @ Empty Bottle",
                       date=datetime.now(),
                       location=[-87.686638, 41.900474]).save()

        # find all events "near" pitchfork office, chicago.
        # note that "near" will show the san francisco event, too,
        # although it sorts to last.
        events = Event.objects(location__near=[-87.67892, 41.9120459])
        self.assertEqual(events.count(), 3)
        self.assertEqual(list(events), [event1, event3, event2])

        # find events within 5 degrees of pitchfork office, chicago
        point_and_distance = [[-87.67892, 41.9120459], 2]
        events = Event.objects(location__geo_within_center=point_and_distance)
        self.assertEqual(events.count(), 2)
        events = list(events)
        self.assertTrue(event2 not in events)
        self.assertTrue(event1 in events)
        self.assertTrue(event3 in events)

        # ensure ordering is respected by "near"
        events = Event.objects(location__near=[-87.67892, 41.9120459])
        events = events.order_by("-date")
        self.assertEqual(events.count(), 3)
        self.assertEqual(list(events), [event3, event1, event2])

        # find events within 10km of san francisco
        point = [-122.415579, 37.7566023]
        events = Event.objects(location__near=point, location__max_distance=10000)
        self.assertEqual(events.count(), 1)
        self.assertEqual(events[0], event2)

        # find events within 1km of greenpoint, broolyn, nyc, ny
        events = Event.objects(location__near=[-73.9509714, 40.7237134], location__max_distance=1000)
        self.assertEqual(events.count(), 0)

        # ensure ordering is respected by "near"
        events = Event.objects(location__near=[-87.67892, 41.9120459],
                               location__max_distance=10000).order_by("-date")
        self.assertEqual(events.count(), 2)
        self.assertEqual(events[0], event3)

        # check that within_box works
        box = [(-125.0, 35.0), (-100.0, 40.0)]
        events = Event.objects(location__geo_within_box=box)
        self.assertEqual(events.count(), 1)
        self.assertEqual(events[0].id, event2.id)

        polygon = [
            (-87.694445, 41.912114),
            (-87.69084, 41.919395),
            (-87.681742, 41.927186),
            (-87.654276, 41.911731),
            (-87.656164, 41.898061),
        ]
        events = Event.objects(location__geo_within_polygon=polygon)
        self.assertEqual(events.count(), 1)
        self.assertEqual(events[0].id, event1.id)

        polygon2 = [
            (-1.742249, 54.033586),
            (-1.225891, 52.792797),
            (-4.40094, 53.389881)
        ]
        events = Event.objects(location__geo_within_polygon=polygon2)
        self.assertEqual(events.count(), 0)

    def test_2dsphere_point_embedded(self):

        class Venue(EmbeddedDocument):
            location = GeoPointField()
            name = StringField()

        class Event(Document):
            title = StringField()
            venue = EmbeddedDocumentField(Venue)

        Event.drop_collection()

        venue1 = Venue(name="The Rock", location=[-87.677137, 41.909889])
        venue2 = Venue(name="The Bridge", location=[-122.4194155, 37.7749295])

        event1 = Event(title="Coltrane Motion @ Double Door",
                       venue=venue1).save()
        event2 = Event(title="Coltrane Motion @ Bottom of the Hill",
                       venue=venue2).save()
        event3 = Event(title="Coltrane Motion @ Empty Bottle",
                       venue=venue1).save()

        # find all events "near" pitchfork office, chicago.
        # note that "near" will show the san francisco event, too,
        # although it sorts to last.
        events = Event.objects(venue__location__near=[-87.67892, 41.9120459])
        self.assertEqual(events.count(), 3)
        self.assertEqual(list(events), [event1, event3, event2])

    def test_linestring(self):

        class Road(Document):
            name = StringField()
            line = LineStringField()

        Road.drop_collection()

        Road(name="66", line=[[40, 5], [41, 6]]).save()

        # near
        point = {"type": "Point", "coordinates": [40, 5]}
        roads = Road.objects.filter(line__near=point["coordinates"]).count()
        self.assertEqual(1, roads)

        roads = Road.objects.filter(line__near=point).count()
        self.assertEqual(1, roads)

        roads = Road.objects.filter(line__near={"$geometry": point}).count()
        self.assertEqual(1, roads)

        # Within
        polygon = {"type": "Polygon",
                   "coordinates": [[[40, 5], [40, 6], [41, 6], [41, 5], [40, 5]]]}
        roads = Road.objects.filter(line__geo_within=polygon["coordinates"]).count()
        self.assertEqual(1, roads)

        roads = Road.objects.filter(line__geo_within=polygon).count()
        self.assertEqual(1, roads)

        roads = Road.objects.filter(line__geo_within={"$geometry": polygon}).count()
        self.assertEqual(1, roads)

        # Intersects
        line = {"type": "LineString",
                "coordinates": [[40, 5], [40, 6]]}
        roads = Road.objects.filter(line__geo_intersects=line["coordinates"]).count()
        self.assertEqual(1, roads)

        roads = Road.objects.filter(line__geo_intersects=line).count()
        self.assertEqual(1, roads)

        roads = Road.objects.filter(line__geo_intersects={"$geometry": line}).count()
        self.assertEqual(1, roads)

        polygon = {"type": "Polygon",
                   "coordinates": [[[40, 5], [40, 6], [41, 6], [41, 5], [40, 5]]]}
        roads = Road.objects.filter(line__geo_intersects=polygon["coordinates"]).count()
        self.assertEqual(1, roads)

        roads = Road.objects.filter(line__geo_intersects=polygon).count()
        self.assertEqual(1, roads)

        roads = Road.objects.filter(line__geo_intersects={"$geometry": polygon}).count()
        self.assertEqual(1, roads)

    def test_polygon(self):

        class Road(Document):
            name = StringField()
            poly = PolygonField()

        Road.drop_collection()

        Road(name="66", poly=[[[40, 5], [40, 6], [41, 6], [40, 5]]]).save()

        # near
        point = {"type": "Point", "coordinates": [40, 5]}
        roads = Road.objects.filter(poly__near=point["coordinates"]).count()
        self.assertEqual(1, roads)

        roads = Road.objects.filter(poly__near=point).count()
        self.assertEqual(1, roads)

        roads = Road.objects.filter(poly__near={"$geometry": point}).count()
        self.assertEqual(1, roads)

        # Within
        polygon = {"type": "Polygon",
                   "coordinates": [[[40, 5], [40, 6], [41, 6], [41, 5], [40, 5]]]}
        roads = Road.objects.filter(poly__geo_within=polygon["coordinates"]).count()
        self.assertEqual(1, roads)

        roads = Road.objects.filter(poly__geo_within=polygon).count()
        self.assertEqual(1, roads)

        roads = Road.objects.filter(poly__geo_within={"$geometry": polygon}).count()
        self.assertEqual(1, roads)

        # Intersects
        line = {"type": "LineString",
                "coordinates": [[40, 5], [41, 6]]}
        roads = Road.objects.filter(poly__geo_intersects=line["coordinates"]).count()
        self.assertEqual(1, roads)

        roads = Road.objects.filter(poly__geo_intersects=line).count()
        self.assertEqual(1, roads)

        roads = Road.objects.filter(poly__geo_intersects={"$geometry": line}).count()
        self.assertEqual(1, roads)

        polygon = {"type": "Polygon",
                   "coordinates": [[[40, 5], [40, 6], [41, 6], [41, 5], [40, 5]]]}
        roads = Road.objects.filter(poly__geo_intersects=polygon["coordinates"]).count()
        self.assertEqual(1, roads)

        roads = Road.objects.filter(poly__geo_intersects=polygon).count()
        self.assertEqual(1, roads)

        roads = Road.objects.filter(poly__geo_intersects={"$geometry": polygon}).count()
        self.assertEqual(1, roads)

    def test_2dsphere_point_sets_correctly(self):
        class Location(Document):
            loc = PointField()

        Location.drop_collection()

        Location(loc=[1,2]).save()
        loc = Location.objects.as_pymongo()[0]
        self.assertEqual(loc["loc"], {"type": "Point", "coordinates": [1, 2]})

        Location.objects.update(set__loc=[2,1])
        loc = Location.objects.as_pymongo()[0]
        self.assertEqual(loc["loc"], {"type": "Point", "coordinates": [2, 1]})

    def test_2dsphere_linestring_sets_correctly(self):
        class Location(Document):
            line = LineStringField()

        Location.drop_collection()

        Location(line=[[1, 2], [2, 2]]).save()
        loc = Location.objects.as_pymongo()[0]
        self.assertEqual(loc["line"], {"type": "LineString", "coordinates": [[1, 2], [2, 2]]})

        Location.objects.update(set__line=[[2, 1], [1, 2]])
        loc = Location.objects.as_pymongo()[0]
        self.assertEqual(loc["line"], {"type": "LineString", "coordinates": [[2, 1], [1, 2]]})

    def test_geojson_PolygonField(self):
        class Location(Document):
            poly = PolygonField()

        Location.drop_collection()

        Location(poly=[[[40, 5], [40, 6], [41, 6], [40, 5]]]).save()
        loc = Location.objects.as_pymongo()[0]
        self.assertEqual(loc["poly"], {"type": "Polygon", "coordinates": [[[40, 5], [40, 6], [41, 6], [40, 5]]]})

        Location.objects.update(set__poly=[[[40, 4], [40, 6], [41, 6], [40, 4]]])
        loc = Location.objects.as_pymongo()[0]
        self.assertEqual(loc["poly"], {"type": "Polygon", "coordinates": [[[40, 4], [40, 6], [41, 6], [40, 4]]]})

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = queryset
import sys
sys.path[0:0] = [""]

import unittest
import uuid
from nose.plugins.skip import SkipTest

from datetime import datetime, timedelta

import pymongo
from pymongo.errors import ConfigurationError
from pymongo.read_preferences import ReadPreference

from bson import ObjectId

from mongoengine import *
from mongoengine.connection import get_connection
from mongoengine.python_support import PY3
from mongoengine.context_managers import query_counter
from mongoengine.queryset import (QuerySet, QuerySetManager,
                                  MultipleObjectsReturned, DoesNotExist,
                                  queryset_manager)
from mongoengine.errors import InvalidQueryError

__all__ = ("QuerySetTest",)


class QuerySetTest(unittest.TestCase):

    def setUp(self):
        connect(db='mongoenginetest')

        class PersonMeta(EmbeddedDocument):
            weight = IntField()

        class Person(Document):
            name = StringField()
            age = IntField()
            person_meta = EmbeddedDocumentField(PersonMeta)
            meta = {'allow_inheritance': True}

        Person.drop_collection()
        self.PersonMeta = PersonMeta
        self.Person = Person

    def test_initialisation(self):
        """Ensure that a QuerySet is correctly initialised by QuerySetManager.
        """
        self.assertTrue(isinstance(self.Person.objects, QuerySet))
        self.assertEqual(self.Person.objects._collection.name,
                         self.Person._get_collection_name())
        self.assertTrue(isinstance(self.Person.objects._collection,
                                   pymongo.collection.Collection))

    def test_cannot_perform_joins_references(self):

        class BlogPost(Document):
            author = ReferenceField(self.Person)
            author2 = GenericReferenceField()

        def test_reference():
            list(BlogPost.objects(author__name="test"))

        self.assertRaises(InvalidQueryError, test_reference)

        def test_generic_reference():
            list(BlogPost.objects(author2__name="test"))

    def test_find(self):
        """Ensure that a query returns a valid set of results.
        """
        self.Person(name="User A", age=20).save()
        self.Person(name="User B", age=30).save()

        # Find all people in the collection
        people = self.Person.objects
        self.assertEqual(people.count(), 2)
        results = list(people)
        self.assertTrue(isinstance(results[0], self.Person))
        self.assertTrue(isinstance(results[0].id, (ObjectId, str, unicode)))
        self.assertEqual(results[0].name, "User A")
        self.assertEqual(results[0].age, 20)
        self.assertEqual(results[1].name, "User B")
        self.assertEqual(results[1].age, 30)

        # Use a query to filter the people found to just person1
        people = self.Person.objects(age=20)
        self.assertEqual(people.count(), 1)
        person = people.next()
        self.assertEqual(person.name, "User A")
        self.assertEqual(person.age, 20)

        # Test limit
        people = list(self.Person.objects.limit(1))
        self.assertEqual(len(people), 1)
        self.assertEqual(people[0].name, 'User A')

        # Test skip
        people = list(self.Person.objects.skip(1))
        self.assertEqual(len(people), 1)
        self.assertEqual(people[0].name, 'User B')

        person3 = self.Person(name="User C", age=40)
        person3.save()

        # Test slice limit
        people = list(self.Person.objects[:2])
        self.assertEqual(len(people), 2)
        self.assertEqual(people[0].name, 'User A')
        self.assertEqual(people[1].name, 'User B')

        # Test slice skip
        people = list(self.Person.objects[1:])
        self.assertEqual(len(people), 2)
        self.assertEqual(people[0].name, 'User B')
        self.assertEqual(people[1].name, 'User C')

        # Test slice limit and skip
        people = list(self.Person.objects[1:2])
        self.assertEqual(len(people), 1)
        self.assertEqual(people[0].name, 'User B')

        # Test slice limit and skip cursor reset
        qs = self.Person.objects[1:2]
        # fetch then delete the cursor
        qs._cursor
        qs._cursor_obj = None
        people = list(qs)
        self.assertEqual(len(people), 1)
        self.assertEqual(people[0].name, 'User B')

        people = list(self.Person.objects[1:1])
        self.assertEqual(len(people), 0)

        # Test slice out of range
        people = list(self.Person.objects[80000:80001])
        self.assertEqual(len(people), 0)

        # Test larger slice __repr__
        self.Person.objects.delete()
        for i in xrange(55):
            self.Person(name='A%s' % i, age=i).save()

        self.assertEqual(self.Person.objects.count(), 55)
        self.assertEqual("Person object", "%s" % self.Person.objects[0])
        self.assertEqual("[<Person: Person object>, <Person: Person object>]",  "%s" % self.Person.objects[1:3])
        self.assertEqual("[<Person: Person object>, <Person: Person object>]",  "%s" % self.Person.objects[51:53])

    def test_find_one(self):
        """Ensure that a query using find_one returns a valid result.
        """
        person1 = self.Person(name="User A", age=20)
        person1.save()
        person2 = self.Person(name="User B", age=30)
        person2.save()

        # Retrieve the first person from the database
        person = self.Person.objects.first()
        self.assertTrue(isinstance(person, self.Person))
        self.assertEqual(person.name, "User A")
        self.assertEqual(person.age, 20)

        # Use a query to filter the people found to just person2
        person = self.Person.objects(age=30).first()
        self.assertEqual(person.name, "User B")

        person = self.Person.objects(age__lt=30).first()
        self.assertEqual(person.name, "User A")

        # Use array syntax
        person = self.Person.objects[0]
        self.assertEqual(person.name, "User A")

        person = self.Person.objects[1]
        self.assertEqual(person.name, "User B")

        self.assertRaises(IndexError, self.Person.objects.__getitem__, 2)

        # Find a document using just the object id
        person = self.Person.objects.with_id(person1.id)
        self.assertEqual(person.name, "User A")

        self.assertRaises(InvalidQueryError, self.Person.objects(name="User A").with_id, person1.id)

    def test_find_only_one(self):
        """Ensure that a query using ``get`` returns at most one result.
        """
        # Try retrieving when no objects exists
        self.assertRaises(DoesNotExist, self.Person.objects.get)
        self.assertRaises(self.Person.DoesNotExist, self.Person.objects.get)

        person1 = self.Person(name="User A", age=20)
        person1.save()
        person2 = self.Person(name="User B", age=30)
        person2.save()

        # Retrieve the first person from the database
        self.assertRaises(MultipleObjectsReturned, self.Person.objects.get)
        self.assertRaises(self.Person.MultipleObjectsReturned,
                          self.Person.objects.get)

        # Use a query to filter the people found to just person2
        person = self.Person.objects.get(age=30)
        self.assertEqual(person.name, "User B")

        person = self.Person.objects.get(age__lt=30)
        self.assertEqual(person.name, "User A")

    def test_find_array_position(self):
        """Ensure that query by array position works.
        """
        class Comment(EmbeddedDocument):
            name = StringField()

        class Post(EmbeddedDocument):
            comments = ListField(EmbeddedDocumentField(Comment))

        class Blog(Document):
            tags = ListField(StringField())
            posts = ListField(EmbeddedDocumentField(Post))

        Blog.drop_collection()

        Blog.objects.create(tags=['a', 'b'])
        self.assertEqual(Blog.objects(tags__0='a').count(), 1)
        self.assertEqual(Blog.objects(tags__0='b').count(), 0)
        self.assertEqual(Blog.objects(tags__1='a').count(), 0)
        self.assertEqual(Blog.objects(tags__1='b').count(), 1)

        Blog.drop_collection()

        comment1 = Comment(name='testa')
        comment2 = Comment(name='testb')
        post1 = Post(comments=[comment1, comment2])
        post2 = Post(comments=[comment2, comment2])
        blog1 = Blog.objects.create(posts=[post1, post2])
        blog2 = Blog.objects.create(posts=[post2, post1])

        blog = Blog.objects(posts__0__comments__0__name='testa').get()
        self.assertEqual(blog, blog1)

        query = Blog.objects(posts__1__comments__1__name='testb')
        self.assertEqual(query.count(), 2)

        query = Blog.objects(posts__1__comments__1__name='testa')
        self.assertEqual(query.count(), 0)

        query = Blog.objects(posts__0__comments__1__name='testa')
        self.assertEqual(query.count(), 0)

        Blog.drop_collection()

    def test_none(self):
        class A(Document):
            s = StringField()

        A.drop_collection()
        A().save()

        self.assertEqual(list(A.objects.none()), [])
        self.assertEqual(list(A.objects.none().all()), [])

    def test_chaining(self):
        class A(Document):
            s = StringField()

        class B(Document):
            ref = ReferenceField(A)
            boolfield = BooleanField(default=False)

        A.drop_collection()
        B.drop_collection()

        a1 = A(s="test1").save()
        a2 = A(s="test2").save()

        B(ref=a1, boolfield=True).save()

        # Works
        q1 = B.objects.filter(ref__in=[a1, a2], ref=a1)._query

        # Doesn't work
        q2 = B.objects.filter(ref__in=[a1, a2])
        q2 = q2.filter(ref=a1)._query
        self.assertEqual(q1, q2)

        a_objects = A.objects(s='test1')
        query = B.objects(ref__in=a_objects)
        query = query.filter(boolfield=True)
        self.assertEqual(query.count(), 1)

    def test_update_write_concern(self):
        """Test that passing write_concern works"""

        self.Person.drop_collection()

        write_concern = {"fsync": True}

        author, created = self.Person.objects.get_or_create(
            name='Test User', write_concern=write_concern)
        author.save(write_concern=write_concern)

        result = self.Person.objects.update(
            set__name='Ross', write_concern={"w": 1})
        self.assertEqual(result, 1)
        result = self.Person.objects.update(
            set__name='Ross', write_concern={"w": 0})
        self.assertEqual(result, None)

        result = self.Person.objects.update_one(
            set__name='Test User', write_concern={"w": 1})
        self.assertEqual(result, 1)
        result = self.Person.objects.update_one(
            set__name='Test User', write_concern={"w": 0})
        self.assertEqual(result, None)

    def test_update_update_has_a_value(self):
        """Test to ensure that update is passed a value to update to"""
        self.Person.drop_collection()

        author = self.Person(name='Test User')
        author.save()

        def update_raises():
            self.Person.objects(pk=author.pk).update({})

        def update_one_raises():
            self.Person.objects(pk=author.pk).update_one({})

        self.assertRaises(OperationError, update_raises)
        self.assertRaises(OperationError, update_one_raises)

    def test_update_array_position(self):
        """Ensure that updating by array position works.

        Check update() and update_one() can take syntax like:
            set__posts__1__comments__1__name="testc"
        Check that it only works for ListFields.
        """
        class Comment(EmbeddedDocument):
            name = StringField()

        class Post(EmbeddedDocument):
            comments = ListField(EmbeddedDocumentField(Comment))

        class Blog(Document):
            tags = ListField(StringField())
            posts = ListField(EmbeddedDocumentField(Post))

        Blog.drop_collection()

        comment1 = Comment(name='testa')
        comment2 = Comment(name='testb')
        post1 = Post(comments=[comment1, comment2])
        post2 = Post(comments=[comment2, comment2])
        Blog.objects.create(posts=[post1, post2])
        Blog.objects.create(posts=[post2, post1])

        # Update all of the first comments of second posts of all blogs
        Blog.objects().update(set__posts__1__comments__0__name="testc")
        testc_blogs = Blog.objects(posts__1__comments__0__name="testc")
        self.assertEqual(testc_blogs.count(), 2)

        Blog.drop_collection()
        Blog.objects.create(posts=[post1, post2])
        Blog.objects.create(posts=[post2, post1])

        # Update only the first blog returned by the query
        Blog.objects().update_one(
            set__posts__1__comments__1__name="testc")
        testc_blogs = Blog.objects(posts__1__comments__1__name="testc")
        self.assertEqual(testc_blogs.count(), 1)

        # Check that using this indexing syntax on a non-list fails
        def non_list_indexing():
            Blog.objects().update(set__posts__1__comments__0__name__1="asdf")
        self.assertRaises(InvalidQueryError, non_list_indexing)

        Blog.drop_collection()

    def test_update_using_positional_operator(self):
        """Ensure that the list fields can be updated using the positional
        operator."""

        class Comment(EmbeddedDocument):
            by = StringField()
            votes = IntField()

        class BlogPost(Document):
            title = StringField()
            comments = ListField(EmbeddedDocumentField(Comment))

        BlogPost.drop_collection()

        c1 = Comment(by="joe", votes=3)
        c2 = Comment(by="jane", votes=7)

        BlogPost(title="ABC", comments=[c1, c2]).save()

        BlogPost.objects(comments__by="jane").update(inc__comments__S__votes=1)

        post = BlogPost.objects.first()
        self.assertEqual(post.comments[1].by, 'jane')
        self.assertEqual(post.comments[1].votes, 8)

    def test_update_using_positional_operator_matches_first(self):

        # Currently the $ operator only applies to the first matched item in
        # the query

        class Simple(Document):
            x = ListField()

        Simple.drop_collection()
        Simple(x=[1, 2, 3, 2]).save()
        Simple.objects(x=2).update(inc__x__S=1)

        simple = Simple.objects.first()
        self.assertEqual(simple.x, [1, 3, 3, 2])
        Simple.drop_collection()

        # You can set multiples
        Simple.drop_collection()
        Simple(x=[1, 2, 3, 4]).save()
        Simple(x=[2, 3, 4, 5]).save()
        Simple(x=[3, 4, 5, 6]).save()
        Simple(x=[4, 5, 6, 7]).save()
        Simple.objects(x=3).update(set__x__S=0)

        s = Simple.objects()
        self.assertEqual(s[0].x, [1, 2, 0, 4])
        self.assertEqual(s[1].x, [2, 0, 4, 5])
        self.assertEqual(s[2].x, [0, 4, 5, 6])
        self.assertEqual(s[3].x, [4, 5, 6, 7])

        # Using "$unset" with an expression like this "array.$" will result in
        # the array item becoming None, not being removed.
        Simple.drop_collection()
        Simple(x=[1, 2, 3, 4, 3, 2, 3, 4]).save()
        Simple.objects(x=3).update(unset__x__S=1)
        simple = Simple.objects.first()
        self.assertEqual(simple.x, [1, 2, None, 4, 3, 2, 3, 4])

        # Nested updates arent supported yet..
        def update_nested():
            Simple.drop_collection()
            Simple(x=[{'test': [1, 2, 3, 4]}]).save()
            Simple.objects(x__test=2).update(set__x__S__test__S=3)
            self.assertEqual(simple.x, [1, 2, 3, 4])

        self.assertRaises(OperationError, update_nested)
        Simple.drop_collection()

    def test_update_using_positional_operator_embedded_document(self):
        """Ensure that the embedded documents can be updated using the positional
        operator."""

        class Vote(EmbeddedDocument):
            score = IntField()

        class Comment(EmbeddedDocument):
            by = StringField()
            votes = EmbeddedDocumentField(Vote)

        class BlogPost(Document):
            title = StringField()
            comments = ListField(EmbeddedDocumentField(Comment))

        BlogPost.drop_collection()

        c1 = Comment(by="joe", votes=Vote(score=3))
        c2 = Comment(by="jane", votes=Vote(score=7))

        BlogPost(title="ABC", comments=[c1, c2]).save()

        BlogPost.objects(comments__by="joe").update(set__comments__S__votes=Vote(score=4))

        post = BlogPost.objects.first()
        self.assertEqual(post.comments[0].by, 'joe')
        self.assertEqual(post.comments[0].votes.score, 4)

    def test_updates_can_have_match_operators(self):

        class Post(Document):
            title = StringField(required=True)
            tags = ListField(StringField())
            comments = ListField(EmbeddedDocumentField("Comment"))

        class Comment(EmbeddedDocument):
            content = StringField()
            name = StringField(max_length=120)
            vote = IntField()

        Post.drop_collection()

        comm1 = Comment(content="very funny indeed", name="John S", vote=1)
        comm2 = Comment(content="kind of funny", name="Mark P", vote=0)

        Post(title='Fun with MongoEngine', tags=['mongodb', 'mongoengine'],
             comments=[comm1, comm2]).save()

        Post.objects().update_one(pull__comments__vote__lt=1)

        self.assertEqual(1, len(Post.objects.first().comments))

    def test_mapfield_update(self):
        """Ensure that the MapField can be updated."""
        class Member(EmbeddedDocument):
            gender = StringField()
            age = IntField()

        class Club(Document):
            members = MapField(EmbeddedDocumentField(Member))

        Club.drop_collection()

        club = Club()
        club.members['John'] = Member(gender="M", age=13)
        club.save()

        Club.objects().update(
            set__members={"John": Member(gender="F", age=14)})

        club = Club.objects().first()
        self.assertEqual(club.members['John'].gender, "F")
        self.assertEqual(club.members['John'].age, 14)

    def test_dictfield_update(self):
        """Ensure that the DictField can be updated."""
        class Club(Document):
            members = DictField()

        club = Club()
        club.members['John'] = dict(gender="M", age=13)
        club.save()

        Club.objects().update(
            set__members={"John": dict(gender="F", age=14)})

        club = Club.objects().first()
        self.assertEqual(club.members['John']['gender'], "F")
        self.assertEqual(club.members['John']['age'], 14)

    def test_update_results(self):
        self.Person.drop_collection()

        result = self.Person(name="Bob", age=25).update(upsert=True, full_result=True)
        self.assertTrue(isinstance(result, dict))
        self.assertTrue("upserted" in result)
        self.assertFalse(result["updatedExisting"])

        bob = self.Person.objects.first()
        result = bob.update(set__age=30, full_result=True)
        self.assertTrue(isinstance(result, dict))
        self.assertTrue(result["updatedExisting"])

        self.Person(name="Bob", age=20).save()
        result = self.Person.objects(name="Bob").update(set__name="bobby", multi=True)
        self.assertEqual(result, 2)

    def test_upsert(self):
        self.Person.drop_collection()

        self.Person.objects(pk=ObjectId(), name="Bob", age=30).update(upsert=True)

        bob = self.Person.objects.first()
        self.assertEqual("Bob", bob.name)
        self.assertEqual(30, bob.age)

    def test_upsert_one(self):
        self.Person.drop_collection()

        self.Person.objects(name="Bob", age=30).update_one(upsert=True)

        bob = self.Person.objects.first()
        self.assertEqual("Bob", bob.name)
        self.assertEqual(30, bob.age)

    def test_set_on_insert(self):
        self.Person.drop_collection()

        self.Person.objects(pk=ObjectId()).update(set__name='Bob', set_on_insert__age=30, upsert=True)

        bob = self.Person.objects.first()
        self.assertEqual("Bob", bob.name)
        self.assertEqual(30, bob.age)

    def test_get_or_create(self):
        """Ensure that ``get_or_create`` returns one result or creates a new
        document.
        """
        person1 = self.Person(name="User A", age=20)
        person1.save()
        person2 = self.Person(name="User B", age=30)
        person2.save()

        # Retrieve the first person from the database
        self.assertRaises(MultipleObjectsReturned,
                          self.Person.objects.get_or_create)
        self.assertRaises(self.Person.MultipleObjectsReturned,
                          self.Person.objects.get_or_create)

        # Use a query to filter the people found to just person2
        person, created = self.Person.objects.get_or_create(age=30)
        self.assertEqual(person.name, "User B")
        self.assertEqual(created, False)

        person, created = self.Person.objects.get_or_create(age__lt=30)
        self.assertEqual(person.name, "User A")
        self.assertEqual(created, False)

        # Try retrieving when no objects exists - new doc should be created
        kwargs = dict(age=50, defaults={'name': 'User C'})
        person, created = self.Person.objects.get_or_create(**kwargs)
        self.assertEqual(created, True)

        person = self.Person.objects.get(age=50)
        self.assertEqual(person.name, "User C")

    def test_bulk_insert(self):
        """Ensure that bulk insert works
        """

        class Comment(EmbeddedDocument):
            name = StringField()

        class Post(EmbeddedDocument):
            comments = ListField(EmbeddedDocumentField(Comment))

        class Blog(Document):
            title = StringField(unique=True)
            tags = ListField(StringField())
            posts = ListField(EmbeddedDocumentField(Post))

        Blog.drop_collection()

        # Recreates the collection
        self.assertEqual(0, Blog.objects.count())

        with query_counter() as q:
            self.assertEqual(q, 0)

            comment1 = Comment(name='testa')
            comment2 = Comment(name='testb')
            post1 = Post(comments=[comment1, comment2])
            post2 = Post(comments=[comment2, comment2])

            blogs = []
            for i in xrange(1, 100):
                blogs.append(Blog(title="post %s" % i, posts=[post1, post2]))

            Blog.objects.insert(blogs, load_bulk=False)
            self.assertEqual(q, 1)  # 1 for the insert

        Blog.drop_collection()
        Blog.ensure_indexes()

        with query_counter() as q:
            self.assertEqual(q, 0)

            Blog.objects.insert(blogs)
            self.assertEqual(q, 2)  # 1 for insert, and 1 for in bulk fetch

        Blog.drop_collection()

        comment1 = Comment(name='testa')
        comment2 = Comment(name='testb')
        post1 = Post(comments=[comment1, comment2])
        post2 = Post(comments=[comment2, comment2])
        blog1 = Blog(title="code", posts=[post1, post2])
        blog2 = Blog(title="mongodb", posts=[post2, post1])
        blog1, blog2 = Blog.objects.insert([blog1, blog2])
        self.assertEqual(blog1.title, "code")
        self.assertEqual(blog2.title, "mongodb")

        self.assertEqual(Blog.objects.count(), 2)

        # test handles people trying to upsert
        def throw_operation_error():
            blogs = Blog.objects
            Blog.objects.insert(blogs)

        self.assertRaises(OperationError, throw_operation_error)

        # Test can insert new doc
        new_post = Blog(title="code123", id=ObjectId())
        Blog.objects.insert(new_post)

        # test handles other classes being inserted
        def throw_operation_error_wrong_doc():
            class Author(Document):
                pass
            Blog.objects.insert(Author())

        self.assertRaises(OperationError, throw_operation_error_wrong_doc)

        def throw_operation_error_not_a_document():
            Blog.objects.insert("HELLO WORLD")

        self.assertRaises(OperationError, throw_operation_error_not_a_document)

        Blog.drop_collection()

        blog1 = Blog(title="code", posts=[post1, post2])
        blog1 = Blog.objects.insert(blog1)
        self.assertEqual(blog1.title, "code")
        self.assertEqual(Blog.objects.count(), 1)

        Blog.drop_collection()
        blog1 = Blog(title="code", posts=[post1, post2])
        obj_id = Blog.objects.insert(blog1, load_bulk=False)
        self.assertEqual(obj_id.__class__.__name__, 'ObjectId')

        Blog.drop_collection()
        post3 = Post(comments=[comment1, comment1])
        blog1 = Blog(title="foo", posts=[post1, post2])
        blog2 = Blog(title="bar", posts=[post2, post3])
        blog3 = Blog(title="baz", posts=[post1, post2])
        Blog.objects.insert([blog1, blog2])

        def throw_operation_error_not_unique():
            Blog.objects.insert([blog2, blog3])

        self.assertRaises(NotUniqueError, throw_operation_error_not_unique)
        self.assertEqual(Blog.objects.count(), 2)

        Blog.objects.insert([blog2, blog3], write_concern={"w": 0,
                            'continue_on_error': True})
        self.assertEqual(Blog.objects.count(), 3)

    def test_get_changed_fields_query_count(self):

        class Person(Document):
            name = StringField()
            owns = ListField(ReferenceField('Organization'))
            projects = ListField(ReferenceField('Project'))

        class Organization(Document):
            name = StringField()
            owner = ReferenceField('Person')
            employees = ListField(ReferenceField('Person'))

        class Project(Document):
            name = StringField()

        Person.drop_collection()
        Organization.drop_collection()
        Project.drop_collection()

        r1 = Project(name="r1").save()
        r2 = Project(name="r2").save()
        r3 = Project(name="r3").save()
        p1 = Person(name="p1", projects=[r1, r2]).save()
        p2 = Person(name="p2", projects=[r2, r3]).save()
        o1 = Organization(name="o1", employees=[p1]).save()

        with query_counter() as q:
            self.assertEqual(q, 0)

            fresh_o1 = Organization.objects.get(id=o1.id)
            self.assertEqual(1, q)
            fresh_o1._get_changed_fields()
            self.assertEqual(1, q)

        with query_counter() as q:
            self.assertEqual(q, 0)

            fresh_o1 = Organization.objects.get(id=o1.id)
            fresh_o1.save()   # No changes, does nothing

            self.assertEqual(q, 1)

        with query_counter() as q:
            self.assertEqual(q, 0)

            fresh_o1 = Organization.objects.get(id=o1.id)
            fresh_o1.save(cascade=False)  # No changes, does nothing

            self.assertEqual(q, 1)

        with query_counter() as q:
            self.assertEqual(q, 0)

            fresh_o1 = Organization.objects.get(id=o1.id)
            fresh_o1.employees.append(p2)  # Dereferences
            fresh_o1.save(cascade=False)   # Saves

            self.assertEqual(q, 3)

    def test_slave_okay(self):
        """Ensures that a query can take slave_okay syntax
        """
        person1 = self.Person(name="User A", age=20)
        person1.save()
        person2 = self.Person(name="User B", age=30)
        person2.save()

        # Retrieve the first person from the database
        person = self.Person.objects.slave_okay(True).first()
        self.assertTrue(isinstance(person, self.Person))
        self.assertEqual(person.name, "User A")
        self.assertEqual(person.age, 20)

    def test_cursor_args(self):
        """Ensures the cursor args can be set as expected
        """
        p = self.Person.objects
        # Check default
        self.assertEqual(p._cursor_args,
                {'snapshot': False, 'slave_okay': False, 'timeout': True})

        p = p.snapshot(False).slave_okay(False).timeout(False)
        self.assertEqual(p._cursor_args,
                {'snapshot': False, 'slave_okay': False, 'timeout': False})

        p = p.snapshot(True).slave_okay(False).timeout(False)
        self.assertEqual(p._cursor_args,
                {'snapshot': True, 'slave_okay': False, 'timeout': False})

        p = p.snapshot(True).slave_okay(True).timeout(False)
        self.assertEqual(p._cursor_args,
                {'snapshot': True, 'slave_okay': True, 'timeout': False})

        p = p.snapshot(True).slave_okay(True).timeout(True)
        self.assertEqual(p._cursor_args,
                         {'snapshot': True, 'slave_okay': True, 'timeout': True})

    def test_repeated_iteration(self):
        """Ensure that QuerySet rewinds itself one iteration finishes.
        """
        self.Person(name='Person 1').save()
        self.Person(name='Person 2').save()

        queryset = self.Person.objects
        people1 = [person for person in queryset]
        people2 = [person for person in queryset]

        # Check that it still works even if iteration is interrupted.
        for person in queryset:
            break
        people3 = [person for person in queryset]

        self.assertEqual(people1, people2)
        self.assertEqual(people1, people3)

    def test_repr(self):
        """Test repr behavior isnt destructive"""

        class Doc(Document):
            number = IntField()

            def __repr__(self):
                return "<Doc: %s>" % self.number

        Doc.drop_collection()

        for i in xrange(1000):
            Doc(number=i).save()

        docs = Doc.objects.order_by('number')

        self.assertEqual(docs.count(), 1000)

        docs_string = "%s" % docs
        self.assertTrue("Doc: 0" in docs_string)

        self.assertEqual(docs.count(), 1000)
        self.assertTrue('(remaining elements truncated)' in "%s" % docs)

        # Limit and skip
        docs = docs[1:4]
        self.assertEqual('[<Doc: 1>, <Doc: 2>, <Doc: 3>]', "%s" % docs)

        self.assertEqual(docs.count(), 3)
        for doc in docs:
            self.assertEqual('.. queryset mid-iteration ..', repr(docs))

    def test_regex_query_shortcuts(self):
        """Ensure that contains, startswith, endswith, etc work.
        """
        person = self.Person(name='Guido van Rossum')
        person.save()

        # Test contains
        obj = self.Person.objects(name__contains='van').first()
        self.assertEqual(obj, person)
        obj = self.Person.objects(name__contains='Van').first()
        self.assertEqual(obj, None)

        # Test icontains
        obj = self.Person.objects(name__icontains='Van').first()
        self.assertEqual(obj, person)

        # Test startswith
        obj = self.Person.objects(name__startswith='Guido').first()
        self.assertEqual(obj, person)
        obj = self.Person.objects(name__startswith='guido').first()
        self.assertEqual(obj, None)

        # Test istartswith
        obj = self.Person.objects(name__istartswith='guido').first()
        self.assertEqual(obj, person)

        # Test endswith
        obj = self.Person.objects(name__endswith='Rossum').first()
        self.assertEqual(obj, person)
        obj = self.Person.objects(name__endswith='rossuM').first()
        self.assertEqual(obj, None)

        # Test iendswith
        obj = self.Person.objects(name__iendswith='rossuM').first()
        self.assertEqual(obj, person)

        # Test exact
        obj = self.Person.objects(name__exact='Guido van Rossum').first()
        self.assertEqual(obj, person)
        obj = self.Person.objects(name__exact='Guido van rossum').first()
        self.assertEqual(obj, None)
        obj = self.Person.objects(name__exact='Guido van Rossu').first()
        self.assertEqual(obj, None)

        # Test iexact
        obj = self.Person.objects(name__iexact='gUIDO VAN rOSSUM').first()
        self.assertEqual(obj, person)
        obj = self.Person.objects(name__iexact='gUIDO VAN rOSSU').first()
        self.assertEqual(obj, None)

        # Test unsafe expressions
        person = self.Person(name='Guido van Rossum [.\'Geek\']')
        person.save()

        obj = self.Person.objects(name__icontains='[.\'Geek').first()
        self.assertEqual(obj, person)

    def test_not(self):
        """Ensure that the __not operator works as expected.
        """
        alice = self.Person(name='Alice', age=25)
        alice.save()

        obj = self.Person.objects(name__iexact='alice').first()
        self.assertEqual(obj, alice)

        obj = self.Person.objects(name__not__iexact='alice').first()
        self.assertEqual(obj, None)

    def test_filter_chaining(self):
        """Ensure filters can be chained together.
        """
        class Blog(Document):
            id = StringField(unique=True, primary_key=True)

        class BlogPost(Document):
            blog = ReferenceField(Blog)
            title = StringField()
            is_published = BooleanField()
            published_date = DateTimeField()

            @queryset_manager
            def published(doc_cls, queryset):
                return queryset(is_published=True)

        Blog.drop_collection()
        BlogPost.drop_collection()

        blog_1 = Blog(id="1")
        blog_2 = Blog(id="2")
        blog_3 = Blog(id="3")

        blog_1.save()
        blog_2.save()
        blog_3.save()

        blog_post_1 = BlogPost(blog=blog_1, title="Blog Post #1",
                               is_published=True,
                               published_date=datetime(2010, 1, 5, 0, 0, 0))
        blog_post_2 = BlogPost(blog=blog_2, title="Blog Post #2",
                               is_published=True,
                               published_date=datetime(2010, 1, 6, 0, 0, 0))
        blog_post_3 = BlogPost(blog=blog_3, title="Blog Post #3",
                               is_published=True,
                               published_date=datetime(2010, 1, 7, 0, 0, 0))

        blog_post_1.save()
        blog_post_2.save()
        blog_post_3.save()

        # find all published blog posts before 2010-01-07
        published_posts = BlogPost.published()
        published_posts = published_posts.filter(
            published_date__lt=datetime(2010, 1, 7, 0, 0, 0))
        self.assertEqual(published_posts.count(), 2)

        blog_posts = BlogPost.objects
        blog_posts = blog_posts.filter(blog__in=[blog_1, blog_2])
        blog_posts = blog_posts.filter(blog=blog_3)
        self.assertEqual(blog_posts.count(), 0)

        BlogPost.drop_collection()
        Blog.drop_collection()

    def assertSequence(self, qs, expected):
        qs = list(qs)
        expected = list(expected)
        self.assertEqual(len(qs), len(expected))
        for i in xrange(len(qs)):
            self.assertEqual(qs[i], expected[i])

    def test_ordering(self):
        """Ensure default ordering is applied and can be overridden.
        """
        class BlogPost(Document):
            title = StringField()
            published_date = DateTimeField()

            meta = {
                'ordering': ['-published_date']
            }

        BlogPost.drop_collection()

        blog_post_1 = BlogPost(title="Blog Post #1",
                               published_date=datetime(2010, 1, 5, 0, 0, 0))
        blog_post_2 = BlogPost(title="Blog Post #2",
                               published_date=datetime(2010, 1, 6, 0, 0, 0))
        blog_post_3 = BlogPost(title="Blog Post #3",
                               published_date=datetime(2010, 1, 7, 0, 0, 0))

        blog_post_1.save()
        blog_post_2.save()
        blog_post_3.save()

        # get the "first" BlogPost using default ordering
        # from BlogPost.meta.ordering
        expected = [blog_post_3, blog_post_2, blog_post_1]
        self.assertSequence(BlogPost.objects.all(), expected)

        # override default ordering, order BlogPosts by "published_date"
        qs = BlogPost.objects.order_by("+published_date")
        expected = [blog_post_1, blog_post_2, blog_post_3]
        self.assertSequence(qs, expected)

    def test_find_embedded(self):
        """Ensure that an embedded document is properly returned from a query.
        """
        class User(EmbeddedDocument):
            name = StringField()

        class BlogPost(Document):
            content = StringField()
            author = EmbeddedDocumentField(User)

        BlogPost.drop_collection()

        post = BlogPost(content='Had a good coffee today...')
        post.author = User(name='Test User')
        post.save()

        result = BlogPost.objects.first()
        self.assertTrue(isinstance(result.author, User))
        self.assertEqual(result.author.name, 'Test User')

        BlogPost.drop_collection()

    def test_find_dict_item(self):
        """Ensure that DictField items may be found.
        """
        class BlogPost(Document):
            info = DictField()

        BlogPost.drop_collection()

        post = BlogPost(info={'title': 'test'})
        post.save()

        post_obj = BlogPost.objects(info__title='test').first()
        self.assertEqual(post_obj.id, post.id)

        BlogPost.drop_collection()


    def test_exec_js_query(self):
        """Ensure that queries are properly formed for use in exec_js.
        """
        class BlogPost(Document):
            hits = IntField()
            published = BooleanField()

        BlogPost.drop_collection()

        post1 = BlogPost(hits=1, published=False)
        post1.save()

        post2 = BlogPost(hits=1, published=True)
        post2.save()

        post3 = BlogPost(hits=1, published=True)
        post3.save()

        js_func = """
            function(hitsField) {
                var count = 0;
                db[collection].find(query).forEach(function(doc) {
                    count += doc[hitsField];
                });
                return count;
            }
        """

        # Ensure that normal queries work
        c = BlogPost.objects(published=True).exec_js(js_func, 'hits')
        self.assertEqual(c, 2)

        c = BlogPost.objects(published=False).exec_js(js_func, 'hits')
        self.assertEqual(c, 1)

        BlogPost.drop_collection()

    def test_exec_js_field_sub(self):
        """Ensure that field substitutions occur properly in exec_js functions.
        """
        class Comment(EmbeddedDocument):
            content = StringField(db_field='body')

        class BlogPost(Document):
            name = StringField(db_field='doc-name')
            comments = ListField(EmbeddedDocumentField(Comment),
                                 db_field='cmnts')

        BlogPost.drop_collection()

        comments1 = [Comment(content='cool'), Comment(content='yay')]
        post1 = BlogPost(name='post1', comments=comments1)
        post1.save()

        comments2 = [Comment(content='nice stuff')]
        post2 = BlogPost(name='post2', comments=comments2)
        post2.save()

        code = """
        function getComments() {
            var comments = [];
            db[collection].find(query).forEach(function(doc) {
                var docComments = doc[~comments];
                for (var i = 0; i < docComments.length; i++) {
                    comments.push({
                        'document': doc[~name],
                        'comment': doc[~comments][i][~comments.content]
                    });
                }
            });
            return comments;
        }
        """

        sub_code = BlogPost.objects._sub_js_fields(code)
        code_chunks = ['doc["cmnts"];', 'doc["doc-name"],',
                       'doc["cmnts"][i]["body"]']
        for chunk in code_chunks:
            self.assertTrue(chunk in sub_code)

        results = BlogPost.objects.exec_js(code)
        expected_results = [
            {u'comment': u'cool', u'document': u'post1'},
            {u'comment': u'yay', u'document': u'post1'},
            {u'comment': u'nice stuff', u'document': u'post2'},
        ]
        self.assertEqual(results, expected_results)

        # Test template style
        code = "{{~comments.content}}"
        sub_code = BlogPost.objects._sub_js_fields(code)
        self.assertEqual("cmnts.body", sub_code)

        BlogPost.drop_collection()

    def test_delete(self):
        """Ensure that documents are properly deleted from the database.
        """
        self.Person(name="User A", age=20).save()
        self.Person(name="User B", age=30).save()
        self.Person(name="User C", age=40).save()

        self.assertEqual(self.Person.objects.count(), 3)

        self.Person.objects(age__lt=30).delete()
        self.assertEqual(self.Person.objects.count(), 2)

        self.Person.objects.delete()
        self.assertEqual(self.Person.objects.count(), 0)

    def test_reverse_delete_rule_cascade(self):
        """Ensure cascading deletion of referring documents from the database.
        """
        class BlogPost(Document):
            content = StringField()
            author = ReferenceField(self.Person, reverse_delete_rule=CASCADE)
        BlogPost.drop_collection()

        me = self.Person(name='Test User')
        me.save()
        someoneelse = self.Person(name='Some-one Else')
        someoneelse.save()

        BlogPost(content='Watching TV', author=me).save()
        BlogPost(content='Chilling out', author=me).save()
        BlogPost(content='Pro Testing', author=someoneelse).save()

        self.assertEqual(3, BlogPost.objects.count())
        self.Person.objects(name='Test User').delete()
        self.assertEqual(1, BlogPost.objects.count())

    def test_reverse_delete_rule_cascade_self_referencing(self):
        """Ensure self-referencing CASCADE deletes do not result in infinite
        loop
        """
        class Category(Document):
            name = StringField()
            parent = ReferenceField('self', reverse_delete_rule=CASCADE)

        Category.drop_collection()

        num_children = 3
        base = Category(name='Root')
        base.save()

        # Create a simple parent-child tree
        for i in range(num_children):
            child_name = 'Child-%i' % i
            child = Category(name=child_name, parent=base)
            child.save()

            for i in range(num_children):
                child_child_name = 'Child-Child-%i' % i
                child_child = Category(name=child_child_name, parent=child)
                child_child.save()

        tree_size = 1 + num_children + (num_children * num_children)
        self.assertEqual(tree_size, Category.objects.count())
        self.assertEqual(num_children, Category.objects(parent=base).count())

        # The delete should effectively wipe out the Category collection
        # without resulting in infinite parent-child cascade recursion
        base.delete()
        self.assertEqual(0, Category.objects.count())

    def test_reverse_delete_rule_nullify(self):
        """Ensure nullification of references to deleted documents.
        """
        class Category(Document):
            name = StringField()

        class BlogPost(Document):
            content = StringField()
            category = ReferenceField(Category, reverse_delete_rule=NULLIFY)

        BlogPost.drop_collection()
        Category.drop_collection()

        lameness = Category(name='Lameness')
        lameness.save()

        post = BlogPost(content='Watching TV', category=lameness)
        post.save()

        self.assertEqual(1, BlogPost.objects.count())
        self.assertEqual('Lameness', BlogPost.objects.first().category.name)
        Category.objects.delete()
        self.assertEqual(1, BlogPost.objects.count())
        self.assertEqual(None, BlogPost.objects.first().category)

    def test_reverse_delete_rule_deny(self):
        """Ensure deletion gets denied on documents that still have references
        to them.
        """
        class BlogPost(Document):
            content = StringField()
            author = ReferenceField(self.Person, reverse_delete_rule=DENY)

        BlogPost.drop_collection()
        self.Person.drop_collection()

        me = self.Person(name='Test User')
        me.save()

        post = BlogPost(content='Watching TV', author=me)
        post.save()

        self.assertRaises(OperationError, self.Person.objects.delete)

    def test_reverse_delete_rule_pull(self):
        """Ensure pulling of references to deleted documents.
        """
        class BlogPost(Document):
            content = StringField()
            authors = ListField(ReferenceField(self.Person,
                                reverse_delete_rule=PULL))

        BlogPost.drop_collection()
        self.Person.drop_collection()

        me = self.Person(name='Test User')
        me.save()

        someoneelse = self.Person(name='Some-one Else')
        someoneelse.save()

        post = BlogPost(content='Watching TV', authors=[me, someoneelse])
        post.save()

        another = BlogPost(content='Chilling Out', authors=[someoneelse])
        another.save()

        someoneelse.delete()
        post.reload()
        another.reload()

        self.assertEqual(post.authors, [me])
        self.assertEqual(another.authors, [])

    def test_delete_with_limits(self):

        class Log(Document):
            pass

        Log.drop_collection()

        for i in xrange(10):
            Log().save()

        Log.objects()[3:5].delete()
        self.assertEqual(8, Log.objects.count())

    def test_delete_with_limit_handles_delete_rules(self):
        """Ensure cascading deletion of referring documents from the database.
        """
        class BlogPost(Document):
            content = StringField()
            author = ReferenceField(self.Person, reverse_delete_rule=CASCADE)
        BlogPost.drop_collection()

        me = self.Person(name='Test User')
        me.save()
        someoneelse = self.Person(name='Some-one Else')
        someoneelse.save()

        BlogPost(content='Watching TV', author=me).save()
        BlogPost(content='Chilling out', author=me).save()
        BlogPost(content='Pro Testing', author=someoneelse).save()

        self.assertEqual(3, BlogPost.objects.count())
        self.Person.objects()[:1].delete()
        self.assertEqual(1, BlogPost.objects.count())


    def test_reference_field_find(self):
        """Ensure cascading deletion of referring documents from the database.
        """
        class BlogPost(Document):
            content = StringField()
            author = ReferenceField(self.Person)

        BlogPost.drop_collection()
        self.Person.drop_collection()

        me = self.Person(name='Test User').save()
        BlogPost(content="test 123", author=me).save()

        self.assertEqual(1, BlogPost.objects(author=me).count())
        self.assertEqual(1, BlogPost.objects(author=me.pk).count())
        self.assertEqual(1, BlogPost.objects(author="%s" % me.pk).count())

        self.assertEqual(1, BlogPost.objects(author__in=[me]).count())
        self.assertEqual(1, BlogPost.objects(author__in=[me.pk]).count())
        self.assertEqual(1, BlogPost.objects(author__in=["%s" % me.pk]).count())

    def test_reference_field_find_dbref(self):
        """Ensure cascading deletion of referring documents from the database.
        """
        class BlogPost(Document):
            content = StringField()
            author = ReferenceField(self.Person, dbref=True)

        BlogPost.drop_collection()
        self.Person.drop_collection()

        me = self.Person(name='Test User').save()
        BlogPost(content="test 123", author=me).save()

        self.assertEqual(1, BlogPost.objects(author=me).count())
        self.assertEqual(1, BlogPost.objects(author=me.pk).count())
        self.assertEqual(1, BlogPost.objects(author="%s" % me.pk).count())

        self.assertEqual(1, BlogPost.objects(author__in=[me]).count())
        self.assertEqual(1, BlogPost.objects(author__in=[me.pk]).count())
        self.assertEqual(1, BlogPost.objects(author__in=["%s" % me.pk]).count())

    def test_update(self):
        """Ensure that atomic updates work properly.
        """
        class BlogPost(Document):
            title = StringField()
            hits = IntField()
            tags = ListField(StringField())

        BlogPost.drop_collection()

        post = BlogPost(name="Test Post", hits=5, tags=['test'])
        post.save()

        BlogPost.objects.update(set__hits=10)
        post.reload()
        self.assertEqual(post.hits, 10)

        BlogPost.objects.update_one(inc__hits=1)
        post.reload()
        self.assertEqual(post.hits, 11)

        BlogPost.objects.update_one(dec__hits=1)
        post.reload()
        self.assertEqual(post.hits, 10)

        BlogPost.objects.update(push__tags='mongo')
        post.reload()
        self.assertTrue('mongo' in post.tags)

        BlogPost.objects.update_one(push_all__tags=['db', 'nosql'])
        post.reload()
        self.assertTrue('db' in post.tags and 'nosql' in post.tags)

        tags = post.tags[:-1]
        BlogPost.objects.update(pop__tags=1)
        post.reload()
        self.assertEqual(post.tags, tags)

        BlogPost.objects.update_one(add_to_set__tags='unique')
        BlogPost.objects.update_one(add_to_set__tags='unique')
        post.reload()
        self.assertEqual(post.tags.count('unique'), 1)

        self.assertNotEqual(post.hits, None)
        BlogPost.objects.update_one(unset__hits=1)
        post.reload()
        self.assertEqual(post.hits, None)

        BlogPost.drop_collection()

    def test_update_push_and_pull_add_to_set(self):
        """Ensure that the 'pull' update operation works correctly.
        """
        class BlogPost(Document):
            slug = StringField()
            tags = ListField(StringField())

        BlogPost.drop_collection()

        post = BlogPost(slug="test")
        post.save()

        BlogPost.objects.filter(id=post.id).update(push__tags="code")
        post.reload()
        self.assertEqual(post.tags, ["code"])

        BlogPost.objects.filter(id=post.id).update(push_all__tags=["mongodb", "code"])
        post.reload()
        self.assertEqual(post.tags, ["code", "mongodb", "code"])

        BlogPost.objects(slug="test").update(pull__tags="code")
        post.reload()
        self.assertEqual(post.tags, ["mongodb"])


        BlogPost.objects(slug="test").update(pull_all__tags=["mongodb", "code"])
        post.reload()
        self.assertEqual(post.tags, [])

        BlogPost.objects(slug="test").update(__raw__={"$addToSet": {"tags": {"$each": ["code", "mongodb", "code"]}}})
        post.reload()
        self.assertEqual(post.tags, ["code", "mongodb"])

    def test_add_to_set_each(self):
        class Item(Document):
            name = StringField(required=True)
            description = StringField(max_length=50)
            parents = ListField(ReferenceField('self'))

        Item.drop_collection()

        item = Item(name='test item').save()
        parent_1 = Item(name='parent 1').save()
        parent_2 = Item(name='parent 2').save()

        item.update(add_to_set__parents=[parent_1, parent_2, parent_1])
        item.reload()

        self.assertEqual([parent_1, parent_2], item.parents)

    def test_pull_nested(self):

        class Collaborator(EmbeddedDocument):
            user = StringField()

            def __unicode__(self):
                return '%s' % self.user

        class Site(Document):
            name = StringField(max_length=75, unique=True, required=True)
            collaborators = ListField(EmbeddedDocumentField(Collaborator))


        Site.drop_collection()

        c = Collaborator(user='Esteban')
        s = Site(name="test", collaborators=[c]).save()

        Site.objects(id=s.id).update_one(pull__collaborators__user='Esteban')
        self.assertEqual(Site.objects.first().collaborators, [])

        def pull_all():
            Site.objects(id=s.id).update_one(pull_all__collaborators__user=['Ross'])

        self.assertRaises(InvalidQueryError, pull_all)

    def test_pull_from_nested_embedded(self):

        class User(EmbeddedDocument):
            name = StringField()

            def __unicode__(self):
                return '%s' % self.name

        class Collaborator(EmbeddedDocument):
            helpful = ListField(EmbeddedDocumentField(User))
            unhelpful = ListField(EmbeddedDocumentField(User))

        class Site(Document):
            name = StringField(max_length=75, unique=True, required=True)
            collaborators = EmbeddedDocumentField(Collaborator)


        Site.drop_collection()

        c = User(name='Esteban')
        f = User(name='Frank')
        s = Site(name="test", collaborators=Collaborator(helpful=[c], unhelpful=[f])).save()

        Site.objects(id=s.id).update_one(pull__collaborators__helpful=c)
        self.assertEqual(Site.objects.first().collaborators['helpful'], [])

        Site.objects(id=s.id).update_one(pull__collaborators__unhelpful={'name': 'Frank'})
        self.assertEqual(Site.objects.first().collaborators['unhelpful'], [])

        def pull_all():
            Site.objects(id=s.id).update_one(pull_all__collaborators__helpful__name=['Ross'])

        self.assertRaises(InvalidQueryError, pull_all)

    def test_pull_from_nested_mapfield(self):

        class Collaborator(EmbeddedDocument):
            user = StringField()

            def __unicode__(self):
                return '%s' % self.user

        class Site(Document):
            name = StringField(max_length=75, unique=True, required=True)
            collaborators = MapField(ListField(EmbeddedDocumentField(Collaborator)))


        Site.drop_collection()

        c = Collaborator(user='Esteban')
        f = Collaborator(user='Frank')
        s = Site(name="test", collaborators={'helpful':[c],'unhelpful':[f]})
        s.save()

        Site.objects(id=s.id).update_one(pull__collaborators__helpful__user='Esteban')
        self.assertEqual(Site.objects.first().collaborators['helpful'], [])

        Site.objects(id=s.id).update_one(pull__collaborators__unhelpful={'user':'Frank'})
        self.assertEqual(Site.objects.first().collaborators['unhelpful'], [])

        def pull_all():
            Site.objects(id=s.id).update_one(pull_all__collaborators__helpful__user=['Ross'])

        self.assertRaises(InvalidQueryError, pull_all)

    def test_update_one_pop_generic_reference(self):

        class BlogTag(Document):
            name = StringField(required=True)

        class BlogPost(Document):
            slug = StringField()
            tags = ListField(ReferenceField(BlogTag), required=True)

        BlogPost.drop_collection()
        BlogTag.drop_collection()

        tag_1 = BlogTag(name='code')
        tag_1.save()
        tag_2 = BlogTag(name='mongodb')
        tag_2.save()

        post = BlogPost(slug="test", tags=[tag_1])
        post.save()

        post = BlogPost(slug="test-2", tags=[tag_1, tag_2])
        post.save()
        self.assertEqual(len(post.tags), 2)

        BlogPost.objects(slug="test-2").update_one(pop__tags=-1)

        post.reload()
        self.assertEqual(len(post.tags), 1)

        BlogPost.drop_collection()
        BlogTag.drop_collection()

    def test_editting_embedded_objects(self):

        class BlogTag(EmbeddedDocument):
            name = StringField(required=True)

        class BlogPost(Document):
            slug = StringField()
            tags = ListField(EmbeddedDocumentField(BlogTag), required=True)

        BlogPost.drop_collection()

        tag_1 = BlogTag(name='code')
        tag_2 = BlogTag(name='mongodb')

        post = BlogPost(slug="test", tags=[tag_1])
        post.save()

        post = BlogPost(slug="test-2", tags=[tag_1, tag_2])
        post.save()
        self.assertEqual(len(post.tags), 2)

        BlogPost.objects(slug="test-2").update_one(set__tags__0__name="python")
        post.reload()
        self.assertEqual(post.tags[0].name, 'python')

        BlogPost.objects(slug="test-2").update_one(pop__tags=-1)
        post.reload()
        self.assertEqual(len(post.tags), 1)

        BlogPost.drop_collection()

    def test_set_list_embedded_documents(self):

        class Author(EmbeddedDocument):
            name = StringField()

        class Message(Document):
            title = StringField()
            authors = ListField(EmbeddedDocumentField('Author'))

        Message.drop_collection()

        message = Message(title="hello", authors=[Author(name="Harry")])
        message.save()

        Message.objects(authors__name="Harry").update_one(
            set__authors__S=Author(name="Ross"))

        message = message.reload()
        self.assertEqual(message.authors[0].name, "Ross")

        Message.objects(authors__name="Ross").update_one(
            set__authors=[Author(name="Harry"),
                          Author(name="Ross"),
                          Author(name="Adam")])

        message = message.reload()
        self.assertEqual(message.authors[0].name, "Harry")
        self.assertEqual(message.authors[1].name, "Ross")
        self.assertEqual(message.authors[2].name, "Adam")

    def test_reload_embedded_docs_instance(self):

        class SubDoc(EmbeddedDocument):
            val = IntField()

        class Doc(Document):
            embedded = EmbeddedDocumentField(SubDoc)

        doc = Doc(embedded=SubDoc(val=0)).save()
        doc.reload()

        self.assertEqual(doc.pk, doc.embedded._instance.pk)

    def test_reload_list_embedded_docs_instance(self):

        class SubDoc(EmbeddedDocument):
            val = IntField()

        class Doc(Document):
            embedded = ListField(EmbeddedDocumentField(SubDoc))

        doc = Doc(embedded=[SubDoc(val=0)]).save()
        doc.reload()

        self.assertEqual(doc.pk, doc.embedded[0]._instance.pk)

    def test_order_by(self):
        """Ensure that QuerySets may be ordered.
        """
        self.Person(name="User B", age=40).save()
        self.Person(name="User A", age=20).save()
        self.Person(name="User C", age=30).save()

        names = [p.name for p in self.Person.objects.order_by('-age')]
        self.assertEqual(names, ['User B', 'User C', 'User A'])

        names = [p.name for p in self.Person.objects.order_by('+age')]
        self.assertEqual(names, ['User A', 'User C', 'User B'])

        names = [p.name for p in self.Person.objects.order_by('age')]
        self.assertEqual(names, ['User A', 'User C', 'User B'])

        ages = [p.age for p in self.Person.objects.order_by('-name')]
        self.assertEqual(ages, [30, 40, 20])

    def test_order_by_optional(self):
        class BlogPost(Document):
            title = StringField()
            published_date = DateTimeField(required=False)

        BlogPost.drop_collection()

        blog_post_3 = BlogPost(title="Blog Post #3",
                               published_date=datetime(2010, 1, 6, 0, 0, 0))
        blog_post_2 = BlogPost(title="Blog Post #2",
                               published_date=datetime(2010, 1, 5, 0, 0, 0))
        blog_post_4 = BlogPost(title="Blog Post #4",
                               published_date=datetime(2010, 1, 7, 0, 0, 0))
        blog_post_1 = BlogPost(title="Blog Post #1", published_date=None)

        blog_post_3.save()
        blog_post_1.save()
        blog_post_4.save()
        blog_post_2.save()

        expected = [blog_post_1, blog_post_2, blog_post_3, blog_post_4]
        self.assertSequence(BlogPost.objects.order_by('published_date'),
                            expected)
        self.assertSequence(BlogPost.objects.order_by('+published_date'),
                            expected)

        expected.reverse()
        self.assertSequence(BlogPost.objects.order_by('-published_date'),
                            expected)

    def test_order_by_list(self):
        class BlogPost(Document):
            title = StringField()
            published_date = DateTimeField(required=False)

        BlogPost.drop_collection()

        blog_post_1 = BlogPost(title="A",
                               published_date=datetime(2010, 1, 6, 0, 0, 0))
        blog_post_2 = BlogPost(title="B",
                               published_date=datetime(2010, 1, 6, 0, 0, 0))
        blog_post_3 = BlogPost(title="C",
                               published_date=datetime(2010, 1, 7, 0, 0, 0))

        blog_post_2.save()
        blog_post_3.save()
        blog_post_1.save()

        qs = BlogPost.objects.order_by('published_date', 'title')
        expected = [blog_post_1, blog_post_2, blog_post_3]
        self.assertSequence(qs, expected)

        qs = BlogPost.objects.order_by('-published_date', '-title')
        expected.reverse()
        self.assertSequence(qs, expected)

    def test_order_by_chaining(self):
        """Ensure that an order_by query chains properly and allows .only()
        """
        self.Person(name="User B", age=40).save()
        self.Person(name="User A", age=20).save()
        self.Person(name="User C", age=30).save()

        only_age = self.Person.objects.order_by('-age').only('age')

        names = [p.name for p in only_age]
        ages = [p.age for p in only_age]

        # The .only('age') clause should mean that all names are None
        self.assertEqual(names, [None, None, None])
        self.assertEqual(ages, [40, 30, 20])

        qs = self.Person.objects.all().order_by('-age')
        qs = qs.limit(10)
        ages = [p.age for p in qs]
        self.assertEqual(ages, [40, 30, 20])

        qs = self.Person.objects.all().limit(10)
        qs = qs.order_by('-age')

        ages = [p.age for p in qs]
        self.assertEqual(ages, [40, 30, 20])

        qs = self.Person.objects.all().skip(0)
        qs = qs.order_by('-age')
        ages = [p.age for p in qs]
        self.assertEqual(ages, [40, 30, 20])

    def test_confirm_order_by_reference_wont_work(self):
        """Ordering by reference is not possible.  Use map / reduce.. or
        denormalise"""

        class Author(Document):
            author = ReferenceField(self.Person)

        Author.drop_collection()

        person_a = self.Person(name="User A", age=20)
        person_a.save()
        person_b = self.Person(name="User B", age=40)
        person_b.save()
        person_c = self.Person(name="User C", age=30)
        person_c.save()

        Author(author=person_a).save()
        Author(author=person_b).save()
        Author(author=person_c).save()

        names = [a.author.name for a in Author.objects.order_by('-author__age')]
        self.assertEqual(names, ['User A', 'User B', 'User C'])

    def test_map_reduce(self):
        """Ensure map/reduce is both mapping and reducing.
        """
        class BlogPost(Document):
            title = StringField()
            tags = ListField(StringField(), db_field='post-tag-list')

        BlogPost.drop_collection()

        BlogPost(title="Post #1", tags=['music', 'film', 'print']).save()
        BlogPost(title="Post #2", tags=['music', 'film']).save()
        BlogPost(title="Post #3", tags=['film', 'photography']).save()

        map_f = """
            function() {
                this[~tags].forEach(function(tag) {
                    emit(tag, 1);
                });
            }
        """

        reduce_f = """
            function(key, values) {
                var total = 0;
                for(var i=0; i<values.length; i++) {
                    total += values[i];
                }
                return total;
            }
        """

        # run a map/reduce operation spanning all posts
        results = BlogPost.objects.map_reduce(map_f, reduce_f, "myresults")
        results = list(results)
        self.assertEqual(len(results), 4)

        music = list(filter(lambda r: r.key == "music", results))[0]
        self.assertEqual(music.value, 2)

        film = list(filter(lambda r: r.key == "film", results))[0]
        self.assertEqual(film.value, 3)

        BlogPost.drop_collection()

    def test_map_reduce_with_custom_object_ids(self):
        """Ensure that QuerySet.map_reduce works properly with custom
        primary keys.
        """

        class BlogPost(Document):
            title = StringField(primary_key=True)
            tags = ListField(StringField())

        post1 = BlogPost(title="Post #1", tags=["mongodb", "mongoengine"])
        post2 = BlogPost(title="Post #2", tags=["django", "mongodb"])
        post3 = BlogPost(title="Post #3", tags=["hitchcock films"])

        post1.save()
        post2.save()
        post3.save()

        self.assertEqual(BlogPost._fields['title'].db_field, '_id')
        self.assertEqual(BlogPost._meta['id_field'], 'title')

        map_f = """
            function() {
                emit(this._id, 1);
            }
        """

        # reduce to a list of tag ids and counts
        reduce_f = """
            function(key, values) {
                var total = 0;
                for(var i=0; i<values.length; i++) {
                    total += values[i];
                }
                return total;
            }
        """

        results = BlogPost.objects.map_reduce(map_f, reduce_f, "myresults")
        results = list(results)

        self.assertEqual(results[0].object, post1)
        self.assertEqual(results[1].object, post2)
        self.assertEqual(results[2].object, post3)

        BlogPost.drop_collection()

    def test_map_reduce_finalize(self):
        """Ensure that map, reduce, and finalize run and introduce "scope"
        by simulating "hotness" ranking with Reddit algorithm.
        """
        from time import mktime

        class Link(Document):
            title = StringField(db_field='bpTitle')
            up_votes = IntField()
            down_votes = IntField()
            submitted = DateTimeField(db_field='sTime')

        Link.drop_collection()

        now = datetime.utcnow()

        # Note: Test data taken from a custom Reddit homepage on
        # Fri, 12 Feb 2010 14:36:00 -0600. Link ordering should
        # reflect order of insertion below, but is not influenced
        # by insertion order.
        Link(title = "Google Buzz auto-followed a woman's abusive ex ...",
             up_votes = 1079,
             down_votes = 553,
             submitted = now-timedelta(hours=4)).save()
        Link(title = "We did it! Barbie is a computer engineer.",
             up_votes = 481,
             down_votes = 124,
             submitted = now-timedelta(hours=2)).save()
        Link(title = "This Is A Mosquito Getting Killed By A Laser",
             up_votes = 1446,
             down_votes = 530,
             submitted=now-timedelta(hours=13)).save()
        Link(title = "Arabic flashcards land physics student in jail.",
             up_votes = 215,
             down_votes = 105,
             submitted = now-timedelta(hours=6)).save()
        Link(title = "The Burger Lab: Presenting, the Flood Burger",
             up_votes = 48,
             down_votes = 17,
             submitted = now-timedelta(hours=5)).save()
        Link(title="How to see polarization with the naked eye",
             up_votes = 74,
             down_votes = 13,
             submitted = now-timedelta(hours=10)).save()

        map_f = """
            function() {
                emit(this[~id], {up_delta: this[~up_votes] - this[~down_votes],
                                sub_date: this[~submitted].getTime() / 1000})
            }
        """

        reduce_f = """
            function(key, values) {
                data = values[0];

                x = data.up_delta;

                // calculate time diff between reddit epoch and submission
                sec_since_epoch = data.sub_date - reddit_epoch;

                // calculate 'Y'
                if(x > 0) {
                    y = 1;
                } else if (x = 0) {
                    y = 0;
                } else {
                    y = -1;
                }

                // calculate 'Z', the maximal value
                if(Math.abs(x) >= 1) {
                    z = Math.abs(x);
                } else {
                    z = 1;
                }

                return {x: x, y: y, z: z, t_s: sec_since_epoch};
            }
        """

        finalize_f = """
            function(key, value) {
                // f(sec_since_epoch,y,z) =
                //                    log10(z) + ((y*sec_since_epoch) / 45000)
                z_10 = Math.log(value.z) / Math.log(10);
                weight = z_10 + ((value.y * value.t_s) / 45000);
                return weight;
            }
        """

        # provide the reddit epoch (used for ranking) as a variable available
        # to all phases of the map/reduce operation: map, reduce, and finalize.
        reddit_epoch = mktime(datetime(2005, 12, 8, 7, 46, 43).timetuple())
        scope = {'reddit_epoch': reddit_epoch}

        # run a map/reduce operation across all links. ordering is set
        # to "-value", which orders the "weight" value returned from
        # "finalize_f" in descending order.
        results = Link.objects.order_by("-value")
        results = results.map_reduce(map_f,
                                     reduce_f,
                                     "myresults",
                                     finalize_f=finalize_f,
                                     scope=scope)
        results = list(results)

        # assert troublesome Buzz article is ranked 1st
        self.assertTrue(results[0].object.title.startswith("Google Buzz"))

        # assert laser vision is ranked last
        self.assertTrue(results[-1].object.title.startswith("How to see"))

        Link.drop_collection()

    def test_item_frequencies(self):
        """Ensure that item frequencies are properly generated from lists.
        """
        class BlogPost(Document):
            hits = IntField()
            tags = ListField(StringField(), db_field='blogTags')

        BlogPost.drop_collection()

        BlogPost(hits=1, tags=['music', 'film', 'actors', 'watch']).save()
        BlogPost(hits=2, tags=['music', 'watch']).save()
        BlogPost(hits=2, tags=['music', 'actors']).save()

        def test_assertions(f):
            f = dict((key, int(val)) for key, val in f.items())
            self.assertEqual(set(['music', 'film', 'actors', 'watch']), set(f.keys()))
            self.assertEqual(f['music'], 3)
            self.assertEqual(f['actors'], 2)
            self.assertEqual(f['watch'], 2)
            self.assertEqual(f['film'], 1)

        exec_js = BlogPost.objects.item_frequencies('tags')
        map_reduce = BlogPost.objects.item_frequencies('tags', map_reduce=True)
        test_assertions(exec_js)
        test_assertions(map_reduce)

        # Ensure query is taken into account
        def test_assertions(f):
            f = dict((key, int(val)) for key, val in f.items())
            self.assertEqual(set(['music', 'actors', 'watch']), set(f.keys()))
            self.assertEqual(f['music'], 2)
            self.assertEqual(f['actors'], 1)
            self.assertEqual(f['watch'], 1)

        exec_js = BlogPost.objects(hits__gt=1).item_frequencies('tags')
        map_reduce = BlogPost.objects(hits__gt=1).item_frequencies('tags', map_reduce=True)
        test_assertions(exec_js)
        test_assertions(map_reduce)

        # Check that normalization works
        def test_assertions(f):
            self.assertAlmostEqual(f['music'], 3.0/8.0)
            self.assertAlmostEqual(f['actors'], 2.0/8.0)
            self.assertAlmostEqual(f['watch'], 2.0/8.0)
            self.assertAlmostEqual(f['film'], 1.0/8.0)

        exec_js = BlogPost.objects.item_frequencies('tags', normalize=True)
        map_reduce = BlogPost.objects.item_frequencies('tags', normalize=True, map_reduce=True)
        test_assertions(exec_js)
        test_assertions(map_reduce)

        # Check item_frequencies works for non-list fields
        def test_assertions(f):
            self.assertEqual(set([1, 2]), set(f.keys()))
            self.assertEqual(f[1], 1)
            self.assertEqual(f[2], 2)

        exec_js = BlogPost.objects.item_frequencies('hits')
        map_reduce = BlogPost.objects.item_frequencies('hits', map_reduce=True)
        test_assertions(exec_js)
        test_assertions(map_reduce)

        BlogPost.drop_collection()

    def test_item_frequencies_on_embedded(self):
        """Ensure that item frequencies are properly generated from lists.
        """

        class Phone(EmbeddedDocument):
            number = StringField()

        class Person(Document):
            name = StringField()
            phone = EmbeddedDocumentField(Phone)

        Person.drop_collection()

        doc = Person(name="Guido")
        doc.phone = Phone(number='62-3331-1656')
        doc.save()

        doc = Person(name="Marr")
        doc.phone = Phone(number='62-3331-1656')
        doc.save()

        doc = Person(name="WP Junior")
        doc.phone = Phone(number='62-3332-1656')
        doc.save()


        def test_assertions(f):
            f = dict((key, int(val)) for key, val in f.items())
            self.assertEqual(set(['62-3331-1656', '62-3332-1656']), set(f.keys()))
            self.assertEqual(f['62-3331-1656'], 2)
            self.assertEqual(f['62-3332-1656'], 1)

        exec_js = Person.objects.item_frequencies('phone.number')
        map_reduce = Person.objects.item_frequencies('phone.number', map_reduce=True)
        test_assertions(exec_js)
        test_assertions(map_reduce)

        # Ensure query is taken into account
        def test_assertions(f):
            f = dict((key, int(val)) for key, val in f.items())
            self.assertEqual(set(['62-3331-1656']), set(f.keys()))
            self.assertEqual(f['62-3331-1656'], 2)

        exec_js = Person.objects(phone__number='62-3331-1656').item_frequencies('phone.number')
        map_reduce = Person.objects(phone__number='62-3331-1656').item_frequencies('phone.number', map_reduce=True)
        test_assertions(exec_js)
        test_assertions(map_reduce)

        # Check that normalization works
        def test_assertions(f):
            self.assertEqual(f['62-3331-1656'], 2.0/3.0)
            self.assertEqual(f['62-3332-1656'], 1.0/3.0)

        exec_js = Person.objects.item_frequencies('phone.number', normalize=True)
        map_reduce = Person.objects.item_frequencies('phone.number', normalize=True, map_reduce=True)
        test_assertions(exec_js)
        test_assertions(map_reduce)

    def test_item_frequencies_null_values(self):

        class Person(Document):
            name = StringField()
            city = StringField()

        Person.drop_collection()

        Person(name="Wilson Snr", city="CRB").save()
        Person(name="Wilson Jr").save()

        freq = Person.objects.item_frequencies('city')
        self.assertEqual(freq, {'CRB': 1.0, None: 1.0})
        freq = Person.objects.item_frequencies('city', normalize=True)
        self.assertEqual(freq, {'CRB': 0.5, None: 0.5})


        freq = Person.objects.item_frequencies('city', map_reduce=True)
        self.assertEqual(freq, {'CRB': 1.0, None: 1.0})
        freq = Person.objects.item_frequencies('city', normalize=True, map_reduce=True)
        self.assertEqual(freq, {'CRB': 0.5, None: 0.5})

    def test_item_frequencies_with_null_embedded(self):
        class Data(EmbeddedDocument):
            name = StringField()

        class Extra(EmbeddedDocument):
            tag = StringField()

        class Person(Document):
            data = EmbeddedDocumentField(Data, required=True)
            extra = EmbeddedDocumentField(Extra)

        Person.drop_collection()

        p = Person()
        p.data = Data(name="Wilson Jr")
        p.save()

        p = Person()
        p.data = Data(name="Wesley")
        p.extra = Extra(tag="friend")
        p.save()

        ot = Person.objects.item_frequencies('extra.tag', map_reduce=False)
        self.assertEqual(ot, {None: 1.0, u'friend': 1.0})

        ot = Person.objects.item_frequencies('extra.tag', map_reduce=True)
        self.assertEqual(ot, {None: 1.0, u'friend': 1.0})

    def test_item_frequencies_with_0_values(self):
        class Test(Document):
            val = IntField()

        Test.drop_collection()
        t = Test()
        t.val = 0
        t.save()

        ot = Test.objects.item_frequencies('val', map_reduce=True)
        self.assertEqual(ot, {0: 1})
        ot = Test.objects.item_frequencies('val', map_reduce=False)
        self.assertEqual(ot, {0: 1})

    def test_item_frequencies_with_False_values(self):
        class Test(Document):
            val = BooleanField()

        Test.drop_collection()
        t = Test()
        t.val = False
        t.save()

        ot = Test.objects.item_frequencies('val', map_reduce=True)
        self.assertEqual(ot, {False: 1})
        ot = Test.objects.item_frequencies('val', map_reduce=False)
        self.assertEqual(ot, {False: 1})

    def test_item_frequencies_normalize(self):
        class Test(Document):
            val = IntField()

        Test.drop_collection()

        for i in xrange(50):
            Test(val=1).save()

        for i in xrange(20):
            Test(val=2).save()

        freqs = Test.objects.item_frequencies('val', map_reduce=False, normalize=True)
        self.assertEqual(freqs, {1: 50.0/70, 2: 20.0/70})

        freqs = Test.objects.item_frequencies('val', map_reduce=True, normalize=True)
        self.assertEqual(freqs, {1: 50.0/70, 2: 20.0/70})

    def test_average(self):
        """Ensure that field can be averaged correctly.
        """
        self.Person(name='person', age=0).save()
        self.assertEqual(int(self.Person.objects.average('age')), 0)

        ages = [23, 54, 12, 94, 27]
        for i, age in enumerate(ages):
            self.Person(name='test%s' % i, age=age).save()

        avg = float(sum(ages)) / (len(ages) + 1) # take into account the 0
        self.assertAlmostEqual(int(self.Person.objects.average('age')), avg)

        self.Person(name='ageless person').save()
        self.assertEqual(int(self.Person.objects.average('age')), avg)

        # dot notation
        self.Person(name='person meta', person_meta=self.PersonMeta(weight=0)).save()
        self.assertAlmostEqual(int(self.Person.objects.average('person_meta.weight')), 0)

        for i, weight in enumerate(ages):
            self.Person(name='test meta%i', person_meta=self.PersonMeta(weight=weight)).save()

        self.assertAlmostEqual(int(self.Person.objects.average('person_meta.weight')), avg)

        self.Person(name='test meta none').save()
        self.assertEqual(int(self.Person.objects.average('person_meta.weight')), avg)


    def test_sum(self):
        """Ensure that field can be summed over correctly.
        """
        ages = [23, 54, 12, 94, 27]
        for i, age in enumerate(ages):
            self.Person(name='test%s' % i, age=age).save()

        self.assertEqual(int(self.Person.objects.sum('age')), sum(ages))

        self.Person(name='ageless person').save()
        self.assertEqual(int(self.Person.objects.sum('age')), sum(ages))

        for i, age in enumerate(ages):
            self.Person(name='test meta%s' % i, person_meta=self.PersonMeta(weight=age)).save()

        self.assertEqual(int(self.Person.objects.sum('person_meta.weight')), sum(ages))

        self.Person(name='weightless person').save()
        self.assertEqual(int(self.Person.objects.sum('age')), sum(ages))

    def test_embedded_average(self):
        class Pay(EmbeddedDocument):
            value = DecimalField()

        class Doc(Document):
            name = StringField()
            pay = EmbeddedDocumentField(
                Pay)

        Doc.drop_collection()

        Doc(name=u"Wilson Junior",
            pay=Pay(value=150)).save()

        Doc(name=u"Isabella Luanna",
            pay=Pay(value=530)).save()

        Doc(name=u"Tayza mariana",
            pay=Pay(value=165)).save()

        Doc(name=u"Eliana Costa",
            pay=Pay(value=115)).save()

        self.assertEqual(
            Doc.objects.average('pay.value'),
            240)

    def test_embedded_array_average(self):
        class Pay(EmbeddedDocument):
            values = ListField(DecimalField())

        class Doc(Document):
            name = StringField()
            pay = EmbeddedDocumentField(
                Pay)

        Doc.drop_collection()

        Doc(name=u"Wilson Junior",
            pay=Pay(values=[150, 100])).save()

        Doc(name=u"Isabella Luanna",
            pay=Pay(values=[530, 100])).save()

        Doc(name=u"Tayza mariana",
            pay=Pay(values=[165, 100])).save()

        Doc(name=u"Eliana Costa",
            pay=Pay(values=[115, 100])).save()

        self.assertEqual(
            Doc.objects.average('pay.values'),
            170)

    def test_array_average(self):
        class Doc(Document):
            values = ListField(DecimalField())

        Doc.drop_collection()

        Doc(values=[150, 100]).save()
        Doc(values=[530, 100]).save()
        Doc(values=[165, 100]).save()
        Doc(values=[115, 100]).save()

        self.assertEqual(
            Doc.objects.average('values'),
            170)

    def test_embedded_sum(self):
        class Pay(EmbeddedDocument):
            value = DecimalField()

        class Doc(Document):
            name = StringField()
            pay = EmbeddedDocumentField(
                Pay)

        Doc.drop_collection()

        Doc(name=u"Wilson Junior",
            pay=Pay(value=150)).save()

        Doc(name=u"Isabella Luanna",
            pay=Pay(value=530)).save()

        Doc(name=u"Tayza mariana",
            pay=Pay(value=165)).save()

        Doc(name=u"Eliana Costa",
            pay=Pay(value=115)).save()

        self.assertEqual(
            Doc.objects.sum('pay.value'),
            960)


    def test_embedded_array_sum(self):
        class Pay(EmbeddedDocument):
            values = ListField(DecimalField())

        class Doc(Document):
            name = StringField()
            pay = EmbeddedDocumentField(
                Pay)

        Doc.drop_collection()

        Doc(name=u"Wilson Junior",
            pay=Pay(values=[150, 100])).save()

        Doc(name=u"Isabella Luanna",
            pay=Pay(values=[530, 100])).save()

        Doc(name=u"Tayza mariana",
            pay=Pay(values=[165, 100])).save()

        Doc(name=u"Eliana Costa",
            pay=Pay(values=[115, 100])).save()

        self.assertEqual(
            Doc.objects.sum('pay.values'),
            1360)

    def test_array_sum(self):
        class Doc(Document):
            values = ListField(DecimalField())

        Doc.drop_collection()

        Doc(values=[150, 100]).save()
        Doc(values=[530, 100]).save()
        Doc(values=[165, 100]).save()
        Doc(values=[115, 100]).save()

        self.assertEqual(
            Doc.objects.sum('values'),
            1360)

    def test_distinct(self):
        """Ensure that the QuerySet.distinct method works.
        """
        self.Person(name='Mr Orange', age=20).save()
        self.Person(name='Mr White', age=20).save()
        self.Person(name='Mr Orange', age=30).save()
        self.Person(name='Mr Pink', age=30).save()
        self.assertEqual(set(self.Person.objects.distinct('name')),
                         set(['Mr Orange', 'Mr White', 'Mr Pink']))
        self.assertEqual(set(self.Person.objects.distinct('age')),
                         set([20, 30]))
        self.assertEqual(set(self.Person.objects(age=30).distinct('name')),
                         set(['Mr Orange', 'Mr Pink']))

    def test_distinct_handles_references(self):
        class Foo(Document):
            bar = ReferenceField("Bar")

        class Bar(Document):
            text = StringField()

        Bar.drop_collection()
        Foo.drop_collection()

        bar = Bar(text="hi")
        bar.save()

        foo = Foo(bar=bar)
        foo.save()

        self.assertEqual(Foo.objects.distinct("bar"), [bar])

    def test_distinct_handles_references_to_alias(self):
        register_connection('testdb', 'mongoenginetest2')

        class Foo(Document):
            bar = ReferenceField("Bar")
            meta = {'db_alias': 'testdb'}

        class Bar(Document):
            text = StringField()
            meta = {'db_alias': 'testdb'}

        Bar.drop_collection()
        Foo.drop_collection()

        bar = Bar(text="hi")
        bar.save()

        foo = Foo(bar=bar)
        foo.save()

        self.assertEqual(Foo.objects.distinct("bar"), [bar])

    def test_distinct_handles_db_field(self):
        """Ensure that distinct resolves field name to db_field as expected.
        """
        class Product(Document):
            product_id = IntField(db_field='pid')

        Product.drop_collection()

        Product(product_id=1).save()
        Product(product_id=2).save()
        Product(product_id=1).save()

        self.assertEqual(set(Product.objects.distinct('product_id')),
                         set([1, 2]))
        self.assertEqual(set(Product.objects.distinct('pid')),
                         set([1, 2]))

        Product.drop_collection()

    def test_distinct_ListField_EmbeddedDocumentField(self):

        class Author(EmbeddedDocument):
            name = StringField()

        class Book(Document):
            title = StringField()
            authors = ListField(EmbeddedDocumentField(Author))

        Book.drop_collection()

        mark_twain = Author(name="Mark Twain")
        john_tolkien = Author(name="John Ronald Reuel Tolkien")

        book = Book(title="Tom Sawyer", authors=[mark_twain]).save()
        book = Book(title="The Lord of the Rings", authors=[john_tolkien]).save()
        book = Book(title="The Stories", authors=[mark_twain, john_tolkien]).save()
        authors = Book.objects.distinct("authors")

        self.assertEqual(authors, [mark_twain, john_tolkien])

    def test_custom_manager(self):
        """Ensure that custom QuerySetManager instances work as expected.
        """
        class BlogPost(Document):
            tags = ListField(StringField())
            deleted = BooleanField(default=False)
            date = DateTimeField(default=datetime.now)

            @queryset_manager
            def objects(cls, qryset):
                opts = {"deleted": False}
                return qryset(**opts)

            @queryset_manager
            def music_posts(doc_cls, queryset, deleted=False):
                return queryset(tags='music',
                                deleted=deleted).order_by('date')

        BlogPost.drop_collection()

        post1 = BlogPost(tags=['music', 'film']).save()
        post2 = BlogPost(tags=['music']).save()
        post3 = BlogPost(tags=['film', 'actors']).save()
        post4 = BlogPost(tags=['film', 'actors', 'music'], deleted=True).save()

        self.assertEqual([p.id for p in BlogPost.objects()],
                         [post1.id, post2.id, post3.id])
        self.assertEqual([p.id for p in BlogPost.music_posts()],
                         [post1.id, post2.id])

        self.assertEqual([p.id for p in BlogPost.music_posts(True)],
                         [post4.id])

        BlogPost.drop_collection()

    def test_custom_manager_overriding_objects_works(self):

        class Foo(Document):
            bar = StringField(default='bar')
            active = BooleanField(default=False)

            @queryset_manager
            def objects(doc_cls, queryset):
                return queryset(active=True)

            @queryset_manager
            def with_inactive(doc_cls, queryset):
                return queryset(active=False)

        Foo.drop_collection()

        Foo(active=True).save()
        Foo(active=False).save()

        self.assertEqual(1, Foo.objects.count())
        self.assertEqual(1, Foo.with_inactive.count())

        Foo.with_inactive.first().delete()
        self.assertEqual(0, Foo.with_inactive.count())
        self.assertEqual(1, Foo.objects.count())

    def test_inherit_objects(self):

        class Foo(Document):
            meta = {'allow_inheritance': True}
            active = BooleanField(default=True)

            @queryset_manager
            def objects(klass, queryset):
                return queryset(active=True)

        class Bar(Foo):
            pass

        Bar.drop_collection()
        Bar.objects.create(active=False)
        self.assertEqual(0, Bar.objects.count())

    def test_inherit_objects_override(self):

        class Foo(Document):
            meta = {'allow_inheritance': True}
            active = BooleanField(default=True)

            @queryset_manager
            def objects(klass, queryset):
                return queryset(active=True)

        class Bar(Foo):
            @queryset_manager
            def objects(klass, queryset):
                return queryset(active=False)

        Bar.drop_collection()
        Bar.objects.create(active=False)
        self.assertEqual(0, Foo.objects.count())
        self.assertEqual(1, Bar.objects.count())

    def test_query_value_conversion(self):
        """Ensure that query values are properly converted when necessary.
        """
        class BlogPost(Document):
            author = ReferenceField(self.Person)

        BlogPost.drop_collection()

        person = self.Person(name='test', age=30)
        person.save()

        post = BlogPost(author=person)
        post.save()

        # Test that query may be performed by providing a document as a value
        # while using a ReferenceField's name - the document should be
        # converted to an DBRef, which is legal, unlike a Document object
        post_obj = BlogPost.objects(author=person).first()
        self.assertEqual(post.id, post_obj.id)

        # Test that lists of values work when using the 'in', 'nin' and 'all'
        post_obj = BlogPost.objects(author__in=[person]).first()
        self.assertEqual(post.id, post_obj.id)

        BlogPost.drop_collection()

    def test_update_value_conversion(self):
        """Ensure that values used in updates are converted before use.
        """
        class Group(Document):
            members = ListField(ReferenceField(self.Person))

        Group.drop_collection()

        user1 = self.Person(name='user1')
        user1.save()
        user2 = self.Person(name='user2')
        user2.save()

        group = Group()
        group.save()

        Group.objects(id=group.id).update(set__members=[user1, user2])
        group.reload()

        self.assertTrue(len(group.members) == 2)
        self.assertEqual(group.members[0].name, user1.name)
        self.assertEqual(group.members[1].name, user2.name)

        Group.drop_collection()

    def test_dict_with_custom_baseclass(self):
        """Ensure DictField working with custom base clases.
        """
        class Test(Document):
            testdict = DictField()

        Test.drop_collection()

        t = Test(testdict={'f': 'Value'})
        t.save()

        self.assertEqual(Test.objects(testdict__f__startswith='Val').count(), 1)
        self.assertEqual(Test.objects(testdict__f='Value').count(), 1)
        Test.drop_collection()

        class Test(Document):
            testdict = DictField(basecls=StringField)

        t = Test(testdict={'f': 'Value'})
        t.save()

        self.assertEqual(Test.objects(testdict__f='Value').count(), 1)
        self.assertEqual(Test.objects(testdict__f__startswith='Val').count(), 1)
        Test.drop_collection()

    def test_bulk(self):
        """Ensure bulk querying by object id returns a proper dict.
        """
        class BlogPost(Document):
            title = StringField()

        BlogPost.drop_collection()

        post_1 = BlogPost(title="Post #1")
        post_2 = BlogPost(title="Post #2")
        post_3 = BlogPost(title="Post #3")
        post_4 = BlogPost(title="Post #4")
        post_5 = BlogPost(title="Post #5")

        post_1.save()
        post_2.save()
        post_3.save()
        post_4.save()
        post_5.save()

        ids = [post_1.id, post_2.id, post_5.id]
        objects = BlogPost.objects.in_bulk(ids)

        self.assertEqual(len(objects), 3)

        self.assertTrue(post_1.id in objects)
        self.assertTrue(post_2.id in objects)
        self.assertTrue(post_5.id in objects)

        self.assertTrue(objects[post_1.id].title == post_1.title)
        self.assertTrue(objects[post_2.id].title == post_2.title)
        self.assertTrue(objects[post_5.id].title == post_5.title)

        BlogPost.drop_collection()

    def tearDown(self):
        self.Person.drop_collection()

    def test_custom_querysets(self):
        """Ensure that custom QuerySet classes may be used.
        """
        class CustomQuerySet(QuerySet):
            def not_empty(self):
                return self.count() > 0

        class Post(Document):
            meta = {'queryset_class': CustomQuerySet}

        Post.drop_collection()

        self.assertTrue(isinstance(Post.objects, CustomQuerySet))
        self.assertFalse(Post.objects.not_empty())

        Post().save()
        self.assertTrue(Post.objects.not_empty())

        Post.drop_collection()

    def test_custom_querysets_set_manager_directly(self):
        """Ensure that custom QuerySet classes may be used.
        """

        class CustomQuerySet(QuerySet):
            def not_empty(self):
                return self.count() > 0

        class CustomQuerySetManager(QuerySetManager):
            queryset_class = CustomQuerySet

        class Post(Document):
            objects = CustomQuerySetManager()

        Post.drop_collection()

        self.assertTrue(isinstance(Post.objects, CustomQuerySet))
        self.assertFalse(Post.objects.not_empty())

        Post().save()
        self.assertTrue(Post.objects.not_empty())

        Post.drop_collection()

    def test_custom_querysets_managers_directly(self):
        """Ensure that custom QuerySet classes may be used.
        """

        class CustomQuerySetManager(QuerySetManager):

            @staticmethod
            def get_queryset(doc_cls, queryset):
                return queryset(is_published=True)

        class Post(Document):
            is_published = BooleanField(default=False)
            published = CustomQuerySetManager()

        Post.drop_collection()

        Post().save()
        Post(is_published=True).save()
        self.assertEqual(Post.objects.count(), 2)
        self.assertEqual(Post.published.count(), 1)

        Post.drop_collection()

    def test_custom_querysets_inherited(self):
        """Ensure that custom QuerySet classes may be used.
        """

        class CustomQuerySet(QuerySet):
            def not_empty(self):
                return self.count() > 0

        class Base(Document):
            meta = {'abstract': True, 'queryset_class': CustomQuerySet}

        class Post(Base):
            pass

        Post.drop_collection()
        self.assertTrue(isinstance(Post.objects, CustomQuerySet))
        self.assertFalse(Post.objects.not_empty())

        Post().save()
        self.assertTrue(Post.objects.not_empty())

        Post.drop_collection()

    def test_custom_querysets_inherited_direct(self):
        """Ensure that custom QuerySet classes may be used.
        """

        class CustomQuerySet(QuerySet):
            def not_empty(self):
                return self.count() > 0

        class CustomQuerySetManager(QuerySetManager):
            queryset_class = CustomQuerySet

        class Base(Document):
            meta = {'abstract': True}
            objects = CustomQuerySetManager()

        class Post(Base):
            pass

        Post.drop_collection()
        self.assertTrue(isinstance(Post.objects, CustomQuerySet))
        self.assertFalse(Post.objects.not_empty())

        Post().save()
        self.assertTrue(Post.objects.not_empty())

        Post.drop_collection()

    def test_count_limit_and_skip(self):
        class Post(Document):
            title = StringField()

        Post.drop_collection()

        for i in xrange(10):
            Post(title="Post %s" % i).save()

        self.assertEqual(5, Post.objects.limit(5).skip(5).count())

        self.assertEqual(10, Post.objects.limit(5).skip(5).count(with_limit_and_skip=False))

    def test_count_and_none(self):
        """Test count works with None()"""

        class MyDoc(Document):
            pass

        MyDoc.drop_collection()
        for i in xrange(0, 10):
            MyDoc().save()

        self.assertEqual(MyDoc.objects.count(), 10)
        self.assertEqual(MyDoc.objects.none().count(), 0)

    def test_call_after_limits_set(self):
        """Ensure that re-filtering after slicing works
        """
        class Post(Document):
            title = StringField()

        Post.drop_collection()

        Post(title="Post 1").save()
        Post(title="Post 2").save()

        posts = Post.objects.all()[0:1]
        self.assertEqual(len(list(posts())), 1)

        Post.drop_collection()

    def test_order_then_filter(self):
        """Ensure that ordering still works after filtering.
        """
        class Number(Document):
            n = IntField()

        Number.drop_collection()

        n2 = Number.objects.create(n=2)
        n1 = Number.objects.create(n=1)

        self.assertEqual(list(Number.objects), [n2, n1])
        self.assertEqual(list(Number.objects.order_by('n')), [n1, n2])
        self.assertEqual(list(Number.objects.order_by('n').filter()), [n1, n2])

        Number.drop_collection()

    def test_clone(self):
        """Ensure that cloning clones complex querysets
        """
        class Number(Document):
            n = IntField()

        Number.drop_collection()

        for i in xrange(1, 101):
            t = Number(n=i)
            t.save()

        test = Number.objects
        test2 = test.clone()
        self.assertFalse(test == test2)
        self.assertEqual(test.count(), test2.count())

        test = test.filter(n__gt=11)
        test2 = test.clone()
        self.assertFalse(test == test2)
        self.assertEqual(test.count(), test2.count())

        test = test.limit(10)
        test2 = test.clone()
        self.assertFalse(test == test2)
        self.assertEqual(test.count(), test2.count())

        Number.drop_collection()

    def test_unset_reference(self):
        class Comment(Document):
            text = StringField()

        class Post(Document):
            comment = ReferenceField(Comment)

        Comment.drop_collection()
        Post.drop_collection()

        comment = Comment.objects.create(text='test')
        post = Post.objects.create(comment=comment)

        self.assertEqual(post.comment, comment)
        Post.objects.update(unset__comment=1)
        post.reload()
        self.assertEqual(post.comment, None)

        Comment.drop_collection()
        Post.drop_collection()

    def test_order_works_with_custom_db_field_names(self):
        class Number(Document):
            n = IntField(db_field='number')

        Number.drop_collection()

        n2 = Number.objects.create(n=2)
        n1 = Number.objects.create(n=1)

        self.assertEqual(list(Number.objects), [n2,n1])
        self.assertEqual(list(Number.objects.order_by('n')), [n1,n2])

        Number.drop_collection()

    def test_order_works_with_primary(self):
        """Ensure that order_by and primary work.
        """
        class Number(Document):
            n = IntField(primary_key=True)

        Number.drop_collection()

        Number(n=1).save()
        Number(n=2).save()
        Number(n=3).save()

        numbers = [n.n for n in Number.objects.order_by('-n')]
        self.assertEqual([3, 2, 1], numbers)

        numbers = [n.n for n in Number.objects.order_by('+n')]
        self.assertEqual([1, 2, 3], numbers)
        Number.drop_collection()

    def test_ensure_index(self):
        """Ensure that manual creation of indexes works.
        """
        class Comment(Document):
            message = StringField()
            meta = {'allow_inheritance': True}

        Comment.ensure_index('message')

        info = Comment.objects._collection.index_information()
        info = [(value['key'],
                 value.get('unique', False),
                 value.get('sparse', False))
                for key, value in info.iteritems()]
        self.assertTrue(([('_cls', 1), ('message', 1)], False, False) in info)

    def test_where(self):
        """Ensure that where clauses work.
        """

        class IntPair(Document):
            fielda = IntField()
            fieldb = IntField()

        IntPair.objects._collection.remove()

        a = IntPair(fielda=1, fieldb=1)
        b = IntPair(fielda=1, fieldb=2)
        c = IntPair(fielda=2, fieldb=1)
        a.save()
        b.save()
        c.save()

        query = IntPair.objects.where('this[~fielda] >= this[~fieldb]')
        self.assertEqual('this["fielda"] >= this["fieldb"]', query._where_clause)
        results = list(query)
        self.assertEqual(2, len(results))
        self.assertTrue(a in results)
        self.assertTrue(c in results)

        query = IntPair.objects.where('this[~fielda] == this[~fieldb]')
        results = list(query)
        self.assertEqual(1, len(results))
        self.assertTrue(a in results)

        query = IntPair.objects.where('function() { return this[~fielda] >= this[~fieldb] }')
        self.assertEqual('function() { return this["fielda"] >= this["fieldb"] }', query._where_clause)
        results = list(query)
        self.assertEqual(2, len(results))
        self.assertTrue(a in results)
        self.assertTrue(c in results)

        def invalid_where():
            list(IntPair.objects.where(fielda__gte=3))

        self.assertRaises(TypeError, invalid_where)

    def test_scalar(self):

        class Organization(Document):
            id = ObjectIdField('_id')
            name = StringField()

        class User(Document):
            id = ObjectIdField('_id')
            name = StringField()
            organization = ObjectIdField()

        User.drop_collection()
        Organization.drop_collection()

        whitehouse = Organization(name="White House")
        whitehouse.save()
        User(name="Bob Dole", organization=whitehouse.id).save()

        # Efficient way to get all unique organization names for a given
        # set of users (Pretend this has additional filtering.)
        user_orgs = set(User.objects.scalar('organization'))
        orgs = Organization.objects(id__in=user_orgs).scalar('name')
        self.assertEqual(list(orgs), ['White House'])

        # Efficient for generating listings, too.
        orgs = Organization.objects.scalar('name').in_bulk(list(user_orgs))
        user_map = User.objects.scalar('name', 'organization')
        user_listing = [(user, orgs[org]) for user, org in user_map]
        self.assertEqual([("Bob Dole", "White House")], user_listing)

    def test_scalar_simple(self):
        class TestDoc(Document):
            x = IntField()
            y = BooleanField()

        TestDoc.drop_collection()

        TestDoc(x=10, y=True).save()
        TestDoc(x=20, y=False).save()
        TestDoc(x=30, y=True).save()

        plist = list(TestDoc.objects.scalar('x', 'y'))

        self.assertEqual(len(plist), 3)
        self.assertEqual(plist[0], (10, True))
        self.assertEqual(plist[1], (20, False))
        self.assertEqual(plist[2], (30, True))

        class UserDoc(Document):
            name = StringField()
            age = IntField()

        UserDoc.drop_collection()

        UserDoc(name="Wilson Jr", age=19).save()
        UserDoc(name="Wilson", age=43).save()
        UserDoc(name="Eliana", age=37).save()
        UserDoc(name="Tayza", age=15).save()

        ulist = list(UserDoc.objects.scalar('name', 'age'))

        self.assertEqual(ulist, [
                (u'Wilson Jr', 19),
                (u'Wilson', 43),
                (u'Eliana', 37),
                (u'Tayza', 15)])

        ulist = list(UserDoc.objects.scalar('name').order_by('age'))

        self.assertEqual(ulist, [
                (u'Tayza'),
                (u'Wilson Jr'),
                (u'Eliana'),
                (u'Wilson')])

    def test_scalar_embedded(self):
        class Profile(EmbeddedDocument):
            name = StringField()
            age = IntField()

        class Locale(EmbeddedDocument):
            city = StringField()
            country = StringField()

        class Person(Document):
            profile = EmbeddedDocumentField(Profile)
            locale = EmbeddedDocumentField(Locale)

        Person.drop_collection()

        Person(profile=Profile(name="Wilson Jr", age=19),
               locale=Locale(city="Corumba-GO", country="Brazil")).save()

        Person(profile=Profile(name="Gabriel Falcao", age=23),
               locale=Locale(city="New York", country="USA")).save()

        Person(profile=Profile(name="Lincoln de souza", age=28),
               locale=Locale(city="Belo Horizonte", country="Brazil")).save()

        Person(profile=Profile(name="Walter cruz", age=30),
               locale=Locale(city="Brasilia", country="Brazil")).save()

        self.assertEqual(
            list(Person.objects.order_by('profile__age').scalar('profile__name')),
            [u'Wilson Jr', u'Gabriel Falcao', u'Lincoln de souza', u'Walter cruz'])

        ulist = list(Person.objects.order_by('locale.city')
                     .scalar('profile__name', 'profile__age', 'locale__city'))
        self.assertEqual(ulist,
                         [(u'Lincoln de souza', 28, u'Belo Horizonte'),
                          (u'Walter cruz', 30, u'Brasilia'),
                          (u'Wilson Jr', 19, u'Corumba-GO'),
                          (u'Gabriel Falcao', 23, u'New York')])

    def test_scalar_decimal(self):
        from decimal import Decimal
        class Person(Document):
            name = StringField()
            rating = DecimalField()

        Person.drop_collection()
        Person(name="Wilson Jr", rating=Decimal('1.0')).save()

        ulist = list(Person.objects.scalar('name', 'rating'))
        self.assertEqual(ulist, [(u'Wilson Jr', Decimal('1.0'))])


    def test_scalar_reference_field(self):
        class State(Document):
            name = StringField()

        class Person(Document):
            name = StringField()
            state = ReferenceField(State)

        State.drop_collection()
        Person.drop_collection()

        s1 = State(name="Goias")
        s1.save()

        Person(name="Wilson JR", state=s1).save()

        plist = list(Person.objects.scalar('name', 'state'))
        self.assertEqual(plist, [(u'Wilson JR', s1)])

    def test_scalar_generic_reference_field(self):
        class State(Document):
            name = StringField()

        class Person(Document):
            name = StringField()
            state = GenericReferenceField()

        State.drop_collection()
        Person.drop_collection()

        s1 = State(name="Goias")
        s1.save()

        Person(name="Wilson JR", state=s1).save()

        plist = list(Person.objects.scalar('name', 'state'))
        self.assertEqual(plist, [(u'Wilson JR', s1)])

    def test_scalar_db_field(self):

        class TestDoc(Document):
            x = IntField()
            y = BooleanField()

        TestDoc.drop_collection()

        TestDoc(x=10, y=True).save()
        TestDoc(x=20, y=False).save()
        TestDoc(x=30, y=True).save()

        plist = list(TestDoc.objects.scalar('x', 'y'))
        self.assertEqual(len(plist), 3)
        self.assertEqual(plist[0], (10, True))
        self.assertEqual(plist[1], (20, False))
        self.assertEqual(plist[2], (30, True))

    def test_scalar_primary_key(self):

        class SettingValue(Document):
            key = StringField(primary_key=True)
            value = StringField()

        SettingValue.drop_collection()
        s = SettingValue(key="test", value="test value")
        s.save()

        val = SettingValue.objects.scalar('key', 'value')
        self.assertEqual(list(val), [('test', 'test value')])

    def test_scalar_cursor_behaviour(self):
        """Ensure that a query returns a valid set of results.
        """
        person1 = self.Person(name="User A", age=20)
        person1.save()
        person2 = self.Person(name="User B", age=30)
        person2.save()

        # Find all people in the collection
        people = self.Person.objects.scalar('name')
        self.assertEqual(people.count(), 2)
        results = list(people)
        self.assertEqual(results[0], "User A")
        self.assertEqual(results[1], "User B")

        # Use a query to filter the people found to just person1
        people = self.Person.objects(age=20).scalar('name')
        self.assertEqual(people.count(), 1)
        person = people.next()
        self.assertEqual(person, "User A")

        # Test limit
        people = list(self.Person.objects.limit(1).scalar('name'))
        self.assertEqual(len(people), 1)
        self.assertEqual(people[0], 'User A')

        # Test skip
        people = list(self.Person.objects.skip(1).scalar('name'))
        self.assertEqual(len(people), 1)
        self.assertEqual(people[0], 'User B')

        person3 = self.Person(name="User C", age=40)
        person3.save()

        # Test slice limit
        people = list(self.Person.objects[:2].scalar('name'))
        self.assertEqual(len(people), 2)
        self.assertEqual(people[0], 'User A')
        self.assertEqual(people[1], 'User B')

        # Test slice skip
        people = list(self.Person.objects[1:].scalar('name'))
        self.assertEqual(len(people), 2)
        self.assertEqual(people[0], 'User B')
        self.assertEqual(people[1], 'User C')

        # Test slice limit and skip
        people = list(self.Person.objects[1:2].scalar('name'))
        self.assertEqual(len(people), 1)
        self.assertEqual(people[0], 'User B')

        people = list(self.Person.objects[1:1].scalar('name'))
        self.assertEqual(len(people), 0)

        # Test slice out of range
        people = list(self.Person.objects.scalar('name')[80000:80001])
        self.assertEqual(len(people), 0)

        # Test larger slice __repr__
        self.Person.objects.delete()
        for i in xrange(55):
            self.Person(name='A%s' % i, age=i).save()

        self.assertEqual(self.Person.objects.scalar('name').count(), 55)
        self.assertEqual("A0", "%s" % self.Person.objects.order_by('name').scalar('name').first())
        self.assertEqual("A0", "%s" % self.Person.objects.scalar('name').order_by('name')[0])
        if PY3:
            self.assertEqual("['A1', 'A2']",  "%s" % self.Person.objects.order_by('age').scalar('name')[1:3])
            self.assertEqual("['A51', 'A52']",  "%s" % self.Person.objects.order_by('age').scalar('name')[51:53])
        else:
            self.assertEqual("[u'A1', u'A2']",  "%s" % self.Person.objects.order_by('age').scalar('name')[1:3])
            self.assertEqual("[u'A51', u'A52']",  "%s" % self.Person.objects.order_by('age').scalar('name')[51:53])

        # with_id and in_bulk
        person = self.Person.objects.order_by('name').first()
        self.assertEqual("A0", "%s" % self.Person.objects.scalar('name').with_id(person.id))

        pks = self.Person.objects.order_by('age').scalar('pk')[1:3]
        if PY3:
            self.assertEqual("['A1', 'A2']",  "%s" % sorted(self.Person.objects.scalar('name').in_bulk(list(pks)).values()))
        else:
            self.assertEqual("[u'A1', u'A2']",  "%s" % sorted(self.Person.objects.scalar('name').in_bulk(list(pks)).values()))

    def test_elem_match(self):
        class Foo(EmbeddedDocument):
            shape = StringField()
            color = StringField()
            thick = BooleanField()
            meta = {'allow_inheritance': False}

        class Bar(Document):
            foo = ListField(EmbeddedDocumentField(Foo))
            meta = {'allow_inheritance': False}

        Bar.drop_collection()

        b1 = Bar(foo=[Foo(shape="square", color="purple", thick=False),
                      Foo(shape="circle", color="red", thick=True)])
        b1.save()

        b2 = Bar(foo=[Foo(shape="square", color="red", thick=True),
                      Foo(shape="circle", color="purple", thick=False)])
        b2.save()

        ak = list(Bar.objects(foo__match={'shape': "square", "color": "purple"}))
        self.assertEqual([b1], ak)

        ak = list(Bar.objects(foo__match=Foo(shape="square", color="purple")))
        self.assertEqual([b1], ak)

    def test_upsert_includes_cls(self):
        """Upserts should include _cls information for inheritable classes
        """

        class Test(Document):
            test = StringField()

        Test.drop_collection()
        Test.objects(test='foo').update_one(upsert=True, set__test='foo')
        self.assertFalse('_cls' in Test._collection.find_one())

        class Test(Document):
            meta = {'allow_inheritance': True}
            test = StringField()

        Test.drop_collection()

        Test.objects(test='foo').update_one(upsert=True, set__test='foo')
        self.assertTrue('_cls' in Test._collection.find_one())

    def test_update_upsert_looks_like_a_digit(self):
        class MyDoc(DynamicDocument):
            pass
        MyDoc.drop_collection()
        self.assertEqual(1, MyDoc.objects.update_one(upsert=True, inc__47=1))
        self.assertEqual(MyDoc.objects.get()['47'], 1)

    def test_dictfield_key_looks_like_a_digit(self):
        """Only should work with DictField even if they have numeric keys."""

        class MyDoc(Document):
            test = DictField()

        MyDoc.drop_collection()
        doc = MyDoc(test={'47': 1})
        doc.save()
        self.assertEqual(MyDoc.objects.only('test__47').get().test['47'], 1)

    def test_read_preference(self):
        class Bar(Document):
            pass

        Bar.drop_collection()
        bars = list(Bar.objects(read_preference=ReadPreference.PRIMARY))
        self.assertEqual([], bars)

        self.assertRaises(ConfigurationError, Bar.objects,
                          read_preference='Primary')

        bars = Bar.objects(read_preference=ReadPreference.SECONDARY_PREFERRED)
        self.assertEqual(bars._read_preference, ReadPreference.SECONDARY_PREFERRED)

    def test_json_simple(self):

        class Embedded(EmbeddedDocument):
            string = StringField()

        class Doc(Document):
            string = StringField()
            embedded_field = EmbeddedDocumentField(Embedded)

        Doc.drop_collection()
        Doc(string="Hi", embedded_field=Embedded(string="Hi")).save()
        Doc(string="Bye", embedded_field=Embedded(string="Bye")).save()

        Doc().save()
        json_data = Doc.objects.to_json(sort_keys=True, separators=(',', ':'))
        doc_objects = list(Doc.objects)

        self.assertEqual(doc_objects, Doc.objects.from_json(json_data))

    def test_json_complex(self):
        if pymongo.version_tuple[0] <= 2 and pymongo.version_tuple[1] <= 3:
            raise SkipTest("Need pymongo 2.4 as has a fix for DBRefs")

        class EmbeddedDoc(EmbeddedDocument):
            pass

        class Simple(Document):
            pass

        class Doc(Document):
            string_field = StringField(default='1')
            int_field = IntField(default=1)
            float_field = FloatField(default=1.1)
            boolean_field = BooleanField(default=True)
            datetime_field = DateTimeField(default=datetime.now)
            embedded_document_field = EmbeddedDocumentField(
                EmbeddedDoc, default=lambda: EmbeddedDoc())
            list_field = ListField(default=lambda: [1, 2, 3])
            dict_field = DictField(default=lambda: {"hello": "world"})
            objectid_field = ObjectIdField(default=ObjectId)
            reference_field = ReferenceField(Simple, default=lambda: Simple().save())
            map_field = MapField(IntField(), default=lambda: {"simple": 1})
            decimal_field = DecimalField(default=1.0)
            complex_datetime_field = ComplexDateTimeField(default=datetime.now)
            url_field = URLField(default="http://mongoengine.org")
            dynamic_field = DynamicField(default=1)
            generic_reference_field = GenericReferenceField(default=lambda: Simple().save())
            sorted_list_field = SortedListField(IntField(),
                                                default=lambda: [1, 2, 3])
            email_field = EmailField(default="ross@example.com")
            geo_point_field = GeoPointField(default=lambda: [1, 2])
            sequence_field = SequenceField()
            uuid_field = UUIDField(default=uuid.uuid4)
            generic_embedded_document_field = GenericEmbeddedDocumentField(
                default=lambda: EmbeddedDoc())

        Simple.drop_collection()
        Doc.drop_collection()

        Doc().save()
        json_data = Doc.objects.to_json()
        doc_objects = list(Doc.objects)

        self.assertEqual(doc_objects, Doc.objects.from_json(json_data))

    def test_as_pymongo(self):

        from decimal import Decimal

        class User(Document):
            id = ObjectIdField('_id')
            name = StringField()
            age = IntField()
            price = DecimalField()

        User.drop_collection()
        User(name="Bob Dole", age=89, price=Decimal('1.11')).save()
        User(name="Barack Obama", age=51, price=Decimal('2.22')).save()

        results = User.objects.only('id', 'name').as_pymongo()
        self.assertEqual(sorted(results[0].keys()), sorted(['_id', 'name']))

        users = User.objects.only('name', 'price').as_pymongo()
        results = list(users)
        self.assertTrue(isinstance(results[0], dict))
        self.assertTrue(isinstance(results[1], dict))
        self.assertEqual(results[0]['name'], 'Bob Dole')
        self.assertEqual(results[0]['price'], 1.11)
        self.assertEqual(results[1]['name'], 'Barack Obama')
        self.assertEqual(results[1]['price'], 2.22)

        # Test coerce_types
        users = User.objects.only('name', 'price').as_pymongo(coerce_types=True)
        results = list(users)
        self.assertTrue(isinstance(results[0], dict))
        self.assertTrue(isinstance(results[1], dict))
        self.assertEqual(results[0]['name'], 'Bob Dole')
        self.assertEqual(results[0]['price'], Decimal('1.11'))
        self.assertEqual(results[1]['name'], 'Barack Obama')
        self.assertEqual(results[1]['price'], Decimal('2.22'))

    def test_as_pymongo_json_limit_fields(self):

        class User(Document):
            email = EmailField(unique=True, required=True)
            password_hash = StringField(db_field='password_hash', required=True)
            password_salt = StringField(db_field='password_salt', required=True)

        User.drop_collection()
        User(email="ross@example.com", password_salt="SomeSalt", password_hash="SomeHash").save()

        serialized_user = User.objects.exclude('password_salt', 'password_hash').as_pymongo()[0]
        self.assertEqual(set(['_id', 'email']), set(serialized_user.keys()))

        serialized_user = User.objects.exclude('id', 'password_salt', 'password_hash').to_json()
        self.assertEqual('[{"email": "ross@example.com"}]', serialized_user)

        serialized_user = User.objects.exclude('password_salt').only('email').as_pymongo()[0]
        self.assertEqual(set(['email']), set(serialized_user.keys()))

        serialized_user = User.objects.exclude('password_salt').only('email').to_json()
        self.assertEqual('[{"email": "ross@example.com"}]', serialized_user)

    def test_no_dereference(self):

        class Organization(Document):
            name = StringField()

        class User(Document):
            name = StringField()
            organization = ReferenceField(Organization)

        User.drop_collection()
        Organization.drop_collection()

        whitehouse = Organization(name="White House").save()
        User(name="Bob Dole", organization=whitehouse).save()

        qs = User.objects()
        self.assertTrue(isinstance(qs.first().organization, Organization))
        self.assertFalse(isinstance(qs.no_dereference().first().organization,
                                    Organization))
        self.assertFalse(isinstance(qs.no_dereference().get().organization,
                                    Organization))
        self.assertTrue(isinstance(qs.first().organization, Organization))

    def test_cached_queryset(self):
        class Person(Document):
            name = StringField()

        Person.drop_collection()
        for i in xrange(100):
            Person(name="No: %s" % i).save()

        with query_counter() as q:
            self.assertEqual(q, 0)
            people = Person.objects

            [x for x in people]
            self.assertEqual(100, len(people._result_cache))
            self.assertEqual(None, people._len)
            self.assertEqual(q, 1)

            list(people)
            self.assertEqual(100, people._len)  # Caused by list calling len
            self.assertEqual(q, 1)

            people.count()  # count is cached
            self.assertEqual(q, 1)

    def test_no_cached_queryset(self):
        class Person(Document):
            name = StringField()

        Person.drop_collection()
        for i in xrange(100):
            Person(name="No: %s" % i).save()

        with query_counter() as q:
            self.assertEqual(q, 0)
            people = Person.objects.no_cache()

            [x for x in people]
            self.assertEqual(q, 1)

            list(people)
            self.assertEqual(q, 2)

            people.count()
            self.assertEqual(q, 3)

    def test_cache_not_cloned(self):

        class User(Document):
            name = StringField()

            def __unicode__(self):
                return self.name

        User.drop_collection()

        User(name="Alice").save()
        User(name="Bob").save()

        users = User.objects.all().order_by('name')
        self.assertEqual("%s" % users, "[<User: Alice>, <User: Bob>]")
        self.assertEqual(2, len(users._result_cache))

        users = users.filter(name="Bob")
        self.assertEqual("%s" % users, "[<User: Bob>]")
        self.assertEqual(1, len(users._result_cache))

    def test_no_cache(self):
        """Ensure you can add meta data to file"""

        class Noddy(Document):
            fields = DictField()

        Noddy.drop_collection()
        for i in xrange(100):
            noddy = Noddy()
            for j in range(20):
                noddy.fields["key"+str(j)] = "value "+str(j)
            noddy.save()

        docs = Noddy.objects.no_cache()

        counter = len([1 for i in docs])
        self.assertEqual(counter, 100)

        self.assertEqual(len(list(docs)), 100)
        self.assertRaises(TypeError, lambda: len(docs))

        with query_counter() as q:
            self.assertEqual(q, 0)
            list(docs)
            self.assertEqual(q, 1)
            list(docs)
            self.assertEqual(q, 2)

    def test_nested_queryset_iterator(self):
        # Try iterating the same queryset twice, nested.
        names = ['Alice', 'Bob', 'Chuck', 'David', 'Eric', 'Francis', 'George']

        class User(Document):
            name = StringField()

            def __unicode__(self):
                return self.name

        User.drop_collection()

        for name in names:
            User(name=name).save()

        users = User.objects.all().order_by('name')
        outer_count = 0
        inner_count = 0
        inner_total_count = 0

        with query_counter() as q:
            self.assertEqual(q, 0)

            self.assertEqual(users.count(), 7)

            for i, outer_user in enumerate(users):
                self.assertEqual(outer_user.name, names[i])
                outer_count += 1
                inner_count = 0

                # Calling len might disrupt the inner loop if there are bugs
                self.assertEqual(users.count(), 7)

                for j, inner_user in enumerate(users):
                    self.assertEqual(inner_user.name, names[j])
                    inner_count += 1
                    inner_total_count += 1

                self.assertEqual(inner_count, 7)  # inner loop should always be executed seven times

            self.assertEqual(outer_count, 7)  # outer loop should be executed seven times total
            self.assertEqual(inner_total_count, 7 * 7)  # inner loop should be executed fourtynine times total

            self.assertEqual(q, 2)

    def test_no_sub_classes(self):
        class A(Document):
            x = IntField()
            y = IntField()

            meta = {'allow_inheritance': True}

        class B(A):
            z = IntField()

        class C(B):
            zz = IntField()

        A.drop_collection()

        A(x=10, y=20).save()
        A(x=15, y=30).save()
        B(x=20, y=40).save()
        B(x=30, y=50).save()
        C(x=40, y=60).save()

        self.assertEqual(A.objects.no_sub_classes().count(), 2)
        self.assertEqual(A.objects.count(), 5)

        self.assertEqual(B.objects.no_sub_classes().count(), 2)
        self.assertEqual(B.objects.count(), 3)

        self.assertEqual(C.objects.no_sub_classes().count(), 1)
        self.assertEqual(C.objects.count(), 1)

        for obj in A.objects.no_sub_classes():
            self.assertEqual(obj.__class__, A)

        for obj in B.objects.no_sub_classes():
            self.assertEqual(obj.__class__, B)

        for obj in C.objects.no_sub_classes():
            self.assertEqual(obj.__class__, C)

    def test_query_reference_to_custom_pk_doc(self):

        class A(Document):
            id = StringField(unique=True, primary_key=True)

        class B(Document):
            a = ReferenceField(A)

        A.drop_collection()
        B.drop_collection()

        a = A.objects.create(id='custom_id')

        b = B.objects.create(a=a)

        self.assertEqual(B.objects.count(), 1)
        self.assertEqual(B.objects.get(a=a).a, a)
        self.assertEqual(B.objects.get(a=a.id).a, a)

    def test_cls_query_in_subclassed_docs(self):

        class Animal(Document):
            name = StringField()

            meta = {
                'allow_inheritance': True
            }

        class Dog(Animal):
            pass

        class Cat(Animal):
            pass

        self.assertEqual(Animal.objects(name='Charlie')._query, {
            'name': 'Charlie',
            '_cls': { '$in': ('Animal', 'Animal.Dog', 'Animal.Cat') }
        })
        self.assertEqual(Dog.objects(name='Charlie')._query, {
            'name': 'Charlie',
            '_cls': 'Animal.Dog'
        })
        self.assertEqual(Cat.objects(name='Charlie')._query, {
            'name': 'Charlie',
            '_cls': 'Animal.Cat'
        })

    def test_can_have_field_same_name_as_query_operator(self):

        class Size(Document):
            name = StringField()

        class Example(Document):
            size = ReferenceField(Size)

        Size.drop_collection()
        Example.drop_collection()

        instance_size = Size(name="Large").save()
        Example(size=instance_size).save()

        self.assertEqual(Example.objects(size=instance_size).count(), 1)
        self.assertEqual(Example.objects(size__in=[instance_size]).count(), 1)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = transform
import sys
sys.path[0:0] = [""]

import unittest

from mongoengine import *
from mongoengine.queryset import Q
from mongoengine.queryset import transform

__all__ = ("TransformTest",)


class TransformTest(unittest.TestCase):

    def setUp(self):
        connect(db='mongoenginetest')

    def test_transform_query(self):
        """Ensure that the _transform_query function operates correctly.
        """
        self.assertEqual(transform.query(name='test', age=30),
                         {'name': 'test', 'age': 30})
        self.assertEqual(transform.query(age__lt=30),
                         {'age': {'$lt': 30}})
        self.assertEqual(transform.query(age__gt=20, age__lt=50),
                         {'age': {'$gt': 20, '$lt': 50}})
        self.assertEqual(transform.query(age=20, age__gt=50),
                         {'$and': [{'age': {'$gt': 50}}, {'age': 20}]})
        self.assertEqual(transform.query(friend__age__gte=30),
                         {'friend.age': {'$gte': 30}})
        self.assertEqual(transform.query(name__exists=True),
                         {'name': {'$exists': True}})

    def test_transform_update(self):
        class DicDoc(Document):
            dictField = DictField()

        class Doc(Document):
            pass

        DicDoc.drop_collection()
        Doc.drop_collection()

        doc = Doc().save()
        dic_doc = DicDoc().save()

        for k, v in (("set", "$set"), ("set_on_insert", "$setOnInsert"), ("push", "$push")):
            update = transform.update(DicDoc, **{"%s__dictField__test" % k: doc})
            self.assertTrue(isinstance(update[v]["dictField.test"], dict))

        # Update special cases
        update = transform.update(DicDoc, unset__dictField__test=doc)
        self.assertEqual(update["$unset"]["dictField.test"], 1)

        update = transform.update(DicDoc, pull__dictField__test=doc)
        self.assertTrue(isinstance(update["$pull"]["dictField"]["test"], dict))


    def test_query_field_name(self):
        """Ensure that the correct field name is used when querying.
        """
        class Comment(EmbeddedDocument):
            content = StringField(db_field='commentContent')

        class BlogPost(Document):
            title = StringField(db_field='postTitle')
            comments = ListField(EmbeddedDocumentField(Comment),
                                 db_field='postComments')

        BlogPost.drop_collection()

        data = {'title': 'Post 1', 'comments': [Comment(content='test')]}
        post = BlogPost(**data)
        post.save()

        self.assertTrue('postTitle' in
                        BlogPost.objects(title=data['title'])._query)
        self.assertFalse('title' in
                         BlogPost.objects(title=data['title'])._query)
        self.assertEqual(BlogPost.objects(title=data['title']).count(), 1)

        self.assertTrue('_id' in BlogPost.objects(pk=post.id)._query)
        self.assertEqual(BlogPost.objects(pk=post.id).count(), 1)

        self.assertTrue('postComments.commentContent' in
                        BlogPost.objects(comments__content='test')._query)
        self.assertEqual(BlogPost.objects(comments__content='test').count(), 1)

        BlogPost.drop_collection()

    def test_query_pk_field_name(self):
        """Ensure that the correct "primary key" field name is used when
        querying
        """
        class BlogPost(Document):
            title = StringField(primary_key=True, db_field='postTitle')

        BlogPost.drop_collection()

        data = {'title': 'Post 1'}
        post = BlogPost(**data)
        post.save()

        self.assertTrue('_id' in BlogPost.objects(pk=data['title'])._query)
        self.assertTrue('_id' in BlogPost.objects(title=data['title'])._query)
        self.assertEqual(BlogPost.objects(pk=data['title']).count(), 1)

        BlogPost.drop_collection()

    def test_chaining(self):
        class A(Document):
            pass

        class B(Document):
            a = ReferenceField(A)

        A.drop_collection()
        B.drop_collection()

        a1 = A().save()
        a2 = A().save()

        B(a=a1).save()

        # Works
        q1 = B.objects.filter(a__in=[a1, a2], a=a1)._query

        # Doesn't work
        q2 = B.objects.filter(a__in=[a1, a2])
        q2 = q2.filter(a=a1)._query

        self.assertEqual(q1, q2)

    def test_raw_query_and_Q_objects(self):
        """
        Test raw plays nicely
        """
        class Foo(Document):
            name = StringField()
            a = StringField()
            b = StringField()
            c = StringField()

            meta = {
                'allow_inheritance': False
            }

        query = Foo.objects(__raw__={'$nor': [{'name': 'bar'}]})._query
        self.assertEqual(query, {'$nor': [{'name': 'bar'}]})

        q1 = {'$or': [{'a': 1}, {'b': 1}]}
        query = Foo.objects(Q(__raw__=q1) & Q(c=1))._query
        self.assertEqual(query, {'$or': [{'a': 1}, {'b': 1}], 'c': 1})

    def test_raw_and_merging(self):
        class Doc(Document):
            meta = {'allow_inheritance': False}

        raw_query = Doc.objects(__raw__={'deleted': False,
                                'scraped': 'yes',
                                '$nor': [{'views.extracted': 'no'},
                                         {'attachments.views.extracted':'no'}]
                                })._query

        expected = {'deleted': False, 'scraped': 'yes',
                    '$nor': [{'views.extracted': 'no'},
                             {'attachments.views.extracted': 'no'}]}
        self.assertEqual(expected, raw_query)

    def test_geojson_PointField(self):
        class Location(Document):
            loc = PointField()

        update = transform.update(Location, set__loc=[1, 2])
        self.assertEqual(update, {'$set': {'loc': {"type": "Point", "coordinates": [1,2]}}})

        update = transform.update(Location, set__loc={"type": "Point", "coordinates": [1,2]})
        self.assertEqual(update, {'$set': {'loc': {"type": "Point", "coordinates": [1,2]}}})

    def test_geojson_LineStringField(self):
        class Location(Document):
            line = LineStringField()

        update = transform.update(Location, set__line=[[1, 2], [2, 2]])
        self.assertEqual(update, {'$set': {'line': {"type": "LineString", "coordinates": [[1, 2], [2, 2]]}}})

        update = transform.update(Location, set__line={"type": "LineString", "coordinates": [[1, 2], [2, 2]]})
        self.assertEqual(update, {'$set': {'line': {"type": "LineString", "coordinates": [[1, 2], [2, 2]]}}})

    def test_geojson_PolygonField(self):
        class Location(Document):
            poly = PolygonField()

        update = transform.update(Location, set__poly=[[[40, 5], [40, 6], [41, 6], [40, 5]]])
        self.assertEqual(update, {'$set': {'poly': {"type": "Polygon", "coordinates": [[[40, 5], [40, 6], [41, 6], [40, 5]]]}}})

        update = transform.update(Location, set__poly={"type": "Polygon", "coordinates": [[[40, 5], [40, 6], [41, 6], [40, 5]]]})
        self.assertEqual(update, {'$set': {'poly': {"type": "Polygon", "coordinates": [[[40, 5], [40, 6], [41, 6], [40, 5]]]}}})

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = visitor
import sys
sys.path[0:0] = [""]

import unittest

from bson import ObjectId
from datetime import datetime

from mongoengine import *
from mongoengine.queryset import Q
from mongoengine.errors import InvalidQueryError

__all__ = ("QTest",)


class QTest(unittest.TestCase):

    def setUp(self):
        connect(db='mongoenginetest')

        class Person(Document):
            name = StringField()
            age = IntField()
            meta = {'allow_inheritance': True}

        Person.drop_collection()
        self.Person = Person

    def test_empty_q(self):
        """Ensure that empty Q objects won't hurt.
        """
        q1 = Q()
        q2 = Q(age__gte=18)
        q3 = Q()
        q4 = Q(name='test')
        q5 = Q()

        class Person(Document):
            name = StringField()
            age = IntField()

        query = {'$or': [{'age': {'$gte': 18}}, {'name': 'test'}]}
        self.assertEqual((q1 | q2 | q3 | q4 | q5).to_query(Person), query)

        query = {'age': {'$gte': 18}, 'name': 'test'}
        self.assertEqual((q1 & q2 & q3 & q4 & q5).to_query(Person), query)

    def test_q_with_dbref(self):
        """Ensure Q objects handle DBRefs correctly"""
        connect(db='mongoenginetest')

        class User(Document):
            pass

        class Post(Document):
            created_user = ReferenceField(User)

        user = User.objects.create()
        Post.objects.create(created_user=user)

        self.assertEqual(Post.objects.filter(created_user=user).count(), 1)
        self.assertEqual(Post.objects.filter(Q(created_user=user)).count(), 1)

    def test_and_combination(self):
        """Ensure that Q-objects correctly AND together.
        """
        class TestDoc(Document):
            x = IntField()
            y = StringField()

        query = (Q(x__lt=7) & Q(x__lt=3)).to_query(TestDoc)
        self.assertEqual(query, {'$and': [{'x': {'$lt': 7}}, {'x': {'$lt': 3}}]})

        query = (Q(y="a") & Q(x__lt=7) & Q(x__lt=3)).to_query(TestDoc)
        self.assertEqual(query, {'$and': [{'y': "a"}, {'x': {'$lt': 7}}, {'x': {'$lt': 3}}]})

        # Check normal cases work without an error
        query = Q(x__lt=7) & Q(x__gt=3)

        q1 = Q(x__lt=7)
        q2 = Q(x__gt=3)
        query = (q1 & q2).to_query(TestDoc)
        self.assertEqual(query, {'x': {'$lt': 7, '$gt': 3}})

        # More complex nested example
        query = Q(x__lt=100) & Q(y__ne='NotMyString')
        query &= Q(y__in=['a', 'b', 'c']) & Q(x__gt=-100)
        mongo_query = {
            'x': {'$lt': 100, '$gt': -100},
            'y': {'$ne': 'NotMyString', '$in': ['a', 'b', 'c']},
        }
        self.assertEqual(query.to_query(TestDoc), mongo_query)

    def test_or_combination(self):
        """Ensure that Q-objects correctly OR together.
        """
        class TestDoc(Document):
            x = IntField()

        q1 = Q(x__lt=3)
        q2 = Q(x__gt=7)
        query = (q1 | q2).to_query(TestDoc)
        self.assertEqual(query, {
            '$or': [
                {'x': {'$lt': 3}},
                {'x': {'$gt': 7}},
            ]
        })

    def test_and_or_combination(self):
        """Ensure that Q-objects handle ANDing ORed components.
        """
        class TestDoc(Document):
            x = IntField()
            y = BooleanField()

        TestDoc.drop_collection()

        query = (Q(x__gt=0) | Q(x__exists=False))
        query &= Q(x__lt=100)
        self.assertEqual(query.to_query(TestDoc), {'$and': [
            {'$or': [{'x': {'$gt': 0}},
                     {'x': {'$exists': False}}]},
            {'x': {'$lt': 100}}]
        })

        q1 = (Q(x__gt=0) | Q(x__exists=False))
        q2 = (Q(x__lt=100) | Q(y=True))
        query = (q1 & q2).to_query(TestDoc)

        TestDoc(x=101).save()
        TestDoc(x=10).save()
        TestDoc(y=True).save()

        self.assertEqual(query,
        {'$and': [
            {'$or': [{'x': {'$gt': 0}}, {'x': {'$exists': False}}]},
            {'$or': [{'x': {'$lt': 100}}, {'y': True}]}
        ]})

        self.assertEqual(2, TestDoc.objects(q1 & q2).count())

    def test_or_and_or_combination(self):
        """Ensure that Q-objects handle ORing ANDed ORed components. :)
        """
        class TestDoc(Document):
            x = IntField()
            y = BooleanField()

        TestDoc.drop_collection()
        TestDoc(x=-1, y=True).save()
        TestDoc(x=101, y=True).save()
        TestDoc(x=99, y=False).save()
        TestDoc(x=101, y=False).save()

        q1 = (Q(x__gt=0) & (Q(y=True) | Q(y__exists=False)))
        q2 = (Q(x__lt=100) & (Q(y=False) | Q(y__exists=False)))
        query = (q1 | q2).to_query(TestDoc)

        self.assertEqual(query,
            {'$or': [
                {'$and': [{'x': {'$gt': 0}},
                          {'$or': [{'y': True}, {'y': {'$exists': False}}]}]},
                {'$and': [{'x': {'$lt': 100}},
                          {'$or': [{'y': False}, {'y': {'$exists': False}}]}]}
            ]}
        )

        self.assertEqual(2, TestDoc.objects(q1 | q2).count())

    def test_multiple_occurence_in_field(self):
        class Test(Document):
            name = StringField(max_length=40)
            title = StringField(max_length=40)

        q1 = Q(name__contains='te') | Q(title__contains='te')
        q2 = Q(name__contains='12') | Q(title__contains='12')

        q3 = q1 & q2

        query = q3.to_query(Test)
        self.assertEqual(query["$and"][0], q1.to_query(Test))
        self.assertEqual(query["$and"][1], q2.to_query(Test))

    def test_q_clone(self):

        class TestDoc(Document):
            x = IntField()

        TestDoc.drop_collection()
        for i in xrange(1, 101):
            t = TestDoc(x=i)
            t.save()

        # Check normal cases work without an error
        test = TestDoc.objects(Q(x__lt=7) & Q(x__gt=3))

        self.assertEqual(test.count(), 3)

        test2 = test.clone()
        self.assertEqual(test2.count(), 3)
        self.assertFalse(test2 == test)

        test3 = test2.filter(x=6)
        self.assertEqual(test3.count(), 1)
        self.assertEqual(test.count(), 3)

    def test_q(self):
        """Ensure that Q objects may be used to query for documents.
        """
        class BlogPost(Document):
            title = StringField()
            publish_date = DateTimeField()
            published = BooleanField()

        BlogPost.drop_collection()

        post1 = BlogPost(title='Test 1', publish_date=datetime(2010, 1, 8), published=False)
        post1.save()

        post2 = BlogPost(title='Test 2', publish_date=datetime(2010, 1, 15), published=True)
        post2.save()

        post3 = BlogPost(title='Test 3', published=True)
        post3.save()

        post4 = BlogPost(title='Test 4', publish_date=datetime(2010, 1, 8))
        post4.save()

        post5 = BlogPost(title='Test 1', publish_date=datetime(2010, 1, 15))
        post5.save()

        post6 = BlogPost(title='Test 1', published=False)
        post6.save()

        # Check ObjectId lookup works
        obj = BlogPost.objects(id=post1.id).first()
        self.assertEqual(obj, post1)

        # Check Q object combination with one does not exist
        q = BlogPost.objects(Q(title='Test 5') | Q(published=True))
        posts = [post.id for post in q]

        published_posts = (post2, post3)
        self.assertTrue(all(obj.id in posts for obj in published_posts))

        q = BlogPost.objects(Q(title='Test 1') | Q(published=True))
        posts = [post.id for post in q]
        published_posts = (post1, post2, post3, post5, post6)
        self.assertTrue(all(obj.id in posts for obj in published_posts))

        # Check Q object combination
        date = datetime(2010, 1, 10)
        q = BlogPost.objects(Q(publish_date__lte=date) | Q(published=True))
        posts = [post.id for post in q]

        published_posts = (post1, post2, post3, post4)
        self.assertTrue(all(obj.id in posts for obj in published_posts))

        self.assertFalse(any(obj.id in posts for obj in [post5, post6]))

        BlogPost.drop_collection()

        # Check the 'in' operator
        self.Person(name='user1', age=20).save()
        self.Person(name='user2', age=20).save()
        self.Person(name='user3', age=30).save()
        self.Person(name='user4', age=40).save()

        self.assertEqual(self.Person.objects(Q(age__in=[20])).count(), 2)
        self.assertEqual(self.Person.objects(Q(age__in=[20, 30])).count(), 3)

        # Test invalid query objs
        def wrong_query_objs():
            self.Person.objects('user1')
        def wrong_query_objs_filter():
            self.Person.objects('user1')
        self.assertRaises(InvalidQueryError, wrong_query_objs)
        self.assertRaises(InvalidQueryError, wrong_query_objs_filter)

    def test_q_regex(self):
        """Ensure that Q objects can be queried using regexes.
        """
        person = self.Person(name='Guido van Rossum')
        person.save()

        import re
        obj = self.Person.objects(Q(name=re.compile('^Gui'))).first()
        self.assertEqual(obj, person)
        obj = self.Person.objects(Q(name=re.compile('^gui'))).first()
        self.assertEqual(obj, None)

        obj = self.Person.objects(Q(name=re.compile('^gui', re.I))).first()
        self.assertEqual(obj, person)

        obj = self.Person.objects(Q(name__not=re.compile('^bob'))).first()
        self.assertEqual(obj, person)

        obj = self.Person.objects(Q(name__not=re.compile('^Gui'))).first()
        self.assertEqual(obj, None)

    def test_q_lists(self):
        """Ensure that Q objects query ListFields correctly.
        """
        class BlogPost(Document):
            tags = ListField(StringField())

        BlogPost.drop_collection()

        BlogPost(tags=['python', 'mongo']).save()
        BlogPost(tags=['python']).save()

        self.assertEqual(BlogPost.objects(Q(tags='mongo')).count(), 1)
        self.assertEqual(BlogPost.objects(Q(tags='python')).count(), 2)

        BlogPost.drop_collection()

    def test_q_merge_queries_edge_case(self):

        class User(Document):
            email = EmailField(required=False)
            name = StringField()

        User.drop_collection()
        pk = ObjectId()
        User(email='example@example.com', pk=pk).save()

        self.assertEqual(1, User.objects.filter(Q(email='example@example.com') |
                                                Q(name='John Doe')).limit(2).filter(pk=pk).count())

    def test_chained_q_or_filtering(self):

        class Post(EmbeddedDocument):
            name = StringField(required=True)

        class Item(Document):
            postables = ListField(EmbeddedDocumentField(Post))

        Item.drop_collection()

        Item(postables=[Post(name="a"), Post(name="b")]).save()
        Item(postables=[Post(name="a"), Post(name="c")]).save()
        Item(postables=[Post(name="a"), Post(name="b"), Post(name="c")]).save()

        self.assertEqual(Item.objects(Q(postables__name="a") & Q(postables__name="b")).count(), 2)
        self.assertEqual(Item.objects.filter(postables__name="a").filter(postables__name="b").count(), 2)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_connection
import sys
sys.path[0:0] = [""]
import unittest
import datetime

import pymongo
from bson.tz_util import utc

from mongoengine import *
import mongoengine.connection
from mongoengine.connection import get_db, get_connection, ConnectionError


class ConnectionTest(unittest.TestCase):

    def tearDown(self):
        mongoengine.connection._connection_settings = {}
        mongoengine.connection._connections = {}
        mongoengine.connection._dbs = {}

    def test_connect(self):
        """Ensure that the connect() method works properly.
        """
        connect('mongoenginetest')

        conn = get_connection()
        self.assertTrue(isinstance(conn, pymongo.mongo_client.MongoClient))

        db = get_db()
        self.assertTrue(isinstance(db, pymongo.database.Database))
        self.assertEqual(db.name, 'mongoenginetest')

        connect('mongoenginetest2', alias='testdb')
        conn = get_connection('testdb')
        self.assertTrue(isinstance(conn, pymongo.mongo_client.MongoClient))

    def test_connect_uri(self):
        """Ensure that the connect() method works properly with uri's
        """
        c = connect(db='mongoenginetest', alias='admin')
        c.admin.system.users.remove({})
        c.mongoenginetest.system.users.remove({})

        c.admin.add_user("admin", "password")
        c.admin.authenticate("admin", "password")
        c.mongoenginetest.add_user("username", "password")

        self.assertRaises(ConnectionError, connect, "testdb_uri_bad", host='mongodb://test:password@localhost')

        connect("testdb_uri", host='mongodb://username:password@localhost/mongoenginetest')

        conn = get_connection()
        self.assertTrue(isinstance(conn, pymongo.mongo_client.MongoClient))

        db = get_db()
        self.assertTrue(isinstance(db, pymongo.database.Database))
        self.assertEqual(db.name, 'mongoenginetest')

        c.admin.system.users.remove({})
        c.mongoenginetest.system.users.remove({})

    def test_connect_uri_without_db(self):
        """Ensure that the connect() method works properly with uri's
        without database_name
        """
        c = connect(db='mongoenginetest', alias='admin')
        c.admin.system.users.remove({})
        c.mongoenginetest.system.users.remove({})

        c.admin.add_user("admin", "password")
        c.admin.authenticate("admin", "password")
        c.mongoenginetest.add_user("username", "password")

        self.assertRaises(ConnectionError, connect, "testdb_uri_bad", host='mongodb://test:password@localhost')

        connect("mongoenginetest", host='mongodb://localhost/')

        conn = get_connection()
        self.assertTrue(isinstance(conn, pymongo.mongo_client.MongoClient))

        db = get_db()
        self.assertTrue(isinstance(db, pymongo.database.Database))
        self.assertEqual(db.name, 'mongoenginetest')

        c.admin.system.users.remove({})
        c.mongoenginetest.system.users.remove({})

    def test_register_connection(self):
        """Ensure that connections with different aliases may be registered.
        """
        register_connection('testdb', 'mongoenginetest2')

        self.assertRaises(ConnectionError, get_connection)
        conn = get_connection('testdb')
        self.assertTrue(isinstance(conn, pymongo.mongo_client.MongoClient))

        db = get_db('testdb')
        self.assertTrue(isinstance(db, pymongo.database.Database))
        self.assertEqual(db.name, 'mongoenginetest2')

    def test_register_connection_defaults(self):
        """Ensure that defaults are used when the host and port are None.
        """
        register_connection('testdb', 'mongoenginetest', host=None, port=None)

        conn = get_connection('testdb')
        self.assertTrue(isinstance(conn, pymongo.mongo_client.MongoClient))

    def test_connection_kwargs(self):
        """Ensure that connection kwargs get passed to pymongo.
        """
        connect('mongoenginetest', alias='t1', tz_aware=True)
        conn = get_connection('t1')

        self.assertTrue(conn.tz_aware)

        connect('mongoenginetest2', alias='t2')
        conn = get_connection('t2')
        self.assertFalse(conn.tz_aware)

    def test_datetime(self):
        connect('mongoenginetest', tz_aware=True)
        d = datetime.datetime(2010, 5, 5, tzinfo=utc)

        class DateDoc(Document):
            the_date = DateTimeField(required=True)

        DateDoc.drop_collection()
        DateDoc(the_date=d).save()

        date_doc = DateDoc.objects.first()
        self.assertEqual(d, date_doc.the_date)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_context_managers
import sys
sys.path[0:0] = [""]
import unittest

from mongoengine import *
from mongoengine.connection import get_db
from mongoengine.context_managers import (switch_db, switch_collection,
                                          no_sub_classes, no_dereference,
                                          query_counter)


class ContextManagersTest(unittest.TestCase):

    def test_switch_db_context_manager(self):
        connect('mongoenginetest')
        register_connection('testdb-1', 'mongoenginetest2')

        class Group(Document):
            name = StringField()

        Group.drop_collection()

        Group(name="hello - default").save()
        self.assertEqual(1, Group.objects.count())

        with switch_db(Group, 'testdb-1') as Group:

            self.assertEqual(0, Group.objects.count())

            Group(name="hello").save()

            self.assertEqual(1, Group.objects.count())

            Group.drop_collection()
            self.assertEqual(0, Group.objects.count())

        self.assertEqual(1, Group.objects.count())

    def test_switch_collection_context_manager(self):
        connect('mongoenginetest')
        register_connection('testdb-1', 'mongoenginetest2')

        class Group(Document):
            name = StringField()

        Group.drop_collection()
        with switch_collection(Group, 'group1') as Group:
            Group.drop_collection()

        Group(name="hello - group").save()
        self.assertEqual(1, Group.objects.count())

        with switch_collection(Group, 'group1') as Group:

            self.assertEqual(0, Group.objects.count())

            Group(name="hello - group1").save()

            self.assertEqual(1, Group.objects.count())

            Group.drop_collection()
            self.assertEqual(0, Group.objects.count())

        self.assertEqual(1, Group.objects.count())

    def test_no_dereference_context_manager_object_id(self):
        """Ensure that DBRef items in ListFields aren't dereferenced.
        """
        connect('mongoenginetest')

        class User(Document):
            name = StringField()

        class Group(Document):
            ref = ReferenceField(User, dbref=False)
            generic = GenericReferenceField()
            members = ListField(ReferenceField(User, dbref=False))

        User.drop_collection()
        Group.drop_collection()

        for i in xrange(1, 51):
            User(name='user %s' % i).save()

        user = User.objects.first()
        Group(ref=user, members=User.objects, generic=user).save()

        with no_dereference(Group) as NoDeRefGroup:
            self.assertTrue(Group._fields['members']._auto_dereference)
            self.assertFalse(NoDeRefGroup._fields['members']._auto_dereference)

        with no_dereference(Group) as Group:
            group = Group.objects.first()
            self.assertTrue(all([not isinstance(m, User)
                                for m in group.members]))
            self.assertFalse(isinstance(group.ref, User))
            self.assertFalse(isinstance(group.generic, User))

        self.assertTrue(all([isinstance(m, User)
                             for m in group.members]))
        self.assertTrue(isinstance(group.ref, User))
        self.assertTrue(isinstance(group.generic, User))

    def test_no_dereference_context_manager_dbref(self):
        """Ensure that DBRef items in ListFields aren't dereferenced.
        """
        connect('mongoenginetest')

        class User(Document):
            name = StringField()

        class Group(Document):
            ref = ReferenceField(User, dbref=True)
            generic = GenericReferenceField()
            members = ListField(ReferenceField(User, dbref=True))

        User.drop_collection()
        Group.drop_collection()

        for i in xrange(1, 51):
            User(name='user %s' % i).save()

        user = User.objects.first()
        Group(ref=user, members=User.objects, generic=user).save()

        with no_dereference(Group) as NoDeRefGroup:
            self.assertTrue(Group._fields['members']._auto_dereference)
            self.assertFalse(NoDeRefGroup._fields['members']._auto_dereference)

        with no_dereference(Group) as Group:
            group = Group.objects.first()
            self.assertTrue(all([not isinstance(m, User)
                                for m in group.members]))
            self.assertFalse(isinstance(group.ref, User))
            self.assertFalse(isinstance(group.generic, User))

        self.assertTrue(all([isinstance(m, User)
                             for m in group.members]))
        self.assertTrue(isinstance(group.ref, User))
        self.assertTrue(isinstance(group.generic, User))

    def test_no_sub_classes(self):
        class A(Document):
            x = IntField()
            y = IntField()

            meta = {'allow_inheritance': True}

        class B(A):
            z = IntField()

        class C(B):
            zz = IntField()

        A.drop_collection()

        A(x=10, y=20).save()
        A(x=15, y=30).save()
        B(x=20, y=40).save()
        B(x=30, y=50).save()
        C(x=40, y=60).save()

        self.assertEqual(A.objects.count(), 5)
        self.assertEqual(B.objects.count(), 3)
        self.assertEqual(C.objects.count(), 1)

        with no_sub_classes(A) as A:
            self.assertEqual(A.objects.count(), 2)

            for obj in A.objects:
                self.assertEqual(obj.__class__, A)

        with no_sub_classes(B) as B:
            self.assertEqual(B.objects.count(), 2)

            for obj in B.objects:
                self.assertEqual(obj.__class__, B)

        with no_sub_classes(C) as C:
            self.assertEqual(C.objects.count(), 1)

            for obj in C.objects:
                self.assertEqual(obj.__class__, C)

        # Confirm context manager exit correctly
        self.assertEqual(A.objects.count(), 5)
        self.assertEqual(B.objects.count(), 3)
        self.assertEqual(C.objects.count(), 1)

    def test_query_counter(self):
        connect('mongoenginetest')
        db = get_db()
        db.test.find({})

        with query_counter() as q:
            self.assertEqual(0, q)

            for i in xrange(1, 51):
                db.test.find({}).count()

            self.assertEqual(50, q)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_dereference
# -*- coding: utf-8 -*-
import sys
sys.path[0:0] = [""]
import unittest

from bson import DBRef, ObjectId

from mongoengine import *
from mongoengine.connection import get_db
from mongoengine.context_managers import query_counter


class FieldTest(unittest.TestCase):

    def setUp(self):
        connect(db='mongoenginetest')
        self.db = get_db()

    def test_list_item_dereference(self):
        """Ensure that DBRef items in ListFields are dereferenced.
        """
        class User(Document):
            name = StringField()

        class Group(Document):
            members = ListField(ReferenceField(User))

        User.drop_collection()
        Group.drop_collection()

        for i in xrange(1, 51):
            user = User(name='user %s' % i)
            user.save()

        group = Group(members=User.objects)
        group.save()

        group = Group(members=User.objects)
        group.save()

        with query_counter() as q:
            self.assertEqual(q, 0)

            group_obj = Group.objects.first()
            self.assertEqual(q, 1)

            len(group_obj._data['members'])
            self.assertEqual(q, 1)

            len(group_obj.members)
            self.assertEqual(q, 2)

            [m for m in group_obj.members]
            self.assertEqual(q, 2)

        # Document select_related
        with query_counter() as q:
            self.assertEqual(q, 0)

            group_obj = Group.objects.first().select_related()
            self.assertEqual(q, 2)
            [m for m in group_obj.members]
            self.assertEqual(q, 2)

        # Queryset select_related
        with query_counter() as q:
            self.assertEqual(q, 0)
            group_objs = Group.objects.select_related()
            self.assertEqual(q, 2)
            for group_obj in group_objs:
                [m for m in group_obj.members]
                self.assertEqual(q, 2)

        User.drop_collection()
        Group.drop_collection()

    def test_list_item_dereference_dref_false(self):
        """Ensure that DBRef items in ListFields are dereferenced.
        """
        class User(Document):
            name = StringField()

        class Group(Document):
            members = ListField(ReferenceField(User, dbref=False))

        User.drop_collection()
        Group.drop_collection()

        for i in xrange(1, 51):
            user = User(name='user %s' % i)
            user.save()

        group = Group(members=User.objects)
        group.save()
        group.reload()  # Confirm reload works

        with query_counter() as q:
            self.assertEqual(q, 0)

            group_obj = Group.objects.first()
            self.assertEqual(q, 1)

            [m for m in group_obj.members]
            self.assertEqual(q, 2)

        # Document select_related
        with query_counter() as q:
            self.assertEqual(q, 0)

            group_obj = Group.objects.first().select_related()

            self.assertEqual(q, 2)
            [m for m in group_obj.members]
            self.assertEqual(q, 2)

        # Queryset select_related
        with query_counter() as q:
            self.assertEqual(q, 0)
            group_objs = Group.objects.select_related()
            self.assertEqual(q, 2)
            for group_obj in group_objs:
                [m for m in group_obj.members]
                self.assertEqual(q, 2)

        User.drop_collection()
        Group.drop_collection()

    def test_list_item_dereference_dref_false_stores_as_type(self):
        """Ensure that DBRef items are stored as their type
        """
        class User(Document):
            my_id = IntField(primary_key=True)
            name = StringField()

        class Group(Document):
            members = ListField(ReferenceField(User, dbref=False))

        User.drop_collection()
        Group.drop_collection()

        user = User(my_id=1, name='user 1').save()

        Group(members=User.objects).save()
        group = Group.objects.first()

        self.assertEqual(Group._get_collection().find_one()['members'], [1])
        self.assertEqual(group.members, [user])

    def test_handle_old_style_references(self):
        """Ensure that DBRef items in ListFields are dereferenced.
        """
        class User(Document):
            name = StringField()

        class Group(Document):
            members = ListField(ReferenceField(User, dbref=True))

        User.drop_collection()
        Group.drop_collection()

        for i in xrange(1, 26):
            user = User(name='user %s' % i)
            user.save()

        group = Group(members=User.objects)
        group.save()

        group = Group._get_collection().find_one()

        # Update the model to change the reference
        class Group(Document):
            members = ListField(ReferenceField(User, dbref=False))

        group = Group.objects.first()
        group.members.append(User(name="String!").save())
        group.save()

        group = Group.objects.first()
        self.assertEqual(group.members[0].name, 'user 1')
        self.assertEqual(group.members[-1].name, 'String!')

    def test_migrate_references(self):
        """Example of migrating ReferenceField storage
        """

        # Create some sample data
        class User(Document):
            name = StringField()

        class Group(Document):
            author = ReferenceField(User, dbref=True)
            members = ListField(ReferenceField(User, dbref=True))

        User.drop_collection()
        Group.drop_collection()

        user = User(name="Ross").save()
        group = Group(author=user, members=[user]).save()

        raw_data = Group._get_collection().find_one()
        self.assertTrue(isinstance(raw_data['author'], DBRef))
        self.assertTrue(isinstance(raw_data['members'][0], DBRef))
        group = Group.objects.first()

        self.assertEqual(group.author, user)
        self.assertEqual(group.members, [user])

        # Migrate the model definition
        class Group(Document):
            author = ReferenceField(User, dbref=False)
            members = ListField(ReferenceField(User, dbref=False))

        # Migrate the data
        for g in Group.objects():
            # Explicitly mark as changed so resets
            g._mark_as_changed('author')
            g._mark_as_changed('members')
            g.save()

        group = Group.objects.first()
        self.assertEqual(group.author, user)
        self.assertEqual(group.members, [user])

        raw_data = Group._get_collection().find_one()
        self.assertTrue(isinstance(raw_data['author'], ObjectId))
        self.assertTrue(isinstance(raw_data['members'][0], ObjectId))

    def test_recursive_reference(self):
        """Ensure that ReferenceFields can reference their own documents.
        """
        class Employee(Document):
            name = StringField()
            boss = ReferenceField('self')
            friends = ListField(ReferenceField('self'))

        Employee.drop_collection()

        bill = Employee(name='Bill Lumbergh')
        bill.save()

        michael = Employee(name='Michael Bolton')
        michael.save()

        samir = Employee(name='Samir Nagheenanajar')
        samir.save()

        friends = [michael, samir]
        peter = Employee(name='Peter Gibbons', boss=bill, friends=friends)
        peter.save()

        Employee(name='Funky Gibbon', boss=bill, friends=friends).save()
        Employee(name='Funky Gibbon', boss=bill, friends=friends).save()
        Employee(name='Funky Gibbon', boss=bill, friends=friends).save()

        with query_counter() as q:
            self.assertEqual(q, 0)

            peter = Employee.objects.with_id(peter.id)
            self.assertEqual(q, 1)

            peter.boss
            self.assertEqual(q, 2)

            peter.friends
            self.assertEqual(q, 3)

        # Document select_related
        with query_counter() as q:
            self.assertEqual(q, 0)

            peter = Employee.objects.with_id(peter.id).select_related()
            self.assertEqual(q, 2)

            self.assertEqual(peter.boss, bill)
            self.assertEqual(q, 2)

            self.assertEqual(peter.friends, friends)
            self.assertEqual(q, 2)

        # Queryset select_related
        with query_counter() as q:
            self.assertEqual(q, 0)

            employees = Employee.objects(boss=bill).select_related()
            self.assertEqual(q, 2)

            for employee in employees:
                self.assertEqual(employee.boss, bill)
                self.assertEqual(q, 2)

                self.assertEqual(employee.friends, friends)
                self.assertEqual(q, 2)

    def test_circular_reference(self):
        """Ensure you can handle circular references
        """
        class Person(Document):
            name = StringField()
            relations = ListField(EmbeddedDocumentField('Relation'))

            def __repr__(self):
                return "<Person: %s>" % self.name

        class Relation(EmbeddedDocument):
            name = StringField()
            person = ReferenceField('Person')

        Person.drop_collection()
        mother = Person(name="Mother")
        daughter = Person(name="Daughter")

        mother.save()
        daughter.save()

        daughter_rel = Relation(name="Daughter", person=daughter)
        mother.relations.append(daughter_rel)
        mother.save()

        mother_rel = Relation(name="Daughter", person=mother)
        self_rel = Relation(name="Self", person=daughter)
        daughter.relations.append(mother_rel)
        daughter.relations.append(self_rel)
        daughter.save()

        self.assertEqual("[<Person: Mother>, <Person: Daughter>]", "%s" % Person.objects())

    def test_circular_reference_on_self(self):
        """Ensure you can handle circular references
        """
        class Person(Document):
            name = StringField()
            relations = ListField(ReferenceField('self'))

            def __repr__(self):
                return "<Person: %s>" % self.name

        Person.drop_collection()
        mother = Person(name="Mother")
        daughter = Person(name="Daughter")

        mother.save()
        daughter.save()

        mother.relations.append(daughter)
        mother.save()

        daughter.relations.append(mother)
        daughter.relations.append(daughter)
        daughter.save()

        self.assertEqual("[<Person: Mother>, <Person: Daughter>]", "%s" % Person.objects())

    def test_circular_tree_reference(self):
        """Ensure you can handle circular references with more than one level
        """
        class Other(EmbeddedDocument):
            name = StringField()
            friends = ListField(ReferenceField('Person'))

        class Person(Document):
            name = StringField()
            other = EmbeddedDocumentField(Other, default=lambda: Other())

            def __repr__(self):
                return "<Person: %s>" % self.name

        Person.drop_collection()
        paul = Person(name="Paul").save()
        maria = Person(name="Maria").save()
        julia = Person(name='Julia').save()
        anna = Person(name='Anna').save()

        paul.other.friends = [maria, julia, anna]
        paul.other.name = "Paul's friends"
        paul.save()

        maria.other.friends = [paul, julia, anna]
        maria.other.name = "Maria's friends"
        maria.save()

        julia.other.friends = [paul, maria, anna]
        julia.other.name = "Julia's friends"
        julia.save()

        anna.other.friends = [paul, maria, julia]
        anna.other.name = "Anna's friends"
        anna.save()

        self.assertEqual(
            "[<Person: Paul>, <Person: Maria>, <Person: Julia>, <Person: Anna>]",
            "%s" % Person.objects()
        )

    def test_generic_reference(self):

        class UserA(Document):
            name = StringField()

        class UserB(Document):
            name = StringField()

        class UserC(Document):
            name = StringField()

        class Group(Document):
            members = ListField(GenericReferenceField())

        UserA.drop_collection()
        UserB.drop_collection()
        UserC.drop_collection()
        Group.drop_collection()

        members = []
        for i in xrange(1, 51):
            a = UserA(name='User A %s' % i)
            a.save()

            b = UserB(name='User B %s' % i)
            b.save()

            c = UserC(name='User C %s' % i)
            c.save()

            members += [a, b, c]

        group = Group(members=members)
        group.save()

        group = Group(members=members)
        group.save()

        with query_counter() as q:
            self.assertEqual(q, 0)

            group_obj = Group.objects.first()
            self.assertEqual(q, 1)

            [m for m in group_obj.members]
            self.assertEqual(q, 4)

            [m for m in group_obj.members]
            self.assertEqual(q, 4)

            for m in group_obj.members:
                self.assertTrue('User' in m.__class__.__name__)

        # Document select_related
        with query_counter() as q:
            self.assertEqual(q, 0)

            group_obj = Group.objects.first().select_related()
            self.assertEqual(q, 4)

            [m for m in group_obj.members]
            self.assertEqual(q, 4)

            [m for m in group_obj.members]
            self.assertEqual(q, 4)

            for m in group_obj.members:
                self.assertTrue('User' in m.__class__.__name__)

        # Queryset select_related
        with query_counter() as q:
            self.assertEqual(q, 0)

            group_objs = Group.objects.select_related()
            self.assertEqual(q, 4)

            for group_obj in group_objs:
                [m for m in group_obj.members]
                self.assertEqual(q, 4)

                [m for m in group_obj.members]
                self.assertEqual(q, 4)

                for m in group_obj.members:
                    self.assertTrue('User' in m.__class__.__name__)

        UserA.drop_collection()
        UserB.drop_collection()
        UserC.drop_collection()
        Group.drop_collection()

    def test_list_field_complex(self):

        class UserA(Document):
            name = StringField()

        class UserB(Document):
            name = StringField()

        class UserC(Document):
            name = StringField()

        class Group(Document):
            members = ListField()

        UserA.drop_collection()
        UserB.drop_collection()
        UserC.drop_collection()
        Group.drop_collection()

        members = []
        for i in xrange(1, 51):
            a = UserA(name='User A %s' % i)
            a.save()

            b = UserB(name='User B %s' % i)
            b.save()

            c = UserC(name='User C %s' % i)
            c.save()

            members += [a, b, c]

        group = Group(members=members)
        group.save()

        group = Group(members=members)
        group.save()

        with query_counter() as q:
            self.assertEqual(q, 0)

            group_obj = Group.objects.first()
            self.assertEqual(q, 1)

            [m for m in group_obj.members]
            self.assertEqual(q, 4)

            [m for m in group_obj.members]
            self.assertEqual(q, 4)

            for m in group_obj.members:
                self.assertTrue('User' in m.__class__.__name__)

        # Document select_related
        with query_counter() as q:
            self.assertEqual(q, 0)

            group_obj = Group.objects.first().select_related()
            self.assertEqual(q, 4)

            [m for m in group_obj.members]
            self.assertEqual(q, 4)

            [m for m in group_obj.members]
            self.assertEqual(q, 4)

            for m in group_obj.members:
                self.assertTrue('User' in m.__class__.__name__)

        # Queryset select_related
        with query_counter() as q:
            self.assertEqual(q, 0)

            group_objs = Group.objects.select_related()
            self.assertEqual(q, 4)

            for group_obj in group_objs:
                [m for m in group_obj.members]
                self.assertEqual(q, 4)

                [m for m in group_obj.members]
                self.assertEqual(q, 4)

                for m in group_obj.members:
                    self.assertTrue('User' in m.__class__.__name__)

        UserA.drop_collection()
        UserB.drop_collection()
        UserC.drop_collection()
        Group.drop_collection()

    def test_map_field_reference(self):

        class User(Document):
            name = StringField()

        class Group(Document):
            members = MapField(ReferenceField(User))

        User.drop_collection()
        Group.drop_collection()

        members = []
        for i in xrange(1, 51):
            user = User(name='user %s' % i)
            user.save()
            members.append(user)

        group = Group(members=dict([(str(u.id), u) for u in members]))
        group.save()

        group = Group(members=dict([(str(u.id), u) for u in members]))
        group.save()

        with query_counter() as q:
            self.assertEqual(q, 0)

            group_obj = Group.objects.first()
            self.assertEqual(q, 1)

            [m for m in group_obj.members]
            self.assertEqual(q, 2)

            for k, m in group_obj.members.iteritems():
                self.assertTrue(isinstance(m, User))

        # Document select_related
        with query_counter() as q:
            self.assertEqual(q, 0)

            group_obj = Group.objects.first().select_related()
            self.assertEqual(q, 2)

            [m for m in group_obj.members]
            self.assertEqual(q, 2)

            for k, m in group_obj.members.iteritems():
                self.assertTrue(isinstance(m, User))

       # Queryset select_related
        with query_counter() as q:
            self.assertEqual(q, 0)

            group_objs = Group.objects.select_related()
            self.assertEqual(q, 2)

            for group_obj in group_objs:
                [m for m in group_obj.members]
                self.assertEqual(q, 2)

                for k, m in group_obj.members.iteritems():
                    self.assertTrue(isinstance(m, User))

        User.drop_collection()
        Group.drop_collection()

    def test_dict_field(self):

        class UserA(Document):
            name = StringField()

        class UserB(Document):
            name = StringField()

        class UserC(Document):
            name = StringField()

        class Group(Document):
            members = DictField()

        UserA.drop_collection()
        UserB.drop_collection()
        UserC.drop_collection()
        Group.drop_collection()

        members = []
        for i in xrange(1, 51):
            a = UserA(name='User A %s' % i)
            a.save()

            b = UserB(name='User B %s' % i)
            b.save()

            c = UserC(name='User C %s' % i)
            c.save()

            members += [a, b, c]

        group = Group(members=dict([(str(u.id), u) for u in members]))
        group.save()
        group = Group(members=dict([(str(u.id), u) for u in members]))
        group.save()

        with query_counter() as q:
            self.assertEqual(q, 0)

            group_obj = Group.objects.first()
            self.assertEqual(q, 1)

            [m for m in group_obj.members]
            self.assertEqual(q, 4)

            [m for m in group_obj.members]
            self.assertEqual(q, 4)

            for k, m in group_obj.members.iteritems():
                self.assertTrue('User' in m.__class__.__name__)

        # Document select_related
        with query_counter() as q:
            self.assertEqual(q, 0)

            group_obj = Group.objects.first().select_related()
            self.assertEqual(q, 4)

            [m for m in group_obj.members]
            self.assertEqual(q, 4)

            [m for m in group_obj.members]
            self.assertEqual(q, 4)

            for k, m in group_obj.members.iteritems():
                self.assertTrue('User' in m.__class__.__name__)

        # Queryset select_related
        with query_counter() as q:
            self.assertEqual(q, 0)

            group_objs = Group.objects.select_related()
            self.assertEqual(q, 4)

            for group_obj in group_objs:
                [m for m in group_obj.members]
                self.assertEqual(q, 4)

                [m for m in group_obj.members]
                self.assertEqual(q, 4)

                for k, m in group_obj.members.iteritems():
                    self.assertTrue('User' in m.__class__.__name__)

        Group.objects.delete()
        Group().save()

        with query_counter() as q:
            self.assertEqual(q, 0)

            group_obj = Group.objects.first()
            self.assertEqual(q, 1)

            [m for m in group_obj.members]
            self.assertEqual(q, 1)
            self.assertEqual(group_obj.members, {})

        UserA.drop_collection()
        UserB.drop_collection()
        UserC.drop_collection()
        Group.drop_collection()

    def test_dict_field_no_field_inheritance(self):

        class UserA(Document):
            name = StringField()
            meta = {'allow_inheritance': False}

        class Group(Document):
            members = DictField()

        UserA.drop_collection()
        Group.drop_collection()

        members = []
        for i in xrange(1, 51):
            a = UserA(name='User A %s' % i)
            a.save()

            members += [a]

        group = Group(members=dict([(str(u.id), u) for u in members]))
        group.save()

        group = Group(members=dict([(str(u.id), u) for u in members]))
        group.save()

        with query_counter() as q:
            self.assertEqual(q, 0)

            group_obj = Group.objects.first()
            self.assertEqual(q, 1)

            [m for m in group_obj.members]
            self.assertEqual(q, 2)

            [m for m in group_obj.members]
            self.assertEqual(q, 2)

            for k, m in group_obj.members.iteritems():
                self.assertTrue(isinstance(m, UserA))

        # Document select_related
        with query_counter() as q:
            self.assertEqual(q, 0)

            group_obj = Group.objects.first().select_related()
            self.assertEqual(q, 2)

            [m for m in group_obj.members]
            self.assertEqual(q, 2)

            [m for m in group_obj.members]
            self.assertEqual(q, 2)

            for k, m in group_obj.members.iteritems():
                self.assertTrue(isinstance(m, UserA))

        # Queryset select_related
        with query_counter() as q:
            self.assertEqual(q, 0)

            group_objs = Group.objects.select_related()
            self.assertEqual(q, 2)

            for group_obj in group_objs:
                [m for m in group_obj.members]
                self.assertEqual(q, 2)

                [m for m in group_obj.members]
                self.assertEqual(q, 2)

                for k, m in group_obj.members.iteritems():
                    self.assertTrue(isinstance(m, UserA))

        UserA.drop_collection()
        Group.drop_collection()

    def test_generic_reference_map_field(self):

        class UserA(Document):
            name = StringField()

        class UserB(Document):
            name = StringField()

        class UserC(Document):
            name = StringField()

        class Group(Document):
            members = MapField(GenericReferenceField())

        UserA.drop_collection()
        UserB.drop_collection()
        UserC.drop_collection()
        Group.drop_collection()

        members = []
        for i in xrange(1, 51):
            a = UserA(name='User A %s' % i)
            a.save()

            b = UserB(name='User B %s' % i)
            b.save()

            c = UserC(name='User C %s' % i)
            c.save()

            members += [a, b, c]

        group = Group(members=dict([(str(u.id), u) for u in members]))
        group.save()
        group = Group(members=dict([(str(u.id), u) for u in members]))
        group.save()

        with query_counter() as q:
            self.assertEqual(q, 0)

            group_obj = Group.objects.first()
            self.assertEqual(q, 1)

            [m for m in group_obj.members]
            self.assertEqual(q, 4)

            [m for m in group_obj.members]
            self.assertEqual(q, 4)

            for k, m in group_obj.members.iteritems():
                self.assertTrue('User' in m.__class__.__name__)

        # Document select_related
        with query_counter() as q:
            self.assertEqual(q, 0)

            group_obj = Group.objects.first().select_related()
            self.assertEqual(q, 4)

            [m for m in group_obj.members]
            self.assertEqual(q, 4)

            [m for m in group_obj.members]
            self.assertEqual(q, 4)

            for k, m in group_obj.members.iteritems():
                self.assertTrue('User' in m.__class__.__name__)

        # Queryset select_related
        with query_counter() as q:
            self.assertEqual(q, 0)

            group_objs = Group.objects.select_related()
            self.assertEqual(q, 4)

            for group_obj in group_objs:
                [m for m in group_obj.members]
                self.assertEqual(q, 4)

                [m for m in group_obj.members]
                self.assertEqual(q, 4)

                for k, m in group_obj.members.iteritems():
                    self.assertTrue('User' in m.__class__.__name__)

        Group.objects.delete()
        Group().save()

        with query_counter() as q:
            self.assertEqual(q, 0)

            group_obj = Group.objects.first()
            self.assertEqual(q, 1)

            [m for m in group_obj.members]
            self.assertEqual(q, 1)

        UserA.drop_collection()
        UserB.drop_collection()
        UserC.drop_collection()
        Group.drop_collection()

    def test_multidirectional_lists(self):

        class Asset(Document):
            name = StringField(max_length=250, required=True)
            parent = GenericReferenceField(default=None)
            parents = ListField(GenericReferenceField())
            children = ListField(GenericReferenceField())

        Asset.drop_collection()

        root = Asset(name='', path="/", title="Site Root")
        root.save()

        company = Asset(name='company', title='Company', parent=root, parents=[root])
        company.save()

        root.children = [company]
        root.save()

        root = root.reload()
        self.assertEqual(root.children, [company])
        self.assertEqual(company.parents, [root])

    def test_dict_in_dbref_instance(self):

        class Person(Document):
            name = StringField(max_length=250, required=True)

        class Room(Document):
            number = StringField(max_length=250, required=True)
            staffs_with_position = ListField(DictField())

        Person.drop_collection()
        Room.drop_collection()

        bob = Person.objects.create(name='Bob')
        bob.save()
        sarah = Person.objects.create(name='Sarah')
        sarah.save()

        room_101 = Room.objects.create(number="101")
        room_101.staffs_with_position = [
            {'position_key': 'window', 'staff': sarah},
            {'position_key': 'door', 'staff': bob.to_dbref()}]
        room_101.save()

        room = Room.objects.first().select_related()
        self.assertEqual(room.staffs_with_position[0]['staff'], sarah)
        self.assertEqual(room.staffs_with_position[1]['staff'], bob)

    def test_document_reload_no_inheritance(self):
        class Foo(Document):
            meta = {'allow_inheritance': False}
            bar = ReferenceField('Bar')
            baz = ReferenceField('Baz')

        class Bar(Document):
            meta = {'allow_inheritance': False}
            msg = StringField(required=True, default='Blammo!')

        class Baz(Document):
            meta = {'allow_inheritance': False}
            msg = StringField(required=True, default='Kaboom!')

        Foo.drop_collection()
        Bar.drop_collection()
        Baz.drop_collection()

        bar = Bar()
        bar.save()
        baz = Baz()
        baz.save()
        foo = Foo()
        foo.bar = bar
        foo.baz = baz
        foo.save()
        foo.reload()

        self.assertEqual(type(foo.bar), Bar)
        self.assertEqual(type(foo.baz), Baz)

    def test_list_lookup_not_checked_in_map(self):
        """Ensure we dereference list data correctly
        """
        class Comment(Document):
            id = IntField(primary_key=True)
            text = StringField()

        class Message(Document):
            id = IntField(primary_key=True)
            comments = ListField(ReferenceField(Comment))

        Comment.drop_collection()
        Message.drop_collection()

        c1 = Comment(id=0, text='zero').save()
        c2 = Comment(id=1, text='one').save()
        Message(id=1, comments=[c1, c2]).save()

        msg = Message.objects.get(id=1)
        self.assertEqual(0, msg.comments[0].id)
        self.assertEqual(1, msg.comments[1].id)

    def test_list_item_dereference_dref_false_save_doesnt_cause_extra_queries(self):
        """Ensure that DBRef items in ListFields are dereferenced.
        """
        class User(Document):
            name = StringField()

        class Group(Document):
            name = StringField()
            members = ListField(ReferenceField(User, dbref=False))

        User.drop_collection()
        Group.drop_collection()

        for i in xrange(1, 51):
            User(name='user %s' % i).save()

        Group(name="Test", members=User.objects).save()

        with query_counter() as q:
            self.assertEqual(q, 0)

            group_obj = Group.objects.first()
            self.assertEqual(q, 1)

            group_obj.name = "new test"
            group_obj.save()

            self.assertEqual(q, 2)

    def test_list_item_dereference_dref_true_save_doesnt_cause_extra_queries(self):
        """Ensure that DBRef items in ListFields are dereferenced.
        """
        class User(Document):
            name = StringField()

        class Group(Document):
            name = StringField()
            members = ListField(ReferenceField(User, dbref=True))

        User.drop_collection()
        Group.drop_collection()

        for i in xrange(1, 51):
            User(name='user %s' % i).save()

        Group(name="Test", members=User.objects).save()

        with query_counter() as q:
            self.assertEqual(q, 0)

            group_obj = Group.objects.first()
            self.assertEqual(q, 1)

            group_obj.name = "new test"
            group_obj.save()

            self.assertEqual(q, 2)

    def test_generic_reference_save_doesnt_cause_extra_queries(self):

        class UserA(Document):
            name = StringField()

        class UserB(Document):
            name = StringField()

        class UserC(Document):
            name = StringField()

        class Group(Document):
            name = StringField()
            members = ListField(GenericReferenceField())

        UserA.drop_collection()
        UserB.drop_collection()
        UserC.drop_collection()
        Group.drop_collection()

        members = []
        for i in xrange(1, 51):
            a = UserA(name='User A %s' % i).save()
            b = UserB(name='User B %s' % i).save()
            c = UserC(name='User C %s' % i).save()

            members += [a, b, c]

        Group(name="test", members=members).save()

        with query_counter() as q:
            self.assertEqual(q, 0)

            group_obj = Group.objects.first()
            self.assertEqual(q, 1)

            group_obj.name = "new test"
            group_obj.save()

            self.assertEqual(q, 2)

    def test_objectid_reference_across_databases(self):
        # mongoenginetest - Is default connection alias from setUp()
        # Register Aliases
        register_connection('testdb-1', 'mongoenginetest2')

        class User(Document):
            name = StringField()
            meta = {"db_alias": "testdb-1"}

        class Book(Document):
            name = StringField()
            author = ReferenceField(User)

        # Drops
        User.drop_collection()
        Book.drop_collection()

        user = User(name="Ross").save()
        Book(name="MongoEngine for pros", author=user).save()

        # Can't use query_counter across databases - so test the _data object
        book = Book.objects.first()
        self.assertFalse(isinstance(book._data['author'], User))

        book.select_related()
        self.assertTrue(isinstance(book._data['author'], User))

    def test_non_ascii_pk(self):
        """
        Ensure that dbref conversion to string does not fail when
        non-ascii characters are used in primary key
        """
        class Brand(Document):
            title = StringField(max_length=255, primary_key=True)

        class BrandGroup(Document):
            title = StringField(max_length=255, primary_key=True)
            brands = ListField(ReferenceField("Brand", dbref=True))

        Brand.drop_collection()
        BrandGroup.drop_collection()

        brand1 = Brand(title="Moschino").save()
        brand2 = Brand(title=u"Денис Симачёв").save()

        BrandGroup(title="top_brands", brands=[brand1, brand2]).save()
        brand_groups = BrandGroup.objects().all()

        self.assertEqual(2, len([brand for bg in brand_groups for brand in bg.brands]))

    def test_dereferencing_embedded_listfield_referencefield(self):
        class Tag(Document):
            meta = {'collection': 'tags'}
            name = StringField()

        class Post(EmbeddedDocument):
            body = StringField()
            tags = ListField(ReferenceField("Tag", dbref=True))

        class Page(Document):
            meta = {'collection': 'pages'}
            tags = ListField(ReferenceField("Tag", dbref=True))
            posts = ListField(EmbeddedDocumentField(Post))

        Tag.drop_collection()
        Page.drop_collection()

        tag = Tag(name='test').save()
        post = Post(body='test body', tags=[tag])
        Page(tags=[tag], posts=[post]).save()

        page = Page.objects.first()
        self.assertEqual(page.tags[0], page.posts[0].tags[0])

if __name__ == '__main__':
    unittest.main()


########NEW FILE########
__FILENAME__ = test_django
import sys
sys.path[0:0] = [""]
import unittest
from nose.plugins.skip import SkipTest
from mongoengine import *


from mongoengine.django.shortcuts import get_document_or_404

from django.http import Http404
from django.template import Context, Template
from django.conf import settings
from django.core.paginator import Paginator

settings.configure(
    USE_TZ=True,
    INSTALLED_APPS=('django.contrib.auth', 'mongoengine.django.mongo_auth'),
    AUTH_USER_MODEL=('mongo_auth.MongoUser'),
    AUTHENTICATION_BACKENDS = ('mongoengine.django.auth.MongoEngineBackend',)
)

try:
    from django.contrib.auth import authenticate, get_user_model
    from mongoengine.django.auth import User
    from mongoengine.django.mongo_auth.models import (
        MongoUser,
        MongoUserManager,
        get_user_document,
    )
    DJ15 = True
except Exception:
    DJ15 = False
from django.contrib.sessions.tests import SessionTestsMixin
from mongoengine.django.sessions import SessionStore, MongoSession
from datetime import tzinfo, timedelta
ZERO = timedelta(0)


class FixedOffset(tzinfo):
    """Fixed offset in minutes east from UTC."""

    def __init__(self, offset, name):
        self.__offset = timedelta(minutes=offset)
        self.__name = name

    def utcoffset(self, dt):
        return self.__offset

    def tzname(self, dt):
        return self.__name

    def dst(self, dt):
        return ZERO


def activate_timezone(tz):
    """Activate Django timezone support if it is available.
    """
    try:
        from django.utils import timezone
        timezone.deactivate()
        timezone.activate(tz)
    except ImportError:
        pass


class QuerySetTest(unittest.TestCase):

    def setUp(self):
        connect(db='mongoenginetest')

        class Person(Document):
            name = StringField()
            age = IntField()
        self.Person = Person

    def test_order_by_in_django_template(self):
        """Ensure that QuerySets are properly ordered in Django template.
        """
        self.Person.drop_collection()

        self.Person(name="A", age=20).save()
        self.Person(name="D", age=10).save()
        self.Person(name="B", age=40).save()
        self.Person(name="C", age=30).save()

        t = Template("{% for o in ol %}{{ o.name }}-{{ o.age }}:{% endfor %}")

        d = {"ol": self.Person.objects.order_by('-name')}
        self.assertEqual(t.render(Context(d)), u'D-10:C-30:B-40:A-20:')
        d = {"ol": self.Person.objects.order_by('+name')}
        self.assertEqual(t.render(Context(d)), u'A-20:B-40:C-30:D-10:')
        d = {"ol": self.Person.objects.order_by('-age')}
        self.assertEqual(t.render(Context(d)), u'B-40:C-30:A-20:D-10:')
        d = {"ol": self.Person.objects.order_by('+age')}
        self.assertEqual(t.render(Context(d)), u'D-10:A-20:C-30:B-40:')

        self.Person.drop_collection()

    def test_q_object_filter_in_template(self):

        self.Person.drop_collection()

        self.Person(name="A", age=20).save()
        self.Person(name="D", age=10).save()
        self.Person(name="B", age=40).save()
        self.Person(name="C", age=30).save()

        t = Template("{% for o in ol %}{{ o.name }}-{{ o.age }}:{% endfor %}")

        d = {"ol": self.Person.objects.filter(Q(age=10) | Q(name="C"))}
        self.assertEqual(t.render(Context(d)), 'D-10:C-30:')

        # Check double rendering doesn't throw an error
        self.assertEqual(t.render(Context(d)), 'D-10:C-30:')

    def test_get_document_or_404(self):
        p = self.Person(name="G404")
        p.save()

        self.assertRaises(Http404, get_document_or_404, self.Person, pk='1234')
        self.assertEqual(p, get_document_or_404(self.Person, pk=p.pk))

    def test_pagination(self):
        """Ensure that Pagination works as expected
        """
        class Page(Document):
            name = StringField()

        Page.drop_collection()

        for i in xrange(1, 11):
            Page(name=str(i)).save()

        paginator = Paginator(Page.objects.all(), 2)

        t = Template("{% for i in page.object_list  %}{{ i.name }}:{% endfor %}")
        for p in paginator.page_range:
            d = {"page": paginator.page(p)}
            end = p * 2
            start = end - 1
            self.assertEqual(t.render(Context(d)), u'%d:%d:' % (start, end))

    def test_nested_queryset_template_iterator(self):
        # Try iterating the same queryset twice, nested, in a Django template.
        names = ['A', 'B', 'C', 'D']

        class CustomUser(Document):
            name = StringField()

            def __unicode__(self):
                return self.name

        CustomUser.drop_collection()

        for name in names:
            CustomUser(name=name).save()

        users = CustomUser.objects.all().order_by('name')
        template = Template("{% for user in users %}{{ user.name }}{% ifequal forloop.counter 2 %} {% for inner_user in users %}{{ inner_user.name }}{% endfor %} {% endifequal %}{% endfor %}")
        rendered = template.render(Context({'users': users}))
        self.assertEqual(rendered, 'AB ABCD CD')

    def test_filter(self):
        """Ensure that a queryset and filters work as expected
        """

        class Note(Document):
            text = StringField()

        Note.drop_collection()

        for i in xrange(1, 101):
            Note(name="Note: %s" % i).save()

        # Check the count
        self.assertEqual(Note.objects.count(), 100)

        # Get the first 10 and confirm
        notes = Note.objects[:10]
        self.assertEqual(notes.count(), 10)

        # Test djangos template filters
        # self.assertEqual(length(notes), 10)
        t = Template("{{ notes.count }}")
        c = Context({"notes": notes})
        self.assertEqual(t.render(c), "10")

        # Test with skip
        notes = Note.objects.skip(90)
        self.assertEqual(notes.count(), 10)

        # Test djangos template filters
        self.assertEqual(notes.count(), 10)
        t = Template("{{ notes.count }}")
        c = Context({"notes": notes})
        self.assertEqual(t.render(c), "10")

        # Test with limit
        notes = Note.objects.skip(90)
        self.assertEqual(notes.count(), 10)

        # Test djangos template filters
        self.assertEqual(notes.count(), 10)
        t = Template("{{ notes.count }}")
        c = Context({"notes": notes})
        self.assertEqual(t.render(c), "10")

        # Test with skip and limit
        notes = Note.objects.skip(10).limit(10)

        # Test djangos template filters
        self.assertEqual(notes.count(), 10)
        t = Template("{{ notes.count }}")
        c = Context({"notes": notes})
        self.assertEqual(t.render(c), "10")


class MongoDBSessionTest(SessionTestsMixin, unittest.TestCase):
    backend = SessionStore

    def setUp(self):
        connect(db='mongoenginetest')
        MongoSession.drop_collection()
        super(MongoDBSessionTest, self).setUp()

    def assertIn(self, first, second, msg=None):
        self.assertTrue(first in second, msg)

    def assertNotIn(self, first, second, msg=None):
        self.assertFalse(first in second, msg)

    def test_first_save(self):
        session = SessionStore()
        session['test'] = True
        session.save()
        self.assertTrue('test' in session)

    def test_session_expiration_tz(self):
        activate_timezone(FixedOffset(60, 'UTC+1'))
        # create and save new session
        session = SessionStore()
        session.set_expiry(600)  # expire in 600 seconds
        session['test_expire'] = True
        session.save()
        # reload session with key
        key = session.session_key
        session = SessionStore(key)
        self.assertTrue('test_expire' in session, 'Session has expired before it is expected')


class MongoAuthTest(unittest.TestCase):
    user_data = {
        'username': 'user',
        'email': 'user@example.com',
        'password': 'test',
    }

    def setUp(self):
        if not DJ15:
            raise SkipTest('mongo_auth requires Django 1.5')
        connect(db='mongoenginetest')
        User.drop_collection()
        super(MongoAuthTest, self).setUp()

    def test_get_user_model(self):
        self.assertEqual(get_user_model(), MongoUser)

    def test_get_user_document(self):
        self.assertEqual(get_user_document(), User)

    def test_user_manager(self):
        manager = get_user_model()._default_manager
        self.assertTrue(isinstance(manager, MongoUserManager))

    def test_user_manager_exception(self):
        manager = get_user_model()._default_manager
        self.assertRaises(MongoUser.DoesNotExist, manager.get,
                          username='not found')

    def test_create_user(self):
        manager = get_user_model()._default_manager
        user = manager.create_user(**self.user_data)
        self.assertTrue(isinstance(user, User))
        db_user = User.objects.get(username='user')
        self.assertEqual(user.id, db_user.id)

    def test_authenticate(self):
        get_user_model()._default_manager.create_user(**self.user_data)
        user = authenticate(username='user', password='fail')
        self.assertEqual(None, user)
        user = authenticate(username='user', password='test')
        db_user = User.objects.get(username='user')
        self.assertEqual(user.id, db_user.id)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_jinja
import sys
sys.path[0:0] = [""]

import unittest

from mongoengine import *

import jinja2


class TemplateFilterTest(unittest.TestCase):

    def setUp(self):
        connect(db='mongoenginetest')

    def test_jinja2(self):
        env = jinja2.Environment()

        class TestData(Document):
            title = StringField()
            description = StringField()

        TestData.drop_collection()

        examples = [('A', '1'),
                    ('B', '2'),
                    ('C', '3')]

        for title, description in examples:
            TestData(title=title, description=description).save()

        tmpl = """
{%- for record in content -%}
    {%- if loop.first -%}{ {%- endif -%}
    "{{ record.title }}": "{{ record.description }}"
    {%- if loop.last -%} }{%- else -%},{% endif -%}
{%- endfor -%}
"""
        ctx = {'content': TestData.objects}
        template = env.from_string(tmpl)
        rendered = template.render(**ctx)

        self.assertEqual('{"A": "1","B": "2","C": "3"}', rendered)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_replicaset_connection
import sys
sys.path[0:0] = [""]
import unittest

import pymongo
from pymongo import ReadPreference, ReplicaSetConnection

import mongoengine
from mongoengine import *
from mongoengine.connection import get_db, get_connection, ConnectionError


class ConnectionTest(unittest.TestCase):

    def tearDown(self):
        mongoengine.connection._connection_settings = {}
        mongoengine.connection._connections = {}
        mongoengine.connection._dbs = {}

    def test_replicaset_uri_passes_read_preference(self):
        """Requires a replica set called "rs" on port 27017
        """

        try:
            conn = connect(db='mongoenginetest', host="mongodb://localhost/mongoenginetest?replicaSet=rs", read_preference=ReadPreference.SECONDARY_ONLY)
        except ConnectionError, e:
            return

        if not isinstance(conn, ReplicaSetConnection):
            return

        self.assertEqual(conn.read_preference, ReadPreference.SECONDARY_ONLY)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_signals
# -*- coding: utf-8 -*-
import sys
sys.path[0:0] = [""]
import unittest

from mongoengine import *
from mongoengine import signals

signal_output = []


class SignalTests(unittest.TestCase):
    """
    Testing signals before/after saving and deleting.
    """

    def get_signal_output(self, fn, *args, **kwargs):
        # Flush any existing signal output
        global signal_output
        signal_output = []
        fn(*args, **kwargs)
        return signal_output

    def setUp(self):
        connect(db='mongoenginetest')

        class Author(Document):
            name = StringField()

            def __unicode__(self):
                return self.name

            @classmethod
            def pre_init(cls, sender, document, *args, **kwargs):
                signal_output.append('pre_init signal, %s' % cls.__name__)
                signal_output.append(str(kwargs['values']))

            @classmethod
            def post_init(cls, sender, document, **kwargs):
                signal_output.append('post_init signal, %s' % document)

            @classmethod
            def pre_save(cls, sender, document, **kwargs):
                signal_output.append('pre_save signal, %s' % document)

            @classmethod
            def pre_save_post_validation(cls, sender, document, **kwargs):
                signal_output.append('pre_save_post_validation signal, %s' % document)
                if 'created' in kwargs:
                    if kwargs['created']:
                        signal_output.append('Is created')
                    else:
                        signal_output.append('Is updated')

            @classmethod
            def post_save(cls, sender, document, **kwargs):
                signal_output.append('post_save signal, %s' % document)
                if 'created' in kwargs:
                    if kwargs['created']:
                        signal_output.append('Is created')
                    else:
                        signal_output.append('Is updated')

            @classmethod
            def pre_delete(cls, sender, document, **kwargs):
                signal_output.append('pre_delete signal, %s' % document)

            @classmethod
            def post_delete(cls, sender, document, **kwargs):
                signal_output.append('post_delete signal, %s' % document)

            @classmethod
            def pre_bulk_insert(cls, sender, documents, **kwargs):
                signal_output.append('pre_bulk_insert signal, %s' % documents)

            @classmethod
            def post_bulk_insert(cls, sender, documents, **kwargs):
                signal_output.append('post_bulk_insert signal, %s' % documents)
                if kwargs.get('loaded', False):
                    signal_output.append('Is loaded')
                else:
                    signal_output.append('Not loaded')
        self.Author = Author
        Author.drop_collection()

        class Another(Document):

            name = StringField()

            def __unicode__(self):
                return self.name

            @classmethod
            def pre_delete(cls, sender, document, **kwargs):
                signal_output.append('pre_delete signal, %s' % document)

            @classmethod
            def post_delete(cls, sender, document, **kwargs):
                signal_output.append('post_delete signal, %s' % document)

        self.Another = Another
        Another.drop_collection()

        class ExplicitId(Document):
            id = IntField(primary_key=True)

            @classmethod
            def post_save(cls, sender, document, **kwargs):
                if 'created' in kwargs:
                    if kwargs['created']:
                        signal_output.append('Is created')
                    else:
                        signal_output.append('Is updated')

        self.ExplicitId = ExplicitId
        ExplicitId.drop_collection()

        # Save up the number of connected signals so that we can check at the
        # end that all the signals we register get properly unregistered
        self.pre_signals = (
            len(signals.pre_init.receivers),
            len(signals.post_init.receivers),
            len(signals.pre_save.receivers),
            len(signals.pre_save_post_validation.receivers),
            len(signals.post_save.receivers),
            len(signals.pre_delete.receivers),
            len(signals.post_delete.receivers),
            len(signals.pre_bulk_insert.receivers),
            len(signals.post_bulk_insert.receivers),
        )

        signals.pre_init.connect(Author.pre_init, sender=Author)
        signals.post_init.connect(Author.post_init, sender=Author)
        signals.pre_save.connect(Author.pre_save, sender=Author)
        signals.pre_save_post_validation.connect(Author.pre_save_post_validation, sender=Author)
        signals.post_save.connect(Author.post_save, sender=Author)
        signals.pre_delete.connect(Author.pre_delete, sender=Author)
        signals.post_delete.connect(Author.post_delete, sender=Author)
        signals.pre_bulk_insert.connect(Author.pre_bulk_insert, sender=Author)
        signals.post_bulk_insert.connect(Author.post_bulk_insert, sender=Author)

        signals.pre_delete.connect(Another.pre_delete, sender=Another)
        signals.post_delete.connect(Another.post_delete, sender=Another)

        signals.post_save.connect(ExplicitId.post_save, sender=ExplicitId)

    def tearDown(self):
        signals.pre_init.disconnect(self.Author.pre_init)
        signals.post_init.disconnect(self.Author.post_init)
        signals.post_delete.disconnect(self.Author.post_delete)
        signals.pre_delete.disconnect(self.Author.pre_delete)
        signals.post_save.disconnect(self.Author.post_save)
        signals.pre_save_post_validation.disconnect(self.Author.pre_save_post_validation)
        signals.pre_save.disconnect(self.Author.pre_save)
        signals.pre_bulk_insert.disconnect(self.Author.pre_bulk_insert)
        signals.post_bulk_insert.disconnect(self.Author.post_bulk_insert)

        signals.post_delete.disconnect(self.Another.post_delete)
        signals.pre_delete.disconnect(self.Another.pre_delete)

        signals.post_save.disconnect(self.ExplicitId.post_save)

        # Check that all our signals got disconnected properly.
        post_signals = (
            len(signals.pre_init.receivers),
            len(signals.post_init.receivers),
            len(signals.pre_save.receivers),
            len(signals.pre_save_post_validation.receivers),
            len(signals.post_save.receivers),
            len(signals.pre_delete.receivers),
            len(signals.post_delete.receivers),
            len(signals.pre_bulk_insert.receivers),
            len(signals.post_bulk_insert.receivers),
        )

        self.ExplicitId.objects.delete()

        self.assertEqual(self.pre_signals, post_signals)

    def test_model_signals(self):
        """ Model saves should throw some signals. """

        def create_author():
            self.Author(name='Bill Shakespeare')

        def bulk_create_author_with_load():
            a1 = self.Author(name='Bill Shakespeare')
            self.Author.objects.insert([a1], load_bulk=True)

        def bulk_create_author_without_load():
            a1 = self.Author(name='Bill Shakespeare')
            self.Author.objects.insert([a1], load_bulk=False)

        self.assertEqual(self.get_signal_output(create_author), [
            "pre_init signal, Author",
            "{'name': 'Bill Shakespeare'}",
            "post_init signal, Bill Shakespeare",
        ])

        a1 = self.Author(name='Bill Shakespeare')
        self.assertEqual(self.get_signal_output(a1.save), [
            "pre_save signal, Bill Shakespeare",
            "pre_save_post_validation signal, Bill Shakespeare",
            "Is created",
            "post_save signal, Bill Shakespeare",
            "Is created"
        ])

        a1.reload()
        a1.name = 'William Shakespeare'
        self.assertEqual(self.get_signal_output(a1.save), [
            "pre_save signal, William Shakespeare",
            "pre_save_post_validation signal, William Shakespeare",
            "Is updated",
            "post_save signal, William Shakespeare",
            "Is updated"
        ])

        self.assertEqual(self.get_signal_output(a1.delete), [
            'pre_delete signal, William Shakespeare',
            'post_delete signal, William Shakespeare',
        ])

        signal_output = self.get_signal_output(bulk_create_author_with_load)

        # The output of this signal is not entirely deterministic. The reloaded
        # object will have an object ID. Hence, we only check part of the output
        self.assertEqual(signal_output[3],
            "pre_bulk_insert signal, [<Author: Bill Shakespeare>]")
        self.assertEqual(signal_output[-2:],
            ["post_bulk_insert signal, [<Author: Bill Shakespeare>]",
             "Is loaded",])

        self.assertEqual(self.get_signal_output(bulk_create_author_without_load), [
            "pre_init signal, Author",
            "{'name': 'Bill Shakespeare'}",
            "post_init signal, Bill Shakespeare",
            "pre_bulk_insert signal, [<Author: Bill Shakespeare>]",
            "post_bulk_insert signal, [<Author: Bill Shakespeare>]",
            "Not loaded",
        ])

    def test_queryset_delete_signals(self):
        """ Queryset delete should throw some signals. """

        self.Another(name='Bill Shakespeare').save()
        self.assertEqual(self.get_signal_output(self.Another.objects.delete), [
            'pre_delete signal, Bill Shakespeare',
            'post_delete signal, Bill Shakespeare',
        ])

    def test_signals_with_explicit_doc_ids(self):
        """ Model saves must have a created flag the first time."""
        ei = self.ExplicitId(id=123)
        # post save must received the created flag, even if there's already
        # an object id present
        self.assertEqual(self.get_signal_output(ei.save), ['Is created'])
        # second time, it must be an update
        self.assertEqual(self.get_signal_output(ei.save), ['Is updated'])

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
