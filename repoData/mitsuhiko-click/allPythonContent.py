__FILENAME__ = core
import os
import sys
import codecs
from contextlib import contextmanager
from itertools import chain, repeat

from .types import convert_type, IntRange, BOOL
from .utils import make_str, make_default_short_help, echo
from .exceptions import ClickException, UsageError, BadParameter, Abort
from .termui import prompt, confirm
from .formatting import HelpFormatter
from .parser import OptionParser, split_opt

from ._compat import PY2, isidentifier

_missing = object()


def batch(iterable, batch_size):
    return list(zip(*repeat(iter(iterable), batch_size)))


def invoke_param_callback(callback, ctx, param, value):
    code = getattr(callback, '__code__', None)
    args = getattr(code, 'co_argcount', 3)

    if args < 3:
        from warnings import warn
        warn(Warning('Invoked legacy parameter callback "%s".  The new '
                     'signature for such callbacks starting with '
                     'click 2.0 is (ctx, param, value).'
                     % callback), stacklevel=3)
        return callback(ctx, value)
    return callback(ctx, param, value)


@contextmanager
def augment_usage_errors(ctx, param=None):
    """Context manager that attaches extra information to exceptions that
    fly.
    """
    try:
        yield
    except BadParameter as e:
        if e.ctx is None:
            e.ctx = ctx
        if param is not None and e.param is None:
            e.param = param
        raise
    except UsageError as e:
        if e.ctx is None:
            e.ctx = ctx
        raise


def iter_params_for_processing(invocation_order, declaration_order):
    """Given a sequence of parameters in the order as should be considered
    for processing and an iterable of parameters that exist, this returns
    a list in the correct order as they should be processed.
    """
    def sort_key(item):
        try:
            idx = invocation_order.index(item)
        except ValueError:
            idx = float('inf')
        return (not item.is_eager, idx)

    return sorted(declaration_order, key=sort_key)


class Context(object):
    """The context is a special internal object that holds state relevant
    for the script execution at every single level.  It's normally invisible
    to commands unless they opt-in to getting access to it.

    The context is useful as it can pass internal objects around and can
    control special execution features such as reading data from
    environment variables.

    A context can be used as context manager in which case it will call
    :meth:`close` on teardown.

    :param command: the command class for this context.
    :param parent: the parent context.
    :param info_name: the info name for this invokation.  Generally this
                      is the most descriptive name for the script or
                      command.  For the toplevel script is is usually
                      the name of the script, for commands below it it's
                      the name of the script.
    :param obj: an arbitrary object of user data.
    :param auto_envvar_prefix: the prefix to use for automatic environment
                               variables.  If this is `None` then reading
                               from environment variables is disabled.  This
                               does not affect manually set environment
                               variables which are always read.
    :param default_map: a dictionary (like object) with default values
                        for parameters.
    :param terminal_width: the width of the terminal.  The default is
                           inherit from parent context.  If no context
                           defines the terminal width then auto
                           detection will be applied.
    """

    def __init__(self, command, parent=None, info_name=None, obj=None,
                 auto_envvar_prefix=None, default_map=None,
                 terminal_width=None):
        #: the parent context or `None` if none exists.
        self.parent = parent
        #: the :class:`Command` for this context.
        self.command = command
        #: the descriptive information name
        self.info_name = info_name
        #: the parsed parameters except if the value is hidden in which
        #: case it's not remembered.
        self.params = {}
        #: the leftover arguments.
        self.args = []
        #: this flag indicates if a subcommand is going to be executed.
        #: a group callback can use this information to figure out if it's
        #: being executed directly or because the execution flow passes
        #: onwards to a subcommand.  By default it's `None` but it can be
        #: the name of the subcommand to execute.
        self.invoked_subcommand = None
        if obj is None and parent is not None:
            obj = parent.obj
        #: the user object stored.
        self.obj = obj
        #: A dictionary (like object) with defaults for parameters.
        self.default_map = default_map

        if terminal_width is None and parent is not None:
            terminal_width = parent.terminal_width
        #: The width of the terminal (None is autodetection).
        self.terminal_width = terminal_width

        # If there is no envvar prefix yet, but the parent has one and
        # the command on this level has a name, we can expand the envvar
        # prefix automatically.
        if auto_envvar_prefix is None:
            if parent is not None \
               and parent.auto_envvar_prefix is not None and \
               self.info_name is not None:
                auto_envvar_prefix = '%s_%s' % (parent.auto_envvar_prefix,
                                           self.info_name.upper())
        else:
            self.auto_envvar_prefix = auto_envvar_prefix.upper()
        self.auto_envvar_prefix = auto_envvar_prefix

        self._close_callbacks = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, tb):
        self.close()

    def make_formatter(self):
        """Creates the formatter for the help and usage output."""
        return HelpFormatter(width=self.terminal_width)

    def call_on_close(self, f):
        """This decorator remembers a function as callback that should be
        executed when the context tears down.  This is most useful to bind
        resource handling to the script execution.  For instance file objects
        opened by the :class:`File` type will register their close callbacks
        here.

        :param f: the function to execute on teardown.
        """
        self._close_callbacks.append(f)
        return f

    def close(self):
        """Invokes all close callbacks."""
        for cb in self._close_callbacks:
            cb()
        self._close_callbacks = []

    @property
    def command_path(self):
        """The computed command path.  This is used for the ``usage``
        information on the help page.  It's automatically created by
        combining the info names of the chain of contexts to the root.
        """
        rv = ''
        if self.info_name is not None:
            rv = self.info_name
        if self.parent is not None:
            rv = self.parent.command_path + ' ' + rv
        return rv.lstrip()

    def find_root(self):
        """Finds the outermost context."""
        node = self
        while node.parent is not None:
            node = node.parent
        return node

    def find_object(self, object_type):
        """Finds the closest object of a given type."""
        node = self
        while node is not None:
            if isinstance(node.obj, object_type):
                return node.obj
            node = node.parent

    def ensure_object(self, object_type):
        """Like :meth:`find_object` but sets the innermost object to a
        new instance of `object_type` if it does not exist.
        """
        rv = self.find_object(object_type)
        if rv is None:
            self.obj = rv = object_type()
        return rv

    def lookup_default(self, name):
        """Looks up the default for a parameter name.  This by default
        looks into the :attr:`default_map` if available.
        """
        if self.default_map is not None:
            rv = self.default_map.get(name)
            if callable(rv):
                rv = rv()
            return rv

    def fail(self, message):
        """Aborts the execution of the program with a specific error
        message.

        :param message: the error message to fail with.
        """
        raise UsageError(message, self)

    def abort(self):
        """Aborts the script."""
        raise Abort()

    def exit(self, code=0):
        """Exits the application with a given exit code."""
        sys.exit(code)

    def get_usage(self):
        """Helper method to get formatted usage string for the current
        context and command.
        """
        return self.command.get_usage(self)

    def get_help(self):
        """Helper method to get formatted help page for the current
        context and command.
        """
        return self.command.get_help(self)

    def invoke(*args, **kwargs):
        """Invokes a command callback in exactly the way it expects.
        """
        self, callback = args[:2]

        # It's also possible to invoke another command which might or
        # might not have a callback.
        if isinstance(callback, Command):
            callback = callback.callback
            if callback is None:
                raise TypeError('The given command does not have a '
                                'callback that can be invoked.')

        args = args[2:]
        if getattr(callback, '__click_pass_context__', False):
            args = (self,) + args
        with augment_usage_errors(self):
            return callback(*args, **kwargs)

    def forward(*args, **kwargs):
        """Similar to :meth:`forward` but fills in default keyword
        arguments from the current context if the other command expects
        it.  This cannot invoke callbacks directly, only other commands.
        """
        self, cmd = args[:2]

        # It's also possible to invoke another command which might or
        # might not have a callback.
        if not isinstance(cmd, Command):
            raise TypeError('Callback is not a command.')

        for param in self.params:
            if param in self.params and \
               param not in kwargs:
                kwargs[param] = self.params[param]

        return self.invoke(cmd, **kwargs)


class BaseCommand(object):
    """The base command implements the minimal API contract of commands.
    Most code will never use this as it does not implement a lot of useful
    functionality but it can act as the direct subclass of alternative
    parsing methods that do not depend on the click parser.

    For instance this can be used to bridge click and other systems like
    argparse or docopt.

    Because base commands do not implement a lot of the API that other
    parts of click take for granted they are not supported for all
    operations.  For instance they cannot be used with the decorators
    usually and they have no built-in callback system.

    :param name: the name of the command to use unless a group overrides it.
    """

    def __init__(self, name):
        #: the name the command thinks it has.  Upon registering a command
        #: on a :class:`Group` the group will default the command name
        #: with this information.  You should instead use the
        #: :class:`Context`\'s :attr:`~Context.info_name` attribute.
        self.name = name

    def get_usage(self, ctx):
        raise NotImplementedError('Base commands cannot get usage')

    def get_help(self, ctx):
        raise NotImplementedError('Base commands cannot get help')

    def make_context(self, info_name, args, parent=None, **extra):
        """This function when given an info name and arguments will kick
        off the parsing and create a new :class:`Context`.  It does not
        invoke the actual command callback though.

        :param info_name: the info name for this invokation.  Generally this
                          is the most descriptive name for the script or
                          command.  For the toplevel script it's usually
                          the name of the script, for commands below it it's
                          the name of the script.
        :param args: the arguments to parse as list of strings.
        :param parent: the parent context if available.
        :param extra: extra keyword arguments forwarded to the context
                      constructor.
        """
        if 'default_map' not in extra:
            default_map = None
            if parent is not None and parent.default_map is not None:
                default_map = parent.default_map.get(info_name)
            extra['default_map'] = default_map
        ctx = Context(self, info_name=info_name, parent=parent, **extra)
        self.parse_args(ctx, args)
        return ctx

    def parse_args(self, ctx, args):
        """Given a context and a list of arguments this creates the parser
        and parses the arguments, then modifies the context as necessary.
        This is automatically invoked by :meth:`make_context`.
        """
        raise NotImplementedError('Base commands do not know how to parse '
                                  'arguments.')

    def invoke(self, ctx):
        """Given a context, this invokes the command.  The default
        implementation is raising a not implemented error.
        """
        raise NotImplementedError('Base commands are not invokable by default')

    def main(self, args=None, prog_name=None, **extra):
        """This is the way to invoke a script with all the bells and
        whistles as a command line application.  This will always terminate
        the application after a call.  If this is not wanted, ``SystemExit``
        needs to be caught.

        This method is also available by directly calling the instance of
        a :class:`Command`.

        :param args: the arguments that should be used for parsing.  If not
                     provided, ``sys.argv[1:]`` is used.
        :param prog_name: the program name that should be used.  By default
                          the program name is constructed by taking the file
                          name from ``sys.argv[0]``.
        :param extra: extra keyword arguments are forwarded to the context
                      constructor.  See :class:`Context` for more information.
        """
        # If we are on python 3 we will verify that the environment is
        # sane at this point of reject further execution to avoid a
        # broken script.
        if not PY2:
            try:
                import locale
                fs_enc = codecs.lookup(locale.getpreferredencoding()).name
            except Exception:
                fs_enc = 'ascii'
            if fs_enc == 'ascii':
                raise RuntimeError('Click will abort further execution '
                                   'because Python 3 was configured to use '
                                   'ASCII as encoding for the environment. '
                                   'Either switch to Python 2 or consult '
                                   'http://click.pocoo.org/python3/ '
                                   'for mitigation steps.')

        if args is None:
            args = sys.argv[1:]
        else:
            args = list(args)
        if prog_name is None:
            prog_name = make_str(os.path.basename(
                sys.argv and sys.argv[0] or __file__))
        try:
            try:
                with self.make_context(prog_name, args, **extra) as ctx:
                    self.invoke(ctx)
                    ctx.exit()
            except (EOFError, KeyboardInterrupt):
                echo(file=sys.stderr)
                raise Abort()
            except ClickException as e:
                e.show()
                sys.exit(e.exit_code)
        except Abort:
            echo('Aborted!', file=sys.stderr)
            sys.exit(1)

    def __call__(self, *args, **kwargs):
        """Alias for :meth:`main`."""
        return self.main(*args, **kwargs)


class Command(BaseCommand):
    """Commands are the basic building block of command line interfaces in
    click.  A basic command handles command line parsing and might dispatch
    more parsing to commands nested below it.

    :param name: the name of the command to use unless a group overrides it.
    :param callback: the callback to invoke.  This is optional.
    :param params: the parameters to register with this command.  This can
                   be either :class:`Option` or :class:`Argument` objects.
    :param help: the help string to use for this command.
    :param epilog: like the help string but it's printed at the end of the
                   help page after everything else.
    :param short_help: the short help to use for this command.  This is
                       shown on the command listing of the parent command.
    :param add_help_option: by default each command registers a ``--help``
                            option.  This can be disabled by this parameter.
    """
    allow_extra_args = False

    def __init__(self, name, callback=None, params=None, help=None,
                 epilog=None, short_help=None,
                 options_metavar='[OPTIONS]', add_help_option=True):
        BaseCommand.__init__(self, name)
        #: the callback to execute when the command fires.  This might be
        #: `None` in which case nothing happens.
        self.callback = callback
        #: the list of parameters for this command in the order they
        #: should show up in the help page and execute.  Eager parameters
        #: will automatically be handled before non eager ones.
        self.params = params or []
        self.help = help
        self.epilog = epilog
        self.options_metavar = options_metavar
        if short_help is None and help:
            short_help = make_default_short_help(help)
        self.short_help = short_help
        if add_help_option:
            self.add_help_option()

    def add_help_option(self):
        """Adds a help option to the command."""
        help_option()(self)

    def get_usage(self, ctx):
        formatter = ctx.make_formatter()
        self.format_usage(ctx, formatter)
        return formatter.getvalue().rstrip('\n')

    def format_usage(self, ctx, formatter):
        """Writes the usage line into the formatter."""
        pieces = self.collect_usage_pieces(ctx)
        formatter.write_usage(ctx.command_path, ' '.join(pieces))

    def collect_usage_pieces(self, ctx):
        """Returns all the pieces that go into the usage line and returns
        it as a list of strings.
        """
        rv = [self.options_metavar]
        for param in self.params:
            rv.extend(param.get_usage_pieces(ctx))
        return rv

    def make_parser(self, ctx):
        """Creates the underlying option parser for this command."""
        parser = OptionParser(ctx)
        for param in self.params:
            param.add_to_parser(parser, ctx)
        return parser

    def get_help(self, ctx):
        """Formats the help into a string and returns it.  This creates a
        formatter and will call into the following formatting methods:
        """
        formatter = ctx.make_formatter()
        self.format_help(ctx, formatter)
        return formatter.getvalue().rstrip('\n')

    def format_help(self, ctx, formatter):
        """Writes the help into the formatter if it exists.

        This calls into the following methods:

        -   :meth:`format_usage`
        -   :meth:`format_help_text`
        -   :meth:`format_options`
        -   :meth:`format_epilog`
        """
        self.format_usage(ctx, formatter)
        self.format_help_text(ctx, formatter)
        self.format_options(ctx, formatter)
        self.format_epilog(ctx, formatter)

    def format_help_text(self, ctx, formatter):
        """Writes the help text to the formatter if it exists."""
        if self.help:
            formatter.write_paragraph()
            with formatter.indentation():
                formatter.write_text(self.help)

    def format_options(self, ctx, formatter):
        """Writes all the options into the formatter if they exist."""
        opts = []
        for param in self.params:
            rv = param.get_help_record(ctx)
            if rv is not None:
                opts.append(rv)

        if opts:
            with formatter.section('Options'):
                formatter.write_dl(opts)

    def format_epilog(self, ctx, formatter):
        """Writes the epilog into the formatter if it exists."""
        if self.epilog:
            formatter.write_paragraph()
            with formatter.indentation():
                formatter.write_text(self.epilog)

    def parse_args(self, ctx, args):
        parser = self.make_parser(ctx)
        opts, args, param_order = parser.parse_args(args=args)

        for param in iter_params_for_processing(param_order, self.params):
            value, args = param.handle_parse_result(ctx, opts, args)

        if args and not self.allow_extra_args:
            ctx.fail('Got unexpected extra argument%s (%s)'
                     % (len(args) != 1 and 's' or '',
                        ' '.join(map(make_str, args))))

        ctx.args = args

    def invoke(self, ctx):
        """Given a context, this invokes the attached callback (if it exists)
        in the right way.
        """
        if self.callback is not None:
            ctx.invoke(self.callback, **ctx.params)


class MultiCommand(Command):
    """A multi command is the basic implementation of a command that
    dispatches to subcommands.  The most common version is the
    :class:`Command`.

    :param invoke_without_command: this controls how the multi command itself
                                   is invoked.  By default it's only invoked
                                   if a subcommand is provided.
    :param no_args_is_help: this controls what happens if no arguments are
                            provided.  This option is enabled by default if
                            `invoke_without_command` is disabled or disabled
                            if it's enabled.  If enabled this will add
                            ``--help`` as argument if no arguments are
                            passed.
    :param subcommand_metavar: the string that is used in the documentation
                               to indicate the subcommand place.
    """
    allow_extra_args = True

    def __init__(self, name=None, invoke_without_command=False,
                 no_args_is_help=None, subcommand_metavar='COMMAND [ARGS]...',
                 **attrs):
        Command.__init__(self, name, **attrs)
        if no_args_is_help is None:
            no_args_is_help = not invoke_without_command
        self.no_args_is_help = no_args_is_help
        self.invoke_without_command = invoke_without_command
        self.subcommand_metavar = subcommand_metavar

    def make_parser(self, ctx):
        parser = Command.make_parser(self, ctx)
        parser.allow_interspersed_args = False
        return parser

    def collect_usage_pieces(self, ctx):
        rv = Command.collect_usage_pieces(self, ctx)
        rv.append(self.subcommand_metavar)
        return rv

    def format_options(self, ctx, formatter):
        Command.format_options(self, ctx, formatter)
        self.format_commands(ctx, formatter)

    def format_commands(self, ctx, formatter):
        """Extra format methods for multi methods that adds all the commands
        after the options.
        """
        rows = []
        for subcommand in self.list_commands(ctx):
            cmd = self.get_command(ctx, subcommand)
            # What is this, the tool lied about a command.  Ignore it
            if cmd is None:
                continue

            help = cmd.short_help or ''
            rows.append((subcommand, help))

        if rows:
            with formatter.section('Commands'):
                formatter.write_dl(rows)

    def parse_args(self, ctx, args):
        if not args and self.no_args_is_help:
            echo(ctx.get_help())
            ctx.exit()
        return Command.parse_args(self, ctx, args)

    def invoke(self, ctx):
        if not ctx.args:
            if self.invoke_without_command:
                return Command.invoke(self, ctx)
            ctx.fail('Missing command.')

        cmd_name = make_str(ctx.args[0])
        cmd = self.get_command(ctx, cmd_name)

        # If we don't find the command we want to show an error message
        # to the user that it was not provided.  However there is
        # something else we should do: if the first argument looks like
        # an option we want to kick off parsing again for arguments to
        # resolve things like --help which now should go to the main
        # place.
        if cmd is None:
            if split_opt(cmd_name)[0]:
                self.parse_args(ctx, ctx.args)
            ctx.fail('No such command "%s".' % cmd_name)

        return self.invoke_subcommand(ctx, cmd, cmd_name, ctx.args[1:])

    def invoke_subcommand(self, ctx, cmd, cmd_name, args):
        # Whenever we dispatch to a subcommand we also invoke the regular
        # callback.  This is done so that parameters can be handled.
        ctx.invoked_subcommand = cmd_name
        Command.invoke(self, ctx)

        with cmd.make_context(cmd_name, args, parent=ctx) as cmd_ctx:
            return cmd.invoke(cmd_ctx)

    def get_command(self, ctx, cmd_name):
        """Given a context and a command name, this returns a
        :class:`Command` object if it exists or returns `None`.
        """
        raise NotImplementedError()

    def list_commands(self, ctx):
        """Returns a list of subcommand names in the order they should
        appear.
        """
        return []


class Group(MultiCommand):
    """A group allows a command to have subcommands attached.  This is the
    most common way to implement nesting in click.

    :param commands: a dictionary of commands.
    """

    def __init__(self, name=None, commands=None, **attrs):
        MultiCommand.__init__(self, name, **attrs)
        #: the registered subcommands by their exported names.
        self.commands = commands or {}

    def add_command(self, cmd, name=None):
        """Registers another :class:`Command` with this group.  If the name
        is not provided, the name of the command is used.
        """
        name = name or cmd.name
        if name is None:
            raise TypeError('Command has no name.')
        self.commands[name] = cmd

    def command(self, *args, **kwargs):
        """A shortcut decorator for declaring and attaching a command to
        the group.  This takes the same arguments as :func:`command` but
        immediately registers the created command with this instance by
        calling into :meth:`add_command`.
        """
        def decorator(f):
            cmd = command(*args, **kwargs)(f)
            self.add_command(cmd)
            return cmd
        return decorator

    def group(self, *args, **kwargs):
        """A shortcut decorator for declaring and attaching a group to
        the group.  This takes the same arguments as :func:`group` but
        immediately registers the created command with this instance by
        calling into :meth:`add_command`.
        """
        def decorator(f):
            cmd = group(*args, **kwargs)(f)
            self.add_command(cmd)
            return cmd
        return decorator

    def get_command(self, ctx, cmd_name):
        return self.commands.get(cmd_name)

    def list_commands(self, ctx):
        return sorted(self.commands)


class CommandCollection(MultiCommand):
    """A command collection is a multi command that merges multiple multi
    commands together into one.  This is a straightforward implementation
    that accepts a list of different multi commands as sources and
    provides all the commands for each of them.
    """

    def __init__(self, name=None, sources=None, **attrs):
        MultiCommand.__init__(self, name, **attrs)
        #: The list of registered multi commands.
        self.sources = sources or []

    def add_source(self, multi_cmd):
        """Adds a new multi command to the chain dispatcher."""
        self.sources.append(multi_cmd)

    def get_command(self, ctx, cmd_name):
        for source in self.sources:
            rv = source.get_command(ctx, cmd_name)
            if rv is not None:
                return rv

    def list_commands(self, ctx):
        rv = set()
        for source in self.sources:
            rv.update(source.list_commands(ctx))
        return sorted(rv)


