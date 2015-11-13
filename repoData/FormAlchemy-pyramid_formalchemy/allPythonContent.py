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
# pyramid_formalchemy documentation build configuration file, created by
# sphinx-quickstart on Sat Jan 15 20:18:53 2011.
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
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.doctest', 'sphinx.ext.intersphinx']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.txt'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'pyramid_formalchemy'
copyright = u'2011, Gael Pasgrimaud'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '0.1'
# The full version, including alpha/beta/rc tags.
release = version

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
htmlhelp_basename = 'pyramid_formalchemydoc'


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'pyramid_formalchemy.tex', u'pyramid\\_formalchemy Documentation',
   u'Gael Pasgrimaud', 'manual'),
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
    ('index', 'pyramid_formalchemy', u'pyramid_formalchemy Documentation',
     [u'Gael Pasgrimaud'], 1)
]


# Example configuration for intersphinx: refer to the Python standard library.
intersphinx_mapping = {
    'pyramid': ('http://docs.pylonsproject.org/projects/pyramid/1.0', None),
    'formalchemy': ('http://docs.formalchemy.org/formalchemy/', None),
  }

html_theme = 'nature'
rstctl_exclude = ['fa.jquery.app', 'fa.jquery.pylons']

import rstctl
extensions.append('rstctl.sphinx')
del rstctl

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
__FILENAME__ = events
from pyramid_formalchemy import events
from pyramidapp.models import Foo
import logging

log = logging.getLogger(__name__)

@events.subscriber([Foo, events.IBeforeValidateEvent])
def before_foo_validate(context, event):
    log.info("%r will be validated" % context)

@events.subscriber([Foo, events.IAfterSyncEvent])
def after_foo_sync(context, event):
    log.info("%r foo has been synced" % context)

@events.subscriber([Foo, events.IBeforeDeleteEvent])
def before_foo_delete(context, event):
    log.info("%r foo will be deleted" % context)

@events.subscriber([Foo, events.IBeforeRenderEvent])
def before_foo_render(context, event):
    log.info("%r foo will be rendered" % event.object)

@events.subscriber([Foo, events.IBeforeShowRenderEvent])
def before_foo_show_render(context, event):
    log.info("%r foo show will be rendered" % event.object)

@events.subscriber([Foo, events.IBeforeEditRenderEvent])
def before_foo_edit_render(context, event):
    log.info("%r foo edit will be rendered" % event.object)

@events.subscriber([Foo, events.IBeforeListingRenderEvent])
def before_foo_listing_render(context, event):
    log.info("%r listing will be rendered" % context)


########NEW FILE########
__FILENAME__ = forms
# -*- coding: utf-8 -*-
from pyramid_formalchemy.utils import TemplateEngine
from pyramidapp import models
from formalchemy import Grid, FieldSet
from formalchemy import fields
from formalchemy import config

config.engine = TemplateEngine()

FieldSet.default_renderers['dropdown'] = fields.SelectFieldRenderer

MyModel = FieldSet(models.MyModel)

GridMyModel = Grid(models.MyModel)
GridMyModelReadOnly = Grid(models.MyModel)
GridMyModelReadOnly.configure(readonly=True)

FooEdit = FieldSet(models.Foo)
FooEdit.configure()

########NEW FILE########
__FILENAME__ = jquery
# -*- coding: utf-8 -*-
from pyramid.config import Configurator
from sqlalchemy import engine_from_config

from pyramidapp.models import initialize_sql

def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application.
    """
    engine = engine_from_config(settings, 'sqlalchemy.')
    initialize_sql(engine)
    config = Configurator(settings=settings)
    config.add_static_view('static', 'pyramidapp:static')
    config.add_route('home', '/')
    config.add_view('pyramidapp.views.my_view',
                    route_name='home',
                    renderer='templates/mytemplate.pt')

    # pyramid_formalchemy's configuration
    config.include('pyramid_fanstatic')
    config.include('pyramid_formalchemy')
    config.include('fa.jquery')

    # register an admin UI
    config.formalchemy_admin('/admin', package='pyramidapp', view='fa.jquery.pyramid.ModelView')

    # register an admin UI for a single model
    config.formalchemy_model('/foo', package='pyramidapp',
                                    view='fa.jquery.pyramid.ModelView',
                                    model='pyramidapp.models.Foo')

    return config.make_wsgi_app()



########NEW FILE########
__FILENAME__ = models
import transaction

from sqlalchemy import Table
from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import Unicode
from sqlalchemy import ForeignKey

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import relation
from sqlalchemy.ext.declarative import declarative_base

from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import sessionmaker

from zope.sqlalchemy import ZopeTransactionExtension
from pyramid.security import Allow, Authenticated, ALL_PERMISSIONS

DBSession = scoped_session(sessionmaker(extension=ZopeTransactionExtension()))
Base = declarative_base()

class MyModel(Base):
    __tablename__ = 'models'
    id = Column(Integer, primary_key=True)
    name = Column(Unicode(255), unique=True)
    value = Column(Integer)

class Foo(Base):
    __tablename__ = 'foo'
    __acl__ = [
            (Allow, 'admin', ALL_PERMISSIONS),
            (Allow, Authenticated, 'view'),
            (Allow, 'editor', 'edit'),
            (Allow, 'manager', ('new', 'edit', 'delete')),
        ]
    id = Column(Integer, primary_key=True)
    bar = Column(Unicode(255))


class Bar(Base):
    __tablename__ = 'bar'
    __acl__ = [
            (Allow, 'admin', ALL_PERMISSIONS),
            (Allow, 'bar_manager', ('view', 'new', 'edit')),
        ]
    id = Column(Integer, primary_key=True)
    foo = Column(Unicode(255))

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    name = Column(Unicode)
    group_id = Column(Integer, ForeignKey('groups.id'))
    group = relation("Group", backref='users')

    def __unicode__(self):
        return self.name

group_permissions = Table('group_permissions', Base.metadata,
        Column('permission_id', Integer, ForeignKey('permissions.id')),
        Column('group_id', Integer, ForeignKey('groups.id')),
    )

class Group(Base):
    __tablename__ = 'groups'
    id = Column(Integer, primary_key=True)
    name = Column(Unicode)
    permissions = relation("Permission", secondary=group_permissions, backref="groups")

    def __unicode__(self):
        return self.name

class Permission(Base):
    __tablename__ = 'permissions'
    id = Column(Integer, primary_key=True)
    name = Column(Unicode)

    def __unicode__(self):
        return self.name

def populate():
    session = DBSession()
    model = MyModel(name=u'root',value=55)
    session.add(model)
    session.flush()
    for i in range(50):
        model = MyModel(name=u'root%i' % i,value=i)
        session.add(model)
        session.flush()
    g = Group()
    g.id = 1
    g.name = 'group1'
    transaction.commit()

def initialize_sql(engine):
    DBSession.configure(bind=engine)
    Base.metadata.bind = engine
    Base.metadata.create_all(engine)
    try:
        populate()
    except IntegrityError:
        DBSession.rollback()

########NEW FILE########
__FILENAME__ = resources
class Root(object):
    def __init__(self, request):
        self.request = request

########NEW FILE########
__FILENAME__ = security
from pyramid.config import Configurator
from sqlalchemy import engine_from_config
from pyramid.authorization import ACLAuthorizationPolicy
from pyramid.authentication import RemoteUserAuthenticationPolicy
from pyramid_formalchemy.resources import Models
from pyramid.security import Allow, Authenticated, ALL_PERMISSIONS

from pyramidapp.models import initialize_sql

class ModelsWithACL(Models):
    """A factory to override the default security setting"""
    __acl__ = [
            (Allow, 'admin', ALL_PERMISSIONS),
            (Allow, Authenticated, 'view'),
            (Allow, 'editor', 'edit'),
            (Allow, 'manager', ('new', 'edit', 'delete')),
        ]

def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application.
    """
    engine = engine_from_config(settings, 'sqlalchemy.')
    initialize_sql(engine)

    # configure the security stuff
    config = Configurator(settings=settings,
                          authentication_policy=RemoteUserAuthenticationPolicy(),
                          authorization_policy=ACLAuthorizationPolicy())

    config.add_static_view('static', 'pyramidapp:static')
    config.add_route('home', '/')
    config.add_view('pyramidapp.views.my_view',
                    route_name='home',
                    renderer='templates/mytemplate.pt')

    # pyramid_formalchemy's configuration
    config.include('pyramid_formalchemy')
    config.formalchemy_admin('admin', package='pyramidapp',
                             factory=ModelsWithACL) # use the secure factory

    return config.make_wsgi_app()



########NEW FILE########
__FILENAME__ = foolisting.pt
registry = dict(version=0)
def bind():
    from cPickle import loads as _loads
    _lookup_attr = _loads('cchameleon.core.codegen\nlookup_attr\np1\n.')
    _init_scope = _loads('cchameleon.core.utils\necontext\np1\n.')
    _attrs_4357125136 = _loads('(dp1\nVclass\np2\nVlayout-grid\np3\ns.')
    _attrs_4357125072 = _loads('(dp1\nVclass\np2\nVui-pager\np3\ns.')
    _attrs_4357124944 = _loads('(dp1\n.')
    _init_stream = _loads('cchameleon.core.generation\ninitialize_stream\np1\n.')
    _attrs_4357125200 = _loads('(dp1\nVclass\np2\nVfa_field\np3\ns.')
    _init_default = _loads('cchameleon.core.generation\ninitialize_default\np1\n.')
    _init_tal = _loads('cchameleon.core.generation\ninitialize_tal\np1\n.')
    def render(econtext, rcontext=None):
        macros = econtext.get('macros')
        _translate = econtext.get('_translate')
        _slots = econtext.get('_slots')
        target_language = econtext.get('target_language')
        u'_init_stream()'
        (_out, _write, ) = _init_stream()
        u'_init_tal()'
        (_attributes, repeat, ) = _init_tal()
        u'_init_default()'
        _default = _init_default()
        u'None'
        default = None
        u'None'
        _domain = None
        u"main.macros['master']"
        _metal = _lookup_attr(econtext['main'], 'macros')['master']
        def _callback_main(econtext, _repeat, _out=_out, _write=_write, _domain=_domain, **_ignored):
            if _repeat:
                repeat.update(_repeat)
            attrs = _attrs_4357124944
            u"''"
            _write(u'<div>\n      My Foo custom listing\n      ')
            _default.value = default = ''
            u'pager'
            _content = econtext['pager']
            attrs = _attrs_4357125072
            u'_content'
            _write(u'<div class="ui-pager">')
            _tmp1 = _content
            _tmp = _tmp1
            if (_tmp.__class__ not in (str, unicode, int, float, )):
                try:
                    _tmp = _tmp.__html__
                except:
                    _tmp = _translate(_tmp, domain=_domain, mapping=None, target_language=target_language, default=None)
                else:
                    _tmp = _tmp()
                    _write(_tmp)
                    _tmp = None
            if (_tmp is not None):
                if not isinstance(_tmp, unicode):
                    _tmp = str(_tmp)
                _write(_tmp)
            u"''"
            _write(u'</div>\n      ')
            _default.value = default = ''
            u'fs.render()'
            _content = _lookup_attr(econtext['fs'], 'render')()
            attrs = _attrs_4357125136
            u'_content'
            _write(u'<table class="layout-grid">')
            _tmp1 = _content
            _tmp = _tmp1
            if (_tmp.__class__ not in (str, unicode, int, float, )):
                try:
                    _tmp = _tmp.__html__
                except:
                    _tmp = _translate(_tmp, domain=_domain, mapping=None, target_language=target_language, default=None)
                else:
                    _tmp = _tmp()
                    _write(_tmp)
                    _tmp = None
            if (_tmp is not None):
                if not isinstance(_tmp, unicode):
                    _tmp = str(_tmp)
                _write(_tmp)
            u"u'\\n      '"
            _write(u'</table>\n      ')
            _default.value = default = u'\n      '
            u'actions.buttons(request)'
            _content = _lookup_attr(econtext['actions'], 'buttons')(econtext['request'])
            attrs = _attrs_4357125200
            u'_content'
            _write(u'<p class="fa_field">')
            _tmp1 = _content
            _tmp = _tmp1
            if (_tmp.__class__ not in (str, unicode, int, float, )):
                try:
                    _tmp = _tmp.__html__
                except:
                    _tmp = _translate(_tmp, domain=_domain, mapping=None, target_language=target_language, default=None)
                else:
                    _tmp = _tmp()
                    _write(_tmp)
                    _tmp = None
            if (_tmp is not None):
                if not isinstance(_tmp, unicode):
                    _tmp = str(_tmp)
                _write(_tmp)
            _write(u'</p>\n    </div>\n')
        u"{'main': _callback_main}"
        _tmp = {'main': _callback_main, }
        u"main.macros['master']"
        _metal.render(_tmp, _out=_out, _write=_write, _domain=_domain, econtext=econtext)
        return _out.getvalue()
    return render

__filename__ = '/Users/gawel/py/formalchemy_project/pyramid_formalchemy/pyramidapp/pyramidapp/templates/foolisting.pt'
registry[(None, True, '1488bdb950901f8f258549439ef6661a49aae984')] = bind()

########NEW FILE########
__FILENAME__ = fooshow.pt
registry = dict(version=0)
def bind():
    from cPickle import loads as _loads
    _lookup_attr = _loads('cchameleon.core.codegen\nlookup_attr\np1\n.')
    _init_scope = _loads('cchameleon.core.utils\necontext\np1\n.')
    _re_amp = _loads("cre\n_compile\np1\n(S'&(?!([A-Za-z]+|#[0-9]+);)'\np2\nI0\ntRp3\n.")
    _attrs_4356515344 = _loads('(dp1\n.')
    _attrs_4356515728 = _loads('(dp1\nVclass\np2\nVui-widget-header ui-widget-link ui-corner-all\np3\ns.')
    _attrs_4356515408 = _loads('(dp1\n.')
    _init_stream = _loads('cchameleon.core.generation\ninitialize_stream\np1\n.')
    _attrs_4356515920 = _loads('(dp1\nVclass\np2\nVui-icon ui-icon-circle-arrow-w\np3\ns.')
    _attrs_4356515664 = _loads('(dp1\nVhref\np2\nV#\nsVclass\np3\nVui-widget-header ui-widget-link ui-widget-button ui-corner-all\np4\ns.')
    _attrs_4356515216 = _loads('(dp1\n.')
    _init_default = _loads('cchameleon.core.generation\ninitialize_default\np1\n.')
    _attrs_4356515536 = _loads('(dp1\nVclass\np2\nVfa_field\np3\ns.')
    _attrs_4356515792 = _loads("(dp1\nVtype\np2\nVsubmit\np3\nsVvalue\np4\nV${F_('Edit')}\np5\ns.")
    _init_tal = _loads('cchameleon.core.generation\ninitialize_tal\np1\n.')
    def render(econtext, rcontext=None):
        macros = econtext.get('macros')
        _translate = econtext.get('_translate')
        _slots = econtext.get('_slots')
        target_language = econtext.get('target_language')
        u'_init_stream()'
        (_out, _write, ) = _init_stream()
        u'_init_tal()'
        (_attributes, repeat, ) = _init_tal()
        u'_init_default()'
        _default = _init_default()
        u'None'
        default = None
        u'None'
        _domain = None
        u"main.macros['master']"
        _metal = _lookup_attr(econtext['main'], 'macros')['master']
        def _callback_main(econtext, _repeat, _out=_out, _write=_write, _domain=_domain, **_ignored):
            if _repeat:
                repeat.update(_repeat)
            attrs = _attrs_4356515216
            u"''"
            _write(u'<div>\n      Custom Foo view\n      ')
            _default.value = default = ''
            u'fs.render()'
            _content = _lookup_attr(econtext['fs'], 'render')()
            attrs = _attrs_4356515344
            u'_content'
            _write(u'<div>')
            _tmp1 = _content
            _tmp = _tmp1
            if (_tmp.__class__ not in (str, unicode, int, float, )):
                try:
                    _tmp = _tmp.__html__
                except:
                    _tmp = _translate(_tmp, domain=_domain, mapping=None, target_language=target_language, default=None)
                else:
                    _tmp = _tmp()
                    _write(_tmp)
                    _tmp = None
            if (_tmp is not None):
                if not isinstance(_tmp, unicode):
                    _tmp = str(_tmp)
                _write(_tmp)
            _write(u'</div>\n      ')
            attrs = _attrs_4356515408
            _write(u'<div>\n        ')
            attrs = _attrs_4356515536
            _write(u'<p class="fa_field">\n          ')
            attrs = _attrs_4356515664
            u"request.fa_url(request.model_name, request.model_id, 'edit')"
            _write(u'<a class="ui-widget-header ui-widget-link ui-widget-button ui-corner-all"')
            _tmp1 = _lookup_attr(econtext['request'], 'fa_url')(_lookup_attr(econtext['request'], 'model_name'), _lookup_attr(econtext['request'], 'model_id'), 'edit')
            if (_tmp1 is _default):
                _tmp1 = u'#'
            if ((_tmp1 is not None) and (_tmp1 is not False)):
                if (_tmp1.__class__ not in (str, unicode, int, float, )):
                    _tmp1 = unicode(_translate(_tmp1, domain=_domain, mapping=None, target_language=target_language, default=None))
                else:
                    if not isinstance(_tmp1, unicode):
                        _tmp1 = str(_tmp1)
                if ('&' in _tmp1):
                    if (';' in _tmp1):
                        _tmp1 = _re_amp.sub('&amp;', _tmp1)
                    else:
                        _tmp1 = _tmp1.replace('&', '&amp;')
                if ('<' in _tmp1):
                    _tmp1 = _tmp1.replace('<', '&lt;')
                if ('>' in _tmp1):
                    _tmp1 = _tmp1.replace('>', '&gt;')
                if ('"' in _tmp1):
                    _tmp1 = _tmp1.replace('"', '&quot;')
                _write(((' href="' + _tmp1) + '"'))
            _write(u'>\n              ')
            attrs = _attrs_4356515792
            'join(value("F_(\'Edit\')"),)'
            _write(u'<input type="submit"')
            _tmp1 = econtext['F_']('Edit')
            if (_tmp1 is _default):
                _tmp1 = u"${F_('Edit')}"
            if ((_tmp1 is not None) and (_tmp1 is not False)):
                if (_tmp1.__class__ not in (str, unicode, int, float, )):
                    _tmp1 = unicode(_translate(_tmp1, domain=_domain, mapping=None, target_language=target_language, default=None))
                else:
                    if not isinstance(_tmp1, unicode):
                        _tmp1 = str(_tmp1)
                if ('&' in _tmp1):
                    if (';' in _tmp1):
                        _tmp1 = _re_amp.sub('&amp;', _tmp1)
                    else:
                        _tmp1 = _tmp1.replace('&', '&amp;')
                if ('<' in _tmp1):
                    _tmp1 = _tmp1.replace('<', '&lt;')
                if ('>' in _tmp1):
                    _tmp1 = _tmp1.replace('>', '&gt;')
                if ('"' in _tmp1):
                    _tmp1 = _tmp1.replace('"', '&quot;')
                _write(((' value="' + _tmp1) + '"'))
            _write(u' />\n          </a>\n          ')
            attrs = _attrs_4356515728
            u'request.fa_url(request.model_name)'
            _write(u'<a class="ui-widget-header ui-widget-link ui-corner-all"')
            _tmp1 = _lookup_attr(econtext['request'], 'fa_url')(_lookup_attr(econtext['request'], 'model_name'))
            if (_tmp1 is _default):
                _tmp1 = None
            if ((_tmp1 is not None) and (_tmp1 is not False)):
                if (_tmp1.__class__ not in (str, unicode, int, float, )):
                    _tmp1 = unicode(_translate(_tmp1, domain=_domain, mapping=None, target_language=target_language, default=None))
                else:
                    if not isinstance(_tmp1, unicode):
                        _tmp1 = str(_tmp1)
                if ('&' in _tmp1):
                    if (';' in _tmp1):
                        _tmp1 = _re_amp.sub('&amp;', _tmp1)
                    else:
                        _tmp1 = _tmp1.replace('&', '&amp;')
                if ('<' in _tmp1):
                    _tmp1 = _tmp1.replace('<', '&lt;')
                if ('>' in _tmp1):
                    _tmp1 = _tmp1.replace('>', '&gt;')
                if ('"' in _tmp1):
                    _tmp1 = _tmp1.replace('"', '&quot;')
                _write(((' href="' + _tmp1) + '"'))
            _write(u'>\n            ')
            attrs = _attrs_4356515920
            u"F_('Back')"
            _write(u'<span class="ui-icon ui-icon-circle-arrow-w"></span>\n            ')
            _tmp1 = econtext['F_']('Back')
            _tmp = _tmp1
            if (_tmp.__class__ not in (str, unicode, int, float, )):
                try:
                    _tmp = _tmp.__html__
                except:
                    _tmp = _translate(_tmp, domain=_domain, mapping=None, target_language=target_language, default=None)
                else:
                    _tmp = _tmp()
                    _write(_tmp)
                    _tmp = None
            if (_tmp is not None):
                if not isinstance(_tmp, unicode):
                    _tmp = str(_tmp)
                if ('&' in _tmp):
                    if (';' in _tmp):
                        _tmp = _re_amp.sub('&amp;', _tmp)
                    else:
                        _tmp = _tmp.replace('&', '&amp;')
                if ('<' in _tmp):
                    _tmp = _tmp.replace('<', '&lt;')
                if ('>' in _tmp):
                    _tmp = _tmp.replace('>', '&gt;')
                _write(_tmp)
            _write(u'\n          </a>\n        </p>\n      </div>\n    </div>\n')
        u"{'main': _callback_main}"
        _tmp = {'main': _callback_main, }
        u"main.macros['master']"
        _metal.render(_tmp, _out=_out, _write=_write, _domain=_domain, econtext=econtext)
        return _out.getvalue()
    return render

