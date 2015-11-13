__FILENAME__ = app
"""Application base class.
"""

import argparse
import codecs
import locale
import logging
import logging.handlers
import os
import sys

from .complete import CompleteCommand
from .help import HelpAction, HelpCommand
from .interactive import InteractiveApp

# Make sure the cliff library has a logging handler
# in case the app developer doesn't set up logging.
# For py26 compat, create a NullHandler

if hasattr(logging, 'NullHandler'):
    NullHandler = logging.NullHandler
else:
    class NullHandler(logging.Handler):
        def handle(self, record):
            pass

        def emit(self, record):
            pass

        def createLock(self):
            self.lock = None

logging.getLogger('cliff').addHandler(NullHandler())


LOG = logging.getLogger(__name__)


class App(object):
    """Application base class.

    :param description: one-liner explaining the program purpose
    :paramtype description: str
    :param version: application version number
    :paramtype version: str
    :param command_manager: plugin loader
    :paramtype command_manager: cliff.commandmanager.CommandManager
    :param stdin: Standard input stream
    :paramtype stdin: readable I/O stream
    :param stdout: Standard output stream
    :paramtype stdout: writable I/O stream
    :param stderr: Standard error output stream
    :paramtype stderr: writable I/O stream
    :param interactive_app_factory: callable to create an
                                    interactive application
    :paramtype interactive_app_factory: cliff.interactive.InteractiveApp
    """

    NAME = os.path.splitext(os.path.basename(sys.argv[0]))[0]

    CONSOLE_MESSAGE_FORMAT = '%(message)s'
    LOG_FILE_MESSAGE_FORMAT = \
        '[%(asctime)s] %(levelname)-8s %(name)s %(message)s'
    DEFAULT_VERBOSE_LEVEL = 1
    DEFAULT_OUTPUT_ENCODING = 'utf-8'

    def __init__(self, description, version, command_manager,
                 stdin=None, stdout=None, stderr=None,
                 interactive_app_factory=InteractiveApp):
        """Initialize the application.
        """
        self.command_manager = command_manager
        self.command_manager.add_command('help', HelpCommand)
        self.command_manager.add_command('complete', CompleteCommand)
        self._set_streams(stdin, stdout, stderr)
        self.interactive_app_factory = interactive_app_factory
        self.parser = self.build_option_parser(description, version)
        self.interactive_mode = False
        self.interpreter = None

    def _set_streams(self, stdin, stdout, stderr):
        locale.setlocale(locale.LC_ALL, '')
        if sys.version_info[:2] == (2, 6):
            # Configure the input and output streams. If a stream is
            # provided, it must be configured correctly by the
            # caller. If not, make sure the versions of the standard
            # streams used by default are wrapped with encodings. This
            # works around a problem with Python 2.6 fixed in 2.7 and
            # later (http://hg.python.org/cpython/rev/e60ef17561dc/).
            lang, encoding = locale.getdefaultlocale()
            encoding = (getattr(sys.stdout, 'encoding', None)
                        or encoding
                        or self.DEFAULT_OUTPUT_ENCODING
                        )
            self.stdin = stdin or codecs.getreader(encoding)(sys.stdin)
            self.stdout = stdout or codecs.getwriter(encoding)(sys.stdout)
            self.stderr = stderr or codecs.getwriter(encoding)(sys.stderr)
        else:
            self.stdin = stdin or sys.stdin
            self.stdout = stdout or sys.stdout
            self.stderr = stderr or sys.stderr

    def build_option_parser(self, description, version,
                            argparse_kwargs=None):
        """Return an argparse option parser for this application.

        Subclasses may override this method to extend
        the parser with more global options.

        :param description: full description of the application
        :paramtype description: str
        :param version: version number for the application
        :paramtype version: str
        :param argparse_kwargs: extra keyword argument passed to the
                                ArgumentParser constructor
        :paramtype extra_kwargs: dict
        """
        argparse_kwargs = argparse_kwargs or {}
        parser = argparse.ArgumentParser(
            description=description,
            add_help=False,
            **argparse_kwargs
        )
        parser.add_argument(
            '--version',
            action='version',
            version='%(prog)s {0}'.format(version),
        )
        parser.add_argument(
            '-v', '--verbose',
            action='count',
            dest='verbose_level',
            default=self.DEFAULT_VERBOSE_LEVEL,
            help='Increase verbosity of output. Can be repeated.',
        )
        parser.add_argument(
            '--log-file',
            action='store',
            default=None,
            help='Specify a file to log output. Disabled by default.',
        )
        parser.add_argument(
            '-q', '--quiet',
            action='store_const',
            dest='verbose_level',
            const=0,
            help='suppress output except warnings and errors',
        )
        parser.add_argument(
            '-h', '--help',
            action=HelpAction,
            nargs=0,
            default=self,  # tricky
            help="show this help message and exit",
        )
        parser.add_argument(
            '--debug',
            default=False,
            action='store_true',
            help='show tracebacks on errors',
        )
        return parser

    def configure_logging(self):
        """Create logging handlers for any log output.
        """
        root_logger = logging.getLogger('')
        root_logger.setLevel(logging.DEBUG)

        # Set up logging to a file
        if self.options.log_file:
            file_handler = logging.FileHandler(
                filename=self.options.log_file,
            )
            formatter = logging.Formatter(self.LOG_FILE_MESSAGE_FORMAT)
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)

        # Always send higher-level messages to the console via stderr
        console = logging.StreamHandler(self.stderr)
        console_level = {0: logging.WARNING,
                         1: logging.INFO,
                         2: logging.DEBUG,
                         }.get(self.options.verbose_level, logging.DEBUG)
        console.setLevel(console_level)
        formatter = logging.Formatter(self.CONSOLE_MESSAGE_FORMAT)
        console.setFormatter(formatter)
        root_logger.addHandler(console)
        return

    def run(self, argv):
        """Equivalent to the main program for the application.

        :param argv: input arguments and options
        :paramtype argv: list of str
        """
        try:
            self.options, remainder = self.parser.parse_known_args(argv)
            self.configure_logging()
            self.interactive_mode = not remainder
            self.initialize_app(remainder)
        except Exception as err:
            if hasattr(self, 'options'):
                debug = self.options.debug
            else:
                debug = True
            if debug:
                LOG.exception(err)
                raise
            else:
                LOG.error(err)
            return 1
        result = 1
        if self.interactive_mode:
            result = self.interact()
        else:
            result = self.run_subcommand(remainder)
        return result

    # FIXME(dhellmann): Consider moving these command handling methods
    # to a separate class.
    def initialize_app(self, argv):
        """Hook for subclasses to take global initialization action
        after the arguments are parsed but before a command is run.
        Invoked only once, even in interactive mode.

        :param argv: List of arguments, including the subcommand to run.
                     Empty for interactive mode.
        """
        return

    def prepare_to_run_command(self, cmd):
        """Perform any preliminary work needed to run a command.

        :param cmd: command processor being invoked
        :paramtype cmd: cliff.command.Command
        """
        return

    def clean_up(self, cmd, result, err):
        """Hook run after a command is done to shutdown the app.

        :param cmd: command processor being invoked
        :paramtype cmd: cliff.command.Command
        :param result: return value of cmd
        :paramtype result: int
        :param err: exception or None
        :paramtype err: Exception
        """
        return

    def interact(self):
        self.interpreter = self.interactive_app_factory(self,
                                                        self.command_manager,
                                                        self.stdin,
                                                        self.stdout,
                                                        )
        self.interpreter.cmdloop()
        return 0

    def run_subcommand(self, argv):
        try:
            subcommand = self.command_manager.find_command(argv)
        except ValueError as err:
            if self.options.debug:
                raise
            else:
                LOG.error(err)
            return 2
        cmd_factory, cmd_name, sub_argv = subcommand
        cmd = cmd_factory(self, self.options)
        err = None
        result = 1
        try:
            self.prepare_to_run_command(cmd)
            full_name = (cmd_name
                         if self.interactive_mode
                         else ' '.join([self.NAME, cmd_name])
                         )
            cmd_parser = cmd.get_parser(full_name)
            parsed_args = cmd_parser.parse_args(sub_argv)
            result = cmd.run(parsed_args)
        except Exception as err:
            if self.options.debug:
                LOG.exception(err)
            else:
                LOG.error(err)
            try:
                self.clean_up(cmd, result, err)
            except Exception as err2:
                if self.options.debug:
                    LOG.exception(err2)
                else:
                    LOG.error('Could not clean up: %s', err2)
            if self.options.debug:
                raise
        else:
            try:
                self.clean_up(cmd, result, None)
            except Exception as err3:
                if self.options.debug:
                    LOG.exception(err3)
                else:
                    LOG.error('Could not clean up: %s', err3)
        return result

