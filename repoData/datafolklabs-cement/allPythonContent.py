__FILENAME__ = arg
"""
Cement core argument module.

"""

from ..core import interface, handler
from ..utils.misc import minimal_logger

LOG = minimal_logger(__name__)


# pylint: disable=w0613
def argument_validator(klass, obj):
    """Validates a handler implementation against the IArgument interface."""
    members = [
        '_setup',
        'parse',
        'add_argument',
    ]

    interface.validate(IArgument, obj, members)


# pylint: disable=W0105,W0232,W0232,R0903,E0213,R0923
class IArgument(interface.Interface):

    """
    This class defines the Argument Handler Interface.  Classes that
    implement this handler must provide the methods and attributes defined
    below.  Implementations do *not* subclass from interfaces.

    Example:

    .. code-block:: python

        from cement.core import interface, arg

        class MyArgumentHandler(arg.CementArgumentHandler):
            class Meta:
                interface = arg.IArgument
                label = 'my_argument_handler'

    """
    class IMeta:

        """Interface meta-data options."""

        label = 'argument'
        """The string identifier of the interface."""

        validator = argument_validator
        """Interface validator function."""

    # Must be provided by the implementation
    Meta = interface.Attribute('Handler Meta-data')

    def _setup(app_obj):
        """
        The _setup function is called during application initialization and
        must 'setup' the handler object making it ready for the framework
        or the application to make further calls to it.

        :param app_obj: The application object
        :returns: None

        """

    # pylint: disable=E0211
    def add_argument(*args, **kw):
        """
        Add arguments for parsing.  This should be -o/--option or positional.
        Note that the interface defines the following parameters so that at
        the very least, external extensions can guarantee that they can
        properly add command line arguments when necessary.  The
        implementation itself should, and will provide and support many more
        options than those listed here.  That said, the implementation must
        support the following:

        :arg args: List of option arguments.  Generally something like
            ['-h', '--help'].
        :keyword dest: The destination name (var).  Default: arg[0]'s string.
        :keyword help: The help text for --help output (for that argument).
        :keyword action: Must support: ['store', 'store_true', 'store_false',
            'store_const']
        :keyword const: The value stored if action == 'store_const'.
        :keyword default: The default value.
        :returns: None

        """

    def parse(arg_list):
        """
        Parse the argument list (i.e. sys.argv).  Can return any object as
        long as it's members contain those of the added arguments.  For
        example, if adding a '-v/--version' option that stores to the dest of
        'version', then the member must be callable as 'Object().version'.

        :param arg_list: A list of command line arguments.
        :returns: Callable object

        """


# pylint: disable=W0105
class CementArgumentHandler(handler.CementBaseHandler):

    """Base class that all Argument Handlers should sub-class from."""

    class Meta:

        """
        Handler meta-data (can be passed as keyword arguments to the parent
        class).
        """

        label = None
        """The string identifier of the handler implementation."""

        interface = IArgument
        """The interface that this class implements."""

    def __init__(self, *args, **kw):
        super(CementArgumentHandler, self).__init__(*args, **kw)

########NEW FILE########
__FILENAME__ = backend
"""Cement core backend module."""

# Note: Nothing is covered here because this file is imported before nose and
# coverage take over.. and so its a false positive that nothing is covered.

import sys  # pragma: nocover

VERSION = (2, 3, 1, 'alpha', 0)  # pragma: nocover

# global handlers dict
__handlers__ = {}  # pragma: nocover

# global hooks dict
__hooks__ = {}  # pragma: nocover

# Save original stdout/stderr for supressing output.  This is actually reset
# in foundation.CementApp.lay_cement() before nullifying output, but we set
# it here just for a default.
__saved_stdout__ = sys.stdout  # pragma: nocover
__saved_stderr__ = sys.stderr  # pragma: nocover

########NEW FILE########
__FILENAME__ = cache
"""Cement core cache module."""

from ..core import interface, handler
from ..utils.misc import minimal_logger

LOG = minimal_logger(__name__)


def cache_validator(klass, obj):
    """Validates a handler implementation against the ICache interface."""

    members = [
        '_setup',
        'get',
        'set',
        'delete',
        'purge',
    ]
    interface.validate(ICache, obj, members)


class ICache(interface.Interface):

    """
    This class defines the Cache Handler Interface.  Classes that
    implement this handler must provide the methods and attributes defined
    below.

    Implementations do *not* subclass from interfaces.

    Usage:

    .. code-block:: python

        from cement.core import cache

        class MyCacheHandler(object):
            class Meta:
                interface = cache.ICache
                label = 'my_cache_handler'
            ...

    """
    # pylint: disable=W0232, C0111, R0903
    class IMeta:

        """Interface meta-data."""

        label = 'cache'
        """The label (or type identifier) of the interface."""

        validator = cache_validator
        """Interface validator function."""

    # Must be provided by the implementation
    Meta = interface.Attribute('Handler meta-data')

    def _setup(app_obj):
        """
        The _setup function is called during application initialization and
        must 'setup' the handler object making it ready for the framework
        or the application to make further calls to it.

        :param app_obj: The application object.
        :returns: None

        """

    def get(key, fallback=None):
        """
        Get the value for a key in the cache.  If the key does not exist
        or the key/value in cache is expired, this functions must return
        'fallback' (which in turn must default to None).

        :param key: The key of the value stored in cache
        :param fallback: Optional value that is returned if the cache is
         expired or the key does not exist.  Default: None
        :returns: Unknown (whatever the value is in cache, or the `fallback`)

        """

    def set(key, value, time=None):
        """
        Set the key/value in the cache for a set amount of `time`.

        :param key: The key of the value to store in cache.
        :param value: The value of that key to store in cache.
        :param time: A one-off expire time.  If no time is given, then a
            default value is used (determined by the implementation).
        :type time: integer (seconds) or None
        :returns: None

        """

    def delete(key):
        """
        Deletes a key/value from the cache.

        :param key: The key in the cache to delete.
        :returns: True if the key is successfully deleted, False otherwise.
        :rtype: boolean

        """

    # pylint: disable=E0211
    def purge():
        """
        Clears all data from the cache.

        """


class CementCacheHandler(handler.CementBaseHandler):

    """
    Base class that all Cache Handlers should sub-class from.

    """
    class Meta:

        """
        Handler meta-data (can be passed as keyword arguments to the parent
        class).
        """

        label = None
        """String identifier of this handler implementation."""

        interface = ICache
        """The interface that this handler class implements."""

    def __init__(self, *args, **kw):
        super(CementCacheHandler, self).__init__(*args, **kw)

########NEW FILE########
__FILENAME__ = config
"""Cement core config module."""

from ..core import interface, handler


def config_validator(klass, obj):
    """Validates a handler implementation against the IConfig interface."""
    members = [
        '_setup',
        'keys',
        'get_sections',
        'get_section_dict',
        'get',
        'set',
        'parse_file',
        'merge',
        'add_section',
        'has_section',
    ]
    interface.validate(IConfig, obj, members)


class IConfig(interface.Interface):

    """
    This class defines the Config Handler Interface.  Classes that
    implement this handler must provide the methods and attributes defined
    below.

    All implementations must provide sane 'default' functionality when
    instantiated with no arguments.  Meaning, it can and should accept
    optional parameters that alter how it functions, but can not require
    any parameters.  When the framework first initializes handlers it does
    not pass anything too them, though a handler can be instantiated first
    (with or without parameters) and then passed to 'CementApp()' already
    instantiated.

    Implementations do *not* subclass from interfaces.

    Usage:

    .. code-block:: python

        from cement.core import config

        class MyConfigHandler(config.CementConfigHandler):
            class Meta:
                interface = config.IConfig
                label = 'my_config_handler'
            ...

    """
    # pylint: disable=W0232, C0111, R0903
    class IMeta:

        """Interface meta-data."""
        label = 'config'
        """The string identifier of the interface."""

        validator = config_validator
        """The validator function."""

    # Must be provided by the implementation
    Meta = interface.Attribute('Handler Meta-data')

    def _setup(app_obj):
        """
        The _setup function is called during application initialization and
        must 'setup' the handler object making it ready for the framework
        or the application to make further calls to it.

        :param app_obj: The application object.
        :returns: None

        """

    def parse_file(file_path):
        """
        Parse config file settings from file_path.  Returns True if the file
        existed, and was parsed successfully.  Returns False otherwise.

        :param file_path: The path to the config file to parse.
        :returns: True if the file was parsed, False otherwise.
        :rtype: boolean

        """

    def keys(section):
        """
        Return a list of configuration keys from `section`.

        :param section: The config [section] to pull keys from.
        :returns: A list of keys in `section`.
        :rtype: list

        """

    def get_sections():
        """
        Return a list of configuration sections.  These are designated by a
        [block] label in a config file.

        :returns: A list of config sections.
        :rtype: list

        """

    def get_section_dict(section):
        """
        Return a dict of configuration parameters for [section].

        :param section: The config [section] to generate a dict from (using
            that section keys).
        :returns: A dictionary of the config section.
        :rtype: dict

        """

    def add_section(section):
        """
        Add a new section if it doesn't exist.

        :param section: The [section] label to create.
        :returns: None

        """

    def get(section, key):
        """
        Return a configuration value based on [section][key].  The return
        value type is unknown.

        :param section: The [section] of the configuration to pull key value
            from.
        :param key: The configuration key to get the value from.
        :returns: The value of the `key` in `section`.
        :rtype: Unknown

        """

    def set(section, key, value):
        """
        Set a configuration value based at [section][key].

        :param section: The [section] of the configuration to pull key value
            from.
        :param key: The configuration key to set the value at.
        :param value: The value to set.
        :returns: None

        """

    def merge(dict_obj, override=True):
        """
        Merges a dict object into the configuration.

        :param dict_obj: The dictionary to merge into the config
        :param override: Boolean.  Whether to override existing values.
            Default: True
        :returns: None
        """

    def has_section(section):
        """
        Returns whether or not the section exists.

        :param section: The section to test for.
        :returns: boolean

        """


class CementConfigHandler(handler.CementBaseHandler):

    """
    Base class that all Config Handlers should sub-class from.

    """
    class Meta:

        """
        Handler meta-data (can be passed as keyword arguments to the parent
        class).
        """

        label = None
        """The string identifier of the implementation."""

        interface = IConfig
        """The interface that this handler implements."""

    def __init__(self, *args, **kw):
        super(CementConfigHandler, self).__init__(*args, **kw)

########NEW FILE########
__FILENAME__ = controller
"""Cement core controller module."""

import re
import textwrap
import argparse
from ..core import exc, interface, handler
from ..utils.misc import minimal_logger

LOG = minimal_logger(__name__)


def controller_validator(klass, obj):
    """
    Validates a handler implementation against the IController interface.

    """
    members = [
        '_setup',
        '_dispatch',
    ]
    meta = [
        'label',
        'aliases',
        'interface',
        'description',
        'config_section',
        'config_defaults',
        'arguments',
        'usage',
        'epilog',
        'stacked_on',
        'stacked_type',
        'hide',
    ]
    interface.validate(IController, obj, members, meta=meta)

    # also check _meta.arguments values
    errmsg = "Controller arguments must be a list of tuples.  I.e. " + \
             "[ (['-f', '--foo'], dict(action='store')), ]"

    if obj._meta.arguments is not None:
        if type(obj._meta.arguments) is not list:
            raise exc.InterfaceError(errmsg)
        for item in obj._meta.arguments:
            if type(item) is not tuple:
                raise exc.InterfaceError(errmsg)
            if type(item[0]) is not list:
                raise exc.InterfaceError(errmsg)
            if type(item[1]) is not dict:
                raise exc.InterfaceError(errmsg)


class IController(interface.Interface):

    """
    This class defines the Controller Handler Interface.  Classes that
    implement this handler must provide the methods and attributes defined
    below.

    Implementations do *not* subclass from interfaces.

    Usage:

    .. code-block:: python

        from cement.core import controller

        class MyBaseController(controller.CementBaseController):
            class Meta:
                interface = controller.IController
                ...
    """
    # pylint: disable=W0232, C0111, R0903
    class IMeta:

        """Interface meta-data."""

        label = 'controller'
        """The string identifier of the interface."""

        validator = controller_validator
        """The interface validator function."""

    # Must be provided by the implementation
    Meta = interface.Attribute('Handler meta-data')

    def _setup(app_obj):
        """
        The _setup function is after application initialization and after it
        is determined that this controller was requested via command line
        arguments.  Meaning, a controllers _setup() function is only called
        right before it's _dispatch() function is called to execute a command.
        Must 'setup' the handler object making it ready for the framework
        or the application to make further calls to it.

        :param app_obj: The application object.
        :returns: None

        """

    def _dispatch(self):
        """
        Reads the application object's data to dispatch a command from this
        controller.  For example, reading self.app.pargs to determine what
        command was passed, and then executing that command function.

        Note that Cement does *not* parse arguments when calling _dispatch()
        on a controller, as it expects the controller to handle parsing
        arguments (I.e. self.app.args.parse()).

        :returns: None

        """


class expose(object):

    """
    Used to expose controller functions to be listed as commands, and to
    decorate the function with Meta data for the argument parser.

    :param help: Help text to display for that command.
    :type help: str
    :param hide: Whether the command should be visible.
    :type hide: boolean
    :param aliases: Aliases to this command.
    :param aliases_only: Whether to only display the aliases (not the label).
     This is useful for situations where you have obscure function names
     which you do not want displayed.  Effecively, if there are aliases and
     `aliases_only` is True, then aliases[0] will appear as the actual
     command/function label.
    :type aliases: list

    Usage:

    .. code-block:: python

        from cement.core.controller import CementBaseController, expose

        class MyAppBaseController(CementBaseController):
            class Meta:
                label = 'base'

            @expose(hide=True, aliases=['run'])
            def default(self):
                print("In MyAppBaseController.default()")

            @expose()
            def my_command(self):
                print("In MyAppBaseController.my_command()")

    """
    # pylint: disable=W0622

    def __init__(self, help='', hide=False, aliases=[], aliases_only=False):
        self.hide = hide
        self.help = help
        self.aliases = aliases
        self.aliases_only = aliases_only

    def __call__(self, func):
        metadict = {}
        metadict['label'] = re.sub('_', '-', func.__name__)
        metadict['func_name'] = func.__name__
        metadict['exposed'] = True
        metadict['hide'] = self.hide
        metadict['help'] = self.help
        metadict['aliases'] = self.aliases
        metadict['aliases_only'] = self.aliases_only
        metadict['controller'] = None  # added by the controller
        func.__cement_meta__ = metadict
        return func


# pylint: disable=R0921
class CementBaseController(handler.CementBaseHandler):

    """
    This is an implementation of the
    `IControllerHandler <#cement.core.controller.IController>`_ interface, but
    as a base class that application controllers `should` subclass from.
    Registering it directly as a handler is useless.

    NOTE: This handler **requires** that the applications 'arg_handler' be
    argparse.  If using an alternative argument handler you will need to
    write your own controller base class.

    Usage:

    .. code-block:: python

        from cement.core import controller

        class MyAppBaseController(controller.CementBaseController):
            class Meta:
                label = 'base'
                description = 'MyApp is awesome'
                config_defaults = dict()
                arguments = []
                epilog = "This is the text at the bottom of --help."
                # ...

        class MyStackedController(controller.CementBaseController):
            class Meta:
                label = 'second_controller'
                aliases = ['sec', 'secondary']
                stacked_on = 'base'
                stacked_type = 'embedded'
                # ...

    """
    class Meta:

        """
        Controller meta-data (can be passed as keyword arguments to the parent
        class).

        """

        interface = IController
        """The interface this class implements."""

        label = 'base'
        """The string identifier for the controller."""

        aliases = []
        """
        A list of aliases for the controller.  Will be treated like
        command/function aliases for non-stacked controllers.  For example:
        'myapp <controller_label> --help' is the same as
        'myapp <controller_alias> --help'.
        """

        aliases_only = False
        """
        When set to True, the controller label will not be displayed at
        command line, only the aliases will.  Effectively, aliases[0] will
        appear as the label.  This feature is useful for the situation Where
        you might want two controllers to have the same label when stacked
        on top of separate controllers.  For example, 'myapp users list' and
        'myapp servers list' where 'list' is a stacked controller, not a
        function.
        """

        description = None
        """The description shown at the top of '--help'.  Default: None"""

        config_section = None
        """
        A config [section] to merge config_defaults into.  Cement will default
        to controller.<label> if None is set.
        """

        config_defaults = {}
        """
        Configuration defaults (type: dict) that are merged into the
        applications config object for the config_section mentioned above.
        """

        arguments = []
        """
        Arguments to pass to the argument_handler.  The format is a list
        of tuples whos items are a ( list, dict ).  Meaning:

        ``[ ( ['-f', '--foo'], dict(dest='foo', help='foo option') ), ]``

        This is equivelant to manually adding each argument to the argument
        parser as in the following example:

        ``parser.add_argument(['-f', '--foo'], help='foo option', dest='foo')``

        """

        stacked_on = 'base'
        """
        A label of another controller to 'stack' commands/arguments on top of.
        """

        stacked_type = 'embedded'
        """
        Whether to `embed` commands and arguments within the parent controller
        or to simply `nest` the controller under the parent controller (making
        it a sub-sub-command).  Must be one of `['embedded', 'nested']` only
        if `stacked_on` is not `None`.
        """

        hide = False
        """Whether or not to hide the controller entirely."""

        epilog = None
        """
        The text that is displayed at the bottom when '--help' is passed.
        """

        usage = None
        """
        The text that is displayed at the top when '--help' is passed.
        Although the default is `None`, Cement will set this to a generic
        usage based on the `prog`, `controller` name, etc if nothing else is
        passed.
        """

        argument_formatter = argparse.RawDescriptionHelpFormatter
        """
        The argument formatter class to use to display --help output.
        """

    def __init__(self, *args, **kw):
        super(CementBaseController, self).__init__(*args, **kw)

        self.app = None
        self._commands = {}  # used to store collected commands
        self._visible_commands = []  # used to sort visible command labels
        self._arguments = []  # used to store collected arguments
        self._dispatch_map = {}  # used to map commands/aliases to controller
        self._dispatch_command = None  # set during _parse_args()

    def _setup(self, app_obj):
        """
        See `IController._setup() <#cement.core.cache.IController._setup>`_.
        """
        super(CementBaseController, self)._setup(app_obj)

        if getattr(self._meta, 'description', None) is None:
            self._meta.description = "%s Controller" % \
                self._meta.label.capitalize()

        self.app = app_obj

    def _collect(self):
        self.app.log.debug("collecting arguments/commands for %s" % self)
        arguments = []
        commands = []

        # process my arguments and commands first
        arguments = list(self._meta.arguments)

        for member in dir(self.__class__):
            if member.startswith('_'):
                continue
            try:
                func = getattr(self.__class__, member).__cement_meta__
            except AttributeError:
                continue
            else:
                func['controller'] = self
                commands.append(func)

        # process stacked controllers second for commands and args
        for contr in handler.list('controller'):
            # don't include self here
            if contr == self.__class__:
                continue

            contr = contr()
            contr._setup(self.app)
            if contr._meta.stacked_on == self._meta.label:
                if contr._meta.stacked_type == 'embedded':
                    contr_arguments, contr_commands = contr._collect()
                    for arg in contr_arguments:
                        arguments.append(arg)
                    for func in contr_commands:
                        commands.append(func)
                elif contr._meta.stacked_type == 'nested':
                    metadict = {}
                    metadict['label'] = re.sub('_', '-', contr._meta.label)
                    metadict['func_name'] = '_dispatch'
                    metadict['exposed'] = True
                    metadict['hide'] = contr._meta.hide
                    metadict['help'] = contr._meta.description
                    metadict['aliases'] = contr._meta.aliases
                    metadict['aliases_only'] = contr._meta.aliases_only
                    metadict['controller'] = contr
                    commands.append(metadict)
                else:
                    raise exc.FrameworkError(
                        "Controller '%s' " % contr._meta.label +
                        "has an unknown stacked type of '%s'." %
                        contr._meta.stacked_type
                    )
        return (arguments, commands)

    def _process_arguments(self):
        for _arg, _kw in self._arguments:
            try:
                self.app.args.add_argument(*_arg, **_kw)
            except argparse.ArgumentError as e:
                raise exc.FrameworkError(e.__str__())

    def _process_commands(self):
        self._dispatch_map = {}
        self._visible_commands = []

        for cmd in self._commands:
            # process command labels
            if cmd['label'] in self._dispatch_map.keys():
                raise exc.FrameworkError(
                    "Duplicate command named '%s' " % cmd['label'] +
                    "found in controller '%s'" % cmd['controller']
                )
            self._dispatch_map[cmd['label']] = cmd

            if not cmd['hide']:
                self._visible_commands.append(cmd['label'])

            # process command aliases
            for alias in cmd['aliases']:
                if alias in self._dispatch_map.keys():
                    raise exc.FrameworkError(
                        "The alias '%s' of the " % alias +
                        "'%s' controller collides " % cmd['controller'] +
                        "with a command or alias of the same name."
                    )
                self._dispatch_map[alias] = cmd
        self._visible_commands.sort()

    def _get_dispatch_command(self):
        if (len(self.app.argv) <= 0) or (self.app.argv[0].startswith('-')):
            # if no command is passed, then use default
            if 'default' in self._dispatch_map.keys():
                self._dispatch_command = self._dispatch_map['default']
        elif self.app.argv[0] in self._dispatch_map.keys():
            self._dispatch_command = self._dispatch_map[self.app.argv[0]]
            self.app.argv.pop(0)
        else:
            # check for default again (will get here if command line has
            # positional arguments that don't start with a -)
            if 'default' in self._dispatch_map.keys():
                self._dispatch_command = self._dispatch_map['default']

    def _parse_args(self):
        self.app.args.description = self._help_text
        self.app.args.usage = self._usage_text
        self.app.args.formatter_class = self._meta.argument_formatter
        self.app._parse_args()

    def _dispatch(self):
        """
        Takes the remaining arguments from self.app.argv and parses for a
        command to dispatch, and if so... dispatches it.

        """
        if hasattr(self._meta, 'epilog'):
            if self._meta.epilog is not None:
                self.app.args.epilog = self._meta.epilog

        self._arguments, self._commands = self._collect()
        self._process_commands()
        self._get_dispatch_command()

        if self._dispatch_command:
            if self._dispatch_command['func_name'] == '_dispatch':
                func = getattr(self._dispatch_command['controller'],
                               '_dispatch')
                func()
            else:
                self._process_arguments()
                self._parse_args()
                func = getattr(self._dispatch_command['controller'],
                               self._dispatch_command['func_name'])
                func()
        else:
            self._process_arguments()
            self._parse_args()

    @property
    def _usage_text(self):
        """Returns the usage text displayed when '--help' is passed."""

        if self._meta.usage is not None:
            return self._meta.usage

        txt = "%s (sub-commands ...) [options ...] {arguments ...}" % \
              self.app.args.prog
        return txt

    @property
    def _help_text(self):
        """Returns the help text displayed when '--help' is passed."""

        cmd_txt = ''
        for label in self._visible_commands:
            cmd = self._dispatch_map[label]
            if len(cmd['aliases']) > 0 and cmd['aliases_only']:
                if len(cmd['aliases']) > 1:
                    first = cmd['aliases'].pop(0)
                    cmd_txt = cmd_txt + "  %s (aliases: %s)\n" % \
                        (first, ', '.join(cmd['aliases']))
                else:
                    cmd_txt = cmd_txt + "  %s\n" % cmd['aliases'][0]
            elif len(cmd['aliases']) > 0:
                cmd_txt = cmd_txt + "  %s (aliases: %s)\n" % \
                    (label, ', '.join(cmd['aliases']))
            else:
                cmd_txt = cmd_txt + "  %s\n" % label

            if cmd['help']:
                cmd_txt = cmd_txt + "    %s\n\n" % cmd['help']
            else:
                cmd_txt = cmd_txt + "\n"

        if len(cmd_txt) > 0:
            txt = '''%s

commands:

%s


        ''' % (self._meta.description, cmd_txt)
        else:
            txt = self._meta.description

        return textwrap.dedent(txt)

########NEW FILE########
__FILENAME__ = exc
"""Cement core exceptions module."""


class FrameworkError(Exception):

    """
    General framework (non-application) related errors.

    :param msg: The error message.

    """

    def __init__(self, msg):
        Exception.__init__(self)
        self.msg = msg

    def __str__(self):
        return self.msg


class InterfaceError(FrameworkError):

    """Interface related errors."""
    pass


class CaughtSignal(FrameworkError):

    """
    Raised when a defined signal is caught.  For more information regarding
    signals, reference the
    `signal <http://docs.python.org/library/signal.html>`_ library.

    :param signum: The signal number.
    :param frame: The signal frame.

    """

    def __init__(self, signum, frame):
        msg = 'Caught signal %s' % signum
        super(CaughtSignal, self).__init__(msg)
        self.signum = signum
        self.frame = frame

########NEW FILE########
__FILENAME__ = extension
"""Cement core extensions module."""

import sys
from ..core import exc, interface, handler
from ..utils.misc import minimal_logger

if sys.version_info[0] >= 3:
    from imp import reload  # pragma: no cover

LOG = minimal_logger(__name__)


def extension_validator(klass, obj):
    """
    Validates an handler implementation against the IExtension interface.

    """
    members = [
        '_setup',
        'load_extension',
        'load_extensions',
        'get_loaded_extensions',
    ]
    interface.validate(IExtension, obj, members)


class IExtension(interface.Interface):

    """
    This class defines the Extension Handler Interface.  Classes that
    implement this handler must provide the methods and attributes defined
    below.

    Implementations do *not* subclass from interfaces.

    Usage:

    .. code-block:: python

        from cement.core import extension

        class MyExtensionHandler(object):
            class Meta:
                interface = extension.IExtension
                label = 'my_extension_handler'
            ...

    """

    # pylint: disable=W0232, C0111, R0903
    class IMeta:

        """Interface meta-data."""

        label = 'extension'
        """The string identifier of the interface."""

        validator = extension_validator
        """The interface validator function."""

    # Must be provided by the implementation
    Meta = interface.Attribute('Handler Meta-data class')

    def _setup(app_obj):
        """
        The _setup function is called during application initialization and
        must 'setup' the handler object making it ready for the framework
        or the application to make further calls to it.

        :param app_obj: The application object.
        :returns: None

        """

    def load_extension(self, ext_module):
        """
        Load an extension whose module is 'ext_module'.  For example,
        'cement.ext.ext_configobj'.

        :param ext_module: The name of the extension to load.
        :type ext_module: str

        """

    def load_extensions(self, ext_list):
        """
        Load all extensions from ext_list.

        :param ext_list: A list of extension modules to load.  For example:
            ``['cement.ext.ext_configobj', 'cement.ext.ext_logging']``

        :type ext_list: list

        """