__filename__ = '/Users/gawel/py/formalchemy_project/pyramid_formalchemy/pyramidapp/pyramidapp/templates/fooshow.pt'
registry[(None, True, '1488bdb950901f8f258549439ef6661a49aae984')] = bind()

########NEW FILE########
__FILENAME__ = mytemplate.pt
registry = dict(version=0)
def bind():
    from cPickle import loads as _loads
    _lookup_attr = _loads('cchameleon.core.codegen\nlookup_attr\np1\n.')
    _attrs_4360318608 = _loads('(dp1\nVid\np2\nVfooter\np3\ns.')
    _attrs_4360315152 = _loads('(dp1\nVhref\np2\nVhttp://docs.pylonshq.com/pyramid/dev/#tutorials\np3\ns.')
    _re_amp = _loads("cre\n_compile\np1\n(S'&(?!([A-Za-z]+|#[0-9]+);)'\np2\nI0\ntRp3\n.")
    _attrs_4360318480 = _loads('(dp1\nVid\np2\nVwrap\np3\ns.')
    _attrs_4360315536 = _loads('(dp1\nVhref\np2\nVhttp://docs.pylonshq.com/pyramid/dev/#sample-applications\np3\ns.')
    _attrs_4360315728 = _loads('(dp1\nVclass\np2\nVmiddle align-center\np3\ns.')
    _attrs_4360317456 = _loads('(dp1\nVcontent\np2\nVpython web application\np3\nsVname\np4\nVkeywords\np5\ns.')
    _attrs_4360318864 = _loads('(dp1\nVid\np2\nVbottom\np3\ns.')
    _attrs_4360315216 = _loads('(dp1\nVclass\np2\nVtop align-center\np3\ns.')
    _attrs_4360315600 = _loads("(dp1\nVsrc\np2\nV${request.static_url('pyramidapp:static/pyramid.png')}\np3\nsVheight\np4\nV169\np5\nsVwidth\np6\nV750\np7\nsValt\np8\nVpyramid\np9\ns.")
    _attrs_4360316624 = _loads('(dp1\nVclass\np2\nVfooter\np3\ns.')
    _attrs_4360315792 = _loads('(dp1\n.')
    _attrs_4360297616 = _loads('(dp1\nVxmlns\np2\nVhttp://www.w3.org/1999/xhtml\np3\nsVxml:lang\np4\nVen\np5\ns.')
    _attrs_4360316368 = _loads('(dp1\n.')
    _attrs_4360341136 = _loads('(dp1\nVid\np2\nVmiddle\np3\ns.')
    _attrs_4360315024 = _loads('(dp1\nVhref\np2\nVhttp://docs.pylonshq.com/pyramid/dev/#api-documentation\np3\ns.')
    _attrs_4360318288 = _loads('(dp1\n.')
    _attrs_4360316880 = _loads('(dp1\n.')
    _attrs_4360316944 = _loads('(dp1\n.')
    _attrs_4360315280 = _loads('(dp1\n.')
    _init_default = _loads('cchameleon.core.generation\ninitialize_default\np1\n.')
    _attrs_4360317584 = _loads('(dp1\nVcontent\np2\nVpyramid web application\np3\nsVname\np4\nVdescription\np5\ns.')
    _attrs_4360318544 = _loads('(dp1\nVhref\np2\nVhttp://pylonshq.com\np3\ns.')
    _attrs_4360314960 = _loads('(dp1\n.')
    _init_tal = _loads('cchameleon.core.generation\ninitialize_tal\np1\n.')
    _attrs_4360318096 = _loads('(dp1\nVmedia\np2\nVscreen\np3\nsVcharset\np4\nVutf-8\np5\nsVhref\np6\nVhttp://fonts.googleapis.com/css?family=Nobile:regular,italic,bold,bolditalic&subset=latin\np7\nsVrel\np8\nVstylesheet\np9\nsVtype\np10\nVtext/css\np11\ns.')
    _attrs_4360317904 = _loads('(dp1\n.')
    _attrs_4360316816 = _loads('(dp1\nVid\np2\nVright\np3\nsVclass\np4\nValign-left\np5\ns.')
    _attrs_4360316752 = _loads('(dp1\nVid\np2\nVleft\np3\nsVclass\np4\nValign-right\np5\ns.')
    _attrs_4360315088 = _loads('(dp1\n.')
    _attrs_4360315408 = _loads('(dp1\nVhref\np2\nVhttp://docs.pylonshq.com/pyramid/dev/#change-history\np3\ns.')
    _attrs_4360318032 = _loads('(dp1\nVclass\np2\nVlinks\np3\ns.')
    _attrs_4360315472 = _loads('(dp1\n.')
    _attrs_4360318672 = _loads('(dp1\n.')
    _attrs_4360315344 = _loads('(dp1\n.')
    _attrs_4360316304 = _loads('(dp1\nVclass\np2\nVapp-name\np3\ns.')
    _attrs_4360317136 = _loads('(dp1\nVcontent\np2\nVtext/html;charset=UTF-8\np3\nsVhttp-equiv\np4\nVContent-Type\np5\ns.')
    _init_stream = _loads('cchameleon.core.generation\ninitialize_stream\np1\n.')
    _attrs_4360315984 = _loads('(dp1\nVclass\np2\nVbottom\np3\ns.')
    _init_scope = _loads('cchameleon.core.utils\necontext\np1\n.')
    _attrs_4360318800 = _loads('(dp1\nVhref\np2\nVhttp://docs.pylonshq.com/pyramid/dev/#narrative-documentation\np3\ns.')
    _attrs_4360317776 = _loads('(dp1\nVtype\np2\nVsubmit\np3\nsVid\np4\nVx\nsVvalue\np5\nVGo\np6\ns.')
    _attrs_4360317648 = _loads('(dp1\nVname\np2\nVq\nsVvalue\np3\nV\nsVtype\np4\nVtext\np5\nsVid\np6\nVq\ns.')
    _attrs_4360317392 = _loads('(dp1\nVaction\np2\nVhttp://docs.pylonshq.com/pyramid/dev/search.html\np3\nsVmethod\np4\nVget\np5\ns.')
    _attrs_4360315856 = _loads('(dp1\nVhref\np2\nVhttp://docs.pylonshq.com/pyramid/dev/#support-and-development\np3\ns.')
    _attrs_4360316112 = _loads('(dp1\nVhref\np2\nVirc://irc.freenode.net#pyramid\np3\ns.')
    _attrs_4360318416 = _loads('(dp1\n.')
    _attrs_4360317968 = _loads('(dp1\nVmedia\np2\nVscreen\np3\nsVcharset\np4\nVutf-8\np5\nsVhref\np6\nVhttp://fonts.googleapis.com/css?family=Neuton&subset=latin\np7\nsVrel\np8\nVstylesheet\np9\nsVtype\np10\nVtext/css\np11\ns.')
    _attrs_4360317712 = _loads("(dp1\nVhref\np2\nV${request.static_url('pyramidapp:static/favicon.ico')}\np3\nsVrel\np4\nVshortcut icon\np5\ns.")
    _attrs_4360318736 = _loads('(dp1\nVid\np2\nVtop\np3\ns.')
    _attrs_4360315920 = _loads('(dp1\nVclass\np2\nVapp-welcome\np3\ns.')
    _attrs_4360317328 = _loads('(dp1\n.')
    _attrs_4360317840 = _loads("(dp1\nVmedia\np2\nVscreen\np3\nsVcharset\np4\nVutf-8\np5\nsVhref\np6\nV${request.static_url('pyramidapp:static/pylons.css')}\np7\nsVrel\np8\nVstylesheet\np9\nsVtype\np10\nVtext/css\np11\ns.")
    _attrs_4360297360 = _loads('(dp1\n.')
    def render(econtext, rcontext=None):
        macros = econtext.get('macros')
        _translate = econtext.get('_translate')
        _slots = econtext.get('_slots')
        target_language = econtext.get('target_language')
        u'_init_stream()'
        (_out, _write, ) = _init_stream()
        u'_init_tal()'
        (_attributes, repeat, ) = _init_tal()
        u'_init_default()'
        _default = _init_default()
        u'None'
        default = None
        u'None'
        _domain = None
        _write('<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">\n')
        attrs = _attrs_4360297616
        _write(u'<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en">\n')
        attrs = _attrs_4360297360
        _write(u'<head>\n\t')
        attrs = _attrs_4360316880
        _write(u'<title>The Pyramid Web Application Development Framework</title>\n\t')
        attrs = _attrs_4360317136
        _write(u'<meta http-equiv="Content-Type" content="text/html;charset=UTF-8" />\n\t')
        attrs = _attrs_4360317456
        _write(u'<meta name="keywords" content="python web application" />\n\t')
        attrs = _attrs_4360317584
        _write(u'<meta name="description" content="pyramid web application" />\n\t')
        attrs = _attrs_4360317712
        'join(value("request.static_url(\'pyramidapp:static/favicon.ico\')"),)'
        _write(u'<link rel="shortcut icon"')
        _tmp1 = _lookup_attr(econtext['request'], 'static_url')('pyramidapp:static/favicon.ico')
        if (_tmp1 is _default):
            _tmp1 = u"${request.static_url('pyramidapp:static/favicon.ico')}"
        if ((_tmp1 is not None) and (_tmp1 is not False)):
            if (_tmp1.__class__ not in (str, unicode, int, float, )):
                _tmp1 = unicode(_translate(_tmp1, domain=_domain, mapping=None, target_language=target_language, default=None))
            else:
                if not isinstance(_tmp1, unicode):
                    _tmp1 = str(_tmp1)
            if ('&' in _tmp1):
                if (';' in _tmp1):
                    _tmp1 = _re_amp.sub('&amp;', _tmp1)
                else:
                    _tmp1 = _tmp1.replace('&', '&amp;')
            if ('<' in _tmp1):
                _tmp1 = _tmp1.replace('<', '&lt;')
            if ('>' in _tmp1):
                _tmp1 = _tmp1.replace('>', '&gt;')
            if ('"' in _tmp1):
                _tmp1 = _tmp1.replace('"', '&quot;')
            _write(((' href="' + _tmp1) + '"'))
        _write(u' />\n\t')
        attrs = _attrs_4360317840
        'join(value("request.static_url(\'pyramidapp:static/pylons.css\')"),)'
        _write(u'<link rel="stylesheet"')
        _tmp1 = _lookup_attr(econtext['request'], 'static_url')('pyramidapp:static/pylons.css')
        if (_tmp1 is _default):
            _tmp1 = u"${request.static_url('pyramidapp:static/pylons.css')}"
        if ((_tmp1 is not None) and (_tmp1 is not False)):
            if (_tmp1.__class__ not in (str, unicode, int, float, )):
                _tmp1 = unicode(_translate(_tmp1, domain=_domain, mapping=None, target_language=target_language, default=None))
            else:
                if not isinstance(_tmp1, unicode):
                    _tmp1 = str(_tmp1)
            if ('&' in _tmp1):
                if (';' in _tmp1):
                    _tmp1 = _re_amp.sub('&amp;', _tmp1)
                else:
                    _tmp1 = _tmp1.replace('&', '&amp;')
            if ('<' in _tmp1):
                _tmp1 = _tmp1.replace('<', '&lt;')
            if ('>' in _tmp1):
                _tmp1 = _tmp1.replace('>', '&gt;')
            if ('"' in _tmp1):
                _tmp1 = _tmp1.replace('"', '&quot;')
            _write(((' href="' + _tmp1) + '"'))
        _write(u' type="text/css" media="screen" charset="utf-8" />\n\t')
        attrs = _attrs_4360317968
        _write(u'<link rel="stylesheet" href="http://fonts.googleapis.com/css?family=Neuton&amp;subset=latin" type="text/css" media="screen" charset="utf-8" />\n\t')
        attrs = _attrs_4360318096
        u"request.static_url('pyramidapp:static/ie6.css')"
        _write(u'<link rel="stylesheet" href="http://fonts.googleapis.com/css?family=Nobile:regular,italic,bold,bolditalic&amp;subset=latin" type="text/css" media="screen" charset="utf-8" />\n\t<!--[if lte IE 6]>\n\t<link rel="stylesheet" href="')
        _tmp1 = _lookup_attr(econtext['request'], 'static_url')('pyramidapp:static/ie6.css')
        _tmp = _tmp1
        if (_tmp.__class__ not in (str, unicode, int, float, )):
            try:
                _tmp = _tmp.__html__
            except:
                _tmp = _translate(_tmp, domain=_domain, mapping=None, target_language=target_language, default=None)
            else:
                _tmp = _tmp()
                _write(_tmp)
                _tmp = None
        if (_tmp is not None):
            if not isinstance(_tmp, unicode):
                _tmp = str(_tmp)
            if ('&' in _tmp):
                if (';' in _tmp):
                    _tmp = _re_amp.sub('&amp;', _tmp)
                else:
                    _tmp = _tmp.replace('&', '&amp;')
            if ('<' in _tmp):
                _tmp = _tmp.replace('<', '&lt;')
            if ('>' in _tmp):
                _tmp = _tmp.replace('>', '&gt;')
            _write(_tmp)
        _write(u'" type="text/css" media="screen" charset="utf-8" />\n\t<![endif]-->\n</head>\n')
        attrs = _attrs_4360316944
        _write(u'<body>\n\t')
        attrs = _attrs_4360318480
        _write(u'<div id="wrap">\n\t\t')
        attrs = _attrs_4360318736
        _write(u'<div id="top">\n\t\t\t')
        attrs = _attrs_4360315216
        _write(u'<div class="top align-center">\n\t\t\t\t')
        attrs = _attrs_4360315280
        _write(u'<div>')
        attrs = _attrs_4360315600
        'join(value("request.static_url(\'pyramidapp:static/pyramid.png\')"),)'
        _write(u'<img')
        _tmp1 = _lookup_attr(econtext['request'], 'static_url')('pyramidapp:static/pyramid.png')
        if (_tmp1 is _default):
            _tmp1 = u"${request.static_url('pyramidapp:static/pyramid.png')}"
        if ((_tmp1 is not None) and (_tmp1 is not False)):
            if (_tmp1.__class__ not in (str, unicode, int, float, )):
                _tmp1 = unicode(_translate(_tmp1, domain=_domain, mapping=None, target_language=target_language, default=None))
            else:
                if not isinstance(_tmp1, unicode):
                    _tmp1 = str(_tmp1)
            if ('&' in _tmp1):
                if (';' in _tmp1):
                    _tmp1 = _re_amp.sub('&amp;', _tmp1)
                else:
                    _tmp1 = _tmp1.replace('&', '&amp;')
            if ('<' in _tmp1):
                _tmp1 = _tmp1.replace('<', '&lt;')
            if ('>' in _tmp1):
                _tmp1 = _tmp1.replace('>', '&gt;')
            if ('"' in _tmp1):
                _tmp1 = _tmp1.replace('"', '&quot;')
            _write(((' src="' + _tmp1) + '"'))
        _write(u' width="750" height="169" alt="pyramid" /></div>\n\t\t\t</div>\n\t\t</div>\n\t\t')
        attrs = _attrs_4360341136
        _write(u'<div id="middle">\n\t\t\t')
        attrs = _attrs_4360315728
        _write(u'<div class="middle align-center">\n\t\t\t\t')
        attrs = _attrs_4360315920
        _write(u'<p class="app-welcome">\n\t\t\t\t\tWelcome to ')
        attrs = _attrs_4360316304
        u'project'
        _write(u'<span class="app-name">')
        _tmp1 = econtext['project']
        _tmp = _tmp1
        if (_tmp.__class__ not in (str, unicode, int, float, )):
            try:
                _tmp = _tmp.__html__
            except:
                _tmp = _translate(_tmp, domain=_domain, mapping=None, target_language=target_language, default=None)
            else:
                _tmp = _tmp()
                _write(_tmp)
                _tmp = None
        if (_tmp is not None):
            if not isinstance(_tmp, unicode):
                _tmp = str(_tmp)
            if ('&' in _tmp):
                if (';' in _tmp):
                    _tmp = _re_amp.sub('&amp;', _tmp)
                else:
                    _tmp = _tmp.replace('&', '&amp;')
            if ('<' in _tmp):
                _tmp = _tmp.replace('<', '&lt;')
            if ('>' in _tmp):
                _tmp = _tmp.replace('>', '&gt;')
            _write(_tmp)
        _write(u'</span>, an application generated by')
        attrs = _attrs_4360316368
        _write(u'<br />\n\t\t\t\t\tthe Pyramid web application development framework.\n\t\t\t\t</p>\n\t\t\t</div>\n\t\t</div>\n\t\t')
        attrs = _attrs_4360318864
        _write(u'<div id="bottom">\n\t\t\t')
        attrs = _attrs_4360315984
        _write(u'<div class="bottom">\n\t\t\t\t')
        attrs = _attrs_4360316752
        _write(u'<div id="left" class="align-right">\n\t\t\t\t\t')
        attrs = _attrs_4360317328
        _write(u'<h2>Search documentation</h2>\n\t\t\t\t\t')
        attrs = _attrs_4360317392
        _write(u'<form method="get" action="http://docs.pylonshq.com/pyramid/dev/search.html">\n\t\t      \t\t\t')
        attrs = _attrs_4360317648
        _write(u'<input type="text" id="q" name="q" value="" />\n\t\t      \t\t\t')
        attrs = _attrs_4360317776
        _write(u'<input type="submit" id="x" value="Go" />\n\t\t  \t\t\t</form>\n\t\t\t\t</div>\n\t\t\t\t')
        attrs = _attrs_4360316816
        _write(u'<div id="right" class="align-left">\n\t\t\t\t\t')
        attrs = _attrs_4360317904
        _write(u'<h2>Pyramid links</h2>\n\t\t\t\t\t')
        attrs = _attrs_4360318032
        _write(u'<ul class="links">\n\t\t\t\t\t\t')
        attrs = _attrs_4360318288
        _write(u'<li>\n\t\t\t\t\t\t\t')
        attrs = _attrs_4360318544
        _write(u'<a href="http://pylonshq.com">Pylons Website</a>\n\t\t\t\t\t\t</li>\n\t\t\t\t\t\t')
        attrs = _attrs_4360318416
        _write(u'<li>\n\t\t\t\t\t\t\t')
        attrs = _attrs_4360318800
        _write(u'<a href="http://docs.pylonshq.com/pyramid/dev/#narrative-documentation">Narrative Documentation</a>\n\t\t\t\t\t\t</li>\n\t\t\t\t\t\t')
        attrs = _attrs_4360318672
        _write(u'<li>\n\t\t\t\t\t\t\t')
        attrs = _attrs_4360315024
        _write(u'<a href="http://docs.pylonshq.com/pyramid/dev/#api-documentation">API Documentation</a>\n\t\t\t\t\t\t</li>\n\t\t\t\t\t\t')
        attrs = _attrs_4360314960
        _write(u'<li>\n\t\t\t\t\t\t\t')
        attrs = _attrs_4360315152
        _write(u'<a href="http://docs.pylonshq.com/pyramid/dev/#tutorials">Tutorials</a>\n\t\t\t\t\t\t</li>\n\t\t\t\t\t\t')
        attrs = _attrs_4360315088
        _write(u'<li>\n\t\t\t\t\t\t\t')
        attrs = _attrs_4360315408
        _write(u'<a href="http://docs.pylonshq.com/pyramid/dev/#change-history">Change History</a>\n\t\t\t\t\t\t</li>\n\t\t\t\t\t\t')
        attrs = _attrs_4360315344
        _write(u'<li>\n\t\t\t\t\t\t\t')
        attrs = _attrs_4360315536
        _write(u'<a href="http://docs.pylonshq.com/pyramid/dev/#sample-applications">Sample Applications</a>\n\t\t\t\t\t\t</li>\n\t\t\t\t\t\t')
        attrs = _attrs_4360315472
        _write(u'<li>\n\t\t\t\t\t\t\t')
        attrs = _attrs_4360315856
        _write(u'<a href="http://docs.pylonshq.com/pyramid/dev/#support-and-development">Support and Development</a>\n\t\t\t\t\t\t</li>\n\t\t\t\t\t\t')
        attrs = _attrs_4360315792
        _write(u'<li>\n\t\t\t\t\t\t\t')
        attrs = _attrs_4360316112
        _write(u'<a href="irc://irc.freenode.net#pyramid">IRC Channel</a>\n\t\t\t\t\t\t</li>\n\t\t  \t\t\t</ul>\n\t\t\t\t</div>\n\t\t\t</div>\n\t\t</div>\n\t</div>\n\t')
        attrs = _attrs_4360318608
        _write(u'<div id="footer">\n\t\t')
        attrs = _attrs_4360316624
        _write(u'<div class="footer">\xa9 Copyright 2008-2011, Agendaless Consulting.</div>\n\t</div>\n</body>\n</html>')
        return _out.getvalue()
    return render

