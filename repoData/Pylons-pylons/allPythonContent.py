__FILENAME__ = commands
"""Paster Commands, for use with paster in your project

.. highlight:: bash

The following commands are made available via paster utilizing
setuptools points discovery. These can be used from the command line
when the directory is the Pylons project.

Commands available:

``controller``
    Create a Controller and accompanying functional test
``restcontroller``
    Create a REST Controller and accompanying functional test
``shell``
    Open an interactive shell with the Pylons app loaded

Example usage::

    ~/sample$ paster controller account
    Creating /Users/ben/sample/sample/controllers/account.py
    Creating /Users/ben/sample/sample/tests/functional/test_account.py
    ~/sample$

.. admonition:: How it Works

    :command:`paster` is a command line script (from the PasteScript
    package) that allows the creation of context sensitive commands.
    :command:`paster` looks in the current directory for a
    ``.egg-info`` directory, then loads the ``paster_plugins.txt``
    file.

    Using setuptools entry points, :command:`paster` looks for
    functions registered with setuptools as
    :func:`paste.paster_command`. These are defined in the entry_points
    block in each packages :file:`setup.py` module.

    This same system is used when running :command:`paster create` to
    determine what templates are available when creating new projects.

"""
import os
import sys

import paste.fixture
import paste.registry
from paste.deploy import loadapp
from paste.script.command import Command, BadCommand
from paste.script.filemaker import FileOp
from tempita import paste_script_template_renderer

import pylons
import pylons.util as util

__all__ = ['ControllerCommand', 'RestControllerCommand', 'ShellCommand']


def can_import(name):
    """Attempt to __import__ the specified package/module, returning
    True when succeeding, otherwise False"""
    try:
        __import__(name)
        return True
    except ImportError:
        return False


def is_minimal_template(package, fail_fast=False):
    """Determine if the specified Pylons project (package) uses the
    Pylons Minimal Template.

    fail_fast causes ImportErrors encountered during detection to be
    raised.
    """
    minimal_template = False
    try:
        # Check if PACKAGE.lib.base exists
        __import__(package + '.lib.base')
    except ImportError, ie:
        if 'No module named lib.base' in str(ie):
            minimal_template = True
    except:
        # PACKAGE.lib.base exists but throws an error
        if fail_fast:
            raise
    return minimal_template


def defines_render(package):
    """Determine if the specified Pylons project (package) defines a
    render callable in their base module
    """
    base_module = (is_minimal_template(package) and package + '.controllers' or
                   package + '.lib.base')
    try:
        base = __import__(base_module, globals(), locals(), ['__doc__'])
    except:
        return False
    return callable(getattr(base, 'render', None))


def validate_name(name):
    """Validate that the name for the controller isn't present on the
    path already"""
    if not name:
        # This happens when the name is an existing directory
        raise BadCommand('Please give the name of a controller.')
    # 'setup' is a valid controller name, but when paster controller is ran
    # from the root directory of a project, importing setup will import the
    # project's setup.py causing a sys.exit(). Blame relative imports
    if name != 'setup' and can_import(name):
        raise BadCommand(
            "\n\nA module named '%s' is already present in your "
            "PYTHON_PATH.\nChoosing a conflicting name will likely cause "
            "import problems in\nyour controller at some point. It's "
            "suggested that you choose an\nalternate name, and if you'd "
            "like that name to be accessible as\n'%s', add a route "
            "to your projects config/routing.py file similar\nto:\n"
            "    map.connect('%s', controller='my_%s')" \
            % (name, name, name, name))
    return True


def check_controller_existence(base_package, directory, name):
    """Check if given controller already exists in project."""
    filename = os.path.join(base_package, 'controllers', directory,
                            name + '.py')
    if os.path.exists(filename):
        raise BadCommand('Controller %s already exists.' %
                         os.path.join(directory, name))


class ControllerCommand(Command):
    """Create a Controller and accompanying functional test

    The Controller command will create the standard controller template
    file and associated functional test to speed creation of
    controllers.

    Example usage::

        yourproj% paster controller comments
        Creating yourproj/yourproj/controllers/comments.py
        Creating yourproj/yourproj/tests/functional/test_comments.py

    If you'd like to have controllers underneath a directory, just
    include the path as the controller name and the necessary
    directories will be created for you::

        yourproj% paster controller admin/trackback
        Creating yourproj/controllers/admin
        Creating yourproj/yourproj/controllers/admin/trackback.py
        Creating yourproj/yourproj/tests/functional/test_admin_trackback.py

    """
    summary = __doc__.splitlines()[0]
    usage = '\n' + __doc__

    min_args = 1
    max_args = 1
    group_name = 'pylons'

    default_verbosity = 3

    parser = Command.standard_parser(simulate=True)
    parser.add_option('--no-test',
                      action='store_true',
                      dest='no_test',
                      help="Don't create the test; just the controller")

    def command(self):
        """Main command to create controller"""
        try:
            file_op = FileOp(source_dir=('pylons', 'templates'))
            try:
                name, directory = file_op.parse_path_name_args(self.args[0])
            except:
                raise BadCommand('No egg_info directory was found')

            # Check the name isn't the same as the package
            base_package = file_op.find_dir('controllers', True)[0]
            if base_package.lower() == name.lower():
                raise BadCommand(
                    'Your controller name should not be the same as '
                    'the package name %r.' % base_package)
            # Validate the name
            name = name.replace('-', '_')
            validate_name(name)

            # Determine the module's import statement
            if is_minimal_template(base_package):
                importstatement = ('from %s.controllers import BaseController'
                                   % base_package)
            else:
                importstatement = ('from %s.lib.base import BaseController' %
                                   base_package)
            if defines_render(base_package):
                importstatement += ', render'

            # Setup the controller
            fullname = os.path.join(directory, name)
            controller_name = util.class_name_from_module_name(
                name.split('/')[-1])
            if not fullname.startswith(os.sep):
                fullname = os.sep + fullname
            testname = fullname.replace(os.sep, '_')[1:]

            module_dir = directory.replace('/', os.path.sep)
            check_controller_existence(base_package, module_dir, name)

            file_op.template_vars.update(
                {'name': controller_name,
                 'fname': os.path.join(directory, name).replace('\\', '/'),
                 'tmpl_name': name,
                 'package': base_package,
                 'importstatement': importstatement})
            file_op.copy_file(template='controller.py_tmpl',
                              dest=os.path.join('controllers', directory),
                              filename=name,
                              template_renderer=paste_script_template_renderer)
            if not self.options.no_test:
                file_op.copy_file(
                    template='test_controller.py_tmpl',
                    dest=os.path.join('tests', 'functional'),
                    filename='test_' + testname,
                    template_renderer=paste_script_template_renderer)
        except BadCommand, e:
            raise BadCommand('An error occurred. %s' % e)
        except:
            msg = str(sys.exc_info()[1])
            raise BadCommand('An unknown error occurred. %s' % msg)


class RestControllerCommand(Command):
    """Create a REST Controller and accompanying functional test

    The RestController command will create a REST-based Controller file
    for use with the :meth:`~routes.mapper.Mapper.resource`
    REST-based dispatching. This template includes the methods that
    :meth:`~routes.mapper.Mapper.resource` dispatches to in
    addition to doc strings for clarification on when the methods will
    be called.

    The first argument should be the singular form of the REST
    resource. The second argument is the plural form of the word. If
    its a nested controller, put the directory information in front as
    shown in the second example below.

    Example usage::

        yourproj% paster restcontroller comment comments
        Creating yourproj/yourproj/controllers/comments.py
        Creating yourproj/yourproj/tests/functional/test_comments.py

    If you'd like to have controllers underneath a directory, just
    include the path as the controller name and the necessary
    directories will be created for you::

        yourproj% paster restcontroller admin/tracback admin/trackbacks
        Creating yourproj/controllers/admin
        Creating yourproj/yourproj/controllers/admin/trackbacks.py
        Creating yourproj/yourproj/tests/functional/test_admin_trackbacks.py

    """
    summary = __doc__.splitlines()[0]
    usage = '\n' + __doc__

    min_args = 2
    max_args = 2
    group_name = 'pylons'

    default_verbosity = 3

    parser = Command.standard_parser(simulate=True)
    parser.add_option('--no-test',
                      action='store_true',
                      dest='no_test',
                      help="Don't create the test; just the controller")

    def command(self):
        """Main command to create controller"""
        try:
            file_op = FileOp(source_dir=('pylons', 'templates'))
            try:
                singularname, singulardirectory = \
                    file_op.parse_path_name_args(self.args[0])
                pluralname, pluraldirectory = \
                    file_op.parse_path_name_args(self.args[1])

            except:
                raise BadCommand('No egg_info directory was found')

            # Check the name isn't the same as the package
            base_package = file_op.find_dir('controllers', True)[0]
            if base_package.lower() == pluralname.lower():
                raise BadCommand(
                    'Your controller name should not be the same as '
                    'the package name %r.' % base_package)
            # Validate the name
            for name in [pluralname]:
                name = name.replace('-', '_')
                validate_name(name)

            # Determine the module's import statement
            if is_minimal_template(base_package):
                importstatement = ('from %s.controllers import BaseController'
                                   % base_package)
            else:
                importstatement = ('from %s.lib.base import BaseController' %
                                   base_package)
            if defines_render(base_package):
                importstatement += ', render'

            module_dir = pluraldirectory.replace('/', os.path.sep)
            check_controller_existence(base_package, module_dir, name)

            # Setup the controller
            fullname = os.path.join(pluraldirectory, pluralname)
            controller_name = util.class_name_from_module_name(
                pluralname.split('/')[-1])
            if not fullname.startswith(os.sep):
                fullname = os.sep + fullname
            testname = fullname.replace(os.sep, '_')[1:]

            nameprefix = ''
            path = ''
            if pluraldirectory:
                nameprefix = pluraldirectory.replace(os.path.sep, '_') + '_'
                path = pluraldirectory + '/'

            controller_c = ''
            if nameprefix:
                controller_c = ", controller='%s', \n\t" % \
                    '/'.join([pluraldirectory, pluralname])
                controller_c += "path_prefix='/%s', name_prefix='%s'" % \
                    (pluraldirectory, nameprefix)
            command = "map.resource('%s', '%s'%s)\n" % \
                (singularname, pluralname, controller_c)

            file_op.template_vars.update(
                {'classname': controller_name,
                 'pluralname': pluralname,
                 'singularname': singularname,
                 'name': controller_name,
                 'nameprefix': nameprefix,
                 'package': base_package,
                 'path': path,
                 'resource_command': command.replace('\n\t', '\n%s#%s' % \
                                                         (' ' * 4, ' ' * 9)),
                 'fname': os.path.join(pluraldirectory, pluralname),
                 'importstatement': importstatement})

            resource_command = ("\nTo create the appropriate RESTful mapping, "
                                "add a map statement to your\n")
            resource_command += ("config/routing.py file near the top like "
                                 "this:\n\n")
            resource_command += command
            file_op.copy_file(template='restcontroller.py_tmpl',
                              dest=os.path.join('controllers', pluraldirectory),
                              filename=pluralname,
                              template_renderer=paste_script_template_renderer)
            if not self.options.no_test:
                file_op.copy_file(
                    template='test_restcontroller.py_tmpl',
                    dest=os.path.join('tests', 'functional'),
                    filename='test_' + testname,
                    template_renderer=paste_script_template_renderer)
            print resource_command
        except BadCommand, e:
            raise BadCommand('An error occurred. %s' % e)
        except:
            msg = str(sys.exc_info()[1])
            raise BadCommand('An unknown error occurred. %s' % msg)


class RoutesCommand(Command):
    """Print the applications routes

    The optional CONFIG_FILE argument specifies the config file to use.
    CONFIG_FILE defaults to 'development.ini'.

    Example::

        $ paster routes my-development.ini

    """
    summary = __doc__.splitlines()[0]
    usage = '\n' + __doc__

    min_args = 0
    max_args = 1
    group_name = 'pylons'

    parser = Command.standard_parser(simulate=True)
    parser.add_option('-q',
                      action='count',
                      dest='quiet',
                      default=0,
                      help=("Do not load logging configuration from the "
                            "config file"))

    def command(self):
        """Main command to create a new shell"""
        self.verbose = 3
        if len(self.args) == 0:
            # Assume the .ini file is ./development.ini
            config_file = 'development.ini'
            if not os.path.isfile(config_file):
                raise BadCommand('%sError: CONFIG_FILE not found at: .%s%s\n'
                                 'Please specify a CONFIG_FILE' % \
                                 (self.parser.get_usage(), os.path.sep,
                                  config_file))
        else:
            config_file = self.args[0]

        config_name = 'config:%s' % config_file
        here_dir = os.getcwd()

        if not self.options.quiet:
            # Configure logging from the config file
            self.logging_file_config(config_file)

        # Load the wsgi app first so that everything is initialized right
        wsgiapp = loadapp(config_name, relative_to=here_dir)
        test_app = paste.fixture.TestApp(wsgiapp)

        # Query the test app to setup the environment and get the mapper
        tresponse = test_app.get('/_test_vars')
        mapper = tresponse.config.get('routes.map')
        if mapper:
            print mapper


class ShellCommand(Command):
    """Open an interactive shell with the Pylons app loaded

    The optional CONFIG_FILE argument specifies the config file to use for
    the interactive shell. CONFIG_FILE defaults to 'development.ini'.

    This allows you to test your mapper, models, and simulate web requests
    using ``paste.fixture``.

    Example::

        $ paster shell my-development.ini

    """
    summary = __doc__.splitlines()[0]
    usage = '\n' + __doc__

    min_args = 0
    max_args = 1
    group_name = 'pylons'

    parser = Command.standard_parser(simulate=True)
    parser.add_option('-d', '--disable-ipython',
                      action='store_true',
                      dest='disable_ipython',
                      help="Don't use IPython if it is available")

    parser.add_option('-q',
                      action='count',
                      dest='quiet',
                      default=0,
                      help=("Do not load logging configuration from the "
                            "config file"))

    def command(self):
        """Main command to create a new shell"""
        self.verbose = 3
        if len(self.args) == 0:
            # Assume the .ini file is ./development.ini
            config_file = 'development.ini'
            if not os.path.isfile(config_file):
                raise BadCommand('%sError: CONFIG_FILE not found at: .%s%s\n'
                                 'Please specify a CONFIG_FILE' % \
                                 (self.parser.get_usage(), os.path.sep,
                                  config_file))
        else:
            config_file = self.args[0]

        config_name = 'config:%s' % config_file
        here_dir = os.getcwd()
        locs = dict(__name__="pylons-admin")

        if not self.options.quiet:
            # Configure logging from the config file
            self.logging_file_config(config_file)

        # Load locals and populate with objects for use in shell
        sys.path.insert(0, here_dir)

        # Load the wsgi app first so that everything is initialized right
        wsgiapp = loadapp(config_name, relative_to=here_dir)
        test_app = paste.fixture.TestApp(wsgiapp)

        # Query the test app to setup the environment
        tresponse = test_app.get('/_test_vars')
        request_id = int(tresponse.body)

        # Disable restoration during test_app requests
        test_app.pre_request_hook = lambda self: \
            paste.registry.restorer.restoration_end()
        test_app.post_request_hook = lambda self: \
            paste.registry.restorer.restoration_begin(request_id)

        # Restore the state of the Pylons special objects
        # (StackedObjectProxies)
        paste.registry.restorer.restoration_begin(request_id)

        # Determine the package name from the pylons.config object
        pkg_name = pylons.config['pylons.package']

        # Start the rest of our imports now that the app is loaded
        if is_minimal_template(pkg_name, True):
            model_module = None
            helpers_module = pkg_name + '.helpers'
            base_module = pkg_name + '.controllers'
        else:
            model_module = pkg_name + '.model'
            helpers_module = pkg_name + '.lib.helpers'
            base_module = pkg_name + '.lib.base'

        if model_module and can_import(model_module):
            locs['model'] = sys.modules[model_module]

        if can_import(helpers_module):
            locs['h'] = sys.modules[helpers_module]

        exec ('from pylons import app_globals, config, request, response, '
              'session, tmpl_context, url') in locs
        exec ('from pylons.controllers.util import abort, redirect') in locs
        exec 'from pylons.i18n import _, ungettext, N_' in locs
        locs.pop('__builtins__', None)

        # Import all objects from the base module
        __import__(base_module)

        base = sys.modules[base_module]
        base_public = [__name for __name in dir(base) if not \
                       __name.startswith('_') or __name == '_']
        locs.update((name, getattr(base, name)) for name in base_public)
        locs.update(dict(wsgiapp=wsgiapp, app=test_app))

        mapper = tresponse.config.get('routes.map')
        if mapper:
            locs['mapper'] = mapper

        banner = "  All objects from %s are available\n" % base_module
        banner += "  Additional Objects:\n"
        if mapper:
            banner += "  %-10s -  %s\n" % ('mapper', 'Routes mapper object')
        banner += "  %-10s -  %s\n" % ('wsgiapp',
            "This project's WSGI App instance")
        banner += "  %-10s -  %s\n" % ('app',
            'paste.fixture wrapped around wsgiapp')

        try:
            if self.options.disable_ipython:
                raise ImportError()

            # try to use IPython if possible
            try:
                # ipython >= 0.11
                from IPython.frontend.terminal.embed import InteractiveShellEmbed
                shell = InteractiveShellEmbed(banner2=banner)
            except ImportError:
                # ipython < 0.11
                from IPython.Shell import IPShellEmbed
                shell = IPShellEmbed(argv=self.args)
                shell.set_banner(shell.IP.BANNER + '\n\n' + banner)

            try:
                shell(local_ns=locs, global_ns={})
            finally:
                paste.registry.restorer.restoration_end()
        except ImportError:
            import code
            py_prefix = sys.platform.startswith('java') and 'J' or 'P'
            newbanner = "Pylons Interactive Shell\n%sython %s\n\n" % \
                (py_prefix, sys.version)
            banner = newbanner + banner
            shell = code.InteractiveConsole(locals=locs)
            try:
                import readline
            except ImportError:
                pass
            try:
                shell.interact(banner)
            finally:
                paste.registry.restorer.restoration_end()

########NEW FILE########
__FILENAME__ = configuration
"""Configuration object and defaults setup

The PylonsConfig object is initialized in pylons projects inside the
:file:`config/environment.py` module. Importing the :data:`config`
object from module causes the PylonsConfig object to be created, and
setup in  app-safe manner so that multiple apps being setup avoid
conflicts.

After importing :data:`config`, the project should then call
:meth:`~PylonsConfig.init_app` with the appropriate options to setup
the configuration. In the config data passed with
:meth:`~PylonsConfig.init_app`, various defaults are set use with Paste
and Routes.

"""
import copy
import logging
import os

from paste.config import DispatchingConfig
from paste.deploy.converters import asbool
from webhelpers.mimehelper import MIMETypes


request_defaults = dict(charset='utf-8', errors='replace',
                        decode_param_names=False, language='en-us')
response_defaults = dict(content_type='text/html',
                         charset='utf-8', errors='strict',
                         headers={'Cache-Control': 'no-cache',
                                  'Pragma': 'no-cache'})

log = logging.getLogger(__name__)


config = DispatchingConfig()


class PylonsConfig(dict):
    """Pylons configuration object

    The Pylons configuration object is a per-application instance
    object that retains the information regarding the global and app
    conf's as well as per-application instance specific data such as
    the mapper, and the paths for this instance.

    The config object is available in your application as the Pylons
    global :data:`pylons.config`. For example::

        from pylons import config

        template_paths = config['pylons.paths']['templates']

    There's several useful keys of the config object most people will
    be interested in:

    ``pylons.paths``
        A dict of absolute paths that were defined in the applications
        ``config/environment.py`` module.
    ``pylons.environ_config``
        Dict of environ keys for where in the environ to pickup various
        objects for registering with Pylons. If these are present then
        PylonsApp will use them from environ rather than using default
        middleware from Beaker. Valid keys are: ``session, cache``
    ``pylons.strict_tmpl_context``
        Whether or not the ``tmpl_context`` object should throw an
        attribute error when access is attempted to an attribute that
        doesn't exist. Defaults to True.
    ``pylons.tmpl_context_attach_args``
        Whethor or not Routes variables should automatically be
        attached to the tmpl_context object when specified in a
        controllers method.
    ``pylons.request_options``
        A dict of Content-Type related default settings for new
        instances of :class:`~pylons.controllers.util.Request`. May
        contain the values ``charset`` and ``errors`` and
        ``decode_param_names``. Overrides the Pylons default values
        specified by the ``request_defaults`` dict.
    ``pylons.response_options``
        A dict of Content-Type related default settings for new
        instances of :class:`~pylons.controllers.util.Response`. May
        contain the values ``content_type``, ``charset`` and
        ``errors``. Overrides the Pylons default values specified by
        the ``response_defaults`` dict.
    ``routes.map``
        Mapper object used for Routing. Yes, it is possible to add
        routes after your application has started running.

    """
    defaults = {
        'debug': False,
        'pylons.package': None,
        'pylons.paths': {'root': None,
                         'controllers': None,
                         'templates': [],
                         'static_files': None},
        'pylons.environ_config': dict(session='beaker.session',
                                      cache='beaker.cache'),
        'pylons.app_globals': None,
        'pylons.h': None,
        'pylons.request_options': request_defaults.copy(),
        'pylons.response_options': response_defaults.copy(),
        'pylons.strict_tmpl_context': True,
        'pylons.tmpl_context_attach_args': False,
    }

    def init_app(self, global_conf, app_conf, package=None, paths=None):
        """Initialize configuration for the application

        .. note
            This *must* be called at least once, as soon as possible
            to setup all the configuration options.

        ``global_conf``
            Several options are expected to be set for a Pylons web
            application. They will be loaded from the global_config
            which has the main Paste options. If ``debug`` is not
            enabled as a global config option, the following option
            *must* be set:

            * error_to - The email address to send the debug error to

            The optional config options in this case are:

            * smtp_server - The SMTP server to use, defaults to
              'localhost'
            * error_log - A logfile to write the error to
            * error_subject_prefix - The prefix of the error email
              subject
            * from_address - Whom the error email should be from
        ``app_conf``
            Defaults supplied via the [app:main] section from the Paste
            config file. ``load_config`` only cares about whether a
            'prefix' option is set, if so it will update Routes to
            ensure URL's take that into account.
        ``package``
            The name of the application package, to be stored in the
            app_conf.

        .. versionchanged:: 1.0
            ``template_engine`` option is no longer supported.

        """
        log.debug("Initializing configuration, package: '%s'", package)

        conf = global_conf.copy()
        conf.update(app_conf)
        conf.update(dict(app_conf=app_conf, global_conf=global_conf))
        conf.update(self.pop('environment_load', {}))

        if paths:
            conf['pylons.paths'] = paths

        conf['pylons.package'] = package

        conf['debug'] = asbool(conf.get('debug'))

        # Load the MIMETypes with its default types
        MIMETypes.init()

        # Ensure all the keys from defaults are present, load them if not
        for key, val in copy.deepcopy(PylonsConfig.defaults).iteritems():
            conf.setdefault(key, val)

        # Load the errorware configuration from the Paste configuration file
        # These all have defaults, and emails are only sent if configured and
        # if this application is running in production mode
        errorware = {}
        errorware['debug'] = conf['debug']
        if not errorware['debug']:
            errorware['debug'] = False
            errorware['error_email'] = conf.get('email_to')
            errorware['error_log'] = conf.get('error_log', None)
            errorware['smtp_server'] = conf.get('smtp_server',
                'localhost')
            errorware['error_subject_prefix'] = conf.get(
                'error_subject_prefix', 'WebApp Error: ')
            errorware['from_address'] = conf.get(
                'from_address', conf.get('error_email_from',
                                         'pylons@yourapp.com'))
            errorware['error_message'] = conf.get('error_message',
                'An internal server error occurred')

        # Copy in some defaults
        if 'cache_dir' in conf:
            conf.setdefault('beaker.session.data_dir',
                            os.path.join(conf['cache_dir'], 'sessions'))
            conf.setdefault('beaker.cache.data_dir',
                            os.path.join(conf['cache_dir'], 'cache'))

        conf['pylons.cache_dir'] = conf.pop('cache_dir',
                                            conf['app_conf'].get('cache_dir'))
        # Save our errorware values
        conf['pylons.errorware'] = errorware

        # Load conf dict into self
        self.update(conf)


pylons_config = PylonsConfig()


# Push an empty config so all accesses to config at import time have something
# to look at and modify. This config will be merged with the app's when it's
# built in the paste.app_factory entry point.
pylons_config.update(copy.deepcopy(PylonsConfig.defaults))
config.push_process_config(pylons_config)

########NEW FILE########
__FILENAME__ = core
"""The core WSGIController"""
import inspect
import logging
import types

from webob.exc import HTTPException, HTTPNotFound

import pylons

__all__ = ['WSGIController']

log = logging.getLogger(__name__)


class WSGIController(object):
    """WSGI Controller that follows WSGI spec for calling and return
    values

    The Pylons WSGI Controller handles incoming web requests that are
    dispatched from the PylonsBaseWSGIApp. These requests result in a
    new instance of the WSGIController being created, which is then
    called with the dict options from the Routes match. The standard
    WSGI response is then returned with start_response called as per
    the WSGI spec.

    Special WSGIController methods you may define:

    ``__before__``
        This method is called before your action is, and should be used
        for setting up variables/objects, restricting access to other
        actions, or other tasks which should be executed before the
        action is called.

    ``__after__``
        This method is called after the action is, unless an unexpected
        exception was raised. Subclasses of
        :class:`~webob.exc.HTTPException` (such as those raised by
        ``redirect_to`` and ``abort``) are expected; e.g. ``__after__``
        will be called on redirects.

    Each action to be called is inspected with :meth:`_inspect_call` so
    that it is only passed the arguments in the Routes match dict that
    it asks for. The arguments passed into the action can be customized
    by overriding the :meth:`_get_method_args` function which is
    expected to return a dict.

    In the event that an action is not found to handle the request, the
    Controller will raise an "Action Not Found" error if in debug mode,
    otherwise a ``404 Not Found`` error will be returned.

    """
    _pylons_log_debug = False

    def _perform_call(self, func, args):
        """Hide the traceback for everything above this method"""
        __traceback_hide__ = 'before_and_this'
        return func(**args)

    def _inspect_call(self, func):
        """Calls a function with arguments from
        :meth:`_get_method_args`

        Given a function, inspect_call will inspect the function args
        and call it with no further keyword args than it asked for.

        If the function has been decorated, it is assumed that the
        decorator preserved the function signature.

        """
        # Check to see if the class has a cache of argspecs yet
        try:
            cached_argspecs = self.__class__._cached_argspecs
        except AttributeError:
            self.__class__._cached_argspecs = cached_argspecs = {}

        # function could be callable
        func_key = getattr(func, 'im_func', func.__call__)
        try:
            argspec = cached_argspecs[func_key]
        except KeyError:
            argspec = cached_argspecs[func_key] = inspect.getargspec(func_key)
        kargs = self._get_method_args()

        log_debug = self._pylons_log_debug
        c = self._py_object.tmpl_context
        environ = self._py_object.request.environ
        args = None

        if argspec[2]:
            if self._py_object.config['pylons.tmpl_context_attach_args']:
                for k, val in kargs.iteritems():
                    setattr(c, k, val)
            args = kargs
        else:
            args = {}
            argnames = argspec[0][isinstance(func, types.MethodType)
                                  and 1 or 0:]
            for name in argnames:
                if name in kargs:
                    if self._py_object.config['pylons.tmpl_context_attach_args']:
                        setattr(c, name, kargs[name])
                    args[name] = kargs[name]
        if log_debug:
            log.debug("Calling %r method with keyword args: **%r",
                      func.__name__, args)
        try:
            result = self._perform_call(func, args)
        except HTTPException, httpe:
            if log_debug:
                log.debug("%r method raised HTTPException: %s (code: %s)",
                          func.__name__, httpe.__class__.__name__,
                          httpe.wsgi_response.code, exc_info=True)
            result = httpe

            # Store the exception in the environ
            environ['pylons.controller.exception'] = httpe

            # 304 Not Modified's shouldn't have a content-type set
            if result.wsgi_response.status_int == 304:
                result.wsgi_response.headers.pop('Content-Type', None)
            result._exception = True

        return result

    def _get_method_args(self):
        """Retrieve the method arguments to use with inspect call

        By default, this uses Routes to retrieve the arguments,
        override this method to customize the arguments your controller
        actions are called with.

        This method should return a dict.

        """
        req = self._py_object.request
        kargs = req.environ['pylons.routes_dict'].copy()
        kargs['environ'] = req.environ
        kargs['start_response'] = self.start_response
        kargs['pylons'] = self._py_object
        return kargs

    def _dispatch_call(self):
        """Handles dispatching the request to the function using
        Routes"""
        log_debug = self._pylons_log_debug
        req = self._py_object.request
        try:
            action = req.environ['pylons.routes_dict']['action']
        except KeyError:
            raise Exception("No action matched from Routes, unable to"
                            "determine action dispatch.")
        action_method = action.replace('-', '_')
        if log_debug:
            log.debug("Looking for %r method to handle the request",
                      action_method)
        try:
            func = getattr(self, action_method, None)
        except UnicodeEncodeError:
            func = None
        if action_method != 'start_response' and callable(func):
            # Store function used to handle request
            req.environ['pylons.action_method'] = func

            response = self._inspect_call(func)
        else:
            if log_debug:
                log.debug("Couldn't find %r method to handle response", action)
            if pylons.config['debug']:
                raise NotImplementedError('Action %r is not implemented' %
                                          action)
            else:
                response = HTTPNotFound()
        return response

    def __call__(self, environ, start_response):
        """The main call handler that is called to return a response"""
        log_debug = self._pylons_log_debug

        # Keep a local reference to the req/response objects
        self._py_object = environ['pylons.pylons']

        # Keep private methods private
        try:
            if environ['pylons.routes_dict']['action'][:1] in ('_', '-'):
                if log_debug:
                    log.debug("Action starts with _, private action not "
                              "allowed. Returning a 404 response")
                return HTTPNotFound()(environ, start_response)
        except KeyError:
            # The check later will notice that there's no action
            pass

        start_response_called = []

        def repl_start_response(status, headers, exc_info=None):
            response = self._py_object.response
            start_response_called.append(None)

            # Copy the headers from the global response
            if log_debug:
                log.debug("Merging pylons.response headers into "
                          "start_response call, status: %s", status)
            headers.extend(header for header in response.headerlist
                           if header[0] == 'Set-Cookie' or
                           header[0].startswith('X-'))
            return start_response(status, headers, exc_info)
        self.start_response = repl_start_response

        if hasattr(self, '__before__'):
            response = self._inspect_call(self.__before__)
            if hasattr(response, '_exception'):
                return response(environ, self.start_response)

        response = self._dispatch_call()
        if not start_response_called:
            self.start_response = start_response
            py_response = self._py_object.response
            # If its not a WSGI response, and we have content, it needs to
            # be wrapped in the response object
            if isinstance(response, str):
                if log_debug:
                    log.debug("Controller returned a string "
                              ", writing it to pylons.response")
                py_response.body = py_response.body + response
            elif isinstance(response, unicode):
                if log_debug:
                    log.debug("Controller returned a unicode string "
                              ", writing it to pylons.response")
                py_response.unicode_body = py_response.unicode_body + \
                        response
            elif hasattr(response, 'wsgi_response'):
                # It's an exception that got tossed.
                if log_debug:
                    log.debug("Controller returned a Response object, merging "
                              "it with pylons.response")
                for name, value in py_response.headers.items():
                    if name.lower() == 'set-cookie':
                        response.headers.add(name, value)
                    else:
                        response.headers.setdefault(name, value)
                try:
                    registry = environ['paste.registry']
                    registry.replace(pylons.response, response)
                except KeyError:
                    # Ignore the case when someone removes the registry
                    pass
                py_response = response
            elif response is None:
                if log_debug:
                    log.debug("Controller returned None")
            else:
                if log_debug:
                    log.debug("Assuming controller returned an iterable, "
                              "setting it as pylons.response.app_iter")
                py_response.app_iter = response
            response = py_response

        if hasattr(self, '__after__'):
            after = self._inspect_call(self.__after__)
            if hasattr(after, '_exception'):
                after.wsgi_response = True
                response = after

        if hasattr(response, 'wsgi_response'):
            # Copy the response object into the testing vars if we're testing
            if 'paste.testing_variables' in environ:
                environ['paste.testing_variables']['response'] = response
            if log_debug:
                log.debug("Calling Response object to return WSGI data")

            return response(environ, self.start_response)

        if log_debug:
            log.debug("Response assumed to be WSGI content, returning "
                      "un-touched")
        return response

########NEW FILE########
__FILENAME__ = jsonrpc
"""The base WSGI JSONRPCController"""
import inspect
import json
import logging
import types
import urllib

from paste.response import replace_header
from pylons.controllers import WSGIController
from pylons.controllers.util import abort, Response

__all__ = ['JSONRPCController', 'JSONRPCError',
           'JSONRPC_PARSE_ERROR',
           'JSONRPC_INVALID_REQUEST',
           'JSONRPC_METHOD_NOT_FOUND',
           'JSONRPC_INVALID_PARAMS',
           'JSONRPC_INTERNAL_ERROR']

log = logging.getLogger(__name__)

JSONRPC_VERSION = '2.0'


class JSONRPCError(BaseException):

    def __init__(self, code, message):
        self.code = code
        self.message = message
        self.data = None

    def __str__(self):
        return str(self.code) + ': ' + self.message

    def as_dict(self):
        """Return a dictionary representation of this object for
        serialization in a JSON-RPC response."""
        error = dict(code=self.code,
                     message=self.message)
        if self.data:
            error['data'] = self.data

        return error


JSONRPC_PARSE_ERROR = JSONRPCError(-32700, "Parse error")
JSONRPC_INVALID_REQUEST = JSONRPCError(-32600, "Invalid Request")
JSONRPC_METHOD_NOT_FOUND = JSONRPCError(-32601, "Method not found")
JSONRPC_INVALID_PARAMS = JSONRPCError(-32602, "Invalid params")
JSONRPC_INTERNAL_ERROR = JSONRPCError(-32603, "Internal error")
_reserved_errors = dict(parse_error=JSONRPC_PARSE_ERROR,
                        invalid_request=JSONRPC_INVALID_REQUEST,
                        method_not_found=JSONRPC_METHOD_NOT_FOUND,
                        invalid_params=JSONRPC_INVALID_PARAMS,
                        internal_error=JSONRPC_INTERNAL_ERROR)