class CementExtensionHandler(handler.CementBaseHandler):

    class Meta:

        """
        Handler meta-data (can be passed as keyword arguments to the parent
        class).
        """

        interface = IExtension
        """The interface that this class implements."""

        label = 'cement'
        """The string identifier of the handler."""

    def __init__(self, **kw):
        """
        This is an implementation of the IExtentionHandler interface.  It
        handles loading framework extensions.

        """
        super(CementExtensionHandler, self).__init__(**kw)
        self.app = None
        self._loaded_extensions = []

    def get_loaded_extensions(self):
        """Returns list of loaded extensions."""
        return self._loaded_extensions

    def load_extension(self, ext_module):
        """
        Given an extension module name, load or in other-words 'import' the
        extension.

        :param ext_module: The extension module name.  For example:
            'cement.ext.ext_logging'.
        :type ext_module: str
        :raises: cement.core.exc.FrameworkError

        """
        # If its not a full module path then preppend our default path
        if ext_module.find('.') == -1:
            ext_module = 'cement.ext.ext_%s' % ext_module

        if ext_module in self._loaded_extensions:
            LOG.debug("framework extension '%s' already loaded" % ext_module)
            return

        LOG.debug("loading the '%s' framework extension" % ext_module)
        try:
            if ext_module not in sys.modules:
                __import__(ext_module, globals(), locals(), [], 0)

            if hasattr(sys.modules[ext_module], 'load'):
                sys.modules[ext_module].load()

            if ext_module not in self._loaded_extensions:
                self._loaded_extensions.append(ext_module)

        except ImportError as e:
            raise exc.FrameworkError(e.args[0])

    def load_extensions(self, ext_list):
        """
        Given a list of extension modules, iterate over the list and pass
        individually to self.load_extension().

        :param ext_list: A list of extension modules.
        :type ext_list: list

        """
        for ext in ext_list:
            self.load_extension(ext)

########NEW FILE########
__FILENAME__ = foundation
"""Cement core foundation module."""

import re
import os
import sys
import signal

from ..core import backend, exc, handler, hook, log, config, plugin
from ..core import output, extension, arg, controller, meta, cache
from ..ext import ext_configparser, ext_argparse, ext_logging
from ..ext import ext_nulloutput, ext_plugin
from ..utils.misc import is_true, minimal_logger
from ..utils import fs

if sys.version_info[0] >= 3:
    from imp import reload  # pragma: nocover

LOG = minimal_logger(__name__)


class NullOut(object):

    def write(self, s):
        pass

    def flush(self):
        pass


def cement_signal_handler(signum, frame):
    """
    Catch a signal, run the 'signal' hook, and then raise an exception
    allowing the app to handle logic elsewhere.

    :param signum: The signal number
    :param frame: The signal frame.
    :raises: cement.core.exc.CaughtSignal

    """
    LOG.debug('Caught signal %s' % signum)

    for res in hook.run('signal', signum, frame):
        pass

    raise exc.CaughtSignal(signum, frame)


class CementApp(meta.MetaMixin):

    """
    The primary class to build applications from.

    Usage:

    The following is the simplest CementApp:

    .. code-block:: python

        from cement.core import foundation
        app = foundation.CementApp('helloworld')
        try:
            app.setup()
            app.run()
        finally:
            app.close()

    A more advanced example looks like:

    .. code-block:: python

        from cement.core import foundation, controller

        class MyController(controller.CementBaseController):
            class Meta:
                label = 'base'
                arguments = [
                    ( ['-f', '--foo'], dict(help='Notorious foo option') ),
                    ]
                config_defaults = dict(
                    debug=False,
                    some_config_param='some_value',
                    )

            @controller.expose(help='This is the default command', hide=True)
            def default(self):
                print('Hello World')

        class MyApp(foundation.CementApp):
            class Meta:
                label = 'helloworld'
                extensions = ['daemon','json',]
                base_controller = MyController

        app = MyApp()
        try:
            app.setup()
            app.run()
        finally:
            app.close()

    """
    class Meta:

        """
        Application meta-data (can also be passed as keyword arguments to the
        parent class).
        """

        label = None
        """
        The name of the application.  This should be the common name as you
        would see and use at the command line.  For example 'helloworld', or
        'my-awesome-app'.
        """

        debug = False
        """
        Used internally, and should not be used by developers.  This is set
        to `True` if `--debug` is passed at command line."""

        config_files = None
        """
        List of config files to parse.

        Note: Though Meta.config_section defaults to None, Cement will
        set this to a default list based on Meta.label (or in other words,
        the name of the application).  This will equate to:

        .. code-block:: python

            ['/etc/<app_label>/<app_label>.conf',
             '~/.<app_label>.conf',
             '~/.<app_label>/config']

        """

        plugins = []
        """
        A list of plugins to load.  This is generally considered bad
        practice since plugins should be dynamically enabled/disabled
        via a plugin config file.
        """

        plugin_config_dir = None
        """
        A directory path where plugin config files can be found.  Files
        must end in '.conf'.  By default, this setting is also overridden
        by the '[base] -> plugin_config_dir' config setting parsed in any
        of the application configuration files.

        Note: Though the meta default is None, Cement will set this to
        ``/etc/<app_label>/plugins.d/`` if not set during app.setup().
        """

        plugin_bootstrap = None
        """
        A python package (dotted import path) where plugin code can be
        loaded from.  This is generally something like 'myapp.plugins'
        where a plugin file would live at ``myapp/plugins/myplugin.py``.
        This provides a facility for applications that use 'namespace'
        packages allowing plugins to share the applications python
        namespace.

        Note: Though the meta default is None, Cement will set this to
        ``<app_label>.plugins`` if not set during app.setup().
        """

        plugin_dir = None
        """
        A directory path where plugin code (modules) can be loaded from.
        By default, this setting is also overridden by the
        '[base] -> plugin_dir' config setting parsed in any of the
        application configuration files (where [base] is the
        base configuration section of the application which is determined
        by Meta.config_section but defaults to Meta.label).

        Note: Though the meta default is None, Cement will set this to
        ``/usr/lib/<app_label>/plugins/`` if not set during app.setup()
        """

        argv = None
        """
        A list of arguments to use for parsing command line arguments
        and options.

        Note: Though Meta.argv defaults to None, Cement will set this to
        ``list(sys.argv[1:])`` if no argv is set in Meta during setup().
        """

        arguments_override_config = False
        """
        A boolean to toggle whether command line arguments should
        override configuration values if the argument name matches the
        config key.  I.e. --foo=bar would override config['myapp']['foo'].

        This is different from ``override_arguments`` in that if
        ``arguments_override_config`` is ``True``, then all arguments will
        override (you don't have to list them all).
        """

        override_arguments = ['debug']
        """
        List of arguments that override their configuration counter-part.
        For example, if ``--debug`` is passed (and it's config value is
        ``debug``) then the ``debug`` key of all configuration sections will
        be overridden by the value of the command line option (``True`` in
        this example).

        This is different from ``arguments_override_config`` in that this is
        a selective list of specific arguments to override the config with
        (and not all arguments that match the config).  This list will take
        affect whether ``arguments_override_config`` is ``True`` or ``False``.
        """

        config_section = None
        """
        The base configuration section for the application.

        Note: Though Meta.config_section defaults to None, Cement will
        set this to the value of Meta.label (or in other words, the name
        of the application).
        """

        config_defaults = None
        """Default configuration dictionary.  Must be of type 'dict'."""

        catch_signals = [signal.SIGTERM, signal.SIGINT]
        """
        List of signals to catch, and raise exc.CaughtSignal for.
        Can be set to None to disable signal handling.
        """

        signal_handler = cement_signal_handler
        """A function that is called to handle any caught signals."""

        config_handler = ext_configparser.ConfigParserConfigHandler
        """
        A handler class that implements the IConfig interface.  This can
        be a string (label of a registered handler), an uninstantiated
        class, or an instantiated class object.
        """

        extension_handler = extension.CementExtensionHandler
        """
        A handler class that implements the IExtension interface.  This can
        be a string (label of a registered handler), an uninstantiated
        class, or an instantiated class object.
        """

        log_handler = ext_logging.LoggingLogHandler
        """
        A handler class that implements the ILog interface.  This can
        be a string (label of a registered handler), an uninstantiated
        class, or an instantiated class object.
        """

        plugin_handler = ext_plugin.CementPluginHandler
        """
        A handler class that implements the IPlugin interface.  This can
        be a string (label of a registered handler), an uninstantiated
        class, or an instantiated class object.
        """

        argument_handler = ext_argparse.ArgParseArgumentHandler
        """
        A handler class that implements the IArgument interface.  This can
        be a string (label of a registered handler), an uninstantiated
        class, or an instantiated class object.
        """

        output_handler = ext_nulloutput.NullOutputHandler
        """
        A handler class that implements the IOutput interface.  This can
        be a string (label of a registered handler), an uninstantiated
        class, or an instantiated class object.
        """

        cache_handler = None
        """
        A handler class that implements the ICache interface.  This can
        be a string (label of a registered handler), an uninstantiated
        class, or an instantiated class object.
        """

        base_controller = None
        """
        This is the base application controller.  If a controller is set,
        runtime operations are passed to the controller for command
        dispatch and argument parsing when CementApp.run() is called.

        Note that cement will automatically set the `base_controller` to a
        registered controller whose label is 'base' (only if `base_controller`
        is not currently set).
        """

        extensions = []
        """List of additional framework extensions to load."""

        bootstrap = None
        """
        A bootstrapping module to load after app creation, and before
        app.setup() is called.  This is useful for larger applications
        that need to offload their bootstrapping code such as registering
        hooks/handlers/etc to another file.

        This must be a dotted python module path.
        I.e. 'myapp.bootstrap' (myapp/bootstrap.py).  Cement will then
        import the module, and if the module has a 'load()' function, that
        will also be called.  Essentially, this is the same as an
        extension or plugin, but as a facility for the application itself
        to bootstrap 'hardcoded' application code.  It is also called
        before plugins are loaded.
        """

        core_extensions = [
            'cement.ext.ext_nulloutput',
            'cement.ext.ext_plugin',
            'cement.ext.ext_configparser',
            'cement.ext.ext_logging',
            'cement.ext.ext_argparse',
        ]
        """
        List of Cement core extensions.  These are generally required by
        Cement and should only be modified if you know what you're
        doing.  Use 'extensions' to add to this list, rather than
        overriding core extensions.  That said if you want to prune down
        your application, you can remove core extensions if they are
        not necessary (for example if using your own log handler
        extension you likely don't want/need LoggingLogHandler to be
        registered).
        """

        core_meta_override = [
            'debug',
            'plugin_config_dir',
            'plugin_dir',
            'ignore_deprecation_warnings',
            'template_dir',
        ]
        """
        List of meta options that can/will be overridden by config options
        of the '[base]' config section (where [base] is the base
        configuration section of the application which is determined by
        Meta.config_section but defaults to Meta.label). These overrides
        are required by the framework to function properly and should not
        be used by end user (developers) unless you really know what
        you're doing.  To add your own extended meta overrides please use
        'meta_override'.
        """

        meta_override = []
        """
        List of meta options that can/will be overridden by config options
        of the '[base]' config section (where [base] is the
        base configuration section of the application which is determined
        by Meta.config_section but defaults to Meta.label).
        """

        ignore_deprecation_warnings = False
        """Disable deprecation warnings from being logged by Cement."""

        template_module = None
        """
        A python package (dotted import path) where template files can be
        loaded from.  This is generally something like 'myapp.templates'
        where a plugin file would live at ``myapp/templates/mytemplate.txt``.
        Templates are first loaded from ``CementApp.Meta.template_dir``, and
        and secondly from ``CementApp.Meta.template_module``.
        """

        template_dir = None
        """
        A directory path where template files can be loaded from.  By default,
        this setting is also overridden by the '[base] -> template_dir' config
        setting parsed in any of the application configuration files (where
        [base] is the base configuration section of the application which is
        determinedby Meta.config_section but defaults to Meta.label).

        Note: Though the meta default is None, Cement will set this to
        ``/usr/lib/<app_label>/templates/`` if not set during app.setup()
        """

    def __init__(self, label=None, **kw):
        super(CementApp, self).__init__(**kw)

        # for convenience we translate this to _meta
        if label:
            self._meta.label = label
        self._validate_label()
        self._loaded_bootstrap = None
        self._parsed_args = None
        self._last_rendered = None

        self.ext = None
        self.config = None
        self.log = None
        self.plugin = None
        self.args = None
        self.output = None
        self.controller = None
        self.cache = None

        # setup argv... this has to happen before lay_cement()
        if self._meta.argv is None:
            self._meta.argv = list(sys.argv[1:])

        # hack for command line --debug
        if '--debug' in self.argv:
            self._meta.debug = True

        # setup the cement framework
        self._lay_cement()

    @property
    def debug(self):
        """
        Returns boolean based on whether `--debug` was passed at command line
        or set via the application's configuration file.

        :returns: boolean
        """
        return self._meta.debug

    @property
    def argv(self):
        """The arguments list that will be used when self.run() is called."""
        return self._meta.argv

    def extend(self, member_name, member_object):
        """
        Extend the CementApp() object with additional functions/classes such
        as 'app.my_custom_function()', etc.  It provides an interface for
        extensions to provide functionality that travel along with the
        application object.

        :param member_name: The name to attach the object to.
        :type member_name: str
        :param member_object: The function or class object to attach to
            CementApp().
        :raises: cement.core.exc.FrameworkError

        """
        if hasattr(self, member_name):
            raise exc.FrameworkError("App member '%s' already exists!" %
                                     member_name)
        LOG.debug("extending appication with '.%s' (%s)" %
                 (member_name, member_object))
        setattr(self, member_name, member_object)

    def _validate_label(self):
        if not self._meta.label:
            raise exc.FrameworkError("Application name missing.")

        # validate the name is ok
        ok = ['_', '-']
        for char in self._meta.label:
            if char in ok:
                continue

            if not char.isalnum():
                raise exc.FrameworkError(
                    "App label can only contain alpha-numeric, dashes, " +
                    "or underscores."
                )

    def setup(self):
        """
        This function wraps all '_setup' actons in one call.  It is called
        before self.run(), allowing the application to be _setup but not
        executed (possibly letting the developer perform other actions
        before full execution.).

        All handlers should be instantiated and callable after setup is
        complete.

        """
        LOG.debug("now setting up the '%s' application" % self._meta.label)

        if self._meta.bootstrap is not None:
            LOG.debug("importing bootstrap code from %s" %
                      self._meta.bootstrap)

            if self._meta.bootstrap not in sys.modules \
                    or self._loaded_bootstrap is None:
                __import__(self._meta.bootstrap, globals(), locals(), [], 0)
                if hasattr(sys.modules[self._meta.bootstrap], 'load'):
                    sys.modules[self._meta.bootstrap].load()

                self._loaded_bootstrap = sys.modules[self._meta.bootstrap]
            else:
                reload(self._loaded_bootstrap)

        for res in hook.run('pre_setup', self):
            pass

        self._setup_signals()
        self._setup_extension_handler()
        self._setup_config_handler()
        self._setup_cache_handler()
        self._setup_log_handler()
        self._setup_plugin_handler()
        self._setup_arg_handler()
        self._setup_output_handler()
        self._setup_controllers()

        for res in hook.run('post_setup', self):
            pass

    def run(self):
        """
        This function wraps everything together (after self._setup() is
        called) to run the application.

        """
        for res in hook.run('pre_run', self):
            pass

        # If controller exists, then pass controll to it
        if self.controller:
            self.controller._dispatch()
        else:
            self._parse_args()

        for res in hook.run('post_run', self):
            pass

    def close(self):
        """
        Close the application.  This runs the pre_close and post_close hooks
        allowing plugins/extensions/etc to 'cleanup' at the end of program
        execution.

        """
        for res in hook.run('pre_close', self):
            pass

        LOG.debug("closing the application")

        for res in hook.run('post_close', self):
            pass

    def render(self, data, template=None):
        """
        This is a simple wrapper around self.output.render() which simply
        returns an empty string if no self.output handler is defined.

        :param data: The data dictionary to render.
        :param template: The template to render to.  Default: None (some
            output handlers do not use templates).

        """
        for res in hook.run('pre_render', self, data):
            if not type(res) is dict:
                LOG.debug("pre_render hook did not return a dict().")
            else:
                data = res

        if self.output is None:
            LOG.debug('render() called, but no output handler defined.')
            out_text = ''
        else:
            out_text = self.output.render(data, template)

        for res in hook.run('post_render', self, out_text):
            if not type(res) is str:
                LOG.debug('post_render hook did not return a str()')
            else:
                out_text = str(res)

        self._last_rendered = (data, out_text)
        return out_text

    def get_last_rendered(self):
        """
        DEPRECATION WARNING: This function is deprecated as of Cement 2.1.3
        in favor of the `self.last_rendered` property, and will be removed in
        future versions of Cement.

        Return the (data, output_text) tuple of the last time self.render()
        was called.

        :returns: tuple (data, output_text)

        """
        if not is_true(self._meta.ignore_deprecation_warnings):
            self.log.warn("Cement Deprecation Warning: " +
                          "CementApp.get_last_rendered() has been " +
                          "deprecated, and will be removed in future " +
                          "versions of Cement.  You should use the " +
                          "CementApp.last_rendered property instead.")
        return self._last_rendered

    @property
    def last_rendered(self):
        """
        Return the (data, output_text) tuple of the last time self.render() was
        called.

        :returns: tuple (data, output_text)

        """
        return self._last_rendered

    @property
    def pargs(self):
        """
        Returns the `parsed_args` object as returned by self.args.parse().
        """
        return self._parsed_args

    def add_arg(self, *args, **kw):
        """A shortcut for self.args.add_argument."""
        self.args.add_argument(*args, **kw)

    def _lay_cement(self):
        """Initialize the framework."""
        LOG.debug("laying cement for the '%s' application" %
                  self._meta.label)

        # overrides via command line
        suppress_output = False

        if '--debug' in self._meta.argv:
            self._meta.debug = True
        else:
            # the following are hacks to suppress console output
            for flag in ['--quiet', '--json', '--yaml']:
                if flag in self._meta.argv:
                    suppress_output = True
                    break

        if suppress_output:
            LOG.debug('suppressing all console output per runtime config')
            backend.__saved_stdout__ = sys.stdout
            backend.__saved_stderr__ = sys.stderr
            sys.stdout = NullOut()
            sys.stderr = NullOut()

        # start clean
        backend.__hooks__ = {}
        backend.__handlers__ = {}

        # define framework hooks
        hook.define('pre_setup')
        hook.define('post_setup')
        hook.define('pre_run')
        hook.define('post_run')
        hook.define('pre_argument_parsing')
        hook.define('post_argument_parsing')
        hook.define('pre_close')
        hook.define('post_close')
        hook.define('signal')
        hook.define('pre_render')
        hook.define('post_render')

        # define and register handlers
        handler.define(extension.IExtension)
        handler.define(log.ILog)
        handler.define(config.IConfig)
        handler.define(plugin.IPlugin)
        handler.define(output.IOutput)
        handler.define(arg.IArgument)
        handler.define(controller.IController)
        handler.define(cache.ICache)

        # extension handler is the only thing that can't be loaded... as,
        # well, an extension.  ;)
        handler.register(extension.CementExtensionHandler)

    def _parse_args(self):
        for res in hook.run('pre_argument_parsing', self):
            pass

        self._parsed_args = self.args.parse(self.argv)

        if self._meta.arguments_override_config is True:
            for member in dir(self._parsed_args):
                if member and member.startswith('_'):
                    continue

                # don't override config values for options that weren't passed
                # or in otherwords are None
                elif getattr(self._parsed_args, member) is None:
                    continue

                for section in self.config.get_sections():
                    if member in self.config.keys(section):
                        self.config.set(section, member,
                                        getattr(self._parsed_args, member))

        for member in self._meta.override_arguments:
            for section in self.config.get_sections():
                if member in self.config.keys(section):
                    self.config.set(section, member,
                                    getattr(self._parsed_args, member))

        for res in hook.run('post_argument_parsing', self):
            pass

    def _setup_signals(self):
        if self._meta.catch_signals is None:
            LOG.debug("catch_signals=None... not handling any signals")
            return

        for signum in self._meta.catch_signals:
            LOG.debug("adding signal handler for signal %s" % signum)
            signal.signal(signum, self._meta.signal_handler)

    def _resolve_handler(self, handler_type, handler_def, raise_error=True):
        han = handler.resolve(handler_type, handler_def, raise_error)
        if han is not None:
            han._setup(self)
            return han

    def _setup_extension_handler(self):
        LOG.debug("setting up %s.extension handler" % self._meta.label)
        self.ext = self._resolve_handler('extension',
                                         self._meta.extension_handler)
        self.ext.load_extensions(self._meta.core_extensions)
        self.ext.load_extensions(self._meta.extensions)

    def _setup_config_handler(self):
        LOG.debug("setting up %s.config handler" % self._meta.label)
        self.config = self._resolve_handler('config',
                                            self._meta.config_handler)
        if self._meta.config_section is None:
            self._meta.config_section = self._meta.label
        self.config.add_section(self._meta.config_section)

        if not self._meta.config_defaults is None:
            self.config.merge(self._meta.config_defaults)

        if self._meta.config_files is None:
            label = self._meta.label

            if 'HOME' in os.environ:
                user_home = fs.abspath(os.environ['HOME'])
            else:
                # Kinda dirty, but should resolve issues on Windows per #183
                user_home = fs.abspath('~')  # pragma: nocover

            self._meta.config_files = [
                os.path.join('/', 'etc', label, '%s.conf' % label),
                os.path.join(user_home, '.%s.conf' % label),
                os.path.join(user_home, '.%s' % label, 'config'),
            ]

        for _file in self._meta.config_files:
            self.config.parse_file(_file)

        self.validate_config()

        # hack for --debug
        if '--debug' in self.argv:
            self.config.set(self._meta.config_section, 'debug', True)

        # override select Meta via config
        base_dict = self.config.get_section_dict(self._meta.config_section)
        for key in base_dict:
            if key in self._meta.core_meta_override or \
                    key in self._meta.meta_override:
                # kind of a hack for core_meta_override
                if key in ['debug']:
                    setattr(self._meta, key, is_true(base_dict[key]))
                else:
                    setattr(self._meta, key, base_dict[key])

    def _setup_log_handler(self):
        LOG.debug("setting up %s.log handler" % self._meta.label)
        self.log = self._resolve_handler('log', self._meta.log_handler)

    def _setup_plugin_handler(self):
        LOG.debug("setting up %s.plugin handler" % self._meta.label)

        # modify app defaults if not set
        if self._meta.plugin_config_dir is None:
            self._meta.plugin_config_dir = '/etc/%s/plugins.d/' % \
                                           self._meta.label

        if self._meta.plugin_dir is None:
            self._meta.plugin_dir = '/usr/lib/%s/plugins' % self._meta.label
        if self._meta.plugin_bootstrap is None:
            self._meta.plugin_bootstrap = '%s.plugins' % self._meta.label

        self.plugin = self._resolve_handler('plugin',
                                            self._meta.plugin_handler)
        self.plugin.load_plugins(self._meta.plugins)
        self.plugin.load_plugins(self.plugin.get_enabled_plugins())

    def _setup_output_handler(self):
        if self._meta.output_handler is None:
            LOG.debug("no output handler defined, skipping.")
            return

        LOG.debug("setting up %s.output handler" % self._meta.label)
        self.output = self._resolve_handler('output',
                                            self._meta.output_handler,
                                            raise_error=False)
        if self._meta.template_module is None:
            self._meta.template_module = '%s.templates' % self._meta.label
        if self._meta.template_dir is None:
            self._meta.template_dir = '/usr/lib/%s/templates' % \
                                      self._meta.label

    def _setup_cache_handler(self):
        if self._meta.cache_handler is None:
            LOG.debug("no cache handler defined, skipping.")
            return

        LOG.debug("setting up %s.cache handler" % self._meta.label)
        self.cache = self._resolve_handler('cache',
                                           self._meta.cache_handler,
                                           raise_error=False)

    def _setup_arg_handler(self):
        LOG.debug("setting up %s.arg handler" % self._meta.label)
        self.args = self._resolve_handler('argument',
                                          self._meta.argument_handler)
        self.args.add_argument('--debug', dest='debug',
                               action='store_true',
                               help='toggle debug output')
        self.args.add_argument('--quiet', dest='suppress_output',
                               action='store_true',
                               help='suppress all output')

    def _setup_controllers(self):
        LOG.debug("setting up application controllers")

        if self._meta.base_controller is not None:
            cntr = self._resolve_handler('controller',
                                         self._meta.base_controller)
            self.controller = cntr
            self._meta.base_controller = self.controller
        elif self._meta.base_controller is None:
            if handler.registered('controller', 'base'):
                self.controller = self._resolve_handler('controller', 'base')
                self._meta.base_controller = self.controller

        # This is necessary for some backend usage
        if self._meta.base_controller is not None:
            if self._meta.base_controller._meta.label != 'base':
                raise exc.FrameworkError("Base controllers must have " +
                                         "a label of 'base'.")

    def validate_config(self):
        """
        Validate application config settings.

        Usage:

        .. code-block:: python

            import os
            from cement.core import foundation

            class MyApp(foundation.CementApp):
                class Meta:
                    label = 'myapp'

                def validate_config(self):
                    # test that the log file directory exist, if not create it
                    logdir = os.path.dirname(self.config.get('log', 'file'))

                    if not os.path.exists(logdir):
                        os.makedirs(logdir)

        """
        pass

########NEW FILE########
__FILENAME__ = handler
"""
Cement core handler module.

"""

import re
from ..core import exc, backend, meta
from ..utils.misc import minimal_logger

LOG = minimal_logger(__name__)


class CementBaseHandler(meta.MetaMixin):

    """Base handler class that all Cement Handlers should subclass from."""

    class Meta:

        """
        Handler meta-data (can also be passed as keyword arguments to the
        parent class).

        """

        label = None
        """The string identifier of this handler."""

        interface = None
        """The interface that this class implements."""

        config_section = None
        """
        A config [section] to merge config_defaults with.

        Note: Though Meta.config_section defaults to None, Cement will
        set this to the value of ``<interface_label>.<handler_label>`` if
        no section is set by the user/develop.
        """

        config_defaults = None
        """
        A config dictionary that is merged into the applications config
        in the [<config_section>] block.  These are defaults and do not
        override any existing defaults under that section.
        """

    def __init__(self, **kw):
        super(CementBaseHandler, self).__init__(**kw)
        self.app = None

    def _setup(self, app_obj):
        """
        The _setup function is called during application initialization and
        must 'setup' the handler object making it ready for the framework
        or the application to make further calls to it.

        :param app_obj: The application object.
        :returns: None

        """
        self.app = app_obj

        if self._meta.config_section is None:
            self._meta.config_section = "%s.%s" % \
                (self._meta.interface.IMeta.label, self._meta.label)

        if self._meta.config_defaults is not None:
            LOG.debug("merging config defaults from '%s' " % self +
                      "into section '%s'" % self._meta.config_section)
            dict_obj = dict()
            dict_obj[self._meta.config_section] = self._meta.config_defaults
            self.app.config.merge(dict_obj, override=False)