__filename__ = '/Users/gawel/py/formalchemy_project/pyramid_formalchemy/pyramidapp/pyramidapp/templates/mytemplate.pt'
registry[(None, True, '1488bdb950901f8f258549439ef6661a49aae984')] = bind()

########NEW FILE########
__FILENAME__ = tests
import unittest2 as unittest
from pyramid.config import Configurator
from pyramid import testing
from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import sessionmaker

from zope.sqlalchemy import ZopeTransactionExtension

import os
import shutil
import tempfile
from webtest import TestApp
from pyramidapp import main
from pyramidapp import models
from paste.deploy import loadapp

dirname = os.path.abspath(__file__)
dirname = os.path.dirname(dirname)
dirname = os.path.dirname(dirname)

class Test_1_UI(unittest.TestCase):

    config = os.path.join(dirname, 'test.ini')
    extra_environ = {}

    def setUp(self):
        app = loadapp('config:%s' % self.config, global_conf={'db':'sqlite://'})
        self.app = TestApp(app, extra_environ=self.extra_environ)
        self.config = Configurator(autocommit=True)
        self.config.begin()

    def test_index(self):
        resp = self.app.get('/')

    def test_1_crud(self):
        # index
        resp = self.app.get('/admin')
        self.assertEqual(resp.status_int, 302)
        assert '/admin/' in resp.location, resp

        resp = self.app.get('/admin/')
        resp.mustcontain('/admin/Foo')
        resp = resp.click('Foo')

        ## Simple model

        # add page
        resp.mustcontain('/admin/Foo/new')
        resp = resp.click(linkid='new')
        resp.mustcontain('/admin/Foo"')
        form = resp.forms[0]
        form['Foo--bar'] = 'value'
        resp = form.submit()
        assert resp.headers['location'] == 'http://localhost/admin/Foo', resp

        # model index
        resp = resp.follow()
        resp.mustcontain('<td>value</td>')
        form = resp.forms[0]
        resp = form.submit()

        # edit page
        form = resp.forms[0]
        form['Foo-1-bar'] = 'new value'
        #form['_method'] = 'PUT'
        resp = form.submit()
        resp = resp.follow()

        # model index
        resp.mustcontain('<td>new value</td>')

        # delete
        resp = self.app.get('/admin/Foo')
        resp.mustcontain('<td>new value</td>')
        resp = resp.forms[1].submit()
        resp = resp.follow()

        assert 'new value' not in resp, resp

    def test_2_model(self):
        # index
        resp = self.app.get('/foo')
        self.assertEqual(resp.status_int, 302)
        assert '/' in resp.location, resp

        ## Simple model
        resp = self.app.get('/foo/')

        # add page
        resp.mustcontain('/foo/new')
        resp = resp.click(linkid='new')
        resp.mustcontain('/foo')
        form = resp.forms[0]
        form['Foo--bar'] = 'value'
        resp = form.submit()
        assert resp.headers['location'] == 'http://localhost/foo/', resp

        # model index
        resp = resp.follow()
        resp.mustcontain('<td>value</td>')
        form = resp.forms[0]
        resp = form.submit()

        # edit page
        form = resp.forms[0]
        form['Foo-1-bar'] = 'new value'
        #form['_method'] = 'PUT'
        resp = form.submit()
        resp = resp.follow()

        # model index
        resp.mustcontain('<td>new value</td>')

        # delete
        resp = self.app.get('/foo/')
        resp.mustcontain('<td>new value</td>')
        resp = resp.forms[1].submit()
        resp = resp.follow()

        assert 'new value' not in resp, resp



    def test_3_json(self):
        # index
        response = self.app.get('/admin/json')
        response.mustcontain('{"models": {', '"Foo": "http://localhost/admin/Foo/json"')

        ## Simple model

        # add page
        response = self.app.post('/admin/Foo/json',
                                    {'bar': 'value'})

        data = response.json
        id = data['absolute_url'].split('/')[-1]

        response.mustcontain('"bar": "value"')


        # get data
        response = self.app.get(str(data['absolute_url']))
        response.mustcontain('"bar": "value"')

        # edit page
        response = self.app.post(str(data['absolute_url']), {'bar': 'new value'})
        response.mustcontain('"bar": "new value"')

        # delete
        response = self.app.delete(str(data['absolute_url']))
        self.assert_(response.json['id'] > 0)

    def test_4_json_prefix(self):
        # index
        response = self.app.get('/admin/json')
        response.mustcontain('{"models": {', '"Foo": "http://localhost/admin/Foo/json"')

        ## Simple model

        # add page
        response = self.app.post('/admin/Foo/json?with_prefix=True',
                                 {'Foo--bar': 'value', 'with_prefix': 'true'})

        data = response.json
        id = data['absolute_url'].split('/')[-1]

        response.mustcontain('"Foo-%s-bar": "value"' % id)


        # get data
        response = self.app.get(str(data['absolute_url'])+'?with_prefix=True')
        response.mustcontain('"Foo-%s-bar": "value"' % id)

        # edit page
        response = self.app.post(str(data['absolute_url']+'?with_prefix=True'), {'Foo-%s-bar' % id: 'new value', 'with_prefix': 'true'})
        response.mustcontain('"Foo-%s-bar": "new value"' % id)

        # delete
        response = self.app.delete(str(data['absolute_url']+'?with_prefix=True'))
        self.assert_(response.json['id'] > 0)

    def test_5_xhr(self):
        # add page
        resp = self.app.post('/admin/Foo/', {'Foo--bar':'value'}, extra_environ={'HTTP_X_REQUESTED_WITH':'XMLHttpRequest'})
        self.assertEqual(resp.content_type, 'text/plain')

        resp = self.app.post('/admin/Foo/1', {'Foo-1-bar':'value'}, extra_environ={'HTTP_X_REQUESTED_WITH':'XMLHttpRequest'})
        self.assertEqual(resp.content_type, 'text/plain')

        # assume all are deleted
        response = self.app.delete('/admin/Foo/1', extra_environ={'HTTP_X_REQUESTED_WITH':'XMLHttpRequest'})
        self.assertEqual(resp.content_type, 'text/plain')


class Test_2_Security(Test_1_UI):

    config = os.path.join(dirname, 'security.ini')
    extra_environ = {'REMOTE_USER': 'admin'}

    def test_model_security(self):
        resp = self.app.get('/admin/', extra_environ={'REMOTE_USER': 'editor'})
        self.assertEqual(resp.status_int, 200)

        resp = self.app.get('/admin/Foo', extra_environ={'REMOTE_USER': 'editor'})
        self.assertEqual(resp.status_int, 200)

        resp = self.app.get('/admin/Foo/new', status=403, extra_environ={'REMOTE_USER': 'editor'})
        self.assertEqual(resp.status_int, 403)

        resp = self.app.get('/admin/Bar', status=403, extra_environ={'REMOTE_USER': 'editor'})
        self.assertEqual(resp.status_int, 403)

        resp = self.app.get('/admin/Bar', extra_environ={'REMOTE_USER': 'bar_manager'})
        self.assertEqual(resp.status_int, 200)

        resp = self.app.post('/admin/Bar', {'Bar--foo':'bar'}, extra_environ={'REMOTE_USER': 'bar_manager'})
        resp = self.app.get('/admin/Bar/1/edit', extra_environ={'REMOTE_USER': 'admin'})
        self.assertEqual(resp.status_int, 200)
        resp.mustcontain('Delete')
        resp = self.app.get('/admin/Bar/1/edit', extra_environ={'REMOTE_USER': 'bar_manager'})
        self.assertEqual(resp.status_int, 200)
        assert 'Delete' not in resp.body, resp.body

    def test_2_model(self):
        pass



class Test_3_JQuery(Test_1_UI):

    config = os.path.join(dirname, 'jquery.ini')

    def test_1_crud(self):
        # index
        resp = self.app.get('/admin/')
        resp.mustcontain('/admin/Foo')
        resp = resp.click('Foo')

        ## Simple model

        # add page
        resp.mustcontain('/admin/Foo/new')
        resp = resp.click(linkid='new')
        resp.mustcontain('/admin/Foo"')
        form = resp.forms[0]
        form['Foo--bar'] = 'value'
        resp = form.submit()
        assert resp.headers['location'] == 'http://localhost/admin/Foo', resp

        # model index
        resp = resp.follow()

        # edit page
        resp = self.app.get('/admin/Foo/1/edit')
        form = resp.forms[0]
        form['Foo-1-bar'] = 'new value'
        #form['_method'] = 'PUT'
        resp = form.submit()
        resp = resp.follow()

        # model index
        resp.mustcontain('<td>new value</td>')

        # delete
        resp = self.app.get('/admin/Foo')
        resp.mustcontain('jQuery')

    def test_2_model(self):
        pass

########NEW FILE########
__FILENAME__ = views
from pyramidapp.models import DBSession
from pyramidapp.models import MyModel
from pyramidapp import forms

def my_view(request):
    dbsession = DBSession()
    root = dbsession.query(MyModel).filter(MyModel.name==u'root').first()
    fs = forms.GridMyModel.bind(instances=[root]).render()
    fs = forms.GridMyModelReadOnly.bind(instances=[root]).render()
    return {'root':root, 'project':'pyramidapp'}

########NEW FILE########
__FILENAME__ = actions
# -*- coding: utf-8 -*-
from chameleon.zpt.template import PageTemplate
from pyramid.util import DottedNameResolver
from pyramid.security import has_permission
from pyramid_formalchemy.i18n import TranslationString
from pyramid_formalchemy.i18n import get_localizer
from pyramid_formalchemy.i18n import _
import functools

__doc__ = """
pyramid_formalchemy provide a way to use some ``actions`` in your template.
Action are basically links or input button.

By default there is only one category ``buttons`` which are the forms buttons
but you can add some categories like this::

    >>> from pyramid_formalchemy.views import ModelView
    >>> from pyramid_formalchemy import actions

    >>> class MyView(ModelView):
    ...     # keep default action categorie and add the custom_actions categorie
    ...     actions_categories = ('buttons', 'custom_actions')
    ...     # update the default actions for all models
    ...     defaults_actions = actions.defaults_actions.copy()
    ...     defaults_actions.update(edit_custom_actions=Actions())

Where ``myactions`` is an :class:`~pyramid_formalchemy.actions.Actions` instance

You can also customize the actions per Model::


    >>> from sqlalchemy import Column, Integer
    >>> from sqlalchemy.ext.declarative import declarative_base
    >>> Base = declarative_base()
    >>> class MyArticle(Base):
    ...     __tablename__ = 'myarticles'
    ...     edit_buttons = Actions()
    ...     id = Column(Integer, primary_key=True)

The available actions are:

- listing

- new

- edit

But you can add your own::

    >>> from pyramid_formalchemy.views import ModelView
    >>> from pyramid_formalchemy import actions
    >>> class MyView(ModelView):
    ...     actions.action()
    ...     def extra(self):
    ...         # do stuff
    ...         return self.render(**kw)

Then pyramid_formalchemy will try to load some ``extra_buttons`` actions.
"""

def action(name=None):
    """A decorator use to add some actions to the request.
    """
    def wrapper(func):
        action = name or func.__name__
        @functools.wraps(func)
        def wrapped(self, *args, **kwargs):
            request = self.request
            if request.format in ('html', 'xhr') and request.model_class is not None:
                for key in self.actions_categories:
                    attr = '%s_%s' % (action, key)
                    objects = getattr(request.model_class, attr, None)
                    if objects is None:
                        objects = self.defaults_actions.get(attr, Actions())
                    request.actions[key] = objects
                request.action = func.__name__
            return func(self, *args, **kwargs)
        return wrapped
    return wrapper


class Action(object):
    """A model action is used to add some action in model views. The content
    and alt parameters should be a :py:class:`pyramid.i18n.TranslationString`::

        >>> from webob import Request
        >>> request = Request.blank('/')

        >>> class MyAction(Action):
        ...     body = u'<a tal:attributes="%(attributes)s">${content}</a>'

        >>> action = MyAction('myaction', content=_('Click here'), 
        ...                   attrs={'href': repr('#'), 'onclick': repr('$.click()')})
        >>> action.render(request)
        u'<a href="#" id="myaction" onclick="$.click()">Click here</a>'

    """

    def __init__(self, id, content="", alt="", permission=None, attrs=None, **rcontext):
        self.id = id
        self.attrs = attrs or {}
        self.permission = permission
        self.rcontext = rcontext
        if 'id' not in self.attrs:
            self.attrs['id'] = repr(id)
        self.update()
        attributes = u';'.join([u'%s %s' % v for v in self.attrs.items()])
        rcontext.update(attrs=self.attrs, attributes=attributes, id=id)
        body = self.body % self.rcontext
        rcontext.update(content=content, alt=alt)
        self.template = PageTemplate(body)

    def update(self):
        pass

    def render(self, request):
        rcontext = {'action': self, 'request': request}
        rcontext.update(self.rcontext)
        localizer = get_localizer(request)
        mapping = getattr(request, 'action_mapping', {})
        if not mapping:
            for k in ('model_name', 'model_label', 'model_id'):
                mapping[k] = localizer.translate(getattr(request, k, ''))
            request.action_mapping = mapping
        for k in ('content', 'alt'):
            v = rcontext[k]
            if isinstance(v, TranslationString):
                v = TranslationString(v, domain=v.domain, mapping=request.action_mapping)
                rcontext[k] = localizer.translate(v)
        return self.template.render(**rcontext)

    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__, self.id)

class Link(Action):
    """
    An action rendered as a link::

        >>> from webob import Request
        >>> request = Request.blank('/')
        >>> action = Link('myaction',
        ...               attrs={'href': 'request.application_url'},
        ...               content=_('Click here'))
        >>> action.render(request)
        u'<a href="http://localhost" id="myaction">Click here</a>'

    """
    body = u'<a tal:attributes="%(attributes)s">${content}</a>'

class ListItem(Action):
    """
    An action rendered as a link contained by a list item::

        >>> from webob import Request
        >>> request = Request.blank('/')
        >>> action = ListItem('myaction',
        ...               attrs={'href': 'request.application_url'},
        ...               content=_('Click here'))
        >>> action.render(request)
        u'<li><a href="http://localhost" id="myaction">Click here</a></li>'

    """
    body = u'<li><a tal:attributes="%(attributes)s">${content}</a></li>'


class Input(Action):
    """An action rendered as an input::

        >>> from webob import Request
        >>> request = Request.blank('/')
        >>> action = Input('myaction',
        ...                content=_('Click here'))

    Rendering::

        >>> action.render(request)
        u'<input value="Click here" type="submit" id="myaction" />'

    """
    body = u'<input tal:attributes="%(attributes)s" value="${content}"/>'

    def update(self):
        if 'type' not in self.attrs:
            self.attrs['type'] = repr('submit')

class Option(Action):
    """An action rendered as a select option::

        >>> from webob import Request
        >>> request = Request.blank('/')
        >>> action = Option('myaction',
        ...                  value='request.application_url',
        ...                  content=_('Click here'))

    Rendering::

        >>> action.render(request)
        u'<option id="myaction" value="http://localhost">Click here</option>'

    """

    body = u'<option tal:attributes="%(attributes)s">${content}</option>'

    def update(self):
        if 'value' not in self.attrs:
            self.attrs['value'] = self.rcontext.get('value', None)

class UIButton(Action):
    """An action rendered as an jquery.ui aware link::

        >>> from webob import Request
        >>> request = Request.blank('/')
        >>> action = UIButton('myaction', icon='ui-icon-trash',
        ...                 content=_("Click here"))
        >>> print action.render(request)
        <a class="ui-widget-header ui-widget-link ui-widget-button ui-corner-all " id="myaction">
          <span class="ui-icon ui-icon-trash"></span>
          Click here
        </a>
        
    You can use javascript::

        >>> action = UIButton('myaction', icon='ui-icon-trash',
        ...                 content=_("Click here"), attrs={'onclick':'$(#link).click();'})
        >>> print action.render(request)
        <a class="ui-widget-header ui-widget-link ui-widget-button ui-corner-all " href="#" id="myaction" onclick="$(#link).click();">
          <span class="ui-icon ui-icon-trash"></span>
          Click here
        </a>
        
    """
    body = '''
<a class="ui-widget-header ui-widget-link ui-widget-button ui-corner-all ${state}"
   tal:attributes="%(attributes)s">
  <span class="ui-icon ${icon}"></span>
  ${content}
</a>'''
    def update(self):
        if 'state' not in self.rcontext:
            self.rcontext['state'] = ''
        if 'onclick' in self.attrs:
            self.rcontext['onclick'] = self.attrs.pop('onclick')
            self.attrs['onclick'] = 'onclick'
            if 'href' not in self.attrs:
                self.attrs['href'] = repr('#')

