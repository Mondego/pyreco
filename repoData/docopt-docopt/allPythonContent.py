__FILENAME__ = conftest
import re
try:
    import json
except ImportError:
    import simplejson as json

import pytest

import docopt


def pytest_collect_file(path, parent):
    if path.ext == ".docopt" and path.basename.startswith("test"):
        return DocoptTestFile(path, parent)


def parse_test(raw):
    raw = re.compile('#.*$', re.M).sub('', raw).strip()
    if raw.startswith('"""'):
        raw = raw[3:]

    for fixture in raw.split('r"""'):
        name = ''
        doc, _, body = fixture.partition('"""')
        cases = []
        for case in body.split('$')[1:]:
            argv, _, expect = case.strip().partition('\n')
            expect = json.loads(expect)
            prog, _, argv = argv.strip().partition(' ')
            cases.append((prog, argv, expect))

        yield name, doc, cases


class DocoptTestFile(pytest.File):

    def collect(self):
        raw = self.fspath.open().read()
        index = 1

        for name, doc, cases in parse_test(raw):
            name = self.fspath.purebasename
            for case in cases:
                yield DocoptTestItem("%s(%d)" % (name, index), self, doc, case)
                index += 1


class DocoptTestItem(pytest.Item):

    def __init__(self, name, parent, doc, case):
        super(DocoptTestItem, self).__init__(name, parent)
        self.doc = doc
        self.prog, self.argv, self.expect = case

    def runtest(self):
        try:
            result = docopt.docopt(self.doc, argv=self.argv)
        except docopt.DocoptExit:
            result = 'user-error'

        if self.expect != result:
            raise DocoptTestException(self, result)

    def repr_failure(self, excinfo):
        """Called when self.runtest() raises an exception."""
        if isinstance(excinfo.value, DocoptTestException):
            return "\n".join((
                "usecase execution failed:",
                self.doc.rstrip(),
                "$ %s %s" % (self.prog, self.argv),
                "result> %s" % json.dumps(excinfo.value.args[1]),
                "expect> %s" % json.dumps(self.expect),
            ))

    def reportinfo(self):
        return self.fspath, 0, "usecase: %s" % self.name


class DocoptTestException(Exception):
    pass

########NEW FILE########
__FILENAME__ = docopt
"""Pythonic command-line interface parser that will make you smile.

 * http://docopt.org
 * Repository and issue-tracker: https://github.com/docopt/docopt
 * Licensed under terms of MIT license (see LICENSE-MIT)
 * Copyright (c) 2013 Vladimir Keleshev, vladimir@keleshev.com

"""
import sys
import re


__all__ = ['docopt']
__version__ = '0.6.1'


class DocoptLanguageError(Exception):

    """Error in construction of usage-message by developer."""


class DocoptExit(SystemExit):

    """Exit in case user invoked program with incorrect arguments."""

    usage = ''

    def __init__(self, message=''):
        SystemExit.__init__(self, (message + '\n' + self.usage).strip())


class Pattern(object):

    def __eq__(self, other):
        return repr(self) == repr(other)

    def __hash__(self):
        return hash(repr(self))

    def fix(self):
        self.fix_identities()
        self.fix_repeating_arguments()
        return self

    def fix_identities(self, uniq=None):
        """Make pattern-tree tips point to same object if they are equal."""
        if not hasattr(self, 'children'):
            return self
        uniq = list(set(self.flat())) if uniq is None else uniq
        for i, child in enumerate(self.children):
            if not hasattr(child, 'children'):
                assert child in uniq
                self.children[i] = uniq[uniq.index(child)]
            else:
                child.fix_identities(uniq)

    def fix_repeating_arguments(self):
        """Fix elements that should accumulate/increment values."""
        either = [list(child.children) for child in transform(self).children]
        for case in either:
            for e in [child for child in case if case.count(child) > 1]:
                if type(e) is Argument or type(e) is Option and e.argcount:
                    if e.value is None:
                        e.value = []
                    elif type(e.value) is not list:
                        e.value = e.value.split()
                if type(e) is Command or type(e) is Option and e.argcount == 0:
                    e.value = 0
        return self


def transform(pattern):
    """Expand pattern into an (almost) equivalent one, but with single Either.

    Example: ((-a | -b) (-c | -d)) => (-a -c | -a -d | -b -c | -b -d)
    Quirks: [-a] => (-a), (-a...) => (-a -a)

    """
    result = []
    groups = [[pattern]]
    while groups:
        children = groups.pop(0)
        parents = [Required, Optional, OptionsShortcut, Either, OneOrMore]
        if any(t in map(type, children) for t in parents):
            child = [c for c in children if type(c) in parents][0]
            children.remove(child)
            if type(child) is Either:
                for c in child.children:
                    groups.append([c] + children)
            elif type(child) is OneOrMore:
                groups.append(child.children * 2 + children)
            else:
                groups.append(child.children + children)
        else:
            result.append(children)
    return Either(*[Required(*e) for e in result])


class LeafPattern(Pattern):

    """Leaf/terminal node of a pattern tree."""

    def __init__(self, name, value=None):
        self.name, self.value = name, value

    def __repr__(self):
        return '%s(%r, %r)' % (self.__class__.__name__, self.name, self.value)

    def flat(self, *types):
        return [self] if not types or type(self) in types else []

    def match(self, left, collected=None):
        collected = [] if collected is None else collected
        pos, match = self.single_match(left)
        if match is None:
            return False, left, collected
        left_ = left[:pos] + left[pos + 1:]
        same_name = [a for a in collected if a.name == self.name]
        if type(self.value) in (int, list):
            if type(self.value) is int:
                increment = 1
            else:
                increment = ([match.value] if type(match.value) is str
                             else match.value)
            if not same_name:
                match.value = increment
                return True, left_, collected + [match]
            same_name[0].value += increment
            return True, left_, collected
        return True, left_, collected + [match]


class BranchPattern(Pattern):

    """Branch/inner node of a pattern tree."""

    def __init__(self, *children):
        self.children = list(children)

    def __repr__(self):
        return '%s(%s)' % (self.__class__.__name__,
                           ', '.join(repr(a) for a in self.children))

    def flat(self, *types):
        if type(self) in types:
            return [self]
        return sum([child.flat(*types) for child in self.children], [])


class Argument(LeafPattern):

    def single_match(self, left):
        for n, pattern in enumerate(left):
            if type(pattern) is Argument:
                return n, Argument(self.name, pattern.value)
        return None, None

    @classmethod
    def parse(class_, source):
        name = re.findall('(<\S*?>)', source)[0]
        value = re.findall('\[default: (.*)\]', source, flags=re.I)
        return class_(name, value[0] if value else None)


class Command(Argument):

    def __init__(self, name, value=False):
        self.name, self.value = name, value

    def single_match(self, left):
        for n, pattern in enumerate(left):
            if type(pattern) is Argument:
                if pattern.value == self.name:
                    return n, Command(self.name, True)
                else:
                    break
        return None, None


class Option(LeafPattern):

    def __init__(self, short=None, long=None, argcount=0, value=False):
        assert argcount in (0, 1)
        self.short, self.long, self.argcount = short, long, argcount
        self.value = None if value is False and argcount else value

    @classmethod
    def parse(class_, option_description):
        short, long, argcount, value = None, None, 0, False
        options, _, description = option_description.strip().partition('  ')
        options = options.replace(',', ' ').replace('=', ' ')
        for s in options.split():
            if s.startswith('--'):
                long = s
            elif s.startswith('-'):
                short = s
            else:
                argcount = 1
        if argcount:
            matched = re.findall('\[default: (.*)\]', description, flags=re.I)
            value = matched[0] if matched else None
        return class_(short, long, argcount, value)

    def single_match(self, left):
        for n, pattern in enumerate(left):
            if self.name == pattern.name:
                return n, pattern
        return None, None

    @property
    def name(self):
        return self.long or self.short

    def __repr__(self):
        return 'Option(%r, %r, %r, %r)' % (self.short, self.long,
                                           self.argcount, self.value)


class Required(BranchPattern):

    def match(self, left, collected=None):
        collected = [] if collected is None else collected
        l = left
        c = collected
        for pattern in self.children:
            matched, l, c = pattern.match(l, c)
            if not matched:
                return False, left, collected
        return True, l, c