def get(handler_type, handler_label, *args):
    """
    Get a handler object.

    Required Arguments:

    :param handler_type: The type of handler (i.e. 'output')
    :type handler_type: str
    :param handler_label: The label of the handler (i.e. 'json')
    :type handler_label: str
    :param fallback:  A fallback value to return if handler_label doesn't
        exist.
    :returns: An uninstantiated handler object
    :raises: cement.core.exc.FrameworkError

    Usage:

        from cement.core import handler
        output = handler.get('output', 'json')
        output.render(dict(foo='bar'))

    """
    if handler_type not in backend.__handlers__:
        raise exc.FrameworkError("handler type '%s' does not exist!" %
                                 handler_type)

    if handler_label in backend.__handlers__[handler_type]:
        return backend.__handlers__[handler_type][handler_label]
    elif len(args) > 0:
        return args[0]
    else:
        raise exc.FrameworkError("handlers['%s']['%s'] does not exist!" %
                                 (handler_type, handler_label))


def list(handler_type):
    """
    Return a list of handlers for a given type.

    :param handler_type: The type of handler (i.e. 'output')
    :returns: List of handlers that match `type`.
    :rtype: list
    :raises: cement.core.exc.FrameworkError

    """
    if handler_type not in backend.__handlers__:
        raise exc.FrameworkError("handler type '%s' does not exist!" %
                                 handler_type)

    res = []
    for label in backend.__handlers__[handler_type]:
        if label == '__interface__':
            continue
        res.append(backend.__handlers__[handler_type][label])
    return res


def define(interface):
    """
    Define a handler based on the provided interface.  Defines a handler type
    based on <interface>.IMeta.label.

    :param interface: The interface class that defines the interface to be
        implemented by handlers.
    :raises: cement.core.exc.InterfaceError
    :raises: cement.core.exc.FrameworkError

    Usage:

    .. code-block:: python

        from cement.core import handler

        handler.define(IDatabaseHandler)

    """
    if not hasattr(interface, 'IMeta'):
        raise exc.InterfaceError("Invalid %s, " % interface +
                                 "missing 'IMeta' class.")
    if not hasattr(interface.IMeta, 'label'):
        raise exc.InterfaceError("Invalid %s, " % interface +
                                 "missing 'IMeta.label' class.")

    LOG.debug("defining handler type '%s' (%s)" %
              (interface.IMeta.label, interface.__name__))

    if interface.IMeta.label in backend.__handlers__:
        raise exc.FrameworkError("Handler type '%s' already defined!" %
                                 interface.IMeta.label)
    backend.__handlers__[interface.IMeta.label] = {'__interface__': interface}


def defined(handler_type):
    """
    Test whether a handler type is defined.

    :param handler_type: The name or 'type' of the handler (I.e. 'logging').
    :returns: True if the handler type is defined, False otherwise.
    :rtype: boolean

    """
    if handler_type in backend.__handlers__:
        return True
    else:
        return False


def register(handler_obj):
    """
    Register a handler object to a handler.  If the same object is already
    registered then no exception is raised, however if a different object
    attempts to be registered to the same name a FrameworkError is
    raised.

    :param handler_obj: The uninstantiated handler object to register.
    :raises: cement.core.exc.InterfaceError
    :raises: cement.core.exc.FrameworkError

    Usage:

    .. code-block:: python

        from cement.core import handler

        class MyDatabaseHandler(object):
            class Meta:
                interface = IDatabase
                label = 'mysql'

            def connect(self):
            ...

        handler.register(MyDatabaseHandler)

    """

    orig_obj = handler_obj

    # for checks
    obj = orig_obj()

    if not hasattr(obj._meta, 'label') or not obj._meta.label:
        raise exc.InterfaceError("Invalid handler %s, " % orig_obj +
                                 "missing '_meta.label'.")
    if not hasattr(obj._meta, 'interface') or not obj._meta.interface:
        raise exc.InterfaceError("Invalid handler %s, " % orig_obj +
                                 "missing '_meta.interface'.")

    # translate dashes to underscores
    orig_obj.Meta.label = re.sub('-', '_', obj._meta.label)
    obj._meta.label = re.sub('-', '_', obj._meta.label)

    handler_type = obj._meta.interface.IMeta.label
    LOG.debug("registering handler '%s' into handlers['%s']['%s']" %
             (orig_obj, handler_type, obj._meta.label))

    if handler_type not in backend.__handlers__:
        raise exc.FrameworkError("Handler type '%s' doesn't exist." %
                                 handler_type)
    if obj._meta.label in backend.__handlers__[handler_type] and \
            backend.__handlers__[handler_type][obj._meta.label] != obj:
        raise exc.FrameworkError("handlers['%s']['%s'] already exists" %
                                (handler_type, obj._meta.label))

    interface = backend.__handlers__[handler_type]['__interface__']
    if hasattr(interface.IMeta, 'validator'):
        interface.IMeta().validator(obj)
    else:
        LOG.debug("Interface '%s' does not have a validator() function!" %
                  interface)

    backend.__handlers__[handler_type][obj.Meta.label] = orig_obj


def registered(handler_type, handler_label):
    """
    Check if a handler is registered.

    :param handler_type: The type of handler (interface label)
    :param handler_label: The label of the handler
    :returns: True if the handler is registered, False otherwise
    :rtype: boolean

    """
    if handler_type in backend.__handlers__ and \
       handler_label in backend.__handlers__[handler_type]:
        return True

    return False


def resolve(handler_type, handler_def, raise_error=True):
    """
    Resolves the actual handler, as it can be either a string identifying
    the handler to load from backend.__handlers__, or it can be an
    instantiated or non-instantiated handler class.

    :param handler_type: The type of handler (aka the interface label)
    :param hander_def: The handler as defined in CementApp.Meta.
    :type handler_def: str, uninstantiated object, or instantiated object
    :param raise_error: Whether or not to raise an exception if unable
        to resolve the handler.
    :type raise_error: boolean
    :returns: The instantiated handler object.

    """
    han = None
    if type(handler_def) == str:
        han = get(handler_type, handler_def)()
    elif hasattr(handler_def, '_meta'):
        if not registered(handler_type, handler_def._meta.label):
            register(handler_def.__class__)
        han = handler_def
    elif hasattr(handler_def, 'Meta'):
        han = handler_def()
        if not registered(handler_type, han._meta.label):
            register(handler_def)

    msg = "Unable to resolve handler '%s' of type '%s'" % \
          (handler_def, handler_type)
    if han is not None:
        return han
    elif han is None and raise_error:
        raise exc.FrameworkError(msg)
    elif han is None:
        LOG.debug(msg)
        return None

########NEW FILE########
__FILENAME__ = hook
"""Cement core hooks module."""

import operator
from ..core import backend, exc
from ..utils.misc import minimal_logger

LOG = minimal_logger(__name__)


def define(name):
    """
    Define a hook namespace that plugins can register hooks in.

    :param name: The name of the hook, stored as hooks['name']
    :raises: cement.core.exc.FrameworkError

    Usage:

    .. code-block:: python

        from cement.core import hook

        hook.define('myhookname_hook')

    """
    LOG.debug("defining hook '%s'" % name)
    if name in backend.__hooks__:
        raise exc.FrameworkError("Hook name '%s' already defined!" % name)
    backend.__hooks__[name] = []


def defined(hook_name):
    """
    Test whether a hook name is defined.

    :param hook_name: The name of the hook.
        I.e. ``my_hook_does_awesome_things``.
    :returns: True if the hook is defined, False otherwise.
    :rtype: boolean

    """
    if hook_name in backend.__hooks__:
        return True
    else:
        return False


def register(name, func, weight=0):
    """
    Register a function to a hook.  The function will be called, in order of
    weight, when the hook is run.

    :param name: The name of the hook to register too.  I.e. ``pre_setup``,
        ``post_run``, etc.
    :param func:    The function to register to the hook.  This is an
        *un-instantiated*, non-instance method, simple function.
    :param weight:  The weight in which to order the hook function.
    :type weight: integer

    Usage:

    .. code-block:: python

        from cement.core import hook

        def my_hook(*args, **kwargs):
            # do something here
            res = 'Something to return'
            return res

        hook.register('post_setup', my_hook)

    """
    if name not in backend.__hooks__:
        LOG.debug("hook name '%s' is not defined! ignoring..." % name)
        return False

    LOG.debug("registering hook '%s' from %s into hooks['%s']" %
              (func.__name__, func.__module__, name))

    # Hooks are as follows: (weight, name, func)
    backend.__hooks__[name].append((int(weight), func.__name__, func))


def run(name, *args, **kwargs):
    """
    Run all defined hooks in the namespace.  Yields the result of each hook
    function run.

    :param name: The name of the hook function.
    :param args: Additional arguments to be passed to the hook functions.
    :param kwargs: Additional keyword arguments to be passed to the hook
        functions.
    :raises: FrameworkError

    Usage:

    .. code-block:: python

        from cement.core import hook

        for result in hook.run('hook_name'):
            # do something with result from each hook function
            ...
    """
    if name not in backend.__hooks__:
        raise exc.FrameworkError("Hook name '%s' is not defined!" % name)

    # Will order based on weight (the first item in the tuple)
    backend.__hooks__[name].sort(key=operator.itemgetter(0))
    for hook in backend.__hooks__[name]:
        LOG.debug("running hook '%s' (%s) from %s" %
                 (name, hook[2], hook[2].__module__))
        res = hook[2](*args, **kwargs)

        # Results are yielded, so you must fun a for loop on it, you can not
        # simply call run_hooks().
        yield res

########NEW FILE########
__FILENAME__ = interface
"""
Cement core interface module.

"""

from ..core import exc

DEFAULT_META = ['interface', 'label', 'config_defaults', 'config_section']


class Interface(object):

    """
    An interface definition class.  All Interfaces should subclass from
    here.  Note that this is not an implementation and should never be
    used directly.
    """

    def __init__(self):
        raise exc.InterfaceError("Interfaces can not be used directly.")


class Attribute(object):

    """
    An interface attribute definition.

    :param description: The description of the attribute.

    """

    def __init__(self, description):
        self.description = description

    def __repr__(self):
        return "<interface.Attribute - '%s'>" % self.description


def validate(interface, obj, members=[], meta=DEFAULT_META):
    """
    A wrapper to validate interfaces.

    :param interface: The interface class to validate against
    :param obj: The object to validate.
    :param members: The object members that must exist.
    :param meta: The meta object members that must exist.
    :raises: cement.core.exc.InterfaceError

    """
    invalid = []

    if hasattr(obj, '_meta') and interface != obj._meta.interface:
        raise exc.InterfaceError("%s does not implement %s." %
                                 (obj, interface))

    for member in members:
        if not hasattr(obj, member):
            invalid.append(member)

    if not hasattr(obj, '_meta'):
        invalid.append("_meta")
    else:
        for member in meta:
            if not hasattr(obj._meta, member):
                invalid.append("_meta.%s" % member)

    if invalid:
        raise exc.InterfaceError("Invalid or missing: %s in %s" %
                                 (invalid, obj))

########NEW FILE########
__FILENAME__ = log
"""
Cement core log module.

"""

from ..core import exc, interface, handler


def log_validator(klass, obj):
    """Validates an handler implementation against the ILog interface."""

    members = [
        '_setup',
        'set_level',
        'get_level',
        'info',
        'warn',
        'error',
        'fatal',
        'debug',
    ]
    interface.validate(ILog, obj, members)


class ILog(interface.Interface):

    """
    This class defines the Log Handler Interface.  Classes that
    implement this handler must provide the methods and attributes defined
    below.

    Implementations do *not* subclass from interfaces.

    Usage:

    .. code-block:: python

        from cement.core import log

        class MyLogHandler(object):
            class Meta:
                interface = log.ILog
                label = 'my_log_handler'
            ...

    """
    # pylint: disable=W0232, C0111, R0903
    class IMeta:

        """Interface meta-data."""

        label = 'log'
        """The string identifier of the interface."""

        validator = log_validator
        """The interface validator function."""

    # Must be provided by the implementation
    Meta = interface.Attribute('Handler Meta-data')

    def _setup(app_obj):
        """
        The _setup function is called during application initialization and
        must 'setup' the handler object making it ready for the framework
        or the application to make further calls to it.

        :param app_obj: The application object.

        """

    def set_level():
        """
        Set the log level.  Must except atleast one of:
            ``['INFO', 'WARN', 'ERROR', 'DEBUG', or 'FATAL']``.

        """

    def get_level():
        """Return a string representation of the log level."""

    def info(msg):
        """
        Log to the 'INFO' facility.

        :param msg: The message to log.

        """

    def warn(self, msg):
        """
        Log to the 'WARN' facility.

        :param msg: The message to log.

        """

    def error(self, msg):
        """
        Log to the 'ERROR' facility.

        :param msg: The message to log.

        """

    def fatal(self, msg):
        """
        Log to the 'FATAL' facility.

        :param msg: The message to log.

        """

    def debug(self, msg):
        """
        Log to the 'DEBUG' facility.

        :param msg: The message to log.

        """


class CementLogHandler(handler.CementBaseHandler):

    """
    Base class that all Log Handlers should sub-class from.

    """
    class Meta:

        """
        Handler meta-data (can be passed as keyword arguments to the parent
        class).
        """

        label = None
        """The string identifier of this handler."""

        interface = ILog
        """The interface that this class implements."""

    def __init__(self, *args, **kw):
        super(CementLogHandler, self).__init__(*args, **kw)

########NEW FILE########
__FILENAME__ = meta
"""Cement core meta functionality."""


class Meta(object):

    """
    Model that acts as a container class for a meta attributes for a larger
    class. It stuffs any kwarg it gets in it's init as an attribute of itself.

    """

    def __init__(self, **kwargs):
        self._merge(kwargs)

    def _merge(self, dict_obj):
        for key in dict_obj.keys():
            setattr(self, key, dict_obj[key])


class MetaMixin(object):

    """
    Mixin that provides the Meta class support to add settings to instances
    of slumber objects. Meta settings cannot start with a _.

    """

    def __init__(self, *args, **kwargs):
        # Get a List of all the Classes we in our MRO, find any attribute named
        #     Meta on them, and then merge them together in order of MRO
        metas = reversed([x.Meta for x in self.__class__.mro()
                          if hasattr(x, "Meta")])
        final_meta = {}

        # Merge the Meta classes into one dict
        for meta in metas:
            final_meta.update(dict([x for x in meta.__dict__.items()
                                    if not x[0].startswith("_")]))

        # Update the final Meta with any kwargs passed in
        for key in final_meta.keys():
            if key in kwargs:
                final_meta[key] = kwargs.pop(key)

        self._meta = Meta(**final_meta)

        # FIX ME: object.__init__() doesn't take params without exception
        super(MetaMixin, self).__init__()

########NEW FILE########
__FILENAME__ = output
"""Cement core output module."""

import os
import sys
import pkgutil
from ..core import backend, exc, interface, handler
from ..utils.misc import minimal_logger
from ..utils import fs

LOG = minimal_logger(__name__)


def output_validator(klass, obj):
    """Validates an handler implementation against the IOutput interface."""

    members = [
        '_setup',
        'render',
    ]
    interface.validate(IOutput, obj, members)


class IOutput(interface.Interface):

    """
    This class defines the Output Handler Interface.  Classes that
    implement this handler must provide the methods and attributes defined
    below.

    Implementations do *not* subclass from interfaces.

    Usage:

    .. code-block:: python

        from cement.core import output

        class MyOutputHandler(object):
            class Meta:
                interface = output.IOutput
                label = 'my_output_handler'
            ...

    """
    # pylint: disable=W0232, C0111, R0903
    class IMeta:

        """Interface meta-data."""

        label = 'output'
        """The string identifier of the interface."""

        validator = output_validator
        """The interface validator function."""

    # Must be provided by the implementation
    Meta = interface.Attribute('Handler meta-data')

    def _setup(app_obj):
        """
        The _setup function is called during application initialization and
        must 'setup' the handler object making it ready for the framework
        or the application to make further calls to it.

        :param app_obj: The application object.

        """

    def render(data_dict):
        """
        Render the data_dict into output in some fashion.

        :param data_dict: The dictionary whose data we need to render into
            output.
        :returns: string or unicode string or None

        """


class CementOutputHandler(handler.CementBaseHandler):

    """
    Base class that all Output Handlers should sub-class from.

    """
    class Meta:

        """
        Handler meta-data (can be passed as keyword arguments to the parent
        class).
        """

        label = None
        """The string identifier of this handler."""

        interface = IOutput
        """The interface that this class implements."""

    def __init__(self, *args, **kw):
        super(CementOutputHandler, self).__init__(*args, **kw)


class TemplateOutputHandler(CementOutputHandler):

    """
    Base class for template base output handlers.

    """

    def _load_template_from_file(self, template_path):
        template_prefix = self.app._meta.template_dir.rstrip('/')
        template_path = template_path.lstrip('/')
        full_path = fs.abspath(os.path.join(template_prefix, template_path))
        LOG.debug("attemping to load output template from file %s" %
                  full_path)
        if os.path.exists(full_path):
            content = open(full_path, 'r').read()
            LOG.debug("loaded output template from file %s" %
                      full_path)
            return content
        else:
            LOG.debug("output template file %s does not exist" %
                      full_path)
            return None

    def _load_template_from_module(self, template_path):
        template_module = self.app._meta.template_module
        template_path = template_path.lstrip('/')

        LOG.debug("attemping to load output template '%s' from module %s" %
                 (template_path, template_module))

        # see if the module exists first
        if template_module not in sys.modules:
            try:
                __import__(template_module, globals(), locals(), [], 0)
            except ImportError as e:
                LOG.debug("unable to import template module '%s'."
                          % template_module)
                return None

        # get the template content
        try:
            content = pkgutil.get_data(template_module, template_path)
            LOG.debug("loaded output template '%s' from module %s" %
                     (template_path, template_module))
            return content
        except IOError as e:
            LOG.debug("output template '%s' does not exist in module %s" %
                     (template_path, template_module))
            return None

    def load_template(self, template_path):
        """
        Loads a template file first from ``self.app._meta.template_dir`` and
        secondly from ``self.app._meta.template_module``.  The
        ``template_dir`` has presedence.

        :param template_path: The secondary path of the template *after*
            either ``template_module`` or ``template_dir`` prefix (set via
            CementApp.Meta)
        :returns: The content of the template (str)
        :raises: FrameworkError if the template does not exist in either the
            ``template_module`` or ``template_dir``.
        """
        if not template_path:
            raise exc.FrameworkError("Invalid template path '%s'." %
                                     template_path)

        # first attempt to load from file
        content = self._load_template_from_file(template_path)
        if content is None:
            # second attempt to load from module
            content = self._load_template_from_module(template_path)

        # if content is None, that means we didn't find a template file in
        # either and that is an exception
        if content is not None:
            return content
        else:
            raise exc.FrameworkError("Could not locate template: %s" %
                                     template_path)

########NEW FILE########
__FILENAME__ = plugin
"""Cement core plugins module."""

from ..core import backend, exc, interface, handler
from ..utils.misc import minimal_logger

LOG = minimal_logger(__name__)


def plugin_validator(klass, obj):
    """Validates an handler implementation against the IPlugin interface."""

    members = [
        '_setup',
        'load_plugin',
        'load_plugins',
        'get_loaded_plugins',
        'get_enabled_plugins',
        'get_disabled_plugins',
    ]
    interface.validate(IPlugin, obj, members)


class IPlugin(interface.Interface):

    """
    This class defines the Plugin Handler Interface.  Classes that
    implement this handler must provide the methods and attributes defined
    below.

    Implementations do *not* subclass from interfaces.

    Usage:

    .. code-block:: python

        from cement.core import plugin

        class MyPluginHandler(object):
            class Meta:
                interface = plugin.IPlugin
                label = 'my_plugin_handler'
            ...

    """
    # pylint: disable=W0232, C0111, R0903
    class IMeta:
        label = 'plugin'
        validator = plugin_validator

    # Must be provided by the implementation
    Meta = interface.Attribute('Handler meta-data')

    def _setup(app_obj):
        """
        The _setup function is called during application initialization and
        must 'setup' the handler object making it ready for the framework
        or the application to make further calls to it.

        :param app_obj: The application object.

        """

    def load_plugin(plugin_name):
        """
        Load a plugin whose name is 'plugin_name'.

        :param plugin_name: The name of the plugin to load.

        """

    def load_plugins(plugin_list):
        """
        Load all plugins from plugin_list.

        :param plugin_list: A list of plugin names to load.

        """

    def get_loaded_plugins():
        """Returns a list of plugins that have been loaded."""

    def get_enabled_plugins():
        """Returns a list of plugins that are enabled in the config."""

    def get_disabled_plugins():
        """Returns a list of plugins that are disabled in the config."""


class CementPluginHandler(handler.CementBaseHandler):

    """
    Base class that all Plugin Handlers should sub-class from.

    """

    class Meta:

        """
        Handler meta-data (can be passed as keyword arguments to the parent
        class).
        """

        label = None
        """The string identifier of this handler."""

        interface = IPlugin
        """The interface that this class implements."""

    def __init__(self, *args, **kw):
        super(CementPluginHandler, self).__init__(*args, **kw)

########NEW FILE########
__FILENAME__ = ext_argparse
"""ArgParse Framework Extension"""

from argparse import ArgumentParser
from ..core import backend, arg, handler
from ..utils.misc import minimal_logger

LOG = minimal_logger(__name__)


class ArgParseArgumentHandler(arg.CementArgumentHandler, ArgumentParser):

    """
    This class implements the :ref:`IArgument <cement.core.arg>`
    interface, and sub-classes from `argparse.ArgumentParser
    <http://docs.python.org/dev/library/argparse.html>`_.
    Please reference the argparse documentation for full usage of the
    class.

    Arguments and Keyword arguments are passed directly to ArgumentParser
    on initialization.
    """

    class Meta:

        """Handler meta-data."""

        interface = arg.IArgument
        """The interface that this class implements."""

        label = 'argparse'
        """The string identifier of the handler."""

    def __init__(self, *args, **kw):
        super(ArgParseArgumentHandler, self).__init__(*args, **kw)
        self.config = None

    def parse(self, arg_list):
        """
        Parse a list of arguments, and return them as an object.  Meaning an
        argument name of 'foo' will be stored as parsed_args.foo.

        :param arg_list: A list of arguments (generally sys.argv) to be
         parsed.
        :returns: object whose members are the arguments parsed.

        """
        return self.parse_args(arg_list)

    def add_argument(self, *args, **kw):
        """
        Add an argument to the parser.  Arguments and keyword arguments are
        passed directly to ArgumentParser.add_argument().

        """
        return super(ArgumentParser, self).add_argument(*args, **kw)


def load():
    """Called by the framework when the extension is 'loaded'."""

    handler.register(ArgParseArgumentHandler)

########NEW FILE########
__FILENAME__ = ext_configobj
"""ConfigObj Framework Extension."""

import os
import sys
from ..core import config, exc, handler
from ..utils.misc import minimal_logger

if sys.version_info[0] >= 3:
    raise exc.CementRuntimeError('ConfigObj does not support Python 3.') \
        # pragma: no cover

from configobj import ConfigObj

LOG = minimal_logger(__name__)


class ConfigObjConfigHandler(config.CementConfigHandler, ConfigObj):
    """
    This class implements the :ref:`IConfig <cement.core.config>`
    interface, and sub-classes from `configobj.ConfigObj
    <http://www.voidspace.org.uk/python/configobj.html>`_,
    which is an external library and not included with Python. Please
    reference the ConfigObj documentation for full usage of the class.

    Arguments and keyword arguments are passed directly to ConfigObj
    on initialization.

    """
    class Meta:
        interface = config.IConfig
        label = 'configobj'

    def __init__(self, *args, **kw):
        super(ConfigObjConfigHandler, self).__init__(*args, **kw)
        self.app = None

    def _setup(self, app_obj):
        self.app = app_obj

    def get_sections(self):
        """
        Return a list of [section] that exist in the configuration.

        :returns: list
        """
        return self.sections

    def get_section_dict(self, section):
        """
        Return a dict representation of a section.

        :param section: The section of the configuration.
         I.e. ``[block_section]``
        :returns: dict

        """
        dict_obj = dict()
        for key in self.keys(section):
            dict_obj[key] = self.get(section, key)
        return dict_obj

    def parse_file(self, file_path):
        """
        Parse config file settings from file_path, overwriting existing
        config settings.  If the file does not exist, returns False.

        :param file_path: The file system path to the configuration file.
        :returns: bool

        """
        file_path = os.path.abspath(os.path.expanduser(file_path))
        if os.path.exists(file_path):
            LOG.debug("config file '%s' exists, loading settings..." %
                      file_path)
            _c = ConfigObj(file_path)
            self.merge(_c.dict())
            return True
        else:
            LOG.debug("config file '%s' does not exist, skipping..." %
                      file_path)
            return False

    def keys(self, section):
        """
        Return a list of keys for a given section.

        :param section: The configuration [section].

        """
        return self[section].keys()

    def get(self, section, key):
        """
        Get a value for a given key under section.

        :param section: The configuration [section].
        :param key: The configuration key under the section.
        :returns: unknown (the value of the key)

        """
        return self[section][key]

    def set(self, section, key, value):
        """
        Set a configuration key value under [section].

        :param section: The configuration [section].
        :param key: The configuration key under the section.
        :param value: The value to set the key to.
        :returns: None
        """
        self[section][key] = value

    def has_section(self, section):
        """
        Return True/False whether the configuration [section] exists.

        :param section: The section to check for.
        :returns: bool

        """
        if section in self.get_sections():
            return True
        else:
            return False

    def add_section(self, section):
        """
        Add a section to the configuration.

        :param section: The configuration [section] to add.

        """
        if not self.has_section(section):
            self[section] = dict()

    def merge(self, dict_obj, override=True):
        """
        Merge a dictionary into our config.  If override is True then
        existing config values are overridden by those passed in.

        :param dict_obj: A dictionary of configuration keys/values to merge
         into our existing config (self).
        :param override: Whether or not to override existing values in the
         config.
        :returns: None

        """
        for section in list(dict_obj.keys()):
            if type(dict_obj[section]) == dict:
                if not section in self.get_sections():
                    self.add_section(section)

                for key in list(dict_obj[section].keys()):
                    if override:
                        self.set(section, key, dict_obj[section][key])
                    else:
                        # only set it if the key doesn't exist
                        if key not in self.keys(section):
                            self.set(section, key, dict_obj[section][key])

                # we don't support nested config blocks, so no need to go
                # further down to more nested dicts.