########NEW FILE########
__FILENAME__ = command

import abc
import argparse
import inspect


class Command(object):
    """Base class for command plugins.

    :param app: Application instance invoking the command.
    :paramtype app: cliff.app.App
    """
    __metaclass__ = abc.ABCMeta

    def __init__(self, app, app_args):
        self.app = app
        self.app_args = app_args
        return

    def get_description(self):
        """Return the command description.
        """
        return inspect.getdoc(self.__class__) or ''

    def get_parser(self, prog_name):
        """Return an :class:`argparse.ArgumentParser`.
        """
        parser = argparse.ArgumentParser(
            description=self.get_description(),
            prog=prog_name,
        )
        return parser

    @abc.abstractmethod
    def take_action(self, parsed_args):
        """Override to do something useful.
        """

    def run(self, parsed_args):
        """Invoked by the application when the command is run.

        Developers implementing commands should override
        :meth:`take_action`.

        Developers creating new command base classes (such as
        :class:`Lister` and :class:`ShowOne`) should override this
        method to wrap :meth:`take_action`.
        """
        self.take_action(parsed_args)
        return 0

########NEW FILE########
__FILENAME__ = commandmanager
"""Discover and lookup command plugins.
"""

import logging

import pkg_resources


LOG = logging.getLogger(__name__)


class EntryPointWrapper(object):
    """Wrap up a command class already imported to make it look like a plugin.
    """

    def __init__(self, name, command_class):
        self.name = name
        self.command_class = command_class

    def load(self):
        return self.command_class


class CommandManager(object):
    """Discovers commands and handles lookup based on argv data.

    :param namespace: String containing the setuptools entrypoint namespace
                      for the plugins to be loaded. For example,
                      ``'cliff.formatter.list'``.
    :param convert_underscores: Whether cliff should convert underscores to
                                to spaces in entry_point commands.
    """
    def __init__(self, namespace, convert_underscores=True):
        self.commands = {}
        self.namespace = namespace
        self.convert_underscores = convert_underscores
        self._load_commands()

    def _load_commands(self):
        for ep in pkg_resources.iter_entry_points(self.namespace):
            LOG.debug('found command %r', ep.name)
            cmd_name = (ep.name.replace('_', ' ')
                        if self.convert_underscores
                        else ep.name)
            self.commands[cmd_name] = ep
        return

    def __iter__(self):
        return iter(self.commands.items())

    def add_command(self, name, command_class):
        self.commands[name] = EntryPointWrapper(name, command_class)

    def find_command(self, argv):
        """Given an argument list, find a command and
        return the processor and any remaining arguments.
        """
        search_args = argv[:]
        name = ''
        while search_args:
            if search_args[0].startswith('-'):
                raise ValueError('Invalid command %r' % search_args[0])
            next_val = search_args.pop(0)
            name = '%s %s' % (name, next_val) if name else next_val
            if name in self.commands:
                cmd_ep = self.commands[name]
                cmd_factory = cmd_ep.load()
                return (cmd_factory, name, search_args)
        else:
            raise ValueError('Unknown command %r' %
                             (argv,))

########NEW FILE########
__FILENAME__ = complete

"""Bash completion for the CLI.
"""

import logging

import six
import stevedore

from cliff import command


class CompleteDictionary:
    """dictionary for bash completion
    """

    def __init__(self):
        self._dictionary = {}

    def add_command(self, command, actions):
        optstr = ' '.join(opt for action in actions
                          for opt in action.option_strings)
        dicto = self._dictionary
        for subcmd in command[:-1]:
            dicto = dicto.setdefault(subcmd, {})
        dicto[command[-1]] = optstr

    def get_commands(self):
        return ' '.join(k for k in sorted(self._dictionary.keys()))

    def _get_data_recurse(self, dictionary, path):
        ray = []
        keys = sorted(dictionary.keys())
        for cmd in keys:
            name = path + "_" + cmd if path else cmd
            value = dictionary[cmd]
            if isinstance(value, six.string_types):
                ray.append((name, value))
            else:
                cmdlist = ' '.join(sorted(value.keys()))
                ray.append((name, cmdlist))
                ray += self._get_data_recurse(value, name)
        return ray

    def get_data(self):
        return sorted(self._get_data_recurse(self._dictionary, ""))


class CompleteShellBase(object):
    """base class for bash completion generation
    """
    def __init__(self, name, output):
        self.name = str(name)
        self.output = output

    def write(self, cmdo, data):
        self.output.write(self.get_header())
        self.output.write("  cmds='{0}'\n".format(cmdo))
        for datum in data:
            self.output.write('  cmds_{0}=\'{1}\'\n'.format(*datum))
        self.output.write(self.get_trailer())


class CompleteNoCode(CompleteShellBase):
    """completion with no code
    """
    def __init__(self, name, output):
        super(CompleteNoCode, self).__init__(name, output)

    def get_header(self):
        return ''

    def get_trailer(self):
        return ''


class CompleteBash(CompleteShellBase):
    """completion for bash
    """
    def __init__(self, name, output):
        super(CompleteBash, self).__init__(name, output)

    def get_header(self):
        return ('_' + self.name + """()
{
  local cur prev words
  COMPREPLY=()
  _get_comp_words_by_ref -n : cur prev words

  # Command data:
""")

    def get_trailer(self):
        return ("""
  cmd=""
  words[0]=""
  completed="${cmds}"
  for var in "${words[@]:1}"
  do
    if [[ ${var} == -* ]] ; then
      break
    fi
    if [ -z "${cmd}" ] ; then
      proposed="${var}"
    else
      proposed="${cmd}_${var}"
    fi
    local i="cmds_${proposed}"
    local comp="${!i}"
    if [ -z "${comp}" ] ; then
      break
    fi
    if [[ ${comp} == -* ]] ; then
      if [[ ${cur} != -* ]] ; then
        completed=""
        break
      fi
    fi
    cmd="${proposed}"
    completed="${comp}"
  done

  if [ -z "${completed}" ] ; then
    COMPREPLY=( $( compgen -f -- "$cur" ) $( compgen -d -- "$cur" ) )
  else
    COMPREPLY=( $(compgen -W "${completed}" -- ${cur}) )
  fi
  return 0
}
complete -F _""" + self.name + ' ' + self.name + '\n')


