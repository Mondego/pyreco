__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# Routes documentation build configuration file, created by
# sphinx-quickstart on Sun Apr 20 19:13:41 2008.
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
#sys.path.append(os.path.abspath('.'))

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
project = 'Routes'
copyright = '2010-2012, Ben Bangert, Mike Orr'

# The default replacements for |version| and |release|, also used in various
# other places throughout the built documents.
#
# The short X.Y version.
version = '1.13'
# The full version, including alpha/beta/rc tags.
release = '1.13'

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
today_fmt = '%B %d, %Y'

# List of documents that shouldn't be included in the build.
#unused_docs = []

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
# html_style = 'default.css'

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
#html_static_path = ['_static']

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
#html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
#html_use_smartypants = True


html_theme_options = {
    "bgcolor": "#fff",
    "footertextcolor": "#666",
    "relbarbgcolor": "#fff",
    "relbarlinkcolor": "#590915",
    "relbartextcolor": "#FFAA2D",
    "sidebarlinkcolor": "#590915",
    "sidebarbgcolor": "#fff",
    "sidebartextcolor": "#333",
    "footerbgcolor": "#fff",
    "linkcolor": "#590915",
    "bodyfont": "helvetica, 'bitstream vera sans', sans-serif",
    "headfont": "georgia, 'bitstream vera sans serif', 'lucida grande', helvetica, verdana, sans-serif",
    "headbgcolor": "#fff",
    "headtextcolor": "#12347A",
    "codebgcolor": "#fff",
}

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
# html_use_opensearch = 'http://routes.groovie.org/'

# If nonempty, this is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = ''

# Output file base name for HTML help builder.
htmlhelp_basename = 'Routesdoc'