class Optional(BranchPattern):

    def match(self, left, collected=None):
        collected = [] if collected is None else collected
        for pattern in self.children:
            m, left, collected = pattern.match(left, collected)
        return True, left, collected


class OptionsShortcut(Optional):

    """Marker/placeholder for [options] shortcut."""


class OneOrMore(BranchPattern):

    def match(self, left, collected=None):
        assert len(self.children) == 1
        collected = [] if collected is None else collected
        l = left
        c = collected
        l_ = None
        matched = True
        times = 0
        while matched:
            # could it be that something didn't match but changed l or c?
            matched, l, c = self.children[0].match(l, c)
            times += 1 if matched else 0
            if l_ == l:
                break
            l_ = l
        if times >= 1:
            return True, l, c
        return False, left, collected


class Either(BranchPattern):

    def match(self, left, collected=None):
        collected = [] if collected is None else collected
        outcomes = []
        for pattern in self.children:
            matched, _, _ = outcome = pattern.match(left, collected)
            if matched:
                outcomes.append(outcome)
        if outcomes:
            return min(outcomes, key=lambda outcome: len(outcome[1]))
        return False, left, collected


class Tokens(list):

    def __init__(self, source, error=DocoptExit):
        self += source.split() if hasattr(source, 'split') else source
        self.error = error

    @staticmethod
    def from_pattern(source):
        source = re.sub(r'([\[\]\(\)\|]|\.\.\.)', r' \1 ', source)
        source = [s for s in re.split('\s+|(\S*<.*?>)', source) if s]
        return Tokens(source, error=DocoptLanguageError)

    def move(self):
        return self.pop(0) if len(self) else None

    def current(self):
        return self[0] if len(self) else None


def parse_long(tokens, options):
    """long ::= '--' chars [ ( ' ' | '=' ) chars ] ;"""
    long, eq, value = tokens.move().partition('=')
    assert long.startswith('--')
    value = None if eq == value == '' else value
    similar = [o for o in options if o.long == long]
    if tokens.error is DocoptExit and similar == []:  # if no exact match
        similar = [o for o in options if o.long and o.long.startswith(long)]
    if len(similar) > 1:  # might be simply specified ambiguously 2+ times?
        raise tokens.error('%s is not a unique prefix: %s?' %
                           (long, ', '.join(o.long for o in similar)))
    elif len(similar) < 1:
        argcount = 1 if eq == '=' else 0
        o = Option(None, long, argcount)
        options.append(o)
        if tokens.error is DocoptExit:
            o = Option(None, long, argcount, value if argcount else True)
    else:
        o = Option(similar[0].short, similar[0].long,
                   similar[0].argcount, similar[0].value)
        if o.argcount == 0:
            if value is not None:
                raise tokens.error('%s must not have an argument' % o.long)
        else:
            if value is None:
                if tokens.current() in [None, '--']:
                    raise tokens.error('%s requires argument' % o.long)
                value = tokens.move()
        if tokens.error is DocoptExit:
            o.value = value if value is not None else True
    return [o]


def parse_shorts(tokens, options):
    """shorts ::= '-' ( chars )* [ [ ' ' ] chars ] ;"""
    token = tokens.move()
    assert token.startswith('-') and not token.startswith('--')
    left = token.lstrip('-')
    parsed = []
    while left != '':
        short, left = '-' + left[0], left[1:]
        similar = [o for o in options if o.short == short]
        if len(similar) > 1:
            raise tokens.error('%s is specified ambiguously %d times' %
                               (short, len(similar)))
        elif len(similar) < 1:
            o = Option(short, None, 0)
            options.append(o)
            if tokens.error is DocoptExit:
                o = Option(short, None, 0, True)
        else:  # why copying is necessary here?
            o = Option(short, similar[0].long,
                       similar[0].argcount, similar[0].value)
            value = None
            if o.argcount != 0:
                if left == '':
                    if tokens.current() in [None, '--']:
                        raise tokens.error('%s requires argument' % short)
                    value = tokens.move()
                else:
                    value = left
                    left = ''
            if tokens.error is DocoptExit:
                o.value = value if value is not None else True
        parsed.append(o)
    return parsed


def parse_pattern(source, options):
    tokens = Tokens.from_pattern(source)
    result = parse_expr(tokens, options)
    if tokens.current() is not None:
        raise tokens.error('unexpected ending: %r' % ' '.join(tokens))
    return Required(*result)


def parse_expr(tokens, options):
    """expr ::= seq ( '|' seq )* ;"""
    seq = parse_seq(tokens, options)
    if tokens.current() != '|':
        return seq
    result = [Required(*seq)] if len(seq) > 1 else seq
    while tokens.current() == '|':
        tokens.move()
        seq = parse_seq(tokens, options)
        result += [Required(*seq)] if len(seq) > 1 else seq
    return [Either(*result)] if len(result) > 1 else result


def parse_seq(tokens, options):
    """seq ::= ( atom [ '...' ] )* ;"""
    result = []
    while tokens.current() not in [None, ']', ')', '|']:
        atom = parse_atom(tokens, options)
        if tokens.current() == '...':
            atom = [OneOrMore(*atom)]
            tokens.move()
        result += atom
    return result


def parse_atom(tokens, options):
    """atom ::= '(' expr ')' | '[' expr ']' | 'options'
             | long | shorts | argument | command ;
    """
    token = tokens.current()
    result = []
    if token in '([':
        tokens.move()
        matching, pattern = {'(': [')', Required], '[': [']', Optional]}[token]
        result = pattern(*parse_expr(tokens, options))
        if tokens.move() != matching:
            raise tokens.error("unmatched '%s'" % token)
        return [result]
    elif token == 'options':
        tokens.move()
        return [OptionsShortcut()]
    elif token.startswith('--') and token != '--':
        return parse_long(tokens, options)
    elif token.startswith('-') and token not in ('-', '--'):
        return parse_shorts(tokens, options)
    elif token.startswith('<') and token.endswith('>') or token.isupper():
        return [Argument(tokens.move())]
    else:
        return [Command(tokens.move())]


def parse_argv(tokens, options, options_first=False):
    """Parse command-line argument vector.

    If options_first:
        argv ::= [ long | shorts ]* [ argument ]* [ '--' [ argument ]* ] ;
    else:
        argv ::= [ long | shorts | argument ]* [ '--' [ argument ]* ] ;

    """
    parsed = []
    while tokens.current() is not None:
        if tokens.current() == '--':
            return parsed + [Argument(None, v) for v in tokens]
        elif tokens.current().startswith('--'):
            parsed += parse_long(tokens, options)
        elif tokens.current().startswith('-') and tokens.current() != '-':
            parsed += parse_shorts(tokens, options)
        elif options_first:
            return parsed + [Argument(None, v) for v in tokens]
        else:
            parsed.append(Argument(None, tokens.move()))
    return parsed


def parse_defaults(doc):
    defaults = []
    for s in parse_section('options:', doc):
        # FIXME corner case "bla: options: --foo"
        _, _, s = s.partition(':')  # get rid of "options:"
        split = re.split('\n[ \t]*(-\S+?)', '\n' + s)[1:]
        split = [s1 + s2 for s1, s2 in zip(split[::2], split[1::2])]
        options = [Option.parse(s) for s in split if s.startswith('-')]
        defaults += options
    return defaults


def parse_section(name, source):
    pattern = re.compile('^([^\n]*' + name + '[^\n]*\n?(?:[ \t].*?(?:\n|$))*)',
                         re.IGNORECASE | re.MULTILINE)
    return [s.strip() for s in pattern.findall(source)]


def formal_usage(section):
    _, _, section = section.partition(':')  # drop "usage:"
    pu = section.split()
    return '( ' + ' '.join(') | (' if s == pu[0] else s for s in pu[1:]) + ' )'


def extras(help, version, options, doc):
    if help and any((o.name in ('-h', '--help')) and o.value for o in options):
        print(doc.strip("\n"))
        sys.exit()
    if version and any(o.name == '--version' and o.value for o in options):
        print(version)
        sys.exit()


class Dict(dict):
    def __repr__(self):
        return '{%s}' % ',\n '.join('%r: %r' % i for i in sorted(self.items()))


