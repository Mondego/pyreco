__FILENAME__ = bootstrap
##############################################################################
#
# Copyright (c) 2006 Zope Foundation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""Bootstrap a buildout-based project

Simply run this script in a directory containing a buildout.cfg.
The script accepts buildout command-line options, so you can
use the -c option to specify an alternate configuration file.
"""

import os, shutil, sys, tempfile, textwrap, urllib, urllib2, subprocess
from optparse import OptionParser

if sys.platform == 'win32':
    def quote(c):
        if ' ' in c:
            return '"%s"' % c # work around spawn lamosity on windows
        else:
            return c
else:
    quote = str

# See zc.buildout.easy_install._has_broken_dash_S for motivation and comments.
stdout, stderr = subprocess.Popen(
    [sys.executable, '-Sc',
     'try:\n'
     '    import ConfigParser\n'
     'except ImportError:\n'
     '    print 1\n'
     'else:\n'
     '    print 0\n'],
    stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
has_broken_dash_S = bool(int(stdout.strip()))

# In order to be more robust in the face of system Pythons, we want to
# run without site-packages loaded.  This is somewhat tricky, in
# particular because Python 2.6's distutils imports site, so starting
# with the -S flag is not sufficient.  However, we'll start with that:
if not has_broken_dash_S and 'site' in sys.modules:
    # We will restart with python -S.
    args = sys.argv[:]
    args[0:0] = [sys.executable, '-S']
    args = map(quote, args)
    os.execv(sys.executable, args)
# Now we are running with -S.  We'll get the clean sys.path, import site
# because distutils will do it later, and then reset the path and clean
# out any namespace packages from site-packages that might have been
# loaded by .pth files.
clean_path = sys.path[:]
import site
sys.path[:] = clean_path
for k, v in sys.modules.items():
    if k in ('setuptools', 'pkg_resources') or (
        hasattr(v, '__path__') and
        len(v.__path__)==1 and
        not os.path.exists(os.path.join(v.__path__[0],'__init__.py'))):
        # This is a namespace package.  Remove it.
        sys.modules.pop(k)

is_jython = sys.platform.startswith('java')

setuptools_source = 'http://peak.telecommunity.com/dist/ez_setup.py'
distribute_source = 'http://python-distribute.org/distribute_setup.py'

# parsing arguments
def normalize_to_url(option, opt_str, value, parser):
    if value:
        if '://' not in value: # It doesn't smell like a URL.
            value = 'file://%s' % (
                urllib.pathname2url(
                    os.path.abspath(os.path.expanduser(value))),)
        if opt_str == '--download-base' and not value.endswith('/'):
            # Download base needs a trailing slash to make the world happy.
            value += '/'
    else:
        value = None
    name = opt_str[2:].replace('-', '_')
    setattr(parser.values, name, value)

usage = '''\
[DESIRED PYTHON FOR BUILDOUT] bootstrap.py [options]

Bootstraps a buildout-based project.

Simply run this script in a directory containing a buildout.cfg, using the
Python that you want bin/buildout to use.

Note that by using --setup-source and --download-base to point to
local resources, you can keep this script from going over the network.
'''

parser = OptionParser(usage=usage)
parser.add_option("-v", "--version", dest="version",
                          help="use a specific zc.buildout version")
parser.add_option("-d", "--distribute",
                   action="store_true", dest="use_distribute", default=False,
                   help="Use Distribute rather than Setuptools.")
parser.add_option("--setup-source", action="callback", dest="setup_source",
                  callback=normalize_to_url, nargs=1, type="string",
                  help=("Specify a URL or file location for the setup file. "
                        "If you use Setuptools, this will default to " +
                        setuptools_source + "; if you use Distribute, this "
                        "will default to " + distribute_source +"."))
parser.add_option("--download-base", action="callback", dest="download_base",
                  callback=normalize_to_url, nargs=1, type="string",
                  help=("Specify a URL or directory for downloading "
                        "zc.buildout and either Setuptools or Distribute. "
                        "Defaults to PyPI."))
parser.add_option("--eggs",
                  help=("Specify a directory for storing eggs.  Defaults to "
                        "a temporary directory that is deleted when the "
                        "bootstrap script completes."))
parser.add_option("-t", "--accept-buildout-test-releases",
                  dest='accept_buildout_test_releases',
                  action="store_true", default=False,
                  help=("Normally, if you do not specify a --version, the "
                        "bootstrap script and buildout gets the newest "
                        "*final* versions of zc.buildout and its recipes and "
                        "extensions for you.  If you use this flag, "
                        "bootstrap and buildout will get the newest releases "
                        "even if they are alphas or betas."))
parser.add_option("-c", None, action="store", dest="config_file",
                   help=("Specify the path to the buildout configuration "
                         "file to be used."))

options, args = parser.parse_args()

# if -c was provided, we push it back into args for buildout's main function
if options.config_file is not None:
    args += ['-c', options.config_file]

if options.eggs:
    eggs_dir = os.path.abspath(os.path.expanduser(options.eggs))
else:
    eggs_dir = tempfile.mkdtemp()

if options.setup_source is None:
    if options.use_distribute:
        options.setup_source = distribute_source
    else:
        options.setup_source = setuptools_source

if options.accept_buildout_test_releases:
    args.append('buildout:accept-buildout-test-releases=true')
args.append('bootstrap')

try:
    import pkg_resources
    import setuptools # A flag.  Sometimes pkg_resources is installed alone.
    if not hasattr(pkg_resources, '_distribute'):
        raise ImportError
except ImportError:
    ez_code = urllib2.urlopen(
        options.setup_source).read().replace('\r\n', '\n')
    ez = {}
    exec ez_code in ez
    setup_args = dict(to_dir=eggs_dir, download_delay=0)
    if options.download_base:
        setup_args['download_base'] = options.download_base
    if options.use_distribute:
        setup_args['no_fake'] = True
    ez['use_setuptools'](**setup_args)
    if 'pkg_resources' in sys.modules:
        reload(sys.modules['pkg_resources'])
    import pkg_resources
    # This does not (always?) update the default working set.  We will
    # do it.
    for path in sys.path:
        if path not in pkg_resources.working_set.entries:
            pkg_resources.working_set.add_entry(path)

cmd = [quote(sys.executable),
       '-c',
       quote('from setuptools.command.easy_install import main; main()'),
       '-mqNxd',
       quote(eggs_dir)]

if not has_broken_dash_S:
    cmd.insert(1, '-S')

find_links = options.download_base
if not find_links:
    find_links = os.environ.get('bootstrap-testing-find-links')
if find_links:
    cmd.extend(['-f', quote(find_links)])

if options.use_distribute:
    setup_requirement = 'distribute'
else:
    setup_requirement = 'setuptools'
ws = pkg_resources.working_set
setup_requirement_path = ws.find(
    pkg_resources.Requirement.parse(setup_requirement)).location
env = dict(
    os.environ,
    PYTHONPATH=setup_requirement_path)

requirement = 'zc.buildout'
version = options.version
if version is None and not options.accept_buildout_test_releases:
    # Figure out the most recent final version of zc.buildout.
    import setuptools.package_index
    _final_parts = '*final-', '*final'
    def _final_version(parsed_version):
        for part in parsed_version:
            if (part[:1] == '*') and (part not in _final_parts):
                return False
        return True
    index = setuptools.package_index.PackageIndex(
        search_path=[setup_requirement_path])
    if find_links:
        index.add_find_links((find_links,))
    req = pkg_resources.Requirement.parse(requirement)
    if index.obtain(req) is not None:
        best = []
        bestv = None
        for dist in index[req.project_name]:
            distv = dist.parsed_version
            if _final_version(distv):
                if bestv is None or distv > bestv:
                    best = [dist]
                    bestv = distv
                elif distv == bestv:
                    best.append(dist)
        if best:
            best.sort()
            version = best[-1].version
if version:
    requirement = '=='.join((requirement, version))
cmd.append(requirement)

if is_jython:
    import subprocess
    exitcode = subprocess.Popen(cmd, env=env).wait()
else: # Windows prefers this, apparently; otherwise we would prefer subprocess
    exitcode = os.spawnle(*([os.P_WAIT, sys.executable] + cmd + [env]))
if exitcode != 0:
    sys.stdout.flush()
    sys.stderr.flush()
    print ("An error occurred when trying to install zc.buildout. "
           "Look above this message for any errors that "
           "were output by easy_install.")
    sys.exit(exitcode)

ws.add_entry(eggs_dir)
ws.require(requirement)
import zc.buildout.buildout
zc.buildout.buildout.main(args)
if not options.eggs: # clean up temporary egg directory
    shutil.rmtree(eggs_dir)

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# FormAlchemy documentation build configuration file, created by
# sphinx-quickstart on Thu Sep  4 22:53:00 2008.
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
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.doctest']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.txt'

# The master toctree document.
master_doc = 'index'

# General substitutions.
project = 'FormAlchemy'
copyright = '2008, Alexandre Conrad'

# The default replacements for |version| and |release|, also used in various
# other places throughout the built documents.
#
# The short X.Y version.
version = '1.3.6'
# The full version, including alpha/beta/rc tags.
release = version

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
today_fmt = '%B %d, %Y'

# List of documents that shouldn't be included in the build.
#unused_docs = []

# List of directories, relative to source directories, that shouldn't be searched
# for source files.
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


# Options for HTML output
# -----------------------

# The style sheet to use for HTML and HTML Help pages. A file of that name
# must exist either in Sphinx' static/ path, or in one of the custom paths
# given in html_static_path.

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
htmlhelp_basename = 'FormAlchemydoc'


# Options for LaTeX output
# ------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, document class [howto/manual]).
latex_documents = [
  ('index', 'FormAlchemy.tex', 'FormAlchemy Documentation',
   'Alexandre Conrad', 'manual'),
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

# Also add __init__'s doc to `autoclass` calls
autoclass_content = 'both'

html_theme = 'nature'
from os import path
pkg_dir = path.abspath(__file__).split('/docs')[0]
setup = path.join(pkg_dir, 'setup.py')
if path.isfile(setup):
    for line_ in open(setup):
        if line_.startswith("version"):
            version = line_.split('=')[-1]
            version = version.strip()
            version = version.strip("'\"")
            release = version
            break
del pkg_dir, setup, path


########NEW FILE########
__FILENAME__ = base
# Copyright (C) 2007 Alexandre Conrad, alexandre (dot) conrad (at) gmail (dot) com
#
# This module is part of FormAlchemy and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php


########NEW FILE########
__FILENAME__ = config
# -*- coding: utf-8 -*-
import sys
from formalchemy import templates

__doc__ = """
There is two configuration settings available in a global config object.

- encoding: the global encoding used by FormAlchemy to deal with unicode. Default: utf-8

- engine: A valide :class:`~formalchemy.templates.TemplateEngine`

- date_format: Used to format date fields. Default to %Y-%d-%m

- date_edit_format: Used to retrieve field order. Default to m-d-y

Here is a simple example::

    >>> from formalchemy import config
    >>> config.encoding = 'iso-8859-1'
    >>> config.encoding
    'iso-8859-1'

    >>> from formalchemy import templates
    >>> config.engine = templates.TempitaEngine

There is also a convenience method to set the configuration from a config file::

    >>> config.from_config({'formalchemy.encoding':'utf-8',
    ...                     'formalchemy.engine':'mako',
    ...                     'formalchemy.engine.options.input_encoding':'utf-8',
    ...                     'formalchemy.engine.options.output_encoding':'utf-8',
    ...                    })
    >>> config.from_config({'formalchemy.encoding':'utf-8'})
    >>> config.encoding
    'utf-8'
    >>> isinstance(config.engine, templates.MakoEngine)
    True

"""

class Config(object):
    __doc__ = __doc__
    __name__ = 'formalchemy.config'
    __file__ = __file__
    __data = dict(
        encoding='utf-8',
        date_format='%Y-%m-%d',
        date_edit_format='m-d-y',
        engine = templates.default_engine,
    )

    def __getattr__(self, attr):
        if attr in self.__data:
            return self.__data[attr]
        else:
            raise AttributeError('Configuration has no attribute %s' % attr)

    def __setattr__(self, attr, value):
        meth = getattr(self, '__set_%s' % attr, None)
        if callable(meth):
            meth(value)
        else:
            self.__data[attr] = value

    def __set_engine(self, value):
        if isinstance(value, templates.TemplateEngine):
            self.__data['engine'] = value
        else:
            raise ValueError('%s is not a template engine')

    def _get_config(self, config, prefix):
        values = {}
        config_keys = config.keys()
        for k in config_keys:
            if k.startswith(prefix):
                v = config.pop(k)
                k = k[len(prefix):]
                values[k] = v
        return values

    def from_config(self, config, prefix='formalchemy.'):
        from formalchemy import templates
        engine_config = self._get_config(config, '%s.engine.options.' % prefix)
        for k, v in self._get_config(config, prefix).items():
            if k == 'engine':
                engine = templates.__dict__.get('%sEngine' % v.title(), None)
                if engine is not None:
                    v = engine(**engine_config)
                else:
                    raise ValueError('%sEngine does not exist' % v.title())
            self.__setattr__(k, v)

    def __repr__(self):
        return "<module 'formalchemy.config' from '%s' with values %s>" % (self.__file__, self.__data)

sys.modules['formalchemy.config'] = Config()


########NEW FILE########
__FILENAME__ = exceptions
# -*- coding: utf-8 -*-

class PkError(Exception):
    """An exception raised when a primary key conflict occur"""

class ValidationError(Exception):
    """an exception raised when the validation failed
    """
    @property
    def message(self):
        return self.args[0]
    def __repr__(self):
        return 'ValidationError(%r,)' % self.message

class FieldNotFoundError(ValidationError):
    """an exception raise when the field is not found in request data"""

########NEW FILE########
__FILENAME__ = couchdb
# -*- coding: utf-8 -*-
__doc__ = """

Define a couchdbkit schema::

    >>> from couchdbkit import schema
    >>> from formalchemy.ext import couchdb
    >>> class Person(couchdb.Document):
    ...     name = schema.StringProperty(required=True)
    ...     @classmethod
    ...     def _render_options(self, fs):
    ...         return [(gawel, gawel._id), (benoitc, benoitc._id)]
    ...     def __unicode__(self): return getattr(self, 'name', None) or u''
    >>> gawel = Person(name='gawel')
    >>> gawel._id = '123'
    >>> benoitc = Person(name='benoitc')
    >>> benoitc._id = '456'

    >>> class Pet(couchdb.Document):
    ...     name = schema.StringProperty(required=True)
    ...     type = schema.StringProperty(required=True)
    ...     birthdate = schema.DateProperty(auto_now=True)
    ...     weight_in_pounds = schema.IntegerProperty()
    ...     spayed_or_neutered = schema.BooleanProperty()
    ...     owner = schema.SchemaProperty(Person)
    ...     friends = schema.SchemaListProperty(Person)

Configure your FieldSet::

    >>> fs = couchdb.FieldSet(Pet)
    >>> fs.configure(include=[fs.name, fs.type, fs.birthdate, fs.weight_in_pounds])
    >>> p = Pet(name='dewey')
    >>> p.name = 'dewey'
    >>> p.type = 'cat'
    >>> p.owner = gawel
    >>> p.friends = [benoitc]
    >>> fs = fs.bind(p)

Render it::

    >>> # rendering
    >>> fs.name.is_required()
    True
    >>> print fs.render() # doctest: +ELLIPSIS +NORMALIZE_WHITESPACE
    <div>
      <label class="field_req" for="Pet--name">Name</label>
      <input id="Pet--name" name="Pet--name" type="text" value="dewey" />
    </div>
    <script type="text/javascript">
    //<![CDATA[
    document.getElementById("Pet--name").focus();
    //]]>
    </script>
    <div>
      <label class="field_req" for="Pet--type">Type</label>
      <input id="Pet--type" name="Pet--type" type="text" value="cat" />
    </div>
    <div>
      <label class="field_opt" for="Pet--birthdate">Birthdate</label>
      <span id="Pet--birthdate"><select id="Pet--birthdate__month" name="Pet--birthdate__month">
    <option value="MM">Month</option>
    ...
    <option selected="selected" value="...">...</option>
    ...
    
Same for grids::

    >>> # grid
    >>> grid = couchdb.Grid(Pet, [p, Pet()])
    >>> grid.configure(include=[grid.name, grid.type, grid.birthdate, grid.weight_in_pounds, grid.friends])
    >>> print grid.render() # doctest: +SKIP +ELLIPSIS +NORMALIZE_WHITESPACE
    <thead>
      <tr>
          <th>Name</th>
          <th>Type</th>
          <th>Birthdate</th>
          <th>Weight in pounds</th>
          <th>Friends</th>
      </tr>
    </thead>
    <tbody>
      <tr class="even">
        <td>
          <input id="Pet--name" name="Pet--name" type="text" value="dewey" />
        </td>
        <td>
          <input id="Pet--type" name="Pet--type" type="text" value="cat" />
        </td>
        <td>
          <span id="Pet--birthdate">...
        </td>
        <td>
          <select id="Pet--friends" multiple="multiple" name="Pet--friends">
            <option value="123">gawel</option>
            <option selected="selected" value="456">benoitc</option>
          </select>
        </td>...

"""
from formalchemy.forms import FieldSet as BaseFieldSet
from formalchemy.tables import Grid as BaseGrid
from formalchemy.fields import Field as BaseField
from formalchemy.forms import SimpleMultiDict
from formalchemy import fields
from formalchemy import validators
from formalchemy import fatypes
from sqlalchemy.util import OrderedDict
from couchdbkit.schema.properties_proxy import LazySchemaList
from couchdbkit import schema

from datetime import datetime


__all__ = ['Field', 'FieldSet', 'Session', 'Document']

class Pk(property):
    def __init__(self, attr='_id'):
        self.attr = attr
    def __get__(self, instance, cls):
        if not instance:
            return self
        return getattr(instance, self.attr, None) or None
    def __set__(self, instance, value):
        setattr(instance, self.attr, value)

class Document(schema.Document):
    _pk = Pk()

class Query(list):
    """A list like object to emulate SQLAlchemy's Query. This mostly exist to
    work with ``webhelpers.paginate.Page``"""

    def __init__(self, model, **options):
        self.model = model
        self._init = False
        self.options = options
    def get(self, id):
        """Get a record by id"""
        return self.model.get(id)
    def view(self, view_name, **kwargs):
        """set self to a list of record returned by view named ``{model_name}/{view_name}``"""
        kwargs = kwargs or self.options
        if not self._init:
            self.extend([r for r in self.model.view('%s/%s' % (self.model.__name__.lower(), view_name), **kwargs)])
            self._init = True
        return self
    def all(self, **kwargs):
        """set self to a list of record returned by view named ``{model_name}/all``"""
        kwargs = kwargs or self.options
        return self.view('all', **kwargs)
    def __len__(self):
        if not self._init:
            self.all()
        return list.__len__(self)

class Session(object):
    """A SA like Session to implement couchdb"""
    def __init__(self, db):
        self.db = db
    def add(self, record):
        """add a record"""
        record.save()
    def update(self, record):
        """update a record"""
        record.save()
    def delete(self, record):
        """delete a record"""
        del self.db[record._id]
    def query(self, model, *args, **kwargs):
        """return a :class:`~formalchemy.ext.couchdb.Query` bound to model object"""
        return Query(model, *args, **kwargs)
    def commit(self):
        """do nothing since there is no transaction in couchdb"""
    remove = commit

def _stringify(value):
    if isinstance(value, (list, LazySchemaList)):
        return [_stringify(v) for v in value]
    if isinstance(value, schema.Document):
        return value._id
    return value

class Field(BaseField):
    """Field for CouchDB FieldSet"""
    def __init__(self, *args, **kwargs):
        self.schema = kwargs.pop('schema')
        if self.schema and 'renderer' not in kwargs:
            kwargs['renderer'] = fields.SelectFieldRenderer
        if self.schema and 'options' not in kwargs:
            if hasattr(self.schema, '_render_options'):
                kwargs['options'] = self.schema._render_options
            else:
                kwargs['options'] = lambda fs: [(d, d._id) for d in Query(self.schema).all()]
        if kwargs.get('type') == fatypes.List:
            kwargs['multiple'] = True
        BaseField.__init__(self, *args, **kwargs)

    @property
    def value(self):
        if not self.is_readonly() and self.parent.data is not None:
            v = self._deserialize()
            if v is not None:
                return v
        value = getattr(self.model, self.name)
        return _stringify(value)

    @property
    def raw_value(self):
        try:
            value = getattr(self.model, self.name)
            return _stringify(value)
        except (KeyError, AttributeError):
            pass
        if callable(self._value):
            return self._value(self.model)
        return self._value

    @property
    def model_value(self):
        return self.raw_value

    def sync(self):
        """Set the attribute's value in `model` to the value given in `data`"""
        if not self.is_readonly():
            value = self._deserialize()
            if self.schema:
                if isinstance(value, list):
                    value = [self.schema.get(v) for v in value]
                else:
                    value = self.schema.get(value)
            setattr(self.model, self.name, value)

class FieldSet(BaseFieldSet):
    """See :class:`~formalchemy.forms.FieldSet`"""
    __sa__ = False
    def __init__(self, model, **kwargs):
        BaseFieldSet.__init__(self, model, **kwargs)
        if model is not None and isinstance(model, schema.Document):
            BaseFieldSet.rebind(self, model.__class__, data=kwargs.get('data', None))
            self.doc = model.__class__
            self.model = model
            self._bound_pk = fields._pk(model)
        else:
            BaseFieldSet.rebind(self, model, data=kwargs.get('data', None))
            self.doc = model
        values = self.doc._properties.values()
        values.sort(lambda a, b: cmp(a.creation_counter, b.creation_counter))
        for v in values:
            if getattr(v, 'name'):
                k = v.name
                sch = None
                if isinstance(v, schema.SchemaListProperty):
                    t = fatypes.List
                    sch = v._schema
                elif isinstance(v, schema.SchemaProperty):
                    t = fatypes.String
                    sch = v._schema
                else:
                    try:
                        t = getattr(fatypes, v.__class__.__name__.replace('Property',''))
                    except AttributeError:
                        raise NotImplementedError('%s is not mapped to a type for field %s (%s)' % (v.__class__, k, v.__class__.__name__))
                self.append(Field(name=k, type=t, schema=sch))
                if v.required:
                    self._fields[k].validators.append(validators.required)

    def bind(self, model=None, session=None, data=None):
        """Bind to an instance"""
        if not (model or session or data):
            raise Exception('must specify at least one of {model, session, data}')
        if not model:
            if not self.model:
                raise Exception('model must be specified when none is already set')
            model = fields._pk(self.model) is None and self.doc() or self.model
        # copy.copy causes a stacktrace on python 2.5.2/OSX + pylons.  unable to reproduce w/ simpler sample.
        mr = object.__new__(self.__class__)
        mr.__dict__ = dict(self.__dict__)
        # two steps so bind's error checking can work
        mr.rebind(model, session, data)
        mr._fields = OrderedDict([(key, renderer.bind(mr)) for key, renderer in self._fields.iteritems()])
        if self._render_fields:
            mr._render_fields = OrderedDict([(field.key, field) for field in
                                             [field.bind(mr) for field in self._render_fields.itervalues()]])
        return mr

    def rebind(self, model=None, session=None, data=None):
        if model is not None and model is not self.doc:
            if not isinstance(model, self.doc):
                try:
                    model = model()
                except Exception, e:
                    raise Exception('''%s appears to be a class, not an instance,
                            but FormAlchemy cannot instantiate it.  (Make sure
                            all constructor parameters are optional!) %r - %s''' % (
                            model, self.doc, e))
        else:
            model = self.doc()
        self.model = model
        self._bound_pk = fields._pk(model)
        if data is None:
            self.data = None
        elif hasattr(data, 'getall') and hasattr(data, 'getone'):
            self.data = data
        else:
            try:
                self.data = SimpleMultiDict(data)
            except:
                raise Exception('unsupported data object %s.  currently only dicts and Paste multidicts are supported' % self.data)

    def jsonify(self):
        if isinstance(self.model, schema.Document):
            return self.model.to_json()
        return self.doc().to_json()

class Grid(BaseGrid, FieldSet):
    """See :class:`~formalchemy.tables.Grid`"""
    def __init__(self, cls, instances=None, **kwargs):
        FieldSet.__init__(self, cls, **kwargs)
        self.rows = instances or []
        self.readonly = False
        self._errors = {}

    def _get_errors(self):
        return self._errors

    def _set_errors(self, value):
        self._errors = value
    errors = property(_get_errors, _set_errors)

    def rebind(self, instances=None, session=None, data=None):
        FieldSet.rebind(self, self.model, data=data)
        if instances is not None:
            self.rows = instances

    def bind(self, instances=None, session=None, data=None):
        mr = FieldSet.bind(self, self.model, session, data)
        mr.rows = instances
        return mr

    def _set_active(self, instance, session=None):
        FieldSet.rebind(self, instance, session or self.session, self.data)


########NEW FILE########
__FILENAME__ = fsblob
# -*- coding: utf-8 -*-
import os
import stat
import cgi
import string
import random
import shutil
import formalchemy.helpers as h
from formalchemy.fields import FileFieldRenderer as Base
from formalchemy.fields import FieldRenderer
from formalchemy.validators import regex
from formalchemy.i18n import _

try:
    from pylons import config
except ImportError:
    config = {}

__all__ = ['file_extension', 'image_extension',
           'FileFieldRenderer', 'ImageFieldRenderer']

def file_extension(extensions=[], errormsg=None):
    """Validate a file extension.
    """
    if errormsg is None:
        errormsg = _('Invalid file extension. Must be %s'%', '.join(extensions))
    return regex(r'^.+\.(%s)$' % '|'.join(extensions), errormsg=errormsg)

def image_extension(extensions=['jpeg', 'jpg', 'gif', 'png']):
    """Validate an image extension. default valid extensions are jpeg, jpg,
    gif, png.
    """
    errormsg = _('Invalid image file. Must be %s'%', '.join(extensions))
    return file_extension(extensions, errormsg=errormsg)

def normalized_basename(path):
    """
    >>> print normalized_basename(u'c:\\Prog files\My fil\xe9.jpg')
    My_fil.jpg

    >>> print normalized_basename('c:\\Prog files\My fil\xc3\xa9.jpg')
    My_fil.jpg

    """
    if isinstance(path, str):
        path = path.decode('utf-8', 'ignore').encode('ascii', 'ignore')
    if isinstance(path, unicode):
        path = path.encode('ascii', 'ignore')
    filename = path.split('/')[-1]
    filename = filename.split('\\')[-1]
    return filename.replace(' ', '_')


class FileFieldRenderer(Base):
    """render a file input field stored on file system
    """

    url_prefix = '/'

    @property
    def storage_path(self):
        if 'app_conf' in config:
            config['app_conf'].get('storage_path', '')

    def __init__(self, *args, **kwargs):
        if not self.storage_path or not os.path.isdir(self.storage_path):
            raise ValueError(
                    'storage_path must be set to a valid path. Got %r' % self.storage_path)
        Base.__init__(self, *args, **kwargs)
        self._path = None

    def relative_path(self, filename):
        """return the file path relative to root
        """
        rdir = lambda: ''.join(random.sample(string.ascii_lowercase, 3))
        path = '/'.join([rdir(), rdir(), rdir(), filename])
        return path

    def get_url(self, relative_path):
        """return the file url. by default return the relative path stored in
        the DB
        """
        return self.url_prefix + relative_path

    def get_size(self):
        relative_path = self.field.value
        if relative_path:
            filepath = os.path.join(self.storage_path,
                                    relative_path.replace('/', os.sep))
            if os.path.isfile(filepath):
                return os.stat(filepath)[stat.ST_SIZE]
        return 0

    def render(self, **kwargs):
        """render a file field and the file preview
        """
        html = Base.render(self, **kwargs)
        value = self.field.value
        if value:
            html += self.render_readonly()

            # add the old value for objects not yet stored
            old_value = '%s--old' % self.name
            html += h.hidden_field(old_value, value=value)
        return html


    def render_readonly(self, **kwargs):
        """render the filename and the binary size in a human readable with a
        link to the file itself.
        """
        value = self.field.value
        if value:
            content = '%s (%s)' % (normalized_basename(value),
                                 self.readable_size())
            return h.content_tag('a', content,
                                 href=self.get_url(value), **kwargs)
        return ''

    def _serialized_value(self):
        name = self.name
        if '%s--remove' % self.name in self.params:
            self._path = None
            return None
        elif name in self.params:
            return self.params.getone(self.name)
        old_value = '%s--old' % self.name
        if old_value in self.params:
            self._path = self.params.getone(old_value)
            return self._path
        raise RuntimeError('This should never occurs')

    def deserialize(self):
        if self._path:
            return self._path
        data = FieldRenderer.deserialize(self)
        if isinstance(data, cgi.FieldStorage):
            filename = normalized_basename(data.filename)
            self._path = self.relative_path(filename)
            filepath = os.path.join(self.storage_path,
                                    self._path.replace('/', os.sep))
            dirname = os.path.dirname(filepath)
            if not os.path.isdir(dirname):
                os.makedirs(dirname)
            fd = open(filepath, 'wb')
            shutil.copyfileobj(data.file, fd)
            fd.close()
            return self._path
        checkbox_name = '%s--remove' % self.name
        if not data and not self.params.has_key(checkbox_name):
            data = getattr(self.field.model, self.field.name)

        # get value from old_value if needed
        old_value = '%s--old' % self.name
        checkbox_name = '%s--remove' % self.name
        if not data and not self.params.has_key(checkbox_name) \
                    and self.params.has_key(old_value):
            return self.params[old_value]
        return data is not None and data or ''

    @classmethod
    def new(cls, storage_path, url_prefix='/'):
        """Return a new class::

            >>> FileFieldRenderer.new(storage_path='/') # doctest: +ELLIPSIS
            <class 'formalchemy.ext.fsblob.ConfiguredFileFieldRenderer_...'>
            >>> ImageFieldRenderer.new(storage_path='/') # doctest: +ELLIPSIS
            <class 'formalchemy.ext.fsblob.ConfiguredImageFieldRenderer_...'>
        """
        if url_prefix[-1] != '/':
            url_prefix += '/'
        name = 'Configured%s_%s' % (cls.__name__, str(random.random())[2:])
        return type(name, (cls,),
                    dict(storage_path=storage_path,
                    url_prefix=url_prefix))


class ImageFieldRenderer(FileFieldRenderer):

    def render_readonly(self, **kwargs):
        """render the image tag with a link to the image itself.
        """
        value = self.field.value
        if value:
            url = self.get_url(value)
            content = '%s (%s)' % (normalized_basename(value),
                                 self.readable_size())
            tag = h.tag('img', src=url, alt=content)
            return h.content_tag('a', tag, href=url, **kwargs)
        return ''


########NEW FILE########
__FILENAME__ = admin
# standard pylons controller imports
import os
import logging
log = logging.getLogger(__name__)

from pylons import request, response, session, config
from pylons import tmpl_context as c

from pylons import url
from pylons.controllers.util import redirect
import pylons.controllers.util as h
from webhelpers.paginate import Page

from sqlalchemy.orm import class_mapper, object_session
from formalchemy import *
from formalchemy.i18n import _, get_translator
from formalchemy.fields import _pk
from formalchemy.templates import MakoEngine

import simplejson as json

__all__ = ['FormAlchemyAdminController']

# misc labels
_('Add')
_('Edit')
_('New')
_('Save')
_('Delete')
_('Cancel')
_('Models')
_('Existing objects')
_('New object')
_('Related types')
_('Existing objects')
_('Create form')

# templates

template_dir = os.path.dirname(__file__)
static_dir = os.path.join(template_dir, 'resources')

def flash(msg):
    """Add 'msg' to the users flashest list in the users session"""
    flashes = session.setdefault('_admin_flashes', [])
    flashes.append(msg)
    session.save()


def get_forms(model_module, forms):
    """scan model and forms"""
    if forms is not None:
        model_fieldsets = dict((form.model.__class__.__name__, form)
                               for form in forms.__dict__.itervalues()
                               if isinstance(form, FieldSet))
        model_grids = dict((form.model.__class__.__name__, form)
                           for form in forms.__dict__.itervalues()
                           if isinstance(form, Grid))
    else:
        model_fieldsets = dict()
        model_grids = dict()

    # generate missing forms, grids
    for key, obj in model_module.__dict__.iteritems():
        try:
            class_mapper(obj)
        except:
            continue
        if not isinstance(obj, type):
            continue
        if key not in model_fieldsets:
            model_fieldsets[key] = FieldSet(obj)
        if key not in model_grids:
            model_grids[key] = Grid(obj)
    # add Edit + Delete link to grids
    for modelname, grid in model_grids.iteritems():
        def edit_link():
            model_url = url('models', modelname=modelname)
            return lambda item: '<a href="%(url)s/%(id)s" title="%(label)s" class="icon edit">%(label)s</a>' % dict(
                                url=model_url, id=_pk(item),
                                label=get_translator().gettext('edit'))
        def delete_link():
            model_url = url('models', modelname=modelname)
            return lambda item: '''<form action="%(url)s/%(id)s" method="POST">
                                    <input type="submit" class="icon delete" title="%(label)s" value="" />
                                    <input type="hidden" name="_method" value="DELETE" />
                                    </form>
                                ''' % dict(
                                    url=model_url, id=_pk(item),
                                    label=get_translator().gettext('delete'))
        grid.append(Field('edit', types.String, edit_link()))
        grid.append(Field('delete', types.String, delete_link()))
        grid.readonly = True

    return {'_model_fieldsets':model_fieldsets, '_model_grids':model_grids}


class AdminController(object):
    """Base class to generate administration interface in Pylons"""
    _custom_css = _custom_js = ''

    def render_json(self, fs=None, **kwargs):
        response.content_type = 'text/javascript'
        if fs:
            fields = dict([(field.key, field.model_value) for field in fs.render_fields.values()])
            data = dict(fields=fields)
            pk = _pk(fs.model)
            if pk:
                data['url'] = url('view_model', modelname=fs.model.__class__.__name__, id=pk)
        else:
            data = {}
        data.update(kwargs)
        return json.dumps(data)

    def index(self, format='html'):
        """List model types"""
        modelnames = sorted(self._model_grids.keys())
        if format == 'json':
            return self.render_json(**dict([(m, url('models', modelname=m)) for m in modelnames]))
        return self._engine('admin_index', c=c, modelname=None,
                                     modelnames=modelnames,
                                     custom_css = self._custom_css,
                                     custom_js = self._custom_js)

    def list(self, modelname, format='html'):
        """List instances of a model type"""
        S = self.Session()
        grid = self._model_grids[modelname]
        query = S.query(grid.model.__class__)
        page = Page(query, page=int(request.GET.get('page', '1')), **self._paginate)
        if format == 'json':
            values = []
            for item in page:
                pk = _pk(item)
                values.append((pk, url('view_model', pk)))
            return self.render_json(records=dict(values), page_count=page.page_count, page=page.page)
        grid = grid.bind(instances=page, session=None)
        clsnames = [f.relation_type().__name__ for f in grid._fields.itervalues() if f.is_relation]
        return self._engine('admin_list', c=c,
                            grid=grid,
                            page=page,
                            clsnames=clsnames,
                            modelname=modelname,
                            custom_css = self._custom_css,
                            custom_js = self._custom_js)

    def edit(self, modelname, id=None, format='html'):
        """Edit (or create, if `id` is None) an instance of the given model type"""

        saved = 1

        if id and id.endswith('.json'):
            id = id[:-5]
            format = 'json'

        if request.method == 'POST' or format == 'json':
            if id:
                prefix = '%s-%s' % (modelname, id)
            else:
                prefix = '%s-' % modelname

            if request.method == 'PUT':
                items = json.load(request.body_file).items()
                request.method = 'POST'
            elif '_method' not in request.POST:
                items = request.POST.items()
                format = 'json'
            else:
                items = None

            if items:
                for k, v in items:
                    if not k.startswith(prefix):
                        if isinstance(v, list):
                            for val in v:
                                request.POST.add('%s-%s' % (prefix, k), val)
                        else:
                            request.POST.add('%s-%s' % (prefix, k), v)

        fs = self._model_fieldsets[modelname]
        S = self.Session()

        if id:
            instance = S.query(fs.model.__class__).get(id)
            assert instance, id
            title = 'Edit'
        else:
            instance = fs.model.__class__
            title = 'New object'

        if request.method == 'POST':
            F_ = get_translator().gettext
            c.fs = fs.bind(instance, data=request.POST, session=not id and S or None)
            if c.fs.validate():
                c.fs.sync()
                S.flush()
                if not id:
                    # needed if the object does not exist in db
                    if not object_session(c.fs.model):
                        S.add(c.fs.model)
                    message = _('Created %s %s')
                else:
                    S.refresh(c.fs.model)
                    message = _('Modified %s %s')
                S.commit()
                saved = 0

                if format == 'html':
                    message = F_(message) % (modelname.encode('utf-8', 'ignore'),
                                             _pk(c.fs.model))
                    flash(message)
                    redirect(url('models', modelname=modelname))
        else:
            c.fs = fs.bind(instance, session=not id and S or None)

        if format == 'html':
            return self._engine('admin_edit', c=c,
                                        action=title, id=id,
                                        modelname=modelname,
                                        custom_css = self._custom_css,
                                        custom_js = self._custom_js)
        else:
            return self.render_json(fs=c.fs, status=saved, model=modelname)

    def delete(self, modelname, id, format='html'):
        """Delete an instance of the given model type"""
        F_ = get_translator().gettext
        fs = self._model_fieldsets[modelname]
        S = self.Session()
        instance = S.query(fs.model.__class__).get(id)
        key = _pk(instance)
        S.delete(instance)
        S.commit()

        if format == 'html':
            message = F_(_('Deleted %s %s')) % (modelname.encode('utf-8', 'ignore'),
                                                key)
            flash(message)
            redirect(url('models', modelname=modelname))
        else:
            return self.render_json(status=0)

    def static(self, id):
        filename = os.path.basename(id)
        if filename not in os.listdir(static_dir):
            raise IOError('Invalid filename: %s' % filename)
        filepath = os.path.join(static_dir, filename)
        if filename.endswith('.css'):
            response.headers['Content-type'] = "text/css"
        elif filename.endswith('.js'):
            response.headers['Content-type'] = "text/javascript"
        elif filename.endswith('.png'):
            response.headers['Content-type'] = "image/png"
        else:
            raise IOError('Invalid filename: %s' % filename)
        fd = open(filepath, 'rb')
        data = fd.read()
        fd.close()
        return data