class Actions(list):
    """A action list. Can contain :class:`pyramid_formalchemy.actions.Action` or a dotted name::

        >>> actions = Actions('pyramid_formalchemy.actions.delete',
        ...                   Link('link1', content=_('A link'), attrs={'href':'request.application_url'}))
        >>> actions
        <Actions [<UIButton delete>, <Link link1>]>

    You must use a request to render them::

        >>> from webob import Request
        >>> request = Request.blank('/')
        >>> print actions.render(request) #doctest: +ELLIPSIS +NORMALIZE_WHITESPACE
        <a class="ui-widget-header ...">
          <span class="ui-icon ui-icon-trash"></span>
          Delete
        </a>
        <a href="http://localhost" id="link1">A link</a>

    You can add actions::

        >>> new_actions = Actions('pyramid_formalchemy.actions.new') + actions
        >>> new_actions
        <Actions [<UIButton new>, <UIButton delete>, <Link link1>]>
        
    """
    tag = u''
    def __init__(self, *args, **kwargs):
        self.sep = kwargs.get('sep', u'\n')
        res = DottedNameResolver('pyramid_formalchemy.actions')
        list.__init__(self, [res.maybe_resolve(a) for a in args])

    def render(self, request, **kwargs):
        allowed_permissions = []
        for a in self:
            if a.permission is None or has_permission(a.permission, request.context, request):
                allowed_permissions.append(a)
        return self.sep.join([a.render(request, **kwargs) for a in allowed_permissions])

    def __add__(self, other):
        actions = list(self)+list(other)
        actions = self.__class__(*actions)
        actions.sep = self.sep
        return actions

    def __nonzero__(self):
        return bool(len(self))

    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__, list.__repr__(self))

class RequestActions(dict):
    """An action container used to store action in requests.
    Return an empty Actions instance if actions are not found"""

    def __getattr__(self, attr):
        actions = self.get(attr, Actions())
        if actions:
            return actions.render
        return None

class Languages(Actions):
    """Languages actions::

        >>> langs = Languages('fr', 'en')
        >>> langs
        <Languages [<ListItem lang_fr>, <ListItem lang_en>]>

    It take care about the active language::

        >>> from webob import Request
        >>> request = Request.blank('/')
        >>> request.cookies['_LOCALE_'] = 'fr'
        >>> request.route_url = lambda name, _query: 'http://localhost/set_language?_LOCALE_=%(_LOCALE_)s' % _query
        >>> print langs.render(request) #doctest: +ELLIPSIS +NORMALIZE_WHITESPACE
        <li><a href="http://localhost/set_language?_LOCALE_=fr" class="lang_fr lang_active" id="lang_fr">French</a></li>
        <li><a href="http://localhost/set_language?_LOCALE_=en" class="lang_en " id="lang_en">English</a></li>
        
    """
    translations = {
            'fr': _('French'),
            'en': _('English'),
            'pt_BR': _('Brazilian'),
            }

    def __init__(self, *args, **kwargs):
        Actions.__init__(self)
        klass=kwargs.get('class_', ListItem)
        for l in args:
            self.append(
                klass(id='lang_%s' % l,
                      content=self.translations.get(l, _(l)), attrs={
                        'class':"string:lang_%s ${request.cookies.get('_LOCALE_') == '%s' and 'lang_active' or ''}" % (l, l),
                        'href':"request.route_url('set_language', _query={'_LOCALE_': '%s'})" % l
                      }
                  ))


class Themes(Actions):
    themes = (
        'black_tie',
        'blitzer',
        'cupertino',
        'dark_hive',
        'dot_luv',
        'eggplant',
        'excite_bike',
        'flick',
        'hot_sneaks',
        'humanity',
        'le_frog',
        'mint_choc',
        'overcast',
        'pepper_grinder',
        'redmond',
        'smoothness',
        'south_street',
        'start',
        'sunny',
        'swanky_purse',
        'trontastic',
        'ui_darkness',
        'ui_lightness',
        'vader',
      )

    def __init__(self, *args, **kwargs):
        Actions.__init__(self)
        klass=kwargs.get('class_', Option)
        if len(args) == 1 and args[0] == '*':
            args = self.themes
        for theme in args:
            label = theme.replace('_', ' ')
            self.append(
                klass(id='theme_%s' % theme,
                      content=_(label), attrs={
                        'selected':"string:${request.cookies.get('_THEME_') == '%s' and 'selected' or None}" % theme,
                        'value':"request.route_url('set_theme', _query={'_THEME_': '%s'})" % theme
                      }
                  ))


new = UIButton(
        id='new',
        content=_('New ${model_label}'),
        permission='new',
        icon='ui-icon-circle-plus',
        attrs=dict(href="request.fa_url(request.model_name, 'new')"),
        )


save = UIButton(
        id='save',
        content=_('Save'),
        permission='edit',
        icon='ui-icon-check',
        attrs=dict(onclick="jQuery(this).parents('form').submit();"),
        )

save_and_add_another = UIButton(
        id='save_and_add_another',
        content=_('Save and add another'),
        permission='edit',
        icon='ui-icon-check',
        attrs=dict(onclick=("var f = jQuery(this).parents('form');"
                            "jQuery('#next', f).val(window.location.href);"
                            "f.submit();")),
        )

edit = UIButton(
        id='edit',
        content=_('Edit'),
        permission='edit',
        icon='ui-icon-check',
        attrs=dict(href="request.fa_url(request.model_name, request.model_id, 'edit')"),
        )

back = UIButton(
        id='back',
        content=_('Back'),
        icon='ui-icon-circle-arrow-w',
        attrs=dict(href="request.fa_url(request.model_name)"),
        )

delete = UIButton(
        id='delete',
        content=_('Delete'),
        permission='delete',
        state='ui-state-error',
        icon='ui-icon-trash',
        attrs=dict(onclick=("var f = jQuery(this).parents('form');"
                      "f.attr('action', window.location.href.replace('/edit', '/delete'));"
                      "f.submit();")),
        )

cancel = UIButton(
        id='cancel',
        content=_('Cancel'),
        permission='view',
        icon='ui-icon-circle-arrow-w',
        attrs=dict(href="request.fa_url(request.model_name)"),
        )

defaults_actions = RequestActions(
    listing_buttons=Actions(new),
    new_buttons=Actions(save, save_and_add_another, cancel),
    show_buttons=Actions(edit, back),
    edit_buttons=Actions(save, delete, cancel),
)

########NEW FILE########
__FILENAME__ = events
import zope.component
__doc__ = """
Event subscription
==================

``pyramid_formalchemy`` provides four events: ``IBeforeValidateEvent``,
``IAfterSyncEvent``, ``IBeforeDeleteEvent`` and ``IBeforeRenderEvent``.
There are also two more specific render evnts: ``IBeforeShowRenderEvent``
and ``IBeforeEditRenderEvent``. You can use ``pyramid_formalchemy.events.subscriber``
decorator to subscribe:

.. literalinclude:: ../../pyramidapp/pyramidapp/events.py

"""


class IBeforeValidateEvent(zope.component.interfaces.IObjectEvent):
    """A model will be validated"""


class IAfterSyncEvent(zope.component.interfaces.IObjectEvent):
    """A model was synced with DB"""


class IBeforeDeleteEvent(zope.component.interfaces.IObjectEvent):
    """A model will be deleted"""


class IBeforeRenderEvent(zope.component.interfaces.IObjectEvent):
    """A model will rendered"""


class IBeforeListingRenderEvent(IBeforeRenderEvent):
    """Listing will be rendered"""


class IBeforeShowRenderEvent(IBeforeRenderEvent):
    """Show will be rendered"""


class IBeforeEditRenderEvent(IBeforeRenderEvent):
    """Edit will be rendered"""


class BeforeValidateEvent(zope.component.interfaces.ObjectEvent):
    """A model will be validated"""
    zope.interface.implements(IBeforeValidateEvent)

    def __init__(self, object, fs, request):
        self.object = object
        self.fs = fs
        self.request = request


class AfterSyncEvent(zope.component.interfaces.ObjectEvent):
    """A model was synced with DB"""
    zope.interface.implements(IAfterSyncEvent)

    def __init__(self, object, fs, request):
        self.object = object
        self.fs = fs
        self.request = request

class BeforeDeleteEvent(zope.component.interfaces.ObjectEvent):
    """A model will be deleted"""
    zope.interface.implements(IBeforeDeleteEvent)

    def __init__(self, object, request):
        self.object = object
        self.request = request


class BeforeRenderEvent(zope.component.interfaces.ObjectEvent):
    """A model will rendered"""
    zope.interface.implements(IBeforeRenderEvent)

    def __init__(self, object, request, **kwargs):
        self.object = object
        self.request = request
        self.kwargs = kwargs

class subscriber(object):
    """event subscriber decorator"""

    def __init__(self, ifaces):
        self.ifaces = ifaces

    def __call__(self, func):
        zope.component.provideHandler(func, self.ifaces)

########NEW FILE########
__FILENAME__ = i18n
# -*- coding: utf-8 -*-
from pyramid.i18n import TranslationStringFactory
from pyramid.i18n import TranslationString
from pyramid.i18n import get_localizer

_ = TranslationStringFactory('pyramid_formalchemy')

class I18NModel(object):

    def __init__(self, context, request):
        self.context = context
        self.request = request

    @property
    def label(self):
        return getattr(self.context, '__label__', self.context.__name__)

    @property
    def plural(self):
        value = getattr(self.context, '__plural__', None)
        if value:
            return value
        else:
            return self.label

    def __getattr__(self, attr):
        return getattr(self.context, attr)


########NEW FILE########
__FILENAME__ = paster
try: # pyramid 1.0.X
    # "pyramid.paster.paste_script..." doesn't exist past 1.0.X
    from pyramid.paster import paste_script_template_renderer
    from pyramid.paster import PyramidTemplate
except ImportError:
    try:  # pyramid 1.1.X, 1.2.X
        # trying to import "paste_script_template_renderer" fails on 1.3.X
        from pyramid.scaffolds import paste_script_template_renderer
        from pyramid.scaffolds import PyramidTemplate
    except ImportError: # pyramid >=1.3a2
        paste_script_template_renderer = None
        from pyramid.scaffolds import PyramidTemplate


class PyramidFormAlchemyTemplate(PyramidTemplate):
    _template_dir = ('pyramid_formalchemy', 'paster_templates/pyramid_fa')
    summary = "Pyramid application template to extend other templates with "
    "formalchemy"
    template_renderer = staticmethod(paste_script_template_renderer)

########NEW FILE########
__FILENAME__ = resources
# -*- coding: utf-8 -*-
from pyramid.exceptions import NotFound
from pyramid_formalchemy import actions
from sqlalchemy import exc as sqlalchemy_exceptions
import logging

log = logging.getLogger(__name__)

class Base(object):
    """Base class used for all traversed class.
    Allow to access to some useful attributes via request::

    - model_class
    - model_name
    - model_instance
    - model_id
    - fa_url
    """

    def __init__(self, request, name):
        self.__name__ = name
        self.__parent__ = None
        self.request = request
        if hasattr(self, '__fa_route_name__'):
            request.session_factory = self.__session_factory__
            request.query_factory = self.__query_factory__
            request.route_name = self.__fa_route_name__
            request.models = self.__models__
            request.forms = self.__forms__
            request.fa_url = self.fa_url
            request.model_instance = None
            request.model_class = None
            request.model_name = None
            request.model_id = None
            request.relation = None
            request.format = 'html'
            if self.__model_class__:
                request.model_class = self.__model_class__
                request.model_name = self.__model_class__.__name__
            request.actions = actions.RequestActions()
            langs = request.registry.settings.get('available_languages', '')
            if langs:
                if isinstance(langs, basestring):
                    langs = langs.split()
                request.actions['languages'] = actions.Languages(*langs)
            themes = request.registry.settings.get('available_themes', '')
            if themes:
                if isinstance(themes, basestring):
                    themes = themes.split()
                request.actions['themes'] = actions.Themes(*themes)

    def get_model(self):
        request = self.request
        if request.model_class:
            return request.model_class
        model_name = request.model_name
        model_class = None
        if isinstance(request.models, list):
            for model in request.models:
                if model.__name__ == model_name:
                    model_class = model
                    break
        elif hasattr(request.models, model_name):
            model_class = getattr(request.models, model_name)
        if model_class is None:
            raise NotFound(request.path)
        request.model_class = model_class
        return model_class

    def get_instance(self):
        model = self.get_model()
        session = self.request.session_factory()
        try:
            return session.query(model).get(self.request.model_id)
        except sqlalchemy_exceptions.InvalidRequestError:
            # pyramid 1.4 compat
            return session.query(model.context).get(self.request.model_id)

    def _fa_url(self, *args, **kwargs):
        matchdict = self.request.matchdict.copy()
        if 'traverse' in matchdict:
            del matchdict['traverse']
        if kwargs:
            matchdict['_query'] = kwargs
        return self.request.route_url(self.__fa_route_name__,
                                      traverse=tuple([str(a) for a in args]),
                                      **matchdict)



class Models(Base):
    """Root of the CRUD interface"""

    def __init__(self, request):
        Base.__init__(self, request, None)

    def fa_url(self, *args, **kwargs):
        return self._fa_url(*args, **kwargs)

    def __getitem__(self, item):
        if item in ('json', 'xhr'):
            self.request.format = item
            return self

        self.request.model_name = item
        model_class = self.get_model()
        mixin_name = '%sCustom%s_%s__%s' % (model_class.__name__, ModelListing.__name__,
                                           self.request.route_name, self.request.method)
        mixin = type(mixin_name, (ModelListing, ), {})
        factory = self.request.registry.pyramid_formalchemy_views.get(mixin.__name__, mixin)
        model = factory(self.request, item)
        model.__parent__ = self
        if hasattr(model, '__acl__'):
            # propagate permissions to parent
            self.__acl__ = model.__acl__
        return model

class ModelListing(Base):
    """Context used for model classes"""

    def __init__(self, request, name=None):
        Base.__init__(self, request, name)
        if name is None:
            # request.model_class and request.model_name are already set
            model = request.model_class
        else:
            request.model_name = name
            model = self.get_model()
        if hasattr(model, '__acl__'):
            # get permissions from SA class
            self.__acl__ = model.__acl__

    def fa_url(self, *args, **kwargs):
        return self._fa_url(*args[1:], **kwargs)

    def __getitem__(self, item):
        if item in ('json', 'xhr'):
            self.request.format = item
            return self

        name = self.request.path.split('/')[-1] #view name
        if name == item:
            name = ''

        mixin_name = '%sCustom%s_%s_%s_%s' % (self.request.model_class.__name__, Model.__name__,
                                              self.request.route_name, name, self.request.method)
        mixin = type(str(mixin_name), (Model, ), {})
        factory = self.request.registry.pyramid_formalchemy_views.get(mixin.__name__, mixin)
        try:
            model = factory(self.request, item)
        except NotFound:
            raise KeyError()
        model.__parent__ = self
        return model

class Model(Base):
    """Context used for model instances"""

    def fa_url(self, *args, **kwargs):
        return self._fa_url(*args[2:], **kwargs)

    def __init__(self, request, name):
        Base.__init__(self, request, name)
        query = request.session_factory.query(request.model_class)
        try:
            request.model_instance = request.query_factory(request, query, id=name)
        except sqlalchemy_exceptions.SQLAlchemyError, exc:
            log.exception(exc)
            request.session_factory().rollback()
            raise NotFound(request.path)

        if request.model_instance is None:
            raise NotFound(request.path)
        request.model_id = name


########NEW FILE########
__FILENAME__ = edit.pt
registry = dict(version=0)
def bind():
    from cPickle import loads as _loads
    _lookup_attr = _loads('cchameleon.core.codegen\nlookup_attr\np1\n.')
    _init_scope = _loads('cchameleon.core.utils\necontext\np1\n.')
    _attrs_4356242384 = _loads('(dp1\n.')
    _attrs_4356371600 = _loads('(dp1\n.')
    _init_stream = _loads('cchameleon.core.generation\ninitialize_stream\np1\n.')
    _attrs_4356243152 = _loads('(dp1\nVclass\np2\nVfa_field\np3\ns.')
    _init_default = _loads('cchameleon.core.generation\ninitialize_default\np1\n.')
    _attrs_4356370704 = _loads('(dp1\nVaction\np2\nV\nsVmethod\np3\nVPOST\np4\nsVenctype\np5\nVmultipart/form-data\np6\ns.')
    _attrs_4356239504 = _loads('(dp1\nVname\np2\nV_method\np3\nsVtype\np4\nVhidden\np5\nsVvalue\np6\nVPUT\np7\ns.')
    _init_tal = _loads('cchameleon.core.generation\ninitialize_tal\np1\n.')
    def render(econtext, rcontext=None):
        macros = econtext.get('macros')
        _translate = econtext.get('_translate')
        _slots = econtext.get('_slots')
        target_language = econtext.get('target_language')
        u'_init_stream()'
        (_out, _write, ) = _init_stream()
        u'_init_tal()'
        (_attributes, repeat, ) = _init_tal()
        u'_init_default()'
        _default = _init_default()
        u'None'
        default = None
        u'None'
        _domain = None
        u"main.macros['master']"
        _metal = _lookup_attr(econtext['main'], 'macros')['master']
        def _callback_main(econtext, _repeat, _out=_out, _write=_write, _domain=_domain, **_ignored):
            if _repeat:
                repeat.update(_repeat)
            attrs = _attrs_4356371600
            _write(u'<div>\n      ')
            attrs = _attrs_4356370704
            u"''"
            _write(u'<form action="" method="POST" enctype="multipart/form-data">\n        ')
            _default.value = default = ''
            u'fs.render()'
            _content = _lookup_attr(econtext['fs'], 'render')()
            attrs = _attrs_4356242384
            u'_content'
            _write(u'<div>')
            _tmp1 = _content
            _tmp = _tmp1
            if (_tmp.__class__ not in (str, unicode, int, float, )):
                try:
                    _tmp = _tmp.__html__
                except:
                    _tmp = _translate(_tmp, domain=_domain, mapping=None, target_language=target_language, default=None)
                else:
                    _tmp = _tmp()
                    _write(_tmp)
                    _tmp = None
            if (_tmp is not None):
                if not isinstance(_tmp, unicode):
                    _tmp = str(_tmp)
                _write(_tmp)
            _write(u'</div>\n        ')
            attrs = _attrs_4356239504
            u"u'\\n        '"
            _write(u'<input type="hidden" name="_method" value="PUT" />\n        ')
            _default.value = default = u'\n        '
            u'actions.buttons(request)'
            _content = _lookup_attr(econtext['actions'], 'buttons')(econtext['request'])
            attrs = _attrs_4356243152
            u'_content'
            _write(u'<p class="fa_field">')
            _tmp1 = _content
            _tmp = _tmp1
            if (_tmp.__class__ not in (str, unicode, int, float, )):
                try:
                    _tmp = _tmp.__html__
                except:
                    _tmp = _translate(_tmp, domain=_domain, mapping=None, target_language=target_language, default=None)
                else:
                    _tmp = _tmp()
                    _write(_tmp)
                    _tmp = None
            if (_tmp is not None):
                if not isinstance(_tmp, unicode):
                    _tmp = str(_tmp)
                _write(_tmp)
            _write(u'</p>\n      </form>\n    </div>\n')
        u"{'main': _callback_main}"
        _tmp = {'main': _callback_main, }
        u"main.macros['master']"
        _metal.render(_tmp, _out=_out, _write=_write, _domain=_domain, econtext=econtext)
        return _out.getvalue()
    return render

__filename__ = '/Users/gawel/py/formalchemy_project/pyramid_formalchemy/pyramid_formalchemy/templates/admin/edit.pt'
registry[(None, True, '1488bdb950901f8f258549439ef6661a49aae984')] = bind()