def docopt(doc, argv=None, help=True, version=None, options_first=False):
    """Parse `argv` based on command-line interface described in `doc`.

    `docopt` creates your command-line interface based on its
    description that you pass as `doc`. Such description can contain
    --options, <positional-argument>, commands, which could be
    [optional], (required), (mutually | exclusive) or repeated...

    Parameters
    ----------
    doc : str
        Description of your command-line interface.
    argv : list of str, optional
        Argument vector to be parsed. sys.argv[1:] is used if not
        provided.
    help : bool (default: True)
        Set to False to disable automatic help on -h or --help
        options.
    version : any object
        If passed, the object will be printed if --version is in
        `argv`.
    options_first : bool (default: False)
        Set to True to require options precede positional arguments,
        i.e. to forbid options and positional arguments intermix.

    Returns
    -------
    args : dict
        A dictionary, where keys are names of command-line elements
        such as e.g. "--verbose" and "<path>", and values are the
        parsed values of those elements.

    Example
    -------
    >>> from docopt import docopt
    >>> doc = '''
    ... Usage:
    ...     my_program tcp <host> <port> [--timeout=<seconds>]
    ...     my_program serial <port> [--baud=<n>] [--timeout=<seconds>]
    ...     my_program (-h | --help | --version)
    ...
    ... Options:
    ...     -h, --help  Show this screen and exit.
    ...     --baud=<n>  Baudrate [default: 9600]
    ... '''
    >>> argv = ['tcp', '127.0.0.1', '80', '--timeout', '30']
    >>> docopt(doc, argv)
    {'--baud': '9600',
     '--help': False,
     '--timeout': '30',
     '--version': False,
     '<host>': '127.0.0.1',
     '<port>': '80',
     'serial': False,
     'tcp': True}

    See also
    --------
    * For video introduction see http://docopt.org
    * Full documentation is available in README.rst as well as online
      at https://github.com/docopt/docopt#readme

    """
    argv = sys.argv[1:] if argv is None else argv

    usage_sections = parse_section('usage:', doc)
    if len(usage_sections) == 0:
        raise DocoptLanguageError('"usage:" (case-insensitive) not found.')
    if len(usage_sections) > 1:
        raise DocoptLanguageError('More than one "usage:" (case-insensitive).')
    DocoptExit.usage = usage_sections[0]

    options = parse_defaults(doc)
    pattern = parse_pattern(formal_usage(DocoptExit.usage), options)
    # [default] syntax for argument is disabled
    #for a in pattern.flat(Argument):
    #    same_name = [d for d in arguments if d.name == a.name]
    #    if same_name:
    #        a.value = same_name[0].value
    argv = parse_argv(Tokens(argv), list(options), options_first)
    pattern_options = set(pattern.flat(Option))
    for options_shortcut in pattern.flat(OptionsShortcut):
        doc_options = parse_defaults(doc)
        options_shortcut.children = list(set(doc_options) - pattern_options)
        #if any_options:
        #    options_shortcut.children += [Option(o.short, o.long, o.argcount)
        #                    for o in argv if type(o) is Option]
    extras(help, version, argv, doc)
    matched, left, collected = pattern.fix().match(argv)
    if matched and left == []:  # better error message if left?
        return Dict((a.name, a.value) for a in (pattern.flat() + collected))
    raise DocoptExit()

########NEW FILE########
__FILENAME__ = arguments_example
"""Usage: arguments_example.py [-vqrh] [FILE] ...
          arguments_example.py (--left | --right) CORRECTION FILE

Process FILE and optionally apply correction to either left-hand side or
right-hand side.

Arguments:
  FILE        optional input file
  CORRECTION  correction angle, needs FILE, --left or --right to be present

Options:
  -h --help
  -v       verbose mode
  -q       quiet mode
  -r       make report
  --left   use left-hand side
  --right  use right-hand side

"""
from docopt import docopt


if __name__ == '__main__':
    arguments = docopt(__doc__)
    print(arguments)

########NEW FILE########
__FILENAME__ = calculator_example
"""Not a serious example.

Usage:
  calculator_example.py <value> ( ( + | - | * | / ) <value> )...
  calculator_example.py <function> <value> [( , <value> )]...
  calculator_example.py (-h | --help)

Examples:
  calculator_example.py 1 + 2 + 3 + 4 + 5
  calculator_example.py 1 + 2 '*' 3 / 4 - 5    # note quotes around '*'
  calculator_example.py sum 10 , 20 , 30 , 40

Options:
  -h, --help

"""
from docopt import docopt


if __name__ == '__main__':
    arguments = docopt(__doc__)
    print(arguments)

########NEW FILE########
__FILENAME__ = config_file_example
"""Usage:
  quick_example.py tcp [<host>] [--force] [--timeout=<seconds>]
  quick_example.py serial <port> [--baud=<rate>] [--timeout=<seconds>]
  quick_example.py -h | --help | --version

"""
from docopt import docopt


def load_json_config():
    import json
    # Pretend that we load the following JSON file:
    source = '''
        {"--force": true,
         "--timeout": "10",
         "--baud": "9600"}
    '''
    return json.loads(source)


def load_ini_config():
    try:  # Python 2
        from ConfigParser import ConfigParser
        from StringIO import StringIO
    except ImportError:  # Python 3
        from configparser import ConfigParser
        from io import StringIO

    # By using `allow_no_value=True` we are allowed to
    # write `--force` instead of `--force=true` below.
    config = ConfigParser(allow_no_value=True)

    # Pretend that we load the following INI file:
    source = '''
        [default-arguments]
        --force
        --baud=19200
        <host>=localhost
    '''

    # ConfigParser requires a file-like object and
    # no leading whitespace.
    config_file = StringIO('\n'.join(source.split()))
    config.readfp(config_file)

    # ConfigParsers sets keys which have no value
    # (like `--force` above) to `None`. Thus we
    # need to substitute all `None` with `True`.
    return dict((key, True if value is None else value)
                for key, value in config.items('default-arguments'))


def merge(dict_1, dict_2):
    """Merge two dictionaries.

    Values that evaluate to true take priority over falsy values.
    `dict_1` takes priority over `dict_2`.

    """
    return dict((str(key), dict_1.get(key) or dict_2.get(key))
                for key in set(dict_2) | set(dict_1))


if __name__ == '__main__':
    json_config = load_json_config()
    ini_config = load_ini_config()
    arguments = docopt(__doc__, version='0.1.1rc')

    # Arguments take priority over INI, INI takes priority over JSON:
    result = merge(arguments, merge(ini_config, json_config))

    from pprint import pprint
    print('\nJSON config:')
    pprint(json_config)
    print('\nINI config:')
    pprint(ini_config)
    print('\nResult:')
    pprint(result)

########NEW FILE########
__FILENAME__ = counted_example
"""Usage: counted_example.py --help
       counted_example.py -v...
       counted_example.py go [go]
       counted_example.py (--path=<path>)...
       counted_example.py <file> <file>

Try: counted_example.py -vvvvvvvvvv
     counted_example.py go go
     counted_example.py --path ./here --path ./there
     counted_example.py this.txt that.txt

"""
from docopt import docopt


print(docopt(__doc__))

########NEW FILE########
__FILENAME__ = git
#! /usr/bin/env python
"""
usage: git [--version] [--exec-path=<path>] [--html-path]
           [-p|--paginate|--no-pager] [--no-replace-objects]
           [--bare] [--git-dir=<path>] [--work-tree=<path>]
           [-c <name>=<value>] [--help]
           <command> [<args>...]

options:
   -c <name=value>
   -h, --help
   -p, --paginate

The most commonly used git commands are:
   add        Add file contents to the index
   branch     List, create, or delete branches
   checkout   Checkout a branch or paths to the working tree
   clone      Clone a repository into a new directory
   commit     Record changes to the repository
   push       Update remote refs along with associated objects
   remote     Manage set of tracked repositories

See 'git help <command>' for more information on a specific command.

"""
from subprocess import call

from docopt import docopt