def jsonrpc_error(req_id, error):
    """Generate a Response object with a JSON-RPC error body. Used to
    raise top-level pre-defined errors that happen outside the
    controller."""
    if error in _reserved_errors:
        err = _reserved_errors[error]
        return Response(body=json.dumps(dict(jsonrpc=JSONRPC_VERSION,
                                             id=req_id,
                                             error=err.as_dict())))


class JSONRPCController(WSGIController):
    """
    A WSGI-speaking JSON-RPC 2.0 controller class

    See the specification:
    `<http://groups.google.com/group/json-rpc/web/json-rpc-2-0>`.

    Many parts of this controller are modelled after XMLRPCController
    from Pylons 0.9.7

    Valid controller return values should be json-serializable objects.

    Sub-classes should catch their exceptions and raise JSONRPCError
    if they want to pass meaningful errors to the client. Unhandled
    errors should be caught and return JSONRPC_INTERNAL_ERROR to the
    client.

    Parts of the specification not supported (yet):
     - Notifications
     - Batch
    """

    def _get_method_args(self):
        """Return `self._rpc_args` to dispatched controller method
        chosen by __call__"""
        return self._rpc_args

    def __call__(self, environ, start_response):
        """Parse the request body as JSON, look up the method on the
        controller and if it exists, dispatch to it.
        """
        length = 0
        if 'CONTENT_LENGTH' not in environ:
            log.debug("No Content-Length")
            abort(411)
        else:
            if environ['CONTENT_LENGTH'] == '':
                abort(411)
            length = int(environ['CONTENT_LENGTH'])
            log.debug('Content-Length: %s', length)
        if length == 0:
            log.debug("Content-Length is 0")
            abort(411)

        raw_body = environ['wsgi.input'].read(length)
        json_body = json.loads(urllib.unquote_plus(raw_body))

        self._req_id = json_body['id']
        self._req_method = json_body['method']
        self._req_params = json_body['params']
        log.debug('id: %s, method: %s, params: %s',
                  self._req_id,
                  self._req_method,
                  self._req_params)

        self._error = None
        try:
            self._func = self._find_method()
        except AttributeError:
            err = jsonrpc_error(self._req_id, 'method_not_found')
            return err(environ, start_response)

        # now that we have a method, make sure we have enough
        # parameters and pass off control to the controller.
        if not isinstance(self._req_params, dict):
            # JSON-RPC version 1 request.
            arglist = inspect.getargspec(self._func)[0][1:]
            if len(self._req_params) < len(arglist):
                err = jsonrpc_error(self._req_id, 'invalid_params')
                return err(environ, start_response)
            else:
                kargs = dict(zip(arglist, self._req_params))
        else:
            # JSON-RPC version 2 request.  Params may be default, and
            # are already a dict, so skip the parameter length check here.
            kargs = self._req_params

        # XX Fix this namespace clash. One cannot use names below as
        # method argument names as this stands!
        kargs['action'], kargs['environ'] = self._req_method, environ
        kargs['start_response'] = start_response
        self._rpc_args = kargs

        status = []
        headers = []
        exc_info = []

        def change_content(new_status, new_headers, new_exc_info=None):
            status.append(new_status)
            headers.extend(new_headers)
            exc_info.append(new_exc_info)

        output = WSGIController.__call__(self, environ, change_content)
        output = list(output)
        headers.append(('Content-Length', str(len(output[0]))))
        replace_header(headers, 'Content-Type', 'application/json')
        start_response(status[0], headers, exc_info[0])

        return output

    def _dispatch_call(self):
        """Implement dispatch interface specified by WSGIController"""
        try:
            raw_response = self._inspect_call(self._func)
        except JSONRPCError, e:
            self._error = e.as_dict()
        except TypeError, e:
            # Insufficient args in an arguments dict v2 call.
            if 'takes at least' in str(e):
                err = _reserved_errors['invalid_params']
                self._error = err.as_dict()
            else:
                raise
        except Exception, e:
            log.debug('Encountered unhandled exception: %s', repr(e))
            err = _reserved_errors['internal_error']
            self._error = err.as_dict()

        response = dict(jsonrpc=JSONRPC_VERSION,
                        id=self._req_id)
        if self._error is not None:
            response['error'] = self._error
        else:
            response['result'] = raw_response

        try:
            return json.dumps(response)
        except TypeError, e:
            log.debug('Error encoding response: %s', e)
            err = _reserved_errors['internal_error']
            return json.dumps(dict(
                    jsonrpc=JSONRPC_VERSION,
                    id=self._req_id,
                    error=err.as_dict()))

    def _find_method(self):
        """Return method named by `self._req_method` in controller if able"""
        log.debug('Trying to find JSON-RPC method: %s', self._req_method)
        if self._req_method.startswith('_'):
            raise AttributeError("Method not allowed")

        try:
            func = getattr(self, self._req_method, None)
        except UnicodeEncodeError:
            # XMLRPCController catches this, not sure why.
            raise AttributeError("Problem decoding unicode in requested "
                                 "method name.")

        if isinstance(func, types.MethodType):
            return func
        else:
            raise AttributeError("No such method: %s" % self._req_method)

########NEW FILE########
__FILENAME__ = util
"""Utility functions and classes available for use by Controllers

Pylons subclasses the `WebOb <http://pythonpaste.org/webob/>`_
:class:`webob.Request` and :class:`webob.Response` classes to provide
backwards compatible functions for earlier versions of Pylons as well
as add a few helper functions to assist with signed cookies.

For reference use, refer to the :class:`Request` and :class:`Response`
below.

Functions available:

:func:`abort`, :func:`forward`, :func:`etag_cache`,
:func:`mimetype` and :func:`redirect`
"""
import base64
import binascii
import hmac
import logging
import re
try:
    import cPickle as pickle
except ImportError:
    import pickle
try:
    from hashlib import sha1
except ImportError:
    import sha as sha1

from webob import BaseRequest as WebObRequest
from webob import Response as WebObResponse
from webob.exc import status_map

import pylons

__all__ = ['abort', 'etag_cache', 'redirect', 'Request', 'Response']

log = logging.getLogger(__name__)

IF_NONE_MATCH = re.compile('(?:W/)?(?:"([^"]*)",?\s*)')


class Request(WebObRequest):
    """WebOb Request subclass

    The WebOb :class:`webob.Request` has no charset, or other defaults. This subclass
    adds defaults, along with several methods for backwards
    compatibility with paste.wsgiwrappers.WSGIRequest.

    """
    def determine_browser_charset(self):
        """Legacy method to return the
        :attr:`webob.Request.accept_charset`"""
        return self.accept_charset

    def languages(self):
        # And we now have the old best_matches code that webob ditched!
        al = self.accept_language
        items = [i for i, q in sorted(al._parsed, key=lambda iq: -iq[1])]
        for index, item in enumerate(items):
            if al._match(item, self.language):
                items[index:] = [self.language]
                break
        else:
            items.append(self.language)
        return items
    languages = property(languages)

    def match_accept(self, mimetypes):
        return self.accept.first_match(mimetypes)

    def signed_cookie(self, name, secret):
        """Extract a signed cookie of ``name`` from the request

        The cookie is expected to have been created with
        ``Response.signed_cookie``, and the ``secret`` should be the
        same as the one used to sign it.

        Any failure in the signature of the data will result in None
        being returned.

        """
        cookie = self.str_cookies.get(name)
        if not cookie:
            return None
        try:
            input_sig, pickled = cookie[:40], base64.standard_b64decode(cookie[40:])
        except binascii.Error:
            # Badly formed data can make base64 die
            return None
        sig = hmac.new(secret, pickled, sha1).hexdigest()

        # Avoid timing attacks
        invalid_bits = 0
        if len(sig) != len(input_sig):
            return None

        for a, b in zip(sig, input_sig):
            invalid_bits += a != b

        if invalid_bits:
            return None
        else:
            return pickle.loads(pickled)


class Response(WebObResponse):
    """WebOb Response subclass

    The WebOb Response has no default content type, or error defaults.
    This subclass adds defaults, along with several methods for
    backwards compatibility with paste.wsgiwrappers.WSGIResponse.

    """
    content = WebObResponse.body

    def determine_charset(self):
        return self.charset

    def has_header(self, header):
        return header in self.headers

    def get_content(self):
        return self.body

    def wsgi_response(self):
        return self.status, self.headers, self.body

    def signed_cookie(self, name, data, secret=None, **kwargs):
        """Save a signed cookie with ``secret`` signature

        Saves a signed cookie of the pickled data. All other keyword
        arguments that ``WebOb.set_cookie`` accepts are usable and
        passed to the WebOb set_cookie method after creating the signed
        cookie value.

        """
        pickled = pickle.dumps(data, pickle.HIGHEST_PROTOCOL)
        sig = hmac.new(secret, pickled, sha1).hexdigest()
        self.set_cookie(name, sig + base64.standard_b64encode(pickled), **kwargs)


def etag_cache(key=None):
    """Use the HTTP Entity Tag cache for Browser side caching

    If a "If-None-Match" header is found, and equivilant to ``key``,
    then a ``304`` HTTP message will be returned with the ETag to tell
    the browser that it should use its current cache of the page.

    Otherwise, the ETag header will be added to the response headers.

    Suggested use is within a Controller Action like so:

    .. code-block:: python

        import pylons

        class YourController(BaseController):
            def index(self):
                etag_cache(key=1)
                return render('/splash.mako')

    .. note::
        This works because etag_cache will raise an HTTPNotModified
        exception if the ETag received matches the key provided.

    """
    if_none_matches = IF_NONE_MATCH.findall(
        pylons.request.environ.get('HTTP_IF_NONE_MATCH', ''))
    response = pylons.response._current_obj()
    response.headers['ETag'] = '"%s"' % key
    if str(key) in if_none_matches:
        log.debug("ETag match, returning 304 HTTP Not Modified Response")
        response.headers.pop('Content-Type', None)
        response.headers.pop('Cache-Control', None)
        response.headers.pop('Pragma', None)
        raise status_map[304]().exception
    else:
        log.debug("ETag didn't match, returning response object")


def forward(wsgi_app):
    """Forward the request to a WSGI application. Returns its response.

    .. code-block:: python

        return forward(FileApp('filename'))

    """
    environ = pylons.request.environ
    controller = environ.get('pylons.controller')
    if not controller or not hasattr(controller, 'start_response'):
        raise RuntimeError("Unable to forward: environ['pylons.controller'] "
                           "is not a valid Pylons controller")
    return wsgi_app(environ, controller.start_response)


def abort(status_code=None, detail="", headers=None, comment=None):
    """Aborts the request immediately by returning an HTTP exception

    In the event that the status_code is a 300 series error, the detail
    attribute will be used as the Location header should one not be
    specified in the headers attribute.

    """
    exc = status_map[status_code](detail=detail, headers=headers,
                                  comment=comment)
    log.debug("Aborting request, status: %s, detail: %r, headers: %r, "
              "comment: %r", status_code, detail, headers, comment)
    raise exc.exception


def redirect(url, code=302):
    """Raises a redirect exception to the specified URL

    Optionally, a code variable may be passed with the status code of
    the redirect, ie::

        redirect(url(controller='home', action='index'), code=303)

    """
    log.debug("Generating %s redirect" % code)
    exc = status_map[code]
    raise exc(location=url).exception

########NEW FILE########
__FILENAME__ = xmlrpc
"""The base WSGI XMLRPCController"""
import inspect
import logging
import types
import xmlrpclib

from paste.response import replace_header

from pylons.controllers import WSGIController
from pylons.controllers.util import abort, Response

__all__ = ['XMLRPCController']

log = logging.getLogger(__name__)

XMLRPC_MAPPING = ((basestring, 'string'), (list, 'array'), (bool, 'boolean'),
                  (int, 'int'), (float, 'double'), (dict, 'struct'),
                  (xmlrpclib.DateTime, 'dateTime.iso8601'),
                  (xmlrpclib.Binary, 'base64'))


def xmlrpc_sig(args):
    """Returns a list of the function signature in string format based on a
    tuple provided by xmlrpclib."""
    signature = []
    for param in args:
        for type, xml_name in XMLRPC_MAPPING:
            if isinstance(param, type):
                signature.append(xml_name)
                break
    return signature


def xmlrpc_fault(code, message):
    """Convienence method to return a Pylons response XMLRPC Fault"""
    fault = xmlrpclib.Fault(code, message)
    return Response(body=xmlrpclib.dumps(fault, methodresponse=True))


class XMLRPCController(WSGIController):
    """XML-RPC Controller that speaks WSGI

    This controller handles XML-RPC responses and complies with the
    `XML-RPC Specification <http://www.xmlrpc.com/spec>`_ as well as
    the `XML-RPC Introspection
    <http://scripts.incutio.com/xmlrpc/introspection.html>`_
    specification.

    By default, methods with names containing a dot are translated to
    use an underscore. For example, the `system.methodHelp` is handled
    by the method :meth:`system_methodHelp`.

    Methods in the XML-RPC controller will be called with the method
    given in the XMLRPC body. Methods may be annotated with a signature
    attribute to declare the valid arguments and return types.

    For example::

        class MyXML(XMLRPCController):
            def userstatus(self):
                return 'basic string'
            userstatus.signature = [ ['string'] ]

            def userinfo(self, username, age=None):
                user = LookUpUser(username)
                response = {'username':user.name}
                if age and age > 10:
                    response['age'] = age
                return response
            userinfo.signature = [['struct', 'string'],
                                  ['struct', 'string', 'int']]

    Since XML-RPC methods can take different sets of data, each set of
    valid arguments is its own list. The first value in the list is the
    type of the return argument. The rest of the arguments are the
    types of the data that must be passed in.

    In the last method in the example above, since the method can
    optionally take an integer value both sets of valid parameter lists
    should be provided.

    Valid types that can be checked in the signature and their
    corresponding Python types::

        'string' - str
        'array' - list
        'boolean' - bool
        'int' - int
        'double' - float
        'struct' - dict
        'dateTime.iso8601' - xmlrpclib.DateTime
        'base64' - xmlrpclib.Binary

    The class variable ``allow_none`` is passed to xmlrpclib.dumps;
    enabling it allows translating ``None`` to XML (an extension to the
    XML-RPC specification)

    .. note::

        Requiring a signature is optional.

    """
    allow_none = False
    max_body_length = 4194304

    def _get_method_args(self):
        return self.rpc_kargs

    def __call__(self, environ, start_response):
        """Parse an XMLRPC body for the method, and call it with the
        appropriate arguments"""
        # Pull out the length, return an error if there is no valid
        # length or if the length is larger than the max_body_length.
        log_debug = self._pylons_log_debug
        length = environ.get('CONTENT_LENGTH')
        if length:
            length = int(length)
        else:
            # No valid Content-Length header found
            if log_debug:
                log.debug("No Content-Length found, returning 411 error")
            abort(411)
        if length > self.max_body_length or length == 0:
            if log_debug:
                log.debug("Content-Length larger than max body length. Max: "
                          "%s, Sent: %s. Returning 413 error",
                          self.max_body_length, length)
            abort(413, "XML body too large")

        body = environ['wsgi.input'].read(int(environ['CONTENT_LENGTH']))
        rpc_args, orig_method = xmlrpclib.loads(body)

        method = self._find_method_name(orig_method)
        func = self._find_method(method)
        if not func:
            if log_debug:
                log.debug("Method: %r not found, returning xmlrpc fault",
                          method)
            return xmlrpc_fault(0, "No such method name %r" %
                                method)(environ, start_response)

        # Signature checking for params
        if hasattr(func, 'signature'):
            if log_debug:
                log.debug("Checking XMLRPC argument signature")
            valid_args = False
            params = xmlrpc_sig(rpc_args)
            for sig in func.signature:
                # Next sig if we don't have the same amount of args
                if len(sig) - 1 != len(rpc_args):
                    continue

                # If the params match, we're valid
                if params == sig[1:]:
                    valid_args = True
                    break

            if not valid_args:
                if log_debug:
                    log.debug("Bad argument signature recieved, returning "
                              "xmlrpc fault")
                msg = ("Incorrect argument signature. %r recieved does not "
                       "match %r signature for method %r" % \
                           (params, func.signature, orig_method))
                return xmlrpc_fault(0, msg)(environ, start_response)

        # Change the arg list into a keyword dict based off the arg
        # names in the functions definition
        arglist = inspect.getargspec(func)[0][1:]
        kargs = dict(zip(arglist, rpc_args))
        kargs['action'], kargs['environ'] = method, environ
        kargs['start_response'] = start_response
        self.rpc_kargs = kargs
        self._func = func

        # Now that we know the method is valid, and the args are valid,
        # we can dispatch control to the default WSGIController
        status = []
        headers = []
        exc_info = []

        def change_content(new_status, new_headers, new_exc_info=None):
            status.append(new_status)
            headers.extend(new_headers)
            exc_info.append(new_exc_info)
        output = WSGIController.__call__(self, environ, change_content)
        output = list(output)
        headers.append(('Content-Length', str(len(output[0]))))
        replace_header(headers, 'Content-Type', 'text/xml')
        start_response(status[0], headers, exc_info[0])
        return output

    def _dispatch_call(self):
        """Dispatch the call to the function chosen by __call__"""
        raw_response = self._inspect_call(self._func)
        if not isinstance(raw_response, xmlrpclib.Fault):
            raw_response = (raw_response,)

        response = xmlrpclib.dumps(raw_response, methodresponse=True,
                                   allow_none=self.allow_none)
        return response

    def _find_method(self, name):
        """Locate a method in the controller by the specified name and
        return it"""
        # Keep private methods private
        if name.startswith('_'):
            if self._pylons_log_debug:
                log.debug("Action starts with _, private action not allowed")
            return

        if self._pylons_log_debug:
            log.debug("Looking for XMLRPC method: %r", name)
        try:
            func = getattr(self, name, None)
        except UnicodeEncodeError:
            return
        if isinstance(func, types.MethodType):
            return func

    def _find_method_name(self, name):
        """Locate a method in the controller by the appropriate name

        By default, this translates method names like
        'system.methodHelp' into 'system_methodHelp'.

        """
        return name.replace('.', '_')

    def _publish_method_name(self, name):
        """Translate an internal method name to a publicly viewable one

        By default, this translates internal method names like
        'blog_view' into 'blog.view'.

        """
        return name.replace('_', '.')

    def system_listMethods(self):
        """Returns a list of XML-RPC methods for this XML-RPC resource"""
        methods = []
        for method in dir(self):
            meth = getattr(self, method)

            if not method.startswith('_') and isinstance(meth,
                                                         types.MethodType):
                methods.append(self._publish_method_name(method))
        return methods
    system_listMethods.signature = [['array']]

    def system_methodSignature(self, name):
        """Returns an array of array's for the valid signatures for a
        method.

        The first value of each array is the return value of the
        method. The result is an array to indicate multiple signatures
        a method may be capable of.

        """
        method = self._find_method(self._find_method_name(name))
        if method:
            return getattr(method, 'signature', '')
        else:
            return xmlrpclib.Fault(0, 'No such method name')
    system_methodSignature.signature = [['array', 'string'],
                                        ['string', 'string']]

    def system_methodHelp(self, name):
        """Returns the documentation for a method"""
        method = self._find_method(self._find_method_name(name))
        if method:
            help = MethodHelp.getdoc(method)
            sig = getattr(method, 'signature', None)
            if sig:
                help += "\n\nMethod signature: %s" % sig
            return help
        return xmlrpclib.Fault(0, "No such method name")
    system_methodHelp.signature = [['string', 'string']]


class MethodHelp(object):
    """Wrapper for formatting doc strings from XMLRPCController
    methods"""
    def __init__(self, doc):
        self.__doc__ = doc

    def getdoc(method):
        """Return a formatted doc string, via inspect.getdoc, from the
        specified XMLRPCController method

        The method's help attribute is used if it exists, otherwise the
        method's doc string is used.
        """
        help = getattr(method, 'help', None)
        if help is None:
            help = method.__doc__
        doc = inspect.getdoc(MethodHelp(help))
        if doc is None:
            return ''
        return doc
    getdoc = staticmethod(getdoc)

########NEW FILE########
__FILENAME__ = cache
"""Caching decorator"""
import inspect
import logging
import time

from decorator import decorator
from paste.deploy.converters import asbool

from pylons.decorators.util import get_pylons

log = logging.getLogger(__name__)


def beaker_cache(key="cache_default", expire="never", type=None,
                 query_args=False,
                 cache_headers=('content-type', 'content-length'),
                 invalidate_on_startup=False,
                 cache_response=True, **b_kwargs):
    """Cache decorator utilizing Beaker. Caches action or other
    function that returns a pickle-able object as a result.

    Optional arguments:

    ``key``
        None - No variable key, uses function name as key
        "cache_default" - Uses all function arguments as the key
        string - Use kwargs[key] as key
        list - Use [kwargs[k] for k in list] as key
    ``expire``
        Time in seconds before cache expires, or the string "never".
        Defaults to "never"
    ``type``
        Type of cache to use: dbm, memory, file, memcached, or None for
        Beaker's default
    ``query_args``
        Uses the query arguments as the key, defaults to False
    ``cache_headers``
        A tuple of header names indicating response headers that
        will also be cached.
    ``invalidate_on_startup``
        If True, the cache will be invalidated each time the application
        starts or is restarted.
    ``cache_response``
        Determines whether the response at the time beaker_cache is used
        should be cached or not, defaults to True.

        .. note::
            When cache_response is set to False, the cache_headers
            argument is ignored as none of the response is cached.

    If cache_enabled is set to False in the .ini file, then cache is
    disabled globally.

    """
    if invalidate_on_startup:
        starttime = time.time()
    else:
        starttime = None
    cache_headers = set(cache_headers)

    def wrapper(func, *args, **kwargs):
        """Decorator wrapper"""
        pylons = get_pylons(args)
        log.debug("Wrapped with key: %s, expire: %s, type: %s, query_args: %s",
                  key, expire, type, query_args)
        enabled = pylons.config.get("cache_enabled", "True")
        if not asbool(enabled):
            log.debug("Caching disabled, skipping cache lookup")
            return func(*args, **kwargs)

        if key:
            key_dict = kwargs.copy()
            key_dict.update(_make_dict_from_args(func, args))
            if query_args:
                key_dict.update(pylons.request.GET.mixed())

            if key != "cache_default":
                if isinstance(key, list):
                    key_dict = dict((k, key_dict[k]) for k in key)
                else:
                    key_dict = {key: key_dict[key]}
        else:
            key_dict = None

        self = None
        if args:
            self = args[0]
        namespace, cache_key = create_cache_key(func, key_dict, self)

        if type:
            b_kwargs['type'] = type

        cache_obj = getattr(pylons.app_globals, 'cache', None)
        if not cache_obj:
            cache_obj = getattr(pylons, 'cache', None)
        if not cache_obj:
            raise Exception('No CacheMiddleware or cache object on '
                            ' app_globals was found')

        my_cache = cache_obj.get_cache(namespace, **b_kwargs)

        if expire == "never":
            cache_expire = None
        else:
            cache_expire = expire

        def create_func():
            log.debug("Creating new cache copy with key: %s, type: %s",
                      cache_key, type)
            result = func(*args, **kwargs)
            glob_response = pylons.response
            headers = glob_response.headerlist
            status = glob_response.status
            full_response = dict(headers=headers, status=status,
                                 cookies=None, content=result)
            return full_response

        response = my_cache.get_value(cache_key, createfunc=create_func,
                                      expiretime=cache_expire,
                                      starttime=starttime)
        if cache_response:
            glob_response = pylons.response
            glob_response.headerlist = [header for header in response['headers']
                                        if header[0].lower() in cache_headers]
            glob_response.status = response['status']

        return response['content']
    return decorator(wrapper)


def create_cache_key(func, key_dict=None, self=None):
    """Get a cache namespace and key used by the beaker_cache decorator.

    Example::
        from pylons import cache
        from pylons.decorators.cache import create_cache_key
        namespace, key = create_cache_key(MyController.some_method)
        cache.get_cache(namespace).remove(key)

    """
    kls = None
    if hasattr(func, 'im_func'):
        kls = func.im_class
        func = func.im_func
        cache_key = func.__name__
    else:
        cache_key = func.__name__
    if key_dict:
        cache_key += " " + " ".join("%s=%s" % (k, v)
                                    for k, v in key_dict.iteritems())

    if not kls and self:
        kls = getattr(self, '__class__', None)

    if kls:
        return '%s.%s' % (kls.__module__, kls.__name__), cache_key
    else:
        return func.__module__, cache_key


def _make_dict_from_args(func, args):
    """Inspects function for name of args"""
    args_keys = {}
    for i, arg in enumerate(inspect.getargspec(func)[0]):
        if arg != "self":
            args_keys[arg] = args[i]
    return args_keys

########NEW FILE########
__FILENAME__ = rest
"""REST decorators"""
import logging

from decorator import decorator

from pylons.controllers.util import abort
from pylons.decorators.util import get_pylons

__all__ = ['dispatch_on', 'restrict']

log = logging.getLogger(__name__)


def restrict(*methods):
    """Restricts access to the function depending on HTTP method

    Example:

    .. code-block:: python

        from pylons.decorators import rest

        class SomeController(BaseController):

            @rest.restrict('GET')
            def comment(self, id):

    """
    def check_methods(func, *args, **kwargs):
        """Wrapper for restrict"""
        if get_pylons(args).request.method not in methods:
            log.debug("Method not allowed by restrict")
            abort(405, headers=[('Allow', ','.join(methods))])
        return func(*args, **kwargs)
    return decorator(check_methods)


def dispatch_on(**method_map):
    """Dispatches to alternate controller methods based on HTTP method

    Multiple keyword arguments should be passed, with the keyword
    corresponding to the HTTP method to dispatch on (DELETE, POST, GET,
    etc.) and the value being the function to call. The value should be
    a string indicating the name of the function to dispatch to.

    Example:

    .. code-block:: python

        from pylons.decorators import rest

        class SomeController(BaseController):

            @rest.dispatch_on(POST='create_comment')
            def comment(self):
                # Do something with the comment

            def create_comment(self, id):
                # Do something if its a post to comment

    """
    def dispatcher(func, self, *args, **kwargs):
        """Wrapper for dispatch_on"""
        alt_method = method_map.get(get_pylons(args).request.method)
        if alt_method:
            alt_method = getattr(self, alt_method)
            log.debug("Dispatching to %s instead", alt_method)
            return self._inspect_call(alt_method, **kwargs)
        return func(self, *args, **kwargs)
    return decorator(dispatcher)

########NEW FILE########
__FILENAME__ = secure
"""Security related decorators"""
import logging
import urlparse

from decorator import decorator
try:
    import webhelpers.html.secure_form as secure_form
except ImportError:
    import webhelpers.pylonslib.secure_form as secure_form

from pylons.controllers.util import abort, redirect
from pylons.decorators.util import get_pylons

__all__ = ['authenticate_form', 'https']

log = logging.getLogger(__name__)

csrf_detected_message = (
    "Cross-site request forgery detected, request denied. See "
    "http://en.wikipedia.org/wiki/Cross-site_request_forgery for more "
    "information.")


def authenticated_form(params):
    submitted_token = params.get(secure_form.token_key)
    return submitted_token is not None and \
        submitted_token == secure_form.authentication_token()


@decorator
def authenticate_form(func, *args, **kwargs):
    """Decorator for authenticating a form

    This decorator uses an authorization token stored in the client's
    session for prevention of certain Cross-site request forgery (CSRF)
    attacks (See
    http://en.wikipedia.org/wiki/Cross-site_request_forgery for more
    information).

    For use with the ``webhelpers.html.secure_form`` helper functions.

    """
    request = get_pylons(args).request
    if authenticated_form(request.params):
        try:
            del request.POST[secure_form.token_key]
        except KeyError:
            del request.GET[secure_form.token_key]
        return func(*args, **kwargs)
    else:
        log.warn('Cross-site request forgery detected, request denied: %r '
                 'REMOTE_ADDR: %s' % (request, request.remote_addr))
        abort(403, detail=csrf_detected_message)


def https(url_or_callable=None):
    """Decorator to redirect to the SSL version of a page if not
    currently using HTTPS. Apply this decorator to controller methods
    (actions).

    Takes a url argument: either a string url, or a callable returning a
    string url. The callable will be called with no arguments when the
    decorated method is called. The url's scheme will be rewritten to
    https if necessary.

    Non-HTTPS POST requests are aborted (405 response code) by this
    decorator.

    Example:

    .. code-block:: python

        # redirect to HTTPS /pylons
        @https('/pylons')
        def index(self):
            do_secure()

        # redirect to HTTPS /auth/login, delaying the url() call until
        # later (as the url object may not be functional when the
        # decorator/method are defined)
        @https(lambda: url(controller='auth', action='login'))
        def login(self):
            do_secure()

        # redirect to HTTPS version of myself
        @https()
        def get(self):
            do_secure()

    """
    def wrapper(func, *args, **kwargs):
        """Decorator Wrapper function"""
        request = get_pylons(args).request
        if request.scheme.lower() == 'https':
            return func(*args, **kwargs)
        if request.method.upper() == 'POST':
            # don't allow POSTs (raises an exception)
            abort(405, headers=[('Allow', 'GET')])

        if url_or_callable is None:
            url = request.url
        elif callable(url_or_callable):
            url = url_or_callable()
        else:
            url = url_or_callable
        # Ensure an https scheme, which also needs a host
        parts = urlparse.urlparse(url)
        url = urlparse.urlunparse(('https', parts[1] or request.host) +
                                  parts[2:])

        log.debug('Redirecting non-https request: %s to: %s',
                  request.path_info, url)
        redirect(url)
    return decorator(wrapper)

########NEW FILE########
__FILENAME__ = util
"""Decorator internal utilities"""
import pylons
from pylons.controllers import WSGIController


def get_pylons(decorator_args):
    """Return the `pylons` object: either the :mod`~pylons` module or
    the :attr:`~WSGIController._py_object` equivalent, searching a
    decorator's *args for the latter

    :attr:`~WSGIController._py_object` is more efficient as it provides
    direct access to the Pylons global variables.
    """
    if decorator_args:
        controller = decorator_args[0]
        if isinstance(controller, WSGIController):
            return controller._py_object
    return pylons

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# Pylons documentation build configuration file, created by
# sphinx-quickstart on Mon Apr 21 20:41:33 2008.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# The contents of this file are pickled, so don't put values in the namespace
# that aren't pickleable (module imports are okay, they're removed automatically).
#
# All configuration values have a default value; values that are commented out
# serve to show the default value.

import sys, os

# If your extensions are in another directory, add it here.
#sys.path.append('some/directory')
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


# General configuration
# ---------------------

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.intersphinx']

intersphinx_mapping = {
    'http://www.sqlalchemy.org/docs/': None,
    'http://sluggo.scrapping.cc/python/WebHelpers/': None,
    'http://routes.groovie.org/': None,
    'http://beaker.groovie.org/': None,
}

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The master toctree document.
master_doc = 'index'

# General substitutions.
project = 'Pylons Framework'
copyright = '2008-2012, Ben Bangert, James Gardner, Philip Jenvey'

# The default replacements for |version| and |release|, also used in various
# other places throughout the built documents.
#
# The short X.Y version.
version = '1.0.1'
# The full version, including alpha/beta/rc tags.
release = '1.0.1'

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
#pygments_style = 'sphinx'

# Options for HTML output
# -----------------------

# Add and use Pylons theme
from subprocess import call, Popen, PIPE

p = Popen('which git', shell=True, stdout=PIPE)
git = p.stdout.read().strip()
cwd = os.getcwd()
_themes = os.path.join(cwd, '_themes')

if not os.path.isdir(_themes):
    call([git, 'clone', 'git://github.com/Pylons/pylons_sphinx_theme.git',
            '_themes'])
else:
    os.chdir(_themes)
    call([git, 'checkout', 'master'])
    call([git, 'pull'])
    os.chdir(cwd)

sys.path.append(os.path.abspath('_themes'))
html_theme_path = ['_themes']
html_theme = 'pylonsfw'
html_theme_options = dict(
    github_url='https://github.com/Pylons/pylons'
    )

# The style sheet to use for HTML and HTML Help pages. A file of that name
# must exist either in Sphinx' static/ path, or in one of the custom paths
# given in html_static_path.
#html_style = 'default.css'

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

# Content template for the index page.
#html_index = ''

# Custom sidebar templates, maps document names to template names.
#html_sidebars = {}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If false, no module index is generated.
#html_use_modindex = True

# If true, the reST sources are included in the HTML build as _sources/<name>.
#html_copy_source = True

# Output file base name for HTML help builder.
htmlhelp_basename = 'Pylonsfwdoc'


# Options for LaTeX output
# ------------------------

# The paper size ('letter' or 'a4').
latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, document class [howto/manual]).
latex_documents = [
  ('index', 'Pylons.tex', 'Pylons Reference Documentation', 
   'Ben Bangert, Graham Higgins, James Gardner, Philip Jenvey', 'manual',
   'toctree_only'),
]

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

########NEW FILE########
__FILENAME__ = uploader
import cPickle
import mimetypes
import os
import sys
import socket
from os import path

import httplib2
import simplejson

socket.setdefaulttimeout(60)

HERE_DIR = os.getcwd()
BUILD_DIR = path.join(HERE_DIR, '_build')

#host = 'http://localhost:25050'
host = 'http://pylonshq.com'

post_uri = '%s/docs/upload' % host
image_uri = '%s/docs/upload_image' % host
delete_uri = '%s/docs/delete_revision' % host


def scan_dir(parent, directory):
    files = []
    for name in os.listdir(directory):
        full_name = path.join(directory, name)
        if name in ['_sources', '_static']:
            continue
        if path.isdir(full_name):
            new_parent = parent + '/' + name
            files.extend(scan_dir(new_parent, full_name))
        else:
            if name.endswith('.fpickle') or name.endswith('.pickle'):
                fp = open(full_name, 'r')
                data = cPickle.load(fp)
                fp.close()
                files.append(
                    ('/'.join([parent, name]), data)
                )
            elif name == 'objects.inv':
                fp = open(full_name, 'r')
                data = {}
                data['current_page_name'] = 'objects.inv'
                data['content'] = fp.read()
                fp.close()
                files.append(
                    ('/'.join([parent, name]), data)
                )
    return files