def load():
    """Called by the framework when the extension is 'loaded'."""
    handler.register(ConfigObjConfigHandler)

########NEW FILE########
__FILENAME__ = ext_configparser
"""ConfigParser Framework Extension."""

import os
import sys
if sys.version_info[0] < 3:
    from ConfigParser import RawConfigParser  # pragma: no cover
else:
    from configparser import RawConfigParser  # pragma: no cover

from ..core import backend, config, handler
from ..utils.misc import minimal_logger

LOG = minimal_logger(__name__)


class ConfigParserConfigHandler(config.CementConfigHandler, RawConfigParser):

    """
    This class is an implementation of the :ref:`IConfig <cement.core.config>`
    interface.  It handles configuration file parsing and the like by
    sub-classing from the standard `ConfigParser
    <http://docs.python.org/library/configparser.html>`_
    library.  Please see the ConfigParser documentation for full usage of the
    class.

    Additional arguments and keyword arguments are passed directly to
    RawConfigParser on initialization.
    """
    class Meta:

        """Handler meta-data."""

        interface = config.IConfig
        """The interface that this handler implements."""

        label = 'configparser'
        """The string identifier of this handler."""

    def __init__(self, *args, **kw):
        # ConfigParser is not a new style object, so you can't call super()
        # super(ConfigParserConfigHandler, self).__init__(*args, **kw)
        RawConfigParser.__init__(self, *args, **kw)
        super(ConfigParserConfigHandler, self).__init__(*args, **kw)
        self.app = None

    def merge(self, dict_obj, override=True):
        """
        Merge a dictionary into our config.  If override is True then
        existing config values are overridden by those passed in.

        :param dict_obj: A dictionary of configuration keys/values to merge
            into our existing config (self).

        :param override:  Whether or not to override existing values in the
            config.

        """
        for section in list(dict_obj.keys()):
            if type(dict_obj[section]) == dict:
                if not section in self.get_sections():
                    self.add_section(section)

                for key in list(dict_obj[section].keys()):
                    if override:
                        self.set(section, key, dict_obj[section][key])
                    else:
                        # only set it if the key doesn't exist
                        if not key in self.keys(section):
                            self.set(section, key, dict_obj[section][key])

                # we don't support nested config blocks, so no need to go
                # further down to more nested dicts.

    def parse_file(self, file_path):
        """
        Parse config file settings from file_path, overwriting existing
        config settings.  If the file does not exist, returns False.

        :param file_path: The file system path to the configuration file.
        :returns: boolean

        """
        file_path = os.path.abspath(os.path.expanduser(file_path))
        if os.path.exists(file_path):
            LOG.debug("config file '%s' exists, loading settings..." %
                      file_path)
            self.read(file_path)
            return True
        else:
            LOG.debug("config file '%s' does not exist, skipping..." %
                      file_path)
            return False

    def keys(self, section):
        """
        Return a list of keys within 'section'.

        :param section: The config section (I.e. [block_section]).
        :returns: List of keys in the `section`.
        :rtype: list

        """
        return self.options(section)

    def get_sections(self):
        """
        Return a list of configuration sections or [blocks].

        :returns: List of sections.
        :rtype: list

        """
        return self.sections()

    def get_section_dict(self, section):
        """
        Return a dict representation of a section.

        :param section: The section of the configuration.
         I.e. [block_section]
        :returns: Dictionary reprisentation of the config section.
        :rtype: dict

        """
        dict_obj = dict()
        for key in self.keys(section):
            dict_obj[key] = self.get(section, key)
        return dict_obj

    def add_section(self, section):
        """
        Adds a block section to the config.

        :param section: The section to add.

        """
        super(ConfigParserConfigHandler, self).add_section(section)


def load():
    """Called by the framework when the extension is 'loaded'."""

    handler.register(ConfigParserConfigHandler)

########NEW FILE########
__FILENAME__ = ext_daemon
"""
The Daemon Framework Extension enables applications built on Cement to easily
perform standard 'daemon' functions.

Requirements
------------

 * Python 2.6+, Python 3+

Features
--------

 * Configurable runtime user and group
 * Adds the --daemon command line option
 * Adds app.daemonize() function to trigger daemon functionality where
   necessary (either in a cement pre_run hook or an application controller
   sub-command, etc).
 * Manages a pid file including cleanup on app.close()

Configuration
-------------

The daemon extension is configurable with the following settings under the
[daemon] section.

    * **user** - The user name to run the process as.
      Default: os.environ['USER']
    * **group** - The group name to run the process as.
      Default: The primary group of the 'user'.
    * **dir** - The directory to run the process in.
      Default: /
    * **pid_file** - The filesystem path to store the PID (Process ID) file.
      Default: None
    * **umask** - The umask value to pass to os.umask().
      Default: 0



Configurations can be passed as defaults to a CementApp:

.. code-block:: python

    from cement.core import foundation
    from cement.utils.misc import init_defaults

    defaults = init_defaults('myapp', 'daemon')
    defaults['daemon']['user'] = 'myuser'
    defaults['daemon']['group'] = 'mygroup'
    defaults['daemon']['dir'] = '/var/lib/myapp/'
    defaults['daemon']['pid_file'] = '/var/run/myapp/myapp.pid'
    defaults['daemon']['umask'] = 0

    app = foundation.CementApp('myapp', config_defaults=defaults)



Application defaults are then overridden by configurations parsed via a
[daemon] config section in any of the applications configuration paths.  An
example configuration block would look like:

.. code-block:: text

    [daemon]
    user = myuser
    group = mygroup
    dir = /var/lib/myapp/
    pid_file = /var/run/myapp/myapp.pid
    umask = 0


Usage
-----

The following example shows how to add the daemon extension, as well as
trigger daemon functionality before app.run() is called.

.. code-block:: python

    from time import sleep
    from cement.core import foundation

    app = foundation.CementApp('myapp', extensions=['daemon'])

    try:
        app.setup()
        app.daemonize()
        app.run()

        count = 0
        while True:
            count = count + 1
            print('Iteration: %s' % count)
            sleep(10)
    finally:
        app.close()


An alternative to the above is to put app.daemonize() within a framework hook:

.. code-block:: python

    from cement.core import hook

    def make_daemon(app):
        app.daemonize()

    hook.register('pre_run', make_daemon)


Finally, some applications may prefer to only daemonize certain sub-commands
rather than the entire parent application.  For example:

.. code-block:: python

    from cement.core import foundation, controller, handler

    class MyAppBaseController(controller.CementBaseController):
        class Meta:
            label = 'base'

        @controller.expose(help="run the daemon command.")
        def run_forever(self):
            from time import sleep
            self.app.daemonize()

            count = 0
            while True:
                count = count + 1
                print(count)
                sleep(10)

    app = foundation.CementApp('myapp',
        extensions=['daemon'],
        base_controller=MyAppBaseController,
        )

    try:
        app.setup()
        app.run()
    finally:
        app.close()


By default, even after app.daemonize() is called... the application will
continue to run in the foreground, but will still manage the pid and
user/group switching.  To detach a process and send it to the background you
simply pass the '--daemon' option at command line.

.. code-block:: text

    $ python example.py --daemon

    $ ps -x | grep example
    37421 ??         0:00.01 python example2.py --daemon
    37452 ttys000    0:00.00 grep example

"""

import os
import sys
import io
import pwd
import grp
from ..core import handler, hook, exc
from ..utils.misc import minimal_logger

LOG = minimal_logger(__name__)
LOG = minimal_logger(__name__)
CEMENT_DAEMON_ENV = None
CEMENT_DAEMON_APP = None


class Environment(object):
    """
    This class provides a mechanism for altering the running processes
    environment.

    Optional Arguments:

        stdin
            A file to read STDIN from.  Default: /dev/null

        stdout
            A file to write STDOUT to.  Default: /dev/null

        stderr
            A file to write STDERR to.  Default: /dev/null

        dir
            The directory to run the process in.

        pid_file
            The filesystem path to where the PID (Process ID) should be
            written to.  Default: None

        user
            The user name to run the process as.  Default: os.environ['USER']

        group
            The group name to run the process as.  Default: The primary group
            of os.environ['USER'].

        umask
            The umask to pass to os.umask().  Default: 0

    """

    def __init__(self, **kw):
        self.stdin = kw.get('stdin', '/dev/null')
        self.stdout = kw.get('stdout', '/dev/null')
        self.stderr = kw.get('stderr', '/dev/null')
        self.dir = kw.get('dir', os.curdir)
        self.pid_file = kw.get('pid_file', None)
        self.umask = kw.get('umask', 0)
        self.user = kw.get('user', os.environ['USER'])

        # clean up
        self.dir = os.path.abspath(os.path.expanduser(self.dir))
        if self.pid_file:
            self.pid_file = os.path.abspath(os.path.expanduser(self.pid_file))

        try:
            self.user = pwd.getpwnam(self.user)
        except KeyError as e:
            raise exc.FrameworkError("Daemon user '%s' doesn't exist." %
                                     self.user)

        try:
            self.group = kw.get('group',
                                grp.getgrgid(self.user.pw_gid).gr_name)
            self.group = grp.getgrnam(self.group)
        except KeyError as e:
            raise exc.FrameworkError("Daemon group '%s' doesn't exist." %
                                     self.group)

    def _write_pid_file(self):
        """
        Writes os.getpid() out to self.pid_file.
        """
        pid = str(os.getpid())
        LOG.debug('writing pid (%s) out to %s' % (pid, self.pid_file))

        # setup pid
        if self.pid_file:
            f = open(self.pid_file, 'w')
            f.write(pid)
            f.close()

            os.chown(self.pid_file, self.user.pw_uid, self.group.gr_gid)

    def switch(self):
        """
        Switch the current process's user/group to self.user, and
        self.group.  Change directory to self.dir, and write the
        current pid out to self.pid_file.
        """
        # set the running uid/gid
        LOG.debug('setting process uid(%s) and gid(%s)' %
                 (self.user.pw_uid, self.group.gr_gid))
        os.setgid(self.group.gr_gid)
        os.setuid(self.user.pw_uid)
        os.environ['HOME'] = self.user.pw_dir
        os.chdir(self.dir)
        if self.pid_file and os.path.exists(self.pid_file):
            raise exc.FrameworkError("Process already running (%s)" %
                                     self.pid_file)
        else:
            self._write_pid_file()

    def daemonize(self):  # pragma: no cover
        """
        Fork the current process into a daemon.

        References:

        UNIX Programming FAQ
            1.7 How do I get my program to act like a daemon?
            http://www.unixguide.net/unix/programming/1.7.shtml
            http://www.faqs.org/faqs/unix-faq/programmer/faq/

        Advanced Programming in the Unix Environment
            W. Richard Stevens, 1992, Addison-Wesley, ISBN 0-201-56317-7.

        """
        LOG.debug('attempting to daemonize the current process')
        # Do first fork.
        try:
            pid = os.fork()
            if pid > 0:
                LOG.debug('successfully detached from first parent')
                os._exit(os.EX_OK)
        except OSError as e:
            sys.stderr.write("Fork #1 failed: (%d) %s\n" %
                            (e.errno, e.strerror))
            sys.exit(1)

        # Decouple from parent environment.
        os.chdir(self.dir)
        os.umask(int(self.umask))
        os.setsid()

        # Do second fork.
        try:
            pid = os.fork()
            if pid > 0:
                LOG.debug('successfully detached from second parent')
                os._exit(os.EX_OK)
        except OSError as e:
            sys.stderr.write("Fork #2 failed: (%d) %s\n" %
                            (e.errno, e.strerror))
            sys.exit(1)

        # Redirect standard file descriptors.
        stdin = open(self.stdin, 'r')
        stdout = open(self.stdout, 'a+')
        stderr = open(self.stderr, 'a+')

        if hasattr(sys.stdin, 'fileno'):
            try:
                os.dup2(stdin.fileno(), sys.stdin.fileno())
            except io.UnsupportedOperation as e:
                # FIXME: ?
                pass
        if hasattr(sys.stdout, 'fileno'):
            try:
                os.dup2(stdout.fileno(), sys.stdout.fileno())
            except io.UnsupportedOperation as e:
                # FIXME: ?
                pass
        if hasattr(sys.stderr, 'fileno'):
            try:
                os.dup2(stderr.fileno(), sys.stderr.fileno())
            except io.UnsupportedOperation as e:
                # FIXME: ?
                pass

        # Update our pid file
        self._write_pid_file()


def daemonize():  # pragma: no cover
    """
    This function switches the running user/group to that configured in
    config['daemon']['user'] and config['daemon']['group'].  The default user
    is os.environ['USER'] and the default group is that user's primary group.
    A pid_file and directory to run in is also passed to the environment.

    It is important to note that with the daemon extension enabled, the
    environment will switch user/group/set pid/etc regardless of whether
    the --daemon option was passed at command line or not.  However, the
    process will only 'daemonize' if the option is passed to do so.  This
    allows the program to run exactly the same in forground or background.

    """
    # We want to honor the runtime user/group/etc even if --daemon is not
    # passed... but only daemonize if it is.
    global CEMENT_DAEMON_ENV
    global CEMENT_DAEMON_APP

    app = CEMENT_DAEMON_APP
    CEMENT_DAEMON_ENV = Environment(
        user=app.config.get('daemon', 'user'),
        group=app.config.get('daemon', 'group'),
        pid_file=app.config.get('daemon', 'pid_file'),
        dir=app.config.get('daemon', 'dir'),
        umask=app.config.get('daemon', 'umask'),
    )

    CEMENT_DAEMON_ENV.switch()

    if '--daemon' in app.argv:
        CEMENT_DAEMON_ENV.daemonize()


def extend_app(app):
    """
    Adds the '--daemon' argument to the argument object, and sets the default
    [daemon] config section options.

    """
    global CEMENT_DAEMON_APP
    CEMENT_DAEMON_APP = app

    app.args.add_argument('--daemon', dest='daemon',
                          action='store_true', help='daemonize the process')

    # Add default config
    user = pwd.getpwnam(os.environ['USER'])
    group = grp.getgrgid(user.pw_gid)

    defaults = dict()
    defaults['daemon'] = dict()
    defaults['daemon']['user'] = user.pw_name
    defaults['daemon']['group'] = group.gr_name
    defaults['daemon']['pid_file'] = None
    defaults['daemon']['dir'] = '/'
    defaults['daemon']['umask'] = 0
    app.config.merge(defaults, override=False)
    app.extend('daemonize', daemonize)


def cleanup(app):  # pragma: no cover
    """
    After application run time, this hook just attempts to clean up the
    pid_file if one was set, and exists.

    """
    global CEMENT_DAEMON_ENV

    if CEMENT_DAEMON_ENV and CEMENT_DAEMON_ENV.pid_file:
        if os.path.exists(CEMENT_DAEMON_ENV.pid_file):
            LOG.debug('Cleaning up pid_file...')
            pid = open(CEMENT_DAEMON_ENV.pid_file, 'r').read().strip()

            # only remove it if we created it.
            if int(pid) == int(os.getpid()):
                os.remove(CEMENT_DAEMON_ENV.pid_file)


def load():
    hook.register('post_setup', extend_app)
    hook.register('pre_close', cleanup)

########NEW FILE########
__FILENAME__ = ext_genshi
"""Genshi extension module."""

import sys
from ..core import output, exc, handler
from ..utils.misc import minimal_logger

if sys.version_info[0] >= 3:
    raise exc.CementRuntimeError('Genshi does not support Python 3.') \
        # pragma: no cover

from genshi.template import NewTextTemplate
LOG = minimal_logger(__name__)


class GenshiOutputHandler(output.TemplateOutputHandler):
    """
    This class implements the :ref:`IOutput <cement.core.output>`
    interface.  It provides text output from template and uses the
    `Genshi Text Templating Language
    <http://genshi.edgewall.org/wiki/Documentation/text-templates.html>`_.
    **Note** This extension has an external dependency on ``genshi``.  You
    must include ``genshi`` in your applications dependencies as Cement
    explicitly does *not* include external dependencies for optional
    extensions.

    Usage:

    .. code-block:: python

        from cement.core import foundation

        class MyApp(foundation.CementApp):
            class Meta:
                label = 'myapp'
                extensions = ['genshi']
                output_handler = 'genshi'
                template_module = 'myapp.templates'
                template_dir = '/usr/lib/myapp/templates'
        # ...

    From here, you would then put a Genshi template file in
    ``myapp/templates/my_template.genshi`` and then render a data dictionary
    with it:

    .. code-block:: python

        # via the app object
        myapp.render(some_data_dict, 'my_template.genshi')

        # or from within a controller or handler
        self.app.render(some_data_dict, 'my_template.genshi')



    Configuration:

    This extension honors the ``template_dir`` configuration option under the
    base configuration section of any application configuration file.  It
    also honors the ``template_module`` and ``template_dir`` meta options
    under the main application object.

    """

    class Meta:
        interface = output.IOutput
        label = 'genshi'

    def render(self, data_dict, template):
        """
        Take a data dictionary and render it using the given template file.

        Required Arguments:

        :param data_dict: The data dictionary to render.
        :param template: The path to the template, after the
            ``template_module`` or ``template_dir`` prefix as defined in the
            application.
        :returns: str (the rendered template text)

        """
        LOG.debug("rendering output using '%s' as a template." % template)
        content = self.load_template(template)
        tmpl = NewTextTemplate(content)
        return tmpl.generate(**data_dict).render()


def load():
    handler.register(GenshiOutputHandler)

########NEW FILE########
__FILENAME__ = ext_json
"""JSON Framework Extension"""

import sys
import json
from ..core import output, backend, hook, handler
from ..utils.misc import minimal_logger

LOG = minimal_logger(__name__)


class JsonOutputHandler(output.CementOutputHandler):

    """
    This class implements the :ref:`IOutput <cement.core.output>`
    interface.  It provides JSON output from a data dictionary using the
    `json <http://docs.python.org/library/json.html>`_ module of the standard
    library.

    Note: The cement framework detects the '--json' option and suppresses
    output (same as if passing --quiet).  Therefore, if debugging or
    troubleshooting issues you must pass the --debug option to see whats
    going on.

    """
    class Meta:

        """Handler meta-data"""

        interface = output.IOutput
        """The interface this class implements."""

        label = 'json'
        """The string identifier of this handler."""

    def __init__(self, *args, **kw):
        super(JsonOutputHandler, self).__init__(*args, **kw)

    def render(self, data_dict, template=None):
        """
        Take a data dictionary and render it as Json output.  Note that the
        template option is received here per the interface, however this
        handler just ignores it.

        :param data_dict: The data dictionary to render.
        :param template: This option is completely ignored.
        :returns: A JSON encoded string.
        :rtype: str

        """
        LOG.debug("rendering output as Json via %s" % self.__module__)
        sys.stdout = backend.__saved_stdout__
        sys.stderr = backend.__saved_stderr__
        return json.dumps(data_dict)


def add_json_option(app):
    """
    This is a ``post_setup`` hook that adds the ``--json`` argument to the
    argument object.

    :param app: The application object.

    """
    app.args.add_argument('--json', dest='output_handler',
                          action='store_const',
                          help='toggle json output handler',
                          const='json')


def set_output_handler(app):
    """
    This is a ``pre_run`` hook that overrides the configured output handler
    if ``--json`` is passed at the command line.

    :param app: The application object.

    """
    if '--json' in app._meta.argv:
        app._meta.output_handler = 'json'
        app._setup_output_handler()


def load():
    """Called by the framework when the extension is 'loaded'."""
    hook.register('post_setup', add_json_option)
    hook.register('pre_run', set_output_handler)
    handler.register(JsonOutputHandler)

########NEW FILE########
__FILENAME__ = ext_logging
"""Logging Framework Extension"""

import os
import logging
from ..core import exc, log, handler
from ..utils.misc import is_true
from ..utils import fs

try:                                        # pragma: no cover
    NullHandler = logging.NullHandler       # pragma: no cover
except AttributeError as e:                 # pragma: no cover
    # Not supported on Python < 3.1/2.7     # pragma: no cover
    class NullHandler(logging.Handler):     # pragma: no cover

        def handle(self, record):           # pragma: no cover
            pass                            # pragma: no cover
                                            # pragma: no cover

        def emit(self, record):             # pragma: no cover
            pass                            # pragma: no cover
                                            # pragma: no cover

        def createLock(self):               # pragma: no cover
            self.lock = None                # pragma: no cover


class LoggingLogHandler(log.CementLogHandler):

    """
    This class is an implementation of the :ref:`ILog <cement.core.log>`
    interface, and sets up the logging facility using the standard Python
    `logging <http://docs.python.org/library/logging.html>`_ module.

    Configuration Options

    The following configuration options are recognized in this class
    (assuming that Meta.config_section is `log`):

        log.level

        log.file

        log.to_console

        log.rotate

        log.max_bytes

        log.max_files


    A sample config section (in any config file) might look like:

    .. code-block:: text

        [log]
        file = /path/to/config/file
        level = info
        to_console = true
        rotate = true
        max_bytes = 512000
        max_files = 4

    """

    #: Handler meta-data.
    class Meta:
        #: The interface that this class implements.
        interface = log.ILog

        #: The string identifier of this handler.
        label = 'logging'

        #: The logging namespace.
        #:
        #: Note: Although Meta.namespace defaults to None, Cement will set
        #: this to the application label (CementApp.Meta.label) if not set
        #: during setup.
        namespace = None

        #: The logging format for the file logger.
        file_format = "%(asctime)s (%(levelname)s) %(namespace)s : " + \
                      "%(message)s"

        #: The logging format for the consoler logger.
        console_format = "%(levelname)s: %(message)s"

        #: The logging format for both file and console if ``debug==True``.
        debug_format = "%(asctime)s (%(levelname)s) %(namespace)s : " + \
                       "%(message)s"

        #: List of logger namespaces to clear.  Useful when imported software
        #: also sets up logging and you end up with duplicate log entries.
        #:
        #: Changes in Cement 2.1.3.  Previous versions only supported
        #: `clear_loggers` as a boolean, but did fully support clearing
        #: non-app logging namespaces.
        clear_loggers = []

        #: The section of the application configuration that holds this
        #: handlers configuration.
        config_section = 'log'

        #: The default configuration dictionary to populate the ``log``
        #: section.
        config_defaults = dict(
            file=None,
            level='INFO',
            to_console=True,
            rotate=False,
            max_bytes=512000,
            max_files=4,
        )

    levels = ['INFO', 'WARN', 'ERROR', 'DEBUG', 'FATAL']

    def __init__(self, *args, **kw):
        super(LoggingLogHandler, self).__init__(*args, **kw)
        self.app = None

    def _setup(self, app_obj):
        super(LoggingLogHandler, self)._setup(app_obj)
        if self._meta.namespace is None:
            self._meta.namespace = "%s" % self.app._meta.label

        self.backend = logging.getLogger("cement:app:%s" %
                                         self._meta.namespace)

        # hack for application debugging
        if is_true(self.app._meta.debug):
            self.app.config.set(self._meta.config_section, 'level', 'DEBUG')

        level = self.app.config.get(self._meta.config_section, 'level')
        self.set_level(level)

        self.debug("logging initialized for '%s' using %s" %
                  (self._meta.namespace, self.__class__.__name__))

    def set_level(self, level):
        """
        Set the log level.  Must be one of the log levels configured in
        self.levels which are ``['INFO', 'WARN', 'ERROR', 'DEBUG', 'FATAL']``.

        :param level: The log level to set.

        """
        self.clear_loggers(self._meta.namespace)
        for namespace in self._meta.clear_loggers:
            self.clear_loggers(namespace)

        level = level.upper()
        if level not in self.levels:
            level = 'INFO'
        level = getattr(logging, level.upper())

        self.backend.setLevel(level)

        # console
        self._setup_console_log()

        # file
        self._setup_file_log()

    def get_level(self):
        """Returns the current log level."""
        return logging.getLevelName(self.backend.level)

    def clear_loggers(self, namespace):
        """Clear any previously configured loggers for `namespace`."""

        for i in logging.getLogger("cement:app:%s" % namespace).handlers:
            logging.getLogger("cement:app:%s" % namespace).removeHandler(i)
            self.backend = logging.getLogger("cement:app:%s" % namespace)

    def _setup_console_log(self):
        """Add a console log handler."""
        to_console = self.app.config.get(self._meta.config_section,
                                         'to_console')
        if is_true(to_console):
            console_handler = logging.StreamHandler()
            if self.get_level() == logging.getLevelName(logging.DEBUG):
                format = logging.Formatter(self._meta.debug_format)
            else:
                format = logging.Formatter(self._meta.console_format)
            console_handler.setFormatter(format)
            console_handler.setLevel(getattr(logging, self.get_level()))
        else:
            console_handler = NullHandler()

        self.backend.addHandler(console_handler)

    def _setup_file_log(self):
        """Add a file log handler."""

        file_path = self.app.config.get(self._meta.config_section, 'file')
        rotate = self.app.config.get(self._meta.config_section, 'rotate')
        max_bytes = self.app.config.get(self._meta.config_section,
                                        'max_bytes')
        max_files = self.app.config.get(self._meta.config_section,
                                        'max_files')
        if file_path:
            file_path = fs.abspath(file_path)
            log_dir = os.path.dirname(file_path)
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)

            if rotate:
                from logging.handlers import RotatingFileHandler
                file_handler = RotatingFileHandler(
                    file_path,
                    maxBytes=int(max_bytes),
                    backupCount=int(max_files),
                )
            else:
                from logging import FileHandler
                file_handler = FileHandler(file_path)

            if self.get_level() == logging.getLevelName(logging.DEBUG):
                format = logging.Formatter(self._meta.debug_format)
            else:
                format = logging.Formatter(self._meta.file_format)
            file_handler.setFormatter(format)
            file_handler.setLevel(getattr(logging, self.get_level()))
        else:
            file_handler = NullHandler()

        self.backend.addHandler(file_handler)

    def _get_logging_kwargs(self, namespace, **kw):
        if namespace is None:
            namespace = self._meta.namespace

        if 'extra' in kw.keys() and 'namespace' in kw['extra'].keys():
            pass
        elif 'extra' in kw.keys() and 'namespace' not in kw['extra'].keys():
            kw['extra']['namespace'] = namespace
        else:
            kw['extra'] = dict(namespace=namespace)

        return kw

    def info(self, msg, namespace=None, **kw):
        """
        Log to the INFO facility.

        :param msg: The message the log.
        :param namespace: A log prefix, generally the module ``__name__`` that
            the log is coming from.  Will default to self._meta.namespace if
            None is passed.
        :keyword kw: Keyword arguments are passed on to the backend logging
            system.

        """
        kwargs = self._get_logging_kwargs(namespace, **kw)
        self.backend.info(msg, **kwargs)

    def warn(self, msg, namespace=None, **kw):
        """
        Log to the WARN facility.

        :param msg: The message the log.
        :param namespace: A log prefix, generally the module ``__name__`` that
            the log is coming from.  Will default to self._meta.namespace if
            None is passed.
        :keyword kw: Keyword arguments are passed on to the backend logging
            system.

        """
        kwargs = self._get_logging_kwargs(namespace, **kw)
        self.backend.warn(msg, **kwargs)

    def error(self, msg, namespace=None, **kw):
        """
        Log to the ERROR facility.

        :param msg: The message the log.
        :param namespace: A log prefix, generally the module ``__name__`` that
            the log is coming from.  Will default to self._meta.namespace if
            None is passed.
        :keyword kw: Keyword arguments are passed on to the backend logging
            system.

        """
        kwargs = self._get_logging_kwargs(namespace, **kw)
        self.backend.error(msg, **kwargs)

    def fatal(self, msg, namespace=None, **kw):
        """
        Log to the FATAL (aka CRITICAL) facility.

        :param msg: The message the log.
        :param namespace: A log prefix, generally the module ``__name__`` that
            the log is coming from.  Will default to self._meta.namespace if
            None is passed.
        :keyword kw: Keyword arguments are passed on to the backend logging
            system.

        """
        kwargs = self._get_logging_kwargs(namespace, **kw)
        self.backend.fatal(msg, **kwargs)

    def debug(self, msg, namespace=None, **kw):
        """
        Log to the DEBUG facility.

        :param msg: The message the log.
        :param namespace: A log prefix, generally the module ``__name__`` that
            the log is coming from.  Will default to self._meta.namespace if
            None is passed.  For debugging, it can be useful to set this to
            ``__file__``, though ``__name__`` is much less verbose.
        :keyword kw: Keyword arguments are passed on to the backend logging
            system.

        """
        kwargs = self._get_logging_kwargs(namespace, **kw)
        self.backend.debug(msg, **kwargs)