if __name__ == '__main__':

    args = docopt(__doc__,
                  version='git version 1.7.4.4',
                  options_first=True)
    print('global arguments:')
    print(args)
    print('command arguments:')

    argv = [args['<command>']] + args['<args>']
    if args['<command>'] == 'add':
        # In case subcommand is implemented as python module:
        import git_add
        print(docopt(git_add.__doc__, argv=argv))
    elif args['<command>'] == 'branch':
        # In case subcommand is a script in some other programming language:
        exit(call(['python', 'git_branch.py'] + argv))
    elif args['<command>'] in 'checkout clone commit push remote'.split():
        # For the rest we'll just keep DRY:
        exit(call(['python', 'git_%s.py' % args['<command>']] + argv))
    elif args['<command>'] in ['help', None]:
        exit(call(['python', 'git.py', '--help']))
    else:
        exit("%r is not a git.py command. See 'git help'." % args['<command>'])

########NEW FILE########
__FILENAME__ = git_add
"""usage: git add [options] [--] [<filepattern>...]

    -h, --help
    -n, --dry-run        dry run
    -v, --verbose        be verbose

    -i, --interactive    interactive picking
    -p, --patch          select hunks interactively
    -e, --edit           edit current diff and apply
    -f, --force          allow adding otherwise ignored files
    -u, --update         update tracked files
    -N, --intent-to-add  record only the fact that the path will be added later
    -A, --all            add all, noticing removal of tracked files
    --refresh            don't add, only refresh the index
    --ignore-errors      just skip files which cannot be added because of errors
    --ignore-missing     check if - even missing - files are ignored in dry run

"""
from docopt import docopt


if __name__ == '__main__':
    print(docopt(__doc__))

########NEW FILE########
__FILENAME__ = git_branch
"""
usage: git branch [options] [-r | -a] [--merged=<commit> | --no-merged=<commit>]
       git branch [options] [-l] [-f] <branchname> [<start-point>]
       git branch [options] [-r] (-d | -D) <branchname>
       git branch [options] (-m | -M) [<oldbranch>] <newbranch>

Generic options
    -h, --help
    -v, --verbose         show hash and subject, give twice for upstream branch
    -t, --track           set up tracking mode (see git-pull(1))
    --set-upstream        change upstream info
    --color=<when>        use colored output
    -r                    act on remote-tracking branches
    --contains=<commit>   print only branches that contain the commit
    --abbrev=<n>          use <n> digits to display SHA-1s

Specific git-branch actions:
    -a                    list both remote-tracking and local branches
    -d                    delete fully merged branch
    -D                    delete branch (even if not merged)
    -m                    move/rename a branch and its reflog
    -M                    move/rename a branch, even if target exists
    -l                    create the branch's reflog
    -f, --force           force creation (when already exists)
    --no-merged=<commit>  print only not merged branches
    --merged=<commit>     print only merged branches

"""
from docopt import docopt


if __name__ == '__main__':
    print(docopt(__doc__))

########NEW FILE########
__FILENAME__ = git_checkout
"""usage: git checkout [options] <branch>
       git checkout [options] <branch> -- <file>...

    -q, --quiet           suppress progress reporting
    -b <branch>           create and checkout a new branch
    -B <branch>           create/reset and checkout a branch
    -l                    create reflog for new branch
    -t, --track           set upstream info for new branch
    --orphan <new branch>
                          new unparented branch
    -2, --ours            checkout our version for unmerged files
    -3, --theirs          checkout their version for unmerged files
    -f, --force           force checkout (throw away local modifications)
    -m, --merge           perform a 3-way merge with the new branch
    --conflict <style>    conflict style (merge or diff3)
    -p, --patch           select hunks interactively

"""
from docopt import docopt


if __name__ == '__main__':
    print(docopt(__doc__))

########NEW FILE########
__FILENAME__ = git_clone
"""usage: git clone [options] [--] <repo> [<dir>]

    -v, --verbose         be more verbose
    -q, --quiet           be more quiet
    --progress            force progress reporting
    -n, --no-checkout     don't create a checkout
    --bare                create a bare repository
    --mirror              create a mirror repository (implies bare)
    -l, --local           to clone from a local repository
    --no-hardlinks        don't use local hardlinks, always copy
    -s, --shared          setup as shared repository
    --recursive           initialize submodules in the clone
    --recurse-submodules  initialize submodules in the clone
    --template <template-directory>
                          directory from which templates will be used
    --reference <repo>    reference repository
    -o, --origin <branch>
                          use <branch> instead of 'origin' to track upstream
    -b, --branch <branch>
                          checkout <branch> instead of the remote's HEAD
    -u, --upload-pack <path>
                          path to git-upload-pack on the remote
    --depth <depth>       create a shallow clone of that depth

"""
from docopt import docopt


if __name__ == '__main__':
    print(docopt(__doc__))

########NEW FILE########
__FILENAME__ = git_commit
"""usage: git commit [options] [--] [<filepattern>...]

    -h, --help
    -q, --quiet           suppress summary after successful commit
    -v, --verbose         show diff in commit message template

Commit message options
    -F, --file <file>     read message from file
    --author <author>     override author for commit
    --date <date>         override date for commit
    -m, --message <message>
                          commit message
    -c, --reedit-message <commit>
                          reuse and edit message from specified commit
    -C, --reuse-message <commit>
                          reuse message from specified commit
    --fixup <commit>      use autosquash formatted message to fixup specified commit
    --squash <commit>     use autosquash formatted message to squash specified commit
    --reset-author        the commit is authored by me now
                          (used with -C-c/--amend)
    -s, --signoff         add Signed-off-by:
    -t, --template <file>
                          use specified template file
    -e, --edit            force edit of commit
    --cleanup <default>   how to strip spaces and #comments from message
    --status              include status in commit message template

Commit contents options
    -a, --all             commit all changed files
    -i, --include         add specified files to index for commit
    --interactive         interactively add files
    -o, --only            commit only specified files
    -n, --no-verify       bypass pre-commit hook
    --dry-run             show what would be committed
    --short               show status concisely
    --branch              show branch information
    --porcelain           machine-readable output
    -z, --null            terminate entries with NUL
    --amend               amend previous commit
    --no-post-rewrite     bypass post-rewrite hook
    -u, --untracked-files=<mode>
                          show untracked files, optional modes: all, normal, no.
                          [default: all]

"""
from docopt import docopt


if __name__ == '__main__':
    print(docopt(__doc__))

########NEW FILE########
__FILENAME__ = git_push
"""usage: git push [options] [<repository> [<refspec>...]]

    -h, --help
    -v, --verbose         be more verbose
    -q, --quiet           be more quiet
    --repo <repository>   repository
    --all                 push all refs
    --mirror              mirror all refs
    --delete              delete refs
    --tags                push tags (can't be used with --all or --mirror)
    -n, --dry-run         dry run
    --porcelain           machine-readable output
    -f, --force           force updates
    --thin                use thin pack
    --receive-pack <receive-pack>
                          receive pack program
    --exec <receive-pack>
                          receive pack program
    -u, --set-upstream    set upstream for git pull/status
    --progress            force progress reporting

"""
from docopt import docopt


if __name__ == '__main__':
    print(docopt(__doc__))

########NEW FILE########
__FILENAME__ = git_remote
"""
usage: git remote [-v | --verbose]
       git remote add [-t <branch>] [-m <master>] [-f] [--mirror] <name> <url>
       git remote rename <old> <new>
       git remote rm <name>
       git remote set-head <name> (-a | -d | <branch>)
       git remote [-v | --verbose] show [-n] <name>
       git remote prune [-n | --dry-run] <name>
       git remote [-v | --verbose] update [-p | --prune] [(<group> | <remote>)...]
       git remote set-branches <name> [--add] <branch>...
       git remote set-url <name> <newurl> [<oldurl>]
       git remote set-url --add <name> <newurl>
       git remote set-url --delete <name> <url>

    -v, --verbose         be verbose; must be placed before a subcommand

"""
from docopt import docopt


if __name__ == '__main__':
    arguments = docopt(__doc__)
    print(arguments)

########NEW FILE########
__FILENAME__ = interactive_example
#!/usr/bin/env python
"""
This example uses docopt with the built in cmd module to demonstrate an
interactive command application.

Usage:
    my_program tcp <host> <port> [--timeout=<seconds>]
    my_program serial <port> [--baud=<n>] [--timeout=<seconds>]
    my_program (-i | --interactive)
    my_program (-h | --help | --version)

Options:
    -i, --interactive  Interactive Mode
    -h, --help  Show this screen and exit.
    --baud=<n>  Baudrate [default: 9600]
"""