def scan_images(directory):
    files = []
    for name in os.listdir(directory):
        if name[-4:] in ['.png', '.jpg', 'gif']:
            files.append(name)
    return files

files = scan_dir('', path.join(BUILD_DIR, 'web'))
images = scan_images(path.join(BUILD_DIR, 'web', '_images'))
http = httplib2.Http(timeout=60)

basedata = {}
# Find the metadata about versions and such
for filename, filedoc in files:
    if 'globalcontext.pickle' in filename:
        basedata['version'] = filedoc['version']
        basedata['project'] = filedoc['project']
        basedata['shorttitle'] = filedoc['shorttitle']

if len(sys.argv) < 2:
    raise Exception('Failed to specify doc-key')

dockey = sys.argv[1]
headers = {}
headers.setdefault('Accept', 'application/json')
headers.setdefault('User-Agent', 'Doc Uploader')
headers.setdefault('Content-Type', 'application/json')
headers.setdefault('Authkey', dockey)

language = os.path.split(HERE_DIR)[-1]

# Delete this revision, just in case
# del_uri = '%s/%s/%s' % (delete_uri, basedata['project'], basedata['version'])
# resp, data = http.request(del_uri, 'GET', headers=headers)

for filename, filedoc in files:
    if not isinstance(filedoc, dict):
        continue
    filedoc['filename'] = filename
    filedoc['language'] = language
    filedoc.update(basedata)
    content = simplejson.dumps(filedoc, ensure_ascii=False).encode('utf-8')
    headers['Content-Length'] = str(len(content))
    resp, data = http.request(post_uri, 'POST', body=content, headers=headers)
    status_code = int(resp.status)
    if status_code == 200:
        print "Uploaded %s" % filename
    else:
        print "FAILED: %s" % filename

for filename in images:
    headers['Content-Type'] = mimetypes.guess_type(filename)
    fp = open(path.join(BUILD_DIR, 'web', '_images', filename), 'r')
    file_content = fp.read()
    fp.close()
    headers['Content-Length'] = str(len(file_content))
    resp, data = http.request(image_uri + '?version=%s&project=%s&name=%s' %
                              (basedata['version'], basedata['project'], filename),
                              'POST', body=file_content, headers=headers)
    status_code = int(resp.status)
    if status_code == 200:
        print "Uploaded %s" % filename
    else:
        print "FAILED: %s" % filename

########NEW FILE########
__FILENAME__ = error
"""Custom EvalException support

Provides template engine HTML error formatters for the Template tab of
EvalException.

"""
import sys

try:
    import mako.exceptions
except ImportError:
    mako = None

__all__ = ['handle_mako_error']


def handle_mako_error(context, exc):
    try:
        exc.is_mako_exception = True
    except:
        pass
    raise (exc, None, sys.exc_info()[2])


def myghty_html_data(exc_value):
    """Format a Myghty exception as HTML"""
    if hasattr(exc_value, 'htmlformat'):
        return exc_value.htmlformat()[333:-14]
    if hasattr(exc_value, 'mtrace'):
        return exc_value.mtrace.htmlformat()[333:-14]

template_error_formatters = [myghty_html_data]


if mako:
    def mako_html_data(exc_value):
        """Format a Mako exception as HTML"""
        if getattr(exc_value, 'is_mako_exception', False) or \
           isinstance(exc_value, (mako.exceptions.CompileException,
                                  mako.exceptions.SyntaxException)):
            return mako.exceptions.html_error_template().render(full=False,
                                                                css=False)
    template_error_formatters.insert(0, mako_html_data)

########NEW FILE########
__FILENAME__ = translation
"""Translation/Localization functions.

Provides :mod:`gettext` translation functions via an app's
``pylons.translator`` and get/set_lang for changing the language
translated to.

"""
import os
from gettext import NullTranslations, translation

import pylons

__all__ = ['_', 'add_fallback', 'get_lang', 'gettext', 'gettext_noop',
           'lazy_gettext', 'lazy_ngettext', 'lazy_ugettext', 'lazy_ungettext',
           'ngettext', 'set_lang', 'ugettext', 'ungettext', 'LanguageError',
           'N_']


class LanguageError(Exception):
    """Exception raised when a problem occurs with changing languages"""
    pass


class LazyString(object):
    """Has a number of lazily evaluated functions replicating a
    string. Just override the eval() method to produce the actual value.

    This method copied from TurboGears.

    """
    def __init__(self, func, *args, **kwargs):
        self.func = func
        self.args = args
        self.kwargs = kwargs

    def eval(self):
        return self.func(*self.args, **self.kwargs)

    def __unicode__(self):
        return unicode(self.eval())

    def __str__(self):
        return str(self.eval())

    def __mod__(self, other):
        return self.eval() % other

    def format(self, *args):
        return self.eval().format(*args)


def lazify(func):
    """Decorator to return a lazy-evaluated version of the original"""
    def newfunc(*args, **kwargs):
        return LazyString(func, *args, **kwargs)
    newfunc.__name__ = 'lazy_%s' % func.__name__
    newfunc.__doc__ = 'Lazy-evaluated version of the %s function\n\n%s' % \
        (func.__name__, func.__doc__)
    return newfunc


def gettext_noop(value):
    """Mark a string for translation without translating it. Returns
    value.

    Used for global strings, e.g.::

        foo = N_('Hello')

        class Bar:
            def __init__(self):
                self.local_foo = _(foo)

        h.set_lang('fr')
        assert Bar().local_foo == 'Bonjour'
        h.set_lang('es')
        assert Bar().local_foo == 'Hola'
        assert foo == 'Hello'

    """
    return value
N_ = gettext_noop


def gettext(value):
    """Mark a string for translation. Returns the localized string of
    value.

    Mark a string to be localized as follows::

        gettext('This should be in lots of languages')

    """
    return pylons.translator.gettext(value)
lazy_gettext = lazify(gettext)


def ugettext(value):
    """Mark a string for translation. Returns the localized unicode
    string of value.

    Mark a string to be localized as follows::

        _('This should be in lots of languages')

    """
    return pylons.translator.ugettext(value)
_ = ugettext
lazy_ugettext = lazify(ugettext)


def ngettext(singular, plural, n):
    """Mark a string for translation. Returns the localized string of
    the pluralized value.

    This does a plural-forms lookup of a message id. ``singular`` is
    used as the message id for purposes of lookup in the catalog, while
    ``n`` is used to determine which plural form to use. The returned
    message is a string.

    Mark a string to be localized as follows::

        ngettext('There is %(num)d file here', 'There are %(num)d files here',
                 n) % {'num': n}

    """
    return pylons.translator.ngettext(singular, plural, n)
lazy_ngettext = lazify(ngettext)


def ungettext(singular, plural, n):
    """Mark a string for translation. Returns the localized unicode
    string of the pluralized value.

    This does a plural-forms lookup of a message id. ``singular`` is
    used as the message id for purposes of lookup in the catalog, while
    ``n`` is used to determine which plural form to use. The returned
    message is a Unicode string.

    Mark a string to be localized as follows::

        ungettext('There is %(num)d file here', 'There are %(num)d files here',
                  n) % {'num': n}

    """
    return pylons.translator.ungettext(singular, plural, n)
lazy_ungettext = lazify(ungettext)


def _get_translator(lang, **kwargs):
    """Utility method to get a valid translator object from a language
    name"""
    if not lang:
        return NullTranslations()
    if 'pylons_config' in kwargs:
        conf = kwargs.pop('pylons_config')
    else:
        conf = pylons.config.current_conf()
    localedir = os.path.join(conf['pylons.paths']['root'], 'i18n')
    if not isinstance(lang, list):
        lang = [lang]
    try:
        translator = translation(conf['pylons.package'], localedir,
                                 languages=lang, **kwargs)
    except IOError, ioe:
        raise LanguageError('IOError: %s' % ioe)
    translator.pylons_lang = lang
    return translator


def set_lang(lang, set_environ=True, **kwargs):
    """Set the current language used for translations.

    ``lang`` should be a string or a list of strings. If a list of
    strings, the first language is set as the main and the subsequent
    languages are added as fallbacks.
    """
    translator = _get_translator(lang, **kwargs)
    if not set_environ:
        return translator
    environ = pylons.request.environ
    environ['pylons.pylons'].translator = translator
    if 'paste.registry' in environ:
        environ['paste.registry'].replace(pylons.translator, translator)


def get_lang():
    """Return the current i18n language used"""
    return getattr(pylons.translator, 'pylons_lang', None)


def add_fallback(lang, **kwargs):
    """Add a fallback language from which words not matched in other
    languages will be translated to.

    This fallback will be associated with the currently selected
    language -- that is, resetting the language via set_lang() resets
    the current fallbacks.

    This function can be called multiple times to add multiple
    fallbacks.
    """
    return pylons.translator.add_fallback(_get_translator(lang, **kwargs))

########NEW FILE########
__FILENAME__ = log
"""Logging related functionality

This logging Handler logs to ``environ['wsgi.errors']`` as designated
in :pep:`333`.

"""
import logging
import types

import pylons

__all__ = ['WSGIErrorsHandler']


class WSGIErrorsHandler(logging.Handler):

    """A handler class that writes logging records to
    `environ['wsgi.errors']`.

    This code is derived from CherryPy's
    :class:`cherrypy._cplogging.WSGIErrorHandler`.

    ``cache``
        Whether the `wsgi.errors` stream is cached (instead of looked up
        via `pylons.request.environ` per every logged message). Enabling
        this option is not recommended (particularly for the use case of
        logging to `wsgi.errors` outside of a request) as the behavior
        of a cached `wsgi.errors` stream is not strictly defined. In
        particular, `mod_wsgi <http://www.modwsgi.org>`_'s `wsgi.errors`
        will raise an exception when used outside of a request.

    """

    def __init__(self, cache=False, *args, **kwargs):
        logging.Handler.__init__(self, *args, **kwargs)
        self.cache = cache
        self.cached_stream = None

    def get_wsgierrors(self):
        """Return the wsgi.errors stream

        Raises a TypeError when outside of a web request
        (pylons.request is not setup)

        """
        if not self.cache:
            return pylons.request.environ.get('wsgi.errors')
        elif not self.cached_stream:
            self.cached_stream = pylons.request.environ.get('wsgi.errors')
            return self.cached_stream
        return self.cached_stream

    def flush(self):
        """Flushes the stream"""
        try:
            stream = self.get_wsgierrors()
        except TypeError:
            pass
        else:
            if stream:
                stream.flush()

    def emit(self, record):
        """Emit a record"""
        try:
            stream = self.get_wsgierrors()
        except TypeError:
            pass
        else:
            if not stream:
                return
            try:
                msg = self.format(record)
                fs = "%s\n"
                if not hasattr(types, "UnicodeType"):  # if no unicode support
                    stream.write(fs % msg)
                else:
                    try:
                        stream.write(fs % msg)
                    except UnicodeError:
                        stream.write(fs % msg.encode("UTF-8"))
                self.flush()
            except (KeyboardInterrupt, SystemExit):
                raise
            except:
                self.handleError(record)

########NEW FILE########
__FILENAME__ = middleware
"""Pylons' WSGI middlewares"""
import logging
import os.path

from paste.deploy.converters import asbool
from paste.urlparser import StaticURLParser
from weberror.evalexception import EvalException
from weberror.errormiddleware import ErrorMiddleware
from webhelpers.html import literal

import pylons
from pylons.controllers.util import Request, Response
from pylons.error import template_error_formatters
from pylons.util import call_wsgi_application

__all__ = ['ErrorHandler', 'error_document_template',
           'footer_html', 'head_html', 'media_path']

log = logging.getLogger(__name__)

media_path = os.path.join(os.path.dirname(__file__), 'media')

head_html = """\
<link rel="stylesheet" href="{{prefix}}/media/pylons/style/itraceback.css" \
type="text/css" media="screen" />"""

footer_html = """\
<script src="{{prefix}}/media/pylons/javascripts/traceback.js"></script>
<script>
var TRACEBACK = {
    uri: "{{prefix}}",
    host: "%s",
    traceback: "/tracebacks"
}
</script>
<div id="service_widget">
<h2 class="assistance">Online Assistance</h2>
<div id="nv">
<ul id="supportnav">
    <li class="nav active"><a class="overview" href="#">Overview</a></li>
    <li class="nav"><a class="search" href="#">Search Mail Lists</a></li>
    <li class="nav"><a class="posttraceback" href="#">Post Traceback</a></li>
</ul>
</div>
<div class="clearfix">&nbsp;</div>
<div class="overviewtab">
<b>Looking for help?</b>

<p>Here are a few tips for troubleshooting if the above traceback isn't
helping out.</p>

<ol>
<li>Search the mail list</li>
<li>Post the traceback, and ask for help on IRC</li>
<li>Post a message to the mail list, referring to the posted traceback</li>

</div>
<div class="posttracebacktab">
<p><b>Note:</b> Clicking this button will post your traceback to the PylonsHQ website.
The traceback includes the module names, Python version, and lines of code that you
can see above. All tracebacks are posted anonymously unless you're logged into the
PylonsHQ website in this browser.</p>
<input type="button" href="#" class="submit_traceback" value="Send TraceBack to PylonsHQ" style="text-align: center;"/>
</div>

<div class="searchtab">
<p>The following mail lists will be searched:<br />
<input type="checkbox" name="lists" value="pylons" checked="checked" /> Pylons<br />
<input type="checkbox" name="lists" value="python" /> Python<br />
<input type="checkbox" name="lists" value="mako" /> Mako<br />
<input type="checkbox" name="lists" value="sqlalchemy" /> SQLAlchemy</p>
<p class="query">for: <input type="text" name="query" class="query" /></p>

<p><input type="submit" value="Search" /></p>
<div class="searchresults">

</div>
</div>

</div>
<div id="pylons_logo">\
<img src="{{prefix}}/media/pylons/img/pylons-powered-02.png" /></div>
<div class="credits">Pylons version %s</div>"""

report_libs = ['pylons', 'genshi', 'sqlalchemy']


def DebugHandler(app, global_conf, **kwargs):
    footer = footer_html % (kwargs.get('traceback_host',
                                       'pylonshq.com'),
                            pylons.__version__)
    py_media = dict(pylons=media_path)
    app = EvalException(app, global_conf,
                        templating_formatters=template_error_formatters,
                        media_paths=py_media, head_html=head_html,
                        footer_html=footer,
                        libraries=report_libs)
    return app


def ErrorHandler(app, global_conf, **errorware):
    """ErrorHandler Toggle

    If debug is enabled, this function will return the app wrapped in
    the WebError ``EvalException`` middleware which displays
    interactive debugging sessions when a traceback occurs.

    Otherwise, the app will be wrapped in the WebError
    ``ErrorMiddleware``, and the ``errorware`` dict will be passed into
    it. The ``ErrorMiddleware`` handles sending an email to the address
    listed in the .ini file, under ``email_to``.

    """
    if asbool(global_conf.get('debug')):
        footer = footer_html % (pylons.config.get('traceback_host',
                                                  'pylonshq.com'),
                                pylons.__version__)
        py_media = dict(pylons=media_path)
        app = EvalException(app, global_conf,
                            templating_formatters=template_error_formatters,
                            media_paths=py_media, head_html=head_html,
                            footer_html=footer,
                            libraries=report_libs)
    else:
        app = ErrorMiddleware(app, global_conf, **errorware)
    return app


class StatusCodeRedirect(object):
    """Internally redirects a request based on status code

    StatusCodeRedirect watches the response of the app it wraps. If the
    response is an error code in the errors sequence passed the request
    will be re-run with the path URL set to the path passed in.

    This operation is non-recursive and the output of the second
    request will be used no matter what it is.

    Should an application wish to bypass the error response (ie, to
    purposely return a 401), set
    ``environ['pylons.status_code_redirect'] = True`` in the application.

    """
    def __init__(self, app, errors=(400, 401, 403, 404),
                 path='/error/document'):
        """Initialize the ErrorRedirect

        ``errors``
            A sequence (list, tuple) of error code integers that should
            be caught.
        ``path``
            The path to set for the next request down to the
            application.

        """
        self.app = app
        self.error_path = path

        # Transform errors to str for comparison
        self.errors = tuple([str(x) for x in errors])

    def __call__(self, environ, start_response):
        status, headers, app_iter, exc_info = call_wsgi_application(
            self.app, environ, catch_exc_info=True)
        if status[:3] in self.errors and \
            'pylons.status_code_redirect' not in environ and self.error_path:
            # Create a response object
            environ['pylons.original_response'] = Response(
                status=status, headerlist=headers, app_iter=app_iter)
            environ['pylons.original_request'] = Request(environ)

            # Create a new environ to avoid touching the original request data
            new_environ = environ.copy()
            new_environ['PATH_INFO'] = self.error_path

            newstatus, headers, app_iter, exc_info = call_wsgi_application(
                    self.app, new_environ, catch_exc_info=True)
        start_response(status, headers, exc_info)
        return app_iter


error_document_template = literal("""\
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">
<head>
 <title>Server Error %(code)s</title>
<!-- CSS Imports -->
<link rel="stylesheet" href="%(prefix)s/error/style/black.css" type="text/css" media="screen" />

<!-- Favorite Icons -->
<link rel="icon" href="%(prefix)s/error/img/favicon.ico" type="image/png" />

<style type="text/css">
        .red {
            color:#FF0000;
        }
        .bold {
            font-weight: bold;
        }
</style>
</head>

<body>
    <div id="container">
        %(message)s
    </div>
</body>
</html>
""")


def debugger_filter_factory(global_conf, **kwargs):
    def filter(app):
        return DebugHandler(app, global_conf, **kwargs)
    return filter


def debugger_filter_app_factory(app, global_conf, **kwargs):
    return DebugHandler(app, global_conf, **kwargs)

########NEW FILE########
__FILENAME__ = templating
"""Render functions and helpers

Render functions and helpers
============================

:mod:`pylons.templating` includes several basic render functions,
:func:`render_mako`, :func:`render_genshi` and :func:`render_jinja2`
that render templates from the file-system with the assumption that
variables intended for the will be attached to :data:`tmpl_context`
(hereafter referred to by its short name of :data:`c` which it is
commonly imported as).

The default render functions work with the template language loader
object that is setup on the :data:`app_globals` object in the project's
:file:`config/environment.py`.

Usage
-----

Generally, one of the render functions will be imported in the
controller. Variables intended for the template are attached to the
:data:`c` object. The render functions return unicode (they actually
return :class:`~webhelpers.html.literal` objects, a subclass of
unicode).

.. admonition :: Tip

    :data:`tmpl_context` (template context) is abbreviated to :data:`c`
    instead of its full name since it will likely be used extensively
    and it's much faster to use :data:`c`. Of course, for users that
    can't tolerate one-letter variables, feel free to not import
    :data:`tmpl_context` as :data:`c` since both names are available in
    templates as well.

Example of rendering a template with some variables::

    from pylons import tmpl_context as c
    from pylons.templating import render_mako as render

    from sampleproject.lib.base import BaseController

    class SampleController(BaseController):

        def index(self):
            c.first_name = "Joe"
            c.last_name = "Smith"
            return render('/some/template.mako')

And the accompanying Mako template:

.. code-block:: mako

    Hello ${c.first name}, I see your lastname is ${c.last_name}!

Your controller will have additional default imports for commonly used
functions.

Template Globals
----------------

Templates rendered in Pylons should include the default Pylons globals
as the :func:`render_mako`, :func:`render_genshi` and
:func:`render_jinja2` functions. The full list of Pylons globals that
are included in the template's namespace are:

- :term:`c` -- Template context object
- :term:`tmpl_context` -- Template context object
- :data:`config` -- Pylons :class:`~pylons.configuration.PylonsConfig`
  object (acts as a dict)
- :term:`app_globals` -- Project application globals object
- :term:`h` -- Project helpers module reference
- :data:`request` -- Pylons :class:`~pylons.controllers.util.Request`
  object for this request
- :data:`response` -- Pylons :class:`~pylons.controllers.util.Response`
  object for this request
- :class:`session` -- Pylons session object (unless Sessions are
  removed)
- :class:`url <routes.util.URLGenerator>` -- Routes url generator
  object
- :class:`translator` -- Gettext translator object configured for
  current locale
- :func:`ungettext` -- Unicode capable version of gettext's ngettext
  function (handles plural translations)
- :func:`_` -- Unicode capable gettext translate function
- :func:`N_` -- gettext no-op function to mark a string for
  translation, but doesn't actually translate

Configuring the template language
---------------------------------

The template engine is created in the projects
``config/environment.py`` and attached to the ``app_globals`` (g)
instance. Configuration options can be directly passed into the
template engine, and are used by the render functions.

.. warning::

    Don't change the variable name on :data:`app_globals` that the
    template loader is attached to if you want to use the render_*
    functions that :mod:`pylons.templating` comes with. The render_*
    functions look for the template loader to render the template.

"""
import logging

from webhelpers.html import literal

import pylons

__all__ = ['render_genshi', 'render_jinja2', 'render_mako']

PYLONS_VARS = ['c', 'app_globals', 'config', 'h', 'render', 'request',
               'session', 'translator', 'ungettext', '_', 'N_']

log = logging.getLogger(__name__)


def pylons_globals():
    """Create and return a dictionary of global Pylons variables

    Render functions should call this to retrieve a list of global
    Pylons variables that should be included in the global template
    namespace if possible.

    Pylons variables that are returned in the dictionary:
        ``c``, ``h``, ``_``, ``N_``, config, request, response,
        translator, ungettext, ``url``

    If SessionMiddleware is being used, ``session`` will also be
    available in the template namespace.

    """
    conf = pylons.config._current_obj()
    c = pylons.tmpl_context._current_obj()
    app_globals = conf.get('pylons.app_globals')
    pylons_vars = dict(
        c=c,
        tmpl_context=c,
        config=conf,
        app_globals=app_globals,
        h=conf.get('pylons.h'),
        request=pylons.request._current_obj(),
        response=pylons.response._current_obj(),
        url=pylons.url._current_obj(),
        translator=pylons.translator._current_obj(),
        ungettext=pylons.i18n.ungettext,
        _=pylons.i18n._,
        N_=pylons.i18n.N_
    )

    # If the session was overriden to be None, don't populate the session
    # var
    econf = pylons.config['pylons.environ_config']
    if 'beaker.session' in pylons.request.environ or \
        ('session' in econf and econf['session'] in pylons.request.environ):
        pylons_vars['session'] = pylons.session._current_obj()
    log.debug("Created render namespace with pylons vars: %s", pylons_vars)
    return pylons_vars


def cached_template(template_name, render_func, ns_options=(),
                    cache_key=None, cache_type=None, cache_expire=None,
                    **kwargs):
    """Cache and render a template

    Cache a template to the namespace ``template_name``, along with a
    specific key if provided.

    Basic Options

    ``template_name``
        Name of the template, which is used as the template namespace.
    ``render_func``
        Function used to generate the template should it no longer be
        valid or doesn't exist in the cache.
    ``ns_options``
        Tuple of strings, that should correspond to keys likely to be
        in the ``kwargs`` that should be used to construct the
        namespace used for the cache. For example, if the template
        language supports the 'fragment' option, the namespace should
        include it so that the cached copy for a template is not the
        same as the fragment version of it.

    Caching options (uses Beaker caching middleware)

    ``cache_key``
        Key to cache this copy of the template under.
    ``cache_type``
        Valid options are ``dbm``, ``file``, ``memory``, ``database``,
        or ``memcached``.
    ``cache_expire``
        Time in seconds to cache this template with this ``cache_key``
        for. Or use 'never' to designate that the cache should never
        expire.

    The minimum key required to trigger caching is
    ``cache_expire='never'`` which will cache the template forever
    seconds with no key.

    """
    # If one of them is not None then the user did set something
    if cache_key is not None or cache_expire is not None or cache_type \
        is not None:

        if not cache_type:
            cache_type = 'dbm'
        if not cache_key:
            cache_key = 'default'
        if cache_expire == 'never':
            cache_expire = None
        namespace = template_name
        for name in ns_options:
            namespace += str(kwargs.get(name))
        cache = pylons.cache.get_cache(namespace, type=cache_type)
        content = cache.get_value(cache_key, createfunc=render_func,
            expiretime=cache_expire)
        return content
    else:
        return render_func()


def render_mako(template_name, extra_vars=None, cache_key=None,
                cache_type=None, cache_expire=None):
    """Render a template with Mako

    Accepts the cache options ``cache_key``, ``cache_type``, and
    ``cache_expire``.

    """
    # Create a render callable for the cache function
    def render_template():
        # Pull in extra vars if needed
        globs = extra_vars or {}

        # Second, get the globals
        globs.update(pylons_globals())

        # Grab a template reference
        template = globs['app_globals'].mako_lookup.get_template(template_name)

        return literal(template.render_unicode(**globs))

    return cached_template(template_name, render_template, cache_key=cache_key,
                           cache_type=cache_type, cache_expire=cache_expire)


def render_mako_def(template_name, def_name, cache_key=None,
                    cache_type=None, cache_expire=None, **kwargs):
    """Render a def block within a Mako template

    Takes the template name, and the name of the def within it to call.
    If the def takes arguments, they should be passed in as keyword
    arguments.

    Example::

        # To call the def 'header' within the 'layout.mako' template
        # with a title argument
        render_mako_def('layout.mako', 'header', title='Testing')

    Also accepts the cache options ``cache_key``, ``cache_type``, and
    ``cache_expire``.

    """
    # Create a render callable for the cache function
    def render_template():
        # Pull in extra vars if needed
        globs = kwargs or {}

        # Second, get the globals
        globs.update(pylons_globals())

        # Grab a template reference
        template = globs['app_globals'].mako_lookup.get_template(
            template_name).get_def(def_name)

        return literal(template.render_unicode(**globs))

    return cached_template(template_name, render_template, cache_key=cache_key,
                           cache_type=cache_type, cache_expire=cache_expire)


def render_genshi(template_name, extra_vars=None, cache_key=None,
                  cache_type=None, cache_expire=None, method='xhtml'):
    """Render a template with Genshi

    Accepts the cache options ``cache_key``, ``cache_type``, and
    ``cache_expire`` in addition to method which are passed to Genshi's
    render function.

    """
    # Create a render callable for the cache function
    def render_template():
        # Pull in extra vars if needed
        globs = extra_vars or {}

        # Second, get the globals
        globs.update(pylons_globals())

        # Grab a template reference
        template = globs['app_globals'].genshi_loader.load(template_name)

        return literal(template.generate(**globs).render(method=method,
                                                         encoding=None))

    return cached_template(template_name, render_template, cache_key=cache_key,
                           cache_type=cache_type, cache_expire=cache_expire,
                           ns_options=('method'), method=method)


def render_jinja2(template_name, extra_vars=None, cache_key=None,
                 cache_type=None, cache_expire=None):
    """Render a template with Jinja2

    Accepts the cache options ``cache_key``, ``cache_type``, and
    ``cache_expire``.

    """
    # Create a render callable for the cache function
    def render_template():
        # Pull in extra vars if needed
        globs = extra_vars or {}

        # Second, get the globals
        globs.update(pylons_globals())

        # Grab a template reference
        template = \
            globs['app_globals'].jinja2_env.get_template(template_name)

        return literal(template.render(**globs))

    return cached_template(template_name, render_template, cache_key=cache_key,
                           cache_type=cache_type, cache_expire=cache_expire)

########NEW FILE########
__FILENAME__ = test
"""Test related functionality

Adds a Pylons plugin to `nose
<http://www.somethingaboutorange.com/mrl/projects/nose/>`_ that loads
the Pylons app *before* scanning for doc tests.

This can be configured in the projects :file:`setup.cfg` under a
``[nosetests]`` block:

.. code-block:: ini

    [nosetests]
    with-pylons=development.ini

Alternate ini files may be specified if the app should be loaded using
a different configuration.

"""
import os
import sys

import nose.plugins
import pkg_resources
from paste.deploy import loadapp

import pylons
from pylons.i18n.translation import _get_translator

pylonsapp = None


class PylonsPlugin(nose.plugins.Plugin):
    """Nose plugin extension

    For use with nose to allow a project to be configured before nose
    proceeds to scan the project for doc tests and unit tests. This
    prevents modules from being loaded without a configured Pylons
    environment.

    """
    enabled = False
    enableOpt = 'pylons_config'
    name = 'pylons'

    def add_options(self, parser, env=os.environ):
        """Add command-line options for this plugin"""
        env_opt = 'NOSE_WITH_%s' % self.name.upper()
        env_opt.replace('-', '_')

        parser.add_option("--with-%s" % self.name,
                          dest=self.enableOpt, type="string",
                          default="",
                          help="Setup Pylons environment with the config file"
                          " specified by ATTR [NOSE_ATTR]")

    def configure(self, options, conf):
        """Configure the plugin"""
        self.config_file = None
        self.conf = conf
        if hasattr(options, self.enableOpt):
            self.enabled = bool(getattr(options, self.enableOpt))
            self.config_file = getattr(options, self.enableOpt)

    def begin(self):
        """Called before any tests are collected or run

        Loads the application, and in turn its configuration.

        """
        global pylonsapp
        path = os.getcwd()
        sys.path.insert(0, path)
        pkg_resources.working_set.add_entry(path)
        self.app = pylonsapp = loadapp('config:' + self.config_file,
                                       relative_to=path)

        # Setup the config and app_globals, only works if we can get
        # to the config object
        conf = getattr(pylonsapp, 'config')
        if conf:
            pylons.config._push_object(conf)

            if 'pylons.app_globals' in conf:
                pylons.app_globals._push_object(conf['pylons.app_globals'])

        # Initialize a translator for tests that utilize i18n
        translator = _get_translator(pylons.config.get('lang'))
        pylons.translator._push_object(translator)

########NEW FILE########
__FILENAME__ = testutil
"""Utility classes for creating workable pylons controllers for unit
testing.

These classes are used solely by Pylons for unit testing controller
functionality.

"""
import gettext

import pylons
from pylons.configuration import request_defaults, response_defaults
from pylons.controllers.util import Request, Response
from pylons.util import ContextObj, PylonsContext


class ControllerWrap(object):
    def __init__(self, controller):
        self.controller = controller

    def __call__(self, environ, start_response):
        app = self.controller()
        app.start_response = None
        return app(environ, start_response)


class SetupCacheGlobal(object):
    def __init__(self, app, environ, setup_g=True, setup_cache=False,
                 setup_session=False):
        if setup_g:
            g = type('G object', (object,), {})
            g.message = 'Hello'
            g.counter = 0
            g.pylons_config = type('App conf', (object,), {})
            g.pylons_config.app_conf = dict(cache_enabled='True')
            self.g = g
        self.app = app
        self.environ = environ
        self.setup_cache = setup_cache
        self.setup_session = setup_session
        self.setup_g = setup_g

    def __call__(self, environ, start_response):
        registry = environ['paste.registry']
        py_obj = PylonsContext()
        environ_config = environ.setdefault('pylons.environ_config', {})
        if self.setup_cache:
            py_obj.cache = environ['beaker.cache']
            registry.register(pylons.cache, environ['beaker.cache'])
            environ_config['cache'] = 'beaker.cache'
        if self.setup_session:
            py_obj.session = environ['beaker.session']
            registry.register(pylons.session, environ['beaker.session'])
            environ_config['session'] = 'beaker.session'
        if self.setup_g:
            py_obj.app_globals = self.g
            registry.register(pylons.app_globals, self.g)
        translator = gettext.NullTranslations()
        py_obj.translator = translator
        registry.register(pylons.translator, translator)

        # Update the environ
        req = Request(environ, charset=request_defaults['charset'],
                      unicode_errors=request_defaults['errors'],
                      decode_param_names=request_defaults['decode_param_names']
        )
        req.language = request_defaults['language']

        response = Response(
            content_type=response_defaults['content_type'],
            charset=response_defaults['charset'])
        response.headers.update(response_defaults['headers'])

        environ.update(self.environ)
        py_obj.config = pylons.config._current_obj()
        py_obj.request = req
        py_obj.response = response
        py_obj.tmpl_context = ContextObj()
        environ['pylons.pylons'] = py_obj
        registry.register(pylons.request, req)
        registry.register(pylons.response, response)
        if 'routes.url' in environ:
            registry.register(pylons.url, environ['routes.url'])
        return self.app(environ, start_response)

########NEW FILE########
__FILENAME__ = url
from repoze.bfg.encode import urlencode
from repoze.bfg.threadlocal import get_current_registry
from repoze.bfg.url import _join_elements

from pylons.interfaces import IRoutesMapper


def route_url(route_name, request, *elements, **kw):
    try:
        reg = request.registry
    except AttributeError:
        reg = get_current_registry()  # b/c
    mapper = reg.getUtility(IRoutesMapper)

    route = mapper.routes.get(route_name)
    if route and 'custom_url_generator' in route.__dict__:
        route_name, request, elements, kw = route.custom_url_generator(
            route_name, request, *elements, **kw)
    anchor = ''
    qs = ''
    app_url = None

    if '_query' in kw:
        qs = '?' + urlencode(kw.pop('_query'), doseq=True)

    if '_anchor' in kw:
        anchor = kw.pop('_anchor')
        if isinstance(anchor, unicode):
            anchor = anchor.encode('utf-8')
        anchor = '#' + anchor

    if '_app_url' in kw:
        app_url = kw.pop('_app_url')

    path = mapper.generate(route_name, kw)  # raises KeyError if generate fails

    if elements:
        suffix = _join_elements(elements)
        if not path.endswith('/'):
            suffix = '/' + suffix
    else:
        suffix = ''

    if app_url is None:
        # we only defer lookup of application_url until here because
        # it's somewhat expensive; we won't need to do it if we've
        # been passed _app_url
        app_url = request.application_url

    return app_url + path + suffix + qs + anchor

########NEW FILE########
__FILENAME__ = util
"""Paste Template and Pylons utility functions

PylonsTemplate is a Paste Template sub-class that configures the source
directory and default plug-ins for a new Pylons project. The minimal
template a more minimal template with less additional directories and
layout.

"""
import logging
import sys

