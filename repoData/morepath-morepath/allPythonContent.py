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

import os
import shutil
import sys
import tempfile

from optparse import OptionParser

tmpeggs = tempfile.mkdtemp()

usage = '''\
[DESIRED PYTHON FOR BUILDOUT] bootstrap.py [options]

Bootstraps a buildout-based project.

Simply run this script in a directory containing a buildout.cfg, using the
Python that you want bin/buildout to use.

Note that by using --find-links to point to local resources, you can keep 
this script from going over the network.
'''

parser = OptionParser(usage=usage)
parser.add_option("-v", "--version", help="use a specific zc.buildout version")

parser.add_option("-t", "--accept-buildout-test-releases",
                  dest='accept_buildout_test_releases',
                  action="store_true", default=False,
                  help=("Normally, if you do not specify a --version, the "
                        "bootstrap script and buildout gets the newest "
                        "*final* versions of zc.buildout and its recipes and "
                        "extensions for you.  If you use this flag, "
                        "bootstrap and buildout will get the newest releases "
                        "even if they are alphas or betas."))
parser.add_option("-c", "--config-file",
                  help=("Specify the path to the buildout configuration "
                        "file to be used."))
parser.add_option("-f", "--find-links",
                  help=("Specify a URL to search for buildout releases"))


options, args = parser.parse_args()

######################################################################
# load/install setuptools

to_reload = False
try:
    import pkg_resources
    import setuptools
except ImportError:
    ez = {}

    try:
        from urllib.request import urlopen
    except ImportError:
        from urllib2 import urlopen

    # XXX use a more permanent ez_setup.py URL when available.
    exec(urlopen('https://bitbucket.org/pypa/setuptools/raw/0.7.2/ez_setup.py'
                ).read(), ez)
    setup_args = dict(to_dir=tmpeggs, download_delay=0)
    ez['use_setuptools'](**setup_args)

    if to_reload:
        reload(pkg_resources)
    import pkg_resources
    # This does not (always?) update the default working set.  We will
    # do it.
    for path in sys.path:
        if path not in pkg_resources.working_set.entries:
            pkg_resources.working_set.add_entry(path)

######################################################################
# Install buildout

ws = pkg_resources.working_set

cmd = [sys.executable, '-c',
       'from setuptools.command.easy_install import main; main()',
       '-mZqNxd', tmpeggs]

find_links = os.environ.get(
    'bootstrap-testing-find-links',
    options.find_links or
    ('http://downloads.buildout.org/'
     if options.accept_buildout_test_releases else None)
    )
if find_links:
    cmd.extend(['-f', find_links])

setuptools_path = ws.find(
    pkg_resources.Requirement.parse('setuptools')).location

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
        search_path=[setuptools_path])
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

import subprocess
if subprocess.call(cmd, env=dict(os.environ, PYTHONPATH=setuptools_path)) != 0:
    raise Exception(
        "Failed to execute command:\n%s",
        repr(cmd)[1:-1])

######################################################################
# Import and run buildout

ws.add_entry(tmpeggs)
ws.require(requirement)
import zc.buildout.buildout

if not [a for a in args if '=' not in a]:
    args.append('bootstrap')

# if -c was provided, we push it back into args for buildout' main function
if options.config_file is not None:
    args[0:0] = ['-c', options.config_file]

zc.buildout.buildout.main(args)
shutil.rmtree(tmpeggs)

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# Morepath documentation build configuration file, created by
# sphinx-quickstart on Tue Aug  6 12:47:25 2013.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os
import pkg_resources

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#sys.path.insert(0, os.path.abspath('.'))

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.intersphinx',
              'morepath.sphinxext']

autoclass_content = 'both'

autodoc_member_order = 'groupwise'

intersphinx_mapping = {
    'reg': ('http://reg.readthedocs.org/en/latest', None),
    'webob': ('http://docs.webob.org/en/latest', None),
    }

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'toc'

