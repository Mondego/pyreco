__FILENAME__ = cache
# -*- coding: utf-8 -*-
import sys
from . import __version__ as bf_version


class Cache(dict):
    """A cache object used for attatching things we want to remember

    This works like a normal object, attributes that are undefined
    raise an AttributeError

    >>> c = Cache()
    >>> c.whatever = "whatever"
    >>> c.whatever
    'whatever'
    >>> c.section.subsection.attribute = "whatever"
    Traceback (most recent call last):
      ...
    AttributeError: 'Cache' object has no attribute 'section'
    """
    def __init__(self, **kw):
        dict.__init__(self, kw)
        self.__dict__ = self


class HierarchicalCache(Cache):
    """A cache object used for attatching things we want to remember

    This works differently than a normal object, attributes that
    are undefined do *not* raise an AttributeError but are silently
    created as an additional HierarchicalCache object.

    >>> c = HierarchicalCache()
    >>> c.whatever = "whatever"
    >>> c.whatever
    'whatever'
    >>> c.section.subsection.attribute = "whatever"
    >>> c.section.subsection.attribute
    'whatever'
    >>> c.sub.d['one'].value.stuff = "whatever"
    >>> c.sub.d.one.value.stuff
    'whatever'
    >>> c.sub.d['one'].value.stuff
    'whatever'
    >>> c.sub.d['one.value.stuff']
    'whatever'
    >>> c.sub.d['one.value.stuff'] = "whatever2"
    >>> c.sub.d.one.value.stuff
    'whatever2'
    >>> list(c.sub.d.one.value.items())
    [('stuff', 'whatever2')]
    >>> "doesn't have this" in c.sub.d
    False
    """
    def __getattr__(self, attr):
        if not attr.startswith("_") and \
                "(" not in attr and \
                "[" not in attr and \
                attr != "trait_names":
            c = HierarchicalCache()
            Cache.__setitem__(self, attr, c)
            return c
        else:
            raise AttributeError

    def __getitem__(self, item):
        if(type(item) == slice or not hasattr(item, "split")):
            raise TypeError("HierarchicalCache objects are not indexable nor "
                            "sliceable. If you were expecting another object "
                            "here, a parent cache object may be inproperly "
                            "configured.")
        dotted_parts = item.split(".")
        try:
            c = self.__getattribute__(dotted_parts[0])
        except AttributeError:
            c = self.__getattr__(item)
        for dotted_part in dotted_parts[1:]:
            c = getattr(c, dotted_part)
        return c

    def __call__(self):
        raise TypeError("HierarchicalCache objects are not callable. If "
                        "you were expecting this to be a method, a "
                        "parent cache object may be inproperly configured.")

    def __setitem__(self, key, item):
        c = self
        try:
            try:
                dotted_parts = key.split(".")
            except AttributeError:
                return
            if len(dotted_parts) > 1:
                c = self.__getitem__(".".join(dotted_parts[:-1]))
                key = dotted_parts[-1]
        finally:
            Cache.__setitem__(c, key, item)

#The main blogofile cache object, transfers state between templates
bf = HierarchicalCache()


def setup_bf():
    global bf
    sys.modules['blogofile_bf'] = bf
    bf.__version__ = bf_version
    bf.cache = sys.modules['blogofile.cache']


def reset_bf(assign_modules=True):
    global bf
    bf.clear()
    setup_bf()

    if assign_modules:
        from . import config, util, server, filter, controller, template
        bf.config = config
        bf.util = util
        bf.server = server
        bf.filter = filter
        bf.controller = controller
        bf.template = template
    return bf

setup_bf()

########NEW FILE########
__FILENAME__ = config
# -*- coding: utf-8 -*-
"""Load the default config, and the user's _config.py file, and
provides the interface to the config.
"""

__author__ = "Ryan McGuire (ryan@enigmacurry.com)"

import os
import logging
import sys
import re
from . import cache
from . import controller
from . import plugin
from . import filter as _filter
from .cache import HierarchicalCache as HC
# TODO: This import MUST come after cache is imported; that's too brittle!
import blogofile_bf as bf


logger = logging.getLogger("blogofile.config")

bf.config = sys.modules['blogofile.config']

site = cache.HierarchicalCache()
controllers = cache.HierarchicalCache()
filters = cache.HierarchicalCache()
plugins = cache.HierarchicalCache()
templates = cache.HierarchicalCache()

default_config_path = os.path.join(
    os.path.dirname(__file__), "default_config.py")


def init_interactive(args=None):
    """Reset the blogofile cache objects, and load the configuration.

    The user's _config.py is always loaded from the current directory
    because we assume that the function/method that calls this has
    already changed to the directory specified by the --src-dir
    command line option.
    """
    # TODO: What purpose does cache.reset_bf() serve? Looks like a
    # testing hook.
    cache.reset_bf()
    try:
        _load_config("_config.py")
    except IOError:
        sys.stderr.write("No configuration found in source dir: {0}\n"
                         .format(args.src_dir))
        sys.stderr.write("Want to make a new site? Try `blogofile init`\n")
        sys.exit(1)


def _load_config(user_config_path):
    """Load the configuration.

    Strategy:

      1) Load the default config
      2) Load the plugins
      3) Load the site filters and controllers
      4) Load the user's config.
      5) Compile file ignore pattern regular expressions

    This establishes sane defaults that the user can override as they
    wish.

    config is exec-ed from Python modules into locals(), then updated
    into globals().
    """
    with open(default_config_path) as f:
        exec(f.read())
    plugin.load_plugins()
    _filter.preload_filters()
    controller.load_controllers(namespace=bf.config.controllers)
    try:
        with open(user_config_path) as f:
            exec(f.read())
    except IOError:
        raise
    _compile_file_ignore_patterns()
    globals().update(locals())


def _compile_file_ignore_patterns():
    site.compiled_file_ignore_patterns = []
    for p in site.file_ignore_patterns:
        if hasattr(p, "findall"):
            # probably already a compiled regex.
            site.compiled_file_ignore_patterns.append(p)
        else:
            site.compiled_file_ignore_patterns.append(
                re.compile(p, re.IGNORECASE))

########NEW FILE########
__FILENAME__ = controller
# -*- coding: utf-8 -*-
"""Controllers

Blogofile controllers reside in the user's _controllers directory
and can generate content for a site.

Controllers can either be standalone .py files, or they can be modules.

Every controller has a contract to provide the following:
 * a run() method, which accepts no arguments.
 * A dictionary called "config" containing the following information:
   * name - The human friendly name for the controller.
   * author - The name or group responsible for writing the controller.
   * description - A brief description of what the controller does.
   * url - The URL where the controller is hosted.
   * priority - The default priority to determine sequence of execution
      This is optional, if not provided, it will default to 50.
      Controllers with higher priorities get run sooner than ones with
      lower priorities.

Example controller (either a standalone .py file or
                      __init__.py inside a module):

    meta = {
        "name"        : "My Controller",
        "description" : "Does cool stuff",
        "author"      : "Joe Programmer",
        "url"         : "http://www.yoururl.com/my-controller"
        }

    config = {"some_config_option" : "some_default_setting",
              "priority" : 90.0}

    def run():
        do_whatever_it_needs_to()

Users can configure a controller in _config.py:

  #To enable the controller (default is always disabled):
  controller.name_of_controller.enabled = True

  #To set the priority:
  controllers.name_of_controller.priority = 40

  #To set a controller specific setting:
  controllers.name_of_controller.some_config_option = "whatever"

Settings set in _config.py always override any default configuration
for the controller.
"""
from __future__ import print_function
import sys
import os
import operator
import logging
import imp

from .cache import bf


bf.controller = sys.modules['blogofile.controller']

logger = logging.getLogger("blogofile.controller")

default_controller_config = {"priority": 50.0,
                             "enabled": False}


def __find_controller_names(directory="_controllers"):
    if(not os.path.isdir(directory)):
        return
    # Find all the standalone .py files and modules in the _controllers dir
    for fn in os.listdir(directory):
        p = os.path.join(directory, fn)
        if os.path.isfile(p):
            if fn.endswith(".py"):
                yield fn[:-3]
        elif os.path.isdir(p):
            if os.path.isfile(os.path.join(p, "__init__.py")):
                yield fn


def init_controllers(namespace):
    """Controllers have an optional init method that runs before the run
    method"""
    # Prune the configured controllers to only those that have a
    # discoverable implementation:
    actual_controllers = {}
    for name, controller in namespace.items():
        if "mod" in controller and type(controller.mod).__name__ == "module":
            actual_controllers[name] = controller
        elif "enabled" in controller and controller.enabled:
            # Throw a fatal error if an enabled controller is unimplemented
            print("Cannot find requested controller: {0}".format(name))
            print("Build aborted.")
            sys.exit(1)
    # Initialize all the actual controllers:
    for name, controller in sorted(actual_controllers.items(),
            key=lambda c: c[1].priority):
        if not controller.mod.__initialized:
            try:
                init_method = controller.mod.init
            except AttributeError:
                controller.mod.__initialized = True
                continue
            else:
                init_method()


def load_controller(name, namespace, directory="_controllers", defaults={},
                    is_plugin=False):
    """Load a single controller by name.
    """
    logger.debug("loading controller: {0}"
                 .format(bf.util.path_join(directory, name)))
    # Don't generate pyc files in the _controllers directory
    try:
        initial_dont_write_bytecode = sys.dont_write_bytecode
    except KeyError:
        initial_dont_write_bytecode = False
    try:
        try:
            sys.dont_write_bytecode = True
            controller = imp.load_module(
                name, *imp.find_module(name, [directory]))
            controller.__initialized = False
            logger.debug("found controller: {0} - {1}"
                         .format(name, controller))
        except (ImportError,) as e:
            logger.error(
                "Cannot import controller : {0} ({1})".format(name, e))
            raise
        # Remember the actual imported module
        namespace[name].mod = controller
        # Load the blogofile defaults for controllers:
        for k, v in list(default_controller_config.items()):
            namespace[name][k] = v
        # Load provided defaults:
        for k, v in list(defaults.items()):
            namespace[name][k] = v
        if not is_plugin:
            # Load any of the controller defined defaults:
            try:
                controller_config = getattr(controller, "config")
                for k, v in list(controller_config.items()):
                    if "." in k:
                        # This is a hierarchical setting
                        tail = namespace[name]
                        parts = k.split(".")
                        for part in parts[:-1]:
                            tail = tail[part]
                        tail[parts[-1]] = v
                    if k == "enabled" and v is True:
                        # Controller default value can't turn itself
                        # on, but it can turn itself off.
                        pass
                    if k == "mod":
                        # Don't ever redefine the module reference
                        pass
                    else:
                        namespace[name][k] = v
            except AttributeError:
                pass
        # Provide every controller with a logger:
        c_logger = logging.getLogger("blogofile.controllers." + name)
        namespace[name]["logger"] = c_logger
        return namespace[name].mod
    finally:
        # Reset the original sys.dont_write_bytecode setting when we're done
        sys.dont_write_bytecode = initial_dont_write_bytecode


def load_controllers(namespace, directory="_controllers", defaults={}):
    """Find all the controllers in the _controllers directory and
    import them into the bf context.
    """
    for name in __find_controller_names(directory):
        load_controller(name, namespace, directory, defaults)


def defined_controllers(namespaces, only_enabled=True):
    """Find all the enabled controllers in order of priority

    if only_enabled == False, find all controllers, regardless of
    their enabled status

    >>> bf_test = bf.cache.HierarchicalCache()
    >>> bf_test.controllers.one.enabled = True
    >>> bf_test.controllers.one.priority = 30
    >>> bf_test.controllers.two.enabled = False
    >>> bf_test.controllers.two.priority = 90
    >>> bf_test.controllers.three.enabled = True
    >>> bf_test.controllers.three.priority = 50
    >>> bf_test2 = bf.cache.HierarchicalCache()
    >>> bf_test2.controllers.one.enabled = True
    >>> bf_test2.controllers.one.priority = 100
    >>> c = defined_controllers((bf_test2,))
    >>> c == [bf_test2.controllers.one]
    True
    >>> c = defined_controllers((bf_test,bf_test2))
    >>> c == [bf_test2.controllers.one, bf_test.controllers.three, bf_test.controllers.one]
    True
    """
    controllers = []
    for namespace in namespaces:
        for c in list(namespace.controllers.values()):
            # Get only the ones that are enabled:
            if "enabled" not in c or c['enabled'] is False:
                # The controller is disabled
                if only_enabled:
                    continue
            controllers.append(c)
    # Sort the controllers by priority
    return [x for x in sorted(controllers,
                              key=operator.attrgetter("priority"),
                              reverse=True)]


def run_all(namespaces):
    """Run each controller in priority order.
    """
    # Get the controllers in priority order:
    controllers = defined_controllers(namespaces)
    # Temporarily add _controllers directory onto sys.path
    for c in controllers:
        if "run" in dir(c.mod):
            logger.info("running controller (priority {0}): {1}"
                        .format(c.priority, c.mod.__file__))
            c.mod.run()
        else:
            logger.debug(
                "controller {0} has no run() method, skipping it.".format(c))

########NEW FILE########
__FILENAME__ = default_config
######################################################################
# This is the main Blogofile configuration file.
# www.Blogofile.com
#
# This is the canonical _config.py with every single default setting.
#
# Don't edit this file directly; create your own _config.py (from
# scratch or using 'blogofile init') and your settings will override
# these defaults.
#
######################################################################

######################################################################
# Basic Settings
#  (almost all sites will want to configure these settings)
######################################################################
## site.url -- Your site's full URL
# Your "site" is the same thing as your _site directory.
#  If you're hosting a blogofile powered site as a subdirectory of a larger
#  non-blogofile site, then you would set the site_url to the full URL
#  including that subdirectory: "http://www.yoursite.com/path/to/blogofile-dir"
site.url = "http://www.example.com"

## site.author -- Your name, the author of the website.
# This is optional. If set to anything other than None, the
# simple_blog template creates a meta tag for the site author.
site.author = None

######################################################################
# Advanced Settings
######################################################################
# Use hard links when copying files. This saves disk space and shortens
# the time to build sites that copy lots of static files.
# This is turned off by default though, because hard links are not
# necessarily what every user wants.
site.use_hard_links = False
#Warn when we're overwriting a file?
site.overwrite_warning = True
# These are the default ignore patterns for excluding files and dirs
# from the _site directory
# These can be strings or compiled patterns.
# Strings are assumed to be case insensitive.
site.file_ignore_patterns = [
    # All files that start with an underscore
    ".*/_.*",
    # Emacs autosave files
    ".*/#.*",
    # Emacs/Vim backup files
    ".*~$",
    # Vim swap files
    ".*/\..*\.swp$",
    # VCS directories
    ".*/\.(git|hg|svn|bzr)$",
    # Git and Mercurial ignored files definitions
    ".*/.(git|hg)ignore$",
    # CVS dir
    ".*/CVS$",
    ]

from blogofile.template import MakoTemplate, JinjaTemplate, \
    MarkdownTemplate, RestructuredTextTemplate, TextileTemplate
#The site base template filename:
site.base_template = "site.mako"
#Template engines mapped to file extensions:
templates.engines = HC(
    mako = MakoTemplate,
    jinja = JinjaTemplate,
    jinja2 = JinjaTemplate,
    markdown = MarkdownTemplate,
    rst = RestructuredTextTemplate,
    textile = TextileTemplate
    )

#Template content blocks:
templates.content_blocks = HC(
    mako = HC(
        pattern = re.compile("\${\W*next.body\(\)\W*}"),
        replacement = "${next.body()}"
        ),
    jinja2 = HC(
        pattern = re.compile("{%\W*block content\W*%}.*?{%\W*endblock\W*%}", re.MULTILINE|re.DOTALL),
        replacement = "{% block content %} {% endblock %}"
        ),
    filter = HC(
        pattern = re.compile("_^"), #Regex that matches nothing
        replacement = "~~!`FILTER_CONTENT_HERE`!~~",
        default_chains = HC(
            markdown = "syntax_highlight, markdown",
            rst = "syntax_highlight, rst"
            )
        )
    )

### Pre/Post build hooks:
def pre_build():
    #Do whatever you want before the _site is built.
    pass

def post_build():
    #Do whatever you want after the _site is built successfully.
    pass

def build_exception():
    #Do whatever you want if there is an unrecoverable error in building the site.
    pass

def build_finally():
    #Do whatever you want after the _site is built successfully OR after a fatal error
    pass

########NEW FILE########
__FILENAME__ = exception
# -*- coding: utf-8 -*-


class FilterNotLoaded(Exception):
    pass

########NEW FILE########
__FILENAME__ = filter
# -*- coding: utf-8 -*-
from __future__ import print_function
import sys
import os
import logging
import imp
import uuid


logger = logging.getLogger("blogofile.filter")

from .cache import bf
from .cache import HierarchicalCache
from . import exception

bf.filter = sys.modules['blogofile.filter']

default_filter_config = {"name": None,
                         "description": None,
                         "author": None,
                         "url": None}


def run_chain(chain, content):
    """Run content through a filter chain.

    Works with either a string or a sequence of filters
    """
    if chain is None:
        return content
    # lib3to2 interprets str as meaning unicode instead of basestring,
    # hand craft the translation to python2:
    if sys.version_info >= (3,):
        is_str = eval("isinstance(chain, str)")
    else:
        is_str = eval("isinstance(chain, basestring)")
    if is_str:
        chain = parse_chain(chain)
    for fn in chain:
        f = get_filter(fn)
        logger.debug("Applying filter: " + fn)
        content = f.run(content)
    logger.debug("Content: " + content)
    return content


def parse_chain(chain):
    """Parse a filter chain into a sequence of filters.
    """
    parts = []
    for p in chain.split(","):
        p = p.strip()
        if p.lower() == "none":
            continue
        if len(p) > 0:
            parts.append(p)
    return parts


def preload_filters(namespace=None, directory="_filters"):
    """Find all the standalone .py files and modules in the directory
    specified and load them into namespace specified.
    """
    if namespace is None:
        namespace = bf.config.filters
    if(not os.path.isdir(directory)):
        return
    for fn in os.listdir(directory):
        p = os.path.join(directory, fn)
        if (os.path.isfile(p) and fn.endswith(".py")):
            # Load a single .py file:
            load_filter(fn[:-3], module_path=p, namespace=namespace)
        elif (os.path.isdir(p)
              and os.path.isfile(os.path.join(p, "__init__.py"))):
            # Load a package:
            load_filter(fn, module_path=p, namespace=namespace)


def init_filters(namespace=None):
    """Filters have an optional init method that runs before the site
    is built.
    """
    if namespace is None:
        namespace = bf.config.filters
    for name, filt in list(namespace.items()):
        if "mod" in filt \
                and type(filt.mod).__name__ == "module"\
                and not filt.mod.__initialized:
            try:
                init_method = filt.mod.init
            except AttributeError:
                filt.mod.__initialized = True
                continue
            logger.debug("Initializing filter: " + name)
            init_method()
            filt.mod.__initialized = True


def get_filter(name, namespace=None):
    """Return an already loaded filter.
    """
    if namespace is None:
        if name.startswith("bf") and "." in name:
            # Name is an absolute reference to a filter in a given
            # namespace; extract the namespace
            namespace, name = name.rsplit(".", 1)
            namespace = eval(namespace)

        else:
            namespace = bf.config.filters
    if name in namespace and "mod" in namespace[name]:
        logger.debug("Retrieving already loaded filter: " + name)
        return namespace[name]['mod']
    else:
        raise exception.FilterNotLoaded("Filter not loaded: {0}".format(name))