class Parameter(object):
    """A parameter to a command comes in two versions: they are either
    :class:`Option`\s or :class:`Argument`\s.  Other subclasses are currently
    not supported by design as some of the internals for parsing are
    intentionally not finalized.

    Some settings are supported by both options and arguments.

    .. versionchanged:: 2.0
       Changed signature for parameter callback to also be passed the
       parameter.  In click 2.0 the old callback format will still work
       but it will raise a warning to give you change to migrate the
       code easier.

    :param param_decls: the parameter declarations for this option or
                        argument.  This is a list of flags or argument
                        names.
    :param type: the type that should be used.  Either a :class:`ParamType`
                 or a python type.  The later is converted into the former
                 automatically if supported.
    :param required: controls if this is optional or not.
    :param default: the default value if omitted.  This can also be a callable
                    in which case it's invoked when the default is needed
                    without any arguments.
    :param callback: a callback that should be executed after the parameter
                     was matched.  This is called as ``fn(ctx, param,
                     value)`` and needs to return the value.  Before click
                     2.0 the signature was ``(ctx, value)``.
    :param nargs: the number of arguments to match.  If not ``1`` the return
                  value is a tuple instead of single value.
    :param metavar: how the value is represented in the help page.
    :param expose_value: if this is `True` then the value is passed onwards
                         to the command callback and stored on the context,
                         otherwise it's skipped.
    :param is_eager: eager values are processed before non eager ones.  This
                     should not be set for arguments or it will inverse the
                     order of processing.
    :param envvar: a string or list of strings that are environment variables
                   that should be checked.
    """
    param_type_name = 'parameter'

    def __init__(self, param_decls=None, type=None, required=False,
                 default=None, callback=None, nargs=1, metavar=None,
                 expose_value=True, is_eager=False, envvar=None):
        self.name, self.opts, self.secondary_opts = \
            self._parse_decls(param_decls or ())
        self.type = convert_type(type, default)
        self.required = required
        self.callback = callback
        self.nargs = nargs
        self.multiple = False
        self.expose_value = expose_value
        self.default = default
        self.is_eager = is_eager
        self.metavar = metavar
        self.envvar = envvar

    def make_metavar(self):
        if self.metavar is not None:
            return self.metavar
        metavar = self.type.get_metavar(self)
        if metavar is None:
            metavar = self.type.name.upper()
        if self.nargs != 1:
            metavar += '...'
        return metavar

    def get_default(self, ctx):
        """Given a context variable this calculates the default value."""
        # Otherwise go with the regular default.
        if callable(self.default):
            rv = self.default()
        else:
            rv = self.default
        return self.type(rv, self, ctx)

    def add_to_parser(self, parser, ctx):
        pass

    def consume_value(self, ctx, opts):
        value = opts.get(self.name)
        if value is None:
            value = ctx.lookup_default(self.name)
        if value is None:
            value = self.value_from_envvar(ctx)
        return value

    def process_value(self, ctx, value):
        """Given a value and context this runs the logic to convert the
        value as necessary.
        """
        def _convert(value, level):
            if level == 0:
                return self.type(value, self, ctx)
            return tuple(_convert(x, level - 1) for x in value or ())
        return _convert(value, (self.nargs != 1) + bool(self.multiple))

    def value_is_missing(self, value):
        if value is None:
            return True
        if (self.nargs != 1 or self.multiple) and value == ():
            return True
        return False

    def full_process_value(self, ctx, value):
        value = self.process_value(ctx, value)

        if value is None:
            value = self.get_default(ctx)

        if self.required and self.value_is_missing(value):
            ctx.fail(self.get_missing_message(ctx))

        return value

    def get_missing_message(self, ctx):
        return 'Missing %s %s.' % (
            self.param_type_name,
            ' / '.join('"%s"' % x for x in chain(
                self.opts, self.secondary_opts)),
        )

    def resolve_envvar_value(self, ctx):
        if self.envvar is None:
            return
        if isinstance(self.envvar, (tuple, list)):
            for envvar in self.envvar:
                rv = os.environ.get(envvar)
                if rv is not None:
                    return rv
        else:
            return os.environ.get(self.envvar)

    def value_from_envvar(self, ctx):
        rv = self.resolve_envvar_value(ctx)
        if rv is not None and self.nargs != 1:
            rv = self.type.split_envvar_value(rv)
        return rv

    def handle_parse_result(self, ctx, opts, args):
        with augment_usage_errors(ctx, param=self):
            value = self.consume_value(ctx, opts)
            value = self.full_process_value(ctx, value)
            if self.callback is not None:
                value = invoke_param_callback(
                    self.callback, ctx, self, value)

        if self.expose_value:
            ctx.params[self.name] = value
        return value, args

    def get_help_record(self, ctx):
        pass

    def get_usage_pieces(self, ctx):
        return []


class Option(Parameter):
    """Options are usually optionaly values on the command line and
    have some extra features that arguments don't have.

    All other parameters are passed onwards to the parameter constructor.

    :param show_default: controls if the default value should be shown on the
                         help page.  Normally defaults are not shown.
    :param prompt: if set to `True` or a non empty string then the user will
                   be prompted for input if not set.  If set to `True` the
                   prompt will be the option name capitalized.
    :param confirmation_prompt: if set then the value will need to be confirmed
                                if it was prompted for.
    :param hide_input: if this is `True` then the input on the prompt will be
                       hidden from the user.  This is useful for password
                       input.
    :param is_flag: forces this option to act as a flag.  The default is
                    auto detection.
    :param flag_value: which value should be used for this flag if it's
                       enabled.  This is set to a boolean automatically if
                       the option string contains a slash to mark two options.
    :param multiple: if this is set to `True` then the argument is accepted
                     multiple times and recorded.  This is similar to ``nargs``
                     in how it works but supports arbitrary number of
                     arguments.
    :param count: this flag makes an option increment an integer.
    :param allow_from_autoenv: if this is enabled then the value of this
                               parameter will be pulled from an environment
                               variable in case a prefix is defined on the
                               context.
    :param help: the help string.
    """
    param_type_name = 'option'

    def __init__(self, param_decls=None, show_default=False,
                 prompt=False, confirmation_prompt=False,
                 hide_input=False, is_flag=None, flag_value=None,
                 multiple=False, count=False, allow_from_autoenv=True,
                 type=None, help=None, **attrs):
        default_is_missing = attrs.get('default', _missing) is _missing
        Parameter.__init__(self, param_decls, type=type, **attrs)

        if prompt is True:
            prompt_text = self.name.replace('_', ' ').capitalize()
        elif prompt is False:
            prompt_text = None
        else:
            prompt_text = prompt
        self.prompt = prompt_text
        self.confirmation_prompt = confirmation_prompt
        self.hide_input = hide_input

        # Flags
        if is_flag is None:
            if flag_value is not None:
                is_flag = True
            else:
                is_flag = bool(self.secondary_opts)
        if is_flag and default_is_missing:
            self.default = False
        if flag_value is None:
            flag_value = not self.default
        self.is_flag = is_flag
        self.flag_value = flag_value
        if self.is_flag and isinstance(self.flag_value, bool) \
           and type is None:
            self.type = BOOL
            self.is_bool_flag = True
        else:
            self.is_bool_flag = False

        # Counting
        self.count = count
        if count:
            if type is None:
                self.type = IntRange(min=0)
            if default_is_missing:
                self.default = 0

        self.multiple = multiple
        self.allow_from_autoenv = allow_from_autoenv
        self.help = help
        self.show_default = show_default

        # Sanity check for stuff we don't support
        if __debug__:
            if self.prompt and self.is_flag and not self.is_bool_flag:
                raise TypeError('Cannot prompt for flags that are not bools.')
            if not self.is_bool_flag and self.secondary_opts:
                raise TypeError('Got secondary option for non boolean flag.')
            if self.is_bool_flag and self.hide_input \
               and self.prompt is not None:
                raise TypeError('Hidden input does not work with boolean '
                                'flag prompts.')
            if self.count:
                if self.multiple:
                    raise TypeError('Options cannot be multiple and count '
                                    'at the same time.')
                elif self.is_flag:
                    raise TypeError('Options cannot be count and flags at '
                                    'the same time.')

    def _parse_decls(self, decls):
        opts = []
        secondary_opts = []
        name = None
        possible_names = []

        for decl in decls:
            if isidentifier(decl):
                if name is not None:
                    raise TypeError('Name defined twice')
                name = decl
            else:
                if '/' in decl:
                    first, second = decl.split('/', 1)
                    possible_names.append(split_opt(first))
                    opts.append(first)
                    secondary_opts.append(second)
                else:
                    possible_names.append(split_opt(decl))
                    opts.append(decl)

        if name is None and possible_names:
            possible_names.sort(key=lambda x: len(x[0]))
            name = possible_names[-1][1].replace('-', '_').lower()
            if not isidentifier(name):
                name = None

        if name is None:
            raise TypeError('Could not determine name for option')

        return name, opts, secondary_opts

    def add_to_parser(self, parser, ctx):
        kwargs = {
            'dest': self.name,
            'nargs': self.nargs,
            'obj': self,
        }

        if self.multiple:
            action = 'append'
        elif self.count:
            action = 'count'
        else:
            action = 'store'

        if self.is_flag:
            kwargs.pop('nargs', None)
            if self.is_bool_flag and self.secondary_opts:
                parser.add_option(self.opts, action=action + '_const',
                                  const=True, **kwargs)
                parser.add_option(self.secondary_opts, action=action +
                                  '_const', const=False, **kwargs)
            else:
                parser.add_option(self.opts, action=action + '_const',
                                  const=self.flag_value,
                                  **kwargs)
        else:
            kwargs['action'] = action
            parser.add_option(self.opts, **kwargs)

    def get_help_record(self, ctx):
        def _write_opts(opts):
            rv = []
            for opt in opts:
                prefix = split_opt(opt)[0]
                rv.append((len(prefix), opt))

            rv.sort(key=lambda x: x[0])

            rv = ', '.join(x[1] for x in rv)
            if not self.is_flag:
                rv += ' ' + self.make_metavar()
            return rv

        rv = [_write_opts(self.opts)]
        if self.secondary_opts:
            rv.append(_write_opts(self.secondary_opts))

        help = self.help or ''
        extra = []
        if self.default is not None and self.show_default:
            extra.append('default: %s' % self.default)
        if self.required:
            extra.append('required')
        if extra:
            help = '%s[%s]' % (help and help + '  ' or '', '; '.join(extra))

        return (' / '.join(rv), help)

    def get_default(self, ctx):
        # If we're a non boolean flag out default is more complex because
        # we need to look at all flags in the same group to figure out
        # if we're the the default one in which case we return the flag
        # value as default.
        if self.is_flag and not self.is_bool_flag:
            for param in ctx.command.params:
                if param.name == self.name and param.default:
                    return param.flag_value
            return None
        return Parameter.get_default(self, ctx)

    def prompt_for_value(self, ctx):
        """This is an alternative flow that can be activated in the full
        value processing if a value does not exist.  It will prompt the
        user until a valid value exists and then returns the processed
        value as result.
        """
        # Calculate the default before prompting anything to be stable.
        default = self.get_default(ctx)

        # If this is a prompt for a flag we need to handle this
        # differently.
        if self.is_bool_flag:
            return confirm(self.prompt, default)

        return prompt(self.prompt, default=default,
                      hide_input=self.hide_input,
                      confirmation_prompt=self.confirmation_prompt,
                      value_proc=lambda x: self.process_value(ctx, x))

    def resolve_envvar_value(self, ctx):
        rv = Parameter.resolve_envvar_value(self, ctx)
        if rv is not None:
            return rv
        if self.allow_from_autoenv and \
           ctx.auto_envvar_prefix is not None:
            envvar = '%s_%s' % (ctx.auto_envvar_prefix, self.name.upper())
            return os.environ.get(envvar)

    def value_from_envvar(self, ctx):
        rv = self.resolve_envvar_value(ctx)
        if rv is None:
            return None
        value_depth = (self.nargs != 1) + bool(self.multiple)
        if value_depth > 0 and rv is not None:
            rv = self.type.split_envvar_value(rv)
            if self.multiple and self.nargs != 1:
                rv = batch(rv, self.nargs)
        return rv

    def full_process_value(self, ctx, value):
        if value is None and self.prompt is not None:
            return self.prompt_for_value(ctx)
        return Parameter.full_process_value(self, ctx, value)


class Argument(Parameter):
    """Arguments are positional parameters to a command.  They generally
    provide fewer features than options but can have infinite ``nargs``
    and are required by default.

    All parameters are passed onwards to the parameter constructor.
    """
    param_type_name = 'argument'

    def __init__(self, param_decls, required=None, **attrs):
        if required is None:
            if attrs.get('default') is not None:
                required = False
            else:
                required = attrs.get('nargs', 1) > 0
        Parameter.__init__(self, param_decls, required=required, **attrs)

    def make_metavar(self):
        if self.metavar is not None:
            return self.metavar
        var = self.name.upper()
        if not self.required:
            var = '[%s]' % var
        if self.nargs != 1:
            var += '...'
        return var

    def _parse_decls(self, decls):
        if not decls:
            raise TypeError('Could not determine name for argument')
        if len(decls) == 1:
            name = arg = decls[0]
            name = name.replace('-', '_').lower()
        elif len(decls) == 2:
            name, arg = decls
        else:
            raise TypeError('Arguments take exactly one or two '
                            'parameter declarations, got %d' % len(decls))
        return name, [arg], []

    def get_usage_pieces(self, ctx):
        return [self.make_metavar()]

    def add_to_parser(self, parser, ctx):
        parser.add_argument(dest=self.name, nargs=self.nargs,
                            obj=self)


# Circular dependency between decorators and core
from .decorators import command, group, help_option

########NEW FILE########
__FILENAME__ = decorators
import sys
import inspect

from functools import update_wrapper

from ._compat import iteritems
from .utils import echo


def pass_context(f):
    """Marks a callback that it wants to receive the current context
    object as first argument.
    """
    f.__click_pass_context__ = True
    return f


def pass_obj(f):
    """Similar to :func:`pass_context` but only pass the object on the
    context onwards (:attr:`Context.obj`).  This is useful if that object
    represents the state of a nested system.
    """
    @pass_context
    def new_func(*args, **kwargs):
        ctx = args[0]
        return ctx.invoke(f, ctx.obj, *args[1:], **kwargs)
    return update_wrapper(new_func, f)


def make_pass_decorator(object_type, ensure=False):
    """Given an object type this creates a decorator that will work
    similar to :func:`pass_obj` but instead of passing the object of the
    current context, it will find the innermost context of type
    :func:`object_type`.

    This generates a decorator that works roughly like this::

        from functools import update_wrapper

        def decorator(f):
            @pass_context
            def new_func(ctx, *args, **kwargs):
                obj = ctx.find_object(object_type)
                return ctx.invoke(f, obj, *args, **kwargs)
            return update_wrapper(new_func, f)
        return decorator

    :param object_type: the type of the object to pass.
    :param ensure: if set to `True`, a new object will be created and
                   remembered on the context if it's not there yet.
    """
    def decorator(f):
        @pass_context
        def new_func(*args, **kwargs):
            ctx = args[0]
            if ensure:
                obj = ctx.ensure_object(object_type)
            else:
                obj = ctx.find_object(object_type)
            if obj is None:
                raise RuntimeError('Managed to invoke callback without a '
                                   'context object of type %r existing'
                                   % object_type.__name__)
            return ctx.invoke(f, obj, *args[1:], **kwargs)
        return update_wrapper(new_func, f)
    return decorator


def _make_command(f, name, attrs, cls):
    if isinstance(f, Command):
        raise TypeError('Attempted to convert a callback into a '
                        'command twice.')
    try:
        params = f.__click_params__
        params.reverse()
        del f.__click_params__
    except AttributeError:
        params = []
    help = inspect.getdoc(f)
    if isinstance(help, bytes):
        help = help.decode('utf-8')
    attrs.setdefault('help', help)
    return cls(name=name or f.__name__.lower(),
               callback=f, params=params, **attrs)


def command(name=None, cls=None, **attrs):
    """Creates a new :class:`Command` and uses the decorated function as
    callback.  This will also automatically attach all decorated
    :func:`option`\s and :func:`argument`\s as parameters to the command.

    The name of the command defaults to the name of the function.  If you
    want to change that, you can pass the intended name as the first
    argument.

    All keyword arguments are forwarded to the underlying command class.

    Once decorated the function turns into a :class:`Command` instance
    that can be invoked as a command line utility or be attached to a
    command :class:`Group`.

    :param name: the name of the command.  This defaults to the function
                 name.
    :param cls: the command class to instantiate.  This defaults to
                :class:`Command`.
    """
    if cls is None:
        cls = Command
    def decorator(f):
        return _make_command(f, name, attrs, cls)
    return decorator


def group(name=None, **attrs):
    """Creates a new :class:`Group` with a function as callback.  This
    works otherwise the same as :func:`command` just that the `cls`
    parameter is set to :class:`Group`.
    """
    attrs.setdefault('cls', Group)
    return command(name, **attrs)


def _param_memo(f, param):
    if isinstance(f, Command):
        f.params.append(param)
    else:
        if not hasattr(f, '__click_params__'):
            f.__click_params__ = []
        f.__click_params__.append(param)


def argument(*param_decls, **attrs):
    """Attaches an option to the command.  All positional arguments are
    passed as parameter declarations to :class:`Argment`, all keyword
    arguments are forwarded unchanged.  This is equivalent to creating an
    :class:`Option` instance manually and attaching it to the
    :attr:`Command.params` list.
    """
    def decorator(f):
        _param_memo(f, Argument(param_decls, **attrs))
        return f
    return decorator


def option(*param_decls, **attrs):
    """Attaches an option to the command.  All positional arguments are
    passed as parameter declarations to :class:`Option`, all keyword
    arguments are forwarded unchanged.  This is equivalent to creating an
    :class:`Option` instance manually and attaching it to the
    :attr:`Command.params` list.
    """
    def decorator(f):
        _param_memo(f, Option(param_decls, **attrs))
        return f
    return decorator


def confirmation_option(*param_decls, **attrs):
    """Shortcut for confirmation prompts that can be ignored by bypassed
    ``--yes`` as parameter.

    This is equivalent to decorating a function with :func:`option` with
    the following parameters::

        def callback(ctx, param, value):
            if not value:
                ctx.abort()

        @click.command()
        @click.option('--yes', is_flag=True, callback=callback,
                      expose_value=False, prompt='Do you want to continue?')
        def dropdb():
            pass
    """
    def decorator(f):
        def callback(ctx, param, value):
            if not value:
                ctx.abort()
        attrs.setdefault('is_flag', True)
        attrs.setdefault('callback', callback)
        attrs.setdefault('expose_value', False)
        attrs.setdefault('prompt', 'Do you want to continue?')
        attrs.setdefault('help', 'Confirm the action without prompting.')
        return option(*(param_decls or ('--yes',)), **attrs)(f)
    return decorator


def password_option(*param_decls, **attrs):
    """Shortcut for password prompts.

    This is equivalent to decorating a function with :func:`option` with
    the following parameters::

        @click.command()
        @click.option('--password', prompt=True, confirmation_prompt=True,
                      hide_input=True)
        def changeadmin(password):
            pass
    """
    def decorator(f):
        attrs.setdefault('prompt', True)
        attrs.setdefault('confirmation_prompt', True)
        attrs.setdefault('hide_input', True)
        return option(*(param_decls or ('--password',)), **attrs)(f)
    return decorator


def version_option(version=None, *param_decls, **attrs):
    """Adds a ``--version`` option which immediately ends the program
    printing out the version number.  This is implemented as an eager
    option that prints the version and exits the program in the callback.

    :param version: the version number to show.  If not provided click
                    attempts an auto discovery via setuptools.
    :param prog_name: the name of the program (defaults to autodetection)
    :param message: custom message to show instead of the default
                    (``'%(prog)s, version %(version)s'``)
    :param others: everything else is forwarded to :func:`option`.
    """
    if version is None:
        module = sys._getframe(1).f_globals.get('__name__')
    def decorator(f):
        prog_name = attrs.pop('prog_name', None)
        message = attrs.pop('message', '%(prog)s, version %(version)s')

        def callback(ctx, param, value):
            if not value:
                return
            prog = prog_name
            if prog is None:
                prog = ctx.find_root().info_name
            ver = version
            if ver is None:
                try:
                    import pkg_resources
                except ImportError:
                    pass
                else:
                    for dist in pkg_resources.working_set:
                        scripts = dist.get_entry_map().get('console_scripts') or {}
                        for script_name, entry_point in iteritems(scripts):
                            if entry_point.module_name == module:
                                ver = dist.version
                                break
                if ver is None:
                    raise RuntimeError('Could not determine version')
            echo(message % {
                'prog': prog,
                'version': ver,
            })
            ctx.exit()

        attrs.setdefault('is_flag', True)
        attrs.setdefault('expose_value', False)
        attrs.setdefault('is_eager', True)
        attrs.setdefault('help', 'Show the version and exit.')
        attrs['callback'] = callback
        return option(*(param_decls or ('--version',)), **attrs)(f)
    return decorator


def help_option(*param_decls, **attrs):
    """Adds a ``--help`` option which immediately ends the program
    printing out the help page.  This is usually unnecessary to add as
    this is added by default to all commands unless supressed.

    Like :func:`version_option` this is implemented as eager option that
    prints in the callback and exits.

    All arguments are forwarded to :func:`option`.
    """
    def decorator(f):
        def callback(ctx, param, value):
            if value:
                echo(ctx.get_help())
                ctx.exit()
        attrs.setdefault('is_flag', True)
        attrs.setdefault('expose_value', False)
        attrs.setdefault('help', 'Show this message and exit.')
        attrs.setdefault('is_eager', True)
        attrs['callback'] = callback
        return option(*(param_decls or ('--help',)), **attrs)(f)
    return decorator


# Circular dependencies between core and decorators
from .core import Command, Group, Argument, Option

########NEW FILE########
__FILENAME__ = exceptions
from ._compat import PY2, filename_to_ui
from .utils import echo


class ClickException(Exception):
    """An exception that click can handle and show to the user.."""

    #: The exit code for this exception
    exit_code = 1

    def __init__(self, message):
        if PY2:
            Exception.__init__(self, message.encode('utf-8'))
        else:
            Exception.__init__(self, message)
        self.message = message

    def format_message(self):
        return self.message

    def show(self, file=None):
        echo('Error: %s' % self.format_message())


class UsageError(ClickException):
    """An internal exception that signals a usage error.  This typically
    aborts any further handling.

    :param message: the error message to display.
    :param ctx: optionally the context that caused this error.  Click will
                fill in the context automatically in some situations.
    """
    exit_code = 2

    def __init__(self, message, ctx=None):
        ClickException.__init__(self, message)
        self.ctx = ctx

    def show(self, file=None):
        if self.ctx is not None:
            echo(self.ctx.get_usage() + '\n', file=file)
        echo('Error: %s' % self.format_message(), file=file)


class BadParameter(UsageError):
    """An exception that formats out a standardized error message for a
    bad parameter.  This is useful when thrown from a callback or type as
    click will attach contextual information to it (for instance like
    which parameter it is).

    .. versionadded:: 2.0

    :param param: the parameter object that caused this error.  This can
                  be left and click if possible will attach this info
                  itself.
    :param param_hint: a string that shows up as parameter name.  This
                       can be used as alternative to `param` in cases
                       where custom validation should happen.  If it is
                       a string it's used as such, if it's a list then
                       each item is quoted and separated.
    """

    def __init__(self, message, ctx=None, param=None,
                 param_hint=None):
        UsageError.__init__(self, message, ctx)
        self.param = param
        self.param_hint = param_hint

    def format_message(self):
        if self.param_hint is not None:
            param_hint = self.param_hint
        elif self.param is not None:
            param_hint = self.param.opts or [self.param.name]
        else:
            return 'Invalid value: %s' % self.message
        if isinstance(param_hint, (tuple, list)):
            param_hint = ' / '.join('"%s"' % x for x in param_hint)
        return 'Invalid value for %s: %s' % (param_hint, self.message)


class FileError(ClickException):
    """Raised if a file cannot be opened."""

    def __init__(self, filename, hint=None):
        ui_filename = filename_to_ui(filename)
        if hint is None:
            hint = 'unknown error'
        ClickException.__init__(self, hint)
        self.ui_filename = ui_filename
        self.filename = filename

    def format_message(self):
        return 'Could not open file %s: %s' % (self.ui_filename, self.message)


class Abort(RuntimeError):
    """An internal signalling exception that signals click to abort."""

########NEW FILE########
__FILENAME__ = formatting
import textwrap
from contextlib import contextmanager

from .termui import get_terminal_size
from ._compat import strip_ansi


def term_len(x):
    return len(strip_ansi(x))


def measure_table(rows):
    widths = {}
    for row in rows:
        for idx, col in enumerate(row):
            widths[idx] = max(widths.get(idx, 0), term_len(col))
    return tuple(y for x, y in sorted(widths.items()))


def iter_rows(rows, col_count):
    for row in rows:
        row = tuple(row)
        yield row + ('',) * (col_count - len(row))