import pkg_resources
from paste.deploy.converters import asbool
from paste.script.appinstall import Installer
from paste.script.templates import Template, var
from tempita import paste_script_template_renderer

import pylons
import pylons.configuration
import pylons.i18n

__all__ = ['AttribSafeContextObj', 'ContextObj', 'PylonsContext',
           'class_name_from_module_name', 'call_wsgi_application']

log = logging.getLogger(__name__)


def call_wsgi_application(application, environ, catch_exc_info=False):
    """
    Call the given WSGI application, returning ``(status_string,
    headerlist, app_iter)``

    Be sure to call ``app_iter.close()`` if it's there.

    If catch_exc_info is true, then returns ``(status_string,
    headerlist, app_iter, exc_info)``, where the fourth item may
    be None, but won't be if there was an exception.  If you don't
    do this and there was an exception, the exception will be
    raised directly.

    """
    captured = []
    output = []

    def start_response(status, headers, exc_info=None):
        if exc_info is not None and not catch_exc_info:
            raise exc_info[0], exc_info[1], exc_info[2]
        captured[:] = [status, headers, exc_info]
        return output.append
    app_iter = application(environ, start_response)
    if not captured or output:
        try:
            output.extend(app_iter)
        finally:
            if hasattr(app_iter, 'close'):
                app_iter.close()
        app_iter = output
    if catch_exc_info:
        return (captured[0], captured[1], app_iter, captured[2])
    else:
        return (captured[0], captured[1], app_iter)


def class_name_from_module_name(module_name):
    """Takes a module name and returns the name of the class it
    defines.

    If the module name contains dashes, they are replaced with
    underscores.

    Example::

        >>> class_name_from_module_name('with-dashes')
        'WithDashes'
        >>> class_name_from_module_name('with_underscores')
        'WithUnderscores'
        >>> class_name_from_module_name('oneword')
        'Oneword'

    """
    words = module_name.replace('-', '_').split('_')
    return ''.join(w.title() for w in words)


class PylonsContext(object):
    """Pylons context object

    All the Pylons Stacked Object Proxies are also stored here, for use
    in generators and async based operation where the globals can't be
    used.

    This object is attached in
    :class:`~pylons.controllers.core.WSGIController` instances as
    :attr:`~WSGIController._py_object`. For example::

        class MyController(WSGIController):
            def index(self):
                pyobj = self._py_object
                return "Environ is %s" % pyobj.request.environ

    """
    pass


class ContextObj(object):
    """The :term:`tmpl_context` object, with strict attribute access
    (raises an Exception when the attribute does not exist)"""
    def __repr__(self):
        attrs = sorted((name, value)
                       for name, value in self.__dict__.iteritems()
                       if not name.startswith('_'))
        parts = []
        for name, value in attrs:
            value_repr = repr(value)
            if len(value_repr) > 70:
                value_repr = value_repr[:60] + '...' + value_repr[-5:]
            parts.append(' %s=%s' % (name, value_repr))
        return '<%s.%s at %s%s>' % (
            self.__class__.__module__,
            self.__class__.__name__,
            hex(id(self)),
            ','.join(parts))


class AttribSafeContextObj(ContextObj):
    """The :term:`tmpl_context` object, with lax attribute access (
    returns '' when the attribute does not exist)"""
    def __getattr__(self, name):
        try:
            return object.__getattribute__(self, name)
        except AttributeError:
            log.debug("No attribute called %s found on c object, returning "
                      "empty string", name)
            return ''


class PylonsTemplate(Template):
    _template_dir = ('pylons', 'templates/default_project')
    template_renderer = staticmethod(paste_script_template_renderer)
    summary = 'Pylons application template'
    egg_plugins = ['PasteScript', 'Pylons']
    vars = [
        var('template_engine', 'mako/genshi/jinja2/etc: Template language',
            default='mako'),
        var('sqlalchemy', 'True/False: Include SQLAlchemy configuration',
            default=False),
    ]
    ensure_names = ['description', 'author', 'author_email', 'url']

    def pre(self, command, output_dir, vars):
        """Called before template is applied."""
        package_logger = vars['package']
        if package_logger == 'root':
            # Rename the app logger in the rare case a project is named 'root'
            package_logger = 'app'
        vars['package_logger'] = package_logger
        vars['template_engine'] = 'mako'

        template_engine = 'mako'

        if template_engine == 'mako':
            # Support a Babel extractor default for Mako
            vars['babel_templates_extractor'] = \
                ("('templates/**.mako', 'mako', {'input_encoding': 'utf-8'})"
                 ",\n%s#%s" % (' ' * 4, ' ' * 8))
        else:
            vars['babel_templates_extractor'] = ''

        # Ensure these exist in the namespace
        for name in self.ensure_names:
            vars.setdefault(name, '')

        vars['version'] = vars.get('version', '0.1')
        vars['zip_safe'] = asbool(vars.get('zip_safe', 'false'))
        vars['sqlalchemy'] = asbool(vars.get('sqlalchemy', 'false'))


class MinimalPylonsTemplate(PylonsTemplate):
    _template_dir = ('pylons', 'templates/minimal_project')
    summary = 'Pylons minimal application template'
    vars = [
        var('template_engine', 'mako/genshi/jinja2/etc: Template language',
            default='mako'),
    ]


class LegacyPylonsTemplate(PylonsTemplate):
    _template_dir = ('pylons', 'templates/legacy_project')
    summary = 'Pylons legacy application template'
    vars = [
        var('template_engine', 'mako/genshi/jinja2/etc: Template language',
            default='mako'),
    ]


class NewPylonsTemplate(PylonsTemplate):
    _template_dir = ('pylons', 'templates/new_project')
    summary = 'Pylons "newstyle" application template'
    vars = []


class NewMinimalPylonsTemplate(PylonsTemplate):
    _template_dir = ('pylons', 'templates/newminimal_project')
    summary = 'Pylons "newstyle" minimal application template'
    vars = []


class NewSQLAlchemyTemplate(PylonsTemplate):
    _template_dir = ('pylons', 'templates/newsqla_project')
    summary = 'Pylons "newstyle" SQLAlchemy template'
    vars = []


class PylonsInstaller(Installer):
    use_cheetah = False
    config_file = 'config/deployment.ini_tmpl'

    def config_content(self, command, vars):
        """
        Called by ``self.write_config``, this returns the text content
        for the config file, given the provided variables.
        """
        modules = [line.strip()
                    for line in self.dist.get_metadata_lines('top_level.txt')
                    if line.strip() and not line.strip().startswith('#')]
        if not modules:
            print >> sys.stderr, 'No modules are listed in top_level.txt'
            print >> sys.stderr, \
                'Try running python setup.py egg_info to regenerate that file'
        for module in modules:
            if pkg_resources.resource_exists(module, self.config_file):
                return self.template_renderer(
                    pkg_resources.resource_string(module, self.config_file),
                    vars, filename=self.config_file)
        # Legacy support for the old location in egg-info
        return super(PylonsInstaller, self).config_content(command, vars)


def resolve_dotted(name):
    return pkg_resources.EntryPoint.parse('x=%s' % name).load(False)

########NEW FILE########
__FILENAME__ = wsgiapp
"""WSGI App Creator

This module is responsible for creating the basic Pylons WSGI
application (PylonsApp). It's generally assumed that it will be called
by Paste, though any WSGI server could create and call the WSGI app as
well.

"""
import logging
import sys

import paste.registry
import pkg_resources
from webob.exc import HTTPNotFound

import pylons
import pylons.templating
from pylons.controllers.util import Request, Response
from pylons.i18n.translation import _get_translator
from pylons.util import (AttribSafeContextObj, ContextObj, PylonsContext,
                         class_name_from_module_name)

__all__ = ['PylonsApp']

log = logging.getLogger(__name__)


class PylonsApp(object):
    """Pylons WSGI Application

    This basic WSGI app is provided should a web developer want to
    get access to the most basic Pylons web application environment
    available. By itself, this Pylons web application does little more
    than dispatch to a controller and setup the context object, the
    request object, and the globals object.

    Additional functionality like sessions, and caching can be setup by
    altering the ``environ['pylons.environ_config']`` setting to
    indicate what key the ``session`` and ``cache`` functionality
    should come from.

    Resolving the URL and dispatching can be customized by sub-classing
    or "monkey-patching" this class. Subclassing is the preferred
    approach.

    """
    def __init__(self, config=None, **kwargs):
        """Initialize a base Pylons WSGI application

        The base Pylons WSGI application requires several keywords, the
        package name, and the globals object. If no helpers object is
        provided then h will be None.

        """
        self.config = config = config or pylons.config._current_obj()
        package_name = config['pylons.package']
        self.helpers = config['pylons.h']
        self.globals = config.get('pylons.app_globals')
        self.environ_config = config['pylons.environ_config']
        self.package_name = package_name
        self.request_options = config['pylons.request_options']
        self.response_options = config['pylons.response_options']
        self.controller_classes = {}
        self.log_debug = False
        self.config.setdefault('lang', None)

        # Cache some options for use during requests
        self._session_key = self.environ_config.get('session', 'beaker.session')
        self._cache_key = self.environ_config.get('cache', 'beaker.cache')

    def __call__(self, environ, start_response):
        """Setup and handle a web request

        PylonsApp splits its functionality into several methods to
        make it easier to subclass and customize core functionality.

        The methods are called in the following order:

        1. :meth:`~PylonsApp.setup_app_env`
        2. :meth:`~PylonsApp.load_test_env` (Only if operating in
           testing mode)
        3. :meth:`~PylonsApp.resolve`
        4. :meth:`~PylonsApp.dispatch`

        The response from :meth:`~PylonsApp.dispatch` is expected to be
        an iterable (valid :pep:`333` WSGI response), which is then
        sent back as the response.

        """
        # Cache the logging level for the request
        log_debug = self.log_debug = logging.DEBUG >= log.getEffectiveLevel()
        environ['pylons.log_debug'] = log_debug

        self.setup_app_env(environ, start_response)
        if 'paste.testing_variables' in environ:
            self.load_test_env(environ)
            if environ['PATH_INFO'] == '/_test_vars':
                paste.registry.restorer.save_registry_state(environ)
                start_response('200 OK', [('Content-type', 'text/plain')])
                return ['%s' % paste.registry.restorer.get_request_id(environ)]

        controller = self.resolve(environ, start_response)
        response = self.dispatch(controller, environ, start_response)

        response_obj = callable(response)
        if 'paste.testing_variables' in environ and response_obj:
            environ['paste.testing_variables']['response'] = response

        try:
            if response_obj:
                return response(environ, start_response)
            elif response is not None:
                return response

            raise Exception("No content returned by controller (Did you "
                            "remember to 'return' it?) in: %r" %
                            controller.__name__)
        finally:
            # Help Python collect ram a bit faster by removing the reference
            # cycle that the pylons object causes
            if 'pylons.pylons' in environ:
                del environ['pylons.pylons']

    def register_globals(self, environ):
        """Registers globals in the environment, called from
        :meth:`~PylonsApp.setup_app_env`

        Override this to control how the Pylons API is setup. Note that
        a custom render function will need to be used if the
        ``pylons.app_globals`` global is not available.

        """
        pylons_obj = environ['pylons.pylons']

        registry = environ['paste.registry']
        registry.register(pylons.response, pylons_obj.response)
        registry.register(pylons.request, pylons_obj.request)

        registry.register(pylons.app_globals, self.globals)
        registry.register(pylons.config, self.config)
        registry.register(pylons.tmpl_context, pylons_obj.tmpl_context)
        registry.register(pylons.translator, pylons_obj.translator)

        if 'session' in pylons_obj.__dict__:
            registry.register(pylons.session, pylons_obj.session)
        if 'cache' in pylons_obj.__dict__:
            registry.register(pylons.cache, pylons_obj.cache)
        elif 'cache' in pylons_obj.app_globals.__dict__:
            registry.register(pylons.cache, pylons_obj.app_globals.cache)

        if 'routes.url' in environ:
            registry.register(pylons.url, environ['routes.url'])

    def setup_app_env(self, environ, start_response):
        """Setup and register all the Pylons objects with the registry

        After creating all the global objects for use in the request,
        :meth:`~PylonsApp.register_globals` is called to register them
        in the environment.

        """
        if self.log_debug:
            log.debug("Setting up Pylons stacked object globals")

        # Setup the basic pylons global objects
        req_options = self.request_options
        req = Request(environ, charset=req_options['charset'],
                      unicode_errors=req_options['errors'],
                      decode_param_names=req_options['decode_param_names'])
        req.language = req_options['language']
        req.config = self.config
        req.link, req.route_dict = environ['wsgiorg.routing_args']

        response = Response(
            content_type=self.response_options['content_type'],
            charset=self.response_options['charset'])
        response.headers.update(self.response_options['headers'])

        # Store a copy of the request/response in environ for faster access
        pylons_obj = PylonsContext()
        pylons_obj.config = self.config
        pylons_obj.request = req
        pylons_obj.response = response
        pylons_obj.app_globals = self.globals
        pylons_obj.h = self.helpers

        if 'routes.url' in environ:
            pylons_obj.url = environ['routes.url']

        environ['pylons.pylons'] = pylons_obj

        environ['pylons.environ_config'] = self.environ_config

        # Setup the translator object
        lang = self.config['lang']
        pylons_obj.translator = _get_translator(lang, pylons_config=self.config)

        if self.config['pylons.strict_tmpl_context']:
            tmpl_context = ContextObj()
        else:
            tmpl_context = AttribSafeContextObj()
        pylons_obj.tmpl_context = req.tmpl_context = tmpl_context

        if self._session_key in environ:
            pylons_obj.session = req.session = environ[self._session_key]
        if self._cache_key in environ:
            pylons_obj.cache = environ[self._cache_key]

        # Load the globals with the registry if around
        if 'paste.registry' in environ:
            self.register_globals(environ)

    def resolve(self, environ, start_response):
        """Uses dispatching information found in
        ``environ['wsgiorg.routing_args']`` to retrieve a controller
        name and return the controller instance from the appropriate
        controller module.

        Override this to change how the controller name is found and
        returned.

        """
        match = environ['wsgiorg.routing_args'][1]
        environ['pylons.routes_dict'] = match
        controller = match.get('controller', match.get('responder'))
        if not controller:
            return

        if self.log_debug:
            log.debug("Resolved URL to controller: %r", controller)
        return self.find_controller(controller)

    def find_controller(self, controller):
        """Locates a controller by attempting to import it then grab
        the SomeController instance from the imported module.

        Controller name is assumed to be a module in the controllers
        directory unless it contains a '.' or ':' which is then assumed
        to be a dotted path to the module and name of the controller
        object.

        Override this to change how the controller object is found once
        the URL has been resolved.

        """
        # If this isn't a basestring, its an object, assume that its the
        # proper instance to begin with
        if not isinstance(controller, basestring):
            return controller

        # Check to see if we've cached the class instance for this name
        if controller in self.controller_classes:
            return self.controller_classes[controller]

        # Check to see if its a dotted name
        if '.' in controller or ':' in controller:
            mycontroller = pkg_resources.EntryPoint.parse(
                'x=%s' % controller).load(False)
            self.controller_classes[controller] = mycontroller
            return mycontroller

        # Pull the controllers class name, import controller
        full_module_name = self.package_name + '.controllers.' \
            + controller.replace('/', '.')

        # Hide the traceback here if the import fails (bad syntax and such)
        __traceback_hide__ = 'before_and_this'

        __import__(full_module_name)
        if hasattr(sys.modules[full_module_name], '__controller__'):
            mycontroller = getattr(sys.modules[full_module_name],
                sys.modules[full_module_name].__controller__)
        else:
            module_name = controller.split('/')[-1]
            class_name = class_name_from_module_name(module_name) + 'Controller'
            if self.log_debug:
                log.debug("Found controller, module: '%s', class: '%s'",
                          full_module_name, class_name)
            mycontroller = getattr(sys.modules[full_module_name], class_name)
        self.controller_classes[controller] = mycontroller
        return mycontroller

    def dispatch(self, controller, environ, start_response):
        """Dispatches to a controller, will instantiate the controller
        if necessary.

        Override this to change how the controller dispatch is handled.

        """
        log_debug = self.log_debug
        if not controller:
            if log_debug:
                log.debug("No controller found, returning 404 HTTP Not Found")
            return HTTPNotFound()(environ, start_response)

        # Is it a responder?
        if 'responder' in environ['pylons.routes_dict']:
            return controller(environ['pylons.pylons'].request)

        # Is it a class? Then its a WSGIController
        if hasattr(controller, '__bases__'):
            if log_debug:
                log.debug("Controller appears to be a class, instantiating")
            controller = controller()
            controller._pylons_log_debug = log_debug

        # Add a reference to the controller app located
        environ['pylons.controller'] = controller

        # Controller is assumed to handle a WSGI call
        if log_debug:
            log.debug("Calling controller class with WSGI interface")
        return controller(environ, start_response)

    def load_test_env(self, environ):
        """Sets up our Paste testing environment"""
        if self.log_debug:
            log.debug("Setting up paste testing environment variables")
        testenv = environ['paste.testing_variables']
        pylons_obj = environ['pylons.pylons']
        testenv['req'] = pylons_obj.request
        testenv['response'] = pylons_obj.response
        testenv['tmpl_context'] = pylons_obj.tmpl_context
        testenv['app_globals'] = testenv['g'] = pylons_obj.app_globals
        testenv['h'] = self.config['pylons.h']
        testenv['config'] = self.config
        if hasattr(pylons_obj, 'session'):
            testenv['session'] = pylons_obj.session
        if hasattr(pylons_obj, 'cache'):
            testenv['cache'] = pylons_obj.cache
        elif hasattr(pylons_obj.app_globals, 'cache'):
            testenv['cache'] = pylons_obj.app_globals.cache

########NEW FILE########
__FILENAME__ = gen-go-pylons
#!/usr/bin/env python
"""Generate go-pylons.py"""
import sys
import textwrap
import virtualenv

filename = 'go-pylons.py'

after_install = """\
import os, subprocess
def after_install(options, home_dir):
    etc = join(home_dir, 'etc')
    ## TODO: this should all come from distutils
    ## like distutils.sysconfig.get_python_inc()
    if sys.platform == 'win32':
        lib_dir = join(home_dir, 'Lib')
        bin_dir = join(home_dir, 'Scripts')
    elif is_jython:
        lib_dir = join(home_dir, 'Lib')
        bin_dir = join(home_dir, 'bin')
    else:
        lib_dir = join(home_dir, 'lib', py_version)
        bin_dir = join(home_dir, 'bin')

    if not os.path.exists(etc):
        os.makedirs(etc)
    subprocess.call([join(bin_dir, 'easy_install'),
        '-f', 'http://pylonshq.com/download/%s', 'Pylons==%s'])
"""


def generate(filename, version):
    path = version
    if '==' in version:
        path = version[:version.find('==')]
    output = virtualenv.create_bootstrap_script(
        textwrap.dedent(after_install % (path, version)))
    fp = open(filename, 'w')
    fp.write(output)
    fp.close()


def main():
    if len(sys.argv) != 2:
        print >> sys.stderr, 'usage: %s version' % sys.argv[0]
        sys.exit(1)
    generate(filename, sys.argv[1])


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = go-pylons
#!/usr/bin/env python
## WARNING: This file is generated
#!/usr/bin/env python
"""Create a "virtual" Python installation
"""

virtualenv_version = "1.5.1"

import sys
import os
import optparse
import re
import shutil
import logging
import tempfile
import distutils.sysconfig
try:
    import subprocess
except ImportError, e:
    if sys.version_info <= (2, 3):
        print 'ERROR: %s' % e
        print 'ERROR: this script requires Python 2.4 or greater; or at least the subprocess module.'
        print 'If you copy subprocess.py from a newer version of Python this script will probably work'
        sys.exit(101)
    else:
        raise
try:
    set
except NameError:
    from sets import Set as set

join = os.path.join
py_version = 'python%s.%s' % (sys.version_info[0], sys.version_info[1])

is_jython = sys.platform.startswith('java')
is_pypy = hasattr(sys, 'pypy_version_info')

if is_pypy:
    expected_exe = 'pypy-c'
elif is_jython:
    expected_exe = 'jython'
else:
    expected_exe = 'python'


REQUIRED_MODULES = ['os', 'posix', 'posixpath', 'nt', 'ntpath', 'genericpath',
                    'fnmatch', 'locale', 'encodings', 'codecs',
                    'stat', 'UserDict', 'readline', 'copy_reg', 'types',
                    're', 'sre', 'sre_parse', 'sre_constants', 'sre_compile',
                    'zlib']

REQUIRED_FILES = ['lib-dynload', 'config']

if sys.version_info[:2] >= (2, 6):
    REQUIRED_MODULES.extend(['warnings', 'linecache', '_abcoll', 'abc'])
if sys.version_info[:2] >= (2, 7):
    REQUIRED_MODULES.extend(['_weakrefset'])
if sys.version_info[:2] <= (2, 3):
    REQUIRED_MODULES.extend(['sets', '__future__'])
if is_pypy:
    # these are needed to correctly display the exceptions that may happen
    # during the bootstrap
    REQUIRED_MODULES.extend(['traceback', 'linecache'])

class Logger(object):

    """
    Logging object for use in command-line script.  Allows ranges of
    levels, to avoid some redundancy of displayed information.
    """

    DEBUG = logging.DEBUG
    INFO = logging.INFO
    NOTIFY = (logging.INFO+logging.WARN)/2
    WARN = WARNING = logging.WARN
    ERROR = logging.ERROR
    FATAL = logging.FATAL

    LEVELS = [DEBUG, INFO, NOTIFY, WARN, ERROR, FATAL]

    def __init__(self, consumers):
        self.consumers = consumers
        self.indent = 0
        self.in_progress = None
        self.in_progress_hanging = False

    def debug(self, msg, *args, **kw):
        self.log(self.DEBUG, msg, *args, **kw)
    def info(self, msg, *args, **kw):
        self.log(self.INFO, msg, *args, **kw)
    def notify(self, msg, *args, **kw):
        self.log(self.NOTIFY, msg, *args, **kw)
    def warn(self, msg, *args, **kw):
        self.log(self.WARN, msg, *args, **kw)
    def error(self, msg, *args, **kw):
        self.log(self.WARN, msg, *args, **kw)
    def fatal(self, msg, *args, **kw):
        self.log(self.FATAL, msg, *args, **kw)
    def log(self, level, msg, *args, **kw):
        if args:
            if kw:
                raise TypeError(
                    "You may give positional or keyword arguments, not both")
        args = args or kw
        rendered = None
        for consumer_level, consumer in self.consumers:
            if self.level_matches(level, consumer_level):
                if (self.in_progress_hanging
                    and consumer in (sys.stdout, sys.stderr)):
                    self.in_progress_hanging = False
                    sys.stdout.write('\n')
                    sys.stdout.flush()
                if rendered is None:
                    if args:
                        rendered = msg % args
                    else:
                        rendered = msg
                    rendered = ' '*self.indent + rendered
                if hasattr(consumer, 'write'):
                    consumer.write(rendered+'\n')
                else:
                    consumer(rendered)

    def start_progress(self, msg):
        assert not self.in_progress, (
            "Tried to start_progress(%r) while in_progress %r"
            % (msg, self.in_progress))
        if self.level_matches(self.NOTIFY, self._stdout_level()):
            sys.stdout.write(msg)
            sys.stdout.flush()
            self.in_progress_hanging = True
        else:
            self.in_progress_hanging = False
        self.in_progress = msg

    def end_progress(self, msg='done.'):
        assert self.in_progress, (
            "Tried to end_progress without start_progress")
        if self.stdout_level_matches(self.NOTIFY):
            if not self.in_progress_hanging:
                # Some message has been printed out since start_progress
                sys.stdout.write('...' + self.in_progress + msg + '\n')
                sys.stdout.flush()
            else:
                sys.stdout.write(msg + '\n')
                sys.stdout.flush()
        self.in_progress = None
        self.in_progress_hanging = False

    def show_progress(self):
        """If we are in a progress scope, and no log messages have been
        shown, write out another '.'"""
        if self.in_progress_hanging:
            sys.stdout.write('.')
            sys.stdout.flush()

    def stdout_level_matches(self, level):
        """Returns true if a message at this level will go to stdout"""
        return self.level_matches(level, self._stdout_level())

    def _stdout_level(self):
        """Returns the level that stdout runs at"""
        for level, consumer in self.consumers:
            if consumer is sys.stdout:
                return level
        return self.FATAL

    def level_matches(self, level, consumer_level):
        """
        >>> l = Logger()
        >>> l.level_matches(3, 4)
        False
        >>> l.level_matches(3, 2)
        True
        >>> l.level_matches(slice(None, 3), 3)
        False
        >>> l.level_matches(slice(None, 3), 2)
        True
        >>> l.level_matches(slice(1, 3), 1)
        True
        >>> l.level_matches(slice(2, 3), 1)
        False
        """
        if isinstance(level, slice):
            start, stop = level.start, level.stop
            if start is not None and start > consumer_level:
                return False
            if stop is not None or stop <= consumer_level:
                return False
            return True
        else:
            return level >= consumer_level

    #@classmethod
    def level_for_integer(cls, level):
        levels = cls.LEVELS
        if level < 0:
            return levels[0]
        if level >= len(levels):
            return levels[-1]
        return levels[level]

    level_for_integer = classmethod(level_for_integer)

def mkdir(path):
    if not os.path.exists(path):
        logger.info('Creating %s', path)
        os.makedirs(path)
    else:
        logger.info('Directory %s already exists', path)

def copyfile(src, dest, symlink=True):
    if not os.path.exists(src):
        # Some bad symlink in the src
        logger.warn('Cannot find file %s (bad symlink)', src)
        return
    if os.path.exists(dest):
        logger.debug('File %s already exists', dest)
        return
    if not os.path.exists(os.path.dirname(dest)):
        logger.info('Creating parent directories for %s' % os.path.dirname(dest))
        os.makedirs(os.path.dirname(dest))
    if symlink and hasattr(os, 'symlink'):
        logger.info('Symlinking %s', dest)
        os.symlink(os.path.abspath(src), dest)
    else:
        logger.info('Copying to %s', dest)
        if os.path.isdir(src):
            shutil.copytree(src, dest, True)
        else:
            shutil.copy2(src, dest)

def writefile(dest, content, overwrite=True):
    if not os.path.exists(dest):
        logger.info('Writing %s', dest)
        f = open(dest, 'wb')
        f.write(content)
        f.close()
        return
    else:
        f = open(dest, 'rb')
        c = f.read()
        f.close()
        if c != content:
            if not overwrite:
                logger.notify('File %s exists with different content; not overwriting', dest)
                return
            logger.notify('Overwriting %s with new content', dest)
            f = open(dest, 'wb')
            f.write(content)
            f.close()
        else:
            logger.info('Content %s already in place', dest)

def rmtree(dir):
    if os.path.exists(dir):
        logger.notify('Deleting tree %s', dir)
        shutil.rmtree(dir)
    else:
        logger.info('Do not need to delete %s; already gone', dir)

def make_exe(fn):
    if hasattr(os, 'chmod'):
        oldmode = os.stat(fn).st_mode & 07777
        newmode = (oldmode | 0555) & 07777
        os.chmod(fn, newmode)
        logger.info('Changed mode of %s to %s', fn, oct(newmode))

def _find_file(filename, dirs):
    for dir in dirs:
        if os.path.exists(join(dir, filename)):
            return join(dir, filename)
    return filename

def _install_req(py_executable, unzip=False, distribute=False):
    if not distribute:
        setup_fn = 'setuptools-0.6c11-py%s.egg' % sys.version[:3]
        project_name = 'setuptools'
        bootstrap_script = EZ_SETUP_PY
        source = None
    else:
        setup_fn = None
        source = 'distribute-0.6.14.tar.gz'
        project_name = 'distribute'
        bootstrap_script = DISTRIBUTE_SETUP_PY
        try:
            # check if the global Python has distribute installed or plain
            # setuptools
            import pkg_resources
            if not hasattr(pkg_resources, '_distribute'):
                location = os.path.dirname(pkg_resources.__file__)
                logger.notify("A globally installed setuptools was found (in %s)" % location)
                logger.notify("Use the --no-site-packages option to use distribute in "
                              "the virtualenv.")
        except ImportError:
            pass

    search_dirs = file_search_dirs()

    if setup_fn is not None:
        setup_fn = _find_file(setup_fn, search_dirs)

    if source is not None:
        source = _find_file(source, search_dirs)

    if is_jython and os._name == 'nt':
        # Jython's .bat sys.executable can't handle a command line
        # argument with newlines
        fd, ez_setup = tempfile.mkstemp('.py')
        os.write(fd, bootstrap_script)
        os.close(fd)
        cmd = [py_executable, ez_setup]
    else:
        cmd = [py_executable, '-c', bootstrap_script]
    if unzip:
        cmd.append('--always-unzip')
    env = {}
    remove_from_env = []
    if logger.stdout_level_matches(logger.DEBUG):
        cmd.append('-v')

    old_chdir = os.getcwd()
    if setup_fn is not None and os.path.exists(setup_fn):
        logger.info('Using existing %s egg: %s' % (project_name, setup_fn))
        cmd.append(setup_fn)
        if os.environ.get('PYTHONPATH'):
            env['PYTHONPATH'] = setup_fn + os.path.pathsep + os.environ['PYTHONPATH']
        else:
            env['PYTHONPATH'] = setup_fn
    else:
        # the source is found, let's chdir
        if source is not None and os.path.exists(source):
            os.chdir(os.path.dirname(source))
            # in this case, we want to be sure that PYTHONPATH is unset (not
            # just empty, really unset), else CPython tries to import the
            # site.py that it's in virtualenv_support
            remove_from_env.append('PYTHONPATH')
        else:
            logger.info('No %s egg found; downloading' % project_name)
        cmd.extend(['--always-copy', '-U', project_name])
    logger.start_progress('Installing %s...' % project_name)
    logger.indent += 2
    cwd = None
    if project_name == 'distribute':
        env['DONT_PATCH_SETUPTOOLS'] = 'true'

    def _filter_ez_setup(line):
        return filter_ez_setup(line, project_name)

    if not os.access(os.getcwd(), os.W_OK):
        cwd = tempfile.mkdtemp()
        if source is not None and os.path.exists(source):
            # the current working dir is hostile, let's copy the
            # tarball to a temp dir
            target = os.path.join(cwd, os.path.split(source)[-1])
            shutil.copy(source, target)
    try:
        call_subprocess(cmd, show_stdout=False,
                        filter_stdout=_filter_ez_setup,
                        extra_env=env,
                        remove_from_env=remove_from_env,
                        cwd=cwd)
    finally:
        logger.indent -= 2
        logger.end_progress()
        if os.getcwd() != old_chdir:
            os.chdir(old_chdir)
        if is_jython and os._name == 'nt':
            os.remove(ez_setup)

def file_search_dirs():
    here = os.path.dirname(os.path.abspath(__file__))
    dirs = ['.', here,
            join(here, 'virtualenv_support')]
    if os.path.splitext(os.path.dirname(__file__))[0] != 'virtualenv':
        # Probably some boot script; just in case virtualenv is installed...
        try:
            import virtualenv
        except ImportError:
            pass
        else:
            dirs.append(os.path.join(os.path.dirname(virtualenv.__file__), 'virtualenv_support'))
    return [d for d in dirs if os.path.isdir(d)]

def install_setuptools(py_executable, unzip=False):
    _install_req(py_executable, unzip)

def install_distribute(py_executable, unzip=False):
    _install_req(py_executable, unzip, distribute=True)

_pip_re = re.compile(r'^pip-.*(zip|tar.gz|tar.bz2|tgz|tbz)$', re.I)
def install_pip(py_executable):
    filenames = []
    for dir in file_search_dirs():
        filenames.extend([join(dir, fn) for fn in os.listdir(dir)
                          if _pip_re.search(fn)])
    filenames = [(os.path.basename(filename).lower(), i, filename) for i, filename in enumerate(filenames)]
    filenames.sort()
    filenames = [filename for basename, i, filename in filenames]
    if not filenames:
        filename = 'pip'
    else:
        filename = filenames[-1]
    easy_install_script = 'easy_install'
    if sys.platform == 'win32':
        easy_install_script = 'easy_install-script.py'
    cmd = [py_executable, join(os.path.dirname(py_executable), easy_install_script), filename]
    if filename == 'pip':
        logger.info('Installing pip from network...')
    else:
        logger.info('Installing %s' % os.path.basename(filename))
    logger.indent += 2
    def _filter_setup(line):
        return filter_ez_setup(line, 'pip')
    try:
        call_subprocess(cmd, show_stdout=False,
                        filter_stdout=_filter_setup)
    finally:
        logger.indent -= 2

def filter_ez_setup(line, project_name='setuptools'):
    if not line.strip():
        return Logger.DEBUG
    if project_name == 'distribute':
        for prefix in ('Extracting', 'Now working', 'Installing', 'Before',
                       'Scanning', 'Setuptools', 'Egg', 'Already',
                       'running', 'writing', 'reading', 'installing',
                       'creating', 'copying', 'byte-compiling', 'removing',
                       'Processing'):
            if line.startswith(prefix):
                return Logger.DEBUG
        return Logger.DEBUG
    for prefix in ['Reading ', 'Best match', 'Processing setuptools',
                   'Copying setuptools', 'Adding setuptools',
                   'Installing ', 'Installed ']:
        if line.startswith(prefix):
            return Logger.DEBUG
    return Logger.INFO