def load_filter(name, module_path, namespace=None):
    """Load a filter from the site's _filters directory.
    """
    if namespace is None:
        namespace = bf.config.filters
    try:
        initial_dont_write_bytecode = sys.dont_write_bytecode
    except KeyError:
        initial_dont_write_bytecode = False
    try:
        # Don't generate .pyc files in the _filters directory
        sys.dont_write_bytecode = True
        if module_path.endswith(".py"):
            mod = imp.load_source(
                "{0}_{1}".format(name, uuid.uuid4()), module_path)
        else:
            mod = imp.load_package(
                "{0}_{1}".format(name, uuid.uuid4()), module_path)
        logger.debug("Loaded filter for first time: {0}".format(module_path))
        mod.__initialized = False
        # Overwrite anything currently in this namespace:
        try:
            del namespace[name]
        except KeyError:
            pass
        # If the filter defines it's own configuration, use that as
        # it's own namespace:
        if hasattr(mod, "config") and \
                isinstance(mod.config, HierarchicalCache):
            namespace[name] = mod.config
        # Load the module into the namespace
        namespace[name].mod = mod
        # If the filter has any aliases, load those as well
        try:
            for alias in mod.config['aliases']:
                namespace[alias] = namespace[name]
        except:
            pass
        # Load the default blogofile config for filters:
        for k, v in list(default_filter_config.items()):
            namespace[name][k] = v
        # Load any filter defined defaults:
        try:
            filter_config = getattr(mod, "config")
            for k, v in list(filter_config.items()):
                if "." in k:
                    # This is a hierarchical setting
                    tail = namespace[name]
                    parts = k.split(".")
                    for part in parts[:-1]:
                        tail = tail[part]
                    tail[parts[-1]] = v
                else:
                    namespace[name][k] = v
        except AttributeError:
            pass
        return mod
    except:
        logger.error("Cannot load filter: " + name)
        raise
    finally:
        # Reset the original sys.dont_write_bytecode setting where we're done
        sys.dont_write_bytecode = initial_dont_write_bytecode


def list_filters(args):
    from . import config, plugin
    config.init_interactive()
    plugin.init_plugins()
    # module path -> list of aliases
    filters = {}
    for name, filt in bf.config.filters.items():
        if "mod" in filt:
            aliases = filters.get(filt.mod.__file__, [])
            aliases.append(name)
            filters[filt.mod.__file__] = aliases
    for mod_path, aliases in filters.items():
        print("{0} - {1}\n".format(", ".join(aliases), mod_path))

########NEW FILE########
__FILENAME__ = main
# -*- coding: utf-8 -*-
"""This is Blogofile -- http://www.Blogofile.com

Please take a moment to read LICENSE.txt. It's short.
"""
from __future__ import print_function

__author__ = "Ryan McGuire (ryan@enigmacurry.com)"

import argparse
import locale
import logging
import os
import shutil
import sys
import time
import platform

from . import __version__
from . import server
from . import config
from . import util
from . import filter as _filter
from . import plugin
from .cache import bf
from .writer import Writer


locale.setlocale(locale.LC_ALL, '')

logging.basicConfig()
logger = logging.getLogger("blogofile")
bf.logger = logger


def main(argv=[]):
    """Blogofile entry point.

    Set up command line parser, parse args, and dispatch to
    appropriate function. Print help and exit if there are too few args.

    :arg argv: List of command line arguments. Non-empty list facilitates
               integration tests.
    :type argv: list
    """
    do_debug()
    argv = argv or sys.argv
    parser, subparsers = setup_command_parser()
    if len(argv) == 1:
        parser.print_help()
        parser.exit(2)
    else:
        args = parser.parse_args(argv[1:])
        set_verbosity(args)
        if args.func == do_help:
            do_help(args, parser, subparsers)
        else:
            args.func(args)


def do_debug():
    """Run blogofile in debug mode depending on the BLOGOFILE_DEBUG environment
    variable:
    If set to "ipython" just start up an embeddable ipython shell at bf.ipshell
    If set to anything else besides 0, setup winpdb environment
    """
    try:
        if os.environ['BLOGOFILE_DEBUG'] == "ipython":
            from IPython.Shell import IPShellEmbed
            bf.ipshell = IPShellEmbed()
        elif os.environ['BLOGOFILE_DEBUG'] != "0":
            print("Running in debug mode, waiting for debugger to connect. "
                  "Password is set to 'blogofile'")
            import rpdb2
            rpdb2.start_embedded_debugger("blogofile")
    except KeyError:
        # Not running in debug mode
        pass


def setup_command_parser():
    """Set up the command line parser, and the parsers for the sub-commands.
    """
    parser_template = _setup_parser_template()
    parser = argparse.ArgumentParser(parents=[parser_template])
    subparsers = parser.add_subparsers(title='sub-commands')
    _setup_help_parser(subparsers)
    _setup_init_parser(subparsers)
    _setup_build_parser(subparsers)
    _setup_serve_parser(subparsers)
    _setup_info_parser(subparsers)
    _setup_plugins_parser(subparsers, parser_template)
    _setup_filters_parser(subparsers)
    return parser, subparsers


def _setup_parser_template():
    """Return the parser template that other parser are based on.
    """
    parser_template = argparse.ArgumentParser(add_help=False)
    parser_template.add_argument(
        "--version", action="version",
        version="Blogofile {0} -- http://www.blogofile.com -- {1} {2}"
        .format(__version__, platform.python_implementation(),
                platform.python_version()))
    parser_template.add_argument(
        "-v", "--verbose", dest="verbose", action="store_true",
        help="Be verbose")
    parser_template.add_argument(
        "-vv", "--veryverbose", dest="veryverbose", action="store_true",
        help="Be extra verbose")
    defaults = {
        "src_dir": os.curdir,
        "verbose": False,
        "veryverbose": False,
    }
    parser_template.set_defaults(**defaults)
    return parser_template


def _setup_help_parser(subparsers):
    """Set up the parser for the help sub-command.
    """
    parser = subparsers.add_parser(
        "help", add_help=False,
        help="Show help for a command.")
    parser.add_argument(
        "command", nargs="*",
        help="a Blogofile subcommand e.g. build")
    parser.set_defaults(func=do_help)
    defaults = {
        'command': None,
        'func': do_help,
    }
    parser.set_defaults(**defaults)


def _setup_init_parser(subparsers):
    """Set up the parser for the init sub-command.
    """
    parser = subparsers.add_parser(
        "init",
        help="Create a new blogofile site.")
    parser.add_argument(
        "src_dir",
        help="""
            Your site's source directory.
            It will be created if it doesn't exist, as will any necessary
            parent directories.
            """)
    parser.add_argument(
        "plugin", nargs="?",
        help="""
            Plugin to initialize site from.
            The plugin must already be installed;
            use `blogofile plugins list` to get the list of installed plugins.
            If omitted, a bare site directory will be created.
            """)
    defaults = {
        "plugin": None,
        "func": do_init,
    }
    parser.set_defaults(**defaults)


def _setup_build_parser(subparsers):
    """Set up the parser for the build sub-command.
    """
    parser = subparsers.add_parser(
        "build",
        help="Build the site from source.")
    parser.add_argument(
        "-s", "--src-dir", dest="src_dir", metavar="DIR",
        help="Your site's source directory (default is current directory)")
    defaults = {
        "src_dir": os.curdir,
        "func": do_build,
    }
    parser.set_defaults(**defaults)


def _setup_serve_parser(subparsers):
    """Set up the parser for the serve sub-command.
    """
    parser = subparsers.add_parser(
        "serve",
        help="""
            Host the _site dir with the builtin webserver.
            Useful for quickly testing your site.
            Not for production use!
            """)
    parser.add_argument(
        "PORT", nargs="?",
        help="TCP port to use; defaults to %(default)s")
    parser.add_argument(
        "IP_ADDR", nargs="?",
        help="""
            IP address to bind to. Defaults to loopback only
            (%(default)s). 0.0.0.0 binds to all network interfaces,
            please be careful!.
            """)
    parser.add_argument(
        "-s", "--src-dir", dest="src_dir", metavar="DIR",
        help="Your site's source directory (default is current directory)")
    defaults = {
        "PORT": "8080",
        "IP_ADDR": "127.0.0.1",
        "src_dir": os.curdir,
        "func": do_serve,
    }
    parser.set_defaults(**defaults)


def _setup_info_parser(subparsers):
    """Set up the parser for the info sub-command.
    """
    parser = subparsers.add_parser(
        "info",
        help="""
            Show information about the
            Blogofile installation and the current site.
            """)
    parser.add_argument(
        "-s", "--src-dir", dest="src_dir", metavar="DIR",
        help="Your site's source directory (default is current directory)")
    defaults = {
        "src_dir": os.curdir,
        "func": do_info,
    }
    parser.set_defaults(**defaults)


def _setup_plugins_parser(subparsers, parser_template):
    """Set up the parser for the plugins sub-command.
    """
    parser = subparsers.add_parser(
        "plugins",
        help="Plugin tools")
    plugin_subparsers = parser.add_subparsers()
    plugins_list = plugin_subparsers.add_parser(
        "list",
        help="List all of the plugins installed")
    plugins_list.set_defaults(func=plugin.list_plugins)
    for p in plugin.iter_plugins():
        # Setup the plugin command parser, if it has one
        try:
            plugin_parser_setup = p.__dist__['command_parser_setup']
        except KeyError:
            continue
        plugin_parser = subparsers.add_parser(
            p.__dist__['config_name'],
            help="Plugin: " + p.__dist__['description'])
        plugin_parser.add_argument(
            "--version", action="version",
            version="{name} plugin {version} by {author} -- {url}"
            .format(**p.__dist__))
        plugin_parser_setup(plugin_parser, parser_template)


def _setup_filters_parser(subparsers):
    """Set up the parser for the filters sub-command.
    """
    parser = subparsers.add_parser(
        "filters",
        help="Filter tools")
    filter_subparsers = parser.add_subparsers()
    filters_list = filter_subparsers.add_parser(
        "list",
        help="List all the filters installed")
    filters_list.set_defaults(func=_filter.list_filters)


def set_verbosity(args):
    """Set verbosity level for logging as requested on command line.
    """
    if args.verbose:
        logger.setLevel(logging.INFO)
        logger.info("Setting verbose mode")
    if args.veryverbose:
        logger.setLevel(logging.DEBUG)
        logger.info("Setting very verbose mode")


def do_help(args, parser, subparsers):
    if "commands" in args.command:
        args.command = sorted(subparsers.choices.keys())

    if not args.command:
        parser.print_help()
        print("\nSee 'blogofile help COMMAND' for more information"
              " on a specific command.")
    else:
        # Where did the subparser help text go? Let's get it back.
        # Certainly there is a better way to retrieve the helptext than this...
        helptext = {}
        for subcommand in args.command:
            for action in subparsers._choices_actions:
                if action.dest == subcommand:
                    helptext[subcommand] = action.help
                    break
            else:
                helptext[subcommand] = ""

        # Print help for each subcommand requested.
        for subcommand in args.command:
            sys.stderr.write("{0} - {1}\n"
                             .format(subcommand, helptext[subcommand]))
            parser = subparsers.choices[subcommand]
            parser.print_help()
            sys.stderr.write("\n")
            # Perform any extra help tasks:
            if hasattr(parser, "extra_help"):
                parser.extra_help()


def do_init(args):
    """Initialize a new blogofile site.
    """
    # Look before we leap because _init_plugin_site uses
    # shutil.copytree() which requires that the src_dir not already
    # exist
    if os.path.exists(args.src_dir):
        print(
            "{0.src_dir} already exists; initialization aborted"
            .format(args),
            file=sys.stderr)
        sys.exit(1)
    if args.plugin is None:
        _init_bare_site(args.src_dir)
    else:
        _init_plugin_site(args)


def _init_bare_site(src_dir):
    """Initialize the site directory as a bare (do-it-yourself) site.

    Write a minimal _config.py file and a message to the user.
    """
    bare_site_config = [
        "# -*- coding: utf-8 -*-\n",
        "# This is a minimal blogofile config file.\n",
        "# See the docs for config options\n",
        "# or run `blogofile help init` to learn how to initialize\n",
        "# a site from a plugin.\n",
    ]
    os.makedirs(src_dir)
    new_config_path = os.path.join(src_dir, '_config.py')
    with open(new_config_path, 'wt') as new_config:
        new_config.writelines(bare_site_config)
    print("_config.py for a bare (do-it-yourself) site "
          "written to {0}\n"
          "If you were expecting more, please see `blogofile init -h`"
          .format(src_dir))


def _init_plugin_site(args):
    """Initialize the site directory with the approprate files from an
    installed blogofile plugin.

    Copy everything except the _controllers, _filters, and _templates
    directories from the plugin's site_src directory.
    """
    p = plugin.get_by_name(args.plugin)
    if p is None:
        print("{0.plugin} plugin not installed; initialization aborted\n\n"
              "installed plugins:".format(args),
              file=sys.stderr)
        plugin.list_plugins(args)
        return
    plugin_path = os.path.dirname(os.path.realpath(p.__file__))
    site_src = os.path.join(plugin_path, 'site_src')
    ignore_dirs = shutil.ignore_patterns(
        '_controllers', '_filters')
    shutil.copytree(site_src, args.src_dir, ignore=ignore_dirs)
    print("{0.plugin} plugin site_src files written to {0.src_dir}"
          .format(args))


def do_build(args, load_config=True):
    _validate_src_dir(args.src_dir)
    if load_config:
        config.init_interactive(args)
    output_dir = util.path_join("_site", util.fs_site_path_helper())
    writer = Writer(output_dir=output_dir)
    logger.debug("Running user's pre_build() function...")
    config.pre_build()
    try:
        writer.write_site()
        logger.debug("Running user's post_build() function...")
        config.post_build()
    except:
        logger.error(
            "Fatal build error occured, calling bf.config.build_exception()")
        config.build_exception()
        raise
    finally:
        logger.debug("Running user's build_finally() function...")
        config.build_finally()


def _validate_src_dir(src_dir):
    """Confirm that `src_dir` exists, and contains a `_config.py` file.

    If so, make `src_dir` the working directory.
    """
    if not os.path.isdir(src_dir):
        print("source dir does not exist: {0}".format(src_dir))
        sys.exit(1)
    if not os.path.isfile(os.path.join(src_dir, "_config.py")):
        print("source dir does not contain a _config.py file")
        sys.exit(1)
    os.chdir(src_dir)


def do_serve(args):
    _validate_src_dir(args.src_dir)
    config.init_interactive(args)
    bfserver = server.Server(args.PORT, args.IP_ADDR)
    bfserver.start()
    while not bfserver.is_shutdown:
        try:
            time.sleep(0.5)
        except KeyboardInterrupt:
            bfserver.shutdown()


def do_info(args):
    """Print some information about the Blogofile installation and the
    current site.
    """
    print("This is Blogofile (version {0}) -- http://www.blogofile.com"
          .format(__version__))
    print("You are using {0} {1} from {2}".format(
        platform.python_implementation(), platform.python_version(),
        sys.executable))
    print("Blogofile is installed at: {0}".format(os.path.split(__file__)[0]))
    # Show _config.py paths
    print(("Default config file: {0}".format(config.default_config_path)))
    if os.path.isfile(os.path.join(args.src_dir, "_config.py")):
        print("Found site _config.py: {0}"
              .format(os.path.abspath("_config.py")))
    else:
        print(
            "The specified directory has no _config.py, and cannot be built.")

########NEW FILE########
__FILENAME__ = plugin
# -*- coding: utf-8 -*-
from __future__ import print_function
import logging
import os
import os.path
import pkg_resources
import sys
from mako.lookup import TemplateLookup
import six
from . import controller
from . import filter as _filter
from . import template
from .cache import bf
from .cache import HierarchicalCache


logger = logging.getLogger("blogofile.plugin")

default_plugin_config = {
    "priority": 50.0,
    "enabled": False,
    }

reserved_attributes = ["mod", "filters", "controllers", "site_src"]


def iter_plugins():
    for plugin in pkg_resources.iter_entry_points("blogofile.plugins"):
        yield plugin.load()


def get_by_name(name):
    for plugin in iter_plugins():
        if plugin.__dist__['config_name'] == name:
            return plugin


def list_plugins(args):
    for plugin in iter_plugins():
        print("{0} ({1}) - {2} - {3}".format(plugin.__dist__['config_name'],
                                             plugin.__dist__['version'],
                                             plugin.__dist__['description'],
                                             plugin.__dist__['author']))


def check_plugin_config(module):
    """Ensure that a plugin has the required components
    and none of the reserved ones.
    """
    try:
        assert isinstance(module.config, HierarchicalCache)
    except AttributeError:
        raise AssertionError("Plugin {0} has no config HierarchicalCache"
                             .format(module))
    except AssertionError:
        raise AssertionError("Plugin {0} config object must extend from "
                             "HierarchicalCache".format(module))
    try:
        module.__dist__
    except AttributeError:
        raise AssertionError("Plugin {0} has no __dist__ dictionary, "
                             "describing the plugins metadata.".format(module))
    #TODO: Why does this fail in a test context? Not really *that* important..
    # for attr in reserved_attributes:
    #     if module.config.has_key(attr):
    #         raise AssertionError, "'{0}' is a reserved attribute name for " \
    #             "Blogofile plugins. They should not be assigned manually."\
    #             .format(attr)


def load_plugins():
    """Discover all the installed plugins and load them into bf.config.plugins

    Load the module itself, the controllers, and the filters.
    """
    for plugin in iter_plugins():
        namespace = bf.config.plugins[plugin.__dist__["config_name"]] = \
            getattr(plugin, "config")
        check_plugin_config(plugin)
        namespace.mod = plugin
        plugin_dir = os.path.dirname(sys.modules[plugin.__name__].__file__)
        # Load filters
        _filter.preload_filters(
            namespace=namespace.filters,
            directory=os.path.join(plugin_dir, "site_src", "_filters"))
        # Load controllers
        controller.load_controllers(
            namespace=namespace.controllers,
            directory=os.path.join(plugin_dir, "site_src", "_controllers"),
            defaults={"enabled": True})


def init_plugins():
    for name, plugin in list(bf.config.plugins.items()):
        if plugin.enabled:
            if "mod" not in plugin:
                print("Cannot find requested plugin: {0}".format(name))
                print("Build aborted.")
                sys.exit(1)
            logger.info("Initializing plugin: {0}".format(
                    plugin.mod.__dist__['config_name']))
            plugin.mod.init()
            for name, filter_ns in list(plugin.filters.items()):
                # Filters from plugins load in their own namespace, but
                # they also load in the regular filter namespace as long as
                # there isn't already a filter with that name. User filters
                # from the _filters directory are loaded after plugins, so
                # they are overlaid on top of these values and take
                # precedence.
                if name not in bf.config.filters:
                    bf.config.filters[name] = filter_ns
                elif "mod" not in bf.config.filters[name]:
                    filter_ns.update(bf.config.filters[name])
                    bf.config.filters[name] = filter_ns