class TextWrapper(textwrap.TextWrapper):

    def _cutdown(self, ucstr, space_left):
        l = 0
        for i in xrange(len(ucstr)):
            l += term_len(ucstr[i])
            if space_left < l:
                return (ucstr[:i], ucstr[i:])
        return ucstr, ''

    def _handle_long_word(self, reversed_chunks, cur_line, cur_len, width):
        space_left = max(width - cur_len, 1)

        if self.break_long_words:
            cut, res = self._cutdown(reversed_chunks[-1], space_left)
            cur_line.append(cut)
            reversed_chunks[-1] = res
        elif not cur_line:
            cur_line.append(reversed_chunks.pop())

    @contextmanager
    def extra_indent(self, indent):
        old_initial_indent = self.initial_indent
        old_subsequent_indent = self.subsequent_indent
        self.initial_indent += indent
        self.subsequent_indent += indent
        try:
            yield
        finally:
            self.initial_indent = old_initial_indent
            self.subsequent_indent = old_subsequent_indent

    def indent_only(self, text):
        rv = []
        for idx, line in enumerate(text.splitlines()):
            indent = self.initial_indent
            if idx > 0:
                indent = self.subsequent_indent
            rv.append(indent + line)
        return '\n'.join(rv)


def wrap_text(text, width=78, initial_indent='', subsequent_indent='',
              preserve_paragraphs=False):
    """A helper function that intelligently wraps text.  By default it
    assumes that it operates on a single paragraph of text but if the
    `preserve_paragraphs` parameter is provided it will intelligently
    handle paragraphs (defined by two empty lines).

    If paragraphs are handled a paragraph can be prefixed with an empty
    line containing the ``\\b`` character (``\\x08``) to indicate that
    no rewrapping should happen in that block.

    :param text: the text that should be rewrapped.
    :param width: the maximum width for the text.
    :param initial_indent: the initial indent that should be placed on the
                           first line as a string.
    :param subsequent_indent: the indent string that should be placed on
                              each consecutive line.
    :param preserve_paragraphs: if this flag is set then the wrapping will
                                intelligently handle paragraphs.
    """
    text = text.expandtabs()
    wrapper = TextWrapper(width, initial_indent=initial_indent,
                          subsequent_indent=subsequent_indent,
                          replace_whitespace=False)
    if not preserve_paragraphs:
        return wrapper.fill(text)

    p = []
    buf = []
    indent = None

    def _flush_par():
        if not buf:
            return
        if buf[0].strip() == '\b':
            p.append((indent or 0, True, '\n'.join(buf[1:])))
        else:
            p.append((indent or 0, False, ' '.join(buf)))
        del buf[:]

    for line in text.splitlines():
        if not line:
            _flush_par()
            indent = None
        else:
            if indent is None:
                orig_len = term_len(line)
                line = line.lstrip()
                indent = orig_len - term_len(line)
            buf.append(line)
    _flush_par()

    rv = []
    for indent, raw, text in p:
        with wrapper.extra_indent(' ' * indent):
            if raw:
                rv.append(wrapper.indent_only(text))
            else:
                rv.append(wrapper.fill(text))

    return '\n\n'.join(rv)


class HelpFormatter(object):
    """This class helps with formatting text based help pages.  It's
    usually just needed for very special internal cases but it's also
    exposed so that developers can write their own fancy outputs.

    At present it always writes into memory.

    :param indent_increment: the additional increment for each level.
    :param width: the width for the text.  This defaults to the terminal
                  width clamped to a maximum of 78.
    """

    def __init__(self, indent_increment=2, width=None):
        self.indent_increment = indent_increment
        if width is None:
            width = min(get_terminal_size()[0], 80) - 2
        self.width = width
        self.current_indent = 0
        self.buffer = []

    def write(self, string):
        """Writes a unicode string into the internal buffer."""
        self.buffer.append(string)

    def indent(self):
        """Increases the indentation."""
        self.current_indent += self.indent_increment

    def dedent(self):
        """Decreases the indentation."""
        self.current_indent -= self.indent_increment

    def write_usage(self, prog, args='', prefix='Usage: '):
        """Writes a usage line into the buffer.

        :param prog: the program name.
        :param args: whitespace separated list of arguments.
        :param prefix: the prefix for the first line.
        """
        prefix = '%*s%s' % (self.current_indent, prefix, prog)
        self.write(prefix)

        text_width = max(self.width - self.current_indent - term_len(prefix), 10)
        indent = ' ' * (term_len(prefix) + 1)
        self.write(wrap_text(args, text_width,
                             initial_indent=' ',
                             subsequent_indent=indent))

        self.write('\n')

    def write_heading(self, heading):
        """Writes a heading into the buffer."""
        self.write('%*s%s:\n' % (self.current_indent, '', heading))

    def write_paragraph(self):
        """Writes a paragraph into the buffer."""
        if self.buffer:
            self.write('\n')

    def write_text(self, text):
        """Writes re-indented text into the buffer.  This rewraps and
        preserves paragraphs.
        """
        text_width = max(self.width - self.current_indent, 11)
        indent = ' ' * self.current_indent
        self.write(wrap_text(text, text_width,
                             initial_indent=indent,
                             subsequent_indent=indent,
                             preserve_paragraphs=True))
        self.write('\n')

    def write_dl(self, rows, col_max=30, col_spacing=2):
        """Writes a definition list into the buffer.  This is how options
        and commands are usually formatted.

        :param rows: a list of two item tuples for the terms and values.
        :param col_max: the maximum width of the first column.
        :param col_spacing: the number of spaces between the first and
                            second column.
        """
        rows = list(rows)
        widths = measure_table(rows)
        if len(widths) != 2:
            raise TypeError('Expected two columns for definition list')

        first_col = min(widths[0], col_max) + col_spacing

        for first, second in iter_rows(rows, len(widths)):
            self.write('%*s%s' % (self.current_indent, '', first))
            if not second:
                self.write('\n')
                continue
            if term_len(first) <= first_col - col_spacing:
                self.write(' ' * (first_col - term_len(first)))
            else:
                self.write('\n')
                self.write(' ' * (first_col + self.current_indent))

            text_width = self.width - first_col - 2
            lines = iter(wrap_text(second, text_width).splitlines())
            if lines:
                self.write(next(lines) + '\n')
                for line in lines:
                    self.write('%*s%s\n' % (
                        first_col + self.current_indent, '', line))
            else:
                self.write('\n')

    @contextmanager
    def section(self, name):
        """Helpful context manager that writes a paragraph, a heading
        and the indents.

        :param name: the section name that is written as heading.
        """
        self.write_paragraph()
        self.write_heading(name)
        self.indent()
        try:
            yield
        finally:
            self.dedent()

    @contextmanager
    def indentation(self):
        """A context manager that increases the indentation."""
        self.indent()
        try:
            yield
        finally:
            self.dedent()

    def getvalue(self):
        """Returns the buffer contents."""
        return ''.join(self.buffer)

########NEW FILE########
__FILENAME__ = parser
# -*- coding: utf-8 -*-
"""
    click.parser
    ~~~~~~~~~~~~

    This module started out as largely a copy paste from the stdlib's
    optparse module with the features removed that we do not need from
    optparse because we implement them in click on a higher level (for
    instance type handling, help formatting and a lot more).

    The plan is to remove more and more from here over time.

    The reason this is a different module and not optparse from the stdlib
    is that there are differences in 2.x and 3.x about the error messages
    generated and optparse in the stdlib uses gettext for no good reason
    and might cause us issues.
"""
from .exceptions import UsageError
from .utils import unpack_args


def split_opt(opt):
    first = opt[:1]
    if first.isalnum():
        return '', opt
    if opt[1:2] == first:
        return opt[:2], opt[2:]
    return first, opt[1:]


class Option(object):

    def __init__(self, opts, dest, action=None, nargs=1, const=None, obj=None):
        self._short_opts = []
        self._long_opts = []
        self.prefixes = set()

        for opt in opts:
            prefix = split_opt(opt)[0]
            if not prefix:
                raise ValueError('Invalid start character for option (%s)'
                                 % opt)
            self.prefixes.add(prefix[0])
            if len(prefix) == 1:
                self._short_opts.append(opt)
            else:
                self._long_opts.append(opt)
                self.prefixes.add(prefix)

        if action is None:
            action = 'store'

        self.dest = dest
        self.action = action
        self.nargs = nargs
        self.const = const
        self.obj = obj

    @property
    def takes_value(self):
        return self.action in ('store', 'append')

    def process(self, value, state):
        if self.action == 'store':
            state.opts[self.dest] = value
        elif self.action == 'store_const':
            state.opts[self.dest] = self.const
        elif self.action == 'append':
            state.opts.setdefault(self.dest, []).append(value)
        elif self.action == 'append_const':
            state.opts.setdefault(self.dest, []).append(self.const)
        elif self.action == 'count':
            state.opts[self.dest] = state.opts.get(self.dest, 0) + 1
        else:
            raise ValueError('unknown action %r' % self.action)
        state.order.append(self.obj)


class Argument(object):

    def __init__(self, dest, nargs=1, obj=None):
        self.dest = dest
        self.nargs = nargs
        self.obj = obj

    def process(self, value, state):
        state.opts[self.dest] = value
        state.order.append(self.obj)


class ParsingState(object):

    def __init__(self, rargs):
        self.opts = {}
        self.largs = []
        self.rargs = rargs
        self.order = []


class OptionParser(object):
    """The option parser is an internal class that is ultimately used to
    parse options and arguments.  It's modelled after optparse and brings
    a similar but vastly simplified API.  It should generally not be used
    directly as the high level click classes wrap it for you.

    It's not nearly as extensible as optparse or argparse as it does not
    implement features that are implemented on a higher level (such as
    types or defaults).

    :param ctx: optionally the :class:`~click.Context` where this parser
                should go with.
    """

    def __init__(self, ctx=None):
        #: The :class:`~click.Context` for this parser.  This might be
        #: `None` for some advanced use cases.
        self.ctx = ctx
        #: This controls how the parser deals with interspersed arguments.
        #: If this is set to `False`, the parser will stop on the first
        #: non-option.  Click uses this to implement nested subcommands
        #: safely.
        self.allow_interspersed_args = True
        self._short_opt = {}
        self._long_opt = {}
        self._opt_prefixes = set(['-', '--'])
        self._args = []

    def add_option(self, opts, dest, action=None, nargs=1, const=None,
                   obj=None):
        """Adds a new option named `dest` to the parser.  The destination
        is not inferred unlike with optparse and needs to be explicitly
        provided.  Action can be any of ``store``, ``store_const``,
        ``append``, ``appnd_const`` or ``count``.

        The `obj` can be used to identify the option in the order list
        that is returned from the parser.
        """
        if obj is None:
            obj = dest
        option = Option(opts, dest, action=action, nargs=nargs,
                        const=const, obj=obj)
        self._opt_prefixes.update(option.prefixes)
        for opt in option._short_opts:
            self._short_opt[opt] = option
        for opt in option._long_opts:
            self._long_opt[opt] = option

    def add_argument(self, dest, nargs=1, obj=None):
        """Adds a positional argument named `dest` to the parser.

        The `obj` can be used to identify the option in the order list
        that is returned from the parser.
        """
        if obj is None:
            obj = dest
        self._args.append(Argument(dest=dest, nargs=nargs, obj=obj))

    def parse_args(self, args):
        """Parses positional arguments and returns ``(values, args, order)``
        for the parsed options and arguments as well as the leftover
        arguments if there are any.  The order is a list of objects as they
        appear on the command line.  If arguments appear multiple times they
        will be memorized multiple times as well.
        """
        state = ParsingState(args)
        self._process_args_for_options(state)
        self._process_args_for_args(state)
        return state.opts, state.largs, state.order

    def _process_args_for_args(self, state):
        pargs, args = unpack_args(state.largs + state.rargs,
                                  [x.nargs for x in self._args])

        for idx, arg in enumerate(self._args):
            arg.process(pargs[idx], state)

        state.largs = args
        state.rargs = []

    def _process_args_for_options(self, state):
        while state.rargs:
            arg = state.rargs[0]
            arglen = len(arg)
            # Double dash es always handled explicitly regardless of what
            # prefixes are valid.
            if arg == '--':
                del state.rargs[0]
                return
            elif arg[:2] in self._opt_prefixes and arglen > 2:
                # process a single long option (possibly with value(s))
                self._process_long_opt(state)
            elif arg[:1] in self._opt_prefixes and arglen > 1:
                # process a cluster of short options (possibly with
                # value(s) for the last one only)
                self._process_short_opts(state)
            elif self.allow_interspersed_args:
                state.largs.append(arg)
                del state.rargs[0]
            else:
                return

        # Say this is the original argument list:
        # [arg0, arg1, ..., arg(i-1), arg(i), arg(i+1), ..., arg(N-1)]
        #                            ^
        # (we are about to process arg(i)).
        #
        # Then rargs is [arg(i), ..., arg(N-1)] and largs is a *subset* of
        # [arg0, ..., arg(i-1)] (any options and their arguments will have
        # been removed from largs).
        #
        # The while loop will usually consume 1 or more arguments per pass.
        # If it consumes 1 (eg. arg is an option that takes no arguments),
        # then after _process_arg() is done the situation is:
        #
        #   largs = subset of [arg0, ..., arg(i)]
        #   rargs = [arg(i+1), ..., arg(N-1)]
        #
        # If allow_interspersed_args is false, largs will always be
        # *empty* -- still a subset of [arg0, ..., arg(i-1)], but
        # not a very interesting subset!

    def _match_long_opt(self, opt):
        # Is there an exact match?
        if opt in self._long_opt:
            return opt

        # Isolate all words with s as a prefix.
        possibilities = [word for word in self._long_opt
                         if word.startswith(opt)]

        # No exact match, so there had better be just one possibility.
        if not possibilities:
            self._error('no such option: %s' % opt)
        elif len(possibilities) == 1:
            self._error('no such option: %s.  Did you mean %s?' %
                        (opt, possibilities[0]))
            return possibilities[0]
        else:
            # More than one possible completion: ambiguous prefix.
            possibilities.sort()
            self._error('no such option: %s.  (Possible options: %s)'
                        % (opt, ', '.join(possibilities)))

    def _process_long_opt(self, state):
        arg = state.rargs.pop(0)

        # Value explicitly attached to arg?  Pretend it's the next
        # argument.
        if '=' in arg:
            opt, next_arg = arg.split('=', 1)
            state.rargs.insert(0, next_arg)
            had_explicit_value = True
        else:
            opt = arg
            had_explicit_value = False

        opt = self._match_long_opt(opt)
        option = self._long_opt[opt]
        if option.takes_value:
            nargs = option.nargs
            if len(state.rargs) < nargs:
                if nargs == 1:
                    self._error('%s option requires an argument' % opt)
                else:
                    self._error('%s option requires %d arguments' % (opt, nargs))
            elif nargs == 1:
                value = state.rargs.pop(0)
            else:
                value = tuple(state.rargs[:nargs])
                del state.rargs[:nargs]

        elif had_explicit_value:
            self._error('%s option does not take a value' % opt)

        else:
            value = None

        option.process(value, state)

    def _process_short_opts(self, state):
        arg = state.rargs.pop(0)
        stop = False
        i = 1
        prefix = arg[0]
        for ch in arg[1:]:
            opt = prefix + ch
            option = self._short_opt.get(opt)
            i += 1

            if not option:
                self._error('no such option: %s' % opt)
            if option.takes_value:
                # Any characters left in arg?  Pretend they're the
                # next arg, and stop consuming characters of arg.
                if i < len(arg):
                    state.rargs.insert(0, arg[i:])
                    stop = True

                nargs = option.nargs
                if len(state.rargs) < nargs:
                    if nargs == 1:
                        self._error('%s option requires an argument' % opt)
                    else:
                        self._error('%s option requires %d arguments' %
                                    (opt, nargs))
                elif nargs == 1:
                    value = state.rargs.pop(0)
                else:
                    value = tuple(state.rargs[:nargs])
                    del state.rargs[:nargs]

            else:
                value = None

            option.process(value, state)

            if stop:
                break

    def _error(self, msg):
        raise UsageError(msg, self.ctx)

########NEW FILE########
__FILENAME__ = termui
import os
import sys
import struct

from ._compat import raw_input, PY2, text_type, string_types, \
     get_best_encoding, colorama, isatty, strip_ansi
from .utils import echo
from .exceptions import Abort, UsageError
from .types import convert_type


# The prompt functions to use.  The doc tools currently override these
# functions to customize how they work.
visible_prompt_func = raw_input

_ansi_colors = ('black', 'red', 'green', 'yellow', 'blue', 'magenta',
                'cyan', 'white', 'reset')
_ansi_reset_all = '\033[0m'


def hidden_prompt_func(prompt):
    import getpass
    return getpass.getpass(prompt)


def _build_prompt(text, suffix, show_default=False, default=None):
    prompt = text
    if default is not None and show_default:
        prompt = '%s [%s]' % (prompt, default)
    return prompt + suffix


def prompt(text, default=None, hide_input=False,
           confirmation_prompt=False, type=None,
           value_proc=None, prompt_suffix=': ', show_default=True):
    """Prompts a user for input.  This is a convenience function that can
    be used to prompt a user for input later.

    If the user aborts the input by sending a interrupt signal this
    function will catch it and raise a :exc:`Abort` exception.

    :param text: the text to show for the prompt.
    :param default: the default value to use if no input happens.  If this
                    is not given it will prompt until it's aborted.
    :param hide_input: if this is set to true then the input value will
                       be hidden.
    :param confirmation_prompt: asks for confirmation for the value.
    :param type: the type to use to check the value against.
    :param value_proc: if this parameter is provided it's a function that
                       is invoked instead of the type conversion to
                       convert a value.
    :param prompt_suffix: a suffix that should be added to the prompt.
    :param show_default: shows or hides the default value in the prompt.
    """
    result = None

    def prompt_func(text):
        f = hide_input and hidden_prompt_func or visible_prompt_func
        try:
            return f(text)
        except (KeyboardInterrupt, EOFError):
            raise Abort()

    if value_proc is None:
        value_proc = convert_type(type, default)

    prompt = _build_prompt(text, prompt_suffix, show_default, default)

    while 1:
        while 1:
            value = prompt_func(prompt)
            if value:
                break
            # If a default is set and used, then the confirmation
            # prompt is always skipped because that's the only thing
            # that really makes sense.
            elif default is not None:
                return default
        try:
            result = value_proc(value)
        except UsageError as e:
            echo('Error: %s' % e.message)
            continue
        if not confirmation_prompt:
            return result
        while 1:
            value2 = prompt_func('Repeat for confirmation: ')
            if value2:
                break
        if value == value2:
            return result
        echo('Error: the two entered values do not match')


def confirm(text, default=False, abort=False, prompt_suffix=': ',
            show_default=True):
    """Prompts for confirmation (yes/no question).

    If the user aborts the input by sending a interrupt signal this
    function will catch it and raise a :exc:`Abort` exception.

    :param text: the question to ask.
    :param default: the default for the prompt.
    :param abort: if this is set to `True` a negative answer aborts the
                  exception by raising :exc:`Abort`.
    :param prompt_suffix: a suffix that should be added to the prompt.
    :param show_default: shows or hides the default value in the prompt.
    """
    prompt = _build_prompt(text, prompt_suffix, show_default,
                           default and 'Y/n' or 'y/N')
    while 1:
        try:
            value = visible_prompt_func(prompt).lower().strip()
        except (KeyboardInterrupt, EOFError):
            raise Abort()
        if value in ('y', 'yes'):
            rv = True
        elif value in ('n', 'no'):
            rv = False
        elif value == '':
            rv = default
        else:
            echo('Error: invalid input')
            continue
        break
    if abort and not rv:
        raise Abort()
    return rv


def get_terminal_size():
    """Returns the current size of the terminal as tuple in the form
    ``(width, height)`` in columns and rows.
    """
    # If shutil has get_terminal_size() (Python 3.3 and later) use that
    if sys.version_info >= (3, 3):
        import shutil
        shutil_get_terminal_size = getattr(shutil, 'get_terminal_size', None)
        if shutil_get_terminal_size:
            sz = shutil_get_terminal_size()
            return sz.columns, sz.lines

    def ioctl_gwinsz(fd):
        try:
            import fcntl
            import termios
            cr = struct.unpack(
                'hh', fcntl.ioctl(fd, termios.TIOCGWINSZ, '1234'))
        except Exception:
            return
        return cr

    cr = ioctl_gwinsz(0) or ioctl_gwinsz(1) or ioctl_gwinsz(2)
    if not cr:
        try:
            fd = os.open(os.ctermid(), os.O_RDONLY)
            try:
                cr = ioctl_gwinsz(fd)
            finally:
                os.close(fd)
        except Exception:
            pass
    if not cr or not cr[0] or not cr[1]:
        cr = (os.environ.get('LINES', 25),
              os.environ.get('COLUMNS', 80))
    return int(cr[1]), int(cr[0])


def echo_via_pager(text):
    """This function takes a text and shows it via an environment specific
    pager on stdout.

    :param text: the text to page.
    """
    if not isinstance(text, string_types):
        text = text_type(text)

    if PY2 and isinstance(text, text_type):
        encoding = get_best_encoding(sys.stdout)
        text = text.encode(encoding, 'replace')

    from ._termui_impl import pager
    return pager(text + '\n')


def progressbar(iterable=None, length=None, label=None, show_eta=True,
                show_percent=None, show_pos=False,
                item_show_func=None, fill_char='#', empty_char='-',
                bar_template='%(label)s  [%(bar)s]  %(info)s',
                info_sep='  ', width=36, file=None):
    """This function creates an iterable context manager that can be used
    to iterate over something while showing a progress bar.  It will
    either iterate over the `iterable` or `length` items (that are counted
    up).  While iteration happens this function will print a rendered
    progress bar to the given `file` (defaults to stdout) and will attempt
    to calculate remaining time and more.  By default this progress bar
    will not be rendered if the file is not a terminal.

    The context manager creates the progress bar.  When the context
    manager is entered the progress bar is already displayed.  With every
    iteration over the progress bar the iterable passed to the bar is
    advanced and the bar is updated.  When the context manager exits
    a newline is printed and the progress bar is finalized on screen.

    No printing must happen or the progress bar will be unintentionally
    destroyed.

    Example usage::

        with progressbar(items) as bar:
            for item in bar:
                do_something_with(item)

    .. versionadded:: 2.0

    :param iterable: an iterable to iterate over.  If not provided the length
                     is required.
    :param length: the number of items to iterate over.  By default the
                   progressbar will attempt to ask the iterator about its
                   length, which might or might not work.  If an iterable is
                   also provided this parameter can be used to override the
                   length.  If an iterable is not provided the progress bar
                   will iterate over a range of that length.
    :param label: the label to show next to the progress bar.
    :param show_eta: enables or disables the estimated time display.  This is
                     automatically disabled if the length cannot be
                     determined.
    :param show_percent: enables or disables the percentage display.  The
                         default is `True` if the iterable has a length or
                         `False` if not.
    :param show_pos: enables or disables the absolute position display.  The
                     default is `False`.
    :param item_show_func: a function called with the current item which
                           can return a string to show the current item
                           next to the progress bar.  Note that the current
                           item can be `None`!
    :param fill_char: the character to use to show the filled part of the
                      progress bar.
    :param empty_char: the character to use to show the non-filled part of
                       the progress bar.
    :param bar_template: the format string to use as template for the bar.
                         The parameters in it are ``label`` for the label,
                         ``bar`` for the progress bar and ``info`` for the
                         info section.
    :param info_sep: the separator between multiple info items (eta etc.)
    :param width: the width of the progress bar in characters.
    :param file: the file to write to.  If this is not a terminal then
                 only the label is printed.
    """
    from ._termui_impl import ProgressBar
    return ProgressBar(iterable=iterable, length=length, show_eta=show_eta,
                       show_percent=show_percent, show_pos=show_pos,
                       item_show_func=item_show_func, fill_char=fill_char,
                       empty_char=empty_char, bar_template=bar_template,
                       info_sep=info_sep, file=file, label=label,
                       width=width)