class TemplateEngine(MakoEngine):
    directories = [os.path.join(p, 'fa_admin') for p in config['pylons.paths']['templates']] + [template_dir]
    _templates = ['base', 'admin_index', 'admin_list', 'admin_edit']

def FormAlchemyAdminController(cls, engine=None, paginate=dict(), **kwargs):
    """
    Generate a controller that is a subclass of `AdminController`
    and the Pylons BaseController `cls`
    """
    kwargs = get_forms(cls.model, cls.forms)
    log.info('creating admin controller with args %s' % kwargs)

    kwargs['_paginate'] = paginate
    if engine is not None:
        kwargs['_engine'] = engine
    else:
        kwargs['_engine'] = TemplateEngine(input_encoding='utf-8', output_encoding='utf-8')

    return type(cls.__name__, (cls, AdminController), kwargs)

########NEW FILE########
__FILENAME__ = controller
# -*- coding: utf-8 -*-
import os
from paste.urlparser import StaticURLParser
from pylons import request, response, session, tmpl_context as c
from pylons.controllers.util import abort, redirect
from pylons.templating import render_mako as render
from pylons import url
from webhelpers.paginate import Page
from sqlalchemy.orm import class_mapper, object_session
from formalchemy.fields import _pk
from formalchemy.fields import _stringify
from formalchemy import Grid, FieldSet
from formalchemy.i18n import get_translator
from formalchemy.fields import Field
from formalchemy import fatypes

try:
    from formalchemy.ext.couchdb import Document
except ImportError:
    Document = None

import simplejson as json

def model_url(*args, **kwargs):
    """wrap ``pylons.url`` and take care about ``model_name`` in
    ``pylons.routes_dict`` if any"""
    if 'model_name' in request.environ['pylons.routes_dict'] and 'model_name' not in kwargs:
        kwargs['model_name'] = request.environ['pylons.routes_dict']['model_name']
    return url(*args, **kwargs)

class Session(object):
    """A abstract class to implement other backend than SA"""
    def add(self, record):
        """add a record"""
    def update(self, record):
        """update a record"""
    def delete(self, record):
        """delete a record"""
    def commit(self):
        """commit transaction"""

class _RESTController(object):
    """A RESTful Controller bound to a model"""

    template = '/forms/restfieldset.mako'
    engine = prefix_name = None
    FieldSet = FieldSet
    Grid = Grid
    pager_args = dict(link_attr={'class': 'ui-pager-link ui-state-default ui-corner-all'},
                      curpage_attr={'class': 'ui-pager-curpage ui-state-highlight ui-corner-all'})

    @property
    def model_name(self):
        """return ``model_name`` from ``pylons.routes_dict``"""
        return request.environ['pylons.routes_dict'].get('model_name', None)

    def Session(self):
        """return a Session object. You **must** override this."""
        return Session()

    def get_model(self):
        """return SA mapper class. You **must** override this."""
        raise NotImplementedError()

    def sync(self, fs, id=None):
        """sync a record. If ``id`` is None add a new record else save current one.

        Default is::

            S = self.Session()
            if id:
                S.merge(fs.model)
            else:
                S.add(fs.model)
            S.commit()
        """
        S = self.Session()
        if id:
            try:
                S.merge(fs.model)
            except AttributeError:
                # SA <= 0.5.6
                S.update(fs.model)
        else:
            S.add(fs.model)
        S.commit()

    def breadcrumb(self, action=None, fs=None, id=None, **kwargs):
        """return items to build the breadcrumb"""
        items = []
        if self.prefix_name:
            items.append((url(self.prefix_name), self.prefix_name))
        if self.model_name:
            items.append((model_url(self.collection_name), self.model_name))
        elif not self.prefix_name and 'is_grid' not in kwargs:
            items.append((model_url(self.collection_name), self.collection_name))
        if id and hasattr(fs.model, '__unicode__'):
            items.append((model_url(self.member_name, id=id), u'%s' % fs.model))
        elif id:
            items.append((model_url(self.member_name, id=id), id))
        if action in ('edit', 'new'):
            items.append((None, action))
        return items

    def render(self, format='html', **kwargs):
        """render the form as html or json"""
        if format != 'html':
            meth = getattr(self, 'render_%s_format' % format, None)
            if meth is not None:
                return meth(**kwargs)
            else:
                abort(404)
        kwargs.update(model_name=self.model_name or self.member_name,
                      prefix_name=self.prefix_name,
                      collection_name=self.collection_name,
                      member_name=self.member_name,
                      breadcrumb=self.breadcrumb(**kwargs),
                      F_=get_translator())
        self.update_resources()
        if self.engine:
            return self.engine.render(self.template, **kwargs)
        else:
            return render(self.template, extra_vars=kwargs)

    def render_grid(self, format='html', **kwargs):
        """render the grid as html or json"""
        return self.render(format=format, is_grid=True, **kwargs)

    def render_json_format(self, fs=None, **kwargs):
        response.content_type = 'text/javascript'
        if fs:
            try:
                fields = fs.jsonify()
            except AttributeError:
                fields = dict([(field.renderer.name, field.model_value) for field in fs.render_fields.values()])
            data = dict(fields=fields)
            pk = _pk(fs.model)
            if pk:
                data['item_url'] = model_url(self.member_name, id=pk)
        else:
            data = {}
        data.update(kwargs)
        return json.dumps(data)

    def render_xhr_format(self, fs=None, **kwargs):
        response.content_type = 'text/html'
        if fs is not None:
            if 'field' in request.GET:
                field_name = request.GET.get('field')
                fields = fs.render_fields
                if field_name in fields:
                    field = fields[field_name]
                    return field.render()
                else:
                    abort(404)
            return fs.render()
        return ''

    def get_page(self, **kwargs):
        """return a ``webhelpers.paginate.Page`` used to display ``Grid``.

        Default is::

            S = self.Session()
            query = S.query(self.get_model())
            kwargs = request.environ.get('pylons.routes_dict', {})
            return Page(query, page=int(request.GET.get('page', '1')), **kwargs)
        """
        S = self.Session()
        options = dict(collection=S.query(self.get_model()), page=int(request.GET.get('page', '1')))
        options.update(request.environ.get('pylons.routes_dict', {}))
        options.update(kwargs)
        collection = options.pop('collection')
        return Page(collection, **options)

    def get(self, id=None):
        """return correct record for ``id`` or a new instance.

        Default is::

            S = self.Session()
            model = self.get_model()
            if id:
                model = S.query(model).get(id)
            else:
                model = model()
            return model or abort(404)

        """
        S = self.Session()
        model = self.get_model()
        if id:
            model = S.query(model).get(id)
        return model or abort(404)

    def get_fieldset(self, id=None):
        """return a ``FieldSet`` object bound to the correct record for ``id``.

        Default is::

            fs = self.FieldSet(self.get(id))
            fs.engine = fs.engine or self.engine
            return fs
        """
        fs = self.FieldSet(self.get(id))
        fs.engine = fs.engine or self.engine
        return fs

    def get_add_fieldset(self):
        """return a ``FieldSet`` used for add form.

        Default is::

            fs = self.get_fieldset()
            for field in fs.render_fields.itervalues():
                if field.is_readonly():
                    del fs[field.name]
            return fs
        """
        fs = self.get_fieldset()
        for field in fs.render_fields.itervalues():
            if field.is_readonly():
                del fs[field.name]
        return fs

    def get_grid(self):
        """return a Grid object

        Default is::

            grid = self.Grid(self.get_model())
            grid.engine = self.engine
            self.update_grid(grid)
            return grid
        """
        grid = self.Grid(self.get_model())
        grid.engine = self.engine
        self.update_grid(grid)
        return grid


    def update_grid(self, grid):
        """Add edit and delete buttons to ``Grid``"""
        try:
            grid.edit
        except AttributeError:
            def edit_link():
                return lambda item: '''
                <form action="%(url)s" method="GET" class="ui-grid-icon ui-widget-header ui-corner-all">
                <input type="submit" class="ui-grid-icon ui-icon ui-icon-pencil" title="%(label)s" value="%(label)s" />
                </form>
                ''' % dict(url=model_url('edit_%s' % self.member_name, id=_pk(item)),
                            label=get_translator()('edit'))
            def delete_link():
                return lambda item: '''
                <form action="%(url)s" method="POST" class="ui-grid-icon ui-state-error ui-corner-all">
                <input type="submit" class="ui-icon ui-icon-circle-close" title="%(label)s" value="%(label)s" />
                <input type="hidden" name="_method" value="DELETE" />
                </form>
                ''' % dict(url=model_url(self.member_name, id=_pk(item)),
                           label=get_translator()('delete'))
            grid.append(Field('edit', fatypes.String, edit_link()))
            grid.append(Field('delete', fatypes.String, delete_link()))
            grid.readonly = True

    def update_resources(self):
        """A hook to add some fanstatic resources"""
        pass

    def index(self, format='html', **kwargs):
        """REST api"""
        page = self.get_page()
        fs = self.get_grid()
        fs = fs.bind(instances=page)
        fs.readonly = True
        if format == 'json':
            values = []
            for item in page:
                pk = _pk(item)
                fs._set_active(item)
                value = dict(id=pk,
                             item_url=model_url(self.member_name, id=pk))
                if 'jqgrid' in request.GET:
                    fields = [_stringify(field.render_readonly()) for field in fs.render_fields.values()]
                    value['cell'] = [pk] + fields
                else:
                    value.update(dict([(field.key, field.model_value) for field in fs.render_fields.values()]))
                values.append(value)
            return self.render_json_format(rows=values,
                                           records=len(values),
                                           total=page.page_count,
                                           page=page.page)
        if 'pager' not in kwargs:
            pager = page.pager(**self.pager_args)
        else:
            pager = kwargs.pop('pager')
        return self.render_grid(format=format, fs=fs, id=None, pager=pager)

    def create(self, format='html', **kwargs):
        """REST api"""
        fs = self.get_add_fieldset()

        if format == 'json' and request.method == 'PUT':
            data = json.load(request.body_file)
        else:
            data = request.POST

        try:
            fs = fs.bind(data=data, session=self.Session())
        except:
            # non SA forms
            fs = fs.bind(self.get_model(), data=data, session=self.Session())
        if fs.validate():
            fs.sync()
            self.sync(fs)
            if format == 'html':
                if request.is_xhr:
                    response.content_type = 'text/plain'
                    return ''
                redirect(model_url(self.collection_name))
            else:
                fs.rebind(fs.model, data=None)
                return self.render(format=format, fs=fs)
        return self.render(format=format, fs=fs, action='new', id=None)

    def delete(self, id, format='html', **kwargs):
        """REST api"""
        record = self.get(id)
        if record:
            S = self.Session()
            S.delete(record)
            S.commit()
        if format == 'html':
            if request.is_xhr:
                response.content_type = 'text/plain'
                return ''
            redirect(model_url(self.collection_name))
        return self.render(format=format, id=id)

    def show(self, id=None, format='html', **kwargs):
        """REST api"""
        fs = self.get_fieldset(id=id)
        fs.readonly = True
        return self.render(format=format, fs=fs, action='show', id=id)

    def new(self, format='html', **kwargs):
        """REST api"""
        fs = self.get_add_fieldset()
        fs = fs.bind(session=self.Session())
        return self.render(format=format, fs=fs, action='new', id=None)

    def edit(self, id=None, format='html', **kwargs):
        """REST api"""
        fs = self.get_fieldset(id)
        return self.render(format=format, fs=fs, action='edit', id=id)

    def update(self, id, format='html', **kwargs):
        """REST api"""
        fs = self.get_fieldset(id)
        if format == 'json' and request.method == 'PUT' and '_method' not in request.GET:
            data = json.load(request.body_file)
        else:
            data = request.POST
        fs = fs.bind(data=data)
        if fs.validate():
            fs.sync()
            self.sync(fs, id)
            if format == 'html':
                if request.is_xhr:
                    response.content_type = 'text/plain'
                    return ''
                redirect(model_url(self.member_name, id=id))
            else:
                return self.render(format=format, fs=fs, status=0)
        if format == 'html':
            return self.render(format=format, fs=fs, action='edit', id=id)
        else:
            return self.render(format=format, fs=fs, status=1)

def RESTController(cls, member_name, collection_name):
    """wrap a controller with :class:`~formalchemy.ext.pylons.controller._RESTController`"""
    return type(cls.__name__, (cls, _RESTController),
                dict(member_name=member_name, collection_name=collection_name))

class _ModelsController(_RESTController):
    """A RESTful Controller bound to more tha one model. The ``model`` and
    ``forms`` attribute can be a list of object or a module"""

    engine = None
    model = forms = None

    _static_app = StaticURLParser(os.path.join(os.path.dirname(__file__), 'resources'))

    def Session(self):
        return meta.Session

    def models(self, format='html', **kwargs):
        """Models index page"""
        models = self.get_models()
        return self.render(models=models, format=format)

    def static(self):
        """Serve static files from the formalchemy package"""
        return self._static_app(request.environ, self.start_response)

    def get_models(self):
        """return a dict containing all model names as key and url as value"""
        models = {}
        if isinstance(self.model, list):
            for model in self.model:
                key = model.__name__
                models[key] = model_url(self.collection_name, model_name=key)
        else:
            for key, obj in self.model.__dict__.iteritems():
                if not key.startswith('_'):
                    if Document is not None:
                        try:
                            if issubclass(obj, Document):
                                models[key] = model_url(self.collection_name, model_name=key)
                                continue
                        except:
                            pass
                    try:
                        class_mapper(obj)
                    except:
                        continue
                    if not isinstance(obj, type):
                        continue
                    models[key] = model_url(self.collection_name, model_name=key)
        return models

    def get_model(self):
        if isinstance(self.model, list):
            for model in self.model:
                if model.__name__ == self.model_name:
                    return model
        elif hasattr(self.model, self.model_name):
            return getattr(self.model, self.model_name)
        abort(404)

    def get_fieldset(self, id):
        if self.forms and hasattr(self.forms, self.model_name):
            fs = getattr(self.forms, self.model_name)
            fs.engine = fs.engine or self.engine
            return id and fs.bind(self.get(id)) or fs
        return _RESTController.get_fieldset(self, id)

    def get_add_fieldset(self):
        if self.forms and hasattr(self.forms, '%sAdd' % self.model_name):
            fs = getattr(self.forms, '%sAdd' % self.model_name)
            fs.engine = fs.engine or self.engine
            return fs
        return self.get_fieldset(id=None)

    def get_grid(self):
        model_name = self.model_name
        if self.forms and hasattr(self.forms, '%sGrid' % model_name):
            g = getattr(self.forms, '%sGrid' % model_name)
            g.engine = g.engine or self.engine
            g.readonly = True
            self.update_grid(g)
            return g
        return _RESTController.get_grid(self)

def ModelsController(cls, prefix_name, member_name, collection_name):
    """wrap a controller with :class:`~formalchemy.ext.pylons.controller._ModelsController`"""
    return type(cls.__name__, (cls, _ModelsController),
                dict(prefix_name=prefix_name, member_name=member_name, collection_name=collection_name))


########NEW FILE########
__FILENAME__ = maps
# -*- coding: utf-8 -*-
import pylons
import logging
log = logging.getLogger(__name__)

try:
    version = pylons.__version__.split('.')
except AttributeError:
    version = ['0', '6']

def format(environ, result):
    if environ.get('HTTP_ACCEPT', '') == 'application/json':
        result['format'] = 'json'
        return True
    elif 'format' not in result:
        result['format'] = 'html'
    return True

def admin_map(map, controller, url='%s'):
    """connect the admin controller `cls` under the given `url`"""
    log.info('connecting %s to %s' % (url, controller))
    map.connect('static_contents', '%s/static_contents/{id}' % url, controller=controller, action='static')

    map.connect('admin', '%s' % url,
        controller=controller, action='index')

    map.connect('formatted_admin', '%s.{format}' % url,
        controller=controller, action='index')

    map.connect("models", "%s/{modelname}" % url,
        controller=controller, action="edit", id=None, format='html',
        conditions=dict(method=["POST"], function=format))

    map.connect("models", "%s/{modelname}" % url,
        controller=controller, action="list",
        conditions=dict(method=["GET"], function=format))

    map.connect("formatted_models", "%s/{modelname}.{format}" % url,
        controller=controller, action="list",
        conditions=dict(method=["GET"]))

    map.connect("new_model", "%s/{modelname}/new" % url,
        controller=controller, action="edit", id=None,
        conditions=dict(method=["GET"]))

    map.connect("formatted_new_model", "%s/{modelname}/new.{format}" % url,
        controller=controller, action="edit", id=None,
        conditions=dict(method=["GET"]))

    map.connect("%s/{modelname}/{id}" % url,
        controller=controller, action="edit",
        conditions=dict(method=["PUT"], function=format))

    map.connect("%s/{modelname}/{id}" % url,
        controller=controller, action="delete",
        conditions=dict(method=["DELETE"]))

    map.connect("edit_model", "%s/{modelname}/{id}/edit" % url,
        controller=controller, action="edit",
        conditions=dict(method=["GET"]))

    map.connect("formatted_edit_model", "%s/{modelname}/{id}.{format}/edit" % url,
        controller=controller, action="edit",
        conditions=dict(method=["GET"]))

    map.connect("view_model", "%s/{modelname}/{id}" % url,
        controller=controller, action="edit",
        conditions=dict(method=["GET"], function=format))

    map.connect("formatted_view_model", "%s/{modelname}/{id}.{format}" % url,
        controller=controller, action="edit",
        conditions=dict(method=["GET"]))


########NEW FILE########
__FILENAME__ = pastertemplate
# -*- coding: utf-8 -*-
try:
    from tempita import paste_script_template_renderer
    from paste.script.templates import Template, var
except ImportError:
    class PylonsTemplate(object):
        pass
else:
    class PylonsTemplate(Template):
        _template_dir = ('formalchemy', 'paster_templates/pylons_fa')
        summary = 'Pylons application template with formalchemy support'
        required_templates = ['pylons']
        template_renderer = staticmethod(paste_script_template_renderer)
        vars = [
            var('admin_controller', 'Add formalchemy\'s admin controller',
                default=False),
            ]


########NEW FILE########
__FILENAME__ = rdf
# -*- coding: utf-8 -*-
__doc__ = """This module provides an experimental subclass of
:class:`~formalchemy.forms.FieldSet` to support RDFAlchemy_.

.. _RDFAlchemy: http://www.openvest.com/trac/wiki/RDFAlchemy

Usage
=====

    >>> from rdfalchemy.samples.company import Company
    >>> c = Company(stockDescription='description', symbol='FA',
    ...             cik='cik', companyName='fa corp',
    ...             stock=['value1'])

    >>> fs = FieldSet(Company)
    >>> fs.configure(options=[fs.stock.set(options=['value1', 'value2'])])
    >>> fs = fs.bind(c)
    >>> fs.stock.value
    ['value1']

    >>> print fs.render().strip() # doctest: +ELLIPSIS +NORMALIZE_WHITESPACE
    <div>
      <label class="field_opt" for="Company--stockDescription">Stockdescription</label>
      <input id="Company--stockDescription" name="Company--stockDescription" type="text" value="description" />
    </div>
    ...
    <div>
      <label class="field_opt" for="Company--stock">Stock</label>
      <select id="Company--stock" name="Company--stock">
    <option selected="selected" value="value1">value1</option>
    <option value="value2">value2</option>
    </select>
    </div>
    

    >>> fs = Grid(Company, [c])
    >>> fs.configure(options=[fs.stock.set(options=['value1', 'value2'])], readonly=True)
    >>> print fs.render().strip() #doctest: +NORMALIZE_WHITESPACE
    <thead>
      <tr>
          <th>Stockdescription</th>
          <th>Companyname</th>
          <th>Cik</th>
          <th>Symbol</th>
          <th>Stock</th>
      </tr>
    </thead>
    <tbody>
      <tr class="even">
        <td>description</td>
        <td>fa corp</td>
        <td>cik</td>
        <td>FA</td>
        <td>value1</td>
      </tr>
    </tbody>
    

"""
from formalchemy.forms import FieldSet as BaseFieldSet
from formalchemy.tables import Grid as BaseGrid
from formalchemy.fields import Field as BaseField
from formalchemy.fields import TextFieldRenderer, SelectFieldRenderer
from formalchemy.forms import SimpleMultiDict
from formalchemy import fields
from formalchemy import validators
from formalchemy import fatypes
from sqlalchemy.util import OrderedDict
from rdfalchemy import descriptors, rdfSubject
import rdflib

from datetime import datetime


__all__ = ['Field', 'FieldSet', 'RdfFieldRenderer']


class Session(object):
    """A SA like Session to implement rdf"""
    def add(self, record):
        """add a record"""
        record.save()
    def update(self, record):
        """update a record"""
        record.save()
    def delete(self, record):
        """delete a record"""
    def query(self, model, *args, **kwargs):
        raise NotImplementedError()
    def commit(self):
        """do nothing since there is no transaction in couchdb"""
    remove = commit

class Field(BaseField):
    """"""

    @property
    def value(self):
        if not self.is_readonly() and self.parent.data is not None:
            v = self._deserialize()
            if v is not None:
                return v
        return getattr(self.model, self.name)

    @property
    def model_value(self):
        return getattr(self.model, self.name)
    raw_value = model_value

    def sync(self):
        """Set the attribute's value in `model` to the value given in `data`"""
        if not self.is_readonly():
            deser = self._deserialize()
            orig = getattr(self.model, self.name)
            if (orig != deser):
                if isinstance(orig, list):
                    # first remove the original triples, instead of doing sophisticated
                    # set manipulations
                    setattr(self.model, self.name, [])
                setattr(self.model, self.name, deser)


class FieldSet(BaseFieldSet):
    __sa__ = False
    _mapping = {
            descriptors.rdfSingle: fatypes.String,
            descriptors.rdfMultiple: fatypes.List,
            descriptors.rdfList: fatypes.List,
        }

    def __init__(self, model, **kwargs):
        BaseFieldSet.__init__(self, model, **kwargs)
        BaseFieldSet.rebind(self, model, data=kwargs.get('data', None))
        for k, v in model.__dict__.iteritems():
            if not k.startswith('_'):
                descriptor = type(v)
                t = self._mapping.get(descriptor)
                if t:
                    self.append(Field(name=k, type=t))

    def bind(self, model=None, session=None, data=None):
        """Bind to an instance"""
        if not (model or session or data):
            raise Exception('must specify at least one of {model, session, data}')
        if not model:
            if not self.model:
                raise Exception('model must be specified when none is already set')
            else:
                model = self.model()
        # copy.copy causes a stacktrace on python 2.5.2/OSX + pylons.  unable to reproduce w/ simpler sample.
        mr = object.__new__(self.__class__)
        mr.__dict__ = dict(self.__dict__)
        # two steps so bind's error checking can work
        mr.rebind(model, session, data)
        mr._fields = OrderedDict([(key, renderer.bind(mr)) for key, renderer in self._fields.iteritems()])
        if self._render_fields:
            mr._render_fields = OrderedDict([(field.key, field) for field in
                                             [field.bind(mr) for field in self._render_fields.itervalues()]])
        return mr

    def rebind(self, model, session=None, data=None):
        if model:
            if isinstance(model, type):
                try:
                    model = model()
                except:
                    raise Exception('%s appears to be a class, not an instance, but FormAlchemy cannot instantiate it.  (Make sure all constructor parameters are optional!)' % model)
            self.model = model
            self._bound_pk = None
        if data is None:
            self.data = None
        elif hasattr(data, 'getall') and hasattr(data, 'getone'):
            self.data = data
        else:
            try:
                self.data = SimpleMultiDict(data)
            except:
                raise Exception('unsupported data object %s.  currently only dicts and Paste multidicts are supported' % self.data)

class Grid(BaseGrid, FieldSet):
    def __init__(self, cls, instances=None, **kwargs):
        FieldSet.__init__(self, cls, **kwargs)
        self.rows = instances or []
        self.readonly = False
        self._errors = {}

    def _get_errors(self):
        return self._errors

    def _set_errors(self, value):
        self._errors = value
    errors = property(_get_errors, _set_errors)

    def rebind(self, instances=None, session=None, data=None):
        FieldSet.rebind(data=data)
        if instances is not None:
            self.rows = instances

    def _set_active(self, instance, session=None):
        FieldSet.rebind(self, instance, session or self.session, self.data)


class RdfFieldRenderer(TextFieldRenderer):
    """render a rdf field  as a text field"""

    def stringify_value(self, v):
        return v.n3()

    def _deserialize(self, data):
        """ data has the pattern "<uri>" """
        uri = data[1:-1]
        # We have to retrieve the type to rebuild the object
        attr = self.__dict__['field']
        # Be careful when orig = None !!!!!
        orig = getattr(attr.model, attr.name)
        if None == orig:
            return rdfSubject(rdflib.term.URIRef(uri))
        elif isinstance(orig, list):
            # rdfalchemy mapper gives me the solution
            rt = attr.model.__class__.__dict__[attr.name].range_type
            from rdfalchemy.orm import mapper
            alch_map = mapper()
            try:
                cls = alch_map[str(rt)]
                return cls(rdflib.term.URIRef(uri))
            except:
                rdfSubject(rdflib.term.URIRef(uri))
        else:
            return type(orig)(rdflib.term.URIRef(uri))


class RdfSelectFieldRenderer(SelectFieldRenderer, RdfFieldRenderer):

    def _serialized_value(self):
        if self.name not in self.params:
            if self.field.is_collection:
                return []
            return None
        return RdfFieldRenderer._serialized_value(self)

    def render_readonly(self, options=None, **kwargs):
        """render a string representation of the field value.
                Try to retrieve a value from `options`
        """
        if not options or self.field.is_scalar_relation:
            return RdfFieldRenderer.render_readonly(self)
        super(RdfSelectFieldRenderer, self).render_readonly(options, **kwargs)





def test_sync():
    from rdfalchemy.samples.company import Company
    c = Company(stockDescription='description', symbol='FA',
                cik='cik', companyName='fa corp',
                stock=['value1'])

    fs = FieldSet(Company)
    fs.configure(include=[fs.companyName, fs.stock.set(options=['value1', 'value2'])])
    fs = fs.bind(c, data={'Company--companyName':'new name', 'Company--stock':'value2'})
    assert fs.stock.raw_value == ['value1']

    fs.validate()
    fs.sync()

    assert fs.stock.raw_value == ['value2']


########NEW FILE########
__FILENAME__ = fatypes
# This module is part of FormAlchemy and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

from sqlalchemy.types import TypeEngine, Integer, Float, String, Unicode, Text, Boolean, Date, DateTime, Time, Numeric, Interval

try:
    from sqlalchemy.types import LargeBinary
except ImportError:
    # SA < 0.6
    from sqlalchemy.types import Binary as LargeBinary

sa_types = set([Integer, Float, String, Unicode, Text, LargeBinary, Boolean, Date, DateTime, Time, Numeric, Interval])

class HTML5Email(String):
    """HTML5 email field"""

class HTML5Url(String):
    """HTML5 url field"""

class HTML5Number(Integer):
    """HTML5 number field"""

class HTML5Color(String):
    """HTML5 color field"""

class HTML5DateTime(DateTime):
    """HTML5 datetime field"""

class HTML5Date(Date):
    """HTML5 date field"""

class HTML5Time(Time):
    """HTML5 time field"""

class List(TypeEngine):
    def get_dbapi_type(self):
        raise NotImplementedError()

class Set(TypeEngine):
    def get_dbapi_type(self):
        raise NotImplementedError()


########NEW FILE########
__FILENAME__ = fields
# Copyright (C) 2007 Alexandre Conrad, alexandre (dot) conrad (at) gmail (dot) com
#
# This module is part of FormAlchemy and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

import cgi
import logging
logger = logging.getLogger('formalchemy.' + __name__)

from copy import copy, deepcopy
import datetime
import warnings

from sqlalchemy.orm.interfaces import MANYTOMANY
from sqlalchemy.orm.interfaces import ONETOMANY
from sqlalchemy.orm import class_mapper, Query
from sqlalchemy.orm.attributes import ScalarAttributeImpl, ScalarObjectAttributeImpl, CollectionAttributeImpl
from sqlalchemy.orm.properties import CompositeProperty, ColumnProperty
try:
    from sqlalchemy import exc as sqlalchemy_exceptions
except ImportError:
    from sqlalchemy import exceptions as sqlalchemy_exceptions
from sqlalchemy.orm import object_session
from formalchemy import helpers as h
from formalchemy import fatypes, validators
from formalchemy.exceptions import FieldNotFoundError
from formalchemy import config
from formalchemy.i18n import get_translator
from formalchemy.i18n import _

__all__ = ['Field', 'FieldRenderer',
           'TextFieldRenderer', 'TextAreaFieldRenderer',
           'PasswordFieldRenderer', 'HiddenFieldRenderer',
           'DateFieldRenderer', 'TimeFieldRenderer',
           'DateTimeFieldRenderer',
           'CheckBoxFieldRenderer', 'CheckBoxSet',
           'deserialize_once']



########################## RENDERER STUFF ############################



def _stringify(k, null_value=u''):
    if k is None:
        return null_value
    if isinstance(k, str):
        return unicode(k, config.encoding)
    elif isinstance(k, unicode):
        return k
    elif hasattr(k, '__unicode__'):
        return unicode(k)
    elif isinstance(k, datetime.timedelta):
        return '%s.%s' % (k.days, k.seconds)
    else:
        return unicode(str(k), config.encoding)

def _htmlify(k, null_value=u''):
    if hasattr(k, '__html__'):
        try:
            return h.literal(k.__html__())
        except TypeError:
            # not callable. skipping
            pass
    return _stringify(k, null_value)

class _NoDefault(object):
    def __repr__(self):
        return '<NoDefault>'
NoDefault = _NoDefault()
del _NoDefault

def deserialize_once(func):
    """Simple deserialization caching decorator.

    To be used on a Renderer object's `deserialize` function, to cache it's
    result while it's being called once for ``validate()`` and another time
    when doing ``sync()``.
    """
    def cache(self, *args, **kwargs):
        if hasattr(self, '_deserialization_result'):
            return self._deserialization_result

        self._deserialization_result = func(self, *args, **kwargs)

        return self._deserialization_result
    return cache

class FieldRenderer(object):
    """
    This should be the super class of all Renderer classes.

    Renderers generate the html corresponding to a single Field,
    and are also responsible for deserializing form data into
    Python objects.

    Subclasses should override `render` and `deserialize`.
    See their docstrings for details.
    """

    def __init__(self, field):
        self.field = field
        assert isinstance(self.field, AbstractField)

    @property
    def name(self):
        """Name of rendered input element.

        The `name` of a field will always look like:
          [fieldset_prefix-]ModelName-[pk]-fieldname

        The fieldset_prefix is defined when instantiating the
        `FieldSet` object, by passing the `prefix=` keyword argument.

        The `ModelName` is taken by introspection from the model
        passed in at that same moment.

        The `pk` is the primary key of the object being edited.
        If you are creating a new object, then the `pk` is an
        empty string.

        The `fieldname` is, well, the field name.

        .. note::
         This method as the direct consequence that you can not `create`
         two objects of the same class, using the same FieldSet, on the
         same page. You can however, create more than one object
         of a certain class, provided that you create multiple FieldSet
         instances and pass the `prefix=` keyword argument.

         Otherwise, FormAlchemy deals very well with editing multiple
         existing objects of same/different types on the same page,
         without any name clash. Just be careful with multiple object
         creation.

        When creating your own Renderer objects, use `self.name` to
        get the field's `name` HTML attribute, both when rendering
        and deserializing.
        """
        clsname = self.field.model.__class__.__name__
        pk = self.field.parent._bound_pk
        assert pk != ''
        if isinstance(pk, basestring) or not hasattr(pk, '__iter__'):
            pk_string = _stringify(pk)
        else:
            # remember to use a delimiter that can be used in the DOM (specifically, no commas).
            # we don't have to worry about escaping the delimiter, since we never try to
            # deserialize the generated name.  All we care about is generating unique
            # names for a given model's domain.
            pk_string = u'_'.join([_stringify(k) for k in pk])

        components = dict(model=clsname, pk=pk_string, name=self.field.name)
        name = self.field.parent._format % components
        if self.field.parent._prefix is not None:
            return u'%s-%s' % (self.field.parent._prefix, name)
        return name

    @property
    def value(self):
        """
        Submitted value, or field value converted to string.
        Return value is always either None or a string.
        """
        if not self.field.is_readonly() and self.params is not None:
            # submitted value.  do not deserialize here since that requires valid data, which we might not have
            try:
                v = self._serialized_value()
            except FieldNotFoundError, e:
                v = None
        else:
            v = None
        # empty field will be '' -- use default value there, too
        if v:
            return v

        value = self.field.model_value
        if value is None:
            return None
        if self.field.is_collection:
            return [self.stringify_value(v) for v in value]
        else:
            return self.stringify_value(value)

    @property
    def _value(self):
        warnings.warn('FieldRenderer._value is deprecated. Use '\
                          'FieldRenderer.value instead')
        return self.value

    @property
    def raw_value(self):
        """return fields field.raw_value (mean real objects, not ForeignKeys)
        """
        return self.field.raw_value

    @property
    def request(self):
        """return the ``request`` bound to the
        :class:`~formalchemy.forms.FieldSet`` during
        :func:`~formalchemy.forms.FieldSet.bind`"""
        return self.field.parent._request

    def get_translator(self, **kwargs):
        """return a GNUTranslations object in the most convenient way
        """
        if 'F_' in kwargs:
            return kwargs.pop('F_')
        if 'lang' in kwargs:
            lang = kwargs.pop('lang')
        else:
            lang = 'en'
        return get_translator(lang=lang, request=self.request)

    def render(self, **kwargs):
        """
        Render the field.  Use `self.name` to get a unique name for the
        input element and id.  `self.value` may also be useful if
        you are not rendering multiple input elements.

        When rendering, you can verify `self.errors` to know
        if you are rendering a new form, or re-displaying a form with
        errors. Knowing that, you could select the data either from
        the model, or the web form submission.
        """
        raise NotImplementedError()

    def render_readonly(self, **kwargs):
        """render a string representation of the field value"""
        value = self.raw_value
        if value is None:
            return ''
        if isinstance(value, list):
            return h.literal(', ').join([self.stringify_value(item, as_html=True) for item in value])
        if isinstance(value, unicode):
            return value
        return self.stringify_value(value, as_html=True)

    @property
    def params(self):
        """This gives access to the POSTed data, as received from
        the web user. You should call `.getone`, or `.getall` to
        retrieve a single value or multiple values for a given
        key.

        For example, when coding a renderer, you'd use:

        .. sourcecode:: py

           vals = self.params.getall(self.name)

        to catch all the values for the renderer's form entry.
        """
        return self.field.parent.data

    @property
    def _params(self):
        warnings.warn('FieldRenderer._params is deprecated. Use '\
                          'FieldRenderer.params instead')
        return self.params

    def _serialized_value(self):
        """
        Returns the appropriate value to deserialize for field's
        datatype, from the user-submitted data.  Only called
        internally, so, if you are overriding `deserialize`,
        you can use or ignore `_serialized_value` as you please.

        This is broken out into a separate method so multi-input
        renderers can stitch their values back into a single one
        to have that can be handled by the default deserialize.

        Do not attempt to deserialize here; return value should be a
        string (corresponding to the output of `str` for your data
        type), or for a collection type, a a list of strings,
        or None if no value was submitted for this renderer.

        The default _serialized_value returns the submitted value(s)
        in the input element corresponding to self.name.
        """
        try:
            if self.field.is_collection:
                return self.params.getall(self.name)
            return self.params.getone(self.name)
        except KeyError:
            raise FieldNotFoundError('%s not found in %r' % (self.name, self.params))

    def deserialize(self):
        """Turns the user-submitted data into a Python value.

        The raw data received from the web can be accessed via
        `self.params`. This dict-like object usually accepts the
        `getone()` and `getall()` method calls.

        For SQLAlchemy
        collections, return a list of primary keys, and !FormAlchemy
        will take care of turning that into a list of objects.
        For manually added collections, return a list of values.

        You will need to override this in a child Renderer object
        if you want to mangle the data from your web form, before
        it reaches your database model. For example, if your render()
        method displays a select box filled with items you got from a
        CSV file or another source, you will need to decide what to do
        with those values when it's time to save them to the database
        -- or is this field going to determine the hashing algorithm
        for your password ?.

        This function should return the value that is going to be
        assigned to the model *and* used in the place of the model
        value if there was an error with the form.

        .. note::
         Note that this function will be called *twice*, once when
         the fieldset is `.validate()`'d -- with it's value only tested,
         and a second time when the fieldset is `.sync()`'d -- and it's
         value assigned to the model. Also note that deserialize() can
         also raise a ValidationError() exception if it finds some
         errors converting it's values.

        If calling this function twice poses a problem to your logic, for
        example, if you have heavy database queries, or temporary objects
        created in this function, consider using the ``deserialize_once``
        decorator, provided using:

        .. sourcecode:: py

          from formalchemy.fields import deserialize_once

          @deserialize_once
          def deserialize(self):
              ... my stuff ...
              return calculated_only_once

        Finally, you should only have to override this if you are using custom
        (e.g., Composite) types.
        """
        if self.field.is_collection:
            return [self._deserialize(subdata) for subdata in self._serialized_value()]
        return self._deserialize(self._serialized_value())

    def _deserialize(self, data):
        if isinstance(self.field.type, fatypes.Boolean):
            if isinstance(data, bool):
                 return data
            if data is not None:
                if data.lower() in ['1', 't', 'true', 'yes']: return True
                if data.lower() in ['0', 'f', 'false', 'no']: return False
        if data is None or data == self.field._null_option[1]:
            return None
        if isinstance(self.field.type, fatypes.Interval):
            return datetime.timedelta(validators.float_(data, self))
        if isinstance(self.field.type, fatypes.Integer):
            return validators.integer(data, self)
        if isinstance(self.field.type, fatypes.Float):
            return validators.float_(data, self)
        if isinstance(self.field.type, fatypes.Numeric):
            if self.field.type.asdecimal:
                return validators.decimal_(data, self)
            else:
                return validators.float_(data, self)

        def _date(data):
            if isinstance(data, datetime.date):
                return data
            if data == 'YYYY-MM-DD' or data == '-MM-DD' or not data.strip():
                return None
            try:
                return datetime.date(*[int(st) for st in data.split('-')])
            except:
                raise validators.ValidationError('Invalid date')
        def _time(data):
            if isinstance(data, datetime.time):
                return data
            if data == 'HH:MM:SS' or not data.strip():
                return None
            try:
                return datetime.time(*[int(st) for st in data.split(':')])
            except:
                raise validators.ValidationError('Invalid time')

        if isinstance(self.field.type, fatypes.Date):
            return _date(data)
        if isinstance(self.field.type, fatypes.Time):
            return _time(data)
        if isinstance(self.field.type, fatypes.DateTime):
            if isinstance(data, datetime.datetime):
                return data
            if 'Z' in data:
                data = data.strip('Z')
            if 'T' in data:
                data_date, data_time = data.split('T')
            elif ' ' in data:
                data_date, data_time = data.split(' ')
            else:
                raise validators.ValidationError('Incomplete datetime: %s' % data)
            dt, tm = _date(data_date), _time(data_time)
            if dt is None and tm is None:
                return None
            elif dt is None or tm is None:
                raise validators.ValidationError('Incomplete datetime')
            return datetime.datetime(dt.year, dt.month, dt.day, tm.hour, tm.minute, tm.second)

        return data

    def stringify_value(self, v, as_html=False):
        if as_html:
            return _htmlify(v, null_value=self.field._null_option[1])
        return _stringify(v, null_value=self.field._null_option[1])

    def __repr__(self):
        return '<%s for %r>' % (self.__class__.__name__, self.field)