def main():
    parser = optparse.OptionParser(
        version=virtualenv_version,
        usage="%prog [OPTIONS] DEST_DIR")

    parser.add_option(
        '-v', '--verbose',
        action='count',
        dest='verbose',
        default=0,
        help="Increase verbosity")

    parser.add_option(
        '-q', '--quiet',
        action='count',
        dest='quiet',
        default=0,
        help='Decrease verbosity')

    parser.add_option(
        '-p', '--python',
        dest='python',
        metavar='PYTHON_EXE',
        help='The Python interpreter to use, e.g., --python=python2.5 will use the python2.5 '
        'interpreter to create the new environment.  The default is the interpreter that '
        'virtualenv was installed with (%s)' % sys.executable)

    parser.add_option(
        '--clear',
        dest='clear',
        action='store_true',
        help="Clear out the non-root install and start from scratch")

    parser.add_option(
        '--no-site-packages',
        dest='no_site_packages',
        action='store_true',
        help="Don't give access to the global site-packages dir to the "
             "virtual environment")

    parser.add_option(
        '--unzip-setuptools',
        dest='unzip_setuptools',
        action='store_true',
        help="Unzip Setuptools or Distribute when installing it")

    parser.add_option(
        '--relocatable',
        dest='relocatable',
        action='store_true',
        help='Make an EXISTING virtualenv environment relocatable.  '
        'This fixes up scripts and makes all .pth files relative')

    parser.add_option(
        '--distribute',
        dest='use_distribute',
        action='store_true',
        help='Use Distribute instead of Setuptools. Set environ variable '
        'VIRTUALENV_USE_DISTRIBUTE to make it the default ')

    parser.add_option(
        '--prompt=',
        dest='prompt',
        help='Provides an alternative prompt prefix for this environment')

    if 'extend_parser' in globals():
        extend_parser(parser)

    options, args = parser.parse_args()

    global logger

    if 'adjust_options' in globals():
        adjust_options(options, args)

    verbosity = options.verbose - options.quiet
    logger = Logger([(Logger.level_for_integer(2-verbosity), sys.stdout)])

    if options.python and not os.environ.get('VIRTUALENV_INTERPRETER_RUNNING'):
        env = os.environ.copy()
        interpreter = resolve_interpreter(options.python)
        if interpreter == sys.executable:
            logger.warn('Already using interpreter %s' % interpreter)
        else:
            logger.notify('Running virtualenv with interpreter %s' % interpreter)
            env['VIRTUALENV_INTERPRETER_RUNNING'] = 'true'
            file = __file__
            if file.endswith('.pyc'):
                file = file[:-1]
            popen = subprocess.Popen([interpreter, file] + sys.argv[1:], env=env)
            raise SystemExit(popen.wait())

    if not args:
        print 'You must provide a DEST_DIR'
        parser.print_help()
        sys.exit(2)
    if len(args) > 1:
        print 'There must be only one argument: DEST_DIR (you gave %s)' % (
            ' '.join(args))
        parser.print_help()
        sys.exit(2)

    home_dir = args[0]

    if os.environ.get('WORKING_ENV'):
        logger.fatal('ERROR: you cannot run virtualenv while in a workingenv')
        logger.fatal('Please deactivate your workingenv, then re-run this script')
        sys.exit(3)

    if 'PYTHONHOME' in os.environ:
        logger.warn('PYTHONHOME is set.  You *must* activate the virtualenv before using it')
        del os.environ['PYTHONHOME']

    if options.relocatable:
        make_environment_relocatable(home_dir)
        return

    create_environment(home_dir, site_packages=not options.no_site_packages, clear=options.clear,
                       unzip_setuptools=options.unzip_setuptools,
                       use_distribute=options.use_distribute,
                       prompt=options.prompt)
    if 'after_install' in globals():
        after_install(options, home_dir)

def call_subprocess(cmd, show_stdout=True,
                    filter_stdout=None, cwd=None,
                    raise_on_returncode=True, extra_env=None,
                    remove_from_env=None):
    cmd_parts = []
    for part in cmd:
        if len(part) > 40:
            part = part[:30]+"..."+part[-5:]
        if ' ' in part or '\n' in part or '"' in part or "'" in part:
            part = '"%s"' % part.replace('"', '\\"')
        cmd_parts.append(part)
    cmd_desc = ' '.join(cmd_parts)
    if show_stdout:
        stdout = None
    else:
        stdout = subprocess.PIPE
    logger.debug("Running command %s" % cmd_desc)
    if extra_env or remove_from_env:
        env = os.environ.copy()
        if extra_env:
            env.update(extra_env)
        if remove_from_env:
            for varname in remove_from_env:
                env.pop(varname, None)
    else:
        env = None
    try:
        proc = subprocess.Popen(
            cmd, stderr=subprocess.STDOUT, stdin=None, stdout=stdout,
            cwd=cwd, env=env)
    except Exception, e:
        logger.fatal(
            "Error %s while executing command %s" % (e, cmd_desc))
        raise
    all_output = []
    if stdout is not None:
        stdout = proc.stdout
        while 1:
            line = stdout.readline()
            if not line:
                break
            line = line.rstrip()
            all_output.append(line)
            if filter_stdout:
                level = filter_stdout(line)
                if isinstance(level, tuple):
                    level, line = level
                logger.log(level, line)
                if not logger.stdout_level_matches(level):
                    logger.show_progress()
            else:
                logger.info(line)
    else:
        proc.communicate()
    proc.wait()
    if proc.returncode:
        if raise_on_returncode:
            if all_output:
                logger.notify('Complete output from command %s:' % cmd_desc)
                logger.notify('\n'.join(all_output) + '\n----------------------------------------')
            raise OSError(
                "Command %s failed with error code %s"
                % (cmd_desc, proc.returncode))
        else:
            logger.warn(
                "Command %s had error code %s"
                % (cmd_desc, proc.returncode))


def create_environment(home_dir, site_packages=True, clear=False,
                       unzip_setuptools=False, use_distribute=False,
                       prompt=None):
    """
    Creates a new environment in ``home_dir``.

    If ``site_packages`` is true (the default) then the global
    ``site-packages/`` directory will be on the path.

    If ``clear`` is true (default False) then the environment will
    first be cleared.
    """
    home_dir, lib_dir, inc_dir, bin_dir = path_locations(home_dir)

    py_executable = os.path.abspath(install_python(
        home_dir, lib_dir, inc_dir, bin_dir,
        site_packages=site_packages, clear=clear))

    install_distutils(home_dir)

    if use_distribute or os.environ.get('VIRTUALENV_USE_DISTRIBUTE'):
        install_distribute(py_executable, unzip=unzip_setuptools)
    else:
        install_setuptools(py_executable, unzip=unzip_setuptools)

    install_pip(py_executable)

    install_activate(home_dir, bin_dir, prompt)

def path_locations(home_dir):
    """Return the path locations for the environment (where libraries are,
    where scripts go, etc)"""
    # XXX: We'd use distutils.sysconfig.get_python_inc/lib but its
    # prefix arg is broken: http://bugs.python.org/issue3386
    if sys.platform == 'win32':
        # Windows has lots of problems with executables with spaces in
        # the name; this function will remove them (using the ~1
        # format):
        mkdir(home_dir)
        if ' ' in home_dir:
            try:
                import win32api
            except ImportError:
                print 'Error: the path "%s" has a space in it' % home_dir
                print 'To handle these kinds of paths, the win32api module must be installed:'
                print '  http://sourceforge.net/projects/pywin32/'
                sys.exit(3)
            home_dir = win32api.GetShortPathName(home_dir)
        lib_dir = join(home_dir, 'Lib')
        inc_dir = join(home_dir, 'Include')
        bin_dir = join(home_dir, 'Scripts')
    elif is_jython:
        lib_dir = join(home_dir, 'Lib')
        inc_dir = join(home_dir, 'Include')
        bin_dir = join(home_dir, 'bin')
    elif is_pypy:
        lib_dir = home_dir
        inc_dir = join(home_dir, 'include')
        bin_dir = join(home_dir, 'bin')
    else:
        lib_dir = join(home_dir, 'lib', py_version)
        inc_dir = join(home_dir, 'include', py_version)
        bin_dir = join(home_dir, 'bin')
    return home_dir, lib_dir, inc_dir, bin_dir


def change_prefix(filename, dst_prefix):
    prefixes = [sys.prefix]
    if hasattr(sys, 'real_prefix'):
        prefixes.append(sys.real_prefix)
    prefixes = map(os.path.abspath, prefixes)
    filename = os.path.abspath(filename)
    for src_prefix in prefixes:
        if filename.startswith(src_prefix):
            _, relpath = filename.split(src_prefix, 1)
            assert relpath[0] == os.sep
            relpath = relpath[1:]
            return join(dst_prefix, relpath)
    assert False, "Filename %s does not start with any of these prefixes: %s" % \
        (filename, prefixes)

def copy_required_modules(dst_prefix):
    import imp
    for modname in REQUIRED_MODULES:
        if modname in sys.builtin_module_names:
            logger.info("Ignoring built-in bootstrap module: %s" % modname)
            continue
        try:
            f, filename, _ = imp.find_module(modname)
        except ImportError:
            logger.info("Cannot import bootstrap module: %s" % modname)
        else:
            if f is not None:
                f.close()
            dst_filename = change_prefix(filename, dst_prefix)
            copyfile(filename, dst_filename)
            if filename.endswith('.pyc'):
                pyfile = filename[:-1]
                if os.path.exists(pyfile):
                    copyfile(pyfile, dst_filename[:-1])


def install_python(home_dir, lib_dir, inc_dir, bin_dir, site_packages, clear):
    """Install just the base environment, no distutils patches etc"""
    if sys.executable.startswith(bin_dir):
        print 'Please use the *system* python to run this script'
        return

    if clear:
        rmtree(lib_dir)
        ## FIXME: why not delete it?
        ## Maybe it should delete everything with #!/path/to/venv/python in it
        logger.notify('Not deleting %s', bin_dir)

    if hasattr(sys, 'real_prefix'):
        logger.notify('Using real prefix %r' % sys.real_prefix)
        prefix = sys.real_prefix
    else:
        prefix = sys.prefix
    mkdir(lib_dir)
    fix_lib64(lib_dir)
    stdlib_dirs = [os.path.dirname(os.__file__)]
    if sys.platform == 'win32':
        stdlib_dirs.append(join(os.path.dirname(stdlib_dirs[0]), 'DLLs'))
    elif sys.platform == 'darwin':
        stdlib_dirs.append(join(stdlib_dirs[0], 'site-packages'))
    if hasattr(os, 'symlink'):
        logger.info('Symlinking Python bootstrap modules')
    else:
        logger.info('Copying Python bootstrap modules')
    logger.indent += 2
    try:
        # copy required files...
        for stdlib_dir in stdlib_dirs:
            if not os.path.isdir(stdlib_dir):
                continue
            for fn in os.listdir(stdlib_dir):
                if fn != 'site-packages' and os.path.splitext(fn)[0] in REQUIRED_FILES:
                    copyfile(join(stdlib_dir, fn), join(lib_dir, fn))
        # ...and modules
        copy_required_modules(home_dir)
    finally:
        logger.indent -= 2
    mkdir(join(lib_dir, 'site-packages'))
    import site
    site_filename = site.__file__
    if site_filename.endswith('.pyc'):
        site_filename = site_filename[:-1]
    elif site_filename.endswith('$py.class'):
        site_filename = site_filename.replace('$py.class', '.py')
    site_filename_dst = change_prefix(site_filename, home_dir)
    site_dir = os.path.dirname(site_filename_dst)
    writefile(site_filename_dst, SITE_PY)
    writefile(join(site_dir, 'orig-prefix.txt'), prefix)
    site_packages_filename = join(site_dir, 'no-global-site-packages.txt')
    if not site_packages:
        writefile(site_packages_filename, '')
    else:
        if os.path.exists(site_packages_filename):
            logger.info('Deleting %s' % site_packages_filename)
            os.unlink(site_packages_filename)

    if is_pypy:
        stdinc_dir = join(prefix, 'include')
    else:
        stdinc_dir = join(prefix, 'include', py_version)
    if os.path.exists(stdinc_dir):
        copyfile(stdinc_dir, inc_dir)
    else:
        logger.debug('No include dir %s' % stdinc_dir)

    if sys.exec_prefix != prefix:
        if sys.platform == 'win32':
            exec_dir = join(sys.exec_prefix, 'lib')
        elif is_jython:
            exec_dir = join(sys.exec_prefix, 'Lib')
        else:
            exec_dir = join(sys.exec_prefix, 'lib', py_version)
        for fn in os.listdir(exec_dir):
            copyfile(join(exec_dir, fn), join(lib_dir, fn))

    if is_jython:
        # Jython has either jython-dev.jar and javalib/ dir, or just
        # jython.jar
        for name in 'jython-dev.jar', 'javalib', 'jython.jar':
            src = join(prefix, name)
            if os.path.exists(src):
                copyfile(src, join(home_dir, name))
        # XXX: registry should always exist after Jython 2.5rc1
        src = join(prefix, 'registry')
        if os.path.exists(src):
            copyfile(src, join(home_dir, 'registry'), symlink=False)
        copyfile(join(prefix, 'cachedir'), join(home_dir, 'cachedir'),
                 symlink=False)

    mkdir(bin_dir)
    py_executable = join(bin_dir, os.path.basename(sys.executable))
    if 'Python.framework' in prefix:
        if re.search(r'/Python(?:-32|-64)*$', py_executable):
            # The name of the python executable is not quite what
            # we want, rename it.
            py_executable = os.path.join(
                    os.path.dirname(py_executable), 'python')

    logger.notify('New %s executable in %s', expected_exe, py_executable)
    if sys.executable != py_executable:
        ## FIXME: could I just hard link?
        executable = sys.executable
        if sys.platform == 'cygwin' and os.path.exists(executable + '.exe'):
            # Cygwin misreports sys.executable sometimes
            executable += '.exe'
            py_executable += '.exe'
            logger.info('Executable actually exists in %s' % executable)
        shutil.copyfile(executable, py_executable)
        make_exe(py_executable)
        if sys.platform == 'win32' or sys.platform == 'cygwin':
            pythonw = os.path.join(os.path.dirname(sys.executable), 'pythonw.exe')
            if os.path.exists(pythonw):
                logger.info('Also created pythonw.exe')
                shutil.copyfile(pythonw, os.path.join(os.path.dirname(py_executable), 'pythonw.exe'))
        if is_pypy:
            # make a symlink python --> pypy-c
            python_executable = os.path.join(os.path.dirname(py_executable), 'python')
            logger.info('Also created executable %s' % python_executable)
            copyfile(py_executable, python_executable)

    if os.path.splitext(os.path.basename(py_executable))[0] != expected_exe:
        secondary_exe = os.path.join(os.path.dirname(py_executable),
                                     expected_exe)
        py_executable_ext = os.path.splitext(py_executable)[1]
        if py_executable_ext == '.exe':
            # python2.4 gives an extension of '.4' :P
            secondary_exe += py_executable_ext
        if os.path.exists(secondary_exe):
            logger.warn('Not overwriting existing %s script %s (you must use %s)'
                        % (expected_exe, secondary_exe, py_executable))
        else:
            logger.notify('Also creating executable in %s' % secondary_exe)
            shutil.copyfile(sys.executable, secondary_exe)
            make_exe(secondary_exe)

    if 'Python.framework' in prefix:
        logger.debug('MacOSX Python framework detected')

        # Make sure we use the the embedded interpreter inside
        # the framework, even if sys.executable points to
        # the stub executable in ${sys.prefix}/bin
        # See http://groups.google.com/group/python-virtualenv/
        #                              browse_thread/thread/17cab2f85da75951
        original_python = os.path.join(
            prefix, 'Resources/Python.app/Contents/MacOS/Python')
        shutil.copy(original_python, py_executable)

        # Copy the framework's dylib into the virtual
        # environment
        virtual_lib = os.path.join(home_dir, '.Python')

        if os.path.exists(virtual_lib):
            os.unlink(virtual_lib)
        copyfile(
            os.path.join(prefix, 'Python'),
            virtual_lib)

        # And then change the install_name of the copied python executable
        try:
            call_subprocess(
                ["install_name_tool", "-change",
                 os.path.join(prefix, 'Python'),
                 '@executable_path/../.Python',
                 py_executable])
        except:
            logger.fatal(
                "Could not call install_name_tool -- you must have Apple's development tools installed")
            raise

        # Some tools depend on pythonX.Y being present
        py_executable_version = '%s.%s' % (
            sys.version_info[0], sys.version_info[1])
        if not py_executable.endswith(py_executable_version):
            # symlinking pythonX.Y > python
            pth = py_executable + '%s.%s' % (
                    sys.version_info[0], sys.version_info[1])
            if os.path.exists(pth):
                os.unlink(pth)
            os.symlink('python', pth)
        else:
            # reverse symlinking python -> pythonX.Y (with --python)
            pth = join(bin_dir, 'python')
            if os.path.exists(pth):
                os.unlink(pth)
            os.symlink(os.path.basename(py_executable), pth)

    if sys.platform == 'win32' and ' ' in py_executable:
        # There's a bug with subprocess on Windows when using a first
        # argument that has a space in it.  Instead we have to quote
        # the value:
        py_executable = '"%s"' % py_executable
    cmd = [py_executable, '-c', 'import sys; print sys.prefix']
    logger.info('Testing executable with %s %s "%s"' % tuple(cmd))
    proc = subprocess.Popen(cmd,
                            stdout=subprocess.PIPE)
    proc_stdout, proc_stderr = proc.communicate()
    proc_stdout = os.path.normcase(os.path.abspath(proc_stdout.strip()))
    if proc_stdout != os.path.normcase(os.path.abspath(home_dir)):
        logger.fatal(
            'ERROR: The executable %s is not functioning' % py_executable)
        logger.fatal(
            'ERROR: It thinks sys.prefix is %r (should be %r)'
            % (proc_stdout, os.path.normcase(os.path.abspath(home_dir))))
        logger.fatal(
            'ERROR: virtualenv is not compatible with this system or executable')
        if sys.platform == 'win32':
            logger.fatal(
                'Note: some Windows users have reported this error when they installed Python for "Only this user".  The problem may be resolvable if you install Python "For all users".  (See https://bugs.launchpad.net/virtualenv/+bug/352844)')
        sys.exit(100)
    else:
        logger.info('Got sys.prefix result: %r' % proc_stdout)

    pydistutils = os.path.expanduser('~/.pydistutils.cfg')
    if os.path.exists(pydistutils):
        logger.notify('Please make sure you remove any previous custom paths from '
                      'your %s file.' % pydistutils)
    ## FIXME: really this should be calculated earlier
    return py_executable

def install_activate(home_dir, bin_dir, prompt=None):
    if sys.platform == 'win32' or is_jython and os._name == 'nt':
        files = {'activate.bat': ACTIVATE_BAT,
                 'deactivate.bat': DEACTIVATE_BAT}
        if os.environ.get('OS') == 'Windows_NT' and os.environ.get('OSTYPE') == 'cygwin':
            files['activate'] = ACTIVATE_SH
    else:
        files = {'activate': ACTIVATE_SH}

        # suppling activate.fish in addition to, not instead of, the
        # bash script support.
        files['activate.fish'] = ACTIVATE_FISH

        # same for csh/tcsh support...
        files['activate.csh'] = ACTIVATE_CSH



    files['activate_this.py'] = ACTIVATE_THIS
    vname = os.path.basename(os.path.abspath(home_dir))
    for name, content in files.items():
        content = content.replace('__VIRTUAL_PROMPT__', prompt or '')
        content = content.replace('__VIRTUAL_WINPROMPT__', prompt or '(%s)' % vname)
        content = content.replace('__VIRTUAL_ENV__', os.path.abspath(home_dir))
        content = content.replace('__VIRTUAL_NAME__', vname)
        content = content.replace('__BIN_NAME__', os.path.basename(bin_dir))
        writefile(os.path.join(bin_dir, name), content)

def install_distutils(home_dir):
    distutils_path = change_prefix(distutils.__path__[0], home_dir)
    mkdir(distutils_path)
    ## FIXME: maybe this prefix setting should only be put in place if
    ## there's a local distutils.cfg with a prefix setting?
    home_dir = os.path.abspath(home_dir)
    ## FIXME: this is breaking things, removing for now:
    #distutils_cfg = DISTUTILS_CFG + "\n[install]\nprefix=%s\n" % home_dir
    writefile(os.path.join(distutils_path, '__init__.py'), DISTUTILS_INIT)
    writefile(os.path.join(distutils_path, 'distutils.cfg'), DISTUTILS_CFG, overwrite=False)

def fix_lib64(lib_dir):
    """
    Some platforms (particularly Gentoo on x64) put things in lib64/pythonX.Y
    instead of lib/pythonX.Y.  If this is such a platform we'll just create a
    symlink so lib64 points to lib
    """
    if [p for p in distutils.sysconfig.get_config_vars().values()
        if isinstance(p, basestring) and 'lib64' in p]:
        logger.debug('This system uses lib64; symlinking lib64 to lib')
        assert os.path.basename(lib_dir) == 'python%s' % sys.version[:3], (
            "Unexpected python lib dir: %r" % lib_dir)
        lib_parent = os.path.dirname(lib_dir)
        assert os.path.basename(lib_parent) == 'lib', (
            "Unexpected parent dir: %r" % lib_parent)
        copyfile(lib_parent, os.path.join(os.path.dirname(lib_parent), 'lib64'))

def resolve_interpreter(exe):
    """
    If the executable given isn't an absolute path, search $PATH for the interpreter
    """
    if os.path.abspath(exe) != exe:
        paths = os.environ.get('PATH', '').split(os.pathsep)
        for path in paths:
            if os.path.exists(os.path.join(path, exe)):
                exe = os.path.join(path, exe)
                break
    if not os.path.exists(exe):
        logger.fatal('The executable %s (from --python=%s) does not exist' % (exe, exe))
        sys.exit(3)
    return exe

############################################################
## Relocating the environment:

def make_environment_relocatable(home_dir):
    """
    Makes the already-existing environment use relative paths, and takes out
    the #!-based environment selection in scripts.
    """
    home_dir, lib_dir, inc_dir, bin_dir = path_locations(home_dir)
    activate_this = os.path.join(bin_dir, 'activate_this.py')
    if not os.path.exists(activate_this):
        logger.fatal(
            'The environment doesn\'t have a file %s -- please re-run virtualenv '
            'on this environment to update it' % activate_this)
    fixup_scripts(home_dir)
    fixup_pth_and_egg_link(home_dir)
    ## FIXME: need to fix up distutils.cfg

OK_ABS_SCRIPTS = ['python', 'python%s' % sys.version[:3],
                  'activate', 'activate.bat', 'activate_this.py']

def fixup_scripts(home_dir):
    # This is what we expect at the top of scripts:
    shebang = '#!%s/bin/python' % os.path.normcase(os.path.abspath(home_dir))
    # This is what we'll put:
    new_shebang = '#!/usr/bin/env python%s' % sys.version[:3]
    activate = "import os; activate_this=os.path.join(os.path.dirname(__file__), 'activate_this.py'); execfile(activate_this, dict(__file__=activate_this)); del os, activate_this"
    if sys.platform == 'win32':
        bin_suffix = 'Scripts'
    else:
        bin_suffix = 'bin'
    bin_dir = os.path.join(home_dir, bin_suffix)
    home_dir, lib_dir, inc_dir, bin_dir = path_locations(home_dir)
    for filename in os.listdir(bin_dir):
        filename = os.path.join(bin_dir, filename)
        if not os.path.isfile(filename):
            # ignore subdirs, e.g. .svn ones.
            continue
        f = open(filename, 'rb')
        lines = f.readlines()
        f.close()
        if not lines:
            logger.warn('Script %s is an empty file' % filename)
            continue
        if not lines[0].strip().startswith(shebang):
            if os.path.basename(filename) in OK_ABS_SCRIPTS:
                logger.debug('Cannot make script %s relative' % filename)
            elif lines[0].strip() == new_shebang:
                logger.info('Script %s has already been made relative' % filename)
            else:
                logger.warn('Script %s cannot be made relative (it\'s not a normal script that starts with %s)'
                            % (filename, shebang))
            continue
        logger.notify('Making script %s relative' % filename)
        lines = [new_shebang+'\n', activate+'\n'] + lines[1:]
        f = open(filename, 'wb')
        f.writelines(lines)
        f.close()

def fixup_pth_and_egg_link(home_dir, sys_path=None):
    """Makes .pth and .egg-link files use relative paths"""
    home_dir = os.path.normcase(os.path.abspath(home_dir))
    if sys_path is None:
        sys_path = sys.path
    for path in sys_path:
        if not path:
            path = '.'
        if not os.path.isdir(path):
            continue
        path = os.path.normcase(os.path.abspath(path))
        if not path.startswith(home_dir):
            logger.debug('Skipping system (non-environment) directory %s' % path)
            continue
        for filename in os.listdir(path):
            filename = os.path.join(path, filename)
            if filename.endswith('.pth'):
                if not os.access(filename, os.W_OK):
                    logger.warn('Cannot write .pth file %s, skipping' % filename)
                else:
                    fixup_pth_file(filename)
            if filename.endswith('.egg-link'):
                if not os.access(filename, os.W_OK):
                    logger.warn('Cannot write .egg-link file %s, skipping' % filename)
                else:
                    fixup_egg_link(filename)

def fixup_pth_file(filename):
    lines = []
    prev_lines = []
    f = open(filename)
    prev_lines = f.readlines()
    f.close()
    for line in prev_lines:
        line = line.strip()
        if (not line or line.startswith('#') or line.startswith('import ')
            or os.path.abspath(line) != line):
            lines.append(line)
        else:
            new_value = make_relative_path(filename, line)
            if line != new_value:
                logger.debug('Rewriting path %s as %s (in %s)' % (line, new_value, filename))
            lines.append(new_value)
    if lines == prev_lines:
        logger.info('No changes to .pth file %s' % filename)
        return
    logger.notify('Making paths in .pth file %s relative' % filename)
    f = open(filename, 'w')
    f.write('\n'.join(lines) + '\n')
    f.close()

def fixup_egg_link(filename):
    f = open(filename)
    link = f.read().strip()
    f.close()
    if os.path.abspath(link) != link:
        logger.debug('Link in %s already relative' % filename)
        return
    new_link = make_relative_path(filename, link)
    logger.notify('Rewriting link %s in %s as %s' % (link, filename, new_link))
    f = open(filename, 'w')
    f.write(new_link)
    f.close()

def make_relative_path(source, dest, dest_is_directory=True):
    """
    Make a filename relative, where the filename is dest, and it is
    being referred to from the filename source.

        >>> make_relative_path('/usr/share/something/a-file.pth',
        ...                    '/usr/share/another-place/src/Directory')
        '../another-place/src/Directory'
        >>> make_relative_path('/usr/share/something/a-file.pth',
        ...                    '/home/user/src/Directory')
        '../../../home/user/src/Directory'
        >>> make_relative_path('/usr/share/a-file.pth', '/usr/share/')
        './'
    """
    source = os.path.dirname(source)
    if not dest_is_directory:
        dest_filename = os.path.basename(dest)
        dest = os.path.dirname(dest)
    dest = os.path.normpath(os.path.abspath(dest))
    source = os.path.normpath(os.path.abspath(source))
    dest_parts = dest.strip(os.path.sep).split(os.path.sep)
    source_parts = source.strip(os.path.sep).split(os.path.sep)
    while dest_parts and source_parts and dest_parts[0] == source_parts[0]:
        dest_parts.pop(0)
        source_parts.pop(0)
    full_parts = ['..']*len(source_parts) + dest_parts
    if not dest_is_directory:
        full_parts.append(dest_filename)
    if not full_parts:
        # Special case for the current directory (otherwise it'd be '')
        return './'
    return os.path.sep.join(full_parts)



############################################################
## Bootstrap script creation:

def create_bootstrap_script(extra_text, python_version=''):
    """
    Creates a bootstrap script, which is like this script but with
    extend_parser, adjust_options, and after_install hooks.

    This returns a string that (written to disk of course) can be used
    as a bootstrap script with your own customizations.  The script
    will be the standard virtualenv.py script, with your extra text
    added (your extra text should be Python code).

    If you include these functions, they will be called:

    ``extend_parser(optparse_parser)``:
        You can add or remove options from the parser here.

    ``adjust_options(options, args)``:
        You can change options here, or change the args (if you accept
        different kinds of arguments, be sure you modify ``args`` so it is
        only ``[DEST_DIR]``).

    ``after_install(options, home_dir)``:

        After everything is installed, this function is called.  This
        is probably the function you are most likely to use.  An
        example would be::

            def after_install(options, home_dir):
                subprocess.call([join(home_dir, 'bin', 'easy_install'),
                                 'MyPackage'])
                subprocess.call([join(home_dir, 'bin', 'my-package-script'),
                                 'setup', home_dir])

        This example immediately installs a package, and runs a setup
        script from that package.

    If you provide something like ``python_version='2.4'`` then the
    script will start with ``#!/usr/bin/env python2.4`` instead of
    ``#!/usr/bin/env python``.  You can use this when the script must
    be run with a particular Python version.
    """
    filename = __file__
    if filename.endswith('.pyc'):
        filename = filename[:-1]
    f = open(filename, 'rb')
    content = f.read()
    f.close()
    py_exe = 'python%s' % python_version
    content = (('#!/usr/bin/env %s\n' % py_exe)
               + '## WARNING: This file is generated\n'
               + content)
    return content.replace('##EXT' 'END##', extra_text)

import os, subprocess
def after_install(options, home_dir):
    etc = join(home_dir, 'etc')
    ## TODO: this should all come from distutils
    ## like distutils.sysconfig.get_python_inc()
    if sys.platform == 'win32':
        lib_dir = join(home_dir, 'Lib')
        bin_dir = join(home_dir, 'Scripts')
    elif is_jython:
        lib_dir = join(home_dir, 'Lib')
        bin_dir = join(home_dir, 'bin')
    else:
        lib_dir = join(home_dir, 'lib', py_version)
        bin_dir = join(home_dir, 'bin')

    if not os.path.exists(etc):
        os.makedirs(etc)
    subprocess.call([join(bin_dir, 'easy_install'),
        '-f', 'http://pylonshq.com/download/1.0', 'Pylons==1.0'])


##file site.py
SITE_PY = """
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
""".decode("base64").decode("zlib")

##file ez_setup.py
EZ_SETUP_PY = """
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
178BYnMUkw==
""".decode("base64").decode("zlib")

##file distribute_setup.py
DISTRIBUTE_SETUP_PY = """
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
""".decode("base64").decode("zlib")

##file activate.sh
ACTIVATE_SH = """
eJytVU1v4jAQPW9+xTT0ANVS1GsrDlRFAqmFqmG72m0rY5IJsRRslDiktNr/vuMQ8tFQpNU2B4I9
H36eeW/SglkgYvBFiLBKYg0LhCRGD1KhA7BjlUQuwkLIHne12HCNNpz5kVrBgsfBmdWCrUrA5VIq
DVEiQWjwRISuDreW5eE+CtodeLeAnhZEGKMGFXqAciMiJVcoNWx4JPgixDjzEj48QVeCfcqmtzfs
cfww+zG4ZfeD2ciGF7gCHaDMPM1jtvuHXAsPfF2rSGeOxV4iDY5GUGb3xVEYv2aj6WQ0vRseAlMY
G5DKsAawwnQUXt2LQOYlzZoYByqhonqoqfxZf4BLD97i4DukgXADCPgGgdOLTK5arYxZB1xnrc9T
EQFcHoZEAa1gSQioo/TPV5FZrDlxJA+NzwF+Ek1UonOzFnKZp6k5mgLBqSkuuAGXS4whJb5xz/xs
wXCHjiVerAk5eh9Kfz1wqOldtVv9dkbscfjgjKeTA8XPrtaNauX5rInOxaHuOReNtpFjo1/OxdFG
5eY9hJ3L3jqcPJbATggXAemDLZX0MNZRYjSDH7C1wMHQh73DyYfTu8a0F9v+6D8W6XNnF1GEIXW/
JrSKPOtnW1YFat9mrLJkzLbyIlTvYzV0RGXcaTBfVLx7jF2PJ2wyuBsydpm7VSVa4C4Zb6pFO2TR
huypCEPwuQjNftUrNl6GsYZzuFrrLdC9iJjQ3omAPBbcI2lsU77tUD43kw1NPZhTrnZWzuQKLomx
Rd4OXM1ByExVVkmoTwfBJ7Lt10Iq1Kgo23Bmd8Ib1KrGbsbO4Pp2yO4fpnf3s6MnZiwuiJuls1/L
Pu4yUCvhpA+vZaJvWWDTr0yFYYyVnHMqCEq+QniuYX225xmnzRENjbXACF3wkCYNVZ1mBwxoR9Iw
WAo3/36oSOTfgjwEEQKt15e9Xpqm52+oaXxszmnE9GLl65RH2OMmS6+u5acKxDmlPgj2eT5/gQOX
LLK0j1y0Uwbmn438VZkVpqlfNKa/YET/53j+99G8H8tUhr9ZSXs2
""".decode("base64").decode("zlib")

##file activate.fish
ACTIVATE_FISH = """
eJydVm1v4jgQ/s6vmA1wBxUE7X2stJVYlVWR2lK13d6d9laRk0yIr8HmbIe0++tvnIQQB9pbXT5A
Ys/LM55nZtyHx5RrSHiGsMm1gRAh1xhDwU0Kng8hFzMWGb5jBv2E69SDs0TJDdj3MxilxmzPZzP7
pVPMMl+q9bjXh1eZQ8SEkAZULoAbiLnCyGSvvV6SC7IoBcS4Nw0wjcFbvJDcjiuTswzFDpiIQaHJ
lQAjQUi1YRmUboC2uZJig8J4PaCnT5IaDcgsbm/CjinOwgx1KcUTMEhhTgV4g2B1fRk8Le8fv86v
g7v545UHpZB9rKnp+gXsMhxLunIIpwVQxP/l9c/Hq9Xt1epm4R27bva6AJqN92G4YhbMG2i+LB+u
grv71c3dY7B6WtzfLy9bePbp0taDTXSwJQJszUnnp0y57mvpPcrF7ZODyhswtd59+/jdgw+fwBNS
xLSscksUPIDqwwNmCez3PpxGeyBYg6HE0YdcWBxcKczYzuVJi5Wu915vn5oWePCCoPUZBN5B7IgV
MCi54ZDLG7TUZ0HweXkb3M5vFmSpFm/gthhBx0UrveoPpv9AJ9unIbQYdUoe21bKg2q48sPFGVwu
H+afrxd1qvclaNlRFyh1EQ2sSccEuNAGWQwysfVpz1tPajUqbqJUnEcIJkWo6OXDaodK8ZiLdbmM
L1wb+9H0D+pcyPSrX5u5kgWSygRYXCnJUi/KKcuU4cqsAyTKZBiissLc7NFwizvjxtieKBVCIdWz
fzilzPaYyljZN0cGN1v7NnaIPNCGmVy3GKuJaQ6iVjE1Qfm+36hglErwmnAD8hu0dDy4uICBA8ZV
pQr/q/+O0KFW2kjelu9Dgb9SDBsWV4F4x5CswgS0zBVlk5tDMP5bVtUGpslbm81Lu2sdKq7uNMGh
MVQ4fy9xhogC1lS5guhISa0DlBWv0O8odT6/LP+4WZzDV6FzIkEqC0uolGZSZoMnlpxplmD2euaT
O4hkTpPnbztDccey0bhjDaBIqaWQa0uwEtQEwtyU56i4fq54F9IE3ORR6mKriODM4XOYZwaVYLYz
7SPbKkz4i7VkB6/Ot1upDE3znNqYKpM8raa0Bx8vfvntJ32UENsM4aI6gJL+jJwhxhh3jVIDOcpi
m0r2hmEtS8XXXNBk71QCDXTBNhhPiHX2LtHkrVIlhoEshH/EZgdq53Eirqs5iFKMnkOmqZTtr3Xq
djvPTWZT4S3NT5aVLgurMPUWI07BRVYqkQrmtCKohNY8qu9EdACoT6ki0a66XxVF4f9AQ3W38yO5
mWmZmIIpnDFrbXakvKWeZhLwhvrbUH8fahhqD0YUcBDJjEBMQwiznE4y5QbHrbhHBOnUAYzb2tVN
jJa65e+eE2Ya30E2GurxUP8ssA6e/wOnvo3V78d3vTcvMB3n7l3iX1JXWqk=
""".decode("base64").decode("zlib")

