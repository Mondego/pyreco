__FILENAME__ = core
#!/usr/bin/env python
# -*- coding: utf-8 -*-

__all__ = ['start', 'customize', 'CMD_SUFFIX', 'Program', 'Command']

import sys
import inspect
import re
from os.path import basename
from collections import defaultdict
from .util import json, autotype, getargspec

Empty = type('Empty', (object, ), {
    '__nonzero__': lambda self: False,
    '__repr__'   : lambda self: 'Empty',
})()

class Command(object):
    '''Make a Python function or a built-in function accepts arguments from
    command line.

    :param func: a function you want to convert
    :type func: Python function or built-in function
    :param name: the name of this command
    :type name: str

    .. versionchanged:: 0.1.5
        It is rewritten again. The API is same as the previous version, but some
        behaviors may be different. Please read :py:meth:`Command.parse` for
        more details.

    .. versionchanged:: 0.1.4
        It is almost rewritten.
    '''

    arg_desc_re = re.compile(r'^\s*-')
    '''It is used to filter argument descriptions in a docstring.

    The regex is ``r'^\s*-'`` by default. It means any line starts with a hyphen
    (-), and whitespace characters before this hyphen are ignored.
    '''

    arg_re = re.compile(r'-(?P<long>-)?(?P<key>(?(long)[^ =,]+|.))[ =]?(?P<meta>[^ ,]+)?')
    '''After it gets descriptions by :py:attr:`Command.arg_desc_re` from a
    docstring, it extracts an argument name (or alias) and a metavar from each
    description by this regex.

    The regex is
    ``-(?P<long>-)?(?P<key>(?(long)[^ =,]+|.))[ =]?(?P<meta>[^ ,]+)?``
    by default. The following formats will be parsed correctly:

    - ``--key meta``
    - ``--key=meta``
    - ``-k meta``
    - ``-k=meta``
    - ``-kmeta``
    '''

    arg_type_map = {
        'n': int, 'num': int, 'number': int,
        'i': int, 'int': int, 'integer': int,
        's': str, 'str': str, 'string': str,
        'f': float, 'float': float,
        'json': json,
        None: autotype
    }
    '''A metavar implies a type.

    The ``n``, ``num``, ``number``, ``i``, ``int`` and ``integer`` mean a `int`.
    The ``s``, ``str`` and ``string`` mean a `str`.
    The ``f`` and ``float`` mean a `float`.

    It also supports to use ``json``. It converts a json from user to a Python
    type.

    If you don't set a metavar, it will try to guess a correct type.

    The metavars here are normalized. Metavars from docstrings will be
    normalized, too. For example, ``JSON`` and ``<json>`` are equal to ``json``.
    '''

    def __init__(self, func, name=None):

        self.name = name
        self.func = func

        arg_names, vararg_name, keyarg_name, arg_defaults = getargspec(func)

        # copy the argument spec info to instance
        self.arg_names = arg_names
        self.vararg_name = vararg_name
        self.keyarg_name = keyarg_name
        self.arg_defaults = arg_defaults or tuple()

        # additional information
        self.no_defult_args_len = len(self.arg_names) - len(self.arg_defaults)
        self.arg_name_set = set(arg_names)
        self.arg_default_map = dict(zip(
            *map(reversed, (self.arg_names, self.arg_defaults))
        ))

        # try to find metas and aliases out

        self.arg_meta_map = {}
        self.alias_arg_map = {}

        doc = inspect.getdoc(func)
        if not doc: return

        for line in doc.splitlines():

            if self.arg_desc_re.match(line):

                aliases_set = set()
                for m in self.arg_re.finditer(line):
                    key, meta = m.group('key', 'meta')
                    key = key.replace('-', '_')
                    self.arg_meta_map[key] = meta
                    aliases_set.add(key)

                arg_name_set = self.arg_name_set & aliases_set
                aliases_set -= arg_name_set

                if arg_name_set:
                    arg_name = arg_name_set.pop()
                    for alias in aliases_set:
                        self.alias_arg_map[alias] = arg_name

    def dealias(self, alias):
        '''It maps `alias` to an argument name. If this `alias` maps noting, it
        return `alias` itself.

        :param key: an alias
        :type key: str
        :rtype: str
        '''
        return self.alias_arg_map.get(alias, alias)

    def cast(self, arg_name, val):
        '''Cast `val` by `arg_name`.

        :param arg_name: an argument name
        :type arg_name: str
        :param val: a value
        :type val: any
        :rtype: any
        '''
        meta = self.arg_meta_map.get(arg_name)
        if meta is not None:
            meta = meta.strip('<>').lower()
        type = self.arg_type_map[meta]
        return type(val)

    def parse(self, raw_args=None):
        """Parse the raw arguments.

        :param raw_args: raw arguments
        :type raw_args: a list or a str
        :rtype: double-tuple: (pargs, kargs)

        .. versionadded:: 0.1.5

        Here are examples:

        >>> def repeat(message, times=2, count=False):
        ...     '''It repeats the message.
        ...
        ...     -m=<str>, --message=<str>  The description of this option.
        ...     -t=<int>, --times=<int>
        ...     -c, --count
        ...     '''
        ...     s = message * times
        ...     return len(s) if count else s
        ...
        >>> repeat('string', 3)
        'stringstringstring'

        Make a :class:`~clime.core.Command` instance:

        >>> repeat_cmd = Command(repeat)
        >>> repeat_cmd.build_usage()
        'repeat [-t<int> | --times=<int>] [-c | --count] <message>'
        >>> repeat_cmd.execute('Hi!')
        'Hi!Hi!'

        You can also use options (keyword arguments) to assign arguments
        (positional arguments):

        >>> repeat_cmd.execute('--message=Hi!')
        'Hi!Hi!'
        >>> repeat_cmd.execute('--message Hi!')
        'Hi!Hi!'

        The short version defined in docstring:

        >>> repeat_cmd.execute('-mHi!')
        'Hi!Hi!'
        >>> repeat_cmd.execute('-m=Hi!')
        'Hi!Hi!'
        >>> repeat_cmd.execute('-m Hi!')
        'Hi!Hi!'

        It counts how many times options appear, if you don't specify a value:

        >>> repeat_cmd.execute('Hi! --times=4')
        'Hi!Hi!Hi!Hi!'
        >>> repeat_cmd.execute('Hi! -tttt')
        'Hi!Hi!Hi!Hi!'

        However, if a default value is a boolean, it just switches the boolean
        value and does it only one time.

        Mix them all:

        >>> repeat_cmd.execute('-m Hi! -tttt --count')
        12
        >>> repeat_cmd.execute('-m Hi! -ttctt')
        12
        >>> repeat_cmd.execute('-ttcttmHi!')
        12
        >>> repeat_cmd.execute('-ttccttmHi!')
        12

        It is also supported to collect arbitrary arguments:

        >>> def everything(*args, **kargs):
        ...     return args, kargs

        >>> everything_cmd = Command(everything)
        >>> everything_cmd.build_usage()
        'everything [--<key>=<value>...] [<args>...]'

        >>> everything_cmd.execute('1 2 3')
        ((1, 2, 3), {})

        >>> everything_cmd.execute('--x=1 --y=2 --z=3')
        ((), {'y': 2, 'x': 1, 'z': 3})
        """

        if raw_args is None:
            raw_args = sys.argv[1:]
        elif isinstance(raw_args, str):
            raw_args = raw_args.split()

        # collect arguments from the raw arguments

        pargs = []
        kargs = defaultdict(list)

        while raw_args:

            key = None
            val = Empty
            arg_name = None

            if raw_args[0].startswith('-') and len(raw_args[0]) >= 2:

                # '-m=hello' or '--msg=hello'
                key, _, val = raw_args.pop(0).partition('=')

                if key.startswith('--'):
                    key = key[2:].replace('-', '_')
                else:

                    # find the start index (sep) of value
                    # '-nnn'       -> sep=4 (the length of this str)
                    # '-nnnmhello' -> sep=5 (the char 'h')
                    sep = 1
                    for c in key[1:]:
                        if c in self.arg_name_set or c in self.alias_arg_map:
                            sep += 1
                        else:
                            break

                    # handle the bool option sequence
                    # '-nnn'       -> 'nn'
                    # '-nnnmhello' -> 'nnn'
                    for c in key[1:sep-1]:
                        arg_name = self.dealias(c)
                        kargs[arg_name].append(Empty)

                    # handle the last option
                    # '-m=hello' (val->'hello') or '-mhello' (val->'')
                    if not val:
                        val = key[sep:] or Empty
                    key = key[sep-1]
                    # '-nnn'       -> key='n', val=Empty
                    # '-nnnmhello' -> key='m', val='hello'

                if not val:
                    # ['-m', 'hello'] or ['--msg', 'hello']
                    if raw_args and not raw_args[0].startswith('-'):
                        val = raw_args.pop(0)
            else:
                val = raw_args.pop(0)

            if key:
                arg_name = self.dealias(key)
                kargs[arg_name].append(val)
            else:
                pargs.append(val)

        # compact the collected kargs
        kargs = dict(kargs)
        for arg_name, collected_vals in kargs.items():
            default = self.arg_default_map.get(arg_name)
            if isinstance(default, bool):
                # switch the boolean value if default is a bool
                kargs[arg_name] = not default
            elif all(val is Empty for val in collected_vals):
                if isinstance(default, int):
                    kargs[arg_name] = len(collected_vals)
                else:
                    kargs[arg_name] = None
            else:
                # take the last value
                val = next(val for val in reversed(collected_vals) if val is not Empty)
                # cast this key arg
                if not self.keyarg_name or arg_name in self.arg_meta_map:
                    kargs[arg_name] = self.cast(arg_name, val)
                else:
                    kargs[arg_name] = self.cast(self.keyarg_name, val)

        # add the defaults to kargs
        for arg_name, default in self.arg_default_map.items():
            if arg_name not in kargs:
                kargs[arg_name] = default

        # keyword-first resolving
        isbuiltin = inspect.isbuiltin(self.func)
        for pos, name in enumerate(self.arg_names):
            if name in kargs and (pos < len(pargs) or isbuiltin):
                pargs.insert(pos, kargs.pop(name))

        # cast the pos args
        for i, parg in enumerate(pargs):
            if i < self.no_defult_args_len:
                pargs[i] = self.cast(self.arg_names[i], parg)
            elif self.vararg_name:
                pargs[i] = self.cast(self.vararg_name, parg)

        return (pargs, kargs)

    scan = parse
    '''
    .. deprecated:: 0.1.5
        Use :py:meth:`Command.parse` instead.
    '''

    def execute(self, raw_args=None):
        '''Execute this command with `raw_args`.

        :param raw_args: raw arguments
        :type raw_args: a list or a str
        :rtype: any
        '''

        pargs, kargs = self.parse(raw_args)
        return self.func(*pargs, **kargs)

    def build_usage(self, without_name=False):
        '''Build the usage of this command.

        :param without_name: Make it return an usage without the function name.
        :type without_name: bool
        :rtype: str
        '''

        # build reverse alias map
        alias_arg_rmap = {}
        for alias, arg_name in self.alias_arg_map.items():
            aliases = alias_arg_rmap.setdefault(arg_name, [])
            aliases.append(alias)

        usage = []

        # build the arguments which have default value
        if self.arg_defaults:
            for arg_name in self.arg_names[-len(self.arg_defaults):]:

                pieces = []
                for name in alias_arg_rmap.get(arg_name, [])+[arg_name]:
                    is_long_opt = len(name) > 1
                    pieces.append('%s%s' % ('-' * (1+is_long_opt), name.replace('_', '-')))
                    meta = self.arg_meta_map.get(name)
                    if meta:
                        if is_long_opt:
                            pieces[-1] += '='+meta
                        else:
                            pieces[-1] += meta

                usage.append('[%s]' % ' | '.join(pieces))

        if self.keyarg_name:
            usage.append('[--<key>=<value>...]')

        # build the arguments which don't have default value
        usage.extend('<%s>' % name.replace('_', '-') for name in self.arg_names[:-len(self.arg_defaults) or None])

        if self.vararg_name:
            usage.append('[<%s>...]' % self.vararg_name.replace('_', '-'))

        if without_name:
            return '%s' % ' '.join(usage)
        else:
            return '%s %s' % ((self.name or self.func.__name__).replace('_', '-'), ' '.join(usage))

    get_usage = build_usage
    '''
    .. deprecated:: 0.2.5
        Use :py:meth:`Command.build_usage` instead.
    '''