class CompleteCommand(command.Command):
    """print bash completion command
    """

    log = logging.getLogger(__name__ + '.CompleteCommand')

    def __init__(self, app, app_args):
        super(CompleteCommand, self).__init__(app, app_args)
        self._formatters = stevedore.ExtensionManager(
            namespace='cliff.formatter.completion',
        )

    def get_parser(self, prog_name):
        parser = super(CompleteCommand, self).get_parser(prog_name)
        parser.add_argument(
            "--name",
            default=None,
            metavar='<command_name>',
            help="Command name to support with command completion"
        )
        parser.add_argument(
            "--shell",
            default='bash',
            metavar='<shell>',
            choices=sorted(self._formatters.names()),
            help="Shell being used. Use none for data only (default: bash)"
        )
        return parser

    def get_actions(self, command):
        the_cmd = self.app.command_manager.find_command(command)
        cmd_factory, cmd_name, search_args = the_cmd
        cmd = cmd_factory(self.app, search_args)
        if self.app.interactive_mode:
            full_name = (cmd_name)
        else:
            full_name = (' '.join([self.app.NAME, cmd_name]))
        cmd_parser = cmd.get_parser(full_name)
        return cmd_parser._get_optional_actions()

    def take_action(self, parsed_args):
        self.log.debug('take_action(%s)' % parsed_args)

        name = parsed_args.name or self.app.NAME
        try:
            shell_factory = self._formatters[parsed_args.shell].plugin
        except KeyError:
            raise RuntimeError('Unknown shell syntax %r' % parsed_args.shell)
        shell = shell_factory(name, self.app.stdout)

        dicto = CompleteDictionary()
        for cmd in self.app.command_manager:
            command = cmd[0].split()
            dicto.add_command(command, self.get_actions(command))

        shell.write(dicto.get_commands(), dicto.get_data())

        return 0

########NEW FILE########
__FILENAME__ = display
"""Application base class for displaying data.
"""
import abc
import logging

import stevedore

from .command import Command


LOG = logging.getLogger(__name__)


class DisplayCommandBase(Command):
    """Command base class for displaying data about a single object.
    """
    __metaclass__ = abc.ABCMeta

    def __init__(self, app, app_args):
        super(DisplayCommandBase, self).__init__(app, app_args)
        self.formatters = self._load_formatter_plugins()

    @abc.abstractproperty
    def formatter_namespace(self):
        "String specifying the namespace to use for loading formatter plugins."

    @abc.abstractproperty
    def formatter_default(self):
        "String specifying the name of the default formatter."

    def _load_formatter_plugins(self):
        # Here so tests can override
        return stevedore.ExtensionManager(
            self.formatter_namespace,
            invoke_on_load=True,
        )

    def get_parser(self, prog_name):
        parser = super(DisplayCommandBase, self).get_parser(prog_name)
        formatter_group = parser.add_argument_group(
            title='output formatters',
            description='output formatter options',
        )
        formatter_choices = sorted(self.formatters.names())
        formatter_default = self.formatter_default
        if formatter_default not in formatter_choices:
            formatter_default = formatter_choices[0]
        formatter_group.add_argument(
            '-f', '--format',
            dest='formatter',
            action='store',
            choices=formatter_choices,
            default=formatter_default,
            help='the output format, defaults to %s' % formatter_default,
        )
        formatter_group.add_argument(
            '-c', '--column',
            action='append',
            default=[],
            dest='columns',
            metavar='COLUMN',
            help='specify the column(s) to include, can be repeated',
        )
        for formatter in self.formatters:
            formatter.obj.add_argument_group(parser)
        return parser

    @abc.abstractmethod
    def produce_output(self, parsed_args, column_names, data):
        """Use the formatter to generate the output.

        :param parsed_args: argparse.Namespace instance with argument values
        :param column_names: sequence of strings containing names
                             of output columns
        :param data: iterable with values matching the column names
        """

    def run(self, parsed_args):
        self.formatter = self.formatters[parsed_args.formatter].obj
        column_names, data = self.take_action(parsed_args)
        self.produce_output(parsed_args, column_names, data)
        return 0

########NEW FILE########
__FILENAME__ = base
"""Base classes for formatters.
"""

import abc


class Formatter(object):
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def add_argument_group(self, parser):
        """Add any options to the argument parser.

        Should use our own argument group.
        """


class ListFormatter(Formatter):
    """Base class for formatters that know how to deal with multiple objects.
    """
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def emit_list(self, column_names, data, stdout, parsed_args):
        """Format and print the list from the iterable data source.

        :param column_names: names of the columns
        :param data: iterable data source, one tuple per object
                     with values in order of column names
        :param stdout: output stream where data should be written
        :param parsed_args: argparse namespace from our local options
        """


class SingleFormatter(Formatter):
    """Base class for formatters that work with single objects.
    """
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def emit_one(self, column_names, data, stdout, parsed_args):
        """Format and print the values associated with the single object.

        :param column_names: names of the columns
        :param data: iterable data source with values in order of column names
        :param stdout: output stream where data should be written
        :param parsed_args: argparse namespace from our local options
        """

########NEW FILE########
__FILENAME__ = commaseparated
"""Output formatters using csv format.
"""

import csv

from .base import ListFormatter


class CSVLister(ListFormatter):

    QUOTE_MODES = {
        'all': csv.QUOTE_ALL,
        'minimal': csv.QUOTE_MINIMAL,
        'nonnumeric': csv.QUOTE_NONNUMERIC,
        'none': csv.QUOTE_NONE,
    }

    def add_argument_group(self, parser):
        group = parser.add_argument_group('CSV Formatter')
        group.add_argument(
            '--quote',
            choices=sorted(self.QUOTE_MODES.keys()),
            dest='quote_mode',
            default='nonnumeric',
            help='when to include quotes, defaults to nonnumeric',
        )

    def emit_list(self, column_names, data, stdout, parsed_args):
        writer = csv.writer(stdout,
                            quoting=self.QUOTE_MODES[parsed_args.quote_mode],
                            )
        writer.writerow(column_names)
        for row in data:
            writer.writerow(row)
        return

########NEW FILE########
__FILENAME__ = shell
"""Output formatters using shell syntax.
"""

from .base import SingleFormatter


class ShellFormatter(SingleFormatter):

    def add_argument_group(self, parser):
        group = parser.add_argument_group(
            title='shell formatter',
            description='a format a UNIX shell can parse (variable="value")',
        )
        group.add_argument(
            '--variable',
            action='append',
            default=[],
            dest='variables',
            metavar='VARIABLE',
            help='specify the variable(s) to include, can be repeated',
        )
        group.add_argument(
            '--prefix',
            action='store',
            default='',
            dest='prefix',
            help='add a prefix to all variable names',
        )

    def emit_one(self, column_names, data, stdout, parsed_args):
        variable_names = [c.lower().replace(' ', '_')
                          for c in column_names
                          ]
        desired_columns = parsed_args.variables
        for name, value in zip(variable_names, data):
            if name in desired_columns or not desired_columns:
                stdout.write('%s%s="%s"\n' % (parsed_args.prefix, name, value))
        return

########NEW FILE########
__FILENAME__ = table
"""Output formatters using prettytable.
"""

import prettytable

from .base import ListFormatter, SingleFormatter


class TableFormatter(ListFormatter, SingleFormatter):

    ALIGNMENTS = {
        int: 'r',
        str: 'l',
        float: 'r',
    }
    try:
        ALIGNMENTS[unicode] = 'l'
    except NameError:
        pass

    def add_argument_group(self, parser):
        pass

    def emit_list(self, column_names, data, stdout, parsed_args):
        x = prettytable.PrettyTable(
            column_names,
            print_empty=False,
        )
        x.padding_width = 1
        # Figure out the types of the columns in the
        # first row and set the alignment of the
        # output accordingly.
        data_iter = iter(data)
        try:
            first_row = next(data_iter)
        except StopIteration:
            pass
        else:
            for value, name in zip(first_row, column_names):
                alignment = self.ALIGNMENTS.get(type(value), 'l')
                x.align[name] = alignment
            # Now iterate over the data and add the rows.
            x.add_row(first_row)
            for row in data_iter:
                x.add_row(row)
        formatted = x.get_string(fields=column_names)
        stdout.write(formatted)
        stdout.write('\n')
        return

    def emit_one(self, column_names, data, stdout, parsed_args):
        x = prettytable.PrettyTable(field_names=('Field', 'Value'),
                                    print_empty=False)
        x.padding_width = 1
        # Align all columns left because the values are
        # not all the same type.
        x.align['Field'] = 'l'
        x.align['Value'] = 'l'
        for name, value in zip(column_names, data):
            x.add_row((name, value))
        formatted = x.get_string(fields=('Field', 'Value'))
        stdout.write(formatted)
        stdout.write('\n')
        return