class EscapingReadonlyRenderer(FieldRenderer):
    """
    In readonly mode, html-escapes the output of the default renderer
    for this field type.  (Escaping is not performed by default because
    it is sometimes useful to have the renderer include raw html in its
    output.  The FormAlchemy admin app extension for Pylons uses this,
    for instance.)
    """
    def __init__(self, field):
        FieldRenderer.__init__(self, field)
        self._renderer = field._get_renderer()(field)

    def render(self, **kwargs):
        return self._renderer.render(**kwargs)

    def render_readonly(self, **kwargs):
        return h.HTML(self._renderer.render_readonly(**kwargs))


class TextFieldRenderer(FieldRenderer):
    """render a field as a text field"""
    @property
    def length(self):
        return self.field.type.length

    def render(self, **kwargs):
        return h.text_field(self.name, value=self.value, maxlength=self.length, **kwargs)


class IntegerFieldRenderer(FieldRenderer):
    """render an integer as a text field"""
    def render(self, **kwargs):
        return h.text_field(self.name, value=self.value, **kwargs)


class FloatFieldRenderer(FieldRenderer):
    """render a float as a text field"""
    def render(self, **kwargs):
        return h.text_field(self.name, value=self.value, **kwargs)

class IntervalFieldRenderer(FloatFieldRenderer):
    """render an interval as a text field"""

    def _deserialize(self, data):
        value = FloatFieldRenderer._deserialize(self, data)
        if isinstance(value, (float, int)):
            return datetime.timedelta(value)
        return value

class PasswordFieldRenderer(TextFieldRenderer):
    """Render a password field"""
    def render(self, **kwargs):
        return h.password_field(self.name, value=self.value, maxlength=self.length, **kwargs)
    def render_readonly(self):
        return '*' * 6

class TextAreaFieldRenderer(FieldRenderer):
    """render a field as a textarea"""
    def render(self, **kwargs):
        if isinstance(kwargs.get('size'), tuple):
            kwargs['size'] = 'x'.join([str(i) for i in kwargs['size']])
        return h.text_area(self.name, content=self.value, **kwargs)


class CheckBoxFieldRenderer(FieldRenderer):
    """render a boolean value as checkbox field"""
    def render(self, **kwargs):
        value = self.value or ''
        return h.check_box(self.name, True,
                           checked=_simple_eval(value.capitalize()),
                           **kwargs)
    def _serialized_value(self):
        if self.name not in self.params:
            return None
        return FieldRenderer._serialized_value(self)
    def deserialize(self):
        if self._serialized_value() is None:
            return False
        return FieldRenderer.deserialize(self)

class FileFieldRenderer(FieldRenderer):
    """render a file input field"""
    remove_label = _('Remove')
    def __init__(self, *args, **kwargs):
        FieldRenderer.__init__(self, *args, **kwargs)
        self._data = None # caches FieldStorage data
        self._filename = None

    def render(self, **kwargs):
        if self.field.model_value:
            checkbox_name = '%s--remove' % self.name
            return h.literal('%s %s %s') % (
                   h.file_field(self.name, **kwargs),
                   h.check_box(checkbox_name),
                   h.label(self.remove_label, for_=checkbox_name))
        else:
            return h.file_field(self.name, **kwargs)

    def get_size(self):
        value = self.raw_value
        if value is None:
            return 0
        return len(value)

    def readable_size(self):
        length = self.get_size()
        if length == 0:
            return '0 KB'
        if length <= 1024:
            return '1 KB'
        if length > 1048576:
            return '%0.02f MB' % (length / 1048576.0)
        return '%0.02f KB' % (length / 1024.0)

    def render_readonly(self, **kwargs):
        """
        render only the binary size in a human readable format but you can
        override it to whatever you want
        """
        return self.readable_size()

    def deserialize(self):
        data = FieldRenderer.deserialize(self)
        if isinstance(data, cgi.FieldStorage):
            if data.filename:
                # FieldStorage can only be read once so we need to cache the
                # value since FA call deserialize during validation and
                # synchronisation
                if self._data is None:
                    self._filename = data.filename
                    self._data = data.file.read()
                data = self._data
            else:
                data = None
        checkbox_name = '%s--remove' % self.name
        if not data and not self.params.has_key(checkbox_name):
            data = getattr(self.field.model, self.field.name)
        return data is not None and data or ''

class DateFieldRenderer(FieldRenderer):
    """Render a date field"""
    @property
    def format(self):
        return config.date_format
    @property
    def edit_format(self):
        return config.date_edit_format
    def render_readonly(self, **kwargs):
        value = self.raw_value
        return value and value.strftime(self.format) or ''
    def _render(self, **kwargs):
        data = self.params
        value = self.field.model_value
        F_ = self.get_translator(**kwargs)
        month_options = [(F_('Month'), 'MM')] + [(F_('month_%02i' % i), str(i)) for i in xrange(1, 13)]
        day_options = [(F_('Day'), 'DD')] + [(i, str(i)) for i in xrange(1, 32)]
        mm_name = self.name + '__month'
        dd_name = self.name + '__day'
        yyyy_name = self.name + '__year'
        is_date_type = isinstance(value, (datetime.datetime, datetime.date, datetime.time))
        values = []
        for key, default in (('month', 'MM'), ('day', 'DD')):
            name = self.name + '__' + key
            v = default
            if data is not None and name in data:
                v = data[name]
            if v.isdigit():
                pass
            elif is_date_type:
                v = getattr(value, key)
            values.append(v)
        mm, dd = values
        # could be blank so don't use and/or construct
        if data is not None and yyyy_name in data:
            yyyy = data[yyyy_name]
        else:
            yyyy = str(self.field.model_value and self.field.model_value.year or 'YYYY')
        selects = dict(
                m=h.select(mm_name, [mm], month_options, **kwargs),
                d=h.select(dd_name, [dd], day_options, **kwargs),
                y=h.text_field(yyyy_name, value=yyyy, maxlength=4, size=4, **kwargs))
        value = [selects.get(l) for l in self.edit_format.split('-')]
        return h.literal('\n').join(value)
    def render(self, **kwargs):
        return h.content_tag('span', self._render(**kwargs), id=self.name)

    def _serialized_value(self):
        return '-'.join([self.params.getone(self.name + '__' + subfield) for subfield in ['year', 'month', 'day']])

class TimeFieldRenderer(FieldRenderer):
    """Render a time field"""
    format = '%H:%M:%S'
    def is_time_type(self):
        return isinstance(self.field.model_value, (datetime.datetime, datetime.date, datetime.time))
    def render_readonly(self, **kwargs):
        value = self.raw_value
        return isinstance(value, datetime.time) and value.strftime(self.format) or ''
    def _render(self, **kwargs):
        data = self.params
        value = self.field.model_value
        hour_options = ['HH'] + [str(i) for i in xrange(24)]
        minute_options = ['MM' ] + [str(i) for i in xrange(60)]
        second_options = ['SS'] + [str(i) for i in xrange(60)]
        hh_name = self.name + '__hour'
        mm_name = self.name + '__minute'
        ss_name = self.name + '__second'
        is_time_type = isinstance(value, (datetime.datetime, datetime.date, datetime.time))
        values = []
        for key, default in (('hour', 'HH'), ('minute', 'MM'), ('second', 'SS')):
            name = self.name + '__' + key
            v = default
            if data is not None and name in data:
                v = data[name]
            if v.isdigit():
                pass
            elif is_time_type:
                v = getattr(value, key)
            values.append(v)
        hh, mm, ss = values
        return h.literal(':').join([
                    h.select(hh_name, [hh], hour_options, **kwargs),
                    h.select(mm_name, [mm], minute_options, **kwargs),
                    h.select(ss_name, [ss], second_options, **kwargs)])
    def render(self, **kwargs):
        return h.content_tag('span', self._render(**kwargs), id=self.name)

    def _serialized_value(self):
        return ':'.join([self.params.getone(self.name + '__' + subfield) for subfield in ['hour', 'minute', 'second']])


class DateTimeFieldRenderer(DateFieldRenderer, TimeFieldRenderer):
    """Render a date time field"""
    format = '%Y-%m-%d %H:%M:%S'
    def render(self, **kwargs):
        return h.content_tag('span', DateFieldRenderer._render(self, **kwargs) + h.literal(' ') + TimeFieldRenderer._render(self, **kwargs), id=self.name)

    def _serialized_value(self):
        return DateFieldRenderer._serialized_value(self) + ' ' + TimeFieldRenderer._serialized_value(self)


class EmailFieldRenderer(FieldRenderer):
    '''
    Render a HTML5 email input field
    '''

    def render(self, **kwargs):
        return h.text_field(self.name, value=self.value, type='email', **kwargs)


class UrlFieldRenderer(FieldRenderer):
    '''
    Render a HTML5 url input field
    '''

    def render(self, **kwargs):
        return h.text_field(self.name, value=self.value, type='url', **kwargs)


class NumberFieldRenderer(IntegerFieldRenderer):
    '''
    Render a HTML5 number input field
    '''

    def render(self, **kwargs):
        return h.text_field(self.name, value=self.value, type='number', **kwargs)


class RangeFieldRenderer(FieldRenderer):
    '''
    Render a HTML5 range input field
    '''

    def render(self, **kwargs):
        return h.text_field(self.name, value=self.value, type='range', **kwargs)


class HTML5DateFieldRenderer(FieldRenderer):
    '''
    Render a HTML5 date input field
    '''

    def render(self, **kwargs):
        return h.text_field(self.name, value=self.value, type='date', **kwargs)

class HTML5DateTimeFieldRenderer(FieldRenderer):
    '''
    Render a HTML5 datetime input field
    '''

    def render(self, **kwargs):
        return h.text_field(self.name, value=self.value, type='datetime', **kwargs)

class LocalDateTimeFieldRenderer(FieldRenderer):
    '''
    Render a HTML5 datetime-local input field.
    '''

    def render(self, **kwargs):
        return h.text_field(self.name, value=self.value, type='datetime-local', **kwargs)


class MonthFieldRender(FieldRenderer):
    '''
    Render a HTML5 month input field.
    '''

    def render(self, **kwargs):
        return h.text_field(self.name, value=self.value, type='month', **kwargs)


class WeekFieldRenderer(FieldRenderer):
    '''
    Render a HTML5 week input field.
    '''

    def render(self, **kwargs):
        return h.text_field(self.name, value=self.value, type='week', **kwargs)


class HTML5TimeFieldRenderer(FieldRenderer):
    '''
    Render a HTML5 time input field.
    '''

    def render(self, **kwargs):
        return h.text_field(self.name, value=self.value, type='time', **kwargs)

class ColorFieldRenderer(FieldRenderer):
    '''
    Render a HTML5 color input field.
    '''

    def render(self, **kwargs):
        return h.text_field(self.name, value=self.value, type='color', **kwargs)


def _extract_options(options):
    if isinstance(options, dict):
        options = options.items()
    for choice in options:
        # Choice is a list/tuple...
        if isinstance(choice, (list, tuple)):
            if len(choice) != 2:
                raise Exception('Options should consist of two items, a name and a value; found %d items in %r' % (len(choice, choice)))
            yield choice
        # ... or just a string.
        else:
            if not isinstance(choice, basestring):
                raise Exception('List, tuple, or string value expected as option (got %r)' % choice)
            yield (choice, choice)


class RadioSet(FieldRenderer):
    """render a field as radio"""
    widget = staticmethod(h.radio_button)
    format = '%(field)s%(label)s'

    def _serialized_value(self):
        if self.name not in self.params:
            return None
        return FieldRenderer._serialized_value(self)

    def _is_checked(self, choice_value, value=NoDefault):
        if value is NoDefault:
            value = self.value
        return value == _stringify(choice_value)

    def render(self, options, **kwargs):
        value = self.value
        self.radios = []
        if callable(options):
            options = options(self.field.parent)
        for i, (choice_name, choice_value) in enumerate(_extract_options(options)):
            choice_id = '%s_%i' % (self.name, i)
            radio = self.widget(self.name, choice_value, id=choice_id,
                                checked=self._is_checked(choice_value, value),
                                **kwargs)
            label = h.label(choice_name, for_=choice_id)
            self.radios.append(h.literal(self.format % dict(field=radio,
                                                            label=label)))
        return h.tag("br").join(self.radios)


class CheckBoxSet(RadioSet):
    widget = staticmethod(h.check_box)

    def _serialized_value(self):
        if self.name not in self.params:
            return []
        return FieldRenderer._serialized_value(self)

    def _is_checked(self, choice_value, value=NoDefault):
        if value is NoDefault:
            value = self.value
        if value is None:
            value = []
        return _stringify(choice_value) in value


class SelectFieldRenderer(FieldRenderer):
    """render a field as select"""
    def _serialized_value(self):
        if self.name not in self.params:
            if self.field.is_collection:
                return []
            return None
        return FieldRenderer._serialized_value(self)

    def render(self, options, **kwargs):
        if callable(options):
            L = _normalized_options(options(self.field.parent))
            if not self.field.is_required() and not self.field.is_collection:
                L.insert(0, self.field._null_option)
        else:
            L = list(options)
        if len(L) > 0:
            if len(L[0]) == 2:
                L = [(k, self.stringify_value(v)) for k, v in L]
            else:
                L = [_stringify(k) for k in L]
        return h.select(self.name, self.value, L, **kwargs)

    def render_readonly(self, options=None, **kwargs):
        """render a string representation of the field value.
           Try to retrieve a value from `options`
        """
        if not options or self.field.is_scalar_relation:
            return FieldRenderer.render_readonly(self)

        value = self.raw_value
        if value is None:
            return ''

        if callable(options):
            L = _normalized_options(options(self.field.parent))
        else:
            L = list(options)

        if len(L) > 0:
            if len(L[0]) == 2:
                L = [(v, k) for k, v in L]
            else:
                L = [(k, _stringify(k)) for k in L]
        D = dict(L)
        if isinstance(value, list):
            return u', '.join([_stringify(D.get(item, item)) for item in value])
        return _stringify(D.get(value, value))


class HiddenFieldRenderer(FieldRenderer):
    """render a field as an hidden field"""
    def render(self, **kwargs):
        return h.hidden_field(self.name, value=self.value, **kwargs)
    def render_readonly(self):
        return ''

def HiddenFieldRendererFactory(cls):
    """A factory to generate a new class to hide an existing renderer"""
    class Renderer(cls, HiddenFieldRenderer):
        def render(self, **kwargs):
            html = super(Renderer, self).render(**kwargs)
            return h.content_tag('div', html, style="display:none;")
        def render_readonly(self):
            return ''
    attrs = dict(__doc__="""Hidden %s renderer""" % cls.__name__)
    renderer = type('Hidden%s' % cls.__name__, (Renderer,), attrs)
    return renderer


HiddenDateFieldRenderer = HiddenFieldRendererFactory(DateFieldRenderer)
HiddenTimeFieldRenderer = HiddenFieldRendererFactory(TimeFieldRenderer)
HiddenDateTimeFieldRenderer = HiddenFieldRendererFactory(DateTimeFieldRenderer)




################## FIELDS STUFF ####################



def _pk_one_column(instance, column):
    try:
        attr = getattr(instance, column.key)
    except AttributeError:
        # FIXME: this is not clean but the only way i've found to retrieve the
        # real attribute name of the primary key.
        # This is needed when you use something like:
        #    id = Column('UGLY_NAMED_ID', primary_key=True)
        # It's a *really* needed feature
        cls = instance.__class__
        for k in instance._sa_class_manager.keys():
            props = getattr(cls, k).property
            if hasattr(props, 'columns'):
                if props.columns[0] is column:
                    attr = getattr(instance, k)
                    break
    return attr

def _pk(instance):
    # Return the value of this instance's primary key, suitable for passing to Query.get().
    # Will be a tuple if PK is multicolumn.
    try:
        columns = class_mapper(type(instance)).primary_key
    except sqlalchemy_exceptions.InvalidRequestError:
        # try to get pk from model attribute
        if hasattr(instance, '_pk'):
            return getattr(instance, '_pk', None) or None
        return None
    if len(columns) == 1:
        return _pk_one_column(instance, columns[0])
    return tuple([_pk_one_column(instance, column) for column in columns])


# see http://code.activestate.com/recipes/364469/ for explanation.
# 2.6 provides ast.literal_eval, but requiring 2.6 is a bit of a stretch for now.
import compiler
class _SafeEval(object):
    def visit(self, node, **kw):
        cls = node.__class__
        meth = getattr(self, 'visit' + cls.__name__, self.default)
        return meth(node, **kw)

    def default(self, node, **kw):
        for child in node.getChildNodes():
            return self.visit(child, **kw)

    visitExpression = default

    def visitName(self, node, **kw):
        if node.name in ['True', 'False', 'None']:
            return eval(node.name)

    def visitConst(self, node, **kw):
        return node.value

    def visitTuple(self, node, **kw):
        return tuple(self.visit(i) for i in node.nodes)

    def visitList(self, node, **kw):
        return [self.visit(i) for i in node.nodes]

def _simple_eval(source):
    """like 2.6's ast.literal_eval, but only does constants, lists, and tuples, for serialized pk eval"""
    if source == '':
        return None
    walker = _SafeEval()
    ast = compiler.parse(source, 'eval')
    return walker.visit(ast)


def _query_options(L):
    """
    Return a list of tuples of `(item description, item pk)`
    for each item in the iterable L, where `item description`
    is the result of str(item) and `item pk` is the item's primary key.
    """
    return [(_stringify(item), _pk(item)) for item in L]


def _normalized_options(options):
    """
    If `options` is an SA query or an iterable of SA instances, it will be
    turned into a list of `(item description, item value)` pairs. Otherwise, a
    copy of the original options will be returned with no further validation.
    """
    if isinstance(options, Query):
        options = options.all()
    if callable(options):
        return options
    i = iter(options)
    try:
        first = i.next()
    except StopIteration:
        return []
    try:
        class_mapper(type(first))
    except:
        return list(options)
    return _query_options(options)


def _foreign_keys(property):
    # 0.4/0.5 compatibility fn
    try:
        return property.foreign_keys
    except AttributeError:
        return [r for l, r in property.synchronize_pairs]


def _model_equal(a, b):
    if not isinstance(a, type):
        a = type(a)
    if not isinstance(b, type):
        b = type(b)
    return a is b


class AbstractField(object):
    """
    Contains the information necessary to render (and modify the rendering of)
    a form field

    Methods taking an `options` parameter will accept several ways of
    specifying those options:

    - an iterable of SQLAlchemy objects; `str()` of each object will be the description, and the primary key the value
    - a SQLAlchemy query; the query will be executed with `all()` and the objects returned evaluated as above
    - an iterable of (description, value) pairs
    - a dictionary of {description: value} pairs

    Options can be "chained" indefinitely because each modification returns a new
    :mod:`Field <formalchemy.fields>` instance, so you can write::

    >>> from formalchemy.tests import FieldSet, User
    >>> fs = FieldSet(User)
    >>> fs.append(Field('foo').dropdown(options=[('one', 1), ('two', 2)]).radio())

    or::

    >>> fs.configure(options=[fs.name.label('Username').readonly()])

    """
    _null_option = (u'None', u'')
    _valide_options = [
            'validate', 'renderer', 'hidden', 'required', 'readonly',
            'null_as', 'label', 'multiple', 'options', 'validators',
            'size', 'instructions', 'metadata', 'html']

    def __init__(self, parent, name=None, type=fatypes.String, **kwattrs):
        # the FieldSet (or any ModelRenderer) owning this instance
        self.parent = parent
        # Renderer for this Field.  this will
        # be autoguessed, unless the user forces it with .dropdown,
        # .checkbox, etc.
        self._renderer = None
        # other render options, such as size, multiple, etc.
        self.render_opts = {}
        # validator functions added with .validate()
        self.validators = []
        # errors found by _validate() (which runs implicit and
        # explicit validators)
        self.errors = []
        self._readonly = False
        # label to use for the rendered field.  autoguessed if not specified by .label()
        self.label_text = None
        # optional attributes to pass to renderers
        self.html_options = {}
        # True iff this Field is a primary key
        self.is_pk = False
        # True iff this Field is a raw foreign key
        self.is_raw_foreign_key = False
        # Field metadata, for customization
        self.metadata = {}
        self.name = name
        self.type = type

    def __deepcopy__(self, memo):
        wrapper = copy(self)
        wrapper.render_opts = dict(self.render_opts)
        wrapper.validators = list(self.validators)
        wrapper.errors = list(self.errors)
        try:
            wrapper._renderer = copy(self._renderer)
        except TypeError: # 2.4 support
            # it's a lambda, safe to just use same referende
            pass
        if hasattr(wrapper._renderer, 'field'):
            wrapper._renderer.field = wrapper
        return wrapper

    @property
    def requires_label(self):
        return not isinstance(self.renderer, HiddenFieldRenderer)

    def query(self, *args, **kwargs):
        """Perform a query in the parent's session"""
        if self.parent.session:
            session = self.parent.session
        else:
            session = object_session(self.model)
        if session:
            return session.query(*args, **kwargs)
        raise Exception(("No session found.  Either bind a session explicitly, "
                         "or specify relation options manually so FormAlchemy doesn't try to autoload them."))

    def _validate(self):
        if self.is_readonly():
            return True

        self.errors = []

        try:
            # Call renderer.deserialize(), because the deserializer can
            # also raise a ValidationError
            value = self._deserialize()
        except validators.ValidationError, e:
            self.errors.append(e.message)
            return False

        L = list(self.validators)
        if self.is_required() and validators.required not in L:
            L.append(validators.required)
        for validator in L:
            if (not (hasattr(validator, 'accepts_none') and validator.accepts_none)) and value is None:
                continue
            try:
                validator(value, self)
            except validators.ValidationError, e:
                self.errors.append(e.message)
            except TypeError:
                warnings.warn(DeprecationWarning('Please provide a field argument to your %r validator. Your validator will break in FA 1.5' % validator))
                try:
                    validator(value)
                except validators.ValidationError, e:
                    self.errors.append(e.message)
        return not self.errors

    def is_required(self):
        """True iff this Field must be given a non-empty value"""
        return validators.required in self.validators

    def is_readonly(self):
        """True iff this Field is in readonly mode"""
        return self._readonly

    @property
    def model(self):
        return self.parent.model

    def _modified(self, **kwattrs):
        # return a copy of self, with the given attributes modified
        copied = deepcopy(self)
        for attr, value in kwattrs.iteritems():
            setattr(copied, attr, value)
        return copied

    def set(self, **kwattrs):
        """
        Sets different properties on the Field object. In contrast to the
        other methods that tweak a Field, this one changes thing
        IN-PLACE, without creating a new object and returning it.
        This is the behavior for the other methods like ``readonly()``,
        ``required()``, ``with_html()``, ``with_metadata``,
        ``with_renderer()``, ``with_null_as()``, ``label()``,
        ``hidden()``, ``validate()``, etc...

        Allowed attributes are:

         * ``validate`` - append one single validator
         * ``validators`` - appends a list of validators
         * ``renderer`` - sets the renderer used (``.with_renderer(val)``
           equiv.)
         * ``hidden`` - marks a field as hidden (changes the renderer)
         * ``required`` - adds the default 'required' validator to the field
         * ``readonly`` - sets the readonly attribute (``.readonly(val)``
           equiv.)
         * ``null_as`` - sets the 'null_as' attribute (``.with_null_as(val)``
           equiv.)
         * ``label`` - sets the label (``.label(val)`` equiv.)
         * ``multiple`` - marks the field as a multi-select (used by some
           renderers)
         * ``options`` - sets `.render_opts['options']` (for selects and similar
           fields, used by some renderers)
         * ``size`` - sets render_opts['size'] with this val (normally an
           attribute to ``textarea()``, ``dropdown()``, used by some renderers)
         * ``instructions`` - shortcut to update `metadata['instructions']`
         * ``metadata`` - dictionary that `updates` the ``.metadata`` attribute
         * ``html`` - dictionary that updates the ``.html_options`` attribute
           (``.with_html()`` equiv.)

        NOTE: everything in ``.render_opts``, updated with everything in
        ``.html_options`` will be passed as keyword arguments to the `render()`
        function of the Renderer set for the field.

        Example::

            >>> field = Field('myfield')
            >>> field.set(label='My field', renderer=SelectFieldRenderer,
            ...           options=[('Value', 1)],
            ...           validators=[lambda x: x, lambda y: y])
            AttributeField(myfield)
            >>> field.label_text
            'My field'
            >>> field.renderer
            <SelectFieldRenderer for AttributeField(myfield)>

        """
        attrs = kwattrs.keys()
        mapping = dict(renderer='_renderer',
                       readonly='_readonly',
                       null_as='_null_option',
                       label='label_text')
        for attr in attrs:
            value = kwattrs.pop(attr)
            if attr == 'validate':
                self.validators.append(value)
            elif attr == 'validators':
                self.validators.extend(value)
            elif attr == 'metadata':
                self.metadata.update(value)
            elif attr == 'html':
                self.html_options.update(value)
            elif attr == 'instructions':
                self.metadata['instructions'] = value
            elif attr == 'required':
                if value:
                    if validators.required not in self.validators:
                        self.validators.append(validators.required)
                else:
                    if validators.required in self.validators:
                        self.validators.remove(validators.required)
            elif attr == 'hidden':
                if isinstance(self.type, fatypes.Date):
                    renderer = HiddenDateFieldRenderer
                elif isinstance(self.type, fatypes.Time):
                    renderer = HiddenTimeFieldRenderer
                elif isinstance(self.type, fatypes.DateTime):
                    renderer = HiddenDateTimeFieldRenderer
                else:
                    renderer = HiddenFieldRenderer
                self._renderer = renderer
            elif attr in 'attrs':
                self.render_opts.update(value)
            elif attr in mapping:
                attr = mapping.get(attr)
                setattr(self, attr, value)
            elif attr in ('multiple', 'options', 'size'):
                if attr == 'options' and value is not None:
                    value = _normalized_options(value)
                self.render_opts[attr] = value
            else:
                raise ValueError('Invalid argument %s' % attr)
        return self

    def with_null_as(self, option):
        """Render null as the given option tuple of text, value."""
        return self._modified(_null_option=option)
    def with_renderer(self, renderer):
        """
        Return a copy of this Field, with a different renderer.
        Used for one-off renderer changes; if you want to change the
        renderer for all instances of a Field type, modify
        FieldSet.default_renderers instead.
        """
        return self._modified(_renderer=renderer)
    def bind(self, parent):
        """Return a copy of this Field, bound to a different parent"""
        return self._modified(parent=parent)
    def with_metadata(self, **attrs):
        """Attach some metadata attributes to the Field, to be used by
        conditions in templates.

        Example usage:

          >>> test = Field('test')
          >>> field = test.with_metadata(instructions='use this widget this way')
          ...

        And further in your templates you can verify:

          >>> 'instructions' in field.metadata
          True

        and display the content in a <span> or something.
        """
        new_attr = self.metadata.copy()
        new_attr.update(attrs)
        return self._modified(metadata=new_attr)
    def validate(self, validator):
        """
        Add the `validator` function to the list of validation
        routines to run when the `FieldSet`'s `validate` method is
        run. Validator functions take one parameter: the value to
        validate. This value will have already been turned into the
        appropriate data type for the given `Field` (string, int, float,
        etc.). It should raise `ValidationError` if validation
        fails with a message explaining the cause of failure.
        """
        field = deepcopy(self)
        field.validators.append(validator)
        return field
    def required(self):
        """
        Convenience method for `validate(validators.required)`. By
        default, NOT NULL columns are required. You can only add
        required-ness, not remove it.
        """
        return self.validate(validators.required)
    def with_html(self, **html_options):
        """
        Give some HTML options to renderer.

        Trailing underscore (_) characters will be stripped. For example,
        you might want to add a `class` attribute to your checkbox. You
        would need to specify `.options(class_='someclass')`.

        For WebHelpers-aware people: those parameters will be passed to
        the `text_area()`, `password()`, `text()`, etc.. webhelpers.

        NOTE: Those options can override generated attributes and can mess
              the `sync` calls, or `label`-tag associations (if you change
              `name`, or `id` for example).  Use with caution.
        """
        new_opts = copy(self.html_options)
        for k, v in html_options.iteritems():
            new_opts[k.rstrip('_')] = v
        return self._modified(html_options=new_opts)
    def label(self, text=NoDefault):
        """Get or set the label for the field. If a value is provided then change
        the label associated with this field.  By default, the field name is
        used, modified for readability (e.g., 'user_name' -> 'User name').
        """
        if text is NoDefault:
            if self.label_text is not None:
                text = self.label_text
            else:
                text = self.parent.prettify(self.key)
            if text:
                F_ = get_translator(request=self.parent._request)
                return h.escape_once(F_(text))
            else:
                return ''
        return self._modified(label_text=text)
    def label_tag(self, **html_options):
        """return the <label /> tag for the field."""
        html_options.update(for_=self.renderer.name)
        if 'class_' in html_options:
            html_options['class_'] += self.is_required() and ' field_req' or ' field_opt'
        else:
            html_options['class_'] = self.is_required() and 'field_req' or 'field_opt'
        return h.content_tag('label', self.label(), **html_options)
    def attrs(self, **kwargs):
        """update ``render_opts``"""
        self.render_opts.update(kwargs)
        return self._modified(render_opts=self.render_opts)
    def readonly(self, value=True):
        """
        Render the field readonly.

        By default, this marks a field to be rendered as read-only.
        Setting the `value` argument to `False` marks the field as editable.
        """
        return self._modified(_readonly=value)
    def hidden(self):
        """Render the field hidden.  (Value only, no label.)"""
        if isinstance(self.type, fatypes.Date):
            renderer = HiddenDateFieldRenderer
        elif isinstance(self.type, fatypes.Time):
            renderer = HiddenTimeFieldRenderer
        elif isinstance(self.type, fatypes.DateTime):
            renderer = HiddenDateTimeFieldRenderer
        else:
            renderer = HiddenFieldRenderer
        return self._modified(_renderer=renderer, render_opts={})
    def password(self):
        """Render the field as a password input, hiding its value."""
        field = deepcopy(self)
        field._renderer = lambda f: f.parent.default_renderers['password']
        field.render_opts = {}
        return field
    def textarea(self, size=None):
        """
        Render the field as a textarea.  Size must be a string
        (`"25x10"`) or tuple (`25, 10`).
        """
        field = deepcopy(self)
        field._renderer = lambda f: f.parent.default_renderers['textarea']
        if size:
            field.render_opts = {'size': size}
        return field
    def radio(self, options=None):
        """Render the field as a set of radio buttons."""
        field = deepcopy(self)
        field._renderer = lambda f: f.parent.default_renderers['radio']
        if options is None:
            options = self.render_opts.get('options')
        else:
            options = _normalized_options(options)
        field.render_opts = {'options': options}
        return field
    def checkbox(self, options=None):
        """Render the field as a set of checkboxes."""
        field = deepcopy(self)
        field._renderer = lambda f: f.parent.default_renderers['checkbox']
        if options is None:
            options = self.render_opts.get('options')
        else:
            options = _normalized_options(options)
        field.render_opts = {'options': options}
        return field
    def dropdown(self, options=None, multiple=False, size=5):
        """
        Render the field as an HTML select field.
        (With the `multiple` option this is not really a 'dropdown'.)
        """
        field = deepcopy(self)
        field._renderer = lambda f: f.parent.default_renderers['dropdown']
        if options is None:
            options = self.render_opts.get('options')
        else:
            options = _normalized_options(options)
        field.render_opts = {'multiple': multiple, 'options': options}
        if multiple:
            field.render_opts['size'] = size
        return field
    def reset(self):
        """
        Return the field with all configuration changes reverted.
        """
        return deepcopy(self.parent._fields[self.name])

    #==========================================================================
    # HTML5 specific input types
    #==========================================================================

    def date(self):
        '''
        Render the field as a HTML5 date input type.
        '''
        field = deepcopy(self)
        field._renderer = lambda f: f.parent.default_renderers['date']
        return field

    def datetime(self):
        '''
        Render the field as a HTML5 datetime input type.
        '''
        field = deepcopy(self)
        field._renderer = lambda f: f.parent.default_renderers['datetime']
        return field

    def datetime_local(self):
        '''
        Render the field as a HTML5 datetime-local input type.
        '''
        field = deepcopy(self)
        field._renderer = lambda f: f.parent.default_renderers['date']
        return field

    def month(self):
        '''
        Render the field as a HTML5 month input type.
        '''
        field = deepcopy(self)
        field._renderer = lambda f: f.parent.default_renderers['month']
        return field

    def week(self):
        '''
        Render the field as a HTML5 week input type.
        '''
        field = deepcopy(self)
        field._renderer = lambda f: f.parent.default_renderers['week']
        return field

    def time(self):
        '''
        Render the field as a HTML5 time input type.
        '''
        field = deepcopy(self)
        field._renderer = lambda f: f.parent.default_renderers['time']
        return field

    def color(self):
        '''
        Render the field as a HTML5 color input type.
        '''
        field = deepcopy(self)
        field._renderer = lambda f: f.parent.default_renderers['color']
        return field

    def range(self, min_=None, max_=None, step=None, value=None):
        '''
        Render the field as a HTML5 range input type, starting at `min_`,
        ending at `max_`, with legal increments every `step` distance.  The
        default is set by `value`.
        '''
        field = deepcopy(self)
        field._renderer = lambda f: f.parent.default_renderers['range']
        field.render_opts = {}
        if min_:
            field.render_opts["min"] = min_
        if max_:
            field.render_opts["max"] = max_
        if step:
            field.render_opts["step"] = step
        if value:
            field.render_opts["value"] = value
        return field

    def number(self, min_=None, max_=None, step=None, value=None):
        '''
        Render the field as a HTML5 number input type, starting at `min_`,
        ending at `max_`, with legal increments every `step` distance.  The
        default is set by `value`.
        '''
        field = deepcopy(self)
        field._renderer = lambda f: f.parent.default_renderers['number']
        field.render_opts = {}
        if min_:
            field.render_opts["min"] = min_
        if max_:
            field.render_opts["max"] = max_
        if step:
            field.render_opts["step"] = step
        if value:
            field.render_opts["value"] = value
        return field

    def url(self):
        '''
        Render the field as a HTML5 url input type.
        '''
        field = deepcopy(self)
        field._renderer = lambda f: f.parent.default_renderers['url']
        return field

    def email(self):
        '''
        Render the field as a HTML5 email input type.
        '''
        field = deepcopy(self)
        field._renderer = lambda f: f.parent.default_renderers['email']
        return field

    def _get_renderer(self):
        for t in self.parent.default_renderers:
            if not isinstance(t, basestring) and type(self.type) is t:
                return self.parent.default_renderers[t]
        for t in self.parent.default_renderers:
            if not isinstance(t, basestring) and isinstance(self.type, t):
                return self.parent.default_renderers[t]
        raise TypeError(
                'No renderer found for field %s. '
                'Type %s as no default renderer' % (self.name, self.type))

    @property
    def renderer(self):
        if self._renderer is None:
            self._renderer = self._get_renderer()
        try:
            self._renderer = self._renderer(self)
        except TypeError:
            pass
        if not isinstance(self._renderer, FieldRenderer):
            # must be a Renderer class.  instantiate.
            self._renderer = self._renderer(self)
        return self._renderer

    def _get_render_opts(self):
        """
        Calculate the final options dict to be sent to renderers.
        """
        # Use options from internally set render_opts
        opts = dict(self.render_opts)
        # Override with user-specified options (with .with_html())
        opts.update(self.html_options)
        return opts

    def render(self):
        """
        Render this Field as HTML.
        """
        if self.is_readonly():
            return self.render_readonly()

        opts = self._get_render_opts()

        if (isinstance(self.type, fatypes.Boolean)
            and not opts.get('options')
            and self.renderer.__class__ in [self.parent.default_renderers['dropdown'], self.parent.default_renderers['radio']]):
            opts['options'] = [('Yes', True), ('No', False)]
        return self.renderer.render(**opts)

    def render_readonly(self):
        """
        Render this Field as HTML for read only mode.
        """
        return self.renderer.render_readonly(**self._get_render_opts())

    def _pkify(self, value):
        """return the PK for value, if applicable"""
        return value

    @property
    def value(self):
        """
        The value of this Field: use the corresponding value in the bound `data`,
        if any; otherwise, use the value in the bound `model`.  For SQLAlchemy models,
        if there is still no value, use the default defined on the corresponding `Column`.

        For SQLAlchemy collections,
        a list of the primary key values of the items in the collection is returned.

        Invalid form data will cause an error to be raised.  Controllers should thus validate first.
        Renderers should thus never access .value; use .model_value instead.
        """
        # TODO add ._validated flag to save users from themselves?
        if not self.is_readonly() and self.parent.data is not None:
            v = self._deserialize()
            if v is not None:
                return self._pkify(v)
        return self.model_value

    @property
    def model_value(self):
        """
        raw value from model, transformed if necessary for use as a form input value.
        """
        raise NotImplementedError()

    @property
    def raw_value(self):
        """
        raw value from model.  different from `.model_value` in SQLAlchemy fields, because for reference types,
        `.model_value` will return the foreign key ID.  This will return the actual object
        referenced instead.
        """
        raise NotImplementedError()

    def _deserialize(self):
        return self.renderer.deserialize()