CMD_SUFFIX = re.compile('^(?P<name>.*?)_cmd$')
'''
It matches the function whose name ends with ``_cmd``.

The regex is ``^(?P<name>.*?)_cmd$``.

Usually, it is used with :py:func:`start`:

::

    import clime
    clime.start(white_pattern=clime.CMD_SUFFIX)
'''

class Program(object):
    '''Convert a module or mapping into a multi-command CLI program.

    .. seealso::
        There is a shortcut of using :py:class:`Program` --- :py:func:`start`.

    :param obj: an `object` you want to convert
    :type obj: a module or a mapping

    :param default: the default command name
    :type default: str

    :param white_list: the white list of commands; By default, it uses the attribute, ``__all__``, of a module.
    :type white_list: list

    :param white_pattern: the white pattern of commands; The regex should have a group named ``name``.
    :type white_pattern: RegexObject

    :param black_list: the black list of commands
    :type black_list: list

    :param ignore_help: Let it treat ``--help`` or ``-h`` as a normal argument.
    :type ignore_help: bool

    :param ignore_return: Make it prevent printing the return value.
    :type ignore_return: bool

    :param name: the name of this program; It is used to show error messages. By default, it takes the first arguments from CLI.
    :type name: str

    :param doc: the documentation for this program
    :type doc: str

    :param debug: It prints a full traceback if it is True.
    :type name: bool

    .. versionchanged:: 0.3
        The ``-h`` option also trigger help text now.

    .. versionadded:: 0.1.9
        Added `white_pattern`.

    .. versionadded:: 0.1.6
        Added `ignore_return`.

    .. versionadded:: 0.1.5
        Added `white_list`, `black_list`, `ignore_help`, `doc` and `debug`.

    .. versionchanged:: 0.1.5
        Renamed `defcmd` and `progname`.

    .. versionchanged:: 0.1.4
       It is almost rewritten.
    '''

    def __init__(self, obj=None, default=None, white_list=None, white_pattern=None, black_list=None, ignore_help=False, ignore_return=False, name=None, doc=None, debug=False):

        obj = obj or sys.modules['__main__']
        self.obj = obj

        if hasattr(obj, 'items'):
            obj_items = obj.items()
        else:
            obj_items = inspect.getmembers(obj)

        if not white_list and hasattr(obj, '__all__'):
            white_list = obj.__all__

        tests = (inspect.isbuiltin, inspect.isfunction, inspect.ismethod)

        self.command_funcs = {}
        for obj_name, obj in obj_items:

            if obj_name.startswith('_'): continue
            if not any(test(obj) for test in tests): continue
            if white_list is not None and obj_name not in white_list: continue
            if black_list is not None and obj_name in black_list: continue

            if white_pattern:
                match = white_pattern.match(obj_name)
                if not match: continue
                obj_name = match.group('name')

            self.command_funcs[obj_name] = obj

        self.default = default
        if len(self.command_funcs) == 1:
            self.default = self.command_funcs.keys()[0]

        self.ignore_help = ignore_help
        self.ignore_return = ignore_return
        self.name = name or basename(sys.argv[0])
        self.doc = doc
        self.debug = debug

    def complain(self, msg):
        '''Print `msg` with the name of this program to `stderr`.'''
        print >> sys.stderr, '%s: %s' % (self.name, msg)

    def main(self, raw_args=None):
        '''Start to parse the raw arguments and send them to a
        :py:class:`~clime.core.Command` instance.

        :param raw_args: The arguments from command line. By default, it takes from ``sys.argv``.
        :type raw_args: list
        '''

        if raw_args is None:
            raw_args = sys.argv[1:]
        elif isinstance(raw_args, str):
            raw_args = raw_args.split()

        # try to find a command name in the raw arguments.
        cmd_name = None
        cmd_func = None

        if len(raw_args) == 0:
            pass
        elif not self.ignore_help and raw_args[0] in ('--help', '-h'):
            self.print_usage()
            return
        else:
            cmd_func = self.command_funcs.get(raw_args[0].replace('-', '_'))
            if cmd_func is not None:
                cmd_name = raw_args.pop(0).replace('-', '_')

        if cmd_func is None:
            # we can't find a command name in normal procedure
            if self.default:
                cmd_name = cmd_name
                cmd_func = self.command_funcs[self.default]
            else:
                self.print_usage()
                return

        if not self.ignore_help and '--help' in raw_args:
            # the user requires help of this command
            self.print_usage(cmd_name)
            return

        # convert the function to a Command object
        cmd = Command(cmd_func, cmd_name)

        try:
            # execute the command with the raw arguments
            return_val = cmd.execute(raw_args)
        except BaseException, e:
            if self.debug:
                from traceback import print_exception
                print_exception(*sys.exc_info())
            else:
                self.complain(e)
            sys.exit(1)

        if not self.ignore_return and return_val is not None:
            if inspect.isgenerator(return_val):
                for i in return_val:
                    print i
            else:
                print return_val

    def print_usage(self, cmd_name=None):
        '''Print the usage(s) of all commands or a command.'''

        def append_usage(cmd_name, without_name=False):
            # nonlocal usages
            cmd_func = self.command_funcs[cmd_name]
            usages.append(Command(cmd_func, cmd_name).build_usage(without_name))

        usages = []
        cmd_func = None

        if cmd_name is None:
            # prepare all usages
            if self.default is not None:
                append_usage(self.default, True)
            for name in sorted(self.command_funcs.keys()):
                append_usage(name)
        else:
            # prepare the usage of a command
            if self.default == cmd_name:
                append_usage(cmd_name, without_name=True)
            append_usage(cmd_name)

        # print the usages
        iusages = iter(usages)
        print 'usage:', next(iusages)
        for usage in iusages:
            print '   or:', usage

        # find the doc

        # find the module-level doc
        if cmd_name is None:
            if self.doc:
                doc = self.doc
            elif inspect.ismodule(self.obj):
                doc = inspect.getdoc(self.obj)
            else:
                doc = None

            # fallback to default command if still not found
            if not doc:
                cmd_name = self.default

        if cmd_name:
            doc = inspect.getdoc(self.command_funcs[cmd_name])

        # print the doc
        if doc:
            print
            print doc
            print

