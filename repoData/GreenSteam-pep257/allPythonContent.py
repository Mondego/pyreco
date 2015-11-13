__FILENAME__ = pep257
#! /usr/bin/env python
"""Static analysis tool for checking docstring conventions and style.

Implemented checks cover PEP257:
http://www.python.org/dev/peps/pep-0257/

Other checks can be added, e.g. NumPy docstring conventions:
https://github.com/numpy/numpy/blob/master/doc/HOWTO_DOCUMENT.rst.txt

The repository is located at:
http://github.com/GreenSteam/pep257

"""
from __future__ import with_statement

import os
import sys
import tokenize as tk
from itertools import takewhile, dropwhile, chain
from optparse import OptionParser
from re import compile as re


try:
    from StringIO import StringIO
except ImportError:  # Python 3.0 and later
    from io import StringIO


try:
    next
except NameError:  # Python 2.5 and earlier
    nothing = object()

    def next(obj, default=nothing):
        if default == nothing:
            return obj.next()
        else:
            try:
                return obj.next()
            except StopIteration:
                return default


__version__ = '0.3.3-alpha'
__all__ = ('check', 'collect')


humanize = lambda string: re(r'(.)([A-Z]+)').sub(r'\1 \2', string).lower()
is_magic = lambda name: name.startswith('__') and name.endswith('__')
is_ascii = lambda string: all(ord(char) < 128 for char in string)
is_blank = lambda string: not string.strip()
leading_space = lambda string: re('\s*').match(string).group()


class Value(object):

    __init__ = lambda self, *args: vars(self).update(zip(self._fields, args))
    __hash__ = lambda self: hash(repr(self))
    __eq__ = lambda self, other: other and vars(self) == vars(other)

    def __repr__(self):
        args = [vars(self)[field] for field in self._fields]
        return '%s(%s)' % (self.__class__.__name__, ', '.join(map(repr, args)))


class Definition(Value):

    _fields = 'name _source start end docstring children parent'.split()

    _human = property(lambda self: humanize(type(self).__name__))
    kind = property(lambda self: self._human.split()[-1])
    module = property(lambda self: self.parent.module)
    all = property(lambda self: self.module.all)
    _slice = property(lambda self: slice(self.start - 1, self.end))
    source = property(lambda self: ''.join(self._source[self._slice]))
    __iter__ = lambda self: chain([self], *self.children)

    @property
    def _publicity(self):
        return {True: 'public', False: 'private'}[self.is_public]

    def __str__(self):
        return 'in %s %s `%s`' % (self._publicity, self._human, self.name)


class Module(Definition):

    _fields = 'name _source start end docstring children parent _all'.split()
    is_public = True
    _nest = staticmethod(lambda s: {'def': Function, 'class': Class}[s])
    module = property(lambda self: self)
    all = property(lambda self: self._all)
    __str__ = lambda self: 'at module level'


class Function(Definition):

    _nest = staticmethod(lambda s: {'def': NestedFunction,
                                    'class': NestedClass}[s])

    @property
    def is_public(self):
        if self.all is not None:
            return self.name in self.all
        else:  # TODO: are there any magic functions? not methods
            return not self.name.startswith('_') or is_magic(self.name)


class NestedFunction(Function):

    is_public = False


class Method(Function):

    @property
    def is_public(self):
        name_is_public = not self.name.startswith('_') or is_magic(self.name)
        return self.parent.is_public and name_is_public


class Class(Definition):

    _nest = staticmethod(lambda s: {'def': Method, 'class': NestedClass}[s])
    is_public = Function.is_public


class NestedClass(Class):

    is_public = False


class Token(Value):

    _fields = 'kind value start end source'.split()


class TokenStream(object):

    def __init__(self, filelike):
        self._generator = tk.generate_tokens(filelike.readline)
        self.current = Token(*next(self._generator, None))
        self.line = self.current.start[0]

    def move(self):
        previous = self.current
        current = next(self._generator, None)
        self.current = None if current is None else Token(*current)
        self.line = self.current.start[0] if self.current else self.line
        return previous

    def __iter__(self):
        while True:
            if self.current is not None:
                yield self.current
            else:
                return
            self.move()


class AllError(Exception):

    def __init__(self, message):
        Exception.__init__(
            self, message +
            'That means pep257 cannot decide which definitions are public. '
            'Variable __all__ should be present at most once in each file, '
            "in form `__all__ = ('a_public_function', 'APublicClass', ...)`. "
            'More info on __all__: http://stackoverflow.com/q/44834/. ')