def clear():
    """Clears the terminal screen.  This will have the effect of clearing
    the whole visible space of the terminal and moving the cursor to the
    top left.  This does not do anything if not connected to a terminal.

    .. versionadded:: 2.0
    """
    if not isatty(sys.stdout):
        return
    # If we're on windows and we don't have colorama available, then we
    # clear the screen by shelling out.  Otherwise we can use an escape
    # sequence.
    if sys.platform.startswith('win') and colorama is None:
        os.system('cls')
    else:
        sys.stdout.write('\033[2J\033[1;1H')


def style(text, fg=None, bg=None, bold=None, dim=None, underline=None,
          blink=None, reverse=None, reset=True):
    """Styles a text with ANSI styles and returns the new string.  By
    default the styling is self contained which means that at the end
    of the string a reset code is issued.  This can be prevented by
    passing ``reset=False``.

    Examples::

        click.echo(click.style('Hello World!', fg='green'))
        click.echo(click.style('ATTENTION!', blink=True))
        click.echo(click.style('Some things', reverse=True, fg='cyan'))

    Supported color names:

    * ``black`` (might be a gray)
    * ``red``
    * ``green``
    * ``yellow`` (might be an orange)
    * ``blue``
    * ``magenta``
    * ``cyan``
    * ``white`` (might be light gray)
    * ``reset`` (reset the color code only)

    .. versionadded:: 2.0

    :param text: the string to style with ansi codes.
    :param fg: if provided this will become the foreground color.
    :param bg: if provided this will become the background color.
    :param bold: if provided this will enable or disable bold mode.
    :param dim: if provided this will enable or disable dim mode.  This is
                badly supported.
    :param underline: if provided this will enable or disable underline.
    :param blink: if provided this will enable or disable blinking.
    :param reverse: if provided this will enable or disable inverse
                    rendering (foreground becomes background and the
                    other way round).
    :param reset: by default a reset-all code is added at the end of the
                  string which means that styles do not carry over.  This
                  can be disabled to compose styles.
    """
    bits = []
    if fg:
        try:
            bits.append('\033[%dm' % (_ansi_colors.index(fg) + 30))
        except ValueError:
            raise TypeError('Unknown color %r' % fg)
    if bg:
        try:
            bits.append('\033[%dm' % (_ansi_colors.index(bg) + 40))
        except ValueError:
            raise TypeError('Unknown color %r' % bg)
    if bold is not None:
        bits.append('\033[%dm' % (1 if bold else 22))
    if dim is not None:
        bits.append('\033[%dm' % (2 if dim else 22))
    if underline is not None:
        bits.append('\033[%dm' % (4 if underline else 24))
    if blink is not None:
        bits.append('\033[%dm' % (5 if blink else 25))
    if reverse is not None:
        bits.append('\033[%dm' % (7 if reverse else 27))
    bits.append(text)
    if reset:
        bits.append(_ansi_reset_all)
    return ''.join(bits)


def unstyle(text):
    """Removes ANSI styling information from a string.  Usually it's not
    necessary to use this function as click's echo function will
    automatically remove styling if necessary.

    .. versionadded:: 2.0

    :param text: the text to remove style information from.
    """
    return strip_ansi(text)


def secho(text, file=None, nl=True, **styles):
    """This function combines :func:`echo` and :func:`style` into one
    call.  As such the following two calls are the same::

        click.secho('Hello World!', fg='green')
        click.echo(click.style('Hello World!', fg='green'))

    All keyword arguments are forwarded to the underlying functions
    depending on which one they go with.

    .. versionadded:: 2.0
    """
    text = style(text, **styles)
    return echo(text, file=file, nl=nl)


def edit(text=None, editor=None, env=None, require_save=True,
         extension='.txt', filename=None):
    r"""Edits the given text in the defined editor.  If an editor is given
    (should be the full path to the executable but the regular operating
    system search path is used for finding the executable) it overrides
    the detected editor.  Optionally some environment variables can be
    used.  If the editor is closed without changes `None` is returned.  In
    case a file is edited directly the return value is always `None` and
    `require_save` and `extension` are ignored.

    If the editor cannot be opened a :exc:`UsageError` is raised.

    Note for Windows: to simplify cross platform usage the newlines are
    automatically converted from posix to windows and reverse.  As such the
    message here will have ``\n`` as newline markers.

    :param text: the text to edit.
    :param editor: optionally the editor to use.  Defaults to automatic
                   detection.
    :param env: environment variables to forward to the editor.
    :param require_save: if this is true, then not saving in the editor
                         will make the return value become `None`.
    :param extension: the extension to tell the editor about.  This defaults
                      to `.txt` but changing this might change syntax
                      highlighting.
    :param filename: if provided it will edit this file instead of the
                     provided text contents.  It will not use a temporary
                     file as an indirection in that case.
    """
    from ._termui_impl import Editor
    editor = Editor(editor=editor, env=env, require_save=require_save,
                    extension=extension)
    if filename is None:
        return editor.edit(text)
    editor.edit_file(filename)


def launch(url, wait=False, locate=False):
    """This function launches the given URL (or filename) in the default
    viewer application for this file type.  If this is an executable it
    might launch the executable in a new session.  The return value is
    the exit code of the launched application.  Usually ``0`` indicates
    success.

    Examples::

        click.open('http://click.pocoo.org/')
        click.open('/my/downloaded/file', locate=True)

    .. versionadded:: 2.0

    :param url: url or filename of the thing to launch.
    :param wait: waits for the program to stop.
    :param locate: if this is set to `True` then instead of launching the
                   application associated with the URL it will attempt to
                   launch a file manager with the file located.  This
                   might have weird effects if the url does not point to
                   the filesystem.
    """
    from _termui_impl import open_url
    return open_url(url, wait=wait, locate=locate)

########NEW FILE########
__FILENAME__ = testing
import os
import sys
import click
import shutil
import tempfile
import contextlib

from ._compat import iteritems, PY2


if PY2:
    from cStringIO import StringIO
else:
    import io
    from ._compat import _find_binary_reader


class EchoingStdin(object):

    def __init__(self, input, output):
        self._input = input
        self._output = output

    def __getattr__(self, x):
        return getattr(self._input, x)

    def _echo(self, rv):
        self._output.write(rv)
        return rv

    def read(self, n=-1):
        return self._echo(self._input.read(n))

    def readline(self, n=-1):
        return self._echo(self._input.readline(n))

    def readlines(self):
        return [self._echo(x) for x in self._input.readlines()]

    def __iter__(self):
        return iter(self._echo(x) for x in self._input)

    def __repr__(self):
        return repr(self._input)


def make_input_stream(input, charset):
    # Is already an input stream.
    if hasattr(input, 'read'):
        if PY2:
            return input
        rv = _find_binary_reader(input)
        if rv is not None:
            return rv
        raise TypeError('Could not find binary reader for input stream.')

    if input is None:
        input = b''
    elif not isinstance(input, bytes):
        input = input.encode(charset)
    if PY2:
        return StringIO(input)
    return io.BytesIO(input)


class Result(object):
    """Holds the captured result of an invoked CLI script."""

    def __init__(self, runner, output_bytes, exit_code, exception):
        #: The runner that created the result
        self.runner = runner
        #: The output as bytes.
        self.output_bytes = output_bytes
        #: The exit code as integer.
        self.exit_code = exit_code
        #: The exception that happend if one did.
        self.exception = exception

    @property
    def output(self):
        """The output as unicode string."""
        return self.output_bytes.decode(self.runner.charset, 'replace') \
            .replace('\r\n', '\n')

    def __repr__(self):
        return '<Result %s>' % (
            self.exception and repr(self.exception) or 'okay',
        )


class CliRunner(object):
    """The CLI runner provides functionality to invoke a Click command line
    script for unittesting purposes in a isolated environment.  This only
    works in single-threaded systems without any concurrency as it changes
    global interpreter state.

    :param charset: the character set for the input and output data.  This is
                    utf-8 by default and should not be changed currently as
                    the reporting to click only works on Python 2 properly.
    :param env: a dictionary with environment variables for overriding.
    :param echo_stdin: if this is set to `True`, then reading from stdin writes
                       to stdout.  This is useful for showing examples in
                       some circumstances.  Note that regular prompts
                       will automatically echo the input.
    """

    def __init__(self, charset=None, env=None, echo_stdin=False):
        if charset is None:
            charset = 'utf-8'
        self.charset = charset
        self.env = env or {}
        self.echo_stdin = echo_stdin

    def get_default_prog_name(self, cli):
        """Given a command object it will return the default program name
        for it.  The default is the `name` attribute or ``"root"`` if not
        set.
        """
        return cli.name or 'root'

    def make_env(self, overrides=None):
        """Returns the environment overrides for invoking a script."""
        rv = dict(self.env)
        if overrides:
            rv.update(overrides)
        return rv

    @contextlib.contextmanager
    def isolation(self, input=None, env=None):
        """A context manager that set up the isolation for invoking of a
        command line tool.  This sets up stdin with the given input data,
        and `os.environ` with the overrides from the given dictionary.
        This also rebinds some internals in Click to be mocked (like the
        prompt functionality).

        This is automatically done in the :meth:`invoke` method.

        :param input: the input stream to put into sys.stdin.
        :param env: the environment overrides as dictionary.
        """
        input = make_input_stream(input, self.charset)

        old_stdin = sys.stdin
        old_stdout = sys.stdout
        old_stderr = sys.stderr

        env = self.make_env(env)

        if PY2:
            sys.stdout = sys.stderr = bytes_output = StringIO()
            if self.echo_stdin:
                input = EchoingStdin(input, bytes_output)
        else:
            bytes_output = io.BytesIO()
            if self.echo_stdin:
                input = EchoingStdin(input, bytes_output)
            input = io.TextIOWrapper(input, encoding=self.charset)
            sys.stdout = sys.stderr = io.TextIOWrapper(
                bytes_output, encoding=self.charset)

        sys.stdin = input

        def visible_input(prompt=None):
            sys.stdout.write(prompt or '')
            val = input.readline().rstrip('\r\n')
            sys.stdout.write(val + '\n')
            sys.stdout.flush()
            return val

        def hidden_input(prompt=None):
            sys.stdout.write((prompt or '') + '\n')
            sys.stdout.flush()
            return input.readline().rstrip('\r\n')

        old_visible_prompt_func = click.termui.visible_prompt_func
        old_hidden_prompt_func = click.termui.hidden_prompt_func
        click.termui.visible_prompt_func = visible_input
        click.termui.hidden_prompt_func = hidden_input

        old_env = {}
        try:
            for key, value in iteritems(env):
                old_env[key] = os.environ.get(value)
                if value is None:
                    try:
                        del os.environ[key]
                    except Exception:
                        pass
                else:
                    os.environ[key] = value
            yield bytes_output
        finally:
            for key, value in iteritems(old_env):
                if value is None:
                    try:
                        del os.environ[key]
                    except Exception:
                        pass
                else:
                    os.environ[key] = value
            sys.stdout = old_stdout
            sys.stderr = old_stderr
            sys.stdin = old_stdin
            click.termui.visible_prompt_func = old_visible_prompt_func
            click.termui.hidden_prompt_func = old_hidden_prompt_func

    def invoke(self, cli, args=None, input=None, env=None, **extra):
        """Invokes a command in an isolated environment.  The arguments are
        forwarded directly to the command line script, the `extra` keyword
        arguments are passed to the :meth:`~click.Command.main` function of
        the command.

        This returns a :class:`Result` object.

        :param cli: the command to invoke
        :param args: the arguments to invoke
        :param input: the input data for `sys.stdin`.
        :param env: the environment overrides.
        :param extra: the keyword arguments to pass to :meth:`main`.
        """
        with self.isolation(input=input, env=env) as out:
            exception = None
            exit_code = 0

            try:
                cli.main(args=args or (),
                         prog_name=self.get_default_prog_name(cli), **extra)
            except SystemExit as e:
                if e.code != 0:
                    exception = e
                exit_code = e.code
            except Exception as e:
                exception = e
                exit_code = -1
            sys.stdout.flush()
            output = out.getvalue()

        return Result(runner=self,
                      output_bytes=output,
                      exit_code=exit_code,
                      exception=exception)

    @contextlib.contextmanager
    def isolated_filesystem(self):
        """A context manager that creates a temporary folder and changes
        the current working directory to it for isolated filesystem tests.
        """
        cwd = os.getcwd()
        t = tempfile.mkdtemp()
        os.chdir(t)
        try:
            yield t
        finally:
            os.chdir(cwd)
            try:
                shutil.rmtree(t)
            except (OSError, IOError):
                pass

########NEW FILE########
__FILENAME__ = types
import os
import sys
import stat

from ._compat import open_stream, text_type, filename_to_ui, get_streerror
from .exceptions import BadParameter
from .utils import safecall, LazyFile


class ParamType(object):
    """Helper for converting values through types.  The following is
    necessary for a valid type:

    *   it needs a name
    *   it needs to pass through None unchanged
    *   it needs to convert from a string
    *   it needs to convert its result type through unchanged
        (eg: needs to be idempotent)
    *   it needs to be able to deal with param and context being none.
        This can be the case when the object is used with prompt
        inputs.
    """

    #: the descriptive name of this type
    name = None

    #: if a list of this type is expected and the value is pulled from a
    #: string environment variable, this is what splits it up.  `None`
    #: means any whitespace.  For all parameters the general rule is that
    #: whitespace splits them up.  The exception are paths and files which
    #: are split by ``os.path.pathsep`` by default (":" on unix and ";" on
    #: windows).
    envvar_list_splitter = None

    def __call__(self, value, param=None, ctx=None):
        if value is not None:
            return self.convert(value, param, ctx)

    def get_metavar(self, param):
        """Returns the metavar default for this param if it provides one."""

    def convert(self, param, ctx, value):
        """Converts the value.  This is not invoked for values that are
        `None` (the missing value).
        """
        return value

    def split_envvar_value(self, rv):
        """Given a value from an environment variable this splits it up
        into small chunks depending on the defined envvar list splitter.

        If the splitter is set to `None` which means that whitespace splits,
        then leading and trailing whitespace is ignored.  Otherwise leading
        and trailing splitters usually lead to empty items being included.
        """
        return (rv or '').split(self.envvar_list_splitter)

    def fail(self, message, param=None, ctx=None):
        """Helper method to fail with an invalid value message."""
        raise BadParameter(message, ctx=ctx, param=param)


class FuncParamType(ParamType):

    def __init__(self, func):
        self.name = func.__name__
        self.func = func

    def convert(self, value, param, ctx):
        try:
            return self.func(value)
        except ValueError:
            try:
                value = unicode(value)
            except UnicodeError:
                value = str(value).decode('utf-8', 'replace')
            self.fail(value, param, ctx)


class StringParamType(ParamType):
    name = 'text'

    def convert(self, value, param, ctx):
        if isinstance(value, bytes):
            try:
                enc = getattr(sys.stdin, 'encoding', None)
                if enc is not None:
                    value = value.decode(enc)
            except UnicodeError:
                try:
                    value = value.decode(sys.getfilesystemencoding())
                except UnicodeError:
                    value = value.decode('utf-8', 'replace')
            return value
        return value

    def __repr__(self):
        return 'STRING'


class Choice(ParamType):
    """The choice type allows a value to checked against a fixed set of
    supported values.  All of these values have to be integers.

    See :ref:`choice-opts` for an example.
    """
    name = 'choice'

    def __init__(self, choices):
        self.choices = choices

    def get_metavar(self, param):
        return '[%s]' % '|'.join(self.choices)

    def convert(self, value, param, ctx):
        if value in self.choices:
            return value
        self.fail('invalid choice: %s. (choose from %s)' %
                  (value, ', '.join(self.choices)), param, ctx)

    def __repr__(self):
        return 'Choice(%r)' % list(self.choices)


class IntParamType(ParamType):
    name = 'integer'

    def convert(self, value, param, ctx):
        try:
            return int(value)
        except ValueError:
            self.fail('%s is not a valid integer' % value, param, ctx)

    def __repr__(self):
        return 'INT'


class IntRange(IntParamType):
    """A parameter that works similar to :data:`click.INT` but restricts
    the value to fit into a range.  The default behavior is to fail if the
    value falls outside the range, but it can also be silently clamped
    between the two edges.

    See :ref:`ranges` for an example.
    """
    name = 'integer range'

    def __init__(self, min=None, max=None, clamp=False):
        self.min = min
        self.max = max
        self.clamp = clamp

    def convert(self, value, param, ctx):
        rv = IntParamType.convert(self, value, param, ctx)
        if self.clamp:
            if self.min is not None and rv < self.min:
                return self.min
            if self.max is not None and rv > self.max:
                return self.max
        if self.min is not None and rv < self.min or \
           self.max is not None and rv > self.max:
            if self.min is None:
                self.fail('%s is bigger than the maximum valid value '
                          '%s.' % (rv, self.max), param, ctx)
            elif self.max is None:
                self.fail('%s is smaller than the minimum valid value '
                          '%s.' % (rv, self.min), param, ctx)
            else:
                self.fail('%s is not in the valid range of %s to %s.'
                          % (rv, self.min, self.max), param, ctx)
        return rv

    def __repr__(self):
        return 'IntRange(%r, %r)' % (self.min, self.max)


class BoolParamType(ParamType):
    name = 'boolean'

    def convert(self, value, param, ctx):
        if isinstance(value, bool):
            return bool(value)
        value = value.lower()
        if value in ('true', '1', 'yes', 'y'):
            return True
        elif value in ('false', '0', 'no', 'n'):
            return False
        self.fail('%s is not a valid boolean' % value, param, ctx)

    def __repr__(self):
        return 'BOOL'


class FloatParamType(ParamType):
    name = 'float'

    def convert(self, value, param, ctx):
        try:
            return float(value)
        except ValueError:
            self.fail('%s is not a valid floating point value' %
                      value, param, ctx)

    def __repr__(self):
        return 'FLOAT'


class UUIDParameterType(ParamType):
    name = 'uuid'

    def convert(self, value, param, ctx):
        import uuid
        try:
            return uuid.UUID(value)
        except ValueError:
            self.fail('%s is not a valid UUID value' % value, param, ctx)

    def __repr__(self):
        return 'UUID'


class File(ParamType):
    """Declares a parameter to be a file for reading or writing.  The file
    is automatically closed once the context tears down (after the command
    finished working).

    Files can be opened for reading or writing.  The special value ``-``
    indicates stdin or stdout depending on the mode.

    By default the file is opened for reading text data but it can also be
    opened in binary mode or for writing.  The encoding parameter can be used
    to force a specific encoding.

    The `lazy` flag controls if the file should be opened immediately or
    upon first IO.  The default is to be non lazy for standard input and
    output streams as well as files opened for reading, lazy otherwise.

    Starting with click 2.0 files can also be opened atomically in which
    case all writes go into a separate file in the same folder and upon
    completion the file will be moved over to the original location.  This
    is useful if a file regularly read by other users is modified.

    See :ref:`file-args` for more information.
    """
    name = 'filename'
    envvar_list_splitter = os.path.pathsep

    def __init__(self, mode='r', encoding=None, errors='strict', lazy=None,
                 atomic=False):
        self.mode = mode
        self.encoding = encoding
        self.errors = errors
        self.lazy = lazy
        self.atomic = atomic

    def resolve_lazy_flag(self, value):
        if self.lazy is not None:
            return self.lazy
        if value == '-':
            return False
        elif 'w' in self.mode:
            return True
        return False

    def convert(self, value, param, ctx):
        try:
            if hasattr(value, 'read') or hasattr(value, 'write'):
                return value

            lazy = self.resolve_lazy_flag(value)

            if lazy:
                f = LazyFile(value, self.mode, self.encoding, self.errors,
                             atomic=self.atomic)
                if ctx is not None:
                    ctx.call_on_close(f.close_intelligently)
                return f

            f, should_close = open_stream(value, self.mode,
                                          self.encoding, self.errors,
                                          atomic=self.atomic)
            # If a context is provided we automatically close the file
            # at the end of the context execution (or flush out).  If a
            # context does not exist it's the caller's responsibility to
            # properly close the file.  This for instance happens when the
            # type is used with prompts.
            if ctx is not None:
                if should_close:
                    ctx.call_on_close(safecall(f.close))
                else:
                    ctx.call_on_close(safecall(f.flush))
            return f
        except (IOError, OSError) as e:
            self.fail('Could not open file: %s: %s' % (
                filename_to_ui(value),
                get_streerror(e),
            ), param, ctx)


class Path(ParamType):
    """The path type is similar to the :class:`File` type but it performs
    different checks.  First of all, instead of returning a open file
    handle it returns just the filename.  Secondly it can perform various
    basic checks about what the file or directory should be.

    :param exists: if set to true, the file or directory needs to exist for
                   this value to be valid.  If this is not required and a
                   file does indeed not exist, then all further checks are
                   silently skipped.
    :param file_okay: controls if a file is a possible value.
    :param dir_okay: controls if a directory is a possible value.
    :param writable: if true, a writable check is performed.
    :param readable: if true, a readable check is performed.
    :param resolve_path: if this is true, then the path is fully resolved
                         before the value is passed onwards.  This means
                         that it's absolute and symlinks are resolved.
    """
    envvar_list_splitter = os.path.pathsep

    def __init__(self, exists=False, file_okay=True, dir_okay=True,
                 writable=False, readable=True, resolve_path=False):
        self.exists = exists
        self.file_okay = file_okay
        self.dir_okay = dir_okay
        self.writable = writable
        self.readable = readable
        self.resolve_path = resolve_path

        if self.file_okay and not self.dir_okay:
            self.name = 'file'
            self.path_type = 'File'
        if self.dir_okay and not self.file_okay:
            self.name = 'directory'
            self.path_type = 'Directory'
        else:
            self.name = 'path'
            self.path_type = 'Path'

    def convert(self, value, param, ctx):
        rv = value
        if self.resolve_path:
            rv = os.path.realpath(rv)

        try:
            st = os.stat(rv)
        except OSError:
            if not self.exists:
                return rv
            self.fail('%s "%s" does not exist.' % (
                self.path_type,
                filename_to_ui(value)
            ), param, ctx)

        if not self.file_okay and stat.S_ISREG(st.st_mode):
            self.fail('%s "%s" is a file.' % (
                self.path_type,
                filename_to_ui(value)
            ), param, ctx)
        if not self.dir_okay and stat.S_ISDIR(st.st_mode):
            self.fail('%s "%s" is a directory.' % (
                self.path_type,
                filename_to_ui(value)
            ), param, ctx)
        if self.writable and not os.access(value, os.W_OK):
            self.fail('%s "%s" is not writable.' % (
                self.path_type,
                filename_to_ui(value)
            ), param, ctx)
        if self.readable and not os.access(value, os.R_OK):
            self.fail('%s "%s" is not readable.' % (
                self.path_type,
                filename_to_ui(value)
            ), param, ctx)

        return rv


def convert_type(ty, default=None):
    """Converts a callable or python ty into the most appropriate param
    ty.
    """
    if isinstance(ty, ParamType):
        return ty
    guessed_type = False
    if ty is None and default is not None:
        ty = type(default)
        guessed_type = True
    if ty is text_type or ty is str or ty is None:
        return STRING
    if ty is int:
        return INT
    # Booleans are only okay if not guessed.  This is done because for
    # flags the default value is actually a bit of a lie in that it
    # indicates which of the flags is the one we want.  See get_default()
    # for more information.
    if ty is bool and not guessed_type:
        return BOOL
    if ty is float:
        return FLOAT
    if guessed_type:
        return STRING

    # Catch a common mistake
    if __debug__:
        try:
            if issubclass(ty, ParamType):
                raise AssertionError('Attempted to use an uninstantiated '
                                     'parameter type (%s).' % ty)
        except TypeError:
            pass
    return FuncParamType(ty)