import sys
import cmd
from docopt import docopt, DocoptExit


def docopt_cmd(func):
    """
    This decorator is used to simplify the try/except block and pass the result
    of the docopt parsing to the called action.
    """
    def fn(self, arg):
        try:
            opt = docopt(fn.__doc__, arg)

        except DocoptExit as e:
            # The DocoptExit is thrown when the args do not match.
            # We print a message to the user and the usage block.

            print('Invalid Command!')
            print(e)
            return

        except SystemExit:
            # The SystemExit exception prints the usage for --help
            # We do not need to do the print here.

            return

        return func(self, opt)

    fn.__name__ = func.__name__
    fn.__doc__ = func.__doc__
    fn.__dict__.update(func.__dict__)
    return fn


class MyInteractive (cmd.Cmd):
    intro = 'Welcome to my interactive program!' \
        + ' (type help for a list of commands.)'
    prompt = '(my_program) '
    file = None

    @docopt_cmd
    def do_tcp(self, arg):
        """Usage: tcp <host> <port> [--timeout=<seconds>]"""

        print(arg)

    @docopt_cmd
    def do_serial(self, arg):
        """Usage: serial <port> [--baud=<n>] [--timeout=<seconds>]
Options:
    --baud=<n>  Baudrate [default: 9600]
        """

        print(arg)

    def do_quit(self, arg):
        """Quits out of Interactive Mode."""

        print('Good Bye!')
        exit()

opt = docopt(__doc__, sys.argv[1:])

if opt['--interactive']:
    MyInteractive().cmdloop()

print(opt)

########NEW FILE########
__FILENAME__ = naval_fate
"""Naval Fate.

Usage:
  naval_fate.py ship new <name>...
  naval_fate.py ship <name> move <x> <y> [--speed=<kn>]
  naval_fate.py ship shoot <x> <y>
  naval_fate.py mine (set|remove) <x> <y> [--moored|--drifting]
  naval_fate.py -h | --help
  naval_fate.py --version

Options:
  -h --help     Show this screen.
  --version     Show version.
  --speed=<kn>  Speed in knots [default: 10].
  --moored      Moored (anchored) mine.
  --drifting    Drifting mine.

"""
from docopt import docopt


if __name__ == '__main__':
    arguments = docopt(__doc__, version='Naval Fate 2.0')
    print(arguments)

########NEW FILE########
__FILENAME__ = odd_even_example
"""Usage: odd_even_example.py [-h | --help] (ODD EVEN)...

Example, try:
  odd_even_example.py 1 2 3 4

Options:
  -h, --help

"""
from docopt import docopt


if __name__ == '__main__':
    arguments = docopt(__doc__)
    print(arguments)

########NEW FILE########
__FILENAME__ = options_example
"""Example of program with many options using docopt.

Usage:
  options_example.py [-hvqrf NAME] [--exclude=PATTERNS]
                     [--select=ERRORS | --ignore=ERRORS] [--show-source]
                     [--statistics] [--count] [--benchmark] PATH...
  options_example.py (--doctest | --testsuite=DIR)
  options_example.py --version

Arguments:
  PATH  destination path

Options:
  -h --help            show this help message and exit
  --version            show version and exit
  -v --verbose         print status messages
  -q --quiet           report only file names
  -r --repeat          show all occurrences of the same error
  --exclude=PATTERNS   exclude files or directories which match these comma
                       separated patterns [default: .svn,CVS,.bzr,.hg,.git]
  -f NAME --file=NAME  when parsing directories, only check filenames matching
                       these comma separated patterns [default: *.py]
  --select=ERRORS      select errors and warnings (e.g. E,W6)
  --ignore=ERRORS      skip errors and warnings (e.g. E4,W)
  --show-source        show source code for each error
  --statistics         count errors and warnings
  --count              print total number of errors and warnings to standard
                       error and set exit code to 1 if total is not null
  --benchmark          measure processing speed
  --testsuite=DIR      run regression tests from dir
  --doctest            run doctest on myself

"""
from docopt import docopt


if __name__ == '__main__':
    arguments = docopt(__doc__, version='1.0.0rc2')
    print(arguments)

########NEW FILE########
__FILENAME__ = options_shortcut_example
"""Example of program which uses [options] shortcut in pattern.

Usage:
  options_shortcut_example.py [options] <port>

Options:
  -h --help                show this help message and exit
  --version                show version and exit
  -n, --number N           use N as a number
  -t, --timeout TIMEOUT    set timeout TIMEOUT seconds
  --apply                  apply changes to database
  -q                       operate in quiet mode

"""
from docopt import docopt


if __name__ == '__main__':
    arguments = docopt(__doc__, version='1.0.0rc2')
    print(arguments)

########NEW FILE########
__FILENAME__ = quick_example
"""Usage:
  quick_example.py tcp <host> <port> [--timeout=<seconds>]
  quick_example.py serial <port> [--baud=9600] [--timeout=<seconds>]
  quick_example.py -h | --help | --version

"""
from docopt import docopt


if __name__ == '__main__':
    arguments = docopt(__doc__, version='0.1.1rc')
    print(arguments)

########NEW FILE########
__FILENAME__ = validation_example
"""Usage: prog.py [--count=N] PATH FILE...

Arguments:
  FILE     input file
  PATH     out directory

Options:
  --count=N   number of operations

"""
import os

from docopt import docopt
try:
    from schema import Schema, And, Or, Use, SchemaError
except ImportError:
    exit('This example requires that `schema` data-validation library'
         ' is installed: \n    pip install schema\n'
         'https://github.com/halst/schema')


if __name__ == '__main__':
    args = docopt(__doc__)

    schema = Schema({
        'FILE': [Use(open, error='FILE should be readable')],
        'PATH': And(os.path.exists, error='PATH should exist'),
        '--count': Or(None, And(Use(int), lambda n: 0 < n < 5),
                      error='--count=N should be integer 0 < N < 5')})
    try:
        args = schema.validate(args)
    except SchemaError as e:
        exit(e)

    print(args)

########NEW FILE########
__FILENAME__ = test_docopt
from __future__ import with_statement
from docopt import (docopt, DocoptExit, DocoptLanguageError,
                    Option, Argument, Command, OptionsShortcut,
                    Required, Optional, Either, OneOrMore,
                    parse_argv, parse_pattern, parse_section,
                    parse_defaults, formal_usage, Tokens, transform
                   )
from pytest import raises


def test_pattern_flat():
    assert Required(OneOrMore(Argument('N')),
                    Option('-a'), Argument('M')).flat() == \
                            [Argument('N'), Option('-a'), Argument('M')]
    assert Required(Optional(OptionsShortcut()),
                    Optional(Option('-a', None))).flat(OptionsShortcut) == \
                            [OptionsShortcut()]


def test_option():
    assert Option.parse('-h') == Option('-h', None)
    assert Option.parse('--help') == Option(None, '--help')
    assert Option.parse('-h --help') == Option('-h', '--help')
    assert Option.parse('-h, --help') == Option('-h', '--help')

    assert Option.parse('-h TOPIC') == Option('-h', None, 1)
    assert Option.parse('--help TOPIC') == Option(None, '--help', 1)
    assert Option.parse('-h TOPIC --help TOPIC') == Option('-h', '--help', 1)
    assert Option.parse('-h TOPIC, --help TOPIC') == Option('-h', '--help', 1)
    assert Option.parse('-h TOPIC, --help=TOPIC') == Option('-h', '--help', 1)

    assert Option.parse('-h  Description...') == Option('-h', None)
    assert Option.parse('-h --help  Description...') == Option('-h', '--help')
    assert Option.parse('-h TOPIC  Description...') == Option('-h', None, 1)

    assert Option.parse('    -h') == Option('-h', None)

    assert Option.parse('-h TOPIC  Descripton... [default: 2]') == \
               Option('-h', None, 1, '2')
    assert Option.parse('-h TOPIC  Descripton... [default: topic-1]') == \
               Option('-h', None, 1, 'topic-1')
    assert Option.parse('--help=TOPIC  ... [default: 3.14]') == \
               Option(None, '--help', 1, '3.14')
    assert Option.parse('-h, --help=DIR  ... [default: ./]') == \
               Option('-h', '--help', 1, "./")
    assert Option.parse('-h TOPIC  Descripton... [dEfAuLt: 2]') == \
               Option('-h', None, 1, '2')