class PluginTools(object):
    """Tools for a plugin to get information about it's runtime environment.
    """
    def __init__(self, module):
        self.module = module
        self.namespace = self.module.config
        self.template_lookup = self._template_lookup()
        self.logger = logging.getLogger(
            "blogofile.plugins.{0}".format(self.module.__name__))

    def _template_lookup(self):
        return TemplateLookup(
            directories=[
                "_templates", os.path.join(self.get_src_dir(), "_templates")],
            input_encoding='utf-8', output_encoding='utf-8',
            encoding_errors='replace')

    def get_src_dir(self):
        """Return the plugin's :file:`site_src directory path.

        :returns: :file:`site_src` path for the plugin.
        :rtype: str
        """
        return os.path.join(os.path.dirname(self.module.__file__), "site_src")

    def materialize_template(self, template_name, location, attrs={}):
        """Materialize a template using the plugin's TemplateLookup
        instance.

        :arg template_name: File name of the template to materialize.
        :type template_name: str

        :arg location: Path and file name in the :file:`_site`
                       directory to render the template to.
        :type location: str

        :arg attrs: Template variable names and values that will be
                    used as the data context to render the template
                    with.
        :type attrs: dict
        """
        template.materialize_template(
            template_name, location, attrs=attrs,
            lookup=self.template_lookup, caller=self.module)

    def add_template_dir(self, path, append=True):
        """Add a template directory to the plugin's TemplateLookup
        instance directories list.

        :arg path: Template path to add to directories list.
        :type path: str

        :arg append: Add the template path to the end of the
                     directories list when True (the default),
                     otherwise, add it to the beginning of the list.
        :type append: Boolean
        """
        if append:
            self.template_lookup.directories.append(path)
        else:
            self.template_lookup.directories.insert(0, path)

    def initialize_controllers(self):
        """Initialize the plugin's controllers.
        """
        for name, controller in six.iteritems(self.module.config.controllers):
            self.logger.info("Initializing controller: {0}".format(name))
            controller.mod.init()

    def run_controllers(self):
        """Run the plugin's controllers.
        """
        for name, controller in six.iteritems(self.module.config.controllers):
            self.logger.info("Running controller: {0}".format(name))
            controller.mod.run()

########NEW FILE########
__FILENAME__ = server
# -*- coding: utf-8 -*-
from __future__ import print_function
import logging
import os
import sys
import threading
try:
    from urllib.parse import urlparse   # For Python 2
except ImportError:
    from urlparse import urlparse       # For Python 3; flake8 ignore # NOQA
from six.moves import SimpleHTTPServer
from six.moves import socketserver
from blogofile import config
from blogofile import util
from .cache import bf

bf.server = sys.modules['blogofile.server']

logger = logging.getLogger("blogofile.server")

class TCPServer(socketserver.TCPServer):
    """TCP Server that allows address reuse"""
    allow_reuse_address = True

class Server(threading.Thread):
    def __init__(self, port, address="127.0.0.1"):
        self.port = int(port)
        self.address = address
        if self.address == "0.0.0.0":
            # Bind to all addresses available
            address = ""
        threading.Thread.__init__(self)
        self.is_shutdown = False
        server_address = (address, self.port)
        HandlerClass = BlogofileRequestHandler
        HandlerClass.protocol_version = "HTTP/1.0"
        ServerClass = TCPServer
        self.httpd = ServerClass(server_address, HandlerClass)
        self.sa = self.httpd.socket.getsockname()

    def run(self):
        print("Blogofile server started on {0}:{1} ..."
              .format(self.sa[0], self.sa[1]))
        self.httpd.serve_forever()

    def shutdown(self):
        print("\nshutting down webserver...")
        self.httpd.shutdown()
        self.httpd.socket.close()
        self.is_shutdown = True


class BlogofileRequestHandler(SimpleHTTPServer.SimpleHTTPRequestHandler):

    error_template = """
<head>
<title>Error response</title>
</head>
<body>
<h1>404 Error</h1>
Your Blogofile site is configured for a subdirectory, maybe you were looking
for the root page? : <a href="{0}">{1}</a>
</body>"""

    def __init__(self, *args, **kwargs):
        path = urlparse(config.site.url).path
        self.BLOGOFILE_SUBDIR_ERROR = self.error_template.format(path, path)
        SimpleHTTPServer.SimpleHTTPRequestHandler.__init__(
            self, *args, **kwargs)

    def translate_path(self, path):
        site_path = urlparse(config.site.url).path
        if(len(site_path.strip("/")) > 0 and
                not path.startswith(site_path)):
            self.error_message_format = self.BLOGOFILE_SUBDIR_ERROR
            # Results in a 404
            return ""
        p = SimpleHTTPServer.SimpleHTTPRequestHandler.translate_path(
            self, path)
        if len(site_path.strip("/")) > 0:
            build_path = os.path.join(
                os.getcwd(),
                util.path_join(site_path.strip("/")))
        else:
            build_path = os.getcwd()
        build_path = p.replace(build_path, os.path.join(os.getcwd(), "_site"))
        return build_path

    def log_message(self, format, *args):
        pass

########NEW FILE########
__FILENAME__ = template
# -*- coding: utf-8 -*-
"""
Template abstraction for Blogofile to support multiple engines.

Templates are dictionaries. Any key/value pairs stored are supplied to
the underlying template as name/values.
"""
from __future__ import print_function
import copy
import logging
import os.path
import re
import sys
import tempfile

import jinja2

import mako
import mako.lookup
import mako.template

from . import filter as _filter
from . import util
from .cache import bf
from .cache import Cache


bf.template = sys.modules['blogofile.template']

base_template_dir = util.path_join(".", "_templates")
logger = logging.getLogger("blogofile.template")
template_content_place_holder = re.compile("~~!`TEMPLATE_CONTENT_HERE`!~~")


class TemplateEngineError(Exception):
    pass


class Template(dict):
    name = "base"

    def __init__(self, template_name, caller=None):
        dict.__init__(self)
        self.template_name = template_name
        self.caller = caller

    def render(self, path=None):
        """Render the template to the specified path on disk, or
        return a string if None.
        """
        raise NotImplementedError(
            "Template base class cannot be used directly")

    def write(self, path, rendered):
        path = util.path_join(bf.writer.output_dir, path)
        # Create the parent directories if they don't exist:
        util.mkdir(os.path.split(path)[0])
        if bf.config.site.overwrite_warning and os.path.exists(path):
            logger.warn("Location is used more than once: {0}".format(path))
        with open(path, "wb") as f:
            f.write(rendered)

    def render_prep(self, path):
        """Gather all the information we want to provide to the
        template before rendering.
        """
        for name, obj in list(bf.config.site.template_vars.items()):
            if name not in self:
                self[name] = obj
        # Create a context object that is fresh for each template render:
        bf.template_context = Cache(**self)
        bf.template_context.template_name = self.template_name
        bf.template_context.render_path = path
        bf.template_context.caller = self.caller
        self["bf"] = bf

    def render_cleanup(self):
        """Clean up stuff after we've rendered a template.
        """
        del bf.template_context

    def __repr__(self):
        return "<{0} file='{1}' {2}>".format(
            self.__class__.__name__, self.template_name, dict.__repr__(self))


class MakoTemplate(Template):
    name = "mako"
    template_lookup = None

    def __init__(self, template_name, caller=None, lookup=None, src=None):
        """Templates can be provided in 2 ways:

             1) Pass template_name to Mako for lookup
             2) Construct a Mako Template object from the src string
        """
        Template.__init__(self, template_name, caller)
        self.create_lookup()
        if lookup:
            # Make sure it's a mako environment:
            if type(lookup) != mako.lookup.TemplateLookup:
                raise TemplateEngineError(
                    "MakoTemplate was passed a non-mako lookup environment:"
                    " {0}".format(lookup))
            self.template_lookup = lookup
        self.add_template_path(bf.writer.temp_proc_dir)
        if src:
            self.mako_template = mako.template.Template(
                src,
                output_encoding="utf-8",
                strict_undefined=True,
                lookup=self.template_lookup)
        else:
            self.mako_template = self.template_lookup.get_template(
                template_name)
            self.mako_template.output_encoding = "utf-8"
            self.mako_template.strict_undefined = True

    @classmethod
    def create_lookup(cls):
        if MakoTemplate.template_lookup is None:
            MakoTemplate.template_lookup = mako.lookup.TemplateLookup(
                directories=[".", base_template_dir],
                input_encoding='utf-8', output_encoding='utf-8',
                encoding_errors='replace')

    @classmethod
    def add_default_template_path(cls, path):
        "Add a path to the default template_lookup"
        cls.create_lookup()
        if path not in cls.template_lookup.directories:
            cls.template_lookup.directories.append(path)

    def add_template_path(self, path, lookup=None):
        if lookup is None:
            lookup = self.template_lookup
        if path not in lookup.directories:
            lookup.directories.append(path)

    def render(self, path=None):
        self.render_prep(path)
        # Make sure bf_base_template is defined
        if "bf_base_template" in self:
            bf_base_template = os.path.split(self["bf_base_template"])[1]
            self.template_lookup.put_template(
                "bf_base_template", self.template_lookup.get_template(
                    bf_base_template))
        else:
            self.template_lookup.put_template(
                "bf_base_template",
                self.template_lookup.get_template(
                    bf.config.site.base_template))
        try:
            rendered = self.mako_template.render(**self)
            if path:
                self.write(path, rendered)
            return rendered
        except:
            logger.error("Error rendering template: {0}".format(
                    self.template_name))
            print((mako.exceptions.text_error_template().render()))
            raise
        finally:
            self.render_cleanup()


class JinjaTemplateLoader(jinja2.FileSystemLoader):
    def __init__(self, searchpath):
        jinja2.FileSystemLoader.__init__(self, searchpath)
        self.bf_base_template = bf.util.path_join(
            "_templates", bf.config.site.base_template)

    def get_source(self, environment, template):
        print(template)
        if template == "bf_base_template":
            with open(self.bf_base_template) as f:
                return (f.read(), self.bf_base_template, lambda: False)
        else:
            return (super(JinjaTemplateLoader, self)
                    .get_source(environment, template))


class JinjaTemplate(Template):
    name = "jinja2"
    template_lookup = None

    def __init__(self, template_name, caller=None, lookup=None, src=None):
        """Templates can be provided in 2 ways:

             1) Pass template_name to Jinja2 for loading
             2) Construct a template object from the src string
        """
        Template.__init__(self, template_name, caller)
        self.create_lookup()
        if lookup:
            # Make sure it's a jinja2 environment:
            if type(lookup) != jinja2.Environment:
                raise TemplateEngineError(
                    "JinjaTemplate was passed a non-jinja lookup environment:"
                    " {0}".format(lookup))
            self.template_lookup = lookup
        self.add_template_path(bf.writer.temp_proc_dir)
        # Jinja needs to delay the loading of the source until render
        # time in order to get the attrs into the loader,
        # so just save src until then.
        self.src = src

    @classmethod
    def create_lookup(cls):
        if cls.template_lookup is None:
            cls.template_lookup = jinja2.Environment(
                loader=JinjaTemplateLoader([base_template_dir,
                                            bf.writer.temp_proc_dir]))

    @classmethod
    def add_default_template_path(cls, path):
        cls.create_lookup()
        if path not in cls.template_lookup.loader.searchpath:
            cls.template_lookup.loader.searchpath.append(path)

    def add_template_path(self, path, lookup=None):
        if lookup is None:
            lookup = self.template_lookup
        if path not in lookup.loader.searchpath:
            lookup.loader.searchpath.append(path)

    def render(self, path=None):
        # Ensure that bf_base_template is set:
        if "bf_base_template" in self:
            self.template_lookup.loader.bf_base_template = (
                self["bf_base_template"])
        else:
            self["bf_base_template"] = (
                self.template_lookup.loader.bf_base_template)
        if self.src:
            self.jinja_template = self.template_lookup.from_string(self.src)
        # elif os.path.isfile(self.template_name):
        #     with open(self.template_name) as t_file:
        #         self.jinja_template = self.template_lookup.from_string(
        #             t_file.read())
        else:
            self.jinja_template = self.template_lookup.get_template(
                self.template_name)
        self.render_prep(path)
        try:
            rendered = bytes(self.jinja_template.render(self), "utf-8")
            if path:
                self.write(path, rendered)
            return rendered
        except:
            logger.error(
                "Error rendering template: {0}".format(self.template_name))
            raise
        finally:
            self.render_cleanup()


class FilterTemplate(Template):
    name = "filter"
    chain = None

    def __init__(self, template_name, caller=None, lookup=None, src=None):
        Template.__init__(self, template_name, caller)
        self.src = src
        self.marker = bf.config.templates.content_blocks.filter.replacement

    def render(self, path=None):
        self.render_prep(path)
        try:
            if self.src is None:
                with open(self.template_name) as f:
                    src = f.read()
            else:
                src = self.src
            # Run the filter chain:
            html = _filter.run_chain(self.chain, src)
            # Place the html into the base template:
            with open(self["bf_base_template"]) as f:
                html = f.read().replace(self.marker, html)
            html = bytes(html, "utf-8")
            if path:
                self.write(path, html)
            return html
        finally:
            self.render_cleanup()


class MarkdownTemplate(FilterTemplate):
    chain = "markdown"


class RestructuredTextTemplate(FilterTemplate):
    chain = "rst"


class TextileTemplate(FilterTemplate):
    chain = "textile"


def get_engine_for_template_name(template_name):
    # Find which template type it is:
    for extension, engine in bf.config.templates.engines.items():
        if template_name.endswith("." + extension):
            return engine
    else:
        raise TemplateEngineError(
            "Template has no engine defined in bf.config."
            "templates.engines: {0}".format(template_name))


def get_base_template_path():
    return bf.util.path_join("_templates", bf.config.site.base_template)


def get_base_template_src():
    with open(get_base_template_path()) as f:
        return f.read()


def materialize_alternate_base_engine(template_name, location, attrs={},
                                      lookup=None, base_engine=None,
                                      caller=None):
    """Materialize a templates within a foreign template engine.

    Procedure:

      1) Load the base template source, and mark the content block
         for later replacement.

      2) Materialize the base template in a temporary location with
         attrs.

      3) Convert the HTML to new template type by replacing the marker.

      4) Materialize the template setting bf_base_template to
         the new base template we created.
    """
    # Since we're mucking with the template attrs, make sure we copy
    # them and don't modify the original ones:
    attrs = copy.copy(attrs)
    if not base_engine:
        base_engine = get_engine_for_template_name(
            bf.config.site.base_template)
    template_engine = get_engine_for_template_name(template_name)
    base_template_src = get_base_template_src()
    if not lookup:
        lookup = base_engine.template_lookup
    else:
        base_engine.add_default_template_path(bf.writer.temp_proc_dir)
    # Replace the content block with our own marker:
    prev_content_block = bf.config.templates.content_blocks[base_engine.name]
    new_content_block = (
        bf.config.templates.content_blocks[template_engine.name])
    base_template_src = prev_content_block.pattern.sub(
        template_content_place_holder.pattern, base_template_src)
    html = str(base_engine(None, src=base_template_src).render(), "utf-8")
    html = template_content_place_holder.sub(
        new_content_block.replacement, html)
    new_base_template = tempfile.mktemp(
        suffix="." + template_engine.name, prefix="bf_template",
        dir=bf.writer.temp_proc_dir)
    with open(new_base_template, "w") as f:
        logger.debug(
            "Writing intermediate base template: {0}"
            .format(new_base_template))
        f.write(html)
    attrs["bf_base_template"] = new_base_template
    materialize_template(
        template_name, location, attrs, base_engine=template_engine)
    os.remove(new_base_template)


def materialize_template(template_name, location, attrs={}, lookup=None,
                         base_engine=None, caller=None):
    """Render a named template with attrs to a location in the _site dir.
    """
    # Find the appropriate template engine based on the file ending:
    template_engine = get_engine_for_template_name(template_name)
    if not base_engine:
        base_engine = get_engine_for_template_name(
            bf.config.site.base_template)
    # Is the base engine the same as the template engine?
    if base_engine == template_engine or base_engine == template_engine.name:
        template = template_engine(template_name, caller=caller, lookup=lookup)
        template.update(attrs)
        template.render(location)
    else:
        materialize_alternate_base_engine(
            template_name, location, attrs=attrs, caller=caller, lookup=lookup,
            base_engine=base_engine)

########NEW FILE########
__FILENAME__ = test_chrome
# -*- coding: utf-8 -*-
# Selenium tests for the builtin Blogofile server. This is only
# intended to be run in a virtualenv via tox. Selenium isn't working
# for me in Python3 right now. Blogofile will be run using the
# virtualenv python but selenium will be run with the system python2.

import unittest
import tempfile
import shutil
import os
import subprocess
import shlex
import time
import datetime
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException

def browserbot(driver, function, *args):
    """Selenium Javascript Helpers"""
    # Original copyright and license for browserbot.js (http://is.gd/Bz4xPc):
    # Copyright (c) 2009-2011 Jari Bakken

    # Permission is hereby granted, free of charge, to any person obtaining
    # a copy of this software and associated documentation files (the
    # "Software", to) deal in the Software without restriction, including
    # without limitation the rights to use, copy, modify, merge, publish,
    # distribute, sublicense, and/or sell copies of the Software, and to
    # permit persons to whom the Software is furnished to do so, subject to
    # the following conditions:

    # The above copyright notice and this permission notice shall be
    # included in all copies or substantial portions of the Software.

    # THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
    # EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
    # MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
    # NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
    # LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
    # OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
    # WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
    browserbot_js = """var browserbot = {

        getOuterHTML: function(element) {
            if (element.outerHTML) {
                return element.outerHTML;
            } else if (typeof(XMLSerializer) != undefined) {
                return new XMLSerializer().serializeToString(element);
            } else {
                throw "can't get outerHTML in this browser";
            }
        }

    };
    """
    js = browserbot_js + \
        "return browserbot.{0}.apply(browserbot, arguments);".format(function)
    return driver.execute_script(js,*args)

def html(web_element):
    """Return the HTML for a Selenium WebElement"""
    return browserbot(web_element.parent, "getOuterHTML", web_element)