# Options for LaTeX output
# ------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, document class [howto/manual]).
latex_documents = [
  ('contents', 'Routes.tex', u'Routes Documentation',
   u'Ben Bangert, Mike Orr', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# Additional stuff for the LaTeX preamble.
latex_preamble = '''
\usepackage{palatino}
\definecolor{TitleColor}{rgb}{0.7,0,0}
\definecolor{InnerLinkColor}{rgb}{0.7,0,0}
\definecolor{OuterLinkColor}{rgb}{0.8,0,0}
\definecolor{VerbatimColor}{rgb}{0.985,0.985,0.985}
\definecolor{VerbatimBorderColor}{rgb}{0.8,0.8,0.8}
'''

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
latex_use_modindex = False

# Added to handle docs in middleware.py
autoclass_content = "both"

########NEW FILE########
__FILENAME__ = base
"""Route and Mapper core classes"""
from routes import request_config
from routes.mapper import Mapper
from routes.route import Route

########NEW FILE########
__FILENAME__ = mapper
"""Mapper and Sub-Mapper"""
import re
import sys
import threading

import pkg_resources
from repoze.lru import LRUCache

from routes import request_config
from routes.util import controller_scan, MatchException, RoutesException, as_unicode
from routes.route import Route


COLLECTION_ACTIONS = ['index', 'create', 'new']
MEMBER_ACTIONS = ['show', 'update', 'delete', 'edit']


def strip_slashes(name):
    """Remove slashes from the beginning and end of a part/URL."""
    if name.startswith('/'):
        name = name[1:]
    if name.endswith('/'):
        name = name[:-1]
    return name


class SubMapperParent(object):
    """Base class for Mapper and SubMapper, both of which may be the parent
    of SubMapper objects
    """
    
    def submapper(self, **kargs):
        """Create a partial version of the Mapper with the designated
        options set
        
        This results in a :class:`routes.mapper.SubMapper` object.
        
        If keyword arguments provided to this method also exist in the
        keyword arguments provided to the submapper, their values will
        be merged with the saved options going first.
        
        In addition to :class:`routes.route.Route` arguments, submapper
        can also take a ``path_prefix`` argument which will be
        prepended to the path of all routes that are connected.
        
        Example::
            
            >>> map = Mapper(controller_scan=None)
            >>> map.connect('home', '/', controller='home', action='splash')
            >>> map.matchlist[0].name == 'home'
            True
            >>> m = map.submapper(controller='home')
            >>> m.connect('index', '/index', action='index')
            >>> map.matchlist[1].name == 'index'
            True
            >>> map.matchlist[1].defaults['controller'] == 'home'
            True
        
        Optional ``collection_name`` and ``resource_name`` arguments are
        used in the generation of route names by the ``action`` and
        ``link`` methods.  These in turn are used by the ``index``,
        ``new``, ``create``, ``show``, ``edit``, ``update`` and
        ``delete`` methods which may be invoked indirectly by listing
        them in the ``actions`` argument.  If the ``formatted`` argument
        is set to ``True`` (the default), generated paths are given the
        suffix '{.format}' which matches or generates an optional format
        extension.
        
        Example::
        
            >>> from routes.util import url_for
            >>> map = Mapper(controller_scan=None)
            >>> m = map.submapper(path_prefix='/entries', collection_name='entries', resource_name='entry', actions=['index', 'new'])
            >>> url_for('entries') == '/entries'
            True
            >>> url_for('new_entry', format='xml') == '/entries/new.xml'
            True

        """
        return SubMapper(self, **kargs)

    def collection(self, collection_name, resource_name, path_prefix=None,
                   member_prefix='/{id}', controller=None,
                   collection_actions=COLLECTION_ACTIONS,
                   member_actions = MEMBER_ACTIONS, member_options=None,
                   **kwargs):
        """Create a submapper that represents a collection.

        This results in a :class:`routes.mapper.SubMapper` object, with a
        ``member`` property of the same type that represents the collection's
        member resources.
        
        Its interface is the same as the ``submapper`` together with
        ``member_prefix``, ``member_actions`` and ``member_options``
        which are passed to the ``member`` submapper as ``path_prefix``,
        ``actions`` and keyword arguments respectively.
        
        Example::
        
            >>> from routes.util import url_for
            >>> map = Mapper(controller_scan=None)
            >>> c = map.collection('entries', 'entry')
            >>> c.member.link('ping', method='POST')
            >>> url_for('entries') == '/entries'
            True
            >>> url_for('edit_entry', id=1) == '/entries/1/edit'
            True
            >>> url_for('ping_entry', id=1) == '/entries/1/ping'
            True

        """
        if controller is None:
            controller = resource_name or collection_name
        
        if path_prefix is None:
            path_prefix = '/' + collection_name

        collection = SubMapper(self, collection_name=collection_name,
                               resource_name=resource_name,
                               path_prefix=path_prefix, controller=controller,
                               actions=collection_actions, **kwargs)
        
        collection.member = SubMapper(collection, path_prefix=member_prefix,
                                      actions=member_actions, 
                                      **(member_options or {}))

        return collection


class SubMapper(SubMapperParent):
    """Partial mapper for use with_options"""
    def __init__(self, obj, resource_name=None, collection_name=None,
                 actions=None, formatted=None, **kwargs):
        self.kwargs = kwargs
        self.obj = obj
        self.collection_name = collection_name
        self.member = None
        self.resource_name = resource_name \
                            or getattr(obj, 'resource_name', None) \
                            or kwargs.get('controller', None) \
                            or getattr(obj, 'controller', None)
        if formatted is not None:
            self.formatted = formatted
        else:
            self.formatted = getattr(obj, 'formatted', None)
            if self.formatted is None:
                self.formatted = True

        self.add_actions(actions or [])
        
    def connect(self, *args, **kwargs):
        newkargs = {}
        newargs = args
        for key, value in self.kwargs.items():
            if key == 'path_prefix':
                if len(args) > 1:
                    newargs = (args[0], self.kwargs[key] + args[1])
                else:
                    newargs = (self.kwargs[key] + args[0],)
            elif key in kwargs:
                if isinstance(value, dict):
                    newkargs[key] = dict(value, **kwargs[key]) # merge dicts
                elif key == 'controller':
                    newkargs[key] = kwargs[key]
                else:
                    newkargs[key] = value + kwargs[key]
            else:
                newkargs[key] = self.kwargs[key]
        for key in kwargs:
            if key not in self.kwargs:
                newkargs[key] = kwargs[key]
        return self.obj.connect(*newargs, **newkargs)

    def link(self, rel=None, name=None, action=None, method='GET',
             formatted=None, **kwargs):
        """Generates a named route for a subresource.

        Example::
        
            >>> from routes.util import url_for
            >>> map = Mapper(controller_scan=None)
            >>> c = map.collection('entries', 'entry')
            >>> c.link('recent', name='recent_entries')
            >>> c.member.link('ping', method='POST', formatted=True)
            >>> url_for('entries') == '/entries'
            True
            >>> url_for('recent_entries') == '/entries/recent'
            True
            >>> url_for('ping_entry', id=1) == '/entries/1/ping'
            True
            >>> url_for('ping_entry', id=1, format='xml') == '/entries/1/ping.xml'
            True

        """
        if formatted or (formatted is None and self.formatted):
            suffix = '{.format}'
        else:
            suffix = ''

        return self.connect(name or (rel + '_' + self.resource_name),
                            '/' + (rel or name) + suffix,
                            action=action or rel or name,
                            **_kwargs_with_conditions(kwargs, method))

    def new(self, **kwargs):
        """Generates the "new" link for a collection submapper."""
        return self.link(rel='new', **kwargs)

    def edit(self, **kwargs):
        """Generates the "edit" link for a collection member submapper."""
        return self.link(rel='edit', **kwargs)

    def action(self, name=None, action=None, method='GET', formatted=None,
               **kwargs):
        """Generates a named route at the base path of a submapper.

        Example::
        
            >>> from routes import url_for
            >>> map = Mapper(controller_scan=None)
            >>> c = map.submapper(path_prefix='/entries', controller='entry')
            >>> c.action(action='index', name='entries', formatted=True)
            >>> c.action(action='create', method='POST')
            >>> url_for(controller='entry', action='index', method='GET') == '/entries'
            True
            >>> url_for(controller='entry', action='index', method='GET', format='xml') == '/entries.xml'
            True
            >>> url_for(controller='entry', action='create', method='POST') == '/entries'
            True

        """
        if formatted or (formatted is None and self.formatted):
            suffix = '{.format}'
        else:
            suffix = ''
        return self.connect(name or (action + '_' + self.resource_name),
                            suffix,
                            action=action or name,
                            **_kwargs_with_conditions(kwargs, method))
            
    def index(self, name=None, **kwargs):
        """Generates the "index" action for a collection submapper."""
        return self.action(name=name or self.collection_name,
                           action='index', method='GET', **kwargs)

    def show(self, name = None, **kwargs):
        """Generates the "show" action for a collection member submapper."""
        return self.action(name=name or self.resource_name,
                           action='show', method='GET', **kwargs)

    def create(self, **kwargs):
        """Generates the "create" action for a collection submapper."""
        return self.action(action='create', method='POST', **kwargs)
        
    def update(self, **kwargs):
        """Generates the "update" action for a collection member submapper."""
        return self.action(action='update', method='PUT', **kwargs)

    def delete(self, **kwargs):
        """Generates the "delete" action for a collection member submapper."""
        return self.action(action='delete', method='DELETE', **kwargs)

    def add_actions(self, actions):
        [getattr(self, action)() for action in actions]

    # Provided for those who prefer using the 'with' syntax in Python 2.5+
    def __enter__(self):
        return self
    
    def __exit__(self, type, value, tb):
        pass

# Create kwargs with a 'conditions' member generated for the given method
def _kwargs_with_conditions(kwargs, method):
    if method and 'conditions' not in kwargs:
        newkwargs = kwargs.copy()
        newkwargs['conditions'] = {'method': method}                
        return newkwargs             
    else:
        return kwargs



class Mapper(SubMapperParent):
    """Mapper handles URL generation and URL recognition in a web
    application.
    
    Mapper is built handling dictionary's. It is assumed that the web
    application will handle the dictionary returned by URL recognition
    to dispatch appropriately.
    
    URL generation is done by passing keyword parameters into the
    generate function, a URL is then returned.
    
    """
    def __init__(self, controller_scan=controller_scan, directory=None, 
                 always_scan=False, register=True, explicit=True):
        """Create a new Mapper instance
        
        All keyword arguments are optional.
        
        ``controller_scan``
            Function reference that will be used to return a list of
            valid controllers used during URL matching. If
            ``directory`` keyword arg is present, it will be passed
            into the function during its call. This option defaults to
            a function that will scan a directory for controllers.
            
            Alternatively, a list of controllers or None can be passed
            in which are assumed to be the definitive list of
            controller names valid when matching 'controller'.
        
        ``directory``
            Passed into controller_scan for the directory to scan. It
            should be an absolute path if using the default 
            ``controller_scan`` function.
        
        ``always_scan``
            Whether or not the ``controller_scan`` function should be
            run during every URL match. This is typically a good idea
            during development so the server won't need to be restarted
            anytime a controller is added.
        
        ``register``
            Boolean used to determine if the Mapper should use 
            ``request_config`` to register itself as the mapper. Since
            it's done on a thread-local basis, this is typically best
            used during testing though it won't hurt in other cases.
        
        ``explicit``
            Boolean used to determine if routes should be connected
            with implicit defaults of::
                
                {'controller':'content','action':'index','id':None}
            
            When set to True, these defaults will not be added to route
            connections and ``url_for`` will not use Route memory.
                
        Additional attributes that may be set after mapper
        initialization (ie, map.ATTRIBUTE = 'something'):
        
        ``encoding``
            Used to indicate alternative encoding/decoding systems to
            use with both incoming URL's, and during Route generation
            when passed a Unicode string. Defaults to 'utf-8'.
        
        ``decode_errors``
            How to handle errors in the encoding, generally ignoring
            any chars that don't convert should be sufficient. Defaults
            to 'ignore'.
        
        ``minimization``
            Boolean used to indicate whether or not Routes should
            minimize URL's and the generated URL's, or require every
            part where it appears in the path. Defaults to True.
        
        ``hardcode_names``
            Whether or not Named Routes result in the default options
            for the route being used *or* if they actually force url
            generation to use the route. Defaults to False.
        
        """
        self.matchlist = []
        self.maxkeys = {}
        self.minkeys = {}
        self.urlcache = LRUCache(1600)
        self._created_regs = False
        self._created_gens = False
        self._master_regexp = None
        self.prefix = None
        self.req_data = threading.local()
        self.directory = directory
        self.always_scan = always_scan
        self.controller_scan = controller_scan
        self._regprefix = None
        self._routenames = {}
        self.debug = False
        self.append_slash = False
        self.sub_domains = False
        self.sub_domains_ignore = []
        self.domain_match = '[^\.\/]+?\.[^\.\/]+'
        self.explicit = explicit
        self.encoding = 'utf-8'
        self.decode_errors = 'ignore'
        self.hardcode_names = True
        self.minimization = False
        self.create_regs_lock = threading.Lock()
        if register:
            config = request_config()
            config.mapper = self
    
    def __str__(self):
        """Generates a tabular string representation."""
        def format_methods(r):
            if r.conditions:
                method = r.conditions.get('method', '')
                return type(method) is str and method or ', '.join(method)
            else:
                return ''

        table = [('Route name', 'Methods', 'Path')] + \
                [(r.name or '', format_methods(r), r.routepath or '')
                 for r in self.matchlist]
            
        widths = [max(len(row[col]) for row in table)
                  for col in range(len(table[0]))]
        
        return '\n'.join(
            ' '.join(row[col].ljust(widths[col])
                     for col in range(len(widths)))
            for row in table)

    def _envget(self):
        try:
            return self.req_data.environ
        except AttributeError:
            return None
    def _envset(self, env):
        self.req_data.environ = env
    def _envdel(self):
        del self.req_data.environ
    environ = property(_envget, _envset, _envdel)
    
    def extend(self, routes, path_prefix=''):
        """Extends the mapper routes with a list of Route objects
        
        If a path_prefix is provided, all the routes will have their
        path prepended with the path_prefix.
        
        Example::
            
            >>> map = Mapper(controller_scan=None)
            >>> map.connect('home', '/', controller='home', action='splash')
            >>> map.matchlist[0].name == 'home'
            True
            >>> routes = [Route('index', '/index.htm', controller='home',
            ...                 action='index')]
            >>> map.extend(routes)
            >>> len(map.matchlist) == 2
            True
            >>> map.extend(routes, path_prefix='/subapp')
            >>> len(map.matchlist) == 3
            True
            >>> map.matchlist[2].routepath == '/subapp/index.htm'
            True
        
        .. note::
            
            This function does not merely extend the mapper with the
            given list of routes, it actually creates new routes with
            identical calling arguments.
        
        """
        for route in routes:
            if path_prefix and route.minimization:
                routepath = '/'.join([path_prefix, route.routepath])
            elif path_prefix:
                routepath = path_prefix + route.routepath
            else:
                routepath = route.routepath
            self.connect(route.name, routepath, **route._kargs)
                
    def connect(self, *args, **kargs):
        """Create and connect a new Route to the Mapper.
        
        Usage:
        
        .. code-block:: python
        
            m = Mapper()
            m.connect(':controller/:action/:id')
            m.connect('date/:year/:month/:day', controller="blog", action="view")
            m.connect('archives/:page', controller="blog", action="by_page",
            requirements = { 'page':'\d{1,2}' })
            m.connect('category_list', 'archives/category/:section', controller='blog', action='category',
            section='home', type='list')
            m.connect('home', '', controller='blog', action='view', section='home')
        
        """
        routename = None
        if len(args) > 1:
            routename = args[0]
        else:
            args = (None,) + args
        if '_explicit' not in kargs:
            kargs['_explicit'] = self.explicit
        if '_minimize' not in kargs:
            kargs['_minimize'] = self.minimization
        route = Route(*args, **kargs)
                
        # Apply encoding and errors if its not the defaults and the route 
        # didn't have one passed in.
        if (self.encoding != 'utf-8' or self.decode_errors != 'ignore') and \
           '_encoding' not in kargs:
            route.encoding = self.encoding
            route.decode_errors = self.decode_errors
        
        if not route.static:
            self.matchlist.append(route)
        
        if routename:
            self._routenames[routename] = route
            route.name = routename
        if route.static:
            return
        exists = False
        for key in self.maxkeys:
            if key == route.maxkeys:
                self.maxkeys[key].append(route)
                exists = True
                break
        if not exists:
            self.maxkeys[route.maxkeys] = [route]
        self._created_gens = False
    
    def _create_gens(self):
        """Create the generation hashes for route lookups"""
        # Use keys temporailly to assemble the list to avoid excessive
        # list iteration testing with "in"
        controllerlist = {}
        actionlist = {}
        
        # Assemble all the hardcoded/defaulted actions/controllers used
        for route in self.matchlist:
            if route.static:
                continue
            if route.defaults.has_key('controller'):
                controllerlist[route.defaults['controller']] = True
            if route.defaults.has_key('action'):
                actionlist[route.defaults['action']] = True
        
        # Setup the lists of all controllers/actions we'll add each route
        # to. We include the '*' in the case that a generate contains a
        # controller/action that has no hardcodes
        controllerlist = controllerlist.keys() + ['*']
        actionlist = actionlist.keys() + ['*']
        
        # Go through our list again, assemble the controllers/actions we'll
        # add each route to. If its hardcoded, we only add it to that dict key.
        # Otherwise we add it to every hardcode since it can be changed.
        gendict = {} # Our generated two-deep hash
        for route in self.matchlist:
            if route.static:
                continue
            clist = controllerlist
            alist = actionlist
            if 'controller' in route.hardcoded:
                clist = [route.defaults['controller']]
            if 'action' in route.hardcoded:
                alist = [unicode(route.defaults['action'])]
            for controller in clist:
                for action in alist:
                    actiondict = gendict.setdefault(controller, {})
                    actiondict.setdefault(action, ([], {}))[0].append(route)
        self._gendict = gendict
        self._created_gens = True

    def create_regs(self, *args, **kwargs):
        """Atomically creates regular expressions for all connected
        routes
        """
        self.create_regs_lock.acquire()
        try:
            self._create_regs(*args, **kwargs)
        finally:
            self.create_regs_lock.release()
    
    def _create_regs(self, clist=None):
        """Creates regular expressions for all connected routes"""
        if clist is None:
            if self.directory:
                clist = self.controller_scan(self.directory)
            elif callable(self.controller_scan):
                clist = self.controller_scan()
            elif not self.controller_scan:
                clist = []
            else:
                clist = self.controller_scan
        
        for key, val in self.maxkeys.iteritems():
            for route in val:
                route.makeregexp(clist)
        
        regexps = []
        routematches = []
        for route in self.matchlist:
            if not route.static:
                routematches.append(route)
                regexps.append(route.makeregexp(clist, include_names=False))
        self._routematches = routematches
        
        # Create our regexp to strip the prefix
        if self.prefix:
            self._regprefix = re.compile(self.prefix + '(.*)')
        
        # Save the master regexp
        regexp = '|'.join(['(?:%s)' % x for x in regexps])
        self._master_reg = regexp
        try:
            self._master_regexp = re.compile(regexp)
        except OverflowError:
            self._master_regexp = None
        self._created_regs = True
    
    def _match(self, url, environ):
        """Internal Route matcher
        
        Matches a URL against a route, and returns a tuple of the match
        dict and the route object if a match is successfull, otherwise
        it returns empty.
        
        For internal use only.
        
        """
        if not self._created_regs and self.controller_scan:
            self.create_regs()
        elif not self._created_regs:
            raise RoutesException("You must generate the regular expressions"
                                 " before matching.")
        
        if self.always_scan:
            self.create_regs()
        
        matchlog = []
        if self.prefix:
            if re.match(self._regprefix, url):
                url = re.sub(self._regprefix, r'\1', url)
                if not url:
                    url = '/'
            else:
                return (None, None, matchlog)
                
        environ = environ or self.environ
        sub_domains = self.sub_domains
        sub_domains_ignore = self.sub_domains_ignore
        domain_match = self.domain_match
        debug = self.debug
        
        if self._master_regexp is not None:
            # Check to see if its a valid url against the main regexp
            # Done for faster invalid URL elimination
            valid_url = re.match(self._master_regexp, url)
        else:
            # Regex is None due to OverflowError caused by too many routes.
            # This will allow larger projects to work but might increase time
            # spent invalidating URLs in the loop below.
            valid_url = True
        if not valid_url:
            return (None, None, matchlog)
        
        for route in self.matchlist:
            if route.static:
                if debug:
                    matchlog.append(dict(route=route, static=True))
                continue
            match = route.match(url, environ, sub_domains, sub_domains_ignore,
                                domain_match)
            if debug:
                matchlog.append(dict(route=route, regexp=bool(match)))
            if isinstance(match, dict) or match:
                return (match, route, matchlog)
        return (None, None, matchlog)
    
    def match(self, url=None, environ=None):
        """Match a URL against against one of the routes contained.
        
        Will return None if no valid match is found.
        
        .. code-block:: python
            
            resultdict = m.match('/joe/sixpack')
        
        """
        if not url and not environ:
            raise RoutesException('URL or environ must be provided')
        
        if not url:
            url = environ['PATH_INFO']
                
        result = self._match(url, environ)
        if self.debug:
            return result[0], result[1], result[2]
        if isinstance(result[0], dict) or result[0]:
            return result[0]
        return None
    
    def routematch(self, url=None, environ=None):
        """Match a URL against against one of the routes contained.
        
        Will return None if no valid match is found, otherwise a
        result dict and a route object is returned.
        
        .. code-block:: python
        
            resultdict, route_obj = m.match('/joe/sixpack')
        
        """
        if not url and not environ:
            raise RoutesException('URL or environ must be provided')
        
        if not url:
            url = environ['PATH_INFO']
        result = self._match(url, environ)
        if self.debug:
            return result[0], result[1], result[2]
        if isinstance(result[0], dict) or result[0]:
            return result[0], result[1]
        return None
    
    def generate(self, *args, **kargs):
        """Generate a route from a set of keywords
        
        Returns the url text, or None if no URL could be generated.
        
        .. code-block:: python
            
            m.generate(controller='content',action='view',id=10)
        
        """
        # Generate ourself if we haven't already
        if not self._created_gens:
            self._create_gens()
        
        if self.append_slash:
            kargs['_append_slash'] = True
        
        if not self.explicit:
            if 'controller' not in kargs:
                kargs['controller'] = 'content'
            if 'action' not in kargs:
                kargs['action'] = 'index'
        
        environ = kargs.pop('_environ', self.environ)
        controller = kargs.get('controller', None)
        action = kargs.get('action', None)

        # If the URL didn't depend on the SCRIPT_NAME, we'll cache it
        # keyed by just by kargs; otherwise we need to cache it with
        # both SCRIPT_NAME and kargs:
        cache_key = unicode(args).encode('utf8') + \
            unicode(kargs).encode('utf8')
        
        if self.urlcache is not None:
            if self.environ:
                cache_key_script_name = '%s:%s' % (
                    environ.get('SCRIPT_NAME', ''), cache_key)
            else:
                cache_key_script_name = cache_key
        
            # Check the url cache to see if it exists, use it if it does
            for key in [cache_key, cache_key_script_name]:
                val = self.urlcache.get(key, self)
                if val != self:
                    return val
        
        controller = as_unicode(controller, self.encoding)
        action = as_unicode(action, self.encoding)

        actionlist = self._gendict.get(controller) or self._gendict.get('*', {})
        if not actionlist and not args:
            return None
        (keylist, sortcache) = actionlist.get(action) or \
                               actionlist.get('*', (None, {}))
        if not keylist and not args:
            return None

        keys = frozenset(kargs.keys())
        cacheset = False
        cachekey = unicode(keys)
        cachelist = sortcache.get(cachekey)
        if args:
            keylist = args
        elif cachelist:
            keylist = cachelist
        else:
            cacheset = True
            newlist = []
            for route in keylist:
                if len(route.minkeys - route.dotkeys - keys) == 0:
                    newlist.append(route)
            keylist = newlist

            class KeySorter:

                def __init__(self, obj, *args):
                    self.obj = obj

                def __lt__(self, other):
                    return self._keysort(self.obj, other.obj) < 0
            
                def _keysort(self, a, b):
                    """Sorts two sets of sets, to order them ideally for
                    matching."""
                    am = a.minkeys
                    a = a.maxkeys
                    b = b.maxkeys

                    lendiffa = len(keys^a)
                    lendiffb = len(keys^b)
                    # If they both match, don't switch them
                    if lendiffa == 0 and lendiffb == 0:
                        return 0

                    # First, if a matches exactly, use it
                    if lendiffa == 0:
                        return -1

                    # Or b matches exactly, use it
                    if lendiffb == 0:
                        return 1

                    # Neither matches exactly, return the one with the most in
                    # common
                    if self._compare(lendiffa, lendiffb) != 0:
                        return self._compare(lendiffa, lendiffb)

                    # Neither matches exactly, but if they both have just as much
                    # in common
                    if len(keys&b) == len(keys&a):
                        # Then we return the shortest of the two
                        return self._compare(len(a), len(b))

                    # Otherwise, we return the one that has the most in common
                    else:
                        return self._compare(len(keys&b), len(keys&a))

                def _compare(self, obj1, obj2):
                    if obj1 < obj2:
                        return -1
                    elif obj1 < obj2:
                        return 1
                    else:
                        return 0
            
            keylist.sort(key=KeySorter)
            if cacheset:
                sortcache[cachekey] = keylist
                
        # Iterate through the keylist of sorted routes (or a single route if
        # it was passed in explicitly for hardcoded named routes)
        for route in keylist:
            fail = False
            for key in route.hardcoded:
                kval = kargs.get(key)
                if not kval:
                    continue
                kval = as_unicode(kval, self.encoding)
                if kval != route.defaults[key] and not callable(route.defaults[key]):
                    fail = True
                    break
            if fail:
                continue
            path = route.generate(**kargs)
            if path:
                if self.prefix:
                    path = self.prefix + path
                external_static = route.static and route.external
                if environ and environ.get('SCRIPT_NAME', '') != ''\
                    and not route.absolute and not external_static:
                    path = environ['SCRIPT_NAME'] + path
                    key = cache_key_script_name
                else:
                    key = cache_key
                if self.urlcache is not None:
                    self.urlcache.put(key, str(path))
                return str(path)
            else:
                continue
        return None
    
    def resource(self, member_name, collection_name, **kwargs):
        """Generate routes for a controller resource
        
        The member_name name should be the appropriate singular version
        of the resource given your locale and used with members of the
        collection. The collection_name name will be used to refer to
        the resource collection methods and should be a plural version
        of the member_name argument. By default, the member_name name
        will also be assumed to map to a controller you create.
        
        The concept of a web resource maps somewhat directly to 'CRUD' 
        operations. The overlying things to keep in mind is that
        mapping a resource is about handling creating, viewing, and
        editing that resource.
        
        All keyword arguments are optional.
        
        ``controller``
            If specified in the keyword args, the controller will be
            the actual controller used, but the rest of the naming
            conventions used for the route names and URL paths are
            unchanged.
        
        ``collection``
            Additional action mappings used to manipulate/view the
            entire set of resources provided by the controller.
            
            Example::
                
                map.resource('message', 'messages', collection={'rss':'GET'})
                # GET /message/rss (maps to the rss action)
                # also adds named route "rss_message"
        
        ``member``
            Additional action mappings used to access an individual
            'member' of this controllers resources.
            
            Example::
                
                map.resource('message', 'messages', member={'mark':'POST'})
                # POST /message/1/mark (maps to the mark action)
                # also adds named route "mark_message"
        
        ``new``
            Action mappings that involve dealing with a new member in
            the controller resources.
            
            Example::
                
                map.resource('message', 'messages', new={'preview':'POST'})
                # POST /message/new/preview (maps to the preview action)
                # also adds a url named "preview_new_message"
        
        ``path_prefix``
            Prepends the URL path for the Route with the path_prefix
            given. This is most useful for cases where you want to mix
            resources or relations between resources.
        
        ``name_prefix``
            Perpends the route names that are generated with the
            name_prefix given. Combined with the path_prefix option,
            it's easy to generate route names and paths that represent
            resources that are in relations.
            
            Example::
                
                map.resource('message', 'messages', controller='categories', 
                    path_prefix='/category/:category_id', 
                    name_prefix="category_")
                # GET /category/7/message/1
                # has named route "category_message"
                
        ``parent_resource`` 
            A ``dict`` containing information about the parent
            resource, for creating a nested resource. It should contain
            the ``member_name`` and ``collection_name`` of the parent
            resource. This ``dict`` will 
            be available via the associated ``Route`` object which can
            be accessed during a request via
            ``request.environ['routes.route']``
 
            If ``parent_resource`` is supplied and ``path_prefix``
            isn't, ``path_prefix`` will be generated from
            ``parent_resource`` as
            "<parent collection name>/:<parent member name>_id". 

            If ``parent_resource`` is supplied and ``name_prefix``
            isn't, ``name_prefix`` will be generated from
            ``parent_resource`` as  "<parent member name>_". 
 
            Example:: 
 
                >>> from routes.util import url_for 
                >>> m = Mapper() 
                >>> m.resource('location', 'locations', 
                ...            parent_resource=dict(member_name='region', 
                ...                                 collection_name='regions'))
                >>> # path_prefix is "regions/:region_id" 
                >>> # name prefix is "region_"  
                >>> url_for('region_locations', region_id=13) 
                '/regions/13/locations'
                >>> url_for('region_new_location', region_id=13) 
                '/regions/13/locations/new'
                >>> url_for('region_location', region_id=13, id=60) 
                '/regions/13/locations/60'
                >>> url_for('region_edit_location', region_id=13, id=60) 
                '/regions/13/locations/60/edit'

            Overriding generated ``path_prefix``::

                >>> m = Mapper()
                >>> m.resource('location', 'locations',
                ...            parent_resource=dict(member_name='region',
                ...                                 collection_name='regions'),
                ...            path_prefix='areas/:area_id')
                >>> # name prefix is "region_"
                >>> url_for('region_locations', area_id=51)
                '/areas/51/locations'

            Overriding generated ``name_prefix``::

                >>> m = Mapper()
                >>> m.resource('location', 'locations',
                ...            parent_resource=dict(member_name='region',
                ...                                 collection_name='regions'),
                ...            name_prefix='')
                >>> # path_prefix is "regions/:region_id" 
                >>> url_for('locations', region_id=51)
                '/regions/51/locations'

        """
        collection = kwargs.pop('collection', {})
        member = kwargs.pop('member', {})
        new = kwargs.pop('new', {})
        path_prefix = kwargs.pop('path_prefix', None)
        name_prefix = kwargs.pop('name_prefix', None)
        parent_resource = kwargs.pop('parent_resource', None)
        
        # Generate ``path_prefix`` if ``path_prefix`` wasn't specified and 
        # ``parent_resource`` was. Likewise for ``name_prefix``. Make sure
        # that ``path_prefix`` and ``name_prefix`` *always* take precedence if
        # they are specified--in particular, we need to be careful when they
        # are explicitly set to "".
        if parent_resource is not None: 
            if path_prefix is None: 
                path_prefix = '%s/:%s_id' % (parent_resource['collection_name'], 
                                             parent_resource['member_name']) 
            if name_prefix is None:
                name_prefix = '%s_' % parent_resource['member_name']
        else:
            if path_prefix is None: path_prefix = ''
            if name_prefix is None: name_prefix = ''
        
        # Ensure the edit and new actions are in and GET
        member['edit'] = 'GET'
        new.update({'new': 'GET'})
        
        # Make new dict's based off the old, except the old values become keys,
        # and the old keys become items in a list as the value
        def swap(dct, newdct):
            """Swap the keys and values in the dict, and uppercase the values
            from the dict during the swap."""
            for key, val in dct.iteritems():
                newdct.setdefault(val.upper(), []).append(key)
            return newdct
        collection_methods = swap(collection, {})
        member_methods = swap(member, {})
        new_methods = swap(new, {})
        
        # Insert create, update, and destroy methods
        collection_methods.setdefault('POST', []).insert(0, 'create')
        member_methods.setdefault('PUT', []).insert(0, 'update')
        member_methods.setdefault('DELETE', []).insert(0, 'delete')
        
        # If there's a path prefix option, use it with the controller
        controller = strip_slashes(collection_name)
        path_prefix = strip_slashes(path_prefix)
        path_prefix = '/' + path_prefix
        if path_prefix and path_prefix != '/':
            path = path_prefix + '/' + controller
        else:
            path = '/' + controller
        collection_path = path
        new_path = path + "/new"
        member_path = path + "/:(id)"
        
        options = { 
            'controller': kwargs.get('controller', controller),
            '_member_name': member_name,
            '_collection_name': collection_name,
            '_parent_resource': parent_resource,
            '_filter': kwargs.get('_filter')
        }
        
        def requirements_for(meth):
            """Returns a new dict to be used for all route creation as the
            route options"""
            opts = options.copy()
            if method != 'any': 
                opts['conditions'] = {'method':[meth.upper()]}
            return opts
        
        # Add the routes for handling collection methods
        for method, lst in collection_methods.iteritems():
            primary = (method != 'GET' and lst.pop(0)) or None
            route_options = requirements_for(method)
            for action in lst:
                route_options['action'] = action
                route_name = "%s%s_%s" % (name_prefix, action, collection_name)
                self.connect("formatted_" + route_name, "%s/%s.:(format)" % \
                             (collection_path, action), **route_options)
                self.connect(route_name, "%s/%s" % (collection_path, action),
                                                    **route_options)
            if primary:
                route_options['action'] = primary
                self.connect("%s.:(format)" % collection_path, **route_options)
                self.connect(collection_path, **route_options)
        
        # Specifically add in the built-in 'index' collection method and its 
        # formatted version
        self.connect("formatted_" + name_prefix + collection_name, 
            collection_path + ".:(format)", action='index', 
            conditions={'method':['GET']}, **options)
        self.connect(name_prefix + collection_name, collection_path, 
                     action='index', conditions={'method':['GET']}, **options)
        
        # Add the routes that deal with new resource methods
        for method, lst in new_methods.iteritems():
            route_options = requirements_for(method)
            for action in lst:
                path = (action == 'new' and new_path) or "%s/%s" % (new_path, 
                                                                    action)
                name = "new_" + member_name
                if action != 'new':
                    name = action + "_" + name
                route_options['action'] = action
                formatted_path = (action == 'new' and new_path + '.:(format)') or \
                    "%s/%s.:(format)" % (new_path, action)
                self.connect("formatted_" + name_prefix + name, formatted_path, 
                             **route_options)
                self.connect(name_prefix + name, path, **route_options)

        requirements_regexp = '[^\/]+(?<!\\\)'

        # Add the routes that deal with member methods of a resource
        for method, lst in member_methods.iteritems():
            route_options = requirements_for(method)
            route_options['requirements'] = {'id':requirements_regexp}
            if method not in ['POST', 'GET', 'any']:
                primary = lst.pop(0)
            else:
                primary = None
            for action in lst:
                route_options['action'] = action
                self.connect("formatted_%s%s_%s" % (name_prefix, action, 
                                                    member_name),
                    "%s/%s.:(format)" % (member_path, action), **route_options)
                self.connect("%s%s_%s" % (name_prefix, action, member_name),
                    "%s/%s" % (member_path, action), **route_options)
            if primary:
                route_options['action'] = primary
                self.connect("%s.:(format)" % member_path, **route_options)
                self.connect(member_path, **route_options)
        
        # Specifically add the member 'show' method
        route_options = requirements_for('GET')
        route_options['action'] = 'show'
        route_options['requirements'] = {'id':requirements_regexp}
        self.connect("formatted_" + name_prefix + member_name, 
                     member_path + ".:(format)", **route_options)
        self.connect(name_prefix + member_name, member_path, **route_options)
    
    def redirect(self, match_path, destination_path, *args, **kwargs):
        """Add a redirect route to the mapper
        
        Redirect routes bypass the wrapped WSGI application and instead
        result in a redirect being issued by the RoutesMiddleware. As
        such, this method is only meaningful when using
        RoutesMiddleware.
        
        By default, a 302 Found status code is used, this can be
        changed by providing a ``_redirect_code`` keyword argument
        which will then be used instead. Note that the entire status
        code string needs to be present.
        
        When using keyword arguments, all arguments that apply to
        matching will be used for the match, while generation specific
        options will be used during generation. Thus all options
        normally available to connected Routes may be used with
        redirect routes as well.
        
        Example::
            
            map = Mapper()
            map.redirect('/legacyapp/archives/{url:.*}, '/archives/{url})
            map.redirect('/home/index', '/', _redirect_code='301 Moved Permanently')
        
        """
        both_args = ['_encoding', '_explicit', '_minimize']
        gen_args = ['_filter']
        
        status_code = kwargs.pop('_redirect_code', '302 Found')
        gen_dict, match_dict = {}, {}
        
        # Create the dict of args for the generation route
        for key in both_args + gen_args:
            if key in kwargs:
                gen_dict[key] = kwargs[key]
        gen_dict['_static'] = True
        
        # Create the dict of args for the matching route
        for key in kwargs:
            if key not in gen_args:
                match_dict[key] = kwargs[key]
        
        self.connect(match_path, **match_dict)
        match_route = self.matchlist[-1]
        
        self.connect('_redirect_%s' % id(match_route), destination_path,
                     **gen_dict)
        match_route.redirect = True
        match_route.redirect_status = status_code

########NEW FILE########
__FILENAME__ = middleware
"""Routes WSGI Middleware"""
import re
import logging

from webob import Request

from routes.base import request_config
from routes.util import URLGenerator, url_for

log = logging.getLogger('routes.middleware')

class RoutesMiddleware(object):
    """Routing middleware that handles resolving the PATH_INFO in
    addition to optionally recognizing method overriding."""
    def __init__(self, wsgi_app, mapper, use_method_override=True, 
                 path_info=True, singleton=True):
        """Create a Route middleware object
        
        Using the use_method_override keyword will require Paste to be
        installed, and your application should use Paste's WSGIRequest
        object as it will properly handle POST issues with wsgi.input
        should Routes check it.
        
        If path_info is True, then should a route var contain
        path_info, the SCRIPT_NAME and PATH_INFO will be altered
        accordingly. This should be used with routes like:
        
        .. code-block:: python
        
            map.connect('blog/*path_info', controller='blog', path_info='')
        
        """
        self.app = wsgi_app
        self.mapper = mapper
        self.singleton = singleton
        self.use_method_override = use_method_override
        self.path_info = path_info
        log_debug = self.log_debug = logging.DEBUG >= log.getEffectiveLevel()
        if self.log_debug:
            log.debug("Initialized with method overriding = %s, and path "
                  "info altering = %s", use_method_override, path_info)
    
    def __call__(self, environ, start_response):
        """Resolves the URL in PATH_INFO, and uses wsgi.routing_args
        to pass on URL resolver results."""
        old_method = None
        if self.use_method_override:
            req = None
            
            # In some odd cases, there's no query string
            try:
                qs = environ['QUERY_STRING']
            except KeyError:
                qs = ''
            if '_method' in qs:
                req = Request(environ)
                req.errors = 'ignore'
                if '_method' in req.GET:
                    old_method = environ['REQUEST_METHOD']
                    environ['REQUEST_METHOD'] = req.GET['_method'].upper()
                    if self.log_debug:
                        log.debug("_method found in QUERY_STRING, altering request"
                                " method to %s", environ['REQUEST_METHOD'])
            elif environ['REQUEST_METHOD'] == 'POST' and is_form_post(environ):
                if req is None:
                    req = Request(environ)
                    req.errors = 'ignore'
                if '_method' in req.POST:
                    old_method = environ['REQUEST_METHOD']
                    environ['REQUEST_METHOD'] = req.POST['_method'].upper()
                    if self.log_debug:
                        log.debug("_method found in POST data, altering request "
                                  "method to %s", environ['REQUEST_METHOD'])
        
        # Run the actual route matching
        # -- Assignment of environ to config triggers route matching
        if self.singleton:
            config = request_config()
            config.mapper = self.mapper
            config.environ = environ
            match = config.mapper_dict
            route = config.route
        else:
            results = self.mapper.routematch(environ=environ)
            if results:
                match, route = results[0], results[1]
            else:
                match = route = None
                
        if old_method:
            environ['REQUEST_METHOD'] = old_method
        
        if not match:
            match = {}
            if self.log_debug:
                urlinfo = "%s %s" % (environ['REQUEST_METHOD'], environ['PATH_INFO'])
                log.debug("No route matched for %s", urlinfo)
        elif self.log_debug:
            urlinfo = "%s %s" % (environ['REQUEST_METHOD'], environ['PATH_INFO'])
            log.debug("Matched %s", urlinfo)
            log.debug("Route path: '%s', defaults: %s", route.routepath, 
                      route.defaults)
            log.debug("Match dict: %s", match)
                
        url = URLGenerator(self.mapper, environ)
        environ['wsgiorg.routing_args'] = ((url), match)
        environ['routes.route'] = route
        environ['routes.url'] = url

        if route and route.redirect:
            route_name = '_redirect_%s' % id(route)
            location = url(route_name, **match)
            log.debug("Using redirect route, redirect to '%s' with status"
                      "code: %s", location, route.redirect_status)
            start_response(route.redirect_status, 
                           [('Content-Type', 'text/plain; charset=utf8'), 
                            ('Location', location)])
            return []

        # If the route included a path_info attribute and it should be used to
        # alter the environ, we'll pull it out
        if self.path_info and 'path_info' in match:
            oldpath = environ['PATH_INFO']
            newpath = match.get('path_info') or ''
            environ['PATH_INFO'] = newpath
            if not environ['PATH_INFO'].startswith('/'):
                environ['PATH_INFO'] = '/' + environ['PATH_INFO']
            environ['SCRIPT_NAME'] += re.sub(r'^(.*?)/' + re.escape(newpath) + '$', 
                                             r'\1', oldpath)
        
        response = self.app(environ, start_response)
        
        # Wrapped in try as in rare cases the attribute will be gone already
        try:
            del self.mapper.environ
        except AttributeError:
            pass
        return response

def is_form_post(environ):
    """Determine whether the request is a POSTed html form"""
    content_type = environ.get('CONTENT_TYPE', '').lower()
    if ';' in content_type:
        content_type = content_type.split(';', 1)[0]
    return content_type in ('application/x-www-form-urlencoded',
                            'multipart/form-data')

########NEW FILE########
__FILENAME__ = route
import re
import sys
import urllib

if sys.version < '2.4':
    from sets import ImmutableSet as frozenset

from routes.util import _url_quote as url_quote, _str_encode, as_unicode


class Route(object):
    """The Route object holds a route recognition and generation
    routine.
    
    See Route.__init__ docs for usage.
    
    """
    # reserved keys that don't count
    reserved_keys = ['requirements']
    
    # special chars to indicate a natural split in the URL
    done_chars = ('/', ',', ';', '.', '#')
    
    def __init__(self, name, routepath, **kargs):
        """Initialize a route, with a given routepath for
        matching/generation
        
        The set of keyword args will be used as defaults.
        
        Usage::
        
            >>> from routes.base import Route
            >>> newroute = Route(None, ':controller/:action/:id')
            >>> sorted(newroute.defaults.items())
            [('action', 'index'), ('id', None)]
            >>> newroute = Route(None, 'date/:year/:month/:day',  
            ...     controller="blog", action="view")
            >>> newroute = Route(None, 'archives/:page', controller="blog", 
            ...     action="by_page", requirements = { 'page':'\d{1,2}' })
            >>> newroute.reqs
            {'page': '\\\d{1,2}'}
        
        .. Note:: 
            Route is generally not called directly, a Mapper instance
            connect method should be used to add routes.
        
        """
        self.routepath = routepath
        self.sub_domains = False
        self.prior = None
        self.redirect = False
        self.name = name
        self._kargs = kargs
        self.minimization = kargs.pop('_minimize', False)
        self.encoding = kargs.pop('_encoding', 'utf-8')
        self.reqs = kargs.get('requirements', {})
        self.decode_errors = 'replace'
        
        # Don't bother forming stuff we don't need if its a static route
        self.static = kargs.pop('_static', False)
        self.filter = kargs.pop('_filter', None)
        self.absolute = kargs.pop('_absolute', False)
        
        # Pull out the member/collection name if present, this applies only to
        # map.resource
        self.member_name = kargs.pop('_member_name', None)
        self.collection_name = kargs.pop('_collection_name', None)
        self.parent_resource = kargs.pop('_parent_resource', None)
        
        # Pull out route conditions
        self.conditions = kargs.pop('conditions', None)
        
        # Determine if explicit behavior should be used
        self.explicit = kargs.pop('_explicit', False)
                
        # Since static need to be generated exactly, treat them as
        # non-minimized
        if self.static:
            self.external = '://' in self.routepath
            self.minimization = False
        
        # Strip preceding '/' if present, and not minimizing
        if routepath.startswith('/') and self.minimization:
            self.routepath = routepath[1:]
        self._setup_route()
        
    def _setup_route(self):
        # Build our routelist, and the keys used in the route
        self.routelist = routelist = self._pathkeys(self.routepath)
        routekeys = frozenset([key['name'] for key in routelist
                               if isinstance(key, dict)])
        self.dotkeys = frozenset([key['name'] for key in routelist
                                  if isinstance(key, dict) and 
                                     key['type'] == '.'])

        if not self.minimization:
            self.make_full_route()
        
        # Build a req list with all the regexp requirements for our args
        self.req_regs = {}
        for key, val in self.reqs.iteritems():
            self.req_regs[key] = re.compile('^' + val + '$')
        # Update our defaults and set new default keys if needed. defaults
        # needs to be saved
        (self.defaults, defaultkeys) = self._defaults(routekeys, 
                                                      self.reserved_keys, 
                                                      self._kargs.copy())
        # Save the maximum keys we could utilize
        self.maxkeys = defaultkeys | routekeys
        
        # Populate our minimum keys, and save a copy of our backward keys for
        # quicker generation later
        (self.minkeys, self.routebackwards) = self._minkeys(routelist[:])
        
        # Populate our hardcoded keys, these are ones that are set and don't 
        # exist in the route
        self.hardcoded = frozenset([key for key in self.maxkeys \
            if key not in routekeys and self.defaults[key] is not None])
        
        # Cache our default keys
        self._default_keys = frozenset(self.defaults.keys())
    
    def make_full_route(self):
        """Make a full routelist string for use with non-minimized
        generation"""
        regpath = ''
        for part in self.routelist:
            if isinstance(part, dict):
                regpath += '%(' + part['name'] + ')s'
            else:
                regpath += part
        self.regpath = regpath
    
    def make_unicode(self, s):
        """Transform the given argument into a unicode string."""
        if isinstance(s, unicode):
            return s
        elif isinstance(s, bytes):
            return s.decode(self.encoding)
        elif callable(s):
            return s
        else:
            return unicode(s)
    
    def _pathkeys(self, routepath):
        """Utility function to walk the route, and pull out the valid
        dynamic/wildcard keys."""
        collecting = False
        current = ''
        done_on = ''
        var_type = ''
        just_started = False
        routelist = []
        for char in routepath:
            if char in [':', '*', '{'] and not collecting and not self.static \
               or char in ['{'] and not collecting:
                just_started = True
                collecting = True
                var_type = char
                if char == '{':
                    done_on = '}'
                    just_started = False
                if len(current) > 0:
                    routelist.append(current)
                    current = ''
            elif collecting and just_started:
                just_started = False
                if char == '(':
                    done_on = ')'
                else:
                    current = char
                    done_on = self.done_chars + ('-',)
            elif collecting and char not in done_on:
                current += char
            elif collecting:
                collecting = False
                if var_type == '{':
                    if current[0] == '.':
                        var_type = '.'
                        current = current[1:]
                    else:
                        var_type = ':'
                    opts = current.split(':')
                    if len(opts) > 1:
                        current = opts[0]
                        self.reqs[current] = opts[1]
                routelist.append(dict(type=var_type, name=current))
                if char in self.done_chars:
                    routelist.append(char)
                done_on = var_type = current = ''
            else:
                current += char
        if collecting:
            routelist.append(dict(type=var_type, name=current))
        elif current:
            routelist.append(current)
        return routelist

    def _minkeys(self, routelist):
        """Utility function to walk the route backwards
        
        Will also determine the minimum keys we can handle to generate
        a working route.
        
        routelist is a list of the '/' split route path
        defaults is a dict of all the defaults provided for the route
        
        """
        minkeys = []
        backcheck = routelist[:]
        
        # If we don't honor minimization, we need all the keys in the
        # route path
        if not self.minimization:
            for part in backcheck:
                if isinstance(part, dict):
                    minkeys.append(part['name'])
            return (frozenset(minkeys), backcheck)
        
        gaps = False
        backcheck.reverse()
        for part in backcheck:
            if not isinstance(part, dict) and part not in self.done_chars:
                gaps = True
                continue
            elif not isinstance(part, dict):
                continue
            key = part['name']
            if self.defaults.has_key(key) and not gaps:
                continue
            minkeys.append(key)
            gaps = True
        return  (frozenset(minkeys), backcheck)
    
    def _defaults(self, routekeys, reserved_keys, kargs):
        """Creates default set with values stringified
        
        Put together our list of defaults, stringify non-None values
        and add in our action/id default if they use it and didn't
        specify it.
        
        defaultkeys is a list of the currently assumed default keys
        routekeys is a list of the keys found in the route path
        reserved_keys is a list of keys that are not
        
        """
        defaults = {}
        # Add in a controller/action default if they don't exist
        if 'controller' not in routekeys and 'controller' not in kargs \
           and not self.explicit:
            kargs['controller'] = 'content'
        if 'action' not in routekeys and 'action' not in kargs \
           and not self.explicit:
            kargs['action'] = 'index'
        defaultkeys = frozenset([key for key in kargs.keys() \
                                 if key not in reserved_keys])
        for key in defaultkeys:
            if kargs[key] is not None:
                defaults[key] = self.make_unicode(kargs[key])
            else:
                defaults[key] = None
        if 'action' in routekeys and not defaults.has_key('action') \
           and not self.explicit:
            defaults['action'] = 'index'
        if 'id' in routekeys and not defaults.has_key('id') \
           and not self.explicit:
            defaults['id'] = None
        newdefaultkeys = frozenset([key for key in defaults.keys() \
                                    if key not in reserved_keys])
        
        return (defaults, newdefaultkeys)
        
    def makeregexp(self, clist, include_names=True):
        """Create a regular expression for matching purposes
        
        Note: This MUST be called before match can function properly.
        
        clist should be a list of valid controller strings that can be 
        matched, for this reason makeregexp should be called by the web
        framework after it knows all available controllers that can be
        utilized.
        
        include_names indicates whether this should be a match regexp
        assigned to itself using regexp grouping names, or if names
        should be excluded for use in a single larger regexp to
        determine if any routes match
        
        """
        if self.minimization:
            reg = self.buildnextreg(self.routelist, clist, include_names)[0]
            if not reg:
                reg = '/'
            reg = reg + '/?' + '$'
        
            if not reg.startswith('/'):
                reg = '/' + reg
        else:
            reg = self.buildfullreg(clist, include_names)
        
        reg = '^' + reg
        
        if not include_names:
            return reg
        
        self.regexp = reg
        self.regmatch = re.compile(reg)
    
    def buildfullreg(self, clist, include_names=True):
        """Build the regexp by iterating through the routelist and
        replacing dicts with the appropriate regexp match"""
        regparts = []
        for part in self.routelist:
            if isinstance(part, dict):
                var = part['name']
                if var == 'controller':
                    partmatch = '|'.join(map(re.escape, clist))
                elif part['type'] == ':':
                    partmatch = self.reqs.get(var) or '[^/]+?'
                elif part['type'] == '.':
                    partmatch = self.reqs.get(var) or '[^/.]+?'
                else:
                    partmatch = self.reqs.get(var) or '.+?'
                if include_names:
                    regpart = '(?P<%s>%s)' % (var, partmatch)
                else:
                    regpart = '(?:%s)' % partmatch
                if part['type'] == '.':
                    regparts.append('(?:\.%s)??' % regpart)
                else:
                    regparts.append(regpart)
            else:
                regparts.append(re.escape(part))
        regexp = ''.join(regparts) + '$'
        return regexp
    
    def buildnextreg(self, path, clist, include_names=True):
        """Recursively build our regexp given a path, and a controller
        list.
        
        Returns the regular expression string, and two booleans that
        can be ignored as they're only used internally by buildnextreg.
        
        """
        if path:
            part = path[0]
        else:
            part = ''
        reg = ''
        
        # noreqs will remember whether the remainder has either a string 
        # match, or a non-defaulted regexp match on a key, allblank remembers
        # if the rest could possible be completely empty
        (rest, noreqs, allblank) = ('', True, True)
        if len(path[1:]) > 0:
            self.prior = part
            (rest, noreqs, allblank) = self.buildnextreg(path[1:], clist, include_names)
        
        if isinstance(part, dict) and part['type'] in (':', '.'):
            var = part['name']
            typ = part['type']
            partreg = ''
            
            # First we plug in the proper part matcher
            if self.reqs.has_key(var):
                if include_names:
                    partreg = '(?P<%s>%s)' % (var, self.reqs[var])
                else:
                    partreg = '(?:%s)' % self.reqs[var]
                if typ == '.':
                    partreg = '(?:\.%s)??' % partreg
            elif var == 'controller':
                if include_names:
                    partreg = '(?P<%s>%s)' % (var, '|'.join(map(re.escape, clist)))
                else:
                    partreg = '(?:%s)' % '|'.join(map(re.escape, clist))
            elif self.prior in ['/', '#']:
                if include_names:
                    partreg = '(?P<' + var + '>[^' + self.prior + ']+?)'
                else:
                    partreg = '(?:[^' + self.prior + ']+?)'
            else:
                if not rest:
                    if typ == '.':
                        exclude_chars = '/.'
                    else:
                        exclude_chars = '/'
                    if include_names:
                        partreg = '(?P<%s>[^%s]+?)' % (var, exclude_chars)
                    else:
                        partreg = '(?:[^%s]+?)' % exclude_chars
                    if typ == '.':
                        partreg = '(?:\.%s)??' % partreg
                else:
                    end = ''.join(self.done_chars)
                    rem = rest
                    if rem[0] == '\\' and len(rem) > 1:
                        rem = rem[1]
                    elif rem.startswith('(\\') and len(rem) > 2:
                        rem = rem[2]
                    else:
                        rem = end
                    rem = frozenset(rem) | frozenset(['/'])
                    if include_names:
                        partreg = '(?P<%s>[^%s]+?)' % (var, ''.join(rem))
                    else:
                        partreg = '(?:[^%s]+?)' % ''.join(rem)
            
            if self.reqs.has_key(var):
                noreqs = False
            if not self.defaults.has_key(var): 
                allblank = False
                noreqs = False
            
            # Now we determine if its optional, or required. This changes 
            # depending on what is in the rest of the match. If noreqs is 
            # true, then its possible the entire thing is optional as there's
            # no reqs or string matches.
            if noreqs:
                # The rest is optional, but now we have an optional with a 
                # regexp. Wrap to ensure that if we match anything, we match
                # our regexp first. It's still possible we could be completely
                # blank as we have a default
                if self.reqs.has_key(var) and self.defaults.has_key(var):
                    reg = '(' + partreg + rest + ')?'
                
                # Or we have a regexp match with no default, so now being 
                # completely blank form here on out isn't possible
                elif self.reqs.has_key(var):
                    allblank = False
                    reg = partreg + rest
                
                # If the character before this is a special char, it has to be
                # followed by this
                elif self.defaults.has_key(var) and \
                     self.prior in (',', ';', '.'):
                    reg = partreg + rest
                
                # Or we have a default with no regexp, don't touch the allblank
                elif self.defaults.has_key(var):
                    reg = partreg + '?' + rest
                
                # Or we have a key with no default, and no reqs. Not possible
                # to be all blank from here
                else:
                    allblank = False
                    reg = partreg + rest
            # In this case, we have something dangling that might need to be
            # matched
            else:
                # If they can all be blank, and we have a default here, we know
                # its safe to make everything from here optional. Since 
                # something else in the chain does have req's though, we have
                # to make the partreg here required to continue matching
                if allblank and self.defaults.has_key(var):
                    reg = '(' + partreg + rest + ')?'
                    
                # Same as before, but they can't all be blank, so we have to 
                # require it all to ensure our matches line up right
                else:
                    reg = partreg + rest
        elif isinstance(part, dict) and part['type'] == '*':
            var = part['name']
            if noreqs:
                if include_names:
                    reg = '(?P<%s>.*)' % var + rest
                else:
                    reg = '(?:.*)' + rest
                if not self.defaults.has_key(var):
                    allblank = False
                    noreqs = False
            else:
                if allblank and self.defaults.has_key(var):
                    if include_names:
                        reg = '(?P<%s>.*)' % var + rest
                    else:
                        reg = '(?:.*)' + rest
                elif self.defaults.has_key(var):
                    if include_names:
                        reg = '(?P<%s>.*)' % var + rest
                    else:
                        reg = '(?:.*)' + rest
                else:
                    if include_names:
                        reg = '(?P<%s>.*)' % var + rest
                    else:
                        reg = '(?:.*)' + rest
                    allblank = False
                    noreqs = False
        elif part and part[-1] in self.done_chars:
            if allblank:
                reg = re.escape(part[:-1]) + '(' + re.escape(part[-1]) + rest
                reg += ')?'
            else:
                allblank = False
                reg = re.escape(part) + rest
        
        # We have a normal string here, this is a req, and it prevents us from 
        # being all blank
        else:
            noreqs = False
            allblank = False
            reg = re.escape(part) + rest
        
        return (reg, noreqs, allblank)
    
    def match(self, url, environ=None, sub_domains=False, 
              sub_domains_ignore=None, domain_match=''):
        """Match a url to our regexp. 
        
        While the regexp might match, this operation isn't
        guaranteed as there's other factors that can cause a match to
        fail even though the regexp succeeds (Default that was relied
        on wasn't given, requirement regexp doesn't pass, etc.).
        
        Therefore the calling function shouldn't assume this will
        return a valid dict, the other possible return is False if a
        match doesn't work out.
        
        """
        # Static routes don't match, they generate only
        if self.static:
            return False
        
        match = self.regmatch.match(url)
        
        if not match:
            return False
            
        sub_domain = None
        
        if sub_domains and environ and 'HTTP_HOST' in environ:
            host = environ['HTTP_HOST'].split(':')[0]
            sub_match = re.compile('^(.+?)\.%s$' % domain_match)
            subdomain = re.sub(sub_match, r'\1', host)
            if subdomain not in sub_domains_ignore and host != subdomain:
                sub_domain = subdomain
        
        if self.conditions:
            if 'method' in self.conditions and environ and \
                environ['REQUEST_METHOD'] not in self.conditions['method']:
                return False
            
            # Check sub-domains?
            use_sd = self.conditions.get('sub_domain')
            if use_sd and not sub_domain:
                return False
            elif not use_sd and 'sub_domain' in self.conditions and sub_domain:
                return False
            if isinstance(use_sd, list) and sub_domain not in use_sd:
                return False
        
        matchdict = match.groupdict()
        result = {}
        extras = self._default_keys - frozenset(matchdict.keys())
        for key, val in matchdict.iteritems():
            if key != 'path_info' and self.encoding:
                # change back into python unicode objects from the URL 
                # representation
                try:
                    val = as_unicode(val, self.encoding, self.decode_errors)
                except UnicodeDecodeError:
                    return False
            
            if not val and key in self.defaults and self.defaults[key]:
                result[key] = self.defaults[key]
            else:
                result[key] = val
        for key in extras:
            result[key] = self.defaults[key]
        
        # Add the sub-domain if there is one
        if sub_domains:
            result['sub_domain'] = sub_domain
        
        # If there's a function, call it with environ and expire if it
        # returns False
        if self.conditions and 'function' in self.conditions and \
            not self.conditions['function'](environ, result):
            return False
        
        return result
    
    def generate_non_minimized(self, kargs):
        """Generate a non-minimal version of the URL"""
        # Iterate through the keys that are defaults, and NOT in the route
        # path. If its not in kargs, or doesn't match, or is None, this
        # route won't work
        for k in self.maxkeys - self.minkeys:
            if k not in kargs:
                return False
            elif self.make_unicode(kargs[k]) != \
                self.make_unicode(self.defaults[k]):
                return False
                
        # Ensure that all the args in the route path are present and not None
        for arg in self.minkeys:
            if arg not in kargs or kargs[arg] is None:
                if arg in self.dotkeys:
                    kargs[arg] = ''
                else:
                    return False

        # Encode all the argument that the regpath can use
        for k in kargs:
            if k in self.maxkeys:
                if k in self.dotkeys:
                    if kargs[k]:
                        kargs[k] = url_quote('.' + as_unicode(kargs[k], self.encoding), self.encoding)
                else:
                    kargs[k] = url_quote(as_unicode(kargs[k], self.encoding), self.encoding)

        return self.regpath % kargs
    
    def generate_minimized(self, kargs):
        """Generate a minimized version of the URL"""
        routelist = self.routebackwards
        urllist = []
        gaps = False
        for part in routelist:
            if isinstance(part, dict) and part['type'] in (':', '.'):
                arg = part['name']
                
                # For efficiency, check these just once
                has_arg = kargs.has_key(arg)
                has_default = self.defaults.has_key(arg)
                
                # Determine if we can leave this part off
                # First check if the default exists and wasn't provided in the 
                # call (also no gaps)
                if has_default and not has_arg and not gaps:
                    continue
                    
                # Now check to see if there's a default and it matches the 
                # incoming call arg
                if (has_default and has_arg) and self.make_unicode(kargs[arg]) == \
                    self.make_unicode(self.defaults[arg]) and not gaps: 
                    continue
                
                # We need to pull the value to append, if the arg is None and 
                # we have a default, use that
                if has_arg and kargs[arg] is None and has_default and not gaps:
                    continue
                
                # Otherwise if we do have an arg, use that
                elif has_arg:
                    val = kargs[arg]
                
                elif has_default and self.defaults[arg] is not None:
                    val = self.defaults[arg]
                # Optional format parameter?
                elif part['type'] == '.':
                    continue
                # No arg at all? This won't work
                else:
                    return False
                    
                val = as_unicode(val, self.encoding)
                urllist.append(url_quote(val, self.encoding))
                if part['type'] == '.':
                    urllist.append('.')

                if has_arg:
                    del kargs[arg]
                gaps = True
            elif isinstance(part, dict) and part['type'] == '*':
                arg = part['name']
                kar = kargs.get(arg)
                if kar is not None:
                    urllist.append(url_quote(kar, self.encoding))
                    gaps = True
            elif part and part[-1] in self.done_chars:
                if not gaps and part in self.done_chars:
                    continue
                elif not gaps:
                    urllist.append(part[:-1])
                    gaps = True
                else:
                    gaps = True
                    urllist.append(part)
            else:
                gaps = True
                urllist.append(part)
        urllist.reverse()
        url = ''.join(urllist)
        return url
    
    def generate(self, _ignore_req_list=False, _append_slash=False, **kargs):
        """Generate a URL from ourself given a set of keyword arguments
        
        Toss an exception if this
        set of keywords would cause a gap in the url.
        
        """
        # Verify that our args pass any regexp requirements
        if not _ignore_req_list:
            for key in self.reqs.keys():
                val = kargs.get(key)
                if val and not self.req_regs[key].match(self.make_unicode(val)):
                    return False
        
        # Verify that if we have a method arg, its in the method accept list. 
        # Also, method will be changed to _method for route generation
        meth = as_unicode(kargs.get('method'), self.encoding)
        if meth:
            if self.conditions and 'method' in self.conditions \
                and meth.upper() not in self.conditions['method']:
                return False
            kargs.pop('method')
        
        if self.minimization:
            url = self.generate_minimized(kargs)
        else:
            url = self.generate_non_minimized(kargs)
        
        if url is False:
            return url
        
        if not url.startswith('/') and not self.static:
            url = '/' + url
        extras = frozenset(kargs.keys()) - self.maxkeys
        if extras:
            if _append_slash and not url.endswith('/'):
                url += '/'
            fragments = []
            # don't assume the 'extras' set preserves order: iterate
            # through the ordered kargs instead
            for key in kargs:
                if key not in extras:
                    continue
                if key == 'action' or key == 'controller':
                    continue
                val = kargs[key]
                if isinstance(val, (tuple, list)):
                    for value in val:
                        value = as_unicode(value, self.encoding)
                        fragments.append((key, _str_encode(value, self.encoding)))
                else:
                    val = as_unicode(val, self.encoding)
                    fragments.append((key, _str_encode(val, self.encoding)))
            if fragments:
                url += '?'
                url += urllib.urlencode(fragments)
        elif _append_slash and not url.endswith('/'):
            url += '/'
        return url

########NEW FILE########
__FILENAME__ = util
"""Utility functions for use in templates / controllers

*PLEASE NOTE*: Many of these functions expect an initialized RequestConfig
object. This is expected to have been initialized for EACH REQUEST by the web
framework.

"""
import os
import re
import urllib
from routes import request_config


class RoutesException(Exception):
    """Tossed during Route exceptions"""


class MatchException(RoutesException):
    """Tossed during URL matching exceptions"""


class GenerationException(RoutesException):
    """Tossed during URL generation exceptions"""


def _screenargs(kargs, mapper, environ, force_explicit=False):
    """
    Private function that takes a dict, and screens it against the current 
    request dict to determine what the dict should look like that is used. 
    This is responsible for the requests "memory" of the current.
    """
    # Coerce any unicode args with the encoding
    encoding = mapper.encoding
    for key, val in kargs.iteritems():
        if isinstance(val, unicode):
            kargs[key] = val.encode(encoding)
    
    if mapper.explicit and mapper.sub_domains and not force_explicit:
        return _subdomain_check(kargs, mapper, environ)
    elif mapper.explicit and not force_explicit:
        return kargs
    
    controller_name = as_unicode(kargs.get('controller'), encoding)
    
    if controller_name and controller_name.startswith('/'):
        # If the controller name starts with '/', ignore route memory
        kargs['controller'] = kargs['controller'][1:]
        return kargs
    elif controller_name and not kargs.has_key('action'):
        # Fill in an action if we don't have one, but have a controller
        kargs['action'] = 'index'
    
    route_args = environ.get('wsgiorg.routing_args')
    if route_args:
        memory_kargs = route_args[1].copy()
    else:
        memory_kargs = {}
     
    # Remove keys from memory and kargs if kargs has them as None
    for key in [key for key in kargs.keys() if kargs[key] is None]:
        del kargs[key]
        if memory_kargs.has_key(key):
            del memory_kargs[key]
    
    # Merge the new args on top of the memory args
    memory_kargs.update(kargs)
    
    # Setup a sub-domain if applicable
    if mapper.sub_domains:
        memory_kargs = _subdomain_check(memory_kargs, mapper, environ)
    return memory_kargs


def _subdomain_check(kargs, mapper, environ):
    """Screen the kargs for a subdomain and alter it appropriately depending
    on the current subdomain or lack therof."""
    if mapper.sub_domains:
        subdomain = kargs.pop('sub_domain', None)
        if isinstance(subdomain, unicode):
            subdomain = str(subdomain)
        
        fullhost = environ.get('HTTP_HOST') or environ.get('SERVER_NAME')
        
        # In case environ defaulted to {}
        if not fullhost:
            return kargs
        
        hostmatch = fullhost.split(':')
        host = hostmatch[0]
        port = ''
        if len(hostmatch) > 1:
            port += ':' + hostmatch[1]
        sub_match = re.compile('^.+?\.(%s)$' % mapper.domain_match)
        domain = re.sub(sub_match, r'\1', host)
        subdomain = as_unicode(subdomain, mapper.encoding)
        if subdomain and not host.startswith(subdomain) and \
            subdomain not in mapper.sub_domains_ignore:
            kargs['_host'] = subdomain + '.' + domain + port
        elif (subdomain in mapper.sub_domains_ignore or \
            subdomain is None) and domain != host:
            kargs['_host'] = domain + port
        return kargs
    else:
        return kargs


def _url_quote(string, encoding):
    """A Unicode handling version of urllib.quote."""
    if encoding:
        if isinstance(string, unicode):
            s = string.encode(encoding)
        elif isinstance(string, str):
            # assume the encoding is already correct
            s = string
        else:
            s = unicode(string).encode(encoding)
    else:
        s = str(string)
    return urllib.quote(s, '/')


def _str_encode(string, encoding):
    if encoding:
        if isinstance(string, unicode):
            s = string.encode(encoding)
        elif isinstance(string, str):
            # assume the encoding is already correct
            s = string
        else:
            s = unicode(string).encode(encoding)
    return s


def url_for(*args, **kargs):
    """Generates a URL 
    
    All keys given to url_for are sent to the Routes Mapper instance for 
    generation except for::
        
        anchor          specified the anchor name to be appened to the path
        host            overrides the default (current) host if provided
        protocol        overrides the default (current) protocol if provided
        qualified       creates the URL with the host/port information as 
                        needed
        
    The URL is generated based on the rest of the keys. When generating a new 
    URL, values will be used from the current request's parameters (if 
    present). The following rules are used to determine when and how to keep 
    the current requests parameters:
    
    * If the controller is present and begins with '/', no defaults are used
    * If the controller is changed, action is set to 'index' unless otherwise 
      specified
    
    For example, if the current request yielded a dict of
    {'controller': 'blog', 'action': 'view', 'id': 2}, with the standard 
    ':controller/:action/:id' route, you'd get the following results::
    
        url_for(id=4)                    =>  '/blog/view/4',
        url_for(controller='/admin')     =>  '/admin',
        url_for(controller='admin')      =>  '/admin/view/2'
        url_for(action='edit')           =>  '/blog/edit/2',
        url_for(action='list', id=None)  =>  '/blog/list'
    
    **Static and Named Routes**
    
    If there is a string present as the first argument, a lookup is done 
    against the named routes table to see if there's any matching routes. The
    keyword defaults used with static routes will be sent in as GET query 
    arg's if a route matches.
    
    If no route by that name is found, the string is assumed to be a raw URL. 
    Should the raw URL begin with ``/`` then appropriate SCRIPT_NAME data will
    be added if present, otherwise the string will be used as the url with 
    keyword args becoming GET query args.
    
    """
    anchor = kargs.get('anchor')
    host = kargs.get('host')
    protocol = kargs.get('protocol')
    qualified = kargs.pop('qualified', None)
    
    # Remove special words from kargs, convert placeholders
    for key in ['anchor', 'host', 'protocol']:
        if kargs.get(key):
            del kargs[key]
    config = request_config()
    route = None
    static = False
    encoding = config.mapper.encoding
    url = ''
    if len(args) > 0:
        route = config.mapper._routenames.get(args[0])
        
        # No named route found, assume the argument is a relative path
        if not route:
            static = True
            url = args[0]
        
        if url.startswith('/') and hasattr(config, 'environ') \
                and config.environ.get('SCRIPT_NAME'):
            url = config.environ.get('SCRIPT_NAME') + url
        
        if static:
            if kargs:
                url += '?'
                query_args = []
                for key, val in kargs.iteritems():
                    if isinstance(val, (list, tuple)):
                        for value in val:
                            query_args.append("%s=%s" % (
                                urllib.quote(unicode(key).encode(encoding)),
                                urllib.quote(unicode(value).encode(encoding))))
                    else:
                        query_args.append("%s=%s" % (
                            urllib.quote(unicode(key).encode(encoding)),
                            urllib.quote(unicode(val).encode(encoding))))
                url += '&'.join(query_args)
    environ = getattr(config, 'environ', {})
    if 'wsgiorg.routing_args' not in environ:
        environ = environ.copy()
        mapper_dict = getattr(config, 'mapper_dict', None)
        if mapper_dict is not None:
            match_dict = mapper_dict.copy()
        else:
            match_dict = {}
        environ['wsgiorg.routing_args'] = ((), match_dict)
    
    if not static:
        route_args = []
        if route:
            if config.mapper.hardcode_names:
                route_args.append(route)
            newargs = route.defaults.copy()
            newargs.update(kargs)
            
            # If this route has a filter, apply it
            if route.filter:
                newargs = route.filter(newargs)
            
            if not route.static:
                # Handle sub-domains
                newargs = _subdomain_check(newargs, config.mapper, environ)
        else:
            newargs = _screenargs(kargs, config.mapper, environ)
        anchor = newargs.pop('_anchor', None) or anchor
        host = newargs.pop('_host', None) or host
        protocol = newargs.pop('_protocol', None) or protocol
        url = config.mapper.generate(*route_args, **newargs)
    if anchor is not None:
        url += '#' + _url_quote(anchor, encoding)
    if host or protocol or qualified:
        if not host and not qualified:
            # Ensure we don't use a specific port, as changing the protocol
            # means that we most likely need a new port
            host = config.host.split(':')[0]
        elif not host:
            host = config.host
        if not protocol:
            protocol = config.protocol
        if url is not None:
            url = protocol + '://' + host + url
    
    if not ascii_characters(url) and url is not None:
        raise GenerationException("url_for can only return a string, got "
                        "unicode instead: %s" % url)
    if url is None:
        raise GenerationException(
            "url_for could not generate URL. Called with args: %s %s" % \
            (args, kargs))
    return url


class URLGenerator(object):
    """The URL Generator generates URL's
    
    It is automatically instantiated by the RoutesMiddleware and put
    into the ``wsgiorg.routing_args`` tuple accessible as::
    
        url = environ['wsgiorg.routing_args'][0][0]
    
    Or via the ``routes.url`` key::
    
        url = environ['routes.url']
    
    The url object may be instantiated outside of a web context for use
    in testing, however sub_domain support and fully qualified URL's
    cannot be generated without supplying a dict that must contain the
    key ``HTTP_HOST``.
    
    """
    def __init__(self, mapper, environ):
        """Instantiate the URLGenerator
        
        ``mapper``
            The mapper object to use when generating routes.
        ``environ``
            The environment dict used in WSGI, alternately, any dict
            that contains at least an ``HTTP_HOST`` value.
        
        """
        self.mapper = mapper
        if 'SCRIPT_NAME' not in environ:
            environ['SCRIPT_NAME'] = ''
        self.environ = environ
    
    def __call__(self, *args, **kargs):
        """Generates a URL 

        All keys given to url_for are sent to the Routes Mapper instance for 
        generation except for::

            anchor          specified the anchor name to be appened to the path
            host            overrides the default (current) host if provided
            protocol        overrides the default (current) protocol if provided
            qualified       creates the URL with the host/port information as 
                            needed

        """
        anchor = kargs.get('anchor')
        host = kargs.get('host')
        protocol = kargs.get('protocol')
        qualified = kargs.pop('qualified', None)

        # Remove special words from kargs, convert placeholders
        for key in ['anchor', 'host', 'protocol']:
            if kargs.get(key):
                del kargs[key]
        
        route = None
        use_current = '_use_current' in kargs and kargs.pop('_use_current')
        
        static = False
        encoding = self.mapper.encoding
        url = ''
                
        more_args = len(args) > 0
        if more_args:
            route = self.mapper._routenames.get(args[0])
        
        if not route and more_args:
            static = True
            url = args[0]
            if url.startswith('/') and self.environ.get('SCRIPT_NAME'):
                url = self.environ.get('SCRIPT_NAME') + url

            if static:
                if kargs:
                    url += '?'
                    query_args = []
                    for key, val in kargs.iteritems():
                        if isinstance(val, (list, tuple)):
                            for value in val:
                                query_args.append("%s=%s" % (
                                    urllib.quote(unicode(key).encode(encoding)),
                                    urllib.quote(unicode(value).encode(encoding))))
                        else:
                            query_args.append("%s=%s" % (
                                urllib.quote(unicode(key).encode(encoding)),
                                urllib.quote(unicode(val).encode(encoding))))
                    url += '&'.join(query_args)
        if not static:
            route_args = []
            if route:
                if self.mapper.hardcode_names:
                    route_args.append(route)
                newargs = route.defaults.copy()
                newargs.update(kargs)
                
                # If this route has a filter, apply it
                if route.filter:
                    newargs = route.filter(newargs)
                if not route.static or (route.static and not route.external):
                    # Handle sub-domains, retain sub_domain if there is one
                    sub = newargs.get('sub_domain', None)
                    newargs = _subdomain_check(newargs, self.mapper,
                                               self.environ)
                    # If the route requires a sub-domain, and we have it, restore
                    # it
                    if 'sub_domain' in route.defaults:
                        newargs['sub_domain'] = sub
                    
            elif use_current:
                newargs = _screenargs(kargs, self.mapper, self.environ, force_explicit=True)
            elif 'sub_domain' in kargs:
                newargs = _subdomain_check(kargs, self.mapper, self.environ)
            else:
                newargs = kargs
            
            anchor = anchor or newargs.pop('_anchor', None)
            host = host or newargs.pop('_host', None)
            protocol = protocol or newargs.pop('_protocol', None)
            newargs['_environ'] = self.environ
            url = self.mapper.generate(*route_args, **newargs)
        if anchor is not None:
            url += '#' + _url_quote(anchor, encoding)
        if host or protocol or qualified:
            if 'routes.cached_hostinfo' not in self.environ:
                cache_hostinfo(self.environ)
            hostinfo = self.environ['routes.cached_hostinfo']
            
            if not host and not qualified:
                # Ensure we don't use a specific port, as changing the protocol
                # means that we most likely need a new port
                host = hostinfo['host'].split(':')[0]
            elif not host:
                host = hostinfo['host']
            if not protocol:
                protocol = hostinfo['protocol']
            if url is not None:
                if host[-1] != '/':
                    host += '/'
                url = protocol + '://' + host + url.lstrip('/')

        if not ascii_characters(url) and url is not None:
            raise GenerationException("Can only return a string, got "
                            "unicode instead: %s" % url)
        if url is None:
            raise GenerationException(
                "Could not generate URL. Called with args: %s %s" % \
                (args, kargs))
        return url
    
    def current(self, *args, **kwargs):
        """Generate a route that includes params used on the current
        request
        
        The arguments for this method are identical to ``__call__``
        except that arguments set to None will remove existing route
        matches of the same name from the set of arguments used to
        construct a URL.
        """
        return self(_use_current=True, *args, **kwargs)


def redirect_to(*args, **kargs):
    """Issues a redirect based on the arguments. 
    
    Redirect's *should* occur as a "302 Moved" header, however the web 
    framework may utilize a different method.
    
    All arguments are passed to url_for to retrieve the appropriate URL, then
    the resulting URL it sent to the redirect function as the URL.
    """
    target = url_for(*args, **kargs)
    config = request_config()
    return config.redirect(target)


def cache_hostinfo(environ):
    """Processes the host information and stores a copy
    
    This work was previously done but wasn't stored in environ, nor is
    it guaranteed to be setup in the future (Routes 2 and beyond).
    
    cache_hostinfo processes environ keys that may be present to
    determine the proper host, protocol, and port information to use
    when generating routes.
    
    """
    hostinfo = {}
    if environ.get('HTTPS') or environ.get('wsgi.url_scheme') == 'https' \
       or environ.get('HTTP_X_FORWARDED_PROTO') == 'https':
        hostinfo['protocol'] = 'https'
    else:
        hostinfo['protocol'] = 'http'
    if environ.get('HTTP_X_FORWARDED_HOST'):
        hostinfo['host'] = environ['HTTP_X_FORWARDED_HOST']
    elif environ.get('HTTP_HOST'):
        hostinfo['host'] = environ['HTTP_HOST']
    else:
        hostinfo['host'] = environ['SERVER_NAME']
        if environ.get('wsgi.url_scheme') == 'https':
            if environ['SERVER_PORT'] != '443':
                hostinfo['host'] += ':' + environ['SERVER_PORT']
        else:
            if environ['SERVER_PORT'] != '80':
                hostinfo['host'] += ':' + environ['SERVER_PORT']
    environ['routes.cached_hostinfo'] = hostinfo
    return hostinfo


def controller_scan(directory=None):
    """Scan a directory for python files and use them as controllers"""
    if directory is None:
        return []
    
    def find_controllers(dirname, prefix=''):
        """Locate controllers in a directory"""
        controllers = []
        for fname in os.listdir(dirname):
            filename = os.path.join(dirname, fname)
            if os.path.isfile(filename) and \
                re.match('^[^_]{1,1}.*\.py$', fname):
                controllers.append(prefix + fname[:-3])
            elif os.path.isdir(filename):
                controllers.extend(find_controllers(filename, 
                                                    prefix=prefix+fname+'/'))
        return controllers
    controllers = find_controllers(directory)
    # Sort by string length, shortest goes first
    controllers.sort(key=len, reverse=True)
    return controllers

def as_unicode(value, encoding, errors='strict'):

    if value is not None and isinstance(value, bytes):
        return value.decode(encoding, errors)

    return value

def ascii_characters(string):

    if string is None:
        return True

    return all(ord(c) < 128 for c in string)
########NEW FILE########
__FILENAME__ = users
#

########NEW FILE########
__FILENAME__ = content
#

########NEW FILE########
__FILENAME__ = users
#

########NEW FILE########
__FILENAME__ = profile_rec
try:
    import profile
    import pstats
except ImportError:
    pass
import tempfile
import os
import time
from routes import Mapper

def get_mapper():
    m = Mapper()
    m.connect('', controller='articles', action='index')
    m.connect('admin', controller='admin/general', action='index')

    m.connect('admin/comments/article/:article_id/:action/:id',
              controller = 'admin/comments', action = None, id=None)
    m.connect('admin/trackback/article/:article_id/:action/:id',
              controller='admin/trackback', action=None, id=None)
    m.connect('admin/content/:action/:id', controller='admin/content')

    m.connect('xml/:action/feed.xml', controller='xml')
    m.connect('xml/articlerss/:id/feed.xml', controller='xml',
              action='articlerss')
    m.connect('index.rdf', controller='xml', action='rss')

    m.connect('articles', controller='articles', action='index')
    m.connect('articles/page/:page', controller='articles',
              action='index', requirements = {'page':'\d+'})

    m.connect(
        'articles/:year/:month/:day/page/:page',
        controller='articles', action='find_by_date', month = None,
        day = None,
        requirements = {'year':'\d{4}', 'month':'\d{1,2}','day':'\d{1,2}'})

    m.connect('articles/category/:id', controller='articles', action='category')
    m.connect('pages/*name', controller='articles', action='view_page')
    m.create_regs(['content','admin/why', 'admin/user'])
    return m

def bench_rec(mapper, n):
    ts = time.time()
    for x in range(1,n):
        pass
    en = time.time()

    match = mapper.match

    # hits
    start = time.time()
    for x in range(1,n):
        match('/admin')
        match('/xml/1/feed.xml')
        match('/index.rdf')
    end = time.time()
    total = end-start-(en-ts)
    per_url = total / (n*10)
    print "Hit recognition\n"
    print "%s ms/url" % (per_url*1000)
    print "%s urls/s\n" % (1.00/per_url)

    # misses
    start = time.time()
    for x in range(1,n):
        match('/content')
        match('/content/list')
        match('/content/show/10')
    end = time.time()
    total = end-start-(en-ts)
    per_url = total / (n*10)
    print "Miss recognition\n"
    print "%s ms/url" % (per_url*1000)
    print "%s urls/s\n" % (1.00/per_url)
        
def do_profile(cmd, globals, locals, sort_order, callers):
    fd, fn = tempfile.mkstemp()
    try:
        if hasattr(profile, 'runctx'):
            profile.runctx(cmd, globals, locals, fn)
        else:
            raise NotImplementedError(
                'No profiling support under Python 2.3')
        stats = pstats.Stats(fn)
        stats.strip_dirs()
        # calls,time,cumulative and cumulative,calls,time are useful
        stats.sort_stats(*sort_order or ('cumulative', 'calls', 'time'))
        if callers:
            stats.print_callers()
        else:
            stats.print_stats()
    finally:
        os.remove(fn)

def main(n=300):
    mapper = get_mapper()
    do_profile('bench_rec(mapper, %s)' % n, globals(), locals(),
               ('time', 'cumulative', 'calls'), None)

if __name__ == '__main__':
    main()
    

########NEW FILE########
__FILENAME__ = test_explicit_use
"""test_explicit_use"""
import os, sys, time, unittest
from nose.tools import eq_, assert_raises

from routes import *
from routes.route import Route
from routes.util import GenerationException

class TestUtils(unittest.TestCase):
    def test_route_dict_use(self):
        m = Mapper()
        m.explicit = True
        m.connect('/hi/{fred}')
        
        environ = {'HTTP_HOST': 'localhost'}
        
        env = environ.copy()
        env['PATH_INFO'] = '/hi/george'
        
        eq_({'fred': 'george'}, m.match(environ=env))

    def test_x_forwarded(self):
        m = Mapper()
        m.explicit = True
        m.connect('/hi/{fred}')
        
        environ = {'HTTP_X_FORWARDED_HOST': 'localhost'}
        url = URLGenerator(m, environ)
        eq_('http://localhost/hi/smith', url(fred='smith', qualified=True))

    def test_server_port(self):
        m = Mapper()
        m.explicit = True
        m.connect('/hi/{fred}')
        
        environ = {'SERVER_NAME': 'localhost', 'wsgi.url_scheme': 'https',
                   'SERVER_PORT': '993'}
        url = URLGenerator(m, environ)
        eq_('https://localhost:993/hi/smith', url(fred='smith', qualified=True))

    def test_subdomain_screen(self):
        m = Mapper()
        m.explicit = True
        m.sub_domains = True
        m.connect('/hi/{fred}')
        
        environ = {'HTTP_HOST': 'localhost.com'}
        url = URLGenerator(m, environ)
        eq_('http://home.localhost.com/hi/smith', url(fred='smith', sub_domain=u'home', qualified=True))
        
        environ = {'HTTP_HOST': 'here.localhost.com', 'PATH_INFO': '/hi/smith'}
        url = URLGenerator(m, environ.copy())
        assert_raises(GenerationException, lambda: url.current(qualified=True))
        
        url = URLGenerator(m, {})
        eq_('/hi/smith', url(fred='smith', sub_domain=u'home'))

    def test_anchor(self):
        m = Mapper()
        m.explicit = True
        m.connect('/hi/{fred}')
        
        environ = {'HTTP_HOST': 'localhost.com'}
        url = URLGenerator(m, environ)
        eq_('/hi/smith#here', url(fred='smith', anchor='here'))

    def test_static_args(self):
        m = Mapper()
        m.explicit = True
        m.connect('http://google.com/', _static=True)
        
        url = URLGenerator(m, {})
        
        eq_('/here?q=fred&q=here%20now', url('/here', q=[u'fred', 'here now']))
    
    def test_current(self):
        m = Mapper()
        m.explicit = True
        m.connect('/hi/{fred}')
        
        environ = {'HTTP_HOST': 'localhost.com', 'PATH_INFO': '/hi/smith'}
        match = m.routematch(environ=environ)[0]
        environ['wsgiorg.routing_args'] = (None, match)
        url = URLGenerator(m, environ)
        eq_('/hi/smith', url.current())

    def test_add_routes(self):
        map = Mapper(explicit=True)
        map.minimization = False
        routes = [
            Route('foo', '/foo',)
        ]
        map.extend(routes)
        eq_(map.match('/foo'), {})
    
    def test_using_func(self):
        def fred(view): pass
        
        m = Mapper()
        m.explicit = True
        m.connect('/hi/{fred}', controller=fred)
        
        environ = {'HTTP_HOST': 'localhost.com', 'PATH_INFO': '/hi/smith'}
        match = m.routematch(environ=environ)[0]
        environ['wsgiorg.routing_args'] = (None, match)
        url = URLGenerator(m, environ)
        eq_('/hi/smith', url.current())
    
    def test_using_prefix(self):
        m = Mapper()
        m.explicit = True
        m.connect('/{first}/{last}')
        
        environ = {'HTTP_HOST': 'localhost.com', 'PATH_INFO': '/content/index', 'SCRIPT_NAME': '/jones'}
        match = m.routematch(environ=environ)[0]
        environ['wsgiorg.routing_args'] = (None, match)
        url = URLGenerator(m, environ)
        
        eq_('/jones/content/index', url.current())
        eq_('/jones/smith/barney', url(first='smith', last='barney'))


########NEW FILE########
__FILENAME__ = test_generation
"""test_generation"""
import sys, time, unittest
import urllib

from nose.tools import eq_, assert_raises
from routes import *

class TestGeneration(unittest.TestCase):

    def test_all_static_no_reqs(self):
        m = Mapper()
        m.connect('hello/world')

        eq_('/hello/world', m.generate())

    def test_basic_dynamic(self):
        for path in ['hi/:fred', 'hi/:(fred)']:
            m = Mapper()
            m.connect(path)

            eq_('/hi/index', m.generate(fred='index'))
            eq_('/hi/show', m.generate(fred='show'))
            eq_('/hi/list%20people', m.generate(fred='list people'))
            eq_(None, m.generate())

    def test_relative_url(self):
        m = Mapper(explicit=False)
        m.minimization = True
        m.environ = dict(HTTP_HOST='localhost')
        url = URLGenerator(m, m.environ)
        m.connect(':controller/:action/:id')
        m.create_regs(['content','blog','admin/comments'])

        eq_('about', url('about'))
        eq_('http://localhost/about', url('about', qualified=True))

    def test_basic_dynamic_explicit_use(self):
        m = Mapper()
        m.connect('hi/{fred}')
        url = URLGenerator(m, {})

        eq_('/hi/index', url(fred='index'))
        eq_('/hi/show', url(fred='show'))
        eq_('/hi/list%20people', url(fred='list people'))

    def test_dynamic_with_default(self):
        for path in ['hi/:action', 'hi/:(action)']:
            m = Mapper(explicit=False)
            m.minimization = True
            m.connect(path)

            eq_('/hi', m.generate(action='index'))
            eq_('/hi/show', m.generate(action='show'))
            eq_('/hi/list%20people', m.generate(action='list people'))
            eq_('/hi', m.generate())

    def test_dynamic_with_false_equivs(self):
        m = Mapper(explicit=False)
        m.minimization = True
        m.connect('article/:page', page=False)
        m.connect(':controller/:action/:id')

        eq_('/blog/view/0', m.generate(controller="blog", action="view", id="0"))
        eq_('/blog/view/0', m.generate(controller="blog", action="view", id=0))
        eq_('/blog/view/False', m.generate(controller="blog", action="view", id=False))
        eq_('/blog/view/False', m.generate(controller="blog", action="view", id='False'))
        eq_('/blog/view', m.generate(controller="blog", action="view", id=None))
        eq_('/blog/view', m.generate(controller="blog", action="view", id='None'))
        eq_('/article', m.generate(page=None))

        m = Mapper()
        m.minimization = True
        m.connect('view/:home/:area', home="austere", area=None)

        eq_('/view/sumatra', m.generate(home='sumatra'))
        eq_('/view/austere/chicago', m.generate(area='chicago'))

        m = Mapper()
        m.minimization = True
        m.connect('view/:home/:area', home=None, area=None)

        eq_('/view/None/chicago', m.generate(home=None, area='chicago'))

    def test_dynamic_with_underscore_parts(self):
        m = Mapper(explicit=False)
        m.minimization = True
        m.connect('article/:small_page', small_page=False)
        m.connect(':(controller)/:(action)/:(id)')

        eq_('/blog/view/0', m.generate(controller="blog", action="view", id="0"))
        eq_('/blog/view/False', m.generate(controller="blog", action="view", id='False'))
        eq_('/blog/view', m.generate(controller="blog", action="view", id='None'))
        eq_('/article', m.generate(small_page=None))
        eq_('/article/hobbes', m.generate(small_page='hobbes'))

    def test_dynamic_with_false_equivs_and_splits(self):
        m = Mapper(explicit=False)
        m.minimization = True
        m.connect('article/:(page)', page=False)
        m.connect(':(controller)/:(action)/:(id)')

        eq_('/blog/view/0', m.generate(controller="blog", action="view", id="0"))
        eq_('/blog/view/0', m.generate(controller="blog", action="view", id=0))
        eq_('/blog/view/False', m.generate(controller="blog", action="view", id=False))
        eq_('/blog/view/False', m.generate(controller="blog", action="view", id='False'))
        eq_('/blog/view', m.generate(controller="blog", action="view", id=None))
        eq_('/blog/view', m.generate(controller="blog", action="view", id='None'))
        eq_('/article', m.generate(page=None))

        m = Mapper()
        m.minimization = True
        m.connect('view/:(home)/:(area)', home="austere", area=None)

        eq_('/view/sumatra', m.generate(home='sumatra'))
        eq_('/view/austere/chicago', m.generate(area='chicago'))

        m = Mapper()
        m.minimization = True
        m.connect('view/:(home)/:(area)', home=None, area=None)

        eq_('/view/None/chicago', m.generate(home=None, area='chicago'))

    def test_dynamic_with_regexp_condition(self):
        for path in ['hi/:name', 'hi/:(name)']:
            m = Mapper()
            m.connect(path, requirements = {'name':'[a-z]+'})

            eq_('/hi/index', m.generate(name='index'))
            eq_(None, m.generate(name='fox5'))
            eq_(None, m.generate(name='something_is_up'))
            eq_('/hi/abunchofcharacter', m.generate(name='abunchofcharacter'))
            eq_(None, m.generate())

    def test_dynamic_with_default_and_regexp_condition(self):
        for path in ['hi/:action', 'hi/:(action)']:
            m = Mapper(explicit=False)
            m.minimization = True
            m.connect(path, requirements = {'action':'[a-z]+'})

            eq_('/hi', m.generate(action='index'))
            eq_(None, m.generate(action='fox5'))
            eq_(None, m.generate(action='something_is_up'))
            eq_(None, m.generate(action='list people'))
            eq_('/hi/abunchofcharacter', m.generate(action='abunchofcharacter'))
            eq_('/hi', m.generate())

    def test_path(self):
        for path in ['hi/*file', 'hi/*(file)']:
            m = Mapper()
            m.minimization = True
            m.connect(path)

            eq_('/hi', m.generate(file=None))
            eq_('/hi/books/learning_python.pdf', m.generate(file='books/learning_python.pdf'))
            eq_('/hi/books/development%26whatever/learning_python.pdf',
                m.generate(file='books/development&whatever/learning_python.pdf'))

    def test_path_backwards(self):
        for path in ['*file/hi', '*(file)/hi']:
            m = Mapper()
            m.minimization = True
            m.connect(path)

            eq_('/hi', m.generate(file=None))
            eq_('/books/learning_python.pdf/hi', m.generate(file='books/learning_python.pdf'))
            eq_('/books/development%26whatever/learning_python.pdf/hi',
                m.generate(file='books/development&whatever/learning_python.pdf'))

    def test_controller(self):
        for path in ['hi/:controller', 'hi/:(controller)']:
            m = Mapper()
            m.connect(path)

            eq_('/hi/content', m.generate(controller='content'))
            eq_('/hi/admin/user', m.generate(controller='admin/user'))

    def test_controller_with_static(self):
        for path in ['hi/:controller', 'hi/:(controller)']:
            m = Mapper()
            m.connect(path)
            m.connect('google', 'http://www.google.com', _static=True)

            eq_('/hi/content', m.generate(controller='content'))
            eq_('/hi/admin/user', m.generate(controller='admin/user'))
            eq_('http://www.google.com', url_for('google'))

    def test_standard_route(self):
        for path in [':controller/:action/:id', ':(controller)/:(action)/:(id)']:
            m = Mapper(explicit=False)
            m.minimization = True
            m.connect(path)

            eq_('/content', m.generate(controller='content', action='index'))
            eq_('/content/list', m.generate(controller='content', action='list'))
            eq_('/content/show/10', m.generate(controller='content', action='show', id ='10'))

            eq_('/admin/user', m.generate(controller='admin/user', action='index'))
            eq_('/admin/user/list', m.generate(controller='admin/user', action='list'))
            eq_('/admin/user/show/10', m.generate(controller='admin/user', action='show', id='10'))

    def test_multiroute(self):
        m = Mapper(explicit=False)
        m.minimization = True
        m.connect('archive/:year/:month/:day', controller='blog', action='view', month=None, day=None,
                            requirements={'month':'\d{1,2}','day':'\d{1,2}'})
        m.connect('viewpost/:id', controller='post', action='view')
        m.connect(':controller/:action/:id')

        url = m.generate(controller='blog', action='view', year=2004, month='blah')
        assert url == '/blog/view?year=2004&month=blah' or url == '/blog/view?month=blah&year=2004'
        eq_('/archive/2004/11', m.generate(controller='blog', action='view', year=2004, month=11))
        eq_('/archive/2004/11', m.generate(controller='blog', action='view', year=2004, month='11'))
        eq_('/archive/2004', m.generate(controller='blog', action='view', year=2004))
        eq_('/viewpost/3', m.generate(controller='post', action='view', id=3))

    def test_multiroute_with_splits(self):
        m = Mapper(explicit=False)
        m.minimization = True
        m.connect('archive/:(year)/:(month)/:(day)', controller='blog', action='view', month=None, day=None,
                            requirements={'month':'\d{1,2}','day':'\d{1,2}'})
        m.connect('viewpost/:(id)', controller='post', action='view')
        m.connect(':(controller)/:(action)/:(id)')

        url = m.generate(controller='blog', action='view', year=2004, month='blah')
        assert url == '/blog/view?year=2004&month=blah' or url == '/blog/view?month=blah&year=2004'
        eq_('/archive/2004/11', m.generate(controller='blog', action='view', year=2004, month=11))
        eq_('/archive/2004/11', m.generate(controller='blog', action='view', year=2004, month='11'))
        eq_('/archive/2004', m.generate(controller='blog', action='view', year=2004))
        eq_('/viewpost/3', m.generate(controller='post', action='view', id=3))

    def test_big_multiroute(self):
        m = Mapper(explicit=False)
        m.minimization = True
        m.connect('', controller='articles', action='index')
        m.connect('admin', controller='admin/general', action='index')

        m.connect('admin/comments/article/:article_id/:action/:id', controller = 'admin/comments', action=None, id=None)
        m.connect('admin/trackback/article/:article_id/:action/:id', controller='admin/trackback', action=None, id=None)
        m.connect('admin/content/:action/:id', controller='admin/content')

        m.connect('xml/:action/feed.xml', controller='xml')
        m.connect('xml/articlerss/:id/feed.xml', controller='xml', action='articlerss')
        m.connect('index.rdf', controller='xml', action='rss')

        m.connect('articles', controller='articles', action='index')
        m.connect('articles/page/:page', controller='articles', action='index', requirements = {'page':'\d+'})

        m.connect('articles/:year/:month/:day/page/:page', controller='articles', action='find_by_date', month = None, day = None,
                            requirements = {'year':'\d{4}', 'month':'\d{1,2}','day':'\d{1,2}'})
        m.connect('articles/category/:id', controller='articles', action='category')
        m.connect('pages/*name', controller='articles', action='view_page')


        eq_('/pages/the/idiot/has/spoken',
            m.generate(controller='articles', action='view_page', name='the/idiot/has/spoken'))
        eq_('/', m.generate(controller='articles', action='index'))
        eq_('/xml/articlerss/4/feed.xml', m.generate(controller='xml', action='articlerss', id=4))
        eq_('/xml/rss/feed.xml', m.generate(controller='xml', action='rss'))
        eq_('/admin/comments/article/4/view/2',
            m.generate(controller='admin/comments', action='view', article_id=4, id=2))
        eq_('/admin', m.generate(controller='admin/general'))
        eq_('/admin/comments/article/4/index', m.generate(controller='admin/comments', article_id=4))
        eq_('/admin/comments/article/4',
            m.generate(controller='admin/comments', action=None, article_id=4))
        eq_('/articles/2004/2/20/page/1',
            m.generate(controller='articles', action='find_by_date', year=2004, month=2, day=20, page=1))
        eq_('/articles/category', m.generate(controller='articles', action='category'))
        eq_('/xml/index/feed.xml', m.generate(controller='xml'))
        eq_('/xml/articlerss/feed.xml', m.generate(controller='xml', action='articlerss'))

        eq_(None, m.generate(controller='admin/comments', id=2))
        eq_(None, m.generate(controller='articles', action='find_by_date', year=2004))

    def test_big_multiroute_with_splits(self):
        m = Mapper(explicit=False)
        m.minimization = True
        m.connect('', controller='articles', action='index')
        m.connect('admin', controller='admin/general', action='index')

        m.connect('admin/comments/article/:(article_id)/:(action)/:(id).html', controller = 'admin/comments', action=None, id=None)
        m.connect('admin/trackback/article/:(article_id)/:action/:(id).html', controller='admin/trackback', action=None, id=None)
        m.connect('admin/content/:(action)/:(id)', controller='admin/content')

        m.connect('xml/:(action)/feed.xml', controller='xml')
        m.connect('xml/articlerss/:(id)/feed.xml', controller='xml', action='articlerss')
        m.connect('index.rdf', controller='xml', action='rss')

        m.connect('articles', controller='articles', action='index')
        m.connect('articles/page/:(page).myt', controller='articles', action='index', requirements = {'page':'\d+'})

        m.connect('articles/:(year)/:month/:(day)/page/:page', controller='articles', action='find_by_date', month = None, day = None,
                            requirements = {'year':'\d{4}', 'month':'\d{1,2}','day':'\d{1,2}'})
        m.connect('articles/category/:id', controller='articles', action='category')
        m.connect('pages/*name', controller='articles', action='view_page')


        eq_('/pages/the/idiot/has/spoken',
            m.generate(controller='articles', action='view_page', name='the/idiot/has/spoken'))
        eq_('/', m.generate(controller='articles', action='index'))
        eq_('/xml/articlerss/4/feed.xml', m.generate(controller='xml', action='articlerss', id=4))
        eq_('/xml/rss/feed.xml', m.generate(controller='xml', action='rss'))
        eq_('/admin/comments/article/4/view/2.html',
            m.generate(controller='admin/comments', action='view', article_id=4, id=2))
        eq_('/admin', m.generate(controller='admin/general'))
        eq_('/admin/comments/article/4/edit/3.html',
            m.generate(controller='admin/comments', article_id=4, action='edit', id=3))
        eq_(None, m.generate(controller='admin/comments', action=None, article_id=4))
        eq_('/articles/2004/2/20/page/1',
            m.generate(controller='articles', action='find_by_date', year=2004, month=2, day=20, page=1))
        eq_('/articles/category', m.generate(controller='articles', action='category'))
        eq_('/xml/index/feed.xml', m.generate(controller='xml'))
        eq_('/xml/articlerss/feed.xml', m.generate(controller='xml', action='articlerss'))

        eq_(None, m.generate(controller='admin/comments', id=2))
        eq_(None, m.generate(controller='articles', action='find_by_date', year=2004))

    def test_big_multiroute_with_nomin(self):
        m = Mapper(explicit=False)
        m.minimization = False
        m.connect('', controller='articles', action='index')
        m.connect('admin', controller='admin/general', action='index')

        m.connect('admin/comments/article/:article_id/:action/:id', controller = 'admin/comments', action=None, id=None)
        m.connect('admin/trackback/article/:article_id/:action/:id', controller='admin/trackback', action=None, id=None)
        m.connect('admin/content/:action/:id', controller='admin/content')

        m.connect('xml/:action/feed.xml', controller='xml')
        m.connect('xml/articlerss/:id/feed.xml', controller='xml', action='articlerss')
        m.connect('index.rdf', controller='xml', action='rss')

        m.connect('articles', controller='articles', action='index')
        m.connect('articles/page/:page', controller='articles', action='index', requirements = {'page':'\d+'})

        m.connect('articles/:year/:month/:day/page/:page', controller='articles', action='find_by_date', month = None, day = None,
                            requirements = {'year':'\d{4}', 'month':'\d{1,2}','day':'\d{1,2}'})
        m.connect('articles/category/:id', controller='articles', action='category')
        m.connect('pages/*name', controller='articles', action='view_page')


        eq_('/pages/the/idiot/has/spoken',
            m.generate(controller='articles', action='view_page', name='the/idiot/has/spoken'))
        eq_('/', m.generate(controller='articles', action='index'))
        eq_('/xml/articlerss/4/feed.xml', m.generate(controller='xml', action='articlerss', id=4))
        eq_('/xml/rss/feed.xml', m.generate(controller='xml', action='rss'))
        eq_('/admin/comments/article/4/view/2',
            m.generate(controller='admin/comments', action='view', article_id=4, id=2))
        eq_('/admin', m.generate(controller='admin/general'))
        eq_('/articles/2004/2/20/page/1',
            m.generate(controller='articles', action='find_by_date', year=2004, month=2, day=20, page=1))
        eq_(None, m.generate(controller='articles', action='category'))
        eq_('/articles/category/4', m.generate(controller='articles', action='category', id=4))
        eq_('/xml/index/feed.xml', m.generate(controller='xml'))
        eq_('/xml/articlerss/feed.xml', m.generate(controller='xml', action='articlerss'))

        eq_(None, m.generate(controller='admin/comments', id=2))
        eq_(None, m.generate(controller='articles', action='find_by_date', year=2004))

    def test_no_extras(self):
        m = Mapper()
        m.minimization = True
        m.connect(':controller/:action/:id')
        m.connect('archive/:year/:month/:day', controller='blog', action='view', month=None, day=None)

        eq_('/archive/2004', m.generate(controller='blog', action='view', year=2004))

    def test_no_extras_with_splits(self):
        m = Mapper()
        m.minimization = True
        m.connect(':(controller)/:(action)/:(id)')
        m.connect('archive/:(year)/:(month)/:(day)', controller='blog', action='view', month=None, day=None)

        eq_('/archive/2004', m.generate(controller='blog', action='view', year=2004))

    def test_the_smallest_route(self):
        for path in ['pages/:title', 'pages/:(title)']:
            m = Mapper()
            m.connect('', controller='page', action='view', title='HomePage')
            m.connect(path, controller='page', action='view')

            eq_('/', m.generate(controller='page', action='view', title='HomePage'))
            eq_('/pages/joe', m.generate(controller='page', action='view', title='joe'))

    def test_extras(self):
        m = Mapper(explicit=False)
        m.minimization = True
        m.connect('viewpost/:id', controller='post', action='view')
        m.connect(':controller/:action/:id')

        eq_('/viewpost/2?extra=x%2Fy', m.generate(controller='post', action='view', id=2, extra='x/y'))
        eq_('/blog?extra=3', m.generate(controller='blog', action='index', extra=3))
        eq_('/viewpost/2?extra=3', m.generate(controller='post', action='view', id=2, extra=3))

    def test_extras_with_splits(self):
        m = Mapper(explicit=False)
        m.minimization = True
        m.connect('viewpost/:(id)', controller='post', action='view')
        m.connect(':(controller)/:(action)/:(id)')

        eq_('/blog?extra=3', m.generate(controller='blog', action='index', extra=3))
        eq_('/viewpost/2?extra=3', m.generate(controller='post', action='view', id=2, extra=3))

    def test_extras_as_unicode(self):
        m = Mapper()
        m.connect(':something')
        thing = "whatever"
        euro = u"\u20ac" # Euro symbol

        eq_("/%s?extra=%%E2%%82%%AC" % thing, m.generate(something=thing, extra=euro))

    def test_extras_as_list_of_unicodes(self):
        m = Mapper()
        m.connect(':something')
        thing = "whatever"
        euro = [u"\u20ac", u"\xa3"] # Euro and Pound sterling symbols

        eq_("/%s?extra=%%E2%%82%%AC&extra=%%C2%%A3" % thing, m.generate(something=thing, extra=euro))


    def test_static(self):
        m = Mapper()
        m.connect('hello/world',known='known_value',controller='content',action='index')

        eq_('/hello/world', m.generate(controller='content',action= 'index',known ='known_value'))
        eq_('/hello/world?extra=hi',
            m.generate(controller='content',action='index',known='known_value',extra='hi'))

        eq_(None, m.generate(known='foo'))

    def test_typical(self):
        for path in [':controller/:action/:id', ':(controller)/:(action)/:(id)']:
            m = Mapper()
            m.minimization = True
            m.minimization = True
            m.connect(path, action = 'index', id = None)

            eq_('/content', m.generate(controller='content', action='index'))
            eq_('/content/list', m.generate(controller='content', action='list'))
            eq_('/content/show/10', m.generate(controller='content', action='show', id=10))

            eq_('/admin/user', m.generate(controller='admin/user', action='index'))
            eq_('/admin/user', m.generate(controller='admin/user'))
            eq_('/admin/user/show/10', m.generate(controller='admin/user', action='show', id=10))

            eq_('/content', m.generate(controller='content'))

    def test_route_with_fixnum_default(self):
        m = Mapper(explicit=False)
        m.minimization = True
        m.connect('page/:id', controller='content', action='show_page', id=1)
        m.connect(':controller/:action/:id')

        eq_('/page', m.generate(controller='content', action='show_page'))
        eq_('/page', m.generate(controller='content', action='show_page', id=1))
        eq_('/page', m.generate(controller='content', action='show_page', id='1'))
        eq_('/page/10', m.generate(controller='content', action='show_page', id=10))

        eq_('/blog/show/4', m.generate(controller='blog', action='show', id=4))
        eq_('/page', m.generate(controller='content', action='show_page'))
        eq_('/page/4', m.generate(controller='content', action='show_page',id=4))
        eq_('/content/show', m.generate(controller='content', action='show'))

    def test_route_with_fixnum_default_with_splits(self):
        m = Mapper(explicit=False)
        m.minimization = True
        m.connect('page/:(id)', controller='content', action='show_page', id =1)
        m.connect(':(controller)/:(action)/:(id)')

        eq_('/page', m.generate(controller='content', action='show_page'))
        eq_('/page', m.generate(controller='content', action='show_page', id=1))
        eq_('/page', m.generate(controller='content', action='show_page', id='1'))
        eq_('/page/10', m.generate(controller='content', action='show_page', id=10))

        eq_('/blog/show/4', m.generate(controller='blog', action='show', id=4))
        eq_('/page', m.generate(controller='content', action='show_page'))
        eq_('/page/4', m.generate(controller='content', action='show_page',id=4))
        eq_('/content/show', m.generate(controller='content', action='show'))

    def test_uppercase_recognition(self):
        for path in [':controller/:action/:id', ':(controller)/:(action)/:(id)']:
            m = Mapper(explicit=False)
            m.minimization = True
            m.connect(path)

            eq_('/Content', m.generate(controller='Content', action='index'))
            eq_('/Content/list', m.generate(controller='Content', action='list'))
            eq_('/Content/show/10', m.generate(controller='Content', action='show', id='10'))

            eq_('/Admin/NewsFeed', m.generate(controller='Admin/NewsFeed', action='index'))

    def test_backwards(self):
        m = Mapper(explicit=False)
        m.minimization = True
        m.connect('page/:id/:action', controller='pages', action='show')
        m.connect(':controller/:action/:id')

        eq_('/page/20', m.generate(controller='pages', action='show', id=20))
        eq_('/pages/boo', m.generate(controller='pages', action='boo'))

    def test_backwards_with_splits(self):
        m = Mapper(explicit=False)
        m.minimization = True
        m.connect('page/:(id)/:(action)', controller='pages', action='show')
        m.connect(':(controller)/:(action)/:(id)')

        eq_('/page/20', m.generate(controller='pages', action='show', id=20))
        eq_('/pages/boo', m.generate(controller='pages', action='boo'))

    def test_both_requirement_and_optional(self):
        m = Mapper()
        m.minimization = True
        m.connect('test/:year', controller='post', action='show', year=None, requirements = {'year':'\d{4}'})

        eq_('/test', m.generate(controller='post', action='show'))
        eq_('/test', m.generate(controller='post', action='show', year=None))

    def test_set_to_nil_forgets(self):
        m = Mapper()
        m.minimization = True
        m.connect('pages/:year/:month/:day', controller='content', action='list_pages', month=None, day=None)
        m.connect(':controller/:action/:id')

        eq_('/pages/2005', m.generate(controller='content', action='list_pages', year=2005))
        eq_('/pages/2005/6', m.generate(controller='content', action='list_pages', year=2005, month=6))
        eq_('/pages/2005/6/12',
            m.generate(controller='content', action='list_pages', year=2005, month=6, day=12))

    def test_url_with_no_action_specified(self):
        m = Mapper()
        m.connect('', controller='content')
        m.connect(':controller/:action/:id')

        eq_('/', m.generate(controller='content', action='index'))
        eq_('/', m.generate(controller='content'))

    def test_url_with_prefix(self):
        m = Mapper(explicit=False)
        m.minimization = True
        m.prefix = '/blog'
        m.connect(':controller/:action/:id')
        m.create_regs(['content','blog','admin/comments'])

        eq_('/blog/content/view', m.generate(controller='content', action='view'))
        eq_('/blog/content', m.generate(controller='content'))
        eq_('/blog/admin/comments', m.generate(controller='admin/comments'))

    def test_url_with_prefix_deeper(self):
        m = Mapper(explicit=False)
        m.minimization = True
        m.prefix = '/blog/phil'
        m.connect(':controller/:action/:id')
        m.create_regs(['content','blog','admin/comments'])

        eq_('/blog/phil/content/view', m.generate(controller='content', action='view'))
        eq_('/blog/phil/content', m.generate(controller='content'))
        eq_('/blog/phil/admin/comments', m.generate(controller='admin/comments'))

    def test_url_with_environ_empty(self):
        m = Mapper(explicit=False)
        m.minimization = True
        m.environ = dict(SCRIPT_NAME='')
        m.connect(':controller/:action/:id')
        m.create_regs(['content','blog','admin/comments'])

        eq_('/content/view', m.generate(controller='content', action='view'))
        eq_('/content', m.generate(controller='content'))
        eq_('/admin/comments', m.generate(controller='admin/comments'))

    def test_url_with_environ(self):
        m = Mapper(explicit=False)
        m.minimization = True
        m.environ = dict(SCRIPT_NAME='/blog')
        m.connect(':controller/:action/:id')
        m.create_regs(['content','blog','admin/comments'])

        eq_('/blog/content/view', m.generate(controller='content', action='view'))
        eq_('/blog/content', m.generate(controller='content'))
        eq_('/blog/content', m.generate(controller='content'))
        eq_('/blog/admin/comments', m.generate(controller='admin/comments'))

        m.environ = dict(SCRIPT_NAME='/notblog')

        eq_('/notblog/content/view', m.generate(controller='content', action='view'))
        eq_('/notblog/content', m.generate(controller='content'))
        eq_('/notblog/content', m.generate(controller='content'))
        eq_('/notblog/admin/comments', m.generate(controller='admin/comments'))


    def test_url_with_environ_and_absolute(self):
        m = Mapper(explicit=False)
        m.minimization = True
        m.environ = dict(SCRIPT_NAME='/blog')
        m.connect('image', 'image/:name', _absolute=True)
        m.connect(':controller/:action/:id')
        m.create_regs(['content','blog','admin/comments'])

        eq_('/blog/content/view', m.generate(controller='content', action='view'))
        eq_('/blog/content', m.generate(controller='content'))
        eq_('/blog/content', m.generate(controller='content'))
        eq_('/blog/admin/comments', m.generate(controller='admin/comments'))
        eq_('/image/topnav.jpg', url_for('image', name='topnav.jpg'))

    def test_route_with_odd_leftovers(self):
        m = Mapper(explicit=False)
        m.minimization = True
        m.connect(':controller/:(action)-:(id)')
        m.create_regs(['content','blog','admin/comments'])

        eq_('/content/view-', m.generate(controller='content', action='view'))
        eq_('/content/index-', m.generate(controller='content'))

    def test_route_with_end_extension(self):
        m = Mapper(explicit=False)
        m.connect(':controller/:(action)-:(id).html')
        m.create_regs(['content','blog','admin/comments'])

        eq_(None, m.generate(controller='content', action='view'))
        eq_(None, m.generate(controller='content'))

        eq_('/content/view-3.html', m.generate(controller='content', action='view', id=3))
        eq_('/content/index-2.html', m.generate(controller='content', id=2))

    def test_unicode(self):
        hoge = u'\u30c6\u30b9\u30c8' # the word test in Japanese
        hoge_enc = urllib.quote(hoge.encode('utf-8'))
        m = Mapper()
        m.connect(':hoge')
        eq_("/%s" % hoge_enc, m.generate(hoge=hoge))
        self.assert_(isinstance(m.generate(hoge=hoge), str))

    def test_unicode_static(self):
        hoge = u'\u30c6\u30b9\u30c8' # the word test in Japanese
        hoge_enc = urllib.quote(hoge.encode('utf-8'))
        m = Mapper()
        m.minimization = True
        m.connect('google-jp', 'http://www.google.co.jp/search', _static=True)
        m.create_regs(['messages'])
        eq_("http://www.google.co.jp/search?q=" + hoge_enc, url_for('google-jp', q=hoge))
        self.assert_(isinstance(url_for('google-jp', q=hoge), str))

    def test_other_special_chars(self):
        m = Mapper()
        m.minimization = True
        m.connect('/:year/:(slug).:(format),:(locale)', locale='en', format='html')
        m.create_regs(['content'])

        eq_('/2007/test', m.generate(year=2007, slug='test'))
        eq_('/2007/test.xml', m.generate(year=2007, slug='test', format='xml'))
        eq_('/2007/test.xml,ja', m.generate(year=2007, slug='test', format='xml', locale='ja'))
        eq_(None, m.generate(year=2007, format='html'))

    def test_dot_format_args(self):
        for minimization in [False, True]:
            m = Mapper(explicit=True)
            m.minimization=minimization
            m.connect('/songs/{title}{.format}')
            m.connect('/stories/{slug}{.format:pdf}')

            eq_('/songs/my-way', m.generate(title='my-way'))
            eq_('/songs/my-way.mp3', m.generate(title='my-way', format='mp3'))
            eq_('/stories/frist-post', m.generate(slug='frist-post'))
            eq_('/stories/frist-post.pdf', m.generate(slug='frist-post', format='pdf'))
            eq_(None, m.generate(slug='frist-post', format='doc'))

if __name__ == '__main__':
    unittest.main()
else:
    def bench_gen(withcache = False):
        m = Mapper()
        m.connect('', controller='articles', action='index')
        m.connect('admin', controller='admin/general', action='index')

        m.connect('admin/comments/article/:article_id/:action/:id', controller = 'admin/comments', action = None, id=None)
        m.connect('admin/trackback/article/:article_id/:action/:id', controller='admin/trackback', action=None, id=None)
        m.connect('admin/content/:action/:id', controller='admin/content')

        m.connect('xml/:action/feed.xml', controller='xml')
        m.connect('xml/articlerss/:id/feed.xml', controller='xml', action='articlerss')
        m.connect('index.rdf', controller='xml', action='rss')

        m.connect('articles', controller='articles', action='index')
        m.connect('articles/page/:page', controller='articles', action='index', requirements = {'page':'\d+'})

        m.connect('articles/:year/:month/:day/page/:page', controller='articles', action='find_by_date', month = None, day = None,
                            requirements = {'year':'\d{4}', 'month':'\d{1,2}','day':'\d{1,2}'})
        m.connect('articles/category/:id', controller='articles', action='category')
        m.connect('pages/*name', controller='articles', action='view_page')
        if withcache:
            m.urlcache = {}
        m._create_gens()
        n = 5000
        start = time.time()
        for x in range(1,n):
            m.generate(controller='articles', action='index', page=4)
            m.generate(controller='admin/general', action='index')
            m.generate(controller='admin/comments', action='show', article_id=2)

            m.generate(controller='articles', action='find_by_date', year=2004, page=1)
            m.generate(controller='articles', action='category', id=4)
            m.generate(controller='xml', action='articlerss', id=2)
        end = time.time()
        ts = time.time()
        for x in range(1,n*6):
            pass
        en = time.time()
        total = end-start-(en-ts)
        per_url = total / (n*6)
        print "Generation (%s URLs)" % (n*6)
        print "%s ms/url" % (per_url*1000)
        print "%s urls/s\n" % (1.00/per_url)

########NEW FILE########
__FILENAME__ = test_middleware
from routes import Mapper
from routes.middleware import RoutesMiddleware
from webtest import TestApp
from nose.tools import eq_

def simple_app(environ, start_response):
    route_dict = environ['wsgiorg.routing_args'][1]
    start_response('200 OK', [('Content-type', 'text/plain')])
    items = route_dict.items()
    items.sort()
    return [('The matchdict items are %s and environ is %s' % (items, environ)).encode()]

def test_basic():
    map = Mapper(explicit=False)
    map.minimization = True
    map.connect(':controller/:action/:id')
    map.create_regs(['content'])
    app = TestApp(RoutesMiddleware(simple_app, map))
    res = app.get('/')
    assert b'matchdict items are []' in res
    
    res = app.get('/content')
    assert b"matchdict items are [('action', 'index'), ('controller', " + repr(
        u'content').encode() + b"), ('id', None)]" in res

def test_no_query():
    map = Mapper(explicit=False)
    map.minimization = True
    map.connect('myapp/*path_info', controller='myapp')
    map.connect('project/*path_info', controller='myapp')
    map.create_regs(['content', 'myapp'])
    
    app = RoutesMiddleware(simple_app, map)
    env = {'PATH_INFO': '/', 'REQUEST_METHOD': 'GET', 'HTTP_HOST': 'localhost'}
    def start_response_wrapper(status, headers, exc=None):
        pass
    response = b''.join(app(env, start_response_wrapper))
    assert b'matchdict items are []' in response

def test_content_split():
    map = Mapper(explicit=False)
    map.minimization = True
    map.connect('myapp/*path_info', controller='myapp')
    map.connect('project/*path_info', controller='myapp')
    map.create_regs(['content', 'myapp'])
    
    app = RoutesMiddleware(simple_app, map)
    env = {'PATH_INFO': '/', 'REQUEST_METHOD': 'POST', 'CONTENT_TYPE': 'text/plain;text/html',
           'HTTP_HOST': 'localhost'}
    def start_response_wrapper(status, headers, exc=None):
        pass
    response = b''.join(app(env, start_response_wrapper))
    assert b'matchdict items are []' in response

def test_no_singleton():
    map = Mapper(explicit=False)
    map.minimization = True
    map.connect('myapp/*path_info', controller='myapp')
    map.connect('project/*path_info', controller='myapp')
    map.create_regs(['content', 'myapp'])
    
    app = RoutesMiddleware(simple_app, map, singleton=False)
    env = {'PATH_INFO': '/', 'REQUEST_METHOD': 'POST', 'CONTENT_TYPE': 'text/plain;text/html'}
    def start_response_wrapper(status, headers, exc=None):
        pass
    response = b''.join(app(env, start_response_wrapper))
    assert b'matchdict items are []' in response
    
    # Now a match
    env = {'PATH_INFO': '/project/fred', 'REQUEST_METHOD': 'POST', 'CONTENT_TYPE': 'text/plain;text/html'}
    def start_response_wrapper(status, headers, exc=None):
        pass
    response = b''.join(app(env, start_response_wrapper))
    assert b"matchdict items are [('action', " + repr(u'index').encode() + \
           b"), ('controller', " + repr(u'myapp').encode() + b"), ('path_info', 'fred')]" in response
    

def test_path_info():
    map = Mapper(explicit=False)
    map.minimization = True
    map.connect('myapp/*path_info', controller='myapp')
    map.connect('project/*path_info', controller='myapp')
    map.create_regs(['content', 'myapp'])
    
    app = TestApp(RoutesMiddleware(simple_app, map))
    res = app.get('/')
    assert 'matchdict items are []' in res
    
    res = app.get('/myapp/some/other/url')
    print res
    assert b"matchdict items are [('action', " + repr(u'index').encode() + \
           b"), ('controller', " + repr(u'myapp').encode() + b"), ('path_info', 'some/other/url')]" in res
    assert "'SCRIPT_NAME': '/myapp'" in res
    assert "'PATH_INFO': '/some/other/url'" in res
    
    res = app.get('/project/pylonshq/browser/pylons/templates/default_project/+package+/pylonshq/browser/pylons/templates/default_project/+package+/controllers')
    print res
    assert "'SCRIPT_NAME': '/project'" in res
    assert "'PATH_INFO': '/pylonshq/browser/pylons/templates/default_project/+package+/pylonshq/browser/pylons/templates/default_project/+package+/controllers'" in res    

def test_redirect_middleware():
    map = Mapper(explicit=False)
    map.minimization = True
    map.connect('myapp/*path_info', controller='myapp')
    map.redirect("faq/{section}", "/static/faq/{section}.html")
    map.redirect("home/index", "/", _redirect_code='301 Moved Permanently')
    map.create_regs(['content', 'myapp'])
    
    app = TestApp(RoutesMiddleware(simple_app, map))
    res = app.get('/')
    assert 'matchdict items are []' in res
    
    res = app.get('/faq/home')
    eq_('302 Found', res.status)
    eq_(res.headers['Location'], '/static/faq/home.html')
    
    res = app.get('/myapp/some/other/url')
    print res
    assert b"matchdict items are [('action', " + repr(u'index').encode() + \
           b"), ('controller', " + repr(u'myapp').encode() + \
           b"), ('path_info', 'some/other/url')]" in res
    assert "'SCRIPT_NAME': '/myapp'" in res
    assert "'PATH_INFO': '/some/other/url'" in res
    
    res = app.get('/home/index')
    assert '301 Moved Permanently' in res.status
    eq_(res.headers['Location'], '/')

def test_method_conversion():
    map = Mapper(explicit=False)
    map.minimization = True
    map.connect('content/:type', conditions=dict(method='DELETE'))
    map.connect(':controller/:action/:id')
    map.create_regs(['content'])
    app = TestApp(RoutesMiddleware(simple_app, map))
    res = app.get('/')
    assert 'matchdict items are []' in res
    
    res = app.get('/content')
    assert b"matchdict items are [('action', 'index'), ('controller', " + \
           repr(u'content').encode() + b"), ('id', None)]" in res
    
    res = app.get('/content/hopper', params={'_method':'DELETE'})
    assert b"matchdict items are [('action', " + repr(u'index').encode() + \
           b"), ('controller', " + repr(u'content').encode() + \
           b"), ('type', " + repr(u'hopper').encode() + b")]" in res
    
    res = app.post('/content/grind', 
                   params={'_method':'DELETE', 'name':'smoth'},
                   headers={'Content-Type': 'application/x-www-form-urlencoded'})
    assert b"matchdict items are [('action', " + repr(u'index').encode() + \
           b"), ('controller', " + repr(u'content').encode() + \
           b"), ('type', " + repr(u'grind').encode() + b")]" in res
    assert "'REQUEST_METHOD': 'POST'" in res

    #res = app.post('/content/grind',
    #               upload_files=[('fileupload', 'hello.txt', 'Hello World')],
    #               params={'_method':'DELETE', 'name':'smoth'})
    #assert "matchdict items are [('action', u'index'), ('controller', u'content'), ('type', u'grind')]" in res
    #assert "'REQUEST_METHOD': 'POST'" in res

########NEW FILE########
__FILENAME__ = test_nonminimization
"""Test non-minimization recognition"""
import urllib

from nose.tools import eq_

from routes import url_for
from routes.mapper import Mapper


def test_basic():
    m = Mapper(explicit=False)
    m.minimization = False
    m.connect('/:controller/:action/:id')
    m.create_regs(['content'])
    
    # Recognize
    eq_(None, m.match('/content'))
    eq_(None, m.match('/content/index'))
    eq_(None, m.match('/content/index/'))
    eq_({'controller':'content','action':'index','id':'4'}, 
        m.match('/content/index/4'))
    eq_({'controller':'content','action':'view','id':'4.html'},
        m.match('/content/view/4.html'))
    
    # Generate
    eq_(None, m.generate(controller='content'))
    eq_('/content/index/4', m.generate(controller='content', id=4))
    eq_('/content/view/3', m.generate(controller='content', action='view', id=3))

def test_full():
    m = Mapper(explicit=False)
    m.minimization = False
    m.connect('/:controller/:action/', id=None)
    m.connect('/:controller/:action/:id')
    m.create_regs(['content'])
    
    # Recognize
    eq_(None, m.match('/content'))
    eq_(None, m.match('/content/index'))
    eq_({'controller':'content','action':'index','id':None}, 
        m.match('/content/index/'))
    eq_({'controller':'content','action':'index','id':'4'}, 
        m.match('/content/index/4'))
    eq_({'controller':'content','action':'view','id':'4.html'},
        m.match('/content/view/4.html'))
    
    # Generate
    eq_(None, m.generate(controller='content'))
    
    # Looks odd, but only controller/action are set with non-explicit, so we
    # do need the id to match
    eq_('/content/index/', m.generate(controller='content', id=None))
    eq_('/content/index/4', m.generate(controller='content', id=4))
    eq_('/content/view/3', m.generate(controller='content', action='view', id=3))

def test_action_required():
    m = Mapper()
    m.minimization = False
    m.explicit = True
    m.connect('/:controller/index', action='index')
    m.create_regs(['content'])
    
    eq_(None, m.generate(controller='content'))
    eq_(None, m.generate(controller='content', action='fred'))
    eq_('/content/index', m.generate(controller='content', action='index'))

def test_query_params():
    m = Mapper()
    m.minimization = False
    m.explicit = True
    m.connect('/:controller/index', action='index')
    m.create_regs(['content'])
    
    eq_(None, m.generate(controller='content'))
    eq_('/content/index?test=sample', 
        m.generate(controller='content', action='index', test='sample'))
    

def test_syntax():
    m = Mapper(explicit=False)
    m.minimization = False
    m.connect('/{controller}/{action}/{id}')
    m.create_regs(['content'])
    
    # Recognize
    eq_(None, m.match('/content'))
    eq_(None, m.match('/content/index'))
    eq_(None, m.match('/content/index/'))
    eq_({'controller':'content','action':'index','id':'4'}, 
        m.match('/content/index/4'))
    
    # Generate
    eq_(None, m.generate(controller='content'))
    eq_('/content/index/4', m.generate(controller='content', id=4))
    eq_('/content/view/3', m.generate(controller='content', action='view', id=3))

def test_regexp_syntax():
    m = Mapper(explicit=False)
    m.minimization = False
    m.connect('/{controller}/{action}/{id:\d\d}')
    m.create_regs(['content'])
    
    # Recognize
    eq_(None, m.match('/content'))
    eq_(None, m.match('/content/index'))
    eq_(None, m.match('/content/index/'))
    eq_(None, m.match('/content/index/3'))
    eq_({'controller':'content','action':'index','id':'44'}, 
        m.match('/content/index/44'))
    
    # Generate
    eq_(None, m.generate(controller='content'))
    eq_(None, m.generate(controller='content', id=4))
    eq_('/content/index/43', m.generate(controller='content', id=43))
    eq_('/content/view/31', m.generate(controller='content', action='view', id=31))

def test_unicode():
    hoge = u'\u30c6\u30b9\u30c8' # the word test in Japanese
    hoge_enc = urllib.quote(hoge.encode('utf-8'))
    m = Mapper()
    m.minimization = False
    m.connect(':hoge')
    eq_("/%s" % hoge_enc, m.generate(hoge=hoge))
    assert isinstance(m.generate(hoge=hoge), str)

def test_unicode_static():
    hoge = u'\u30c6\u30b9\u30c8' # the word test in Japanese
    hoge_enc = urllib.quote(hoge.encode('utf-8'))
    m = Mapper()
    m.minimization = False
    m.connect('google-jp', 'http://www.google.co.jp/search', _static=True)
    m.create_regs(['messages'])
    eq_("http://www.google.co.jp/search?q=" + hoge_enc,
                     url_for('google-jp', q=hoge))
    assert isinstance(url_for('google-jp', q=hoge), str)

def test_other_special_chars():
    m = Mapper()
    m.minimization = False
    m.connect('/:year/:(slug).:(format),:(locale)', locale='en', format='html')
    m.create_regs(['content'])
    
    eq_('/2007/test.xml,ja', m.generate(year=2007, slug='test', format='xml', locale='ja'))
    eq_(None, m.generate(year=2007, format='html'))

########NEW FILE########
__FILENAME__ = test_recognition
"""test_recognition"""

import sys
import time
import unittest
import urllib
from nose.tools import eq_, assert_raises
from routes import *
from routes.util import RoutesException

class TestRecognition(unittest.TestCase):
    
    def test_regexp_char_escaping(self):
        m = Mapper(explicit=False)
        m.minimization = True
        m.connect(':controller/:(action).:(id)')
        m.create_regs(['content'])
        
        eq_({'action':'view','controller':'content','id':'2'}, m.match('/content/view.2'))
        
        m.connect(':controller/:action/:id')
        m.create_regs(['content', 'find.all'])
        eq_({'action':'view','controller':'find.all','id':None}, m.match('/find.all/view'))
        eq_(None, m.match('/findzall/view'))
        
    def test_all_static(self):
        m = Mapper(explicit=False)
        m.minimization = True
        m.connect('hello/world/how/are/you', controller='content', action='index')
        m.create_regs([])
        
        eq_(None, m.match('/x'))
        eq_(None, m.match('/hello/world/how'))
        eq_(None, m.match('/hello/world/how/are'))
        eq_(None, m.match('/hello/world/how/are/you/today'))
        eq_({'controller':'content','action':'index'}, m.match('/hello/world/how/are/you'))
    
    def test_unicode(self):
        hoge = u'\u30c6\u30b9\u30c8' # the word test in Japanese
        m = Mapper(explicit=False)
        m.minimization = True
        m.connect(':hoge')
        eq_({'controller': 'content', 'action': 'index', 'hoge': hoge},
                         m.match('/' + hoge))
    
    def test_disabling_unicode(self):
        hoge = u'\u30c6\u30b9\u30c8' # the word test in Japanese
        hoge_enc = urllib.quote(hoge.encode('utf-8'))
        m = Mapper(explicit=False)
        m.minimization = True
        m.encoding = None
        m.connect(':hoge')
        eq_({'controller': 'content', 'action': 'index', 'hoge': hoge_enc},
                         m.match('/' + hoge_enc))
            
    def test_basic_dynamic(self):
        for path in ['hi/:name', 'hi/:(name)']:
            m = Mapper(explicit=False)
            m.minimization = True
            m.connect(path, controller='content')
            m.create_regs([])
        
            eq_(None, m.match('/boo'))
            eq_(None, m.match('/boo/blah'))
            eq_(None, m.match('/hi'))
            eq_(None, m.match('/hi/dude/what'))
            eq_({'controller':'content','name':'dude','action':'index'}, m.match('/hi/dude'))
            eq_({'controller':'content','name':'dude','action':'index'}, m.match('/hi/dude/'))
    
    def test_basic_dynamic_backwards(self):
        for path in [':name/hi', ':(name)/hi']:
            m = Mapper(explicit=False)
            m.minimization = True
            m.connect(path)
            m.create_regs([])

            eq_(None, m.match('/'))
            eq_(None, m.match('/hi'))
            eq_(None, m.match('/boo'))
            eq_(None, m.match('/boo/blah'))
            eq_(None, m.match('/shop/wallmart/hi'))
            eq_({'name':'fred', 'action':'index', 'controller':'content'}, m.match('/fred/hi'))
            eq_({'name':'index', 'action':'index', 'controller':'content'}, m.match('/index/hi'))
    
    def test_dynamic_with_underscores(self):
        m = Mapper(explicit=False)
        m.minimization = True
        m.connect('article/:small_page', small_page=False)
        m.connect(':(controller)/:(action)/:(id)')
        m.create_regs(['article', 'blog'])
        
        eq_({'controller':'blog','action':'view','id':'0'}, m.match('/blog/view/0'))
        eq_({'controller':'blog','action':'view','id':None}, m.match('/blog/view'))
        
    def test_dynamic_with_default(self):
        for path in ['hi/:action', 'hi/:(action)']:
            m = Mapper(explicit=False)
            m.minimization = True
            m.connect(path, controller='content')
            m.create_regs([])
        
            eq_(None, m.match('/boo'))
            eq_(None, m.match('/boo/blah'))
            eq_(None, m.match('/hi/dude/what'))
            eq_({'controller':'content','action':'index'}, m.match('/hi'))
            eq_({'controller':'content','action':'index'}, m.match('/hi/index'))
            eq_({'controller':'content','action':'dude'}, m.match('/hi/dude'))
    
    def test_dynamic_with_default_backwards(self):
        for path in [':action/hi', ':(action)/hi']:
            m = Mapper(explicit=False)
            m.minimization = True
            m.connect(path, controller='content')
            m.create_regs([])

            eq_(None, m.match('/'))
            eq_(None, m.match('/boo'))
            eq_(None, m.match('/boo/blah'))
            eq_(None, m.match('/hi'))
            eq_({'controller':'content','action':'index'}, m.match('/index/hi'))
            eq_({'controller':'content','action':'index'}, m.match('/index/hi/'))
            eq_({'controller':'content','action':'dude'}, m.match('/dude/hi'))
    
    def test_dynamic_with_string_condition(self):
        for path in [':name/hi', ':(name)/hi']:
            m = Mapper(explicit=False)
            m.minimization = True
            m.connect(path, controller='content', requirements={'name':'index'})
            m.create_regs([])
        
            eq_(None, m.match('/boo'))
            eq_(None, m.match('/boo/blah'))
            eq_(None, m.match('/hi'))
            eq_(None, m.match('/dude/what/hi'))
            eq_({'controller':'content','name':'index','action':'index'}, m.match('/index/hi'))
            eq_(None, m.match('/dude/hi'))
    
    def test_dynamic_with_string_condition_backwards(self):
        for path in ['hi/:name', 'hi/:(name)']:
            m = Mapper(explicit=False)
            m.minimization = True
            m.connect(path, controller='content', requirements={'name':'index'})
            m.create_regs([])

            eq_(None, m.match('/boo'))
            eq_(None, m.match('/boo/blah'))
            eq_(None, m.match('/hi'))
            eq_(None, m.match('/hi/dude/what'))
            eq_({'controller':'content','name':'index','action':'index'}, m.match('/hi/index'))
            eq_(None, m.match('/hi/dude'))
    
    def test_dynamic_with_regexp_condition(self):
        for path in ['hi/:name', 'hi/:(name)']:
            m = Mapper(explicit=False)
            m.minimization = True
            m.connect(path, controller='content', requirements={'name':'[a-z]+'})
            m.create_regs([])
        
            eq_(None, m.match('/boo'))
            eq_(None, m.match('/boo/blah'))
            eq_(None, m.match('/hi'))
            eq_(None, m.match('/hi/FOXY'))
            eq_(None, m.match('/hi/138708jkhdf'))
            eq_(None, m.match('/hi/dkjfl8792343dfsf'))
            eq_(None, m.match('/hi/dude/what'))
            eq_(None, m.match('/hi/dude/what/'))
            eq_({'controller':'content','name':'index','action':'index'}, m.match('/hi/index'))
            eq_({'controller':'content','name':'dude','action':'index'}, m.match('/hi/dude'))
    
    def test_dynamic_with_regexp_and_default(self):
        for path in ['hi/:action', 'hi/:(action)']:
            m = Mapper(explicit=False)
            m.minimization = True
            m.connect(path, controller='content', requirements={'action':'[a-z]+'})
            m.create_regs([])
        
            eq_(None, m.match('/boo'))
            eq_(None, m.match('/boo/blah'))
            eq_(None, m.match('/hi/FOXY'))
            eq_(None, m.match('/hi/138708jkhdf'))
            eq_(None, m.match('/hi/dkjfl8792343dfsf'))
            eq_(None, m.match('/hi/dude/what/'))
            eq_({'controller':'content','action':'index'}, m.match('/hi'))
            eq_({'controller':'content','action':'index'}, m.match('/hi/index'))
            eq_({'controller':'content','action':'dude'}, m.match('/hi/dude'))
    
    def test_dynamic_with_default_and_string_condition_backwards(self):
        for path in [':action/hi', ':(action)/hi']:
            m = Mapper(explicit=False)
            m.minimization = True
            m.connect(path)
            m.create_regs([])

            eq_(None, m.match('/'))
            eq_(None, m.match('/boo'))
            eq_(None, m.match('/boo/blah'))
            eq_(None, m.match('/hi'))
            eq_({'action':'index', 'controller':'content'}, m.match('/index/hi'))

    def test_dynamic_and_controller_with_string_and_default_backwards(self):
        for path in [':controller/:action/hi', ':(controller)/:(action)/hi']:
            m = Mapper()
            m.connect(path, controller='content')
            m.create_regs(['content','admin/user'])

            eq_(None, m.match('/'))
            eq_(None, m.match('/fred'))

    
    def test_multiroute(self):
        m = Mapper(explicit=False)
        m.minimization = True
        m.connect('archive/:year/:month/:day', controller='blog', action='view', month=None, day=None,
                                    requirements={'month':'\d{1,2}','day':'\d{1,2}'})
        m.connect('viewpost/:id', controller='post', action='view')
        m.connect(':controller/:action/:id')
        m.create_regs(['post','blog','admin/user'])
        
        eq_(None, m.match('/'))
        eq_(None, m.match('/archive'))
        eq_(None, m.match('/archive/2004/ab'))
        eq_({'controller':'blog','action':'view','id':None}, m.match('/blog/view'))
        eq_({'controller':'blog','action':'view','month':None,'day':None,'year':'2004'}, 
                         m.match('/archive/2004'))
        eq_({'controller':'blog','action':'view', 'month':'4', 'day':None,'year':'2004'}, 
                         m.match('/archive/2004/4'))

    def test_multiroute_with_nomin(self):
        m = Mapper()
        m.minimization = False
        m.connect('/archive/:year/:month/:day', controller='blog', action='view', month=None, day=None,
                                    requirements={'month':'\d{1,2}','day':'\d{1,2}'})
        m.connect('/viewpost/:id', controller='post', action='view')
        m.connect('/:controller/:action/:id')
        m.create_regs(['post','blog','admin/user'])
        
        eq_(None, m.match('/'))
        eq_(None, m.match('/archive'))
        eq_(None, m.match('/archive/2004/ab'))
        eq_(None, m.match('/archive/2004/4'))
        eq_(None, m.match('/archive/2004'))
        eq_({'controller':'blog','action':'view','id':'3'}, m.match('/blog/view/3'))
        eq_({'controller':'blog','action':'view','month':'10','day':'23','year':'2004'}, 
                         m.match('/archive/2004/10/23'))

    def test_multiroute_with_splits(self):
        m = Mapper(explicit=False)
        m.minimization = True
        m.connect('archive/:(year)/:(month)/:(day)', controller='blog', action='view', month=None, day=None,
                                    requirements={'month':'\d{1,2}','day':'\d{1,2}'})
        m.connect('viewpost/:(id)', controller='post', action='view')
        m.connect(':(controller)/:(action)/:(id)')
        m.create_regs(['post','blog','admin/user'])
        
        eq_(None, m.match('/'))
        eq_(None, m.match('/archive'))
        eq_(None, m.match('/archive/2004/ab'))
        eq_({'controller':'blog','action':'view','id':None}, m.match('/blog/view'))
        eq_({'controller':'blog','action':'view','month':None,'day':None,'year':'2004'}, 
                         m.match('/archive/2004'))
        eq_({'controller':'blog','action':'view', 'month':'4', 'day':None,'year':'2004'}, 
                         m.match('/archive/2004/4'))
    
    def test_dynamic_with_regexp_defaults_and_gaps(self):
        m = Mapper()
        m.minimization = True
        m.connect('archive/:year/:month/:day', controller='blog', action='view', month=None, day=None,
                                    requirements={'month':'\d{1,2}'})
        m.connect('view/:id/:controller', controller='blog', id=2, action='view', requirements={'id':'\d{1,2}'})
        m.create_regs(['post','blog','admin/user'])

        eq_(None, m.match('/'))
        eq_(None, m.match('/archive'))
        eq_(None, m.match('/archive/2004/haha'))
        eq_(None, m.match('/view/blog'))
        eq_({'controller':'blog', 'action':'view', 'id':'2'}, m.match('/view'))
        eq_({'controller':'blog','action':'view','month':None,'day':None,'year':'2004'}, m.match('/archive/2004'))

    def test_dynamic_with_regexp_defaults_and_gaps_and_splits(self):
        m = Mapper()
        m.minimization = True
        m.connect('archive/:(year)/:(month)/:(day)', controller='blog', action='view', month=None, day=None,
                                    requirements={'month':'\d{1,2}'})
        m.connect('view/:(id)/:(controller)', controller='blog', id=2, action='view', requirements={'id':'\d{1,2}'})
        m.create_regs(['post','blog','admin/user'])

        eq_(None, m.match('/'))
        eq_(None, m.match('/archive'))
        eq_(None, m.match('/archive/2004/haha'))
        eq_(None, m.match('/view/blog'))
        eq_({'controller':'blog', 'action':'view', 'id':'2'}, m.match('/view'))
        eq_({'controller':'blog','action':'view','month':None,'day':None,'year':'2004'}, m.match('/archive/2004'))

    def test_dynamic_with_regexp_gaps_controllers(self):
        for path in ['view/:id/:controller', 'view/:(id)/:(controller)']:
            m = Mapper()
            m.minimization = True
            m.connect(path, id=2, action='view', requirements={'id':'\d{1,2}'})
            m.create_regs(['post','blog','admin/user'])
        
            eq_(None, m.match('/'))
            eq_(None, m.match('/view'))
            eq_(None, m.match('/view/blog'))
            eq_(None, m.match('/view/3'))
            eq_(None, m.match('/view/4/honker'))
            eq_({'controller':'blog','action':'view','id':'2'}, m.match('/view/2/blog'))
    
    def test_dynamic_with_trailing_strings(self):
        for path in ['view/:id/:controller/super', 'view/:(id)/:(controller)/super']:
            m = Mapper()
            m.minimization = True
            m.connect(path, controller='blog', id=2, action='view', requirements={'id':'\d{1,2}'})
            m.create_regs(['post','blog','admin/user'])
        
            eq_(None, m.match('/'))
            eq_(None, m.match('/view'))
            eq_(None, m.match('/view/blah/blog/super'))
            eq_(None, m.match('/view/ha/super'))
            eq_(None, m.match('/view/super'))
            eq_(None, m.match('/view/4/super'))
            eq_({'controller':'blog','action':'view','id':'2'}, m.match('/view/2/blog/super'))
            eq_({'controller':'admin/user','action':'view','id':'4'}, m.match('/view/4/admin/user/super'))
    
    def test_dynamic_with_trailing_non_keyword_strings(self):
        m = Mapper(explicit=False)
        m.minimization = True
        m.connect('somewhere/:over/rainbow', controller='blog')
        m.connect('somewhere/:over', controller='post')
        m.create_regs(['post','blog','admin/user'])
    
        eq_(None, m.match('/'))
        eq_(None, m.match('/somewhere'))
        eq_({'controller':'blog','action':'index','over':'near'}, m.match('/somewhere/near/rainbow'))
        eq_({'controller':'post','action':'index','over':'tomorrow'}, m.match('/somewhere/tomorrow'))
        
    def test_dynamic_with_trailing_dyanmic_defaults(self):
        for path in ['archives/:action/:article', 'archives/:(action)/:(article)']:
            m = Mapper()
            m.minimization = True
            m.connect(path, controller='blog')
            m.create_regs(['blog'])
        
            eq_(None, m.match('/'))
            eq_(None, m.match('/archives'))
            eq_(None, m.match('/archives/introduction'))
            eq_(None, m.match('/archives/sample'))
            eq_(None, m.match('/view/super'))
            eq_(None, m.match('/view/4/super'))
            eq_({'controller':'blog','action':'view','article':'introduction'}, 
                             m.match('/archives/view/introduction'))
            eq_({'controller':'blog','action':'edit','article':'recipes'}, 
                             m.match('/archives/edit/recipes'))
    
    def test_path(self):
        for path in ['hi/*file', 'hi/*(file)']:
            m = Mapper()
            m.minimization = True
            m.connect(path, controller='content', action='download')
            m.create_regs([])
        
            eq_(None, m.match('/boo'))
            eq_(None, m.match('/boo/blah'))
            eq_(None, m.match('/hi'))
            eq_({'controller':'content','action':'download','file':'books/learning_python.pdf'}, m.match('/hi/books/learning_python.pdf'))
            eq_({'controller':'content','action':'download','file':'dude'}, m.match('/hi/dude'))
            eq_({'controller':'content','action':'download','file':'dude/what'}, m.match('/hi/dude/what'))
    
    def test_path_with_dynamic(self):
        for path in [':controller/:action/*url', ':(controller)/:(action)/*(url)']:
            m = Mapper()
            m.minimization = True
            m.connect(path)
            m.create_regs(['content','admin/user'])
        
            eq_(None, m.match('/'))
            eq_(None, m.match('/blog'))
            eq_(None, m.match('/content'))
            eq_(None, m.match('/content/view'))
            eq_({'controller':'content','action':'view','url':'blob'}, m.match('/content/view/blob'))
            eq_(None, m.match('/admin/user'))
            eq_(None, m.match('/admin/user/view'))
            eq_({'controller':'admin/user','action':'view','url':'blob/check'}, m.match('/admin/user/view/blob/check'))
    
    
    def test_path_with_dyanmic_and_default(self):
        for path in [':controller/:action/*url', ':(controller)/:(action)/*(url)']:
            m = Mapper()
            m.minimization = True
            m.connect(path, controller='content', action='view', url=None)
            m.create_regs(['content','admin/user'])
        
            eq_(None, m.match('/goober/view/here'))
            eq_({'controller':'content','action':'view','url':None}, m.match('/'))
            eq_({'controller':'content','action':'view','url':None}, m.match('/content'))
            eq_({'controller':'content','action':'view','url':None}, m.match('/content/'))
            eq_({'controller':'content','action':'view','url':None}, m.match('/content/view'))
            eq_({'controller':'content','action':'view','url':'fred'}, m.match('/content/view/fred'))
            eq_({'controller':'admin/user','action':'view','url':None}, m.match('/admin/user'))
            eq_({'controller':'admin/user','action':'view','url':None}, m.match('/admin/user/view'))
    
    def test_path_with_dynamic_and_default_backwards(self):
        for path in ['*file/login', '*(file)/login']:
            m = Mapper()
            m.minimization = True
            m.connect(path, controller='content', action='download', file=None)
            m.create_regs([])

            eq_(None, m.match('/boo'))
            eq_(None, m.match('/boo/blah'))
            eq_({'controller':'content','action':'download','file':''}, m.match('//login'))
            eq_({'controller':'content','action':'download','file':'books/learning_python.pdf'}, m.match('/books/learning_python.pdf/login'))
            eq_({'controller':'content','action':'download','file':'dude'}, m.match('/dude/login'))
            eq_({'controller':'content','action':'download','file':'dude/what'}, m.match('/dude/what/login'))
        
    def test_path_backwards(self):
        for path in ['*file/login', '*(file)/login']:
            m = Mapper()
            m.minimization = True
            m.connect(path, controller='content', action='download')
            m.create_regs([])
        
            eq_(None, m.match('/boo'))
            eq_(None, m.match('/boo/blah'))
            eq_(None, m.match('/login'))
            eq_({'controller':'content','action':'download','file':'books/learning_python.pdf'}, m.match('/books/learning_python.pdf/login'))
            eq_({'controller':'content','action':'download','file':'dude'}, m.match('/dude/login'))
            eq_({'controller':'content','action':'download','file':'dude/what'}, m.match('/dude/what/login'))
    
    def test_path_backwards_with_controller(self):
        m = Mapper()
        m.minimization = True
        m.connect('*url/login', controller='content', action='check_access')
        m.connect('*url/:controller', action='view')
        m.create_regs(['content', 'admin/user'])

        eq_(None, m.match('/boo'))
        eq_(None, m.match('/boo/blah'))
        eq_(None, m.match('/login'))
        eq_({'controller':'content','action':'check_access','url':'books/learning_python.pdf'}, m.match('/books/learning_python.pdf/login'))
        eq_({'controller':'content','action':'check_access','url':'dude'}, m.match('/dude/login'))
        eq_({'controller':'content','action':'check_access','url':'dude/what'}, m.match('/dude/what/login'))
        
        eq_(None, m.match('/admin/user'))
        eq_({'controller':'admin/user','action':'view','url':'books/learning_python.pdf'}, m.match('/books/learning_python.pdf/admin/user'))
        eq_({'controller':'admin/user','action':'view','url':'dude'}, m.match('/dude/admin/user'))
        eq_({'controller':'admin/user','action':'view','url':'dude/what'}, m.match('/dude/what/admin/user'))
    
    def test_path_backwards_with_controller_and_splits(self):
        m = Mapper()
        m.minimization = True
        m.connect('*(url)/login', controller='content', action='check_access')
        m.connect('*(url)/:(controller)', action='view')
        m.create_regs(['content', 'admin/user'])

        eq_(None, m.match('/boo'))
        eq_(None, m.match('/boo/blah'))
        eq_(None, m.match('/login'))
        eq_({'controller':'content','action':'check_access','url':'books/learning_python.pdf'}, m.match('/books/learning_python.pdf/login'))
        eq_({'controller':'content','action':'check_access','url':'dude'}, m.match('/dude/login'))
        eq_({'controller':'content','action':'check_access','url':'dude/what'}, m.match('/dude/what/login'))
        
        eq_(None, m.match('/admin/user'))
        eq_({'controller':'admin/user','action':'view','url':'books/learning_python.pdf'}, m.match('/books/learning_python.pdf/admin/user'))
        eq_({'controller':'admin/user','action':'view','url':'dude'}, m.match('/dude/admin/user'))
        eq_({'controller':'admin/user','action':'view','url':'dude/what'}, m.match('/dude/what/admin/user'))
    
    def test_controller(self):
        m = Mapper()
        m.minimization = True
        m.connect('hi/:controller', action='hi')
        m.create_regs(['content','admin/user'])
        
        eq_(None, m.match('/boo'))
        eq_(None, m.match('/boo/blah'))
        eq_(None, m.match('/hi/13870948'))
        eq_(None, m.match('/hi/content/dog'))
        eq_(None, m.match('/hi/admin/user/foo'))
        eq_(None, m.match('/hi/admin/user/foo/'))
        eq_({'controller':'content','action':'hi'}, m.match('/hi/content'))
        eq_({'controller':'admin/user', 'action':'hi'}, m.match('/hi/admin/user'))
    
    def test_standard_route(self):
        m = Mapper(explicit=False)
        m.minimization = True
        m.connect(':controller/:action/:id')
        m.create_regs(['content','admin/user'])
        
        eq_({'controller':'content','action':'index', 'id': None}, m.match('/content'))
        eq_({'controller':'content','action':'list', 'id':None}, m.match('/content/list'))
        eq_({'controller':'content','action':'show','id':'10'}, m.match('/content/show/10'))

        eq_({'controller':'admin/user','action':'index', 'id': None}, m.match('/admin/user'))
        eq_({'controller':'admin/user','action':'list', 'id':None}, m.match('/admin/user/list'))
        eq_({'controller':'admin/user','action':'show','id':'bbangert'}, m.match('/admin/user/show/bbangert'))

        eq_(None, m.match('/content/show/10/20'))
        eq_(None, m.match('/food'))
    
    def test_standard_route_with_gaps(self):
        m = Mapper()
        m.minimization = True
        m.connect(':controller/:action/:(id).py')
        m.create_regs(['content','admin/user'])
        
        eq_({'controller':'content','action':'index', 'id': 'None'}, m.match('/content/index/None.py'))
        eq_({'controller':'content','action':'list', 'id':'None'}, m.match('/content/list/None.py'))
        eq_({'controller':'content','action':'show','id':'10'}, m.match('/content/show/10.py'))

    def test_standard_route_with_gaps_and_domains(self):
        m = Mapper()
        m.minimization = True
        m.connect('manage/:domain.:ext', controller='admin/user', action='view', ext='html')
        m.connect(':controller/:action/:id')
        m.create_regs(['content','admin/user'])
        
        eq_({'controller':'content','action':'index', 'id': 'None.py'}, m.match('/content/index/None.py'))
        eq_({'controller':'content','action':'list', 'id':'None.py'}, m.match('/content/list/None.py'))
        eq_({'controller':'content','action':'show','id':'10.py'}, m.match('/content/show/10.py'))
        eq_({'controller':'content','action':'show.all','id':'10.py'}, m.match('/content/show.all/10.py'))
        eq_({'controller':'content','action':'show','id':'www.groovie.org'}, m.match('/content/show/www.groovie.org'))
        
        eq_({'controller':'admin/user','action':'view', 'ext': 'html', 'domain': 'groovie'}, m.match('/manage/groovie'))
        eq_({'controller':'admin/user','action':'view', 'ext': 'xml', 'domain': 'groovie'}, m.match('/manage/groovie.xml'))
    
    def test_standard_with_domains(self):
        m = Mapper()
        m.minimization = True
        m.connect('manage/:domain', controller='domains', action='view')
        m.create_regs(['domains'])
        
        eq_({'controller':'domains','action':'view','domain':'www.groovie.org'}, m.match('/manage/www.groovie.org'))
    
    def test_default_route(self):
        m = Mapper()
        m.minimization = True
        m.connect('',controller='content',action='index')
        m.create_regs(['content'])
        
        eq_(None, m.match('/x'))
        eq_(None, m.match('/hello/world'))
        eq_(None, m.match('/hello/world/how/are'))
        eq_(None, m.match('/hello/world/how/are/you/today'))
        
        eq_({'controller':'content','action':'index'}, m.match('/'))

    def test_dynamic_with_prefix(self):
        m = Mapper(explicit=False)
        m.minimization = True
        m.prefix = '/blog'
        m.connect(':controller/:action/:id')
        m.connect('', controller='content', action='index')
        m.create_regs(['content', 'archive', 'admin/comments'])

        eq_(None, m.match('/x'))
        eq_(None, m.match('/admin/comments'))
        eq_(None, m.match('/content/view'))
        eq_(None, m.match('/archive/view/4'))
        
        eq_({'controller':'content','action':'index'}, m.match('/blog'))
        eq_({'controller':'content','action':'index','id':None}, m.match('/blog/content'))
        eq_({'controller':'admin/comments','action':'view','id':None}, m.match('/blog/admin/comments/view'))
        eq_({'controller':'archive','action':'index','id':None}, m.match('/blog/archive'))
        eq_({'controller':'archive','action':'view', 'id':'4'}, m.match('/blog/archive/view/4'))
    
    def test_dynamic_with_multiple_and_prefix(self):
        m = Mapper(explicit=False)
        m.minimization = True
        m.prefix = '/blog'
        m.connect(':controller/:action/:id')
        m.connect('home/:action', controller='archive')
        m.connect('', controller='content')
        m.create_regs(['content', 'archive', 'admin/comments'])

        eq_(None, m.match('/x'))
        eq_(None, m.match('/admin/comments'))
        eq_(None, m.match('/content/view'))
        eq_(None, m.match('/archive/view/4'))
        
        eq_({'controller':'content', 'action':'index'}, m.match('/blog/'))
        eq_({'controller':'archive', 'action':'view'}, m.match('/blog/home/view'))
        eq_({'controller':'content','action':'index','id':None}, m.match('/blog/content'))
        eq_({'controller':'admin/comments','action':'view','id':None}, m.match('/blog/admin/comments/view'))
        eq_({'controller':'archive','action':'index','id':None}, m.match('/blog/archive'))
        eq_({'controller':'archive','action':'view', 'id':'4'}, m.match('/blog/archive/view/4'))
        
    
    def test_splits_with_extension(self):
        m = Mapper()
        m.minimization = True
        m.connect('hi/:(action).html', controller='content')
        m.create_regs([])

        eq_(None, m.match('/boo'))
        eq_(None, m.match('/boo/blah'))
        eq_(None, m.match('/hi/dude/what'))
        eq_(None, m.match('/hi'))
        eq_({'controller':'content','action':'index'}, m.match('/hi/index.html'))
        eq_({'controller':'content','action':'dude'}, m.match('/hi/dude.html'))
    
    def test_splits_with_dashes(self):
        m = Mapper()
        m.minimization = True
        m.connect('archives/:(year)-:(month)-:(day).html', controller='archives', action='view')
        m.create_regs([])
        
        eq_(None, m.match('/boo'))
        eq_(None, m.match('/archives'))
        
        eq_({'controller':'archives','action':'view','year':'2004','month':'12','day':'4'},
                         m.match('/archives/2004-12-4.html'))
        eq_({'controller':'archives','action':'view','year':'04','month':'10','day':'4'},
                         m.match('/archives/04-10-4.html'))
        eq_({'controller':'archives','action':'view','year':'04','month':'1','day':'1'},
                         m.match('/archives/04-1-1.html'))
    
    def test_splits_packed_with_regexps(self):
        m = Mapper()
        m.minimization = True
        m.connect('archives/:(year):(month):(day).html', controller='archives', action='view',
               requirements=dict(year=r'\d{4}',month=r'\d{2}',day=r'\d{2}'))
        m.create_regs([])

        eq_(None, m.match('/boo'))
        eq_(None, m.match('/archives'))
        eq_(None, m.match('/archives/2004020.html'))
        eq_(None, m.match('/archives/200502.html'))

        eq_({'controller':'archives','action':'view','year':'2004','month':'12','day':'04'},
                      m.match('/archives/20041204.html'))
        eq_({'controller':'archives','action':'view','year':'2005','month':'10','day':'04'},
                      m.match('/archives/20051004.html'))
        eq_({'controller':'archives','action':'view','year':'2006','month':'01','day':'01'},
                      m.match('/archives/20060101.html'))

    def test_splits_with_slashes(self):
        m = Mapper()
        m.minimization = True
        m.connect(':name/:(action)-:(day)', controller='content')
        m.create_regs([])
        
        eq_(None, m.match('/something'))
        eq_(None, m.match('/something/is-'))
        
        eq_({'controller':'content','action':'view','day':'3','name':'group'},
                         m.match('/group/view-3'))
        eq_({'controller':'content','action':'view','day':'5','name':'group'},
                         m.match('/group/view-5'))
    
    def test_splits_with_slashes_and_default(self):
        m = Mapper(explicit=False)
        m.minimization = True
        m.connect(':name/:(action)-:(id)', controller='content')
        m.create_regs([])
        
        eq_(None, m.match('/something'))
        eq_(None, m.match('/something/is'))
        
        eq_({'controller':'content','action':'view','id':'3','name':'group'},
                         m.match('/group/view-3'))
        eq_({'controller':'content','action':'view','id':None,'name':'group'},
                         m.match('/group/view-'))
    
    def test_no_reg_make(self):
        m = Mapper()
        m.connect(':name/:(action)-:(id)', controller='content')
        m.controller_scan = False
        def call_func():
            m.match('/group/view-3')
        assert_raises(RoutesException, call_func)        
    
    def test_routematch(self):
        m = Mapper(explicit=False)
        m.minimization = True
        m.connect(':controller/:action/:id')
        m.create_regs(['content'])
        route = m.matchlist[0]
        
        resultdict, route_obj = m.routematch('/content')
        eq_({'action':'index', 'controller':'content','id':None}, resultdict)
        eq_(route, route_obj)
        eq_(None, m.routematch('/nowhere'))
    
    def test_routematch_debug(self):
        m = Mapper(explicit=False)
        m.minimization = True
        m.connect(':controller/:action/:id')
        m.debug = True
        m.create_regs(['content'])
        route = m.matchlist[0]
        
        resultdict, route_obj, debug = m.routematch('/content')
        eq_({'action':'index', 'controller':'content','id':None}, resultdict)
        eq_(route, route_obj)
        resultdict, route_obj, debug = m.routematch('/nowhere')
        eq_(None, resultdict)
        eq_(None, route_obj)
        eq_(len(debug), 0)
    
    def test_match_debug(self):
        m = Mapper(explicit=False)
        m.minimization = True
        m.connect('nowhere', 'http://nowhere.com/', _static=True)
        m.connect(':controller/:action/:id')
        m.debug = True
        m.create_regs(['content'])
        route = m.matchlist[0]
        
        resultdict, route_obj, debug = m.match('/content')
        eq_({'action':'index', 'controller':'content','id':None}, resultdict)
        eq_(route, route_obj)
        resultdict, route_obj, debug = m.match('/nowhere')
        eq_(None, resultdict)
        eq_(route_obj, None)
        eq_(len(debug), 0)
    
    def test_conditions(self):
        m = Mapper(explicit=False)
        m.minimization = True
        m.connect('home/upload', controller='content', action='upload', conditions=dict(method=['POST']))
        m.connect(':controller/:action/:id')
        m.create_regs(['content', 'blog'])
        
        con = request_config()
        con.mapper = m
        env = dict(PATH_INFO='/nowhere', HTTP_HOST='example.com', REQUEST_METHOD='GET')
        con.mapper_dict = {}
        con.environ = env
        eq_(None, con.mapper_dict)
        
        env['PATH_INFO'] = '/content'
        con.environ = env
        eq_({'action':'index','controller':'content','id':None}, con.mapper_dict)
        
        env['PATH_INFO'] = '/home/upload'
        con.environ = env
        eq_(None, con.mapper_dict)
        
        env['REQUEST_METHOD'] = 'POST'
        con.environ = env
        eq_({'action':'upload','controller':'content'}, con.mapper_dict)
        
    def test_subdomains(self):
        m = Mapper(explicit=False)
        m.minimization = True
        m.sub_domains = True
        m.connect(':controller/:action/:id')
        m.create_regs(['content', 'blog'])
        
        con = request_config()
        con.mapper = m
        env = dict(PATH_INFO='/nowhere', HTTP_HOST='example.com')
        con.mapper_dict = {}
        con.environ = env
        
        eq_(None, con.mapper_dict)
        
        env['PATH_INFO'] = '/content'
        con.environ = env
        eq_({'action': 'index', 'controller': 'content', 'sub_domain': None, 'id': None},
            con.mapper_dict)
        
        env['HTTP_HOST'] = 'fred.example.com'
        con.environ = env
        eq_({'action': 'index', 'controller': 'content', 'sub_domain': 'fred', 'id': None},
            con.mapper_dict)
        
        env['HTTP_HOST'] = 'www.example.com'
        con.environ = env
        eq_({'action': 'index', 'controller': 'content', 'sub_domain': 'www', 'id': None},
            con.mapper_dict)
    
    def test_subdomains_with_conditions(self):
        m = Mapper(explicit=False)
        m.minimization = True
        m.sub_domains = True
        m.connect(':controller/:action/:id')
        m.create_regs(['content', 'blog'])
        
        con = request_config()
        con.mapper = m
        env = dict(PATH_INFO='/nowhere', HTTP_HOST='example.com')
        con.mapper_dict = {}
        con.environ = env
        
        eq_(None, con.mapper_dict)
        
        env['PATH_INFO'] = '/content'
        con.environ = env
        eq_({'action': 'index', 'controller': 'content', 'sub_domain': None, 'id': None},
            con.mapper_dict)
        
        m.connect('', controller='users', action='home', conditions={'sub_domain':True})
        m.create_regs(['content', 'users', 'blog'])
        env['PATH_INFO'] = '/'
        con.environ = env
        eq_(None, con.mapper_dict)
        
        env['HTTP_HOST'] = 'fred.example.com'
        con.environ = env
        eq_({'action': 'home', 'controller': 'users', 'sub_domain': 'fred'}, con.mapper_dict)
        
        m.sub_domains_ignore = ['www']
        env['HTTP_HOST'] = 'www.example.com'
        con.environ = env
        eq_(None, con.mapper_dict)
    
    def test_subdomain_with_conditions2(self):
        m = Mapper()
        m.minimization = True
        m.sub_domains = True
        m.connect('admin/comments', controller='admin', action='comments',
                  conditions={'sub_domain':True})
        m.connect('admin/comments', controller='blog_admin', action='comments')
        m.connect('admin/view', controller='blog_admin', action='view',
                  conditions={'sub_domain':False})
        m.connect('admin/view', controller='admin', action='view')
        m.create_regs(['content', 'blog_admin', 'admin'])
        
        con = request_config()
        con.mapper = m
        env = dict(PATH_INFO='/nowhere', HTTP_HOST='example.com')
        con.mapper_dict = {}
        con.environ = env
        
        eq_(None, con.mapper_dict)
        
        env['PATH_INFO'] = '/admin/comments'
        con.environ = env
        eq_({'action': 'comments', 'controller':'blog_admin', 'sub_domain': None}, con.mapper_dict)
        
        env['PATH_INFO'] = '/admin/view'
        env['HTTP_HOST'] = 'fred.example.com'
        con.environ = env
        eq_({'action': 'view', 'controller':'admin', 'sub_domain': 'fred'}, con.mapper_dict)
    
    def test_subdomains_with_ignore(self):
        m = Mapper(explicit=False)
        m.minimization = True
        m.sub_domains = True
        m.sub_domains_ignore = ['www']
        m.connect(':controller/:action/:id')
        m.create_regs(['content', 'blog'])
        
        con = request_config()
        con.mapper = m
        env = dict(PATH_INFO='/nowhere', HTTP_HOST='example.com')
        con.mapper_dict = {}
        con.environ = env
        
        eq_(None, con.mapper_dict)
        
        env['PATH_INFO'] = '/content'
        con.environ = env
        eq_({'action': 'index', 'controller': 'content', 'sub_domain': None, 'id': None},
            con.mapper_dict)
        
        env['HTTP_HOST'] = 'fred.example.com'
        con.environ = env
        eq_({'action': 'index', 'controller': 'content', 'sub_domain': 'fred', 'id': None},
            con.mapper_dict)
        
        env['HTTP_HOST'] = 'www.example.com'
        con.environ = env
        eq_({'action': 'index', 'controller': 'content', 'sub_domain': None, 'id': None},
            con.mapper_dict)
    
    def test_other_special_chars(self):
        m = Mapper(explicit=False)
        m.minimization = True
        m.connect('/:year/:(slug).:(format),:(locale)', format='html', locale='en')
        m.connect('/error/:action/:id', controller='error')
        m.create_regs(['content'])

        eq_({'year': '2007', 'slug': 'test', 'locale': 'en', 'format': 'html',
                          'controller': 'content', 'action': 'index'},
                         m.match('/2007/test'))
        eq_({'year': '2007', 'slug': 'test', 'format': 'html', 'locale': 'en',
                          'controller': 'content', 'action': 'index'},
                         m.match('/2007/test.html'))
        eq_({'year': '2007', 'slug': 'test',
                          'format': 'html', 'locale': 'en',
                          'controller': 'content', 'action': 'index'},
                         m.match('/2007/test.html,en'))
        eq_(None, m.match('/2007/test.'))
        eq_({'controller': 'error', 'action': 'img',
                          'id': 'icon-16.png'}, m.match('/error/img/icon-16.png'))
    
    def test_various_periods(self):
        m = Mapper(explicit=False)
        m.minimization = True
        m.connect('sites/:site/pages/:page')
        m.create_regs(['content'])
        
        eq_({'action': u'index', 'controller': u'content', 
                          'site': u'python.com', 'page': u'index.html'}, 
                         m.match('/sites/python.com/pages/index.html'))
        m = Mapper(explicit=False)
        m.minimization = True
        m.connect('sites/:site/pages/:page.:format', format='html')
        m.create_regs(['content'])
        
        eq_({'action': u'index', 'controller': u'content', 
                          'site': u'python.com', 'page': u'index', 'format': u'html'}, 
                         m.match('/sites/python.com/pages/index.html'))
        
    def test_empty_fails(self):
        m = Mapper(explicit=False)
        m.minimization = True
        m.connect(':controller/:action/:id')
        m.connect('', controller='content', action='view', id=4)
        m.create_regs(['content'])
        
        eq_({'controller':'content','action':'index','id':None}, m.match('/content'))
        eq_({'controller':'content','action':'view','id':'4'}, m.match('/'))
        def call_func():
            m.match('')
        assert_raises(RoutesException, call_func)

    def test_home_noargs(self):
        m = Mapper(controller_scan=None, directory=None, always_scan=False)
        m.minimization = True
        m.explicit = True
        m.connect('')
        m.create_regs([])
        
        eq_(None, m.match('/content'))
        eq_({}, m.match('/'))
        def call_func():
            m.match('')
        assert_raises(RoutesException, call_func)
        
    def test_dot_format_args(self):
        for minimization in [False, True]:
            m = Mapper(explicit=True)
            m.minimization=minimization
            m.connect('/songs/{title}{.format}')
            m.connect('/stories/{slug:[^./]+?}{.format:pdf}')
            
            eq_({'title': 'my-way', 'format': None}, m.match('/songs/my-way'))
            eq_({'title': 'my-way', 'format': 'mp3'}, m.match('/songs/my-way.mp3'))
            eq_({'slug': 'frist-post', 'format': None}, m.match('/stories/frist-post'))
            eq_({'slug': 'frist-post', 'format': 'pdf'}, m.match('/stories/frist-post.pdf'))
            eq_(None, m.match('/stories/frist-post.doc'))


if __name__ == '__main__':
    unittest.main()
else:
    def bench_rec():
        n = 1000
        m = Mapper()
        m.connect('', controller='articles', action='index')
        m.connect('admin', controller='admin/general', action='index')

        m.connect('admin/comments/article/:article_id/:action/:id', controller = 'admin/comments', action = None, id=None)
        m.connect('admin/trackback/article/:article_id/:action/:id', controller='admin/trackback', action=None, id=None)
        m.connect('admin/content/:action/:id', controller='admin/content')

        m.connect('xml/:action/feed.xml', controller='xml')
        m.connect('xml/articlerss/:id/feed.xml', controller='xml', action='articlerss')
        m.connect('index.rdf', controller='xml', action='rss')

        m.connect('articles', controller='articles', action='index')
        m.connect('articles/page/:page', controller='articles', action='index', requirements = {'page':'\d+'})

        m.connect('articles/:year/:month/:day/page/:page', controller='articles', action='find_by_date', month = None, day = None,
                            requirements = {'year':'\d{4}', 'month':'\d{1,2}','day':'\d{1,2}'})
        m.connect('articles/category/:id', controller='articles', action='category')
        m.connect('pages/*name', controller='articles', action='view_page')
        m.create_regs(['content','admin/why', 'admin/user'])
        start = time.time()
        for x in range(1,n):
            a = m.match('/admin/comments/article/42/show/52')
            a = m.match('/admin/content/view/5')
            a = m.match('/index.rdf')
            
            a = m.match('/xml/view/feed.xml')
            a = m.match('/xml/articlerss/42/feed.xml')
            a = m.match('/articles')
            
            a = m.match('/articles/2004/12/20/page/2')
            a = m.match('/articles/category/42')
            a = m.match('/pages/this/is/long')
            a = m.match('/miss')
        end = time.time()
        ts = time.time()
        for x in range(1,n):
            pass
        en = time.time()
        total = end-start-(en-ts)
        per_url = total / (n*10)
        print "Recognition\n"
        print "%s ms/url" % (per_url*1000)
        print "%s urls/s\n" % (1.00/per_url)
    
"""
Copyright (c) 2005 Ben Bangert <ben@groovie.org>, Parachute
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions
are met:
1. Redistributions of source code must retain the above copyright
   notice, this list of conditions and the following disclaimer.
2. Redistributions in binary form must reproduce the above copyright
   notice, this list of conditions and the following disclaimer in the
   documentation and/or other materials provided with the distribution.
3. The name of the author or contributors may not be used to endorse or
   promote products derived from this software without specific prior
   written permission.

THIS SOFTWARE IS PROVIDED BY THE AUTHOR AND CONTRIBUTORS ``AS IS'' AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
ARE DISCLAIMED.  IN NO EVENT SHALL THE AUTHOR OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
SUCH DAMAGE.
"""

########NEW FILE########
__FILENAME__ = test_resources
"""test_resources"""
import unittest
from nose.tools import eq_, assert_raises

from routes import *

class TestResourceGeneration(unittest.TestCase):
    def _assert_restful_routes(self, m, options, path_prefix=''):
        baseroute = '/' + path_prefix + options['controller']
        eq_(baseroute, m.generate(action='index', **options))
        eq_(baseroute + '.xml', m.generate(action='index', format='xml', **options))
        eq_(baseroute + '/new', m.generate(action='new', **options))
        eq_(baseroute + '/1', m.generate(action='show', id='1', **options))
        eq_(baseroute + '/1/edit', m.generate(action='edit',id='1', **options))
        eq_(baseroute + '/1.xml', m.generate(action='show', id='1',format='xml', **options))
        
        eq_(baseroute, m.generate(action='create', method='post', **options))
        eq_(baseroute + '/1', m.generate(action='update', method='put', id='1', **options))
        eq_(baseroute + '/1', m.generate(action='delete', method='delete', id='1', **options))
    
    def test_resources(self):
        m = Mapper()
        m.resource('message', 'messages')
        m.resource('massage', 'massages')
        m.resource('passage', 'passages')
        m.create_regs(['messages'])
        options = dict(controller='messages')
        eq_('/messages', url_for('messages'))
        eq_('/messages.xml', url_for('formatted_messages', format='xml'))
        eq_('/messages/1', url_for('message', id=1))
        eq_('/messages/1.xml', url_for('formatted_message', id=1, format='xml'))
        eq_('/messages/new', url_for('new_message'))
        eq_('/messages/1.xml', url_for('formatted_message', id=1, format='xml'))
        eq_('/messages/1/edit', url_for('edit_message', id=1))
        eq_('/messages/1/edit.xml', url_for('formatted_edit_message', id=1, format='xml'))
        self._assert_restful_routes(m, options)
    
    def test_resources_with_path_prefix(self):
        m = Mapper()
        m.resource('message', 'messages', path_prefix='/thread/:threadid')
        m.create_regs(['messages'])
        options = dict(controller='messages', threadid='5')
        self._assert_restful_routes(m, options, path_prefix='thread/5/')
    
    def test_resources_with_collection_action(self):
        m = Mapper()
        m.resource('message', 'messages', collection=dict(rss='GET'))
        m.create_regs(['messages'])
        options = dict(controller='messages')
        self._assert_restful_routes(m, options)
        eq_('/messages/rss', m.generate(controller='messages', action='rss'))
        eq_('/messages/rss', url_for('rss_messages'))
        eq_('/messages/rss.xml', m.generate(controller='messages', action='rss', format='xml'))
        eq_('/messages/rss.xml', url_for('formatted_rss_messages', format='xml'))
    
    def test_resources_with_member_action(self):
        for method in ['put', 'post']:
            m = Mapper()
            m.resource('message', 'messages', member=dict(mark=method))
            m.create_regs(['messages'])
            options = dict(controller='messages')
            self._assert_restful_routes(m, options)
            eq_('/messages/1/mark', m.generate(method=method, action='mark', id='1', **options))
            eq_('/messages/1/mark.xml', 
                m.generate(method=method, action='mark', id='1', format='xml', **options))
    
    def test_resources_with_new_action(self):
        m = Mapper()
        m.resource('message', 'messages/', new=dict(preview='POST'))
        m.create_regs(['messages'])
        options = dict(controller='messages')
        self._assert_restful_routes(m, options)
        eq_('/messages/new/preview', m.generate(controller='messages', action='preview', method='post'))
        eq_('/messages/new/preview', url_for('preview_new_message'))
        eq_('/messages/new/preview.xml', 
            m.generate(controller='messages', action='preview', method='post', format='xml'))
        eq_('/messages/new/preview.xml', url_for('formatted_preview_new_message', format='xml'))
    
    def test_resources_with_name_prefix(self):
        m = Mapper()
        m.resource('message', 'messages', name_prefix='category_', new=dict(preview='POST'))
        m.create_regs(['messages'])
        options = dict(controller='messages')
        self._assert_restful_routes(m, options)
        eq_('/messages/new/preview', url_for('category_preview_new_message'))
        assert_raises(Exception, url_for, 'category_preview_new_message', method='get')


class TestResourceRecognition(unittest.TestCase):
    def test_resource(self):
        m = Mapper()
        m.resource('person', 'people')
        m.create_regs(['people'])
        
        con = request_config()
        con.mapper = m
        def test_path(path, method):
            env = dict(HTTP_HOST='example.com', PATH_INFO=path, REQUEST_METHOD=method)
            con.mapper_dict = {}
            con.environ = env
        
        test_path('/people', 'GET')
        eq_({'controller':'people', 'action':'index'}, con.mapper_dict)
        test_path('/people.xml', 'GET')
        eq_({'controller':'people', 'action':'index', 'format':'xml'}, con.mapper_dict)
        
        test_path('/people', 'POST')
        eq_({'controller':'people', 'action':'create'}, con.mapper_dict)
        test_path('/people.html', 'POST')
        eq_({'controller':'people', 'action':'create', 'format':'html'}, con.mapper_dict)
        
        test_path('/people/2.xml', 'GET')
        eq_({'controller':'people', 'action':'show', 'id':'2', 'format':'xml'}, con.mapper_dict)
        test_path('/people/2', 'GET')
        eq_({'controller':'people', 'action':'show', 'id':'2'}, con.mapper_dict)
        
        test_path('/people/2/edit', 'GET')
        eq_({'controller':'people', 'action':'edit', 'id':'2'}, con.mapper_dict)
        test_path('/people/2/edit.xml', 'GET')
        eq_({'controller':'people', 'action':'edit', 'id':'2', 'format':'xml'}, con.mapper_dict)

        test_path('/people/2', 'DELETE')
        eq_({'controller':'people', 'action':'delete', 'id':'2'}, con.mapper_dict)

        test_path('/people/2', 'PUT')
        eq_({'controller':'people', 'action':'update', 'id':'2'}, con.mapper_dict        )
        test_path('/people/2.json', 'PUT')
        eq_({'controller':'people', 'action':'update', 'id':'2', 'format':'json'}, con.mapper_dict        )

        # Test for dots in urls
        test_path('/people/2\.13', 'PUT')
        eq_({'controller':'people', 'action':'update', 'id':'2\.13'}, con.mapper_dict)
        test_path('/people/2\.13.xml', 'PUT')
        eq_({'controller':'people', 'action':'update', 'id':'2\.13', 'format':'xml'}, con.mapper_dict)
        test_path('/people/user\.name', 'PUT')
        eq_({'controller':'people', 'action':'update', 'id':'user\.name'}, con.mapper_dict)
        test_path('/people/user\.\.\.name', 'PUT')
        eq_({'controller':'people', 'action':'update', 'id':'user\.\.\.name'}, con.mapper_dict)
        test_path('/people/user\.name\.has\.dots', 'PUT')
        eq_({'controller':'people', 'action':'update', 'id':'user\.name\.has\.dots'}, con.mapper_dict)
        test_path('/people/user\.name\.is\.something.xml', 'PUT')
        eq_({'controller':'people', 'action':'update', 'id':'user\.name\.is\.something', 'format':'xml'}, con.mapper_dict)
        test_path('/people/user\.name\.ends\.with\.dot\..xml', 'PUT')
        eq_({'controller':'people', 'action':'update', 'id':'user\.name\.ends\.with\.dot\.', 'format':'xml'}, con.mapper_dict)
        test_path('/people/user\.name\.ends\.with\.dot\.', 'PUT')
        eq_({'controller':'people', 'action':'update', 'id':'user\.name\.ends\.with\.dot\.'}, con.mapper_dict)
        test_path('/people/\.user\.name\.starts\.with\.dot', 'PUT')
        eq_({'controller':'people', 'action':'update', 'id':'\.user\.name\.starts\.with\.dot'}, con.mapper_dict)
        test_path('/people/user\.name.json', 'PUT')
        eq_({'controller':'people', 'action':'update', 'id':'user\.name', 'format':'json'}, con.mapper_dict)

    def test_resource_with_nomin(self):
        m = Mapper()
        m.minimization = False
        m.resource('person', 'people')
        m.create_regs(['people'])
        
        con = request_config()
        con.mapper = m
        def test_path(path, method):
            env = dict(HTTP_HOST='example.com', PATH_INFO=path, REQUEST_METHOD=method)
            con.mapper_dict = {}
            con.environ = env
        
        test_path('/people', 'GET')
        eq_({'controller':'people', 'action':'index'}, con.mapper_dict)
        
        test_path('/people', 'POST')
        eq_({'controller':'people', 'action':'create'}, con.mapper_dict)
        
        test_path('/people/2', 'GET')
        eq_({'controller':'people', 'action':'show', 'id':'2'}, con.mapper_dict)
        test_path('/people/2/edit', 'GET')
        eq_({'controller':'people', 'action':'edit', 'id':'2'}, con.mapper_dict)

        test_path('/people/2', 'DELETE')
        eq_({'controller':'people', 'action':'delete', 'id':'2'}, con.mapper_dict)

        test_path('/people/2', 'PUT')
        eq_({'controller':'people', 'action':'update', 'id':'2'}, con.mapper_dict)

    def test_resource_created_with_parent_resource(self): 
        m = Mapper()
        m.resource('location', 'locations',
                   parent_resource=dict(member_name='region',
                                        collection_name='regions'))
        m.create_regs(['locations'])
        
        con = request_config()
        con.mapper = m
        def test_path(path, method):
            env = dict(HTTP_HOST='example.com', PATH_INFO=path,
                       REQUEST_METHOD=method)
            con.mapper_dict = {}
            con.environ = env
        
        test_path('/regions/13/locations', 'GET')
        eq_(con.mapper_dict, {'region_id': '13', 'controller': 'locations',
                                   'action': 'index'})
        url = url_for('region_locations', region_id=13)
        eq_(url, '/regions/13/locations')
        
        test_path('/regions/13/locations', 'POST')
        eq_(con.mapper_dict, {'region_id': '13', 'controller': 'locations',
                                   'action': 'create'})
        # new
        url = url_for('region_new_location', region_id=13)
        eq_(url, '/regions/13/locations/new')
        # create
        url = url_for('region_locations', region_id=13)
        eq_(url, '/regions/13/locations')
        
        test_path('/regions/13/locations/60', 'GET')
        eq_(con.mapper_dict, {'region_id': '13', 'controller': 'locations',
                                   'id': '60', 'action': 'show'})
        url = url_for('region_location', region_id=13, id=60)
        eq_(url, '/regions/13/locations/60')
        
        test_path('/regions/13/locations/60/edit', 'GET')
        eq_(con.mapper_dict, {'region_id': '13', 'controller': 'locations',
                                   'id': '60', 'action': 'edit'})
        url = url_for('region_edit_location', region_id=13, id=60)
        eq_(url, '/regions/13/locations/60/edit')
        
        test_path('/regions/13/locations/60', 'DELETE')
        eq_(con.mapper_dict, {'region_id': '13', 'controller': 'locations',
                                   'id': '60', 'action': 'delete'})
        url = url_for('region_location', region_id=13, id=60)
        eq_(url, '/regions/13/locations/60')
        
        test_path('/regions/13/locations/60', 'PUT')
        eq_(con.mapper_dict, {'region_id': '13', 'controller': 'locations',
                                   'id': '60', 'action': 'update'})
        url = url_for('region_location', region_id=13, id=60)
        eq_(url, '/regions/13/locations/60')
    
        # Make sure ``path_prefix`` overrides work
        # empty ``path_prefix`` (though I'm not sure why someone would do this)
        m = Mapper()
        m.resource('location', 'locations',
                   parent_resource=dict(member_name='region',
                                        collection_name='regions'),
                   path_prefix='')
        url = url_for('region_locations')
        eq_(url, '/locations')
        # different ``path_prefix``
        m = Mapper()
        m.resource('location', 'locations',
                   parent_resource=dict(member_name='region',
                                        collection_name='regions'),
                   path_prefix='areas/:area_id')
        url = url_for('region_locations', area_id=51)
        eq_(url, '/areas/51/locations')

        # Make sure ``name_prefix`` overrides work
        # empty ``name_prefix``
        m = Mapper()
        m.resource('location', 'locations',
                   parent_resource=dict(member_name='region',
                                        collection_name='regions'),
                   name_prefix='')
        url = url_for('locations', region_id=51)
        eq_(url, '/regions/51/locations')
        # different ``name_prefix``
        m = Mapper()
        m.resource('location', 'locations',
                   parent_resource=dict(member_name='region',
                                        collection_name='regions'),
                   name_prefix='area_')
        url = url_for('area_locations', region_id=51)
        eq_(url, '/regions/51/locations')

        # Make sure ``path_prefix`` and ``name_prefix`` overrides work together
        # empty ``path_prefix``
        m = Mapper()
        m.resource('location', 'locations',
                   parent_resource=dict(member_name='region',
                                        collection_name='regions'),
                   path_prefix='',
                   name_prefix='place_')
        url = url_for('place_locations')
        eq_(url, '/locations')
        # empty ``name_prefix``
        m = Mapper()
        m.resource('location', 'locations',
                   parent_resource=dict(member_name='region',
                                        collection_name='regions'),
                   path_prefix='areas/:area_id',
                   name_prefix='')
        url = url_for('locations', area_id=51)
        eq_(url, '/areas/51/locations')
        # different ``path_prefix`` and ``name_prefix``
        m = Mapper()
        m.resource('location', 'locations',
                   parent_resource=dict(member_name='region',
                                        collection_name='regions'),
                   path_prefix='areas/:area_id',
                   name_prefix='place_')
        url = url_for('place_locations', area_id=51)
        eq_(url, '/areas/51/locations')

    def test_resource_created_with_parent_resource_nomin(self): 
        m = Mapper()
        m.minimization = False
        m.resource('location', 'locations',
                   parent_resource=dict(member_name='region',
                                        collection_name='regions'))
        m.create_regs(['locations'])
        
        con = request_config()
        con.mapper = m
        def test_path(path, method):
            env = dict(HTTP_HOST='example.com', PATH_INFO=path,
                       REQUEST_METHOD=method)
            con.mapper_dict = {}
            con.environ = env
        
        test_path('/regions/13/locations', 'GET')
        eq_(con.mapper_dict, {'region_id': '13', 'controller': 'locations',
                                   'action': 'index'})
        url = url_for('region_locations', region_id=13)
        eq_(url, '/regions/13/locations')
        
        test_path('/regions/13/locations', 'POST')
        eq_(con.mapper_dict, {'region_id': '13', 'controller': 'locations',
                                   'action': 'create'})
        # new
        url = url_for('region_new_location', region_id=13)
        eq_(url, '/regions/13/locations/new')
        # create
        url = url_for('region_locations', region_id=13)
        eq_(url, '/regions/13/locations')
        
        test_path('/regions/13/locations/60', 'GET')
        eq_(con.mapper_dict, {'region_id': '13', 'controller': 'locations',
                                   'id': '60', 'action': 'show'}) 
        url = url_for('region_location', region_id=13, id=60)               
        eq_(url, '/regions/13/locations/60')                                
                                                                            
        test_path('/regions/13/locations/60/edit', 'GET')                   
        eq_(con.mapper_dict, {'region_id': '13', 'controller': 'locations',
                                   'id': '60', 'action': 'edit'}) 
        url = url_for('region_edit_location', region_id=13, id=60)          
        eq_(url, '/regions/13/locations/60/edit')                           
                                                                            
        test_path('/regions/13/locations/60', 'DELETE')                     
        eq_(con.mapper_dict, {'region_id': '13', 'controller': 'locations',
                                   'id': '60', 'action': 'delete'}) 
        url = url_for('region_location', region_id=13, id=60)               
        eq_(url, '/regions/13/locations/60')                                
                                                                            
        test_path('/regions/13/locations/60', 'PUT')                        
        eq_(con.mapper_dict, {'region_id': '13', 'controller': 'locations',
                                   'id': '60', 'action': 'update'})
        url = url_for('region_location', region_id=13, id=60)
        eq_(url, '/regions/13/locations/60')
    
        # Make sure ``path_prefix`` overrides work
        # empty ``path_prefix`` (though I'm not sure why someone would do this)
        m = Mapper()
        m.resource('location', 'locations',
                   parent_resource=dict(member_name='region',
                                        collection_name='regions'),
                   path_prefix='/')
        url = url_for('region_locations')
        eq_(url, '/locations')
        # different ``path_prefix``
        m = Mapper()
        m.resource('location', 'locations',
                   parent_resource=dict(member_name='region',
                                        collection_name='regions'),
                   path_prefix='areas/:area_id')
        url = url_for('region_locations', area_id=51)
        eq_(url, '/areas/51/locations')

        # Make sure ``name_prefix`` overrides work
        # empty ``name_prefix``
        m = Mapper()
        m.resource('location', 'locations',
                   parent_resource=dict(member_name='region',
                                        collection_name='regions'),
                   name_prefix='')
        url = url_for('locations', region_id=51)
        eq_(url, '/regions/51/locations')
        # different ``name_prefix``
        m = Mapper()
        m.resource('location', 'locations',
                   parent_resource=dict(member_name='region',
                                        collection_name='regions'),
                   name_prefix='area_')
        url = url_for('area_locations', region_id=51)
        eq_(url, '/regions/51/locations')

        # Make sure ``path_prefix`` and ``name_prefix`` overrides work together
        # empty ``path_prefix``
        m = Mapper()
        m.resource('location', 'locations',
                   parent_resource=dict(member_name='region',
                                        collection_name='regions'),
                   path_prefix='',
                   name_prefix='place_')
        url = url_for('place_locations')
        eq_(url, '/locations')
        # empty ``name_prefix``
        m = Mapper()
        m.resource('location', 'locations',
                   parent_resource=dict(member_name='region',
                                        collection_name='regions'),
                   path_prefix='areas/:area_id',
                   name_prefix='')
        url = url_for('locations', area_id=51)
        eq_(url, '/areas/51/locations')
        # different ``path_prefix`` and ``name_prefix``
        m = Mapper()
        m.resource('location', 'locations',
                   parent_resource=dict(member_name='region',
                                        collection_name='regions'),
                   path_prefix='areas/:area_id',
                   name_prefix='place_')
        url = url_for('place_locations', area_id=51)
        eq_(url, '/areas/51/locations')

        

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_submapper
"""test_resources"""
import unittest
from nose.tools import eq_, assert_raises

from routes import *

class TestSubmapper(unittest.TestCase):
    def test_submapper(self):
        m = Mapper()
        c = m.submapper(path_prefix='/entries', requirements=dict(id='\d+'))
        c.connect('entry', '/{id}')
        
        eq_('/entries/1', url_for('entry', id=1))
        assert_raises(Exception, url_for, 'entry', id='foo')

    def test_submapper_nesting(self):
        m = Mapper()
        c = m.submapper(path_prefix='/entries', controller='entry',
                        requirements=dict(id='\d+'))
        e = c.submapper(path_prefix='/{id}')
        
        eq_('entry', c.resource_name)
        eq_('entry', e.resource_name)
        
        e.connect('entry', '')
        e.connect('edit_entry', '/edit')

        eq_('/entries/1', url_for('entry', id=1))
        eq_('/entries/1/edit', url_for('edit_entry', id=1))
        assert_raises(Exception, url_for, 'entry', id='foo')

    def test_submapper_action(self):
        m = Mapper(explicit=True)
        c = m.submapper(path_prefix='/entries', controller='entry')

        c.action(name='entries', action='list')
        c.action(action='create', method='POST')
                
        eq_('/entries', url_for('entries', method='GET'))
        eq_('/entries', url_for('create_entry', method='POST'))
        eq_('/entries', url_for(controller='entry', action='list', method='GET'))
        eq_('/entries', url_for(controller='entry', action='create', method='POST'))
        assert_raises(Exception, url_for, 'entries', method='DELETE')

    def test_submapper_link(self):
        m = Mapper(explicit=True)
        c = m.submapper(path_prefix='/entries', controller='entry')
        
        c.link(rel='new')
        c.link(rel='ping', method='POST')
        
        eq_('/entries/new', url_for('new_entry', method='GET'))
        eq_('/entries/ping', url_for('ping_entry', method='POST'))
        eq_('/entries/new', url_for(controller='entry', action='new', method='GET'))
        eq_('/entries/ping', url_for(controller='entry', action='ping', method='POST'))
        assert_raises(Exception, url_for, 'new_entry', method='PUT')
        assert_raises(Exception, url_for, 'ping_entry', method='PUT')

    def test_submapper_standard_actions(self):
        m = Mapper()
        c = m.submapper(path_prefix='/entries', collection_name='entries',
                        controller='entry')
        e = c.submapper(path_prefix='/{id}')
        
        c.index()
        c.create()
        e.show()
        e.update()
        e.delete()

        eq_('/entries', url_for('entries', method='GET'))
        eq_('/entries', url_for('create_entry', method='POST'))
        assert_raises(Exception, url_for, 'entries', method='DELETE')
        
        eq_('/entries/1', url_for('entry', id=1, method='GET'))
        eq_('/entries/1', url_for('update_entry', id=1, method='PUT'))
        eq_('/entries/1', url_for('delete_entry', id=1, method='DELETE'))
        assert_raises(Exception, url_for, 'entry', id=1, method='POST')

    def test_submapper_standard_links(self):
        m = Mapper()
        c = m.submapper(path_prefix='/entries', controller='entry')
        e = c.submapper(path_prefix='/{id}')
        
        c.new()
        e.edit()

        eq_('/entries/new', url_for('new_entry', method='GET'))
        assert_raises(Exception, url_for, 'new_entry', method='POST')
        
        eq_('/entries/1/edit', url_for('edit_entry', id=1, method='GET'))
        assert_raises(Exception, url_for, 'edit_entry', id=1, method='POST')

    def test_submapper_action_and_link_generation(self):
        m = Mapper()
        c = m.submapper(path_prefix='/entries', controller='entry',
                        collection_name='entries',
                        actions=['index', 'new', 'create'])
        e = c.submapper(path_prefix='/{id}',
                       actions=['show', 'edit', 'update', 'delete'])

        eq_('/entries', url_for('entries', method='GET'))
        eq_('/entries', url_for('create_entry', method='POST'))
        assert_raises(Exception, url_for, 'entries', method='DELETE')
        
        eq_('/entries/1', url_for('entry', id=1, method='GET'))
        eq_('/entries/1', url_for('update_entry', id=1, method='PUT'))
        eq_('/entries/1', url_for('delete_entry', id=1, method='DELETE'))
        assert_raises(Exception, url_for, 'entry', id=1, method='POST')

        eq_('/entries/new', url_for('new_entry', method='GET'))
        assert_raises(Exception, url_for, 'new_entry', method='POST')
        
        eq_('/entries/1/edit', url_for('edit_entry', id=1, method='GET'))
        assert_raises(Exception, url_for, 'edit_entry', id=1, method='POST')

    def test_collection(self):
        m = Mapper()
        c = m.collection('entries', 'entry')

        eq_('/entries', url_for('entries', method='GET'))
        eq_('/entries', url_for('create_entry', method='POST'))
        assert_raises(Exception, url_for, 'entries', method='DELETE')
        
        eq_('/entries/1', url_for('entry', id=1, method='GET'))
        eq_('/entries/1', url_for('update_entry', id=1, method='PUT'))
        eq_('/entries/1', url_for('delete_entry', id=1, method='DELETE'))
        assert_raises(Exception, url_for, 'entry', id=1, method='POST')

        eq_('/entries/new', url_for('new_entry', method='GET'))
        assert_raises(Exception, url_for, 'new_entry', method='POST')
        
        eq_('/entries/1/edit', url_for('edit_entry', id=1, method='GET'))
        assert_raises(Exception, url_for, 'edit_entry', id=1, method='POST')

    def test_collection_options(self):
        m = Mapper()
        requirement=dict(id='\d+')
        c = m.collection('entries', 'entry', conditions=dict(sub_domain=True),
                         requirements=requirement)
        for r in m.matchlist:
            eq_(True, r.conditions['sub_domain'])
            eq_(requirement, r.reqs)

    def test_subsubmapper_with_controller(self):
        m = Mapper()
        col1 = m.collection('parents', 'parent',
                            controller='col1',
                            member_prefix='/{parent_id}')
        # NOTE: If one uses functions as controllers, the error will be here.
        col2 = col1.member.collection('children', 'child',
                                      controller='col2',
                                      member_prefix='/{child_id}')
        match = m.match('/parents/1/children/2')
        eq_('col2', match.get('controller'))


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_utils
"""test_utils"""
import os, sys, time, unittest
from nose.tools import eq_, assert_raises

from routes.util import controller_scan, GenerationException
from routes import *

class TestUtils(unittest.TestCase):
    def setUp(self):
        m = Mapper(explicit=False)
        m.minimization = True
        m.connect('archive/:year/:month/:day', controller='blog', action='view', month=None, day=None,
                  requirements={'month':'\d{1,2}','day':'\d{1,2}'})
        m.connect('viewpost/:id', controller='post', action='view')
        m.connect(':controller/:action/:id')
        con = request_config()
        con.mapper = m
        con.host = 'www.test.com'
        con.protocol = 'http'
        if hasattr(con, 'environ'):
            del con.environ
        self.con = con
    
    def test_url_for_with_nongen(self):
        con = self.con
        con.mapper_dict = {}
        
        eq_('/blog', url_for('/blog'))
        eq_('/blog?q=fred&q=here%20now', url_for('/blog', q=['fred', u'here now']))
        eq_('/blog#here', url_for('/blog', anchor='here'))

    def test_url_for_with_nongen_no_encoding(self):
        con = self.con
        con.mapper_dict = {}
        con.mapper.encoding = None
        
        eq_('/blog', url_for('/blog'))
        eq_('/blog#here', url_for('/blog', anchor='here'))
        
    def test_url_for_with_unicode(self):
        con = self.con
        con.mapper_dict = {}
        
        eq_('/blog', url_for(controller='blog'))
        eq_('/blog/view/umulat', url_for(controller='blog', action='view', id=u'umulat'))
        eq_('/blog/view/umulat?other=%CE%B1%CF%83%CE%B4%CE%B3', 
            url_for(controller='blog', action='view', id=u'umulat', other=u'\u03b1\u03c3\u03b4\u03b3'))
        
        url = URLGenerator(con.mapper, {})
        for urlobj in [url_for, url]:
            def raise_url():
                return urlobj(u'/some/st\xc3rng')
            assert_raises(Exception, raise_url)
    
    def test_url_for(self):
        con = self.con
        con.mapper_dict = {}
        url = URLGenerator(con.mapper, {'HTTP_HOST':'www.test.com:80'})
        
        for urlobj in [url_for, url]:
            eq_('/blog', urlobj(controller='blog'))
            eq_('/content', urlobj())
            eq_('https://www.test.com/viewpost', urlobj(controller='post', action='view', protocol='https'))
            eq_('http://www.test.org/content', urlobj(host='www.test.org'))
    
    def test_url_raises(self):
        con = self.con
        con.mapper.explicit = True
        con.mapper_dict = {}
        url = URLGenerator(con.mapper, {})
        assert_raises(GenerationException, url_for, action='juice')
        assert_raises(GenerationException, url, action='juice')
    
    def test_url_for_with_defaults(self):
        con = self.con
        con.mapper_dict = {'controller':'blog','action':'view','id':4}
        url = URLGenerator(con.mapper, {'wsgiorg.routing_args':((), con.mapper_dict)})
        
        eq_('/blog/view/4', url_for())
        eq_('/post/index/4', url_for(controller='post'))
        eq_('/blog/view/2', url_for(id=2))
        eq_('/viewpost/4', url_for(controller='post', action='view', id=4))

        eq_('/blog/view/4', url.current())
        eq_('/post/index/4', url.current(controller='post'))
        eq_('/blog/view/2', url.current(id=2))
        eq_('/viewpost/4', url.current(controller='post', action='view', id=4))
        
        con.mapper_dict = {'controller':'blog','action':'view','year':2004}
        url = URLGenerator(con.mapper, {'wsgiorg.routing_args':((), con.mapper_dict)})
        
        eq_('/archive/2004/10', url_for(month=10))
        eq_('/archive/2004/9/2', url_for(month=9, day=2))
        eq_('/blog', url_for(controller='blog', year=None))

        eq_('/archive/2004/10', url.current(month=10))
        eq_('/archive/2004/9/2', url.current(month=9, day=2))
        eq_('/blog', url.current(controller='blog', year=None))
    
    def test_url_for_with_more_defaults(self):
        con = self.con
        con.mapper_dict = {'controller':'blog','action':'view','id':4}
        url = URLGenerator(con.mapper, {'wsgiorg.routing_args':((), con.mapper_dict)})
        
        eq_('/blog/view/4', url_for())
        eq_('/post/index/4', url_for(controller='post'))
        eq_('/blog/view/2', url_for(id=2))
        eq_('/viewpost/4', url_for(controller='post', action='view', id=4))

        eq_('/blog/view/4', url.current())
        eq_('/post/index/4', url.current(controller='post'))
        eq_('/blog/view/2', url.current(id=2))
        eq_('/viewpost/4', url.current(controller='post', action='view', id=4))
        
        con.mapper_dict = {'controller':'blog','action':'view','year':2004}
        url = URLGenerator(con.mapper, {'wsgiorg.routing_args':((), con.mapper_dict)})
        eq_('/archive/2004/10', url_for(month=10))
        eq_('/archive/2004/9/2', url_for(month=9, day=2))
        eq_('/blog', url_for(controller='blog', year=None))
        eq_('/archive/2004', url_for())

        eq_('/archive/2004/10', url.current(month=10))
        eq_('/archive/2004/9/2', url.current(month=9, day=2))
        eq_('/blog', url.current(controller='blog', year=None))
        eq_('/archive/2004', url.current())
    
    def test_url_for_with_defaults_and_qualified(self):
        m = self.con.mapper
        m.connect('home', '', controller='blog', action='splash')
        m.connect('category_home', 'category/:section', controller='blog', action='view', section='home')
        m.connect(':controller/:action/:id')
        m.create_regs(['content','blog','admin/comments'])
        self.con.environ = dict(SCRIPT_NAME='', HTTP_HOST='www.example.com', PATH_INFO='/blog/view/4')
        self.con.environ.update({'wsgiorg.routing_args':((), self.con.mapper_dict)})
        url = URLGenerator(m, self.con.environ)
        
        eq_('/blog/view/4', url_for())
        eq_('/post/index/4', url_for(controller='post'))
        eq_('http://www.example.com/blog/view/4', url_for(qualified=True))
        eq_('/blog/view/2', url_for(id=2))
        eq_('/viewpost/4', url_for(controller='post', action='view', id=4))

        eq_('/blog/view/4', url.current())
        eq_('/post/index/4', url.current(controller='post'))
        eq_('http://www.example.com/blog/view/4', url.current(qualified=True))
        eq_('/blog/view/2', url.current(id=2))
        eq_('/viewpost/4', url.current(controller='post', action='view', id=4))
        
        env = dict(SCRIPT_NAME='', SERVER_NAME='www.example.com', SERVER_PORT='8080', PATH_INFO='/blog/view/4')
        env['wsgi.url_scheme'] = 'http'
        self.con.environ = env
        self.con.environ.update({'wsgiorg.routing_args':((), self.con.mapper_dict)})
        url = URLGenerator(m, self.con.environ)
        
        eq_('/post/index/4', url_for(controller='post'))
        eq_('http://www.example.com:8080/blog/view/4', url_for(qualified=True))
        
        eq_('/post/index/4', url.current(controller='post'))
        eq_('http://www.example.com:8080/blog/view/4', url.current(qualified=True))
        
    def test_route_overflow(self):
        m = self.con.mapper
        m.create_regs(["x"*50000])
        m.connect('route-overflow', "x"*50000)
        url = URLGenerator(m, {})
        eq_("/%s" % ("x"*50000), url('route-overflow'))
    
    def test_with_route_names(self):
        m = self.con.mapper
        self.con.mapper_dict = {}
        m.connect('home', '', controller='blog', action='splash')
        m.connect('category_home', 'category/:section', controller='blog', action='view', section='home')
        m.create_regs(['content','blog','admin/comments'])
        url = URLGenerator(m, {})
        
        for urlobj in [url, url_for]:
            eq_('/content/view', urlobj(controller='content', action='view'))
            eq_('/content', urlobj(controller='content'))
            eq_('/admin/comments', urlobj(controller='admin/comments'))
            eq_('/category', urlobj('category_home'))
            eq_('/category/food', urlobj('category_home', section='food'))
            eq_('/', urlobj('home'))
        
    def test_with_route_names_and_defaults(self):
        m = self.con.mapper
        self.con.mapper_dict = {}        
        m.connect('home', '', controller='blog', action='splash')
        m.connect('category_home', 'category/:section', controller='blog', action='view', section='home')
        m.connect('building', 'building/:campus/:building/alljacks', controller='building', action='showjacks')
        m.create_regs(['content','blog','admin/comments','building'])

        self.con.mapper_dict = dict(controller='building', action='showjacks', campus='wilma', building='port')
        url = URLGenerator(m, {'wsgiorg.routing_args':((), self.con.mapper_dict)})

        eq_('/building/wilma/port/alljacks', url_for())
        eq_('/', url_for('home'))
        eq_('/building/wilma/port/alljacks', url.current())
        eq_('/', url.current('home'))
        
    def test_with_route_names_and_hardcode(self):
        m = self.con.mapper
        self.con.mapper_dict = {}
        m.hardcode_names = False
        
        m.connect('home', '', controller='blog', action='splash')
        m.connect('category_home', 'category/:section', controller='blog', action='view', section='home')
        m.connect('building', 'building/:campus/:building/alljacks', controller='building', action='showjacks')
        m.connect('gallery_thumb', 'gallery/:(img_id)_thumbnail.jpg')
        m.connect('gallery', 'gallery/:(img_id).jpg')
        m.create_regs(['content','blog','admin/comments','building'])

        self.con.mapper_dict = dict(controller='building', action='showjacks', campus='wilma', building='port')
        url = URLGenerator(m, {'wsgiorg.routing_args':((), self.con.mapper_dict)})
        eq_('/building/wilma/port/alljacks', url_for())
        eq_('/', url_for('home'))
        eq_('/gallery/home_thumbnail.jpg', url_for('gallery_thumb', img_id='home'))
        eq_('/gallery/home_thumbnail.jpg', url_for('gallery', img_id='home'))

        eq_('/building/wilma/port/alljacks', url.current())
        eq_('/', url.current('home'))
        eq_('/gallery/home_thumbnail.jpg', url.current('gallery_thumb', img_id='home'))
        eq_('/gallery/home_thumbnail.jpg', url.current('gallery', img_id='home'))
        
        m.hardcode_names = True
        eq_('/gallery/home_thumbnail.jpg', url_for('gallery_thumb', img_id='home'))
        eq_('/gallery/home.jpg', url_for('gallery', img_id='home'))

        eq_('/gallery/home_thumbnail.jpg', url.current('gallery_thumb', img_id='home'))
        eq_('/gallery/home.jpg', url.current('gallery', img_id='home'))
        m.hardcode_names = False
    
    def test_redirect_to(self):
        m = self.con.mapper
        self.con.mapper_dict = {}
        self.con.environ = dict(SCRIPT_NAME='', HTTP_HOST='www.example.com')
        result = None
        def printer(echo):
            redirect_to.result = echo
        self.con.redirect = printer
        m.create_regs(['content','blog','admin/comments'])

        redirect_to(controller='content', action='view')
        eq_('/content/view', redirect_to.result)
        redirect_to(controller='content', action='lookup', id=4)
        eq_('/content/lookup/4', redirect_to.result)
        redirect_to(controller='admin/comments',action='splash')
        eq_('/admin/comments/splash', redirect_to.result)
        redirect_to('http://www.example.com/')
        eq_('http://www.example.com/', redirect_to.result)
        redirect_to('/somewhere.html', var='keyword')
        eq_('/somewhere.html?var=keyword', redirect_to.result)

    def test_redirect_to_with_route_names(self):
        m = self.con.mapper
        self.con.mapper_dict = {}
        result = None
        def printer(echo):
            redirect_to.result = echo
        self.con.redirect = printer
        m.connect('home', '', controller='blog', action='splash')
        m.connect('category_home', 'category/:section', controller='blog', action='view', section='home')
        m.create_regs(['content','blog','admin/comments'])
        
        redirect_to(controller='content', action='view')
        eq_('/content/view', redirect_to.result)
        redirect_to(controller='content')
        eq_('/content', redirect_to.result)
        redirect_to(controller='admin/comments')
        eq_('/admin/comments', redirect_to.result)
        redirect_to('category_home')
        eq_('/category', redirect_to.result)
        redirect_to('category_home', section='food')
        eq_('/category/food', redirect_to.result)
        redirect_to('home')
        eq_('/', redirect_to.result)
    
    def test_static_route(self):
        m = self.con.mapper
        self.con.mapper_dict = {}
        self.con.environ = dict(SCRIPT_NAME='', HTTP_HOST='example.com')
        m.connect(':controller/:action/:id')
        m.connect('home', 'http://www.groovie.org/', _static=True)
        m.connect('space', '/nasa/images', _static=True)
        m.create_regs(['content', 'blog'])
        
        url = URLGenerator(m, {})
        for urlobj in [url_for, url]:
            eq_('http://www.groovie.org/', urlobj('home'))
            eq_('http://www.groovie.org/?s=stars', urlobj('home', s='stars'))
            eq_('/content/view', urlobj(controller='content', action='view'))
            eq_('/nasa/images?search=all', urlobj('space', search='all'))
    
    def test_static_route_with_script(self):
        m = self.con.mapper
        self.con.mapper_dict = {}
        self.con.environ = dict(SCRIPT_NAME='/webapp', HTTP_HOST='example.com')
        m.connect(':controller/:action/:id')
        m.connect('home', 'http://www.groovie.org/', _static=True)
        m.connect('space', '/nasa/images', _static=True)
        m.connect('login', '/login', action='nowhereville')
        m.create_regs(['content', 'blog'])
        
        self.con.environ.update({'wsgiorg.routing_args':((), {})})
        url = URLGenerator(m, self.con.environ)
        for urlobj in [url_for, url]:
            eq_('http://www.groovie.org/', urlobj('home'))
            eq_('http://www.groovie.org/?s=stars', urlobj('home', s='stars'))
            eq_('/webapp/content/view', urlobj(controller='content', action='view'))
            eq_('/webapp/nasa/images?search=all', urlobj('space', search='all'))
            eq_('http://example.com/webapp/nasa/images', urlobj('space', protocol='http'))
            eq_('http://example.com/webapp/login', urlobj('login', qualified=True))
    
    def test_static_route_with_vars(self):
        m = self.con.mapper
        self.con.mapper_dict = {}
        self.con.environ = dict(SCRIPT_NAME='/webapp', HTTP_HOST='example.com')
        m.connect('home', 'http://{domain}.groovie.org/{location}', _static=True)
        m.connect('space', '/nasa/{location}', _static=True)
        m.create_regs(['home', 'space'])
        
        self.con.environ.update({'wsgiorg.routing_args':((), {})})
        url = URLGenerator(m, self.con.environ)
        for urlobj in [url_for, url]:
            assert_raises(GenerationException, urlobj, 'home')
            assert_raises(GenerationException, urlobj, 'home', domain='fred')
            assert_raises(GenerationException, urlobj, 'home', location='index')
            eq_('http://fred.groovie.org/index', urlobj('home', domain='fred', location='index'))
            eq_('http://fred.groovie.org/index?search=all', urlobj('home', domain='fred', location='index', search='all'))
            eq_('/webapp/nasa/images?search=all', urlobj('space', location='images', search='all'))
            eq_('http://example.com/webapp/nasa/images', urlobj('space', location='images', protocol='http'))
    
    def test_static_route_with_vars_and_defaults(self):
        m = self.con.mapper
        self.con.mapper_dict = {}
        self.con.environ = dict(SCRIPT_NAME='/webapp', HTTP_HOST='example.com')
        m.connect('home', 'http://{domain}.groovie.org/{location}', domain='routes', _static=True)
        m.connect('space', '/nasa/{location}', location='images', _static=True)
        m.create_regs(['home', 'space'])
        
        self.con.environ.update({'wsgiorg.routing_args':((), {})})
        url = URLGenerator(m, self.con.environ)
        
        assert_raises(GenerationException, url_for, 'home')
        assert_raises(GenerationException, url_for, 'home', domain='fred')
        eq_('http://routes.groovie.org/index', url_for('home', location='index'))
        eq_('http://fred.groovie.org/index', url_for('home', domain='fred', location='index'))
        eq_('http://routes.groovie.org/index?search=all', url_for('home', location='index', search='all'))
        eq_('http://fred.groovie.org/index?search=all', url_for('home', domain='fred', location='index', search='all'))
        eq_('/webapp/nasa/articles?search=all', url_for('space', location='articles', search='all'))
        eq_('http://example.com/webapp/nasa/articles', url_for('space', location='articles', protocol='http'))
        eq_('/webapp/nasa/images?search=all', url_for('space', search='all'))
        eq_('http://example.com/webapp/nasa/images', url_for('space', protocol='http'))
        
        assert_raises(GenerationException, url.current, 'home')
        assert_raises(GenerationException, url.current, 'home', domain='fred')
        eq_('http://routes.groovie.org/index', url.current('home', location='index'))
        eq_('http://fred.groovie.org/index', url.current('home', domain='fred', location='index'))
        eq_('http://routes.groovie.org/index?search=all', url.current('home', location='index', search='all'))
        eq_('http://fred.groovie.org/index?search=all', url.current('home', domain='fred', location='index', search='all'))
        eq_('/webapp/nasa/articles?search=all', url.current('space', location='articles', search='all'))
        eq_('http://example.com/webapp/nasa/articles', url.current('space', location='articles', protocol='http'))
        eq_('/webapp/nasa/images?search=all', url.current('space', search='all'))
        eq_('http://example.com/webapp/nasa/images', url.current('space', protocol='http'))
    
    
    def test_static_route_with_vars_and_requirements(self):
        m = self.con.mapper
        self.con.mapper_dict = {}
        self.con.environ = dict(SCRIPT_NAME='/webapp', HTTP_HOST='example.com')
        m.connect('home', 'http://{domain}.groovie.org/{location}', requirements=dict(domain='fred|bob'), _static=True)
        m.connect('space', '/nasa/articles/{year}/{month}', requirements=dict(year=r'\d{2,4}', month=r'\d{1,2}'), _static=True)
        m.create_regs(['home', 'space'])
        
        
        self.con.environ.update({'wsgiorg.routing_args':((), {})})
        url = URLGenerator(m, self.con.environ)

        assert_raises(GenerationException, url_for, 'home', domain='george', location='index')
        assert_raises(GenerationException, url_for, 'space', year='asdf', month='1')
        assert_raises(GenerationException, url_for, 'space', year='2004', month='a')
        assert_raises(GenerationException, url_for, 'space', year='1', month='1')
        assert_raises(GenerationException, url_for, 'space', year='20045', month='1')
        assert_raises(GenerationException, url_for, 'space', year='2004', month='123')
        eq_('http://fred.groovie.org/index', url_for('home', domain='fred', location='index'))
        eq_('http://bob.groovie.org/index', url_for('home', domain='bob', location='index'))
        eq_('http://fred.groovie.org/asdf', url_for('home', domain='fred', location='asdf'))
        eq_('/webapp/nasa/articles/2004/6', url_for('space', year='2004', month='6'))
        eq_('/webapp/nasa/articles/2004/12', url_for('space', year='2004', month='12'))
        eq_('/webapp/nasa/articles/89/6', url_for('space', year='89', month='6'))

        assert_raises(GenerationException, url.current, 'home', domain='george', location='index')
        assert_raises(GenerationException, url.current, 'space', year='asdf', month='1')
        assert_raises(GenerationException, url.current, 'space', year='2004', month='a')
        assert_raises(GenerationException, url.current, 'space', year='1', month='1')
        assert_raises(GenerationException, url.current, 'space', year='20045', month='1')
        assert_raises(GenerationException, url.current, 'space', year='2004', month='123')
        eq_('http://fred.groovie.org/index', url.current('home', domain='fred', location='index'))
        eq_('http://bob.groovie.org/index', url.current('home', domain='bob', location='index'))
        eq_('http://fred.groovie.org/asdf', url.current('home', domain='fred', location='asdf'))
        eq_('/webapp/nasa/articles/2004/6', url.current('space', year='2004', month='6'))
        eq_('/webapp/nasa/articles/2004/12', url.current('space', year='2004', month='12'))
        eq_('/webapp/nasa/articles/89/6', url.current('space', year='89', month='6'))
    
    def test_no_named_path(self):
        m = self.con.mapper
        self.con.mapper_dict = {}
        self.con.environ = dict(SCRIPT_NAME='', HTTP_HOST='example.com')
        m.connect(':controller/:action/:id')
        m.connect('home', 'http://www.groovie.org/', _static=True)
        m.connect('space', '/nasa/images', _static=True)
        m.create_regs(['content', 'blog'])
        
        url = URLGenerator(m, {})
        for urlobj in [url_for, url]:
            eq_('http://www.google.com/search', urlobj('http://www.google.com/search'))
            eq_('http://www.google.com/search?q=routes', urlobj('http://www.google.com/search', q='routes'))
            eq_('/delicious.jpg', urlobj('/delicious.jpg'))
            eq_('/delicious/search?v=routes', urlobj('/delicious/search', v='routes'))
    
    def test_append_slash(self):
        m = self.con.mapper
        self.con.mapper_dict = {}
        m.append_slash = True
        self.con.environ = dict(SCRIPT_NAME='', HTTP_HOST='example.com')
        m.connect(':controller/:action/:id')
        m.connect('home', 'http://www.groovie.org/', _static=True)
        m.connect('space', '/nasa/images', _static=True)
        m.create_regs(['content', 'blog'])
        
        url = URLGenerator(m, {})
        for urlobj in [url_for, url]:
            eq_('http://www.google.com/search', urlobj('http://www.google.com/search'))
            eq_('http://www.google.com/search?q=routes', urlobj('http://www.google.com/search', q='routes'))
            eq_('/delicious.jpg', urlobj('/delicious.jpg'))
            eq_('/delicious/search?v=routes', urlobj('/delicious/search', v='routes'))
            eq_('/content/list/', urlobj(controller='/content', action='list'))
            eq_('/content/list/?page=1', urlobj(controller='/content', action='list', page='1'))

    def test_no_named_path_with_script(self):
        m = self.con.mapper
        self.con.mapper_dict = {}
        self.con.environ = dict(SCRIPT_NAME='/webapp', HTTP_HOST='example.com')
        m.connect(':controller/:action/:id')
        m.connect('home', 'http://www.groovie.org/', _static=True)
        m.connect('space', '/nasa/images', _static=True)
        m.create_regs(['content', 'blog'])
        
        url = URLGenerator(m, self.con.environ)
        for urlobj in [url_for, url]:
            eq_('http://www.google.com/search', urlobj('http://www.google.com/search'))
            eq_('http://www.google.com/search?q=routes', urlobj('http://www.google.com/search', q='routes'))
            eq_('/webapp/delicious.jpg', urlobj('/delicious.jpg'))
            eq_('/webapp/delicious/search?v=routes', urlobj('/delicious/search', v='routes'))

    def test_route_filter(self):
        def article_filter(kargs):
            article = kargs.pop('article', None)
            if article is not None:
                kargs.update(
                    dict(year=article.get('year', 2004),
                         month=article.get('month', 12),
                         day=article.get('day', 20),
                         slug=article.get('slug', 'default')
                    )
                )
            return kargs
        
        self.con.mapper_dict = {}
        self.con.environ = dict(SCRIPT_NAME='', HTTP_HOST='example.com')

        m = Mapper(explicit=False)
        m.minimization = True
        m.connect(':controller/:(action)-:(id).html')
        m.connect('archives', 'archives/:year/:month/:day/:slug', controller='archives', action='view',
                  _filter=article_filter)
        m.create_regs(['content','archives','admin/comments'])
        self.con.mapper = m
        
        url = URLGenerator(m, self.con.environ)
        for urlobj in [url_for, url]:
            assert_raises(Exception, urlobj, controller='content', action='view')
            assert_raises(Exception, urlobj, controller='content')
        
            eq_('/content/view-3.html', urlobj(controller='content', action='view', id=3))
            eq_('/content/index-2.html', urlobj(controller='content', id=2))
        
            eq_('/archives/2005/10/5/happy', 
                urlobj('archives',year=2005, month=10, day=5, slug='happy'))
            story = dict(year=2003, month=8, day=2, slug='woopee')
            empty = {}
            eq_({'controller':'archives','action':'view','year':'2005',
                'month':'10','day':'5','slug':'happy'}, m.match('/archives/2005/10/5/happy'))
            eq_('/archives/2003/8/2/woopee', urlobj('archives', article=story))
            eq_('/archives/2004/12/20/default', urlobj('archives', article=empty))
    
    def test_with_ssl_environ(self):
        base_environ = dict(SCRIPT_NAME='', HTTPS='on', SERVER_PORT='443', PATH_INFO='/', 
            HTTP_HOST='example.com', SERVER_NAME='example.com')
        self.con.mapper_dict = {}
        self.con.environ = base_environ.copy()

        m = Mapper(explicit=False)
        m.minimization = True
        m.connect(':controller/:action/:id')
        m.create_regs(['content','archives','admin/comments'])
        m.sub_domains = True
        self.con.mapper = m
        
        url = URLGenerator(m, self.con.environ)
        for urlobj in [url_for, url]:
    
            # HTTPS is on, but we're running on a different port internally
            eq_(self.con.protocol, 'https')
            eq_('/content/view', urlobj(controller='content', action='view'))
            eq_('/content/index/2', urlobj(controller='content', id=2))
            eq_('https://nowhere.com/content', urlobj(host='nowhere.com', controller='content'))
        
            # If HTTPS is on, but the port isn't 443, we'll need to include the port info
            environ = base_environ.copy()
            environ.update(dict(SERVER_PORT='8080'))
            self.con.environ = environ
            self.con.mapper_dict = {}
            eq_('/content/index/2', urlobj(controller='content', id=2))
            eq_('https://nowhere.com/content', urlobj(host='nowhere.com', controller='content'))
            eq_('https://nowhere.com:8080/content', urlobj(host='nowhere.com:8080', controller='content'))
            eq_('http://nowhere.com/content', urlobj(host='nowhere.com', protocol='http', controller='content'))
            eq_('http://home.com/content', urlobj(host='home.com', protocol='http', controller='content'))
            
    
    def test_with_http_environ(self):
        base_environ = dict(SCRIPT_NAME='', SERVER_PORT='1080', PATH_INFO='/', 
            HTTP_HOST='example.com', SERVER_NAME='example.com')
        base_environ['wsgi.url_scheme'] = 'http'
        self.con.environ = base_environ.copy()
        self.con.mapper_dict = {}

        m = Mapper(explicit=False)
        m.minimization = True
        m.connect(':controller/:action/:id')
        m.create_regs(['content','archives','admin/comments'])
        self.con.mapper = m
        
        url = URLGenerator(m, self.con.environ)
        for urlobj in [url_for, url]:
            eq_(self.con.protocol, 'http')
            eq_('/content/view', urlobj(controller='content', action='view'))
            eq_('/content/index/2', urlobj(controller='content', id=2))
            eq_('https://example.com/content', urlobj(protocol='https', controller='content'))
    
        
    def test_subdomains(self):
        base_environ = dict(SCRIPT_NAME='', PATH_INFO='/', HTTP_HOST='example.com', SERVER_NAME='example.com')
        self.con.mapper_dict = {}
        self.con.environ = base_environ.copy()

        m = Mapper(explicit=False)
        m.minimization = True
        m.sub_domains = True
        m.connect(':controller/:action/:id')
        m.create_regs(['content','archives','admin/comments'])
        self.con.mapper = m
        
        url = URLGenerator(m, self.con.environ)
        for urlobj in [url_for, url]:
            eq_('/content/view', urlobj(controller='content', action='view'))
            eq_('/content/index/2', urlobj(controller='content', id=2))
            environ = base_environ.copy()
            environ.update(dict(HTTP_HOST='sub.example.com'))
            self.con.environ = environ
            self.con.mapper_dict = {'sub_domain':'sub'}
            eq_('/content/view/3', urlobj(controller='content', action='view', id=3))
            eq_('http://new.example.com/content', urlobj(controller='content', sub_domain='new'))

    def test_subdomains_with_exceptions(self):
        base_environ = dict(SCRIPT_NAME='', PATH_INFO='/', HTTP_HOST='example.com', SERVER_NAME='example.com')
        self.con.mapper_dict = {}
        self.con.environ = base_environ.copy()

        m = Mapper(explicit=False)
        m.minimization = True
        m.sub_domains = True
        m.sub_domains_ignore = ['www']
        m.connect(':controller/:action/:id')
        m.create_regs(['content','archives','admin/comments'])
        self.con.mapper = m
        
        url = URLGenerator(m, self.con.environ)
        eq_('/content/view', url_for(controller='content', action='view'))
        eq_('/content/index/2', url_for(controller='content', id=2))
        eq_('/content/view', url(controller='content', action='view'))
        eq_('/content/index/2', url(controller='content', id=2))
        
        environ = base_environ.copy()
        environ.update(dict(HTTP_HOST='sub.example.com'))
        self.con.environ = environ
        self.con.mapper_dict = {'sub_domain':'sub'}
        self.con.environ.update({'wsgiorg.routing_args':((), self.con.mapper_dict)})
        url = URLGenerator(m, self.con.environ)
        
        eq_('/content/view/3', url_for(controller='content', action='view', id=3))
        eq_('http://new.example.com/content', url_for(controller='content', sub_domain='new'))
        eq_('http://example.com/content', url_for(controller='content', sub_domain='www'))
        eq_('/content/view/3', url(controller='content', action='view', id=3))
        eq_('http://new.example.com/content', url(controller='content', sub_domain='new'))
        eq_('http://example.com/content', url(controller='content', sub_domain='www'))
        
        self.con.mapper_dict = {'sub_domain':'www'}
        self.con.environ.update({'wsgiorg.routing_args':((), self.con.mapper_dict)})
        url = URLGenerator(m, self.con.environ)
        
        eq_('http://example.com/content/view/3', url_for(controller='content', action='view', id=3))
        eq_('http://new.example.com/content', url_for(controller='content', sub_domain='new'))
        eq_('/content', url_for(controller='content', sub_domain='sub'))
        
        # This requires the sub-domain, because we don't automatically go to the existing match dict
        eq_('http://example.com/content/view/3', url(controller='content', action='view', id=3, sub_domain='www'))
        eq_('http://new.example.com/content', url(controller='content', sub_domain='new'))
        eq_('/content', url(controller='content', sub_domain='sub'))
    
    def test_subdomains_with_named_routes(self):
        base_environ = dict(SCRIPT_NAME='', PATH_INFO='/', HTTP_HOST='example.com', SERVER_NAME='example.com')
        self.con.mapper_dict = {}
        self.con.environ = base_environ.copy()

        m = Mapper(explicit=False)
        m.minimization = True
        m.sub_domains = True
        m.connect(':controller/:action/:id')
        m.connect('category_home', 'category/:section', controller='blog', action='view', section='home')
        m.connect('building', 'building/:campus/:building/alljacks', controller='building', action='showjacks')
        m.create_regs(['content','blog','admin/comments','building'])
        self.con.mapper = m
        
        url = URLGenerator(m, self.con.environ)
        for urlobj in [url_for, url]:
            eq_('/content/view', urlobj(controller='content', action='view'))
            eq_('/content/index/2', urlobj(controller='content', id=2))
            eq_('/category', urlobj('category_home'))
            eq_('http://new.example.com/category', urlobj('category_home', sub_domain='new'))
        
        environ = base_environ.copy()
        environ.update(dict(HTTP_HOST='sub.example.com'))
        self.con.environ = environ
        self.con.mapper_dict = {'sub_domain':'sub'}
        self.con.environ.update({'wsgiorg.routing_args':((), self.con.mapper_dict)})
        url = URLGenerator(m, self.con.environ)
        
        eq_('/content/view/3', url_for(controller='content', action='view', id=3))
        eq_('http://joy.example.com/building/west/merlot/alljacks', 
            url_for('building', campus='west', building='merlot', sub_domain='joy'))
        eq_('http://example.com/category/feeds', url_for('category_home', section='feeds', sub_domain=None))

        eq_('/content/view/3', url(controller='content', action='view', id=3))
        eq_('http://joy.example.com/building/west/merlot/alljacks', 
            url('building', campus='west', building='merlot', sub_domain='joy'))
        eq_('http://example.com/category/feeds', url('category_home', section='feeds', sub_domain=None))

    
    def test_subdomains_with_ports(self):
        base_environ = dict(SCRIPT_NAME='', PATH_INFO='/', HTTP_HOST='example.com:8000', SERVER_NAME='example.com')
        self.con.mapper_dict = {}
        self.con.environ = base_environ.copy()

        m = Mapper(explicit=False)
        m.minimization = True
        m.sub_domains = True
        m.connect(':controller/:action/:id')
        m.connect('category_home', 'category/:section', controller='blog', action='view', section='home')
        m.connect('building', 'building/:campus/:building/alljacks', controller='building', action='showjacks')
        m.create_regs(['content','blog','admin/comments','building'])
        self.con.mapper = m
        
        url = URLGenerator(m, self.con.environ)
        for urlobj in [url, url_for]:
            self.con.environ['HTTP_HOST'] = 'example.com:8000'
            eq_('/content/view', urlobj(controller='content', action='view'))
            eq_('/category', urlobj('category_home'))
            eq_('http://new.example.com:8000/category', urlobj('category_home', sub_domain='new'))
            eq_('http://joy.example.com:8000/building/west/merlot/alljacks', 
                urlobj('building', campus='west', building='merlot', sub_domain='joy'))
        
            self.con.environ['HTTP_HOST'] = 'example.com'
            del self.con.environ['routes.cached_hostinfo']
            eq_('http://new.example.com/category', urlobj('category_home', sub_domain='new'))
    
    def test_subdomains_with_default(self):
        base_environ = dict(SCRIPT_NAME='', PATH_INFO='/', HTTP_HOST='example.com:8000', SERVER_NAME='example.com')
        self.con.mapper_dict = {}
        self.con.environ = base_environ.copy()

        m = Mapper(explicit=False)
        m.minimization = True
        m.sub_domains = True
        m.connect(':controller/:action/:id')
        m.connect('category_home', 'category/:section', controller='blog', action='view', section='home',
                  sub_domain='cat', conditions=dict(sub_domain=['cat']))
        m.connect('building', 'building/:campus/:building/alljacks', controller='building', action='showjacks')
        m.create_regs(['content','blog','admin/comments','building'])
        self.con.mapper = m
        
        urlobj = URLGenerator(m, self.con.environ)
        self.con.environ['HTTP_HOST'] = 'example.com:8000'
        eq_('/content/view', urlobj(controller='content', action='view'))
        eq_('http://cat.example.com:8000/category', urlobj('category_home'))
    
        self.con.environ['HTTP_HOST'] = 'example.com'
        del self.con.environ['routes.cached_hostinfo']
        
        assert_raises(GenerationException, lambda: urlobj('category_home', sub_domain='new'))

    
    def test_controller_scan(self):
        here_dir = os.path.dirname(__file__)
        controller_dir = os.path.join(os.path.dirname(here_dir), 
            os.path.join('test_files', 'controller_files'))
        controllers = controller_scan(controller_dir)
        eq_(len(controllers), 3)
        eq_(controllers[0], 'admin/users')
        eq_(controllers[1], 'content')
        eq_(controllers[2], 'users')
    
    def test_auto_controller_scan(self):
        here_dir = os.path.dirname(__file__)
        controller_dir = os.path.join(os.path.dirname(here_dir), 
            os.path.join('test_files', 'controller_files'))
        m = Mapper(directory=controller_dir, explicit=False)
        m.minimization = True
        m.always_scan = True
        m.connect(':controller/:action/:id')
        
        eq_({'action':'index', 'controller':'content','id':None}, m.match('/content'))
        eq_({'action':'index', 'controller':'users','id':None}, m.match('/users'))
        eq_({'action':'index', 'controller':'admin/users','id':None}, m.match('/admin/users'))

class TestUtilsWithExplicit(unittest.TestCase):
    def setUp(self):
        m = Mapper(explicit=True)
        m.minimization = True
        m.connect('archive/:year/:month/:day', controller='blog', action='view', month=None, day=None,
                  requirements={'month':'\d{1,2}','day':'\d{1,2}'})
        m.connect('viewpost/:id', controller='post', action='view', id=None)
        m.connect(':controller/:action/:id')
        con = request_config()
        con.mapper = m
        con.host = 'www.test.com'
        con.protocol = 'http'
        self.con = con
        
    def test_url_for(self):
        con = self.con
        con.mapper_dict = {}
        
        assert_raises(Exception, url_for, controller='blog')
        assert_raises(Exception, url_for)
        eq_('/blog/view/3', url_for(controller='blog', action='view', id=3))
        eq_('https://www.test.com/viewpost', url_for(controller='post', action='view', protocol='https'))
        eq_('http://www.test.org/content/view/2', url_for(host='www.test.org', controller='content', action='view', id=2))
    
    def test_url_for_with_defaults(self):
        con = self.con
        con.mapper_dict = {'controller':'blog','action':'view','id':4}
        
        assert_raises(Exception, url_for)
        assert_raises(Exception, url_for, controller='post')
        assert_raises(Exception, url_for, id=2)
        eq_('/viewpost/4', url_for(controller='post', action='view', id=4))
        
        con.mapper_dict = {'controller':'blog','action':'view','year':2004}
        assert_raises(Exception, url_for, month=10)
        assert_raises(Exception, url_for, month=9, day=2)
        assert_raises(Exception, url_for, controller='blog', year=None)
    
    def test_url_for_with_more_defaults(self):
        con = self.con
        con.mapper_dict = {'controller':'blog','action':'view','id':4}
        
        assert_raises(Exception, url_for)
        assert_raises(Exception, url_for, controller='post')
        assert_raises(Exception, url_for, id=2)
        eq_('/viewpost/4', url_for(controller='post', action='view', id=4))
        
        con.mapper_dict = {'controller':'blog','action':'view','year':2004}
        assert_raises(Exception, url_for, month=10)
        assert_raises(Exception, url_for)
    
    def test_url_for_with_defaults_and_qualified(self):
        m = self.con.mapper
        m.connect('home', '', controller='blog', action='splash')
        m.connect('category_home', 'category/:section', controller='blog', action='view', section='home')
        m.connect(':controller/:action/:id')
        m.create_regs(['content','blog','admin/comments'])
        env = dict(SCRIPT_NAME='', SERVER_NAME='www.example.com', SERVER_PORT='80', PATH_INFO='/blog/view/4')
        env['wsgi.url_scheme'] = 'http'
        
        self.con.environ = env
        
        assert_raises(Exception, url_for)
        assert_raises(Exception, url_for, controller='post')
        assert_raises(Exception, url_for, id=2)
        assert_raises(Exception, url_for, qualified=True, controller='blog', id=4)
        eq_('http://www.example.com/blog/view/4', url_for(qualified=True, controller='blog', action='view', id=4))
        eq_('/viewpost/4', url_for(controller='post', action='view', id=4))
        
        env = dict(SCRIPT_NAME='', SERVER_NAME='www.example.com', SERVER_PORT='8080', PATH_INFO='/blog/view/4')
        env['wsgi.url_scheme'] = 'http'
        self.con.environ = env
        assert_raises(Exception, url_for, controller='post')
        eq_('http://www.example.com:8080/blog/view/4', url_for(qualified=True, controller='blog', action='view', id=4))
        
    
    def test_with_route_names(self):
        m = self.con.mapper
        m.minimization = True
        self.con.mapper_dict = {}
        m.connect('home', '', controller='blog', action='splash')
        m.connect('category_home', 'category/:section', controller='blog', action='view', section='home')
        m.create_regs(['content','blog','admin/comments'])

        assert_raises(Exception, url_for, controller='content', action='view')
        assert_raises(Exception, url_for, controller='content')
        assert_raises(Exception, url_for, controller='admin/comments')
        eq_('/category', url_for('category_home'))
        eq_('/category/food', url_for('category_home', section='food'))
        assert_raises(Exception, url_for, 'home', controller='content')
        eq_('/', url_for('home'))

    def test_with_route_names_and_nomin(self):
        m = self.con.mapper
        m.minimization = False
        self.con.mapper_dict = {}
        m.connect('home', '', controller='blog', action='splash')
        m.connect('category_home', 'category/:section', controller='blog', action='view', section='home')
        m.create_regs(['content','blog','admin/comments'])

        assert_raises(Exception, url_for, controller='content', action='view')
        assert_raises(Exception, url_for, controller='content')
        assert_raises(Exception, url_for, controller='admin/comments')
        eq_('/category/home', url_for('category_home'))
        eq_('/category/food', url_for('category_home', section='food'))
        assert_raises(Exception, url_for, 'home', controller='content')
        eq_('/', url_for('home'))

    def test_with_route_names_and_defaults(self):
        m = self.con.mapper
        self.con.mapper_dict = {}
        m.connect('home', '', controller='blog', action='splash')
        m.connect('category_home', 'category/:section', controller='blog', action='view', section='home')
        m.connect('building', 'building/:campus/:building/alljacks', controller='building', action='showjacks')
        m.create_regs(['content','blog','admin/comments','building'])

        self.con.mapper_dict = dict(controller='building', action='showjacks', campus='wilma', building='port')
        assert_raises(Exception, url_for)
        eq_('/building/wilma/port/alljacks', url_for(controller='building', action='showjacks', campus='wilma', building='port'))
        eq_('/', url_for('home'))

    def test_with_resource_route_names(self):
        m = Mapper()
        self.con.mapper = m
        self.con.mapper_dict = {}
        m.resource('message', 'messages', member={'mark':'GET'}, collection={'rss':'GET'})
        m.create_regs(['messages'])

        assert_raises(Exception, url_for, controller='content', action='view')
        assert_raises(Exception, url_for, controller='content')
        assert_raises(Exception, url_for, controller='admin/comments')
        eq_('/messages', url_for('messages'))
        eq_('/messages/rss', url_for('rss_messages'))
        eq_('/messages/4', url_for('message', id=4))
        eq_('/messages/4/edit', url_for('edit_message', id=4))
        eq_('/messages/4/mark', url_for('mark_message', id=4))
        eq_('/messages/new', url_for('new_message'))
        
        eq_('/messages.xml', url_for('formatted_messages', format='xml'))
        eq_('/messages/rss.xml', url_for('formatted_rss_messages', format='xml'))
        eq_('/messages/4.xml', url_for('formatted_message', id=4, format='xml'))
        eq_('/messages/4/edit.xml', url_for('formatted_edit_message', id=4, format='xml'))
        eq_('/messages/4/mark.xml', url_for('formatted_mark_message', id=4, format='xml'))
        eq_('/messages/new.xml', url_for('formatted_new_message', format='xml'))

    def test_with_resource_route_names_and_nomin(self):
        m = Mapper()
        self.con.mapper = m
        self.con.mapper_dict = {}
        m.minimization = False
        m.resource('message', 'messages', member={'mark':'GET'}, collection={'rss':'GET'})
        m.create_regs(['messages'])

        assert_raises(Exception, url_for, controller='content', action='view')
        assert_raises(Exception, url_for, controller='content')
        assert_raises(Exception, url_for, controller='admin/comments')
        eq_('/messages', url_for('messages'))
        eq_('/messages/rss', url_for('rss_messages'))
        eq_('/messages/4', url_for('message', id=4))
        eq_('/messages/4/edit', url_for('edit_message', id=4))
        eq_('/messages/4/mark', url_for('mark_message', id=4))
        eq_('/messages/new', url_for('new_message'))
        
        eq_('/messages.xml', url_for('formatted_messages', format='xml'))
        eq_('/messages/rss.xml', url_for('formatted_rss_messages', format='xml'))
        eq_('/messages/4.xml', url_for('formatted_message', id=4, format='xml'))
        eq_('/messages/4/edit.xml', url_for('formatted_edit_message', id=4, format='xml'))
        eq_('/messages/4/mark.xml', url_for('formatted_mark_message', id=4, format='xml'))
        eq_('/messages/new.xml', url_for('formatted_new_message', format='xml'))
        

if __name__ == '__main__':
    unittest.main()
else:
    def bench_gen(withcache = False):
        m = Mapper(explicit=False)
        m.connect('', controller='articles', action='index')
        m.connect('admin', controller='admin/general', action='index')
        
        m.connect('admin/comments/article/:article_id/:action/:id', controller = 'admin/comments', action = None, id=None)
        m.connect('admin/trackback/article/:article_id/:action/:id', controller='admin/trackback', action=None, id=None)
        m.connect('admin/content/:action/:id', controller='admin/content')
        
        m.connect('xml/:action/feed.xml', controller='xml')
        m.connect('xml/articlerss/:id/feed.xml', controller='xml', action='articlerss')
        m.connect('index.rdf', controller='xml', action='rss')

        m.connect('articles', controller='articles', action='index')
        m.connect('articles/page/:page', controller='articles', action='index', requirements = {'page':'\d+'})

        m.connect('articles/:year/:month/:day/page/:page', controller='articles', action='find_by_date', month = None, day = None,
                            requirements = {'year':'\d{4}', 'month':'\d{1,2}','day':'\d{1,2}'})
        m.connect('articles/category/:id', controller='articles', action='category')
        m.connect('pages/*name', controller='articles', action='view_page')
        con = Config()
        con.mapper = m
        con.host = 'www.test.com'
        con.protocol = 'http'
        con.mapper_dict = {'controller':'xml','action':'articlerss'}
        
        if withcache:
            m.urlcache = {}
        m._create_gens()
        n = 5000
        start = time.time()
        for x in range(1,n):
            url_for(controller='/articles', action='index', page=4)
            url_for(controller='admin/general', action='index')
            url_for(controller='admin/comments', action='show', article_id=2)

            url_for(controller='articles', action='find_by_date', year=2004, page=1)
            url_for(controller='articles', action='category', id=4)
            url_for(id=2)
        end = time.time()
        ts = time.time()
        for x in range(1,n*6):
            pass
        en = time.time()
        total = end-start-(en-ts)
        per_url = total / (n*6)
        print "Generation (%s URLs) RouteSet" % (n*6)
        print "%s ms/url" % (per_url*1000)
        print "%s urls/s\n" % (1.00/per_url)

########NEW FILE########
__FILENAME__ = test_base
import unittest
from routes import request_config, _RequestConfig
from routes.base import Route

class TestBase(unittest.TestCase):
    def test_route(self):
        route = Route(None, ':controller/:action/:id')
        assert not route.static
    
    def test_request_config(self):
        orig_config = request_config()
        class Obby(object): pass
        myobj = Obby()
        class MyCallable(object):
            def __init__(self):
                class Obby(object): pass
                self.obj = myobj
            
            def __call__(self):
                return self.obj
        
        mycall = MyCallable()
        if hasattr(orig_config, 'using_request_local'):
            orig_config.request_local = mycall 
            config = request_config()
        assert id(myobj) == id(config)
        old_config = request_config(original=True)
        assert issubclass(old_config.__class__, _RequestConfig) is True
        del orig_config.request_local
 
if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_environment
import unittest
import routes

class TestEnvironment(unittest.TestCase):
    def setUp(self):
        m = routes.Mapper(explicit=False)
        m.minimization = True
        m.connect('archive/:year/:month/:day', controller='blog', action='view', month=None, day=None,
                  requirements={'month':'\d{1,2}','day':'\d{1,2}'})
        m.connect('viewpost/:id', controller='post', action='view')
        m.connect(':controller/:action/:id')
        m.create_regs(['content', 'blog'])
        con = routes.request_config()
        con.mapper = m
        self.con = con
    
    def test_env_set(self):
        env = dict(PATH_INFO='/content', HTTP_HOST='somewhere.com')
        con = self.con
        con.mapper_dict = {}
        assert con.mapper_dict == {}
        delattr(con, 'mapper_dict')
        
        assert not hasattr(con, 'mapper_dict')
        con.mapper_dict = {}
        
        con.environ = env
        assert con.mapper.environ == env
        assert con.protocol == 'http'
        assert con.host == 'somewhere.com'
        assert con.mapper_dict.has_key('controller')
        assert con.mapper_dict['controller'] == 'content'

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_mapper_str
import unittest
from routes import Mapper

class TestMapperStr(unittest.TestCase):
    def test_str(self):
        m = Mapper()
        m.connect('/{controller}/{action}')
        m.connect('entries', '/entries', controller='entry', action='index')
        m.connect('entry', '/entries/{id}', controller='entry', action='show')

        expected = """\
Route name Methods Path
                   /{controller}/{action}
entries            /entries
entry              /entries/{id}"""
        
        for expected_line, actual_line in zip(expected.splitlines(), str(m).splitlines()):
            assert expected_line == actual_line.rstrip()

########NEW FILE########