########NEW FILE########
__FILENAME__ = listing.pt
registry = dict(version=0)
def bind():
    from cPickle import loads as _loads
    _lookup_attr = _loads('cchameleon.core.codegen\nlookup_attr\np1\n.')
    _init_scope = _loads('cchameleon.core.utils\necontext\np1\n.')
    _attrs_4353960208 = _loads('(dp1\nVclass\np2\nVlayout-grid\np3\ns.')
    _attrs_4353960144 = _loads('(dp1\nVclass\np2\nVui-pager\np3\ns.')
    _init_stream = _loads('cchameleon.core.generation\ninitialize_stream\np1\n.')
    _attrs_4353960272 = _loads('(dp1\nVclass\np2\nVfa_field\np3\ns.')
    _init_default = _loads('cchameleon.core.generation\ninitialize_default\np1\n.')
    _attrs_4353960016 = _loads('(dp1\n.')
    _init_tal = _loads('cchameleon.core.generation\ninitialize_tal\np1\n.')
    def render(econtext, rcontext=None):
        macros = econtext.get('macros')
        _translate = econtext.get('_translate')
        _slots = econtext.get('_slots')
        target_language = econtext.get('target_language')
        u'_init_stream()'
        (_out, _write, ) = _init_stream()
        u'_init_tal()'
        (_attributes, repeat, ) = _init_tal()
        u'_init_default()'
        _default = _init_default()
        u'None'
        default = None
        u'None'
        _domain = None
        u"main.macros['master']"
        _metal = _lookup_attr(econtext['main'], 'macros')['master']
        def _callback_main(econtext, _repeat, _out=_out, _write=_write, _domain=_domain, **_ignored):
            if _repeat:
                repeat.update(_repeat)
            attrs = _attrs_4353960016
            u"''"
            _write(u'<div>\n      ')
            _default.value = default = ''
            u'pager'
            _content = econtext['pager']
            attrs = _attrs_4353960144
            u'_content'
            _write(u'<div class="ui-pager">')
            _tmp1 = _content
            _tmp = _tmp1
            if (_tmp.__class__ not in (str, unicode, int, float, )):
                try:
                    _tmp = _tmp.__html__
                except:
                    _tmp = _translate(_tmp, domain=_domain, mapping=None, target_language=target_language, default=None)
                else:
                    _tmp = _tmp()
                    _write(_tmp)
                    _tmp = None
            if (_tmp is not None):
                if not isinstance(_tmp, unicode):
                    _tmp = str(_tmp)
                _write(_tmp)
            u"''"
            _write(u'</div>\n      ')
            _default.value = default = ''
            u'fs.render()'
            _content = _lookup_attr(econtext['fs'], 'render')()
            attrs = _attrs_4353960208
            u'_content'
            _write(u'<table class="layout-grid">')
            _tmp1 = _content
            _tmp = _tmp1
            if (_tmp.__class__ not in (str, unicode, int, float, )):
                try:
                    _tmp = _tmp.__html__
                except:
                    _tmp = _translate(_tmp, domain=_domain, mapping=None, target_language=target_language, default=None)
                else:
                    _tmp = _tmp()
                    _write(_tmp)
                    _tmp = None
            if (_tmp is not None):
                if not isinstance(_tmp, unicode):
                    _tmp = str(_tmp)
                _write(_tmp)
            u"u'\\n      '"
            _write(u'</table>\n      ')
            _default.value = default = u'\n      '
            u'actions.buttons(request)'
            _content = _lookup_attr(econtext['actions'], 'buttons')(econtext['request'])
            attrs = _attrs_4353960272
            u'_content'
            _write(u'<p class="fa_field">')
            _tmp1 = _content
            _tmp = _tmp1
            if (_tmp.__class__ not in (str, unicode, int, float, )):
                try:
                    _tmp = _tmp.__html__
                except:
                    _tmp = _translate(_tmp, domain=_domain, mapping=None, target_language=target_language, default=None)
                else:
                    _tmp = _tmp()
                    _write(_tmp)
                    _tmp = None
            if (_tmp is not None):
                if not isinstance(_tmp, unicode):
                    _tmp = str(_tmp)
                _write(_tmp)
            _write(u'</p>\n    </div>\n')
        u"{'main': _callback_main}"
        _tmp = {'main': _callback_main, }
        u"main.macros['master']"
        _metal.render(_tmp, _out=_out, _write=_write, _domain=_domain, econtext=econtext)
        return _out.getvalue()
    return render

__filename__ = '/Users/gawel/py/formalchemy_project/pyramid_formalchemy/pyramid_formalchemy/templates/admin/listing.pt'
registry[(None, True, '1488bdb950901f8f258549439ef6661a49aae984')] = bind()

########NEW FILE########
__FILENAME__ = master.pt
registry = dict(version=0)
def bind():
    from cPickle import loads as _loads
    _attrs_4353373456 = _loads('(dp1\nVrel\np2\nVstylesheet\np3\ns.')
    _lookup_attr = _loads('cchameleon.core.codegen\nlookup_attr\np1\n.')
    _init_scope = _loads('cchameleon.core.utils\necontext\np1\n.')
    _re_amp = _loads("cre\n_compile\np1\n(S'&(?!([A-Za-z]+|#[0-9]+);)'\np2\nI0\ntRp3\n.")
    _attrs_4353342480 = _loads('(dp1\n.')
    _attrs_4345507344 = _loads('(dp1\nVid\np2\nVheader\np3\nsVclass\np4\nVui-widget-header ui-corner-all\np5\ns.')
    _attrs_4353343184 = _loads('(dp1\nVclass\np2\nVbreadcrumb\np3\ns.')
    _attrs_4353342544 = _loads('(dp1\n.')
    _attrs_4353376016 = _loads('(dp1\n.')
    _init_stream = _loads('cchameleon.core.generation\ninitialize_stream\np1\n.')
    _attrs_4353376144 = _loads('(dp1\n.')
    _attrs_4353376208 = _loads('(dp1\n.')
    _attrs_4353372432 = _loads('(dp1\nVsrc\np2\nVhttps://ajax.googleapis.com/ajax/libs/jquery/1.6.1/jquery.min.js\np3\ns.')
    _init_default = _loads('cchameleon.core.generation\ninitialize_default\np1\n.')
    _attrs_4353372560 = _loads('(dp1\nVid\np2\nVcontent\np3\nsVclass\np4\nVui-admin ui-widget\np5\ns.')
    _attrs_4345507600 = _loads('(dp1\n.')
    _attrs_4353342352 = _loads('(dp1\n.')
    _attrs_4353413200 = _loads('(dp1\n.')
    _init_tal = _loads('cchameleon.core.generation\ninitialize_tal\np1\n.')
    def render(econtext, rcontext=None):
        macros = econtext.get('macros')
        _translate = econtext.get('_translate')
        _slots = econtext.get('_slots')
        target_language = econtext.get('target_language')
        u"%(scope)s['%(out)s'], %(scope)s['%(write)s']"
        (_out, _write, ) = (econtext['_out'], econtext['_write'], )
        u'_init_tal()'
        (_attributes, repeat, ) = _init_tal()
        u'_init_default()'
        _default = _init_default()
        u'None'
        default = None
        u'None'
        _domain = None
        attrs = _attrs_4353376016
        _write(u'<html>\n    ')
        attrs = _attrs_4353376144
        u"''"
        _write(u'<head>\n      ')
        _default.value = default = ''
        u"request.model_name or 'root'"
        _content = (_lookup_attr(econtext['request'], 'model_name') or 'root')
        attrs = _attrs_4353413200
        u'_content'
        _write(u'<title>')
        _tmp1 = _content
        _tmp = _tmp1
        if (_tmp.__class__ not in (str, unicode, int, float, )):
            try:
                _tmp = _tmp.__html__
            except:
                _tmp = _translate(_tmp, domain=_domain, mapping=None, target_language=target_language, default=None)
            else:
                _tmp = _tmp()
                _write(_tmp)
                _tmp = None
        if (_tmp is not None):
            if not isinstance(_tmp, unicode):
                _tmp = str(_tmp)
            if ('&' in _tmp):
                if (';' in _tmp):
                    _tmp = _re_amp.sub('&amp;', _tmp)
                else:
                    _tmp = _tmp.replace('&', '&amp;')
            if ('<' in _tmp):
                _tmp = _tmp.replace('<', '&lt;')
            if ('>' in _tmp):
                _tmp = _tmp.replace('>', '&gt;')
            _write(_tmp)
        _write(u'</title>\n      ')
        attrs = _attrs_4353373456
        u"request.static_url('pyramid_formalchemy:static/admin.css')"
        _write(u'<link rel="stylesheet"')
        _tmp1 = _lookup_attr(econtext['request'], 'static_url')('pyramid_formalchemy:static/admin.css')
        if (_tmp1 is _default):
            _tmp1 = None
        if ((_tmp1 is not None) and (_tmp1 is not False)):
            if (_tmp1.__class__ not in (str, unicode, int, float, )):
                _tmp1 = unicode(_translate(_tmp1, domain=_domain, mapping=None, target_language=target_language, default=None))
            else:
                if not isinstance(_tmp1, unicode):
                    _tmp1 = str(_tmp1)
            if ('&' in _tmp1):
                if (';' in _tmp1):
                    _tmp1 = _re_amp.sub('&amp;', _tmp1)
                else:
                    _tmp1 = _tmp1.replace('&', '&amp;')
            if ('<' in _tmp1):
                _tmp1 = _tmp1.replace('<', '&lt;')
            if ('>' in _tmp1):
                _tmp1 = _tmp1.replace('>', '&gt;')
            if ('"' in _tmp1):
                _tmp1 = _tmp1.replace('"', '&quot;')
            _write(((' href="' + _tmp1) + '"'))
        _write(u'></link>\n      ')
        attrs = _attrs_4353372432
        _write(u'<script src="https://ajax.googleapis.com/ajax/libs/jquery/1.6.1/jquery.min.js"></script>\n    </head>\n    ')
        attrs = _attrs_4353376208
        _write(u'<body>\n      ')
        attrs = _attrs_4353372560
        _write(u'<div id="content" class="ui-admin ui-widget">\n        ')
        attrs = _attrs_4345507344
        _write(u'<h1 id="header" class="ui-widget-header ui-corner-all">\n          ')
        attrs = _attrs_4353343184
        u'breadcrumb'
        _write(u'<div class="breadcrumb">\n            ')
        _tmp1 = econtext['breadcrumb']
        item = None
        (_tmp1, _tmp2, ) = repeat.insert('item', _tmp1)
        for item in _tmp1:
            _tmp2 = (_tmp2 - 1)
            u"''"
            _write(u'')
            _default.value = default = ''
            u'item[1]'
            _content = item[1]
            attrs = _attrs_4353342480
            u'item[0]'
            _write(u'<a')
            _tmp3 = item[0]
            if (_tmp3 is _default):
                _tmp3 = None
            if ((_tmp3 is not None) and (_tmp3 is not False)):
                if (_tmp3.__class__ not in (str, unicode, int, float, )):
                    _tmp3 = unicode(_translate(_tmp3, domain=_domain, mapping=None, target_language=target_language, default=None))
                else:
                    if not isinstance(_tmp3, unicode):
                        _tmp3 = str(_tmp3)
                if ('&' in _tmp3):
                    if (';' in _tmp3):
                        _tmp3 = _re_amp.sub('&amp;', _tmp3)
                    else:
                        _tmp3 = _tmp3.replace('&', '&amp;')
                if ('<' in _tmp3):
                    _tmp3 = _tmp3.replace('<', '&lt;')
                if ('>' in _tmp3):
                    _tmp3 = _tmp3.replace('>', '&gt;')
                if ('"' in _tmp3):
                    _tmp3 = _tmp3.replace('"', '&quot;')
                _write(((' href="' + _tmp3) + '"'))
            u'_content'
            _write('>')
            _tmp3 = _content
            _tmp = _tmp3
            if (_tmp.__class__ not in (str, unicode, int, float, )):
                try:
                    _tmp = _tmp.__html__
                except:
                    _tmp = _translate(_tmp, domain=_domain, mapping=None, target_language=target_language, default=None)
                else:
                    _tmp = _tmp()
                    _write(_tmp)
                    _tmp = None
            if (_tmp is not None):
                if not isinstance(_tmp, unicode):
                    _tmp = str(_tmp)
                if ('&' in _tmp):
                    if (';' in _tmp):
                        _tmp = _re_amp.sub('&amp;', _tmp)
                    else:
                        _tmp = _tmp.replace('&', '&amp;')
                if ('<' in _tmp):
                    _tmp = _tmp.replace('<', '&lt;')
                if ('>' in _tmp):
                    _tmp = _tmp.replace('>', '&gt;')
                _write(_tmp)
            u'not repeat.item.end'
            _write(u'</a>\n                ')
            _tmp3 = not _lookup_attr(repeat.item, 'end')
            if _tmp3:
                pass
                attrs = _attrs_4353342544
                _write(u'<span>/</span>')
            _write(u'\n            ')
            if (_tmp2 == 0):
                break
            _write(' ')
        u"''"
        _write(u'\n          </div>\n          ')
        _default.value = default = ''
        u"request.model_name or 'root'"
        _content = (_lookup_attr(econtext['request'], 'model_name') or 'root')
        attrs = _attrs_4353342352
        u'_content'
        _write(u'<div>')
        _tmp1 = _content
        _tmp = _tmp1
        if (_tmp.__class__ not in (str, unicode, int, float, )):
            try:
                _tmp = _tmp.__html__
            except:
                _tmp = _translate(_tmp, domain=_domain, mapping=None, target_language=target_language, default=None)
            else:
                _tmp = _tmp()
                _write(_tmp)
                _tmp = None
        if (_tmp is not None):
            if not isinstance(_tmp, unicode):
                _tmp = str(_tmp)
            if ('&' in _tmp):
                if (';' in _tmp):
                    _tmp = _re_amp.sub('&amp;', _tmp)
                else:
                    _tmp = _tmp.replace('&', '&amp;')
            if ('<' in _tmp):
                _tmp = _tmp.replace('<', '&lt;')
            if ('>' in _tmp):
                _tmp = _tmp.replace('>', '&gt;')
            _write(_tmp)
        u"%(slots)s.get(u'main')"
        _write(u'</div>\n        </h1>\n        ')
        _tmp = _slots.get(u'main')
        u'%(tmp)s is not None'
        _tmp1 = (_tmp is not None)
        if _tmp1:
            pass
            u'isinstance(%(tmp)s, basestring)'
            _tmp2 = isinstance(_tmp, basestring)
            if not _tmp2:
                pass
                econtext.update(dict(rcontext=rcontext, _domain=_domain))
                _tmp(econtext, repeat)
            else:
                pass
                u'%(tmp)s'
                _tmp2 = _tmp
                _tmp = _tmp2
                if (_tmp.__class__ not in (str, unicode, int, float, )):
                    try:
                        _tmp = _tmp.__html__
                    except:
                        _tmp = _translate(_tmp, domain=_domain, mapping=None, target_language=target_language, default=None)
                    else:
                        _tmp = _tmp()
                        _write(_tmp)
                        _tmp = None
                if (_tmp is not None):
                    if not isinstance(_tmp, unicode):
                        _tmp = str(_tmp)
                    _write(_tmp)
        else:
            pass
            attrs = _attrs_4345507600
            _write(u'<div>\n        </div>')
        _write(u'\n      </div>\n    </body>\n</html>')
        return
    return render

__filename__ = '/Users/gawel/py/formalchemy_project/pyramid_formalchemy/pyramid_formalchemy/templates/admin/master.pt'
registry[('master', False, '1488bdb950901f8f258549439ef6661a49aae984')] = bind()

########NEW FILE########
__FILENAME__ = models.pt
registry = dict(version=0)
def bind():
    from cPickle import loads as _loads
    _lookup_attr = _loads('cchameleon.core.codegen\nlookup_attr\np1\n.')
    _attrs_4358089040 = _loads('(dp1\n.')
    _init_scope = _loads('cchameleon.core.utils\necontext\np1\n.')
    _re_amp = _loads("cre\n_compile\np1\n(S'&(?!([A-Za-z]+|#[0-9]+);)'\np2\nI0\ntRp3\n.")
    _attrs_4358088464 = _loads('(dp1\n.')
    _init_stream = _loads('cchameleon.core.generation\ninitialize_stream\np1\n.')
    _attrs_4358088656 = _loads('(dp1\n.')
    _init_default = _loads('cchameleon.core.generation\ninitialize_default\np1\n.')
    _attrs_4358088848 = _loads('(dp1\n.')
    _init_tal = _loads('cchameleon.core.generation\ninitialize_tal\np1\n.')
    def render(econtext, rcontext=None):
        macros = econtext.get('macros')
        _translate = econtext.get('_translate')
        _slots = econtext.get('_slots')
        target_language = econtext.get('target_language')
        u'_init_stream()'
        (_out, _write, ) = _init_stream()
        u'_init_tal()'
        (_attributes, repeat, ) = _init_tal()
        u'_init_default()'
        _default = _init_default()
        u'None'
        default = None
        u'None'
        _domain = None
        u"main.macros['master']"
        _metal = _lookup_attr(econtext['main'], 'macros')['master']
        def _callback_main(econtext, _repeat, _out=_out, _write=_write, _domain=_domain, **_ignored):
            if _repeat:
                repeat.update(_repeat)
            attrs = _attrs_4358088464
            u'models'
            _write(u'<div>\n      ')
            _tmp1 = econtext['models']
            item = None
            (_tmp1, _tmp2, ) = repeat.insert('item', _tmp1)
            for item in _tmp1:
                _tmp2 = (_tmp2 - 1)
                attrs = _attrs_4358088656
                _write(u'<div>\n        ')
                attrs = _attrs_4358088848
                u"''"
                _write(u'<div>\n          ')
                _default.value = default = ''
                u'item'
                _content = item
                attrs = _attrs_4358089040
                u'request.route_url(request.route_name, traverse=item)'
                _write(u'<a')
                _tmp3 = _lookup_attr(econtext['request'], 'route_url')(_lookup_attr(econtext['request'], 'route_name'), traverse=item)
                if (_tmp3 is _default):
                    _tmp3 = None
                if ((_tmp3 is not None) and (_tmp3 is not False)):
                    if (_tmp3.__class__ not in (str, unicode, int, float, )):
                        _tmp3 = unicode(_translate(_tmp3, domain=_domain, mapping=None, target_language=target_language, default=None))
                    else:
                        if not isinstance(_tmp3, unicode):
                            _tmp3 = str(_tmp3)
                    if ('&' in _tmp3):
                        if (';' in _tmp3):
                            _tmp3 = _re_amp.sub('&amp;', _tmp3)
                        else:
                            _tmp3 = _tmp3.replace('&', '&amp;')
                    if ('<' in _tmp3):
                        _tmp3 = _tmp3.replace('<', '&lt;')
                    if ('>' in _tmp3):
                        _tmp3 = _tmp3.replace('>', '&gt;')
                    if ('"' in _tmp3):
                        _tmp3 = _tmp3.replace('"', '&quot;')
                    _write(((' href="' + _tmp3) + '"'))
                u'_content'
                _write('>')
                _tmp3 = _content
                _tmp = _tmp3
                if (_tmp.__class__ not in (str, unicode, int, float, )):
                    try:
                        _tmp = _tmp.__html__
                    except:
                        _tmp = _translate(_tmp, domain=_domain, mapping=None, target_language=target_language, default=None)
                    else:
                        _tmp = _tmp()
                        _write(_tmp)
                        _tmp = None
                if (_tmp is not None):
                    if not isinstance(_tmp, unicode):
                        _tmp = str(_tmp)
                    if ('&' in _tmp):
                        if (';' in _tmp):
                            _tmp = _re_amp.sub('&amp;', _tmp)
                        else:
                            _tmp = _tmp.replace('&', '&amp;')
                    if ('<' in _tmp):
                        _tmp = _tmp.replace('<', '&lt;')
                    if ('>' in _tmp):
                        _tmp = _tmp.replace('>', '&gt;')
                    _write(_tmp)
                _write(u'</a>\n        </div>\n      </div>')
                if (_tmp2 == 0):
                    break
                _write(' ')
            _write(u'\n    </div>\n')
        u"{'main': _callback_main}"
        _tmp = {'main': _callback_main, }
        u"main.macros['master']"
        _metal.render(_tmp, _out=_out, _write=_write, _domain=_domain, econtext=econtext)
        return _out.getvalue()
    return render