def test_option_name():
    assert Option('-h', None).name == '-h'
    assert Option('-h', '--help').name == '--help'
    assert Option(None, '--help').name == '--help'


def test_commands():
    assert docopt('Usage: prog add', 'add') == {'add': True}
    assert docopt('Usage: prog [add]', '') == {'add': False}
    assert docopt('Usage: prog [add]', 'add') == {'add': True}
    assert docopt('Usage: prog (add|rm)', 'add') == {'add': True, 'rm': False}
    assert docopt('Usage: prog (add|rm)', 'rm') == {'add': False, 'rm': True}
    assert docopt('Usage: prog a b', 'a b') == {'a': True, 'b': True}
    with raises(DocoptExit):
        docopt('Usage: prog a b', 'b a')


def test_formal_usage():
    doc = """
    Usage: prog [-hv] ARG
           prog N M

    prog is a program."""
    usage, = parse_section('usage:', doc)
    assert usage == "Usage: prog [-hv] ARG\n           prog N M"
    assert formal_usage(usage) == "( [-hv] ARG ) | ( N M )"


def test_parse_argv():
    o = [Option('-h'), Option('-v', '--verbose'), Option('-f', '--file', 1)]
    TS = lambda s: Tokens(s, error=DocoptExit)
    assert parse_argv(TS(''), options=o) == []
    assert parse_argv(TS('-h'), options=o) == [Option('-h', None, 0, True)]
    assert parse_argv(TS('-h --verbose'), options=o) == \
            [Option('-h', None, 0, True), Option('-v', '--verbose', 0, True)]
    assert parse_argv(TS('-h --file f.txt'), options=o) == \
            [Option('-h', None, 0, True), Option('-f', '--file', 1, 'f.txt')]
    assert parse_argv(TS('-h --file f.txt arg'), options=o) == \
            [Option('-h', None, 0, True),
             Option('-f', '--file', 1, 'f.txt'),
             Argument(None, 'arg')]
    assert parse_argv(TS('-h --file f.txt arg arg2'), options=o) == \
            [Option('-h', None, 0, True),
             Option('-f', '--file', 1, 'f.txt'),
             Argument(None, 'arg'),
             Argument(None, 'arg2')]
    assert parse_argv(TS('-h arg -- -v'), options=o) == \
            [Option('-h', None, 0, True),
             Argument(None, 'arg'),
             Argument(None, '--'),
             Argument(None, '-v')]


def test_parse_pattern():
    o = [Option('-h'), Option('-v', '--verbose'), Option('-f', '--file', 1)]
    assert parse_pattern('[ -h ]', options=o) == \
               Required(Optional(Option('-h')))
    assert parse_pattern('[ ARG ... ]', options=o) == \
               Required(Optional(OneOrMore(Argument('ARG'))))
    assert parse_pattern('[ -h | -v ]', options=o) == \
               Required(Optional(Either(Option('-h'),
                                Option('-v', '--verbose'))))
    assert parse_pattern('( -h | -v [ --file <f> ] )', options=o) == \
               Required(Required(
                   Either(Option('-h'),
                          Required(Option('-v', '--verbose'),
                               Optional(Option('-f', '--file', 1, None))))))
    assert parse_pattern('(-h|-v[--file=<f>]N...)', options=o) == \
               Required(Required(Either(Option('-h'),
                              Required(Option('-v', '--verbose'),
                                  Optional(Option('-f', '--file', 1, None)),
                                     OneOrMore(Argument('N'))))))
    assert parse_pattern('(N [M | (K | L)] | O P)', options=[]) == \
               Required(Required(Either(
                   Required(Argument('N'),
                            Optional(Either(Argument('M'),
                                            Required(Either(Argument('K'),
                                                            Argument('L')))))),
                   Required(Argument('O'), Argument('P')))))
    assert parse_pattern('[ -h ] [N]', options=o) == \
               Required(Optional(Option('-h')),
                        Optional(Argument('N')))
    assert parse_pattern('[options]', options=o) == \
            Required(Optional(OptionsShortcut()))
    assert parse_pattern('[options] A', options=o) == \
            Required(Optional(OptionsShortcut()),
                     Argument('A'))
    assert parse_pattern('-v [options]', options=o) == \
            Required(Option('-v', '--verbose'),
                     Optional(OptionsShortcut()))
    assert parse_pattern('ADD', options=o) == Required(Argument('ADD'))
    assert parse_pattern('<add>', options=o) == Required(Argument('<add>'))
    assert parse_pattern('add', options=o) == Required(Command('add'))


def test_option_match():
    assert Option('-a').match([Option('-a', value=True)]) == \
            (True, [], [Option('-a', value=True)])
    assert Option('-a').match([Option('-x')]) == (False, [Option('-x')], [])
    assert Option('-a').match([Argument('N')]) == (False, [Argument('N')], [])
    assert Option('-a').match([Option('-x'), Option('-a'), Argument('N')]) == \
            (True, [Option('-x'), Argument('N')], [Option('-a')])
    assert Option('-a').match([Option('-a', value=True), Option('-a')]) == \
            (True, [Option('-a')], [Option('-a', value=True)])


def test_argument_match():
    assert Argument('N').match([Argument(None, 9)]) == \
            (True, [], [Argument('N', 9)])
    assert Argument('N').match([Option('-x')]) == (False, [Option('-x')], [])
    assert Argument('N').match([Option('-x'),
                                Option('-a'),
                                Argument(None, 5)]) == \
            (True, [Option('-x'), Option('-a')], [Argument('N', 5)])
    assert Argument('N').match([Argument(None, 9), Argument(None, 0)]) == \
            (True, [Argument(None, 0)], [Argument('N', 9)])


def test_command_match():
    assert Command('c').match([Argument(None, 'c')]) == \
            (True, [], [Command('c', True)])
    assert Command('c').match([Option('-x')]) == (False, [Option('-x')], [])
    assert Command('c').match([Option('-x'),
                               Option('-a'),
                               Argument(None, 'c')]) == \
            (True, [Option('-x'), Option('-a')], [Command('c', True)])
    assert Either(Command('add', False), Command('rm', False)).match(
            [Argument(None, 'rm')]) == (True, [], [Command('rm', True)])


def test_optional_match():
    assert Optional(Option('-a')).match([Option('-a')]) == \
            (True, [], [Option('-a')])
    assert Optional(Option('-a')).match([]) == (True, [], [])
    assert Optional(Option('-a')).match([Option('-x')]) == \
            (True, [Option('-x')], [])
    assert Optional(Option('-a'), Option('-b')).match([Option('-a')]) == \
            (True, [], [Option('-a')])
    assert Optional(Option('-a'), Option('-b')).match([Option('-b')]) == \
            (True, [], [Option('-b')])
    assert Optional(Option('-a'), Option('-b')).match([Option('-x')]) == \
            (True, [Option('-x')], [])
    assert Optional(Argument('N')).match([Argument(None, 9)]) == \
            (True, [], [Argument('N', 9)])
    assert Optional(Option('-a'), Option('-b')).match(
                [Option('-b'), Option('-x'), Option('-a')]) == \
            (True, [Option('-x')], [Option('-a'), Option('-b')])


def test_required_match():
    assert Required(Option('-a')).match([Option('-a')]) == \
            (True, [], [Option('-a')])
    assert Required(Option('-a')).match([]) == (False, [], [])
    assert Required(Option('-a')).match([Option('-x')]) == \
            (False, [Option('-x')], [])
    assert Required(Option('-a'), Option('-b')).match([Option('-a')]) == \
            (False, [Option('-a')], [])