#: A unicode string parameter type which is the implicit default.  This
#: can also be selected by using ``str`` as type.
STRING = StringParamType()

#: An integer parameter.  This can also be selected by using ``int`` as
#: type.
INT = IntParamType()

#: A floating point value parameter.  This can also be selected by using
#: ``float`` as type.
FLOAT = FloatParamType()

#: A boolean parameter.  This is the default for boolean flags.  This can
#: also be selected by using ``bool`` as a type.
BOOL = BoolParamType()

#: A UUID parameter.
UUID = UUIDParameterType()

########NEW FILE########
__FILENAME__ = utils
import os
import sys
from collections import deque

from ._compat import text_type, open_stream, get_streerror, string_types, \
     PY2, binary_streams, text_streams, filename_to_ui, \
     auto_wrap_for_ansi, strip_ansi, isatty, _default_text_stdout, \
     is_bytes

if not PY2:
    from ._compat import _find_binary_writer


echo_native_types = string_types + (bytes, bytearray)


def _posixify(name):
    return '-'.join(name.split()).lower()


def unpack_args(args, nargs_spec):
    """Given an iterable of arguments and an iterable of nargs specifications
    it returns a tuple with all the unpacked arguments at the first index
    and all remaining arguments as the second.

    The nargs specification is the number of arguments that should be consumed
    or `-1` to indicate that this position should eat up all the remainders.

    Missing items are filled with `None`.

    Examples:

    >>> unpack_args(range(6), [1, 2, 1, -1])
    ((0, (1, 2), 3, (4, 5)), [])
    >>> unpack_args(range(6), [1, 2, 1])
    ((0, (1, 2), 3), [4, 5])
    >>> unpack_args(range(6), [-1])
    (((0, 1, 2, 3, 4, 5),), [])
    >>> unpack_args(range(6), [1, 1])
    ((0, 1), [2, 3, 4, 5])
    """
    args = deque(args)
    nargs_spec = deque(nargs_spec)
    rv = []
    spos = None

    def _fetch(c):
        try:
            return (spos is not None and c.pop() or c.popleft())
        except IndexError:
            return None

    while nargs_spec:
        nargs = _fetch(nargs_spec)
        if nargs == 1:
            rv.append(_fetch(args))
        elif nargs > 1:
            x = [_fetch(args) for _ in range(nargs)]
            # If we're reversed we're pulling in the arguments in reverse
            # so we need to turn them around.
            if spos is not None:
                x.reverse()
            rv.append(tuple(x))
        elif nargs < 0:
            if spos is not None:
                raise TypeError('Cannot have two nargs < 0')
            spos = len(rv)
            rv.append(None)

    # spos is the position of the wildcard (star).  If it's not None
    # we fill it with the remainder.
    if spos is not None:
        rv[spos] = tuple(args)
        args = []

    return rv, list(args)


def safecall(func):
    """Wraps a function so that it swallows exceptions."""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception:
            pass
    return wrapper


def make_str(value):
    """Converts a value into a valid string."""
    if isinstance(value, bytes):
        try:
            return value.decode(sys.getfilesystemencoding())
        except UnicodeError:
            return value.decode('utf-8', 'replace')
    return text_type(value)


def make_default_short_help(help, max_length=45):
    words = help.split()
    total_length = 0
    result = []
    done = False

    for word in words:
        if '.' in word:
            word = word.split('.', 1)[0] + '.'
            done = True
        new_length = result and 1 + len(word) or len(word)
        if total_length + new_length > max_length:
            result.append('...')
            done = True
        else:
            if result:
                result.append(' ')
            result.append(word)
        if done:
            break
        total_length += new_length

    return ''.join(result)


class LazyFile(object):
    """A lazy file works like a regular file but it does not fully open
    the file but it does perform some basic checks early to see if the
    filename parameter does make sense.  This is useful for safely opening
    files for writing.
    """

    def __init__(self, filename, mode='r', encoding=None, errors='strict',
                 atomic=False):
        self.name = filename
        self.mode = mode
        self.encoding = encoding
        self.errors = errors
        self.atomic = atomic

        if filename == '-':
            self._f, self.should_close = open_stream(filename, mode,
                                                     encoding, errors)
        else:
            if 'r' in mode:
                # Open and close the file in case we're opening it for
                # reading so that we can catch at least some errors in
                # some cases early.
                open(filename, mode).close()
            self._f = None
            self.should_close = True

    def __getattr__(self, name):
        return getattr(self.open(), name)

    def __repr__(self):
        if self._f is not None:
            return repr(self._f)
        return '<unopened file %r %s>' % (self.name, self.mode)

    def open(self):
        """Opens the file if it's not yet open.  This call might fail with
        a :exc:`FileError`.  Not handling this error will produce an error
        that click shows.
        """
        if self._f is not None:
            return self._f
        try:
            rv, self.should_close = open_stream(self.name, self.mode,
                                                self.encoding,
                                                self.errors,
                                                atomic=self.atomic)
        except (IOError, OSError) as e:
            from .exceptions import FileError
            raise FileError(self.name, hint=get_streerror(e))
        self._f = rv
        return rv

    def close(self):
        """Closes the underlying file, no matter what."""
        if self._f is not None:
            self._f.close()

    def close_intelligently(self):
        """This function only closes the file if it was opened by the lazy
        file wrapper.  For instance this will never close stdin.
        """
        if self.should_close:
            self.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, tb):
        self.close_intelligently()


def echo(message=None, file=None, nl=True):
    """Prints a message plus a newline to the given file or stdout.  On
    first sight this looks like the print function but it has improved
    support for handling unicode and binary data that does not fail no
    matter how badly configured the system is.

    Primarily it means that you can print binary data as well as unicode
    data on both 2.x and 3.x to the given file in the most appropriate way
    possible.  This is a very carefree function as in that it will try its
    best to not fail.

    In addition to that if `colorama`_ is installed the echo function will
    also support clever handling of ANSI codes.  Essentially it will then
    do the following:

    -   add transparent handling of ANSI color codes on Windows.
    -   hide ANSI codes automatically if the destination file is not a
        terminal.

    .. _colorama: http://pypi.python.org/pypi/colorama

    .. versionchanged:: 2.0
       Starting with version 2.0 of click, the echo function will work
       with colorama if it's installed.

    :param message: the message to print
    :param file: the file to write to (defaults to ``stdout``)
    :param nl: if set to `True` (the default) a newline is printed afterwards.
    """
    if file is None:
        file = _default_text_stdout()

    # Convert non bytes/text into the native string type.
    if message is not None and not isinstance(message, echo_native_types):
        message = text_type(message)

    # If there is a message, and we're on python 3, and the value looks
    # like bytes we manually need to find the binary stream and write the
    # message in there.  This is done separately so that most stream
    # types will work as you would expect.  Eg: you can write to StringIO
    # for other cases.
    if message and not PY2 and is_bytes(message):
        binary_file = _find_binary_writer(file)
        if binary_file is not None:
            file.flush()
            binary_file.write(message)
            if nl:
                binary_file.write(b'\n')
            binary_file.flush()
            return

    # ANSI style support.  If there is no message or we are dealing with
    # bytes nothing is happening.  If we are connected to a file we want
    # to strip colors.  If we have support for wrapping streams (windows
    # through colorama) we want to do that.
    if message and not is_bytes(message):
        if not isatty(file):
            message = strip_ansi(message)
        elif auto_wrap_for_ansi is not None:
            file = auto_wrap_for_ansi(file)

    if message:
        file.write(message)
    if nl:
        file.write('\n')
    file.flush()


def get_binary_stream(name):
    """Returns a system stream for byte processing.  This essentially
    returns the stream from the sys module with the given name but it
    solves some compatibility issues between different Python versions.
    Primarily this function is necessary for getting binary streams on
    Python 3.

    :param name: the name of the stream to open.  Valid names are ``'stdin'``,
                 ``'stdout'`` and ``'stderr'``
    """
    opener = binary_streams.get(name)
    if opener is None:
        raise TypeError('Unknown standard stream %r' % name)
    return opener()


def get_text_stream(name, encoding=None, errors='strict'):
    """Returns a system stream for text processing.  This usually returns
    a wrapped stream around a binary stream returned from
    :func:`get_binary_stream` but it also can take shortcuts on Python 3
    for already correctly configured streams.

    :param name: the name of the stream to open.  Valid names are ``'stdin'``,
                 ``'stdout'`` and ``'stderr'``
    :param encoding: overrides the detected default encoding.
    :param errors: overrides the default error mode.
    """
    opener = text_streams.get(name)
    if opener is None:
        raise TypeError('Unknown standard stream %r' % name)
    return opener(encoding, errors)


def format_filename(filename, shorten=False):
    """Formats a filename for user display.  The main purpose of this
    function is to ensure that the filename can be displayed at all.  This
    will decode the filename to unicode if necessary in a way that it will
    not fail.  Optionally it can shorten the filename to not include the
    full path to the filename.

    :param filename: formats a filename for UI display.  This will also convert
                     the filename into unicode without failing.
    :param shorten: this optionally shortens the filename to strip of the
                    path that leads up to it.
    """
    if shorten:
        filename = os.path.basename(filename)
    return filename_to_ui(filename)


def get_app_dir(app_name, roaming=True, force_posix=False):
    r"""Returns the config folder for the application.  The default behavior
    is to return whatever is most appropriate for the operating system.

    To give you an idea, for an app called ``"Foo Bar"`` something like
    the following folders could be returned:

    Mac OS X:
      ``~/Library/Application Support/Foo Bar``
    Mac OS X (posix):
      ``~/.foo-bar``
    Unix:
      ``~/.config/foo-bar``
    Unix (posix):
      ``~/.foo-bar``
    Win XP (roaming):
      ``C:\Documents and Settings\<user>\Local Settings\Application Data\Foo Bar``
    Win XP (not roaming):
      ``C:\Documents and Settings\<user>\Application Data\Foo Bar``
    Win 7 (roaming):
      ``C:\Users\<user>\AppData\Roaming\Foo Bar``
    Win 7 (not roaming):
      ``C:\Users\<user>\AppData\Local\Foo Bar``

    .. versionadded:: 2.0

    :param app_name: the application name.  This should be properly capitalized
                     and can contain whitespace.
    :param roaming: controls if the folder should be roaming or not on windows.
                    Has no affect otherwise.
    :param force_posix: if this is set to `True` then on any posix system the
                        folder will be stored in the home folder with a leading
                        dot instead of the XDG config home or darwin's
                        application support folder.
    """
    if sys.platform.startswith('win'):
        key = roaming and 'APPDATA' or 'LOCALAPPDATA'
        folder = os.environ.get(key)
        if folder is None:
            folder = os.path.expanduser('~')
        return os.path.join(folder, app_name)
    if force_posix:
        return os.path.join(os.path.expanduser('~/.' + _posixify(app_name)))
    if sys.platform == 'darwin':
        return os.path.join(os.path.expanduser(
            '~/Library/Application Support'), app_name)
    return os.path.join(
        os.environ.get('XDG_CONFIG_HOME', os.path.expanduser('~/.config')),
        _posixify(app_name))

########NEW FILE########
__FILENAME__ = _compat
import re
import io
import os
import sys
import codecs
import tempfile
from weakref import WeakKeyDictionary


PY2 = sys.version_info[0] == 2


_ansi_re = re.compile('\033\[((?:\d|;)*)([a-zA-Z])')


def _make_text_stream(stream, encoding, errors):
    if encoding is None:
        encoding = get_best_encoding(stream)
    if errors is None:
        errors = 'replace'
    return _NonClosingTextIOWrapper(stream, encoding, errors,
                                    line_buffering=True)


def is_ascii_encoding(encoding):
    """Checks if a given encoding is ascii."""
    try:
        return codecs.lookup(encoding).name == 'ascii'
    except LookupError:
        return False


def get_best_encoding(stream):
    """Returns the default stream encoding if not found."""
    rv = getattr(stream, 'encoding', None) or sys.getdefaultencoding()
    if is_ascii_encoding(rv):
        return 'utf-8'
    return rv


class _NonClosingTextIOWrapper(io.TextIOWrapper):

    def __init__(self, stream, encoding, errors, **extra):
        io.TextIOWrapper.__init__(self, _FixupStream(stream),
                                  encoding, errors, **extra)

    # The io module is already a place where Python 2 got the
    # python 3 text behavior forced on, so we need to unbreak
    # it to look like python 2 stuff.
    if PY2:
        def write(self, x):
            if isinstance(x, str) or is_bytes(x):
                self.flush()
                return self.buffer.write(str(x))
            return io.TextIOWrapper.write(self, x)

        def writelines(self, lines):
            for line in lines:
                self.write(line)

    def __del__(self):
        try:
            self.detach()
        except Exception:
            pass


class _FixupStream(object):
    """The new io interface needs more from streams than streams
    traditionally implement.  As such this fixup stuff is necessary in
    some circumstances.
    """

    def __init__(self, stream):
        self._stream = stream

    def __getattr__(self, name):
        return getattr(self._stream, name)

    def read1(self, size):
        f = getattr(self._stream, 'read1', None)
        if f is not None:
            return f(size)
        return self._stream.read(size)

    def readable(self):
        x = getattr(self._stream, 'readable', None)
        if x is not None:
            return x
        try:
            self._stream.read(0)
        except Exception:
            return False
        return True

    def writable(self):
        x = getattr(self._stream, 'writable', None)
        if x is not None:
            return x
        try:
            self._stream.write('')
        except Exception:
            try:
                self._stream.write(b'')
            except Exception:
                return False
        return True

    def seekable(self):
        x = getattr(self._stream, 'seekable', None)
        if x is not None:
            return x
        try:
            self._stream.seek(self._stream.tell())
        except Exception:
            return False
        return True


if PY2:
    text_type = unicode
    bytes = str
    raw_input = raw_input
    string_types = (str, unicode)
    iteritems = lambda x: x.iteritems()
    range_type = xrange

    def is_bytes(x):
        return isinstance(x, (buffer, bytearray))

    _identifier_re = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')

    # For Windows we need to force stdout/stdin/stderr to binary if it's
    # fetched for that.  This obviously is not the most correct way to do
    # it as it changes global state.  Unfortunately there does not seem to
    # be a clear better way to do it as just reopening the file in binary
    # mode does not change anything.
    #
    # An option would be to do what python 3 does and to open the file as
    # binary only, patch it back to the system and then use a wrapper
    # stream that converts newlines.  It's not quite clear what's the
    # correct option here.
    if sys.platform == 'win32':
        import msvcrt
        def set_binary_mode(f):
            try:
                fileno = f.fileno()
            except Exception:
                pass
            else:
                msvcrt.setmode(fileno, os.O_BINARY)
            return f
    else:
        set_binary_mode = lambda x: x

    def isidentifier(x):
        return _identifier_re.search(x) is not None

    def get_binary_stdin():
        return set_binary_mode(sys.stdin)

    def get_binary_stdout():
        return set_binary_mode(sys.stdout)

    def get_binary_stderr():
        return set_binary_mode(sys.stderr)

    def get_text_stdin(encoding=None, errors=None):
        return _make_text_stream(sys.stdin, encoding, errors)

    def get_text_stdout(encoding=None, errors=None):
        return _make_text_stream(sys.stdout, encoding, errors)

    def get_text_stderr(encoding=None, errors=None):
        return _make_text_stream(sys.stderr, encoding, errors)

    def filename_to_ui(value):
        if isinstance(value, bytes):
            value = value.decode(sys.getfilesystemencoding(), 'replace')
        return value
else:
    import io
    text_type = str
    raw_input = input
    string_types = (str,)
    range_type = range
    isidentifier = lambda x: x.isidentifier()
    iteritems = lambda x: iter(x.items())

    def is_bytes(x):
        return isinstance(x, (bytes, memoryview, bytearray))

    def _is_binary_reader(stream, default=False):
        try:
            return isinstance(stream.read(0), bytes)
        except Exception:
            return default
            # This happens in some cases where the stream was already
            # closed.  In this case we assume the defalt.

    def _is_binary_writer(stream, default=False):
        try:
            stream.write(b'')
        except Exception:
            try:
                stream.write('')
                return False
            except Exception:
                pass
            return default
        return True

    def _find_binary_reader(stream):
        # We need to figure out if the given stream is already binary.
        # This can happen because the official docs recommend detatching
        # the streams to get binary streams.  Some code might do this, so
        # we need to deal with this case explicitly.
        is_binary = _is_binary_reader(stream, False)

        if is_binary:
            return stream

        buf = getattr(stream, 'buffer', None)
        # Same situation here, this time we assume that the buffer is
        # actually binary in case it's closed.
        if buf is not None and _is_binary_reader(buf, True):
            return buf

    def _find_binary_writer(stream):
        # We need to figure out if the given stream is already binary.
        # This can happen because the official docs recommend detatching
        # the streams to get binary streams.  Some code might do this, so
        # we need to deal with this case explicitly.
        if _is_binary_writer(stream, False):
            return stream

        buf = getattr(stream, 'buffer', None)

        # Same situation here, this time we assume that the buffer is
        # actually binary in case it's closed.
        if buf is not None and _is_binary_writer(buf, True):
            return buf

    def _stream_is_misconfigured(stream):
        """A stream is misconfigured if it's encoding is ASCII."""
        return is_ascii_encoding(getattr(stream, 'encoding', None))

    def _is_compatible_text_stream(stream, encoding, errors):
        stream_encoding = getattr(stream, 'encoding', None)
        stream_errors = getattr(stream, 'errors', None)

        # Perfect match.
        if stream_encoding == encoding and stream_errors == errors:
            return True

        # Otherwise it's only a compatible stream if we did not ask for
        # an encoding.
        if encoding is None:
            return stream_encoding is not None

        return False

    def _force_correct_text_reader(text_reader, encoding, errors):
        if _is_binary_reader(text_reader, False):
            binary_reader = text_reader
        else:
            # If there is no target encoding set we need to verify that the
            # reader is actually not misconfigured.
            if encoding is None and not _stream_is_misconfigured(text_reader):
                return text_reader

            if _is_compatible_text_stream(text_reader, encoding, errors):
                return text_reader

            # If the reader has no encoding we try to find the underlying
            # binary reader for it.  If that fails because the environment is
            # misconfigured, we silently go with the same reader because this
            # is too common to happen.  In that case mojibake is better than
            # exceptions.
            binary_reader = _find_binary_reader(text_reader)
            if binary_reader is None:
                return text_reader

        # At this point we default the errors to replace instead of strict
        # because nobody handles those errors anyways and at this point
        # we're so fundamentally fucked that nothing can repair it.
        if errors is None:
            errors = 'replace'
        return _make_text_stream(binary_reader, encoding, errors)

    def _force_correct_text_writer(text_writer, encoding, errors):
        if _is_binary_writer(text_writer, False):
            binary_writer = text_writer
        else:
            # If there is no target encoding set we need to verify that the
            # writer is actually not misconfigured.
            if encoding is None and not _stream_is_misconfigured(text_writer):
                return text_writer

            if _is_compatible_text_stream(text_writer, encoding, errors):
                return text_writer

            # If the writer has no encoding we try to find the underlying
            # binary writer for it.  If that fails because the environment is
            # misconfigured, we silently go with the same writer because this
            # is too common to happen.  In that case mojibake is better than
            # exceptions.
            binary_writer = _find_binary_writer(text_writer)
            if binary_writer is None:
                return text_writer

        # At this point we default the errors to replace instead of strict
        # because nobody handles those errors anyways and at this point
        # we're so fundamentally fucked that nothing can repair it.
        if errors is None:
            errors = 'replace'
        return _make_text_stream(binary_writer, encoding, errors)

    def get_binary_stdin():
        reader = _find_binary_reader(sys.stdin)
        if reader is None:
            raise RuntimeError('Was not able to determine binary '
                               'stream for sys.stdin.')
        return reader

    def get_binary_stdout():
        writer = _find_binary_writer(sys.stdout)
        if writer is None:
            raise RuntimeError('Was not able to determine binary '
                               'stream for sys.stdout.')
        return writer

    def get_binary_stderr():
        writer = _find_binary_writer(sys.stderr)
        if writer is None:
            raise RuntimeError('Was not able to determine binary '
                               'stream for sys.stderr.')
        return writer

    def get_text_stdin(encoding=None, errors=None):
        return _force_correct_text_reader(sys.stdin, encoding, errors)

    def get_text_stdout(encoding=None, errors=None):
        return _force_correct_text_writer(sys.stdout, encoding, errors)

    def get_text_stderr(encoding=None, errors=None):
        return _force_correct_text_writer(sys.stderr, encoding, errors)

    def filename_to_ui(value):
        if isinstance(value, bytes):
            value = value.decode(sys.getfilesystemencoding(), 'replace')
        else:
            value = value.encode('utf-8', 'surrogateescape') \
                .decode('utf-8', 'replace')
        return value


def get_streerror(e, default=None):
    if hasattr(e, 'strerror'):
        msg = e.strerror
    else:
        if default is not None:
            msg = default
        else:
            msg = str(e)
    if isinstance(msg, bytes):
        msg = msg.decode('utf-8', 'replace')
    return msg


def open_stream(filename, mode='r', encoding=None, errors='strict',
                atomic=False):
    # standard streams first.  These are simple because they don't need
    # special handling for the atomic flag.  It's entirely ignored.
    if filename == '-':
        if 'w' in mode:
            if 'b' in mode:
                return get_binary_stdout(), False
            return get_text_stdout(encoding=encoding, errors=errors), False
        if 'b' in mode:
            return get_binary_stdin(), False
        return get_text_stdin(encoding=encoding, errors=errors), False

    # Non-atomic writes directly go out through the regular open
    # functions.
    if not atomic:
        if encoding is None:
            return open(filename, mode), True
        return io.open(filename, mode, encoding=encoding, errors=errors), True

    # Atomic writes are more complicated.  They work by opening a file
    # as a proxy in the same folder and then using the fdopen
    # functionality to wrap it in a python file.  Then we wrap it in an
    # atomic file that moves the file over on close.
    fd, tmp_filename = tempfile.mkstemp(dir=os.path.dirname(filename),
                                        prefix='.__atomic-write')

    if encoding is not None:
        f = io.open(fd, mode, encoding=encoding, errors=errors)
    else:
        f = os.fdopen(fd, mode)

    return _AtomicFile(f, tmp_filename, filename), True


# Used in a destructor call, needs extra protection from interpreter
# cleanup.
_rename = os.rename


class _AtomicFile(object):

    def __init__(self, f, tmp_filename, real_filename):
        self._f = f
        self._tmp_filename = tmp_filename
        self._real_filename = real_filename
        self.closed = False

    @property
    def name(self):
        return self._real_filename

    def close(self, delete=False):
        if self.closed:
            return
        self._f.close()
        _rename(self._tmp_filename, self._real_filename)
        self.closed = True

    def __getattr__(self, name):
        return getattr(self._f, name)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, tb):
        self.close(delete=exc_type is not None)

    def __repr__(self):
        return repr(self._f)


auto_wrap_for_ansi = None
colorama = None