##file activate.csh
ACTIVATE_CSH = """
eJx9U11vmzAUffevOCVRu+UB9pws29Kl0iq1aVWllaZlcgxciiViItsQdb9+xiQp+dh4QOB7Pu49
XHqY59IgkwVhVRmLmFAZSrGRNkdgykonhFiqSCRW1sJSmJg8wCDT5QrucRCyHn6WFRKhVGmhKwVp
kUpNiS3emup3TY6XIn7DVNQyJUwlrgthJD6n/iCNv72uhCzCpFx9CRkThRQGKe08cWXJ9db/yh/u
pvzl9mn+PLnjj5P5D1yM8QmXlzBkSdXwZ0H/BBc0mEo5FE5qI2jKhclHOOvy9HD/OO/6YO1mX9vx
sY0H/tPIV0dtqel0V7iZvWyNg8XFcBA0ToEqVeqOdNUEQFvN41SumAv32VtJrakQNSmLWmgp4oJM
yDoBHgoydtoEAs47r5wHHnUal5vbJ8oOI+9wI86vb2d8Nrm/4Xy4RZ8R85E4uTZPB5EZPnTaaAGu
E59J8BE2J8XgrkbLeXMlVoQxznEYFYY8uFFdxsKQRx90Giwx9vSueHP1YNaUSFG4vTaErNSYuBOF
lXiVyXa9Sy3JdClEyK1dD6Nos9mEf8iKlOpmqSNTZnYjNEWiUYn2pKNB3ttcLJ3HmYYXy6Un76f7
r8rRsC1TpTJj7f19m5sUf/V3Ir+x/yjtLu8KjLX/CmN/AcVGUUo=
""".decode("base64").decode("zlib")

##file activate.bat
ACTIVATE_BAT = """
eJyFUkEKgzAQvAfyhz0YaL9QEWpRqlSjWGspFPZQTevFHOr/adQaU1GaUzI7Mzu7ZF89XhKkEJS8
qxaKMMsvboQ+LxxE44VICSW1gEa2UFaibqoS0iyJ0xw2lIA6nX5AHCu1jpRsv5KRjknkac9VLVug
sX9mtzxIeJDE/mg4OGp47qoLo3NHX2jsMB3AiDht5hryAUOEifoTdCXbSh7V0My2NMq/Xbh5MEjU
ZT63gpgNT9lKOJ/CtHsvT99re3pX303kydn4HeyOeAg5cjf2EW1D6HOPkg9NGKhu
""".decode("base64").decode("zlib")

##file deactivate.bat
DEACTIVATE_BAT = """
eJxzSE3OyFfIT0vj4spMU0hJTcvMS01RiPf3cYkP8wwKCXX0iQ8I8vcNCFHQ4FIAguLUEgWIgK0q
FlWqXJpcICVYpGzx2BAZ4uHv5+Hv6wq1BWINXBTdKriEKkI1DhW2QAfhttcxxANiFZCBbglQSJUL
i2dASrm4rFz9XLgAwJNbyQ==
""".decode("base64").decode("zlib")

##file distutils-init.py
DISTUTILS_INIT = """
eJytV92L4zYQf9dfMU0ottuse/TeFkKh3MvC0Ydy0IdlMVpbTtR1JCMpm+T++s5Y/pBs53oPZ1hQ
pPnSb34zo5WnVhsH2jLpV/Y2Li/cKKkOFoYN3Za6ErAdFtKC0g44vEvjzrwR6h1Oujo3YgdWw0VA
yRWcLUo6cBpqqSpwRwHWVY18ZRB9W3jq3HDlfoIvqK7NG2gF7a297VANvZ3O1sGrQI/eDe5yB0ZY
WQkLUpHxhVX09NDe3FGr31BL1lJUD9f8ln+FShpROm1ujOFS8ZOAPUKRt9wd836Hjqw7O9nYgvYD
iX+1VOlMPPXQ5EVRy0YURbaDZDSQZEzWo7rS5kSLNHaQwX4RRLrQGe1nj92Fh1zltEhHDDZfEO0g
O6MraHn5xg8IpYOfLfC2FdxYShLC64EES4A0uuROYhq49Zs368RpMvTHJmOiscKHUXRXKIpcKiuM
Sz/sYHa7TkxcRYkkEhN8HZaxKCJXFFJJh+baW5JluRG8SjM20JHEA9qWWtXywBjbbvF2rjzC61k2
VSGuDibTUGlhVeLgTekLHPEP73wQrrscUsUGrPCGjkTCC1JXXyw8EJWP3FSUZY8IiSCCRp97dnfO
RUUx5a0RtbxSzLX/3XBXYxIpyQka/fh74pGrjQ5QzUt9OnFV5dMV+otOG5gQjctxozNTNtzaSSiN
JHqu0FeJmsqRN/KrKHRLGbaQWtHUgRB9FDfu5giN4eZWIDqWCv8vrcTjrNZgRXQPzy+RmGjQpLRI
EKz0UqQLlR28ciusM8jn7PtcLPZy2zbSDeyyos0iO+ybBgPyRvSk/CEFm8IndQebz8iXTRbbjhDP
5xh7iJfBrKd/Nenjj6Jvgp2B+W7AnP102BXH5IZWPV3tI2MUOvXowpdS12IIXhLLP0lKyeuZrpEv
pFhPqHg3JFTd1cceVp0EsPgGU0wFO2u4iyYRoFYfEm9kG/RZcUUBm87t9mFtx9iCtC9kx4Rt4R8a
OdgzSt40vtyFecAZZ8BfCOhCrC8djMGPFaz2Vlt5TSZCk053+37wbLDLRXfZ+F45NtdVpVWdudSC
xgODI8EsiLoTl5aO0lhoigX7GHZDHAY4LxoMIu1gXPYPksmFquxF4uRKZhEnKzXu82HESb+LlNQz
Fh/RvFJVuhK+Ee5slBdj30FcRGdJ5rhKxtkyKxWcGoV/WOCYKqkNDYJ5fNQVx3g400tpJBS2FSU+
Tco9ss8nZ08dtscGQfSby87b73fOw+4UgrEMNnY6uMzYvSDxPVPpsij6+l0/ZPfuH0Iz010giY34
HpL0ZLyLJB4ukaQRU+GwptO7yIZCQE33B0K9iCqO6X+AR4n7wAeH68DPkJzpTsD3x+/cj9LIVHC2
An1wmv7CzWHoqR02vb0VL73siP+3nkX0YbQ0l9f6WDyOm24cj3rxO2MMip6kpcu6VCefn/789PR3
0v0fg21sFIp70rj9PCi8YDRDXFucym/43qN+iENh1Jy/dIIIqF3OIkDvBMsdx+huWv8Kz73vl8g5
WQ3JOGqwu3lb4dfKKbvLigXDQsb8B/xt39Q=
""".decode("base64").decode("zlib")

##file distutils.cfg
DISTUTILS_CFG = """
eJxNj00KwkAMhfc9xYNuxe4Ft57AjYiUtDO1wXSmNJnK3N5pdSEEAu8nH6lxHVlRhtDHMPATA4uH
xJ4EFmGbvfJiicSHFRzUSISMY6hq3GLCRLnIvSTnEefN0FIjw5tF0Hkk9Q5dRunBsVoyFi24aaLg
9FDOlL0FPGluf4QjcInLlxd6f6rqkgPu/5nHLg0cXCscXoozRrP51DRT3j9QNl99AP53T2Q=
""".decode("base64").decode("zlib")

##file activate_this.py
ACTIVATE_THIS = """
eJyNUlGL2zAMfvevEBlHEujSsXsL9GGDvW1jD3sZpQQ3Ua7aJXawnbT595Ocpe0dO5ghseVP+vRJ
VpIkn2cYPZknwAvWLXWYhRP5Sk4baKgOWRWNqtpdgTyH2Y5wpq5Tug406YAgKEzkwqg7NBPwR86a
Hk0olPopaK0NHJHzYQPnE5rI0o8+yBUwiBfyQcT8mMPJGiAT0A0O+b8BY4MKJ7zPcSSzHaKrSpJE
qeDmUgGvVbPCS41DgO+6xy/OWbfAThMn/OQ9ukDWRCSLiKzk1yrLjWapq6NnvHUoHXQ4bYPdrsVX
4lQMc/q6ZW975nmSK+oH6wL42a9H65U6aha342Mh0UVDzrD87C1bH73s16R5zsStkBZDp0NrXQ+7
HaRnMo8f06UBnljKoOtn/YT+LtdvSyaT/BtIv9KR60nF9f3qmuYKO4//T9ItJMsjPfgUHqKwCZ3n
xu/Lx8M/UvCLTxW7VULHxB1PRRbrYfvWNY5S8it008jOjcleaMqVBDnUXcWULV2YK9JEQ92OfC96
1Tv4ZicZZZ7GpuEpZbbeQ7DxquVx5hdqoyFSSmXwfC90f1Dc7hjFs/tK99I0fpkI8zSLy4tSy+sI
3vMWehjQNJmE5VePlZbL61nzX3S93ZcfDqznnkb9AZ3GWJU=
""".decode("base64").decode("zlib")

if __name__ == '__main__':
    main()

## TODO:
## Copy python.exe.manifest
## Monkeypatch distutils.sysconfig

########NEW FILE########
__FILENAME__ = conftest
import sys
import os
import shutil
import pkg_resources

here = os.path.dirname(__file__)
base = os.path.dirname(here)
sys.path.append(here)
sys.path.insert(0, base)

here = os.path.dirname(__file__)

pkg_resources.working_set.add_entry(base)

if not os.environ.get('PASTE_TESTING'):
    output_dir = os.path.join(here, 'test_webapps', 'output')
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)


########NEW FILE########
__FILENAME__ = test_basic_app
import os
import re
import sys


from nose.tools import raises

from __init__ import test_root


def make_app(global_conf, full_stack=True, static_files=True, include_cache_middleware=False, attribsafe=False, **app_conf):
    import pylons
    import pylons.configuration as configuration
    from beaker.cache import CacheManager
    from beaker.middleware import SessionMiddleware, CacheMiddleware
    from nose.tools import raises
    from paste.registry import RegistryManager
    from paste.deploy.converters import asbool
    from pylons.decorators import jsonify
    from pylons.middleware import ErrorHandler, StatusCodeRedirect
    from pylons.wsgiapp import PylonsApp
    from routes import Mapper
    from routes.middleware import RoutesMiddleware
    
    paths = dict(root=os.path.join(test_root, 'sample_controllers'), controllers=os.path.join(test_root, 'sample_controllers', 'controllers'))

    config = configuration.pylons_config
    config.init_app(global_conf, app_conf, package='sample_controllers', paths=paths)
    map = Mapper(directory=config['pylons.paths']['controllers'])
    map.connect('/{controller}/{action}')
    map.connect('/test_func', controller='sample_controllers.controllers.hello:special_controller')
    map.connect('/test_empty', controller='sample_controllers.controllers.hello:empty_wsgi')
    config['routes.map'] = map
    
    class AppGlobals(object):
        def __init__(self):
            self.cache = 'Nothing here but a string'
    
    config['pylons.app_globals'] = AppGlobals()
    
    if attribsafe:
        config['pylons.strict_tmpl_context'] = False
    
    app = PylonsApp(config=config)
    app = RoutesMiddleware(app, config['routes.map'], singleton=False)
    if include_cache_middleware:
        app = CacheMiddleware(app, config)
    app = SessionMiddleware(app, config)

    if asbool(full_stack):
        app = ErrorHandler(app, global_conf, **config['pylons.errorware'])
        if asbool(config['debug']):
            app = StatusCodeRedirect(app)
        else:
            app = StatusCodeRedirect(app, [401, 403, 404, 500])
    app = RegistryManager(app)

    app.config = config
    return app

class TestWsgiApp(object):
    def setUp(self):
        from paste.fixture import TestApp
        from routes.util import URLGenerator
        
        app = make_app({})
        self.app = TestApp(app)
        self.url = URLGenerator(app.config['routes.map'], {})
    
    def test_testvars(self):
        resp = self.app.get('/_test_vars', extra_environ={'paste.testing_variables': True})
        assert re.match(r'^\d+$', resp.body)
    
    def test_exception_resp_attach(self):
        resp = self.app.get('/test_func', expect_errors=True)
        assert resp.status == 404
    
    @raises(Exception)
    def test_no_content(self):
        resp = self.app.get('/test_empty', expect_errors=True)
        assert 'wontgethre'
    
    def test_middleware_cache_obj_instance(self):
        from paste.fixture import TestApp
        app = TestApp(make_app({}, include_cache_middleware=True))
        resp = app.get('/hello/index')
        assert resp.cache
    
    def test_attribsafe_tmpl_context(self):
        from paste.fixture import TestApp
        app = TestApp(make_app({}, attribsafe=True))
        resp = app.get('/hello/index')
        assert 'Hello World' in resp
    
    def test_cache_obj_appglobals(self):
        resp = self.app.get('/hello/index', extra_environ={'paste.testing_variables': True})
        assert resp.cache == 'Nothing here but a string'
    
    def test_controller_name_override(self):
        resp = self.app.get('/goodbye/index')
        assert 'Hello World' in resp


class TestJsonifyDecorator(object):
    def setUp(self):
        from paste.fixture import TestApp
        from routes.util import URLGenerator
        app = make_app({})
        self.config = app.config
        self.app = TestApp(app)
        self.url = URLGenerator(app.config['routes.map'], {})
    
    def test_basic_response(self):
        response = self.app.get('/hello/index')
        assert 'Hello World' in response
    
    def test_config(self):
        import pylons
        import pylons.configuration as configuration
        assert pylons.config == configuration.config

    @raises(AssertionError)
    def test_eval(self):
        from paste.fixture import TestApp
        app = TestApp(make_app(dict(debug='True')))
        app.get('/hello/oops', status=500, extra_environ={'paste.throw_errors': False})

    def test_set_lang(self):
        self._test_set_lang('set_lang')

    def test_set_lang_pylonscontext(self):
        self._test_set_lang('set_lang_pylonscontext')

    def _test_set_lang(self, action):
        response = self.app.get(self.url(controller='i18nc', action=action, lang='ja'))
        assert u'\u8a00\u8a9e\u8a2d\u5b9a\u3092\u300cja\u300d\u306b\u5909\u66f4\u3057\u307e\u3057\u305f'.encode('utf-8') in response
        response = self.app.get(self.url(controller='i18nc', action=action, lang='ch'))
        assert 'Could not set language to "ch"' in response

    def test_detect_lang(self):
        response = self.app.get(self.url(controller='i18nc', action='i18n_index'), headers={
                'Accept-Language':'fr;q=0.6, en;q=0.1, ja;q=0.3'})
        # expect japanese fallback for nonexistent french.
        assert u'\u6839\u672c\u30a4\u30f3\u30c7\u30af\u30b9\u30da\u30fc\u30b8'.encode('utf-8') in response

    def test_no_lang(self):
        response = self.app.get(self.url(controller='i18nc', action='no_lang'))
        assert 'No language' in response
        assert 'No languages' in response
    
    def test_langs(self):
        response = self.app.get(self.url(controller='i18nc', action='langs'), headers={
                'Accept-Language':'fr;q=0.6, en;q=0.1, ja;q=0.3'})
        assert "['fr', 'ja', 'en-us']" in response

########NEW FILE########
__FILENAME__ = test_controller
# -*- coding: utf-8 -*-
from paste.fixture import TestApp
from paste.registry import RegistryManager
from webob.exc import status_map

import pylons
from pylons.controllers import WSGIController

from pylons.testutil import SetupCacheGlobal, ControllerWrap
from __init__ import TestWSGIController, TestMiddleware

class BasicWSGIController(WSGIController):
    def __init__(self):
        self._pylons_log_debug = True

    def __before__(self):
        pylons.response.headers['Cache-Control'] = 'private'
    
    def __after__(self):
        pylons.response.set_cookie('big_message', 'goodbye')
    
    def index(self):
        return 'hello world'

    def yield_fun(self):
        def its():
            x = 0
            while x < 100:
                yield 'hi'
                x += 1
        return its()
    
    def strme(self):
        return "hi there"
    
    def use_redirect(self):
        pylons.response.set_cookie('message', 'Hello World')
        exc = status_map[301]
        raise exc('/elsewhere').exception
    
    def use_customnotfound(self):
        exc = status_map[404]
        raise exc('Custom not found').exception
    
    def header_check(self):
        pylons.response.headers['Content-Type'] = 'text/plain'
        return "Hello all!"
    
    def nothing(self):
        return

    def params(self):
        items = pylons.request.params.mixed().items()
        items.sort()
        return str(items)

    def list(self):
        return ['from', ' a ', 'list']

class FilteredWSGIController(WSGIController):
    def __init__(self):
        self.before = 0
        self.after = 0

    def __before__(self):
        self.before += 1

    def __after__(self):
        self.after += 1
        action = pylons.request.environ['pylons.routes_dict'].get('action')
        if action in ('after_response', 'after_string_response'):
            pylons.response.write(' from __after__')

    def index(self):
        return 'hi all, before is %s' % self.before

    def after_response(self):
        return 'hi'

    def after_string_response(self):
        return 'hello'

class TestBasicWSGI(TestWSGIController):
    def __init__(self, *args, **kargs):
        TestWSGIController.__init__(self, *args, **kargs)
        self.baseenviron = {}
        app = ControllerWrap(BasicWSGIController)
        app = self.sap = SetupCacheGlobal(app, self.baseenviron)
        app = TestMiddleware(app)
        app = RegistryManager(app)
        self.app = TestApp(app)
        
    def setUp(self):
        TestWSGIController.setUp(self)
        self.baseenviron.update(self.environ)

    def test_wsgi_call(self):
        resp = self.get_response()
        assert 'hello world' in resp
    
    def test_yield_wrapper(self):
        resp = self.get_response(action='yield_fun')
        assert 'hi' * 100 in resp

    def test_404(self):
        self.environ['paste.config']['global_conf']['debug'] = False
        self.environ['pylons.routes_dict']['action'] = 'notthere'
        resp = self.app.get('/', status=404)
        assert resp.status == 404
    
    def test_404exception(self):
        self.environ['paste.config']['global_conf']['debug'] = False
        self.environ['pylons.routes_dict']['action'] = 'use_customnotfound'
        resp = self.app.get('/', status=404)
        assert 'pylons.controller.exception' in resp.environ
        exc = resp.environ['pylons.controller.exception']
        assert exc.detail == 'Custom not found'
        assert resp.status == 404
    
    def test_private_func(self):
        self.baseenviron['pylons.routes_dict']['action'] = '_private'
        resp = self.app.get('/', status=404)
        assert resp.status == 404
    
    def test_strme_func(self):
        self.baseenviron['pylons.routes_dict']['action'] = 'strme'
        resp = self.app.get('/')
        assert "hi there" in resp
    
    def test_header_check(self):
        self.baseenviron['pylons.routes_dict']['action'] = 'header_check'
        resp = self.app.get('/')
        assert "Hello all!" in resp
        assert resp.response.headers['Content-Type'] == 'text/plain'
        assert resp.response.headers['Cache-Control'] == 'private'
        assert resp.header('Content-Type') == 'text/plain'
    
    def test_head(self):
        self.baseenviron['pylons.routes_dict']['action'] = 'header_check'
        resp = self.app._gen_request('HEAD', '/')
        assert '' == resp.body
        assert resp.header('Content-Type') == 'text/plain'

    def test_redirect(self):
        self.baseenviron['pylons.routes_dict']['action'] = 'use_redirect'
        resp = self.app.get('/', status=301)

    def test_nothing(self):
        self.baseenviron['pylons.routes_dict']['action'] = 'nothing'
        resp = self.app.get('/')
        assert '' == resp.body
        assert resp.response.headers['Cache-Control'] == 'private'

    def test_unicode_action(self):
        self.baseenviron['pylons.routes_dict']['action'] = u'ÐžÐ±ÑÑƒÐ¶Ð´ÐµÐ½Ð¸ÐµÐšÐ¾Ð¼Ð¿Ð°Ð½Ð¸Ð¹'
        resp = self.app.get('/', status=404)

    def test_params(self):
        self.baseenviron['pylons.routes_dict']['action'] = u'params'
        resp = self.app.get('/?foo=bar')
        assert "'foo', u'bar')]" in resp, str(resp)
        resp = self.app.post('/?foo=bar', params=dict(snafu='snafoo'))
        assert "'foo', u'bar')" in resp, str(resp)
        assert "'snafu', u'snafoo')]" in resp, str(resp)
        resp = self.app.put('/?foo=bar', params=dict(snafu='snafoo'))
        assert "'foo', u'bar')" in resp, str(resp)
        assert "'snafu', u'snafoo')]" in resp, str(resp)

    def test_list(self):
        self.baseenviron['pylons.routes_dict']['action'] = 'list'
        assert 'from a list' in self.app.get('/')

class TestFilteredWSGI(TestWSGIController):
    def __init__(self, *args, **kargs):
        TestWSGIController.__init__(self, *args, **kargs)
        self.baseenviron = {}
        app = ControllerWrap(FilteredWSGIController)
        app = self.sap = SetupCacheGlobal(app, self.baseenviron)
        app = RegistryManager(app)
        self.app = TestApp(app)
        
    def setUp(self):
        TestWSGIController.setUp(self)
        self.baseenviron.update(self.environ)
    
    def test_before(self):
        resp = self.get_response(action='index')
        assert 'hi' in resp
        assert 'before is 1' in resp

    def test_after_response(self):
        resp = self.get_response(action='after_response')
        assert 'hi from __after__' in resp

    def test_after_string_response(self):
        resp = self.get_response(action='after_string_response')
        assert 'hello from __after__' in resp

    def test_start_response(self):
        self.baseenviron['pylons.routes_dict']['action'] = 'start_response'
        self.app.get('/', status=404)

########NEW FILE########
__FILENAME__ = test_decorator_authenticate_form
# -*- coding: utf-8 -*-
import logging
import logging.handlers
import os

from beaker.middleware import SessionMiddleware
from paste.fixture import TestApp
from paste.registry import RegistryManager
from routes import request_config

from __init__ import data_dir, TestWSGIController

session_dir = os.path.join(data_dir, 'session')

try:
    import shutil
    shutil.rmtree(session_dir)
except:
    pass


# Eat the logging handler messages
my_logger = logging.getLogger()
my_logger.setLevel(logging.INFO)
# Add the log message handler to the logger
class NullHandler(logging.Handler):
    def emit(self, record):
        pass
my_logger.addHandler(NullHandler())


def make_protected():
    from pylons.controllers import WSGIController
    from pylons.decorators.secure import authenticate_form
    from webhelpers.pylonslib import secure_form
    from pylons import request
    
    class ProtectedController(WSGIController):
        def form(self):
            request_config().environ = request.environ
            return secure_form.authentication_token()

        @authenticate_form
        def protected(self):
            request_config().environ = request.environ
            return 'Authenticated'
    return ProtectedController


class TestAuthenticateFormDecorator(TestWSGIController):
    def setUp(self):
        from pylons.testutil import ControllerWrap, SetupCacheGlobal
        ProtectedController = make_protected()
        TestWSGIController.setUp(self)
        app = ControllerWrap(ProtectedController)
        app = SetupCacheGlobal(app, self.environ, setup_session=True)
        app = SessionMiddleware(app, {}, data_dir=session_dir)
        app = RegistryManager(app)
        self.app = TestApp(app)

    def test_unauthenticated(self):
        from pylons.decorators.secure import csrf_detected_message
        
        self.environ['pylons.routes_dict']['action'] = 'protected'
        response = self.app.post('/protected', extra_environ=self.environ,
                                 expect_errors=True)
        assert response.status == 403
        assert csrf_detected_message in response

    def test_authenticated(self):
        from webhelpers.pylonslib import secure_form
        
        self.environ['pylons.routes_dict']['action'] = 'form'
        response = self.app.get('/form', extra_environ=self.environ)
        token = response.body

        self.environ['pylons.routes_dict']['action'] = 'protected'
        response = self.app.post('/protected',
                                 params={secure_form.token_key: token},
                                 extra_environ=self.environ,
                                 expect_errors=True)
        assert 'Authenticated' in response

        self.environ['pylons.routes_dict']['action'] = 'protected'
        response = self.app.put('/protected',
                                params={secure_form.token_key: token},
                                extra_environ=self.environ,
                                expect_errors=True)
        assert 'Authenticated' in response

        # GET with token_key in query string
        response = self.app.get('/protected',
                                 params={secure_form.token_key: token},
                                 extra_environ=self.environ,
                                 expect_errors=True)
        assert 'Authenticated' in response

        # POST with token_key in query string
        response = self.app.post('/protected?' + secure_form.token_key + '=' + token,
                                 extra_environ=self.environ,
                                 expect_errors=True)
        assert 'Authenticated' in response

########NEW FILE########
__FILENAME__ = test_decorator_cache
import os
import shutil
import time

from webtest import TestApp
from paste.registry import RegistryManager

from beaker.middleware import CacheMiddleware

from __init__ import data_dir, TestWSGIController

environ = {}
sap = None

def make_cache_controller():
    global sap
    import pylons
    from pylons.decorators.cache import beaker_cache, create_cache_key

    from pylons.controllers import WSGIController, XMLRPCController
    from pylons.testutil import SetupCacheGlobal, ControllerWrap
    
    class CacheController(WSGIController):
        @beaker_cache(key=None, invalidate_on_startup=True)
        def test_default_cache_decorator_invalidate(self):
            pylons.app_globals.counter += 1
            return 'Counter=%s' % pylons.app_globals.counter

        @beaker_cache(key=None)
        def test_default_cache_decorator(self):
            pylons.app_globals.counter += 1
            return 'Counter=%s' % pylons.app_globals.counter

        def test_default_cache_decorator_func(self):
            def func():
                pylons.app_globals.counter += 1
                return 'Counter=%s' % pylons.app_globals.counter
            func = beaker_cache(key=None)(func)
            return func()
    
        def test_response_cache_func(self, use_cache_status=True):
            pylons.response.status_int = 404
            def func():
                pylons.app_globals.counter += 1
                return 'Counter=%s' % pylons.app_globals.counter
            if use_cache_status:
                func = beaker_cache(key=None)(func)
            else:
                func = beaker_cache(key=None, cache_response=False)(func)
            return func()

        @beaker_cache(key=None, type='dbm')
        def test_dbm_cache_decorator(self):
            pylons.app_globals.counter += 1
            return 'Counter=%s' % pylons.app_globals.counter

        @beaker_cache(key="param", query_args=True)
        def test_get_cache_decorator(self):
            pylons.app_globals.counter += 1
            return 'Counter=%s' % pylons.app_globals.counter

        @beaker_cache(query_args=True)
        def test_get_cache_default(self):
            pylons.app_globals.counter += 1
            return 'Counter=%s' % pylons.app_globals.counter

        @beaker_cache(expire=1)
        def test_expire_cache_decorator(self):
            pylons.app_globals.counter += 1
            return 'Counter=%s' % pylons.app_globals.counter

        @beaker_cache(expire=1)
        def test_expire_dbm_cache_decorator(self):
            pylons.app_globals.counter += 1
            return 'Counter=%s' % pylons.app_globals.counter

        @beaker_cache(key="id")
        def test_key_cache_decorator(self, id):
            pylons.app_globals.counter += 1
            return 'Counter=%s, id=%s' % (pylons.app_globals.counter, id)

        @beaker_cache(key=["id", "id2"])
        def test_keyslist_cache_decorator(self, id, id2="123"):
            pylons.app_globals.counter += 1
            return 'Counter=%s, id=%s' % (pylons.app_globals.counter, id)

        def test_invalidate_cache(self):
            ns, key = create_cache_key(CacheController.test_default_cache_decorator)
            c = pylons.cache.get_cache(ns)
            c.remove_value(key)

        def test_invalidate_dbm_cache(self):
            ns, key = create_cache_key(CacheController.test_dbm_cache_decorator)
            c = pylons.cache.get_cache(ns, type='dbm')
            c.remove_value(key)

        @beaker_cache(cache_headers=('content-type','content-length', 'x-powered-by'))
        def test_header_cache(self):
            pylons.response.headers['Content-Type'] = 'application/special'
            pylons.response.headers['x-powered-by'] = 'pylons'
            pylons.response.headers['x-dont-include'] = 'should not be included'
            return "Hello folks, time is %s" % time.time()

        @beaker_cache(query_args=True)
        def test_cache_key_dupe(self):
            return "Hello folks, time is %s" % time.time()
    
    app = ControllerWrap(CacheController)
    app = sap = SetupCacheGlobal(app, environ, setup_cache=True)
    app = CacheMiddleware(app, {}, data_dir=cache_dir)
    app = RegistryManager(app)
    app = TestApp(app)

    # This one is missing cache middleware and the cache object to miss on purpsoe
    bad_app = ControllerWrap(CacheController)
    bad_app = SetupCacheGlobal(bad_app, environ, setup_cache=False)
    bad_app = RegistryManager(bad_app)
    bad_app = TestApp(bad_app)
    return app, bad_app


cache_dir = os.path.join(data_dir, 'cache')

try:
    shutil.rmtree(cache_dir)
except:
    pass


class TestBadCacheDecorator(TestWSGIController):
    def setUp(self):
        app, bad_app = make_cache_controller()
        self.app = bad_app
        TestWSGIController.setUp(self)
        environ.update(self.environ)
    
    def test_no_cache(self):
        self.assertRaises(Exception, lambda: self.get_response(action='test_default_cache_decorator'))

class TestCacheDecorator(TestWSGIController):
    def setUp(self):
        app, bad_app = make_cache_controller()
        self.app = app
        TestWSGIController.setUp(self)
        environ.update(self.environ)

    def test_default_cache_decorator(self):
        sap.g.counter = 0
        self.get_response(action='test_default_cache_decorator_invalidate')

        response = self.get_response(action='test_default_cache_decorator_invalidate')
        assert 'text/html' in response.headers['content-type']
        assert 'Counter=1' in response

        response = self.get_response(action='test_default_cache_decorator_invalidate')
        assert 'Counter=1' in response
    
    def test_default_cache_decorator(self):
        sap.g.counter = 0
        self.get_response(action='test_invalidate_cache')

        response = self.get_response(action='test_default_cache_decorator')
        assert 'text/html' in response.headers['content-type']
        assert 'Counter=1' in response

        response = self.get_response(action='test_default_cache_decorator')
        assert 'Counter=1' in response
        
        response = self.get_response(action='test_get_cache_decorator', _url='/?param=123')
        assert 'Counter=2' in response
        response = self.get_response(action='test_get_cache_decorator', _url="/?param=123")
        assert 'Counter=2' in response
        
        response = self.get_response(action='test_expire_cache_decorator')
        assert 'Counter=3' in response
        response = self.get_response(action='test_expire_cache_decorator')
        assert 'Counter=3' in response
        time.sleep(2)
        response = self.get_response(action='test_expire_cache_decorator')
        assert 'Counter=4' in response
        
        response = self.get_response(action='test_key_cache_decorator', id=1)
        assert 'Counter=5' in response
        response = self.get_response(action='test_key_cache_decorator', id=2)
        assert 'Counter=6' in response
        response = self.get_response(action='test_key_cache_decorator', id=1)
        assert 'Counter=5' in response
        
        response = self.get_response(action='test_keyslist_cache_decorator', id=1, id2=2)
        assert 'Counter=7' in response
        response = self.get_response(action='test_keyslist_cache_decorator', id=1, id2=2)
        assert 'Counter=7' in response
        
        response = self.get_response(action='test_get_cache_default', _url='/?param=1243')
        assert 'Counter=8' in response
        response = self.get_response(action='test_get_cache_default', _url="/?param=1243")
        assert 'Counter=8' in response
        response = self.get_response(action='test_get_cache_default', _url="/?param=123")
        assert 'Counter=9' in response

        response = self.get_response(action='test_default_cache_decorator_func')
        assert 'text/html' in response.headers['content-type']
        assert 'Counter=10' in response
        response = self.get_response(action='test_default_cache_decorator_func')
        assert 'Counter=10' in response
        
        response = self.get_response(action='test_response_cache_func', use_cache_status=True)
        
        assert 'Counter=10' in response
        
        response = self.get_response(action='test_response_cache_func', use_cache_status=False,
                                     test_args=dict(status=404))
        assert 'Counter=10' in response
        
    
    def test_dbm_cache_decorator(self):
        sap.g.counter = 0
        self.get_response(action="test_invalidate_dbm_cache")
        
        response = self.get_response(action="test_dbm_cache_decorator")
        assert "Counter=1" in response

        response = self.get_response(action="test_dbm_cache_decorator")
        assert "Counter=1" in response
        
        self.get_response(action="test_invalidate_dbm_cache")
        response = self.get_response(action="test_dbm_cache_decorator")
        assert "Counter=2" in response

        sap.g.counter = 0
        response = self.get_response(action="test_expire_dbm_cache_decorator")
        assert "Counter=1" in response
        response = self.get_response(action="test_expire_dbm_cache_decorator")
        assert "Counter=1" in response
        time.sleep(2)
        response = self.get_response(action="test_expire_dbm_cache_decorator")
        assert "Counter=2" in response
        
    def test_cache_key(self):
        from pylons.decorators.cache import beaker_cache, create_cache_key
        
        key = create_cache_key(TestCacheDecorator.test_default_cache_decorator)
        assert key == ('%s.TestCacheDecorator' % self.__module__, 'test_default_cache_decorator')
        
        response = self.get_response(action='test_invalidate_cache')
        response = self.get_response(action='test_default_cache_decorator')
        assert 'Counter=1' in response
        response = self.get_response(action='test_default_cache_decorator')
        assert 'Counter=1' in response
        response = self.get_response(action='test_invalidate_cache')
        response = self.get_response(action='test_default_cache_decorator')
        assert 'Counter=2' in response

    def test_cache_key_dupe(self):
        response = self.get_response(action='test_cache_key_dupe',
                                     _url='/test_cache_key_dupe?id=1')
        time.sleep(0.1)
        response2 = self.get_response(action='test_cache_key_dupe',
                                      _url='/test_cache_key_dupe?id=2&id=1')
        assert str(response) != str(response2)
        
    def test_header_cache(self):
        response = self.get_response(action='test_header_cache')
        assert response.headers['content-type'] == 'application/special'
        assert response.headers['x-powered-by'] == 'pylons'
        assert 'x-dont-include' not in response.headers
        output = response.body

        time.sleep(1)
        response = self.get_response(action='test_header_cache')
        assert response.body == output
        assert response.headers['content-type'] == 'application/special'
        assert response.headers['x-powered-by'] == 'pylons'
        assert 'x-dont-include' not in response.headers
        
    def test_nocache(self):
        import pylons
        sap.g.counter = 0
        pylons.config['cache_enabled'] = 'False'
        response = self.get_response(action='test_default_cache_decorator')
        assert 'Counter=1' in response
        response = self.get_response(action='test_default_cache_decorator')
        assert 'Counter=2' in response
        pylons.config['cache_enabled'] = 'True'