def test_either_match():
    assert Either(Option('-a'), Option('-b')).match(
            [Option('-a')]) == (True, [], [Option('-a')])
    assert Either(Option('-a'), Option('-b')).match(
            [Option('-a'), Option('-b')]) == \
                    (True, [Option('-b')], [Option('-a')])
    assert Either(Option('-a'), Option('-b')).match(
            [Option('-x')]) == (False, [Option('-x')], [])
    assert Either(Option('-a'), Option('-b'), Option('-c')).match(
            [Option('-x'), Option('-b')]) == \
                    (True, [Option('-x')], [Option('-b')])
    assert Either(Argument('M'),
                  Required(Argument('N'), Argument('M'))).match(
                                   [Argument(None, 1), Argument(None, 2)]) == \
            (True, [], [Argument('N', 1), Argument('M', 2)])


def test_one_or_more_match():
    assert OneOrMore(Argument('N')).match([Argument(None, 9)]) == \
            (True, [], [Argument('N', 9)])
    assert OneOrMore(Argument('N')).match([]) == (False, [], [])
    assert OneOrMore(Argument('N')).match([Option('-x')]) == \
            (False, [Option('-x')], [])
    assert OneOrMore(Argument('N')).match(
            [Argument(None, 9), Argument(None, 8)]) == (
                    True, [], [Argument('N', 9), Argument('N', 8)])
    assert OneOrMore(Argument('N')).match(
            [Argument(None, 9), Option('-x'), Argument(None, 8)]) == (
                    True, [Option('-x')], [Argument('N', 9), Argument('N', 8)])
    assert OneOrMore(Option('-a')).match(
            [Option('-a'), Argument(None, 8), Option('-a')]) == \
                    (True, [Argument(None, 8)], [Option('-a'), Option('-a')])
    assert OneOrMore(Option('-a')).match([Argument(None, 8),
                                          Option('-x')]) == \
                    (False, [Argument(None, 8), Option('-x')], [])
    assert OneOrMore(Required(Option('-a'), Argument('N'))).match(
            [Option('-a'), Argument(None, 1), Option('-x'),
             Option('-a'), Argument(None, 2)]) == \
             (True, [Option('-x')],
              [Option('-a'), Argument('N', 1), Option('-a'), Argument('N', 2)])
    assert OneOrMore(Optional(Argument('N'))).match([Argument(None, 9)]) == \
                    (True, [], [Argument('N', 9)])


def test_list_argument_match():
    assert Required(Argument('N'), Argument('N')).fix().match(
            [Argument(None, '1'), Argument(None, '2')]) == \
                    (True, [], [Argument('N', ['1', '2'])])
    assert OneOrMore(Argument('N')).fix().match(
          [Argument(None, '1'), Argument(None, '2'), Argument(None, '3')]) == \
                    (True, [], [Argument('N', ['1', '2', '3'])])
    assert Required(Argument('N'), OneOrMore(Argument('N'))).fix().match(
          [Argument(None, '1'), Argument(None, '2'), Argument(None, '3')]) == \
                    (True, [], [Argument('N', ['1', '2', '3'])])
    assert Required(Argument('N'), Required(Argument('N'))).fix().match(
            [Argument(None, '1'), Argument(None, '2')]) == \
                    (True, [], [Argument('N', ['1', '2'])])


def test_basic_pattern_matching():
    # ( -a N [ -x Z ] )
    pattern = Required(Option('-a'), Argument('N'),
                       Optional(Option('-x'), Argument('Z')))
    # -a N
    assert pattern.match([Option('-a'), Argument(None, 9)]) == \
            (True, [], [Option('-a'), Argument('N', 9)])
    # -a -x N Z
    assert pattern.match([Option('-a'), Option('-x'),
                          Argument(None, 9), Argument(None, 5)]) == \
            (True, [], [Option('-a'), Argument('N', 9),
                        Option('-x'), Argument('Z', 5)])
    # -x N Z  # BZZ!
    assert pattern.match([Option('-x'),
                          Argument(None, 9),
                          Argument(None, 5)]) == \
            (False, [Option('-x'), Argument(None, 9), Argument(None, 5)], [])


def test_pattern_either():
    assert transform(Option('-a')) == Either(Required(Option('-a')))
    assert transform(Argument('A')) == Either(Required(Argument('A')))
    assert transform(Required(Either(Option('-a'), Option('-b')),
                    Option('-c'))) == \
            Either(Required(Option('-a'), Option('-c')),
                   Required(Option('-b'), Option('-c')))
    assert transform(Optional(Option('-a'), Either(Option('-b'),
                                                   Option('-c')))) == \
            Either(Required(Option('-b'), Option('-a')),
                   Required(Option('-c'), Option('-a')))
    assert transform(Either(Option('-x'),
                            Either(Option('-y'), Option('-z')))) == \
            Either(Required(Option('-x')),
                   Required(Option('-y')),
                   Required(Option('-z')))
    assert transform(OneOrMore(Argument('N'), Argument('M'))) == \
            Either(Required(Argument('N'), Argument('M'),
                            Argument('N'), Argument('M')))


def test_pattern_fix_repeating_arguments():
    assert Option('-a').fix_repeating_arguments() == Option('-a')
    assert Argument('N', None).fix_repeating_arguments() == Argument('N', None)
    assert Required(Argument('N'),
                    Argument('N')).fix_repeating_arguments() == \
            Required(Argument('N', []), Argument('N', []))
    assert Either(Argument('N'),
                        OneOrMore(Argument('N'))).fix() == \
            Either(Argument('N', []), OneOrMore(Argument('N', [])))


def test_set():
    assert Argument('N') == Argument('N')
    assert set([Argument('N'), Argument('N')]) == set([Argument('N')])


def test_pattern_fix_identities_1():
    pattern = Required(Argument('N'), Argument('N'))
    assert pattern.children[0] == pattern.children[1]
    assert pattern.children[0] is not pattern.children[1]
    pattern.fix_identities()
    assert pattern.children[0] is pattern.children[1]


def test_pattern_fix_identities_2():
    pattern = Required(Optional(Argument('X'), Argument('N')), Argument('N'))
    assert pattern.children[0].children[1] == pattern.children[1]
    assert pattern.children[0].children[1] is not pattern.children[1]
    pattern.fix_identities()
    assert pattern.children[0].children[1] is pattern.children[1]


def test_long_options_error_handling():
#    with raises(DocoptLanguageError):
#        docopt('Usage: prog --non-existent', '--non-existent')
#    with raises(DocoptLanguageError):
#        docopt('Usage: prog --non-existent')
    with raises(DocoptExit):
        docopt('Usage: prog', '--non-existent')
    with raises(DocoptExit):
        docopt('Usage: prog [--version --verbose]\n'
               'Options: --version\n --verbose', '--ver')
    with raises(DocoptLanguageError):
        docopt('Usage: prog --long\nOptions: --long ARG')
    with raises(DocoptExit):
        docopt('Usage: prog --long ARG\nOptions: --long ARG', '--long')
    with raises(DocoptLanguageError):
        docopt('Usage: prog --long=ARG\nOptions: --long')
    with raises(DocoptExit):
        docopt('Usage: prog --long\nOptions: --long', '--long=ARG')


def test_short_options_error_handling():
    with raises(DocoptLanguageError):
        docopt('Usage: prog -x\nOptions: -x  this\n -x  that')

#    with raises(DocoptLanguageError):
#        docopt('Usage: prog -x')
    with raises(DocoptExit):
        docopt('Usage: prog', '-x')

    with raises(DocoptLanguageError):
        docopt('Usage: prog -o\nOptions: -o ARG')
    with raises(DocoptExit):
        docopt('Usage: prog -o ARG\nOptions: -o ARG', '-o')


def test_matching_paren():
    with raises(DocoptLanguageError):
        docopt('Usage: prog [a [b]')
    with raises(DocoptLanguageError):
        docopt('Usage: prog [a [b] ] c )')


def test_allow_double_dash():
    assert docopt('usage: prog [-o] [--] <arg>\nkptions: -o',
                  '-- -o') == {'-o': False, '<arg>': '-o', '--': True}
    assert docopt('usage: prog [-o] [--] <arg>\nkptions: -o',
                  '-o 1') == {'-o': True, '<arg>': '1', '--': False}
    with raises(DocoptExit):  # "--" is not allowed; FIXME?
        docopt('usage: prog [-o] <arg>\noptions:-o', '-- -o')