class Parser(object):

    def __call__(self, filelike, filename):
        self.source = filelike.readlines()
        src = ''.join(self.source)
        self.stream = TokenStream(StringIO(src))
        self.filename = filename
        self.all = None
        return self.parse_module()

    current = property(lambda self: self.stream.current)
    line = property(lambda self: self.stream.line)

    def consume(self, kind):
        assert self.stream.move().kind == kind

    def leapfrog(self, kind):
        for token in self.stream:
            if token.kind == kind:
                self.consume(kind)
                return

    def parse_docstring(self):
        for token in self.stream:
            if token.kind in [tk.COMMENT, tk.NEWLINE, tk.NL]:
                continue
            elif token.kind == tk.STRING:
                return token.value
            else:
                return None

    def parse_definitions(self, class_, all=False):
        for token in self.stream:
            if all and token.value == '__all__':
                self.parse_all()
            if token.value in ['def', 'class']:
                yield self.parse_definition(class_._nest(token.value))
            if token.kind == tk.INDENT:
                self.consume(tk.INDENT)
                for definition in self.parse_definitions(class_):
                    yield definition
            if token.kind == tk.DEDENT:
                return

    def parse_all(self):
        assert self.current.value == '__all__'
        self.consume(tk.NAME)
        if self.current.value != '=':
            raise AllError('Could not evaluate contents of __all__. ')
        self.consume(tk.OP)
        if self.current.value not in '([':
            raise AllError('Could not evaluate contents of __all__. ')
        if self.current.value == '[':
            msg = ("%s WARNING: __all__ is defined as a list, this means "
                   "pep257 cannot reliably detect contents of the __all__ "
                   "variable, because it can be mutated. Change __all__ to be "
                   "an (immutable) tuple, to remove this warning. Note, "
                   "pep257 uses __all__ to detect which definitions are "
                   "public, to warn if public definitions are missing "
                   "docstrings. If __all__ is a (mutable) list, pep257 cannot "
                   "reliably assume its contents. pep257 will proceed "
                   "assuming __all__ is not mutated.\n" % self.filename)
            sys.stderr.write(msg)
        self.consume(tk.OP)
        s = '('
        while self.current.kind in (tk.NL, tk.COMMENT):
            self.stream.move()
        if self.current.kind != tk.STRING:
            raise AllError('Could not evaluate contents of __all__. ')
        while self.current.value not in ')]':
            s += self.current.value
            self.stream.move()
        s += ')'
        try:
            self.all = eval(s, {})
        except BaseException:
            raise AllError('Could not evaluate contents of __all__: %s. ' % s)

    def parse_module(self):
        start = self.line
        docstring = self.parse_docstring()
        children = list(self.parse_definitions(Module, all=True))
        assert self.current is None
        end = self.line
        module = Module(self.filename, self.source, start, end,
                        docstring, children, None, self.all)
        for child in module.children:
            child.parent = module
        return module

    def parse_definition(self, class_):
        start = self.line
        self.consume(tk.NAME)
        name = self.current.value
        self.leapfrog(tk.INDENT)
        assert self.current.kind != tk.INDENT
        docstring = self.parse_docstring()
        children = list(self.parse_definitions(class_))
        assert self.current.kind == tk.DEDENT
        end = self.line - 1
        definition = class_(name, self.source, start, end,
                            docstring, children, None)
        for child in definition.children:
            child.parent = definition
        return definition


class Error(object):

    """Error in docstring style."""

    # Options that define how errors are printed:
    explain = False
    source = False

    def __init__(self, message=None, final=False):
        self.message, self.is_final = message, final
        self.definition, self.explanation = [None, None]

    code = property(lambda self: self.message.partition(':')[0])
    filename = property(lambda self: self.definition.module.name)
    line = property(lambda self: self.definition.start)

    @property
    def lines(self):
        source = ''
        lines = self.definition._source[self.definition._slice]
        offset = self.definition.start
        lines_stripped = list(reversed(list(dropwhile(is_blank,
                                                      reversed(lines)))))
        numbers_width = 0
        for n, line in enumerate(lines_stripped):
            numbers_width = max(numbers_width, n + offset)
        numbers_width = len(str(numbers_width))
        numbers_width = 6
        for n, line in enumerate(lines_stripped):
            source += '%*d: %s' % (numbers_width, n + offset, line)
            if n > 5:
                source += '        ...\n'
                break
        return source

    def __str__(self):
        self.explanation = '\n'.join(l for l in self.explanation.split('\n')
                                     if not is_blank(l))
        template = '%(filename)s:%(line)s %(definition)s:\n        %(message)s'
        if self.source and self.explain:
            template += '\n\n%(explanation)s\n\n%(lines)s\n'
        elif self.source and not self.explain:
            template += '\n\n%(lines)s\n'
        elif self.explain and not self.source:
            template += '\n\n%(explanation)s\n\n'
        return template % dict((name, getattr(self, name)) for name in
                               ['filename', 'line', 'definition', 'message',
                                'explanation', 'lines'])

    __repr__ = __str__

    def __lt__(self, other):
        return (self.filename, self.line) < (other.filename, other.line)