# If we're on windows we provide transparent integration through
# colorama.  This will make ansi colors through the echo function
# work automatically.
if sys.platform.startswith('win'):
    try:
        import colorama
    except ImportError:
        pass
    else:
        _ansi_stream_wrappers = WeakKeyDictionary()

        def auto_wrap_for_ansi(stream):
            try:
                cached = _ansi_stream_wrappers.get(stream)
            except Exception:
                cached = None
            if cached is not None:
                return cached
            strip = not isatty(stream)
            rv = colorama.AnsiToWin32(stream, strip=strip).stream
            try:
                _ansi_stream_wrappers[stream] = rv
            except Exception:
                pass
            return rv


def strip_ansi(value):
    return _ansi_re.sub('', value)


def isatty(stream):
    try:
        return stream.isatty()
    except Exception:
        return False


_default_text_cache = WeakKeyDictionary()


def _default_text_stdout():
    """Like :func:`get_text_stdout` but uses a cache if available to speed
    it up.  This will not create streams over and over again.
    """
    stream = sys.stdout
    try:
        rv = _default_text_cache.get(stream)
    except Exception:
        rv = None
    if rv is not None:
        return rv
    rv = get_text_stdout()
    try:
        _default_text_cache[stream] = rv
    except Exception:
        pass
    return rv


binary_streams = {
    'stdin': get_binary_stdin,
    'stdout': get_binary_stdout,
    'stderr': get_binary_stderr,
}

text_streams = {
    'stdin': get_text_stdin,
    'stdout': get_text_stdout,
    'stderr': get_text_stderr,
}

########NEW FILE########
__FILENAME__ = _termui_impl
"""
    click._termui_impl
    ~~~~~~~~~~~~~~~~~~

    This module contains implementations for the termui module.  To keep the
    import time of click down some infrequently used functionality is placed
    in this module and only imported as needed.

    :copyright: (c) 2014 by Armin Ronacher.
    :license: BSD, see LICENSE for more details.
"""
import os
import sys
import time
import math
from ._compat import _default_text_stdout, range_type, PY2, isatty, \
     open_stream, strip_ansi
from .utils import echo
from .exceptions import ClickException


if os.name == 'nt':
    BEFORE_BAR = '\r'
    AFTER_BAR = '\n'
else:
    BEFORE_BAR = '\r\033[?25l'
    AFTER_BAR = '\033[?25h\n'


def _length_hint(obj):
    """Returns the length hint of an object."""
    try:
        return len(obj)
    except TypeError:
        try:
            get_hint = type(obj).__length_hint__
        except AttributeError:
            return None
        try:
            hint = get_hint(obj)
        except TypeError:
            return None
        if hint is NotImplemented or \
           not isinstance(hint, (int, long)) or \
           hint < 0:
            return None
        return hint


class ProgressBar(object):

    def __init__(self, iterable, length=None, fill_char='#', empty_char=' ',
                 bar_template='%(bar)s', info_sep='  ', show_eta=True,
                 show_percent=None, show_pos=False, item_show_func=None,
                 label=None, file=None, width=30):
        self.fill_char = fill_char
        self.empty_char = empty_char
        self.bar_template = bar_template
        self.info_sep = info_sep
        self.show_eta = show_eta
        self.show_percent = show_percent
        self.show_pos = show_pos
        self.item_show_func = item_show_func
        self.label = label or ''
        if file is None:
            file = _default_text_stdout()
        self.file = file
        self.width = width

        if length is None:
            length = _length_hint(iterable)
        if iterable is None:
            if length is None:
                raise TypeError('iterable or length is required')
            iterable = range_type(length)
        self.iter = iter(iterable)
        self.length = length
        self.length_known = length is not None
        self.pos = 0
        self.avg = []
        self.start = self.last_eta = time.time()
        self.eta_known = False
        self.finished = False
        self.max_width = None
        self.entered = False
        self.current_item = None

        try:
            self.is_hidden = not self.file.isatty()
        except Exception:
            self.is_hidden = True

    def __enter__(self):
        self.entered = True
        return self

    def __exit__(self, exc_type, exc_value, tb):
        self.render_finish()

    def __iter__(self):
        if not self.entered:
            raise RuntimeError('You need to use progress bars in a with block.')
        self.render_progress()
        return self

    def render_finish(self):
        if self.is_hidden:
            return
        self.file.write(AFTER_BAR)
        self.file.flush()

    @property
    def pct(self):
        if self.finished:
            return 1.0
        return min(self.pos / (float(self.length) or 1), 1.0)

    @property
    def time_per_iteration(self):
        if not self.avg:
            return 0.0
        return sum(self.avg) / float(len(self.avg))

    @property
    def eta(self):
        if self.length_known and not self.finished:
            return self.time_per_iteration * (self.length - self.pos)
        return 0.0

    def format_eta(self):
        if self.eta_known:
            return time.strftime('%H:%M:%S', time.gmtime(self.eta + 1))
        return ''

    def format_pos(self):
        pos = str(self.pos)
        if self.length_known:
            pos += '/%s' % self.length
        return pos

    def format_pct(self):
        return ('% 4d%%' % int(self.pct * 100))[1:]

    def format_progress_line(self):
        show_percent = self.show_percent

        info_bits = []
        if self.length_known:
            bar_length = int(self.pct * self.width)
            bar = self.fill_char * bar_length
            bar += self.empty_char * (self.width - bar_length)
            if show_percent is None:
                show_percent = not self.show_pos
        else:
            if self.finished:
                bar = self.fill_char * self.width
            else:
                bar = list(self.empty_char * self.width)
                if self.time_per_iteration != 0:
                    bar[int((math.cos(self.pos * self.time_per_iteration)
                        / 2.0 + 0.5) * self.width)] = self.fill_char
                bar = ''.join(bar)

        if self.show_pos:
            info_bits.append(self.format_pos())
        if show_percent:
            info_bits.append(self.format_pct())
        if self.show_eta and self.eta_known and not self.finished:
            info_bits.append(self.format_eta())
        if self.item_show_func is not None:
            item_info = self.item_show_func(self.current_item)
            if item_info is not None:
                info_bits.append(item_info)

        return (self.bar_template % {
            'label': self.label,
            'bar': bar,
            'info': self.info_sep.join(info_bits)
        }).strip()

    def render_progress(self):
        if self.is_hidden:
            echo(self.label, file=self.file)
            self.file.flush()
            return

        clear_width = self.width
        if self.max_width is not None:
            clear_width = self.max_width
        self.file.write(BEFORE_BAR)
        line = self.format_progress_line()
        line_len = len(strip_ansi(line))
        if self.max_width is None or self.max_width < line_len:
            self.max_width = line_len
        # Use echo here so that we get colorama support.
        echo(line, file=self.file, nl=False)
        self.file.write(' ' * (clear_width - line_len))
        self.file.flush()

    def make_step(self):
        self.pos += 1
        if self.length_known and self.pos >= self.length:
            self.finished = True

        if (time.time() - self.last_eta) < 1.0:
            return

        self.last_eta = time.time()
        self.avg = self.avg[-6:] + [-(self.start - time.time()) / (self.pos)]

        self.eta_known = self.length_known

    def finish(self):
        self.eta_known = 0
        self.current_item = None
        self.finished = True

    def next(self):
        if self.is_hidden:
            return next(self.iter)
        try:
            rv = next(self.iter)
            self.current_item = rv
        except StopIteration:
            self.finish()
            self.render_progress()
            raise StopIteration()
        else:
            self.make_step()
            self.render_progress()
            return rv

    if not PY2:
        __next__ = next
        del next


def pager(text):
    """Decide what method to use for paging through text."""
    stdout = _default_text_stdout()
    if not isatty(sys.stdin) or not isatty(stdout):
        return _nullpager(stdout, text)
    if 'PAGER' in os.environ:
        if sys.platform == 'win32':
            return _tempfilepager(strip_ansi(text), os.environ['PAGER'])
        elif os.environ.get('TERM') in ('dumb', 'emacs'):
            return _pipepager(strip_ansi(text), os.environ['PAGER'])
        else:
            return _pipepager(text, os.environ['PAGER'])
    if os.environ.get('TERM') in ('dumb', 'emacs'):
        return _nullpager(stdout, text)
    if sys.platform == 'win32' or sys.platform.startswith('os2'):
        return _tempfilepager(strip_ansi(text), 'more <')
    if hasattr(os, 'system') and os.system('(less) 2>/dev/null') == 0:
        return _pipepager(text, 'less')

    import tempfile
    fd, filename = tempfile.mkstemp()
    os.close(fd)
    try:
        if hasattr(os, 'system') and os.system('more "%s"' % filename) == 0:
            return _pipepager(text, 'more')
        return _nullpager(stdout, text)
    finally:
        os.unlink(filename)


def _pipepager(text, cmd):
    """Page through text by feeding it to another program."""
    pipe = os.popen(cmd, 'w')
    try:
        pipe.write(text)
        pipe.close()
    except IOError:
        pass


def _tempfilepager(text, cmd):
    """Page through text by invoking a program on a temporary file."""
    import tempfile
    filename = tempfile.mktemp()
    with open_stream(filename, 'w')[1] as f:
        f.write(text)
    try:
        os.system(cmd + ' "' + filename + '"')
    finally:
        os.unlink(filename)


def _nullpager(stream, text):
    """Simply print unformatted text.  This is the ultimate fallback."""
    stream.write(strip_ansi(text))


class Editor(object):

    def __init__(self, editor=None, env=None, require_save=True,
                 extension='.txt'):
        self.editor = editor
        self.env = env
        self.require_save = require_save
        self.extension = extension

    def get_editor(self):
        if self.editor is not None:
            return self.editor
        for key in 'VISUAL', 'EDITOR':
            rv = os.environ.get(key)
            if rv:
                return rv
        if sys.platform.startswith('win'):
            return 'notepad'
        for editor in 'vim', 'nano':
            if os.system('which %s &> /dev/null' % editor) == 0:
                return editor
        return 'vi'

    def edit_file(self, filename):
        import subprocess
        editor = self.get_editor()
        if self.env:
            environ = os.environ.copy()
            environ.update(self.env)
        else:
            environ = None
        try:
            c = subprocess.Popen([editor, filename], env=environ)
            exit_code = c.wait()
            if exit_code != 0:
                raise ClickException('%s: Editing failed!' % editor)
        except OSError as e:
            raise ClickException('%s: Editing failed: %s' % (editor, e))

    def edit(self, text):
        import tempfile

        text = text or ''
        if text and not text.endswith('\n'):
            text += '\n'

        fd, name = tempfile.mkstemp(prefix='editor-', suffix=self.extension)
        try:
            if sys.platform.startswith('win'):
                encoding = 'utf-8-sig'
                text = text.replace('\n', '\r\n')
            else:
                encoding = 'utf-8'
            text = text.encode(encoding)

            f = os.fdopen(fd, 'wb')
            f.write(text)
            f.close()
            timestamp = os.path.getmtime(name)

            self.edit_file(name)

            if self.require_save \
               and os.path.getmtime(name) == timestamp:
                return None

            f = open(name)
            try:
                rv = f.read()
            finally:
                f.close()
            return rv.decode('utf-8-sig').replace('\r\n', '\n')
        finally:
            os.unlink(name)


def open_url(url, wait=False, locate=False):
    import subprocess

    def _unquote_file(url):
        try:
            import urllib
        except ImportError:
            import urllib
        if url.startswith('file://'):
            url = urllib.unquote(url[7:])
        return url

    if sys.platform == 'darwin':
        args = ['open']
        if wait:
            args.append('-W')
        if locate:
            args.append('-R')
        args.append(_unquote_file(url))
        return subprocess.Popen(args).wait()
    elif sys.platform.startswith('win'):
        if locate:
            url = _unquote_file(url)
            args = ['explorer', '/select,"%s"' % _unquote_file(url)]
        else:
            args = ['start']
            if wait:
                args.append('/WAIT')
        args.append(url)
        return subprocess.Popen(args).wait()

    try:
        if locate:
            url = os.path.dirname(_unquote_file(url)) or '.'
        else:
            url = _unquote_file(url)
        c = subprocess.Popen(['xdg-open', url])
        if wait:
            return c.wait()
        return 0
    except OSError:
        if url.startswith(('http://', 'https://')) and not locate and not wait:
            import webbrowser
            webbrowser.open(url)
            return 0
        return 1

########NEW FILE########
__FILENAME__ = clickdoctools
import os
import sys
import click
import shutil
import tempfile
import contextlib

try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO

from docutils import nodes
from docutils.statemachine import ViewList

from sphinx.domains import Domain
from sphinx.util.compat import Directive


class EchoingStdin(object):

    def __init__(self, input, output):
        self._input = input
        self._output = output

    def __getattr__(self, x):
        return getattr(self._input, x)

    def _echo(self, rv):
        mark = False
        if rv.endswith('\xff'):
            rv = rv[:-1]
            mark = True
        self._output.write(rv)
        if mark:
            self._output.write('^D\n')
        return rv

    def read(self, n=-1):
        return self._echo(self._input.read(n))

    def readline(self, n=-1):
        return self._echo(self._input.readline(n))

    def readlines(self):
        return [self._echo(x) for x in self._input.readlines()]

    def __iter__(self):
        return iter(self._echo(x) for x in self._input)


@contextlib.contextmanager
def isolation(input=None, env=None):
    if isinstance(input, unicode):
        input = input.encode('utf-8')
    input = StringIO(input or '')
    output = StringIO()
    sys.stdin = EchoingStdin(input, output)
    sys.stdin.encoding = 'utf-8'

    def visible_input(prompt=None):
        sys.stdout.write(prompt or '')
        val = input.readline().rstrip('\r\n')
        sys.stdout.write(val + '\n')
        sys.stdout.flush()
        return val

    def hidden_input(prompt=None):
        sys.stdout.write((prompt or '') + '\n')
        sys.stdout.flush()
        return input.readline().rstrip('\r\n')

    sys.stdout = output
    sys.stderr = output
    old_visible_prompt_func = click.termui.visible_prompt_func
    old_hidden_prompt_func = click.termui.hidden_prompt_func
    click.termui.visible_prompt_func = visible_input
    click.termui.hidden_prompt_func = hidden_input

    old_env = {}
    try:
        if env:
            for key, value in env.iteritems():
                old_env[key] = os.environ.get(value)
                os.environ[key] = value
        yield output
    finally:
        for key, value in old_env.iteritems():
            if value is None:
                try:
                    del os.environ[key]
                except Exception:
                    pass
            else:
                os.environ[key] = value
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__
        click.termui.visible_prompt_func = old_visible_prompt_func
        click.termui.hidden_prompt_func = old_hidden_prompt_func


@contextlib.contextmanager
def isolated_filesystem():
    cwd = os.getcwd()
    t = tempfile.mkdtemp()
    os.chdir(t)
    try:
        yield
    finally:
        os.chdir(cwd)
        try:
            shutil.rmtree(t)
        except (OSError, IOError):
            pass


class ExampleRunner(object):

    def __init__(self):
        self.namespace = {
            'click': click,
            '__file__': 'dummy.py',
        }

    def declare(self, source):
        code = compile(source, '<docs>', 'exec')
        eval(code, self.namespace)

    def run(self, source):
        code = compile(source, '<docs>', 'exec')
        buffer = []

        def invoke(cmd, args=None, prog_name=None, prog_prefix='python ',
                   input=None, terminate_input=False, env=None,
                   **extra):
            if env:
                for key, value in sorted(env.items()):
                    if ' ' in value:
                        value = '"%s"' % value
                    buffer.append('$ export %s=%s' % (key, value))
            args = args or []
            if prog_name is None:
                prog_name = cmd.name.replace('_', '-') + '.py'
            buffer.append(('$ %s%s %s' % (
                prog_prefix,
                prog_name,
                ' '.join(('"%s"' % x) if ' ' in x else x for x in args)
            )).rstrip())
            if isinstance(input, (tuple, list)):
                input = '\n'.join(input) + '\n'
                if terminate_input:
                    input += '\xff'
            with isolation(input=input, env=env) as output:
                try:
                    cmd.main(args=args, prog_name=prog_name, **extra)
                except SystemExit:
                    pass
                buffer.extend(output.getvalue().splitlines())

        def println(text=''):
            buffer.append(text)

        eval(code, self.namespace, {
            'invoke': invoke,
            'println': println,
            'isolated_filesystem': isolated_filesystem,
        })
        return buffer

    def close(self):
        pass


def parse_rst(state, content_offset, doc):
    node = nodes.section()
    # hack around title style bookkeeping
    surrounding_title_styles = state.memo.title_styles
    surrounding_section_level = state.memo.section_level
    state.memo.title_styles = []
    state.memo.section_level = 0
    state.nested_parse(doc, content_offset, node, match_titles=1)
    state.memo.title_styles = surrounding_title_styles
    state.memo.section_level = surrounding_section_level
    return node.children


def get_example_runner(document):
    runner = getattr(document, 'click_example_runner', None)
    if runner is None:
        runner = document.click_example_runner = ExampleRunner()
    return runner


class ExampleDirective(Directive):
    has_content = True
    required_arguments = 0
    optional_arguments = 0
    final_argument_whitespace = False

    def run(self):
        doc = ViewList()
        runner = get_example_runner(self.state.document)
        try:
            runner.declare('\n'.join(self.content))
        except:
            runner.close()
            raise
        doc.append('.. sourcecode:: python', '')
        doc.append('', '')
        for line in self.content:
            doc.append(' ' + line, '')
        return parse_rst(self.state, self.content_offset, doc)


class RunExampleDirective(Directive):
    has_content = True
    required_arguments = 0
    optional_arguments = 0
    final_argument_whitespace = False

    def run(self):
        doc = ViewList()
        runner = get_example_runner(self.state.document)
        try:
            rv = runner.run('\n'.join(self.content))
        except:
            runner.close()
            raise
        doc.append('.. sourcecode:: text', '')
        doc.append('', '')
        for line in rv:
            doc.append(' ' + line, '')
        return parse_rst(self.state, self.content_offset, doc)


class ClickDomain(Domain):
    name = 'click'
    label = 'Click'
    directives = {
        'example':  ExampleDirective,
        'run':      RunExampleDirective,
    }


def delete_example_runner_state(app, doctree):
    runner = getattr(doctree, 'click_example_runner', None)
    if runner is not None:
        runner.close()
        del doctree.click_example_runner


def setup(app):
    app.add_domain(ClickDomain)

    app.connect('doctree-read', delete_example_runner_state)

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# click documentation build configuration file, created by
# sphinx-quickstart on Mon Apr 26 19:53:01 2010.
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
sys.path.append(os.path.abspath('_themes'))
sys.path.append(os.path.abspath('..'))
sys.path.append(os.path.abspath('.'))

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.intersphinx',
              'clickdoctools']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'click'
copyright = u'2014, Armin Ronacher'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '1.0'
# The full version, including alpha/beta/rc tags.
release = '1.0'

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

# A list of ignored prefixes for module index sorting.
#modindex_common_prefix = []


# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  Major themes that come with
# Sphinx are currently 'default' and 'sphinxdoc'.
html_theme = 'click'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
html_theme_options = {
}

# Add any paths that contain custom themes here, relative to this directory.
html_theme_path = ['_themes']

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
html_title = 'click'

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
html_sidebars = {
    'index':    ['sidebarintro.html', 'sourcelink.html', 'searchbox.html'],
    '**':       ['sidebarlogo.html', 'localtoc.html', 'relations.html',
                 'sourcelink.html', 'searchbox.html']
}

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

# If nonempty, this is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = ''

# Output file base name for HTML help builder.
htmlhelp_basename = 'clickdoc'


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'click.tex', u'click documentation',
   u'Armin Ronacher', 'manual'),
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
#latex_domain_indices = True


# -- Options for manual page output --------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'click', u'click documentation',
     [u'Armin Ronacher'], 1)
]

intersphinx_mapping = {
    'http://docs.python.org/dev': None
}

########NEW FILE########
__FILENAME__ = aliases
import os
import click

try:
    import ConfigParser as configparser
except ImportError:
    import configparser


class Config(object):
    """The config in this example only holds aliases."""

    def __init__(self):
        self.path = os.getcwd()
        self.aliases = {}

    def read_config(self, filename):
        parser = configparser.RawConfigParser()
        parser.read([filename])
        try:
            self.aliases.update(parser.items('aliases'))
        except configparser.NoSectionError:
            pass


pass_config = click.make_pass_decorator(Config, ensure=True)


class AliasedGroup(click.Group):
    """This subclass of a group supports looking up aliases in a config
    file and with a bit of magic.
    """

    def get_command(self, ctx, cmd_name):
        # Step one: bulitin commands as normal
        rv = click.Group.get_command(self, ctx, cmd_name)
        if rv is not None:
            return rv

        # Step two: find the config object and ensure it's there.  This
        # will create the config object is missing.
        cfg = ctx.ensure_object(Config)

        # Step three: lookup an explicit command aliase in the config
        if cmd_name in cfg.aliases:
            actual_cmd = cfg.aliases[cmd_name]
            return click.Group.get_command(self, ctx, actual_cmd)

        # Alternative option: if we did not find an explicit alias we
        # allow automatic abbreviation of the command.  "status" for
        # instance will match "st".  We only allow that however if
        # there is only one command.
        matches = [x for x in self.list_commands(ctx)
                   if x.lower().startswith(cmd_name.lower())]
        if not matches:
            return None
        elif len(matches) == 1:
            return click.Group.get_command(self, ctx, matches[0])
        ctx.fail('Too many matches: %s' % ', '.join(sorted(matches)))


def read_config(ctx, param, value):
    """Callback that is used whenever --config is passed.  We use this to
    always load the correct config.  This means that the config is loaded
    even if the group itself never executes so our aliases stay always
    available.
    """
    cfg = ctx.ensure_object(Config)
    if value is None:
        value = os.path.join(os.path.dirname(__file__), 'aliases.ini')
    cfg.read_config(value)
    return value


@click.command(cls=AliasedGroup)
@click.option('--config', type=click.Path(exists=True, dir_okay=False),
              callback=read_config, expose_value=False,
              help='The config file to use instead of the default.')
def cli():
    """An example application that supports aliases."""


@cli.command()
def push():
    """Pushes changes."""
    click.echo('Push')


@cli.command()
def pull():
    """Pulls changes."""
    click.echo('Pull')


@cli.command()
def clone():
    """Clones a repository."""
    click.echo('Clone')


@cli.command()
def commit():
    """Commits pending changes."""
    click.echo('Commit')


@cli.command()
@pass_config
def status(config):
    """Shows the status."""
    click.echo('Status for %s' % config.path)

########NEW FILE########
__FILENAME__ = colors
import click


all_colors = 'black', 'red', 'green', 'yellow', 'blue', 'magenta', \
             'cyan', 'white'


@click.command()
def cli():
    """This script prints some colors.  If colorama is installed this will
    also work on Windows.  It will also automatically remove all ANSI
    styles if data is piped into a file.

    Give it a try!
    """
    for color in all_colors:
        click.echo(click.style('I am colored %s' % color, fg=color))
    for color in all_colors:
        click.echo(click.style('I am colored %s and bold' % color,
                               fg=color, bold=True))
    for color in all_colors:
        click.echo(click.style('I am reverse colored %s' % color, fg=color,
                               reverse=True))

    click.echo(click.style('I am blinking', blink=True))
    click.echo(click.style('I am underlined', underline=True))

########NEW FILE########
__FILENAME__ = cli
import os
import sys
import click


class Context(object):

    def __init__(self):
        self.verbose = False
        self.home = os.getcwd()

    def log(self, msg, *args):
        """Logs a message to stderr."""
        if args:
            msg %= args
        click.echo(msg, file=sys.stderr)

    def vlog(self, msg, *args):
        """Logs a message to stderr only if verbose is enabled."""
        if self.verbose:
            self.log(msg, *args)


pass_context = click.make_pass_decorator(Context, ensure=True)
cmd_folder = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                          'commands'))