########NEW FILE########
__FILENAME__ = help
import argparse
import sys
import traceback

from .command import Command


class HelpAction(argparse.Action):
    """Provide a custom action so the -h and --help options
    to the main app will print a list of the commands.

    The commands are determined by checking the CommandManager
    instance, passed in as the "default" value for the action.
    """
    def __call__(self, parser, namespace, values, option_string=None):
        app = self.default
        parser.print_help(app.stdout)
        app.stdout.write('\nCommands:\n')
        command_manager = app.command_manager
        for name, ep in sorted(command_manager):
            try:
                factory = ep.load()
            except Exception as err:
                app.stdout.write('Could not load %r\n' % ep)
                if namespace.debug:
                    traceback.print_exc(file=app.stdout)
                continue
            try:
                cmd = factory(app, None)
            except Exception as err:
                app.stdout.write('Could not instantiate %r: %s\n' % (ep, err))
                if namespace.debug:
                    traceback.print_exc(file=app.stdout)
                continue
            one_liner = cmd.get_description().split('\n')[0]
            app.stdout.write('  %-13s  %s\n' % (name, one_liner))
        sys.exit(0)


class HelpCommand(Command):
    """print detailed help for another command
    """

    def get_parser(self, prog_name):
        parser = super(HelpCommand, self).get_parser(prog_name)
        parser.add_argument('cmd',
                            nargs='*',
                            help='name of the command',
                            )
        return parser

    def take_action(self, parsed_args):
        if parsed_args.cmd:
            try:
                the_cmd = self.app.command_manager.find_command(
                    parsed_args.cmd,
                )
                cmd_factory, cmd_name, search_args = the_cmd
            except ValueError:
                # Did not find an exact match
                cmd = parsed_args.cmd[0]
                fuzzy_matches = [k[0] for k in self.app.command_manager
                                 if k[0].startswith(cmd)
                                 ]
                if not fuzzy_matches:
                    raise
                self.app.stdout.write('Command "%s" matches:\n' % cmd)
                for fm in fuzzy_matches:
                    self.app.stdout.write('  %s\n' % fm)
                return
            cmd = cmd_factory(self.app, search_args)
            full_name = (cmd_name
                         if self.app.interactive_mode
                         else ' '.join([self.app.NAME, cmd_name])
                         )
            cmd_parser = cmd.get_parser(full_name)
        else:
            cmd_parser = self.get_parser(' '.join([self.app.NAME, 'help']))
        cmd_parser.print_help(self.app.stdout)
        return 0

########NEW FILE########
__FILENAME__ = interactive
"""Application base class.
"""

import itertools
import logging
import logging.handlers
import shlex

import cmd2

LOG = logging.getLogger(__name__)


class InteractiveApp(cmd2.Cmd):
    """Provides "interactive mode" features.

    Refer to the cmd2_ and cmd_ documentation for details
    about subclassing and configuring this class.

    .. _cmd2: http://packages.python.org/cmd2/index.html
    .. _cmd: http://docs.python.org/library/cmd.html

    :param parent_app: The calling application (expected to be derived
                       from :class:`cliff.main.App`).
    :param command_manager: A :class:`cliff.commandmanager.CommandManager`
                            instance.
    :param stdin: Standard input stream
    :param stdout: Standard output stream
    """

    use_rawinput = True
    doc_header = "Shell commands (type help <topic>):"
    app_cmd_header = "Application commands (type help <topic>):"

    def __init__(self, parent_app, command_manager, stdin, stdout):
        self.parent_app = parent_app
        self.prompt = '(%s) ' % parent_app.NAME
        self.command_manager = command_manager
        cmd2.Cmd.__init__(self, 'tab', stdin=stdin, stdout=stdout)

    def default(self, line):
        # Tie in the the default command processor to
        # dispatch commands known to the command manager.
        # We send the message through our parent app,
        # since it already has the logic for executing
        # the subcommand.
        line_parts = shlex.split(line.parsed.raw)
        self.parent_app.run_subcommand(line_parts)

    def completedefault(self, text, line, begidx, endidx):
        # Tab-completion for commands known to the command manager.
        # Does not handle options on the commands.
        if not text:
            completions = sorted(n for n, v in self.command_manager)
        else:
            completions = sorted(n for n, v in self.command_manager
                                 if n.startswith(text)
                                 )
        return completions

    def help_help(self):
        # Use the command manager to get instructions for "help"
        self.default('help help')

    def do_help(self, arg):
        if arg:
            # Check if the arg is a builtin command or something
            # coming from the command manager
            arg_parts = shlex.split(arg)
            method_name = '_'.join(
                itertools.chain(
                    ['do'],
                    itertools.takewhile(lambda x: not x.startswith('-'),
                                        arg_parts)
                )
            )
            # Have the command manager version of the help
            # command produce the help text since cmd and
            # cmd2 do not provide help for "help"
            if hasattr(self, method_name):
                return cmd2.Cmd.do_help(self, arg)
            # Dispatch to the underlying help command,
            # which knows how to provide help for extension
            # commands.
            self.default(self.parsed('help ' + arg))
        else:
            cmd2.Cmd.do_help(self, arg)
            cmd_names = sorted([n for n, v in self.command_manager])
            self.print_topics(self.app_cmd_header, cmd_names, 15, 80)
        return

    def get_names(self):
        # Override the base class version to filter out
        # things that look like they should be hidden
        # from the user.
        return [n
                for n in cmd2.Cmd.get_names(self)
                if not n.startswith('do__')
                ]

    def precmd(self, statement):
        # Pre-process the parsed command in case it looks like one of
        # our subcommands, since cmd2 does not handle multi-part
        # command names by default.
        line_parts = shlex.split(statement.parsed.raw)
        try:
            the_cmd = self.command_manager.find_command(line_parts)
            cmd_factory, cmd_name, sub_argv = the_cmd
        except ValueError:
            # Not a plugin command
            pass
        else:
            statement.parsed.command = cmd_name
            statement.parsed.args = ' '.join(sub_argv)
        return statement

########NEW FILE########
__FILENAME__ = lister
"""Application base class for providing a list of data as output.
"""
import abc

try:
    from itertools import compress
except ImportError:
    # for py26 compat
    from itertools import izip

    def compress(data, selectors):
        return (d for d, s in izip(data, selectors) if s)

import logging

from .display import DisplayCommandBase


LOG = logging.getLogger(__name__)


class Lister(DisplayCommandBase):
    """Command base class for providing a list of data as output.
    """
    __metaclass__ = abc.ABCMeta

    @property
    def formatter_namespace(self):
        return 'cliff.formatter.list'

    @property
    def formatter_default(self):
        return 'table'

    @abc.abstractmethod
    def take_action(self, parsed_args):
        """Return a tuple containing the column names and an iterable
        containing the data to be listed.
        """

    def produce_output(self, parsed_args, column_names, data):
        if not parsed_args.columns:
            columns_to_include = column_names
            data_gen = data
        else:
            columns_to_include = [c for c in column_names
                                  if c in parsed_args.columns
                                  ]
            if not columns_to_include:
                raise ValueError('No recognized column names in %s' %
                                 str(parsed_args.columns))
            # Set up argument to compress()
            selector = [(c in columns_to_include)
                        for c in column_names]
            # Generator expression to only return the parts of a row
            # of data that the user has expressed interest in
            # seeing. We have to convert the compress() output to a
            # list so the table formatter can ask for its length.
            data_gen = (list(compress(row, selector))
                        for row in data)
        self.formatter.emit_list(columns_to_include,
                                 data_gen,
                                 self.app.stdout,
                                 parsed_args,
                                 )
        return 0