__filename__ = '/Users/gawel/py/formalchemy_project/pyramid_formalchemy/pyramid_formalchemy/templates/admin/models.pt'
registry[(None, True, '1488bdb950901f8f258549439ef6661a49aae984')] = bind()

########NEW FILE########
__FILENAME__ = new.pt
registry = dict(version=0)
def bind():
    from cPickle import loads as _loads
    _lookup_attr = _loads('cchameleon.core.codegen\nlookup_attr\np1\n.')
    _init_scope = _loads('cchameleon.core.utils\necontext\np1\n.')
    _re_amp = _loads("cre\n_compile\np1\n(S'&(?!([A-Za-z]+|#[0-9]+);)'\np2\nI0\ntRp3\n.")
    _attrs_4356178128 = _loads('(dp1\n.')
    _attrs_4356132752 = _loads('(dp1\n.')
    _init_stream = _loads('cchameleon.core.generation\ninitialize_stream\np1\n.')
    _attrs_4356178000 = _loads('(dp1\nVmethod\np2\nVPOST\np3\nsVenctype\np4\nVmultipart/form-data\np5\ns.')
    _init_default = _loads('cchameleon.core.generation\ninitialize_default\np1\n.')
    _attrs_4356178192 = _loads('(dp1\nVclass\np2\nVfa_field\np3\ns.')
    _init_tal = _loads('cchameleon.core.generation\ninitialize_tal\np1\n.')
    def render(econtext, rcontext=None):
        macros = econtext.get('macros')
        _translate = econtext.get('_translate')
        _slots = econtext.get('_slots')
        target_language = econtext.get('target_language')
        u'_init_stream()'
        (_out, _write, ) = _init_stream()
        u'_init_tal()'
        (_attributes, repeat, ) = _init_tal()
        u'_init_default()'
        _default = _init_default()
        u'None'
        default = None
        u'None'
        _domain = None
        u"main.macros['master']"
        _metal = _lookup_attr(econtext['main'], 'macros')['master']
        def _callback_main(econtext, _repeat, _out=_out, _write=_write, _domain=_domain, **_ignored):
            if _repeat:
                repeat.update(_repeat)
            attrs = _attrs_4356132752
            _write(u'<div>\n      ')
            attrs = _attrs_4356178000
            u'request.fa_url(request.model_name)'
            _write(u'<form method="POST" enctype="multipart/form-data"')
            _tmp1 = _lookup_attr(econtext['request'], 'fa_url')(_lookup_attr(econtext['request'], 'model_name'))
            if (_tmp1 is _default):
                _tmp1 = None
            if ((_tmp1 is not None) and (_tmp1 is not False)):
                if (_tmp1.__class__ not in (str, unicode, int, float, )):
                    _tmp1 = unicode(_translate(_tmp1, domain=_domain, mapping=None, target_language=target_language, default=None))
                else:
                    if not isinstance(_tmp1, unicode):
                        _tmp1 = str(_tmp1)
                if ('&' in _tmp1):
                    if (';' in _tmp1):
                        _tmp1 = _re_amp.sub('&amp;', _tmp1)
                    else:
                        _tmp1 = _tmp1.replace('&', '&amp;')
                if ('<' in _tmp1):
                    _tmp1 = _tmp1.replace('<', '&lt;')
                if ('>' in _tmp1):
                    _tmp1 = _tmp1.replace('>', '&gt;')
                if ('"' in _tmp1):
                    _tmp1 = _tmp1.replace('"', '&quot;')
                _write(((' action="' + _tmp1) + '"'))
            u"''"
            _write(u'>\n        ')
            _default.value = default = ''
            u'fs.render()'
            _content = _lookup_attr(econtext['fs'], 'render')()
            attrs = _attrs_4356178128
            u'_content'
            _write(u'<div>')
            _tmp1 = _content
            _tmp = _tmp1
            if (_tmp.__class__ not in (str, unicode, int, float, )):
                try:
                    _tmp = _tmp.__html__
                except:
                    _tmp = _translate(_tmp, domain=_domain, mapping=None, target_language=target_language, default=None)
                else:
                    _tmp = _tmp()
                    _write(_tmp)
                    _tmp = None
            if (_tmp is not None):
                if not isinstance(_tmp, unicode):
                    _tmp = str(_tmp)
                _write(_tmp)
            u"u'\\n        '"
            _write(u'</div>\n        ')
            _default.value = default = u'\n        '
            u'actions.buttons(request)'
            _content = _lookup_attr(econtext['actions'], 'buttons')(econtext['request'])
            attrs = _attrs_4356178192
            u'_content'
            _write(u'<p class="fa_field">')
            _tmp1 = _content
            _tmp = _tmp1
            if (_tmp.__class__ not in (str, unicode, int, float, )):
                try:
                    _tmp = _tmp.__html__
                except:
                    _tmp = _translate(_tmp, domain=_domain, mapping=None, target_language=target_language, default=None)
                else:
                    _tmp = _tmp()
                    _write(_tmp)
                    _tmp = None
            if (_tmp is not None):
                if not isinstance(_tmp, unicode):
                    _tmp = str(_tmp)
                _write(_tmp)
            _write(u'</p>\n      </form>\n    </div>\n')
        u"{'main': _callback_main}"
        _tmp = {'main': _callback_main, }
        u"main.macros['master']"
        _metal.render(_tmp, _out=_out, _write=_write, _domain=_domain, econtext=econtext)
        return _out.getvalue()
    return render

__filename__ = '/Users/gawel/py/formalchemy_project/pyramid_formalchemy/pyramid_formalchemy/templates/admin/new.pt'
registry[(None, True, '1488bdb950901f8f258549439ef6661a49aae984')] = bind()

########NEW FILE########
__FILENAME__ = show.pt
registry = dict(version=0)
def bind():
    from cPickle import loads as _loads
    _lookup_attr = _loads('cchameleon.core.codegen\nlookup_attr\np1\n.')
    _init_scope = _loads('cchameleon.core.utils\necontext\np1\n.')
    _attrs_4362312784 = _loads('(dp1\n.')
    _init_stream = _loads('cchameleon.core.generation\ninitialize_stream\np1\n.')
    _attrs_4362313104 = _loads('(dp1\n.')
    _init_default = _loads('cchameleon.core.generation\ninitialize_default\np1\n.')
    _attrs_4362312976 = _loads('(dp1\n.')
    _init_tal = _loads('cchameleon.core.generation\ninitialize_tal\np1\n.')
    _attrs_4362313296 = _loads('(dp1\nVclass\np2\nVfa_field\np3\ns.')
    def render(econtext, rcontext=None):
        macros = econtext.get('macros')
        _translate = econtext.get('_translate')
        _slots = econtext.get('_slots')
        target_language = econtext.get('target_language')
        u'_init_stream()'
        (_out, _write, ) = _init_stream()
        u'_init_tal()'
        (_attributes, repeat, ) = _init_tal()
        u'_init_default()'
        _default = _init_default()
        u'None'
        default = None
        u'None'
        _domain = None
        u"main.macros['master']"
        _metal = _lookup_attr(econtext['main'], 'macros')['master']
        def _callback_main(econtext, _repeat, _out=_out, _write=_write, _domain=_domain, **_ignored):
            if _repeat:
                repeat.update(_repeat)
            attrs = _attrs_4362312784
            u"''"
            _write(u'<div>\n      ')
            _default.value = default = ''
            u'fs.render()'
            _content = _lookup_attr(econtext['fs'], 'render')()
            attrs = _attrs_4362312976
            u'_content'
            _write(u'<div>')
            _tmp1 = _content
            _tmp = _tmp1
            if (_tmp.__class__ not in (str, unicode, int, float, )):
                try:
                    _tmp = _tmp.__html__
                except:
                    _tmp = _translate(_tmp, domain=_domain, mapping=None, target_language=target_language, default=None)
                else:
                    _tmp = _tmp()
                    _write(_tmp)
                    _tmp = None
            if (_tmp is not None):
                if not isinstance(_tmp, unicode):
                    _tmp = str(_tmp)
                _write(_tmp)
            _write(u'</div>\n      ')
            attrs = _attrs_4362313104
            u"u'\\n      '"
            _write(u'<div>\n      ')
            _default.value = default = u'\n      '
            u'actions.buttons(request)'
            _content = _lookup_attr(econtext['actions'], 'buttons')(econtext['request'])
            attrs = _attrs_4362313296
            u'_content'
            _write(u'<p class="fa_field">')
            _tmp1 = _content
            _tmp = _tmp1
            if (_tmp.__class__ not in (str, unicode, int, float, )):
                try:
                    _tmp = _tmp.__html__
                except:
                    _tmp = _translate(_tmp, domain=_domain, mapping=None, target_language=target_language, default=None)
                else:
                    _tmp = _tmp()
                    _write(_tmp)
                    _tmp = None
            if (_tmp is not None):
                if not isinstance(_tmp, unicode):
                    _tmp = str(_tmp)
                _write(_tmp)
            _write(u'</p>\n      </div>\n    </div>\n')
        u"{'main': _callback_main}"
        _tmp = {'main': _callback_main, }
        u"main.macros['master']"
        _metal.render(_tmp, _out=_out, _write=_write, _domain=_domain, econtext=econtext)
        return _out.getvalue()
    return render

__filename__ = '/Users/gawel/py/formalchemy_project/pyramid_formalchemy/pyramid_formalchemy/templates/admin/show.pt'
registry[(None, True, '1488bdb950901f8f258549439ef6661a49aae984')] = bind()

########NEW FILE########
__FILENAME__ = fieldset.pt
registry = dict(version=0)
def bind():
    from cPickle import loads as _loads
    _lookup_attr = _loads('cchameleon.core.codegen\nlookup_attr\np1\n.')
    _init_scope = _loads('cchameleon.core.utils\necontext\np1\n.')
    _re_amp = _loads("cre\n_compile\np1\n(S'&(?!([A-Za-z]+|#[0-9]+);)'\np2\nI0\ntRp3\n.")
    _attrs_4355399760 = _loads('(dp1\n.')
    _attrs_4355400208 = _loads('(dp1\nVclass\np2\nVfa_instructions ui-corner-all\np3\ns.')
    _attrs_4355399888 = _loads('(dp1\n.')
    _attrs_4355400144 = _loads('(dp1\nVclass\np2\nVlabel\np3\ns.')
    _init_stream = _loads('cchameleon.core.generation\ninitialize_stream\np1\n.')
    _init_default = _loads('cchameleon.core.generation\ninitialize_default\np1\n.')
    _attrs_4355400400 = _loads('(dp1\nVclass\np2\nVui-state-error ui-corner-all\np3\ns.')
    _attrs_4355400080 = _loads('(dp1\n.')
    _attrs_4355400464 = _loads('(dp1\nVclass\np2\nVfield_input\np3\ns.')
    _attrs_4355400528 = _loads('(dp1\n.')
    _attrs_4355400016 = _loads('(dp1\nVclass\np2\nVfa_field ui-widget\np3\ns.')
    _init_tal = _loads('cchameleon.core.generation\ninitialize_tal\np1\n.')
    _attrs_4355400272 = _loads('(dp1\n.')
    def render(econtext, rcontext=None):
        macros = econtext.get('macros')
        _translate = econtext.get('_translate')
        _slots = econtext.get('_slots')
        target_language = econtext.get('target_language')
        u'_init_stream()'
        (_out, _write, ) = _init_stream()
        u'_init_tal()'
        (_attributes, repeat, ) = _init_tal()
        u'_init_default()'
        _default = _init_default()
        u'None'
        default = None
        u'None'
        _domain = None
        u'False'
        focus_rendered = False
        u'fieldset.errors.get(None, False)'
        _write(u'\n')
        _tmp1 = _lookup_attr(_lookup_attr(econtext['fieldset'], 'errors'), 'get')(None, False)
        if _tmp1:
            pass
            attrs = _attrs_4355399760
            u"''"
            _write(u'<div>\n  ')
            _default.value = default = ''
            u'fieldset.error.get(None)'
            _tmp1 = _lookup_attr(_lookup_attr(econtext['fieldset'], 'error'), 'get')(None)
            error = None
            (_tmp1, _tmp2, ) = repeat.insert('error', _tmp1)
            for error in _tmp1:
                _tmp2 = (_tmp2 - 1)
                u'error'
                _content = error
                attrs = _attrs_4355399888
                u'_content'
                _write(u'<div>')
                _tmp3 = _content
                _tmp = _tmp3
                if (_tmp.__class__ not in (str, unicode, int, float, )):
                    try:
                        _tmp = _tmp.__html__
                    except:
                        _tmp = _translate(_tmp, domain=_domain, mapping=None, target_language=target_language, default=None)
                    else:
                        _tmp = _tmp()
                        _write(_tmp)
                        _tmp = None
                if (_tmp is not None):
                    if not isinstance(_tmp, unicode):
                        _tmp = str(_tmp)
                    if ('&' in _tmp):
                        if (';' in _tmp):
                            _tmp = _re_amp.sub('&amp;', _tmp)
                        else:
                            _tmp = _tmp.replace('&', '&amp;')
                    if ('<' in _tmp):
                        _tmp = _tmp.replace('<', '&lt;')
                    if ('>' in _tmp):
                        _tmp = _tmp.replace('>', '&gt;')
                    _write(_tmp)
                _write(u'</div>')
                if (_tmp2 == 0):
                    break
                _write(' ')
            _write(u'\n</div>')
        u'fieldset.render_fields.itervalues()'
        _write(u'\n\n')
        _tmp1 = _lookup_attr(_lookup_attr(econtext['fieldset'], 'render_fields'), 'itervalues')()
        field = None
        (_tmp1, _tmp2, ) = repeat.insert('field', _tmp1)
        for field in _tmp1:
            _tmp2 = (_tmp2 - 1)
            _write(u'\n  ')
            attrs = _attrs_4355400016
            u'field.requires_label'
            _write(u'<div class="fa_field ui-widget">\n    ')
            _tmp3 = _lookup_attr(field, 'requires_label')
            if _tmp3:
                pass
                attrs = _attrs_4355400144
                u"''"
                _write(u'<div class="label">\n      ')
                _default.value = default = ''
                u'isinstance(field.type, fatypes.Boolean)'
                _tmp3 = isinstance(_lookup_attr(field, 'type'), _lookup_attr(econtext['fatypes'], 'Boolean'))
                if _tmp3:
                    pass
                    u'field.render()'
                    _content = _lookup_attr(field, 'render')()
                    attrs = _attrs_4355400272
                    u'_content'
                    _write(u'<div>')
                    _tmp3 = _content
                    _tmp = _tmp3
                    if (_tmp.__class__ not in (str, unicode, int, float, )):
                        try:
                            _tmp = _tmp.__html__
                        except:
                            _tmp = _translate(_tmp, domain=_domain, mapping=None, target_language=target_language, default=None)
                        else:
                            _tmp = _tmp()
                            _write(_tmp)
                            _tmp = None
                    if (_tmp is not None):
                        if not isinstance(_tmp, unicode):
                            _tmp = str(_tmp)
                        _write(_tmp)
                    _write(u'</div>')
                u"''"
                _write(u'\n      ')
                _default.value = default = ''
                u'field.label_tag()'
                _content = _lookup_attr(field, 'label_tag')()
                u'_content'
                _tmp3 = _content
                _tmp = _tmp3
                if (_tmp.__class__ not in (str, unicode, int, float, )):
                    try:
                        _tmp = _tmp.__html__
                    except:
                        _tmp = _translate(_tmp, domain=_domain, mapping=None, target_language=target_language, default=None)
                    else:
                        _tmp = _tmp()
                        _write(_tmp)
                        _tmp = None
                if (_tmp is not None):
                    if not isinstance(_tmp, unicode):
                        _tmp = str(_tmp)
                    _write(_tmp)
                _write(u'\n    </div>')
            u"u'\\n    '"
            _write(u'\n    ')
            _default.value = default = u'\n    '
            u"'instructions' in field.metadata"
            _tmp3 = ('instructions' in _lookup_attr(field, 'metadata'))
            if _tmp3:
                pass
                u"field.metadata['instructions']"
                _content = _lookup_attr(field, 'metadata')['instructions']
                attrs = _attrs_4355400208
                u'_content'
                _write(u'<div class="fa_instructions ui-corner-all">')
                _tmp3 = _content
                _tmp = _tmp3
                if (_tmp.__class__ not in (str, unicode, int, float, )):
                    try:
                        _tmp = _tmp.__html__
                    except:
                        _tmp = _translate(_tmp, domain=_domain, mapping=None, target_language=target_language, default=None)
                    else:
                        _tmp = _tmp()
                        _write(_tmp)
                        _tmp = None
                if (_tmp is not None):
                    if not isinstance(_tmp, unicode):
                        _tmp = str(_tmp)
                    if ('&' in _tmp):
                        if (';' in _tmp):
                            _tmp = _re_amp.sub('&amp;', _tmp)
                        else:
                            _tmp = _tmp.replace('&', '&amp;')
                    if ('<' in _tmp):
                        _tmp = _tmp.replace('<', '&lt;')
                    if ('>' in _tmp):
                        _tmp = _tmp.replace('>', '&gt;')
                    _write(_tmp)
                _write(u'</div>')
            u'field.errors'
            _write(u'\n    ')
            _tmp3 = _lookup_attr(field, 'errors')
            if _tmp3:
                pass
                attrs = _attrs_4355400400
                u"''"
                _write(u'<div class="ui-state-error ui-corner-all">\n      ')
                _default.value = default = ''
                u'field.errors'
                _tmp3 = _lookup_attr(field, 'errors')
                error = None
                (_tmp3, _tmp4, ) = repeat.insert('error', _tmp3)
                for error in _tmp3:
                    _tmp4 = (_tmp4 - 1)
                    u'error'
                    _content = error
                    attrs = _attrs_4355400528
                    u'_content'
                    _write(u'<div>')
                    _tmp5 = _content
                    _tmp = _tmp5
                    if (_tmp.__class__ not in (str, unicode, int, float, )):
                        try:
                            _tmp = _tmp.__html__
                        except:
                            _tmp = _translate(_tmp, domain=_domain, mapping=None, target_language=target_language, default=None)
                        else:
                            _tmp = _tmp()
                            _write(_tmp)
                            _tmp = None
                    if (_tmp is not None):
                        if not isinstance(_tmp, unicode):
                            _tmp = str(_tmp)
                        if ('&' in _tmp):
                            if (';' in _tmp):
                                _tmp = _re_amp.sub('&amp;', _tmp)
                            else:
                                _tmp = _tmp.replace('&', '&amp;')
                        if ('<' in _tmp):
                            _tmp = _tmp.replace('<', '&lt;')
                        if ('>' in _tmp):
                            _tmp = _tmp.replace('>', '&gt;')
                        _write(_tmp)
                    _write(u'</div>')
                    if (_tmp4 == 0):
                        break
                    _write(' ')
                _write(u'\n    </div>')
            u"''"
            _write(u'\n    ')
            _default.value = default = ''
            u'not isinstance(field.type, fatypes.Boolean)'
            _tmp3 = not isinstance(_lookup_attr(field, 'type'), _lookup_attr(econtext['fatypes'], 'Boolean'))
            if _tmp3:
                pass
                u'field.render()'
                _content = _lookup_attr(field, 'render')()
                attrs = _attrs_4355400464
                u'_content'
                _write(u'<div class="field_input">')
                _tmp3 = _content
                _tmp = _tmp3
                if (_tmp.__class__ not in (str, unicode, int, float, )):
                    try:
                        _tmp = _tmp.__html__
                    except:
                        _tmp = _translate(_tmp, domain=_domain, mapping=None, target_language=target_language, default=None)
                    else:
                        _tmp = _tmp()
                        _write(_tmp)
                        _tmp = None
                if (_tmp is not None):
                    if not isinstance(_tmp, unicode):
                        _tmp = str(_tmp)
                    _write(_tmp)
                _write(u'</div>')
            u'not field.is_readonly() and (fieldset.focus == field or fieldset.focus is True) and not focus_rendered'
            _write(u'\n  </div>\n  ')
            _tmp3 = (not _lookup_attr(field, 'is_readonly')() and ((_lookup_attr(econtext['fieldset'], 'focus') == field) or (_lookup_attr(econtext['fieldset'], 'focus') is True)) and not focus_rendered)
            if _tmp3:
                pass
                attrs = _attrs_4355400080
                u'True'
                _write(u'<script>\n    ')
                focus_rendered = True
                u'field.renderer.name'
                _write(u'\n    jQuery(document).ready(function(){jQuery("[name=\'')
                _tmp3 = _lookup_attr(_lookup_attr(field, 'renderer'), 'name')
                _tmp = _tmp3
                if (_tmp.__class__ not in (str, unicode, int, float, )):
                    try:
                        _tmp = _tmp.__html__
                    except:
                        _tmp = _translate(_tmp, domain=_domain, mapping=None, target_language=target_language, default=None)
                    else:
                        _tmp = _tmp()
                        _write(_tmp)
                        _tmp = None
                if (_tmp is not None):
                    if not isinstance(_tmp, unicode):
                        _tmp = str(_tmp)
                    if ('&' in _tmp):
                        if (';' in _tmp):
                            _tmp = _re_amp.sub('&amp;', _tmp)
                        else:
                            _tmp = _tmp.replace('&', '&amp;')
                    if ('<' in _tmp):
                        _tmp = _tmp.replace('<', '&lt;')
                    if ('>' in _tmp):
                        _tmp = _tmp.replace('>', '&gt;')
                    _write(_tmp)
                _write(u'\']").focus();});\n  </script>')
            _write(u'\n')
            if (_tmp2 == 0):
                break
            _write(' ')
        _write(u'')
        return _out.getvalue()
    return render