class ComplexCLI(click.MultiCommand):

    def list_commands(self, ctx):
        rv = []
        for filename in os.listdir(cmd_folder):
            if filename.endswith('.py') and \
               filename.startswith('cmd_'):
                rv.append(filename[4:-3])
        rv.sort()
        return rv

    def get_command(self, ctx, name):
        try:
            mod = __import__('complex.commands.cmd_' +
                             name.encode('ascii', 'replace'),
                             None, None, ['cli'])
        except ImportError:
            return
        return mod.cli


@click.command(cls=ComplexCLI)
@click.option('--home', type=click.Path(exists=True, file_okay=False,
                                        resolve_path=True),
              help='Changes the folder to operate on.')
@click.option('-v', '--verbose', is_flag=True,
              help='Enables verbose mode.')
@pass_context
def cli(ctx, verbose, home):
    """A complex command line interface."""
    ctx.verbose = verbose
    if home is not None:
        ctx.home = home


def main():
    cli(auto_envvar_prefix='COMPLEX')

########NEW FILE########
__FILENAME__ = cmd_init
import click
from complex.cli import pass_context


@click.command('init', short_help='Initializes a repo.')
@click.argument('path', required=False, type=click.Path(resolve_path=True))
@pass_context
def cli(ctx, path):
    """Initializes a repository."""
    if path is None:
        path = ctx.home
    ctx.log('Initialized the repository in %s',
            click.format_filename(path))

########NEW FILE########
__FILENAME__ = cmd_status
import click
from complex.cli import pass_context


@click.command('status', short_help='Shows file changes.')
@pass_context
def cli(ctx):
    """Shows file changes in the current working directory."""
    ctx.log('Changed files: none')
    ctx.vlog('bla bla bla, debug info')

########NEW FILE########
__FILENAME__ = inout
import click


@click.command()
@click.argument('input', type=click.File('rb'), nargs=-1)
@click.argument('output', type=click.File('wb'))
def cli(input, output):
    """This script works similar to the unix `cat` command but it writes
    into a specific file (which could be the standard output as denoted by
    the ``-`` sign).

    \b
    Copy stdin to stdout:
        inout - -

    \b
    Copy foo.txt and bar.txt to stdout:
        inout foo.txt bar.txt -

    \b
    Write stdin into the file foo.txt
        inout - foo.txt
    """
    for f in input:
        while True:
            chunk = f.read(1024)
            if not chunk:
                break
            output.write(chunk)
            output.flush()

########NEW FILE########
__FILENAME__ = naval
import click


@click.group()
@click.version_option()
def cli():
    """Naval Fate.

    This is the docopt example adopted to Click but with some actual
    commands implemented and not just the empty parsing which really
    is not all that interesting.
    """


@cli.group()
def ship():
    """Manages ships."""


@ship.command('new')
@click.argument('name')
def ship_new(name):
    """Creates a new ship."""
    click.echo('Created ship %s' % name)


@ship.command('move')
@click.argument('ship')
@click.argument('x', type=float)
@click.argument('y', type=float)
@click.option('--speed', metavar='KN', default=10,
              help='Speed in knots.')
def ship_move(ship, x, y, speed):
    """Moves SHIP to the new location X,Y."""
    click.echo('Moving ship %s to %s,%s with speed %s' % (ship, x, y, speed))


@ship.command('shoot')
@click.argument('ship')
@click.argument('x', type=float)
@click.argument('y', type=float)
def ship_shoot(ship, x, y):
    """Makes SHIP fire to X,Y."""
    click.echo('Ship %s fires to %s,%s' % (ship, x, y))


@cli.group('mine')
def mine(ship):
    """Manages mines."""


@mine.command('set')
@click.argument('x', type=float)
@click.argument('y', type=float)
@click.option('ty', '--moored', flag_value='moored',
              default=True,
              help='Moored (anchored) mine. Default.')
@click.option('ty', '--drifting', flag_value='drifting',
              help='Drifting mine.')
def mine_set(x, y, ty):
    """Sets a mine at a specific coordinate."""
    click.echo('Set %s mine at %s,%s' % (ty, x, y))


@mine.command('remove')
@click.argument('x', type=float)
@click.argument('y', type=float)
def mine_remove(x, y):
    """Removes a mine at a specific coordinate."""
    click.echo('Removed mine at %s,%s' % (x, y))

########NEW FILE########
__FILENAME__ = repo
import os
import sys
import posixpath

import click


class Repo(object):

    def __init__(self, home):
        self.home = home
        self.config = {}
        self.verbose = False

    def set_config(self, key, value):
        self.config[key] = value
        if self.verbose:
            click.echo('  config[%s] = %s' % (key, value), file=sys.stderr)

    def __repr__(self):
        return '<Repo %r>' % self.home


pass_repo = click.make_pass_decorator(Repo)


@click.group()
@click.option('--repo-home', envvar='REPO_HOME', default='.repo',
              metavar='PATH', help='Changes the repository folder location.')
@click.option('--config', nargs=2, multiple=True,
              metavar='KEY VALUE', help='Overrides a config key/value pair.')
@click.option('--verbose', '-v', is_flag=True,
              help='Enables verbose mode.')
@click.version_option('1.0')
@click.pass_context
def cli(ctx, repo_home, config, verbose):
    """Repo is a command line tool that showcases how to build complex
    command line interfaces with Click.

    This tool is supposed to look like a distributed version control
    system to show how something like this can be structured.
    """
    # Create a repo object and remember it as as the context object.  From
    # this point onwards other commands can refer to it by using the
    # @pass_repo decorator.
    ctx.obj = Repo(os.path.abspath(repo_home))
    ctx.obj.verbose = verbose
    for key, value in config:
        ctx.obj.set_config(key, value)


@cli.command()
@click.argument('src')
@click.argument('dest', required=False)
@click.option('--shallow/--deep', default=False,
              help='Makes a checkout shallow or deep.  Deep by default.')
@click.option('--rev', '-r', default='HEAD',
              help='Clone a specific revision instead of HEAD.')
@pass_repo
def clone(repo, src, dest, shallow, rev):
    """Clones a repository.

    This will clone the repository at SRC into the folder DEST.  If DEST
    is not provided this will automatically use the last path component
    of SRC and create that folder.
    """
    if dest is None:
        dest = posixpath.split(src)[-1] or '.'
    click.echo('Cloning repo %s to %s' % (src, os.path.abspath(dest)))
    repo.home = dest
    if shallow:
        click.echo('Making shallow checkout')
    click.echo('Checking out revision %s' % rev)


@cli.command()
@click.confirmation_option()
@pass_repo
def delete(repo):
    """Deletes a repository.

    This will throw away the current repository.
    """
    click.echo('Destroying repo %s' % repo.home)
    click.echo('Deleted!')


@cli.command()
@click.option('--username', prompt=True,
              help='The developer\'s shown username.')
@click.option('--email', prompt='E-Mail',
              help='The developer\'s email address')
@click.password_option(help='The login password.')
@pass_repo
def setuser(repo, username, email, password):
    """Sets the user credentials.

    This will override the current user config.
    """
    repo.set_config('username', username)
    repo.set_config('email', email)
    repo.set_config('password', '*' * len(password))
    click.echo('Changed credentials.')


@cli.command()
@click.option('--message', '-m', multiple=True,
              help='The commit message.  If provided multiple times each '
              'argument gets converted into a new line.')
@click.argument('files', nargs=-1, type=click.Path())
@pass_repo
def commit(repo, files, message):
    """Commits outstanding changes.

    Commit changes to the given files into the repository.  You will need to
    "repo push" to push up your changes to other repositories.

    If a list of files is omitted, all changes reported by "repo status"
    will be committed.
    """
    if not message:
        marker = '# Files to be committed:'
        hint = ['', '', marker, '#']
        for file in files:
            hint.append('#   U %s' % file)
        message = click.edit('\n'.join(hint))
        if message is None:
            click.echo('Aborted!')
            return
        msg = message.split(marker)[0].rstrip()
        if not msg:
            click.echo('Aborted! Empty commit message')
            return
    else:
        msg = '\n'.join(message)
    click.echo('Files to be committed: %s' % (files,))
    click.echo('Commit message:\n' + msg)


@cli.command(short_help='Copies files.')
@click.option('--force', is_flag=True,
              help='forcibly copy over an existing managed file')
@click.argument('src', nargs=-1, type=click.Path())
@click.argument('dst', type=click.Path())
@pass_repo
def copy(repo, src, dst, force):
    """Copies one or multiple files to a new location.  This copies all
    files from SRC to DST.
    """
    for fn in src:
        click.echo('Copy from %s -> %s' % (fn, dst))

########NEW FILE########
__FILENAME__ = termui
# coding: utf-8
import click
import time
import random

try:
    range_type = xrange
except NameError:
    range_type = range


@click.group()
def cli():
    """This script showcases different terminal UI helpers in Click."""
    pass


@cli.command()
def colordemo():
    """Demonstrates ANSI color support."""
    for color in 'red', 'green', 'blue':
        click.echo(click.style('I am colored %s' % color, fg=color))
        click.echo(click.style('I am background colored %s' % color, bg=color))


@cli.command()
def pager():
    """Demonstrates using the pager."""
    lines = []
    for x in xrange(200):
        lines.append('%s. Hello World!' % click.style(str(x), fg='green'))
    click.echo_via_pager('\n'.join(lines))


@cli.command()
@click.option('--count', default=8000, type=click.IntRange(1, 100000),
              help='The number of items to process.')
def progress(count):
    """Demonstrates the progress bar."""
    items = range_type(count)

    def process_slowly(item):
        time.sleep(0.002 * random.random())

    def filter(items):
        for item in items:
            if random.random() > 0.3:
                yield item

    with click.progressbar(items, label='Processing user accounts',
                           fill_char=click.style('#', fg='green')) as bar:
        for item in bar:
            process_slowly(item)

    def show_item(item):
        if item is not None:
            return 'Item #%d' % item

    with click.progressbar(filter(items), label='Committing transaction',
                           fill_char=click.style('#', fg='yellow'),
                           item_show_func=show_item) as bar:
        for item in bar:
            process_slowly(item)

    with click.progressbar(length=count, label='Counting',
                           bar_template='%(label)s  %(bar)s | %(info)s',
                           fill_char=click.style(u'█', fg='cyan'),
                           empty_char=' ') as bar:
        for item in bar:
            process_slowly(item)


@cli.command()
@click.argument('url')
def open(url):
    """Opens a file or URL In the default application."""
    click.launch(url)


@cli.command()
@click.argument('url')
def locate(url):
    """Opens a file or URL In the default application."""
    click.launch(url, locate=True)


@cli.command()
def edit():
    """Opens an editor with some text in it."""
    MARKER = '# Everything below is ignored\n'
    message = click.edit('\n\n' + MARKER)
    if message is not None:
        msg = message.split(MARKER, 1)[0].rstrip('\n')
        if not msg:
            click.echo('Empty message!')
        else:
            click.echo('Message:\n' + msg)
    else:
        click.echo('You did not enter anything!')


@cli.command()
def clear():
    """Clears the entire screen."""
    click.clear()

########NEW FILE########
__FILENAME__ = validation
import click
try:
    from urllib import parser as urlparse
except ImportError:
    import urlparse


def validate_count(ctx, param, value):
    if value < 0 or value % 2 != 0:
        raise click.BadParameter('Should be a positive, even integer.')
    return value


class URL(click.ParamType):
    name = 'url'

    def convert(self, value, param, ctx):
        if not isinstance(value, tuple):
            value = urlparse.urlparse(value)
            if value.scheme not in ('http', 'https'):
                self.fail('invalid URL scheme (%s).  Only HTTP URLs are '
                          'allowed' % value.scheme, param, ctx)
        return value


@click.command()
@click.option('--count', default=2, callback=validate_count,
              help='A positive even number.')
@click.option('--foo', help='A mysterious parameter.')
@click.option('--url', help='A URL', type=URL())
@click.version_option()
def cli(count, foo, url):
    """Validation.

    This example validates parameters in different ways.  It does it
    through callbacks, through a custom type as well as by validating
    manually in the function.
    """
    if foo is not None and foo != 'wat':
        raise click.BadParameter('If a value is provided it needs to be the '
                                 'value "wat".', param_hint=['--foo'])
    click.echo('count: %s' % count)
    click.echo('foo: %s' % foo)
    click.echo('url: %s' % repr(url))

########NEW FILE########
__FILENAME__ = conftest
from click.testing import CliRunner

import pytest


@pytest.fixture(scope='function')
def runner(request):
    return CliRunner()

########NEW FILE########
__FILENAME__ = test_arguments
# -*- coding: utf-8 -*-
import click


def test_nargs_star(runner):
    @click.command()
    @click.argument('src', nargs=-1)
    @click.argument('dst')
    def copy(src, dst):
        click.echo('src=%s' % '|'.join(src))
        click.echo('dst=%s' % dst)

    result = runner.invoke(copy, ['foo.txt', 'bar.txt', 'dir'])
    assert not result.exception
    assert result.output.splitlines() == [
        'src=foo.txt|bar.txt',
        'dst=dir',
    ]


def test_nargs_tup(runner):
    @click.command()
    @click.argument('name', nargs=1)
    @click.argument('point', nargs=2, type=click.INT)
    def copy(name, point):
        click.echo('name=%s' % name)
        click.echo('point=%d/%d' % point)

    result = runner.invoke(copy, ['peter', '1', '2'])
    assert not result.exception
    assert result.output.splitlines() == [
        'name=peter',
        'point=1/2',
    ]


def test_nargs_err(runner):
    @click.command()
    @click.argument('x')
    def copy(x):
        click.echo(x)

    result = runner.invoke(copy, ['foo'])
    assert not result.exception
    assert result.output == 'foo\n'

    result = runner.invoke(copy, ['foo', 'bar'])
    assert result.exit_code == 2
    assert 'Got unexpected extra argument (bar)' in result.output


def test_file_args(runner):
    @click.command()
    @click.argument('input', type=click.File('rb'))
    @click.argument('output', type=click.File('wb'))
    def inout(input, output):
        while True:
            chunk = input.read(1024)
            if not chunk:
                break
            output.write(chunk)

    with runner.isolated_filesystem():
        result = runner.invoke(inout, ['-', 'hello.txt'], input='Hey!')
        assert result.output == ''
        assert result.exit_code == 0
        with open('hello.txt', 'rb') as f:
            assert f.read() == b'Hey!'

        result = runner.invoke(inout, ['hello.txt', '-'])
        assert result.output == 'Hey!'
        assert result.exit_code == 0


def test_file_atomics(runner):
    @click.command()
    @click.argument('output', type=click.File('wb', atomic=True))
    def inout(output):
        output.write(b'Foo bar baz\n')
        output.flush()
        with open(output.name, 'rb') as f:
            old_content = f.read()
            assert old_content == b'OLD\n'

    with runner.isolated_filesystem():
        with open('foo.txt', 'wb') as f:
            f.write(b'OLD\n')
        result = runner.invoke(inout, ['foo.txt'], input='Hey!')
        assert result.output == ''
        assert result.exit_code == 0
        with open('foo.txt', 'rb') as f:
            assert f.read() == b'Foo bar baz\n'


def test_stdout_default(runner):
    @click.command()
    @click.argument('output', type=click.File('w'), default='-')
    def inout(output):
        output.write('Foo bar baz\n')
        output.flush()

    result = runner.invoke(inout, [])
    assert not result.exception
    assert result.output == 'Foo bar baz\n'


def test_nargs_envvar(runner):
    @click.command()
    @click.option('--arg', nargs=-1)
    def cmd(arg):
        click.echo('|'.join(arg))

    result = runner.invoke(cmd, [], auto_envvar_prefix='TEST',
                           env={'TEST_ARG': 'foo bar'})
    assert not result.exception
    assert result.output == 'foo|bar\n'

    @click.command()
    @click.option('--arg', envvar='X', nargs=-1)
    def cmd(arg):
        click.echo('|'.join(arg))

    result = runner.invoke(cmd, [], env={'X': 'foo bar'})
    assert not result.exception
    assert result.output == 'foo|bar\n'


def test_empty_nargs(runner):
    @click.command()
    @click.argument('arg', nargs=-1)
    def cmd(arg):
        click.echo('arg:' + '|'.join(arg))

    result = runner.invoke(cmd, [])
    assert result.exit_code == 0
    assert result.output == 'arg:\n'

    @click.command()
    @click.argument('arg', nargs=-1, required=True)
    def cmd2(arg):
        click.echo('arg:' + '|'.join(arg))

    result = runner.invoke(cmd2, [])
    assert result.exit_code == 2
    assert 'Missing argument "arg"' in result.output


def test_missing_arg(runner):
    @click.command()
    @click.argument('arg')
    def cmd(arg):
        click.echo('arg:' + arg)

    result = runner.invoke(cmd, [])
    assert result.exit_code == 2
    assert 'Missing argument "arg".' in result.output


def test_implicit_non_required(runner):
    @click.command()
    @click.argument('f', default='test')
    def cli(f):
        click.echo(f)

    result = runner.invoke(cli, [])
    assert result.exit_code == 0
    assert result.output == 'test\n'


def test_eat_options(runner):
    @click.command()
    @click.option('-f')
    @click.argument('files', nargs=-1)
    def cmd(f, files):
        for filename in files:
            click.echo(filename)
        click.echo(f)

    result = runner.invoke(cmd, ['--', '-foo', 'bar'])
    assert result.output.splitlines() == [
        '-foo',
        'bar',
        '',
    ]

    result = runner.invoke(cmd, ['-f', '-x', '--', '-foo', 'bar'])
    assert result.output.splitlines() == [
        '-foo',
        'bar',
        '-x',
    ]

########NEW FILE########
__FILENAME__ = test_basic
# -*- coding: utf-8 -*-
import os
import uuid
import click


def test_basic_functionality(runner):
    @click.command()
    def cli():
        """Hello World!"""
        click.echo('I EXECUTED')

    result = runner.invoke(cli, ['--help'])
    assert not result.exception
    assert 'Hello World!' in result.output
    assert 'Show this message and exit.' in result.output
    assert result.exit_code == 0
    assert 'I EXECUTED' not in result.output

    result = runner.invoke(cli, [])
    assert not result.exception
    assert 'I EXECUTED' in result.output
    assert result.exit_code == 0


def test_basic_group(runner):
    @click.group()
    def cli():
        """This is the root."""
        click.echo('ROOT EXECUTED')

    @cli.command()
    def subcommand():
        """This is a subcommand."""
        click.echo('SUBCOMMAND EXECUTED')

    result = runner.invoke(cli, ['--help'])
    assert not result.exception
    assert 'This is the root' in result.output
    assert 'This is a subcommand.' in result.output
    assert result.exit_code == 0
    assert 'ROOT EXECUTED' not in result.output

    result = runner.invoke(cli, ['subcommand'])
    assert not result.exception
    assert result.exit_code == 0
    assert 'ROOT EXECUTED' in result.output
    assert 'SUBCOMMAND EXECUTED' in result.output


def test_basic_option(runner):
    @click.command()
    @click.option('--foo', default='no value')
    def cli(foo):
        click.echo('FOO:[%s]' % foo)

    result = runner.invoke(cli, [])
    assert not result.exception
    assert 'FOO:[no value]' in result.output

    result = runner.invoke(cli, ['--foo=42'])
    assert not result.exception
    assert 'FOO:[42]' in result.output

    result = runner.invoke(cli, ['--foo'])
    assert result.exception
    assert '--foo option requires an argument' in result.output

    result = runner.invoke(cli, ['--foo='])
    assert not result.exception
    assert 'FOO:[]' in result.output

    result = runner.invoke(cli, [u'--foo=\N{SNOWMAN}'])
    assert not result.exception
    assert u'FOO:[\N{SNOWMAN}]' in result.output


def test_int_option(runner):
    @click.command()
    @click.option('--foo', default=42)
    def cli(foo):
        click.echo('FOO:[%s]' % (foo * 2))

    result = runner.invoke(cli, [])
    assert not result.exception
    assert 'FOO:[84]' in result.output

    result = runner.invoke(cli, ['--foo=23'])
    assert not result.exception
    assert 'FOO:[46]' in result.output

    result = runner.invoke(cli, ['--foo=bar'])
    assert result.exception
    assert 'Invalid value for "--foo": bar is not a valid integer' \
        in result.output


def test_uuid_option(runner):
    @click.command()
    @click.option('--u', default='ba122011-349f-423b-873b-9d6a79c688ab',
                  type=click.UUID)
    def cli(u):
        assert type(u) is uuid.UUID
        click.echo('U:[%s]' % u)

    result = runner.invoke(cli, [])
    assert not result.exception
    assert 'U:[ba122011-349f-423b-873b-9d6a79c688ab]' in result.output

    result = runner.invoke(cli, ['--u=821592c1-c50e-4971-9cd6-e89dc6832f86'])
    assert not result.exception
    assert 'U:[821592c1-c50e-4971-9cd6-e89dc6832f86]' in result.output

    result = runner.invoke(cli, ['--u=bar'])
    assert result.exception
    assert 'Invalid value for "--u": bar is not a valid UUID value' \
        in result.output


def test_float_option(runner):
    @click.command()
    @click.option('--foo', default=42, type=click.FLOAT)
    def cli(foo):
        assert type(foo) is float
        click.echo('FOO:[%s]' % foo)

    result = runner.invoke(cli, [])
    assert not result.exception
    assert 'FOO:[42.0]' in result.output

    result = runner.invoke(cli, ['--foo=23.5'])
    assert not result.exception
    assert 'FOO:[23.5]' in result.output

    result = runner.invoke(cli, ['--foo=bar'])
    assert result.exception
    assert 'Invalid value for "--foo": bar is not a valid float' \
        in result.output


def test_boolean_option(runner):
    for default in True, False:
        @click.command()
        @click.option('--with-foo/--without-foo', default=default)
        def cli(with_foo):
            click.echo(with_foo)

        result = runner.invoke(cli, ['--with-foo'])
        assert not result.exception
        assert result.output == 'True\n'
        result = runner.invoke(cli, ['--without-foo'])
        assert not result.exception
        assert result.output == 'False\n'
        result = runner.invoke(cli, [])
        assert not result.exception
        assert result.output == '%s\n' % default

    for default in True, False:
        @click.command()
        @click.option('--flag', is_flag=True, default=default)
        def cli(flag):
            click.echo(flag)

        result = runner.invoke(cli, ['--flag'])
        assert not result.exception
        assert result.output == '%s\n' % (not default)
        result = runner.invoke(cli, [])
        assert not result.exception
        assert result.output == '%s\n' % (default)


def test_file_option(runner):
    @click.command()
    @click.option('--file', type=click.File('w'))
    def input(file):
        file.write('Hello World!\n')

    @click.command()
    @click.option('--file', type=click.File('r'))
    def output(file):
        click.echo(file.read())

    with runner.isolated_filesystem():
        result_in = runner.invoke(input, ['--file=example.txt'])
        result_out = runner.invoke(output, ['--file=example.txt'])

    assert not result_in.exception
    assert result_in.output == ''
    assert not result_out.exception
    assert result_out.output == 'Hello World!\n\n'


def test_file_lazy_mode(runner):
    do_io = False

    @click.command()
    @click.option('--file', type=click.File('w'))
    def input(file):
        if do_io:
            file.write('Hello World!\n')

    @click.command()
    @click.option('--file', type=click.File('r'))
    def output(file):
        pass

    with runner.isolated_filesystem():
        os.mkdir('example.txt')

        do_io = True
        result_in = runner.invoke(input, ['--file=example.txt'])
        assert result_in.exit_code == 1

        do_io = False
        result_in = runner.invoke(input, ['--file=example.txt'])
        assert result_in.exit_code == 0

        result_out = runner.invoke(output, ['--file=example.txt'])
        assert result_out.exception

    @click.command()
    @click.option('--file', type=click.File('w', lazy=False))
    def input_non_lazy(file):
        file.write('Hello World!\n')

    with runner.isolated_filesystem():
        os.mkdir('example.txt')
        result_in = runner.invoke(input_non_lazy, ['--file=example.txt'])
        assert result_in.exit_code == 2
        assert 'Invalid value for "--file": Could not open file: example.txt' \
            in result_in.output