def parse_options():
    parser = OptionParser(version=__version__,
                          usage='Usage: pep257 [options] [<file|dir>...]')
    option = parser.add_option
    option('-e', '--explain', action='store_true',
           help='show explanation of each error')
    option('-s', '--source', action='store_true',
           help='show source for each error')
    option('--ignore', metavar='<codes>', default='',
           help='ignore a list comma-separated error codes, '
                'for example: --ignore=D101,D202')
    option('--match', metavar='<pattern>', default='(?!test_).*\.py',
           help="check only files that exactly match <pattern> regular "
                "expression; default is --match='(?!test_).*\.py' which "
                "matches files that don't start with 'test_' but end with "
                "'.py'")
    option('--match-dir', metavar='<pattern>', default='[^\.].*',
           help="search only dirs that exactly match <pattern> regular "
                "expression; default is --match-dir='[^\.].*', which matches "
                "all dirs that don't start with a dot")
    return parser.parse_args()


def collect(names, match=lambda name: True, match_dir=lambda name: True):
    """Walk dir trees under `names` and generate filnames that `match`.

    Example
    -------
    >>> sorted(collect(['non-dir.txt', './'],
    ...                match=lambda name: name.endswith('.py')))
    ['non-dir.txt', './pep257.py', './setup.py', './test_pep257.py']

    """
    for name in names:  # map(expanduser, names):
        if os.path.isdir(name):
            for root, dirs, filenames in os.walk(name):
                for dir in dirs:
                    if not match_dir(dir):
                        dirs.remove(dir)  # do not visit those dirs
                for filename in filenames:
                    if match(filename):
                        yield os.path.join(root, filename)
        else:
            yield name


def check(filenames, ignore=()):
    """Generate PEP 257 errors that exist in `filenames` iterable.

    Skips errors with error-codes defined in `ignore` iterable.

    Example
    -------
    >>> check(['pep257.py'], ignore=['D100'])
    <generator object check at 0x...>

    """
    for filename in filenames:
        try:
            with open(filename) as file:
                source = file.read()
            for error in PEP257Checker().check_source(source, filename):
                code = getattr(error, 'code', None)
                if code is not None and code not in ignore:
                    yield error
        except (EnvironmentError, AllError):
            yield sys.exc_info()[1]
        except tk.TokenError:
            yield SyntaxError('invalid syntax in file %s' % filename)


def main(options, arguments):
    Error.explain = options.explain
    Error.source = options.source
    collected = collect(arguments or ['.'],
                        match=re(options.match + '$').match,
                        match_dir=re(options.match_dir + '$').match)
    code = 0
    for error in check(collected, ignore=options.ignore.split(',')):
        sys.stderr.write('%s\n' % error)
        code = 1
    return code


parse = Parser()


def check_for(kind, terminal=False):
    def decorator(f):
        f._check_for = kind
        f._terminal = terminal
        return f
    return decorator