class Field(AbstractField):
    """
    A manually-added form field
    """
    def __init__(self, name=None, type=fatypes.String, value=None, **kwattrs):
        """
        Create a new Field object.

        - `name`:
              field name

        - `type=types.String`:
              data type, from formalchemy.types (Integer, Float, String,
              LargeBinary, Boolean, Date, DateTime, Time) or a custom type

        - `value=None`:
              default value.  If value is a callable, it will be passed the current
              bound model instance when the value is read.  This allows creating a
              Field whose value depends on the model once, then binding different
              instances to it later.

          * `name`: field name
          * `type`: data type, from formalchemy.types (Boolean, Integer, String, etc.),
            or a custom type for which you have added a renderer.
          * `value`: default value.  If value is a callable, it will be passed
            the current bound model instance when the value is read.  This allows
            creating a Field whose value depends on the model once, then
            binding different instances to it later.
        """
        AbstractField.__init__(self, None) # parent will be set by ModelRenderer.add
        self.type = type()
        self.name = self.key = name
        self._value = value
        self.is_relation = False
        self.is_scalar_relation = False
        self.set(**kwattrs)

    def set(self, **kwattrs):
        if 'value' in kwattrs:
            self._value = kwattrs.pop('value')
        return AbstractField.set(self, **kwattrs)

    @property
    def model_value(self):
        return self.raw_value

    @property
    def is_collection(self):
        if isinstance(self.type, (fatypes.List, fatypes.Set)):
            return True
        return self.render_opts.get('multiple', False) or isinstance(self.renderer, self.parent.default_renderers['checkbox'])

    @property
    def raw_value(self):
        try:
            # this is NOT the same as getattr -- getattr will return the class's
            # value for the attribute name, which for a manually added Field will
            # be the Field object.  So force looking in the instance __dict__ only.
            return self.model.__dict__[self.name]
        except (KeyError, AttributeError):
            pass
        if callable(self._value):
            return self._value(self.model)
        return self._value

    def sync(self):
        """Set the attribute's value in `model` to the value given in `data`"""
        if not self.is_readonly():
            self._value = self._deserialize()

    def __repr__(self):
        return 'AttributeField(%s)' % self.name

    def __unicode__(self):
        return self.render_readonly()

    def __eq__(self, other):
        # we override eq so that when we configure with options=[...], we can match the renders in options
        # with the ones that were generated at FieldSet creation time
        try:
            return self.name == other.name and _model_equal(self.model, other.model)
        except (AttributeError, ValueError):
            return False
    def __hash__(self):
        return hash(self.name)


class AttributeField(AbstractField):
    """
    Field corresponding to an SQLAlchemy attribute.
    """
    def __init__(self, instrumented_attribute, parent):
        """
            >>> from formalchemy.tests import FieldSet, Order
            >>> fs = FieldSet(Order)
            >>> print fs.user.key
            user

            >>> print fs.user.name
            user_id
        """
        AbstractField.__init__(self, parent)
        # we rip out just the parts we care about from InstrumentedAttribute.
        # impl is the AttributeImpl.  So far all we care about there is ".key,"
        # which is the name of the attribute in the mapped class.
        self._impl = instrumented_attribute.impl
        # property is the PropertyLoader which handles all the interesting stuff.
        # mapper, columns, and foreign keys are all located there.
        self._property = instrumented_attribute.property

        # True iff this is a multi-valued (one-to-many or many-to-many) SA relation
        self.is_collection = isinstance(self._impl, CollectionAttributeImpl)

        # True iff this is the 'one' end of a one-to-many relation
        self.is_scalar_relation = isinstance(self._impl, ScalarObjectAttributeImpl)

        # True iff this field represents a mapped SA relation
        self.is_relation = self.is_scalar_relation or self.is_collection

        self.is_composite = isinstance(self._property, CompositeProperty)

        _columns = self._columns

        self.is_pk = bool([c for c in self._columns if c.primary_key])

        self.is_raw_foreign_key = bool(isinstance(self._property, ColumnProperty) and _foreign_keys(self._property.columns[0]))

        self.is_composite_foreign_key = len(_columns) > 1 and not [c for c in _columns if not _foreign_keys(c)]

        if self.is_composite:
            # this is a little confusing -- we need to return an _instance_ of
            # the correct type, which for composite values will be the value
            # itself. SA should probably have called .type something
            # different, or just not instantiated them...
            self.type = self._property.composite_class.__new__(self._property.composite_class)
        elif len(_columns) > 1:
            self.type = None # may have to be more accurate here
        else:
            self.type = _columns[0].type

        self.key = self._impl.key
        self._column_name = '_'.join([c.name for c in _columns])

        # The name of the form input. usually the same as the key, except for
        # single-valued SA relation properties. For example, for order.user,
        # name will be 'user_id' (assuming that is indeed the name of the foreign
        # key to users), but for user.orders, name will be 'orders'.
        if self.is_collection or self.is_composite or not hasattr(self.model, self._column_name):
            self.name = self.key
        else:
            self.name = self._column_name

        # smarter default "required" value
        if not self.is_collection and not self.is_readonly() and [c for c in _columns if not c.nullable]:
            self.validators.append(validators.required)

        info = dict([(str(k), v) for k, v in self.info.items() if k in self._valide_options])
        if self.is_relation and 'label' not in info:
            m = self._property.mapper.class_
            label = getattr(m, '__label__', None)
            if self._property.direction in (MANYTOMANY, ONETOMANY):
                label = getattr(m, '__plural__', label)
            if label:
                info['label'] = label
        self.set(**info)

    @property
    def info(self):
        """return the best information from SA's Column.info"""
        info = None

        if self.is_relation:
            pairs = self._property.local_remote_pairs
            if len(pairs):
                for pair in reversed(pairs):
                    for col in pair:
                        if col.table in self._property.parent.tables and not col.primary_key:
                            return getattr(col, 'info', None)
                        elif col.table in self._property.mapper.tables:
                            if col.primary_key:
                                if self._property.direction == MANYTOMANY:
                                    return getattr(col, 'info', None)
                            else:
                                parent_info = getattr(col, 'info', {})
                                info = {}
                                for k, v in parent_info.items():
                                    if k.startswith('backref_'):
                                        info[k[8:]] = v
                                return info
        else:
            try:
                col = getattr(self.model.__table__.c, self.key)
            except AttributeError:
                return {}
            else:
                return getattr(col, 'info', None)
        return {}

    def is_readonly(self):
        from sqlalchemy.sql.expression import _Label
        return AbstractField.is_readonly(self) or isinstance(self._columns[0], _Label)

    @property
    def _columns(self):
        if self.is_scalar_relation:
            # If the attribute is a foreign key, return the Column that this
            # attribute is mapped from -- e.g., .user -> .user_id.
            return _foreign_keys(self._property)
        elif isinstance(self._impl, ScalarAttributeImpl) or self._impl.__class__.__name__ in ('ProxyImpl', '_ProxyImpl'): # 0.4 compatibility: ProxyImpl is a one-off class for each synonym, can't import it
            # normal property, mapped to a single column from the main table
            prop = getattr(self._property, '_proxied_property', None)
            if prop is None:
                prop = self._property
            return prop.columns
        else:
            # collection -- use the mapped class's PK
            assert self.is_collection, self._impl.__class__
            return self._property.mapper.primary_key

    def relation_type(self):
        """
        The type of object in the collection (e.g., `User`).
        Calling this is only valid when `is_relation` is True.
        """
        return self._property.mapper.class_

    def _pkify(self, value):
        """return the PK for value, if applicable"""
        if value is None:
            return None
        if self.is_collection:
            return [_pk(item) for item in value]
        if self.is_relation:
            return _pk(value)
        return value

    @property
    def model_value(self):
        return self._pkify(self.raw_value)

    @property
    def raw_value(self):
        if self.is_scalar_relation:
            v = getattr(self.model, self.key)
        else:
            try:
                v = getattr(self.model, self.name)
            except AttributeError:
                v = getattr(self.model, self.key)
        if v is not None:
            return v

        _columns = self._columns
        if len(_columns) == 1 and  _columns[0].default:
            try:
                from sqlalchemy.sql.expression import Function
            except ImportError:
                from sqlalchemy.sql.expression import _Function as Function
            arg = _columns[0].default.arg
            if callable(arg) or isinstance(arg, Function):
                # callables often depend on the current time, e.g. datetime.now or the equivalent SQL function.
                # these are meant to be the value *at insertion time*, so it's not strictly correct to
                # generate a value at form-edit time.
                pass
            else:
                return arg
        return None

    def sync(self):
        """Set the attribute's value in `model` to the value given in `data`"""
        if not self.is_readonly():
            setattr(self.model, self.name, self._deserialize())

    def __eq__(self, other):
        # we override eq so that when we configure with options=[...], we can match the renders in options
        # with the ones that were generated at FieldSet creation time
        try:
            return self._impl is other._impl and _model_equal(self.model, other.model)
        except (AttributeError, ValueError):
            return False
    def __hash__(self):
        return hash(self._impl)

    def __repr__(self):
        return 'AttributeField(%s)' % self.key

    def render(self):
        if self.is_readonly():
            return self.render_readonly()
        if self.is_relation and self.render_opts.get('options') is None:
            if self.is_required() or self.is_collection:
                self.render_opts['options'] = []
            else:
                self.render_opts['options'] = [self._null_option]
            # todo 2.0 this does not handle primaryjoin (/secondaryjoin) alternate join conditions
            q = self.query(self.relation_type())
            order_by = self._property.order_by
            if order_by:
                if not isinstance(order_by, list):
                    order_by = [order_by]
                q = q.order_by(*order_by)
            self.render_opts['options'] += _query_options(q)
            logger.debug('options for %s are %s' % (self.name, self.render_opts['options']))
        if self.is_collection and isinstance(self.renderer, self.parent.default_renderers['dropdown']):
            self.render_opts['multiple'] = True
            if 'size' not in self.render_opts:
                self.render_opts['size'] = 5
        return AbstractField.render(self)

    def _get_renderer(self):
        if self.is_relation:
            return self.parent.default_renderers['dropdown']
        return AbstractField._get_renderer(self)

    def _deserialize(self):
        # for multicolumn keys, we turn the string into python via _simple_eval; otherwise,
        # the key is just the raw deserialized value (which is already an int, etc., as necessary)
        if len(self._columns) > 1:
            python_pk = _simple_eval
        else:
            python_pk = lambda st: st

        if self.is_collection:
            return [self.query(self.relation_type()).get(python_pk(pk)) for pk in self.renderer.deserialize()]
        if self.is_composite_foreign_key:
            return self.query(self.relation_type()).get(python_pk(self.renderer.deserialize()))
        return self.renderer.deserialize()

########NEW FILE########
__FILENAME__ = forms
# Copyright (C) 2007 Alexandre Conrad, alexandre (dot) conrad (at) gmail (dot) com
#
# This module is part of FormAlchemy and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

import cgi
import warnings
import logging
logger = logging.getLogger('formalchemy.' + __name__)


MIN_SA_VERSION = '0.4.5'
from sqlalchemy import __version__
if __version__.split('.') < MIN_SA_VERSION.split('.'):
    raise ImportError('Version %s or later of SQLAlchemy required' % MIN_SA_VERSION)

from sqlalchemy.orm.attributes import InstrumentedAttribute
from sqlalchemy.orm.properties import SynonymProperty
from sqlalchemy.orm import configure_mappers, object_session, class_mapper
from sqlalchemy.orm.session import Session
from sqlalchemy.orm.scoping import ScopedSession
from sqlalchemy.orm.dynamic import DynamicAttributeImpl
from sqlalchemy.util import OrderedDict
from formalchemy import multidict

try:
    from sqlalchemy.orm.descriptor_props import CompositeProperty
except ImportError:
    # <= SA 0.7
    class CompositeProperty(object):
        pass

try:
    from sqlalchemy.orm.exc import UnmappedInstanceError
except ImportError:
    class UnmappedInstanceError(Exception):
        """
            Exception to provide support for sqlalchemy < 0.6
        """

from formalchemy.validators import ValidationError
from formalchemy import fields
from formalchemy import config
from formalchemy import exceptions
from formalchemy import fatypes

from tempita import Template as TempitaTemplate # must import after base

configure_mappers() # initializes InstrumentedAttributes


try:
    # 0.5
    from sqlalchemy.orm.attributes import manager_of_class
    def _get_attribute(cls, p):
        manager = manager_of_class(cls)
        return manager[p.key]
except ImportError:
    # 0.4
    def _get_attribute(cls, p):
        return getattr(cls, p.key)


def prettify(text):
    """
    Turn an attribute name into something prettier, for a default label where none is given.

    >>> prettify("my_column_name")
    'My column name'
    """
    return text.replace("_", " ").capitalize()


class SimpleMultiDict(multidict.UnicodeMultiDict):
    def __init__(self, *args, **kwargs):
        encoding = kwargs.get('encoding', config.encoding)
        multi = multidict.MultiDict()
        multidict.UnicodeMultiDict.__init__(self, multi=multi, encoding=encoding)
        for value in args:
            if isinstance(value, (list, tuple)):
                items = value
            else:
                items = value.items()
            for k, v in items:
                if isinstance(v, (list, tuple)):
                    for item in v:
                        self.add(k, item)
                else:
                    self.add(k, v)



__all__ = ['FieldSet', 'SimpleMultiDict']


class DefaultRenderers(object):

    default_renderers = {
        fatypes.String: fields.TextFieldRenderer,
        fatypes.Unicode: fields.TextFieldRenderer,
        fatypes.Text: fields.TextFieldRenderer,
        fatypes.Integer: fields.IntegerFieldRenderer,
        fatypes.Float: fields.FloatFieldRenderer,
        fatypes.Numeric: fields.FloatFieldRenderer,
        fatypes.Interval: fields.IntervalFieldRenderer,
        fatypes.Boolean: fields.CheckBoxFieldRenderer,
        fatypes.DateTime: fields.DateTimeFieldRenderer,
        fatypes.Date: fields.DateFieldRenderer,
        fatypes.Time: fields.TimeFieldRenderer,
        fatypes.LargeBinary: fields.FileFieldRenderer,
        fatypes.List: fields.SelectFieldRenderer,
        fatypes.Set: fields.SelectFieldRenderer,
        'dropdown': fields.SelectFieldRenderer,
        'checkbox': fields.CheckBoxSet,
        'radio': fields.RadioSet,
        'password': fields.PasswordFieldRenderer,
        'textarea': fields.TextAreaFieldRenderer,
        'email': fields.EmailFieldRenderer,
        fatypes.HTML5Url: fields.UrlFieldRenderer,
        'url': fields.UrlFieldRenderer,
        fatypes.HTML5Number: fields.NumberFieldRenderer,
        'number': fields.NumberFieldRenderer,
        'range': fields.RangeFieldRenderer,
        fatypes.HTML5Date: fields.HTML5DateFieldRenderer,
        'date': fields.HTML5DateFieldRenderer,
        fatypes.HTML5DateTime: fields.HTML5DateTimeFieldRenderer,
        'datetime': fields.HTML5DateTimeFieldRenderer,
        'datetime_local': fields.LocalDateTimeFieldRenderer,
        'month': fields.MonthFieldRender,
        'week': fields.WeekFieldRenderer,
        fatypes.HTML5Time: fields.HTML5TimeFieldRenderer,
        'time': fields.HTML5TimeFieldRenderer,
        fatypes.HTML5Color: fields.ColorFieldRenderer,
        'color': fields.ColorFieldRenderer,
    }


class FieldSet(DefaultRenderers):
    """
    A `FieldSet` is bound to a SQLAlchemy mapped instance (or class, for
    creating new instances) and can render a form for editing that instance,
    perform validation, and sync the form data back to the bound instance.

    `FieldSets` are responsible for generating HTML fields from a given
    `model`.

    You can derive your own subclasses from `FieldSet` to provide a customized
    `render` and/or `configure`.

    You can write `render` by manually sticking strings together if that's what you want,
    but we recommend using a templating package for clarity and maintainability.
    !FormAlchemy includes the Tempita templating package as formalchemy.tempita;
    see http://pythonpaste.org/tempita/ for documentation.

    `formalchemy.forms.template_text_tempita` is the default template used by `FieldSet.`
    !FormAlchemy also includes a Mako version, `formalchemy.forms.template_text_mako`,
    and will use that instead if Mako is available.  The rendered HTML is identical
    but (we suspect) Mako is faster.

    Usage:

        - `model`:
              a SQLAlchemy mapped class or instance.  New object creation
              should be done by passing the class, which will need a default
              (no-parameter) constructor.  After construction or binding of
              the :class:`~formalchemy.forms.FieldSet`, the instantiated object will be available as
              the `.model` attribute.

        - `session=None`:
              the session to use for queries (for relations). If `model` is associated
              with a session, that will be used by default. (Objects mapped with a
              `scoped_session
              <http://www.sqlalchemy.org/docs/05/session.html#contextual-thread-local-sessions>`_
              will always have a session. Other objects will
              also have a session if they were loaded by a Query.)

        - `data=None`:
              dictionary-like object of user-submitted data to validate and/or
              sync to the `model`. Scalar attributes should have a single
              value in the dictionary; multi-valued relations should have a
              list, even if there are zero or one values submitted.  Currently,
              pylons request.params() objects and plain dictionaries are known
              to work.

        - `request=None`:
              WebOb-like object that can be taken in place of `data`.
              FormAlchemy will make sure it's a POST, and use it's 'POST'
              attribute as the data.  Also, the request object will be
              available to renderers as the `.request` attribute.

        - `prefix=None`:
              the prefix to prepend to html name attributes. This is useful to avoid
              field name conflicts when there are two fieldsets creating objects
              from the same model in one html page.  (This is not needed when
              editing existing objects, since the object primary key is used as part
              of the field name.)


        Only the `model` parameter is required.

        After binding, :class:`~formalchemy.forms.FieldSet`'s `model` attribute will always be an instance.
        If you bound to a class, `FormAlchemy` will call its constructor with no
        arguments to create an appropriate instance.

        .. NOTE::

          This instance will not be added to the current session, even if you are using `Session.mapper`.

        All of these parameters may be overridden by the `bind` or `rebind`
        methods.  The `bind` method returns a new instance bound as specified,
        while `rebind` modifies the current :class:`~formalchemy.forms.FieldSet` and has
        no return value. (You may not `bind` to a different type of SQLAlchemy
        model than the initial one -- if you initially bind to a `User`, you
        must subsequently bind `User`'s to that :class:`~formalchemy.forms.FieldSet`.)

        Typically, you will configure a :class:`~formalchemy.forms.FieldSet` once in
        your common form library, then `bind` specific instances later for editing. (The
        `bind` method is thread-safe; `rebind` is not.)  Thus:

        load stuff:

        >>> from formalchemy.tests import FieldSet, User, session

        now, in `library.py`

        >>> fs = FieldSet(User)
        >>> fs.configure(options=[]) # put all configuration stuff here

        and in `controller.py`

        >>> from library import fs
        >>> user = session.query(User).first()
        >>> fs2 = fs.bind(user)
        >>> html = fs2.render()

        The `render_fields` attribute is an OrderedDict of all the `Field`'s
        that have been configured, keyed by name. The order of the fields
        is the order in `include`, or the order they were declared
        in the SQLAlchemy model class if no `include` is specified.

        The `_fields` attribute is an OrderedDict of all the `Field`'s
        the ModelRenderer knows about, keyed by name, in their
        unconfigured state.  You should not normally need to access
        `_fields` directly.

        (Note that although equivalent `Field`'s (fields referring to
        the same attribute on the SQLAlchemy model) will equate with
        the == operator, they are NOT necessarily the same `Field`
        instance.  Stick to referencing `Field`'s from their parent
        `FieldSet` to always get the "right" instance.)
    """
    __sa__ = True
    engine = _render = _render_readonly = None

    prettify = staticmethod(prettify)

    def __init__(self, model, session=None, data=None, prefix=None,
                 format=u'%(model)s-%(pk)s-%(name)s',
                 request=None):
        self._fields = OrderedDict()
        self._render_fields = OrderedDict()
        self.model = self.session = None
        self.readonly = False
        self.validator = None
        self.focus = True
        self._request = request
        self._format = format
        self._prefix = prefix
        self._errors = []


        if not model:
            raise Exception('model parameter may not be None')
        self._original_cls = isinstance(model, type) and model or type(model)

        if self.__sa__:
            FieldSet.rebind(self, model, session, data, request)

            cls = isinstance(self.model, type) and self.model or type(self.model)
            try:
                class_mapper(cls)
            except:
                # this class is not managed by SA.  extract any raw Fields defined on it.
                keys = cls.__dict__.keys()
                keys.sort(lambda a, b: cmp(a.lower(), b.lower())) # 2.3 support
                for key in keys:
                    field = cls.__dict__[key]
                    if isinstance(field, fields.Field):
                        if field.name and field.name != key:
                            raise Exception('Fields in a non-mapped class have the same name as their attribute.  Do not manually give them a name.')
                        field.name = field.key = key
                        self.append(field)
                if not self._fields:
                    raise Exception("not bound to a SA instance, and no manual Field definitions found")
            else:
                # SA class.
                # load synonyms so we can ignore them
                ignore_keys = set()
                for p in class_mapper(cls).iterate_properties:
                    if isinstance(p, SynonymProperty):
                        ignore_keys.add(p.name)
                    elif hasattr(p, '_is_polymorphic_discriminator') and p._is_polymorphic_discriminator:
                        ignore_keys.add(p.key)
                    elif isinstance(p, CompositeProperty):
                        for p in p.props:
                            ignore_keys.add(p.key)

                # attributes we're interested in
                attrs = []
                for p in class_mapper(cls).iterate_properties:
                    attr = _get_attribute(cls, p)
                    if ((isinstance(p, SynonymProperty) or attr.property.key not in ignore_keys)
                        and not isinstance(attr.impl, DynamicAttributeImpl)):
                        attrs.append(attr)
                # sort relations last before storing in the OrderedDict
                L = [fields.AttributeField(attr, self) for attr in attrs]
                L.sort(lambda a, b: cmp(a.is_relation, b.is_relation)) # note, key= not used for 2.3 support
                self._fields.update((field.key, field) for field in L)


    def configure(self, pk=False, focus=True, readonly=False, global_validator=None, exclude=[], include=[], options=[]):
        """
        The `configure` method specifies a set of attributes to be rendered.
        By default, all attributes are rendered except primary keys and
        foreign keys.  But, relations `based on` foreign keys `will` be
        rendered.  For example, if an `Order` has a `user_id` FK and a `user`
        relation based on it, `user` will be rendered (as a select box of
        `User`'s, by default) but `user_id` will not.

        Parameters:
          * `pk=False`:
                set to True to include primary key columns
          * `exclude=[]`:
                an iterable of attributes to exclude.  Other attributes will
                be rendered normally
          * `include=[]`:
                an iterable of attributes to include.  Other attributes will
                not be rendered
          * `options=[]`:
                an iterable of modified attributes.  The set of attributes to
                be rendered is unaffected
          * `global_validator=None`:
                global_validator` should be a function that performs
                validations that need to know about the entire form.
          * `focus=True`:
                the attribute (e.g., `fs.orders`) whose rendered input element
                gets focus. Default value is True, meaning, focus the first
                element. False means do not focus at all.
          * `readonly=False`:
                if true, the fieldset will be rendered as a table (tbody)
                instead of a group of input elements.  Opening and closing
                table tags are not included.

        Only one of {`include`, `exclude`} may be specified.

        Note that there is no option to include foreign keys.  This is
        deliberate.  Use `include` if you really need to manually edit FKs.

        If `include` is specified, fields will be rendered in the order given
        in `include`.  Otherwise, fields will be rendered in alphabetical
        order.

        Examples: given a `FieldSet` `fs` bound to a `User` instance as a
        model with primary key `id` and attributes `name` and `email`, and a
        relation `orders` of related Order objects, the default will be to
        render `name`, `email`, and `orders`. To render the orders list as
        checkboxes instead of a select, you could specify::

        >>> from formalchemy.tests import FieldSet, User
        >>> fs = FieldSet(User)
        >>> fs.configure(options=[fs.orders.checkbox()])

        To render only name and email,

        >>> fs.configure(include=[fs.name, fs.email])

        or

        >>> fs.configure(exclude=[fs.orders])

        Of course, you can include modifications to a field in the `include`
        parameter, such as here, to render name and options-as-checkboxes:

        >>> fs.configure(include=[fs.name, fs.orders.checkbox()])
        """
        self.focus = focus
        self.readonly = readonly
        self.validator = global_validator
        self._render_fields = OrderedDict([(field.key, field) for field in self._get_fields(pk, exclude, include, options)])

    def bind(self, model=None, session=None, data=None, request=None,
             with_prefix=True):
        """
        Return a copy of this FieldSet or Grid, bound to the given
        `model`, `session`, and `data`. The parameters to this method are the
        same as in the constructor.

        Often you will create and `configure` a FieldSet or Grid at application
        startup, then `bind` specific instances to it for actual editing or display.
        """
        if not (model is not None or session or data or request):
            raise Exception('must specify at least one of {model, session, data, request}')

        if not model:
            if not self.model:
                raise Exception('model must be specified when none is already set')
            model = fields._pk(self.model) is None and type(self.model) or self.model

        # copy.copy causes a stacktrace on python 2.5.2/OSX + pylons.  unable to reproduce w/ simpler sample.
        mr = object.__new__(self.__class__)
        mr.__dict__ = dict(self.__dict__)
        # two steps so bind's error checking can work
        FieldSet.rebind(mr, model, session, data, request,
                        with_prefix=with_prefix)
        mr._fields = OrderedDict([(key, renderer.bind(mr)) for key, renderer in self._fields.iteritems()])
        if self._render_fields:
            mr._render_fields = OrderedDict([(field.key, field) for field in
                                             [field.bind(mr) for field in self._render_fields.itervalues()]])
        mr._request = request
        return mr


    def rebind(self, model=None, session=None, data=None, request=None,
               with_prefix=True):
        """
        Like `bind`, but acts on this instance.  No return value.
        Not all parameters are treated the same; specifically, what happens if they are NOT specified is different:

        * if `model` is not specified, the old model is used
        * if `session` is not specified, FA tries to re-guess session from the model
        * if `data` is not specified, it is rebound to None
        * if `request` is specified and not `data` request.POST is used as data.
          `request` is also saved to be access by renderers (as
          `fs.FIELD.renderer.request`).
        * if `with_prefix` is False then a prefix ``{Model}-{pk}`` is added to each data keys
        """
        if data is None and request is not None:
            if hasattr(request, 'environ') and hasattr(request, 'POST'):
                if request.environ.get('REQUEST_METHOD', '').upper() == 'POST':
                    data = request.POST or None

        original_model = model
        if model:
            if isinstance(model, type):
                try:
                    model = model()
                except Exception, e:
                    model_error = str(e)
                    msg = ("%s appears to be a class, not an instance, but "
                           "FormAlchemy cannot instantiate it. "
                           "(Make sure all constructor parameters are "
                           "optional!). The error was:\n%s")
                    raise Exception(msg % (model, model_error))

                # take object out of session, if present
                try:
                    _obj_session = object_session(model)
                except (AttributeError, UnmappedInstanceError):
                    pass # non-SA object; doesn't need session
                else:
                    if _obj_session:
                        _obj_session.expunge(model)
            else:
                try:
                    session_ = object_session(model)
                except:
                    # non SA class
                    if fields._pk(model) is None and model is not self._original_cls:
                        error = ('Mapped instances to be bound must either have '
                                'a primary key set or not be in a Session.  When '
                                'creating a new object, bind the class instead '
                                '[i.e., bind(User), not bind(User())].')
                        raise Exception(error)
                else:
                    if session_:
                        # for instances of mapped classes, require that the instance
                        # have a PK already
                        try:
                            class_mapper(type(model))
                        except:
                            pass
                        else:
                            if fields._pk(model) is None:
                                error = ('Mapped instances to be bound must either have '
                                        'a primary key set or not be in a Session.  When '
                                        'creating a new object, bind the class instead '
                                        '[i.e., bind(User), not bind(User())]')
                                raise Exception(error)
            if (self.model and type(self.model) != type(model) and
                not issubclass(model.__class__, self._original_cls)):
                raise ValueError('You can only bind to another object of the same type or subclass you originally bound to (%s), not %s' % (type(self.model), type(model)))
            self.model = model
            self._bound_pk = fields._pk(model)

        if data is not None and not with_prefix:
            if isinstance(data, multidict.UnicodeMultiDict):
                encoding = data.encoding
            else:
                encoding = config.encoding
            pk = fields._pk(self.model) or ''
            prefix = '%s-%s' % (self._original_cls.__name__, pk)
            if self._prefix:
                prefix = '%s-%s' % (self._prefix, prefix)
            data = SimpleMultiDict([('%s-%s' % (prefix, k), v) for k, v in data.items()], encoding=encoding)

        if data is None:
            self.data = None
        elif isinstance(data, multidict.UnicodeMultiDict):
            self.data = data
        elif isinstance(data, multidict.MultiDict):
            self.data = multidict.UnicodeMultiDict(multi=data, encoding=config.encoding)
        elif hasattr(data, 'getall') and hasattr(data, 'getone'):
            self.data = data
        elif isinstance(data, (dict, list)):
            self.data = SimpleMultiDict(data, encoding=config.encoding)
        else:
            raise Exception('unsupported data object %s.  currently only dicts and Paste multidicts are supported' % self.data)

        if not self.__sa__:
            return

        if session:
            if not isinstance(session, Session) and not isinstance(session, ScopedSession):
                raise ValueError('Invalid SQLAlchemy session object %s' % session)
            self.session = session
        elif model:
            if '_obj_session' in locals():
                # model may be a temporary object, expunged from its session -- grab the existing reference
                self.session = _obj_session
            else:
                try:
                    o_session = object_session(model)
                except (AttributeError, UnmappedInstanceError):
                    pass # non-SA object
                else:
                    if o_session:
                        self.session = o_session
        # if we didn't just instantiate (in which case object_session will be None),
        # the session should be the same as the object_session
        if self.session and model == original_model:
            try:
                o_session = object_session(self.model)
            except (AttributeError, UnmappedInstanceError):
                pass # non-SA object
            else:
                if o_session and self.session is not o_session:
                    raise Exception('You may not explicitly bind to a session when your model already belongs to a different one')

    def validate(self):
        """
        Validate attributes and `global_validator`.
        If validation fails, the validator should raise `ValidationError`.
        """
        if self.readonly:
            raise ValidationError('Cannot validate a read-only FieldSet')
        if self.data is None:
            raise ValidationError('Cannot validate without binding data')
        success = True
        for field in self.render_fields.itervalues():
            success = field._validate() and success
        # run this _after_ the field validators, since each field validator
        # resets its error list. we want to allow the global validator to add
        # errors to individual fields.
        if self.validator:
            self._errors = []
            try:
                self.validator(self)
            except ValidationError, e:
                self._errors = e.args
                success = False
        return success

    def sync(self):
        """
        Sync (copy to the corresponding attributes) the data passed to the constructor or `bind` to the `model`.
        """
        if self.readonly:
            raise Exception('Cannot sync a read-only FieldSet')
        if self.data is None:
            raise Exception("No data bound; cannot sync")
        for field in self.render_fields.itervalues():
            field.sync()
        if self.session:
            self.session.add(self.model)

    def render(self, **kwargs):
        if fields._pk(self.model) != self._bound_pk and self.data is not None:
            msg = ("Primary key of model has changed since binding, "
                   "probably due to sync()ing a new instance (from %r to %r). "
                   "You can solve this by either binding to a model "
                   "with the original primary key again, or by binding data to None.")
            raise exceptions.PkError(msg % (self._bound_pk, fields._pk(self.model)))
        engine = self.engine or config.engine
        if 'request' not in kwargs:
            kwargs['request'] = self._request
        if self.readonly:
            template = 'fieldset_readonly'
        else:
            template = 'fieldset'
        return engine(template, fieldset=self, **kwargs)

    @property
    def errors(self):
        """
        A dictionary of validation failures.  Always empty before `validate()` is run.
        Dictionary keys are attributes; values are lists of messages given to `ValidationError`.
        Global errors (not specific to a single attribute) are under the key `None`.
        """
        errors = {}
        if self._errors:
            errors[None] = self._errors
        errors.update(dict([(field, field.errors)
                            for field in self.render_fields.itervalues() if field.errors]))
        return errors


    @property
    def render_fields(self):
        """
        The set of attributes that will be rendered, as a (ordered)
        dict of `{fieldname: Field}` pairs
        """
        if not self._render_fields:
            self._render_fields = OrderedDict([(field.key, field) for field in self._get_fields()])
        return self._render_fields

    def copy(self, *args):
        """return a copy of the fieldset. args is a list of field names or field
        objects to render in the new fieldset"""
        mr = self.bind(self.model, self.session)
        _fields = self._render_fields or self._fields
        _new_fields = []
        if args:
            for field in args:
                if isinstance(field, basestring):
                    if field in _fields:
                        field = _fields.get(field)
                    else:
                        raise AttributeError('%r as not field named %s' % (self, field))
                assert isinstance(field, fields.AbstractField), field
                field.bind(mr)
                _new_fields.append(field)
            mr._render_fields = OrderedDict([(field.key, field) for field in _new_fields])
        return mr

    def append(self, field):
        """Add a form Field. By default, this Field will be included in the rendered form or table."""
        if not isinstance(field, fields.AbstractField):
            raise ValueError('Can only add Field or AttributeField objects; got %s instead' % field)
        field.parent = self
        _fields = self._render_fields or self._fields
        _fields[field.name] = field

    def add(self, field):
        warnings.warn(DeprecationWarning('FieldSet.add is deprecated. Use FieldSet.append instead. Your validator will break in FA 1.5'))
        self.append(field)

    def extend(self, fields):
        """Add a list of fields. By default, each Field will be included in the
        rendered form or table."""
        for field in fields:
            self.append(field)

    def insert(self, field, new_field):
        """Insert a new field *before* an existing field.

        This is like the normal ``insert()`` function of ``list`` objects. It
        takes the place of the previous element, and pushes the rest forward.
        """
        fields_ = self._render_fields or self._fields
        if not isinstance(new_field, fields.Field):
            raise ValueError('Can only add Field objects; got %s instead' % field)
        if isinstance(field, fields.AbstractField):
            try:
                index = fields_.keys().index(field.key)
            except ValueError:
                raise ValueError('%s not in fields' % field.key)
        else:
            raise TypeError('field must be a Field. Got %r' % field)
        new_field.parent = self
        items = list(fields_.iteritems()) # prepare for Python 3
        items.insert(index, (new_field.name, new_field))
        if self._render_fields:
            self._render_fields = OrderedDict(items)
        else:
            self._fields = OrderedDict(items)

    def insert_after(self, field, new_field):
        """Insert a new field *after* an existing field.

        Use this if your business logic requires to add after a certain field,
        and not before.
        """
        fields_ = self._render_fields or self._fields
        if not isinstance(new_field, fields.Field):
            raise ValueError('Can only add Field objects; got %s instead' % field)
        if isinstance(field, fields.AbstractField):
            try:
                index = fields_.keys().index(field.key)
            except ValueError:
                raise ValueError('%s not in fields' % field.key)
        else:
            raise TypeError('field must be a Field. Got %r' % field)
        new_field.parent = self
        items = list(fields_.iteritems())
        new_item = (new_field.name, new_field)
        if index + 1 == len(items): # after the last element ?
            items.append(new_item)
        else:
            items.insert(index + 1, new_item)
        if self._render_fields:
            self._render_fields = OrderedDict(items)
        else:
            self._fields = OrderedDict(items)

    def to_dict(self, with_prefix=True, as_string=False):
        """This method intend to help you to work with json. Render fieldset as
        a dict. If ``with_prefix`` is False then the prefix ``{Model}-{pk}`` is
        not added. If ``as_string`` is True then all value are set using
        ``field.render_readonly()`` else the pythonic value is used"""
        _fields = self._render_fields or self._fields
        def get_value(f):
            if as_string:
                return f.render_readonly()
            else:
                return f.value
        if as_string:
            data = [(f, f.render_readonly()) for f in _fields.values()]
        else:
            data = [(f, f.value) for f in _fields.values() if not isinstance(f.renderer, fields.PasswordFieldRenderer)]

        if with_prefix:
            data = [(f.renderer.name, v) for f, v in data]
        else:
            data = [(f.name, v) for f, v in data]

        return dict(data)

    def _raw_fields(self):
        return self._fields.values()

    def _get_fields(self, pk=False, exclude=[], include=[], options=[]):
        # sanity check
        if include and exclude:
            raise Exception('Specify at most one of include, exclude')

        # help people who meant configure(include=[X]) but just wrote configure(X), resulting in pk getting the positional argument
        if pk not in [True, False]:
            raise ValueError('pk option must be True or False, not %s' % pk)

        # verify that options that should be lists of Fields, are
        for iterable in ['include', 'exclude', 'options']:
            try:
                L = list(eval(iterable))
            except:
                raise ValueError('`%s` parameter should be an iterable' % iterable)
            for field in L:
                if not isinstance(field, fields.AbstractField):
                    raise TypeError('non-AbstractField object `%s` found in `%s`' % (field, iterable))
                if field not in self._fields.values():
                    raise ValueError('Unrecognized Field `%r` in `%s` -- did you mean to call append() first?' % (field, iterable))

        # if include is given, those are the fields used.  otherwise, include those not explicitly (or implicitly) excluded.
        if not include:
            ignore = list(exclude) # don't modify `exclude` directly to avoid surprising caller
            if not pk:
                ignore.extend([wrapper for wrapper in self._raw_fields() if wrapper.is_pk and not wrapper.is_collection])
            ignore.extend([wrapper for wrapper in self._raw_fields() if wrapper.is_raw_foreign_key])
            include = [field for field in self._raw_fields() if field not in ignore]

        # in the returned list, replace any fields in `include` w/ the corresponding one in `options`, if present.
        # this is a bit clunky because we want to
        #   1. preserve the order given in `include`
        #   2. not modify `include` (or `options`) directly; that could surprise the caller
        options_dict = {} # create + update for 2.3's benefit
        options_dict.update(dict([(wrapper, wrapper) for wrapper in options]))
        L = []
        for wrapper in include:
            if wrapper in options_dict:
                L.append(options_dict[wrapper])
            else:
                L.append(wrapper)
        return L

    def __getattr__(self, attrname):
        try:
            return self._render_fields[attrname]
        except KeyError:
            try:
                return self._fields[attrname]
            except KeyError:
                raise AttributeError(attrname)

    __getitem__ = __getattr__

    def __setattr__(self, attrname, value):
        if attrname not in ('_fields', '__dict__', 'focus', 'model', 'session', 'data') and \
           (attrname in self._fields or isinstance(value, fields.AbstractField)):
            raise AttributeError('Do not set field attributes manually.  Use append() or configure() instead')
        object.__setattr__(self, attrname, value)

    def __delattr__(self, attrname):
        if attrname in self._render_fields:
            del self._render_fields[attrname]
        elif attrname in self._fields:
            raise RuntimeError("You try to delete a field but your form is not configured")
        else:
            raise AttributeError("field %s does not exist" % attrname)

    __delitem__ = __delattr__

    def __repr__(self):
        _fields = self._fields
        conf = ''
        if self._render_fields:
            conf = ' (configured)'
            _fields = self._render_fields
        return '<%s%s with %r>' % (self.__class__.__name__, conf,
                                   _fields.keys())


