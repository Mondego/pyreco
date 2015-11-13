__FILENAME__ = errors
# clize -- A command-line argument parser for Python
# Copyright (C) 2013 by Yann Kaiser <kaiser.yann@gmail.com>
# See COPYING for details.

from functools import partial

from clize import util


class UserError(ValueError):
    """An error to be printed to the user."""

    def __str__(self):
        return self.prefix_with_pname(super(UserError, self).__str__())

    def prefix_with_pname(self, message):
        return '{0}: {1}'.format(self.get_pname('Error'), message)

    def get_pname(self, default='command'):
        try:
            return self.pname
        except AttributeError:
            return default


class ArgumentError(UserError):
    """An error related to the arguments passed through the command-line
    interface"""
    def __init__(self, message=None):
        if message is not None:
            self.message = message

    def __str__(self):
        usage = ''
        try:
            usage = '\n' + '\n'.join(
                self.cli.helper.show_usage(self.get_pname()))
        except Exception:
            pass
        return self.prefix_with_pname(self.message + usage)


class MissingRequiredArguments(ArgumentError):
    """Raised when required parameters have not been provided an argument"""

    def __init__(self, missing):
        self.missing = missing

    @property
    def message(self):
        return "Missing required arguments: {0}".format(
                    ', '.join(arg.display_name for arg in self.missing))


class TooManyArguments(ArgumentError):
    """Raised when too many positional arguments have been passed for the
    parameters to consume."""

    def __init__(self, extra):
        self.extra = extra

    @property
    def message(self):
        return "Received extra arguments: {0}".format(
                    ' '.join(self.extra))


class DuplicateNamedArgument(ArgumentError):
    """Raised when a named option or flag has been passed twice."""

    @property
    def message(self):
        return "{0} was specified more than once".format(
            self.param.aliases[0])


class UnknownOption(ArgumentError):
    """Raised when a named argument has no matching parameter."""

    def __init__(self, name):
        self.name = name

    @property
    def message(self):
        return "Unknown option {0!r}".format(self.name)


class MissingValue(ArgumentError):
    """Raised when an option received no value."""

    @property
    def message(self):
        return "No value found after {0}".format(self.param.display_name)


class BadArgumentFormat(ArgumentError):
    """Raised when an argument cannot be converted to the correct format."""

    def __init__(self, typ, val):
        self.typ = typ
        self.val = val

    @property
    def message(self):
        return "Bad format for {0}: {1!r}".format(
            util.name_type2cli(self.typ), self.val)


class ArgsBeforeAlternateCommand(ArgumentError):
    """Raised when there are arguments before a non-fallback alternate
    command."""
    def __init__(self, param):
        self.param = param

    @property
    def message(self):
        return "Arguments found before alternate action parameter {0}".format(
            self.param.display_name)


class SetErrorContext(object):
    """Context manager that sets attributes on exceptions that are raised
    past it"""

    def __init__(self, exc_type, **attributes):
        """
        :param exc_type: The exception type to operate on.
        :param attributes: The attributes to set on the matching exceptions.
            They will only be set if yet unset on the exception.
        """
        self.exc_type = exc_type
        self.values = attributes

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if isinstance(exc_val, self.exc_type):
            for key, val in self.values.items():
                if not hasattr(exc_val, key):
                    setattr(exc_val, key, val)

SetUserErrorContext = partial(SetErrorContext, UserError)
SetArgumentErrorContext = partial(SetErrorContext, ArgumentError)

########NEW FILE########
__FILENAME__ = help
# clize - automatically generate command-line interfaces from callables
# clize -- A command-line argument parser for Python
# Copyright (C) 2013 by Yann Kaiser <kaiser.yann@gmail.com>
# See COPYING for details.

from __future__ import unicode_literals

import itertools
from functools import partial
import inspect
import re

import six
from sigtools.modifiers import annotate, kwoargs
from sigtools.wrappers import wrappers

from clize import runner, parser, util

def lines_to_paragraphs(L):
    return list(itertools.chain.from_iterable((x, '') for x in L))

p_delim = re.compile(r'\n\s*\n')

class Help(object):

    def __init__(self, subject, owner):
        self.subject = subject
        self.owner = owner

    @util.property_once
    def header(self):
        self.prepare()
        return self.__dict__['header']

    def prepare(self):
        """Override for stuff to be done once per subject"""

    @runner.Clize(pass_name=True, hide_help=True)
    @kwoargs('usage')
    @annotate(args=parser.Parameter.UNDOCUMENTED)
    def cli(self, name, usage=False, *args):
        """Show the help

        usage: Only show the full usage
        """
        name = name.rpartition(' ')[0]
        f = util.Formatter()
        if usage:
            f.extend(self.show_full_usage(name))
        else:
            f.extend(self.show(name))
        return six.text_type(f)

def update_new(target, other):
    for key, val in six.iteritems(other):
        if key not in target:
            target[key] = val

def split_docstring(s):
    if not s:
        return
    code_coming = False
    code = False
    for p in p_delim.split(s):
        if code_coming or code and p.startswith(' '):
            yield p
            code_coming = False
            code = True
        else:
            item = ' '.join(p.split())
            if item.endswith(':'):
                code_coming = True
            code = False
            yield item


class ClizeHelp(Help):
    @property
    def signature(self):
        return self.subject.signature

    @classmethod
    def get_arg_type(cls, arg):
        if arg.kwarg:
            if arg.func:
                return 'alt'
            else:
                return 'opt'
        else:
            return 'pos'

    @classmethod
    def filter_undocumented(cls, params):
        for param in params:
            if not param.undocumented:
                yield param

    def prepare(self):
        self.arguments = {
            'pos': list(self.filter_undocumented(self.signature.positional)),
            'opt': list(self.filter_undocumented(self.signature.named)),
            'alt': list(self.filter_undocumented(self.signature.alternate)),
            }
        self.header, self.arghelp, self.before, self.after, self.footer = \
            self.parse_help()
        self.order = list(self.arghelp.keys())

    def parse_func_help(self, obj):
        return self.parse_docstring(inspect.getdoc(obj))

    argdoc_re = re.compile('^([a-zA-Z_]+): ?(.+)$')
    def parse_docstring(self, s):
        header = []
        arghelp = util.OrderedDict()
        before = {}
        after = {}
        last_arghelp = None
        cur_after = []
        for p in split_docstring(s):
            argdoc = self.argdoc_re.match(p)
            if argdoc:
                argname, text = argdoc.groups()
                arghelp[argname] = text
                if cur_after:
                    prev, this = cur_after, None
                    if prev[-1].endswith(':'):
                        this = [prev.pop()]
                    if last_arghelp:
                        after[last_arghelp] = cur_after
                    else:
                        header.extend(cur_after)
                    if this:
                        before[argname] = this
                    cur_after = []
                last_arghelp = argname
            else:
                cur_after.append(p)
        if not arghelp:
            header = cur_after
            footer = []
        else:
            footer = cur_after
        return (
            lines_to_paragraphs(header), arghelp, before, after,
            lines_to_paragraphs(footer)
            )

    def parse_help(self):
        header, arghelp, before, after, footer = \
            self.parse_func_help(self.subject.func)
        for wrapper in wrappers(self.subject.func):
            _, w_arghelp, w_before, w_after, _ = \
                self.parse_func_help(wrapper)
            update_new(arghelp, w_arghelp)
            update_new(before, w_before)
            update_new(after, w_after)
        return header, arghelp, before, after, footer

    @property
    def description(self):
        try:
            return self.header[0]
        except IndexError:
            return ''

    def show_usage(self, name):
        return 'Usage: {0} {1}{2}'.format(
            name,
            '[OPTIONS] ' if self.signature.named else '',
            ' '.join(str(arg)
                     for arg in self.signature.positional)
            ),

    def alternates_with_helper(self):
        for param in self.signature.alternate:
            if param.undocumented:
                continue
            try:
                helper = param.func.helper
            except AttributeError:
                pass
            else:
                yield param, param.display_name, helper

    def usages(self, name):
        yield name, str(self.signature)
        for param, subname, helper in self.alternates_with_helper():
            for usage in helper.usages(' '.join((name, subname))):
                yield usage

    def show_full_usage(self, name):
        for name, usage in self.usages(name):
            yield ' '.join((name, usage))

    def docstring_index(self, param):
        name = getattr(param, 'argument_name', param.display_name)
        try:
            return self.order.index(name), name
        except ValueError:
            return float('inf'), name

    kind_order = [
        ('pos', 'Positional arguments:'),
        ('opt', 'Options:'),
        ('alt', 'Other actions:'),
        ]
    def show_arguments(self):
        f = util.Formatter()
        with f.columns() as cols:
            for key, message in self.kind_order:
                f.new_paragraph()
                if key in self.arguments and self.arguments[key]:
                    if key == 'opt':
                        params = sorted(self.arguments[key],
                                        key=self.docstring_index)
                    else:
                        params = self.arguments[key]
                    if getattr(params[0], 'argument_name', None
                            ) not in self.before:
                        f.append(message)
                    with f.indent():
                        for arg in params:
                            self.show_argument(arg, f, cols)
        return f

    def show_argument(self, param, f, cols):
        name = getattr(param, 'argument_name', None)
        if name in self.before:
            for p in self.before[name]:
                f.new_paragraph()
                f.append(p, indent=-2)
        desc = getattr(param, 'description', None)
        if desc is None:
            desc = self.arghelp.get(name, '')
        if getattr(param, 'default', None) in (util.UNSET, None, False, ''):
            default = ''
        else:
            default = "((default: {0})".format(param.default)
        cols.append(param.full_name, desc + default)
        if name in self.after:
            for p in self.after[name]:
                f.new_paragraph()
                f.append(p, indent=-2)
            f.new_paragraph()

    def show(self, name):
        f = util.Formatter()
        for iterable in (self.show_usage(name), self.header,
                         self.show_arguments(), self.footer):
            f.extend(iterable)
            f.new_paragraph()
        return f