class TestBrowser(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        #Remember the current directory to preserve state
        cls.previous_cwd = os.getcwd()
        #Create a staging directory that we can build in
        cls.build_path = tempfile.mkdtemp()
        #Change to that directory just like a user would
        os.chdir(cls.build_path)
        #Initialize and build the site
        subprocess.Popen(shlex.split("blogofile init blog_unit_test"),
                         stdout=subprocess.PIPE).wait()
        subprocess.Popen(shlex.split("blogofile build"),
                         stdout=subprocess.PIPE).wait()
        #Start the server
        cls.port = 42042
        cls.url = u"http://localhost:{0}".format(cls.port)
        cls.server = subprocess.Popen(shlex.split("blogofile serve {0}".
                                                   format(cls.port)),
                                      stdout=subprocess.PIPE)
        cls.chrome = webdriver.Chrome()
    @classmethod
    def tearDownClass(cls):
        cls.chrome.stop_client()
        #Stop the server
        cls.server.kill()
        #go back to the directory we used to be in
        os.chdir(cls.previous_cwd)
        #Clean up the build directory
        shutil.rmtree(cls.build_path)
        
    def testMainPage(self):
        self.chrome.get(self.url)
        self.assertEqual(self.chrome.current_url,self.url+u"/")
        self.assertEqual(self.chrome.title,u"Your Blog's Name")

    def testChronlogicalBlog(self):
        self.chrome.get(self.url)
        #Click on "chronological blog page" link on index
        self.chrome.find_element_by_link_text("chronological blog page").click()
        #Make sure we went to the right URL:
        self.assertEqual(self.chrome.current_url,self.url+u"/blog/")
        #Make sure there are five blog posts:
        self.assertEqual(len(self.chrome.find_elements_by_class_name("blog_post")),5)
        #Make sure there is no previous page:
        with self.assertRaises(NoSuchElementException):
            self.chrome.find_element_by_partial_link_text("Previous Page")
        #Go to the next page:
        self.chrome.find_element_by_partial_link_text("Next Page").click()
        #Make sure we went to the right URL:
        self.assertEqual(self.chrome.current_url,self.url+u"/blog/page/2/")
        #Make sure there are five blog posts:
        self.assertEqual(len(self.chrome.find_elements_by_class_name("blog_post")),5)
        #Go to the last page:
        self.chrome.find_element_by_partial_link_text("Next Page").click()
        #Make sure there is no next page:
        with self.assertRaises(NoSuchElementException):
            self.chrome.find_element_by_partial_link_text("Next Page")
        #Go back to the start:
        self.chrome.find_element_by_partial_link_text("Previous Page").click()
        self.chrome.find_element_by_partial_link_text("Previous Page").click()
        self.assertEqual(self.chrome.current_url,self.url+u"/blog/page/1/")
        #Make sure the unpublished draft is not present. It would be
        #the very first post on the first page if it were actually
        #published:
        with self.assertRaises(NoSuchElementException):
            self.chrome.find_element_by_link_text("This post is unpublished")

    def testPostFeatures(self):
        self.chrome.get(self.url+"/blog")
        self.chrome.find_element_by_link_text("Post 7").click()
        self.assertEqual(self.chrome.current_url,self.url+u"/blog/2009/08/29/post-seven/")
        self.assertEqual(self.chrome.find_element_by_class_name("post_prose").text,u"This is post #7")
        self.assertEqual(self.chrome.find_element_by_class_name("blog_post_date").text,u"August 29, 2009 at 03:25 PM")
        self.assertEqual(self.chrome.find_element_by_class_name("blog_post_categories").text,u"general stuff")
        self.chrome.find_element_by_link_text("general stuff").click()
        self.assertEqual(self.chrome.current_url,self.url+u"/blog/category/general-stuff/")
        
    def testPostWithNoDate(self):
        self.chrome.get(self.url+"/blog")
        self.chrome.find_element_by_link_text("Post without a date").click()
        #Make sure the post has today's date
        now = datetime.datetime.now().strftime("%B %d, %Y")
        #I guess this might fail at 23:59:59..
        self.assertTrue(self.chrome.find_element_by_class_name("blog_post_date").text.startswith(now))

    def testPostUnicode(self):
        self.chrome.get(self.url+"/blog/2009/08/22/unicode-test-")
        self.assertIn("私はガラスを食べられます。それは私を傷つけません".decode("utf-8"), self.chrome.get_page_source())
        self.assertIn("日本語テスト".decode("utf-8"), self.chrome.find_element_by_css_selector(".blog_post_title a").text)

    def testMarkdownTemplate(self):
        self.chrome.get(self.url+"/markdown_test.html")
        self.assertIn("<a href=\"http://www.blogofile.com\">This is a link</a>", self.chrome.get_page_source())

    def testPluginFilters(self):
        self.chrome.get(self.url+"/filter_test.html")
        self.assertIn(u"This is text from the plugin version of the filter.",
                      self.chrome.find_element_by_id("original_plugin_filter").text)
        self.assertIn(u"This is text from the overriden userspace filter.",
                      self.chrome.find_element_by_id("overriden_plugin_filter").text)

########NEW FILE########
__FILENAME__ = test_integration
# -*- coding: utf-8 -*-
"""Integration tests for blogofile.
"""
import os
import shutil
from tempfile import mkdtemp
try:
    import unittest2 as unittest        # For Python 2.6
except ImportError:
    import unittest                     # flake8 ignore # NOQA
from ... import main


class TestBlogofileCommands(unittest.TestCase):
    """Intrgration tests for the blogofile commands.
    """
    def _call_entry_point(self, *args):
        main.main(*args)

    def test_blogofile_init_bare_site(self):
        """`blogofile init src` initializes bare site w/ _config.py file
        """
        src_dir = mkdtemp()
        self.addCleanup(shutil.rmtree, src_dir)
        os.rmdir(src_dir)
        self._call_entry_point(['blogofile', 'init', src_dir])
        self.assertEqual(os.listdir(src_dir), ['_config.py'])

    def test_blogofile_build_bare_site(self):
        """`blogofile build` on bare site creates _site directory
        """
        self.addCleanup(os.chdir, os.getcwd())
        src_dir = mkdtemp()
        self.addCleanup(shutil.rmtree, src_dir)
        os.rmdir(src_dir)
        self._call_entry_point(['blogofile', 'init', src_dir])
        self._call_entry_point(['blogofile', 'build', '-s', src_dir])
        self.assertIn('_site', os.listdir(src_dir))

########NEW FILE########
__FILENAME__ = commands
import shutil
import sys
import os, os.path
import imp

import blogofile.main
from blogofile import argparse

## These are commands that are installed into the blogofile
## command-line utility. You can turn these off entirely by removing
## the command_parser_setup parameter in the module __dist__ object.

def setup(parent_parser, parser_template):
    from . import __dist__
    #Add additional subcommands under the main parser:
    cmd_subparsers = parent_parser.add_subparsers()

    #command1
    command1 = cmd_subparsers.add_parser(
        "command1", help="Example Command 1", parents=[parser_template])
    command1.add_argument("--extra-coolness",action="store_true",
                          help="Run with extra coolness")
    command1.set_defaults(func=do_command1)

    #command2
    command2 = cmd_subparsers.add_parser(
        "command2", help="Example Command 2", parents=[parser_template])
    command2.add_argument("ARG1",help="Required ARG1")
    command2.add_argument("ARG2",help="Optional ARG2",
                          nargs="?",default="Default")
    command2.set_defaults(func=do_command2)

    
#These are the actual command actions:
    
def do_command1(args):
    print("")
    print("This is command1.")
    if args.extra_coolness:
        print("It's as cool as can be.")
    else:
        print("It could be cooler though with --extra-coolness")
        
def do_command2(args):
    print("")
    print("This is command2.")
    print("Required ARG1 = {0}".format(args.ARG1))
    print("Optional ARG2 = {0}".format(args.ARG2))

########NEW FILE########
__FILENAME__ = photos
import shutil
import os
from blogofile import util

from . import plugin

def copy_photos():
    plugin.logger.info("Copying gallery photos..")
    if plugin.config.gallery.src:
        #The user has supplied their own photos
        shutil.copytree(plugin.config.gallery.src,
                        util.fs_site_path_helper(
                "_site",plugin.config.gallery.path,"img"))
    else:
        #The user has not configured the photo path
        #Use the supplied photos as an example
        shutil.copytree(os.path.join(plugin.tools.get_src_dir(),"_photos"),
                        util.fs_site_path_helper(
                "_site",plugin.config.gallery.path,"img"))

def get_photo_names():
    img_dir = util.fs_site_path_helper(
        "_site",plugin.config.gallery.path,"img")
    return [p for p in os.listdir(img_dir) if p.lower().endswith(".jpg")]

def write_pages(photos):
    for photo in photos:
        plugin.tools.materialize_template(
            "photo.mako", (plugin.config.gallery.path,photo+".html"),
            {"photo":photo})

def write_index(photos):
    plugin.tools.materialize_template(
        "photo_index.mako", (plugin.config.gallery.path,"index.html"),
        {"photos":photos})

########NEW FILE########
__FILENAME__ = filter_to_override
def run(content):
    return "This is text from the plugin version of the filter."

########NEW FILE########
__FILENAME__ = test_build
# -*- coding: utf-8 -*-
try:
    import unittest2 as unittest        # For Python 2.6
except ImportError:
    import unittest                     # flake8 ignore # NOQA
import tempfile
import shutil
import os
import re
from blogofile import main
from blogofile import util
from blogofile import template
from blogofile import cache
import logging


@unittest.skip('outdated integration test')
class TestBuild(unittest.TestCase):

    def setUp(self):
        main.do_debug()
        #Remember the current directory to preserve state
        self.previous_dir = os.getcwd()
        #Create a staging directory that we can build in
        self.build_path = tempfile.mkdtemp()
        #Change to that directory just like a user would
        os.chdir(self.build_path)
        #Reinitialize the configuration
        main.config.init()

    def tearDown(self):
        #Revert the config overridden options
        main.config.override_options = {}
        #go back to the directory we used to be in
        os.chdir(self.previous_dir)
        #Clean up the build directory
        shutil.rmtree(self.build_path)
        #Clear Template Engine environments:
        template.MakoTemplate.template_lookup = None
        template.JinjaTemplate.template_lookup = None
        main.config.reset_config()
        cache.reset_bf()

    def testBlogSubDir(self):
        """Test to make sure blogs hosted in subdirectories
        off the webroot work"""
        main.main("init blog_unit_test")
        main.config.override_options = {
            "site.url": "http://www.yoursite.com/~username",
            "blog.path": "/path/to/blog"}
        main.main("build")
        lsdir = os.listdir(os.path.join(self.build_path, "_site",
                                        "path", "to", "blog"))
        for fn in ("category", "page", "feed"):
            assert(fn in lsdir)

    def testPermaPages(self):
        """Test that permapages are written"""
        main.main("init blog_unit_test")
        main.config.override_options = {
            "site.url": "http://www.test.com/",
            "blog.path": "/blog"}
        main.main("build")
        assert "index.html" in os.listdir(
            os.path.join(self.build_path, "_site", "blog",
                         "2009", "07", "23", "post-1"))
        assert "index.html" in os.listdir(
            os.path.join(self.build_path, "_site", "blog",
                         "2009", "07", "24", "post-2"))

    def testNoPosts(self):
        """Test when there are no posts, site still builds cleanly"""
        main.main("init blog_unit_test")
        main.config.override_options = {
            "site_url": "http://www.test.com/",
            "blog_path": "/blog"}
        shutil.rmtree("_posts")
        util.mkdir("_posts")
        main.main("build")

    def testPostInSubdir(self):
        "Test a post in a subdirectory of _posts"
        pass

    def testNoPostsDir(self):
        """Test when there is no _posts dir, site still builds cleanly"""
        main.main("init blog_unit_test")
        main.config.override_options = {
            "site.url": "http://www.test.com/",
            "blog.path": "/blog"}
        shutil.rmtree("_posts")
        logger = logging.getLogger("blogofile")
        #We don't need to see the error that this test checks for:
        logger.setLevel(logging.CRITICAL)
        main.main("build")
        logger.setLevel(logging.ERROR)

    def testCategoryPages(self):
        """Test that categories are written"""
        main.main("init blog_unit_test")
        main.config.override_options = {
            "site.url": "http://www.test.com",
            "blog.path": "/path/to/blog"}
        main.main("build")
        assert "index.html" in os.listdir(
            os.path.join(self.build_path, "_site", "path",
                         "to", "blog", "category", "category-1", "1"))
        assert "index.html" in os.listdir(
            os.path.join(self.build_path, "_site", "path",
                         "to", "blog", "category", "category-1"))
        assert "index.html" in os.listdir(
            os.path.join(self.build_path, "_site", "path",
                         "to", "blog", "category", "category-2"))
        assert "index.html" in os.listdir(
            os.path.join(self.build_path, "_site", "path",
                         "to", "blog", "category", "category-2", "1"))

    def testArchivePages(self):
        """Test that archives are written"""
        main.main("init blog_unit_test")
        main.config.override_options = {
            "site.url": "http://www.test.com",
            "blog.path": "/path/to/blog"}
        main.main("build")
        assert "index.html" in os.listdir(
            os.path.join(self.build_path, "_site", "path",
                         "to", "blog", "archive", "2009", "07", "1"))

    def testFeeds(self):
        """Test that RSS/Atom feeds are written"""
        main.main("init blog_unit_test")
        main.config.override_options = {
            "site.url": "http://www.test.com",
            "blog.path": "/path/to/blog"}
        main.main("build")
        #Whole blog feeds
        assert "index.xml" in os.listdir(
            os.path.join(self.build_path, "_site", "path", "to",
                         "blog", "feed"))
        assert "index.xml" in os.listdir(
            os.path.join(self.build_path, "_site", "path", "to",
                         "blog", "feed", "atom"))
        #Per category feeds
        assert "index.xml" in os.listdir(
            os.path.join(self.build_path, "_site", "path", "to",
                         "blog", "category", "category-1", "feed"))
        assert "index.xml" in os.listdir(
            os.path.join(self.build_path, "_site", "path", "to",
                         "blog", "category", "category-1", "feed", "atom"))

    def testFileIgnorePatterns(self):
        main.main("init blog_unit_test")
        #Initialize the config manually
        main.config.init("_config.py")
        #Add some file_ignore_patterns:
        open("test.txt", "w").close()
        open("test.py", "w").close()
        #File ignore patterns can be strings
        main.config.site.file_ignore_patterns.append(r".*test\.txt$")
        #Or, they can be precompiled regexes
        p = re.compile(".*\.py$")
        main.config.site.file_ignore_patterns.append(p)
        main.config.recompile()
        main.do_build([], load_config=False)
        assert not "test.txt" in os.listdir(
            os.path.join(self.build_path, "_site"))
        assert not "test.py" in os.listdir(
            os.path.join(self.build_path, "_site"))

    def testAutoPermalinks(self):
        main.main("init blog_unit_test")
        main.main("build")
        #Make sure the post with question mark in title was generated properly
        assert os.path.isfile(os.path.join(
                self.build_path, "_site", "blog", "2009", "08",
                "29", "this-title-has-a-question-mark-", "index.html"))

    def testAutoPermalinkPagesRespectBlogPath(self):
        """Test that default auto_permalink.path incorporates the
           configured blog.path setting"""
        main.main("init blog_unit_test")
        main.config.override_options = {
            "site.url": "http://www.test.com",
            "blog.path": "some-crazy-blog"}
        main.main("build")
        assert "index.html" in os.listdir(
            os.path.join(self.build_path, "_site", "some-crazy-blog",
                         "2009", "07", "23", "post-1"))
        assert "index.html" in os.listdir(
            os.path.join(self.build_path, "_site", "some-crazy-blog",
                         "2009", "07", "24", "post-2"))

########NEW FILE########
__FILENAME__ = test_config
# -*- coding: utf-8 -*-
"""Unit tests for blogofile config module.
"""
import os
try:
    import unittest2 as unittest        # For Python 2.6
except ImportError:
    import unittest                     # flake8 ignore # NOQA
from mock import (
    MagicMock,
    mock_open,
    patch,
    )
from .. import config


class TestConfigModuleAttributes(unittest.TestCase):
    """Unit tests for attributes that config exposes in its module scope.
    """
    def test_bf_config_is_module(self):
        """config has bf.config attribute that is a module
        """
        from types import ModuleType
        self.assertIsInstance(config.bf.config, ModuleType)

    def test_bf_config_module_name(self):
        """bf.config attribute is blogofile.config module
        """
        self.assertEqual(config.bf.config.__name__, 'blogofile.config')

    def test_site_is_hierarchical_cache(self):
        """config has site attribute that is a HierarchicalCache object
        """
        from ..cache import HierarchicalCache
        self.assertIsInstance(config.site, HierarchicalCache)

    def test_controllers_is_hierarchical_cache(self):
        """config has controllers attribute that is a HierarchicalCache object
        """
        from ..cache import HierarchicalCache
        self.assertIsInstance(config.controllers, HierarchicalCache)

    def test_filters_is_hierarchical_cache(self):
        """config has filters attribute that is a HierarchicalCache object
        """
        from ..cache import HierarchicalCache
        self.assertIsInstance(config.filters, HierarchicalCache)

    def test_plugins_is_hierarchical_cache(self):
        """config has plugins attribute that is a HierarchicalCache object
        """
        from ..cache import HierarchicalCache
        self.assertIsInstance(config.plugins, HierarchicalCache)

    def test_templates_is_hierarchical_cache(self):
        """config has templates attribute that is a HierarchicalCache object
        """
        from ..cache import HierarchicalCache
        self.assertIsInstance(config.templates, HierarchicalCache)

    def test_default_config_path(self):
        """config has default_config_path attr set to default_config module
        """
        self.assertEqual(
            config.default_config_path,
            os.path.join(os.path.abspath('blogofile'), 'default_config.py'))


class TestConfigInitInteractive(unittest.TestCase):
    """Unit tests for init_interactive function.
    """
    def _call_fut(self, *args):
        """Call the function under test.
        """
        return config.init_interactive(*args)

    def test_init_interactive_loads_user_config(self):
        """init_interactive loads value from user _config.py
        """
        args = MagicMock(src_dir='foo')
        mo = mock_open(read_data='site.url = "http://www.example.com/test/"')
        with patch.object(config, 'open', mo, create=True):
            self._call_fut(args)
        self.assertEqual(config.site.url, 'http://www.example.com/test/')

    def test_init_interactive_no_config_raises_SystemExit(self):
        """init_interactive raises SystemExit when no _config.py exists
        """
        args = MagicMock(src_dir='foo')
        with self.assertRaises(SystemExit):
            self._call_fut(args)


class TestConfigLoadConfig(unittest.TestCase):
    """Unit tests for _load_config function.
    """
    def _call_fut(self, *args):
        """Call the function under test.
        """
        return config._load_config(*args)

    def test_init_interactive_loads_default_config(self):
        """init_interactive loads values from default_config.py
        """
        with patch.object(config, 'open', mock_open(), create=True):
            self._call_fut('_config.py')
        self.assertEqual(config.site.url, 'http://www.example.com')

    def test_load_config_no_config_raises_IOError(self):
        """_load_config raises IOError when no _config.py exists
        """
        with self.assertRaises(IOError):
            self._call_fut('_config.py')

########NEW FILE########
__FILENAME__ = test_content
# -*- coding: utf-8 -*-
try:
    import unittest2 as unittest        # For Python 2.6
except ImportError:
    import unittest                     # flake8 ignore # NOQA
import tempfile
import shutil
import os
from blogofile import main


@unittest.skip('outdated integration test')
class TestContent(unittest.TestCase):

    def setUp(self):
        #Remember the current directory to preserve state
        self.previous_dir = os.getcwd()
        #Create a staging directory that we can build in
        self.build_path = tempfile.mkdtemp()
        #Change to that directory just like a user would
        os.chdir(self.build_path)
        #Reinitialize the configuration
        main.config.init()

    def tearDown(self):
        #Revert the config overridden options
        main.config.override_options = {}
        #go back to the directory we used to be in
        os.chdir(self.previous_dir)
        #Clean up the build directory
        shutil.rmtree(self.build_path)

    def testAutoPermalink(self):
        """make sure post without permalink gets a good autogenerated one
        """
        main.main("init blog_unit_test")
        #Write a post to the _posts dir:
        src = """---
title: This is a test post
date: 2009/08/16 00:00:00
---
This is a test post
"""
        f = open(
            os.path.join(self.build_path, "_posts", "01. Test post.html"), "w")
        f.write(src)
        f.close()
        main.config.override_options = {
            "site.url": "http://www.yoursite.com",
            "blog.path": "/blog",
            "blog.auto_permalink.enabled": True,
            "blog.auto_permalink.path": "/blog/:year/:month/:day/:title"}
        main.main("build")
        rendered = open(os.path.join(self.build_path,"_site","blog","2009","08",
                                     "16","this-is-a-test-post","index.html"
                                     )).read()

    def testHardCodedPermalinkUpperCase(self):
        """Permalink's set by the user should appear exactly as the user enters"""
        main.main("init blog_unit_test")
        #Write a post to the _posts dir:
        permalink = "http://www.yoursite.com/bLog/2009/08/16/This-Is-A-TeSt-Post"
        src = """---
title: This is a test post
permalink: %(permalink)s
date: 2009/08/16 00:00:00
---
This is a test post
""" % {'permalink':permalink}
        f = open(os.path.join(self.build_path,"_posts","01. Test post.html"),"w")
        f.write(src)
        f.close()
        main.config.override_options = {
            "site.url":"http://www.yoursite.com",
            "blog.path":"/blog",
            "blog.auto_permalink.enabled": True,
            "blog.auto_permalink.path": "/blog/:year/:month/:day/:title" }
        main.main("build")
        rendered = open(os.path.join(self.build_path,"_site","bLog","2009","08",
                                     "16","This-Is-A-TeSt-Post","index.html"
                                     )).read()

    def testUpperCaseAutoPermalink(self):
        """Auto generated permalinks should have title and filenames lower case
        (but not the rest of the URL)"""
        main.main("init blog_unit_test")
        #Write a post to the _posts dir:
        src = """---
title: This is a test post
date: 2009/08/16 00:00:00
---
This is a test post without a permalink
"""
        f = open(os.path.join(self.build_path,"_posts","01. Test post.html"),"w")
        f.write(src)
        f.close()
        main.config.override_options = {
            "site.url":"http://www.BlogoFile.com",
            "blog.path":"/Blog",
            "blog.auto_permalink.enabled": True,
            "blog.auto_permalink.path": "/Blog/:year/:month/:day/:title" }
        main.main("build")
        rendered = open(os.path.join(self.build_path,"_site","Blog","2009","08",
                                     "16","this-is-a-test-post","index.html"
                                     )).read()
    
    def testPathOnlyPermalink(self):
        """Test to make sure path only permalinks are generated correctly"""
        main.main("init blog_unit_test")
        #Write a post to the _posts dir:
        permalink = "/blog/2009/08/16/this-is-a-test-post"
        src = """---
title: This is a test post
permalink: %(permalink)s
date: 2009/08/16 00:00:00
---
This is a test post
""" %{'permalink':permalink}
        f = open(os.path.join(self.build_path,"_posts","01. Test post.html"),"w")
        f.write(src)
        f.close()
        main.config.override_options = {
            "site.url":"http://www.yoursite.com",
            "blog.path":"/blog",
            "blog.auto_permalink.enabled": True,
            "blog.auto_permalink.path": "/blog/:year/:month/:day/:title" }
        main.main("build")
        rendered = open(os.path.join(self.build_path,"_site","blog","2009","08",
                                     "16","this-is-a-test-post","index.html"
                                     )).read()

#TODO: Replace BeautifulSoup with lxml or use Selenium:
#     def testFeedLinksAreURLs(self):
#         """Make sure feed links are full URLs and not just paths"""
#         main.main("init blog_unit_test")
#         #Write a post to the _posts dir:
#         permalink = "/blog/2009/08/16/test-post"
#         src = """---
# title: This is a test post
# permalink: %(permalink)s
# date: 2009/08/16 00:00:00
# ---
# This is a test post
# """ %{'permalink':permalink}
#         f = open(os.path.join(self.build_path,"_posts","01. Test post.html"),"w")
#         f.write(src)
#         f.close()
#         main.config.override_options = {
#             "site.url":"http://www.yoursite.com",
#             "blog.path":"/blog",
#             "blog.auto_permalink.enabled": True,
#             "blog.auto_permalink.path": "/blog/:year/:month/:day/:title" }
#         main.main("build")
#         feed = open(os.path.join(self.build_path,"_site","blog","feed",
#                                  "index.xml")).read()
#         soup = BeautifulSoup.BeautifulStoneSoup(feed)
#         for link in soup.findAll("link"):
#             assert(link.contents[0].startswith("http://"))


#TODO: Replace BeautifulSoup with lxml or use Selenium:        
#     def testCategoryLinksInPosts(self):
#         """Make sure category links in posts are correct"""
#         main.main("init blog_unit_test")
#         main.config.override_options = {
#             "site.url":"http://www.yoursite.com",
#             "blog.path":"/blog"
#             }
#         #Write a blog post with categories:
#         src = """---
# title: This is a test post
# categories: Category 1, Category 2
# date: 2009/08/16 00:00:00
# ---
# This is a test post
# """
#         f = open(os.path.join(self.build_path,"_posts","01. Test post.html"),"w")
#         f.write(src)
#         f.close()
#         main.main("build")
#         #Open up one of the permapages:
#         page = open(os.path.join(self.build_path,"_site","blog","2009",
#                                  "08","16","this-is-a-test-post","index.html")).read()
#         soup = BeautifulSoup.BeautifulStoneSoup(page)
#         print(soup.findAll("a"))
#         assert soup.find("a",attrs={'href':'/blog/category/category-1'})
#         assert soup.find("a",attrs={'href':'/blog/category/category-2'})

    def testReStructuredFilter(self):
        """Test to make sure reStructuredTest work well"""

        main.main("init blog_unit_test")
        #Write a post to the _posts dir:
        src = """---
title: This is a test post
date: 2010/03/27 00:00:00
---

This is a reStructured post
===========================

Plain text :

::

    $ echo "hello"
    hello

"""
        f = open(os.path.join(self.build_path,"_posts","01. Test post.rst"),"w")
        f.write(src)
        f.close()
        main.config.override_options = {
            "site.url":"http://www.yoursite.com",
            "blog.path":"/blog",
            "blog.auto_permalink.enabled": True,
            "blog.auto_permalink.path": "/blog/:year/:month/:day/:title" }
        main.main("build")
        rendered = open(os.path.join(self.build_path,"_site","blog","2010","03",
                                     "27","this-is-a-test-post","index.html"
                                     )).read()
        assert """<h1 class="title">This is a reStructured post</h1>
<p>Plain text :</p>
<pre class="literal-block">
$ echo &quot;hello&quot;
hello
</pre>""" in rendered

    def testUnpublishedPost(self):
        """A post marked 'draft: True' should never show up in
        archives, categories, chronological listings, or feeds. It
        should generate a single permapage and that's all."""
        main.main("init blog_unit_test")
        main.main("build")
        #Make sure the permapage was written
        rendered = open(os.path.join(
                self.build_path,"_site","blog","2099","08",
                "01","this-post-is-unpublished","index.html"
                )).read()
        #Make sure the archive was not written
        assert not os.path.exists(os.path.join(
                self.build_path,"_site","blog","archive",
                "2099"))
        #Make sure the category was not written
        assert not os.path.exists(os.path.join(
                self.build_path,"_site","blog","category",
                "drafts"))

########NEW FILE########
__FILENAME__ = test_main
# -*- coding: utf-8 -*-
"""Unit tests for blogofile main module.

Tests entry point function, command line parser, and sub-command
action functions.
"""
import argparse
import logging
import os
import platform
import sys
try:
    import unittest2 as unittest        # For Python 2.6
except ImportError:
    import unittest                     # flake8 ignore # NOQA
from mock import MagicMock
from mock import Mock
from mock import patch
import six
from .. import main


class TestEntryPoint(unittest.TestCase):
    """Unit tests for blogofile entry point function.
    """
    def _call_entry_point(self):
        main.main()

    @patch.object(main, 'setup_command_parser', return_value=(Mock(), []))
    def test_entry_w_too_few_args_prints_help(self, mock_setup_parser):
        """entry with 1 arg calls parser print_help and exits
        """
        mock_parser, mock_subparsers = mock_setup_parser()
        mock_parser.exit = sys.exit
        with patch.object(main, 'sys') as mock_sys:
            mock_sys.argv = ['blogofile']
            with self.assertRaises(SystemExit):
                self._call_entry_point()
        mock_parser.print_help.assert_called_once()

    @patch.object(main, 'setup_command_parser', return_value=(Mock(), []))
    def test_entry_parse_args(self, mock_setup_parser):
        """entry with >1 arg calls parse_args
        """
        mock_parser, mock_subparsers = mock_setup_parser()
        with patch.object(main, 'sys') as mock_sys:
            mock_sys.argv = 'blogofile foo'.split()
            self._call_entry_point()
        mock_parser.parse_args.assert_called_once()

    @patch.object(main, 'setup_command_parser', return_value=(Mock(), []))
    @patch.object(main, 'set_verbosity')
    def test_entry_set_verbosity(self, mock_set_verbosity, mock_setup_parser):
        """entry with >1 arg calls set_verbosity
        """
        mock_parser, mock_subparsers = mock_setup_parser()
        mock_args = Mock()
        mock_parser.parse_args = Mock(return_value=mock_args)
        with patch.object(main, 'sys') as mock_sys:
            mock_sys.argv = 'blogofile foo bar'.split()
            self._call_entry_point()
        mock_set_verbosity.assert_called_once_with(mock_args)

    @patch.object(main, 'setup_command_parser',
                  return_value=(Mock(name='parser'), Mock(name='subparsers')))
    @patch.object(main, 'do_help')
    def test_entry_do_help(self, mock_do_help, mock_setup_parser):
        """entry w/ help in args calls do_help w/ args, parser & subparsers
        """
        mock_parser, mock_subparsers = mock_setup_parser()
        mock_args = Mock(name='args', func=mock_do_help)
        mock_parser.parse_args = Mock(return_value=mock_args)
        with patch.object(main, 'sys') as mock_sys:
            mock_sys.argv = 'blogofile help'.split()
            self._call_entry_point()
        mock_do_help.assert_called_once_with(
            mock_args, mock_parser, mock_subparsers)

    @patch.object(main, 'setup_command_parser', return_value=(Mock(), []))
    def test_entry_arg_func(self, mock_setup_parser):
        """entry with >1 arg calls args.func with args
        """
        mock_parser, mock_subparsers = mock_setup_parser()
        mock_args = Mock()
        mock_parser.parse_args = Mock(return_value=mock_args)
        with patch.object(main, 'sys') as mock_sys:
            mock_sys.argv = 'blogofile foo bar'.split()
            self._call_entry_point()
        mock_args.func.assert_called_once_with(mock_args)


class TestLoggingVerbosity(unittest.TestCase):
    """Unit tests for logging verbosity setup.
    """
    def _call_fut(self, *args):
        """Call the fuction under test.
        """
        main.set_verbosity(*args)

    @patch.object(main, 'logger')
    def test_verbose_mode_sets_INFO_logging(self, mock_logger):
        """verbose==True in args sets INFO level logging
        """
        mock_args = Mock(verbose=True, veryverbose=False)
        self._call_fut(mock_args)
        mock_logger.setLevel.assert_called_once_with(logging.INFO)

    @patch.object(main, 'logger')
    def test_very_verbose_mode_sets_DEBUG_logging(self, mock_logger):
        """veryverbose==True in args sets DEBUG level logging
        """
        mock_args = Mock(verbose=False, veryverbose=True)
        self._call_fut(mock_args)
        mock_logger.setLevel.assert_called_once_with(logging.DEBUG)


class TestParserTemplate(unittest.TestCase):
    """Unit tests for command line parser template.
    """
    def _call_fut(self):
        """Call function under test.
        """
        return main._setup_parser_template()

    @patch('sys.stderr', new_callable=six.StringIO)
    def test_parser_template_version(self, mock_stderr):
        """parser template version arg returns expected string and exits
        """
        from .. import __version__
        parser_template = self._call_fut()
        with self.assertRaises(SystemExit):
            parser_template.parse_args(['--version'])
        self.assertEqual(
            mock_stderr.getvalue(),
            'Blogofile {0} -- http://www.blogofile.com -- {1} {2}\n'
            .format(__version__, platform.python_implementation(),
                    platform.python_version()))

    def test_parser_template_verbose_default(self):
        """parser template sets verbose default to False
        """
        parser_template = self._call_fut()
        args = parser_template.parse_args([])
        self.assertFalse(args.verbose)

    def test_parser_template_verbose_true(self):
        """parser template sets verbose to True when -v in args
        """
        parser_template = self._call_fut()
        args = parser_template.parse_args(['-v'])
        self.assertTrue(args.verbose)

    def test_parser_template_veryverbose_default(self):
        """parser template sets veryverbose default to False
        """
        parser_template = self._call_fut()
        args = parser_template.parse_args([])
        self.assertFalse(args.veryverbose)

    def test_parser_template_veryverbose_true(self):
        """parser template sets veryverbose to True when -vv in args
        """
        parser_template = self._call_fut()
        args = parser_template.parse_args(['-vv'])
        self.assertTrue(args.veryverbose)


class TestHelpParser(unittest.TestCase):
    """Unit tests for help sub-command parser.
    """
    def _parse_args(self, *args):
        """Set up sub-command parser, parse args, and return result.
        """
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        main._setup_help_parser(subparsers)
        return parser.parse_args(*args)

    def test_help_parser_commands_default(self):
        """help w/ no command sets command arg to empty list
        """
        args = self._parse_args(['help'])
        self.assertEqual(args.command, [])

    def test_help_parser_commands(self):
        """help w/ commands sets command arg to list of commands
        """
        args = self._parse_args('help foo bar'.split())
        self.assertEqual(args.command, 'foo bar'.split())

    def test_help_parser_func_do_help(self):
        """help action function is do_help
        """
        args = self._parse_args(['help'])
        self.assertEqual(args.func, main.do_help)


class TestInitParser(unittest.TestCase):
    """Unit tests for init sub-command parser.
    """
    def _parse_args(self, *args):
        """Set up sub-command parser, parse args, and return result.
        """
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        main._setup_init_parser(subparsers)
        return parser.parse_args(*args)

    def test_init_parser_src_dir_arg(self):
        """init parser sets src_dir arg to given arg
        """
        args = self._parse_args('init foo'.split())
        self.assertEqual(args.src_dir, 'foo')

    def test_init_parser_plugin_default(self):
        """init parser sets default plugin arg to None
        """
        args = self._parse_args('init foo'.split())
        self.assertEqual(args.plugin, None)

    def test_init_parser_plugin_arg(self):
        """init parser sets plugin arg to given arg
        """
        args = self._parse_args('init foo bar'.split())
        self.assertEqual(args.plugin, 'bar')

    def test_init_parser_func_do_build(self):
        """init action function is do_init
        """
        args = self._parse_args('init foo'.split())
        self.assertEqual(args.func, main.do_init)


class TestDoInit(unittest.TestCase):
    """Unit tests for init sub-command action function.
    """
    def _call_fut(self, args):
        """Call the fuction under test.
        """
        main.do_init(args)

    @patch.object(main.os.path, 'exists', return_value=True)
    @patch('sys.stderr', new_callable=six.StringIO)
    def test_do_init_not_overwrite_existing_src_dir(self, mock_stderr,
                                                    mock_path_exists):
        """do_init won't overwrite existing src_dir and exits w/ msg
        """
        args = Mock(src_dir='foo/bar', plugin=None)
        with self.assertRaises(SystemExit):
            self._call_fut(args)
        self.assertEqual(
            mock_stderr.getvalue(),
            '{0.src_dir} already exists; initialization aborted\n'
            .format(args))

    @patch.object(main.os.path, 'exists', return_value=False)
    @patch.object(main, '_init_bare_site', autospec=True)
    def test_do_init_wo_plugin_calls_init_bare_site(self, mock_init_bare_site,
                                                    mock_path_exists):
        """do_init w/o plugin calls _init_bare_site w/ src_dir arg
        """
        args = Mock(src_dir='foo/bar', plugin=None)
        self._call_fut(args)
        mock_init_bare_site.assert_called_once_with(args.src_dir)

    @patch.object(main.os.path, 'exists', return_value=False)
    @patch.object(main, '_init_plugin_site', autospec=True)
    def test_do_init_w_plugin_init_plugin_site(self, mock_init_plugin_site,
                                               mock_path_exists):
        """do_init w plugin calls _init_plugin_site w/ args
        """
        args = Mock(src_dir='foo/bar', plugin='blog')
        self._call_fut(args)
        mock_init_plugin_site.assert_called_once_with(args)


class TestInitBareSite(unittest.TestCase):
    """Unit tests _init_bare_site function.
    """
    def _call_fut(self, args):
        """Call the fuction under test.
        """
        main._init_bare_site(args)

    @patch.object(main.os, 'makedirs', autospec=True)
    def test_init_bare_site_creates_src_dir(self, mock_mkdirs):
        """_init_bare_site calls os.makedirs to create src_dir c/w parents
        """
        src_dir = 'foo/bar'
        with patch.object(main, 'open', create=True) as mock_open:
            spec = six.StringIO if six.PY3 else file
            mock_open.return_value = MagicMock(spec=spec)
            self._call_fut(src_dir)
        mock_mkdirs.assert_called_once_with(src_dir)

    @patch.object(main.os, 'makedirs')
    def test_init_bare_site_writes_to_config_file(self, mock_mkdirs):
        """_init_bare_site writes new _config.py file
        """
        with patch.object(main, 'open', create=True) as mock_open:
            spec = six.StringIO if six.PY3 else file
            mock_open.return_value = MagicMock(spec=spec)
            new_config_handle = mock_open.return_value.__enter__.return_value
            self._call_fut('foo/bar')
            self.assertTrue(new_config_handle.writelines.called)

    @patch.object(main.os, 'makedirs')
    def test_init_bare_site_writes_config(self, mock_mkdirs):
        """_init_bare_site writes expected lines to new _config.py file
        """
        with patch.object(main, 'open', create=True) as mock_open:
            spec = six.StringIO if six.PY3 else file
            mock_open.return_value = MagicMock(spec=spec)
            new_config_handle = mock_open.return_value.__enter__.return_value
            self._call_fut('foo/bar')
            new_config_handle.writelines.called_with('# -*- coding: utf-8 -*-')

    @patch.object(main.os, 'makedirs')
    @patch('sys.stdout', new_callable=six.StringIO)
    def test_init_bare_site_prints_config_written_msg(self, mock_stdout,
                                                      mock_mkdirs):
        """_init_bare_site prints msg re: creation of _config.py file
        """
        src_dir = 'foo/bar'
        with patch.object(main, 'open', create=True) as mock_open:
            spec = six.StringIO if six.PY3 else file
            mock_open.return_value = MagicMock(spec=spec)
            self._call_fut(src_dir)
        self.assertEqual(
            mock_stdout.getvalue(),
            '_config.py for a bare (do-it-yourself) site written to {0}\n'
            'If you were expecting more, please see `blogofile init -h`\n'
            .format(src_dir))


class TestInitPluginSite(unittest.TestCase):
    """Unit tests _init_plugin_site function.
    """
    def _call_fut(self, *args):
        """Call the fuction under test.
        """
        main._init_plugin_site(*args)

    @patch.object(main.shutil, 'copytree')
    def test_init_plugin_site_gets_plugin_by_name(self, mock_copytree):
        """_init_plugin_site calls plugin.get_by_name w/ plugin arg
        """
        from .. import plugin as plugin_module
        args = Mock(src_dir='foo/bar', plugin='baz')
        mock_plugin = Mock(__file__='baz_plugin/__init__.py')
        patch_get_by_name = patch.object(
            plugin_module, 'get_by_name', return_value=mock_plugin)
        with patch_get_by_name as mock_get_by_name:
            self._call_fut(args)
        mock_get_by_name.assert_called_once_with(args.plugin)

    @patch('sys.stderr', new_callable=six.StringIO)
    def test_init_plugin_site_msg_re_unknown_plugin(self, mock_stderr):
        """_init_plugin_site shows msg if plugin arg not found
        """
        from .. import plugin as plugin_module
        args = Mock(src_dir='foo/bar', plugin='baz')
        patch_get_by_name = patch.object(
            plugin_module, 'get_by_name', return_value=None)
        patch_open = patch.object(main, 'open', create=True)
        # nested contexts for Python 2.6 compatibility
        with patch_open as mock_open:
            spec = six.StringIO if six.PY3 else file
            mock_open.return_value = MagicMock(spec=spec)
            with patch_get_by_name:
                self._call_fut(args)
        self.assertTrue(
            mock_stderr.getvalue().startswith(
                '{0.plugin} plugin not installed; initialization aborted\n\n'
                'installed plugins:\n'.format(args)))

    @patch('sys.stderr', new_callable=six.StringIO)
    def test_init_plugin_site_plugin_list_if_unknown_plugin(self, mock_stderr):
        """
        """
        from .. import plugin as plugin_module
        args = Mock(src_dir='foo/bar', plugin='baz')
        patch_get_by_name = patch.object(
            plugin_module, 'get_by_name', return_value=None)
        patch_list_plugins = patch.object(plugin_module, 'list_plugins')
        patch_open = patch.object(main, 'open', create=True)
        # nested contexts for Python 2.6 compatibility
        with patch_list_plugins as mock_list_plugins:
            with patch_get_by_name:
                with patch_open:
                    self._call_fut(args)
        assert mock_list_plugins.called

    @patch.object(main.shutil, 'copytree')
    @patch.object(main.shutil, 'ignore_patterns')
    def test_init_plugin_site_ignore_dirs(self, mock_ignore_patterns,
                                          mock_copytree):
        """_init_plugin_site calls shutil.ignore_patterns w/ expected dirs
        """
        from .. import plugin as plugin_module
        args = Mock(src_dir='foo/bar', plugin='baz')
        mock_plugin = Mock(__file__='baz_plugin/__init__.py')
        patch_get_by_name = patch.object(
            plugin_module, 'get_by_name', return_value=mock_plugin)
        with patch_get_by_name:
            self._call_fut(args)
        mock_ignore_patterns.assert_called_once_with(
            '_controllers', '_filters')

    @patch.object(main.shutil, 'ignore_patterns')
    @patch.object(main.shutil, 'copytree')
    def test_init_plugin_site_copies_site_src_tree(self, mock_copytree,
                                                   mock_ignore_patterns):
        """_init_plugin_site calls shutil.copytree w/ expected args
        """
        from .. import plugin as plugin_module
        args = Mock(src_dir='foo/bar', plugin='baz')
        mock_plugin = Mock(__file__='baz_plugin/__init__.py')
        patch_get_by_name = patch.object(
            plugin_module, 'get_by_name', return_value=mock_plugin)
        with patch_get_by_name:
            self._call_fut(args)
            mock_plugin_path = os.path.dirname(
                os.path.realpath(mock_plugin.__file__))
            mock_site_src = os.path.join(mock_plugin_path, 'site_src')
        mock_copytree.assert_called_once_with(
            mock_site_src, args.src_dir, ignore=mock_ignore_patterns())

    @patch.object(main.shutil, 'copytree')
    @patch('sys.stdout', new_callable=six.StringIO)
    def test_init_plugin_site_prints_config_written_msg(self, mock_stdout,
                                                        mock_copytree):
        """_init_plugin_site prints msg re: creation of _config.py file
        """
        from .. import plugin as plugin_module
        args = Mock(src_dir='foo/bar', plugin='baz')
        mock_plugin = Mock(__file__='baz_plugin/__init__.py')
        patch_get_by_name = patch.object(
            plugin_module, 'get_by_name', return_value=mock_plugin)
        patch_open = patch.object(main, 'open', create=True)
        # nested contexts for Python 2.6 compatibility
        with patch_open as mock_open:
            spec = six.StringIO if six.PY3 else file
            mock_open.return_value = MagicMock(spec=spec)
            with patch_get_by_name:
                self._call_fut(args)
        self.assertEqual(
            mock_stdout.getvalue(),
            '{0.plugin} plugin site_src files written to {0.src_dir}\n'
            .format(args))


class TestBuildParser(unittest.TestCase):
    """Unit tests for build sub-command parser.
    """
    def _parse_args(self, *args):
        """Set up sub-command parser, parse args, and return result.
        """
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        main._setup_build_parser(subparsers)
        return parser.parse_args(*args)

    def test_build_parser_src_dir_default(self):
        """build parser sets src_dir default to relative cwd
        """
        args = self._parse_args(['build'])
        self.assertEqual(args.src_dir, '.')

    def test_build_parser_src_dir_value(self):
        """build parser sets src_dir to arg value
        """
        args = self._parse_args('build -s foo'.split())
        self.assertEqual(args.src_dir, 'foo')

    def test_build_parser_func_do_build(self):
        """build action function is do_build
        """
        args = self._parse_args(['build'])
        self.assertEqual(args.func, main.do_build)


class TestServeParser(unittest.TestCase):
    """Unit tests for serve sub-command parser.
    """
    def _parse_args(self, *args):
        """Set up sub-command parser, parse args, and return result.
        """
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        main._setup_serve_parser(subparsers)
        return parser.parse_args(*args)

    def test_serve_parser_ip_addr_default(self):
        """serve parser sets ip address default to 127.0.0.1
        """
        args = self._parse_args(['serve'])
        self.assertEqual(args.IP_ADDR, '127.0.0.1')

    def test_serve_parser_ip_addr_arg(self):
        """serve parser sets ip address to given arg
        """
        args = self._parse_args('serve 8888 192.168.1.5'.split())
        self.assertEqual(args.IP_ADDR, '192.168.1.5')

    def test_serve_parser_port_default(self):
        """serve parser sets ip address default to 127.0.0.1
        """
        args = self._parse_args(['serve'])
        self.assertEqual(args.PORT, '8080')

    def test_serve_parser_port_arg(self):
        """serve parser sets port to given arg
        """
        args = self._parse_args('serve 8888'.split())
        self.assertEqual(args.PORT, '8888')

    def test_serve_parser_src_dir_default(self):
        """serve parser sets src_dir default to relative cwd
        """
        args = self._parse_args(['serve'])
        self.assertEqual(args.src_dir, '.')

    def test_serve_parser_src_dir_value(self):
        """serve parser sets src_dir to arg value
        """
        args = self._parse_args('serve -s foo'.split())
        self.assertEqual(args.src_dir, 'foo')

    def test_serve_parser_func_do_serve(self):
        """serve action function is do_serve
        """
        args = self._parse_args(['serve'])
        self.assertEqual(args.func, main.do_serve)


class TestInfoParser(unittest.TestCase):
    """Unit tests for info sub-command parser.
    """
    def _parse_args(self, *args):
        """Set up sub-command parser, parse args, and return result.
        """
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        main._setup_info_parser(subparsers)
        return parser.parse_args(*args)

    def test_info_parser_src_dir_default(self):
        """info parser sets src_dir default to relative cwd
        """
        args = self._parse_args(['info'])
        self.assertEqual(args.src_dir, '.')

    def test_info_parser_src_dir_value(self):
        """info parser sets src_dir to arg value
        """
        args = self._parse_args('info -s foo'.split())
        self.assertEqual(args.src_dir, 'foo')

    def test_info_parser_func_do_info(self):
        """info action function is do_info
        """
        args = self._parse_args(['info'])
        self.assertEqual(args.func, main.do_info)


class TestPluginsParser(unittest.TestCase):
    """Unit tests for plugins sub-command parser.
    """
    def _parse_args(self, *args):
        """Set up sub-command parser, parse args, and return result.
        """
        parser_template = argparse.ArgumentParser(add_help=False)
        parser = argparse.ArgumentParser(parents=[parser_template])
        subparsers = parser.add_subparsers()
        main._setup_plugins_parser(subparsers, parser_template)
        return parser.parse_args(*args)

    def test_plugins_parser_func_list_plugins(self):
        """plugins list action function is plugin.list_plugins
        """
        args = self._parse_args('plugins list'.split())
        self.assertEqual(args.func, main.plugin.list_plugins)


class TestFiltersParser(unittest.TestCase):
    """Unit tests for filters sub-command parser.
    """
    def _parse_args(self, *args):
        """Set up sub-command parser, parse args, and return result.
        """
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        main._setup_filters_parser(subparsers)
        return parser.parse_args(*args)

    def test_filters_parser_func_list_filters(self):
        """filters list action function is _filter.list_filters
        """
        args = self._parse_args('filters list'.split())
        self.assertEqual(args.func, main._filter.list_filters)

########NEW FILE########
__FILENAME__ = test_plugin
# -*- coding: utf-8 -*-
"""Unit tests for blogofile plugin module.
"""
try:
    import unittest2 as unittest        # For Python 2.6
except ImportError:
    import unittest                     # flake8 ignore # NOQA
from mock import (
    MagicMock,
    patch,
)
from .. import plugin


class TestGetByName(unittest.TestCase):
    """Unit tests for get_by_name function.
    """
    def _call_fut(self, *args):
        """Call the fuction under test.
        """
        return plugin.get_by_name(*args)

    def test_get_by_name(self):
        """get_by_name returns plugin with matching name
        """
        mock_plugin = MagicMock(__dist__={'config_name': 'foo'})
        with patch.object(plugin, 'iter_plugins', return_value=[mock_plugin]):
            p = self._call_fut('foo')
        self.assertEqual(p, mock_plugin)


class TestPluginTools(unittest.TestCase):
    """Unit tests for PluginTools class.
    """
    def _get_target_class(self):
        from ..plugin import PluginTools
        return PluginTools

    def _make_one(self, *args):
        return self._get_target_class()(*args)

    def test_init_module_attribute(self):
        """PluginTools instance has module attribute
        """
        mock_plugin_module = MagicMock(
            config={'name': 'foo'}, __name__='mock_plugin', __file__='./foo')
        tools = self._make_one(mock_plugin_module)
        self.assertEqual(tools.module, mock_plugin_module)

    def test_init_namespace_attribute(self):
        """PluginTools instance namespace attr is plugin module config var
        """
        mock_plugin_module = MagicMock(
            config={'name': 'foo'}, __name__='mock_plugin', __file__='./foo')
        tools = self._make_one(mock_plugin_module)
        self.assertEqual(tools.namespace, mock_plugin_module.config)

    def test_init_template_lookup_attribute(self):
        """PluginTools template_lookup attr is mako.lookup.TemplateLookup
        """
        from mako.lookup import TemplateLookup
        mock_plugin_module = MagicMock(
            config={'name': 'foo'}, __name__='mock_plugin', __file__='./foo')
        tools = self._make_one(mock_plugin_module)
        self.assertIsInstance(tools.template_lookup, TemplateLookup)

    def test_init_logger_name(self):
        """PluginTools logger has plugin name
        """
        mock_plugin_module = MagicMock(
            config={'name': 'foo'}, __name__='mock_plugin', __file__='./foo')
        tools = self._make_one(mock_plugin_module)
        self.assertEqual(
            tools.logger.name,
            'blogofile.plugins.{0}'.format(mock_plugin_module.__name__))

    def test_template_lookup(self):
        """_template_lookup calls mako.lookup.TemplateLookup w/ expected args
        """
        mock_plugin_module = MagicMock(
            config={'name': 'foo'}, __name__='mock_plugin', __file__='./foo')
        with patch.object(plugin, 'TemplateLookup') as mock_TemplateLookup:
            self._make_one(mock_plugin_module)
        mock_TemplateLookup.assert_called_once_with(
            directories=['_templates', './site_src/_templates'],
            input_encoding='utf-8', output_encoding='utf-8',
            encoding_errors='replace')

    def test_get_src_dir(self):
        """get_src_dir method returns expected directory name
        """
        mock_plugin_module = MagicMock(
            config={'name': 'foo'}, __name__='mock_plugin',
            __file__='/foo/bar.py')
        tools = self._make_one(mock_plugin_module)
        src_dir = tools.get_src_dir()
        self.assertEqual(src_dir, '/foo/site_src')

    def test_add_template_dir_append(self):
        """add_template_dir appends to template_lookup.directories by default
        """
        mock_plugin_module = MagicMock(
            config={'name': 'foo'}, __name__='mock_plugin',
            __file__='/foo/bar.py')
        tools = self._make_one(mock_plugin_module)
        tools.add_template_dir('baz')
        self.assertEqual(
            tools.template_lookup.directories,
            ['_templates', '/foo/site_src/_templates', 'baz'])

    def test_add_template_dir_prepend(self):
        """add_template_dir prepends to template_lookup.directories
        """
        mock_plugin_module = MagicMock(
            config={'name': 'foo'}, __name__='mock_plugin',
            __file__='/foo/bar.py')
        tools = self._make_one(mock_plugin_module)
        tools.add_template_dir('baz', append=False)
        self.assertEqual(
            tools.template_lookup.directories,
            ['baz', '_templates', '/foo/site_src/_templates'])

    def test_materialize_template(self):
        """materialize_template calls template.materialize_template w/ exp args
        """
        mock_plugin_module = MagicMock(
            config={'name': 'foo'}, __name__='mock_plugin',
            __file__='/foo/bar.py')
        # nested contexts for Python 2.6 compatibility
        with patch.object(plugin, 'TemplateLookup') as mock_TL:
            tools = self._make_one(mock_plugin_module)
            with patch.object(
                plugin.template, 'materialize_template') as mock_mt:
                tools.materialize_template(
                    'foo.mako', 'bar.html', {'flip': 'flop'})
        mock_mt.assert_called_once_with(
            'foo.mako', 'bar.html', attrs={'flip': 'flop'},
            caller=mock_plugin_module, lookup=mock_TL())

    def test_initialize_controllers(self):
        """initialize_controllers calls controller module init function
        """
        mock_controllers_module_init = MagicMock(name='mock_init')
        mock_controller = MagicMock(
            name='mock_controller',
            mod=MagicMock(
                name='mock_mod',
                init=mock_controllers_module_init))
        mock_plugin_module = MagicMock(
            __name__='mock_plugin', __file__='/foo/bar.py',
            config=MagicMock(
                name='mock_config',
                controllers={'blog': mock_controller}))
        tools = self._make_one(mock_plugin_module)
        tools.initialize_controllers()
        mock_controllers_module_init.assert_called_once_with()

    def test_run_controllers(self):
        """run_controllers calls controller module run function
        """
        mock_controllers_module_run = MagicMock(name='mock_rub')
        mock_controller = MagicMock(
            name='mock_controller',
            mod=MagicMock(
                name='mock_mod',
                run=mock_controllers_module_run))
        mock_plugin_module = MagicMock(
            __name__='mock_plugin', __file__='/foo/bar.py',
            config=MagicMock(
                name='mock_config',
                controllers={'blog': mock_controller}))
        tools = self._make_one(mock_plugin_module)
        tools.run_controllers()
        mock_controllers_module_run.assert_called_once_with()

########NEW FILE########
__FILENAME__ = test_server
# -*- coding: utf-8 -*-
## Mechanize isn't supported on Python 3.x
## How can I force nose to run these tests as Python 2.x?

# import unittest
# import tempfile
# import shutil
# import os
# import mechanize
# from .. import main
# from .. import server


# class TestServer(unittest.TestCase):

#     def setUp(self):
#         main.do_debug()
#         #Remember the current directory to preserve state
#         self.previous_dir = os.getcwd()
#         #Create a staging directory that we can build in
#         self.build_path = tempfile.mkdtemp()
#         #Change to that directory just like a user would
#         os.chdir(self.build_path)
#         #Reinitialize the configuration
#         main.config.init()
#         #Build the unit test site
#         main.main("init blog_unit_test")
#         main.main("build")
#         #Start the server
#         self.port = 42042
#         self.url = "http://localhost:"+str(self.port)
#         self.server = server.Server(self.port)
#         self.server.start()

#     def tearDown(self):
#         #Revert the config overridden options
#         main.config.override_options = {}
#         #Stop the server
#         self.server.shutdown()
#         #go back to the directory we used to be in
#         os.chdir(self.previous_dir)
#         #Clean up the build directory
#         shutil.rmtree(self.build_path)

#     def testBuildAndServe(self):
#         br = mechanize.Browser()
#         #Test the index page
#         br.open(self.url)
#         #Click the title
#         br.follow_link(text_regex="Your Blog's Name")
#         assert br.geturl().strip("/") == self.url
#         #Go to the chronological page
#         br.follow_link(text_regex="chronological blog page")
#         assert br.geturl() == self.url + "/blog/"
#         #Go to page 2
#         br.follow_link(text_regex="Next Page")
#         #Go to page 3
#         br.follow_link(text_regex="Next Page")
#         #Go back to page 2
#         br.follow_link(text_regex="Previous Page")
#         #Go back to page 1
#         br.follow_link(text_regex="Previous Page")
#         assert br.geturl() == self.url + "/blog/page/1/"
#         #Go to a permalink page:
#         br.open("/blog/2009/08/29/post-seven/")
#         #Go to one it's categories:
#         br.follow_link(text_regex="general stuff")
#         #Go to the next category page
#         br.follow_link(text_regex="Next Page")
#         #Come back to the 1st category page
#         br.follow_link(text_regex="Previous Page")
#         assert br.geturl() == self.url + "/blog/category/general-stuff/1/"
#         #Go to a archive page:
#         br.open("/blog/archive/2009/08/1/")
#         #Go to the next page of this archive
#         br.follow_link(text_regex="Next Page")
#         #Come back to the 1st archive page
#         br.follow_link(text_regex="Previous Page")
#         assert br.geturl() == self.url + "/blog/archive/2009/08/1/"

#     def testServeSubdirectory(self):
#         #The site was already built in setUp
#         #Rebuild the site with a new config:
#         main.config.site_url = "http://www.yoursite.com/people/ryan"
#         main.do_build({},load_config=False)
#         br = mechanize.Browser()

########NEW FILE########
__FILENAME__ = test_util
# -*- coding: utf-8 -*-
"""Unit tests for blogofile util module.
"""
try:
    import unittest2 as unittest        # For Python 2.6
except ImportError:
    import unittest                     # flake8 ignore # NOQA
from mock import (
    MagicMock,
    patch,
    )
import six
from .. import util


@patch.object(util.bf, 'config')
class TestCreateSlug(unittest.TestCase):
    """Unit tests for create_slug function.
    """
    def _call_fut(self, *args):
        """Call the fuction under test.
        """
        return util.create_slug(*args)

    def test_ascii(self, mock_config):
        """create_slug returns expected result for ASCII title
        """
        mock_config.site = MagicMock(slugify=None, slug_unicode=None)
        mock_config.blog = MagicMock(slugify=None)
        slug = self._call_fut('Foo Bar!')
        self.assertEqual(slug, 'foo-bar')

    def test_unidecode(self, mock_config):
        """create_slug returns expected ASCII result for Unicode title
        """
        mock_config.site = MagicMock(slugify=None, slug_unicode=None)
        mock_config.blog = MagicMock(slugify=None)
        slug = self._call_fut(six.u('\u5317\u4EB0'))
        self.assertEqual(slug, 'bei-jing')

    def test_unicode(self, mock_config):
        """create_slug returns expected Unicode result for Unicode title
        """
        mock_config.site = MagicMock(slugify=None, slug_unicode=True)
        mock_config.blog.slugify = None
        slug = self._call_fut(six.u('\u5317\u4EB0'))
        self.assertEqual(slug, six.u('\u5317\u4EB0'))

    def test_user_site_slugify(self, mock_config):
        """create_slug uses user-defined config.site.slugify function
        """
        mock_config.site = MagicMock(slugify=lambda s: 'bar-foo')
        mock_config.blog = MagicMock(slugify=None)
        slug = self._call_fut('Foo Bar!')
        self.assertEqual(slug, 'bar-foo')

    def test_user_blog_slugify(self, mock_config):
        """create_slug uses user-defined config.blog.slugify function
        """
        mock_config.site = MagicMock(slugify=None)
        mock_config.blog = MagicMock(slugify=lambda s: 'deprecated')
        slug = self._call_fut('Foo Bar!')
        self.assertEqual(slug, 'deprecated')


@patch.object(util.bf, 'config')
class TestSitePathHelper(unittest.TestCase):
    """Unit tests for site_path_helper function."""
    def _call_fut(self, *args, **kwargs):
        """Call the fuction under test.
        """
        return util.site_path_helper(*args, **kwargs)

    def test_root_path(self, mock_config):
        """site_path_helper returns expected path in site root
        """
        mock_config.site.url = 'http://www.blogofile.com'
        path = self._call_fut('blog')
        self.assertEqual(path, '/blog')

    def test_subdir_path(self, mock_config):
        """site_path_helper returns expected path in site subdir
        """
        mock_config.site.url = 'http://www.blogofile.com/~ryan/site1'
        path = self._call_fut('blog')
        self.assertEqual(path, '/~ryan/site1/blog')

    def test_leading_slash(self, mock_config):
        """site_path_helper returns expected path when arg has leading slash
        """
        mock_config.site.url = 'http://www.blogofile.com/~ryan/site1'
        path = self._call_fut('/blog')
        self.assertEqual(path, '/~ryan/site1/blog')

    def test_multiple_args(self, mock_config):
        """site_path_helper returns expected path for multiple args
        """
        mock_config.site.url = 'http://www.blogofile.com/~ryan/site1'
        path = self._call_fut('blog', 'category1')
        self.assertEqual(path, '/~ryan/site1/blog/category1')

    def test_trailing_slash(self, mock_config):
        """site_path_helper returns path w/ trailing slash when requested
        """
        mock_config.site.url = 'http://www.blogofile.com'
        path = self._call_fut('blog', trailing_slash=True)
        self.assertEqual(path, '/blog/')

    def test_root_slash(self, mock_config):
        mock_config.site.url = 'http://www.blogofile.com'
        path = self._call_fut(trailing_slash=True)
        self.assertEqual(path, '/')

########NEW FILE########
__FILENAME__ = util
# -*- coding: utf-8 -*-
"""Blogofile utility functions.
"""
from __future__ import print_function
import re
import os
import sys
import logging
import fileinput
try:
    from urllib.parse import urlparse   # For Python 2
except ImportError:
    from urlparse import urlparse       # For Python 3; flake8 ignore # NOQA
from markupsafe import Markup
import six
from unidecode import unidecode
from .cache import bf
bf.util = sys.modules['blogofile.util']


logger = logging.getLogger("blogofile.util")

# Word separators and punctuation for slug creation
PUNCT_RE = re.compile(r'[\t !"#$%&\'()*\-/<=>?@\[\\\]^_`{|},.]+')

html_escape_table = {
    "&": "&amp;",
    '"': "&quot;",
    "'": "&apos;",
    ">": "&gt;",
    "<": "&lt;",
    }


def html_escape(text):
    """Produce entities within text.
    """
    L = []
    for c in text:
        L.append(html_escape_table.get(c, c))
    return "".join(L)


def should_ignore_path(path):
    """See if a given path matches the ignore patterns.
    """
    if os.path.sep == '\\':
        path = path.replace('\\', '/')
    for p in bf.config.site.compiled_file_ignore_patterns:
        if p.match(path):
            return True
    return False


def mkdir(newdir):
    """works the way a good mkdir should :)
    - already exists, silently complete
    - regular file in the way, raise an exception
    - parent directory(ies) does not exist, make them as well
    """
    if os.path.isdir(newdir):
        pass
    elif os.path.isfile(newdir):
        raise OSError("a file with the same name as the desired "
                      "dir, '{0}', already exists.".format(newdir))
    else:
        head, tail = os.path.split(newdir)
        if head and not os.path.isdir(head):
            mkdir(head)
        # print "mkdir {0}.format(repr(newdir))
        if tail:
            os.mkdir(newdir)


def url_path_helper(*parts):
    """
    path_parts is a sequence of path parts to concatenate

    >>> url_path_helper("one","two","three")
    'one/two/three'
    >>> url_path_helper(("one","two"),"three")
    'one/two/three'
    >>> url_path_helper("one/two","three")
    'one/two/three'
    >>> url_path_helper("one","/two/","three")
    'one/two/three'
    >>> url_path_helper("/one","two","three")
    'one/two/three'
    """
    new_parts = []
    for p in parts:
        if hasattr(p, "__iter__") and not isinstance(p, str):
            # This part is a sequence itself, recurse into it
            p = path_join(*p, **{'sep': "/"})
        p = p.strip("/")
        if p in ("", "\\", "/"):
            continue
        new_parts.append(p)

    if len(new_parts) > 0:
        return "/".join(new_parts)
    else:
        return "/"


def site_path_helper(*parts, **kwargs):
    """Make an absolute path on the site, appending a sequence of path parts
    to the site path.

    Use ``trailing_slash=True`` as the final argument to get a slash appended
    to the path.
    """
    try:
        trailing_slash = kwargs["trailing_slash"]
    except KeyError:
        trailing_slash = False
    site_path = urlparse(bf.config.site.url).path
    path = url_path_helper(site_path, *parts)
    if not path.startswith("/"):
        path = "/" + path
    if trailing_slash and not path.endswith("/"):
        path += "/"
    return path


def fs_site_path_helper(*parts):
    """Build a path relative to the built site inside the _site dir.

    >>> bf.config.site.url = "http://www.blogofile.com/ryan/site1"
    >>> fs_site_path_helper()
    ''
    >>> fs_site_path_helper("/blog","/category","stuff")
    'blog/category/stuff'
    """
    return path_join(url_path_helper(*parts).strip("/"))


#TODO: seems to have a lot in common with url_path_helper; commonize
def path_join(*parts, **kwargs):
    """A better os.path.join.

    Converts (back)slashes from other platforms automatically
    Normally, os.path.join is great, as long as you pass each dir/file
    independantly, but not if you (accidentally/intentionally) put a slash in

    If sep is specified, use that as the seperator rather than the
    system default.
    """
    if 'sep' in kwargs:
        sep = kwargs['sep']
    else:
        sep = os.sep
    if os.sep == "\\":
        wrong_slash_type = "/"
    else:
        wrong_slash_type = "\\"
    new_parts = []
    for p in parts:
        if hasattr(p, "__iter__") and not isinstance(p, str):
            #This part is a sequence itself, recurse into it
            p = path_join(*p)
        if p in ("", "\\", "/"):
            continue
        new_parts.append(p.replace(wrong_slash_type, os.sep))
    return sep.join(new_parts)


def recursive_file_list(directory, regex=None):
    """Recursively walk a directory tree and find all the files matching regex.
    """
    if type(regex) == str:
        regex = re.compile(regex)
    for root, dirs, files in os.walk(directory):
        for f in files:
            if regex:
                if regex.match(f):
                    yield os.path.join(root, f)
            else:
                yield os.path.join(root, f)


def rewrite_strings_in_files(existing_string, replacement_string, paths):
    """Replace existing_string with replacement_string
    in all the files listed in paths"""
    for line in fileinput.input(paths, inplace=True):
        #inplace=True redirects sys.stdout back to the file
        line = line.replace(existing_string, replacement_string)
        sys.stdout.write(line)


def force_unicode(s, encoding='utf-8', strings_only=False, errors='strict'):  #pragma: no cover
    """
    Force a string to be unicode.

    If strings_only is True, don't convert (some) non-string-like objects.

    Originally copied from the Django source code, further modifications have
    been made.

    Original copyright and license:

        Copyright (c) Django Software Foundation and individual contributors.
        All rights reserved.

        Redistribution and use in source and binary forms, with or without modification,
        are permitted provided that the following conditions are met:

            1. Redistributions of source code must retain the above copyright notice,
               this list of conditions and the following disclaimer.

            2. Redistributions in binary form must reproduce the above copyright
               notice, this list of conditions and the following disclaimer in the
               documentation and/or other materials provided with the distribution.

            3. Neither the name of Django nor the names of its contributors may be used
               to endorse or promote products derived from this software without
               specific prior written permission.

        THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
        ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
        WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
        DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
        ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
        (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
        LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
        ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
        (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
        SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
    """
    if strings_only and is_protected_type(s):
        return s
    if not isinstance(s, str,):
        if hasattr(s, '__unicode__'):
            s = str(s)
        else:
            try:
                s = str(str(s), encoding, errors)
            except UnicodeEncodeError:
                if not isinstance(s, Exception):
                    raise
                # If we get to here, the caller has passed in an Exception
                # subclass populated with non-ASCII data without special
                # handling to display as a string. We need to handle this
                # without raising a further exception. We do an
                # approximation to what the Exception's standard str()
                # output should be.
                s = ' '.join([force_unicode(arg, encoding, strings_only,
                        errors) for arg in s])
    elif not isinstance(s, str):
        # Note: We use .decode() here, instead of unicode(s, encoding,
        # errors), so that if s is a SafeString, it ends up being a
        # SafeUnicode at the end.
        s = s.decode(encoding, errors)
    return s


def create_slug(title, delim='-'):
    """Create a slug from `title`, with words lowercased, and
    separated by `delim`.

    User may provide their own function to do this via `config.site.slugify`.

    `config.site.slug_unicode` controls whether Unicode characters are included
    in the slug as is, or mapped to reasonable ASCII equivalents.
    """
    # Dispatch to user-supplied slug creation function, if one exists
    if bf.config.site.slugify:
        return bf.config.site.slugify(title)
    elif bf.config.blog.slugify:
        # For backward compatibility
        return bf.config.blog.slugify(title)
    # Get rid of any HTML entities
    slug = Markup(title).unescape()
    result = []
    for word in PUNCT_RE.split(slug):
        if not bf.config.site.slug_unicode:
            result.extend(unidecode(word).split())
        else:
            result.append(word)
    slug = six.text_type(delim.join(result)).lower()
    return slug

########NEW FILE########
__FILENAME__ = writer
# -*- coding: utf-8 -*-
"""Write out the static blog to ./_site based on templates found in
the current working directory.
"""

__author__ = "Ryan McGuire (ryan@enigmacurry.com)"

import logging
import os
import re
import shutil
import tempfile

from . import util
from . import config
from . import cache
from . import filter as _filter
from . import controller
from . import plugin
from . import template


logger = logging.getLogger("blogofile.writer")


class Writer(object):

    def __init__(self, output_dir):
        self.config = config
        # Base templates are templates (usually in ./_templates) that are only
        # referenced by other templates.
        self.base_template_dir = util.path_join(".", "_templates")
        self.output_dir = output_dir

    def __load_bf_cache(self):
        # Template cache object, used to transfer state to/from each template:
        self.bf = cache.bf
        self.bf.writer = self
        self.bf.logger = logger

    def write_site(self):
        self.__load_bf_cache()
        self.__setup_temp_dir()
        try:
            self.__setup_output_dir()
            self.__calculate_template_files()
            self.__init_plugins()
            self.__init_filters_controllers()
            self.__run_controllers()
            self.__write_files()
        finally:
            self.__delete_temp_dir()

    def __setup_temp_dir(self):
        """Create a directory for temporary data.
        """
        self.temp_proc_dir = tempfile.mkdtemp(prefix="blogofile_")
        # Make sure this temp directory is added to each template lookup:
        for engine in self.bf.config.templates.engines.values():
            try:
                engine.add_default_template_path(self.temp_proc_dir)
            except AttributeError:
                pass

    def __delete_temp_dir(self):
        "Cleanup and delete temporary directory"
        shutil.rmtree(self.temp_proc_dir)

    def __setup_output_dir(self):
        """Setup the staging directory"""
        if os.path.isdir(self.output_dir):
            # I *would* just shutil.rmtree the whole thing and recreate it,
            # but I want the output_dir to retain its same inode on the
            # filesystem to be compatible with some HTTP servers.
            # So this just deletes the *contents* of output_dir
            for f in os.listdir(self.output_dir):
                f = util.path_join(self.output_dir, f)
                try:
                    os.remove(f)
                except OSError:
                    pass
                try:
                    shutil.rmtree(f)
                except OSError:
                    pass
        util.mkdir(self.output_dir)

    def __calculate_template_files(self):
        """Build a regex for template file paths"""
        endings = []
        for ending in self.config.templates.engines.keys():
            endings.append("." + re.escape(ending) + "$")
        p = "(" + "|".join(endings) + ")"
        self.template_file_regex = re.compile(p)

    def __write_files(self):
        """Write all files for the blog to _site.

        Convert all templates to straight HTML.  Copy other
        non-template files directly.
        """
        for root, dirs, files in os.walk("."):
            if root.startswith("./"):
                root = root[2:]
            for d in list(dirs):
                # Exclude some dirs
                d_path = util.path_join(root, d)
                if util.should_ignore_path(d_path):
                    logger.debug("Ignoring directory: " + d_path)
                    dirs.remove(d)
            try:
                util.mkdir(util.path_join(self.output_dir, root))
            except OSError:
                pass
            for t_fn in files:
                t_fn_path = util.path_join(root, t_fn)
                if util.should_ignore_path(t_fn_path):
                    # Ignore this file.
                    logger.debug("Ignoring file: " + t_fn_path)
                    continue
                elif self.template_file_regex.search(t_fn):
                    logger.info("Processing template: " + t_fn_path)
                    # Process this template file
                    html_path = self.template_file_regex.sub("", t_fn)
                    template.materialize_template(
                        t_fn_path,
                        util.path_join(root, html_path))
                else:
                    # Copy this non-template file
                    f_path = util.path_join(root, t_fn)
                    logger.debug("Copying file: " + f_path)
                    out_path = util.path_join(self.output_dir, f_path)
                    if self.config.site.overwrite_warning and \
                            os.path.exists(out_path):
                        logger.warn("Location is used more than once: {0}"
                                    .format(f_path))
                    if self.config.site.use_hard_links:
                        # Try hardlinking first, and if that fails copy
                        try:
                            os.link(f_path, out_path)
                        except Exception:
                            shutil.copyfile(f_path, out_path)
                    else:
                        shutil.copyfile(f_path, out_path)

    def __init_plugins(self):
        # Run plugin defined init methods
        plugin.init_plugins()

    def __init_filters_controllers(self):
        # Run filter/controller defined init methods
        _filter.init_filters()
        controller.init_controllers(namespace=self.bf.config.controllers)

    def __run_controllers(self):
        """Run all the controllers in the _controllers directory.
        """
        namespaces = [self.bf.config]
        for plugin in list(self.bf.config.plugins.values()):
            if plugin.enabled:
                namespaces.append(plugin)
        controller.run_all(namespaces)

########NEW FILE########
__FILENAME__ = blogger2blogofile
#!/usr/bin/env python

__author__ = "Seth de l'Isle"

#### Usage:
## You can generate a Blogger export file by logging into blogger,
## then going to Settings -> Basic -> Export Blog.  You will get a
## file to download with the current date in the name and a .xml
## extension.  Running blogger2blogofile.py in that directory, with
## the filename of the export file as the only argument will generate
## a _posts directory ready for use with Blogofile.


import sys
try:
    import feedparser
except ImportError:
    print >> sys.stderr, """This tool requires the universal feedparser module.

Depending on your tools, try:
    apt-get install python-feedparser
or: 
    easy_install feedparser

or check out the download files at http://code.google.com/p/feedparser/downloads/list
 """ 
    sys.exit()

import yaml
import time
import os
import codecs
import unittest
import pickle
import shutil
import base64
import tarfile
import io
import urlparse

class Blogger:
    def __init__(self, dumpFile):
        self.feed = feedparser.parse(dumpFile)
        self.entries = [Entry(entry) for entry in self.feed.entries if self.is_post(entry)]

    @staticmethod
    def is_post(entry): 
        # tag.term looks like 'http://schemas.google.com/blogger/2008/kind#post' 
        return any([tag for tag in entry.tags if 'kind#post' in tag.term])

    def write_posts(self, targetPath):
        for entry in self.entries:
            entry.write_post(targetPath)

class Entry:
    def __init__(self, feedEntry):
        self.feedEntry = feedEntry
        fileNameDate = self.blogofile_date('published').replace('/', '-')
        self.build_header()
        dateNameFile = fileNameDate + self.feedEntry.title.replace('/', '-') + '.html'
        if self.data['draft']:
            self.postFile = dateNameFile 
        else:
            permalink = self.data['permalink']
            bloggerSlug = os.path.basename(urlparse.urlsplit(permalink)[2])
            self.postFile = time.strftime("%Y-%m-%d", self.feedEntry.published_parsed) + '-' + bloggerSlug

    def build_header(self):
        allTags = self.feedEntry.tags
        tags = [tag.term for tag in allTags 
                        if not 'schemas.google.com' in tag.term]

        data = {'tags': tags,
                'date': self.blogofile_date('published'),
                'updated': self.blogofile_date('updated'),
                'title': self.feedEntry.title,
                'encoding': 'utf8',
                'draft': bool('app_draft' in self.feedEntry.keys() and 
                               self.feedEntry.app_draft == 'yes'),
                'author': self.feedEntry.author_detail.name}

        if 'link' in self.feedEntry.keys():
            data['permalink'] = urlparse.urlparse(self.feedEntry['link']).path

        self.data = data


    def write_post(self, targetPath):
        entryPath = os.path.join(targetPath, self.postFile)

        if os.path.isfile(entryPath):
            print >> sys.stderr, "Skipping.  Target file already exists: " + entryPath
        else:
            targetFile = open(entryPath, 'w')
            print >> targetFile, '---'
            print >> targetFile, self.blogofile_header()
            print >> targetFile, '---'
            targetFile.write(codecs.encode(self.feedEntry.content[0].value, 'utf8'))

    def blogofile_header(self):
        return yaml.safe_dump(self.data)

    def blogofile_date(self, dateType):
        dateStruct = {'published': self.feedEntry.published_parsed,
                      'updated': self.feedEntry.updated_parsed}[dateType]
        return time.strftime("%Y/%m/%d %H:%M:%S", dateStruct)

#base64 encoded test files gzipped tarballed as a python string
testData = (
"""H4sIAJVWaU0AA+1ZbY/buBHOZ/0KwkG6G3RtkdT79jZoNrkURosiSK57KHrFgpZoSWdZ0klUHOfX
d2Yk21pnnUva3AUFloBlWSKH8z7Dx0utk1o1rW6mSaOWZlbn8arQj77m4DB818VvEXh8/I3DcTl/
JITnCCmlwHnC893gEeNflYsTo2uNahh71Ca6yNvTkv/a+//TEcdVvb1tdGrBJa7K1jRdbKrGqrl1
Hi/33mG9gtvXdPsyj41VCyu+vV10eWHy8vbWSuihtM6T2rHenqm6vgVqpqmKM6t2rRur9qz27VlX
J8roBJ751o3kgk95MOXeDyK8dPilK2fCk1MeXnJu1QEuaLuFyU2hYUVopWMat8QYkoqs2ORrbfW8
39J9LYD/8zluYc0Da+5ZcxFZcwd+udKaw5cIfbhYphYCuRYSbx3rTS1c3KXIy1ULxIVnnRe18K0U
CKbCSklGEYCQWaOXOCO0bjJj6kvb3mw2s0VRpaluZnG1tlF/re15kRCBwwPHiRxX+JEf2XXVmtZO
9FJ1hbE91w0gAlzf9UTk+tyNQH7gF/gw2xqFl9y6AaUWeaxMXpW2MtX6j+/XBbwROK3RqGgprRud
5GgJB9RRSxfkkZ6l7jAv/QPzMvhtmJfhmPnoFPNgjz3zjrBuWl0s4U4i8w4aw3EthYRUisZwyBjO
kTEcNIbRzRpnHIzRxpleq3aWVlVaaBJpEM+WnIf2Ki+TxygKrCJV0wLk1+WfIpLicu8xLoeppP1C
LUgEcK2/A+cucu66R2p3PStF9sCzuvcw17fadLTTsfpRSXbZPoaZAc4cSIdIOiKlDCb0TtOom2qZ
F9rmIgIrOl4QSumDIT3pebCQeDdZc2sqo5B/D/wHjOc5+EJ1Jqua20QbldNL967agUQKe6c9mVKR
6jyI67faZCzRrDibQ8KEZxTJoMaeDKig/VCZ7M/dQjdGx1mZ/9KRauFlhJb3OQjpE9mccgWwBR5w
ORLtAiSK6MH0Hg+doVmn9zqmT7LV3QKyeTbOIj6Id3/SgCjChDHOGb6HGvB9vA2Q2d7dh0zlg7+b
aqOahBWqSfW0jVWhGbC9riA6t6yFDKtSUE3AD5qGhYE41h47P6GrpzBb0mJItVS6cb1j3Wx1CzeU
wzAD65JeUOAER4ETYOAsVIs8ByHc4/c464ScIuu9sTOzRuOFg7uXaQf84wN0y7dn71TR0U+HkrSp
Q8w8odcHL6rl4EfhERdhYKWwe4o7p4cd60LlJU4P8TFukyJ11BiQj4B8xO+YEiuBOK4q0oVaMoMu
Y1dVIsotEUZo5Fqzb11/v/U4VPgpeEqz/f37PyGEL6n/44Hn+NLD/g/C+aH/+z3Gb9T/Hfo8d4hI
AX1d8AP3L93gUgYzHoRTHlFEekd9HlSQ54YpBhtDqgSuwDGLLUs7DV0Hg3QHj3JoJMqUmUyzuqje
sfOfOu46S7ou6KrpKi9YnRdq+ZQVOmGmArJJ3sZd20Ifwqoly6oN+8eHhV71dPKWtV2tm7xqcHbV
Neyv6oNaZfT6pw5EcfsHwElDKX1ZNUYtCv2HctHWf1Lxqqw2sFkK/PWPTAZUlyo2bKFj1bX6gm2r
juG8C7Yjlql3er91v66Gogx8dusZ6x/8qIviAhUAO5NKqlKzqsaWShUM9mug94M3cHskE+lC0JXj
1eUnnoR0L2bsDapIlSCl6bW8M0aVlvkH1CU8xJqPSiQJoUA12wu26AwrK2JtVeoNzfu+TDFFM9MA
xYJ6wBn7btEw+9lwJQ0yVeRpeTVBg+tmwmKQt1ZJApJdTXj/u61VvP9dgH6uJqaZxoq0MMWCB1UD
FgPJRZVs4auBT/LsO8WwXbqaDJ0S1eKynW3yFRwXklzNqia18Zf9CjqmS2jx/Cm4rZTXugHR8pY7
s5/rdMLITa8m11v2Y14kS93phv3rL69e/o2dY/uVlh2Rwrgq9NLYy6SYYfV8esFevJhe/3P69vnU
mfF+dtxoUMc7vWMHV0KbrMtWt/ZiO22VDXPtpwz8sV8tZ95nLbVh4tN/X7BlU62B00FK9qKfDfrJ
1yko3FxN7hN1wjKdpxm+lf6EtU2811wHTqWSexRX46+dYm2TdeuFHdphbJ/Spe0JWb+fnlb1Jk9M
djVxORgbnMRW8EFb2mRUMuzHTjB5dq2QTJPrFqI/qyCOF2NjQeB/pI8RXXtwHJt8cnDQOdtU5ZnZ
JQ/yajjcdui1c5ZWGHO4Tx/gFBPNljJUBUHTatXEWR8mkOh+1pALgIvneaLOWpa/zjBaNlmOIbDP
fH2ygQ6+bilxFUUfiLBrwj6osktUCwmKwrPRuxwxh99dU+7fwO6qhb1AANWiBBRoQG8JxxeatK4g
j8FLmA2bz6FjjVcQ36CabZMX4FEgWo3zoC+tkv0+/ZK9kIOIS8ybpBuM9BzCGMsAKA9a4ckC7KLA
vLPJQOT5eNnkS5PUpFco8F8iE7902LlAncBMCnkJ2TiO+qab7T31EPBPXvInkcDrNX/yUjwJOd1/
/CSkezF5NmRH8iMixqh5Ijm+VAx06wu0PuhhzDvmyXKUYjXUkHVeYIrtwyRRsVZ6txTr25ose5/g
urxP8F28TZ7tMvSusx9JBr6Yx+AzKNuwc4s8jzyurboyaVmRr3rW13D66k875e6L5MAq0cfmdrQ6
bapNS/5dvdO9+4C/FAmVElhSEwcdnKTAuvm6xnrbF7k5eNlsAIo+QoXC+1Ch6HC+E5LOeHCgg/P1
XAZ4sJvD+REPeobgowShIYPI0BtEhsagkEugkHcECo1wFXHAVfCQOgMdrPS2VibOSP8DuML9yIWT
qRf5gRN60ncdSqDgTXt8hQCmw5FMnMRS5AhLkXAQajTMwsOglOPDqYQz4ms00IthIwthIgSLPASL
/GOwaIR0yfDTQqFibSHsnZGnvcdO7zgsFcPHg5RT8Ko1AUQHCR0Op+fdmZNgoQNEJEdiOc5YLAca
TT6SyaFjqOMjhhQcyeSEB5mc6H8HwD62ImFIB5HAq04YzZUH6WDZgN65ZBAXDeIeG8QdGcT9CtDj
vcyP7eGdhB69kWkQOurRO4+gRw8BAO8YevRGIeL9Soh8vjcRqDRiOLrjQP4oLnw0RAFlqYRkQcDS
GLYB/WNOFl+QvS/Y0G1AXn5F/LHrMX+EK7UEGL1BvGgEZvoBJhE/vJtE/OgAZgafxCFPgZmBuANm
BvKzwczAGYOZgUuIY4CcB8deGAQExdys+vMLZGSCkNp0tN1pRJOgnoF+iGBfKI7oh7Knv6yqhGCl
z6QcuiPKyHnoj7HS8DTc/WmsNAx3+R+pRFbae9wxRhrxu9aM4AbxrX75gJFG8mOMNHLGGGnkfgIj
jSizRZjZomCPkUbhf4eR3hf+UXQCIxVwXk/HNRSqZUg1FBLtgJE6Qu5KaP/HCqd/Vjj9tcLdccAJ
7v0WESe4fwdVFTz4ElhV8PAueCp4ROVeHBlXgPh7/FSA2ASgir5V2JVraBXuQqhCeEcYqoDGYQyi
gqXA+dHIQiDcL0R0H44q5DE/UPVT5CMlHtLR3jswVWAvkPYbprQPKQubHLKPdI8hVQFtwYDgiCkP
EcFx/B5T9XYIjpD+8T8JAv9YoldhTz6iJoo/IK4P42E8jIfxMB7Gw3gY33b8ByuzBgEAKAAA""")

testDataFile = io.BytesIO(base64.b64decode(testData))
testDataTar = tarfile.open("tar",  mode='r:gz', fileobj=testDataFile)
entryPickle = testDataTar.extractfile('feedparser-entry.pickle').read()
draftPickle = testDataTar.extractfile('feedparser-draft.pickle').read()

class MockBlogger(Blogger):
    def __init__(self):
        self.entries = [Entry(pickle.loads(entryPickle)),
                        Entry(pickle.loads(draftPickle))]

class TestBloggerfile(unittest.TestCase):
    def test_entry_header(self):
        entry = Entry(pickle.loads(entryPickle))
        header = yaml.load(entry.blogofile_header())
        assert 'barberry' in header['title'].lower()
        assert header['date'] == "2010/11/08 06:36:00"
        assert 'barberry' in header['permalink'].lower()
        assert 'food' in header['tags']
        assert header['updated'] == "2010/12/07 06:47:27" 
        assert header['author'] == "Seth de l'Isle"
        assert header['draft'] == False
        assert header['encoding'] == 'utf8'

    def test_draft_header(self):
        entry = Entry(pickle.loads(draftPickle))
        header = yaml.load(entry.blogofile_header())
        assert header['draft'] == True

    def test_write_posts(self):
        if os.path.isdir('test_data'):
            shutil.rmtree('test_data')

        os.mkdir('test_data')

        targetPath = os.path.join('test_data', '_posts')
        os.mkdir(targetPath)

        blogger = MockBlogger()
        blogger.write_posts(targetPath)
        assert os.path.isfile(os.path.join(targetPath, 
                                blogger.entries[0].postFile))
        assert os.path.isfile(os.path.join(targetPath,
                                blogger.entries[1].postFile))

        if os.path.isdir('test_data'):
            shutil.rmtree('test_data')

def display_error_and_usage(error):
    print >> sys.stderr, error
    print >> sys.stderr, "Usage: bloggerfile.py BloggerExportfile.xml"
    sys.exit()

if __name__ == '__main__':

        if '-t' in sys.argv:
            try:
                del sys.argv[sys.argv.index('-t')]
                unittest.main()
            except AttributeError:
                display_error_and_usage("Error: bad test option(s): " + " ".join(sys.argv[1:]))
        else:
            if len(sys.argv) > 2:
                display_error_and_usage("Error: extra options after Blogger export file: " + " ".join(sys.argv[2:]))
            try:
                dumpFile = sys.argv[1]
                if not os.path.isfile(dumpFile):
                    raise IOError
                blogger = Blogger(dumpFile)
                if not os.path.isdir('_posts'):
                    os.mkdir('_posts')
                blogger.write_posts('_posts')
            except IndexError:
                display_error_and_usage("Error: Please specify a Blogger export file.")
            except IOError:
                display_error_and_usage("Error: Couldn't read Blogger export file: " + sys.argv[1])

########NEW FILE########
__FILENAME__ = wordpress2blogofile
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Export a Wordpress blog to Blogofile /_posts directory format

This file is a part of Blogofile (http://www.blogofile.com)

This file is MIT licensed, see http://blogofile.com/LICENSE.html for details.

Requirements:

  * An existing Wordpress database hosted on MySQL (other databases probably work
    too, you just need to craft your own db_conn string below.)

  * python-mysqldb (http://mysql-python.sourceforge.net/)
    On Ubuntu this is easy to get: sudo apt-get install python-mysqldb

  * Configure the connection details below and run:

    python wordpress2blogofile.py

    If everything worked right, this will create a _posts directory with your converted posts.
"""

import os
import re
import sys
import yaml
import codecs
import sqlalchemy as sa
import sqlalchemy.orm as orm
from sqlalchemy.ext.declarative import declarative_base

#########################
## Config
#########################
table_prefix = "wp_"

#MySQL config options.
#   (Other databases probably supported, but untested. Just craft your own
#    db_conn string according to the SQLAlchemy docs. See : http://is.gd/M1vU6j )
db_username  = "your_database_username"
db_password  = "your_database_password"
db_host      = "127.0.0.1"
db_port      = "3306"
db_database  = "name_of_wordpress_database"
db_encoding  = "utf8"
db_conn      = "mysql://{db_username}:{db_password}@{db_host}:{db_port}/{db_database}?charset={db_encoding}".format(**locals())

# End Config
#########################


engine = sa.create_engine(db_conn)
Session = orm.scoped_session(
        orm.sessionmaker(autocommit=False,
                         autoflush=False,
                         bind=engine))
Base = declarative_base(bind=engine)

session = Session()


class Post(Base):
    __tablename__ = table_prefix + "posts"
    __table_args__ = {'autoload': True}
    id = sa.Column("ID", sa.Integer, primary_key=True)
    author_id = sa.Column("post_author",
            sa.ForeignKey(table_prefix + 'users.ID'))
    author = orm.relation("User", primaryjoin="Post.author_id == User.id")
    term_relationship = orm.relation("TermRelationship",
                                 primaryjoin="Post.id == TermRelationship.id")

    def categories(self):
        return [r.taxonomy.term.name for r in self.term_relationship
                if r.taxonomy.taxonomy == "category"]

    def tags(self):
        return [r.taxonomy.term.name for r in self.term_relationship
                if r.taxonomy.taxonomy == "post_tag"]

    def __repr__(self):
        return u"<Post '{0}' id={1} status='{2}'>".format(
                self.post_title, self.id, self.post_status)

    def permalink(self):
        site_url = get_blog_url()
        structure = get_blog_permalink_structure()
        structure = structure.replace("%year%", str(self.post_date.year))
        structure = structure.replace("%monthnum%",
                str(self.post_date.month).zfill(2))
        structure = structure.replace("%day%", str(self.post_date.day).zfill(2))
        structure = structure.replace("%hour%",
                str(self.post_date.hour).zfill(2))
        structure = structure.replace("%minute%",
                str(self.post_date.minute).zfill(2))
        structure = structure.replace("%second%",
                str(self.post_date.second).zfill(2))
        structure = structure.replace("%postname%", self.post_name)
        structure = structure.replace("%post_id%", str(self.id))
        try:
            structure = structure.replace("%category%", self.categories()[0])
        except IndexError:
            pass
        try:
            structure = structure.replace("%tag%", self.tags()[0])
        except IndexError:
            pass
        structure = structure.replace("%author%", self.author.user_nicename)
        return site_url.rstrip("/") + "/" + structure.lstrip("/")


class User(Base):
    __tablename__ = table_prefix + "users"
    __table_args__ = {'autoload': True}
    id = sa.Column("ID", sa.Integer, primary_key=True)

    def __repr__(self):
        return u"<User '{0}'>".format(self.user_nicename)


class Term(Base):
    __tablename__ = table_prefix + "terms"
    __table_args__ = {'autoload': True}
    id = sa.Column("term_id", sa.Integer, primary_key=True)
    
    def __repr__(self):
        return u"<Term '{0}'>".format(self.name)


class TermTaxonomy(Base):
    __tablename__ = table_prefix + "term_taxonomy"
    __table_args__ = {'autoload': True}
    id = sa.Column('term_taxonomy_id', sa.Integer, primary_key=True)
    term_id = sa.Column("term_id",
            sa.ForeignKey(table_prefix + "terms.term_id"))
    term = orm.relation("Term", primaryjoin="Term.id == TermTaxonomy.term_id")
    

class TermRelationship(Base):
    __tablename__ = table_prefix + "term_relationships"
    __table_args__ = {'autoload': True}
    id = sa.Column('object_id', sa.ForeignKey(table_prefix + "posts.ID"),
                   primary_key=True)
    taxonomy_id = sa.Column("term_taxonomy_id", sa.ForeignKey(
            table_prefix + "term_taxonomy.term_id"), primary_key=True)
    taxonomy = orm.relation("TermTaxonomy",
            primaryjoin="TermTaxonomy.id == TermRelationship.taxonomy_id")


class WordpressOptions(Base):
    __tablename__ = table_prefix + "options"
    __table_args__ = {'autoload': True}
                            

def get_published_posts(blog_id=0):
    return [p for p in session.query(Post).all() if p.post_status=="publish"
            and p.post_type=="post"]


def get_blog_url(blog_id=0):
    return session.query(WordpressOptions).filter(
            WordpressOptions.blog_id==blog_id).\
            filter(WordpressOptions.option_name=="siteurl").\
            first().option_value


def get_blog_permalink_structure(blog_id=0):
    return session.query(WordpressOptions).filter(
            WordpressOptions.blog_id==blog_id).\
            filter(WordpressOptions.option_name=="permalink_structure").\
            first().option_value
    
if __name__ == '__main__':
    #Output textile files in ./_posts
    if os.path.isdir("_posts"):
        print "There's already a _posts directory here, "\
                "I'm not going to overwrite it."
        sys.exit(1)
    else:
        os.mkdir("_posts")

    post_num = 1
    for post in get_published_posts():
        yaml_data = {
            "title": post.post_title,
            "date": post.post_date.strftime("%Y/%m/%d %H:%M:%S"),
            "permalink": post.permalink(),
            "categories": ", ".join(post.categories()),
            "tags": ", ".join(post.tags()),
            "guid": post.guid
            }
        fn = u"{0}. {1}.html".format(
                str(post_num).zfill(4),
                re.sub(r'[/!:?\-,\']', '', post.post_title.strip().lower().replace(' ', '_')))
        print "writing " + fn
        f = codecs.open(os.path.join("_posts", fn), "w", "utf-8")
        f.write("---\n")
        f.write(yaml.safe_dump(yaml_data, default_flow_style=False, allow_unicode=True).decode("utf-8"))
        f.write("---\n")
        f.write(post.post_content.replace(u"\r\n", u"\n"))
        f.close()
        post_num += 1

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# Blogofile documentation build configuration file, created by
# sphinx-quickstart on Mon Aug 17 21:05:43 2009.
#
# This file is execfile()d with the current directory set to its
# containing dir.
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
#sys.path.append(os.path.abspath('.'))

# -- General configuration ----------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = ["sphinx.ext.graphviz"]
graphviz_output_format = "svg"

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = 'Blogofile'
copyright = '2012, Blogofile Contributors'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '0.8'
# The full version, including alpha/beta/rc tags.
release = '0.8b1'

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

# The reST default role (used for this markup: `text`) to use for all
# documents.
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


# -- Options for HTML output --------------------------------------------------

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
html_static_path = []

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
htmlhelp_basename = 'Blogofiledoc'

# -- Options for LaTeX output -------------------------------------------------

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
# (source start file, target name, title, author, documentclass [howto/manual])
latex_documents = [
  ('index', 'Blogofile.tex', 'Blogofile Documentation',
   'Blogofile Contributors', 'manual'),
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
    ('index', 'blogofile', 'Blogofile Documentation',
     ['Blogofile Contributors'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'Blogofile', 'Blogofile Documentation',
   'Blogofile Contributors', 'Blogofile', 'One line description of project.',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'

########NEW FILE########