########NEW FILE########
__FILENAME__ = helpers
"""
A small module to wrap WebHelpers in FormAlchemy.
"""
from webhelpers.html.tags import text
from webhelpers.html.tags import hidden
from webhelpers.html.tags import password
from webhelpers.html.tags import textarea
from webhelpers.html.tags import checkbox
from webhelpers.html.tags import radio
from webhelpers.html import tags
from webhelpers.html import HTML, literal

def html_escape(s):
    return HTML(s)

escape_once = html_escape

def content_tag(name, content, **options):
    """
    Create a tag with content

    Takes the same keyword args as ``tag``

    Examples::

        >>> print content_tag("p", "Hello world!")
        <p>Hello world!</p>
        >>> print content_tag("div", content_tag("p", "Hello world!"), class_="strong")
        <div class="strong"><p>Hello world!</p></div>
    """
    if content is None:
        content = ''
    tag = HTML.tag(name, _closed=False, **options) + HTML(content) + literal('</%s>' % name)
    return tag

def text_field(name, value=None, **options):
    """
    Creates a standard text field.

    ``value`` is a string, the content of the text field

    Options:

    * ``disabled`` - If set to True, the user will not be able to use this input.
    * ``size`` - The number of visible characters that will fit in the input.
    * ``maxlength`` - The maximum number of characters that the browser will allow the user to enter.

    Remaining keyword options will be standard HTML options for the tag.
    """
    _update_fa(options, name)
    return text(name, value=value, **options)

def password_field(name="password", value=None, **options):
    """
    Creates a password field

    Takes the same options as text_field
    """
    _update_fa(options, name)
    return password(name, value=value, **options)

def text_area(name, content='', **options):
    """
    Creates a text input area.

    Options:

    * ``size`` - A string specifying the dimensions of the textarea.

    Example::

        >>> print text_area("Body", '', size="25x10")
        <textarea cols="25" id="Body" name="Body" rows="10"></textarea>
    """
    _update_fa(options, name)
    if 'size' in options:
        options["cols"], options["rows"] = options["size"].split("x")
        del options['size']
    return textarea(name, content=content, **options)

def check_box(name, value="1", checked=False, **options):
    """
    Creates a check box.
    """
    _update_fa(options, name)
    if checked:
        options["checked"] = "checked"
    return tags.checkbox(name, value=value, **options)

def hidden_field(name, value=None, **options):
    """
    Creates a hidden field.

    Takes the same options as text_field
    """
    _update_fa(options, name)
    return tags.hidden(name, value=value, **options)

def file_field(name, value=None, **options):
    """
    Creates a file upload field.

    If you are using file uploads then you will also need to set the multipart option for the form.

    Example::

        >>> print file_field('myfile')
        <input id="myfile" name="myfile" type="file" />
    """
    _update_fa(options, name)
    return tags.file(name, value=value, type="file", **options)

def radio_button(name, *args, **options):
    _update_fa(options, name)
    return radio(name, *args, **options)

def tag(name, open=False, **options):
    """
    Returns an XHTML compliant tag of type ``name``.

    ``open``
        Set to True if the tag should remain open

    All additional keyword args become attribute/value's for the tag. To pass in Python
    reserved words, append _ to the name of the key. For attributes with no value (such as
    disabled and readonly), a value of True is permitted.

    Examples::

        >>> print tag("br")
        <br />
        >>> print tag("br", True)
        <br>
        >>> print tag("input", type="text")
        <input type="text" />
        >>> print tag("input", type='text', disabled='disabled')
        <input disabled="disabled" type="text" />
    """
    return HTML.tag(name, _closed=not open, **options)

def label(value, **kwargs):
    """
    Return a label tag

        >>> print label('My label', for_='fieldname')
        <label for="fieldname">My label</label>

    """
    if 'for_' in kwargs:
        kwargs['for'] = kwargs.pop('for_')
    return tag('label', open=True, **kwargs) + literal(value) + literal('</label>')

def select(name, selected, select_options, **attrs):
    """
    Creates a dropdown selection box::

    <select id="people" name="people">
    <option value="George">George</option>
    </select>

    """
    if 'options' in attrs:
        del attrs['options']
    select_options = _sanitize_select_options(select_options)
    _update_fa(attrs, name)
    return tags.select(name, selected, select_options, **attrs)

def _sanitize_select_options(options):
    if isinstance(options, (list, tuple)):
        if _only_contains_leaves(options) and len(options) >= 2:
            return (options[1], options[0])
        else:
            return [_sanitize_select_options(option) for option in options]
    return options

def _only_contains_leaves(option):
    for sub_option in option:
        if isinstance(sub_option, (list, tuple)):
            return False
    return True

def _update_fa(attrs, name):
    if 'id' not in attrs:
        attrs['id'] = name
    if 'options' in attrs:
        del attrs['options']

if __name__=="__main__":
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = i18n
# Copyright (C) 2007 Alexandre Conrad, alexandre (dot) conrad (at) gmail (dot) com
#
# This module is part of FormAlchemy and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

import os
from gettext import GNUTranslations

i18n_path = os.path.join(os.path.dirname(__file__), 'i18n_resources')

try:
    from pyramid.i18n import get_localizer
    from pyramid.i18n import TranslationStringFactory
    HAS_PYRAMID = True
except ImportError:
    HAS_PYRAMID = False

try:
    from pylons.i18n import get_lang
    HAS_PYLONS = True
except:
    HAS_PYLONS = False

if not HAS_PYLONS:
    def get_lang(): return []

class _Translator(object):
    """dummy translator"""
    def gettext(self, value):
        if isinstance(value, str):
            return unicode(value, 'utf-8')
        return value
_translator = _Translator()

def get_translator(lang=None, request=None):
    """
    return a GNUTranslations instance for `lang`::

        >>> translator = get_translator('fr')
        ... assert translate('Remove') == 'Supprimer'
        ... assert translate('month_01') == 'Janvier'
        >>> translator = get_translator('en')
        ... assert translate('Remove') == 'Remove'
        ... assert translate('month_01') == 'January'

    The correct gettext method is stored in request if possible::

        >>> from webob import Request
        >>> req = Request.blank('/')
        >>> translator = get_translator('fr', request=req)
        ... assert translate('Remove') == 'Supprimer'
        >>> translator = get_translator('en', request=req)
        ... assert translate('Remove') == 'Supprimer'

    """
    if request is not None:
        translate = request.environ.get('fa.translate')
        if translate:
            return translate

        if HAS_PYRAMID:
            translate = get_localizer(request).translate
            request.environ['fa.translate'] = translate
            return translate

    # get possible fallback languages
    try:
        langs = get_lang() or []
    except TypeError:
        # this occurs when Pylons is available and we are not in a valid thread
        langs = []

    # insert lang if provided
    if lang and lang not in langs:
        langs.insert(0, lang)

    if not langs:
        langs = ['en']

    # get the first available catalog
    for lang in langs:
        filename = os.path.join(i18n_path, lang, 'LC_MESSAGES','formalchemy.mo')
        if os.path.isfile(filename):
            translations_path = os.path.join(i18n_path, lang, 'LC_MESSAGES','formalchemy.mo')
            tr = GNUTranslations(open(translations_path, 'rb')).gettext
            def translate(value):
                value = tr(value)
                if not isinstance(value, unicode):
                    return unicode(value, 'utf-8')
                return value
            if request is not None:
                request.environ['fa.translate'] = translate
            return translate

    # dummy translator
    if request is not None:
        request.environ['fa.translate'] = _translator.gettext
    return _translator.gettext

if HAS_PYRAMID:
    _ = TranslationStringFactory('formalchemy')
else:
    def _(value):
        """dummy 'translator' to mark translation strings in python code"""
        return value

# month translation
_('Year')
_('Month')
_('Day')
_('month_01')
_('month_02')
_('month_03')
_('month_04')
_('month_05')
_('month_06')
_('month_07')
_('month_08')
_('month_09')
_('month_10')
_('month_11')
_('month_12')


########NEW FILE########
__FILENAME__ = msgfmt
#! /usr/bin/env python
# -*- coding: iso-8859-1 -*-
# Written by Martin v. Loewis <loewis@informatik.hu-berlin.de>
#
# Changed by Christian 'Tiran' Heimes <tiran@cheimes.de> for the placeless
# translation service (PTS) of zope
#
# Slightly updated by Hanno Schlichting <plone@hannosch.info>
#
# Included by Ingeniweb from PlacelessTranslationService 1.4.8

"""Generate binary message catalog from textual translation description.

This program converts a textual Uniforum-style message catalog (.po file) into
a binary GNU catalog (.mo file).  This is essentially the same function as the
GNU msgfmt program, however, it is a simpler implementation.

This file was taken from Python-2.3.2/Tools/i18n and altered in several ways.
Now you can simply use it from another python module:

  from msgfmt import Msgfmt
  mo = Msgfmt(po).get()

where po is path to a po file as string, an opened po file ready for reading or
a list of strings (readlines of a po file) and mo is the compiled mo
file as binary string.

Exceptions:

  * IOError if the file couldn't be read

  * msgfmt.PoSyntaxError if the po file has syntax errors

"""
import struct
import array
import types
from cStringIO import StringIO

__version__ = "1.1pts"

class PoSyntaxError(Exception):
    """ Syntax error in a po file """
    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return 'Po file syntax error: %s' % self.msg

class Msgfmt:
    """ """
    def __init__(self, po, name='unknown'):
        self.po = po
        self.name = name
        self.messages = {}

    def readPoData(self):
        """ read po data from self.po and store it in self.poLines """
        output = []
        if isinstance(self.po, types.FileType):
            self.po.seek(0)
            output = self.po.readlines()
        if isinstance(self.po, list):
            output = self.po
        if isinstance(self.po, str):
            output = open(self.po, 'rb').readlines()
        if not output:
            raise ValueError, "self.po is invalid! %s" % type(self.po)
        return output

    def add(self, id, str, fuzzy):
        "Add a non-empty and non-fuzzy translation to the dictionary."
        if str and not fuzzy:
            self.messages[id] = str

    def generate(self):
        "Return the generated output."
        keys = self.messages.keys()
        # the keys are sorted in the .mo file
        keys.sort()
        offsets = []
        ids = strs = ''
        for id in keys:
            # For each string, we need size and file offset.  Each string is NUL
            # terminated; the NUL does not count into the size.
            offsets.append((len(ids), len(id), len(strs), len(self.messages[id])))
            ids += id + '\0'
            strs += self.messages[id] + '\0'
        output = ''
        # The header is 7 32-bit unsigned integers.  We don't use hash tables, so
        # the keys start right after the index tables.
        # translated string.
        keystart = 7*4+16*len(keys)
        # and the values start after the keys
        valuestart = keystart + len(ids)
        koffsets = []
        voffsets = []
        # The string table first has the list of keys, then the list of values.
        # Each entry has first the size of the string, then the file offset.
        for o1, l1, o2, l2 in offsets:
            koffsets += [l1, o1+keystart]
            voffsets += [l2, o2+valuestart]
        offsets = koffsets + voffsets
        output = struct.pack("Iiiiiii",
                             0x950412deL,       # Magic
                             0,                 # Version
                             len(keys),         # # of entries
                             7*4,               # start of key index
                             7*4+len(keys)*8,   # start of value index
                             0, 0)              # size and offset of hash table
        output += array.array("i", offsets).tostring()
        output += ids
        output += strs
        return output


    def get(self):
        """ """
        ID = 1
        STR = 2

        section = None
        fuzzy = 0

        lines = self.readPoData()

        # Parse the catalog
        lno = 0
        for l in lines:
            lno += 1
            # If we get a comment line after a msgstr or a line starting with
            # msgid, this is a new entry
            # XXX: l.startswith('msgid') is needed because not all msgid/msgstr
            # pairs in the plone pos have a leading comment
            if (l[0] == '#' or l.startswith('msgid')) and section == STR:
                self.add(msgid, msgstr, fuzzy)
                section = None
                fuzzy = 0
            # Record a fuzzy mark
            if l[:2] == '#,' and 'fuzzy' in l:
                fuzzy = 1
            # Skip comments
            if l[0] == '#':
                continue
            # Now we are in a msgid section, output previous section
            if l.startswith('msgid'):
                section = ID
                l = l[5:]
                msgid = msgstr = ''
            # Now we are in a msgstr section
            elif l.startswith('msgstr'):
                section = STR
                l = l[6:]
            # Skip empty lines
            l = l.strip()
            if not l:
                continue
            # XXX: Does this always follow Python escape semantics?
            # XXX: eval is evil because it could be abused
            try:
                l = eval(l, globals())
            except Exception, msg:
                raise PoSyntaxError('%s (line %d of po file %s): \n%s' % (msg, lno, self.name, l))
            if section == ID:
                msgid += l
            elif section == STR:
                msgstr += l
            else:
                raise PoSyntaxError('error in line %d of po file %s' % (lno, self.name))

        # Add last entry
        if section == STR:
            self.add(msgid, msgstr, fuzzy)

        # Compute output
        return self.generate()

    def getAsFile(self):
        return StringIO(self.get())

    def __call__(self):
        return self.getAsFile()

########NEW FILE########
__FILENAME__ = multidict
# -*- coding: utf-8 -*-
import cgi
import copy
from UserDict import DictMixin
from webob.multidict import MultiDict

class UnicodeMultiDict(DictMixin):
    """
    A MultiDict wrapper that decodes returned values to unicode on the
    fly. Decoding is not applied to assigned values.

    The key/value contents are assumed to be ``str``/``strs`` or
    ``str``/``FieldStorages`` (as is returned by the ``paste.request.parse_``
    functions).

    Can optionally also decode keys when the ``decode_keys`` argument is
    True.

    ``FieldStorage`` instances are cloned, and the clone's ``filename``
    variable is decoded. Its ``name`` variable is decoded when ``decode_keys``
    is enabled.

    """
    def __init__(self, multi, encoding=None, errors='strict',
                 decode_keys=False):
        self.multi = multi
        if encoding is None:
            encoding = sys.getdefaultencoding()
        self.encoding = encoding
        self.errors = errors
        self.decode_keys = decode_keys

    def _decode_key(self, key):
        if self.decode_keys:
            try:
                key = key.decode(self.encoding, self.errors)
            except AttributeError:
                pass
        return key

    def _encode_key(self, key):
        if self.decode_keys and isinstance(key, unicode):
            return key.encode(self.encoding, self.errors)
        return key

    def _decode_value(self, value):
        """
        Decode the specified value to unicode. Assumes value is a ``str`` or
        `FieldStorage`` object.

        ``FieldStorage`` objects are specially handled.
        """
        if isinstance(value, cgi.FieldStorage):
            # decode FieldStorage's field name and filename
            value = copy.copy(value)
            if self.decode_keys:
                if not isinstance(value.name, unicode):
                    value.name = value.name.decode(self.encoding, self.errors)
            if value.filename:
                if not isinstance(value.filename, unicode):
                    value.filename = value.filename.decode(self.encoding,
                                                           self.errors)
        elif not isinstance(value, unicode):
            try:
                value = value.decode(self.encoding, self.errors)
            except AttributeError:
                pass
        return value

    def _encode_value(self, value):
        if isinstance(value, unicode):
            value = value.encode(self.encoding, self.errors)
        return value

    def __getitem__(self, key):
        return self._decode_value(self.multi.__getitem__(self._encode_key(key)))

    def __setitem__(self, key, value):
        self.multi.__setitem__(self._encode_key(key), self._encode_value(value))

    def add(self, key, value):
        """
        Add the key and value, not overwriting any previous value.
        """
        self.multi.add(self._encode_key(key), self._encode_value(value))

    def getall(self, key):
        """
        Return a list of all values matching the key (may be an empty list)
        """
        return map(self._decode_value, self.multi.getall(self._encode_key(key)))

    def getone(self, key):
        """
        Get one value matching the key, raising a KeyError if multiple
        values were found.
        """
        return self._decode_value(self.multi.getone(self._encode_key(key)))

    def mixed(self):
        """
        Returns a dictionary where the values are either single
        values, or a list of values when a key/value appears more than
        once in this dictionary.  This is similar to the kind of
        dictionary often used to represent the variables in a web
        request.
        """
        unicode_mixed = {}
        for key, value in self.multi.mixed().iteritems():
            if isinstance(value, list):
                value = [self._decode_value(value) for value in value]
            else:
                value = self._decode_value(value)
            unicode_mixed[self._decode_key(key)] = value
        return unicode_mixed

    def dict_of_lists(self):
        """
        Returns a dictionary where each key is associated with a
        list of values.
        """
        unicode_dict = {}
        for key, value in self.multi.dict_of_lists().iteritems():
            value = [self._decode_value(value) for value in value]
            unicode_dict[self._decode_key(key)] = value
        return unicode_dict

    def __delitem__(self, key):
        self.multi.__delitem__(self._encode_key(key))

    def __contains__(self, key):
        return self.multi.__contains__(self._encode_key(key))

    has_key = __contains__

    def clear(self):
        self.multi.clear()

    def copy(self):
        return UnicodeMultiDict(self.multi.copy(), self.encoding, self.errors)

    def setdefault(self, key, default=None):
        return self._decode_value(
            self.multi.setdefault(self._encode_key(key),
                                  self._encode_value(default)))

    def pop(self, key, *args):
        return self._decode_value(self.multi.pop(self._encode_key(key), *args))

    def popitem(self):
        k, v = self.multi.popitem()
        return (self._decode_key(k), self._decode_value(v))

    def __repr__(self):
        items = map('(%r, %r)'.__mod__, _hide_passwd(self.iteritems()))
        return '%s([%s])' % (self.__class__.__name__, ', '.join(items))

    def __len__(self):
        return self.multi.__len__()

    ##
    ## All the iteration:
    ##

    def keys(self):
        return [self._decode_key(k) for k in self.multi.iterkeys()]

    def iterkeys(self):
        for k in self.multi.iterkeys():
            yield self._decode_key(k)

    __iter__ = iterkeys

    def items(self):
        return [(self._decode_key(k), self._decode_value(v))
                for k, v in self.multi.iteritems()]

    def iteritems(self):
        for k, v in self.multi.iteritems():
            yield (self._decode_key(k), self._decode_value(v))

    def values(self):
        return [self._decode_value(v) for v in self.multi.itervalues()]

    def itervalues(self):
        for v in self.multi.itervalues():
            yield self._decode_value(v)

def _hide_passwd(items):
    for k, v in items:
        if ('password' in k
            or 'passwd' in k
            or 'pwd' in k
        ):
            yield k, '******'
        else:
            yield k, v

########NEW FILE########
__FILENAME__ = tables
# Copyright (C) 2007 Alexandre Conrad, alexandre (dot) conrad (at) gmail (dot) com
#
# This module is part of FormAlchemy and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

import helpers as h

from formalchemy import config
from formalchemy.forms import FieldSet

from tempita import Template as TempitaTemplate # must import after base


__all__ = ["Grid"]

def _validate_iterable(o):
    try:
        iter(o)
    except:
        raise Exception('instances must be an iterable, not %s' % o)


class Grid(FieldSet):
    """
    Besides `FieldSet`, `FormAlchemy` provides `Grid` for editing and
    rendering multiple instances at once.  Most of what you know about
    `FieldSet` applies to `Grid`, with the following differences to
    accomodate being bound to multiple objects:

    The `Grid` constructor takes the following arguments:

    * `cls`: the class type that the `Grid` will render (NOT an instance)

    * `instances=[]`: the instances to render as grid rows

    * `session=None`: as in `FieldSet`

    * `data=None`: as in `FieldSet`

    * `request=None`: as in `FieldSet`

    `bind` and `rebind` take the last 3 arguments (`instances`, `session`,
    and `data`); you may not specify a different class type than the one
    given to the constructor.

    The `Grid` `errors` attribute is a dictionary keyed by bound instance,
    whose value is similar to the `errors` from a `FieldSet`, that is, a
    dictionary whose keys are `Field`s, and whose values are
    `ValidationError` instances.
    """
    engine = _render = _render_readonly = None

    def __init__(self, cls, instances=[], session=None, data=None,
                 request=None, prefix=None):
        if self.__sa__:
            from sqlalchemy.orm import class_mapper
            if not class_mapper(cls):
                raise Exception('Grid must be bound to an SA mapped class')
        FieldSet.__init__(self, model=cls, session=session, data=data,
                          request=request, prefix=prefix)
        self.rows = instances
        self.readonly = False
        self._errors = {}

    def configure(self, **kwargs):
        """
        The `Grid` `configure` method takes the same arguments as `FieldSet`
        (`pk`, `exclude`, `include`, `options`, `readonly`), except there is
        no `focus` argument.
        """
        if 'focus' in kwargs:
            del kwargs['focus']
        FieldSet.configure(self, **kwargs)

    def bind(self, instances, session=None, data=None, request=None):
        """bind to instances"""
        _validate_iterable(instances)
        if not session:
            i = iter(instances)
            try:
                instance = i.next()
            except StopIteration:
                pass
            else:
                from sqlalchemy.orm import object_session
                session = object_session(instance)
        mr = FieldSet.bind(self, self.model, session, data, request)
        mr.rows = instances
        mr._request = request
        return mr

    def rebind(self, instances=None, session=None, data=None, request=None):
        """rebind to instances"""
        if instances is not None:
            _validate_iterable(instances)
        FieldSet.rebind(self, self.model, session, data, request)
        if instances is not None:
            self.rows = instances

    def copy(self, *args):
        """return a copy of the fieldset. args is a list of field names or field
        objects to render in the new fieldset"""
        mr = FieldSet.bind(self, self.model, self.session)
        mr.rows = []
        mr.readonly = self.readonly
        mr._errors = {}
        _fields = self._render_fields or self._fields
        _new_fields = []
        if args:
            for field in args:
                if isinstance(field, basestring):
                    if field in _fields:
                        field = _fields.get(field)
                    else:
                        raise AttributeError('%r as not field named %s' % (self, field))
                assert isinstance(field, fields.AbstractField), field
                field.bind(mr)
                _new_fields.append(field)
            mr._render_fields = OrderedDict([(field.key, field) for field in _new_fields])
        return mr


    def render(self, **kwargs):
        engine = self.engine or config.engine
        if self._render or self._render_readonly:
            import warnings
            warnings.warn(DeprecationWarning('_render and _render_readonly are deprecated and will be removed in 1.5. Use a TemplateEngine instead'))
        if self.readonly:
            if self._render_readonly is not None:
                engine._update_args(kwargs)
                return self._render_readonly(collection=self, **kwargs)
            return engine('grid_readonly', collection=self, **kwargs)
        if 'request' not in kwargs:
            kwargs['request'] = self._request
        if self._render is not None:
            engine._update_args(kwargs)
            return self._render(collection=self, **kwargs)
        return engine('grid', collection=self, **kwargs)

    def _set_active(self, instance, session=None):
        FieldSet.rebind(self, instance, session or self.session, self.data)

    def get_errors(self, row):
        if self._errors:
            return self._errors.get(row, {})
        return {}

    @property
    def errors(self):
        return self._errors

    def validate(self):
        """These are the same as in `FieldSet`"""
        if self.data is None:
            raise Exception('Cannot validate without binding data')
        if self.readonly:
            raise Exception('Cannot validate a read-only Grid')
        self._errors.clear()
        success = True
        for row in self.rows:
            self._set_active(row)
            row_errors = {}
            for field in self.render_fields.itervalues():
                success = field._validate() and success
                if field.errors:
                    row_errors[field] = field.errors
            self._errors[row] = row_errors
        return success

    def sync_one(self, row):
        """
        Use to sync a single one of the instances that are
        bound to the `Grid`.
        """
        # we want to allow the user to sync just rows w/o errors, so this is public
        if self.readonly:
            raise Exception('Cannot sync a read-only Grid')
        self._set_active(row)
        FieldSet.sync(self)

    def sync(self):
        """These are the same as in `FieldSet`"""
        for row in self.rows:
            self.sync_one(row)

########NEW FILE########
__FILENAME__ = templates
# -*- coding: utf-8 -*-
import os
import sys

from formalchemy.i18n import get_translator
from formalchemy import helpers

from tempita import Template as TempitaTemplate
try:
    from mako.lookup import TemplateLookup
    from mako.template import Template as MakoTemplate
    from mako.exceptions import TopLevelLookupException
    HAS_MAKO = True
except ImportError:
    HAS_MAKO = False
try:
    from genshi.template import TemplateLoader as GenshiTemplateLoader
    HAS_GENSHI = True
except ImportError:
    HAS_GENSHI = False

MAKO_TEMPLATES = os.path.join(
        os.path.dirname(__file__),
        'paster_templates','pylons_fa','+package+','templates', 'forms')

class TemplateEngine(object):
    """Base class for templates engines
    """
    directories = []
    extension = None
    _templates = ['fieldset', 'fieldset_readonly',
                  'grid', 'grid_readonly']
    def __init__(self, **kw):
        self.templates = {}
        if 'extension' in kw:
            self.extension = kw.pop('extension')
        if 'directories' in kw:
            self.directories = list(kw.pop('directories'))
        for name in self._templates:
            self.templates[name] = self.get_template(name, **kw)

    def get_template(self, name, **kw):
        """return the template object for `name`. Must be override by engines"""
        return None

    def get_filename(self, name):
        """return the filename for template `name`"""
        for dirname in self.directories + [os.path.dirname(__file__)]:
            filename = os.path.join(dirname, '%s.%s' % (name, self.extension))
            if os.path.isfile(filename):
                return filename

    def render(self, template_name, **kwargs):
        """render the template. Must be override by engines"""
        return ''

    def _update_args(cls, kw):
        kw['F_'] = get_translator(lang=kw.get('lang', None),
                                  request=kw.get('request', None))
        kw['html'] = helpers
        return kw
    _update_args = classmethod(_update_args)

    def __call__(self, template_name, **kw):
        """update kw to extend the namespace with some FA's utils then call `render`"""
        self._update_args(kw)
        return self.render(template_name, **kw)

class TempitaEngine(TemplateEngine):
    """Template engine for tempita. File extension is `.tmpl`.
    """
    extension = 'tmpl'
    def get_template(self, name, **kw):
        filename = self.get_filename(name)
        if filename:
            return TempitaTemplate.from_filename(filename, **kw)

    def render(self, template_name, **kwargs):
        template = self.templates.get(template_name, None)
        return template.substitute(**kwargs)

class MakoEngine(TemplateEngine):
    """Template engine for mako. File extension is `.mako`.
    """
    extension = 'mako'
    _lookup = None
    def get_template(self, name, **kw):
        if self._lookup is None:
            self._lookup = TemplateLookup(directories=self.directories, **kw)
        try:
            return self._lookup.get_template('%s.%s' % (name, self.extension))
        except TopLevelLookupException:
            filename = os.path.join(MAKO_TEMPLATES, '%s.mako_tmpl' % name)
            if os.path.isfile(filename):
                template = TempitaTemplate.from_filename(filename)
                return MakoTemplate(template.substitute(template_engine='mako'), **kw)

    def render(self, template_name, **kwargs):
        template = self.templates.get(template_name, None)
        return template.render_unicode(**kwargs)

class GenshiEngine(TemplateEngine):
    """Template engine for genshi. File extension is `.html`.
    """
    extension = 'html'
    def get_template(self, name, **kw):
        filename = self.get_filename(name)
        if filename:
            loader = GenshiTemplateLoader(os.path.dirname(filename), **kw)
            return loader.load(os.path.basename(filename))

    def render(self, template_name, **kwargs):
        template = self.templates.get(template_name, None)
        return template.generate(**kwargs).render('html', doctype=None)


if HAS_MAKO:
    default_engine = MakoEngine(input_encoding='utf-8', output_encoding='utf-8')
    engines = dict(mako=default_engine, tempita=TempitaEngine())
else:
    default_engine = TempitaEngine()
    engines = dict(tempita=TempitaEngine())

########NEW FILE########
__FILENAME__ = fake_module
# -*- coding: utf-8 -*-
#used to simulate the library module used in doctests


########NEW FILE########
__FILENAME__ = test_aliases
# -*- coding: utf-8 -*-
from formalchemy.tests import *


def test_aliases():
    fs = FieldSet(Aliases)
    fs.bind(Aliases)
    assert fs.id.name == 'id'

def test_render_aliases():
    """
    >>> alias = session.query(Aliases).first()
    >>> alias
    >>> fs = FieldSet(Aliases)
    >>> print fs.render()
    <div>
     <label class="field_opt" for="Aliases--text">
      Text
     </label>
     <input id="Aliases--text" name="Aliases--text" type="text" />
    </div>
    <script type="text/javascript">
     //<![CDATA[
    document.getElementById("Aliases--text").focus();
    //]]>
    </script>
    """


########NEW FILE########
__FILENAME__ = test_binary
import cgi
import shutil
import tempfile
from StringIO import StringIO

from formalchemy.fields import FileFieldRenderer
from formalchemy.ext import fsblob
from formalchemy.tests import *
from webtest import TestApp, selenium
from webob import multidict

BOUNDARY='testdata'
ENVIRON = {
        'REQUEST_METHOD':'POST',
        'CONTENT_TYPE': 'multipart/form-data;boundary="%s"' % BOUNDARY
        }
TEST_DATA = '''--%s
Content-Disposition: form-data; name="Binaries--file"; filename="test.js"
Content-Type: application/x-javascript

var test = null;

--%s--
''' % (BOUNDARY, BOUNDARY)
EMPTY_DATA = '''--%s
Content-Disposition: form-data; name="Binaries--file"; filename=""
Content-Type: application/x-javascript

--%s--
''' % (BOUNDARY, BOUNDARY)
REMOVE_DATA = '''--%s
Content-Disposition: form-data; name="Binaries--file--remove"
1
--%s
Content-Disposition: form-data; name="Binaries--file"; filename=""
Content-Type: application/x-javascript

--%s--
''' % (BOUNDARY, BOUNDARY, BOUNDARY)


def get_fields(data):
    return multidict.MultiDict.from_fieldstorage(cgi.FieldStorage(fp=StringIO(data), environ=ENVIRON))

def test_binary():
    r"""

    Notice that those tests assume that the FileFieldRenderer work with LargeBinary type
    *and* String type if you only want to store file path in your DB.

    Configure a fieldset with a file field

        >>> fs = FieldSet(Three)
        >>> record = fs.model
        >>> fs.configure(include=[fs.bar.with_renderer(FileFieldRenderer)])
        >>> isinstance(fs.bar.renderer, FileFieldRenderer)
        True

    At creation time only the input field is rendered

        >>> print fs.render()
        <div>
         <label class="field_opt" for="Three--bar">
          Bar
         </label>
         <input id="Three--bar" name="Three--bar" type="file" />
        </div>
        <script type="text/javascript">
         //<![CDATA[
        document.getElementById("Three--bar").focus();
        //]]>
        </script>

    If the field has a value then we add a check box to remove it

        >>> record.bar = '/path/to/file'
        >>> print fs.render()
        <div>
         <label class="field_opt" for="Three--bar">
          Bar
         </label>
         <input id="Three--bar" name="Three--bar" type="file" />
         <input id="Three--bar--remove" name="Three--bar--remove" type="checkbox" value="1" />
         <label for="Three--bar--remove">
          Remove
         </label>
        </div>
        <script type="text/javascript">
         //<![CDATA[
        document.getElementById("Three--bar").focus();
        //]]>
        </script>

    Now submit form with empty value

        >>> fs.rebind(data={'Three--bar':''})
        >>> fs.validate()
        True
        >>> fs.sync()

    The field value does not change

        >>> print record.bar
        /path/to/file

    Try to remove it by checking the checkbox

        >>> fs.rebind(data={'Three--bar':'', 'Three--bar--remove':'1'})
        >>> fs.validate()
        True
        >>> fs.sync()

    The field value is removed

        >>> print record.bar
        <BLANKLINE>

    Also check that this work with cgi.FieldStorage

        >>> fs = FieldSet(Binaries)
        >>> record = fs.model

    We need test data

        >>> data = get_fields(TEST_DATA)
        >>> print data.getone('Binaries--file')
        FieldStorage(u'Binaries--file', u'test.js')

        >>> fs.rebind(data=data)
        >>> if fs.validate(): fs.sync()

    We get the file, yeah.

        >>> print record.file
        var test = null;
        <BLANKLINE>

    Now submit form with empty value

        >>> data = get_fields(EMPTY_DATA)
        >>> fs.rebind(data=data)
        >>> if fs.validate(): fs.sync()

    The field value dos not change

        >>> print record.file
        var test = null;
        <BLANKLINE>

    Remove file

        >>> data = get_fields(REMOVE_DATA)
        >>> fs.rebind(data=data)
        >>> if fs.validate(): fs.sync()

    The field value is now empty

        >>> print record.file
        <BLANKLINE>

    See what append in read only mode

        >>> record.file = 'e'*1000
        >>> print fs.file.render_readonly()
        1 KB

        >>> record.file = 'e'*1000*1024
        >>> print fs.file.render_readonly()
        1000.00 KB

        >>> record.file = 'e'*2*1024*1024
        >>> print fs.file.render_readonly()
        2.00 MB

    """

class BlobTestCase(unittest.TestCase):

    renderer = fsblob.FileFieldRenderer

    def setUp(self):
        self.wd = tempfile.mkdtemp()
        self.binary = Three()
        self.fs = FieldSet(Three)
        self.fs.configure(include=[self.fs.bar, self.fs.foo])
        self.fs.foo.set(renderer=self.renderer.new(
                        storage_path=self.wd,
                        url_prefix='/media'))
        self.app = TestApp(application(self.binary, self.fs))

    def test_file(self):
        resp = self.app.get('/')
        resp.mustcontain('type="file"')
        resp = self.app.post('/', {"Three--bar":'bar'},
                             upload_files=[('Three--foo', 'foo.txt', 'data')])
        resp = self.app.get('/')
        resp.mustcontain('<a href="/media/', '/foo.txt">', 'foo.txt (1 KB)')
        self.assert_(self.binary.foo.endswith('foo.txt'), repr(self.binary.foo))
        resp = self.app.get('/')
        resp.mustcontain('name="Three--foo--remove"',
                         '<a href="/media/', '/foo.txt">', 'foo.txt (1 KB)')

        # no change
        form = resp.form
        resp = form.submit()
        resp.mustcontain('<a href="/media/', '/foo.txt">', 'foo.txt (1 KB)')
        self.assert_(self.binary.foo.endswith('foo.txt'), repr(self.binary.foo))

        # remove file
        resp = self.app.get('/')
        form = resp.form
        form['Three--foo--remove'] = '1'
        resp = form.submit()
        self.assert_(self.binary.foo == '', repr(self.binary.foo))
        resp.mustcontain(no='foo.txt (1 KB)')

    def tearDown(self):
        shutil.rmtree(self.wd)