class DispatcherHelper(Help):
    def show_commands(self):
        f = util.Formatter()
        f.append('Commands:')
        with f.indent():
            with f.columns() as cols:
                for names, command in self.owner.cmds.items():
                    cols.append(', '.join(names), command.helper.description)
        return f

    def prepare_notes(self, doc):
        if doc is None:
            return ()
        else:
            return lines_to_paragraphs(split_docstring(inspect.cleandoc(doc)))

    def prepare(self):
        self.header = self.prepare_notes(self.owner.description)
        self.footer = self.prepare_notes(self.owner.footnotes)

    def show(self, name):
        f = util.Formatter()
        for text in (self.show_usage(name), self.header,
                     self.show_commands(), self.footer):
            f.extend(text)
            f.new_paragraph()
        return f

    def show_usage(self, name):
        yield 'Usage: {0} command [args...]'.format(name)

    def subcommands_with_helper(self):
        for names, subcommand in self.owner.cmds.items():
            try:
                helper = subcommand.helper
            except AttributeError:
                pass
            else:
                yield names, subcommand, helper

    def usages(self, name):
        if self.subject.help_aliases:
            help_name = ' '.join((name, self.subject.help_aliases[0]))
            yield help_name, str(self.cli.signature)
        for names, subcommand, helper in self.subcommands_with_helper():
            for usage in helper.usages(' '.join((name, names[0]))):
                yield usage

    def show_full_usage(self, name):
        for name, usage in self.usages(name):
            yield ' '.join((name, usage))

########NEW FILE########
__FILENAME__ = legacy
# clize -- A command-line argument parser for Python
# Copyright (C) 2013 by Yann Kaiser <kaiser.yann@gmail.com>
# See COPYING for details.

import warnings
from functools import partial
from itertools import chain
from collections import defaultdict

from sigtools.specifiers import forwards_to
from sigtools.modifiers import autokwoargs, annotate

from clize import runner, parser, util


def _clize(fn, alias={}, force_positional=(), coerce={},
           require_excess=False, extra=(),
           use_kwoargs=None):
    sig = util.funcsigs.signature(fn)
    has_kwoargs = False
    annotations = defaultdict(list)
    ann_positional = []
    for param in sig.parameters.values():
        if param.kind == param.KEYWORD_ONLY:
            has_kwoargs = True
        elif require_excess and param.kind == param.VAR_POSITIONAL:
            annotations[param.name].append(parser.Parameter.REQUIRED)
        if param.annotation != param.empty:
            ann = util.maybe_iter(param.annotation)
            annotations[param.name].extend(ann)
            if clize.POSITIONAL in ann:
                ann_positional.append(param.name)
                annotations[param.name].remove(clize.POSITIONAL)
    for name, aliases in alias.items():
        annotations[name].extend(aliases)
    for name, func in coerce.items():
        annotations[name].append(func)
    annotate(**annotations)(fn)
    use_kwoargs = has_kwoargs if use_kwoargs is None else use_kwoargs
    if not use_kwoargs:
        fn = autokwoargs(
            exceptions=chain(ann_positional, force_positional))(fn)
    return runner.Clize(fn, extra=extra)


@forwards_to(_clize, 1)
def clize(fn=None, **kwargs):
    """Compatibility with clize<3.0 releases. Decorates a function in order
    to be passed to `clize.run`. See :ref:`porting-2`."""
    warnings.warn('Use clize.Clize instead of clize.clize, or pass the '
                  'function directly to run(), undecorated.',
                  DeprecationWarning, stacklevel=2)
    if fn is None:
        return partial(_clize, **kwargs)
    else:
        return _clize(fn, **kwargs)

clize.kwo = partial(clize, use_kwoargs=True)
clize.POSITIONAL = clize.P = parser.ParameterFlag('POSITIONAL',
                                                  'clize.legacy.clize')


class MakeflagParameter(parser.NamedParameter):
    """Parameter class that imitates those returned by Clize 2's `make_flag`
    when passed a callable for source. See :ref:`porting-2`."""
    def __init__(self, func, **kwargs):
        super(MakeflagParameter, self).__init__(**kwargs)
        self.func = func

    def noop(self, *args, **kwargs):
        pass

    def read_argument(self, args, i, ba):
        try:
            val = args[i + 1]
            skip = 1
        except IndexError:
            val = True
            skip = 0
        ret = self.func(name=ba.name, command=ba.sig,
                        val=val, params=ba.kwargs)
        if ret:
            func = self.noop
        else:
            func = None
        return skip, None, None, func



def make_flag(source, names, default=False, type=bool,
              help='', takes_argument=0):
    """Compatibility with clize<3.0 releases. Creates a parameter instance.
    See :ref:`porting-2`."""
    warnings.warn('Compatibility with clize<3.0 releases. Helper function to '
                  'create alternate actions. See :ref:`porting-2`.',
                  DeprecationWarning, stacklevel=1)
    kwargs = {}
    kwargs['aliases'] = [util.name_py2cli(alias, kw=True)
                         for alias in names]
    if callable(source):
        return MakeflagParameter(source, **kwargs)
    cls = parser.OptionParameter
    kwargs['argument_name'] = source
    kwargs['default'] = default
    if not takes_argument:
        return parser.FlagParameter(value=True, **kwargs)
    kwargs['typ'] = type
    if type is int:
        cls = parser.IntOptionParameter
    return cls(**kwargs)

########NEW FILE########
__FILENAME__ = parser
# clize -- A command-line argument parser for Python
# Copyright (C) 2013 by Yann Kaiser <kaiser.yann@gmail.com>
# See COPYING for details.

"""
interpret function signatures and read commandline arguments
"""

import itertools

import six

from clize import errors, util

funcsigs = util.funcsigs


class ParameterFlag(object):
    def __init__(self, name, prefix='clize.Parameter'):
        self.name = name
        self.prefix = prefix

    def __repr__(self):
        return '{0.prefix}.{0.name}'.format(self)


class Parameter(object):
    """Represents a CLI parameter.

    :param str display_name: The 'default' representation of the parameter.
    :param bool undocumented:
        If true, hides the parameter from the command help.
    :param last_option: 
    """

    required = False

    def __init__(self, display_name, undocumented=False, last_option=None):
        self.display_name = display_name
        self.undocumented = undocumented
        self.last_option = last_option

    @classmethod
    def from_parameter(self, param):
        """"""
        if param.annotation != param.empty:
            annotations = util.maybe_iter(param.annotation)
        else:
            annotations = []

        named = param.kind in (param.KEYWORD_ONLY, param.VAR_KEYWORD)
        aliases = [param.name]
        default = util.UNSET
        typ = util.identity

        kwargs = {
            'argument_name': param.name,
            'undocumented': Parameter.UNDOCUMENTED in annotations,
            }

        if param.default is not param.empty:
            if Parameter.REQUIRED not in annotations:
                default = param.default
            if default is not None:
                typ = type(param.default)

        if Parameter.LAST_OPTION in annotations:
            kwargs['last_option'] = True

        set_coerce = False
        for thing in annotations:
            if isinstance(thing, Parameter):
                return thing
            elif callable(thing):
                if set_coerce:
                    raise ValueError(
                        "Coercion function specified twice in annotation: "
                        "{0.__name__} {1.__name__}".format(typ, thing))
                typ = thing
                set_coerce = True
            elif isinstance(thing, six.string_types):
                if not named:
                    raise ValueError("Cannot give aliases for a positional "
                                     "parameter.")
                if len(thing.split()) > 1:
                    raise ValueError("Cannot have whitespace in aliases.")
                aliases.append(thing)
            elif isinstance(thing, ParameterFlag):
                pass
            else:
                raise ValueError(thing)

        if named:
            kwargs['aliases'] = [
                util.name_py2cli(alias, named)
                for alias in aliases]
            if default is False and typ is bool:
                return FlagParameter(value=True, false_value=False, **kwargs)
            else:
                kwargs['default'] = default
                kwargs['typ'] = typ
                if typ is int:
                    return IntOptionParameter(**kwargs)
                else:
                    return OptionParameter(**kwargs)
        else:
            kwargs['display_name'] = util.name_py2cli(param.name)
            if param.kind == param.VAR_POSITIONAL:
                return ExtraPosArgsParameter(
                    required=Parameter.REQUIRED in annotations,
                    typ=typ, **kwargs)
            else:
                return PositionalParameter(default=default, typ=typ, **kwargs)

    R = REQUIRED = ParameterFlag('REQUIRED')
    """Annotate a parameter with this to force it to be required.

    Mostly only useful for ``*args`` parameters. In other cases simply don't
    provide a default value."""

    L = LAST_OPTION = ParameterFlag('LAST_OPTION')
    """Annotate a parameter with this and all following arguments will be
    processed as positional."""

    # I = IGNORE = ParameterFlag('IGNORE')

    U = UNDOCUMENTED = ParameterFlag('UNDOCUMENTED')
    """Parameters annotated with this will be omitted from the
    documentation."""

    # M = MULTIPLE = ParameterFlag('MULTIPLE')

    def read_argument(self, ba, i):
        """Reads one or more arguments from ``ba.in_args`` from position ``i``.

        :param clize.parser.CliBoundArguments ba:
            The bound arguments object this call is expected to mutate.
        :param int i:
            The current position in ``ba.args``.
        """
        raise NotImplementedError

    def apply_generic_flags(self, ba):
        """Called after `read_argument` in order to set attributes on ``ba``
        independently of the arguments.

        :param clize.parser.CliBoundArguments ba:
            The bound arguments object this call is expected to mutate.
        """
        if self.last_option:
            ba.posarg_only = True

    def format_type(self):
        return ''

    @util.property_once
    def full_name(self):
        return self.display_name + self.format_type()

    def __str__(self):
        return self.display_name


class ParameterWithSourceEquivalent(Parameter):
    """Parameter that relates to a function parameter in the source.

    :param str argument_name: The name of the parameter.
    """
    def __init__(self, argument_name, **kwargs):
        super(ParameterWithSourceEquivalent, self).__init__(**kwargs)
        self.argument_name = argument_name