class PEP257Checker(object):

    """Checker for PEP 257.

    D10x: Missing docstrings
    D20x: Whitespace issues
    D30x: Docstring formatting
    D40x: Docstring content issues

    """

    def check_source(self, source, filename):
        module = parse(StringIO(source), filename)
        for definition in module:
            for check in self.checks:
                terminate = False
                if isinstance(definition, check._check_for):
                    error = check(None, definition, definition.docstring)
                    errors = error if hasattr(error, '__iter__') else [error]
                    for error in errors:
                        if error is not None:
                            partition = check.__doc__.partition('.\n')
                            message, _, explanation = partition
                            if error.message is None:
                                error.message = message
                            error.explanation = explanation
                            error.definition = definition
                            yield error
                            if check._terminal:
                                terminate = True
                                break
                if terminate:
                    break

    @property
    def checks(self):
        all = [check for check in vars(type(self)).values()
               if hasattr(check, '_check_for')]
        return sorted(all, key=lambda check: not check._terminal)

    @check_for(Definition, terminal=True)
    def check_docstring_missing(self, definition, docstring):
        """D10{0,1,2,3}: Public definitions should have docstrings.

        All modules should normally have docstrings.  [...] all functions and
        classes exported by a module should also have docstrings. Public
        methods (including the __init__ constructor) should also have
        docstrings.

        Note: Public (exported) definitions are either those with names listed
              in __all__ variable (if present), or those that do not start
              with a single underscore.

        """
        if (not docstring and definition.is_public or
                docstring and is_blank(eval(docstring))):
            codes = {Module: 'D100', Class: 'D101', NestedClass: 'D101',
                     Method: 'D102', Function: 'D103', NestedFunction: 'D103'}
            return Error('%s: Docstring missing' % codes[type(definition)])

    @check_for(Definition)
    def check_one_liners(self, definition, docstring):
        """D200: One-liner docstrings should fit on one line with quotes.

        The closing quotes are on the same line as the opening quotes.
        This looks better for one-liners.

        """
        if docstring:
            lines = eval(docstring).split('\n')
            if len(lines) > 1:
                non_empty_lines = sum(1 for l in lines if not is_blank(l))
                if non_empty_lines == 1:
                    return Error('D200: One-line docstring should not occupy '
                                 '%s lines' % len(lines))

    @check_for(Function)
    def check_no_blank_before(self, function, docstring):  # def
        """D20{1,2}: No blank lines allowed around function/method docstring.

        There's no blank line either before or after the docstring.

        """
        # NOTE: This does not take comments into account.
        # NOTE: This does not take into account functions with groups of code.
        if docstring:
            before, _, after = function.source.partition(docstring)
            blanks_before = list(map(is_blank, before.split('\n')[:-1]))
            blanks_after = list(map(is_blank, after.split('\n')[1:]))
            blanks_before_count = sum(takewhile(bool, reversed(blanks_before)))
            blanks_after_count = sum(takewhile(bool, blanks_after))
            if blanks_before_count != 0:
                yield Error('D201: No blank lines allowed *before* %s '
                            'docstring, found %s'
                            % (function.kind, blanks_before_count))
            if not all(blanks_after) and blanks_after_count != 0:
                yield Error('D202: No blank lines allowed *after* %s '
                            'docstring, found %s'
                            % (function.kind, blanks_after_count))

    @check_for(Class)
    def check_blank_before_after_class(slef, class_, docstring):
        """D20{3,4}: Class docstring should have 1 blank line around them.

        Insert a blank line before and after all docstrings (one-line or
        multi-line) that document a class -- generally speaking, the class's
        methods are separated from each other by a single blank line, and the
        docstring needs to be offset from the first method by a blank line;
        for symmetry, put a blank line between the class header and the
        docstring.

        """
        # NOTE: this gives flase-positive in this case
        # class Foo:
        #
        #     """Docstring."""
        #
        #
        # # comment here
        # def foo(): pass
        if docstring:
            before, _, after = class_.source.partition(docstring)
            blanks_before = list(map(is_blank, before.split('\n')[:-1]))
            blanks_after = list(map(is_blank, after.split('\n')[1:]))
            blanks_before_count = sum(takewhile(bool, reversed(blanks_before)))
            blanks_after_count = sum(takewhile(bool, blanks_after))
            if blanks_before_count != 1:
                yield Error('D203: Expected 1 blank line *before* class '
                            'docstring, found %s' % blanks_before_count)
            if not all(blanks_after) and blanks_after_count != 1:
                yield Error('D204: Expected 1 blank line *after* class '
                            'docstring, found %s' % blanks_after_count)

    @check_for(Definition)
    def check_blank_after_summary(self, definition, docstring):
        """D205: Blank line missing between one-line summary and description.

        Multi-line docstrings consist of a summary line just like a one-line
        docstring, followed by a blank line, followed by a more elaborate
        description. The summary line may be used by automatic indexing tools;
        it is important that it fits on one line and is separated from the
        rest of the docstring by a blank line.

        """
        if docstring:
            lines = eval(docstring).strip().split('\n')
            if len(lines) > 1 and not is_blank(lines[1]):
                return Error()

    @check_for(Definition)
    def check_indent(self, definition, docstring):
        """D20{6,7,8}: The entire docstring should be indented same as code.

        The entire docstring is indented the same as the quotes at its
        first line.

        """
        if docstring:
            before_docstring, _, _ = definition.source.partition(docstring)
            _, _, indent = before_docstring.rpartition('\n')
            lines = docstring.split('\n')
            if len(lines) > 1:
                lines = lines[1:]  # First line does not need indent.
                indents = [leading_space(l) for l in lines if not is_blank(l)]
                if set(' \t') == set(''.join(indents) + indent):
                    return Error('D206: Docstring indented with both tabs and '
                                 'spaces')
                if (len(indents) > 1 and min(indents[:-1]) > indent
                        or indents[-1] > indent):
                    return Error('D208: Docstring is over-indented')
                if min(indents) < indent:
                    return Error('D207: Docstring is under-indented')

    @check_for(Definition)
    def check_newline_after_last_paragraph(self, definition, docstring):
        """D209: Put multi-line docstring closing quotes on separate line.

        Unless the entire docstring fits on a line, place the closing
        quotes on a line by themselves.

        """
        if docstring:
            lines = [l for l in eval(docstring).split('\n') if not is_blank(l)]
            if len(lines) > 1:
                if docstring.split("\n")[-1].strip() not in ['"""', "'''"]:
                    return Error('D209: Put multi-line docstring closing '
                                 'quotes on separate line')

    @check_for(Definition)
    def check_triple_double_quotes(self, definition, docstring):
        r'''D300: Use """triple double quotes""".

        For consistency, always use """triple double quotes""" around
        docstrings. Use r"""raw triple double quotes""" if you use any
        backslashes in your docstrings. For Unicode docstrings, use
        u"""Unicode triple-quoted strings""".

        Note: Exception to this is made if the docstring contains
              """ quotes in its body.

        '''
        if docstring and '"""' in eval(docstring) and docstring.startswith(
                ("'''", "r'''", "u'''")):
            # Allow ''' quotes if docstring contains """, because otherwise """
            # quotes could not be expressed inside docstring.  Not in PEP 257.
            return
        if docstring and not docstring.startswith(('"""', 'r"""', 'u"""')):
            quotes = "'''" if "'''" in docstring[:4] else "'"
            return Error('D300: Expected """-quotes, got %s-quotes' % quotes)

    @check_for(Definition)
    def check_backslashes(self, definition, docstring):
        r'''D301: Use r""" if any backslashes in a docstring.

        Use r"""raw triple double quotes""" if you use any backslashes
        (\) in your docstrings.

        '''
        # Just check that docstring is raw, check_triple_double_quotes
        # ensures the correct quotes.
        if docstring and '\\' in docstring and not docstring.startswith('r'):
            return Error()

    @check_for(Definition)
    def check_unicode_docstring(self, definition, docstring):
        r'''D302: Use u""" for docstrings with Unicode.

        For Unicode docstrings, use u"""Unicode triple-quoted strings""".

        '''
        # Just check that docstring is unicode, check_triple_double_quotes
        # ensures the correct quotes.
        if docstring and sys.version_info[0] <= 2:
            if not is_ascii(docstring) and not docstring.startswith('u'):
                return Error()

    @check_for(Definition)
    def check_ends_with_period(self, definition, docstring):
        """D400: First line should end with a period.

        The [first line of a] docstring is a phrase ending in a period.

        """
        if docstring:
            summary_line = eval(docstring).strip().split('\n')[0]
            if not summary_line.endswith('.'):
                return Error("D400: First line should end with '.', not %r"
                             % summary_line[-1])

    @check_for(Function)
    def check_imperative_mood(self, function, docstring):  # def context
        """D401: First line should be in imperative mood: 'Do', not 'Does'.

        [Docstring] prescribes the function or method's effect as a command:
        ("Do this", "Return that"), not as a description; e.g. don't write
        "Returns the pathname ...".

        """
        if docstring:
            stripped = eval(docstring).strip()
            if stripped:
                first_word = stripped.split()[0]
                if first_word.endswith('s') and not first_word.endswith('ss'):
                    return Error('D401: First line should be imperative: '
                                 '%r, not %r' % (first_word[:-1], first_word))

    @check_for(Function)
    def check_no_signature(self, function, docstring):  # def context
        """D402: First line should not be function's or method's "signature".

        The one-line docstring should NOT be a "signature" reiterating the
        function/method parameters (which can be obtained by introspection).

        """
        if docstring:
            first_line = eval(docstring).strip().split('\n')[0]
            if function.name + '(' in first_line.replace(' ', ''):
                return Error("D402: First line should not be %s's signature"
                             % function.kind)

    # Somewhat hard to determine if return value is mentioned.
    # @check(Function)
    def SKIP_check_return_type(self, function, docstring):
        """D40x: Return value type should be mentioned.

        [T]he nature of the return value cannot be determined by
        introspection, so it should be mentioned.

        """
        if docstring and function.returns_value:
            if 'return' not in docstring.lower():
                return Error()