########NEW FILE########
__FILENAME__ = test_column
# -*- coding: utf-8 -*-
from formalchemy.tests import *

class Label(Base):
    __tablename__ = 'label'
    id = Column(Integer, primary_key=True)
    label = Column(String, label='My label')

def test_label():
    """
    >>> Label.__table__.c.label.info
    {'label': 'My label'}
    >>> fs = FieldSet(Label)
    >>> print fs.label.label_text
    My label
    >>> print fs.label.label()
    My label
    """

def test_fk_label(self):
    """
    >>> fs = FieldSet(Order)
    >>> print fs.user.label_text
    User
    >>> print fs.user.label()
    User
    """


########NEW FILE########
__FILENAME__ = test_dates
from formalchemy.tests import *
from formalchemy.fields import DateTimeFieldRenderer
import datetime


class Dt(Base):
    __tablename__ = 'dts'
    id = Column('id', Integer, primary_key=True)
    foo = Column('foo', Date, nullable=True)
    bar = Column('bar', Time, nullable=True)
    foobar = Column('foobar', DateTime, nullable=True)

class DateTimeFieldRendererFr(DateTimeFieldRenderer):
    edit_format = 'd-m-y'

def test_dt_hang_up():
    """
    >>> class MyClass(object):
    ...     td = Field(type=types.DateTime, value=datetime.datetime.now())
    ...     t = Field().required()
    >>> MyFS = FieldSet(MyClass)

    >>> fs = MyFS.bind(model=MyClass, data={
    ...     'MyClass--td__year': '2011',
    ...     'MyClass--td__month': '12',
    ...     'MyClass--td__day': '12',
    ...     'MyClass--td__hour': '17',
    ...     'MyClass--td__minute': '28',
    ...     'MyClass--td__second': '49',
    ...     'MyClass--t': ""})

    >>> fs.validate()
    False

    >>> print pretty_html(fs.td.render()) #doctest: +ELLIPSIS
    <span id="MyClass--td">
     <select id="MyClass--td__month" name="MyClass--td__month">
      ...
      <option selected="selected" value="12">
       December
      </option>
     </select>
     <select id="MyClass--td__day" name="MyClass--td__day">
      <option value="DD">
       Day
      </option>
      ...
      <option selected="selected" value="12">
       12
      </option>
      ...
     </select>
     <input id="MyClass--td__year" maxlength="4" name="MyClass--td__year" size="4" type="text" value="2011" />
     <select id="MyClass--td__hour" name="MyClass--td__hour">
      <option value="HH">
       HH
      </option>
      ...
      <option selected="selected" value="17">
       17
      </option>
      ...
     </select>
     :
     <select id="MyClass--td__minute" name="MyClass--td__minute">
      <option value="MM">
       MM
      </option>
      ...
      <option selected="selected" value="28">
       28
      </option>
      ...
     </select>
     :
     <select id="MyClass--td__second" name="MyClass--td__second">
      <option value="SS">
       SS
      </option>
      ...
      <option selected="selected" value="49">
       49
      </option>
      ...
     </select>
    </span>

    >>> fs.td.value
    datetime.datetime(2011, 12, 12, 17, 28, 49)
    """

def test_hidden():
    """
    >>> fs = FieldSet(Dt)
    >>> _ = fs.foo.set(hidden=True)
    >>> print pretty_html(fs.foo.render()) #doctest: +ELLIPSIS
    <div style="display:none;">
     <span id="Dt--foo">
    ...

    >>> _ = fs.bar.set(hidden=True)
    >>> print pretty_html(fs.bar.render()) #doctest: +ELLIPSIS
    <div style="display:none;">
     <span id="Dt--bar">
    ...

    >>> _ = fs.foobar.set(hidden=True)
    >>> print pretty_html(fs.foobar.render()) #doctest: +ELLIPSIS
    <div style="display:none;">
     <span id="Dt--foobar">
    ...
    """



__doc__ = r"""
>>> fs = FieldSet(Dt)
>>> fs.configure(options=[fs.foobar.with_renderer(DateTimeFieldRendererFr)])
>>> print pretty_html(fs.foobar.with_html(lang='fr').render()) #doctest: +ELLIPSIS
<span id="Dt--foobar">
 <select id="Dt--foobar__day" lang="fr" name="Dt--foobar__day">
  <option selected="selected" value="DD">
   Jour
  </option>
...
 <select id="Dt--foobar__month" lang="fr" name="Dt--foobar__month">
  <option selected="selected" value="MM">
   Mois
  </option>
  <option value="1">
   Janvier
  </option>
...

>>> fs = FieldSet(Dt)
>>> print pretty_html(fs.foobar.render()) #doctest: +ELLIPSIS
<span id="Dt--foobar">
 <select id="Dt--foobar__month" name="Dt--foobar__month">
  <option selected="selected" value="MM">
   Month
  </option>
  ...
 </select>
 <select id="Dt--foobar__day" name="Dt--foobar__day">
  <option selected="selected" value="DD">
   Day
  </option>
  ...
 </select>
 <input id="Dt--foobar__year" maxlength="4" name="Dt--foobar__year" size="4" type="text" value="YYYY" />
 <select id="Dt--foobar__hour" name="Dt--foobar__hour">
  <option selected="selected" value="HH">
   HH
  </option>
  ...
 </select>
 :
 <select id="Dt--foobar__minute" name="Dt--foobar__minute">
  <option selected="selected" value="MM">
   MM
  </option>
  ...
 </select>
 :
 <select id="Dt--foobar__second" name="Dt--foobar__second">
  <option selected="selected" value="SS">
   SS
  </option>
  ...
 </select>
</span>

>>> fs = FieldSet(Dt)
>>> dt = fs.model
>>> dt.foo = datetime.date(2008, 6, 3);  dt.bar=datetime.time(14, 16, 18);  dt.foobar=datetime.datetime(2008, 6, 3, 14, 16, 18)
>>> print pretty_html(fs.foo.render()) #doctest: +ELLIPSIS
<span id="Dt--foo">
 <select id="Dt--foo__month" name="Dt--foo__month">
  <option value="MM">
   Month
  </option>
  ...
  <option selected="selected" value="6">
   June
  </option>
  ...
 </select>
 <select id="Dt--foo__day" name="Dt--foo__day">
  <option value="DD">
   Day
  </option>
  ...
  <option selected="selected" value="3">
   3
  </option>
  ...
  <option value="31">
   31
  </option>
 </select>
 <input id="Dt--foo__year" maxlength="4" name="Dt--foo__year" size="4" type="text" value="2008" />
</span>

>>> print pretty_html(fs.bar.render()) #doctest: +ELLIPSIS
<span id="Dt--bar">
 <select id="Dt--bar__hour" name="Dt--bar__hour">
  <option value="HH">
   HH
  </option>
  <option value="0">
   0
  </option>
  ...
  <option value="13">
   13
  </option>
  <option selected="selected" value="14">
   14
  </option>
  ...
  <option value="23">
   23
  </option>
 </select>
 :
 <select id="Dt--bar__minute" name="Dt--bar__minute">
  <option value="MM">
   MM
  </option>
  <option value="0">
   0
  </option>
  ...
  <option value="15">
   15
  </option>
  <option selected="selected" value="16">
   16
  </option>
  <option value="17">
   17
  </option>
  ...
  <option value="59">
   59
  </option>
 </select>
 :
 <select id="Dt--bar__second" name="Dt--bar__second">
  <option value="SS">
   SS
  </option>
  <option value="0">
   0
  </option>
  ...
  <option value="17">
   17
  </option>
  <option selected="selected" value="18">
   18
  </option>
  <option value="19">
   19
  </option>
  ...
  <option value="59">
   59
  </option>
 </select>
</span>

>>> print pretty_html(fs.foobar.render()) #doctest: +ELLIPSIS
<span id="Dt--foobar">
 <select id="Dt--foobar__month" name="Dt--foobar__month">
  <option value="MM">
   Month
  </option>
  ...
  <option selected="selected" value="6">
   June
  </option>
  ...
 </select>
 <select id="Dt--foobar__day" name="Dt--foobar__day">
  <option value="DD">
   Day
  </option>
  ...
  <option selected="selected" value="3">
   3
  </option>
  ...
 </select>
 <input id="Dt--foobar__year" maxlength="4" name="Dt--foobar__year" size="4" type="text" value="2008" />
 <select id="Dt--foobar__hour" name="Dt--foobar__hour">
  <option value="HH">
   HH
  </option>
  ...
  <option selected="selected" value="14">
   14
  </option>
  ...
 </select>
 :
 <select id="Dt--foobar__minute" name="Dt--foobar__minute">
  <option value="MM">
   MM
  </option>
  ...
  <option selected="selected" value="16">
   16
  </option>
  ...
 </select>
 :
 <select id="Dt--foobar__second" name="Dt--foobar__second">
  <option value="SS">
   SS
  </option>
  ...
  <option selected="selected" value="18">
   18
  </option>
  ...
 </select>
</span>

>>> fs.rebind(dt, data={'Dt--foo__day': 'DD', 'Dt--foo__month': '2', 'Dt--foo__year': '', 'Dt--bar__hour': 'HH', 'Dt--bar__minute': '6', 'Dt--bar__second': '8'})
>>> print pretty_html(fs.foo.render()) #doctest: +ELLIPSIS
<span id="Dt--foo">
 <select id="Dt--foo__month" name="Dt--foo__month">
  <option value="MM">
   Month
  </option>
  <option value="1">
   January
  </option>
  <option selected="selected" value="2">
   February
  </option>
  ...
 </select>
 <select id="Dt--foo__day" name="Dt--foo__day">
  <option value="DD">
   Day
  </option>
  <option value="1">
   1
  </option>
  ...
  <option value="31">
   31
  </option>
 </select>
 <input id="Dt--foo__year" maxlength="4" name="Dt--foo__year" size="4" type="text" value="" />
</span>
>>> print pretty_html(fs.bar.render()) #doctest: +ELLIPSIS
<span id="Dt--bar">
 <select id="Dt--bar__hour" name="Dt--bar__hour">
  <option value="HH">
   HH
  </option>
  ...
  <option selected="selected" value="14">
   14
  </option>
  ...
 </select>
 :
 <select id="Dt--bar__minute" name="Dt--bar__minute">
  <option value="MM">
   MM
  </option>
  ...
  <option selected="selected" value="6">
   6
  </option>
  ...
 </select>
 :
 <select id="Dt--bar__second" name="Dt--bar__second">
  <option value="SS">
   SS
  </option>
  ...
  <option selected="selected" value="8">
   8
  </option>
  ...
 </select>
</span>

>>> fs.rebind(dt, data={'Dt--foo__day': '11', 'Dt--foo__month': '2', 'Dt--foo__year': '1951', 'Dt--bar__hour': '4', 'Dt--bar__minute': '6', 'Dt--bar__second': '8', 'Dt--foobar__day': '11', 'Dt--foobar__month': '2', 'Dt--foobar__year': '1951', 'Dt--foobar__hour': '4', 'Dt--foobar__minute': '6', 'Dt--foobar__second': '8'})
>>> fs.sync()
>>> dt.foo
datetime.date(1951, 2, 11)
>>> dt.bar
datetime.time(4, 6, 8)
>>> dt.foobar
datetime.datetime(1951, 2, 11, 4, 6, 8)
>>> session.rollback()

>>> fs.rebind(dt, data={'Dt--foo__day': 'DD', 'Dt--foo__month': 'MM', 'Dt--foo__year': 'YYYY', 'Dt--bar__hour': 'HH', 'Dt--bar__minute': 'MM', 'Dt--bar__second': 'SS', 'Dt--foobar__day': 'DD', 'Dt--foobar__month': 'MM', 'Dt--foobar__year': '', 'Dt--foobar__hour': 'HH', 'Dt--foobar__minute': 'MM', 'Dt--foobar__second': 'SS'})
>>> fs.validate()
True
>>> fs.sync()
>>> dt.foo is None
True
>>> dt.bar is None
True
>>> dt.foobar is None
True
>>> session.rollback()

>>> fs.rebind(dt, data={'Dt--foo__day': '1', 'Dt--foo__month': 'MM', 'Dt--foo__year': 'YYYY', 'Dt--bar__hour': 'HH', 'Dt--bar__minute': 'MM', 'Dt--bar__second': 'SS', 'Dt--foobar__day': 'DD', 'Dt--foobar__month': 'MM', 'Dt--foobar__year': '', 'Dt--foobar__hour': 'HH', 'Dt--foobar__minute': 'MM', 'Dt--foobar__second': 'SS'})
>>> fs.validate()
False
>>> fs.errors
{AttributeField(foo): ['Invalid date']}

>>> fs.rebind(dt, data={'Dt--foo__day': 'DD', 'Dt--foo__month': 'MM', 'Dt--foo__year': 'YYYY', 'Dt--bar__hour': 'HH', 'Dt--bar__minute': '1', 'Dt--bar__second': 'SS', 'Dt--foobar__day': 'DD', 'Dt--foobar__month': 'MM', 'Dt--foobar__year': '', 'Dt--foobar__hour': 'HH', 'Dt--foobar__minute': 'MM', 'Dt--foobar__second': 'SS'})
>>> fs.validate()
False
>>> fs.errors
{AttributeField(bar): ['Invalid time']}

>>> fs.rebind(dt, data={'Dt--foo__day': 'DD', 'Dt--foo__month': 'MM', 'Dt--foo__year': 'YYYY', 'Dt--bar__hour': 'HH', 'Dt--bar__minute': 'MM', 'Dt--bar__second': 'SS', 'Dt--foobar__day': '11', 'Dt--foobar__month': '2', 'Dt--foobar__year': '1951', 'Dt--foobar__hour': 'HH', 'Dt--foobar__minute': 'MM', 'Dt--foobar__second': 'SS'})
>>> fs.validate()
False
>>> fs.errors
{AttributeField(foobar): ['Incomplete datetime']}

>>> fs.rebind(dt)
>>> dt.bar = datetime.time(0)
>>> print fs.bar.render() #doctest: +ELLIPSIS
<span id="Dt--bar"><select id="Dt--bar__hour" name="Dt--bar__hour">
<option value="HH">HH</option>
<option selected="selected" value="0">0</option>
...

>>> print fs.bar.render_readonly()
00:00:00

>>> fs = FieldSet(Dt)
>>> print fs.bar.render() #doctest: +ELLIPSIS
<span id="Dt--bar"><select id="Dt--bar__hour" name="Dt--bar__hour">
<option selected="selected" value="HH">HH</option>
<option value="0">0</option>
...

"""

if __name__ == '__main__':
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = test_fieldset
__doc__ = r"""
>>> from formalchemy.tests import *

>>> FieldSet.default_renderers = original_renderers.copy()

# some low-level testing first

>>> fs = FieldSet(order1)
>>> fs._raw_fields()
[AttributeField(id), AttributeField(user_id), AttributeField(quantity), AttributeField(user)]
>>> fs.user.name
'user_id'

>>> fs = FieldSet(bill)
>>> fs._raw_fields()
[AttributeField(id), AttributeField(email), AttributeField(password), AttributeField(name), AttributeField(orders)]
>>> fs.orders.name
'orders'

binding should not change attribute order:
>>> fs = FieldSet(User)
>>> fs_bound = fs.bind(User)
>>> fs_bound._fields.values()
[AttributeField(id), AttributeField(email), AttributeField(password), AttributeField(name), AttributeField(orders)]

>>> fs = FieldSet(User2)
>>> fs._raw_fields()
[AttributeField(user_id), AttributeField(address_id), AttributeField(name), AttributeField(address)]

>>> fs.render() #doctest: +ELLIPSIS
Traceback (most recent call last):
...
Exception: No session found...

>>> fs = FieldSet(One)
>>> fs.configure(pk=True, focus=None)
>>> fs.id.is_required()
True
>>> print fs.render()
<div>
 <label class="field_req" for="One--id">
  Id
 </label>
 <input id="One--id" name="One--id" type="text" />
</div>

>>> fs = FieldSet(Two)
>>> fs
<FieldSet with ['id', 'foo']>
>>> fs.configure(pk=True)
>>> fs
<FieldSet (configured) with ['id', 'foo']>
>>> print fs.render()
<div>
 <label class="field_req" for="Two--id">
  Id
 </label>
 <input id="Two--id" name="Two--id" type="text" />
</div>
<script type="text/javascript">
 //<![CDATA[
document.getElementById("Two--id").focus();
//]]>
</script>
<div>
 <label class="field_opt" for="Two--foo">
  Foo
 </label>
 <input id="Two--foo" name="Two--foo" type="text" value="133" />
</div>

>>> fs = FieldSet(Two)
>>> print fs.render()
<div>
 <label class="field_opt" for="Two--foo">
  Foo
 </label>
 <input id="Two--foo" name="Two--foo" type="text" value="133" />
</div>
<script type="text/javascript">
 //<![CDATA[
document.getElementById("Two--foo").focus();
//]]>
</script>

>>> fs = FieldSet(Two)
>>> fs.configure(options=[fs.foo.label('A custom label')])
>>> print fs.render()
<div>
 <label class="field_opt" for="Two--foo">
  A custom label
 </label>
 <input id="Two--foo" name="Two--foo" type="text" value="133" />
</div>
<script type="text/javascript">
 //<![CDATA[
document.getElementById("Two--foo").focus();
//]]>
</script>
>>> fs.configure(options=[fs.foo.label('')])
>>> print fs.render()
<div>
 <label class="field_opt" for="Two--foo">
 </label>
 <input id="Two--foo" name="Two--foo" type="text" value="133" />
</div>
<script type="text/javascript">
 //<![CDATA[
document.getElementById("Two--foo").focus();
//]]>
</script>

>>> fs = FieldSet(Two)
>>> assert fs.render() == configure_and_render(fs, include=[fs.foo])
>>> assert fs.render() == configure_and_render(fs, exclude=[fs.id])

>>> fs = FieldSet(Two)
>>> fs.configure(include=[fs.foo.hidden()])
>>> print fs.render()
<input id="Two--foo" name="Two--foo" type="hidden" value="133" />

>>> fs = FieldSet(Two)
>>> fs.configure(include=[fs.foo.dropdown([('option1', 'value1'), ('option2', 'value2')])])
>>> print fs.render()
<div>
 <label class="field_opt" for="Two--foo">
  Foo
 </label>
 <select id="Two--foo" name="Two--foo">
  <option value="value1">
   option1
  </option>
  <option value="value2">
   option2
  </option>
 </select>
</div>
<script type="text/javascript">
 //<![CDATA[
document.getElementById("Two--foo").focus();
//]]>
</script>

>>> fs = FieldSet(Two)
>>> assert configure_and_render(fs, include=[fs.foo.dropdown([('option1', 'value1'), ('option2', 'value2')])]) == configure_and_render(fs, options=[fs.foo.dropdown([('option1', 'value1'), ('option2', 'value2')])]) 
>>> print pretty_html(fs.foo.with_html(onblur='test()').render())
<select id="Two--foo" name="Two--foo" onblur="test()">
 <option value="value1">
  option1
 </option>
 <option value="value2">
  option2
 </option>
</select>
>>> print fs.foo.reset().with_html(onblur='test').render()
<input id="Two--foo" name="Two--foo" onblur="test" type="text" value="133" />

# Test with_metadata()
>>> fs = FieldSet(Three)
>>> fs.configure(include=[fs.foo.with_metadata(instructions=u'Answer well')])
>>> print fs.render()
<div>
 <label class="field_opt" for="Three--foo">
  Foo
 </label>
 <input id="Three--foo" name="Three--foo" type="text" />
 <span class="instructions">
  Answer well
 </span>
</div>
<script type="text/javascript">
 //<![CDATA[
document.getElementById("Three--foo").focus();
//]]>
</script>

# test sync
>>> print session.query(One).count()
0
>>> fs_1 = FieldSet(One, data={}, session=session)
>>> fs_1.sync()
>>> session.flush()
>>> print session.query(One).count()
1
>>> session.rollback()

>>> twof = TwoFloat(id=1, foo=32.2)
>>> fs_twof = FieldSet(twof)
>>> print '%.1f' % fs_twof.foo.value
32.2
>>> print pretty_html(fs_twof.foo.render())
<input id="TwoFloat-1-foo" name="TwoFloat-1-foo" type="text" value="32.2" />

>>> import datetime
>>> twoi = TwoInterval(id=1, foo=datetime.timedelta(2.2))
>>> fs_twoi = FieldSet(twoi)
>>> fs_twoi.foo.renderer
<IntervalFieldRenderer for AttributeField(foo)>
>>> fs_twoi.foo.value
datetime.timedelta(2, 17280)
>>> print pretty_html(fs_twoi.foo.render())
<input id="TwoInterval-1-foo" name="TwoInterval-1-foo" type="text" value="2.17280" />
>>> fs_twoi.rebind(data={"TwoInterval-1-foo": "3.1"})
>>> fs_twoi.sync()
>>> new_twoi = fs_twoi.model
>>> new_twoi.foo == datetime.timedelta(3.1)
True

# test render and sync fatypes.Numeric
# http://code.google.com/p/formalchemy/issues/detail?id=41
>>> twon = TwoNumeric(id=1, foo=Decimal('2.3'))
>>> fs_twon = FieldSet(twon)
>>> print pretty_html(fs_twon.foo.render())
<input id="TwoNumeric-1-foo" name="TwoNumeric-1-foo" type="text" value="2.3" />
>>> fs_twon.rebind(data={"TwoNumeric-1-foo": "6.7"})
>>> fs_twon.sync()
>>> new_twon = fs_twon.model
>>> new_twon.foo == Decimal("6.7")
True

# test sync when TwoNumeric-1-foo is empty
>>> fs_twon.rebind(data={"TwoNumeric-1-foo": ""})
>>> fs_twon.sync()
>>> new_twon = fs_twon.model
>>> str(new_twon.foo)
'None'

>>> fs_cb = FieldSet(CheckBox)
>>> fs_cb.field.value is None
True
>>> print pretty_html(fs_cb.field.dropdown().render())
<select id="CheckBox--field" name="CheckBox--field">
 <option value="True">
  Yes
 </option>
 <option value="False">
  No
 </option>
</select>

# test no checkbox/radio submitted
>>> fs_cb.rebind(data={})
>>> fs_cb.field.raw_value is None
True
>>> fs_cb.field.value
False
>>> fs_cb.field.renderer.value is None
True
>>> print fs_cb.field.render()
<input id="CheckBox--field" name="CheckBox--field" type="checkbox" value="True" />
>>> fs_cb.field.renderer #doctest: +ELLIPSIS
<CheckBoxFieldRenderer for AttributeField(field)>
>>> fs_cb.field.renderer._serialized_value() is None
True
>>> print pretty_html(fs_cb.field.radio().render())
<input id="CheckBox--field_0" name="CheckBox--field" type="radio" value="True" />
<label for="CheckBox--field_0">
 Yes
</label>
<br />
<input id="CheckBox--field_1" name="CheckBox--field" type="radio" value="False" />
<label for="CheckBox--field_1">
 No
</label>

>>> fs_cb.validate()
True
>>> fs_cb.errors
{}
>>> fs_cb.sync()
>>> cb = fs_cb.model
>>> cb.field
False
>>> fs_cb.rebind(data={'CheckBox--field': 'True'})
>>> fs_cb.validate()
True
>>> fs_cb.sync()
>>> cb.field
True
>>> fs_cb.configure(options=[fs_cb.field.dropdown()])
>>> fs_cb.rebind(data={'CheckBox--field': 'False'})
>>> fs_cb.sync()
>>> cb.field
False

>>> fs = FieldSet(Two)
>>> print pretty_html(fs.foo.dropdown(options=['one', 'two']).radio().render())
<input id="Two--foo_0" name="Two--foo" type="radio" value="one" />
<label for="Two--foo_0">
 one
</label>
<br />
<input id="Two--foo_1" name="Two--foo" type="radio" value="two" />
<label for="Two--foo_1">
 two
</label>

>>> assert fs.foo.radio(options=['one', 'two']).render() == fs.foo.dropdown(options=['one', 'two']).radio().render()
>>> print fs.foo.radio(options=['one', 'two']).dropdown().render()
<select id="Two--foo" name="Two--foo">
<option value="one">one</option>
<option value="two">two</option>
</select>

>>> assert fs.foo.dropdown(options=['one', 'two']).render() == fs.foo.radio(options=['one', 'two']).dropdown().render()
>>> print pretty_html(fs.foo.dropdown(options=['one', 'two'], multiple=True).checkbox().render())
<input id="Two--foo_0" name="Two--foo" type="checkbox" value="one" />
<label for="Two--foo_0">
 one
</label>
<br />
<input id="Two--foo_1" name="Two--foo" type="checkbox" value="two" />
<label for="Two--foo_1">
 two
</label>

>>> fs = FieldSet(User, session=session)
>>> print fs.render()
<div>
 <label class="field_req" for="User--email">
  Email
 </label>
 <input id="User--email" maxlength="40" name="User--email" type="text" />
</div>
<script type="text/javascript">
 //<![CDATA[
document.getElementById("User--email").focus();
//]]>
</script>
<div>
 <label class="field_req" for="User--password">
  Password
 </label>
 <input id="User--password" maxlength="20" name="User--password" type="text" />
</div>
<div>
 <label class="field_opt" for="User--name">
  Name
 </label>
 <input id="User--name" maxlength="30" name="User--name" type="text" />
</div>
<div>
 <label class="field_opt" for="User--orders">
  Orders
 </label>
 <select id="User--orders" multiple="multiple" name="User--orders" size="5">
  <option value="2">
   Quantity: 5
  </option>
  <option value="3">
   Quantity: 6
  </option>
  <option value="1">
   Quantity: 10
  </option>
 </select>
</div>

>>> fs = FieldSet(bill)
>>> print pretty_html(fs.orders.render())
<select id="User-1-orders" multiple="multiple" name="User-1-orders" size="5">
 <option value="2">
  Quantity: 5
 </option>
 <option value="3">
  Quantity: 6
 </option>
 <option selected="selected" value="1">
  Quantity: 10
 </option>
</select>
>>> print pretty_html(fs.orders.checkbox().render())
<input id="User-1-orders_0" name="User-1-orders" type="checkbox" value="2" />
<label for="User-1-orders_0">
 Quantity: 5
</label>
<br />
<input id="User-1-orders_1" name="User-1-orders" type="checkbox" value="3" />
<label for="User-1-orders_1">
 Quantity: 6
</label>
<br />
<input checked="checked" id="User-1-orders_2" name="User-1-orders" type="checkbox" value="1" />
<label for="User-1-orders_2">
 Quantity: 10
</label>

>>> print fs.orders.checkbox(options=session.query(Order).filter_by(id=1)).render()
<input checked="checked" id="User-1-orders_0" name="User-1-orders" type="checkbox" value="1" /><label for="User-1-orders_0">Quantity: 10</label>

>>> fs = FieldSet(bill, data={})
>>> fs.configure(include=[fs.orders.checkbox()])
>>> fs.validate()
True

>>> fs = FieldSet(bill, data={'User-1-orders': ['2', '3']})
>>> print pretty_html(fs.orders.render())
<select id="User-1-orders" multiple="multiple" name="User-1-orders" size="5">
 <option selected="selected" value="2">
  Quantity: 5
 </option>
 <option selected="selected" value="3">
  Quantity: 6
 </option>
 <option value="1">
  Quantity: 10
 </option>
</select>

>>> fs.orders.model_value
[1]
>>> fs.orders.raw_value
[<Order for user 1: 10>]

>>> fs = FieldSet(Two)
>>> print fs.foo.render()
<input id="Two--foo" name="Two--foo" type="text" value="133" />

>>> fs = FieldSet(Two)
>>> print fs.foo.dropdown([('option1', 'value1'), ('option2', 'value2')]).render()
<select id="Two--foo" name="Two--foo">
<option value="value1">option1</option>
<option value="value2">option2</option>
</select>

>>> fs = FieldSet(Order, session)
>>> print fs.render()
<div>
 <label class="field_req" for="Order--quantity">
  Quantity
 </label>
 <input id="Order--quantity" name="Order--quantity" type="text" />
</div>
<script type="text/javascript">
 //<![CDATA[
document.getElementById("Order--quantity").focus();
//]]>
</script>
<div>
 <label class="field_req" for="Order--user_id">
  User
 </label>
 <select id="Order--user_id" name="Order--user_id">
  <option value="1">
   Bill
  </option>
  <option value="2">
   John
  </option>
 </select>
</div>

# this seems particularly prone to errors; break it out in its own test
>>> fs = FieldSet(order1)
>>> fs.user.value
1

# test re-binding
>>> fs = FieldSet(Order)
>>> fs.configure(pk=True, options=[fs.quantity.hidden()])
>>> fs.rebind(order1)
>>> fs.quantity.value
10
>>> fs.session == object_session(order1)
True
>>> print fs.render()
<div>
 <label class="field_req" for="Order-1-id">
  Id
 </label>
 <input id="Order-1-id" name="Order-1-id" type="text" value="1" />
</div>
<script type="text/javascript">
 //<![CDATA[
document.getElementById("Order-1-id").focus();
//]]>
</script>
<input id="Order-1-quantity" name="Order-1-quantity" type="hidden" value="10" />
<div>
 <label class="field_req" for="Order-1-user_id">
  User
 </label>
 <select id="Order-1-user_id" name="Order-1-user_id">
  <option selected="selected" value="1">
   Bill
  </option>
  <option value="2">
   John
  </option>
 </select>
</div>

>>> fs = FieldSet(One)
>>> fs.configure(pk=True)
>>> print fs.render()
<div>
 <label class="field_req" for="One--id">
  Id
 </label>
 <input id="One--id" name="One--id" type="text" />
</div>
<script type="text/javascript">
 //<![CDATA[
document.getElementById("One--id").focus();
//]]>
</script>
>>> fs.configure(include=[])
>>> print fs.render()
<BLANKLINE>
>>> fs.configure(pk=True, focus=None)
>>> print fs.render()
<div>
 <label class="field_req" for="One--id">
  Id
 </label>
 <input id="One--id" name="One--id" type="text" />
</div>

>>> fs = FieldSet(One)
>>> fs.rebind(Two) #doctest: +ELLIPSIS
Traceback (most recent call last):
...
ValueError: ...

>>> fs = FieldSet(Two)
>>> fs.configure()
>>> fs2 = fs.bind(Two)
>>> [fs2 == field.parent for field in fs2._render_fields.itervalues()]
[True]

>>> fs = FieldSet(OTOParent, session)
>>> print fs.render()
<div>
 <label class="field_req" for="OTOParent--oto_child_id">
  Child
 </label>
 <select id="OTOParent--oto_child_id" name="OTOParent--oto_child_id">
  <option value="1">
   baz
  </option>
 </select>
</div>
<script type="text/javascript">
 //<![CDATA[
document.getElementById("OTOParent--oto_child_id").focus();
//]]>
</script>

>>> fs.rebind(parent)
>>> fs.child.raw_value
<OTOChild baz>

# validation + sync
>>> fs_2 = FieldSet(Two, session=session, data={'Two--foo': ''})
>>> fs_2.foo.value # '' is deserialized to None, so default of 133 is used
'133'
>>> fs_2.validate()
True
>>> fs_2.configure(options=[fs_2.foo.required()], focus=None)
>>> fs_2.validate()
False
>>> fs_2.errors
{AttributeField(foo): ['Please enter a value']}
>>> print fs_2.render()
<div>
 <label class="field_req" for="Two--foo">
  Foo
 </label>
 <input id="Two--foo" name="Two--foo" type="text" value="133" />
 <span class="field_error">
  Please enter a value
 </span>
</div>
>>> fs_2.rebind(data={'Two--foo': 'asdf'})
>>> fs_2.data
SimpleMultiDict([('Two--foo', u'asdf')])
>>> fs_2.validate()
False
>>> fs_2.errors
{AttributeField(foo): ['Value is not an integer']}
>>> print fs_2.render()
<div>
 <label class="field_req" for="Two--foo">
  Foo
 </label>
 <input id="Two--foo" name="Two--foo" type="text" value="asdf" />
 <span class="field_error">
  Value is not an integer
 </span>
</div>
>>> fs_2.rebind(data={'Two--foo': '2'})
>>> fs_2.data
SimpleMultiDict([('Two--foo', u'2')])
>>> fs_2.validate()
True
>>> fs_2.errors
{}
>>> fs_2.sync()
>>> fs_2.model.foo
2
>>> session.flush()
>>> print fs_2.render() #doctest: +ELLIPSIS
Traceback (most recent call last):
...
PkError: Primary key of model has changed since binding, probably due to sync()ing a new instance (from None to 1)...
>>> session.rollback()

>>> fs_1 = FieldSet(One, session=session, data={'One--id': '1'})
>>> fs_1.configure(pk=True)
>>> fs_1.validate()
True
>>> fs_1.sync()
>>> fs_1.model.id
1
>>> fs_1.rebind(data={'One--id': 'asdf'})
>>> fs_1.id.renderer.name
u'One--id'
>>> fs_1.validate()
False
>>> fs_1.errors
{AttributeField(id): ['Value is not an integer']}

# test updating _bound_pk copy
>>> one = One(id=1)
>>> fs_11 = FieldSet(one)
>>> fs_11.id.renderer.name
u'One-1-id'
>>> one.id = 2
>>> fs_11.rebind(one)
>>> fs_11.id.renderer.name
u'One-2-id'

>>> fs_u = FieldSet(User, session=session, data={})
>>> fs_u.configure(include=[fs_u.orders])
>>> fs_u.validate()
True
>>> fs_u.sync()
>>> fs_u.model.orders
[]
>>> fs_u.rebind(User, session, data={'User--orders': [str(order1.id), str(order2.id)]})
>>> fs_u.validate()
True
>>> fs_u.sync()
>>> fs_u.model.orders == [order1, order2]
True
>>> session.rollback()

>>> fs_3 = FieldSet(Three, data={'Three--foo': 'asdf', 'Three--bar': 'fdsa'})
>>> fs_3.foo.value
u'asdf'
>>> print fs_3.foo.textarea().render()
<textarea id="Three--foo" name="Three--foo">asdf</textarea>
>>> print fs_3.foo.textarea("3x4").render()
<textarea cols="3" id="Three--foo" name="Three--foo" rows="4">asdf</textarea>
>>> print fs_3.foo.textarea((3,4)).render()
<textarea cols="3" id="Three--foo" name="Three--foo" rows="4">asdf</textarea>
>>> fs_3.bar.value
u'fdsa'
>>> def custom_validator(fs):
...   if fs.foo.value != fs.bar.value:
...     fs.foo.errors.append('does not match bar')
...     raise ValidationError('foo and bar do not match')
>>> fs_3.configure(global_validator=custom_validator, focus=None)
>>> fs_3.validate()
False
>>> sorted(fs_3.errors.items())
[(None, ('foo and bar do not match',)), (AttributeField(foo), ['does not match bar'])]
>>> print fs_3.render()
<div class="fieldset_error">
 foo and bar do not match
</div>
<div>
 <label class="field_opt" for="Three--foo">
  Foo
 </label>
 <input id="Three--foo" name="Three--foo" type="text" value="asdf" />
 <span class="field_error">
  does not match bar
 </span>
</div>
<div>
 <label class="field_opt" for="Three--bar">
  Bar
 </label>
 <input id="Three--bar" name="Three--bar" type="text" value="fdsa" />
</div>

# custom renderer
>>> fs_3 = FieldSet(Three, data={'Three--foo': 'http://example.com/image.png'})
>>> fs_3.configure(include=[fs_3.foo.with_renderer(ImgRenderer)])
>>> print fs_3.foo.render()
<img src="http://example.com/image.png">

# natural PKs
>>> fs_npk = FieldSet(NaturalOrder, session)
>>> print fs_npk.render()
<div>
 <label class="field_req" for="NaturalOrder--quantity">
  Quantity
 </label>
 <input id="NaturalOrder--quantity" name="NaturalOrder--quantity" type="text" />
</div>
<script type="text/javascript">
 //<![CDATA[
document.getElementById("NaturalOrder--quantity").focus();
//]]>
</script>
<div>
 <label class="field_req" for="NaturalOrder--user_email">
  User
 </label>
 <select id="NaturalOrder--user_email" name="NaturalOrder--user_email">
  <option value="nbill@example.com">
   Natural Bill
  </option>
  <option value="njohn@example.com">
   Natural John
  </option>
 </select>
</div>
>>> fs_npk.rebind(norder2, session, data={'NaturalOrder-2-user_email': nbill.email, 'NaturalOrder-2-quantity': str(norder2.quantity)})
>>> fs_npk.user_email.renderer.name
u'NaturalOrder-2-user_email'
>>> fs_npk.sync()
>>> fs_npk.model.user_email == nbill.email
True
>>> session.rollback()

# allow attaching custom attributes to wrappers
>>> fs = FieldSet(User)
>>> fs.name.baz = 'asdf'
>>> fs2 = fs.bind(bill)
>>> fs2.name.baz
'asdf'

# equality can tell an field bound to an instance is the same as one bound to a type
>>> fs.name == fs2.name
True

# Field
>>> fs = FieldSet(One)
>>> fs.add(Field('foo'))
>>> print configure_and_render(fs, focus=None)
<div>
 <label class="field_opt" for="One--foo">
  Foo
 </label>
 <input id="One--foo" name="One--foo" type="text" />
</div>

>>> fs = FieldSet(One)
>>> fs.add(Field('foo', types.Integer, value=2))
>>> fs.foo.value
2
>>> print configure_and_render(fs, focus=None)
<div>
 <label class="field_opt" for="One--foo">
  Foo
 </label>
 <input id="One--foo" name="One--foo" type="text" value="2" />
</div>
>>> fs.rebind(One, data={'One--foo': '4'})
>>> fs.sync()
>>> fs.foo.value
4

>>> fs = FieldSet(One)
>>> fs.add(Field('foo', types.Integer, value=2).dropdown(options=[('1', 1), ('2', 2)]))
>>> print configure_and_render(fs, focus=None)
<div>
 <label class="field_opt" for="One--foo">
  Foo
 </label>
 <select id="One--foo" name="One--foo">
  <option value="1">
   1
  </option>
  <option selected="selected" value="2">
   2
  </option>
 </select>
</div>

# test Field __hash__, __eq__
>>> fs.foo == fs.foo.dropdown(options=[('1', 1), ('2', 2)])
True

>>> fs2 = FieldSet(One)
>>> fs2.add(Field('foo', types.Integer, value=2))
>>> fs2.configure(options=[fs2.foo.dropdown(options=[('1', 1), ('2', 2)])], focus=None)
>>> fs.render() == fs2.render()
True

>>> fs_1 = FieldSet(One)
>>> fs_1.add(Field('foo', types.Integer, value=[2, 3]).dropdown(options=[('1', 1), ('2', 2), ('3', 3)], multiple=True))
>>> print configure_and_render(fs_1, focus=None)
<div>
 <label class="field_opt" for="One--foo">
  Foo
 </label>
 <select id="One--foo" multiple="multiple" name="One--foo" size="5">
  <option value="1">
   1
  </option>
  <option selected="selected" value="2">
   2
  </option>
  <option selected="selected" value="3">
   3
  </option>
 </select>
</div>
>>> fs_1.rebind(One, data={'One--foo': ['1', '2']})
>>> fs_1.sync()
>>> fs_1.foo.value
[1, 2]

# test attribute names
>>> fs = FieldSet(One)
>>> fs.add(Field('foo'))
>>> fs.foo == fs['foo']
True
>>> fs.add(Field('add'))
>>> fs.add == fs['add']
False

# change default renderer 
>>> class BooleanSelectRenderer(SelectFieldRenderer):
...     def render(self, **kwargs):
...         kwargs['options'] = [('Yes', True), ('No', False)]
...         return SelectFieldRenderer.render(self, **kwargs)
>>> d = dict(FieldSet.default_renderers)
>>> d[types.Boolean] = BooleanSelectRenderer
>>> fs = FieldSet(CheckBox)
>>> fs.default_renderers = d
>>> print fs.field.render()
<select id="CheckBox--field" name="CheckBox--field">
<option value="True">Yes</option>
<option value="False">No</option>
</select>

# test setter rejection
>>> fs = FieldSet(One)
>>> fs.id = fs.id.required()
Traceback (most recent call last):
...
AttributeError: Do not set field attributes manually.  Use append() or configure() instead

# join
>>> fs = FieldSet(Order__User)
>>> fs._fields.values()
[AttributeField(orders_id), AttributeField(orders_user_id), AttributeField(orders_quantity), AttributeField(users_id), AttributeField(users_email), AttributeField(users_password), AttributeField(users_name)]
>>> fs.rebind(session.query(Order__User).filter_by(orders_id=1).one())
>>> print configure_and_render(fs, focus=None)
<div>
 <label class="field_req" for="Order__User-1_1-orders_quantity">
  Orders quantity
 </label>
 <input id="Order__User-1_1-orders_quantity" name="Order__User-1_1-orders_quantity" type="text" value="10" />
</div>
<div>
 <label class="field_req" for="Order__User-1_1-users_email">
  Users email
 </label>
 <input id="Order__User-1_1-users_email" maxlength="40" name="Order__User-1_1-users_email" type="text" value="bill@example.com" />
</div>
<div>
 <label class="field_req" for="Order__User-1_1-users_password">
  Users password
 </label>
 <input id="Order__User-1_1-users_password" maxlength="20" name="Order__User-1_1-users_password" type="text" value="1234" />
</div>
<div>
 <label class="field_opt" for="Order__User-1_1-users_name">
  Users name
 </label>
 <input id="Order__User-1_1-users_name" maxlength="30" name="Order__User-1_1-users_name" type="text" value="Bill" />
</div>
>>> fs.rebind(session.query(Order__User).filter_by(orders_id=1).one(), data={'Order__User-1_1-orders_quantity': '5', 'Order__User-1_1-users_email': bill.email, 'Order__User-1_1-users_password': '5678', 'Order__User-1_1-users_name': 'Bill'})
>>> fs.validate()
True
>>> fs.sync()
>>> session.flush()
>>> session.refresh(bill)
>>> bill.password == '5678'
True
>>> session.rollback()

>>> FieldSet.default_renderers[Point] = PointFieldRenderer
>>> fs = FieldSet(Vertex)
>>> print pretty_html(fs.start.render())
<input id="Vertex--start-x" name="Vertex--start-x" type="text" value="" />
<input id="Vertex--start-y" name="Vertex--start-y" type="text" value="" />
>>> fs.rebind(Vertex)
>>> v = fs.model
>>> v.start = Point(1,2)
>>> v.end = Point(3,4)
>>> print pretty_html(fs.start.render())
<input id="Vertex--start-x" name="Vertex--start-x" type="text" value="1" />
<input id="Vertex--start-y" name="Vertex--start-y" type="text" value="2" />
>>> fs.rebind(v)
>>> fs.rebind(data={'Vertex--start-x': '10', 'Vertex--start-y': '20', 'Vertex--end-x': '30', 'Vertex--end-y': '40'})
>>> fs.validate()
True
>>> fs.sync()
>>> session.add(v)
>>> session.flush()
>>> v.id
1
>>> session.refresh(v)
>>> v.start.x
10
>>> v.end.y
40
>>> session.rollback()

# readonly tests
>>> t = FieldSet(john)
>>> john.name = None
>>> t.configure(readonly=True)
>>> t.readonly
True
>>> print t.render()
<tbody>
 <tr>
  <td class="field_readonly">
   Email:
  </td>
  <td>
   john@example.com
  </td>
 </tr>
 <tr>
  <td class="field_readonly">
   Password:
  </td>
  <td>
   5678
  </td>
 </tr>
 <tr>
  <td class="field_readonly">
   Name:
  </td>
  <td>
  </td>
 </tr>
 <tr>
  <td class="field_readonly">
   Orders:
  </td>
  <td>
   Quantity: 5, Quantity: 6
  </td>
 </tr>
</tbody>
>>> session.rollback()
>>> session.refresh(john)

>>> fs_or = FieldSet(order1)
>>> print fs_or.user.render_readonly()
<a href="mailto:bill@example.com">Bill</a>

>>> out = FieldSet(OrderUserTag, session=session)
>>> list(sorted(out._fields))
['id', 'order_id', 'order_user', 'tag', 'user_id']
>>> print out.order_user.name
order_user
>>> out.order_user.is_raw_foreign_key
False
>>> out.order_user.is_composite_foreign_key
True
>>> list(sorted(out.render_fields))
['order_user', 'tag']
>>> print pretty_html(out.order_user.render())
<select id="OrderUserTag--order_user" name="OrderUserTag--order_user">
 <option value="(1, 1)">
  OrderUser(1, 1)
 </option>
 <option value="(1, 2)">
  OrderUser(1, 2)
 </option>
</select>
>>> out.rebind(data={'OrderUserTag--order_user': '(1, 2)', 'OrderUserTag--tag': 'asdf'})
>>> out.validate()
True
>>> out.sync()
>>> print out.model.order_user
OrderUser(1, 2)

>>> fs = FieldSet(Function)
>>> fs.configure(pk=True)
>>> fs.foo.render().startswith('<span')
True

>>> fs_r = FieldSet(Recursive)
>>> fs_r.parent_id.is_raw_foreign_key
True
>>> fs_r.rebind(data={'Recursive--foo': 'asdf'})
>>> fs_r.validate()
True

>>> fs_oo = FieldSet(OptionalOrder, session=session)
>>> fs_oo.configure(options=[fs_oo.user.with_null_as(('No user', ''))])
>>> fs_oo.user._null_option
('No user', '')
>>> print pretty_html(fs_oo.user.render())
<select id="OptionalOrder--user_id" name="OptionalOrder--user_id">
 <option selected="selected" value="">
  No user
 </option>
 <option value="1">
  Bill
 </option>
 <option value="2">
  John
 </option>
</select>

>>> fs_oo = FieldSet(OptionalOrder)
>>> fs_oo.rebind(data={'OptionalOrder--user_id': fs_oo.user_id._null_option[1], 'OptionalOrder--quantity': ''})
>>> fs_oo.validate()
True
>>> fs_oo.user_id.value is None
True

>>> fs_bad = FieldSet(One)
>>> fs_bad.configure(include=[Field('invalid')])
Traceback (most recent call last):
...
ValueError: Unrecognized Field `AttributeField(invalid)` in `include` -- did you mean to call append() first?

>>> fs_s = FieldSet(Synonym)
>>> fs_s._fields
{'foo': AttributeField(foo), 'id': AttributeField(id)}

>>> fs_prefix = FieldSet(Two, prefix="myprefix")
>>> print(fs_prefix.render())
<div>
 <label class="field_opt" for="myprefix-Two--foo">
  Foo
 </label>
 <input id="myprefix-Two--foo" name="myprefix-Two--foo" type="text" value="133" />
</div>
<script type="text/javascript">
 //<![CDATA[
document.getElementById("myprefix-Two--foo").focus();
//]]>
</script>

>>> fs_prefix.rebind(data={"myprefix-Two--foo": "42"})
>>> fs_prefix.validate()
True
>>> fs_prefix.sync()
>>> fs_prefix.model.foo
42

>>> fs_two = FieldSet(Two)
>>> fs_two.configure(options=[fs_two.foo.label('1 < 2')])
>>> print fs_two.render()
<div>
 <label class="field_opt" for="Two--foo">
  1 &lt; 2
 </label>
 <input id="Two--foo" name="Two--foo" type="text" value="133" />
</div>
<script type="text/javascript">
 //<![CDATA[
document.getElementById("Two--foo").focus();
//]]>
</script>

>>> fs_prop = FieldSet(Property)
>>> fs_prop.foo.is_readonly()
True

>>> fs_conflict = FieldSet(ConflictNames)
>>> fs_conflict.rebind(conflict_names)
>>> print fs_conflict.render() #doctest: +ELLIPSIS
<div>
...

"""