def test_path_option(runner):
    @click.command()
    @click.option('-O', type=click.Path(file_okay=False, exists=True,
                                        writable=True))
    def write_to_dir(o):
        with open(os.path.join(o, 'foo.txt'), 'wb') as f:
            f.write(b'meh\n')

    with runner.isolated_filesystem():
        os.mkdir('test')

        result = runner.invoke(write_to_dir, ['-O', 'test'])
        assert not result.exception

        with open('test/foo.txt', 'rb') as f:
            assert f.read() == b'meh\n'

        result = runner.invoke(write_to_dir, ['-O', 'test/foo.txt'])
        assert 'Invalid value for "-O": Directory "test/foo.txt" is a file.' \
            in result.output

    @click.command()
    @click.option('-f', type=click.Path(exists=True))
    def showtype(f):
        click.echo('is_file=%s' % os.path.isfile(f))
        click.echo('is_dir=%s' % os.path.isdir(f))

    with runner.isolated_filesystem():
        result = runner.invoke(showtype, ['-f', 'xxx'])
        assert 'Error: Invalid value for "-f": Path "xxx" does not exist' \
            in result.output

        result = runner.invoke(showtype, ['-f', '.'])
        assert 'is_file=False' in result.output
        assert 'is_dir=True' in result.output

    @click.command()
    @click.option('-f', type=click.Path())
    def exists(f):
        click.echo('exists=%s' % os.path.exists(f))

    with runner.isolated_filesystem():
        result = runner.invoke(exists, ['-f', 'xxx'])
        assert 'exists=False' in result.output

        result = runner.invoke(exists, ['-f', '.'])
        assert 'exists=True' in result.output


def test_choice_option(runner):
    @click.command()
    @click.option('--method', type=click.Choice(['foo', 'bar', 'baz']))
    def cli(method):
        click.echo(method)

    result = runner.invoke(cli, ['--method=foo'])
    assert not result.exception
    assert result.output == 'foo\n'

    result = runner.invoke(cli, ['--method=meh'])
    assert result.exit_code == 2
    assert 'Invalid value for "--method": invalid choice: meh. ' \
        '(choose from foo, bar, baz)' in result.output

    result = runner.invoke(cli, ['--help'])
    assert '--method [foo|bar|baz]' in result.output


def test_int_range_option(runner):
    @click.command()
    @click.option('--x', type=click.IntRange(0, 5))
    def cli(x):
        click.echo(x)

    result = runner.invoke(cli, ['--x=5'])
    assert not result.exception
    assert result.output == '5\n'

    result = runner.invoke(cli, ['--x=6'])
    assert result.exit_code == 2
    assert 'Invalid value for "--x": 6 is not in the valid range of 0 to 5.\n' \
        in result.output

    @click.command()
    @click.option('--x', type=click.IntRange(0, 5, clamp=True))
    def clamp(x):
        click.echo(x)

    result = runner.invoke(clamp, ['--x=5'])
    assert not result.exception
    assert result.output == '5\n'

    result = runner.invoke(clamp, ['--x=6'])
    assert not result.exception
    assert result.output == '5\n'

    result = runner.invoke(clamp, ['--x=-1'])
    assert not result.exception
    assert result.output == '0\n'


def test_required_option(runner):
    @click.command()
    @click.option('--foo', required=True)
    def cli(foo):
        click.echo(foo)

    result = runner.invoke(cli, [])
    assert result.exit_code == 2
    assert 'Missing option "--foo"' in result.output


def test_evaluation_order(runner):
    called = []

    def memo(ctx, value):
        called.append(value)
        return value

    @click.command()
    @click.option('--missing', default='missing',
                  is_eager=False, callback=memo)
    @click.option('--eager-flag1', flag_value='eager1',
                  is_eager=True, callback=memo)
    @click.option('--eager-flag2', flag_value='eager2',
                  is_eager=True, callback=memo)
    @click.option('--eager-flag3', flag_value='eager3',
                  is_eager=True, callback=memo)
    @click.option('--normal-flag1', flag_value='normal1',
                  is_eager=False, callback=memo)
    @click.option('--normal-flag2', flag_value='normal2',
                  is_eager=False, callback=memo)
    @click.option('--normal-flag3', flag_value='normal3',
                  is_eager=False, callback=memo)
    def cli(**x):
        pass

    result = runner.invoke(cli, ['--eager-flag2',
                                 '--eager-flag1',
                                 '--normal-flag2',
                                 '--eager-flag3',
                                 '--normal-flag3',
                                 '--normal-flag3',
                                 '--normal-flag1',
                                 '--normal-flag1'])
    assert not result.exception
    assert called == [
        'eager2',
        'eager1',
        'eager3',
        'normal2',
        'normal3',
        'normal1',
        'missing',
    ]

########NEW FILE########
__FILENAME__ = test_commands
# -*- coding: utf-8 -*-
import re
import click


def test_other_command_invoke(runner):
    @click.command()
    @click.pass_context
    def cli(ctx):
        return ctx.invoke(other_cmd, 42)

    @click.command()
    @click.argument('arg', type=click.INT)
    def other_cmd(arg):
        click.echo(arg)

    result = runner.invoke(cli, [])
    assert not result.exception
    assert result.output == '42\n'


def test_other_command_forward(runner):
    cli = click.Group()

    @cli.command()
    @click.option('--count', default=1)
    def test(count):
        click.echo('Count: %d' % count)

    @cli.command()
    @click.option('--count', default=1)
    @click.pass_context
    def dist(ctx, count):
        ctx.forward(test)
        ctx.invoke(test, count=42)

    result = runner.invoke(cli, ['dist'])
    assert not result.exception
    assert result.output == 'Count: 1\nCount: 42\n'


def test_auto_shorthelp(runner):
    @click.group()
    def cli():
        pass

    @cli.command()
    def short():
        """This is a short text."""

    @cli.command()
    def long():
        """This is a long text that is too long to show as short help
        and will be truncated instead."""

    result = runner.invoke(cli, ['--help'])
    assert re.search(
        r'Commands:\n\s+'
        r'long\s+This is a long text that is too long to show\.\.\.\n\s+'
        r'short\s+This is a short text\.', result.output) is not None


def test_default_maps(runner):
    @click.group()
    def cli():
        pass

    @cli.command()
    @click.option('--name', default='normal')
    def foo(name):
        click.echo(name)

    result = runner.invoke(cli, ['foo'], default_map={
        'foo': {'name': 'changed'}
    })

    assert not result.exception
    assert result.output == 'changed\n'


def test_group_with_args(runner):
    @click.group()
    @click.argument('obj')
    def cli(obj):
        click.echo('obj=%s' % obj)

    @cli.command()
    def move():
        click.echo('move')

    result = runner.invoke(cli, [])
    assert result.exit_code == 0
    assert 'Show this message and exit.' in result.output

    result = runner.invoke(cli, ['obj1'])
    assert result.exit_code == 2
    assert 'Error: Missing command.' in result.output

    result = runner.invoke(cli, ['obj1', '--help'])
    assert result.exit_code == 0
    assert 'Show this message and exit.' in result.output

    result = runner.invoke(cli, ['obj1', 'move'])
    assert result.exit_code == 0
    assert result.output == 'obj=obj1\nmove\n'


def test_base_command(runner):
    import optparse

    @click.group()
    def cli():
        pass

    class OptParseCommand(click.BaseCommand):

        def __init__(self, name, parser, callback):
            click.BaseCommand.__init__(self, name)
            self.parser = parser
            self.callback = callback

        def parse_args(self, ctx, args):
            try:
                opts, args = parser.parse_args(args)
            except Exception as e:
                ctx.fail(str(e))
            ctx.args = args
            ctx.params = vars(opts)

        def get_usage(self, ctx):
            return self.parser.get_usage()

        def get_help(self, ctx):
            return self.parser.format_help()

        def invoke(self, ctx):
            ctx.invoke(self.callback, ctx.args, **ctx.params)

    parser = optparse.OptionParser(usage='Usage: foo test [OPTIONS]')
    parser.add_option("-f", "--file", dest="filename",
                      help="write report to FILE", metavar="FILE")
    parser.add_option("-q", "--quiet",
                      action="store_false", dest="verbose", default=True,
                      help="don't print status messages to stdout")

    def test_callback(args, filename, verbose):
        click.echo(' '.join(args))
        click.echo(filename)
        click.echo(verbose)
    cli.add_command(OptParseCommand('test', parser, test_callback))

    result = runner.invoke(cli, ['test', '-f', 'test.txt', '-q',
                                 'whatever.txt', 'whateverelse.txt'])
    assert not result.exception
    assert result.output.splitlines() == [
        'whatever.txt whateverelse.txt',
        'test.txt',
        'False',
    ]

    result = runner.invoke(cli, ['test', '--help'])
    assert not result.exception
    assert result.output.splitlines() == [
        'Usage: foo test [OPTIONS]',
        '',
        'Options:',
        '  -h, --help            show this help message and exit',
        '  -f FILE, --file=FILE  write report to FILE',
        '  -q, --quiet           don\'t print status messages to stdout',
    ]

########NEW FILE########
__FILENAME__ = test_compat
import click


def test_legacy_callbacks(runner):
    def legacy_callback(ctx, value):
        return value.upper()

    @click.command()
    @click.option('--foo', callback=legacy_callback)
    def cli(foo):
        click.echo(foo)

    result = runner.invoke(cli, ['--foo', 'wat'])
    assert result.exit_code == 0
    assert 'WAT' in result.output
    assert 'Invoked legacy parameter callback' in result.output

########NEW FILE########
__FILENAME__ = test_context
# -*- coding: utf-8 -*-
import click


def test_ensure_context_objects(runner):
    class Foo(object):
        def __init__(self):
            self.title = 'default'

    pass_foo = click.make_pass_decorator(Foo, ensure=True)

    @click.group()
    @pass_foo
    def cli(foo):
        pass

    @cli.command()
    @pass_foo
    def test(foo):
        click.echo(foo.title)

    result = runner.invoke(cli, ['test'])
    assert not result.exception
    assert result.output == 'default\n'


def test_get_context_objects(runner):
    class Foo(object):
        def __init__(self):
            self.title = 'default'

    pass_foo = click.make_pass_decorator(Foo, ensure=True)

    @click.group()
    @click.pass_context
    def cli(ctx):
        ctx.obj = Foo()
        ctx.obj.title = 'test'

    @cli.command()
    @pass_foo
    def test(foo):
        click.echo(foo.title)

    result = runner.invoke(cli, ['test'])
    assert not result.exception
    assert result.output == 'test\n'


def test_get_context_objects_no_ensuring(runner):
    class Foo(object):
        def __init__(self):
            self.title = 'default'

    pass_foo = click.make_pass_decorator(Foo)

    @click.group()
    @click.pass_context
    def cli(ctx):
        ctx.obj = Foo()
        ctx.obj.title = 'test'

    @cli.command()
    @pass_foo
    def test(foo):
        click.echo(foo.title)

    result = runner.invoke(cli, ['test'])
    assert not result.exception
    assert result.output == 'test\n'


def test_get_context_objects_missing(runner):
    class Foo(object):
        pass

    pass_foo = click.make_pass_decorator(Foo)

    @click.group()
    @click.pass_context
    def cli(ctx):
        pass

    @cli.command()
    @pass_foo
    def test(foo):
        click.echo(foo.title)

    result = runner.invoke(cli, ['test'])
    assert result.exception is not None
    assert isinstance(result.exception, RuntimeError)
    assert "Managed to invoke callback without a context object " \
        "of type 'Foo' existing" in str(result.exception)

########NEW FILE########
__FILENAME__ = test_formatting
# -*- coding: utf-8 -*-
import click


def test_basic_functionality(runner):
    @click.command()
    def cli():
        """First paragraph.

        This is a very long second
        paragraph and not correctly
        wrapped but it will be rewrapped.

        \b
        This is
        a paragraph
        without rewrapping.

        \b
        1
         2
          3

        And this is a paragraph
        that will be rewrapped again.
        """

    result = runner.invoke(cli, ['--help'], terminal_width=60)
    assert not result.exception
    assert result.output.splitlines() == [
        'Usage: cli [OPTIONS]',
        '',
        '  First paragraph.',
        '',
        '  This is a very long second paragraph and not correctly',
        '  wrapped but it will be rewrapped.',
        '',
        '  This is',
        '  a paragraph',
        '  without rewrapping.',
        '',
        '  1',
        '   2',
        '    3',
        '',
        '  And this is a paragraph that will be rewrapped again.',
        '',
        'Options:',
        '  --help  Show this message and exit.',
    ]

########NEW FILE########
__FILENAME__ = test_options
# -*- coding: utf-8 -*-
import re
import os
import click


def test_prefixes(runner):
    @click.command()
    @click.option('++foo', is_flag=True, help='das foo')
    @click.option('--bar', is_flag=True, help='das bar')
    def cli(foo, bar):
        click.echo('foo=%s bar=%s' % (foo, bar))

    result = runner.invoke(cli, ['++foo', '--bar'])
    assert not result.exception
    assert result.output == 'foo=True bar=True\n'

    result = runner.invoke(cli, ['--help'])
    assert re.search(r'\+\+foo\s+das foo', result.output) is not None
    assert re.search(r'--bar\s+das bar', result.output) is not None


def test_counting(runner):
    @click.command()
    @click.option('-v', count=True, help='Verbosity',
                  type=click.IntRange(0, 3))
    def cli(v):
        click.echo('verbosity=%d' % v)

    result = runner.invoke(cli, ['-vvv'])
    assert not result.exception
    assert result.output == 'verbosity=3\n'

    result = runner.invoke(cli, ['-vvvv'])
    assert result.exception
    assert 'Invalid value for "-v": 4 is not in the valid range of 0 to 3.' \
        in result.output

    result = runner.invoke(cli, [])
    assert not result.exception
    assert result.output == 'verbosity=0\n'


def test_multiple_required(runner):
    @click.command()
    @click.option('-m', '--message', multiple=True, required=True)
    def cli(message):
        click.echo('\n'.join(message))

    result = runner.invoke(cli, ['-m', 'foo', '-mbar'])
    assert not result.exception
    assert result.output == 'foo\nbar\n'

    result = runner.invoke(cli, [])
    assert result.exception
    assert 'Error: Missing option "-m" / "--message".' in result.output


def test_multiple_envvar(runner):
    @click.command()
    @click.option('--arg', multiple=True)
    def cmd(arg):
        click.echo('|'.join(arg))

    result = runner.invoke(cmd, [], auto_envvar_prefix='TEST',
                           env={'TEST_ARG': 'foo bar baz'})
    assert not result.exception
    assert result.output == 'foo|bar|baz\n'

    @click.command()
    @click.option('--arg', multiple=True, envvar='X')
    def cmd(arg):
        click.echo('|'.join(arg))

    result = runner.invoke(cmd, [], env={'X': 'foo bar baz'})
    assert not result.exception
    assert result.output == 'foo|bar|baz\n'

    @click.command()
    @click.option('--arg', multiple=True, type=click.Path())
    def cmd(arg):
        click.echo('|'.join(arg))

    result = runner.invoke(cmd, [], auto_envvar_prefix='TEST',
                           env={'TEST_ARG': 'foo%sbar' % os.path.pathsep})
    assert not result.exception
    assert result.output == 'foo|bar\n'


def test_nargs_envvar(runner):
    @click.command()
    @click.option('--arg', nargs=2)
    def cmd(arg):
        click.echo('|'.join(arg))

    result = runner.invoke(cmd, [], auto_envvar_prefix='TEST',
                           env={'TEST_ARG': 'foo bar'})
    assert not result.exception
    assert result.output == 'foo|bar\n'

    @click.command()
    @click.option('--arg', nargs=2, multiple=True)
    def cmd(arg):
        for item in arg:
            click.echo('|'.join(item))

    result = runner.invoke(cmd, [], auto_envvar_prefix='TEST',
                           env={'TEST_ARG': 'x 1 y 2'})
    assert not result.exception
    assert result.output == 'x|1\ny|2\n'


def test_custom_validation(runner):
    def validate_pos_int(ctx, value):
        if value < 0:
            raise click.BadParameter('Value needs to be positive')
        return value

    @click.command()
    @click.option('--foo', callback=validate_pos_int, default=1)
    def cmd(foo):
        click.echo(foo)

    result = runner.invoke(cmd, ['--foo', '-1'])
    assert 'Invalid value for "--foo": Value needs to be positive' \
        in result.output

    result = runner.invoke(cmd, ['--foo', '42'])
    assert result.output == '42\n'

########NEW FILE########
__FILENAME__ = test_testing
import click

from click.testing import CliRunner

from click._compat import PY2

# Use the most reasonable io that users would use for the python version.
if PY2:
    from cStringIO import StringIO as ReasonableBytesIO
else:
    from io import BytesIO as ReasonableBytesIO


def test_runner():
    @click.command()
    def test():
        i = click.get_binary_stream('stdin')
        o = click.get_binary_stream('stdout')
        while 1:
            chunk = i.read(4096)
            if not chunk:
                break
            o.write(chunk)
            o.flush()

    runner = CliRunner()
    result = runner.invoke(test, input='Hello World!\n')
    assert not result.exception
    assert result.output == 'Hello World!\n'

    runner = CliRunner(echo_stdin=True)
    result = runner.invoke(test, input='Hello World!\n')
    assert not result.exception
    assert result.output == 'Hello World!\nHello World!\n'


def test_runner_with_stream():
    @click.command()
    def test():
        i = click.get_binary_stream('stdin')
        o = click.get_binary_stream('stdout')
        while 1:
            chunk = i.read(4096)
            if not chunk:
                break
            o.write(chunk)
            o.flush()

    runner = CliRunner()
    result = runner.invoke(test, input=ReasonableBytesIO(b'Hello World!\n'))
    assert not result.exception
    assert result.output == 'Hello World!\n'

    runner = CliRunner(echo_stdin=True)
    result = runner.invoke(test, input=ReasonableBytesIO(b'Hello World!\n'))
    assert not result.exception
    assert result.output == 'Hello World!\nHello World!\n'


def test_prompts():
    @click.command()
    @click.option('--foo', prompt=True)
    def test(foo):
        click.echo('foo=%s' % foo)

    runner = CliRunner()
    result = runner.invoke(test, input='wau wau\n')
    assert not result.exception
    assert result.output == 'Foo: wau wau\nfoo=wau wau\n'

    @click.command()
    @click.option('--foo', prompt=True, hide_input=True)
    def test(foo):
        click.echo('foo=%s' % foo)

    runner = CliRunner()
    result = runner.invoke(test, input='wau wau\n')
    assert not result.exception
    assert result.output == 'Foo: \nfoo=wau wau\n'

########NEW FILE########
__FILENAME__ = test_utils
import sys
import click


def test_echo(runner):
    with runner.isolation() as out:
        click.echo(u'\N{SNOWMAN}')
        click.echo(b'\x44\x44')
        click.echo(42, nl=False)
        click.echo(b'a', nl=False)
        click.echo('\x1b[31mx\x1b[39m', nl=False)
        bytes = out.getvalue()
        assert bytes == b'\xe2\x98\x83\nDD\n42ax'

    # If we are on python 2 we expect that writing bytes into a string io
    # does not do anything crazy.  On Python 3
    if sys.version_info[0] == 2:
        import StringIO
        sys.stdout = x = StringIO.StringIO()
        try:
            click.echo('\xf6')
        finally:
            sys.stdout = sys.__stdout__
        assert x.getvalue() == '\xf6\n'

    # And in any case, if wrapped, we expect bytes to survive.
    @click.command()
    def cli():
        click.echo(b'\xf6')
    result = runner.invoke(cli, [])
    assert result.output_bytes == b'\xf6\n'

    # Ensure we do not strip for bytes.
    with runner.isolation() as out:
        click.echo(bytearray(b'\x1b[31mx\x1b[39m'), nl=False)
        assert out.getvalue() == b'\x1b[31mx\x1b[39m'


def test_styling():
    examples = [
        ('x', dict(fg='black'), '\x1b[30mx\x1b[0m'),
        ('x', dict(fg='red'), '\x1b[31mx\x1b[0m'),
        ('x', dict(fg='green'), '\x1b[32mx\x1b[0m'),
        ('x', dict(fg='yellow'), '\x1b[33mx\x1b[0m'),
        ('x', dict(fg='blue'), '\x1b[34mx\x1b[0m'),
        ('x', dict(fg='magenta'), '\x1b[35mx\x1b[0m'),
        ('x', dict(fg='cyan'), '\x1b[36mx\x1b[0m'),
        ('x', dict(fg='white'), '\x1b[37mx\x1b[0m'),
        ('x', dict(bg='black'), '\x1b[40mx\x1b[0m'),
        ('x', dict(bg='red'), '\x1b[41mx\x1b[0m'),
        ('x', dict(bg='green'), '\x1b[42mx\x1b[0m'),
        ('x', dict(bg='yellow'), '\x1b[43mx\x1b[0m'),
        ('x', dict(bg='blue'), '\x1b[44mx\x1b[0m'),
        ('x', dict(bg='magenta'), '\x1b[45mx\x1b[0m'),
        ('x', dict(bg='cyan'), '\x1b[46mx\x1b[0m'),
        ('x', dict(bg='white'), '\x1b[47mx\x1b[0m'),
        ('foo bar', dict(blink=True), '\x1b[5mfoo bar\x1b[0m'),
        ('foo bar', dict(underline=True), '\x1b[4mfoo bar\x1b[0m'),
        ('foo bar', dict(bold=True), '\x1b[1mfoo bar\x1b[0m'),
        ('foo bar', dict(dim=True), '\x1b[2mfoo bar\x1b[0m'),
    ]
    for text, styles, ref in examples:
        assert click.style(text, **styles) == ref
        assert click.unstyle(ref) == text


def test_filename_formatting():
    assert click.format_filename(b'foo.txt') == 'foo.txt'
    assert click.format_filename(b'/x/foo.txt') == '/x/foo.txt'
    assert click.format_filename(u'/x/foo.txt') == '/x/foo.txt'
    assert click.format_filename(u'/x/foo.txt', shorten=True) == 'foo.txt'
    assert click.format_filename(b'/x/foo\xff.txt', shorten=True) \
        == u'foo\ufffd.txt'


def test_prompts(runner):
    @click.command()
    def test():
        if click.confirm('Foo'):
            click.echo('yes!')
        else:
            click.echo('no :(')

    result = runner.invoke(test, input='y\n')
    assert not result.exception
    assert result.output == 'Foo [y/N]: y\nyes!\n'

    result = runner.invoke(test, input='\n')
    assert not result.exception
    assert result.output == 'Foo [y/N]: \nno :(\n'

    result = runner.invoke(test, input='n\n')
    assert not result.exception
    assert result.output == 'Foo [y/N]: n\nno :(\n'

    @click.command()
    def test_no():
        if click.confirm('Foo', default=True):
            click.echo('yes!')
        else:
            click.echo('no :(')

    result = runner.invoke(test_no, input='y\n')
    assert not result.exception
    assert result.output == 'Foo [Y/n]: y\nyes!\n'

    result = runner.invoke(test_no, input='\n')
    assert not result.exception
    assert result.output == 'Foo [Y/n]: \nyes!\n'

    result = runner.invoke(test_no, input='n\n')
    assert not result.exception
    assert result.output == 'Foo [Y/n]: n\nno :(\n'

########NEW FILE########