# General information about the project.
project = u'Morepath'
copyright = u'2013-2014, Morepath developers'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = pkg_resources.get_distribution('morepath').version
# The full version, including alpha/beta/rc tags.
# the full version, including alpha/beta/rc tags
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
htmlhelp_basename = 'Morepathdoc'


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
  ('index', 'Morepath.tex', u'Morepath Documentation',
   u'Morepath developers', 'manual'),
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
    ('index', 'morepath', u'Morepath Documentation',
     [u'Morepath developers'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'Morepath', u'Morepath Documentation',
   u'Morepath developers', 'Morepath', 'One line description of project.',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'

########NEW FILE########
__FILENAME__ = extra
import impossible_import_error_generating_thing_should_be_ignored

########NEW FILE########
__FILENAME__ = m
import morepath

app = morepath.App()

class Foo(object):
    pass

@app.path(path='foo', model=Foo)
def get_foo():
    return Foo()

########NEW FILE########
__FILENAME__ = app
from .mount import Mount
from .request import Request
from .traject import Traject
from .config import Configurable
from .settings import SettingSectionContainer
from .converter import ConverterRegistry
from .error import MountError
from .tween import TweenRegistry
from morepath import generic
from reg import ClassRegistry, Lookup, CachingClassLookup, implicit
import venusian
from .reify import reify


class AppBase(Configurable, ClassRegistry, ConverterRegistry,
              TweenRegistry):
    """Base for application objects.

    Extends :class:`morepath.config.Configurable`,
    :class:`reg.ClassRegistry` and
    :class:`morepath.converter.ConverterRegistry`.

    The application base is split from the :class:`App`
    class so that we can have an :class:`App` class that automatically
    extends from ``global_app``, which defines the Morepath framework
    itself.  Normally you would use :class:`App` instead this one.

    AppBase can be used as a WSGI application, i.e. it can be called
    with ``environ`` and ``start_response`` arguments.
    """
    def __init__(self, name=None, extends=None, variables=None,
                 testing_config=None):
        """
        :param name: A name for this application. This is used in
          error reporting.
        :type name: str
        :param extends: :class:`App` objects that this
          app extends/overrides.
        :type extends: list, :class:`App` or ``None``
        :param variables: variable names that
          this application expects when mounted. Optional.
        :type variables: list or set
        :param testing_config: a :class:`morepath.Config` that actions
          are added to directly, instead of waiting for
          a scanning phase. This is handy during testing. If you want to
          use decorators inline in a test function, supply a
          ``testing_config``. It's not useful outside of tests. Optional.
        """
        ClassRegistry.__init__(self)
        Configurable.__init__(self, extends, testing_config)
        ConverterRegistry.__init__(self)
        TweenRegistry.__init__(self)
        self.name = name
        if variables is None:
            variables = set()
        self._variables = set(variables)
        self.traject = Traject()
        self.settings = SettingSectionContainer()
        self._mounted = {}
        self._variables = variables or set()
        if not variables:
            self._app_mount = self.mounted()
        else:
            self._app_mount = FailingWsgi(self)
        # allow being scanned by venusian
        venusian.attach(self, callback)

    def __repr__(self):
        if self.name is None:
            return '<morepath.App at 0x%x>' % id(self)
        return '<morepath.App %r>' % self.name

    def clear(self):
        """Clear all registrations in this application.
        """
        ClassRegistry.clear(self)
        Configurable.clear(self)
        TweenRegistry.clear(self)
        self.traject = Traject()
        self.settings = SettingSectionContainer()
        self._mounted = {}

    def actions(self):
        yield self.function(generic.settings), lambda: self.settings

    @reify
    def lookup(self):
        """Get the :class:`reg.Lookup` for this application.

        :returns: a :class:`reg.Lookup` instance.
        """
        return Lookup(CachingClassLookup(self))

    def set_implicit(self):
        """Set app's lookup as implicit reg lookup.

        Only does something if implicit mode is enabled. If disabled,
        has no effect.
        """

    def request(self, environ):
        """Create a :class:`Request` given WSGI environment.

        :param environ: WSGI environment
        :returns: :class:`morepath.Request` instance
        """
        request = Request(environ)
        request.lookup = self.lookup
        return request

    def mounted(self, **context):
        """Create :class:`morepath.mount.Mount` for application.

        :param kw: the arguments with which to mount the app.
        :returns: :class:`morepath.mount.Mount` instance. This is
          a WSGI application.
        """
        for name in self._variables:
            if name not in context:
                raise MountError(
                    "Cannot mount app without context variable: %s" % name)
        return Mount(self, lambda: context, {})

    def __call__(self, environ, start_response):
        """This app as a WSGI application.

        This is only possible when the app expects no variables; if it
        does, use ``mount()`` to create a WSGI app first.
        """
        return self._app_mount(environ, start_response)

    def mount_variables(self):
        return self._variables


class FailingWsgi(object):
    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        raise MountError(
            "Cannot run WSGI app as this app requires "
            "mount variables: %s" % ', '.join(
                self.app.mount_variables()))


class App(AppBase):
    """A Morepath-based application object.

    Extends :class:`AppBase` and through it
    :class:`morepath.config.Configurable`, :class:`reg.ClassRegistry`
    and :class:`morepath.converter.ConverterRegistry`.

    You can configure an application using Morepath decorator directives.

    An application can extend one or more other applications, if
    desired.  All morepath App's descend from ``global_app`` however,
    which contains the base configuration of the Morepath framework.

    Conflicting configuration within an app is automatically
    rejected. An extended app cannot conflict with the apps it is
    extending however; instead configuration is overridden.
    """
    def __init__(self, name=None, extends=None, variables=None,
                 testing_config=None):
        """
        :param name: A name for this application. This is used in
          error reporting.
        :type name: str
        :param extends: :class:`App` objects that this
          app extends/overrides.
        :type extends: list, :class:`App` or ``None``
        :param variables: variable names that
          this application expects when mounted. Optional.
        :type variables: list or set
        :param testing_config: a :class:`morepath.Config` that actions
          are added to directly, instead of waiting for
          a scanning phase. This is handy during testing. If you want to
          use decorators inline in a test function, supply a
          ``testing_config``. It's not useful outside of tests. Optional.
        """
        if not extends:
            extends = [global_app]
        super(App, self).__init__(name, extends, variables, testing_config)
        # XXX why does this need to be repeated?
        venusian.attach(self, callback)


def callback(scanner, name, obj):
    scanner.config.configurable(obj)


def set_implicit(self):
    implicit.lookup = self.lookup


def enable_implicit():
    AppBase.set_implicit = set_implicit


def no_set_implicit(self):
    pass


def disable_implicit():
    AppBase.set_implicit = no_set_implicit


global_app = AppBase('global_app')
"""The global app object.

Instance of :class:`AppBase`.

This is the application object that the Morepath framework is
registered on. It's automatically included in the extends of any
:class:`App`` object.

You could add configuration to ``global_app`` but it is recommended
you don't do so. Instead to extend or override the framework you can
create your own :class:`App` with this additional configuration.
"""

########NEW FILE########
__FILENAME__ = compat
# taken from pyramid.compat

import sys

# True if we are running on Python 3.
PY3 = sys.version_info[0] == 3


if PY3:  # pragma: no cover
    text_type = str
else:
    text_type = unicode


def bytes_(s, encoding='latin-1', errors='strict'):
    """ If ``s`` is an instance of ``text_type``, return
    ``s.encode(encoding, errors)``, otherwise return ``s``"""
    if isinstance(s, text_type):  # pragma: no cover
        return s.encode(encoding, errors)
    return s

########NEW FILE########
__FILENAME__ = config
import sys
from copy import copy
import venusian
from .error import (ConflictError, DirectiveError, DirectiveReportError)
from .toposort import topological_sort
from .framehack import caller_package


class Configurable(object):
    """Object to which configuration actions apply.

    Actions can be added to a configurable.

    Once all actions are added, the configurable is executed.
    This checks for any conflicts between configurations and
    the configurable is expanded with any configurations from its
    extends list. Then the configurable is performed, meaning all
    its actions are performed (to it).
    """
    def __init__(self, extends=None, testing_config=None):
        """
        :param extends:
          the configurables that this configurable extends. Optional.
        :type extends: list of configurables, single configurable.
        :param testing_config:
          We can pass a config object used during testing. This causes
          the actions to be issued against the configurable directly
          instead of waiting for Venusian scanning. This allows
          the use of directive decorators in tests where scanning is
          not an option. Optional, default no testing config.
        """
        if extends is None:
            extends = []
        if not isinstance(extends, list):
            extends = [extends]
        self.extends = extends
        self._testing_config = testing_config
        self.clear()
        if self._testing_config:
            self._testing_config.configurable(self)

    @property
    def testing_config(self):
        return self._testing_config

    @testing_config.setter
    def testing_config(self, config):
        self._testing_config = config
        config.configurable(self)

    def clear(self):
        """Clear any previously registered actions.

        This is normally not invoked directly, instead is called
        indirectly by :meth:`Config.commit`.
        """
        self._grouped_actions = {}
        self._class_to_actions = {}

    def actions(self):
        """Actions the configurable wants to register as it is scanned.

        A configurable may want to register some actions as it is registered
        with the config system.

        Should return a sequence of action, obj tuples.
        """
        return []

    def group_actions(self):
        """Group actions into :class:`Actions` by class.
        """
        # grouped actions by class (in fact deepest base class before
        # Directive)
        d = self._grouped_actions
        # make sure we don't forget about action classes in extends
        for configurable in self.extends:
            for action_class in configurable.action_classes():
                if action_class not in d:
                    d[action_class] = []
        # do the final grouping into Actions objects
        self._class_to_actions = {}
        for action_class, actions in d.items():
            self._class_to_actions[action_class] = Actions(
                actions, self.action_extends(action_class))

    def action_extends(self, action_class):
        """Get actions for action class in extends.
        """
        return [
            configurable._class_to_actions.get(action_class, Actions([], []))
            for configurable in self.extends]

    def action_classes(self):
        """Get action classes sorted in dependency order.
        """
        return sort_action_classes(self._class_to_actions.keys())

    def execute(self):
        """Execute actions for configurable.
        """
        self.group_actions()
        for action_class in self.action_classes():
            actions = self._class_to_actions.get(action_class)
            if actions is None:
                continue
            actions.prepare(self)
            actions.perform(self)

    def action(self, action, obj):
        """Register an action with configurable.

        This is normally not invoked directly, instead is called
        indirectly by :meth:`Config.commit`.

        :param action: The action to register with the configurable.
        :param obj: The object that this action is performed on.
        """
        self._grouped_actions.setdefault(
            group_key(action), []).append((action, obj))


def group_key(action):
    """We group actions by their deepest base class that's still a real action.

    This way subclasses of for instance the ViewDirective still
    group with the ViewDirective, so that conflicts can be detected.
    """
    found = None
    for c in action.__class__.__mro__:
        if c is Directive or c is Action:
            return found
        found = c
    assert False  # pragma: nocoverage


class Actions(object):
    def __init__(self, actions, extends):
        self._actions = actions
        self._action_map = {}
        self.extends = extends

    def prepare(self, configurable):
        """Prepare.

        Detect any conflicts between actions.
        Merges in configuration of what this action extends.

        Prepare must be called before perform is called.
        """
        # check for conflicts and fill action map
        discriminators = {}
        self._action_map = action_map = {}
        for action, obj in self._actions:
            id = action.identifier(configurable)
            discs = [id]
            discs.extend(action.discriminators(configurable))
            for disc in discs:
                other_action = discriminators.get(disc)
                if other_action is not None:
                    raise ConflictError([action, other_action])
                discriminators[disc] = action
            action_map[id] = action, obj
        # inherit from extends
        for extend in self.extends:
            self.combine(extend)

    def combine(self, actions):
        """Combine another prepared actions with this one.

        Those configuration actions that would conflict are taken to
        have precedence over those being combined with this one. This
        allows the extending actions to override actions in
        extended actions.

        :param actions: the :class:`Actions` to combine with this one.
        """
        to_combine = actions._action_map.copy()
        to_combine.update(self._action_map)
        self._action_map = to_combine

    def perform(self, configurable):
        """Perform actions in this configurable.

        Prepare must be called before calling this.
        """
        values = list(self._action_map.values())
        values.sort(key=lambda value: value[0].order or 0)
        for action, obj in values:
            try:
                action.perform(configurable, obj)
            except DirectiveError as e:
                raise DirectiveReportError(u"{}".format(e), action)


class Action(object):
    """A configuration action.

    A configuration action is performed on an object. Actions can
    conflict with each other based on their identifier and
    discriminators. Actions can override each other based on their
    identifier.

    Can be subclassed to implement concrete configuration actions.

    Action classes can have a ``depends`` attribute, which is a list
    of other action classes that need to be executed before this one
    is. Actions which depend on another will be executed after those
    actions are executed.
    """
    depends = []

    def __init__(self, configurable):
        """Initialize action.

        :param configurable: :class:`morepath.config.Configurable` object
          for which this action was configured.
        """
        self.configurable = configurable
        self.order = None

    def codeinfo(self):
        """Info about where in the source code the action was invoked.

        By default there is no code info.
        """
        return None

    def identifier(self, configurable):
        """Returns an immutable that uniquely identifies this config.

        :param configurable: :class:`morepath.config.Configurable` object
          for which this action is being executed.

        Used for overrides and conflict detection.
        """
        raise NotImplementedError()  # pragma: nocoverage

    def discriminators(self, configurable):
        """Returns a list of immutables to detect conflicts.

        :param configurable: :class:`morepath.config.Configurable` object
          for which this action is being executed.

        Used for additional configuration conflict detection.
        """
        return []

    def clone(self, **kw):
        """Make a clone of this action.

        Keyword parameters can be used to override attributes in clone.

        Used during preparation to create new fully prepared actions.
        """
        action = copy(self)
        for key, value in kw.items():
            setattr(action, key, value)
        return action

    def prepare(self, obj):
        """Prepare action for configuration.

        :param obj: The object that the action should be performed on.

        Returns an iterable of prepared action, obj tuples.
        """
        return [(self, obj)]

    def perform(self, configurable, obj):
        """Register whatever is being configured with configurable.

        :param configurable: the :class:`morepath.config.Configurable`
          being configured.
        :param obj: the object that the action should be performed on.
        """
        raise NotImplementedError()


class Directive(Action):
    """An :class:`Action` that can be used as a decorator.

    Extends :class:`morepath.config.Action`.

    Base class for concrete Morepath directives such as ``@app.path()``,
    ``@app.view()``, etc.

    Can be used as a Python decorator.

    Can also be used as a context manager for a Python ``with``
    statement. This can be used to provide defaults for the directives
    used within the ``with`` statements context.

    When used as a decorator this tracks where in the source code
    the directive was used for the purposes of error reporting.
    """

    def __init__(self, configurable):
        """Initialize Directive.

        :param configurable: :class:`morepath.config.Configurable` object
          for which this action was configured.
        """
        super(Directive, self).__init__(configurable)
        self.attach_info = None

    def codeinfo(self):
        """Info about where in the source code the directive was invoked.
        """
        if self.attach_info is None:
            return None
        return self.attach_info.codeinfo

    def __enter__(self):
        return DirectiveAbbreviation(self)

    def __exit__(self, type, value, tb):
        if tb is not None:
            return False

    def __call__(self, wrapped):
        """Call with function to decorate.
        """
        if self.configurable._testing_config:
            # If we are in testing mode, we immediately add the action.
            # Note that this broken for staticmethod and classmethod, unlike
            # the Venusian way, but we can fail hard when we see it.
            # It's broken for methods as well, but we cannot detect it
            # without Venusian, so unfortunately we're going to have to
            # let that pass.
            # XXX could we use something like Venusian's f_locals hack
            # to determine the class scope here and do the right thing?
            if isinstance(wrapped, staticmethod):
                raise DirectiveError(
                    "Cannot use staticmethod with testing_config.")
            elif isinstance(wrapped, classmethod):
                raise DirectiveError(
                    "Cannot use classmethod with testing_config.")
            self.configurable._testing_config.action(self, wrapped)
            return wrapped

        # Normally we only add the action through Venusian scanning.
        def callback(scanner, name, obj):
            if self.attach_info.scope == 'class':
                if isinstance(wrapped, staticmethod):
                    func = wrapped.__get__(obj)
                elif isinstance(wrapped, classmethod):
                    func = wrapped.__get__(obj, obj)
                else:
                    raise DirectiveError(
                        "Cannot use directive on normal method %s of "
                        "class %s. Use staticmethod or classmethod first."
                        % (wrapped, obj))
            else:
                func = wrapped
            scanner.config.action(self, func)
        self.attach_info = venusian.attach(wrapped, callback)
        return wrapped


class DirectiveAbbreviation(object):
    def __init__(self, directive):
        self.directive = directive

    def __call__(self, **kw):
        return self.directive.clone(**kw)


def ignore_import_error(pkg):
    # ignore import errors
    if issubclass(sys.exc_info()[0], ImportError):
        return
    raise  # reraise last exception


class Config(object):
    """Contains and executes configuration actions.

    Morepath configuration actions consist of decorator calls on
    :class:`App` instances, i.e. ``@app.view()`` and
    ``@app.path()``. The Config object can scan these configuration
    actions in a package. Once all required configuration is scanned,
    the configuration can be committed. The configuration is then
    processed, associated with :class:`morepath.config.Configurable`
    objects (i.e. :class:`App` objects), conflicts are detected,
    overrides applied, and the configuration becomes final.

    Once the configuration is committed all configured Morepath
    :class:`App` objects are ready to be served using WSGI.

    See :func:`setup`, which creates an instance with standard
    Morepath framework configuration. See also :func:`autoconfig` and
    :func:`autosetup` which help automatically load configuration from
    dependencies.
    """
    def __init__(self):
        self.configurables = []
        self.actions = []
        self.count = 0

    def scan(self, package=None, ignore=None):
        """Scan package for configuration actions (decorators).

        Register any found configuration actions with this
        object. This also includes finding any
        :class:`morepath.config.Configurable` objects.

        :param package: The Python module or package to scan. Optional; if left
          empty case the calling package is scanned.
        :ignore: A Venusian_ style ignore to ignore some modules during
          scanning. Optional.
        """
        if package is None:
            package = caller_package()
        scanner = venusian.Scanner(config=self)
        scanner.scan(package, ignore=ignore, onerror=ignore_import_error)

    def configurable(self, configurable):
        """Register a configurable with this config.

        This is normally not invoked directly, instead is called
        indirectly by :meth:`scan`.

        A :class:`App` object is a configurable.

        :param: The :class:`morepath.config.Configurable` to register.
        """
        self.configurables.append(configurable)
        for action, obj in configurable.actions():
            self.action(action, obj)

    def action(self, action, obj):
        """Register an action and obj with this config.

        This is normally not invoked directly, instead is called
        indirectly by :meth:`scan`.

        A Morepath directive decorator is an action, and obj is the
        function that was decorated.

        :param: The :class:`Action` to register.
        :obj: The object to perform action on.
        """
        action.order = self.count
        self.count += 1
        self.actions.append((action, obj))

    def prepared(self):
        """Get prepared actions before they are performed.

        The preparation phase happens as the first stage of a commit.
        This allows configuration actions to complete their
        configuration, do error checking, or transform themselves into
        different configuration actions.

        This calls :meth:`Action.prepare` on all registered configuration
        actions.

        :returns: An iterable of prepared action, obj combinations.
        """
        for action, obj in self.actions:
            for prepared, prepared_obj in action.prepare(obj):
                yield (prepared, prepared_obj)

    def commit(self):
        """Commit all configuration.

        * Clears any previous configuration from all registered
          :class:`morepath.config.Configurable` objects.
        * Prepares actions using :meth:`prepared`.
        * Actions are grouped by type of action (action class).
        * The action groups are executed in order of ``depends``
          between their action classes.
        * Per action group, configuration conflicts are detected.
        * Per action group, extending configuration is merged.
        * Finally all configuration actions are performed, completing
          the configuration process.

        This method should be called only once during the lifetime of
        a process, before the configuration is first used. After this
        the configuration is considered to be fixed and cannot be
        further modified. In tests this method can be executed
        multiple times as it automatically clears the
        configuration of its configurables first.
        """
        # clear all previous configuration; commit can only be run
        # once during runtime so it's handy to clear this out for tests
        for configurable in self.configurables:
            configurable.clear()

        for action, obj in self.prepared():
            action.configurable.action(action, obj)

        for configurable in sort_configurables(self.configurables):
            configurable.execute()


def sort_configurables(configurables):
    """Sort configurables topologically by extends.
    """
    return topological_sort(configurables, lambda c: c.extends)


def sort_action_classes(action_classes):
    """Sort action classes topologically by depends.
    """
    return topological_sort(action_classes, lambda c: c.depends)

########NEW FILE########
__FILENAME__ = converter
from reg.mapping import Map, ClassMapKey
try:
    from types import ClassType
except ImportError:
    # You're running Python 3!
    ClassType = None
from morepath.error import DirectiveError
from webob.exc import HTTPBadRequest


class Converter(object):
    """How to decode from strings to objects and back.

    Only used for decoding for a list with a single value, will
    error if more or less than one value is entered.

    Used for decoding/encoding URL parameters and path parameters.
    """
    def __init__(self, decode, encode=None):
        """Create new converter.

        :param decode: function that given string can decode them into objects.
        :param encode: function that given objects can encode them into
            strings.
        """
        fallback_encode = getattr(__builtins__, "unicode", str)
        self.single_decode = decode
        self.single_encode = encode or fallback_encode

    def decode(self, strings):
        if len(strings) != 1:
            raise ValueError
        return self.single_decode(strings[0])

    def encode(self, value):
        return [self.single_encode(value)]

    def is_missing(self, value):
        # a single value is missing if the list is empty
        return value == []

    def __eq__(self, other):
        if not isinstance(other, Converter):
            return False
        return (self.single_decode is other.single_decode and
                self.single_encode is other.single_encode)

    def __ne__(self, other):
        return not self == other


class ListConverter(object):
    """How to decode from list of strings to list of objects and back.

    Used for decoding/encoding URL parameters and path parameters.
    """
    def __init__(self, converter):
        """Create new converter.

        :param converter: the converter to use for list entries.
        """
        self.converter = converter

    def decode(self, strings):
        decode = self.converter.single_decode
        return [decode(s) for s in strings]

    def encode(self, values):
        encode = self.converter.single_encode
        return [encode(v) for v in values]

    def is_missing(self, value):
        # a list value is never missing, even if the list is empty
        return False

    def __eq__(self, other):
        if not isinstance(other, ListConverter):
            return False
        return self.converter == other.converter

    def __ne__(self, other):
        return not self == other


IDENTITY_CONVERTER = Converter(lambda s: s, lambda s: s)


class ConverterRegistry(object):
    """A registry for converters.

    Used to decode/encode URL parameters and path variables used
    by the :meth:`morepath.AppBase.path` directive.

    Is aware of inheritance.
    """
    def __init__(self):
        self._map = Map()

    def register_converter(self, type, converter):
        """Register a converter for type.

        :param type: the Python type for which to register
          the converter.
        :param converter: a :class:`morepath.Converter` instance.
        """
        self._map[ClassMapKey(type)] = converter

    def converter_for_type(self, type):
        """Get converter for type.

        Is aware of inheritance; if nothing is registered for given
        type it returns the converter registered for its base class.

        :param type: The type for which to look up the converter.
        :returns: a :class:`morepath.Converter` instance.
        """
        result = self._map.get(ClassMapKey(type))
        if result is None:
            raise DirectiveError(
                "Cannot find converter for type: %r" % type)
        return result

    def converter_for_value(self, v):
        """Get converter for value.

        Is aware of inheritance; if nothing is registered for type of
        given value it returns the converter registered for its base class.

        :param value: The value for which to look up the converter.
        :returns: a :class:`morepath.Converter` instance.
        """
        if v is None:
            return IDENTITY_CONVERTER
        try:
            return self.converter_for_type(type(v))
        except DirectiveError:
            raise DirectiveError(
                "Cannot find converter for default value: %r (%s)" %
                (v, type(v)))

    def converter_for_explicit_or_type(self, c):
        """Given a converter or a type, turn it into an explicit one.
        """
        if type(c) in [type, ClassType]:
            return self.converter_for_type(c)
        return c

    def converter_for_explicit_or_type_or_list(self, c):
        """Given a converter or type or list, turn it into an explicit one.

        :param c: can either be a converter, or a type for which
          a converter can be looked up, or a list with a converter or a type
          in it.
        :returns: a :class:`Converter` instance.
        """
        if isinstance(c, list):
            if len(c) == 0:
                c = IDENTITY_CONVERTER
            else:
                c = self.converter_for_explicit_or_type(c[0])
            return ListConverter(c)
        return self.converter_for_explicit_or_type(c)

    def explicit_converters(self, converters):
        """Given converter dictionary, make everything in it explicit.

        This means types have converters looked up for them, and
        lists are turned into :class:`ListConverter`.
        """
        return {name: self.converter_for_explicit_or_type_or_list(value) for
                name, value in converters.items()}

    def argument_and_explicit_converters(self, arguments, converters):
        """Use explict converters unless none supplied, then use default args.
        """
        result = self.explicit_converters(converters)
        for name, value in arguments.items():
            if name not in result:
                result[name] = self.converter_for_value(value)
        return result


class ParameterFactory(object):
    """Convert URL parameters.

    Given expected URL parameters, converters for them and required
    parameters, create a dictionary of converted URL parameters.
    """
    def __init__(self, parameters, converters, required, extra=False):
        """
        :param parameters: dictionary of parameter names -> default values.
        :param converters: dictionary of parameter names -> converters.
        :param required: dictionary of parameter names -> required booleans.
        :param extra: should extra unknown parameters be included?
        """
        self.parameters = parameters
        self.converters = converters
        self.required = required
        self.extra = extra

    def __call__(self, url_parameters):
        """Convert URL parameters to Python dictionary with values.
        """
        result = {}
        for name, default in self.parameters.items():
            value = url_parameters.getall(name)
            converter = self.converters.get(name, IDENTITY_CONVERTER)
            if converter.is_missing(value):
                if name in self.required:
                    raise HTTPBadRequest(
                        "Required URL parameter missing: %s" %
                        name)
                result[name] = default
                continue
            try:
                result[name] = converter.decode(value)
            except ValueError:
                raise HTTPBadRequest(
                    "Cannot decode URL parameter %s: %s" % (
                        name, value))

        if not self.extra:
            return result

        remaining = set(url_parameters.keys()).difference(
            set(result.keys()))
        extra = {}
        for name in remaining:
            value = url_parameters.getall(name)
            converter = self.converters.get(name, IDENTITY_CONVERTER)
            try:
                extra[name] = converter.decode(value)
            except ValueError:
                raise HTTPBadRequest(
                    "Cannot decode URL parameter %s: %s" % (
                        name, value))
        result['extra_parameters'] = extra
        return result

########NEW FILE########
__FILENAME__ = core
from .app import global_app
from .config import Config
from .mount import Mount
import morepath.directive
from morepath import generic
from .app import AppBase
from .request import Request, Response, LinkMaker, NothingMountedLinkMaker
from .converter import Converter, IDENTITY_CONVERTER
from webob import Response as BaseResponse
from webob.exc import HTTPException, HTTPForbidden, HTTPMethodNotAllowed
import morepath
from reg import mapply, KeyIndex
from datetime import datetime, date
from time import mktime, strptime


assert morepath.directive  # we need to make the function directive work


def setup():
    """Set up core Morepath framework configuration.

    Returns a :class:`Config` object; you can then :meth:`Config.scan`
    the configuration of other packages you want to load and then
    :meth:`Config.commit` it.

    See also :func:`autoconfig` and :func:`autosetup`.

    :returns: :class:`Config` object.
    """
    config = Config()
    config.scan(morepath, ignore=['.tests'])
    return config


@global_app.function(generic.consume, Request, object)
def traject_consume(request, model, lookup):
    traject = generic.traject(model, lookup=lookup, default=None)
    if traject is None:
        return None
    value, stack, traject_variables = traject.consume(request.unconsumed)
    if value is None:
        return None
    get_model, get_parameters = value
    variables = get_parameters(request.GET)
    context = generic.context(model, default=None, lookup=lookup)
    if context is None:
        return None
    variables.update(context)
    variables['parent'] = model
    variables['request'] = request
    variables.update(traject_variables)
    next_model = mapply(get_model, **variables)
    if next_model is None:
        return None
    request.unconsumed = stack
    return next_model


@global_app.function(generic.link, Request, object, object)
def link(request, model, mounted):
    result = []
    parameters = {}
    while mounted is not None:
        path, params = generic.path(model, lookup=mounted.lookup)
        result.append(path)
        parameters.update(params)
        model = mounted
        mounted = mounted.parent
    result.append(request.script_name)
    result.reverse()
    return '/'.join(result).strip('/'), parameters


@global_app.function(generic.linkmaker, Request, object)
def linkmaker(request, mounted):
    return LinkMaker(request, mounted)


@global_app.function(generic.linkmaker, Request, type(None))
def none_linkmaker(request, mounted):
    return NothingMountedLinkMaker(request)


@global_app.function(generic.traject, AppBase)
def app_traject(app):
    return app.traject


@global_app.function(generic.lookup, Mount)
def mount_lookup(model):
    return model.app.lookup


@global_app.function(generic.traject, Mount)
def mount_traject(model):
    return model.app.traject


@global_app.function(generic.context, Mount)
def mount_context(mount):
    return mount.create_context()


@global_app.function(generic.response, Request, object)
def get_response(request, model, predicates=None):
    view = generic.view.component(
        request, model, lookup=request.lookup,
        predicates=predicates,
        default=None)
    if view is None:
        return None
    if (view.permission is not None and
        not generic.permits(request.identity, model, view.permission,
                            lookup=request.lookup)):
        raise HTTPForbidden()
    content = view(request, model)
    if isinstance(content, BaseResponse):
        # the view took full control over the response
        return content
    # XXX consider always setting a default render so that view.render
    # can never be None
    if view.render is not None:
        response = view.render(content)
    else:
        response = Response(content, content_type='text/plain')
    request.run_after(response)
    return response


@global_app.function(generic.permits, object, object, object)
def has_permission(identity, model, permission):
    return False


@global_app.predicate(name='name', index=KeyIndex, order=0,
                      default='')
def name_predicate(self, request):
    return request.view_name


@global_app.predicate(name='request_method', index=KeyIndex, order=1,
                      default='GET')
def request_method_predicate(self, request):
    return request.method


@global_app.predicate_fallback(name='request_method')
def method_not_allowed(self, request):
    raise HTTPMethodNotAllowed()


@global_app.converter(type=int)
def int_converter():
    return Converter(int)


@global_app.converter(type=type(u""))
def unicode_converter():
    return IDENTITY_CONVERTER


# Python 2
if type(u"") != type(""): # flake8: noqa
    @global_app.converter(type=type(""))
    def str_converter():
        # XXX do we want to decode/encode unicode?
        return IDENTITY_CONVERTER


def date_decode(s):
    return date.fromtimestamp(mktime(strptime(s, '%Y%m%d')))


def date_encode(d):
    return d.strftime('%Y%m%d')


@global_app.converter(type=date)
def date_converter():
    return Converter(date_decode, date_encode)


def datetime_decode(s):
    return datetime.fromtimestamp(mktime(strptime(s, '%Y%m%dT%H%M%S')))


def datetime_encode(d):
    return d.strftime('%Y%m%dT%H%M%S')


@global_app.converter(type=datetime)
def datetime_converter():
    return Converter(datetime_decode, datetime_encode)


@global_app.tween_factory()
def excview_tween_factory(app, handler):
    def excview_tween(request):
        try:
            response = handler(request)
        except Exception as exc:
            # override predicates so that they aren't taken from request;
            # default name and GET is correct for exception views.
            response = generic.response(request, exc, lookup=app.lookup,
                                        default=None, predicates={})
            if response is None:
                raise
            return response
        return response
    return excview_tween


@global_app.view(model=HTTPException)
def standard_exception_view(self, model):
    # webob HTTPException is a response already
    return self

########NEW FILE########
__FILENAME__ = directive
from .app import AppBase
from .config import Directive
from .settings import SettingSection
from .error import ConfigError
from .view import (register_view, render_json, render_html,
                   register_predicate, register_predicate_fallback,
                   get_predicates_with_defaults)
from .security import (register_permission_checker,
                       Identity, NoIdentity)
from .path import register_path
from .mount import register_mount
from .traject import Path
from reg import KeyIndex
from .request import Request, Response
from morepath import generic
from functools import update_wrapper


class directive(object):
    """Register a new directive with Morepath.

    Instantiate this class with the name of the configuration directive.
    The instance is a decorator that can be applied to a subclass of
    :class:`Directive`. For example::

      @directive('foo')
      class FooDirective(Directive):
         ...

    This needs to be executed *before* the directive is being used and
    thus might introduce import dependency issues unlike normal Morepath
    configuration, so beware!
    """
    def __init__(self, name):
        self.name = name

    def __call__(self, directive):
        def method(self, *args, **kw):
            return directive(self, *args, **kw)
        # this is to help morepath.sphinxext to do the right thing
        method.actual_directive = directive
        update_wrapper(method, directive.__init__)
        setattr(AppBase, self.name, method)
        return directive


@directive('setting')
class SettingDirective(Directive):
    def __init__(self, app, section, name):
        """Register application setting.

        An application setting is registered under the ``settings``
        attribute of :class:`morepath.app.AppBase`. It will
        be executed early in configuration so other configuration
        directives can depend on the settings being there.

        The decorated function returns the setting value when executed.

        :param section: the name of the section the setting should go
          under.
        :param name: the name of the setting in its section.
        """

        super(SettingDirective, self).__init__(app)
        self.section = section
        self.name = name

    def identifier(self, app):
        return self.section, self.name

    def perform(self, app, obj):
        section = getattr(app.settings, self.section, None)
        if section is None:
            section = SettingSection()
            setattr(app.settings, self.section, section)
        setattr(section, self.name, obj())


class SettingValue(object):
    def __init__(self, value):
        self.value = value

    def __call__(self):
        return self.value


@directive('setting_section')
class SettingSectionDirective(Directive):
    def __init__(self, app, section):
        """Register application setting in a section.

        An application settings are registered under the ``settings``
        attribute of :class:`morepath.app.AppBase`. It will
        be executed early in configuration so other configuration
        directives can depend on the settings being there.

        The decorated function returns a dictionary with as keys the
        setting names and as values the settings.

        :param section: the name of the section the setting should go
          under.
        """

        super(SettingSectionDirective, self).__init__(app)
        self.section = section

    def prepare(self, obj):
        section = obj()
        app = self.configurable
        for name, value in section.items():
            yield (app.setting(section=self.section, name=name),
                   SettingValue(value))


@directive('converter')
class ConverterDirective(Directive):
    depends = [SettingDirective]

    def __init__(self, app, type):
        """Register custom converter for type.

        :param type: the Python type for which to register the
          converter.  Morepath uses converters when converting path
          variables and URL parameters when decoding or encoding
          URLs. Morepath looks up the converter using the
          type. The type is either given explicitly as the value in
          the ``converters`` dictionary in the
          :meth:`morepath.AppBase.path` directive, or is deduced from
          the value of the default argument of the decorated model
          function or class using ``type()``.
        """
        super(ConverterDirective, self).__init__(app)
        self.type = type

    def identifier(self, app):
        return ('converter', self.type)

    def perform(self, app, obj):
        app.register_converter(self.type, obj())


@directive('path')
class PathDirective(Directive):
    depends = [SettingDirective, ConverterDirective]

    def __init__(self, app, path, model=None,
                 variables=None, converters=None, required=None,
                 get_converters=None, absorb=False):
        """Register a model for a path.

        Decorate a function or a class (constructor). The function
        should return an instance of the model class, for instance by
        querying it from the database, or ``None`` if the model does
        not exist.

        The decorated function gets as arguments any variables
        specified in the path as well as URL parameters.

        If you declare a ``request`` parameter the function is
        able to use that information too.

        :param path: the route for which the model is registered.
        :param model: the class of the model that the decorated function
          should return. If the directive is used on a class instead of a
          function, the model should not be provided.
        :param variables: a function that given a model object can construct
          the variables used in the path (including any URL parameters).
          If omitted, variables are retrieved from the model by using
          the arguments of the decorated function.
        :param converters: a dictionary containing converters for variables.
          The key is the variable name, the value is a
          :class:`morepath.Converter` instance.
        :param required: list or set of names of those URL parameters which
          should be required, i.e. if missing a 400 Bad Request response is
          given. Any default value is ignored. Has no effect on path
          variables. Optional.
        :param get_converters: a function that returns a converter dictionary.
          This function is called once during configuration time. It can
          be used to programmatically supply converters. It is merged
          with the ``converters`` dictionary, if supplied. Optional.
        :param absorb: If set to ``True``, matches any subpath that
          matches this path as well. This is passed into the decorated
          function as the ``remaining`` variable.
        """
        super(PathDirective, self).__init__(app)
        self.model = model
        self.path = path
        self.variables = variables
        self.converters = converters
        self.required = required
        self.get_converters = get_converters
        self.absorb = absorb

    def identifier(self, app):
        return ('path', Path(self.path).discriminator())

    def discriminators(self, app):
        return [('model', self.model)]

    def prepare(self, obj):
        model = self.model
        if isinstance(obj, type):
            if model is not None:
                raise ConfigError(
                    "@path decorates class so cannot "
                    "have explicit model: %s" % model)
            model = obj
        if model is None:
            raise ConfigError(
                "@path does not decorate class and has no explicit model")
        yield self.clone(model=model), obj

    def perform(self, app, obj):
        register_path(app, self.model, self.path,
                      self.variables, self.converters, self.required,
                      self.get_converters, self.absorb,
                      obj)


@directive('permission_rule')
class PermissionRuleDirective(Directive):
    depends = [SettingDirective]

    def __init__(self, app, model, permission, identity=Identity):
        """Declare whether a model has a permission.

        The decorated function receives ``model``, `permission``
        (instance of any permission object) and ``identity``
        (:class:`morepath.security.Identity`) parameters. The
        decorated function should return ``True`` only if the given
        identity exists and has that permission on the model.

        :param model: the model class
        :param permission: permission class
        :param identity: identity class to check permission for. If ``None``,
          the identity to check for is the special
          :data:`morepath.security.NO_IDENTITY`.
        """
        super(PermissionRuleDirective, self).__init__(app)
        self.model = model
        self.permission = permission
        if identity is None:
            identity = NoIdentity
        self.identity = identity

    def identifier(self, app):
        return (self.model, self.permission, self.identity)

    def perform(self, app, obj):
        register_permission_checker(
            app, self.identity, self.model, self.permission, obj)


@directive('predicate')
class PredicateDirective(Directive):
    depends = [SettingDirective]

    def __init__(self, app, name, order, default, index=KeyIndex):
        """Register custom view predicate.

        The decorated function gets ``model`` and ``request`` (a
        :class:`morepath.Request` object) parameters.

        From this information it should calculate a predicate value
        and return it. You can then pass these extra predicate
        arguments to :meth:`morepath.AppBase.view` and this view is
        only found if the predicate matches.

        :param name: the name of the view predicate.
        :param order: when this custom view predicate should be checked
          compared to the others. A lower order means a higher importance.
        :type order: int
        :param default: the default value for this view predicate.
          This is used when the predicate is omitted or ``None`` when
          supplied to the :meth:`morepath.AppBase.view` directive.
          This is also used when using :meth:`Request.view` to render
          a view.
        :param index: the predicate index to use. Default is
          :class:`reg.KeyIndex` which matches by name.

        """
        super(PredicateDirective, self).__init__(app)
        self.name = name
        self.order = order
        self.default = default
        self.index = index

    def identifier(self, app):
        return self.name

    def perform(self, app, obj):
        register_predicate(app, self.name, self.order, self.default,
                           self.index, obj)


@directive('predicate_fallback')
class PredicateFallbackDirective(Directive):
    depends = [SettingDirective, PredicateDirective]

    def __init__(self, app, name):
        """For a given predicate name, register fallback view.

        The decorated function gets ``self`` and ``request`` parameters.

        The fallback view is a view that gets called when the
        named predicate does not match and no view has been registered
        that can handle that case.

        :param name: the name of the predicate.
        """
        super(PredicateFallbackDirective, self).__init__(app)
        self.name = name

    def identifier(self, app):
        return self.name

    def perform(self, app, obj):
        register_predicate_fallback(app, self.name, obj)


@directive('view')
class ViewDirective(Directive):
    depends = [SettingDirective, PredicateDirective,
               PredicateFallbackDirective]

    def __init__(self, app, model, render=None, permission=None,
                 **predicates):
        '''Register a view for a model.

        The decorated function gets ``self`` (model instance) and
        ``request`` (:class:`morepath.Request`) parameters. The
        function should return either a (unicode) string that is
        the response body, or a :class:`morepath.Response` object.

        If a specific ``render`` function is given the output of the
        function is passed to this first, and the function could
        return whatever the ``render`` parameter expects as input.
        :func:`morepath.render_json` for instance expects a Python
        object such as a dict that can be serialized to JSON.

        See also :meth:`morepath.AppBase.json` and
        :meth:`morepath.AppBase.html`.

        :param model: the class of the model for which this view is registered.
          The ``self`` passed into the view function is an instance
          of the model (or of a subclass).
        :param render: an optional function that can render the output of the
          view function to a response, and possibly set headers such as
          ``Content-Type``, etc.
        :param permission: a permission class. The model should have this
          permission, otherwise access to this view is forbidden. If omitted,
          the view function is public.
        :param name: the name of the view as it appears in the URL. If omitted,
          it is the empty string, meaning the default view for the model.
          This is a predicate.
        :param request_method: the request method to which this view should
          answer, i.e. GET, POST, etc. If omitted, this view responds to
          GET requests only. This is a predicate.
        :param predicates: predicates to match this view on. Use
          :data:`morepath.ANY` for a predicate if you don't care what
          the value is. If you don't specify a predicate, the default
          value is used. Standard predicate values are
          ``name`` and ``request_method``, but you can install your
          own using the :meth:`morepath.AppBase.predicate` directive.
        '''
        super(ViewDirective, self).__init__(app)
        self.model = model
        self.render = render
        self.permission = permission
        self.predicates = predicates

    def clone(self, **kw):
        # XXX standard clone doesn't work due to use of predicates
        # non-immutable in __init__. move this to another phase so
        # that this more complex clone isn't needed?
        args = dict(
            app=self.configurable,
            model=self.model,
            render=self.render,
            permission=self.permission)
        args.update(self.predicates)
        args.update(kw)
        return ViewDirective(**args)

    def identifier(self, app):
        predicates = get_predicates_with_defaults(
            self.predicates, app.exact('predicate_info', ()))
        predicates_discriminator = tuple(sorted(predicates.items()))
        return (self.model, predicates_discriminator)

    def perform(self, app, obj):
        register_view(app, self.model, obj, self.render, self.permission,
                      self.predicates)


@directive('json')
class JsonDirective(ViewDirective):
    def __init__(self, app, model, render=None, permission=None, **predicates):
        """Register JSON view.

        This is like :meth:`morepath.AppBase.view`, but with
        :func:`morepath.render_json` as default for the `render`
        function.

        Transforms the view output to JSON and sets the content type to
        ``application/json``.

        :param model: the class of the model for which this view is registered.
        :param name: the name of the view as it appears in the URL. If omitted,
          it is the empty string, meaning the default view for the model.
        :param render: an optional function that can render the output of the
          view function to a response, and possibly set headers such as
          ``Content-Type``, etc. Renders as JSON by default.
        :param permission: a permission class. The model should have this
          permission, otherwise access to this view is forbidden. If omitted,
          the view function is public.
        :param name: the name of the view as it appears in the URL. If omitted,
          it is the empty string, meaning the default view for the model.
          This is a predicate.
        :param request_method: the request method to which this view should
          answer, i.e. GET, POST, etc. If omitted, this view will respond to
          GET requests only. This is a predicate.
        :param predicates: predicates to match this view on. See the
          documentation of :meth:`AppBase.view` for more information.
        """
        render = render or render_json
        super(JsonDirective, self).__init__(app, model, render, permission,
                                            **predicates)


@directive('html')
class HtmlDirective(ViewDirective):
    def __init__(self, app, model, render=None, permission=None, **predicates):
        """Register HTML view.

        This is like :meth:`morepath.AppBase.view`, but with
        :func:`morepath.render_html` as default for the `render`
        function.

        Sets the content type to ``text/html``.

        :param model: the class of the model for which this view is registered.
        :param name: the name of the view as it appears in the URL. If omitted,
          it is the empty string, meaning the default view for the model.
        :param render: an optional function that can render the output of the
          view function to a response, and possibly set headers such as
          ``Content-Type``, etc. Renders as HTML by default.
        :param permission: a permission class. The model should have this
          permission, otherwise access to this view is forbidden. If omitted,
          the view function is public.
        :param name: the name of the view as it appears in the URL. If omitted,
          it is the empty string, meaning the default view for the model.
          This is a predicate.
        :param request_method: the request method to which this view should
          answer, i.e. GET, POST, etc. If omitted, this view will respond to
          GET requests only. This is a predicate.
        :param predicates: predicates to match this view on. See the
          documentation of :meth:`AppBase.view` for more information.
        """
        render = render or render_html
        super(HtmlDirective, self).__init__(app, model, render, permission,
                                            **predicates)


@directive('mount')
class MountDirective(PathDirective):
    depends = [SettingDirective, ConverterDirective]

    def __init__(self, base_app, path, app, converters=None,
                 required=None, get_converters=None):
        """Mount sub application on path.

        The decorated function gets the variables specified in path as
        parameters. It should return a dictionary with the required
        variables for the mounted app. The variables are declared in
        the :class:`morepath.App` constructor.

        :param path: the path to mount the application on.
        :param app: the :class:`morepath.App` instance to mount.
        :param converters: converters as for the
          :meth:`morepath.AppBase.path` directive.
        :param required: list or set of names of those URL parameters which
          should be required, i.e. if missing a 400 Bad Request response is
          given. Any default value is ignored. Has no effect on path
          variables. Optional.
        :param get_converters: a function that returns a converter dictionary.
          This function is called once during configuration time. It can
          be used to programmatically supply converters. It is merged
          with the ``converters`` dictionary, if supplied. Optional.
        """
        super(MountDirective, self).__init__(base_app, path,
                                             converters=converters,
                                             required=required,
                                             get_converters=get_converters)
        self.mounted_app = app

    # XXX it's a bit of a hack to make the mount directive
    # group with the path directive so we get conflicts,
    # we need to override prepare to shut it up again
    def prepare(self, obj):
        yield self.clone(), obj

    def discriminators(self, app):
        return [('mount', self.mounted_app)]

    def perform(self, app, obj):
        register_mount(app, self.mounted_app, self.path, self.converters,
                       self.required, self.get_converters, obj)


tween_factory_id = 0


@directive('tween_factory')
class TweenFactoryDirective(Directive):
    depends = [SettingDirective]

    def __init__(self, app, under=None, over=None, name=None):
        '''Register tween factory.

        The tween system allows the creation of lightweight middleware
        for Morepath that is aware of the request and the application.

        The decorated function is a tween factory. It should return a tween.
        It gets two arguments: the app for which this tween is in use,
        and another tween that this tween can wrap.

        A tween is a function that takes a request and a mounted
        application as arguments.

        Tween factories can be set to be over or under each other to
        control the order in which the produced tweens are wrapped.

        :param under: This tween factory produces a tween that wants to
          be wrapped by the tween produced by the ``under`` tween factory.
          Optional.
        :param over: This tween factory produces a tween that wants to
          wrap the tween produced by the over ``tween`` factory. Optional.
        :param name: The name under which to register this tween factory,
          so that it can be overridden by applications that extend this one.
          If no name is supplied a default name is generated.
        '''
        super(TweenFactoryDirective, self).__init__(app)
        global tween_factory_id
        self.app = app
        self.under = under
        self.over = over
        if name is None:
            name = u'tween_factory_%s' % tween_factory_id
            tween_factory_id += 1
        self.name = name

    def identifier(self, app):
        return self.name

    def perform(self, app, obj):
        app.register_tween_factory(obj, over=self.over, under=self.under)


@directive('identity_policy')
class IdentityPolicyDirective(Directive):
    depends = [SettingDirective]

    def __init__(self, app):
        '''Register identity policy.

        The decorated function should return an instance of an
        identity policy, which should have ``identify``, ``remember``
        and ``forget`` methods.
        '''
        super(IdentityPolicyDirective, self).__init__(app)

    def prepare(self, obj):
        policy = obj()
        app = self.configurable
        yield app.function(
            generic.identify, Request), policy.identify
        yield (app.function(
            generic.remember_identity, Response, Request, object),
            policy.remember)
        yield app.function(
            generic.forget_identity, Response, Request), policy.forget


@directive('verify_identity')
class VerifyIdentityDirective(Directive):
    def __init__(self, app, identity=object):
        '''Verify claimed identity.

        The decorated function gives a single ``identity`` argument which
        contains the claimed identity. It should return ``True`` only if the
        identity can be verified with the system.

        This is particularly useful with identity policies such as
        basic authentication and cookie-based authentication where the
        identity information (username/password) is repeatedly sent to
        the the server and needs to be verified.

        For some identity policies (auth tkt, session) this can always
        return ``True`` as the act of establishing the identity means
        the identity is verified.

        The default behavior is to always return ``False``.

        :param identity: identity class to verify. Optional.
        '''
        super(VerifyIdentityDirective, self).__init__(app)
        self.identity = identity

    def prepare(self, obj):
        yield self.configurable.function(
            generic.verify_identity, self.identity), obj


@directive('function')
class FunctionDirective(Directive):
    depends = [SettingDirective]

    def __init__(self, app, target, *sources):
        '''Register function as implementation of generic function

        The decorated function is an implementation of the generic
        function supplied to the decorator. This way you can override
        parts of the Morepath framework, or create new hookable
        functions of your own. This is a layer over
        :meth:`reg.IRegistry.register`.

        :param target: the generic function to register an implementation for.
        :type target: function object
        :param sources: classes of parameters to register for.
        '''
        super(FunctionDirective, self).__init__(app)
        self.target = target
        self.sources = tuple(sources)

    def identifier(self, app):
        return (self.target, self.sources)

    def perform(self, app, obj):
        app.register(self.target, self.sources, obj)

########NEW FILE########
__FILENAME__ = error
# -*- coding: utf-8 -*-


class ConfigError(Exception):
    """Raised when configuration is bad
    """


def conflict_keyfunc(action):
    codeinfo = action.codeinfo()
    if codeinfo is None:
        return 0
    filename, lineno, function, sourceline = codeinfo
    return (filename, lineno)


class ConflictError(ConfigError):
    """Raised when there is a conflict in configuration.
    """
    def __init__(self, actions):
        actions.sort(key=conflict_keyfunc)
        self.actions = actions
        result = [
            'Conflict between:']
        for action in actions:
            codeinfo = action.codeinfo()
            if codeinfo is None:
                continue
            filename, lineno, function, sourceline = codeinfo
            result.append('  File "%s", line %s' % (filename, lineno))
            result.append('    %s' % sourceline)
        msg = '\n'.join(result)
        super(ConflictError, self).__init__(msg)


class DirectiveReportError(ConfigError):
    """Raised when there's a problem with a directive.
    """
    def __init__(self, message, action):
        codeinfo = action.codeinfo()
        result = [message]
        if codeinfo is not None:
            filename, lineno, function, sourceline = codeinfo
            result.append('  File "%s", line %s' % (filename, lineno))
            result.append('    %s' % sourceline)
        msg = '\n'.join(result)
        super(DirectiveReportError, self).__init__(msg)


class DirectiveError(ConfigError):
    pass


class ResolveError(Exception):
    """Raised when path cannot be resolved
    """


class ViewError(ResolveError):
    """Raised when a view cannot be resolved
    """


class TrajectError(Exception):
    """Raised when path supplied to traject is not allowed.
    """


class LinkError(Exception):
    """Raised when a link cannot be made.
    """


class MountError(Exception):
    pass


class TopologicalSortError(Exception):
    pass

########NEW FILE########
__FILENAME__ = framehack
import sys


# taken from pyramid.path
def caller_module(level=2, sys=sys):
    module_globals = sys._getframe(level).f_globals
    module_name = module_globals.get('__name__') or '__main__'
    module = sys.modules[module_name]
    return module


def caller_package(level=2, caller_module=caller_module):
    # caller_module in arglist for tests
    module = caller_module(level+1)
    f = getattr(module, '__file__', '')
    if (('__init__.py' in f) or ('__init__$py' in f)):  # empty at >>>
        # Module is a package
        return module
    # Go up one level to get package
    package_name = module.__name__.rsplit('.', 1)[0]
    return sys.modules[package_name]

########NEW FILE########
__FILENAME__ = generic
import reg
from .error import LinkError


@reg.generic
def consume(request, model):
    """Consume request.unconsumed to new model, starting with model.

    Returns the new model, or None if no new model could be found.

    Adjusts request.unconsumed with the remaining unconsumed stack.
    """
    return None


@reg.generic
def context(model):
    """Get the context dictionary available for a model.
    """
    raise NotImplementedError  # pragma: nocoverage


@reg.generic
def lookup(obj):
    """Get the lookup that this object is associated with.
    """
    raise NotImplementedError    # pragma: nocoverage


@reg.generic
def path(model):
    """Get the path and parameters for a model in its own application.
    """
    raise LinkError()


@reg.generic
def link(request, model, mounted):
    """Create a link (URL) to a model, including any mounted applications.
    """
    raise NotImplementedError  # pragma: nocoverage


@reg.generic
def traject(obj):
    """Get traject for obj.
    """
    raise NotImplementedError  # pragma: nocoverage


@reg.generic
def view(request, model):
    """Get the view that represents the model in the context of a request.

    This view is a representation of the model that be rendered to
    a response. It may also return a Response directly. If a string is
    returned, the string is converted to a Response with the string as
    the response body.
    """
    raise NotImplementedError  # pragma: nocoverage


@reg.generic
def response(request, model):
    """Get a Response for the model in the context of the request.
    """
    raise NotImplementedError  # pragma: nocoverage


@reg.generic
def settings():
    """Return current settings object.

    In it are sections, and inside of the sections are the setting values.
    If there is a ``logging`` section and a ``loglevel`` setting in it,
    this is how you would access it::

      settings().logging.loglevel

    """
    raise NotImplementedError  # pragma: nocoverage


@reg.generic
def identify(request):
    """Returns an Identity or None if no identity can be found.

    Can also return NO_IDENTITY, but None is converted automatically
    to this.
    """
    raise NotImplementedError  # pragma: nocoverage


@reg.generic
def verify_identity(identity):
    """Returns True if the claimed identity can be verified.
    """
    return False


@reg.generic
def remember_identity(response, request, identity):
    """Modify response so that identity is remembered by client.
    """
    raise NotImplementedError  # pragma: nocoverage


@reg.generic
def forget_identity(response, request):
    """Modify response so that identity is forgotten by client.
    """
    raise NotImplementedError  # pragma: nocoverage


@reg.generic
def permits(identity, model, permission):
    """Returns True if identity has permission for model.

    identity can be the special NO_IDENTITY singleton; register for
    NoIdentity to handle this case separately.
    """
    raise NotImplementedError  # pragma: nocoverage


@reg.generic
def linkmaker(request, mounted):
    """Returns a link maker for request and mounted.
    """
    raise NotImplementedError  # pragma: nocoverage

########NEW FILE########
__FILENAME__ = mount
from .path import register_path, get_arguments, SPECIAL_ARGUMENTS
from .reify import reify
from reg import mapply


class Mount(object):
    def __init__(self, app, context_factory, variables):
        self.app = app
        self.context_factory = context_factory
        self.variables = variables

    def create_context(self):
        return mapply(self.context_factory, **self.variables)

    def __repr__(self):
        variable_info = ', '.join(["%s=%r" % t for t in
                                   sorted(self.variables.items())])
        result = '<morepath.Mount of %s' % repr(self.app)
        if variable_info:
            result += ' with variables: %s>' % variable_info
        else:
            result += '>'
        return result

    @reify
    def lookup(self):
        return self.app.lookup

    def set_implicit(self):
        self.app.set_implicit()

    def __call__(self, environ, start_response):
        request = self.app.request(environ)
        request.mounts.append(self)
        response = self.app.publish(request)
        return response(environ, start_response)

    @reify
    def parent(self):
        return self.variables.get('parent')

    def child(self, app, **context):
        factory = self.app._mounted.get(app)
        if factory is None:
            return None
        if 'parent' not in context:
            context['parent'] = self
        mounted = factory(**context)
        if mounted.create_context() is None:
            return None
        return mounted


def register_mount(base_app, app, path, converters, required, get_converters,
                   context_factory):
    # specific class as we want a different one for each mount
    class SpecificMount(Mount):
        def __init__(self, **kw):
            super(SpecificMount, self).__init__(app, context_factory, kw)
    # need to construct argument info from context_factory, not SpecificMount
    arguments = get_arguments(context_factory, SPECIAL_ARGUMENTS)
    register_path(base_app, SpecificMount, path, lambda m: m.variables,
                  converters, required, get_converters, False,
                  SpecificMount, arguments=arguments)
    register_mounted(base_app, app, SpecificMount)


def register_mounted(base_app, app, model_factory):
    base_app._mounted[app] = model_factory

########NEW FILE########
__FILENAME__ = path
from morepath import generic
from morepath.traject import Path, Inverse
from morepath.converter import ParameterFactory

from reg import arginfo

SPECIAL_ARGUMENTS = ['request', 'parent']


def get_arguments(callable, exclude):
    """Get dictionary with arguments and their default value.

    If no default is given, default value is taken to be None.
    """
    info = arginfo(callable)
    defaults = info.defaults or []
    defaults = [None] * (len(info.args) - len(defaults)) + list(defaults)
    return {name: default for (name, default) in zip(info.args, defaults)
            if name not in exclude}


def get_url_parameters(arguments, exclude):
    return {name: default for (name, default) in arguments.items() if
            name not in exclude}


def get_variables_func(arguments, exclude):
    names = [name for name in arguments.keys() if name not in exclude]
    return lambda model: {name: getattr(model, name) for
                          name in names}


def register_path(app, model, path, variables, converters, required,
                  get_converters, absorb, model_factory, arguments=None):
    traject = app.traject

    converters = converters or {}
    if get_converters is not None:
        converters.update(get_converters())
    if arguments is None:
        arguments = get_arguments(model_factory, SPECIAL_ARGUMENTS)
    converters = app.argument_and_explicit_converters(arguments, converters)
    exclude = Path(path).variables()
    exclude.update(app.mount_variables())
    parameters = get_url_parameters(arguments, exclude)
    if required is None:
        required = set()
    required = set(required)
    parameter_factory = ParameterFactory(parameters, converters, required,
                                         'extra_parameters' in arguments)
    if variables is None:
        variables = get_variables_func(arguments, app.mount_variables())

    traject.add_pattern(path, (model_factory, parameter_factory),
                        converters, absorb)

    inverse = Inverse(path, variables, converters, parameters.keys(),
                      absorb)
    app.register(generic.path, [model], inverse)

########NEW FILE########
__FILENAME__ = publish
from morepath import generic
from .mount import Mount
from .traject import create_path
from webob.exc import HTTPNotFound


DEFAULT_NAME = u''


class ResponseSentinel(object):
    pass


RESPONSE_SENTINEL = ResponseSentinel()


def resolve_model(request):
    """Resolve path to a model using consumers.
    """
    lookup = request.lookup  # XXX can get this from argument too
    mounts = request.mounts
    model = mounts[-1]
    model.set_implicit()
    while request.unconsumed:
        next_model = generic.consume(request, model, lookup=lookup)
        if next_model is None:
            return model
        model = next_model
        if isinstance(model, Mount):
            model.set_implicit()
            mounts.append(model)
        # get new lookup for whatever we found if it exists
        lookup = generic.lookup(model, lookup=lookup, default=lookup)
        request.lookup = lookup
    # if there is nothing (left), we consume toward a root model
    if not request.unconsumed and isinstance(model, Mount):
        root_model = generic.consume(request, model, lookup=lookup)
        if root_model is not None:
            model = root_model
        # XXX handling mounting? lookups? write test cases
    request.lookup = lookup
    return model


def resolve_response(request, model):
    request.view_name = get_view_name(request.unconsumed)

    response = generic.response(request, model, default=RESPONSE_SENTINEL,
                                lookup=request.lookup)
    if response is RESPONSE_SENTINEL:
        raise HTTPNotFound()
    return response


def get_view_name(stack):
    unconsumed_amount = len(stack)
    if unconsumed_amount > 1:
        raise HTTPNotFound()
    elif unconsumed_amount == 0:
        return DEFAULT_NAME
    elif unconsumed_amount == 1:
        return stack[0].lstrip('+')
    assert False, ("Unconsumed stack: %s" %
                   create_path(stack))  # pragma: nocoverage


def publish(request):
    model = resolve_model(request)
    return resolve_response(request, model)

########NEW FILE########
__FILENAME__ = reify
# taken from pyramid.decorator


class reify(object):
    """ Use as a class method decorator.  It operates almost exactly like the
    Python ``@property`` decorator, but it puts the result of the method it
    decorates into the instance dict after the first call, effectively
    replacing the function it decorates with an instance variable.  It is, in
    Python parlance, a non-data descriptor.  An example:

    .. code-block:: python

       class Foo(object):
           @reify
           def jammy(self):
               print('jammy called')
               return 1

    And usage of Foo:

    f = Foo()
    v = f.jammy
    'jammy called'
    print(v)
    1
    print f.jammy
    1
    # jammy func not called the second time; it replaced itself with 1
    """
    def __init__(self, wrapped):
        self.wrapped = wrapped
        try:
            self.__doc__ = wrapped.__doc__
        except:  # pragma: no cover
            pass

    def __get__(self, inst, objtype=None):
        if inst is None:
            return self
        val = self.wrapped(inst)
        setattr(inst, self.wrapped.__name__, val)
        return val

########NEW FILE########
__FILENAME__ = request
from morepath import generic
from webob import BaseRequest, Response as BaseResponse
from .reify import reify
from .traject import parse_path
from .error import LinkError

try:
    from urllib.parse import urlencode
except ImportError:
    # Python 2
    from urllib import urlencode
import reg


NO_DEFAULT = reg.Sentinel('NO_DEFAULT')


class Request(BaseRequest):
    """Request.

    Extends :class:`webob.request.BaseRequest`
    """
    def __init__(self, environ):
        super(Request, self).__init__(environ)
        self.unconsumed = parse_path(self.path_info)
        self.mounts = []
        self._after = []

    @reify
    def identity(self):
        """Self-proclaimed identity of the user.

        The identity is established using the identity policy. Normally
        this would be an instance of :class:`morepath.security.Identity`.

        If no identity is claimed or established, or if the identity
        is not verified by the application, the identity is the the
        special value :attr:`morepath.security.NO_IDENTITY`.

        The identity can be used for authentication/authorization of
        the user, using Morepath permission directives.
        """
        # XXX annoying circular dependency
        from .security import NO_IDENTITY
        result = generic.identify(self, lookup=self.lookup,
                                  default=NO_IDENTITY)
        if not generic.verify_identity(result, lookup=self.lookup):
            return NO_IDENTITY
        return result

    @reify
    def mounted(self):
        return self.mounts[-1]

    def view(self, obj, default=None, **predicates):
        """Call view for model instance.

        This does not render the view, but calls the appropriate
        view function and returns its result.

        :param obj: the model instance to call the view on.
        :param default: default value if view is not found.
        :param predicates: extra predicates to modify view
          lookup, such as ``name`` and ``request_method``. The default
          ``name`` is empty, so the default view is looked up,
          and the default ``request_method`` is ``GET``. If you introduce
          your own predicates you can specify your own default.
        """
        return generic.linkmaker(self, self.mounted, lookup=self.lookup).view(
            obj, default, **predicates)

    def link(self, obj, name='', default=None):
        """Create a link (URL) to a view on a model instance.

        If no link can be constructed for the model instance, a
        :exc:``morepath.LinkError`` is raised. ``None`` is treated
        specially: if ``None`` is passed in the default value is
        returned.

        :param obj: the model instance to link to, or ``None``.
        :param name: the name of the view to link to. If omitted, the
          the default view is looked up.
        :param default: if ``None`` is passed in, the default value is
          returned. By default this is ``None``.

        """
        return generic.linkmaker(self, self.mounted,
                                 lookup=self.lookup).link(obj, name, default)

    @reify
    def parent(self):
        """Obj to call :meth:`Request.link` or :meth:`Request.view` on parent.

        Get an object that represents the parent app that this app is mounted
        inside. You can call ``link`` and ``view`` on it.
        """
        return generic.linkmaker(self, self.mounted.parent, lookup=self.lookup)

    def child(self, app, **variables):
        """Obj to call :meth:`Request.link` or :meth:`Request.view` on child.

        Get an object that represents the application mounted in this app.
        You can call ``link`` and ``view`` on it.
        """
        return generic.linkmaker(self, self.mounted.child(app, **variables),
                                 lookup=self.lookup)

    def after(self, func):
        """Call function with response after this request is done.

        Can be used explicitly::

          def myfunc(response):
              response.headers.add('blah', 'something')
          request.after(my_func)

        or as a decorator::

          @request.after
          def myfunc(response):
              response.headers.add('blah', 'something')

        :param func: callable that is called with response
        :returns: func argument, not wrapped
        """
        self._after.append(func)
        return func

    def run_after(self, response):
        for after in self._after:
            after(response)


class Response(BaseResponse):
    """Response.

    Extends :class:`webob.response.Response`.
    """


class LinkMaker(object):
    def __init__(self, request, mounted):
        self.request = request
        self.mounted = mounted

    def link(self, obj, name='', default=None):
        if obj is None:
            return default
        path, parameters = generic.link(
            self.request, obj, self.mounted, lookup=self.mounted.lookup)
        parts = []
        if path:
            parts.append(path)
        if name:
            parts.append(name)
        result = '/' + '/'.join(parts)
        if parameters:
            result += '?' + urlencode(parameters, True)
        return result

    def view(self, obj, default=None, **predicates):
        view = generic.view.component(
            self.request, obj, lookup=self.mounted.lookup, default=default,
            predicates=predicates)
        if view is None:
            return None
        return view(self.request, obj)

    @reify
    def parent(self):
        return generic.linkmaker(self.request, self.mounted.parent,
                                 lookup=self.mounted.lookup)

    def child(self, app, **variables):
        return generic.linkmaker(self.request,
                                 self.mounted.child(app, **variables),
                                 lookup=self.mounted.lookup)


class NothingMountedLinkMaker(object):
    def __init__(self, request):
        self.request = request

    def link(self, obj, name='', default=None):
        raise LinkError("Cannot link to %r (name %r)" % (obj, name))

    def view(self, obj, default=None, **predicates):
        raise LinkError("Cannot view %r (predicates %r)" % (obj, predicates))

    @reify
    def parent(self):
        return NothingMountedLinkMaker(self.request)

    def child(self, app, **variables):
        return NothingMountedLinkMaker(self.request)

########NEW FILE########
__FILENAME__ = run
from wsgiref.simple_server import make_server


def run(wsgi, host=None, port=None):  # pragma: no cover
    """Uses wsgiref.simple_server to run application for debugging purposes.

    Don't use this in production; use an external WSGI server instead,
    for instance Apache mod_wsgi, Nginx wsgi, Waitress, Gunicorn.

    :param wsgi: WSGI app.
    :param host: hostname.
    :param port: port.
    """
    if host is None:
        host = '127.0.0.1'
    if port is None:
        port = 5000
    server = make_server(host, port, wsgi)
    print("Running %s with wsgiref.simple_server on http://%s:%s" % (
        wsgi, host, port))
    server.serve_forever()

########NEW FILE########
__FILENAME__ = security
from morepath import generic
from .compat import bytes_
import binascii
import base64


class NoIdentity(object):
    userid = None


NO_IDENTITY = NoIdentity()


class Identity(object):
    """Claimed identity of a user.

    Note that this identity is just a claim; to authenticate the user
    and authorize them you need to implement Morepath permission directives.
    """
    def __init__(self, userid, **kw):
        """
        :param userid: The userid of this identity
        :param kw: Extra information to store in identity.
        """
        self.userid = userid
        self._names = kw.keys()
        for key, value in kw.items():
            setattr(self, key, value)
        self.verified = None  # starts out as never verified

    def as_dict(self):
        """Export identity as dictionary.

        This includes the userid and the extra keyword parameters used
        when the identity was created.

        :returns: dict with identity info.
        """
        result = {
            'userid': self.userid,
            }
        for name in self._names:
            result[name] = getattr(self, name)
        return result


class BasicAuthIdentityPolicy(object):
    """Identity policy that uses HTTP Basic Authentication.

    Note that this policy does **not** do any password validation. You're
    expected to do so using permission directives.
    """
    def __init__(self, realm='Realm'):
        self.realm = realm

    def identify(self, request):
        """Establish claimed identity using request.

        :param request: Request to extract identity information from.
        :type request: :class:`morepath.Request`.
        :returns: :class:`morepath.security.Identity` instance.
        """
        try:
            authorization = request.authorization
        except ValueError:
            return None
        if authorization is None:
            return None
        authtype, params = authorization
        auth = parse_basic_auth(authtype, params)
        if auth is None:
            return None
        return Identity(userid=auth.username, password=auth.password)

    def remember(self, response, request, identity):
        """Remember identity on response.

        This is a no-op for basic auth, as the browser re-identifies
        upon each request in that case.

        :param response: response object on which to store identity.
        :type response: :class:`morepath.Response`
        :param request: request object.
        :type request: :class:`morepath.Request`
        :param identity: identity to remember.
        :type identity: :class:`morepath.security.Identity`
        """

    def forget(self, response, request):
        """Forget identity on response.

        This causes the browser to issue a basic authentication
        dialog.  Warning: for basic auth, the browser in fact does not
        forget the information even if ``forget`` is called.

        :param response: response object on which to forget identity.
        :type response: :class:`morepath.Response`
        :param request: request object.
        :type request: :class:`morepath.Request`

        """
        response.headers.add('WWW-Authenticate',
                             'Basic realm="%s"' % self.realm)


def register_permission_checker(registry, identity, model, permission, func):
    registry.register(generic.permits, (identity, model, permission), func)


class BasicAuthInfo(object):
    def __init__(self, username, password):
        self.username = username
        self.password = password


# code taken from
# pyramid.authentication.BasicAuthenticationPolicy._get_credentials
def parse_basic_auth(authtype, params):
    # try:
    #     authtype, params = parse_auth(value)
    # except ValueError:
    #     return None

    if authtype != 'Basic':
        return None
    try:
        authbytes = b64decode(params.strip())
    except (TypeError, binascii.Error):  # can't decode
        return None

    # try utf-8 first, then latin-1; see discussion in
    # https://github.com/Pylons/pyramid/issues/898
    try:
        auth = authbytes.decode('utf-8')
    except UnicodeDecodeError:
        # might get nonsense but normally not get decode error
        auth = authbytes.decode('latin-1')

    try:
        username, password = auth.split(':', 1)
    except ValueError:  # not enough values to unpack
        return None

    return BasicAuthInfo(username, password)


def b64decode(v):
    return base64.b64decode(bytes_(v))

########NEW FILE########
__FILENAME__ = settings

class SettingSectionContainer(object):
    pass


class SettingSection(object):
    pass

########NEW FILE########
__FILENAME__ = sphinxext
"""Sphinx extension to make sure directives have proper signatures.

This is tricky as directives are added as methods to the ``AppBase``
object using the directive decorator, and the signature needs to be
obtained from the directive class's ``__init__`` manually. In addition
this signature has a first argument (``app``) that needs to be
removed.
"""
import inspect


def setup(app):  # pragma: nocoverage
    # all inline to avoid dependency on sphinx.ext.autodoc which
    # would trip up scanning
    from sphinx.ext.autodoc import ModuleDocumenter, MethodDocumenter

    class DirectiveDocumenter(MethodDocumenter):
        objtype = 'morepath_directive'
        priority = MethodDocumenter.priority + 1
        member_order = 49

        @classmethod
        def can_document_member(cls, member, membername, isattr, parent):
            return (inspect.isroutine(member) and
                    not isinstance(parent, ModuleDocumenter) and
                    hasattr(member, 'actual_directive'))

        def import_object(self):
            if not super(DirectiveDocumenter, self).import_object():
                return
            object = getattr(self.object, 'actual_directive', None)
            if object is None:
                return False
            self.object = object.__init__
            self.directivetype = 'decorator'
            return True

        def format_signature(self):
            result = super(DirectiveDocumenter, self).format_signature()
            # brute force ripping out of first argument
            result = result.replace('(app, ', '(')
            result = result.replace('(base_app, ', '(')
            result = result.replace('(app)', '()')
            return result

    def decide_to_skip(app, what, name, obj, skip, options):
        if what != 'class':
            return skip
        directive = getattr(obj, 'actual_directive', None)
        if directive is not None:
            return False
        return skip

    app.connect('autodoc-skip-member', decide_to_skip)
    app.add_autodocumenter(DirectiveDocumenter)

########NEW FILE########
__FILENAME__ = abbr
import morepath

app = morepath.App()


class Model(object):
    def __init__(self, id):
        self.id = id


@app.path(model=Model, path='{id}')
def get_model(id):
    return Model(id)


with app.view(model=Model) as view:
    @view()
    def default(self, request):
        return "Default view: %s" % self.id

    @view(name='edit')
    def edit(self, request):
        return "Edit view: %s" % self.id

########NEW FILE########
__FILENAME__ = basic
import morepath

app = morepath.App()


@app.path(path='/')
class Root(object):
    def __init__(self):
        self.value = 'ROOT'


class Model(object):
    def __init__(self, id):
        self.id = id


@app.path(model=Model, path='{id}')
def get_model(id):
    return Model(id)


@app.view(model=Model)
def default(self, request):
    return "The view for model: %s" % self.id


@app.view(model=Model, name='link')
def link(self, request):
    return request.link(self)


@app.view(model=Model, name='json', render=morepath.render_json)
def json(self, request):
    return {'id': self.id}


@app.view(model=Root)
def root_default(self, request):
    return "The root: %s" % self.value


@app.view(model=Root, name='link')
def root_link(self, request):
    return request.link(self)

########NEW FILE########
__FILENAME__ = caller
import morepath


def main():
    config = morepath.setup()
    config.scan()
    config.commit()

########NEW FILE########
__FILENAME__ = other
import morepath


app = morepath.App()


@app.path(path='/')
class Root(object):
    pass


@app.view(model=Root)
def root_default(self, request):
    return "Hello world"

########NEW FILE########
__FILENAME__ = other
import morepath


app = morepath.App()


@app.path(path='/')
class Root(object):
    pass


@app.view(model=Root)
def root_default(self, request):
    return "Hello world"

########NEW FILE########
__FILENAME__ = conflict
import morepath

app = morepath.App()


@app.path(path='/')
class Root(object):
    pass


@app.path(path='/', model=Root)
def get_root():
    return Root()

########NEW FILE########
__FILENAME__ = identity_policy
import morepath

app = morepath.App()


class Model(object):
    def __init__(self, id):
        self.id = id


class Permission(object):
    pass


@app.path(model=Model, path='{id}')
def get_model(id):
    return Model(id)


@app.view(model=Model, permission=Permission)
def default(self, request):
    return "Model: %s" % self.id


@app.permission_rule(model=Model, permission=Permission)
def model_permission(identity, model, permission):
    return model.id == 'foo'


class IdentityPolicy(object):
    def identify(self, request):
        return morepath.Identity('testidentity')

    def remember(self, request, identity):
        return []

    def forget(self, request):
        return []


@app.identity_policy()
def get_identity_policy():
    return IdentityPolicy()


@app.verify_identity()
def verify_identity(identity):
    return True

########NEW FILE########
__FILENAME__ = mapply_bug
import morepath


app = morepath.App()


@app.path(path='')
class Root(object):
    pass


@app.html(model=Root)
def index(self, request):
    return "the root"

########NEW FILE########
__FILENAME__ = method
import morepath

app = morepath.App()


class StaticMethod(object):
    pass


class ClassMethod(object):
    def __init__(self, cls):
        self.cls = cls


@app.path(path='/')
class Root(object):
    def __init__(self):
        self.value = 'ROOT'

    @app.path(model=StaticMethod, path='static')
    @staticmethod
    def static_method():
        return StaticMethod()

    @app.path(model=ClassMethod, path='class')
    @classmethod
    def class_method(cls):
        assert cls is Root
        return ClassMethod(cls)


@app.view(model=StaticMethod)
def static_method_default(self, request):
    return "Static Method"


@app.view(model=ClassMethod)
def class_method_default(self, request):
    assert self.cls is Root
    return "Class Method"

########NEW FILE########
__FILENAME__ = nested
import morepath

outer_app = morepath.App('outer')
app = morepath.App('inner')


@outer_app.mount('inner', app)
def inner_context():
    return {}


@app.path(path='')
class Root(object):
    pass


class Model(object):
    def __init__(self, id):
        self.id = id


@app.path(model=Model, path='{id}')
def get_model(id):
    return Model(id)


@app.view(model=Model)
def default(self, request):
    return "The view for model: %s" % self.id


@app.view(model=Model, name='link')
def link(self, request):
    return request.link(self)

########NEW FILE########
__FILENAME__ = noconverter
import morepath

app = morepath.App()


# for which there is no known converter
class Dummy(object):
    pass


class Foo(object):
    pass


@app.path(path='/', model=Foo)
def get_foo(a=Dummy()):
    pass

########NEW FILE########
__FILENAME__ = normalmethod
import morepath

app = morepath.App()


class NormalMethod(object):
    pass


@app.path(path='/')
class Root(object):
    def __init__(self):
        self.value = 'ROOT'

    @app.path(model=NormalMethod, path='normal')
    def normal_method(self):
        return NormalMethod()


@app.view(model=NormalMethod)
def normal_method_default(self, request):
    return "Normal Method"

########NEW FILE########
__FILENAME__ = someerror
import morepath

app = morepath.App()

1/0

########NEW FILE########
__FILENAME__ = test_app
from morepath.app import App, global_app
from morepath.error import MountError
import morepath
import pytest


def setup_module(module):
    morepath.disable_implicit()


def test_global_app():
    assert global_app.extends == []
    assert global_app.name == 'global_app'


def test_app_without_extends():
    myapp = App()
    assert myapp.extends == [global_app]
    assert myapp.name is None


def test_app_with_extends():
    parentapp = App()
    myapp = App('myapp', extends=parentapp)
    assert myapp.extends == [parentapp]
    assert myapp.name == 'myapp'


def test_app_caching_lookup():
    class MockClassLookup(object):
        called = 0

        def all(self, key, classes):
            self.called += 1
            return ["answer"]

    class MockApp(MockClassLookup, App):
        pass

    myapp = MockApp()
    lookup = myapp.lookup
    answer = lookup.component('foo', [])
    assert answer == 'answer'
    assert myapp.called == 1

    # after this the answer will be cached for those parameters
    answer = lookup.component('foo', [])
    assert myapp.called == 1

    answer = myapp.lookup.component('foo', [])
    assert myapp.called == 1

    # but different parameters does trigger another call
    lookup.component('bar', [])
    assert myapp.called == 2


def test_app_name_repr():
    app = morepath.App(name='foo')
    assert repr(app) == "<morepath.App 'foo'>"


def test_app_unnamed_repr():
    app = morepath.App()
    assert repr(app).startswith("<morepath.App at 0x")


def test_app_set_implicit():
    app = morepath.App()
    app.set_implicit()


def test_app_mounted():
    app = morepath.App(variables=['foo'])
    with pytest.raises(MountError):
        app.mounted()

########NEW FILE########
__FILENAME__ = test_config
from morepath import config
from morepath.error import ConflictError
import pytest
import morepath


def setup_module(module):
    morepath.disable_implicit()


def test_action():
    performed = []

    class MyAction(config.Action):
        def perform(self, configurable, obj):
            performed.append(obj)

        def identifier(self, configurable):
            return ()

    c = config.Config()
    x = config.Configurable()

    class Foo(object):
        pass

    foo = Foo()
    c.configurable(x)
    c.action(MyAction(x), foo)
    assert performed == []
    c.commit()
    assert performed == [foo]


def test_action_not_implemented():
    class UnimplementedAction(config.Action):
        def identifier(self, configurable):
            return ()

    c = config.Config()
    x = config.Configurable()
    c.configurable(x)
    c.action(UnimplementedAction(x), None)
    with pytest.raises(NotImplementedError):
        c.commit()


def test_directive():
    performed = []

    class MyDirective(config.Directive):
        def perform(self, configurable, obj):
            performed.append(obj)

        def identifier(self, configurable):
            return ()

    c = config.Config()
    x = config.Configurable()

    c.configurable(x)

    d = MyDirective(x)

    # but this has no effect without scanning
    @d
    def foo():
        pass

    # so register action manually
    c.action(d, foo)

    c.commit()
    assert performed == [foo]


def test_directive_testing_config():
    performed = []

    class MyDirective(config.Directive):
        def perform(self, configurable, obj):
            performed.append(obj)

        def identifier(self, configurable):
            return ()

    c = config.Config()
    x = config.Configurable(testing_config=c)

    assert c.configurables == [x]

    # Due to testing_config, now the directive does work without scanning.
    @MyDirective(x)
    def foo():
        pass

    c.commit()
    assert performed == [foo]


def test_directive_without_testing_config_not_found():
    performed = []

    class MyDirective(config.Directive):
        def perform(self, configurable, obj):
            performed.append(obj)

        def identifier(self, configurable):
            return ()

    c = config.Config()
    x = config.Configurable()

    # The configurable won't be picked up.
    assert c.configurables == []

    # Since there's no testing_config, the directive does not get picked up,
    # as it isn't scanned.
    @MyDirective(x)
    def foo():
        pass

    c.commit()
    assert performed == []


def test_directive_testing_config_external():
    performed = []

    class MyDirective(config.Directive):
        def perform(self, configurable, obj):
            performed.append(obj)

        def identifier(self, configurable):
            return ()

    c = config.Config()
    x = config.Configurable()

    # we set up testing config later
    x.testing_config = c
    assert x.testing_config is c

    # even setting it up later will find us the configurable
    assert c.configurables == [x]

    # Due to testing_config, now the directive does work without scanning.
    @MyDirective(x)
    def foo():
        pass

    c.commit()
    assert performed == [foo]


def test_conflict():
    class MyDirective(config.Directive):
        def identifier(self, configurable):
            return 1
    c = config.Config()
    x = config.Configurable(testing_config=c)

    @MyDirective(x)
    def foo():
        pass

    @MyDirective(x)
    def bar():
        pass

    with pytest.raises(ConflictError):
        c.commit()

    try:
        c.commit()
    except ConflictError as e:
        s = str(e)
        # XXX how can we test more details? very dependent on code
        assert s.startswith('Conflict between:')


def test_different_configurables_no_conflict():
    class MyDirective(config.Directive):
        def identifier(self, configurable):
            return 1

        def perform(self, configurable, obj):
            pass

    c = config.Config()
    x1 = config.Configurable(testing_config=c)
    x2 = config.Configurable(testing_config=c)

    @MyDirective(x1)
    def foo():
        pass

    @MyDirective(x2)
    def bar():
        pass

    c.commit()


def test_extra_discriminators_per_directive():
    class ADirective(config.Directive):
        def __init__(self, configurable, v):
            super(ADirective, self).__init__(configurable)
            self.v = v

        def identifier(self, configurable):
            return 'a'

        def discriminators(self, configurable):
            return [self.v]

        def perform(self, configurable, obj):
            pass

    c = config.Config()
    x = config.Configurable(testing_config=c)

    @ADirective(x, 1)
    def foo():
        pass

    @ADirective(x, 1)
    def bar():
        pass

    with pytest.raises(ConflictError):
        c.commit()


def test_configurable_inherit_without_change():
    performed = []

    class MyAction(config.Action):
        def perform(self, configurable, obj):
            performed.append((configurable, obj))

        def identifier(self, configurable):
            return ()

    c = config.Config()
    x = config.Configurable()
    y = config.Configurable(x)
    c.configurable(x)
    c.configurable(y)

    class Foo(object):
        pass

    foo = Foo()
    c.action(MyAction(x), foo)
    c.commit()

    assert performed == [(x, foo), (y, foo)]


def test_configurable_inherit_extending():
    a_performed = []
    b_performed = []

    class AAction(config.Action):
        def perform(self, configurable, obj):
            a_performed.append((configurable, obj))

        def identifier(self, configurable):
            return 'a_action'

    class BAction(config.Action):
        def perform(self, configurable, obj):
            b_performed.append((configurable, obj))

        def identifier(self, configurable):
            return 'b_action'

    c = config.Config()
    x = config.Configurable()
    y = config.Configurable(x)
    c.configurable(x)
    c.configurable(y)

    class Foo(object):
        pass

    foo = Foo()
    bar = Foo()
    c.action(AAction(x), foo)
    c.action(BAction(y), bar)
    c.commit()

    assert a_performed == [(x, foo), (y, foo)]
    assert b_performed == [(y, bar)]


def test_configurable_inherit_overriding():
    performed = []

    class MyAction(config.Action):
        def __init__(self, configurable, value):
            super(MyAction, self).__init__(configurable)
            self.value = value

        def perform(self, configurable, obj):
            performed.append((configurable, obj))

        def identifier(self, configurable):
            return 'action', self.value

    c = config.Config()
    x = config.Configurable()
    y = config.Configurable(x)
    c.configurable(x)
    c.configurable(y)

    class Foo(object):
        def __init__(self, name):
            self.name = name

        def __repr__(self):
            return '<Obj %s>' % self.name

    one = Foo('one')
    two = Foo('two')
    three = Foo('three')
    c.action(MyAction(x, 1), one)
    c.action(MyAction(x, 2), two)
    c.action(MyAction(y, 1), three)
    c.commit()

    assert performed == [(x, one), (x, two), (y, two), (y, three)]


def test_configurable_extra_discriminators():
    performed = []

    class MyAction(config.Action):
        def __init__(self, configurable, value, extra):
            super(MyAction, self).__init__(configurable)
            self.value = value
            self.extra = extra

        def perform(self, configurable, obj):
            performed.append((configurable, obj))

        def identifier(self, configurable):
            return 'action', self.value

        def discriminators(self, configurable):
            return [('extra', self.extra)]

    c = config.Config()
    x = config.Configurable()
    c.configurable(x)

    class Foo(object):
        def __init__(self, name):
            self.name = name

        def __repr__(self):
            return '<Obj %s>' % self.name

    one = Foo('one')
    two = Foo('two')
    three = Foo('three')
    c.action(MyAction(x, 1, 'a'), one)
    c.action(MyAction(x, 2, 'b'), two)
    c.action(MyAction(x, 3, 'b'), three)
    with pytest.raises(ConflictError):
        c.commit()


def test_prepare_returns_multiple_actions():
    performed = []

    class MyAction(config.Action):
        def __init__(self, configurable, value):
            super(MyAction, self).__init__(configurable)
            self.value = value

        def perform(self, configurable, obj):
            performed.append(obj)

        def identifier(self, configurable):
            return self.value

        def prepare(self, obj):
            yield MyAction(self.configurable, 1), obj
            yield MyAction(self.configurable, 2), obj

    c = config.Config()
    x = config.Configurable()

    class Foo(object):
        pass

    foo = Foo()
    c.configurable(x)
    c.action(MyAction(x, 3), foo)
    c.commit()
    assert performed == [foo, foo]


def test_abbreviation():
    performed = []

    class MyDirective(config.Directive):
        def __init__(self, configurable, foo=None, bar=None):
            super(MyDirective, self).__init__(configurable)
            self.foo = foo
            self.bar = bar

        def perform(self, configurable, obj):
            performed.append((obj, self.foo, self.bar))

        def identifier(self, configurable):
            return self.foo, self.bar

    c = config.Config()
    x = config.Configurable(testing_config=c)

    with MyDirective(x, foo='blah') as d:
        @d(bar='one')
        def f1():
            pass

        @d(bar='two')
        def f2():
            pass

    c.commit()

    assert performed == [(f1, 'blah', 'one'), (f2, 'blah', 'two')]


def test_config_phases():
    # when an action has a higher priority than another one,
    # we want it to be completely prepared and performed before
    # the other one even gets prepared and performed. This allows
    # directives that set up information that other directives use
    # during identifier and preparation stages (such as is the
    # case for view predicates)

    early_performed = []
    late_performed = []

    class EarlyAction(config.Action):
        def perform(self, configurable, obj):
            early_performed.append(obj)

        def identifier(self, configurable):
            return ('early',)

    class LateAction(config.Action):
        depends = [EarlyAction]

        # default priority
        def perform(self, configurable, obj):
            # make a copy of the early_performed list to
            # demonstrate it was already there when it's
            # in late_performed
            late_performed.append(list(early_performed))

        def identifier(self, configurable):
            # at this stage we already should have performed early
            assert early_performed == ['foo']
            return ('late')

    c = config.Config()
    x = config.Configurable()

    c.configurable(x)
    c.action(EarlyAction(x), 'foo')
    c.action(LateAction(x), 'bar')
    c.commit()
    assert early_performed == ['foo']
    assert late_performed == [['foo']]


def test_config_phases_extends():
    # when an action has a higher priority than another one,
    # we want it to be completely prepared and performed before
    # the other one even gets prepared and performed. This allows
    # directives that set up information that other directives use
    # during identifier and preparation stages (such as is the
    # case for view predicates)

    early_performed = []
    late_performed = []

    class EarlyAction(config.Action):
        def perform(self, configurable, obj):
            early_performed.append((configurable, obj))

        def identifier(self, configurable):
            return ('early',)

    class LateAction(config.Action):
        depends = [EarlyAction]

        # default priority
        def perform(self, configurable, obj):
            # make a copy of the early_performed list to
            # demonstrate it was already there when it's
            # in late_performed
            late_performed.append((configurable, list(early_performed)))

        def identifier(self, configurable):
            # at this stage we already should have performed early
            assert len(early_performed)
            return ('late',)

    c = config.Config()
    x = config.Configurable()
    y = config.Configurable(x)

    c.configurable(x)
    c.configurable(y)
    c.action(EarlyAction(x), 'foo')
    c.action(LateAction(y), 'bar')
    c.commit()
    assert early_performed == [(x, 'foo'), (y, 'foo')]
    assert late_performed == [(y, early_performed)]


def test_directive_on_method():
    performed = []

    class MyDirective(config.Directive):
        def __init__(self, configurable, foo=None):
            super(MyDirective, self).__init__(configurable)
            self.foo = foo

        def perform(self, configurable, obj):
            performed.append((obj, self.foo))

        def identifier(self, configurable):
            return self.foo

    c = config.Config()
    x = config.Configurable(testing_config=c)

    # This should error and does in Venusian mode,
    # but doesn't in testing_config mode.
    class Something(object):
        @MyDirective(x, 'A')
        def method():
            return "Result"


def test_directive_on_staticmethod():
    performed = []

    class MyDirective(config.Directive):
        def __init__(self, configurable, foo=None):
            super(MyDirective, self).__init__(configurable)
            self.foo = foo

        def perform(self, configurable, obj):
            performed.append((obj, self.foo))

        def identifier(self, configurable):
            return self.foo

    c = config.Config()
    x = config.Configurable(testing_config=c)

    # in Venusian code this will work, but we cannot support it in
    # testing_config mode, so we'll fail.
    with pytest.raises(config.DirectiveError):
        class Something(object):
            @MyDirective(x, 'A')
            @staticmethod
            def method():
                return 'result'


def test_directive_on_classmethod():
    performed = []

    class MyDirective(config.Directive):
        def __init__(self, configurable, foo=None):
            super(MyDirective, self).__init__(configurable)
            self.foo = foo

        def perform(self, configurable, obj):
            performed.append((obj, self.foo))

        def identifier(self, configurable):
            return self.foo

    c = config.Config()
    x = config.Configurable(testing_config=c)

    # in Venusian mode this will work, but we cannot support it in
    # testing_config mode so we'll fail.
    with pytest.raises(config.DirectiveError):
        class Something(object):
            @MyDirective(x, 'A')
            @classmethod
            def method(cls):
                return cls, 'result'


def test_configurable_actions():
    performed = []

    class MyAction(config.Action):
        def perform(self, configurable, obj):
            performed.append(obj)

        def identifier(self, configurable):
            return ()

    class App(config.Configurable):
        def actions(self):
            yield MyAction(self), self

    c = config.Config()
    x = App()

    c.configurable(x)
    assert performed == []
    c.commit()
    assert performed == [x]

########NEW FILE########
__FILENAME__ = test_converter
from morepath.converter import (ConverterRegistry, Converter,
                                ListConverter,
                                IDENTITY_CONVERTER)
from morepath.error import DirectiveError
import pytest


def test_converter_registry():
    r = ConverterRegistry()

    c = Converter(int, type(u""))
    r.register_converter(int, c)
    assert r.converter_for_type(int) is c
    assert r.converter_for_value(1) is c
    assert r.converter_for_value(None) is IDENTITY_CONVERTER
    with pytest.raises(DirectiveError):
        r.converter_for_value('s')


def test_converter_registry_inheritance():
    r = ConverterRegistry()

    class Lifeform(object):
        def __init__(self, name):
            self.name = name

    class Animal(Lifeform):
        pass

    seaweed = Lifeform('seaweed')
    elephant = Animal('elephant')

    lifeforms = {
        'seaweed': seaweed,
        'elephant': elephant,
        }

    def lifeform_decode(s):
        try:
            return lifeforms[s]
        except KeyError:
            raise ValueError

    def lifeform_encode(l):
        return l.name

    c = Converter(lifeform_decode, lifeform_encode)
    r.register_converter(Lifeform, c)
    assert r.converter_for_type(Lifeform) is c
    assert r.converter_for_type(Animal) is c
    assert r.converter_for_value(Lifeform('seaweed')) is c
    assert r.converter_for_value(Animal('elephant')) is c
    assert r.converter_for_value(None) is IDENTITY_CONVERTER
    with pytest.raises(DirectiveError):
        assert r.converter_for_value('s') is None
    assert r.converter_for_type(Lifeform).decode(['elephant']) is elephant
    assert r.converter_for_type(Lifeform).encode(seaweed) == ['seaweed']


def test_converter_equality():
    def decode():
        pass

    def encode():
        pass

    def other_encode():
        pass

    def other_decode():
        pass

    one = Converter(decode, encode)
    two = Converter(decode, encode)
    three = Converter(other_decode, other_encode)
    four = Converter(decode, other_encode)
    five = Converter(other_decode, encode)
    six = Converter(decode)

    l0 = ListConverter(one)
    l1 = ListConverter(one)
    l2 = ListConverter(two)
    l3 = ListConverter(three)

    assert one == two
    assert one != three
    assert one != four
    assert one != five
    assert one != six
    assert three != four
    assert four != five
    assert five != six

    assert one != l0
    assert l0 != one
    assert l0 == l1
    assert not l0 != l1
    assert l0 == l2
    assert l1 != l3
    assert not l1 == l3

########NEW FILE########
__FILENAME__ = test_directive
from .fixtures import (basic, nested, abbr, mapply_bug,
                       normalmethod, method, conflict, pkg, noconverter)
from morepath import setup
from morepath.error import (ConflictError, MountError, DirectiveError,
                            LinkError, DirectiveReportError)
from morepath.view import render_html
from morepath.app import App
from morepath.converter import Converter
import morepath
import reg

import pytest
from webtest import TestApp as Client


def setup_module(module):
    morepath.disable_implicit()


def test_basic():
    config = setup()
    config.scan(basic)
    config.commit()

    c = Client(basic.app)

    response = c.get('/foo')

    assert response.body == b'The view for model: foo'

    response = c.get('/foo/link')
    assert response.body == b'/foo'


def test_basic_json():
    config = setup()
    config.scan(basic)
    config.commit()

    c = Client(basic.app)

    response = c.get('/foo/json')

    assert response.body == b'{"id": "foo"}'


def test_basic_root():
    config = setup()
    config.scan(basic)
    config.commit()

    c = Client(basic.app)

    response = c.get('/')

    assert response.body == b'The root: ROOT'

    # + is to make sure we get the view, not the sub-model as
    # the model is greedy
    response = c.get('/+link')
    assert response.body == b'/'


def test_nested():
    config = setup()
    config.scan(nested)
    config.commit()

    c = Client(nested.outer_app)

    response = c.get('/inner/foo')

    assert response.body == b'The view for model: foo'

    response = c.get('/inner/foo/link')
    assert response.body == b'/inner/foo'


def test_abbr():
    config = setup()
    config.scan(abbr)
    config.commit()

    c = Client(abbr.app)

    response = c.get('/foo')
    assert response.body == b'Default view: foo'

    response = c.get('/foo/edit')
    assert response.body == b'Edit view: foo'


def test_scanned_normal_method():
    config = setup()
    with pytest.raises(DirectiveError):
        config.scan(normalmethod)


def test_scanned_static_method():
    config = setup()
    config.scan(method)
    config.commit()

    c = Client(method.app)

    response = c.get('/static')
    assert response.body == b'Static Method'

    root = method.Root()
    assert isinstance(root.static_method(), method.StaticMethod)


def test_scanned_class_method():
    config = setup()
    config.scan(method)
    config.commit()

    c = Client(method.app)

    response = c.get('/class')
    assert response.body == b'Class Method'

    root = method.Root()
    assert isinstance(root.class_method(), method.ClassMethod)


def test_scanned_no_converter():
    config = setup()
    config.scan(noconverter)
    with pytest.raises(DirectiveReportError):
        config.commit()


def test_scanned_conflict():
    config = setup()
    config.scan(conflict)
    with pytest.raises(ConflictError):
        config.commit()


def test_scanned_some_error():
    config = setup()
    with pytest.raises(ZeroDivisionError):
        config.scan(pkg)


def test_scanned_caller_package():
    from .fixtures import callerpkg
    callerpkg.main()

    from .fixtures.callerpkg.other import app

    c = Client(app)

    response = c.get('/')
    assert response.body == b'Hello world'


def test_scanned_caller_package_scan_module():
    from .fixtures import callerpkg2
    callerpkg2.main()

    from .fixtures.callerpkg2.other import app

    c = Client(app)

    response = c.get('/')
    assert response.body == b'Hello world'


def test_imperative():
    class Foo(object):
        pass

    @reg.generic
    def target():
        pass

    app = App()

    c = setup()
    foo = Foo()
    c.configurable(app)
    c.action(app.function(target), foo)
    c.commit()

    assert target.component(lookup=app.lookup) is foo


def test_basic_imperative():
    app = morepath.App()

    class Root(object):
        def __init__(self):
            self.value = 'ROOT'

    class Model(object):
        def __init__(self, id):
            self.id = id

    def get_model(id):
        return Model(id)

    def default(self, request):
        return "The view for model: %s" % self.id

    def link(self, request):
        return request.link(self)

    def json(self, request):
        return {'id': self.id}

    def root_default(self, request):
        return "The root: %s" % self.value

    def root_link(self, request):
        return request.link(self)

    c = setup()
    c.configurable(app)
    c.action(app.path(path=''), Root)
    c.action(app.path(model=Model, path='{id}'),
             get_model)
    c.action(app.view(model=Model),
             default)
    c.action(app.view(model=Model, name='link'),
             link)
    c.action(app.view(model=Model, name='json',
                      render=morepath.render_json),
             json)
    c.action(app.view(model=Root),
             root_default)
    c.action(app.view(model=Root, name='link'),
             root_link)
    c.commit()

    c = Client(app)

    response = c.get('/foo')
    assert response.body == b'The view for model: foo'

    response = c.get('/foo/link')
    assert response.body == b'/foo'

    response = c.get('/foo/json')
    assert response.body == b'{"id": "foo"}'

    response = c.get('/')
    assert response.body == b'The root: ROOT'

    # + is to make sure we get the view, not the sub-model
    response = c.get('/+link')
    assert response.body == b'/'


def test_basic_testing_config():
    config = setup()
    app = morepath.App(testing_config=config)

    @app.path(path='')
    class Root(object):
        def __init__(self):
            self.value = 'ROOT'

    class Model(object):
        def __init__(self, id):
            self.id = id

    @app.path(model=Model, path='{id}')
    def get_model(id):
        return Model(id)

    @app.view(model=Model)
    def default(self, request):
        return "The view for model: %s" % self.id

    @app.view(model=Model, name='link')
    def link(self, request):
        return request.link(self)

    @app.view(model=Model, name='json', render=morepath.render_json)
    def json(self, request):
        return {'id': self.id}

    @app.view(model=Root)
    def root_default(self, request):
        return "The root: %s" % self.value

    @app.view(model=Root, name='link')
    def root_link(self, request):
        return request.link(self)

    config.commit()

    c = Client(app)

    response = c.get('/foo')
    assert response.body == b'The view for model: foo'

    response = c.get('/foo/link')
    assert response.body == b'/foo'

    response = c.get('/foo/json')
    assert response.body == b'{"id": "foo"}'

    response = c.get('/')
    assert response.body == b'The root: ROOT'

    # + is to make sure we get the view, not the sub-model
    response = c.get('/+link')
    assert response.body == b'/'


def test_link_to_unknown_model():
    config = setup()
    app = morepath.App(testing_config=config)

    @app.path(path='')
    class Root(object):
        def __init__(self):
            self.value = 'ROOT'

    class Model(object):
        def __init__(self, id):
            self.id = id

    @app.view(model=Root)
    def root_link(self, request):
        try:
            return request.link(Model('foo'))
        except LinkError:
            return "Link error"

    @app.view(model=Root, name='default')
    def root_link_with_default(self, request):
        try:
            return request.link(Model('foo'), default='hey')
        except LinkError:
            return "Link Error"

    config.commit()

    c = Client(app)

    response = c.get('/')
    assert response.body == b'Link error'
    response = c.get('/default')
    assert response.body == b'Link Error'


def test_link_to_none():
    config = setup()
    app = morepath.App(testing_config=config)

    @app.path(path='')
    class Root(object):
        def __init__(self):
            self.value = 'ROOT'

    class Model(object):
        def __init__(self, id):
            self.id = id

    @app.view(model=Root)
    def root_link(self, request):
        return str(request.link(None) is None)

    @app.view(model=Root, name='default')
    def root_link_with_default(self, request):
        return request.link(None, default='unknown')

    config.commit()

    c = Client(app)

    response = c.get('/')
    assert response.body == b'True'
    response = c.get('/default')
    assert response.body == b'unknown'


def test_link_with_parameters():
    config = setup()
    app = morepath.App(testing_config=config)

    @app.path(path='')
    class Root(object):
        def __init__(self):
            self.value = 'ROOT'

    class Model(object):
        def __init__(self, id, param):
            self.id = id
            self.param = param

    @app.path(model=Model, path='{id}')
    def get_model(id, param=0):
        assert isinstance(param, int)
        return Model(id, param)

    @app.view(model=Model)
    def default(self, request):
        return "The view for model: %s %s" % (self.id, self.param)

    @app.view(model=Model, name='link')
    def link(self, request):
        return request.link(self)

    config.commit()

    c = Client(app)

    response = c.get('/foo')
    assert response.body == b'The view for model: foo 0'

    response = c.get('/foo/link')
    assert response.body == b'/foo?param=0'

    response = c.get('/foo?param=1')
    assert response.body == b'The view for model: foo 1'

    response = c.get('/foo/link?param=1')
    assert response.body == b'/foo?param=1'


def test_root_link_with_parameters():
    config = setup()
    app = morepath.App(testing_config=config)

    @app.path(path='')
    class Root(object):
        def __init__(self, param=0):
            assert isinstance(param, int)
            self.param = param

    @app.view(model=Root)
    def default(self, request):
        return "The view for root: %s" % self.param

    @app.view(model=Root, name='link')
    def link(self, request):
        return request.link(self)

    config.commit()

    c = Client(app)

    response = c.get('/')
    assert response.body == b'The view for root: 0'

    response = c.get('/link')
    assert response.body == b'/?param=0'

    response = c.get('/?param=1')
    assert response.body == b'The view for root: 1'

    response = c.get('/link?param=1')
    assert response.body == b'/?param=1'


def test_implicit_variables():
    config = setup()
    app = morepath.App(testing_config=config)

    @app.path(path='')
    class Root(object):
        pass

    class Model(object):
        def __init__(self, id):
            self.id = id

    @app.path(model=Model, path='{id}')
    def get_model(id):
        return Model(id)

    @app.view(model=Model)
    def default(self, request):
        return "The view for model: %s" % self.id

    @app.view(model=Model, name='link')
    def link(self, request):
        return request.link(self)

    config.commit()

    c = Client(app)

    response = c.get('/foo/link')
    assert response.body == b'/foo'


def test_implicit_parameters():
    config = setup()
    app = morepath.App(testing_config=config)

    @app.path(path='')
    class Root(object):
        pass

    class Model(object):
        def __init__(self, id):
            self.id = id

    @app.path(model=Model, path='foo')
    def get_model(id):
        return Model(id)

    @app.view(model=Model)
    def default(self, request):
        return "The view for model: %s" % self.id

    @app.view(model=Model, name='link')
    def link(self, request):
        return request.link(self)

    config.commit()

    c = Client(app)

    response = c.get('/foo')
    assert response.body == b'The view for model: None'
    response = c.get('/foo?id=bar')
    assert response.body == b'The view for model: bar'
    response = c.get('/foo/link')
    assert response.body == b'/foo'
    response = c.get('/foo/link?id=bar')
    assert response.body == b'/foo?id=bar'


def test_implicit_parameters_default():
    config = setup()
    app = morepath.App(testing_config=config)

    @app.path(path='')
    class Root(object):
        pass

    class Model(object):
        def __init__(self, id):
            self.id = id

    @app.path(model=Model, path='foo')
    def get_model(id='default'):
        return Model(id)

    @app.view(model=Model)
    def default(self, request):
        return "The view for model: %s" % self.id

    @app.view(model=Model, name='link')
    def link(self, request):
        return request.link(self)

    config.commit()

    c = Client(app)

    response = c.get('/foo')
    assert response.body == b'The view for model: default'
    response = c.get('/foo?id=bar')
    assert response.body == b'The view for model: bar'
    response = c.get('/foo/link')
    assert response.body == b'/foo?id=default'
    response = c.get('/foo/link?id=bar')
    assert response.body == b'/foo?id=bar'


def test_simple_root():
    config = setup()
    app = morepath.App(testing_config=config)

    class Hello(object):
        pass

    hello = Hello()

    @app.path(model=Hello, path='')
    def hello_model():
        return hello

    @app.view(model=Hello)
    def hello_view(self, request):
        return 'hello'

    config.commit()

    c = Client(app)

    response = c.get('/')
    assert response.body == b'hello'


def test_json_directive():
    config = setup()
    app = morepath.App(testing_config=config)

    @app.path(path='{id}')
    class Model(object):
        def __init__(self, id):
            self.id = id

    @app.json(model=Model)
    def json(self, request):
        return {'id': self.id}

    config.commit()

    c = Client(app)

    response = c.get('/foo')
    assert response.body == b'{"id": "foo"}'


def test_redirect():
    config = setup()
    app = morepath.App(testing_config=config)

    @app.path(path='')
    class Root(object):
        def __init__(self):
            pass

    @app.view(model=Root, render=render_html)
    def default(self, request):
        return morepath.redirect('/')

    config.commit()

    c = Client(app)

    c.get('/', status=302)


def test_root_conflict():
    config = setup()
    app = morepath.App(testing_config=config)

    @app.path(path='')
    class Root(object):
        pass

    @app.path(path='')
    class Something(object):
        pass

    with pytest.raises(ConflictError):
        config.commit()


def test_root_conflict2():
    config = setup()
    app = morepath.App(testing_config=config)

    @app.path(path='')
    class Root(object):
        pass

    @app.path(path='/')
    class Something(object):
        pass

    with pytest.raises(ConflictError):
        config.commit()


def test_root_no_conflict_different_apps():
    config = setup()
    app_a = morepath.App(testing_config=config)
    app_b = morepath.App(testing_config=config)

    @app_a.path(path='')
    class Root(object):
        pass

    @app_b.path(path='')
    class Something(object):
        pass

    config.commit()


def test_model_conflict():
    config = setup()
    app = morepath.App(testing_config=config)

    class A(object):
        pass

    @app.path(model=A, path='a')
    def get_a():
        return A()

    @app.path(model=A, path='a')
    def get_a_again():
        return A()

    with pytest.raises(ConflictError):
        config.commit()


def test_path_conflict():
    config = setup()
    app = morepath.App(testing_config=config)

    class A(object):
        pass

    class B(object):
        pass

    @app.path(model=A, path='a')
    def get_a():
        return A()

    @app.path(model=B, path='a')
    def get_b():
        return B()

    with pytest.raises(ConflictError):
        config.commit()


def test_path_conflict_with_variable():
    config = setup()
    app = morepath.App(testing_config=config)

    class A(object):
        pass

    class B(object):
        pass

    @app.path(model=A, path='a/{id}')
    def get_a(id):
        return A()

    @app.path(model=B, path='a/{id2}')
    def get_b(id):
        return B()

    with pytest.raises(ConflictError):
        config.commit()


def test_path_conflict_with_variable_different_converters():
    config = setup()
    app = morepath.App(testing_config=config)

    class A(object):
        pass

    class B(object):
        pass

    @app.path(model=A, path='a/{id}', converters=Converter(decode=int))
    def get_a(id):
        return A()

    @app.path(model=B, path='a/{id}')
    def get_b(id):
        return B()

    with pytest.raises(ConflictError):
        config.commit()


def test_model_no_conflict_different_apps():
    config = setup()
    app_a = morepath.App(testing_config=config)

    class A(object):
        pass

    @app_a.path(model=A, path='a')
    def get_a():
        return A()

    app_b = morepath.App(testing_config=config)

    @app_b.path(model=A, path='a')
    def get_a_again():
        return A()

    config.commit()


def test_view_conflict():
    config = setup()
    app = morepath.App(testing_config=config)

    class Model(object):
        pass

    @app.view(model=Model, name='a')
    def a_view(self, request):
        pass

    @app.view(model=Model, name='a')
    def a1_view(self, request):
        pass

    with pytest.raises(ConflictError):
        config.commit()


def test_view_no_conflict_different_names():
    config = setup()
    app = morepath.App(testing_config=config)

    class Model(object):
        pass

    @app.view(model=Model, name='a')
    def a_view(self, request):
        pass

    @app.view(model=Model, name='b')
    def b_view(self, request):
        pass

    config.commit()


def test_view_no_conflict_different_predicates():
    config = setup()
    app = morepath.App(testing_config=config)

    class Model(object):
        pass

    @app.view(model=Model, name='a', request_method='GET')
    def a_view(self, request):
        pass

    @app.view(model=Model, name='a', request_method='POST')
    def b_view(self, request):
        pass

    config.commit()


def test_view_no_conflict_different_apps():
    config = setup()
    app_a = morepath.App(testing_config=config)
    app_b = morepath.App(testing_config=config)

    class Model(object):
        pass

    @app_a.view(model=Model, name='a')
    def a_view(self, request):
        pass

    @app_b.view(model=Model, name='a')
    def a1_view(self, request):
        pass

    config.commit()


def test_view_conflict_with_json():
    config = setup()
    app = morepath.App(testing_config=config)

    class Model(object):
        pass

    @app.view(model=Model, name='a')
    def a_view(self, request):
        pass

    @app.json(model=Model, name='a')
    def a1_view(self, request):
        pass

    with pytest.raises(ConflictError):
        config.commit()


def test_view_conflict_with_html():
    config = setup()
    app = morepath.App(testing_config=config)

    class Model(object):
        pass

    @app.view(model=Model, name='a')
    def a_view(self, request):
        pass

    @app.html(model=Model, name='a')
    def a1_view(self, request):
        pass

    with pytest.raises(ConflictError):
        config.commit()


def test_function_conflict():
    config = setup()
    app = morepath.App(testing_config=config)

    class A(object):
        pass

    def func(a):
        pass

    @app.function(func, A)
    def a_func(self, request):
        pass

    @app.function(func, A)
    def a1_func(self, request):
        pass

    with pytest.raises(ConflictError):
        config.commit()


def test_function_no_conflict_different_apps():
    config = setup()
    app_a = morepath.App(testing_config=config)
    app_b = morepath.App(testing_config=config)

    def func(a):
        pass

    class A(object):
        pass

    @app_a.function(func, A)
    def a_func(a):
        pass

    @app_b.function(func, A)
    def a1_func(a):
        pass

    config.commit()


def test_run_app_with_context_without_it():
    config = setup()
    app = morepath.App('app', variables=['mount_id'], testing_config=config)
    config.commit()

    c = Client(app)
    with pytest.raises(MountError):
        c.get('/foo')


def test_mapply_bug():
    config = setup()
    config.scan(mapply_bug)
    config.commit()

    c = Client(mapply_bug.app)

    response = c.get('/')

    assert response.body == b'the root'


def test_abbr_imperative():
    config = setup()
    app = morepath.App(testing_config=config)

    class Model(object):
        pass

    @app.path(path='/', model=Model)
    def get_model():
        return Model()

    with app.view(model=Model) as view:
        @view()
        def default(self, request):
            return "Default view"

        @view(name='edit')
        def edit(self, request):
            return "Edit view"

    config.commit()

    c = Client(app)

    response = c.get('/')
    assert response.body == b'Default view'

    response = c.get('/edit')
    assert response.body == b'Edit view'


def test_abbr_imperative_exception_propagated():
    config = setup()
    app = morepath.App(testing_config=config)

    class Model(object):
        pass

    @app.path(path='/', model=Model)
    def get_model():
        return Model()

    with pytest.raises(ZeroDivisionError):
        with app.view(model=Model) as view:
            @view()
            def default(self, request):
                return "Default view"

            1/0

########NEW FILE########
__FILENAME__ = test_excview
import morepath
from morepath import setup
from webob.exc import HTTPNotFound
from webtest import TestApp as Client
import pytest


def setup_module(module):
    morepath.disable_implicit()


def test_404_http_exception():
    config = setup()
    app = morepath.App(testing_config=config)

    @app.path(path='')
    class Root(object):
        pass

    config.commit()

    c = Client(app)
    c.get('/', status=404)


def test_other_exception_not_handled():
    config = setup()
    app = morepath.App(testing_config=config)

    class MyException(Exception):
        pass

    @app.path(path='')
    class Root(object):
        pass

    @app.view(model=Root)
    def root_default(self, request):
        raise MyException()

    config.commit()

    c = Client(app)

    # the WSGI web server will handle any unhandled errors and turn
    # them into 500 errors
    with pytest.raises(MyException):
        c.get('/')


def test_http_exception_excview():
    config = setup()
    app = morepath.App(testing_config=config)

    @app.path(path='')
    class Root(object):
        pass

    @app.view(model=HTTPNotFound)
    def notfound_default(self, request):
        return "Not found!"

    config.commit()

    c = Client(app)
    response = c.get('/')
    assert response.body == b'Not found!'


def test_other_exception_excview():
    config = setup()
    app = morepath.App(testing_config=config)

    class MyException(Exception):
        pass

    @app.path(path='')
    class Root(object):
        pass

    @app.view(model=Root)
    def root_default(self, request):
        raise MyException()

    @app.view(model=MyException)
    def myexception_default(self, request):
        return "My exception"

    config.commit()

    c = Client(app)

    response = c.get('/')
    assert response.body == b'My exception'


def test_http_exception_excview_retain_status():
    config = setup()
    app = morepath.App(testing_config=config)

    @app.path(path='')
    class Root(object):
        pass

    @app.view(model=HTTPNotFound)
    def notfound_default(self, request):
        def set_status(response):
            response.status_code = self.code
        request.after(set_status)
        return "Not found!!"

    config.commit()

    c = Client(app)
    response = c.get('/', status=404)
    assert response.body == b'Not found!!'


def test_excview_named_view():
    config = setup()
    app = morepath.App(testing_config=config)

    @app.path(path='')
    class Root(object):
        pass

    class MyException(Exception):
        pass

    @app.view(model=Root, name='view')
    def view(self, request):
        raise MyException()

    # the view name should have no infleunce on myexception lookup
    @app.view(model=MyException)
    def myexception_default(self, request):
        return "My exception"

    config.commit()

    c = Client(app)
    response = c.get('/view')
    assert response.body == b'My exception'

########NEW FILE########
__FILENAME__ = test_extend
from morepath.app import App
from morepath import setup
from webtest import TestApp as Client
import morepath


def setup_module(module):
    morepath.disable_implicit()


def test_extends():
    config = setup()
    app = App(testing_config=config)
    extending = App(extends=[app], testing_config=config)

    @app.path(path='users/{username}')
    class User(object):
        def __init__(self, username):
            self.username = username

    @app.view(model=User)
    def render_user(self, request):
        return "User: %s" % self.username

    @extending.view(model=User, name='edit')
    def edit_user(self, request):
        return "Edit user: %s" % self.username

    config.commit()

    cl = Client(app)
    response = cl.get('/users/foo')
    assert response.body == b'User: foo'
    response = cl.get('/users/foo/edit', status=404)

    cl = Client(extending)
    response = cl.get('/users/foo')
    assert response.body == b'User: foo'
    response = cl.get('/users/foo/edit')
    assert response.body == b'Edit user: foo'


def test_overrides_view():
    config = setup()
    app = App(testing_config=config)
    overriding = App(extends=[app], testing_config=config)

    @app.path(path='users/{username}')
    class User(object):
        def __init__(self, username):
            self.username = username

    @app.view(model=User)
    def render_user(self, request):
        return "User: %s" % self.username

    @overriding.view(model=User)
    def render_user2(self, request):
        return "USER: %s" % self.username

    config.commit()

    cl = Client(app)
    response = cl.get('/users/foo')
    assert response.body == b'User: foo'

    cl = Client(overriding)
    response = cl.get('/users/foo')
    assert response.body == b'USER: foo'


def test_overrides_model():
    config = setup()
    app = App(testing_config=config)
    overriding = App(extends=[app], testing_config=config)

    @app.path(path='users/{username}')
    class User(object):
        def __init__(self, username):
            self.username = username

    @app.view(model=User)
    def render_user(self, request):
        return "User: %s" % self.username

    @overriding.path(model=User, path='users/{username}')
    def get_user(username):
        if username != 'bar':
            return None
        return User(username)

    config.commit()

    cl = Client(app)
    response = cl.get('/users/foo')
    assert response.body == b'User: foo'
    response = cl.get('/users/bar')
    assert response.body == b'User: bar'

    cl = Client(overriding)
    response = cl.get('/users/foo', status=404)
    response = cl.get('/users/bar')
    assert response.body == b'User: bar'

########NEW FILE########
__FILENAME__ = test_implicit
import morepath
import reg
from webtest import TestApp as Client


def setup_module(module):
    morepath.enable_implicit()


def setup_function(f):
    reg.implicit.clear()


def test_implicit_function():
    config = morepath.setup()
    app = morepath.App(testing_config=config)

    @app.path(path='')
    class Model(object):
        def __init__(self):
            pass

    @reg.generic
    def one():
        return "Default one"

    @reg.generic
    def two():
        return "Default two"

    @app.function(one)
    def one_impl():
        return two()

    @app.function(two)
    def two_impl():
        return "The real two"

    @app.view(model=Model)
    def default(self, request):
        return one()

    config.commit()

    c = Client(app)

    response = c.get('/')
    assert response.body == b'The real two'


def test_implicit_function_mounted():
    config = morepath.setup()
    alpha = morepath.App(testing_config=config)
    beta = morepath.App(testing_config=config, variables=['id'])

    @alpha.mount(path='mounted/{id}', app=beta)
    def mount_beta(id):
        return {'id': id}

    class AlphaRoot(object):
        pass

    class Root(object):
        def __init__(self, id):
            self.id = id

    @alpha.path(path='/', model=AlphaRoot)
    def get_alpha_root():
        return AlphaRoot()

    @beta.path(path='/', model=Root)
    def get_root(id):
        return Root(id)

    @reg.generic
    def one():
        return "Default one"

    @reg.generic
    def two():
        return "Default two"

    @beta.function(one)
    def one_impl():
        return two()

    @beta.function(two)
    def two_impl():
        return "The real two"

    @alpha.view(model=AlphaRoot)
    def alpha_default(self, request):
        return one()

    @beta.view(model=Root)
    def default(self, request):
        return "View for %s, message: %s" % (self.id, one())

    config.commit()

    c = Client(alpha)

    response = c.get('/mounted/1')
    assert response.body == b'View for 1, message: The real two'

    response = c.get('/')
    assert response.body == b'Default one'


def test_implicit_disabled():
    morepath.disable_implicit()
    config = morepath.setup()
    app = morepath.App(testing_config=config)

    @app.path(path='')
    class Model(object):
        def __init__(self):
            pass

    @reg.generic
    def one():
        return "default one"

    @app.view(model=Model)
    def default(self, request):
        try:
            return one()
        except reg.NoImplicitLookupError:
            return "No implicit found"

    config.commit()

    c = Client(app)

    response = c.get('/')
    assert response.body == b'No implicit found'

########NEW FILE########
__FILENAME__ = test_model
try:
    from urllib.parse import urlencode
except ImportError:
    # Python 2
    from urllib import urlencode
from morepath.path import register_path, get_arguments
from morepath.converter import Converter, IDENTITY_CONVERTER, ConverterRegistry
from morepath.app import App
from morepath import setup
from morepath import generic
from morepath.core import traject_consume
import morepath
import webob


def setup_module(module):
    morepath.disable_implicit()


def consume(app, path, parameters=None):
    if parameters:
        path += '?' + urlencode(parameters, True)
    request = app.request(webob.Request.blank(path).environ)
    return traject_consume(request, app, lookup=app.lookup), request


class Root(object):
    pass


class Model(object):
    pass


def test_register_path():
    config = setup()
    app = App(testing_config=config)
    root = Root()
    lookup = app.lookup

    def get_model(id):
        model = Model()
        model.id = id
        return model

    config.commit()

    register_path(app, Root, '', lambda m: {}, None, None, None, False,
                  lambda: root)
    register_path(app, Model, '{id}', lambda model: {'id': model.id},
                  None, None, None, False, get_model)
    app.register(generic.context, [object], lambda obj: {})

    obj, request = consume(app, 'a')
    assert obj.id == 'a'
    model = Model()
    model.id = 'b'
    assert generic.path(model, lookup=lookup) == ('b', {})


def test_register_path_with_parameters():
    config = setup()
    app = App(testing_config=config)
    root = Root()
    lookup = app.lookup

    def get_model(id, param='default'):
        model = Model()
        model.id = id
        model.param = param
        return model

    config.commit()

    register_path(app, Root,  '', lambda m: {}, None, None, None, False,
                  lambda: root)
    register_path(app, Model, '{id}', lambda model: {'id': model.id,
                                                     'param': model.param},
                  None, None, None, False, get_model)
    app.register(generic.context, [object], lambda obj: {})

    obj, request = consume(app, 'a')
    assert obj.id == 'a'
    assert obj.param == 'default'

    obj, request = consume(app, 'a', {'param': 'value'})
    assert obj.id == 'a'
    assert obj.param == 'value'

    model = Model()
    model.id = 'b'
    model.param = 'other'
    assert generic.path(model, lookup=lookup) == ('b', {'param': ['other']})


def test_traject_path_with_leading_slash():
    config = setup()
    app = App(testing_config=config)
    root = Root()

    def get_model(id):
        model = Model()
        model.id = id
        return model

    config.commit()

    register_path(app, Root, '', lambda m: {}, None, None, None, False,
                  lambda: root)
    register_path(app, Model, '/foo/{id}', lambda model: {'id': model.id},
                  None, None, None, False, get_model)
    app.register(generic.context, [object], lambda obj: {})

    obj, request = consume(app, 'foo/a')
    assert obj.id == 'a'
    obj, request = consume(app, '/foo/a')
    assert obj.id == 'a'


def test_get_arguments():
    def foo(a, b):
        pass
    assert get_arguments(foo, []) == {'a': None, 'b': None}


def test_get_arguments_defaults():
    def foo(a, b=1):
        pass
    assert get_arguments(foo, []) == {'a': None, 'b': 1}


def test_get_arguments_exclude():
    def foo(a, b, request):
        pass
    assert get_arguments(foo, ['request']) == {'a': None, 'b': None}


def test_argument_and_explicit_converters_none_defaults():
    class MyConverterRegistry(ConverterRegistry):
        def converter_for_type(self, t):
            return IDENTITY_CONVERTER

        def converter_for_value(self, v):
            return IDENTITY_CONVERTER

    reg = MyConverterRegistry()

    assert reg.argument_and_explicit_converters({'a': None}, {}) == {
        'a': IDENTITY_CONVERTER}


def test_argument_and_explicit_converters_explicit():
    class MyConverterRegistry(ConverterRegistry):
        def converter_for_type(self, t):
            return IDENTITY_CONVERTER

        def converter_for_value(self, v):
            return IDENTITY_CONVERTER

    reg = MyConverterRegistry()

    assert reg.argument_and_explicit_converters(
        {'a': None}, {'a': Converter(int)}) == {'a': Converter(int)}


def test_argument_and_explicit_converters_from_type():
    class MyConverterRegistry(ConverterRegistry):
        def converter_for_type(self, t):
            return Converter(int)

        def converter_for_value(self, v):
            return IDENTITY_CONVERTER

    reg = MyConverterRegistry()

    assert reg.argument_and_explicit_converters({'a': None}, {'a': int}) == {
        'a': Converter(int)}

########NEW FILE########
__FILENAME__ = test_mount_directive
import morepath
from morepath import setup
from morepath.error import LinkError, ConflictError
from webtest import TestApp as Client
import pytest


def test_model_mount_conflict():
    config = setup()
    app = morepath.App(testing_config=config)
    app2 = morepath.App(testing_config=config)

    class A(object):
        pass

    @app.path(model=A, path='a')
    def get_a():
        return A()

    @app.mount(app=app2, path='a')
    def get_mount():
        return {}

    with pytest.raises(ConflictError):
        config.commit()


def test_mount():
    config = setup()
    app = morepath.App('app', testing_config=config)
    mounted = morepath.App('mounted', testing_config=config)

    @mounted.path(path='')
    class MountedRoot(object):
        pass

    @mounted.view(model=MountedRoot)
    def root_default(self, request):
        return "The root"

    @mounted.view(model=MountedRoot, name='link')
    def root_link(self, request):
        return request.link(self)

    @app.mount(path='{id}', app=mounted)
    def get_context():
        return {}

    config.commit()

    c = Client(app)

    response = c.get('/foo')
    assert response.body == b'The root'

    response = c.get('/foo/link')
    assert response.body == b'/foo'


def test_mount_empty_context_should_fail():
    config = setup()
    app = morepath.App('app', testing_config=config)
    mounted = morepath.App('mounted', testing_config=config)

    @mounted.path(path='')
    class MountedRoot(object):
        pass

    @mounted.view(model=MountedRoot)
    def root_default(self, request):
        return "The root"

    @mounted.view(model=MountedRoot, name='link')
    def root_link(self, request):
        return request.link(self)

    @app.mount(path='{id}', app=mounted)
    def get_context():
        return None

    config.commit()

    c = Client(app)

    c.get('/foo', status=404)
    c.get('/foo/link', status=404)


def test_mount_context():
    config = setup()
    app = morepath.App('app', testing_config=config)
    mounted = morepath.App('mounted', variables=['mount_id'],
                           testing_config=config)

    @mounted.path(path='')
    class MountedRoot(object):
        def __init__(self, mount_id):
            self.mount_id = mount_id

    @mounted.view(model=MountedRoot)
    def root_default(self, request):
        return "The root for mount id: %s" % self.mount_id

    @app.mount(path='{id}', app=mounted)
    def get_context(id):
        return {
            'mount_id': id
            }

    config.commit()

    c = Client(app)

    response = c.get('/foo')
    assert response.body == b'The root for mount id: foo'
    response = c.get('/bar')
    assert response.body == b'The root for mount id: bar'


def test_mount_context_parameters():
    config = setup()
    app = morepath.App('app', testing_config=config)
    mounted = morepath.App('mounted', variables=['mount_id'],
                           testing_config=config)

    @mounted.path(path='')
    class MountedRoot(object):
        def __init__(self, mount_id):
            assert isinstance(mount_id, int)
            self.mount_id = mount_id

    @mounted.view(model=MountedRoot)
    def root_default(self, request):
        return "The root for mount id: %s" % self.mount_id

    @app.mount(path='mounts', app=mounted)
    def get_context(mount_id=0):
        return {
            'mount_id': mount_id
            }

    config.commit()

    c = Client(app)

    response = c.get('/mounts?mount_id=1')
    assert response.body == b'The root for mount id: 1'
    response = c.get('/mounts')
    assert response.body == b'The root for mount id: 0'


def test_mount_context_parameters_empty_context():
    config = setup()
    app = morepath.App('app', testing_config=config)
    mounted = morepath.App('mounted', variables=['mount_id'],
                           testing_config=config)

    @mounted.path(path='')
    class MountedRoot(object):
        # use a default parameter
        def __init__(self, mount_id='default'):
            self.mount_id = mount_id

    @mounted.view(model=MountedRoot)
    def root_default(self, request):
        return "The root for mount id: %s" % self.mount_id

    # the context does not in fact construct the context.
    # this means the parameters are instead constructed from the
    # arguments of the MountedRoot constructor, and these
    # default to 'default'
    @app.mount(path='{id}', app=mounted)
    def get_context(id):
        return {}

    config.commit()

    c = Client(app)

    response = c.get('/foo')
    assert response.body == b'The root for mount id: default'
    # the URL parameter mount_id cannot interfere with the mounting
    # process
    response = c.get('/bar?mount_id=blah')
    assert response.body == b'The root for mount id: default'


def test_mount_context_standalone():
    config = setup()
    app = morepath.App('mounted', variables=['mount_id'],
                       testing_config=config)

    @app.path(path='')
    class Root(object):
        def __init__(self, mount_id):
            self.mount_id = mount_id

    @app.view(model=Root)
    def root_default(self, request):
        return "The root for mount id: %s" % self.mount_id

    config.commit()

    c = Client(app.mounted(mount_id='foo'))

    response = c.get('/')
    assert response.body == b'The root for mount id: foo'


def test_mount_parent_link():
    config = setup()
    app = morepath.App('app', testing_config=config)

    @app.path(path='models/{id}')
    class Model(object):
        def __init__(self, id):
            self.id = id

    mounted = morepath.App('mounted', variables=['mount_id'],
                           testing_config=config)

    @mounted.path(path='')
    class MountedRoot(object):
        def __init__(self, mount_id):
            self.mount_id = mount_id

    @mounted.view(model=MountedRoot)
    def root_default(self, request):
        return request.parent.link(Model('one'))

    @app.mount(path='{id}', app=mounted)
    def get_context(id):
        return {
            'mount_id': id
            }

    config.commit()

    c = Client(app)

    response = c.get('/foo')
    assert response.body == b'/models/one'


def test_mount_child_link():
    config = setup()
    app = morepath.App('app', testing_config=config)
    mounted = morepath.App('mounted', variables=['mount_id'],
                           testing_config=config)

    @mounted.path(path='models/{id}')
    class Model(object):
        def __init__(self, id):
            self.id = id

    @app.path(path='')
    class Root(object):
        pass

    @app.view(model=Root)
    def app_root_default(self, request):
        return request.child(mounted, id='foo').link(Model('one'))

    @app.mount(path='{id}', app=mounted)
    def get_context(id):
        return {
            'mount_id': id
            }

    config.commit()

    c = Client(app)

    response = c.get('/')
    assert response.body == b'/foo/models/one'


def test_mount_child_link_unknown_child():
    config = setup()
    app = morepath.App('app', testing_config=config)
    mounted = morepath.App('mounted', variables=['mount_id'],
                           testing_config=config)

    @mounted.path(path='models/{id}')
    class Model(object):
        def __init__(self, id):
            self.id = id

    @app.path(path='')
    class Root(object):
        pass

    @app.view(model=Root)
    def app_root_default(self, request):
        try:
            return request.child(mounted, id='foo').link(Model('one'))
        except LinkError:
            return 'link error'

    @app.mount(path='{id}', app=mounted)
    def get_context(id):
        # no child will be found ever
        return None

    config.commit()

    c = Client(app)

    response = c.get('/')
    assert response.body == b'link error'


def test_mount_child_link_unknown_parent():
    config = setup()
    app = morepath.App('app', testing_config=config)

    class Model(object):
        def __init__(self, id):
            self.id = id

    @app.path(path='')
    class Root(object):
        pass

    @app.view(model=Root)
    def app_root_default(self, request):
        try:
            return request.parent.link(Model('one'))
        except LinkError:
            return 'link error'

    config.commit()

    c = Client(app)

    response = c.get('/')
    assert response.body == b'link error'


def test_mount_child_link_unknown_app():
    config = setup()
    app = morepath.App('app', testing_config=config)
    mounted = morepath.App('mounted', variables=['mount_id'],
                           testing_config=config)

    @mounted.path(path='models/{id}')
    class Model(object):
        def __init__(self, id):
            self.id = id

    @app.path(path='')
    class Root(object):
        pass

    @app.view(model=Root)
    def app_root_default(self, request):
        try:
            return request.child(mounted, id='foo').link(Model('one'))
        except LinkError:
            return "link error"

    # no mounting, so mounted is unknown when making link

    config.commit()

    c = Client(app)

    response = c.get('/')
    assert response.body == b'link error'


def test_mount_repr():
    config = setup()
    app = morepath.App('app', testing_config=config)
    mounted = morepath.App('mounted', variables=['mount_id'],
                           testing_config=config)

    @mounted.path(path='models/{id}')
    class Model(object):
        def __init__(self, id):
            self.id = id

    @app.path(path='')
    class Root(object):
        pass

    @app.view(model=Root)
    def app_root_default(self, request):
        return repr(request.mounted.child(mounted, id='foo'))

    @app.mount(path='{id}', app=mounted)
    def get_context(id):
        return {
            'mount_id': id
            }

    config.commit()

    c = Client(app)

    response = c.get('/')
    assert response.body == (
        b"<morepath.Mount of <morepath.App 'mounted'> with "
        b"variables: id='foo', "
        b"parent=<morepath.Mount of <morepath.App 'app'>>>")


def test_request_view_in_mount():
    config = setup()
    app = morepath.App('app', testing_config=config)
    mounted = morepath.App('mounted', variables=['mount_id'],
                           testing_config=config)

    @app.path(path='')
    class Root(object):
        pass

    @mounted.path(path='models/{id}')
    class Model(object):
        def __init__(self, id):
            self.id = id

    @mounted.view(model=Model)
    def model_default(self, request):
        return {'hey': 'Hey'}

    @app.view(model=Root)
    def root_default(self, request):
        return request.child(mounted, id='foo').view(
            Model('x'))['hey']

    @app.mount(path='{id}', app=mounted)
    def get_context(id):
        return {
            'mount_id': id
            }

    config.commit()

    c = Client(app)

    response = c.get('/')
    assert response.body == b'Hey'


def test_request_view_in_mount_broken():
    config = setup()
    app = morepath.App('app', testing_config=config)
    mounted = morepath.App('mounted', variables=['mount_id'],
                           testing_config=config)

    @app.path(path='')
    class Root(object):
        pass

    @mounted.path(path='models/{id}')
    class Model(object):
        def __init__(self, id):
            self.id = id

    @mounted.view(model=Model)
    def model_default(self, request):
        return {'hey': 'Hey'}

    @app.view(model=Root)
    def root_default(self, request):
        try:
            return request.child(mounted, id='foo').view(
                Model('x'))['hey']
        except LinkError:
            return "link error"

    # deliberately don't mount so using view is broken

    config.commit()

    c = Client(app)

    response = c.get('/')
    assert response.body == b'link error'


def test_mount_implict_converters():
    config = setup()

    app = morepath.App(testing_config=config)
    mounted = morepath.App(testing_config=config)

    class MountedRoot(object):
        def __init__(self, id):
            self.id = id

    @mounted.path(path='', model=MountedRoot)
    def get_root(id):
        return MountedRoot(id)

    @mounted.view(model=MountedRoot)
    def root_default(self, request):
        return "The root for: %s %s" % (self.id, type(self.id))

    @app.mount(path='{id}', app=mounted)
    def get_context(id=0):
        return {'id': id}

    config.commit()

    c = Client(app)

    response = c.get('/1')
    assert response.body in \
        (b"The root for: 1 <type 'int'>", b"The root for: 1 <class 'int'>")


def test_mount_explicit_converters():
    config = setup()

    app = morepath.App(testing_config=config)
    mounted = morepath.App(testing_config=config)

    class MountedRoot(object):
        def __init__(self, id):
            self.id = id

    @mounted.path(path='', model=MountedRoot)
    def get_root(id):
        return MountedRoot(id)

    @mounted.view(model=MountedRoot)
    def root_default(self, request):
        return "The root for: %s %s" % (self.id, type(self.id))

    @app.mount(path='{id}', app=mounted, converters=dict(id=int))
    def get_context(id):
        return {'id': id}

    config.commit()

    c = Client(app)

    response = c.get('/1')
    assert response.body in \
        (b"The root for: 1 <type 'int'>", b"The root for: 1 <class 'int'>")

########NEW FILE########
__FILENAME__ = test_path_directive
import morepath
from morepath import setup
from morepath.converter import Converter
from morepath.error import DirectiveReportError, ConfigError

from webtest import TestApp as Client
import pytest


def setup_module(module):
    morepath.disable_implicit()


def test_simple_path_one_step():
    config = setup()
    app = morepath.App(testing_config=config)

    class Model(object):
        def __init__(self):
            pass

    @app.path(model=Model, path='simple')
    def get_model():
        return Model()

    @app.view(model=Model)
    def default(self, request):
        return "View"

    @app.view(model=Model, name='link')
    def link(self, request):
        return request.link(self)

    config.commit()

    c = Client(app)

    response = c.get('/simple')
    assert response.body == b'View'

    response = c.get('/simple/link')
    assert response.body == b'/simple'


def test_simple_path_two_steps():
    config = setup()
    app = morepath.App(testing_config=config)

    class Model(object):
        def __init__(self):
            pass

    @app.path(model=Model, path='one/two')
    def get_model():
        return Model()

    @app.view(model=Model)
    def default(self, request):
        return "View"

    @app.view(model=Model, name='link')
    def link(self, request):
        return request.link(self)

    config.commit()

    c = Client(app)

    response = c.get('/one/two')
    assert response.body == b'View'

    response = c.get('/one/two/link')
    assert response.body == b'/one/two'


def test_variable_path_one_step():
    config = setup()
    app = morepath.App(testing_config=config)

    class Model(object):
        def __init__(self, name):
            self.name = name

    @app.path(model=Model, path='{name}')
    def get_model(name):
        return Model(name)

    @app.view(model=Model)
    def default(self, request):
        return "View: %s" % self.name

    @app.view(model=Model, name='link')
    def link(self, request):
        return request.link(self)

    config.commit()

    c = Client(app)

    response = c.get('/foo')
    assert response.body == b'View: foo'

    response = c.get('/foo/link')
    assert response.body == b'/foo'


def test_variable_path_two_steps():
    config = setup()
    app = morepath.App(testing_config=config)

    class Model(object):
        def __init__(self, name):
            self.name = name

    @app.path(model=Model, path='document/{name}')
    def get_model(name):
        return Model(name)

    @app.view(model=Model)
    def default(self, request):
        return "View: %s" % self.name

    @app.view(model=Model, name='link')
    def link(self, request):
        return request.link(self)

    config.commit()

    c = Client(app)

    response = c.get('/document/foo')
    assert response.body == b'View: foo'

    response = c.get('/document/foo/link')
    assert response.body == b'/document/foo'


def test_variable_path_two_variables():
    config = setup()
    app = morepath.App(testing_config=config)

    class Model(object):
        def __init__(self, name, version):
            self.name = name
            self.version = version

    @app.path(model=Model, path='{name}-{version}')
    def get_model(name, version):
        return Model(name, version)

    @app.view(model=Model)
    def default(self, request):
        return "View: %s %s" % (self.name, self.version)

    @app.view(model=Model, name='link')
    def link(self, request):
        return request.link(self)

    config.commit()

    c = Client(app)

    response = c.get('/foo-one')
    assert response.body == b'View: foo one'

    response = c.get('/foo-one/link')
    assert response.body == b'/foo-one'


def test_variable_path_explicit_converter():
    config = setup()
    app = morepath.App(testing_config=config)

    class Model(object):
        def __init__(self, id):
            self.id = id

    @app.path(model=Model, path='{id}',
              converters=dict(id=Converter(int)))
    def get_model(id):
        return Model(id)

    @app.view(model=Model)
    def default(self, request):
        return "View: %s (%s)" % (self.id, type(self.id))

    @app.view(model=Model, name='link')
    def link(self, request):
        return request.link(self)

    config.commit()

    c = Client(app)

    response = c.get('/1')
    assert response.body in \
        (b"View: 1 (<type 'int'>)", b"View: 1 (<class 'int'>)")

    response = c.get('/1/link')
    assert response.body == b'/1'

    response = c.get('/broken', status=404)


def test_variable_path_implicit_converter():
    config = setup()
    app = morepath.App(testing_config=config)

    class Model(object):
        def __init__(self, id):
            self.id = id

    @app.path(model=Model, path='{id}')
    def get_model(id=0):
        return Model(id)

    @app.view(model=Model)
    def default(self, request):
        return "View: %s (%s)" % (self.id, type(self.id))

    @app.view(model=Model, name='link')
    def link(self, request):
        return request.link(self)

    config.commit()

    c = Client(app)

    response = c.get('/1')
    assert response.body in \
        (b"View: 1 (<type 'int'>)", b"View: 1 (<class 'int'>)")

    response = c.get('/1/link')
    assert response.body == b'/1'

    response = c.get('/broken', status=404)


def test_variable_path_explicit_trumps_implicit():
    config = setup()
    app = morepath.App(testing_config=config)

    class Model(object):
        def __init__(self, id):
            self.id = id

    @app.path(model=Model, path='{id}',
              converters=dict(id=Converter(int)))
    def get_model(id='foo'):
        return Model(id)

    @app.view(model=Model)
    def default(self, request):
        return "View: %s (%s)" % (self.id, type(self.id))

    @app.view(model=Model, name='link')
    def link(self, request):
        return request.link(self)

    config.commit()

    c = Client(app)

    response = c.get('/1')
    assert response.body in \
        (b"View: 1 (<type 'int'>)", b"View: 1 (<class 'int'>)")

    response = c.get('/1/link')
    assert response.body == b'/1'

    response = c.get('/broken', status=404)


def test_url_parameter_explicit_converter():
    config = setup()
    app = morepath.App(testing_config=config)

    class Model(object):
        def __init__(self, id):
            self.id = id

    @app.path(model=Model, path='/',
              converters=dict(id=Converter(int)))
    def get_model(id):
        return Model(id)

    @app.view(model=Model)
    def default(self, request):
        return "View: %s (%s)" % (self.id, type(self.id))

    @app.view(model=Model, name='link')
    def link(self, request):
        return request.link(self)

    config.commit()

    c = Client(app)

    response = c.get('/?id=1')
    assert response.body in \
        (b"View: 1 (<type 'int'>)", b"View: 1 (<class 'int'>)")

    response = c.get('/link?id=1')
    assert response.body == b'/?id=1'

    response = c.get('/?id=broken', status=400)

    response = c.get('/')
    assert response.body in \
        (b"View: None (<type 'NoneType'>)", b"View: None (<class 'NoneType'>)")


def test_url_parameter_explicit_converter_get_converters():
    config = setup()
    app = morepath.App(testing_config=config)

    class Model(object):
        def __init__(self, id):
            self.id = id

    def get_converters():
        return dict(id=Converter(int))

    @app.path(model=Model, path='/', get_converters=get_converters)
    def get_model(id):
        return Model(id)

    @app.view(model=Model)
    def default(self, request):
        return "View: %s (%s)" % (self.id, type(self.id))

    @app.view(model=Model, name='link')
    def link(self, request):
        return request.link(self)

    config.commit()

    c = Client(app)

    response = c.get('/?id=1')
    assert response.body in \
        (b"View: 1 (<type 'int'>)", b"View: 1 (<class 'int'>)")

    response = c.get('/link?id=1')
    assert response.body == b'/?id=1'

    response = c.get('/?id=broken', status=400)

    response = c.get('/')
    assert response.body in \
        (b"View: None (<type 'NoneType'>)", b"View: None (<class 'NoneType'>)")


def test_url_parameter_get_converters_overrides_converters():
    config = setup()
    app = morepath.App(testing_config=config)

    class Model(object):
        def __init__(self, id):
            self.id = id

    def get_converters():
        return dict(id=Converter(int))

    @app.path(model=Model, path='/', converters={id: type(u"")},
              get_converters=get_converters)
    def get_model(id):
        return Model(id)

    @app.view(model=Model)
    def default(self, request):
        return "View: %s (%s)" % (self.id, type(self.id))

    @app.view(model=Model, name='link')
    def link(self, request):
        return request.link(self)

    config.commit()

    c = Client(app)

    response = c.get('/?id=1')
    assert response.body in \
        (b"View: 1 (<type 'int'>)", b"View: 1 (<class 'int'>)")

    response = c.get('/link?id=1')
    assert response.body == b'/?id=1'

    response = c.get('/?id=broken', status=400)

    response = c.get('/')
    assert response.body in \
        (b"View: None (<type 'NoneType'>)", b"View: None (<class 'NoneType'>)")


def test_url_parameter_implicit_converter():
    config = setup()
    app = morepath.App(testing_config=config)

    class Model(object):
        def __init__(self, id):
            self.id = id

    @app.path(model=Model, path='/')
    def get_model(id=0):
        return Model(id)

    @app.view(model=Model)
    def default(self, request):
        return "View: %s (%s)" % (self.id, type(self.id))

    @app.view(model=Model, name='link')
    def link(self, request):
        return request.link(self)

    config.commit()

    c = Client(app)

    response = c.get('/?id=1')
    assert response.body in \
        (b"View: 1 (<type 'int'>)", b"View: 1 (<class 'int'>)")

    response = c.get('/link?id=1')
    assert response.body == b'/?id=1'

    response = c.get('/?id=broken', status=400)

    response = c.get('/')
    assert response.body in \
        (b"View: 0 (<type 'int'>)", b"View: 0 (<class 'int'>)")


def test_url_parameter_explicit_trumps_implicit():
    config = setup()
    app = morepath.App(testing_config=config)

    class Model(object):
        def __init__(self, id):
            self.id = id

    @app.path(model=Model, path='/',
              converters=dict(id=Converter(int)))
    def get_model(id='foo'):
        return Model(id)

    @app.view(model=Model)
    def default(self, request):
        return "View: %s (%s)" % (self.id, type(self.id))

    @app.view(model=Model, name='link')
    def link(self, request):
        return request.link(self)

    config.commit()

    c = Client(app)

    response = c.get('/?id=1')
    assert response.body in \
        (b"View: 1 (<type 'int'>)", b"View: 1 (<class 'int'>)")

    response = c.get('/link?id=1')
    assert response.body == b'/?id=1'

    response = c.get('/?id=broken', status=400)

    response = c.get('/')
    assert response.body in \
        (b"View: foo (<type 'str'>)", b"View: foo (<class 'str'>)")


def test_decode_encode():
    config = setup()
    app = morepath.App(testing_config=config)

    class Model(object):
        def __init__(self, id):
            self.id = id

    def my_decode(s):
        return s + 'ADD'

    def my_encode(s):
        return s[:-len('ADD')]

    @app.path(model=Model, path='/',
              converters=dict(id=Converter(my_decode, my_encode)))
    def get_model(id):
        return Model(id)

    @app.view(model=Model)
    def default(self, request):
        return "View: %s" % self.id

    @app.view(model=Model, name='link')
    def link(self, request):
        return request.link(self)

    config.commit()

    c = Client(app)

    response = c.get('/?id=foo')
    assert response.body == b"View: fooADD"

    response = c.get('/link?id=foo')
    assert response.body == b'/?id=foo'


def test_unknown_converter():
    config = setup()
    app = morepath.App(testing_config=config)

    class Model(object):
        def __init__(self, d):
            self.d = d

    class Unknown(object):
        pass

    @app.path(model=Model, path='/')
    def get_model(d=Unknown()):
        return Model(d)

    @app.view(model=Model)
    def default(self, request):
        return "View: %s" % self.d

    @app.view(model=Model, name='link')
    def link(self, request):
        return request.link(self)

    with pytest.raises(DirectiveReportError):
        config.commit()


def test_unknown_explicit_converter():
    config = setup()
    app = morepath.App(testing_config=config)

    class Model(object):
        def __init__(self, d):
            self.d = d

    class Unknown(object):
        pass

    @app.path(model=Model, path='/', converters={'d': Unknown})
    def get_model(d):
        return Model(d)

    @app.view(model=Model)
    def default(self, request):
        return "View: %s" % self.d

    @app.view(model=Model, name='link')
    def link(self, request):
        return request.link(self)

    with pytest.raises(DirectiveReportError):
        config.commit()


def test_default_date_converter():
    config = setup()
    app = morepath.App(testing_config=config)

    class Model(object):
        def __init__(self, d):
            self.d = d

    from datetime import date

    @app.path(model=Model, path='/')
    def get_model(d=date(2011, 1, 1)):
        return Model(d)

    @app.view(model=Model)
    def default(self, request):
        return "View: %s" % self.d

    @app.view(model=Model, name='link')
    def link(self, request):
        return request.link(self)

    config.commit()

    c = Client(app)

    response = c.get('/?d=20121110')
    assert response.body == b"View: 2012-11-10"

    response = c.get('/')
    assert response.body == b"View: 2011-01-01"

    response = c.get('/link?d=20121110')
    assert response.body == b'/?d=20121110'

    response = c.get('/link')
    assert response.body == b'/?d=20110101'

    response = c.get('/?d=broken', status=400)


def test_default_datetime_converter():
    config = setup()
    app = morepath.App(testing_config=config)

    class Model(object):
        def __init__(self, d):
            self.d = d

    from datetime import datetime

    @app.path(model=Model, path='/')
    def get_model(d=datetime(2011, 1, 1, 10, 30)):
        return Model(d)

    @app.view(model=Model)
    def default(self, request):
        return "View: %s" % self.d

    @app.view(model=Model, name='link')
    def link(self, request):
        return request.link(self)

    config.commit()

    c = Client(app)

    response = c.get('/?d=20121110T144530')
    assert response.body == b"View: 2012-11-10 14:45:30"

    response = c.get('/')
    assert response.body == b"View: 2011-01-01 10:30:00"

    response = c.get('/link?d=20121110T144500')
    assert response.body == b'/?d=20121110T144500'

    response = c.get('/link')
    assert response.body == b'/?d=20110101T103000'

    response = c.get('/?d=broken', status=400)


def test_custom_date_converter():
    config = setup()
    app = morepath.App(testing_config=config)

    class Model(object):
        def __init__(self, d):
            self.d = d

    from datetime import date
    from time import strptime, mktime

    def date_decode(s):
        return date.fromtimestamp(mktime(strptime(s, '%d-%m-%Y')))

    def date_encode(d):
        return d.strftime('%d-%m-%Y')

    @app.converter(type=date)
    def date_converter():
        return Converter(date_decode, date_encode)

    @app.path(model=Model, path='/')
    def get_model(d=date(2011, 1, 1)):
        return Model(d)

    @app.view(model=Model)
    def default(self, request):
        return "View: %s" % self.d

    @app.view(model=Model, name='link')
    def link(self, request):
        return request.link(self)

    config.commit()

    c = Client(app)

    response = c.get('/?d=10-11-2012')
    assert response.body == b"View: 2012-11-10"

    response = c.get('/')
    assert response.body == b"View: 2011-01-01"

    response = c.get('/link?d=10-11-2012')
    assert response.body == b'/?d=10-11-2012'

    response = c.get('/link')
    assert response.body == b'/?d=01-01-2011'

    response = c.get('/?d=broken', status=400)


def test_variable_path_parameter_required_no_default():
    config = setup()
    app = morepath.App(testing_config=config)

    class Model(object):
        def __init__(self, id):
            self.id = id

    @app.path(model=Model, path='', required=['id'])
    def get_model(id):
        return Model(id)

    @app.view(model=Model)
    def default(self, request):
        return "View: %s" % self.id

    @app.view(model=Model, name='link')
    def link(self, request):
        return request.link(self)

    config.commit()

    c = Client(app)

    response = c.get('/?id=a')
    assert response.body == b"View: a"

    response = c.get('/', status=400)


def test_variable_path_parameter_required_with_default():
    config = setup()
    app = morepath.App(testing_config=config)

    class Model(object):
        def __init__(self, id):
            self.id = id

    @app.path(model=Model, path='', required=['id'])
    def get_model(id='b'):
        return Model(id)

    @app.view(model=Model)
    def default(self, request):
        return "View: %s" % self.id

    @app.view(model=Model, name='link')
    def link(self, request):
        return request.link(self)

    config.commit()

    c = Client(app)

    response = c.get('/?id=a')
    assert response.body == b"View: a"

    response = c.get('/', status=400)


def test_type_hints_and_converters():
    config = setup()
    app = morepath.App(testing_config=config)

    class Model(object):
        def __init__(self, d):
            self.d = d

    from datetime import date

    @app.path(model=Model, path='', converters=dict(d=date))
    def get_model(d):
        return Model(d)

    @app.view(model=Model)
    def default(self, request):
        return "View: %s" % self.d

    @app.view(model=Model, name='link')
    def link(self, request):
        return request.link(self)

    config.commit()

    c = Client(app)

    response = c.get('/?d=20140120')
    assert response.body == b"View: 2014-01-20"

    response = c.get('/link?d=20140120')
    assert response.body == b'/?d=20140120'


def test_link_for_none_means_no_parameter():
    config = setup()
    app = morepath.App(testing_config=config)

    class Model(object):
        def __init__(self, id):
            self.id = id

    @app.path(model=Model, path='')
    def get_model(id):
        return Model(id)

    @app.view(model=Model)
    def default(self, request):
        return "View: %s" % self.id

    @app.view(model=Model, name='link')
    def link(self, request):
        return request.link(self)

    config.commit()

    c = Client(app)

    response = c.get('/')
    assert response.body == b"View: None"

    response = c.get('/link')
    assert response.body == b'/'


def test_path_and_url_parameter_converter():
    config = setup()
    app = morepath.App(testing_config=config)

    class Model(object):
        def __init__(self, id, param):
            self.id = id
            self.param = param

    from datetime import date

    @app.path(model=Model, path='/{id}', converters=dict(param=date))
    def get_model(id=0, param=None):
        return Model(id, param)

    @app.view(model=Model)
    def default(self, request):
        return "View: %s %s" % (self.id, self.param)

    @app.view(model=Model, name='link')
    def link(self, request):
        return request.link(self)

    config.commit()

    c = Client(app)

    response = c.get('/1/link')
    assert response.body == b'/1'


def test_root_named_link():
    config = setup()
    app = morepath.App(testing_config=config)

    @app.path(path='')
    class Root(object):
        pass

    @app.view(model=Root)
    def default(self, request):
        return request.link(self, 'foo')

    config.commit()

    c = Client(app)

    response = c.get('/')
    assert response.body == b'/foo'


def test_path_class_and_model_argument():
    config = setup()
    app = morepath.App(testing_config=config)

    class Foo(object):
        pass

    @app.path(path='', model=Foo)
    class Root(object):
        pass

    with pytest.raises(ConfigError):
        config.commit()


def test_path_no_class_and_no_model_argument():
    config = setup()
    app = morepath.App(testing_config=config)

    @app.path(path='')
    def get_foo():
        return None

    with pytest.raises(ConfigError):
        config.commit()


def test_url_parameter_list():
    config = setup()
    app = morepath.App(testing_config=config)

    class Model(object):
        def __init__(self, item):
            self.item = item

    @app.path(model=Model, path='/', converters={'item': [int]})
    def get_model(item):
        return Model(item)

    @app.view(model=Model)
    def default(self, request):
        return repr(self.item)

    @app.view(model=Model, name='link')
    def link(self, request):
        return request.link(self)

    config.commit()

    c = Client(app)

    response = c.get('/?item=1&item=2')
    assert response.body == b"[1, 2]"

    response = c.get('/link?item=1&item=2')
    assert response.body == b'/?item=1&item=2'

    response = c.get('/link')
    assert response.body == b'/'

    response = c.get('/?item=broken&item=1', status=400)

    response = c.get('/')
    assert response.body == b"[]"


def test_url_parameter_list_empty():
    config = setup()
    app = morepath.App(testing_config=config)

    class Model(object):
        def __init__(self, item):
            self.item = item

    @app.path(model=Model, path='/', converters={'item': []})
    def get_model(item):
        return Model(item)

    @app.view(model=Model)
    def default(self, request):
        return repr(self.item)

    @app.view(model=Model, name='link')
    def link(self, request):
        return request.link(self)

    config.commit()

    c = Client(app)

    response = c.get('/?item=a&item=b')
    assert response.body in (b"[u'a', u'b']", b"['a', 'b']")

    response = c.get('/link?item=a&item=b')
    assert response.body == b'/?item=a&item=b'

    response = c.get('/link')
    assert response.body == b'/'

    response = c.get('/')
    assert response.body == b"[]"


def test_url_parameter_list_explicit_converter():
    config = setup()
    app = morepath.App(testing_config=config)

    class Model(object):
        def __init__(self, item):
            self.item = item

    @app.path(model=Model, path='/', converters={'item': [Converter(int)]})
    def get_model(item):
        return Model(item)

    @app.view(model=Model)
    def default(self, request):
        return repr(self.item)

    @app.view(model=Model, name='link')
    def link(self, request):
        return request.link(self)

    config.commit()

    c = Client(app)

    response = c.get('/?item=1&item=2')
    assert response.body == b"[1, 2]"

    response = c.get('/link?item=1&item=2')
    assert response.body == b'/?item=1&item=2'

    response = c.get('/link')
    assert response.body == b'/'

    response = c.get('/?item=broken&item=1', status=400)

    response = c.get('/')
    assert response.body == b"[]"


def test_url_parameter_list_unknown_explicit_converter():
    config = setup()
    app = morepath.App(testing_config=config)

    class Model(object):
        def __init__(self, item):
            self.item = item

    class Unknown(object):
        pass

    @app.path(model=Model, path='/', converters={'item': [Unknown]})
    def get_model(item):
        return Model(item)

    with pytest.raises(DirectiveReportError):
        config.commit()


def test_url_parameter_list_but_only_one_allowed():
    config = setup()
    app = morepath.App(testing_config=config)

    class Model(object):
        def __init__(self, item):
            self.item = item

    @app.path(model=Model, path='/', converters={'item': int})
    def get_model(item):
        return Model(item)

    @app.view(model=Model)
    def default(self, request):
        return repr(self.item)

    @app.view(model=Model, name='link')
    def link(self, request):
        return request.link(self)

    config.commit()

    c = Client(app)

    c.get('/?item=1&item=2', status=400)

    c.get('/link?item=1&item=2', status=400)


def test_extra_parameters():
    config = setup()
    app = morepath.App(testing_config=config)

    class Model(object):
        def __init__(self, extra_parameters):
            self.extra_parameters = extra_parameters

    @app.path(model=Model, path='/')
    def get_model(extra_parameters):
        return Model(extra_parameters)

    @app.view(model=Model)
    def default(self, request):
        return repr(sorted(self.extra_parameters.items()))

    @app.view(model=Model, name='link')
    def link(self, request):
        return request.link(self)

    config.commit()

    c = Client(app)

    response = c.get('/?a=A&b=B')
    assert response.body in \
        (b"[(u'a', u'A'), (u'b', u'B')]", b"[('a', 'A'), ('b', 'B')]")
    response = c.get('/link?a=A&b=B')
    assert sorted(response.body[2:].split(b"&")) == [b'a=A', b'b=B']


def test_extra_parameters_with_get_converters():
    config = setup()
    app = morepath.App(testing_config=config)

    class Model(object):
        def __init__(self, extra_parameters):
            self.extra_parameters = extra_parameters

    def get_converters():
        return {
            'a': int,
            'b': type(u""),
            }

    @app.path(model=Model, path='/', get_converters=get_converters)
    def get_model(extra_parameters):
        return Model(extra_parameters)

    @app.view(model=Model)
    def default(self, request):
        return repr(sorted(self.extra_parameters.items()))

    @app.view(model=Model, name='link')
    def link(self, request):
        return request.link(self)

    config.commit()

    c = Client(app)

    response = c.get('/?a=1&b=B')
    assert response.body in \
        (b"[(u'a', 1), (u'b', u'B')]", b"[('a', 1), ('b', 'B')]")
    response = c.get('/link?a=1&b=B')
    assert sorted(response.body[2:].split(b"&")) == [b'a=1', b'b=B']


def test_script_name():
    config = setup()
    app = morepath.App(testing_config=config)

    class Model(object):
        def __init__(self):
            pass

    @app.path(model=Model, path='simple')
    def get_model():
        return Model()

    @app.view(model=Model)
    def default(self, request):
        return "View"

    @app.view(model=Model, name='link')
    def link(self, request):
        return request.link(self)

    config.commit()

    c = Client(app)

    response = c.get('/prefix/simple',
                     extra_environ=dict(SCRIPT_NAME='/prefix'))
    assert response.body == b'View'

    response = c.get('/prefix/simple/link',
                     extra_environ=dict(SCRIPT_NAME='/prefix'))
    assert response.body == b'/prefix/simple'


@pytest.mark.xfail
def test_sub_path_different_variable():
    config = setup()
    app = morepath.App(testing_config=config)

    class M(object):
        def __init__(self, id):
            self.id = id

    class S(object):
        def __init__(self, id, m):
            self.id = id
            self.m = m

    @app.path(model=M, path='{id}')
    def get_m(id):
        return M(id)

    @app.path(model=S, path='{m}/{id}')
    def get_s(m, id):
        return S(id, m)

    @app.view(model=M)
    def default_m(self, request):
        return "M: %s" % self.id

    @app.view(model=S)
    def default_s(self, request):
        return "S: %s %s" % (self.id, self.m)

    config.commit()

    c = Client(app)

    response = c.get('/a')
    assert response.body == b'M: a'

    response = c.get('/a/b')
    assert response.body == b'/S: b a'


def test_absorb_path():
    config = setup()
    app = morepath.App(testing_config=config)

    class Root(object):
        pass

    class Model(object):
        def __init__(self, absorb):
            self.absorb = absorb

    @app.path(model=Root, path='')
    def get_root():
        return Root()

    @app.path(model=Model, path='foo', absorb=True)
    def get_model(absorb):
        return Model(absorb)

    @app.view(model=Model)
    def default(self, request):
        return "%s" % self.absorb

    @app.view(model=Root)
    def default_root(self, request):
        return request.link(Model('a/b'))

    config.commit()

    c = Client(app)

    response = c.get('/foo/a')
    assert response.body == b'a'

    response = c.get('/foo')
    assert response.body == b''

    response = c.get('/foo/a/b')
    assert response.body == b'a/b'

    # link to a/b absorb
    response = c.get('/')
    assert response.body == b'/foo/a/b'


def test_absorb_path_with_variables():
    config = setup()
    app = morepath.App(testing_config=config)

    class Root(object):
        pass

    class Model(object):
        def __init__(self, id, absorb):
            self.id = id
            self.absorb = absorb

    @app.path(model=Root, path='')
    def get_root():
        return Root()

    @app.path(model=Model, path='{id}', absorb=True)
    def get_model(id, absorb):
        return Model(id, absorb)

    @app.view(model=Model)
    def default(self, request):
        return "I:%s A:%s" % (self.id, self.absorb)

    @app.view(model=Root)
    def default_root(self, request):
        return request.link(Model('foo', 'a/b'))

    config.commit()

    c = Client(app)

    response = c.get('/foo/a')
    assert response.body == b'I:foo A:a'

    response = c.get('/foo')
    assert response.body == b'I:foo A:'

    response = c.get('/foo/a/b')
    assert response.body == b'I:foo A:a/b'

    # link to a/b absorb
    response = c.get('/')
    assert response.body == b'/foo/a/b'


def test_absorb_path_explicit_subpath_ignored():
    config = setup()
    app = morepath.App(testing_config=config)

    class Root(object):
        pass

    class Model(object):
        def __init__(self, absorb):
            self.absorb = absorb

    class Another(object):
        pass

    @app.path(model=Root, path='')
    def get_root():
        return Root()

    @app.path(model=Model, path='foo', absorb=True)
    def get_model(absorb):
        return Model(absorb)

    @app.path(model=Another, path='foo/another')
    def get_another():
        return Another()

    @app.view(model=Model)
    def default(self, request):
        return "%s" % self.absorb

    @app.view(model=Another)
    def default_another(self, request):
        return "Another"

    @app.view(model=Root)
    def default_root(self, request):
        return request.link(Another())

    config.commit()

    c = Client(app)

    response = c.get('/foo/a')
    assert response.body == b'a'

    response = c.get('/foo/another')
    assert response.body == b'another'

    # link to another still works XXX is this wrong?
    response = c.get('/')
    assert response.body == b'/foo/another'


def test_absorb_path_root():
    config = setup()
    app = morepath.App(testing_config=config)

    class Model(object):
        def __init__(self, absorb):
            self.absorb = absorb

    @app.path(model=Model, path='', absorb=True)
    def get_model(absorb):
        return Model(absorb)

    @app.view(model=Model)
    def default(self, request):
        return "A:%s L:%s" % (self.absorb, request.link(self))

    config.commit()

    c = Client(app)

    response = c.get('/a')
    assert response.body == b'A:a L:/a'

    response = c.get('/')
    assert response.body == b'A: L:/'

    response = c.get('/a/b')
    assert response.body == b'A:a/b L:/a/b'

########NEW FILE########
__FILENAME__ = test_predicates
from morepath.app import App
from morepath import setup

from webtest import TestApp as Client
import morepath


def setup_module(module):
    morepath.disable_implicit()


def test_view_predicates():
    config = setup()
    app = App(testing_config=config)

    @app.path(path='')
    class Root(object):
        pass

    @app.view(model=Root, name='foo', request_method='GET')
    def get(self, request):
        return 'GET'

    @app.view(model=Root, name='foo', request_method='POST')
    def post(self, request):
        return 'POST'

    config.commit()

    c = Client(app)

    response = c.get('/foo')
    assert response.body == b'GET'
    response = c.post('/foo')
    assert response.body == b'POST'


def test_extra_predicates():
    config = setup()
    app = App(testing_config=config)

    @app.path(path='{id}')
    class Model(object):
        def __init__(self, id):
            self.id = id

    @app.view(model=Model, name='foo', id='a')
    def get_a(self, request):
        return 'a'

    @app.view(model=Model, name='foo', id='b')
    def get_b(self, request):
        return 'b'

    @app.predicate(name='id', order=2, default='')
    def get_id(self, request):
        return self.id
    config.commit()

    c = Client(app)

    response = c.get('/a/foo')
    assert response.body == b'a'
    response = c.get('/b/foo')
    assert response.body == b'b'

########NEW FILE########
__FILENAME__ = test_publish
import morepath
from morepath.app import App
from morepath.publish import publish, resolve_response
from morepath.path import register_path
from morepath.request import Response
from morepath.view import register_view, render_json, render_html
from morepath.core import setup
from webob.exc import HTTPNotFound, HTTPBadRequest
import webob

import pytest


def setup_module(module):
    morepath.disable_implicit()


def get_environ(path, **kw):
    return webob.Request.blank(path, **kw).environ


class Model(object):
    pass


def test_view():
    config = setup()
    app = App(testing_config=config)
    config.commit()

    def view(self, request):
        return "View!"

    register_view(app, Model, view, predicates=dict(name=''))

    model = Model()
    result = resolve_response(app.request(get_environ(path='')), model)
    assert result.body == b'View!'


def test_predicates():
    config = setup()
    app = App(testing_config=config)
    config.commit()

    def view(self, request):
        return "all"

    def post_view(self, request):
        return "post"

    register_view(app, Model, view, predicates=dict(name=''))
    register_view(app, Model, post_view,
                  predicates=dict(name='', request_method='POST'))

    model = Model()
    assert resolve_response(
        app.request(get_environ(path='')), model).body == b'all'
    assert (resolve_response(app.request(get_environ(path='', method='POST')),
                             model).body == b'post')


def test_notfound():
    config = setup()
    app = App(testing_config=config)
    config.commit()

    request = app.request(get_environ(path=''))
    request.mounts.append(app.mounted())

    with pytest.raises(HTTPNotFound):
        publish(request)


def test_notfound_with_predicates():
    config = setup()
    app = App(testing_config=config)
    config.commit()

    def view(self, request):
        return "view"

    register_view(app, Model, view, predicates=dict(name=''))
    model = Model()
    request = app.request(get_environ(''))
    request.unconsumed = ['foo']
    with pytest.raises(HTTPNotFound):
        resolve_response(request, model)


def test_response_returned():
    config = setup()
    app = App(testing_config=config)
    config.commit()

    def view(self, request):
        return Response('Hello world!')

    register_view(app, Model, view)
    model = Model()
    response = resolve_response(app.request(get_environ(path='')), model)
    assert response.body == b'Hello world!'


def test_request_view():
    config = setup()
    app = App(testing_config=config)
    config.commit()

    def view(self, request):
        return {'hey': 'hey'}

    register_view(app, Model, view, render=render_json)

    request = app.request(get_environ(path=''))
    request.mounts = [app]  # XXX should do this centrally

    model = Model()
    response = resolve_response(request, model)
    # when we get the response, the json will be rendered
    assert response.body == b'{"hey": "hey"}'
    assert response.content_type == 'application/json'
    # but we get the original json out when we access the view
    assert request.view(model) == {'hey': 'hey'}


def test_request_view_with_predicates():
    config = setup()
    app = App(testing_config=config)
    config.commit()

    def view(self, request):
        return {'hey': 'hey'}

    register_view(app, Model, view, render=render_json,
                  predicates=dict(name='foo'))

    request = app.request(get_environ(path=''))
    request.mounts = [app]  # XXX should do this centrally

    model = Model()
    # since the name is set to foo, we get nothing here
    assert request.view(model) is None
    # we have to pass the name predicate ourselves
    assert request.view(model, name='foo') == {'hey': 'hey'}
    # the predicate information in the request is ignored when we do a
    # manual view lookup using request.view
    request = app.request(get_environ(path='foo'))
    request.mounts = [app]  # XXX should do this centrally
    assert request.view(model) is None


def test_render_html():
    config = setup()
    app = App(testing_config=config)
    config.commit()

    def view(self, request):
        return '<p>Hello world!</p>'

    register_view(app, Model, view, render=render_html)

    request = app.request(get_environ(path=''))
    model = Model()
    response = resolve_response(request, model)
    assert response.body == b'<p>Hello world!</p>'
    assert response.content_type == 'text/html'


def test_view_raises_http_error():
    config = setup()
    app = App(testing_config=config)
    config.commit()

    def view(self, request):
        raise HTTPBadRequest()

    register_path(app, Model, 'foo', None, None, None, None, False, Model)
    register_view(app, Model, view)

    request = app.request(get_environ(path='foo'))
    request.mounts.append(app.mounted())

    with pytest.raises(HTTPBadRequest):
        publish(request)


def test_view_after():
    config = setup()
    app = App(testing_config=config)
    config.commit()

    def view(self, request):
        @request.after
        def set_header(response):
            response.headers.add('Foo', 'FOO')
        return "View!"

    register_view(app, Model, view, predicates=dict(name=''))

    model = Model()
    result = resolve_response(app.request(get_environ(path='')), model)
    assert result.body == b'View!'
    assert result.headers.get('Foo') == 'FOO'


def test_conditional_view_after():
    config = setup()
    app = App(testing_config=config)
    config.commit()

    def view(self, request):
        if False:
            @request.after
            def set_header(response):
                response.headers.add('Foo', 'FOO')
        return "View!"

    register_view(app, Model, view, predicates=dict(name=''))

    model = Model()
    result = resolve_response(app.request(get_environ(path='')), model)
    assert result.body == b'View!'
    assert result.headers.get('Foo') is None


def test_view_after_non_decorator():
    config = setup()
    app = App(testing_config=config)
    config.commit()

    def set_header(response):
        response.headers.add('Foo', 'FOO')

    def view(self, request):
        request.after(set_header)
        return "View!"

    register_view(app, Model, view, predicates=dict(name=''))

    model = Model()
    result = resolve_response(app.request(get_environ(path='')), model)
    assert result.body == b'View!'
    assert result.headers.get('Foo') == 'FOO'

########NEW FILE########
__FILENAME__ = test_reify
from morepath import reify

# from pyramid.tests.test_decorator


def test__get__with_inst():
    def wrapped(inst):
        return 'a'
    decorator = reify(wrapped)
    inst = Dummy()
    result = decorator.__get__(inst)
    assert result == 'a'
    assert inst.__dict__['wrapped'] == 'a'


def test__get__noinst():
    decorator = reify(None)
    result = decorator.__get__(None)
    assert result is decorator


def test__doc__copied():
    def wrapped(inst):
        """My doc"""

    decorator = reify(wrapped)
    assert decorator.__doc__ == 'My doc'


class Dummy(object):
    pass

########NEW FILE########
__FILENAME__ = test_resolve
# -*- coding: utf-8 -*-

from reg import Lookup, ClassRegistry
import morepath
from morepath import generic
from morepath.traject import VIEW_PREFIX
from morepath.request import Request
from morepath.publish import resolve_model
import webob


def setup_module(module):
    morepath.disable_implicit()


class Traverser(object):
    """A traverser is a consumer that consumes only a single step.

    Only the top of the stack is popped.

    Should be constructed with a traversal function. The function
    takes three arguments: the object to traverse into, and the namespace
    and name to traverse. It should return either the object traversed towards,
    or None if this object cannot be found.
    """

    def __init__(self, func):
        self.func = func

    def __call__(self, request, model, lookup):
        if not request.unconsumed:
            return None
        name = request.unconsumed.pop()
        next_model = self.func(model, name)
        if next_model is None:
            request.unconsumed.append(name)
            return None
        return next_model


def get_request(path, lookup):
    request = Request(webob.Request.blank(path).environ)
    request.lookup = lookup
    return request


def get_registry():
    return ClassRegistry()


def get_lookup(registry):
    return Lookup(registry)


class Container(dict):
    lookup = None

    def set_implicit(self):
        pass


class Model(object):
    def __repr__(self):
        return "<Model>"


def get_structure():
    """A structure of containers and models.

    The structure is:

    /a
    /sub
    /sub/b

    all starting at root.
    """

    root = Container()

    a = Model()
    root['a'] = a

    sub = Container()
    root['sub'] = sub

    b = Model()
    sub['b'] = b
    sub.attr = b

    return root


def test_resolve_no_consumers():
    lookup = get_lookup(get_registry())
    request = get_request(path='/a', lookup=lookup)

    class DummyBase(object):
        lookup = None

        def set_implicit(self):
            pass

    base = DummyBase()

    request.mounts.append(base)

    obj = resolve_model(request)

    assert obj is base
    assert request.unconsumed == [u'a']
    assert request.lookup is lookup


def test_resolve_traverse():
    reg = get_registry()

    lookup = get_lookup(reg)

    reg.register(generic.consume, [Request, Container],
                 Traverser(traverse_container))

    base = get_structure()
    request = get_request(path='/a', lookup=lookup)
    request.mounts.append(base)
    obj = resolve_model(request)
    assert obj is base['a']
    assert request.unconsumed == []
    assert request.lookup is lookup

    request = get_request(path='/sub', lookup=lookup)
    request.mounts.append(base)

    obj = resolve_model(request)
    assert obj is base['sub']
    assert request.unconsumed == []
    assert request.lookup is lookup

    request = get_request(path='/sub/b', lookup=lookup)
    request.mounts.append(base)

    obj = resolve_model(request)
    assert obj is base['sub']['b']
    assert request.unconsumed == []
    assert request.lookup is lookup

    # there is no /c
    request = get_request(path='/c', lookup=lookup)
    request.mounts.append(base)

    obj = resolve_model(request)
    assert obj is base
    assert request.unconsumed == ['c']
    assert request.lookup is lookup

    # there is a sub, but no c in sub
    request = get_request(path='/sub/c', lookup=lookup)
    request.mounts.append(base)

    obj = resolve_model(request)
    assert obj is base['sub']
    assert request.unconsumed == ['c']
    assert request.lookup is lookup


def traverse_container(container, name):
    if name.startswith(VIEW_PREFIX):
        return None
    return container.get(name)


def traverse_attributes(container, name):
    if name.startswith(VIEW_PREFIX):
        return None
    return getattr(container, name, None)

########NEW FILE########
__FILENAME__ = test_security
# -*- coding: utf-8 -*-
import morepath
from morepath import setup
from morepath.request import Response
from morepath import generic
from morepath.security import (Identity, BasicAuthIdentityPolicy,
                               NO_IDENTITY)
from .fixtures import identity_policy
import base64
import json
from webtest import TestApp as Client
try:
    from cookielib import CookieJar
except ImportError:
    from http.cookiejar import CookieJar
from webob.exc import HTTPForbidden


def setup_module(module):
    morepath.disable_implicit()


def test_no_permission():
    config = setup()
    app = morepath.App(testing_config=config)

    class Model(object):
        def __init__(self, id):
            self.id = id

    class Permission(object):
        pass

    @app.path(model=Model, path='{id}',
              variables=lambda model: {'id': model.id})
    def get_model(id):
        return Model(id)

    @app.view(model=Model, permission=Permission)
    def default(self, request):
        return "Model: %s" % self.id

    config.commit()

    c = Client(app)

    c.get('/foo', status=403)


def test_permission_directive():
    config = setup()
    app = morepath.App(testing_config=config)

    class Model(object):
        def __init__(self, id):
            self.id = id

    class Permission(object):
        pass

    @app.verify_identity()
    def verify_identity(identity):
        return True

    @app.path(model=Model, path='{id}',
              variables=lambda model: {'id': model.id})
    def get_model(id):
        return Model(id)

    @app.permission_rule(model=Model, permission=Permission)
    def get_permission(identity, model, permission):
        if model.id == 'foo':
            return True
        else:
            return False

    @app.view(model=Model, permission=Permission)
    def default(self, request):
        return "Model: %s" % self.id

    @app.identity_policy()
    class IdentityPolicy(object):
        def identify(self, request):
            return Identity('testidentity')

        def remember(self, response, request, identity):
            pass

        def forget(self, response, request):
            pass

    config.commit()

    c = Client(app)

    response = c.get('/foo')
    assert response.body == b'Model: foo'
    response = c.get('/bar', status=403)


def test_permission_directive_no_identity():
    config = setup()
    app = morepath.App(testing_config=config)

    class Model(object):
        def __init__(self, id):
            self.id = id

    class Permission(object):
        pass

    @app.path(model=Model, path='{id}',
              variables=lambda model: {'id': model.id})
    def get_model(id):
        return Model(id)

    @app.permission_rule(model=Model, permission=Permission, identity=None)
    def get_permission(identity, model, permission):
        if model.id == 'foo':
            return True
        else:
            return False

    @app.view(model=Model, permission=Permission)
    def default(self, request):
        return "Model: %s" % self.id

    config.commit()

    c = Client(app)

    response = c.get('/foo')
    assert response.body == b'Model: foo'
    response = c.get('/bar', status=403)


def test_policy_action():
    config = setup()
    config.scan(identity_policy)
    config.commit()

    c = Client(identity_policy.app)

    response = c.get('/foo')
    assert response.body == b'Model: foo'
    response = c.get('/bar', status=403)


def test_basic_auth_identity_policy():
    config = setup()
    app = morepath.App(testing_config=config)

    class Model(object):
        def __init__(self, id):
            self.id = id

    class Permission(object):
        pass

    @app.path(model=Model, path='{id}',
              variables=lambda model: {'id': model.id})
    def get_model(id):
        return Model(id)

    @app.permission_rule(model=Model, permission=Permission)
    def get_permission(identity, model, permission):
        return identity.userid == 'user' and identity.password == 'secret'

    @app.view(model=Model, permission=Permission)
    def default(self, request):
        return "Model: %s" % self.id

    @app.identity_policy()
    def policy():
        return BasicAuthIdentityPolicy()

    @app.verify_identity()
    def verify_identity(identity):
        return True

    @app.view(model=HTTPForbidden)
    def make_unauthorized(self, request):
        @request.after
        def set_status_code(response):
            response.status_code = 401
        return "Unauthorized"

    config.commit()

    c = Client(app)

    response = c.get('/foo', status=401)

    headers = {'Authorization': 'Basic ' +
               str(base64.b64encode(b'user:wrong').decode())}
    response = c.get('/foo', headers=headers, status=401)

    headers = {'Authorization': 'Basic ' +
               str(base64.b64encode(b'user:secret').decode())}
    response = c.get('/foo', headers=headers)
    assert response.body == b'Model: foo'


def test_basic_auth_identity_policy_errors():
    config = setup()
    app = morepath.App(testing_config=config)

    class Model(object):
        def __init__(self, id):
            self.id = id

    class Permission(object):
        pass

    @app.path(model=Model, path='{id}',
              variables=lambda model: {'id': model.id})
    def get_model(id):
        return Model(id)

    @app.permission_rule(model=Model, permission=Permission)
    def get_permission(identity, model, permission):
        return identity.userid == 'user' and identity.password == u'sëcret'

    @app.view(model=Model, permission=Permission)
    def default(self, request):
        return "Model: %s" % self.id

    @app.identity_policy()
    def policy():
        return BasicAuthIdentityPolicy()

    @app.verify_identity()
    def verify_identity(identity):
        return True

    config.commit()

    c = Client(app)

    response = c.get('/foo', status=403)

    headers = {'Authorization': 'Something'}
    response = c.get('/foo', headers=headers, status=403)

    headers = {'Authorization': 'Something other'}
    response = c.get('/foo', headers=headers, status=403)

    headers = {'Authorization': 'Basic ' + 'nonsense'}
    response = c.get('/foo', headers=headers, status=403)

    headers = {'Authorization': 'Basic ' + 'nonsense1'}
    response = c.get('/foo', headers=headers, status=403)

    # fallback to utf8
    headers = {
        'Authorization': 'Basic ' + str(base64.b64encode(
            u'user:sëcret'.encode('utf8')).decode())}
    response = c.get('/foo', headers=headers)
    assert response.body == b'Model: foo'

    # fallback to latin1
    headers = {
        'Authorization': 'Basic ' + str(base64.b64encode(
            u'user:sëcret'.encode('latin1')).decode())}
    response = c.get('/foo', headers=headers)
    assert response.body == b'Model: foo'

    # unknown encoding
    headers = {
        'Authorization': 'Basic ' + str(base64.b64encode(
            u'user:sëcret'.encode('cp500')).decode())}
    response = c.get('/foo', headers=headers, status=403)

    headers = {
        'Authorization': 'Basic ' + str(base64.b64encode(
            u'usersëcret'.encode('utf8')).decode())}
    response = c.get('/foo', headers=headers, status=403)

    headers = {
        'Authorization': 'Basic ' + str(base64.b64encode(
            u'user:sëcret:'.encode('utf8')).decode())}
    response = c.get('/foo', headers=headers, status=403)


def test_basic_auth_remember():
    config = setup()
    app = morepath.App(testing_config=config)

    @app.path(path='{id}',
              variables=lambda model: {'id': model.id})
    class Model(object):
        def __init__(self, id):
            self.id = id

    @app.view(model=Model)
    def default(self, request):
        # will not actually do anything as it's a no-op for basic
        # auth, but at least won't crash
        response = Response()
        generic.remember_identity(response, request, Identity('foo'),
                                  lookup=request.lookup)
        return response

    @app.identity_policy()
    def policy():
        return BasicAuthIdentityPolicy()

    config.commit()

    c = Client(app)

    response = c.get('/foo', status=200)
    assert response.body == b''


def test_basic_auth_forget():
    config = setup()
    app = morepath.App(testing_config=config)

    @app.path(path='{id}')
    class Model(object):
        def __init__(self, id):
            self.id = id

    @app.view(model=Model)
    def default(self, request):
        # will not actually do anything as it's a no-op for basic
        # auth, but at least won't crash
        response = Response(content_type='text/plain')
        generic.forget_identity(response, request, lookup=request.lookup)
        return response

    @app.identity_policy()
    def policy():
        return BasicAuthIdentityPolicy()

    config.commit()

    c = Client(app)

    response = c.get('/foo', status=200)
    assert response.body == b''

    assert sorted(response.headers.items()) == [
        ('Content-Length', '0'),
        ('Content-Type', 'text/plain; charset=UTF-8'),
        ('WWW-Authenticate', 'Basic realm="Realm"'),
        ]


class DumbCookieIdentityPolicy(object):
    """A very insecure cookie-based policy.

    Only for testing. Don't use in practice!
    """
    def identify(self, request):
        data = request.cookies.get('dumb_id', None)
        if data is None:
            return NO_IDENTITY
        data = json.loads(base64.b64decode(data).decode())
        return Identity(**data)

    def remember(self, response, request, identity):
        data = base64.b64encode(str.encode(json.dumps(identity.as_dict())))
        response.set_cookie('dumb_id', data)

    def forget(self, response, request):
        response.delete_cookie('dumb_id')


def test_cookie_identity_policy():
    config = setup()
    app = morepath.App(testing_config=config)

    @app.path(path='{id}')
    class Model(object):
        def __init__(self, id):
            self.id = id

    class Permission(object):
        pass

    @app.permission_rule(model=Model, permission=Permission)
    def get_permission(identity, model, permission):
        return identity.userid == 'user'

    @app.view(model=Model, permission=Permission)
    def default(self, request):
        return "Model: %s" % self.id

    @app.view(model=Model, name='log_in')
    def log_in(self, request):
        response = Response()
        generic.remember_identity(response, request,
                                  Identity(userid='user',
                                           payload='Amazing'),
                                  lookup=request.lookup)
        return response

    @app.view(model=Model, name='log_out')
    def log_out(self, request):
        response = Response()
        generic.forget_identity(response, request, lookup=request.lookup)
        return response

    @app.identity_policy()
    def policy():
        return DumbCookieIdentityPolicy()

    @app.verify_identity()
    def verify_identity(identity):
        return True

    config.commit()

    c = Client(app, cookiejar=CookieJar())

    response = c.get('/foo', status=403)

    response = c.get('/foo/log_in')

    response = c.get('/foo', status=200)
    assert response.body == b'Model: foo'

    response = c.get('/foo/log_out')

    response = c.get('/foo', status=403)


def test_default_verify_identity():
    config = setup()
    app = morepath.App(testing_config=config)
    config.commit()

    identity = morepath.Identity('foo')

    assert not generic.verify_identity(identity, lookup=app.lookup)


def test_verify_identity_directive():
    config = setup()
    app = morepath.App(testing_config=config)

    @app.verify_identity()
    def verify_identity(identity):
        return identity.password == 'right'

    config.commit()
    identity = morepath.Identity('foo', password='wrong')
    assert not generic.verify_identity(identity, lookup=app.lookup)
    identity = morepath.Identity('foo', password='right')
    assert generic.verify_identity(identity, lookup=app.lookup)

########NEW FILE########
__FILENAME__ = test_setting_directive
import morepath
from morepath.error import ConflictError
import pytest
from webtest import TestApp as Client


def setup_module(module):
    morepath.disable_implicit()


def test_app_extends_settings():
    config = morepath.setup()

    alpha = morepath.App(testing_config=config)
    beta = morepath.App(extends=[alpha],
                        testing_config=config)

    @alpha.setting('one', 'foo')
    def get_foo_setting():
        return 'FOO'

    @beta.setting('one', 'bar')
    def get_bar_setting():
        return 'BAR'

    config.commit()

    assert alpha.settings.one.foo == 'FOO'
    with pytest.raises(AttributeError):
        assert alpha.settings.one.bar
    assert beta.settings.one.foo == 'FOO'
    assert beta.settings.one.bar == 'BAR'


def test_app_overrides_settings():
    config = morepath.setup()

    alpha = morepath.App(testing_config=config)
    beta = morepath.App(extends=[alpha],
                        testing_config=config)

    @alpha.setting('one', 'foo')
    def get_foo_setting():
        return 'FOO'

    @beta.setting('one', 'foo')
    def get_bar_setting():
        return 'OVERRIDE'

    config.commit()

    assert alpha.settings.one.foo == 'FOO'
    assert beta.settings.one.foo == 'OVERRIDE'


def test_app_overrides_settings_three():
    config = morepath.setup()

    alpha = morepath.App(testing_config=config)
    beta = morepath.App(extends=[alpha],
                        testing_config=config)
    gamma = morepath.App(extends=[beta], testing_config=config)

    @alpha.setting('one', 'foo')
    def get_foo_setting():
        return 'FOO'

    @beta.setting('one', 'foo')
    def get_bar_setting():
        return 'OVERRIDE'

    config.commit()

    assert gamma.settings.one.foo == 'OVERRIDE'


def test_app_section_settings():
    config = morepath.setup()

    app = morepath.App(testing_config=config)

    @app.setting_section('one')
    def settings():
        return {
            'foo': "FOO",
            'bar': "BAR"
            }

    config.commit()
    assert app.settings.one.foo == 'FOO'
    assert app.settings.one.bar == 'BAR'


def test_app_section_settings_conflict():
    config = morepath.setup()

    app = morepath.App(testing_config=config)

    @app.setting_section('one')
    def settings():
        return {
            'foo': "FOO",
            'bar': "BAR"
            }

    @app.setting('one', 'foo')
    def get_foo():
        return 'another'

    with pytest.raises(ConflictError):
        config.commit()


def test_settings_function():
    morepath.enable_implicit()

    config = morepath.setup()

    app = morepath.App(testing_config=config)

    @app.setting('section', 'name')
    def setting():
        return 'LAH'

    @app.path(path='')
    class Model(object):
        def __init__(self):
            pass

    @app.view(model=Model)
    def default(self, request):
        return morepath.settings().section.name

    config.commit()

    c = Client(app)

    response = c.get('/')
    assert response.body == b'LAH'

########NEW FILE########
__FILENAME__ = test_traject
import morepath
from morepath.traject import (Traject, Node, Step, TrajectError,
                              is_identifier, parse_variables,
                              Path, parse_path, create_path)
from morepath.converter import ParameterFactory
from morepath import generic
from morepath.app import App
from morepath.request import Request
from morepath.core import traject_consume
from morepath.converter import Converter, IDENTITY_CONVERTER
import pytest
from webob.exc import HTTPBadRequest
import webob


def setup_module(module):
    morepath.disable_implicit()


class Root(object):
    pass


class Model(object):
    pass


class Special(object):
    pass


def test_name_step():
    step = Step('foo')
    assert step.s == 'foo'
    assert step.generalized == 'foo'
    assert step.parts == ('foo',)
    assert step.names == []
    assert step.converters == {}
    assert not step.has_variables()
    assert step.match('foo') == (True, {})
    assert step.match('bar') == (False, {})
    assert step.discriminator_info() == 'foo'


def test_variable_step():
    step = Step('{foo}')
    assert step.s == '{foo}'
    assert step.generalized == '{}'
    assert step.parts == ('', '')
    assert step.names == ['foo']
    assert step.converters == {}
    assert step.has_variables()
    assert step.match('bar') == (True, {'foo': 'bar'})
    assert step.discriminator_info() == '{}'


def test_mixed_step():
    step = Step('a{foo}b')
    assert step.s == 'a{foo}b'
    assert step.generalized == 'a{}b'
    assert step.parts == ('a', 'b')
    assert step.names == ['foo']
    assert step.converters == {}
    assert step.has_variables()
    assert step.match('abarb') == (True, {'foo': 'bar'})
    assert step.match('ab') == (False, {})
    assert step.match('xbary') == (False, {})
    assert step.match('yabarbx') == (False, {})
    assert step.match('afoo') == (False, {})
    assert step.discriminator_info() == 'a{}b'


def test_multi_mixed_step():
    step = Step('{foo}a{bar}')
    assert step.s == '{foo}a{bar}'
    assert step.generalized == '{}a{}'
    assert step.parts == ('', 'a', '')
    assert step.names == ['foo', 'bar']
    assert step.converters == {}
    assert step.has_variables()
    assert step.discriminator_info() == '{}a{}'


def test_converter():
    step = Step('{foo}', converters=dict(foo=Converter(int)))
    assert step.match('1') == (True, {'foo': 1})
    assert step.match('x') == (False, {})
    assert step.discriminator_info() == '{}'


def sorted_steps(l):
    steps = [Step(s) for s in l]
    return [step.s for step in sorted(steps)]


def test_steps_the_same():
    step1 = Step('{foo}')
    step2 = Step('{foo}')
    assert step1 == step2
    assert not step1 != step2
    assert not step1 < step2
    assert not step1 > step2
    assert step1 >= step2
    assert step1 <= step2


def test_step_different():
    step1 = Step('{foo}')
    step2 = Step('bar')
    assert step1 != step2
    assert not step1 == step2
    assert not step1 < step2
    assert step1 > step2
    assert step1 >= step2
    assert not step1 <= step2


def test_order_prefix_earlier():
    assert sorted_steps(['{foo}', 'prefix{foo}']) == [
        'prefix{foo}', '{foo}']


def test_order_postfix_earlier():
    assert sorted_steps(['{foo}', '{foo}postfix']) == [
        '{foo}postfix', '{foo}']


def test_order_prefix_before_postfix():
    assert sorted_steps(['{foo}', 'a{foo}', '{foo}a']) == [
        'a{foo}', '{foo}a', '{foo}']


def test_order_prefix_before_postfix2():
    assert sorted_steps(['{foo}', 'a{foo}', '{foo}b']) == [
        'a{foo}', '{foo}b', '{foo}']


def test_order_longer_prefix_before_shorter():
    assert sorted_steps(['ab{f}', 'a{f}']) == [
        'ab{f}', 'a{f}']


def test_order_longer_postfix_before_shorter():
    assert sorted_steps(['{f}ab', '{f}b']) == [
        '{f}ab', '{f}b']


def test_order_dont_care_variable_names():
    assert sorted_steps(['a{f}', 'ab{g}']) == [
        'ab{g}', 'a{f}']


def test_order_two_variables_before_one():
    assert sorted_steps(['{a}x{b}', '{a}']) == [
        '{a}x{b}', '{a}']


def test_order_two_variables_before_with_postfix():
    assert sorted_steps(['{a}x{b}x', '{a}x']) == [
        '{a}x{b}x', '{a}x']


def test_order_two_variables_before_with_prefix():
    assert sorted_steps(['x{a}x{b}', 'x{a}']) == [
        'x{a}x{b}', 'x{a}']


def test_order_two_variables_infix():
    assert sorted_steps(['{a}xyz{b}', '{a}xy{b}', '{a}yz{b}', '{a}x{b}',
                         '{a}z{b}', '{a}y{b}']) == [
        '{a}xyz{b}', '{a}yz{b}', '{a}z{b}', '{a}xy{b}', '{a}y{b}', '{a}x{b}']


def test_order_alphabetical():
    # reverse alphabetical
    assert sorted_steps(['a{f}', 'b{f}']) == [
        'b{f}', 'a{f}']
    assert sorted_steps(['{f}a', '{f}b']) == [
        '{f}b', '{f}a']


def test_invalid_step():
    with pytest.raises(TrajectError):
        Step('{foo')


def test_illegal_consecutive_variables():
    with pytest.raises(TrajectError):
        Step('{a}{b}')


def test_illegal_variable():
    with pytest.raises(TrajectError):
        Step('{a:int:int}')


def test_illegal_identifier():
    with pytest.raises(TrajectError):
        Step('{1}')


def test_unknown_converter():
    with pytest.raises(TrajectError):
        Step('{foo:blurb}')


def test_name_node():
    node = Node()
    step_node = node.add(Step('foo'))
    assert node.get('foo') == (step_node, {})
    assert node.get('bar') == (None, {})


def test_variable_node():
    node = Node()
    step_node = node.add(Step('{x}'))
    assert node.get('foo') == (step_node, {'x': 'foo'})
    assert node.get('bar') == (step_node, {'x': 'bar'})


def test_mixed_node():
    node = Node()
    step_node = node.add(Step('prefix{x}postfix'))
    assert node.get('prefixfoopostfix') == (step_node, {'x': 'foo'})
    assert node.get('prefixbarpostfix') == (step_node, {'x': 'bar'})
    assert node.get('prefixwhat') == (None, {})


def test_variable_node_specific_first():
    node = Node()
    x_node = node.add(Step('{x}'))
    prefix_node = node.add(Step('prefix{x}'))
    assert node.get('what') == (x_node, {'x': 'what'})
    assert node.get('prefixwhat') == (prefix_node, {'x': 'what'})


def test_variable_node_more_specific_first():
    node = Node()
    xy_node = node.add(Step('x{x}y'))
    xay_node = node.add(Step('xa{x}y'))
    ay_node = node.add(Step('a{x}y'))
    assert node.get('xwhaty') == (xy_node, {'x': 'what'})
    assert node.get('xawhaty') == (xay_node, {'x': 'what'})
    assert node.get('awhaty') == (ay_node, {'x': 'what'})


def test_variable_node_optional_colon():
    node = Node()
    x_node = node.add(Step('{x}'))
    xy_node = node.add(Step('{x}:{y}'))
    assert node.get('a') == (x_node, {'x': 'a'})
    assert node.get('a:b') == (xy_node, {'x': 'a', 'y': 'b'})


def test_traject_simple():
    traject = Traject()
    traject.add_pattern('a/b/c', 'abc')
    traject.add_pattern('a/b/d', 'abd')
    traject.add_pattern('x/y', 'xy')
    traject.add_pattern('x/z', 'xz')

    assert traject.consume(['c', 'b', 'a']) == ('abc', [], {})
    assert traject.consume(['d', 'b', 'a']) == ('abd', [], {})
    assert traject.consume(['y', 'x']) == ('xy', [], {})
    assert traject.consume(['z', 'x']) == ('xz', [], {})
    assert traject.consume(['d', 'c', 'b', 'a']) == ('abc', ['d'], {})
    assert traject.consume(['d', 'd', 'b', 'a']) == ('abd', ['d'], {})
    assert traject.consume(['3', '2', '1', 'y', 'x']) == (
        'xy', ['3', '2', '1'], {})
    assert traject.consume(['3', '2', '1']) == (None, ['3', '2', '1'], {})
    assert traject.consume(['b', 'a']) == (None, [], {})


def test_traject_variable_specific_first():
    traject = Traject()
    traject.add_pattern('a/{x}/b', 'axb')
    traject.add_pattern('a/prefix{x}/b', 'aprefixxb')
    assert traject.consume(['b', 'lah', 'a']) == ('axb', [], {'x': 'lah'})
    assert traject.consume(['b', 'prefixlah', 'a']) == (
        'aprefixxb', [], {'x': 'lah'})


def test_traject_multiple_steps_with_variables():
    traject = Traject()
    traject.add_pattern('{x}/{y}', 'xy')
    assert traject.consume(['y', 'x']) == ('xy', [], {'x': 'x', 'y': 'y'})


def test_traject_with_converter():
    traject = Traject()
    traject.add_pattern('{x}', 'found', dict(x=Converter(int)))
    assert traject.consume(['1']) == ('found', [], {'x': 1})
    assert traject.consume(['foo']) == (None, ['foo'], {})


def test_traject_type_conflict():
    traject = Traject()
    traject.add_pattern('{x}', 'found_int', dict(x=Converter(int)))
    with pytest.raises(TrajectError):
        traject.add_pattern('{x}', 'found_str', dict(x=Converter(str)))


def test_traject_type_conflict_default_type():
    traject = Traject()
    traject.add_pattern('{x}', 'found_str')
    with pytest.raises(TrajectError):
        traject.add_pattern('{x}', 'found_int', dict(x=Converter(int)))


def test_traject_type_conflict_explicit_default():
    traject = Traject()
    traject.add_pattern('{x}', 'found_explicit', dict(x=IDENTITY_CONVERTER))
    traject.add_pattern('{x}', 'found_implicit')
    # these add_pattern calls are equivalent so will not result in an error
    assert True


def test_traject_type_conflict_middle():
    traject = Traject()
    traject.add_pattern('a/{x}/y', 'int', dict(x=Converter(int)))
    with pytest.raises(TrajectError):
        traject.add_pattern('a/{x}/z', 'str')


def test_traject_no_type_conflict_middle():
    traject = Traject()
    traject.add_pattern('a/{x}/y', 'int', dict(x=Converter(int)))
    traject.add_pattern('a/{x}/z', 'int2', dict(x=Converter(int)))


def test_traject_greedy_middle_prefix():
    traject = Traject()
    traject.add_pattern('a/prefix{x}/y', 'prefix')
    traject.add_pattern('a/{x}/z', 'no_prefix')

    assert traject.consume(['y', 'prefixX', 'a']) == ('prefix', [], {'x': 'X'})
    assert traject.consume(['z', 'prefixX', 'a']) == (None, ['z'], {'x': 'X'})
    assert traject.consume(['z', 'blah', 'a']) == (
        'no_prefix', [], {'x': 'blah'})


def test_traject_type_conflict_middle_end():
    traject = Traject()
    traject.add_pattern('a/{x}/y', 'int', dict(x=Converter(int)))
    with pytest.raises(TrajectError):
        traject.add_pattern('a/{x}', 'str')


def test_traject_no_type_conflict_middle_end():
    traject = Traject()
    traject.add_pattern('a/{x}/y', 'int', dict(x=Converter(int)))
    traject.add_pattern('a/{x}', 'int2', dict(x=Converter(int)))
    assert True


def test_parse_path():
    assert parse_path(u'/a/b/c') == ['c', 'b', 'a']


def test_parse_path_empty():
    assert parse_path(u'') == []


def test_parse_path_slash():
    assert parse_path(u'/') == []


def test_parse_path_no_slash():
    assert parse_path('a/b/c') == ['c', 'b', 'a']


def test_parse_path_end_slash():
    assert parse_path('a/b/c/') == ['c', 'b', 'a']


def test_parse_path_multi_slash():
    assert parse_path(u'/a/b/c') == parse_path(u'/a//b/c')
    assert parse_path(u'/a/b/c') == parse_path(u'/a///b/c')


def test_create_path():
    assert create_path(['c', 'b', 'a']) == '/a/b/c'


# XXX removing /./ from paths and checking for ../


def test_identifier():
    assert is_identifier('a')
    not is_identifier('')
    assert is_identifier('a1')
    assert not is_identifier('1')
    assert is_identifier('_')
    assert is_identifier('_foo')
    assert is_identifier('foo')
    assert not is_identifier('.')


def test_parse_variables():
    assert parse_variables('No variables') == []
    assert parse_variables('The {foo} is the {bar}.') == ['foo', 'bar']
    with pytest.raises(TrajectError):
        parse_variables('{}')
    with pytest.raises(TrajectError):
        parse_variables('{1illegal}')


def consume(app, path):
    request = app.request(webob.Request.blank(path).environ)
    return traject_consume(request, app, lookup=app.lookup), request

paramfac = ParameterFactory({}, {}, [])


def test_traject_consume():
    app = App()
    traject = Traject()
    traject.add_pattern('sub', (Model, paramfac))
    app.register(generic.traject, [App], lambda base: traject)
    app.register(generic.context, [object], lambda obj: {})

    found, request = consume(app, 'sub')
    assert isinstance(found, Model)
    assert request.unconsumed == []


def test_traject_consume_parameter():
    app = App()
    traject = Traject()

    class Model(object):
        def __init__(self, a):
            self.a = a

    get_param = ParameterFactory({'a': 0}, {'a': Converter(int)}, [])
    traject.add_pattern('sub', (Model, get_param))
    app.register(generic.traject, [App], lambda base: traject)
    app.register(generic.context, [object], lambda obj: {})

    found, request = consume(app, 'sub?a=1')
    assert isinstance(found, Model)
    assert found.a == 1
    assert request.unconsumed == []
    found, request = consume(app, 'sub')
    assert isinstance(found, Model)
    assert found.a == 0
    assert request.unconsumed == []


def test_traject_consume_model_factory_gets_request():
    app = App()
    traject = Traject()

    class Model(object):
        def __init__(self, info):
            self.info = info

    def get_model(request):
        return Model(request.method)

    traject.add_pattern('sub', (get_model, paramfac))
    app.register(generic.traject, [App], lambda base: traject)
    app.register(generic.context, [object], lambda obj: {})

    found, request = consume(app, 'sub')
    assert isinstance(found, Model)
    assert request.unconsumed == []
    assert found.info == 'GET'


def test_traject_consume_not_found():
    app = App()
    found, request = consume(app, 'sub')
    assert found is None
    assert request.unconsumed == ['sub']


def test_traject_consume_factory_returns_none():
    app = App()

    traject = Traject()

    def get_model():
        return None

    traject.add_pattern('sub', (get_model, paramfac))
    app.register(generic.traject, [App], lambda base: traject)
    app.register(generic.context, [object], lambda obj: {})

    found, request = consume(app, 'sub')

    assert found is None
    assert request.unconsumed == ['sub']


def test_traject_consume_variable():
    app = App()

    traject = Traject()

    def get_model(foo):
        result = Model()
        result.foo = foo
        return result

    traject.add_pattern('{foo}', (get_model, paramfac))
    app.register(generic.traject, [App], lambda base: traject)
    app.register(generic.context, [object], lambda obj: {})

    found, request = consume(app, 'something')
    assert isinstance(found, Model)
    assert found.foo == 'something'
    assert request.unconsumed == []


def test_traject_consume_view():
    app = App()

    traject = Traject()

    def get_model(foo):
        result = Model()
        result.foo = foo
        return result

    traject.add_pattern('', (Root, paramfac))
    traject.add_pattern('{foo}', (get_model, paramfac))
    app.register(generic.traject, [App], lambda base: traject)
    app.register(generic.context, [object], lambda obj: {})

    found, request = consume(app, '+something')
    assert isinstance(found, Root)
    assert request.unconsumed == ['+something']


def test_traject_root():
    app = App()

    traject = Traject()

    traject.add_pattern('', (Root, paramfac))
    app.register(generic.traject, [App], lambda base: traject)
    app.register(generic.context, [object], lambda obj: {})

    found, request = consume(app, '')
    assert isinstance(found, Root)
    assert request.unconsumed == []


def test_traject_consume_combination():
    app = App()

    traject = Traject()

    def get_model(foo):
        result = Model()
        result.foo = foo
        return result

    traject.add_pattern('special', (Special, paramfac))
    traject.add_pattern('{foo}', (get_model, paramfac))
    app.register(generic.traject, [App], lambda base: traject)
    app.register(generic.context, [object], lambda obj: {})

    found, request = consume(app, 'something')
    assert isinstance(found, Model)
    assert request.unconsumed == []
    assert found.foo == 'something'

    found, request = consume(app, 'special')
    assert isinstance(found, Special)
    assert request.unconsumed == []


def test_traject_nested():
    app = App()

    traject = Traject()
    traject.add_pattern('a', (Model, paramfac))
    traject.add_pattern('a/b', (Special, paramfac))
    app.register(generic.traject, [App], lambda base: traject)
    app.register(generic.context, [object], lambda obj: {})

    found, request = consume(app, 'a')
    assert isinstance(found, Model)
    assert request.unconsumed == []
    found, request = consume(app, 'a/b')
    assert isinstance(found, Special)
    assert request.unconsumed == []


def test_traject_nested_not_resolved_entirely_by_consumer():
    app = App()
    traject = Traject()
    traject.add_pattern('a', (Model, paramfac))
    app.register(generic.traject, [App], lambda base: traject)
    app.register(generic.context, [object], lambda obj: {})

    found, request = consume(app, 'a')
    assert isinstance(found, Model)
    assert request.unconsumed == []
    found, request = consume(app, 'a/b')
    assert isinstance(found, Model)
    assert request.unconsumed == ['b']


def test_traject_nested_with_variable():
    app = App()

    traject = Traject()

    def get_model(id):
        result = Model()
        result.id = id
        return result

    def get_special(id):
        result = Special()
        result.id = id
        return result

    traject.add_pattern('{id}', (get_model, paramfac))
    traject.add_pattern('{id}/sub', (get_special, paramfac))
    app.register(generic.traject, [App], lambda base: traject)
    app.register(generic.context, [object], lambda obj: {})

    found, request = consume(app, 'a')
    assert isinstance(found, Model)
    assert request.unconsumed == []
    found, request = consume(app, 'b')
    assert isinstance(found, Model)
    assert request.unconsumed == []
    found, request = consume(app, 'a/sub')
    assert isinstance(found, Special)
    assert request.unconsumed == []


def test_traject_with_multiple_variables():
    app = App()

    traject = Traject()

    def get_model(first_id):
        result = Model()
        result.first_id = first_id
        return result

    def get_special(first_id, second_id):
        result = Special()
        result.first_id = first_id
        result.second_id = second_id
        return result
    traject.add_pattern('{first_id}', (get_model, paramfac))
    traject.add_pattern('{first_id}/{second_id}', (get_special, paramfac))
    app.register(generic.traject, [App], lambda base: traject)
    app.register(generic.context, [object], lambda obj: {})

    found, request = consume(app, 'a')
    assert isinstance(found, Model)
    assert found.first_id == 'a'
    assert not hasattr(found, 'second_id')
    assert request.unconsumed == []

    found, request = consume(app, 'a/b')
    assert isinstance(found, Special)
    assert found.first_id == 'a'
    assert found.second_id == 'b'
    assert request.unconsumed == []


def test_traject_no_concecutive_variables():
    traject = Traject()

    with pytest.raises(TrajectError):
        traject.add_pattern('{foo}{bar}', 'value')


def test_traject_no_duplicate_variables():
    traject = Traject()

    with pytest.raises(TrajectError):
        traject.add_pattern('{foo}-{foo}', 'value')
    with pytest.raises(TrajectError):
        traject.add_pattern('{foo}/{foo}', 'value')


def test_interpolation_str():
    assert Path('{foo} is {bar}').interpolation_str() == '%(foo)s is %(bar)s'


def test_path_discriminator():
    p = Path('/foo/{x}/bar/{y}')
    assert p.discriminator() == 'foo/{}/bar/{}'


def fake_request(path):
    return Request(webob.Request.blank(path).environ)


def test_empty_parameter_factory():
    get_parameters = ParameterFactory({}, {}, [])
    assert get_parameters(fake_request('').GET) == {}
    # unexpected parameter is ignored
    assert get_parameters(fake_request('?a=A').GET) == {}


def test_single_parameter():
    get_parameters = ParameterFactory({'a': None}, {'a': Converter(str)}, [])
    assert get_parameters(fake_request('?a=A').GET) == {'a': 'A'}
    assert get_parameters(fake_request('').GET) == {'a': None}


def test_single_parameter_int():
    get_parameters = ParameterFactory({'a': None}, {'a': Converter(int)}, [])
    assert get_parameters(fake_request('?a=1').GET) == {'a': 1}
    assert get_parameters(fake_request('').GET) == {'a': None}
    with pytest.raises(HTTPBadRequest):
        get_parameters(fake_request('?a=A').GET)


def test_single_parameter_default():
    get_parameters = ParameterFactory({'a': 'default'}, {}, [])
    assert get_parameters(fake_request('?a=A').GET) == {'a': 'A'}
    assert get_parameters(fake_request('').GET) == {'a': 'default'}


def test_single_parameter_int_default():
    get_parameters = ParameterFactory({'a': 0}, {'a': Converter(int)}, [])
    assert get_parameters(fake_request('?a=1').GET) == {'a': 1}
    assert get_parameters(fake_request('').GET) == {'a': 0}
    with pytest.raises(HTTPBadRequest):
        get_parameters(fake_request('?a=A').GET)


def test_parameter_required():
    get_parameters = ParameterFactory({'a': None}, {}, ['a'])
    assert get_parameters(fake_request('?a=foo').GET) == {'a': 'foo'}
    with pytest.raises(HTTPBadRequest):
        get_parameters(fake_request('').GET)


def test_extra_parameters():
    get_parameters = ParameterFactory({'a': None}, {}, [], True)
    assert get_parameters(fake_request('?a=foo').GET) == {
        'a': 'foo',
        'extra_parameters': {}}
    assert get_parameters(fake_request('?b=foo').GET) == {
        'a': None,
        'extra_parameters': {'b': 'foo'}}
    assert get_parameters(fake_request('?a=foo&b=bar').GET) == {
        'a': 'foo',
        'extra_parameters': {'b': 'bar'}}

########NEW FILE########
__FILENAME__ = test_tween
import morepath
from morepath.tween import TweenRegistry
from morepath.error import TopologicalSortError
import pytest
from webtest import TestApp as Client


def setup_module(module):
    morepath.disable_implicit()


def test_tween_sorting_no_tweens():
    reg = TweenRegistry()
    assert reg.sorted_tween_factories() == []


def test_tween_sorting_one_tween():
    reg = TweenRegistry()

    def foo():
        pass

    reg.register_tween_factory(foo, over=None, under=None)
    assert reg.sorted_tween_factories() == [foo]


def test_tween_sorting_two_tweens_under():
    reg = TweenRegistry()

    def top():
        pass

    def bottom():
        pass

    reg.register_tween_factory(top, over=None, under=None)
    reg.register_tween_factory(bottom, over=None, under=top)
    assert reg.sorted_tween_factories() == [top, bottom]


def test_tween_sorting_two_tweens_under_reverse_reg():
    reg = TweenRegistry()

    def top():
        pass

    def bottom():
        pass

    reg.register_tween_factory(bottom, over=None, under=top)
    reg.register_tween_factory(top, over=None, under=None)
    assert reg.sorted_tween_factories() == [top, bottom]


def test_tween_sorting_two_tweens_over():
    reg = TweenRegistry()

    def top():
        pass

    def bottom():
        pass

    reg.register_tween_factory(top, over=bottom, under=None)
    reg.register_tween_factory(bottom, over=None, under=None)
    assert reg.sorted_tween_factories() == [top, bottom]


def test_tween_sorting_two_tweens_over_reverse_reg():
    reg = TweenRegistry()

    def top():
        pass

    def bottom():
        pass

    reg.register_tween_factory(bottom, over=None, under=None)
    reg.register_tween_factory(top, over=bottom, under=None)
    assert reg.sorted_tween_factories() == [top, bottom]


def test_tween_sorting_three():
    reg = TweenRegistry()

    def a():
        pass

    def b():
        pass

    def c():
        pass

    reg.register_tween_factory(a, over=None, under=None)
    reg.register_tween_factory(b, over=None, under=a)
    reg.register_tween_factory(c, over=a, under=None)
    assert reg.sorted_tween_factories() == [c, a, b]


def test_tween_sorting_dag_error():
    reg = TweenRegistry()

    def a():
        pass

    reg.register_tween_factory(a, over=None, under=a)

    with pytest.raises(TopologicalSortError):
        reg.sorted_tween_factories()


def test_tween_sorting_dag_error2():
    reg = TweenRegistry()

    def a():
        pass

    reg.register_tween_factory(a, over=a, under=None)

    with pytest.raises(TopologicalSortError):
        reg.sorted_tween_factories()


def test_tween_sorting_dag_error3():
    reg = TweenRegistry()

    def a():
        pass

    def b():
        pass

    reg.register_tween_factory(a, over=b, under=None)
    reg.register_tween_factory(b, over=a, under=None)

    with pytest.raises(TopologicalSortError):
        reg.sorted_tween_factories()


def test_tween_sorting_dag_error4():
    reg = TweenRegistry()

    def a():
        pass

    def b():
        pass

    def c():
        pass

    reg.register_tween_factory(a, over=b, under=None)
    reg.register_tween_factory(b, over=c, under=None)
    reg.register_tween_factory(c, over=a, under=None)

    with pytest.raises(TopologicalSortError):
        reg.sorted_tween_factories()


def test_tween_directive():
    config = morepath.setup()
    app = morepath.App(testing_config=config)

    @app.path(path='')
    class Root(object):
        pass

    @app.view(model=Root)
    def default(self, request):
        return "View"

    @app.tween_factory()
    def get_modify_response_tween(app, handler):
        def plusplustween(request):
            response = handler(request)
            response.headers['Tween-Header'] = 'FOO'
            return response
        return plusplustween

    config.commit()

    c = Client(app)

    response = c.get('/')
    assert response.body == b'View'
    assert response.headers['Tween-Header'] == 'FOO'

########NEW FILE########
__FILENAME__ = test_view_directive
import morepath
from morepath.error import ConflictError
from webtest import TestApp as Client
import pytest


def setup_module(module):
    morepath.disable_implicit()


def test_view_get_only():
    config = morepath.setup()
    app = morepath.App(testing_config=config)

    @app.path(path='')
    class Model(object):
        def __init__(self):
            pass

    @app.view(model=Model)
    def default(self, request):
        return "View"
    config.commit()

    c = Client(app)

    response = c.get('/')
    assert response.body == b'View'

    response = c.post('/', status=405)


def test_view_any():
    config = morepath.setup()
    app = morepath.App(testing_config=config)

    @app.path(path='')
    class Model(object):
        def __init__(self):
            pass

    @app.view(model=Model, request_method=morepath.ANY)
    def default(self, request):
        return "View"
    config.commit()

    c = Client(app)

    response = c.get('/')
    assert response.body == b'View'

    response = c.post('/')
    assert response.body == b'View'


def test_view_name_conflict_involving_default():
    config = morepath.setup()
    app = morepath.App(testing_config=config)

    @app.path(path='')
    class Model(object):
        def __init__(self):
            pass

    @app.view(model=Model)
    def default(self, request):
        return "View"

    @app.view(model=Model, name='')
    def default2(self, request):
        return "View"

    with pytest.raises(ConflictError):
        config.commit()


def test_view_custom_predicate_conflict_involving_default_extends():
    config = morepath.setup()
    core = morepath.App(testing_config=config)
    app = morepath.App(testing_config=config, extends=core)

    @core.predicate(name='foo', order=100, default='DEFAULT')
    def get_foo(request, model):
        return 'foo'

    @app.path(path='')
    class Model(object):
        def __init__(self):
            pass

    @app.view(model=Model)
    def default(self, request):
        return "View"

    @app.view(model=Model, foo='DEFAULT')
    def default2(self, request):
        return "View"

    with pytest.raises(ConflictError):
        config.commit()

########NEW FILE########
__FILENAME__ = toposort
from .error import TopologicalSortError


def topological_sort(l, get_depends):
    result = []
    marked = set()
    temporary_marked = set()

    def visit(n):
        if n in marked:
            return
        if n in temporary_marked:
            raise TopologicalSortError("Not a DAG")
        temporary_marked.add(n)
        for m in get_depends(n):
            visit(m)
        marked.add(n)
        result.append(n)
    for n in l:
        visit(n)
    return result

########NEW FILE########
__FILENAME__ = traject
import re
from functools import total_ordering
from .converter import IDENTITY_CONVERTER
from .error import TrajectError

IDENTIFIER = re.compile(r'^[^\d\W]\w*$')
PATH_VARIABLE = re.compile(r'\{([^}]*)\}')
VARIABLE = '{}'
PATH_SEPARATOR = re.compile(r'/+')
VIEW_PREFIX = '+'


@total_ordering
class Step(object):
    def __init__(self, s, converters=None):
        self.s = s
        self.converters = converters or {}
        self.generalized = generalize_variables(s)
        self.parts = tuple(self.generalized.split('{}'))
        self._variables_re = create_variables_re(s)
        self.names = parse_variables(s)
        self.cmp_converters = [self.get_converter(name) for name in self.names]
        self.validate()
        self.named_interpolation_str = interpolation_str(s) % tuple(
            [('%(' + name + ')s') for name in self.names])
        if len(set(self.names)) != len(self.names):
            raise TrajectError("Duplicate variable")

    def validate(self):
        self.validate_parts()
        self.validate_variables()

    def validate_parts(self):
        # XXX should also check for valid URL characters
        for part in self.parts:
            if '{' in part or '}' in part:
                raise TrajectError("invalid step: %s" % self.s)

    def validate_variables(self):
        parts = self.parts
        if parts[0] == '':
            parts = parts[1:]
        if parts[-1] == '':
            parts = parts[:-1]
        for part in parts:
            if part == '':
                raise TrajectError(
                    "illegal consecutive variables: %s" % self.s)

    def discriminator_info(self):
        return self.generalized

    def has_variables(self):
        return bool(self.names)

    def match(self, s):
        result = {}
        matched = self._variables_re.match(s)
        if matched is None:
            return False, result
        for name, value in zip(self.names, matched.groups()):
            converter = self.get_converter(name)
            try:
                result[name] = converter.decode([value])
            except ValueError:
                return False, {}
        return True, result

    def get_converter(self, name):
        return self.converters.get(name, IDENTITY_CONVERTER)

    def __eq__(self, other):
        if self.s != other.s:
            return False
        return self.cmp_converters == other.cmp_converters

    def __ne__(self, other):
        if self.s != other.s:
            return True
        return self.cmp_converters != other.cmp_converters

    def __lt__(self, other):
        if self.parts == other.parts:
            return False
        if self._variables_re.match(other.s) is not None:
            return False
        if other._variables_re.match(self.s) is not None:
            return True
        return self.parts > other.parts


class Node(object):
    def __init__(self):
        self._name_nodes = {}
        self._variable_nodes = []
        self.value = None
        self.absorb = False

    def add(self, step):
        if not step.has_variables():
            return self.add_name_node(step)
        return self.add_variable_node(step)

    def add_name_node(self, step):
        node = self._name_nodes.get(step.s)
        if node is not None:
            return node
        node = StepNode(step)
        self._name_nodes[step.s] = node
        return node

    def add_variable_node(self, step):
        for i, node in enumerate(self._variable_nodes):
            if node.step == step:
                return node
            if node.step.generalized == step.generalized:
                raise TrajectError("step %s and %s are in conflict" %
                                   (node.step.s, step.s))
            if step > node.step:
                continue
            result = StepNode(step)
            self._variable_nodes.insert(i, result)
            return result
        result = StepNode(step)
        self._variable_nodes.append(result)
        return result

    def get(self, segment):
        node = self._name_nodes.get(segment)
        if node is not None:
            return node, {}
        for node in self._variable_nodes:
            matched, variables = node.match(segment)
            if matched:
                return node, variables
        return None, {}


class StepNode(Node):
    def __init__(self, step):
        super(StepNode, self).__init__()
        self.step = step

    def match(self, segment):
        return self.step.match(segment)


class Path(object):
    def __init__(self, path):
        self.path = path
        self.stack = parse_path(path)
        self.steps = [Step(segment) for segment in reversed(parse_path(path))]

    def discriminator(self):
        return '/'.join([step.discriminator_info() for step in self.steps])

    def interpolation_str(self):
        return '/'.join([step.named_interpolation_str for step in self.steps])

    def variables(self):
        result = []
        for step in self.steps:
            result.extend(step.names)
        return set(result)


class Inverse(object):
    def __init__(self, path, get_variables, converters,
                 parameter_names, absorb):
        self.path = path
        self.interpolation_path = Path(path).interpolation_str()
        self.get_variables = get_variables
        self.converters = converters
        self.parameter_names = set(parameter_names)
        self.absorb = absorb

    def __call__(self, model):
        converters = self.converters
        parameter_names = self.parameter_names
        all_variables = self.get_variables(model)
        if self.absorb:
            absorbed_path = all_variables.pop('absorb')
        else:
            absorbed_path = None
        extra_parameters = all_variables.pop('extra_parameters', None)
        assert isinstance(all_variables, dict)
        variables = {
            name: converters.get(name, IDENTITY_CONVERTER).encode(value)[0] for
            name, value in all_variables.items()
            if name not in parameter_names}

        # all remaining variables need to show up in the path
        # XXX not sure about value != []
        parameters = {
            name: converters.get(name, IDENTITY_CONVERTER).encode(value) for
            name, value in all_variables.items()
            if (name in parameter_names and
                value is not None and value != [])
            }
        if extra_parameters:
            for name, value in extra_parameters.items():
                parameters[name] = converters.get(
                    name, IDENTITY_CONVERTER).encode(value)
        path = self.interpolation_path % variables
        if absorbed_path is not None:
            path += '/' + absorbed_path
        return path, parameters


class Traject(object):
    def __init__(self):
        super(Traject, self).__init__()
        self._root = Node()

    def add_pattern(self, path, value, converters=None, absorb=False):
        node = self._root
        known_variables = set()
        for segment in reversed(parse_path(path)):
            step = Step(segment, converters)
            node = node.add(step)
            variables = set(step.names)
            if known_variables.intersection(variables):
                raise TrajectError("Duplicate variables")
            known_variables.update(variables)
        node.value = value
        if absorb:
            node.absorb = True

    def consume(self, stack):
        stack = stack[:]
        node = self._root
        variables = {}
        while stack:
            if node.absorb:
                variables['absorb'] = '/'.join(reversed(stack))
                return node.value, [], variables
            segment = stack.pop()
            if segment.startswith(VIEW_PREFIX):
                stack.append(segment)
                return node.value, stack, variables
            new_node, new_variables = node.get(segment)
            if new_node is None:
                stack.append(segment)
                return node.value, stack, variables
            node = new_node
            variables.update(new_variables)
        if node.absorb:
            variables['absorb'] = ''
            return node.value, stack, variables
        return node.value, stack, variables


def parse_path(path):
    """Parse a path /foo/bar/baz to a stack of steps.

    A step is a string, such as 'foo', 'bar' and 'baz'.
    """
    path = path.strip('/')
    if not path:
        return []
    result = PATH_SEPARATOR.split(path)
    result.reverse()
    return result


def create_path(stack):
    """Builds a path from a stack.
    """
    return '/' + u'/'.join(reversed(stack))


def is_identifier(s):
    return IDENTIFIER.match(s) is not None


def parse_variables(s):
    result = PATH_VARIABLE.findall(s)
    for name in result:
        if not is_identifier(name):
            raise TrajectError(
                "illegal variable identifier: %s" % name)
    return result


def create_variables_re(s):
    return re.compile('^' + PATH_VARIABLE.sub(r'(.+)', s) + '$')


def generalize_variables(s):
    return PATH_VARIABLE.sub('{}', s)


def interpolation_str(s):
    return PATH_VARIABLE.sub('%s', s)

########NEW FILE########
__FILENAME__ = tween
from .toposort import topological_sort
from .publish import publish
from .reify import reify


class TweenRegistry(object):
    def __init__(self):
        self._tween_factories = {}

    def register_tween_factory(self, tween_factory, over, under):
        self._tween_factories[tween_factory] = over, under

    def clear(self):
        self._tween_factories = {}

    def sorted_tween_factories(self):
        tween_factory_depends = {}
        for tween_factory, (over, under) in self._tween_factories.items():
            depends = []
            if under is not None:
                depends.append(under)
            tween_factory_depends[tween_factory] = depends
        for tween_factory, (over, under) in self._tween_factories.items():
            if over is not None:
                depends = tween_factory_depends[over]
                depends.append(tween_factory)
        return topological_sort(
            self._tween_factories.keys(),
            lambda tween_factory: tween_factory_depends.get(tween_factory, []))

    @reify
    def publish(self):
        result = publish
        for tween_factory in reversed(self.sorted_tween_factories()):
            result = tween_factory(self, result)
        return result

########NEW FILE########
__FILENAME__ = view
from morepath import generic
from .request import Request, Response
from reg import PredicateMatcher, Predicate, ANY
import json
from webob.exc import HTTPFound


class View(object):
    def __init__(self, func, render, permission):
        self.func = func
        self.render = render
        self.permission = permission

    def __call__(self, request, model):
        # the argument order is reversed here for the actual view function
        # this still makes request weigh stronger in multiple dispatch,
        # but lets view authors write 'self, request'.
        return self.func(model, request)


# XXX what happens if predicates is None for one registration
# but filled for another?
def register_view(registry, model, view, render=None, permission=None,
                  predicates=None):
    if permission is not None:
        # instantiate permission class so it can be looked up using reg
        permission = permission()
    registration = View(view, render, permission)
    if predicates is not None:
        registration = get_predicate_registration(registry, model,
                                                  predicates, registration)
    registry.register(generic.view, (Request, model), registration)


def get_predicate_registration(registry, model, predicates, registration):
    predicate_info = registry.exact('predicate_info', ())
    predicates = get_predicates_with_defaults(predicates, predicate_info)
    matcher = registry.exact(generic.view, (Request, model))
    if matcher is None:
        predicate_infos = list(predicate_info.values())
        predicate_infos.sort()
        matcher = PredicateMatcher(
            [predicate for (order, predicate) in predicate_infos])
    matcher.register(predicates, registration)
    for order, predicate in predicate_info.values():
        fallback = getattr(predicate, 'fallback', None)
        if fallback is None:
            continue
        if predicates[predicate.name] is ANY:
            continue
        p = predicates.copy()
        p[predicate.name] = ANY
        matcher.register(p, View(fallback, None, None))
    return matcher


def get_predicates_with_defaults(predicates, predicate_info):
    result = {}
    for order, predicate in predicate_info.values():
        value = predicates.get(predicate.name)
        if value is None:
            value = predicate.default
        result[predicate.name] = value
    return result


def register_predicate(registry, name, order, default, index, calc):
    # reverse parameters to be consistent with view
    def self_request_calc(self, request):
        return calc(request, self)
    predicate_info = registry.exact('predicate_info', ())
    if predicate_info is None:
        predicate_info = {}
        registry.register('predicate_info', (), predicate_info)
    predicate_info[name] = order, Predicate(name, index,
                                            self_request_calc, default)


def register_predicate_fallback(registry, name, obj):
    predicate_info = registry.exact('predicate_info', ())
    # XXX raise configuration error
    info = predicate_info.get(name)
    assert info is not None
    order, predicate = info
    predicate.fallback = obj


def render_json(content):
    """Take dict/list/string/number content and return json response.
    """
    return Response(json.dumps(content), content_type='application/json')


def render_html(content):
    """Take string and return text/html response.
    """
    return Response(content, content_type='text/html')


def redirect(location):
    return HTTPFound(location=location)

########NEW FILE########