if __name__ == '__main__':
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = test_fieldset_api
# -*- coding: utf-8 -*-
from formalchemy.tests import *
from formalchemy.fields import PasswordFieldRenderer

def copy():
    """
    >>> fs = FieldSet(User)
    >>> fs1 = fs.copy(fs.id, fs.email)
    >>> fs1._render_fields.keys()
    ['id', 'email']
    >>> fs2 = fs.copy(fs.name, fs.email)
    >>> fs2._render_fields.keys()
    ['name', 'email']
    """

def append():
    """
    >>> fs = FieldSet(User)
    >>> fs.append(Field('added'))
    >>> fs._fields.keys()
    ['id', 'email', 'password', 'name', 'orders', 'added']

    >>> fs = FieldSet(User)
    >>> fs.configure()
    >>> fs.append(Field('added'))
    >>> fs._fields.keys()
    ['id', 'email', 'password', 'name', 'orders']
    >>> fs._render_fields.keys()
    ['email', 'password', 'name', 'orders', 'added']
    """

def extend():
    """
    >>> fs = FieldSet(User)
    >>> fs.extend([Field('added')])
    >>> fs._fields.keys()
    ['id', 'email', 'password', 'name', 'orders', 'added']
    >>> fs._render_fields.keys()
    []
    >>> fs.added
    AttributeField(added)

    >>> fs = FieldSet(User)
    >>> fs.configure()
    >>> fs.extend([Field('added')])
    >>> fs._fields.keys()
    ['id', 'email', 'password', 'name', 'orders']
    >>> fs._render_fields.keys()
    ['email', 'password', 'name', 'orders', 'added']
    >>> fs.added
    AttributeField(added)
    """

def insert():
    """
    >>> fs = FieldSet(User)
    >>> fs.insert(fs.password, Field('login'))
    >>> fs._fields.keys()
    ['id', 'email', 'login', 'password', 'name', 'orders']
    >>> fs._render_fields.keys()
    []
    >>> fs.login
    AttributeField(login)

    >>> fs = FieldSet(User)
    >>> fs.configure()
    >>> fs.insert(fs.password, Field('login'))
    >>> fs._fields.keys()
    ['id', 'email', 'password', 'name', 'orders']
    >>> fs._render_fields.keys()
    ['email', 'login', 'password', 'name', 'orders']
    >>> fs.login
    AttributeField(login)
    """

def test_insert_after_relation():
    """
    >>> fs = FieldSet(OTOParent)
    >>> fs.configure()
    >>> fs.insert(fs.child, Field('foo'))
    >>> fs.insert_after(fs.child, Field('bar'))
    >>> fs._render_fields.keys()
    ['foo', 'child', 'bar']
    """

def test_insert_after_alias():
    """
    >>> fs = FieldSet(Aliases)
    >>> fs.configure()
    >>> fs.insert(fs.text, Field('foo'))
    >>> fs.insert_after(fs.text, Field('bar'))
    >>> fs._render_fields.keys()
    ['foo', 'text', 'bar']
    """

def insert_after():
    """
    >>> fs = FieldSet(User)
    >>> fs.insert_after(fs.password, Field('login'))
    >>> fs._fields.keys()
    ['id', 'email', 'password', 'login', 'name', 'orders']
    >>> fs._render_fields.keys()
    []
    >>> fs.login
    AttributeField(login)

    >>> fs = FieldSet(User)
    >>> fs.configure()
    >>> fs.insert_after(fs.password, Field('login'))
    >>> fs._fields.keys()
    ['id', 'email', 'password', 'name', 'orders']
    >>> fs._render_fields.keys()
    ['email', 'password', 'login', 'name', 'orders']
    >>> fs.login
    AttributeField(login)

    >>> fs.insert_after('somethingbad', Field('login'))  #doctest: +ELLIPSIS
    Traceback (most recent call last):
    ...
    TypeError: field must be a Field. Got 'somethingbad'
    >>> fs.insert_after(fs.password, ['some', 'random', 'objects'])  #doctest: +ELLIPSIS
    Traceback (most recent call last):
    ...
    ValueError: Can only add Field objects; got AttributeField(password) instead
    """


def delete():
    """
    >>> fs = FieldSet(User)
    >>> del fs.name #doctest: +ELLIPSIS
    Traceback (most recent call last):
    ...
    RuntimeError: You try to delete a field but your form is not configured

    >>> del fs.notexist #doctest: +ELLIPSIS
    Traceback (most recent call last):
    ...
    AttributeError: field notexist does not exist

    >>> fs.configure()
    >>> del fs.name
    >>> fs._fields.keys()
    ['id', 'email', 'password', 'name', 'orders']
    >>> fs._render_fields.keys()
    ['email', 'password', 'orders']

    """

def test_delete_relation():
    """
    >>> fs = FieldSet(OTOParent)
    >>> fs.configure()
    >>> del fs.child
    """

def field_set():
    """
    >>> fs = FieldSet(User)
    >>> fs.insert(fs.password, Field('login'))
    >>> def validate(value, field):
    ...     if len(value) < 2: raise ValidationError('Need more than 2 chars')
    >>> fs.password.set(renderer=PasswordFieldRenderer, validate=validate)
    AttributeField(password)
    >>> fs.password.renderer
    <PasswordFieldRenderer for AttributeField(password)>
    >>> fs.password.validators # doctest: +ELLIPSIS
    [<function required at ...>, <function validate at ...>]

    >>> fs.password.set(instructions='Put a password here')
    AttributeField(password)
    >>> fs.password.metadata
    {'instructions': 'Put a password here'}

    >>> field = Field('password', value='passwd', renderer=PasswordFieldRenderer)
    >>> field.renderer
    <PasswordFieldRenderer for AttributeField(password)>
    >>> field.raw_value
    'passwd'

    >>> field.set(value='new_passwd')
    AttributeField(password)
    >>> field.raw_value
    'new_passwd'

    >>> field.set(required=True)
    AttributeField(password)
    >>> field.validators  #doctest: +ELLIPSIS
    [<function required at ...>]
    >>> field.set(required=False)
    AttributeField(password)
    >>> field.validators
    []

    >>> field.set(html={'this': 'that'})
    AttributeField(password)
    >>> field.html_options
    {'this': 'that'}
    >>> field.set(html={'some': 'thing'})
    AttributeField(password)
    >>> field.html_options
    {'this': 'that', 'some': 'thing'}

    >>> bob = lambda x: x
    >>> field.set(validators=[bob])
    AttributeField(password)
    >>> field.validators  #doctest: +ELLIPSIS
    [<function <lambda> at ...>]

    >>> field.set(validators=[bob])
    AttributeField(password)
    >>> field.validators  #doctest: +ELLIPSIS
    [<function <lambda> at ...>, <function <lambda> at ...>]

    >>> field.set(non_exist=True)
    Traceback (most recent call last):
    ...
    ValueError: Invalid argument non_exist

    """


########NEW FILE########
__FILENAME__ = test_fsblob
import os
import cgi
import shutil
import tempfile
from StringIO import StringIO
from nose import with_setup

from formalchemy.tests import *
from formalchemy.tests.test_binary import *
from formalchemy.ext.fsblob import FileFieldRenderer as BaseFile
from formalchemy.ext.fsblob import ImageFieldRenderer as BaseImage
from formalchemy.ext.fsblob import file_extension

TEMPDIR = tempfile.mkdtemp()

class FileFieldRenderer(BaseFile):
    storage_path = TEMPDIR

class ImageFieldRenderer(BaseImage):
    storage_path = TEMPDIR

def setup_tempdir():
    if not os.path.isdir(TEMPDIR):
        os.makedirs(TEMPDIR)

def teardown_tempdir():
    if os.path.isdir(TEMPDIR):
        shutil.rmtree(TEMPDIR)

@with_setup(setup_tempdir, teardown_tempdir)
def test_file_storage():
    fs = FieldSet(Binaries)
    record = fs.model
    fs.configure(include=[fs.file.with_renderer(FileFieldRenderer)])

    assert 'test.js' not in fs.render()

    data = get_fields(TEST_DATA)
    fs.rebind(data=data)
    assert fs.validate() is True
    assert fs.file.value.endswith('/test.js')
    fs.sync()
    filepath = os.path.join(TEMPDIR, fs.file.value)
    assert os.path.isfile(filepath), filepath

    view = fs.file.render_readonly()
    value = '<a href="/%s">test.js (1 KB)</a>' % fs.file.value
    assert value in view, '%s != %s' % (value, view)

    assert value in fs.file.render(), fs.render()

@with_setup(setup_tempdir, teardown_tempdir)
def test_image_storage():
    fs = FieldSet(Binaries)
    record = fs.model
    fs.configure(include=[fs.file.with_renderer(ImageFieldRenderer)])

    assert 'test.js' not in fs.render()

    data = get_fields(TEST_DATA)
    fs.rebind(data=data)
    assert fs.validate() is True
    fs.sync()
    assert fs.file.value.endswith('/test.js')
    filepath = os.path.join(TEMPDIR, fs.file.value)
    assert os.path.isfile(filepath), filepath

    view = fs.file.render_readonly()
    v = fs.file.value
    value = '<a href="/%s"><img alt="test.js (1 KB)" src="/%s" /></a>' % (v, v)
    assert value in view, '%s != %s' % (value, view)

    assert value in fs.file.render(), fs.render()

@with_setup(setup_tempdir, teardown_tempdir)
def test_file_validation():
    fs = FieldSet(Binaries)
    record = fs.model
    fs.configure(include=[
        fs.file.with_renderer(
                    FileFieldRenderer
                ).validate(file_extension(['js']))])
    data = get_fields(TEST_DATA)
    fs.rebind(data=data)
    assert fs.validate() is True

    fs.configure(include=[
        fs.file.with_renderer(
                    FileFieldRenderer
                ).validate(file_extension(['txt']))])
    data = get_fields(TEST_DATA)
    fs.rebind(data=data)
    assert fs.validate() is False


########NEW FILE########
__FILENAME__ = test_html5
# -*- coding: utf-8 -*-
from formalchemy.tests import *
from formalchemy.fatypes import *
from formalchemy import tests
from webtest import SeleniumApp, selenium

def test_render():
    """
    >>> html5_test_fieldset = FieldSet(Three)
    >>> print html5_test_fieldset.foo.url().render()
    <input id="Three--foo" name="Three--foo" type="url" />

    >>> print html5_test_fieldset.foo.email().render()
    <input id="Three--foo" name="Three--foo" type="email" />

    >>> print html5_test_fieldset.foo.range(min_=2, max_=10, step=5).render()
    <input id="Three--foo" max="10" min="2" name="Three--foo" step="5" type="range" />

    >>> print html5_test_fieldset.foo.number(min_=2, max_=10, step=5).render()
    <input id="Three--foo" max="10" min="2" name="Three--foo" step="5" type="number" />

    >>> print html5_test_fieldset.foo.time().render()
    <input id="Three--foo" name="Three--foo" type="time" />

    >>> print html5_test_fieldset.foo.date().render()
    <input id="Three--foo" name="Three--foo" type="date" />

    >>> print html5_test_fieldset.foo.datetime().render()
    <input id="Three--foo" name="Three--foo" type="datetime" />

    >>> print html5_test_fieldset.foo.datetime_local().render()
    <input id="Three--foo" name="Three--foo" type="date" />

    >>> print html5_test_fieldset.foo.week().render()
    <input id="Three--foo" name="Three--foo" type="week" />

    >>> print html5_test_fieldset.foo.month().render()
    <input id="Three--foo" name="Three--foo" type="month" />

    >>> print html5_test_fieldset.foo.color().render()
    <input id="Three--foo" name="Three--foo" type="color" />
    """

class HTML5(Base):
    __tablename__ = 'html5'
    id = Column('id', Integer, primary_key=True)
    date = Column(HTML5Date, nullable=True)
    time = Column(HTML5Time, nullable=True)
    datetime = Column(HTML5DateTime, nullable=True)
    color = Column(HTML5Color, nullable=True)

@selenium
class TestDateTime(unittest.TestCase):

    def setUp(self):
        self.app = SeleniumApp(application(HTML5))

    def test_render(self):
        resp = self.app.get('/')
        form = resp.form
        form['HTML5--date'] = '2011-01-1'
        form['HTML5--time'] = '12:10'
        form['HTML5--datetime'] = '2011-01-1T10:11Z'
        form['HTML5--color'] = '#fff'
        resp = form.submit()
        resp.mustcontain('OK')
        resp.mustcontain('2011-01-01 10:11:00')

    def tearDown(self):
        self.app.close()


########NEW FILE########
__FILENAME__ = test_json
# -*- coding: utf-8 -*-
from formalchemy.tests import *
from formalchemy.fields import PasswordFieldRenderer
try:
    import json
except ImportError:
    import simplejson as json

def to_dict():
    """
    >>> fs = FieldSet(User, session=session)
    >>> _ = fs.password.set(renderer=PasswordFieldRenderer)

    >>> fs.to_dict()
    {u'User--id': None, u'User--name': None, u'User--email': None, u'User--orders': []}

    >>> fs = FieldSet(bill)
    >>> _ = fs.password.set(renderer=PasswordFieldRenderer)

    >>> fs.to_dict()
    {u'User-1-email': u'bill@example.com', u'User-1-id': 1, u'User-1-orders': [1], u'User-1-name': u'Bill'}

    >>> fs.to_dict(with_prefix=False)
    {'orders': [1], 'id': 1, 'name': u'Bill', 'email': u'bill@example.com'}

    >>> print json.dumps(fs.to_dict(with_prefix=False, as_string=True))
    {"orders": "Quantity: 10", "password": "******", "id": "1", "name": "Bill", "email": "bill@example.com"}
    """

def bind_without_prefix():
    """
    >>> data = {u'password': u'1', u'id': 1, u'orders': [1], u'email': u'bill@example.com', u'name': u'Bill'}

    >>> fs = FieldSet(User)
    >>> fs = fs.bind(data=data, session=session, with_prefix=False)
    >>> fs.validate()
    True

    >>> fs.rebind(bill, data=data, with_prefix=False)
    >>> fs.validate()
    True
    >>> fs.password.value
    u'1'

    >>> data = {u'password': u'2', u'id': 1, u'orders': [1], u'email': u'bill@example.com', u'name': u'Bill'}
    >>> fs = fs.bind(bill, data=data, with_prefix=False)
    >>> fs.validate()
    True
    >>> fs.password.value
    u'2'

    """

########NEW FILE########
__FILENAME__ = test_manual
# -*- coding: utf-8 -*-
from formalchemy.tests import FieldSet, Field, EscapingReadonlyRenderer, types, configure_and_render, pretty_html

class Manual(object):
    a = Field()
    b = Field(type=types.Integer).dropdown([('one', 1), ('two', 2)], multiple=True)
    d = Field().textarea((80, 10))

class ReportByUserForm(object):
   user_id = Field(type=types.Integer)
   from_date = Field(type=types.Date).required()
   to_date = Field(type=types.Date).required()


def test_manual(self):
    """
    >>> fs = FieldSet(Manual)
    >>> print configure_and_render(fs, focus=None)
    <div>
     <label class="field_opt" for="Manual--a">
      A
     </label>
     <input id="Manual--a" name="Manual--a" type="text" />
    </div>
    <div>
     <label class="field_opt" for="Manual--b">
      B
     </label>
     <select id="Manual--b" multiple="multiple" name="Manual--b" size="5">
      <option value="1">
       one
      </option>
      <option value="2">
       two
      </option>
     </select>
    </div>
    <div>
     <label class="field_opt" for="Manual--d">
      D
     </label>
     <textarea cols="80" id="Manual--d" name="Manual--d" rows="10">
     </textarea>
    </div>
    >>> fs.rebind(data={'Manual--a': 'asdf'})
    >>> print pretty_html(fs.a.render())
    <input id="Manual--a" name="Manual--a" type="text" value="asdf" />

    >>> t = FieldSet(Manual)
    >>> t.configure(include=[t.a, t.b], readonly=True)
    >>> t.model.b = [1, 2]
    >>> print t.render()
    <tbody>
     <tr>
      <td class="field_readonly">
       A:
      </td>
      <td>
      </td>
     </tr>
     <tr>
      <td class="field_readonly">
       B:
      </td>
      <td>
       one, two
      </td>
     </tr>
    </tbody>
    >>> t.model.a = 'test'
    >>> print t.a.render_readonly()
    test
    >>> t.configure(readonly=True, options=[t.a.with_renderer(EscapingReadonlyRenderer)])
    >>> t.model.a = '<test>'
    >>> print t.a.render_readonly()
    &lt;test&gt;

    """

def test_manual2():
    """
    >>> fs = FieldSet(ReportByUserForm)
    >>> print fs.render() #doctest: +ELLIPSIS
    <div>
     <label class="field_req" for="ReportByUserForm--from_date">
      From date
     </label>
    ...
    <div>
     <label class="field_opt" for="ReportByUserForm--user_id">
      User id
     </label>
     <input id="ReportByUserForm--user_id" name="ReportByUserForm--user_id" type="text" />
    </div>
    """

########NEW FILE########
__FILENAME__ = test_misc
# -*- coding: utf-8 -*-
import unittest
from formalchemy.tests import *
from formalchemy.fields import AbstractField, FieldRenderer
from formalchemy.fields import _htmlify, deserialize_once

class TestAbstractField(unittest.TestCase):

    def setUp(self):
        self.fs = FieldSet(User)
        self.f = AbstractField(self.fs, name="field", type=types.String)
        self.f.set(renderer=FieldRenderer)
        self.fs.append(self.f)

    def test_not_implemented(self):
        f = self.f
        self.assertRaises(NotImplementedError, lambda: f.model_value)
        self.assertRaises(NotImplementedError, lambda: f.raw_value)
        self.assertRaises(NotImplementedError, f.render)

    def test_errors(self):
        f = self.f
        self.assertEqual(f.errors, [])

class TestUtils(unittest.TestCase):

    def test_htmlify(self):
        class H(object):
            __html__ = ''
            def __repr__(self): return '-'
        self.assertEqual(_htmlify(H()), '-')

        class H(object):
            def __html__(self): return 'html'
            def __repr__(self): return '-'
        self.assertEqual(_htmlify(H()), 'html')

    def test_deserialize_once(self):
        class H(object):
            value = 'foo'
            @deserialize_once
            def deserialize(self):
                return self.value
        h = H()
        self.assertEqual(h.deserialize(), 'foo')
        h.value = 'bar'
        self.assertEqual(h.deserialize(), 'foo')

########NEW FILE########
__FILENAME__ = test_multiple_keys
# -*- coding: utf-8 -*-
from formalchemy.tests import *

def test_renderer_names():
    """
    Check that the input name take care of multiple primary keys::

        >>> fs = FieldSet(primary1)
        >>> print fs.field.render()
        <input id="PrimaryKeys-1_22-field" maxlength="10" name="PrimaryKeys-1_22-field" type="text" value="value1" />

        >>> fs = FieldSet(primary2)
        >>> print fs.field.render()
        <input id="PrimaryKeys-1_33-field" maxlength="10" name="PrimaryKeys-1_33-field" type="text" value="value2" />

    Check form rendering with keys::

        >>> fs = FieldSet(primary2)
        >>> fs.configure(pk=True)
        >>> print fs.render()
        <div>
         <label class="field_req" for="PrimaryKeys-1_33-id">
          Id
         </label>
         <input id="PrimaryKeys-1_33-id" name="PrimaryKeys-1_33-id" type="text" value="1" />
        </div>
        <script type="text/javascript">
         //<![CDATA[
        document.getElementById("PrimaryKeys-1_33-id").focus();
        //]]>
        </script>
        <div>
         <label class="field_req" for="PrimaryKeys-1_33-id2">
          Id2
         </label>
         <input id="PrimaryKeys-1_33-id2" maxlength="10" name="PrimaryKeys-1_33-id2" type="text" value="33" />
        </div>
        <div>
         <label class="field_req" for="PrimaryKeys-1_33-field">
          Field
         </label>
         <input id="PrimaryKeys-1_33-field" maxlength="10" name="PrimaryKeys-1_33-field" type="text" value="value2" />
        </div>
    """

def test_foreign_keys():
    """
    Assume that we can have more than one ForeignKey as primary key::

        >>> fs = FieldSet(orderuser2)
        >>> fs.configure(pk=True)

        >>> print pretty_html(fs.user.render())
        <select id="OrderUser-1_2-user_id" name="OrderUser-1_2-user_id">
         <option selected="selected" value="1">
          Bill
         </option>
         <option value="2">
          John
         </option>
        </select>

        >>> print pretty_html(fs.order.render())
        <select id="OrderUser-1_2-order_id" name="OrderUser-1_2-order_id">
         <option value="1">
          Quantity: 10
         </option>
         <option selected="selected" value="2">
          Quantity: 5
         </option>
         <option value="3">
          Quantity: 6
         </option>
        </select>
    """


def test_deserialize():
    """
    Assume that we can deserialize a value
    """
    fs = FieldSet(primary1, data={'PrimaryKeys-1_22-field':'new_value'})
    assert fs.validate() is True
    assert fs.field.value == 'new_value'
    fs.sync()
    session.rollback()

def test_deserialize_new_record():
    """
    Assume that we can deserialize a value
    """
    fs = FieldSet(PrimaryKeys(), data={'PrimaryKeys-_-id':'8',
                                       'PrimaryKeys-_-id2':'9'})
    fs.configure(include=[fs.id, fs.id2])
    assert fs.validate() is True
    fs.sync()
    assert fs.model.id == 8, fs.model.id
    assert fs.model.id2 == '9', fs.model.id2
    session.rollback()



########NEW FILE########
__FILENAME__ = test_options
# -*- coding: utf-8 -*-
from formalchemy.tests import *

def test_dropdown():
    """
    >>> fs = FieldSet(bill)
    >>> print pretty_html(fs.orders.render())
    <select id="User-1-orders" multiple="multiple" name="User-1-orders" size="5">
     <option value="2">
      Quantity: 5
     </option>
     <option value="3">
      Quantity: 6
     </option>
     <option selected="selected" value="1">
      Quantity: 10
     </option>
    </select>
    """

def test_lazy_filtered_dropdown():
    """
    >>> fs = FieldSet(bill)
    >>> def available_orders(fs_):
    ...     return fs_.session.query(Order).filter_by(quantity=10)
    >>> fs.configure(include=[fs.orders.dropdown(options=available_orders)])
    >>> print pretty_html(fs.orders.render())
    <select id="User-1-orders" multiple="multiple" name="User-1-orders" size="5">
     <option selected="selected" value="1">
      Quantity: 10
     </option>
    </select>
    """

def test_lazy_record():
    """
    >>> fs = FieldSet(bill)
    >>> r = engine.execute('select quantity, user_id from orders').fetchall()
    >>> r = engine.execute("select 'Swedish' as name, 'sv_SE' as iso_code union all select 'English', 'en_US'").fetchall()
    >>> fs.configure(include=[fs.orders.dropdown(options=r)])
    >>> print pretty_html(fs.orders.render())
    <select id="User-1-orders" multiple="multiple" name="User-1-orders" size="5">
     <option value="sv_SE">
      Swedish
     </option>
     <option value="en_US">
      English
     </option>
    </select>
    """

def test_manual_options():
    """
    >>> fs = FieldSet(bill)
    >>> fs.append(Field(name="cb").checkbox(options=[('one', 1), ('two', 2)])) 
    >>> print fs.render() #doctest: +ELLIPSIS
    <div>...
     <label class="field_opt" for="User-1-cb">
      Cb
     </label>
     <input id="User-1-cb_0" name="User-1-cb" type="checkbox" value="1" />
     <label for="User-1-cb_0">
      one
     </label>
     <br />
     <input id="User-1-cb_1" name="User-1-cb" type="checkbox" value="2" />
     <label for="User-1-cb_1">
      two
     </label>
    </div>
    """

########NEW FILE########
__FILENAME__ = test_readonly
# -*- coding: utf-8 -*-
from formalchemy.tests import *


def test_readonly_mode():
    """
    Assume that the field value is render in readonly mode::

        >>> fs = FieldSet(Two)
        >>> fs.configure(options=[fs.foo.readonly()])
        >>> print fs.render()
        <div>
         <label class="field_opt" for="Two--foo">
          Foo
         </label>
         133
        </div>
    """

def test_focus_with_readonly_mode():
    """
    Assume that the field value is render in readonly mode and that the focus
    is set to the correct field::

        >>> fs = FieldSet(Three)
        >>> fs.configure(options=[fs.foo.readonly()])
        >>> print fs.render()
        <div>
         <label class="field_opt" for="Three--foo">
          Foo
         </label>
        </div>
        <div>
         <label class="field_opt" for="Three--bar">
          Bar
         </label>
         <input id="Three--bar" name="Three--bar" type="text" />
        </div>
        <script type="text/javascript">
         //<![CDATA[
        document.getElementById("Three--bar").focus();
        //]]>
        </script>

    """

def test_ignore_request_in_readonly():
    fs = FieldSet(bill)

    value = bill.name

    assert fs.name.value == value, '%s != %s' % (fs.name.value, value)

    fs.configure(options=[fs.name.readonly()])

    assert value in fs.render(), fs.render()

    data = {'User-1-password':bill.password,
            'User-1-email': bill.email,
            'User-1-name': 'new name',
            'User-1-orders': [o.id for o in bill.orders]}

    fs.rebind(bill, data=data)
    fs.configure(options=[fs.name.readonly()])

    assert fs.name.value == value, '%s != %s' % (fs.name.value, value)

    assert fs.name.is_readonly()

    fs.sync()

    assert bill.name == value, '%s != %s' % (bill.name, value)

    bill.name = value




########NEW FILE########
__FILENAME__ = test_request
# -*- coding: utf-8 -*-
from formalchemy.tests import *
from webob import Request

def test_get():
    """
    >>> fs = FieldSet(User)
    >>> request = Request.blank('/')
    >>> fs = fs.bind(User, request=request)
    >>> fs.id.renderer.request is request
    True
    """

def test_post():
    """
    >>> fs = FieldSet(User)
    >>> request = Request.blank('/')
    >>> request.method = 'POST'
    >>> request.POST['User--id'] = '1'
    >>> request.POST['User--name'] = 'bill'
    >>> request.POST['User--email'] = 'a@a.com'
    >>> request.POST['User--password'] = 'xx'
    >>> fs = fs.bind(request=request)
    >>> fs.id.renderer.request is request
    True
    >>> fs.validate()
    True
    """

def test_post_on_fieldset():
    """
    >>> request = Request.blank('/')
    >>> request.method = 'POST'
    >>> request.POST['User--id'] = '1'
    >>> request.POST['User--name'] = 'bill'
    >>> request.POST['User--email'] = 'a@a.com'
    >>> request.POST['User--password'] = 'xx'
    >>> fs = FieldSet(User, request=request)
    >>> fs.id.renderer.request is request
    True
    >>> fs.validate()
    True
    """
    