class ParameterWithValue(Parameter):
    """A parameter that stores a value, with possible default and/or
    conversion.

    :param callable typ: A callable to convert the value or raise `ValueError`.
        Defaults to `.util.identity`.
    :param default: A default value for the parameter or `.util.UNSET`.
    """

    def __init__(self, typ=util.identity, default=util.UNSET, **kwargs):
        super(ParameterWithValue, self).__init__(**kwargs)
        self.typ = typ
        self.default = default

    @property
    def required(self):
        """Tells if the parameter has no default value."""
        return self.default is util.UNSET

    def coerce_value(self, arg):
        """Coerces ``arg`` using the ``typ`` function. Raises
        `.errors.BadArgumentFormat` if the coercion function raises
        `ValueError`.
        """
        try:
            return self.typ(arg)
        except ValueError as e:
            exc = errors.BadArgumentFormat(self.typ, arg)
            exc.__cause__ = e
            raise exc

    def format_type(self):
        if (
                self.typ is not util.identity
                and not issubclass(self.typ, six.string_types)
            ):
            return '=' + util.name_type2cli(self.typ)
        return ''

    @util.property_once
    def full_name(self):
        return self.display_name + self.format_type()

    def __str__(self):
        if self.required:
            return self.full_name
        else:
            return '[{0}]'.format(self.full_name)


class PositionalParameter(ParameterWithValue, ParameterWithSourceEquivalent):
    """Equivalent of a positional-only parameter in python."""
    def read_argument(self, ba, i):
        val = self.coerce_value(ba.in_args[i])
        ba.args.append(val)


class NamedParameter(Parameter):
    """Equivalent of a keyword-only parameter in python.

    :param aliases: The arguments that trigger this parameter. The first alias
        is used to refer to the parameter.
    :type aliases: sequence of strings
    """
    def __init__(self, aliases, **kwargs):
        kwargs.setdefault('display_name', aliases[0])
        super(NamedParameter, self).__init__(**kwargs)
        self.aliases = aliases

    __key_count = itertools.count()
    @classmethod
    def alias_key(cls, name):
        """Key function to sort aliases in source order, but with short
        forms(one dash) first."""
        return len(name) - len(name.lstrip('-')), next(cls.__key_count)

    @util.property_once
    def full_name(self):
        return ', '.join(sorted(self.aliases, key=self.alias_key)
            ) + self.format_type()

    def __str__(self):
        return '[{0}]'.format(self.display_name)

    def redispatch_short_arg(self, rest, ba, i):
        """Processes the rest of an argument as if it was a new one prefixed
        with one dash."""
        if not rest:
            return
        try:
            nparam = ba.sig.aliases['-' + rest[0]]
        except KeyError as e:
            raise errors.UnknownOption(e.args[0])
        orig_args = ba.in_args
        ba.in_args = ba.in_args[:i] + ('-' + rest,) + ba.in_args[i + 1:]
        try:
            nparam.read_argument(ba, i)
        finally:
            ba.in_args = orig_args
        ba.unsatisfied.discard(nparam)


class FlagParameter(NamedParameter, ParameterWithSourceEquivalent):
    """A named parameter that takes no argument.

    :param value: The value when the argument is present.
    :param false_value: The value when the argument is given one of the
        false value triggers using ``--param=xyz``.
    """

    false_triggers = '0', 'n', 'no', 'f', 'false'

    def __init__(self, value, false_value, **kwargs):
        super(FlagParameter, self).__init__(**kwargs)
        self.value = value
        self.false_value = false_value

    def read_argument(self, ba, i):
        arg = ba.in_args[i]
        if arg[1] == '-':
            ba.kwargs[self.argument_name] = (
                self.value if self.is_flag_activation(arg)
                else self.false_value
                )
        else:
            ba.kwargs[self.argument_name] = self.value
            self.redispatch_short_arg(arg[2:], ba, i)


    def is_flag_activation(self, arg):
        """Checks if an argument triggers the true or false value."""
        if arg[1] != '-':
            return True
        arg, sep, val = arg.partition('=')
        return (
            not sep or
            val and val.lower() not in self.false_triggers
            )

    def format_type(self):
        return ''


class OptionParameter(NamedParameter, ParameterWithValue,
                      ParameterWithSourceEquivalent):
    """A named parameter that takes an argument."""

    def read_argument(self, ba, i):
        if self.argument_name in ba.kwargs:
            raise errors.DuplicateNamedArgument()
        arg = ba.in_args[i]
        if arg.startswith('--'):
            name, glued, val = arg.partition('=')
        else:
            arg = arg.lstrip('-')
            if len(arg) > 1:
                glued = True
                val = arg[1:]
            else:
                glued = False
        if not glued:
            try:
                val = ba.in_args[i+1]
            except IndexError:
                raise errors.MissingValue
        ba.kwargs[self.argument_name] = self.coerce_value(val)
        ba.skip = not glued

    def format_type(self):
        return '=' + util.name_type2cli(self.typ)

    def __str__(self):
        if self.required:
            fmt = '{0}{1}'
        else:
            fmt = '[{0}{1}]'
        return fmt.format(self.display_name, self.format_type())

def split_int_rest(s):
    for i, c, in enumerate(s):
        if not c.isdigit():
            return s[:i], s[i:]

class IntOptionParameter(OptionParameter):
    """A named parameter that takes an integer as argument. The short form
    of it can be chained with the short form of other named parameters."""

    def read_argument(self, ba, i):
        if self.argument_name in ba.kwargs:
            raise errors.DuplicateNamedArgument()
        arg = ba.in_args[i]
        if arg.startswith('--'):
            super(IntOptionParameter, self).read_argument(ba, i)
            return

        arg = arg.lstrip('-')[1:]
        if not arg:
            super(IntOptionParameter, self).read_argument(ba, i)
            return

        val, rest = split_int_rest(arg)
        ba.kwargs[self.argument_name] = self.coerce_value(val)

        self.redispatch_short_arg(rest, ba, i)


class MultiParameter(ParameterWithValue):
    """Parameter that can collect multiple values."""

    def __str__(self):
        return '[{0}...]'.format(self.name)

    def get_collection(self, ba):
        """Return an object that new values will be appended to."""
        raise NotImplementedError

    def read_argument(self, ba, i):
        val = self.coerce_value(ba.in_args[i])
        self.get_collection(ba).append(val)


class MultiOptionParameter(NamedParameter, MultiParameter):
    """Named parameter that can collect multiple values."""

    required = False

    def get_collection(self, ba):
        return ba.kwargs.setdefault(self.argument_name, [])


class EatAllPositionalParameter(MultiParameter):
    """Helper parameter that collects multiple values to be passed as
    positional arguments to the callee."""

    def get_collection(self, ba):
        return ba.args


class EatAllOptionParameterArguments(EatAllPositionalParameter):
    """Helper parameter for .EatAllOptionParameter that adds the remaining
    arguments as positional arguments for the function."""

    def __init__(self, param, **kwargs):
        super(EatAllOptionParameterArguments, self).__init__(
            display_name='...', undocumented=False, **kwargs)
        self.param = param


class IgnoreAllOptionParameterArguments(EatAllOptionParameterArguments):
    """Helper parameter for .EatAllOptionParameter that ignores the remaining
    arguments."""

    def read_argument(self, ba, i):
        pass


class EatAllOptionParameter(MultiOptionParameter):
    """Parameter that collects all remaining arguments as positional
    arguments, even those which look like named arguments."""

    extra_type = EatAllOptionParameterArguments

    def __init__(self, **kwargs):
        super(EatAllOptionParameter, self).__init__(**kwargs)
        self.args_param = self.extra_type(self)

    def read_argument(self, ba, i):
        super(EatAllOptionParameter, self).read_argument(ba, i)
        ba.post_name.append(ba.in_args[i])
        ba.posarg_only = True
        ba.sticky = self.args_param


class FallbackCommandParameter(EatAllOptionParameter):
    """Parameter that sets an alternative function when triggered. When used
    as an argument other than the first all arguments are discarded."""

    def __init__(self, func, **kwargs):
        super(FallbackCommandParameter, self).__init__(**kwargs)
        self.func = func
        self.ignore_all = IgnoreAllOptionParameterArguments(self)

    @util.property_once
    def description(self):
        try:
            return self.func.helper.description
        except AttributeError:
            pass

    def get_collection(self, ba):
        return []

    def read_argument(self, ba, i):
        ba.args[:] = []
        ba.kwargs.clear()
        super(FallbackCommandParameter, self).read_argument(ba, i)
        ba.func = self.func
        if i:
            ba.sticky = self.ignore_all


class AlternateCommandParameter(FallbackCommandParameter):
    """Parameter that sets an alternative function when triggered. When used
    as an argument other than the first all arguments are discarded."""

    def read_argument(self, ba, i):
        if i:
            raise errors.ArgsBeforeAlternateCommand(self)
        return super(AlternateCommandParameter, self).read_argument(ba, i)


class ExtraPosArgsParameter(PositionalParameter):
    """Parameter that forwards all remaining positional arguments to the
    callee."""

    required = None # clear required property from ParameterWithValue

    def __init__(self, required=False, **kwargs):
        super(ExtraPosArgsParameter, self).__init__(**kwargs)
        self.required = required

    def read_argument(self, ba, i):
        super(ExtraPosArgsParameter, self).read_argument(ba, i)
        ba.sticky = self

    def __str__(self):
        if self.required:
            fmt = '{0}...'
        else:
            fmt = '[{0}...]'
        return fmt.format(self.display_name)


class CliSignature(object):
    """A collection of parameters that can be used to translate CLI arguments
    to function arguments.

    :param iterable parameters: The parameters to use.

    .. attribute:: positional

        List of positional parameters.

    .. attribute:: alternate

        List of parameters that initiate an alternate action.

    .. attribute:: named

        List of named parameters that aren't in `.alternate`.

    .. attribute:: aliases
        :annotation: = {}

        Maps parameter names to `Parameter` instances.

    .. attribute:: required
        :annotation: = set()

        A set of all required parameters.
    """

    def __init__(self, parameters):
        pos = self.positional = []
        named = self.named = []
        alt = self.alternate = []
        aliases = self.aliases = {}
        required = self.required = set()
        for param in parameters:
            required_ = getattr(param, 'required', False)
            func = getattr(param, 'func', None)
            aliases_ = getattr(param, 'aliases', None)

            if required_:
                required.add(param)

            if aliases_ is not None:
                for alias in aliases_:
                    aliases[alias] = param

            if func:
                alt.append(param)
            elif aliases_ is not None:
                named.append(param)
            else:
                pos.append(param)

    param_cls = Parameter
    """The parameter class `.from_signature` will use to convert source
    parameters to CLI parameters"""

    @classmethod
    def from_signature(cls, sig, extra=()):
        """Takes a signature object and returns an instance of this class
        derived from it.

        :param inspect.Signature sig: The signature object to use.
        :param iterable extra: Extra parameter instances to include.
        """
        return cls(
            itertools.chain(
                (
                    cls.param_cls.from_parameter(param)
                    for param in sig.parameters.values()
                ), extra))

    def read_arguments(self, args, name='unnamed'):
        """Returns a `.CliBoundArguments` instance for this CLI signature
        bound to the given arguments.

        :param sequence args: The CLI arguments, minus the script name.
        :param str name: The script name.
        """
        return CliBoundArguments(self, args, name)

    def __str__(self):
        return ' '.join(
            str(p)
            for p in itertools.chain(self.named, self.positional)
            if not p.undocumented
            )