def load():
    """Called by the framework when the extension is 'loaded'."""
    handler.register(LoggingLogHandler)

########NEW FILE########
__FILENAME__ = ext_memcached
"""Memcached Framework Extension."""

import sys
import pylibmc
from ..core import cache, handler
from ..utils.misc import minimal_logger

LOG = minimal_logger(__name__)


class MemcachedCacheHandler(cache.CementCacheHandler):
    """
    This class implements the :ref:`ICache <cement.core.cache>`
    interface.  It provides a caching interface using the
    `pylibmc <http://sendapatch.se/projects/pylibmc/>`_ library.

    **Note** This extension has an external dependency on `pylibmc`.  You
    must include `pylibmc` in your applications dependencies as Cement
    explicitly does *not* include external dependencies for optional
    extensions.

    **Note** This extension is not supported on Python 3, due to the fact
    that `pylibmc` does not appear to support Python 3 as of yet.

    Configuration:

    The Memcached extension is configurable with the following config settings
    under a `[cache.memcached]` section of the application configuration.

        * **expire_time** - The default time in second to expire items in the
          cache.  Default: 0 (does not expire).
        * **hosts** - List of Memcached servers.

    Configurations can be passed as defaults to a CementApp:

    .. code-block:: python

        from cement.core import foundation, backend
        from cement.utils.misc import init_defaults

        defaults = init_defaults('myapp', 'cache.memcached')
        defaults['cache.memcached']['expire_time'] = 0
        defaults['cache.memcached']['hosts'] = ['127.0.0.1']

        app = foundation.CementApp('myapp',
                                   config_defaults=defaults,
                                   cache_handler='memcached',
                                   )


    Additionally, an application configuration file might have a section like
    the following:

    .. code-block:: text

        [cache.memcached]

        # time in seconds that an item in the cache will expire
        expire_time = 3600

        # comma seperated list of memcached servers
        hosts = 127.0.0.1, cache.example.com


    Usage:

    .. code-block:: python

        from cement.core import foundation
        from cement.utils.misc import init_defaults

        defaults = init_defaults('myapp', 'memcached')
        defaults['cache.memcached']['expire_time'] = 300 # seconds
        defaults['cache.memcached']['hosts'] = ['127.0.0.1']

        class MyApp(foundation.CementApp):
            class Meta:
                label = 'myapp'
                config_defaults = defaults
                extensions = ['memcached']
                cache_handler = 'memcached'

        app = MyApp()
        try:
            app.setup()
            app.run()

            # Set a cached value
            app.cache.set('my_key', 'my value')

            # Get a cached value
            app.cache.get('my_key')

            # Delete a cached value
            app.cache.delete('my_key')

            # Delete the entire cache
            app.cache.purge()

        finally:
            app.close()

    """
    class Meta:
        interface = cache.ICache
        label = 'memcached'
        config_defaults = dict(
            hosts=['127.0.0.1'],
            expire_time=0,
        )

    def __init__(self, *args, **kw):
        super(MemcachedCacheHandler, self).__init__(*args, **kw)
        self.mc = None

    def _setup(self, *args, **kw):
        super(MemcachedCacheHandler, self)._setup(*args, **kw)
        self._fix_hosts()
        self.mc = pylibmc.Client(self._config('hosts'))

    def _fix_hosts(self):
        """
        Useful to fix up the hosts configuration (i.e. convert a
        comma-separated string into a list).  This function does not return
        anything, however it is expected to set the `hosts` value of the
        `[cache.memcached]` section (which is what this extension reads for
        it's host configution).

        :returns: None

        """
        hosts = self._config('hosts')
        fixed_hosts = []

        if type(hosts) == str:
            parts = hosts.split(',')
            for part in parts:
                fixed_hosts.append(part.strip())
        elif type(hosts) == list:
            fixed_hosts = hosts
        self.app.config.set(self._meta.config_section, 'hosts', fixed_hosts)

    def get(self, key, fallback=None, **kw):
        """
        Get a value from the cache.  Any additional keyword arguments will be
        passed directly to `pylibmc` get function.

        :param key: The key of the item in the cache to get.
        :param fallback: The value to return if the item is not found in the
         cache.
        :returns: The value of the item in the cache, or the `fallback` value.

        """
        LOG.debug("getting cache value using key '%s'" % key)
        res = self.mc.get(key, **kw)
        if res is None:
            return fallback
        else:
            return res

    def _config(self, key):
        """
        This is a simple wrapper, and is equivalent to:
        `self.app.config.get('cache.memcached', <key>)`.

        :param key: The key to get a config value from the 'cache.memcached'
         config section.
        :returns: The value of the given key.

        """
        return self.app.config.get(self._meta.config_section, key)

    def set(self, key, value, time=None, **kw):
        """
        Set a value in the cache for the given `key`.  Any additional
        keyword arguments will be passed directly to the `pylibmc` set
        function.

        :param key: The key of the item in the cache to set.
        :param value: The value of the item to set.
        :param time: The expiration time (in seconds) to keep the item cached.
         Defaults to `expire_time` as defined in the applications
         configuration.
        :returns: None

        """
        if time is None:
            time = int(self._config('expire_time'))

        self.mc.set(key, value, time=time, **kw)

    def delete(self, key, **kw):
        """
        Delete an item from the cache for the given `key`.  Any additional
        keyword arguments will be passed directly to the `pylibmc` delete
        function.

        :param key: The key to delete from the cache.
        :returns: None

        """
        self.mc.delete(key, **kw)

    def purge(self, **kw):
        """
        Purge the entire cache, all keys and values will be lost.  Any
        additional keyword arguments will be passed directly to the
        `pylibmc` flush_all() function.

        :returns: None

        """

        self.mc.flush_all(**kw)


def load():
    """
    Registers the MemcachedCacheHandler, generally called by the CementApp
    during extension loading.

    """
    handler.register(MemcachedCacheHandler)

########NEW FILE########
__FILENAME__ = ext_mustache
"""Mustache extension module."""

import sys
import pystache
from ..core import output, exc, handler
from ..utils.misc import minimal_logger

LOG = minimal_logger(__name__)


class MustacheOutputHandler(output.TemplateOutputHandler):
    """
    This class implements the :ref:`IOutput <cement.core.output>`
    interface.  It provides text output from template and uses the
    `Mustache Templating Language <http://mustache.github.com>`_.

    **Note** This extension has an external dependency on ``pystache``.  You
    must include ``pystache`` in your applications dependencies as Cement
    explicitly does *not* include external dependencies for optional
    extensions.

    Usage:

    .. code-block:: python

        from cement.core import foundation

        class MyApp(foundation.CementApp):
            class Meta:
                label = 'myapp'
                extensions = ['mustache']
                output_handler = 'mustache'
                template_module = 'myapp.templates'
                template_dir = '/usr/lib/myapp/templates'
        # ...

    From here, you would then put a Mustache template file in
    `myapp/templates/my_template.mustache` and then render a data dictionary
    with it:

    .. code-block:: python

        # via the app object
        myapp.render(some_data_dict, 'my_template.mustache')

        # or from within a controller or handler
        self.app.render(some_data_dict, 'my_template.mustache')



    Configuration:

    This extension honors the ``template_dir`` configuration option under the
    base configuration section of any application configuration file.  It
    also honors the ``template_module`` and ``template_dir`` meta options
    under the main application object.

    """

    class Meta:
        interface = output.IOutput
        label = 'mustache'

    def render(self, data_dict, template):
        """
        Take a data dictionary and render it using the given template file.

        Required Arguments:

        :param data_dict: The data dictionary to render.
        :param template: The path to the template, after the
            ``template_module`` or ``template_dir`` prefix as defined in the
            application.
        :returns: str (the rendered template text)

        """
        LOG.debug("rendering output using '%s' as a template." % template)
        content = self.load_template(template)
        return pystache.render(content, data_dict)


def load():
    handler.register(MustacheOutputHandler)

########NEW FILE########
__FILENAME__ = ext_nulloutput
"""NullOutput Framework Extension"""

from ..core import backend, output, handler
from ..utils.misc import minimal_logger

LOG = minimal_logger(__name__)


class NullOutputHandler(output.CementOutputHandler):

    """
    This class is an internal implementation of the
    :ref:`IOutput <cement.core.output>` interface. It does not take any
    parameters on initialization.

    """
    class Meta:

        """Handler meta-data"""

        interface = output.IOutput
        """The interface this class implements."""

        label = 'null'
        """The string identifier of this handler."""

    def render(self, data_dict, template=None):
        """
        This implementation does not actually render anything to output, but
        rather logs it to the debug facility.

        :param data_dict: The data dictionary to render.
        :param template: The template parameter is not used by this
            implementation at all.
        :returns: None

        """
        LOG.debug("not rendering any output to console")
        LOG.debug("DATA: %s" % data_dict)
        return None


def load():
    """Called by the framework when the extension is 'loaded'."""
    handler.register(NullOutputHandler)

########NEW FILE########
__FILENAME__ = ext_plugin
"""Plugin Framework Extension"""

import os
import sys
import glob
import imp
from ..core import backend, handler, plugin, exc
from ..utils.misc import is_true, minimal_logger
from ..utils.fs import abspath

LOG = minimal_logger(__name__)

# FIX ME: This is a redundant name... ?


class CementPluginHandler(plugin.CementPluginHandler):

    """
    This class is an internal implementation of the
    :ref:`IPlugin <cement.core.plugin>` interface. It does not take any
    parameters on initialization.

    """

    class Meta:

        """Handler meta-data."""

        interface = plugin.IPlugin
        """The interface that this class implements."""

        label = 'cement'
        """The string identifier for this class."""

    def __init__(self):
        super(CementPluginHandler, self).__init__()
        self._loaded_plugins = []
        self._enabled_plugins = []
        self._disabled_plugins = []
        self._plugin_configs = {}

    def _setup(self, app_obj):
        super(CementPluginHandler, self)._setup(app_obj)
        self._enabled_plugins = []
        self._disabled_plugins = []
        self._plugin_configs = {}
        self.config_dir = abspath(self.app._meta.plugin_config_dir)
        self.bootstrap = self.app._meta.plugin_bootstrap
        self.load_dir = abspath(self.app._meta.plugin_dir)

        # grab a generic config handler object
        config_handler = handler.get('config', self.app.config._meta.label)

        # first parse plugin config dir for enabled plugins
        if self.config_dir:
            if not os.path.exists(self.config_dir):
                LOG.debug('plugin config dir %s does not exist.' %
                          self.config_dir)
            else:
                # sort so that we always load plugins in the same order
                # regardless of OS (seems some don't sort reliably)
                plugin_config_files = glob.glob("%s/*.conf" % self.config_dir)
                plugin_config_files.sort()

                for config in plugin_config_files:
                    config = os.path.abspath(os.path.expanduser(config))
                    LOG.debug("loading plugin config from '%s'." % config)
                    pconfig = config_handler()
                    pconfig._setup(self.app)
                    pconfig.parse_file(config)

                    if not pconfig.get_sections():
                        LOG.debug("config file '%s' has no sections." %
                                  config)
                        continue

                    plugin = pconfig.get_sections()[0]
                    if not 'enable_plugin' in pconfig.keys(plugin):
                        continue

                    if is_true(pconfig.get(plugin, 'enable_plugin')):
                        LOG.debug("enabling plugin '%s' per plugin config" %
                                  plugin)
                        if plugin not in self._enabled_plugins:
                            self._enabled_plugins.append(plugin)
                        if plugin in self._disabled_plugins:
                            self._disabled_plugins.remove(plugin)
                    else:
                        LOG.debug("disabling plugin '%s' per plugin config" %
                                  plugin)
                        if plugin not in self._disabled_plugins:
                            self._disabled_plugins.append(plugin)
                        if plugin in self._enabled_plugins:
                            self._enabled_plugins.remove(plugin)

                    # Store the config for later use in load_plugin()
                    # NOTE: Store the config regardless of whether it is
                    # enabled or disabled
                    if plugin not in self._plugin_configs.keys():
                        self._plugin_configs[plugin] = {}

                    for key in pconfig.keys(plugin):
                        val = pconfig.get(plugin, key)
                        self._plugin_configs[plugin][key] = val

        # second, parse all app configs for plugins. Note: these are already
        # loaded from files when app.config was setup.  The application
        # configuration OVERRIDES plugin configs.
        for plugin in self.app.config.get_sections():
            if not 'enable_plugin' in self.app.config.keys(plugin):
                continue
            if is_true(self.app.config.get(plugin, 'enable_plugin')):
                LOG.debug("enabling plugin '%s' per application config" %
                          plugin)
                if plugin not in self._enabled_plugins:
                    self._enabled_plugins.append(plugin)
                if plugin in self._disabled_plugins:
                    self._disabled_plugins.remove(plugin)
            else:
                LOG.debug("disabling plugin '%s' per application config" %
                          plugin)
                if plugin not in self._disabled_plugins:
                    self._disabled_plugins.append(plugin)
                if plugin in self._enabled_plugins:
                    self._enabled_plugins.remove(plugin)

    def _load_plugin_from_dir(self, plugin_name, plugin_dir):
        """
        Load a plugin from file within a plugin directory rather than a
        python package within sys.path.

        :param plugin_name: The name of the plugin, also the name of the file
            with '.py' appended to the name.
        :param plugin_dir: The filesystem directory path where to find the
            file.

        """
        full_path = os.path.join(plugin_dir, "%s.py" % plugin_name)
        if not os.path.exists(full_path):
            LOG.debug("plugin file '%s' does not exist." % full_path)
            return False

        LOG.debug("attempting to load '%s' from '%s'" % (plugin_name,
                                                         plugin_dir))

        # We don't catch this because it would make debugging a nightmare
        f, path, desc = imp.find_module(plugin_name, [plugin_dir])
        mod = imp.load_module(plugin_name, f, path, desc)
        if mod and hasattr(mod, 'load'):
            mod.load()
        return True

    def _load_plugin_from_bootstrap(self, plugin_name, base_package):
        """
        Load a plugin from a python package.  Returns True if no ImportError
        is encountered.

        :param plugin_name: The name of the plugin, also the name of the
            module to load from base_package.
            I.e. ``myapp.bootstrap.myplugin``
        :type plugin_name: str
        :param base_package: The base python package to load the plugin module
            from.  I.e.'myapp.bootstrap' or similar.
        :type base_package: str
        :returns: True is the plugin was loaded, False otherwise
        :raises: ImportError

        """

        full_module = '%s.%s' % (base_package, plugin_name)

        # If the base package doesn't exist, we return False rather than
        # bombing out.
        if base_package not in sys.modules:
            try:
                __import__(base_package, globals(), locals(), [], 0)
            except ImportError as e:
                LOG.debug("unable to import plugin bootstrap module '%s'."
                          % base_package)
                return False

        LOG.debug("attempting to load '%s' from '%s'" % (plugin_name,
                                                         base_package))
        # We don't catch this because it would make debugging a nightmare
        if full_module not in sys.modules:
            __import__(full_module, globals(), locals(), [], 0)

        if hasattr(sys.modules[full_module], 'load'):
            sys.modules[full_module].load()

        return True

    def load_plugin(self, plugin_name):
        """
        Load a plugin whose name is 'plugin_name'.  First attempt to load
        from a plugin directory (plugin_dir), secondly attempt to load from a
        bootstrap module (plugin_bootstrap) determined by
        self.app._meta.plugin_bootstrap.

        Upon successful loading of a plugin, the plugin name is appended to
        the self._loaded_plugins list.

        :param plugin_name: The name of the plugin to load.
        :type plugin_name: str
        :raises: cement.core.exc.FrameworkError

        """
        LOG.debug("loading application plugin '%s'" % plugin_name)

        # first attempt to load from plugin_dir, then from a bootstrap module

        if self._load_plugin_from_dir(plugin_name, self.load_dir):
            self._loaded_plugins.append(plugin_name)
        elif self._load_plugin_from_bootstrap(plugin_name, self.bootstrap):
            self._loaded_plugins.append(plugin_name)
        else:
            raise exc.FrameworkError("Unable to load plugin '%s'." %
                                     plugin_name)

        # Merge in missing config settings (app config settings take
        # precedence):
        #
        # Note that we loaded the plugin configs during _setup() into
        # self._plugin_configs... yes, this is fucking dirty.
        if plugin_name not in self.app.config.get_sections():
            self.app.config.add_section(plugin_name)

        if plugin_name in self._plugin_configs.keys():
            plugin_config = self._plugin_configs[plugin_name]
            for key, val in plugin_config.items():
                if key not in self.app.config.keys(plugin_name):
                    self.app.config.set(plugin_name, key, val)

    def load_plugins(self, plugin_list):
        """
        Load a list of plugins.  Each plugin name is passed to
        self.load_plugin().

        :param plugin_list: A list of plugin names to load.

        """
        for plugin_name in plugin_list:
            self.load_plugin(plugin_name)

    def get_loaded_plugins(self):
        """List of plugins that have been loaded."""
        return self._loaded_plugins

    def get_enabled_plugins(self):
        """List of plugins that are enabled (not necessary loaded yet)."""
        return self._enabled_plugins

    def get_disabled_plugins(self):
        """List of disabled plugins"""
        return self._disabled_plugins


def load():
    """Called by the framework when the extension is 'loaded'."""
    handler.register(CementPluginHandler)

########NEW FILE########
__FILENAME__ = ext_yaml
"""YAML Framework Extension"""

import sys
import yaml
from ..core import backend, output, hook, handler
from ..utils.misc import minimal_logger

LOG = minimal_logger(__name__)


class YamlOutputHandler(output.CementOutputHandler):
    """
    This class implements the :ref:`IOutput <cement.core.output>`
    interface.  It provides YAML output from a data dictionary and uses
    `pyYAML <http://pyyaml.org/wiki/PyYAMLDocumentation>`_ to dump it to
    STDOUT.

    Note: The cement framework detects the '--yaml' option and suppresses
    output (same as if passing --quiet).  Therefore, if debugging or
    troubleshooting issues you must pass the --debug option to see whats
    going on.

    """
    class Meta:
        interface = output.IOutput
        label = 'yaml'

    def __init__(self, *args, **kw):
        super(YamlOutputHandler, self).__init__(*args, **kw)
        self.config = None

    def _setup(self, app_obj):
        self.app = app_obj

    def render(self, data_dict, template=None):
        """
        Take a data dictionary and render it as Yaml output.  Note that the
        template option is received here per the interface, however this
        handler just ignores it.

        :param data_dict: The data dictionary to render.
        :param template: This option is completely ignored.
        :returns: A Yaml encoded string.
        :rtype: str

        """
        LOG.debug("rendering output as Yaml via %s" % self.__module__)
        sys.stdout = backend.__saved_stdout__
        sys.stderr = backend.__saved_stderr__
        return yaml.dump(data_dict)


def add_yaml_option(app):
    """
    This is a ``post_setup`` hook that adds the ``--yaml`` argument to the
    command line.

    :param app: The application object.

    """
    app.args.add_argument('--yaml',
                          dest='output_handler',
                          action='store_const',
                          help='toggle yaml output handler',
                          const='yaml')


def set_output_handler(app):
    """
    This is a ``pre_run`` hook that overrides the configured output handler
    if ``--yaml`` is passed at the command line.

    :param app: The application object.

    """
    if '--yaml' in app._meta.argv:
        app._meta.output_handler = 'yaml'
        app._setup_output_handler()


def load():
    """Called by the framework when the extension is 'loaded'."""
    handler.register(YamlOutputHandler)
    hook.register('post_setup', add_yaml_option)
    hook.register('pre_run', set_output_handler)

########NEW FILE########
__FILENAME__ = fs
"""Common File System Utilities."""

import os
import shutil


def abspath(path):
    """
    Return an absolute path, while also expanding the '~' user directory
    shortcut.

    :param path: The original path to expand.
    :rtype: str

    """
    return os.path.abspath(os.path.expanduser(path))


def backup(path, suffix='.bak'):
    """
    Rename a file or directory safely without overwriting an existing
    backup of the same name.

    :param path: The path to the file or directory to make a backup of.
    :param suffix: The suffix to rename files with.
    :returns: The new path of backed up file/directory
    :rtype: str

    """
    count = -1
    new_path = None
    while True:
        if os.path.exists(path):
            if count == -1:
                new_path = "%s%s" % (path, suffix)
            else:
                new_path = "%s%s.%s" % (path, suffix, count)
            if os.path.exists(new_path):
                count += 1
                continue
            else:
                if os.path.isfile(path):
                    shutil.copy(path, new_path)
                elif os.path.isdir(path):
                    shutil.copytree(path, new_path)
                break
        else:
            break
    return new_path

########NEW FILE########
__FILENAME__ = misc
"""Misc utilities."""

import sys
import logging
from textwrap import TextWrapper


class MinimalLogger(object):
    def __init__(self, namespace, debug, *args, **kw):
        self.namespace = namespace
        self.backend = logging.getLogger(namespace)
        formatter = logging.Formatter(
            "%(asctime)s (%(levelname)s) %(namespace)s : %(message)s"
        )
        console = logging.StreamHandler()
        console.setFormatter(formatter)
        console.setLevel(logging.INFO)
        self.backend.setLevel(logging.INFO)

        # FIX ME: really don't want to hard check sys.argv like this but
        # can't figure any better way get logging started (only for debug)
        # before the app logging is setup.
        if '--debug' in sys.argv or debug:
            console.setLevel(logging.DEBUG)
            self.backend.setLevel(logging.DEBUG)

        self.backend.addHandler(console)

    def _get_logging_kwargs(self, namespace, **kw):
        if not namespace:
            namespace = self.namespace

        if 'extra' in kw.keys() and 'namespace' in kw['extra'].keys():
            pass
        elif 'extra' in kw.keys() and 'namespace' not in kw['extra'].keys():
            kw['extra']['namespace'] = namespace
        else:
            kw['extra'] = dict(namespace=namespace)

        return kw

    def info(self, msg, namespace=None, **kw):
        kwargs = self._get_logging_kwargs(namespace, **kw)
        self.backend.info(msg, **kwargs)

    def warn(self, msg, namespace=None, **kw):
        kwargs = self._get_logging_kwargs(namespace, **kw)
        self.backend.warn(msg, **kwargs)

    def error(self, msg, namespace=None, **kw):
        kwargs = self._get_logging_kwargs(namespace, **kw)
        self.backend.error(msg, **kwargs)

    def fatal(self, msg, namespace=None, **kw):
        kwargs = self._get_logging_kwargs(namespace, **kw)
        self.backend.fatal(msg, **kwargs)

    def debug(self, msg, namespace=None, **kw):
        kwargs = self._get_logging_kwargs(namespace, **kw)
        self.backend.debug(msg, **kwargs)


def init_defaults(*sections):
    """
    Returns a standard dictionary object to use for application defaults.
    If sections are given, it will create a nested dict for each section name.

    :arg sections: Section keys to create nested dictionaries for.
    :returns: Dictionary of nested dictionaries (sections)
    :rtype: dict

    .. code-block:: python

        from cement.core import foundation
        from cement.utils.misc import init_defaults

        defaults = init_defaults('myapp', 'section2', 'section3')
        defaults['myapp']['debug'] = False
        defaults['section2']['foo'] = 'bar
        defaults['section3']['foo2'] = 'bar2'

        app = foundation.CementApp('myapp', config_defaults=defaults)

    """
    defaults = dict()
    for section in sections:
        defaults[section] = dict()
    return defaults


def minimal_logger(namespace, debug=False):
    """
    Setup just enough for cement to be able to do debug logging.  This is the
    logger used by the Cement framework, which is setup and accessed before
    the application is functional (and more importantly before the
    applications log handler is usable).

    :param namespace: The logging namespace.  This is generally '__name__' or
        anything you want.
    :param debug: Toggle debug output. Default: False
    :type debug: boolean
    :returns: Logger object

    .. code-block:: python

        from cement.utils.misc import minimal_logger
        LOG = minimal_logger('cement')
        LOG.debug('This is a debug message')

    """
    return MinimalLogger(namespace, debug)


def is_true(item):
    """
    Given a value, determine if it is one of [True, 'True', 'true', 1, '1'].

    :param item: The item to convert to a boolean.
    :returns: True if `item` is in ``[True, 'True', 'true', 1, '1']``, False
        otherwise.
    :rtype: boolean

    """
    if item in [True, 'True', 'true', 1, '1']:
        return True
    else:
        return False