__filename__ = '/Users/gawel/py/formalchemy_project/pyramid_formalchemy/pyramid_formalchemy/templates/forms/fieldset.pt'
registry[(None, True, '1488bdb950901f8f258549439ef6661a49aae984')] = bind()

########NEW FILE########
__FILENAME__ = fieldset_readonly.pt
registry = dict(version=0)
def bind():
    from cPickle import loads as _loads
    _lookup_attr = _loads('cchameleon.core.codegen\nlookup_attr\np1\n.')
    _init_scope = _loads('cchameleon.core.utils\necontext\np1\n.')
    _init_default = _loads('cchameleon.core.generation\ninitialize_default\np1\n.')
    _attrs_4355418576 = _loads('(dp1\nVstyle\np2\nVdisplay:none\np3\ns.')
    _attrs_4355401296 = _loads('(dp1\n.')
    _init_stream = _loads('cchameleon.core.generation\ninitialize_stream\np1\n.')
    _attrs_4355399952 = _loads('(dp1\n.')
    _attrs_4355441232 = _loads('(dp1\n.')
    _attrs_4355400784 = _loads('(dp1\n.')
    _attrs_4355400912 = _loads('(dp1\nVclass\np2\nVfield_readonly\np3\ns.')
    _init_tal = _loads('cchameleon.core.generation\ninitialize_tal\np1\n.')
    _attrs_4355400848 = _loads('(dp1\n.')
    def render(econtext, rcontext=None):
        macros = econtext.get('macros')
        _translate = econtext.get('_translate')
        _slots = econtext.get('_slots')
        target_language = econtext.get('target_language')
        u'_init_stream()'
        (_out, _write, ) = _init_stream()
        u'_init_tal()'
        (_attributes, repeat, ) = _init_tal()
        u'_init_default()'
        _default = _init_default()
        u'None'
        default = None
        u'None'
        _domain = None
        attrs = _attrs_4355441232
        u'fieldset.render_fields.itervalues()'
        _write(u'<tbody>\n  ')
        _tmp1 = _lookup_attr(_lookup_attr(econtext['fieldset'], 'render_fields'), 'itervalues')()
        field = None
        (_tmp1, _tmp2, ) = repeat.insert('field', _tmp1)
        for field in _tmp1:
            _tmp2 = (_tmp2 - 1)
            u'field.requires_label'
            _write(u'')
            _tmp3 = _lookup_attr(field, 'requires_label')
            if _tmp3:
                pass
                attrs = _attrs_4355401296
                _write(u'<tr>\n      ')
                attrs = _attrs_4355400912
                u"''"
                _write(u'<td class="field_readonly">\n        ')
                _default.value = default = ''
                u'field.label_tag()'
                _content = _lookup_attr(field, 'label_tag')()
                u'_content'
                _tmp3 = _content
                _tmp = _tmp3
                if (_tmp.__class__ not in (str, unicode, int, float, )):
                    try:
                        _tmp = _tmp.__html__
                    except:
                        _tmp = _translate(_tmp, domain=_domain, mapping=None, target_language=target_language, default=None)
                    else:
                        _tmp = _tmp()
                        _write(_tmp)
                        _tmp = None
                if (_tmp is not None):
                    if not isinstance(_tmp, unicode):
                        _tmp = str(_tmp)
                    _write(_tmp)
                u"''"
                _write(u'\n      </td>\n      ')
                _default.value = default = ''
                u'field.render_readonly()'
                _content = _lookup_attr(field, 'render_readonly')()
                attrs = _attrs_4355400848
                u'_content'
                _write(u'<td>')
                _tmp3 = _content
                _tmp = _tmp3
                if (_tmp.__class__ not in (str, unicode, int, float, )):
                    try:
                        _tmp = _tmp.__html__
                    except:
                        _tmp = _translate(_tmp, domain=_domain, mapping=None, target_language=target_language, default=None)
                    else:
                        _tmp = _tmp()
                        _write(_tmp)
                        _tmp = None
                if (_tmp is not None):
                    if not isinstance(_tmp, unicode):
                        _tmp = str(_tmp)
                    _write(_tmp)
                _write(u'</td>\n    </tr>')
            _write(u'\n  ')
            if (_tmp2 == 0):
                break
            _write(' ')
        _write(u'\n  ')
        attrs = _attrs_4355418576
        _write(u'<tr style="display:none">')
        attrs = _attrs_4355400784
        _write(u'<td>&nbsp;</td>')
        attrs = _attrs_4355399952
        u'fieldset.render_fields.itervalues()'
        _write(u'<td>\n    ')
        _tmp1 = _lookup_attr(_lookup_attr(econtext['fieldset'], 'render_fields'), 'itervalues')()
        field = None
        (_tmp1, _tmp2, ) = repeat.insert('field', _tmp1)
        for field in _tmp1:
            _tmp2 = (_tmp2 - 1)
            u"''"
            _write(u'')
            _default.value = default = ''
            u'not field.requires_label'
            _tmp3 = not _lookup_attr(field, 'requires_label')
            if _tmp3:
                pass
                u'field.render_readonly()'
                _content = _lookup_attr(field, 'render_readonly')()
                u'_content'
                _tmp3 = _content
                _tmp = _tmp3
                if (_tmp.__class__ not in (str, unicode, int, float, )):
                    try:
                        _tmp = _tmp.__html__
                    except:
                        _tmp = _translate(_tmp, domain=_domain, mapping=None, target_language=target_language, default=None)
                    else:
                        _tmp = _tmp()
                        _write(_tmp)
                        _tmp = None
                if (_tmp is not None):
                    if not isinstance(_tmp, unicode):
                        _tmp = str(_tmp)
                    _write(_tmp)
            _write(u'\n    ')
            if (_tmp2 == 0):
                break
            _write(' ')
        _write(u'\n  </td>\n  </tr>\n</tbody>')
        return _out.getvalue()
    return render

__filename__ = '/Users/gawel/py/formalchemy_project/pyramid_formalchemy/pyramid_formalchemy/templates/forms/fieldset_readonly.pt'
registry[(None, True, '1488bdb950901f8f258549439ef6661a49aae984')] = bind()

########NEW FILE########
__FILENAME__ = grid.pt
registry = dict(version=0)
def bind():
    from cPickle import loads as _loads
    _lookup_attr = _loads('cchameleon.core.codegen\nlookup_attr\np1\n.')
    _init_scope = _loads('cchameleon.core.utils\necontext\np1\n.')
    _re_amp = _loads("cre\n_compile\np1\n(S'&(?!([A-Za-z]+|#[0-9]+);)'\np2\nI0\ntRp3\n.")
    _attrs_4361422096 = _loads('(dp1\nVclass\np2\nVlayout-grid\np3\ns.')
    _attrs_4361422992 = _loads('(dp1\n.')
    _attrs_4361422800 = _loads('(dp1\n.')
    _init_stream = _loads('cchameleon.core.generation\ninitialize_stream\np1\n.')
    _attrs_4361422352 = _loads('(dp1\n.')
    _init_default = _loads('cchameleon.core.generation\ninitialize_default\np1\n.')
    _attrs_4361422416 = _loads('(dp1\n.')
    _attrs_4361422480 = _loads('(dp1\nVclass\np2\nVui-widget-header\np3\ns.')
    _attrs_4361422608 = _loads('(dp1\n.')
    _attrs_4361423312 = _loads('(dp1\nVclass\np2\nVgrid_error\np3\ns.')
    _init_tal = _loads('cchameleon.core.generation\ninitialize_tal\np1\n.')
    def render(econtext, rcontext=None):
        macros = econtext.get('macros')
        _translate = econtext.get('_translate')
        _slots = econtext.get('_slots')
        target_language = econtext.get('target_language')
        u'_init_stream()'
        (_out, _write, ) = _init_stream()
        u'_init_tal()'
        (_attributes, repeat, ) = _init_tal()
        u'_init_default()'
        _default = _init_default()
        u'None'
        default = None
        u'None'
        _domain = None
        attrs = _attrs_4361422096
        _write(u'<table class="layout-grid">\n')
        attrs = _attrs_4361422352
        _write(u'<thead>\n  ')
        attrs = _attrs_4361422480
        u"''"
        _write(u'<tr class="ui-widget-header">\n    ')
        _default.value = default = ''
        u'collection.render_fields.itervalues()'
        _tmp1 = _lookup_attr(_lookup_attr(econtext['collection'], 'render_fields'), 'itervalues')()
        field = None
        (_tmp1, _tmp2, ) = repeat.insert('field', _tmp1)
        for field in _tmp1:
            _tmp2 = (_tmp2 - 1)
            u'field.label()'
            _content = _lookup_attr(field, 'label')()
            attrs = _attrs_4361422608
            u'_content'
            _write(u'<th>')
            _tmp3 = _content
            _tmp = _tmp3
            if (_tmp.__class__ not in (str, unicode, int, float, )):
                try:
                    _tmp = _tmp.__html__
                except:
                    _tmp = _translate(_tmp, domain=_domain, mapping=None, target_language=target_language, default=None)
                else:
                    _tmp = _tmp()
                    _write(_tmp)
                    _tmp = None
            if (_tmp is not None):
                if not isinstance(_tmp, unicode):
                    _tmp = str(_tmp)
                if ('&' in _tmp):
                    if (';' in _tmp):
                        _tmp = _re_amp.sub('&amp;', _tmp)
                    else:
                        _tmp = _tmp.replace('&', '&amp;')
                if ('<' in _tmp):
                    _tmp = _tmp.replace('<', '&lt;')
                if ('>' in _tmp):
                    _tmp = _tmp.replace('>', '&gt;')
                _write(_tmp)
            _write(u'</th>')
            if (_tmp2 == 0):
                break
            _write(' ')
        _write(u'\n  </tr>\n</thead>\n')
        attrs = _attrs_4361422416
        u'collection.rows'
        _write(u'<tbody>\n  ')
        _tmp1 = _lookup_attr(econtext['collection'], 'rows')
        row = None
        (_tmp1, _tmp2, ) = repeat.insert('row', _tmp1)
        for row in _tmp1:
            _tmp2 = (_tmp2 - 1)
            u'collection._set_active(row)'
            _write(u'')
            dummy = _lookup_attr(econtext['collection'], '_set_active')(row)
            u'collection.get_errors(row)'
            row_errors = _lookup_attr(econtext['collection'], 'get_errors')(row)
            attrs = _attrs_4361422800
            u"ui-widget-${repeat.row.even and 'even' or 'odd'}"
            _write(u'<tr')
            _tmp3 = ('%s%s' % (u'ui-widget-', ((_lookup_attr(repeat.row, 'even') and 'even') or 'odd'), ))
            if (_tmp3 is _default):
                _tmp3 = None
            if ((_tmp3 is not None) and (_tmp3 is not False)):
                if (_tmp3.__class__ not in (str, unicode, int, float, )):
                    _tmp3 = unicode(_translate(_tmp3, domain=_domain, mapping=None, target_language=target_language, default=None))
                else:
                    if not isinstance(_tmp3, unicode):
                        _tmp3 = str(_tmp3)
                if ('&' in _tmp3):
                    if (';' in _tmp3):
                        _tmp3 = _re_amp.sub('&amp;', _tmp3)
                    else:
                        _tmp3 = _tmp3.replace('&', '&amp;')
                if ('<' in _tmp3):
                    _tmp3 = _tmp3.replace('<', '&lt;')
                if ('>' in _tmp3):
                    _tmp3 = _tmp3.replace('>', '&gt;')
                if ('"' in _tmp3):
                    _tmp3 = _tmp3.replace('"', '&quot;')
                _write(((' class="' + _tmp3) + '"'))
            u'collection.render_fields.itervalues()'
            _write(u'>\n      ')
            _tmp3 = _lookup_attr(_lookup_attr(econtext['collection'], 'render_fields'), 'itervalues')()
            field = None
            (_tmp3, _tmp4, ) = repeat.insert('field', _tmp3)
            for field in _tmp3:
                _tmp4 = (_tmp4 - 1)
                attrs = _attrs_4361422992
                u"''"
                _write(u'<td>\n        ')
                _default.value = default = ''
                u'field.render()'
                _content = _lookup_attr(field, 'render')()
                u'_content'
                _tmp5 = _content
                _tmp = _tmp5
                if (_tmp.__class__ not in (str, unicode, int, float, )):
                    try:
                        _tmp = _tmp.__html__
                    except:
                        _tmp = _translate(_tmp, domain=_domain, mapping=None, target_language=target_language, default=None)
                    else:
                        _tmp = _tmp()
                        _write(_tmp)
                        _tmp = None
                if (_tmp is not None):
                    if not isinstance(_tmp, unicode):
                        _tmp = str(_tmp)
                    _write(_tmp)
                u'row_errors.get(field, [])'
                _write(u'\n        ')
                _tmp5 = _lookup_attr(row_errors, 'get')(field, [])
                error = None
                (_tmp5, _tmp6, ) = repeat.insert('error', _tmp5)
                for error in _tmp5:
                    _tmp6 = (_tmp6 - 1)
                    attrs = _attrs_4361423312
                    u'error'
                    _write(u'<div class="grid_error">')
                    _tmp7 = error
                    _tmp = _tmp7
                    if (_tmp.__class__ not in (str, unicode, int, float, )):
                        try:
                            _tmp = _tmp.__html__
                        except:
                            _tmp = _translate(_tmp, domain=_domain, mapping=None, target_language=target_language, default=None)
                        else:
                            _tmp = _tmp()
                            _write(_tmp)
                            _tmp = None
                    if (_tmp is not None):
                        if not isinstance(_tmp, unicode):
                            _tmp = str(_tmp)
                        if ('&' in _tmp):
                            if (';' in _tmp):
                                _tmp = _re_amp.sub('&amp;', _tmp)
                            else:
                                _tmp = _tmp.replace('&', '&amp;')
                        if ('<' in _tmp):
                            _tmp = _tmp.replace('<', '&lt;')
                        if ('>' in _tmp):
                            _tmp = _tmp.replace('>', '&gt;')
                        _write(_tmp)
                    _write(u'</div>')
                    if (_tmp6 == 0):
                        break
                    _write(' ')
                _write(u'\n      </td>')
                if (_tmp4 == 0):
                    break
                _write(' ')
            _write(u'\n    </tr>\n  ')
            if (_tmp2 == 0):
                break
            _write(' ')
        _write(u'\n</tbody>\n</table>')
        return _out.getvalue()
    return render

__filename__ = '/Users/gawel/py/formalchemy_project/pyramid_formalchemy/pyramid_formalchemy/templates/forms/grid.pt'
registry[(None, True, '1488bdb950901f8f258549439ef6661a49aae984')] = bind()