########NEW FILE########
__FILENAME__ = test_decorator_https
from paste.fixture import TestApp
from paste.registry import RegistryManager

from routes.middleware import RoutesMiddleware

from __init__ import TestWSGIController

def make_httpscontroller():
    from pylons import request, url
    from pylons.controllers import WSGIController
    from pylons.decorators.secure import https
    
    class HttpsController(WSGIController):

        @https('/pylons')
        def index(self):
            return 'index page'

        @https(lambda: url(controller='auth', action='login'))
        def login2(self):
            return 'login2 page'

        @https(lambda: request.url)
        def secure(self):
            return 'secure page'

        @https()
        def get(self):
            return 'get page'
    return HttpsController

class TestHttpsDecorator(TestWSGIController):
    def setUp(self):
        from pylons.testutil import ControllerWrap, SetupCacheGlobal
        HttpsController = make_httpscontroller()
        TestWSGIController.setUp(self)
        from routes import Mapper
        map = Mapper()
        map.connect('/:action')
        map.connect('/:action/:id')
        map.connect('/:controller/:action/:id')
        map.connect('/:controller/:action')
        app = ControllerWrap(HttpsController)
        app = SetupCacheGlobal(app, self.environ, setup_cache=False)
        app = RoutesMiddleware(app, map)
        app = RegistryManager(app)
        self.app = TestApp(app)

    def test_https_explicit_path(self):
        self.environ['pylons.routes_dict']['action'] = 'index'

        response = self.app.get('/index', status=302)
        assert response.header_dict.get('location') == \
            'https://localhost/pylons'

        self.environ['wsgi.url_scheme'] = 'https'
        response = self.app.get('/index', status=200)
        assert 'location' not in response.header_dict
        assert 'index page' in response

    def test_https_disallows_post(self):
        self.environ['pylons.routes_dict']['action'] = 'index'
        response = self.app.post('/index', status=405)

    def test_https_callable(self):
        self.environ['pylons.routes_dict']['action'] = 'login2'

        response = self.app.get('/login2', status=302)
        assert response.header_dict.get('location') == \
            'https://localhost/auth/login'

        self.environ['wsgi.url_scheme'] = 'https'
        response = self.app.get('/login2', status=200)
        assert 'location' not in response.header_dict
        assert 'login2 page' in response

    def test_https_callable_current(self):
        self.environ['pylons.routes_dict']['action'] = 'secure'

        response = self.app.get('/secure', status=302)
        assert response.header_dict.get('location') == \
            'https://localhost/secure'

        self.environ['wsgi.url_scheme'] = 'https'
        response = self.app.get('/secure', status=200)
        assert 'location' not in response.header_dict
        assert 'secure page' in response

    def test_https_redirect_to_self(self):
        self.environ['pylons.routes_dict']['action'] = 'get'

        response = self.app.get('/get', status=302)
        assert response.header_dict.get('location') == \
            'https://localhost/get'

        self.environ['wsgi.url_scheme'] = 'https'
        response = self.app.get('/get', status=200)
        assert 'location' not in response.header_dict
        assert 'get page' in response

########NEW FILE########
__FILENAME__ = test_decorator_jsonify
import warnings

from paste.fixture import TestApp
from paste.registry import RegistryManager

from __init__ import TestWSGIController

def make_cache_controller_app():
    from pylons.testutil import ControllerWrap, SetupCacheGlobal
    from pylons.decorators import jsonify
    from pylons.controllers import WSGIController
    
    class CacheController(WSGIController):

        @jsonify
        def test_bad_json(self):
            return ["this is neat"]

        @jsonify
        def test_bad_json2(self):
            return ("this is neat",)
    
        @jsonify
        def test_good_json(self):
            return dict(fred=42)

    environ = {}
    app = ControllerWrap(CacheController)
    app = sap = SetupCacheGlobal(app, environ)
    app = RegistryManager(app)
    app = TestApp(app)
    return app, environ


class TestJsonifyDecorator(TestWSGIController):
    def setUp(self):
        self.app, environ = make_cache_controller_app()
        TestWSGIController.setUp(self)
        environ.update(self.environ)
        warnings.simplefilter('error', Warning)
    
    def tearDown(self):
        warnings.simplefilter('always', Warning)

    def test_bad_json(self):
        for action in 'test_bad_json', 'test_bad_json2':
            try:
                response = self.get_response(action=action)
            except Warning, msg:
                assert 'JSON responses with Array envelopes are' in msg[0]
    
    def test_good_json(self):
        response = self.get_response(action='test_good_json')
        assert '{"fred": 42}' in response
        assert response.header('Content-Type') == 'application/json; charset=utf-8'

########NEW FILE########
__FILENAME__ = test_decorator_validate
# -*- coding: utf-8 -*-
import formencode
from formencode.htmlfill import html_quote
from paste.fixture import TestApp
from paste.registry import RegistryManager

from __init__ import TestWSGIController


def custom_error_formatter(error):
    return '<p><span class="pylons-error">%s</span></p>\n' % html_quote(error)

class NetworkForm(formencode.Schema):
    allow_extra_fields = True
    filter_extra_fields = True
    new_network = formencode.validators.URL(not_empty=True)

class HelloForm(formencode.Schema):
    hello = formencode.ForEach(formencode.validators.Int())

def make_validating_controller():
    from pylons.decorators import validate
    from pylons.controllers import WSGIController
    
    class ValidatingController(WSGIController):
        def new_network(self):
            return """
<html>
  <form action="/dhcp/new_form" method="POST">
    <table>
      <tr>
        <th>Network</th>
        <td>
          <input id="new_network" name="new_network" type="text" value="" />
        </td>
      </tr>
    </table>
    <input name="commit" type="submit" value="Save changes" />
  </form>
</html>
"""

        @validate(schema=NetworkForm, form='new_network')
        def network(self):
            return 'Your network is: %s' % self.form_result.get('new_network')

        def view_hello(self):
            return """
<html>
  <form action="/hello" method="POST">
    <table>
      <tr>
        <th>Hello</th>
        <td>
          <form:iferror name="hello">Bad Hello!&nbsp;</form:iferror>
          <input id="hello" name="hello" type="text" value="" />
          <input id="hello" name="hello" type="text" value="" />
          <input id="hello" name="hello" type="text" value="" />
        </td>
      </tr>
    </table>
    <input name="commit" type="submit" value="Submit" />
  </form>
</html>
"""

        @validate(schema=HelloForm(), post_only=False, form='view_hello')
        def hello(self):
            return str(self.form_result)

        @validate(schema=HelloForm(), post_only=False, form='view_hello',
                  auto_error_formatter=custom_error_formatter)
        def hello_custom(self):
            return str(self.form_result)

        @validate(schema=NetworkForm, form='hello_recurse')
        def hello_recurse(self, environ):
            if environ['REQUEST_METHOD'] == 'GET':
                return self.new_network()
            else:
                return 'Your network is: %s' % self.form_result.get('new_network')
    return ValidatingController


class TestValidateDecorator(TestWSGIController):
    def setUp(self):
        from pylons.testutil import ControllerWrap, SetupCacheGlobal
        ValidatingController = make_validating_controller()
        
        TestWSGIController.setUp(self)
        app = SetupCacheGlobal(ControllerWrap(ValidatingController),
                               self.environ)
        app = RegistryManager(app)
        self.app = TestApp(app)

    def test_network_validated(self):
        response = self.post_response(action='network',
                                      new_network='http://pylonshq.com/')
        assert 'Your network is: http://pylonshq.com/' in response

    def test_network_failed_validation_non_ascii(self):
        response = self.post_response(action='network', new_network='Росси́я')
        assert 'That is not a valid URL' in response
        assert 'Росси́я' in response

    def test_recurse_validated(self):
        response = self.post_response(action='hello_recurse',
                                      new_network='http://pylonshq.com/')
        assert 'Your network is: http://pylonshq.com/' in response

    def test_hello(self):
        self.environ['pylons.routes_dict']['action'] = 'hello'
        response = self.app.post('/hello?hello=1&hello=2&hello=3',
                                 extra_environ=self.environ)
        assert "'hello': [1, 2, 3]" in response
                                      
    def test_hello_failed(self):
        self.environ['pylons.routes_dict']['action'] = 'hello'
        response = self.app.post('/hello?hello=1&hello=2&hello=hi',
                                 extra_environ=self.environ)
        assert 'Bad Hello!&nbsp;' in response
        assert "[None, None, u'Please enter an integer value']" in response

    def test_hello_custom_failed(self):
        self.environ['pylons.routes_dict']['action'] = 'hello_custom'
        response = \
            self.app.post('/hello_custom?hello=1&hello=2&hello=hi',
                          extra_environ=self.environ)
        assert 'Bad Hello!&nbsp;' in response
        assert "[None, None, u'Please enter an integer value']" in response
        assert ("""<p><span class="pylons-error">[None, None, u'Please enter """
                """an integer value']</span></p>""") in response

########NEW FILE########
__FILENAME__ = test_helpers
import warnings
from unittest import TestCase

from paste.fixture import TestApp
from paste.httpexceptions import HTTPMovedPermanently
from paste.registry import RegistryManager

from __init__ import TestWSGIController


def make_helperscontroller():
    import pylons
    from pylons.controllers import WSGIController
    from pylons.controllers.util import etag_cache
    
    class HelpersController(WSGIController):

        def test_etag_cache(self):
            etag_cache('test')
            return "from etag_cache"
    return HelpersController

class TestHelpers(TestWSGIController):
    def __init__(self, *args, **kargs):
        from pylons.testutil import ControllerWrap, SetupCacheGlobal
        HelpersController = make_helperscontroller()
        TestWSGIController.__init__(self, *args, **kargs)
        self.baseenviron = {}
        app = ControllerWrap(HelpersController)
        app = self.sap = SetupCacheGlobal(app, self.baseenviron)
        app = RegistryManager(app)
        self.app = TestApp(app)
        
    def setUp(self):
        TestWSGIController.setUp(self)
        self.baseenviron.update(self.environ)
        warnings.simplefilter('error', DeprecationWarning)

    def tearDown(self):
        warnings.simplefilter('always', DeprecationWarning)

    def test_return_etag_cache(self):
        self.baseenviron['pylons.routes_dict']['action'] = 'test_etag_cache'
        response = self.app.get('/')
        assert '"test"' == response.header('Etag')
        assert 'from etag_cache' in response

########NEW FILE########
__FILENAME__ = test_i18n
# -*- coding: utf-8 -*-
import os
import sys

from paste.fixture import TestApp

from __init__ import test_root

lang_setup = None


def setup_py_trans():
    global lang_setup
    import pylons
    from pylons.i18n.translation import _get_translator
    root = os.path.join(test_root, 'sample_controllers')
    lang_setup = {'pylons.paths': {'root': root}, 'pylons.package': 'sample_controllers'}
    sys.path.append(test_root)
    pylons.translator._push_object(_get_translator(None, pylons_config=lang_setup))

glob_set = []


class TestI18N(object):
    def setUp(self):
        setup_py_trans()

    def test_lazify(self):
        from pylons.i18n.translation import lazify

        def show_str(st):
            return '%s%s' % (st, len(glob_set))
        lazy_show_str = lazify(show_str)
        result1 = lazy_show_str('fred')
        result2 = show_str('fred')
        assert str(result1) == str(result2)
        glob_set.append('1')
        assert str(result1) != str(result2)

    def test_noop(self):
        import pylons
        from pylons.i18n.translation import _, N_, set_lang
        foo = N_('Hello')

        class Bar(object):
            def __init__(self):
                self.local_foo = _(foo)

        assert Bar().local_foo == 'Hello'

        t = set_lang('fr', set_environ=False, pylons_config=lang_setup)
        pylons.translator._push_object(t)
        assert Bar().local_foo == 'Bonjour'
        t = set_lang('es', set_environ=False, pylons_config=lang_setup)
        pylons.translator._push_object(t)
        assert Bar().local_foo == u'¡Hola!'
        assert foo == 'Hello'

########NEW FILE########
__FILENAME__ = test_jsonrpc
# -*- coding: utf-8 -*-
from paste.fixture import TestApp
from paste.registry import RegistryManager

import webob.exc as exc
import json

from __init__ import TestWSGIController

def make_basejsonrpc():
    from pylons.controllers import JSONRPCController, JSONRPCError

    class BaseJSONRPCController(JSONRPCController):

        def __init__(self):
            self._pylons_log_debug = True

        def echo(self, message):
            return message

        def int_arg_check(self, arg):
            if not isinstance(arg, int):
                raise JSONRPCError(1, 'That is not an integer')
            else:
                return 'got an integer'

        def return_garbage(self):
            return JSONRPCController

        def subtract(self, x, y):
            if not isinstance(x, int) and not isinstance(y, int):
                raise JSONRPCError(1, 'That is not an integer')
            else:
                return x - y

        def v2_echo(self, message='Default message'):
            return message

        def v2_int_arg_check(self, arg=99):
            if not isinstance(arg, int):
                raise JSONRPCError(1, 'That is not an integer')
            else:
                return 'got an integer'

        def v2_decrement(self, x, y=1):
            """Like subtract, but decrements by default."""
            if not isinstance(x, int) and not isinstance(y, int):
                raise JSONRPCError(1, 'That is not an integer')
            else:
                return x - y

        def _private(self):
            return 'private method'

    return BaseJSONRPCController


class TestJSONRPCController(TestWSGIController):

    def __init__(self, *args, **kwargs):
        from pylons.testutil import ControllerWrap, SetupCacheGlobal

        BaseJSONRPCController = make_basejsonrpc()
        TestWSGIController.__init__(self, *args, **kwargs)
        self.baseenviron = {}
        self.baseenviron['pylons.routes_dict'] = {}
        app = ControllerWrap(BaseJSONRPCController)
        app = self.sap = SetupCacheGlobal(app, self.baseenviron)
        app = RegistryManager(app)
        self.app = TestApp(app)

    def test_echo(self):
        response = self.jsonreq('echo', args=('hello, world',))
        assert dict(jsonrpc='2.0',
                    id='test',
                    result='hello, world') == response

    def test_int_arg_check(self):
        response = self.jsonreq('int_arg_check', args=('1',))
        assert dict(jsonrpc='2.0',
                    id='test',
                    error={'code': 1,
                           'message': 'That is not an integer'}) == response

    def test_return_garbage(self):
        response = self.jsonreq('return_garbage')
        assert dict(jsonrpc='2.0',
                    id='test',
                    error={'code': -32603,
                           'message': "Internal error"}) == response

    def test_private_method(self):
        response = self.jsonreq('_private')
        assert dict(jsonrpc='2.0',
                    id='test',
                    error={'code': -32601,
                           'message': "Method not found"}) == response

    def test_content_type(self):
        response = self.jsonreq('echo', args=('foo',))
        assert self.response.header('Content-Type') == 'application/json'

    def test_missing_method(self):
        response = self.jsonreq('foo')
        assert dict(jsonrpc='2.0',
                    id='test',
                    error={'code': -32601,
                           'message': "Method not found"}) == response

    def test_no_content_length(self):
        data = json.dumps(dict(jsonrpc='2.0',
                               id='test',
                               method='echo',
                               args=('foo',)))
        self.assertRaises(exc.HTTPLengthRequired,
                          lambda: self.app.post('/', extra_environ=\
                                                    dict(CONTENT_LENGTH='')))

    def test_zero_content_length(self):
        data = json.dumps(dict(jsonrpc='2.0',
                               id='test',
                               method='echo',
                               args=('foo',)))
        self.assertRaises(exc.HTTPLengthRequired,
                          lambda: self.app.post('/', extra_environ=\
                                                    dict(CONTENT_LENGTH='0')))

    def test_positional_params(self):
        response = self.jsonreq('subtract', args=[4, 2])
        assert dict(jsonrpc='2.0',
                    id='test',
                    result=2) == response

    def test_missing_positional_param(self):
        response = self.jsonreq('subtract', args=[1])
        assert dict(jsonrpc='2.0',
                    id='test',
                    error={'code': -32602,
                           'message': "Invalid params"}) == response

    def test_wrong_param_type(self):
        response = self.jsonreq('subtract', args=['1', '2'])
        assert dict(jsonrpc='2.0',
                    id='test',
                    error={'code': 1,
                           'message': "That is not an integer"}) == response

    def test_v2_echo(self):
        response = self.jsonreq('v2_echo', args={'message': 'hello, world'})
        assert dict(jsonrpc='2.0',
                    id='test',
                    result='hello, world') == response

    def test_v2_echo_default(self):
        response = self.jsonreq('v2_echo', args={})
        assert dict(jsonrpc='2.0',
                    id='test',
                    result='Default message') == response

    def test_v2_int_arg_check_valid(self):
        response = self.jsonreq('v2_int_arg_check', args={'arg': 5})
        assert dict(jsonrpc='2.0',
                    id='test',
                    result='got an integer')

    def test_v2_int_arg_check_default_keyword_argument(self):
        response = self.jsonreq('v2_int_arg_check', args={})
        assert dict(jsonrpc='2.0',
                    id='test',
                    result='got an integer')

    def test_v2_int_arg_check(self):
        response = self.jsonreq('v2_int_arg_check', args={'arg': 'abc'})
        assert dict(jsonrpc='2.0',
                    id='test',
                    error={'code': 1,
                           'message': "That is not an integer"}) == response

    def test_v2_decrement(self):
        response = self.jsonreq('v2_decrement', args={'x': 50, 'y': 100})
        assert dict(jsonrpc='2.0',
                    id='test',
                    result=-50) == response

    def test_v2_decrement_default_keywoard_argument(self):
        response = self.jsonreq('v2_decrement', args={'x': 50})
        assert dict(jsonrpc='2.0',
                    id='test',
                    result=49) == response

    def test_v2_decrement_missing_keyword_argument(self):
        response = self.jsonreq('v2_decrement', args={})
        assert dict(jsonrpc='2.0',
                    id='test',
                    error={'code': -32602,
                           'message': "Invalid params"}) == response

########NEW FILE########
__FILENAME__ = test_middleware
# -*- coding: utf-8 -*-
from webtest import TestApp

def simple_app(environ, start_response):
    start_response('200 OK', [('Content-type', 'text/plain')])
    return ['Hello world!']

def simple_exception_app(environ, start_response):
    if environ['PATH_INFO'].startswith('/error/document'):
        start_response('200 OK', [('Content-type', 'text/plain')])
        return ['Made it to the error']
    else:
        start_response('404 Not Found', [('Content-type', 'text/plain')])
        return ['No page found!']

def test_plain_wrap():
    from pylons.middleware import StatusCodeRedirect
    app = TestApp(StatusCodeRedirect(simple_app))
    res = app.get('/')
    assert res.status_int == 200

def test_status_intercept():
    from pylons.middleware import StatusCodeRedirect
    app = TestApp(StatusCodeRedirect(simple_exception_app))
    res = app.get('/', status=404)
    assert 'Made it to the error' in res

def test_original_path():
    from pylons.middleware import StatusCodeRedirect
    app = TestApp(StatusCodeRedirect(simple_exception_app))
    res = app.get('/', status=404)
    if getattr(res, 'environ', None) is not None: # webob<1.2
        assert res.environ['PATH_INFO'] == '/'

def test_retains_response():
    from pylons.middleware import StatusCodeRedirect
    app = TestApp(StatusCodeRedirect(simple_exception_app))
    res = app.get('/', status=404)
    if getattr(res, 'environ', None) is not None: # webob<1.2
        assert 'pylons.original_response' in res.environ
        assert 'No page found!' in res.environ['pylons.original_response'].body

def test_retains_request():
    from pylons.middleware import StatusCodeRedirect
    app = TestApp(StatusCodeRedirect(simple_exception_app))
    res = app.get('/fredrick', status=404)
    if getattr(res, 'environ', None) is not None: # webob<1.2
        assert 'pylons.original_request' in res.environ
        assert '/fredrick' == res.environ['pylons.original_request'].path_info
    

########NEW FILE########
__FILENAME__ = test_templating
import os
import re
import sys

from beaker.cache import CacheManager
from beaker.middleware import SessionMiddleware, CacheMiddleware
from mako.lookup import TemplateLookup
from nose.tools import raises
from paste.fixture import TestApp
from paste.registry import RegistryManager
from paste.deploy.converters import asbool
from routes import Mapper
from routes.middleware import RoutesMiddleware

from nose.tools import raises

from __init__ import test_root


def make_app(global_conf, full_stack=True, static_files=True, include_cache_middleware=False, attribsafe=False, **app_conf):
    import pylons
    import pylons.configuration as configuration
    from pylons import url
    from pylons.decorators import jsonify
    from pylons.middleware import ErrorHandler, StatusCodeRedirect
    from pylons.error import handle_mako_error
    from pylons.wsgiapp import PylonsApp

    root = os.path.dirname(os.path.abspath(__file__))
    paths = dict(root=os.path.join(test_root, 'sample_controllers'), controllers=os.path.join(test_root, 'sample_controllers', 'controllers'),
                 templates=os.path.join(test_root, 'sample_controllers', 'templates'))
    sys.path.append(test_root)

    config = configuration.PylonsConfig()
    config.init_app(global_conf, app_conf, package='sample_controllers', paths=paths)
    map = Mapper(directory=config['pylons.paths']['controllers'])
    map.connect('/{controller}/{action}')
    config['routes.map'] = map
    
    class AppGlobals(object): pass
    
    config['pylons.app_globals'] = AppGlobals()
    
    config['pylons.app_globals'].mako_lookup = TemplateLookup(
        directories=paths['templates'], imports=['from markupsafe import escape']
    )
        
    if attribsafe:
        config['pylons.strict_tmpl_context'] = False
    
    app = PylonsApp(config=config)
    app = RoutesMiddleware(app, config['routes.map'], singleton=False)
    if include_cache_middleware:
        app = CacheMiddleware(app, config)
    app = SessionMiddleware(app, config)

    if asbool(full_stack):
        app = ErrorHandler(app, global_conf, **config['pylons.errorware'])
        if asbool(config['debug']):
            app = StatusCodeRedirect(app)
        else:
            app = StatusCodeRedirect(app, [401, 403, 404, 500])
    app = RegistryManager(app)

    app.config = config
    return app

class TestTemplatingApp(object):
    def setUp(self):
        self.app = TestApp(make_app({'cache_dir': os.path.join(os.path.dirname(__file__), 'cache')}, include_cache_middleware=True))
    
    def test_testvars(self):
        resp = self.app.get('/hello/intro_template')
        assert 'Hi there 6' in resp
    
    def test_template_cache(self):
        resp = self.app.get('/hello/time_template')
        resp2 = self.app.get('/hello/time_template')
        assert resp.body == resp2.body


########NEW FILE########
__FILENAME__ = test_xmlrpc
# -*- coding: utf-8 -*-
from paste.fixture import TestApp
from paste.registry import RegistryManager

import webob.exc as exc
import xmlrpclib

from __init__ import TestWSGIController

def make_basexmlrpc():
    from pylons.controllers import XMLRPCController
    class BaseXMLRPCController(XMLRPCController):
        def __init__(self):
            self._pylons_log_debug = True
    
        foo = 'bar'
    
        def userstatus(self):
            return 'basic string'
        userstatus.signature = [ ['string'] ]
    
        def docs(self):
            "This method has a docstring"
            return dict(mess='a little somethin', a=1, b=[1,2,3], c=('all','the'))
        docs.signature = [ ['struct'] ]
    
        def uni(self):
            "This method has a docstring"
            return dict(mess=u'A unicode string, oh boy')
        uni.signature = [ ['struct'] ]
    
        def intargcheck(self, arg):
            if not isinstance(arg, int):
                return xmlrpclib.Fault(0, 'Integer required')
            else:
                return "received int"
        intargcheck.signature = [ ['string', 'int'] ]
    
        def nosig(self):
            return 'not much'
    
        def structured_methodname(self, arg):
            "This method has a docstring"
            return 'Transform okay'
        structured_methodname.signature = [ ['string', 'string'] ]
    
        def longdoc(self):
            """This function
            has multiple lines
            in it"""
            return "hi all"
    
        def _private(self):
            return 'private method'
    return BaseXMLRPCController
    
class TestXMLRPCController(TestWSGIController):
    def __init__(self, *args, **kargs):
        from pylons.testutil import ControllerWrap, SetupCacheGlobal
        BaseXMLRPCController = make_basexmlrpc()
        
        TestWSGIController.__init__(self, *args, **kargs)
        self.baseenviron = {}
        self.baseenviron['pylons.routes_dict'] = {}
        app = ControllerWrap(BaseXMLRPCController)
        app = self.sap = SetupCacheGlobal(app, self.baseenviron)
        app = RegistryManager(app)
        self.app = TestApp(app)
    
    def test_index(self):
        response = self.xmlreq('userstatus')
        assert response == 'basic string'
    
    def test_structure(self):
        response = self.xmlreq('docs')
        assert dict(mess='a little somethin', a=1, b=[1,2,3], c=['all','the']) == response
    
    def test_methodhelp(self):
        response = self.xmlreq('system.methodHelp', ('docs',))
        assert "This method has a docstring" in response
    
    def test_methodhelp_with_structured_methodname(self):
        response = self.xmlreq('system.methodHelp', ('structured.methodname',))
        assert "This method has a docstring" in response
    
    def test_methodsignature(self):
        response = self.xmlreq('system.methodSignature', ('docs',))
        assert [['struct']] == response
    
    def test_methodsignature_with_structured_methodname(self):
        response = self.xmlreq('system.methodSignature', ('structured.methodname',))
        assert [['string', 'string']] == response
    
    def test_listmethods(self):
        response = self.xmlreq('system.listMethods')
        assert response == ['docs', 'intargcheck', 'longdoc', 'nosig', 'structured.methodname', 'system.listMethods', 'system.methodHelp', 'system.methodSignature', 'uni', 'userstatus']    
    
    def test_unicode(self):
        response = self.xmlreq('uni')
        assert 'A unicode string' in response['mess']
    
    def test_unicode_method(self):
        data = xmlrpclib.dumps((), methodname=u'ОбсуждениеКомпаний')
        self.response = response = self.app.post('/', params=data, extra_environ=dict(CONTENT_TYPE='text/xml'))
    
    def test_no_length(self):
        data = xmlrpclib.dumps((), methodname=u'ОбсуждениеКомпаний')
        self.assertRaises(exc.HTTPLengthRequired, lambda: self.app.post('/', extra_environ=dict(CONTENT_LENGTH='')))
    
    def test_too_big(self):
        data = xmlrpclib.dumps((), methodname=u'ОбсуждениеКомпаний')
        self.assertRaises(exc.HTTPRequestEntityTooLarge, lambda: self.app.post('/', extra_environ=dict(CONTENT_LENGTH='4194314')))
    
    def test_badargs(self):
        self.assertRaises(xmlrpclib.Fault, self.xmlreq, 'system.methodHelp')
    
    def test_badarity(self):
        self.assertRaises(xmlrpclib.Fault, self.xmlreq, 'system.methodHelp')
    
    # Unsure whether this is actually picked up by xmlrpclib, but what the hey
    def test_bad_paramval(self):
        self.assertRaises(xmlrpclib.Fault, self.xmlreq, 'intargcheck', (12.5,))
    
    def test_missingmethod(self):
        self.assertRaises(xmlrpclib.Fault, self.xmlreq, 'doesntexist')
    
    def test_nosignature(self):
        response = self.xmlreq('system.methodSignature', ('nosig',))
        assert response == ''
    
    def test_nosignature_unicode(self):
        self.assertRaises(xmlrpclib.Fault, self.xmlreq, 'system.methodSignature',
                          (u'ОбсуждениеКомпаний',))
    
    def test_nodocs(self):
        response = self.xmlreq('system.methodHelp', ('nosig',))
        assert response == ''
    
    def test_nodocs_unicode(self):
        self.assertRaises(xmlrpclib.Fault, self.xmlreq, 'system.methodHelp',
                          (u'ОбсуждениеКомпаний',))
    
    def test_multilinedoc(self):
        response = self.xmlreq('system.methodHelp', ('longdoc',))
        assert 'This function\nhas multiple lines\nin it' in response
    
    def test_contenttype(self):
        response = self.xmlreq('system.methodHelp', ('longdoc',))
        assert self.response.header('Content-Type') == 'text/xml'
    
    def test_start_response(self):
        self.assertRaises(xmlrpclib.Fault, self.xmlreq, 'start_response')
    
    def test_private_func(self):
        self.assertRaises(xmlrpclib.Fault, self.xmlreq, '_private')
    
    def test_var(self):
        self.assertRaises(xmlrpclib.Fault, self.xmlreq, 'foo')
    


########NEW FILE########
__FILENAME__ = app_globals
"""The application's Globals object"""
from pylons import config

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
        self.message = 'Hello'
        self.counter = 0

########NEW FILE########
__FILENAME__ = base_with_xmlrpc
from pylons import tmpl_context as c, app_globals, cache, request, session
from pylons.controllers import WSGIController, XMLRPCController
from pylons.controllers.util import abort, etag_cache, redirect
from pylons.decorators import jsonify, validate
from pylons.templating import render_mako as render
from pylons.i18n import N_, _, ungettext
import projectname.model as model
import projectname.lib.helpers as h

class BaseController(WSGIController):
    def __call__(self, environ, start_response):
        # Insert any code to be run per request here. The Routes match
        # is under environ['pylons.routes_dict'] should you want to check
        # the action or route vars here
        return WSGIController.__call__(self, environ, start_response)

# Include the '_' function in the public names
__all__ = [__name for __name in locals().keys() if not __name.startswith('_') \
           or __name == '_']

########NEW FILE########
__FILENAME__ = cache_controller
from pylons import app_globals
from pylons.decorators.cache import beaker_cache
from projectname.lib.base import BaseController

class CacheController(BaseController):

    @beaker_cache(key=None)
    def test_default_cache_decorator(self):
        app_globals.counter += 1
        return 'Counter=%s' % app_globals.counter

    @beaker_cache(key="param", query_args=True)
    def test_get_cache_decorator(self):
        app_globals.counter += 1
        return 'Counter=%s' % app_globals.counter

    @beaker_cache(expire=4)
    def test_expire_cache_decorator(self):
        app_globals.counter += 1
        return 'Counter=%s' % app_globals.counter

    @beaker_cache(key="id")
    def test_key_cache_decorator(self, id):
        app_globals.counter += 1
        return 'Counter=%s, id=%s' % (app_globals.counter, id)

    @beaker_cache(key=["id", "id2"])
    def test_keyslist_cache_decorator(self, id, id2="123"):
        app_globals.counter += 1
        return 'Counter=%s, id=%s' % (app_globals.counter, id)

########NEW FILE########
__FILENAME__ = controller_sample
import datetime

from projectname.lib.base import *
import projectname.lib.helpers as h
from pylons import request, response, session, url
from pylons import tmpl_context as c
from pylons import app_globals
from pylons.decorators import rest
from pylons.i18n import _, get_lang, set_lang, LanguageError
from pylons.templating import render_mako, render_genshi, render_jinja2
from pylons.controllers.util import abort, redirect

class SampleController(BaseController):
    def index(self):
        return 'basic index page'
    
    def session_increment(self):
        session.setdefault('counter', -1)
        session['counter'] += 1
        session.save()
        return 'session incrementer'
    
    def globalup(self):
        return app_globals.message
    
    def global_store(self, id=None):
        if id:
            app_globals.counter += int(id)
        return str(app_globals.counter)
    
    def myself(self):
        return request.url
    
    def myparams(self):
        return str(request.params)
    
    def testdefault(self):
        c.test = "This is in c var"
        return render_genshi('testgenshi.html')
        
    def test_template_caching(self):
        return render_mako('/test_mako.html', cache_expire='never')

    @rest.dispatch_on(GET='test_only_get')
    @rest.restrict('POST')
    def test_only_post(self):
        return 'It was a post!'

    @rest.restrict('GET')
    def test_only_get(self):
        return 'It was a get!'

    @rest.restrict('POST')
    @rest.dispatch_on(POST='test_only_post')
    def impossible(self):
        return 'This should never be shown'

    def testjinja2(self):
        c.test = "This is in c var"
        c.now = datetime.datetime.now
        return render_jinja2('testjinja2.html')

    def set_lang(self):
        return self._set_lang(_)

    def set_lang_pylonscontext(self, pylons):
        return self._set_lang(lambda *args: pylons.translator.ugettext(*args))

    def _set_lang(self, gettext):
        lang = request.GET['lang']
        try:
            set_lang(lang)
        except (LanguageError, IOError), e:
            resp_unicode = gettext('Could not set language to "%(lang)s"') % {'lang': lang}
        else:
            session['lang'] = lang
            session.save()
            resp_unicode = gettext('Set language to "%(lang)s"') % {'lang': lang}
        return resp_unicode

    def i18n_index(self):
        locale_list = request.languages
        set_lang(request.languages)
        return unicode(_('basic index page'))

    def no_lang(self):
        set_lang(None)
        response.write(_('No language'))
        set_lang([])
        response.write(_('No languages'))
        return ''