def wrap(text, width=77, indent='', long_words=False, hyphens=False):
    """
    Wrap text for cleaner output (this is a simple wrapper around
    `textwrap.TextWrapper` in the standard library).

    :param text: The text to wrap
    :param width: The max width of a line before breaking
    :param indent: String to prefix subsequent lines after breaking
    :param long_words: Break on long words
    :param hyphens: Break on hyphens
    :returns: str(text)

    """
    if type(text) != str:
        raise TypeError("`text` must be a string.")

    wrapper = TextWrapper(subsequent_indent=indent, width=width,
                          break_long_words=long_words,
                          break_on_hyphens=hyphens)
    return wrapper.fill(text)

########NEW FILE########
__FILENAME__ = shell
"""Common Shell Utilities."""

from subprocess import Popen, PIPE
from multiprocessing import Process
from threading import Thread


def exec_cmd(cmd_args, shell=False):
    """
    Execute a shell call using Subprocess.

    :param cmd_args: List of command line arguments.
    :type cmd_args: list
    :param shell: See `Subprocess
        <http://docs.python.org/library/subprocess.html>`_
    :type shell: boolean
    :returns: The (stdout, stderror, return_code) of the command
    :rtype: tuple

    Usage:

    .. code-block:: python

        from cement.utils import shell

        stdout, stderr, exitcode = shell.exec_cmd(['echo', 'helloworld'])

    """
    proc = Popen(cmd_args, stdout=PIPE, stderr=PIPE, shell=shell)
    (stdout, stderr) = proc.communicate()
    proc.wait()
    return (stdout, stderr, proc.returncode)


def exec_cmd2(cmd_args, shell=False):
    """
    Similar to exec_cmd, however does not capture stdout, stderr (therefore
    allowing it to print to console).

    :param cmd_args: List of command line arguments.
    :type cmd_args: list
    :param shell: See `Subprocess
        <http://docs.python.org/library/subprocess.html>`_
    :type shell: boolean
    :returns: The integer return code of the command.
    :rtype: int

    Usage:

    .. code-block:: python

        from cement.utils import shell

        exitcode = shell.exec_cmd2(['echo', 'helloworld'])

    """
    proc = Popen(cmd_args, shell=shell)
    proc.wait()
    return proc.returncode


def spawn_process(target, start=True, join=False, *args, **kwargs):
    """
    A quick wrapper around multiprocessing.Process().  By default the start()
    function will be called before the spawned process object is returned.

    :param target: The target function to execute in the sub-process.
    :param start: Call start() on the process before returning the process
        object.
    :param join: Call join() on the process before returning the process
        object.  Only called if start=True.
    :param args: Additional arguments are passed to Process().
    :param kwargs: Additional keyword arguments are passed to Process().
    :returns: The process object returned by Process().

    Usage:

    .. code-block:: python

        from cement.utils import shell

        def add(a, b):
            print(a + b)

        p = shell.spawn_process(add, args=(12, 27))
        p.join()

    """
    proc = Process(target=target, *args, **kwargs)

    if start and not join:
        proc.start()
    elif start and join:
        proc.start()
        proc.join()
    return proc


def spawn_thread(target, start=True, join=False, *args, **kwargs):
    """
    A quick wrapper around threading.Thread().  By default the start()
    function will be called before the spawned thread object is returned

    :param target: The target function to execute in the thread.
    :param start: Call start() on the thread before returning the thread
        object.
    :param join: Call join() on the thread before returning the thread
        object.  Only called if start=True.
    :param args: Additional arguments are passed to Thread().
    :param kwargs: Additional keyword arguments are passed to Thread().
    :returns: The thread object returned by Thread().

    Usage:

    .. code-block:: python

        from cement.utils import shell

        def add(a, b):
            print(a + b)

        t = shell.spawn_thread(add, args=(12, 27))
        t.join()

    """
    thr = Thread(target=target, *args, **kwargs)

    if start and not join:
        thr.start()
    elif start and join:
        thr.start()
        thr.join()
    return thr

########NEW FILE########
__FILENAME__ = test
"""Cement testing utilities."""

import unittest
from ..core import backend, foundation

# shortcuts
from nose import SkipTest
from nose.tools import ok_ as ok
from nose.tools import eq_ as eq
from nose.tools import raises
from nose.plugins.attrib import attr


class TestApp(foundation.CementApp):

    """
    Basic CementApp for generic testing.

    """
    class Meta:
        label = 'test'
        config_files = []
        argv = []
        base_controller = None
        arguments = []


class CementTestCase(unittest.TestCase):
    """
    A sub-class of unittest.TestCase.

    """

    app_class = TestApp
    """The test class that is used by self.make_app to create an app."""

    def __init__(self, *args, **kw):
        super(CementTestCase, self).__init__(*args, **kw)

    def setUp(self):
        """
        Sets up self.app with a generic TestApp().  Also resets the backend
        hooks and handlers so that everytime an app is created it is setup
        clean each time.

        """
        self.app = self.make_app()

    def make_app(self, *args, **kw):
        """
        Create a generic app using TestApp.  Arguments and Keyword Arguments
        are passed to the app.

        """
        self.reset_backend()
        return self.app_class(*args, **kw)

    def reset_backend(self):
        """
        Remove all registered hooks and handlers from the backend.

        """
        for _handler in backend.__handlers__.copy():
            del backend.__handlers__[_handler]
        for _hook in backend.__hooks__.copy():
            del backend.__hooks__[_hook]

    def ok(self, expr, msg=None):
        """Shorthand for assert."""
        return ok(expr, msg)

    def eq(self, a, b, msg=None):
        """Shorthand for 'assert a == b, "%r != %r" % (a, b)'. """
        return eq(a, b, msg)

# The following are for internal, Cement unit testing only


@attr('core')
class CementCoreTestCase(CementTestCase):
    pass


@attr('ext')
class CementExtTestCase(CementTestCase):
    pass

########NEW FILE########
__FILENAME__ = version

# Copyright (c) Django Software Foundation and individual contributors.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#    1. Redistributions of source code must retain the above copyright notice,
#       this list of conditions and the following disclaimer.
#
#    2. Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#
#    3. Neither the name of Django nor the names of its contributors may be
#       used to endorse or promote products derived from this software without
#       specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#

# The following code was copied from the Django project, and only lightly
# modified.  Please adhere to the above copyright and license for the code
# in this file.

# Note: Nothing is covered here because this file is imported before nose and
# coverage take over.. and so its a false positive that nothing is covered.

import datetime  # pragma: nocover
import os  # pragma: nocover
import subprocess  # pragma: nocover

from cement.core.backend import VERSION  # pragma: nocover


def get_version(version=VERSION):  # pragma: nocover
    "Returns a PEP 386-compliant version number from VERSION."
    assert len(version) == 5
    assert version[3] in ('alpha', 'beta', 'rc', 'final')

    # Now build the two parts of the version number:
    # main = X.Y[.Z]
    # sub = .devN - for pre-alpha releases
    #     | {a|b|c}N - for alpha, beta and rc releases

    # We want to explicitly include all three version/release numbers
    # parts = 2 if version[2] == 0 else 3
    parts = 3
    main = '.'.join(str(x) for x in version[:parts])

    sub = ''
    if version[3] == 'alpha' and version[4] == 0:
        git_changeset = get_git_changeset()
        if git_changeset:
            sub = '.dev%s' % git_changeset

    elif version[3] != 'final':
        mapping = {'alpha': 'a', 'beta': 'b', 'rc': 'c'}
        sub = mapping[version[3]] + str(version[4])

    return main + sub


def get_git_changeset():  # pragma: nocover
    """Returns a numeric identifier of the latest git changeset.

    The result is the UTC timestamp of the changeset in YYYYMMDDHHMMSS format.
    This value isn't guaranteed to be unique, but collisions are very
    unlikely, so it's sufficient for generating the development version
    numbers.
    """
    repo_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    git_log = subprocess.Popen('git log --pretty=format:%ct --quiet -1 HEAD',
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               shell=True, cwd=repo_dir,
                               universal_newlines=True)
    timestamp = git_log.communicate()[0]
    try:
        timestamp = datetime.datetime.utcfromtimestamp(int(timestamp))
    except ValueError: 	# pragma: nocover
        return None  	# pragma: nocover
    return timestamp.strftime('%Y%m%d%H%M%S')

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# Cement documentation build configuration file, created by
# sphinx-quickstart on Mon Aug 22 17:52:04 2011.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os
sys.path.insert(0, os.path.abspath('../cement/'))

# If we dont' prep an app, then we'll get runtime errors
from cement.utils import test, version
app = test.TestApp()

RELEASE = version.get_version()
VERSION = '.'.join(RELEASE.split('.')[:2])

### Hack for Read The Docs:

import sys

class Mock(object):
    def __init__(self, *args, **kwargs):
        pass

    def __call__(self, *args, **kwargs):
        return Mock()

    @classmethod
    def __getattr__(cls, name):
        if name in ('__file__', '__path__'):
            return '/dev/null'
        elif name[0] == name[0].upper():
            mockType = type(name, (), {})
            mockType.__module__ = __name__
            return mockType
        else:
            return Mock()

MOCK_MODULES = ['pylibmc']
for mod_name in MOCK_MODULES:
    sys.modules[mod_name] = Mock()

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#sys.path.insert(0, os.path.abspath('.'))

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.extlinks',
    ]

extlinks = {'issue' : ('https://github.com/datafolklabs/cement/issues/%s', 'Issue #')}

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'Cement'
copyright = u'2009-2012, BJ Dierkes'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#a
# The short X.Y version.
version = VERSION

# The full version, including alpha/beta/rc tags.
release = RELEASE

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
#show_authors = False

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# A list of ignored prefixes for module index sorting.
#modindex_common_prefix = []


# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = 'nature'

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
html_short_title = u'Cement CLI Application Framework v%s' % RELEASE

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
htmlhelp_basename = 'Cementdoc'


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'Cement.tex', u'Cement Documentation',
   u'BJ Dierkes', 'manual'),
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
    ('index', 'cement', u'Cement Documentation',
     [u'BJ Dierkes'], 1)
]

########NEW FILE########
__FILENAME__ = devtools
#!/usr/bin/env python

import os
import sys
import re
import tempfile

from cement.core.foundation import CementApp
from cement.core.controller import CementBaseController, expose
from cement.utils.version import get_version
from cement.utils import shell

VERSION = get_version()

class CementDevtoolsController(CementBaseController):
    class Meta:
        label = 'base'
        arguments = [
            (['-y, --noprompt'], 
             dict(help='answer yes to prompts.', action='store_true', 
                  dest='noprompt')),
            (['--ignore-errors'],
             dict(help="don't stop operations because of errors", 
                  action='store_true', dest='ignore_errors')),
            (['--loud'], dict(help='add more verbose output', 
             action='store_true', dest='loud')),
            (['modifier1'], 
             dict(help='command modifier positional argument', nargs='?')),
        ]
        
    def _do_error(self, msg):
        if self.app.pargs.ignore_errors:
            self.app.log.error(msg)
        else:
            raise Exception(msg)
            
    @expose(hide=True) 
    def default(self):
        raise AssertionError("A sub-command is required.  See --help.")
        
    def _do_git(self):
        # make sure we don't have any uncommitted changes
        print('Checking for Uncommitted Changes')
        out, err, res = shell.exec_cmd(['git', '--no-pager', 'diff'])
        if len(out) > 0:
            self._do_error('There are uncommitted changes. See `git status`.')
        
        # make sure we don't have any un-added files
        print('Checking for Untracked Files')
        out, err, res = shell.exec_cmd(['git', 'status'])
        if re.match('Untracked files', out):
            self._do_error('There are untracked files.  See `git status`.')
                
        # make sure there isn't an existing tag
        print("Checking for Duplicate Git Tag")
        out, err, res = shell.exec_cmd(['git', 'tag'])
        for ver in out.split('\n'):
            if ver == VERSION:
                self._do_error("Tag %s already exists" % VERSION)
        
        print("Tagging Git Release")
        out, err, res = shell.exec_cmd(['git', 'tag', '-a', '-m', VERSION, 
                                        VERSION])
        if res > 0:
            self._do_error("Unable to tag release with git.")

    def _do_tests(self):
        print('Running Nose Tests')
        out, err, res = shell.exec_cmd(['which', 'nosetests'])
        
        if self.app.pargs.loud:
            cmd_args = ['coverage', 'run', out.strip(), '--verbosity=3']
            res = shell.exec_cmd2(cmd_args)
        else:
            cmd_args = ['coverage', 'run', out.strip(), '--verbosity=0']
            out, err, res = shell.exec_cmd(cmd_args)
        if res > 0:
            self._do_error("\n\nNose tests did not pass.\n\n" +
                           "$ %s\n%s" % (' '.join(cmd_args), err))
        
    def _do_pep8(self):
        print("Checking PEP8 Compliance")
        cmd_args = ['pep8', '-r', 'cement/', '--exclude=*.pyc']
        out, err, res = shell.exec_cmd(cmd_args)
        if res > 0:
            self._do_error("\n\nPEP8 checks did not pass.\n\n" +
                           "$ %s\n%s" % (' '.join(cmd_args), out))

    @expose(help='run all unit tests')
    def run_tests(self):
        print('')
        print('Python Version: %s' % sys.version)
        print('')
        print("Running Tests for Cement Version %s" % VERSION)
        print('-' * 77)
        self._do_pep8()
        self._do_tests()
        print('')

    def _do_sphinx(self, dest_path):
        print("Building Documentation")
        cmd_args = ['rm', '-rf', 'docs/build/*']
        cmd_args = ['sphinx-build', 'doc/source', dest_path]
        out, err, res = shell.exec_cmd(cmd_args)
        if res > 0:
            self._do_error("\n\nFailed to build sphinx documentation\n\n" +
                           "$ %s\n%s" % (' '.join(cmd_args), out))
                           
    @expose(help='create a cement release')
    def make_release(self):
        print('')
        print("Making Release for Version %s" % VERSION)
        print('-' * 77)
        if not self.app.pargs.noprompt:
            res = raw_input("Continue? [yN] ")
            if res not in ['Y', 'y', '1']:
                sys.exit(1)
        
        tmp = tempfile.mkdtemp()
        print("Destination: %s" % tmp)
        os.makedirs(os.path.join(tmp, 'source'))
        os.makedirs(os.path.join(tmp, 'doc'))
        
        self._do_pep8()
        self._do_tests()
        self._do_git()
        self._do_sphinx(os.path.join(tmp, 'doc'))
        
        tar_path = os.path.join(tmp, 'source', 'cement-%s.tar' % VERSION)
        gzip_path = "%s.gz" % tar_path
        
        print("Generating Release Files")
        cmd_args = ['git', 'archive', VERSION, 
                    '--prefix=cement-%s/' % VERSION,
                    '--output=%s' % tar_path]
        out, err, res = shell.exec_cmd(cmd_args)
        
        cmd_args = ['gzip', tar_path]
        out, err, res = shell.exec_cmd(cmd_args)
        if res > 0:
            self._do_error("\n\nFailed generating git archive.\n\n" +
                           "$ %s" % (' '.join(cmd_args), err))

        print('')
        
    @expose(help='get the current version of the sources')
    def get_version(self):
        print(VERSION)
        
class CementDevtoolsApp(CementApp):
    class Meta:
        label = 'cement-devtools'
        base_controller = CementDevtoolsController
        
                
def main():
    app = CementDevtoolsApp('cement-devtools')
    try:
        app.setup()
        app.run()
    except AssertionError as e:
        print("AssertionError => %s" % e.args[0])
    finally:
        app.close()

if __name__ == '__main__':
    main()
########NEW FILE########
__FILENAME__ = bootstrap
"""Test bootstrap file"""

def load():
    pass
########NEW FILE########
__FILENAME__ = backend_tests
"""Tests for cement.core.backend."""


########NEW FILE########
__FILENAME__ = cache_tests
"""Tests for cement.core.cache."""

from cement.core import exc, cache, handler
from cement.utils import test

class MyCacheHandler(cache.CementCacheHandler):
    class Meta:
        label = 'my_cache_handler'

    def get(self, key, fallback=None):
        pass
        
    def set(self, key, value):
        pass
    
    def delete(self, key):
        pass
    
    def purge(self):
        pass
        
@test.attr('core')
class CacheTestCase(test.CementCoreTestCase):
    def setUp(self):
        super(CacheTestCase, self).setUp()
        self.app = self.make_app(cache_handler=MyCacheHandler)
    
    def test_base_handler(self):
        self.app.setup()
        self.app.cache.set('foo', 'bar')
        self.app.cache.get('foo')
        self.app.cache.delete('foo')
        self.app.cache.purge()
            
        
        
    

########NEW FILE########
__FILENAME__ = config_tests
"""Tests for cement.core.config."""

import os
from tempfile import mkstemp
from cement.core import exc, config, handler, backend
from cement.utils import test

CONFIG = """
[my_section]
my_param = my_value
"""

class BogusConfigHandler(config.CementConfigHandler):
    class Meta:
        label = 'bogus'

class ConfigTestCase(test.CementCoreTestCase):
    @test.raises(exc.InterfaceError)
    def test_invalid_config_handler(self):
        handler.register(BogusConfigHandler)

    def test_has_key(self):
        self.app.setup()
        self.ok(self.app.config.has_section(self.app._meta.config_section))

    def test_config_override(self):
        defaults = dict()
        defaults['test'] = dict()
        defaults['test']['debug'] = False
        defaults['test']['foo'] = 'bar'

        # first test that it doesn't override the config with the default
        # setting of arguments_override_config=False
        self.app = self.make_app(
            config_defaults=defaults,
            argv=['--foo=not_bar'],
            arguments_override_config=False
            )
        self.app.setup()
        self.app.args.add_argument('--foo', action='store')
        self.app.run()
        self.eq(self.app.config.get('test', 'foo'), 'bar')

        # then make sure that it does
        self.app = self.make_app(
            config_defaults=defaults,
            argv=['--foo=not_bar'],
            arguments_override_config=True,
            meta_override=['foo'],
            )
        self.app.setup()
        self.app.args.add_argument('--foo', action='store')
        self.app.run()
        self.eq(self.app.config.get('test', 'foo'), 'not_bar')

        # one last test just for code coverage
        self.app = self.make_app(
            config_defaults=defaults,
            argv=['--debug'],
            arguments_override_config=True
            )
        self.app.setup()
        self.app.args.add_argument('--foo', action='store')
        self.app.run()
        self.eq(self.app.config.get('test', 'foo'), 'bar')

    def test_parse_file_bad_path(self):
        self.app._meta.config_files = ['./some_bogus_path']
        self.app.setup()

    def test_parse_file(self):
        _, tmppath = mkstemp()
        f = open(tmppath, 'w+')
        f.write(CONFIG)
        f.close()
        self.app._meta.config_files = [tmppath]
        self.app.setup()
        self.eq(self.app.config.get('my_section', 'my_param'), 'my_value')

########NEW FILE########
__FILENAME__ = controller_tests
"""Tests for cement.core.controller."""

from cement.core import exc, controller, handler
from cement.utils import test

class TestController(controller.CementBaseController):
    class Meta:
        label = 'base'
        arguments = [
            (['-f', '--foo'], dict(help='foo option'))
        ]
        usage = 'My Custom Usage TXT'
        epilog = "This is the epilog"

    @controller.expose(hide=True)
    def default(self):
        pass

class TestWithPositionalController(controller.CementBaseController):
    class Meta:
        label = 'base'
        arguments = [
            (['foo'], dict(help='foo option', nargs='?'))
        ]

    @controller.expose(hide=True)
    def default(self):
        self.app.render(dict(foo=self.app.pargs.foo))

class Embedded(controller.CementBaseController):
    class Meta:
        label = 'embedded_controller'
        stacked_on = 'base'
        stacked_type = 'embedded'
        arguments = [(['-t'], dict())]

    @controller.expose(aliases=['emcmd1'], help='This is my help txt')
    def embedded_cmd1(self):
        pass

class Nested(controller.CementBaseController):
    class Meta:
        label = 'nested_controller'
        stacked_on = 'base'
        stacked_type = 'nested'
        arguments = [(['-t'], dict())]

    @controller.expose()
    def nested_cmd1(self):
        pass

class AliasesOnly(controller.CementBaseController):
    class Meta:
        label = 'aliases_only_controller'
        stacked_on = 'base'
        stacked_type = 'nested'
        aliases = ['this_is_ao_controller']
        aliases_only = True

    @controller.expose(aliases=['ao_cmd1'], aliases_only=True)
    def aliases_only_cmd1(self):
        pass

    @controller.expose(aliases=['ao_cmd2', 'ao2'], aliases_only=True)
    def aliases_only_cmd2(self):
        pass

class DuplicateCommand(controller.CementBaseController):
    class Meta:
        label = 'duplicate_command'
        stacked_on = 'base'
        stacked_type = 'embedded'

    @controller.expose()
    def default(self):
        pass

class DuplicateAlias(controller.CementBaseController):
    class Meta:
        label = 'duplicate_command'
        stacked_on = 'base'
        stacked_type = 'embedded'

    @controller.expose(aliases=['default'])
    def cmd(self):
        pass

class Bad(controller.CementBaseController):
    class Meta:
        label = 'bad_controller'
        arguments = []

class BadStackedType(controller.CementBaseController):
    class Meta:
        label = 'bad_stacked_type'
        stacked_on = 'base'
        stacked_type = 'bogus'
        arguments = []

class ArgumentConflict(controller.CementBaseController):
    class Meta:
        label = 'embedded'
        stacked_on = 'base'
        stacked_type = 'embedded'
        arguments = [(['-f', '--foo'], dict())]

class ControllerTestCase(test.CementCoreTestCase):
    def test_default(self):
        app = self.make_app(base_controller=TestController)
        app.setup()
        app.run()

    def test_epilog(self):
        app = self.make_app(base_controller=TestController)
        app.setup()
        app.run()
        self.eq(app.args.epilog, 'This is the epilog')

    def test_txt_defined_base_controller(self):
        handler.register(TestController)
        self.app.setup()

    @test.raises(exc.InterfaceError)
    def test_invalid_arguments_1(self):
        Bad.Meta.arguments = ['this is invalid']
        handler.register(Bad)

    @test.raises(exc.InterfaceError)
    def test_invalid_arguments_2(self):
        Bad.Meta.arguments = [('this is also invalid', dict())]
        handler.register(Bad)

    @test.raises(exc.InterfaceError)
    def test_invalid_arguments_3(self):
        Bad.Meta.arguments = [(['-f'], 'and this is invalid')]
        handler.register(Bad)

    @test.raises(exc.InterfaceError)
    def test_invalid_arguments_4(self):
        Bad.Meta.arguments = 'totally jacked'
        handler.register(Bad)

    def test_embedded_controller(self):
        app = self.make_app(argv=['embedded-cmd1'])
        handler.register(TestController)
        handler.register(Embedded)
        app.setup()
        app.run()

        check = 'embedded-cmd1' in app.controller._visible_commands
        self.ok(check)

        # also check for the alias here
        check = 'emcmd1' in app.controller._dispatch_map
        self.ok(check)

    def test_nested_controller(self):
        app = self.make_app(argv=['nested-controller'])
        handler.register(TestController)
        handler.register(Nested)
        app.setup()
        app.run()

        check = 'nested-controller' in app.controller._visible_commands
        self.ok(check)

        self.eq(app.controller._dispatch_command['func_name'], '_dispatch')

    def test_aliases_only_controller(self):
        app = self.make_app(argv=['aliases-only-controller'])
        handler.register(TestController)
        handler.register(AliasesOnly)
        app.setup()
        app.run()

    @test.raises(exc.FrameworkError)
    def test_bad_stacked_type(self):
        app = self.make_app()
        handler.register(TestController)
        handler.register(BadStackedType)
        app.setup()
        app.run()

    @test.raises(exc.FrameworkError)
    def test_duplicate_command(self):
        app = self.make_app()
        handler.register(TestController)
        handler.register(DuplicateCommand)
        app.setup()
        app.run()

    @test.raises(exc.FrameworkError)
    def test_duplicate_alias(self):
        app = self.make_app()
        handler.register(TestController)
        handler.register(DuplicateAlias)
        app.setup()
        app.run()

    def test_usage_txt(self):
        app = self.make_app()
        handler.register(TestController)
        app.setup()
        self.eq(app.controller._usage_text, 'My Custom Usage TXT')

    @test.raises(exc.FrameworkError)
    def test_argument_conflict(self):
        try:
            app = self.make_app(base_controller=TestController)
            handler.register(ArgumentConflict)
            app.setup()
            app.run()
        except NameError as e:
            # This is a hack due to a Travis-CI Bug:
            # https://github.com/travis-ci/travis-ci/issues/998
            if e.args[0] == "global name 'ngettext' is not defined":
                bug = "https://github.com/travis-ci/travis-ci/issues/998"
                raise test.SkipTest("Travis-CI Bug: %s" % bug)
            else:
                raise

    def test_default_command_with_positional(self):
        app = self.make_app(base_controller=TestWithPositionalController,
                            argv=['mypositional'])
        app.setup()
        app.run()
        self.eq(app.get_last_rendered()[0]['foo'], 'mypositional')

########NEW FILE########
__FILENAME__ = exc_tests
"""Tests for cement.core.exc."""

from cement.core import exc
from cement.utils import test

class ExceptionTestCase(test.CementCoreTestCase):
    @test.raises(exc.FrameworkError)
    def test_cement_runtime_error(self):
        try:
            raise exc.FrameworkError("FrameworkError Test")
        except exc.FrameworkError as e:
            self.eq(e.msg, "FrameworkError Test")
            self.eq(e.__str__(), "FrameworkError Test")
            raise
        
    @test.raises(exc.InterfaceError)
    def test_cement_interface_error(self):
        try:
            raise exc.InterfaceError("InterfaceError Test")
        except exc.InterfaceError as e:
            self.eq(e.msg, "InterfaceError Test")
            self.eq(e.__str__(), "InterfaceError Test")
            raise

    @test.raises(exc.CaughtSignal)
    def test_cement_signal_error(self):
        try:
            import signal
            raise exc.CaughtSignal(signal.SIGTERM, 5)
        except exc.CaughtSignal as e:
            self.eq(e.signum, signal.SIGTERM)
            self.eq(e.frame, 5)
            raise

########NEW FILE########
__FILENAME__ = extension_tests
"""Tests for cement.core.extension."""

from cement.core import exc, backend, extension, handler, output, interface
from cement.utils import test

class IBogus(interface.Interface):
    class IMeta:
        label = 'bogus'
        