########NEW FILE########
__FILENAME__ = show
"""Application base class for displaying data about a single object.
"""
import abc
import itertools
import logging

from .display import DisplayCommandBase


LOG = logging.getLogger(__name__)


class ShowOne(DisplayCommandBase):
    """Command base class for displaying data about a single object.
    """
    __metaclass__ = abc.ABCMeta

    @property
    def formatter_namespace(self):
        return 'cliff.formatter.show'

    @property
    def formatter_default(self):
        return 'table'

    @abc.abstractmethod
    def take_action(self, parsed_args):
        """Return a two-part tuple with a tuple of column names
        and a tuple of values.
        """

    def produce_output(self, parsed_args, column_names, data):
        if not parsed_args.columns:
            columns_to_include = column_names
        else:
            columns_to_include = [c for c in column_names
                                  if c in parsed_args.columns]
            # Set up argument to compress()
            selector = [(c in columns_to_include)
                        for c in column_names]
            data = list(itertools.compress(data, selector))
        self.formatter.emit_one(columns_to_include,
                                data,
                                self.app.stdout,
                                parsed_args)
        return 0

    def dict2columns(self, data):
        """Implement the common task of converting a dict-based object
        to the two-column output that ShowOne expects.
        """
        if not data:
            return ({}, {})
        else:
            return zip(*sorted(data.items()))

########NEW FILE########
__FILENAME__ = test_app
# -*- encoding: utf-8 -*-
from argparse import ArgumentError
try:
    from StringIO import StringIO
except ImportError:
    # Probably python 3, that test won't be run so ignore the error
    pass
import sys

import nose
import mock

from cliff.app import App
from cliff.command import Command
from cliff.commandmanager import CommandManager


def make_app():
    cmd_mgr = CommandManager('cliff.tests')

    # Register a command that succeeds
    command = mock.MagicMock(spec=Command)
    command_inst = mock.MagicMock(spec=Command)
    command_inst.run.return_value = 0
    command.return_value = command_inst
    cmd_mgr.add_command('mock', command)

    # Register a command that fails
    err_command = mock.Mock(name='err_command', spec=Command)
    err_command_inst = mock.Mock(spec=Command)
    err_command_inst.run = mock.Mock(
        side_effect=RuntimeError('test exception')
    )
    err_command.return_value = err_command_inst
    cmd_mgr.add_command('error', err_command)

    app = App('testing interactive mode',
              '1',
              cmd_mgr,
              stderr=mock.Mock(),  # suppress warning messages
              )
    return app, command


def test_no_args_triggers_interactive_mode():
    app, command = make_app()
    app.interact = mock.MagicMock(name='inspect')
    app.run([])
    app.interact.assert_called_once_with()


def test_interactive_mode_cmdloop():
    app, command = make_app()
    app.interactive_app_factory = mock.MagicMock(
        name='interactive_app_factory'
    )
    assert app.interpreter is None
    app.run([])
    assert app.interpreter is not None
    app.interactive_app_factory.return_value.cmdloop.assert_called_once_with()


def test_initialize_app():
    app, command = make_app()
    app.initialize_app = mock.MagicMock(name='initialize_app')
    app.run(['mock'])
    app.initialize_app.assert_called_once_with(['mock'])


def test_prepare_to_run_command():
    app, command = make_app()
    app.prepare_to_run_command = mock.MagicMock(name='prepare_to_run_command')
    app.run(['mock'])
    app.prepare_to_run_command.assert_called_once_with(command())


def test_clean_up_success():
    app, command = make_app()
    app.clean_up = mock.MagicMock(name='clean_up')
    app.run(['mock'])
    app.clean_up.assert_called_once_with(command.return_value, 0, None)


def test_clean_up_error():
    app, command = make_app()

    app.clean_up = mock.MagicMock(name='clean_up')
    app.run(['error'])

    app.clean_up.assert_called_once()
    call_args = app.clean_up.call_args_list[0]
    assert call_args == mock.call(mock.ANY, 1, mock.ANY)
    args, kwargs = call_args
    assert isinstance(args[2], RuntimeError)
    assert args[2].args == ('test exception',)


def test_clean_up_error_debug():
    app, command = make_app()

    app.clean_up = mock.MagicMock(name='clean_up')
    try:
        app.run(['--debug', 'error'])
    except RuntimeError as err:
        assert app.clean_up.call_args_list[0][0][2] is err
    else:
        assert False, 'Should have had an exception'

    app.clean_up.assert_called_once()
    call_args = app.clean_up.call_args_list[0]
    assert call_args == mock.call(mock.ANY, 1, mock.ANY)
    args, kwargs = call_args
    assert isinstance(args[2], RuntimeError)
    assert args[2].args == ('test exception',)


def test_error_handling_clean_up_raises_exception():
    app, command = make_app()

    app.clean_up = mock.MagicMock(
        name='clean_up',
        side_effect=RuntimeError('within clean_up'),
    )
    app.run(['error'])

    app.clean_up.assert_called_once()
    call_args = app.clean_up.call_args_list[0]
    assert call_args == mock.call(mock.ANY, 1, mock.ANY)
    args, kwargs = call_args
    assert isinstance(args[2], RuntimeError)
    assert args[2].args == ('test exception',)


def test_error_handling_clean_up_raises_exception_debug():
    app, command = make_app()

    app.clean_up = mock.MagicMock(
        name='clean_up',
        side_effect=RuntimeError('within clean_up'),
    )
    try:
        app.run(['--debug', 'error'])
    except RuntimeError as err:
        if not hasattr(err, '__context__'):
            # The exception passed to clean_up is not the exception
            # caused *by* clean_up.  This test is only valid in python
            # 2 because under v3 the original exception is re-raised
            # with the new one as a __context__ attribute.
            assert app.clean_up.call_args_list[0][0][2] is not err
    else:
        assert False, 'Should have had an exception'

    app.clean_up.assert_called_once()
    call_args = app.clean_up.call_args_list[0]
    assert call_args == mock.call(mock.ANY, 1, mock.ANY)
    args, kwargs = call_args
    assert isinstance(args[2], RuntimeError)
    assert args[2].args == ('test exception',)


def test_normal_clean_up_raises_exception():
    app, command = make_app()

    app.clean_up = mock.MagicMock(
        name='clean_up',
        side_effect=RuntimeError('within clean_up'),
    )
    app.run(['mock'])

    app.clean_up.assert_called_once()
    call_args = app.clean_up.call_args_list[0]
    assert call_args == mock.call(mock.ANY, 0, None)


def test_normal_clean_up_raises_exception_debug():
    app, command = make_app()

    app.clean_up = mock.MagicMock(
        name='clean_up',
        side_effect=RuntimeError('within clean_up'),
    )
    app.run(['--debug', 'mock'])

    app.clean_up.assert_called_once()
    call_args = app.clean_up.call_args_list[0]
    assert call_args == mock.call(mock.ANY, 0, None)


def test_build_option_parser_conflicting_option_should_throw():
    class MyApp(App):
        def __init__(self):
            super(MyApp, self).__init__(
                description='testing',
                version='0.1',
                command_manager=CommandManager('tests'),
            )

        def build_option_parser(self, description, version):
            parser = super(MyApp, self).build_option_parser(description,
                                                            version)
            parser.add_argument(
                '-h', '--help',
                default=self,  # tricky
                help="show this help message and exit",
            )

    # TODO: tests should really use unittest2.
    try:
        MyApp()
    except ArgumentError:
        pass
    else:
        raise Exception('Exception was not thrown')