if __name__ == '__main__':
    try:
        sys.exit(main(*parse_options()))
    except KeyboardInterrupt:
        pass

########NEW FILE########
__FILENAME__ = test
# encoding: utf-8
# No docstring, so we can test D100
import sys


expected = set([])


def expect(*args):
    """Decorator that expects a certain PEP 257 violation."""
    none = lambda a: None
    if len(args) == 1:
        return lambda f: expected.add((f.__name__, args[0])) or none(f()) or f
    expected.add(args)


expect('class_', 'D101: Docstring missing')


class class_:

    expect('meta', 'D101: Docstring missing')

    class meta:
        """"""

    @expect('D102: Docstring missing')
    def method():
        pass

    def _ok_since_private():
        pass

    @expect('D102: Docstring missing')
    def __init__(self=None):
        pass


@expect('D103: Docstring missing')
def function():
    """ """
    def ok_since_nested():
        pass

    @expect('D103: Docstring missing')
    def nested():
        ''


@expect('D200: One-line docstring should not occupy 3 lines')
def asdlkfasd():
    """
    Wrong.
    """


@expect('D201: No blank lines allowed *before* function docstring, found 1')
def leading_space():

    """Leading space."""


@expect('D202: No blank lines allowed *after* function docstring, found 1')
def trailing_space():
    """Leading space."""

    pass