class _SeekFallbackCommand(object):
    """Context manager that tries to seek a fallback command if an error was
    raised."""
    def __enter__(self):
        pass

    def __exit__(self, typ, exc, tb):
        if exc is None:
            return
        try:
            pos = exc.pos
            ba = exc.ba
        except AttributeError:
            return

        for i, arg in enumerate(ba.in_args[pos + 1:], pos +1):
            param = ba.sig.aliases.get(arg, None)
            if param in ba.sig.alternate:
                try:
                    param.read_argument(ba, i)
                except errors.ArgumentError:
                    continue
                ba.unsatisfied.clear()
                return True


class CliBoundArguments(object):
    """Command line arguments bound to a `.CliSignature` instance.

    :param CliSignature sig: The signature to bind against.
    :param sequence args: The CLI arguments, minus the script name.
    :param str name: The script name.

    .. attribute:: sig

        The signature being bound to.

    .. attribute:: in_args

        The CLI arguments, minus the script name.

    .. attribute:: name

        The script name.

    .. attribute:: args
        :annotation: = []

        List of arguments to pass to the target function.

    .. attribute:: kwargs
        :annotation: = {}

        Mapping of named arguments to pass to the target function.

    .. attribute:: func
        :annotation: = None

        If not `None`, replaces the target function.

    .. attribute:: post_name
        :annotation: = []

        List of words to append to the script name when passed to the target
        function.

    The following attributes only exist while arguments are being processed:

    .. attribute:: sticky
       :annotation: = None

       If not `None`, a parameter that will keep receiving positional
       arguments.

    .. attribute:: posarg_only
       :annotation: = False

       Arguments will always be processed as positional when this is set to
       `True`.

    .. attribute:: skip
       :annotation: = 0

       Amount of arguments to skip.

    .. attribute:: unsatisfied
       :annotation: = set(<required parameters>)

       Required parameters that haven't yet been satisfied.

    """


    def __init__(self, sig, args, name):
        self.sig = sig
        self.name = name
        self.in_args = args
        self.func = None
        self.post_name = []
        self.args = []
        self.kwargs = {}

        self.sticky = None
        self.posarg_only = False
        self.skip = 0
        self.unsatisfied = set(self.sig.required)

        posparam = iter(self.sig.positional)

        with _SeekFallbackCommand():
            for i, arg in enumerate(self.in_args):
                if self.skip > 0:
                    self.skip -= 1
                    continue
                with errors.SetArgumentErrorContext(pos=i, val=arg, ba=self):
                    if self.posarg_only or arg[0] != '-' or len(arg) < 2:
                        if self.sticky is not None:
                            param = self.sticky
                        else:
                            try:
                                param = next(posparam)
                            except StopIteration:
                                exc = errors.TooManyArguments(self.in_args[i:])
                                exc.__cause__ = None
                                raise exc
                    elif arg == '--':
                        self.posarg_only = True
                        continue
                    else:
                        if arg.startswith('--'):
                            name = arg.partition('=')[0]
                        else:
                            name = arg[:2]
                        try:
                            param = self.sig.aliases[name]
                        except KeyError:
                            raise errors.UnknownOption(name)
                    with errors.SetArgumentErrorContext(param=param):
                        param.read_argument(self, i)
                        self.unsatisfied.discard(param)
                        param.apply_generic_flags(self)

        if self.unsatisfied and not self.func:
            raise errors.MissingRequiredArguments(self.unsatisfied)

        del self.sticky, self.posarg_only, self.skip, self.unsatisfied

    def __iter__(self):
        yield self.func
        yield self.post_name
        yield self.args
        yield self.kwargs

########NEW FILE########
__FILENAME__ = runner
# clize -- A command-line argument parser for Python
# Copyright (C) 2013 by Yann Kaiser <kaiser.yann@gmail.com>
# See COPYING for details.

from __future__ import print_function

import sys
import os
from functools import partial, update_wrapper
import operator
import itertools

import six
from sigtools.modifiers import annotate, autokwoargs
from sigtools.specifiers import forwards_to_method
from sigtools.signatures import mask

from clize import util, errors, parser

funcsigs = util.funcsigs

class _CliWrapper(object):
    def __init__(self, obj):
        self.obj = obj

    @property
    def cli(self):
        return self.obj

def cli_commands(obj, namef, clizer):
    cmds = util.OrderedDict()
    cmd_by_name = {}
    for key, val in util.dict_from_names(obj).items():
        if not key:
            continue
        names = tuple(namef(name) for name in util.maybe_iter(key))
        cli = clizer.get_cli(val)
        cmds[names] = cli
        for name in names:
            cmd_by_name[name] = cli
    return cmds, cmd_by_name

class Clize(object):
    """Wraps a function into a CLI object that accepts command-line arguments
    and translates them to match the wrapped function's parameters."""

    @forwards_to_method('__init__', 1)
    def __new__(cls, fn=None, **kwargs):
        if fn is None:
            return partial(cls, **kwargs)
        else:
            return super(Clize, cls).__new__(cls)

    def __init__(self, fn, owner=None, alt=(), extra=(), pass_name=False,
                 help_names=('help', 'h'), helper_class=None, hide_help=False):
        """
        :param sequence alt: Alternate actions the CLI will handle.
        :param bool pass_name: Pass the command name as first argument to the
            wrapped function.
        :param help_names: Names to use to trigger the help.
        :type help_names: sequence of strings
        :param helper_class: A callable to produce a helper object to be
            used when the help is triggered. If unset, uses `.ClizeHelp`.
        :type helper_class: a type like `.ClizeHelp`
        :param bool hide_help: Mark the parameters used to trigger the help
            as undocumented.
        """
        update_wrapper(self, fn)
        self.func = fn
        self.owner = owner
        self.alt = util.maybe_iter(alt)
        self.extra = extra
        self.pass_name = pass_name
        self.help_names = help_names
        self.help_aliases = [util.name_py2cli(s, kw=True) for s in help_names]
        self.helper_class = helper_class
        self.hide_help = hide_help

    def parameters(self):
        """Returns the parameters used to instantiate this class, minus the
        wrapped callable."""
        return {
            'owner': self.owner,
            'alt': self.alt,
            'pass_name': self.pass_name,
            'help_names': self.help_names,
            'helper_class': self.helper_class,
            'hide_help': self.hide_help,
            }

    @classmethod
    def keep(cls, fn=None, **kwargs):
        """Instead of wrapping the decorated callable, sets its ``cli``
        attribute to a `.Clize` instance. Useful if you need to use the
        decorator but must still be able to call the function regularily.
        """
        if fn is None:
            return partial(cls.keep, **kwargs)
        else:
            fn.cli = cls(fn, **kwargs)
            return fn

    @classmethod
    def as_is(cls, obj):
        """Returns a CLI object which uses the given callable with no
        translation."""
        return _CliWrapper(obj)

    @classmethod
    def get_cli(cls, obj, **kwargs):
        """Makes an attempt to discover a command-line interface for the
        given object.

        .. _cli-object:

        The process used is as follows:

        1. If the object has a ``cli`` attribute, it is used with no further
           transformation.
        2. If the object is callable, `.Clize` or whichever object this
           class method is used from is used to build a CLI. ``**kwargs`` are
           forwarded to its initializer.
        3. If the object is iterable, `.SubcommandDispatcher` is used on
           the object, and its `cli <.SubcommandDispatcher.cli>` method
           is used.

        Most notably, `clize.run` uses this class method in order to interpret
        the given object(s).
        """
        try:
            cli = obj.cli
        except AttributeError:
            if callable(obj):
                cli = cls(obj, **kwargs)
            else:
                try:
                    iter(obj)
                except TypeError:
                    raise TypeError("Don't know how to build a cli for "
                                    + repr(obj))
                cli = SubcommandDispatcher(obj, **kwargs).cli
        return cli

    @property
    def cli(self):
        """Returns the object itself, in order to be selected by `.get_cli`"""
        return self

    def __repr__(self):
        return '<Clize for {0!r}>'.format(self.func)

    def __get__(self, obj, owner=None):
        try:
            func = self.func.__get__(obj, owner)
        except AttributeError:
            func = self.func
        if func is self.func:
            return self
        params = self.parameters()
        params['owner'] = obj
        return type(self)(func, **params)

    @util.property_once
    def helper(self):
        """A cli object(usually inherited from `.help.Help`) when the user
        requests a help message. See the constructor for ways to affect this
        attribute."""
        if self.helper_class is None:
            from clize.help import ClizeHelp as class_
        else:
            class_ = self.helper_class
        return class_(self, self.owner)

    @util.property_once
    def signature(self):
        """The `.parser.CliSignature` object used to parse arguments."""
        return parser.CliSignature.from_signature(
            mask(util.funcsigs.signature(self.func), self.pass_name),
            extra=itertools.chain(self._process_alt(self.alt), self.extra))

    def _process_alt(self, alt):
        if self.help_names:
            p = parser.FallbackCommandParameter(
                func=self.helper.cli, undocumented=self.hide_help,
                aliases=self.help_aliases)
            yield p

        for name, func in util.dict_from_names(alt).items():
            func = self.get_cli(func)
            param = parser.AlternateCommandParameter(
                undocumented=False, func=func,
                aliases=[util.name_py2cli(name, kw=True)])
            yield param

    def __call__(self, *args):
        with errors.SetUserErrorContext(cli=self, pname=args[0]):
            func, name, posargs, kwargs = self.read_commandline(args)
            return func(*posargs, **kwargs)

    def read_commandline(self, args):
        """Reads the command-line arguments from args and returns a tuple
        with the callable to run, the name of the program, the positional
        and named arguments to pass to the callable.

        :raises: `.ArgumentError`
        """
        ba = self.signature.read_arguments(args[1:], args[0])
        func, post, posargs, kwargs = ba
        name = ' '.join([args[0]] + post)
        if func or self.pass_name:
            posargs.insert(0, name)
        return func or self.func, name, posargs, kwargs