########NEW FILE########
__FILENAME__ = controller_sqlatest
import datetime

from projectname.lib.base import *
try:
    import sqlalchemy as sa
    from projectname.model.meta import Session, Base
    from projectname.model import Foo
    SQLAtesting = True
except:
    SQLAtesting = False
import projectname.lib.helpers as h
from pylons import request, response, session
from pylons import tmpl_context as c
from pylons import app_globals
from pylons.decorators import rest
from pylons.i18n import _, get_lang, set_lang, LanguageError
from pylons.templating import render_mako, render_genshi, render_jinja2
from pylons.controllers.util import abort, redirect

class SampleController(BaseController):
    def index(self):
        return 'basic index page'
    
    def testsqlalchemy(self):
        if SQLAtesting:
            c.foos = Session.query(Foo).all()
            return render_mako('test_sqlalchemy.html')
        pass
    
    def set_lang(self):
        return self._set_lang(_)
    
    def set_lang_pylonscontext(self, pylons):
        return self._set_lang(lambda *args: pylons.translator.ugettext(*args))
    
    def _set_lang(self, gettext):
        lang = request.GET['lang']
        try:
            set_lang(lang)
        except (LanguageError, IOError), e:
            resp_unicode = gettext('Could not set language to "%(lang)s"') % {'lang': lang}
        else:
            session['lang'] = lang
            session.save()
            resp_unicode = gettext('Set language to "%(lang)s"') % {'lang': lang}
        return resp_unicode
    
    def i18n_index(self):
        locale_list = request.languages
        set_lang(request.languages)
        return unicode(_('basic index page'))
    
    def no_lang(self):
        set_lang(None)
        response.write(_('No language'))
        set_lang([])
        response.write(_('No languages'))
        return ''
        

########NEW FILE########
__FILENAME__ = controller_xmlrpc
from projectname.lib.base import *
from pylons.controllers import XMLRPCController

class XmlrpcController(XMLRPCController):
    def userstatus(self):
        return 'basic string'
    userstatus.signature = [ ['string'] ]
    
    def docs(self):
        "This method has a docstring"
        return dict(mess='a little somethin', a=1, b=[1,2,3], c=('all','the'))
    docs.signature = [ ['struct'] ]

    def uni(self):
        "This method has a docstring"
        return dict(mess=u'A unicode string, oh boy')
    docs.signature = [ ['struct'] ]
    
########NEW FILE########
__FILENAME__ = environment_def_engine
"""Pylons environment configuration"""
import os


from mako.lookup import TemplateLookup
from genshi.template import TemplateLoader
from jinja2 import ChoiceLoader, Environment, FileSystemLoader
from pylons.configuration import PylonsConfig
from pylons.error import handle_mako_error

import projectname.lib.app_globals as app_globals
import projectname.lib.helpers
from projectname.config.routing import make_map

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
    config.init_app(global_conf, app_conf, package='projectname', paths=paths)

    config['routes.map'] = make_map(config)
    config['pylons.app_globals'] = app_globals.Globals(config)
    config['pylons.h'] = projectname.lib.helpers
    
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

    # Create the Genshi TemplateLoader
    config['pylons.app_globals'].genshi_loader = TemplateLoader(
        paths['templates'], auto_reload=True)

    # Create the Jinja2 Environment
    config['pylons.app_globals'].jinja2_env = Environment(loader=ChoiceLoader(
            [FileSystemLoader(path) for path in paths['templates']]))

    # CONFIGURATION OPTIONS HERE (note: all config options will override
    # any Pylons config options)
    
    return config

########NEW FILE########
__FILENAME__ = environment_def_sqlamodel
"""Pylons environment configuration"""
import os


from mako.lookup import TemplateLookup
from genshi.template import TemplateLoader
from jinja2 import ChoiceLoader, Environment, FileSystemLoader
from pylons.configuration import PylonsConfig
from pylons.error import handle_mako_error
from sqlalchemy import engine_from_config
 
import projectname.lib.app_globals as app_globals
import projectname.lib.helpers
from projectname.config.routing import make_map
from projectname.model import init_model

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
    config.init_app(global_conf, app_conf, package='projectname', paths=paths)

    config['routes.map'] = make_map(config)
    config['pylons.app_globals'] = app_globals.Globals(config)
    config['pylons.h'] = projectname.lib.helpers
    
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

    # Create the Genshi TemplateLoader
    config['pylons.app_globals'].genshi_loader = TemplateLoader(
        paths['templates'], auto_reload=True)

    # Create the Jinja2 Environment
    config['pylons.app_globals'].jinja2_env = Environment(loader=ChoiceLoader(
            [FileSystemLoader(path) for path in paths['templates']]))

    # CONFIGURATION OPTIONS HERE (note: all config options will override
    # any Pylons config options)
    
    engine = engine_from_config(config, 'sqlalchemy.')
    init_model(engine)

    return config

########NEW FILE########
__FILENAME__ = functional_controller_cache_decorator
import time

from projectname.tests import *

class TestCacheController(TestController):
    
    def test_default_cache_decorator(self):
        response = self.app.get(url(controller='cache', action='test_default_cache_decorator'))
        assert 'Counter=1' in response

        response = self.app.get(url(controller='cache', action='test_default_cache_decorator'))
        assert 'Counter=1' in response
        
        response = self.app.get(url(controller='cache', action='test_get_cache_decorator', param="123"))
        assert 'Counter=2' in response
        response = self.app.get(url(controller='cache', action='test_get_cache_decorator', param="123"))
        assert 'Counter=2' in response
        
        response = self.app.get(url(controller='cache', action='test_expire_cache_decorator'))
        assert 'Counter=3' in response
        response = self.app.get(url(controller='cache', action='test_expire_cache_decorator'))
        assert 'Counter=3' in response
        time.sleep(8)
        response = self.app.get(url(controller='cache', action='test_expire_cache_decorator'))
        assert 'Counter=4' in response
        
        response = self.app.get(url(controller='cache', action='test_key_cache_decorator', id=1))
        assert 'Counter=5' in response
        response = self.app.get(url(controller='cache', action='test_key_cache_decorator', id=2))
        assert 'Counter=6' in response
        response = self.app.get(url(controller='cache', action='test_key_cache_decorator', id=1))
        assert 'Counter=5' in response
        
        response = self.app.get(url(controller='cache', action='test_keyslist_cache_decorator', id=1, id2=2))
        assert 'Counter=7' in response
        response = self.app.get(url(controller='cache', action='test_keyslist_cache_decorator', id=1, id2=2))
        assert 'Counter=7' in response
       

########NEW FILE########
__FILENAME__ = functional_controller_xmlrpc
from projectname.tests import *
from xmlrpclib import loads, dumps

class TestXmlrpcController(TestController):
    xmlurl = None
    
    def xmlreq(self, method, args=None):
        if args is None:
            args = ()
        ee = dict(CONTENT_TYPE='text/xml')
        data = dumps(args, methodname=method)
        response = self.app.post(self.xmlurl, params = data, extra_environ=ee)
        return loads(response.body)[0][0]
    
    def setUp(self):
        self.xmlurl = url(controller='xmlrpc', action='index')
    
    def test_index(self):
        response = self.xmlreq('userstatus')
        assert response == 'basic string'
    
    def test_structure(self):
        response = self.xmlreq('docs')
        assert dict(mess='a little somethin', a=1, b=[1,2,3], c=['all','the']) == response
        
    def test_methodhelp(self):
        response = self.xmlreq('system.methodHelp', ('docs',))
        assert "This method has a docstring" in response
    
    def test_methodsignature(self):
        response = self.xmlreq('system.methodSignature', ('docs',))
        assert [['struct']] == response
    
    def test_listmethods(self):
        response = self.xmlreq('system.listMethods')
        assert response == ['docs', 'system.listMethods', 'system.methodHelp', 'system.methodSignature', 'uni', 'userstatus']
    
    def test_unicode(self):
        response = self.xmlreq('uni')
        assert 'A unicode string' in response['mess']
########NEW FILE########
__FILENAME__ = functional_sample_controller_i18n
from projectname.tests import *

class TestSampleController(TestController):
    def test_set_lang(self):
        self._test_set_lang('set_lang')

    def test_set_lang_pylonscontext(self):
        self._test_set_lang('set_lang_pylonscontext')

    def _test_set_lang(self, action):
        response = self.app.get(url(controller='sample', action=action, lang='ja'))
        assert u'\u8a00\u8a9e\u8a2d\u5b9a\u3092\u300cja\u300d\u306b\u5909\u66f4\u3057\u307e\u3057\u305f'.encode('utf-8') in response
        response = self.app.get(url(controller='sample', action=action, lang='fr'))
        assert 'Could not set language to "fr"' in response

    def test_detect_lang(self):
        response = self.app.get(url(controller='sample', action='i18n_index'), headers={
                'Accept-Language':'fr;q=0.6, en;q=0.1, ja;q=0.3'})
        # expect japanese fallback for nonexistent french.
        assert u'\u6839\u672c\u30a4\u30f3\u30c7\u30af\u30b9\u30da\u30fc\u30b8'.encode('utf-8') in response

    def test_no_lang(self):
        response = self.app.get(url(controller='sample', action='no_lang'))
        assert 'No language' in response
        assert 'No languages' in response

########NEW FILE########
__FILENAME__ = functional_sample_controller_jinja2
from projectname.tests import *

class TestJinja2Controller(TestController):
    def test_jinja2(self):
        response = self.app.get(url(controller='sample', action='testjinja2'))
        assert 'Hello from Jinja2' in response
        assert 'This is in c var' in response

########NEW FILE########
__FILENAME__ = functional_sample_controller_mako
from projectname.tests import *

class TestMakoController(TestController):
    def test_mako(self):
        response = self.app.get(url(controller='sample', action='testmako'))
        assert 'Hello, 5+5 is 10' in response

########NEW FILE########
__FILENAME__ = functional_sample_controller_sample1
import pylons
from projectname.tests import *

class TestSampleController(TestController):
    def test_conf_with_app_globals(self):
        assert 'pylons.app_globals' in pylons.config
        assert hasattr(pylons.app_globals, 'cache')
    
    def test_root_index(self):
        response = self.app.get('/')
        assert 'Welcome' in response
        # Test response...
    
    def test_index(self):
        response = self.app.get(url(controller='sample', action='index'))
        assert 'basic index page' in response
    
    def test_session(self):
        response = self.app.get(url(controller='sample', action='session_increment'))
        assert response.session.has_key('counter')
        assert response.session['counter'] == 0
        
        response = self.app.get(url(controller='sample', action='session_increment'))
        assert response.session['counter'] == 1
        assert 'session incrementer' in response
    
    def test_global(self):
        response = self.app.get(url(controller='sample', action='globalup'))
        assert 'Hello' in response
    
    def test_global_persistence(self):
        response = self.app.get(url(controller='sample', action='global_store'))
        assert '0' in response
        
        response = self.app.get(url(controller='sample', action='global_store', id=2))
        assert '2' in response
        
        response = self.app.get(url(controller='sample', action='global_store'))
        assert '2' in response
        
        response = self.app.get(url(controller='sample', action='global_store', id=3))
        assert '5' in response
        
        response = self.app.get(url(controller='sample', action='global_store'))
        assert '5' in response
    
    def test_helper_urlfor(self):
        response = self.app.get(url(controller='sample', action='myself'))
        assert 'sample/myself' in response
    
    def test_params(self):
        response = self.app.get(url(controller='sample', action='myparams', extra='something', data=4))
        assert 'extra' in response
        assert 'something' in response
        assert 'data' in response

########NEW FILE########
__FILENAME__ = functional_sample_controller_sample2
from projectname.tests import *

class TestSample2Controller(TestController):
    def test_session(self):
        response = self.app.get(url(controller='sample', action='session_increment'))
        assert response.session.has_key('counter')
        assert response.session['counter'] == 0
        
        response = self.app.get(url(controller='sample', action='session_increment'))
        assert response.session['counter'] == 1
        assert 'session incrementer' in response
    
    def test_genshi_default(self):
        self._test_genshi_default('testdefault')
    
    def _test_genshi_default(self, action):
        response = self.app.get(url(controller='sample', action=action))
        assert 'Hello from Genshi' in response
        assert 'This is in c var' in response

########NEW FILE########
__FILENAME__ = functional_sample_controller_sample3
from projectname.tests import *

class TestSample2Controller(TestController):
    def test_session(self):
        response = self.app.get(url(controller='sample', action='session_increment'))
        assert response.session.has_key('counter')
        assert response.session['counter'] == 0
        
        response = self.app.get(url(controller='sample', action='session_increment'))
        assert response.session['counter'] == 1
        assert 'session incrementer' in response
        
    def test_default(self):
        response = self.app.get(url(controller='sample', action='test_template_caching'))
        assert 'Hi everyone!' in response
    
########NEW FILE########
__FILENAME__ = functional_sample_controller_sample4
from projectname.tests import *

class TestSample2Controller(TestController):
    def test_get(self):
        response = self.app.get(url(controller='sample', action='test_only_get'))
        assert 'It was a get' in response
    
    def test_redir_get(self):
        response = self.app.get(url(controller='sample', action='test_only_post'))
        assert 'It was a get' in response
        
    def test_post(self):
        response = self.app.post(url(controller='sample', action='test_only_post'),
            params={'id':4})
        assert 'It was a post' in response

    def test_head(self):
        response = self.app._gen_request('HEAD', url(controller='sample', action='index'))
        assert '' == response.body

########NEW FILE########
__FILENAME__ = functional_sample_controller_sqlatesting
from projectname.tests import *
try:
    from sqlalchemy.exceptions import IntegrityError
except ImportError:
    from sqlalchemy.exc import IntegrityError
    
from projectname.model.meta import Session, Base
from projectname.model import Foo

class TestSQLAlchemyController(TestController):
    def setUp(self):
        Base.metadata.create_all(bind=Session.bind)
        f = Foo(id = 1, bar = u"Wabbit")
        Session.add(f)
        Session.commit()
        assert f.bar == u"Wabbit"
    
    def tearDown(self):
        Base.metadata.drop_all(bind=Session.bind)

    def test_sqlalchemy(self):
        response = self.app.get(url(controller='sample', action='testsqlalchemy'))
        assert 'foos = [Foo:1]' in response

    # def test_exception(self):
    #     me = Foo(id=3, bar='giuseppe')
    #     me_again = Foo(id=3, bar='giuseppe')
    #     self.assertRaises(IntegrityError, Session.commit)
    #     Session.rollback()

########NEW FILE########
__FILENAME__ = helpers_sample
"""Helper functions

Consists of functions to typically be used within templates, but also
available to Controllers. This module is available to both as 'h'.
"""

########NEW FILE########
__FILENAME__ = middleware_mako
"""Pylons middleware initialization"""
from beaker.middleware import SessionMiddleware
from paste.cascade import Cascade
from paste.registry import RegistryManager
from paste.urlparser import StaticURLParser
from paste.deploy.converters import asbool
from pylons.middleware import ErrorHandler, StatusCodeRedirect
from pylons.wsgiapp import PylonsApp
from routes.middleware import RoutesMiddleware

from projectname.config.environment import load_environment

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
    app = RoutesMiddleware(app, config['routes.map'], singleton=False)
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
__FILENAME__ = rest_routing
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
    map.explicit = False
    
    # The ErrorController route (handles 404/500 error pages); it should
    # likely stay at the top, ensuring it can always be resolved
    map.connect('/error/{action}', controller='error')
    map.connect('/error/{action}/{id}', controller='error')

    # CUSTOM ROUTES HERE
    map.resource('restsample', 'restsamples')
    map.resource('restsample', 'restsamples', controller='mysubdir/restsamples', 
        path_prefix='/mysubdir', name_prefix='mysubdir_')

    map.connect('/{controller}/{action}')
    map.connect('/{controller}/{action}/{id}')

    return map

########NEW FILE########
__FILENAME__ = test_make_project
"""Tests against full Pylons projects created from scratch"""
import os
import sys
import shutil
import re

import pkg_resources
from nose import SkipTest
from paste.fixture import TestFileEnvironment

if os.environ.get('SKIP_INTEGRATED', 'False') != '0':
    raise SkipTest()

import pylons
import pylons.test

try:
    import sqlalchemy as sa
    SQLAtesting = True
except ImportError:
    SQLAtesting = False
# SQLAtesting = False

is_jython = sys.platform.startswith('java')

TEST_OUTPUT_DIRNAME = 'output'

for spec in ['PasteScript', 'Paste', 'PasteDeploy', 'pylons']:
    pkg_resources.require(spec)

template_path = os.path.join(
    os.path.dirname(__file__), 'filestotest').replace('\\','/')

test_environ = os.environ.copy()
test_environ['PASTE_TESTING'] = 'true'

testenv = TestFileEnvironment(
    os.path.join(os.path.dirname(__file__), TEST_OUTPUT_DIRNAME).replace('\\','/'),
    template_path=template_path,
    environ=test_environ)

projenv = None

def _get_script_name(script):
    if sys.platform == 'win32' and not script.lower().endswith('.exe'):
        script += '.exe'
    return script

def svn_repos_setup():
    res = testenv.run(_get_script_name('svnadmin'), 'create', 'REPOS',
                      printresult=False)
    path = testenv.base_path.replace('\\','/').replace(' ','%20')
    base = 'file://'
    if ':' in path:
        base = 'file:///'
    testenv.svn_url = base + path + '/REPOS'
    assert 'REPOS' in res.files_created
    testenv.ignore_paths.append('REPOS')

def paster_create(template_engine='mako', overwrite=False, sqlatesting=False):
    global projenv
    paster_args = ['create', '--verbose', '--no-interactive']
    if overwrite:
        paster_args.append('-f')
    paster_args.extend(['--template=pylons',
                        'ProjectName',
                        'version=0.1',
                        'sqlalchemy=%s' % sqlatesting,
                        'zip_safe=False',
                        'template_engine=%s' % template_engine])
    res = testenv.run(_get_script_name('paster'), *paster_args)
    expect_fn = ['projectname', 'development.ini', 'setup.cfg', 'README.txt',
                 'setup.py']
    for fn in expect_fn:
        fn = os.path.join('ProjectName', fn)
        if not overwrite:
            assert fn in res.files_created.keys()
        assert fn in res.stdout
    
    if not overwrite:
        setup = res.files_created[os.path.join('ProjectName','setup.py')]
        setup.mustcontain('0.1')
        setup.mustcontain('projectname.config.middleware:make_app')
        setup.mustcontain('main = pylons.util:PylonsInstaller')
        setup.mustcontain("include_package_data=True")
        assert '0.1' in setup
    testenv.run(_get_script_name(sys.executable)+' setup.py egg_info',
                cwd=os.path.join(testenv.cwd, 'ProjectName').replace('\\','/'),
                expect_stderr=True)
    #testenv.run(_get_script_name('svn'), 'commit', '-m', 'Created project', 'ProjectName')
    # A new environment with a new
    projenv = TestFileEnvironment(
        os.path.join(testenv.base_path, 'ProjectName').replace('\\','/'),
        start_clear=False,
        template_path=template_path,
        environ=test_environ)
    projenv.environ['PYTHONPATH'] = (
        projenv.environ.get('PYTHONPATH', '') + ':'
        + projenv.base_path)
    

def make_controller():
    res = projenv.run(_get_script_name('paster')+' controller sample')
    assert os.path.join('projectname','controllers','sample.py') in res.files_created
    assert os.path.join('projectname','tests','functional','test_sample.py') in res.files_created
    #res = projenv.run(_get_script_name('svn')+' status')
    # Make sure all files are added to the repository:
    assert '?' not in res.stdout

def make_controller_subdirectory():
    res = projenv.run(_get_script_name('paster')+' controller mysubdir/sample')
    assert os.path.join('projectname','controllers', 'mysubdir', 'sample.py') in res.files_created
    assert os.path.join('projectname','tests','functional','test_mysubdir_sample.py') in res.files_created
    #res = projenv.run(_get_script_name('svn')+' status')
    # Make sure all files are added to the repository:
    assert '?' not in res.stdout

def make_restcontroller():
    res = projenv.run(_get_script_name('paster')+' restcontroller restsample restsamples')
    assert os.path.join('projectname','controllers','restsamples.py') in res.files_created
    assert os.path.join('projectname','tests','functional','test_restsamples.py') in res.files_created
    #res = projenv.run(_get_script_name('svn')+' status')
    # Make sure all files are added to the repository:
    assert '?' not in res.stdout

def make_restcontroller_subdirectory():
    res = projenv.run(_get_script_name('paster')+' restcontroller mysubdir/restsample mysubdir/restsamples')
    assert os.path.join('projectname','controllers','mysubdir', 'restsamples.py') in res.files_created
    assert os.path.join('projectname','tests','functional','test_mysubdir_restsamples.py') in res.files_created
    #res = projenv.run(_get_script_name('svn')+' status')
    # Make sure all files are added to the repository:
    assert '?' not in res.stdout


def _do_proj_test(copydict, emptyfiles=None, match_routes_output=None):
    """Given a dict of files, where the key is a filename in filestotest, the value is
    the destination in the new projects dir. emptyfiles is a list of files that should
    be created and empty."""
    if pylons.test.pylonsapp:
        pylons.test.pylonsapp = None
    
    if not emptyfiles:
        emptyfiles = []
    for original, newfile in copydict.iteritems():
        projenv.writefile(newfile, frompath=original)
    for fi in emptyfiles:
        projenv.writefile(fi)
    
    # here_dir = os.getcwd()
    # test_dir = os.path.join(testenv.cwd, 'ProjectName').replace('\\','/')
    # os.chdir(test_dir)
    # sys.path.append(test_dir)
    # nose.run(argv=['nosetests', '-d', test_dir])
    # 
    # sys.path.pop(-1)
    # os.chdir(here_dir)
    
    res = projenv.run(_get_script_name('nosetests')+' -d',
                      expect_stderr=True,
                      cwd=os.path.join(testenv.cwd, 'ProjectName').replace('\\','/'))
    if match_routes_output:
        res = projenv.run(_get_script_name('paster')+' routes',
                          expect_stderr=False,
                          cwd=os.path.join(testenv.cwd, 'ProjectName').replace('\\','/'))
        for pattern in match_routes_output:
            assert re.compile(pattern).search(res.stdout)
        

def do_nosetests():
    _do_proj_test({'development.ini':'development.ini'})

def do_knowntest():
    copydict = {
        'helpers_sample.py':'projectname/lib/helpers.py',
        'controller_sample.py':'projectname/controllers/sample.py',
        'app_globals.py':'projectname/lib/app_globals.py',
        'functional_sample_controller_sample1.py':'projectname/tests/functional/test_sample.py',
    }
    _do_proj_test(copydict)

def do_i18ntest():
    copydict = {
        'functional_sample_controller_i18n.py':'projectname/tests/functional/test_i18n.py',
        'messages.ja.po':'projectname/i18n/ja/LC_MESSAGES/projectname.po',
        'messages.ja.mo':'projectname/i18n/ja/LC_MESSAGES/projectname.mo',
    }
    _do_proj_test(copydict)

def do_genshi():
    paster_create(template_engine='genshi', overwrite=True)
    reset = {
        'helpers_sample.py':'projectname/lib/helpers.py',
        'app_globals.py':'projectname/lib/app_globals.py',
        'rest_routing.py':'projectname/config/routing.py',
        'development.ini':'development.ini',
        }
    copydict = {
        'testgenshi.html':'projectname/templates/testgenshi.html',
        'environment_def_engine.py':'projectname/config/environment.py',
        'functional_sample_controller_sample2.py':'projectname/tests/functional/test_sample2.py'
    }
    copydict.update(reset)
    empty = ['projectname/templates/__init__.py', 'projectname/tests/functional/test_cache.py']
    _do_proj_test(copydict, empty)

def do_two_engines():
    copydict = {
        'middleware_two_engines.py':'projectname/config/middleware.py',
        'test_mako.html':'projectname/templates/test_mako.html',
        'functional_sample_controller_sample3.py':'projectname/tests/functional/test_sample2.py',
    }
    _do_proj_test(copydict)

def do_crazy_decorators():
    _do_proj_test({'functional_sample_controller_sample4.py':'projectname/tests/functional/test_sample3.py'})

def do_jinja2():
    paster_create(template_engine='jinja2', overwrite=True)
    reset = {
        'helpers_sample.py':'projectname/lib/helpers.py',
        'app_globals.py':'projectname/lib/app_globals.py',
        'rest_routing.py':'projectname/config/routing.py',
        'development.ini':'development.ini',
        }
    copydict = {
        'controller_sample.py':'projectname/controllers/sample.py',
        'testjinja2.html':'projectname/templates/testjinja2.html',
        'environment_def_engine.py':'projectname/config/environment.py',
        'functional_sample_controller_jinja2.py':'projectname/tests/functional/test_jinja2.py',
    }
    copydict.update(reset)
    empty = [
         'projectname/templates/__init__.py',
         'projectname/tests/functional/test_sample.py',
         'projectname/tests/functional/test_sample2.py',
         'projectname/tests/functional/test_sample3.py',
         'projectname/tests/functional/test_cache.py'
     ]
    _do_proj_test(copydict, empty)

def do_cache_decorator():
    copydict = {
        'middleware_mako.py':'projectname/config/middleware.py',
        'app_globals.py':'projectname/lib/app_globals.py',
        'cache_controller.py':'projectname/controllers/cache.py',
        'functional_controller_cache_decorator.py':'projectname/tests/functional/test_cache.py',
    }
    empty = [
        'projectname/tests/functional/test_mako.py',
        'projectname/tests/functional/test_jinja2.py',
        'projectname/tests/functional/test_sample.py',
        'projectname/tests/functional/test_sample2.py',
        'projectname/tests/functional/test_sample3.py'
     ]
    _do_proj_test(copydict, empty)

def do_xmlrpc():
    copydict = {
        'middleware_mako.py':'projectname/config/middleware.py',
        'base_with_xmlrpc.py':'projectname/lib/base.py',
        'controller_xmlrpc.py':'projectname/controllers/xmlrpc.py',
        'functional_controller_xmlrpc.py':'projectname/tests/functional/test_xmlrpc.py'
    }
    empty = [
        'projectname/tests/functional/test_cache.py',
        'projectname/tests/functional/test_jinja2.py',
    ]
    _do_proj_test(copydict, empty)


def make_tag():
    global tagenv
    #res = projenv.run(_get_script_name('svn')+' commit -m "updates"')
    # Space at the end needed so run() doesn't add \n causing svntag to complain
    #res = projenv.run(_get_script_name(sys.executable)+' setup.py svntag --version=0.5 ')
    # XXX Still fails => setuptools problem on win32?
    assert 'Tagging 0.5 version' in res.stdout
    assert 'Auto-update of version strings' in res.stdout
    res = testenv.run(_get_script_name('svn')+' co %s/ProjectName/tags/0.5 Proj-05 '
                      % testenv.svn_url)
    setup = res.files_created['Proj-05/setup.py']
    setup.mustcontain('0.5')
    assert 'Proj-05/setup.cfg' not in res.files_created
    tagenv = TestFileEnvironment(
        os.path.join(testenv.base_path, 'Proj-05').replace('\\','/'),
        start_clear=False,
        template_path=template_path)

def do_sqlaproject():
    paster_create(template_engine='mako', overwrite=True, sqlatesting=True)
    reset = {
        'helpers_sample.py':'projectname/lib/helpers.py',
        'app_globals.py':'projectname/lib/app_globals.py',
        'rest_routing.py':'projectname/config/routing.py',
        'development_sqlatesting.ini':'development.ini',
        'websetup.py':'projectname/websetup.py',
        'model__init__.py':'projectname/model/__init__.py',
        'environment_def_sqlamodel.py':'projectname/config/environment.py',
        'tests__init__.py':'projectname/tests/__init__.py',
        }
    copydict = {
        'controller_sqlatest.py':'projectname/controllers/sample.py',
        'test_mako.html':'projectname/templates/test_mako.html',
        'test_sqlalchemy.html':'projectname/templates/test_sqlalchemy.html',
        'functional_sample_controller_sqlatesting.py':'projectname/tests/functional/test_sqlalchemyproject.py',
    }
    copydict.update(reset)
    empty = [
         'projectname/templates/__init__.py',
         'projectname/tests/functional/test_sample.py',
         'projectname/tests/functional/test_sample2.py',
         'projectname/tests/functional/test_sample3.py',
         'projectname/tests/functional/test_cache.py'
     ]
    _do_proj_test(copydict, empty)
    # res = projenv.run(_get_script_name('paster')+' setup-app development.ini', expect_stderr=True,)
    # assert '?' not in res.stdout


# Unfortunately, these are ordered, so be careful
def test_project_paster_create():
    paster_create()

def test_project_make_controller():
    make_controller()

def test_project_make_controller_subdirectory():
    make_controller_subdirectory()

def test_project_do_nosetests():
    do_nosetests()

def test_project_do_knowntest():
    do_knowntest()

def test_project_do_i18ntest():
    do_i18ntest()

def test_project_make_restcontroller():
    make_restcontroller()

def test_project_make_restcontroller_subdirectory():
    make_restcontroller_subdirectory()
    
def test_project_do_rest_nosetests():
    copydict = {
        'rest_routing.py':'projectname/config/routing.py',
        'development.ini':'development.ini',
    }
    match_routes_output = [
        'Route name +Methods +Path',
        'restsamples +GET +/restsamples'
    ]
    _do_proj_test(copydict, match_routes_output)

# Tests with templating plugin dependencies
def test_project_do_crazy_decorators():
    do_crazy_decorators()

def test_project_do_cache_decorator():
    do_cache_decorator()

def test_project_do_genshi_default():
    if is_jython:
        raise SkipTest('Jython does not currently support Genshi')
    do_genshi()

def test_project_do_jinja2():
    do_jinja2()

def test_project_do_xmlrpc():
    do_xmlrpc()

#def test_project_make_tag():
#    make_tag()
def test_project_do_sqlaproject():
    if SQLAtesting:
        do_sqlaproject()
    else:
        pass

def teardown():
    dir_to_clean = os.path.join(os.path.dirname(__file__), TEST_OUTPUT_DIRNAME)
    cov_dir = os.path.join(dir_to_clean, 'ProjectName')
    main_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    
    # Scan and move the coverage files
    # for name in os.listdir(cov_dir):
    #     if name.startswith('.coverage.'):
    #         shutil.move(os.path.join(cov_dir, name), main_dir)
    #     
    shutil.rmtree(dir_to_clean)

########NEW FILE########
__FILENAME__ = event_file
from pylons.events import NewRequest, NewResponse, subscriber


@subscriber(NewRequest)
def add_reggy(event):
    event.request.reg = True

@subscriber(NewResponse)
def add_respy(event):
    event.response.reg = True

########NEW FILE########
__FILENAME__ = goodbye
import logging

from pylons import request, response, session, tmpl_context as c, url
from pylons.controllers import WSGIController
from pylons.controllers.util import abort, redirect
from webob import Response
from webob.exc import HTTPNotFound

log = logging.getLogger(__name__)

class Smithy(WSGIController):
    def __init__(self):
        self._pylons_log_debug = True

    def index(self):
        return 'Hello World'
    
__controller__ = 'Smithy'

########NEW FILE########
__FILENAME__ = hello
import logging

from pylons import request, response, session, tmpl_context as c, url
from pylons.controllers import WSGIController
from pylons.controllers.util import abort, redirect
from pylons.templating import render_mako
from webob import Response
from webob.exc import HTTPNotFound

log = logging.getLogger(__name__)

class HelloController(WSGIController):
    def __init__(self):
        self._pylons_log_debug = True

    def index(self):
        return 'Hello World'
    
    def oops(self):
        raise Exception('oops')
    
    def abort(self):
        abort(404)
    
    def intro_template(self):
        return render_mako('/hello.html')
    
    def time_template(self):
        return render_mako('/time.html', cache_key='fred', cache_expire=20)


def special_controller(environ, start_response):
    return HTTPNotFound()

def empty_wsgi(environ, start_response):
    return

def a_view(request):
    return Response('A View')

########NEW FILE########
__FILENAME__ = i18nc
import datetime

from pylons import request, response, session, url
from pylons import tmpl_context as c
from pylons import app_globals
from pylons.i18n import _, get_lang, set_lang, LanguageError
from pylons.controllers import WSGIController
from pylons.controllers.util import abort, redirect

class I18NcController(WSGIController):
    def set_lang(self):
        return self._set_lang(_)

    def set_lang_pylonscontext(self, pylons):
        return self._set_lang(lambda *args: pylons.translator.ugettext(*args))

    def _set_lang(self, gettext):
        lang = request.GET['lang']
        try:
            set_lang(lang)
        except (LanguageError, IOError), e:
            resp_unicode = gettext('Could not set language to "%(lang)s"') % {'lang': lang}
        else:
            session['lang'] = lang
            session.save()
            resp_unicode = gettext('Set language to "%(lang)s"') % {'lang': lang}
        return resp_unicode

    def i18n_index(self):
        obj = request._current_obj()
        locale_list = request.languages
        set_lang(request.languages)
        return unicode(_('basic index page'))

    def no_lang(self):
        set_lang(None)
        response.write(_('No language'))
        set_lang([])
        response.write(_('No languages'))
        return ''
    
    def langs(self):
        locale_list = request.languages
        set_lang(request.languages)
        return str(get_lang())

########NEW FILE########