def start(*args, **kargs):
    '''It is same as ``Program(*args, **kargs).main()``.

    .. versionchanged:: 1.0
        renamed from `customize` to `start`

    .. versionadded:: 0.1.6

    .. seealso::
        :py:class:`Program` has the detail of arguments.
    '''

    prog = Program(*args, **kargs)
    prog.main()

    return prog

# for backward compatibility
customize = start
'''
.. deprecated:: 0.1.6
    Use :py:func:`start` instead.
'''

if __name__ == '__main__':

    import doctest
    doctest.testmod()

    def read_json(json=None):
        '''
        options:
            --json=<json>
        '''
        return json

    read_json_cmd = Command(read_json)

    print '---'
    print read_json_cmd.build_usage()
    print read_json_cmd.execute('[1,2,3]')
    print read_json_cmd.execute(['--json', '{"x": 1}'])
    print '---'

    prog = Program(white_list=['read_json'], debug=True)
    prog.main()
    # python -m clime.core read-json --help
    # python -m clime.core read-json '{"x": 1}'
    # python -m clime.core read-json --json='{"x":1}'

########NEW FILE########
__FILENAME__ = now
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from . import core
core.start()

########NEW FILE########
__FILENAME__ = util
#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''It contains the helper functions.'''

import inspect

def json(s):
    '''Convert a JSON string `s` into a Python's type.'''
    import json
    return json.loads(s)