def _dispatcher_helper(*args, **kwargs):
    """alias for clize.help.DispatcherHelper, avoiding circular import"""
    from clize.help import DispatcherHelper
    return DispatcherHelper(*args, **kwargs)

def make_dispatcher_helper(*args, **kwargs):
    from clize.help import DispatcherHelper
    return DispatcherHelper(*args, **kwargs)

class SubcommandDispatcher(object):
    clizer = Clize

    def __init__(self, commands=(), description=None, footnotes=None):
        self.cmds, self.cmds_by_name = cli_commands(
            commands, namef=util.name_py2cli, clizer=self.clizer)
        self.description = description
        self.footnotes = footnotes

    @Clize(pass_name=True, helper_class=make_dispatcher_helper)
    @annotate(command=(operator.methodcaller('lower'),
                       parser.Parameter.LAST_OPTION))
    def cli(self, name, command, *args):
        try:
            func = self.cmds_by_name[command]
        except KeyError:
            raise errors.ArgumentError('Unknwon command "{0}"'.format(command))
        return func('{0} {1}'.format(name, command), *args)


def fix_argv(argv, path):
    """Properly display ``python -m`` invocations"""
    if not path[0]:
        argv = argv[:]
        import __main__
        argv[0] = '{0} -m {1}'.format(
            os.path.basename(sys.executable) if sys.executable else 'python',
            main_module_name(__main__))
    return argv


def main_module_name(module):
    if module.__file__.endswith('/__main__.py'):
        return module.__package__
    return (
        module.__package__ + '.' +
        os.path.splitext(os.path.basename(module.__file__))[0]
        )


@autokwoargs
def run(args=None, catch=(), exit=True, out=None, err=None, *fn, **kwargs):
    """Runs a function or :ref:`CLI object<cli-object>` with ``args``, prints
    the return value if not None, or catches the given exception types as well
    as `clize.UserError` and prints their string representation, then exit with
    the appropriate status code.

    :param sequence args: The arguments to pass the CLI, for instance
        ``('./a_script.py', 'spam', 'ham')``. If unspecified, uses `sys.argv`.
    :param catch: Catch these exceptions and print their string representation
        rather than letting python print an uncaught exception traceback.
    :type catch: sequence of exception classes
    :param bool exit: If true, exit with the appropriate status code once the
        function is done.
    :param file out: The file in which to print the return value of the
        command. If unspecified, uses `sys.stdout`
    :param file err: The file in which to print any exception text.
        If unspecified, uses `sys.stderr`.

    """
    if len(fn) == 1:
        fn = fn[0]
    cli = Clize.get_cli(fn, **kwargs)

    if args is None:
        args = fix_argv(sys.argv, sys.path)
    if out is None:
        out = sys.stdout
    if err is None:
        err = sys.stderr

    try:
        ret = cli(*args)
    except tuple(catch) + (errors.UserError,) as exc:
        print(str(exc), file=err)
        if exit:
            sys.exit(2 if isinstance(exc, errors.ArgumentError) else 1)
    else:
        if ret is not None:
            print(ret, file=out)
        if exit:
            sys.exit()


########NEW FILE########
__FILENAME__ = test_help
from sigtools.support import f
from clize import runner, help
from clize.tests.util import testfunc

@testfunc
def test_whole_help(self, sig, doc, help_str):
    func = f(sig, pre="from clize import Parameter")
    func.__doc__ = doc
    r = runner.Clize(func)
    h = help.ClizeHelp(r, None)
    p_help_str = str(h.show('func'))
    self.assertEqual(p_help_str.split(), help_str.split())

@test_whole_help
class WholeHelpTests(object):
    simple = "one, *args, two", """
        Description

        one: Argument one

        args: Other arguments

        two: Option two

        Footer
    """, """
        Usage: func [OPTIONS] one [args...]

        Description

        Positional arguments:
            one     Argument one
            args    Other arguments

        Options:
            --two=STR   Option two

        Other actions:
            -h, --help  Show the help

        Footer
    """

    pos_out_of_order = "one, two", """
        Description

        two: Argument two

        one: Argument one
    """, """
        Usage: func one two

        Description

        Positional arguments:
            one     Argument one
            two     Argument two

        Other actions:
            -h, --help  Show the help
    """

    opt_out_of_order = "*, one, two", """
        two: Option two

        one: Option one
    """, """
        Usage: func [OPTIONS]

        Options:
            --two=STR   Option two
            --one=STR   Option one

        Other actions:
            -h, --help  Show the help
    """

########NEW FILE########
__FILENAME__ = test_legacy
#!/usr/bin/python
# encoding: utf-8

import unittest
import warnings

from clize import clize, errors, runner

class OldInterfaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        warnings.filterwarnings('ignore', 'Use clize\.Clize',
                                DeprecationWarning)

    @classmethod
    def tearDownClass(self):
        warnings.filters.pop(0)

class ParamTests(OldInterfaceTests):
    def test_pos(self):
        @clize
        def fn(one, two, three):
            return one, two, three
        self.assertEqual(
            fn('fn', "1", "2", "3"),
            ('1', '2', '3')
            )

    def test_kwargs(self):
        @clize
        def fn(one='1', two='2', three='3'):
            return one, two, three
        self.assertEqual(
            fn('fn', '--three=6', '--two', '4'),
            ('1', '4', '6')
            )

    def test_mixed(self):
        @clize
        def fn(one, two='2', three='3'):
            return one, two, three
        self.assertEqual(
            fn('fn', '--two', '4', '0'),
            ('0', '4', '3')
            )

    def test_catchall(self):
        @clize
        def fn(one, two='2', *rest):
            return one, two, rest
        self.assertEqual(
            fn('fn', '--two=4', '1', '2', '3', '4'),
            ('1', '4', ('2', '3', '4'))
            )

    def test_coerce(self):
        @clize
        def fn(one=1, two=2, three=False):
            return one, two, three
        self.assertEqual(
            fn('fn', '--one=0', '--two', '4', '--three'),
            (0, 4, True)
            )

    def test_explicit_coerce(self):
        @clize(coerce={'one': int, 'two': int})
        def fn(one, two):
            return one, two
        self.assertEqual(
            fn('fn', '1', '2'),
            (1, 2)
            )

    def test_extra(self):
        @clize
        def fn(*args):
            return args
        self.assertEqual(fn('fn'), ())
        self.assertEqual(fn('fn', '1'), ('1',))
        self.assertEqual(fn('fn', '1', '2'), ('1', '2'))

    def test_extra_required(self):
        @clize(require_excess=True)
        def fn(*args):
            return args
        self.assertRaises(errors.MissingRequiredArguments, fn, 'fn')
        self.assertEqual(fn('fn', '1'), ('1',))
        self.assertEqual(fn('fn', '1', '2'), ('1', '2'))

    def test_too_short(self):
        @clize
        def fn(one, two):
            pass
        self.assertRaises(errors.MissingRequiredArguments, fn, 'fn', 'one')

    def test_too_long(self):
        @clize
        def fn(one, two):
            pass
        self.assertRaises(errors.TooManyArguments, fn, 'fn', 'one', 'two', 'three')

    def test_missing_arg(self):
        @clize
        def fn(one='1', two='2'):
            pass
        self.assertRaises(errors.MissingValue, fn, 'fn', '--one')

    def test_short_param(self):
        @clize(alias={'one': ('o',)})
        def fn(one='1'):
            return one
        self.assertEqual(fn('fn', '--one', '0'), '0')
        self.assertEqual(fn('fn', '-o', '0'), '0')

    def test_short_int_param(self):
        @clize(alias={'one': ('o',), 'two': ('t',), 'three': ('s',)})
        def fn(one=1, two=2, three=False):
            return one, two, three
        self.assertEqual(fn('fn', '--one', '0'), (0, 2, False))
        self.assertEqual(fn('fn', '-o', '0', '-t', '4', '-s'), (0, 4, True))
        self.assertEqual(fn('fn', '-o0t4s'), (0, 4, True))

    def test_force_posarg(self):
        @clize(force_positional=('one',))
        def fn(one=1):
            return one
        self.assertEqual(fn('fn', '0'), 0)

    def test_unknown_option(self):
        @clize
        def fn(one=1):
            return one
        self.assertRaises(errors.UnknownOption, fn, 'fn', '--doesnotexist')

    def test_coerce_fail(self):
        @clize
        def fn(one=1):
            return 1
        self.assertRaises(errors.BadArgumentFormat, fn, 'fn', '--one=nan')

def run_group(functions, args):
    disp = runner.SubcommandDispatcher(functions)
    return disp.cli(*args)

class SubcommandTests(OldInterfaceTests):

    def test_pos(self):
        @clize
        def fn1(one, two):
            return one, two
        self.assertEqual(
            run_group((fn1,), ('group', 'fn1', 'one', 'two')),
            ('one', 'two')
            )

    def test_opt(self):
        @clize
        def fn1(one='1', two='2'):
            return one, two
        self.assertEqual(
            run_group((fn1,), ('group', 'fn1', '--one=one', '--two', 'two')),
            ('one', 'two')
            )

    def test_unknown_command(self):
        @clize
        def fn1():
            return
        self.assertRaises(
            errors.ArgumentError,
            run_group, (fn1,), ('group', 'unknown')
            )

    def test_no_command(self):
        @clize
        def fn1():
            return
        self.assertRaises(
            errors.ArgumentError,
            run_group, (fn1,), ('group',)
            )

    def test_opts_but_no_command(self):
        @clize
        def fn1():
            return
        self.assertRaises(
            errors.ArgumentError,
            run_group, (fn1,), ('group', '--opt')
            )

class HelpTester(object):
    def assertHelpEquals(
            self, fn, help_str,
            alias={}, force_positional=(),
            require_excess=False, coerce={}
            ):
        return self.assertEqual(
            help('fn',
                read_arguments(fn, alias, force_positional,
                               require_excess, coerce)[0],
                do_print=False),
            help_str
            )