class BogusExtensionHandler(extension.CementExtensionHandler):
    class Meta:
        interface = IBogus
        label = 'bogus'

class ExtensionTestCase(test.CementCoreTestCase):
    @test.raises(exc.FrameworkError)
    def test_invalid_extension_handler(self):
        # the handler type bogus doesn't exist
        handler.register(BogusExtensionHandler)

    def test_load_extensions(self):
        ext = extension.CementExtensionHandler()
        ext._setup(self.app)
        ext.load_extensions(['cement.ext.ext_configparser'])

    def test_load_extensions_again(self):
        ext = extension.CementExtensionHandler()
        ext._setup(self.app)
        ext.load_extensions(['cement.ext.ext_configparser'])
        ext.load_extensions(['cement.ext.ext_configparser'])
    
    @test.raises(exc.FrameworkError)
    def test_load_bogus_extension(self):
        ext = extension.CementExtensionHandler()
        ext._setup(self.app)
        ext.load_extensions(['bogus'])

    def test_get_loaded_extensions(self):
        ext = extension.CementExtensionHandler()
        ext._setup(self.app)
        
        res = 'cement.ext.ext_json' not in ext.get_loaded_extensions()
        self.ok(res)
        
        ext.load_extensions(['json'])
        
        res = 'cement.ext.ext_json' in ext.get_loaded_extensions()
        self.ok(res)

########NEW FILE########
__FILENAME__ = foundation_tests
"""Tests for cement.core.setup."""

import os
import sys
from cement.core import foundation, exc, backend, config, extension, plugin
from cement.core import log, output, handler, hook, arg, controller
from cement.utils import test
from cement.utils.misc import init_defaults

def my_extended_func():
    return 'KAPLA'

class DeprecatedApp(foundation.CementApp):
    class Meta:
        label = 'deprecated'
        defaults = None

class TestOutputHandler(output.CementOutputHandler):
    file_suffix = None

    class Meta:
        interface = output.IOutput
        label = 'test_output_handler'

    def _setup(self, config_obj):
        self.config = config_obj

    def render(self, data_dict, template=None):
        return None

class BogusBaseController(controller.CementBaseController):
    class Meta:
        label = 'bad_base_controller_label'

def my_hook_one(app):
    return 1

def my_hook_two(app):
    return 2

def my_hook_three(app):
    return 3

class FoundationTestCase(test.CementCoreTestCase):
    def setUp(self):
        self.app = self.make_app('my_app')

    def test_argv_is_none(self):
        app = self.make_app('myapp', argv=None)
        app.setup()
        self.eq(app.argv, list(sys.argv[1:]))

    def test_bootstrap(self):
        app = self.make_app('my_app', bootstrap='tests.bootstrap')
        app.setup()
        self.eq(app._loaded_bootstrap.__name__, 'tests.bootstrap')

    def test_reload_bootstrap(self):
        app = self.make_app('my_app', bootstrap='cement.utils.test')
        app._loaded_bootstrap = test
        app.setup()
        self.eq(app._loaded_bootstrap.__name__, 'cement.utils.test')

    def test_argv(self):
        app = self.make_app('my_app', argv=['bogus', 'args'])
        self.eq(app.argv, ['bogus', 'args'])

    @test.raises(exc.FrameworkError)
    def test_resolve_handler_bad_handler(self):
        class Bogus(object):
            pass

        try:
            self.app._resolve_handler('output', Bogus)
        except exc.FrameworkError as e:
            self.ok(e.msg.find('resolve'))
            raise

    def test_default(self):
        self.app.setup()
        self.app.run()

    def test_passed_handlers(self):
        from cement.ext import ext_configparser
        from cement.ext import ext_logging
        from cement.ext import ext_argparse
        from cement.ext import ext_plugin
        from cement.ext import ext_nulloutput

        # forces CementApp._resolve_handler to register the handler
        from cement.ext import ext_json

        app = self.make_app('my-app-test',
            config_handler=ext_configparser.ConfigParserConfigHandler,
            log_handler=ext_logging.LoggingLogHandler(),
            arg_handler=ext_argparse.ArgParseArgumentHandler(),
            extension_handler=extension.CementExtensionHandler(),
            plugin_handler=ext_plugin.CementPluginHandler(),
            output_handler=ext_json.JsonOutputHandler(),
            argv=[__file__, '--debug']
            )

        app.setup()

    def test_debug(self):
        app = self.make_app('my-app-test', argv=[__file__])
        app.setup()
        self.eq(app.debug, False)

        self.reset_backend()
        app = self.make_app('my-app-test', argv=[__file__, '--debug'])
        app.setup()
        self.eq(app.debug, True)

        self.reset_backend()
        defaults = init_defaults('my-app-test')
        defaults['my-app-test']['debug'] = True
        app = self.make_app('my-app-test', argv=[__file__],
                            config_defaults=defaults)
        app.setup()
        self.eq(app.debug, True)

    def test_null_out(self):
        null = foundation.NullOut()
        null.write('nonsense')

    def test_render(self):
        # Render with default
        self.app.setup()
        self.app.render(dict(foo='bar'))

        # Render with no output_handler... this is hackish, but there are
        # circumstances where app.output would be None.
        app = self.make_app('test', output_handler=None)
        app.setup()
        app.output = None
        app.render(dict(foo='bar'))

    @test.raises(exc.FrameworkError)
    def test_bad_label(self):
        try:
            app = foundation.CementApp(None)
        except exc.FrameworkError as e:
            # FIX ME: verify error msg
            raise

    @test.raises(exc.FrameworkError)
    def test_bad_label_chars(self):
        try:
            app = foundation.CementApp('some!bogus()label')
        except exc.FrameworkError as e:
            self.ok(e.msg.find('alpha-numeric'))
            raise

    def test_add_arg_shortcut(self):
        self.app.setup()
        self.app.add_arg('--foo', action='store')

    def test_reset_output_handler(self):
        app = self.make_app('test', argv=[], output_handler=TestOutputHandler)
        app.setup()
        app.run()

        app.output = None

        app._meta.output_handler = None
        app._setup_output_handler()

    def test_lay_cement(self):
        app = self.make_app('test', argv=['--quiet'])
        app = self.make_app('test', argv=['--json', '--yaml'])

    def test_none_member(self):
        class Test(object):
            var = None

        self.app.setup()
        self.app.args.parsed_args = Test()
        try:
            self.app._parse_args()
        except SystemExit:
            pass

    @test.raises(exc.CaughtSignal)
    def test_cement_signal_handler(self):
        import signal
        try:
            foundation.cement_signal_handler(signal.SIGTERM, 5)
        except exc.CaughtSignal as e:
            self.eq(e.signum, signal.SIGTERM)
            self.eq(e.frame, 5)
            raise

    def test_cement_without_signals(self):
        app = self.make_app('test', catch_signals=None)
        app.setup()

    def test_extend(self):
        self.app.extend('kapla', my_extended_func)
        self.eq(self.app.kapla(), 'KAPLA')

    @test.raises(exc.FrameworkError)
    def test_extended_duplicate(self):
        self.app.extend('config', my_extended_func)

    def test_no_handler(self):
        app = self.make_app('myapp')
        app._resolve_handler('cache', None, raise_error=False)

    def test_config_files_is_none(self):
        app = self.make_app('myapp', config_files=None)
        app.setup()

        label = 'myapp'
        user_home = os.path.abspath(os.path.expanduser(os.environ['HOME']))
        files = [
                os.path.join('/', 'etc', label, '%s.conf' % label),
                os.path.join(user_home, '.%s.conf' % label),
                os.path.join(user_home, '.%s' % label, 'config'),
                ]
        for f in files:
            res = f in app._meta.config_files
            self.ok(res)

    @test.raises(exc.FrameworkError)
    def test_base_controller_label(self):
        app = self.make_app('myapp', base_controller=BogusBaseController)
        app.setup()

    def test_pargs(self):
        app = self.make_app(argv=['--debug'])
        app.setup()
        app.run()
        self.eq(app.pargs.debug, True)

    def test_last_rendered(self):
        self.app.setup()
        output_text = self.app.render({'foo':'bar'})
        last_data, last_output = self.app.last_rendered
        self.eq({'foo':'bar'}, last_data)
        self.eq(output_text, last_output)

    def test_get_last_rendered(self):
        ### DEPRECATED - REMOVE AFTER THE FUNCTION IS REMOVED
        self.app.setup()
        output_text = self.app.render({'foo':'bar'})
        last_data, last_output = self.app.get_last_rendered()
        self.eq({'foo':'bar'}, last_data)
        self.eq(output_text, last_output)

########NEW FILE########
__FILENAME__ = handler_tests
"""Tests for cement.core.handler."""

from cement.core import exc, backend, handler, handler, output, meta
from cement.core import interface
from cement.utils import test
from cement.ext.ext_configparser import ConfigParserConfigHandler

class BogusOutputHandler(meta.MetaMixin):
    class Meta:
        #interface = IBogus
        label = 'bogus_handler'

class BogusOutputHandler2(meta.MetaMixin):
    class Meta:
        interface = output.IOutput
        label = 'bogus_handler'

class BogusHandler3(meta.MetaMixin):
    pass   

class BogusHandler4(meta.MetaMixin):
    class Meta:
        interface = output.IOutput
        # label = 'bogus4'

class DuplicateHandler(output.CementOutputHandler):
    class Meta:
        interface = output.IOutput
        label = 'null'

    def _setup(self, config_obj):
        pass
    
    def render(self, data_dict, template=None):
        pass
        
class BogusInterface1(interface.Interface):
    pass
    
class BogusInterface2(interface.Interface):
    class IMeta:
        pass
    
class TestInterface(interface.Interface):
    class IMeta:
        label = 'test'
        
class TestHandler(meta.MetaMixin):
    class Meta:
        interface = TestInterface
        label = 'test'
        
class HandlerTestCase(test.CementCoreTestCase):
    def setUp(self):
        self.app = self.make_app()
        
    @test.raises(exc.FrameworkError)
    def test_get_invalid_handler(self):
        handler.get('output', 'bogus_handler')

    @test.raises(exc.InterfaceError)
    def test_register_invalid_handler(self):
        handler.register(BogusOutputHandler)

    @test.raises(exc.InterfaceError)
    def test_register_invalid_handler_no_meta(self):
        handler.register(BogusHandler3)

    @test.raises(exc.InterfaceError)
    def test_register_invalid_handler_no_Meta_label(self):
        handler.register(BogusHandler4)
    
    @test.raises(exc.FrameworkError)
    def test_register_duplicate_handler(self):
        from cement.ext import ext_nulloutput
        handler.register(ext_nulloutput.NullOutputHandler)
        try:
            handler.register(DuplicateHandler)
        except exc.FrameworkError:
            raise
    
    @test.raises(exc.InterfaceError)
    def test_register_unproviding_handler(self):
        try:
            handler.register(BogusOutputHandler2)
        except exc.InterfaceError:
            del backend.__handlers__['output']
            raise

    def test_verify_handler(self):
        self.app.setup()
        self.ok(handler.registered('output', 'null'))
        self.eq(handler.registered('output', 'bogus_handler'), False)
        self.eq(handler.registered('bogus_type', 'bogus_handler'), False)

    @test.raises(exc.FrameworkError)
    def test_get_bogus_handler(self):
        handler.get('log', 'bogus')

    @test.raises(exc.FrameworkError)
    def test_get_bogus_handler_type(self):
        handler.get('bogus', 'bogus')

    def test_handler_defined(self):
        for handler_type in ['config', 'log', 'argument', 'plugin', 
                             'extension', 'output', 'controller']:
            yield is_defined, handler_type

        # and check for bogus one too
        self.eq(handler.defined('bogus'), False)
    
    def test_handler_list(self):
        self.app.setup()
        handler_list = handler.list('config')
        res = ConfigParserConfigHandler in handler_list
        self.ok(res)
    
    @test.raises(exc.FrameworkError)
    def test_handler_list_bogus_type(self):
        self.app.setup()
        handler_list = handler.list('bogus')
    
    def is_defined(handler_type):
        self.eq(handler.defined(handler_type), True)

    @test.raises(exc.InterfaceError)
    def test_bogus_interface_no_IMeta(self):
        handler.define(BogusInterface1)

    @test.raises(exc.InterfaceError)
    def test_bogus_interface_no_IMeta_label(self):
        handler.define(BogusInterface2)

    @test.raises(exc.FrameworkError)
    def test_define_duplicate_interface(self):
        handler.define(output.IOutput)
        handler.define(output.IOutput)

    def test_interface_with_no_validator(self):
        handler.define(TestInterface)
        handler.register(TestHandler)
    
    def test_handler_defined(self):
        handler.defined('output')
    
    def test_handler_not_defined(self):
        self.eq(handler.defined('bogus'), False)
        
    def test_handler_registered(self):
        self.app.setup()
        self.eq(handler.registered('output', 'null'), True)
    
    def test_handler_get_fallback(self):
        self.app.setup()
        self.eq(handler.get('log', 'foo', 'bar'), 'bar')

########NEW FILE########
__FILENAME__ = hook_tests
"""Tests for cement.core.hook."""

import signal
from cement.core import exc, backend, hook, foundation
from cement.utils import test

def cement_hook_one(*args, **kw):
    return 'kapla 1'

def cement_hook_two(*args, **kw):
    return 'kapla 2'

def cement_hook_three(*args, **kw):
    return 'kapla 3'

def nosetests_hook(*args, **kw):
    return 'kapla 4'

def cement_hook_five(app, data):
    return data
    
class HookTestCase(test.CementCoreTestCase):
    def setUp(self):
        self.app = self.make_app()
        hook.define('nosetests_hook')
        
    def test_define(self):
        self.ok('nosetests_hook' in backend.__hooks__)

    @test.raises(exc.FrameworkError)
    def test_define_again(self):
        try:
            hook.define('nosetests_hook')
        except exc.FrameworkError as e:
            self.eq(e.msg, "Hook name 'nosetests_hook' already defined!")
            raise
    
    def test_hooks_registered(self):
        hook.register('nosetests_hook', cement_hook_one, weight=99)
        hook.register('nosetests_hook', cement_hook_two, weight=-1)
        hook.register('some_bogus_hook', cement_hook_three, weight=-99)
        self.eq(len(backend.__hooks__['nosetests_hook']), 2)
    
    def test_run(self):
        hook.register('nosetests_hook', cement_hook_one, weight=99)
        hook.register('nosetests_hook', cement_hook_two, weight=-1)
        hook.register('nosetests_hook', cement_hook_three, weight=-99)
        
        results = []
        for res in hook.run('nosetests_hook'):
            results.append(res)
    
        self.eq(results[0], 'kapla 3')
        self.eq(results[1], 'kapla 2')
        self.eq(results[2], 'kapla 1')

    @test.raises(exc.FrameworkError)
    def test_run_bad_hook(self):
        for res in hook.run('some_bogus_hook'):
            pass

    def test_hook_is_defined(self):
        self.ok(hook.defined('nosetests_hook'))
        self.eq(hook.defined('some_bogus_hook'), False)
        
    def test_framework_hooks(self):
        app = self.make_app('myapp', argv=['--quiet'])
        hook.register('pre_setup', cement_hook_one)
        hook.register('post_setup', cement_hook_one)
        hook.register('pre_run', cement_hook_one)
        hook.register('post_run', cement_hook_one)
        hook.register('pre_argument_parsing', cement_hook_one)
        hook.register('post_argument_parsing', cement_hook_one)
        hook.register('pre_close', cement_hook_one)
        hook.register('post_close', cement_hook_one)
        hook.register('signal', cement_hook_one)
        hook.register('pre_render', cement_hook_one)
        hook.register('pre_render', cement_hook_five)
        hook.register('post_render', cement_hook_one)
        hook.register('post_render', cement_hook_five)
        app.setup()
        app.run()
        app.render(dict(foo='bar'))
        app.close()
    
        # this is where cement_signal_hook is run
        try:
            foundation.cement_signal_handler(signal.SIGTERM, 5)
        except exc.CaughtSignal as e:
            pass

########NEW FILE########
__FILENAME__ = interface_tests
"""Tests for cement.core.interface."""

from cement.core import exc, interface, output, handler, meta
from cement.utils import test

class TestInterface(interface.Interface):
    class IMeta:
        label = 'test'

class TestHandler(handler.CementBaseHandler):
    class Meta:
        interface = TestInterface
        label = 'test'
        
class TestHandler2(handler.CementBaseHandler):
    class Meta:
        interface = output.IOutput
        label = 'test2'

class TestHandler3():
    pass
    
class InterfaceTestCase(test.CementCoreTestCase):
    def setUp(self):
        self.app = self.make_app()
        
    @test.raises(exc.InterfaceError)
    def test_interface_class(self):
        try:
            i = interface.Interface()
        except exc.InterfaceError as e:
            self.eq(e.msg, "Interfaces can not be used directly.")
            raise

    def test_attribute_class(self):
        i = interface.Attribute('Test attribute')
        self.eq(i.__repr__(), "<interface.Attribute - 'Test attribute'>")

    def test_validator(self):
        interface.validate(TestInterface, TestHandler(), [])
    
    @test.raises(exc.InterfaceError)
    def test_validate_bad_interface(self):
        han = TestHandler2()
        try:
            interface.validate(TestInterface, han, [])
        except exc.InterfaceError as e:
            self.eq(e.msg, "%s does not implement %s." % (han, TestInterface))
            raise
        
    @test.raises(exc.InterfaceError)
    def test_validate_bad_interface_no_meta(self):
        han = TestHandler3()
        try:
            interface.validate(TestInterface, han, [])
        except exc.InterfaceError as e:
            self.eq(e.msg, "Invalid or missing: ['_meta'] in %s" % han)
            raise 

    @test.raises(exc.InterfaceError)
    def test_validate_bad_interface_missing_meta(self):
        han = TestHandler()
        try:
            interface.validate(TestInterface, han, [], ['missing_meta'])
        except exc.InterfaceError as e:
            self.eq(e.msg, "Invalid or missing: ['_meta.missing_meta'] in %s" % han)
            raise

########NEW FILE########
__FILENAME__ = log_tests
"""Tests for cement.core.log."""

import logging
from cement.core import exc, backend, handler, log
from cement.utils import test
from cement.utils.misc import init_defaults

class BogusHandler1(log.CementLogHandler):
    class Meta:
        interface = log.ILog
        label = 'bogus'

class LogTestCase(test.CementCoreTestCase):
    def setUp(self):
        self.app = self.make_app()

    @test.raises(exc.InterfaceError)
    def test_unproviding_handler(self):
        try:
            handler.register(BogusHandler1)
        except exc.InterfaceError:
            raise

    def test_logging(self):
        defaults = init_defaults()
        defaults['log'] = dict(
            file='/dev/null',
            to_console=True
            )
        app = self.make_app(config_defaults=defaults)
        app.setup()
        app.log.info('Info Message')
        app.log.warn('Warn Message')
        app.log.error('Error Message')
        app.log.fatal('Fatal Message')
        app.log.debug('Debug Message')

    def test_bogus_log_level(self):
        app = self.make_app('test')
        app.setup()
        app.config.set('log', 'file', '/dev/null')
        app.config.set('log', 'to_console', True)

        # setup logging again
        app.log._setup(app)
        app.log.set_level('BOGUS')

    def test_get_level(self):
        self.app.setup()
        self.eq('INFO', self.app.log.get_level())

    def test_console_log(self):
        app = self.make_app('test', debug=True)
        app.setup()

        app.config.set('log', 'file', '/dev/null')
        app.config.set('log', 'to_console', True)

        app.log._setup(app)
        app.log.info('Tested.')

########NEW FILE########
__FILENAME__ = meta_tests
"""Cement meta tests."""

from cement.core import backend, exc, meta
from cement.utils import test

class TestMeta(meta.MetaMixin):
    class Meta:
        option_one = 'value one'
        option_two = 'value two'
    
    def __init__(self, **kw):
        super(TestMeta, self).__init__(**kw)
        self.option_three = kw.get('option_three', None)
        
class MetaTestCase(test.CementCoreTestCase):
    def test_passed_kwargs(self):
        t = TestMeta(option_two='some other value', option_three='value three')
        self.eq(t._meta.option_one, 'value one')
        self.eq(t._meta.option_two, 'some other value')
        self.eq(hasattr(t._meta, 'option_three'), False)
        self.eq(t.option_three, 'value three')
    
    

########NEW FILE########
__FILENAME__ = output_tests
"""Tests for cement.core.output."""

import os
from tempfile import mkdtemp
from cement.core import exc, backend, handler, output
from cement.utils import test
from cement.utils.misc import init_defaults

class TestOutputHandler(output.TemplateOutputHandler):
    class Meta:
        label = 'test_output_handler'
    
    def render(self, data, template):
        content = self.load_template(template)
        return content % data

TEST_TEMPLATE = "%(foo)s"

class OutputTestCase(test.CementCoreTestCase):
    def setUp(self):
        self.app = self.make_app()
    
    def test_load_template_from_file(self):
        tmpdir = mkdtemp()
        template = os.path.join(tmpdir, 'mytemplate.txt')
        
        f = open(template, 'w')
        f.write(TEST_TEMPLATE)
        f.close()
        
        app = self.make_app('myapp',
            config_files=[],
            template_dir=tmpdir,
            output_handler=TestOutputHandler,
            )
        app.setup()
        app.run()
        self.ok(app.render(dict(foo='bar'), 'mytemplate.txt'))

    @test.raises(exc.FrameworkError)
    def test_load_template_from_bad_file(self):
        tmpdir = mkdtemp()
        template = os.path.join(tmpdir, 'my-bogus-template.txt')

        app = self.make_app('myapp',
            config_files=[],
            template_dir=tmpdir,
            output_handler=TestOutputHandler,
            )
        app.setup()
        app.run()
        app.render(dict(foo='bar'), 'my-bogus-template.txt')
########NEW FILE########
__FILENAME__ = plugin_tests
"""Tests for cement.core.plugin."""

import os
import sys
import shutil
from tempfile import mkdtemp
from cement.core import exc, backend, plugin, handler
from cement.utils import test
from cement.utils.misc import init_defaults

CONF = """
[myplugin]
enable_plugin = true
foo = bar

"""

CONF2 = """
[myplugin]
enable_plugin = false
foo = bar
"""

CONF3 = """
[bogus_plugin]
foo = bar
"""

CONF4 = """
[ext_json]
enable_plugin = true
foo = bar
"""

CONF5 = ''

PLUGIN = """

from cement.core import handler, output

class TestOutputHandler(output.CementOutputHandler):
    class Meta:
        interface = output.IOutput
        label = 'test_output_handler'

    def _setup(self, app_obj):
        self.app = app_obj

    def render(self, data_dict, template=None):
        pass

def load():
    handler.register(TestOutputHandler)

"""