def autotype(s):
    '''Automatively detect the type (int, float or string) of `s` and convert
    `s` into it.'''

    if not isinstance(s, str):
        return s

    if s.isdigit():
        return int(s)

    try:
        return float(s)
    except ValueError:
        return s

def getargspec(func):
    '''Get the argument specification of `func`.

    :param func: The target.
    :type func: a python function, built-in function or bound method
    :rtype: (args, varargs, keywords, defaults)

    It gets the argument specification by parsing documentation of the
    function if `func` is a built-in function.

    .. versionchanged:: 0.1.4
       Remove `self` automatively if `func` is a method.

    .. versionadded:: 0.1.3
    '''

    if inspect.isfunction(func):
        return inspect.getargspec(func)

    if inspect.ismethod(func):
        argspec = inspect.getargspec(func)
        argspec[0].pop(0)
        return argspec

    def strbetween(s, a, b):
        return s[s.find(a): s.rfind(b)]

    argspecdoc = (inspect.getdoc(func) or '').split('\n')[0]
    argpart = strbetween(argspecdoc, '(', ')')
    args = argpart.split(',')
    args = (arg.strip(' ()[]') for arg in args)
    args = [arg for arg in args if arg]

    defaultpart = strbetween(argspecdoc, '[', ']')
    defaultcount = len([d for d in defaultpart.split(',') if d.strip('[]')])

    return (args, None, None, (None,) * defaultcount or None)