class HelpTests(HelpTester):
    def test_pos(self):
        def fn(one, two, three, *more):
            pass
        self.assertHelpEquals(
            fn, """\
Usage: fn one two three [more...]

Positional arguments:
  one      
  two      
  three    
  more...  
""")

    def test_kwargs(self):
        def fn(one='1', two=2, three=3.0, four=False):
            pass
        self.assertHelpEquals(
            fn, """\
Usage: fn [OPTIONS] 

Options:
  --one=STR      
  --two=INT      
  --three=FLOAT  
  --four         
""")

    def test_mixed(self):
        def fn(one, two='2', *more):
            pass
        self.assertHelpEquals(
            fn, """\
Usage: fn [OPTIONS] one [more...]

Positional arguments:
  one      
  more...  

Options:
  --two=STR  
""")

    def test_require_excess(self):
        def fn(one, *more):
            pass
        self.assertHelpEquals(
            fn, """\
Usage: fn one more...

Positional arguments:
  one      
  more...  
""",
            require_excess=True)

    def test_alias(self):
        def fn(one='1', two='2'):
            pass
        self.assertHelpEquals(
            fn, """\
Usage: fn [OPTIONS] 

Options:
  -o, --one=STR  
  -t, --two=STR  
""",
            alias={'one': ('o',), 'two': ('t',)}
            )

    def test_force_positional(self):
        def fn(one='1', two='2'):
            pass
        self.assertHelpEquals(
            fn, """\
Usage: fn [OPTIONS] [one]

Positional arguments:
  one  

Options:
  --two=STR  
""",
            force_positional=('one',)
            )

    def test_doc(self):
        def fn(one, two='2', three=3, four=False, *more):
            """
            Command description

            one: First parameter

            two: Second parameter

            three: This help text spans
            over two lines in the source

            four: Fourth parameter

            more: Catch-all parameter

            Footnotes
            """
        self.assertHelpEquals(
            fn, """\
Usage: fn [OPTIONS] one [two] [more...]

Command description

Positional arguments:
  one       First parameter
  two       Second parameter(default: 2)
  more...   Catch-all parameter

Options:
  -t, --three=INT   This help text spans over two lines in the
                    source(default: 3)
  -f, --four        Fourth parameter

Footnotes
""",
            force_positional=('two',),
            alias={'three':('t',), 'four': ('f',)})

    def test_supercommand(self):
        @clize
        def fn1():
            pass
        @clize
        def fn2():
            pass
        subcommands, supercommand = read_supercommand(
            (fn1, fn2), "Description", "Footnotes", ('help', 'h')
            )
        self.assertEqual(
            help('group', supercommand, do_print=False),
            """\
Usage: group command [OPTIONS] 

Description

Available commands:
  fn1  
  fn2  

See 'group command --help' for more information on a specific command.

Footnotes
"""
            )

    def test_nolongs(self):
        def fn(a):
            pass

        self.assertHelpEquals(
            fn, """\
Usage: fn a

Positional arguments:
  a  
"""
            )


########NEW FILE########
__FILENAME__ = test_legacy_py3k
#!/usr/bin/python

import unittest

from sigtools import modifiers
from clize import clize, errors

#from tests import HelpTester

class AnnotationParams(unittest.TestCase):
    def test_alias(self):
        @clize
        @modifiers.annotate(one='o')
        def fn(one=1):
            return one
        self.assertEqual(
            fn('fn', '-o', '2'),
            2
            )

    def test_position(self):
        @clize
        @modifiers.annotate(one=clize.POSITIONAL)
        def fn(one=1):
            return one
        self.assertEqual(
            fn('fn', '2'),
            2
            )

    def test_coerce(self):
        @clize
        @modifiers.annotate(one=float)
        def fn(one):
            return one
        self.assertEqual(
            fn('fn', '2.1'),
            2.1
            )

    def test_coerce_and_default(self):
        @clize
        @modifiers.annotate(one=float)
        def fn(one=1):
            return one
        self.assertEqual(
            fn('fn'),
            1
            )
        self.assertEqual(
            fn('fn', '--one', '2.1'),
            2.1
            )

    def test_multiple(self):
        @clize
        @modifiers.annotate(one=(float, clize.POSITIONAL))
        def fn(one=1):
            return one
        self.assertEqual(
            fn('fn', '2.1'),
            2.1
            )
        self.assertEqual(
            fn('fn'),
            1
            )

class AnnotationFailures(unittest.TestCase):
    def test_coerce_twice(self):
        def test():
            @clize
            @modifiers.annotate(one=(float, int))
            def fn(one):
                return one
            fn.signature
        self.assertRaises(ValueError, test)

    def test_alias_space(self):
        def test():
            @clize
            @modifiers.annotate(one='a b')
            def fn(one=1):
                return one
            fn.signature
        self.assertRaises(ValueError, test)

    def test_unknown(self):
        def test():
            @clize
            @modifiers.annotate(one=1.0)
            def fn(one):
                return one
            fn.signature
        self.assertRaises(ValueError, test)

class KwoargsParams(unittest.TestCase):
    def test_kwoparam(self):
        @clize
        @modifiers.kwoargs('one')
        def fn(one):
            return one

        self.assertEqual(
            fn('fn', '--one=one'),
            'one'
            )

    def test_kwoparam_required(self):
        @clize
        @modifiers.kwoargs('one')
        def fn(one):
            return one

        self.assertRaises(errors.MissingRequiredArguments, fn, 'fn')

    def test_kwoparam_optional(self):
        @clize
        @modifiers.kwoargs('one')
        def fn(one=1):
            return one
        self.assertEqual(
            fn('fn'),
            1
            )
        self.assertEqual(
            fn('fn', '--one', '2'),
            2
            )
        self.assertEqual(
            fn('fn', '--one=2'),
            2
            )

    def test_optional_pos(self):
        @clize.kwo
        def fn(one, two=2):
            return one, two
        self.assertEqual(
            fn('fn', '1'),
            ('1', 2)
            )
        self.assertEqual(
            fn('fn', '1', '3'),
            ('1', 3)
            )

class KwoargsHelpTests(object):
    def test_kwoparam(self):
        @modifiers.kwoargs('one')
        def fn(one='1'):
            """

            one: one!
            """
            pass
        self.assertHelpEquals(
            fn, """\
Usage: fn [OPTIONS] 

Options:
  --one=STR   one!(default: 1)
""")

    def test_kwoparam_required(self):
        @modifiers.kwoargs('one')
        def fn(one):
            """
            one: one!
            """
            pass
        self.assertHelpEquals(
            fn, """\
Usage: fn [OPTIONS] 

Options:
  --one=STR   one!(required)
""")

########NEW FILE########
__FILENAME__ = test_parser
from sigtools import support, modifiers
from clize.util import funcsigs

from clize import parser, errors, util
from clize.tests.util import testfunc


@testfunc
def fromsigtests(self, sig_str, typ, str_rep, attrs):
    sig = support.s(sig_str, pre='from clize import Parameter')
    param = list(sig.parameters.values())[0]
    cparam = parser.Parameter.from_parameter(param)
    self.assertEqual(type(cparam), typ)
    self.assertEqual(str(cparam), str_rep)
    p_attrs = dict(
        (key, getattr(cparam, key))
        for key in attrs
        )
    self.assertEqual(p_attrs, attrs)


@fromsigtests
class FromSigTests(object):
    pos = 'one', parser.PositionalParameter, 'one', {
        'typ': util.identity, 'default': util.UNSET, 'required': True,
        'argument_name': 'one', 'display_name': 'one',
        'undocumented': False, 'last_option': None}
    pos_default_str = 'one="abc"', parser.PositionalParameter, '[one]', {
        'typ': type("abc"), 'default': "abc", 'required': False,
        'argument_name': 'one', 'display_name': 'one',
        'undocumented': False, 'last_option': None}
    pos_default_none = 'one=None', parser.PositionalParameter, '[one]', {
        'typ': util.identity, 'default': None, 'required': False,
        'argument_name': 'one', 'display_name': 'one',
        'undocumented': False, 'last_option': None}
    pos_default_int = 'one=3', parser.PositionalParameter, '[one=INT]', {
        'typ': int, 'default': 3, 'required': False,
        'argument_name': 'one', 'display_name': 'one',
        'undocumented': False, 'last_option': None}
    pos_default_but_required = (
        'one:Parameter.REQUIRED=3', parser.PositionalParameter, 'one=INT', {
            'typ': int, 'default': util.UNSET, 'required': True,
            'argument_name': 'one', 'display_name': 'one',
            'undocumented': False, 'last_option': None})
    pos_last_option = (
        'one:Parameter.LAST_OPTION', parser.PositionalParameter, 'one', {
            'typ': util.identity, 'default': util.UNSET, 'required': True,
            'argument_name': 'one', 'display_name': 'one',
            'undocumented': False, 'last_option': True})

    collect = '*args', parser.ExtraPosArgsParameter, '[args...]', {
        'typ': util.identity, 'default': util.UNSET, 'required': False,
        'argument_name': 'args', 'display_name': 'args',
        'undocumented': False, 'last_option': None}
    collect_int = '*args:int', parser.ExtraPosArgsParameter, '[args...]', {
        'typ': int, 'default': util.UNSET, 'required': False,
        }
    collect_required = (
        '*args:Parameter.REQUIRED', parser.ExtraPosArgsParameter, 'args...', {
            'typ': util.identity, 'default': util.UNSET, 'required': True,
            'argument_name': 'args', 'display_name': 'args',
            'undocumented': False, 'last_option': None})

    named = '*, one', parser.OptionParameter, '--one=STR', {
        'typ': util.identity, 'default': util.UNSET, 'required': True,
        'argument_name': 'one', 'display_name': '--one', 'aliases': ['--one'],
        'undocumented': False, 'last_option': None}
    named_bool = '*, one=False', parser.FlagParameter, '[--one]', {
        }
    named_int = '*, one: int', parser.IntOptionParameter, '--one=INT', {
        'typ': int, 'default': util.UNSET, 'required': True,
        'argument_name': 'one', 'display_name': '--one', 'aliases': ['--one'],
        'undocumented': False, 'last_option': None}

    alias = '*, one: "a"', parser.OptionParameter, '--one=STR', {
        'display_name': '--one', 'aliases': ['--one', '-a']}

    def test_param_inst(self):
        param = parser.Parameter('abc')
        sig = support.s('xyz: p', locals={'p': param})
        sparam = list(sig.parameters.values())[0]
        cparam = parser.Parameter.from_parameter(sparam)
        self.assertTrue(cparam is param)