def test_option_parser_conflicting_option_custom_arguments_should_not_throw():
    class MyApp(App):
        def __init__(self):
            super(MyApp, self).__init__(
                description='testing',
                version='0.1',
                command_manager=CommandManager('tests'),
            )

        def build_option_parser(self, description, version):
            argparse_kwargs = {'conflict_handler': 'resolve'}
            parser = super(MyApp, self).build_option_parser(
                description,
                version,
                argparse_kwargs=argparse_kwargs)
            parser.add_argument(
                '-h', '--help',
                default=self,  # tricky
                help="show this help message and exit",
            )

    MyApp()


def test_output_encoding_default():
    # The encoding should come from getdefaultlocale() because
    # stdout has no encoding set.
    if sys.version_info[:2] != (2, 6):
        raise nose.SkipTest('only needed for python 2.6')
    data = '\xc3\xa9'
    u_data = data.decode('utf-8')

    class MyApp(App):
        def __init__(self):
            super(MyApp, self).__init__(
                description='testing',
                version='0.1',
                command_manager=CommandManager('tests'),
            )

    stdout = StringIO()
    getdefaultlocale = lambda: ('ignored', 'utf-8')

    with mock.patch('sys.stdout', stdout):
        with mock.patch('locale.getdefaultlocale', getdefaultlocale):
            app = MyApp()
            app.stdout.write(u_data)
            actual = stdout.getvalue()
            assert data == actual


def test_output_encoding_cliff_default():
    # The encoding should come from cliff.App.DEFAULT_OUTPUT_ENCODING
    # because the other values are missing or None
    if sys.version_info[:2] != (2, 6):
        raise nose.SkipTest('only needed for python 2.6')
    data = '\xc3\xa9'
    u_data = data.decode('utf-8')

    class MyApp(App):
        def __init__(self):
            super(MyApp, self).__init__(
                description='testing',
                version='0.1',
                command_manager=CommandManager('tests'),
            )

    stdout = StringIO()
    getdefaultlocale = lambda: ('ignored', None)

    with mock.patch('sys.stdout', stdout):
        with mock.patch('locale.getdefaultlocale', getdefaultlocale):
            app = MyApp()
            app.stdout.write(u_data)
            actual = stdout.getvalue()
            assert data == actual


def test_output_encoding_sys():
    # The encoding should come from sys.stdout because it is set
    # there.
    if sys.version_info[:2] != (2, 6):
        raise nose.SkipTest('only needed for python 2.6')
    data = '\xc3\xa9'
    u_data = data.decode('utf-8')

    class MyApp(App):
        def __init__(self):
            super(MyApp, self).__init__(
                description='testing',
                version='0.1',
                command_manager=CommandManager('tests'),
            )

    stdout = StringIO()
    stdout.encoding = 'utf-8'
    getdefaultlocale = lambda: ('ignored', 'utf-16')

    with mock.patch('sys.stdout', stdout):
        with mock.patch('locale.getdefaultlocale', getdefaultlocale):
            app = MyApp()
            app.stdout.write(u_data)
            actual = stdout.getvalue()
            assert data == actual


def test_error_encoding_default():
    # The encoding should come from getdefaultlocale() because
    # stdout has no encoding set.
    if sys.version_info[:2] != (2, 6):
        raise nose.SkipTest('only needed for python 2.6')
    data = '\xc3\xa9'
    u_data = data.decode('utf-8')

    class MyApp(App):
        def __init__(self):
            super(MyApp, self).__init__(
                description='testing',
                version='0.1',
                command_manager=CommandManager('tests'),
            )

    stderr = StringIO()
    getdefaultlocale = lambda: ('ignored', 'utf-8')

    with mock.patch('sys.stderr', stderr):
        with mock.patch('locale.getdefaultlocale', getdefaultlocale):
            app = MyApp()
            app.stderr.write(u_data)
            actual = stderr.getvalue()
            assert data == actual


def test_error_encoding_sys():
    # The encoding should come from sys.stdout (not sys.stderr)
    # because it is set there.
    if sys.version_info[:2] != (2, 6):
        raise nose.SkipTest('only needed for python 2.6')
    data = '\xc3\xa9'
    u_data = data.decode('utf-8')

    class MyApp(App):
        def __init__(self):
            super(MyApp, self).__init__(
                description='testing',
                version='0.1',
                command_manager=CommandManager('tests'),
            )

    stdout = StringIO()
    stdout.encoding = 'utf-8'
    stderr = StringIO()
    getdefaultlocale = lambda: ('ignored', 'utf-16')

    with mock.patch('sys.stdout', stdout):
        with mock.patch('sys.stderr', stderr):
            with mock.patch('locale.getdefaultlocale', getdefaultlocale):
                app = MyApp()
                app.stderr.write(u_data)
                actual = stderr.getvalue()
                assert data == actual


def test_unknown_cmd():
    app, command = make_app()
    assert app.run(['hell']) == 2


def test_unknown_cmd_debug():
    app, command = make_app()
    try:
        app.run(['--debug', 'hell']) == 2
    except ValueError as err:
        assert "['hell']" in ('%s' % err)

########NEW FILE########
__FILENAME__ = test_command

from cliff.command import Command


class TestCommand(Command):
    """Description of command.
    """

    def take_action(self, parsed_args):
        return


def test_get_description():
    cmd = TestCommand(None, None)
    desc = cmd.get_description()
    assert desc == "Description of command.\n    "


def test_get_parser():
    cmd = TestCommand(None, None)
    parser = cmd.get_parser('NAME')
    assert parser.prog == 'NAME'

########NEW FILE########
__FILENAME__ = test_commandmanager

import mock

from cliff.commandmanager import CommandManager


class TestCommand(object):
    @classmethod
    def load(cls):
        return cls

    def __init__(self):
        return


class TestCommandManager(CommandManager):
    def _load_commands(self):
        self.commands = {
            'one': TestCommand,
            'two words': TestCommand,
            'three word command': TestCommand,
        }


def test_lookup_and_find():
    def check(mgr, argv):
        cmd, name, remaining = mgr.find_command(argv)
        assert cmd
        assert name == ' '.join(argv)
        assert not remaining
    mgr = TestCommandManager('test')
    for expected in [['one'],
                     ['two', 'words'],
                     ['three', 'word', 'command'],
                     ]:
        yield check, mgr, expected
    return


def test_lookup_with_remainder():
    def check(mgr, argv):
        cmd, name, remaining = mgr.find_command(argv)
        assert cmd
        assert remaining == ['--opt']
    mgr = TestCommandManager('test')
    for expected in [['one', '--opt'],
                     ['two', 'words', '--opt'],
                     ['three', 'word', 'command', '--opt'],
                     ]:
        yield check, mgr, expected
    return


def test_find_invalid_command():
    mgr = TestCommandManager('test')

    def check_one(argv):
        try:
            mgr.find_command(argv)
        except ValueError as err:
            assert '-b' in ('%s' % err)
        else:
            assert False, 'expected a failure'
    for argv in [['a', '-b'],
                 ['-b'],
                 ]:
        yield check_one, argv


def test_find_unknown_command():
    mgr = TestCommandManager('test')
    try:
        mgr.find_command(['a', 'b'])
    except ValueError as err:
        assert "['a', 'b']" in ('%s' % err)
    else:
        assert False, 'expected a failure'


def test_add_command():
    mgr = TestCommandManager('test')
    mock_cmd = mock.Mock()
    mgr.add_command('mock', mock_cmd)
    found_cmd, name, args = mgr.find_command(['mock'])
    assert found_cmd is mock_cmd


def test_load_commands():
    testcmd = mock.Mock(name='testcmd')
    testcmd.name.replace.return_value = 'test'
    mock_pkg_resources = mock.Mock(return_value=[testcmd])
    with mock.patch('pkg_resources.iter_entry_points',
                    mock_pkg_resources) as iter_entry_points:
        mgr = CommandManager('test')
        assert iter_entry_points.called_once_with('test')
        names = [n for n, v in mgr]
        assert names == ['test']