########NEW FILE########
__FILENAME__ = grid_readonly.pt
registry = dict(version=0)
def bind():
    from cPickle import loads as _loads
    _lookup_attr = _loads('cchameleon.core.codegen\nlookup_attr\np1\n.')
    _init_scope = _loads('cchameleon.core.utils\necontext\np1\n.')
    _re_amp = _loads("cre\n_compile\np1\n(S'&(?!([A-Za-z]+|#[0-9]+);)'\np2\nI0\ntRp3\n.")
    _attrs_4356384400 = _loads('(dp1\nVclass\np2\nVui-widget-header\np3\ns.')
    _attrs_4356384336 = _loads('(dp1\n.')
    _attrs_4356384272 = _loads('(dp1\n.')
    _attrs_4356384528 = _loads('(dp1\n.')
    _init_stream = _loads('cchameleon.core.generation\ninitialize_stream\np1\n.')
    _attrs_4356384912 = _loads('(dp1\n.')
    _attrs_4356384720 = _loads('(dp1\n.')
    _init_default = _loads('cchameleon.core.generation\ninitialize_default\np1\n.')
    _attrs_4356384016 = _loads('(dp1\n.')
    _init_tal = _loads('cchameleon.core.generation\ninitialize_tal\np1\n.')
    def render(econtext, rcontext=None):
        macros = econtext.get('macros')
        _translate = econtext.get('_translate')
        _slots = econtext.get('_slots')
        target_language = econtext.get('target_language')
        u'_init_stream()'
        (_out, _write, ) = _init_stream()
        u'_init_tal()'
        (_attributes, repeat, ) = _init_tal()
        u'_init_default()'
        _default = _init_default()
        u'None'
        default = None
        u'None'
        _domain = None
        attrs = _attrs_4356384016
        _write(u'<table>\n  ')
        attrs = _attrs_4356384272
        _write(u'<thead>\n    ')
        attrs = _attrs_4356384400
        u"''"
        _write(u'<tr class="ui-widget-header">\n      ')
        _default.value = default = ''
        u'collection.render_fields.itervalues()'
        _tmp1 = _lookup_attr(_lookup_attr(econtext['collection'], 'render_fields'), 'itervalues')()
        field = None
        (_tmp1, _tmp2, ) = repeat.insert('field', _tmp1)
        for field in _tmp1:
            _tmp2 = (_tmp2 - 1)
            u'field.label()'
            _content = _lookup_attr(field, 'label')()
            attrs = _attrs_4356384528
            u'_content'
            _write(u'<th>')
            _tmp3 = _content
            _tmp = _tmp3
            if (_tmp.__class__ not in (str, unicode, int, float, )):
                try:
                    _tmp = _tmp.__html__
                except:
                    _tmp = _translate(_tmp, domain=_domain, mapping=None, target_language=target_language, default=None)
                else:
                    _tmp = _tmp()
                    _write(_tmp)
                    _tmp = None
            if (_tmp is not None):
                if not isinstance(_tmp, unicode):
                    _tmp = str(_tmp)
                if ('&' in _tmp):
                    if (';' in _tmp):
                        _tmp = _re_amp.sub('&amp;', _tmp)
                    else:
                        _tmp = _tmp.replace('&', '&amp;')
                if ('<' in _tmp):
                    _tmp = _tmp.replace('<', '&lt;')
                if ('>' in _tmp):
                    _tmp = _tmp.replace('>', '&gt;')
                _write(_tmp)
            _write(u'</th>')
            if (_tmp2 == 0):
                break
            _write(' ')
        _write(u'\n    </tr>\n  </thead>\n  ')
        attrs = _attrs_4356384336
        u'collection.rows'
        _write(u'<tbody>\n    ')
        _tmp1 = _lookup_attr(econtext['collection'], 'rows')
        row = None
        (_tmp1, _tmp2, ) = repeat.insert('row', _tmp1)
        for row in _tmp1:
            _tmp2 = (_tmp2 - 1)
            u'collection._set_active(row)'
            _write(u'')
            dummy = _lookup_attr(econtext['collection'], '_set_active')(row)
            attrs = _attrs_4356384720
            u"ui-widget-${repeat.row.even and 'even' or 'odd'}"
            _write(u'<tr')
            _tmp3 = ('%s%s' % (u'ui-widget-', ((_lookup_attr(repeat.row, 'even') and 'even') or 'odd'), ))
            if (_tmp3 is _default):
                _tmp3 = None
            if ((_tmp3 is not None) and (_tmp3 is not False)):
                if (_tmp3.__class__ not in (str, unicode, int, float, )):
                    _tmp3 = unicode(_translate(_tmp3, domain=_domain, mapping=None, target_language=target_language, default=None))
                else:
                    if not isinstance(_tmp3, unicode):
                        _tmp3 = str(_tmp3)
                if ('&' in _tmp3):
                    if (';' in _tmp3):
                        _tmp3 = _re_amp.sub('&amp;', _tmp3)
                    else:
                        _tmp3 = _tmp3.replace('&', '&amp;')
                if ('<' in _tmp3):
                    _tmp3 = _tmp3.replace('<', '&lt;')
                if ('>' in _tmp3):
                    _tmp3 = _tmp3.replace('>', '&gt;')
                if ('"' in _tmp3):
                    _tmp3 = _tmp3.replace('"', '&quot;')
                _write(((' class="' + _tmp3) + '"'))
            u"''"
            _write(u'>\n        ')
            _default.value = default = ''
            u'collection.render_fields.itervalues()'
            _tmp3 = _lookup_attr(_lookup_attr(econtext['collection'], 'render_fields'), 'itervalues')()
            field = None
            (_tmp3, _tmp4, ) = repeat.insert('field', _tmp3)
            for field in _tmp3:
                _tmp4 = (_tmp4 - 1)
                u'field.render_readonly()'
                _content = _lookup_attr(field, 'render_readonly')()
                attrs = _attrs_4356384912
                u'_content'
                _write(u'<td>')
                _tmp5 = _content
                _tmp = _tmp5
                if (_tmp.__class__ not in (str, unicode, int, float, )):
                    try:
                        _tmp = _tmp.__html__
                    except:
                        _tmp = _translate(_tmp, domain=_domain, mapping=None, target_language=target_language, default=None)
                    else:
                        _tmp = _tmp()
                        _write(_tmp)
                        _tmp = None
                if (_tmp is not None):
                    if not isinstance(_tmp, unicode):
                        _tmp = str(_tmp)
                    _write(_tmp)
                _write(u'</td>')
                if (_tmp4 == 0):
                    break
                _write(' ')
            _write(u'\n      </tr>\n    ')
            if (_tmp2 == 0):
                break
            _write(' ')
        _write(u'\n  </tbody>\n</table>')
        return _out.getvalue()
    return render

__filename__ = '/Users/gawel/py/formalchemy_project/pyramid_formalchemy/pyramid_formalchemy/templates/forms/grid_readonly.pt'
registry[(None, True, '1488bdb950901f8f258549439ef6661a49aae984')] = bind()

########NEW FILE########
__FILENAME__ = utils
# -*- coding: utf-8 -*-
from formalchemy.templates import TemplateEngine as BaseTemplateEngine
from formalchemy import config
from formalchemy import fatypes
from webhelpers.html import literal
from pyramid.renderers import render

class TemplateEngine(BaseTemplateEngine):
    """A template engine aware of pyramid"""

    def __init__(self, *args, **kwargs):
        """Do nothing. Almost all the mechanism is deleged to pyramid.renderers"""

    def render(self, name=None, renderer=None, template=None, **kwargs):
        renderer = renderer or template
        if renderer is None:
            name = name.strip('/')
            if not name.endswith('.pt'):
                name = '%s.pt' % name
            renderer = 'pyramid_formalchemy:templates/forms/%s' % name
        kwargs.update(dict(
            fatypes=fatypes,
        ))
        return literal(render(renderer, kwargs, request=kwargs.get('request')))

config.engine = TemplateEngine()

########NEW FILE########
__FILENAME__ = views
# -*- coding: utf-8 -*-
import zope.component.event
from zope.interface import alsoProvides
from webhelpers.paginate import Page
from sqlalchemy.orm import class_mapper
from formalchemy.fields import _pk
from formalchemy.fields import _stringify
from formalchemy.i18n import get_translator
from formalchemy.fields import Field
from formalchemy import fatypes
from pyramid.renderers import get_renderer
from pyramid.response import Response
from pyramid.security import has_permission
from pyramid.i18n import get_locale_name
from pyramid import httpexceptions as exc
from pyramid.exceptions import NotFound
from pyramid_formalchemy.utils import TemplateEngine
from pyramid_formalchemy.i18n import I18NModel
from pyramid_formalchemy import events
from pyramid_formalchemy import actions

try:
    from formalchemy.ext.couchdb import Document
except ImportError:
    Document = None

try:
    import simplejson as json
except ImportError:
    import json

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

def set_language(request):
    """Set the _LOCALE_ cookie used by ``pyramid``"""
    resp = exc.HTTPFound(location=request.referer or request.application_url)
    resp.set_cookie('_LOCALE_', request.GET.get('_LOCALE_', 'en'))
    return resp

def set_theme(request):
    """Set the _THEME_ cookie used by ``pyramid_formalchemy`` to get a
    jquery.ui theme"""
    resp = exc.HTTPFound(location=request.referer or request.application_url)
    resp.set_cookie('_THEME_', request.GET.get('_THEME_', 'smoothness'))
    return resp

class ModelView(object):
    """A RESTful view bound to a model"""

    engine = TemplateEngine()
    pager_args = dict(link_attr={'class': 'ui-pager-link ui-state-default ui-corner-all'},
                      curpage_attr={'class': 'ui-pager-curpage ui-state-highlight ui-corner-all'})

    actions_categories = ('buttons',)
    defaults_actions = actions.defaults_actions

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.session = request.session_factory

        self.fieldset_class = request.forms.FieldSet
        self.grid_class = request.forms.Grid
        if '_LOCALE_' not in request.cookies:
            locale = get_locale_name(request)
            request.cookies['_LOCALE_'] = locale
        if '_THEME_' not in request.cookies:
            theme = request.registry.settings.get('default_theme_name', 'smoothness')
            request.cookies['_THEME_'] = theme

    def models(self, **kwargs):
        """Models index page"""
        request = self.request
        models = []
        if isinstance(request.models, list):
            for model in request.models:
                if has_permission('view', model, request) or not hasattr(model, '__acl__'):
                    key = model.__name__
                    models.append(model)
        else:
            for key, obj in request.models.__dict__.iteritems():
                if not key.startswith('_'):
                    if Document is not None:
                        try:
                            if issubclass(obj, Document):
                                if has_permission('view', obj, request) or not hasattr(model, '__acl__'):
                                    models.append(obj)
                                continue
                        except:
                            pass
                    try:
                        class_mapper(obj)
                    except:
                        continue
                    if not isinstance(obj, type):
                        continue
                    if has_permission('view', obj, request) or not hasattr(obj, '__acl__'):
                        models.append(obj)

        results = {}
        for m in models:
            if request.format == 'html':
                url = request.fa_url(m.__name__)
            else:
                url = request.fa_url(m.__name__, request.format)
            results[I18NModel(m, request).plural] = url

        if kwargs.get('json'):
            return results
        return self.render(models=results)

    def sync(self, fs, id=None):
        """sync a record. If ``id`` is None add a new record else save current one."""
        if id:
            self.session.merge(fs.model)
        else:
            self.session.add(fs.model)
        event = events.AfterSyncEvent(fs.model, fs, self.request)
        zope.component.event.objectEventNotify(event)

    def validate(self, fs):
        """validate fieldset"""
        event = events.BeforeValidateEvent(fs.model, fs, self.request)
        zope.component.event.objectEventNotify(event)
        return fs.validate()

    def breadcrumb(self, fs=None, **kwargs):
        """return items to build the breadcrumb"""
        items = []
        request = self.request
        model_name = request.model_name
        id = request.model_id
        items.append((request.fa_url(), 'root', 'root_url'))
        if request.model_name:
            items.append((request.fa_url(model_name), model_name, 'model_url'))
        if id and hasattr(fs.model, '__unicode__'):
            items.append((request.fa_url(model_name, id), u'%s' % self.context.get_instance(), 'instance_url'))
        elif id:
            items.append((request.fa_url(model_name, id), id, 'instance_url'))
        return items

    def render(self, **kwargs):
        """render the form as html or json"""
        request = self.request
        if request.format != 'html':
            meth = getattr(self, 'render_%s_format' % request.format, None)
            if meth is not None:
                return meth(**kwargs)
            else:
                raise NotFound()

        if request.model_class:
            request.model_class = model_class = I18NModel(request.model_class, request)
            request.model_label = model_label = model_class.label
            request.model_plural = model_plural = model_class.plural
        else:
            model_class = request.model_class
            model_label = model_plural = ''
        self.update_resources()
        kwargs.update(
                      main = get_renderer('pyramid_formalchemy:templates/admin/master.pt').implementation(),
                      model_class=model_class,
                      model_name=request.model_name,
                      model_label=model_label,
                      model_plural=model_plural,
                      breadcrumb=self.breadcrumb(**kwargs),
                      actions=request.actions,
                      F_=get_translator()),
        return kwargs

    def render_grid(self, **kwargs):
        """render the grid as html or json"""
        return self.render(is_grid=True, **kwargs)

    def render_json_format(self, fs=None, **kwargs):
        request = self.request
        request.override_renderer = 'json'
        if fs is not None:
            data = fs.to_dict(with_prefix=request.params.get('with_prefix', False))
            pk = _pk(fs.model)
            if pk:
                if 'id' not in data:
                    data['id'] = pk
                data['absolute_url'] = request.fa_url(request.model_name, 'json', pk)
        else:
            data = {}
        data.update(kwargs)
        return data

    def render_xhr_format(self, fs=None, **kwargs):
        self.request.response_content_type = 'text/html'
        if fs is not None:
            if 'field' in self.request.GET:
                field_name = self.request.GET.get('field')
                fields = fs.render_fields
                if field_name in fields:
                    field = fields[field_name]
                    return Response(field.render())
                else:
                    raise NotFound()
            return Response(fs.render())
        return Response('')

    def get_page(self, **kwargs):
        """return a ``webhelpers.paginate.Page`` used to display ``Grid``.
        """
        request = self.request
        def get_page_url(page, partial=None):
            url = "%s?page=%s" % (self.request.path, page)
            if partial:
                url += "&partial=1"
            return url
        options = dict(page=int(request.GET.get('page', '1')),
                       url=get_page_url)
        options.update(kwargs)
        if 'collection' not in options:
            query = self.session.query(request.model_class)
            options['collection'] = request.query_factory(request, query)
        collection = options.pop('collection')
        return Page(collection, **options)

    def get_fieldset(self, suffix='', id=None):
        """return a ``FieldSet`` object bound to the correct record for ``id``.
        """
        request = self.request
        model = id and request.model_instance or request.model_class
        form_name = request.model_name + suffix
        fs = getattr(request.forms, form_name, None)
        if fs is None:
            fs = getattr(request.forms, request.model_name,
                         self.fieldset_class)
        if isinstance(fs, type) and issubclass(fs, self.fieldset_class):
            fs = fs(request.model_class)
            if not isinstance(request.forms, list):
                # add default fieldset to form module eg: caching
                setattr(request.forms, form_name, fs)
        fs.engine = fs.engine or self.engine
        fs = id and fs.bind(model) or fs.copy()
        fs._request = request
        return fs

    def get_grid(self):
        """return a Grid object"""
        request = self.request
        model_name = request.model_name
        form_name = '%sGrid' % model_name
        if hasattr(request.forms, form_name):
            g = getattr(request.forms, form_name)
            g.engine = g.engine or self.engine
            g.readonly = True
            g._request = self.request
            self.update_grid(g)
            return g
        model = self.context.get_model()
        grid = self.grid_class(model)
        grid.engine = self.engine
        if not isinstance(request.forms, list):
            # add default grid to form module eg: caching
            setattr(request.forms, form_name, grid)
        grid = grid.copy()
        grid._request = self.request
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
                ''' % dict(url=self.request.fa_url(self.request.model_name, _pk(item), 'edit'),
                            label=get_translator(request=self.request)('edit'))
            def delete_link():
                return lambda item: '''
                <form action="%(url)s" method="POST" class="ui-grid-icon ui-state-error ui-corner-all">
                <input type="submit" class="ui-icon ui-icon-circle-close" title="%(label)s" value="%(label)s" />
                </form>
                ''' % dict(url=self.request.fa_url(self.request.model_name, _pk(item), 'delete'),
                           label=get_translator(request=self.request)('delete'))
            grid.append(Field('edit', fatypes.String, edit_link()))
            grid.append(Field('delete', fatypes.String, delete_link()))
            grid.readonly = True

    def update_resources(self):
        """A hook to add some fanstatic resources"""
        pass

    @actions.action()
    def listing(self, **kwargs):
        """listing page"""
        page = self.get_page(**kwargs)
        fs = self.get_grid()
        fs = fs.bind(instances=page, request=self.request)
        fs.readonly = True

        event = events.BeforeRenderEvent(self.request.model_class(), self.request, fs=fs, page=page)
        alsoProvides(event, events.IBeforeListingRenderEvent)
        zope.component.event.objectEventNotify(event)

        if self.request.format == 'json':
            values = []
            request = self.request
            for item in page:
                pk = _pk(item)
                fs._set_active(item)
                value = dict(id=pk,
                             absolute_url=request.fa_url(request.model_name, pk))
                if 'jqgrid' in request.GET:
                    fields = [_stringify(field.render_readonly()) for field in fs.render_fields.values()]
                    value['cell'] = [pk] + fields
                else:
                    value.update(fs.to_dict(with_prefix=bool(request.params.get('with_prefix'))))
                values.append(value)
            return self.render_json_format(rows=values,
                                           records=len(values),
                                           total=page.page_count,
                                           page=page.page)
        if 'pager' not in kwargs:
            pager = page.pager(**self.pager_args)
        else:
            pager = kwargs.pop('pager')
        return self.render_grid(fs=fs, id=None, pager=pager)

    @actions.action()
    def show(self):
        id = self.request.model_id
        fs = self.get_fieldset(suffix='View', id=id)
        fs.readonly = True

        event = events.BeforeRenderEvent(self.request.model_instance, self.request, fs=fs)
        alsoProvides(event, events.IBeforeShowRenderEvent)
        zope.component.event.objectEventNotify(event)

        return self.render(fs=fs, id=id)

    @actions.action()
    def new(self):
        fs = self.get_fieldset(suffix='Add')
        fs = fs.bind(session=self.session, request=self.request)

        event = events.BeforeRenderEvent(fs.model, self.request, fs=fs)
        alsoProvides(event, events.IBeforeEditRenderEvent)
        zope.component.event.objectEventNotify(event)

        return self.render(fs=fs, id=None)

    @actions.action('new')
    def create(self):
        request = self.request
        fs = self.get_fieldset(suffix='Add')

        event = events.BeforeRenderEvent(fs.model, self.request, fs=fs)
        alsoProvides(event, events.IBeforeEditRenderEvent)
        zope.component.event.objectEventNotify(event)

        if request.format == 'json' and request.method == 'PUT':
            data = json.load(request.body_file)
        elif request.content_type == 'application/json':
            data = json.load(request.body_file)
        else:
            data = request.POST

        with_prefix = True
        if request.format == 'json':
            with_prefix = bool(request.params.get('with_prefix'))

        fs = fs.bind(data=data, session=self.session, request=request, with_prefix=with_prefix)
        #try:
        #    fs = fs.bind(data=data, session=self.session, request=request, with_prefix=with_prefix)
        #except Exception:
        #    # non SA forms
        #    fs = fs.bind(self.context.get_model(), data=data, session=self.session,
        #                 request=request, with_prefix=with_prefix)

        if self.validate(fs):
            fs.sync()
            self.sync(fs)
            self.session.flush()
            if request.format in ('html', 'xhr'):
                if request.is_xhr or request.format == 'xhr':
                    return Response(content_type='text/plain')
                next = request.POST.get('next') or request.fa_url(request.model_name)
                return exc.HTTPFound(
                    location=next)
            else:
                fs.rebind(fs.model, data=None)
                return self.render(fs=fs)
        return self.render(fs=fs, id=None)

    @actions.action()
    def edit(self):
        id = self.request.model_id
        fs = self.get_fieldset(suffix='Edit', id=id)

        event = events.BeforeRenderEvent(self.request.model_instance, self.request, fs=fs)
        alsoProvides(event, events.IBeforeEditRenderEvent)
        zope.component.event.objectEventNotify(event)

        return self.render(fs=fs, id=id)

    @actions.action('edit')
    def update(self):
        request = self.request
        id = request.model_id
        fs = self.get_fieldset(suffix='Edit', id=id)

        event = events.BeforeRenderEvent(self.request.model_instance, self.request, fs=fs)
        alsoProvides(event, events.IBeforeEditRenderEvent)
        zope.component.event.objectEventNotify(event)

        if request.format == 'json' and request.method == 'PUT':
            data = json.load(request.body_file)
        elif request.content_type == 'application/json':
            data = json.load(request.body_file)
        else:
            data = request.POST

        with_prefix = True
        if request.format == 'json':
            with_prefix = bool(request.params.get('with_prefix'))

        fs = fs.bind(request=request, with_prefix=with_prefix)
        if self.validate(fs):
            fs.sync()
            self.sync(fs, id)
            self.session.flush()
            if request.format in ('html', 'xhr'):
                if request.is_xhr or request.format == 'xhr':
                    return Response(content_type='text/plain')
                return exc.HTTPFound(
                        location=request.fa_url(request.model_name, _pk(fs.model)))
            else:
                return self.render(fs=fs, status=0)
        if request.format == 'html':
            return self.render(fs=fs, id=id)
        else:
            return self.render(fs=fs, status=1)

    def delete(self):
        request = self.request
        record = request.model_instance

        event = events.BeforeDeleteEvent(record, self.request)
        zope.component.event.objectEventNotify(event)

        if record:
            self.session.delete(record)
        else:
            raise NotFound()

        if request.format == 'html':
            if request.is_xhr or request.format == 'xhr':
                return Response(content_type='text/plain')
            return exc.HTTPFound(location=request.fa_url(request.model_name))
        return self.render(id=request.model_id)

    def autocomplete(self, *args, **kwargs):
        filter_term = "%s%%" % self.request.params.get('term')
        filter_attr = getattr(self.request.model_class, self.request.params.get('filter_by'))
        query = self.session.query(self.request.model_class.id, filter_attr).filter(filter_attr.ilike(filter_term))
        items = self.request.query_factory(self.request, query)
        return Response(json.dumps([{'label' : x[1],
                                     'value' : x[0]} for x in items ]),
                        content_type='text/plain')


########NEW FILE########