@testfunc
def signaturetests(self, sig_str, str_rep, args, posargs, kwargs):
    sig = support.s(sig_str, locals={'P': parser.Parameter})
    csig = parser.CliSignature.from_signature(sig)
    ba = csig.read_arguments(args)
    self.assertEqual(str(csig), str_rep)
    self.assertEqual(ba.args, posargs)
    self.assertEqual(ba.kwargs, kwargs)

@signaturetests
class SigTests(object):
    pos = (
        'one, two, three', 'one two three',
        ('1', '2', '3'), ['1', '2', '3'], {})

    _two_str_usage = '--one=STR --two=STR'
    kw_glued = (
        '*, one, two', _two_str_usage,
        ('--one=1', '--two=2'), [], {'one': '1', 'two': '2'})
    kw_nonglued = (
        '*, one, two', _two_str_usage,
        ('--one', '1', '--two', '2'), [], {'one': '1', 'two': '2'})

    kw_short_nonglued = (
        '*, one: "a", two: "b"', _two_str_usage,
        ('-a', '1', '-b', '2'), [], {'one': '1', 'two': '2'})
    kw_short_glued = (
        '*, one: "a", two: "b"', _two_str_usage,
        ('-a1', '-b2'), [], {'one': '1', 'two': '2'})

    pos_and_kw = (
        'one, *, two, three, four: "a", five: "b"',
        '--two=STR --three=STR --four=STR --five=STR one',
        ('1', '--two', '2', '--three=3', '-a', '4', '-b5'),
        ['1'], {'two': '2', 'three': '3', 'four': '4', 'five': '5'})
    pos_and_kw_mixed = (
        'one, two, *, three', '--three=STR one two',
        ('1', '--three', '3', '2'), ['1', '2'], {'three': '3'}
        )

    flag = '*, one=False', '[--one]', ('--one',), [], {'one': True}
    flag_absent = '*, one=False', '[--one]', (), [], {}
    flag_glued = (
        '*, a=False, b=False, c=False', '[-a] [-b] [-c]',
        ('-ac',), [], {'a': True, 'c': True}
        )

    _one_flag = '*, one:"a"=False'
    _one_flag_u = '[--one]'
    flag_false = _one_flag, _one_flag_u, ('--one=',), [], {'one': False}
    flag_false_0 = _one_flag, _one_flag_u, ('--one=0',), [], {'one': False}
    flag_false_n = _one_flag, _one_flag_u, ('--one=no',), [], {'one': False}
    flag_false_f = _one_flag, _one_flag_u, ('--one=false',), [], {'one': False}

    collect_pos = '*args', '[args...]', ('1', '2', '3'), ['1', '2', '3'], {}
    pos_and_collect = (
        'a, *args', 'a [args...]',
        ('1', '2', '3'), ['1', '2', '3'], {})
    collect_and_kw = (
        '*args, one', '--one=STR [args...]',
        ('2', '--one', '1', '3'), ['2', '3'], {'one': '1'})

    conv = 'a=1', '[a=INT]', ('1',), [1], {}

    named_int_glued = (
        '*, one:"a"=1, two:"b"="s"', '[--one=INT] [--two=STR]',
        ('-a15bham',), [], {'one': 15, 'two': 'ham'})

    double_dash = (
        'one, two, three', 'one two three',
        ('first', '--', '--second', 'third'),
        ['first', '--second', 'third'], {}
        )

    pos_last_option = (
        'one, two:P.L, *r, three', '--three=STR one two [r...]',
        ('1', '--three=3', '2', '--four', '4'),
        ['1', '2', '--four', '4'], {'three': '3'}
        )
    kw_last_option = (
        'one, two, *r, three:P.L', '--three=STR one two [r...]',
        ('1', '--three=3', '2', '--four', '4'),
        ['1', '2', '--four', '4'], {'three': '3'}
        )

@testfunc
def extraparamstests(self, sig_str, extra, args, posargs, kwargs, func):
    sig = support.s(sig_str)
    csig = parser.CliSignature.from_signature(sig, extra=extra)
    ba = csig.read_arguments(args)
    self.assertEqual(ba.args, posargs)
    self.assertEqual(ba.kwargs, kwargs)
    self.assertEqual(ba.func, func)


@extraparamstests
class ExtraParamsTests(object):
    _func = support.f('')
    alt_cmd = (
        '', [parser.AlternateCommandParameter(func=_func, aliases=['--alt'])],
        ('--alt', 'a', '-b', '--third'), ['a', '-b', '--third'], {}, _func
        )
    alt_cmd2 = (
        '', [parser.AlternateCommandParameter(func=_func, aliases=['--alt'])],
        ('--alt', '--alpha', '-b'), ['--alpha', '-b'], {}, _func
        )
    flb_cmd_start = (
        '', [parser.FallbackCommandParameter(func=_func, aliases=['--alt'])],
        ('--alt', '-a', 'b', '--third'), ['-a', 'b', '--third'], {}, _func
        )
    flb_cmd_valid = (
        '*a', [parser.FallbackCommandParameter(func=_func, aliases=['--alt'])],
        ('a', '--alt', 'b', '-c', '--fourth'), [], {}, _func
        )
    flb_cmd_invalid = (
        '', [parser.FallbackCommandParameter(func=_func, aliases=['--alt'])],
        ('a', '--alt', 'a', '-b'), [], {}, _func
        )
    flb_cmd_invalid_valid = (
        'a: int, b',
        [parser.FallbackCommandParameter(func=_func, aliases=['--alt'])],
        ('xyz', 'abc', '--alt', 'def', '-g', '--hij'), [], {}, _func
        )

    def test_alt_middle(self):
        _func = support.f('')
        self.assertRaises(
            errors.ArgsBeforeAlternateCommand,
            self._test_func,
            '*a', [
                parser.AlternateCommandParameter(
                    func=_func, aliases=['--alt'])],
            ('a', '--alt', 'a', 'b'), ['a', 'b'], {}, _func
        )


@testfunc
def sigerrortests(self, sig_str, args, exc_typ):
    sig = support.s(sig_str)
    csig = parser.CliSignature.from_signature(sig)
    try:
        csig.read_arguments(args)
    except exc_typ:
        pass
    except: #pragma: no cover
        raise
    else: #pragma: no cover
        self.fail('{0.__name__} not raised'.format(exc_typ))

@sigerrortests
class SigErrorTests(object):
    not_enough_pos = 'one, two', ['1'], errors.MissingRequiredArguments
    too_many_pos = 'one', ['1', '2'], errors.TooManyArguments

    missing_kw = '*, one', [], errors.MissingRequiredArguments
    duplicate_kw = (
        '*, one', ['--one', '1', '--one=1'], errors.DuplicateNamedArgument)
    unknown_kw = '', ['--one'], errors.UnknownOption
    unknown_kw_after_short_flag = '*, o=False', ['-oa'], errors.UnknownOption
    missing_value = '*, one', ['--one'], errors.MissingValue

    bad_format = 'one=1', ['a'], errors.BadArgumentFormat

    def test_not_enough_pos_collect(self):
        @modifiers.annotate(args=parser.Parameter.REQUIRED)
        def func(*args):
            raise NotImplementedError
        csig = parser.CliSignature.from_signature(funcsigs.signature(func))
        try:
            csig.read_arguments(())
        except errors.MissingRequiredArguments:
            pass
        except: # pragma: no cover
            raise
        else:
            self.fail('MissingRequiredArguments not raised') # pragma: no cover

@testfunc
def badparam(self, sig_str, locals=None):
    if locals is None:
        locals = {}
    sig = support.s(sig_str, pre='from clize import Parameter', locals=locals)
    param = list(sig.parameters.values())[0]
    try:
        cparam = parser.Parameter.from_parameter(param)
    except ValueError:
        pass
    else:
        self.fail('ValueError not raised')

class UnknownAnnotation(object):
    pass

@badparam
class BadParamTests(object):
    alias_superfluous = 'one: "a"',
    alias_spaces = '*, one: "a b"',
    unknown_annotation = 'one: ua', {'ua': UnknownAnnotation()}
    coerce_twice = 'one: co', {'co': (str, int)}

########NEW FILE########
__FILENAME__ = util
from functools import partial
import unittest

class Tests(unittest.TestCase):
    pass

def make_run_test(func, value, **kwargs):
    def _func(self):
        return func(self, *value, **kwargs)
    return _func

def build_sigtests(func, cls):
    members = {
            '_test_func': func,
        }
    for key, value in cls.__dict__.items():
        if key.startswith('test_') or key.startswith('_'):
            members[key] = value
        else:
            members['test_' + key] = make_run_test(func, value)
    return type(cls.__name__, (Tests, unittest.TestCase), members)

def testfunc(test_func):
    return partial(build_sigtests, test_func)

########NEW FILE########
__FILENAME__ = util
# clize -- A command-line argument parser for Python
# Copyright (C) 2013 by Yann Kaiser <kaiser.yann@gmail.com>
# See COPYING for details.

"""various"""

import os
from functools import update_wrapper

import inspect
try:
    inspect.signature
except AttributeError:
    import funcsigs
else:
    funcsigs = inspect

try:
    from collections import OrderedDict
except ImportError:
    from ordereddict import OrderedDict

import six
from sigtools.wrappers import wrapper_decorator


class _Unset(object):
    __slots__ = ()
    def __repr__(self):
        return '<unset>'
UNSET = _Unset()
del _Unset

def identity(x=None):
    return x

def name_py2cli(name, kw=False):
    name = name.strip('_').replace('_', '-')
    if kw:
        if len(name) > 1:
            return '--' + name
        else:
            return '-' + name
    else:
        return name

def name_cli2py(name, kw=False):
    return name.strip('-').replace('-', '_')

def name_type2cli(typ):
    if typ is identity or typ in six.string_types:
        return 'STR'
    else:
        return typ.__name__.upper()