def test_docopt():
    doc = '''Usage: prog [-v] A

             Options: -v  Be verbose.'''
    assert docopt(doc, 'arg') == {'-v': False, 'A': 'arg'}
    assert docopt(doc, '-v arg') == {'-v': True, 'A': 'arg'}

    doc = """Usage: prog [-vqr] [FILE]
              prog INPUT OUTPUT
              prog --help

    Options:
      -v  print status messages
      -q  report only file names
      -r  show all occurrences of the same error
      --help

    """
    a = docopt(doc, '-v file.py')
    assert a == {'-v': True, '-q': False, '-r': False, '--help': False,
                 'FILE': 'file.py', 'INPUT': None, 'OUTPUT': None}

    a = docopt(doc, '-v')
    assert a == {'-v': True, '-q': False, '-r': False, '--help': False,
                 'FILE': None, 'INPUT': None, 'OUTPUT': None}

    with raises(DocoptExit):  # does not match
        docopt(doc, '-v input.py output.py')

    with raises(DocoptExit):
        docopt(doc, '--fake')

    with raises(SystemExit):
        docopt(doc, '--hel')

    #with raises(SystemExit):
    #    docopt(doc, 'help')  XXX Maybe help command?


def test_language_errors():
    with raises(DocoptLanguageError):
        docopt('no usage with colon here')
    with raises(DocoptLanguageError):
        docopt('usage: here \n\n and again usage: here')


def test_issue_40():
    with raises(SystemExit):  # i.e. shows help
        docopt('usage: prog --help-commands | --help', '--help')
    assert docopt('usage: prog --aabb | --aa', '--aa') == {'--aabb': False,
                                                           '--aa': True}


def test_issue34_unicode_strings():
    try:
        assert docopt(eval("u'usage: prog [-o <a>]'"), '') == \
                {'-o': False, '<a>': None}
    except SyntaxError:
        pass  # Python 3


def test_count_multiple_flags():
    assert docopt('usage: prog [-v]', '-v') == {'-v': True}
    assert docopt('usage: prog [-vv]', '') == {'-v': 0}
    assert docopt('usage: prog [-vv]', '-v') == {'-v': 1}
    assert docopt('usage: prog [-vv]', '-vv') == {'-v': 2}
    with raises(DocoptExit):
        docopt('usage: prog [-vv]', '-vvv')
    assert docopt('usage: prog [-v | -vv | -vvv]', '-vvv') == {'-v': 3}
    assert docopt('usage: prog -v...', '-vvvvvv') == {'-v': 6}
    assert docopt('usage: prog [--ver --ver]', '--ver --ver') == {'--ver': 2}


def test_any_options_parameter():
    with raises(DocoptExit):
        docopt('usage: prog [options]', '-foo --bar --spam=eggs')
#    assert docopt('usage: prog [options]', '-foo --bar --spam=eggs',
#                  any_options=True) == {'-f': True, '-o': 2,
#                                         '--bar': True, '--spam': 'eggs'}
    with raises(DocoptExit):
        docopt('usage: prog [options]', '--foo --bar --bar')
#    assert docopt('usage: prog [options]', '--foo --bar --bar',
#                  any_options=True) == {'--foo': True, '--bar': 2}
    with raises(DocoptExit):
        docopt('usage: prog [options]', '--bar --bar --bar -ffff')
#    assert docopt('usage: prog [options]', '--bar --bar --bar -ffff',
#                  any_options=True) == {'--bar': 3, '-f': 4}
    with raises(DocoptExit):
        docopt('usage: prog [options]', '--long=arg --long=another')
#    assert docopt('usage: prog [options]', '--long=arg --long=another',
#                  any_options=True) == {'--long': ['arg', 'another']}


#def test_options_shortcut_multiple_commands():
#    # any_options is disabled
#    assert docopt('usage: prog c1 [options] prog c2 [options]',
#        'c2 -o', any_options=True) == {'-o': True, 'c1': False, 'c2': True}
#    assert docopt('usage: prog c1 [options] prog c2 [options]',
#        'c1 -o', any_options=True) == {'-o': True, 'c1': True, 'c2': False}


def test_default_value_for_positional_arguments():
    doc = """Usage: prog [--data=<data>...]\n
             Options:\n\t-d --data=<arg>    Input data [default: x]
          """
    a = docopt(doc, '')
    assert a == {'--data': ['x']}
    doc = """Usage: prog [--data=<data>...]\n
             Options:\n\t-d --data=<arg>    Input data [default: x y]
          """
    a = docopt(doc, '')
    assert a == {'--data': ['x', 'y']}
    doc = """Usage: prog [--data=<data>...]\n
             Options:\n\t-d --data=<arg>    Input data [default: x y]
          """
    a = docopt(doc, '--data=this')
    assert a == {'--data': ['this']}


#def test_parse_defaults():
#    assert parse_defaults("""usage: prog
#                          options:
#                          -o, --option <o>
#                          --another <a>  description
#                                         [default: x]
#                          <a>
#                          <another>  description [default: y]""") == \
#           ([Option('-o', '--option', 1, None),
#             Option(None, '--another', 1, 'x')],
#            [Argument('<a>', None),
#             Argument('<another>', 'y')])
#
#    doc = '''
#    -h, --help  Print help message.
#    -o FILE     Output file.
#    --verbose   Verbose mode.'''
#    assert parse_defaults(doc)[0] == [Option('-h', '--help'),
#                                      Option('-o', None, 1),
#                                      Option(None, '--verbose')]


def test_issue_59():
    assert docopt('usage: prog --long=<a>', '--long=') == {'--long': ''}
    assert docopt('usage: prog -l <a>\n'
                  'options: -l <a>', ['-l', '']) == {'-l': ''}


def test_options_first():
    assert docopt('usage: prog [--opt] [<args>...]',
                  '--opt this that') == {'--opt': True,
                                         '<args>': ['this', 'that']}
    assert docopt('usage: prog [--opt] [<args>...]',
                  'this that --opt') == {'--opt': True,
                                         '<args>': ['this', 'that']}
    assert docopt('usage: prog [--opt] [<args>...]',
                  'this that --opt',
                  options_first=True) == {'--opt': False,
                                          '<args>': ['this', 'that', '--opt']}


def test_issue_68_options_shortcut_does_not_include_options_in_usage_pattern():
    args = docopt('usage: prog [-ab] [options]\n'
                  'options: -x\n -y', '-ax')
    # Need to use `is` (not `==`) since we want to make sure
    # that they are not 1/0, but strictly True/False:
    assert args['-a'] is True
    assert args['-b'] is False
    assert args['-x'] is True
    assert args['-y'] is False


def test_issue_65_evaluate_argv_when_called_not_when_imported():
    import sys
    sys.argv = 'prog -a'.split()
    assert docopt('usage: prog [-ab]') == {'-a': True, '-b': False}
    sys.argv = 'prog -b'.split()
    assert docopt('usage: prog [-ab]') == {'-a': False, '-b': True}


def test_issue_71_double_dash_is_not_a_valid_option_argument():
    with raises(DocoptExit):
        docopt('usage: prog [--log=LEVEL] [--] <args>...', '--log -- 1 2')
    with raises(DocoptExit):
        docopt('''usage: prog [-l LEVEL] [--] <args>...
                  options: -l LEVEL''', '-l -- 1 2')


usage = '''usage: this

usage:hai
usage: this that

usage: foo
       bar

PROGRAM USAGE:
 foo
 bar
usage:
\ttoo
\ttar
Usage: eggs spam
BAZZ
usage: pit stop'''


def test_parse_section():
    assert parse_section('usage:', 'foo bar fizz buzz') == []
    assert parse_section('usage:', 'usage: prog') == ['usage: prog']
    assert parse_section('usage:',
                         'usage: -x\n -y') == ['usage: -x\n -y']
    assert parse_section('usage:', usage) == [
            'usage: this',
            'usage:hai',
            'usage: this that',
            'usage: foo\n       bar',
            'PROGRAM USAGE:\n foo\n bar',
            'usage:\n\ttoo\n\ttar',
            'Usage: eggs spam',
            'usage: pit stop',
    ]


def test_issue_126_defaults_not_parsed_correctly_when_tabs():
    section = 'Options:\n\t--foo=<arg>  [default: bar]'
    assert parse_defaults(section) == [Option(None, '--foo', 1, 'bar')]

########NEW FILE########