def test_load_commands_keep_underscores():
    testcmd = mock.Mock()
    testcmd.name = 'test_cmd'
    mock_pkg_resources = mock.Mock(return_value=[testcmd])
    with mock.patch('pkg_resources.iter_entry_points',
                    mock_pkg_resources) as iter_entry_points:
        mgr = CommandManager('test', convert_underscores=False)
        assert iter_entry_points.called_once_with('test')
        names = [n for n, v in mgr]
        assert names == ['test_cmd']


def test_load_commands_replace_underscores():
    testcmd = mock.Mock()
    testcmd.name = 'test_cmd'
    mock_pkg_resources = mock.Mock(return_value=[testcmd])
    with mock.patch('pkg_resources.iter_entry_points',
                    mock_pkg_resources) as iter_entry_points:
        mgr = CommandManager('test', convert_underscores=True)
        assert iter_entry_points.called_once_with('test')
        names = [n for n, v in mgr]
        assert names == ['test cmd']

########NEW FILE########
__FILENAME__ = test_complete
"""Bash completion tests
"""

import mock

from cliff.app import App
from cliff.commandmanager import CommandManager
from cliff import complete


def test_complete_dictionary():
    sot = complete.CompleteDictionary()
    sot.add_command("image delete".split(),
                    [mock.Mock(option_strings=["1"])])
    sot.add_command("image list".split(),
                    [mock.Mock(option_strings=["2"])])
    sot.add_command("image create".split(),
                    [mock.Mock(option_strings=["3"])])
    sot.add_command("volume type create".split(),
                    [mock.Mock(option_strings=["4"])])
    sot.add_command("volume type delete".split(),
                    [mock.Mock(option_strings=["5"])])
    assert "image volume" == sot.get_commands()
    result = sot.get_data()
    assert "image" == result[0][0]
    assert "create delete list" == result[0][1]
    assert "image_create" == result[1][0]
    assert "3" == result[1][1]
    assert "image_delete" == result[2][0]
    assert "1" == result[2][1]
    assert "image_list" == result[3][0]
    assert "2" == result[3][1]


class FakeStdout:
    def __init__(self):
        self.content = []

    def write(self, text):
        self.content.append(text)

    def make_string(self):
        result = ''
        for line in self.content:
            result = result + line
        return result


def given_cmdo_data():
    cmdo = "image server"
    data = [("image", "create"),
            ("image_create", "--eolus"),
            ("server", "meta ssh"),
            ("server_meta_delete", "--wilson"),
            ("server_ssh", "--sunlight")]
    return cmdo, data


def then_data(content):
    assert "  cmds='image server'\n" in content
    assert "  cmds_image='create'\n" in content
    assert "  cmds_image_create='--eolus'\n" in content
    assert "  cmds_server='meta ssh'\n" in content
    assert "  cmds_server_meta_delete='--wilson'\n" in content
    assert "  cmds_server_ssh='--sunlight'\n" in content


def test_complete_no_code():
    output = FakeStdout()
    sot = complete.CompleteNoCode("doesNotMatter", output)
    sot.write(*given_cmdo_data())
    then_data(output.content)


def test_complete_bash():
    output = FakeStdout()
    sot = complete.CompleteBash("openstack", output)
    sot.write(*given_cmdo_data())
    then_data(output.content)
    assert "_openstack()\n" in output.content[0]
    assert "complete -F _openstack openstack\n" in output.content[-1]


def test_complete_command_parser():
    sot = complete.CompleteCommand(mock.Mock(), mock.Mock())
    parser = sot.get_parser('nothing')
    assert "nothing" == parser.prog
    assert "print bash completion command\n    " == parser.description


def given_complete_command():
    cmd_mgr = CommandManager('cliff.tests')
    app = App('testing', '1', cmd_mgr, stdout=FakeStdout())
    sot = complete.CompleteCommand(app, mock.Mock())
    cmd_mgr.add_command('complete', complete.CompleteCommand)
    return sot, app, cmd_mgr


def then_actions_equal(actions):
    optstr = ' '.join(opt for action in actions
                      for opt in action.option_strings)
    assert '-h --help --name --shell' == optstr


def test_complete_command_get_actions():
    sot, app, cmd_mgr = given_complete_command()
    app.interactive_mode = False
    actions = sot.get_actions(["complete"])
    then_actions_equal(actions)


def test_complete_command_get_actions_interactive():
    sot, app, cmd_mgr = given_complete_command()
    app.interactive_mode = True
    actions = sot.get_actions(["complete"])
    then_actions_equal(actions)


def test_complete_command_take_action():
    sot, app, cmd_mgr = given_complete_command()
    parsed_args = mock.Mock()
    parsed_args.name = "test_take"
    parsed_args.shell = "bash"
    content = app.stdout.content
    assert 0 == sot.take_action(parsed_args)
    assert "_test_take()\n" in content[0]
    assert "complete -F _test_take test_take\n" in content[-1]
    assert "  cmds='complete help'\n" in content
    assert "  cmds_complete='-h --help --name --shell'\n" in content
    assert "  cmds_help='-h --help'\n" in content

########NEW FILE########
__FILENAME__ = test_help
try:
    from StringIO import StringIO
except:
    from io import StringIO

import mock

from cliff.app import App
from cliff.command import Command
from cliff.commandmanager import CommandManager
from cliff.help import HelpCommand


class TestParser(object):

    def print_help(self, stdout):
        stdout.write('TestParser')


class TestCommand(Command):

    @classmethod
    def load(cls):
        return cls

    def get_parser(self, ignore):
        # Make it look like this class is the parser
        # so parse_args() is called.
        return TestParser()

    def take_action(self, args):
        return


class TestCommandManager(CommandManager):
    def _load_commands(self):
        self.commands = {
            'one': TestCommand,
            'two words': TestCommand,
            'three word command': TestCommand,
        }


def test_show_help_for_command():
    # FIXME(dhellmann): Are commands tied too closely to the app? Or
    # do commands know too much about apps by using them to get to the
    # command manager?
    stdout = StringIO()
    app = App('testing', '1', TestCommandManager('cliff.test'), stdout=stdout)
    app.NAME = 'test'
    help_cmd = HelpCommand(app, mock.Mock())
    parser = help_cmd.get_parser('test')
    parsed_args = parser.parse_args(['one'])
    try:
        help_cmd.run(parsed_args)
    except SystemExit:
        pass
    assert stdout.getvalue() == 'TestParser'


def test_list_matching_commands():
    # FIXME(dhellmann): Are commands tied too closely to the app? Or
    # do commands know too much about apps by using them to get to the
    # command manager?
    stdout = StringIO()
    app = App('testing', '1', TestCommandManager('cliff.test'), stdout=stdout)
    app.NAME = 'test'
    help_cmd = HelpCommand(app, mock.Mock())
    parser = help_cmd.get_parser('test')
    parsed_args = parser.parse_args(['t'])
    try:
        help_cmd.run(parsed_args)
    except SystemExit:
        pass
    help_output = stdout.getvalue()
    assert 'Command "t" matches:' in help_output
    assert 'two' in help_output
    assert 'three' in help_output


def test_list_matching_commands_no_match():
    # FIXME(dhellmann): Are commands tied too closely to the app? Or
    # do commands know too much about apps by using them to get to the
    # command manager?
    stdout = StringIO()
    app = App('testing', '1', TestCommandManager('cliff.test'), stdout=stdout)
    app.NAME = 'test'
    help_cmd = HelpCommand(app, mock.Mock())
    parser = help_cmd.get_parser('test')
    parsed_args = parser.parse_args(['z'])
    try:
        help_cmd.run(parsed_args)
    except SystemExit:
        pass
    except ValueError:
        pass
    else:
        assert False, 'Should have seen a ValueError'