@expect('D201: No blank lines allowed *before* function docstring, found 1')
@expect('D202: No blank lines allowed *after* function docstring, found 1')
def trailing_and_leading_space():

    """Trailing and leading space."""

    pass


expect('LeadingSpaceMissing',
       'D203: Expected 1 blank line *before* class docstring, found 0')


class LeadingSpaceMissing:
    """Leading space missing."""


expect('TrailingSpace',
       'D204: Expected 1 blank line *after* class docstring, found 0')


class TrailingSpace:

    """TrailingSpace."""
    pass


expect('LeadingAndTrailingSpaceMissing',
       'D203: Expected 1 blank line *before* class docstring, found 0')
expect('LeadingAndTrailingSpaceMissing',
       'D204: Expected 1 blank line *after* class docstring, found 0')


class LeadingAndTrailingSpaceMissing:
    """Leading and trailing space missing."""
    pass


@expect('D205: Blank line missing between one-line summary and description')
def asdfasdf():
    """Summary.
    Description.

    """


@expect('D207: Docstring is under-indented')
def asdfsdf():
    """Summary.

Description.

    """


@expect('D207: Docstring is under-indented')
def asdsdfsdffsdf():
    """Summary.

    Description.

"""


@expect('D208: Docstring is over-indented')
def asdfsdsdf24():
    """Summary.

       Description.

    """


@expect('D208: Docstring is over-indented')
def asdfsdsdfsdf24():
    """Summary.

    Description.

        """


@expect('D208: Docstring is over-indented')
def asdfsdfsdsdsdfsdf24():
    """Summary.

        Description.

    """


@expect('D209: Put multi-line docstring closing quotes on separate line')
def asdfljdf24():
    """Summary.

    Description."""


@expect('D300: Expected """-quotes, got \'\'\'-quotes')
def lsfklkjllkjl():
    r'''Summary.'''


@expect('D300: Expected """-quotes, got \'-quotes')
def lalskklkjllkjl():
    r'Summary.'


@expect('D301: Use r""" if any backslashes in a docstring')
def lalsksdewnlkjl():
    """Sum\\mary."""


if sys.version_info[0] <= 2:
    @expect('D302: Use u""" for docstrings with Unicode')
    def lasewnlkjl():
        """Юникод."""


@expect("D400: First line should end with '.', not 'y'")
def lwnlkjl():
    """Summary"""


@expect("D401: First line should be imperative: 'Return', not 'Returns'")
def liouiwnlkjl():
    """Returns foo."""


@expect("D402: First line should not be function's signature")
def foobar():
    """Signature: foobar()."""


def new_209():
    """First line.

    More lines.
    """
    pass


def old_209():
    """One liner.

    Multi-line comments. OK to have extra blank line

    """


def run():
    """Run the functions above and check errors agains expected errors."""
    import pep257
    expect(__file__, 'D100: Docstring missing')
    results = list(pep257.check([__file__]))
    assert set(map(type, results)) == set([pep257.Error]), results
    results = set([(e.definition.name, e.message) for e in results])
    print('\n  extra: %r' % (results - expected))
    print('\nmissing: %r' % (expected - results))
    assert expected == results

########NEW FILE########
__FILENAME__ = test_definitions
from pep257 import (StringIO, TokenStream, Parser,
                    Module, Class, Method, Function, NestedFunction)


_ = type('', (), dict(__repr__=lambda *a: '_', __eq__=lambda *a: True))()


parse = Parser()
source = '''
"""Module."""
__all__ = ('a', 'b'
           'c',)
def function():
    "Function."
    def nested_1():
        """Nested."""
    if True:
        def nested_2():
            pass
class class_(object):
    """Class."""
    def method_1(self):
        """Method."""
    def method_2(self):
        def nested_3(self):
            """Nested."""
'''
source_alt = '''
__all__ = ['a', 'b'
           'c',]
'''
source_alt_nl_at_bracket = '''
__all__ = [

    # Inconvenient comment.
    'a', 'b' 'c',]
'''