class PluginTestCase(test.CementCoreTestCase):
    def setUp(self):
        self.app = self.make_app()

    def test_load_plugins_from_files(self):
        tmpdir = mkdtemp()
        f = open(os.path.join(tmpdir, 'myplugin.conf'), 'w')
        f.write(CONF)
        f.close()

        f = open(os.path.join(tmpdir, 'myplugin.py'), 'w')
        f.write(PLUGIN)
        f.close()

        app = self.make_app('myapp',
            config_files=[],
            plugin_config_dir=tmpdir,
            plugin_dir=tmpdir,
            plugin_bootstrap=None,
            )
        app.setup()

        try:
            han = handler.get('output', 'test_output_handler')()
            self.eq(han._meta.label, 'test_output_handler')
        finally:
            shutil.rmtree(tmpdir)

    def test_load_order_presedence_one(self):
        # App config defines it as enabled, even though the plugin config has
        # it disabled... app trumps
        defaults = init_defaults('myapp', 'myplugin')
        defaults['myplugin']['enable_plugin'] = True
        tmpdir = mkdtemp()

        f = open(os.path.join(tmpdir, 'myplugin.conf'), 'w')
        f.write(CONF2)
        f.close()

        f = open(os.path.join(tmpdir, 'myplugin.py'), 'w')
        f.write(PLUGIN)
        f.close()

        app = self.make_app('myapp',
            config_defaults=defaults,
            config_files=[],
            plugin_config_dir=tmpdir,
            plugin_dir=tmpdir,
            plugin_bootstrap=None,
            )
        app.setup()

        try:
            res = 'myplugin' in app.plugin._enabled_plugins
            self.ok(res)

            res = 'myplugin' not in app.plugin._disabled_plugins
            self.ok(res)

        finally:
            shutil.rmtree(tmpdir)

    def test_load_order_presedence_two(self):
        # App config defines it as false, even though the plugin config has
        # it enabled... app trumps
        defaults = init_defaults('myapp', 'myplugin')
        defaults['myplugin']['enable_plugin'] = False
        tmpdir = mkdtemp()

        f = open(os.path.join(tmpdir, 'myplugin.conf'), 'w')
        f.write(CONF)
        f.close()

        f = open(os.path.join(tmpdir, 'myplugin.py'), 'w')
        f.write(PLUGIN)
        f.close()

        app = self.make_app('myapp',
            config_defaults=defaults,
            config_files=[],
            plugin_config_dir=tmpdir,
            plugin_dir=tmpdir,
            plugin_bootstrap=None,
            )
        app.setup()

        try:
            res = 'myplugin' in app.plugin._disabled_plugins
            self.ok(res)

            res = 'myplugin' not in app.plugin._enabled_plugins
            self.ok(res)

        finally:
            shutil.rmtree(tmpdir)

    def test_load_order_presedence_three(self):
        # Multiple plugin configs, first plugin conf defines it as disabled,
        # but last read should make it enabled.
        defaults = init_defaults('myapp', 'myplugin')
        tmpdir = mkdtemp()

        f = open(os.path.join(tmpdir, 'a.conf'), 'w')
        f.write(CONF2) # disabled config
        f.close()

        f = open(os.path.join(tmpdir, 'b.conf'), 'w')
        f.write(CONF) # enabled config
        f.close()

        f = open(os.path.join(tmpdir, 'myplugin.py'), 'w')
        f.write(PLUGIN)
        f.close()

        app = self.make_app('myapp',
            config_defaults=defaults,
            config_files=[],
            plugin_config_dir=tmpdir,
            plugin_dir=tmpdir,
            plugin_bootstrap=None,
            )
        app.setup()

        try:
            res = 'myplugin' in app.plugin._enabled_plugins
            self.ok(res)

            res = 'myplugin' not in app.plugin._disabled_plugins
            self.ok(res)

        finally:
            shutil.rmtree(tmpdir)

    def test_load_order_presedence_four(self):
        # Multiple plugin configs, first plugin conf defines it as enabled,
        # but last read should make it disabled.
        defaults = init_defaults('myapp', 'myplugin')
        tmpdir = mkdtemp()

        f = open(os.path.join(tmpdir, 'a.conf'), 'w')
        f.write(CONF) # enabled config
        f.close()

        f = open(os.path.join(tmpdir, 'b.conf'), 'w')
        f.write(CONF2) # disabled config
        f.close()

        f = open(os.path.join(tmpdir, 'myplugin.py'), 'w')
        f.write(PLUGIN)
        f.close()

        app = self.make_app('myapp',
            config_defaults=defaults,
            config_files=[],
            plugin_config_dir=tmpdir,
            plugin_dir=tmpdir,
            plugin_bootstrap=None,
            )
        app.setup()

        try:
            res = 'myplugin' in app.plugin._disabled_plugins
            self.ok(res)

            res = 'myplugin' not in app.plugin._enabled_plugins
            self.ok(res)

        finally:
            shutil.rmtree(tmpdir)

    def test_load_order_presedence_five(self):
        # Multiple plugin configs, enable -> disabled -> enable
        defaults = init_defaults('myapp', 'myplugin')
        tmpdir = mkdtemp()

        f = open(os.path.join(tmpdir, 'a.conf'), 'w')
        f.write(CONF) # enabled config
        f.close()

        f = open(os.path.join(tmpdir, 'b.conf'), 'w')
        f.write(CONF2) # disabled config
        f.close()

        f = open(os.path.join(tmpdir, 'c.conf'), 'w')
        f.write(CONF) # enabled config
        f.close()

        f = open(os.path.join(tmpdir, 'e.conf'), 'w')
        f.write(CONF2) # disabled config
        f.close()

        f = open(os.path.join(tmpdir, 'f.conf'), 'w')
        f.write(CONF) # enabled config
        f.close()

        f = open(os.path.join(tmpdir, 'myplugin.py'), 'w')
        f.write(PLUGIN)
        f.close()

        app = self.make_app('myapp',
            config_defaults=defaults,
            config_files=[],
            plugin_config_dir=tmpdir,
            plugin_dir=tmpdir,
            plugin_bootstrap=None,
            )
        app.setup()

        try:
            res = 'myplugin' in app.plugin._enabled_plugins
            self.ok(res)

            res = 'myplugin' not in app.plugin._disabled_plugins
            self.ok(res)

        finally:
            shutil.rmtree(tmpdir)

    def test_load_plugins_from_config(self):
        tmpdir = mkdtemp()
        f = open(os.path.join(tmpdir, 'myplugin.py'), 'w')
        f.write(PLUGIN)
        f.close()

        defaults = init_defaults()
        defaults['myplugin'] = dict()
        defaults['myplugin']['enable_plugin'] = True
        defaults['myplugin2'] = dict()
        defaults['myplugin2']['enable_plugin'] = False
        app = self.make_app('myapp', config_defaults=defaults,
            config_files=[],
            plugin_config_dir=tmpdir,
            plugin_dir=tmpdir,
            plugin_bootstrap=None,
            )
        app.setup()

        try:
            han = handler.get('output', 'test_output_handler')()
            self.eq(han._meta.label, 'test_output_handler')
        finally:
            shutil.rmtree(tmpdir)

        # some more checks
        res = 'myplugin' in app.plugin.get_enabled_plugins()
        self.ok(res)

        res = 'myplugin' in app.plugin.get_loaded_plugins()
        self.ok(res)

        res = 'myplugin2' in app.plugin.get_disabled_plugins()
        self.ok(res)

        res = 'myplugin2' not in app.plugin.get_enabled_plugins()
        self.ok(res)

        res = 'myplugin2' not in app.plugin.get_loaded_plugins()
        self.ok(res)

    def test_disabled_plugins_from_files(self):
        tmpdir = mkdtemp()
        f = open(os.path.join(tmpdir, 'myplugin.conf'), 'w')
        f.write(CONF2)
        f.close()

        f = open(os.path.join(tmpdir, 'myplugin.py'), 'w')
        f.write(PLUGIN)
        f.close()

        app = self.make_app('myapp',
            config_files=[],
            plugin_config_dir=tmpdir,
            plugin_dir=tmpdir,
            plugin_bootstrap=None,
            )
        app.setup()
        shutil.rmtree(tmpdir)

        res = 'test_output_handler' not in backend.__handlers__['output']
        self.ok(res)

        res = 'myplugin2' not in app.plugin.get_enabled_plugins()
        self.ok(res)

    def test_bogus_plugin_from_files(self):
        tmpdir = mkdtemp()
        f = open(os.path.join(tmpdir, 'myplugin.conf'), 'w')
        f.write(CONF3)
        f.close()

        # do this for coverage... empty config file
        f = open(os.path.join(tmpdir, 'bogus.conf'), 'w')
        f.write(CONF5)
        f.close()

        app = self.make_app('myapp',
            config_files=[],
            plugin_config_dir=tmpdir,
            plugin_dir=tmpdir,
            plugin_bootstrap=None,
            )
        app.setup()
        shutil.rmtree(tmpdir)

        res = 'bogus_plugin' not in app.plugin.get_enabled_plugins()
        self.ok(res)

    @test.raises(exc.FrameworkError)
    def test_bad_plugin_dir(self):
        tmpdir = mkdtemp()
        f = open(os.path.join(tmpdir, 'myplugin.conf'), 'w')
        f.write(CONF)
        f.close()

        app = self.make_app('myapp',
            config_files=[],
            plugin_config_dir=tmpdir,
            plugin_dir='./some/bogus/path',
            plugin_bootstrap=None,
            )
        try:
            app.setup()
        except ImportError as e:
            raise
        except exc.FrameworkError as e:
            raise
        finally:
            shutil.rmtree(tmpdir)

    def test_load_plugin_from_module(self):
        # We mock this out by loading a cement ext, but it is essentially the
        # same type of code.
        tmpdir = mkdtemp()
        del sys.modules['cement.ext.ext_json']
        f = open(os.path.join(tmpdir, 'ext_json.conf'), 'w')
        f.write(CONF4)
        f.close()

        app = self.make_app('myapp',
            config_files=[],
            plugin_config_dir=tmpdir,
            plugin_dir=tmpdir,
            plugin_bootstrap='cement.ext',
            )
        app.setup()

        res = 'ext_json' in app.plugin.get_enabled_plugins()
        self.ok(res)

        shutil.rmtree(tmpdir)


########NEW FILE########
__FILENAME__ = configobj_tests
"""Tests for cement.ext.ext_configobj."""

import os
import sys
from tempfile import mkstemp
from cement.core import handler, backend, log
from cement.utils import test

if sys.version_info[0] < 3:
    import configobj
else:
    raise test.SkipTest('ConfigObj does not support Python 3') # pragma: no cover


CONFIG = """
[my_section]
my_param = my_value
"""

class ConfigObjExtTestCase(test.CementTestCase):
    def setUp(self):
        _, self.tmppath = mkstemp()
        f = open(self.tmppath, 'w+')
        f.write(CONFIG)
        f.close()
        self.app = self.make_app('myapp',
            extensions=['configobj'],
            config_handler='configobj',
            config_files = [self.tmppath],
            argv=[]
            )

    def tearDown(self):
        if os.path.exists(self.tmppath):
            os.remove(self.tmppath)

    def test_configobj(self):
        self.app.setup()

    def test_has_section(self):
        self.app.setup()
        self.ok(self.app.config.has_section('my_section'))

    def test_keys(self):
        self.app.setup()
        res = 'my_param' in self.app.config.keys('my_section')
        self.ok(res)

    def test_parse_file_bad_path(self):
        self.app._meta.config_files = ['./some_bogus_path']
        self.app.setup()

    def test_parse_file(self):
        self.app.setup()
        self.eq(self.app.config.get('my_section', 'my_param'), 'my_value')

        self.eq(self.app.config.get_section_dict('my_section'),
                {'my_param': 'my_value'})



########NEW FILE########
__FILENAME__ = configparser_tests

from cement.utils import test
from cement.utils.misc import init_defaults

@test.attr('core')
class ConfigParserConfigHandlerTestCase(test.CementExtTestCase):
    pass
########NEW FILE########
__FILENAME__ = daemon_tests
"""Tests for cement.ext.ext_daemon."""

### NOTE: A large portion of ext_daemon is tested, but not included in
### Coverage report because nose/coverage lose sight of things after the
### sub-process is forked.

import os
import tempfile
from random import random
from cement.core import handler, backend, log, hook, exc
from cement.utils import shell
from cement.utils import test
from cement.ext import ext_daemon

class DaemonExtTestCase(test.CementExtTestCase):
    def setUp(self):
        self.app = self.make_app()

    def test_switch(self):
        env = ext_daemon.Environment()
        env.switch()

    def test_switch_with_pid(self):
        (_, tmpfile) = tempfile.mkstemp()
        os.remove(tmpfile)
        env = ext_daemon.Environment(pid_file=tmpfile)
        env.switch()

        try:
            self.ok(os.path.exists(tmpfile))
        finally:
            os.remove(tmpfile)

    @test.raises(exc.FrameworkError)
    def test_pid_exists(self):
        (_, tmpfile) = tempfile.mkstemp()

        env = ext_daemon.Environment(pid_file=tmpfile)
        env.switch()

        try:
            self.ok(os.path.exists(tmpfile))
        except exc.FrameworkError as e:
            self.ok(e.msg.startswith('Process already running'))
            raise
        finally:
            env = ext_daemon.Environment()
            env.switch()
            os.remove(tmpfile)

    @test.raises(exc.FrameworkError)
    def test_bogus_user(self):
        rand = random()

        try:
            env = ext_daemon.Environment(user='cement_test_user%s' % rand)
        except exc.FrameworkError as e:
            self.ok(e.msg.startswith('Daemon user'))
            raise
        finally:
            env = ext_daemon.Environment()
            env.switch()

    @test.raises(exc.FrameworkError)
    def test_bogus_group(self):
        rand = random()

        try:
            env = ext_daemon.Environment(group='cement_test_group%s' % rand)
        except exc.FrameworkError as e:
            self.ok(e.msg.startswith('Daemon group'))
            raise
        finally:
            env = ext_daemon.Environment()
            env.switch()

    def test_daemon(self):
        (_, tmpfile) = tempfile.mkstemp()
        os.remove(tmpfile)
        from cement.utils import shell

        # Test in a sub-process to avoid Nose hangup
        def target():
            app = self.make_app('test', argv=['--daemon'],
                                extensions=['daemon'])

            app.setup()
            app.config.set('daemon', 'pid_file', tmpfile)

            try:
                ### FIX ME: Can't daemonize, because nose loses sight of it
                app.daemonize()
                app.run()
            finally:
                app.close()
                ext_daemon.cleanup(app)

        p = shell.spawn_process(target)
        p.join()
        self.eq(p.exitcode, 0)

    def test_daemon_not_passed(self):
        app = self.make_app('myapp', extensions=['daemon'])

        app.setup()
        app.config.set('daemon', 'pid_file', None)

        try:
            app.run()
        finally:
            ext_daemon.cleanup(app)

########NEW FILE########
__FILENAME__ = genshi_tests
"""Tests for cement.ext.ext_genshi."""

import sys
import random

from cement.core import exc, foundation, handler, backend, controller
from cement.utils import test

if sys.version_info[0] < 3:
    import configobj
else:
    raise test.SkipTest('Genshi does not support Python 3') # pragma: no cover

class GenshiExtTestCase(test.CementExtTestCase):
    def setUp(self):
        self.app = self.make_app('tests',
            extensions=['genshi'],
            output_handler='genshi',
            argv=[]
            )

    def test_genshi(self):
        self.app.setup()
        rando = random.random()
        res = self.app.render(dict(foo=rando), 'test_template.genshi')
        genshi_res = "foo equals %s\n" % rando
        self.eq(res, genshi_res)

    @test.raises(exc.FrameworkError)
    def test_genshi_bad_template(self):
        self.app.setup()
        res = self.app.render(dict(foo='bar'), 'bad_template2.genshi')

    @test.raises(exc.FrameworkError)
    def test_genshi_nonexistent_template(self):
        self.app.setup()
        res = self.app.render(dict(foo='bar'), 'missing_template.genshi')

    @test.raises(exc.FrameworkError)
    def test_genshi_none_template(self):
        self.app.setup()
        try:
            res = self.app.render(dict(foo='bar'), None)
        except exc.FrameworkError as e:
            self.eq(e.msg, "Invalid template path 'None'.")
            raise

    @test.raises(exc.FrameworkError)
    def test_genshi_bad_module(self):
        self.app.setup()
        self.app._meta.template_module = 'this_is_a_bogus_module'
        res = self.app.render(dict(foo='bar'), 'bad_template.genshi')

########NEW FILE########
__FILENAME__ = json_tests
"""Tests for cement.ext.ext_json."""

import json
import sys
from cement.core import handler, backend, hook
from cement.utils import test

class JsonExtTestCase(test.CementExtTestCase):
    def setUp(self):
        self.app = self.make_app('tests', 
            extensions=['json'],
            output_handler='json',
            argv=['--json']
            )
    
    def test_json(self):    
        self.app.setup()
        self.app.run()
        res = self.app.render(dict(foo='bar'))
        json_res = json.dumps(dict(foo='bar'))
        self.eq(res, json_res)

########NEW FILE########
__FILENAME__ = logging_tests
"""Tests for cement.ext.ext_logging."""

import os
import logging
from tempfile import mkstemp
from cement.core import handler, backend, log
from cement.utils import test
from cement.ext import ext_logging
from cement.utils.misc import init_defaults

class MyLog(ext_logging.LoggingLogHandler):
    class Meta:
        label = 'mylog'
        level = 'INFO'

    def __init__(self, *args, **kw):
        super(MyLog, self).__init__(*args, **kw)

@test.attr('core')
class LoggingExtTestCase(test.CementExtTestCase):
    def test_alternate_namespaces(self):
        defaults = init_defaults('myapp', 'log')
        defaults['log']['to_console'] = False
        defaults['log']['file'] = '/dev/null'
        defaults['log']['level'] = 'debug'
        app = self.make_app(config_defaults=defaults)
        app.setup()
        app.log.info('TEST', extra=dict(namespace=__name__))
        app.log.warn('TEST', extra=dict(namespace=__name__))
        app.log.error('TEST', extra=dict(namespace=__name__))
        app.log.fatal('TEST', extra=dict(namespace=__name__))
        app.log.debug('TEST', extra=dict(namespace=__name__))

        app.log.info('TEST', __name__, extra=dict(foo='bar'))
        app.log.warn('TEST', __name__, extra=dict(foo='bar'))
        app.log.error('TEST', __name__, extra=dict(foo='bar'))
        app.log.fatal('TEST', __name__, extra=dict(foo='bar'))
        app.log.debug('TEST', __name__, extra=dict(foo='bar'))

        app.log.info('TEST', __name__)
        app.log.warn('TEST', __name__)
        app.log.error('TEST', __name__)
        app.log.fatal('TEST', __name__)
        app.log.debug('TEST', __name__)

    def test_bad_level(self):
        defaults = init_defaults()
        defaults['log'] = dict(
            level='BOGUS',
            to_console=False,
            )
        app = self.make_app(config_defaults=defaults)
        app.setup()
        self.eq(app.log.get_level(), 'INFO')

    def test_clear_loggers(self):
        self.app.setup()

        han = handler.get('log', 'logging')
        Log = han()
        Log.clear_loggers(self.app._meta.label)

        #previous_logger = logging.getLogger(name)
        MyLog = ext_logging.LoggingLogHandler(clear_loggers="%s:%s" % \
                                             (self.app._meta.label,
                                              self.app._meta.label))
        MyLog._setup(self.app)

    def test_rotate(self):
        log_file = mkstemp()[1]
        defaults = init_defaults()
        defaults['log'] = dict(
            file=log_file,
            level='DEBUG',
            rotate=True,
            max_bytes=10,
            max_files=2,
            )
        app = self.make_app(config_defaults=defaults)
        app.setup()
        app.log.info('test log message')

        # check that a second file was created, because this log is over 12
        # bytes.
        self.ok(os.path.exists("%s.1" % log_file))
        self.ok(os.path.exists("%s.2" % log_file))

        # this file should exist because of max files
        self.eq(os.path.exists("%s.3" % log_file), False)

    def test_missing_log_dir(self):
        _, tmp_path = mkstemp()
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

        defaults = init_defaults()
        defaults['log'] = dict(
            file=os.path.join(tmp_path, 'myapp.log'),
            )
        app = self.make_app(config_defaults=defaults)
        app.setup()

########NEW FILE########
__FILENAME__ = memcached_tests
"""Tests for cement.ext.ext_memcached."""

import sys
from time import sleep
from random import random
from cement.core import handler
from cement.utils import test
from cement.utils.misc import init_defaults

if sys.version_info[0] < 3:
    import pylibmc
else:
    raise test.SkipTest('pylibmc does not support Python 3') # pragma: no cover

class MemcachedExtTestCase(test.CementTestCase):
    def setUp(self):
        self.key = "cement-tests-random-key-%s" % random()
        defaults = init_defaults('tests', 'cache.memcached')
        defaults['cache.memcached']['hosts'] = '127.0.0.1, localhost'
        self.app = self.make_app('tests',
            config_defaults=defaults,
            extensions=['memcached'],
            cache_handler='memcached',
            )
        self.app.setup()

    def tearDown(self):
        self.app.cache.delete(self.key)

    def test_memcache_list_type_config(self):
        defaults = init_defaults('tests', 'cache.memcached')
        defaults['cache.memcached']['hosts'] = ['127.0.0.1', 'localhost']
        self.app = self.make_app('tests',
            config_defaults=defaults,
            extensions=['memcached'],
            cache_handler='memcached',
            )
        self.app.setup()
        self.eq(self.app.config.get('cache.memcached', 'hosts'),
            ['127.0.0.1', 'localhost'])

    def test_memcache_str_type_config(self):
        defaults = init_defaults('tests', 'cache.memcached')
        defaults['cache.memcached']['hosts'] = '127.0.0.1, localhost'
        self.app = self.make_app('tests',
            config_defaults=defaults,
            extensions=['memcached'],
            cache_handler='memcached',
            )
        self.app.setup()
        self.eq(self.app.config.get('cache.memcached', 'hosts'),
            ['127.0.0.1', 'localhost'])

    def test_memcached_set(self):
        self.app.cache.set(self.key, 1001)
        self.eq(self.app.cache.get(self.key), 1001)

    def test_memcached_get(self):
        # get empty value
        self.app.cache.delete(self.key)
        self.eq(self.app.cache.get(self.key), None)

        # get empty value with fallback
        self.eq(self.app.cache.get(self.key, 1234), 1234)

    def test_memcached_delete(self):
        self.app.cache.delete(self.key)

    def test_memcached_purge(self):
        self.app.cache.set(self.key, 1002)
        self.app.cache.purge()
        self.eq(self.app.cache.get(self.key), None)

    def test_memcache_expire(self):
        self.app.cache.set(self.key, 1003, time=2)
        sleep(3)
        self.eq(self.app.cache.get(self.key), None)


########NEW FILE########
__FILENAME__ = mustache_tests
"""Tests for cement.ext.ext_mustache."""

import sys
import random

from cement.core import exc, foundation, handler, backend, controller
from cement.utils import test


class MustacheExtTestCase(test.CementExtTestCase):
    def setUp(self):
        self.app = self.make_app('tests',
            extensions=['mustache'],
            output_handler='mustache',
            argv=[]
            )

    def test_mustache(self):
        self.app.setup()
        rando = random.random()
        res = self.app.render(dict(foo=rando), 'test_template.mustache')
        mustache_res = "foo equals %s\n" % rando
        self.eq(res, mustache_res)

    @test.raises(exc.FrameworkError)
    def test_mustache_bad_template(self):
        self.app.setup()
        res = self.app.render(dict(foo='bar'), 'bad_template2.mustache')

    @test.raises(exc.FrameworkError)
    def test_mustache_nonexistent_template(self):
        self.app.setup()
        res = self.app.render(dict(foo='bar'), 'missing_template.mustache')

    @test.raises(exc.FrameworkError)
    def test_mustache_none_template(self):
        self.app.setup()
        try:
            res = self.app.render(dict(foo='bar'), None)
        except exc.FrameworkError as e:
            self.eq(e.msg, "Invalid template path 'None'.")
            raise

    @test.raises(exc.FrameworkError)
    def test_mustache_bad_module(self):
        self.app.setup()
        self.app._meta.template_module = 'this_is_a_bogus_module'
        res = self.app.render(dict(foo='bar'), 'bad_template.mustache')

########NEW FILE########
__FILENAME__ = yaml_tests
"""Tests for cement2.ext.ext_yaml."""

import yaml
from cement.core import handler, hook
from cement.utils import test

class YamlExtTestCase(test.CementTestCase):
    def setUp(self):
        self.app = self.make_app('tests',
            extensions=['yaml'],
            output_handler='yaml',
            argv=['--yaml']
            )

    def test_yaml(self):
        self.app.setup()
        self.app.run()
        res = self.app.render(dict(foo='bar'))
        yaml_res = yaml.dump(dict(foo='bar'))
        self.eq(res, yaml_res)

########NEW FILE########
__FILENAME__ = fs_tests
"""Tests for cement.utils.fs"""

import os
import tempfile
from cement.utils import fs, test

class FsUtilsTestCase(test.CementCoreTestCase):
    def test_abspath(self):
        path = fs.abspath('.')
        self.ok(path.startswith('/'))
    
    def test_backup(self):
        _, tmpfile = tempfile.mkstemp()
        bkfile = fs.backup(tmpfile)
        self.eq("%s.bak" % os.path.basename(tmpfile), os.path.basename(bkfile))
        bkfile = fs.backup(tmpfile)
        self.eq("%s.bak.0" % os.path.basename(tmpfile), os.path.basename(bkfile))
        bkfile = fs.backup(tmpfile)
        self.eq("%s.bak.1" % os.path.basename(tmpfile), os.path.basename(bkfile))
        
        tmpdir = tempfile.mkdtemp()
        bkdir = fs.backup(tmpdir)
        self.eq("%s.bak" % os.path.basename(tmpdir), os.path.basename(bkdir))
        
        res = fs.backup('someboguspath')
        self.eq(res, None)
########NEW FILE########
__FILENAME__ = misc_tests
"""Tests for cement.utils.misc."""

from cement.utils import test, misc

class BackendTestCase(test.CementCoreTestCase):
    def test_defaults(self):
        defaults = misc.init_defaults('myapp', 'section2', 'section3')
        defaults['myapp']['debug'] = True
        defaults['section2']['foo'] = 'bar'
        self.app = self.make_app('myapp', config_defaults=defaults)
        self.app.setup()
        self.eq(self.app.config.get('myapp', 'debug'), True)
        self.ok(self.app.config.get_section_dict('section2'))

    def test_minimal_logger(self):
        log = misc.minimal_logger(__name__)
        log = misc.minimal_logger(__name__, debug=True)
        log.info('info test')
        log.warn('warn test')
        log.error('error test')
        log.fatal('fatal test')
        log.debug('debug test')

        log.info('info test with namespce', 'test_namespace')

        log.info('info test with extra kwargs', extra=dict(foo='bar'))

        log.info('info test with extra kwargs', extra=dict(namespace='foo'))

        # set logging back to non-debug
        misc.minimal_logger(__name__, debug=False)
        pass

    def test_wrap_str(self):
        text = "aaaaa bbbbb ccccc"
        new_text = misc.wrap(text, width=5)
        parts = new_text.split('\n')
        self.eq(len(parts), 3)
        self.eq(parts[1], 'bbbbb')

        new_text = misc.wrap(text, width=5, indent='***')
        parts = new_text.split('\n')
        self.eq(parts[2], '***ccccc')

    @test.raises(TypeError)
    def test_wrap_int(self):
        text = int('1' * 80)
        try:
            new_text = misc.wrap(text, width=5)
        except TypeError as e:
            self.eq(e.args[0], "`text` must be a string.")
            raise

    @test.raises(TypeError)
    def test_wrap_none(self):
        text = None
        try:
            new_text = misc.wrap(text, width=5)
        except TypeError as e:
            self.eq(e.args[0], "`text` must be a string.")
            raise

########NEW FILE########
__FILENAME__ = shell_tests
"""Tests for cement.utils.shell"""

import time
from cement.utils import shell, test

def add(a, b):
    return a + b
    
class ShellUtilsTestCase(test.CementCoreTestCase):
    def test_exec_cmd(self):
        out, err, ret = shell.exec_cmd(['echo', 'KAPLA!'])
        self.eq(ret, 0)
        self.eq(out, b'KAPLA!\n')
        
    def test_exec_cmd_shell_true(self):
        out, err, ret = shell.exec_cmd(['echo KAPLA!'], shell=True)
        self.eq(ret, 0)
        self.eq(out, b'KAPLA!\n')
        
    def test_exec_cmd2(self):
        ret = shell.exec_cmd2(['echo'])
        self.eq(ret, 0)
        
    def test_exec_cmd2_shell_true(self):
        ret = shell.exec_cmd2(['echo johnny'], shell=True)
        self.eq(ret, 0)
    
    def test_exec_cmd_bad_command(self):
        out, err, ret = shell.exec_cmd(['false'])
        self.eq(ret, 1)
    
    def test_exec_cmd2_bad_command(self):
        ret = shell.exec_cmd2(['false'])
        self.eq(ret, 1)
    
    def test_spawn_process(self):
        p = shell.spawn_process(add, args=(23, 2))
        p.join()
        self.eq(p.exitcode, 0)
        
        p = shell.spawn_process(add, join=True, args=(23, 2))
        self.eq(p.exitcode, 0)
        
    def test_spawn_thread(self):
        t = shell.spawn_thread(time.sleep, args=(10))
        
        # before joining it is alive
        res = t.is_alive()
        self.eq(res, True)
        
        t.join()
        
        # after joining it is not alive
        res = t.is_alive()
        self.eq(res, False)
        
        t = shell.spawn_thread(time.sleep, join=True, args=(10))
        res = t.is_alive()
        self.eq(res, False)

########NEW FILE########
__FILENAME__ = version_tests
"""Tests for cement.utils.version."""

from cement.utils import version, test

class VersionUtilsTestCase(test.CementCoreTestCase):
    def test_get_version(self):
        ver = version.get_version()
        self.ok(ver.startswith('2.3'))

        ver = version.get_version((2, 1, 1, 'alpha', 1))
        self.eq(ver, '2.1.1a1')

        ver = version.get_version((2, 1, 2, 'beta', 2))
        self.eq(ver, '2.1.2b2')

        ver = version.get_version((2, 1, 2, 'rc', 3))
        self.eq(ver, '2.1.2c3')

########NEW FILE########