def test_post_on_grid():
    """
    >>> request = Request.blank('/')
    >>> request.method = 'POST'
    >>> request.POST['User-1-id'] = '1'
    >>> request.POST['User-1-name'] = 'bill'
    >>> request.POST['User-1-email'] = 'a@a.com'
    >>> request.POST['User-1-password'] = 'xx'
    >>> g = Grid(User, [bill], request=request)
    >>> g.id.renderer.request is request
    True
    >>> g.validate()
    True
    >>> print g.render()  #doctest: +ELLIPSIS
    <thead>...<input id="User-1-password" maxlength="20" name="User-1-password" type="text" value="xx" />...</tbody>
    """
    


########NEW FILE########
__FILENAME__ = test_tables
from formalchemy.tests import *
def test_rebind_and_render(self):
    """Explicitly test rebind + render:

    >>> g = Grid(User, session=session)
    >>> g.rebind([bill, john])
    >>> print pretty_html(g.render())
    <thead>
     <tr>
      <th>
       Email
      </th>
      <th>
       Password
      </th>
      <th>
       Name
      </th>
      <th>
       Orders
      </th>
     </tr>
    </thead>
    <tbody>
     <tr class="even">
      <td>
       <input id="User-1-email" maxlength="40" name="User-1-email" type="text" value="bill@example.com" />
      </td>
      <td>
       <input id="User-1-password" maxlength="20" name="User-1-password" type="text" value="1234" />
      </td>
      <td>
       <input id="User-1-name" maxlength="30" name="User-1-name" type="text" value="Bill" />
      </td>
      <td>
       <select id="User-1-orders" multiple="multiple" name="User-1-orders" size="5">
        <option value="2">
         Quantity: 5
        </option>
        <option value="3">
         Quantity: 6
        </option>
        <option selected="selected" value="1">
         Quantity: 10
        </option>
       </select>
      </td>
     </tr>
     <tr class="odd">
      <td>
       <input id="User-2-email" maxlength="40" name="User-2-email" type="text" value="john@example.com" />
      </td>
      <td>
       <input id="User-2-password" maxlength="20" name="User-2-password" type="text" value="5678" />
      </td>
      <td>
       <input id="User-2-name" maxlength="30" name="User-2-name" type="text" value="John" />
      </td>
      <td>
       <select id="User-2-orders" multiple="multiple" name="User-2-orders" size="5">
        <option selected="selected" value="2">
         Quantity: 5
        </option>
        <option selected="selected" value="3">
         Quantity: 6
        </option>
        <option value="1">
         Quantity: 10
        </option>
       </select>
      </td>
     </tr>
    </tbody>
    """

def test_extra_field():
    """
    Test rendering extra field:
    >>> g = Grid(User, session=session)
    >>> g.add(Field('edit', types.String, 'fake edit link'))
    >>> g._set_active(john)
    >>> print g.edit.render()
    <input id="User-2-edit" name="User-2-edit" type="text" value="fake edit link" />

    And extra field w/ callable value:
    >>> g = Grid(User, session=session)
    >>> g.add(Field('edit', types.String, lambda o: 'fake edit link for %s' % o.id))
    >>> g._set_active(john)
    >>> print g.edit.render()
    <input id="User-2-edit" name="User-2-edit" type="text" value="fake edit link for 2" />

    Text syncing:
    >>> g = Grid(User, [john, bill], session=session)
    >>> g.rebind(data={'User-1-email': '', 'User-1-password': '1234_', 'User-1-name': 'Bill_', 'User-1-orders': '1', 'User-2-email': 'john_@example.com', 'User-2-password': '5678_', 'User-2-name': 'John_', 'User-2-orders': ['2', '3'], })
    >>> g.validate()
    False
    >>> g.errors[bill]
    {AttributeField(email): ['Please enter a value']}
    >>> g.errors[john]
    {}
    >>> g.sync_one(john)
    >>> session.flush()
    >>> session.refresh(john)
    >>> john.email == 'john_@example.com'
    True
    >>> session.rollback()

    Test preventing user from binding to the wrong kind of object:
    >>> g = g.bind([john])
    >>> g.rows == [john]
    True
    >>> g.rebind(User)
    Traceback (most recent call last):
    ...
    Exception: instances must be an iterable, not <class 'formalchemy.tests.User'>
    >>> g = g.bind(User)
    Traceback (most recent call last):
    ...
    Exception: instances must be an iterable, not <class 'formalchemy.tests.User'>

    Simulate creating a grid in a different thread than it's used in:
    >>> _Session = sessionmaker(bind=engine)
    >>> _old_session = _Session()
    >>> assert _old_session != object_session(john)
    >>> g = Grid(User, session=_old_session)
    >>> g2 = g.bind([john])
    >>> _ = g2.render()
    """

def test_rebind_render():
    """
    Explicitly test rebind + render:
    >>> g = Grid(User, session=session, prefix="myprefix")
    >>> g.rebind([bill, john])
    >>> print pretty_html(g.render())
    <thead>
     <tr>
      <th>
       Email
      </th>
      <th>
       Password
      </th>
      <th>
       Name
      </th>
      <th>
       Orders
      </th>
     </tr>
    </thead>
    <tbody>
     <tr class="even">
      <td>
       <input id="myprefix-User-1-email" maxlength="40" name="myprefix-User-1-email" type="text" value="bill@example.com" />
      </td>
      <td>
       <input id="myprefix-User-1-password" maxlength="20" name="myprefix-User-1-password" type="text" value="1234" />
      </td>
      <td>
       <input id="myprefix-User-1-name" maxlength="30" name="myprefix-User-1-name" type="text" value="Bill" />
      </td>
      <td>
       <select id="myprefix-User-1-orders" multiple="multiple" name="myprefix-User-1-orders" size="5">
        <option value="2">
         Quantity: 5
        </option>
        <option value="3">
         Quantity: 6
        </option>
        <option selected="selected" value="1">
         Quantity: 10
        </option>
       </select>
      </td>
     </tr>
     <tr class="odd">
      <td>
       <input id="myprefix-User-2-email" maxlength="40" name="myprefix-User-2-email" type="text" value="john@example.com" />
      </td>
      <td>
       <input id="myprefix-User-2-password" maxlength="20" name="myprefix-User-2-password" type="text" value="5678" />
      </td>
      <td>
       <input id="myprefix-User-2-name" maxlength="30" name="myprefix-User-2-name" type="text" value="John" />
      </td>
      <td>
       <select id="myprefix-User-2-orders" multiple="multiple" name="myprefix-User-2-orders" size="5">
        <option selected="selected" value="2">
         Quantity: 5
        </option>
        <option selected="selected" value="3">
         Quantity: 6
        </option>
        <option value="1">
         Quantity: 10
        </option>
       </select>
      </td>
     </tr>
    </tbody>
    >>> g.rebind(data={'myprefix-User-1-email': 'updatebill_@example.com', 'myprefix-User-1-password': '1234_', 'myprefix-User-1-name': 'Bill_', 'myprefix-User-1-orders': '1', 'myprefix-User-2-email': 'john_@example.com', 'myprefix-User-2-password': '5678_', 'myprefix-User-2-name': 'John_', 'myprefix-User-2-orders': ['2', '3'], })
    >>> g.validate()
    True
    >>> g.sync()
    >>> bill.email
    u'updatebill_@example.com'
    """

if __name__ == '__main__':
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = test_unicode
# -*- coding: utf-8 -*-
from formalchemy.tests import *
from formalchemy.multidict import UnicodeMultiDict
from formalchemy.multidict import MultiDict

def test_unicode():
    """
    >>> jose = User(email='jose@example.com',
    ...             password='6565',
    ...             name=u'Jos\xe9')
    >>> order4 = Order(user=jose, quantity=4)
    >>> session.add(jose)
    >>> session.add(order4)
    >>> session.flush()
    >>> FieldSet.default_renderers = original_renderers.copy()
    >>> fs = FieldSet(jose)
    >>> print fs.render() #doctest: +ELLIPSIS
    <div>
    ...<input id="User-3-name" maxlength="30" name="User-3-name" type="text" value="José" />...

    >>> fs.readonly = True
    >>> print fs.render() #doctest: +ELLIPSIS
    <tbody>...José...

    >>> fs = FieldSet(order4)
    >>> print fs.render() #doctest: +ELLIPSIS
    <div>
    ...José...

    >>> fs.readonly = True
    >>> print fs.render() #doctest: +ELLIPSIS
    <tbody>...José...

    >>> session.rollback()
    """

def test_unicode_data(self):
    """
    >>> fs = FieldSet(User, session=session)
    >>> data = UnicodeMultiDict(MultiDict({'User--name': 'José', 'User--email': 'j@jose.com', 'User--password': 'pwd'}), encoding='utf-8')
    >>> data.encoding
    'utf-8'
    >>> fs.rebind(data=data)
    >>> fs.data is data
    True
    >>> print(fs.render()) # doctest: +ELLIPSIS
    <div>...<input id="User--name" maxlength="30" name="User--name" type="text" value="José" />...</div>

    >>> data = UnicodeMultiDict(MultiDict({'name': 'José', 'email': 'j@jose.com', 'password': 'pwd'}), encoding='utf-8')
    >>> fs.rebind(data=data, with_prefix=False)
    >>> print(fs.render()) # doctest: +ELLIPSIS
    <div>...<input id="User--name" maxlength="30" name="User--name" type="text" value="José" />...</div>

    >>> fs.rebind(data={'User--name': 'José', 'User--email': 'j@jose.com', 'User--password': 'pwd'})
    >>> isinstance(fs.data, UnicodeMultiDict)
    True
    >>> print(fs.render()) # doctest: +ELLIPSIS
    <div>...<input id="User--name" maxlength="30" name="User--name" type="text" value="José" />...</div>
    """

########NEW FILE########
__FILENAME__ = test_validate
# -*- coding: utf-8 -*-
from formalchemy.tests import *

def validate_empty():
    """
    >>> fs = FieldSet(bill)
    >>> fs.validate()
    Traceback (most recent call last):
    ...
    ValidationError: Cannot validate without binding data
    >>> fs.render() #doctest: +ELLIPSIS
    '<div>...</div>'
    """

def validate_no_field_in_data():
    """
    >>> fs = FieldSet(bill)
    >>> fs.rebind(data={})
    >>> fs.validate()
    False
    >>> fs.render() #doctest: +ELLIPSIS
    '<div>...</div>'
    """

########NEW FILE########
__FILENAME__ = test_validators
# -*- coding: utf-8 -*-
from formalchemy.tests import *
from formalchemy import validators

def validator1(value, field):
    if not value:
        raise ValidationError('Must have a value')

@validators.accepts_none
def validator2(value, field):
    if not value:
        raise ValidationError('Must have a value')


def accepts_none():
    """
    >>> fs = FieldSet(bill)
    >>> fs.configure(include=[fs.name.validate(validator1)])
    >>> fs = fs.bind(data={'User-1-name':''})
    >>> fs.validate()
    True

    >>> fs = FieldSet(bill)
    >>> fs.configure(include=[fs.name.validate(validator2)])
    >>> fs = fs.bind(data={'User-1-name':''})
    >>> fs.validate()
    False
    """


########NEW FILE########
__FILENAME__ = validators
# Copyright (C) 2007 Alexandre Conrad, alexandre (dot) conrad (at) gmail (dot) com
#
# This module is part of FormAlchemy and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

# todo 2.0 pass field and value (so exception can refer to field name, for instance)
from exceptions import ValidationError
from i18n import _

if 'any' not in locals():
    # pre-2.5 support
    def any(seq):
        """
        >>> any(xrange(10))
        True
        >>> any([0, 0, 0])
        False
        """
        for o in seq:
            if o:
                return True
        return False

def accepts_none(func):
    """validator decorator to validate None value"""
    func.accepts_none = True
    return func

def required(value, field=None):
    """Successful if value is neither None nor the empty string (yes, including empty lists)"""
    if value is None or value == '':
        msg = isinstance(value, list) and _('Please select a value') or _('Please enter a value')
        raise ValidationError(msg)
required = accepts_none(required)

# other validators will not be called for empty values

def integer(value, field=None):
    """Successful if value is an int"""
    # the validator contract says you don't have to worry about "value is None",
    # but this is called from deserialize as well as validation
    if isinstance(value, int):
        return value
    if value is None or not value.strip():
        return None
    try:
        return int(value)
    except:
        raise ValidationError(_('Value is not an integer'))

def float_(value, field=None):
    """Successful if value is a float"""
    # the validator contract says you don't have to worry about "value is None",
    # but this is called from deserialize as well as validation
    if value is None or not value.strip():
        return None
    try:
        return float(value)
    except:
        raise ValidationError(_('Value is not a number'))

from decimal import Decimal
def decimal_(value, field=None):
    """Successful if value can represent a decimal"""
    # the validator contract says you don't have to worry about "value is None",
    # but this is called from deserialize as well as validation
    if value is None or not value.strip():
        return None
    try:
        return Decimal(value)
    except:
        raise ValidationError(_('Value is not a number'))

def currency(value, field=None):
    """Successful if value looks like a currency amount (has exactly two digits after a decimal point)"""
    if '%.2f' % float_(value) != value:
        raise ValidationError('Please specify full currency value, including cents (e.g., 12.34)')

def email(value, field=None):
    """
    Successful if value is a valid RFC 822 email address.
    Ignores the more subtle intricacies of what is legal inside a quoted region,
    and thus may accept some
    technically invalid addresses, but will never reject a valid address
    (which is a much worse problem).
    """
    if not value.strip():
        return None

    reserved = r'()<>@,;:\"[]'

    try:
        recipient, domain = value.split('@', 1)
    except ValueError:
        raise ValidationError(_('Missing @ sign'))

    if any([ord(ch) < 32 for ch in value]):
        raise ValidationError(_('Control characters present'))
    if any([ord(ch) > 127 for ch in value]):
        raise ValidationError(_('Non-ASCII characters present'))

    # validate recipient
    if not recipient:
        raise ValidationError(_('Recipient must be non-empty'))
    if recipient.endswith('.'):
        raise ValidationError(_("Recipient must not end with '.'"))

    # quoted regions, aka the reason any regexp-based validator is wrong
    i = 0
    while i < len(recipient):
        if recipient[i] == '"' and (i == 0 or recipient[i - 1] == '.' or recipient[i - 1] == '"'):
            # begin quoted region -- reserved characters are allowed here.
            # (this implementation allows a few addresses not strictly allowed by rfc 822 --
            # for instance, a quoted region that ends with '\' appears to be illegal.)
            i += 1
            while i < len(recipient):
                if recipient[i] == '"':
                    break # end of quoted region
                i += 1
            else:
                raise ValidationError(_("Unterminated quoted section in recipient"))
            i += 1
            if i < len(recipient) and recipient[i] != '.':
                raise ValidationError(_("Quoted section must be followed by '@' or '.'"))
            continue
        if recipient[i] in reserved:
            raise ValidationError(_("Reserved character present in recipient"))
        i += 1

    # validate domain
    if not domain:
        raise ValidationError(_('Domain must be non-empty'))
    if domain.endswith('.'):
        raise ValidationError(_("Domain must not end with '.'"))
    if '..' in domain:
        raise ValidationError(_("Domain must not contain '..'"))
    if any([ch in reserved for ch in domain]):
        raise ValidationError(_("Reserved character present in domain"))


# parameterized validators return the validation function
def length(min=0, max=None):
    """Returns a validator that is successful if the input's length is between min and max."""
    min_ = min
    max_ = max
    def f(value, field=None):
        if len(value) < min_:
            raise ValidationError(_('Value must be at least %(min)d characters long') % {'min': min_})
        if max_ is not None and len(value) > max_:
            raise ValidationError(_('Value must be no more than %(max)d characters long') % {'max': max_})
    return f

def maxlength(max):
    """Returns a validator that is successful if the input's length is at most the given one."""
    if max <= 0:
        raise ValueError('Invalid maximum length')
    return length(max=max)

def minlength(min):
    """Returns a validator that is successful if the input's length is at least the given one."""
    if min <= 0:
        raise ValueError('Invalid minimum length')
    return length(min=min)

def regex(exp, errormsg=_('Invalid input')):
    """
    Returns a validator that is successful if the input matches (that is,
    fulfils the semantics of re.match) the given expression.
    Expressions may be either a string or a Pattern object of the sort returned by
    re.compile.
    """
    import re
    if type(exp) != type(re.compile('')):
        exp = re.compile(exp)
    def f(value, field=None):
        if not exp.match(value):
            raise ValidationError(errormsg)
    return f

# possible others:
# oneof raises if input is not one of [or a subset of for multivalues] the given list of possibilities
# url(check_exists=False)
# address parts
# cidr
# creditcard number/securitycode (/expires?)
# whole-form validators
#   fieldsmatch
#   requiredipresent/missing


########NEW FILE########
__FILENAME__ = performance_test
#!bin/python
import webob
import formalchemy
import sqlalchemy as sa
from sqlalchemy.orm import relation, backref
from sqlalchemy.ext.declarative import declarative_base

from repoze.profile.profiler import AccumulatingProfileMiddleware

def make_middleware(app):
    return AccumulatingProfileMiddleware(
        app,
        log_filename='/tmp/profile.log',
        discard_first_request=True,
        flush_at_shutdown=True,
        path='/__profile__')

Base = declarative_base()

class User(Base):
   __tablename__ = 'users'
   id = sa.Column(sa.Integer, primary_key=True)
   name = sa.Column(sa.Unicode(12))
   fullname = sa.Column(sa.Unicode(40))
   password = sa.Column(sa.Unicode(20))

def simple_app(environ, start_response):
    resp = webob.Response()
    fs = formalchemy.FieldSet(User)
    body = fs.bind(User()).render()
    body += fs.bind(User()).render()
    fs.rebind(User())
    body += fs.render()
    resp.body = body
    return resp(environ, start_response)

if __name__ == '__main__':
    import sys
    import os
    import signal
    from paste.httpserver import serve
    print 'Now do:'
    print 'ab -n 100 http://127.0.0.1:8080/'
    print 'wget -O - http://127.0.0.1:8080/__profile__'
    serve(make_middleware(simple_app))

########NEW FILE########
__FILENAME__ = environment
"""Pylons environment configuration"""
import os

from mako.lookup import TemplateLookup
from pylons.configuration import PylonsConfig
from pylons.error import handle_mako_error
from sqlalchemy import engine_from_config

import pylonsapp.lib.app_globals as app_globals
import pylonsapp.lib.helpers
from pylonsapp.config.routing import make_map
from pylonsapp.model import init_model

def load_environment(global_conf, app_conf):
    """Configure the Pylons environment via the ``pylons.config``
    object
    """
    config = PylonsConfig()
    
    # Pylons paths
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    paths = dict(root=root,
                 controllers=os.path.join(root, 'controllers'),
                 static_files=os.path.join(root, 'public'),
                 templates=[os.path.join(root, 'templates')])

    # Initialize config with the basic options
    config.init_app(global_conf, app_conf, package='pylonsapp', paths=paths)

    config['routes.map'] = make_map(config)
    config['pylons.app_globals'] = app_globals.Globals(config)
    config['pylons.h'] = pylonsapp.lib.helpers
    
    # Setup cache object as early as possible
    import pylons
    pylons.cache._push_object(config['pylons.app_globals'].cache)
    

    # Create the Mako TemplateLookup, with the default auto-escaping
    config['pylons.app_globals'].mako_lookup = TemplateLookup(
        directories=paths['templates'],
        error_handler=handle_mako_error,
        module_directory=os.path.join(app_conf['cache_dir'], 'templates'),
        input_encoding='utf-8', default_filters=['escape'],
        imports=['from webhelpers.html import escape'])

    # Setup the SQLAlchemy database engine
    engine = engine_from_config(config, 'sqlalchemy.')
    init_model(engine)

    # CONFIGURATION OPTIONS HERE (note: all config options will override
    # any Pylons config options)
    
    return config

########NEW FILE########
__FILENAME__ = middleware
"""Pylons middleware initialization"""
from beaker.middleware import SessionMiddleware
from paste.cascade import Cascade
from paste.registry import RegistryManager
from paste.urlparser import StaticURLParser
from paste.deploy.converters import asbool
from pylons.middleware import ErrorHandler, StatusCodeRedirect
from pylons.wsgiapp import PylonsApp
from routes.middleware import RoutesMiddleware

from pylonsapp.config.environment import load_environment

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

    # The Pylons WSGI app
    app = PylonsApp(config=config)

    # Routing/Session/Cache Middleware
    app = RoutesMiddleware(app, config['routes.map'])
    app = SessionMiddleware(app, config)

    # CUSTOM MIDDLEWARE HERE (filtered by error handling middlewares)

    if asbool(full_stack):
        # Handle Python exceptions
        app = ErrorHandler(app, global_conf, **config['pylons.errorware'])

        # Display error documents for 401, 403, 404 status codes (and
        # 500 when debug is disabled)
        if asbool(config['debug']):
            app = StatusCodeRedirect(app)
        else:
            app = StatusCodeRedirect(app, [400, 401, 403, 404, 500])

    # Establish the Registry for this application
    app = RegistryManager(app)

    if asbool(static_files):
        # Serve static files
        static_app = StaticURLParser(config['pylons.paths']['static_files'])
        app = Cascade([static_app, app])
    app.config = config
    return app

########NEW FILE########
__FILENAME__ = routing
"""Routes configuration

The more specific and detailed routes should be defined first so they
may take precedent over the more generic routes. For more information
refer to the routes manual at http://routes.groovie.org/docs/
"""
from routes import Mapper

def make_map(config):
    """Create, configure and return the routes Mapper"""
    map = Mapper(directory=config['pylons.paths']['controllers'],
                 always_scan=config['debug'])
    map.minimization = False

    # The ErrorController route (handles 404/500 error pages); it should
    # likely stay at the top, ensuring it can always be resolved
    map.connect('/error/{action}', controller='error')
    map.connect('/error/{action}/{id}', controller='error')

    # CUSTOM ROUTES HERE
    # Map the /admin url to FA's AdminController
    # Map static files
    map.connect('fa_static', '/admin/_static/{path_info:.*}', controller='admin', action='static')
    # Index page
    map.connect('admin', '/admin', controller='admin', action='models')
    map.connect('formatted_admin', '/admin.json', controller='admin', action='models', format='json')
    # Models
    map.resource('model', 'models', path_prefix='/admin/{model_name}', controller='admin')

    # serve couchdb's Pets as resource
    # Index page
    map.connect('couchdb', '/couchdb', controller='couchdb', action='models')
    # Model resources
    map.resource('node', 'nodes', path_prefix='/couchdb/{model_name}', controller='couchdb')


    # serve Owner Model as resource
    map.resource('owner', 'owners')

    map.connect('/{controller}/{action}')
    map.connect('/{controller}/{action}/{id}')

    return map

########NEW FILE########
__FILENAME__ = admin
import logging
from formalchemy.ext.pylons.controller import ModelsController
from webhelpers.paginate import Page
from pylonsapp.lib.base import BaseController, render
from pylonsapp import model
from pylonsapp import forms
from pylonsapp.model import meta

log = logging.getLogger(__name__)

class AdminControllerBase(BaseController):
    model = model # where your SQLAlchemy mappers are
    forms = forms # module containing FormAlchemy fieldsets definitions
    def Session(self): # Session factory
        return meta.Session

    ## customize the query for a model listing
    # def get_page(self):
    #     if self.model_name == 'Foo':
    #         return Page(meta.Session.query(model.Foo).order_by(model.Foo.bar)
    #     return super(AdminControllerBase, self).get_page()

AdminController = ModelsController(AdminControllerBase,
                                   prefix_name='admin',
                                   member_name='model',
                                   collection_name='models',
                                  )

########NEW FILE########
__FILENAME__ = basic
import logging
from pylons import request, response, session, url, tmpl_context as c
from pylons.controllers.util import abort, redirect
from pylonsapp.lib.base import BaseController, render
from pylonsapp.model import meta
from pylonsapp import model
from pylonsapp.forms import FieldSet

log = logging.getLogger(__name__)

Foo = FieldSet(model.Foo)
Foo.configure(options=[Foo.bar.label('This is the bar field')])

class BasicController(BaseController):

    def index(self, id=None):
        if id:
            record = meta.Session.query(model.Foo).filter_by(id=id).first()
        else:
            record = model.Foo()
        assert record is not None, repr(id)
        c.fs = Foo.bind(record, data=request.POST or None)
        if request.POST and c.fs.validate():
            c.fs.sync()
            if id:
                meta.Session.update(record)
            else:
                meta.Session.add(record)
            meta.Session.commit()
            redirect(url.current(id=record.id))
        return render('/form.mako')

########NEW FILE########
__FILENAME__ = couchdb
__doc__ = """This is an example on ow to setup a CRUD UI with couchdb as
backend"""
import os
import logging
import pylonsapp
from couchdbkit import *
from webhelpers.paginate import Page
from pylonsapp.lib.base import BaseController, render
from couchdbkit.loaders import FileSystemDocsLoader
from formalchemy.ext import couchdb
from formalchemy.ext.pylons.controller import ModelsController

log = logging.getLogger(__name__)

class Person(couchdb.Document):
    """A Person node"""
    name = StringProperty(required=True)
    def __unicode__(self):
        return self.name or u''

class Pet(couchdb.Document):
    """A Pet node"""
    name = StringProperty(required=True)
    type = StringProperty(required=True)
    birthdate = DateProperty(auto_now=True)
    weight_in_pounds = IntegerProperty(default=0)
    spayed_or_neutered = BooleanProperty()
    owner = SchemaListProperty(Person)
    def __unicode__(self):
        return self.name or u''

# You don't need a try/except. This is just to allow to run FA's tests without
# couchdb installed. Btw this have to be in another place in your app. eg: you
# don't need to sync views each time the controller is loaded.
try:
    server = Server()
    if server: pass
except:
    server = None
else:
    db = server.get_or_create_db('formalchemy_test')

    design_docs = os.path.join(os.path.dirname(pylonsapp.__file__), '_design')
    loader = FileSystemDocsLoader(design_docs)
    loader.sync(db, verbose=True)

    contain(db, Pet, Person)

class CouchdbController(BaseController):

    # override default classes to use couchdb fieldsets
    FieldSet = couchdb.FieldSet
    Grid = couchdb.Grid
    model = [Person, Pet]

    def Session(self):
        """return a formalchemy.ext.couchdb.Session"""
        return couchdb.Session(db)

CouchdbController = ModelsController(CouchdbController, prefix_name='couchdb', member_name='node', collection_name='nodes')

########NEW FILE########
__FILENAME__ = error
import cgi

from paste.urlparser import PkgResourcesParser
from pylons.middleware import error_document_template
from webhelpers.html.builder import literal

from pylonsapp.lib.base import BaseController

class ErrorController(BaseController):
    """Generates error documents as and when they are required.

    The ErrorDocuments middleware forwards to ErrorController when error
    related status codes are returned from the application.

    This behaviour can be altered by changing the parameters to the
    ErrorDocuments middleware in your config/middleware.py file.

    """
    def document(self):
        """Render the error document"""
        request = self._py_object.request
        resp = request.environ.get('pylons.original_response')
        content = literal(resp.body) or cgi.escape(request.GET.get('message', ''))
        page = error_document_template % \
            dict(prefix=request.environ.get('SCRIPT_NAME', ''),
                 code=cgi.escape(request.GET.get('code', str(resp.status_int))),
                 message=content)
        return page

    def img(self, id):
        """Serve Pylons' stock images"""
        return self._serve_file('/'.join(['media/img', id]))

    def style(self, id):
        """Serve Pylons' stock stylesheets"""
        return self._serve_file('/'.join(['media/style', id]))

    def _serve_file(self, path):
        """Call Paste's FileApp (a WSGI application) to serve the file
        at the specified path
        """
        request = self._py_object.request
        request.environ['PATH_INFO'] = '/%s' % path
        return PkgResourcesParser('pylons', 'pylons')(request.environ, self.start_response)

########NEW FILE########
__FILENAME__ = fsblob
import logging
from pylons import request, response, session, url, tmpl_context as c
from pylons.controllers.util import abort, redirect
from pylonsapp.lib.base import BaseController, render
from pylonsapp.model import meta
from pylonsapp import model
from pylonsapp.forms.fsblob import Files

log = logging.getLogger(__name__)

class FsblobController(BaseController):

    def index(self, id=None):
        if id:
            record = meta.Session.query(model.Files).filter_by(id=id).first()
        else:
            record = model.Files()
        assert record is not None, repr(id)
        c.fs = Files.bind(record, data=request.POST or None)
        if request.POST and c.fs.validate():
            c.fs.sync()
            if id:
                meta.Session.merge(record)
            else:
                meta.Session.add(record)
            meta.Session.commit()
            redirect(url.current(id=record.id))
        return render('/form.mako')

########NEW FILE########
__FILENAME__ = owners
import logging

from pylons import request, response, session, url, tmpl_context as c
from pylons.controllers.util import abort, redirect

from pylonsapp.lib.base import BaseController, render
from pylonsapp import model
from pylonsapp.model import meta

from formalchemy.ext.pylons.controller import RESTController

log = logging.getLogger(__name__)

class OwnersController(BaseController):

    def Session(self):
        return meta.Session

    def get_model(self):
        return model.Owner

OwnersController = RESTController(OwnersController, 'owner', 'owners')

########NEW FILE########
__FILENAME__ = fsblob
# -*- coding: utf-8 -*-
from pylons import config
from pylonsapp import model
from pylonsapp.forms import FieldSet
from formalchemy.ext.fsblob import FileFieldRenderer

Files = FieldSet(model.Files)
Files.configure(options=[Files.path.with_renderer(
        FileFieldRenderer.new(
            storage_path=config['app_conf']['storage_path'],
            url_prefix='/'))])



########NEW FILE########
__FILENAME__ = app_globals
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
        self.cache = CacheManager(**parse_cache_config_options(config))

########NEW FILE########
__FILENAME__ = base
"""The base Controller API

Provides the BaseController class for subclassing.
"""
from pylons.controllers import WSGIController
from pylons.templating import render_mako as render

from pylonsapp.model.meta import Session

class BaseController(WSGIController):

    def __call__(self, environ, start_response):
        """Invoke the Controller"""
        # WSGIController.__call__ dispatches to the Controller method
        # the request is routed to. This routing information is
        # available in environ['pylons.routes_dict']
        try:
            return WSGIController.__call__(self, environ, start_response)
        finally:
            Session.remove()

########NEW FILE########
__FILENAME__ = helpers
"""Helper functions

Consists of functions to typically be used within templates, but also
available to Controllers. This module is available to templates as 'h'.
"""
# Import helpers as desired, or define your own, ie:
#from webhelpers.html.tags import checkbox, password

########NEW FILE########
__FILENAME__ = meta
"""SQLAlchemy Metadata and Session object"""
from sqlalchemy import MetaData
from sqlalchemy.orm import scoped_session, sessionmaker

__all__ = ['Session', 'metadata']

# SQLAlchemy session manager. Updated by model.init_model()
Session = scoped_session(sessionmaker())

# Global metadata. If you have multiple databases with overlapping table
# names, you'll need a metadata for each database
metadata = MetaData()

########NEW FILE########
__FILENAME__ = test_admin
from pylonsapp.tests import *
from pylonsapp import model
from pylonsapp.model import meta
import simplejson as json

class TestAdminController(TestController):

    def setUp(self):
        TestController.setUp(self)
        meta.Session.bind.execute(model.foo_table.delete())

    def test_index(self):
        # index
        response = self.app.get(url('admin'))
        response.mustcontain('/admin/Foo/models')
        response = response.click('Foo')

        ## Simple model

        # add page
        response.mustcontain('/admin/Foo/models/new')
        response = response.click('New Foo')
        form = response.forms[0]
        form['Foo--bar'] = 'value'
        response = form.submit()
        assert response.headers['location'] == 'http://localhost/admin/Foo/models'

        # model index
        response = response.follow()
        response.mustcontain('<td>value</td>')

        # edit page
        form = response.forms[0]
        response = form.submit()
        form = response.forms[0]
        form['Foo-1-bar'] = 'new value'
        form['_method'] = 'PUT'
        response = form.submit()
        response = response.follow()

        # model index
        response.mustcontain('<td>new value</td>')

        # delete
        response = self.app.get(url('models', model_name='Foo'))
        response.mustcontain('<td>new value</td>')
        response = response.forms[1].submit()
        response = response.follow()

        assert 'new value' not in response, response

    def test_fk(self):
        response = self.app.get(url('admin'))
        response.mustcontain('/admin/Animal/models')

        ## Animals / FK
        response = response.click('Animal')

        # add page
        response.mustcontain('/admin/Animal/models/new', 'New Animal')
        response = response.click('New Animal')
        response.mustcontain('<option value="1">gawel</option>')
        form = response.forms[0]
        form['Animal--name'] = 'dewey'
        form['Animal--owner_id'] = '1'
        response = form.submit()
        assert response.headers['location'] == 'http://localhost/admin/Animal/models'

    def test_json(self):
        # index
        response = self.app.get(url('formatted_admin', format='json'))
        response.mustcontain('{"models": {"Files": "/admin/Files/models",')

        ## Simple model

        # add page
        response = self.app.post(url('formatted_models', model_name='Foo', format='json'),
                                    {'Foo--bar': 'value'})

        data = json.loads(response.body)
        id = data['item_url'].split('/')[-1]

        response.mustcontain('"Foo-%s-bar": "value"' % id)


        # get data
        response = self.app.get('%s.json' % data['item_url'])
        response.mustcontain('"Foo-%s-bar": "value"' % id)

        # edit page
        response = self.app.put('%s.json' % data['item_url'], '{"Foo-%s-bar": "new value"}' % id)
        response.mustcontain('"Foo-%s-bar": "new value"' % id)

        # delete
        response = self.app.delete('%s.json' % data['item_url'])



########NEW FILE########
__FILENAME__ = test_basic
from pylonsapp.tests import *

class TestBasicController(TestController):

    def test_index(self):
        response = self.app.get(url(controller='basic', action='index'))
        response.mustcontain('This is the bar field')

########NEW FILE########
__FILENAME__ = test_couchdb
from pylonsapp.tests import *
from couchdbkit import Server

try:
    server = Server()
    if server: pass
except:
    server = None
else:
    try:
        server.delete_db('formalchemy_test')
    except:
        pass
    db = server.get_or_create_db('formalchemy_test')

def couchdb_runing(func):
    if server:
        return func
    else:
        def f(self): pass
        return f

class TestCouchdbController(TestController):

    @couchdb_runing
    def test_index(self):
        response = self.app.get('/couchdb')
        response.mustcontain('/couchdb/Pet/nodes')
        response = response.click('Pet')

        response.mustcontain('/couchdb/Pet/nodes/new')
        response = response.click('New Pet')
        form = response.forms[0]
        form['Pet--name'] = 'value'
        form['Pet--type'] = 'cat'
        response = form.submit()
        assert response.headers['location'] == 'http://localhost/couchdb/Pet/nodes'

        # model index
        response = response.follow()
        response.mustcontain('<td>value</td>')

        # edit page
        form = response.forms[0]
        response = form.submit()
        form = response.forms[0]
        for k in form.fields.keys():
            if k and k.endswith('name'):
                form[k] = 'new value'
                node_id = k.split('-')[1]
        form['_method'] = 'PUT'
        response = form.submit()
        response = response.follow()

        # model index
        response.mustcontain('<td>new value</td>')

        # json response
        response = self.app.get('%s.json' % url('node', model_name='Pet', id=node_id))
        response.mustcontain('"fields": {"doc_type": "Pet", "name": "new value",')

        # delete
        response = self.app.get(url('nodes', model_name='Pet'))
        response.mustcontain('<td>new value</td>')
        response = response.forms[1].submit()
        response = response.follow()

        assert 'new value' not in response, response

########NEW FILE########
__FILENAME__ = test_fsblob
from pylonsapp.tests import *
from pylonsapp import model
from pylonsapp.model import meta
from pylons import config
import os

class TestFsblobController(TestController):

    def setUp(self):
        TestController.setUp(self)
        meta.Session.bind.execute(model.files_table.delete())

    def test_index(self):
        # form
        response = self.app.get(url(controller='fsblob', action='index'))
        response.mustcontain('Files--path')

        # test post file
        response = self.app.post(url(controller='fsblob', action='index'),
                                 upload_files=[('Files--path', 'test.txt', 'My test\n')])
        response = response.follow()
        response.mustcontain('Remove')

        # get file with http
        fresponse = response.click('test.txt')
        assert fresponse.headers['content-type'] == 'text/plain'
        fresponse.mustcontain('My test')

        # assume storage
        #fpath = os.path.join(config['app_conf']['storage_path'],
        #        fresponse.request.path_info[1:])

        #assert os.path.isfile(fpath), fpath

        # remove
        form = response.form
        form['Files-1-path--remove'] = True


########NEW FILE########
__FILENAME__ = test_owners
from pylonsapp.tests import *

class TestOwnersController(TestController):

    def test_index(self):
        resp = self.app.get(url('owners'))
        resp.mustcontain('gawel')

        resp = self.app.get(url('formatted_owners', format='json'))
        resp.mustcontain('"rows": [{"item_url": "/owners')

    def test_add(self):
        resp = self.app.post(url('/owners.json'), {"Owner--animals": '1', "Owner--name": "gawel"})
        resp.mustcontain('"gawel"', '/owners/')

    def test_view(self):
        resp = self.app.get(url('/owners/1'))
        resp.mustcontain('gawel')

        resp = self.app.get(url('/owners/1.json'))
        resp.mustcontain('"gawel"')

    def test_edit(self):
        resp = self.app.get(url('/owners/1/edit'))
        resp.mustcontain('<form action="/owners/1" method="POST" enctype="multipart/form-data">',
                         'gawel')

    def test_update(self):
        resp = self.app.put(url('/owners/31.json'), '{"Owner-31-animals": [1], "Owner-31-name": "gawel"}')
        resp.mustcontain('"gawel"', '/owners/31')


########NEW FILE########
__FILENAME__ = test_models

########NEW FILE########