def test_parser():
    all = ('a', 'bc')
    module = parse(StringIO(source), 'file.py')
    assert len(list(module)) == 8
    assert Module('file.py', _, 1, len(source.split('\n')),
                  '"""Module."""', _, _, all) == module

    function, class_ = module.children
    assert Function('function', _, _, _, '"Function."', _, module) == function
    assert Class('class_', _, _, _, '"""Class."""', _, module) == class_

    nested_1, nested_2 = function.children
    assert NestedFunction('nested_1', _, _, _,
                          '"""Nested."""', _, function) == nested_1
    assert NestedFunction('nested_2', _, _, _, None, _, function) == nested_2
    assert nested_1.is_public is False

    method_1, method_2 = class_.children
    assert method_1.parent == method_2.parent == class_
    assert Method('method_1', _, _, _, '"""Method."""', _, class_) == method_1
    assert Method('method_2', _, _, _, None, _, class_) == method_2

    nested_3, = method_2.children
    assert NestedFunction('nested_3', _, _, _,
                          '"""Nested."""', _, method_2) == nested_3
    assert nested_3.module == module
    assert nested_3.all == all

    module = parse(StringIO(source_alt), 'file_alt.py')
    assert Module('file_alt.py', _, 1, len(source_alt.split('\n')),
                  None, _, _, all) == module

    module = parse(StringIO(source_alt_nl_at_bracket), 'file_alt_nl.py')
    assert Module('file_alt_nl.py', _, 1,
                  len(source_alt_nl_at_bracket.split('\n')), None, _, _,
                  all) == module


def _test_module():

    module = Module(source, 'module.py')
    assert module.source == source
    assert module.parent is None
    assert module.name == 'module'
    assert module.docstring == '"""Module docstring."""'
    assert module.is_public

    function, = module.children
    assert function.source.startswith('def function')
    assert function.source.endswith('pass\n')
    assert function.parent is module
    assert function.name == 'function'
    assert function.docstring == '"""Function docstring."""'

    #nested_function, = function.children
    #assert nested_function.source.startswith('def nested_function')
    #assert nested_function.source.endswith('pass\n')


def test_token_stream():
    stream = TokenStream(StringIO('hello#world'))
    assert stream.current.value == 'hello'
    assert stream.line == 1
    assert stream.move().value == 'hello'
    assert stream.current.value == '#world'
    assert stream.line == 1


def test_pep257():
    """Run domain-specific tests from test.py file."""
    import test
    test.run()

########NEW FILE########
__FILENAME__ = test_pep257
"""Use tox or py.test to run the test-suite."""
# -*- coding: utf-8 -*-
from __future__ import with_statement

from pytest import skip

import pep257


__all__ = []


@skip
def test_pep257_conformance():
    errors = list(pep257.check(['pep257.py', 'test_pep257.py']))
    print(errors)
    assert len(errors) == 0


def test_get_summary_line_info():
    s1 = '''"""First line summary."""'''
    s2 = '''"""First line summary.
    With subsequent line.
    """'''
    s3 = '''""""""'''
    s4 = '''"""
    Second line summary.
    """'''
    s5 = '''"""
    Second line summary.
    With subsquent line.
    """'''
    assert pep257.get_summary_line_info(s1) == ('First line summary.', 0)
    assert pep257.get_summary_line_info(s2) == ('First line summary.', 0)
    assert pep257.get_summary_line_info(s3) == ('', 0)
    assert pep257.get_summary_line_info(s4) == ('Second line summary.', 1)
    assert pep257.get_summary_line_info(s5) == ('Second line summary.', 1)


def test_parse_docstring():
    s1 = '''def foo():  # o hai comment
    """docstring"""
    2 + 2'''
    assert pep257.parse_docstring(s1) == '"""docstring"""'

    s2 = '''def foo():  # o hai comment
    2 + 2'''
    assert pep257.parse_docstring(s2) is None

    assert pep257.parse_docstring("def foo():pass") is None
    # TODO
    # assert pep257.parse_docstring("def bar():'doc';pass") == "'doc'"


def test_abs_pos():
    assert pep257.abs_pos((1, 0), 'foo') == 0
    assert pep257.abs_pos((1, 2), 'foo') == 2
    assert pep257.abs_pos((2, 0), 'foo\nbar') == 4


def test_rel_pos():
    assert pep257.rel_pos(0, 'foo') == (1, 0)
    assert pep257.rel_pos(2, 'foo') == (1, 2)
    assert pep257.rel_pos(4, 'foo\nbar') == (2, 0)
    assert pep257.rel_pos(6, 'foo\nbar') == (2, 2)