########NEW FILE########
__FILENAME__ = __main__
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import imp
from .core import Program, start

def convert(target, *args, **kargs):

    module = None

    try:
        module = __import__(target)
    except ImportError:
        module = imp.load_source('tmp', target)

    prog = Program(module)
    prog.main(sys.argv[2:])

# This function is used by the command script installed in system.
def run():
    sys.argv[0] = 'clime'
    start({'convert': convert})

if __name__ == '__main__':
    # ``python -m clime`` will go here.
    run()

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# Clime documentation build configuration file, created by
# sphinx-quickstart on Mon Mar 19 21:47:40 2012.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os

# search the parent folder for the Clime with this tarball
sys.path.insert(0, os.popen('git rev-parse --show-toplevel 2> /dev/null').read().strip())

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#sys.path.insert(0, os.path.abspath('.'))

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.todo', 'sphinx.ext.viewcode', 'sphinx.ext.doctest']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'Clime'
copyright = u'2013, Mosky'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.

from clime import __version__

# The short X.Y version.
version = 'v' + '.'.join(__version__.split('.')[:2])
# The full version, including alpha/beta/rc tags.
release = 'v' + __version__

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
html_theme = 'nature'

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
htmlhelp_basename = 'Climedoc'


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
  ('index', 'Clime.tex', u'Clime Documentation',
   u'Mosky', 'manual'),
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
    ('index', 'clime', u'Clime Documentation',
     [u'Mosky'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'Clime', u'Clime Documentation',
   u'Mosky', 'Clime', 'One line description of project.',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'

# Mosky's settings

def skip_inner_members(app, what, name, obj, skip, options):
    if name in ('__dict__', '__doc__', '__module__', '__init__', '__weakref__'):
        return True
    else:
        return False

def display_call_method(app, what, name, obj, skip, options):
    if name == '__call__':
        return False
    else:
        return skip

def setup(app):
    app.connect('autodoc-skip-member', display_call_method)

########NEW FILE########
__FILENAME__ = calc
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from math import ceil, floor, factorial, pow, sqrt, log

if __name__ == '__main__':
    from clime import now

########NEW FILE########
__FILENAME__ = climebox
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: noet sts=4:ts=4:sw=4
# author: takano32 <tak@no32 dot tk>
#

def climebox_usage():
	# TODO: default command
	clime.Program().printusage()

def climebox_dirname(file_name):
	# http://docs.python.org/release/2.7.3/library/os.path.html#module-os.path
	print(os.path.dirname(file_name))

def climebox_false():
	exit(1)

def climebox_pwd():
	# http://docs.python.org/release/2.7.3/library/os.path.html#module-os.path
	print(os.getcwd())

if __name__ == '__main__':
	import clime
	import sys, os
	import inspect
	execname = os.path.basename(sys.argv[0])

	if execname == 'climebox' or execname == 'climebox.py':
		clime.Program(defcmdname = 'climebox_usage').main()
		exit(0)

	import __main__
	for cmdname in clime.Program().cmdfs.keys():
		attr = getattr(__main__, cmdname)
		cmdname = 'climebox_' + execname
		if cmdname == attr.func_name:
			clime.Program(defcmdname = cmdname, progname = execname).main()



########NEW FILE########
__FILENAME__ = cmd_suffix
#!/usr/bin/env python
# -*- coding: utf-8 -*-

def say(word, name=None):
    if name:
        print '%s, %s!' % (word, name)
    else:
        print '%s!' % word

def hi_cmd(name=None):
    say('Hi', name)

def hello_cmd(name=None):
    say('Hello', name)

if __name__ == '__main__':
    import clime
    clime.start(white_pattern=clime.CMD_SUFFIX)

########NEW FILE########
__FILENAME__ = lineno
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys

def lineno(start=0):
    for i, line in enumerate(sys.stdin, start):
        sys.stdout.write('%3d| %s' % (i, line))

if __name__ == '__main__':
    import clime.now

########NEW FILE########
__FILENAME__ = pyramid
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# file: pyramid.py

def draw(story, squash=1):
    '''It draws a pyramid.

    -s <int>, --squash=<int>
    '''

    ground_len = 1 + (story-1) * squash * 2

    for i in range(1, ground_len+1, squash*2):
        print ('*'*i).center(ground_len)

if __name__ == '__main__':
    import clime.now

########NEW FILE########
__FILENAME__ = repeat
#!/usr/bin/env python
# -*- coding: utf-8 -*-

def repeat(message, times=2, count=False):
    '''It repeats the message.

    options:
        -m=<str>, --message=<str>  The message you want to repeat.
        -t=<int>, --times=<int>    How many times?
        -c, --count                Count it?
    '''

    s = message * times
    return len(s) if count else s

if __name__ == '__main__':
    import clime.now

########NEW FILE########
__FILENAME__ = reverse
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from sys import getfilesystemencoding as _getfilesystemencoding

ENCODING = _getfilesystemencoding()

def reverse(x):
    '''We assume it is a helper function for something else.

    It returns True to let other stuff work.
    '''

    if not isinstance(x, basestring):
        x = unicode(x)

    if isinstance(x, str):
        x = unicode(x, ENCODING)

    print x[::-1].decode(ENCODING)

    return x

if __name__ == '__main__':
    import clime
    clime.start(ignore_return=True)

########NEW FILE########
__FILENAME__ = test
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest
from clime import Command
from clime.util import *

class TestClime(unittest.TestCase):

    def test_util_autotype(self):
        cases   = ('string', '100', '100.0', None)
        answers = ('string',  100 ,  100.0 , None)
        for case, answer in zip(cases, answers):
            self.assertEqual(autotype(case), answer)

    def test_util_getargspec(self):

        docs = [
            None,
            '',
            'abcd',
            'f1()',
            'f2(x)',
            'f3(x, y)',
            'f4(x[, a])',
            'f5(x, y[, a])',
            'f6(x, y[, a[, b]])',
            'f7([a])',
            'f8([a[, b]])',
        ]

        answers = [
            ([], 0),
            ([], 0),
            ([], 0),
            ([], 0),
            (['x'], 0),
            (['x', 'y'], 0),
            (['x', 'a'], 1),
            (['x', 'y', 'a'], 1),
            (['x', 'y', 'a', 'b'], 2),
            (['a'], 1),
            (['a', 'b'], 2),
        ]

        f = type('Dummy', tuple(), {'__doc__': None})()
        trans = lambda x: (x[0], len(x[-1] or []))

        for doc, answer in zip(docs, answers):
            f.__doc__ = doc
            self.assertEqual(trans(getargspec(f)), answer)

    def test_command_arg_re(self):

        cases = [
            '--key meta',
            '--key=meta',
        ]

        for case in cases:
            self.assertEqual(Command.arg_re.match(case).group('key', 'meta'), ('key', 'meta'))

        cases = [
            '-k meta',
            '-k=meta',
            '-kmeta',
        ]

        for case in cases:
            self.assertEqual(Command.arg_re.match(case).group('key', 'meta'), ('k', 'meta'))

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