def maybe_iter(x):
    try:
        iter(x)
    except TypeError:
        return x,
    else:
        if isinstance(x, six.string_types):
            return x,
    return x

def dict_from_names(obj, receiver=None, func=identity):
    try:
        obj.items
    except AttributeError:
        pass
    else:
        if receiver is None:
            return obj
        else:
            receiver.update(obj)
            return receiver
    if receiver is None:
        receiver = OrderedDict()
    receiver.update((func(x.__name__), x) for x in maybe_iter(obj))
    return receiver

class property_once(object):
    def __init__(self, func):
        update_wrapper(self, func)
        self.func = func
        self.key = func.__name__

    def __get__(self, obj, owner):
        if obj is None:
            return self
        try:
            return obj.__dict__[self.key] # could happen if we've been
                                          # assigned to multiple names
        except KeyError:
            ret = obj.__dict__[self.key] = self.func(obj)
            return ret

    def __repr__(self):
        return '<property_once from {0!r}>'.format(self.func)


class _FormatterRow(object):
    def __init__(self, columns, cells):
        self.columns = columns
        self.cells = cells

    def __iter__(self):
        return iter(self.cells)

    def __repr__(self):
        return repr(self.cells)

    def __str__(self):
        return self.columns.format_cells(self.cells)

class _FormatterColumns(object):
    def __init__(self, formatter, num, spacing, align,
                 min_widths, max_widths):
        self.formatter = formatter
        self.num = num
        self.spacing = spacing
        self.align = align or '<' * num
        self.min_widths = min_widths or (0,) * num
        self.max_widths = max_widths or (None,) * num
        self.rows = []
        self.finished = False

    def __enter__(self):
        return self

    def append(self, *cells):
        if len(cells) != self.num:
            raise ValueError('expected {0} cells but got {1}'.format(
                             self.num, len(cells)))
        row = _FormatterRow(self, cells)
        self.rows.append(row)
        self.formatter.append(row)

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.finished = True
        self.compute_widths()

    def compute_widths(self):
        self.widths = tuple(
            max(len(s) for s in col)
            for col in zip(*self.rows)
            )

    def format_cells(self, cells):
        return self.spacing.join(
            '{0:{1}{2}}'.format(cell, align, width)
            for cell, align, width in zip(cells, self.align, self.widths)
            )

class _FormatterIndent(object):
    def __init__(self, formatter, indent):
        self.formatter = formatter
        self.indent = indent

    def __enter__(self):
        self.formatter._indent += self.indent
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.formatter._indent -= self.indent

try:
    terminal_width = max(50, os.get_terminal_size().columns - 1)
except (AttributeError, OSError):
    terminal_width = 70 #fair terminal dice roll

class Formatter(object):
    delimiter = '\n'

    def __init__(self, max_width=-1):
        self.max_width = terminal_width if max_width == -1 else max_width
        self.lines = []
        self._indent = 0

    def append(self, line, indent=0):
        self.lines.append((self._indent + indent, line))

    def new_paragraph(self):
        if self.lines and self.lines[-1][1]:
            self.lines.append((0, ''))

    def extend(self, iterable):
        if not isinstance(iterable, Formatter):
            iterator = ((0, line) for line in iterable)
        else:
            iterator = iter(iterable)
        try:
            first = next(iterator)
        except StopIteration:
            return
        if not first[1]:
            self.new_paragraph()
        else:
            self.append(first[1], first[0])
        for indent, line in iterator:
            self.append(line, indent)

    def indent(self, indent=2):
        return _FormatterIndent(self, indent)

    def columns(self, num=2, spacing='   ', align=None,
                min_widths=None, max_widths=None):
        return _FormatterColumns(
            self, num, spacing, align,
            min_widths, max_widths)

    def __str__(self):
        if self.lines and not self.lines[-1][1]:
            lines = self.lines[:-1]
        else:
            lines = self.lines
        return self.delimiter.join(
            ' ' * indent + six.text_type(line)
            for indent, line in lines
            )

    def __iter__(self):
        return iter(self.lines)


########NEW FILE########
__FILENAME__ = conf
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# clize documentation build configuration file, created by
# sphinx-quickstart on Sun Sep 29 22:54:15 2013.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os

on_rtd = os.environ.get('READTHEDOCS', False) == 'True'

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#sys.path.insert(0, os.path.abspath('.'))

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.intersphinx', 'sphinx.ext.coverage', 'sphinx.ext.viewcode', 'sigtools.sphinxext']

# Add any paths that contain templates here, relative to this directory.
templates_path = []

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = 'clize'
copyright = '2013, Yann Kaiser'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '3.0'
# The full version, including alpha/beta/rc tags.
release = '3.0a1'

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
default_role = 'py:obj'

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
html_theme = 'default' if on_rtd else 'nature'

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
htmlhelp_basename = 'clizedoc'


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
  ('index', 'clize.tex', 'clize Documentation',
   'Yann Kaiser', 'manual'),
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
    ('index', 'clize', 'clize Documentation',
     ['Yann Kaiser'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'clize', 'clize Documentation',
   'Yann Kaiser', 'clize', 'One line description of project.',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'


# Example configuration for intersphinx: refer to the Python standard library.
intersphinx_mapping = {
    'python': ('http://docs.python.org/3/', None),
    'sigtools': ('http://sigtools.readthedocs.org/en/latest/', None),
    }

autoclass_content = 'both'
autodoc_member_order = 'bysource'
autodoc_default_flags = 'members', 'undoc-members'

########NEW FILE########
__FILENAME__ = altcommands
#!/usr/bin/env python

from clize import run


def do_nothing():
    """Does nothing"""
    return "I did nothing, I swear!"


version = 0.2

def version_():
    """Show the version"""
    return 'Do Nothing version {0}'.format(version)

if __name__ == '__main__':
    run(do_nothing, alt=version_)

########NEW FILE########
__FILENAME__ = clscommand
#!/usr/bin/env python

from __future__ import print_function

from sigtools.modifiers import autokwoargs, annotate
from sigtools.signatures import forwards, merge
from clize import run

try:
    from inspect import signature
except ImportError:
    from funcsigs import signature


class Command(object):
    def __init__(self):
        self.__signature__ = forwards(
            signature(self.__call__),
            merge(
                signature(self.do),
                signature(self.prepare),
                signature(self.status)
            )
        )
        self._sigtools__wrappers = (
            self.do, self.prepare, self.status, self.__call__)

    @autokwoargs
    def __call__(self, quiet=False, dry_run=False, *args, **kwargs):
        """
        General options:

        quiet: Print less output

        dry_run: Don't do anything concrete
        """
        self.prepare(*args, **kwargs)
        if not quiet:
            self.status(*args, **kwargs)
        if not dry_run:
            return self.do(*args, **kwargs)

    def prepare(self, *args, **kwargs):
        pass

    def status(self, *args, **kwargs):
        pass

    def do(self, *args, **kwargs):
        pass


class AddCmd(Command):
    """Sums the given numbers

    numbers: The numbers to add together
    """
    @autokwoargs
    def status(self, no_prefix=False, *numbers):
        """
        Formatting options:

        no_prefix: Don't print a prefix in the status message
        """
        if not no_prefix:
            print("summing ", end='')
        print(*numbers, sep=' + ')

    @annotate(numbers=int)
    def do(self, *numbers, **kwargs):
        return sum(numbers)


if __name__ == '__main__':
    run(AddCmd())

########NEW FILE########
__FILENAME__ = decorators
#!/usr/bin/env python

from sigtools.modifiers import autokwoargs
from sigtools.wrappers import wrapper_decorator
from clize import run


@wrapper_decorator
@autokwoargs
def with_uppercase(wrapped, uppercase=False, *args, **kwargs):
    """
    Formatting options:

    uppercase: Print output in capitals
    """
    ret = wrapped(*args, **kwargs)
    if uppercase:
        return str(ret).upper()
    else:
        return ret


@with_uppercase
def hello_world(name=None):
    """Says hello world

    name: Who to say hello to
    """
    if name is not None:
        return 'Hello ' + name
    else:
        return 'Hello world!'

if __name__ == '__main__':
    run(hello_world)

########NEW FILE########
__FILENAME__ = echo
#!/usr/bin/env python
from sigtools.modifiers import annotate, autokwoargs
from clize import ArgumentError, Parameter, run

@annotate(text=Parameter.REQUIRED,
          prefix='p', suffix='s', reverse='r', repeat='n')
@autokwoargs
def echo(prefix='', suffix='', reverse=False, repeat=1, *text):
    """Echoes text back

    text: The text to echo back

    reverse: Reverse text before processing

    repeat: Amount of times to repeat text

    prefix: Prepend this to each line in word

    suffix: Append this to each line in word

    """
    text = ' '.join(text)
    if 'spam' in text:
        raise ArgumentError("I don't want any spam!")
    if reverse:
        text = text[::-1]
    text = text * repeat
    if prefix or suffix:
        return '\n'.join(prefix + line + suffix
                         for line in text.split('\n'))
    return text

def version():
    """Show the version"""
    return 'echo version 0.2'

if __name__ == '__main__':
    run(echo, alt=version)

########NEW FILE########
__FILENAME__ = hello
#!/usr/bin/env python
from sigtools.modifiers import kwoargs
from clize import run

@kwoargs('no_capitalize')
def hello_world(name=None, no_capitalize=False):
    """Greets the world or the given name.

    name: If specified, only greet this person.

    no_capitalize: Don't capitalize the give name.
    """
    if name:
        if not no_capitalize:
            name = name.title()
        return 'Hello {0}!'.format(name)
    return 'Hello world!'

if __name__ == '__main__':
    run(hello_world)

########NEW FILE########
__FILENAME__ = helloworld
#!/usr/bin/env python
from clize import run

def hello_world():
    return "Hello world!"

if __name__ == '__main__':
    run(hello_world)

########NEW FILE########
__FILENAME__ = multicommands
#!/usr/bin/env python
from clize import run


def add(*text):
    """Adds an entry to the to-do list.

    text: The text associated with the entry.
    """
    return "OK I will remember that."


def list_():
    """Lists the existing entries."""
    return "Sorry I forgot it all :("


if __name__ == '__main__':
    run(add, list_, description="""
        A reliable to-do list utility.

        Store entries at your own risk.
        """)

########NEW FILE########