def test_show_help_for_help():
    # FIXME(dhellmann): Are commands tied too closely to the app? Or
    # do commands know too much about apps by using them to get to the
    # command manager?
    stdout = StringIO()
    app = App('testing', '1', TestCommandManager('cliff.test'), stdout=stdout)
    app.NAME = 'test'
    help_cmd = HelpCommand(app, mock.Mock())
    parser = help_cmd.get_parser('test')
    parsed_args = parser.parse_args([])
    try:
        help_cmd.run(parsed_args)
    except SystemExit:
        pass
    help_text = stdout.getvalue()
    assert 'usage: test help [-h]' in help_text

########NEW FILE########
__FILENAME__ = test_lister
#!/usr/bin/env python

import weakref

from cliff.lister import Lister

import mock


class FauxFormatter(object):

    def __init__(self):
        self.args = []
        self.obj = weakref.proxy(self)

    def emit_list(self, columns, data, stdout, args):
        self.args.append((columns, data))


class ExerciseLister(Lister):

    def _load_formatter_plugins(self):
        return {
            'test': FauxFormatter(),
        }
        return

    def take_action(self, parsed_args):
        return (
            parsed_args.columns,
            [('a', 'A'), ('b', 'B')],
        )


#    def run(self, parsed_args):
#        self.formatter = self.formatters[parsed_args.formatter]
#        column_names, data = self.take_action(parsed_args)
#        self.produce_output(parsed_args, column_names, data)
#        return 0

def test_formatter_args():
    app = mock.Mock()
    test_lister = ExerciseLister(app, [])

    parsed_args = mock.Mock()
    parsed_args.columns = ('Col1', 'Col2')
    parsed_args.formatter = 'test'

    test_lister.run(parsed_args)
    f = test_lister.formatters['test']
    assert len(f.args) == 1
    args = f.args[0]
    assert args[0] == list(parsed_args.columns)
    data = list(args[1])
    assert data == [['a', 'A'], ['b', 'B']]

########NEW FILE########
__FILENAME__ = test_show
#!/usr/bin/env python

from cliff.show import ShowOne

import mock


class FauxFormatter(object):

    def __init__(self):
        self.args = []

    def emit_list(self, columns, data, stdout, args):
        self.args.append((columns, data))


class ExerciseShowOne(ShowOne):

    def load_formatter_plugins(self):
        self.formatters = {
            'test': FauxFormatter(),
        }
        return

    def take_action(self, parsed_args):
        return (
            parsed_args.columns,
            [('a', 'A'), ('b', 'B')],
        )


# def test_formatter_args():
#     app = mock.Mock()
#     test_lister = ExerciseLister(app, [])

#     parsed_args = mock.Mock()
#     parsed_args.columns = ('Col1', 'Col2')
#     parsed_args.formatter = 'test'

#     test_lister.run(parsed_args)
#     f = test_lister.formatters['test']
#     assert len(f.args) == 1
#     args = f.args[0]
#     assert args[0] == list(parsed_args.columns)
#     data = list(args[1])
#     assert data == [['a', 'A'], ['b', 'B']]

def test_dict2columns():
    app = mock.Mock()
    test_show = ExerciseShowOne(app, [])
    d = {'a': 'A', 'b': 'B', 'c': 'C'}
    expected = [('a', 'b', 'c'), ('A', 'B', 'C')]
    actual = list(test_show.dict2columns(d))
    assert expected == actual

########NEW FILE########
__FILENAME__ = encoding
# -*- encoding: utf-8 -*-

import logging

from cliff.lister import Lister


class Encoding(Lister):
    """Show some unicode text
    """

    log = logging.getLogger(__name__)

    def take_action(self, parsed_args):
        messages = [
            u'pi: π',
            u'GB18030:鼀丅㐀ٸཌྷᠧꌢ€',
        ]
        return (
            ('UTF-8', 'Unicode'),
            [(repr(t.encode('utf-8')), t)
             for t in messages],
        )

########NEW FILE########
__FILENAME__ = list
import logging
import os

from cliff.lister import Lister


class Files(Lister):
    """Show a list of files in the current directory.

    The file name and size are printed by default.
    """

    log = logging.getLogger(__name__)

    def take_action(self, parsed_args):
        return (('Name', 'Size'),
                ((n, os.stat(n).st_size) for n in os.listdir('.'))
                )

########NEW FILE########
__FILENAME__ = main
import logging
import sys

from cliff.app import App
from cliff.commandmanager import CommandManager


class DemoApp(App):

    log = logging.getLogger(__name__)

    def __init__(self):
        super(DemoApp, self).__init__(
            description='cliff demo app',
            version='0.1',
            command_manager=CommandManager('cliff.demo'),
            )

    def initialize_app(self, argv):
        self.log.debug('initialize_app')

    def prepare_to_run_command(self, cmd):
        self.log.debug('prepare_to_run_command %s', cmd.__class__.__name__)

    def clean_up(self, cmd, result, err):
        self.log.debug('clean_up %s', cmd.__class__.__name__)
        if err:
            self.log.debug('got an error: %s', err)


def main(argv=sys.argv[1:]):
    myapp = DemoApp()
    return myapp.run(argv)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))

########NEW FILE########
__FILENAME__ = show
import logging
import os

from cliff.show import ShowOne


class File(ShowOne):
    "Show details about a file"

    log = logging.getLogger(__name__)

    def get_parser(self, prog_name):
        parser = super(File, self).get_parser(prog_name)
        parser.add_argument('filename', nargs='?', default='.')
        return parser

    def take_action(self, parsed_args):
        stat_data = os.stat(parsed_args.filename)
        columns = ('Name',
                   'Size',
                   'UID',
                   'GID',
                   'Modified Time',
                   )
        data = (parsed_args.filename,
                stat_data.st_size,
                stat_data.st_uid,
                stat_data.st_gid,
                stat_data.st_mtime,
                )
        return (columns, data)

########NEW FILE########
__FILENAME__ = simple
import logging

from cliff.command import Command


class Simple(Command):
    "A simple command that prints a message."

    log = logging.getLogger(__name__)

    def take_action(self, parsed_args):
        self.log.info('sending greeting')
        self.log.debug('debugging')
        self.app.stdout.write('hi!\n')


class Error(Command):
    "Always raises an error"

    log = logging.getLogger(__name__)

    def take_action(self, parsed_args):
        self.log.info('causing error')
        raise RuntimeError('this is the expected exception')

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# cliff documentation build configuration file, created by
# sphinx-quickstart on Wed Apr 25 11:14:29 2012.
#
# This file is execfile()d with the current directory set to its
# containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import datetime
import subprocess

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#sys.path.insert(0, os.path.abspath('.'))

# -- General configuration ---------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.todo']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'cliff'
copyright = u'2012-%s, Doug Hellmann' % datetime.datetime.today().year

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = subprocess.check_output([
    'sh', '-c',
    'cd ../..; python setup.py --version',
])
version = version.strip()
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
exclude_patterns = []

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


# -- Options for HTML output -------------------------------------------------

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
htmlhelp_basename = 'cliffdoc'


# -- Options for LaTeX output ------------------------------------------------

latex_elements = {
    # The paper size ('letterpaper' or 'a4paper').
    #'papersize': 'letterpaper',

    # The font size ('10pt', '11pt' or '12pt').
    #'pointsize': '10pt',

    # Additional stuff for the LaTeX preamble.
    #'preamble': '',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author,
# documentclass [howto/manual]).
latex_documents = [
    ('index', 'cliff.tex', u'cliff Documentation',
     u'Doug Hellmann', 'manual'),
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


# -- Options for manual page output ------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'cliff', u'cliff Documentation',
     [u'Doug Hellmann'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ----------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
    ('index', 'cliff', u'cliff Documentation',
     u'Doug Hellmann', 'cliff', 'One line description of project.',
     'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'

########NEW FILE########