def test_parse_functions():
    parse = pep257.parse_functions
    assert parse('') == []
    # TODO assert pf('def foo():pass') == ['def foo():pass']
    assert parse('def foo():\n    pass\n') == ['def foo():\n    pass\n']
    assert parse('def foo():\n  pass') == ['def foo():\n  pass']
    f1 = '''def foo():\n  pass\ndef bar():\n  pass'''
    assert parse(f1) == ['def foo():\n  pass\n',
                         'def bar():\n  pass']
    f2 = '''def foo():\n  pass\noh, hai\ndef bar():\n  pass'''
    assert parse(f2) == ['def foo():\n  pass\n',
                         'def bar():\n  pass']


def test_parse_methods():
    parse = pep257.parse_methods
    assert parse('') == []
    m1 = '''class Foo:
    def m1():
        pass
    def m2():
        pass'''
    assert parse(m1) == ['def m1():\n        pass\n    ',
                         'def m2():\n        pass']
    m2 = '''class Foo:
    def m1():
        pass
    attribute
    def m2():
        pass'''
    assert parse(m2) == ['def m1():\n        pass\n    ',
                         'def m2():\n        pass']


def test_check_triple_double_quotes():
    check = pep257.check_triple_double_quotes
    assert check("'''Not using triple douple quotes'''", None, None)
    assert not check('"""Using triple double quotes"""', None, None)
    assert not check('r"""Using raw triple double quotes"""', None, None)
    assert not check('u"""Using unicode triple double quotes"""', None, None)


def test_check_backslashes():
    check = pep257.check_backslashes
    assert check('"""backslash\\here""""', None, None)
    assert not check('r"""backslash\\here""""', None, None)


def test_check_unicode_docstring():
    check = pep257.check_unicode_docstring
    assert not check('"""No Unicode here."""', None, None)
    assert not check('u"""Здесь Юникод: øπΩ≈ç√∫˜µ≤"""', None, None)
    assert check('"""Здесь Юникод: øπΩ≈ç√∫˜µ≤"""', None, None)


def test_check_ends_with_period():
    check = pep257.check_ends_with_period
    s1 = '"""Should end with a period"""'
    s2 = '"""Should end with a period."""'
    s3 = '''"""
        Should end with a period
        """'''
    s4 = '''"""
        Should end with a period.
        """'''
    assert check(s1, None, None)
    assert not check(s2, None, None)
    assert check(s3, None, None)
    assert not check(s4, None, None)


def test_check_blank_before_after_class():
    check = pep257.check_blank_before_after_class
    c1 = '''class Perfect(object):

    """This should work perfectly."""

    pass'''
    assert not check('"""This should work perfectly."""', c1, False)

    c2 = '''class BadTop(object):
    """This should fail due to a lack of whitespace above."""

    pass'''
    assert check('"""This should fail due to a lack of whitespace above."""',
                 c2, False)
    c3 = '''class BadBottom(object):

    """This should fail due to a lack of whitespace below."""
    pass'''
    assert check('"""This should fail due to a lack of whitespace below."""',
                 c3, False)
    c4 = '''class GoodWithNoFollowingWhiteSpace(object):

    """This should work."""'''
    assert not check('"""This should work."""',
                     c4, False)
    c5 = '''class GoodWithFollowingWhiteSpace(object):

    """This should work."""


'''
    assert not check('"""This should work."""', c5, False)

    c6 = '''class Perfect(object):

    """This should work perfectly."""

    def foo(self):
        """This should work perfectly."""
        pass

    '''
    assert not check('"""This should work perfectly."""', c6, False)


def test_check_blank_after_summary():
    check = pep257.check_blank_after_summary
    s1 = '''"""Blank line missing after one-line summary.
    ....................
    """'''
    s2 = '''"""Blank line missing after one-line summary.

    """'''
    s3 = '''"""
    Blank line missing after one-line summary.
    ....................
    """'''
    s4 = '''"""
    Blank line missing after one-line summary.

    """'''
    assert check(s1, None, None)
    assert not check(s2, None, None)
    assert check(s3, None, None)
    assert not check(s4, None, None)


def test_check_indent():
    check = pep257.check_indent
    context = '''def foo():
    """Docstring.

    Properly indented.

    """
    pass'''
    assert not check('"""%s"""' % context.split('"""')[1], context, None)
    context = '''def foo():
    """Docstring.

Not Properly indented.

    """
    pass'''
    assert check('"""%s"""' % context.split('"""')[1], context, None)

########NEW FILE########
